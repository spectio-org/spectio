// The catalog at Launch (FU-P3-87e; ui-spec §4.7.1 "At Launch"; boards LiteLaunch, MLiteLaunch):
// the picker and its states, fill on choose and Load to inspect, the engine as the user's choice,
// the profile and params prefill, the reset rules, Manage catalog and Save to catalog in dialogs,
// and Try leaving out saved locations.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, fetched, json, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/catalog";
const PATH = "/home/amartin/.spectio/catalog.toml";
const SLURM = { ...VERSION, executor: "slurm" };
const entry = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, engine: "nextflow", location: "nf-core/rnaseq", revision: "3.27.0" },
  ...{ profile: "test", params_file: "conf/test.yaml", etag: `"${name}-1"` },
  ...over,
});
const list = (items: unknown[], state = "ok", detail: string | null = null) => ({ items, file: { path: PATH, state, detail } });
const RNASEQ = entry("rnaseq-test");
const LIVER = entry("liver-qc", { label: "Liver QC", engine: "snakemake", location: "/g/demo-lab/pipelines/liver", revision: null, profile: null, params_file: null });
const INSPECTED = {
  location: "https://github.com/nf-core/rnaseq",
  revision: "3.27.0",
  engine: null,
  engine_files: ["main.nf", "Snakefile"], // no guess: the engine is the entry's
  name: "nf-core/rnaseq",
  version: "3.27.0",
  engine_version: null,
  engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" },
  schema: { type: "object", properties: { depth: { type: "integer", default: 3 }, input: { type: "string" }, custom_config_base: { type: "string" } } },
  schema_source: "nextflow_schema.json",
  profiles: ["docker", "test"],
  params_file: {
    path: "conf/test.yaml",
    values: { depth: 5, input: "s3://x/samples.csv", custom_config_base: "/g/lab/conf", foo: 1, bar: "b" },
    code_loading: [
      { field: "params.custom_config_base", value: "/g/lab/conf", writable_by_others: false },
      { field: "params_file", value: "/data/rnaseq/conf/test.yaml", writable_by_others: true },
    ],
    error: null,
  },
};

/** Launch with this catalog; returns the fetch mock and the POST /runs bodies. */
function launchWith(catalog: unknown, more: Record<string, unknown> = {}) {
  const posted: unknown[] = [];
  const mock = serve({
    "/api/v1/version": SLURM,
    "/api/v1/environments": () => json(500, { title: "x" }),
    [API]: catalog,
    "/api/v1/workflows:inspect": INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
    "/api/v1/runs": (_url: URL, init?: RequestInit) => (posted.push(JSON.parse(String(init?.body))), json(201, { id: "run_1", name: "x", state: "queued" })),
    ...more,
  });
  app("/launch");
  return { mock, posted };
}
const picker = () => screen.findByRole("combobox", { name: "From your catalog" });
const pipeline = () => screen.getByRole("textbox", { name: /^Pipeline/ });
const loadButton = () => screen.getByRole("button", { name: "Load" });
const section = () => screen.getByRole("region", { name: "Pipeline" });
const before = () => screen.getByRole("status", { name: "Before Launch" });
const inspects = (mock: ReturnType<typeof serve>) => fetched(mock).filter((u) => u.startsWith("/api/v1/workflows:inspect"));

