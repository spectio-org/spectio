import { ActionIcon, Button } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { type ReactNode, type Ref, useEffect, useMemo, useRef, useState } from "react";
import { type ApiError, type ResultEntry, type Results, type RunDetail, type WorkRoot, getRun, listResults, resultUrl } from "../api";
import { type IconName, Icon } from "../icons";
import { usePageCrumb } from "../shell/crumb";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";
import { EmptyState, ErrorPanel, SkeletonRows } from "../shell/States";
import { Toolbar, ToolbarSearch } from "../shell/Toolbar";
import { CopyButton } from "./CopyMenu";
import { type EntryKind, OFFLINE, OFFLINE_WHY, type Sort, SORTS, counts, entryKind, filterEntries, hasDotPart, join, sortEntries, taskSearch } from "./explorer";
import { kindWord, size } from "./preview";
import { isPlainText, isResultPath } from "./ReportViewer";
import { NotFound, findTask } from "./RunDetailPage";
import { runName, taskLabel } from "./RunState";
import { when, words } from "./stateWord";

// The results browser (P1 Task 32 part two; ui-spec §4.4 run tools note and §4.4.1, Explorer,
// FU-P3-85d; boards LiteResults, MLiteResults): one folder of a run's results at a time, read only,
// under a path bar of links back up, with Copy path. One card, as RunOutputs' "Published files":
// the counts and the filter, then a table (rows on the phone) sorted with folders first. A folder
// opens here, an HTML file in the report viewer, any other file in its preview; each file row ends
// with Download. A link that leaves the results directory is not followed. Sort, filter and the
// row to focus on the way back are kept in the URL. The same page shows a Nextflow attempt's work
// directory (`work`, FU-P3-85e; board LiteWorkdir): its routes, the task's name in the h1, the back
// link and the title, an HTML file opening its preview (never the report viewer), no dot name.

export interface ResultsSearch {
  path?: string;
  sort?: Sort;
  q?: string;
  focus?: string;
  /** the preview shows an HTML file as text, not in the report viewer (FU-P3-88a) */
  view?: "text";
  task?: string;
  attempt?: number;
}

const Q_MAX = 200;

/** `/runs/$id/results?path=<folder>` (no path: the results root), and the preview's
 * `/runs/$id/results/file?path=<file>`. The view is kept in the URL (ui-spec §4.4.1): `sort` (name,
 * the default, is never written), the filter `q`, the row to `focus` on the way back from a preview,
 * `view=text` for the source of an HTML file, and the `task` and `attempt` a Preview of the task
 * sheet's Outputs returns to. A URL's text is
 * shown only in the filter field and its no-match line, so `q` and `focus` with a control, bidi or
 * format character are dropped (SEC-P3T32B-02). */
export function resultsSearch(search: Record<string, unknown>): ResultsSearch {
  const { path, sort, q, focus, view } = search;
  return {
    ...(typeof path === "string" && path !== "" ? { path } : {}),
    ...(SORTS.includes(sort as Sort) && sort !== "name" ? { sort: sort as Sort } : {}),
    ...(typeof q === "string" && q !== "" && q.length <= Q_MAX && isPlainText(q) ? { q } : {}),
    ...(typeof focus === "string" && isResultPath(focus) && !focus.includes("/") ? { focus } : {}),
    ...(view === "text" ? { view } : {}),
    ...taskSearch(search),
  };
}

const LIVE_DELAY = 150; // ms after typing stops: the filter's count and its URL

const KIND_ICONS: Record<EntryKind, IconName> = {
  folder: "folder",
  text: "file",
  table: "table",
  json: "braces",
  image: "image",
  tiff: "image",
  ometiff: "image",
  omezarr: "image",
  html: "fileCode",
  pdf: "file",
  binary: "file",
  file: "file",
  link: "externalLink",
};

/** The kind as a text badge with its icon: colour is never the only signal (board LiteKind). */
export function KindBadge({ kind, work = false }: { kind: EntryKind; work?: boolean }) {
  return (
    <span className="sp-kind" data-kind={kind}>
      <Icon name={KIND_ICONS[kind]} />
      {kindWord(kind, work)}
    </span>
  );
}

