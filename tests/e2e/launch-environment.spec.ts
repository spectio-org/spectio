import { test, expect } from '@playwright/test';
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { isLocal, resolveTarget } from './base-url';

// The launch smoke on a defined environment (FU-P3-86g; ui-spec §4.8.1 "At Launch" and "Run
// detail"): New environment in Launch's dialog, saved and checked, then a launch with it, whose run
// page names it. Against a real `spectio serve` (a local-mode one is enough):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test launch-environment.spec.ts --project desktop
// It deletes the environment and the catalog entry it made; the runs stay under the server's runs root.

const target = resolveTarget(process.env);
test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

const PIPELINE = join(__dirname, '..', 'pipelines', 'synthetic', 'nextflow');

test('define an environment from Launch, launch with it, and read it on the run', async ({ page, request }) => {
  const name = `e2e-${Date.now().toString(36)}`;
  try {
    await page.goto('/launch');
    const add = page.getByRole('button', { name: 'New environment' });
    await add.click();
    const dialog = page.getByRole('dialog', { name: 'New environment' });
    await expect(dialog.getByLabel('Name')).toBeFocused();
    await page.keyboard.type(name);
    await dialog.getByLabel('CPUs at most').fill('1');
    await dialog.getByRole('button', { name: 'Save and choose it' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('radio', { name: `${name}, Local` })).toBeChecked();

    await page.getByRole('textbox', { name: /^Pipeline/ }).fill(PIPELINE);
    await page.getByRole('button', { name: 'Load' }).click();
    await expect(page.getByText('Loaded', { exact: true })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Where it runs' })).toContainText(/at most 1 CPU(?!s)/);
    const posted = page.waitForRequest((r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/runs');
    await page.getByRole('button', { name: 'Launch' }).last().click();
    expect((await posted).postDataJSON()).toMatchObject({ environment: name });

    await expect(page).toHaveURL(/\/runs\/run_/);
    const fact = page.locator('dt', { hasText: /^Environment$/ }).locator('xpath=following-sibling::dd[1]');
    await expect(fact).toContainText(`${name} · Local`);
    await expect(fact).toContainText(/at most 1 CPU(?!s)/);
  } finally {
    const item = await request.get(`/api/v1/environments/${name}`);
    if (item.ok()) {
      const removed = await request.delete(`/api/v1/environments/${name}`, {
        headers: { Origin: new URL(target.url).origin, 'If-Match': item.headers()['etag'] },
      });
      expect(removed.status()).toBe(204);
    }
  }
});

// The launch smoke from a catalog entry (FU-P3-87e; ui-spec §4.7.1 "At Launch"): the entry chosen in
// the picker only fills the form, Load inspects it, and Launch sends its location and engine.
test('launch from a catalog entry', async ({ page, request }) => {
  const name = `e2e-${Date.now().toString(36)}`;
  const origin = new URL(target.url).origin;
  const made = await request.post('/api/v1/catalog', {
    headers: { Origin: origin },
    data: { name, label: null, engine: 'nextflow', location: PIPELINE, revision: null, profile: null, params_file: null },
  });
  expect(made.status()).toBe(201);
  try {
    await page.goto('/launch');
    await page.getByRole('combobox', { name: 'From your catalog' }).selectOption(name);
    await expect(page.getByRole('textbox', { name: /^Pipeline/ })).toHaveValue(PIPELINE);
    await expect(page.getByText(`From the catalog: ${name}`)).toBeVisible();
    await page.getByRole('button', { name: 'Load' }).click();
    await expect(page.getByText('Loaded', { exact: true })).toBeVisible();
    await expect(page.getByText(`In your catalog as ${name}`)).toBeVisible();
    const posted = page.waitForRequest((r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/runs');
    await page.getByRole('button', { name: 'Launch' }).last().click();
    expect((await posted).postDataJSON()).toMatchObject({ workflow: { location: PIPELINE, engine: 'nextflow' } });
    await expect(page).toHaveURL(/\/runs\/run_/);
  } finally {
    const removed = await request.delete(`/api/v1/catalog/${name}`, { headers: { Origin: origin, 'If-Match': (await made.json()).etag } });
    expect(removed.status()).toBe(204);
  }
});

// FU-P3-121 (login1 retest h): an extra config file Launch would refuse (group-writable) is said in
// "Before Launch" first, and checked again when the window comes back; then a pointer click (the
// mouse at the aside button's centre, not Enter or a DOM click) on the aside's Launch sends it.
// It writes a file in the server's home: this machine's server only (SEC-P3FU86F-01).
test('an extra config file Launch would refuse is said before Launch; a pointer click on the aside Launch sends it', async ({ page }) => {
  test.skip(!isLocal(target.url), "writes a file in the server's home");
  const dir = mkdtempSync(join(homedir(), 'spectio-e2e-'));
  const file = join(dir, 'extra.config');
  writeFileSync(file, 'process.cpus = 1\n');
  chmodSync(file, 0o664);
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/launch');
    await page.getByRole('textbox', { name: /^Pipeline/ }).fill(PIPELINE);
    await page.getByRole('button', { name: 'Load' }).click();
    await expect(page.getByText('Loaded', { exact: true })).toBeVisible();
    await page.getByRole('region', { name: 'Where it runs' }).getByRole('button', { name: /^Extra config file/ }).click();
    await page.getByRole('textbox', { name: 'Extra config file (optional)' }).fill(file);
    const before = page.locator('#launch-missing');
    await expect(before.getByRole('link', { name: 'Fix Extra config file: the file is writable by group or others' })).toBeVisible();
    await expect(before).not.toContainText('Nothing is missing');

    chmodSync(file, 0o600); // as `chmod go-w` in a terminal, then back to the browser
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(before).toContainText('Nothing is missing');

    const aside = page.getByRole('complementary', { name: 'Launch' }).getByRole('button', { name: 'Launch' });
    await aside.scrollIntoViewIfNeeded();
    const box = (await aside.boundingBox())!;
    const posted = page.waitForRequest((r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/v1/runs');
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    expect((await posted).postDataJSON()).toMatchObject({ config_file: file });
    await expect(page).toHaveURL(/\/runs\/run_/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
