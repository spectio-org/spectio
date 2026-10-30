import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
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

function page(onLaunched = vi.fn()) {
  render(
    <MantineProvider>
      <LaunchPage onLaunched={onLaunched} />
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
