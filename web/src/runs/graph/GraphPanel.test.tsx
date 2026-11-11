// The Graph tab and the Launch map against the contract's routes (spikes/metroflow/graph-contract.md),
// mocked: GET /features, /runs/{id}/graph, /runs/{id}/processes/{name}/outputs, /workflows:graph.
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, FakeEventSource, app, fetched, run, serve, stubStream, viewport } from "../../testing";
import { resetFeatures } from "./features";
import { groupsAround, keyPairs, paramOf } from "./GraphPanel";
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
    [`${URL_}/processes/`]: { items: [] }, // any other step's outputs
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
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(within(sheet).getByRole("heading", { name: /^BWA/ })).toHaveFocus();
  expect(within(sheet).getByText("genome")).toBeInTheDocument();
  expect(within(sheet).getByText("GRCh38")).toBeInTheDocument();
  expect(within(sheet).getByRole("list", { name: "What BWA reads from" })).toBeInTheDocument();
  expect(await within(sheet).findByText("S1.bam")).toBeInTheDocument();
  expect(within(sheet).getAllByText(/removed \(temporary\)/).length).toBeGreaterThan(0);
  expect(within(sheet).getByRole("link", { name: "Open align/S1.bam" })).toHaveAttribute("href", expect.stringContaining("path=align"));
  expect(within(sheet).queryByRole("link", { name: "Open S1.tmp.sam" })).toBeNull();

  const before = fetched(mock).filter((u) => u.endsWith("/outputs")).length;
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(fetched(mock).filter((u) => u.endsWith("/outputs")).length).toBeGreaterThan(before));
});

test("Open in Tasks from the sheet goes to the Tasks tab on that process", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list&node=${encodeURIComponent(`${P}ALIGN:BWA`)}`);
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Open in Tasks" }));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ tab: "tasks", process: `${P}ALIGN:BWA` }));
});

test("Trace upstream keeps only the step's ancestors in the List", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list&node=${encodeURIComponent(`${P}QC:gate`)}`);
  const sheet = await screen.findByRole("complementary", { name: "QC gate (QC gate)" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Before: what leads to QC gate" }));
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
  // C has more jobs than one page: it stays one node rather than show part of its jobs
  expect(expandedSteps(doc).map((n) => n.id)).toEqual(["B", "A"]);
});

const bwaOnMap = () => screen.findByRole("button", { name: "BWA, process, Running, 2 of 4 jobs done", hidden: true });

