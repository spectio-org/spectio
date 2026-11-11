// The workflow graph (issue #160; ui-spec §4.14): a toolbar (level, layout, colour, search, Map
// or List, export), the map drawn with React Flow, and the List, its table equivalent. Shared by
// the run's Graph tab and the Launch map. Every node is a native button whose name says its state;
// pipeline text is rendered as text only.
import { Drawer, NativeSelect, TextInput, useComputedColorScheme } from "@mantine/core";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
  type NodeHandle,
  type NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { type MutableRefObject, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ProcessStatus, Task } from "../../api";
import { ICONS, Icon } from "../../icons";
import { usePhone } from "../../shell/layout";
import { tone } from "../stateWord";
import { Code, type CodeSource } from "./Code";
import { download, svgToPng, toHtml, toSvg } from "./export";
import { hasUpstream, place } from "./layout";
import {
  type Flag,
  type NodeDiff,
  type View,
  type ViewEdge,
  type ViewNode,
  autoFold,
  bandOf,
  collapse,
  criticalPath,
  durationOf,
  heat,
  overlayValue,
  restrict,
  search,
  statusAt,
  toggled,
  topoOrder,
} from "./model";
import { type GraphSettings, LAYOUTS, LEVELS, OVERLAYS } from "./settings";
import { type GraphDocument, isEstimate } from "./types";
import "./graph.css";

const STATUS_WORDS: Record<ProcessStatus, string> = {
  pending: "Pending",
  running: "Running",
  done: "Done",
  failed: "Failed",
  stopped: "Stopped",
  awaiting_checkpoint: "Waiting for a checkpoint",
  not_needed: "Not needed in this run",
  up_to_date: "Up to date",
  no_tasks: "No task",
};
const KIND_WORDS: Record<string, string> = {
  process: "process",
  rule: "rule",
  checkpoint: "checkpoint",
  gate: "QC gate",
  stage: "stage",
  subworkflow: "subworkflow",
  job: "job",
};

/** The graph's light line icons (24 × 24 paths, as `ICONS`). */
export const GICONS = {
  process: "M7 7h10v10H7z M10 3v4 M14 3v4 M10 17v4 M14 17v4 M3 10h4 M3 14h4 M17 10h4 M17 14h4",
  rule: ICONS.fileCode,
  job: ICONS.tag,
  gate: ICONS.shield,
  stage: ICONS.layers,
  subworkflow: ICONS.folder,
  checkpoint: "M5 21V4 M5 4h11l-2 4 2 4H5",
  temp: "M7 3h10 M7 21h10 M8 3c0 5 8 5 8 9s-8 4-8 9 M16 3c0 5-8 5-8 9s8 4 8 9",
  conditional: "M6 3v12 M18 9a3 3 0 1 0 0-.01 M6 21a3 3 0 1 0 0-.01 M18 9c0 6-12 3-12 9",
  retried: ICONS.reload,
  cached: "M3 5h18v4H3z M5 9v11h14V9 M10 13h4",
  fold: "M6 12h12",
  unfold: "M12 6v12 M6 12h12",
  up: "M12 19V5 M5 12l7-7 7 7",
  down: "M12 5v14 M19 12l-7 7-7-7",
  channel: "M3 9h18v6H3z M8 9v6 M13 9v6 M18 9v6",
  file: ICONS.file,
  code: ICONS.braces,
  close: ICONS.cross,
  link: "M5 12h14 M13 6l6 6-6 6",
  peek: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  hide: "M3 3l18 18 M10.6 5.1A10 10 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 1-3.2 3.9 M6.6 6.6C3.9 8.4 2 12 2 12s4 7 10 7a9.6 9.6 0 0 0 5.4-1.6 M9.9 9.9a3 3 0 0 0 4.2 4.2",
  focus: "M12 3v3 M12 18v3 M3 12h3 M18 12h3 M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  fullscreen: "M4 9V4h5 M20 9V4h-5 M4 15v5h5 M20 15v5h-5",
  compact: "M4 7h16 M4 12h10 M4 17h6 M17 14l3 3-3 3",
  legend: ICONS.info,
  copy: ICONS.copy,
  image: ICONS.image,
  table: ICONS.table,
  reads: ICONS.dna,
  binary: "M6 3h9l4 4v14H6z M14 3v5h5 M9 12v4 M12.5 12h1.5v4 M9 18h.01",
  cpu: "M7 7h10v10H7z M10 10h4v4h-4z M10 3v4 M14 3v4 M10 17v4 M14 17v4 M3 10h4 M3 14h4 M17 10h4 M17 14h4",
  memory: "M3 8h18v8H3z M7 8v8 M11 8v8 M15 8v8 M6 16v3 M18 16v3",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
  params: ICONS.sliders,
  outputs: ICONS.download,
  jobs: ICONS.list,
} as const;

export const kindIcon = (kind: string): string => GICONS[kind as keyof typeof GICONS] ?? GICONS.process;

/** The marks of a step: a short visible mark, and the words its accessible name gets. */
export const FLAG_MARKS: Record<Flag, { mark: string; words: string }> = {
  checkpoint: { mark: "checkpoint", words: "checkpoint: the graph grows once it ends" },
  temp: { mark: "temp", words: "writes temporary files, removed once read" },
  conditional: { mark: "if", words: "runs only under a condition" },
  retried: { mark: "retried", words: "some jobs were retried" },
  cached: { mark: "cached", words: "some jobs reused from an earlier run" },
};

/** A mark: on the map a small round badge (its words are in the node's name), elsewhere a
 * tinted chip with its word. */
export function FlagChip({ flag, badge = false }: { flag: Flag; badge?: boolean }) {
  if (badge)
    return (
      <span className="sp-gbadge" data-flag={flag}>
        <Icon path={GICONS[flag]} size={10} stroke={2.2} />
      </span>
    );
  return (
    <span className="sp-gflag" data-flag={flag}>
      <span className="sp-gflag-dot">
        <Icon path={GICONS[flag]} size={10} stroke={2.2} />
      </span>
      {FLAG_MARKS[flag].mark}
    </span>
  );
}

