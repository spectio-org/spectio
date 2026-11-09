import { Button } from "@mantine/core";
import { Link, Navigate } from "@tanstack/react-router";
import { type ReactNode, createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { type ApiError, type ResultStat, type RunDetail, type TextRead, type WorkRoot, getRun, readResultText, resultUrl, statResult } from "../api";
import { ICONS, Icon } from "../icons";
import { usePageCrumb } from "../shell/crumb";
import { usePhone } from "../shell/layout";
import { CopyButton } from "./CopyMenu";
import { LogViewer } from "./LogViewer";
import {
  COLUMNS_MAX,
  IMAGE_MAX,
  KIB,
  type Kind,
  READ,
  ROWS_MAX,
  SHOWN_MAX,
  SVG_MAX,
  capLines,
  fileKind,
  hasLevels,
  jsonView,
  kindWord,
  parseTable,
  size,
  wholeLines,
} from "./preview";
import { isResultPath } from "./ReportViewer";
import { OFFLINE, OFFLINE_WHY, hasDotPart, join } from "./explorer";
import { BackToRun, Crumbs, type ResultsSearch, useTaskName } from "./ResultsBrowser";
import { NotFound } from "./RunDetailPage";
import { runName } from "./RunState";
import { isTerminal, when } from "./stateWord";

// The preview page of one results file (ui-spec §4.4.1, FU-P3-85c; boards LiteFilePreview,
// MLiteFilePreview, LiteFilePreviewStates; api §5.3): the `stat` route first (facts, kind, the
// caps, the path the server answered for), then the viewer of its kind. Text, table cells and
// formatted JSON are text nodes only; an image is an <img> of the raw route with `as=image`. The
// same page previews a file of a Nextflow attempt's work directory (`work`, FU-P3-85e): the viewers
// read it from the `workdir` routes (the Work context), and an HTML file is never opened.

/** The work directory the viewers read from; undefined for the run's results. */
const Work = createContext<WorkRoot | undefined>(undefined);

const parent = (path: string) => path.split("/").slice(0, -1).join("/");
const kib = (n: number) => `${Math.round(n / KIB)} KiB`;
const clock = (d: Date) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

/** A refusal in words (the States of ui-spec §4.4.1), with Retry when trying again may help. */
function Problem({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  const work = useContext(Work);
  const [title, body, retry]: [string, string | null, boolean] =
    error.status === 404
      ? ["This file is not there now", "It may have been moved or deleted since the folder was listed.", true]
      : error.status === 409
        ? ["The run's directory is not reachable", error.message, true]
        : error.status === 410
          ? ["The work directory was removed", null, false]
          : error.status === 422
            ? [notAFile(work), null, false]
            : error.status === 503
              ? [OFFLINE, OFFLINE_WHY, true]
              : ["The file could not be read", error.message, true];
  return <Note title={title} body={body} actions={retry ? <Button variant="default" size="xs" onClick={onRetry}>Retry</Button> : null} />;
}

const notAFile = (work?: WorkRoot) => (work ? "Not a file of this job's work directory." : "Not a file of this run's results.");

function Note({ title, body, actions }: { title: string; body?: string | null; actions?: ReactNode }) {
  return (
    <div className="sp-note sp-file-why" role="note">
      <strong>{title}</strong>
      {body && <span>{body}</span>}
      {actions && <div className="sp-actions">{actions}</div>}
    </div>
  );
}

function DownloadLink({ href, name, label = "Download" }: { href: string; name: string; label?: string }) {
  return (
    <Button component="a" variant="default" size="xs" href={href} download aria-label={`Download ${name}`} leftSection={<Icon path={ICONS.download} size={14} />}>
      {label}
    </Button>
  );
}

/** Text shown whole: at most 20,000 lines, each cut at 10,000 characters, in LogViewer. */
function Lines({ shown, label, levels, gutter, after, cap }: { shown: ReturnType<typeof capLines>; label: string; levels: boolean; gutter: boolean; after?: ReactNode; cap?: ReactNode }) {
  const phone = usePhone();
  const [wrap, setWrap] = useState(phone);
  const { lines, capped } = shown;
  return (
    <>
      <div className="sp-actions">
        <Button variant="default" size="xs" aria-pressed={wrap} onClick={() => setWrap(!wrap)}>
          Wrap lines
        </Button>
      </div>
      <LogViewer text={lines.map((l) => `${l}\n`).join("")} label={label} start="top" levels={levels} gutterFrom={gutter ? 1 : undefined} wrap={wrap} searchButton={phone} />
      {after}
      {cap ?? (capped && <p className="sp-file-cap">{LINES_CAP}</p>)}
    </>
  );
}

const LINES_CAP = "Showing the first 20,000 lines. Download to see the rest.";

type Read = { text: string; next: number | null };

/** The text viewer: whole up to 64 KiB; else Start (with Load more, to 1 MiB) or End. */
function TextView({ id, file, levels, note, retry }: { id: string; file: ResultStat; levels: boolean; note?: string; retry: () => void }) {
  const work = useContext(Work);
  const phone = usePhone();
  const total = file.size ?? 0;
  const whole = total <= READ;
  const [end, setEnd] = useState(false);
  const [read, setRead] = useState<Read | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const capLine = useRef<HTMLParagraphElement>(null);
  const moreRead = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    moreRead.current?.abort(); // a Load more still in flight belongs to the read this one replaces
    setRead(null);
    setError(null);
    const opts = whole || end ? { tail: READ } : { from: 0, to: READ - 1 };
    readResultText(id, file.path, opts, controller.signal, work)
      .then((r: TextRead) => setRead({ text: end && !whole ? wholeLines(r.text) : r.text, next: r.next }))
      .catch((e: ApiError) => controller.signal.aborted || setError(e));
    return () => controller.abort();
  }, [id, file, whole, end, work]);

  const next = read?.next ?? null;
  const capped = next !== null && next >= SHOWN_MAX && next < total;
  const shown = useMemo(() => capLines(read?.text ?? ""), [read]);
  const stopped = capped || shown.capped; // either cap ends Load more
  // focus moves to the line that says so only when a Load more reached it, not on the first read
  const stoppedByMore = stopped && !end && !whole && (next ?? 0) > READ;
  useEffect(() => {
    if (stoppedByMore) capLine.current?.focus();
  }, [stoppedByMore]);

  if (error?.status === 415) return <Binary id={id} file={file} />;
  if (error) return <Problem error={error} onRetry={retry} />;
  if (total === 0 || read?.text === "") return <Note title="This file is empty." />;
  if (!read) return <p className="sp-muted">Loading the file…</p>;

  const more = !end && !whole && next !== null && next < total && !capped && !shown.capped;
  const loadMore = () => {
    if (next === null || loading) return;
    const controller = new AbortController();
    moreRead.current = controller;
    setLoading(true);
    readResultText(id, file.path, { from: next, to: Math.min(next + READ, SHOWN_MAX) - 1 }, controller.signal, work)
      .then((r) => controller.signal.aborted || setRead((s) => ({ text: (s?.text ?? "") + r.text, next: r.next })))
      .catch((e: ApiError) => controller.signal.aborted || setError(e))
      .finally(() => moreRead.current === controller && setLoading(false));
  };
  const shownBytes = whole ? total : end ? READ : (next ?? 0);
  const pair = !whole && (
    <div className="sp-segments" role="group" aria-label="Read from">
      <button type="button" aria-pressed={!end} onClick={() => setEnd(false)}>
        Start
      </button>
      <button type="button" aria-pressed={end} onClick={() => setEnd(true)}>
        End
      </button>
    </div>
  );
  const pager = (
    <>
      {more && (
        <Button variant="default" className="sp-file-more" onClick={loadMore} aria-busy={loading}>
          Load more
        </Button>
      )}
      {!whole && !end && (
        <span className="sp-muted" aria-live="polite">
          {kib(shownBytes)} shown
        </span>
      )}
    </>
  );
  return (
    <div className="sp-file-viewer">
      {note && <p className="sp-muted">{note}</p>}
      <div className="sp-file-line">
        {!phone && pair}
        <span className="sp-muted">
          {whole ? `Whole file · ${size(total)}` : end ? `Last 64 KiB of ${size(total)}: line numbers not known` : shown.capped ? "Search covers the 20,000 lines shown" : `Search covers the ${kib(shownBytes)} shown`}
        </span>
      </div>
      <Lines
        shown={shown}
        label={`${file.name}, ${whole ? "whole file" : end ? "last 64 KiB" : "from the start"}`}
        levels={levels}
        gutter={!end}
        after={more && <span className="sp-muted sp-file-cut">… cut at {kib(next ?? 0)}</span>}
        cap={
          stopped && (
            <p ref={capLine} tabIndex={-1} className="sp-file-cap">
              {shown.capped ? LINES_CAP : `Showing the first 1 MiB of ${size(total)}. Download to see the rest.`}
            </p>
          )
        }
      />
      <div className="sp-file-pager">
        {pager}
        {phone && pair}
      </div>
    </div>
  );
}

