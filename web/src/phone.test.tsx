// The phone layout (ui-spec §4.11; MLiteTopbar, MLiteRuns, MLiteRunDetail; UX-PAR-08 and 10): the
// page title in the top bar's second row, and stacked cards where the wider layouts have tables.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { NO_RESOURCES, app, run, serve, stubStream, viewport } from "./testing";

beforeEach(() => {
  stubStream();
  viewport(390);
});
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
/** The phone top bar (jsdom counts every <header> as a banner, also the page's own). */
async function topBar() {
  await screen.findByRole("navigation", { name: "Main" });
  return document.querySelector<HTMLElement>("header.sp-mtopbar")!;
}
const SUMMARY = { groups: [{ key: "running", count: 1 }] };

function detail() {
  return serve({
    [`${URL_}/processes`]: {
      items: [{ process: "NFCORE:RNASEQ:ALIGN", stage_id: null, counts: { succeeded: 12, running: 3 }, retries: 0 }],
    },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: {
      items: [{ id: "tsk_1", process: "NFCORE:RNASEQ:ALIGN", tag: "S01", name: "ALIGN (S01)", state: "running", stage_id: null, attempt_n: 1, resources: NO_RESOURCES }],
      next: null,
    },
    [`${URL_}/logs`]: () => new Response(""),
    [URL_]: { ...run({ name: "rnaseq-2026-10-25" }), params: { outdir: "results" } },
  });
}

test("UX-PAR-08: a run's title is the top bar's h1, with its state line and a 44 px way back to Runs", async () => {
  detail();
  app(`/runs/${ID}`);
  const bar = await topBar();
  const title = await within(bar).findByRole("heading", { level: 1, name: "rnaseq-2026-10-25" });
  expect(screen.getAllByRole("heading", { level: 1 })).toEqual([title]);
  expect(within(bar).getByText("Running")).toBeInTheDocument();
  expect(within(bar).getByRole("link", { name: "Back to Runs" })).toHaveAttribute("href", "/runs");
});

test("UX-PAR-08: the runs list's title and subtitle sit in the top bar, with no back link", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  const bar = await topBar();
  expect(await within(bar).findByRole("heading", { level: 1, name: "Runs" })).toBeInTheDocument();
  expect(await within(bar).findByText("1 active")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(within(bar).queryByRole("link", { name: /^Back to/ })).toBeNull();
});

test("UX-PAR-08: Home keeps its greeting in the page, as on MLiteHome", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/");
  const title = await screen.findByRole("heading", { level: 1 });
  expect(screen.getByRole("main")).toContainElement(title);
  expect(within(await topBar()).queryByRole("heading")).toBeNull();
});

test("UX-PAR-10: the runs list is one card per run, not a table", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  const list = await screen.findByRole("list", { name: "Runs" });
  const card = within(list).getByRole("link", { name: "Open run rnaseq-a" }).closest("li")!;
  expect(card).toHaveAttribute("data-tone", "running");
  expect(within(card).getByText("Running")).toBeInTheDocument();
  expect(card).toHaveTextContent("nf-core/rnaseq 3.27.0");
  expect(card).toHaveTextContent("24 / 32 tasks");
  expect(card).toHaveTextContent("3 tasks running");
  expect(screen.queryByRole("table")).toBeNull();
});

test("UX-PAR-10: the run's processes, tasks and parameters are cards and rows, not tables", async () => {
  detail();
  app(`/runs/${ID}`);
  const processes = await screen.findByRole("list", { name: "Processes" });
  const align = within(processes).getByText("ALIGN").closest("li")!;
  expect(align).toHaveTextContent("12 / 15");
  expect(within(align).getByText("Running")).toBeInTheDocument();
  expect(screen.queryByRole("table")).toBeNull();

  await userEvent.click(screen.getByRole("tab", { name: "Tasks" }));
  const tasks = await screen.findByRole("list", { name: "Tasks" });
  expect(within(tasks).getByRole("listitem")).toHaveTextContent("ALIGN (S01)");
  expect(screen.queryByRole("table")).toBeNull();

  await userEvent.click(screen.getByRole("tab", { name: "Parameters" }));
  const panel = screen.getByRole("tabpanel");
  expect(within(panel).getByRole("term")).toHaveTextContent("outdir");
  expect(within(panel).getByRole("definition")).toHaveTextContent("results");
  expect(screen.queryByRole("table")).toBeNull();
});
