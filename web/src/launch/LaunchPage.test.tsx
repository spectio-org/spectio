import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ICONS } from "../icons";
import { LayoutContext } from "../shell/layout";
import { LaunchPage } from "./LaunchPage";

const INSPECTED = {
  location: "/data/rnaseq",
  revision: null,
  engine: "nextflow",
  engine_files: ["main.nf"],
  name: "rnaseq",
  version: "3.27.0",
  engine_version: "26.10.4",
  engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" },
  schema: {
    type: "object",
    required: ["input"],
    properties: { input: { type: "string" }, depth: { type: "integer", default: 3 } },
  },
  schema_source: "nextflow_schema.json",
  profiles: ["docker", "test"],
};

function json(status: number, body: unknown): Response {
  const type = status >= 400 ? "application/problem+json" : "application/json";
  return new Response(JSON.stringify(body), { status, headers: { "content-type": type } });
}

const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function page(onLaunched = vi.fn(), phone = false) {
  render(
    <MantineProvider>
      <LayoutContext.Provider value={{ phone, titleRow: null }}>
        <LaunchPage onLaunched={onLaunched} />
      </LayoutContext.Provider>
    </MantineProvider>,
  );
  return onLaunched;
}

const pipeline = () => screen.getByRole("textbox", { name: /^Pipeline/ });
const launch = () => screen.getByRole("button", { name: "Launch" });

async function load(inspected: unknown = INSPECTED, location = "/data/rnaseq") {
  fetchMock.mockResolvedValueOnce(json(200, inspected));
  await userEvent.type(pipeline(), location);
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText(/form from nextflow_schema.json|no parameter schema/);
}

test('the page title is "Launch a workflow"', () => {
  page();
  expect(screen.getByRole("heading", { level: 1, name: "Launch a workflow" })).toBeInTheDocument();
});

test("Revision shows only once the Pipeline field reads as a repository (UX-G2-08)", async () => {
  page();
  await userEvent.type(pipeline(), "/data/rnaseq");
  expect(screen.queryByRole("textbox", { name: /Revision/ })).toBeNull();
  await userEvent.clear(pipeline());
  await userEvent.type(pipeline(), "nf-core/rnaseq");
  const revision = screen.getByRole("textbox", { name: /Revision/ });
  expect(revision).toBeRequired();
  expect(screen.getByText("Read as GitHub: https://github.com/nf-core/rnaseq")).toBeInTheDocument();
});

test("Load inspects; the guess is pressed; Launch waits for the required field, then posts", async () => {
  const onLaunched = page();
  expect(launch()).toHaveAttribute("aria-disabled", "true");
  expect(screen.getByText("Load a pipeline first")).toBeInTheDocument();
  await load();
  const [url] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/v1/workflows:inspect?location=%2Fdata%2Frnaseq");
  expect(screen.getByRole("button", { name: "Nextflow" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText(/Guessed from main.nf/)).toBeInTheDocument();
  expect(launch()).toHaveAttribute("aria-disabled", "true");
  expect(launch()).toHaveAccessibleDescription("Fill the required field: input");
  await userEvent.click(launch()); // aria-disabled: nothing is sent
  expect(fetchMock).toHaveBeenCalledTimes(1);

  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/data/samples.csv");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /Profile/ }), "docker");
  expect(launch()).not.toHaveAttribute("aria-disabled");
  fetchMock.mockResolvedValueOnce(json(201, { id: "run_1", name: "rnaseq-x", state: "queued" }));
  await userEvent.click(launch());
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_1"));
  const [postUrl, init] = fetchMock.mock.calls[1];
  expect(postUrl).toBe("/api/v1/runs");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual({
    workflow: { location: "/data/rnaseq", revision: null, engine: "nextflow" },
    profiles: ["docker"],
    params: { input: "/data/samples.csv" }, // depth kept its default: not sent
  });
});

test("an edit of the Pipeline field cancels the inspect in flight", async () => {
  page();
  let signal: AbortSignal | undefined;
  fetchMock.mockImplementationOnce((_url, init) => {
    signal = init?.signal ?? undefined;
    return new Promise((_resolve, reject) =>
      signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))),
    );
  });
  await userEvent.type(pipeline(), "/data/rnaseq");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  expect(screen.getByRole("button", { name: /Loading/ })).toHaveAttribute("aria-busy", "true");
  await userEvent.type(pipeline(), "2");
  expect(signal?.aborted).toBe(true);
  expect(screen.getByRole("button", { name: "Load" })).not.toHaveAttribute("aria-busy", "true");
  expect(screen.queryByRole("alert")).toBeNull(); // a cancel is not an error
  await userEvent.clear(pipeline());
  await load();
  await userEvent.type(pipeline(), "2"); // an edit after a load forgets its guess too (CR-P3T19-01)
  for (const name of ["Nextflow", "Snakemake"]) {
    expect(screen.getByRole("button", { name })).toHaveAttribute("aria-pressed", "false");
  }
});

