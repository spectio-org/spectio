// A simulated Nextflow run of the demo pipeline (issue #160): tasks start when what they read is
// done, at most MAX_RUNNING at once; one task fails its first attempt and is retried. Pure: the
// caller advances the clock. `graphOf` turns the state into the GraphDocument the server would send.
import type { GraphDocument, GraphNode } from "../runs/graph/types";
import { EDGES, ROOT, SAMPLES, STAGES, STEPS, type Step } from "./pipeline";

export const MAX_RUNNING = 8;
/** The task that fails once: the demo's retry. */
export const FLAKY = { step: `${ROOT}:ALIGN_STAR:STAR_ALIGN`, sample: "KO_REP2" };

export interface SimTask {
  id: string;
  step: Step;
  sample: string | null;
  /** `cached`: reused from an earlier run (`-resume`), never run here. */
  state: "pending" | "running" | "succeeded" | "cached";
  attempt: number;
  start: number | null;
  end: number | null;
  failedAttempts: number;
}

export interface Sim {
  /** Simulated seconds since the start. */
  clock: number;
  /** The run's start, epoch ms. */
  epoch: number;
  tasks: SimTask[];
  /** Duration factor: the previous run was a bit slower. */
  pace: number;
  steps: Step[];
}

const isDone = (t: SimTask): boolean => t.state === "succeeded" || t.state === "cached";

const upstream = new Map<string, string[]>();
for (const e of EDGES) upstream.set(e.target, [...(upstream.get(e.target) ?? []), e.source]);

export function newSim(epoch: number, options: { pace?: number; skip?: string[]; cached?: string[] } = {}): Sim {
  const steps = STEPS.filter((s) => !options.skip?.includes(s.id));
  let n = 0;
  const tasks: SimTask[] = steps.flatMap((step) =>
    (step.perSample ? SAMPLES : [null]).map((sample) => ({
      id: `tsk_${String(++n).padStart(3, "0")}`,
      step,
      sample,
      state: options.cached?.includes(step.id) ? ("cached" as const) : ("pending" as const),
      attempt: 0,
      start: null,
      end: null,
      failedAttempts: 0,
    })),
  );
  return { clock: 0, epoch, tasks, pace: options.pace ?? 1, steps };
}

/** The same jitter for a task on every call, so durations do not move between ticks. */
function jitter(id: string): number {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return 0.75 + (h % 50) / 100;
}

function ready(sim: Sim, t: SimTask): boolean {
  const ids = new Set(sim.steps.map((s) => s.id));
  return (upstream.get(t.step.id) ?? [])
    .filter((u) => ids.has(u))
    .every((u) => {
      const theirs = sim.tasks.filter((x) => x.step.id === u);
      const perSample = theirs[0]?.step.perSample && t.step.perSample;
      return theirs.filter((x) => !perSample || x.sample === t.sample).every(isDone);
    });
}

/** Advances the clock by `dt` simulated seconds, in one-second steps so tasks chain within a tick. */
export function advance(sim: Sim, dt: number): void {
  const until = sim.clock + dt;
  while (sim.clock < until) {
    sim.clock = Math.min(until, sim.clock + 1);
    for (const t of sim.tasks) {
      if (t.state !== "running" || t.end === null || t.end > sim.clock) continue;
      if (t.step.id === FLAKY.step && t.sample === FLAKY.sample && t.attempt === 1) {
        t.failedAttempts += 1; // exit 137 on the first attempt; Nextflow retries it
        t.state = "pending";
        t.end = null;
        continue;
      }
      t.state = "succeeded";
    }
    let running = sim.tasks.filter((t) => t.state === "running").length;
    for (const t of sim.tasks) {
      if (running >= MAX_RUNNING) break;
      if (t.state !== "pending" || !ready(sim, t)) continue;
      t.state = "running";
      t.attempt += 1;
      t.start ??= sim.clock;
      t.end = sim.clock + Math.round(t.step.seconds * sim.pace * jitter(t.id) * (t.attempt > 1 ? 1.3 : 1));
      running += 1;
    }
  }
}

export const finished = (sim: Sim): boolean => sim.tasks.every(isDone);

export const iso = (sim: Sim, seconds: number): string => new Date(sim.epoch + seconds * 1000).toISOString().replace(".000Z", "Z");

export function countsOf(tasks: SimTask[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const t of tasks) counts[t.state] = (counts[t.state] ?? 0) + 1;
  return counts;
}

function nodeOf(sim: Sim, step: Step, order: number): GraphNode {
  const tasks = sim.tasks.filter((t) => t.step.id === step.id);
  const counts = countsOf(tasks);
  const starts = tasks.map((t) => t.start).filter((s): s is number => s !== null);
  const done = tasks.every(isDone);
  const first = starts.length ? Math.min(...starts) : null;
  const last = done && first !== null ? Math.max(...tasks.map((t) => t.end ?? 0)) : null;
  const failed = tasks.reduce((n, t) => n + t.failedAttempts, 0);
  const parts = step.id.split(":");
  const sub = parts.length > 3 ? `sub:${parts.slice(0, -1).join(":")}` : `sub:${ROOT}`;
  return {
    id: step.id,
    name: parts.at(-1)!,
    kind: "process",
    stage_id: step.stage,
    subworkflow: sub,
    source: { file: step.file, line: 1 },
    condition: step.params.find((p) => p.startsWith("skip_")) ? `!params.${step.params.find((p) => p.startsWith("skip_"))}` : null,
    params: step.params,
    status: done ? "done" : starts.length ? "running" : "pending",
    counts,
    retries: failed,
    pipeline_order: order,
    metrics:
      first === null
        ? {}
        : { duration_s: (last ?? sim.clock) - first, cpu_mean: step.cpu, mem_max: step.mem, failed },
    first_start: first === null ? null : iso(sim, first),
    last_end: last === null ? null : iso(sim, last),
  };
}

export function graphOf(sim: Sim): GraphDocument {
  const ids = new Set(sim.steps.map((s) => s.id));
  const subs = new Set(sim.steps.map((s) => s.id.split(":").slice(0, -1).join(":")).filter((p) => p !== ROOT));
  return {
    version: 1,
    engine: "nextflow",
    producer: "nf-dag",
    complete: true,
    groups: [
      ...Object.entries(STAGES).map(([id, name]) => ({ id: `stage:${id}`, kind: "stage" as const, name, parent: null, condition: null })),
      { id: "sub:NFCORE_RNASEQ", kind: "subworkflow", name: "NFCORE_RNASEQ", parent: null, condition: null },
      { id: `sub:${ROOT}`, kind: "subworkflow", name: "RNASEQ", parent: "sub:NFCORE_RNASEQ", condition: null },
      ...[...subs].map((p) => ({
        id: `sub:${p}`,
        kind: "subworkflow" as const,
        name: p.split(":").at(-1)!,
        parent: `sub:${ROOT}`,
        condition: p.endsWith("BAM_QC") ? "!params.skip_qc" : null,
      })),
    ],
    nodes: sim.steps.map((s, i) => nodeOf(sim, s, i + 1)),
    edges: EDGES.filter((e) => ids.has(e.source) && ids.has(e.target)),
  };
}
