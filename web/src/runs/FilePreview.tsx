import { Button } from "@mantine/core";
import { Link, Navigate } from "@tanstack/react-router";
import { type ReactNode, Suspense, createContext, lazy, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
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
  REPORT_MAX,
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
import { type Flat, type ImageState, imageState, readFlat } from "./imaging/flat";
import { DecoderPool } from "./imaging/pool";
import { OFFLINE, OFFLINE_WHY, hasDotPart, join } from "./explorer";
import { BackToRun, Crumbs, type ResultsSearch, useTaskName } from "./ResultsBrowser";
import { NotFound } from "./RunDetailPage";
import { compareText } from "./gridText";
import type GridOf from "./DataGrid";
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

// AG Grid is its own chunk, loaded with the first table (ui-spec §4.13).
const DataGrid = lazy(() => import("./DataGrid")) as unknown as typeof GridOf;
/** Up to this many rows the table grows to them; past it, a fixed height scrolls them virtually. */
const SHORT = 15;

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
      <p className="sp-muted">{[file.name, cut ? "read from the first 1 MiB" : null, ...notes].filter(Boolean).join(" · ")}</p>
      <div className="sp-file-table" role="region" aria-label={`${file.name}, table`} data-scroll={rows.length > SHORT ? "" : undefined}>
        <Suspense fallback={<p className="sp-muted">Loading the table…</p>}>
          <DataGrid<string[]>
            key={String(header)}
            label={file.name}
            rowData={rows}
            domLayout={rows.length > SHORT ? "normal" : "autoHeight"}
            defaultColDef={{ flex: 1, minWidth: 120 }}
            columnDefs={Array.from({ length: columns }, (_, i) => ({
              colId: String(i),
              headerName: head ? (head[i] ?? "") : `Column ${i + 1}`,
              valueGetter: ({ data }) => data?.[i] ?? "",
              comparator: compareText,
              filter: "agTextColumnFilter",
              floatingFilter: true,
              suppressFloatingFilterButton: true,
              suppressHeaderMenuButton: true,
              suppressHeaderFilterButton: true,
            }))}
          />
        </Suspense>
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

const px = (w: number, h: number) => `${w.toLocaleString("en-US")} × ${h.toLocaleString("en-US")}`;

/** A TIFF, or an OME-TIFF's first plane on a phone or without WebGL 2: the flat view on a 2D canvas (ui-spec
 * §4.4.1, imaging), read through the pinned client and our decoder pool, or the state that stopped it. */
function TiffView({ id, file, ome }: { id: string; file: ResultStat; ome: boolean }) {
  const work = useContext(Work);
  const phone = usePhone();
  const [tries, setTries] = useState(0);
  const [flat, setFlat] = useState<Flat | null>(null);
  const [state, setState] = useState<ImageState | { problem: ApiError } | "phone" | null>(null);
  const [actual, setActual] = useState(false);
  const empty = (file.size ?? 0) === 0;
  useEffect(() => {
    if (empty) return;
    const controller = new AbortController();
    const pool = new DecoderPool();
    setFlat(null);
    setState(null);
    readFlat(resultUrl(id, file.path, { as: "tiff" }, work), file.size ?? 0, file.name, ome, phone, pool, controller.signal)
      .then((read) => controller.signal.aborted || (read ? setFlat(read) : setState("phone")))
      .catch((err) => controller.signal.aborted || setState(imageState(err)));
    return () => (controller.abort(), pool.destroy());
  }, [id, file, ome, phone, work, tries, empty]);
  const paint = useCallback(
    (canvas: HTMLCanvasElement | null) => {
      const context = flat && canvas?.getContext("2d");
      if (!flat || !canvas || !context) return;
      [canvas.width, canvas.height] = [flat.width, flat.height];
      const image = context.createImageData(flat.width, flat.height);
      image.data.set(flat.rgba);
      context.putImageData(image, 0, 0);
    },
    [flat],
  );

  const retry = () => setTries((t) => t + 1);
  const download = <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />;
  const copyLink = <CopyButton text={window.location.href} label="Copy link" name="Copy link" />;
  if (empty) return <Note title="This file is empty." actions={download} />;
  if (state === "phone") return <Note title="This image is too large to show on a phone." actions={<>{copyLink}{download}</>} />;
  if (state) return <ImageStateView state={state} retry={retry} download={download} />;
  if (!flat) return <p className="sp-muted">Loading the image…</p>;

  const asOme = ome && !flat.noOme;
  const [W, H] = flat.full;
  const facts = [
    phone ? `Shown: ${asOme ? "channel 1, first plane, " : ""}${px(flat.width, flat.height)} of ${px(W, H)} px` : `${px(W, H)} px`,
    !phone && asOme ? "Shown: channel 1, first plane" : null,
    !asOme && flat.pages > 1 ? `Shown: page 1 of ${flat.pages}` : null,
    flat.note,
    flat.stretched ? "Contrast stretched for display" : null,
  ];
  const canvas = <canvas ref={paint} className="sp-file-image" data-actual={actual || undefined} role="img" aria-label={file.name} />;
  return (
    <div className="sp-file-viewer">
      {flat.noOme && <p className="sp-muted">This file has no OME metadata: shown as a TIFF.</p>}
      <div className="sp-actions">
        <Button variant="default" size="xs" aria-pressed={actual} onClick={() => setActual(!actual)}>
          Actual size
        </Button>
      </div>
      <div className="sp-file-backdrop">
        {actual ? (
          <div className="sp-file-scroll" role="region" tabIndex={0} aria-label={`${file.name}, image`}>
            {canvas}
          </div>
        ) : (
          canvas
        )}
        <span className="sp-file-natural">{facts.filter(Boolean).join(" · ")}</span>
      </div>
      {phone && (
        <div className="sp-file-line">
          <span>
            <strong>Open on a larger screen</strong> to see every channel, plane and time point: the viewer needs 768 px and WebGL 2.
          </span>
          {copyLink}
        </div>
      )}
    </div>
  );
}

/** A problem before the first tile is drawn, in the viewer's place (flat view and WebGL viewer). */
function ImageStateView({ state, retry, download }: { state: ImageState | { problem: ApiError }; retry: () => void; download: ReactNode }) {
  if ("problem" in state) return <Problem error={state.problem} onRetry={retry} />;
  const again = state.action && (
    <Button variant="default" size="xs" onClick={retry}>
      {state.action === "retry" ? "Retry" : "Reload"}
    </Button>
  );
  if (state.status) return <div className="sp-file-line"><span role="status">{state.title}</span>{again}</div>;
  return <Note title={state.title} actions={(again || state.download) && <>{again}{state.download && download}</>} />;
}

// the WebGL viewer, with Viv and deck.gl: a lazy chunk, out of the main bundle
const OmeView = lazy(() => import("./imaging/OmeView"));
// probed once per page, and the probe's context lost at once: it would count against the
// browser's context limit, which evicts the oldest context, the live viewer's (req. 19 WebGL)
let webgl2: boolean | undefined;
export const hasWebgl2 = () => {
  if (webgl2 === undefined) {
    try {
      const gl = document.createElement("canvas").getContext("webgl2");
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
      webgl2 = !!gl;
    } catch {
      webgl2 = false;
    }
  }
  return webgl2;
};

/** An OME-TIFF: the WebGL viewer on a desktop or tablet with WebGL 2, else the flat view. */
function OmeTiffView({ id, file }: { id: string; file: ResultStat }) {
  const work = useContext(Work);
  const phone = usePhone();
  const webgl = hasWebgl2();
  const flat = <TiffView id={id} file={file} ome />;
  if (phone || !webgl || (file.size ?? 0) === 0) return flat;
  const download = <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />;
  return (
    <Suspense fallback={<p className="sp-muted">Loading the image…</p>}>
      <OmeView
        key={file.path}
        url={resultUrl(id, file.path, { as: "tiff" }, work)}
        size={file.size ?? 0}
        name={file.name}
        fallback={flat}
        stateView={(state, retry) => <ImageStateView state={state} retry={retry} download={download} />}
      />
    </Suspense>
  );
}

/** An OME-Zarr folder: the WebGL viewer reading its keys through our store, with Browse folder
 * where a file has Download. On a phone or without WebGL 2, a note: the flat Zarr view is not built yet. */
function OmeZarrView({ id, file }: { id: string; file: ResultStat }) {
  const work = useContext(Work);
  const phone = usePhone();
  const zarr = useCallback((key: string) => resultUrl(id, `${file.path}/${key}`, { as: "zarr" }, work), [id, file.path, work]);
  const browse = work ? (
    <Link to="/runs/$id/workdir" params={{ id }} search={{ path: file.path, task: work.task, attempt: work.attempt }}>Browse folder</Link>
  ) : (
    <Link to="/runs/$id/results" params={{ id }} search={{ path: file.path }}>Browse folder</Link>
  );
  if (phone) return <Note title="Open on a larger screen: Spectio shows an OME-Zarr in the image viewer only." actions={browse} />;
  if (!hasWebgl2()) return <Note title="This browser cannot open the image viewer: it needs WebGL 2, which is off or missing." actions={browse} />;
  return (
    <Suspense fallback={<p className="sp-muted">Loading the image…</p>}>
      <OmeView key={file.path} url="" size={0} zarr={zarr} workdir={!!work} name={file.name} fallback={<Note title="This browser cannot open the image viewer: it needs WebGL 2, which is off or missing." actions={browse} />} stateView={(state, retry) => <ImageStateView state={state} retry={retry} download={browse} />} />
    </Suspense>
  );
}

function Binary({ id, file }: { id: string; file: ResultStat }) {
  const work = useContext(Work);
  return <Note title="This file is not text. Download it to open it." actions={<DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />} />;
}

function Viewer({ id, file, kind, retry, search }: { id: string; file: ResultStat; kind: Kind; retry: () => void; search: ResultsSearch }) {
  const work = useContext(Work);
  const download = <DownloadLink href={resultUrl(id, file.path, { download: true }, work)} name={file.name} />;
  switch (kind) {
    case "binary":
      return <Binary id={id} file={file} />;
    case "pdf":
      return <Note title="Spectio does not open PDF files. Download it to open it." actions={download} />;
    case "html": {
      if (work) return <Note title="Spectio does not open HTML from a work directory. Download it to open it." actions={download} />;
      const { sort, q, task, attempt } = search;
      if (search.view === "text") return <TextView id={id} file={file} levels={false} retry={retry} />;
      // the report viewer, as from the folder (FU-P3-88a); past its cap, Download; from a job's
      // Outputs, a link, so the back link still returns to the sheet
      if ((file.size ?? 0) > REPORT_MAX) return <Note title="Too large for the report viewer (over 1 GiB). Download it to open it." actions={download} />;
      if (!task || !attempt) return <Navigate to="/runs/$id/report" params={{ id }} search={{ path: file.path, from: "results", sort, q }} replace />;
      return (
        <Note
          title="An HTML report opens in Spectio's report viewer."
          actions={
            <Link to="/runs/$id/report" params={{ id }} search={{ path: file.path }}>
              Open it in the report viewer
            </Link>
          }
        />
      );
    }
    case "image":
      return <ImageView id={id} file={file} />;
    case "tiff":
      return <TiffView id={id} file={file} ome={false} />;
    case "ometiff":
      return <OmeTiffView id={id} file={file} />;
    case "omezarr":
      return <OmeZarrView id={id} file={file} />;
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
  const image = file?.type === "dir" && fileKind(file.name) === "omezarr"; // the one folder previewed
  if (file?.type === "dir" && !image && work) return <Navigate to="/runs/$id/workdir" params={{ id }} search={{ path: file.path, sort, q, task, attempt }} replace />;
  if (file?.type === "dir" && !image) return <Navigate to="/runs/$id/results" params={{ id }} search={{ path: file.path, sort, q, task, attempt }} replace />;

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
          <Viewer id={id} file={file} kind={kind} retry={retry} search={search} />
        )}
      </div>
    </Work.Provider>
  );
}
