const puppeteer = require('puppeteer-core');
const http = require('http');
const path = require('path');

async function authenticate() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ jsonrpc: '2.0', params: { db: 'dbprod', login: 'admin', password: 'admin' } });
    const req = http.request({
      hostname: 'localhost', port: 8069, path: '/web/session/authenticate', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) }
    }, res => {
      let cookie = '';
      if (res.headers['set-cookie']) {
        for (const raw of res.headers['set-cookie']) {
          const m = raw.match(/session_id=([^;]+)/);
          if (m) { cookie = m[1]; break; }
        }
      }
      res.on('data', () => {});
      res.on('end', () => resolve(cookie));
    });
    req.write(postData);
    req.end();
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function run() {
  const sessionId = await authenticate();
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });
  await page.setCookie({ name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });
  await page.goto('http://localhost:8069/web#action=pbi_sales_dashboards.action_pbi_sales_kpi_dashboard_sman', { waitUntil: 'networkidle2' });
  
  await page.waitForSelector('.pbi-sales-sman-dashboard', { timeout: 20000 });

  // Select Year 2025
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    if (s) { s.value = '2025'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await sleep(2000);

  // Select Month 9 (September)
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[1];
    if (s) { s.value = '9'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await sleep(3000);

  const kpiRow = await page.$('.pbi-kpi-row.twelve') || await page.$('.pbi-kpi-row');
  if (kpiRow) {
    await kpiRow.screenshot({ path: '/Users/saravanan/Projects/cloud/docs/images/comparison/00_kpi_tiles_sep2025.png' });
    console.log('Saved 00_kpi_tiles_sep2025.png!');
  } else {
    console.log('kpiRow not found');
  }

  // Also check values in KPI row
  const values = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.pbi-kpi')).map(k => ({
      label: k.querySelector('.label')?.innerText || '',
      value: k.querySelector('.value')?.innerText || ''
    }));
  });
  console.log('KPI Tiles values:', JSON.stringify(values, null, 2));

  await browser.close();
}
run();
