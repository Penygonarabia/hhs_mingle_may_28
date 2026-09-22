const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function inspectError() {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));

  await page.goto('https://staging-hhsv3.cieloapps.com/web/login', { waitUntil: 'domcontentloaded' });
  await page.type('input[name="login"]', 'admin');
  await page.type('input[name="password"]', 'Digitalhhs@#123');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => window.location.pathname.startsWith('/web') && !window.location.pathname.includes('/login'), { timeout: 30000 });
  await sleep(2000);

  await page.evaluate(() => { window.location.hash = '#menu_id=1370&action=1820'; });
  await page.waitForSelector('.pbi-page', { timeout: 45000 });
  await sleep(6000);

  // Check if any error dialogs, modals, alerts, or notification toasts are present
  const errorInfo = await page.evaluate(() => {
    const dialogs = Array.from(document.querySelectorAll('.modal, .o_dialog, .o_notification, .o_error_dialog, .alert, .pbi-error')).map(d => ({
      className: d.className,
      text: d.innerText
    }));

    const errorTexts = Array.from(document.querySelectorAll('*')).filter(el => {
      const t = el.innerText || '';
      return (t.includes('Error') || t.includes('Traceback') || t.includes('500') || t.includes('Failed to load') || t.includes('Exception')) && el.children.length === 0;
    }).map(el => ({
      tagName: el.tagName,
      className: el.className,
      text: el.innerText
    }));

    const page0Text = document.querySelector('.pbi-page')?.innerText || '';

    return { dialogs, errorTexts: errorTexts.slice(0, 20), page0Text: page0Text.slice(0, 500) };
  });

  console.log('Error info found:', JSON.stringify(errorInfo, null, 2));

  const debugDir = '/Users/saravanan/Projects/hhs_cloud/docs/images/comparison/error_debug';
  if (!fs.existsSync(debugDir)) fs.mkdirSync(debugDir, { recursive: true });

  await page.screenshot({ path: path.join(debugDir, 'current_dashboard_view.png') });
  console.log('Saved current_dashboard_view.png');

  // Also check individual pages
  const p0 = (await page.$$('.pbi-page'))[0];
  if (p0) {
    await p0.screenshot({ path: path.join(debugDir, 'p0.png') });
    console.log('Saved p0.png');
  }

  await browser.close();
}

inspectError().catch(console.error);
