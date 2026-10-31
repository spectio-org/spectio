import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, VERSION, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

/** A clipboard that keeps what was written (jsdom has none); `readText` reads the last. */
beforeEach(() => {
  let last = "";
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: async (text: string) => void (last = text), readText: async () => last },
  });
});
afterEach(() => {
  Reflect.deleteProperty(navigator, "clipboard");
});

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const PROCESSES = {
  items: [
    { process: "NFCORE:RNASEQ:FASTQC", stage_id: null, counts: { succeeded: 12 }, retries: 0 },
    { process: "NFCORE:RNASEQ:ALIGN", stage_id: null, counts: { succeeded: 12, running: 3, pending: 5 }, retries: 1 },
  ],
};
const TASKS = {
  items: [{ id: "tsk_1", process: "NFCORE:RNASEQ:ALIGN", tag: "S01", name: "ALIGN (S01)", state: "failed", stage_id: null }],
  next: null,
};

/** The shared run header (LiteRunDetail), once the run has loaded. */
async function runHeader() {
  return (await screen.findByRole("heading", { level: 1 })).closest("header")!;
}

function detail(over: Record<string, unknown> = {}, more: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}/processes`]: PROCESSES,
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: TASKS,
    [`${URL_}/logs?source=engine`]: () => new Response("N E X T F L O W  ~  version 26.10.4\n"),
    [URL_]: { ...run(over), params: { outdir: "results", depth: 3 } },
    ...more,
  });
}

test("the header names the run, its state word and short id; the crumb is the run's name", async () => {
  detail({ name: "rnaseq-2026-10-25" });
  app(`/runs/${ID}`);
  expect(await screen.findByRole("heading", { level: 1, name: "rnaseq-2026-10-25" })).toBeInTheDocument();
  expect(screen.getByText("7T9V1W")).toBeInTheDocument();
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(await within(crumbs).findByText("rnaseq-2026-10-25")).toHaveAttribute("aria-current", "page");
  expect(within(crumbs).queryByText(ID)).toBeNull();
  expect(document.title).toBe("rnaseq-2026-10-25 · Spectio");
});

test("Cancel asks first in a modal dialog, returns focus, then posts :cancel", async () => {
  const cancelled = vi.fn((_url: URL, _init?: RequestInit) => json(202, { ...run({ state: "cancelling" }), params: {} }));
  detail({}, { [`${URL_}:cancel`]: cancelled });
  app(`/runs/${ID}`);
  const cancel = await screen.findByRole("button", { name: "Cancel run" });
  await userEvent.click(cancel);
  const dialog = await screen.findByRole("dialog", { name: "Cancel this run?" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(
    within(dialog).getByText("Spectio stops its head with signals, and the engine stops its tasks."),
  ).toBeInTheDocument();
  await userEvent.click(within(dialog).getByRole("button", { name: "Keep running" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(cancel).toHaveFocus());
  expect(cancelled).not.toHaveBeenCalled();

  await userEvent.click(cancel);
  await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancel the run" }));
  await waitFor(() => expect(cancelled).toHaveBeenCalledTimes(1));
  expect(cancelled.mock.calls[0][1]).toMatchObject({ method: "POST" });
  expect(await screen.findByText("Cancelling")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Cancel run" })).toBeNull();
  await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toHaveFocus());
  expect(document.activeElement).not.toBe(document.body);
});

test("no Cancel on a terminal run, nor on a run started from a terminal", async () => {
  detail({ origin: "cli-observed", head: { session: null, node: "login1", alive: true, exit_code: null } });
  app(`/runs/${ID}`);
  await screen.findByRole("heading", { level: 1 });
  expect(screen.queryByRole("button", { name: "Cancel run" })).toBeNull();
  expect(screen.getByText("Not checked (started from a terminal)")).toBeInTheDocument();
});

test("the facts say the head is not started yet while head is null", async () => {
  detail({ state: "queued", head: null, started_at: null });
  app(`/runs/${ID}`);
  expect(await screen.findByText("Not started yet")).toBeInTheDocument();
});

test("with no stage, the flat processes list and its line", async () => {
  detail();
  app(`/runs/${ID}`);
  expect(
    await screen.findByText("No stages for this pipeline: processes as the engine reports them."),
  ).toBeInTheDocument();
  const table = screen.getByRole("table", { name: "Processes" });
  const align = within(table).getByText("NFCORE:RNASEQ:ALIGN").closest("tr")!;
  expect(within(align).getByText("Running")).toBeInTheDocument();
  expect(within(within(table).getByText("NFCORE:RNASEQ:FASTQC").closest("tr")!).getByText("Done")).toBeInTheDocument();
});

test("with stages, the stage list and the header line", async () => {
  detail(
    {},
    {
      [`${URL_}/stages`]: {
        items: [
          { id: "st1", position: 1, name: "QC", source: "detected", state: "completed", task_counts: { succeeded: 12 } },
          { id: "st2", position: 2, name: "Align", source: "declared", state: "running", task_counts: { succeeded: 12, running: 3 } },
        ],
      },
    },
  );
  app(`/runs/${ID}`);
  expect(await screen.findByText(/1 of 2 stages done · 1 running/)).toBeInTheDocument();
  expect(screen.getByText("QC")).toBeInTheDocument();
  expect(screen.getByText("Declared")).toBeInTheDocument();
  expect(screen.queryByText(/No stages for this pipeline/)).toBeNull();
});

test("on a failed run the tasks filter starts at failed", async () => {
  const mock = detail({ state: "failed", ended_at: "2026-10-31T08:00:00+00:00" });
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Tasks" }));
  expect(screen.getByRole("button", { name: /^Failed/ })).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?state=failed&limit=50`));
  expect(await screen.findByText(/\(S01\)/)).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Process" })).toBeInTheDocument();
});

