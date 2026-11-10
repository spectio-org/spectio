// Launch, "What to run" (ui-spec §4.15; api §5.9; #161): one Nextflow module or one Snakemake rule,
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
const launch = () => screen.getAllByRole("button", { name: "Launch" }).at(-1)!;
const singleMode = () => userEvent.click(screen.getByRole("radio", { name: "Single module / rule" }));

test("the What to run fieldset shows only when the server has single targets on", () => {
  page({ ...SERVER, features: { single_target: false } });
  expect(screen.queryByRole("group", { name: "What to run" })).toBeNull();
});

test("a registry module: Load pins the registry's version, its inputs are the parameters, Launch sends the target", async () => {
  fetchMock.mockImplementation(async (url) => {
    if (String(url) === "/api/v1/targets:inspect") return json(200, FASTQC);
    if (String(url) === "/api/v1/runs") return json(201, { id: "run_m", state: "queued" });
    return json(404, {});
  });
  const onLaunched = page();
  const group = screen.getByRole("group", { name: "What to run" });
  expect(within(group).getByRole("radio", { name: "Whole pipeline" })).toBeChecked();
  await singleMode();
  await userEvent.type(screen.getByRole("textbox", { name: /^Module or pipeline/ }), "nf-core/fastqc");
  expect(screen.queryByRole("textbox", { name: /^Revision/ })).toBeNull();
  const version = screen.getByRole("textbox", { name: /^Version/ });
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  expect(await screen.findByText("Pinned to 0.0.0-6d1763b, the registry's current version")).toBeInTheDocument();
  expect(version).toHaveValue("0.0.0-6d1763b");
  expect(bodies()[0]).toEqual(["/api/v1/targets:inspect", { engine: "nextflow", location: "nf-core/fastqc", version: null }]);
  expect(screen.getByText("Run FastQC on sequenced reads")).toBeInTheDocument();
  expect(screen.getByText("Runs module nf-core/fastqc 0.0.0-6d1763b, from the registry")).toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox", { name: /^reads/ }), "/data/a.fq.gz");
  await userEvent.type(screen.getByRole("textbox", { name: /^meta/ }), '{{"id": "a"}');
  await userEvent.click(launch());
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
  await userEvent.type(screen.getByRole("textbox", { name: /^Module or pipeline/ }), "nf-core/nope");
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
  await userEvent.type(screen.getByRole("textbox", { name: /^Module or pipeline/ }), "/data/synth");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  const rule = await screen.findByRole("combobox", { name: /^Rule/ });
  expect((rule as HTMLSelectElement).options[0].text).toBe("Choose a rule");
  // Before Launch asks for the rule
  expect(screen.getByRole("link", { name: "Choose a rule" })).toBeInTheDocument();
  await userEvent.selectOptions(rule, "qc_report");
  const plan = await screen.findByText("Will run: make_reads 12, qc_stats 12, qc_report 1 (25 jobs)");
  expect(plan.closest("[role=status]")).not.toBeNull();
  expect(screen.getByText("Runs rule qc_report and the jobs it needs")).toBeInTheDocument();
  expect(screen.getByText("snakemake … qc_report")).toBeInTheDocument();
  await userEvent.click(launch());
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
  await userEvent.type(screen.getByRole("textbox", { name: /^Module or pipeline/ }), "/data/synth");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await userEvent.selectOptions(await screen.findByRole("combobox", { name: /^Rule/ }), "qc_report");
  expect(await screen.findByText("The dry run failed: MissingInputException")).toBeInTheDocument();
  expect(screen.getByText("Nothing is missing.")).toBeInTheDocument();
});
