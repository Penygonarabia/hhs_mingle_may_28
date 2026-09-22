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

const sleep = ms => new Promise(r => setTimeout(r, ms));

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

  // Wait until year select options are rendered
  console.log('Waiting for filter options to load...');
  await page.waitForFunction(() => {
    const selects = document.querySelectorAll('.filter-group select');
    return selects.length >= 2 && selects[0].options.length > 0 && selects[1].options.length > 0;
  }, { timeout: 30000 });

  await sleep(1000);

  // Select Year 2025
  console.log('Selecting Year 2025...');
  const yearResponsePromise = page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200, { timeout: 30000 });
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[0];
    if (s) {
      s.value = '2025';
      s.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await yearResponsePromise;
  await sleep(1500);

  // Select Month 9 (September)
  console.log('Selecting Month 9 (September)...');
  const monthResponsePromise = page.waitForResponse(res => res.url().includes('/pbi_dashboards/sales_mail_sman/data') && res.status() === 200, { timeout: 30000 });
  await page.evaluate(() => {
    const s = document.querySelectorAll('.filter-group select')[1];
    if (s) {
      s.value = '9';
      s.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await monthResponsePromise;
  await sleep(3000);

  const outDir = '/Users/saravanan/Projects/cloud/docs/images/comparison';
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  // 1. Capture 00_kpis.png (Page 1 cards / top overview)
  const cardGrid = await page.$('.pbi-page:first-child .pbi-card-grid');
  const page1 = (await page.$$('.pbi-page'))[0];
  if (cardGrid) {
    await cardGrid.screenshot({ path: path.join(outDir, '00_kpis.png') });
    console.log('Captured 00_kpis.png');
  } else if (page1) {
    await page1.screenshot({ path: path.join(outDir, '00_kpis.png') });
    console.log('Captured 00_kpis.png');
  }

  const pages = await page.$$('.pbi-page');
  console.log(`Found ${pages.length} pages.`);

  // Function to click toggle and screenshot page
  async function captureTab(pageIndex, buttonText, outName) {
    const p = (await page.$$('.pbi-page'))[pageIndex];
    if (!p) return;
    
    // Find and click the toggle button
    const clicked = await page.evaluate((pIdx, bTxt) => {
      const pEl = document.querySelectorAll('.pbi-page')[pIdx];
      if (!pEl) return false;
      const btns = Array.from(pEl.querySelectorAll('.toggle-btn, button'));
      const target = btns.find(b => b.textContent.trim().toLowerCase().includes(bTxt.toLowerCase()));
      if (target) {
        target.click();
        return true;
      }
      return false;
    }, pageIndex, buttonText);

    await sleep(600);
    const refreshedP = (await page.$$('.pbi-page'))[pageIndex];
    if (refreshedP) {
      await refreshedP.screenshot({ path: path.join(outDir, outName) });
      console.log(`Captured ${outName} (button: ${buttonText})`);
    }
  }

  // Direct page captures
  const singlePages = [
    { idx: 0, file: 'page_01.png' },
    { idx: 1, file: 'page_02.png' },
    { idx: 2, file: 'page_03.png' },
    { idx: 5, file: 'page_06.png' },
    { idx: 6, file: 'page_07.png' },
    { idx: 7, file: 'page_08.png' },
    { idx: 8, file: 'page_09.png' },
    { idx: 9, file: 'page_10.png' },
    { idx: 10, file: 'page_11.png' },
    { idx: 11, file: 'page_12.png' },
    { idx: 16, file: 'page_17.png' },
  ];

  for (const item of singlePages) {
    const pEl = (await page.$$('.pbi-page'))[item.idx];
    if (pEl) {
      await pEl.screenshot({ path: path.join(outDir, item.file) });
      console.log(`Captured ${item.file}`);
    }
  }

  // Multi-tab captures:
  // Page 4: Q1, Q2, Q3
  await captureTab(3, 'Q1', 'page_04_tab_Q1.png');
  await captureTab(3, 'Q2', 'page_04_tab_Q2.png');
  await captureTab(3, 'Q3', 'page_04_tab_Q3.png');

  // Page 5: Q1, Q2, Q3
  await captureTab(4, 'Q1', 'page_05_tab_Q1.png');
  await captureTab(4, 'Q2', 'page_05_tab_Q2.png');
  await captureTab(4, 'Q3', 'page_05_tab_Q3.png');

  // Page 13: Dealers, Projects
  await captureTab(12, 'Dealer', 'page_13_tab_Dealers.png');
  await captureTab(12, 'Project', 'page_13_tab_Projects.png');

  // Page 14: Dealers, Projects
  await captureTab(13, 'Dealer', 'page_14_tab_Dealers.png');
  await captureTab(13, 'Project', 'page_14_tab_Projects.png');

  // Page 15: Western, Riyadh, Eastern, Qassim
  await captureTab(14, 'West', 'page_15_tab_Western_Region.png');
  await captureTab(14, 'Riyadh', 'page_15_tab_Riyadh_Region.png');
  await captureTab(14, 'East', 'page_15_tab_Eastern_Region.png');
  await captureTab(14, 'Qassim', 'page_15_tab_Qassim_Region.png');

  // Page 16: Western, Riyadh, Eastern, Qassim
  await captureTab(15, 'West', 'page_16_tab_Western_Region.png');
  await captureTab(15, 'Riyadh', 'page_16_tab_Riyadh_Region.png');
  await captureTab(15, 'East', 'page_16_tab_Eastern_Region.png');
  await captureTab(15, 'Qassim', 'page_16_tab_Qassim_Region.png');

  await browser.close();
  console.log('All screenshots captured successfully!');
}

run().catch(console.error);
