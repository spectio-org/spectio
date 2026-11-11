// Screens of single-target runs (#161, ui-spec 4.15): the web code of the checkout in a browser, the API mocked
// with demo data (`demo-lab`, `login1`, `/scratch/demo`), so no server, engine or cluster is needed.
//
//     (cd web && npx vite --port 5173 &)              # the dev server of the checkout
//     node tools/media/single_target_demo.js <out-dir> # writes seven PNGs at 1440 x 1000, device scale 2
//
// docs/assets/shots/app-single-target-*_light.webp are made from four of them (2, 3, 4 and 6; see
// docs/assets/media.yaml), each at 1440 wide: `convert <png> -resize 1440x -define webp:lossless=true -define webp:method=6 <webp>`.
// Env: SPECTIO_WEB_URL (default http://127.0.0.1:5173). Needs Node with `playwright` and Chromium.
const { chromium } = require("playwright");
const OUT = (process.argv[2] || "out").replace(/\/?$/, "/");
const BASE = process.env.SPECTIO_WEB_URL || "http://127.0.0.1:5173";
const NONE = { version: null, hash: null, source: null, path: null, flag: null, more: 0, checksum_changed: null };
const MOD = { ...NONE, kind: "module", name: "nf-core/fastqc", version: "0.0.0-6d1763b", source: "registry", hash: "b64b18ed9c41f0a2d7e6c3b5a8f1e0d2c4b6a8e0f2d4c6b8a0e2f4d6c8b0a2e4" };
const RULE = { ...NONE, kind: "rule", name: "qc_report", flag: "target" };
const VERSION = { version: "0.0.2", node: "login1", runs_root: "/scratch/demo/spectio-runs", account: "demo", executor: "slurm", features: { single_target: true } };
const ENV = { name: "slurm", label: "SLURM (from spectio init)", executor: "slurm", builtin: true, default: true, usable: true, unusable_reason: null, slurm: { partition: "htc", account: "mylab", time_min: null, mem_mib: null }, local: null, profiles: { nextflow: null, snakemake: null }, etag: '"slurm"' };
const RUNENV = { name: "slurm", label: "SLURM (from spectio init)", executor: "slurm", slurm: { partition: "htc", account: "mylab", time_min: null, mem_mib: null }, local: null, state: "recorded" };
const now = Date.now();
const iso = (minAgo) => new Date(now - minAgo * 60000).toISOString();
const base = (o) => ({
  origin: "ui", created_at: iso(14), started_at: iso(13), ended_at: null, profiles: [], environment: RUNENV, failure: null,
  head: { session: `spectio-${o.id}`, node: "login1", alive: true, exit_code: null, checked: true },
  summary: { tasks: { done: 0, total: 0, failed: 0, cached: 0, lower_bound: false }, last_failure: null, stage_mode: "quarters", open_checkpoints: [], dag_updates: 0 },
  ...o,
});
const NF = { engine: "nextflow", engine_version: "26.10.4", location: "nf-core/fastqc", name: "nf-core/fastqc", version: "0.0.0-6d1763b" };
const SMK = { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/synth-qc", name: "synth-qc", version: "1.2.0" };
const RUN_M = base({ id: "run_01JC2M0D7KE5N6KE6MD0M0D1AB", name: "fastqc-sampleA", state: "running", workflow: NF, target: MOD,
  task_counts: { succeeded: 2, running: 1 }, summary: { ...base({}).summary, tasks: { done: 2, total: 3, failed: 0, cached: 0, lower_bound: false } } });
const RUN_R = base({ id: "run_01JC2M0D7KE5N6KE6RVQC00000", name: "synth-qc-report", state: "succeeded", workflow: SMK, target: RULE, ended_at: iso(2),
  head: { session: `spectio-${"run_01JC2M0D7KE5N6KE6RVQC00000"}`, node: "login1", alive: false, exit_code: 0, checked: true },
  task_counts: { succeeded: 25 }, summary: { ...base({}).summary, tasks: { done: 25, total: 25, failed: 0, cached: 0, lower_bound: false } } });
const RUN_CLI = base({ id: "run_01JC2M0D7KE5N6KE6C7M0D2000", name: "fastqc-terminal", state: "succeeded", origin: "cli-observed", workflow: NF, ended_at: iso(60), created_at: iso(70), started_at: iso(70),
  target: { ...MOD, hash: "c0ffee11aa22bb33cc44dd55ee66ff7788990011aabbccddeeff001122334455", checksum_changed: true },
  head: { session: null, node: "login1", alive: false, exit_code: 0, checked: true }, environment: null,
  task_counts: { succeeded: 1 }, summary: { ...base({}).summary, tasks: { done: 1, total: 1, failed: 0, cached: 0 } } });
const RUN_P = base({ id: "run_01JC2M0D7KE5N6KE6WH0P10000", name: "rnaseq-cohort-3", state: "running", created_at: iso(40), started_at: iso(40),
  workflow: { engine: "nextflow", engine_version: "26.10.4", location: "/g/demo-lab/pipelines/rnaseq", name: "nf-core/rnaseq", version: "3.27.0" }, target: null, profiles: ["slurm"],
  task_counts: { succeeded: 120, running: 8, pending: 40 }, summary: { ...base({}).summary, tasks: { done: 120, total: 168, failed: 0, cached: 0 } } });
const DETAIL = (r, o = {}) => ({ ...r, params: {}, stages_note: null, failures: [], failures_total: 0, command: null, parent_run_id: null, resumed_as: [],
  actions: { resume: { allowed: false, reason: "running" } }, results_dir: null, engine_settings: { cleanup: null, notemp: null }, ...o });
const proc = (process, status, counts) => ({ process, stage_id: null, counts, retries: 0, status, is_checkpoint: false, lower_bound: false, pipeline_order: 0, efficiency: null });
const RES = { cpus: 2, memory_bytes: 4e9, time_s: 3600, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };
const task = (i, state, process = "FASTQC") => ({ id: `tsk_${i}`, process, tag: `sample${"ABC"[i]}`, name: `${process} (sample${"ABC"[i]})`, state, stage_id: null, attempt_n: 1, resources: RES });

const routes = {
  "/api/v1/version": VERSION,
  "/api/v1/environments": { items: [ENV], default: "slurm", file: { path: "/home/demo/.spectio/environments.toml", state: "ok", detail: null } },
  "/api/v1/catalog": { items: [], file: { path: "/home/demo/.spectio/catalog.toml", state: "missing", detail: null } },
  "/api/v1/runs:summary": { groups: [{ key: "running", count: 2 }, { key: "succeeded", count: 2 }] },
  "/api/v1/runs?target=any": { items: [RUN_M, RUN_R, RUN_CLI], next: null },
  "/api/v1/runs?": { items: [RUN_M, RUN_P, RUN_R, RUN_CLI], next: null },
  "/api/v1/runs": { items: [RUN_M, RUN_P, RUN_R, RUN_CLI], next: null },
  [`/api/v1/runs/${RUN_M.id}/processes`]: { items: [proc("FASTQC", "running", { succeeded: 2, running: 1 })] },
  [`/api/v1/runs/${RUN_M.id}/stages`]: { items: [] },
  [`/api/v1/runs/${RUN_M.id}/tasks`]: { items: [task(0, "succeeded"), task(1, "succeeded"), task(2, "running")], next: null },
  [`/api/v1/runs/${RUN_M.id}`]: DETAIL(RUN_M, { stages_note: "This run targets one module", params: { meta: { id: "sampleA", single_end: false }, reads: "/g/demo-lab/data/sampleA_R{1,2}.fq.gz" },
    command: { argv: [], text: "nextflow run … module run nf-core/fastqc -version 0.0.0-6d1763b -params-file .spectio/params.json" } }),
  [`/api/v1/runs/${RUN_R.id}/processes`]: { items: [proc("make_reads", "done", { succeeded: 12 }), proc("qc_stats", "done", { succeeded: 12 }), proc("qc_report", "done", { succeeded: 1 }),
    proc("merge_bams", "not_needed", {}), proc("call_variants", "not_needed", {}), proc("plot_summary", "not_needed", {}), proc("all", "not_needed", {})] },
  [`/api/v1/runs/${RUN_R.id}/stages`]: { items: [] },
  [`/api/v1/runs/${RUN_R.id}/tasks`]: { items: [], next: null },
  [`/api/v1/runs/${RUN_R.id}`]: DETAIL(RUN_R, { stages_note: "This run targets rule qc_report", actions: { resume: { allowed: false, reason: null } }, results_dir: null,
    command: { argv: [], text: "snakemake --directory /scratch/demo/spectio-runs/run_r qc_report --configfile .spectio/params.json --logger spectio" } }),
  [`/api/v1/runs/${RUN_CLI.id}/processes`]: { items: [proc("FASTQC", "done", { succeeded: 1 })] },
  [`/api/v1/runs/${RUN_CLI.id}/stages`]: { items: [] },
  [`/api/v1/runs/${RUN_CLI.id}/tasks`]: { items: [], next: null },
  [`/api/v1/runs/${RUN_CLI.id}`]: DETAIL(RUN_CLI, { stages_note: "This run targets one module", actions: { resume: { allowed: false, reason: null } } }),
  "/api/v1/workflows:inspect": { location: "/g/demo-lab/pipelines/synth-qc", revision: null, engine: "snakemake", engine_files: ["Snakefile"], name: "synth-qc", version: "1.2.0",
    engine_version: "9.27.1", engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" }, schema: null, schema_source: "none", profiles: [], params_file: null },
};
const FASTQC = { kind: "module", source: "registry", name: "nf-core/fastqc", version: "0.0.0-6d1763b", description: "Run FastQC on sequenced reads",
  inputs: [{ name: "meta", type: "map", description: "Groovy Map containing sample information, e.g. [ id:'sample1', single_end:false ]" },
           { name: "reads", type: "file", description: "List of input FastQ files of size 1 and 2 for single-end and paired-end data" }] };

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
  // the live stream, open and quiet
  await page.addInitScript(() => {
    window.EventSource = class { constructor() { this.readyState = 1; setTimeout(() => this.onopen && this.onopen(), 50); } addEventListener() {} removeEventListener() {} close() {} };
  });
  await page.route("**/api/v1/**", async (route) => {
    const u = new URL(route.request().url());
    const key = u.pathname + u.search;
    if (u.pathname === "/api/v1/events/stream") return route.fulfill({ status: 200, contentType: "text/event-stream", body: ": hi\n\n" });
    if (u.pathname === "/api/v1/targets:inspect") {
      const b = JSON.parse(route.request().postData() || "{}");
      if (b.engine === "nextflow") return route.fulfill({ json: FASTQC });
      return route.fulfill({ json: { kind: "rule", rules: ["all", "make_reads", "qc_stats", "qc_report", "merge_bams", "call_variants", "plot_summary"],
        plan: b.rule ? { jobs: { make_reads: 12, qc_stats: 12, qc_report: 1 }, total: 25 } : null } });
    }
    if (u.pathname.endsWith("/logs")) {
      const smk = u.pathname.includes(RUN_R.id);
      const body = smk ? "Building DAG of jobs...\nJob stats:\nmake_reads  12\nqc_stats    12\nqc_report    1\ntotal       25\n...\n25 of 25 steps (100%) done\n"
        : "N E X T F L O W  ~  version 26.10.4\nmodule run nf-core/fastqc -version 0.0.0-6d1763b\n[a1/2b3c4d] FASTQC (sampleA) | 2 of 3\n";
      return route.fulfill({ status: 200, contentType: "text/plain", body });
    }
    const match = Object.keys(routes).filter((k) => key.startsWith(k)).sort((a, b) => b.length - a.length)[0];
    if (!match) return route.fulfill({ status: 404, contentType: "application/problem+json", body: JSON.stringify({ title: "Not found", detail: key }) });
    return route.fulfill({ json: routes[match] });
  });
  const shot = async (name, full = false) => { await page.waitForTimeout(500); await page.screenshot({ path: OUT + name + ".png", fullPage: full }); };

  // 1. Launch, module: mode, name, Load
  await page.goto(BASE + "/launch");
  await page.getByRole("radio", { name: /One step/ }).check();
  await page.getByRole("textbox", { name: /^Module/ }).fill("nf-core/fastqc");
  await shot("1-launch-module-empty");
  await page.getByRole("button", { name: "Load", exact: true }).click();
  await page.getByText("Pinned to 0.0.0-6d1763b").waitFor();
  await page.getByRole("textbox", { name: /^meta/ }).fill('{"id": "sampleA", "single_end": false}');
  await page.getByRole("textbox", { name: /^reads/ }).fill("/g/demo-lab/data/sampleA_R{1,2}.fq.gz");
  await shot("2-launch-module-loaded", true);

  // 2. Launch, rule
  await page.goto(BASE + "/launch");
  await page.getByRole("radio", { name: /One step/ }).check();
  await page.getByRole("radio", { name: /Snakemake rule/ }).check({ force: true });
  await page.getByRole("textbox", { name: /^Snakemake pipeline/ }).fill("/g/demo-lab/pipelines/synth-qc");
  await page.getByRole("button", { name: "Load", exact: true }).click();
  const rule = page.getByRole("radio", { name: /^qc_report/ });
  await rule.waitFor();
  await rule.click();
  await page.getByText("What will run").waitFor();
  await shot("3-launch-rule", true);

  // 3. Runs list
  await page.goto(BASE + "/runs");
  await page.getByRole("grid", { name: "Runs" }).waitFor();
  await shot("4-runs-list");

  // 4. Module run detail (monitoring)
  await page.goto(BASE + `/runs/${RUN_M.id}`);
  await page.getByText("This run targets one module").waitFor();
  await shot("5-run-module", true);

  // 5. Rule run detail, outside fold open
  await page.goto(BASE + `/runs/${RUN_R.id}`);
  await shot("6-run-rule", true);

  // 6. Terminal module run with a changed checksum
  await page.goto(BASE + `/runs/${RUN_CLI.id}`);
  await page.getByText(/checksum differs/).waitFor();
  await page.screenshot({ path: OUT + "7-run-checksum.png", clip: { x: 0, y: 0, width: 1440, height: 520 } });

  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
