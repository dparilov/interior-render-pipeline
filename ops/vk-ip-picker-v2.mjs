#!/usr/bin/env node
/**
 * vk-ip-picker v2 — один поток, медленно, ждёт подтверждения
 * VK Cloud (OpenStack Neutron API)
 */

import { execFileSync, execSync } from 'child_process';
import { appendFileSync, mkdirSync } from 'fs';

const EXT_NET_ID = 'ec8c610e-6387-447e-83d2-d2c541e88164'; // internet
const NEUTRON    = 'https://infra.mail.ru:9696/v2.0';
const PROJECT_ID = '8dab7410a82c48ad9c1ae6753257479a';
const USB_IFACE  = 'enxf643213298a9';
const OPENCLAW   = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN    = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV        = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT       = '125132275';

const VK_TOKEN = 'gAAAAABpwD31fW2sDaQQ6ixsNLA2uWixNsf1zkUEBhk_uKn7pEKWY9UGSa1pLtkCYJlLwBv0pSm8R9gVF-J6oo_o3Gar-3SgzSMXzGVy3pms3wtxr0FnmzL2o8wCxFoG--rwF8eY_tqt6FllWoLAx6p5KU5Bbke2Hps4ggSgSiKEf6vdazisAPaWXuxSLC3_cK3lH9qGbx6w';

const ALLOWED_SUBNETS = [
  '128.140.173.0/24',
  '178.237.21.0/24',
  '178.237.28.0/24',
  '185.32.249.0/24',
  '185.32.251.0/24',
  '194.186.63.0/24',
  '217.69.132.0/24',
  '79.137.183.0/24',
  '94.139.244.0/24',
  '95.142.201.0/24',
  '95.142.203.0/24',
  '95.142.207.0/24',
  '95.213.44.0/24',
  '95.213.45.0/24',
  '109.120.181.194/24',
];

const LOG_DIR  = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/vk-ip-picker-v2.log';
mkdirSync(LOG_DIR, { recursive: true });

const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i+1] : null; };
const MAX_ATTEMPTS = parseInt(getArg('--max') || '500');

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

function ipToInt(ip) {
  return ip.split('.').reduce((acc, o) => (acc << 8) + parseInt(o), 0) >>> 0;
}
function isInSubnet(ip, cidr) {
  const [subnet, bits] = cidr.split('/');
  const mask = ~((1 << (32 - parseInt(bits))) - 1) >>> 0;
  return (ipToInt(ip) & mask) === (ipToInt(subnet) & mask);
}
function matchedSubnet(ip) {
  return ALLOWED_SUBNETS.find(s => isInSubnet(ip, s)) || null;
}

async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: { 'X-Auth-Token': VK_TOKEN, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${url} → ${res.status}: ${text.substring(0,200)}`);
  return text ? JSON.parse(text) : {};
}

function pingViaUSB(ip, mode) {
  const cmd = mode === 1
    ? `ping -c 10 -i 1 -W 3 -I ${USB_IFACE} ${ip}`
    : `ping -c 4  -i 1 -W 2 -I ${USB_IFACE} ${ip}`;
  try {
    execSync(cmd, { timeout: 25000, stdio: 'pipe' });
    return true;
  } catch { return false; }
}

async function deleteFloatingIP(id) {
  try { await apiCall('DELETE', `${NEUTRON}/floatingips/${id}`); } catch {}
}

log(`=== START VK v2 max=${MAX_ATTEMPTS} subnets=${ALLOWED_SUBNETS.length} ===`);

let attempt = 0;
let foundMatch = 0;
let mode = 1;

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const desc = `vk-v2-${attempt}`;

  let fipId, ip;
  try {
    const res = await apiCall('POST', `${NEUTRON}/floatingips`, {
      floatingip: {
        floating_network_id: EXT_NET_ID,
        description: desc,
        tenant_id: PROJECT_ID,
      }
    });
    fipId = res.floatingip?.id;
    ip = res.floatingip?.floating_ip_address;
  } catch (e) {
    log(`[${attempt}] ERROR: ${e.message}`);
    await new Promise(r => setTimeout(r, 3000));
    continue;
  }

  if (!ip) {
    log(`[${attempt}] NO_IP`);
    if (fipId) await deleteFloatingIP(fipId);
    continue;
  }

  const subnet = matchedSubnet(ip);
  if (!subnet) {
    log(`[${attempt}] SKIP ip=${ip}`);
    await deleteFloatingIP(fipId);
    await new Promise(r => setTimeout(r, 500));
    continue;
  }

  foundMatch++;

  if (foundMatch === 21 && mode === 1) {
    mode = 2;
    log(`=== РЕЖИМ 2: быстрый пинг ===`);
    sendTelegram(`ℹ️ VK: 20 совпадений по подсети, все без пинга. Быстрый режим.`);
  }

  log(`[${attempt}] MATCH #${foundMatch} ip=${ip} subnet=${subnet} mode=${mode} — pinging...`);
  const pingOk = pingViaUSB(ip, mode);

  if (!pingOk) {
    log(`[${attempt}] PING FAIL ip=${ip}, releasing`);
    await deleteFloatingIP(fipId);
    await new Promise(r => setTimeout(r, 500));
    continue;
  }

  // НАШЛИ
  log(`[${attempt}] ✅ PING OK ip=${ip} subnet=${subnet} id=${fipId}`);
  sendTelegram(
    `✅ VK Cloud — найден живой IP!\n` +
    `IP: \`${ip}\`\n` +
    `Подсеть: ${subnet}\n` +
    `Floating IP ID: \`${fipId}\`\n` +
    `Попытка: ${attempt}\n\n` +
    `Адрес зарезервирован. Оставить или продолжать?`
  );
  log(`=== PAUSE — ${ip} зарезервирован ===`);
  process.exit(0);
}

log(`=== NOT FOUND after ${attempt} attempts ===`);
sendTelegram(`❌ VK Cloud: не нашли за ${attempt} попыток`);
