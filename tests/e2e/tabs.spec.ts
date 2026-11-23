import { test, expect, type APIRequestContext, type Browser, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { isLocal, resolveTarget } from './base-url';
import { portOf, sessionCookie, withoutTicket } from './global-setup';

// RC1 gaps L-06, X-13, N-04 and M-06 (docs: RC1 acceptance §18): what one browser tab does, the
// other tab of the same browser shows. Two pages of one context share the cookie, so they are one
// user in two tabs; each page has its own EventSource. Run like skeleton.spec.ts (tests/e2e/serve-local.sh
// and SPECTIO_E2E_BASE_URL). The tests that launch a run need SPECTIO_E2E_ENGINES=1.

const target = resolveTarget(process.env);
const ENGINES = process.env.SPECTIO_E2E_ENGINES === '1';
const NEEDS_ENGINES = 'needs Nextflow: set SPECTIO_E2E_ENGINES=1 (CI job e2e-local)';
const NEEDS_LOCAL = 'needs the server on this machine: serve-local.sh writes the link pointer next to the specs';
const SYNTHETIC = join(__dirname, '..', 'pipelines', 'synthetic');
const LOCAL = join(__dirname, '.local');
const REPO = join(__dirname, '..', '..');
const LIVE = /^live, updated \d+ s ago$/;

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

/** POST /runs of the synthetic Nextflow pipeline; `params.scale` makes it last. */
async function launch(request: APIRequestContext, profiles: string[], params: object = {}): Promise<string> {
  const response = await request.post('/api/v1/runs', {
    headers: { Origin: new URL(target.url).origin },
    data: { workflow: { location: join(SYNTHETIC, 'nextflow'), revision: null, engine: 'nextflow' }, profiles, params },
  });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()).id;
}

/** Wait until the run's API state is one of `states`. */
async function reach(request: APIRequestContext, id: string, states: string[]) {
  await expect
    .poll(async () => (await (await request.get(`/api/v1/runs/${id}`)).json()).state, { timeout: 120_000 })
    .toMatch(new RegExp(`^(${states.join('|')})$`));
}

/** A happy run that has ended, and its name (what the list and the bell call it). */
async function endedRun(request: APIRequestContext): Promise<{ id: string; name: string }> {
  const id = await launch(request, ['test']);
  await reach(request, id, ['succeeded']);
  return { id, name: (await (await request.get(`/api/v1/runs/${id}`)).json()).name };
}

/** A browser context with no session: the cookies global-setup.ts got are not in it. */
const bare = (browser: Browser) => browser.newContext({ baseURL: target.url, storageState: { cookies: [], origins: [] } });

/** A fresh single-use ticket for the server at `target`, from `spectio login --print-link --json`
 * (as global-setup.ts gets its own). */
function newTicket(): string {
  const pointer = join(LOCAL, `${portOf(target.url)}.config`);
  const config = readFileSync(pointer, 'utf8').trim();
  const out = execFileSync('uv', ['run', '--locked', '--project', REPO, 'spectio', 'login', '--print-link', '--json'], {
    env: { ...process.env, SPECTIO_CONFIG: config },
    encoding: 'utf8',
  });
  const line = /^spectio-ticket-v1 (\{.*\})$/m.exec(out);
  if (!line) throw new Error('spectio login --print-link --json printed no ticket');
  return (JSON.parse(line[1]) as { ticket: string }).ticket;
}

/** Opens the token link in `page`, as a user does; an error never names the ticket. */
async function openLink(page: Page, ticket: string) {
  await page.goto(`/auth/link#${ticket}`).catch((error) => {
    throw withoutTicket(error, ticket);
  });
}

const bellOf = (page: Page) => page.getByRole('button', { name: /^Notifications(, \d+ unread)?$/ });

