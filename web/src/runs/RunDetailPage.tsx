import { Button, Modal, Tabs } from "@mantine/core";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { ICONS, Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { FoldSection } from "../shell/FoldSection";
import { usePhone } from "../shell/layout";
import { CopyButton } from "./CopyMenu";
import { type Detail, DetailSheet } from "./DetailSheet";
import { LogLines, LogViewer } from "./LogViewer";
import { RunHeader, runDirectory } from "./RunHeader";
import { ProcessName, Word, runName, taskLabel } from "./RunState";
import {
  classWord,
  engineName,
  isTerminal,
  lastSegment,
  plural,
  processWord,
  stageWord,
  sum,
  taskWord,
  tone,
  total,
  words,
} from "./stateWord";

const RUN_ID = /^run_[0-7][0-9A-HJKMNP-TV-Z]{25}$/; // api §7, as the server checks it
const CANCELLABLE = new Set(["queued", "running"]);
const LOGS: { source: LogSource; label: string }[] = [
  { source: "head-out", label: "Head output" },
  { source: "head-err", label: "Head errors" },
  { source: "engine", label: "Engine log" },
];

const TABS = ["summary", "tasks", "parameters", "logs"] as const;
type Tab = (typeof TABS)[number];

/** The run's URL keeps its tab, the log source on Logs (?tab=logs&source=engine) and the process
 * on Tasks (?tab=tasks&process=ALIGN), so a view can be linked and reloaded; anything else falls
 * back to the Summary, the engine log and every process. */
export function runSearch(search: Record<string, unknown>): { tab?: Exclude<Tab, "summary">; source?: LogSource; process?: string } {
  const tab = TABS.find((t) => t !== "summary" && t === search.tab) as Exclude<Tab, "summary"> | undefined;
  if (tab === "tasks" && typeof search.process === "string" && search.process !== "") return { tab, process: search.process };
  if (tab !== "logs") return tab ? { tab } : {};
  return { tab, source: LOGS.find((l) => l.source === search.source)?.source ?? "engine" };
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
 * The bar is decoration; the text says the value. */
function Bar({ done, all }: { done: number; all: number }) {
  const width = all ? Math.round((done / all) * 100) : 0;
  return (
    <span className="sp-bar" data-full={all > 0 && done === all} aria-hidden="true">
      <span style={{ width: `${width}%` }} />
    </span>
  );
}

/** On the phone, one card per process (MLiteRunDetail; UX-PAR-10): name and state word, the
 * bar, then the counts the table has in columns. */
type Rows = { processes: Process[]; ended: boolean; label: string; w: Words; onOpen: (d: Detail) => void };

function ProcessCards({ processes, ended, label, w, onOpen }: Rows) {
  return (
    <ul className="sp-cards-list" aria-label={label}>
      {processes.map((p) => {
        const all = total(p.counts);
        const done = sum(p.counts, "succeeded", "cached", "stored");
        const word = processWord(p.counts, ended);
        return (
          <li key={p.process} className="sp-row-card" data-rail="" data-tone={tone(word)}>
            <span className="sp-row-card-top">
              <OpenProcess name={p.process} w={w} onOpen={onOpen} />
              <Word state={word} word={word} />
            </span>
            <span className="sp-done">
              <Bar done={done} all={all} /> {done} / {all} {w.units}
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

function ProcessTable({ processes, ended, label, w, onOpen }: Rows) {
  const phone = usePhone();
  if (phone) return <ProcessCards processes={processes} ended={ended} label={label} w={w} onOpen={onOpen} />;
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
          {processes.map((p) => {
            const all = total(p.counts);
            const done = sum(p.counts, "succeeded", "cached", "stored");
            const word = processWord(p.counts, ended);
            return (
              <tr key={p.process}>
                <td>
                  <OpenProcess name={p.process} w={w} onOpen={onOpen} />
                </td>
                <td>
                  <Word state={word} word={word} />
                </td>
                <td>
                  {all ? (
                    <span className="sp-done">
                      <Bar done={done} all={all} /> {done} / {all}
                    </span>
                  ) : (
                    `0 ${w.units} yet`
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
  const note = run.stages_note ? (
    <p role="note" className="sp-muted">
      {run.stages_note}
    </p>
  ) : null;
  if (!stages.length) {
    return (
      <FoldSection id="processes" screen="run" icon={ICONS.list} title={w.Groups} summary={plural(processes.length, w.group, w.groups)}>
        {note}
        <p className="sp-muted">No stages for this pipeline: {w.groups} as the engine reports them.</p>
        <ProcessTable processes={processes} ended={ended} label={w.Groups} w={w} onOpen={onOpen} />
      </FoldSection>
    );
  }
  const loose = processes.filter((p) => !stages.some((s) => s.id === p.stage_id));
  const running = stages.filter((s) => s.state === "running").length;
  return (
    <FoldSection id="stages" screen="run" icon={ICONS.layers} title="Stages" summary={`${plural(stages.length, "stage", "stages")} · ${running} running`}>
      {note}
      <p className="sp-intro">
        {plural(stages.length, "stage", "stages")}, in order, each with its {w.groups} in the order {engine} first reported
        them. Open a stage to see its {w.groups}. A stage declared in <span className="sp-mono">spectio.yml</span> shows
        Declared; a detected one shows Detected and is for display only.{" "}
        <button type="button" className="sp-link-button" onClick={onTasks}>
          All {w.units} <Icon path={ICONS.arrowRight} size={13} />
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
                <Icon path={ICONS.chevronDown} size={16} stroke={2} />
              </span>
            </summary>
            <p className="sp-link-end">
              <button type="button" className="sp-link-button" aria-label={`Open stage ${stage.name ?? stage.id}`} onClick={() => onOpen({ kind: "stage", id: stage.id })}>
                Stage details <Icon path={ICONS.arrowRight} size={13} />
              </button>
            </p>
            <ProcessTable processes={mine} ended={ended} label={`${w.Groups} of ${stage.name ?? stage.id}`} w={w} onOpen={onOpen} />
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
              <Icon path={ICONS.chevronDown} size={16} stroke={2} />
            </span>
          </summary>
          <ProcessTable processes={loose} ended={ended} label={`${w.Groups} not in a stage`} w={w} onOpen={onOpen} />
        </details>
      )}
      <p className="sp-legend">
        Pending: no {w.unit} has started. Running: {w.units} are running, or some are done and more are to come. Done:
        every {w.unit} succeeded or was reused. Stopped: the run ended before it finished.
      </p>
    </FoldSection>
  );
}

/** "Why it failed", open first on a failed run (ui-spec §4.4, UX-PAR-25): the run-level part. The
 * per-job cards (SLURM state, resources, last lines) come with P1 Tasks 29 and 32. */
function WhyItFailed({ run, processes, onTasks, onOpen }: { run: RunDetail; processes: Process[]; onTasks: () => void; onOpen: (d: Detail) => void }) {
  const failure = run.failure as { class?: unknown; message?: unknown; task_id?: unknown } | null;
  const kind = typeof failure?.class === "string" ? failure.class : null;
  const message = typeof failure?.message === "string" ? failure.message.trim() : "";
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
        const found = page.items?.find((t) => t.id === culpritId);
        if (found) return setCulprit(found);
        cursor = page.next ?? null;
        if (!cursor) return;
      }
    };
    find().catch(() => undefined); // the line is extra: without it, the rest still says why
    return () => controller.abort();
  }, [run.id, culpritId]);
  const failed = run.summary.tasks.failed;
  const headline = failed > 0 ? `${plural(failed, unit, units)} failed, and the run stopped` : kind ? `The run stopped: ${classWord(kind)}` : "The run stopped";
  return (
    <FoldSection id="why" screen="run" icon={ICONS.alert} title="Why it failed" summary={kind ? classWord(kind) : undefined}>
      {failed > 0 && (
        <p className="sp-link-end">
          <button type="button" className="sp-link-button" onClick={onTasks}>
            {Units}, filtered to Failed <Icon path={ICONS.arrowRight} size={13} />
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
                  {w.Group} {lastSegment(culprit.process)} <Icon path={ICONS.arrowRight} size={13} />
                </button>
              </>
            )}
          </p>
        )}
      </div>
    </FoldSection>
  );
}

/** How to look at the head by hand: ssh and tmux attach with tmux heads; the process with the
 * local executor, whose head has no terminal (P1 Task 9; tmux heads come with Task 10). */
function HeadByHand({ run, server }: { run: RunDetail; server: ServerVersion | null }) {
  const head = run.head!;
  const local = server?.executor === "local";
  const pid = head.session?.split(".")[0] ?? "";
  const commands = local ? `ps -o pid,etime,args --sid ${pid}` : `ssh ${head.node}\ntmux attach -t ${head.session}`;
  return (
    <FoldSection id="attach" screen="run" icon={ICONS.terminal} title="Open the head by hand" summary={local ? `process ${pid}` : `tmux on ${head.node}`} card>
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

/** The last lines of a log, read once when the section opens. */
function LogTail({ id, source, ended, onAll }: { id: string; source: LogSource; ended: boolean; onAll: (s: LogSource) => void }) {
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getLog(id, source, controller.signal)
      .then((t) => setText(t.trimEnd().split("\n").slice(-6).join("\n") || (ended ? "Empty." : "Empty so far.")))
      .catch((e: ApiError) => controller.signal.aborted || setText(e.status === 404 ? "Not written yet." : `Could not read it: ${e.message}`));
    return () => controller.abort();
  }, [id, source, ended]);
  const label = LOGS.find((l) => l.source === source)!.label;
  return (
    <>
      <pre className="sp-code sp-log-tail sp-nowrap" tabIndex={0} aria-label={`${label}, last lines`}>
        {text === null ? "Loading…" : <LogLines text={text} />}
      </pre>
      <button type="button" className="sp-link-button" onClick={() => onAll(source)}>
        All logs: head output, head errors, engine log <Icon path={ICONS.arrowRight} size={13} />
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
function SummaryAside({ run, server, onLogs }: { run: RunDetail; server: ServerVersion | null; onLogs: (s: LogSource) => void }) {
  const head = run.head;
  const failed = run.state === "failed";
  const params = Object.keys(run.params).length;
  return (
    <aside className="sp-aside" aria-label="About this run">
      {head?.alive && head.session && run.origin !== "cli-observed" && <HeadByHand run={run} server={server} />}
      <FoldSection
        id={failed ? "head-err" : "engine-log"}
        screen="run"
        icon={ICONS.file}
        title={failed ? "Head errors · last lines" : "Engine log · last lines"}
        card
      >
        <LogTail id={run.id} source={failed ? "head-err" : "engine"} ended={isTerminal(run.state)} onAll={onLogs} />
      </FoldSection>
      {head && !head.alive && run.origin !== "cli-observed" && (
        <FoldSection
          id="head-ended"
          screen="run"
          icon={ICONS.power}
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
      <FoldSection id="params" screen="run" icon={ICONS.sliders} title="Parameters" summary={`${params} set at launch`} defaultOpen={false} card>
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

type Shown = { rows: Task[]; next: string | null };

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

/** A refresh: the fresh first page, then the rows Load more added past it, and their cursor. */
function refresh(shown: Shown | null, page: Page<Task>): Shown {
  const fresh = page.items ?? [];
  const last = fresh[fresh.length - 1];
  const tail = shown && last && page.next ? shown.rows.filter((t) => t.id > last.id) : [];
  return tail.length ? { rows: [...fresh, ...tail], next: shown!.next } : { rows: fresh, next: page.next ?? null };
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
  return (
    <section className="sp-runs" aria-label={w.Units}>
      <div className="sp-filters">
        <div className="sp-segments" role="group" aria-label={`Show ${w.units}`}>
          {TASK_FILTERS.map((f, i) => (
            <button key={f.label} type="button" aria-pressed={filter === i} onClick={() => setFilter(i)}>
              {f.label}
              <span className="sp-count">{count(f.states)}</span>
            </button>
          ))}
        </div>
        <label className="sp-select">
          {w.Group}{" "}
          <select value={process} onChange={(e) => setProcess(e.currentTarget.value)}>
            <option value="">
              All {w.groups} ({processes.length})
            </option>
            {processes.map((p) => (
              <option key={p.process} value={p.process}>
                {lastSegment(p.process)} ({total(p.counts)})
              </option>
            ))}
            {process && !processes.some((p) => p.process === process) && <option value={process}>{lastSegment(process)}</option>}
          </select>
        </label>
      </div>
      <p className="sp-sub">
        <span>In the order {engineName(run.workflow.engine)} first reported them</span>
        {active && <LiveStatus />}
      </p>
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
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td data-rail="" data-tone={tone(t.state)} className="sp-task">
                    <OpenTask task={t} w={w} onOpen={onOpen} />
                  </td>
                  <td>
                    <Word state={t.state} word={taskWord(t.state)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
}: {
  run: RunDetail;
  server: ServerVersion | null;
  source: LogSource;
  setSource: (s: LogSource) => void;
  onTasks: () => void;
}) {
  const [text, setText] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const w = words(run.workflow.engine);
  useEffect(() => {
    const controller = new AbortController();
    setText(null);
    getLog(run.id, source, controller.signal)
      .then(setText)
      .catch((e: ApiError) => controller.signal.aborted || setText(e.status === 404 ? "Not written yet." : `Could not read it: ${e.message}`));
    return () => controller.abort();
  }, [run.id, source, reloads]);
  // The public demo has no server behind /api: Open raw opens the text shown, as a blob.
  const [demoRaw, setDemoRaw] = useState<string | null>(null);
  useEffect(() => {
    if (import.meta.env.MODE !== "demo" || text === null) return;
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    setDemoRaw(url);
    return () => {
      URL.revokeObjectURL(url);
      setDemoRaw(null);
    };
  }, [text]);
  const raw = import.meta.env.MODE === "demo" ? demoRaw : logUrl(run.id, source);
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
      <div className="sp-filters sp-log-tools">
        <div className="sp-segments" role="group" aria-label="Log">
          {LOGS.map((l) => (
            <button key={l.source} type="button" aria-pressed={source === l.source} onClick={() => setSource(l.source)}>
              {l.label}
            </button>
          ))}
        </div>
        <span className="sp-muted sp-grow">
          {DESCRIPTIONS[source](engineName(run.workflow.engine))} · last 64 KiB · loaded when you open it
        </span>
        <span className="sp-actions">
          <Button variant="default" leftSection={<Icon path={ICONS.reload} size={15} />} onClick={() => setReloads((n) => n + 1)}>
            Reload
          </Button>
          <Button variant="default" leftSection={<Icon path={ICONS.download} size={15} />} onClick={download} disabled={text === null}>
            Download last 64 KiB
          </Button>
          <Button
            component="a"
            variant="default"
            href={raw ?? undefined}
            disabled={raw === null}
            target="_blank"
            rel="noopener noreferrer"
            leftSection={<Icon path={ICONS.externalLink} size={15} />}
          >
            Open raw<span className="sp-sr"> (opens in a new tab)</span>
          </Button>
        </span>
      </div>
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
      <LogViewer text={text} label={label} />
      <p className="sp-log-note">
        <Icon path={ICONS.file} size={15} stroke={1.6} />
        <span>
          {run.workflow.engine === "snakemake"
            ? "Each job's own log, as its rule declares it, is not in these logs:"
            : "Each task's own files (.command.log, .command.err, .command.sh …) stay in its work directory, not in these logs:"}{" "}
          <button type="button" className="sp-link-button" onClick={onTasks}>
            open a {w.unit} in {w.Units} <Icon path={ICONS.arrowRight} size={13} />
          </button>
        </span>
      </p>
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
    <Modal opened={opened} onClose={onClose} title="Cancel this run?" returnFocus centered>
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
      <div className="sp-actions">
        <Button variant="default" data-autofocus onClick={onClose}>
          Keep running
        </Button>
        <Button color="red" onClick={onConfirm}>
          Cancel the run
        </Button>
      </div>
    </Modal>
  );
}

/** The run detail (ui-spec §4.4, 0.0.1): the shared header with Cancel, the facts and counts, then
 * Summary (why it failed, stages or processes, and the aside), Tasks, Parameters and Logs;
 * refetched on each stream frame for the run until it ends. */
export function RunDetailPage({ id }: { id: string }) {
  const valid = RUN_ID.test(id);
  const server = useServer();
  const phone = usePhone();
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
  // the last picked log source, so Logs reopens on it after another tab
  const lastSource = useRef(logSource);
  const go = useCallback(
    (to: Tab, opts: { source?: LogSource; process?: string } = {}) => {
      if (to === "logs") lastSource.current = opts.source ?? lastSource.current;
      return navigate({ search: runSearch({ tab: to, source: lastSource.current, process: opts.process }), replace: true });
    },
    [navigate],
  );
  const [taskFilter, setTaskFilter] = useState<number | null>(null);
  // the detail sheet's views, the shown one last (DetailSheet)
  const [views, setViews] = useState<Detail[]>([]);
  const title = useRef<HTMLHeadingElement>(null);
  const panels = { tasks: useRef<HTMLDivElement>(null), logs: useRef<HTMLDivElement>(null) };
  const focusPanel = useRef(false);
  useEffect(() => {
    if (focusPanel.current && (tab === "tasks" || tab === "logs")) panels[tab].current?.focus();
    focusPanel.current = false;
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
  // The Summary's log links open Logs on the same source, with focus on its panel.
  const showLogs = (source: LogSource) => {
    focusPanel.current = true;
    go("logs", { source });
  };
  // The sheet's Open in Tasks: the Tasks tab on that process, every state.
  const showProcess = (process: string) => {
    setViews([]);
    setTaskFilter(0);
    focusTasks(process);
    go("tasks", { process });
  };
  const w = words(run.workflow.engine);
  const params = Object.keys(run.params).length;

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
      />
      <DetailSheet
        run={run}
        stages={stages}
        processes={processes}
        views={views}
        onOpen={(view) => setViews((shown) => [...shown, view])}
        onBack={() => setViews((shown) => shown.slice(0, -1))}
        onClose={() => setViews([])}
        onTasks={showProcess}
      />
      <CancelDialog run={run} server={server} opened={asking} onClose={() => setAsking(false)} onConfirm={confirm} />

      <Tabs value={tab} onChange={(t) => go(TABS.find((x) => x === t) ?? "summary")} keepMounted={false}>
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
            <SummaryAside run={run} server={server} onLogs={showLogs} />
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
          {params === 0 ? (
            <p className="sp-empty">No parameters were set at launch.</p>
          ) : phone ? (
            <div className="sp-card">
              <ParamsList params={run.params} />
            </div>
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
                  {Object.entries(run.params).map(([key, value]) => (
                    <tr key={key}>
                      <td className="sp-mono">{key}</td>
                      <td>{typeof value === "string" ? value : JSON.stringify(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Tabs.Panel>
        <Tabs.Panel value="logs" pt="md" ref={panels.logs} tabIndex={-1}>
          <LogsPanel run={run} server={server} source={logSource} setSource={(source) => go("logs", { source })} onTasks={() => go("tasks")} />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
}
