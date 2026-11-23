import { test, expect } from '@playwright/test';
import { resolveTarget } from './base-url';

// The OME-TIFF WebGL viewer under the server's CSP (FU-P3-102e; dev-env §15.3 req. 19 Tests;
// ui-spec §4.4.1), against a real `spectio serve` with the seeded run, whose results hold
// imaging/cells.ome.tif (2 channels, 3 Z planes; tests/e2e/seed_stages.py):
//   bash tests/e2e/serve-local.sh --port 8765 --seed-stages &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 SPECTIO_E2E_SEEDED=1 npx playwright test viewer.spec.ts
// Viv, deck.gl and luma.gl must run with 'wasm-unsafe-eval' and worker-src 'self' only: no
// 'unsafe-eval', no blob: worker. Every `securitypolicyviolation` and every `URL.createObjectURL`
// call is recorded; none may happen. Projects desktop (Chromium), firefox and webkit. The OME-Zarr
// case (FU-P3-102g) reads imaging/cells.ome.zarr key by key through the raw route with as=zarr,
// a raw level and a zlib level (Blosc and LZ4 are refused: numcodecs needs 'unsafe-eval', inbox #135).
// The plain-TIFF case (RC1 P-06) reads imaging/plain.tif (one 8-bit grey plane, no OME-XML): a TIFF
// is drawn flat on a 2D canvas through the same pinned client and decoder pool, never in WebGL.

const target = resolveTarget(process.env);
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const FILE = 'imaging/cells.ome.tif';

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(process.env.SPECTIO_E2E_SEEDED !== '1', 'needs the seeded run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1');

/** Records every CSP violation and every `URL.createObjectURL` call in `window.cspSeen`. */
async function watchCsp(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    const seen: string[] = [];
    (window as unknown as { cspSeen: string[] }).cspSeen = seen;
    document.addEventListener('securitypolicyviolation', (e) => seen.push(`${e.violatedDirective} ${e.blockedURI}`));
    const make = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (obj: Blob | MediaSource) => (seen.push('createObjectURL'), make(obj));
  });
}

test('the OME-TIFF viewer draws under the CSP, with no violation, reading only its raw URL', async ({ page, baseURL }) => {
  await watchCsp(page); // no blob: URL is ever made (a blob: worker would be refused by the CSP, so fail closed: but it must not be tried)
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent(FILE)}`);
  const region = page.getByRole('region', { name: 'cells.ome.tif, image viewer' });
  await expect(region).toBeVisible();
  const status = page.locator('.sp-file-viewer [role="status"]'); // the viewer's own status line
  await expect(page.getByText('64 × 48 px · 2 channels · 3 planes · 1 time point · uint8')).toBeVisible();
  await expect(status).toHaveText('', { timeout: 15_000 }); // read, nothing stopped
  // the keys and the buttons
  const zoom = page.getByText(/^Zoom \d+ %$/);
  const before = await zoom.textContent();
  await region.focus();
  await page.keyboard.press('+');
  await expect(zoom).not.toHaveText(before!);
  await page.getByRole('button', { name: 'Fit' }).click();
  await expect(zoom).toHaveText(before!);
  await page.getByRole('slider', { name: 'Z plane' }).fill('3');
  await expect(page.getByText('3 of 3')).toBeVisible();
  await expect(status).toHaveText('', { timeout: 15_000 });
  await expect(page.getByText('Some tiles could not be read.')).toHaveCount(0);
  if (process.env.SPECTIO_E2E_SHOT) await page.screenshot({ path: process.env.SPECTIO_E2E_SHOT });
  expect(await page.evaluate(() => (window as unknown as { cspSeen: string[] }).cspSeen)).toEqual([]);
  // the file is read through the raw route only; nothing leaves the origin
  const origin = new URL(baseURL!).origin;
  expect(requests.filter((u) => !u.startsWith(origin))).toEqual([]);
  expect(requests.filter((u) => u.includes('cells.ome.tif') && !u.includes('/results/stat') && !u.includes('/results/file'))).not.toHaveLength(0);
});

test('the OME-Zarr viewer draws under the CSP, reading only keys below its folder with as=zarr', async ({ page, baseURL }) => {
  await watchCsp(page);
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent('imaging/cells.ome.zarr')}`);
  await expect(page.getByRole('region', { name: 'cells.ome.zarr, image viewer' })).toBeVisible();
  await expect(page.getByText('64 × 48 px · 2 channels · 1 plane · 1 time point · uint8')).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Show channel 1, DNA' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.locator('.sp-file-viewer [role="status"]')).toHaveText('', { timeout: 15_000 });
  await expect(page.getByText('Some tiles could not be read.')).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { cspSeen: string[] }).cspSeen)).toEqual([]);
  const origin = new URL(baseURL!).origin;
  expect(requests.filter((u) => !u.startsWith(origin))).toEqual([]);
  const keys = requests.filter((u) => u.includes('/results/raw/'));
  expect(keys).not.toHaveLength(0);
  for (const u of keys) expect(u).toMatch(/\/results\/raw\/imaging\/cells\.ome\.zarr\/[A-Za-z0-9_.\/-]+\?as=zarr$/);
  expect(keys.some((u) => u.includes('.zmetadata'))).toBe(false);
});

test('a plain TIFF draws flat under the CSP', async ({ page, baseURL }) => {
  await watchCsp(page);
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto(`/runs/${SEEDED}/results/file?path=${encodeURIComponent('imaging/plain.tif')}`);
  // the flat view: a canvas named for the file, its facts line, and none of the WebGL viewer's parts
  const canvas = page.getByRole('img', { name: 'plain.tif' });
  await expect(canvas).toBeVisible();
  await expect(page.getByText('64 × 48 px', { exact: true })).toBeVisible();
  await expect(page.getByText('Loading the image…')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'plain.tif, image viewer' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Fit' })).toHaveCount(0);
  await expect(page.getByText('This file has no OME metadata: shown as a TIFF.')).toHaveCount(0); // a .tif name is not an OME claim
  await expect(page.getByText('Not an image Spectio can read', { exact: false })).toHaveCount(0);
  await expect(page.getByText('This image could not be decoded.')).toHaveCount(0);
  // drawn: the canvas has the plane's size and its pixels, (4x + 2y) mod 256 in grey
  const pixels = await canvas.evaluate((el: HTMLCanvasElement) => {
    const at = (x: number, y: number) => Array.from(el.getContext('2d')!.getImageData(x, y, 1, 1).data);
    return { width: el.width, height: el.height, first: at(0, 0), last: at(63, 47) };
  });
  expect(pixels).toEqual({ width: 64, height: 48, first: [0, 0, 0, 255], last: [90, 90, 90, 255] });
  // Actual size keeps the same canvas, in a scroll region
  await page.getByRole('button', { name: 'Actual size' }).click();
  await expect(page.getByRole('region', { name: 'plain.tif, image' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'plain.tif' })).toBeVisible();
  // no CSP violation, no blob: URL (a blob: worker would be refused), nothing leaves the origin
  expect(await page.evaluate(() => (window as unknown as { cspSeen: string[] }).cspSeen)).toEqual([]);
  const origin = new URL(baseURL!).origin;
  expect(requests.filter((u) => !u.startsWith(origin))).toEqual([]);
  const reads = requests.filter((u) => u.includes('plain.tif') && !u.includes('/results/stat') && !u.includes('/results/file'));
  expect(reads).not.toHaveLength(0);
  for (const u of reads) expect(u).toMatch(/\/results\/raw\/imaging\/plain\.tif\?as=tiff$/);
});
