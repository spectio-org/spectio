// The run's Graph tab (issue #160; ui-spec §4.14): the graph of GET /runs/{id}/graph, refetched
// live, with the Jobs level, Compare with another run, Replay, lineage and the node sheet
// (status, parameters with this run's values, outputs read live, jobs).
import { NativeSelect } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type Json, type Run, type RunDetail, type Task, listRuns, listTasks } from "../../api";
import { useFrames } from "../../live";
import { usePhone } from "../../shell/layout";
import type { Detail } from "../DetailSheet";
import { isTerminal, runWord } from "../stateWord";
import { Icon } from "../../icons";
import { Code } from "./Code";
import { FlagChip, GICONS, GraphView, Panel, formatSeconds, kindIcon, kindWord, progress, statusTone, statusWord } from "./GraphView";
import { type NodeDiff, type View, type ViewEdge, type ViewNode, collapse, diffGraphs, durationOf, lineage, timeSpan, toggled } from "./model";
import { type GraphSearch, type GraphSettings, searchOf, settingsOf } from "./settings";
import { type GraphDocument, type GraphNode, type NodeOutput, getNodeOutputs, getRunGraph } from "./types";

/** The Jobs level draws one node per job: every step's jobs, in pipeline order, until this many. */
export const MAX_JOBS = 2000;
/** The tasks route's page size, the most jobs drawn for one step. */
const JOBS_PER_STEP = 200;
/** How many steps' jobs load at once. */
const JOBS_FETCHES = 4;

/** Runs `fn` on every item, at most `size` at a time. */
async function inPool<T>(items: T[], size: number, fn: (item: T) => Promise<void>): Promise<void> {
  const queue = [...items];
  await Promise.all(Array.from({ length: Math.min(size, queue.length) }, async () => {
    while (queue.length) await fn(queue.shift() as T);
  }));
}

/** The steps the Jobs level loads the jobs of: all those with jobs, in pipeline order, while the
 * total stays under MAX_JOBS. A step with more than JOBS_PER_STEP jobs, or past the total, stays
 * one node, so no step is drawn with part of its jobs. */
export function expandedSteps(doc: GraphDocument): GraphNode[] {
  const total = (n: GraphNode) => Object.values(n.counts ?? {}).reduce((a, b) => a + b, 0);
  const steps = doc.nodes.filter((n) => n.kind !== "gate" && total(n) > 0).sort((a, b) => (a.pipeline_order ?? 0) - (b.pipeline_order ?? 0));
  const out: GraphNode[] = [];
  let sum = 0;
  for (const n of steps) {
    const t = total(n);
    if (t > JOBS_PER_STEP || sum + t > MAX_JOBS) continue;
    sum += t;
    out.push(n);
  }
  return out;
}

const PRODUCER_NOTES: Record<GraphDocument["producer"], string | null> = {
  "smk-rulegraph": null,
  "nf-dag": null,
  "bioflow-insight": "Links read from the pipeline's code by BioFlow-Insight; the run may take fewer paths.",
  "stages-only": "The links between steps are not known for this run: steps are grouped by stage, without arrows.",
};

interface Props {
  run: RunDetail;
  search: GraphSearch;
  onSearch: (search: GraphSearch) => void;
  /** Opens the run's own detail sheet (a process's jobs, a job). */
  onOpen: (detail: Detail) => void;
  /** Opens the Tasks tab on a process. */
  onTasks: (process: string) => void;
}

function value(params: Record<string, Json>, key: string): string {
  let at: Json | undefined = params[key];
  if (at === undefined && key.includes(".")) {
    at = params;
    for (const part of key.split(".")) at = at && typeof at === "object" && !Array.isArray(at) ? (at as Record<string, Json>)[part] : undefined;
  }
  if (at === undefined) return "(not set: the pipeline's default)";
  return typeof at === "string" ? at : JSON.stringify(at);
}

