// The workflow graph of issue #160: GraphDocument v1 and its routes, as in
// spikes/metroflow/graph-contract.md (api §5.10 once the spec lands). Hand-written like api.ts;
// the server routes come with the same branch.
import { ApiError, type Counts, type ProcessStatus } from "../../api";

export type GraphLevel = "stage" | "subworkflow" | "process" | "jobs";
export type GraphLayout = "layered-tb" | "layered-lr" | "metro" | "compact" | "upstream";
export type GraphOverlay = "state" | "duration" | "cpu" | "memory" | "failures" | "critical";
/** `gate`: kept for the stage gates of a later version; 0.0.1 sends none. */
export type NodeKind = "process" | "rule" | "checkpoint" | "gate";

export interface GraphGroup {
  id: string;
  kind: "stage" | "subworkflow";
  name: string;
  parent: string | null;
  condition: string | null;
}

export interface GraphMetrics {
  duration_s?: number | null;
  cpu_mean?: number | null;
  mem_max?: number | null;
  failed?: number | null;
}

export interface GraphNode {
  id: string;
  name: string;
  kind: NodeKind;
  stage_id: string | null;
  subworkflow: string | null;
  source: { file: string; line: number | null } | null;
  condition: string | null;
  params: string[];
  /** BioFlow-Insight's position, the Upstream layout's hint. */
  layout?: { x: number; y: number } | null;
  // runtime overlay, on /runs/{id}/graph only
  status?: ProcessStatus;
  counts?: Counts;
  retries?: number;
  pipeline_order?: number;
  metrics?: GraphMetrics;
  first_start?: string | null;
  last_end?: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  /** The code's condition on this link, when the producer knows it. */
  condition?: string | null;
  /** Read from the code, not seen at run time. */
  static?: boolean;
}

export interface GraphDocument {
  version: 1;
  engine: "nextflow" | "snakemake";
  producer: "smk-rulegraph" | "nf-dag" | "bioflow-insight" | "stages-only";
  /** false: the edges are unknown, or the DAG can still grow (an open checkpoint). */
  complete: boolean;
  /** The whole graph is a static estimate from the code (BioFlow-Insight): edges may be wrong. */
  estimate?: boolean;
  groups: GraphGroup[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeOutput {
  path: string;
  task_id: string;
  attempt_n: number;
  state: "present" | "removed" | "missing" | "unknown";
  temp: boolean;
  /** What `path` is relative to: the launch directory, the results directory, or none. */
  root: "launch" | "results" | "absolute";
}

const API = "/api/v1";

async function call<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(API + path, { signal });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const slug = typeof body?.type === "string" ? body.type.replace("/problems/", "") : null;
    throw new ApiError(response.status, body?.detail ?? body?.title ?? `HTTP ${response.status}`, [], null, slug);
  }
  return body as T;
}

const run = (id: string) => `/runs/${encodeURIComponent(id)}`;

/** `GET /features`; a server without the route has none. */
export async function getFeatures(signal?: AbortSignal): Promise<string[]> {
  try {
    const found = await call<{ features?: unknown }>("/features", signal);
    return Array.isArray(found.features) ? found.features.filter((f): f is string => typeof f === "string") : [];
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return [];
    throw e;
  }
}

export function getRunGraph(id: string, signal?: AbortSignal): Promise<GraphDocument> {
  return call(`${run(id)}/graph`, signal);
}

export function getWorkflowGraph(location: string, revision: string | null, signal?: AbortSignal): Promise<GraphDocument> {
  const query = new URLSearchParams({ location });
  if (revision) query.set("revision", revision);
  return call(`/workflows:graph?${query}`, signal);
}

export function getNodeOutputs(id: string, process: string, signal?: AbortSignal): Promise<{ items: NodeOutput[] }> {
  return call(`${run(id)}/processes/${encodeURIComponent(process)}/outputs`, signal);
}

/** The graph, or some of its links, is read from the code rather than seen at run time. */
export const isEstimate = (doc: GraphDocument): boolean => !!doc.estimate || doc.edges.some((e) => e.static);
