const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const TARGET_DIRS = [
  '/Users/saravanan/Projects/hhs_cloud/docs/images/comparison',
  '/Users/saravanan/Projects/cloud/docs/images/comparison'
];

function saveScreenshot(sourceBuffer, filename) {
  for (const dir of TARGET_DIRS) {
    if (fs.existsSync(dir)) {
      const dest = path.join(dir, filename);
      fs.writeFileSync(dest, sourceBuffer);
      console.log(`Saved ${filename} to ${dest}`);
    }
  }
}

async function run() {
  console.log('Launching browser for Staging Dashboard screenshot capture...');
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });

  console.log('Navigating to login page...');
  await page.goto('https://staging-hhsv3.cieloapps.com/web/login', { waitUntil: 'domcontentloaded' });

  const loginInput = await page.$('input[name="login"]');
  if (loginInput) {
    console.log('Entering credentials...');
    await page.type('input[name="login"]', 'admin');
    await page.type('input[name="password"]', 'Digitalhhs@#123');
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => window.location.pathname.startsWith('/web') && !window.location.pathname.includes('/login'), { timeout: 30000 });
    console.log('Logged in successfully!');
  }

  await sleep(2000);

  console.log('Navigating to dashboard target URL: https://staging-hhsv3.cieloapps.com/web#menu_id=1370&action=1820');
  await page.evaluate(() => {
    window.location.hash = '#menu_id=1370&action=1820';
  });

  console.log('Waiting for .pbi-page elements...');
  await page.waitForSelector('.pbi-page', { timeout: 45000 });
  await sleep(3000);

  // Set filter Year: 2025, Month: 9 (September)
  console.log('Setting Year to 2025 and Month to 9 (September)...');
  await page.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('.filter-group select, .filter-select'));
    for (const sel of selects) {
      if (Array.from(sel.options).some(o => o.value === '2025')) {
        sel.value = '2025';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  });

  await sleep(2000);

  await page.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('.filter-group select, .filter-select'));
    for (const sel of selects) {
      if (Array.from(sel.options).some(o => o.value === '9' && o.text.includes('September'))) {
        sel.value = '9';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  });

  console.log('Waiting for charts and data to settle...');
  await sleep(6000);

  for (const dir of TARGET_DIRS) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  // 1. Capture KPI overview / 00_kpis.png
  console.log('Capturing KPI overview...');
  const kpiEl = await page.$('.pbi-page:first-child .pbi-card-grid') || await page.$('.pbi-kpi-row') || (await page.$$('.pbi-page'))[0];
  if (kpiEl) {
    const kpiBuf = await kpiEl.screenshot();
    saveScreenshot(kpiBuf, '00_kpis.png');
  }

  const pages = await page.$$('.pbi-page');
  console.log(`Found ${pages.length} dashboard pages.`);

  // Function to click tab and take screenshot of page
  async function captureTab(pageIndex, buttonKeywords, outName) {
    const p = (await page.$$('.pbi-page'))[pageIndex];
    if (!p) {
      console.warn(`Page index ${pageIndex} not found!`);
      return;
    }

    const clicked = await page.evaluate((pIdx, keywords) => {
      const pEl = document.querySelectorAll('.pbi-page')[pIdx];
      if (!pEl) return false;
      const btns = Array.from(pEl.querySelectorAll('button, .toggle-btn, .btn, .pbi-tab'));
      for (const kw of keywords) {
        const target = btns.find(b => b.innerText.trim().toLowerCase().includes(kw.toLowerCase()));
        if (target) {
          target.click();
          return true;
        }
      }
      return false;
    }, pageIndex, Array.isArray(buttonKeywords) ? buttonKeywords : [buttonKeywords]);

    await sleep(800);
    const refreshedP = (await page.$$('.pbi-page'))[pageIndex];
    if (refreshedP) {
      const buf = await refreshedP.screenshot();
      saveScreenshot(buf, outName);
    }
  }

  // Single page captures
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
    { idx: 16, file: 'page_17.png' }
  ];

  for (const item of singlePages) {
    const pEl = (await page.$$('.pbi-page'))[item.idx];
    if (pEl) {
      const buf = await pEl.screenshot();
      saveScreenshot(buf, item.file);
    }
  }

  // Multi-tab captures:
  // Page 4: Q1, Q2, Q3 (Index 3)
  console.log('Capturing Chart 4 tabs...');
  await captureTab(3, ['Q1'], 'page_04_tab_Q1.png');
  await captureTab(3, ['Q2'], 'page_04_tab_Q2.png');
  await captureTab(3, ['Q3'], 'page_04_tab_Q3.png');

  // Page 5: Q1, Q2, Q3 (Index 4)
  console.log('Capturing Chart 5 tabs...');
  await captureTab(4, ['Q1'], 'page_05_tab_Q1.png');
  await captureTab(4, ['Q2'], 'page_05_tab_Q2.png');
  await captureTab(4, ['Q3'], 'page_05_tab_Q3.png');

  // Page 13: Dealers, Projects (Index 12)
  console.log('Capturing Chart 13 tabs...');
  await captureTab(12, ['Dealer'], 'page_13_tab_Dealers.png');
  await captureTab(12, ['Project'], 'page_13_tab_Projects.png');

  // Page 14: Dealers, Projects (Index 13)
  console.log('Capturing Chart 14 tabs...');
  await captureTab(13, ['Dealer'], 'page_14_tab_Dealers.png');
  await captureTab(13, ['Project'], 'page_14_tab_Projects.png');

  // Page 15: Western, Riyadh, Eastern, Qassim (Index 14)
  console.log('Capturing Chart 15 tabs...');
  await captureTab(14, ['West'], 'page_15_tab_Western_Region.png');
  await captureTab(14, ['Riyadh'], 'page_15_tab_Riyadh_Region.png');
  await captureTab(14, ['East'], 'page_15_tab_Eastern_Region.png');
  await captureTab(14, ['Qassim'], 'page_15_tab_Qassim_Region.png');

  // Page 16: Western, Riyadh, Eastern, Qassim (Index 15)
  console.log('Capturing Chart 16 tabs...');
  await captureTab(15, ['West'], 'page_16_tab_Western_Region.png');
  await captureTab(15, ['Riyadh'], 'page_16_tab_Riyadh_Region.png');
  await captureTab(15, ['East'], 'page_16_tab_Eastern_Region.png');
  await captureTab(15, ['Qassim'], 'page_16_tab_Qassim_Region.png');

  await browser.close();
  console.log('All screenshots captured and saved successfully!');
}

run().catch(err => {
  console.error('Error during screenshot capture:', err);
  process.exit(1);
});
