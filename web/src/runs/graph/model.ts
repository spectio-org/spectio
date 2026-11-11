// Pure functions of the workflow graph (issue #160): the levels a GraphDocument is shown at,
// search, the critical path, a diff with another run, lineage and replay. No React here.
import type { Counts, ProcessStatus, Task } from "../../api";
import type { GraphDocument, GraphLevel, GraphMetrics, GraphNode, GraphOverlay, NodeKind } from "./types";

export type ViewKind = NodeKind | "stage" | "subworkflow" | "job";

export interface ViewNode {
  id: string;
  label: string;
  kind: ViewKind;
  /** The document nodes it stands for (itself at the process level). */
  members: string[];
  status: ProcessStatus | null;
  counts: Counts;
  metrics: GraphMetrics;
  first_start: string | null;
  last_end: string | null;
  /** The lane it belongs to (Metro, Compact): its subworkflow, else its stage. */
  lane: string | null;
  laneLabel: string | null;
  /** BioFlow-Insight's position, when the document has one. */
  hint: { x: number; y: number } | null;
  /** The group a double-click folds or unfolds (a subworkflow or `stage:<id>`), if any. */
  group?: string | null;
  /** A job: its key (Nextflow's tag, Snakemake's wildcards) and its step's name. */
  key?: string | null;
  step?: string;
  /** What sets the step apart, drawn as marks: see FLAG_WORDS. */
  flags?: Flag[];
}

export type Flag = "checkpoint" | "temp" | "conditional" | "retried" | "cached";

/** A step's marks: a checkpoint (the DAG grows after it), temporary outputs, a condition in the
 * code, retried jobs, jobs reused from an earlier run. */
export function flagsOf(nodes: GraphNode[]): Flag[] {
  const out: Flag[] = [];
  if (nodes.some((n) => n.kind === "checkpoint")) out.push("checkpoint");
  if (nodes.some((n) => n.temp)) out.push("temp");
  if (nodes.some((n) => n.condition)) out.push("conditional");
  if (nodes.some((n) => (n.retries ?? 0) > 0)) out.push("retried");
  if (nodes.some((n) => (n.counts?.cached ?? 0) + (n.counts?.stored ?? 0) > 0)) out.push("cached");
  return out;
}

export interface ViewEdge {
  id: string;
  source: string;
  target: string;
  /** The conditions of the links it stands for, when known. */
  conditions: string[];
  /** The document links it stands for, as [source, target] node ids. */
  pairs: [string, string][];
}

export interface View {
  nodes: ViewNode[];
  edges: ViewEdge[];
}

const DONE: ProcessStatus[] = ["done", "up_to_date", "not_needed", "no_tasks"];
// The first status any member has wins, in this order.
const RANK: ProcessStatus[] = ["failed", "running", "awaiting_checkpoint", "stopped", "pending"];

/** One status for many nodes: failed, then running…; all done-like: done; some done and some
 * pending: running (the group is under way). */
export function aggregateStatus(statuses: (ProcessStatus | null | undefined)[]): ProcessStatus | null {
  const known = statuses.filter((s): s is ProcessStatus => !!s);
  if (known.length === 0) return null;
  if (known.every((s) => DONE.includes(s))) return known.every((s) => s === known[0]) ? known[0] : "done";
  if (known.includes("pending") && known.some((s) => DONE.includes(s)) && !known.includes("failed")) return "running";
  return RANK.find((s) => known.includes(s)) ?? known[0];
}

function sumCounts(all: Counts[]): Counts {
  const out: Counts = {};
  for (const counts of all) for (const [k, v] of Object.entries(counts)) out[k] = (out[k] ?? 0) + v;
  return out;
}

const minIso = (xs: (string | null | undefined)[]) => xs.filter((x): x is string => !!x).sort()[0] ?? null;
const maxIso = (xs: (string | null | undefined)[]) => xs.filter((x): x is string => !!x).sort().at(-1) ?? null;