test("the parameters table, and a log loaded on click", async () => {
  detail({}, { [`${URL_}/logs?source=head-out`]: () => new Response("head says hello\n") });
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Parameters" }));
  expect(screen.getByRole("table", { name: "Parameters" })).toHaveTextContent("outdir");
  await userEvent.click(screen.getByRole("tab", { name: "Logs" }));
  await userEvent.click(screen.getByRole("button", { name: "Head output" }));
  expect(await screen.findByText(/head says hello/)).toBeInTheDocument();
});

test("a frame for this run refetches it; none once it is terminal", async () => {
  let state = "running";
  const mock = detail({}, { [URL_]: () => json(200, { ...run({ state }), params: {} }) });
  app(`/runs/${ID}`);
  await screen.findByRole("heading", { level: 1 });
  const count = () => fetched(mock).filter((u) => u === URL_).length;
  const before = count();
  state = "succeeded";
  FakeEventSource.last!.frame({ run_id: "run_other" });
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(count()).toBe(before + 1), { timeout: 3000 });
  expect(await screen.findByText("Succeeded")).toBeInTheDocument();
  FakeEventSource.last!.frame({ run_id: ID });
  await new Promise((r) => setTimeout(r, 1200));
  expect(count()).toBe(before + 1);
});

test("a malformed run id shows not-found inside the shell, without asking the server", async () => {
  const mock = detail();
  app("/runs/%E0");
  expect(await screen.findByRole("heading", { level: 1, name: "No such run" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "All runs" })).toHaveAttribute("href", "/runs");
  expect(fetched(mock).some((u) => u.startsWith("/api/v1/runs/"))).toBe(false);
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).queryByText("%E0")).toBeNull();
});

test("an unknown run id shows not-found", async () => {
  serve({});
  app("/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V9Z");
  expect(await screen.findByRole("heading", { level: 1, name: "No such run" })).toBeInTheDocument();
});

