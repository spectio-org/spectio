import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, fetched, json, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const SUMMARY = { groups: [{ key: "running", count: 1 }, { key: "failed", count: 1 }] };
const observed = run({
  id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V2X",
  name: "pilot-hand",
  origin: "cli-observed",
  head: { session: null, node: "login1", alive: true, exit_code: null, checked: true },
});
const failed = run({
  id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V3Y",
  name: "sarek-c",
  state: "failed",
  ended_at: "2026-10-31T08:00:00+00:00",
  failure: { class: "task_failed", message: "exit 1 · DEEPVARIANT (NA12878)" },
});

test('the empty list reads "No runs yet." with a link to launch', async () => {
  serve({ "/api/v1/runs:summary": { groups: [] }, "/api/v1/runs": { items: [], next: null } });
  app("/runs");
  const empty = (await screen.findByText("No runs yet.")).parentElement!;
  expect(within(empty).getByRole("link", { name: "Launch a workflow" })).toHaveAttribute("href", "/launch");
  expect(screen.getByRole("heading", { level: 1, name: "Runs" })).toBeInTheDocument();
});

test("the table shows each run with its state word, a row label and the terminal chip", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), observed, failed], next: null } });
  app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  const header = within(table).getAllByRole("columnheader").map((h) => h.textContent?.trim());
  expect(header).toEqual(["", "Run", "State", "Workflow", "Tasks", "Started", "Duration"]);
  // the API's order, newest first: no header is sorted until one is pressed (FU-P3-115b)
  expect(within(table).getByRole("columnheader", { name: "Run" })).toHaveAttribute("aria-sort", "none");
  const open = within(table).getByRole("link", { name: "Open run rnaseq-a" });
  expect(open).toHaveAttribute("href", "/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W");
  const row = open.closest('[role="row"]') as HTMLElement;
  expect(within(row).getByText("Running")).toBeInTheDocument();
  expect(within(row).getByText("24 / 32")).toBeInTheDocument();
  expect(within(row).getByText("7T9V1W")).toBeInTheDocument();
  const hand = within(table).getByRole("link", { name: "Open run pilot-hand" }).closest('[role="row"]') as HTMLElement;
  expect(within(hand).getByText("From a terminal")).toBeInTheDocument();
  const bad = within(table).getByRole("link", { name: "Open run sarek-c" }).closest('[role="row"]') as HTMLElement;
  expect(within(bad).getByText("Failed")).toBeInTheDocument();
  expect(within(bad).getByText("task failed · exit 1 · DEEPVARIANT (NA12878)")).toBeInTheDocument();
});

test("state filters are pressed buttons and the name filter asks for a prefix", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  const all = await screen.findByRole("button", { name: /^All/ });
  expect(all).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: /^Failed/ }));
  expect(screen.getByRole("button", { name: /^Failed/ })).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?state=failed&limit=50"));
  await userEvent.click(screen.getByRole("button", { name: /^Active/ }));
  await waitFor(() =>
    expect(fetched(mock)).toContain("/api/v1/runs?state=queued,running,pausing,paused,awaiting_review,cancelling&limit=50"),
  );
  await userEvent.type(screen.getByRole("searchbox", { name: "Filter by run name" }), "rna");
  await waitFor(() => expect(fetched(mock).some((u) => u.includes("q=rna"))).toBe(true));
});

