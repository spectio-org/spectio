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
