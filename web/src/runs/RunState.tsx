import "./runs.css";
import { Link } from "@tanstack/react-router";
import type { Run, RunState } from "../api";
import { Icon } from "../shell/Sidebar";
import { runWord, shortId } from "./stateWord";

// The icons of ui-spec §3.1: clock, play, flag, pause, check, cross, slash.
const ICONS: Record<RunState, string> = {
  queued: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
  running: "M7 5l12 7-12 7z",
  awaiting_review: "M5 21V4 M5 4h11l-2 4 2 4H5",
  pausing: "M8 5v14 M16 5v14",
  paused: "M8 5v14 M16 5v14",
  succeeded: "M5 12l5 5 9-10",
  failed: "M6 6l12 12 M18 6L6 18",
  cancelling: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M6 18L18 6",
  cancelled: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M6 18L18 6",
};

/** Icon and word, never colour alone (ui-spec §3.1). */
export function StateWord({ state }: { state: RunState }) {
  return (
    <span className="sp-state" data-state={state}>
      <Icon path={ICONS[state] ?? ICONS.queued} size={15} />
      {runWord(state)}
    </span>
  );
}

/** The context line under the state word in a table (ui-spec §3.1). */
export function stateContext(run: Run): string {
  switch (run.state) {
    case "queued":
      return run.head ? "head started" : "head not started yet";
    case "running":
      return `${run.task_counts.running ?? 0} tasks running`;
    case "cancelling":
      return "stopping the engine";
    case "succeeded":
      return "completed";
    case "failed":
      return typeof run.failure?.message === "string" ? run.failure.message : "failed";
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