test("Load more asks for the next page and appends it", async () => {
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs?limit=50&cursor=abc": { items: [failed], next: null },
    "/api/v1/runs": { items: [run()], next: "abc" },
  });
  app("/runs");
  await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
  expect(await screen.findByRole("link", { name: "Open run sarek-c" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open run rnaseq-a" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
});

test("a stream frame refetches the list; a lost stream reads Reconnecting…", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  await screen.findByRole("link", { name: "Open run rnaseq-a" });
  const stream = FakeEventSource.last!;
  expect(stream.url).toBe("/api/v1/events/stream");
  stream.open();
  expect(await screen.findByText(/live, updated \d+ s ago/)).toBeInTheDocument();
  const before = fetched(mock).filter((u) => u.startsWith("/api/v1/runs?")).length;
  stream.frame({ run_id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W" });
  await waitFor(
    () => expect(fetched(mock).filter((u) => u.startsWith("/api/v1/runs?")).length).toBeGreaterThan(before),
    { timeout: 3000 },
  );
  stream.fail();
  expect(await screen.findByText("Reconnecting…")).toBeInTheDocument();
});

test("an older response that lands last does not overwrite the list of the pressed filter", async () => {
  let release: () => void = () => {};
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs?state=failed": { items: [failed], next: null },
    "/api/v1/runs": () => new Promise<Response>((done) => (release = () => done(json(200, { items: [run()], next: null })))),
  });
  app("/runs");
  await userEvent.click(await screen.findByRole("button", { name: /^Failed/ }));
  expect(await screen.findByRole("link", { name: "Open run sarek-c" })).toBeInTheDocument();
  release();
  await new Promise((r) => setTimeout(r, 50));
  expect(screen.queryByRole("link", { name: "Open run rnaseq-a" })).toBeNull();
  expect(screen.getByRole("link", { name: "Open run sarek-c" })).toBeInTheDocument();
});

test("a stream frame refreshes the first page and keeps the rows Load more added, and the cursor", async () => {
  const older = run({ id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V0A", name: "old-b", created_at: "2026-10-30T07:40:00+00:00" });
  const mock = serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs?limit=50&cursor=abc": { items: [older], next: "def" },
    "/api/v1/runs": { items: [run()], next: "abc" },
  });
  app("/runs");
  await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
  expect(await screen.findByRole("link", { name: "Open run old-b" })).toBeInTheDocument();
  const stream = FakeEventSource.last!;
  stream.open();
  const before = fetched(mock).filter((u) => u === "/api/v1/runs?limit=50").length;
  stream.frame({ run_id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W" });
  await waitFor(() => expect(fetched(mock).filter((u) => u === "/api/v1/runs?limit=50").length).toBeGreaterThan(before), {
    timeout: 3000,
  });
  await new Promise((r) => setTimeout(r, 50));
  expect(screen.getByRole("link", { name: "Open run old-b" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open run rnaseq-a" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Load more" }));
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?limit=50&cursor=def"));
});

test("UX-PAR-01, inbox #91 (b): each row shows its pipeline's mark: nf-core for an nf-core/ name, else the engine's", async () => {
  const snake = run({
    id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V4Z",
    name: "plate-qc-a",
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/plate-qc", name: "plate-qc", version: null },
    summary: { tasks: { done: 31, total: 96, failed: 0, cached: 0 }, last_failure: null, stage_mode: "quarters" },
  });
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), snake], next: null } });
  app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  const nf = within(table).getByRole("link", { name: "Open run rnaseq-a" }).closest('[role="row"]') as HTMLElement;
  const mark = within(nf).getByRole("img", { name: "nf-core" });
  expect(mark.getAttribute("src")).toMatch(/logo-nf-core/);
  expect(Number(mark.getAttribute("width"))).toBeGreaterThanOrEqual(16);
  expect(Number(mark.getAttribute("width"))).toBeLessThanOrEqual(24);
  // The version sits on the name's line (UX-PAR-17), Nextflow's running total is "known so far".
  expect(within(nf).getByText("nf-core/rnaseq").parentElement).toHaveTextContent("nf-core/rnaseq 3.27.0");
  expect(within(nf).getByText("known so far")).toBeInTheDocument();
  const sm = within(table).getByRole("link", { name: "Open run plate-qc-a" }).closest('[role="row"]') as HTMLElement;
  expect(within(sm).getByRole("img", { name: "Snakemake" }).getAttribute("src")).toMatch(/logo-snakemake/);
  expect(within(sm).getByText("jobs")).toBeInTheDocument(); // UX-PAR-20
  expect(within(sm).getByText("3 jobs running")).toBeInTheDocument();
});

