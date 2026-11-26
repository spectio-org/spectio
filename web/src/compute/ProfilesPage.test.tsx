// The Profiles pages (#408; ui-spec §4.8.1): the list with each profile's compute and resources,
// and the form with its compute, resources, software and engine profiles.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, json, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/execution-profiles";
const COMPUTES = "/api/v1/computes";
const SLURM = { ...VERSION, executor: "slurm" };
const FILE = { path: "/home/amartin/.spectio/execution-profiles.toml", state: "ok", detail: null };
const compute = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, executor: "slurm", slurm: { account: "lab-a" }, local: null, software: ["conda", "apptainer"], apptainer_args: "" },
  ...{ builtin: false, usable: true, unusable_reason: null, etag: `"c-${name}"` },
  ...over,
});
const CLUSTERS = {
  items: [
    compute("slurm", { label: "SLURM (from spectio init)", builtin: true }),
    compute("local", { label: "Login node", executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 }, builtin: true }),
    compute("embl-slurm", { label: "EMBL cluster", software: ["apptainer"] }),
    compute("broken", { usable: false, unusable_reason: "sbatch not found" }),
  ],
  file: { ...FILE, path: "/home/amartin/.spectio/computes.toml" },
};
const profile = (name: string, over: Record<string, unknown> = {}) => ({
  name,
  label: null,
  compute: "embl-slurm",
  resources: { partition: "gpu-el10", constraint: null, gres: "gpu:H100:1", time_min: 240, mem_mib: 65536, cpus: 8 },
  software: ["apptainer"],
  engine_profiles: { nextflow: null, snakemake: null },
  builtin: false,
  etag: `"${name}-1"`,
  ...over,
});
const NO_RESOURCES = { partition: null, constraint: null, gres: null, time_min: null, mem_mib: null, cpus: null };
const BUILTINS = [
  profile("slurm", { label: "SLURM (from spectio init)", compute: "slurm", resources: NO_RESOURCES, software: ["conda", "apptainer"], builtin: true }),
  profile("local", { label: "Login node", compute: "local", resources: NO_RESOURCES, software: ["conda", "apptainer"], builtin: true }),
];
const list = (items: unknown[], state = "ok") => ({ items, default: "slurm", file: { ...FILE, state } });
const MINE = [profile("gpu-h100", { label: "One H100 per job", engine_profiles: { nextflow: "singularity", snakemake: "slurm-prof" } }), profile("on-broken", { compute: "broken" })];

test("the list: each profile with its compute, its resources in words and its engine profiles", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), [COMPUTES]: CLUSTERS, "/api/v1/version": SLURM });
  app("/profiles");
  const card = (await screen.findByRole("heading", { name: "One H100 per job" })).closest("article")!;
  expect(card).toHaveTextContent("gpu-h100");
  expect(within(card).getByText("EMBL cluster")).toHaveClass("sp-chip");
  expect(card).toHaveTextContent("partition gpu-el10 · SLURM account lab-a · GRES gpu:H100:1 · 4 h per job · 64 GiB per job · 8 CPUs per job · deploys with apptainer");
  expect(card).toHaveTextContent("Profiles: Nextflow singularity · Snakemake slurm-prof");
  expect(within(card).getByRole("link", { name: "Edit gpu-h100" })).toHaveAttribute("href", "/profiles/gpu-h100");
  const builtin = screen.getByRole("heading", { name: "SLURM (from spectio init)" }).closest("article")!;
  expect(within(builtin).getByText("Built-in")).toBeInTheDocument();
  expect(within(builtin).queryByRole("link", { name: /^Edit/ })).toBeNull();
  expect(within(builtin).getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/profiles/new?from=slurm");
  expect(screen.getByRole("heading", { name: "on-broken" }).closest("article")).toHaveTextContent("Not usable: its compute broken is not usable: sbatch not found");
});

