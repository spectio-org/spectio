import { Button, Modal, Tabs } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  type LogSource,
  type Process,
  type RunDetail,
  type Stage,
  type Task,
  cancelRun,
  getLog,
  getRun,
  listProcesses,
  listStages,
  listTasks,
} from "../api";
import { LiveStatus, useFrames } from "../live";
import { usePageCrumb } from "../shell/crumb";
import { StateWord, runName, tasksText } from "./RunState";
import { duration, isTerminal, processWord, shortId, stageWord, stagesLine, when } from "./stateWord";

const RUN_ID = /^run_[0-7][0-9A-HJKMNP-TV-Z]{25}$/; // api §7, as the server checks it
const CANCELLABLE = new Set(["queued", "running"]);
const TASK_STATES = ["pending", "submitted", "running", "succeeded", "failed", "cached", "stored", "aborted", "not_scheduled"];
const LOGS: { source: LogSource; label: string }[] = [
  { source: "head-out", label: "Head output" },
  { source: "head-err", label: "Head errors" },
  { source: "engine", label: "Engine log" },
];

/** The last segment of a process name; the full name stays its accessible text (ui-spec §4.4). */
function ProcessName({ name }: { name: string }) {
  const last = name.split(":").pop() ?? name;
  if (last === name) return <span className="sp-mono">{name}</span>;
  return (
    <span className="sp-mono">
      <span aria-hidden="true">{last}</span>
      <span className="sp-sr">{name}</span>
    </span>
  );
}

const sum = (counts: Record<string, number>, ...states: string[]) =>
  states.reduce((n, s) => n + (counts[s] ?? 0), 0);

