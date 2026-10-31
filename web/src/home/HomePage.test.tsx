import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, run, serve, stubStream } from "../testing";

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
