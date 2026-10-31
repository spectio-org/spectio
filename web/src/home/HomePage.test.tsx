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
});

test('home with no run reads "No runs yet."', async () => {
  serve({ "/api/v1/runs:summary": { groups: [] }, "/api/v1/runs": { items: [], next: null } });
  app("/");
  expect(await screen.findByText("No runs yet.")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Active runs" })).toBeNull();
});

test("a finished run whose failure has no message ends its line without a separator", async () => {
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
