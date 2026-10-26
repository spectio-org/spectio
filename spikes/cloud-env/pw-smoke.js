// Spike D2: Playwright + the pre-installed Chromium. Opens about:blank, a local page and one HTTPS page
// through the agent proxy, and prints versions and timings. Usage: node pw-smoke.js <screenshot.png>
const { chromium } = require('playwright');
(async () => {
  const t0 = Date.now();
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ proxy });
  const t1 = Date.now();
  const page = await browser.newPage({ viewport: { width: 800, height: 400 } });
  await page.goto('about:blank');
  await page.setContent('<h1 style="font-family:sans-serif">Spectio D2 spike</h1><p>Playwright + Chromium in a cloud session</p>');
  await page.screenshot({ path: process.argv[2] || 'pw.png' });
  let remote;
  try {
    const r = await page.goto('https://example.com/', { timeout: 20000 });
    remote = `example.com status=${r.status()} title="${await page.title()}"`;
  } catch (e) { remote = `example.com failed: ${e.message.split('\n')[0]}`; }
  console.log(`playwright ${require('playwright/package.json').version}`);
  console.log(`chromium ${browser.version()}`);
  console.log(`launch ${t1 - t0} ms, total ${Date.now() - t0} ms`);
  console.log(remote);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
