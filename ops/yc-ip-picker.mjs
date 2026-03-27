#!/usr/bin/env node
/**
 * yc-ip-picker.mjs v2
 * Резервирует статический IP в Yandex Cloud, перебирая зоны по кругу.
 * Логирует все попытки, ведёт итоговую статистику.
 *
 * Usage:
 *   node yc-ip-picker.mjs --token <IAM_TOKEN> [--max-attempts 500] [--name my-ip]
 */

import { execFileSync } from 'child_process';
import { appendFileSync, writeFileSync, mkdirSync } from 'fs';

const FOLDER_ID = 'b1gvdqihg3a1691k3qgo';
const API_BASE = 'https://vpc.api.cloud.yandex.net/vpc/v1/addresses';
const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const NVM_BIN = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };
const CHAT = '125132275';

const ZONES = ['ru-central1-a', 'ru-central1-b', 'ru-central1-d', 'ru-central1-e'];

const ALLOWED_SUBNETS = [
  '130.193.62.0/24',
  '178.154.244.0/24',
  '178.154.245.0/24',
  '185.32.187.0/24',
  '213.180.199.0/24',
  '5.45.214.0/24',
  '77.88.44.0/24',
  '77.88.55.0/24',
  '87.250.255.0/24',
  '89.232.188.0/24',
];

// Log paths
const LOG_DIR = process.env.HOME + '/.openclaw/workspace/logs';
const LOG_FILE = LOG_DIR + '/yc-ip-picker.log';
const REPORT_FILE = LOG_DIR + '/yc-ip-picker-report.txt';

// Parse args
const args = process.argv.slice(2);
const getArg = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i+1] : null; };
const IAM_TOKEN = getArg('--token');
const MAX_ATTEMPTS = parseInt(getArg('--max-attempts') || '500');
const IP_NAME_BASE = getArg('--name') || `ip-picker-${Date.now()}`;

if (!IAM_TOKEN) {
  console.error('Usage: node yc-ip-picker.mjs --token <IAM_TOKEN> [--max-attempts 500] [--name my-ip]');
  process.exit(1);
}

mkdirSync(LOG_DIR, { recursive: true });

// Subnet check
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

// Logging
function log(line) {
  const ts = new Date().toISOString();
  const msg = `${ts} ${line}`;
  console.log(msg);
  appendFileSync(LOG_FILE, msg + '\n');
}

// API
async function apiCall(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Authorization': `Bearer ${IAM_TOKEN}`, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(`API ${method} ${url} → ${res.status}: ${text}`);
  return JSON.parse(text);
}

async function reserveIP(name, zone) {
  return apiCall('POST', API_BASE, {
    folderId: FOLDER_ID,
    name,
    externalIpv4AddressSpec: { zoneId: zone },
  });
}

async function deleteIP(addressId) {
  return apiCall('DELETE', `${API_BASE}/${addressId}`);
}

function sendTelegram(msg) {
  try {
    execFileSync(OPENCLAW, ['message', 'send', '--channel', 'telegram', '--target', CHAT, '--silent', '-m', msg],
      { timeout: 15000, env: ENV });
  } catch (e) {
    log(`SEND_ERROR: ${e.message}`);
  }
}

// Stats: { ip -> { zone, count, rejected } }
const stats = {};

function recordIP(ip, zone, accepted) {
  if (!stats[ip]) stats[ip] = { zone, count: 0, rejected: 0 };
  stats[ip].count++;
  if (!accepted) stats[ip].rejected++;
}

