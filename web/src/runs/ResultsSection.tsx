import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { ApiError, ResultReport, Results, RunDetail } from "../api";
import { listResults } from "../api";
import { Icon } from "../icons";
import { FoldSection } from "../shell/FoldSection";
import { CopyButton } from "./CopyMenu";
import { when } from "./stateWord";

// The Summary's "Results and reports" (P1 Task 32 part two; ui-spec §4.4 run tools note; board
// LiteRunDetail): the results directory with Copy, the reports found below it, MultiQC first, and
// the top folders, each a link into the results browser (LiteResults). Read from
// `GET /runs/{id}/results` when the run changes state.

const MULTIQC = "multiqc_report.html";

/** The reports as rows: MultiQC's, then one row per folder of two or more reports (a link to that
 * folder in the browser), and every other report alone. */
function reportRows(reports: ResultReport[]) {
  const groups = new Map<string, ResultReport[]>();
  for (const r of reports) if (r.group && !r.path.endsWith(MULTIQC)) groups.set(r.group, [...(groups.get(r.group) ?? []), r]);
  const rows: ({ kind: "report"; report: ResultReport } | { kind: "group"; group: string; n: number })[] = [];
  const seen = new Set<string>();
  for (const r of reports) {
    const group = r.group && !r.path.endsWith(MULTIQC) ? groups.get(r.group)! : null;
    if (!group || group.length === 1) rows.push({ kind: "report", report: r });
    else if (!seen.has(r.group!)) {
      seen.add(r.group!);
      rows.push({ kind: "group", group: r.group!, n: group.length });
    }
  }
  return rows;
}

/** Where MultiQC's report stands while none is found: only for an nf-core pipeline, which writes
 * one at its end (ui-spec §4.4 run tools note). */
function multiqcMissing(run: RunDetail): string | null {
  if (!run.workflow.name?.startsWith("nf-core/")) return null;
  if (run.state === "failed") return "No MultiQC report: the run failed before it";
  if (run.state === "queued" || run.state === "running") return "written at the end of the run";
  return null;
}

function Contents({ run, results }: { run: RunDetail; results: Results }) {
  if (!results.exists) {
    return (
      <div className="sp-results-state">
        <strong>The results directory does not exist yet</strong>
        <span className="sp-muted">The pipeline creates it when its first results are published. Spectio checks again when the run changes state.</span>
      </div>
    );
  }
  const rows = reportRows(results.reports);
  const multiqc = results.reports.some((r) => r.path.endsWith(MULTIQC));
  const missing = multiqc ? null : multiqcMissing(run);
  const folders = results.entries.filter((e) => e.type === "dir");
  return (
    <>
      <h3 className="sp-results-h">Reports</h3>
      <ul className="sp-results-list">
        {missing && (
          <li>
            <span className="sp-results-what">
              <span>MultiQC report</span>
              <span className="sp-muted">{missing}</span>
            </span>
          </li>
        )}
        {rows.map((row) =>
          row.kind === "report" ? (
            <li key={row.report.path}>
              <span className="sp-results-what">
                <span>{row.report.title}</span>
                <span className="sp-muted sp-mono">{row.report.path}</span>
              </span>
              <Link
                to="/runs/$id/report"
                params={{ id: run.id }}
                search={{ path: row.report.path }}
                aria-label={row.report.path.endsWith(MULTIQC) ? "Open the MultiQC report" : `Open the report ${row.report.title}`}
              >
                Open
              </Link>
            </li>
          ) : (
            <li key={row.group}>
              <span className="sp-results-what">
                <span>{row.group} reports</span>
                <span className="sp-muted">{row.n} HTML files</span>
              </span>
              <Link
                to="/runs/$id/results"
                params={{ id: run.id }}
                search={{ path: row.group }}
                aria-label={`Browse the ${row.n} reports in ${row.group}/`}
              >
                Browse {row.group}/
              </Link>
            </li>
          ),
        )}
        {!missing && rows.length === 0 && <li className="sp-muted">No HTML report found yet.</li>}
      </ul>
      {folders.length > 0 && (
        <>
          <h3 className="sp-results-h">Folders</h3>
          <ul className="sp-results-list">
            {folders.map((f) => (
              <li key={f.name}>
                <Link
                  to="/runs/$id/results"
                  params={{ id: run.id }}
                  search={{ path: f.name }}
                  aria-label={`Browse ${f.name}/, modified ${when(f.mtime)}`}
                  className="sp-mono"
                >
                  {f.name}/
                </Link>
                <span className="sp-muted">modified {when(f.mtime)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <Link to="/runs/$id/results" params={{ id: run.id }} className="sp-results-all">
        Browse all results <Icon name="arrowRight" />
      </Link>
      <p className="sp-muted">
        Reports open in Spectio's sandboxed report viewer, where they cannot reach Spectio.
        {multiqc &&
          " MultiQC's scripts stop there: its tables show, its plots and toolbox do not. To see all of a report you trust, use Download in the viewer: the report then runs outside Spectio's sandbox."}
      </p>
    </>
  );
}

export function ResultsSection({ run }: { run: RunDetail }) {
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  const root = run.results_dir;
  useEffect(() => {
    if (!root) return;
    const controller = new AbortController();
    listResults(run.id, "", controller.signal)
      .then((found) => {
        setResults(found);
        setError(null);
      })
      .catch((e: ApiError) => controller.signal.aborted || setError(e.message));
    return () => controller.abort();
  }, [run.id, root, run.state]);

  const from = run.workflow.engine === "snakemake" ? "Results directory: the launch directory." : "Results directory, from --outdir.";
  return (
    <FoldSection id="results" screen="run" icon="folder" title="Results and reports" card>
      {!root ? (
        <p className="sp-muted">
          No results directory to show: the run sets no outdir, or one Spectio does not show (one that holds the runs or your home
          directory, a hidden or engine folder, or a path with ..).
        </p>
      ) : (
        <div className="sp-results">
          <span className="sp-muted">{from} Read-only.</span>
          <span className="sp-copy-line">
            <span className="sp-mono">{root}</span>
            <CopyButton text={root} label="Copy" name="Copy the results directory" />
          </span>
          {error ? <p role="alert">The results could not be read: {error}</p> : results ? <Contents run={run} results={results} /> : <p className="sp-muted">Loading the results…</p>}
        </div>
      )}
    </FoldSection>
  );
}
