// The demo's server (issue #160): `fetch` and `EventSource` answered in the browser, with the routes
// the Runs list, Run detail and its Graph tab read. Two Nextflow runs of the demo pipeline (one
// live, one finished for the diff) and one failed Snakemake run. Nothing leaves the page.
import type { GraphDocument } from "../runs/graph/types";
import { PARAMS, ROOT, STEPS } from "./pipeline";
import { type Sim, advance, countsOf, finished, graphOf, iso, newSim } from "./sim";

const API = "/api/v1";
export const LIVE = "run_01JCDE7M0RN5Q2P3R5S7T9V1W1";
export const DONE = "run_01JCDE7M0RN5Q2P3R5S7T9V1W2";
export const SMK = "run_01JCDE7M0RN5Q2P3R5S7T9V1W3";
/** Simulated seconds per real second. */
export const SPEED = 15;

const NO_RESOURCES = { cpus: null, memory_bytes: null, time_s: null, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };

interface State {
  live: Sim;
  done: Sim;
  paused: boolean;
}
let state: State;

export function reset(): void {
  const now = Date.now();
  const done = newSim(now - 3 * 3600_000, { pace: 1.2, skip: [`${ROOT}:BAM_QC:RSEQC_INFEREXPERIMENT`] });
  advance(done, 20_000);
  // the live run resumes the previous one: the genome preparation is reused from its cache
  const live = newSim(now, { cached: STEPS.filter((s) => s.id.includes(":PREPARE_GENOME:")).map((s) => s.id) });
  advance(live, 30); // already started when the page opens
  state = { live, done, paused: false };
}

export const setPaused = (paused: boolean) => (state.paused = paused);
export const isPaused = () => state.paused;

const sims = (): Record<string, Sim> => ({ [LIVE]: state.live, [DONE]: state.done });

function runOf(id: string): Record<string, unknown> | null {
  if (id === SMK) return SMK_RUN;
  const sim = sims()[id];
  if (!sim) return null;
  const end = finished(sim) ? Math.max(...sim.tasks.map((t) => t.end ?? 0)) : null;
  const counts = countsOf(sim.tasks);
  return {
    id,
    name: id === LIVE ? "rnaseq-ko-vs-wt" : "rnaseq-ko-vs-wt-previous",
    state: end === null ? "running" : "succeeded",
    origin: "ui",
    created_at: iso(sim, -5),
    started_at: iso(sim, 0),
    ended_at: end === null ? null : iso(sim, end),
    workflow: { engine: "nextflow", engine_version: "26.10.4", location: "nf-core/rnaseq", name: "nf-core/rnaseq", version: "3.27.0" },
    profiles: ["docker"],
    failure: null,
    head: { session: `spectio-${id}`, node: "login1", alive: end === null, exit_code: end === null ? null : 0, checked: true },
    task_counts: counts,
    summary: {
      tasks: { done: (counts.succeeded ?? 0) + (counts.cached ?? 0), total: sim.tasks.length, failed: 0, cached: counts.cached ?? 0 },
      last_failure: null,
      stage_mode: "quarters",
    },
  };
}

const DETAIL = {
  stages_note: null,
  failures: [],
  failures_total: 0,
  command: null,
  parent_run_id: null,
  resumed_as: [],
  results_dir: "/scratch/demo/spectio-runs/rnaseq-ko-vs-wt/results",
};

function detailOf(id: string): Record<string, unknown> | null {
  const run = runOf(id);
  if (!run) return null;
  const running = run.state === "running";
  return {
    ...run,
    ...DETAIL,
    params: id === SMK ? { samples: "config/samples.tsv", ref: "data/genome.fa" } : PARAMS,
    actions: { resume: running ? { allowed: false, reason: "running" } : { allowed: false, reason: "demo" } },
  };
}

