import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { join } from 'node:path';
import { resolveTarget } from './base-url';

// The 0.0.1 smoke of P1 Task 20, against a real `spectio serve` (tests/e2e/serve-local.sh):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test skeleton.spec.ts   (in tests/e2e)
// Tests that run a workflow engine need Nextflow on the server's PATH and SPECTIO_E2E_ENGINES=1;
// CI's e2e-local job sets it after dev/bootstrap.sh. The others answer from the server alone or
// from route mocks. Local-only order (inbox #80): no token link or session cookie before P1
// Tasks 12 to 16, so the two session tests wait as fixme, and what holds today is tested instead.

const target = resolveTarget(process.env);
const ENGINES = process.env.SPECTIO_E2E_ENGINES === '1';
const NEEDS_ENGINES = 'needs Nextflow: set SPECTIO_E2E_ENGINES=1 (CI job e2e-local)';
const SYNTHETIC = join(__dirname, '..', 'pipelines', 'synthetic');
const RUN = 'run_01JBC6Q4ZK7M8N2P3R5S7T9V1W';

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

/** POST /runs as the launch form does; `profiles` and `params` slow the run down when asked. */
async function launch(request: APIRequestContext, profiles: string[], params: object = {}): Promise<string> {
  const response = await request.post('/api/v1/runs', {
    headers: { Origin: new URL(target.url).origin },
    data: { workflow: { location: join(SYNTHETIC, 'nextflow'), revision: null, engine: 'nextflow' }, profiles, params },
  });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()).id;
}

/** Wait until the run's API state is `state`. */
async function reach(request: APIRequestContext, id: string, states: string[]) {
  await expect
    .poll(async () => (await (await request.get(`/api/v1/runs/${id}`)).json()).state, { timeout: 120_000 })
    .toMatch(new RegExp(`^(${states.join('|')})$`));
}

const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

function mockRun(over: object = {}) {
  return {
    id: RUN, name: 'rnaseq-mock', state: 'running', origin: 'ui',
    created_at: '2026-10-31T07:40:00+00:00', started_at: '2026-10-31T07:40:05+00:00', ended_at: null,
    workflow: { engine: 'nextflow', engine_version: '26.10.4', location: '/g/demo-lab/pipelines/rnaseq', name: 'nf-core/rnaseq', version: '3.27.0' },
    profiles: ['test'], failure: null,
    head: { session: `spectio-${RUN}`, node: 'login1', alive: true, exit_code: null },
    task_counts: { succeeded: 24, running: 3 },
    summary: { tasks: { done: 24, total: 27, failed: 0, cached: 0 }, last_failure: null },
    params: {}, ...over,
  };
}

async function mockDetail(page: Page, stages: object[]) {
  await page.route(`**/api/v1/runs/${RUN}`, (r) => r.fulfill(json(mockRun())));
  await page.route(`**/api/v1/runs/${RUN}/stages`, (r) => r.fulfill(json({ items: stages })));
  await page.route(`**/api/v1/runs/${RUN}/processes`, (r) =>
    r.fulfill(json({ items: [
      { process: 'NFCORE:QC:FASTQC', stage_id: stages.length ? 'st1' : null, counts: { succeeded: 12 }, retries: 0 },
      { process: 'NFCORE:ALIGN:STAR', stage_id: stages.length ? 'st2' : null, counts: { succeeded: 12, running: 3 }, retries: 0 },
    ] })),
  );
}

test('link → empty list → launch happy (Nextflow, local) → detail shows Succeeded and 65 tasks', async ({ page }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  // No link exchange before P1 Task 12: the address is the way in. The two projects share one
  // server, so the empty list is the server's answer replayed, not the server's state.
  await page.route('**/api/v1/runs?*', (r) => r.fulfill(json({ items: [], next: null })));
  await page.goto('/runs');
  await expect(page.getByText('No runs yet.')).toBeVisible();
  await page.locator('.sp-empty').getByRole('link', { name: 'Launch a workflow' }).click();
  await page.unroute('**/api/v1/runs?*');

  await page.getByRole('textbox', { name: /^Pipeline/ }).fill(join(SYNTHETIC, 'nextflow'));
  await page.getByRole('button', { name: 'Load', exact: true }).click();
  await page.getByRole('combobox', { name: 'Profile' }).selectOption('test');
  await page.getByRole('button', { name: 'Launch', exact: true }).click();

  await expect(page).toHaveURL(/\/runs\/run_[0-9A-Z]{26}$/);
  await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 150_000 });
  await expect(page.getByText('65 / 65 tasks')).toBeVisible();
});

