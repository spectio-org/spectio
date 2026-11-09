// The results explorer (ui-spec §4.4.1, Explorer; FU-P3-85d; boards LiteResults, MLiteResults):
// one card with the counts and the filter, Kind badges, a file opening its preview, the Download
// icon button, sort with aria-sort, the view in the URL, the way back to a row, the phone rows.
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const ROOT = "/g/demo-lab/rnaseq/2026-10-25";
const T1 = "2026-10-31T08:00:00+00:00";
const T2 = "2026-10-31T09:00:00+00:00";

const FASTQC = {
  root: ROOT,
  path: "fastqc",
  exists: true,
  truncated: false,
  reports: [],
  entries: [
    { name: "versions.yml", type: "file", size: 84, mtime: T2 },
    { name: "zips", type: "dir", size: null, mtime: T1 },
    { name: "S01_fastqc.html", type: "file", size: 626688, mtime: T1 },
    { name: "README", type: "file", size: 2048, mtime: T1 },
    { name: "latest", type: "link_outside", size: null, mtime: T1 },
  ],
};

function results(listing: unknown = FASTQC, over: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}/results`]: listing,
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }), results_dir: ROOT, ...over },
  });
}

/** A link's search as an object. */
const query = (a: HTMLElement) => Object.fromEntries(new URL(a.getAttribute("href")!, "http://x").searchParams);
const table = () => screen.findByRole("table", { name: "fastqc" });
/** The explorer card's polite region (the path bar's Copy path has its own). */
const live = () => within(screen.getByRole("region", { name: /^Results · / })).getByRole("status");
const rowNames = (t: HTMLElement) => within(t).getAllByRole("rowheader").map((th) => th.textContent);

test("one card: the counts, Kind badges, a file opening its preview, the Download icon button", async () => {
  results();
  app(`/runs/${ID}/results?path=fastqc`);
  expect(await screen.findByRole("heading", { level: 2, name: "Results · 1 folder, 4 files" })).toBeInTheDocument();
  const t = await table();
  const kinds = within(t).getAllByRole("row").slice(1).map((r) => r.querySelector("[data-kind]")?.textContent);
  expect(kinds).toEqual(["Folder", "Link outside", "File", "HTML report", "Text"]);
  for (const badge of t.querySelectorAll("[data-kind]")) expect(badge.querySelector("svg")).not.toBeNull(); // never colour alone
  const file = within(t).getByRole("link", { name: "versions.yml" });
  expect(new URL(file.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}/results/file`);
  expect(query(file)).toEqual({ path: "fastqc/versions.yml" });
  const report = within(t).getByRole("link", { name: "S01_fastqc.html" });
  expect(new URL(report.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}/report`);
  expect(query(report)).toEqual({ path: "fastqc/S01_fastqc.html", from: "results" });
  expect(query(within(t).getByRole("link", { name: "zips" }))).toEqual({ path: "fastqc/zips" });
  // Download on each file row, named after it; none on a folder or a link outside
  const download = within(t).getByRole("link", { name: "Download versions.yml" });
  expect(download.getAttribute("href")).toBe(`${URL_}/results/raw/fastqc/versions.yml?download=true`);
  expect(download).toHaveAttribute("download");
  expect(within(t).getAllByRole("link", { name: /^Download / })).toHaveLength(3);
  expect(within(t).queryByRole("link", { name: "latest" })).toBeNull();
  expect(within(t).getByText("not followed")).toBeInTheDocument();
  expect(within(t).getByText("612 KiB")).toBeInTheDocument();
});

test("sort: header buttons with aria-sort, folders first, a second press reverses, &sort= with a history replace", async () => {
  results();
  const router = app(`/runs/${ID}/results?path=fastqc`);
  const t = await table();
  const header = (name: string) => within(t).getByRole("button", { name }).closest("th")!;
  expect(header("Name")).toHaveAttribute("aria-sort", "ascending");
  expect(header("Size")).not.toHaveAttribute("aria-sort");
  expect(rowNames(t)).toEqual(["zips", "latest not followed", "README", "S01_fastqc.html", "versions.yml"]);
  const before = router.history.length;
  await userEvent.click(within(t).getByRole("button", { name: "Size" }));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ path: "fastqc", sort: "size" }));
  expect(header("Size")).toHaveAttribute("aria-sort", "ascending");
  expect(header("Name")).not.toHaveAttribute("aria-sort");
  expect(rowNames(t)).toEqual(["zips", "versions.yml", "README", "S01_fastqc.html", "latest not followed"]);
  await userEvent.click(within(t).getByRole("button", { name: "Size" }));
  await waitFor(() => expect(header("Size")).toHaveAttribute("aria-sort", "descending"));
  expect(router.state.location.search).toMatchObject({ sort: "-size" });
  expect(rowNames(t)).toEqual(["zips", "S01_fastqc.html", "README", "versions.yml", "latest not followed"]);
  expect(router.history.length).toBe(before);
  // the links keep the sort: a folder, and a file's preview (which returns with it)
  expect(query(within(t).getByRole("link", { name: "zips" }))).toEqual({ path: "fastqc/zips", sort: "-size" });
  expect(query(within(t).getByRole("link", { name: "versions.yml" }))).toEqual({ path: "fastqc/versions.yml", sort: "-size" });
});

test("filter: rows go at once, the polite region says 'n of m shown' 150 ms later, &q= with a history replace", async () => {
  results();
  const router = app(`/runs/${ID}/results?path=fastqc`);
  const t = await table();
  const before = router.history.length;
  const field = screen.getByRole("searchbox", { name: "Filter this folder" });
  await userEvent.type(field, "YML");
  expect(rowNames(t)).toEqual(["versions.yml"]);
  const status = live();
  await waitFor(() => expect(status).toHaveTextContent("1 of 5 shown"));
  await waitFor(() => expect(router.state.location.search).toMatchObject({ path: "fastqc", q: "YML" }));
  expect(router.history.length).toBe(before);
  expect(query(within(t).getByRole("link", { name: "versions.yml" }))).toEqual({ path: "fastqc/versions.yml", q: "YML" });
});

test("the live region waits until typing stops for 150 ms", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  try {
    results();
    app(`/runs/${ID}/results?path=fastqc`);
    await table();
    const field = screen.getByRole("searchbox", { name: "Filter this folder" });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await user.type(field, "z");
    const status = live();
    act(() => vi.advanceTimersByTime(100));
    expect(status).toHaveTextContent("");
    act(() => vi.advanceTimersByTime(60));
    expect(status).toHaveTextContent("1 of 5 shown");
  } finally {
    vi.useRealTimers();
  }
});

test("no match: the line names the filter, Clear empties it and the URL", async () => {
  results();
  const router = app(`/runs/${ID}/results?path=fastqc&q=S03`);
  await screen.findByRole("heading", { level: 2, name: "Results · 1 folder, 4 files" });
  const field = screen.getByRole("searchbox", { name: "Filter this folder" });
  expect(field).toHaveValue("S03");
  expect(screen.getByText("No entry in this folder matches 'S03'")).toBeInTheDocument();
  expect(screen.queryByRole("table", { name: "fastqc" })).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Clear" }));
  expect(field).toHaveValue("");
  expect(field).toHaveFocus();
  expect(rowNames(await table())).toHaveLength(5);
  await waitFor(() => expect(router.state.location.search).not.toHaveProperty("q"));
});

test("back from a preview with &focus=: the row is scrolled into view and its link takes focus", async () => {
  const scrolled = vi.fn();
  Element.prototype.scrollIntoView = scrolled;
  results();
  app(`/runs/${ID}/results?path=fastqc&sort=-size&focus=README`);
  const t = await table();
  const link = within(t).getByRole("link", { name: "README" });
  await waitFor(() => expect(link).toHaveFocus());
  expect(scrolled).toHaveBeenCalled();
  expect(scrolled.mock.contexts[0]).toBe(link.closest("tr"));
});

test("more than 1,000 entries: the line says sort and filter see only those, with the path to open on the cluster", async () => {
  results({ ...FASTQC, truncated: true });
  app(`/runs/${ID}/results?path=fastqc`);
  expect(
    await screen.findByText("This folder has more than 1,000 entries. Spectio lists 1,000 of them, in no particular order; sort and filter see only those."),
  ).toBeInTheDocument();
  expect(screen.getAllByText(`${ROOT}/fastqc`).length).toBeGreaterThan(1);
});

test("phone: one link per row, 'Kind · size · modified' under the name, a Sort by select, Download in the preview only", async () => {
  viewport(390);
  results();
  const router = app(`/runs/${ID}/results?path=fastqc`);
  const list = await screen.findByRole("list", { name: "fastqc" });
  const links = within(list).getAllByRole("link");
  expect(links.map((a) => a.querySelector("[data-name]")?.textContent)).toEqual(["zips", "README", "S01_fastqc.html", "versions.yml"]);
  expect(within(list).getByRole("link", { name: /^versions\.yml/ })).toHaveTextContent(/Text · 84 B · /);
  expect(within(list).queryByRole("link", { name: /^Download/ })).toBeNull();
  expect(within(list).getByText("latest")).toBeInTheDocument();
  expect(screen.queryByRole("table")).toBeNull();
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Sort by" }), "-mtime");
  await waitFor(() => expect(router.state.location.search).toMatchObject({ sort: "-mtime" }));
  expect(within(list).getAllByRole("link").map((a) => a.querySelector("[data-name]")?.textContent)).toEqual(["zips", "versions.yml", "README", "S01_fastqc.html"]);
});

test("a folder opened from the task sheet's Outputs goes back to the sheet", async () => {
  results({ ...FASTQC, path: "counts" }, { workflow: { engine: "snakemake", engine_version: "9.5.1", location: "/g/x", name: null, version: null } });
  app(`/runs/${ID}/results?path=counts&task=tsk_19&attempt=2`);
  const back = await screen.findByRole("link", { name: /rnaseq-2026-10-25 · job, attempt 2/ });
  expect(new URL(back.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}`);
  expect(query(back)).toEqual({ task: "tsk_19", attempt: "2" });
});
