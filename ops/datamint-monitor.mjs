import { chromium } from 'playwright';
import { appendFileSync } from 'fs';
import { execFileSync } from 'child_process';

const THRESHOLD = 0.001; // 0.1% as decimal
const CHAT = '-1003596522926';
const TOPIC = '41';
const LOG = process.env.HOME + '/.openclaw/workspace/datamint-monitor.log';
const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
const P = 'mongo_events_based_position_metrics_table-';
const NVM_BIN = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin';
const ENV = { ...process.env, PATH: NVM_BIN + ':' + (process.env.PATH || ''), NODE_OPTIONS: '' };

function log(msg) {
  appendFileSync(LOG, `${new Date().toISOString()} ${msg}\n`);
}

function send(msg) {
  try {
    execFileSync(OPENCLAW, ['message', 'send', '--channel', 'telegram', '--target', CHAT, '--thread-id', TOPIC, '--silent', '-m', msg], { timeout: 15000, env: ENV });
  } catch (e) {
    log(`SEND ERROR: ${e.message}`);
  }
}

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    httpCredentials: { username: 'datamint', password: 'Datamint-d3m0-v8K9q' }
  });
  const page = await context.newPage();
  await page.goto('https://inv.ondatamint.com/dashboard/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Set filters and wait for data to update
  await page.evaluate(() => {
    function setProps(id, val) {
      const el = document.querySelector('#' + id);
      const rk = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
      let fiber = el[rk];
      for (let i = 0; i < 30 && fiber; i++) {
        if (fiber.memoizedProps?.setProps) { fiber.memoizedProps.setProps(val); return true; }
        fiber = fiber.return;
      }
      return false;
    }
    setProps('investor_selection', { value: ['parilov2026'] });
    setProps('position_status_filter', { value: 'Fully opened' });
  });

  // Wait for network to settle after filter change
  await page.waitForTimeout(2000);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Get data and verify filters applied
  const data = await page.evaluate((P) => {
    const tableEl = document.querySelector('#mongo_events_based_position_metrics_table');
    const rk = Object.keys(tableEl).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
    let fiber = tableEl[rk];
    for (let i = 0; i < 20 && fiber; i++) {
      if (fiber.memoizedProps?.data && Array.isArray(fiber.memoizedProps.data))
        return fiber.memoizedProps.data;
      fiber = fiber.return;
    }
    return null;
  }, P);

  if (!data || data.length === 0) {
    log('No data returned');
    process.exit(1);
  }

  // Verify: only parilov2026 rows should be present
  const owners = [...new Set(data.map(r => r[P + 'owner']))];
  if (owners.length !== 1 || owners[0] !== 'parilov2026') {
    log(`FILTER NOT APPLIED: owners=${owners.join(',')} total=${data.length}. Skipping.`);
    process.exit(1);
  }

  const rows = data
    .map(r => ({
      name: r[P + 'position-name'],
      dp_minus_pnl: (r[P + 'default-profit-pct'] || 0) - (r[P + 'pnl-pct'] || 0),
      expiration: r[P + 'expiration-timestamp'] || '—',
      dp_usd: r[P + 'default-profit'] || 0,
      pnl_usd: r[P + 'pnl'] || 0,
      pnl_pct_annual: r[P + 'pnl-pct-annual'] || 0,
      dp_pct_annual: r[P + 'default-profit-pct-annual'] || 0,
      ap: r[P + 'axe-point'] != null ? (r[P + 'axe-point'] * 100).toFixed(1) + '%' : '—',
    }))
    .sort((a, b) => a.dp_minus_pnl - b.dp_minus_pnl);

  if (rows.length === 0) {
    log('No rows after filter');
    process.exit(0);
  }

  const min = rows[0];
  const minPct = (min.dp_minus_pnl * 100).toFixed(2);

  if (min.dp_minus_pnl < THRESHOLD) {
    const msg = [
      `⚠️ DataMint Alert:`,
      `\`#parilov2026_${min.name}\``,
      `DP%-PnL% = ${minPct}% (порог: ${(THRESHOLD*100).toFixed(1)}%)`,
      `AP = ${min.ap}`,
      `Expiration: ${min.expiration}`,
      `Default PnL: $${min.dp_usd.toFixed(2)}`,
      `Current PnL: $${min.pnl_usd.toFixed(2)}`,
      `Default PnL%Y: ${(min.dp_pct_annual * 100).toFixed(2)}%`,
      `Current PnL%Y: ${(min.pnl_pct_annual * 100).toFixed(2)}%`,
    ].join('\n');
    log(`ALERT: ${min.name} DP%-PnL%=${minPct}%`);
    send(msg);
  } else {
    log(`OK: min DP%-PnL%=${minPct}% (${min.name}), ${rows.length} positions`);
  }

} catch (e) {
  log(`ERROR: ${e.message}`);
} finally {
  if (browser) await browser.close();
}
