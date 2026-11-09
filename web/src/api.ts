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

/** Schema `RunEnvironment`: the run's own environment, as resolved at launch (FU-P3-86a, api
 * §5.4); its fields are null unless `state` is `recorded`. */
export interface RunEnvironment {
  name: string | null;
  label: string | null;
  executor: "local" | "slurm" | null;
  slurm: { partition: string | null; account: string | null; time_min: number | null; mem_mib: number | null } | null;
  local: { cpus: number | null; mem_mib: number | null } | null;
  state: "recorded" | "not_recorded" | "not_readable";
}

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
  /** Null for a run started from a terminal (optional until the screens of FU-P3-86g read it). */
  environment?: RunEnvironment | null;
  failure: { [key: string]: Json } | null;
  /** `checked` false: a run started from a terminal on another host or boot, whose head the
   * server cannot see (architecture §13.8). */
  head: { session: string | null; node: string; alive: boolean; exit_code: number | null; checked: boolean } | null;
  task_counts: Counts;
  summary: {
    /** `lower_bound`: a checkpoint is open, the total may grow (P1 Task 34; optional until the
     * screens of P1 Task 35 read it). */
    tasks: { done: number; total: number; failed: number; cached: number; lower_bound?: boolean };
    last_failure: { [key: string]: Json } | null;
    /** Where the run's stages come from; `quarters` when it has none (api §7, P1 Task 27). */
    stage_mode: "declared" | "detected" | "quarters";
    /** Snakemake checkpoint rules with a job left, and the count of `snakemake.dag_updated`. */
    open_checkpoints?: string[];
    dag_updates?: number;
  };
}

/** Schema `EngineSettings`: Nextflow's `cleanup`; Snakemake's `--notemp`, null in 0.0.1. */
export interface EngineSettings {
  cleanup: boolean | null;
  notemp: boolean | null;
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
  /** The engine command as the head script runs it; null for a run started from a terminal
   * (api §5, P1 Task 30). */
  command: { argv: string[]; text: string } | null;
  parent_run_id: string | null;
  /** The runs that resumed this one (P1 Task 30). */
  resumed_as: { id: string; name: string | null; state: RunState }[];
  /** Whether Resume is allowed now, and why not (api §5, P1 Task 30). */
  actions: { resume: { allowed: boolean; reason: ResumeReason | null } };
  /** The run's results directory; null when unknown or a run started from a terminal (api §5,
   * P1 Task 31). */
  results_dir: string | null;
  engine_settings?: EngineSettings;
}

/** Schema `ResultEntry`: one item of a results folder. */
export interface ResultEntry {
  name: string;
  type: "dir" | "file" | "link_outside";
  size: number | null;
  mtime: string | null;
}

/** Schema `ResultReport`: an HTML report found below the results root. */
export interface ResultReport {
  path: string;
  title: string;
  group: string | null;
}

/** Schema `ResultStat`: the listing's entry for one results path, with the root and the path the
 * server answered for (api §5.3). */
export interface ResultStat {
  root: string;
  path: string;
  name: string;
  type: "dir" | "file" | "link_outside";
  size: number | null;
  mtime: string | null;
}

/** `GET /api/v1/runs/{id}/results?path=` (P1 Task 31). */
export interface Results {
  root: string;
  path: string;
  exists: boolean;
  entries: ResultEntry[];
  truncated: boolean;
  /** Absent from a work directory's listing. */
  reports: ResultReport[];
}

/** Schema `CodeLoading`: a value that loads code or configuration (dev-env §15.3 req. 16):
 * `field` is `params.<name>`, `workflow.location` or `engine.<option>`. */
export interface CodeLoading {
  field: string;
  value: string;
  writable_by_others: boolean;
}

/** `GET /runs/{id}:launch-template` (schema `LaunchTemplate`): a `POST /runs` body prefilled from
 * a run, for Copy to a new launch (P1 Task 30). */
export interface LaunchTemplate {
  workflow: { location: string; revision: string | null; engine: Engine };
  profiles: string[];
  params: { [key: string]: Json };
  /** The top-level parameters that differ from the pipeline's schema defaults. */
  non_default: string[];
  code_loading: CodeLoading[];
  /** The run's environment by name, or the default when that name is gone (FU-P3-86c). */
  environment: string;
  /** Why the default is chosen instead of the run's environment. */
  environment_notice: string | null;
}

/** Why Resume is refused (`actions.resume.reason`, and the `reason` of a `409`). */
export type ResumeReason =
  | "running"
  | "head_unverified"
  | "resume_in_progress"
  | "cli_observed"
  | "not_failed_or_cancelled"
  | "launch_dir_refused"
  | "session_id_refused";

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

/** A process's or rule's status (api §5 note of 2026-11-07; ui-spec §5.2). */
export type ProcessStatus =
  | "pending"
  | "running"
  | "done"
  | "failed"
  | "stopped"
  | "awaiting_checkpoint"
  | "not_needed"
  | "up_to_date"
  | "no_tasks";

