const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });

  await page.goto('https://staging-hhsv3.cieloapps.com/web/login', { waitUntil: 'domcontentloaded' });
  await page.type('input[name="login"]', 'admin');
  await page.type('input[name="password"]', 'Digitalhhs@#123');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => window.location.pathname.startsWith('/web') && !window.location.pathname.includes('/login'), { timeout: 30000 });
  await sleep(2000);

  await page.evaluate(() => { window.location.hash = '#menu_id=1370&action=1820'; });
  await page.waitForSelector('.pbi-page', { timeout: 45000 });
  await sleep(3000);

  // Set Year 2025 and Month 9
  console.log('Changing Year to 2025...');
  await page.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('.filter-select'));
    for (const s of selects) {
      if (Array.from(s.options).some(o => o.value === '2025')) {
        s.value = '2025';
        s.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  });
  await sleep(3000);

  console.log('Changing Month to 9 (September)...');
  await page.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('.filter-select'));
    for (const s of selects) {
      if (Array.from(s.options).some(o => o.value === '9')) {
        s.value = '9';
        s.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  });
  await sleep(4000);

  const cardTexts = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('.pbi-page:first-child .pbi-card')).map(c => c.innerText.trim());
    const titles = Array.from(document.querySelectorAll('.pbi-page h2, .pbi-page h3, .pbi-page .pbi-card-title')).map(t => t.innerText.trim());
    return { cards, titles };
  });

  console.log('Card Texts after 2025 & Sep:');
  console.log(JSON.stringify(cardTexts, null, 2));

  await browser.close();
}

main().catch(console.error);