test("UX-PAR-12: the state filter lives in the URL, so Home's cards can link to it", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [failed], next: null } });
  const router = app("/runs?state=failed");
  expect(await screen.findByRole("button", { name: /^Failed/ })).toHaveAttribute("aria-pressed", "true");
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?state=failed&limit=50"));
  await userEvent.click(screen.getByRole("button", { name: /^All/ }));
  await waitFor(() => expect(router.state.location.search).toEqual({}));
  await userEvent.click(screen.getByRole("button", { name: /^Active/ }));
  await waitFor(() => expect(router.state.location.search).toEqual({ state: "active" }));
});

test("UX-PAR-12: the name filter lives in the URL too, next to the state filter", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [failed], next: null } });
  const router = app("/runs?state=failed&q=sar");
  expect(await screen.findByRole("searchbox", { name: "Filter by run name" })).toHaveValue("sar");
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?state=failed&q=sar&limit=50"));
  await userEvent.type(screen.getByRole("searchbox", { name: "Filter by run name" }), "ek");
  await waitFor(() => expect(router.state.location.search).toEqual({ state: "failed", q: "sarek" }));
  await userEvent.click(screen.getByRole("button", { name: /^All/ }));
  await waitFor(() => expect(router.state.location.search).toEqual({ q: "sarek" }));
  await userEvent.clear(screen.getByRole("searchbox", { name: "Filter by run name" }));
  await waitFor(() => expect(router.state.location.search).toEqual({}));
});

test("CR-P3PARA-09: the name box follows the URL when a link drops or changes q", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [failed], next: null } });
  const router = app("/runs?q=sar");
  const box = await screen.findByRole("searchbox", { name: "Filter by run name" });
  expect(box).toHaveValue("sar");
  // The sidebar's Runs link goes to /runs, with no q: the box empties with the list.
  await userEvent.click(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: /^Runs/ }));
  await waitFor(() => expect(box).toHaveValue(""));
  act(() => void router.navigate({ to: "/runs", search: { q: "rna" } }));
  await waitFor(() => expect(box).toHaveValue("rna"));
  // Typing still lands in the URL, and a trailing space the user typed stays in the box.
  await userEvent.type(box, "seq ");
  await waitFor(() => expect(router.state.location.search).toEqual({ q: "rnaseq" }));
  await new Promise((r) => setTimeout(r, 300));
  expect(box).toHaveValue("rnaseq ");
});

test("UX-PAR-18: the footer counts the rows shown against the filter's total", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: "abc" } });
  app("/runs");
  expect(await screen.findByText("1 of 2 runs · newest first")).toBeInTheDocument();
  expect(screen.getByRole("searchbox", { name: "Filter by run name" })).toBeInTheDocument();
});

test("UX-G3a-05: below 1100 px the grid drops Started, so it fits at 1024 px", async () => {
  viewport(1024);
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  expect(within(table).getAllByRole("columnheader").map((h) => h.textContent?.trim())).toEqual(["", "Run", "State", "Workflow", "Tasks", "Duration"]);
});

test("a cell takes focus from the keyboard: the header, then the first run's name cell", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), failed], next: null } });
  app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  act(() => within(table).getByRole("columnheader", { name: "Run" }).focus());
  await userEvent.keyboard("{ArrowDown}");
  await waitFor(() => expect(document.activeElement).toHaveAttribute("role", "gridcell"));
  expect(document.activeElement).toHaveTextContent("rnaseq-a");
});

test("CR-P3FU101A-01: Enter on a run's name cell opens the run", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), failed], next: null } });
  const router = app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  act(() => within(table).getByRole("columnheader", { name: "Run" }).focus());
  await userEvent.keyboard("{ArrowDown}");
  await waitFor(() => expect(document.activeElement).toHaveTextContent("rnaseq-a"));
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(router.state.location.pathname).toBe("/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W"));
});

