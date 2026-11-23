import { test, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readdirSync, rmdirSync, rmSync, statSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import { isLocal, resolveTarget } from './base-url';

// A Nextflow run started by hand while `spectio serve` runs (RC1 T-04; architecture §13.8, ui-spec §6,
// docs/usage/runs-from-a-terminal.md), against a real server on this machine (the CI job e2e-local):
//   bash tests/e2e/serve-local.sh --port 8765 &
//   SPECTIO_E2E_BASE_URL=http://127.0.0.1:8765 SPECTIO_E2E_ENGINES=1 npx playwright test terminal.spec.ts --project desktop
// The test runs the synthetic pipeline with engine-bridges/nf-spectio/tests/run_local.sh --terminal: no
// SPECTIO_* variable, the bridge named by NXF_PLUGINS_DEFAULT, in a launch directory of its own. The
// bridge writes its pointer to ~/.spectio/observed/ of the user, which the server scans: the server
// and this test must share a home, so it is a server on this machine only. If ~/.spectio does not
// exist the test makes it (mode 0700, as the bridge requires) and removes what it made.

const target = resolveTarget(process.env);
const ENGINES = process.env.SPECTIO_E2E_ENGINES === '1';
const REPO = join(__dirname, '..', '..');
const RUN_LOCAL = join(REPO, 'engine-bridges', 'nf-spectio', 'tests', 'run_local.sh');

test.skip(target.serveStatic, 'needs a Spectio server: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');
test.skip(!target.serveStatic && !isLocal(target.url), "the bridge writes a pointer in this user's home: a local server only");
test.skip(!ENGINES, 'needs Nextflow: set SPECTIO_E2E_ENGINES=1 (CI job e2e-local)');

const RUN_FILE = /^(run_[0-9A-Z]{26})-nf-spectio-0001\.jsonl$/;

/** The run ID the bridge made, from the name of its spool file in the launch directory. */
function runIdOf(launchDir: string): string | null {
  try {
    for (const name of readdirSync(join(launchDir, '.spectio', 'events'))) {
      const found = RUN_FILE.exec(name);
      if (found) return found[1];
    }
  } catch {
    // the bridge has not started yet
  }
  return null;
}

test('a Nextflow run started by hand appears with From a terminal and ends', async ({ page, request }) => {
  test.setTimeout(300_000);
  const spectioHome = join(homedir(), '.spectio');
  const madeHome = !existsSync(spectioHome);
  test.skip(!madeHome && (statSync(spectioHome).mode & 0o077) !== 0, `${spectioHome} is not private (mode 0700): the server would not read its pointers`);
  if (madeHome) mkdirSync(spectioHome, { mode: 0o700 });

  const scratch = mkdtempSync(join(tmpdir(), 'spectio-e2e-'));
  chmodSync(scratch, 0o700);
  const launchDir = join(scratch, 'term-run');
  mkdirSync(launchDir, { mode: 0o700 });
  let runId: string | null = null;
  try {
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('SPECTIO_')));
    env.NEXTFLOW = process.env.SPECTIO_ENGINES_NEXTFLOW_CMD || 'nextflow';
    let output = '';
    const child = spawn('bash', [RUN_LOCAL, '--terminal', launchDir], { env: env as NodeJS.ProcessEnv, stdio: ['ignore', 'pipe', 'pipe'] });
    child.stdout.on('data', (chunk) => (output += chunk));
    child.stderr.on('data', (chunk) => (output += chunk));
    const exited = new Promise<number | null>((done) => child.on('close', done));

    // the bridge made a run ID and wrote its spool; the server found the pointer and indexed the run
    await expect.poll(() => (runId = runIdOf(launchDir)), { timeout: 120_000, message: 'the bridge wrote no spool' }).not.toBeNull();
    await expect
      .poll(async () => (await request.get(`/api/v1/runs/${runId}`)).status(), { timeout: 60_000, message: 'the server did not find the pointer' })
      .toBe(200);
    const name = `${basename(launchDir)}-${runId!.slice(-6)}`; // the run is named after its launch directory

    // the list: the run, with the chip
    await page.goto('/runs');
    const link = page.getByRole('link', { name: `Open run ${name}`, exact: true });
    await expect(link).toBeVisible();
    const row = page.getByRole('row').filter({ has: link });
    await expect(row.getByText('From a terminal')).toBeVisible();

    // the detail follows it to its end, with no action on it: Spectio only watches
    await link.click();
    await expect(page).toHaveURL(new RegExp(`/runs/${runId}$`));
    await expect(page.locator('header .sp-state')).toHaveText('Succeeded', { timeout: 150_000 });
    await expect(page.getByText('65 / 65 tasks')).toBeVisible();
    await expect(page.getByRole('button', { name: /^Cancel/ })).toHaveCount(0);
    expect((await (await request.get(`/api/v1/runs/${runId}`)).json()).origin).toBe('cli-observed');

    expect(await exited, output.slice(-2000)).toBe(0);
  } finally {
    rmSync(scratch, { recursive: true, force: true });
    // the pointer: moved to ended/ by the server when the run ended, or still in observed/
    const observed = join(spectioHome, 'observed');
    for (const dir of [observed, join(observed, 'ended')]) {
      if (runId) rmSync(join(dir, `${runId}.json`), { force: true });
    }
    if (madeHome) {
      for (const dir of [join(observed, 'ended'), observed, spectioHome]) {
        try {
          rmdirSync(dir); // only while empty: a file the server or another run left stays
        } catch {
          // not empty, or not there
        }
      }
    }
  }
});
