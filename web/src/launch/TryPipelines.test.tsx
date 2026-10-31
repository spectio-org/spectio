// "Try a test pipeline" in Launch (P3-parD, Thomas 2026-10-31: "pas de wf par défaut de test dans
// launch pour tester"): the pipelines this server ran recently, one click fills the field and loads
// it; with none, how to get one. And /launch?location= opens Launch on a pipeline (Home's links).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, fetched, run, serve, stubStream, viewport } from "../testing";
import { recentPipelines } from "./TryPipelines";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const at = (location: string, name: string | null, engine = "nextflow", n = 0) =>
  run({
    id: `run_01JBC6Q4ZK7M8N2P3R5S7T9V${String(n).padStart(2, "0")}`,
    workflow: { engine, engine_version: null, location, name, version: null },
  });

const INSPECTED = {
  location: "/g/demo-lab/pipelines/synthetic",
  revision: null,
  engine: "nextflow",
  engine_files: ["main.nf"],
  name: "spectio/synthetic-scenarios",
  version: "0.1.0",
  engine_version: "26.10.4",
  engine_versions: { nextflow: "26.10.4" },
  schema: null,
  schema_source: "none",
  profiles: ["test"],
};

test("recentPipelines: distinct locations, newest first, at most five", () => {
  const runs = [
    at("/p/a", "a"),
    at("/p/b", "b"),
    at("/p/a", "a"),
    at("/p/c", null),
    at("/p/d", "d"),
    at("/p/e", "e"),
    at("/p/f", "f"),
  ];
  expect(recentPipelines(runs as never).map((r) => r.workflow.location)).toEqual(["/p/a", "/p/b", "/p/c", "/p/d", "/p/e"]);
});

test("Launch lists the pipelines this server ran; one click fills the field and loads it", async () => {
  const mock = serve({
    "/api/v1/runs": {
      items: [at("/g/demo-lab/pipelines/nf-core-demo", "nf-core/demo"), at("/g/demo-lab/pipelines/synthetic-smk", "synthetic-smk", "snakemake")],
      next: null,
    },
    "/api/v1/workflows:inspect": INSPECTED,
  });
  app("/launch");
  const group = await screen.findByRole("group", { name: "Try a test pipeline" });
  const demo = await within(group).findByRole("button", { name: "Use nf-core/demo, /g/demo-lab/pipelines/nf-core-demo" });
  expect(within(demo).getByRole("img", { name: "nf-core" })).toBeInTheDocument();
  const smk = within(group).getByRole("button", { name: "Use synthetic-smk, /g/demo-lab/pipelines/synthetic-smk" });
  expect(within(smk).getByRole("img", { name: "Snakemake" })).toBeInTheDocument();
  await userEvent.click(demo);
  expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("/g/demo-lab/pipelines/nf-core-demo");
  expect(await screen.findByText("Loaded")).toBeInTheDocument();
  expect(fetched(mock)).toContain("/api/v1/workflows:inspect?location=/g/demo-lab/pipelines/nf-core-demo");
  expect(fetched(mock)).toContain("/api/v1/runs?limit=50");
});

test("with no run on this server, Launch says how to get a test pipeline", async () => {
  serve({ "/api/v1/runs": { items: [], next: null } });
  app("/launch");
  expect(await screen.findByText(/No pipeline has run on this server yet/)).toBeInTheDocument();
  const link = screen.getByRole("link", { name: /How to get the synthetic test pipelines/ });
  expect(link).toHaveAttribute("href", expect.stringContaining("dev-environment-and-testing/#101-synthetic-scenario-pipelines"));
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

test("/launch?location= opens Launch on that pipeline and loads it", async () => {
  const mock = serve({ "/api/v1/runs": { items: [], next: null }, "/api/v1/workflows:inspect": INSPECTED });
  app("/launch?location=%2Fg%2Fdemo-lab%2Fpipelines%2Fsynthetic");
  expect(await screen.findByText("Loaded")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("/g/demo-lab/pipelines/synthetic");
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/workflows:inspect?location=/g/demo-lab/pipelines/synthetic"));
});

test("a repository from the list fills the field and asks for its revision, without loading", async () => {
  const mock = serve({ "/api/v1/runs": { items: [at("nf-core/rnaseq", "nf-core/rnaseq")], next: null } });
  app("/launch");
  await userEvent.click(await screen.findByRole("button", { name: "Use nf-core/rnaseq, nf-core/rnaseq" }));
  expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("nf-core/rnaseq");
  expect(screen.getByRole("textbox", { name: /Revision/ })).toHaveFocus();
  expect(fetched(mock).some((u) => u.startsWith("/api/v1/workflows:inspect"))).toBe(false);
});

test("on the phone, the test pipelines are native buttons too", async () => {
  viewport(390);
  serve({ "/api/v1/runs": { items: [at("/p/a", "a")], next: null } });
  app("/launch");
  const group = await screen.findByRole("group", { name: "Try a test pipeline" });
  expect((await within(group).findByRole("button", { name: "Use a, /p/a" })).tagName).toBe("BUTTON");
});
