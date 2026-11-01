// A small typed client of the routes the screens use (P1 Tasks 17, 18 and 20; api §5).
// Hand-written from the OpenAPI snapshot packages/spectio-server/openapi/0.0.1.json, whose read
// routes have response models (FU-P3-21); api.test.ts checks the field names against it.

export type Engine = "nextflow" | "snakemake";
export const ENGINES: Engine[] = ["nextflow", "snakemake"];
export const ENGINE_FILES: Record<Engine, string[]> = {
  nextflow: ["main.nf"],
  snakemake: ["Snakefile", "workflow/Snakefile"],
};

export type JSONSchema = Record<string, unknown>;

/** `GET /api/v1/workflows:inspect` */
export interface Inspected {
  location: string;
  revision: string | null;
  engine: Engine | null;
  engine_files: string[];
  name: string;
  version: string | null;
  engine_version: string | null;
  engine_versions: Partial<Record<Engine, string | null>>;
  schema: JSONSchema | null;
  schema_source: "nextflow_schema.json" | "config.schema.yaml" | "inferred" | "none";
  profiles: string[];
}

/** The body of `POST /api/v1/runs` (api §5 note of 2026-10-30). */
export interface LaunchBody {
  workflow: { location: string; revision: string | null; engine: Engine };
  name?: string;
  profiles: string[];
  params: Record<string, unknown>;
}

export interface Launched {
  id: string;
  name: string;
  state: string;
}

/** `GET /api/v1/version` (schema `ServerVersion`) */
export interface ServerVersion {
  version: string;
  node: string;
  runs_root: string;
  account: string;
  executor: string;
}

/** api §7.1 (schema `Run.state`). */
export type RunState =
  | "queued"
  | "running"
  | "pausing"
  | "paused"
  | "awaiting_review"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled";
/** api §7.2 (schema `Task.state`). */
export type TaskState =
  | "pending"
  | "submitted"
  | "running"
  | "succeeded"
  | "failed"
  | "cached"
  | "stored"
  | "aborted"
  | "not_scheduled";
export type StageState = "not_started" | "running" | "awaiting_review" | "completed" | "failed" | "skipped";
export type Counts = Record<string, number>;
export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

/** Schema `Run`: an item of `GET /runs`. */
export interface Run {
  id: string;
  name: string | null;
  state: RunState;
  origin: "ui" | "api" | "wes" | "cli-observed" | "cli-adopted" | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  workflow: {
    engine: string | null;
    engine_version: string | null;
    location: string;
    name: string | null;
    version: string | null;
  };
  profiles: string[];
  failure: { [key: string]: Json } | null;
  head: { session: string | null; node: string; alive: boolean; exit_code: number | null } | null;
  task_counts: Counts;
  summary: {
    tasks: { done: number; total: number; failed: number; cached: number };
    last_failure: { [key: string]: Json } | null;
    /** Where the run's stages come from; `quarters` when it has none (api §7, P1 Task 27). */
    stage_mode: "declared" | "detected" | "quarters";
  };
}

/** Schema `RunDetail`: `GET /runs/{id}` and `POST /runs/{id}:cancel`. */
export interface RunDetail extends Run {
  params: { [key: string]: Json };
  /** Why declared stages were not applied: two matching overlays, overlapping globs. */
  stages_note: string | null;
  /** The failed tasks' last attempts, in the order their last attempts were created, at most
   * 10 (api §5, P1 Task 29). */
  failures: Failure[];
  failures_total: number;
}

/** Schema `Scheduler`: what SLURM says of a failed job; fields from `sacct` [to be validated]. */
export interface Scheduler {
  state: string | null;
  reason: string | null;
  state_source: "sacct" | "engine_message" | null;
  max_rss_bytes: number | null;
  req_mem_bytes: number | null;
  elapsed_s: number | null;
  time_limit_s: number | null;
  usage_source: "sacct" | "trace" | null;
  accounting: "available" | "pending" | "unavailable";
}

/** Schema `Failure`: one failed task's last attempt. */
export interface Failure {
  task_id: string;
  process: string;
  tag: string | null;
  attempt_n: number;
  native_id: string | null;
  exit_code: number | null;
  message: string | null;
  log_tail: string | null;
  scheduler: Scheduler;
  /** The directory to copy: the attempt's work directory (Nextflow), the launch directory
   * (Snakemake); null when not recorded. */
  work_dir: string | null;
}

/** Schema `Resources`: asked for and used, by the task's last attempt; null until known. */
export interface Resources {
  cpus: number | null;
  memory_bytes: number | null;
  time_s: number | null;
  realtime_s: number | null;
  cpu_percent: number | null;
  peak_rss_bytes: number | null;
  source: "trace" | "benchmark" | "sacct" | null;
}

export interface Page<T> {
  items: T[];
  next: string | null;
}

/** Schema `Process`. */
export interface Process {
  process: string;
  stage_id: string | null;
  counts: Counts;
  retries: number;
}

/** Schema `Stage`. */
export interface Stage {
  id: string;
  position: number;
  name: string | null;
  source: "declared" | "detected";
  state: StageState;
  task_counts: Counts;
}

