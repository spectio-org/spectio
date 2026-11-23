import { test, expect, type APIRequestContext, type Page, type Request } from '@playwright/test';
import { join } from 'node:path';
import { resolveTarget } from './base-url';

// RC1 gaps L-04, R-06 and D-20 (docs: RC1 acceptance §18): the live stream of a real server drops
// and comes back, and the screens that follow it catch up. Run like skeleton.spec.ts (tests/e2e/serve-local.sh
// and SPECTIO_E2E_BASE_URL); both tests launch a run, so they need SPECTIO_E2E_ENGINES=1.
//
// A stream already open is not cut by `page.route`, which sees new requests only. So each test installs
// the abort before it opens the page: the page's EventSource never connects, retries (the browser
// after a network error, or live.tsx after 5 s), and connects once the route is released.

const target = resolveTarget(process.env);
const ENGINES = process.env.SPECTIO_E2E_ENGINES === '1';
const NEEDS_ENGINES = 'needs Nextflow: set SPECTIO_E2E_ENGINES=1 (CI job e2e-local)';
const SYNTHETIC = join(__dirname, '..', 'pipelines', 'synthetic');
const STREAM = '**/api/v1/events/stream**';

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

/** The stream requests a page makes, and how many of them the server answered. */
function watchStream(page: Page) {
  const asked: Request[] = [];
  let answered = 0;
  page.on('request', (r) => r.url().includes('/api/v1/events/stream') && asked.push(r));
  page.on('response', (r) => r.url().includes('/api/v1/events/stream') && r.status() === 200 && answered++);
  return { asked, answered: () => answered };
}

test('a dropped event stream says Reconnecting…, comes back and refetches the runs that changed', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(240_000);
  const id = await launch(request, ['local'], { scale: 5 });
  await reach(request, id, ['running']);
  const name: string = (await (await request.get(`/api/v1/runs/${id}`)).json()).name;
  const stream = watchStream(page);

  // The list opens while the stream is refused: it shows the run as it is now.
  await page.route(STREAM, (r) => r.abort());
  await page.goto(`/runs?q=${encodeURIComponent(name)}`);
  await expect(page.getByRole('link', { name: `Open run ${name}` }).first()).toBeVisible();
  const state = page.locator('.sp-grid .sp-state').first();
  await expect(state).toHaveText('Running');
  await expect(page.getByText('Reconnecting…').first()).toBeVisible();
  // It retries, and each try is refused: no frame can reach the list.
  await expect.poll(() => stream.asked.length, { timeout: 30_000 }).toBeGreaterThan(1);
  expect(stream.answered()).toBe(0);

  // The run ends meanwhile, which the page cannot hear.
  const cancelled = await request.post(`/api/v1/runs/${id}:cancel`, { headers: { Origin: new URL(target.url).origin } });
  expect(cancelled.status(), await cancelled.text()).toBeLessThan(300);
  await reach(request, id, ['cancelled']);
  await expect(state).not.toHaveText('Cancelled');

  // The route is released: a new EventSource connects (R-06) and the list refetches (L-04).
  await page.unroute(STREAM);
  await expect.poll(() => stream.answered(), { timeout: 30_000 }).toBeGreaterThan(0);
  await expect(page.getByText(/^live, updated \d+ s ago$/).first()).toBeVisible();
  await expect(state).toHaveText('Cancelled');
  await expect(page.getByText('Reconnecting…')).toHaveCount(0);
});

test('the run detail reconnects after a dropped stream and shows the tasks that finished', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(240_000);
  const id = await launch(request, ['local'], { scale: 5 });
  const stream = watchStream(page);

  // The detail opens while the stream is refused, on a run that has not ended.
  await page.route(STREAM, (r) => r.abort());
  await page.goto(`/runs/${id}`);
  const header = page.locator('header');
  const state = header.locator('.sp-state');
  await expect(state).toHaveText(/Queued|Running/);
  await expect(header.getByText('Reconnecting…')).toBeVisible();

  // The run ends meanwhile: the API says so, the page does not.
  await reach(request, id, ['succeeded']);
  expect(stream.answered()).toBe(0);
  await expect(state).not.toHaveText('Succeeded');

  // The route is released: the stream reconnects and the header catches up, with no reload.
  await page.evaluate(() => ((window as unknown as { marker: number }).marker = 1));
  await page.unroute(STREAM);
  await expect(state).toHaveText('Succeeded', { timeout: 30_000 });
  await expect(header.getByText(/^(\d+) \/ \1 tasks$/)).toBeVisible();
  expect(stream.answered()).toBeGreaterThan(0);
  expect(await page.evaluate(() => (window as unknown as { marker?: number }).marker)).toBe(1);
});
