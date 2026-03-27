import { chromium } from 'playwright';
import { appendFileSync } from 'fs';
import { execFileSync } from 'child_process';

const THRESHOLD = 14; // annDefaultProfit > 14%
const CHAT = '-1003596522926';
const TOPIC = '41';
const LOG = process.env.HOME + '/.openclaw/workspace/searcher-monitor.log';
const OPENCLAW = process.env.HOME + '/.nvm/versions/node/v22.22.0/bin/openclaw';
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
    httpCredentials: { username: 'datamint', password: 'Datamint-d3m0-v8K9q' },
    permissions: ['clipboard-read', 'clipboard-write']
  });
  const page = await context.newPage();
  await page.goto('https://inv.ondatamint.com/searcher/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);

  // Set filters
  await page.evaluate(() => {
    function sp(id, val) {
      const el = document.querySelector('#' + id);
      if (!el) return;
      const rk = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
      let f = el[rk];
      for (let i = 0; i < 30 && f; i++) {
        if (f.memoizedProps?.setProps) { f.memoizedProps.setProps(val); return; }
        f = f.return;
      }
    }
    sp('bet-kind-radio', { value: 'Default profit' });
    sp('option-date-range', { start_date: '2026-06-25', end_date: '2026-07-03' });
    sp('ap-abs-control-group-lower-limit-input', { value: 20 });
  });
  await page.waitForTimeout(1000);
  await page.click('#refresh-button');
  await page.waitForTimeout(20000);
  await page.waitForLoadState('networkidle');

  // Get data, find top by annDefaultProfit
  const topInfo = await page.evaluate(() => {
    const el = document.querySelector('#data-table');
    const rk = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
    let f = el[rk];
    let data = null;
    for (let i = 0; i < 40 && f; i++) {
      if (f.memoizedProps?.data?.length > 0) { data = f.memoizedProps.data; break; }
      f = f.return;
    }
    if (!data || data.length === 0) return null;
    const sorted = [...data].sort((a, b) => {
      const va = parseFloat((a.annDefaultProfit || '').replace(/[^0-9.\-]/g, '')) || 0;
      const vb = parseFloat((b.annDefaultProfit || '').replace(/[^0-9.\-]/g, '')) || 0;
      return vb - va;
    });
    const top = sorted[0];
    return {
      annDP: parseFloat((top.annDefaultProfit || '').replace(/[^0-9.\-]/g, '')) || 0,
      row_id: top.row_id,
      betSlug: top.betSlug,
      ap: top.ap || '—'
    };
  });

  if (!topInfo) {
    log('No data returned');
    process.exit(1);
  }

  if (topInfo.annDP < THRESHOLD) {
    log(`OK: top annDP=${topInfo.annDP}% AP=${topInfo.ap} (${topInfo.betSlug}), below ${THRESHOLD}%`);
    process.exit(0);
  }

  // Sort table via setProps so the top row is first visible
  await page.evaluate(() => {
    const el = document.querySelector('#data-table');
    const rk = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
    let f = el[rk];
    for (let i = 0; i < 40 && f; i++) {
      if (f.memoizedProps?.setProps) {
        f.memoizedProps.setProps({
          sort_by: [{ column_id: 'annDefaultProfit', direction: 'desc' }]
        });
        return;
      }
      f = f.return;
    }
  });
  await page.waitForTimeout(2000);

  // Double-click betSlug in first row to open popup
  const betSlugCell = page.locator('#data-table td[data-dash-column="betSlug"]').first();
  await betSlugCell.dblclick();
  await page.waitForTimeout(2000);

  const popupVisible = await page.locator('#cell-popup').isVisible();
  if (!popupVisible) {
    log(`ALERT but popup failed: annDP=${topInfo.annDP}% AP=${topInfo.ap} ${topInfo.betSlug}`);
    send(`📊 Searcher Alert: annDP=${topInfo.annDP}%, AP=${topInfo.ap}\n${topInfo.betSlug}\n(popup not available)`);
    process.exit(0);
  }

  // Click Copy to fill clipboard
  await page.click('#popup-copy');
  await page.waitForTimeout(500);

  const clipText = await page.evaluate(() => navigator.clipboard.readText());
  await page.click('#popup-ok');

  log(`ALERT: annDP=${topInfo.annDP}% AP=${topInfo.ap} ${topInfo.betSlug}`);
  send(`📊 Searcher Alert (annDP=${topInfo.annDP}%, AP=${topInfo.ap}):\n\`\`\`\n${clipText}\n\`\`\``);

} catch (e) {
  log(`ERROR: ${e.message}`);
} finally {
  if (browser) await browser.close();
}