function tasksOf(id: string, process: string | null, wanted: string | null) {
  const sim = sims()[id];
  if (!sim) return [];
  return sim.tasks
    .filter((t) => !process || t.step.id === process)
    .filter((t) => !wanted || wanted.split(",").includes(t.state))
    .map((t) => ({
      id: t.id,
      process: t.step.id,
      tag: t.sample,
      name: `${t.step.id.split(":").at(-1)}${t.sample ? ` (${t.sample})` : ""}`,
      state: t.state,
      stage_id: t.step.stage,
      attempt_n: t.attempt || null,
      resources: NO_RESOURCES,
      slurm: null,
    }));
}

function outputsOf(id: string, process: string) {
  const sim = sims()[id];
  const step = STEPS.find((s) => s.id === process);
  if (!sim || !step) return [];
  return sim.tasks
    .filter((t) => t.step.id === process && t.state === "succeeded")
    .flatMap((t) =>
      step.outputs.map((o) => ({
        path: o.replace("{s}", t.sample ?? ""),
        task_id: t.id,
        attempt_n: t.attempt,
        state: "present",
        temp: false,
        root: "results",
      })),
    );
}

function graphFor(id: string): GraphDocument | null {
  if (id === SMK) return SMK_GRAPH;
  const sim = sims()[id];
  return sim ? graphOf(sim) : null;
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": status >= 400 ? "application/problem+json" : "application/json" },
  });
const missing = (what: string) => json(404, { type: "/problems/not-found", title: "Not found", detail: `${what} is not part of this demo` });

/** Answers one request of the app, by path; the demo has no writes. */
export function answer(url: URL, method = "GET"): Response {
  const path = decodeURIComponent(url.pathname.slice(API.length));
  const q = url.searchParams;
  if (method !== "GET") return json(403, { type: "/problems/forbidden", title: "Read-only demo", detail: "This demo does not launch, stop or change runs." });
  if (path === "/version") return json(200, { version: "0.0.2-demo", node: "login1", runs_root: "/scratch/demo/spectio-runs", account: "demo", executor: "local" });
  if (path === "/features") return json(200, { features: ["graph_view"] });
  if (path === "/catalog") return json(200, { items: [], file: { path: "~/.spectio/catalog.toml", state: "missing", detail: null } });
  if (path === "/me/notifications") return json(200, { items: [], unread: 0, read_up_to: null });
  if (path === "/runs:summary") {
    const groups: Record<string, number> = {};
    for (const r of [LIVE, DONE, SMK].map(runOf)) groups[String(r!.state)] = (groups[String(r!.state)] ?? 0) + 1;
    return json(200, { groups: Object.entries(groups).map(([key, count]) => ({ key, count })) });
  }
  if (path === "/runs") {
    const states = q.get("state")?.split(",");
    const items = [LIVE, DONE, SMK].map(runOf).filter((r) => !states || states.includes(String(r!.state)));
    return json(200, { items, next: null });
  }
  const m = /^\/runs\/([^/]+)(\/.*)?$/.exec(path);
  if (!m) return missing(path);
  const [, id, rest = ""] = m;
  const detail = detailOf(id);
  if (!detail) return missing("This run");
  if (rest === "") return json(200, detail);
  if (rest === "/graph") return json(200, graphFor(id));
  if (rest === "/stages") return json(200, { items: [] });
  if (rest === "/tasks") return json(200, { items: tasksOf(id, q.get("process"), q.get("state")), next: null });
  if (rest === "/processes") {
    const doc = graphFor(id)!;
    return json(200, {
      items: doc.nodes.map((n) => ({ process: n.id, stage_id: n.stage_id, counts: n.counts ?? {}, retries: n.retries ?? 0, status: n.status, pipeline_order: n.pipeline_order })),
    });
  }
  const out = /^\/processes\/(.+)\/outputs$/.exec(rest);
  if (out) return json(200, { items: outputsOf(id, out[1]) });
  return missing(path);
}

type Handler = (event: MessageEvent) => void;
const sources = new Set<DemoEventSource>();

