import "./runs.css";
import { Link } from "@tanstack/react-router";
import type { Run, RunState, Task } from "../api";
import { Icon } from "../icons";
import { PipelineMark } from "../shell/EngineMark";
import { type Tone, classWord, lastSegment, plural, runWord, shortId, tone, words } from "./stateWord";

// The icons of ui-spec §3.1, one per tone: clock, play, flag, pause, check, cross, slash.
const SLASH = "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M6 18L18 6";
const TONE_ICONS: Record<Tone, string> = {
  queued: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
  running: "M7 5l12 7-12 7z",
  review: "M5 21V4 M5 4h11l-2 4 2 4H5",
  paused: "M8 5v14 M16 5v14",
  succeeded: "M5 12l5 5 9-10",
  failed: "M6 6l12 12 M18 6L6 18",
  cancelled: SLASH,
  cached: "M5 12l5 5 9-10",
};

/** Icon and word, never colour alone (ui-spec §3.1); the colour is the state's tone token. `state`
 * picks the tone and icon (a run, stage or task state, or a stage or process word). */
export function Word({ state, word }: { state: string; word: string }) {
  const t = tone(state);
  return (
    <span className="sp-state" data-state={state} data-tone={t}>
      <Icon path={TONE_ICONS[t]} size={15} />
      {word}
    </span>
  );
}

/** The "near limit" badge in words, after a measured value (a peak or a duration above 90 %). */
export function NearLimit({ on }: { on: boolean }) {
  return on ? <> <span className="sp-near">near limit</span></> : null;
}

export function StateWord({ state }: { state: RunState }) {
  return <Word state={state} word={runWord(state)} />;
}

/** The run's failure as words: "tool error · <message>", or, with no message, "tool error · 2
 * tasks failed" (UX-PAR-16); never blank. */
export function failureText(run: Run): string {
  const failure = run.failure as { class?: unknown; message?: unknown } | null;
  const message = typeof failure?.message === "string" ? failure.message.trim() : "";
  const kind = typeof failure?.class === "string" ? classWord(failure.class) : "";
  const { unit, units } = words(run.workflow.engine);
  const failed = run.summary.tasks.failed;
  const detail = message || (failed > 0 ? `${plural(failed, unit, units)} failed` : "");
  return [kind, detail].filter(Boolean).join(" · ") || "failed";
}

/** The context line under the state word in a table (ui-spec §3.1). */
export function stateContext(run: Run): string {
  const { unit, units } = words(run.workflow.engine);
  switch (run.state) {
    case "queued":
      return run.head ? "head started" : "head not started yet";
    case "running":
      return `${plural(run.task_counts.running ?? 0, unit, units)} running`;
    case "cancelling":
      return "stopping the engine";
    case "succeeded":
      return "completed";
    case "failed":
      return failureText(run);
    case "cancelled":
      return "cancelled";
    default:
      return "";
  }
}

export const runName = (run: Run): string => run.name ?? `Run ${shortId(run.id)}`;

/** The run's name as a link whose accessible name names the row ("Open run <name>"). */
export function RunLink({ run }: { run: Run }) {
  const name = runName(run);
  return (
    <Link to="/runs/$id" params={{ id: run.id }} className="sp-run-link" aria-label={`Open run ${name}`}>
      {name}
    </Link>
  );
}

export const tasksText = (run: Run): string =>
  run.summary.tasks.total ? `${run.summary.tasks.done} / ${run.summary.tasks.total}` : "—";

/** The run's pipeline: its mark (nf-core for an nf-core/ name, else the engine's; inbox #91), the
 * name and the version, muted, on one line (UX-PAR-01). */
export function Pipeline({ run, size = 20 }: { run: Run; size?: number }) {
  const w = run.workflow;
  return (
    <span className="sp-pipeline">
      <PipelineMark engine={w.engine} name={w.name} size={size} />
      <span>
        {w.name ?? w.location}
        {w.version && <span className="sp-version"> {w.version}</span>}
      </span>
    </span>
  );
}

/** The last segment of a process name; the full name stays its accessible text (ui-spec §4.4). */
export function ProcessName({ name }: { name: string }) {
  const last = lastSegment(name);
  if (last === name) return <span className="sp-mono">{name}</span>;
  return (
    <span className="sp-mono">
      <span aria-hidden="true">{last}</span>
      <span className="sp-sr">{name}</span>
    </span>
  );
}

/** A task as one line: the engine's name for it (`ALIGN (S01)`), else its process and tag. */
export const taskLabel = (t: Task): string => t.name ?? (t.tag ? `${lastSegment(t.process)} (${t.tag})` : lastSegment(t.process));