test("choosing an entry only fills the form; Load inspects with its params file; Launch sends what the form holds", async () => {
  const { mock, posted } = launchWith(list([LIVER, RNASEQ]));
  const select = await picker();
  expect([...select.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["None", "Liver QC · Snakemake", "rnaseq-test · Nextflow"]);
  await userEvent.selectOptions(select, "rnaseq-test");
  expect(pipeline()).toHaveValue("nf-core/rnaseq");
  expect(screen.getByRole("textbox", { name: /Revision/ })).toHaveValue("3.27.0");
  expect(select).toHaveAccessibleDescription("nf-core/rnaseq@3.27.0");
  expect(screen.getByRole("button", { name: "Nextflow" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Nextflow, from the catalog entry")).toBeInTheDocument();
  expect(screen.getByText("From the catalog: rnaseq-test · profile test · parameters from conf/test.yaml")).toHaveAttribute("role", "status");
  expect(inspects(mock)).toEqual([]); // the choice fetches nothing
  await userEvent.click(loadButton());
  expect(await screen.findByText("Loaded")).toBeInTheDocument();
  expect(inspects(mock)).toEqual(["/api/v1/workflows:inspect?location=nf-core/rnaseq&revision=3.27.0&params_file=conf/test.yaml"]);
  // the engine stays the entry's, though the files allow both
  expect(screen.getByRole("button", { name: "Nextflow" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("combobox", { name: /^Profile/ })).toHaveValue("test");
  expect(screen.getByRole("textbox", { name: /^depth/ })).toHaveValue("5");
  expect(screen.getByText("3 values of conf/test.yaml fill the form and read changed. 2 values of conf/test.yaml have no field in this form, and are not sent: foo, bar")).toBeInTheDocument();
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml sets custom_config_base: /g/lab/conf")).toBeInTheDocument();
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml loads code or configuration · writable by others")).toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "Summary" })).getByText(/from the catalog entry rnaseq-test/)).toBeInTheDocument();
  await userEvent.click(screen.getAllByRole("button", { name: "Launch" }).at(-1)!);
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({
    workflow: { location: "https://github.com/nf-core/rnaseq", revision: "3.27.0", engine: "nextflow" },
    profiles: ["test"],
    params: { depth: 5, input: "s3://x/samples.csv", custom_config_base: "/g/lab/conf" },
  });
});

test("a code_loading warning names what Launch sends: none for a hidden field or a changed value (SEC-P3FU87E-02)", async () => {
  const hidden = { ...INSPECTED.schema, properties: { ...INSPECTED.schema.properties, custom_config_base: { type: "string", hidden: true } } };
  launchWith(list([RNASEQ]), { "/api/v1/workflows:inspect": { ...INSPECTED, schema: hidden } });
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  expect(screen.getByText(/have no field in this form, and are not sent: custom_config_base, foo, bar/)).toBeInTheDocument();
  expect(within(before()).queryByText(/sets custom_config_base/)).toBeNull();
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml loads code or configuration · writable by others")).toBeInTheDocument();
});

test("a code_loading warning goes when the value is changed in the form (SEC-P3FU87E-02)", async () => {
  launchWith(list([RNASEQ]));
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml sets custom_config_base: /g/lab/conf")).toBeInTheDocument();
  await userEvent.clear(screen.getByRole("textbox", { name: /^custom_config_base/ }));
  expect(within(before()).queryByText(/sets custom_config_base/)).toBeNull();
});

test("the params file itself not writable by others is still named before Launch (SEC-P3FU87E-01)", async () => {
  const file = { ...INSPECTED.params_file, code_loading: [{ field: "params_file", value: "/data/rnaseq/conf/test.yaml", writable_by_others: false }] };
  launchWith(list([RNASEQ]), { "/api/v1/workflows:inspect": { ...INSPECTED, params_file: file } });
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml loads code or configuration")).toBeInTheDocument();
});

test("None after Load keeps the params file's report: the unplaced line and the warnings (CR-P3FU87E-02)", async () => {
  launchWith(list([RNASEQ]));
  const select = await picker();
  await userEvent.selectOptions(select, "rnaseq-test");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  await userEvent.selectOptions(select, "");
  expect(screen.queryByText(/^From the catalog:/)).toBeNull();
  expect(screen.getByRole("textbox", { name: /^depth/ })).toHaveValue("5");
  expect(screen.getByText(/2 values of conf\/test.yaml have no field in this form, and are not sent: foo, bar/)).toBeInTheDocument();
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml sets custom_config_base: /g/lab/conf")).toBeInTheDocument();
  expect(within(before()).getByText("Warning, not a blocker: conf/test.yaml loads code or configuration · writable by others")).toBeInTheDocument();
});

test("an entry edited in Manage catalog after Load: the card's Edit opens the new values and sends the new etag (CR-P3FU87E-01)", async () => {
  let item = RNASEQ;
  const puts: RequestInit[] = [];
  launchWith(() => json(200, list([item])), {
    [`${API}/rnaseq-test`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "PUT") return json(200, item);
      puts.push(init);
      item = { ...JSON.parse(String(init.body)), etag: `"rnaseq-test-${puts.length + 1}"` };
      return json(200, item);
    },
  });
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  await userEvent.click(screen.getByRole("button", { name: "Manage catalog" }));
  const manage = await screen.findByRole("dialog", { name: "Manage catalog" });
  await userEvent.click(within(manage).getByRole("button", { name: "Edit rnaseq-test" }));
  await userEvent.type(within(manage).getByLabelText("Label (optional)"), "RNA-seq test");
  await userEvent.click(within(manage).getByRole("button", { name: "Save" }));
  await within(manage).findByRole("button", { name: "Add pipeline" });
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await userEvent.click(screen.getByRole("button", { name: "Edit rnaseq-test" }));
  const dialog = await screen.findByRole("dialog", { name: "Edit rnaseq-test" });
  expect(within(dialog).getByLabelText("Label (optional)")).toHaveValue("RNA-seq test");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
  await waitFor(() => expect(puts).toHaveLength(2));
  expect(new Headers(puts[1].headers).get("if-match")).toBe('"rnaseq-test-2"');
});

test("a params file that cannot be read is a line, and the pipeline loads with its defaults", async () => {
  launchWith(list([RNASEQ]), { "/api/v1/workflows:inspect": { ...INSPECTED, params_file: { path: "conf/test.yaml", values: null, code_loading: [], error: "not found" } } });
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  expect(await screen.findByText("conf/test.yaml could not be read: not found")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: /^depth/ })).toHaveValue("");
});

test("the entry's profile not in the pipeline: its line, and the environment's rule", async () => {
  launchWith(list([entry("rnaseq-test", { profile: "embl" })]));
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  expect(await screen.findByText("The catalog's profile embl is not in this pipeline: none selected")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: /^Profile/ })).toHaveValue("");
});

test("the entry's profile not in the pipeline, the environment's is: the line says it was selected instead (CR-P3FU87E-05)", async () => {
  const env = { name: "slurm", label: null, executor: "slurm", builtin: true, default: true, usable: true, unusable_reason: null, slurm: { partition: "htc", account: null, time_min: null, mem_mib: null }, local: null, profiles: { nextflow: "docker", snakemake: null }, etag: '"slurm"' };
  const environments = { items: [env], default: "slurm", file: { path: "/home/amartin/.spectio/environments.toml", state: "ok", detail: null } };
  launchWith(list([entry("rnaseq-test", { profile: "embl" })]), { "/api/v1/environments": environments });
  await userEvent.selectOptions(await picker(), "rnaseq-test");
  await userEvent.click(loadButton());
  expect(await screen.findByText("The catalog's profile embl is not in this pipeline: the environment's profile docker is selected")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: /^Profile/ })).toHaveValue("docker");
});

