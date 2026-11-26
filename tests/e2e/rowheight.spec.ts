import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { resolveTarget } from './base-url';

// #353: the runs list keeps one row height whatever the names, and no cell clips its content.
// The list is mocked, so the spec needs a built web/ and a browser, not a Spectio server's data:
// the screens are measured as Chromium lays them out (jsdom has no layout).

const target = resolveTarget(process.env);
test.skip(target.serveStatic, 'needs the built screens: SPECTIO_E2E_BASE_URL (tests/e2e/serve-local.sh)');

const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
const LONG = 'a-very-long-run-name-that-goes-on-and-on-well-past-two-lines-of-the-name-column-' + 'x'.repeat(40);

const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString();

function run(n: number, over: Record<string, unknown> = {}) {
  return {
    id: `run_01JBC6Q4ZK7M8N2P3R5S7T9V${String(n).padStart(2, '0')}`, name: `run-${n}`, state: 'running', origin: 'ui',
    created_at: ago(n * 60), started_at: ago(n * 60), ended_at: null,
    workflow: { engine: 'nextflow', engine_version: '26.10.4', location: '/g/demo-lab/pipelines/rnaseq', name: 'nf-core/rnaseq', version: '3.27.0', main_script: null },
    profiles: ['test'], failure: null, target: null,
    head: { session: null, node: 'login1', alive: true, exit_code: null, checked: true },
    task_counts: { succeeded: 24, running: 3 },
    summary: { tasks: { done: 24, total: 27, failed: 2, cached: 0 }, last_failure: null, stage_mode: 'quarters' },
    ...over,
  };
}
const rule = { kind: 'rule', name: 'a_rule_with_a_name_that_is_much_too_long_for_the_workflow_column_to_hold', version: null, hash: null, source: null, path: null, flag: 'target', more: 2, checksum_changed: true };
const module_ = { kind: 'module', name: 'nf-core/fastqc', version: '0.0.0-6d1763b', hash: 'a'.repeat(64), source: 'registry', path: null, flag: null, more: 0, checksum_changed: true };
const RUNS = [
  run(1),
  run(2, { name: LONG, origin: 'cli-observed', pinned: true }),
  run(3, { name: null, origin: 'cli-observed', workflow: { engine: 'snakemake', engine_version: '9.2', location: '/g/lab/' + 'deep/'.repeat(20) + 'Snakefile', name: null, version: null, main_script: null }, target: rule }),
  run(4, { name: 'two words', workflow: { engine: 'nextflow', engine_version: '26', location: '/x', name: 'some-organisation/' + 'a-pipeline-with-a-very-long-name-'.repeat(3), version: 'v10.20.30-rc1+build.12345', main_script: null }, target: module_ }),
  run(5, { name: LONG, origin: 'cli-observed', state: 'failed', ended_at: ago(1), workflow: { engine: 'nextflow', engine_version: '26', location: '/x', name: 'nf-core/' + 'p'.repeat(90), version: '3.27.0', main_script: null }, target: rule }),
];

async function open(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.route('**/api/v1/**', (r) => r.fulfill(json({})));
  await page.route('**/api/v1/version', (r) => r.fulfill(json({ version: '0.0.1', node: 'login1', runs_root: '/runs', account: 'me', executor: 'tmux', features: { single_target: true } })));
  await page.route('**/api/v1/me/notifications*', (r) => r.fulfill(json({ items: [], unread: 0, read_up_to: null })));
  await page.route('**/api/v1/runs:summary*', (r) => r.fulfill(json({ groups: [{ key: 'running', count: 3 }, { key: 'failed', count: 1 }] })));
  await page.route('**/api/v1/runs?*', (r) => r.fulfill(json({ items: RUNS, next: null })));
  await page.goto('/runs');
  await expect(page.getByRole('grid', { name: 'Runs' })).toBeVisible();
  await expect(page.locator('.ag-row')).toHaveCount(RUNS.length);
}

for (const width of [1440, 1280]) {
  test(`one row height and no clipped cell at ${width} px`, async ({ page }, info) => {
    await open(page, width);
    const m = await page.evaluate(() => {
      const rows = [...document.querySelectorAll<HTMLElement>('.ag-row')];
      const rects = (el: HTMLElement) => el.getBoundingClientRect();
      return {
        rows: rows.map((r) => r.getBoundingClientRect().height),
        cells: rows.flatMap((r, i) =>
          [...r.querySelectorAll<HTMLElement>('.ag-cell')].map((c) => {
            const box = rects(c);
            const escaped = [...c.querySelectorAll<HTMLElement>('.sp-chip, .sp-id, .sp-pin, .sp-target-to')].filter((e) => {
              const b = rects(e);
              return b.bottom > box.bottom + 0.5 || b.right > box.right + 0.5 || b.top < box.top - 0.5;
            }).length;
            const kids = [...c.children].map((k) => k.getBoundingClientRect());
            const content = kids.length ? Math.max(...kids.map((k) => k.bottom)) - Math.min(...kids.map((k) => k.top)) : 0;
            return { row: i, col: c.getAttribute('col-id'), text: c.innerText.slice(0, 30), content: Math.round(content * 10) / 10, sh: c.scrollHeight, ch: c.clientHeight, sw: c.scrollWidth, cw: c.clientWidth, escaped };
          }),
        ),
      };
    });
    console.log(JSON.stringify({ width, rows: m.rows, tallest: m.cells.reduce((a, c) => (c.content > a.content ? c : a)), cells: m.cells.filter((c) => c.col === 'name' || c.col === 'workflow').map((c) => `${c.row}:${c.col}:${c.content}/${c.ch}`) }));
    const shot = process.env.SPECTIO_ROWH_SHOT;
    if (shot) {
      mkdirSync(dirname(shot), { recursive: true });
      await page.screenshot({ path: shot.replace('.png', `-${width}.png`) });
    }
    expect(new Set(m.rows).size, `row heights ${m.rows}`).toBe(1);
    for (const c of m.cells) {
      expect(c.sh, `${JSON.stringify(c)}`).toBeLessThanOrEqual(c.ch);
      expect(c.sw, `${JSON.stringify(c)}`).toBeLessThanOrEqual(c.cw);
      expect(c.escaped, `${JSON.stringify(c)}`).toBe(0);
    }
    info.annotations.push({ type: 'row-height', description: String(m.rows[0]) });
  });
}

test('a clamped workflow name shows its full text, with the warning, on keyboard focus', async ({ page }) => {
  await open(page, 1440);
  const button = page.getByRole('button', { name: /^Copy workflow .*checksum changed/ }).first();
  await button.focus();
  const tip = page.getByRole('tooltip');
  await expect(tip).toContainText('checksum changed');
  await expect(tip).toContainText('→ rule');
});