/** Schema `ProcessEfficiency`: over its tasks' last attempts; ratios, 0.63 for 63 %. */
export interface ProcessEfficiency {
  jobs: { done: number; total: number };
  measured: number;
  cpu_mean: number | null;
  cpu_max: number | null;
  mem_mean: number | null;
  mem_max: number | null;
  requested: { cpus: number | null; mem_bytes: number | null; time_limit_s: number | null; varies: boolean };
  used: { peak_rss_bytes_max: number | null; elapsed_s_max: number | null };
}

/** Schema `Process`. The fields of P1 Task 34 are optional until its screens (Task 35). */
export interface Process {
  process: string;
  stage_id: string | null;
  counts: Counts;
  retries: number;
  status?: ProcessStatus;
  is_checkpoint?: boolean;
  lower_bound?: boolean;
  efficiency?: ProcessEfficiency;
  /** 0 first: the rule graph's topological order, else the list's (FU-P3-82). */
  pipeline_order?: number;
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

/** Schema `SlurmRequest`: what the engine asked SLURM for. */
export interface SlurmRequest {
  partition: string | null;
  account: string | null;
  qos: string | null;
  cpus: number | null;
  mem_bytes: number | null;
  mem_per_cpu_bytes: number | null;
  time_limit_s: number | null;
  gres: string | null;
  constraint: string | null;
  nodes: number | null;
  tasks: number | null;
}

/** Schema `SlurmAllocated`: what SLURM gave the job, from `sacct` once it ended. */
export interface SlurmAllocated {
  partition: string | null;
  account: string | null;
  qos: string | null;
  ncpus: number | null;
  req_mem_bytes: number | null;
  time_limit_s: number | null;
  alloc_tres: string | null;
  nnodes: number | null;
}

/** Schema `Slurm`: `custom_options` when `slurm_extra` or `clusterOptions` was set (never the
 * text). */
export interface Slurm {
  request: SlurmRequest;
  allocated: SlurmAllocated | null;
  custom_options: boolean | null;
}

/** Schema `Efficiency`: one job's CPU and memory efficiency (schedulers §3.6). */
export interface Efficiency {
  cpu: number | null;
  mem: number | null;
  elapsed_s: number | null;
  peak_rss_bytes: number | null;
  state: "running" | "pending_accounting" | "available" | "unavailable";
  source: "sacct" | "trace" | "benchmark" | null;
  reason: "local" | "no_job_id" | "accounting_off" | "not_found" | "cached" | null;
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
  /** Null on a local run (P1 Task 34; optional until Task 35). */
  slurm?: Slurm | null;
  efficiency?: Efficiency;
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

/** Schema `TaskOutput`: one output of a Snakemake job (P1 Task 34). */
export interface TaskOutput {
  path: string;
  state: "present" | "not_yet" | "absent" | "temp_removed" | "tbd";
  protected: boolean;
  removed_at: string | null;
}

/** Schema `TaskFiles`: `GET /tasks/{id}/attempts/{n}/files` (P1 Task 28). */
export interface TaskFiles {
  task_id: string;
  attempt: number;
  work_dir: string | null;
  native_id: string | null;
  files: TaskFile[];
  /** Snakemake's outputs; null for a Nextflow attempt (optional until P1 Task 35). */
  outputs?: TaskOutput[] | null;
}

export type LogSource = "head-out" | "head-err" | "engine";

export interface FieldError {
  field: string;
  message: string;
}

/** An RFC 9457 problem; a 422 carries `errors` with a dotted `field` (inbox #86 rule 3), a 409
 * of `:relaunch` its `reason` (api §5.1). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly errors: FieldError[] = [],
    readonly reason: string | null = null,
    /** The problem's `type` slug, such as `environment-exists` (api §5.4). */
    readonly slug: string | null = null,
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
    const reason = typeof body?.reason === "string" ? body.reason : null;
    const slug = typeof body?.type === "string" ? body.type.replace("/problems/", "") : null;
    throw new ApiError(response.status, detail, Array.isArray(body?.errors) ? body.errors : [], reason, slug);
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

/** Resume: a child run in the same launch directory (`:relaunch` with `mode: resume`, api §5.1). */
export function resumeRun(id: string): Promise<RunDetail> {
  return call(`${run(id)}:relaunch`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ mode: "resume" }),
  });
}

export function getLaunchTemplate(id: string, signal?: AbortSignal): Promise<LaunchTemplate> {
  return call(`${run(id)}:launch-template`, { signal });
}

/** A Nextflow attempt's work directory, read in place of the run's results by the same calls
 * (`GET /tasks/{id}/attempts/{n}/workdir`, api §5.3, FU-P3-85e): no reports, no report viewer. */
