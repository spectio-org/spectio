// The workflow graph (issue #160; ui-spec §4.14): a toolbar (level, layout, colour, search, Map
// or List, export), the map drawn with React Flow, and the List, its table equivalent. Shared by
// the run's Graph tab and the Launch map. Every node is a native button whose name says its state;
// pipeline text is rendered as text only.
import { NativeSelect, TextInput, useComputedColorScheme } from "@mantine/core";
import {
  Background,
  Controls,
  Handle,
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
  collapse,
  criticalPath,
  durationOf,
  heat,
  overlayValue,
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

/** The marks of a step: a short visible mark, and the words its accessible name gets. */
export const FLAG_MARKS: Record<Flag, { mark: string; words: string }> = {
  checkpoint: { mark: "◆ checkpoint", words: "checkpoint: the graph grows once it ends" },
  temp: { mark: "temp", words: "writes temporary files, removed once read" },
  conditional: { mark: "if", words: "runs only under a condition" },
  retried: { mark: "↻", words: "some jobs were retried" },
  cached: { mark: "cached", words: "some jobs reused from an earlier run" },
};

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
  selected: boolean;
  badge: string | null;
  horizontal: boolean;
  onOpen: (n: ViewNode) => void;
  onToggle: (group: string) => void;
  onCode: (n: ViewNode, x: number, y: number) => void;
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
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);
  const style = data.heat !== null ? { ["--sp-heat" as string]: `${Math.round(10 + data.heat * 80)}%` } : undefined;
  return (
    <div
      className="sp-gnode"
      data-tone={data.tone}
      data-kind={node.kind}
      data-dim={data.dim || undefined}
      data-crit={data.crit || undefined}
      data-match={data.matched || undefined}
      data-selected={data.selected || undefined}
      data-heat={data.heat !== null || undefined}
      style={style}
      onDoubleClick={
        node.group
          ? () => {
              if (timer.current) clearTimeout(timer.current);
              data.onToggle(node.group!);
            }
          : undefined
      }
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
        // a box with a group waits a moment before opening its sheet, so a double-click folds
        // the group without the sheet opening over the map first
        onClick={(e) => {
          if (timer.current) clearTimeout(timer.current);
          if (!node.group || e.detail === 0) return data.onOpen(node); // Enter or Space: at once
          if (e.detail === 1) timer.current = setTimeout(() => data.onOpen(node), 250);
        }}
      >
        {node.kind === "job" && node.step && <span className="sp-gnode-step">{node.step}</span>}
        <span className="sp-gnode-name">{data.label}</span>
        <span className="sp-gnode-meta">{data.meta}</span>
        {node.flags && node.flags.length > 0 && (
          <span className="sp-gflags" aria-hidden="true">
            {node.flags.map((f) => (
              <span key={f} className="sp-gflag" data-flag={f}>
                {FLAG_MARKS[f].mark}
              </span>
            ))}
          </span>
        )}
        {data.badge && <span className="sp-gnode-badge">{data.badge}</span>}
      </button>
      <Handle type="source" position={horizontal ? Position.Right : Position.Bottom} isConnectable={false} />
    </div>
  );
}

function LaneBox({ data }: NodeProps<Node<{ label: string }>>) {
  return (
    <div className="sp-glane" aria-hidden="true">
      <span>{data.label}</span>
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
}

interface Shown {
  view: View;
  status: Map<string, ProcessStatus | null>;
  matches: Set<string>;
  crit: { nodes: Set<string>; edges: Set<string> } | null;
  heat: Map<string, number>;
}

function useShown(doc: GraphDocument, settings: GraphSettings, jobs: Record<string, Task[]> | undefined, decor: Decor, runtime: boolean): Shown {
  const view = useMemo(() => collapse(doc, settings.level, jobs, settings.fold), [doc, settings.level, jobs, settings.fold]);
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

function Map_({ settings, decor, shown, onOpen, onToggle, onCode, onEdge, title, nextRef }: { settings: GraphSettings; decor: Decor; shown: Shown; onOpen: (n: ViewNode) => void; onToggle: (group: string) => void; onCode: (n: ViewNode, x: number, y: number) => void; onEdge?: (e: ViewEdge) => void; title: string; nextRef: MutableRefObject<(() => void) | null> }) {
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
      nodes.push({ id: `lane:${lane.id}`, type: "lane", position: { x: 0, y: lane.y }, data: { label: lane.label }, width, height: lane.h, selectable: false, draggable: false, focusable: false, zIndex: -1 });
    }
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
      const h = heated.get(n.id);
      const value = overlayText(n, settings.overlay);
      const metric = value ? ` · ${value}` : "";
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
        data: {
          node: n,
          status: s,
          label: n.label,
          meta: `${statusWord(s)}${total > 0 && n.kind !== "job" ? ` · ${done}/${total}` : ""}${metric}`,
          aria: ariaOf(n, s, extra),
          tone: n.kind === "gate" && !s ? "review" : statusTone(s),
          heat: h ?? null,
          dim: (searching && !matched) || lineageOut,
          crit: inCrit,
          matched: matched && searching,
          selected: decor.selected === n.id,
          badge,
          horizontal,
          onOpen,
          onToggle,
          onCode,
        },
      };
    };
    for (const n of view.nodes) nodes.push(make(n));
    const edges: Edge[] = view.edges.map((e) => {
      const onCrit = crit?.edges.has(e.id) ?? false;
      const dim = (searching && !(matches.has(e.source) && matches.has(e.target))) || (decor.lineage ? !(decor.lineage.has(e.source) && decor.lineage.has(e.target)) : false);
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: layout === "metro" || layout === "compact" ? "smoothstep" : "default",
        focusable: false,
        className: [onCrit && "sp-gedge-crit", dim && "sp-gedge-dim"].filter(Boolean).join(" ") || undefined,
        animated: status.get(e.target) === "running" && !dim,
        interactionWidth: 14,
        data: { edge: e },
      };
    });
    return { nodes, edges };
  }, [view, placed, status, matches, crit, heated, decor, searching, horizontal, layout, onOpen, onToggle, onCode, settings.overlay]);

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

