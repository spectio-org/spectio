// The Graph tab and the Launch map against the contract's routes (spikes/metroflow/graph-contract.md),
// mocked: GET /features, /runs/{id}/graph, /runs/{id}/processes/{name}/outputs, /workflows:graph.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, FakeEventSource, app, fetched, run, serve, stubStream, viewport } from "../../testing";
import { resetFeatures } from "./features";
import { DOC } from "./fixture";
import type { GraphDocument } from "./types";

beforeEach(stubStream);
beforeEach(resetFeatures);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const P = "NFCORE_DEMO:DEMO:";
const PROCESSES = { items: DOC.nodes.filter((n) => n.kind !== "gate").map((n) => ({ process: n.id, stage_id: n.stage_id, counts: n.counts ?? {}, retries: 0 })) };

function mocks(features: string[] = ["graph_view"], more: Record<string, unknown> = {}) {
  return serve({
    "/api/v1/features": { features },
    [`${URL_}/processes`]: PROCESSES,
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: { items: [], next: null },
    [`${URL_}/graph`]: DOC,
    [`${URL_}/processes/${encodeURIComponent(`${P}ALIGN:BWA`)}/outputs`]: {
      items: [
        { path: "align/S1.bam", task_id: "tsk_1", attempt_n: 1, state: "present", temp: false, root: "results" },
        { path: "align/S1.tmp.sam", task_id: "tsk_1", attempt_n: 1, state: "removed", temp: true, root: "launch" },
      ],
    },
    [URL_]: { ...DETAIL, ...run(), params: { genome: "GRCh38", outdir: "results" } },
    ...more,
  });
}

/** The map's node buttons are inside React Flow, which hides nodes until measured in jsdom;
 * the List is the same graph as a table. */
const listView = () => screen.findByRole("table", { name: "Graph as a list" });

test("without the graph_view flag there is no Graph tab, and ?tab=graph falls back to the Summary", async () => {
  mocks([]);
  app(`/runs/${ID}?tab=graph`);
  expect(await screen.findByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByRole("tab", { name: "Graph" })).toBeNull();
});

test("with the flag, the Graph tab draws every step as a button that says its state", async () => {
  const mock = mocks();
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("tab", { name: "Graph" }));
  const bwa = await screen.findByRole("button", { name: "BWA, process, Running, 2 of 4 jobs done", hidden: true });
  expect(bwa.tagName).toBe("BUTTON");
  expect(screen.getByRole("button", { name: "QC gate, QC gate, Not run yet", hidden: true })).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${URL_}/graph`);
  expect(screen.getByRole("toolbar", { name: "Graph view" })).toBeInTheDocument();
});

test("the List view is the table equivalent, in pipeline order, with what each step runs after", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  const table = await listView();
  const rows = within(table).getAllByRole("row").slice(1);
  expect(rows).toHaveLength(6);
  const report = rows.find((r) => within(r).queryByRole("button", { name: "Open process REPORT" }))!;
  expect(report).toHaveTextContent("BWA, QC gate");
});

test("search is kept in the URL and filters the List; a level groups the steps", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list`);
  await listView();
  await userEvent.type(screen.getByRole("textbox", { name: "Search" }), "state:running");
  await waitFor(() => expect(router.state.location.search).toMatchObject({ tab: "graph", q: "state:running" }));
  expect(within(await listView()).getAllByRole("row")).toHaveLength(2);
  expect(screen.getByText("1 match")).toBeInTheDocument();

  await userEvent.clear(screen.getByRole("textbox", { name: "Search" }));
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Show" }), "subworkflow");
  await waitFor(() => expect(router.state.location.search).toMatchObject({ level: "subworkflow" }));
  const names = within(await listView()).getAllByRole("button").map((b) => b.textContent);
  expect(names.sort()).toEqual(["ALIGN", "QC", "REPORT"]);
});

