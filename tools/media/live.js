// Capture a page of a running Spectio (`spectio serve`), after a few steps (P1 Task 19).
//   SPECTIO_URL=http://… node tools/media/live.js <route> <width> <height> <out.png> [step…]
// $NAME in the route or a step is replaced by that environment variable; SPECTIO_THEME (light or dark) sets the
// browser's colour scheme, which the screens follow until a theme is picked.
// Steps: fill:<label>=<value> (the text or search field whose accessible name starts with <label>),
// click:<button name>, view:<visible text> (its last match, scrolled to the middle), open:<start of a folded section's button name>, top (scroll to the top), wait:<visible text>. Run through shots.py, which preloads page_text.js
// for the hygiene check.
const path = require('path');
const { chromium } = require(require.resolve('playwright', { paths: [path.resolve(__dirname, '../canvas'), process.cwd()] }));
const [,, route, W, H, out, ...raw] = process.argv;
const expand = (s) => s.replace(/\$(\w+)/g, (m, name) => process.env[name] ?? m);
const url = process.env.SPECTIO_URL.replace(/\/+$/, '') + expand(route);
const steps = raw.map(expand);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: +W, height: +H }, colorScheme: process.env.SPECTIO_THEME === 'dark' ? 'dark' : 'light' });
  await page.goto(url, { waitUntil: 'networkidle' });
  for (const step of steps) {
    const [kind, arg] = [step.slice(0, step.indexOf(':')), step.slice(step.indexOf(':') + 1)];
    if (kind === 'fill') {
      const [label, value] = [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)];
      const name = new RegExp('^' + label); // a text field, or a search field (the log search, P3-parD)
      await page.getByRole('textbox', { name }).or(page.getByRole('searchbox', { name })).fill(value);
    } else if (kind === 'click') {
      await page.getByRole('button', { name: arg, exact: true }).click();
    } else if (kind === 'open') {
      await page.getByRole('button', { name: new RegExp('^' + arg) }).click();
      await page.waitForTimeout(500); // the section's open transition, so the chevron has settled
    } else if (kind === 'view') {
      await page.getByText(arg).last().evaluate((el) => el.scrollIntoView({ block: 'center' }));
    } else if (kind === 'top') {
      await page.evaluate(() => window.scrollTo(0, 0));
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
