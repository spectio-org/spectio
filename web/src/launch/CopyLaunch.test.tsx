// Copy to a new launch (P1 Task 32 part two; ui-spec §4.4 run tools note; board LiteLaunch):
// /launch?from=<run> prefills the form from `GET /runs/{id}:launch-template`.
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const INSPECTED = {
  location: "/g/demo-lab/pipelines/rnaseq",
  revision: null,
  engine: "nextflow",
  engine_files: ["main.nf"],
  name: "rnaseq",
  version: "3.27.0",
  engine_version: "26.10.4",
  engine_versions: { nextflow: "26.10.4" },
  schema: {
    type: "object",
    required: ["input"],
    properties: {
      input: { type: "string" },
      outdir: { type: "string", default: "results" },
      depth: { type: "integer", default: 3 },
      skip_qc: { type: "boolean", default: false },
      custom_config_base: { type: "string" },
    },
  },
  schema_source: "nextflow_schema.json",
  profiles: ["docker", "test"],
};
const TEMPLATE = {
  workflow: { location: "/g/demo-lab/pipelines/rnaseq", revision: null, engine: "nextflow" },
  profiles: ["test"],
  params: { input: "samplesheet.csv", outdir: "/g/out/a", depth: 3, skip_qc: true, custom_config_base: "/g/shared/configs", legacy: "x" },
  non_default: ["input", "outdir", "skip_qc", "custom_config_base", "legacy"],
  code_loading: [
    { field: "workflow.location", value: "/g/demo-lab/pipelines/rnaseq", writable_by_others: false },
    { field: "params.custom_config_base", value: "/g/shared/configs", writable_by_others: true },
  ],
};

function copy(over: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}:launch-template`]: { ...TEMPLATE, ...over },
    [URL_]: { ...DETAIL, ...run({ state: "failed", name: "wgs-cohort-12" }) },
    "/api/v1/workflows:inspect": INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
  });
}

test("the form opens prefilled, with the banner naming exactly the values that differ", async () => {
  const mock = copy();
  app(`/launch?from=${ID}`);
  expect(
    await screen.findByText(
      "Prefilled from wgs-cohort-12 (7T9V1W): 5 values differ from the pipeline's defaults: input, outdir, skip_qc, custom_config_base, legacy.",
    ),
  ).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${URL_}:launch-template`);
  expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("/g/demo-lab/pipelines/rnaseq");
  expect(screen.getByRole("combobox", { name: /^Profile/ })).toHaveValue("test");
  expect(screen.getByRole("textbox", { name: "input (required)" })).toHaveValue("samplesheet.csv");
  expect(screen.getByRole("textbox", { name: "depth (optional)" })).toHaveValue("3");
  expect(screen.getByRole("checkbox", { name: "skip_qc (optional)" })).toBeChecked();
  // a key the form does not have is named, not sent silently
  expect(screen.getByText("Not in this pipeline's form, and not sent: legacy.")).toBeInTheDocument();
});

test("outdir warns while it is the run's own; a value that loads code says so, and writable by others", async () => {
  copy();
  app(`/launch?from=${ID}`);
  const outdir = await screen.findByRole("textbox", { name: "outdir (optional)" });
  const warning = "Warning: same as wgs-cohort-12. Change it to keep the two runs' results apart.";
  expect(screen.getByText(warning)).toBeInTheDocument();
  expect(screen.getByText("custom_config_base: loads code or configuration · writable by others")).toBeInTheDocument();
  expect(screen.getByText("Pipeline: loads code or configuration")).toBeInTheDocument();
  await userEvent.clear(outdir);
  await userEvent.type(outdir, "/g/out/b");
  expect(screen.queryByText(warning)).toBeNull();
});

test("Clear and start empty drops the prefill", async () => {
  copy();
  const router = app(`/launch?from=${ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Clear and start empty" }));
  await waitFor(() => expect(router.state.location.search).toEqual({}));
  await waitFor(() => expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue(""));
  expect(screen.queryByText(/Prefilled from/)).toBeNull();
});

test("a template that cannot be read says so, and the form stays empty", async () => {
  serve({
    [`${URL_}:launch-template`]: () => json(404, { title: "Not found", detail: "no such run" }),
    [URL_]: () => json(404, { title: "Not found", detail: "no such run" }),
    "/api/v1/runs?": { items: [], next: null },
  });
  app(`/launch?from=${ID}`);
  expect(await screen.findByRole("alert")).toHaveTextContent("Not prefilled: no such run");
  expect(screen.getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("");
});

test("a from that is not a run ID is ignored", async () => {
  const mock = copy();
  app("/launch?from=..%2Fx");
  await screen.findByRole("heading", { level: 1, name: "Launch a workflow" });
  expect(fetched(mock).some((u) => u.includes("launch-template"))).toBe(false);
});