test("an integer enum is sent as its integer, not its text (CR-P3T19-02)", async () => {
  const onLaunched = page();
  const schema = { type: "object", properties: { level: { type: "integer", enum: [1, 2] } } };
  await load({ ...INSPECTED, schema });
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /^level/ }), "2");
  fetchMock.mockResolvedValueOnce(json(201, { id: "run_1", name: "rnaseq-x", state: "queued" }));
  await userEvent.click(launch());
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_1"));
  expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body)).params).toEqual({ level: 2 });
});

test("a 422 of inspect lands on the Pipeline field", async () => {
  page();
  fetchMock.mockResolvedValueOnce(
    json(422, { status: 422, errors: [{ field: "location", message: "not a directory" }] }),
  );
  await userEvent.type(pipeline(), "/nope");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await waitFor(() => expect(pipeline()).toHaveAttribute("aria-invalid", "true"));
  expect(pipeline()).toHaveAccessibleDescription(expect.stringContaining("not a directory"));
});

test("a 422 of the launch maps each error onto its field, with aria-describedby", async () => {
  page();
  await load();
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "x");
  fetchMock.mockResolvedValueOnce(
    json(422, {
      status: 422,
      errors: [
        { field: "params.input", message: "is not a file" },
        { field: "workflow.engine", message: "no main.nf in this pipeline" },
        { field: "name", message: "too long" },
      ],
    }),
  );
  await userEvent.click(launch());
  const input = screen.getByRole("textbox", { name: /^input/ });
  await waitFor(() => expect(input).toHaveAttribute("aria-invalid", "true"));
  expect(input).toHaveAccessibleDescription(expect.stringContaining("is not a file"));
  expect(screen.getByRole("group", { name: "Engine" })).toHaveAccessibleDescription(
    expect.stringContaining("no main.nf in this pipeline"),
  );
  expect(screen.getByRole("textbox", { name: /Run name/ })).toHaveAccessibleDescription(
    expect.stringContaining("too long"),
  );
});

test("no schema: key/value rows, each labelled with its row", async () => {
  page();
  await load({ ...INSPECTED, schema: null, schema_source: "none" });
  await userEvent.click(screen.getByRole("button", { name: "Add a parameter" }));
  await userEvent.type(screen.getByRole("textbox", { name: "Name, row 1" }), "outdir");
  await userEvent.type(screen.getByRole("textbox", { name: "Value, row 1" }), "results");
  expect(screen.getByRole("button", { name: "Remove row 1" })).toBeInTheDocument();
  fetchMock.mockResolvedValueOnce(json(201, { id: "run_2" }));
  await userEvent.click(launch());
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body)).params).toEqual({ outdir: "results" });
});

test("both entry files: no guess, Launch says to choose the engine", async () => {
  page();
  await load({ ...INSPECTED, engine: null, engine_files: ["main.nf", "workflow/Snakefile"] });
  expect(screen.getByRole("button", { name: "Nextflow" })).toHaveAttribute("aria-pressed", "false");
  expect(launch()).toHaveAccessibleDescription("Choose the engine");
});

