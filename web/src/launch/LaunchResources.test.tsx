// Resources and Extra config file, two rows of "Where it runs" (FU-P3-110d; ui-spec §4.6 notes of
// 2026-11-10 and the drawn layout of FU-P3-110c; api §5.7; boards LiteLaunch, LiteLaunchSnakemake,
// MLiteLaunch): what each state shows and what POST /runs receives.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, json, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const SLURM_SERVER = { ...VERSION, executor: "slurm" };
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
  profiles: ["docker"],
};
const SNAKEMAKE = {
  ...INSPECTED,
  name: "kd-screen",
  version: null,
  engine: "snakemake",
  engine_files: ["workflow/Snakefile"],
  schema_source: "inferred",
  profiles: ["slurm"],
  schema: {
    type: "object",
    properties: { samples: { type: "string", default: "config/samples.tsv" }, ref: { type: "object", default: { build: "GRCh38", release: 113 } } },
  },
};
const item = (name: string, over: Record<string, unknown> = {}) => ({
  ...{ name, label: null, executor: "slurm", builtin: false, default: false, usable: true, unusable_reason: null },
  ...{ slurm: { partition: "htc", account: "mylab", time_min: null, mem_mib: null }, local: null },
  ...{ profiles: { nextflow: null, snakemake: null }, etag: `"${name}"` },
  ...over,
});
const LOCAL = item("local", { label: "Login node", executor: "local", builtin: true, default: true, slurm: null, local: { cpus: 2, mem_mib: 8192 } });
const LONG = item("mylab-long", { label: "Long jobs", slurm: { partition: "long", account: "mylab", time_min: 2880, mem_mib: 32768 } });
const envs = (items: unknown[], fallback = "local") => ({
  items,
  default: fallback,
  file: { path: "/home/amartin/.spectio/environments.toml", state: "ok", detail: null },
});

/** Launch with these environments and this pipeline; `answer` replies to POST /runs. Returns the bodies sent. */
function launchWith(over: { environments?: unknown; inspected?: unknown; answer?: () => Response | Promise<Response> } = {}) {
  const posted: Record<string, unknown>[] = [];
  serve({
    "/api/v1/version": SLURM_SERVER,
    "/api/v1/environments": over.environments ?? envs([LOCAL]),
    "/api/v1/workflows:inspect": over.inspected ?? INSPECTED,
    "/api/v1/runs?": { items: [], next: null },
    "/api/v1/runs": (_url: URL, init?: RequestInit) => {
      posted.push(JSON.parse(String(init?.body)));
      return over.answer ? over.answer() : json(201, { id: "run_1", name: "x", state: "queued" });
    },
  });
  app("/launch");
  return posted;
}
async function load(at = "/data/rnaseq") {
  await userEvent.type(await screen.findByRole("textbox", { name: /^Pipeline/ }), at);
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText(/· form (from|inferred)/);
}
const where = () => screen.getByRole("region", { name: "Where it runs" });
const row = (name: RegExp) => within(where()).getByRole("button", { name });
const launchButton = () => screen.getAllByRole("button", { name: /^Launch/ }).at(-1)!;
const summaryValue = (name: string) => within(screen.getByRole("region", { name: "Summary" })).getByText(name).nextElementSibling!;
const missing = () => document.getElementById("launch-missing")!;

test("both rows are folded by default, their closed lines say what is in force, and nothing extra is sent", async () => {
  const posted = launchWith();
  await load();
  const resources = row(/^Resources/);
  expect(resources).toHaveAttribute("aria-expanded", "false");
  expect(resources).toHaveTextContent("The pipeline's defaults");
  const config = row(/^Extra config file/);
  expect(config).toHaveAttribute("aria-expanded", "false");
  expect(config).toHaveTextContent("No extra config file");
  expect(summaryValue("Resources")).toHaveTextContent("from the environment");
  expect(summaryValue("Extra config")).toHaveTextContent("none");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).not.toHaveProperty("default_resources");
  expect(posted[0]).not.toHaveProperty("config_file");
});