function JsonView({ id, file, retry }: { id: string; file: ResultStat; retry: () => void }) {
  const work = useContext(Work);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [raw, setRaw] = useState(false);
  const big = (file.size ?? 0) > SHOWN_MAX;
  useEffect(() => {
    if (big) return;
    const controller = new AbortController();
    setText(null);
    setError(null);
    readResultText(id, file.path, { tail: SHOWN_MAX }, controller.signal, work)
      .then((r) => setText(r.text))
      .catch((e: ApiError) => controller.signal.aborted || setError(e));
    return () => controller.abort();
  }, [id, file, big, work]);
  if (big) return <TextView id={id} file={file} levels={false} note="Not shown formatted: larger than 1 MiB" retry={retry} />;
  if (error?.status === 415) return <Binary id={id} file={file} />;
  if (error) return <Problem error={error} onRetry={retry} />;
  if (text === null) return <p className="sp-muted">Loading the file…</p>;
  if (text === "") return <Note title="This file is empty." />;
  const view = jsonView(text);
  if ("fallback" in view) {
    return (
      <div className="sp-file-viewer">
        <p className="sp-muted">{view.fallback}</p>
        <Lines shown={capLines(text)} label={`${file.name}, whole file`} levels={false} gutter />
      </div>
    );
  }
  return (
    <div className="sp-file-viewer">
      <div className="sp-file-line">
        <Button variant="default" size="xs" aria-pressed={raw} onClick={() => setRaw(!raw)}>
          Show as text
        </Button>
        {!raw && <span className="sp-muted">Formatted view: large numbers and repeated keys may differ</span>}
      </div>
      <Lines key={String(raw)} shown={capLines(raw ? text : view.text)} label={`${file.name}, ${raw ? "whole file" : "formatted"}`} levels={false} gutter />
    </div>
  );
}

