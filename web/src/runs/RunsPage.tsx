import { Button } from "@mantine/core";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useMediaQuery } from "@mantine/hooks";
import type { CellKeyDownEvent, ColDef, FullWidthCellKeyDownEvent, SortChangedEvent } from "ag-grid-community";
import { type ReactNode, Suspense, createContext, lazy, useCallback, useContext, useEffect, useRef, useState } from "react";
import { type Page, type Run, type RunsSort, type ServerVersion, type Summary, listRuns, runsSummary, setPinned } from "../api";
import { ICONS, Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { useServer } from "../server";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";
import type GridOf from "./DataGrid";
import { DeleteRuns } from "./DeleteRuns";
import { Pipeline, RunLink, StateWord, runName, stateContext, tasksText } from "./RunState";
import { ACTIVE, duration, isTerminal, plural, shortId, tone, when, words } from "./stateWord";

/** The state filters; `key` is the `?state=` of the URL, so Home's cards link to one (UX-PAR-12). */
export const FILTERS: { key: string; label: string; states: string[] | null }[] = [
  { key: "all", label: "All", states: null },
  { key: "active", label: "Active", states: ACTIVE },
  { key: "failed", label: "Failed", states: ["failed"] },
  { key: "succeeded", label: "Succeeded", states: ["succeeded"] },
  { key: "cancelled", label: "Cancelled", states: ["cancelled"] },
];

/** The list's orders (`?sort=`, FU-P3-115b) and the footer's words for each; none is newest first. */
const SORTS: Partial<Record<RunsSort, string>> = {
  name: "by name",
  "-name": "by name, Z to A",
  state: "by state",
  "-state": "by state, Z to A",
  started_at: "oldest started first",
  "-started_at": "latest started first",
  duration: "shortest first",
  "-duration": "longest first",
};

/** The `/runs` search params: a known filter key, or none, the name filter and the sort when set. */
export function runsSearch(search: Record<string, unknown>): { state?: string; q?: string; sort?: RunsSort } {
  const { state, q, sort } = search;
  return {
    ...(typeof state === "string" && FILTERS.some((f) => f.key === state && f.key !== "all") ? { state } : {}),
    ...(typeof q === "string" && q !== "" ? { q } : {}),
    ...(typeof sort === "string" && Object.hasOwn(SORTS, sort) ? { sort: sort as RunsSort } : {}),
  };
}

/** The page's selection and pin action, read by the grid's cells and the phone's cards. */
const Rows = createContext<{ selected: Set<string>; toggle: (ids: string[], on: boolean) => void; pin: (run: Run) => void; ids: string[] }>({
  selected: new Set(),
  toggle: () => {},
  pin: () => {},
  ids: [],
});

/** A row's box, a native checkbox named after its run (ui-spec §4.3 note of 2026-11-10). */
function SelectBox({ run }: { run: Run }) {
  const { selected, toggle } = useContext(Rows);
  return (
    <input
      type="checkbox"
      className="sp-select"
      aria-label={`Select run ${runName(run)}`}
      checked={selected.has(run.id)}
      onChange={(e) => toggle([run.id], e.currentTarget.checked)}
    />
  );
}

/** The header's box; Space on its header cell ticks it, as on a row's Select cell. */
function SelectAll() {
  const { selected, toggle, ids } = useContext(Rows);
  const box = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const cell = box.current?.closest<HTMLElement>(".ag-header-cell");
    const onKey = (e: KeyboardEvent) => {
      if (e.key === " " && e.target === cell) {
        e.preventDefault();
        box.current?.click();
      }
    };
    cell?.addEventListener("keydown", onKey);
    return () => cell?.removeEventListener("keydown", onKey);
  }, []);
  return (
    <input
      ref={box}
      type="checkbox"
      className="sp-select"
      aria-label="Select all runs on this page"
      checked={ids.length > 0 && ids.every((id) => selected.has(id))}
      onChange={(e) => toggle(ids, e.currentTarget.checked)}
    />
  );
}

