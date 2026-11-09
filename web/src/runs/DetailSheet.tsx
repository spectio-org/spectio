import { Button, Drawer } from "@mantine/core";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { type Counts, type Process, type RunDetail, type Stage, type Task, listTasks } from "../api";
import { ICONS, Icon } from "../icons";
import { useFrames } from "../live";
import { usePhone } from "../shell/layout";
import { bytes, nearLimit, seconds } from "./resources";
import { efficiencyFacts } from "./ByProcess";
import { NearLimit, Word, taskLabel } from "./RunState";
import { Facts, SlurmFacts } from "./SlurmFacts";
import { TaskFiles } from "./TaskFiles";
import { type Shown, isTerminal, lastSegment, neededFirst, processState, refresh, stageWord, sum, taskWord, total, words } from "./stateWord";

// The detail of a stage, a process (a rule) or a task (a job), in a side sheet (LiteTaskFiles,
// MLiteTaskFilesSheet; P3-parD, Thomas 2026-10-31: "steps & stages pas clickable, pas de détails"):
// a right sheet on a desktop, full screen on the phone; Mantine's Drawer is aria-modal, traps focus,
// closes on Escape and returns focus to its opener (ui-spec §4.11). A stage lists its processes, a
// process its tasks (GET /tasks?process=, paged), a task what 0.0.1 serves of it; each view opens the
// next, and Back returns. A task shows its attempt, its resources and its files (TaskFiles, P1
// Task 32 on Tasks 28 and 29's routes).

/** `attempt`: a task's sheet reopened from the run's URL, on that attempt, focus on its title. */
export type Detail = { kind: "stage"; id: string } | { kind: "process"; name: string } | { kind: "task"; task: Task; attempt?: number };

interface Props {
  run: RunDetail;
  stages: Stage[];
  processes: Process[];
  /** The views opened, the shown one last. */
  views: Detail[];
  onOpen: (view: Detail) => void;
  onBack: () => void;
  onClose: () => void;
  onTasks: (process: string) => void;
}

function title(view: Detail, stages: Stage[]): string {
  if (view.kind === "process") return lastSegment(view.name);
  if (view.kind === "task") return taskLabel(view.task);
  const stage = stages.find((s) => s.id === view.id);
  return stage?.name ?? view.id;
}

/** "Stage 2 · Align", or "Not in a stage". */
function stageLine(id: string | null, stages: Stage[]): string {
  const stage = stages.find((s) => s.id === id);
  return stage ? `Stage ${stage.position} · ${stage.name ?? stage.id}` : "Not in a stage";
}

/** The counts as chips: done of all, then running, pending, failed, cached and retried. */
function CountChips({ counts, retries, label }: { counts: Counts; retries: number; label: string }) {
  const chips = [
    { text: `${sum(counts, "succeeded", "cached", "stored")} of ${total(counts)} done`, tone: "succeeded" },
    { text: `${sum(counts, "running")} running`, tone: "running" },
    { text: `${sum(counts, "pending", "submitted")} pending`, tone: "queued" },
    { text: `${sum(counts, "failed")} failed`, tone: "failed" },
    { text: `${sum(counts, "cached", "stored")} cached`, tone: "cached" },
    { text: `${retries} retried`, tone: "review" },
  ];
  return (
    <ul className="sp-counts" aria-label={label}>
      {chips.map((chip) => (
        <li key={chip.tone} className="sp-chip" data-tone={chip.tone}>
          {chip.text}
        </li>
      ))}
    </ul>
  );
}

/** A process's tasks, 50 at a time, each opening its detail, read again on each frame of an active
 * run (FU-P3-80). Every row has the same two columns, named by a header: the task, then its state. */