test('home at / shows the count cards, the active runs and the runs that ended', async ({ page }) => {
  await page.route('**/api/v1/runs:summary*', (r) =>
    r.fulfill(json({ groups: [{ key: 'running', count: 1 }, { key: 'succeeded', count: 2 }] })));
  await page.route('**/api/v1/runs?*', (r) => {
    const url = new URL(r.request().url());
    if (url.searchParams.get('state')) return r.fulfill(json({ items: [mockRun()], next: null }));
    const ended = mockRun({ id: 'run_01JBC6Q4ZK7M8N2P3R5S7T9V2X', name: 'fetch-geo', state: 'succeeded', ended_at: '2026-10-31T08:00:00+00:00' });
    return r.fulfill(json({ items: url.searchParams.get('sort') ? [ended] : [mockRun(), ended], next: null }));
  });
  await page.goto('/');
  const cards = page.getByRole('list', { name: 'Runs by state' });
  await expect(cards.getByText('Running')).toBeVisible();
  await expect(cards.getByText('Succeeded')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Active runs' }).getByRole('link', { name: 'Open run rnaseq-mock' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Finished recently' }).getByRole('link', { name: 'Open run fetch-geo' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Your pipelines' })).toContainText('/g/demo-lab/pipelines/rnaseq');
});

test('the detail shows the flat list with no stage, and the stages when /stages has items', async ({ page }, info) => {
  // The phone shows the processes as stacked cards, not a table (UX-PAR-10).
  const processes = info.project.name === 'phone' ? 'list' : 'table';
  await mockDetail(page, []);
  await page.goto(`/runs/${RUN}`);
  await expect(page.getByText('No stages for this pipeline: processes as the engine reports them.')).toBeVisible();
  await expect(page.getByRole(processes, { name: 'Processes' })).toBeVisible();

  await page.unrouteAll();
  await mockDetail(page, [
    { id: 'st1', position: 1, name: 'QC', source: 'detected', state: 'completed', task_counts: { succeeded: 12 } },
    { id: 'st2', position: 2, name: 'Align', source: 'detected', state: 'running', task_counts: { succeeded: 12, running: 3 } },
  ]);
  await page.reload();
  await expect(page.getByText('1 of 2 stages done · 1 running')).toBeVisible();
  await expect(page.getByRole(processes, { name: 'Processes of Align' })).toBeVisible(); // the running stage is open
  await expect(page.getByText('No stages for this pipeline')).toHaveCount(0);
});

test('cancel a running Snakemake run → Cancelled', async () => {
  test.fixme(true, 'TODO(P1 Task 7): the Snakemake logger plugin is not built, so a Snakemake run reports nothing yet');
});

test('cancel a running Nextflow run → Cancelled', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const id = await launch(request, ['local'], { scale: 5 }); // two CPUs and more samples: it still runs
  await reach(request, id, ['running']);
  await page.goto(`/runs/${id}`);
  const cancel = page.getByRole('button', { name: 'Cancel run' });
  await cancel.click();
  const dialog = page.getByRole('dialog', { name: 'Cancel this run?' });
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  await dialog.getByRole('button', { name: 'Cancel the run' }).click();
  await expect(page.locator('header .sp-state')).toHaveText(/Cancelling|Cancelled/);
  await expect(page.locator('header .sp-state')).toHaveText('Cancelled', { timeout: 150_000 });
  await expect(cancel).toHaveCount(0);
});

test('a reused link shows the expired message', async () => {
  test.fixme(true, 'TODO(P1 Task 16): no token link before Tasks 12 to 16 (inbox #80, local-only order)');
});

test('the detail updates without a reload as tasks finish', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const id = await launch(request, ['local'], { scale: 3 });
  const streams: Record<string, string>[] = [];
  page.on('request', (r) => r.url().endsWith('/api/v1/events/stream') && streams.push(r.headers()));
  await page.goto(`/runs/${id}`);
  await page.evaluate(() => ((window as unknown as { marker: number }).marker = 1));
  const tasks = page.locator('header').getByText(/ tasks$/);
  const first = await tasks.textContent();
  await expect(tasks).not.toHaveText(first ?? '', { timeout: 120_000 });
  await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 150_000 });
  expect(await page.evaluate(() => (window as unknown as { marker?: number }).marker)).toBe(1); // no reload
  expect(streams).toHaveLength(1); // one EventSource, same origin, no session cookie yet (Task 13)
  expect(streams[0].cookie).toBeUndefined();
});

test('a request without the cookie shows the 401 page, not data', async () => {
  test.fixme(true, 'TODO(P1 Task 16): no session cookie before Tasks 12 to 16 (inbox #80, local-only order)');
});

// What holds in the local-only order, in place of the two session tests above.

test('a foreign Host gets 400 and no data', async ({ playwright }) => {
  const request = await playwright.request.newContext({ baseURL: target.url, extraHTTPHeaders: { Host: 'evil.example' } });
  for (const path of ['/api/v1/runs', '/runs', '/']) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(400);
    const body = await response.text();
    expect(body).not.toContain('"items"');
    expect(body).not.toContain('<script');
  }
  await request.dispose();
});

test('the served pages carry the CSP, Referrer-Policy and COOP headers', async ({ page }) => {
  for (const path of ['/', '/runs', `/runs/${RUN}`, '/launch']) {
    const response = await page.goto(path);
    const headers = response!.headers();
    expect(headers['content-security-policy'], path).toContain("default-src 'none'");
    expect(headers['content-security-policy'], path).toContain("script-src 'self';");
    expect(headers['referrer-policy'], path).toBe('no-referrer');
    expect(headers['cross-origin-opener-policy'], path).toBe('same-origin');
  }
});

test('a malformed run id shows not-found inside the shell', async ({ page }) => {
  const errors: Error[] = [];
  page.on('pageerror', (e) => errors.push(e));
  await page.goto('/runs/%E0');
  await expect(page.getByRole('heading', { level: 1, name: 'No such run' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('%E0'); // no URL text, crumbs included
  expect(errors).toEqual([]);
});