function TableView({ id, file, retry }: { id: string; file: ResultStat; retry: () => void }) {
  const work = useContext(Work);
  const [read, setRead] = useState<TextRead | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [header, setHeader] = useState(true);
  const [asText, setAsText] = useState(false);
  const empty = (file.size ?? 0) === 0;
  useEffect(() => {
    if (empty || asText) return;
    const controller = new AbortController();
    setRead(null);
    setError(null);
    readResultText(id, file.path, { from: 0, to: SHOWN_MAX - 1 }, controller.signal, work)
      .then(setRead)
      .catch((e: ApiError) => controller.signal.aborted || setError(e));
    return () => controller.abort();
  }, [id, file, empty, asText, work]);
  if (asText) return <TextView id={id} file={file} levels={false} retry={retry} />;
  if (empty || read?.text === "") return <Note title="This file is empty." />;
  if (error?.status === 415) return <Binary id={id} file={file} />;
  if (error) return <Problem error={error} onRetry={retry} />;
  if (!read) return <p className="sp-muted">Loading the file…</p>;

  const cut = read.next !== null && read.size !== null && read.next < read.size;
  const table = parseTable(read.text, /\.csv$/i.test(file.name) ? "csv" : "tsv", cut);
  const width = Math.max(0, ...table.rows.map((r) => r.length));
  const columns = Math.min(width, COLUMNS_MAX);
  const head = header ? table.rows[0] : undefined;
  const body = header ? table.rows.slice(1) : table.rows;
  const rows = body.slice(0, ROWS_MAX);
  const notes = [
    table.stopped || cut ? `Showing ${rows.length} of at least ${body.length} rows` : null,
    width > COLUMNS_MAX ? `Showing ${COLUMNS_MAX} of ${width} columns` : null,
  ].filter((n): n is string => n !== null);
  const cells = (row: string[]) => Array.from({ length: columns }, (_, i) => row[i] ?? "");
  return (
    <div className="sp-file-viewer">
      <div className="sp-file-line">
        <Button variant="default" size="xs" aria-pressed={header} onClick={() => setHeader(!header)}>
          First row is a header
        </Button>
        <Button variant="default" size="xs" onClick={() => setAsText(true)}>
          Show as text
        </Button>
      </div>
      {table.comments.length > 0 && <pre className="sp-file-comments">{table.comments.join("\n")}</pre>}
      <div className="sp-file-table" role="region" tabIndex={0} aria-label={`${file.name}, table`}>
        <table className="sp-table">
          <caption className="sp-muted">{[file.name, cut ? "read from the first 1 MiB" : null, ...notes].filter(Boolean).join(" · ")}</caption>
          <thead>
            <tr>
              {(head ? cells(head) : Array.from({ length: columns }, (_, i) => `Column ${i + 1}`)).map((c, i) => (
                <th key={i} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, r) => (
              <tr key={r}>
                {cells(row).map((c, i) => (
                  <td key={i}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {notes.map((n) => (
        <p key={n} className="sp-muted">
          {n}
        </p>
      ))}
    </div>
  );
}

function ImageView({ id, file }: { id: string; file: ResultStat }) {
  const work = useContext(Work);
  const [failed, setFailed] = useState(false);
  const [tries, setTries] = useState(0);
  const [natural, setNatural] = useState<string | null>(null);
  const [actual, setActual] = useState(false);
  const cap = /\.svg$/i.test(file.name) ? SVG_MAX : IMAGE_MAX;
  if (failed || (file.size ?? 0) > cap) {
    return (
      <Note
        title="This image could not be shown here. Download it to open it."
        actions={
          <>
            <Button variant="default" size="xs" onClick={() => (setFailed(false), setTries((t) => t + 1))}>
              Retry
            </Button>
            <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />
          </>
        }
      />
    );
  }
  const img = (
    <img
      key={tries}
      className="sp-file-image"
      data-actual={actual || undefined}
      src={resultUrl(id, file.path, { as: "image" }, work)}
      alt={file.name}
      onLoad={(e) => setNatural(`${e.currentTarget.naturalWidth} × ${e.currentTarget.naturalHeight} px`)}
      onError={() => setFailed(true)}
    />
  );
  return (
    <div className="sp-file-viewer">
      <div className="sp-actions">
        <Button variant="default" size="xs" aria-pressed={actual} onClick={() => setActual(!actual)}>
          Actual size
        </Button>
      </div>
      <div className="sp-file-backdrop">
        {actual ? (
          <div className="sp-file-scroll" role="region" tabIndex={0} aria-label={`${file.name}, image`}>
            {img}
          </div>
        ) : (
          img
        )}
        {natural && <span className="sp-file-natural">{natural}</span>}
      </div>
    </div>
  );
}

function Binary({ id, file }: { id: string; file: ResultStat }) {
  const work = useContext(Work);
  return <Note title="This file is not text. Download it to open it." actions={<DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />} />;
}

function Viewer({ id, file, kind, retry }: { id: string; file: ResultStat; kind: Kind; retry: () => void }) {
  const work = useContext(Work);
  const download = <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />;
  switch (kind) {
    case "binary":
      return <Binary id={id} file={file} />;
    case "pdf":
      return <Note title="Spectio does not open PDF files. Download it to open it." actions={download} />;
    case "html":
      return work ? (
        <Note title="Spectio does not open HTML from a work directory. Download it to open it." actions={download} />
      ) : (
        <Note
          title="An HTML report opens in Spectio's report viewer."
          actions={
            <Link to="/runs/$id/report" params={{ id }} search={{ path: file.path }}>
              Open it in the report viewer
            </Link>
          }
        />
      );
    case "image":
      return <ImageView id={id} file={file} />;
    case "json":
      return <JsonView id={id} file={file} retry={retry} />;
    case "table":
      return <TableView id={id} file={file} retry={retry} />;
    default:
      return <TextView id={id} file={file} levels={hasLevels(file.name)} retry={retry} />;
  }
}

/** `/runs/$id/results/file?path=<file>`, with the folder's `sort` and `q` it returns to, or the
 * `task` and `attempt` of the sheet a Preview of its Outputs came from. */
export function FilePreview({ id, search, work }: { id: string; search: ResultsSearch; work?: WorkRoot }) {
  const path = search.path ?? "";
  const [run, setRun] = useState<RunDetail | null>(null);
  const [missing, setMissing] = useState(false);
  const [file, setFile] = useState<ResultStat | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [reads, setReads] = useState(0);
  const [readAt, setReadAt] = useState<Date | null>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const valid = isResultPath(path) && !(work && hasDotPart(path));
  const taskName = useTaskName(id, work);

  useEffect(() => {
    const controller = new AbortController();
    getRun(id, controller.signal)
      .then(setRun)
      .catch((e: ApiError) => controller.signal.aborted || (e.status === 404 && setMissing(true)));
    return () => controller.abort();
  }, [id]);
  useEffect(() => {
    if (!valid) return;
    const controller = new AbortController();
    setError(null);
    statResult(id, path, controller.signal, work)
      .then((found) => {
        setFile(found);
        setReadAt(new Date());
      })
      .catch((e: ApiError) => controller.signal.aborted || (setFile(null), setError(e)));
    return () => controller.abort();
  }, [id, path, valid, reads, work?.task, work?.attempt]);

  const loaded = file !== null;
  useEffect(() => {
    if (loaded) title.current?.focus();
  }, [loaded]);

  const name = run ? runName(run) : null;
  // the name the server answered for once known, else the URL's last part (a path that passed
  // isResultPath); a refused path is never shown (SEC-P3T32B-02)
  const fileName = file?.name ?? (valid ? path.split("/").pop()! : null);
  usePageCrumb(name);
  useEffect(() => {
    if (name && !work) document.title = `${fileName ?? "File preview"} · ${name} · Spectio`;
    else if (name && taskName) document.title = `${fileName ?? "File preview"} · ${taskName} · ${name} · Spectio`;
  }, [name, fileName, taskName, work]);

  if (missing) return <NotFound />;
  const { sort, q, task, attempt } = search;
  if (file?.type === "dir" && work) return <Navigate to="/runs/$id/workdir" params={{ id }} search={{ path: file.path, sort, q, task, attempt }} replace />;
  if (file?.type === "dir") return <Navigate to="/runs/$id/results" params={{ id }} search={{ path: file.path, sort, q, task, attempt }} replace />;

  const retry = () => setReads((r) => r + 1);
  const shown = file?.path ?? "";
  const folder = parent(shown);
  const parts = shown ? shown.split("/") : [];
  const where = file ? join(file.root, file.path) : null;
  const ended = run ? isTerminal(run.state) : true;
  const kind = file ? fileKind(file.name) : null;
  return (
    <Work.Provider value={work}>
      <div className="sp-runs sp-file-page">
        {work ? (
          <Link className="sp-report-back" to="/runs/$id/workdir" params={{ id }} search={{ path: folder || undefined, sort, q, focus: file?.name, task, attempt }}>
            <Icon path={ICONS.chevronLeft} size={14} /> {file ? folder.split("/").pop() || "work directory" : "Work directory"}
          </Link>
        ) : task && attempt ? (
          <BackToRun id={id} run={run} task={task} attempt={attempt} />
        ) : (
          <Link className="sp-report-back" to="/runs/$id/results" params={{ id }} search={{ path: folder || undefined, sort, q, focus: file?.name }}>
            <Icon path={ICONS.chevronLeft} size={14} /> {file ? folder.split("/").pop() || "results" : "Results"}
          </Link>
        )}
        <h1 ref={title} tabIndex={-1} className="sp-page-title sp-file-name">
          {fileName ?? "File preview"}
        </h1>
        {file && kind && (
          <div className="sp-file-facts">
            <span>
              {[kindWord(file.type === "link_outside" ? "link" : kind, !!work), file.size === null ? null : size(file.size), file.mtime ? `modified ${when(file.mtime)}` : null, !ended && readAt ? `read at ${clock(readAt)}` : null]
                .filter(Boolean)
                .join(" · ")}
            </span>
            {!ended && (
              <Button variant="default" size="xs" leftSection={<Icon path={ICONS.reload} size={14} />} onClick={retry}>
                Reload
              </Button>
            )}
          </div>
        )}
        {file && !ended && <p className="sp-muted">The view does not follow the file on its own: Reload reads it again.</p>}
        {file && where && (
          <div className="sp-pathbar">
            <Crumbs id={id} parts={parts} work={work} />
            <span className="sp-copy-line">
              <span className="sp-mono">{where}</span>
              <CopyButton text={where} label="Copy path" name="Copy path" />
              {file.type === "file" && <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />}
            </span>
          </div>
        )}
        {!valid ? (
          <Note title={notAFile(work)} />
        ) : error ? (
          <Problem error={error} onRetry={retry} />
        ) : !file || !kind ? (
          <p className="sp-muted">Loading the file…</p>
        ) : file.type === "link_outside" ? (
          <Note title={work ? "A link outside the run: not followed." : "A link outside the results directory: not followed."} />
        ) : (
          <Viewer id={id} file={file} kind={kind} retry={retry} />
        )}
      </div>
    </Work.Provider>
  );
}
