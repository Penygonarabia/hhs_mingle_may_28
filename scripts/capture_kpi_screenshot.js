const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const http = require('http');

async function authenticate() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: '2.0',
      params: {
        db: 'dbprod',
        login: 'admin',
        password: 'admin'
      }
    });

    const req = http.request({
      hostname: 'localhost',
      port: 8069,
      path: '/web/session/authenticate',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    }, (res) => {
      let cookie = '';
      if (res.headers['set-cookie']) {
        for (const raw of res.headers['set-cookie']) {
          const match = raw.match(/session_id=([^;]+)/);
          if (match) {
            cookie = match[1];
            break;
          }
        }
      }
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        resolve(cookie);
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function run() {
  console.log('Authenticating...');
  const sessionId = await authenticate();

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });

  await page.setCookie({
    name: 'session_id',
    value: sessionId,
    domain: 'localhost',
    path: '/'
  });

  console.log('Navigating to Sales Analysis with Salesman...');
  await page.goto('http://localhost:8069/web#action=pbi_sales_dashboards.action_pbi_sales_mail_dashboard_sman', { waitUntil: 'networkidle2' });

  await page.waitForSelector('.pbi-sales-mail-sman-dashboard', { timeout: 30000 });

  // Wait for initial select options
  await page.waitForFunction(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    return s && s.options.length > 0;
  });

  // Select Year 2025
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    s.value = '2025';
    s.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);

  // Select Month 9 (September)
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[1];
    s.value = '9';
    s.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200);

  await new Promise(r => setTimeout(r, 2000));

  // Let's inspect the KPI elements and controls
  const info = await page.evaluate(() => {
    const topBar = document.querySelector('.pbi-sales-mail-sman-dashboard .controls-bar');
    const header = document.querySelector('.pbi-sales-mail-sman-dashboard header') || document.querySelector('.pbi-sales-dashboard-header') || document.querySelector('.controls-bar');
    const kpiRows = Array.from(document.querySelectorAll('.pbi-kpi-row'));
    const kpiWrap = document.querySelector('.pbi-kpi-container') || document.querySelector('.kpi-section');
    return {
      topBar: !!topBar,
      kpiRowsCount: kpiRows.length,
      kpiRowClasses: kpiRows.map(r => r.className),
      bodyClasses: Array.from(document.querySelectorAll('.pbi-sales-mail-sman-dashboard > *')).map(e => e.className)
    };
  });
  console.log('DOM info:', JSON.stringify(info, null, 2));

  // Let's see if we can capture the top KPI section
  // If the dashboard has controls-bar + any top cards or page 1 KPI cards:
  const controlsBar = await page.$('.controls-bar');
  const firstPage = (await page.$$('.pbi-page'))[0];
  
  // Also check for any header or KPI container
  const outputDir = '/Users/saravanan/Projects/cloud/docs/images/comparison';
  
  // Let's check if there is a header or if page 1 has the summary
  const headerElem = await page.$('.controls-bar');
  if (headerElem) {
    await headerElem.screenshot({ path: path.join(outputDir, '00_header_controls.png') });
  }

  // Let's check if there is a specific KPI element or create a focused high-res screenshot
  const page01Elem = (await page.$$('.pbi-page'))[0];
  if (page01Elem) {
    // Also check if there's a card grid inside page 1 representing the primary KPIs
    await page01Elem.screenshot({ path: path.join(outputDir, '00_kpis.png') });
    console.log('Captured fresh 00_kpis.png from Page 1 (Top Level KPIs & Matrices)');
  }

  await browser.close();
  console.log('Done.');
}

run().catch(console.error);
