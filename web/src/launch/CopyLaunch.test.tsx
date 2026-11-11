// Copy to a new launch (P1 Task 32 part two; ui-spec §4.4 run tools note; board LiteLaunch):
// /launch?from=<run> prefills the form from `GET /runs/{id}:launch-template`.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, VERSION, app, fetched, json, run, serve, stubStream } from "../testing";

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
  // and in Before Launch, as a warning that does not block (FU-P3-86h), linking outdir
  const before = screen.getByRole("status", { name: "Before Launch" });
  const link = within(before).getByRole("link", { name: "Warning, not a blocker: outdir is the same as wgs-cohort-12" });
  expect(before).toHaveTextContent(/^Nothing is missing\./);
  await userEvent.click(link);
  expect(outdir).toHaveFocus();
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

test("FU-P3-110d: the run's resources and extra config file are prefilled, the file a code_loading item read again at Launch", async () => {
  const path = "/home/amartin/configs/lab-tweaks.config";
  const posted: Record<string, unknown>[] = [];
  serve({
    [`${URL_}:launch-template`]: {
      ...TEMPLATE,
      default_resources: { cpus: 4, mem_mib: 16384, time_min: 90 },
      config_file: path,
      code_loading: [...TEMPLATE.code_loading, { field: "config_file", value: path, writable_by_others: false }],
    },
    [URL_]: { ...DETAIL, ...run({ state: "failed", name: "wgs-cohort-12" }) },
    "/api/v1/workflows:inspect": INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
    "/api/v1/runs": (_url: URL, init?: RequestInit) => (posted.push(JSON.parse(String(init?.body))), json(201, { id: "run_2", name: "x", state: "queued" })),
  });
  app(`/launch?from=${ID}`);
  const item = await screen.findByText("Extra config file: loads code or configuration");
  expect(item.closest("li")).toHaveTextContent(path);
  const where = screen.getByRole("region", { name: "Where it runs" });
  expect(within(where).getByRole("button", { name: /^Resources/ })).toHaveTextContent("Defaults: 4 CPUs · 16 GiB · 1 h 30 min per task");
  expect(within(where).getByRole("button", { name: /^Extra config file/ })).toHaveTextContent("lab-tweaks.config");
  await userEvent.click(within(where).getByRole("button", { name: /^Resources/ }));
  expect(screen.getByRole("textbox", { name: "CPUs per task" })).toHaveValue("4");
  expect(screen.getByRole("textbox", { name: "Memory per task" })).toHaveValue("16");
  expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveValue("1");
  expect(screen.getByRole("textbox", { name: "Time per task, minutes" })).toHaveValue("30");
  await userEvent.click(screen.getAllByRole("button", { name: "Launch" }).at(-1)!);
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({ default_resources: { cpus: 4, mem_mib: 16384, time_min: 90 }, config_file: path });
});

test("a copy of a Snakemake file-target run opens as a Snakemake step, not a Nextflow module (SEC-161W-04)", async () => {
  const mock = serve({
    "/api/v1/version": { ...VERSION, features: { single_target: true } },
    [`${URL_}:launch-template`]: {
      ...TEMPLATE,
      workflow: { location: "/g/demo-lab/pipelines/synth-qc", revision: null, engine: "snakemake" },
      profiles: [],
      params: {},
      non_default: [],
      code_loading: [],
      target: { kind: "file", name: "results/x.txt" },
    },
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "synth" }) },
    "/api/v1/workflows:inspect": { ...INSPECTED, location: "/g/demo-lab/pipelines/synth-qc", engine: "snakemake", engine_files: ["Snakefile"], schema: null, schema_source: "none", profiles: [] },
    "/api/v1/targets:inspect": { kind: "rule", rules: ["all", "qc_report"], plan: null },
    "/api/v1/runs?": { items: [], next: null },
  });
  app(`/launch?from=${ID}`);
  await waitFor(() => expect(fetched(mock)).toContain("/api/v1/targets:inspect"));
  const inspect = mock.mock.calls.find(([u]) => String(u).endsWith("/targets:inspect"));
  expect(JSON.parse(String(inspect?.[1]?.body))).toMatchObject({ engine: "snakemake" });
});
