// Each job's files in the task sheet (P1 Task 32; ui-spec §4.4 note 2026-10-28, Job files; boards
// LiteTaskFiles, MLiteTaskFilesSheet and every panel of LiteTaskFilesStates), read from P1 Task 28's
// routes: the listing names each file with its state, a read returns its last 64 KiB as text.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, fetched, json, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const PROCESS = "NFCORE:RNASEQ:SUBREAD_FEATURECOUNTS";
const WORK = "/scratch/amartin/spectio-runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/work/9d/77c2140f5be3a1c96e04d2b88a7f13";
const GIB = 1024 ** 3;
const RESOURCES = { cpus: 6, memory_bytes: 8 * GIB, time_s: 8 * 3600, realtime_s: 360, cpu_percent: 412, peak_rss_bytes: 8 * GIB, source: "trace" };
const TASK = {
  id: "tsk_19",
  process: PROCESS,
  tag: "S19",
  name: "SUBREAD_FEATURECOUNTS (S19)" as string | null,
  state: "failed",
  stage_id: null,
  attempt_n: 2 as number | null,
  resources: RESOURCES,
};
const file = (name: string, kind: string, over: Record<string, unknown> = {}) => ({
  name,
  kind,
  size: 2458,
  mtime: "2026-10-31T08:42:00+00:00",
  state: "present",
  note: null,
  ...over,
});
const NF_FILES = [
  file(".command.sh", "script", { note: "May show values from your parameters or environment." }),
  file(".command.run", "wrapper", { note: "The value of every variable is hidden." }),
  file(".command.out", "stdout", { size: 3250586 }),
  file(".command.err", "stderr", { size: 0 }),
  file(".command.log", "job_log", { note: "May show values from your parameters or environment." }),
  file(".exitcode", "exit", { size: 4 }),
  file(".command.begin", "marker", { size: 0 }),
  file(".command.trace", "trace", { state: "absent", size: null, mtime: null }),
];
const listing = (files: unknown[], n = 2, work_dir: string | null = WORK) => ({ task_id: "tsk_19", attempt: n, work_dir, native_id: "8812477", files });
const FILES = `/api/v1/tasks/tsk_19/attempts`;

