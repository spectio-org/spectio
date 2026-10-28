import { test, expect } from '@playwright/test';
import { boardShotPath } from './boards';
import { resolveTarget } from './base-url';

test('the home page answers, shows its main region, no script errors', async ({ page }, testInfo) => {
  const errors: Error[] = [];
  page.on('pageerror', (e) => errors.push(e));
  // Not 'load': a slow image or video of a remote target (the docs preview) must not fail a smoke test.
  const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
  expect(response?.ok()).toBe(true);
  await expect(page).toHaveTitle(/Spectio/);
  await expect(page.getByRole('main')).toBeVisible();
  // The stand-in page plays the Runs table until the product exists; another target is not that board.
  if (resolveTarget(process.env).serveStatic) {
    await page.screenshot({ path: boardShotPath('RunsTable', testInfo.project.name), fullPage: true });
  }
  expect(errors).toEqual([]);
});
