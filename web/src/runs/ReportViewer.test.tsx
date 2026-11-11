// The report viewer (P1 Task 31; board LiteReportViewer; dev-env §15.3 req. 14): a pipeline's HTML
// report in a sandboxed iframe, under a banner that says it is untrusted.
import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const PATH = "multiqc/star_salmon/multiqc_report.html";
const detail = () => ({ ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }), params: {}, failures: [], failures_total: 0 });

test("a report opens sandboxed, under the untrusted banner, with Download", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent(PATH)}`);
  expect(await screen.findByRole("heading", { level: 1, name: "MultiQC report" })).toBeInTheDocument();
  expect(screen.getByText(PATH)).toBeInTheDocument();
  expect(screen.getByText(/runs in a sandbox and cannot reach Spectio/)).toBeInTheDocument();
  const frame = screen.getByTitle("MultiQC report of rnaseq-2026-10-25, sandboxed");
  expect(frame.getAttribute("sandbox")).toBe("allow-scripts allow-downloads");
  expect(frame.getAttribute("referrerpolicy")).toBe("no-referrer");
  expect(frame.getAttribute("src")).toBe(`${URL_}/results/raw/multiqc/star_salmon/multiqc_report.html`);
  const download = screen.getByRole("link", { name: /Download/ });
  expect(download.getAttribute("href")).toBe(`${URL_}/results/raw/multiqc/star_salmon/multiqc_report.html?download=true`);
  expect(screen.getByRole("link", { name: /rnaseq-2026-10-25/ }).getAttribute("href")).toBe(`/runs/${ID}`);
  expect(screen.getByText(/Report blank\?/)).toBeInTheDocument();
  expect(getComputedStyle(screen.getByRole("link", { name: "Show the source as text" })).color).toBe("var(--sp-text-link)"); // FU-P3-104
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(await within(crumbs).findByText("rnaseq-2026-10-25")).toBeInTheDocument();
  expect(within(crumbs).getByText("Report").getAttribute("aria-current")).toBe("page");
});

test("another report is titled by its file name, each path part encoded", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent("qc/a b#1.htm")}`);
  expect(await screen.findByRole("heading", { level: 1, name: "a b#1" })).toBeInTheDocument();
  expect(screen.getByTitle(/sandboxed/).getAttribute("src")).toBe(`${URL_}/results/raw/qc/a%20b%231.htm`);
});

test("no report path, or not an HTML file, frames nothing", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent("data/counts.tsv")}`);
  expect(await screen.findByRole("heading", { level: 1, name: "No such report" })).toBeInTheDocument();
  expect(screen.queryByTitle(/sandboxed/)).toBeNull();
});

test("an unknown run is not found", async () => {
  serve({ [URL_]: () => json(404, { title: "Not found", detail: "no such run" }) });
  app(`/runs/${ID}/report?path=${encodeURIComponent(PATH)}`);
  expect(await screen.findByRole("heading", { level: 1, name: "No such run" })).toBeInTheDocument();
  expect(screen.queryByTitle(/sandboxed/)).toBeNull();
});

test.each(["a/../b.html", "./b.html", "a//b.html", "/etc/b.html", "a\u202eb.html", "a\u200eb.html", "a\u2069b.html", "a\u061cb.html", "a\u200bb.html", "a\u2028b.html", "a\ufeffb.html"])("a path with a dot or empty part frames nothing, nor one with a bidi or format character (SEC-P3T31-10 r4, SEC-P3T32B-02): %s", async (path) => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent(path)}`);
  expect(await screen.findByRole("heading", { level: 1, name: "No such report" })).toBeInTheDocument();
  expect(screen.queryByTitle(/sandboxed/)).toBeNull();
  expect(screen.queryByText(path)).toBeNull();
});

test("opened from the results browser: back to the file's folder with its sort, filter and row; the folder path ends with the file (FU-P3-85d)", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent(PATH)}&from=results&sort=-mtime&q=multi`);
  await screen.findByRole("heading", { level: 1, name: "MultiQC report" });
  const back = screen.getAllByRole("link", { name: "star_salmon" })[0]; // the back link, then the folder path
  const url = new URL(back.getAttribute("href")!, "http://x");
  expect(url.pathname).toBe(`/runs/${ID}/results`);
  expect(Object.fromEntries(url.searchParams)).toEqual({ path: "multiqc/star_salmon", sort: "-mtime", q: "multi", focus: "multiqc_report.html" });
  expect(screen.queryByRole("link", { name: /Summary/ })).toBeNull();
  const bar = screen.getByRole("navigation", { name: "Folder" });
  expect(within(bar).getAllByRole("link").map((a) => a.textContent)).toEqual(["results", "multiqc", "star_salmon"]);
  expect(within(bar).getByRole("link", { name: "multiqc" }).getAttribute("href")).toBe(`/runs/${ID}/results?path=multiqc&sort=-mtime`);
  expect(within(bar).getByText("multiqc_report.html")).toHaveAttribute("aria-current", "page");
});

test("a report at the results root opened from the browser goes back to the root", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=report.html&from=results`);
  await screen.findByRole("heading", { level: 1, name: "report" });
  const back = screen.getAllByRole("link", { name: "results" })[0];
  expect(back.getAttribute("href")).toBe(`/runs/${ID}/results?focus=report.html`);
});

test("opened from the Summary there is no folder path", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent(PATH)}`);
  await screen.findByRole("heading", { level: 1, name: "MultiQC report" });
  expect(screen.queryByRole("navigation", { name: "Folder" })).toBeNull();
});

test("the page head (ui-spec §12.5, UI-17): tile and h1 in one header, the run named in the subtitle", async () => {
  serve({ [URL_]: detail() });
  app(`/runs/${ID}/report?path=${encodeURIComponent(PATH)}`);
  const head = (await screen.findByRole("heading", { level: 1, name: "MultiQC report" })).closest("header")!;
  expect(head).toHaveClass("sp-head");
  expect(head.querySelector(".sp-head-tile")).not.toBeNull();
  expect(within(head).getByRole("link", { name: /rnaseq-2026-10-25 · Summary/ })).toBeInTheDocument();
  expect(within(head).getByRole("link", { name: /Download/ })).toBeInTheDocument();
});
