// The Profile row of Launch (#408; ui-spec §4.8.1 "At Launch"; boards LiteLaunch, MLiteLaunch): its
// states, the preselection (the catalog entry's default profile, else the server's), the lines that
// follow the choice, the engine's profile prefill, and Copy's profile.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, VERSION, app, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const PROFILES = "/api/v1/execution-profiles";
const COMPUTES = "/api/v1/computes";
const SLURM = { ...VERSION, executor: "slurm" };
const INSPECTED = {
  location: "/data/rnaseq",
  revision: null,
  engine: "nextflow",
  engine_files: ["main.nf"],
  main_scripts: ["main.nf"],
  name: "rnaseq",
  version: "3.27.0",
  engine_version: "26.10.4",
  engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" },
  schema: { type: "object", properties: { depth: { type: "integer", default: 3 } } },
  schema_source: "nextflow_schema.json",
  profiles: ["docker", "slurm"],
};
const FILE = (state = "ok") => ({ path: "/home/amartin/.spectio/x.toml", state, detail: null });
const compute = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, executor: "slurm", slurm: { account: "mylab" }, local: null, software: ["conda", "apptainer"], apptainer_args: "" },
  ...{ builtin: false, usable: true, unusable_reason: null, etag: `"c-${name}"` },
  ...over,
});
const COMPUTE_LIST = {
  items: [
    compute("slurm", { label: "SLURM (from spectio init)", builtin: true, slurm: { account: null } }),
    compute("local", { label: "Login node", executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 }, builtin: true }),
    compute("broken", { usable: false, unusable_reason: "sbatch not found" }),
  ],
  file: FILE(),
};
const NOTHING = { partition: null, constraint: null, gres: null, time_min: null, mem_mib: null, cpus: null };
const profile = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, compute: "slurm", resources: NOTHING, software: ["conda", "apptainer"] },
  ...{ engine_profiles: { nextflow: null, snakemake: null }, builtin: false, etag: `"${name}"` },
  ...over,
});
const SLURM_P = profile("slurm", { label: "SLURM (from spectio init)", builtin: true });
const LOCAL_P = profile("local", { label: "Login node", compute: "local", builtin: true });
const GPU = profile("gpu-h100", { label: "One H100", resources: { ...NOTHING, partition: "gpu-el10", gres: "gpu:H100:1", time_min: 240 } });
const list = (items: unknown[], fallback: string | undefined = "slurm") => ({ items, ...(fallback ? { default: fallback } : {}), file: FILE() });
const entry = (over: Record<string, unknown> = {}) => ({
  ...{ name: "rnaseq", label: null, engine: "nextflow", location: "/data/rnaseq", revision: null, profile: null, params_file: null },
  ...{ profiles: ["gpu-h100", "local"], default_profile: "gpu-h100", etag: '"rnaseq"' },
  ...over,
});

/** Launch on a SLURM server with these profiles; returns the POST /runs bodies. */
function launchWith(profiles: unknown, more: Record<string, unknown> = {}) {
  const posted: unknown[] = [];
  serve({
    "/api/v1/version": SLURM,
    [PROFILES]: profiles,
    [COMPUTES]: COMPUTE_LIST,
    "/api/v1/workflows:inspect": { ...INSPECTED, engine_files: ["main.nf", "Snakefile"] },
    "/api/v1/runs?": { items: [], next: null },
    "/api/v1/runs": (_url: URL, init?: RequestInit) => (posted.push(JSON.parse(String(init?.body))), json(201, { id: "run_1", name: "x", state: "queued" })),
    ...more,
  });
  app("/launch");
  return posted;
}
async function load() {
  await userEvent.type(await screen.findByRole("textbox", { name: /^Pipeline/ }), "/data/rnaseq");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText(/form from nextflow_schema.json/);
  await userEvent.click(screen.getByRole("button", { name: "Nextflow" })); // main.nf and a Snakefile: no guess
}
const where = () => screen.getByRole("region", { name: "Where it runs" });
const tasksRow = () => within(where()).getByText("Tasks").nextElementSibling!;
const launchButton = () => screen.getAllByRole("button", { name: "Launch" }).at(-1)!;
const profileSelect = () => screen.findByRole("combobox", { name: "Profile" });

