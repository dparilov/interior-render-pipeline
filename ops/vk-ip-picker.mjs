#!/usr/bin/env node
/**
 * vk-ip-picker.mjs
 * Резервирует floating IP в VK Cloud (OpenStack-совместимый API),
 * перебирая зоны по кругу. Логирует все попытки, ведёт итоговую статистику.
 *
 * VK Cloud API: OpenStack Neutron / nova
 * Docs: https://cloud.vk.com/docs/networks/vnet/how-to/create-floating-ip
 *
 * Usage:
 *   node vk-ip-picker.mjs \
 *     --token <KEYSTONE_TOKEN> \
 *     --project <PROJECT_ID> \
 *     --region <REGION> \
 *     [--max-attempts 500] [--name my-ip]
 *
 * Regions: RegionOne (Moscow), RegionTwo (Saint-Petersburg)
 * Get token: https://cloud.vk.com/docs/tools-for-using-services/api/rest-api/case-keystone-token
 */

import { execFileSync } from 'child_process';
import { appendFileSync, writeFileSync, mkdirSync } from 'fs';

// ── Config ────────────────────────────────────────────────────────────────────
// VK Cloud OpenStack endpoint
const NEUTRON_BASE = (region) =>
  `https://infra.mail.ru:9696/v2.0`;

// External network ID in VK Cloud (public network for floating IPs)
// Default for RegionOne: ext-net
const EXT_NET_NAME = 'ext-net';

const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT = '125132275';

const LOG_DIR = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/vk-ip-picker.log';
const REPORT_FILE = LOG_DIR + '/vk-ip-picker-report.txt';

// ── Args ──────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i+1] : null; };

const TOKEN = getArg('--token');
const PROJECT_ID = getArg('--project');
const REGION = getArg('--region') || 'RegionOne';
const MAX_ATTEMPTS = parseInt(getArg('--max-attempts') || '500');
const IP_NAME_BASE = getArg('--name') || `vk-pick-${Date.now()}`;

// Allowed subnets — передай через --subnets "1.2.3.0/24,4.5.6.0/24"
// или отредактируй массив ниже
let ALLOWED_SUBNETS = [];
const subnetsArg = getArg('--subnets');
if (subnetsArg) {
  ALLOWED_SUBNETS = subnetsArg.split(',').map(s => s.trim());
} else {
  // Заглушка — замени когда будет список
  ALLOWED_SUBNETS = [
    // '1.2.3.0/24',
  ];
}

if (!TOKEN || !PROJECT_ID) {
  console.error([
    'Usage: node vk-ip-picker.mjs \\',
    '  --token <KEYSTONE_TOKEN> \\',
    '  --project <PROJECT_ID> \\',
    '  [--region RegionOne] \\',
    '  [--subnets "1.2.3.0/24,4.5.6.0/24"] \\',
    '  [--max-attempts 500] \\',
    '  [--name my-ip]',
    '',
    'Regions: RegionOne (Moscow), RegionTwo (Saint-Petersburg)',
    'Get token: https://cloud.vk.com/docs/tools-for-using-services/api/rest-api/case-keystone-token',
  ].join('\n'));
  process.exit(1);
}

if (ALLOWED_SUBNETS.length === 0) {
  console.error('ERROR: No allowed subnets configured. Pass --subnets or edit the script.');
  process.exit(1);
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function ipToInt(ip) {
  return ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct), 0) >>> 0;
}
function isInSubnet(ip, cidr) {
  const [subnet, bits] = cidr.split('/');
  const mask = ~((1 << (32 - parseInt(bits))) - 1) >>> 0;
  return (ipToInt(ip) & mask) === (ipToInt(subnet) & mask);
}
function matchedSubnet(ip) {
  return ALLOWED_SUBNETS.find(s => isInSubnet(ip, s)) || null;
}

mkdirSync(LOG_DIR, { recursive: true });

function log(line) {
  const ts = new Date().toISOString();
  const msg = `${ts} ${line}`;
  console.log(msg);
  appendFileSync(LOG_FILE, msg + '\n');
}

async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: {
      'X-Auth-Token': TOKEN,
      'Content-Type': 'application/json',
      'X-OpenStack-Region': REGION,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`API ${method} ${url} → ${res.status}: ${text}`);
  return text ? JSON.parse(text) : {};
}

// Find external network ID by name
async function getExtNetId() {
  const res = await apiCall('GET', `${NEUTRON_BASE(REGION)}/networks?name=${EXT_NET_NAME}`);
  const net = res.networks?.[0];
  if (!net) throw new Error(`External network '${EXT_NET_NAME}' not found`);
  return net.id;
}

async function createFloatingIP(extNetId, description) {
  const res = await apiCall('POST', `${NEUTRON_BASE(REGION)}/floatingips`, {
    floatingip: {
      floating_network_id: extNetId,
      description,
      tenant_id: PROJECT_ID,
    }
  });
  return res.floatingip;
}

