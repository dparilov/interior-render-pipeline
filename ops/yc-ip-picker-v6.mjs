#!/usr/bin/env node
/**
 * yc-ip-picker v6
 * - Один поток, зоны чередуются: d, a, d, b
 * - Не 158.160 → сразу skip
 * - 158.160 → ping 10 сек, пауза 5 сек, ещё один ping
 * - При успехе → стоп, пишем в Telegram
 * - Каждые 20 адресов 158.160 → репорт
 * - USB интерфейс определяется динамически
 * - VM 158.160.119.28 не трогаем никогда
 */

import { execFileSync, execSync } from 'child_process';
import { appendFileSync, mkdirSync, writeFileSync } from 'fs';

const FOLDER_ID = 'b1gvdqihg3a1691k3qgo';
const API_BASE  = 'https://vpc.api.cloud.yandex.net/vpc/v1/addresses';
const VM_IP     = '158.160.119.28'; // неприкосновенный
const OPENCLAW  = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN   = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV       = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT      = '125132275';

const IAM = 'REDACTED_TOKEN';

const ZONES = ['ru-central1-d', 'ru-central1-a', 'ru-central1-d', 'ru-central1-b'];

const LOG_DIR  = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/yc-ip-picker-v6.log';
mkdirSync(LOG_DIR, { recursive: true });

const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i+1] : null; };
const MAX_ATTEMPTS = parseInt(getArg('--max') || '1000');
const MAX_158_FAIL = 100; // после 100 неудачных 158.160 — стоп

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

// Динамически находим USB интерфейс (10.101.x.x)
function getUsbIface() {
  try {
    const out = execSync('ip -o addr show', { encoding: 'utf8' });
    for (const line of out.split('\n')) {
      if (line.includes('10.101.')) {
        const parts = line.trim().split(/\s+/);
        if (parts[1]) return parts[1];
      }
    }
  } catch {}
  return null;
}

function pingViaUSB(ip) {
  const iface = getUsbIface();
  if (!iface) {
    log(`USB iface not found!`);
    return false;
  }
  try {
    // Первый пинг — 10 пакетов
    execSync(`ping -c 10 -i 1 -W 3 -I ${iface} ${ip}`, { timeout: 20000, stdio: 'pipe' });
    return true;
  } catch {}
  return false;
}

function pingViaUSB2(ip) {
  const iface = getUsbIface();
  if (!iface) return false;
  try {
    // Второй пинг — 6 пакетов
    execSync(`ping -c 6 -i 1 -W 3 -I ${iface} ${ip}`, { timeout: 15000, stdio: 'pipe' });
    return true;
  } catch {}
  return false;
}

async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Authorization': `Bearer ${IAM}`, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status}: ${text.substring(0,300)}`);
  return text ? JSON.parse(text) : {};
}

async function deleteIP(id) {
  try { await apiCall('DELETE', `${API_BASE}/${id}`); } catch (e) {
    log(`DELETE ERROR ${id}: ${e.message}`);
  }
}

// --- Main ---
log(`=== START v6 zones=${ZONES.join(',')} max=${MAX_ATTEMPTS} ===`);
log(`=== USB iface: ${getUsbIface() || 'NOT FOUND'} ===`);