function ProcessTasks({ run, process, name, onOpen }: { run: RunDetail; process: string; name: string; onOpen: (t: Task) => void }) {
  const w = words(run.workflow.engine);
  const [shown, setShown] = useState<Shown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reads = useRef(0); // only the latest first page is shown
  const first = (signal?: AbortSignal) => {
    const mine = ++reads.current;
    return listTasks(run.id, { process, limit: 50 }, signal)
      .then((page) => {
        if (mine !== reads.current) return;
        setShown((s) => refresh(s, page));
        setError(null);
      })
      .catch((e: Error) => signal?.aborted || mine !== reads.current || setError(e.message));
  };
  // a Load more in flight: a second click meanwhile would add the same page twice
  const [loading, setLoading] = useState(false);
  const more = (cursor: string) => {
    if (loading) return;
    setLoading(true);
    listTasks(run.id, { process, limit: 50, cursor })
      .then((page) => {
        setShown((s) => ({ rows: [...(s?.rows ?? []), ...(page.items ?? [])], next: page.next ?? null }));
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    const controller = new AbortController();
    setShown(null);
    first(controller.signal);
    return () => controller.abort();
  }, [run.id, process]);
  useFrames(() => first(), run.id, !isTerminal(run.state));
  // a failed re-read keeps the rows (and the focused one) under the alert (CR-P3FU80-02)
  const alert = error && <p role="alert">The {w.units} could not be read: {error}</p>;
  if (shown === null) return alert || <p className="sp-muted">Loading the {w.units}…</p>;
  if (!shown.rows.length) return alert || <p className="sp-muted">No {w.unit} reported yet.</p>;
  return (
    <>
      {alert}
      <div className="sp-task-head" aria-hidden="true">
        <span>{w.Unit}</span>
        <span>State</span>
      </div>
      <ul className="sp-sheet-list sp-task-rows" aria-label={`${w.Units} of ${name}`}>
        {shown.rows.map((t) => (
          <li key={t.id}>
            <button
              type="button"
              className="sp-sheet-row"
              aria-label={`Open ${w.unit} ${taskLabel(t)}, ${taskWord(t.state)}`}
              onClick={() => onOpen(t)}
            >
              <span className="sp-mono">{taskLabel(t)}</span>
              <Word state={t.state} word={taskWord(t.state)} />
            </button>
          </li>
        ))}
      </ul>
      {shown.next && (
        <div>
          <Button variant="default" aria-busy={loading} disabled={loading} onClick={() => more(shown.next!)}>
            Load more {w.units}
          </Button>
        </div>
      )}
    </>
  );
}

function ProcessView({ run, stages, process, onOpen, onTasks }: { run: RunDetail; stages: Stage[]; process: Process; onOpen: Props["onOpen"]; onTasks: Props["onTasks"] }) {
  const w = words(run.workflow.engine);
  const name = lastSegment(process.process);
  const { state, word } = processState(process, isTerminal(run.state), run.summary.open_checkpoints);
  const efficiency = efficiencyFacts(process.efficiency, w);
  return (
    <>
      <p className="sp-mono sp-sheet-name">{process.process}</p>
      <p className="sp-sub">
        <Word state={state} word={word} />
        {process.is_checkpoint && <span className="sp-chip">Checkpoint</span>}
        <span>{stageLine(process.stage_id, stages)}</span>
      </p>
      <CountChips counts={process.counts} retries={process.retries} label={`${w.Units} of ${name} by state`} />
      {efficiency.length > 0 && (
        <section aria-label="Efficiency">
          <h3 className="sp-sheet-h">Efficiency</h3>
          <Facts facts={efficiency} />
        </section>
      )}
      <div>
        <Button variant="default" aria-label={`Open ${name} in ${w.Units}`} onClick={() => onTasks(process.process)}>
          Open in {w.Units}
        </Button>
      </div>
      <h3 className="sp-sheet-h">{w.Units}</h3>
      <ProcessTasks run={run} process={process.process} name={name} onOpen={(task) => onOpen({ kind: "task", task })} />
    </>
  );
}

function StageView({ run, stage, processes, onOpen }: { run: RunDetail; stage: Stage; processes: Process[]; onOpen: Props["onOpen"] }) {
  const w = words(run.workflow.engine);
  const ended = isTerminal(run.state);
  const mine = processes.filter((p) => p.stage_id === stage.id);
  const word = stageWord(stage, ended);
  const name = stage.name ?? stage.id;
  return (
    <>
      <p className="sp-sub">
        <span>Stage {stage.position}</span>
        <span className="sp-chip">{stage.source === "declared" ? "Declared" : "Detected"}</span>
        <Word state={word} word={word} />
      </p>
      <CountChips counts={stage.task_counts} retries={mine.reduce((n, p) => n + p.retries, 0)} label={`${w.Units} of ${name} by state`} />
      <h3 className="sp-sheet-h">{w.Groups}</h3>
      {mine.length === 0 ? (
        <p className="sp-muted">No {w.group} reported in this stage yet.</p>
      ) : (
        <ul className="sp-sheet-list" aria-label={`${w.Groups} of ${name}`}>
          {neededFirst(mine).map((p) => {
            const { state, word: pw } = processState(p, ended, run.summary.open_checkpoints);
            return (
              <li key={p.process}>
                <button type="button" className="sp-sheet-row" aria-label={`Open ${w.group} ${p.process}`} onClick={() => onOpen({ kind: "process", name: p.process })}>
                  <span className="sp-mono sp-grow">{lastSegment(p.process)}</span>
                  <span className="sp-muted">
                    {sum(p.counts, "succeeded", "cached", "stored")} / {total(p.counts)}
                  </span>
                  <Word state={state} word={pw} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

/** "8 GB · 8 GB near limit": asked, then measured, the badge in words when near the limit. */
function Pair({ asked, used, near }: { asked: string; used: string; near?: boolean }) {
  return (
    <>
      {asked} · {used}
      <NearLimit on={!!near} />
    </>
  );
}

function TaskView({ run, stages, processes, task, attempt, onOpen }: { run: RunDetail; stages: Stage[]; processes: Process[]; task: Task; attempt?: number; onOpen: Props["onOpen"] }) {
  const w = words(run.workflow.engine);
  const known = processes.some((p) => p.process === task.process);
  const r = task.resources;
  const near = nearLimit(r);
  const facts: [string, ReactNode][] = [
    ["ID", <span className="sp-mono">{task.id}</span>],
    ["Tag", task.tag ?? "—"],
    ["State", <Word state={task.state} word={taskWord(task.state)} />],
    ["Last attempt", task.attempt_n ?? "—"],
    [
      w.Group,
      known ? (
        <button type="button" className="sp-link-button" aria-label={`Open ${w.group} ${task.process}`} onClick={() => onOpen({ kind: "process", name: task.process })}>
          <span className="sp-mono">{lastSegment(task.process)}</span> <Icon path={ICONS.arrowRight} size={13} />
        </button>
      ) : (
        <span className="sp-mono">{task.process}</span>
      ),
    ],
    ["Stage", stageLine(task.stage_id, stages)],
    ["CPUs · CPU %", <Pair asked={r.cpus === null ? "—" : String(r.cpus)} used={r.cpu_percent === null ? "—" : `${Math.round(r.cpu_percent)} %`} />],
    ["Memory, asked · peak", <Pair asked={bytes(r.memory_bytes)} used={bytes(r.peak_rss_bytes)} near={near.memory} />],
    ["Time limit · duration", <Pair asked={seconds(r.time_s)} used={seconds(r.realtime_s)} near={near.time} />],
  ];
  return (
    <>
      <Facts facts={facts} />
      <SlurmFacts task={task} />
      <h3 className="sp-sheet-h">Files</h3>
      <TaskFiles run={run} task={task} attempt={attempt} />
    </>
  );
}

export function DetailSheet({ run, stages, processes, views, onOpen, onBack, onClose, onTasks }: Props) {
  const phone = usePhone();
  const view = views[views.length - 1] ?? null;
  const shown = useRef<HTMLElement>(null);
  const last = useRef<Detail | null>(null);
  // a new view in an open sheet takes the focus; the first one leaves it to the Drawer
  useEffect(() => {
    if (view && last.current && last.current !== view) shown.current?.focus();
    last.current = view;
  }, [view]);
  const name = view ? title(view, stages) : "";
  const previous = views.length > 1 ? title(views[views.length - 2], stages) : null;
  let body = null;
  if (view?.kind === "process") {
    const process = processes.find((p) => p.process === view.name);
    body = process ? <ProcessView run={run} stages={stages} process={process} onOpen={onOpen} onTasks={onTasks} /> : null;
  } else if (view?.kind === "stage") {
    const stage = stages.find((s) => s.id === view.id);
    body = stage ? <StageView run={run} stage={stage} processes={processes} onOpen={onOpen} /> : null;
  } else if (view?.kind === "task") {
    body = <TaskView run={run} stages={stages} processes={processes} task={view.task} attempt={view.attempt} onOpen={onOpen} />;
  }
  return (
    <Drawer
      opened={view !== null}
      onClose={onClose}
      position="right"
      size={phone ? "100%" : 560}
      // reopened from the URL, the focus trap starts on the title (data-autofocus), not on Close
      title={view?.kind === "task" && view.attempt ? <span data-autofocus tabIndex={-1}>{name}</span> : name}
      returnFocus
      closeButtonProps={{ "aria-label": "Close" }}
      classNames={{ title: "sp-sheet-title" }}
    >
      {view && (
        <section key={views.length} ref={shown} className="sp-sheet" aria-label={name} tabIndex={-1}>
          {previous && (
            <button type="button" className="sp-link-button" onClick={onBack}>
              <Icon path={ICONS.chevronLeft} size={13} /> Back to {previous}
            </button>
          )}
          {body ?? <p className="sp-muted">The server no longer reports it for this run.</p>}
        </section>
      )}
    </Drawer>
  );
}