test("UX-PAR-26: the Tasks tab filters by pressed state buttons and refreshes on frames", async () => {
  const mock = detail({ task_counts: { succeeded: 24, running: 3, pending: 5 } });
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Tasks" }));
  const filters = screen.getByRole("group", { name: "Show tasks" });
  expect(within(filters).getByRole("button", { name: /^All\s*32/ })).toHaveAttribute("aria-pressed", "true");
  const running = within(filters).getByRole("button", { name: /^Running\s*3/ });
  expect(within(filters).getByRole("button", { name: /^Failed\s*0/ })).toBeInTheDocument();
  await userEvent.click(running);
  expect(running).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?state=running&limit=50`));
  // The task cell reads "PROCESS (tag)", and its state is a word with an icon in a tone.
  const table = await screen.findByRole("table", { name: "Tasks" });
  const row = within(table).getByText("ALIGN").closest("tr")!;
  expect(row).toHaveTextContent("ALIGN (S01)");
  expect(within(row).getByText("Failed").closest("[data-tone]")).toHaveAttribute("data-tone", "failed");
  // Live: a frame for this run refetches the shown page.
  const count = () => fetched(mock).filter((u) => u.startsWith(`${URL_}/tasks`)).length;
  const before = count();
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(count()).toBeGreaterThan(before), { timeout: 3000 });
  expect(screen.getByText(/1 of 3 tasks/)).toBeInTheDocument();
});

test("UX-PAR-20/21/22: a Snakemake run reads jobs and rules; facts sit in the header with the engine mark", async () => {
  detail({
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/wgs", name: "wgs-germline", version: null },
  });
  app(`/runs/${ID}`);
  const header = await runHeader();
  expect(within(header).getByText("24 / 32 jobs")).toBeInTheDocument();
  expect(within(header).getByText("Snakemake 9.27.1 · test")).toBeInTheDocument();
  expect(within(header).getByText("wgs-germline (no version declared)")).toBeInTheDocument();
  expect(within(header).getAllByRole("img", { name: "Snakemake" }).length).toBeGreaterThan(0);
  expect(within(header).getByText(`/scratch/amartin/spectio-runs/${ID}`)).toBeInTheDocument();
  const chips = within(header).getByRole("list", { name: "Jobs by state" }); // CR-P3PARA-07
  expect(within(chips).getByText("0 failed").closest("[data-tone]")).toHaveAttribute("data-tone", "failed");
  expect(within(chips).getByText("1 retried")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Rules" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Rule, first-seen order" })).toBeInTheDocument();
  // CR-P3PARA-03: the engine's mark beside the Pipeline fact.
  const pipeline = within(header).getByText("wgs-germline (no version declared)").closest("dd")!;
  expect(within(pipeline).getByRole("img", { name: "Snakemake" })).toBeInTheDocument();
  // The facts stay on every tab.
  await userEvent.click(screen.getByRole("tab", { name: "Logs" }));
  expect(within(await runHeader()).getByText("Snakemake 9.27.1 · test")).toBeInTheDocument();
  // CR-P3PARA-07: the Jobs tab names its filters and table in the engine's words.
  await userEvent.click(screen.getByRole("tab", { name: "Jobs" }));
  expect(screen.getByRole("group", { name: "Show jobs" })).toBeInTheDocument();
  expect(await screen.findByRole("table", { name: "Jobs" })).toBeInTheDocument();
});

test("UX-PAR-25/16: a failed run opens on Why it failed, never blank, with a way to the failed tasks", async () => {
  const mock = detail({
    state: "failed",
    ended_at: "2026-10-31T08:00:00+00:00",
    failure: { class: "tool_error", message: "", task_id: null, attempt_n: 1 },
    head: { session: `spectio-${ID}`, node: "login1", alive: false, exit_code: 1 },
    summary: { tasks: { done: 24, total: 32, failed: 2, cached: 0 }, last_failure: null },
  }, { [`${URL_}/logs?source=head-err`]: () => new Response("line 1\nError in rule x\n") });
  app(`/runs/${ID}`);
  const why = await screen.findByRole("region", { name: "Why it failed" });
  expect(within(why).getByRole("button", { name: /^Why it failed/ })).toHaveAttribute("aria-expanded", "true");
  expect(within(why).getByText("tool_error")).toBeInTheDocument();
  expect(within(why).getByText("2 tasks failed, and the run stopped")).toBeInTheDocument();
  expect(within(await runHeader()).getByText(/^ended /)).toBeInTheDocument();
  // The head has ended: folded, with its exit code as the summary.
  expect(screen.getByRole("button", { name: /^The head has ended\s*exit 1/ })).toHaveAttribute("aria-expanded", "false");
  expect(await screen.findByText(/Error in rule x/)).toBeInTheDocument();
  await userEvent.click(within(why).getByRole("button", { name: "Tasks, filtered to Failed" }));
  expect(screen.getByRole("tab", { name: "Tasks" })).toHaveAttribute("aria-selected", "true");
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?state=failed&limit=50`));
});

