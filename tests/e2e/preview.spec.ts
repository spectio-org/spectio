import { test, expect, type Page } from '@playwright/test';
import { resolveTarget } from './base-url';

// The file preview's image (FU-P3-85c; api §5.3 tests; ui-spec §4.4.1; dev-env §15.3 req. 14),
// against a real `spectio serve` with the seeded run, whose results hold
// tests/fixtures/results/hostile_image.svg (tests/e2e/seed_stages.py):
//   bash tests/e2e/serve-local.sh --port 8765 --seed-stages &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 SPECTIO_E2E_SEEDED=1 npx playwright test preview.spec.ts
// The SVG has a <script>, an outside <image href> and a foreignObject <img onerror>: in an <img>
// none of them may run or fetch; a top-level navigation to the same URL must download the file.
// The seeded logs/big.log (200 KiB) checks that Load more keeps focus in a real browser.

const target = resolveTarget(process.env);
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const IS_SEEDED = process.env.SPECTIO_E2E_SEEDED === '1';
const SVG = 'hostile/hostile_image.svg';
const RAW = `/api/v1/runs/${SEEDED}/results/raw/hostile/hostile_image.svg?as=image`;

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(!IS_SEEDED, 'needs the seeded run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1');

/** Every request a script of the SVG could make: outside, or back to the API with a marker. */
function watch(page: Page) {
  const seen: string[] = [];
  page.context().on('request', (r) => {
    const url = r.url();
    if (url.includes('example.com') || url.includes('svg-script-ran') || url.includes('svg-onerror-ran')) seen.push(url);
  });
  return seen;
}

test('an SVG in the preview loads in an <img>, runs nothing and fetches nothing', async ({ page }) => {
  const seen = watch(page);
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent(SVG)}`);
  const img = page.getByRole('img', { name: 'hostile_image.svg' });
  await expect(img).toBeVisible();
  await expect(img).toHaveAttribute('src', RAW);
  // decoded: the rectangle drew, at its own size
  await expect.poll(() => img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth)).toBe(120);
  await expect(page.getByText('120 × 60 px')).toBeVisible();
  await page.waitForTimeout(500); // let a script that could run, run
  expect(seen).toEqual([]);
  await expect(page.getByText('This image could not be shown here')).toHaveCount(0);
});

test('the image URL, once loaded in an <img>, downloads on a top-level navigation, with no SVG document', async ({ page }) => {
  const seen = watch(page);
  // first the <img>: its inline image/svg+xml answer is now in this context's cache
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent(SVG)}`);
  const img = page.getByRole('img', { name: 'hostile_image.svg' });
  await expect.poll(() => img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth)).toBe(120);
  // then the same URL as a document, from that same page
  const download = page.waitForEvent('download');
  await page.goto(RAW).catch(() => {}); // a download aborts the navigation
  const file = await download;
  expect(file.suggestedFilename()).toBe('hostile_image.svg');
  await page.waitForTimeout(500);
  expect(seen).toEqual([]);
  // the page is still the run's: no SVG document replaced it
  expect(await page.evaluate(() => document.documentElement.namespaceURI)).toBe('http://www.w3.org/1999/xhtml');
  expect(await page.evaluate(() => document.documentElement.getAttribute('data-ran'))).toBeNull();
});

test('Load more keeps focus while it loads and after', async ({ page }) => {
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent('logs/big.log')}`);
  const more = page.getByRole('button', { name: 'Load more' });
  await more.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('128 KiB shown', { exact: true })).toBeVisible();
  await expect(more).toBeFocused();
  await page.keyboard.press('Enter'); // focus still on it: the keyboard loads the next read
  await expect(page.getByText('192 KiB shown', { exact: true })).toBeVisible();
  await expect(more).toBeFocused();
});

test('a TSV preview is an AG Grid under the CSP: no violation, sorts and moves from the keyboard', async ({ page }) => {
  // AG Grid writes its theme in <style> elements (style-src 'unsafe-inline' already allows them);
  // its icon set is left out (data: images, refused by img-src 'self') and it compiles no code.
  await page.addInitScript(() => {
    const seen: string[] = [];
    (window as unknown as { cspSeen: string[] }).cspSeen = seen;
    document.addEventListener('securitypolicyviolation', (e) => seen.push(`${e.violatedDirective} ${e.blockedURI}`));
  });
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent('multiqc/align_mqc.tsv')}`);
  const grid = page.getByRole('region', { name: 'align_mqc.tsv, table' }).getByRole('grid', { name: 'align_mqc.tsv' });
  await expect(grid).toBeVisible();
  const aligned = grid.getByRole('columnheader', { name: 'Aligned' });
  await aligned.focus();
  await page.keyboard.press('Enter');
  await expect(aligned).toHaveAttribute('aria-sort', 'ascending');
  await page.keyboard.press('ArrowDown'); // the filter row
  await page.keyboard.press('ArrowDown'); // the first row: the lowest Aligned
  await expect(page.locator(':focus')).toHaveAttribute('role', 'gridcell');
  await expect(page.locator(':focus')).toHaveText('89.7');
  await grid.getByRole('textbox', { name: 'Sample Filter Input' }).fill('S01');
  await expect(grid.getByRole('gridcell', { name: 'S02' })).toHaveCount(0);
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => (window as unknown as { cspSeen: string[] }).cspSeen)).toEqual([]);
  expect(requests.filter((u) => !u.startsWith(new URL(page.url()).origin))).toEqual([]); // no font, licence or telemetry call
});