/** Schema `Task`. */
export interface Task {
  id: string;
  process: string;
  tag: string | null;
  name: string | null;
  state: TaskState;
  stage_id: string | null;
  /** The last attempt's number, the one `resources` and the attempt files are read from. */
  attempt_n: number | null;
  resources: Resources;
}

/** Schema `Summary`: `GET /runs:summary?group_by=state`. */
export interface Summary {
  groups: { key: string; count: number }[];
}

/** Schema `TaskFile`: one file of an attempt; `size` and `mtime` only when `present`. */
export interface TaskFile {
  name: string;
  kind: "script" | "wrapper" | "stdout" | "stderr" | "job_log" | "exit" | "marker" | "trace" | "rule_log" | "slurm_log";
  size: number | null;
  mtime: string | null;
  state: "present" | "not_yet" | "absent" | "deleted_after_success" | "cleaned";
  note: string | null;
}

/** Schema `TaskFiles`: `GET /tasks/{id}/attempts/{n}/files` (P1 Task 28). */
export interface TaskFiles {
  task_id: string;
  attempt: number;
  work_dir: string | null;
  native_id: string | null;
  files: TaskFile[];
}

export type LogSource = "head-out" | "head-err" | "engine";

export interface FieldError {
  field: string;
  message: string;
}

/** An RFC 9457 problem; a 422 carries `errors` with a dotted `field` (inbox #86 rule 3). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly errors: FieldError[] = [],
  ) {
    super(message);
  }
}

const API = "/api/v1";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail ?? body?.title ?? `HTTP ${response.status}`;
    throw new ApiError(response.status, detail, Array.isArray(body?.errors) ? body.errors : []);
  }
  return body as T;
}

export function getVersion(signal?: AbortSignal): Promise<ServerVersion> {
  return call("/version", { signal });
}

export function inspect(
  location: string,
  revision: string | null,
  signal?: AbortSignal,
): Promise<Inspected> {
  const query = new URLSearchParams({ location });
  if (revision) query.set("revision", revision);
  return call(`/workflows:inspect?${query}`, { signal });
}

const query = (params: Record<string, string | number | null | undefined>) => {
  const found = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") found.set(key, String(value));
  }
  const text = found.toString();
  return text ? `?${text}` : "";
};
const run = (id: string) => `/runs/${encodeURIComponent(id)}`;

export interface RunsQuery {
  state?: string;
  q?: string;
  sort?: "-created_at" | "-ended_at";
  limit?: number;
  cursor?: string | null;
}

export function listRuns(params: RunsQuery, signal?: AbortSignal): Promise<Page<Run>> {
  return call(`/runs${query({ ...params })}`, { signal });
}

export function runsSummary(signal?: AbortSignal): Promise<Summary> {
  return call("/runs:summary?group_by=state", { signal });
}

export function getRun(id: string, signal?: AbortSignal): Promise<RunDetail> {
  return call(run(id), { signal });
}

export function listProcesses(id: string, signal?: AbortSignal): Promise<{ items: Process[] }> {
  return call(`${run(id)}/processes`, { signal });
}

export function listStages(id: string, signal?: AbortSignal): Promise<{ items: Stage[] }> {
  return call(`${run(id)}/stages`, { signal });
}

export function listTasks(
  id: string,
  params: { state?: string; process?: string; cursor?: string | null; limit?: number },
  signal?: AbortSignal,
): Promise<Page<Task>> {
  return call(`${run(id)}/tasks${query({ ...params })}`, { signal });
}

export function cancelRun(id: string): Promise<RunDetail> {
  return call(`${run(id)}:cancel`, { method: "POST" });
}

/** Where a run log's text is served: the same origin, text/plain (the Logs tab's Open raw). */
export const logUrl = (id: string, source: LogSource) => `${API}${run(id)}/logs${query({ source })}`;

/** The last 64 KiB of a run log, as text. */
export async function getLog(id: string, source: LogSource, signal?: AbortSignal): Promise<string> {
  const response = await fetch(logUrl(id, source), { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? body?.title ?? `HTTP ${response.status}`);
  }
  return response.text();
}

const attempt = (taskId: string, n: number) => `/tasks/${encodeURIComponent(taskId)}/attempts/${n}/files`;

export function listTaskFiles(taskId: string, n: number, signal?: AbortSignal): Promise<TaskFiles> {
  return call(attempt(taskId, n), { signal });
}

/** Where a job file is served, as text/plain: its last 64 KiB, or `tail` bytes (at most 1 MiB);
 * `download` asks for it as an attachment. A Snakemake name is a path: each part is encoded. */
export const taskFileUrl = (taskId: string, n: number, name: string, opts: { tail?: number; download?: boolean } = {}) =>
  `${API}${attempt(taskId, n)}/${name.split("/").map(encodeURIComponent).join("/")}${query({ tail: opts.tail, download: opts.download ? "true" : null })}`;

/** The last 64 KiB of a job file, as text; a refusal is an ApiError with its status (404, 410,
 * 415, 422, 503). */
export async function getTaskFile(taskId: string, n: number, name: string, signal?: AbortSignal): Promise<string> {
  const response = await fetch(taskFileUrl(taskId, n, name), { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? body?.title ?? `HTTP ${response.status}`);
  }
  return response.text();
}

export function launch(body: LaunchBody): Promise<Launched> {
  return call("/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}