test('a run deleted in one tab leaves the list of the other', async ({ page, context, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const { id, name } = await endedRun(request);
  const other = await context.newPage();
  const list = `/runs?q=${encodeURIComponent(name)}`;
  const row = (p: Page) => p.getByRole('link', { name: `Open run ${name}` });
  await page.goto(list);
  await other.goto(list);
  await expect(row(page)).toBeVisible();
  await expect(row(other)).toBeVisible();
  await expect(other.getByText(LIVE).first()).toBeVisible(); // the second tab hears the stream

  await page.getByRole('checkbox', { name: `Select run ${name}` }).check();
  await page.getByRole('button', { name: 'Delete…' }).click();
  await page.getByRole('dialog', { name: 'Delete 1 run?' }).getByRole('button', { name: 'Delete', exact: true }).click();
  await expect(page.getByRole('status').getByText('1 run deleted')).toBeVisible();
  expect((await request.get(`/api/v1/runs/${id}`)).status()).toBe(404);

  // the next frame of the stream refetches the other tab's list: no reload
  await other.evaluate(() => ((window as unknown as { marker: number }).marker = 1));
  await expect(row(other)).toHaveCount(0, { timeout: 15_000 });
  expect(await other.evaluate(() => (window as unknown as { marker?: number }).marker)).toBe(1);
});

test('cancel in one tab, the other shows Cancelled and no Cancel button', async ({ page, context, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(240_000);
  const id = await launch(request, ['local'], { scale: 5 }); // two CPUs and more samples: it still runs
  await reach(request, id, ['running']);
  const other = await context.newPage();
  const errors: Error[] = [];
  other.on('pageerror', (e) => errors.push(e));
  await page.goto(`/runs/${id}`);
  await other.goto(`/runs/${id}`);
  const cancel = (p: Page) => p.getByRole('button', { name: 'Cancel run' });
  await expect(cancel(page)).toBeVisible();
  await expect(cancel(other)).toBeVisible();

  await cancel(page).click();
  const dialog = page.getByRole('dialog', { name: 'Cancel this run?' });
  await dialog.getByRole('button', { name: 'Cancel the run' }).click();
  await expect(page.locator('header .sp-state')).toHaveText('Cancelled', { timeout: 150_000 });

  // the other tab follows through its own stream: Cancelled, no Cancel button, no error
  await expect(other.locator('header .sp-state')).toHaveText('Cancelled', { timeout: 30_000 });
  await expect(cancel(other)).toHaveCount(0);
  await expect(other.getByText('could not be read')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('Mark all as read in one tab marks the run read in the other', async ({ page, context, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const { name } = await endedRun(request); // an ended run is an unread notification
  const other = await context.newPage();
  await page.goto('/runs');
  await other.goto('/runs');
  const unread = /^Notifications, [1-9]\d* unread$/;
  await expect(bellOf(page)).toHaveAccessibleName(unread);
  await expect(bellOf(other)).toHaveAccessibleName(unread);

  await bellOf(page).click();
  await page.getByRole('button', { name: 'Mark all as read' }).click();

  // Marking is no run change, so no frame says so: the other tab's notifications are read again on
  // its next load. Other tests end runs too, so not the unread count — this test's own run: its
  // item is there, and its label does not end with "unread" (the bell names an item that way).
  await other.reload();
  await bellOf(other).click();
  const item = other.locator('.sp-notif-list').getByRole('link', { name: new RegExp(`^${name},`) });
  await expect(item).toBeVisible();
  await expect(item).not.toHaveAccessibleName(/unread$/);
});

test('signing out in one tab sends the other to sign-in on its next request', async ({ browser }) => {
  test.skip(!isLocal(target.url), NEEDS_LOCAL);
  // its own session, from its own link: signing out must not end the one the other tests share
  const context = await bare(browser);
  try {
    const page = await context.newPage();
    await openLink(page, newTicket());
    await expect(page).toHaveURL(new URL('/', target.url).href);
    const other = await context.newPage();
    await other.goto('/runs');
    await expect(other.getByRole('heading', { level: 1, name: 'Runs' })).toBeVisible();

    await page.goto('/profile');
    await page.getByRole('button', { name: 'Sign out of this session' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Signed out of this session.' })).toBeVisible();
    expect((await context.cookies()).map((c) => c.name)).not.toContain(sessionCookie(target.url));

    // the other tab's next navigation meets the sign-in answer, not the app
    const next = await other.goto('/runs');
    expect(next!.status()).toBe(401);
    await expect(other.locator('body')).toContainText('Sign-in required');
    await expect(other.locator('body')).toContainText('spectio login --print-link');
    expect((await context.request.get('/api/v1/me')).status()).toBe(401);
  } finally {
    await context.close();
  }
});