// An nf-core schema with two groups (LiteLaunch): one with a required field, one without.
const NF_CORE = {
  ...INSPECTED,
  name: "nf-core/rnaseq",
  schema: {
    type: "object",
    $defs: {
      input_output_options: {
        title: "Input/output options",
        description: "Where the pipeline finds its data.",
        fa_icon: "fas fa-folder-open",
        required: ["input"],
        properties: { input: { type: "string", format: "file-path", description: "The samplesheet." }, outdir: { type: "string" } },
      },
      alignment_options: {
        title: "Alignment options",
        fa_icon: "fas fa-dna",
        properties: { min_mapped_reads: { type: "number", default: 5 }, aligner: { type: "string", enum: ["star", "hisat2"] } },
      },
      other: { title: "Other", fa_icon: "fas fa-unknown-thing", properties: { x: { type: "string" } } },
    },
    allOf: [{ $ref: "#/$defs/input_output_options" }, { $ref: "#/$defs/alignment_options" }, { $ref: "#/$defs/other" }],
  },
};
const group = (name: RegExp) => screen.getByRole("region", { name });
const toggle = (name: RegExp) => screen.getByRole("button", { name });

test("UX-PAR-30: each schema group folds, with its icon, description, counts and status; issues open", async () => {
  page();
  await load(NF_CORE);
  // A required field still empty: open, and says so.
  const io = toggle(/^Input\/output options/);
  expect(io).toHaveAttribute("aria-expanded", "true");
  expect(io).toHaveAccessibleName("Input/output options 1 required field empty");
  expect(io).toHaveAccessibleDescription("Where the pipeline finds its data. · 2 parameters · 1 required");
  expect(group(/^Input\/output/).querySelector("path")).toHaveAttribute("d", ICONS.folder);
  // Defaults only: folded, and an unknown fa_icon falls back to the neutral icon.
  const align = toggle(/^Alignment options/);
  expect(align).toHaveAttribute("aria-expanded", "false");
  expect(align).toHaveAccessibleName("Alignment options defaults");
  expect(group(/^Alignment/).querySelector("path")).toHaveAttribute("d", ICONS.dna);
  expect(group(/^Other/).querySelector("path")).toHaveAttribute("d", ICONS.sliders);
  expect(screen.getByText("One section per schema group · 0 values differ from their defaults")).toBeInTheDocument();
  // Filled and changed: the status follows, the field's hint says so.
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/data/s.csv");
  expect(io).toHaveAccessibleName("Input/output options 1 required · filled 1 changed");
  expect(screen.getByRole("textbox", { name: /^input/ })).toHaveAccessibleDescription(
    "The samplesheet. · string · file-path · changed · no default",
  );
  await userEvent.click(align);
  await userEvent.type(screen.getByRole("textbox", { name: /^min_mapped_reads/ }), "10");
  expect(align).toHaveAccessibleName("Alignment options 1 changed");
  expect(screen.getByRole("textbox", { name: /^min_mapped_reads/ })).toHaveAccessibleDescription("number · changed · default 5");
  expect(screen.getByText("One section per schema group · 2 values differ from their defaults")).toBeInTheDocument();
});

// A Snakemake config inferred from config/config.yaml (LiteLaunchSnakemake): a nested map is a
// section of dotted keys.
const SNAKEMAKE = {
  ...INSPECTED,
  name: "rna-seq-star-deseq2",
  version: null,
  engine: "snakemake",
  engine_files: ["workflow/Snakefile"],
  schema_source: "inferred",
  profiles: ["slurm"],
  schema: {
    type: "object",
    properties: {
      samples: { type: "string", default: "config/samples.tsv" },
      ref: { type: "object", default: { species: "homo_sapiens", release: 113 } },
    },
  },
};