function sumMetrics(nodes: GraphNode[]): GraphMetrics {
  const vals = (k: keyof GraphMetrics) => nodes.map((n) => n.metrics?.[k]).filter((v): v is number => typeof v === "number");
  const sum = (k: keyof GraphMetrics) => (vals(k).length ? vals(k).reduce((a, b) => a + b, 0) : null);
  const max = (k: keyof GraphMetrics) => (vals(k).length ? Math.max(...vals(k)) : null);
  const cpu = vals("cpu_mean");
  return {
    duration_s: sum("duration_s"),
    failed: sum("failed"),
    mem_max: max("mem_max"),
    cpu_mean: cpu.length ? cpu.reduce((a, b) => a + b, 0) / cpu.length : null,
  };
}

function groupName(doc: GraphDocument, id: string | null): string | null {
  if (!id) return null;
  return doc.groups.find((g) => g.id === id)?.name ?? id.replace(/^(stage|sub):/, "");
}

function laneOf(n: GraphNode): string | null {
  return n.subworkflow ?? (n.stage_id ? `stage:${n.stage_id}` : null);
}

function processNode(doc: GraphDocument, n: GraphNode): ViewNode {
  const lane = laneOf(n);
  return {
    id: n.id,
    label: n.name,
    kind: n.kind,
    members: [n.id],
    status: n.status ?? null,
    counts: n.counts ?? {},
    metrics: n.metrics ?? {},
    first_start: n.first_start ?? null,
    last_end: n.last_end ?? null,
    lane,
    laneLabel: groupName(doc, lane),
    hint: n.layout ?? null,
    flags: flagsOf([n]),
  };
}

/** Edges between the nodes the document nodes collapse to, without loops or duplicates. */
function collapseEdges(doc: GraphDocument, to: (id: string) => string | undefined): ViewEdge[] {
  const seen = new Map<string, ViewEdge>();
  for (const e of doc.edges) {
    const source = to(e.source);
    const target = to(e.target);
    if (!source || !target || source === target) continue;
    const id = `${source}->${target}`;
    const edge = seen.get(id) ?? { id, source, target, conditions: [], pairs: [] };
    if (e.condition && !edge.conditions.includes(e.condition)) edge.conditions.push(e.condition);
    edge.pairs.push([e.source, e.target]);
    seen.set(id, edge);
  }
  return [...seen.values()];
}

function merged(doc: GraphDocument, id: string, label: string, kind: ViewKind, members: GraphNode[], lane: string | null): ViewNode {
  return {
    id,
    label,
    kind,
    members: members.map((m) => m.id),
    status: aggregateStatus(members.map((m) => m.status)),
    counts: sumCounts(members.map((m) => m.counts ?? {})),
    metrics: sumMetrics(members),
    first_start: minIso(members.map((m) => m.first_start)),
    last_end: maxIso(members.map((m) => m.last_end)),
    lane,
    laneLabel: groupName(doc, lane),
    hint: null,
    flags: flagsOf(members),
  };
}

/** The subworkflow each node collapses to: the outermost one below the wrapper chain (a root
 * subworkflow holding only one subworkflow and no node, as nf-core's NFCORE_X → X). */
export function collapsedSubworkflow(doc: GraphDocument): Map<string, string | null> {
  const subs = doc.groups.filter((g) => g.kind === "subworkflow");
  const children = (parent: string | null) => subs.filter((g) => g.parent === parent);
  const direct = (id: string | null) => doc.nodes.filter((n) => n.subworkflow === id);
  let root: string | null = null;
  for (;;) {
    const kids = children(root);
    if (kids.length !== 1 || direct(root).length > 0) break;
    root = kids[0].id;
  }
  const parentOf = new Map(subs.map((g) => [g.id, g.parent]));
  const out = new Map<string, string | null>();
  for (const n of doc.nodes) {
    let sub = n.subworkflow;
    // climb until the subworkflow is a child of the root
    while (sub && parentOf.has(sub) && parentOf.get(sub) !== root) sub = parentOf.get(sub) ?? null;
    out.set(n.id, sub && sub !== root ? sub : null);
  }
  return out;
}