test("Nextflow on Login node: three optional inputs with the caps in their hints; the values go in default_resources", async () => {
  const posted = launchWith();
  await load();
  await userEvent.click(row(/^Resources/));
  expect(within(where()).getByText(/Used by every process that does not set its own\. A process that sets its own CPUs, memory or time keeps them\. Replaces the pipeline's own default for all processes\./)).toBeInTheDocument();
  const cpus = screen.getByRole("textbox", { name: "CPUs per task" });
  expect(cpus).toHaveAttribute("inputmode", "numeric");
  expect(cpus).toHaveAttribute("placeholder", "the pipeline's default");
  expect(cpus).toHaveAccessibleDescription(expect.stringContaining("1 to 256 · at most 2 (Login node)"));
  const mem = screen.getByRole("textbox", { name: "Memory per task" });
  expect(mem).toHaveAttribute("inputmode", "decimal");
  expect(mem).toHaveAccessibleDescription(expect.stringContaining("Rounded to MiB · at most 8 GiB (Login node)"));
  expect(screen.getByRole("combobox", { name: "Memory per task, unit" })).toHaveValue("GiB");
  const time = screen.getByRole("group", { name: "Time per task" });
  const hours = within(time).getByRole("textbox", { name: "Time per task, hours" });
  const minutes = within(time).getByRole("textbox", { name: "Time per task, minutes" });
  expect(hours).toHaveAccessibleDescription(expect.stringContaining("1 min to 720 h (30 days)"));
  await userEvent.type(cpus, "2");
  await userEvent.type(mem, "6");
  await userEvent.type(hours, "2");
  await userEvent.type(minutes, "0");
  expect(summaryValue("Resources")).toHaveTextContent("2 CPUs · 6 GiB · 2 h per task; processes that set their own keep them");
  await userEvent.click(row(/^Resources/));
  expect(row(/^Resources/)).toHaveTextContent("Defaults: 2 CPUs · 6 GiB · 2 h per task");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0].default_resources).toEqual({ cpus: 2, mem_mib: 6144, time_min: 120 });
});

test("out of bounds before Launch: each error under its input, listed in Before Launch with a link, and nothing is sent", async () => {
  const posted = launchWith();
  await load();
  await userEvent.click(row(/^Resources/));
  const cpus = screen.getByRole("textbox", { name: "CPUs per task" });
  await userEvent.type(cpus, "4");
  await userEvent.type(screen.getByRole("textbox", { name: "Memory per task" }), "12");
  const hours = screen.getByRole("textbox", { name: "Time per task, hours" });
  await userEvent.type(hours, "0");
  await userEvent.type(screen.getByRole("textbox", { name: "Time per task, minutes" }), "0");
  expect(cpus).toHaveAttribute("aria-invalid", "true");
  expect(cpus).toHaveAccessibleDescription(expect.stringContaining("At most 2 CPUs in Login node"));
  expect(screen.getByRole("textbox", { name: "Memory per task" })).toHaveAccessibleDescription(expect.stringContaining("At most 8 GiB in Login node"));
  // the error first, then the hint, on each time input (UX-P3FU110C-01)
  expect(hours).toHaveAttribute("aria-invalid", "true");
  expect(hours).toHaveAccessibleDescription(expect.stringMatching(/^At least 1 minute/));
  const list = within(missing());
  expect(list.getByRole("link", { name: "Fix CPUs per task: at most 2 on Login node" })).toBeInTheDocument();
  expect(list.getByRole("link", { name: "Fix Memory per task: at most 8 GiB on Login node" })).toBeInTheDocument();
  const timeLink = list.getByRole("link", { name: "Fix Time per task: at least 1 minute" });
  await userEvent.click(row(/^Resources/)); // folded: the link opens it again
  await userEvent.click(timeLink);
  await waitFor(() => expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveFocus());
  await userEvent.click(launchButton());
  expect(posted).toHaveLength(0);
  await userEvent.clear(screen.getByRole("textbox", { name: "Time per task, hours" }));
  await userEvent.type(screen.getByRole("textbox", { name: "Time per task, hours" }), "721");
  expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveAccessibleDescription(expect.stringMatching(/^At most 720 hours \(30 days\)/));
});

