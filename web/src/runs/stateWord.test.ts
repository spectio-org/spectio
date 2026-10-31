import { expect, test } from "vitest";
import type { Stage } from "../api";
import {
  duration,
  isTerminal,
  processWord,
  runWord,
  shortId,
  stageWord,
  stagesLine,
  when,
} from "./stateWord";

test("run states read as the words of ui-spec §3.1", () => {
  expect(runWord("queued")).toBe("Queued");
  expect(runWord("running")).toBe("Running");
  expect(runWord("awaiting_review")).toBe("Awaiting review");
  expect(runWord("cancelling")).toBe("Cancelling");
  expect(runWord("succeeded")).toBe("Succeeded");
  expect(runWord("failed")).toBe("Failed");
  expect(runWord("cancelled")).toBe("Cancelled");
  expect(isTerminal("succeeded") && isTerminal("failed") && isTerminal("cancelled")).toBe(true);
  expect(isTerminal("cancelling")).toBe(false);
});

test("a process reads Pending, Running, Done or Failed from its task counts", () => {
  expect(processWord({}, false)).toBe("Pending");
  expect(processWord({ pending: 3, submitted: 1 }, false)).toBe("Pending");
  expect(processWord({ succeeded: 2, running: 1 }, false)).toBe("Running");
  expect(processWord({ succeeded: 2, pending: 1 }, false)).toBe("Running");
  expect(processWord({ succeeded: 2, cached: 3 }, false)).toBe("Done");
  expect(processWord({ succeeded: 2, failed: 1, running: 1 }, false)).toBe("Failed");
});

test("on an ended run, an unfinished process is Stopped and one that never started is Not run", () => {
  expect(processWord({ succeeded: 2, aborted: 1 }, true)).toBe("Stopped");
  expect(processWord({ running: 1 }, true)).toBe("Stopped");
  expect(processWord({ pending: 4 }, true)).toBe("Not run");
  expect(processWord({}, true)).toBe("Not run");
  expect(processWord({ succeeded: 4 }, true)).toBe("Done");
  expect(processWord({ failed: 1, aborted: 2 }, true)).toBe("Failed");
});

const stage = (state: Stage["state"], task_counts: Stage["task_counts"] = {}): Stage => ({
  id: "s",
  position: 1,
  name: "align",
  source: "detected",
  state,
  task_counts,
});

test("stage states map to the words of the ui-spec §4.4 note", () => {
  expect(stageWord(stage("not_started"), false)).toBe("Pending");
  expect(stageWord(stage("running"), false)).toBe("Running");
  expect(stageWord(stage("completed"), true)).toBe("Done");
  expect(stageWord(stage("failed", { failed: 1 }), true)).toBe("Failed");
  expect(stageWord(stage("failed", { succeeded: 3, aborted: 1 }), true)).toBe("Stopped");
  expect(stageWord(stage("skipped"), true)).toBe("Not run");
  expect(stageWord(stage("running"), true)).toBe("Stopped");
  expect(stageWord(stage("not_started"), true)).toBe("Not run");
});

test('the header line of a run with stages reads "n of m stages done · k running"', () => {
  const stages = [stage("completed"), stage("completed"), stage("running"), stage("not_started")];
  expect(stagesLine(stages)).toBe("2 of 4 stages done · 1 running");
  expect(stagesLine([])).toBeNull();
});

test("the short id is the last six characters of the ULID", () => {
  expect(shortId("run_01JBC6Q4ZK7M8N2P3R5S7T9V1W")).toBe("7T9V1W");
});

test("durations and times read as on the boards", () => {
  const start = new Date(2026, 9, 31, 7, 40, 0);
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 7, 40, 12).toISOString())).toBe("12 s");
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 8, 18, 0).toISOString())).toBe("38 min");
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 8, 45, 0).toISOString())).toBe("1 h 05");
  expect(duration(null, null)).toBe("—");
  const now = new Date(2026, 9, 31, 12, 0, 0);
  expect(when(new Date(2026, 9, 31, 9, 2).toISOString(), now)).toBe("Today 09:02");
  expect(when(new Date(2026, 9, 25, 18, 10).toISOString(), now)).toBe("Sun 18:10");
  expect(when(new Date(2026, 8, 1, 6, 5).toISOString(), now)).toBe("2026-09-01 06:05");
  expect(when(null, now)).toBe("—");
});

test("UX-PAR-16: a failed run's context is never blank", async () => {
  const { stateContext } = await import("./RunState");
  const { run } = await import("../testing");
  const failed = (failure: unknown, failedTasks = 2) =>
    stateContext(run({ state: "failed", failure, summary: { tasks: { done: 3, total: 5, failed: failedTasks, cached: 0 }, last_failure: null } }) as never);
  expect(failed({ class: "tool_error", message: "" })).toBe("tool error · 2 tasks failed");
  expect(failed({ class: "head_lost", message: "" }, 0)).toBe("head lost");
  expect(failed({ class: "tool_error", message: "exit 1 · DEEPVARIANT (NA12878)" })).toBe("tool error · exit 1 · DEEPVARIANT (NA12878)");
  expect(failed(null, 0)).toBe("failed");
  const snake = run({ state: "failed", failure: { class: "engine_fault", message: "" }, workflow: { engine: "snakemake" }, summary: { tasks: { done: 1, total: 2, failed: 1, cached: 0 }, last_failure: null } });
  expect(stateContext(snake as never)).toBe("engine error · 1 job failed");
});

test("UX-PAR-20: Snakemake runs read jobs and rules", async () => {
  const { words } = await import("./stateWord");
  expect(words("snakemake")).toMatchObject({ unit: "job", units: "jobs", group: "rule", groups: "rules", Group: "Rule" });
  expect(words("nextflow")).toMatchObject({ unit: "task", units: "tasks", group: "process", Groups: "Processes" });
  expect(words(null).units).toBe("tasks");
});
