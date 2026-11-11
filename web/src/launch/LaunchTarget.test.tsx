// Launch, "What to run" (ui-spec §4.15; api §5.10; #161): one Nextflow module or one Snakemake rule,
// offered only when the server says `features.single_target`.
import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { ServerVersion } from "../api";
import { ServerContext } from "../server";
import { LayoutContext } from "../shell/layout";
import { LaunchPage } from "./LaunchPage";

const SERVER: ServerVersion = {
  version: "0.0.2",
  node: "login1",
  runs_root: "/scratch/runs",
  account: "amartin",
  executor: "local",
  features: { single_target: true },
};

const FASTQC = {
  kind: "module",
  source: "registry",
  name: "nf-core/fastqc",
  version: "0.0.0-6d1763b",
  description: "Run FastQC on sequenced reads",
  inputs: [
    { name: "meta", type: "map", description: "Groovy Map containing sample information" },
    { name: "reads", type: "file", description: "List of input FastQ files" },
  ],
};

const SMK = {
  location: "/data/synth",
  revision: null,
  engine: "snakemake",
  engine_files: ["Snakefile"],
  name: "synth",
  version: null,
  engine_version: "9.27.1",
  engine_versions: { snakemake: "9.27.1" },
  schema: null,
  schema_source: "none",
  profiles: [],
  params_file: null,
};

function json(status: number, body: unknown): Response {
  const type = status >= 400 ? "application/problem+json" : "application/json";
  return new Response(JSON.stringify(body), { status, headers: { "content-type": type } });
}

const fetchMock = vi.fn<typeof fetch>();
beforeEach(() =>
  vi.stubGlobal("fetch", (url: RequestInfo | URL, init?: RequestInit) =>
    ["/api/v1/environments", "/api/v1/catalog"].includes(String(url)) ? Promise.resolve(json(500, { title: "x" })) : fetchMock(url, init),
  ),
);
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function page(server: ServerVersion = SERVER, onLaunched = vi.fn()) {
  render(
    <MantineProvider>
      <ServerContext.Provider value={server}>
        <LayoutContext.Provider value={{ phone: false, titleRow: null }}>
          <LaunchPage onLaunched={onLaunched} />
        </LayoutContext.Provider>
      </ServerContext.Provider>
    </MantineProvider>,
  );
  return onLaunched;
}

const bodies = () => fetchMock.mock.calls.map(([url, init]) => [String(url), init?.body ? JSON.parse(String(init.body)) : null] as const);
const launch = (name = "Launch") => screen.getAllByRole("button", { name }).at(-1)!;
const singleMode = () => userEvent.click(screen.getByRole("radio", { name: "One step" }));
const ruleKind = () => userEvent.click(screen.getByRole("radio", { name: "Snakemake rule" }));
const title = () => screen.getByRole("heading", { level: 1 });

test("the What to run cards show only when the server has single targets on", () => {
  page({ ...SERVER, features: { single_target: false } });
  expect(screen.queryByRole("radiogroup", { name: "What to run" })).toBeNull();
  expect(title()).toHaveTextContent("Launch a workflow");
});

test("the mode cards are radios, and the title follows the mode and the kind of step", async () => {
  page();
  const modes = screen.getByRole("radiogroup", { name: "What to run" });
  expect(within(modes).getByRole("radio", { name: "Whole pipeline" })).toBeChecked();
  expect(title()).toHaveTextContent("Launch a workflow");
  expect(screen.queryByRole("radiogroup", { name: "Kind of step" })).toBeNull();
  await singleMode();
  expect(within(modes).getByRole("radio", { name: "One step" })).toBeChecked();
  expect(title()).toHaveTextContent("Launch one module");
  expect(screen.getByText("Run a single Nextflow module, outside any pipeline.")).toBeInTheDocument();
  await ruleKind();
  expect(title()).toHaveTextContent("Launch one rule");
  expect(screen.getByText("Run one Snakemake rule and only the jobs it needs.")).toBeInTheDocument();
  await userEvent.click(within(modes).getByRole("radio", { name: "Whole pipeline" }));
  expect(title()).toHaveTextContent("Launch a workflow");
});

