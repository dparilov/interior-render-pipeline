import puppeteer from 'puppeteer';
const browser = await puppeteer.launch({headless: true, args: ['--no-sandbox','--disable-setuid-sandbox']});

const pdfOpts = {format: 'A4', margin: {top:'15mm',bottom:'15mm',left:'20mm',right:'20mm'}, printBackground: true};
const base = '/home/dima/.openclaw/workspace-dev/culture-spb';

for (const [html, pdf] of [['spec.html','SPEC.pdf'],['spec-external.html','SPEC-EXTERNAL.pdf']]) {
  const page = await browser.newPage();
  await page.goto(`file://${base}/${html}`, {waitUntil: 'networkidle0'});
  await page.pdf({...pdfOpts, path: `${base}/${pdf}`});
  await page.close();
  console.log(`Created ${pdf}`);
}
await browser.close();