test("a click opens the step's details beside the map; double-click or the fold button folds its subworkflow", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph`);
  // click events only: d3-zoom's mousedown handler needs a window jsdom's user-event does not give
  fireEvent.click(await bwaOnMap(), { detail: 1 });
  await waitFor(() => expect(router.state.location.search).toMatchObject({ node: `${P}ALIGN:BWA` }));
  const panel = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(router.state.location.search).toMatchObject({ node: `${P}ALIGN:BWA` });
  await userEvent.click(within(panel).getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("complementary", { name: "BWA (process)" })).toBeNull();

  // a real double-click: click, click, then dblclick
  const bwa = await bwaOnMap();
  fireEvent.click(bwa, { detail: 1 });
  fireEvent.click(bwa, { detail: 2 });
  fireEvent.dblClick(bwa, { detail: 2 });
  await waitFor(() => expect(String(router.state.location.search.fold)).toContain("sub:NFCORE_DEMO:DEMO:ALIGN"));
  expect(screen.queryByRole("button", { name: "BWA, process, Running, 2 of 4 jobs done", hidden: true })).toBeNull();
  // the folded box has a visible unfold button
  fireEvent.click(await screen.findByRole("button", { name: /^Unfold ALIGN: show its 2 steps$/, hidden: true }));
  await waitFor(() => expect(String(router.state.location.search.fold ?? "")).not.toContain("ALIGN"));
  // the layered layout draws ALIGN as an area: one fold button, on its title, none on its steps
  expect(await screen.findAllByRole("button", { name: "Fold ALIGN into one box", hidden: true })).toHaveLength(1);
});

test("a right-click shows the step's code by the node; Escape closes it and focus goes back to the node", async () => {
  const mock = mocks(["graph_view"], {
    "/api/v1/workflows:source": { file: "modules/bwa/main.nf", line: 3, code: "process BWA {\n  script: 'bwa mem'\n}", truncated: false },
  });
  app(`/runs/${ID}?tab=graph`);
  const bwa = await bwaOnMap();
  fireEvent.contextMenu(bwa);
  const card = await screen.findByRole("dialog", { name: "Code of BWA" });
  expect(await within(card).findByText(/script: 'bwa mem'/)).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.startsWith("/api/v1/workflows:source") && u.includes("name="))).toBe(true);
  expect(within(card).getByRole("button", { name: "Close the code" })).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: "Code of BWA" })).toBeNull();
  expect(bwa).toHaveFocus();
});

test("each link in a step's sheet is a button that opens what flows along it", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  await userEvent.click(within(sheet).getAllByRole("button", { name: /^Channel from .+: what flows$/ })[0]);
  const edge = await screen.findByRole("complementary", { name: /→ BWA \(channel\)$/ });
  expect(within(edge).getByText(/Files emitted upstream/)).toBeInTheDocument();
});

test("a channel lists the upstream files, published or still in a work directory, each previewable", async () => {
  const trim = `${URL_}/processes/${encodeURIComponent(`${P}ALIGN:TRIM`)}/outputs`;
  mocks(["graph_view"], {
    [trim]: { items: [{ path: "S1.trimmed.fq.gz", work_path: "S1.trimmed.fq.gz", task_id: "tsk_9", attempt_n: 1, state: "present", temp: false, root: "work", size: 4096 }] },
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  await userEvent.click(within(sheet).getByRole("button", { name: /^Channel from TRIM: what flows$/ }));
  const edge = await screen.findByRole("complementary", { name: /^TRIM → BWA \(channel\)$/ });
  expect(await within(edge).findByRole("button", { name: "First lines of S1.trimmed.fq.gz" })).toBeInTheDocument();
  expect(within(edge).getByRole("link", { name: "Open S1.trimmed.fq.gz" })).toHaveAttribute("href", expect.stringContaining("/workdir/file"));
});

test("Snakemake: a link is files, and lists what the upstream rule wrote", async () => {
  const trim = `${URL_}/processes/${encodeURIComponent(`${P}ALIGN:TRIM`)}/outputs`;
  mocks(["graph_view"], {
    [`${URL_}/graph`]: { ...DOC, engine: "snakemake" },
    [trim]: { items: [{ path: "trimmed/S1.fq.gz", task_id: "tsk_9", attempt_n: 1, state: "present", temp: false, root: "launch", size: 4096 }] },
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: /^BWA/ });
  await userEvent.click(within(sheet).getByRole("button", { name: /^Files from TRIM: what flows$/ }));
  const edge = await screen.findByRole("complementary", { name: /^TRIM → BWA \(files\)$/ });
  expect(within(edge).getByText(/Files written upstream/)).toBeInTheDocument();
  expect(await within(edge).findByRole("button", { name: "First lines of trimmed/S1.fq.gz" })).toBeInTheDocument();
});

test("a link whose upstream step has not run says nothing has flowed", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process REPORT" }));
  const sheet = await screen.findByRole("complementary", { name: "REPORT (process)" });
  await userEvent.click(within(sheet).getAllByRole("button", { name: /^Channel from .+: what flows$/ }).find((b) => /QC gate/.test(b.getAttribute("aria-label") ?? ""))!);
  const edge = await screen.findByRole("complementary", { name: /→ REPORT \(channel\)$/ });
  expect(within(edge).getByText(/has not run yet: nothing has flowed/)).toBeInTheDocument();
});

test("keyPairs splits Snakemake wildcards and keeps a Nextflow tag whole", () => {
  expect(keyPairs("region=chr1, sample=A")).toEqual([
    ["region", "chr1"],
    ["sample", "A"],
  ]);
  expect(keyPairs("S1 (lane 2)")).toEqual([["tag", "S1 (lane 2)"]]);
  expect(keyPairs(null)).toEqual([]);
});

test("Escape closes a step's details and focus goes back to what opened them", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  const opener = within(await listView()).getByRole("button", { name: "Open process BWA" });
  await userEvent.click(opener);
  const panel = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(within(panel).getByRole("heading", { name: /^BWA/ })).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("complementary", { name: "BWA (process)" })).toBeNull());
  expect(within(await listView()).getByRole("button", { name: "Open process BWA" })).toHaveFocus();
});

test("an output's first lines open in place; a BAM has no first lines but opens in the preview page", async () => {
  const bwa = `${URL_}/processes/${encodeURIComponent(`${P}ALIGN:BWA`)}/outputs`;
  mocks(["graph_view"], {
    [bwa]: { items: [{ path: "trim/S1.fq.gz", task_id: "tsk_1", attempt_n: 1, state: "present", temp: false, root: "results", size: 2048 }, { path: "align/S1.bam", task_id: "tsk_1", attempt_n: 1, state: "present", temp: false, root: "results", size: 3 * 2 ** 30 }] },
    [`${bwa}:head`]: { text: "@r1\nACGT\n+\nIIII", more: true, gzip: true },
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(await within(sheet).findByText(/3 GiB/)).toBeInTheDocument();
  expect(within(sheet).queryByRole("button", { name: "First lines of align/S1.bam" })).toBeNull();
  expect(within(sheet).getByRole("link", { name: "Open align/S1.bam" })).toBeInTheDocument();
  const peek = within(sheet).getByRole("button", { name: "First lines of trim/S1.fq.gz" });
  await userEvent.click(peek);
  expect(peek).toHaveAttribute("aria-expanded", "true");
  expect(await within(sheet).findByText(/ACGT/)).toBeInTheDocument();
});

test("Hide leaves a step out, says so, and Show all brings it back; Focus shows one group", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process TRIM" }));
  const sheet = await screen.findByRole("complementary", { name: "TRIM (process)" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Hide TRIM from the map" }));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ hide: `${P}ALIGN:TRIM` }));
  expect(within(await listView()).queryByRole("button", { name: "Open process TRIM" })).toBeNull();
  expect(screen.getByText(/1 step is hidden/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Show all" }));
  expect(await within(await listView()).findByRole("button", { name: "Open process TRIM" })).toBeInTheDocument();
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  await userEvent.click(within(await screen.findByRole("complementary", { name: "BWA (process)" })).getByRole("button", { name: "Focus: show only ALIGN" }));
  await waitFor(() => expect(within(screen.getByRole("table", { name: "Graph as a list" })).getAllByRole("button").map((b) => b.textContent).sort()).toEqual(["BWA", "TRIM"]));
  expect(screen.getByText(/Only ALIGN is shown/)).toBeInTheDocument();
});

test("Escape in the search box clears it", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&show=list`);
  const box = await screen.findByRole("textbox", { name: "Search" });
  await userEvent.type(box, "bwa");
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(box).toHaveValue(""));
});