const jobStatus: Record<string, ProcessStatus> = {
  pending: "pending",
  submitted: "pending",
  running: "running",
  succeeded: "done",
  cached: "up_to_date",
  stored: "up_to_date",
  failed: "failed",
  aborted: "stopped",
  not_scheduled: "not_needed",
};

/** A job's key as a set of tokens: Snakemake's `k=v` pairs, or the words of a Nextflow tag. */
function keyTokens(key: string | null | undefined): Set<string> | null {
  if (!key) return null;
  const tokens = key.split(/[\s,;|]+/).filter(Boolean);
  return tokens.length ? new Set(tokens) : null;
}

/** Two jobs of linked steps are linked when one step has a single job (a fan-in or a fan-out),
 * or when one job's key is part of the other's (same sample, or `sample=A` in
 * `sample=A, chrom=1`). Jobs with no key are linked only through a single job. */
const tokensOf = new WeakMap<ViewNode, Set<string> | null>(); // built once per job, not per pair

export function jobsLinked(a: ViewNode, b: ViewNode, sources: number, targets: number): boolean {
  if (sources === 1 || targets === 1) return true;
  const tokens = (n: ViewNode) => {
    if (!tokensOf.has(n)) tokensOf.set(n, keyTokens(n.key));
    return tokensOf.get(n) ?? null;
  };
  const x = tokens(a);
  const y = tokens(b);
  if (!x || !y) return false;
  const within = (p: Set<string>, q: Set<string>) => [...p].every((t) => q.has(t));
  return within(x, y) || within(y, x);
}

/** The fold list with `group` added, or removed when it is already there. */
export const toggled = (fold: string[], group: string): string[] => (fold.includes(group) ? fold.filter((g) => g !== group) : [...fold, group]);

/** The group a double-click on `n` folds at `level`, and the groups of the node's lane chain. */
function groupOf(doc: GraphDocument, n: GraphNode, level: GraphLevel, outer: Map<string, string | null>): string | null {
  if (level === "stage") return n.stage_id ? `stage:${n.stage_id}` : null;
  if (level === "subworkflow") return outer.get(n.id) ?? null;
  return n.subworkflow && doc.groups.some((g) => g.id === n.subworkflow) ? n.subworkflow : n.stage_id ? `stage:${n.stage_id}` : null;
}

function jobOf(t: Task, step: ViewNode): ViewNode {
  return {
    id: `job:${t.id}`,
    label: t.tag ?? t.name ?? t.id,
    kind: "job",
    members: [step.id],
    status: jobStatus[t.state] ?? null,
    counts: { [t.state]: 1 },
    metrics: {},
    first_start: null,
    last_end: null,
    lane: step.id,
    laneLabel: step.label,
    hint: null,
    group: step.group,
    key: t.tag,
    step: step.label,
  };
}

/** The document at a level. `jobs`: the loaded jobs of each step (Jobs level: every step with
 * jobs is replaced by one node per job, linked job to job). `toggle`: the groups folded or
 * unfolded by hand: at the Process and Jobs levels a listed group is folded into one node; at the
 * Subworkflow and Stage levels a listed group is unfolded into its steps. */