let attempt = 0;
let found158 = 0; // счётчик 158.160 адресов
let pingOk = 0;
let pingFail = 0;
let vmCheckOk = 0;
let vmCheckFail = 0;

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const zone = ZONES[(attempt - 1) % ZONES.length];
  const name = `yc-v6-${attempt}`;

  // Резервируем
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
    log(`[${attempt}] ERROR: ${e.message}`);
    await new Promise(r => setTimeout(r, 3000));
    continue;
  }

  if (!ip) {
    log(`[${attempt}] NO_IP`);
    if (addressId) await deleteIP(addressId);
    continue;
  }

  // Защита VM
  if (ip === VM_IP) {
    log(`[${attempt}] VM IP ${ip} — skip, не удаляем`);
    continue;
  }

  // Скипаем не 158.160
  if (!ip.startsWith('158.160.')) {
    log(`[${attempt}] SKIP ip=${ip} zone=${zone}`);
    await deleteIP(addressId);
    await new Promise(r => setTimeout(r, 300));
    continue;
  }

  found158++;
  const iface = getUsbIface();
  log(`[${attempt}] 158.160 #${found158} zone=${zone} ip=${ip} iface=${iface} — ping1...`);

  // Первый пинг
  const ping1 = pingViaUSB(ip);

  if (ping1) {
    pingOk++;
    log(`[${attempt}] ✅ PING1 OK ip=${ip}`);
    sendTelegram(
      `✅ Найден кандидат!\nIP: \`${ip}\`\nЗона: ${zone}\nAddress ID: \`${addressId}\`\nПопытка: ${attempt}, 158.160: ${found158}\n\nАдрес держу. Оставить?`
    );
    log(`=== PAUSE — ${ip} зарезервирован, ждём решения ===`);
    process.exit(0);
  }

  // Пауза 5 сек
  log(`[${attempt}] ping1 fail, pause 5s...`);
  await new Promise(r => setTimeout(r, 5000));

  // Второй пинг
  log(`[${attempt}] ping2 ip=${ip}...`);
  const ping2 = pingViaUSB2(ip);

  if (ping2) {
    pingOk++;
    log(`[${attempt}] ✅ PING2 OK ip=${ip}`);
    sendTelegram(
      `✅ Найден кандидат (ping2)!\nIP: \`${ip}\`\nЗона: ${zone}\nAddress ID: \`${addressId}\`\nПопытка: ${attempt}, 158.160: ${found158}\n\nАдрес держу. Оставить?`
    );
    log(`=== PAUSE — ${ip} зарезервирован, ждём решения ===`);
    process.exit(0);
  }

  pingFail++;
  log(`[${attempt}] PING FAIL ip=${ip}, releasing`);
  await deleteIP(addressId);
  await new Promise(r => setTimeout(r, 500));

  // Проверяем VM каждые 5 адресов 158.160
  if (found158 % 5 === 0) {
    const iface = getUsbIface();
    let vmOk = false;
    if (iface) {
      try {
        execSync(`ping -c 3 -W 2 -I ${iface} ${VM_IP}`, { timeout: 10000, stdio: 'pipe' });
        vmOk = true;
      } catch {}
    }
    if (!vmOk) {
      vmCheckFail++;
      log(`[VM CHECK] ⚠️ VM ${VM_IP} не пингуется! iface=${iface}`);
      sendTelegram(`⚠️ ALERT: VM ${VM_IP} не отвечает на пинг через USB!\nUSB iface: ${iface || 'НЕ НАЙДЕН'}`);
    } else {
      vmCheckOk++;
      log(`[VM CHECK] ✅ VM ${VM_IP} OK (${vmCheckOk} ok / ${vmCheckFail} fail)`);
    }
  }

  // Стоп после 100 неудачных 158.160
  if (pingFail >= MAX_158_FAIL) {
    log(`=== STOP: ${MAX_158_FAIL} неудачных 158.160 ===`);
    const candidates = execSync(
      `grep "PING FAIL" ${LOG_FILE} | grep -oP '158\\.160\\.\\d+\\.\\d+' | sort -u`,
      { encoding: 'utf8' }
    ).trim();
    const outFile = LOG_DIR + '/yc-v6-candidates.txt';
    writeFileSync(outFile, candidates + '\n');
    sendTelegram(`🛑 Остановка после ${MAX_158_FAIL} неудачных 158.160\nВсего попыток: ${attempt}\nСписок адресов отправляю...`);
    execFileSync(OPENCLAW, ['message', 'send', '--channel', 'telegram', '--target', CHAT, '--silent', '--media', outFile, '-m', `${pingFail} адресов 158.160 без пинга — для Windows утилиты`], { timeout: 15000, env: ENV });
    process.exit(0);
  }

  // Репорт каждые 10 адресов 158.160
  if (found158 % 10 === 0) {
    const total158 = found158;
    const ratio = `${pingOk}/${total158} живых (${Math.round(pingOk/total158*100)}%)`;
    const msg = `📊 Репорт YC #${found158/10}\nПопыток всего: ${attempt}\n158.160 адресов: ${found158}\n✅ Живых: ${pingOk} | ❌ Без пинга: ${pingFail}\nRatio: ${ratio}\nVM ${VM_IP}: ✅ ${vmCheckOk} / ⚠️ ${vmCheckFail}\nUSB: ${getUsbIface() || 'N/A'}`;
    log(`REPORT: attempts=${attempt} found158=${found158} ok=${pingOk} fail=${pingFail}`);
    sendTelegram(msg);
  }
}

const msg = `❌ Не нашли за ${attempt} попыток (158.160: ${found158}, ping ok: ${pingOk})`;
log(`=== DONE: ${msg} ===`);
sendTelegram(msg);
