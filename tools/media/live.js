// Capture a page of a running Spectio (`spectio serve`), after a few steps (P1 Task 19).
//   node tools/media/live.js <url> <width> <height> <out.png> [step…]
// Steps: fill:<label>=<value> (the field whose accessible name starts with <label>),
// click:<button name>, wait:<visible text>. Run through shots.py, which preloads page_text.js
// for the hygiene check.
const path = require('path');
const { chromium } = require(require.resolve('playwright', { paths: [path.resolve(__dirname, '../canvas'), process.cwd()] }));
const [,, url, W, H, out, ...steps] = process.argv;
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: +W, height: +H }, colorScheme: 'light' });
  await page.goto(url, { waitUntil: 'networkidle' });
  for (const step of steps) {
    const [kind, arg] = [step.slice(0, step.indexOf(':')), step.slice(step.indexOf(':') + 1)];
    if (kind === 'fill') {
      const [label, value] = [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)];
      await page.getByRole('textbox', { name: new RegExp('^' + label) }).fill(value);
    } else if (kind === 'click') {
      await page.getByRole('button', { name: arg, exact: true }).click();
    } else if (kind === 'wait') {
      await page.getByText(arg).first().waitFor({ timeout: 30000 });
    } else {
      throw new Error(`unknown step ${step}`);
    }
  }
  await page.screenshot({ path: out });
  await browser.close();
  console.log('ok', out);
})().catch((e) => { console.error(e); process.exit(1); });
