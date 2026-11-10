import { Button } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { type ReactNode, type Ref, useState } from "react";
import { type Process, type RunDetail, type ServerVersion, type Stage, setPinned } from "../api";
import { runEnvName, summary as envSummary } from "../environments/fields";
import { ICONS, Icon } from "../icons";
import { LiveStatus } from "../live";
import { toYaml } from "../launch/schemaFields";
import { EngineMark, PipelineMark, markFor } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { PhoneTitle, usePhone } from "../shell/layout";
import { type CopyItem, CopyButton, CopyMenu } from "./CopyMenu";
import { DeleteRuns } from "./DeleteRuns";
import { ResumeAction } from "./ResumeDialog";
import { StateWord, failureText, runName, tasksText } from "./RunState";
import { duration, engineName, executorLabel, isTerminal, plural, runWord, shortId, stagesLine, sum, tone, when, words } from "./stateWord";

// The run header that every tab of the run shares (ui-spec §4.4 run tools note; LiteRunDetail;
// UX-PAR-19, 21 and 22): the state bar, the engine's mark tile, the name and short ID, the state
// line, Cancel, Resume, Copy to a new launch, Copy, Pin or Unpin and, once ended, Delete… (FU-P3-115b),
// then the facts and the task counts.

/** The chips under the facts: the states with tasks, failed and retried always (UX-PAR-22). A chip
 * with a `filter` (a Tasks tab filter's label) opens the Tasks tab on it (P3-parD). */