test("a SLURM environment's values are the placeholders, said under the inputs and on the folded line", async () => {
  launchWith({ environments: envs([LONG], "mylab-long") });
  await load();
  expect(row(/^Resources/)).toHaveTextContent("From the environment: 48 h · 32 GiB per task");
  await userEvent.click(row(/^Resources/));
  const mem = screen.getByRole("textbox", { name: "Memory per task" });
  expect(mem).toHaveAttribute("placeholder", "32");
  expect(mem).toHaveAccessibleDescription(expect.stringContaining("Empty: 32 GiB, from Long jobs"));
  expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveAttribute("placeholder", "48");
  expect(screen.getByRole("textbox", { name: "Time per task, minutes" })).toHaveAttribute("placeholder", "0");
  expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveAccessibleDescription(expect.stringContaining("Empty: 48 h, from Long jobs"));
});

test("the server's 422 on a resource lands on its input", async () => {
  launchWith({ answer: () => json(422, { status: 422, errors: [{ field: "default_resources.cpus", message: "At most 2 CPUs in Login node" }] }) });
  await load();
  await userEvent.click(launchButton());
  const cpus = await screen.findByRole("textbox", { name: "CPUs per task" });
  expect(cpus).toHaveAttribute("aria-invalid", "true");
  expect(cpus).toHaveAccessibleDescription(expect.stringContaining("At most 2 CPUs in Login node"));
});

test("Snakemake with no profile: memory and time only, CPUs from threads, time not enforced on this machine", async () => {
  const posted = launchWith({ inspected: SNAKEMAKE });
  await load("/data/smk");
  await userEvent.click(row(/^Resources/));
  expect(screen.queryByRole("textbox", { name: "CPUs per task" })).toBeNull();
  expect(within(where()).getByText("Snakemake takes CPUs from each rule's threads.")).toBeInTheDocument();
  expect(within(where()).getByText(/Used by every rule that does not set its own\. A rule that sets its own memory or time keeps them\./)).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Time per task, hours" })).toHaveAccessibleDescription(expect.stringContaining("not enforced on this machine"));
  await userEvent.type(screen.getByRole("textbox", { name: "Memory per task" }), "4");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0].default_resources).toEqual({ mem_mib: 4096 });
});

test("Snakemake with a profile: the profile sets the resources, values typed before are kept but not sent", async () => {
  const posted = launchWith({ inspected: SNAKEMAKE });
  await load("/data/smk");
  await userEvent.click(row(/^Resources/));
  await userEvent.type(screen.getByRole("textbox", { name: "Memory per task" }), "4");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /^Profile/ }), "slurm");
  expect(within(where()).getByText(/The profile slurm sets the resources, so none are set here\./)).toBeInTheDocument();
  expect(screen.queryByRole("textbox", { name: "Memory per task" })).toBeNull();
  expect(summaryValue("Resources")).toHaveTextContent("from the profile slurm");
  // back to no profile: the value typed is still there
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /^Profile/ }), "");
  expect(screen.getByRole("textbox", { name: "Memory per task" })).toHaveValue("4");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /^Profile/ }), "slurm");
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).not.toHaveProperty("default_resources");
});

test("the extra config file: its hint and kept-as line, sent as config_file, and the reading status while Launch waits", async () => {
  let reply: (r: Response) => void = () => {};
  const posted = launchWith({ answer: () => new Promise<Response>((done) => (reply = done)) });
  await load();
  await userEvent.click(row(/^Extra config file/));
  const input = screen.getByRole("textbox", { name: "Extra config file (optional)" });
  expect(input).toHaveAccessibleDescription(expect.stringContaining("A .config file, passed with -c after the pipeline's own."));
  expect(input).toHaveAccessibleDescription(expect.stringContaining("type its absolute path (the browser cannot list the server's files)"));
  expect(input).toHaveAccessibleDescription(
    expect.stringContaining("Read once at Launch and kept with the run as extra.config, readable by you only (0600), with its SHA-256 · at most 256 KiB"),
  );
  await userEvent.type(input, "/home/amartin/configs/lab-tweaks.config");
  expect(summaryValue("Extra config")).toHaveTextContent("/home/amartin/configs/lab-tweaks.config");
  await userEvent.click(launchButton());
  expect(await screen.findByText("Reading lab-tweaks.config on login1: its owner, mode and size, then a copy for the run…")).toHaveAttribute("role", "status");
  expect(input).toHaveAttribute("readonly");
  expect(launchButton()).toHaveTextContent("Launching…");
  expect(launchButton()).toHaveAttribute("aria-disabled", "true");
  expect(posted[0].config_file).toBe("/home/amartin/configs/lab-tweaks.config");
  reply(json(201, { id: "run_1", name: "x", state: "queued" }));
});

