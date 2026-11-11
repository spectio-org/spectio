// The run's Graph tab (issue #160; ui-spec §4.14): the graph of GET /runs/{id}/graph, refetched
// live, with the Jobs level, Compare with another run, Replay, lineage and the node sheet
// (status, parameters with this run's values, outputs read live, jobs).
import { NativeSelect } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type Json, type Run, type RunDetail, type Task, listRuns, listTasks, resultUrl } from "../../api";
import { useFrames } from "../../live";
import { usePhone } from "../../shell/layout";
import type { Detail } from "../DetailSheet";
import { isTerminal, runWord, taskWord } from "../stateWord";
import { Icon } from "../../icons";
import { Code, type CodeSource, useCode } from "./Code";
import { isResultPath } from "../ReportViewer";
import { fileKind, size as sizeText } from "../preview";
import { BAND_WORDS, FlagChip, GICONS, GraphView, Panel, formatSeconds, kindIcon, kindWord, progress, statusTone, statusWord, viewOf } from "./GraphView";
import { type Declared, declarations, jobStatus, type NodeDiff, type View, type ViewEdge, type ViewNode, bandOf, diffGraphs, durationOf, lineage, timeSpan, toggled } from "./model";
import { type GraphSearch, type GraphSettings, searchOf, settingsOf } from "./settings";
import { type GraphDocument, type GraphNode, type NodeOutput, getNodeOutputs, getOutputHead, getRunGraph } from "./types";

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

/** A parameter's value in this run, its kind and its text: `undefined` when the run did not set
 * it (the pipeline's default applies). */
export function paramOf(params: Record<string, Json>, key: string): { kind: string; text: string; set: boolean } {
  let at: Json | undefined = params[key];
  if (at === undefined && key.includes(".")) {
    at = params;
    for (const part of key.split(".")) at = at && typeof at === "object" && !Array.isArray(at) ? (at as Record<string, Json>)[part] : undefined;
  }
  if (at === undefined) return { kind: "default", text: "not set: the pipeline's default", set: false };
  if (at === null) return { kind: "null", text: "null", set: true };
  if (typeof at === "boolean") return { kind: "yes/no", text: at ? "true" : "false", set: true };
  if (typeof at === "number") return { kind: "number", text: String(at), set: true };
  if (Array.isArray(at)) return { kind: `list of ${at.length}`, text: at.map((v) => (typeof v === "string" ? v : JSON.stringify(v))).join(", "), set: true };
  if (typeof at === "object") return { kind: "map", text: JSON.stringify(at), set: true };
  return { kind: /^(\/|\.{1,2}\/|~\/|[a-z][\w+.-]*:\/\/)|\.[a-z0-9]{1,6}$/i.test(at) && !/\s/.test(at) ? "path" : "text", text: at, set: true };
}

/** A file's look: the icon and word of its kind, and whether its first lines are worth showing
 * (text, and gzip of text: FASTQ, VCF, tables) or an image a thumbnail. */
const GZ_TEXT = /\.(fq|fastq|fa|fasta|fna|vcf|sam|bed|gtf|gff3?|txt|tsv|csv|tab|log|json)\.b?gz$/i;
export function fileLook(path: string): { icon: string; word: string; peek: boolean; image: boolean } {
  const name = path.split("/").pop() ?? path;
  if (/\.(fq|fastq)(\.b?gz)?$/i.test(name)) return { icon: GICONS.reads, word: "reads", peek: true, image: false };
  if (GZ_TEXT.test(name)) return { icon: GICONS.file, word: "gzip text", peek: true, image: false };
  if (/\.(bam|cram|bai|crai|csi|tbi|bcf)$/i.test(name)) return { icon: GICONS.binary, word: /\.(bam|cram)$/i.test(name) ? "alignments (binary)" : /\.bcf$/i.test(name) ? "variants (binary)" : "index (binary)", peek: false, image: false };
  const kind = fileKind(name);
  if (kind === "image") return { icon: GICONS.image, word: "image", peek: false, image: true };
  if (kind === "table") return { icon: GICONS.table, word: "table", peek: true, image: false };
  if (kind === "text" || kind === "json") return { icon: GICONS.file, word: kind === "json" ? "JSON" : "text", peek: true, image: false };
  if (kind === "html") return { icon: GICONS.code, word: "report", peek: false, image: false };
  return { icon: GICONS.binary, word: kind === "binary" ? "binary" : "file", peek: false, image: false };
}

