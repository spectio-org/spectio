// Each job's SLURM request and efficiency in the task sheet (P1 Task 35; ui-spec §4.4 note
// 2026-11-07; boards LiteTaskFiles, MLiteTaskFilesSheet, LiteTaskFilesStates L and M).
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const PROCESS = "NFCORE:RNASEQ:SUBREAD_FEATURECOUNTS";
const GIB = 1024 ** 3;
const RESOURCES = { cpus: 6, memory_bytes: 8 * GIB, time_s: 8 * 3600, realtime_s: 360, cpu_percent: 412, peak_rss_bytes: 8 * GIB, source: "trace" };
const REQUEST = { partition: "htc", account: null, qos: null, cpus: 6, mem_bytes: 8 * GIB, mem_per_cpu_bytes: null, time_limit_s: 8 * 3600, gres: null, constraint: null, nodes: null, tasks: null };
const TASK = {
  id: "tsk_19",
  process: PROCESS,
  tag: "S19",
  name: "SUBREAD_FEATURECOUNTS (S19)",
  state: "failed",
  stage_id: null,
  attempt_n: 1,
  resources: RESOURCES,
  slurm: {
    request: REQUEST,
    allocated: { partition: "htc-el8", account: "demo", qos: "normal", ncpus: 6, req_mem_bytes: 8 * GIB, time_limit_s: 8 * 3600, alloc_tres: "cpu=6,mem=8G,node=1", nnodes: 1 },
    custom_options: true,
  },
  efficiency: { cpu: 0.69, mem: 1.0, elapsed_s: 360, peak_rss_bytes: 8 * GIB, state: "available", source: "sacct", reason: null },
};

function open(task: Record<string, unknown>, more: Record<string, unknown> = {}) {
  const mock = serve({
    ...more,
    [`${URL_}/processes`]: { items: [{ process: PROCESS, stage_id: null, counts: { failed: 1 }, retries: 0 }] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: { items: [task], next: null },
    [`${URL_}/logs`]: () => new Response(""),
    [`/api/v1/tasks/tsk_19/attempts/1/files`]: { task_id: "tsk_19", attempt: 1, work_dir: null, native_id: "8812477", files: [] },
    [URL_]: { ...DETAIL, ...run({ state: "failed" }), params: {}, failures: [], failures_total: 0 },
  });
  app(`/runs/${ID}?tab=tasks`);
  return mock;
}

/** A block's facts as [term, value] pairs. */
const factsOf = (region: HTMLElement) => within(region).getAllByRole("term").map((dt) => [dt.textContent, dt.nextElementSibling?.textContent]);

async function sheet() {
  await userEvent.click(await screen.findByRole("button", { name: "Files of SUBREAD_FEATURECOUNTS (S19), attempt 1" }));
  return screen.findByRole("dialog", { name: "SUBREAD_FEATURECOUNTS (S19)" });
}

test("SLURM facts show the request, 'Custom sbatch options set' without text, and 'differs from the request'", async () => {
  open(TASK);
  const drawer = await sheet();
  const slurm = within(drawer).getByRole("region", { name: "SLURM" });
  expect(factsOf(slurm)).toEqual([
    ["Partition", "htc"],
    ["CPUs", "6"],
    ["Memory", "8 GB"],
    ["Time limit", "8 h"],
    ["Allocated", "htc-el8 · demo · normal · 6 CPUs · 8 GB · 8 h · cpu=6,mem=8G,node=1 differs from the request"],
    ["Custom sbatch options set", "yes"],
  ]);
  expect(drawer.textContent).not.toMatch(/slurm_extra|clusterOptions|--/);
  const efficiency = within(drawer).getByRole("region", { name: "Efficiency" });
  expect(factsOf(efficiency)).toEqual([
    ["CPU · memory", "69 % · 100 % near limit · from sacct"],
    ["Elapsed · time limit", "6 min of 8 h"],
    ["Peak · memory asked", "8 GB of 8 GB"],
  ]);
});

test("efficiency reads 'Waiting for SLURM accounting (sacct)' before sacct answers", async () => {
  open({ ...TASK, slurm: { request: REQUEST, allocated: null, custom_options: null }, efficiency: { cpu: 0.6, mem: 0.12, elapsed_s: 360, peak_rss_bytes: GIB, state: "pending_accounting", source: "trace", reason: null } });
  const drawer = await sheet();
  const efficiency = within(drawer).getByRole("region", { name: "Efficiency" });
  expect(within(efficiency).getByText("Waiting for SLURM accounting (sacct)")).toBeInTheDocument();
  expect(factsOf(efficiency)[0]).toEqual(["CPU · memory", "60 % · 12 % low · from the Nextflow trace"]);
  const slurm = within(drawer).getByRole("region", { name: "SLURM" });
  expect(within(slurm).queryByText("Allocated")).toBeNull();
  expect(within(slurm).queryByText("Custom sbatch options set")).toBeNull();
});

test("a local run has no SLURM block and says why there is no accounting", async () => {
  open({ ...TASK, slurm: null, efficiency: { cpu: null, mem: null, elapsed_s: 360, peak_rss_bytes: null, state: "unavailable", source: null, reason: "local" } });
  const drawer = await sheet();
  expect(within(drawer).queryByRole("region", { name: "SLURM" })).toBeNull();
  expect(within(drawer).getByText("No accounting for this job (local run)")).toBeInTheDocument();
});

test("a running job's efficiency is measured when it ends", async () => {
  open({ ...TASK, state: "running", efficiency: { cpu: null, mem: null, elapsed_s: 120, peak_rss_bytes: null, state: "running", source: null, reason: null } });
  const drawer = await sheet();
  const efficiency = within(drawer).getByRole("region", { name: "Efficiency" });
  expect(within(efficiency).getByText("Measured when the job ends")).toBeInTheDocument();
  expect(factsOf(efficiency)).toEqual([["Elapsed · time limit", "2 min of 8 h"]]);
});

test("opening a job's SLURM facts reads that one task, so sacct is asked while the run is live (CON-SLURM-POLL-01)", async () => {
  const mock = open(TASK);
  await sheet();
  expect(fetched(mock)).toContain(`${URL_}/tasks?task=tsk_19&limit=1`);
});

test("the sheet shows the one task's fresh SLURM facts, not the list's", async () => {
  const fresh = { ...TASK, efficiency: { ...TASK.efficiency, cpu: 0.42 } };
  open(TASK, { [`${URL_}/tasks?task=tsk_19`]: { items: [fresh], next: null } });
  const drawer = await sheet();
  const efficiency = within(drawer).getByRole("region", { name: "Efficiency" });
  expect(await within(efficiency).findByText(/^42 %/)).toBeInTheDocument();
});

test("a task with no SLURM block asks nothing more when opened", async () => {
  const mock = open({ ...TASK, slurm: null });
  await sheet();
  expect(fetched(mock).filter((u) => u.includes("task=tsk_19"))).toEqual([]);
});
