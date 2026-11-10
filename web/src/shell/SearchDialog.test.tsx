// Search in 0.0.1 (FU-P3-89; ui-spec top bar note): a modal dialog over what the API already
// serves (GET /runs?q=, GET /runs/{id}, GET /catalog) and the app's pages, no GET /search yet.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, viewport } from "../testing";

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const RNA = { name: "rnaseq", label: "RNA-seq", engine: "nextflow", location: "/g/p/rnaseq", revision: null, profile: null, params_file: null, etag: "e1" };
const CATALOG = { items: [RNA], file: { path: "/home/amartin/.spectio/catalog.toml", state: "ok", detail: null } };

function backend(over: Record<string, unknown> = {}) {
  return serve({
    "/api/v1/runs?q=": (url: URL) => json(200, { items: (url.searchParams.get("q") ?? "").startsWith("rna") ? [run()] : [], next_cursor: null }),
    "/api/v1/runs": { items: [], next_cursor: null },
    "/api/v1/catalog": CATALOG,
    ...over,
  });
}

beforeEach(() => viewport(1440));
afterEach(() => vi.unstubAllGlobals());

async function openByButton() {
  const opener = await screen.findByRole("button", { name: "Search" });
  await userEvent.click(opener);
  return { opener, dialog: await screen.findByRole("dialog", { name: "Search" }) };
}

test("the top-bar button opens a modal dialog with a labelled input; Escape closes it and focus returns", async () => {
  backend();
  app("/environments");
  const { opener, dialog } = await openByButton();
  expect(dialog).toHaveAttribute("aria-modal", "true");
  const input = within(dialog).getByRole("searchbox", { name: "Search runs, pipelines and pages" });
  await waitFor(() => expect(input).toHaveFocus());
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(opener).toHaveFocus());
});

test("Ctrl+K and ⌘K open the dialog", async () => {
  backend();
  app("/environments");
  await screen.findByRole("button", { name: "Search" });
  await userEvent.keyboard("{Control>}k{/Control}");
  expect(await screen.findByRole("dialog", { name: "Search" })).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await userEvent.keyboard("{Meta>}k{/Meta}");
  expect(await screen.findByRole("dialog", { name: "Search" })).toBeInTheDocument();
});

test("results are grouped under Runs, Pipelines and Pages, after one debounced request", async () => {
  const mock = backend();
  app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "rna");
  const runs = await within(dialog).findByRole("region", { name: "Runs" });
  expect(within(runs).getByRole("button", { name: `Run rnaseq-a, ${ID}` })).toBeInTheDocument();
  const pipelines = within(dialog).getByRole("region", { name: "Pipelines" });
  expect(within(pipelines).getByRole("button", { name: "Pipeline RNA-seq, /g/p/rnaseq" })).toBeInTheDocument();
  expect(within(dialog).queryByRole("region", { name: "Pages" })).toBeNull();
  expect(within(dialog).getByRole("status")).toHaveTextContent("2 results");
  // typed in under 150 ms: one request for "rna", none for "r" or "rn"
  expect(fetched(mock).filter((u) => u.includes("q="))).toEqual(["/api/v1/runs?q=rna&limit=5"]);
});

test("a page matches by name; arrow keys move through the results and Enter opens one", async () => {
  backend();
  const router = app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "la");
  const pages = await within(dialog).findByRole("region", { name: "Pages" });
  const launch = within(pages).getByRole("button", { name: "Page Launch" });
  expect(within(dialog).getByRole("status")).toHaveTextContent("1 result");
  await userEvent.keyboard("{ArrowDown}");
  expect(launch).toHaveFocus();
  await userEvent.keyboard("{ArrowUp}");
  expect(within(dialog).getByRole("searchbox")).toHaveFocus();
  await userEvent.keyboard("{ArrowDown}{Enter}");
  await waitFor(() => expect(router.state.location.pathname).toBe("/launch"));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

test("a run ID is looked up exactly with GET /runs/{id}", async () => {
  const mock = backend({ [`/api/v1/runs/${ID}`]: { ...DETAIL, ...run({ name: "wgs-12" }) } });
  const router = app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), ID);
  const hit = await within(dialog).findByRole("button", { name: `Run wgs-12, ${ID}` });
  expect(fetched(mock)).toContain(`/api/v1/runs/${ID}`);
  await userEvent.click(hit);
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${ID}`));
});

test("nothing found says No match", async () => {
  backend();
  app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "zzz");
  await waitFor(() => expect(within(dialog).getByRole("status")).toHaveTextContent("No match"));
});

test("a failed request shows an error line", async () => {
  backend({ "/api/v1/runs?q=": () => json(500, { title: "Server error", detail: "database locked" }) });
  app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "rna");
  expect(await within(dialog).findByText("Search failed: database locked")).toBeInTheDocument();
  // the catalog still answered
  expect(within(dialog).getByRole("button", { name: "Pipeline RNA-seq, /g/p/rnaseq" })).toBeInTheDocument();
});

test("on the phone the search icon opens the same dialog, full screen", async () => {
  viewport(390);
  backend();
  app("/environments");
  const { dialog } = await openByButton();
  expect(dialog).toHaveAttribute("data-full-screen", "true");
});