const THUMB_MAX = 2 << 20;

/** One output as a card: kind, name, folder, size, state; its first lines on demand, a thumbnail
 * for a small image, and Open when the preview page can read it. */
function FileCard({ run, process, item }: { run: RunDetail; process: string; item: NodeOutput }) {
  const [head, setHead] = useState<{ text: string; more: boolean } | string | null>(null);
  const [open, setOpen] = useState(false);
  const look = fileLook(item.path);
  const name = item.path.split("/").pop() ?? item.path;
  const dir = item.path.slice(0, item.path.length - name.length).replace(/\/$/, "");
  // a path with an empty, `.` or `..` part, or a control or format character, is never asked for
  const present = item.state === "present" && isResultPath(item.path) && (!item.work_path || isResultPath(item.work_path));
  const work = item.work_path ? { task: item.task_id, attempt: item.attempt_n } : undefined;
  const page = present && item.root === "results" ? { to: "/runs/$id/results/file" as const, search: { path: item.path } } : present && work ? { to: "/runs/$id/workdir/file" as const, search: { path: item.work_path!, ...work } } : null;
  const thumb = look.image && present && (item.size ?? Infinity) <= THUMB_MAX && (item.root === "results" || work) ? resultUrl(run.id, work ? item.work_path! : item.path, { as: "image" }, work) : null;
  const toggle = () => {
    setOpen(!open);
    if (head || open) return;
    getOutputHead(run.id, process, item.path, item.task_id).then(
      (h) => setHead({ text: h.text, more: h.more }),
      (e: ApiError) => setHead(e.slug === "not-text" ? "A binary file: no lines to show." : `Could not read it: ${e.message}`),
    );
  };
  const stateWord = present ? "present" : item.state === "removed" ? "removed (temporary)" : item.state === "missing" ? "missing" : "not checked";
  return (
    <li className="sp-gfile" data-state={item.state}>
      <span className="sp-gfile-icon" aria-hidden="true">
        {thumb ? <img src={thumb} alt="" loading="lazy" /> : <Icon path={look.icon} size={16} stroke={1.7} />}
      </span>
      <span className="sp-gfile-text">
        <span className="sp-gfile-name sp-mono" title={item.path}>
          {name}
        </span>
        <span className="sp-gfile-sub">
          <span className="sp-gdot" data-state={item.state} aria-hidden="true" />
          <span className="sp-gsr">{stateWord}, </span>
          {item.state !== "present" && <span>{stateWord} · </span>}
          {look.word}
          {item.size != null && ` · ${sizeText(item.size)}`}
          {dir && <span className="sp-gfile-dir sp-mono"> · {dir}</span>}
        </span>
      </span>
      <span className="sp-gfile-acts">
        {look.peek && present && (
          <button type="button" className="sp-gicon" aria-expanded={open} aria-label={`First lines of ${item.path}`} onClick={toggle}>
            <Icon path={GICONS.peek} size={15} stroke={1.8} />
          </button>
        )}
        {page && (
          <Link className="sp-gicon" to={page.to} params={{ id: run.id }} search={page.search} aria-label={`Open ${item.path}`}>
            <Icon path={GICONS.open} size={15} stroke={1.8} />
          </Link>
        )}
      </span>
      {open && (
        <div className="sp-gfile-head">
          {head === null ? (
            <p className="sp-muted">Reading…</p>
          ) : typeof head === "string" ? (
            <p className="sp-muted">{head}</p>
          ) : (
            <>
              <pre className="sp-gcode" tabIndex={0} aria-label={`First lines of ${item.path}`}>
                {head.text}
              </pre>
              {head.more && <p className="sp-muted">First lines only.</p>}
            </>
          )}
        </div>
      )}
    </li>
  );
}

const FILES_SHOWN = 12;

/** The jobs of one step that ran more than once (Nextflow `errorStrategy 'retry'`, Snakemake
 * `--retries`): each opens the job's sheet, whose attempts tab shows every execution. */