// FU-P3-115b: selection, the bulk bar and its Delete sheet, the pin button, sortable headers.
const done = run({ id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V5Q", name: "atac-d", state: "succeeded", ended_at: "2026-10-31T09:00:00+00:00" });
const LIST = { "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), failed, done], next: null } };
const tick = (name: string) => userEvent.click(screen.getByRole("checkbox", { name: `Select run ${name}` }));

test("FU-P3-115b: a selected run that has not ended keeps Delete refused, with its reason", async () => {
  serve(LIST);
  app("/runs");
  await screen.findByRole("grid", { name: "Runs" });
  await tick("sarek-c");
  expect(screen.getByText("1 selected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete…" })).not.toHaveAttribute("aria-disabled");
  await tick("rnaseq-a");
  const del = screen.getByRole("button", { name: "Delete…" });
  expect(del).toHaveAttribute("aria-disabled", "true");
  expect(del).toHaveAccessibleDescription("1 selected run has not ended: cancel it first");
  await userEvent.click(del);
  expect(screen.queryByRole("dialog")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Clear selection" }));
  expect(screen.queryByText(/selected$/)).toBeNull();
  expect(screen.getByRole("checkbox", { name: "Select run sarek-c" })).not.toBeChecked();
});

test("FU-P3-115b: the Delete sheet lists the runs and sends directories only when ticked", async () => {
  const bodies: unknown[] = [];
  serve({
    ...LIST,
    "/api/v1/runs:delete": (_url: URL, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)));
      return json(200, { deleted: [failed.id, done.id], directories: [] });
    },
  });
  app("/runs");
  await screen.findByRole("grid", { name: "Runs" });
  await userEvent.click(screen.getByRole("checkbox", { name: "Select all runs on this page" }));
  await tick("rnaseq-a");
  const opener = screen.getByRole("button", { name: "Delete…" });
  await userEvent.click(opener);
  const sheet = await screen.findByRole("dialog", { name: "Delete 2 runs?" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(within(sheet).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["sarek-c · Failed", "atac-d · Succeeded"]);
  expect(within(sheet).getByRole("checkbox", { name: "Also delete their run directories" })).not.toBeChecked();
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(bodies).toEqual([{ ids: [failed.id, done.id], directories: false }]));
  expect(await screen.findByText("2 runs deleted")).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  // Delete… has gone with the selection: focus lands on what the delete said
  await waitFor(() => expect(document.activeElement).toHaveTextContent("2 runs deleted"));

  await tick("atac-d");
  await userEvent.click(screen.getByRole("button", { name: "Delete…" }));
  const again = await screen.findByRole("dialog", { name: "Delete 1 run?" });
  await userEvent.click(within(again).getByRole("checkbox", { name: "Also delete their run directories" }));
  await userEvent.click(within(again).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(bodies[1]).toEqual({ ids: [done.id], directories: true }));
});

test("FU-P3-115b: a 409 keeps the sheet open with the run named and why", async () => {
  serve({
    ...LIST,
    "/api/v1/runs:delete": () =>
      json(409, {
      type: "/problems/directory-not-removable",
      title: "Directory not removable",
      detail: "Spectio removes only a run directory it created and no other run uses.",
      errors: [{ field: failed.id, message: "started from a terminal: its launch directory is your own" }],
    }),
  });
  app("/runs");
  await screen.findByRole("grid", { name: "Runs" });
  await tick("sarek-c");
  await userEvent.click(screen.getByRole("button", { name: "Delete…" }));
  const sheet = await screen.findByRole("dialog", { name: "Delete 1 run?" });
  await userEvent.click(within(sheet).getByRole("checkbox", { name: "Also delete their run directories" }));
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete" }));
  const alert = await within(sheet).findByRole("alert");
  expect(alert).toHaveTextContent("Nothing was deleted. Spectio removes only a run directory it created and no other run uses.");
  expect(alert).toHaveTextContent("sarek-c: started from a terminal: its launch directory is your own");
  expect(screen.getByRole("dialog", { name: "Delete 1 run?" })).toBeInTheDocument();
});

test("FU-P3-115b: the pin button is pressed for a pinned run and sends PATCH pinned", async () => {
  const calls: { url: string; method?: string; body?: string }[] = [];
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs/": (url: URL, init?: RequestInit) => {
      calls.push({ url: url.pathname, method: init?.method, body: String(init?.body) });
      return json(200, { ...failed, pinned: true });
    },
    "/api/v1/runs": { items: [run({ pinned: true }), failed], next: null },
  });
  app("/runs");
  await screen.findByRole("grid", { name: "Runs" });
  expect(screen.getByRole("button", { name: "Pin run rnaseq-a" })).toHaveAttribute("aria-pressed", "true");
  const pin = screen.getByRole("button", { name: "Pin run sarek-c" });
  expect(pin).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(pin);
  await waitFor(() => expect(calls).toEqual([{ url: `/api/v1/runs/${failed.id}`, method: "PATCH", body: '{"pinned":true}' }]));
});