test("Focus at the Subworkflow level opens the group and shows only its steps (CR-02)", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list&level=subworkflow&fold=sub:${P}ALIGN`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  await userEvent.click(within(await screen.findByRole("complementary", { name: "BWA (process)" })).getByRole("button", { name: "Focus: show only ALIGN" }));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ focus: `sub:${P}ALIGN` }));
  await waitFor(() => expect(within(screen.getByRole("table", { name: "Graph as a list" })).getAllByRole("button").map((b) => b.textContent).sort()).toEqual(["BWA", "TRIM"]));
});

test("a step folded away after it was opened dims nothing on the map (CR-01)", async () => {
  mocks();
  app(`/runs/${ID}?tab=graph&node=${encodeURIComponent(`${P}ALIGN:BWA`)}&fold=sub:${P}ALIGN`);
  await screen.findByRole("toolbar", { name: "Graph view" });
  await waitFor(() => expect(document.querySelectorAll(".sp-gnode").length).toBeGreaterThan(0));
  expect(document.querySelectorAll(".sp-gnode[data-dim]")).toHaveLength(0);
});

test("an output whose path climbs out of its folder gets no thumbnail, no first lines and no link (SEC-160-07)", async () => {
  const bwa = `${URL_}/processes/${encodeURIComponent(`${P}ALIGN:BWA`)}/outputs`;
  mocks(["graph_view"], {
    [bwa]: { items: [{ path: "x.png", work_path: "../../x.png", task_id: "tsk_1", attempt_n: 1, state: "present", temp: false, root: "absolute", size: 10 }] },
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(await within(sheet).findByText("x.png")).toBeInTheDocument();
  expect(within(sheet).queryByRole("link", { name: "Open x.png" })).toBeNull();
  expect(sheet.querySelector("img")).toBeNull();
});

test("groupsAround names a step's stage and its subworkflow chain", () => {
  expect(groupsAround(DOC, `${P}ALIGN:BWA`).sort()).toEqual(["stage:align", "sub:NFCORE_DEMO", "sub:NFCORE_DEMO:DEMO", "sub:NFCORE_DEMO:DEMO:ALIGN"].sort());
});

test("a link says the channel type each side declares in its code", async () => {
  const code = (id: string) =>
    id === `${P}ALIGN:TRIM`
      ? "process TRIM {\n  output:\n  tuple val(meta), path('*.fq.gz'), emit: reads\n  script:\n  ''\n}"
      : id === `${P}ALIGN:BWA`
        ? "process BWA {\n  input:\n  tuple val(meta), path(reads)\n  path index\n  script:\n  ''\n}"
        : null;
  mocks(["graph_view"], { [`${URL_}/graph`]: { ...DOC, nodes: DOC.nodes.map((n) => ({ ...n, code: code(n.id) })) } });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  await userEvent.click(within(sheet).getByRole("button", { name: /^Channel from TRIM: what flows$/ }));
  const edge = await screen.findByRole("complementary", { name: /^TRIM → BWA \(channel\)$/ });
  // one row per part, aligned: the channel's name, its kind, its value
  const emits = within(edge).getByRole("table", { name: "TRIM emits" });
  const rows = within(emits).getAllByRole("row").map((r) => r.textContent);
  expect(rows).toEqual(["EmitKindValue", "readstuplevalmeta", "path'*.fq.gz'"]);
  expect(within(within(edge).getByRole("table", { name: "BWA takes" })).getByRole("cell", { name: "index" })).toBeInTheDocument();
});

test("a step whose jobs ran again lists them under Executions, each opening its attempts", async () => {
  mocks(["graph_view"], {
    [`${URL_}/tasks`]: { items: [{ id: "tsk_7", process: `${P}ALIGN:BWA`, tag: "S2", name: null, state: "succeeded", stage_id: "align", attempt_n: 3, resources: {} }], next: null },
  });
  app(`/runs/${ID}?tab=graph&show=list`);
  await userEvent.click(within(await listView()).getByRole("button", { name: "Open process BWA" }));
  const sheet = await screen.findByRole("complementary", { name: "BWA (process)" });
  expect(await within(sheet).findByRole("button", { name: /^Open S2: 3 attempts/ })).toBeInTheDocument();
});

test("at the Subworkflow level, a step listed in a group's sheet opens that group and the step's sheet", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list&level=subworkflow`);
  await userEvent.click(within(await listView()).getByRole("button", { name: /^Open subworkflow ALIGN/ }));
  const group = await screen.findByRole("complementary", { name: /^ALIGN/ });
  await userEvent.click(within(group).getByRole("button", { name: /^Show BWA on the graph/ }));
  expect(await screen.findByRole("complementary", { name: "BWA (process)" })).toBeInTheDocument();
  expect(router.state.location.search).toMatchObject({ level: "subworkflow" });
  expect(String(router.state.location.search.fold)).toContain(`sub:${P}ALIGN`);
});