test("one step: the kind of step replaces the engine picker, the catalog and the test pipelines", async () => {
  page();
  expect(screen.getByRole("group", { name: "Engine" })).toBeInTheDocument();
  expect(await screen.findByText("The catalog could not be read.")).toBeInTheDocument();
  await singleMode();
  const kind = screen.getByRole("radiogroup", { name: "Kind of step" });
  expect(within(kind).getByRole("radio", { name: "Nextflow module" })).toBeChecked();
  expect(screen.queryByRole("group", { name: "Engine" })).toBeNull();
  expect(screen.queryByText("The catalog could not be read.")).toBeNull();
  expect(screen.queryByRole("combobox", { name: /^Profile/ })).toBeNull();
  expect(screen.getByRole("textbox", { name: /^Run name/ })).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: /^Module/ })).toHaveAccessibleDescription(
    "A registry module such as nf-core/fastqc, or the absolute path of a module directory.",
  );
  // a Try chip fills the field
  await userEvent.click(screen.getByRole("button", { name: "Try nf-core/multiqc" }));
  expect(screen.getByRole("textbox", { name: /^Module/ })).toHaveValue("nf-core/multiqc");
  expect(launch("Launch module")).toBeInTheDocument();
  await ruleKind();
  expect(screen.getByRole("textbox", { name: /^Snakemake pipeline/ })).toBeInTheDocument();
  expect(screen.queryByRole("group", { name: "Engine" })).toBeNull();
  expect(screen.getByRole("combobox", { name: /^Profile/ })).toBeInTheDocument();
});

test("a registry module: Load pins the registry's version, its inputs are the parameters, Launch sends the target", async () => {
  fetchMock.mockImplementation(async (url) => {
    if (String(url) === "/api/v1/targets:inspect") return json(200, FASTQC);
    if (String(url) === "/api/v1/runs") return json(201, { id: "run_m", state: "queued" });
    return json(404, {});
  });
  const onLaunched = page();
  await singleMode();
  await userEvent.type(screen.getByRole("textbox", { name: /^Module/ }), "nf-core/fastqc");
  expect(screen.queryByRole("textbox", { name: /^Revision/ })).toBeNull();
  const version = screen.getByRole("textbox", { name: /^Version/ });
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  expect(await screen.findByText("Pinned to 0.0.0-6d1763b, the registry's current version")).toBeInTheDocument();
  expect(version).toHaveValue("0.0.0-6d1763b");
  expect(bodies()[0]).toEqual(["/api/v1/targets:inspect", { engine: "nextflow", location: "nf-core/fastqc", version: null }]);
  expect(screen.getByText("Run FastQC on sequenced reads")).toBeInTheDocument();
  expect(screen.getByText("from the registry")).toBeInTheDocument();
  expect(screen.getByText("checksum: after install")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Module inputs/ })).toBeInTheDocument();
  // a module run takes no extra config file (api §5.10): no row, no Summary line
  expect(screen.queryByText("Extra config file")).toBeNull();
  expect(screen.queryByText("Extra config")).toBeNull();
  expect(screen.getByText("2 required")).toBeInTheDocument();
  expect(screen.getByText("Runs module nf-core/fastqc 0.0.0-6d1763b, from the registry")).toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox", { name: /^reads/ }), "/data/a.fq.gz");
  await userEvent.type(screen.getByRole("textbox", { name: /^meta/ }), '{{"id": "a"}');
  await userEvent.click(launch("Launch module"));
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_m"));
  const [, sent] = bodies().find(([url]) => url === "/api/v1/runs")!;
  expect(sent).toMatchObject({
    workflow: { location: "nf-core/fastqc", revision: null, engine: "nextflow" },
    params: { meta: { id: "a" }, reads: "/data/a.fq.gz" },
    target: { kind: "module", version: "0.0.0-6d1763b" },
  });
});