async function deleteFloatingIP(floatingipId) {
  await apiCall('DELETE', `${NEUTRON_BASE(REGION)}/floatingips/${floatingipId}`);
}

function sendTelegram(msg) {
  try {
    execFileSync(OPENCLAW, ['message', 'send', '--channel', 'telegram', '--target', CHAT, '--silent', '-m', msg],
      { timeout: 15000, env: ENV });
  } catch (e) {
    log(`SEND_ERROR: ${e.message}`);
  }
}

// Stats
const stats = {};
function recordIP(ip, zone, accepted) {
  if (!stats[ip]) stats[ip] = { zone, count: 0, rejected: 0 };
  stats[ip].count++;
  if (!accepted) stats[ip].rejected++;
}

function buildReport(result) {
  const lines = [];
  lines.push('=== VK Cloud IP Picker — Итоговый отчёт ===');
  lines.push(`Дата: ${new Date().toISOString()}`);
  lines.push(`Попыток: ${result.attempts} из ${MAX_ATTEMPTS}`);
  lines.push(`Регион: ${REGION}`);
  lines.push(`Результат: ${result.success ? `✅ НАЙДЕН ${result.ip}` : '❌ НЕ НАЙДЕН'}`);
  lines.push('');
  lines.push('--- Уникальные адреса (отклонённые) ---');

  const sorted = Object.entries(stats)
    .filter(([, v]) => v.rejected > 0)
    .sort((a, b) => b[1].count - a[1].count);

  if (sorted.length === 0) {
    lines.push('(нет отклонённых)');
  } else {
    lines.push(`${'IP'.padEnd(20)} ${'Выдан'.padStart(6)} ${'Откл.'.padStart(6)}`);
    lines.push('-'.repeat(35));
    for (const [ip, v] of sorted) {
      lines.push(`${ip.padEnd(20)} ${String(v.count).padStart(6)} ${String(v.rejected).padStart(6)}`);
    }
  }
  return lines.join('\n');
}

// ── Main ──────────────────────────────────────────────────────────────────────
log(`=== START provider=vk-cloud region=${REGION} max_attempts=${MAX_ATTEMPTS} subnets=${ALLOWED_SUBNETS.join(',')} ===`);

let extNetId;
try {
  extNetId = await getExtNetId();
  log(`External network ID: ${extNetId}`);
} catch (e) {
  log(`FATAL: ${e.message}`);
  process.exit(1);
}

let attempt = 0;
let found = null;

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const desc = `${IP_NAME_BASE}-${attempt}`;

  let fip;
  try {
    fip = await createFloatingIP(extNetId, desc);
  } catch (e) {
    log(`[${attempt}/${MAX_ATTEMPTS}] ERROR creating: ${e.message}`);
    await new Promise(r => setTimeout(r, 2000));
    continue;
  }

  const ip = fip.floating_ip_address;
  const fipId = fip.id;

  if (!ip) {
    log(`[${attempt}/${MAX_ATTEMPTS}] NO_IP id=${fipId}, deleting`);
    try { await deleteFloatingIP(fipId); } catch {}
    continue;
  }

  const subnet = matchedSubnet(ip);
  if (subnet) {
    log(`[${attempt}/${MAX_ATTEMPTS}] ACCEPTED ip=${ip} subnet=${subnet} id=${fipId}`);
    recordIP(ip, REGION, true);
    found = { ip, subnet, fipId, attempts: attempt };
    break;
  } else {
    log(`[${attempt}/${MAX_ATTEMPTS}] REJECTED ip=${ip} id=${fipId}`);
    recordIP(ip, REGION, false);
    try { await deleteFloatingIP(fipId); } catch (e) {
      log(`[${attempt}/${MAX_ATTEMPTS}] DELETE_ERROR: ${e.message}`);
    }
    await new Promise(r => setTimeout(r, 500));
  }
}

const report = buildReport(found ? { success: true, ...found, attempts: attempt } : { success: false, attempts: attempt });
writeFileSync(REPORT_FILE, report);
console.log('\n' + report);
log(`=== END attempts=${attempt} result=${found ? 'FOUND ' + found.ip : 'NOT_FOUND'} ===`);

if (found) {
  const msg = [
    `✅ VK Cloud IP найден!`,
    `IP: \`${found.ip}\``,
    `Подсеть: ${found.subnet}`,
    `Регион: ${REGION}`,
    `Floating IP ID: \`${found.fipId}\``,
    `Попыток: ${found.attempts}`,
  ].join('\n');
  sendTelegram(msg);
} else {
  const uniqueCount = Object.keys(stats).length;
  const msg = [
    `❌ VK Cloud IP не найден за ${attempt} попыток`,
    `Уникальных IP отклонено: ${uniqueCount}`,
    `Регион: ${REGION}`,
    `Отчёт: ${REPORT_FILE}`,
  ].join('\n');
  sendTelegram(msg);
  process.exit(1);
}