/** The pin toggle of a row (aria-pressed); pinned runs come first in every sort. */
function PinButton({ run }: { run: Run }) {
  const { pin } = useContext(Rows);
  return (
    <button type="button" className="sp-pin" aria-pressed={!!run.pinned} aria-label={`Pin run ${runName(run)}`} onClick={() => pin(run)}>
      <Icon path={ICONS.pin} size={15} />
    </button>
  );
}

/** Where heads run, by the server's executor: tmux sessions on the login node, or processes on
 * this host with the local executor (P1 Task 9; tmux comes with Task 10). */
export const headsWhere = (server: ServerVersion) =>
  server.executor === "local" ? `heads run as processes on ${server.node}` : `heads in tmux sessions on ${server.node}`;

/** "known so far" while a Nextflow run runs: its total grows as processes start (UX-PAR-17). */
const knownSoFar = (run: Run) =>
  run.workflow.engine === "nextflow" && !isTerminal(run.state) && !!run.summary.tasks.total;

/** Under the count: the engine's unit for Snakemake, "known so far", and the failed count. */
function TasksCell({ run }: { run: Run }) {
  const failed = run.summary.tasks.failed;
  const note = run.workflow.engine === "snakemake" ? "jobs" : knownSoFar(run) ? "known so far" : null;
  return (
    <>
      {tasksText(run)}
      {(failed > 0 || note) && (
        <span className="sp-muted">
          {failed > 0 && <span className="sp-bad-inline">{failed} failed</span>}
          {failed > 0 && note && " · "}
          {note && <span>{note}</span>}
        </span>
      )}
    </>
  );
}
/** A run as a card, for the phone (MLiteRuns, MLiteHome; UX-PAR-10): the state and duration,
 * the name, the pipeline with its mark and the tasks, then the context. */
export function RunCard({ run, select }: { run: Run; select?: ReactNode }) {
  const { units } = words(run.workflow.engine);
  return (
    <li className="sp-run-card" data-rail="" data-tone={tone(run.state)}>
      <span className="sp-run-card-top">
        {select}
        <StateWord state={run.state} />
        <span>{duration(run.started_at, run.ended_at)}</span>
      </span>
      <RunLink run={run} />
      <span className="sp-run-card-line">
        <Pipeline run={run} size={16} />
        <span>
          {" · "}
          {tasksText(run)} {units}
          {knownSoFar(run) && " known so far"}
        </span>
      </span>
      <span className="sp-run-card-line">
        {run.origin === "cli-observed" && (
          <span className="sp-chip">
            <Icon path={ICONS.terminal} size={12} /> From a terminal
          </span>
        )}
        <span>{stateContext(run)}</span>
      </span>
    </li>
  );
}

// AG Grid is its own chunk, loaded with the desktop list; the phone keeps its cards (ui-spec §4.13).
const DataGrid = lazy(() => import("./DataGrid")) as unknown as typeof GridOf;

/** The 0.0.1 columns (ui-spec §4.3) after the select box. Run, State, Started and Duration sort
 * on the server (`colId` is the `sort=` key): the grid keeps the API's order (`comparator` 0) and
 * filters nothing on its own. The state rail is the row's left edge, in its tone. */
const keep = () => 0;
const COLUMNS: ColDef<Run>[] = [
  {
    colId: "select",
    headerName: "",
    flex: 0,
    width: 52,
    minWidth: 52,
    headerComponent: SelectAll,
    cellRenderer: ({ data: run }: { data: Run }) => <SelectBox run={run} />,
  },
  {
    headerName: "Run",
    colId: "name",
    flex: 1.4,
    cellRenderer: ({ data: run }: { data: Run }) => (
      <>
        <span className="sp-run-cell">
          <RunLink run={run} />
          <PinButton run={run} />
        </span>
        {run.origin === "cli-observed" && (
          <span className="sp-chip">
            <Icon path={ICONS.terminal} size={12} /> From a terminal
          </span>
        )}
        <span className="sp-id">{shortId(run.id)}</span>
      </>
    ),
  },
  {
    headerName: "State",
    colId: "state",
    flex: 1.6,
    cellRenderer: ({ data: run }: { data: Run }) => (
      <>
        <StateWord state={run.state} />
        <span className="sp-muted">{stateContext(run)}</span>
      </>
    ),
  },
  { headerName: "Workflow", flex: 1.4, cellRenderer: ({ data: run }: { data: Run }) => <Pipeline run={run} /> },
  { headerName: "Tasks", cellRenderer: ({ data: run }: { data: Run }) => <TasksCell run={run} /> },
  { headerName: "Started", colId: "started_at", valueGetter: ({ data: run }) => (run ? when(run.started_at ?? run.created_at) : "") },
  { headerName: "Duration", colId: "duration", valueGetter: ({ data: run }) => (run ? duration(run.started_at, run.ended_at) : "") },
];

