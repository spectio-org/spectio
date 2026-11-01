// The hand-written client against the OpenAPI snapshot (FU-P3-21): each sample below satisfies
// its TypeScript type exactly (`satisfies` refuses a missing or extra field), and its fields must
// be the schema's properties, so a field added to or dropped from a response model fails here.
import { expect, test } from "vitest";
import snapshot from "../../packages/spectio-server/openapi/0.0.1.json";
import type { Failure, Process, Resources, Run, RunDetail, Scheduler, ServerVersion, Stage, Task } from "./api";

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
  failure: null,
  head: { session: null, node: "", alive: false, exit_code: null },
  task_counts: {},
  summary: { tasks: { done: 0, total: 0, failed: 0, cached: 0 }, last_failure: null, stage_mode: "quarters" },
} satisfies Run;

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

const SAMPLES: Record<string, object> = {
  Run: run,
  RunDetail: { ...run, params: {}, stages_note: null, failures: [failure], failures_total: 1 } satisfies RunDetail,
  Failure: failure,
  Scheduler: scheduler,
  Resources: resources,
  WorkflowRef: run.workflow,
  Head: run.head,
  RunSummary: run.summary,
  TaskSummary: run.summary.tasks,
  ServerVersion: { version: "", node: "", runs_root: "", account: "", executor: "" } satisfies ServerVersion,
  Process: { process: "", stage_id: null, counts: {}, retries: 0 } satisfies Process,
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
  } satisfies Task,
};

test.each(Object.keys(SAMPLES))("the client's %s has the snapshot's fields", (name) => {
  const schema = schemas[name];
  expect(schema, name).toBeDefined();
  expect(Object.keys(SAMPLES[name]).sort()).toEqual(Object.keys(schema.properties).sort());
  expect([...(schema.required ?? [])].sort()).toEqual(Object.keys(schema.properties).sort());
});
