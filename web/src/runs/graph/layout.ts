// Node positions for each layout of the workflow graph (issue #160). Pure: a View in, boxes out.
import dagre from "@dagrejs/dagre";
import { ranks, topoOrder, type View, type ViewNode } from "./model";
import type { GraphLayout } from "./types";

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Lane {
  id: string;
  label: string;
  y: number;
  h: number;
}

export interface Placed {
  /** Top-left boxes of the view's nodes; a job's box is relative to its process. */
  boxes: Map<string, Box>;
  /** Metro and Compact: one horizontal band per lane. */
  lanes: Lane[];
}

export const NODE_W = 184;
export const NODE_H = 52;
const JOB_W = 112;
const JOB_H = 30;
const JOB_COLS = 4;
const GAP = 12;
const HEADER = 40;
const COL = NODE_W + 56;

/** A node's size: a process holding its jobs grows to fit them in a grid. */
export function sizeOf(n: ViewNode): { w: number; h: number } {
  const jobs = n.jobs?.length ?? 0;
  if (!jobs) return { w: NODE_W, h: NODE_H };
  const cols = Math.min(JOB_COLS, jobs);
  const rows = Math.ceil(jobs / JOB_COLS);
  return { w: Math.max(NODE_W, cols * (JOB_W + GAP) + GAP), h: HEADER + rows * (JOB_H + GAP) + GAP / 2 };
}

function placeJobs(n: ViewNode, boxes: Map<string, Box>) {
  n.jobs?.forEach((j, i) => {
    boxes.set(j.id, { x: GAP + (i % JOB_COLS) * (JOB_W + GAP), y: HEADER + Math.floor(i / JOB_COLS) * (JOB_H + GAP), w: JOB_W, h: JOB_H });
  });
}

function layered(view: View, rankdir: "TB" | "LR"): Map<string, Box> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir, nodesep: 32, ranksep: 56, marginx: 16, marginy: 16 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of view.nodes) g.setNode(n.id, { ...sizeOf(n), width: sizeOf(n).w, height: sizeOf(n).h });
  for (const e of view.edges) if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target);
  dagre.layout(g);
  const boxes = new Map<string, Box>();
  for (const n of view.nodes) {
    const p = g.node(n.id) as { x: number; y: number; width: number; height: number };
    boxes.set(n.id, { x: p.x - p.width / 2, y: p.y - p.height / 2, w: p.width, h: p.height });
  }
  return boxes;
}

function laneOrder(view: View): { id: string; label: string }[] {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const seen = new Map<string, string>();
  for (const id of topoOrder(view)) {
    const n = byId.get(id)!;
    const lane = n.lane ?? "";
    if (!seen.has(lane)) seen.set(lane, n.lane ? n.laneLabel ?? n.lane : "Other");
  }
  return [...seen].map(([id, label]) => ({ id, label }));
}

/** One band per lane (subworkflow or stage), x by rank: the metro map. Nodes of one lane and
 * one rank stack inside the band. */
function metro(view: View): Placed {
  const rank = ranks(view);
  const lanes = laneOrder(view);
  const boxes = new Map<string, Box>();
  const out: Lane[] = [];
  let y = 0;
  for (const lane of lanes) {
    const members = view.nodes.filter((n) => (n.lane ?? "") === lane.id);
    const stack = new Map<number, number>();
    let height = 0;
    for (const n of members) {
      const r = rank.get(n.id) ?? 0;
      const { w, h } = sizeOf(n);
      const off = stack.get(r) ?? 0;
      boxes.set(n.id, { x: 120 + r * COL, y: y + 28 + off, w, h });
      stack.set(r, off + h + GAP);
      height = Math.max(height, off + h);
    }
    out.push({ id: lane.id, label: lane.label, y, h: height + 44 });
    y += height + 60;
  }
  return { boxes, lanes: out };
}

/** One row per lane, nodes side by side in topological order. */
function compact(view: View): Placed {
  const order = topoOrder(view);
  const at = new Map(order.map((id, i) => [id, i]));
  const lanes = laneOrder(view);
  const boxes = new Map<string, Box>();
  const out: Lane[] = [];
  let y = 0;
  for (const lane of lanes) {
    const members = view.nodes.filter((n) => (n.lane ?? "") === lane.id).sort((a, b) => at.get(a.id)! - at.get(b.id)!);
    let x = 120;
    let height = 0;
    for (const n of members) {
      const { w, h } = sizeOf(n);
      boxes.set(n.id, { x, y: y + 28, w, h });
      x += w + GAP * 2;
      height = Math.max(height, h);
    }
    out.push({ id: lane.id, label: lane.label, y, h: height + 44 });
    y += height + 60;
  }
  return { boxes, lanes: out };
}

/** BioFlow-Insight's positions (Graphviz points, y up), scaled; nodes without one are laid out
 * by Layered below them. */
function upstream(view: View): Placed {
  const hinted = view.nodes.filter((n) => n.hint);
  if (hinted.length === 0) return { boxes: layered(view, "TB"), lanes: [] };
  const xs = hinted.map((n) => n.hint!.x);
  const ys = hinted.map((n) => n.hint!.y);
  const [minX, maxY] = [Math.min(...xs), Math.max(...ys)];
  const boxes = new Map<string, Box>();
  let bottom = 0;
  for (const n of hinted) {
    const { w, h } = sizeOf(n);
    const box = { x: (n.hint!.x - minX) * 2.2, y: (maxY - n.hint!.y) * 2.2, w, h };
    boxes.set(n.id, box);
    bottom = Math.max(bottom, box.y + h);
  }
  const rest = view.nodes.filter((n) => !n.hint);
  if (rest.length) {
    const more = layered({ nodes: rest, edges: view.edges }, "TB");
    for (const [id, b] of more) boxes.set(id, { ...b, y: b.y + bottom + 60 });
  }
  return { boxes, lanes: [] };
}

export function hasUpstream(view: View): boolean {
  return view.nodes.some((n) => n.hint);
}

export function place(view: View, layout: GraphLayout): Placed {
  let placed: Placed;
  if (layout === "metro") placed = metro(view);
  else if (layout === "compact") placed = compact(view);
  else if (layout === "upstream") placed = upstream(view);
  else placed = { boxes: layered(view, layout === "layered-lr" ? "LR" : "TB"), lanes: [] };
  for (const n of view.nodes) placeJobs(n, placed.boxes);
  return placed;
}
