import { test, expect, type Page } from '@playwright/test';
import { resolveTarget } from './base-url';

// The report viewer of P1 Task 31 (dev-env §15.3 req. 14), against a real `spectio serve` with the
// seeded run, whose results hold tests/fixtures/results (tests/e2e/seed_stages.py):
//   bash tests/e2e/serve-local.sh --port 8765 --seed-stages &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 SPECTIO_E2E_SEEDED=1 npx playwright test report.spec.ts
// The MultiQC report is a real MultiQC 1.35 report of a custom content table, made on this machine
// (tests/fixtures/results/SOURCE.json). TODO(P1 Task 22): the same check with the MultiQC report
// of the nf-core/rnaseq megatest, on slurm-mini.

const target = resolveTarget(process.env);
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const IS_SEEDED = process.env.SPECTIO_E2E_SEEDED === '1';

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(!IS_SEEDED, 'needs the seeded run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1');

/** Opens the viewer on `path`; every request to example.com is recorded and answered here. */
async function open(page: Page, path: string) {
  const outside: string[] = [];
  await page.context().route('https://example.com/**', (route) => {
    outside.push(route.request().url());
    return route.fulfill({ status: 200, contentType: 'text/html', body: 'outside' });
  });
  const popups: string[] = [];
  page.context().on('page', (p) => popups.push(p.url()));
  await page.goto(`/runs/${SEEDED}/report?path=${encodeURIComponent(path)}`);
  await expect(page.getByText(`Untrusted report: ${path}`)).toBeVisible();
  await expect(page.getByText('Spectio never asks you to paste a link.', { exact: false })).toBeVisible();
  const frame = page.frameLocator('iframe[title$="sandboxed"]');
  return { frame, outside, popups };
}

test('req14: a report in the viewer cannot open windows, navigate the top page or leave', async ({ page }) => {
  const { frame, outside, popups } = await open(page, 'hostile/hostile_report.html');
  await expect(frame.getByRole('heading', { name: 'Hostile report' })).toBeVisible();
  const at = page.url();
  const out = frame.locator('#out');

  await frame.getByRole('button', { name: 'Open a window' }).click();
  await expect(out).toHaveText('blocked');
  await frame.getByRole('button', { name: 'Move the page' }).click();
  await expect(out).toHaveText('blocked');
  await frame.getByRole('button', { name: 'Call the API' }).click();
  await expect(out).toHaveText('blocked');
  await frame.getByRole('button', { name: 'Read cookies' }).click();
  await expect(out).toHaveText('blocked'); // an opaque origin: document.cookie throws
  await frame.getByRole('link', { name: 'An external link' }).click();
  await frame.getByRole('link', { name: 'A link in the frame' }).click();

  await page.waitForTimeout(500); // let a navigation that was allowed happen
  expect(page.url()).toBe(at);
  expect(popups).toEqual([]);
  expect(outside).toEqual([]);
  await expect(page.getByText('Untrusted report: hostile/hostile_report.html')).toBeVisible();
});

test('a MultiQC report renders in the viewer and cannot call the API', async ({ page }) => {
  const { frame, outside } = await open(page, 'multiqc/multiqc_report.html');
  await expect(page.getByRole('heading', { level: 1, name: 'MultiQC report' })).toBeVisible();
  // The report's scripts draw its sections and its table. MultiQC 1.35 then reads localStorage,
  // which throws in an opaque origin, so its "Loading report.." note stays and its toolbox does
  // not start (2026-11-04, inbox #100 rule 14): the viewer's "Report blank?" line points to Download.
  await expect(frame.getByRole('heading', { name: /Alignment/ }).first()).toBeVisible({ timeout: 30_000 });
  await expect(frame.getByText('S01', { exact: true }).first()).toBeVisible();
  const iframe = await page.locator('iframe[title$="sandboxed"]').elementHandle();
  const inside = await iframe!.contentFrame();
  const called = await inside!.evaluate(() =>
    fetch('/api/v1/version').then(
      () => 'reached',
      () => 'blocked',
    ),
  );
  expect(called).toBe('blocked');
  expect(await inside!.evaluate(() => window.origin)).toBe('null'); // opaque: not Spectio's origin
  expect(outside).toEqual([]);
});

test('the viewer frames its report when reached by in-app navigation (CR-P3T31-02)', async ({ page }) => {
  // A CSP is the document's: load another screen, then move to the viewer without a new document,
  // as a link of the app does (TanStack Router wraps history.pushState).
  const blocked: string[] = [];
  page.on('console', (m) => m.text().includes('frame-src') && blocked.push(m.text()));
  await page.goto(`/runs/${SEEDED}`);
  await expect(page.locator('h1').first()).toBeVisible();
  const path = 'hostile/hostile_report.html';
  await page.evaluate(
    (to) => window.history.pushState({ ...window.history.state, __TSR_index: 1 }, '', to),
    `/runs/${SEEDED}/report?path=${encodeURIComponent(path)}`,
  );
  await expect(page.getByText(`Untrusted report: ${path}`)).toBeVisible();
  const frame = page.frameLocator('iframe[title$="sandboxed"]');
  await expect(frame.getByRole('heading', { name: 'Hostile report' })).toBeVisible();
  expect(blocked).toEqual([]);
});
