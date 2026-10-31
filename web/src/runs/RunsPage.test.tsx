import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const SUMMARY = { groups: [{ key: "running", count: 1 }, { key: "failed", count: 1 }] };
const observed = run({
  id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V2X",
  name: "pilot-hand",
  origin: "cli-observed",
  head: { session: null, node: "login1", alive: true, exit_code: null },
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
  const table = await screen.findByRole("table");
  const header = within(table).getAllByRole("columnheader").map((h) => h.textContent);
  expect(header).toEqual(["Run", "State", "Workflow", "Tasks", "Started", "Duration"]);
  expect(within(table).getByRole("columnheader", { name: "Started" })).toHaveAttribute("data-wide");
  const open = within(table).getByRole("link", { name: "Open run rnaseq-a" });
  expect(open).toHaveAttribute("href", "/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W");
  const row = open.closest("tr")!;
  expect(within(row).getByText("Running")).toBeInTheDocument();
  expect(within(row).getByText("24 / 32")).toBeInTheDocument();
  expect(within(row).getByText("7T9V1W")).toBeInTheDocument();
  const hand = within(table).getByRole("link", { name: "Open run pilot-hand" }).closest("tr")!;
  expect(within(hand).getByText("From a terminal")).toBeInTheDocument();
  const bad = within(table).getByRole("link", { name: "Open run sarek-c" }).closest("tr")!;
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

test("UX-PAR-01: each row shows its engine's mark, never the nf-core mark", async () => {
  const snake = run({
    id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V4Z",
    name: "plate-qc-a",
    workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/plate-qc", name: "plate-qc", version: null },
    summary: { tasks: { done: 31, total: 96, failed: 0, cached: 0 }, last_failure: null },
  });
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run(), snake], next: null } });
  app("/runs");
  const table = await screen.findByRole("table");
  const nf = within(table).getByRole("link", { name: "Open run rnaseq-a" }).closest("tr")!;
  const mark = within(nf).getByRole("img", { name: "Nextflow" });
  expect(mark.getAttribute("src")).toMatch(/logo-nextflow/);
  expect(Number(mark.getAttribute("width"))).toBeGreaterThanOrEqual(16);
  expect(Number(mark.getAttribute("width"))).toBeLessThanOrEqual(24);
  expect(within(table).queryByRole("img", { name: /nf-core/i })).toBeNull();
  expect(document.querySelector('img[src*="nf-core"]')).toBeNull();
  // The version sits on the name's line (UX-PAR-17), Nextflow's running total is "known so far".
  expect(within(nf).getByText("nf-core/rnaseq").parentElement).toHaveTextContent("nf-core/rnaseq 3.27.0");
  expect(within(nf).getByText("known so far")).toBeInTheDocument();
  const sm = within(table).getByRole("link", { name: "Open run plate-qc-a" }).closest("tr")!;
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

test("UX-PAR-18: the footer counts the rows shown against the filter's total", async () => {
  serve({ "/api/v1/runs:summary": SUMMARY, "/api/v1/runs": { items: [run()], next: "abc" } });
  app("/runs");
  expect(await screen.findByText("1 of 2 runs · newest first")).toBeInTheDocument();
  expect(screen.getByRole("searchbox", { name: "Filter by run name" })).toBeInTheDocument();
});
