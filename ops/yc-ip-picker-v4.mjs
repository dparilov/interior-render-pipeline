#!/usr/bin/env node
/**
 * yc-ip-picker v4 — 4 параллельных воркера по зонам
 * Каждый воркер резервирует IP в своей зоне, проверяет 158.160, пингует через USB
 * Останавливаются все как только один находит живой IP
 */

import { execFileSync, execSync } from 'child_process';
import { appendFileSync, mkdirSync } from 'fs';

const FOLDER_ID = 'b1gvdqihg3a1691k3qgo';
const VM_ID = 'fhm1n6ch1gkk5eqckb73';
const API_BASE = 'https://vpc.api.cloud.yandex.net/vpc/v1/addresses';
const COMPUTE_BASE = 'https://compute.api.cloud.yandex.net/compute/v1';
const USB_IFACE = 'enxf643213298a9';
const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT = '125132275';

const IAM = 'REDACTED_TOKEN';

// 4 воркера — 4 зоны (a используется дважды т.к. самая перспективная)
const WORKER_ZONES = ['ru-central1-a', 'ru-central1-b', 'ru-central1-d', 'ru-central1-a'];

const LOG_DIR = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/yc-ip-picker-v4.log';
mkdirSync(LOG_DIR, { recursive: true });

const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i+1] : null; };
const MAX_PER_WORKER = parseInt(getArg('--max') || '200');

let done = false; // глобальный флаг остановки
let stats = { total: 0, found158: 0, pingOk: 0 };

function log(line) {
  const ts = new Date().toISOString();
  const msg = `${ts} ${line}`;
  console.log(msg);
  appendFileSync(LOG_FILE, msg + '\n');
}

function sendTelegram(msg) {
  try {
    execFileSync(OPENCLAW, ['message', 'send', '--channel', 'telegram', '--target', CHAT, '--silent', '-m', msg],
      { timeout: 15000, env: ENV });
  } catch (e) { log(`SEND_ERROR: ${e.message}`); }
}

async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Authorization': `Bearer ${IAM}`, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status}: ${text.substring(0, 200)}`);
  return text ? JSON.parse(text) : {};
}

function pingViaUSB(ip) {
  try {
    execSync(`ping -c 10 -i 1 -W 3 -I ${USB_IFACE} ${ip}`, { timeout: 20000, stdio: 'pipe' });
    return true;
  } catch { return false; }
}

async function cleanupAddress(id, ip = null) {
  // Если есть IP и он 158.160 — сначала пингуем, вдруг живой
  if (ip && ip.startsWith('158.160.') && !done) {
    const alive = pingViaUSB(ip);
    if (alive) {
      log(`CLEANUP PING OK — ${ip} пингуется! Оставляем id=${id}`);
      done = true;
      stats.pingOk++;
      sendTelegram(`✅ IP найден при очистке!\nIP: \`${ip}\`\nAddress ID: \`${id}\`\nПинг ✅`);
      return; // не удаляем
    }
  }
  try { await apiCall('DELETE', `${API_BASE}/${id}`); } catch {}
}

async function worker(workerId, zone) {
  log(`[W${workerId}] START zone=${zone}`);
  let attempt = 0;

  while (!done && attempt < MAX_PER_WORKER) {
    attempt++;
    stats.total++;
    const name = `yc-v4-w${workerId}-${attempt}`;

    let addressId, ip;
    try {
      const result = await apiCall('POST', API_BASE, {
        folderId: FOLDER_ID,
        name,
        externalIpv4AddressSpec: { zoneId: zone },
      });
      let address;
      if (result.metadata?.addressId) {
        await new Promise(r => setTimeout(r, 3000));
        address = await apiCall('GET', `${API_BASE}/${result.metadata.addressId}`);
      } else {
        address = result;
      }
      addressId = address.id;
      ip = address.externalIpv4Address?.address;
    } catch (e) {
      log(`[W${workerId}] attempt=${attempt} ERROR: ${e.message}`);
      await new Promise(r => setTimeout(r, 3000));
      continue;
    }

    if (!ip) {
      log(`[W${workerId}] attempt=${attempt} NO_IP, deleting`);
      if (addressId) await cleanupAddress(addressId, ip);
      continue;
    }

    if (!ip.startsWith('158.160.')) {
      log(`[W${workerId}] SKIP zone=${zone} ip=${ip}`);
      await cleanupAddress(addressId, null);
      await new Promise(r => setTimeout(r, 200));
      continue;
    }

    if (done) {
      log(`[W${workerId}] done flag set, releasing ${ip}`);
      await cleanupAddress(addressId, ip);
      break;
    }

    stats.found158++;
    log(`[W${workerId}] 158.160 FOUND zone=${zone} ip=${ip} id=${addressId} — pinging...`);
    const pingOk = pingViaUSB(ip);

    if (!pingOk) {
      log(`[W${workerId}] PING FAIL ip=${ip}, releasing`);
      await cleanupAddress(addressId, ip);
      await new Promise(r => setTimeout(r, 300));
      continue;
    }

    // ПОБЕДА
    if (done) {
      // другой воркер уже нашёл — отпускаем
      log(`[W${workerId}] PING OK but already done, releasing ${ip}`);
      await cleanupAddress(addressId, null); // уже нашли — просто удаляем
      break;
    }

    done = true;
    stats.pingOk++;
    log(`[W${workerId}] ✅ PING OK ip=${ip} zone=${zone} id=${addressId}`);
    sendTelegram(`✅ IP найден!\nIP: \`${ip}\`\nЗона: ${zone}\nВоркер: W${workerId}\nПопыток всего: ${stats.total}\n\nНазначаю VM...`);

    // Назначаем VM
    try {
      // Получаем текущий интерфейс VM
      const vm = await apiCall('GET', `${COMPUTE_BASE}/instances/${VM_ID}?view=FULL`);
      const iface = vm.networkInterfaces?.[0];
      log(`[W${workerId}] VM iface: subnetId=${iface?.subnetId}`);

      // Используем updateNetworkInterface
      const op = await apiCall('POST', `${COMPUTE_BASE}/instances/${VM_ID}:updateNetworkInterface`, {
        networkInterfaceIndex: '0',
        externalIpv4AddressSpec: {
          address: ip,
        }
      });
      log(`[W${workerId}] VM assign operation: ${op.id || JSON.stringify(op).substring(0,100)}`);
      sendTelegram(`✅ IP \`${ip}\` назначен VM!\nЗона: ${zone}\nAddress ID: \`${addressId}\``);
    } catch (e) {
      log(`[W${workerId}] VM ASSIGN ERROR: ${e.message}`);
      sendTelegram(`⚠️ IP \`${ip}\` найден и зарезервирован!\nПинг ✅, но назначить VM не удалось:\n${e.message.substring(0,200)}\n\nAddress ID: \`${addressId}\`\nЗона: ${zone}`);
    }
    break;
  }

  log(`[W${workerId}] END zone=${zone} attempts=${attempt}`);
}

// Запускаем 4 воркера параллельно
log(`=== START v4 workers=4 max_per_worker=${MAX_PER_WORKER} ===`);
log(`=== Zones: ${WORKER_ZONES.join(', ')} ===`);

await Promise.all(WORKER_ZONES.map((zone, i) => worker(i + 1, zone)));

log(`=== DONE total=${stats.total} found158=${stats.found158} pingOk=${stats.pingOk} ===`);
if (!stats.pingOk) {
  sendTelegram(`❌ Не нашли за ${stats.total} попыток (158.160 встречалось: ${stats.found158})`);
}