test("an entry whose pipeline is gone: the error names the entry, and the picker keeps it", async () => {
  launchWith(list([LIVER]), {
    "/api/v1/workflows:inspect": () =>
      json(422, { title: "Validation failed", errors: [{ field: "location", message: "/g/demo-lab/pipelines/liver is not a directory this account can read." }] }),
  });
  const select = await picker();
  await userEvent.selectOptions(select, "liver-qc");
  await userEvent.click(loadButton());
  expect(await screen.findByText("/g/demo-lab/pipelines/liver is not a directory this account can read. From your catalog entry liver-qc: edit it in Manage catalog.")).toBeInTheDocument();
  expect(select).toHaveValue("liver-qc");
});

test("reset rules: editing Pipeline sets the picker to None; None keeps the fields; Clear and start empty empties them", async () => {
  launchWith(list([LIVER, RNASEQ]));
  const select = await picker();
  await userEvent.selectOptions(select, "liver-qc");
  await userEvent.type(pipeline(), "-v2");
  expect(select).toHaveValue("");
  expect(screen.queryByText(/^From the catalog:/)).toBeNull();
  await userEvent.selectOptions(select, "rnaseq-test");
  await userEvent.selectOptions(select, "");
  expect(pipeline()).toHaveValue("nf-core/rnaseq");
  expect(screen.queryByText(/^From the catalog:/)).toBeNull();
  await userEvent.selectOptions(select, "liver-qc"); // another entry replaces the form
  expect(pipeline()).toHaveValue("/g/demo-lab/pipelines/liver");
  expect(screen.getByRole("button", { name: "Snakemake" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: "Clear and start empty" }));
  expect(pipeline()).toHaveValue("");
  expect(select).toHaveValue("");
  expect(screen.getByRole("button", { name: "Snakemake" })).toHaveAttribute("aria-pressed", "false");
});