test("UX-PAR-31/32: a Snakemake nested map is a section of dotted keys, rebuilt on submit; the preview is YAML", async () => {
  const onLaunched = page();
  fetchMock.mockResolvedValueOnce(json(200, SNAKEMAKE));
  await userEvent.type(pipeline(), "/data/smk");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  const ref = await screen.findByRole("region", { name: /^ref/ });
  await userEvent.click(within(ref).getByRole("button", { name: /^ref/ }));
  const release = within(ref).getByRole("textbox", { name: "ref.release" });
  await userEvent.type(release, "114");
  const preview = screen.getByLabelText("Config preview, as YAML", { selector: "pre" });
  expect(preview.textContent).toBe("ref:\n  species: homo_sapiens\n  release: 114\n");
  fetchMock.mockResolvedValueOnce(json(422, { status: 422, errors: [{ field: "params.ref.release", message: "no such release" }] }));
  await userEvent.click(launch());
  await waitFor(() => expect(release).toHaveAttribute("aria-invalid", "true"));
  expect(release).toHaveAccessibleDescription(expect.stringContaining("no such release"));
  expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body)).params).toEqual({ ref: { species: "homo_sapiens", release: 114 } });
  expect(onLaunched).not.toHaveBeenCalled();
  expect(screen.getByText(/passed as --workflow-profile/)).toBeInTheDocument();
});

test("UX-PAR-32: the params.json preview is exactly the params Launch sends", async () => {
  const onLaunched = page();
  await load(NF_CORE);
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/data/s.csv");
  await userEvent.click(toggle(/^Alignment options/));
  await userEvent.type(screen.getByRole("textbox", { name: /^min_mapped_reads/ }), "10");
  const preview = screen.getByLabelText("params.json preview", { selector: "pre" });
  fetchMock.mockResolvedValueOnce(json(201, { id: "run_1" }));
  await userEvent.click(launch());
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_1"));
  const sent = JSON.parse(String(fetchMock.mock.calls[1][1]?.body)).params;
  expect(JSON.parse(preview.textContent!)).toEqual(sent);
  expect(sent).toEqual({ input: "/data/s.csv", min_mapped_reads: 10 });
  expect(screen.getByText(/passed with -params-file/)).toBeInTheDocument();
  expect(screen.getByText(/passed as -profile/)).toBeInTheDocument();
});

test("UX-PAR-33: the Loaded card's status, and Where it runs names the engine and the tasks", async () => {
  page();
  await load(NF_CORE);
  const card = screen.getByText("nf-core/rnaseq 3.27.0").closest("[data-loaded]")!;
  expect(within(card as HTMLElement).getByText("Loaded")).toBeInTheDocument();
  expect(within(card as HTMLElement).getByRole("img", { name: "Nextflow" })).toBeInTheDocument();
  const where = screen.getByRole("complementary", { name: "Where it runs and launch" });
  expect(within(where).getByText("Tasks")).toBeInTheDocument();
  expect(within(where).getByText(/fixed for this server/)).toBeInTheDocument();
});

test("UX-PAR-34: on the phone the pinned bar says why Launch waits, then what it launches", async () => {
  page(vi.fn(), true);
  expect(launch()).toHaveAccessibleDescription("Load a pipeline first");
  await load({ ...NF_CORE, profiles: ["docker"] });
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/data/s.csv");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /Profile/ }), "docker");
  expect(launch()).not.toHaveAttribute("aria-disabled");
  expect(launch()).toHaveAccessibleDescription("nf-core/rnaseq 3.27.0 · Nextflow · docker · 1 value changed");
});

test("SEC-P3PARB-01: a schema key Launch refuses is named, not dropped silently", async () => {
  page();
  const schema = JSON.parse('{"type":"object","properties":{"__proto__":{"type":"string"},"depth":{"type":"integer"}}}');
  await load({ ...INSPECTED, schema });
  expect(screen.getByRole("textbox", { name: /^depth/ })).toBeInTheDocument();
  expect(screen.getByText(/Not in the form: __proto__/)).toBeInTheDocument();
});
