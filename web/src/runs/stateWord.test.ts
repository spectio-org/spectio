import { expect, test } from "vitest";
import type { Stage } from "../api";
import {
  duration,
  formatDuration,
  isTerminal,
  taskWord,
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

test("a process reads what is happening now: Failed, Running, Queued, Pending, then Succeeded (#385)", () => {
  expect(processWord({}, false)).toBe("Pending");
  expect(processWord({ pending: 3 }, false)).toBe("Pending");
  // none running, one waiting in the scheduler
  expect(processWord({ pending: 3, submitted: 1 }, false)).toBe("Queued");
  expect(processWord({ submitted: 2 }, false)).toBe("Queued");
  expect(processWord({ succeeded: 2, running: 1 }, false)).toBe("Running");
  expect(processWord({ running: 1, submitted: 2 }, false)).toBe("Running");
  // some done and more to come reads Pending, not Running
  expect(processWord({ succeeded: 2, pending: 1 }, false)).toBe("Pending");
  expect(processWord({ succeeded: 2, submitted: 1 }, false)).toBe("Queued");
  expect(processWord({ succeeded: 2, cached: 3 }, false)).toBe("Succeeded");
  expect(processWord({ succeeded: 2, failed: 1, running: 1 }, false)).toBe("Failed");
});

test("on an ended run, an unfinished process is Stopped and one that never started is Not run", () => {
  expect(processWord({ succeeded: 2, aborted: 1 }, true)).toBe("Stopped");
  expect(processWord({ running: 1 }, true)).toBe("Stopped");
  expect(processWord({ pending: 4 }, true)).toBe("Not run");
  expect(processWord({}, true)).toBe("Not run");
  expect(processWord({ succeeded: 4 }, true)).toBe("Succeeded");
  expect(processWord({ failed: 1, aborted: 2 }, true)).toBe("Failed");
});

test("a task waiting in the scheduler reads Queued, one not yet sent Pending (#385)", () => {
  expect(taskWord("submitted")).toBe("Queued");
  expect(taskWord("pending")).toBe("Pending");
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
  expect(stageWord(stage("completed"), true)).toBe("Succeeded");
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

test("one duration format: s, min, h, then h and min (ui-spec §12.8)", () => {
  expect(formatDuration(null)).toBe("—");
  expect(formatDuration(14)).toBe("14 s");
  expect(formatDuration(6 * 60 + 5)).toBe("6 min");
  expect(formatDuration(38 * 60)).toBe("38 min");
  expect(formatDuration(4 * 3600)).toBe("4 h");
  expect(formatDuration(2 * 3600 + 3 * 60)).toBe("2 h 3 min");
});

test("durations and times read as on the boards", () => {
  const start = new Date(2026, 9, 31, 7, 40, 0);
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 7, 40, 12).toISOString())).toBe("12 s");
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 8, 18, 0).toISOString())).toBe("38 min");
  expect(duration(start.toISOString(), new Date(2026, 9, 31, 8, 45, 0).toISOString())).toBe("1 h 5 min");
  expect(duration(null, null)).toBe("—");
  const now = new Date(2026, 9, 31, 12, 0, 0);
  expect(when(new Date(2026, 9, 31, 9, 2).toISOString(), now)).toBe("Today 09:02");
  expect(when(new Date(2026, 9, 25, 18, 10).toISOString(), now)).toBe("Sun 18:10");
  expect(when(new Date(2026, 8, 1, 6, 5).toISOString(), now)).toBe("2026-09-01 06:05");
  expect(when(null, now)).toBe("—");
});

test("UX-PAR-16: a failed run's context is the class and the message, never blank (#385: no count)", async () => {
  const { stateContext } = await import("./RunState");
  const { run } = await import("../testing");
  const failed = (failure: unknown, failedTasks = 2) =>
    stateContext(run({ state: "failed", failure, summary: { tasks: { done: 3, total: 5, failed: failedTasks, cached: 0 }, last_failure: null, stage_mode: "quarters" } }) as never);
  expect(failed({ class: "tool_error", message: "" })).toBe("tool error · see the failed tasks");
  expect(failed({ class: "head_lost", message: "" }, 0)).toBe("head lost");
  expect(failed({ class: "tool_error", message: "exit 1 · DEEPVARIANT (NA12878)" })).toBe("tool error · exit 1 · DEEPVARIANT (NA12878)");
  expect(failed(null, 0)).toBe("failed");
  const snake = run({ state: "failed", failure: { class: "engine_fault", message: "" }, workflow: { engine: "snakemake" }, summary: { tasks: { done: 1, total: 2, failed: 1, cached: 0 }, last_failure: null, stage_mode: "quarters" } });
  expect(stateContext(snake as never)).toBe("engine error · see the failed jobs");
});

test("#385: a run's context does not repeat its word; a running run says when its jobs wait", async () => {
  const { stateContext } = await import("./RunState");
  const { run } = await import("../testing");
  const counts = (task_counts: Record<string, number>, engine = "snakemake", state = "running") =>
    stateContext(run({ state, task_counts, workflow: { engine } }) as never);
  expect(counts({ running: 3, submitted: 2 })).toBe("3 jobs running");
  expect(counts({ running: 1 }, "nextflow")).toBe("1 task running");
  expect(counts({ submitted: 5 })).toBe("all 5 jobs queued in the scheduler");
  expect(counts({ submitted: 1 }, "nextflow")).toBe("all 1 task queued in the scheduler");
  expect(counts({ submitted: 2, pending: 4 })).toBe("2 jobs queued in the scheduler");
  expect(counts({}, "snakemake", "succeeded")).toBe("");
  expect(counts({}, "snakemake", "cancelled")).toBe("");
});

test("UX-PAR-20: Snakemake runs read jobs and rules", async () => {
  const { words } = await import("./stateWord");
  expect(words("snakemake")).toMatchObject({ unit: "job", units: "jobs", group: "rule", groups: "rules", Group: "Rule" });
  expect(words("nextflow")).toMatchObject({ unit: "task", units: "tasks", group: "process", Groups: "Processes" });
  expect(words(null).units).toBe("tasks");
});

test("UX-PAR-33: one label for the server's executor", async () => {
  const { executorLabel } = await import("./stateWord");
  expect(executorLabel("slurm")).toBe("SLURM");
  expect(executorLabel("local")).toBe("Local");
  expect(executorLabel("pbs")).toBe("PBS");
});
