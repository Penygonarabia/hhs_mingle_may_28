const puppeteer = require('puppeteer-core');
const http = require('http');

async function authenticate() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: '2.0',
      params: { db: 'dbprod', login: 'admin', password: 'admin' }
    });
    const req = http.request({
      hostname: 'localhost',
      port: 8069,
      path: '/web/session/authenticate',
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) }
    }, (res) => {
      let cookie = '';
      for (const raw of res.headers['set-cookie']) {
        const match = raw.match(/session_id=([^;]+)/);
        if (match) cookie = match[1];
      }
      res.on('data', () => {});
      res.on('end', () => resolve(cookie));
    });
    req.write(postData);
    req.end();
  });
}

async function captureKPIs() {
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
  await page.waitForSelector('.pbi-sales-mail-sman-dashboard', { timeout: 30000 });

  await page.waitForFunction(() => {
    const selects = document.querySelectorAll('.filter-group select');
    return selects.length >= 2 && selects[0].options.length > 0 && selects[1].options.length > 0;
  }, { timeout: 30000 });

  // Select 2025 and 9
  const yrP = page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    if (s) { s.value = '2025'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await yrP;

  const mthP = page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[1];
    if (s) { s.value = '9'; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await mthP;

  await new Promise(r => setTimeout(r, 2000));

  const clip = await page.evaluate(() => {
    const heading1 = document.querySelectorAll('.kpi-heading')[0];
    const row2 = document.querySelectorAll('.pbi-kpi-row')[1];
    if (!heading1 || !row2) return null;
    const r1 = heading1.getBoundingClientRect();
    const r2 = row2.getBoundingClientRect();
    return {
      x: r1.left,
      y: r1.top,
      width: Math.max(r1.width, r2.width),
      height: (r2.bottom - r1.top)
    };
  });

  if (clip) {
    await page.screenshot({
      path: '/Users/saravanan/Projects/cloud/docs/images/comparison/00_kpis.png',
      clip: clip
    });
    console.log('Saved exact 00_kpis.png with clip:', clip);
  } else {
    console.log('Could not find KPI elements to clip');
  }

  await browser.close();
}

captureKPIs();