function ProcessTable({ processes, ended, label }: { processes: Process[]; ended: boolean; label: string }) {
  return (
    <div className="sp-table-wrap">
      <table className="sp-table" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">Process, first-seen order</th>
            <th scope="col">State</th>
            <th scope="col">Tasks done</th>
            <th scope="col" className="sp-num" data-narrow="">Running</th>
            <th scope="col" className="sp-num" data-narrow="">Pending</th>
            <th scope="col" className="sp-num">Failed</th>
            <th scope="col" className="sp-num" data-narrow="">Retried</th>
          </tr>
        </thead>
        <tbody>
          {processes.map((p) => {
            const total = Object.values(p.counts).reduce((a, b) => a + b, 0);
            return (
              <tr key={p.process}>
                <td>
                  <ProcessName name={p.process} />
                </td>
                <td>{processWord(p.counts, ended)}</td>
                <td>{total ? `${sum(p.counts, "succeeded", "cached", "stored")} / ${total}` : "0 tasks yet"}</td>
                <td className="sp-num" data-narrow="">{sum(p.counts, "running")}</td>
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
function StagesOrProcesses({ stages, processes, ended }: { stages: Stage[]; processes: Process[]; ended: boolean }) {
  if (!stages.length) {
    return (
      <section className="sp-section" aria-labelledby="processes-title">
        <h2 id="processes-title">Processes</h2>
        <p className="sp-muted">No stages for this pipeline: processes as the engine reports them.</p>
        <ProcessTable processes={processes} ended={ended} label="Processes" />
      </section>
    );
  }
  const loose = processes.filter((p) => !stages.some((s) => s.id === p.stage_id));
  return (
    <section className="sp-section" aria-labelledby="stages-title">
      <h2 id="stages-title">Stages</h2>
      {stages.map((stage) => {
        const total = Object.values(stage.task_counts).reduce((a, b) => a + b, 0);
        const done = sum(stage.task_counts, "succeeded", "cached", "stored");
        const mine = processes.filter((p) => p.stage_id === stage.id);
        return (
          <details key={stage.id} className="sp-stage" open={stage.state === "running"}>
            <summary>
              <span className="sp-id">{stage.position}</span>
              <span className="sp-grow">{stage.name ?? stage.id}</span>
              <span className="sp-chip">{stage.source === "declared" ? "Declared" : "Detected"}</span>
              <span>{stageWord(stage, ended)}</span>
              <span>
                {done} of {total} tasks
              </span>
            </summary>
            <ProcessTable processes={mine} ended={ended} label={`Processes of ${stage.name ?? stage.id}`} />
          </details>
        );
      })}
      {loose.length > 0 && (
        <details className="sp-stage">
          <summary>
            <span className="sp-grow">Not in a stage</span>
          </summary>
          <ProcessTable processes={loose} ended={ended} label="Processes not in a stage" />
        </details>
      )}
    </section>
  );
}

function head(run: RunDetail): string {
  if (!run.head) return "Head not started yet";
  if (run.origin === "cli-observed") return `head on ${run.head.node}, not checked`;
  const state = run.head.alive ? "alive" : "exited";
  return `${run.head.session ?? "no session"} · ${state} · on ${run.head.node}`;
}

function Facts({ run }: { run: RunDetail }) {
  const w = run.workflow;
  const failure = run.failure as { class?: string; message?: string } | null;
  const rows: [string, string][] = [
    ["Pipeline", [w.name ?? "—", w.version].filter(Boolean).join(" ")],
    ["Pipeline directory", w.location],
    ["Engine", [w.engine ?? "—", w.engine_version].filter(Boolean).join(" ")],
    ["Profile", run.profiles.join(", ") || "(none)"],
    ["Started", when(run.started_at)],
    ["Ended", when(run.ended_at)],
    ["Duration", duration(run.started_at, run.ended_at)],
    ["Head", head(run)],
    ["Exit code", run.head?.exit_code === null || !run.head ? "—" : String(run.head.exit_code)],
    ["Failure", failure ? [failure.class, failure.message].filter(Boolean).join(": ") : "—"],
  ];
  return (
    <div className="sp-table-wrap">
      <table className="sp-table sp-facts" aria-label="Facts">
        <tbody>
          {rows.map(([name, value]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TasksPanel({ id, failed, processes }: { id: string; failed: boolean; processes: Process[] }) {
  const [state, setState] = useState(failed ? "failed" : "");
  const [process, setProcess] = useState("");
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [next, setNext] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setTasks(null);
    listTasks(id, { state, process, limit: 50 }, controller.signal)
      .then((page) => {
        setTasks(page.items);
        setNext(page.next);
        setError(null);
      })
      .catch((e: Error) => controller.signal.aborted || setError(e.message));
    return () => controller.abort();
  }, [id, state, process]);
  const more = () =>
    listTasks(id, { state, process, limit: 50, cursor: next })
      .then((page) => {
        setTasks((shown) => [...(shown ?? []), ...page.items]);
        setNext(page.next);
      })
      .catch((e: Error) => setError(e.message));
  return (
    <section className="sp-section" aria-label="Tasks">
      <div className="sp-filters">
        <label>
          State{" "}
          <select value={state} onChange={(e) => setState(e.currentTarget.value)}>
            <option value="">All states</option>
            {TASK_STATES.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label>
          Process{" "}
          <select value={process} onChange={(e) => setProcess(e.currentTarget.value)}>
            <option value="">All processes</option>
            {processes.map((p) => (
              <option key={p.process} value={p.process}>
                {p.process} ({Object.values(p.counts).reduce((a, b) => a + b, 0)})
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p role="alert">The tasks could not be read: {error}</p>}
      {tasks === null && !error && <p className="sp-muted">Loading the tasks…</p>}
      {tasks?.length === 0 && <p className="sp-empty">No task matches these filters.</p>}
      {!!tasks?.length && (
        <div className="sp-table-wrap">
          <table className="sp-table" aria-label="Tasks">
            <thead>
              <tr>
                <th scope="col">Process</th>
                <th scope="col">Tag</th>
                <th scope="col">State</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td>
                    <ProcessName name={t.process} />
                  </td>
                  <td>{t.tag ?? t.name ?? "—"}</td>
                  <td>{t.state.replace("_", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {next && (
        <Button variant="default" mt="sm" onClick={more}>
          Load more tasks
        </Button>
      )}
    </section>
  );
}

function LogsPanel({ id }: { id: string }) {
  const [source, setSource] = useState<LogSource | null>(null);
  const [text, setText] = useState<string | null>(null);
  const show = (s: LogSource) => {
    setSource(s);
    setText(null);
    getLog(id, s)
      .then(setText)
      .catch((e: ApiError) => setText(e.status === 404 ? "Not written yet." : `Could not read it: ${e.message}`));
  };
  return (
    <section className="sp-section" aria-label="Logs">
      <div className="sp-actions">
        {LOGS.map((l) => (
          <Button key={l.source} variant={source === l.source ? "light" : "default"} aria-pressed={source === l.source} onClick={() => show(l.source)}>
            {l.label}
          </Button>
        ))}
      </div>
      {source && (
        <pre className="sp-log" aria-label={LOGS.find((l) => l.source === source)?.label}>
          {text ?? "Loading…"}
        </pre>
      )}
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

/** The run detail (ui-spec §4.4, 0.0.1): header with Cancel, facts, counts, stages or processes,
 * then tasks, parameters and logs; refetched on each stream frame for the run until it ends. */
export function RunDetailPage({ id }: { id: string }) {
  const valid = RUN_ID.test(id);
  const [run, setRun] = useState<RunDetail | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [missing, setMissing] = useState(!valid);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
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

  const ended = isTerminal(run.state);
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
  const counts = Object.entries(run.task_counts).filter(([, n]) => n > 0);
  const line = stagesLine(stages);

  return (
    <div className="sp-runs">
      <header className="sp-card sp-head" data-rail={run.state}>
        <div>
          <h1 ref={title} tabIndex={-1} className="sp-page-title">
            {name}
          </h1>
          <p className="sp-sub sp-page-sub">
            <span className="sp-id">{shortId(run.id)}</span>
            <StateWord state={run.state} />
            {line && <span>{line}</span>}
            <span>{tasksText(run)} tasks</span>
            <span>{duration(run.started_at, run.ended_at)}</span>
            {!ended && <LiveStatus />}
          </p>
          {cancelError && <p role="alert">Cancel failed: {cancelError}</p>}
        </div>
        {canCancel && (
          <Button ref={cancelButton} color="red" variant="outline" onClick={() => setAsking(true)}>
            Cancel run
          </Button>
        )}
      </header>

      <Modal
        opened={asking}
        onClose={() => setAsking(false)}
        title="Cancel this run?"
        returnFocus
        centered
      >
        <p>Spectio interrupts its head in the tmux session, and the engine stops its tasks.</p>
        <div className="sp-actions">
          <Button variant="default" data-autofocus onClick={() => setAsking(false)}>
            Keep running
          </Button>
          <Button color="red" onClick={confirm}>
            Cancel the run
          </Button>
        </div>
      </Modal>

      <Tabs defaultValue="summary" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="summary">Summary</Tabs.Tab>
          <Tabs.Tab value="tasks">Tasks</Tabs.Tab>
          <Tabs.Tab value="parameters">Parameters</Tabs.Tab>
          <Tabs.Tab value="logs">Logs</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="summary" pt="md">
          <div className="sp-runs">
            <Facts run={run} />
            {counts.length > 0 && (
              <ul className="sp-counts" aria-label="Tasks by state">
                {counts.map(([state, n]) => (
                  <li key={state} className="sp-chip">
                    {n} {state.replace("_", " ")}
                  </li>
                ))}
              </ul>
            )}
            <StagesOrProcesses stages={stages} processes={processes} ended={ended} />
          </div>
        </Tabs.Panel>
        <Tabs.Panel value="tasks" pt="md">
          <TasksPanel id={id} failed={run.state === "failed"} processes={processes} />
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
          <LogsPanel id={id} />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
}
