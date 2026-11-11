import { Button, Modal, SegmentedControl, Select, Tabs } from "@mantine/core";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { type KeyboardEvent, type Ref, useCallback, useEffect, useId, useRef, useState } from "react";
import {
  ApiError,
  type LogSource,
  type Page,
  type Process,
  type RunDetail,
  type ServerVersion,
  type Stage,
  type Task,
  cancelRun,
  getLog,
  getRun,
  listProcesses,
  listStages,
  listTasks,
  logUrl,
} from "../api";
import { Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { FoldSection } from "../shell/FoldSection";
import { CardHead } from "../shell/CardHead";
import { usePhone } from "../shell/layout";
import { EmptyState, ErrorPanel } from "../shell/States";
import { Toolbar, ToolbarSearch } from "../shell/Toolbar";
import { useAccountingReads } from "./accounting";
import { CopyButton, useCopyStatus } from "./CopyMenu";
import { type Detail, DetailSheet } from "./DetailSheet";
import { taskSearch } from "./explorer";
import { FailureSummary } from "./FailureSummary";
import { LogLines, LogViewer, ToolButton } from "./LogViewer";
import { ByProcess } from "./ByProcess";
import { bytes, isLow, isNear, nearLimit, percent, resourcesLine, seconds } from "./resources";
import { ResultsSection } from "./ResultsSection";
import { RunHeader, runDirectory } from "./RunHeader";
import { CheckpointMark, Low, NearLimit, ProcessName, Word, runName, taskLabel } from "./RunState";
import {
  classWord,
  engineName,
  isTerminal,
  lastSegment,
  neededFirst,
  plural,
  processState,
  refresh,
  type Shown,
  stageWord,
  sum,
  taskWord,
  tone,
  total,
  words,
} from "./stateWord";

export const RUN_ID = /^run_[0-7][0-9A-HJKMNP-TV-Z]{25}$/; // api §7, as the server checks it
const CANCELLABLE = new Set(["queued", "running"]);
const LOGS: { source: LogSource; label: string }[] = [
  { source: "head-out", label: "Head output" },
  { source: "head-err", label: "Head errors" },
  { source: "engine", label: "Engine log" },
];

const TABS = ["summary", "tasks", "parameters", "logs"] as const;
type Tab = (typeof TABS)[number];

type RunSearch = { tab?: Exclude<Tab, "summary">; source?: LogSource; from?: "summary"; process?: string; task?: string; attempt?: number };

/** The run's URL keeps its tab, the log source on Logs (?tab=logs&source=engine, with &from=summary
 * when the Summary's last lines opened it: Logs then shows Back to Summary) and the process
 * on Tasks (?tab=tasks&process=ALIGN), so a view can be linked and reloaded; anything else falls
 * back to the Summary, the engine log and every process. `&task=<id>&attempt=<n>` reopens that
 * task's sheet on that attempt (ui-spec §4.4.1, Back to the task sheet). */
export function runSearch(search: Record<string, unknown>): RunSearch {
  return { ...tabSearch(search), ...taskSearch(search) };
}

function tabSearch(search: Record<string, unknown>): RunSearch {
  const tab = TABS.find((t) => t !== "summary" && t === search.tab) as Exclude<Tab, "summary"> | undefined;
  if (tab === "tasks" && typeof search.process === "string" && search.process !== "") return { tab, process: search.process };
  if (tab !== "logs") return tab ? { tab } : {};
  const source = LOGS.find((l) => l.source === search.source)?.source ?? "engine";
  return search.from === "summary" ? { tab, source, from: "summary" } : { tab, source };
}

type Words = ReturnType<typeof words>;


/** A process's name as the button that opens its detail; the label names the row. */
function OpenProcess({ name, w, onOpen }: { name: string; w: Words; onOpen: (d: Detail) => void }) {
  return (
    <button type="button" className="sp-link-button sp-open" aria-label={`Open ${w.group} ${name}`} onClick={() => onOpen({ kind: "process", name })}>
      <ProcessName name={name} />
    </button>
  );
}

/** "n of m" with a bar beside it: indigo when all is done, running blue otherwise (UX-PAR-24).
 * The bar is decoration; the text says the value. `lower`: the total may grow (a checkpoint is
 * open), so the part past the known jobs is hatched and the bar is never full (ui-spec §5.2). */
function Bar({ done, all, lower = false }: { done: number; all: number; lower?: boolean }) {
  const width = all ? Math.round((done / all) * 100) : 0;
  return (
    <span className="sp-bar" data-full={all > 0 && done === all && !lower} data-lower={lower || undefined} aria-hidden="true">
      <span style={{ width: `${width}%` }} />
    </span>
  );
}

/** On the phone, one card per process (MLiteRunDetail; UX-PAR-10): name and state word, the
 * bar, then the counts the table has in columns. */
type Rows = { processes: Process[]; ended: boolean; open: string[]; label: string; w: Words; onOpen: (d: Detail) => void };

const QUIET = new Set(["not_needed", "up_to_date", "no_tasks"]); // states with no job to come

/** "12 / 20", "0 / at least 3", "0 jobs yet", or "0 jobs" for a state with no job to come. */
function doneText(p: Process, w: Words): string {
  const all = total(p.counts);
  const done = sum(p.counts, "succeeded", "cached", "stored");
  if (!all) return QUIET.has(p.status ?? "") ? `0 ${w.units}` : `0 ${w.units} yet`;
  return p.lower_bound ? `${done} / at least ${all}` : `${done} / ${all}`;
}

/** The process's name, and the "Checkpoint" mark of a checkpoint rule. */
function NameCell({ p, w, onOpen }: { p: Process; w: Words; onOpen: (d: Detail) => void }) {
  return (
    <>
      <OpenProcess name={p.process} w={w} onOpen={onOpen} />
      {p.is_checkpoint && <CheckpointMark />}
    </>
  );
}

function ProcessCards({ processes, ended, open, label, w, onOpen }: Rows) {
  return (
    <ul className="sp-cards-list" aria-label={label}>
      {neededFirst(processes).map((p) => {
        const all = total(p.counts);
        const done = sum(p.counts, "succeeded", "cached", "stored");
        const { state, word } = processState(p, ended, open);
        return (
          <li key={p.process} className="sp-row-card" data-rail="" data-tone={tone(state)} data-quiet={p.status === "not_needed" || undefined}>
            <span className="sp-row-card-top">
              <span>
                <NameCell p={p} w={w} onOpen={onOpen} />
              </span>
              <Word state={state} word={word} />
            </span>
            <span className="sp-done">
              <Bar done={done} all={all} lower={p.lower_bound} /> {all ? `${doneText(p, w)} ${w.units}` : doneText(p, w)}
            </span>
            <span className="sp-muted">
              {sum(p.counts, "running")} running · {sum(p.counts, "pending", "submitted")} pending ·{" "}
              {sum(p.counts, "failed")} failed · {p.retries} retried
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ProcessTable({ processes, ended, open, label, w, onOpen }: Rows) {
  const phone = usePhone();
  if (phone) return <ProcessCards processes={processes} ended={ended} open={open} label={label} w={w} onOpen={onOpen} />;
  return (
    <div className="sp-table-wrap">
      <table className="sp-table" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">{w.Group}, first-seen order</th>
            <th scope="col">State</th>
            <th scope="col">{w.Units} done</th>
            <th scope="col" className="sp-num" data-narrow="">Running</th>
            <th scope="col" className="sp-num" data-narrow="">Pending</th>
            <th scope="col" className="sp-num">Failed</th>
            <th scope="col" className="sp-num" data-narrow="">Retried</th>
          </tr>
        </thead>
        <tbody>
          {neededFirst(processes).map((p) => {
            const all = total(p.counts);
            const done = sum(p.counts, "succeeded", "cached", "stored");
            const { state, word } = processState(p, ended, open);
            return (
              <tr key={p.process} data-quiet={p.status === "not_needed" || undefined}>
                <td>
                  <NameCell p={p} w={w} onOpen={onOpen} />
                </td>
                <td className="sp-state-cell">
                  <Word state={state} word={word} />
                </td>
                <td>
                  {all ? (
                    <span className="sp-done">
                      <Bar done={done} all={all} lower={p.lower_bound} /> {doneText(p, w)}
                    </span>
                  ) : (
                    doneText(p, w)
                  )}
                </td>
                <td className="sp-num" data-narrow="" data-running={sum(p.counts, "running") > 0 || undefined}>
                  {sum(p.counts, "running")}
                </td>
                <td className="sp-num" data-narrow="">{sum(p.counts, "pending", "submitted")}</td>
                <td className="sp-num">{sum(p.counts, "failed")}</td>
                <td className="sp-num" data-narrow="">{p.retries}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Stages in position order, each opening to its processes; or the flat list (ui-spec §4.4 note). */
function StagesOrProcesses({
  run,
  stages,
  processes,
  onTasks,
  onOpen,
}: {
  run: RunDetail;
  stages: Stage[];
  processes: Process[];
  onTasks: () => void;
  onOpen: (d: Detail) => void;
}) {
  const ended = isTerminal(run.state);
  const w = words(run.workflow.engine);
  const engine = engineName(run.workflow.engine);
  const open = run.summary.open_checkpoints ?? [];
  const updates = run.summary.dag_updates ?? 0;
  const note = (
    <>
      {run.stages_note && (
        <p role="note" className="sp-muted">
          {run.stages_note}
        </p>
      )}
      {processes.length > 0 && processes.every((p) => p.status === "up_to_date") && (
        <p role="note" className="sp-note">
          Nothing to run: all outputs are up to date
        </p>
      )}
      {open.length > 0 && (
        <p role="note" className="sp-note">
          The DAG grows after checkpoint {open.join(", ")}: more {w.units} may come.
        </p>
      )}
      {/* the old and new totals and the checkpoint's name are not served yet (FU-P3-54) */}
      {updates > 0 && (
        <p className="sp-muted">
          DAG updated after a checkpoint{updates > 1 ? ` (${updates} times)` : ""}: the {w.unit} count includes the new {w.units}.
        </p>
      )}
    </>
  );
  const legend = (
    <p className="sp-legend">
      Pending: no {w.unit} has started. Running: {w.units} are running, or some are done and more are to come. Done:
      every {w.unit} succeeded or was reused. Stopped: the run ended before it finished.{" "}
      {run.workflow.engine === "snakemake"
        ? "Waiting for checkpoint: its jobs may appear once the checkpoint ends. Up to date: its outputs already exist. Not needed in this run: the targets or an input function left it out. \"at least\": a checkpoint is open and more jobs may come."
        : "No task (condition or empty input): a when: condition was false, or its input was empty. Processes the script does not call in this run are not listed."}
    </p>
  );
  if (!stages.length) {
    return (
      <FoldSection id="processes" screen="run" icon="list" title={w.Groups} summary={plural(processes.length, w.group, w.groups)}>
        {note}
        <p className="sp-muted">No stages for this pipeline: {w.groups} as the engine reports them.</p>
        <ProcessTable processes={processes} ended={ended} open={open} label={w.Groups} w={w} onOpen={onOpen} />
        {legend}
      </FoldSection>
    );
  }
  const loose = processes.filter((p) => !stages.some((s) => s.id === p.stage_id));
  const running = stages.filter((s) => s.state === "running").length;
  return (
    <FoldSection id="stages" screen="run" icon="layers" title="Stages" summary={`${plural(stages.length, "stage", "stages")} · ${running} running`}>
      {note}
      <p className="sp-intro">
        {plural(stages.length, "stage", "stages")}, in order, each with its {w.groups} in the order {engine} first reported
        them. Open a stage to see its {w.groups}. A stage declared in <span className="sp-mono">spectio.yml</span> shows
        Declared; a detected one shows Detected and is for display only.{" "}
        <button type="button" className="sp-link-button" onClick={onTasks}>
          All {w.units} <Icon name="arrowRight" />
        </button>
      </p>
      {stages.map((stage) => {
        const all = total(stage.task_counts);
        const done = sum(stage.task_counts, "succeeded", "cached", "stored");
        const mine = processes.filter((p) => p.stage_id === stage.id);
        const word = stageWord(stage, ended);
        return (
          <details key={stage.id} className="sp-stage" open={stage.state === "running"}>
            <summary>
              <span className="sp-stage-n">{stage.position}</span>
              <span className="sp-stage-name">
                <strong>{stage.name ?? stage.id}</strong>{" "}
                <span className="sp-chip">{stage.source === "declared" ? "Declared" : "Detected"}</span>
                <span className="sp-muted">{plural(mine.length, w.group, w.groups)}</span>
              </span>
              <Word state={word} word={word} />
              <span className="sp-done">
                <Bar done={done} all={all} />
                {done} of {all} {w.units}
              </span>
              <span className="sp-chev">
                <Icon name="chevronDown" />
              </span>
            </summary>
            <p className="sp-link-end">
              <button type="button" className="sp-link-button" aria-label={`Open stage ${stage.name ?? stage.id}`} onClick={() => onOpen({ kind: "stage", id: stage.id })}>
                Stage details <Icon name="arrowRight" />
              </button>
            </p>
            <ProcessTable processes={mine} ended={ended} open={open} label={`${w.Groups} of ${stage.name ?? stage.id}`} w={w} onOpen={onOpen} />
          </details>
        );
      })}
      {loose.length > 0 && (
        <details className="sp-stage">
          <summary>
            <span className="sp-stage-name">
              <strong>Not in a stage</strong>
            </span>
            <span className="sp-chev">
              <Icon name="chevronDown" />
            </span>
          </summary>
          <ProcessTable processes={loose} ended={ended} open={open} label={`${w.Groups} not in a stage`} w={w} onOpen={onOpen} />
        </details>
      )}
      {legend}
    </FoldSection>
  );
}

/** "Why it failed", open first on a failed run (ui-spec §4.4, UX-PAR-25): the run-level part, then
 * one card per job that failed on its last attempt (FailureSummary, P1 Task 32). */
function WhyItFailed({ run, processes, onTasks, onOpen }: { run: RunDetail; processes: Process[]; onTasks: () => void; onOpen: (d: Detail) => void }) {
  const failure = run.failure as { class?: unknown; message?: unknown; task_id?: unknown } | null;
  const kind = typeof failure?.class === "string" ? failure.class : null;
  // left out when a job's card already shows it unchanged (CR-P3T32-04)
  const said = typeof failure?.message === "string" ? failure.message.trim() : "";
  const message = run.failures.some((f) => f.message?.trim() === said) ? "" : said;
  const culpritId = typeof failure?.task_id === "string" ? failure.task_id : null;
  const w = words(run.workflow.engine);
  const { unit, units, Units } = w;
  // the task that failed first (failure.task_id), found among the run's failed tasks: up to 5 pages
  // of 50; past 250 failed tasks the line is left out
  const [culprit, setCulprit] = useState<Task | null>(null);
  useEffect(() => {
    if (!culpritId) return;
    const controller = new AbortController();
    const find = async () => {
      let cursor: string | null = null;
      for (let n = 0; n < 5; n += 1) {
        const page = await listTasks(run.id, { state: "failed", limit: 50, cursor }, controller.signal);
        const found = page.items.find((t) => t.id === culpritId);
        if (found) return setCulprit(found);
        cursor = page.next;
        if (!cursor) return;
      }
    };
    find().catch(() => undefined); // the line is extra: without it, the rest still says why
    return () => controller.abort();
  }, [run.id, culpritId]);
  const failed = run.summary.tasks.failed;
  const headline = failed > 0 ? `${plural(failed, unit, units)} failed, and the run stopped` : kind ? `The run stopped: ${classWord(kind)}` : "The run stopped";
  return (
    <FoldSection id="why" screen="run" icon="alert" title="Why it failed" summary={kind ? classWord(kind) : undefined}>
      {failed > 0 && (
        <p className="sp-link-end">
          <button type="button" className="sp-link-button" onClick={onTasks}>
            {Units}, filtered to Failed <Icon name="arrowRight" />
          </button>
        </p>
      )}
      <div className="sp-why" data-rail="" data-tone="failed">
        <p className="sp-why-head">
          {kind && (
            <span className="sp-chip" data-tone="failed">
              {kind}
            </span>
          )}
          <strong>{headline}</strong>
        </p>
        {message && <p className="sp-why-message">{message}</p>}
        {culprit && (
          <p className="sp-why-first">
            First to fail: <span className="sp-mono">{taskLabel(culprit)}</span>
            {processes.some((p) => p.process === culprit.process) && (
              <>
                {" · "}
                <button
                  type="button"
                  className="sp-link-button"
                  aria-label={`Open ${w.group} ${culprit.process}`}
                  onClick={() => onOpen({ kind: "process", name: culprit.process })}
                >
                  {w.Group} {lastSegment(culprit.process)} <Icon name="arrowRight" />
                </button>
              </>
            )}
          </p>
        )}
      </div>
      <FailureSummary run={run} processes={processes} onOpen={onOpen} />
    </FoldSection>
  );
}

// What may go into the copied commands: a host name, a tmux session name, a local head's
// `<pid>.<start>`. Anything else shows no commands, and each value is quoted (SEC-P3PARA-01).
const HOST_NAME = /^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$/;
const SESSION_NAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
const LOCAL_HEAD = /^([0-9]{1,10})\.[0-9]{1,20}$/;

/** How to look at the head by hand: ssh and tmux attach with tmux heads (P1 Task 10, the exact
 * session as dev-env §15.3 req. 11 targets it); the process with the local executor, whose head
 * has no terminal (P1 Task 9). */
function HeadByHand({ run, server }: { run: RunDetail; server: ServerVersion | null }) {
  const head = run.head!;
  const local = server?.executor === "local";
  const session = head.session ?? "";
  const pid = LOCAL_HEAD.exec(session)?.[1];
  if (local ? pid === undefined : !HOST_NAME.test(head.node) || !SESSION_NAME.test(session)) return null;
  const commands = local ? `ps -o pid,etime,args --sid ${pid}` : `ssh -- '${head.node}'\ntmux attach -t '=${session}'`;
  return (
    <FoldSection id="attach" screen="run" icon="terminal" title="Open the head by hand" summary={local ? `process ${pid}` : `tmux on ${head.node}`} card>
      <p className="sp-muted">
        {local
          ? `The engine runs as process ${pid}, in its own session on ${head.node}, with no terminal to attach to. To see it and what it started:`
          : `The engine runs in its own tmux session on ${head.node}. Attach to watch it or to act on it; detach with Ctrl-b d and the run goes on.`}
      </p>
      <pre className="sp-code">{commands}</pre>
      <CopyButton text={commands} label="Copy commands" name="Copy the commands to open the head by hand" />
    </FoldSection>
  );
}

/** The last lines of a log, read when the section opens and again on each frame of an active run. */
function LogTail({ id, source, ended, onAll, openerRef }: { id: string; source: LogSource; ended: boolean; onAll: (s: LogSource) => void; openerRef: Ref<HTMLButtonElement> }) {
  const [text, setText] = useState<string | null>(null);
  const [frames, setFrames] = useState(0); // read again on each frame while the run is active (FU-P3-80)
  useFrames(() => setFrames((n) => n + 1), id, !ended);
  useEffect(() => {
    const controller = new AbortController();
    getLog(id, source, controller.signal)
      .then((t) => setText(t.trimEnd().split("\n").slice(-6).join("\n") || (ended ? "Empty." : "Empty so far.")))
      .catch((e: ApiError) => controller.signal.aborted || setText(e.status === 404 ? "Not written yet." : `Could not read it: ${e.message}`));
    return () => controller.abort();
  }, [id, source, ended, frames]);
  const label = LOGS.find((l) => l.source === source)!.label;
  return (
    <>
      {/* a click on the lines opens the full log too, not a text selection; the button below is the keyboard's way (FU-P3-88a) */}
      <pre className="sp-code sp-log-tail sp-nowrap" data-opens tabIndex={0} aria-label={`${label}, last lines`} onClick={() => { if (!window.getSelection()?.toString()) onAll(source); }}>
        {text === null ? "Loading…" : <LogLines text={text} />}
      </pre>
      <button ref={openerRef} type="button" className="sp-link-button" onClick={() => onAll(source)}>
        Open the full {label.toLowerCase()} <Icon name="arrowRight" />
      </button>
    </>
  );
}

function ParamsList({ params }: { params: RunDetail["params"] }) {
  const entries = Object.entries(params);
  if (!entries.length) return <p className="sp-muted">No parameters were set at launch.</p>;
  return (
    <dl className="sp-params">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt className="sp-mono">{key}</dt>
          <dd>{typeof value === "string" ? value : JSON.stringify(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

/** The Summary's aside (LiteRunDetail, LiteRunFailed; UX-PAR-23): the parts the 0.0.1 API serves.
 * Results and reports come with P1 Task 31. */
function SummaryAside({ run, server, onLogs, logOpener }: { run: RunDetail; server: ServerVersion | null; onLogs: (s: LogSource) => void; logOpener: Ref<HTMLButtonElement> }) {
  const head = run.head;
  const failed = run.state === "failed";
  const params = Object.keys(run.params).length;
  return (
    <aside className="sp-aside" aria-label="About this run">
      {head?.alive && head.session && run.origin !== "cli-observed" && <HeadByHand run={run} server={server} />}
      <FoldSection
        id={failed ? "head-err" : "engine-log"}
        screen="run"
        icon="file"
        title={failed ? "Head errors · last lines" : "Engine log · last lines"}
        card
      >
        <LogTail id={run.id} source={failed ? "head-err" : "engine"} ended={isTerminal(run.state)} onAll={onLogs} openerRef={logOpener} />
      </FoldSection>
      {head && !head.alive && run.origin !== "cli-observed" && (
        <FoldSection
          id="head-ended"
          screen="run"
          icon="power"
          title="The head has ended"
          summary={head.exit_code != null ? `exit ${head.exit_code}` : undefined}
          defaultOpen={false}
          card
        >
          <p className="sp-muted">
            The engine's head on {head.node} has ended
            {head.exit_code != null ? ` with exit code ${head.exit_code}` : ""}. Its output and errors stay in Logs.
          </p>
        </FoldSection>
      )}
      {run.origin !== "cli-observed" && <ResultsSection run={run} />}
      <FoldSection id="params" screen="run" icon="sliders" title="Parameters" summary={`${params} set at launch`} defaultOpen={false} card>
        <ParamsList params={run.params} />
      </FoldSection>
    </aside>
  );
}

/** The Tasks tab's state filters, as on LiteRunTasks; Retried waits for a retry filter on /tasks. */
const TASK_FILTERS: { label: string; states: string[] | null }[] = [
  { label: "All", states: null },
  { label: "Running", states: ["running"] },
  { label: "Pending", states: ["pending", "submitted"] },
  { label: "Succeeded", states: ["succeeded"] },
  { label: "Failed", states: ["failed"] },
];

const EFF_SOURCE = "From sacct when the job has ended; before that from the engine's trace or benchmark";

/** A job's efficiency on the phone: "CPU eff. 34 % · Mem eff. 3 %, low"; while it runs, when it
 * will be measured. */
function efficiencyLine(t: Task): string | null {
  const e = t.efficiency;
  if (!e) return null;
  if (e.state === "running") return "Measured when the job ends";
  if (e.cpu === null && e.mem === null) return null;
  const flag = (r: number | null, memory: boolean) => (isLow(r) ? ", low" : memory && isNear(r) ? ", near limit" : "");
  return `CPU eff. ${percent(e.cpu)}${flag(e.cpu, false)} · Mem eff. ${percent(e.mem)}${flag(e.mem, true)}`;
}

/** The Tasks tab's two views (ui-spec §4.4 note 2026-11-07): the list, and By process (By rule). */
function ViewTabs({ view, setView, w }: { view: "list" | "process"; setView: (v: "list" | "process") => void; w: Words }) {
  const views = [
    { key: "list" as const, label: `${w.Unit} list` },
    { key: "process" as const, label: `By ${w.group}` },
  ];
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = view === "list" ? "process" : "list"; // two tabs: every arrow key moves to the other
    setView(next);
    event.currentTarget.querySelector<HTMLButtonElement>(`[data-view="${next}"]`)?.focus();
  };
  return (
    <div className="sp-segments sp-view-tabs" role="tablist" aria-label={`${w.Units} view`} onKeyDown={onKey}>
      {views.map((v) => (
        <button
          key={v.key}
          type="button"
          role="tab"
          data-view={v.key}
          id={`view-${v.key}`}
          aria-controls={`view-panel-${v.key}`}
          aria-selected={view === v.key}
          tabIndex={view === v.key ? 0 : -1}
          onClick={() => setView(v.key)}
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}

/** A task's name and tag as the button that opens its detail; the label names the row. */
function OpenTask({ task, w, onOpen }: { task: Task; w: Words; onOpen: (d: Detail) => void }) {
  return (
    <button type="button" className="sp-link-button sp-open" aria-label={`Open ${w.unit} ${taskLabel(task)}`} onClick={() => onOpen({ kind: "task", task })}>
      <strong>
        <ProcessName name={task.process} />
      </strong>
      {(task.tag ?? task.name) && <> ({task.tag ?? task.name})</>}
    </button>
  );
}

/** The row's Files button: the task's detail, which shows its files; the name names the row
 * (ui-spec §4.4 note 2026-10-28, Job files). */
function FilesButton({ task, onOpen, wide = false }: { task: Task; onOpen: (d: Detail) => void; wide?: boolean }) {
  const attempt = task.attempt_n === null ? "" : `, attempt ${task.attempt_n}`;
  return (
    <Button
      variant="default"
      size={wide ? "md" : "xs"}
      fullWidth={wide}
      className={wide ? "sp-files-button" : undefined}
      leftSection={<Icon name="file" size="button" />}
      aria-label={`Files of ${taskLabel(task)}${attempt}`}
      onClick={() => onOpen({ kind: "task", task })}
    >
      Files
    </Button>
  );
}

function TasksPanel({
  run,
  processes,
  filter,
  setFilter,
  process,
  setProcess,
  onOpen,
}: {
  run: RunDetail;
  processes: Process[];
  filter: number;
  setFilter: (i: number) => void;
  process: string;
  setProcess: (process: string) => void;
  onOpen: (d: Detail) => void;
}) {
  const id = run.id;
  const w = words(run.workflow.engine);
  const phone = usePhone();
  const effSource = useId();
  const [view, setView] = useState<"list" | "process">("list");
  const [shown, setShown] = useState<Shown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const states = TASK_FILTERS[filter].states?.join(",") ?? "";
  const loads = useRef(0); // only the latest response is shown

  const load = useCallback(
    (merge: boolean) => {
      const mine = ++loads.current;
      listTasks(id, { state: states, process, limit: 50 })
        .then((page) => {
          if (mine !== loads.current) return;
          setShown((s) => (merge ? refresh(s, page) : { rows: page.items ?? [], next: page.next ?? null }));
          setError(null);
        })
        .catch((e: Error) => mine === loads.current && setError(e.message));
    },
    [id, states, process],
  );
  useEffect(() => {
    setShown(null);
    load(false);
  }, [load]);
  const active = !isTerminal(run.state);
  useFrames(() => load(true), id, active);

  const more = () => {
    const mine = loads.current;
    listTasks(id, { state: states, process, limit: 50, cursor: shown?.next })
      .then((page) => {
        if (mine !== loads.current) return;
        setShown((s) => ({ rows: [...(s?.rows ?? []), ...(page.items ?? [])], next: page.next ?? null }));
      })
      .catch((e: Error) => setError(e.message));
  };

  const counts = process ? (processes.find((p) => p.process === process)?.counts ?? {}) : run.task_counts;
  const count = (states: string[] | null) => (states ? sum(counts, ...states) : total(counts));
  const tasks = shown?.rows ?? null;
  // one toolbar for both views (ui-spec §12.6), the view tabs first so they keep focus on a switch
  const toolbar = (
    <Toolbar
      label={`${w.Units} tools`}
      filters={
        <>
          <ViewTabs view={view} setView={setView} w={w} />
          {view === "list" && (
            <>
              <div className="sp-segments" role="group" aria-label={`Show ${w.units}`}>
                {TASK_FILTERS.map((f, i) => (
                  <button key={f.label} type="button" aria-pressed={filter === i} onClick={() => setFilter(i)}>
                    {f.label}
                    <span className="sp-count">{count(f.states)}</span>
                  </button>
                ))}
              </div>
              <Select
                size="sm"
                className="sp-task-group"
                aria-label={w.Group}
                allowDeselect={false}
                value={process}
                onChange={(value) => setProcess(value ?? "")}
                data={[
                  { value: "", label: `All ${w.groups} (${processes.length})` },
                  ...processes.map((p) => ({ value: p.process, label: `${lastSegment(p.process)} (${total(p.counts)})` })),
                  ...(process && !processes.some((p) => p.process === process) ? [{ value: process, label: lastSegment(process) }] : []),
                ]}
              />
            </>
          )}
        </>
      }
      caption={
        view === "list" && (
          <>
            In the order {engineName(run.workflow.engine)} first reported them
            {active && <LiveStatus />}
          </>
        )
      }
    />
  );
  if (view === "process") {
    return (
      <section className="sp-runs" aria-label={w.Units}>
        {toolbar}
        <div role="tabpanel" id="view-panel-list" aria-labelledby="view-list" hidden />
        <div role="tabpanel" id="view-panel-process" aria-labelledby="view-process">
          <ByProcess
            processes={processes}
            w={w}
            onShow={(name) => {
              setView("list");
              setProcess(name);
            }}
          />
        </div>
      </section>
    );
  }
  return (
    <section className="sp-runs" aria-label={w.Units}>
      {toolbar}
      <div role="tabpanel" id="view-panel-process" aria-labelledby="view-process" hidden />
      <div role="tabpanel" id="view-panel-list" aria-labelledby="view-list" className="sp-runs">
        {error && <p role="alert">The {w.units} could not be read: {error}</p>}
        {tasks === null && !error && <p className="sp-muted">Loading the {w.units}…</p>}
        {tasks?.length === 0 && <p className="sp-empty">No {w.unit} matches these filters.</p>}
        {!!tasks?.length && phone && (
          <ul className="sp-cards-list" aria-label={w.Units}>
            {tasks.map((t) => (
              <li key={t.id} className="sp-row-card sp-task" data-rail="" data-tone={tone(t.state)}>
                <span className="sp-row-card-top">
                  <OpenTask task={t} w={w} onOpen={onOpen} />
                  <Word state={t.state} word={taskWord(t.state)} />
                </span>
                <span className="sp-muted">
                  {t.attempt_n !== null && `attempt ${t.attempt_n} · `}
                  {resourcesLine(t.resources)}
                </span>
                {efficiencyLine(t) && <span className="sp-muted">{efficiencyLine(t)}</span>}
                <FilesButton task={t} onOpen={onOpen} wide />
              </li>
            ))}
          </ul>
        )}
        {!!tasks?.length && !phone && (
          <div className="sp-table-wrap">
            <table className="sp-table" aria-label={w.Units}>
              <thead>
                <tr>
                  <th scope="col">{w.Unit}</th>
                  <th scope="col">State</th>
                  <th scope="col" className="sp-num">Attempt</th>
                  <th scope="col" className="sp-num">Duration</th>
                  <th scope="col" className="sp-num" data-narrow="">CPUs</th>
                  <th scope="col" className="sp-num" data-narrow="">CPU %</th>
                  <th scope="col" className="sp-num">Memory</th>
                  <th scope="col">Peak memory</th>
                  <th scope="col" className="sp-num">Time limit</th>
                  <th scope="col" className="sp-num sp-nowrap-cell" aria-describedby={effSource}>
                    CPU eff.
                  </th>
                  <th scope="col" className="sp-num sp-nowrap-cell" aria-describedby={effSource}>
                    Mem eff.
                  </th>
                  <th scope="col">
                    <span className="sp-sr">Files</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => {
                  const r = t.resources;
                  const near = nearLimit(r);
                  return (
                    <tr key={t.id}>
                      <td data-rail="" data-tone={tone(t.state)} className="sp-task">
                        <OpenTask task={t} w={w} onOpen={onOpen} />
                      </td>
                      <td>
                        <Word state={t.state} word={taskWord(t.state)} />
                      </td>
                      <td className="sp-num">{t.attempt_n ?? "—"}</td>
                      <td className="sp-num sp-nowrap-cell">
                        {seconds(r.realtime_s)}
                        <NearLimit on={near.time} />
                      </td>
                      <td className="sp-num" data-narrow="">{r.cpus ?? "—"}</td>
                      <td className="sp-num" data-narrow="">{r.cpu_percent === null ? "—" : `${Math.round(r.cpu_percent)} %`}</td>
                      <td className="sp-num sp-nowrap-cell">{bytes(r.memory_bytes)}</td>
                      <td className="sp-nowrap-cell">
                        {bytes(r.peak_rss_bytes)}
                        <NearLimit on={near.memory} />
                      </td>
                      <td className="sp-num sp-nowrap-cell">{seconds(r.time_s)}</td>
                      <td className="sp-num sp-nowrap-cell">
                        {percent(t.efficiency?.cpu)}
                        <Low on={isLow(t.efficiency?.cpu)} />
                      </td>
                      <td className="sp-num sp-nowrap-cell">
                        {percent(t.efficiency?.mem)}
                        <Low on={isLow(t.efficiency?.mem)} />
                        <NearLimit on={isNear(t.efficiency?.mem)} />
                      </td>
                      <td>
                        <FilesButton task={t} onOpen={onOpen} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!!tasks?.length && !phone && (
          <p className="sp-muted">
            CPU eff. and Mem eff.: <span id={effSource}>{EFF_SOURCE}</span>. "low": under 25 %.
          </p>
        )}
        {!!tasks?.length && (
          <p className="sp-foot-line">
            {tasks.length} of {plural(count(TASK_FILTERS[filter].states), w.unit, w.units)}
          </p>
        )}
        {shown?.next && (
          <div>
            <Button variant="default" onClick={more}>
              Load more {w.units}
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

const DESCRIPTIONS: Record<LogSource, (engine: string) => string> = {
  "head-out": () => "The engine's standard output in its head",
  "head-err": () => "The head's standard error",
  engine: (engine) => `${engine}'s log of this run`,
};

/** The log's file on the server, as the runner writes it under the run's launch directory
 * (api/logs.py): known for a driven run only. Snakemake's engine log is the newest *.log of a
 * directory, whose name the API does not serve. */
function logFile(run: RunDetail, server: ServerVersion | null, source: LogSource): { path: string; note?: string } | null {
  const directory = runDirectory(run, server);
  if (!directory) return null;
  const launch = `${directory}/launch`;
  if (source === "head-out") return { path: `${launch}/.spectio/head.out` };
  if (source === "head-err") return { path: `${launch}/.spectio/head.err` };
  if (run.workflow.engine === "nextflow") return { path: `${launch}/.nextflow.log` };
  if (run.workflow.engine === "snakemake") return { path: `${launch}/.snakemake/log/`, note: "the newest .log there" };
  return null;
}

function LogsPanel({
  run,
  server,
  source,
  setSource,
  onTasks,
  onBack,
}: {
  run: RunDetail;
  server: ServerVersion | null;
  source: LogSource;
  setSource: (s: LogSource) => void;
  onTasks: () => void;
  /** Back to Summary, when the Summary's last lines opened Logs (FU-P3-88a) */
  onBack?: () => void;
}) {
  const [text, setText] = useState<string | null>(null);
  // a read that did not give the text: "missing" (404, not written yet) or the error's message
  const [failure, setFailure] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const [said, copy] = useCopyStatus();
  const w = words(run.workflow.engine);
  useEffect(() => {
    const controller = new AbortController();
    setText(null);
    setFailure(null);
    getLog(run.id, source, controller.signal)
      .then(setText)
      .catch((e: ApiError) => controller.signal.aborted || setFailure(e.status === 404 ? "missing" : e.message));
    return () => controller.abort();
  }, [run.id, source, reloads]);
  const reload = () => setReloads((n) => n + 1);
  const label = LOGS.find((l) => l.source === source)!.label;
  const file = logFile(run, server, source);
  const download = () => {
    const url = URL.createObjectURL(new Blob([text ?? ""], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${runName(run)}-${source}.log`;
    // Attached, and revoked after the click: Firefox and some Safari versions drop the download otherwise.
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  return (
    <section className="sp-runs sp-logs" aria-label="Logs">
      {onBack && (
        <button type="button" className="sp-link-button sp-logs-back" onClick={onBack}>
          <Icon name="chevronLeft" /> Back to Summary
        </button>
      )}
      {file && (
        <div className="sp-log-file">
          <span id="log-file-label" className="sp-muted">
            File
          </span>
          <code aria-labelledby="log-file-label">{file.path}</code>
          {file.note && <span className="sp-muted">{file.note}</span>}
          <CopyButton text={file.path} label="Copy" name={`Copy the ${label.toLowerCase()} path`} />
        </div>
      )}
      <LogViewer
        text={text}
        label={label}
        filters={<SegmentedControl size="sm" aria-label="Log" value={source} onChange={(value) => setSource(value as LogSource)} data={LOGS.map((l) => ({ value: l.source, label: l.label }))} />}
        actions={
          <>
            <ToolButton label="Reload" icon="reload" onClick={reload} />
            <ToolButton label={`Copy the ${label.toLowerCase()}`} icon="copy" disabled={text === null} onClick={() => copy({ label, what: `the ${label.toLowerCase()}`, text: text ?? "" })} />
            <ToolButton label="Download last 64 KiB" icon="download" disabled={text === null} onClick={download} />
            <ToolButton label="Open raw (opens in a new tab)" icon="externalLink" href={logUrl(run.id, source)} />
          </>
        }
        placeholder={
          failure === "missing" ? (
            <EmptyState icon="file">This log is not written yet.</EmptyState>
          ) : failure ? (
            <ErrorPanel onRetry={reload}>
              The {label.toLowerCase()} could not be read: {failure}
            </ErrorPanel>
          ) : undefined
        }
      />
      <p className="sp-muted sp-log-caption">{DESCRIPTIONS[source](engineName(run.workflow.engine))} · last 64 KiB · loaded when you open it <span role="status">{said}</span>
      </p>
      <p className="sp-log-note">
        <Icon name="file" />
        <span>
          {run.workflow.engine === "snakemake"
            ? "Each job's own log, as its rule declares it, is not in these logs:"
            : "Each task's own files (.command.log, .command.err, .command.sh …) stay in its work directory, not in these logs:"}{" "}
          <button type="button" className="sp-link-button" onClick={onTasks}>
            open a {w.unit} in {w.Units} <Icon name="arrowRight" />
          </button>
        </span>
      </p>
    </section>
  );
}

/** The Parameters tab (ui-spec §12.6, §12.7; UI-10): a filter in the toolbar, then the parameters
 * set at launch in a card, a table on desktop and a list on the phone. */
function ParamsPanel({ params }: { params: RunDetail["params"] }) {
  const phone = usePhone();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(true);
  const all = Object.entries(params);
  if (all.length === 0) return <EmptyState icon="sliders">No parameters were set at launch.</EmptyState>;
  const needle = query.trim().toLowerCase();
  const shown = all.filter(([key, value]) => !needle || `${key} ${JSON.stringify(value)}`.toLowerCase().includes(needle));
  return (
    <section className="sp-runs" aria-label="Parameters">
      <Toolbar label="Parameters tools" search={<ToolbarSearch label="Filter the parameters" value={query} onChange={setQuery} />} />
      <div className="sp-card">
        <CardHead id="run-params" icon="sliders" title="Parameters" meta={needle ? `${shown.length} of ${all.length}` : `${all.length} set at launch`} open={open} onToggle={() => setOpen(!open)} />
        <div id="run-params-body" hidden={!open}>
          {shown.length === 0 ? (
            <EmptyState icon="search">No parameter matches this filter.</EmptyState>
          ) : phone ? (
            <ParamsList params={Object.fromEntries(shown)} />
          ) : (
            <div className="sp-table-wrap">
              <table className="sp-table" aria-label="Parameters">
                <thead>
                  <tr>
                    <th scope="col">Parameter</th>
                    <th scope="col">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map(([key, value]) => (
                    <tr key={key}>
                      <td className="sp-mono">{key}</td>
                      <td>{typeof value === "string" ? value : JSON.stringify(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

/** The not-found state inside the shell: for a run, and for any path the router does not know
 * (such as a malformed run id, /runs/%E0, which matches no route). */
export function NotFound({ run = true }: { run?: boolean }) {
  const title = run ? "No such run" : "Page not found";
  useEffect(() => {
    document.title = `${title} · Spectio`;
  }, [title]);
  return (
    <div className="sp-runs">
      <h1 className="sp-page-title">{title}</h1>
      <p>Spectio has no {run ? "run" : "page"} at this address.</p>
      <div>
        <Button component={Link} to={run ? "/runs" : "/"}>
          {run ? "All runs" : "Home"}
        </Button>
      </div>
    </div>
  );
}

/** Cancel's confirm (LiteCancelDialog; UX-PAR-29): what stops, and how, for this server's executor. */
function CancelDialog({ run, server, opened, onClose, onConfirm }: { run: RunDetail; server: ServerVersion | null; opened: boolean; onClose: () => void; onConfirm: () => void }) {
  const local = server?.executor === "local";
  const w = words(run.workflow.engine);
  const running = sum(run.task_counts, "running");
  const pending = sum(run.task_counts, "pending", "submitted");
  return (
    <Modal opened={opened} onClose={onClose} title="Cancel this run?" returnFocus centered classNames={{ title: "sp-sheet-title" }}>
      <p>
        {local
          ? "Spectio stops its head with signals, and the engine stops its tasks."
          : "Spectio interrupts its head in the tmux session, and the engine stops its tasks."}
      </p>
      <p>
        {runName(run)} has {running} running and {pending} pending {w.units}; they will not finish. Results already
        written stay in the output directory.
      </p>
      <p className="sp-note">
        {local
          ? "SIGTERM to the head's process group, then SIGKILL after 60 s if it still runs."
          : "Ctrl-C to the engine in its tmux session, then SIGTERM and SIGKILL after 60 s each."}{" "}
        The run shows Cancelling, then Cancelled.
      </p>
      <div className="sp-dialog-foot">
        <Button variant="default" data-autofocus onClick={onClose}>
          Keep running
        </Button>
        <Button color="failed" onClick={onConfirm}>
          Cancel the run
        </Button>
      </div>
    </Modal>
  );
}

const FIND_PAGES = 10; // of 200 tasks: the first 2,000 tasks of a run, in ID order

/** One task of the run by its ID, from the run's task listing (no route reads one task alone yet:
 * `GET /tasks/{id}` is FU-P3-96), so a task past the first 2,000 is not found. */
export async function findTask(runId: string, taskId: string, signal: AbortSignal): Promise<Task | null> {
  let cursor: string | null = null;
  for (let n = 0; n < FIND_PAGES; n += 1) {
    const page: Page<Task> = await listTasks(runId, { limit: 200, cursor }, signal);
    const found = page.items.find((t) => t.id === taskId);
    if (found) return found;
    cursor = page.next;
    if (!cursor) return null;
  }
  return null;
}

/** The run detail (ui-spec §4.4, 0.0.1): the shared header with Cancel, the facts and counts, then
 * Summary (why it failed, stages or processes, and the aside), Tasks, Parameters and Logs;
 * refetched on each stream frame for the run until it ends. */
export function RunDetailPage({ id }: { id: string }) {
  const valid = RUN_ID.test(id);
  const server = useServer();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [missing, setMissing] = useState(!valid);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  // the root route passes unknown keys through, so the page reads the search through runSearch too
  const search = runSearch(useSearch({ from: "/runs/$id" }));
  const navigate = useNavigate({ from: "/runs/$id" });
  const tab: Tab = search.tab ?? "summary";
  const logSource = search.source ?? "engine";
  // the last log source shown, so Logs reopens on it after another tab (also after Back or Forward)
  const lastSource = useRef(logSource);
  if (tab === "logs") lastSource.current = logSource;
  // each view is a history entry: Back and Forward step through them (FU-P3-109)
  const go = useCallback(
    (to: Tab, opts: { source?: LogSource; process?: string; from?: "summary" } = {}) => {
      if (to === "logs") lastSource.current = opts.source ?? lastSource.current;
      return navigate({ search: runSearch({ tab: to, source: lastSource.current, process: opts.process, from: opts.from }) });
    },
    [navigate],
  );
  const [taskFilter, setTaskFilter] = useState<number | null>(null);
  // the detail sheet's views, the shown one last (DetailSheet)
  const [views, setViews] = useState<Detail[]>([]);
  const [sheetLost, setSheetLost] = useState(false);
  // &task=&attempt= (back from a Preview of the sheet's Outputs): that task's sheet, on that attempt
  const { task: openTask, attempt: openAttempt } = search;
  useEffect(() => {
    setSheetLost(false);
    if (!valid || !openTask || !openAttempt) return;
    const controller = new AbortController();
    // not found or not read: the page shows without the sheet, and says so
    findTask(id, openTask, controller.signal)
      .then((task) => (task ? setViews([{ kind: "task", task, attempt: openAttempt }]) : setSheetLost(true)))
      .catch(() => controller.signal.aborted || setSheetLost(true));
    return () => controller.abort();
  }, [id, valid, openTask, openAttempt]);
  const closeSheet = () => {
    setViews([]);
    if (openTask) navigate({ search: (prev) => runSearch({ ...prev, task: undefined, attempt: undefined }), replace: true });
  };
  const title = useRef<HTMLHeadingElement>(null);
  const panels = { tasks: useRef<HTMLDivElement>(null), logs: useRef<HTMLDivElement>(null) };
  const focusPanel = useRef(false);
  // Back to Summary from Logs: focus returns to the last lines' button that opened it (FU-P3-88a)
  const logOpener = useRef<HTMLButtonElement>(null);
  const focusOpener = useRef(false);
  useEffect(() => {
    if (focusPanel.current && (tab === "tasks" || tab === "logs")) panels[tab].current?.focus();
    if (focusOpener.current && tab === "summary") logOpener.current?.focus();
    focusPanel.current = false;
    focusOpener.current = false;
  }, [tab, logSource, search.process]);

  const load = useCallback(() => {
    if (!valid) return;
    Promise.all([getRun(id), listProcesses(id), listStages(id)])
      .then(([r, p, s]) => {
        setRun(r);
        setProcesses(p.items ?? []);
        setStages(s.items ?? []);
        setError(null);
      })
      .catch((e: ApiError) => (e.status === 404 ? setMissing(true) : setError(e.message)));
  }, [id, valid]);
  useEffect(load, [load]);
  useFrames(load, id, valid && !(run && isTerminal(run.state)));
  useAccountingReads(load, id, !!run && isTerminal(run.state), processes); // sacct lands after the end (FU-P3-119)

  const name = run ? runName(run) : null;
  usePageCrumb(name);
  useEffect(() => {
    if (name) document.title = `${name} · Spectio`;
  }, [name]);

  if (missing) return <NotFound />;
  if (!run) {
    return (
      <div className="sp-runs">
        {error ? <p role="alert">The run could not be read: {error}</p> : <p className="sp-muted">Loading the run…</p>}
      </div>
    );
  }

  const canCancel = CANCELLABLE.has(run.state) && run.origin !== "cli-observed";
  const confirm = () => {
    setAsking(false);
    cancelRun(id)
      .then((r) => {
        setRun(r);
        setCancelError(null);
        title.current?.focus(); // the Cancel button is gone once the run is cancelling
      })
      .catch((e: Error) => setCancelError(e.message));
  };
  // A failed run's Tasks tab starts at Failed.
  const filter = taskFilter ?? (run.state === "failed" ? TASK_FILTERS.findIndex((f) => f.label === "Failed") : 0);
  // A count chip or Why it failed opens Tasks on that state, with focus on its panel.
  // Already on that view, the URL does not change and the effect does not run: focus it here.
  const focusTasks = (process?: string) => {
    if (tab === "tasks" && search.process === process) panels.tasks.current?.focus();
    else focusPanel.current = true;
  };
  const showTasks = (label: string) => {
    setTaskFilter(Math.max(0, TASK_FILTERS.findIndex((f) => f.label === label)));
    focusTasks();
    go("tasks");
  };
  // The Summary's last lines open Logs on the same source, with focus on its panel and a way back.
  const showLogs = (source: LogSource) => {
    focusPanel.current = true;
    go("logs", { source, from: "summary" });
  };
  const backToSummary = () => {
    focusOpener.current = true;
    go("summary");
  };
  // The sheet's Open in Tasks: the Tasks tab on that process, every state.
  const showProcess = (process: string) => {
    setViews([]);
    setTaskFilter(0);
    focusTasks(process);
    go("tasks", { process });
  };
  const w = words(run.workflow.engine);

  return (
    <div className="sp-runs">
      <RunHeader
        run={run}
        stages={stages}
        processes={processes}
        server={server}
        titleRef={title}
        canCancel={canCancel}
        onCancel={() => setAsking(true)}
        cancelError={cancelError}
        onChip={showTasks}
        onRun={setRun}
        summaryTab={tab === "summary"}
      />
      {sheetLost && <p role="status">This job's sheet could not be reopened.</p>}
      <DetailSheet
        run={run}
        stages={stages}
        processes={processes}
        views={views}
        onOpen={(view) => setViews((shown) => [...shown, view])}
        onBack={() => setViews((shown) => shown.slice(0, -1))}
        onClose={closeSheet}
        onTasks={showProcess}
      />
      <CancelDialog run={run} server={server} opened={asking} onClose={() => setAsking(false)} onConfirm={confirm} />

      <Tabs className="sp-run-tabs" value={tab} onChange={(t) => go(TABS.find((x) => x === t) ?? "summary")} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="summary">Summary</Tabs.Tab>
          <Tabs.Tab value="tasks">{w.Units}</Tabs.Tab>
          <Tabs.Tab value="parameters">Parameters</Tabs.Tab>
          <Tabs.Tab value="logs">Logs</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="summary" pt="md">
          <div className="sp-detail-grid">
            <div className="sp-runs">
              {run.state === "failed" && <WhyItFailed run={run} processes={processes} onTasks={() => showTasks("Failed")} onOpen={(view) => setViews([view])} />}
              <StagesOrProcesses run={run} stages={stages} processes={processes} onTasks={() => go("tasks")} onOpen={(view) => setViews([view])} />
            </div>
            <SummaryAside run={run} server={server} onLogs={showLogs} logOpener={logOpener} />
          </div>
        </Tabs.Panel>
        <Tabs.Panel value="tasks" pt="md" ref={panels.tasks} tabIndex={-1}>
          <TasksPanel
            run={run}
            processes={processes}
            filter={filter}
            setFilter={setTaskFilter}
            process={search.process ?? ""}
            setProcess={(process) => go("tasks", { process })}
            onOpen={(view) => setViews([view])}
          />
        </Tabs.Panel>
        <Tabs.Panel value="parameters" pt="md">
          <ParamsPanel params={run.params} />
        </Tabs.Panel>
        <Tabs.Panel value="logs" pt="md" ref={panels.logs} tabIndex={-1}>
          <LogsPanel
            run={run}
            server={server}
            source={logSource}
            setSource={(source) => go("logs", { source, from: search.from })}
            onTasks={() => go("tasks")}
            onBack={search.from ? backToSummary : undefined}
          />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
}