test("the table names the compute in its second column", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), [COMPUTES]: CLUSTERS, "/api/v1/version": SLURM });
  app("/profiles?view=table");
  const grid = await screen.findByRole("table", { name: "Profiles, built-ins first" });
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Profile", "Compute", "Settings", "State", "Actions"]);
  expect(within(within(grid).getByRole("rowheader", { name: /One H100 per job/ }).closest("tr")!).getByText("EMBL cluster")).toBeInTheDocument();
});

test("only the built-ins: the empty state says what New profile does", async () => {
  serve({ [API]: list(BUILTINS), [COMPUTES]: CLUSTERS, "/api/v1/version": SLURM });
  app("/profiles");
  expect(await screen.findByText(/Only the built-in profiles so far/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "New profile" })).toHaveAttribute("href", "/profiles/new");
});

test("Delete: a profile a catalog entry lists is refused by the server, and the dialog says so", async () => {
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-h100`]: () => json(409, { type: "/problems/profile-in-use", title: "In use", detail: "The catalog entry rnaseq lists this profile." }),
    [API]: list([...BUILTINS, ...MINE]),
    [COMPUTES]: CLUSTERS,
  });
  app("/profiles");
  await userEvent.click(await screen.findByRole("button", { name: "Delete gpu-h100" }));
  const dialog = await screen.findByRole("dialog", { name: "Delete gpu-h100?" });
  expect(dialog).toHaveTextContent("remove it from the entry first");
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete gpu-h100" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("The catalog entry rnaseq lists this profile.");
});

test("the form: the compute starts as the server's, its software is what the compute has; the body posts under resources", async () => {
  const bodies: Record<string, unknown>[] = [];
  serve({
    "/api/v1/version": SLURM,
    [COMPUTES]: CLUSTERS,
    [API]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list(bodies.length ? [...BUILTINS, profile("gpu-h100")] : BUILTINS));
      bodies.push(JSON.parse(String(init.body)));
      return json(201, profile("gpu-h100"));
    },
  });
  app("/profiles/new");
  const select = await screen.findByRole("combobox", { name: "Compute" });
  expect(select).toHaveValue("slurm");
  // a compute that is not usable is not offered
  expect(within(select).queryByRole("option", { name: /broken/ })).toBeNull();
  await userEvent.selectOptions(select, "embl-slurm");
  const software = screen.getByRole("group", { name: "Software" });
  expect(within(software).queryByRole("checkbox", { name: "Conda" })).toBeNull(); // the compute has Apptainer only
  expect(within(software).getByRole("checkbox", { name: "Apptainer" })).toBeChecked();
  await userEvent.type(screen.getByLabelText("Name"), "gpu-h100");
  await userEvent.type(screen.getByLabelText("Partition"), "gpu-el10");
  await userEvent.type(screen.getByLabelText("GRES"), "gpu:H100:1");
  await userEvent.type(screen.getByLabelText("Hours"), "4");
  await userEvent.type(screen.getByLabelText("Memory per job"), "64");
  await userEvent.type(screen.getByLabelText("CPUs per job"), "8");
  await userEvent.type(screen.getByLabelText("Nextflow profiles (-profile)"), "singularity");
  await userEvent.type(screen.getByLabelText("Snakemake profile"), "slurm-prof");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(bodies).toHaveLength(1));
  expect(bodies[0]).toEqual({
    ...{ name: "gpu-h100", label: null, compute: "embl-slurm", software: ["apptainer"] },
    resources: { partition: "gpu-el10", constraint: null, gres: "gpu:H100:1", time_min: 240, mem_mib: 65536, cpus: 8 },
    engine_profiles: { nextflow: "singularity", snakemake: "slurm-prof" },
  });
  expect((await screen.findByRole("heading", { name: "gpu-h100" })).closest("article")).toHaveTextContent("EMBL cluster");
});

test("the form: a 422 on a resource lands on its field; a missing name or compute says why Save waits", async () => {
  serve({
    "/api/v1/version": SLURM,
    [COMPUTES]: CLUSTERS,
    [API]: (_u: URL, init?: RequestInit) =>
      init?.method === "POST"
        ? json(422, { title: "x", detail: "Invalid", errors: [{ field: "resources.partition", message: "partition gpu is not on this compute" }] })
        : json(200, list(BUILTINS)),
  });
  app("/profiles/new");
  await userEvent.type(await screen.findByLabelText("Name"), "x");
  await userEvent.type(screen.getByLabelText("Partition"), "gpu");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByLabelText("Partition")).toHaveAccessibleDescription(/partition gpu is not on this compute/));
  await userEvent.type(screen.getByLabelText("Hours"), "0");
  await userEvent.type(screen.getByLabelText("Minutes"), "0");
  expect(screen.getByLabelText("Hours")).toHaveAccessibleDescription(/At least 1 minute/);
  expect(screen.getByRole("button", { name: "Save" })).toHaveAccessibleDescription("Fix Time per job first");
});

test("editing: the compute and the resources are read back; Save sends If-Match; after it, the list with focus", async () => {
  const sent: { body: Record<string, unknown>; etag: string | null }[] = [];
  serve({
    "/api/v1/version": SLURM,
    [COMPUTES]: CLUSTERS,
    [`${API}/gpu-h100`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "PUT") return json(200, MINE[0]);
      sent.push({ body: JSON.parse(String(init.body)), etag: new Headers(init.headers).get("if-match") });
      return json(200, MINE[0]);
    },
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/profiles/gpu-h100");
  expect(await screen.findByLabelText("Name")).toHaveAttribute("readonly");
  expect(screen.getByRole("combobox", { name: "Compute" })).toHaveValue("embl-slurm");
  expect(screen.getByLabelText("Partition")).toHaveValue("gpu-el10");
  expect(screen.getByLabelText("Hours")).toHaveValue("4");
  expect(screen.getByLabelText("Memory per job")).toHaveValue("64");
  expect(screen.getByText(/execution-profiles\.toml; comments in it are not kept/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "One H100 per job" })).toHaveFocus());
  expect(sent[0]!.etag).toBe('"gpu-h100-1"');
  expect(sent[0]!.body).toMatchObject({ compute: "embl-slurm", resources: { partition: "gpu-el10", time_min: 240 } });
  expect(screen.getByText("Saved gpu-h100")).toHaveAttribute("role", "status");
});

test("a built-in opens read only, with Duplicate to edit; its duplicate is named <name>-copy with the built-in's label cleared", async () => {
  serve({ "/api/v1/version": SLURM, [COMPUTES]: CLUSTERS, [`${API}/slurm`]: BUILTINS[0], [API]: list(BUILTINS) });
  app("/profiles/slurm");
  expect(await screen.findByLabelText("Partition")).toHaveAttribute("readonly");
  expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  expect(screen.getByRole("combobox", { name: "Compute" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/profiles/new?from=slurm");
  app("/profiles/new?from=slurm");
  await waitFor(() => expect(screen.getAllByLabelText("Name").some((el) => (el as HTMLInputElement).value === "slurm-copy")).toBe(true));
});

test("the computes cannot be read: the form says so with Retry", async () => {
  let fail = true;
  serve({ "/api/v1/version": SLURM, [COMPUTES]: () => (fail ? json(500, { title: "x", detail: "boom" }) : json(200, CLUSTERS)), [API]: list(BUILTINS) });
  app("/profiles/new");
  expect(await screen.findByRole("alert")).toHaveTextContent("Computes could not be read. boom");
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByLabelText("Name")).toBeInTheDocument();
});

test("phone: the page stacks Duplicate and Delete, named with the profile", async () => {
  viewport(390);
  serve({ "/api/v1/version": SLURM, [COMPUTES]: CLUSTERS, [`${API}/gpu-h100`]: MINE[0], [API]: list([...BUILTINS, ...MINE]) });
  app("/profiles/gpu-h100");
  const more = await screen.findByRole("group", { name: "More for this profile" });
  expect([...more.querySelectorAll("a, button")].map((b) => b.textContent)).toEqual(["Duplicate gpu-h100", "Delete gpu-h100"]);
});
