// "Why it failed" per job (P1 Task 32 on Task 29's `failures`; ui-spec §4.4 note 2026-10-28,
// Failure summary; boards LiteRunFailed, MLiteRunFailed): each job that failed on its last attempt,
// its attempt, job ID, exit code, SLURM state and where it came from, memory and time asked and used,
// the engine's message unchanged, its last lines, Open job files and Copy work directory.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const GIB = 1024 ** 3;
const WORK = "/scratch/amartin/spectio-runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/work/9d/77c2140f";
const SCHEDULER = {
  state: "OUT_OF_MEMORY",
  reason: "Step 0: OutOfMemory",
  state_source: "sacct",
  max_rss_bytes: 2 * GIB,
  req_mem_bytes: 2 * GIB,
  elapsed_s: 4320,
  time_limit_s: 4 * 3600,
  usage_source: "sacct",
  accounting: "available",
};
const FAILURE = {
  task_id: "tsk_1",
  process: "NFCORE:RNASEQ:ALIGN",
  tag: "S00",
  attempt_n: 2,
  native_id: "8812402",
  exit_code: 137,
  message: "Process `ALIGN (S00)` terminated with an error exit status (137)",
  log_tail: "line 1\nslurmstepd: error: Detected 1 oom_kill event in StepId=8812402.batch\n",
  scheduler: SCHEDULER,
  work_dir: WORK,
};

function failed(over: Record<string, unknown> = {}, more: Record<string, unknown> = {}) {
  return serve({
    "/api/v1/version": { ...VERSION, executor: "slurm" },
    [`${URL_}/processes`]: { items: [{ process: "NFCORE:RNASEQ:ALIGN", stage_id: null, counts: { failed: 1, succeeded: 3 }, retries: 1 }] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: { items: [], next: null },
    [`${URL_}/logs`]: () => new Response(""),
    "/api/v1/tasks/tsk_1/attempts/2/files/": () => new Response("oom\n"),
    "/api/v1/tasks/tsk_1/attempts/2/files": {
      task_id: "tsk_1",
      attempt: 2,
      work_dir: WORK,
      native_id: "8812402",
      files: [{ name: ".command.log", kind: "job_log", size: 4, mtime: null, state: "present", note: null }],
    },
    [URL_]: {
      ...run({
        state: "failed",
        ended_at: "2026-10-31T08:00:00+00:00",
        failure: { class: "tool_error", message: "", task_id: "tsk_1", attempt_n: 2 },
        summary: { tasks: { done: 3, total: 4, failed: 1, cached: 0 }, last_failure: null, stage_mode: "quarters" },
      }),
      params: {},
      failures: [FAILURE],
      failures_total: 1,
      ...over,
    },
    ...more,
  });
}

const card = async (name = "ALIGN (S00), attempt 2") => screen.findByRole("article", { name });
const fact = (scope: HTMLElement, name: string) => within(scope).getByText(name).nextSibling;

test("failed run: Why it failed shows SLURM state, requested and used memory, last lines", async () => {
  failed();
  app(`/runs/${ID}`);
  const job = await card();
  expect(within(job).getByText("OUT_OF_MEMORY")).toBeInTheDocument();
  expect(fact(job, "Attempt")).toHaveTextContent("2");
  expect(fact(job, "SLURM job")).toHaveTextContent("8812402");
  expect(fact(job, "Exit code")).toHaveTextContent("137");
  expect(fact(job, "Memory, asked · used")).toHaveTextContent("2 GB · 2 GB near limit");
  expect(fact(job, "Time, limit · used")).toHaveTextContent("4 h · 1 h 12");
  expect(within(job).getByText(FAILURE.message)).toBeInTheDocument();
  expect(within(job).getByText("SLURM state: from sacct · Reason: Step 0: OutOfMemory · used: from sacct")).toBeInTheDocument();
  const tail = within(job).getByLabelText("ALIGN (S00), last lines");
  expect(tail).toHaveTextContent(/oom_kill event/);
  expect(within(job).getByRole("button", { name: "Copy the work directory of ALIGN (S00)" })).toBeInTheDocument();
});

test("Open job files opens the task sheet on its job log; Escape returns focus to the button", async () => {
  failed();
  app(`/runs/${ID}`);
  const open = within(await card()).getByRole("button", { name: "Open the job files of ALIGN (S00)" });
  await userEvent.click(open);
  const sheet = await screen.findByRole("dialog", { name: "ALIGN (S00)" });
  expect(await within(sheet).findByText("oom")).toBeInTheDocument();
  expect(within(sheet).getByRole("tab", { selected: true })).toHaveTextContent(".command.log");
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(open).toHaveFocus());
});

test("Snakemake: the state from the plugin's message, usage unavailable, Copy launch directory", async () => {
  const smk = {
    ...FAILURE,
    process: "bwa_mem",
    tag: "sample=WGS-07",
    message: null,
    work_dir: "/scratch/amartin/spectio-runs/x/launch",
    scheduler: { ...SCHEDULER, state_source: "engine_message", max_rss_bytes: null, elapsed_s: null, usage_source: null, accounting: "unavailable" },
  };
  failed({
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/p/wgs", name: "wgs", version: null },
    failures: [smk],
  });
  app(`/runs/${ID}`);
  const job = await card("bwa_mem (sample=WGS-07), attempt 2");
  expect(fact(job, "Memory, asked · used")).toHaveTextContent("2 GB · —");
  expect(
    within(job).getByText("SLURM state: from the Snakemake SLURM plugin's message · Reason: Step 0: OutOfMemory · used: SLURM accounting unavailable"),
  ).toBeInTheDocument();
  expect(within(job).getByRole("button", { name: "Copy the launch directory of bwa_mem (sample=WGS-07)" })).toBeInTheDocument();
});

test("sacct still asked: the line says so", async () => {
  failed({ failures: [{ ...FAILURE, scheduler: { ...SCHEDULER, state: null, reason: null, state_source: null, usage_source: null, max_rss_bytes: null, elapsed_s: null, accounting: "pending" } }] });
  app(`/runs/${ID}`);
  expect(within(await card()).getByText("SLURM state: asking sacct · used: asking sacct")).toBeInTheDocument();
});

test("the local executor: a process ID, no SLURM line, used from the Nextflow trace", async () => {
  failed(
    { failures: [{ ...FAILURE, native_id: "4242", scheduler: { ...SCHEDULER, state: null, reason: null, state_source: null, usage_source: "trace", accounting: "unavailable" } }] },
    { "/api/v1/version": VERSION },
  );
  app(`/runs/${ID}`);
  const job = await card();
  expect(fact(job, "Job ID")).toHaveTextContent("4242");
  expect(within(job).queryByText(/SLURM/)).toBeNull();
  expect(within(job).getByText("used: from the Nextflow trace")).toBeInTheDocument();
});

test("more failures than shown: 'Showing 1 of 12 failed tasks', and the failed tasks are a click away", async () => {
  failed({ failures_total: 12 });
  app(`/runs/${ID}`);
  const why = await screen.findByRole("region", { name: "Why it failed" });
  expect(await within(why).findByText("Showing 1 of 12 failed tasks.")).toBeInTheDocument();
  expect(within(why).getByRole("button", { name: "Tasks, filtered to Failed" })).toBeInTheDocument();
});

test("on the phone the cards are one column of label and value rows", async () => {
  viewport(390);
  failed();
  app(`/runs/${ID}`);
  const job = await card();
  expect(fact(job, "Exit code")).toHaveTextContent("137");
  expect(within(job).getByRole("button", { name: "Open the job files of ALIGN (S00)" })).toBeInTheDocument();
});
