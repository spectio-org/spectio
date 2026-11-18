// The Environment row of Launch (FU-P3-86g; ui-spec §4.8.1 "At Launch"; boards LiteLaunch,
// MLiteLaunch, LiteLaunchNewEnvironment): its states, the lines that follow the choice, the
// profile prefill, New environment in a dialog, and Copy's environment.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, VERSION, app, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/environments";
const SLURM = { ...VERSION, executor: "slurm" };
const INSPECTED = {
  location: "/data/rnaseq",
  revision: null,
  engine: "nextflow",
  engine_files: ["main.nf"],
  name: "rnaseq",
  version: "3.27.0",
  engine_version: "26.10.4",
  engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" },
  schema: { type: "object", properties: { depth: { type: "integer", default: 3 } } },
  schema_source: "nextflow_schema.json",
  profiles: ["docker", "slurm"],
};
const item = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, executor: "slurm", builtin: false, default: false, usable: true, unusable_reason: null },
  ...{ slurm: { partition: "htc", account: "mylab", time_min: null, mem_mib: null }, local: null },
  ...{ profiles: { nextflow: null, snakemake: null }, etag: `"${name}"` },
  ...over,
});
const LOCAL = item("local", { label: "Login node", executor: "local", builtin: true, slurm: null, local: { cpus: 2, mem_mib: 8192 } });
const BUILTINS = [item("slurm", { label: "SLURM (from spectio init)", builtin: true, default: true }), LOCAL];
const list = (items: unknown[], state = "ok", fallback = "slurm") => ({
  items,
  default: fallback,
  file: { path: "/home/amartin/.spectio/environments.toml", state, detail: null },
});

