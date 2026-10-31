import { Button } from "@mantine/core";
import type { ReactNode, Ref } from "react";
import type { Process, RunDetail, ServerVersion, Stage } from "../api";
import { ICONS } from "../icons";
import { LiveStatus } from "../live";
import { EngineMark } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { StateWord, failureText, runName, tasksText } from "./RunState";
import { duration, engineName, isTerminal, plural, shortId, stagesLine, sum, tone, when, words } from "./stateWord";

// The run header that every tab of the run shares (ui-spec §4.4 run tools note; LiteRunDetail;
// UX-PAR-19, 21 and 22): the state bar, the engine's mark tile, the name and short ID, the state
// line, Cancel, then the facts and the task counts. P1 Task 32 adds Copy, Resume and Copy to a
// new launch here.

/** The chips under the facts: the states with tasks, failed and retried always (UX-PAR-22). */
export function taskChips(run: RunDetail, processes: Process[]): { label: string; n: number; tone: string }[] {
  const c = run.task_counts;
  const chips = [
    { label: "succeeded", n: sum(c, "succeeded"), tone: "succeeded", always: false },
    { label: "running", n: sum(c, "running"), tone: "running", always: false },
    { label: "pending", n: sum(c, "pending", "submitted"), tone: "queued", always: false },
    { label: "failed", n: sum(c, "failed"), tone: "failed", always: true },
    { label: "retried", n: processes.reduce((n, p) => n + p.retries, 0), tone: "review", always: true },
    { label: "cached", n: sum(c, "cached", "stored"), tone: "cached", always: false },
    { label: "aborted", n: sum(c, "aborted"), tone: "cancelled", always: false },
    { label: "not scheduled", n: sum(c, "not_scheduled"), tone: "cancelled", always: false },
  ];
  return chips.filter((chip) => chip.always || chip.n > 0);
}

function headWord(run: RunDetail): string {
  if (!run.head) return "Not started yet";
  if (run.origin === "cli-observed") return "Not checked (started from a terminal)";
  return run.head.alive ? "Alive" : "Exited";
}

function Facts({ run, server }: { run: RunDetail; server: ServerVersion | null }) {
  const w = run.workflow;
  const ended = isTerminal(run.state);
  const engine = [engineName(w.engine), w.engine_version].filter(Boolean).join(" ");
  const pipeline = w.name ? (w.version ? `${w.name} ${w.version}` : `${w.name} (no version declared)`) : w.location;
  const facts: [string, ReactNode][] = [
    ["Pipeline", pipeline],
    [
      "Engine · profile",
      <span className="sp-pipeline">
        <EngineMark engine={w.engine} size={18} named />
        <span>{[engine, ...run.profiles].join(" · ")}</span>
      </span>,
    ],
    ["Started · ended", `${when(run.started_at)} · ${ended ? when(run.ended_at) : "—"}`],
    ["Duration", duration(run.started_at, run.ended_at)],
    ["Head session", <span className="sp-mono">{run.head?.session ?? "—"}</span>],
    ["Head", headWord(run)],
    ["Login node", run.head?.node ?? server?.node ?? "—"],
    ["Exit code", run.head?.exit_code != null ? String(run.head.exit_code) : ended ? "—" : "— (still running)"],
    ["Pipeline directory", <span className="sp-mono">{w.location}</span>],
    [
      "Run directory",
      // A driven run's directory is runs_root/<run id> (runner/rundir.py); a run from a terminal has its own.
      <span className="sp-mono">{run.origin !== "cli-observed" && server ? `${server.runs_root}/${run.id}` : "—"}</span>,
    ],
    ["Executor", server ? server.executor.toUpperCase() : "—"],
    ["Failure", run.state === "failed" ? failureText(run) : "—"],
  ];
  return (
    <dl className="sp-facts">
      {facts.map(([name, value]) => (
        <div key={name}>
          <dt>{name}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

interface Props {
  run: RunDetail;
  stages: Stage[];
  processes: Process[];
  server: ServerVersion | null;
  titleRef: Ref<HTMLHeadingElement>;
  canCancel: boolean;
  onCancel: () => void;
  cancelError: string | null;
}

export function RunHeader({ run, stages, processes, server, titleRef, canCancel, onCancel, cancelError }: Props) {
  const ended = isTerminal(run.state);
  const { unit, units } = words(run.workflow.engine);
  const line = stagesLine(stages);
  const failed = run.summary.tasks.failed;
  const w = run.workflow;
  const summary = [
    [w.name, w.version].filter(Boolean).join(" ") || w.location,
    [engineName(w.engine), w.engine_version].filter(Boolean).join(" "),
    `head ${headWord(run).toLowerCase()}`,
  ].join(" · ");
  return (
    <header className="sp-card sp-run-head" data-rail="" data-tone={tone(run.state)}>
      <div className="sp-run-top">
        {w.engine && (
          <span className="sp-mark-tile">
            <EngineMark engine={w.engine} size={24} />
          </span>
        )}
        <div className="sp-grow">
          <div className="sp-title-row">
            <h1 ref={titleRef} tabIndex={-1} className="sp-page-title">
              {runName(run)}
            </h1>
            <span className="sp-id">{shortId(run.id)}</span>
          </div>
          <p className="sp-sub sp-page-sub">
            <StateWord state={run.state} />
            {failed > 0 && <span>{plural(failed, unit, units)} failed</span>}
            {line && <span>{line}</span>}
            <span>
              {tasksText(run)} {units}
            </span>
            <span>{duration(run.started_at, run.ended_at)}</span>
            {ended ? <span>ended {when(run.ended_at)}</span> : <LiveStatus />}
          </p>
          {cancelError && <p role="alert">Cancel failed: {cancelError}</p>}
        </div>
        {canCancel && (
          <Button color="red" variant="outline" onClick={onCancel}>
            Cancel run
          </Button>
        )}
      </div>
      <FoldSection id="facts" screen="run" icon={ICONS.info} title="Facts" summary={summary}>
        <Facts run={run} server={server} />
      </FoldSection>
      <div className="sp-chips-row">
        <span className="sp-chips-label">{units === "jobs" ? "Jobs" : "Tasks"}</span>
        <ul className="sp-counts" aria-label="Tasks by state">
          {taskChips(run, processes).map((chip) => (
            <li key={chip.label} className="sp-chip" data-tone={chip.tone}>
              {chip.n} {chip.label}
            </li>
          ))}
        </ul>
      </div>
    </header>
  );
}