const SORTABLE = new Set(["name", "state", "started_at", "duration"]);

/** AG Grid keeps Tab and Enter for its cells, so a cell's controls are not tab stops: Enter on the
 * Run cell follows its link, Space on it presses its pin, Space on a Select cell ticks its box
 * (ui-spec §4.13). A key on the control itself is the control's own. */
const onCellKey = (e: CellKeyDownEvent<Run> | FullWidthCellKeyDownEvent<Run>) => {
  const key = e.event as KeyboardEvent | null | undefined;
  const cell = key?.target as HTMLElement | undefined;
  if (!key || !cell || cell.getAttribute("role") !== "gridcell" || !("colDef" in e)) return;
  const keys: Record<string, Record<string, string>> = {
    name: { Enter: "a.sp-run-link", " ": "button.sp-pin" },
    select: { " ": "input.sp-select" },
  };
  const target = keys[e.colDef.colId ?? ""]?.[key.key];
  if (!target) return;
  key.preventDefault();
  cell.querySelector<HTMLElement>(target)?.click();
};

const PAGE = 50;

type List = { rows: Run[]; next: string | null };

// The list's order (sort=-created_at): newest first, then by ID.
const older = (a: Run, b: Run) => a.created_at < b.created_at || (a.created_at === b.created_at && a.id < b.id);

/** A refresh on a stream frame: the fresh first page, then the rows "Load more" added past it
 * and their cursor. Newest first, those are the rows older than its last row. Under another sort a
 * row can move (an unpin, a run that ends), so every shown row the fresh page lacks is kept, in
 * its old place: Load more replaces it if its next page brings it again (CR-P3FU115B-02). */
function refresh(shown: List | null, page: Page<Run>, newest: boolean): List {
  const fresh = page.items ?? [];
  const last = fresh[fresh.length - 1];
  const ids = new Set(fresh.map((r) => r.id));
  const tail = shown && last && page.next ? shown.rows.filter((r) => !ids.has(r.id) && (!newest || older(r, last))) : [];
  return tail.length ? { rows: [...fresh, ...tail], next: shown!.next } : { rows: fresh, next: page.next ?? null };
}

const count = (summary: Summary | null, states: string[] | null) =>
  (summary?.groups ?? [])
    .filter((g) => states === null || states.includes(g.key))
    .reduce((sum, g) => sum + g.count, 0);

/** The "Launch a workflow" empty state (ui-spec §11): says why, and the next step. */
export function NoRuns() {
  return (
    <div className="sp-empty">
      <p>No runs yet.</p>
      <Button component={Link} to="/launch">
        Launch a workflow
      </Button>
    </div>
  );
}

/** The runs list (ui-spec §4.3, 0.0.1 columns): state and name filters, Load more, refreshed
 * from the stream. */