export interface WorkRoot {
  task: string;
  attempt: number;
}
const tree = (id: string, work?: WorkRoot) =>
  work ? `/tasks/${encodeURIComponent(work.task)}/attempts/${work.attempt}/workdir` : `${run(id)}/results`;

/** One folder of the run's results, or of `work`, `path` relative to its root ("" for the root);
 * a work directory's listing has no `reports`. */
export function listResults(id: string, path: string, signal?: AbortSignal, work?: WorkRoot): Promise<Results> {
  return call(`${tree(id, work)}${query({ path })}`, { signal });
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

/** A results path in a URL: each part encoded, so `?`, `#`, `%` and `%2F` stay in the name. */
const resultPath = (path: string) => path.split("/").map(encodeURIComponent).join("/");

/** Where a results file is served: an HTML report with the sandbox CSP of req. 14 (for the
 * report viewer's iframe), any other file, or `download`, as an attachment; `as: "image"` for
 * the preview's `<img>` (api §5.3). */
export const resultUrl = (id: string, path: string, opts: { download?: boolean; as?: "image" | "tiff" } = {}, work?: WorkRoot) =>
  `${API}${tree(id, work)}/raw/${resultPath(path)}${query({ download: opts.download ? "true" : null, as: opts.as })}`;

/** Where a results file is read as text (api §5.3). */
export const resultTextUrl = (id: string, path: string, tail?: number, work?: WorkRoot) => `${API}${tree(id, work)}/text/${resultPath(path)}${query({ tail })}`;

/** The facts of one results path (api §5.3). */
export function statResult(id: string, path: string, signal?: AbortSignal, work?: WorkRoot): Promise<ResultStat> {
  return call(`${tree(id, work)}/stat/${resultPath(path)}`, { signal });
}

/** A text read: `next` is the byte after the last one read (the `Content-Range` last byte + 1)
 * and `size` the file's, for a Range read; both null for a tail read. */
export interface TextRead {
  text: string;
  next: number | null;
  size: number | null;
}

const CONTENT_RANGE = /^bytes (\d+)-(\d+)\/(\d+)$/;

/** A results file as text: bytes `from` to `to` with one Range, or its last `tail` bytes. A
 * refusal is an ApiError with its status and the server's text. */
export async function readResultText(
  id: string,
  path: string,
  opts: { from?: number; to?: number; tail?: number },
  signal?: AbortSignal,
  work?: WorkRoot,
): Promise<TextRead> {
  const headers = opts.from === undefined ? undefined : { range: `bytes=${opts.from}-${opts.to ?? ""}` };
  const response = await fetch(resultTextUrl(id, path, opts.tail, work), { signal, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? body?.title ?? `HTTP ${response.status}`);
  }
  const text = await response.text();
  const range = CONTENT_RANGE.exec(response.headers.get("content-range") ?? "");
  return range ? { text, next: Number(range[2]) + 1, size: Number(range[3]) } : { text, next: null, size: null };
}

export function launch(body: LaunchBody): Promise<Launched> {
  return call("/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** Schema `EnvironmentItem` (api §5.4): a built-in or one of `environments.toml`'s. */
export interface EnvironmentItem {
  name: string;
  label: string | null;
  executor: "local" | "slurm";
  builtin: boolean;
  default: boolean;
  usable: boolean;
  unusable_reason: string | null;
  slurm: NonNullable<RunEnvironment["slurm"]> | null;
  local: NonNullable<RunEnvironment["local"]> | null;
  profiles: { nextflow: string | null; snakemake: string | null };
  etag: string;
}
export type EnvironmentBody = Omit<EnvironmentItem, "builtin" | "default" | "usable" | "unusable_reason" | "etag">;

/** Schema `EnvironmentList`. */
export interface EnvironmentList {
  items: EnvironmentItem[];
  default: string;
  file: { path: string; state: "missing" | "ok" | "refused" | "invalid" | "unreachable"; detail: string | null };
}

const env = (name: string) => `/environments/${encodeURIComponent(name)}`;
const sendJson = (method: string, body: unknown, etag?: string): RequestInit => ({
  method,
  headers: { "content-type": "application/json", ...(etag ? { "if-match": etag } : {}) },
  body: JSON.stringify(body),
});

export const listEnvironments = (signal?: AbortSignal): Promise<EnvironmentList> => call("/environments", { signal });
export const getEnvironment = (name: string, signal?: AbortSignal): Promise<EnvironmentItem> => call(env(name), { signal });
export const createEnvironment = (body: EnvironmentBody): Promise<EnvironmentItem> => call("/environments", sendJson("POST", body));
export const replaceEnvironment = (body: EnvironmentBody, etag: string): Promise<EnvironmentItem> =>
  call(env(body.name), sendJson("PUT", body, etag));
export const deleteEnvironment = (name: string, etag: string): Promise<null> =>
  call(env(name), { method: "DELETE", headers: { "if-match": etag } });
export const makeDefault = (name: string): Promise<null> => call(`${env(name)}:make-default`, { method: "POST" });
