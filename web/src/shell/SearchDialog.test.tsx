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

// run() ended or started 2026-10-31 07:40 UTC; one hour later reads "1 h ago" (ui-spec §12.8)
beforeEach(() => {
  viewport(1440);
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-31T08:41:00+00:00"));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
const RNA_RUN = "Run rnaseq-a, Running, Nextflow, 1 h ago";

async function openByButton() {
  const opener = await screen.findByRole("button", { name: "Search runs, pipelines and pages" });
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
  await screen.findByRole("button", { name: "Search runs, pipelines and pages" });
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
  expect(within(runs).getByRole("button", { name: RNA_RUN })).toBeInTheDocument();
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
  const hit = await within(dialog).findByRole("button", { name: "Run wgs-12, Running, Nextflow, 1 h ago" });
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
  expect(within(dialog).getByText("No run, pipeline or page matches “zzz”.")).toBeInTheDocument();
});

test("UI-06: a spotlight panel, no close button, an Esc hint, and a prompt before typing", async () => {
  backend();
  app("/environments");
  const { dialog } = await openByButton();
  expect(within(dialog).queryByRole("button", { name: /close/i })).toBeNull();
  expect(within(dialog).getByText("Esc")).toBeInTheDocument();
  expect(within(dialog).getByText("Type a run name or ID, a pipeline or a page.")).toBeInTheDocument();
});

test("UI-06: a run row shows its state tile and word, engine mark and time; the active row follows the arrows", async () => {
  backend();
  app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "rna");
  const runRow = await within(dialog).findByRole("button", { name: RNA_RUN });
  expect(runRow.querySelector(".sp-search-tile")).toHaveAttribute("data-tone", "running");
  expect(within(runRow).getByText("Running")).toBeInTheDocument();
  expect(within(runRow).getByText("1 h ago")).toBeInTheDocument();
  expect(runRow.querySelector("img.sp-engine-mark")).not.toBeNull();
  const pipeRow = within(dialog).getByRole("button", { name: "Pipeline RNA-seq, /g/p/rnaseq" });
  // Enter on the input opens the first row: it is the active one until the arrows move
  expect(runRow).toHaveAttribute("data-active");
  await userEvent.keyboard("{ArrowDown}{ArrowDown}");
  expect(pipeRow).toHaveFocus();
  expect(pipeRow).toHaveAttribute("data-active");
  expect(runRow).not.toHaveAttribute("data-active");
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

test("on a 360 px phone the search icon still shows and opens the dialog (CR-P3FU89-01)", async () => {
  viewport(360);
  backend();
  app("/environments");
  const { opener, dialog } = await openByButton();
  // sp-narrow-hide hides a control below 390 px (shell.css); a phone has no ⌘K, so search keeps its icon
  expect(opener).not.toHaveClass("sp-narrow-hide");
  expect(dialog).toHaveAttribute("data-full-screen", "true");
});

test("FU-P3-116: the short ID the UI shows (last 6 of the run ID) finds its run, in any case", async () => {
  const other = run({ id: "run_01JBC6Q4ZK7M8N2P3R5SD80950", name: "sarek-b" });
  backend({ "/api/v1/runs?limit=200": { items: [run(), other], next: null } });
  app("/environments");
  const { dialog } = await openByButton();
  await userEvent.type(within(dialog).getByRole("searchbox"), "d80950");
  const runs = await within(dialog).findByRole("region", { name: "Runs" });
  expect(within(runs).getAllByRole("button").map((b) => b.getAttribute("aria-label"))).toEqual(["Run sarek-b, Running, Nextflow, 1 h ago"]);
  expect(within(dialog).getByRole("status")).toHaveTextContent("1 result");
});