function buildReport(result) {
  const lines = [];
  lines.push('=== YC IP Picker — Итоговый отчёт ===');
  lines.push(`Дата: ${new Date().toISOString()}`);
  lines.push(`Попыток: ${result.attempts} из ${MAX_ATTEMPTS}`);
  lines.push(`Зоны: ${ZONES.join(', ')}`);
  lines.push(`Результат: ${result.success ? `✅ НАЙДЕН ${result.ip} (${result.zone})` : '❌ НЕ НАЙДЕН'}`);
  lines.push('');
  lines.push('--- Уникальные адреса (отклонённые) ---');

  const sorted = Object.entries(stats)
    .filter(([, v]) => v.rejected > 0)
    .sort((a, b) => b[1].count - a[1].count);

  if (sorted.length === 0) {
    lines.push('(нет отклонённых)');
  } else {
    lines.push(`${'IP'.padEnd(20)} ${'Зона'.padEnd(18)} ${'Выдан'.padStart(6)} ${'Откл.'.padStart(6)}`);
    lines.push('-'.repeat(55));
    for (const [ip, v] of sorted) {
      lines.push(`${ip.padEnd(20)} ${v.zone.padEnd(18)} ${String(v.count).padStart(6)} ${String(v.rejected).padStart(6)}`);
    }
  }

  lines.push('');
  lines.push('--- Статистика по зонам ---');
  const byZone = {};
  for (const [, v] of Object.entries(stats)) {
    if (!byZone[v.zone]) byZone[v.zone] = { total: 0, unique: 0 };
    byZone[v.zone].total += v.count;
    byZone[v.zone].unique++;
  }
  for (const [zone, z] of Object.entries(byZone)) {
    lines.push(`  ${zone}: ${z.total} попыток, ${z.unique} уникальных IP`);
  }

  return lines.join('\n');
}

// Main
log(`=== START max_attempts=${MAX_ATTEMPTS} zones=${ZONES.join(',')} ===`);
console.log(`Allowed subnets: ${ALLOWED_SUBNETS.join(', ')}`);
console.log('');

let attempt = 0;
let found = null;

while (attempt < MAX_ATTEMPTS) {
  attempt++;
  const zone = ZONES[(attempt - 1) % ZONES.length];
  const name = `${IP_NAME_BASE}-${attempt}`;

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
    ip = address.externalIpv4Address?.address || address.address?.externalIpv4Address?.address;
  } catch (e) {
    log(`[${attempt}/${MAX_ATTEMPTS}] zone=${zone} ERROR: ${e.message}`);
    await new Promise(r => setTimeout(r, 2000));
    continue;
  }

  if (!ip) {
    log(`[${attempt}/${MAX_ATTEMPTS}] zone=${zone} NO_IP id=${addressId}, deleting`);
    try { await deleteIP(addressId); } catch {}
    continue;
  }

  const subnet = matchedSubnet(ip);
  if (subnet) {
    log(`[${attempt}/${MAX_ATTEMPTS}] ACCEPTED zone=${zone} ip=${ip} subnet=${subnet} id=${addressId}`);
    recordIP(ip, zone, true);
    found = { ip, zone, subnet, addressId, attempts: attempt };
    break;
  } else {
    log(`[${attempt}/${MAX_ATTEMPTS}] REJECTED zone=${zone} ip=${ip} id=${addressId}`);
    recordIP(ip, zone, false);
    try {
      await deleteIP(addressId);
    } catch (e) {
      log(`[${attempt}/${MAX_ATTEMPTS}] DELETE_ERROR zone=${zone} ip=${ip}: ${e.message}`);
    }
    await new Promise(r => setTimeout(r, 500));
  }
}

// Write report
const report = buildReport(found ? { success: true, ...found, attempts: attempt } : { success: false, attempts: attempt });
writeFileSync(REPORT_FILE, report);
console.log('\n' + report);
log(`=== END attempts=${attempt} result=${found ? 'FOUND ' + found.ip : 'NOT_FOUND'} ===`);

// Telegram message
if (found) {
  const msg = [
    `✅ YC IP найден!`,
    `IP: \`${found.ip}\``,
    `Подсеть: ${found.subnet}`,
    `Зона: ${found.zone}`,
    `Address ID: \`${found.addressId}\``,
    `Попыток: ${found.attempts}`,
    `Лог: ${LOG_FILE}`,
    `Отчёт: ${REPORT_FILE}`,
  ].join('\n');
  sendTelegram(msg);
} else {
  const uniqueCount = Object.keys(stats).length;
  const msg = [
    `❌ YC IP не найден за ${attempt} попыток`,
    `Уникальных IP отклонено: ${uniqueCount}`,
    `Зоны: ${ZONES.join(', ')}`,
    `Отчёт: ${REPORT_FILE}`,
  ].join('\n');
  sendTelegram(msg);
  process.exit(1);
}
