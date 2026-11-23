import { test, expect, type APIRequestContext, type Browser, type Page, type Request } from '@playwright/test';
import { cpSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { isLocal, resolveTarget } from './base-url';
import { newTicket, sessionCookie, withoutTicket } from './global-setup';

// The 0.0.1 smoke of P1 Task 20, against a real `spectio serve` (tests/e2e/serve-local.sh):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test skeleton.spec.ts   (in tests/e2e)
// Tests that run a workflow engine need Nextflow on the server's PATH and SPECTIO_E2E_ENGINES=1;
// CI's e2e-local job sets it after dev/bootstrap.sh. The others answer from the server alone or
// from route mocks. Each test has the session that global-setup.ts got through the token link
// (P1 Task 12); the tests of the link itself and of Sign out open their own context with a fresh link.

const target = resolveTarget(process.env);
const ENGINES = process.env.SPECTIO_E2E_ENGINES === '1';
const NEEDS_ENGINES = 'needs Nextflow: set SPECTIO_E2E_ENGINES=1 (CI job e2e-local)';
// Snakemake on the server's PATH too (RC1 gaps E-02 and X-09), with the Snakemake logger plugin installed.
const SNAKEMAKE = process.env.SPECTIO_E2E_SNAKEMAKE === '1';
const NEEDS_SNAKEMAKE = 'needs Snakemake and its logger plugin on the server: set SPECTIO_E2E_SNAKEMAKE=1 (with SPECTIO_E2E_ENGINES=1)';
// Tests that mint a token link or write a pipeline copy need the server's files, so its machine.
const NEEDS_LOCAL = 'needs the server on this machine: serve-local.sh writes the link pointer next to the specs';
// The run tests/e2e/seed_stages.py writes (serve-local.sh --seed-stages): P1 Task 27.
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const IS_SEEDED = process.env.SPECTIO_E2E_SEEDED === '1';
const NEEDS_SEED = 'needs the seeded rnaseq run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1';
const SYNTHETIC = join(__dirname, '..', 'pipelines', 'synthetic');
const RUN = 'run_01JBC6Q4ZK7M8N2P3R5S7T9V1W';

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

/** POST /runs as the launch form does; `profiles` and `params` slow the run down when asked. */
async function launch(
  request: APIRequestContext,
  profiles: string[],
  params: object = {},
  engine: 'nextflow' | 'snakemake' = 'nextflow',
  location = join(SYNTHETIC, engine),
): Promise<string> {
  const response = await request.post('/api/v1/runs', {
    headers: { Origin: new URL(target.url).origin },
    data: { workflow: { location, revision: null, engine }, profiles, params },
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
    summary: { tasks: { done: 24, total: 27, failed: 0, cached: 0 }, last_failure: null, stage_mode: 'quarters' },
    params: {}, stages_note: null,
    // the fields of P1 Tasks 29 to 31 (schema RunDetail)
    failures: [], failures_total: 0, command: null, parent_run_id: null, resumed_as: [],
    actions: { resume: { allowed: false, reason: 'running' } }, results_dir: null,
    head_logs: ['head-out', 'head-err'], // FU-P3-124
    ...over,
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
  // The link was exchanged once in global-setup.ts. The two projects share one server, so the
  // empty list is the server's answer replayed, not the server's state.
  await page.route('**/api/v1/runs?*', (r) => r.fulfill(json({ items: [], next: null })));
  await page.goto('/runs');
  await expect(page.getByText('No runs yet.')).toBeVisible();
  await page.locator('.sp-empty').getByRole('link', { name: 'Launch a workflow' }).click();
  await page.unroute('**/api/v1/runs?*');

  await page.getByRole('textbox', { name: /^Pipeline/ }).fill(join(SYNTHETIC, 'nextflow'));
  await page.getByRole('button', { name: 'Load', exact: true }).click();
  await page.getByRole('combobox', { name: 'Profile' }).selectOption('test');
  // Launch is in the page head and under the aside on a desktop, one action (P3-parC): the head's.
  await page.getByRole('button', { name: 'Launch', exact: true }).first().click();

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

test('FU-P3-109: Home\'s Your pipelines and Where your runs go keep long paths inside the page, shown whole', async ({ page }, info) => {
  if (info.project.name === 'desktop') await page.setViewportSize({ width: 1440, height: 1180 });
  const long = '/g/demo-lab/' + 'a-very-long-directory-name-without-any-break/'.repeat(4) + 'rnaseq';
  const root = '/scratch/amartin/' + 'spectio-runs-on-a-long-shared-scratch-volume/'.repeat(3) + 'runs';
  const server = await (await page.request.get('/api/v1/version')).json();
  await page.route('**/api/v1/version', (r) => r.fulfill(json({ ...server, runs_root: root })));
  await page.route('**/api/v1/runs:summary*', (r) => r.fulfill(json({ groups: [{ key: 'succeeded', count: 1 }] })));
  const ended = mockRun({ state: 'succeeded', ended_at: '2026-10-31T08:00:00+00:00',
    workflow: { engine: 'nextflow', engine_version: '26.10.4', location: long, name: null, version: null } });
  await page.route('**/api/v1/runs?*', (r) => r.fulfill(json({ items: [ended], next: null })));
  await page.goto('/');
  const pipelines = page.getByRole('region', { name: 'Your pipelines' });
  const where = page.getByRole('region', { name: 'Where your runs go' });
  await expect(pipelines.getByRole('link', { name: `Launch ${long}, ${long}` })).toBeVisible();
  await expect(where).toContainText(root);
  // nothing runs past the right edge: no page scroll, every card within the viewport
  const width = page.viewportSize()!.width;
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  for (const card of [pipelines, where]) {
    const box = (await card.boundingBox())!;
    expect(box.x + box.width).toBeLessThanOrEqual(width);
  }
  // the whole value is on screen as text, not cut by an ellipsis (no hover needed)
  for (const text of [pipelines.getByText(long).last(), where.getByText(root)]) {
    expect(await text.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  }
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

test('a run of the synthetic happy shows no stage, only its processes (P1 Task 27)', async ({ page, request }, info) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const id = await launch(request, ['test']);
  await reach(request, id, ['succeeded']);
  expect((await (await request.get(`/api/v1/runs/${id}/stages`)).json()).items).toEqual([]);
  await page.goto(`/runs/${id}`);
  await expect(page.getByText('No stages for this pipeline: processes as the engine reports them.')).toBeVisible();
  await expect(page.getByRole(info.project.name === 'phone' ? 'list' : 'table', { name: 'Processes' })).toBeVisible();
});

test('FU-P3-115b: an ended run is selected in the list and deleted, and leaves the API', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const id = await launch(request, ['test']);
  await reach(request, id, ['succeeded']);
  const name = (await (await request.get(`/api/v1/runs/${id}`)).json()).name;
  await page.goto(`/runs?q=${encodeURIComponent(name)}`);
  await page.getByRole('checkbox', { name: `Select run ${name}` }).check();
  await page.getByRole('button', { name: 'Delete…' }).click();
  const sheet = page.getByRole('dialog', { name: 'Delete 1 run?' });
  await expect(sheet.getByRole('listitem')).toHaveText(`${name} · Succeeded`);
  await sheet.getByRole('button', { name: 'Delete', exact: true }).click();
  await expect(page.getByRole('status').getByText('1 run deleted')).toBeVisible();
  await expect(page.getByRole('link', { name: `Open run ${name}` })).toHaveCount(0);
  expect((await request.get(`/api/v1/runs/${id}`)).status()).toBe(404);
});

test('a seeded rnaseq run shows 8 detected stages above its processes (P1 Task 27)', async ({ page, request }) => {
  test.skip(!IS_SEEDED, NEEDS_SEED);
  await reach(request, SEEDED, ['succeeded']);
  const run = await (await request.get(`/api/v1/runs/${SEEDED}`)).json();
  expect(run.summary.stage_mode).toBe('detected');
  const stages = (await (await request.get(`/api/v1/runs/${SEEDED}/stages`)).json()).items;
  expect(stages.map((s: { id: string }) => s.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8].map((n) => `detected:${n}`));
  await page.goto(`/runs/${SEEDED}`);
  await expect(page.getByText('0 of 8 stages done · 0 running')).toBeVisible(); // a preview: no task ran
  const section = page.getByRole('region', { name: 'Stages' });
  await expect(section.getByText(/^8 stages, in order/)).toBeVisible();
  await expect(section.locator('.sp-stage')).toHaveCount(8); // all 67 processes are in a stage: no "Not in a stage"
  await expect(section.getByText('Detected', { exact: true })).toHaveCount(8);
  await expect(section.getByText('Report', { exact: true })).toBeVisible();
});

test('launch happy (Snakemake, local) → detail shows Succeeded and the golden counts', async ({ page, request }) => {
  test.skip(!ENGINES || !SNAKEMAKE, !ENGINES ? NEEDS_ENGINES : NEEDS_SNAKEMAKE);
  test.setTimeout(240_000);
  // chunks=2: what Nextflow's profile `test` sets, and what the golden of the happy scenario counts
  const id = await launch(request, ['local'], { chunks: 2 }, 'snakemake');
  await reach(request, id, ['succeeded']);
  await page.goto(`/runs/${id}`);
  await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 150_000 });
  await expect(page.locator('header').getByText(/^(\d+) \/ \1 jobs$/)).toBeVisible(); // done = total, in jobs
  // the golden of the scenario, rule by rule (tests/slurm/e2e_client.py compares the same way)
  const golden = join(SYNTHETIC, 'golden', readdirSync(join(SYNTHETIC, 'golden')).find((d) => d.startsWith('snakemake-'))!, 'happy.tsv');
  const want: Record<string, number> = {};
  for (const line of readFileSync(golden, 'utf8').split('\n')) {
    const [, process, status, , , , count] = line.split('\t');
    if (status === 'COMPLETED') want[process] = Number(count);
  }
  const got = Object.fromEntries(
    ((await (await request.get(`/api/v1/runs/${id}/processes`)).json()).items as { process: string; counts: { succeeded?: number } }[])
      .map((p) => [p.process.toUpperCase(), p.counts.succeeded ?? 0]),
  );
  expect(got).toEqual(want);
});

test('cancel a running Snakemake run → Cancelled', async ({ page, request }) => {
  test.skip(!ENGINES || !SNAKEMAKE, !ENGINES ? NEEDS_ENGINES : NEEDS_SNAKEMAKE);
  test.setTimeout(240_000);
  const id = await launch(request, ['local'], { chunks: 2, scale: 5 }, 'snakemake'); // more samples: it still runs
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

/** A browser context with no session: the cookies global-setup.ts got are not in it. */
const bare = (browser: Browser) => browser.newContext({ baseURL: target.url, storageState: { cookies: [], origins: [] } });

/** Opens the token link of `ticket` in `page`, as a user does; an error never names the ticket. */
async function openLink(page: Page, ticket: string) {
  await page.goto(`/auth/link#${ticket}`).catch((error) => {
    throw withoutTicket(error, ticket);
  });
}

test('a reused link shows the expired message', async ({ browser }) => {
  test.skip(!isLocal(target.url), NEEDS_LOCAL);
  const ticket = newTicket(target.url);
  const first = await bare(browser);
  const second = await bare(browser);
  try {
    // the first use signs in: the bootstrap page exchanges the ticket and opens the app
    const used = await first.newPage();
    await openLink(used, ticket);
    await expect(used).toHaveURL(new URL('/', target.url).href);
    expect((await first.cookies()).map((c) => c.name)).toContain(sessionCookie(target.url));
    // the second finds the ticket burnt: the message, no sign-in, no cookie
    const reused = await second.newPage();
    await openLink(reused, ticket);
    await expect(reused.getByText('This link was already used or has expired.')).toBeVisible();
    await expect(reused.getByText('spectio login --print-link')).toBeVisible();
    await expect(reused.getByText('Signing in…')).toBeHidden();
    expect(new URL(reused.url()).hash).toBe(''); // the ticket is out of the address bar
    expect((await second.cookies()).map((c) => c.name)).not.toContain(sessionCookie(target.url));
  } finally {
    await first.close();
    await second.close();
  }
});

test('the detail updates without a reload as tasks finish', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const id = await launch(request, ['local'], { scale: 3 });
  const streams: Request[] = [];
  page.on('request', (r) => r.url().endsWith('/api/v1/events/stream') && streams.push(r));
  await page.goto(`/runs/${id}`);
  await page.evaluate(() => ((window as unknown as { marker: number }).marker = 1));
  const tasks = page.locator('header').getByText(/ tasks$/);
  const first = await tasks.textContent();
  await expect(tasks).not.toHaveText(first ?? '', { timeout: 120_000 });
  await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 150_000 });
  expect(await page.evaluate(() => (window as unknown as { marker?: number }).marker)).toBe(1); // no reload
  expect(streams).toHaveLength(1); // one EventSource, same origin
  // It carries the session cookie of this port (req. 3 [to be validated]); headers() leaves cookies out.
  expect((await streams[0].allHeaders()).cookie).toMatch(new RegExp(`(^|; )${sessionCookie(target.url)}=`));
});

test('a request without the cookie shows the 401 page, not data', async ({ browser }) => {
  const context = await bare(browser);
  try {
    const page = await context.newPage();
    const response = await page.goto('/runs');
    expect(response!.status()).toBe(401);
    const body = await page.locator('body').innerText();
    expect(body).toContain('Sign-in required');
    expect(body).toContain('spectio login --print-link');
    expect(body).not.toContain('"items"'); // no run data
    for (const path of ['/api/v1/runs', '/api/v1/me']) {
      const api = await context.request.get(path);
      expect(api.status(), path).toBe(401);
      expect(await api.text(), path).not.toContain('"items"');
    }
  } finally {
    await context.close();
  }
});

// What holds whatever the order of the tasks: the Host check and the headers.

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
    expect(headers['content-security-policy'], path).toContain("script-src 'self' 'wasm-unsafe-eval';");
    expect(headers['content-security-policy'], path).toContain("worker-src 'self'");
    expect(headers['content-security-policy'], path).not.toContain("'unsafe-eval'");
    expect(headers['content-security-policy'], path).not.toContain('blob:');
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

// P1 Task 32, the parts on Tasks 28 and 29's routes: each job's files, the failure summary and the
// resources, answered by route mocks (the shapes of packages/spectio-server/openapi/0.0.1.json).
const GIB = 1024 ** 3;
const PROC = 'NFCORE:RNASEQ:SUBREAD_FEATURECOUNTS';
const WORKDIR = `/scratch/amartin/spectio-runs/${RUN}/work/9d/77c2140f5be3a1c96e04d2b88a7f13`;
const FAILED_TASK = {
  id: 'tsk_19', process: PROC, tag: 'S19', name: 'SUBREAD_FEATURECOUNTS (S19)', state: 'failed', stage_id: null, attempt_n: 1,
  resources: { cpus: 6, memory_bytes: 8 * GIB, time_s: 8 * 3600, realtime_s: 360, cpu_percent: 412, peak_rss_bytes: 8 * GIB, source: 'trace' },
};
const jobFile = (name: string, kind: string, over: object = {}) =>
  ({ name, kind, size: 2458, mtime: '2026-10-31T08:42:00+00:00', state: 'present', note: null, ...over });

async function mockFailed(page: Page, over: object = {}) {
  await page.route(`**/api/v1/runs/${RUN}`, (r) => r.fulfill(json({
    ...mockRun({
      state: 'failed', ended_at: '2026-10-31T08:50:00+00:00',
      failure: { class: 'tool_error', message: '', task_id: 'tsk_19', attempt_n: 1 },
      head: { session: `spectio-${RUN}`, node: 'login1', alive: false, exit_code: 1 },
      task_counts: { succeeded: 24, failed: 1 },
      summary: { tasks: { done: 24, total: 25, failed: 1, cached: 0 }, last_failure: null, stage_mode: 'quarters' },
    }),
    failures: [{
      task_id: 'tsk_19', process: PROC, tag: 'S19', attempt_n: 1, native_id: '8812477', exit_code: 137,
      message: 'Process `SUBREAD_FEATURECOUNTS (S19)` terminated with an error exit status (137)',
      log_tail: 'Total alignments : 61842317\nslurmstepd: error: Detected 1 oom_kill event in StepId=8812477.batch\n',
      scheduler: { state: 'OUT_OF_MEMORY', reason: 'Step 0: OutOfMemory', state_source: 'sacct', max_rss_bytes: 8 * GIB, req_mem_bytes: 8 * GIB,
        elapsed_s: 360, time_limit_s: 8 * 3600, usage_source: 'sacct', accounting: 'available' },
      work_dir: WORKDIR,
    }],
    failures_total: 1,
    ...over,
  })));
  await page.route(`**/api/v1/runs/${RUN}/stages`, (r) => r.fulfill(json({ items: [] })));
  await page.route(`**/api/v1/runs/${RUN}/processes`, (r) =>
    r.fulfill(json({ items: [{ process: PROC, stage_id: null, counts: { succeeded: 24, failed: 1 }, retries: 0 }] })));
  await page.route(`**/api/v1/runs/${RUN}/tasks?*`, (r) => r.fulfill(json({ items: [FAILED_TASK], next: null })));
  await page.route(`**/api/v1/runs/${RUN}/logs?*`, (r) => r.fulfill({ status: 200, contentType: 'text/plain', body: 'Error executing process\n' }));
  await page.route('**/api/v1/version', (r) => r.fulfill(json({ version: '0.0.1', node: 'login1', runs_root: '/scratch/amartin/spectio-runs', account: 'amartin', executor: 'slurm' })));
  await page.route('**/api/v1/tasks/tsk_19/attempts/1/files', (r) => r.fulfill(json({
    task_id: 'tsk_19', attempt: 1, work_dir: WORKDIR, native_id: '8812477',
    files: [
      jobFile('.command.sh', 'script'), jobFile('.command.run', 'wrapper'), jobFile('.command.out', 'stdout', { size: 3250586 }),
      jobFile('.command.err', 'stderr'), jobFile('.command.log', 'job_log', { note: 'May show values from your parameters or environment.' }),
      jobFile('.exitcode', 'exit'), jobFile('.command.begin', 'marker'),
      jobFile('.command.trace', 'trace', { state: 'absent', size: null, mtime: null, note: 'Written only when the run measures its tasks.' }),
    ],
  })));
  await page.route('**/api/v1/tasks/tsk_19/attempts/1/files/**', (r) => {
    const name = decodeURIComponent(new URL(r.request().url()).pathname.split('/files/')[1]);
    return name === '.command.log'
      ? r.fulfill({ status: 200, contentType: 'text/plain', body: '|| Process BAM file S19.markdup.sorted.bam...\nslurmstepd: error: Detected 1 oom_kill event in StepId=8812477.batch\n' })
      : r.fulfill({ status: 200, contentType: 'text/plain', body: `${name}\n` });
  });
}

test('failed run: Why it failed shows SLURM state, requested and used memory, last lines', async ({ page }) => {
  await mockFailed(page);
  await page.goto(`/runs/${RUN}`);
  const job = page.getByRole('article', { name: 'SUBREAD_FEATURECOUNTS (S19), attempt 1' });
  await expect(job.getByText('OUT_OF_MEMORY')).toBeVisible();
  await expect(job.getByText('8 GB · 8 GB near limit')).toBeVisible();
  await expect(job.getByText(/SLURM state: from sacct · Reason: Step 0: OutOfMemory/)).toBeVisible();
  await expect(job.getByLabel('SUBREAD_FEATURECOUNTS (S19), last lines')).toContainText('oom_kill event');
  await expect(job.getByRole('button', { name: 'Copy the work directory of SUBREAD_FEATURECOUNTS (S19)' })).toBeVisible();
});

test("Files opens the drawer on .command.log for a failed attempt; Escape returns focus to the row's button", async ({ page }) => {
  await mockFailed(page);
  await page.goto(`/runs/${RUN}?tab=tasks`);
  const files = page.getByRole('button', { name: 'Files of SUBREAD_FEATURECOUNTS (S19), attempt 1' });
  await files.click();
  const sheet = page.getByRole('dialog', { name: 'SUBREAD_FEATURECOUNTS (S19)' });
  await expect(sheet).toHaveAttribute('aria-modal', 'true');
  await expect(sheet.getByText(/oom_kill event/)).toBeVisible();
  await expect(sheet.getByText(WORKDIR)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(sheet).toHaveCount(0);
  await expect(files).toBeFocused();
});

test("tabs are buttons with role tab; the size line and Download; a missing file's state is in its label", async ({ page }, info) => {
  await mockFailed(page);
  await page.goto(`/runs/${RUN}?tab=tasks`);
  await page.getByRole('button', { name: 'Files of SUBREAD_FEATURECOUNTS (S19), attempt 1' }).click();
  const sheet = page.getByRole('dialog', { name: 'SUBREAD_FEATURECOUNTS (S19)' });
  await expect(sheet.getByText(/^whole file · 2\.4 KiB · written /)).toBeVisible();
  if (info.project.name === 'phone') {
    // the phone's files are a native select labelled File (MLiteTaskFilesSheet)
    const select = sheet.getByRole('combobox', { name: 'File' });
    await expect(select.getByRole('option', { name: '.command.trace · missing' })).toHaveCount(1);
    await select.selectOption('.command.out');
  } else {
    for (const tab of await sheet.getByRole('tab').all()) expect(await tab.evaluate((e) => e.tagName)).toBe('BUTTON');
    await sheet.getByRole('button', { name: 'More files' }).click();
    await expect(sheet.getByRole('tab', { name: '.command.trace · missing' })).toBeVisible();
    await sheet.getByRole('tab', { name: '.command.out' }).click();
  }
  await expect(sheet.getByText(/^last 64 KiB of 3\.1 MiB/)).toBeVisible();
  await expect(sheet.getByRole('link', { name: 'Download last 1 MiB of .command.out' })).toHaveText('Download last 1 MiB');
});

test("resources columns show 'near limit' as text", async ({ page }, info) => {
  await mockFailed(page);
  await page.goto(`/runs/${RUN}?tab=tasks`);
  if (info.project.name === 'phone') {
    await expect(page.getByText('attempt 1 · asked 8 GB · peak 8 GB, near limit · limit 8 h')).toBeVisible();
  } else {
    const row = page.getByRole('table', { name: 'Tasks' }).getByRole('row').nth(1);
    await expect(row.getByRole('cell').nth(7)).toHaveText('8 GB near limit');
    await expect(row.getByText('near limit')).toHaveCSS('white-space', 'nowrap');
  }
});

// P1 Task 35: each job's SLURM request and efficiency, and the By process view, on Task 34's
// fields (route mocks in the shapes of packages/spectio-server/openapi/0.0.1.json).
const SLURM_TASK = {
  ...FAILED_TASK,
  slurm: {
    request: { partition: 'htc', account: null, qos: null, cpus: 6, mem_bytes: 8 * GIB, mem_per_cpu_bytes: null, time_limit_s: 8 * 3600, gres: null, constraint: null, nodes: null, tasks: null },
    allocated: { partition: 'htc-el8', account: 'demo', qos: 'normal', ncpus: 6, req_mem_bytes: 8 * GIB, time_limit_s: 8 * 3600, alloc_tres: 'cpu=6,mem=8G,node=1', nnodes: 1 },
    custom_options: true,
  },
  efficiency: { cpu: 0.69, mem: 1.0, elapsed_s: 360, peak_rss_bytes: 8 * GIB, state: 'available', source: 'sacct', reason: null },
};
const PROC_EFFICIENCY = {
  jobs: { done: 24, total: 25 }, measured: 24, pending_accounting: 0, cpu_mean: 0.34, cpu_max: 0.41, mem_mean: 0.03, mem_max: 0.05,
  requested: { cpus: 6, mem_bytes: 8 * GIB, time_limit_s: 8 * 3600, varies: false }, used: { peak_rss_bytes_max: 0.4 * GIB, elapsed_s_max: 360 },
};

test("the job sheet shows the SLURM request, 'Custom sbatch options set' and efficiency from sacct", async ({ page }) => {
  await mockFailed(page);
  await page.route(`**/api/v1/runs/${RUN}/tasks?*`, (r) => r.fulfill(json({ items: [SLURM_TASK], next: null })));
  await page.goto(`/runs/${RUN}?tab=tasks`);
  await page.getByRole('button', { name: 'Files of SUBREAD_FEATURECOUNTS (S19), attempt 1' }).click();
  const sheet = page.getByRole('dialog', { name: 'SUBREAD_FEATURECOUNTS (S19)' });
  const slurm = sheet.getByRole('region', { name: 'SLURM' });
  await expect(slurm.getByText('differs from the request')).toBeVisible();
  await expect(slurm.getByText('Custom sbatch options set')).toBeVisible();
  await expect(sheet.getByRole('region', { name: 'Efficiency' }).getByText(/from sacct/)).toBeVisible();
});

test('By process is a tab button; the waste line names the process', async ({ page }, info) => {
  await mockFailed(page);
  await page.route(`**/api/v1/runs/${RUN}/processes`, (r) =>
    r.fulfill(json({ items: [{ process: PROC, stage_id: null, counts: { succeeded: 24, failed: 1 }, retries: 0, status: 'failed', efficiency: PROC_EFFICIENCY }] })));
  await page.goto(`/runs/${RUN}?tab=tasks`);
  const tab = page.getByRole('tab', { name: 'By process' });
  expect(await tab.evaluate((e) => e.tagName)).toBe('BUTTON');
  await tab.click();
  await expect(page.getByText('24 tasks of SUBREAD_FEATURECOUNTS used under 25 % of their memory.')).toBeVisible();
  if (info.project.name === 'phone') {
    await expect(page.getByRole('combobox', { name: 'Sort by' })).toBeVisible();
  } else {
    await expect(page.getByRole('button', { name: 'Sort by CPU eff. mean' })).toBeVisible();
  }
  await page.getByRole('button', { name: `Show the tasks of process ${PROC}` }).click();
  await expect(page.getByRole('tab', { name: 'Task list' })).toHaveAttribute('aria-selected', 'true');
});

test("the Copy items are in the shared header's More actions on every tab and state, and announce 'Copied'", async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await mockFailed(page);
  for (const tab of ['', '?tab=tasks', '?tab=parameters', '?tab=logs']) {
    await page.goto(`/runs/${RUN}${tab}`);
    await expect(page.locator('header').getByRole('button', { name: 'More actions', exact: true })).toBeVisible();
  }
  await page.locator('header').getByRole('button', { name: 'More actions', exact: true }).click();
  // the menu stays in the viewport, on the phone too (UI-09)
  const menu = page.getByRole('menu');
  const box = (await menu.boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width);
  await menu.getByRole('menuitem', { name: 'Copy run ID' }).click();
  // The header holds the Copy status and, on the desktop, the Facts region's own status line.
  await expect(page.locator('header').getByRole('status').filter({ hasText: 'Copied' })).toHaveText('Copied the run ID');
});

test('Launch: a wrong value shows its error on the field; each row says required or optional', async ({ page }) => {
  await page.route('**/api/v1/workflows:inspect*', (r) => r.fulfill(json({
    location: '/data/rnaseq', revision: null, engine: 'nextflow', engine_files: ['main.nf'], name: 'rnaseq', version: '3.27.0',
    engine_version: '26.10.4', engine_versions: { nextflow: '26.10.4' }, schema_source: 'nextflow_schema.json', profiles: ['test'],
    schema: { type: 'object', required: ['input'], properties: {
      input: { type: 'string', pattern: '\\.csv$' }, depth: { type: 'integer', minimum: 1, maximum: 9, default: 3 } } },
  })));
  await page.goto('/launch');
  await page.getByRole('textbox', { name: /^Pipeline/ }).fill('/data/rnaseq');
  await page.getByRole('button', { name: 'Load', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'input (required)' })).toBeVisible();
  const depth = page.getByRole('textbox', { name: 'depth (optional)' });
  await depth.fill('12');
  await expect(depth).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText('Must be at most 9.', { exact: true })).toBeVisible(); // Before Launch says it too (FU-P3-86h)
  await expect(page.getByRole('button', { name: 'Launch', exact: true }).last()).toHaveAttribute('aria-disabled', 'true');
});