test("FU-P3-115b: a header sorts on the server, lives in the URL, and the footer says the order", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), failed], next: "abc" } });
  const router = app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  const name = within(table).getByRole("columnheader", { name: "Run" });
  expect(name).toHaveAttribute("aria-sort", "none");
  act(() => name.focus());
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(router.state.location.search).toEqual({ sort: "name" }));
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?sort=name&limit=50"));
  expect(name).toHaveAttribute("aria-sort", "ascending");
  expect(await screen.findByText("2 of 2 runs · by name")).toBeInTheDocument();
  // the server's order stays: the grid does not sort the rows itself
  const links = within(table).getAllByRole("link").map((a) => a.textContent);
  expect(links).toEqual(["rnaseq-a", "sarek-c"]);
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?sort=-name&limit=50"));
  // a sort change asks for a first page: no cursor of the old order
  expect(fetched(mock).filter((u) => u.includes("cursor"))).toEqual([]);
});

test("FU-P3-115b: a sort from the URL is asked for and shown on its header", async () => {
  const mock = serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [failed], next: null } });
  app("/runs?sort=-duration&state=failed");
  const table = await screen.findByRole("grid", { name: "Runs" });
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/runs?state=failed&sort=-duration&limit=50"));
  await waitFor(() => expect(within(table).getByRole("columnheader", { name: "Duration" })).toHaveAttribute("aria-sort", "descending"));
  expect(screen.getByText(/longest first$/)).toBeInTheDocument();
});

test("FU-P3-115b: on a phone each card starts with its box, and the bulk bar follows it", async () => {
  viewport(360);
  serve(LIST);
  app("/runs");
  await screen.findByRole("list", { name: "Runs" });
  // its own class, not the select wrappers' full-width one; its label is the 44 px hit area (UX-P3FU115B-01, -02)
  const box = screen.getByRole("checkbox", { name: "Select run atac-d" });
  expect(box).toHaveClass("sp-row-check");
  expect(box).not.toHaveClass("sp-select");
  expect(box.parentElement).toHaveClass("sp-row-hit");
  await userEvent.click(box.parentElement!);
  expect(box).toBeChecked();
  expect(screen.getByText("1 selected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete…" })).not.toHaveAttribute("aria-disabled");
});

test("FU-P3-115b: from the keyboard, Space on a Select cell ticks its box and on the header ticks all", async () => {
  serve(LIST);
  app("/runs");
  const table = await screen.findByRole("grid", { name: "Runs" });
  const head = screen.getByRole("checkbox", { name: "Select all runs on this page" }).closest('[role="columnheader"]') as HTMLElement;
  act(() => within(table).getByRole("columnheader", { name: "Run" }).focus());
  await userEvent.keyboard("{ArrowDown}{ArrowLeft}");
  await waitFor(() => expect(document.activeElement).toHaveAttribute("aria-colindex", "1"));
  await userEvent.keyboard(" ");
  expect(screen.getByRole("checkbox", { name: "Select run rnaseq-a" })).toBeChecked();
  act(() => head.focus());
  await userEvent.keyboard(" ");
  expect(screen.getByText("3 selected")).toBeInTheDocument();
});

