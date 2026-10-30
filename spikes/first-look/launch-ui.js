// Spike first-look, part 2: launch two dummy runs from the "New run" form and screenshot them.
//   node spikes/first-look/launch-ui.js [port] [outdir]
// Run 1 (3 samples) succeeds: launch-form.png, live-run.png (while it runs), run-done.png.
// Run 2 (2 samples, "Fail a task") fails: run-failed.png. Exits 1 if a run ends in another state.
const { chromium } = require('playwright');

const port = process.argv[2] || '8765';
const out = process.argv[3] || `${__dirname}/shots`;
const base = `http://127.0.0.1:${port}`;

async function launch(page, samples, fail) {
  await page.goto(base + '/');
  await page.fill('#f-samples', String(samples));
  if (fail) await page.check('#f-fail');
  await Promise.all([page.waitForURL(/\/runs\/run_/), page.click('button[type=submit]')]);
  return page.url();
}

async function waitState(page, url, states, timeoutS) {
  for (let i = 0; i < timeoutS; i++) {
    await page.goto(url);
    const state = (await page.textContent('.head .st')).trim().split(' ').pop().toLowerCase();
    if (states.includes(state)) return state;
    await page.waitForTimeout(1000);
  }
  throw new Error(`${url}: not in ${states} after ${timeoutS} s`);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  let ok = true;

  await page.goto(base + '/');
  await page.fill('#f-samples', '3');
  await page.screenshot({ path: `${out}/launch-form.png`, fullPage: true });

  const run1 = await launch(page, 3, false);
  console.log('launched', run1);
  // Live: wait until some task has finished and the run is still running.
  for (let i = 0; i < 120; i++) {
    await page.goto(run1);
    const head = await page.textContent('.head');
    if (/Running/.test(head) && !/ 0 \/ \d+ tasks done/.test(head)) break;
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: `${out}/live-run.png`, fullPage: true });
  const s1 = await waitState(page, run1, ['succeeded', 'failed'], 180);
  console.log('run 1', s1);
  ok = ok && s1 === 'succeeded';
  await page.screenshot({ path: `${out}/run-done.png`, fullPage: true });

  const run2 = await launch(page, 2, true);
  console.log('launched', run2);
  const s2 = await waitState(page, run2, ['succeeded', 'failed'], 180);
  console.log('run 2', s2);
  ok = ok && s2 === 'failed';
  await page.screenshot({ path: `${out}/run-failed.png`, fullPage: true });

  await page.goto(base + '/');
  await page.screenshot({ path: `${out}/runs-local.png`, fullPage: true });
  await browser.close();
  process.exit(ok ? 0 : 1);
})();
