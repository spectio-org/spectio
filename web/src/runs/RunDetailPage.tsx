import { Button, Modal, Tabs } from "@mantine/core";
import { Link } from "@tanstack/react-router";
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
} from "../api";
import { ICONS, Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { FoldSection } from "../shell/FoldSection";
import { RunHeader } from "./RunHeader";
import { Word, runName } from "./RunState";
import {
  classWord,
  engineName,
  isTerminal,
  plural,
  processWord,
  stageWord,
  taskWord,
  tone,
  words,
} from "./stateWord";

const RUN_ID = /^run_[0-7][0-9A-HJKMNP-TV-Z]{25}$/; // api §7, as the server checks it
const CANCELLABLE = new Set(["queued", "running"]);
const LOGS: { source: LogSource; label: string }[] = [
  { source: "head-out", label: "Head output" },
  { source: "head-err", label: "Head errors" },
  { source: "engine", label: "Engine log" },
];

type Words = ReturnType<typeof words>;

const sum = (counts: Record<string, number>, ...states: string[]) => states.reduce((n, s) => n + (counts[s] ?? 0), 0);
const total = (counts: Record<string, number>) => Object.values(counts).reduce((a, b) => a + b, 0);
const lastSegment = (name: string) => name.split(":").pop() ?? name;

/** The last segment of a process name; the full name stays its accessible text (ui-spec §4.4). */
function ProcessName({ name }: { name: string }) {
  const last = lastSegment(name);
  if (last === name) return <span className="sp-mono">{name}</span>;
  return (
    <span className="sp-mono">
      <span aria-hidden="true">{last}</span>
      <span className="sp-sr">{name}</span>
    </span>
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

function ProcessTable({ processes, ended, label, w }: { processes: Process[]; ended: boolean; label: string; w: Words }) {
  return (
    <div className="sp-table-wrap">
      <table className="sp-table" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">{w.Group}, first-seen order</th>
            <th scope="col">State</th>
            <th scope="col">{w.units[0].toUpperCase() + w.units.slice(1)} done</th>
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
                  <ProcessName name={p.process} />
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
}: {
  run: RunDetail;
  stages: Stage[];
  processes: Process[];
  onTasks: () => void;
}) {
  const ended = isTerminal(run.state);
  const w = words(run.workflow.engine);
  const engine = engineName(run.workflow.engine);
  if (!stages.length) {
    return (
      <FoldSection id="processes" screen="run" icon={ICONS.list} title={w.Groups} summary={plural(processes.length, w.group, w.groups)}>
        <p className="sp-muted">No stages for this pipeline: {w.groups} as the engine reports them.</p>
        <ProcessTable processes={processes} ended={ended} label={w.Groups} w={w} />
      </FoldSection>
    );
  }
  const loose = processes.filter((p) => !stages.some((s) => s.id === p.stage_id));
  const running = stages.filter((s) => s.state === "running").length;
  return (
    <FoldSection id="stages" screen="run" icon={ICONS.layers} title="Stages" summary={`${plural(stages.length, "stage", "stages")} · ${running} running`}>
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
            <ProcessTable processes={mine} ended={ended} label={`${w.Groups} of ${stage.name ?? stage.id}`} w={w} />
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
          <ProcessTable processes={loose} ended={ended} label={`${w.Groups} not in a stage`} w={w} />
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
function WhyItFailed({ run, onTasks }: { run: RunDetail; onTasks: () => void }) {
  const failure = run.failure as { class?: unknown; message?: unknown } | null;
  const kind = typeof failure?.class === "string" ? failure.class : null;
  const message = typeof failure?.message === "string" ? failure.message.trim() : "";
  const { unit, units } = words(run.workflow.engine);
  const failed = run.summary.tasks.failed;
  const headline = failed > 0 ? `${plural(failed, unit, units)} failed, and the run stopped` : kind ? `The run stopped: ${classWord(kind)}` : "The run stopped";
  return (
    <FoldSection id="why" screen="run" icon={ICONS.alert} title="Why it failed" summary={kind ? classWord(kind) : undefined}>
      {failed > 0 && (
        <p className="sp-link-end">
          <button type="button" className="sp-link-button" onClick={onTasks}>
            Tasks, filtered to Failed <Icon path={ICONS.arrowRight} size={13} />
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
      </div>
    </FoldSection>
  );
}

/** Copies `text`; says so in a status line, or says why not. */
function CopyButton({ text, label, name }: { text: string; label: string; name: string }) {
  const [said, setSaid] = useState<string | null>(null);
  const copy = () =>
    (navigator.clipboard?.writeText(text) ?? Promise.reject(new Error("no clipboard")))
      .then(() => setSaid("Copied"))
      .catch(() => setSaid("Could not copy: select the text instead"));
  return (
    <span className="sp-actions">
      <Button variant="light" size="xs" aria-label={name} onClick={copy}>
        {label}
      </Button>
      <span role="status" className="sp-muted">
        {said}
      </span>
    </span>
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
      <pre className="sp-code sp-log-tail" tabIndex={0} aria-label={`${label}, last lines`}>
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
}: {
  run: RunDetail;
  processes: Process[];
  filter: number;
  setFilter: (i: number) => void;
}) {
  const id = run.id;
  const w = words(run.workflow.engine);
  const [process, setProcess] = useState("");
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
    <section className="sp-runs" aria-label={w.units === "jobs" ? "Jobs" : "Tasks"}>
      <div className="sp-filters">
        <div className="sp-segments" role="group" aria-label="Show tasks">
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
      {!!tasks?.length && (
        <div className="sp-table-wrap">
          <table className="sp-table" aria-label="Tasks">
            <thead>
              <tr>
                <th scope="col">{w.units === "jobs" ? "Job" : "Task"}</th>
                <th scope="col">State</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td data-rail="" data-tone={tone(t.state)} className="sp-task">
                    <strong>
                      <ProcessName name={t.process} />
                    </strong>
                    {(t.tag ?? t.name) && <> ({t.tag ?? t.name})</>}
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

/** A log line's level, as a secondary tint: the level word is in the text already. */
const level = (line: string) => (/\bERROR\b|\bError\b|exception/.test(line) ? "failed" : /\bWARN|\bretry/i.test(line) ? "review" : undefined);

/** A log's lines, each tinted by its level. */
function LogLines({ text }: { text: string }) {
  return text.split("\n").map((line, i) => (
    <span key={i} data-tone={level(line)}>
      {line}
      {"\n"}
    </span>
  ));
}

function LogsPanel({ run, source, setSource }: { run: RunDetail; source: LogSource; setSource: (s: LogSource) => void }) {
  const [text, setText] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setText(null);
    getLog(run.id, source, controller.signal)
      .then(setText)
      .catch((e: ApiError) => controller.signal.aborted || setText(e.status === 404 ? "Not written yet." : `Could not read it: ${e.message}`));
    return () => controller.abort();
  }, [run.id, source, reloads]);
  const label = LOGS.find((l) => l.source === source)!.label;
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
    <section className="sp-runs" aria-label="Logs">
      <div className="sp-filters">
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
        <Button variant="default" leftSection={<Icon path={ICONS.reload} size={15} />} onClick={() => setReloads((n) => n + 1)}>
          Reload
        </Button>
        <Button variant="default" leftSection={<Icon path={ICONS.download} size={15} />} onClick={download} disabled={text === null}>
          Download last 64 KiB
        </Button>
      </div>
      <pre className="sp-log" aria-label={label}>
        {text === null ? "Loading…" : <LogLines text={text} />}
      </pre>
      <p className="sp-muted">
        {run.workflow.engine === "snakemake"
          ? "Each job's own log, as its rule declares it, is not in these logs."
          : "Each task's own files (.command.log, .command.err, .command.sh …) stay in its work directory, not in these logs."}
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
  const [run, setRun] = useState<RunDetail | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [missing, setMissing] = useState(!valid);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [tab, setTab] = useState<string | null>("summary");
  const [taskFilter, setTaskFilter] = useState<number | null>(null);
  const [logSource, setLogSource] = useState<LogSource>("engine");
  const title = useRef<HTMLHeadingElement>(null);

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
  const showFailedTasks = () => {
    setTaskFilter(TASK_FILTERS.findIndex((f) => f.label === "Failed"));
    setTab("tasks");
  };
  const showLogs = (source: LogSource) => {
    setLogSource(source);
    setTab("logs");
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
      />
      <CancelDialog run={run} server={server} opened={asking} onClose={() => setAsking(false)} onConfirm={confirm} />

      <Tabs value={tab} onChange={setTab} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="summary">Summary</Tabs.Tab>
          <Tabs.Tab value="tasks">{w.units === "jobs" ? "Jobs" : "Tasks"}</Tabs.Tab>
          <Tabs.Tab value="parameters">Parameters</Tabs.Tab>
          <Tabs.Tab value="logs">Logs</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="summary" pt="md">
          <div className="sp-detail-grid">
            <div className="sp-runs">
              {run.state === "failed" && <WhyItFailed run={run} onTasks={showFailedTasks} />}
              <StagesOrProcesses run={run} stages={stages} processes={processes} onTasks={() => setTab("tasks")} />
            </div>
            <SummaryAside run={run} server={server} onLogs={showLogs} />
          </div>
        </Tabs.Panel>
        <Tabs.Panel value="tasks" pt="md">
          <TasksPanel run={run} processes={processes} filter={filter} setFilter={setTaskFilter} />
        </Tabs.Panel>
        <Tabs.Panel value="parameters" pt="md">
          {Object.keys(run.params).length === 0 ? (
            <p className="sp-empty">No parameters were set at launch.</p>
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
        <Tabs.Panel value="logs" pt="md">
          <LogsPanel run={run} source={logSource} setSource={setLogSource} />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
}