test("CR-P3FU115B-01: a run deleted from the rows Load more added leaves the list", async () => {
  const old = run({ id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V0A", name: "old-b", state: "succeeded", created_at: "2026-10-30T07:40:00+00:00", ended_at: "2026-10-30T08:00:00+00:00" });
  const oldest = run({ id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V0B", name: "old-c", state: "failed", created_at: "2026-10-30T07:30:00+00:00", ended_at: "2026-10-30T08:00:00+00:00" });
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs:delete": () => json(200, { deleted: [old.id], directories: [] }),
    "/api/v1/runs?limit=50&cursor=abc": { items: [old, oldest], next: "def" },
    "/api/v1/runs": { items: [run()], next: "abc" },
  });
  app("/runs");
  await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
  await screen.findByRole("link", { name: "Open run old-b" });
  await tick("old-b");
  await userEvent.click(screen.getByRole("button", { name: "Delete…" }));
  const sheet = await screen.findByRole("dialog", { name: "Delete 1 run?" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete" }));
  expect(await screen.findByText("1 run deleted")).toBeInTheDocument();
  await new Promise((r) => setTimeout(r, 50));
  expect(screen.queryByRole("link", { name: "Open run old-b" })).toBeNull();
  expect(screen.getByRole("link", { name: "Open run old-c" })).toBeInTheDocument();
});

test("CR-P3FU115B-02: under another sort, a row that leaves the first page stays, and Load more does not repeat it", async () => {
  let first = { items: [run(), failed], next: "abc" };
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs?sort=-duration&limit=50&cursor=abc": { items: [done], next: "def" },
    "/api/v1/runs?sort=-duration&limit=50&cursor=def": { items: [failed], next: null },
    "/api/v1/runs": () => json(200, first),
  });
  app("/runs?sort=-duration");
  await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
  await screen.findByRole("link", { name: "Open run atac-d" });
  first = { items: [run(), done], next: "abc" };
  const stream = FakeEventSource.last!;
  stream.open();
  stream.frame({ run_id: failed.id });
  await waitFor(() => expect(screen.getAllByRole("link", { name: "Open run atac-d" })).toHaveLength(1), { timeout: 3000 });
  await new Promise((r) => setTimeout(r, 1200));
  expect(screen.getByRole("link", { name: "Open run sarek-c" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Load more" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Load more" })).toBeNull());
  expect(screen.getAllByRole("link", { name: "Open run sarek-c" })).toHaveLength(1);
});

test("CR-P3FU115B-03: the grid sorts on one column only: Shift on a second header does not add a sort", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), failed], next: null } });
  app("/runs?sort=name");
  const table = await screen.findByRole("grid", { name: "Runs" });
  const name = within(table).getByRole("columnheader", { name: "Run" });
  await waitFor(() => expect(name).toHaveAttribute("aria-sort", "ascending"));
  const state = within(table).getByRole("columnheader", { name: "State" });
  act(() => state.focus());
  await userEvent.keyboard("{Shift>}{Enter}{/Shift}");
  await waitFor(() => expect(state).toHaveAttribute("aria-sort", "ascending"));
  expect(name).toHaveAttribute("aria-sort", "none");
});

test("CR-P3FU115B-04: a pin that succeeds clears what a failed one said", async () => {
  let fail = true;
  serve({
    "/api/v1/runs:summary": SUMMARY,
    "/api/v1/runs/": () => (fail ? json(500, { title: "Server error", detail: "boom" }) : json(200, { ...failed, pinned: true })),
    "/api/v1/runs": { items: [run(), failed], next: null },
  });
  app("/runs");
  await screen.findByRole("grid", { name: "Runs" });
  await userEvent.click(screen.getByRole("button", { name: "Pin run sarek-c" }));
  expect(await screen.findByText(/^sarek-c was not pinned/)).toBeInTheDocument();
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Pin run sarek-c" }));
  await waitFor(() => expect(screen.queryByText(/^sarek-c was not pinned/)).toBeNull());
});
