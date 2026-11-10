import { test, expect } from '@playwright/test';
import { resolveTarget } from './base-url';

// The OME-TIFF WebGL viewer under the server's CSP (FU-P3-102e; dev-env §15.3 req. 19 Tests;
// ui-spec §4.4.1), against a real `spectio serve` with the seeded run, whose results hold
// imaging/cells.ome.tif (2 channels, 3 Z planes; tests/e2e/seed_stages.py):
//   bash tests/e2e/serve-local.sh --port 8765 --seed-stages &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 SPECTIO_E2E_SEEDED=1 npx playwright test viewer.spec.ts
// Viv, deck.gl and luma.gl must run with 'wasm-unsafe-eval' and worker-src 'self' only: no
// 'unsafe-eval', no blob: worker. Every `securitypolicyviolation` is recorded; none may fire.

const target = resolveTarget(process.env);
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const FILE = 'imaging/cells.ome.tif';

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(process.env.SPECTIO_E2E_SEEDED !== '1', 'needs the seeded run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1');

test('the OME-TIFF viewer draws under the CSP, with no violation, reading only its raw URL', async ({ page, baseURL }) => {
  await page.addInitScript(() => {
    const seen: string[] = [];
    (window as unknown as { cspSeen: string[] }).cspSeen = seen;
    document.addEventListener('securitypolicyviolation', (e) => seen.push(`${e.violatedDirective} ${e.blockedURI}`));
  });
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
