import { Button } from "@mantine/core";
import type { ReactNode, Ref } from "react";
import type { Process, RunDetail, ServerVersion, Stage } from "../api";
import { ICONS } from "../icons";
import { LiveStatus } from "../live";
import { toYaml } from "../launch/schemaFields";
import { EngineMark, PipelineMark, markFor } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { PhoneTitle, usePhone } from "../shell/layout";
import { type CopyItem, CopyMenu } from "./CopyMenu";
import { StateWord, failureText, runName, tasksText } from "./RunState";
import { duration, engineName, executorLabel, isTerminal, plural, shortId, stagesLine, sum, tone, when, words } from "./stateWord";

// The run header that every tab of the run shares (ui-spec §4.4 run tools note; LiteRunDetail;
// UX-PAR-19, 21 and 22): the state bar, the engine's mark tile, the name and short ID, the state
// line, Cancel and Copy, then the facts and the task counts. P1 Task 32 adds Resume, Copy to a
// new launch and Copy's "Command" here.

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

/** A driven run's directory, runs_root/<run id> (runner/rundir.py); a run from a terminal has its
 * own, which the API does not serve. */
export function runDirectory(run: RunDetail, server: ServerVersion | null): string | null {
  return run.origin !== "cli-observed" && server ? `${server.runs_root}/${run.id}` : null;
}

/** What Copy offers for this run (LiteRunActions B, H): its config as the engine reads it, its
 * directory when known, its ID. */
export function copyItems(run: RunDetail, server: ServerVersion | null): CopyItem[] {
  const items: CopyItem[] = [];
  if (Object.keys(run.params).length) {
    items.push(
      run.workflow.engine === "snakemake"
        ? { label: "Config (config.yaml)", what: "the config", text: toYaml(run.params) }
        : { label: "Config (params.json)", what: "the params", text: `${JSON.stringify(run.params, null, 2)}\n` },
    );
  }
  const directory = runDirectory(run, server);
  if (directory) items.push({ label: "Run directory", what: "the run directory", text: directory });
  items.push({ label: "Run ID", what: "the run ID", text: run.id });
  return items;
}

function headWord(run: RunDetail): string {
  if (!run.head) return "Not started yet";
  if (run.origin === "cli-observed") return "Not checked (started from a terminal)";
  // the runner reports a head's end after its 60 s end grace (the spool may still hold events):
  // until then a run that has ended has a head that is ending, not alive (P3-parB)
  if (run.head.alive) return isTerminal(run.state) ? "Ending" : "Alive";
  return "Exited";
}

function Facts({ run, server }: { run: RunDetail; server: ServerVersion | null }) {
  const w = run.workflow;
  const ended = isTerminal(run.state);
  const engine = [engineName(w.engine), w.engine_version].filter(Boolean).join(" ");
  const pipeline = w.name ? (w.version ? `${w.name} ${w.version}` : `${w.name} (no version declared)`) : w.location;
  const facts: [string, ReactNode][] = [
    [
      "Pipeline",
      // the pipeline's mark: nf-core for an nf-core/ name, else the engine's (inbox #91)
      <span className="sp-pipeline">
        <PipelineMark engine={w.engine} name={w.name} size={18} />
        <span>{pipeline}</span>
      </span>,
    ],
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
    ["Run directory", <span className="sp-mono">{runDirectory(run, server) ?? "—"}</span>],
    ["Executor", server ? executorLabel(server.executor) : "—"],
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
  const phone = usePhone();
  const ended = isTerminal(run.state);
  const { unit, units, Units } = words(run.workflow.engine);
  const line = stagesLine(stages);
  const failed = run.summary.tasks.failed;
  const w = run.workflow;
  const pipeline = [w.name, w.version].filter(Boolean).join(" ") || w.location;
  const engine = [engineName(w.engine), w.engine_version].filter(Boolean).join(" ");
  const summary = [pipeline, engine, `head ${headWord(run).toLowerCase()}`].join(" · ");
  const state = (
    <>
      <StateWord state={run.state} />
      {failed > 0 && <span>{plural(failed, unit, units)} failed</span>}
      {line && <span>{line}</span>}
    </>
  );
  const progress = (
    <>
      <span>
        {tasksText(run)} {units}
      </span>
      <span>{duration(run.started_at, run.ended_at)}</span>
      {ended ? <span>ended {when(run.ended_at)}</span> : <LiveStatus />}
    </>
  );
  return (
    <header className="sp-card sp-run-head" data-rail="" data-tone={tone(run.state)}>
      {/* The phone: the name and state line in the top bar, with the way back (MLiteRunDetail; UX-PAR-08). */}
      <PhoneTitle title={runName(run)} sub={state} back={{ to: "/runs", label: "Runs" }} titleRef={titleRef} />
      <div className="sp-run-top">
        {markFor(w.engine, w.name) && (
          <span className="sp-mark-tile">
            <PipelineMark engine={w.engine} name={w.name} size={26} />
          </span>
        )}
        {phone ? (
          <div className="sp-grow">
            <strong className="sp-run-pipeline">{pipeline}</strong>
            <span className="sp-muted">{[engine, ...run.profiles].join(" · ")}</span>
            <p className="sp-sub">
              <span>
                Run <span className="sp-mono">{shortId(run.id)}</span>
              </span>
              {progress}
            </p>
          </div>
        ) : (
          <div className="sp-grow">
            <div className="sp-title-row">
              <h1 ref={titleRef} tabIndex={-1} className="sp-page-title">
                {runName(run)}
              </h1>
              <span className="sp-id">{shortId(run.id)}</span>
            </div>
            <p className="sp-sub sp-page-sub">
              {state}
              {progress}
            </p>
          </div>
        )}
        <div className="sp-run-actions">
          {canCancel && (
            <Button color="red" variant="outline" onClick={onCancel}>
              Cancel run
            </Button>
          )}
          <CopyMenu items={copyItems(run, server)} fullWidth={phone} />
        </div>
      </div>
      {cancelError && <p role="alert">Cancel failed: {cancelError}</p>}
      <FoldSection id="facts" screen="run" icon={ICONS.info} title="Facts" summary={summary} defaultOpen={!phone}>
        <Facts run={run} server={server} />
      </FoldSection>
      <div className="sp-chips-row">
        <span className="sp-chips-label">{Units}</span>
        <ul className="sp-counts" aria-label={`${Units} by state`}>
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
