// Spike first-look: screenshot the running demo (node spikes/first-look/shoot.js [port] [outdir]).
const { chromium } = require('playwright');
(async () => {
  const port = process.argv[2] || '8765';
  const out = process.argv[3] || `${__dirname}/shots`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const base = `http://127.0.0.1:${port}`;
  await page.goto(base + '/');
  await page.screenshot({ path: `${out}/runs.png`, fullPage: true });
  const links = await page.$$eval('a[href^="/runs/"]', as => as.map(a => [a.textContent, a.getAttribute('href')]));
  for (const [name, href] of links) {
    await page.goto(base + href);
    await page.screenshot({ path: `${out}/run-${name.trim()}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + '/');
  await page.screenshot({ path: `${out}/runs-phone.png`, fullPage: true });
  await browser.close();
})();