test("UX-PAR-23: the Summary aside opens the head by hand and tails the engine log", async () => {
  detail({}, { "/api/v1/version": { ...VERSION, executor: "slurm" } });
  app(`/runs/${ID}`);
  const attach = await screen.findByRole("region", { name: "Open the head by hand" });
  expect(within(attach).getByText(`tmux attach -t spectio-${ID}`, { exact: false })).toBeInTheDocument();
  expect(within(attach).getByRole("button", { name: "Copy the commands to open the head by hand" })).toBeInTheDocument();
  const log = screen.getByRole("region", { name: "Engine log · last lines" });
  expect(await within(log).findByText(/N E X T F L O W/)).toBeInTheDocument();
  const params = screen.getByRole("button", { name: /^Parameters\s*2 set at launch/ });
  expect(params).toHaveAttribute("aria-expanded", "false");
});

test("the log tail of an ended run reads Empty., and its lines carry the level tint", async () => {
  detail({ state: "succeeded", ended_at: "2026-10-31T08:00:00+00:00" }, { [`${URL_}/logs?source=engine`]: () => new Response("") });
  app(`/runs/${ID}`);
  const log = await screen.findByRole("region", { name: "Engine log · last lines" });
  expect(await within(log).findByText("Empty.")).toBeInTheDocument();
});

test("the log tail tints its lines by level, as the Logs tab does", async () => {
  detail({}, { [`${URL_}/logs?source=engine`]: () => new Response("all good\nWARN slow disk\nERROR boom\n") });
  app(`/runs/${ID}`);
  const log = await screen.findByRole("region", { name: "Engine log · last lines" });
  expect(await within(log).findByText("ERROR boom")).toHaveAttribute("data-tone", "failed");
  expect(within(log).getByText("WARN slow disk")).toHaveAttribute("data-tone", "review");
  expect(within(log).getByText("all good")).not.toHaveAttribute("data-tone");
});

test("Download attaches its anchor to the page and revokes the URL after the click", async () => {
  detail();
  const revoke = vi.fn();
  const { createObjectURL, revokeObjectURL } = URL; // restored after the test (CR-P3PARA-10)
  Object.assign(URL, { createObjectURL: () => "blob:x", revokeObjectURL: revoke });
  const attached: boolean[] = [];
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    attached.push(document.body.contains(this));
  });
  try {
    app(`/runs/${ID}`);
    await userEvent.click(await screen.findByRole("tab", { name: "Logs" }));
    await screen.findByText(/N E X T F L O W/, { selector: "span" });
    screen.getByRole("button", { name: "Download last 64 KiB" }).click();
    expect(attached).toEqual([true]);
    expect(document.querySelector("a[download]")).toBeNull();
    expect(revoke).not.toHaveBeenCalled();
    await waitFor(() => expect(revoke).toHaveBeenCalledWith("blob:x"));
  } finally {
    click.mockRestore();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
  }
  // CR-P3PARA-10: the stubs do not outlive the test
  expect(URL.createObjectURL).toBe(createObjectURL);
  expect(URL.revokeObjectURL).toBe(revokeObjectURL);
});

test("UX-PAR-23: with the local executor the head has no terminal: its process instead", async () => {
  detail({ head: { session: "18823.3644058", node: "login1", alive: true, exit_code: null } });
  app(`/runs/${ID}`);
  const attach = await screen.findByRole("region", { name: "Open the head by hand" });
  expect(within(attach).getByText("ps -o pid,etime,args --sid 18823")).toBeInTheDocument();
  expect(within(attach).queryByText(/tmux/)).toBeNull();
});

