import { test, expect } from '@playwright/test';
import { boardShotPath } from './boards';

test('the home page answers, shows its main region, no script errors', async ({ page }, testInfo) => {
  const errors: Error[] = [];
  page.on('pageerror', (e) => errors.push(e));
  const response = await page.goto('/');
  expect(response?.ok()).toBe(true);
  await expect(page).toHaveTitle(/Spectio/);
  await expect(page.getByRole('main')).toBeVisible();
  // The stand-in page plays the Runs table until the product exists.
  await page.screenshot({ path: boardShotPath('RunsTable', testInfo.project.name), fullPage: true });
  expect(errors).toEqual([]);
});