function Retries({ run, process, onOpen }: { run: RunDetail; process: string; onOpen: (detail: Detail) => void }) {
  const [items, setItems] = useState<Task[] | null>(null);
  useEffect(() => {
    setItems(null);
    const controller = new AbortController();
    // optional: on an error the section is left out, the Tasks tab still lists every attempt
    listTasks(run.id, { process, limit: JOBS_PER_STEP }, controller.signal).then(
      (page) => setItems(page.items ?? []),
      () => controller.signal.aborted || setItems([]),
    );
    return () => controller.abort();
  }, [run.id, process]);
  const again = (items ?? []).filter((t) => (t.attempt_n ?? 1) > 1);
  if (again.length === 0) return null;
  return (
    <>
      <H icon={GICONS.job}>Executions</H>
      <p className="sp-ghelp">
        {again.length} {again.length === 1 ? "job was" : "jobs were"} run again after a failure; open one to see each attempt, its exit code and its logs.
      </p>
      <ul className="sp-gsteps" aria-label={`Jobs of ${process} run more than once`}>
        {again.map((t) => (
          <li key={t.id}>
            <button type="button" className="sp-gwire-chip" data-tone={statusTone(jobStatus[t.state] ?? null)} aria-label={`Open ${t.name ?? t.tag ?? t.id}: ${t.attempt_n} attempts, ${taskWord(t.state)}`} onClick={() => onOpen({ kind: "task", task: t })}>
              <span>{t.tag ?? t.name ?? t.id}</span>
              <span className="sp-muted">{t.attempt_n} attempts</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function Outputs({ run, process, task }: { run: RunDetail; process: string; task?: string }) {
  const [items, setItems] = useState<NodeOutput[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [all, setAll] = useState(false);
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
  const shown = all ? mine : mine.slice(0, FILES_SHOWN);
  return (
    <>
      <ul className="sp-gfiles" aria-label={`Outputs of ${process}`}>
        {shown.map((o) => (
          <FileCard key={`${o.task_id}:${o.work_path ?? o.path}`} run={run} process={process} item={o} />
        ))}
      </ul>
      {mine.length > shown.length && (
        <button type="button" className="sp-link-button" onClick={() => setAll(true)}>
          Show the {mine.length - shown.length} others
        </button>
      )}
    </>
  );
}

/** A node's links as a small diagram: what it reads from above, itself, what it feeds below.
 * Each other step is a button that opens the link (files for Snakemake, a channel for Nextflow). */
function Wiring({ view, node, engine, onEdge }: { view: View; node: ViewNode; engine: string; onEdge: (e: ViewEdge) => void }) {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const ins = view.edges.filter((e) => e.target === node.id);
  const outs = view.edges.filter((e) => e.source === node.id);
  const smk = engine === "snakemake";
  const what = smk ? "Files" : "Channel";
  const chips = (edges: ViewEdge[], way: "in" | "out") => (
    <ul className="sp-gwire-row" aria-label={way === "in" ? `What ${node.label} reads from` : `What ${node.label} feeds`}>
      {edges.map((e) => {
        const other = byId.get(way === "in" ? e.source : e.target);
        const name = other ? (other.kind === "job" && other.step ? `${other.step} ${other.label}` : other.label) : way === "in" ? e.source : e.target;
        return (
          <li key={e.id}>
            <button type="button" className="sp-gwire-chip" data-tone={statusTone(other?.status ?? null)} onClick={() => onEdge(e)} aria-label={`${what} ${way === "in" ? "from" : "to"} ${name}${e.conditions.length ? `, if ${e.conditions.join(" or ")}` : ""}: what flows`}>
              <Icon path={kindIcon(other?.kind ?? "process")} size={12} stroke={1.9} />
              <span>{name}</span>
              {e.conditions.length > 0 && <span className="sp-gwire-if">if</span>}
            </button>
          </li>
        );
      })}
    </ul>
  );
  return (
    <div className="sp-gwire">
      {ins.length ? chips(ins, "in") : <p className="sp-gwire-none">Pipeline inputs</p>}
      <div className="sp-gwire-link" aria-hidden="true">
        <Icon path={smk ? GICONS.file : GICONS.channel} size={12} stroke={1.9} /> {smk ? "files" : "channels"}
      </div>
      <div className="sp-gwire-me" data-tone={statusTone(node.status)}>
        <Icon path={kindIcon(node.kind)} size={13} stroke={1.9} />
        {node.label}
      </div>
      <div className="sp-gwire-link" aria-hidden="true">
        <Icon path={smk ? GICONS.file : GICONS.channel} size={12} stroke={1.9} /> {smk ? "files" : "channels"}
      </div>
      {outs.length ? chips(outs, "out") : <p className="sp-gwire-none">End of the pipeline</p>}
    </div>
  );
}

/** A ratio as a bar with its band (CPU, memory) or as a share (duration). */
function Gauge({ icon, label, ratio, text, band, hint }: { icon: string; label: string; ratio: number; text: string; band: string | null; hint: string }) {
  return (
    <div className="sp-ggauge" data-band={band ?? undefined}>
      <span className="sp-ggauge-label">
        <Icon path={icon} size={13} stroke={1.9} />
        {label}
      </span>
      <strong>{text}</strong>
      <span className="sp-ggauge-bar" role="img" aria-label={`${label}: ${text}, ${hint}`}>
        <span style={{ width: `${Math.round(Math.min(1, ratio) * 100)}%` }} />
        {band && <span className="sp-ggauge-tick" aria-hidden="true" />}
      </span>
      <span className="sp-ggauge-hint">{hint}</span>
    </div>
  );
}

function Efficiency({ cpu, mem, seconds, span, words }: { cpu: number | null | undefined; mem: number | null | undefined; seconds: number; span: number; words: { cpu: string; mem: string } }) {
  if (cpu == null && mem == null && !(seconds > 0 && span > 0)) return null;
  return (
    <>
      <h3 className="sp-sheet-h">
        <Icon path={GICONS.cpu} size={14} stroke={1.8} /> Efficiency
      </h3>
      <div className="sp-ggauges">
        {cpu != null && <Gauge icon={GICONS.cpu} label="CPU" ratio={cpu} text={`${Math.round(cpu * 100)} %`} band={bandOf(cpu)} hint={`${words.cpu}; ${BAND_WORDS[bandOf(cpu)]}`} />}
        {mem != null && <Gauge icon={GICONS.memory} label="Memory" ratio={mem} text={`${Math.round(mem * 100)} %`} band={bandOf(mem)} hint={`${words.mem}; ${BAND_WORDS[bandOf(mem)]}`} />}
        {seconds > 0 && span > 0 && <Gauge icon={GICONS.clock} label="Time" ratio={Math.min(1, seconds / span)} text={`${Math.round(Math.min(1, seconds / span) * 100)} %`} band={null} hint={`busy ${formatSeconds(seconds)} of the run's ${formatSeconds(span)}, first job's start to last job's end`} />}
      </div>
    </>
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
  onFocus: (group: string) => void;
  onHide: (id: string) => void;
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

/** A section title with its light icon. */
function H({ icon, children }: { icon: string; children: ReactNode }) {
  return (
    <h3 className="sp-sheet-h">
      <Icon path={icon} size={14} stroke={1.8} /> {children}
    </h3>
  );
}

function JobFacts({ task }: { task: Task }) {
  const r = task.resources;
  return (
    <>
      <H icon={GICONS.job}>Key</H>
      <dl className="sp-gfacts" aria-label="Key of this job">
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
      <H icon={GICONS.memory}>Asked and used</H>
      <dl className="sp-gfacts" aria-label="Resources of this job">
        <dt>Attempt</dt>
        <dd>{task.attempt_n ?? "—"}</dd>
        <dt>CPUs</dt>
        <dd>{r.cpus ?? "—"}</dd>
        <dt>Memory</dt>
        <dd>
          {bytes(r.peak_rss_bytes)} used of {bytes(r.memory_bytes)} asked
        </dd>
        <dt>Wall time</dt>
        <dd>{r.realtime_s !== null ? formatSeconds(r.realtime_s) : "—"}</dd>
      </dl>
    </>
  );
}

function NodeSheet({ run, doc, view, node, task, diff, onClose, onMember, onTrace, onOpen, onTasks, onToggle, onFocus, onHide, onEdge, trace }: SheetProps) {
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const members = node ? node.members.map((m) => byId.get(m)).filter((m) => !!m) : [];
  const single = node && members.length === 1 && node.id === members[0].id ? members[0] : null;
  const params = [...new Set(members.flatMap((m) => m.params))].sort();
  const { done, total } = node ? progress(node.counts) : { done: 0, total: 0 };
  const folded = node?.kind === "stage" || node?.kind === "subworkflow";
  const group = node?.group ?? null;
  // wall-clock times: the run's from its first start to its last end (now while it runs), the
  // step's from its first job's start to its last job's end
  const now = isTerminal(run.state) ? null : Date.now();
  const t = timeSpan(doc);
  const span = t ? Math.max(0, ((now ?? t.to) - t.from) / 1000) : 0;
  const wall = node?.first_start ? Math.max(0, ((node.last_end ? Date.parse(node.last_end) : now ?? Date.parse(node.first_start)) - Date.parse(node.first_start)) / 1000) : 0;
  const tone = statusTone(node?.status ?? null);
  return (
    <Panel id={node?.id ?? null} opened={node !== null} onClose={onClose} title={node ? node.label : ""} icon={kindIcon(node?.kind ?? "process")} tone={tone} kind={node ? kindWord(node.kind) : ""}>
      {node && (
        <section className="sp-sheet" aria-label={node.label}>
          <div className="sp-ghero">
            <span className="sp-state" data-tone={tone}>
              {statusWord(node.status)}
            </span>
            {total > 0 && node.kind !== "job" && (
              <span className="sp-ghero-jobs">
                <span className="sp-ghero-bar" role="img" aria-label={`${done} of ${total} jobs done`}>
                  <span style={{ width: `${Math.round((done / total) * 100)}%` }} />
                </span>
                {done}/{total} jobs
              </span>
            )}
            {durationOf(node) > 0 && (
              <span className="sp-ghero-time">
                <Icon path={GICONS.clock} size={12} stroke={1.9} />
                {formatSeconds(durationOf(node))}
              </span>
            )}
          </div>
          {diff && diff.change === "added" && <p className="sp-gnote">New in this run: the compared run did not have it.</p>}
          {node.flags && node.flags.length > 0 && (
            <p className="sp-gflags-row">
              {node.flags.map((f) => (
                <FlagChip key={f} flag={f} />
              ))}
            </p>
          )}
          <div className="sp-gactions" role="group" aria-label={`Actions on ${node.label}`}>
            {group && (
              <button type="button" className="sp-gaction" onClick={() => onToggle(group)} aria-label={folded ? `Unfold ${node.label}` : `Fold ${groupLabel(doc, group)}`}>
                <Icon path={folded ? GICONS.unfold : GICONS.fold} size={14} stroke={2} />
                {folded ? "Unfold" : "Fold"}
              </button>
            )}
            <button type="button" className="sp-gaction" aria-pressed={trace === "up"} onClick={() => onTrace(trace === "up" ? null : "up")} aria-label={`Before: what leads to ${node.label}`}>
              <Icon path={GICONS.up} size={14} stroke={2} />
              Before
            </button>
            <button type="button" className="sp-gaction" aria-pressed={trace === "down"} onClick={() => onTrace(trace === "down" ? null : "down")} aria-label={`After: what follows ${node.label}`}>
              <Icon path={GICONS.down} size={14} stroke={2} />
              After
            </button>
            {group && (
              <button type="button" className="sp-gaction" onClick={() => onFocus(group)} aria-label={`Focus: show only ${groupLabel(doc, group)}`}>
                <Icon path={GICONS.focus} size={14} stroke={2} />
                Focus
              </button>
            )}
            {node.kind !== "stage" && node.kind !== "subworkflow" && (
              <button type="button" className="sp-gaction" onClick={() => onHide(node.kind === "job" ? node.members[0] : node.id)} aria-label={`Hide ${node.kind === "job" ? node.step : node.label} from the map`}>
                <Icon path={GICONS.hide} size={14} stroke={2} />
                Hide
              </button>
            )}
          </div>
          {(single?.source || single?.condition || node.kind === "job") && (
            <dl className="sp-gfacts">
              {node.kind === "job" && (
                <>
                  <dt>
                    <Icon path={GICONS.process} size={13} stroke={1.8} /> Step
                  </dt>
                  <dd>{node.step}</dd>
                </>
              )}
              {single?.source && (
                <>
                  <dt>
                    <Icon path={GICONS.rule} size={13} stroke={1.8} /> Code
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
                    <Icon path={GICONS.conditional} size={13} stroke={1.8} /> Runs if
                  </dt>
                  <dd>
                    <code>{single.condition}</code>
                  </dd>
                </>
              )}
            </dl>
          )}
          <H icon={doc.engine === "snakemake" ? GICONS.file : GICONS.channel}>Links</H>
          <Wiring view={view} node={node} engine={doc.engine} onEdge={onEdge} />
          {task ? (
            <Efficiency cpu={task.efficiency?.cpu} mem={task.efficiency?.mem} seconds={task.resources.realtime_s ?? 0} span={span} words={{ cpu: "CPU time over CPUs asked", mem: "peak memory over memory asked" }} />
          ) : (
            <Efficiency cpu={node.metrics.cpu_mean} mem={node.metrics.mem_max} seconds={wall} span={span} words={{ cpu: "mean over its jobs", mem: "its highest job" }} />
          )}
          {task && (
            <>
              <JobFacts task={task} />
              <p>
                <button type="button" className="sp-link-button" onClick={() => onOpen({ kind: "task", task })}>
                  Open this job: script, logs, files
                </button>
              </p>
              <H icon={GICONS.outputs}>Outputs</H>
              <Outputs run={run} process={node.members[0]} task={task.id} />
            </>
          )}
          {members.length > 1 && (
            <>
              <H icon={GICONS.jobs}>Steps ({members.length})</H>
              <ul className="sp-gsteps" aria-label={`Steps of ${node.label}`}>
                {members.map((m) => (
                  <li key={m.id}>
                    <button type="button" className="sp-gwire-chip" data-tone={statusTone(m.status ?? null)} aria-label={`Show ${m.name} on the graph, ${statusWord(m.status ?? null)}`} onClick={() => onMember(m.id)}>
                      <Icon path={kindIcon(m.kind)} size={12} stroke={1.9} />
                      <span>{m.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          {single && single.kind !== "gate" && (
            <>
              <H icon={GICONS.outputs}>Outputs</H>
              <Outputs run={run} process={single.id} />
              <Retries run={run} process={single.id} onOpen={onOpen} />
              <p className="sp-gjobs-links">
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
          <H icon={GICONS.params}>Parameters</H>
          {params.length === 0 ? (
            <p className="sp-muted">No parameter is known to be read by {members.length > 1 ? "these steps" : "this step"}.</p>
          ) : (
            // a table: name, kind, value, aligned; the run's own values first, the defaults after
            // (Thomas: easier to read)
            <table className="sp-gdecl-table sp-gparams" aria-label={`Parameters of ${node.label}`}>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Value in this run</th>
                </tr>
              </thead>
              <tbody>
                {params
                  .map((p) => [p, paramOf(run.params, p)] as const)
                  .sort((a, b) => Number(b[1].set) - Number(a[1].set))
                  .map(([p, v]) => (
                    <tr key={p} data-set={v.set || undefined}>
                      <th scope="row" className="sp-mono">
                        {p}
                      </th>
                      <td>
                        <span className="sp-gdecl-kind" data-kind={v.kind}>
                          {v.kind}
                        </span>
                      </td>
                      <td className={v.set ? "sp-mono" : "sp-muted"} data-bool={v.kind === "yes/no" ? v.text : undefined}>
                        {v.text}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
          {(single || node.kind === "job") && (
            <details className="sp-gdetails">
              <summary>
                <Icon path={GICONS.code} size={14} stroke={1.8} /> Code
              </summary>
              <Code name={node.members[0]} code={byId.get(node.members[0])?.code} where={{ location: run.workflow.location, revision: null, fromRun: true }} />
            </details>
          )}
        </section>
      )}
    </Panel>
  );
}

/** What a step's code declares on one side of a link: Nextflow channel items (`tuple val(meta),
 * path(reads)`, with their `emit:` names), Snakemake files (with `temp`, `directory`…). */
function Declares({ name, label, code, engine, section, where }: { name: string; label: string; code?: string | null; engine: string; section: "input" | "output"; where: CodeSource }) {
  const { text, error } = useCode(name, code, where);
  const found: Declared[] = text ? declarations(text, engine, section) : [];
  const title = `${label} ${section === "output" ? (engine === "snakemake" ? "writes" : "emits") : engine === "snakemake" ? "reads" : "takes"}`;
  return (
    <div className="sp-gdecl">
      <p className="sp-gdecl-title">
        <Icon path={section === "output" ? GICONS.outputs : GICONS.up} size={13} stroke={1.9} /> {title}
      </p>
      {text === null ? (
        <p className="sp-muted">{error ? "Its code is not available." : "Reading its code…"}</p>
      ) : found.length === 0 ? (
        <p className="sp-muted">No {section} block found in its code.</p>
      ) : (
        // a small table, one row per item part: the channel's (or file's) name, its kind, its
        // value, aligned (Thomas: key and value, like a table)
        <table className="sp-gdecl-table" aria-label={title}>
          <thead>
            <tr>
              <th scope="col">{engine === "snakemake" ? "Name" : section === "output" ? "Emit" : "Input"}</th>
              <th scope="col">Kind</th>
              <th scope="col">{engine === "snakemake" ? "Pattern" : "Value"}</th>
            </tr>
          </thead>
          {found.map((d, i) => (
            <tbody key={i} title={d.text}>
              {d.parts.map((p, j) => (
                <tr key={j}>
                  {j === 0 && (
                    <th scope="rowgroup" rowSpan={d.parts.length} className="sp-mono">
                      {d.label ?? (engine === "snakemake" ? `#${i + 1}` : section === "input" ? `#${i + 1}` : "—")}
                      {d.optional && <span className="sp-gdecl-opt">optional</span>}
                      {d.parts.length > 1 && <span className="sp-gdecl-opt">tuple</span>}
                    </th>
                  )}
                  <td>
                    <span className="sp-gdecl-kind" data-kind={p.kind}>
                      {p.kind}
                    </span>
                  </td>
                  <td className="sp-mono">{p.name || "—"}</td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      )}
    </div>
  );
}

/** What flows along a link: Snakemake links steps through files, Nextflow through channels whose
 * items are the files the upstream step emitted. Shown: the two steps, the link between them, and
 * the upstream side's recorded outputs as file cards. */
function EdgeSheet({ run, doc, view, edge, onClose, onNode }: { run: RunDetail; doc: GraphDocument; view: View; edge: ViewEdge | null; onClose: () => void; onNode: (id: string) => void }) {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const names = new Map(doc.nodes.map((n) => [n.id, n.name]));
  const from = edge ? byId.get(edge.source) : undefined;
  const to = edge ? byId.get(edge.target) : undefined;
  const sources = edge ? [...new Set(edge.pairs.map(([a]) => a))] : [];
  const job = from?.kind === "job" ? from.id.slice("job:".length) : undefined;
  const smk = doc.engine === "snakemake";
  // the two steps' own names (a job's step, a folded box's first link)
  const [upStep, downStep] = edge ? edge.pairs[0] ?? [from?.members[0] ?? edge.source, to?.members[0] ?? edge.target] : ["", ""];
  const byDoc = new Map(doc.nodes.map((n) => [n.id, n]));
  const where: CodeSource = { location: run.workflow.location, revision: null, fromRun: true };
  const idle = !from?.status || from.status === "pending" || from.status === "not_needed" || from.status === "no_tasks";
  const end = (n: ViewNode | undefined, id: string) => (
    <button type="button" className="sp-gflow-end" data-tone={statusTone(n?.status ?? null)} onClick={() => onNode(id)} aria-label={`Open ${n?.label ?? id}`}>
      <Icon path={kindIcon(n?.kind ?? "process")} size={14} stroke={1.9} />
      <span>{n?.label ?? id}</span>
    </button>
  );
  return (
    <Panel id={edge?.id ?? null} opened={edge !== null} onClose={onClose} title={edge ? `${from?.label ?? edge.source} → ${to?.label ?? edge.target}` : ""} icon={smk ? GICONS.file : GICONS.channel} kind={smk ? "files" : "channel"}>
      {edge && (
        <section className="sp-sheet" aria-label="Link">
          <div className="sp-gflow-diagram">
            {end(from, edge.source)}
            <div className="sp-gflow-pipe">
              <span className="sp-gflow-carrier">
                <Icon path={smk ? GICONS.file : GICONS.channel} size={13} stroke={1.9} />
                {smk ? "files" : "channel"}
              </span>
              {edge.conditions.length > 0 && (
                <span className="sp-gflow-if">
                  <Icon path={GICONS.conditional} size={12} stroke={1.9} /> if <code>{edge.conditions.join(" or ")}</code>
                </span>
              )}
            </div>
            {end(to, edge.target)}
          </div>
          <H icon={smk ? GICONS.file : GICONS.channel}>{smk ? "Files, as the code declares them" : "Channel type, as the code declares it"}</H>
          <div className="sp-gdecls">
            <Declares name={upStep} label={byDoc.get(upStep)?.name ?? upStep} code={byDoc.get(upStep)?.code} engine={doc.engine} section="output" where={where} />
            <Declares name={downStep} label={byDoc.get(downStep)?.name ?? downStep} code={byDoc.get(downStep)?.code} engine={doc.engine} section="input" where={where} />
          </div>
          {edge.pairs.length > 1 && (
            <>
              <H icon={GICONS.link}>Links it stands for ({edge.pairs.length})</H>
              <ul className="sp-gsheet-list">
                {edge.pairs.map(([a, b]) => (
                  <li key={`${a}->${b}`} className="sp-mono">
                    {names.get(a) ?? a} → {names.get(b) ?? b}
                  </li>
                ))}
              </ul>
            </>
          )}
          <H icon={GICONS.outputs}>{smk ? "Files written upstream" : "Files emitted upstream"}</H>
          {idle ? (
            <p className="sp-muted">{`${from?.label ?? edge.source} ${from?.status === "not_needed" ? "is not needed in this run" : "has not run yet"}: nothing has flowed through this link.`}</p>
          ) : sources.map((p) => (
            <div key={p}>
              {sources.length > 1 && <p className="sp-gfrom sp-mono">{names.get(p) ?? p}</p>}
              <Outputs run={run} process={p} task={job} />
            </div>
          ))}
        </section>
      )}
    </Panel>
  );
}

/** The groups a step sits in: its stage, and its subworkflow and every one above it. */
export function groupsAround(doc: GraphDocument, id: string): string[] {
  const n = doc.nodes.find((x) => x.id === id);
  if (!n) return [];
  const parent = new Map(doc.groups.map((g) => [g.id, g.parent ?? null]));
  const out = n.stage_id ? [`stage:${n.stage_id}`] : [];
  for (let at = n.subworkflow ?? null; at; at = parent.get(at) ?? null) out.push(at);
  return out;
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
  const view = useMemo(() => (doc ? viewOf(doc, settings, settings.level === "jobs" ? jobs : undefined) : null), [doc, settings.level, jobs, settings.fold, settings.focus, settings.hide]); // eslint-disable-line react-hooks/exhaustive-deps
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
        onReset={() => (setEdge(null), setTrace(null), set({ node: null }))}
        source={source}
        side={
          <>
            <EdgeSheet run={run} doc={doc} view={view} edge={edge} onClose={() => setEdge(null)} onNode={(id) => (setEdge(null), set({ node: id }))} />
            <NodeSheet
              run={run}
              doc={doc}
              view={view}
              node={selected}
              task={task}
              diff={selected ? diff?.get(selected.id) ?? null : null}
              onClose={() => set({ node: null })}
              // a step listed in a group's panel: open its groups where we are, at the same
              // level, so it is drawn and its panel opens (Thomas: the panel just closed)
              onMember={(id) => {
                const opened = settings.level === "subworkflow" || settings.level === "stage";
                // at a folded level, only the groups it folds: its subworkflows, or its stage
                const around = groupsAround(doc, id).filter((g) => !opened || g.startsWith(settings.level === "stage" ? "stage:" : "sub:"));
                set({ node: id, fold: opened ? [...new Set([...settings.fold, ...around])] : settings.fold.filter((f) => !around.includes(f)) });
              }}
              onTrace={(direction) => {
                setTrace(direction && selected ? { id: selected.id, direction } : null);
              }}
              trace={trace && selected && trace.id === selected.id ? trace.direction : null}
              onOpen={(d) => (set({ node: null }), onOpen(d))}
              onTasks={onTasks}
              onToggle={(g) => set({ fold: toggled(settings.fold, g), node: null })}
              // at the folded levels `fold` lists the opened groups; elsewhere the folded ones (CR-02)
              onFocus={(g) => set({ focus: g, fold: settings.level === "subworkflow" || settings.level === "stage" ? [...new Set([...settings.fold, g])] : settings.fold.filter((f) => f !== g) })}
              onHide={(id) => set({ hide: [...settings.hide, id], node: null })}
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