test("a step's sheet shows this run's parameter values, its links, and its outputs read live", async () => {
  const mock = mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("dialog", { name: "BWA (process)" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(within(sheet).getByText("genome")).toBeInTheDocument();
  expect(within(sheet).getByText("GRCh38")).toBeInTheDocument();
  expect(within(sheet).getByText("Runs after")).toBeInTheDocument();
  expect(await within(sheet).findByText("align/S1.bam")).toBeInTheDocument();
  expect(within(sheet).getByText("Removed (temporary)")).toBeInTheDocument();
  expect(within(sheet).getByRole("link", { name: "Preview align/S1.bam" })).toHaveAttribute("href", expect.stringContaining("path=align"));
  expect(within(sheet).queryByRole("link", { name: "Preview align/S1.tmp.sam" })).toBeNull();

  const before = fetched(mock).filter((u) => u.endsWith("/outputs")).length;
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(fetched(mock).filter((u) => u.endsWith("/outputs")).length).toBeGreaterThan(before));
});

test("Open in Tasks from the sheet goes to the Tasks tab on that process", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list&node=${encodeURIComponent(`${P}ALIGN:BWA`)}`);
  const sheet = await screen.findByRole("dialog", { name: "BWA (process)" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Open in Tasks" }));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ tab: "tasks", process: `${P}ALIGN:BWA` }));
});

test("Trace upstream keeps only the step's ancestors in the List", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list&node=${encodeURIComponent(`${P}QC:gate`)}`);
  const sheet = await screen.findByRole("dialog", { name: "QC gate (QC gate)" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Trace upstream" }));
  await waitFor(() => expect(within(screen.getByRole("table", { name: "Graph as a list" })).getAllByRole("row")).toHaveLength(4));
  expect(screen.getByText(/Showing what leads to QC gate/)).toBeInTheDocument();
});

test("the critical path is named in the List; a static estimate says so", async () => {
  mocks(["graph_view"], { [`${URL_}/graph`]: { ...DOC, estimate: true } });
  app(`/runs/${ID}?tab=graph&show=list&overlay=critical`);
  const table = await listView();
  expect(within(table).getAllByText("critical path")).toHaveLength(2);
  expect(screen.getByRole("note")).toHaveTextContent("Static estimate from the code");
});

test("Compare with another run marks the steps new in this run", async () => {
  const other = { ...DOC, nodes: DOC.nodes.filter((n) => !n.id.endsWith("REPORT")) };
  const OTHER = "run_01JBC6Q4ZK7M8N2P3R5S7T9V2X";
  mocks(["graph_view"], {
    "/api/v1/runs?": { items: [run(), run({ id: OTHER, name: "rnaseq-b" })], next: null },
    [`/api/v1/runs/${OTHER}/graph`]: other,
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await listView();
  const compare = screen.getByRole("combobox", { name: "Compare with" });
  await waitFor(() => expect(within(compare).getAllByRole("option")).toHaveLength(2));
  await userEvent.selectOptions(compare, OTHER);
  expect(await screen.findByText("new in this run")).toBeInTheDocument();
});

test("Replay is a switch with a time slider", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  await listView();
  const replay = screen.getByRole("switch", { name: "Replay" });
  expect(replay).toHaveAttribute("aria-checked", "false");
  await userEvent.click(replay);
  expect(replay).toHaveAttribute("aria-checked", "true");
  expect(screen.getByRole("slider", { name: "Replay time" })).toBeInTheDocument();
  // at the start, BWA has not begun
  const bwa = within(screen.getByRole("table", { name: "Graph as a list" })).getByRole("button", { name: "Open process BWA" }).closest("tr")!;
  expect(bwa).toHaveTextContent("Pending");
});

test("the graph is refetched on a live frame", async () => {
  const mock = mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  await listView();
  const before = fetched(mock).filter((u) => u.endsWith("/graph")).length;
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(fetched(mock).filter((u) => u.endsWith("/graph")).length).toBeGreaterThan(before));
});

test("on the phone the Graph tab opens on the List", async () => {
  viewport(390);
  mocks();
  app(`/runs/${ID}?tab=graph`);
  expect(await listView()).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "List" })).toHaveAttribute("aria-pressed", "true");
});

test("Launch shows a Workflow map of the loaded pipeline, folded until opened", async () => {
  const inspected = { location: "/data/demo", revision: null, engine: "nextflow", engine_files: ["main.nf"], name: "demo", version: null, engine_version: null, engine_versions: {}, schema: null, schema_source: "none", profiles: [], params_file: null };
  const mock = serve({
    "/api/v1/features": { features: ["graph_view"] },
    "/api/v1/workflows:inspect": inspected,
    "/api/v1/workflows:graph": { ...DOC, producer: "bioflow-insight", estimate: true, nodes: DOC.nodes.map(({ status, counts, metrics, first_start, last_end, ...n }) => n) },
  });
  app("/launch?location=/data/demo");
  const open = await screen.findByRole("button", { name: /Workflow map/ });
  expect(open).toHaveAttribute("aria-expanded", "false");
  await userEvent.click(open);
  await userEvent.click(await screen.findByRole("button", { name: "List" }));
  expect(within(await screen.findByRole("table", { name: "Graph as a list" })).getAllByRole("row")).toHaveLength(7);
  expect(fetched(mock)).toContain("/api/v1/workflows:graph?location=/data/demo");
  expect(screen.getByRole("note")).toHaveTextContent("Static estimate");
  // no run yet: no colour overlay and no Jobs level
  expect(screen.queryByRole("combobox", { name: "Colour by" })).toBeNull();
  expect(within(screen.getByRole("combobox", { name: "Show" })).queryByRole("option", { name: "Jobs" })).toBeNull();
});

test("Launch has no Workflow map without the flag", async () => {
  serve({
    "/api/v1/features": { features: [] },
    "/api/v1/workflows:inspect": { location: "/data/demo", revision: null, engine: "nextflow", engine_files: ["main.nf"], name: "demo", version: null, engine_version: null, engine_versions: {}, schema: null, schema_source: "none", profiles: [], params_file: null },
  });
  app("/launch?location=/data/demo");
  expect(await screen.findByRole("button", { name: /Parameters/ })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Workflow map/ })).toBeNull();
});

test("a disabled graph on the server says so", async () => {
  mocks(["graph_view"], {
    [`${URL_}/graph`]: () => new Response(JSON.stringify({ type: "/problems/feature-disabled", title: "Off" }), { status: 404, headers: { "content-type": "application/problem+json" } }),
  });
  app(`/runs/${ID}?tab=graph`);
  expect(await screen.findByRole("alert")).toHaveTextContent("The graph is turned off on this server.");
});

test("the Jobs level loads every started step, in pipeline order, under the job cap", async () => {
  const { expandedSteps, MAX_JOBS } = await import("./GraphPanel");
  const doc: GraphDocument = {
    ...DOC,
    nodes: [
      { ...DOC.nodes[0], id: "A", pipeline_order: 2, counts: { succeeded: 3 } },
      { ...DOC.nodes[0], id: "B", pipeline_order: 1, counts: { running: 1 } },
      { ...DOC.nodes[0], id: "C", pipeline_order: 3, counts: { succeeded: MAX_JOBS } },
      { ...DOC.nodes[0], id: "D", pipeline_order: 4, counts: {} },
    ],
  };
  // C is capped at one page (200), so it still fits
  expect(expandedSteps(doc).map((n) => n.id)).toEqual(["B", "A", "C"]);
});
