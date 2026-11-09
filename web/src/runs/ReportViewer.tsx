import { Button } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { type ApiError, type RunDetail, getRun, resultUrl } from "../api";
import { ICONS, Icon } from "../icons";
import { usePageCrumb } from "../shell/crumb";
import type { Sort } from "./explorer";
import { resultsSearch } from "./ResultsBrowser";
import { NotFound } from "./RunDetailPage";
import { runName } from "./RunState";

// The report viewer (P1 Task 31; board LiteReportViewer): one HTML report of a run's results in an
// iframe sandboxed twice, by its `sandbox` attribute and by the CSP the API serves it with (dev-env
// §15.3 req. 14): scripts run, but in an opaque origin that cannot call the API, open a window or
// move this page. The banner says the report is the pipeline's, not Spectio's.

const MULTIQC = "multiqc_report.html";

/** `/runs/$id/report?path=<results path>`; opened from the results browser, `&from=results` and
 * the browser's `sort` and `q`, which its back link returns with (ui-spec §4.4.1, HTML report). */
export function reportSearch(search: Record<string, unknown>): { path?: string; from?: "results"; sort?: Sort; q?: string } {
  const path = typeof search.path === "string" && search.path !== "" ? { path: search.path } : {};
  if (search.from !== "results") return path;
  const { sort, q } = resultsSearch(search);
  return { ...path, from: "results", ...(sort ? { sort } : {}), ...(q ? { q } : {}) };
}

/** A report's title, as the listing gives it (`files.results._report`). */
export function reportTitle(path: string): string {
  const name = path.split("/").pop() ?? path;
  return name.endsWith(MULTIQC) ? "MultiQC report" : name.replace(/\.[^.]*$/, "");
}

/** The bidi and other format controls, line and paragraph separators the server refuses in a
 * path: exactly `FORMAT_CHARS` of `spectio_server/files/redact.py`, which a pytest compares with
 * this text (SEC-P3T32B-05, FU-P3-37). */
export const FORMAT_CHARS = "\\u061c\\u200b-\\u200f\\u2028-\\u202e\\u2060-\\u206f\\ufeff\\ufff9-\\ufffb";
const UNSAFE = new RegExp(`[\\u0000-\\u001f\\u007f-\\u009f${FORMAT_CHARS}]`);

/** Text with no control, bidi or format character: what a URL may put in a field or a message. */
export const isPlainText = (text: string): boolean => !UNSAFE.test(text);

/** A path below the results root as the API names one: relative, with no empty, `.` or `..`
 * part, no control character and no bidi or format character. Anything else is never asked for,
 * nor shown (SEC-P3T31-10 r4, SEC-P3G4-02, SEC-P3T32B-02, SEC-P3T32B-05). */
export const isResultPath = (path: string): boolean =>
  isPlainText(path) && path.split("/").every((part) => part !== "" && part !== "." && part !== "..");

const isReport = (path: string) => isResultPath(path) && /\.html?$/i.test(path);

export function ReportViewer({ id, path, from, sort, q }: { id: string } & ReturnType<typeof reportSearch>) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getRun(id, controller.signal)
      .then(setRun)
      .catch((e: ApiError) => controller.signal.aborted || (e.status === 404 ? setMissing(true) : setError(e.message)));
    return () => controller.abort();
  }, [id]);

  const name = run ? runName(run) : null;
  const title = path && isReport(path) ? reportTitle(path) : "No such report";
  usePageCrumb(name);
  useEffect(() => {
    if (name) document.title = `${title} · ${name} · Spectio`;
  }, [name, title]);

  if (missing) return <NotFound />;
  if (!run) {
    return (
      <div className="sp-runs">
        {error ? <p role="alert">The run could not be read: {error}</p> : <p className="sp-muted">Loading the run…</p>}
      </div>
    );
  }
  // opened from the results browser: back to the file's folder, its row in focus (ui-spec §4.4.1)
  const parts = from && path && isReport(path) ? path.split("/") : null;
  const folder = parts ? parts.slice(0, -1) : [];
  const back = parts ? (
    <Link className="sp-report-back" to="/runs/$id/results" params={{ id }} search={{ path: folder.join("/") || undefined, sort, q, focus: parts[parts.length - 1] }}>
      <Icon path={ICONS.chevronLeft} size={14} /> {folder[folder.length - 1] ?? "results"}
    </Link>
  ) : (
    <Link className="sp-report-back" to="/runs/$id" params={{ id }}>
      <Icon path={ICONS.chevronLeft} size={14} /> {name} · Summary
    </Link>
  );
  if (!path || !isReport(path)) {
    return (
      <div className="sp-runs">
        {back}
        <h1 className="sp-page-title">{title}</h1>
        <p>Only an HTML file of the run's results opens here.</p>
      </div>
    );
  }
  return (
    <div className="sp-runs sp-report">
      {back}
      <h1 className="sp-page-title">{title}</h1>
      {parts && (
        <nav className="sp-pathbar" aria-label="Folder">
          <ol>
            {["results", ...parts].map((part, i) => (
              <li key={i}>
                {i < parts.length ? (
                  <Link to="/runs/$id/results" params={{ id }} search={{ path: parts.slice(0, i).join("/") || undefined, sort }}>
                    {part}
                  </Link>
                ) : (
                  <span aria-current="page">{part}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="sp-report-banner">
        <Icon path={ICONS.shield} size={20} />
        <div>
          <p>
            Untrusted report: <code>{path}</code>
          </p>
          <p className="sp-muted">Written by the pipeline. It runs in a sandbox and cannot reach Spectio. Spectio never asks you to paste a link.</p>
        </div>
        <Button component="a" href={resultUrl(id, path, { download: true })} variant="default" leftSection={<Icon path={ICONS.download} size={16} />}>
          Download
        </Button>
      </div>
      <iframe
        className="sp-report-frame"
        title={`${title} of ${name}, sandboxed`}
        sandbox="allow-scripts allow-downloads"
        referrerPolicy="no-referrer"
        src={resultUrl(id, path)}
      />
      <p className="sp-muted">Report blank? Some reports need what the sandbox blocks. Download it and open it on your computer.</p>
    </div>
  );
}