const COLUMNS: { key: "name" | "size" | "mtime"; label: string; num?: boolean }[] = [
  { key: "name", label: "Name" },
  { key: "size", label: "Size", num: true },
  { key: "mtime", label: "Modified" },
];
const SORT_WORDS: Record<Sort, string> = {
  name: "Name, A to Z",
  "-name": "Name, Z to A",
  size: "Size, smallest first",
  "-size": "Size, largest first",
  mtime: "Modified, oldest first",
  "-mtime": "Modified, newest first",
};

/** The entry's name: a link to the folder, the report viewer or the preview; a link outside is
 * not followed. `view` is the sort and filter a file's page returns with. */
function EntryLink({ id, folder, entry, view, work, focusRef, children }: { id: string; folder: string; entry: ResultEntry; view: { sort?: Sort; q?: string }; work?: WorkRoot; focusRef?: Ref<HTMLAnchorElement>; children: ReactNode }) {
  const path = join(folder, entry.name);
  const props = { ref: focusRef, className: "sp-explorer-link", params: { id } };
  if (work) {
    const keep = { task: work.task, attempt: work.attempt };
    return entry.type === "dir" ? (
      <Link {...props} to="/runs/$id/workdir" search={{ path, sort: view.sort, ...keep }}>
        {children}
      </Link>
    ) : (
      <Link {...props} to="/runs/$id/workdir/file" search={{ path, ...view, ...keep }}>
        {children}
      </Link>
    );
  }
  if (entry.type === "dir") {
    return (
      <Link {...props} to="/runs/$id/results" search={{ path, sort: view.sort }}>
        {children}
      </Link>
    );
  }
  return entryKind(entry) === "html" ? (
    <Link {...props} to="/runs/$id/report" search={{ path, from: "results" as const, ...view }}>
      {children}
    </Link>
  ) : (
    <Link {...props} to="/runs/$id/results/file" search={{ path, ...view }}>
      {children}
    </Link>
  );
}