test("states: loading, a read error with Retry, an empty catalog", async () => {
  let answer: (r: Response) => void = () => {};
  let calls = 0;
  launchWith(() => (++calls === 1 ? new Promise<Response>((r) => (answer = r)) : json(200, list([]))));
  expect(await screen.findByText("Loading the catalog…")).toBeInTheDocument();
  answer(json(500, { title: "boom", detail: "boom" }));
  expect(await screen.findByText("The catalog could not be read.")).toBeInTheDocument();
  await userEvent.click(within(section()).getByRole("button", { name: "Retry" }));
  const empty = await screen.findByText("Your catalog is empty. Load a pipeline, then Save to catalog.");
  expect(empty).toHaveAttribute("role", "status");
  expect(screen.queryByRole("combobox", { name: "From your catalog" })).toBeNull();
  expect(screen.getByRole("button", { name: "Manage catalog" })).toBeInTheDocument();
  expect(pipeline()).toBeEnabled(); // the free field works in every state
});

test.each([
  ["refused", "Spectio does not read your catalog file: see Manage catalog", false],
  ["invalid", "Your catalog file has a mistake: see Manage catalog", false],
  ["unreachable", "Your catalog cannot be read right now", true],
])("the file %s: its line (UX-P3FU87C-06)", async (state, line, retry) => {
  launchWith(list([], state, "group-writable"));
  expect(await screen.findByText(line)).toBeInTheDocument();
  expect(!!within(section()).queryByRole("button", { name: "Retry" })).toBe(retry);
});

test("Manage catalog: a dialog with the list's rows, focus on its heading, Edit in place with Back, focus back on close", async () => {
  launchWith(list([LIVER, RNASEQ]));
  await picker();
  const manage = screen.getByRole("button", { name: "Manage catalog" });
  await userEvent.click(manage);
  const dialog = await screen.findByRole("dialog", { name: "Manage catalog" });
  await waitFor(() => expect(within(dialog).getByRole("heading", { name: "Manage catalog" })).toHaveFocus());
  // the same content as the page list (UX-P3FU87C-01): each label a heading that takes focus
  const row = within(dialog).getByRole("heading", { name: "Liver QC" }).closest("article")!;
  expect(within(dialog).getByRole("heading", { name: "Liver QC" })).toHaveAttribute("tabindex", "-1");
  expect(row).toHaveTextContent("/g/demo-lab/pipelines/liver");
  expect(within(dialog).getByRole("heading", { name: "rnaseq-test" }).closest("article")).toHaveTextContent("profile test · parameters from conf/test.yaml");
  await userEvent.click(within(dialog).getByRole("button", { name: "Edit rnaseq-test" }));
  expect(within(dialog).getByRole("textbox", { name: /^Name/ })).toHaveValue("rnaseq-test");
  await userEvent.click(within(dialog).getByRole("button", { name: "Back" }));
  expect(within(dialog).getByRole("button", { name: "Add pipeline" })).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(manage).toHaveFocus());
});

