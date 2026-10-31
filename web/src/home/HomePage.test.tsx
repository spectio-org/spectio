import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ended = run({
  id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V3Y",
  name: "fetch-geo-2610",
  state: "succeeded",
  ended_at: "2026-10-31T07:39:00+00:00",
  workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/plate-qc", name: "plate-qc", version: null },
});

test("home shows the count cards, the active runs, the runs that ended and the pipelines", async () => {
  serve({
    "/api/v1/runs:summary": { groups: [{ key: "running", count: 4 }, { key: "succeeded", count: 5 }] },
    "/api/v1/runs?sort=-ended_at": { items: [ended], next: null },
    "/api/v1/runs?state=": { items: [run()], next: null },
    "/api/v1/runs": { items: [run(), ended], next: null },
  });
  app("/");
  const cards = await screen.findByRole("list", { name: "Runs by state" });
  expect(within(cards).getByText("4")).toBeInTheDocument();
  expect(within(cards).getByText("5")).toBeInTheDocument();
  const active = screen.getByRole("region", { name: "Active runs" });
  expect(await within(active).findByRole("link", { name: "Open run rnaseq-a" })).toBeInTheDocument();
  const finished = screen.getByRole("region", { name: "Finished recently" });
  expect(await within(finished).findByRole("link", { name: "Open run fetch-geo-2610" })).toBeInTheDocument();
  const pipelines = screen.getByRole("region", { name: "Your pipelines" });
  expect(await within(pipelines).findByText("/g/demo-lab/pipelines/plate-qc")).toBeInTheDocument();
  expect(within(pipelines).getByText("/g/demo-lab/pipelines/rnaseq")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Launch a workflow" })).toHaveAttribute("href", "/launch");
  expect(within(active).getByRole("link", { name: "All runs" })).toHaveAttribute("href", "/runs");
  // inbox #91 (b): the pipeline's mark, nf-core for an nf-core/ name, else the engine's (P3-parC)
  const nf = within(active).getByRole("link", { name: "Open run rnaseq-a" }).closest("li")!;
  expect(within(nf).getByRole("img", { name: "nf-core" })).toBeInTheDocument();
  const sm = within(finished).getByRole("link", { name: "Open run fetch-geo-2610" }).closest("li")!;
  expect(within(sm).getByRole("img", { name: "Snakemake" })).toBeInTheDocument();
  expect(within(pipelines).getByRole("img", { name: "nf-core" })).toBeInTheDocument();
  expect(within(pipelines).getByRole("img", { name: "Snakemake" })).toBeInTheDocument();
});

test('home with no run reads "No runs yet."', async () => {
  serve({ "/api/v1/runs:summary": { groups: [] }, "/api/v1/runs": { items: [], next: null } });
  app("/");
  expect(await screen.findByText("No runs yet.")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Active runs" })).toBeNull();
});

test("a finished run whose failure has no message still says why (UX-PAR-16)", async () => {
  const failed = run({ ...ended, state: "failed", failure: { class: "tool_error", message: "", task_id: null, attempt_n: 1 } });
  serve({
    "/api/v1/runs:summary": { groups: [{ key: "failed", count: 1 }] },
    "/api/v1/runs?sort=-ended_at": { items: [failed], next: null },
    "/api/v1/runs?state=": { items: [], next: null },
    "/api/v1/runs": { items: [failed], next: null },
  });
  app("/");
  const finished = await screen.findByRole("region", { name: "Finished recently" });
  const row = (await within(finished).findByRole("link", { name: "Open run fetch-geo-2610" })).closest("li")!;
  expect(within(row).getByText("plate-qc")).toBeInTheDocument();
  expect(row).toHaveTextContent("plate-qc · tool error");
});

test("an older refresh that lands last does not overwrite a newer one", async () => {
  let calls = 0;
  let release: () => void = () => {};
  serve({
    "/api/v1/runs:summary": { groups: [{ key: "running", count: 1 }] },
    "/api/v1/runs?sort=-ended_at": { items: [], next: null },
    "/api/v1/runs?state=": () => {
      calls += 1;
      if (calls > 1) return json(200, { items: [run({ name: "newer" })], next: null });
      return new Promise<Response>((done) => (release = () => done(json(200, { items: [run({ name: "older" })], next: null }))));
    },
    "/api/v1/runs": { items: [], next: null },
  });
  app("/");
  await screen.findByRole("list", { name: "Runs by state" }).catch(() => undefined);
  FakeEventSource.last!.open();
  const active = await screen.findByRole("region", { name: "Active runs" });
  expect(await within(active).findByRole("link", { name: "Open run newer" })).toBeInTheDocument();
  release();
  await new Promise((r) => setTimeout(r, 50));
  expect(within(active).queryByRole("link", { name: "Open run older" })).toBeNull();
});

test("UX-PAR-11/12/13/16: subtitle words, linked cards with a detail line, a non-blank failure and where runs go", async () => {
  const failed = run({
    ...ended,
    id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V5A",
    name: "wgs-cohort-12",
    state: "failed",
    failure: { class: "tool_error", message: "", task_id: null, attempt_n: 1 },
    summary: { tasks: { done: 143, total: 175, failed: 2, cached: 0 }, last_failure: null },
  });
  const hand = run({ origin: "cli-observed", name: "pilot-hand" });
  serve({
    "/api/v1/runs:summary": { groups: [{ key: "running", count: 4 }, { key: "queued", count: 1 }, { key: "failed", count: 3 }] },
    "/api/v1/runs?sort=-ended_at": { items: [failed, ended], next: null },
    "/api/v1/runs?state=": { items: [hand, run()], next: null },
    "/api/v1/runs": { items: [run(), ended], next: null },
  });
  app("/");
  expect(await screen.findByText("4 runs running and 1 queued")).toBeInTheDocument();
  const cards = await screen.findByRole("list", { name: "Runs by state" });
  const failedCard = within(cards).getByRole("link", { name: "3 runs failed, show them" });
  expect(failedCard).toHaveAttribute("href", "/runs?state=failed");
  expect(within(failedCard).getByText("latest: wgs-cohort-12")).toBeInTheDocument();
  expect(within(cards).getByRole("link", { name: "4 runs running, show them" })).toHaveAttribute("href", "/runs?state=active");
  expect(within(cards).getByText("1 started from a terminal")).toBeInTheDocument();

  const finished = screen.getByRole("region", { name: "Finished recently" });
  const row = (await within(finished).findByRole("link", { name: "Open run wgs-cohort-12" })).closest("li")!;
  expect(within(row).getByText(/tool error · 2 jobs failed/)).toBeInTheDocument();
  expect(within(row).getByRole("img", { name: "Snakemake" })).toBeInTheDocument();

  const active = screen.getByRole("region", { name: "Active runs" });
  const handRow = within(active).getByRole("link", { name: "Open run pilot-hand" }).closest("li")!;
  expect(within(handRow).getByText(/from a terminal/)).toBeInTheDocument();

  const where = screen.getByRole("region", { name: "Where your runs go" });
  expect(await within(where).findByText("/scratch/amartin/spectio-runs")).toBeInTheDocument();
  expect(within(where).getByText(/Spectio 0.0.1 on login1, under your account amartin/)).toBeInTheDocument();
  // UX-PAR-33: one executor label, here and in the sidebar's foot.
  const sidebar = screen.getByRole("navigation", { name: "Main" });
  expect(within(sidebar).getByText(/^Local · server on login1/)).toBeInTheDocument();
});