test("a Profile select of the profiles on a usable compute; the server's default is chosen, its compute and resources are said; Launch sends it", async () => {
  const posted = launchWith(list([SLURM_P, LOCAL_P, GPU, profile("on-broken", { compute: "broken" })]));
  const select = await profileSelect();
  expect([...select.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["SLURM (from spectio init) · slurm", "Login node · local", "One H100 · slurm"]);
  expect(select).toHaveValue("slurm");
  expect(select).toHaveAccessibleDescription("Compute slurm, SLURM · SLURM's defaults for your account · deploys with conda and apptainer");
  await load();
  expect(tasksRow()).toHaveTextContent("sent to SLURM by Nextflow");
  await userEvent.selectOptions(select, "gpu-h100");
  expect(select).toHaveAccessibleDescription(/Compute slurm, SLURM · partition gpu-el10 · GRES gpu:H100:1 · 4 h per job/);
  expect(tasksRow()).toHaveTextContent("sent to SLURM by Nextflow · partition gpu-el10 · GRES gpu:H100:1");
  // the summary names the profile, its compute and its resources
  const summary = within(screen.getByRole("region", { name: "Summary" }));
  expect(summary.getByText("Profile").nextElementSibling).toHaveTextContent("One H100 · compute slurm (SLURM) · partition gpu-el10 · GRES gpu:H100:1 · 4 h per job");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({ execution_profile: "gpu-h100" });
  expect(posted[0]).not.toHaveProperty("environment");
});

test("a local profile: the Tasks row says where it runs", async () => {
  launchWith(list([SLURM_P, LOCAL_P]));
  await userEvent.selectOptions(await profileSelect(), "local");
  await load();
  expect(tasksRow()).toHaveTextContent("run on login1 by Nextflow · at most 2 CPUs");
});

test("without a default in the list, the profile named like the server's executor is chosen", async () => {
  launchWith(list([LOCAL_P, SLURM_P], undefined));
  expect(await profileSelect()).toHaveValue("slurm");
});

test("the catalog entry's profiles are the only ones offered, and its default is preselected once the pipeline is loaded from it", async () => {
  const posted = launchWith(list([SLURM_P, LOCAL_P, GPU]), { "/api/v1/catalog": { items: [entry()], file: FILE() } });
  await userEvent.selectOptions(await screen.findByRole("combobox", { name: "From your catalog" }), "rnaseq");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText("Loaded");
  const select = await profileSelect();
  expect([...select.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["Login node · local", "One H100 · slurm"]);
  expect(select).toHaveValue("gpu-h100");
  expect(screen.getByText("The profiles of the catalog entry rnaseq")).toBeInTheDocument();
  await userEvent.selectOptions(select, "local");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({ execution_profile: "local" });
});

test("a list with nothing usable: a line with a link to Profiles, and the summary says Not chosen yet", async () => {
  launchWith(list([profile("on-broken", { compute: "broken" })]));
  const line = await screen.findByText(/No profile can be used yet/);
  expect(within(line).getByRole("link", { name: "See Profiles" })).toHaveAttribute("href", "/profiles");
  await load();
  expect(within(screen.getByRole("region", { name: "Summary" })).getByText("Profile").nextElementSibling).toHaveTextContent("Not chosen yet");
  expect(screen.getByRole("link", { name: "Choose where it runs" })).toBeInTheDocument();
});

test("the lists cannot be read: Retry, and Launch sends no profile", async () => {
  const posted = launchWith(() => json(500, { title: "boom", detail: "boom" }));
  expect(await screen.findByText("Profiles could not be read")).toBeInTheDocument();
  expect(screen.getByText("The server's default profile will be used")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  await load();
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).not.toHaveProperty("execution_profile");
  expect(posted[0]).not.toHaveProperty("environment");
});

test("the profiles are loading: a status line and a skeleton", async () => {
  launchWith(() => new Promise<Response>(() => {}));
  expect(await screen.findByText("Loading profiles…")).toBeInTheDocument();
});

test("a 422 on execution_profile lands on the Profile select", async () => {
  launchWith(list([SLURM_P, LOCAL_P]), {
    "/api/v1/runs": () => json(422, { title: "Invalid", detail: "Invalid", errors: [{ field: "execution_profile", message: "slurm is not usable" }] }),
  });
  await profileSelect();
  await load();
  await userEvent.click(launchButton());
  await waitFor(() => expect(screen.getByRole("combobox", { name: "Profile" })).toHaveAccessibleDescription(/slurm is not usable/));
});

test("the execution profile's engine profile is preselected when the pipeline has it, until the engine's profile is changed", async () => {
  const mine = profile("mylab", { engine_profiles: { nextflow: "docker", snakemake: "slurm" } });
  const embl = profile("embl-p", { engine_profiles: { nextflow: "embl", snakemake: null } });
  launchWith(list([SLURM_P, LOCAL_P, mine, embl]));
  await load();
  const engineProfile = screen.getByRole("combobox", { name: /^Nextflow profile/ });
  expect(engineProfile).toHaveValue("");
  const choose = async (name: string) => userEvent.selectOptions(await profileSelect(), name);
  await choose("mylab");
  expect(engineProfile).toHaveValue("docker");
  await choose("embl-p");
  expect(engineProfile).toHaveValue("");
  expect(screen.getByText("The execution profile's default embl is not in this pipeline: none selected")).toBeInTheDocument();
  // Snakemake with a profile: the engine's profile owns the SLURM resources
  await userEvent.click(screen.getByRole("button", { name: "Snakemake" }));
  await choose("mylab");
  const snakemakeProfile = screen.getByRole("combobox", { name: /^Snakemake profile/ });
  expect(snakemakeProfile).toHaveValue("slurm");
  expect(tasksRow()).toHaveTextContent("sent to SLURM by Snakemake · resources and partition from the profile slurm (this profile's are not passed)");
  await userEvent.selectOptions(snakemakeProfile, "docker");
  await choose("embl-p");
  expect(snakemakeProfile).toHaveValue("docker"); // changed by the user: kept
});

test("Copy to a new launch preselects the run's profile, and the banner says when it is gone", async () => {
  const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
  const template = {
    workflow: { location: "/data/rnaseq", revision: null, engine: "nextflow" },
    ...{ profiles: [], params: {}, non_default: [], code_loading: [] },
    environment: "local",
    environment_notice: null,
  };
  serve({
    "/api/v1/version": SLURM,
    [PROFILES]: list([SLURM_P, LOCAL_P]),
    [COMPUTES]: COMPUTE_LIST,
    [`/api/v1/runs/${ID}:launch-template`]: template,
    [`/api/v1/runs/${ID}`]: { ...DETAIL, ...run({ state: "failed", name: "wgs" }) },
    "/api/v1/workflows:inspect": INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
  });
  app(`/launch?from=${ID}`);
  await waitFor(() => expect(screen.getByRole("combobox", { name: "Profile" })).toHaveValue("local"));
});