test("UX-PAR-27: the Logs tab opens on the engine log, with Reload and Download", async () => {
  const mock = detail();
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Logs" }));
  const logs = screen.getByRole("group", { name: "Log" });
  expect(within(logs).getByRole("button", { name: "Engine log" })).toHaveAttribute("aria-pressed", "true");
  expect(await screen.findByLabelText("Engine log", { selector: "pre" })).toHaveTextContent("N E X T F L O W");
  const before = fetched(mock).filter((u) => u.endsWith("logs?source=engine")).length;
  await userEvent.click(screen.getByRole("button", { name: "Reload" }));
  await waitFor(() => expect(fetched(mock).filter((u) => u.endsWith("logs?source=engine")).length).toBe(before + 1));
  expect(screen.getByRole("button", { name: "Download last 64 KiB" })).toBeInTheDocument();
  expect(screen.getByText(/stay in its work directory/)).toBeInTheDocument();
});

test("UX-PAR-29: the Cancel dialog says what stops and how, for the server's executor", async () => {
  detail();
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Cancel run" }));
  const dialog = await screen.findByRole("dialog", { name: "Cancel this run?" });
  expect(within(dialog).getByText(/rnaseq-a has 3 running and 5 pending tasks; they will not finish/)).toBeInTheDocument();
  expect(within(dialog).getByText(/process group/)).toBeInTheDocument(); // VERSION.executor is local
});

test("P3-parB: a run that has ended but whose head end is not yet reported shows Head Ending, not Alive", async () => {
  detail({ state: "succeeded", head: { session: "18823.3644058", node: "login1", alive: true, exit_code: null } });
  app(`/runs/${ID}`);
  expect(await screen.findByText("Ending")).toBeInTheDocument();
  expect(screen.queryByText("Alive")).toBeNull();
});

// P3-parC: the run detail against LiteRunDetail, LiteRunLogs and LiteRunActions.

test("P3-parC: an nf-core/ pipeline shows the nf-core mark in the header tile and the Pipeline fact; the Engine fact keeps Nextflow's", async () => {
  detail();
  app(`/runs/${ID}`);
  const header = await runHeader();
  expect(header.querySelector(".sp-mark-tile img")).toHaveAttribute("alt", "nf-core");
  const pipeline = within(header).getByText("nf-core/rnaseq 3.27.0").closest("dd")!;
  expect(within(pipeline).getByRole("img", { name: "nf-core" })).toBeInTheDocument();
  const engine = within(header).getByText("Nextflow 26.10.4 · test").closest("dd")!;
  expect(engine.querySelector("img")).toHaveAttribute("src", expect.stringContaining("logo-nextflow"));
});

test("P3-parC: Copy is a menu of native buttons: config, run directory and run ID; arrows move, Escape returns", async () => {
  detail();
  app(`/runs/${ID}`);
  const copy = await screen.findByRole("button", { name: "Copy" });
  expect(copy).toHaveAttribute("aria-haspopup", "menu");
  expect(copy).toHaveAttribute("aria-expanded", "false");
  await userEvent.click(copy);
  expect(copy).toHaveAttribute("aria-expanded", "true");
  const menu = screen.getByRole("menu", { name: "Copy" });
  const items = within(menu).getAllByRole("menuitem");
  expect(items.map((i) => i.textContent)).toEqual(["Config (params.json)", "Run directory", "Run ID"]);
  expect(items.every((i) => i.tagName === "BUTTON")).toBe(true);
  await waitFor(() => expect(items[0]).toHaveFocus());
  await userEvent.keyboard("{ArrowDown}");
  expect(items[1]).toHaveFocus();
  await userEvent.keyboard("{ArrowUp}{ArrowUp}");
  expect(items[2]).toHaveFocus(); // wraps
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("menu")).toBeNull();
  expect(copy).toHaveFocus();

  await userEvent.click(copy);
  await userEvent.click(within(screen.getByRole("menu")).getByRole("menuitem", { name: "Run directory" }));
  expect(await navigator.clipboard.readText()).toBe(`/scratch/amartin/spectio-runs/${ID}`);
  expect(screen.getByText("Copied the run directory")).toHaveAttribute("role", "status");
  expect(copy).toHaveFocus();
  await userEvent.click(copy);
  await userEvent.click(screen.getByRole("menuitem", { name: "Config (params.json)" }));
  expect(JSON.parse(await navigator.clipboard.readText())).toEqual({ outdir: "results", depth: 3 });
});