export const statusWord = (s: ProcessStatus | null): string => (s ? STATUS_WORDS[s] ?? s : "Not run yet");
/** The colour family of a process status ("done" is the succeeded tone, stateWord.ts knows "Done"). */
export const statusTone = (s: ProcessStatus | null): string => (s === "done" ? "succeeded" : tone(s ?? "pending"));
export const kindWord = (k: string): string => KIND_WORDS[k] ?? k;

/** Done and total jobs of a node's counts. */
export function progress(counts: Record<string, number>): { done: number; total: number } {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const done = (counts.succeeded ?? 0) + (counts.cached ?? 0) + (counts.stored ?? 0);
  return { done, total };
}

export function formatSeconds(s: number): string {
  if (s < 60) return `${Math.round(s)} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
  return `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min`;
}

function diffWord(d: NodeDiff | undefined): string | null {
  if (!d) return null;
  if (d.change === "added") return "new in this run";
  const parts: string[] = [];
  if (d.duration_delta !== null && Math.abs(d.duration_delta) >= 1)
    parts.push(`${d.duration_delta > 0 ? "+" : "−"}${formatSeconds(Math.abs(d.duration_delta))}`);
  if (d.reuse === "cached") parts.push("cached");
  if (d.reuse === "rerun") parts.push("re-run");
  if (d.reuse === "mixed") parts.push("partly cached");
  return parts.length ? parts.join(", ") : null;
}

/** A link's other end, with the code's conditions on it ("B (when params.x)"). */
export const linkText = (label: string, conditions: string[]): string => (conditions.length ? `${label} (when ${conditions.join(" or ")})` : label);

/** A node's links, both ways, with their conditions: the sheet's text for what the map draws. */
export function Links({ view, id, onEdge }: { view: View; id: string; onEdge?: (edge: ViewEdge) => void }) {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const after = view.edges.filter((e) => e.target === id);
  const feeds = view.edges.filter((e) => e.source === id);
  if (!after.length && !feeds.length) return <p className="sp-muted">No known link to another step.</p>;
  const list = (edges: typeof after, end: "source" | "target", what: string) =>
    edges.length > 0 && (
      <>
        <dt>{what}</dt>
        <dd>
          {edges.map((e, i) => {
            const text = linkText(byId.get(e[end])?.label ?? e[end], e.conditions);
            return (
              <span key={`${e.source}>${e.target}`}>
                {i > 0 && ", "}
                {onEdge ? (
                  <button type="button" className="sp-link-button" onClick={() => onEdge(e)} aria-label={`What flows: ${byId.get(e.source)?.label ?? e.source} to ${byId.get(e.target)?.label ?? e.target}`}>
                    {text}
                  </button>
                ) : (
                  text
                )}
              </span>
            );
          })}
        </dd>
      </>
    );
  return (
    <dl className="facts">
      {list(after, "source", "Runs after")}
      {list(feeds, "target", "Feeds")}
    </dl>
  );
}

/** What else changes how nodes look: the open node, a traced lineage, a diff, a replay time. */
export interface Decor {
  selected?: string | null;
  /** The open link's id: drawn like the open step's links. */
  edge?: string | null;
  lineage?: Set<string> | null;
  diff?: Map<string, NodeDiff> | null;
  replayAt?: number | null;
}

interface NodeData extends Record<string, unknown> {
  node: ViewNode;
  status: ProcessStatus | null;
  label: string;
  meta: string;
  aria: string;
  tone: string;
  heat: number | null;
  dim: boolean;
  crit: boolean;
  matched: boolean;
  /** The open step, or a step linked to the open step or link. */
  ring: "selected" | "near" | null;
  /** CPU and Memory: how well the request fits; Duration: the share of the run. */
  bar: { pct: number; band: string | null } | null;
  badge: string | null;
  horizontal: boolean;
  onOpen: (n: ViewNode) => void;
  onToggle: (group: string) => void;
  onCode: (n: ViewNode, x: number, y: number) => void;
  /** The name of the group the node folds into, or of the folded group it stands for. */
  groupName: string;
}

/** A step's two handles, where `NodeBox` draws them: in at the top (left), out at the bottom (right). */
function handlesOf(w: number, h: number, horizontal: boolean): NodeHandle[] {
  return horizontal
    ? [
        { type: "target", position: Position.Left, x: 0, y: h / 2, width: 1, height: 1 },
        { type: "source", position: Position.Right, x: w, y: h / 2, width: 1, height: 1 },
      ]
    : [
        { type: "target", position: Position.Top, x: w / 2, y: 0, width: 1, height: 1 },
        { type: "source", position: Position.Bottom, x: w / 2, y: h, width: 1, height: 1 },
      ];
}

function NodeBox({ data }: NodeProps<Node<NodeData>>) {
  const { node, horizontal } = data;
  const folded = node.kind === "stage" || node.kind === "subworkflow";
  const style = data.heat !== null ? { ["--sp-heat" as string]: `${Math.round(10 + data.heat * 80)}%` } : undefined;
  return (
    <div
      className="sp-gnode"
      data-tone={data.tone}
      data-kind={node.kind}
      data-dim={data.dim || undefined}
      data-crit={data.crit || undefined}
      data-match={data.matched || undefined}
      data-ring={data.ring ?? undefined}
      data-heat={data.heat !== null || undefined}
      data-band={data.bar?.band ?? undefined}
      style={style}
      onDoubleClick={node.group ? () => data.onToggle(node.group!) : undefined}
      onContextMenu={(e) => {
        e.preventDefault();
        data.onCode(node, e.clientX, e.clientY);
      }}
    >
      <Handle type="target" position={horizontal ? Position.Left : Position.Top} isConnectable={false} />
      <button type="button" className="sp-gnode-btn" data-gid={node.id} aria-label={data.aria} onClick={() => data.onOpen(node)}>
        {node.kind === "job" && node.step && <span className="sp-gnode-step">{node.step}</span>}
        <span className="sp-gnode-name">
          <span className="sp-gnode-kind">
            <Icon path={kindIcon(node.kind)} size={12} stroke={1.9} />
          </span>
          {data.label}
        </span>
        <span className="sp-gnode-meta">{data.meta}</span>
        {data.bar && (
          <span className="sp-gnode-bar" aria-hidden="true">
            <span style={{ width: `${Math.round(Math.min(1, data.bar.pct) * 100)}%` }} />
          </span>
        )}
      </button>
      {node.flags && node.flags.length > 0 && (
        <span className="sp-gbadges" aria-hidden="true">
          {node.flags.map((f) => (
            <FlagChip key={f} flag={f} badge />
          ))}
        </span>
      )}
      {data.badge && <span className="sp-gnode-badge">{data.badge}</span>}
      {node.group && (
        <button
          type="button"
          className="sp-gfold"
          onDoubleClick={(e) => e.stopPropagation()}
          data-folded={folded || undefined}
          onClick={() => data.onToggle(node.group!)}
          aria-label={folded ? `Unfold ${data.groupName}: show its ${node.members.length} steps` : `Fold ${data.groupName} into one box`}
        >
          <Icon path={folded ? GICONS.unfold : GICONS.fold} size={12} stroke={2.2} />
          {folded && <span>{node.members.length}</span>}
        </button>
      )}
      <Handle type="source" position={horizontal ? Position.Right : Position.Bottom} isConnectable={false} />
    </div>
  );
}

function LaneBox({ data }: NodeProps<Node<{ label: string; area: boolean }>>) {
  return (
    <div className="sp-glane" data-area={data.area || undefined} aria-hidden="true">
      <span>
        <Icon path={GICONS.subworkflow} size={12} stroke={1.9} />
        {data.label}
      </span>
    </div>
  );
}

const NODE_TYPES = { sp: NodeBox, lane: LaneBox };

interface Props {
  doc: GraphDocument;
  /** The run's or pipeline's name: the export's title and file name. */
  title: string;
  settings: GraphSettings;
  onSettings: (patch: Partial<GraphSettings>) => void;
  /** A run's graph: the colour overlays apply and the Jobs level is offered. */
  runtime?: boolean;
  jobs?: Record<string, Task[]>;
  decor?: Decor;
  onOpen: (node: ViewNode) => void;
  /** More controls for the toolbar (Compare, Replay). */
  extra?: ReactNode;
  /** Where the pipeline's code is read (right-click on a step, and the sheets). */
  source?: CodeSource | null;
  /** A link was clicked on the map: what flows along it. */
  onEdge?: (edge: ViewEdge) => void;
  /** Shown above the map (notes on the producer, the jobs shown). */
  notes?: ReactNode;
  /** Docked beside the map: the open step's or link's details (not on phones, which use sheets). */
  side?: ReactNode;
}

interface Shown {
  view: View;
  status: Map<string, ProcessStatus | null>;
  matches: Set<string>;
  crit: { nodes: Set<string>; edges: Set<string> } | null;
  heat: Map<string, number>;
}

/** The view the map, the list and the details panel show: the level, the folds, then the
 * focused group and the hidden steps. */
export function viewOf(doc: GraphDocument, settings: GraphSettings, jobs?: Record<string, Task[]>): View {
  return restrict(doc, collapse(doc, settings.level, jobs, settings.fold), settings.focus, settings.hide);
}

function useShown(doc: GraphDocument, settings: GraphSettings, jobs: Record<string, Task[]> | undefined, decor: Decor, runtime: boolean): Shown {
  const view = useMemo(() => viewOf(doc, settings, jobs), [doc, settings.level, jobs, settings.fold, settings.focus, settings.hide]); // eslint-disable-line react-hooks/exhaustive-deps
  const matches = useMemo(() => search(doc, view, settings.q), [doc, view, settings.q]);
  const overlay = runtime ? settings.overlay : "state";
  const crit = useMemo(() => (overlay === "critical" ? criticalPath(view) : null), [view, overlay]);
  const heated = useMemo(() => (overlay === "state" || overlay === "critical" ? new Map<string, number>() : heat(view, overlay)), [view, overlay]);
  const status = useMemo(() => {
    const out = new Map<string, ProcessStatus | null>();
    for (const n of view.nodes) out.set(n.id, decor.replayAt != null && n.kind !== "job" ? statusAt(n, decor.replayAt) : n.status);
    return out;
  }, [view, decor.replayAt]);
  return { view, status, matches, crit, heat: heated };
}

function ariaOf(n: ViewNode, status: ProcessStatus | null, extra: string[]): string {
  const { done, total } = progress(n.counts);
  const parts = [n.label, kindWord(n.kind), statusWord(status)];
  if (n.kind !== "job" && total > 0) parts.push(`${done} of ${total} jobs done`);
  for (const f of n.flags ?? []) parts.push(FLAG_MARKS[f].words);
  return [...parts, ...extra].join(", ");
}

function Map_({ settings, decor, shown, onOpen, onToggle, onCode, onEdge, title, nextRef, engine, groupNames }: { engine: string; groupNames: Map<string, string>; settings: GraphSettings; decor: Decor; shown: Shown; onOpen: (n: ViewNode) => void; onToggle: (group: string) => void; onCode: (n: ViewNode, x: number, y: number) => void; onEdge?: (e: ViewEdge) => void; title: string; nextRef: MutableRefObject<(() => void) | null> }) {
  const dark = useComputedColorScheme("light") === "dark";
  const { view, status, matches, crit, heat: heated } = shown;
  const layout = settings.layout === "upstream" && !hasUpstream(view) ? "layered-tb" : settings.layout;
  const placed = useMemo(() => place(view, layout), [view, layout]);
  const horizontal = layout !== "layered-tb" && layout !== "upstream";
  const searching = settings.q.trim() !== "";
  const flow = useReactFlow();
  const wrap = useRef<HTMLDivElement>(null);
  const [cursor, setCursor] = useState(0);

  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const width = Math.max(0, ...[...placed.boxes.values()].map((b) => b.x + b.w)) + 40;
    for (const lane of placed.lanes) {
      nodes.push({ id: `lane:${lane.id}`, type: "lane", position: { x: lane.x ?? 0, y: lane.y }, data: { label: lane.label, area: lane.x !== undefined }, width: lane.w ?? width, height: lane.h, selectable: false, draggable: false, focusable: false, zIndex: -1 });
    }
    // what the open step or link lights up: itself, its links and the steps at their other end
    const lit = new Set<string>();
    const litEdges = new Set<string>();
    const openEdge = decor.edge ? view.edges.find((e) => e.id === decor.edge) : undefined;
    if (openEdge) {
      lit.add(openEdge.source).add(openEdge.target);
      litEdges.add(openEdge.id);
    } else if (decor.selected) {
      lit.add(decor.selected);
      for (const e of view.edges)
        if (e.source === decor.selected || e.target === decor.selected) {
          lit.add(e.source).add(e.target);
          litEdges.add(e.id);
        }
    }
    const spotlight = lit.size > 0 && !decor.lineage && !searching;
    const longest = Math.max(0, ...view.nodes.map((n) => durationOf(n)));
    const make = (n: ViewNode): Node<NodeData> => {
      const box = placed.boxes.get(n.id)!;
      const s = status.get(n.id) ?? null;
      const matched = matches.has(n.id);
      const inCrit = crit?.nodes.has(n.id) ?? false;
      const lineageOut = decor.lineage ? !decor.lineage.has(n.id) : false;
      const badge = diffWord(decor.diff?.get(n.id));
      const { done, total } = progress(n.counts);
      const extra: string[] = [];
      if (matched && searching) extra.push("matches the search");
      if (inCrit) extra.push("on the critical path");
      if (badge) extra.push(badge);
      const v = overlayValue(n, settings.overlay);
      const bar = barOf(settings.overlay, v, longest);
      const semantic = settings.overlay === "cpu" || settings.overlay === "memory";
      const h = semantic ? undefined : heated.get(n.id);
      const value = overlayText(n, settings.overlay);
      const metric = value ? ` · ${value}` : "";
      const ring = decor.selected === n.id || (openEdge && lit.has(n.id)) ? "selected" : spotlight && lit.has(n.id) ? "near" : null;
      return {
        id: n.id,
        type: "sp",
        position: { x: box.x, y: box.y },
        width: box.w,
        height: box.h,
        draggable: false,
        selectable: false,
        focusable: false,
        // React Flow sets `pointer-events: none` on a node that is neither selectable nor draggable
        // and has no handler of its own, so its button never got a click (found with the demo)
        style: { pointerEvents: "all" },
        // Handles given rather than measured: React Flow drops the measured ones whenever a node
        // object changes, and at the Jobs level they were not measured again, so no edge was drawn
        handles: handlesOf(box.w, box.h, horizontal),
        zIndex: ring ? 2 : 0,
        data: {
          node: n,
          status: s,
          label: n.label,
          meta: `${statusWord(s)}${total > 0 && n.kind !== "job" ? ` · ${done}/${total}` : ""}${metric}`,
          aria: ariaOf(n, s, extra),
          tone: n.kind === "gate" && !s ? "review" : statusTone(s),
          heat: h ?? null,
          dim: (searching && !matched) || lineageOut || (spotlight && !lit.has(n.id)),
          crit: inCrit,
          matched: matched && searching,
          ring,
          bar,
          badge,
          horizontal,
          onOpen,
          onToggle,
          onCode,
          groupName: n.group ? groupNames.get(n.group) ?? n.group.replace(/^(stage|sub|file):/, "") : "",
        },
      };
    };
    for (const n of view.nodes) nodes.push(make(n));
    const word = engine === "snakemake" ? "files" : "channel";
    const edges: Edge[] = view.edges.map((e) => {
      const onCrit = crit?.edges.has(e.id) ?? false;
      const near = litEdges.has(e.id);
      const dim = (searching && !(matches.has(e.source) && matches.has(e.target))) || (decor.lineage ? !(decor.lineage.has(e.source) && decor.lineage.has(e.target)) : false) || (spotlight && !near);
      const cond = e.conditions.length > 0;
      return {
        label: near ? (cond ? `${word} · if` : word) : cond ? "if" : undefined,
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
        id: e.id,
        source: e.source,
        target: e.target,
        type: layout === "metro" || layout === "compact" ? "smoothstep" : "default",
        focusable: false,
        className: [onCrit && "sp-gedge-crit", dim && "sp-gedge-dim", near && "sp-gedge-near", cond && "sp-gedge-if"].filter(Boolean).join(" ") || undefined,
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: near ? "var(--sp-accent)" : onCrit ? "var(--sp-state-review)" : "var(--sp-text-faint)" },
        animated: !near && status.get(e.target) === "running" && !dim,
        zIndex: near ? 1 : 0,
        interactionWidth: 14,
        data: { edge: e },
      };
    });
    return { nodes, edges };
  }, [view, placed, status, matches, crit, heated, decor, searching, horizontal, layout, onOpen, onToggle, onCode, settings.overlay, engine, groupNames]);

  // the opened step stays in view when the details panel narrows the map: checked once the
  // map has its new width and a double-click is over, and moved only when it is out of view
  const selected = decor.selected ?? null;
  useEffect(() => {
    const timer = setTimeout(() => {
      const b = selected ? placed.boxes.get(selected) : undefined;
      const r = wrap.current?.getBoundingClientRect();
      if (!b || !r) return;
      const a = flow.flowToScreenPosition({ x: b.x, y: b.y });
      const z = flow.flowToScreenPosition({ x: b.x + b.w, y: b.y + b.h });
      if (a.x < r.left || z.x > r.right || a.y < r.top || z.y > r.bottom) void flow.setCenter(b.x + b.w / 2, b.y + b.h / 2, { zoom: flow.getZoom(), duration: 200 });
    }, 400);
    return () => clearTimeout(timer);
  }, [selected]); // on a new selection only, not on every layout

  // a new level, layout, fold, focus or hidden set: fit the new drawing (React Flow fits only once)
  const shape = `${settings.level}|${layout}|${settings.fold.join()}|${settings.focus}|${settings.hide.join()}`;
  const first = useRef(true);
  useEffect(() => {
    if (first.current) return void (first.current = false);
    const timer = setTimeout(() => void flow.fitView({ duration: 200 }), 60);
    return () => clearTimeout(timer);
  }, [shape]); // eslint-disable-line react-hooks/exhaustive-deps

  // Enter in the search box: the next match, centred and focused
  const order = useMemo(() => topoOrder(view).filter((id) => matches.has(id)), [view, matches]);
  const next = () => {
    if (order.length === 0) return;
    const id = order[cursor % order.length];
    setCursor((c) => c + 1);
    const b = placed.boxes.get(id);
    if (b) void flow.setCenter(b.x + b.w / 2, b.y + b.h / 2, { zoom: 1.1, duration: 300 });
    wrap.current?.querySelector<HTMLButtonElement>(`[data-gid="${CSS.escape(id)}"]`)?.focus({ preventScroll: true });
  };
  nextRef.current = next;

  return (
    <div className="sp-graph-map" ref={wrap} data-searching={searching || undefined} aria-label={`Map of ${title}`} role="group">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        colorMode={dark ? "dark" : "light"}
        fitView
        minZoom={0.1}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        zoomOnDoubleClick={false}
        onEdgeClick={onEdge ? (_, edge) => onEdge((edge.data as { edge: ViewEdge }).edge) : undefined}
        onlyRenderVisibleElements={view.nodes.length > 300}
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} aria-label="Zoom" />
        <MiniMap
          pannable
          zoomable
          ariaLabel="Minimap"
          nodeColor={(n) => (n.type === "lane" ? "transparent" : `var(--sp-state-${(n.data as NodeData).tone})`)}
        />
      </ReactFlow>
    </div>
  );
}

function List({ shown, settings, onOpen, decor }: { shown: Shown; settings: GraphSettings; onOpen: (n: ViewNode) => void; decor: Decor }) {
  const { view, status, matches, crit } = shown;
  const order = topoOrder(view);
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const rows = order.map((id) => byId.get(id)!).filter((n) => !settings.q.trim() || matches.has(n.id)).filter((n) => !decor.lineage || decor.lineage.has(n.id));
  if (rows.length === 0) return <p className="sp-empty">Nothing in the graph matches “{settings.q}”.</p>;
  return (
    <div className="sp-table-wrap">
      <table className="sp-table" aria-label="Graph as a list">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Kind</th>
            <th scope="col">Group</th>
            <th scope="col">State</th>
            <th scope="col">Jobs</th>
            <th scope="col">Duration</th>
            <th scope="col">Runs after</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((n) => {
            const s = status.get(n.id) ?? null;
            const { done, total } = progress(n.counts);
            const after = view.edges.filter((e) => e.target === n.id).map((e) => linkText(byId.get(e.source)?.label ?? e.source, e.conditions));
            const badge = diffWord(decor.diff?.get(n.id));
            return (
              <tr key={n.id} data-selected={decor.selected === n.id || undefined}>
                <td>
                  <button type="button" className="sp-link-button" aria-label={`Open ${kindWord(n.kind)} ${n.label}`} onClick={() => onOpen(n)}>
                    {n.label}
                  </button>
                  {crit?.nodes.has(n.id) && <span className="sp-gtag">critical path</span>}
                  {badge && <span className="sp-gtag">{badge}</span>}
                </td>
                <td>{kindWord(n.kind)}</td>
                <td>{n.laneLabel ?? "—"}</td>
                <td>
                  <span className="sp-state" data-tone={statusTone(s)}>
                    {statusWord(s)}
                  </span>
                </td>
                <td>{total ? `${done} of ${total}` : "—"}</td>
                <td>{durationOf(n) ? formatSeconds(durationOf(n)) : "—"}</td>
                <td>{after.length ? after.join(", ") : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** What each colour mode measures and where the value comes from (shown under the toolbar). */
export const OVERLAY_HELP: Record<GraphSettings["overlay"], string> = {
  state: "Colour = the step's state, from its jobs: failed wins, then running; all jobs done is done.",
  duration: "Duration = wall time of the step, from its first job's start to its last job's end (summed for a folded group).",
  cpu: "CPU = CPU efficiency: CPU time used over the CPUs asked for, averaged over the step's jobs (from sacct, else the engine's trace).",
  memory: "Memory = memory efficiency: peak memory over the memory asked for, of the step's highest job.",
  failures: "Failures = failed attempts of the step's jobs, retried ones included.",
  critical: "Critical path = the chain of linked steps with the longest total duration: it sets the run's shortest possible time.",
};

const STATE_KEY: [string, string][] = [
  ["succeeded", "Done"],
  ["running", "Running"],
  ["failed", "Failed"],
  ["queued", "Pending"],
  ["cached", "Cached or up to date"],
  ["review", "Waiting for a checkpoint or gate"],
];

/** A node's value in a colour mode, as text ("12 min 3 s", "84 %", "2 failed"). */
export function overlayText(n: ViewNode, overlay: GraphSettings["overlay"]): string | null {
  const v = overlayValue(n, overlay);
  if (v === null) return null;
  if (overlay === "duration") return formatSeconds(v);
  if (overlay === "cpu" || overlay === "memory") return `${Math.round(v * 100)} %`;
  if (overlay === "failures") return `${v} failed`;
  return null;
}

/** The small bar under a step: CPU and Memory efficiency against its band, Duration against the
 * longest step. */
function barOf(overlay: GraphSettings["overlay"], v: number | null, longest: number): NodeData["bar"] {
  if (v === null) return null;
  if (overlay === "cpu" || overlay === "memory") return { pct: v, band: bandOf(v) };
  if (overlay === "duration" && longest > 0) return { pct: v / longest, band: null };
  return null;
}

/** What each efficiency band means, for the legend and the details panel. */
export const BAND_WORDS: Record<string, string> = {
  low: "under 30 %: far more asked than used",
  fair: "30 to 70 %",
  good: "70 to 105 %: well sized",
  over: "over 105 %: more used than asked",
};

/** The legend: one line always shown (the colour key), the rest behind a toggle so it does not
 * push the map down. */
function Legend({ overlay, view }: { overlay: GraphSettings["overlay"]; view: View }) {
  const [open, setOpen] = useState(false);
  const semantic = overlay === "cpu" || overlay === "memory";
  const texts = view.nodes.map((n) => [overlayValue(n, overlay), overlayText(n, overlay)] as const).filter(([v]) => v !== null) as [number, string][];
  const low = texts.length ? texts.reduce((a, b) => (b[0] < a[0] ? b : a)) : null;
  const high = texts.length ? texts.reduce((a, b) => (b[0] > a[0] ? b : a)) : null;
  const key =
    overlay === "state" || overlay === "critical" ? (
      <ul className="sp-gkey">
        {STATE_KEY.map(([t, label]) => (
          <li key={t}>
            <span className="sp-gswatch" data-tone={t} aria-hidden="true" /> {label}
          </li>
        ))}
        {overlay === "critical" && (
          <li>
            <span className="sp-gswatch" data-crit aria-hidden="true" /> On the critical path
          </li>
        )}
      </ul>
    ) : semantic ? (
      <ul className="sp-gkey" aria-label="Efficiency bands">
        {(["low", "fair", "good", "over"] as const).map((b) => (
          <li key={b}>
            <span className="sp-gswatch" data-band={b} aria-hidden="true" /> {BAND_WORDS[b]}
          </li>
        ))}
      </ul>
    ) : high ? (
      <span className="sp-gkey">
        {low![1]} <span className="sp-gramp" aria-hidden="true" /> {high[1]}
      </span>
    ) : (
      <span className="sp-gkey">No step has a value yet: steps keep their state colour.</span>
    );
  return (
    <div className="sp-glegend" role="note" aria-label="Legend">
      <div className="sp-glegend-row">
        <button type="button" className="sp-glegend-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          <Icon path={GICONS.legend} size={14} stroke={1.9} />
          Legend
          <Icon path={open ? ICONS.chevronDown : ICONS.chevronRight} size={12} stroke={2} />
        </button>
        {key}
      </div>
      {open && (
        <div className="sp-glegend-more">
          <p className="sp-glegend-help">{OVERLAY_HELP[overlay]}</p>
          <ul className="sp-gkey sp-gkey-grid" aria-label="Marks">
            {(Object.keys(FLAG_MARKS) as Flag[]).map((f) => (
              <li key={f}>
                <FlagChip flag={f} /> {FLAG_MARKS[f].words}
              </li>
            ))}
          </ul>
          <ul className="sp-gkey sp-gkey-grid" aria-label="Links and boxes">
            <li>
              <svg width="34" height="10" aria-hidden="true">
                <path d="M2 5h26" className="sp-gkey-edge" />
                <path d="M26 1l6 4-6 4z" className="sp-gkey-arrow" />
              </svg>
              a link: what the upstream step writes, the downstream step reads
            </li>
            <li>
              <svg width="34" height="10" aria-hidden="true">
                <path d="M2 5h26" className="sp-gkey-edge" strokeDasharray="4 3" />
                <path d="M26 1l6 4-6 4z" className="sp-gkey-arrow" />
              </svg>
              a link under a condition (“if”)
            </li>
            <li>
              <span className="sp-gfold sp-gfold-key" aria-hidden="true">
                <Icon path={GICONS.fold} size={12} stroke={2.2} />
              </span>
              fold a group into one box;{" "}
              <span className="sp-gfold sp-gfold-key" data-folded aria-hidden="true">
                <Icon path={GICONS.unfold} size={12} stroke={2.2} />
                <span>4</span>
              </span>{" "}
              unfold it (or double-click)
            </li>
            <li>
              <span className="sp-gswatch" data-ring aria-hidden="true" /> the open step and the steps it is linked to
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}

/** What each layout does, under the toolbar, so Metro and Compact are not a guess. */
export const LAYOUT_HELP: Record<GraphSettings["layout"], string> = {
  "layered-tb": "Steps in layers, top to bottom: each step below the steps it reads from.",
  "layered-lr": "Steps in layers, left to right: each step right of the steps it reads from.",
  metro: "Left to right, each subworkflow or stage drawn as an area around its steps, so a group's steps stay together.",
  compact: "Each subworkflow or stage as a small grid in pipeline order, the groups packed side by side: the most steps on one screen, links drawn without layers.",
  upstream: "Positions BioFlow-Insight computed from the code (Launch only).",
};

function Toolbar({ settings, onSettings, runtime, upstream, onNext, matches, onExport, extra, onCompact, onFullscreen, full }: {
  settings: GraphSettings;
  onSettings: (p: Partial<GraphSettings>) => void;
  runtime: boolean;
  upstream: boolean;
  onNext: () => void;
  matches: number;
  onExport: (kind: "svg" | "png" | "html" | "copy") => void;
  extra?: ReactNode;
  onCompact: (() => void) | null;
  onFullscreen: () => void;
  full: boolean;
}) {
  const levels = runtime ? LEVELS : LEVELS.filter((l) => l.value !== "jobs");
  return (
    <div className="sp-gtoolbar" role="toolbar" aria-label="Graph view">
      <NativeSelect size="xs" label="Show" value={settings.level} onChange={(e) => onSettings({ level: e.currentTarget.value as GraphSettings["level"], fold: [] })} data={levels} />
      <NativeSelect
        size="xs"
        label="Layout"
        value={settings.layout}
        onChange={(e) => onSettings({ layout: e.currentTarget.value as GraphSettings["layout"] })}
        data={LAYOUTS.map((l) => ({ ...l, disabled: l.value === "upstream" && !upstream }))}
        disabled={settings.show === "list"}
      />
      {runtime && (
        <NativeSelect size="xs" label="Colour by" value={settings.overlay} onChange={(e) => onSettings({ overlay: e.currentTarget.value as GraphSettings["overlay"] })} data={OVERLAYS} />
      )}
      <TextInput
        size="xs"
        label="Search"
        placeholder="name, state:failed, param:genome, file:…"
        value={settings.q}
        onChange={(e) => onSettings({ q: e.currentTarget.value })}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onNext();
          } else if (e.key === "Escape" && settings.q) {
            e.preventDefault();
            onSettings({ q: "" });
          }
        }}
        description={settings.q.trim() ? `${matches} ${matches === 1 ? "match" : "matches"}${matches > 0 && settings.show === "map" ? ", Enter for the next, Escape to clear" : ""}` : undefined}
        inputWrapperOrder={["label", "input", "description"]}
        leftSection={<Icon path={ICONS.search} size={13} />}
        className="sp-gsearch"
      />
      <div className="sp-gview" role="group" aria-label="View as">
        {(["map", "list"] as const).map((v) => (
          <button key={v} type="button" className="sp-gbtn" aria-pressed={settings.show === v} onClick={() => onSettings({ show: v })}>
            {v === "map" ? "Map" : "List"}
          </button>
        ))}
      </div>
      <div className="sp-gview" role="group" aria-label="Fold">
        <button type="button" className="sp-gbtn" onClick={onCompact ?? undefined} disabled={!onCompact}>
          <Icon path={GICONS.compact} size={13} stroke={2} /> Auto-fold
        </button>
        <button type="button" className="sp-gbtn" onClick={() => onSettings({ fold: [] })} disabled={settings.fold.length === 0}>
          <Icon path={GICONS.unfold} size={13} stroke={2} /> {settings.level === "subworkflow" || settings.level === "stage" ? "Fold all" : "Unfold all"}
        </button>
      </div>
      {extra}
      <div className="sp-gview" role="group" aria-label="Export">
        <button type="button" className="sp-gbtn" onClick={() => onExport("svg")}>
          <Icon path={ICONS.download} size={13} /> SVG
        </button>
        <button type="button" className="sp-gbtn" onClick={() => onExport("png")}>
          <Icon path={ICONS.download} size={13} /> PNG
        </button>
        <button type="button" className="sp-gbtn" onClick={() => onExport("html")}>
          <Icon path={ICONS.download} size={13} /> HTML
        </button>
        <button type="button" className="sp-gbtn" onClick={() => onExport("copy")}>
          <Icon path={GICONS.copy} size={13} /> Copy PNG
        </button>
      </div>
      <button type="button" className="sp-gbtn sp-gbtn-line" aria-pressed={full} onClick={onFullscreen}>
        <Icon path={GICONS.fullscreen} size={13} stroke={2} /> {full ? "Exit full screen" : "Full screen"}
      </button>
    </div>
  );
}

/** At most this many boxes after Auto-fold. */
const AUTO_FOLD_MAX = 24;

function Inner({ doc, title, settings, onSettings, runtime = false, jobs, decor = {}, onOpen, onEdge, source, extra, notes, side }: Props) {
  const groupNames = useMemo(() => new Map(doc.groups.map((g) => [g.id, g.name])), [doc.groups]);
  const shown = useShown(doc, settings, jobs, decor, runtime);
  const [exportError, setExportError] = useState<string | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const layout = settings.layout === "upstream" && !hasUpstream(shown.view) ? "layered-tb" : settings.layout;
  const onExport = (kind: "svg" | "png" | "html" | "copy") => {
    const placed = place(shown.view, layout);
    const svg = toSvg(shown.view, placed, title);
    const name = `${title.replace(/[^\w.-]+/g, "_")}-graph.${kind}`;
    setExportError(null);
    setSaid(null);
    if (kind === "svg") download(name, new Blob([svg], { type: "image/svg+xml" }));
    else if (kind === "html") download(name, new Blob([toHtml(shown.view, placed, title, doc.engine)], { type: "text/html" }));
    else if (kind === "copy")
      svgToPng(svg)
        .then((b) => navigator.clipboard.write([new ClipboardItem({ "image/png": b })]))
        .then(
          () => setSaid("The map is copied as a PNG."),
          () => setExportError("The PNG could not be copied: this browser refused the clipboard. Use the PNG button instead."),
        );
    else svgToPng(svg).then((b) => download(name, b), (e: Error) => setExportError(`The PNG could not be made: ${e.message}`));
  };
  const nextRef = useRef<(() => void) | null>(null);
  const onToggle = useCallback(
    (group: string) => onSettings({ fold: toggled(settings.fold, group) }),
    [onSettings, settings.fold],
  );
  const [pop, setPop] = useState<{ node: ViewNode; x: number; y: number } | null>(null);
  const onCode = useCallback((node: ViewNode, x: number, y: number) => setPop({ node, x, y }), []);
  const closePop = useCallback(() => setPop(null), []);
  const root = useRef<HTMLDivElement>(null);
  const [full, setFull] = useState(false);
  useEffect(() => {
    const on = () => setFull(document.fullscreenElement === root.current && root.current !== null);
    document.addEventListener("fullscreenchange", on);
    return () => document.removeEventListener("fullscreenchange", on);
  }, []);
  const onFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else root.current?.requestFullscreen?.().catch(() => setExportError("Full screen was refused by the browser."));
  };
  const foldable = settings.level === "process" || settings.level === "jobs";
  // about half as many boxes, and at most AUTO_FOLD_MAX
  const auto = foldable ? autoFold(shown.view, Math.min(AUTO_FOLD_MAX, Math.ceil(shown.view.nodes.length / 2))) : [];
  // Escape leaves the focused group, unless something on top (a card, the panel) took it
  const focus = settings.focus;
  useEffect(() => {
    if (!focus) return;
    const key = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented || document.querySelector(".sp-ginspect")) return;
      onSettings({ focus: null });
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [focus, onSettings]);
  return (
    <div className="sp-graph" ref={root} data-full={full || undefined}>
      {pop && <CodePop doc={doc} pop={pop} source={source ?? null} onClose={closePop} />}
      <Toolbar
        settings={settings}
        onSettings={onSettings}
        runtime={runtime}
        upstream={hasUpstream(shown.view)}
        onNext={() => nextRef.current?.()}
        matches={shown.matches.size}
        onExport={onExport}
        extra={extra}
        onCompact={auto.length ? () => onSettings({ fold: [...settings.fold, ...auto] }) : null}
        onFullscreen={onFullscreen}
        full={full}
      />
      {exportError && <p role="alert">{exportError}</p>}
      <p role="status" className="sp-gnote">
        {said}
      </p>
      {settings.show === "map" && <p className="sp-gnote sp-glayout-help">{LAYOUT_HELP[layout]}</p>}
      {isEstimate(doc) && (
        <p className="sp-gbanner" role="note">
          Static estimate from the code: links may be approximate, and loops in the code are drawn with one link set aside.
        </p>
      )}
      {settings.focus && (
        <p className="sp-gbanner sp-gbanner-focus" role="note">
          <Icon path={GICONS.focus} size={14} stroke={2} /> Only {groupNames.get(settings.focus) ?? settings.focus.replace(/^(stage|sub):/, "")} is shown.{" "}
          <button type="button" className="sp-link-button" onClick={() => onSettings({ focus: null })}>
            Show everything (Escape)
          </button>
        </p>
      )}
      {settings.hide.length > 0 && (
        <p className="sp-gbanner sp-gbanner-focus" role="note">
          <Icon path={GICONS.hide} size={14} stroke={2} /> {settings.hide.length} {settings.hide.length === 1 ? "step is" : "steps are"} hidden ({settings.hide.map((h) => doc.nodes.find((n) => n.id === h)?.name ?? h).join(", ")}); the links through {settings.hide.length === 1 ? "it" : "them"} are kept.{" "}
          <button type="button" className="sp-link-button" onClick={() => onSettings({ hide: settings.hide.slice(0, -1) })}>
            Undo the last
          </button>
          {" · "}
          <button type="button" className="sp-link-button" onClick={() => onSettings({ hide: [] })}>
            Show all
          </button>
        </p>
      )}
      {notes}
      {runtime && settings.show === "map" && <Legend overlay={settings.overlay} view={shown.view} />}
      <div className="sp-gbody" data-side={side ? true : undefined}>
        {settings.show === "map" ? (
          <Map_ nextRef={nextRef} settings={settings} decor={decor} shown={shown} onOpen={onOpen} onToggle={onToggle} onCode={onCode} onEdge={onEdge} title={title} engine={doc.engine} groupNames={groupNames} />
        ) : (
          <List shown={shown} settings={settings} onOpen={onOpen} decor={decor} />
        )}
        {side}
      </div>
    </div>
  );
}

/** The right-click card: a step's code by the cursor (MetroFlow's code tooltip). Escape or the
 * close button ends it, and focus moves into it so the keyboard can scroll the code. */
function CodePop({ doc, pop, source, onClose }: { doc: GraphDocument; pop: { node: ViewNode; x: number; y: number }; source: CodeSource | null; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = pop.node.members[0];
  const docNode = doc.nodes.find((n) => n.id === id);
  const single = pop.node.members.length === 1;
  const nodeId = pop.node.id;
  useEffect(() => {
    ref.current?.querySelector<HTMLButtonElement>("button")?.focus();
    // back to the node's button when the card closes
    return () => document.querySelector<HTMLElement>(`[data-gid="${CSS.escape(nodeId)}"]`)?.focus();
  }, [nodeId]);
  useEffect(() => {
    // first, in the capture phase, so the details panel under the card stays open
    const key = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      onClose();
    };
    document.addEventListener("keydown", key, true);
    return () => document.removeEventListener("keydown", key, true);
  }, [onClose]);
  const left = Math.max(12, Math.min(pop.x, window.innerWidth - 572));
  const top = Math.max(12, Math.min(pop.y, window.innerHeight - 320));
  return (
    <div ref={ref} className="sp-gcodepop" role="dialog" aria-label={`Code of ${pop.node.step ?? pop.node.label}`} style={{ left, top }}>
      <header>
        <span>{pop.node.step ?? pop.node.label}</span>
        <button type="button" className="sp-gbtn" onClick={onClose} aria-label="Close the code">
          ×
        </button>
      </header>
      {docNode?.condition && (
        <p>
          Runs when <code>{docNode.condition}</code>
        </p>
      )}
      {single ? <Code name={id} code={docNode?.code} where={source} /> : <p className="sp-muted">A group of {pop.node.members.length} steps: open it to see each step, or right-click one of them.</p>}
    </div>
  );
}

export function GraphView(props: Props) {
  return (
    <ReactFlowProvider>
      <Inner {...props} />
    </ReactFlowProvider>
  );
}

/** The details of a step or a link: docked beside the map, so the map stays in view and usable
 * (Escape or × closes it, and focus goes back to where it was); a sheet on a phone. */
export function Panel({ id, opened, title, icon, onClose, children, tone, kind }: { id: string | null; opened: boolean; title: string; icon: string; onClose: () => void; children: ReactNode; tone?: string; kind?: string }) {
  const phone = usePhone();
  const ref = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!opened || phone) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    ref.current?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
    const typing = (t: EventTarget | null) => t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement || (t instanceof HTMLElement && t.isContentEditable);
    const key = (e: KeyboardEvent) => e.key === "Escape" && !e.defaultPrevented && !typing(e.target) && close.current();
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      // back to the opener, unless the user already moved on (clicked another step)
      const at = document.activeElement;
      const lost = !at || at === document.body || !!ref.current?.contains(at);
      if (lost && opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [opened, phone, id]);
  if (phone)
    return (
      <Drawer opened={opened} onClose={onClose} position="right" size="100%" title={title} returnFocus closeButtonProps={{ "aria-label": "Close" }} classNames={{ title: "sp-sheet-title" }}>
        {children}
      </Drawer>
    );
  if (!opened) return null;
  return (
    <aside className="sp-ginspect" aria-label={kind ? `${title} (${kind})` : title} ref={ref}>
      <header>
        <span className="sp-ginspect-icon" data-tone={tone} aria-hidden="true">
          <Icon path={icon} size={16} stroke={1.8} />
        </span>
        <h2 tabIndex={-1}>
          {title}
          {kind && <small>{kind}</small>}
        </h2>
        <button type="button" className="sp-gicon" onClick={onClose} aria-label="Close">
          <Icon path={GICONS.close} size={16} stroke={2} />
        </button>
      </header>
      {children}
    </aside>
  );
}