// P1 Task 32 part two: Resume, Copy to a new launch, results and reports, on Tasks 30 and 31's
// routes, answered by route mocks.
const CHILD = 'run_01JBC6Q4ZK7M8N2P3R5S7T9C2D';

/** Opens the run header's Facts when they are folded (the phone folds them, MLiteRunDetail). */
async function openFacts(page: Page) {
  const button = page.getByRole('region', { name: 'Facts' }).locator('.sp-fold-btn');
  if ((await button.getAttribute('aria-expanded')) === 'false') await button.click();
}

test('Resume asks, creates a child, and both runs link to each other', async ({ page }) => {
  await mockFailed(page, { actions: { resume: { allowed: true, reason: null } } });
  const child = mockRun({ id: CHILD, name: 'rnaseq-mock-T9C2D', state: 'queued', started_at: null, parent_run_id: RUN });
  let posted: unknown = null;
  await page.route(`**/api/v1/runs/${RUN}:relaunch`, (r) => {
    posted = r.request().postDataJSON();
    return r.fulfill({ ...json(child), status: 201 });
  });
  await page.route(`**/api/v1/runs/${CHILD}`, (r) => r.fulfill(json(child)));
  await page.route(`**/api/v1/runs/${CHILD}/stages`, (r) => r.fulfill(json({ items: [] })));
  await page.route(`**/api/v1/runs/${CHILD}/processes`, (r) => r.fulfill(json({ items: [] })));
  await page.goto(`/runs/${RUN}`);
  const resume = page.locator('header').getByRole('button', { name: 'Resume', exact: true });
  await resume.click();
  const dialog = page.getByRole('dialog', { name: 'Resume this run?' });
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  await expect(dialog).toContainText('Nextflow runs again with -resume and reuses the 24 tasks that finished. This run stays Failed.');
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(resume).toBeFocused();

  await resume.click();
  await dialog.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/runs/${CHILD}$`));
  expect(posted).toEqual({ mode: 'resume' });
  await openFacts(page);
  await expect(page.getByRole('region', { name: 'Facts' }).getByRole('link', { name: 'run 7T9V1W' })).toHaveAttribute('href', `/runs/${RUN}`);

  // the parent, now with its child
  await page.unroute(`**/api/v1/runs/${RUN}`);
  await mockFailed(page, { actions: { resume: { allowed: false, reason: 'resume_in_progress' } }, resumed_as: [{ id: CHILD, name: 'rnaseq-mock-T9C2D', state: 'running' }] });
  await page.goto(`/runs/${RUN}`);
  await openFacts(page);
  await expect(page.getByRole('region', { name: 'Facts' }).getByRole('link', { name: 'rnaseq-mock-T9C2D · Running' })).toHaveAttribute('href', `/runs/${CHILD}`);
  await expect(resume).toHaveAccessibleDescription('A resume of this run is already running: rnaseq-mock-T9C2D.');
});

test('a refused Resume stays visible, aria-disabled, with its reason as text', async ({ page }) => {
  await mockFailed(page, {
    head: { session: `spectio-${RUN}`, node: 'login2', alive: false, exit_code: 1 },
    actions: { resume: { allowed: false, reason: 'head_unverified' } },
  });
  await page.goto(`/runs/${RUN}`);
  const resume = page.locator('header').getByRole('button', { name: 'Resume', exact: true });
  await expect(resume).toHaveAttribute('aria-disabled', 'true');
  const why = 'The head may still be running on login2, and Spectio cannot check it from login1. Resume when it has ended.';
  await expect(resume).toHaveAccessibleDescription(why);
  await expect(page.locator('header').getByText(why)).toBeVisible();
  await resume.focus(); // still reachable by keyboard; Enter opens nothing
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('Copy to a new launch opens the form prefilled with the non-default values listed', async ({ page }) => {
  await mockFailed(page);
  await page.route(`**/api/v1/runs/${RUN}:launch-template`, (r) => r.fulfill(json({
    workflow: { location: '/g/demo-lab/pipelines/rnaseq', revision: null, engine: 'nextflow' },
    profiles: ['test'],
    params: { input: 'samplesheet.csv', outdir: '/g/demo-lab/rnaseq/a', depth: 3, custom_config_base: '/g/shared/configs' },
    non_default: ['input', 'outdir', 'custom_config_base'],
    code_loading: [{ field: 'params.custom_config_base', value: '/g/shared/configs', writable_by_others: true }],
  })));
  await page.route('**/api/v1/workflows:inspect*', (r) => r.fulfill(json({
    location: '/g/demo-lab/pipelines/rnaseq', revision: null, engine: 'nextflow', engine_files: ['main.nf'], name: 'rnaseq', version: '3.27.0',
    engine_version: '26.10.4', engine_versions: { nextflow: '26.10.4' }, schema_source: 'nextflow_schema.json', profiles: ['test'],
    schema: { type: 'object', required: ['input'], properties: {
      input: { type: 'string' }, outdir: { type: 'string', default: 'results' }, depth: { type: 'integer', default: 3 },
      custom_config_base: { type: 'string' } } },
  })));
  await page.goto(`/runs/${RUN}`);
  // a failed run's primary is Resume: Copy to a new launch is in More actions (UI-09)
  await page.locator('header').getByRole('button', { name: 'More actions', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Copy to a new launch' }).click();
  await expect(page).toHaveURL(new RegExp(`/launch\\?from=${RUN}$`));
  await expect(page.getByText(
    "Prefilled from rnaseq-mock (7T9V1W): 3 values differ from the pipeline's defaults: input, outdir, custom_config_base.",
  )).toBeVisible();
  await expect(page.getByRole('textbox', { name: /^Pipeline/ })).toHaveValue('/g/demo-lab/pipelines/rnaseq');
  await expect(page.getByRole('textbox', { name: 'input (required)' })).toHaveValue('samplesheet.csv');
  await expect(page.getByRole('combobox', { name: 'Profile' })).toHaveValue('test');
  await expect(page.getByText("Warning: same as rnaseq-mock. Change it to keep the two runs' results apart.")).toBeVisible();
  await expect(page.getByText('custom_config_base: loads code or configuration · writable by others')).toBeVisible();
  await page.getByRole('button', { name: 'Clear and start empty' }).click();
  await expect(page).toHaveURL(/\/launch$/);
  await expect(page.getByRole('textbox', { name: /^Pipeline/ })).toHaveValue('');
});

const RESULTS = '/g/demo-lab/rnaseq/2026-10-25';
const MQC = 'multiqc/multiqc_report.html';

async function mockResults(page: Page) {
  await mockFailed(page, { results_dir: RESULTS });
  const listing = (path: string, entries: object[]) => json({
    root: RESULTS, path, exists: true, truncated: false, entries,
    reports: [{ path: MQC, title: 'MultiQC report', group: 'multiqc' }, { path: 'fastqc/S01_fastqc.html', title: 'S01_fastqc', group: 'fastqc' }],
  });
  const mtime = '2026-10-31T08:42:00+00:00';
  await page.route(`**/api/v1/runs/${RUN}/results`, (r) => r.fulfill(listing('', [
    { name: 'fastqc', type: 'dir', size: null, mtime }, { name: 'multiqc', type: 'dir', size: null, mtime },
  ])));
  await page.route(`**/api/v1/runs/${RUN}/results?path=fastqc`, (r) => r.fulfill(listing('fastqc', [
    { name: 'S01_fastqc.html', type: 'file', size: 626688, mtime }, { name: 'versions.yml', type: 'file', size: 84, mtime },
    { name: 'latest', type: 'link_outside', size: null, mtime },
  ])));
  await page.route(`**/api/v1/runs/${RUN}/results/raw/**`, (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>r</title><h1>A report from the pipeline</h1>' }));
}

test("a report opens in the viewer with its 'Untrusted report' banner", async ({ page }) => {
  await mockResults(page);
  await page.goto(`/runs/${RUN}`);
  const results = page.getByRole('region', { name: 'Results and reports' });
  await expect(results.getByText(RESULTS)).toBeVisible();
  await results.getByRole('link', { name: 'Open the MultiQC report' }).click();
  await expect(page).toHaveURL(new RegExp(`/runs/${RUN}/report\\?path=`));
  await expect(page.getByText(`Untrusted report: ${MQC}`)).toBeVisible();
  const frame = page.frameLocator('iframe[title$="sandboxed"]');
  await expect(frame.getByRole('heading', { name: 'A report from the pipeline' })).toBeVisible();
  await expect(page.locator('iframe[title$="sandboxed"]')).toHaveAttribute('sandbox', 'allow-scripts allow-downloads');
});

test('the results browser shows one folder; an HTML file opens in the viewer, another opens its preview', async ({ page }, info) => {
  await mockResults(page);
  await page.goto(`/runs/${RUN}/results?path=fastqc`);
  await expect(page.getByRole('heading', { level: 1, name: 'Results' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Folder' }).getByRole('link', { name: 'results' })).toBeVisible();
  const phone = info.project.name === 'phone';
  const table = page.getByRole(phone ? 'list' : 'table', { name: 'fastqc' });
  // FU-P3-85d: a file's name opens its preview; on the desktop, Download is the row's icon button.
  await expect(table.getByRole('link', { name: /^versions\.yml/ })).toHaveAttribute('href', `/runs/${RUN}/results/file?path=${encodeURIComponent('fastqc/versions.yml')}`);
  if (!phone) {
    await expect(table.getByRole('link', { name: 'Download versions.yml' })).toHaveAttribute('href', `/api/v1/runs/${RUN}/results/raw/fastqc/versions.yml?download=true`);
  }
  await expect(table.getByText('not followed')).toBeVisible();
  await table.getByRole('link', { name: /^S01_fastqc\.html/ }).click();
  await expect(page.getByText('Untrusted report: fastqc/S01_fastqc.html')).toBeVisible();
});

// RC1 gaps D-07, Q-02, N-02, X-16, X-03 and U-02 (docs: RC1 acceptance §18): what a user does on a
// real, ended run: its logs, the search, the bell, the pin, Resume, and the profile's Sign out.

/** A happy run that has ended, and its name (what the list, the search and the bell call it). */
async function endedRun(request: APIRequestContext): Promise<{ id: string; name: string }> {
  const id = await launch(request, ['test']);
  await reach(request, id, ['succeeded']);
  return { id, name: (await (await request.get(`/api/v1/runs/${id}`)).json()).name };
}

const escapeRe = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

test('the Logs tab of a real run shows the engine log and downloads it', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const { id, name } = await endedRun(request);
  await page.goto(`/runs/${id}`);
  await page.getByRole('tab', { name: 'Logs' }).click();
  const logs = page.getByRole('region', { name: 'Logs' });
  // the file the engine log is read from, then its lines (the last 64 KiB of .nextflow.log)
  await expect(logs.getByRole('code', { name: 'File' })).toContainText(`/${id}/launch/.nextflow.log`);
  const lines = logs.locator('pre[aria-label="Engine log"]');
  await expect(lines).toContainText(/nextflow/i);
  await expect(logs.getByRole('group', { name: 'Show lines' }).getByRole('button', { name: /^All/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(logs.getByText("Nextflow's log of this run · last 64 KiB")).toBeVisible();
  // Download saves what the viewer shows
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    logs.getByRole('button', { name: 'Download last 64 KiB' }).click(),
  ]);
  expect(download.suggestedFilename()).toBe(`${name}-engine.log`);
  const saved = readFileSync((await download.path())!, 'utf8');
  expect(saved).toMatch(/nextflow/i);
  expect(await lines.innerText()).toContain(saved.split('\n').find((line) => line.trim() !== '')!.trim());
});

test('Ctrl+K finds a run by its short ID and Enter opens it', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const { id, name } = await endedRun(request);
  await page.goto('/runs');
  await page.keyboard.press('Control+K');
  const dialog = page.getByRole('dialog', { name: 'Search' });
  await expect(dialog).toBeVisible();
  const input = dialog.getByRole('searchbox', { name: 'Search runs, pipelines and pages' });
  await expect(input).toBeFocused();
  await input.fill(id.slice(-6)); // the short ID the UI shows: the last six characters
  // wait for the row before Enter: it opens the first result once there is one
  await expect(dialog.getByRole('button', { name: new RegExp(`^Run ${escapeRe(name)}, Succeeded, Nextflow,`) })).toBeVisible();
  await input.press('Enter');
  await expect(page).toHaveURL(new RegExp(`/runs/${id}$`));
  await expect(dialog).toBeHidden();
});

test('an ended run appears in the bell and opens from it', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(180_000);
  const { id, name } = await endedRun(request);
  await page.goto('/runs');
  const bell = page.getByRole('button', { name: /^Notifications, \d+ unread$/ });
  await expect(bell).toHaveAccessibleName(/^Notifications, [1-9]\d* unread$/); // the run that just ended is unread
  await bell.click();
  const row = page.getByRole('link', { name: new RegExp(`^${escapeRe(name)}, Succeeded, Nextflow, .*unread$`) });
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/runs/${id}$`));
  // opening a run does not read it; Mark all as read does
  await bell.click();
  await page.getByRole('button', { name: 'Mark all as read' }).click();
  await expect(bell).toHaveAccessibleName('Notifications, 0 unread');
  await expect(page.getByRole('link', { name: new RegExp(`^${escapeRe(name)}, Succeeded, Nextflow, [^,]*$`) })).toBeVisible(); // still listed, now read
});

test('pin a run; it stays first after a reload', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.setTimeout(240_000);
  const { id, name } = await endedRun(request);
  const newer = await launch(request, ['test']); // created after the pinned run: it comes first until the pin
  const origin = new URL(target.url).origin;
  try {
    await page.goto('/runs');
    const pin = page.getByRole('button', { name: `Pin run ${name}`, exact: true });
    await expect(pin).toHaveAttribute('aria-pressed', 'false');
    await pin.click();
    await expect(pin).toHaveAttribute('aria-pressed', 'true');
    await page.reload();
    await expect(pin).toHaveAttribute('aria-pressed', 'true');
    // of every Pin button on the page, the pinned run's is the topmost
    await expect
      .poll(async () => {
        const tops = await page.getByRole('button', { name: /^Pin run / }).evaluateAll((els) =>
          els.map((el) => ({ label: el.getAttribute('aria-label'), y: el.getBoundingClientRect().y })));
        return tops.sort((a, b) => a.y - b.y)[0]?.label;
      })
      .toBe(`Pin run ${name}`);
  } finally {
    await request.patch(`/api/v1/runs/${id}`, { headers: { Origin: origin }, data: { pinned: false } });
    await request.post(`/api/v1/runs/${newer}:cancel`, { headers: { Origin: origin } }); // it may have ended already
  }
});

test('resume a real failed run: the child caches the tasks that succeeded', async ({ page, request }) => {
  test.skip(!ENGINES, NEEDS_ENGINES);
  test.skip(!isLocal(target.url), NEEDS_LOCAL);
  test.setTimeout(300_000);
  // A copy of the pipeline whose injected failure ends once a marker file exists: the user's fix.
  // The script text is the same in both runs, so the tasks that succeeded keep their cache.
  const copy = mkdtempSync(join(tmpdir(), 'spectio-e2e-resume-'));
  cpSync(SYNTHETIC, copy, { recursive: true, dereference: true });
  const marker = join(copy, 'FIXED');
  const main = join(copy, 'nextflow', 'main.nf');
  const hook = '"synth.py fail ${params.fail_mode}';
  const source = readFileSync(main, 'utf8');
  expect(source).toContain(hook);
  writeFileSync(main, source.replace(hook, () => `"test -e '${marker}' || synth.py fail \${params.fail_mode}`));

  // the scenario tool_error_then_fixed_resume: COMPARE for treatA exits 1 and is not retried
  const failed = await launch(request, ['test'], { fail_mode: 'exit', fail_process: 'COMPARE', fail_sample: 'treatA' }, 'nextflow', join(copy, 'nextflow'));
  await reach(request, failed, ['failed']);
  writeFileSync(marker, 'fixed\n');

  await page.goto(`/runs/${failed}`);
  await expect(page.locator('header .sp-state')).toHaveText('Failed');
  const resume = page.locator('header').getByRole('button', { name: 'Resume', exact: true });
  await expect(resume).not.toHaveAttribute('aria-disabled', 'true');
  await resume.click();
  const dialog = page.getByRole('dialog', { name: 'Resume this run?' });
  await expect(dialog).toContainText('Nextflow runs again with -resume and reuses the');
  await dialog.getByRole('button', { name: 'Resume', exact: true }).click();

  // the child is a new run, Succeeded, and reused what the first run finished (cached_min 50 in the scenario)
  await expect(page).toHaveURL(/\/runs\/run_[0-9A-Z]{26}$/);
  const child = new URL(page.url()).pathname.split('/').pop()!;
  expect(child).not.toBe(failed);
  await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 200_000 });
  const cached = await page.getByRole('list', { name: 'Tasks by state' }).getByText(/^\d+ cached$/).innerText();
  expect(Number(cached.split(' ')[0])).toBeGreaterThanOrEqual(50);
  expect((await (await request.get(`/api/v1/runs/${child}`)).json()).parent_run_id).toBe(failed);
  expect((await (await request.get(`/api/v1/runs/${failed}`)).json()).state).toBe('failed'); // the parent stays Failed
});