export function collapse(doc: GraphDocument, level: GraphLevel, jobs: Record<string, Task[]> = {}, toggle: string[] = []): View {
  const flip = new Set(toggle);
  const subs = new Map(doc.groups.filter((g) => g.kind === "subworkflow").map((g) => [g.id, g.parent]));
  const outer = collapsedSubworkflow(doc);
  const hasSubs = subs.size > 0;
  const key = new Map<string, string>();
  const buckets = new Map<string, { label: string; kind: ViewKind; members: GraphNode[]; lane: string | null; group: string | null }>();
  const put = (n: GraphNode, id: string, label: string, kind: ViewKind, lane: string | null, group: string | null) => {
    key.set(n.id, id);
    const bucket = buckets.get(id) ?? { label, kind, members: [], lane, group };
    bucket.members.push(n);
    buckets.set(id, bucket);
  };
  const own = (n: GraphNode, group: string | null) => put(n, n.id, n.name, n.kind, laneOf(n), group);
  for (const n of doc.nodes) {
    if (level === "stage") {
      const id = `stage:${n.stage_id ?? "-"}`;
      if (n.stage_id && flip.has(id)) own(n, id);
      else put(n, id, n.stage_id ? groupName(doc, id) ?? n.stage_id : "No stage", "stage", null, n.stage_id ? id : null);
    } else if (level === "subworkflow") {
      const sub = hasSubs ? outer.get(n.id) ?? null : null;
      if (sub && !flip.has(sub)) put(n, sub, groupName(doc, sub) ?? sub, "subworkflow", sub, sub);
      else own(n, sub);
    } else {
      // the outermost folded group holding the node wins: its subworkflows, then its stage
      let folded: string | null = null;
      for (let at = n.subworkflow; at; at = subs.get(at) ?? null) if (flip.has(at)) folded = at;
      const stage = n.stage_id ? `stage:${n.stage_id}` : null;
      if (!folded && stage && flip.has(stage)) folded = stage;
      if (folded) put(n, folded, groupName(doc, folded) ?? folded, folded.startsWith("stage:") ? "stage" : "subworkflow", folded.startsWith("stage:") ? null : folded, folded);
      else own(n, groupOf(doc, n, level, outer));
    }
  }
  const nodes: ViewNode[] = [];
  for (const [id, b] of buckets) {
    const single = b.members.length === 1 && b.kind !== "stage" && b.kind !== "subworkflow";
    nodes.push({ ...(single ? processNode(doc, b.members[0]) : merged(doc, id, b.label, b.kind, b.members, b.lane)), group: b.group });
  }
  const view = { nodes, edges: collapseEdges(doc, (id) => key.get(id)) };
  return level === "jobs" ? explode(view, jobs) : view;
}

/** The Jobs level: each step with loaded jobs becomes its jobs, and each link between steps
 * becomes links between their jobs (`jobsLinked`). */
function explode(view: View, jobs: Record<string, Task[]>): View {
  const of = new Map<string, ViewNode[]>();
  const nodes: ViewNode[] = [];
  for (const n of view.nodes) {
    const loaded = n.members.length === 1 && n.id === n.members[0] ? jobs[n.id] : undefined;
    if (!loaded?.length) {
      nodes.push(n);
      of.set(n.id, [n]);
      continue;
    }
    const mine = loaded.map((t) => jobOf(t, n));
    nodes.push(...mine);
    of.set(n.id, mine);
  }
  const edges: ViewEdge[] = [];
  for (const e of view.edges) {
    const from = of.get(e.source) ?? [];
    const to = of.get(e.target) ?? [];
    for (const a of from)
      for (const b of to)
        if (jobsLinked(a, b, from.length, to.length)) edges.push({ id: `${a.id}->${b.id}`, source: a.id, target: b.id, conditions: e.conditions, pairs: e.pairs });
  }
  return { nodes, edges };
}

// ---- search ---------------------------------------------------------------------------------

/** The view nodes a query matches. Terms are ANDed: plain words match the name or the label;
 * `kind:`, `state:`, `param:` and `file:` match those fields of a member node. */
export function search(doc: GraphDocument, view: View, query: string): Set<string> {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const found = new Set<string>();
  if (terms.length === 0) return found;
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const matches = (v: ViewNode, term: string) => {
    const [field, value] = term.includes(":") ? [term.slice(0, term.indexOf(":")), term.slice(term.indexOf(":") + 1)] : ["", term];
    const members = v.members.map((m) => byId.get(m)).filter((m): m is GraphNode => !!m);
    switch (field) {
      case "kind":
        return v.kind.includes(value) || members.some((m) => m.kind.includes(value));
      case "state":
        return (v.status ?? "").includes(value) || members.some((m) => (m.status ?? "").includes(value));
      case "param":
        return members.some((m) => m.params.some((p) => p.toLowerCase().includes(value)));
      case "file":
        return members.some((m) => (m.source?.file ?? "").toLowerCase().includes(value));
      default:
        return v.label.toLowerCase().includes(term) || members.some((m) => m.id.toLowerCase().includes(term));
    }
  };
  for (const v of view.nodes) if (terms.every((t) => matches(v, t))) found.add(v.id);
  return found;
}