function detail(files: Record<string, unknown>, over: Record<string, unknown> = {}, task = TASK) {
  return serve({
    [`${URL_}/processes`]: { items: [{ process: PROCESS, stage_id: null, counts: { failed: 1 }, retries: 1 }] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: { items: [task], next: null },
    [`${URL_}/logs`]: () => new Response(""),
    [URL_]: { ...run({ state: "failed", ...over }), params: {}, failures: [], failures_total: 0 },
    ...files,
  });
}

/** The Tasks tab, then the row's Files button; returns the button and the sheet. */
async function openFiles(name = "Files of SUBREAD_FEATURECOUNTS (S19), attempt 2") {
  app(`/runs/${ID}?tab=tasks`);
  const button = await screen.findByRole("button", { name });
  await userEvent.click(button);
  const sheet = await screen.findByRole("dialog", { name: "SUBREAD_FEATURECOUNTS (S19)" });
  return { button, sheet };
}

const text = (body: string) => () => new Response(body, { headers: { "content-type": "text/plain" } });

test("Files opens the drawer on .command.log for a failed attempt; Escape returns focus to the row's button", async () => {
  const mock = detail({
    [`${FILES}/2/files/.command.log`]: text("Running\nslurmstepd: error: Detected 1 oom_kill event\n"),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { button, sheet } = await openFiles();
  const selected = within(sheet).getByRole("tab", { selected: true });
  expect(selected).toHaveTextContent(".command.log");
  const panel = within(sheet).getByRole("tabpanel", { name: ".command.log" });
  expect(await within(panel).findByText(/oom_kill event/)).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${FILES}/2/files/.command.log`);
  expect(within(sheet).getByText(WORK)).toBeInTheDocument();
  expect(within(sheet).getByRole("button", { name: "Copy the work directory" })).toBeInTheDocument();
  expect(within(panel).getByText("May show values from your parameters or environment.")).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(button).toHaveFocus());
});

test("tabs are buttons with role tab, in the spec's order; the drawer is aria-modal; More files shows the last two", async () => {
  detail({
    [`${FILES}/2/files/`]: text("x\n"),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { sheet } = await openFiles();
  expect(sheet).toHaveAttribute("aria-modal", "true");
  const tabs = within(sheet).getAllByRole("tab");
  for (const tab of tabs) expect(tab.tagName).toBe("BUTTON");
  expect(tabs.map((t) => t.textContent)).toEqual([".command.log", ".command.err", ".command.out", ".command.sh", ".command.run", ".exitcode"]);
  await userEvent.click(within(sheet).getByRole("button", { name: "More files" }));
  expect(within(sheet).getAllByRole("tab").map((t) => t.textContent)).toEqual([
    ".command.log", ".command.err", ".command.out", ".command.sh", ".command.run", ".exitcode", ".command.begin", ".command.trace · missing",
  ]);
  // arrow keys move between tabs (ARIA tabs pattern)
  within(sheet).getByRole("tab", { name: ".command.log" }).focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(within(sheet).getByRole("tab", { name: ".command.err" })).toHaveFocus();
  expect(within(sheet).getByRole("tab", { name: ".command.err" })).toHaveAttribute("aria-selected", "true");
});

test("the size line says 'whole file' or 'last 64 KiB of …'; Download says 'Download last 1 MiB' for a larger file", async () => {
  detail({
    [`${FILES}/2/files/`]: text("line\n"),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { sheet } = await openFiles();
  let panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText(/^whole file · 2\.4 KiB · written /)).toBeInTheDocument();
  const small = within(panel).getByRole("link", { name: "Download .command.log" });
  expect(small).toHaveTextContent(/^Download$/);
  expect(small).toHaveAttribute("href", `${FILES}/2/files/.command.log?tail=1048576&download=true`);
  await userEvent.click(within(sheet).getByRole("tab", { name: ".command.out" }));
  panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText(/^last 64 KiB of 3\.1 MiB · written /)).toBeInTheDocument();
  expect(within(panel).getByRole("link", { name: "Download last 1 MiB of .command.out" })).toHaveTextContent("Download last 1 MiB");
});

test("a missing file says why, in words, and its tab label carries the state", async () => {
  const states = [
    file(".command.log", "job_log", { state: "not_yet", size: null, mtime: null }),
    file(".command.err", "stderr", { state: "cleaned", size: null, mtime: null }),
    file(".command.out", "stdout", { state: "absent", size: null, mtime: null }),
    file(".command.sh", "script", { state: "deleted_after_success", size: null, mtime: null }),
  ];
  detail({ [`${FILES}/2/files`]: listing(states) }, {}, { ...TASK, state: "running" });
  const { sheet } = await openFiles();
  expect(within(sheet).getAllByRole("tab").map((t) => t.textContent)).toEqual([
    ".command.log · not yet", ".command.err · gone", ".command.out · missing", ".command.sh · deleted",
  ]);
  const says = async (tab: string, words: string) => {
    await userEvent.click(within(sheet).getByRole("tab", { name: tab }));
    expect(within(within(sheet).getByRole("tabpanel")).getByText(words)).toBeInTheDocument();
  };
  await says(".command.log · not yet", "The job has not written this file yet");
  await says(".command.err · gone", "The work directory was removed");
  await says(".command.out · missing", "The job ended without writing this file");
  await says(".command.sh · deleted", "Deleted by the Snakemake SLURM plugin after the job succeeded");
});

test("a read refused: 415 not text, 410 gone, 503 offline with Retry", async () => {
  let offline = true;
  detail({
    [`${FILES}/2/files/.command.log`]: () => json(415, { title: "Binary file" }),
    [`${FILES}/2/files/.command.err`]: () => json(410, { title: "Cleaned" }),
    [`${FILES}/2/files/.command.out`]: () => (offline ? json(503, { title: "File system not answering" }) : new Response("back\n")),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { sheet } = await openFiles();
  let panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText("This file is not text. Download it to open it")).toBeInTheDocument();
  await userEvent.click(within(sheet).getByRole("tab", { name: ".command.err" }));
  panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText("The work directory was removed")).toBeInTheDocument();
  await userEvent.click(within(sheet).getByRole("tab", { name: ".command.out" }));
  panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText("Spectio cannot read the cluster's files right now")).toBeInTheDocument();
  offline = false;
  await userEvent.click(within(panel).getByRole("button", { name: "Retry" }));
  expect(await within(within(sheet).getByRole("tabpanel")).findByText("back")).toBeInTheDocument();
});

test("a read that 404s while the listing still says present: Retry reads the file again (CR-P3T32-02)", async () => {
  let gone = true;
  detail({
    [`${FILES}/2/files/.command.log`]: () => (gone ? json(404, { title: "Not found" }) : new Response("here again\n")),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { sheet } = await openFiles();
  const panel = within(sheet).getByRole("tabpanel");
  expect(await within(panel).findByText("This file is not there now")).toBeInTheDocument();
  gone = false;
  await userEvent.click(within(panel).getByRole("button", { name: "Retry" }));
  expect(await within(within(sheet).getByRole("tabpanel")).findByText("here again")).toBeInTheDocument();
});

test("picking another attempt says 'Loading the files…' until its listing comes (CR-P3T32-03)", async () => {
  let answer: (r: Response) => void = () => undefined;
  detail({
    [`${FILES}/1/files`]: () => new Promise<Response>((resolve) => (answer = resolve)),
    [`${FILES}/2/files/`]: text("second try\n"),
    [`${FILES}/2/files`]: listing([file(".command.log", "job_log")]),
  });
  const { sheet } = await openFiles();
  expect(await within(sheet).findByText("second try")).toBeInTheDocument();
  await userEvent.selectOptions(within(sheet).getByRole("combobox", { name: "Attempt" }), "1");
  expect(within(sheet).getByText("Loading the files…")).toBeInTheDocument();
  expect(within(sheet).queryByText("This attempt has no file to show.")).toBeNull();
  answer(json(200, listing([], 1)));
  expect(await within(sheet).findByText("This attempt has no file to show.")).toBeInTheDocument();
});

test("the listing itself offline: the reason in words and Retry", async () => {
  let offline = true;
  detail({ [`${FILES}/2/files`]: () => (offline ? json(503, { title: "File system not answering" }) : json(200, listing([]))) });
  const { sheet } = await openFiles();
  expect(await within(sheet).findByText("Spectio cannot read the cluster's files right now")).toBeInTheDocument();
  offline = false;
  await userEvent.click(within(sheet).getByRole("button", { name: "Retry" }));
  expect(await within(sheet).findByText("This attempt has no file to show.")).toBeInTheDocument();
});

test("an earlier attempt's files: the Attempt select lists 1 to the last", async () => {
  const mock = detail({
    [`${FILES}/1/files/`]: text("first try\n"),
    [`${FILES}/1/files`]: listing([file(".command.log", "job_log")], 1),
    [`${FILES}/2/files/`]: text("second try\n"),
    [`${FILES}/2/files`]: listing([file(".command.log", "job_log")]),
  });
  const { sheet } = await openFiles();
  expect(await within(sheet).findByText("second try")).toBeInTheDocument();
  await userEvent.selectOptions(within(sheet).getByRole("combobox", { name: "Attempt" }), "1");
  expect(await within(sheet).findByText("first try")).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${FILES}/1/files`);
});

test("the task's facts: last attempt, resources with near limit in words; no note about Tasks 28 and 29", async () => {
  detail({ [`${FILES}/2/files`]: listing([]) });
  const { sheet } = await openFiles();
  const facts = within(sheet).getByRole("region", { name: "SUBREAD_FEATURECOUNTS (S19)" });
  expect(within(facts).getByText("Memory, asked · peak").nextSibling).toHaveTextContent("8 GB · 8 GB near limit");
  expect(within(facts).getByText("Time limit · duration").nextSibling).toHaveTextContent("8 h · 6 min");
  expect(within(facts).getByText("CPUs · CPU %").nextSibling).toHaveTextContent("6 · 412 %");
  expect(within(facts).getByText("Last attempt").nextSibling).toHaveTextContent("2");
  expect(within(sheet).queryByText(/Tasks 28 and 29/)).toBeNull();
});

test("Snakemake: the launch directory, the SLURM log first, and no job script", async () => {
  const smk = [
    file(".snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731209.log", "slurm_log"),
    file("logs/bwa_mem/WGS-07.log", "rule_log"),
  ];
  const launchDir = "/scratch/amartin/spectio-runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/launch";
  const mock = detail(
    {
      [`${FILES}/2/files/`]: text("[M::mem_process_seqs] Processed\n"),
      [`${FILES}/2/files`]: listing(smk, 2, launchDir),
    },
    { workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/p/wgs", name: "wgs", version: null } },
    { ...TASK, process: "bwa_mem", tag: "sample=WGS-07", name: null },
  );
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("button", { name: "Files of bwa_mem (sample=WGS-07), attempt 2" }));
  const sheet = await screen.findByRole("dialog", { name: "bwa_mem (sample=WGS-07)" });
  expect(within(sheet).getByText("Launch directory")).toBeInTheDocument();
  expect(within(sheet).getByRole("tab", { selected: true })).toHaveTextContent("SLURM log");
  expect(await within(sheet).findByText(/mem_process_seqs/)).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${FILES}/2/files/.snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731209.log`);
  expect(within(sheet).getByText("Snakemake keeps no job script; the rule's command is in the Snakefile.")).toBeInTheDocument();
});

test("on the phone the files are a native select labelled File", async () => {
  viewport(390);
  detail({
    [`${FILES}/2/files/`]: text("x\n"),
    [`${FILES}/2/files`]: listing(NF_FILES),
  });
  const { sheet } = await openFiles();
  const select = within(sheet).getByRole("combobox", { name: "File" });
  expect(select).toHaveValue(".command.log");
  expect(within(sheet).queryAllByRole("tab")).toHaveLength(0);
  expect(within(select).getByRole("option", { name: ".command.trace · missing" })).toBeInTheDocument();
});

test("resources columns show 'near limit' as text, after the state; unknown values read —", async () => {
  const fresh = { ...TASK, id: "tsk_20", tag: "S20", name: "SUBREAD_FEATURECOUNTS (S20)", state: "pending", attempt_n: null, resources: { ...RESOURCES, realtime_s: null, cpu_percent: null, peak_rss_bytes: null } };
  serve({
    [`${URL_}/processes`]: { items: [{ process: PROCESS, stage_id: null, counts: { failed: 1, pending: 1 }, retries: 1 }] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: { items: [TASK, fresh], next: null },
    [URL_]: { ...run({ state: "running" }), params: {}, failures: [], failures_total: 0 },
  });
  app(`/runs/${ID}?tab=tasks`);
  const table = await screen.findByRole("table", { name: "Tasks" });
  const heads = within(table).getAllByRole("columnheader").map((h) => h.textContent);
  expect(heads).toEqual(["Task", "State", "Attempt", "Duration", "CPUs", "CPU %", "Memory", "Peak memory", "Time limit", "Files"]);
  const [, failedRow, pendingRow] = within(table).getAllByRole("row");
  expect(within(failedRow).getAllByRole("cell").map((c) => c.textContent).slice(1)).toEqual([
    "Failed", "2", "6 min", "6", "412 %", "8 GB", "8 GB near limit", "8 h", "Files",
  ]);
  expect(within(pendingRow).getAllByRole("cell").map((c) => c.textContent).slice(2, 9)).toEqual(["—", "—", "6", "—", "8 GB", "—", "8 h"]);
  expect(within(pendingRow).getByRole("button", { name: "Files of SUBREAD_FEATURECOUNTS (S20)" })).toBeInTheDocument();
});

test("on the phone each task has one resources line and a full-width Files button", async () => {
  viewport(390);
  detail({ [`${FILES}/2/files`]: listing([]) });
  app(`/runs/${ID}?tab=tasks`);
  const cards = await screen.findByRole("list", { name: "Tasks" });
  expect(within(cards).getByText("attempt 2 · asked 8 GB · peak 8 GB, near limit · limit 8 h")).toBeInTheDocument();
  await userEvent.click(within(cards).getByRole("button", { name: "Files of SUBREAD_FEATURECOUNTS (S19), attempt 2" }));
  expect(await screen.findByRole("dialog", { name: "SUBREAD_FEATURECOUNTS (S19)" })).toHaveAttribute("aria-modal", "true");
});