/** The live stream: one frame per tick for the live run, as `spectio.run.delta`. */
export class DemoEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  readyState = DemoEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private handlers = new Map<string, Handler>();
  constructor(readonly url: string) {
    sources.add(this);
    setTimeout(() => {
      this.readyState = DemoEventSource.OPEN;
      this.onopen?.();
    }, 50);
  }
  addEventListener(type: string, handler: Handler) {
    this.handlers.set(type, handler);
  }
  close() {
    this.readyState = DemoEventSource.CLOSED;
    sources.delete(this);
  }
  emit(runId: string) {
    this.handlers.get("spectio.run.delta")?.(new MessageEvent("spectio.run.delta", { data: JSON.stringify({ run_id: runId }) }));
  }
}

/** Advances the live run by one real second and tells the open streams. */
export function tick(): void {
  if (state.paused || finished(state.live)) return;
  advance(state.live, SPEED);
  sources.forEach((s) => s.emit(LIVE));
}

/** Installs the demo server in place of the network. */
export function install(): void {
  reset();
  const real = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.href);
    if (!url.pathname.startsWith(API)) return real(input, init);
    return answer(url, init?.method ?? (input instanceof Request ? input.method : "GET"));
  };
  (window as unknown as { EventSource: unknown }).EventSource = DemoEventSource;
  setInterval(tick, 1000);
}

// --- The Snakemake run: a finished rule graph with one failed rule ---------------------------

const rule = (id: string, file: string, status: "done" | "failed" | "not_needed", counts: Record<string, number>, duration: number) => ({
  id,
  name: id,
  kind: "rule" as const,
  stage_id: file.replace("rules/", "").replace(".smk", ""),
  subworkflow: null,
  source: { file: `workflow/${file}`, line: null },
  condition: null,
  params: [],
  status,
  counts,
  retries: 0,
  metrics: { duration_s: duration, failed: counts.failed ?? 0 },
});

const SMK_GRAPH: GraphDocument = {
  version: 1,
  engine: "snakemake",
  producer: "smk-rulegraph",
  complete: true,
  groups: [
    { id: "stage:qc", kind: "stage", name: "rules/qc.smk", parent: null, condition: null },
    { id: "stage:mapping", kind: "stage", name: "rules/mapping.smk", parent: null, condition: null },
    { id: "stage:calling", kind: "stage", name: "rules/calling.smk", parent: null, condition: null },
  ],
  nodes: [
    rule("fastp", "rules/qc.smk", "done", { succeeded: 4 }, 120),
    rule("bwa_map", "rules/mapping.smk", "done", { succeeded: 4 }, 600),
    rule("samtools_sort", "rules/mapping.smk", "done", { succeeded: 4 }, 180),
    rule("samtools_index", "rules/mapping.smk", "done", { succeeded: 4 }, 40),
    rule("call_variants", "rules/calling.smk", "failed", { succeeded: 3, failed: 1 }, 420),
    rule("plot_quals", "rules/calling.smk", "not_needed", {}, 0),
    { ...rule("all", "Snakefile", "not_needed", {}, 0), stage_id: null },
  ],
  edges: [
    { source: "fastp", target: "bwa_map" },
    { source: "bwa_map", target: "samtools_sort" },
    { source: "samtools_sort", target: "samtools_index" },
    { source: "samtools_index", target: "call_variants" },
    { source: "call_variants", target: "plot_quals" },
    { source: "plot_quals", target: "all" },
  ],
};

const SMK_RUN = {
  id: SMK,
  name: "variant-calling-batch3",
  state: "failed",
  origin: "cli-observed",
  created_at: "2026-11-10T14:00:00Z",
  started_at: "2026-11-10T14:00:04Z",
  ended_at: "2026-11-10T14:23:10Z",
  workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/variant-calling", name: "variant-calling", version: null },
  profiles: [],
  failure: { kind: "task", detail: "Rule call_variants failed for sample S3 (exit 1)." },
  head: { session: null, node: "login1", alive: false, exit_code: 1, checked: true },
  task_counts: { succeeded: 19, failed: 1 },
  summary: { tasks: { done: 19, total: 20, failed: 1, cached: 0 }, last_failure: null, stage_mode: "quarters" },
};