export function RunsPage() {
  const search = useSearch({ from: "/runs" });
  const navigate = useNavigate({ from: "/runs" });
  const filter = Math.max(0, FILTERS.findIndex((f) => f.key === search.state));
  const q = search.q ?? "";
  const sort = search.sort;
  // Each change keeps the other param: the name filter lands 250 ms after typing, a click may come between.
  const setSearch = (change: { state?: string; q?: string; sort?: string }) =>
    navigate({ search: (prev) => runsSearch({ ...prev, ...change }), replace: true });
  const setFilter = (i: number) => setSearch({ state: FILTERS[i].states ? FILTERS[i].key : undefined });
  const server = useServer();
  const phone = usePhone();
  // UX-G3a-05: Started drops below 1100 px, so the grid fits at 1024 px without a sideways scroll.
  const narrow = useMediaQuery("(max-width: 1099.98px)") ?? false;
  const [typed, setTyped] = useState(q);
  // The q this page last wrote: a q from elsewhere (a link that drops it) re-seeds the box, while
  // the page's own write never trims what the user is still typing (CR-P3PARA-09).
  const written = useRef(q);
  const [list, setList] = useState<List | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const states = FILTERS[filter].states?.join(",");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // what the last delete or pin said, focused after a delete: Delete… has gone with the selection
  const [said, setSaid] = useState<string[]>([]);
  const saidLine = useRef<HTMLDivElement>(null);
  useEffect(() => setSelected(new Set()), [states, q]);

  useEffect(() => {
    document.title = "Runs · Spectio";
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      written.current = typed.trim();
      setSearch({ q: written.current });
    }, 250);
    return () => clearTimeout(timer);
  }, [typed]);
  useEffect(() => {
    if (q === written.current) return;
    written.current = q;
    setTyped(q);
  }, [q]);

  // A response is dropped once the filters change (the query's signal is aborted), and a first
  // page once a newer one was asked for: an older response can land last.
  const query = useRef(new AbortController());
  const loads = useRef(0);
  const load = useCallback(
    (merge = false) => {
      const { signal } = query.current;
      const mine = ++loads.current;
      const stale = () => signal.aborted || mine !== loads.current;
      Promise.all([listRuns({ state: states, q, sort, limit: PAGE }, signal), runsSummary(signal)])
        .then(([page, sum]) => {
          if (stale()) return;
          setList((shown) => (merge ? refresh(shown, page, !sort) : { rows: page.items ?? [], next: page.next ?? null }));
          setSummary(sum);
          setError(null);
        })
        .catch((e: Error) => stale() || setError(e.message));
    },
    [states, q, sort],
  );
  useEffect(() => {
    const controller = new AbortController();
    query.current = controller;
    load();
    return () => controller.abort();
  }, [load]);
  useFrames(() => load(true));

  const runs = list?.rows ?? null;
  const next = list?.next ?? null;
  const more = () => {
    const { signal } = query.current;
    listRuns({ state: states, q, sort, limit: PAGE, cursor: next }, signal)
      .then((page) => {
        if (signal.aborted) return;
        const items = page.items ?? [];
        const ids = new Set(items.map((r) => r.id));
        setList((shown) => ({ rows: [...(shown?.rows ?? []).filter((r) => !ids.has(r.id)), ...items], next: page.next ?? null }));
      })
      .catch((e: Error) => signal.aborted || setError(e.message));
  };

  const chosen = (runs ?? []).filter((r) => selected.has(r.id));
  const live = chosen.filter((r) => !isTerminal(r.state)).length;
  const why = live
    ? `${plural(live, "selected run has", "selected runs have")} not ended: cancel ${live === 1 ? "it" : "them"} first`
    : chosen.length > 200
      ? "At most 200 runs at once: clear some first"
      : null;
  const rows = {
    selected,
    ids: (runs ?? []).map((r) => r.id),
    toggle: (ids: string[], on: boolean) =>
      setSelected((was) => {
        const now = new Set(was);
        for (const id of ids) on ? now.add(id) : now.delete(id);
        return now;
      }),
    pin: (run: Run) =>
      setPinned(run.id, !run.pinned)
        .then(() => {
          setSaid([]);
          load(true);
        })
        .catch((e: Error) => setSaid([`${runName(run)} was not pinned: ${e.message}`])),
  };
  const deleted = (lines: string[], ids: string[]) => {
    // a refresh keeps the rows Load more added that the first page lacks, as a deleted run is
    const gone = new Set(ids);
    setList((l) => l && { ...l, rows: l.rows.filter((r) => !gone.has(r.id)) });
    setSelected(new Set());
    setSaid(lines);
    load(true);
    setTimeout(() => saidLine.current?.focus());
  };
  const onSort = (e: SortChangedEvent<Run>) => {
    if (e.source !== "uiColumnSorted") return;
    const col = e.columns?.find((c) => c.getSort());
    setSearch({ sort: col ? `${col.getSort() === "desc" ? "-" : ""}${col.getColId()}` : undefined });
  };
  const columns = COLUMNS.filter((c) => !(narrow && c.headerName === "Started")).map(
    (c): ColDef<Run> =>
      c.colId && SORTABLE.has(c.colId)
        ? { ...c, sortable: true, comparator: keep, sortingOrder: ["asc", "desc"], sort: sort === c.colId ? "asc" : sort === `-${c.colId}` ? "desc" : null }
        : c,
  );

  const total = count(summary, null);
  const filtered = filter !== 0 || q !== "";
  // "of N" only while the filter's total is known from the summary (ui-spec §4.11).
  const shownTotal = q === "" && summary ? count(summary, FILTERS[filter].states) : null;
  return (
    <div className="sp-runs">
      <PageHead
        section="runs"
        title="Runs"
        phoneBar="title-and-sub"
        sub={
          <>
            <span>
              {total} {total === 1 ? "run" : "runs"}
            </span>
            <span>{count(summary, ACTIVE)} active</span>
            {server && !phone && <span>{headsWhere(server)}</span>}
            <LiveStatus />
          </>
        }
        action={
          <Button component={Link} to="/launch">
            Launch a workflow
          </Button>
        }
      />

      <div className="sp-filters">
        <label className="sp-search-field">
          <Icon path={ICONS.search} size={16} />
          <input
            type="search"
            aria-label="Filter by run name"
            placeholder="Filter by run name"
            value={typed}
            onChange={(e) => setTyped(e.currentTarget.value)}
          />
        </label>
        <div className="sp-segments" role="group" aria-label="Show runs">
          {FILTERS.map((f, i) => (
            <button key={f.label} type="button" aria-pressed={filter === i} onClick={() => setFilter(i)}>
              {f.label}
              <span className="sp-count">{count(summary, f.states)}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div role="alert" className="sp-empty">
          <p>The runs could not be read: {error}</p>
          <Button variant="default" onClick={() => load()}>
            Retry
          </Button>
        </div>
      )}
      <div ref={saidLine} tabIndex={-1} role="status" className="sp-said">
        {said.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
      {chosen.length > 0 && (
        <div className="sp-bulk" role="group" aria-label="Selected runs">
          <strong>{chosen.length} selected</strong>
          <DeleteRuns runs={chosen} why={why} onDeleted={deleted} />
          <Button variant="subtle" onClick={() => setSelected(new Set())}>
            Clear selection
          </Button>
        </div>
      )}
      {runs === null && !error && <p className="sp-muted">Loading the runs…</p>}
      {runs?.length === 0 && (filtered ? <p className="sp-empty">No run matches these filters.</p> : <NoRuns />)}
      <Rows.Provider value={rows}>
      {!!runs?.length && phone && (
        <ul className="sp-run-cards" aria-label="Runs">
          {runs.map((run) => (
            <RunCard key={run.id} run={run} select={<SelectBox run={run} />} />
          ))}
        </ul>
      )}
      {!!runs?.length && !phone && (
        <Suspense fallback={<p className="sp-muted">Loading the runs…</p>}>
          <DataGrid<Run>
            label="Runs"
            className="sp-grid-runs"
            rowData={runs}
            columnDefs={columns}
            defaultColDef={{ sortable: false, autoHeight: true, wrapText: true, flex: 1, minWidth: 110, suppressHeaderMenuButton: true }}
            getRowId={({ data }) => data.id}
            getRowStyle={({ data }) => (data ? { "--tone": `var(--sp-state-${tone(data.state)})` } : undefined)}
            domLayout="autoHeight"
            onCellKeyDown={onCellKey}
            onSortChanged={onSort}
          />
        </Suspense>
      )}
      </Rows.Provider>
      {!!runs?.length && (
        <p className="sp-foot-line">
          {shownTotal !== null ? `${runs.length} of ${shownTotal} runs` : `${runs.length} ${runs.length === 1 ? "run" : "runs"}`} ·{" "}
          {(sort && SORTS[sort]) ?? "newest first"}
        </p>
      )}
      {next && (
        <div>
          <Button variant="default" onClick={more}>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
