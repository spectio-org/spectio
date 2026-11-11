// Node positions for each layout of the workflow graph (issue #160). Pure: a View in, boxes out.
import dagre from "@dagrejs/dagre";
import { topoOrder, type View, type ViewNode } from "./model";
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
  /** Left edge and width; absent: the band spans the whole map. */
  x?: number;
  w?: number;
  y: number;
  h: number;
}

export interface Placed {
  /** Top-left boxes of the view's nodes. */
  boxes: Map<string, Box>;
  /** Metro and Compact: one horizontal band per lane. */
  lanes: Lane[];
}

export const NODE_W = 184;
export const NODE_H = 52;
export const JOB_W = 150;
export const JOB_H = 44;
const GAP = 12;
const WRAP = 6; // Compact: the most nodes in one row of a lane
const TITLE = 32; // room above a group area for its name (and the marks riding on its steps)

/** A node's size: a job (Jobs level) is smaller than a step. */
export function sizeOf(n: ViewNode): { w: number; h: number } {
  return n.kind === "job" ? { w: JOB_W, h: JOB_H } : { w: NODE_W, h: NODE_H };
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

/** Metro: Layered left-right, with each subworkflow or stage drawn as an area around its steps
 * (dagre compound nodes), so a group's steps stay together and only the space they need is used. */
function metro(view: View): Placed {
  const g = new dagre.graphlib.Graph({ compound: true });
  g.setGraph({ rankdir: "LR", nodesep: 22, ranksep: 64, marginx: 16, marginy: 16 + TITLE });
  g.setDefaultEdgeLabel(() => ({}));
  const lanes = laneOrder(view).filter((l) => l.id !== "");
  for (const lane of lanes) g.setNode(`lane:${lane.id}`, { label: lane.label });
  for (const n of view.nodes) {
    const { w, h } = sizeOf(n);
    // a step leaves room above it for its area's title
    g.setNode(n.id, { width: w, height: h + (n.lane ? TITLE : 0) });
    if (n.lane) g.setParent(n.id, `lane:${n.lane}`);
  }
  for (const e of view.edges) if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target);
  dagre.layout(g);
  const boxes = new Map<string, Box>();
  for (const n of view.nodes) {
    const p = g.node(n.id) as { x: number; y: number; width: number; height: number };
    const { w, h } = sizeOf(n);
    boxes.set(n.id, { x: p.x - w / 2, y: p.y - p.height / 2 + (n.lane ? TITLE : 0), w, h });
  }
  const out: Lane[] = [];
  for (const lane of lanes) {
    const kids = view.nodes.filter((n) => n.lane === lane.id).map((n) => boxes.get(n.id)!);
    if (kids.length === 0) continue;
    const x = Math.min(...kids.map((b) => b.x)) - 12;
    const y = Math.min(...kids.map((b) => b.y)) - TITLE - 6;
    out.push({ id: lane.id, label: lane.label, x, y, w: Math.max(...kids.map((b) => b.x + b.w)) + 12 - x, h: Math.max(...kids.map((b) => b.y + b.h)) + 12 - y });
  }
  return { boxes, lanes: out };
}

/** Compact: each lane is a near-square grid in topological order, and the lanes are packed in
 * rows (shelves) about twice as wide as the square of the same area, to suit a wide screen,
 * rather than one long band each. */
function compact(view: View): Placed {
  const order = topoOrder(view);
  const at = new Map(order.map((id, i) => [id, i]));
  const blocks = laneOrder(view).map((lane) => {
    const members = view.nodes.filter((n) => (n.lane ?? "") === lane.id).sort((a, b) => at.get(a.id)! - at.get(b.id)!);
    const cols = Math.max(1, Math.min(WRAP, Math.ceil(Math.sqrt(members.length * 1.6))));
    const cell = members.some((n) => n.kind !== "job") ? { w: NODE_W, h: NODE_H } : { w: JOB_W, h: JOB_H };
    const rows = Math.ceil(members.length / cols);
    return { lane, members, cols, cell, w: cols * (cell.w + GAP * 2) - GAP * 2 + 24, h: rows * (cell.h + GAP) - GAP + TITLE + 18 };
  });
  const area = blocks.reduce((a, b) => a + b.w * b.h, 0);
  const width = Math.max(Math.max(0, ...blocks.map((b) => b.w)), Math.sqrt(area) * 2);
  const boxes = new Map<string, Box>();
  const out: Lane[] = [];
  let x = 0;
  let y = 0;
  let shelf = 0;
  for (const b of blocks) {
    if (x > 0 && x + b.w > width) {
      x = 0;
      y += shelf + 24;
      shelf = 0;
    }
    b.members.forEach((n, i) => {
      const { w, h } = sizeOf(n);
      boxes.set(n.id, { x: x + 12 + (i % b.cols) * (b.cell.w + GAP * 2), y: y + TITLE + Math.floor(i / b.cols) * (b.cell.h + GAP), w, h });
    });
    out.push({ id: b.lane.id, label: b.lane.label, x, w: b.w, y, h: b.h });
    x += b.w + 24;
    shelf = Math.max(shelf, b.h);
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
  // No edges (stages-only): ranks and layers mean nothing, so every layout but Upstream is the
  // wrapped grid per lane; otherwise dagre would set every node on one line.
  if (view.edges.length === 0 && layout !== "upstream") placed = compact(view);
  else if (layout === "metro") placed = metro(view);
  else if (layout === "compact") placed = compact(view);
  else if (layout === "upstream") placed = upstream(view);
  else placed = { boxes: layered(view, layout === "layered-lr" ? "LR" : "TB"), lanes: [] };
  return placed;
}

/** The centre-top of what a group occupies on the map: its folded box, or its steps' boxes. */
export function groupBox(view: View, placed: Placed, group: string): { x: number; y: number } | null {
  const boxes = view.nodes.filter((n) => n.id === group || n.group === group).map((n) => placed.boxes.get(n.id)).filter((b) => !!b);
  if (boxes.length === 0) return null;
  const left = Math.min(...boxes.map((b) => b.x));
  const right = Math.max(...boxes.map((b) => b.x + b.w));
  return { x: (left + right) / 2, y: Math.min(...boxes.map((b) => b.y)) };
}
