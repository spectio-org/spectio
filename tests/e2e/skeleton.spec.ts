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
// The run tests/e2e/seed_stages.py writes (serve-local.sh --seed-stages): P1 Task 27.
const SEEDED = 'run_01K8T27SEEDED0000000000000';
const IS_SEEDED = process.env.SPECTIO_E2E_SEEDED === '1';
const NEEDS_SEED = 'needs the seeded rnaseq run: serve-local.sh --seed-stages and SPECTIO_E2E_SEEDED=1';
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
    summary: { tasks: { done: 24, total: 27, failed: 0, cached: 0 }, last_failure: null, stage_mode: 'quarters' },
    params: {}, stages_note: null, ...over,
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

async function mockFailed(page: Page) {
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

test("the Copy menu is in the shared header on every tab and state, and announces 'Copied'", async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await mockFailed(page);
  for (const tab of ['', '?tab=tasks', '?tab=parameters', '?tab=logs']) {
    await page.goto(`/runs/${RUN}${tab}`);
    await expect(page.locator('header').getByRole('button', { name: 'Copy', exact: true })).toBeVisible();
  }
  await page.locator('header').getByRole('button', { name: 'Copy', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Run ID' }).click();
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
  await expect(page.getByText('Must be at most 9.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Launch', exact: true }).last()).toHaveAttribute('aria-disabled', 'true');
});

// The rest of Task 32's plan waits for its routes (Thomas's order of 2026-10-31 skips Tasks 30 and 31).
test('Resume asks, creates a child, and both runs link to each other', async () => {
  test.fixme(true, 'TODO(P1 Task 30): POST /runs/{id}:resume is not built');
});
test('a refused Resume stays visible, aria-disabled, with its reason as text', async () => {
  test.fixme(true, 'TODO(P1 Task 30): actions.resume is not served');
});
test('Copy to a new launch opens the form prefilled with the non-default values listed', async () => {
  test.fixme(true, 'TODO(P1 Task 30): GET /runs/{id}:launch-template is not built');
});
test("a report opens in the viewer with its 'Untrusted report' banner", async () => {
  test.fixme(true, 'TODO(P1 Task 31): results and reports are not served');
});