// ---- topology -------------------------------------------------------------------------------

/** The view without its back edges (found by depth-first search from the nodes in order), so
 * the algorithms below run on a DAG: a static graph read from the code can have cycles. */
export function acyclic(view: View): View {
  const out = new Map<string, ViewEdge[]>();
  for (const e of view.edges) out.set(e.source, [...(out.get(e.source) ?? []), e]);
  const state = new Map<string, 1 | 2>(); // 1 on the stack, 2 done
  const back = new Set<string>();
  for (const root of view.nodes) {
    if (state.has(root.id)) continue;
    // iterative DFS: [node, index of its next edge]
    const stack: [string, number][] = [[root.id, 0]];
    state.set(root.id, 1);
    while (stack.length) {
      const top = stack[stack.length - 1];
      const edges = out.get(top[0]) ?? [];
      if (top[1] >= edges.length) {
        state.set(top[0], 2);
        stack.pop();
        continue;
      }
      const e = edges[top[1]++];
      const s = state.get(e.target);
      if (s === 1) back.add(e.id);
      else if (s === undefined) {
        state.set(e.target, 1);
        stack.push([e.target, 0]);
      }
    }
  }
  return back.size ? { nodes: view.nodes, edges: view.edges.filter((e) => !back.has(e.id)) } : view;
}

/** Kahn's order on the view without its back edges. */
export function topoOrder(full: View): string[] {
  const view = acyclic(full);
  const ids = view.nodes.map((n) => n.id);
  const indeg = new Map(ids.map((id) => [id, 0]));
  const out = new Map<string, string[]>(ids.map((id) => [id, []]));
  for (const e of view.edges) {
    if (!indeg.has(e.source) || !indeg.has(e.target)) continue;
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1);
    out.get(e.source)!.push(e.target);
  }
  const ready = ids.filter((id) => indeg.get(id) === 0);
  const done: string[] = [];
  while (ready.length) {
    const id = ready.shift()!;
    done.push(id);
    for (const t of out.get(id)!) {
      indeg.set(t, indeg.get(t)! - 1);
      if (indeg.get(t) === 0) ready.push(t);
    }
  }
  const placed = new Set(done);
  return [...done, ...ids.filter((id) => !placed.has(id))];
}

/** Each node's rank: 0 for a source, else one more than its highest predecessor. */
export function ranks(full: View): Map<string, number> {
  const view = acyclic(full);
  const rank = new Map<string, number>();
  const preds = new Map<string, string[]>();
  for (const e of view.edges) preds.set(e.target, [...(preds.get(e.target) ?? []), e.source]);
  for (const id of topoOrder(view)) {
    const ps = (preds.get(id) ?? []).filter((p) => rank.has(p));
    rank.set(id, ps.length ? Math.max(...ps.map((p) => rank.get(p)!)) + 1 : 0);
  }
  return rank;
}

export function durationOf(n: ViewNode): number {
  if (typeof n.metrics.duration_s === "number") return n.metrics.duration_s;
  if (n.first_start && n.last_end) return Math.max(0, (Date.parse(n.last_end) - Date.parse(n.first_start)) / 1000);
  return 0;
}

/** The path with the longest sum of node durations: its nodes and edges. */
export function criticalPath(full: View): { nodes: Set<string>; edges: Set<string> } {
  const view = acyclic(full);
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const best = new Map<string, number>();
  const via = new Map<string, ViewEdge | null>();
  const incoming = new Map<string, ViewEdge[]>();
  for (const e of view.edges) incoming.set(e.target, [...(incoming.get(e.target) ?? []), e]);
  for (const id of topoOrder(view)) {
    let top = 0;
    let from: ViewEdge | null = null;
    for (const e of incoming.get(id) ?? []) {
      const b = best.get(e.source);
      if (b !== undefined && b > top) {
        top = b;
        from = e;
      }
    }
    best.set(id, top + durationOf(byId.get(id)!));
    via.set(id, from);
  }
  const nodes = new Set<string>();
  const edges = new Set<string>();
  let end: string | null = null;
  for (const [id, v] of best) if (v > 0 && (end === null || v > best.get(end)!)) end = id;
  for (let at = end; at; ) {
    if (nodes.has(at)) break;
    nodes.add(at);
    const e: ViewEdge | null | undefined = via.get(at);
    if (!e) break;
    edges.add(e.id);
    at = e.source;
  }
  return { nodes, edges };
}