test("the server refuses the file (422): its reason exactly, the form's hint on its own line, focus on the input", async () => {
  launchWith({ answer: () => json(422, { status: 422, errors: [{ field: "config_file", message: "the file is writable by group or others" }] }) });
  await load();
  await userEvent.click(row(/^Extra config file/));
  const input = screen.getByRole("textbox", { name: "Extra config file (optional)" });
  await userEvent.type(input, "/home/amartin/configs/lab-tweaks.config");
  await userEvent.click(row(/^Extra config file/)); // folded again: the error opens it
  await userEvent.click(launchButton());
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("the file is writable by group or others");
  expect(alert).toHaveTextContent("Fix its mode (chmod go-w), then Launch again.");
  const again = screen.getByRole("textbox", { name: "Extra config file (optional)" });
  expect(again).toHaveAttribute("aria-invalid", "true");
  await waitFor(() => expect(again).toHaveFocus());
});

test("the file could not be read (503): a banner with the server's reason, the values kept, and Launch again", async () => {
  let answers = 0;
  const posted = launchWith({
    answer: () =>
      ++answers === 1
        ? json(503, { status: 503, type: "/problems/runner-offline", title: "File system not answering", detail: "the config file cannot be read: Input/output error" })
        : json(201, { id: "run_1", name: "x", state: "queued" }),
  });
  await load();
  await userEvent.click(row(/^Extra config file/));
  await userEvent.type(screen.getByRole("textbox", { name: "Extra config file (optional)" }), "/home/amartin/x.config");
  await userEvent.click(launchButton());
  const banner = await screen.findByRole("alert");
  expect(banner).toHaveTextContent("The extra config file could not be read: Input/output error. Nothing was started and your values are kept.");
  expect(screen.getByRole("textbox", { name: "Extra config file (optional)" })).toHaveValue("/home/amartin/x.config");
  await userEvent.click(within(banner).getByRole("button", { name: "Launch again" }));
  await waitFor(() => expect(posted).toHaveLength(2));
});

test("Snakemake with an extra file sends only the keys set, and the preview says where the others come from", async () => {
  const posted = launchWith({ inspected: SNAKEMAKE });
  await load("/data/smk");
  await userEvent.click(row(/^Extra config file/));
  const input = screen.getByRole("textbox", { name: "Extra config file (optional)" });
  expect(input).toHaveAccessibleDescription(expect.stringContaining("A .yaml or .json file of workflow config, merged key by key under the form's values"));
  expect(input).toHaveAccessibleDescription(expect.stringContaining("a top-level map, no __use_yte__"));
  await userEvent.type(input, "/home/amartin/configs/kd-screen-extra.yaml");
  const ref = screen.getByRole("region", { name: /^ref/ });
  await userEvent.click(within(ref).getByRole("button", { name: /^ref/ }));
  await userEvent.type(within(ref).getByRole("textbox", { name: "ref.release (optional)" }), "114");
  await userEvent.click(screen.getByRole("button", { name: /^Config preview, as YAML/ }));
  expect(screen.getByLabelText("Config preview, as YAML", { selector: "pre" }).textContent).toBe("ref:\n  release: 114\n");
  expect(screen.getByText(/Only the keys you set · .* other keys come from extra\.yaml, then the pipeline/)).toBeInTheDocument();
  await userEvent.click(launchButton());
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0].params).toEqual({ ref: { release: 114 } });
  expect(posted[0].config_file).toBe("/home/amartin/configs/kd-screen-extra.yaml");
});

test("phone: the same rows in the main column, the 503 banner above the form", async () => {
  viewport(360);
  launchWith({ answer: () => json(503, { status: 503, title: "File system not answering", detail: "the config file cannot be read: timed out" }) });
  await load();
  await userEvent.click(row(/^Extra config file/));
  await userEvent.type(screen.getByRole("textbox", { name: "Extra config file (optional)" }), "/home/amartin/x.config");
  await userEvent.click(launchButton());
  const banner = await screen.findByRole("alert");
  // before the form's first section, never in the pinned bar
  expect(banner.compareDocumentPosition(screen.getByRole("region", { name: "Pipeline" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(banner.closest(".launch-bar")).toBeNull();
});
