import { test, expect } from '@playwright/test';
import { resolveTarget } from './base-url';

// The Catalog pages by keyboard alone (FU-P3-87d; ui-spec §4.7.1): add, edit, delete, against a
// real `spectio serve` (a local-mode one is enough):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test catalog.spec.ts --project desktop
// It writes ~/.spectio/catalog.toml of that server's data directory and deletes what it made.
// Saving checks how the fields are written, not that the pipeline exists (api §5.6): the
// repository below is never fetched.

const target = resolveTarget(process.env);
test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

test('add, edit and delete a catalog entry with the keyboard', async ({ page, isMobile }) => {
  const name = `e2e-${Date.now().toString(36)}`;
  const heading = page.getByRole('heading', { name, exact: true });
  await page.goto('/catalog');
  await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Launch' })).toHaveAttribute('aria-current', 'page');

  await page.getByRole('link', { name: 'Add pipeline' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/catalog\/new$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Add pipeline' })).toBeFocused();
  await page.getByLabel('Name').focus();
  await page.keyboard.type(name);
  await page.getByLabel('Pipeline').focus();
  await page.keyboard.type('nf-core/rnaseq');
  await page.keyboard.press('Tab'); // Revision, shown once Pipeline reads as a repository
  await page.keyboard.type('3.27.0');
  await page.keyboard.press('Enter'); // submits the form
  await expect(page).toHaveURL(/\/catalog$/);
  await expect(heading).toBeFocused();
  await expect(page.getByText(`Saved ${name}`)).toBeAttached();

  // the phone opens the entry from its card; the desktop from its row's Edit
  await (isMobile ? heading.getByRole('link') : page.getByRole('link', { name: `Edit ${name}` })).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp(`/catalog/${name}$`));
  await page.getByLabel('Label (optional)').focus();
  await page.keyboard.type(`Made by ${name}`);
  await page.keyboard.press('Enter');
  const labelled = page.getByRole('heading', { name: `Made by ${name}` });
  await expect(labelled).toBeFocused();

  if (isMobile) {
    await labelled.getByRole('link').focus();
    await page.keyboard.press('Enter');
  }
  const del = page.getByRole('button', { name: `Delete ${name}` });
  await del.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: `Delete ${name}?` });
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(del).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', { name: `Delete ${name}` })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByText(`Deleted ${name}`)).toBeAttached();
  await expect(labelled).toHaveCount(0);
  await expect(page.locator('h2:focus, h1:focus')).toHaveCount(1);
});