/** Ancestors (`up`), descendants (`down`) or both of a node, itself included. */
export function lineage(view: View, id: string, direction: "up" | "down" | "both"): Set<string> {
  const found = new Set([id]);
  // each walk keeps its own visited set: with a cycle, the other walk's nodes must still be crossed
  const walk = (dir: "up" | "down") => {
    const seen = new Set([id]);
    const queue = [id];
    while (queue.length) {
      const at = queue.shift()!;
      for (const e of view.edges) {
        const [from, to] = dir === "down" ? [e.source, e.target] : [e.target, e.source];
        if (from === at && !seen.has(to)) {
          seen.add(to);
          found.add(to);
          queue.push(to);
        }
      }
    }
  };
  if (direction !== "down") walk("up");
  if (direction !== "up") walk("down");
  return found;
}

// ---- diff -----------------------------------------------------------------------------------

export interface NodeDiff {
  change: "added" | "removed" | "same";
  /** Seconds, this run minus the other; null when either has no duration. */
  duration_delta: number | null;
  /** This run's tasks were reused (cached) rather than run again. */
  reuse: "cached" | "rerun" | "mixed" | null;
}

function reuseOf(counts: Counts | undefined): NodeDiff["reuse"] {
  const cached = (counts?.cached ?? 0) + (counts?.stored ?? 0);
  const ran = (counts?.succeeded ?? 0) + (counts?.failed ?? 0) + (counts?.running ?? 0);
  if (!cached && !ran) return null;
  return cached && ran ? "mixed" : cached ? "cached" : "rerun";
}

/** This run's graph against another's, node by node (by id). */
export function diffGraphs(mine: GraphDocument, other: GraphDocument): Map<string, NodeDiff> {
  const theirs = new Map(other.nodes.map((n) => [n.id, n]));
  const out = new Map<string, NodeDiff>();
  const dur = (n: GraphNode) => (typeof n.metrics?.duration_s === "number" ? n.metrics.duration_s : null);
  for (const n of mine.nodes) {
    const o = theirs.get(n.id);
    const a = dur(n);
    const b = o ? dur(o) : null;
    out.set(n.id, {
      change: o ? "same" : "added",
      duration_delta: a !== null && b !== null ? a - b : null,
      reuse: reuseOf(n.counts),
    });
  }
  for (const o of other.nodes) if (!out.has(o.id)) out.set(o.id, { change: "removed", duration_delta: null, reuse: null });
  return out;
}

// ---- replay and overlays --------------------------------------------------------------------

/** The run's time span: the first start and the last end of any node. */
export function timeSpan(doc: GraphDocument): { from: number; to: number } | null {
  const from = minIso(doc.nodes.map((n) => n.first_start));
  const to = maxIso(doc.nodes.map((n) => n.last_end ?? n.first_start));
  return from && to ? { from: Date.parse(from), to: Date.parse(to) } : null;
}

/** A node's state at time `t` (ms): pending before its first start, running until its last
 * end, then its final status. */
export function statusAt(n: ViewNode, t: number): ProcessStatus | null {
  if (!n.first_start || t < Date.parse(n.first_start)) return n.first_start ? "pending" : n.status;
  if (!n.last_end || t < Date.parse(n.last_end)) return "running";
  return n.status;
}

/** The value an overlay colours by, or null when the node has none. */
export function overlayValue(n: ViewNode, overlay: GraphOverlay): number | null {
  switch (overlay) {
    case "duration":
      return durationOf(n) || null;
    case "cpu":
      return n.metrics.cpu_mean ?? null;
    case "memory":
      return n.metrics.mem_max ?? null;
    case "failures":
      return n.metrics.failed ?? n.counts.failed ?? null;
    default:
      return null;
  }
}