function Outputs({ run, process, task }: { run: RunDetail; process: string; task?: string }) {
  const [items, setItems] = useState<NodeOutput[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    getNodeOutputs(run.id, process)
      .then((r) => (setItems(r.items ?? []), setError(null)))
      .catch((e: Error) => setError(e.message));
  }, [run.id, process]);
  useEffect(load, [load]);
  useFrames(load, run.id, !isTerminal(run.state));
  if (error) return <p role="alert">The outputs could not be read: {error}</p>;
  if (!items) return <p className="sp-muted">Reading the outputs…</p>;
  const mine = task ? items.filter((o) => o.task_id === task) : items;
  if (mine.length === 0) return <p className="sp-muted">No output recorded yet.</p>;
  return (
    <ul className="sp-gsheet-list" aria-label={`Outputs of ${process}`}>
      {mine.map((o) => (
        <li key={`${o.task_id}:${o.path}`}>
          <span className="sp-mono">{o.path}</span>
          <span className="sp-state" data-tone={o.state === "present" ? "succeeded" : o.state === "removed" ? "cached" : "queued"}>
            {o.state === "present" ? "Present" : o.state === "removed" ? "Removed (temporary)" : o.state === "missing" ? "Missing" : "Not checked"}
          </span>
          {o.temp && o.state !== "removed" && <span className="sp-gtag">temporary</span>}
          {o.state === "present" && o.root === "results" && (
            <Link className="sp-text-link" to="/runs/$id/results/file" params={{ id: run.id }} search={{ path: o.path }} aria-label={`Preview ${o.path}`}>
              Preview
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}

/** A node's links one way, each a button that opens what flows along it: files for Snakemake,
 * a channel for Nextflow. */
function Flows({ view, node, engine, way, onEdge }: { view: View; node: ViewNode; engine: string; way: "in" | "out"; onEdge: (e: ViewEdge) => void }) {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const edges = view.edges.filter((e) => (way === "in" ? e.target : e.source) === node.id);
  const smk = engine === "snakemake";
  if (edges.length === 0) return <p className="sp-muted">{way === "in" ? "Nothing known: it starts from the pipeline's inputs." : "Nothing known downstream."}</p>;
  return (
    <ul className="sp-gflows" aria-label={way === "in" ? `What ${node.label} receives` : `What ${node.label} sends`}>
      {edges.map((e) => {
        const other = byId.get(way === "in" ? e.source : e.target);
        const name = other?.label ?? (way === "in" ? e.source : e.target);
        return (
          <li key={e.id}>
            <button type="button" className="sp-gflow" onClick={() => onEdge(e)} aria-label={`${smk ? "Files" : "Channel"} ${way === "in" ? "from" : "to"} ${name}${e.conditions.length ? `, if ${e.conditions.join(" or ")}` : ""}: what flows`}>
              <Icon path={smk ? GICONS.file : GICONS.channel} size={14} stroke={1.8} />
              <span className="sp-gflow-what">{smk ? "files" : "channel"}</span>
              <span>{way === "in" ? "from" : "to"}</span>
              <Icon path={kindIcon(other?.kind ?? "process")} size={13} stroke={1.8} />
              <strong>{name}</strong>
              {e.conditions.length > 0 && <span className="sp-gtag">if {e.conditions.join(" or ")}</span>}
              <Icon path={GICONS.link} size={13} stroke={1.8} />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

interface SheetProps {
  run: RunDetail;
  doc: GraphDocument;
  view: View;
  node: ViewNode | null;
  task: Task | null;
  diff: NodeDiff | null;
  onClose: () => void;
  onMember: (id: string) => void;
  onTrace: (direction: "up" | "down" | null) => void;
  onOpen: (detail: Detail) => void;
  onTasks: (process: string) => void;
  onToggle: (group: string) => void;
  onEdge: (edge: ViewEdge) => void;
  trace: "up" | "down" | null;
}

/** A job's key as name and value pairs: Snakemake's `k=v` wildcards, or Nextflow's tag. */
export function keyPairs(key: string | null): [string, string][] {
  if (!key) return [];
  const parts = key.split(/,\s*/);
  return parts.every((p) => p.includes("=")) ? parts.map((p) => [p.slice(0, p.indexOf("=")), p.slice(p.indexOf("=") + 1)]) : [["tag", key]];
}

const bytes = (b: number | null) => (b === null ? "—" : b >= 1 << 30 ? `${(b / (1 << 30)).toFixed(1)} GiB` : `${Math.round(b / (1 << 20))} MiB`);

function JobFacts({ task }: { task: Task }) {
  const r = task.resources;
  return (
    <>
      <h3 className="sp-sheet-h">Key</h3>
      <dl className="facts" aria-label="Key of this job">
        {keyPairs(task.tag).map(([k, v]) => (
          <div key={k} style={{ display: "contents" }}>
            <dt className="sp-mono">{k}</dt>
            <dd className="sp-mono">{v}</dd>
          </div>
        ))}
        {!task.tag && (
          <>
            <dt>name</dt>
            <dd className="sp-mono">{task.name ?? task.id}</dd>
          </>
        )}
      </dl>
      <h3 className="sp-sheet-h">Resources</h3>
      <dl className="facts" aria-label="Resources of this job">
        <dt>Attempt</dt>
        <dd>{task.attempt_n ?? "—"}</dd>
        <dt>CPUs</dt>
        <dd>{r.cpus ?? "—"}</dd>
        <dt>Memory asked</dt>
        <dd>{bytes(r.memory_bytes)}</dd>
        <dt>Peak memory</dt>
        <dd>{bytes(r.peak_rss_bytes)}</dd>
        <dt>Wall time</dt>
        <dd>{r.realtime_s !== null ? formatSeconds(r.realtime_s) : "—"}</dd>
      </dl>
    </>
  );
}

function NodeSheet({ run, doc, view, node, task, diff, onClose, onMember, onTrace, onOpen, onTasks, onToggle, onEdge, trace }: SheetProps) {
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const members = node ? node.members.map((m) => byId.get(m)).filter((m) => !!m) : [];
  const single = node && members.length === 1 && node.id === members[0].id ? members[0] : null;
  const params = [...new Set(members.flatMap((m) => m.params))].sort();
  const { done, total } = node ? progress(node.counts) : { done: 0, total: 0 };
  const folded = node?.kind === "stage" || node?.kind === "subworkflow";
  return (
    <Panel id={node?.id ?? null} opened={node !== null} onClose={onClose} title={node ? `${node.label} (${kindWord(node.kind)})` : ""} icon={kindIcon(node?.kind ?? "process")}>
      {node && (
        <section className="sp-sheet" aria-label={node.label}>
          <p>
            <span className="sp-state" data-tone={statusTone(node.status)}>
              {statusWord(node.status)}
            </span>
            {total > 0 && ` ${done} of ${total} jobs done`}
            {durationOf(node) > 0 && ` · ${formatSeconds(durationOf(node))}`}
          </p>
          {diff && diff.change === "added" && <p className="sp-gnote">New in this run: the compared run did not have it.</p>}
          {single?.id && <p className="sp-mono sp-sheet-name">{single.id}</p>}
          {node.flags && node.flags.length > 0 && (
            <p className="sp-gflags">
              {node.flags.map((f) => (
                <FlagChip key={f} flag={f} />
              ))}
            </p>
          )}
          <div className="sp-gactions" role="group" aria-label={`Actions on ${node.label}`}>
            {node.group && (
              <button type="button" className="sp-gaction" onClick={() => onToggle(node.group!)}>
                <Icon path={folded ? GICONS.unfold : GICONS.fold} size={14} stroke={2} />
                {folded ? `Unfold ${node.label}` : `Fold ${groupLabel(doc, node.group)}`}
              </button>
            )}
            <button type="button" className="sp-gaction" aria-pressed={trace === "up"} onClick={() => onTrace(trace === "up" ? null : "up")}>
              <Icon path={GICONS.up} size={14} stroke={2} />
              What leads here
            </button>
            <button type="button" className="sp-gaction" aria-pressed={trace === "down"} onClick={() => onTrace(trace === "down" ? null : "down")}>
              <Icon path={GICONS.down} size={14} stroke={2} />
              What follows
            </button>
          </div>
          <dl className="sp-gfacts">
            {node.kind === "job" && (
              <>
                <dt>Step</dt>
                <dd>{node.step}</dd>
              </>
            )}
            {single?.source && (
              <>
                <dt>
                  <Icon path={GICONS.file} size={13} stroke={1.8} /> Defined in
                </dt>
                <dd className="sp-mono">
                  {single.source.file}
                  {single.source.line ? `:${single.source.line}` : ""}
                </dd>
              </>
            )}
            {single?.condition && (
              <>
                <dt>
                  <Icon path={GICONS.conditional} size={13} stroke={1.8} /> Runs when
                </dt>
                <dd>
                  <code>{single.condition}</code>
                </dd>
              </>
            )}
          </dl>
          <h3 className="sp-sheet-h">Receives</h3>
          <p className="sp-muted sp-ghelp">{doc.engine === "snakemake" ? "Files its input names, written by these rules." : "Items (files, often with a sample id) these processes emit into its input channels."}</p>
          <Flows view={view} node={node} engine={doc.engine} way="in" onEdge={onEdge} />
          <h3 className="sp-sheet-h">Sends</h3>
          <Flows view={view} node={node} engine={doc.engine} way="out" onEdge={onEdge} />
          {task && (
            <>
              <JobFacts task={task} />
              <p>
                <button type="button" className="sp-link-button" onClick={() => onOpen({ kind: "task", task })}>
                  Open this job: script, logs, files
                </button>
              </p>
              <h3 className="sp-sheet-h">Outputs</h3>
              <Outputs run={run} process={node.members[0]} task={task.id} />
            </>
          )}
          {members.length > 1 && (
            <>
              <h3 className="sp-sheet-h">Steps ({members.length})</h3>
              <ul className="sp-gsheet-list" aria-label={`Steps of ${node.label}`}>
                {members.map((m) => (
                  <li key={m.id}>
                    <button type="button" className="sp-link-button" aria-label={`Show ${m.name} on the graph`} onClick={() => onMember(m.id)}>
                      {m.name}
                    </button>
                    <span className="sp-state" data-tone={statusTone(m.status ?? null)}>
                      {statusWord(m.status ?? null)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {(single || node.kind === "job") && (
            <details className="sp-gdetails">
              <summary>Code</summary>
              <Code name={node.members[0]} code={byId.get(node.members[0])?.code} where={{ location: run.workflow.location, revision: null, fromRun: true }} />
            </details>
          )}
          <h3 className="sp-sheet-h">Parameters</h3>
          {params.length === 0 ? (
            <p className="sp-muted">No parameter is known to be read by {members.length > 1 ? "these steps" : "this step"}.</p>
          ) : (
            <dl className="facts" aria-label={`Parameters of ${node.label}`}>
              {params.map((p) => (
                <div key={p} style={{ display: "contents" }}>
                  <dt className="sp-mono">{p}</dt>
                  <dd>{value(run.params, p)}</dd>
                </div>
              ))}
            </dl>
          )}
          {single && single.kind !== "gate" && (
            <>
              <h3 className="sp-sheet-h">Outputs</h3>
              <Outputs run={run} process={single.id} />
              <h3 className="sp-sheet-h">Jobs</h3>
              <p>
                <button type="button" className="sp-link-button" onClick={() => onOpen({ kind: "process", name: single.id })}>
                  Open its jobs
                </button>
                {" · "}
                <button type="button" className="sp-link-button" onClick={() => onTasks(single.id)}>
                  Open in Tasks
                </button>
              </p>
            </>
          )}
        </section>
      )}
    </Panel>
  );
}

/** What flows along a link: Snakemake links steps through files, Nextflow through channels whose
 * items are the files the upstream step emitted. Shown: the upstream side's recorded outputs. */
function EdgeSheet({ run, doc, view, edge, onClose }: { run: RunDetail; doc: GraphDocument; view: View; edge: ViewEdge | null; onClose: () => void }) {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const names = new Map(doc.nodes.map((n) => [n.id, n.name]));
  const from = edge ? byId.get(edge.source) : undefined;
  const to = edge ? byId.get(edge.target) : undefined;
  const sources = edge ? [...new Set(edge.pairs.map(([a]) => a))] : [];
  const job = from?.kind === "job" ? from.id.slice("job:".length) : undefined;
  const smk = doc.engine === "snakemake";
  return (
    <Panel id={edge?.id ?? null} opened={edge !== null} onClose={onClose} title={edge ? `${from?.label ?? edge.source} → ${to?.label ?? edge.target}` : ""} icon={smk ? GICONS.file : GICONS.channel}>
      {edge && (
        <section className="sp-sheet" aria-label="Link">
          <div className="sp-gpipe" aria-hidden="true">
            <span className="sp-gpipe-end">
              <Icon path={kindIcon(from?.kind ?? "process")} size={14} stroke={1.8} />
              {from?.label ?? edge.source}
            </span>
            <span className="sp-gpipe-mid">
              <Icon path={smk ? GICONS.file : GICONS.channel} size={14} stroke={1.8} />
              {smk ? "files" : "channel"}
              <Icon path={GICONS.link} size={14} stroke={1.8} />
            </span>
            <span className="sp-gpipe-end">
              <Icon path={kindIcon(to?.kind ?? "process")} size={14} stroke={1.8} />
              {to?.label ?? edge.target}
            </span>
          </div>
          <p>
            {smk
              ? "Snakemake links two rules through files: the downstream rule's input is a file the upstream rule writes."
              : "Nextflow links two processes through a channel: each item the upstream process emits (usually files, with values such as a sample id) is read by the downstream one."}
          </p>
          {edge.conditions.length > 0 && (
            <p>
              Only when <code>{edge.conditions.join(" or ")}</code>
            </p>
          )}
          {edge.pairs.length > 1 && (
            <>
              <h3 className="sp-sheet-h">Links it stands for</h3>
              <ul className="sp-gsheet-list">
                {edge.pairs.map(([a, b]) => (
                  <li key={`${a}->${b}`} className="sp-mono">
                    {names.get(a) ?? a} → {names.get(b) ?? b}
                  </li>
                ))}
              </ul>
            </>
          )}
          <h3 className="sp-sheet-h">{smk ? "Files written upstream" : "Files emitted upstream"}</h3>
          <p className="sp-muted">
            {smk ? "The downstream rule reads those its input names." : "The channel carries them, alone or with values, to the downstream process."}
          </p>
          {sources.map((p) => (
            <div key={p}>
              {sources.length > 1 && <p className="sp-mono">{names.get(p) ?? p}</p>}
              <Outputs run={run} process={p} task={job} />
            </div>
          ))}
        </section>
      )}
    </Panel>
  );
}

const groupLabel = (doc: GraphDocument, id: string): string => doc.groups.find((g) => g.id === id)?.name ?? id.replace(/^(stage|sub):/, "");

function Compare({ run, value, onChange }: { run: Run; value: string; onChange: (id: string) => void }) {
  const [others, setOthers] = useState<Run[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    listRuns({ q: run.workflow.name ?? undefined, limit: 50 }, controller.signal)
      .then((page) => setOthers((page.items ?? []).filter((r) => r.id !== run.id && r.workflow.location === run.workflow.location)))
      .catch(() => setOthers([]));
    return () => controller.abort();
  }, [run.id, run.workflow.name, run.workflow.location]);
  return (
    <NativeSelect
      size="xs"
      label="Compare with"
      value={value}
      onChange={(e) => onChange(e.currentTarget.value)}
      data={[{ value: "", label: others.length ? "(no other run)" : "(no other run of this pipeline)" }, ...others.map((r) => ({ value: r.id, label: `${r.name ?? r.id} · ${runWord(r.state)}` }))]}
    />
  );
}

function Replay({ span, at, onAt }: { span: { from: number; to: number }; at: number | null; onAt: (t: number | null) => void }) {
  const [playing, setPlaying] = useState(false);
  const atRef = useRef(at);
  atRef.current = at;
  useEffect(() => {
    if (!playing) return;
    const step = Math.max(1000, (span.to - span.from) / 100);
    const timer = setInterval(() => {
      const next = (atRef.current ?? span.from) + step;
      if (next >= span.to) setPlaying(false);
      onAt(Math.min(next, span.to));
    }, 150);
    return () => clearInterval(timer);
  }, [playing, span, onAt]);
  const on = at !== null;
  return (
    <div className="sp-greplay">
      <button type="button" role="switch" aria-checked={on} className="sp-gbtn" onClick={() => (setPlaying(false), onAt(on ? null : span.from))}>
        Replay
      </button>
      {on && (
        <>
          <button type="button" className="sp-gbtn" onClick={() => setPlaying(!playing)} aria-label={playing ? "Pause the replay" : "Play the replay"}>
            {playing ? "Pause" : "Play"}
          </button>
          <input
            type="range"
            min={span.from}
            max={span.to}
            step={Math.max(1, Math.round((span.to - span.from) / 200))}
            value={at}
            onChange={(e) => onAt(Number(e.currentTarget.value))}
            aria-label="Replay time"
            aria-valuetext={`${formatSeconds((at - span.from) / 1000)} after the start`}
          />
          <span className="sp-muted">+{formatSeconds((at - span.from) / 1000)}</span>
        </>
      )}
    </div>
  );
}

export function GraphPanel({ run, search, onSearch, onOpen, onTasks }: Props) {
  const phone = usePhone();
  const settings = settingsOf(search, phone);
  const [doc, setDoc] = useState<GraphDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Record<string, Task[]>>({});
  const [compareId, setCompareId] = useState("");
  const [other, setOther] = useState<GraphDocument | null>(null);
  const [replayAt, setReplayAt] = useState<number | null>(null);
  const [edge, setEdge] = useState<ViewEdge | null>(null);
  const [trace, setTrace] = useState<{ id: string; direction: "up" | "down" } | null>(null);
  const live = !isTerminal(run.state);
  const source = useMemo(() => ({ location: run.workflow.location, revision: null, fromRun: true }), [run.workflow.location]);

  const load = useCallback(() => {
    getRunGraph(run.id)
      .then((d) => (setDoc(d), setError(null)))
      .catch((e: ApiError) => setError(e.slug === "feature-disabled" ? "The graph is turned off on this server." : e.message));
  }, [run.id]);
  useEffect(load, [load]);
  useFrames(load, run.id, live);

  // the Jobs level: every step's jobs (expandedSteps), refetched only when their counts change
  const wantJobs = settings.level === "jobs" && doc !== null;
  const expanded = wantJobs ? expandedSteps(doc) : [];
  const jobsKey = expanded.map((n) => `${n.id}=${JSON.stringify(n.counts ?? {})}`).join("\n");
  const fetched = useRef(new Map<string, string>()); // `${run}/${step}` → the counts its jobs were loaded at
  useEffect(() => {
    if (!jobsKey) {
      fetched.current.clear();
      return setJobs({});
    }
    const want = new Map(jobsKey.split("\n").map((line) => [line.slice(0, line.lastIndexOf("=")), line.slice(line.lastIndexOf("=") + 1)] as const));
    setJobs((prev) => Object.fromEntries(Object.entries(prev).filter(([p]) => want.has(p))));
    const stale = [...want].filter(([p, counts]) => fetched.current.get(`${run.id}/${p}`) !== counts).map(([p]) => p);
    const controller = new AbortController();
    void inPool(stale, JOBS_FETCHES, (p) =>
      listTasks(run.id, { process: p, limit: JOBS_PER_STEP }, controller.signal)
        .then((page) => {
          if (controller.signal.aborted) return;
          fetched.current.set(`${run.id}/${p}`, want.get(p) ?? "");
          setJobs((prev) => ({ ...prev, [p]: page.items ?? [] }));
        })
        .catch(() => undefined),
    );
    return () => controller.abort();
  }, [jobsKey, run.id]);

  useEffect(() => {
    if (!compareId) return setOther(null);
    const controller = new AbortController();
    getRunGraph(compareId, controller.signal).then(setOther, () => controller.signal.aborted || setOther(null));
    return () => controller.abort();
  }, [compareId]);

  const set = (patch: Partial<GraphSettings>) => onSearch(searchOf({ ...settings, ...patch }, phone));
  const view = useMemo(() => (doc ? collapse(doc, settings.level, settings.level === "jobs" ? jobs : undefined, settings.fold) : null), [doc, settings.level, jobs, settings.fold]);
  const diff = useMemo(() => (doc && other ? diffGraphs(doc, other) : null), [doc, other]);
  const traced = useMemo(() => (view && trace && view.nodes.some((n) => n.id === trace.id) ? lineage(view, trace.id, trace.direction) : null), [view, trace]);
  const span = doc ? timeSpan(doc) : null;

  if (error) return <p role="alert">The graph could not be read: {error}</p>;
  if (!doc || !view) return <p className="sp-muted">Drawing the graph…</p>;
  if (doc.nodes.length === 0) return <p className="sp-empty">No step is known for this run yet.</p>;

  const selected = settings.node ? view.nodes.find((n) => n.id === settings.node) ?? null : null;
  const task = selected?.kind === "job" ? Object.values(jobs).flat().find((t) => `job:${t.id}` === selected.id) ?? null : null;
  const removed = diff ? [...diff].filter(([, d]) => d.change === "removed").map(([id]) => other?.nodes.find((n) => n.id === id)?.name ?? id) : [];
  const note = PRODUCER_NOTES[doc.producer];
  const shownJobs = expanded.reduce((n, s) => n + (jobs[s.id]?.length ?? 0), 0);
  const left = doc.nodes.filter((n) => Object.values(n.counts ?? {}).some((c) => c > 0) && !jobs[n.id]?.length).length;

  return (
    <>
      <GraphView
        doc={doc}
        title={run.name ?? run.id}
        settings={settings}
        onSettings={set}
        runtime
        jobs={settings.level === "jobs" ? jobs : undefined}
        decor={{ selected: settings.node, edge: edge?.id ?? null, lineage: traced, diff, replayAt }}
        onOpen={(n) => (setEdge(null), set({ node: n.id }))}
        onEdge={setEdge}
        source={source}
        side={
          <>
            <EdgeSheet run={run} doc={doc} view={view} edge={edge} onClose={() => setEdge(null)} />
            <NodeSheet
              run={run}
              doc={doc}
              view={view}
              node={selected}
              task={task}
              diff={selected ? diff?.get(selected.id) ?? null : null}
              onClose={() => set({ node: null })}
              onMember={(id) => set({ level: "process", node: id })}
              onTrace={(direction) => {
                setTrace(direction && selected ? { id: selected.id, direction } : null);
              }}
              trace={trace && selected && trace.id === selected.id ? trace.direction : null}
              onOpen={(d) => (set({ node: null }), onOpen(d))}
              onTasks={onTasks}
              onToggle={(g) => set({ fold: toggled(settings.fold, g), node: null })}
              onEdge={(e) => (set({ node: null }), setEdge(e))}
            />
          </>
        }
        extra={
          <>
            <Compare run={run} value={compareId} onChange={setCompareId} />
            {span && span.to > span.from && <Replay span={span} at={replayAt} onAt={setReplayAt} />}
          </>
        }
        notes={
          <>
            {note && <p className="sp-gnote">{note}</p>}
            {!doc.complete && doc.producer !== "stages-only" && <p className="sp-gnote">The graph can still grow: steps after an open checkpoint join it once the checkpoint ends.</p>}
            {settings.level === "jobs" && (
              <p className="sp-gnote">
                {`One box per job (${shownJobs}), named by its key: Nextflow's tag, or Snakemake's wildcards. Jobs of linked steps are linked when their keys match, or when one step has a single job.`}
                {left > 0 && ` ${left} ${left === 1 ? "step is" : "steps are"} still one box (not started yet, more than ${JOBS_PER_STEP} jobs, or past ${MAX_JOBS} in all); the Tasks tab lists every job.`}
              </p>
            )}
            {removed.length > 0 && <p className="sp-gnote">Only in the compared run: {removed.join(", ")}.</p>}
            {traced && trace && (
              <p className="sp-gnote">
                {`Showing what ${trace.direction === "up" ? "leads to" : "follows from"} ${view.nodes.find((n) => n.id === trace.id)?.label ?? trace.id}. `}
                <button type="button" className="sp-link-button" onClick={() => setTrace(null)}>
                  Clear trace
                </button>
              </p>
            )}
          </>
        }
      />
    </>
  );
}