/** Launch on a SLURM server with these environments; returns the POST /runs bodies. */
function launchWith(environments: unknown, more: Record<string, unknown> = {}) {
  const posted: unknown[] = [];
  serve({
    "/api/v1/version": SLURM,
    [API]: environments,
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

test("from two environments: radios named with their executor, the default checked, the Tasks row follows the choice", async () => {
  const posted = launchWith(list([...BUILTINS, item("broken", { usable: false, unusable_reason: "partition is not a valid name" })]));
  const group = await screen.findByRole("group", { name: "Environment" });
  const slurm = within(group).getByRole("radio", { name: "SLURM (from spectio init), SLURM" });
  expect(slurm).toBeChecked();
  expect(slurm).toHaveAccessibleDescription("partition htc · SLURM account mylab");
  expect(within(group).queryByRole("radio", { name: /broken/ })).toBeNull();
  expect(screen.getByText("Not offered: broken (partition is not a valid name)")).toBeInTheDocument();
  await load();
  // the Executor row is dropped: the radio's badge carries it
  expect(within(where()).queryByText("Executor")).toBeNull();
  expect(tasksRow()).toHaveTextContent("sent to SLURM by Nextflow · partition htc");
  expect(screen.getByText("The login node and the run directory are fixed for this server.")).toBeInTheDocument();
  await userEvent.click(within(group).getByRole("radio", { name: "Login node, Local" }));
  expect(tasksRow()).toHaveTextContent("run on login1 by Nextflow · at most 2 CPUs");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({ environment: "local" });
});

test("one usable environment is a text row, with New environment beside it", async () => {
  launchWith(list([LOCAL]));
  expect(await screen.findByText("Environment: Login node · on login1 (the login node) · at most 2 CPUs and 8 GiB")).toBeInTheDocument();
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.getByRole("button", { name: "New environment" })).toBeInTheDocument();
});

test("over six environments: a native select with the summary under it", async () => {
  const many = Array.from({ length: 6 }, (_, i) => item(`env-${i}`));
  launchWith(list([...BUILTINS, ...many]));
  const select = await screen.findByRole("combobox", { name: "Environment" });
  expect(select).toHaveValue("slurm");
  expect(select).toHaveAccessibleDescription("partition htc · SLURM account mylab");
});

test("a list with nothing usable: the summary says Not chosen yet, not still loading (CR-P3FU86H-02)", async () => {
  launchWith(list([item("broken", { usable: false, unusable_reason: "partition is not a valid name" })]));
  await screen.findByText("Not offered: broken (partition is not a valid name)");
  await load();
  const summary = screen.getByRole("region", { name: "Summary" });
  expect(within(summary).getByText("Environment").nextElementSibling).toHaveTextContent("Not chosen yet");
  expect(screen.getByRole("link", { name: "Choose where it runs" })).toBeInTheDocument();
});

test("the list cannot be read: Retry, and Launch sends no environment", async () => {
  const posted = launchWith(() => json(500, { title: "boom", detail: "boom" }));
  expect(await screen.findByText("Environments could not be read")).toBeInTheDocument();
  expect(screen.getByText("The server's default environment will be used")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  await load();
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).not.toHaveProperty("environment");
});

test("the file has a mistake: built-ins only, a link to Environments, New environment waits", async () => {
  launchWith(list(BUILTINS, "invalid"));
  const line = await screen.findByText(/Your environments file has a mistake: only the built-ins are offered/);
  expect(within(line).getByRole("link", { name: "See Environments" })).toHaveAttribute("href", "/environments");
  const add = screen.getByRole("button", { name: "New environment" });
  expect(add).toHaveAttribute("aria-disabled", "true");
  expect(add).toHaveAccessibleDescription(/Your environments file has a mistake/);
});

test("a 422 on environment lands on the Environment group", async () => {
  launchWith(list(BUILTINS), {
    "/api/v1/runs": () => json(422, { title: "Invalid", detail: "Invalid", errors: [{ field: "environment", message: "slurm is not usable" }] }),
  });
  await screen.findByRole("group", { name: "Environment" });
  await load();
  await userEvent.click(launchButton());
  const group = screen.getByRole("group", { name: "Environment" });
  await waitFor(() => expect(group).toHaveAccessibleDescription("slurm is not usable"));
});

test("the environment's profile is preselected when the pipeline has it, until Profile is changed", async () => {
  const mine = item("mylab", { profiles: { nextflow: "docker", snakemake: "slurm" } });
  const embl = item("embl-env", { profiles: { nextflow: "embl", snakemake: null } });
  launchWith(list([...BUILTINS, mine, embl]));
  await load();
  const profile = screen.getByRole("combobox", { name: /^Profile/ });
  expect(profile).toHaveValue("");
  await userEvent.click(screen.getByRole("radio", { name: "mylab, SLURM" }));
  expect(profile).toHaveValue("docker");
  await userEvent.click(screen.getByRole("radio", { name: "embl-env, SLURM" }));
  expect(profile).toHaveValue("");
  expect(screen.getByText("The environment's profile embl is not in this pipeline: none selected")).toBeInTheDocument();
  // Snakemake with a profile: the profile owns the SLURM resources
  await userEvent.click(screen.getByRole("button", { name: "Snakemake" }));
  await userEvent.click(screen.getByRole("radio", { name: "mylab, SLURM" }));
  expect(profile).toHaveValue("slurm");
  expect(tasksRow()).toHaveTextContent(
    "sent to SLURM by Snakemake · resources and partition from the profile slurm (this environment's are not passed)",
  );
  await userEvent.selectOptions(profile, "docker");
  await userEvent.click(screen.getByRole("radio", { name: "embl-env, SLURM" }));
  expect(profile).toHaveValue("docker"); // changed by the user: kept
});

test("New environment opens the form in a dialog; on Save it is listed and checked", async () => {
  let items = [...BUILTINS];
  const created = item("mylab-long", { label: "Long jobs" });
  // POST /environments answers the new item, and the next list has it
  launchWith((_u: URL, init?: RequestInit) => {
    if (init?.method === "POST") return (items = [...items, created]), json(201, created);
    return json(200, list(items));
  });
  const add = await screen.findByRole("button", { name: "New environment" });
  await userEvent.click(add);
  const dialog = await screen.findByRole("dialog", { name: "New environment" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  const name = within(dialog).getByRole("textbox", { name: "Name" });
  await waitFor(() => expect(name).toHaveFocus());
  await userEvent.type(name, "mylab-long");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save and choose it" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(await screen.findByRole("radio", { name: "Long jobs, SLURM" })).toBeChecked();
});

test("a Reload that fails keeps the dialog and its values (CR-P3FU86G-03)", async () => {
  let reads = 0;
  launchWith((_u: URL, init?: RequestInit) => {
    if (init?.method === "POST") return json(409, { type: "/problems/environments-file-changed", title: "Changed", detail: "x" });
    return ++reads === 1 ? json(200, list(BUILTINS)) : json(500, { title: "boom", detail: "boom" });
  });
  await userEvent.click(await screen.findByRole("button", { name: "New environment" }));
  const dialog = await screen.findByRole("dialog", { name: "New environment" });
  await userEvent.type(within(dialog).getByRole("textbox", { name: "Name" }), "mylab-long");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save and choose it" }));
  await userEvent.click(await within(dialog).findByRole("button", { name: "Reload" }));
  expect(await screen.findByText("Environments could not be read")).toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "New environment" })).toBeInTheDocument();
  expect(within(screen.getByRole("dialog")).getByRole("textbox", { name: "Name" })).toHaveValue("mylab-long");
});

test("Cancel closes the dialog and gives focus back to New environment", async () => {
  launchWith(list(BUILTINS));
  const add = await screen.findByRole("button", { name: "New environment" });
  await userEvent.click(add);
  const dialog = await screen.findByRole("dialog", { name: "New environment" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(add).toHaveFocus());
});

test("Copy to a new launch preselects the run's environment, and the banner says when it is gone", async () => {
  const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
  const template = {
    workflow: { location: "/data/rnaseq", revision: null, engine: "nextflow" },
    ...{ profiles: [], params: {}, non_default: [], code_loading: [] },
    environment: "slurm",
    environment_notice: "The environment mylab of this run no longer exists: slurm is chosen.",
  };
  serve({
    "/api/v1/version": SLURM,
    [API]: list(BUILTINS, "ok", "local"),
    [`/api/v1/runs/${ID}:launch-template`]: template,
    [`/api/v1/runs/${ID}`]: { ...DETAIL, ...run({ state: "failed", name: "wgs" }) },
    "/api/v1/workflows:inspect": INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
  });
  app(`/launch?from=${ID}`);
  expect(await screen.findByText("The environment mylab of this run no longer exists: slurm is chosen.")).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "SLURM (from spectio init), SLURM" })).toBeChecked();
});
