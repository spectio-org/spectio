// The hand-written client against the OpenAPI snapshot (FU-P3-21): each sample below satisfies
// its TypeScript type exactly (`satisfies` refuses a missing or extra field), and its fields must
// be the schema's properties, so a field added to or dropped from a response model fails here.
import { expect, test } from "vitest";
import snapshot from "../../packages/spectio-server/openapi/0.0.1.json";
import type { RunEnvironment, CodeLoading, Efficiency, EngineSettings, Failure, LaunchTemplate, Me, Notification, Notifications, Process, ProcessEfficiency, ResultEntry, ResultReport, ResultStat, Results, Resources, Run, RunConfigFile, RunDefaultResources, RunDetail, Scheduler, ServerVersion, Slurm, SlurmAllocated, SlurmRequest, Stage, Task, TaskFile, TaskFiles, TaskOutput } from "./api";

const schemas = snapshot.components.schemas as unknown as Record<
  string,
  { properties: Record<string, unknown>; required?: string[] }
>;

const run = {
  id: "run_x",
  name: null,
  state: "queued",
  origin: null,
  created_at: "",
  started_at: null,
  ended_at: null,
  workflow: { engine: null, engine_version: null, location: "", name: null, version: null },
  profiles: [],
  environment: {
    name: "slurm",
    label: "SLURM (from spectio init)",
    executor: "slurm",
    slurm: { partition: "htc", account: null, time_min: null, mem_mib: null },
    local: { cpus: null, mem_mib: null },
    state: "recorded",
  },
  pinned: false,
  failure: null,
  head: { session: null, node: "", alive: false, exit_code: null, checked: true },
  task_counts: {},
  summary: {
    tasks: { done: 0, total: 0, failed: 0, cached: 0, lower_bound: false },
    last_failure: null,
    stage_mode: "quarters",
    open_checkpoints: [],
    dag_updates: 0,
  },
} satisfies Run;

const me = {
  principal: { user: "", uid: 0 },
  session: { started_at: null, expires_at: null },
  paths: { config_file: "", data_dir: "", db_dir: "", observed_dir: "" },
} satisfies Me;

const scheduler = {
  state: null,
  reason: null,
  state_source: null,
  max_rss_bytes: null,
  req_mem_bytes: null,
  elapsed_s: null,
  time_limit_s: null,
  usage_source: null,
  accounting: "unavailable",
} satisfies Scheduler;

const failure = {
  task_id: "",
  process: "",
  tag: null,
  attempt_n: 1,
  native_id: null,
  exit_code: null,
  message: null,
  log_tail: null,
  scheduler,
  work_dir: null,
} satisfies Failure;

const resources = {
  cpus: null,
  memory_bytes: null,
  time_s: null,
  realtime_s: null,
  cpu_percent: null,
  peak_rss_bytes: null,
  source: null,
} satisfies Resources;

const request = {
  partition: null,
  account: null,
  qos: null,
  cpus: 2,
  mem_bytes: null,
  mem_per_cpu_bytes: null,
  time_limit_s: null,
  gres: null,
  constraint: null,
  nodes: null,
  tasks: null,
} satisfies SlurmRequest;

const allocated = {
  partition: null,
  account: null,
  qos: null,
  ncpus: 2,
  req_mem_bytes: null,
  time_limit_s: null,
  alloc_tres: null,
  nnodes: null,
} satisfies SlurmAllocated;

const slurm = { request, allocated, custom_options: null } satisfies Slurm;

const efficiency = {
  cpu: 0.4,
  mem: null,
  elapsed_s: 65,
  peak_rss_bytes: null,
  state: "available",
  source: "sacct",
  reason: null,
} satisfies Efficiency;

const processEfficiency = {
  jobs: { done: 1, total: 2 },
  measured: 1,
  pending_accounting: 0,
  cpu_mean: 0.4,
  cpu_max: 0.4,
  mem_mean: null,
  mem_max: null,
  requested: { cpus: 2, mem_bytes: null, time_limit_s: null, varies: false },
  used: { peak_rss_bytes_max: null, elapsed_s_max: 65 },
} satisfies ProcessEfficiency;

const output = { path: "out/a.txt", state: "temp_removed", protected: false, removed_at: "" } satisfies TaskOutput;
const engineSettings = { cleanup: null, notemp: null } satisfies EngineSettings;