function Listing({ id, folder, results, search, work }: { id: string; folder: string; results: Results; search: ResultsSearch; work?: WorkRoot }) {
  const phone = usePhone();
  const navigate = useNavigate({ from: work ? "/runs/$id/workdir" : "/runs/$id/results" });
  const sort = search.sort ?? "name";
  const [typed, setTyped] = useState(search.q ?? "");
  const [said, setSaid] = useState("");
  const bar = useRef<HTMLDivElement>(null);
  const focused = useRef<HTMLAnchorElement>(null);
  const write = (change: Partial<ResultsSearch>) =>
    navigate({ search: (prev) => resultsSearch({ ...prev, ...change, focus: undefined }), replace: true });

  const entries = results.entries;
  const shown = useMemo(() => sortEntries(filterEntries(entries, typed), sort), [entries, typed, sort]);
  // the count is said, and the filter written to the URL, once typing stops
  useEffect(() => {
    const timer = setTimeout(() => {
      setSaid(typed ? `${shown.length} of ${entries.length} shown` : "");
      write({ q: typed || undefined });
    }, LIVE_DELAY);
    return () => clearTimeout(timer);
  }, [typed]);
  // back from a file's page: its row in view, its link focused
  useEffect(() => {
    focused.current?.closest("tr, li")?.scrollIntoView?.({ block: "center" });
    focused.current?.focus();
  }, []);

  if (!results.exists && work) {
    return (
      <EmptyState icon="folder">
        The work directory is not there yet. The job creates it when it starts; on a shared file system it may take a moment to appear. Spectio checks again when you reload.
      </EmptyState>
    );
  }
  if (!results.exists) {
    return (
      <EmptyState icon="folder">The results directory does not exist yet. The pipeline creates it when its first results are published. Spectio checks again when you reload.</EmptyState>
    );
  }
  const label = folder.split("/").pop() || (work ? "work directory" : "results");
  const view = { sort: search.sort, q: typed || undefined };
  const focusRef = (entry: ResultEntry) => (entry.name === search.focus ? focused : undefined);
  const facts = (entry: ResultEntry) => [kindWord(entryKind(entry), !!work), entry.type === "file" && entry.size !== null ? size(entry.size) : null, when(entry.mtime)].filter(Boolean).join(" · ");
  const clear = () => {
    setTyped("");
    bar.current?.querySelector("input")?.focus();
  };

  const rows = phone ? (
    <ul className="sp-explorer-rows" aria-label={label}>
      {shown.map((entry) => {
        const first = (
          <>
            <span className="sp-explorer-first">
              <Icon name={entry.type === "dir" ? "folder" : "file"} />
              <span data-name="">{entry.name}</span>
            </span>
            <span className="sp-muted">{entry.type === "link_outside" ? `${facts(entry)} · not followed` : facts(entry)}</span>
          </>
        );
        return (
          <li key={entry.name}>
            {entry.type === "link_outside" ? (
              <div className="sp-explorer-row">{first}</div>
            ) : (
              <EntryLink id={id} folder={folder} entry={entry} view={view} work={work} focusRef={focusRef(entry)}>
                {first}
              </EntryLink>
            )}
          </li>
        );
      })}
    </ul>
  ) : (
    <div className="sp-table-wrap sp-explorer-table">
      <table className="sp-table" aria-label={label}>
        <thead>
          <tr>
            {COLUMNS.map((c, i) => {
              const on = sort.replace("-", "") === c.key;
              const down = on && sort.startsWith("-");
              const th = (
                <th key={c.key} scope="col" className={c.num ? "sp-num" : undefined} aria-sort={on ? (down ? "descending" : "ascending") : undefined}>
                  <button type="button" className="sp-sort" data-on={on || undefined} onClick={() => write({ sort: (on && !down ? `-${c.key}` : c.key) as Sort })}>
                    {c.label}
                    {on && <span aria-hidden="true">{down ? " ↓" : " ↑"}</span>}
                  </button>
                </th>
              );
              return i === 1 ? [<th key="kind" scope="col">Kind</th>, th] : th;
            })}
            <th scope="col">
              <span className="sp-sr">Download</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {shown.map((entry) => (
            <tr key={entry.name}>
              <th scope="row">
                <span className="sp-result-name">
                  <Icon name={entry.type === "dir" ? "folder" : "file"} />
                  {entry.type === "link_outside" ? (
                    <span>
                      {entry.name} <span className="sp-muted">not followed</span>
                    </span>
                  ) : (
                    <EntryLink id={id} folder={folder} entry={entry} view={view} work={work} focusRef={focusRef(entry)}>
                      {entry.name}
                    </EntryLink>
                  )}
                </span>
              </th>
              <td>
                <KindBadge kind={entryKind(entry)} work={!!work} />
              </td>
              <td className="sp-num">{entry.type === "file" && entry.size !== null ? size(entry.size) : "—"}</td>
              <td>{when(entry.mtime)}</td>
              <td className="sp-explorer-act">
                {entry.type === "file" && (
                  <ActionIcon component="a" variant="default" size="md" href={resultUrl(id, join(folder, entry.name), { download: true }, work)} download aria-label={`Download ${entry.name}`}>
                    <Icon name="download" />
                  </ActionIcon>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <>
      <section className="sp-card sp-explorer" aria-labelledby={`${id}-explorer`}>
        <div className="sp-explorer-head">
          <h2 id={`${id}-explorer`}>
            {work ? "Work directory" : "Results"} · {counts(entries)}
          </h2>
        </div>
        <div ref={bar}>
          <Toolbar
            label="Filter and sort"
            search={<ToolbarSearch label="Filter this folder" value={typed} onChange={setTyped} />}
            filters={
              phone && (
                <label className="sp-select">
                  Sort by
                  <select value={sort} onChange={(e) => write({ sort: e.currentTarget.value as Sort })}>
                    {SORTS.map((s) => (
                      <option key={s} value={s}>
                        {SORT_WORDS[s]}
                      </option>
                    ))}
                  </select>
                </label>
              )
            }
          />
          <span role="status" className="sp-sr">
            {said}
          </span>
        </div>
        {results.truncated && (
          <div className="sp-note" role="note">
            <p>This folder has more than 1,000 entries. Spectio lists 1,000 of them, in no particular order; sort and filter see only those.</p>
            <p>
              Open it on the cluster: <span className="sp-mono">{join(results.root, folder)}</span>
            </p>
          </div>
        )}
        {entries.length === 0 ? (
          <EmptyState icon="folder">This folder is empty.</EmptyState>
        ) : shown.length === 0 ? (
          <EmptyState
            icon="search"
            action={
              <Button variant="default" onClick={clear}>
                Clear
              </Button>
            }
          >
            No entry in this folder matches '{typed}'
          </EmptyState>
        ) : (
          rows
        )}
      </section>
      <p className="sp-muted">
        {work
          ? "Read-only. A folder's size is not counted. Names that start with a dot are not listed: the job's own files are in the task sheet. A staged input copied here, or linked from another task of this run, reads like an output."
          : "Read-only. A folder's size is not counted. A file's name opens its preview; an HTML report opens in Spectio's report viewer."}
      </p>
    </>
  );
}

/** The link back to the run: its Summary, or the task sheet a Preview of its Outputs came from. */
export function BackToRun({ id, run, task, attempt }: { id: string; run: RunDetail | null; task?: string; attempt?: number }) {
  const name = run ? runName(run) : "Run";
  return task && attempt ? (
    <Link className="sp-report-back" to="/runs/$id" params={{ id }} search={{ task, attempt }}>
      <Icon name="chevronLeft" /> {name} · {words(run?.workflow.engine ?? null).unit}, attempt {attempt}
    </Link>
  ) : (
    <Link className="sp-report-back" to="/runs/$id" params={{ id }}>
      <Icon name="chevronLeft" /> {name} · Summary
    </Link>
  );
}

/** The task's name for a work directory's pages, from the run's task listing (the task's ID when
 * the listing does not have it); null until known, or with no `work`. */
export function useTaskName(id: string, work?: WorkRoot): string | null {
  const [name, setName] = useState<string | null>(null);
  const task = work?.task;
  useEffect(() => {
    if (!task) return;
    const controller = new AbortController();
    findTask(id, task, controller.signal)
      .then((t) => setName(t ? taskLabel(t) : task))
      .catch(() => controller.signal.aborted || setName(task));
    return () => controller.abort();
  }, [id, task]);
  return name;
}

/** A work directory's link back: the run, with the task sheet open on that attempt. */
function BackToTask({ id, work, name }: { id: string; work: WorkRoot; name: string | null }) {
  return (
    <Link className="sp-report-back" to="/runs/$id" params={{ id }} search={{ task: work.task, attempt: work.attempt }}>
      <Icon name="chevronLeft" /> {name ?? "Task"} · attempt {work.attempt}
    </Link>
  );
}

/** The path bar: links from `results` (or `work directory`) down, the last part the current page. */
export function Crumbs({ id, parts, work, sort }: { id: string; parts: string[]; work?: WorkRoot; sort?: Sort }) {
  const keep = work ? { task: work.task, attempt: work.attempt } : {};
  const to = (path: string) =>
    work ? (
      <Link to="/runs/$id/workdir" params={{ id }} search={{ path: path || undefined, sort, ...keep }}>
        {path.split("/").pop() || "work directory"}
      </Link>
    ) : (
      <Link to="/runs/$id/results" params={{ id }} search={{ path: path || undefined, sort }}>
        {path.split("/").pop() || "results"}
      </Link>
    );
  const root = work ? "work directory" : "results";
  return (
    <nav aria-label="Folder">
      <ol>
        <li>{parts.length ? to("") : <span aria-current="page">{root}</span>}</li>
        {parts.map((part, i) => (
          <li key={i}>{i < parts.length - 1 ? to(parts.slice(0, i + 1).join("/")) : <span aria-current="page">{part}</span>}</li>
        ))}
      </ol>
    </nav>
  );
}

export function ResultsBrowser({ id, search, work }: { id: string; search: ResultsSearch; work?: WorkRoot }) {
  const path = search.path ?? "";
  const [run, setRun] = useState<RunDetail | null>(null);
  const [missing, setMissing] = useState(false);
  const [results, setResults] = useState<Results | null>(null);
  // a refusal in words (ui-spec §4.4.1 States), with Retry when trying again may help
  const [error, setError] = useState<{ title: string; body?: string; retry?: boolean } | null>(null);
  const [reads, setReads] = useState(0);
  const valid = path === "" || (isResultPath(path) && !(work && hasDotPart(path)));
  const taskName = useTaskName(id, work);
  const where_ = work ? "this job's work directory" : "this run's results";
  useEffect(() => {
    const controller = new AbortController();
    getRun(id, controller.signal)
      .then(setRun)
      .catch((e: ApiError) => controller.signal.aborted || (e.status === 404 ? setMissing(true) : setError({ title: e.message })));
    return () => controller.abort();
  }, [id]);
  useEffect(() => {
    setResults(null);
    setError(null);
    if (!valid) return;
    const controller = new AbortController();
    listResults(id, path, controller.signal, work)
      .then(setResults)
      .catch((e: ApiError) => {
        if (controller.signal.aborted) return;
        setError(
          e.status === 404 && path
            ? { title: `No such folder in ${where_}.` }
            : e.status === 422
              ? { title: `Not a folder of ${where_}.` }
              : e.status === 410 && work
                ? { title: "The work directory was removed" }
                : e.status === 409
                  ? { title: "The run's directory is not reachable", body: e.message, retry: true }
                  : e.status === 503
                    ? { title: OFFLINE, body: OFFLINE_WHY, retry: true }
                    : { title: e.message },
        );
      });
    return () => controller.abort();
  }, [id, path, valid, work?.task, work?.attempt, reads]);

  const name = run ? runName(run) : null;
  usePageCrumb(name);
  const folderName = (results?.path ?? "").split("/").pop() || "work directory";
  useEffect(() => {
    if (name && !work) document.title = `Results · ${name} · Spectio`;
    else if (name && taskName) document.title = `${folderName} · ${taskName} · ${name} · Spectio`;
  }, [name, taskName, folderName, work]);

  if (missing) return <NotFound />;
  // The path bar shows the folder the server answered for, never the URL's own text (SEC-P3T32B-02).
  const shown = results?.path ?? "";
  const parts = shown ? shown.split("/") : [];
  const where = results ? join(results.root, shown) : null;
  return (
    <div className="sp-runs">
      <PageHead
        section="runs"
        icon="folder"
        title={work ? (taskName ? `Work directory · ${taskName} · attempt ${work.attempt}` : "Work directory") : "Results"}
        sub={work ? <BackToTask id={id} work={work} name={taskName} /> : <BackToRun id={id} run={run} task={search.task} attempt={search.attempt} />}
        phoneTitle="title"
      />
      <div className="sp-pathbar">
        <Crumbs id={id} parts={parts} work={work} sort={search.sort} />
        {where && (
          <span className="sp-copy-line">
            <span className="sp-mono">{where}</span>
            <CopyButton text={where} label="Copy path" name="Copy path" />
          </span>
        )}
      </div>
      {!valid ? (
        <p role="alert">Not a folder of {where_}.</p>
      ) : error?.retry ? (
        <ErrorPanel onRetry={() => setReads((r) => r + 1)}>
          <strong>{error.title}</strong>
          {error.body && <> {error.body}</>}
        </ErrorPanel>
      ) : error ? (
        <p role="alert">{error.title}</p>
      ) : results ? (
        <Listing key={path} id={id} folder={path} results={results} search={search} work={work} />
      ) : (
        <SkeletonRows label="Loading the folder…" />
      )}
    </div>
  );
}
