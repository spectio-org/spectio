import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

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
  expect(within(crumbs).getByText("rnaseq-2026-10-25")).toHaveAttribute("aria-current", "page");
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
    within(dialog).getByText("Spectio interrupts its head in the tmux session, and the engine stops its tasks."),
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
});

test("no Cancel on a terminal run, nor on a run started from a terminal", async () => {
  detail({ origin: "cli-observed", head: { session: null, node: "login1", alive: true, exit_code: null } });
  app(`/runs/${ID}`);
  await screen.findByRole("heading", { level: 1 });
  expect(screen.queryByRole("button", { name: "Cancel run" })).toBeNull();
  expect(screen.getByText("head on login1, not checked")).toBeInTheDocument();
});

test("the facts say Head not started yet while head is null", async () => {
  detail({ state: "queued", head: null, started_at: null });
  app(`/runs/${ID}`);
  expect(await screen.findByText("Head not started yet")).toBeInTheDocument();
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
  const state = screen.getByRole("combobox", { name: "State" });
  expect(state).toHaveValue("failed");
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?state=failed&limit=50`));
  expect(await screen.findByText("S01")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Process" })).toBeInTheDocument();
});

test("the parameters table and a log loaded on click", async () => {
  detail();
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Parameters" }));
  expect(screen.getByText("outdir")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Logs" }));
  await userEvent.click(screen.getByRole("button", { name: "Engine log" }));
  expect(await screen.findByText(/N E X T F L O W/)).toBeInTheDocument();
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