const taskFile = { name: ".command.log", kind: "job_log", size: null, mtime: null, state: "not_yet", note: null } satisfies TaskFile;

const SAMPLES: Record<string, object> = {
  TaskFile: taskFile,
  TaskFiles: { task_id: "", attempt: 1, work_dir: null, native_id: null, files: [taskFile], outputs: [output] } satisfies TaskFiles,
  TaskOutput: output,
  EngineSettings: engineSettings,
  SlurmRequest: request,
  SlurmAllocated: allocated,
  Slurm: slurm,
  Efficiency: efficiency,
  ProcessEfficiency: processEfficiency,
  JobCount: processEfficiency.jobs,
  Requested: processEfficiency.requested,
  Used: processEfficiency.used,
  Run: run,
  RunDetail: {
    ...run,
    params: {},
    stages_note: null,
    failures: [failure],
    failures_total: 1,
    command: null,
    parent_run_id: null,
    resumed_as: [],
    actions: { resume: { allowed: false, reason: "running" } },
    results_dir: null,
    engine_settings: engineSettings,
    default_resources: null,
    config_file: null,
  } satisfies RunDetail,
  RunDefaultResources: { cpus: null, mem_mib: null, time_min: null, state: "recorded" } satisfies RunDefaultResources,
  RunConfigFile: {
    path: null,
    kept_as: null,
    sha256: null,
    size: null,
    includes: null,
    state: "recorded",
  } satisfies RunConfigFile,
  ResultEntry: { name: "", type: "file", size: null, mtime: null } satisfies ResultEntry,
  ResultReport: { path: "", title: "", group: null } satisfies ResultReport,
  Results: { root: "", path: "", exists: true, entries: [], truncated: false, reports: [] } satisfies Results,
  ResultStat: { root: "", path: "", name: "", type: "file", size: null, mtime: null } satisfies ResultStat,
  CodeLoading: { field: "", value: "", writable_by_others: false } satisfies CodeLoading,
  LaunchTemplate: {
    workflow: { location: "", revision: null, engine: "nextflow" },
    profiles: [],
    params: {},
    non_default: [],
    code_loading: [],
    environment: "local",
    environment_notice: null,
    default_resources: null,
    config_file: null,
  } satisfies LaunchTemplate,
  TemplateWorkflow: { location: "", revision: null, engine: "nextflow" },
  Failure: failure,
  Scheduler: scheduler,
  Resources: resources,
  WorkflowRef: run.workflow,
  RunEnvironment: run.environment satisfies RunEnvironment,
  EnvironmentSlurm: run.environment.slurm,
  EnvironmentLocal: run.environment.local,
  Head: run.head,
  RunSummary: run.summary,
  TaskSummary: run.summary.tasks,
  ServerVersion: { version: "", node: "", runs_root: "", account: "", executor: "" } satisfies ServerVersion,
  Me: me,
  Notification: { id: "", kind: "run_failed", run_id: "", run_name: null, at: "", read: false } satisfies Notification,
  Notifications: { items: [], unread: 0, read_up_to: null } satisfies Notifications,
  Principal: me.principal,
  MeSession: me.session,
  MePaths: me.paths,
  Process: {
    process: "",
    stage_id: null,
    counts: {},
    retries: 0,
    status: "awaiting_checkpoint",
    is_checkpoint: false,
    lower_bound: true,
    efficiency: processEfficiency,
    pipeline_order: 0,
  } satisfies Process,
  Stage: { id: "", position: 0, name: null, source: "detected", state: "running", task_counts: {} } satisfies Stage,
  Task: {
    id: "",
    process: "",
    tag: null,
    name: null,
    state: "failed",
    stage_id: null,
    attempt_n: 1,
    resources,
    slurm,
    efficiency,
  } satisfies Task,
};

test.each(Object.keys(SAMPLES))("the client's %s has the snapshot's fields", (name) => {
  const schema = schemas[name];
  expect(schema, name).toBeDefined();
  expect(Object.keys(SAMPLES[name]).sort()).toEqual(Object.keys(schema.properties).sort());
  expect([...(schema.required ?? [])].sort()).toEqual(Object.keys(schema.properties).sort());
});
