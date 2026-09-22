const puppeteer = require('puppeteer-core');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getErrorDetails() {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1200']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: 2 });

  page.on('pageerror', err => console.log('PAGE ERROR EVENT:', err.message));

  await page.goto('https://staging-hhsv3.cieloapps.com/web/login', { waitUntil: 'domcontentloaded' });
  await page.type('input[name="login"]', 'admin');
  await page.type('input[name="password"]', 'Digitalhhs@#123');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => window.location.pathname.startsWith('/web') && !window.location.pathname.includes('/login'), { timeout: 30000 });
  await sleep(2000);

  await page.evaluate(() => { window.location.hash = '#menu_id=1370&action=1820'; });
  await sleep(6000);

  // Click 'See details' inside the error dialog if present
  const details = await page.evaluate(async () => {
    const seeDetailsBtn = document.querySelector('.o_error_dialog button.btn-link, .o_error_dialog [data-bs-toggle="collapse"], .o_error_dialog details, .o_error_dialog a');
    if (seeDetailsBtn) seeDetailsBtn.click();
    
    const clipboardBtn = document.querySelector('.o_error_dialog button');
    
    const modal = document.querySelector('.o_error_dialog, .modal');
    return {
      modalText: modal ? modal.innerText : 'No modal found',
      html: modal ? modal.innerHTML : ''
    };
  });

  console.log('Error Modal Text:\n', details.modalText);
  console.log('Error Modal HTML:\n', details.html);

  await browser.close();
}

getErrorDetails().catch(console.error);
