// The hand-written client against the OpenAPI snapshot (FU-P3-21): each sample below satisfies
// its TypeScript type exactly (`satisfies` refuses a missing or extra field), and its fields must
// be the schema's properties, so a field added to or dropped from a response model fails here.
import { expect, test } from "vitest";
import snapshot from "../../packages/spectio-server/openapi/0.0.1.json";
import type { Process, Run, RunDetail, ServerVersion, Stage, Task } from "./api";

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

const SAMPLES: Record<string, object> = {
  Run: run,
  RunDetail: { ...run, params: {}, stages_note: null } satisfies RunDetail,
  WorkflowRef: run.workflow,
  Head: run.head,
  RunSummary: run.summary,
  TaskSummary: run.summary.tasks,
  ServerVersion: { version: "", node: "", runs_root: "", account: "", executor: "" } satisfies ServerVersion,
  Process: { process: "", stage_id: null, counts: {}, retries: 0 } satisfies Process,
  Stage: { id: "", position: 0, name: null, source: "detected", state: "running", task_counts: {} } satisfies Stage,
  Task: { id: "", process: "", tag: null, name: null, state: "failed", stage_id: null } satisfies Task,
};

test.each(Object.keys(SAMPLES))("the client's %s has the snapshot's fields", (name) => {
  const schema = schemas[name];
  expect(schema, name).toBeDefined();
  expect(Object.keys(SAMPLES[name]).sort()).toEqual(Object.keys(schema.properties).sort());
  expect([...(schema.required ?? [])].sort()).toEqual(Object.keys(schema.properties).sort());
});
