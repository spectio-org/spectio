import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { type ApiError, type ResultEntry, type Results, type RunDetail, getRun, listResults, resultUrl } from "../api";
import { ICONS, Icon } from "../icons";
import { usePageCrumb } from "../shell/crumb";
import { CopyButton } from "./CopyMenu";
import { isResultPath } from "./ReportViewer";
import { bytes } from "./resources";
import { NotFound } from "./RunDetailPage";
import { runName } from "./RunState";
import { when } from "./stateWord";

// The results browser (P1 Task 32 part two; ui-spec §4.4 run tools note; board LiteResults): one
// folder of a run's results at a time, read only, under a path bar of links back up, with Copy
// path. A folder opens here, an HTML file in the report viewer, any other file downloads; a link
// that leaves the results directory is not followed.

/** `/runs/$id/results?path=<folder>`; no path is the results root. */
export function resultsSearch(search: Record<string, unknown>): { path?: string } {
  return typeof search.path === "string" && search.path !== "" ? { path: search.path } : {};
}

const TYPES: Record<ResultEntry["type"], string> = { dir: "folder", file: "file", link_outside: "link outside the results directory" };
const isHtml = (name: string) => /\.html?$/i.test(name);
const join = (folder: string, name: string) => (folder ? `${folder}/${name}` : name);

function Entry({ id, folder, entry }: { id: string; folder: string; entry: ResultEntry }) {
  const path = join(folder, entry.name);
  if (entry.type === "dir") {
    return (
      <Link to="/runs/$id/results" params={{ id }} search={{ path }}>
        {entry.name}
      </Link>
    );
  }
  if (entry.type === "link_outside") {
    return (
      <>
        {entry.name} <span className="sp-muted">not followed</span>
      </>
    );
  }
  return isHtml(entry.name) ? (
    <>
      <Link to="/runs/$id/report" params={{ id }} search={{ path }}>
        {entry.name}
      </Link>{" "}
      <span className="sp-muted">opens in the report viewer</span>
    </>
  ) : (
    <>
      <a href={resultUrl(id, path, { download: true })} download>
        {entry.name}
      </a>{" "}
      <span className="sp-muted">downloads</span>
    </>
  );
}

function Listing({ id, folder, results }: { id: string; folder: string; results: Results }) {
  if (!results.exists) {
    return (
      <div className="sp-results-state">
        <strong>The results directory does not exist yet</strong>
        <span className="sp-muted">The pipeline creates it when its first results are published. Spectio checks again when you reload.</span>
      </div>
    );
  }
  const label = folder.split("/").pop() || "results";
  return (
    <>
      {results.truncated && (
        <div className="sp-results-state">
          <strong>Showing the first 1,000 entries of this folder</strong>
          <span className="sp-muted">
            This folder has more. Open it on the cluster to see them all: <span className="sp-mono">{join(results.root, folder)}</span>
          </span>
        </div>
      )}
      <div className="sp-table-wrap">
        <table className="sp-table" aria-label={label}>
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Type</th>
              <th scope="col" className="sp-num">Size</th>
              <th scope="col">Modified</th>
            </tr>
          </thead>
          <tbody>
            {results.entries.map((entry) => (
              <tr key={entry.name}>
                <td>
                  <span className="sp-result-name">
                    <Icon path={entry.type === "dir" ? ICONS.folder : ICONS.file} size={15} />
                    <span>
                      <Entry id={id} folder={folder} entry={entry} />
                    </span>
                  </span>
                </td>
                <td>{entry.type === "file" && isHtml(entry.name) ? "HTML report" : TYPES[entry.type]}</td>
                <td className="sp-num">{entry.type === "file" ? bytes(entry.size) : "—"}</td>
                <td>{when(entry.mtime)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {results.entries.length === 0 && <p className="sp-muted">This folder is empty.</p>}
      <p className="sp-muted">Read-only. A folder's size is not counted. An HTML file opens in Spectio's report viewer; any other file downloads.</p>
    </>
  );
}

export function ResultsBrowser({ id, path = "" }: { id: string; path?: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [missing, setMissing] = useState(false);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  const valid = path === "" || isResultPath(path);
  useEffect(() => {
    const controller = new AbortController();
    getRun(id, controller.signal)
      .then(setRun)
      .catch((e: ApiError) => controller.signal.aborted || (e.status === 404 ? setMissing(true) : setError(e.message)));
    return () => controller.abort();
  }, [id]);
  useEffect(() => {
    setResults(null);
    setError(null);
    if (!valid) return;
    const controller = new AbortController();
    listResults(id, path, controller.signal)
      .then(setResults)
      .catch((e: ApiError) => {
        if (controller.signal.aborted) return;
        setError(e.status === 404 && path ? "No such folder in this run's results." : e.status === 422 ? "Not a folder of this run's results." : e.message);
      });
    return () => controller.abort();
  }, [id, path, valid]);

  const name = run ? runName(run) : null;
  usePageCrumb(name);
  useEffect(() => {
    if (name) document.title = `Results · ${name} · Spectio`;
  }, [name]);

  if (missing) return <NotFound />;
  const parts = valid && path ? path.split("/") : [];
  const where = results && valid ? join(results.root, path) : null;
  return (
    <div className="sp-runs">
      <Link className="sp-report-back" to="/runs/$id" params={{ id }}>
        <Icon path={ICONS.chevronLeft} size={14} /> {name ?? "Run"} · Summary
      </Link>
      <h1 className="sp-page-title">Results</h1>
      <div className="sp-pathbar">
        <nav aria-label="Folder">
          <ol>
            <li>
              {parts.length ? (
                <Link to="/runs/$id/results" params={{ id }}>
                  results
                </Link>
              ) : (
                <span aria-current="page">results</span>
              )}
            </li>
            {parts.map((part, i) => (
              <li key={i}>
                {i < parts.length - 1 ? (
                  <Link to="/runs/$id/results" params={{ id }} search={{ path: parts.slice(0, i + 1).join("/") }}>
                    {part}
                  </Link>
                ) : (
                  <span aria-current="page">{part}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
        {where && (
          <span className="sp-copy-line">
            <span className="sp-mono">{where}</span>
            <CopyButton text={where} label="Copy path" name="Copy path" />
          </span>
        )}
      </div>
      {!valid ? (
        <p role="alert">Not a folder of this run's results.</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : results ? (
        <Listing id={id} folder={path} results={results} />
      ) : (
        <p className="sp-muted">Loading the folder…</p>
      )}
    </div>
  );
}