test("P3-parC: a Snakemake run copies its config as config.yaml; a run from a terminal has no run directory to copy", async () => {
  detail({
    origin: "cli-observed",
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/wgs", name: "wgs-germline", version: null },
  });
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Copy" }));
  const items = within(screen.getByRole("menu")).getAllByRole("menuitem");
  expect(items.map((i) => i.textContent)).toEqual(["Config (config.yaml)", "Run ID"]);
  await userEvent.click(items[0]);
  expect(await navigator.clipboard.readText()).toBe("outdir: results\ndepth: 3\n");
});

test("P3-parC: the tab and the log source are in the URL: a log view can be linked and reloaded", async () => {
  const mock = detail({}, { [`${URL_}/logs?source=head-err`]: () => new Response("boom\n") });
  const router = app(`/runs/${ID}?tab=logs&source=head-err`);
  expect(await screen.findByRole("tab", { name: "Logs" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("button", { name: "Head errors" })).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/logs?source=head-err`));
  await userEvent.click(screen.getByRole("button", { name: "Engine log" }));
  await waitFor(() => expect(router.state.location.search).toEqual({ tab: "logs", source: "engine" }));
  await userEvent.click(screen.getByRole("tab", { name: "Tasks" }));
  await waitFor(() => expect(router.state.location.search).toEqual({ tab: "tasks" }));
  await userEvent.click(screen.getByRole("tab", { name: "Summary" }));
  await waitFor(() => expect(router.state.location.search).toEqual({}));
});

test("P3-parC: the picked log source is kept across a tab switch (CR-P3PARC-02)", async () => {
  detail({}, { [`${URL_}/logs?source=head-err`]: () => new Response("boom\n") });
  app(`/runs/${ID}?tab=logs`);
  await userEvent.click(await screen.findByRole("button", { name: "Head errors" }));
  await userEvent.click(screen.getByRole("tab", { name: "Summary" }));
  await userEvent.click(screen.getByRole("tab", { name: "Logs" }));
  expect(await screen.findByRole("button", { name: "Head errors" })).toHaveAttribute("aria-pressed", "true");
});

test("P3-parC: an unknown tab or source in the URL falls back to the Summary and the engine log", async () => {
  const mock = detail();
  app(`/runs/${ID}?tab=nope&source=%2Fetc%2Fpasswd`);
  expect(await screen.findByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
  await userEvent.click(screen.getByRole("tab", { name: "Logs" }));
  expect(screen.getByRole("button", { name: "Engine log" })).toHaveAttribute("aria-pressed", "true");
  expect(fetched(mock).some((u) => u.includes("passwd"))).toBe(false);
});

test("P3-parC: the aside's All logs opens the Logs tab on the tail's source, with focus on the panel", async () => {
  detail({
    state: "failed",
    ended_at: "2026-10-31T08:00:00+00:00",
    head: { session: `spectio-${ID}`, node: "login1", alive: false, exit_code: 1 },
  }, { [`${URL_}/logs?source=head-err`]: () => new Response("Error in rule x\n") });
  const router = app(`/runs/${ID}`);
  const tail = await screen.findByRole("region", { name: "Head errors · last lines" });
  await userEvent.click(within(tail).getByRole("button", { name: /^All logs/ }));
  expect(screen.getByRole("tab", { name: "Logs" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("button", { name: "Head errors" })).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(screen.getByRole("tabpanel", { name: "Logs" })).toHaveFocus());
  expect(router.state.location.search).toEqual({ tab: "logs", source: "head-err" });
});

test("P3-parC: the log's file on the server, with Copy; an Open raw link to the same text", async () => {
  detail({}, { [`${URL_}/logs?source=head-out`]: () => new Response("hello\n") });
  app(`/runs/${ID}?tab=logs&source=engine`);
  const file = await screen.findByLabelText("File");
  expect(file).toHaveTextContent(`/scratch/amartin/spectio-runs/${ID}/launch/.nextflow.log`);
  await userEvent.click(screen.getByRole("button", { name: "Copy the engine log path" }));
  expect(await navigator.clipboard.readText()).toBe(`/scratch/amartin/spectio-runs/${ID}/launch/.nextflow.log`);
  const raw = screen.getByRole("link", { name: /^Open raw/ });
  expect(raw).toHaveAttribute("href", `/api/v1/runs/${ID}/logs?source=engine`);
  expect(raw).toHaveAttribute("target", "_blank");
  expect(raw).toHaveAttribute("rel", expect.stringContaining("noopener"));
  await userEvent.click(screen.getByRole("button", { name: "Head output" }));
  expect(screen.getByLabelText("File")).toHaveTextContent(`/scratch/amartin/spectio-runs/${ID}/launch/.spectio/head.out`);
  expect(screen.getByRole("link", { name: /^Open raw/ })).toHaveAttribute("href", `/api/v1/runs/${ID}/logs?source=head-out`);
});

test("P3-parC: Snakemake's engine log is the newest file of a directory", async () => {
  detail({
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/wgs", name: "wgs", version: null },
  });
  app(`/runs/${ID}?tab=logs&source=engine`);
  expect(await screen.findByLabelText("File")).toHaveTextContent(`/scratch/amartin/spectio-runs/${ID}/launch/.snakemake/log/`);
  expect(screen.getByText(/the newest \.log there/)).toBeInTheDocument();
});

test("P3-parC: a run from a terminal has no File row", async () => {
  detail({ origin: "cli-observed" });
  app(`/runs/${ID}?tab=logs&source=engine`);
  await screen.findByLabelText("Engine log", { selector: "pre" });
  expect(screen.queryByLabelText("File")).toBeNull();
});

test("P3-parC: the viewer does not wrap, opens at its newest lines, and tints levels as the board does", async () => {
  const top = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  const height = Object.getOwnPropertyDescriptor(Element.prototype, "scrollHeight")!;
  Object.defineProperty(Element.prototype, "scrollHeight", { configurable: true, get: () => 900 });
  Object.defineProperty(Element.prototype, "scrollTop", {
    configurable: true,
    get(this: { _top?: number }) {
      return this._top ?? 0;
    },
    set(this: { _top?: number }, v: number) {
      this._top = v;
    },
  });
  try {
    detail({}, {
      [`${URL_}/logs?source=engine`]: () =>
        new Response(
          "Oct-25 07:40:12 [main] INFO  nextflow.cli.CmdRun - N E X T F L O W\n" +
            "[88/f1d0e2] STAR_ALIGN (S04) completed\n" +
            "retry 1/3 with memory 8 GB\n" +
            "ERROR nextflow.processor.TaskProcessor - exit 137\n" +
            "nextflow.Session - progress 524 / 803 tasks\n" +
            "Finished job 12.\n",
        ),
    });
    app(`/runs/${ID}?tab=logs&source=engine`);
    const pre = await screen.findByLabelText("Engine log", { selector: "pre" });
    await within(pre).findByText(/completed/);
    expect(pre).toHaveClass("sp-nowrap");
    expect(pre).toHaveAttribute("tabindex", "0");
    await waitFor(() => expect(pre.scrollTop).toBe(900));
    expect(within(pre).getByText(/N E X T F L O W/)).not.toHaveAttribute("data-tone");
    expect(within(pre).getByText(/completed/)).toHaveAttribute("data-tone", "ok");
    expect(within(pre).getByText(/Finished job/)).toHaveAttribute("data-tone", "ok");
    expect(within(pre).getByText(/retry 1\/3/)).toHaveAttribute("data-tone", "review");
    expect(within(pre).getByText(/exit 137/)).toHaveAttribute("data-tone", "failed");
    expect(within(pre).getByText(/progress 524/)).toHaveAttribute("data-tone", "progress");
  } finally {
    Object.defineProperty(Element.prototype, "scrollTop", top);
    Object.defineProperty(Element.prototype, "scrollHeight", height);
  }
});

test("P3-parC: the note under the viewer leads to the Tasks tab", async () => {
  detail();
  app(`/runs/${ID}?tab=logs&source=engine`);
  await userEvent.click(await screen.findByRole("button", { name: /open a task in Tasks/ }));
  expect(screen.getByRole("tab", { name: "Tasks" })).toHaveAttribute("aria-selected", "true");
});
