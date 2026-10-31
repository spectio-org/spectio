import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, fetched, run, serve, stubStream } from "../testing";

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
  expect(within(bad).getByText("exit 1 · DEEPVARIANT (NA12878)")).toBeInTheDocument();
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
