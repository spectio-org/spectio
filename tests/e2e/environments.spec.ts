import { test, expect } from '@playwright/test';
import { isLocal, resolveTarget } from './base-url';

// The Environments pages by keyboard alone (FU-P3-86f; ui-spec §4.8.1): create, edit, make
// default, delete, against a real `spectio serve` (a local-mode one is enough):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test environments.spec.ts --project desktop
// It writes ~/.spectio/environments.toml of that server's data directory, so it runs against this
// machine only, and afterAll puts back what it changed: its environment deleted, the default restored
// (SEC-P3FU86F-01).

const target = resolveTarget(process.env);
test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(!target.serveStatic && !isLocal(target.url), 'writes the server\'s environments file: a local server only');

const name = `e2e-${Date.now().toString(36)}`;
let defaultBefore: string | undefined;

test.beforeAll(async ({ request }) => {
  const list = await request.get('/api/v1/environments');
  expect(list.ok()).toBe(true);
  defaultBefore = (await list.json()).default;
});

test.afterAll(async ({ request }) => {
  const headers = { Origin: new URL(target.url).origin };
  const item = await request.get(`/api/v1/environments/${name}`);
  if (item.ok()) {
    const removed = await request.delete(`/api/v1/environments/${name}`, { headers: { ...headers, 'If-Match': item.headers()['etag'] } });
    expect(removed.status()).toBe(204);
  }
  const now = (await (await request.get('/api/v1/environments')).json()).default;
  if (defaultBefore && now !== defaultBefore) {
    const restored = await request.post(`/api/v1/environments/${defaultBefore}:make-default`, { headers });
    expect(restored.ok()).toBe(true);
  }
});

test('create, edit, make default and delete an environment with the keyboard', async ({ page }) => {
  const heading = page.getByRole('heading', { name, exact: true });
  await page.goto('/environments');

  await page.getByRole('link', { name: 'New environment' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/environments\/new$/);
  await page.getByLabel('Name').focus();
  await page.keyboard.type(name);
  await page.keyboard.press('Tab'); // Label
  await page.keyboard.press('Tab'); // the first field of the executor's values
  await page.keyboard.type('2');
  await page.getByRole('button', { name: 'Save' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/environments$/);
  await expect(heading).toBeFocused();
  await expect(page.getByText(`Saved ${name}`)).toBeAttached();

  await page.getByRole('link', { name: `Edit ${name}` }).focus();
  await page.keyboard.press('Enter');
  await page.getByLabel('Label (optional)').focus();
  await page.keyboard.type(`Made by ${name}`);
  await page.keyboard.press('Enter'); // submits the form
  const labelled = page.getByRole('heading', { name: `Made by ${name}` });
  await expect(labelled).toBeFocused();

  await page.getByRole('button', { name: `Make default ${name}` }).focus();
  await page.keyboard.press('Enter');
  await expect(labelled).toBeFocused();
  await expect(page.getByText(`${name} is now the default`)).toBeAttached();

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