function Legend({ overlay, view }: { overlay: GraphSettings["overlay"]; view: View }) {
  const help = <span className="sp-glegend-help">{OVERLAY_HELP[overlay]}</span>;
  if (overlay === "state")
    return (
      <div className="sp-glegend" role="note" aria-label="Legend">
        <ul className="sp-gkey">
          {STATE_KEY.map(([t, label]) => (
            <li key={t}>
              <span className="sp-gswatch" data-tone={t} aria-hidden="true" /> {label}
            </li>
          ))}
        </ul>
        <ul className="sp-gkey" aria-label="Marks">
          {Object.values(FLAG_MARKS).map((f) => (
            <li key={f.mark}>
              <span className="sp-gflag">{f.mark}</span> {f.words}
            </li>
          ))}
        </ul>
        {help}
      </div>
    );
  if (overlay === "critical")
    return (
      <div className="sp-glegend" role="note" aria-label="Legend">
        {help} Thick outline: on the path.
      </div>
    );
  const texts = view.nodes.map((n) => [overlayValue(n, overlay), overlayText(n, overlay)] as const).filter(([v]) => v !== null) as [number, string][];
  const low = texts.length ? texts.reduce((a, b) => (b[0] < a[0] ? b : a)) : null;
  const high = texts.length ? texts.reduce((a, b) => (b[0] > a[0] ? b : a)) : null;
  return (
    <div className="sp-glegend" role="note" aria-label="Legend">
      {help}{" "}
      {high ? (
        <>
          Lightest {low![1]} <span className="sp-gramp" aria-hidden="true" /> darkest {high[1]}; the value is written on each step. Steps with no value keep their state colour.
        </>
      ) : (
        "No step has a value yet (jobs still running, cached, or not measured): steps keep their state colour."
      )}
    </div>
  );
}

function Toolbar({ settings, onSettings, runtime, upstream, onNext, matches, onExport, extra }: {
  settings: GraphSettings;
  onSettings: (p: Partial<GraphSettings>) => void;
  runtime: boolean;
  upstream: boolean;
  onNext: () => void;
  matches: number;
  onExport: (kind: "svg" | "png" | "html") => void;
  extra?: ReactNode;
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
          }
        }}
        description={settings.q.trim() ? `${matches} ${matches === 1 ? "match" : "matches"}${matches > 0 && settings.show === "map" ? ", Enter for the next" : ""}` : undefined}
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
      </div>
    </div>
  );
}

function Inner({ doc, title, settings, onSettings, runtime = false, jobs, decor = {}, onOpen, onEdge, source, extra, notes }: Props) {
  const shown = useShown(doc, settings, jobs, decor, runtime);
  const [exportError, setExportError] = useState<string | null>(null);
  const layout = settings.layout === "upstream" && !hasUpstream(shown.view) ? "layered-tb" : settings.layout;
  const onExport = (kind: "svg" | "png" | "html") => {
    const placed = place(shown.view, layout);
    const svg = toSvg(shown.view, placed, title);
    const name = `${title.replace(/[^\w.-]+/g, "_")}-graph.${kind}`;
    setExportError(null);
    if (kind === "svg") download(name, new Blob([svg], { type: "image/svg+xml" }));
    else if (kind === "html") download(name, new Blob([toHtml(shown.view, placed, title, doc.engine)], { type: "text/html" }));
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
  return (
    <div className="sp-graph">
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
      />
      {exportError && <p role="alert">{exportError}</p>}
      {isEstimate(doc) && (
        <p className="sp-gbanner" role="note">
          Static estimate from the code: links may be approximate, and loops in the code are drawn with one link set aside.
        </p>
      )}
      {notes}
      {runtime && settings.show === "map" && <Legend overlay={settings.overlay} view={shown.view} />}
      {settings.show === "map" ? (
        <Map_ nextRef={nextRef} settings={settings} decor={decor} shown={shown} onOpen={onOpen} onToggle={onToggle} onCode={onCode} onEdge={onEdge} title={title} />
      ) : (
        <List shown={shown} settings={settings} onOpen={onOpen} decor={decor} />
      )}
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
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
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
