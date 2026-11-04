// The Summary's "Results and reports" section and the results browser (P1 Task 32 part two;
// ui-spec §4.4 run tools note; boards LiteRunDetail and LiteResults; api §5, Task 31's routes).
import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const ROOT = "/g/demo-lab/rnaseq/2026-10-25";
const T = "2026-10-31T09:02:00+00:00";

const LISTING = {
  root: ROOT,
  path: "",
  exists: true,
  entries: [
    { name: "fastqc", type: "dir", size: null, mtime: T },
    { name: "multiqc", type: "dir", size: null, mtime: T },
    { name: "pipeline_info", type: "dir", size: null, mtime: T },
    { name: "notes.txt", type: "file", size: 84, mtime: T },
  ],
  truncated: false,
  reports: [
    { path: "multiqc/multiqc_report.html", title: "MultiQC report", group: "multiqc" },
    { path: "fastqc/S01_fastqc.html", title: "S01_fastqc", group: "fastqc" },
    { path: "fastqc/S02_fastqc.html", title: "S02_fastqc", group: "fastqc" },
    { path: "pipeline_info/execution_report.html", title: "execution_report", group: "pipeline_info" },
  ],
};

function detail(over: Record<string, unknown> = {}, results: unknown = LISTING) {
  return serve({
    [`${URL_}/processes`]: { items: [] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/logs`]: () => new Response(""),
    [`${URL_}/results`]: results,
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }), results_dir: ROOT, ...over },
  });
}

const section = () => screen.findByRole("region", { name: "Results and reports" });

test("the section shows the results directory with Copy, the reports MultiQC first, and the folders", async () => {
  detail();
  app(`/runs/${ID}`);
  const results = await section();
  expect(within(results).getByText(ROOT)).toBeInTheDocument();
  expect(within(results).getByRole("button", { name: "Copy the results directory" })).toBeInTheDocument();
  const multiqc = await within(results).findByRole("link", { name: "Open the MultiQC report" });
  expect(multiqc.getAttribute("href")).toBe(`/runs/${ID}/report?path=${encodeURIComponent("multiqc/multiqc_report.html")}`);
  const links = within(results).getAllByRole("link").map((a) => a.getAttribute("aria-label") ?? a.textContent);
  expect(links.indexOf("Open the MultiQC report")).toBe(0);
  // two reports in one folder are a group: a link to the folder in the results browser
  expect(within(results).getByRole("link", { name: "Browse the 2 reports in fastqc/" }).getAttribute("href")).toBe(
    `/runs/${ID}/results?path=fastqc`,
  );
  expect(within(results).getByRole("link", { name: "Open the report execution_report" })).toBeInTheDocument();
  expect(within(results).getByRole("link", { name: /^Browse pipeline_info\/, modified / })).toBeInTheDocument();
  expect(within(results).getByRole("link", { name: "Browse all results" }).getAttribute("href")).toBe(`/runs/${ID}/results`);
});

test("the sandbox note does not promise working reports: MultiQC's scripts stop there (CR-P3T32B-02)", async () => {
  detail();
  app(`/runs/${ID}`);
  const results = await section();
  await within(results).findByRole("link", { name: "Open the MultiQC report" });
  expect(within(results).queryByText(/their scripts run/)).toBeNull();
  expect(
    within(results).getByText(
      "Reports open in Spectio's sandboxed report viewer, where they cannot reach Spectio. MultiQC's scripts stop there: its tables show, its plots and toolbox do not. To see all of a report you trust, use Download in the viewer: the report then runs outside Spectio's sandbox.",
    ),
  ).toBeInTheDocument();
});

test("with no MultiQC report listed, the note says nothing of MultiQC or Download (CR-P3T32B-04, SEC-P3T32B-04)", async () => {
  detail({}, { ...LISTING, reports: LISTING.reports.filter((r) => !r.path.endsWith("multiqc_report.html")) });
  app(`/runs/${ID}`);
  const results = await section();
  await within(results).findByRole("link", { name: "Open the report execution_report" });
  expect(within(results).getByText("Reports open in Spectio's sandboxed report viewer, where they cannot reach Spectio.")).toBeInTheDocument();
  expect(within(results).queryByText(/MultiQC's scripts/)).toBeNull();
  expect(within(results).queryByText(/Download/)).toBeNull();
});

test("a failed nf-core run with no MultiQC report says so; a running one says it comes at the end", async () => {
  detail({ state: "failed" }, { ...LISTING, reports: [] });
  app(`/runs/${ID}`);
  expect(await within(await section()).findByText("No MultiQC report: the run failed before it")).toBeInTheDocument();
});

test("a running nf-core run: MultiQC is written at the end of the run", async () => {
  detail({ state: "running" }, { ...LISTING, reports: [] });
  app(`/runs/${ID}`);
  const results = await section();
  expect(await within(results).findByText("written at the end of the run")).toBeInTheDocument();
});

test("a results directory that does not exist yet says so", async () => {
  detail({ state: "running" }, { ...LISTING, exists: false, entries: [], reports: [] });
  app(`/runs/${ID}`);
  expect(await within(await section()).findByText("The results directory does not exist yet")).toBeInTheDocument();
});

test("no results directory to show: the word for an outdir Spectio refuses or none (CR-P3T31-09 r3)", async () => {
  const mock = detail({ results_dir: null });
  app(`/runs/${ID}`);
  const results = await section();
  expect(results).toHaveTextContent(
    "No results directory to show: the run sets no outdir, or one Spectio does not show (one that holds the runs or your home directory, a hidden or engine folder, or a path with ..).",
  );
  expect(fetched(mock).some((u) => u.includes("/results"))).toBe(false);
});

test("a run started from a terminal has no Results section", async () => {
  detail({ origin: "cli-observed" });
  app(`/runs/${ID}`);
  await screen.findByRole("heading", { level: 1 });
  expect(screen.queryByRole("region", { name: "Results and reports" })).toBeNull();
});

test("the results browser shows one folder: path bar, Copy path, and each kind of entry", async () => {
  const mock = serve({
    [`${URL_}/results`]: {
      ...LISTING,
      path: "fastqc",
      entries: [
        { name: "zips", type: "dir", size: null, mtime: T },
        { name: "S01_fastqc.html", type: "file", size: 626688, mtime: T },
        { name: "versions.yml", type: "file", size: 84, mtime: T },
        { name: "latest", type: "link_outside", size: null, mtime: T },
      ],
    },
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }), results_dir: ROOT },
  });
  app(`/runs/${ID}/results?path=fastqc`);
  expect(await screen.findByRole("heading", { level: 1, name: "Results" })).toBeInTheDocument();
  expect(fetched(mock)).toContain(`${URL_}/results?path=fastqc`);
  const bar = screen.getByRole("navigation", { name: "Folder" });
  expect(within(bar).getByRole("link", { name: "results" }).getAttribute("href")).toBe(`/runs/${ID}/results`);
  expect(within(bar).getByText("fastqc")).toHaveAttribute("aria-current", "page");
  expect(screen.getByText(`${ROOT}/fastqc`)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy path" })).toBeInTheDocument();
  const table = screen.getByRole("table", { name: "fastqc" });
  expect(within(table).getByRole("link", { name: "zips" }).getAttribute("href")).toBe(`/runs/${ID}/results?path=${encodeURIComponent("fastqc/zips")}`);
  expect(within(table).getByRole("link", { name: "S01_fastqc.html" }).getAttribute("href")).toBe(
    `/runs/${ID}/report?path=${encodeURIComponent("fastqc/S01_fastqc.html")}`,
  );
  const file = within(table).getByRole("link", { name: "versions.yml" });
  expect(file.getAttribute("href")).toBe(`${URL_}/results/raw/fastqc/versions.yml?download=true`);
  expect(within(table).queryByRole("link", { name: "latest" })).toBeNull();
  expect(within(table).getByText("link outside the results directory")).toBeInTheDocument();
  expect(within(table).getByText("612 KB")).toBeInTheDocument();
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByText("Results")).toHaveAttribute("aria-current", "page");
});

test("the results browser says when a folder is cut at 1,000 entries, or missing", async () => {
  serve({
    [`${URL_}/results?path=big`]: { ...LISTING, path: "big", truncated: true },
    [`${URL_}/results?path=gone`]: () => json(404, { title: "Not found", detail: "no such folder" }),
    [URL_]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  const router = app(`/runs/${ID}/results?path=big`);
  expect(await screen.findByText("Showing the first 1,000 entries of this folder")).toBeInTheDocument();
  await router.navigate({ to: "/runs/$id/results", params: { id: ID }, search: { path: "gone" } });
  await waitFor(() => expect(screen.getByText("No such folder in this run's results.")).toBeInTheDocument());
});

test("a folder the server does not confirm is not shown in the path bar (SEC-P3T32B-02)", async () => {
  const text = "Session expired, call 555 1234";
  serve({
    [`${URL_}/results`]: () => json(404, { title: "Not found", detail: "no such folder" }),
    [URL_]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  app(`/runs/${ID}/results?path=${encodeURIComponent(text)}`);
  expect(await screen.findByText("No such folder in this run's results.")).toBeInTheDocument();
  expect(screen.queryByText(text)).toBeNull();
  expect(screen.queryByText(new RegExp(text))).toBeNull();
});

test.each(["a\u202eb", "a\u200fb", "a\u2066b"])("a path with a bidi or format character is not asked for (SEC-P3T32B-02): %j", async (path) => {
  const mock = serve({ [URL_]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT } });
  app(`/runs/${ID}/results?path=${encodeURIComponent(path)}`);
  expect(await screen.findByText("Not a folder of this run's results.")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.includes("/results"))).toBe(false);
});

test("a path with a dot part or an empty part is not asked for (SEC-P3T31-10 r4)", async () => {
  const mock = serve({ [URL_]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT } });
  app(`/runs/${ID}/results?path=${encodeURIComponent("a/../b")}`);
  expect(await screen.findByText("Not a folder of this run's results.")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.includes("/results"))).toBe(false);
});

test("Back from the browser goes to the run's Summary", async () => {
  serve({ [`${URL_}/results`]: LISTING, [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }), results_dir: ROOT } });
  app(`/runs/${ID}/results`);
  const back = await screen.findByRole("link", { name: /rnaseq-2026-10-25 · Summary/ });
  expect(back.getAttribute("href")).toBe(`/runs/${ID}`);
  const folder = within(screen.getByRole("table", { name: "results" })).getByRole("link", { name: "fastqc" });
  expect(folder.getAttribute("href")).toBe(`/runs/${ID}/results?path=fastqc`);
});
