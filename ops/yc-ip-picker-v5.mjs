#!/usr/bin/env node
/**
 * yc-ip-picker v5 — один поток, медленно, ждёт подтверждения
 *
 * Режим 1 (первые 20 адресов 158.160): ping -c 10 -i 1 -W 3
 * Режим 2 (после 20 неудач): ping -c 4 -i 1 -W 2 (быстрее)
 *
 * При успехе — останавливается, пишет в Telegram, ждёт подтверждения
 */

import { execFileSync, execSync } from 'child_process';
import { appendFileSync, mkdirSync } from 'fs';

const FOLDER_ID  = 'b1gvdqihg3a1691k3qgo';
const API_BASE   = 'https://vpc.api.cloud.yandex.net/vpc/v1/addresses';
const USB_IFACE  = 'enxf643213298a9';
const OPENCLAW   = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN    = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV        = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT       = '125132275';

const IAM = 'REDACTED_TOKEN';

const LOG_DIR  = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/yc-ip-picker-v5.log';
mkdirSync(LOG_DIR, { recursive: true });

const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i+1] : null; };
const MAX_ATTEMPTS = parseInt(getArg('--max') || '500');
// Зоны по кругу: d первая (10 живых из 20 в прошлом прогоне), потом a (8), b (2)
const ZONES = ['ru-central1-d', 'ru-central1-a', 'ru-central1-d', 'ru-central1-b'];

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
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status}: ${text.substring(0,300)}`);
  return text ? JSON.parse(text) : {};
}

function pingViaUSB(ip, mode) {
  const cmd = mode === 1
    ? `ping -c 10 -i 1 -W 3 -I ${USB_IFACE} ${ip}`  // режим 1: тщательно
    : `ping -c 4  -i 1 -W 2 -I ${USB_IFACE} ${ip}`; // режим 2: быстро
  try {
    execSync(cmd, { timeout: 25000, stdio: 'pipe' });
    return true;
  } catch { return false; }
}

async function deleteIP(id) {
  try { await apiCall('DELETE', `${API_BASE}/${id}`); } catch {}
}

// --- Main ---
log(`=== START v5 zones=${ZONES.join(',')} max=${MAX_ATTEMPTS} ===`);

let attempt = 0;
let found158 = 0; // счётчик 158.160 адресов
let mode = 1;     // 1 = тщательный пинг, 2 = быстрый

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const name = `yc-v5-${attempt}`;
  const zone = ZONES[(attempt - 1) % ZONES.length];

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

  // Скипаем не 158.160
  if (!ip.startsWith('158.160.')) {
    log(`[${attempt}] SKIP ip=${ip}`);
    await deleteIP(addressId);
    await new Promise(r => setTimeout(r, 500));
    continue;
  }

  found158++;

  // Проверяем режим
  if (found158 === 21 && mode === 1) {
    mode = 2;
    log(`=== РЕЖИМ 2: после 20 неудач, переключаемся на быстрый пинг ===`);
    sendTelegram(`ℹ️ 20 адресов 158.160 — все без пинга. Переключаюсь на быстрый режим.`);
  }

  log(`[${attempt}] 158.160 #${found158} zone=${zone} ip=${ip} mode=${mode} — pinging via USB...`);

  const pingOk = pingViaUSB(ip, mode);

  if (!pingOk) {
    log(`[${attempt}] PING FAIL ip=${ip}, releasing`);
    await deleteIP(addressId);
    await new Promise(r => setTimeout(r, 500));
    continue;
  }

  // ✅ НАШЛИ
  log(`[${attempt}] ✅ PING OK ip=${ip} id=${addressId} — ожидаю подтверждения`);
  sendTelegram(
    `✅ Найден живой IP!\n` +
    `IP: \`${ip}\`\n` +
    `Зона: ${zone}\n` +
    `Address ID: \`${addressId}\`\n` +
    `Попытка: ${attempt}, 158.160 найдено: ${found158}\n\n` +
    `Адрес зарезервирован. Жду твоего подтверждения — оставить или продолжать поиск?`
  );

  // Ждём подтверждения — просто останавливаемся
  log(`=== PAUSE — адрес ${ip} зарезервирован, ждём решения ===`);
  process.exit(0);
}

log(`=== NOT FOUND after ${attempt} attempts, 158.160 found: ${found158} ===`);
sendTelegram(`❌ Не нашли за ${attempt} попыток (158.160 встречалось: ${found158})`);
