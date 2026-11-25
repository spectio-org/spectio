// The refusal of the paths the containers would not see (built 2026-11-25, api §5.2): the 422's
// `allow_unmounted` field shows the server's words and a checkbox; launching again with it sends
// `allow_unmounted: true`.
import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { LayoutContext } from "../shell/layout";
import { LaunchPage } from "./LaunchPage";

const INSPECTED = {
  location: "/data/pipeline",
  revision: null,
  engine: "snakemake",
  engine_files: ["workflow/Snakefile"],
  main_scripts: [],
  name: "pipeline",
  version: null,
  engine_version: "9.27.1",
  engine_versions: { nextflow: "26.10.4", snakemake: "9.27.1" },
  schema: { type: "object", required: ["input"], properties: { input: { type: "string" } } },
  schema_source: "config.schema.yaml",
  profiles: [],
};

const REFUSAL = {
  type: "/problems/validation-failed",
  status: 422,
  errors: [
    {
      field: "allow_unmounted",
      message:
        "May not be visible in the containers: /shared/scratch/samples.csv. Add -B /shared to the Apptainer options of environment local, or confirm to launch anyway.",
    },
  ],
};

function json(status: number, body: unknown): Response {
  const type = status >= 400 ? "application/problem+json" : "application/json";
  return new Response(JSON.stringify(body), { status, headers: { "content-type": type } });
}

const fetchMock = vi.fn<typeof fetch>();
// The Environment row, the catalog picker and the feature flags read on their own (as in
// LaunchPage.test): they fail here, so the form sends no environment and no profile.
beforeEach(() =>
  vi.stubGlobal("fetch", (url: RequestInfo | URL, init?: RequestInit) =>
    ["/api/v1/environments", "/api/v1/catalog", "/api/v1/features"].includes(String(url))
      ? Promise.resolve(json(500, { title: "x" }))
      : fetchMock(url, init),
  ),
);
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

function page(onLaunched = vi.fn()) {
  render(
    <MantineProvider>
      <LayoutContext.Provider value={{ phone: false, titleRow: null }}>
        <LaunchPage onLaunched={onLaunched} />
      </LayoutContext.Provider>
    </MantineProvider>,
  );
  return onLaunched;
}

const pipeline = () => screen.getByRole("textbox", { name: /^Pipeline/ });
/** The Launch beside the form (the aside's); the page head has one too. */
const launch = () => screen.getAllByRole("button", { name: "Launch" }).at(-1)!;

async function load() {
  fetchMock.mockResolvedValueOnce(json(200, INSPECTED));
  await userEvent.type(pipeline(), "/data/pipeline");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText(/form from config\.schema\.yaml/);
}

test("a 422 on allow_unmounted shows the message with a checkbox that launches anyway", async () => {
  const onLaunched = page();
  await load();
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/shared/scratch/samples.csv");
  fetchMock.mockResolvedValueOnce(json(422, REFUSAL));
  await userEvent.click(launch());
  await screen.findByText(/May not be visible in the containers: \/shared\/scratch\/samples\.csv/);
  const checkbox = screen.getByRole("checkbox", {
    name: "Launch anyway: these paths are not visible in the containers",
  });
  expect(checkbox).toBeVisible();
  expect(JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body))).not.toHaveProperty("allow_unmounted");

  fetchMock.mockResolvedValueOnce(json(201, { id: "run_1", name: "pipeline-x", state: "queued" }));
  await userEvent.click(checkbox);
  await userEvent.click(launch());
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_1"));
  expect(JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body)).allow_unmounted).toBe(true);
  expect(screen.queryByText(/May not be visible in the containers/)).toBeNull();
});

test("a parameter edited after a refusal drops the Alert and the confirmation (CR-01)", async () => {
  const onLaunched = page();
  await load();
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/shared/scratch/samples.csv");
  fetchMock.mockResolvedValueOnce(json(422, REFUSAL));
  await userEvent.click(launch());
  const checkbox = await screen.findByRole("checkbox", { name: /Launch anyway/ });
  await userEvent.click(checkbox); // ticked: the next launch would send allow_unmounted

  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "x");
  expect(screen.queryByText(/May not be visible in the containers/)).toBeNull(); // the Alert is gone
  expect(screen.queryByRole("checkbox", { name: /Launch anyway/ })).toBeNull(); // so is the box

  fetchMock.mockResolvedValueOnce(json(201, { id: "run_1", name: "pipeline-x", state: "queued" }));
  await userEvent.click(launch());
  await waitFor(() => expect(onLaunched).toHaveBeenCalledWith("run_1"));
  expect(JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body))).not.toHaveProperty(
    "allow_unmounted",
  ); // unticked by the edit, the launch sends no confirmation
});

test("another field's refusal is not the container paths check", async () => {
  page();
  await load();
  await userEvent.type(screen.getByRole("textbox", { name: /^input/ }), "/data/samples.csv");
  fetchMock.mockResolvedValueOnce(
    json(422, {
      type: "/problems/validation-failed",
      status: 422,
      errors: [{ field: "params.input", message: "does not match the pattern" }],
    }),
  );
  await userEvent.click(launch());
  await waitFor(() => expect(screen.getByRole("textbox", { name: /^input/ })).toHaveAttribute("aria-invalid", "true"));
  expect(screen.queryByText(/May not be visible in the containers/)).toBeNull();
  expect(screen.queryByRole("checkbox", { name: /Launch anyway/ })).toBeNull();
});
