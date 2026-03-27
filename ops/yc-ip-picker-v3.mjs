#!/usr/bin/env node
/**
 * yc-ip-picker v3
 * - Резервирует IP в YC, пропускает всё кроме 158.160.x.x
 * - При 158.160.x.x — пингует через USB модем (enxf643213298a9)
 * - Если ping OK → оставляет, назначает VM, репортит в Telegram
 * - API через дефолтный маршрут (VPN), пинг через USB
 */

import { execFileSync, execSync } from 'child_process';
import { appendFileSync, mkdirSync } from 'fs';

const FOLDER_ID = 'b1gvdqihg3a1691k3qgo';
const VM_ID = 'fhm1n6ch1gkk5eqckb73';
const VM_ZONE = 'ru-central1-a';
const API_BASE = 'https://vpc.api.cloud.yandex.net/vpc/v1/addresses';
const COMPUTE_BASE = 'https://compute.api.cloud.yandex.net/compute/v1';
const USB_IFACE = 'enxf643213298a9';
const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT = '125132275';

const IAM = 'REDACTED_TOKEN';

const LOG_DIR = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/yc-ip-picker-v3.log';
mkdirSync(LOG_DIR, { recursive: true });

const args = process.argv.slice(2);
const getArg = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i+1] : null; };
const MAX_ATTEMPTS = parseInt(getArg('--max-attempts') || '500');

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
  } catch (e) {
    log(`SEND_ERROR: ${e.message}`);
  }
}

async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Authorization': `Bearer ${IAM}`, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status}: ${text}`);
  return text ? JSON.parse(text) : {};
}

async function reserveIP(name, zone) {
  return apiCall('POST', API_BASE, {
    folderId: FOLDER_ID,
    name,
    externalIpv4AddressSpec: { zoneId: zone },
  });
}

async function deleteIP(id) {
  return apiCall('DELETE', `${API_BASE}/${id}`);
}

function pingViaUSB(ip) {
  try {
    // 10 пакетов, интервал 1 сек, таймаут ответа 3 сек — как у Windows утилиты
    execSync(`ping -c 10 -i 1 -W 3 -I ${USB_IFACE} ${ip}`, { timeout: 20000, stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

async function getVMNetworkInterface() {
  const vm = await apiCall('GET', `${COMPUTE_BASE}/instances/${VM_ID}?view=FULL`);
  const iface = vm.networkInterfaces?.[0];
  return iface;
}

async function assignIPToVM(addressId, ip) {
  // Получаем текущий интерфейс VM
  const iface = await getVMNetworkInterface();
  if (!iface) throw new Error('No network interface on VM');
  
  const subnetId = iface.subnetId;
  const ifaceIndex = iface.index || 0;

  // Обновляем primary address — назначаем зарезервированный IP
  return apiCall('PATCH', `${COMPUTE_BASE}/instances/${VM_ID}`, {
    updateMask: 'networkInterfaces',
    networkInterfaces: [{
      index: String(ifaceIndex),
      subnetId,
      primaryV4AddressSpec: {
        oneToOneNatSpec: {
          ipVersion: 'IPV4',
          address: ip,
        }
      }
    }]
  });
}

// Зоны — только те где есть 158.160.x.x (a, b, d)
const ZONES = ['ru-central1-a', 'ru-central1-b', 'ru-central1-d', 'ru-central1-a'];

log(`=== START v3 max_attempts=${MAX_ATTEMPTS} usb_iface=${USB_IFACE} vm=${VM_ID} ===`);

let attempt = 0;

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const zone = ZONES[(attempt - 1) % ZONES.length];
  const name = `yc-v3-${attempt}`;

  let addressId, ip;
  try {
    const result = await reserveIP(name, zone);
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
    log(`[${attempt}] zone=${zone} ERROR: ${e.message}`);
    await new Promise(r => setTimeout(r, 2000));
    continue;
  }

  if (!ip) {
    log(`[${attempt}] zone=${zone} NO_IP, deleting ${addressId}`);
    try { await deleteIP(addressId); } catch {}
    continue;
  }

  // Шаг 2: только 158.160.x.x
  const is158 = ip.startsWith('158.160.');
  if (!is158) {
    log(`[${attempt}] SKIP zone=${zone} ip=${ip} (not 158.160)`);
    try { await deleteIP(addressId); } catch {}
    await new Promise(r => setTimeout(r, 300));
    continue;
  }

  // Шаг 3: пингуем через USB модем
  log(`[${attempt}] 158.160 FOUND zone=${zone} ip=${ip} id=${addressId} — pinging via ${USB_IFACE}...`);
  const pingOk = pingViaUSB(ip);

  if (!pingOk) {
    log(`[${attempt}] PING FAIL ip=${ip}, releasing`);
    try { await deleteIP(addressId); } catch {}
    await new Promise(r => setTimeout(r, 500));
    continue;
  }

  // Шаг 4: ping OK!
  log(`[${attempt}] PING OK ip=${ip} zone=${zone} id=${addressId} — KEEPING`);
  sendTelegram(`✅ IP найден и пингуется!\nIP: \`${ip}\`\nЗона: ${zone}\nPing через USB: ✅\nAddress ID: \`${addressId}\`\n\nПытаюсь назначить VM...`);

  // Шаг 5: назначаем VM
  try {
    await assignIPToVM(addressId, ip);
    log(`[${attempt}] VM ASSIGNED ip=${ip} vm=${VM_ID}`);
    sendTelegram(`✅ IP \`${ip}\` назначен VM \`${VM_ID}\`\nЗона: ${zone}`);
  } catch (e) {
    log(`[${attempt}] VM ASSIGN ERROR: ${e.message}`);
    sendTelegram(`⚠️ IP \`${ip}\` найден и зарезервирован, но назначить VM не удалось:\n${e.message}\n\nAddress ID: \`${addressId}\``);
  }

  log(`=== DONE attempt=${attempt} ip=${ip} ===`);
  process.exit(0);
}

log(`=== NOT FOUND after ${MAX_ATTEMPTS} attempts ===`);
sendTelegram(`❌ Не нашли подходящий 158.160.x.x IP за ${MAX_ATTEMPTS} попыток`);
process.exit(1);
