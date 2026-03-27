import { chromium } from '/home/dima/.nvm/versions/node/v22.22.0/lib/node_modules/playwright/index.mjs';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  httpCredentials: { username: 'datamint', password: 'Datamint-d3m0-v8K9q' }
});
const page = await context.newPage();

await page.goto('https://inv.ondatamint.com/dashboard/', { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(3000);

// Set investor filter to parilov2026 + Fully opened
await page.evaluate(() => {
  const setDashProps = (id, props) => {
    const el = document.querySelector(id);
    if (!el) return false;
    const rk = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
    if (!rk) return false;
    let fiber = el[rk];
    for (let i = 0; i < 40 && fiber; i++) {
      if (fiber.memoizedProps?.setProps) {
        fiber.memoizedProps.setProps(props);
        return true;
      }
      fiber = fiber.return;
    }
    return false;
  };
  setDashProps('#investor_selection', { value: ['parilov2026'] });
  setDashProps('#position_status_filter', { value: 'Fully opened' });
});

await page.waitForTimeout(2000);
await page.click('#reload_full_dash_board');
await page.waitForTimeout(6000);

// Extract position table data
const positions = await page.evaluate(() => {
  const table = document.querySelector('#mongo_events_based_position_metrics_table');
  if (!table) return null;
  const rk = Object.keys(table).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  if (!rk) return null;
  let fiber = table[rk];
  for (let i = 0; i < 80 && fiber; i++) {
    if (fiber.memoizedProps?.data) return fiber.memoizedProps.data;
    fiber = fiber.return;
  }
  return null;
});

await browser.close();

if (!positions || positions.length === 0) {
  console.log('No data found');
  process.exit(1);
}

const prefix = 'mongo_events_based_position_metrics_table-';

// Show sample values to understand format
const sample = positions[0];
const apProxRaw = sample[`${prefix}axe-point-proximity`];
const apAbsRaw = sample[`${prefix}axe-point-proximity-abs`];
const investRaw = sample[`${prefix}investments`];
console.log(`Sample: name=${sample[`${prefix}position-name`]}, ap-proximity=${apProxRaw}, ap-proximity-abs=${apAbsRaw}, invest=${investRaw}`);

// Parse and filter: |AP%| < 20% means axe-point-proximity-abs < 0.20
const parseNum = (v) => {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v.replace('%', '').replace(',', '.').replace(/[^0-9.\-]/g, ''));
  return NaN;
};

const filtered = positions
  .map(row => {
    const apAbs = parseNum(row[`${prefix}axe-point-proximity-abs`]);
    const invest = parseNum(row[`${prefix}investments`]);
    const name = row[`${prefix}position-name`] ?? '';
    const apProx = parseNum(row[`${prefix}axe-point-proximity`]);
    return { name, apAbs, apProx, invest };
  })
  .filter(r => !isNaN(r.apAbs) && !isNaN(r.invest) && r.apAbs < 0.20);

console.log(`\nПозиции с |AP%| < 20%: ${filtered.length} из ${positions.length}`);

// Aggregate by brackets
const brackets = [
  { label: '0–5%',   min: 0,    max: 0.05  },
  { label: '5–10%',  min: 0.05, max: 0.10  },
  { label: '10–15%', min: 0.10, max: 0.15  },
  { label: '15–20%', min: 0.15, max: 0.20  },
];

console.log('');
for (const b of brackets) {
  const inBracket = filtered.filter(r => r.apAbs >= b.min && r.apAbs < b.max);
  const total = inBracket.reduce((sum, r) => sum + r.invest, 0);
  console.log(`|AP%| ${b.label}: ${inBracket.length} поз., $${total.toFixed(2)}`);
}

const grandTotal = filtered.reduce((sum, r) => sum + r.invest, 0);
console.log(`\nИТОГО: $${grandTotal.toFixed(2)} (${filtered.length} позиций)`);

if (filtered.length > 0) {
  console.log('\nПозиции:');
  filtered.sort((a, b) => a.apAbs - b.apAbs);
  for (const r of filtered) {
    console.log(`  ${r.name}: |AP|=${(r.apAbs*100).toFixed(2)}%, AP=${(r.apProx*100).toFixed(2)}%, invest=$${r.invest.toFixed(2)}`);
  }
}
