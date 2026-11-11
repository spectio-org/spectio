// The workflow graph (issue #160; ui-spec §4.14): a toolbar (level, layout, colour, search, Map
// or List, export), the map drawn with React Flow, and the List, its table equivalent. Shared by
// the run's Graph tab and the Launch map. Every node is a native button whose name says its state;
// pipeline text is rendered as text only.
import { Drawer, Menu, NativeSelect, TextInput, useComputedColorScheme } from "@mantine/core";
import {
  Background,
  ControlButton,
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
import { type MutableRefObject, type ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProcessStatus, Task } from "../../api";
import { ICONS, Icon } from "../../icons";
import { usePhone } from "../../shell/layout";
import { tone } from "../stateWord";
import { Code, type CodeSource } from "./Code";
import { download, svgToPng, toHtml, toSvg } from "./export";
import { groupBox, hasUpstream, place } from "./layout";
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
  OUTLIER,
  outliers,
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
  fit: "M4 9V4h5 M20 9V4h-5 M4 15v5h5 M20 15v5h-5 M9 9h6v6H9z",
  arrow: "M5 12h14 M13 6l6 6-6 6",
  warn: "M12 9v4 M12 17h.01 M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  tasks: ICONS.table,
  compact: "M4 7h16 M4 12h10 M4 17h6 M17 14l3 3-3 3",
  legend: ICONS.info,
  copy: ICONS.copy,
  open: ICONS.externalLink,
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
  checkpoint: { mark: "checkpoint", words: "checkpoint: the steps after it are known only once it ends, so the graph can grow" },
  temp: { mark: "temp", words: "temp: writes temporary files, deleted once every step that reads them has run" },
  conditional: { mark: "if", words: "if: runs only when a condition in the code holds; its panel gives the condition" },
  retried: { mark: "retried", words: "retried: a job failed and the engine ran it again; its panel lists each job's attempts" },
  cached: { mark: "cached", words: "cached: reused from an earlier run (resume or up to date), not run again" },
};

/** A mark: on the map a small round badge (its words are in the node's name), elsewhere a
 * tinted chip with its word. */