test("a click on the empty map closes what is open and clears the lit steps", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph`);
  fireEvent.click(await bwaOnMap(), { detail: 1 });
  await screen.findByRole("complementary", { name: "BWA (process)" });
  fireEvent.click(document.querySelector(".react-flow__pane")!);
  await waitFor(() => expect(screen.queryByRole("complementary", { name: "BWA (process)" })).toBeNull());
  expect(router.state.location.search.node).toBeUndefined();
});

test("paramOf gives each parameter's kind and text, and says when the run left it to the default", () => {
  const params = { genome: "GRCh38", input: "data/samples.csv", skip_qc: false, n: 3, xs: [1, 2], o: { a: 1 }, z: null };
  expect(paramOf(params, "genome")).toEqual({ kind: "text", text: "GRCh38", set: true });
  expect(paramOf(params, "input").kind).toBe("path");
  expect(paramOf(params, "skip_qc")).toEqual({ kind: "yes/no", text: "false", set: true });
  expect(paramOf(params, "n").kind).toBe("number");
  expect(paramOf(params, "xs")).toEqual({ kind: "list of 2", text: "1, 2", set: true });
  expect(paramOf(params, "o").kind).toBe("map");
  expect(paramOf(params, "o.a").text).toBe("1");
  expect(paramOf(params, "z").kind).toBe("null");
  expect(paramOf(params, "missing").set).toBe(false);
});

test("Escape with nothing open leaves Focus first; an Escape from outside the graph does nothing", async () => {
  mocks();
  const router = app(`/runs/${ID}?tab=graph&show=list&focus=sub:${P}ALIGN`);
  await listView();
  const outside = document.createElement("div");
  outside.tabIndex = -1;
  document.body.append(outside);
  fireEvent.keyDown(outside, { key: "Escape" });
  expect(router.state.location.search).toMatchObject({ focus: `sub:${P}ALIGN` });
  outside.remove();
  fireEvent.keyDown(document.body, { key: "Escape" });
  await waitFor(() => expect(router.state.location.search.focus).toBeUndefined());
});