test('the profile names the account and Sign out ends this session', async ({ browser, request }) => {
  test.skip(!isLocal(target.url), NEEDS_LOCAL);
  // its own session, from its own link: signing out must not end the one the other tests share
  const context = await bare(browser);
  try {
    const page = await context.newPage();
    await openLink(page, newTicket(target.url));
    await expect(page).toHaveURL(new URL('/', target.url).href);
    const me = await (await context.request.get('/api/v1/me')).json();

    await page.goto('/profile');
    await expect(page.getByRole('heading', { level: 1, name: 'Profile' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Who the server runs as' })).toContainText(me.principal.user);
    const paths = page.getByRole('region', { name: 'Config paths' });
    await expect(paths).toContainText(me.paths.config_file);
    await expect(paths).toContainText(me.paths.data_dir);
    await expect(paths.getByRole('button', { name: 'Copy the config file path' })).toBeVisible();

    await page.getByRole('button', { name: 'Sign out of this session' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Signed out of this session.' })).toBeVisible();
    expect((await context.cookies()).map((c) => c.name)).not.toContain(sessionCookie(target.url));
    // the next request meets the sign-in answer, not the app
    const next = await page.goto('/runs');
    expect(next!.status()).toBe(401);
    await expect(page.locator('body')).toContainText('Sign-in required');
    expect((await context.request.get('/api/v1/me')).status()).toBe(401);
    // the session of the other tests is still good
    expect((await request.get('/api/v1/me')).status()).toBe(200);
  } finally {
    await context.close();
  }
});