test("a module view that fails is a line under Load, and the engine's first line is said", async () => {
  fetchMock.mockResolvedValue(json(502, { type: "/problems/engine-failed", title: "The engine failed", detail: "nextflow module view: Module not found" }));
  page();
  await singleMode();
  await userEvent.type(screen.getByRole("textbox", { name: /^Module/ }), "nf-core/nope");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  expect(await screen.findByText("Not loaded: nextflow module view: Module not found")).toBeInTheDocument();
});

test("a Snakemake rule: Load lists the rules, choosing one previews the jobs, Launch sends the rule", async () => {
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url);
    if (u.startsWith("/api/v1/workflows:inspect")) return json(200, SMK);
    if (u === "/api/v1/targets:inspect") {
      const body = JSON.parse(String(init!.body));
      return json(200, {
        kind: "rule",
        rules: ["all", "make_reads", "qc_stats", "qc_report"],
        plan: body.rule ? { jobs: { make_reads: 12, qc_stats: 12, qc_report: 1 }, total: 25 } : null,
      });
    }
    if (u === "/api/v1/runs") return json(201, { id: "run_r", state: "queued" });
    return json(404, {});
  });
  const onLaunched = page();
  await singleMode();
  await ruleKind();
  await userEvent.type(screen.getByRole("textbox", { name: /^Snakemake pipeline/ }), "/data/synth");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  const rules = await screen.findByRole("radiogroup", { name: "Rule" });
  expect(within(rules).getAllByRole("radio").map((b) => b.getAttribute("aria-checked"))).toEqual(["false", "false", "false", "false"]);
  // Before Launch asks for the rule, and its link focuses the first rule
  const choose = screen.getByRole("link", { name: "Choose a rule" });
  await userEvent.click(choose);
  expect(within(rules).getByRole("radio", { name: /^all/ })).toHaveFocus();
  expect(launch("Launch rule")).toBeInTheDocument();
  await userEvent.click(within(rules).getByRole("radio", { name: /^qc_report/ }));
  const plan = await screen.findByRole("status", { name: /What will run/ });
  expect(plan).toHaveTextContent("dry run, 25 jobs");
  expect(within(plan).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "make_reads12 jobs",
    "qc_stats12 jobs",
    "qc_report1 job · target",
  ]);
  expect(plan).toHaveTextContent("Not run: all");
  expect(within(rules).getByRole("radio", { name: "qc_report target" })).toHaveAttribute("aria-checked", "true");
  expect(within(rules).getByRole("radio", { name: "make_reads needed" })).toHaveAttribute("aria-checked", "false");
  expect(within(rules).getByRole("radio", { name: "qc_stats needed" })).toHaveAttribute("data-needed");
  expect(within(rules).getByRole("radio", { name: "all" })).not.toHaveAttribute("data-needed");
  expect(screen.getByText("Runs rule qc_report and the jobs it needs")).toBeInTheDocument();
  expect(screen.getByText("snakemake … qc_report")).toBeInTheDocument();
  await userEvent.click(launch("Launch qc_report"));
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_r"));
  const [, sent] = bodies().find(([url]) => url === "/api/v1/runs")!;
  expect(sent).toMatchObject({ workflow: { location: "/data/synth", engine: "snakemake" }, target: { kind: "rule", name: "qc_report" } });
});

test("a dry run that fails says why, and Launch stays allowed", async () => {
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url);
    if (u.startsWith("/api/v1/workflows:inspect")) return json(200, SMK);
    if (u === "/api/v1/targets:inspect") {
      const body = JSON.parse(String(init!.body));
      return json(200, { kind: "rule", rules: ["qc_report"], plan: null, ...(body.rule ? { error: "MissingInputException" } : {}) });
    }
    return json(404, {});
  });
  page();
  await singleMode();
  await ruleKind();
  await userEvent.type(screen.getByRole("textbox", { name: /^Snakemake pipeline/ }), "/data/synth");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await userEvent.click(await screen.findByRole("radio", { name: /^qc_report/ }));
  expect(await screen.findByText("The dry run failed: MissingInputException")).toBeInTheDocument();
  expect(screen.getByText("Nothing is missing.")).toBeInTheDocument();
});
