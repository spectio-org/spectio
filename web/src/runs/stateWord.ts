// The words of the run, stage and process states (ui-spec §3.1 and the §4.4 note of 2026-10-28,
// "State word"), and the short formats the run screens share.
import type { Counts, RunState, Stage } from "../api";

const RUN_WORDS: Record<RunState, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_review: "Awaiting review",
  pausing: "Pausing",
  paused: "Paused",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelling: "Cancelling",
  cancelled: "Cancelled",
};

export const runWord = (state: RunState): string => RUN_WORDS[state] ?? state;

/** The run states that count as active (api §7.1). */
export const ACTIVE: string[] = ["queued", "running", "pausing", "paused", "awaiting_review", "cancelling"];

/** The eight colour families of `--sp-state-*` (design/tokens/spectio-tokens.css). */
export type Tone = "queued" | "running" | "review" | "paused" | "succeeded" | "failed" | "cancelled" | "cached";

const TONES: Record<string, Tone> = {
  running: "running",
  Running: "running",
  awaiting_review: "review",
  "Awaiting review": "review",
  pausing: "paused",
  paused: "paused",
  succeeded: "succeeded",
  completed: "succeeded",
  Done: "succeeded",
  failed: "failed",
  Failed: "failed",
  cancelling: "cancelled",
  cancelled: "cancelled",
  aborted: "cancelled",
  skipped: "cancelled",
  Stopped: "cancelled",
  "Not run": "cancelled",
  cached: "cached",
  stored: "cached",
};

/** The tone of a run, stage or task state, or of a stage or process word; queued otherwise
 * (pending, submitted, not started, not scheduled). */
export const tone = (state: string): Tone => TONES[state] ?? "queued";

const TASK_WORDS: Record<string, string> = {
  pending: "Pending",
  submitted: "Submitted",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  cached: "Cached",
  stored: "Stored",
  aborted: "Aborted",
  not_scheduled: "Not scheduled",
};
export const taskWord = (state: string): string => TASK_WORDS[state] ?? state;

/** The engine's own words (UX-PAR-20): Snakemake has jobs and rules, Nextflow tasks and processes. */
export function words(engine: string | null) {
  return engine === "snakemake"
    ? { unit: "job", units: "jobs", Unit: "Job", Units: "Jobs", group: "rule", groups: "rules", Group: "Rule", Groups: "Rules" }
    : { unit: "task", units: "tasks", Unit: "Task", Units: "Tasks", group: "process", groups: "processes", Group: "Process", Groups: "Processes" };
}

/** "1 task", "3 jobs". */
export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

const CLASS_WORDS: Record<string, string> = {
  oom: "out of memory",
  timeout: "time limit",
  preempted: "preempted",
  node_failure: "node failure",
  cancelled_external: "cancelled outside Spectio",
  image: "image error",
  tool_error: "tool error",
  engine_fault: "engine error",
  head_lost: "head lost",
  launch_error: "launch error",
  engine_missing: "engine missing",
  engine_version: "engine version",
  input_check: "input check",
};
/** The words of a failure class (the store's `failure_class` values). */
export const classWord = (value: string): string => CLASS_WORDS[value] ?? value.replace(/_/g, " ");

const ENGINE_NAMES: Record<string, string> = { nextflow: "Nextflow", snakemake: "Snakemake" };
/** "Nextflow", "Snakemake"; an unknown engine as the API names it. */
export const engineName = (engine: string | null): string => (engine ? (ENGINE_NAMES[engine] ?? engine) : "—");
export const isTerminal = (state: RunState): boolean =>
  state === "succeeded" || state === "failed" || state === "cancelled";

/** Every count, whatever its state. */
export const total = (counts: Counts) => Object.values(counts).reduce((a, b) => a + b, 0);
/** The last segment of a process name (`NFCORE:RNASEQ:ALIGN` → `ALIGN`). */
export const lastSegment = (name: string) => name.split(":").pop() ?? name;
export const sum = (counts: Counts, ...states: string[]) => states.reduce((n, s) => n + (counts[s] ?? 0), 0);

/** A process or rule has no stored state: its word comes from its task counts. `ended`: the run
 * is terminal, so what had not finished is Stopped and what never started is Not run. */
export function processWord(counts: Counts, ended: boolean): string {
  if (sum(counts, "failed") > 0) return "Failed";
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const done = sum(counts, "succeeded", "cached", "stored");
  if (total > 0 && done === total) return "Done";
  if (sum(counts, "succeeded", "cached", "stored", "running", "aborted") === 0) {
    return ended ? "Not run" : "Pending";
  }
  return ended ? "Stopped" : "Running";
}

/** The word of `run_stages.state`; `failed` reads Failed only when one of the stage's own tasks
 * failed, otherwise Stopped. */
export function stageWord(stage: Stage, ended: boolean): string {
  switch (stage.state) {
    case "completed":
      return "Done";
    case "failed":
      return sum(stage.task_counts, "failed") > 0 ? "Failed" : "Stopped";
    case "skipped":
      return "Not run";
    case "running":
      return ended ? "Stopped" : "Running";
    case "awaiting_review":
      return "Awaiting review";
    default:
      return ended ? "Not run" : "Pending";
  }
}

/** "n of m stages done · k running", or null for a run with no stage. */
export function stagesLine(stages: Stage[]): string | null {
  if (!stages.length) return null;
  const done = stages.filter((s) => s.state === "completed").length;
  const running = stages.filter((s) => s.state === "running").length;
  return `${done} of ${stages.length} stages done · ${running} running`;
}

/** The last 6 characters of the ULID (ui-spec §4.4). */
export const shortId = (id: string): string => id.slice(-6);

/** "12 s", "38 min", "1 h 05"; "—" before the start. `end` null: until now. */
export function duration(start: string | null, end: string | null, now = new Date()): string {
  if (!start) return "—";
  const seconds = Math.max(0, Math.round(((end ? new Date(end) : now).getTime() - new Date(start).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")}`;
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const two = (v: number) => String(v).padStart(2, "0");

/** "Today 09:02", "Sun 18:10" within the week, else "2026-09-01 06:05"; local time. */
export function when(iso: string | null, now = new Date()): string {
  if (!iso) return "—";
  const at = new Date(iso);
  const time = `${two(at.getHours())}:${two(at.getMinutes())}`;
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(now) - day(at)) / 86400000);
  if (days === 0) return `Today ${time}`;
  if (days > 0 && days < 7) return `${DAYS[at.getDay()]} ${time}`;
  return `${at.getFullYear()}-${two(at.getMonth() + 1)}-${two(at.getDate())} ${time}`;
}

const EXECUTORS: Record<string, string> = { slurm: "SLURM", local: "Local" };
/** The server's executor as people write it (UX-PAR-33): "SLURM", "Local". */
export const executorLabel = (executor: string): string => EXECUTORS[executor] ?? executor.toUpperCase();