test("Save to catalog: a dialog prefilled with a unique name; on Save the entry is chosen and the card says so", async () => {
  const saved = entry("nf-core-rnaseq-2", { profile: null, params_file: null });
  let items: unknown[] = [entry("nf-core-rnaseq", { location: "/elsewhere", revision: null })];
  const posts: unknown[] = [];
  launchWith(() => json(200, list(items)), {
    "/api/v1/workflows:inspect": { ...INSPECTED, params_file: null },
    [API]: (_url: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list(items));
      posts.push(JSON.parse(String(init.body)));
      items = [...items, saved];
      return json(201, saved);
    },
  });
  await picker();
  await userEvent.type(pipeline(), "nf-core/rnaseq");
  await userEvent.type(screen.getByRole("textbox", { name: /Revision/ }), "3.27.0");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  await userEvent.click(screen.getByRole("button", { name: "Nextflow" }));
  const save = screen.getByRole("button", { name: "Save to catalog" });
  await userEvent.click(save);
  const dialog = await screen.findByRole("dialog", { name: "Save to catalog" });
  const name = within(dialog).getByRole("textbox", { name: /^Name/ });
  await waitFor(() => expect(name).toHaveFocus());
  expect(name).toHaveValue("nf-core-rnaseq-2");
  expect(within(dialog).getByRole("textbox", { name: /^Pipeline/ })).toHaveValue("https://github.com/nf-core/rnaseq");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(posts[0]).toMatchObject({ name: "nf-core-rnaseq-2", engine: "nextflow", revision: "3.27.0" });
  expect(await screen.findByRole("combobox", { name: "From your catalog" })).toHaveValue("nf-core-rnaseq-2");
  expect(screen.getByText("In your catalog as nf-core-rnaseq-2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Edit nf-core-rnaseq-2" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Save to catalog" })).toBeNull();
});

/** Launch with a loaded pipeline not in the catalog; returns its Save to catalog button. */
async function loadedNotSaved() {
  launchWith(list([]), { "/api/v1/workflows:inspect": { ...INSPECTED, params_file: null } });
  await screen.findByText("Your catalog is empty. Load a pipeline, then Save to catalog.");
  await userEvent.type(pipeline(), "nf-core/rnaseq");
  await userEvent.type(screen.getByRole("textbox", { name: /Revision/ }), "3.27.0");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  return screen.getByRole("button", { name: "Save to catalog" });
}

test.each([
  ["Cancel", 1440],
  ["Escape", 1440],
  ["Cancel", 390],
  ["Escape", 390],
])("Save to catalog: %s at %ipx closes the dialog and focus goes back to Save to catalog (CR-P3FU87E-04)", async (how, width) => {
  viewport(width);
  const save = await loadedNotSaved();
  await userEvent.click(save);
  const dialog = await screen.findByRole("dialog", { name: "Save to catalog" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(!!dialog.closest(".sp-bottom-sheet")).toBe(width === 390); // the phone's full-height sheet
  await waitFor(() => expect(within(dialog).getByRole("textbox", { name: /^Name/ })).toHaveFocus());
  if (how === "Cancel") await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
  else await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(save).toHaveFocus());
});

test("Save to catalog waits while the catalog cannot be read", async () => {
  launchWith(() => json(500, { title: "boom" }), { "/api/v1/workflows:inspect": { ...INSPECTED, params_file: null } });
  await screen.findByText("The catalog could not be read.");
  await userEvent.type(pipeline(), "nf-core/rnaseq");
  await userEvent.type(screen.getByRole("textbox", { name: /Revision/ }), "3.27.0");
  await userEvent.click(loadButton());
  await screen.findByText("Loaded");
  const save = screen.getByRole("button", { name: "Save to catalog" });
  expect(save).toHaveAttribute("aria-disabled", "true");
  expect(save).toHaveAccessibleDescription("Waits until the catalog can be read");
  await userEvent.click(save);
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("Try a test pipeline leaves out a location already in the catalog", async () => {
  const at = (location: string, name: string) => run({ id: `run_${name}`, workflow: { ...run().workflow, name, location } });
  launchWith(list([LIVER]), { "/api/v1/runs?": { items: [at("/g/demo-lab/pipelines/liver", "liver"), at("/p/a", "a")], next: null } });
  const group = await screen.findByRole("group", { name: "Try a test pipeline" });
  await picker();
  expect(within(group).getByRole("button", { name: "Use a, /p/a" })).toBeInTheDocument();
  expect(within(group).queryByRole("button", { name: /liver/ })).toBeNull();
});