export function FlagChip({ flag, badge = false }: { flag: Flag; badge?: boolean }) {
  if (badge)
    return (
      <span className="sp-gbadge" data-flag={flag}>
        <Icon path={GICONS[flag]} size={10} stroke={2.2} />
        <span className="sp-gbadge-word">{FLAG_MARKS[flag].mark}</span>
        <span className="sp-gbadge-tip" role="tooltip">
          {FLAG_MARKS[flag].words}
        </span>
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
  /** A job's value over its step's median, when out of the norm. */
  odd: number | null;
  /** Hover or keyboard focus: the map shows the node's card above everything (null: hide it). */
  onTip: (id: string | null, at?: Element, now?: boolean) => void;
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
  /** Its group is drawn as an area whose title folds it: no fold button on the step. */
  areaFold?: boolean;
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
      data-odd={data.odd !== null || undefined}
      data-band={data.bar?.band ?? undefined}
      style={style}
      onMouseEnter={(e) => data.onTip(node.id, e.currentTarget)}
      onMouseLeave={() => data.onTip(null)}
      onDoubleClick={node.group ? () => data.onToggle(node.group!) : undefined}
      onContextMenu={(e) => {
        e.preventDefault();
        data.onCode(node, e.clientX, e.clientY);
      }}
    >
      <Handle type="target" position={horizontal ? Position.Left : Position.Top} isConnectable={false} />
      <button
        type="button"
        className="sp-gnode-btn"
        data-gid={node.id}
        aria-label={data.aria}
        onClick={() => data.onOpen(node)}
        onFocus={(e) => e.currentTarget.matches(":focus-visible") && data.onTip(node.id, e.currentTarget.parentElement ?? e.currentTarget, true)}
        onBlur={() => data.onTip(null)}
      >
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
      {node.group && (folded || !data.areaFold) && (
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

interface LaneData extends Record<string, unknown> {
  id: string;
  label: string;
  area: boolean;
  /** The group its fold button folds, when it is one. */
  fold: string | null;
  /** Its title opens the group's details, when the screen has them. */
  onGroup?: (group: string) => void;
  onToggle: (group: string) => void;
  onTip: (id: string | null, at?: Element, now?: boolean) => void;
  selected: boolean;
}

/** A group's band or area. Drawn as an area, its round button folds it (Thomas: folding belongs
 * to the subworkflow or stage, not to each step) and its name opens its details. */
function LaneBox({ data }: NodeProps<Node<LaneData>>) {
  const tipOn = (e: { currentTarget: Element }, now?: boolean) => data.onTip(`lane:${data.id}`, e.currentTarget, now);
  const tipOff = () => data.onTip(null);
  const name = (
    <>
      <Icon path={data.id.startsWith("stage:") ? GICONS.stage : GICONS.subworkflow} size={12} stroke={1.9} />
      {data.label}
    </>
  );
  return (
    <div className="sp-glane" data-area={data.area || undefined} data-selected={data.selected || undefined}>
      <span className="sp-glane-title">
        {data.fold && (
          <button type="button" className="sp-glane-fold-icon nodrag nopan" onClick={() => data.onToggle(data.fold!)} onDoubleClick={(e) => e.stopPropagation()} aria-label={`Fold ${data.label} into one box`}>
            <Icon path={GICONS.fold} size={11} stroke={2.4} />
          </button>
        )}
        {data.onGroup && data.fold ? (
          <button type="button" className="sp-glane-fold nodrag nopan" onClick={() => data.onGroup!(data.fold!)} onDoubleClick={(e) => e.stopPropagation()} onMouseEnter={tipOn} onMouseLeave={tipOff} onFocus={(e) => e.currentTarget.matches(":focus-visible") && tipOn(e, true)} onBlur={tipOff} aria-label={`Details of ${data.label}`}>
            {name}
          </button>
        ) : (
          <span className="sp-glane-name" aria-hidden="true" onMouseEnter={tipOn} onMouseLeave={tipOff}>
            {name}
          </span>
        )}
      </span>
    </div>
  );
}

const NODE_TYPES = { sp: NodeBox, lane: LaneBox };

/** What a card on the map shows: a step's, a group's or a link's facts, drawn (Thomas: coloured,
 * more graphic). The same facts are in the step's accessible name and in its panel. */
export interface TipInfo {
  icon: string;
  tone: string | null;
  title: string;
  sub: string;
  state?: string;
  /** A link's two ends. */
  ends?: { label: string; tone: string; icon: string }[];
  progress?: { done: number; total: number };
  /** States of a group's boxes, as coloured counts. */
  chips?: { tone: string; text: string }[];
  rows: { icon: string; k: string; v: string; bar?: { pct: number; band: string | null } | null; warn?: boolean }[];
  flags?: Flag[];
  hint: string;
}

function TipCard({ info, x, y, above, now }: { info: TipInfo; x: number; y: number; above: boolean; now?: boolean }) {
  return (
    <div className="sp-gtip" data-tone={info.tone ?? undefined} data-above={above || undefined} data-now={now || undefined} aria-hidden="true" style={{ left: x, top: y }}>
      <div className="sp-gtip-head">
        <span className="sp-gtip-icon">
          <Icon path={info.icon} size={14} stroke={1.9} />
        </span>
        <span className="sp-gtip-title">
          <strong>{info.title}</strong>
          <small>{info.sub}</small>
        </span>
        {info.state && <span className="sp-gtip-state">{info.state}</span>}
      </div>
      {info.ends && (
        <div className="sp-gtip-ends">
          {info.ends.map((e, i) => (
            <span key={i} style={{ display: "contents" }}>
              {i > 0 && <Icon path={GICONS.arrow} size={14} stroke={2} />}
              <span className="sp-gtip-end" data-tone={e.tone}>
                <Icon path={e.icon} size={11} stroke={2} />
                {e.label}
              </span>
            </span>
          ))}
        </div>
      )}
      {info.progress && info.progress.total > 0 && (
        <div className="sp-gtip-prog">
          <span className="sp-gtip-progbar">
            <span style={{ width: `${Math.round((info.progress.done / info.progress.total) * 100)}%` }} />
          </span>
          {info.progress.done}/{info.progress.total} jobs
        </div>
      )}
      {info.chips && info.chips.length > 0 && (
        <div className="sp-gtip-chips">
          {info.chips.map((c) => (
            <span key={c.text} className="sp-gtip-chip" data-tone={c.tone}>
              {c.text}
            </span>
          ))}
        </div>
      )}
      {info.rows.length > 0 && (
        <dl>
          {info.rows.map((r) => (
            <div key={r.k} data-warn={r.warn || undefined}>
              <dt>
                <Icon path={r.icon} size={12} stroke={1.9} />
                {r.k}
              </dt>
              <dd>
                {r.v}
                {r.bar && (
                  <span className="sp-gtip-bar" data-band={r.bar.band ?? undefined}>
                    <span style={{ width: `${Math.round(Math.min(1, r.bar.pct) * 100)}%` }} />
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {info.flags && info.flags.length > 0 && (
        <div className="sp-gtip-chips">
          {info.flags.map((f) => (
            <FlagChip key={f} flag={f} />
          ))}
        </div>
      )}
      <span className="sp-gtip-hint">{info.hint}</span>
    </div>
  );
}

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
  /** Back to the plain map: nothing open, nothing traced (Escape, or a click on the empty map). */
  onReset?: () => void;
  /** A group's name on the map was clicked: its details (subworkflow or stage). */
  onGroup?: (group: string) => void;
  /** Shown above the map and kept in view: what narrows the map (a traced lineage). */
  banner?: ReactNode;
}

interface Shown {
  view: View;
  status: Map<string, ProcessStatus | null>;
  matches: Set<string>;
  crit: { nodes: Set<string>; edges: Set<string> } | null;
  heat: Map<string, number>;
  /** Jobs out of their step's norm under the colour mode: value over the step's median. */
  odd: Map<string, number>;
}

/** The view the map, the list and the details panel show: the level, the folds, then the
 * focused group and the hidden steps. */
/** Whether a key went to a field the user types in. */
const typing = (t: EventTarget | null) => t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement || (t instanceof HTMLElement && t.isContentEditable);

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
  const odd = useMemo(() => outliers(view, overlay), [view, overlay]);
  return { view, status, matches, crit, heat: heated, odd };
}

function ariaOf(n: ViewNode, status: ProcessStatus | null, extra: string[]): string {
  const { done, total } = progress(n.counts);
  const parts = [n.label, kindWord(n.kind), statusWord(status)];
  if (n.kind !== "job" && total > 0) parts.push(`${done} of ${total} jobs done`);
  for (const f of n.flags ?? []) parts.push(FLAG_MARKS[f].words);
  return [...parts, ...extra].join(", ");
}


function Map_({ settings, decor, shown, onOpen, onToggle, onCode, onEdge, onPane, onGroup, title, nextRef, engine, groupNames }: { onPane?: () => void; onGroup?: (group: string) => void; engine: string; groupNames: Map<string, string>; settings: GraphSettings; decor: Decor; shown: Shown; onOpen: (n: ViewNode) => void; onToggle: (group: string) => void; onCode: (n: ViewNode, x: number, y: number) => void; onEdge?: (e: ViewEdge) => void; title: string; nextRef: MutableRefObject<(() => void) | null> }) {
  const dark = useComputedColorScheme("light") === "dark";
  const { view, status, matches, crit, heat: heated, odd } = shown;
  const layout = settings.layout === "upstream" && !hasUpstream(view) ? "layered-tb" : settings.layout;
  const placed = useMemo(() => place(view, layout), [view, layout]);
  const horizontal = layout !== "layered-tb" && layout !== "upstream";
  const searching = settings.q.trim() !== "";
  const flow = useReactFlow();
  const wrap = useRef<HTMLDivElement>(null);
  const [cursor, setCursor] = useState(0);
  // the card of the step, group or link under the mouse (or the focused step), drawn over the whole
  // map so no step covers it (Thomas: the cards went under the steps). A link's facts are also in
  // each step's panel, whose links are buttons, so the keyboard reaches them too.
  const [tip, setTip] = useState<{ id: string; x: number; y: number; above: boolean; now?: boolean } | null>(null);
  const onTip = useCallback((id: string | null, at?: Element, now?: boolean) => {
    const w = wrap.current?.getBoundingClientRect();
    if (!id || !at || !w) return setTip(null);
    const r = at.getBoundingClientRect();
    const above = r.bottom - w.top + 230 > w.height && r.top - w.top > 230;
    setTip({ id, x: Math.max(8, Math.min(r.left - w.left, w.width - 316)), y: above ? r.top - w.top - 8 : r.bottom - w.top + 8, above, now });
  }, []);
  // a card never outlives what it is about (a step hidden or folded under the mouse), and Escape
  // closes it (WCAG 1.4.13)
  // keyed on text: `fold` and `hide` are new arrays on every render
  useEffect(() => setTip(null), [settings.level, settings.fold.join(), settings.focus, settings.hide.join(), layout]);
  useEffect(() => {
    if (!tip) return;
    const key = (e: KeyboardEvent) => e.key === "Escape" && setTip(null);
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [tip]);
  const hover = (ev: { clientX: number; clientY: number }, e: Edge) => {
    const w = wrap.current?.getBoundingClientRect();
    if (!w) return;
    const x = ev.clientX - w.left;
    const y = ev.clientY - w.top;
    const above = y + 230 > w.height;
    setTip({ id: `edge:${e.id}`, x: Math.max(8, Math.min(x + 14, w.width - 316)), y: above ? y - 14 : y + 14, above });
  };

  const { nodes, edges, tips } = useMemo(() => {
    const nodes: Node[] = [];
    const tips = new Map<string, TipInfo>();
    const width = Math.max(0, ...[...placed.boxes.values()].map((b) => b.x + b.w)) + 40;
    // an area that is a foldable group carries the fold button; its steps then need none
    const foldable = new Set(view.nodes.filter((n) => n.group).map((n) => n.group!));
    const areaFolds = new Set<string>();
    for (const lane of placed.lanes) {
      const fold = lane.x !== undefined && foldable.has(lane.id) ? lane.id : null;
      if (fold) areaFolds.add(fold);
      const kids = view.nodes.filter((n) => n.lane === lane.id);
      const byState = new Map<ProcessStatus | null, number>();
      for (const n of kids) byState.set(status.get(n.id) ?? null, (byState.get(status.get(n.id) ?? null) ?? 0) + 1);
      const sum = kids.reduce((a, n) => ({ done: a.done + progress(n.counts).done, total: a.total + progress(n.counts).total }), { done: 0, total: 0 });
      const what = lane.id.startsWith("stage:") ? "stage" : lane.id.startsWith("file:") ? "rule file" : kids[0]?.kind === "job" ? "step" : "subworkflow";
      tips.set(`lane:${lane.id}`, {
        icon: lane.id.startsWith("stage:") ? GICONS.stage : GICONS.subworkflow,
        tone: null,
        title: lane.label,
        sub: `${what} · ${kids.length} ${kids.length === 1 ? "box" : "boxes"}`,
        progress: kids[0]?.kind === "job" ? undefined : sum,
        chips: [...byState].map(([st, k]) => ({ tone: statusTone(st), text: `${k} ${statusWord(st).toLowerCase()}` })),
        rows: [],
        hint: fold ? `${onGroup ? "Click the name: details · " : ""}round − button: fold it into one box` : "",
      });
      nodes.push({ id: `lane:${lane.id}`, type: "lane", position: { x: lane.x ?? 0, y: lane.y }, data: { id: lane.id, label: lane.label, area: lane.x !== undefined, fold, onToggle, onGroup, onTip, selected: decor.selected === lane.id } satisfies LaneData, width: lane.w ?? width, height: lane.h, selectable: false, draggable: false, focusable: false, zIndex: -1, style: { pointerEvents: "all" } });
    }
    // what the open step or link lights up: itself, its links and the steps at their other end
    const lit = new Set<string>();
    const litEdges = new Set<string>();
    const openEdge = decor.edge ? view.edges.find((e) => e.id === decor.edge) : undefined;
    if (openEdge) {
      lit.add(openEdge.source).add(openEdge.target);
      litEdges.add(openEdge.id);
    } else if (decor.selected && view.nodes.some((n) => n.id === decor.selected)) {
      // only a step on the map: one folded away or hidden lights nothing (CR-01)
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
      // a job's duration bar is against its step's longest job, like its colour
      const bar = n.kind === "job" && settings.overlay === "duration" && heated.has(n.id) ? { pct: heated.get(n.id)!, band: null } : barOf(settings.overlay, v, longest);
      const off = odd.get(n.id) ?? null;
      if (off !== null) extra.push(`${times(off)} its step's median: out of the norm`);
      const semantic = settings.overlay === "cpu" || settings.overlay === "memory";
      const h = semantic ? undefined : heated.get(n.id);
      const value = overlayText(n, settings.overlay);
      const metric = value ? ` · ${value}${off !== null ? ` · ${times(off)} median` : ""}` : "";
      const ring = decor.selected === n.id || (openEdge && lit.has(n.id)) ? "selected" : spotlight && lit.has(n.id) ? "near" : null;
      const tone = n.kind === "gate" && !s ? "review" : statusTone(s);
      tips.set(n.id, {
        icon: kindIcon(n.kind),
        tone,
        title: n.label,
        sub: n.kind === "job" ? `job of ${n.step ?? ""}` : `${kindWord(n.kind)}${n.group && n.kind !== "stage" && n.kind !== "subworkflow" ? ` · in ${groupNames.get(n.group) ?? n.group.replace(/^(stage|sub|file):/, "")}` : ""}`,
        state: statusWord(s),
        progress: total > 0 && n.kind !== "job" ? { done, total } : undefined,
        rows: [
          ...(durationOf(n) ? [{ icon: GICONS.clock, k: "Duration", v: formatSeconds(durationOf(n)), bar: settings.overlay === "duration" ? bar : null }] : []),
          ...(value && settings.overlay !== "duration" ? [{ icon: settings.overlay === "memory" ? GICONS.memory : settings.overlay === "cpu" ? GICONS.cpu : GICONS.warn, k: OVERLAY_NAME[settings.overlay] ?? "Value", v: value, bar }] : []),
          ...(off !== null ? [{ icon: GICONS.warn, k: "Out of the norm", v: `${times(off)} its step's median`, warn: true }] : []),
          ...(badge ? [{ icon: GICONS.link, k: "Compared", v: badge }] : []),
        ],
        flags: n.flags,
        hint: `Click: details · right-click: code${n.group ? " · double-click: fold" : ""}`,
      });
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
          tone,
          heat: h ?? null,
          odd: off,
          onTip,
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
          areaFold: !!n.group && areaFolds.has(n.group),
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
    // a link's card: its two ends, what it carries, its condition
    const byId = new Map(view.nodes.map((n) => [n.id, n]));
    for (const e of view.edges) {
      const a = byId.get(e.source);
      const b = byId.get(e.target);
      tips.set(`edge:${e.id}`, {
        icon: engine === "snakemake" ? GICONS.file : GICONS.channel,
        tone: null,
        title: engine === "snakemake" ? "Files" : "Channel",
        sub: engine === "snakemake" ? "files the downstream rule reads" : "values and files, item by item",
        ends: [a, b].map((x, i) => ({ label: x?.label ?? (i ? e.target : e.source), tone: statusTone(status.get(x?.id ?? "") ?? null), icon: kindIcon(x?.kind ?? "process") })),
        rows: [
          ...(e.conditions.length ? [{ icon: GICONS.conditional, k: "Only if", v: e.conditions.join(" or ") }] : []),
          ...(e.pairs.length > 1 ? [{ icon: GICONS.link, k: "Stands for", v: `${e.pairs.length} step-to-step links` }] : []),
        ],
        hint: "Click: its types and files",
      });
    }
    return { nodes, edges, tips };
  }, [view, placed, status, matches, crit, heated, odd, decor, searching, horizontal, layout, onOpen, onToggle, onCode, onTip, onGroup, settings.overlay, engine, groupNames]);

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
  // One group folded or unfolded by hand keeps the zoom, and keeps that group where it was on
  // screen (Thomas: "on ne garde pas le zoom et la vue"); anything else fits the new drawing.
  const shape = `${settings.level}|${layout}|${settings.focus}|${settings.hide.join()}`;
  const before = useRef({ shape, fold: settings.fold, view, placed });
  const first = useRef(true);
  const foldKey = settings.fold.join();
  useEffect(() => {
    const was = before.current;
    if (first.current) return void (first.current = false);
    if (was.shape === shape && was.fold.join() === settings.fold.join()) return;
    const toggled = [...settings.fold.filter((g) => !was.fold.includes(g)), ...was.fold.filter((g) => !settings.fold.includes(g))];
    const from = was.shape === shape && toggled.length === 1 ? groupBox(was.view, was.placed, toggled[0]) : null;
    const to = from ? groupBox(view, placed, toggled[0]) : null;
    if (from && to) {
      const { x, y, zoom } = flow.getViewport();
      void flow.setViewport({ x: x + (from.x - to.x) * zoom, y: y + (from.y - to.y) * zoom, zoom }, { duration: 200 });
      return;
    }
    const timer = setTimeout(() => void flow.fitView({ ...FIT, duration: 200 }), 60);
    return () => clearTimeout(timer);
  }, [shape, foldKey]); // eslint-disable-line react-hooks/exhaustive-deps
  // after the effect above: the drawing it compares the next change with
  useEffect(() => {
    before.current = { shape, fold: settings.fold, view, placed };
  });

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
        fitViewOptions={FIT}
        minZoom={0.1}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        zoomOnDoubleClick={false}
        onEdgeClick={onEdge ? (_, edge) => onEdge((edge.data as { edge: ViewEdge }).edge) : undefined}
        onPaneClick={onPane}
        onMoveStart={() => setTip(null)}
        onEdgeMouseEnter={(ev, e) => hover(ev, e)}
        onEdgeMouseLeave={() => setTip(null)}
        // the empty inside of a group's area is the map too
        onNodeClick={onPane ? (e, n) => n.type === "lane" && !(e.target as Element).closest("button") && onPane() : undefined}
        onlyRenderVisibleElements={view.nodes.length > 300}
      >
        <Background gap={24} size={1} />
        {tip && tips.get(tip.id) && <TipCard info={tips.get(tip.id)!} x={tip.x} y={tip.y} above={tip.above} now={tip.now} />}
        <Controls showInteractive={false} showFitView={false} aria-label="Zoom" className="sp-gcontrols">
          {/* our own fit button: React Flow's drew a pale icon that read as disabled (Thomas); no
              animation, which a zoom still settling could cut short and leave the map unmoved */}
          <ControlButton onClick={() => void flow.fitView(FIT)} aria-label="Fit the whole map in view" title="Fit the whole map in view">
            <Icon path={GICONS.fit} size={14} stroke={2} />
          </ControlButton>
        </Controls>
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

const OVERLAY_NAME: Partial<Record<GraphSettings["overlay"], string>> = { cpu: "CPU used / asked", memory: "Memory used / asked", failures: "Failures" };

/** A ratio to a median, as people say it: "3.1×", "0.4×". */
export const times = (r: number) => `${r >= 10 ? Math.round(r) : r.toFixed(1)}×`;

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
function Legend({ overlay, view, runtime, help, notes }: { overlay: GraphSettings["overlay"]; view: View; runtime: boolean; help: string; notes?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const jobs = view.nodes.some((n) => n.kind === "job");
  const semantic = overlay === "cpu" || overlay === "memory";
  // jobs are coloured against their own step's jobs: the key's ends then come from the steps only
  const texts = view.nodes.filter((n) => n.kind !== "job").map((n) => [overlayValue(n, overlay), overlayText(n, overlay)] as const).filter(([v]) => v !== null) as [number, string][];
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
    ) : jobs ? (
      <span className="sp-gkey">
        lowest <span className="sp-gramp" aria-hidden="true" /> highest, among each step's jobs
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
        {runtime && key}
        {runtime && jobs && (overlay === "duration" || overlay === "cpu" || overlay === "memory") && (
          <span className="sp-gkey">
            <span className="sp-gswatch" data-odd aria-hidden="true" /> each job against its step's jobs; dashed: {OUTLIER}× above or below its step's median
          </span>
        )}
      </div>
      {open && (
        <div className="sp-glegend-more">
          <p className="sp-glegend-help">{help}</p>
          {notes}
          {runtime && <p className="sp-glegend-help">{OVERLAY_HELP[overlay]}</p>}
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
  "layered-tb": "Steps in layers, top to bottom: each step below the steps it reads from, inside its subworkflow or stage, whose title folds it.",
  "layered-lr": "Steps in layers, left to right: each step right of the steps it reads from, inside its subworkflow or stage, whose title folds it.",
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
      <Menu position="bottom-end" withinPortal={false} shadow="md">
        <Menu.Target>
          <button type="button" className="sp-gbtn sp-gbtn-line">
            <Icon path={ICONS.download} size={13} /> Export
            <Icon path={ICONS.chevronDown} size={12} stroke={2} />
          </button>
        </Menu.Target>
        {/* Escape closes the menu only, not the details panel behind it */}
        <Menu.Dropdown onKeyDown={(e) => e.key === "Escape" && e.nativeEvent.preventDefault()}>
          <Menu.Item leftSection={<Icon path={ICONS.download} size={13} />} onClick={() => onExport("svg")}>
            SVG
          </Menu.Item>
          <Menu.Item leftSection={<Icon path={ICONS.download} size={13} />} onClick={() => onExport("png")}>
            PNG
          </Menu.Item>
          <Menu.Item leftSection={<Icon path={ICONS.download} size={13} />} onClick={() => onExport("html")}>
            HTML
          </Menu.Item>
          <Menu.Item leftSection={<Icon path={GICONS.copy} size={13} />} onClick={() => onExport("copy")}>
            Copy PNG
          </Menu.Item>
        </Menu.Dropdown>
      </Menu>
      <button type="button" className="sp-gbtn sp-gbtn-line" aria-pressed={full} onClick={onFullscreen} aria-label="Full screen">
        <Icon path={GICONS.fullscreen} size={13} stroke={2} />
      </button>
    </div>
  );
}

/** Fitting the map leaves room at the top for the legend drawn over it. */
const FIT = { padding: { top: "56px", right: "24px", bottom: "24px", left: "24px" } } as const;

/** At most this many boxes after Auto-fold. */
const AUTO_FOLD_MAX = 24;

function Inner({ doc, title, settings, onSettings, runtime = false, jobs, decor = {}, onOpen, onEdge, source, extra, notes, side, onReset, onGroup, banner }: Props) {
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
      // the item takes the promise, so the write starts within the click (Safari, CR-12)
      Promise.resolve()
        .then(() => navigator.clipboard.write([new ClipboardItem({ "image/png": svgToPng(svg) })]))
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
  // Escape, when nothing on top took it (a card, the panel): out of the focused group, else back
  // to the plain map (what is open or traced is cleared; folds, search and layout stay)
  const focus = settings.focus;
  const reset = useRef(onReset);
  reset.current = onReset;
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented || typing(e.target) || document.querySelector(".sp-ginspect, .sp-gcodepop")) return;
      // the graph's own Escape: from inside it, or with nothing focused; not a page dialog's
      if (e.target !== document.body && !(e.target instanceof Node && root.current?.contains(e.target))) return;
      if (focus) onSettings({ focus: null });
      else reset.current?.();
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [focus, onSettings]);
  // the map fills the screen below the toolbar and banners (Thomas: less room for the header):
  // their height, kept as a CSS variable the map's height is worked out from
  const head = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = head.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => root.current?.style.setProperty("--sp-ghead", `${Math.round(el.getBoundingClientRect().height)}px`));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <div className="sp-graph" ref={root} data-full={full || undefined}>
      {pop && <CodePop doc={doc} pop={pop} source={source ?? null} onClose={closePop} />}
      <div className="sp-ghead" ref={head}>
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
        {banner}
        {settings.show === "list" && notes}
      </div>
      <div className="sp-gbody" data-list={settings.show === "list" || undefined}>
        {settings.show === "map" ? (
          <div className="sp-gmapcell">
            <Map_ nextRef={nextRef} settings={settings} decor={decor} shown={shown} onOpen={onOpen} onToggle={onToggle} onCode={onCode} onEdge={onEdge} onPane={onReset} onGroup={onGroup} title={title} engine={doc.engine} groupNames={groupNames} />
            {/* over the map's top left corner: the colour key, and behind its toggle the layout's help and the notes */}
            <Legend overlay={settings.overlay} view={shown.view} runtime={runtime} help={LAYOUT_HELP[layout]} notes={notes} />
          </div>
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

/** The details panel's width: dragged or set with the arrow keys, kept in this browser. */
const SIDE_KEY = "spectio.graph.side";
const SIDE_MIN = 300;
const SIDE_MAX = 900;
const readSide = (): number => {
  try {
    const v = Number(localStorage.getItem(SIDE_KEY));
    return v >= SIDE_MIN && v <= SIDE_MAX ? v : 400;
  } catch {
    return 400;
  }
};

/** The panel's left edge: drag it, or focus it and use the arrow keys (a window splitter). */
function Resizer({ panel }: { panel: MutableRefObject<HTMLElement | null> }) {
  const [width, setWidth] = useState(readSide);
  useLayoutEffect(() => {
    panel.current?.parentElement?.style.setProperty("--sp-side-w", `${width}px`);
    try {
      localStorage.setItem(SIDE_KEY, String(width));
    } catch {
      // private window: the width is not kept
    }
  }, [width, panel]);
  // never so wide that the map is gone
  const clamp = (w: number) => Math.round(Math.max(SIDE_MIN, Math.min(SIDE_MAX, (panel.current?.parentElement?.clientWidth || Infinity) - 320, w)));
  const drag = (e: React.PointerEvent<HTMLButtonElement>) => {
    const x0 = e.clientX;
    const w0 = width;
    const el = e.currentTarget;
    el.setPointerCapture(e.pointerId);
    const move = (m: PointerEvent) => setWidth(clamp(w0 + x0 - m.clientX));
    const up = () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("pointercancel", up);
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
  };
  return (
    <button
      type="button"
      className="sp-ginspect-resize"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the details panel"
      aria-valuenow={width}
      aria-valuemin={SIDE_MIN}
      aria-valuemax={SIDE_MAX}
      onPointerDown={drag}
      onKeyDown={(e) => {
        const by = { ArrowLeft: 32, ArrowRight: -32 }[e.key];
        const to = e.key === "Home" ? SIDE_MIN : e.key === "End" ? SIDE_MAX : by !== undefined ? width + by : null;
        if (to === null) return;
        e.preventDefault();
        setWidth(clamp(to));
      }}
    />
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
      <Resizer panel={ref} />
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
      <div className="sp-ginspect-body">{children}</div>
    </aside>
  );
}
