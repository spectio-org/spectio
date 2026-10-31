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
export const isTerminal = (state: RunState): boolean =>
  state === "succeeded" || state === "failed" || state === "cancelled";

const n = (counts: Counts, ...states: string[]) => states.reduce((sum, s) => sum + (counts[s] ?? 0), 0);

/** A process or rule has no stored state: its word comes from its task counts. `ended`: the run
 * is terminal, so what had not finished is Stopped and what never started is Not run. */
export function processWord(counts: Counts, ended: boolean): string {
  if (n(counts, "failed") > 0) return "Failed";
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const done = n(counts, "succeeded", "cached", "stored");
  if (total > 0 && done === total) return "Done";
  if (n(counts, "succeeded", "cached", "stored", "running", "aborted") === 0) {
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
      return n(stage.task_counts, "failed") > 0 ? "Failed" : "Stopped";
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
