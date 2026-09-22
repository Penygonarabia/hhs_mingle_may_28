const puppeteer = require('puppeteer-core');
const path = require('path');
const http = require('http');

async function authenticate() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: '2.0',
      params: { db: 'dbprod', login: 'admin', password: 'admin' }
    });
    const req = http.request({
      hostname: 'localhost', port: 8069, path: '/web/session/authenticate', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) }
    }, res => {
      let cookie = '';
      if (res.headers['set-cookie']) {
        for (const raw of res.headers['set-cookie']) {
          const match = raw.match(/session_id=([^;]+)/);
          if (match) { cookie = match[1]; break; }
        }
      }
      res.on('data', () => {});
      res.on('end', () => resolve(cookie));
    });
    req.write(postData);
    req.end();
  });
}

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
  await page.goto('http://localhost:8069/web#action=pbi_sales_dashboards.action_pbi_sales_mail_dashboard_sman', { waitUntil: 'networkidle2' });
  await page.waitForSelector('.pbi-sales-mail-sman-dashboard');

  // Select Year 2025
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    if (s) { s.value = '2025'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);

  // Select Month 9 (September)
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[1];
    if (s) { s.value = '9'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);

  await new Promise(r => setTimeout(r, 2000));

  // Find the KPI container or wrap the KPI rows
  const kpiBox = await page.evaluate(() => {
    const kpiRows = document.querySelectorAll('.pbi-kpi-row');
    if (kpiRows.length > 0) {
      const parent = kpiRows[0].parentElement;
      const rect = parent.getBoundingClientRect();
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
    }
    return null;
  });

  const outputDir = '/Users/saravanan/Projects/cloud/docs/images/comparison';
  
  if (kpiBox && kpiBox.width > 0 && kpiBox.height > 0) {
    console.log('KPI Box dimensions:', kpiBox);
    await page.screenshot({
      path: path.join(outputDir, '00_kpis.png'),
      clip: {
        x: Math.max(0, kpiBox.x),
        y: Math.max(0, kpiBox.y),
        width: Math.min(1600, kpiBox.width),
        height: kpiBox.height
      }
    });
    console.log('Captured crisp KPI tiles screenshot to 00_kpis.png!');
  } else {
    // Fallback: capture first KPI row
    const kpiRow = await page.$('.pbi-kpi-row');
    if (kpiRow) {
      await kpiRow.screenshot({ path: path.join(outputDir, '00_kpis.png') });
    }
  }

  await browser.close();
}

run().catch(console.error);