/** Each node's overlay value on 0..1 against the view's maximum. */
export function heat(view: View, overlay: GraphOverlay): Map<string, number> {
  const out = new Map<string, number>();
  const vals = view.nodes.map((n) => [n.id, overlayValue(n, overlay)] as const);
  const max = Math.max(0, ...vals.map(([, v]) => v ?? 0));
  for (const [id, v] of vals) if (v !== null && max > 0) out.set(id, v / max);
  return out;
}

// ---- focus, hide, auto-fold -----------------------------------------------------------------

/** The view with only `focus`'s steps (a subworkflow, nested ones included, or a stage), and
 * without the `hide` steps. A hidden step's links are bridged, so what ran before it still
 * leads to what ran after it. */
export function restrict(doc: GraphDocument, view: View, focus: string | null, hide: string[]): View {
  if (!focus && hide.length === 0) return view;
  const parent = new Map(doc.groups.map((g) => [g.id, g.parent ?? null]));
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const within = (m: string) => {
    const n = byId.get(m);
    if (!n) return false;
    if (n.stage_id && `stage:${n.stage_id}` === focus) return true;
    for (let at = n.subworkflow ?? null; at; at = parent.get(at) ?? null) if (at === focus) return true;
    return false;
  };
  const hidden = new Set(hide);
  const gone = (n: ViewNode) => hidden.has(n.id) || (n.members.length === 1 && hidden.has(n.members[0]));
  const keep = new Set(view.nodes.filter((n) => (!focus || n.id === focus || n.members.some(within)) && !gone(n)).map((n) => n.id));
  const out = new Map<string, ViewEdge[]>();
  for (const e of view.edges) out.set(e.source, [...(out.get(e.source) ?? []), e]);
  const hiddenIds = new Set(view.nodes.filter(gone).map((n) => n.id));
  const edges: ViewEdge[] = view.edges.filter((e) => keep.has(e.source) && keep.has(e.target));
  const have = new Set(edges.map((e) => `${e.source}>${e.target}`));
  for (const e of view.edges) {
    if (!keep.has(e.source) || !hiddenIds.has(e.target)) continue;
    // walk through hidden steps only, to the kept steps they lead to, keeping the conditions
    // met on the way (CR-14)
    const seen = new Set<string>();
    const stack: [string, string[]][] = [[e.target, e.conditions]];
    while (stack.length) {
      const [at, conditions] = stack.pop()!;
      if (seen.has(at)) continue;
      seen.add(at);
      for (const next of out.get(at) ?? []) {
        const t = next.target;
        const all = [...new Set([...conditions, ...next.conditions])];
        if (hiddenIds.has(t)) stack.push([t, all]);
        else if (keep.has(t) && !have.has(`${e.source}>${t}`)) {
          have.add(`${e.source}>${t}`);
          edges.push({ id: `${e.source}->${t}`, source: e.source, target: t, conditions: all, pairs: [] });
        }
      }
    }
  }
  return { nodes: view.nodes.filter((n) => keep.has(n.id)), edges };
}

/** The groups to fold so the view has at most `max` boxes: the biggest groups first. */
export function autoFold(view: View, max: number): string[] {
  const sizes = new Map<string, number>();
  for (const n of view.nodes) if (n.group && n.kind !== "stage" && n.kind !== "subworkflow") sizes.set(n.group, (sizes.get(n.group) ?? 0) + 1);
  let count = view.nodes.length;
  const out: string[] = [];
  for (const [g, size] of [...sizes].sort((a, b) => b[1] - a[1])) {
    if (count <= max || size < 2) break;
    out.push(g);
    count -= size - 1;
  }
  return out;
}

/** How well a step's request fits its use, from an efficiency ratio (used over asked):
 * `low` under 30 % (much more asked than used), `fair` under 70 %, `good` up to 105 %, `over`
 * above (more used than asked: memory near its limit, or more CPUs used than asked). */
export type Band = "low" | "fair" | "good" | "over";
export const bandOf = (ratio: number): Band => (ratio < 0.3 ? "low" : ratio < 0.7 ? "fair" : ratio <= 1.05 ? "good" : "over");