export function taskChips(run: RunDetail, processes: Process[]): { label: string; n: number; tone: string; filter?: string }[] {
  const c = run.task_counts;
  const chips = [
    { label: "succeeded", n: sum(c, "succeeded"), tone: "succeeded", always: false, filter: "Succeeded" },
    { label: "running", n: sum(c, "running"), tone: "running", always: false, filter: "Running" },
    { label: "pending", n: sum(c, "pending", "submitted"), tone: "queued", always: false, filter: "Pending" },
    { label: "failed", n: sum(c, "failed"), tone: "failed", always: true, filter: "Failed" },
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

/** What Copy offers for this run (LiteRunActions B, H): the engine command, its config as the
 * engine reads it, its directory when known, its ID. */
export function copyItems(run: RunDetail, server: ServerVersion | null): CopyItem[] {
  const items: CopyItem[] = [];
  if (run.command) items.push({ label: "Command", what: "the command", text: run.command.text });
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
  // a run started from a terminal on another host or boot: its head cannot be seen from here
  if (!run.head.checked) return `Not checked (on ${run.head.node}, started from a terminal)`;
  // the runner reports a head's end after its 60 s end grace (the spool may still hold events):
  // until then a run that has ended has a head that is ending, not alive (P3-parB)
  if (run.head.alive) return isTerminal(run.state) ? "Ending" : "Alive";
  return "Exited";
}

/** The engine's own settings that change what the job files show (ui-spec §5.2). */
function engineSettings(run: RunDetail): [string, ReactNode][] {
  const s = run.engine_settings;
  const said = [
    s?.cleanup && "Work directory cleaned after success (cleanup = true)",
    s?.notemp && "Temporary files kept (--notemp)",
  ].filter((x): x is string => !!x);
  return said.length ? [["Engine settings", <span className="sp-lines">{said.map((t) => <span key={t}>{t}</span>)}</span>]] : [];
}

/** The run's environment, from its own snapshot (ui-spec §4.8.1, Run detail): no row for a run
 * started from a terminal, and the Executor row reads the same snapshot, never `GET /version`. */
function environmentFacts(run: RunDetail, server: ServerVersion | null): [string, ReactNode][] {
  const env = run.environment;
  const word = !env || env.state === "not_recorded" ? "not recorded" : env.state === "not_readable" ? "cannot be read" : null;
  if (!env || word) return [...(env ? [["Environment", word] as [string, ReactNode]] : []), ["Executor", word]];
  const profile = run.workflow.engine === "snakemake" && env.executor === "slurm" ? run.profiles[0] : undefined;
  const sub = profile
    ? `resources and partition from the profile ${profile} (this environment's are not passed)`
    : envSummary({ executor: env.executor ?? "slurm", slurm: env.slurm, local: env.local }, run.head?.node ?? server?.node ?? "the server", server?.executor ?? "slurm");
  const executor = executorLabel(env.executor ?? "");
  const value = (
    <span className="sp-lines">
      <span>
        {runEnvName(env)}
        <span className="sp-chip sp-env-badge">
          <span className="sp-sr"> · </span>
          {executor}
        </span>
      </span>
      <span className="sp-muted">{sub}</span>
    </span>
  );
  return [["Environment", value], ["Executor", executor]];
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
    [
      "Pipeline directory",
      <span className="sp-copy-line">
        <span className="sp-mono">{w.location}</span>
        <CopyButton text={w.location} label="Copy" name="Copy the pipeline directory" />
      </span>,
    ],
    ["Run directory", <span className="sp-mono">{runDirectory(run, server) ?? "—"}</span>],
    ...environmentFacts(run, server),
    ...engineSettings(run),
    ["Failure", run.state === "failed" ? failureText(run) : "—"],
  ];
  // a Resume and its parent link to each other (LiteRunActions G); the parent is named by its short ID
  if (run.parent_run_id) {
    facts.push([
      "Resume of",
      <Link className="sp-text-link" to="/runs/$id" params={{ id: run.parent_run_id }}>
        run {shortId(run.parent_run_id)}
      </Link>,
    ]);
  }
  if (run.resumed_as.length) {
    facts.push([
      "Resumed as",
      <span className="sp-lines">
        {run.resumed_as.map((child) => (
          <Link key={child.id} className="sp-text-link" to="/runs/$id" params={{ id: child.id }}>
            {child.name ?? `run ${shortId(child.id)}`} · {runWord(child.state)}
          </Link>
        ))}
      </span>,
    ]);
  }
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

const RESUMABLE = new Set(["failed", "cancelled"]);

interface Props {
  run: RunDetail;
  stages: Stage[];
  processes: Process[];
  server: ServerVersion | null;
  titleRef: Ref<HTMLHeadingElement>;
  canCancel: boolean;
  onCancel: () => void;
  cancelError: string | null;
  /** A count chip pressed: the Tasks tab filter it names. */
  onChip: (filter: string) => void;
  /** The run as `PATCH /runs/{id}` answered it (Pin, Unpin). */
  onRun: (run: RunDetail) => void;
}

export function RunHeader({ run, stages, processes, server, titleRef, canCancel, onCancel, cancelError, onChip, onRun }: Props) {
  const phone = usePhone();
  const navigate = useNavigate();
  const [pinError, setPinError] = useState<string | null>(null);
  const pin = () =>
    setPinned(run.id, !run.pinned)
      .then((r) => {
        onRun(r);
        setPinError(null);
      })
      .catch((e: Error) => setPinError(e.message));
  const ended = isTerminal(run.state);
  // Failed and Cancelled add Resume, every ended state Copy to a new launch; a run started from a
  // terminal has neither (ui-spec §4.4 run tools note, header actions)
  const launched = run.origin !== "cli-observed";
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
          {launched && RESUMABLE.has(run.state) && <ResumeAction run={run} server={server} fullWidth={phone} />}
          {launched && ended && (
            <Button renderRoot={(props) => <Link to="/launch" search={{ from: run.id }} {...props} />} variant="default" className="sp-copy-launch" fullWidth={phone}>
              Copy to a new launch
            </Button>
          )}
          <CopyMenu items={copyItems(run, server)} fullWidth={phone} />
          <Button variant="default" onClick={pin} leftSection={<Icon path={ICONS.pin} size={15} />} fullWidth={phone}>
            {run.pinned ? "Unpin" : "Pin"}
          </Button>
          {ended && <DeleteRuns runs={[run]} why={null} onDeleted={(said) => navigate({ to: "/runs", state: { said } })} />}
        </div>
      </div>
      {cancelError && <p role="alert">Cancel failed: {cancelError}</p>}
      {pinError && <p role="alert">Pin failed: {pinError}</p>}
      <FoldSection id="facts" screen="run" icon={ICONS.info} title="Facts" summary={summary} defaultOpen={!phone}>
        <Facts run={run} server={server} />
      </FoldSection>
      <div className="sp-chips-row">
        <span className="sp-chips-label">{Units}</span>
        <ul className="sp-counts" aria-label={`${Units} by state`}>
          {taskChips(run, processes).map((chip) =>
            chip.filter ? (
              <li key={chip.label}>
                <button
                  type="button"
                  className="sp-chip sp-chip-button"
                  data-tone={chip.tone}
                  aria-label={`Show the ${plural(chip.n, `${chip.label} ${unit}`, `${chip.label} ${units}`)}`}
                  onClick={() => onChip(chip.filter!)}
                >
                  {chip.n} {chip.label}
                </button>
              </li>
            ) : (
              <li key={chip.label} className="sp-chip" data-tone={chip.tone}>
                {chip.n} {chip.label}
              </li>
            ),
          )}
        </ul>
      </div>
    </header>
  );
}
