import { Button } from "@mantine/core";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { type Page, type Run, type ServerVersion, type Summary, listRuns, runsSummary } from "../api";
import { ICONS, Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { useServer } from "../server";
import { PageHead } from "../shell/PageHead";
import { Pipeline, RunLink, StateWord, stateContext, tasksText } from "./RunState";
import { ACTIVE, duration, isTerminal, shortId, tone, when } from "./stateWord";

/** The state filters; `key` is the `?state=` of the URL, so Home's cards link to one (UX-PAR-12). */
export const FILTERS: { key: string; label: string; states: string[] | null }[] = [
  { key: "all", label: "All", states: null },
  { key: "active", label: "Active", states: ACTIVE },
  { key: "failed", label: "Failed", states: ["failed"] },
  { key: "succeeded", label: "Succeeded", states: ["succeeded"] },
  { key: "cancelled", label: "Cancelled", states: ["cancelled"] },
];

/** The `/runs` search params: a known filter key, or none, and the name filter when set. */
export function runsSearch(search: Record<string, unknown>): { state?: string; q?: string } {
  const { state, q } = search;
  return {
    ...(typeof state === "string" && FILTERS.some((f) => f.key === state && f.key !== "all") ? { state } : {}),
    ...(typeof q === "string" && q !== "" ? { q } : {}),
  };
}

/** Where heads run, by the server's executor: tmux sessions on the login node, or processes on
 * this host with the local executor (P1 Task 9; tmux comes with Task 10). */
export const headsWhere = (server: ServerVersion) =>
  server.executor === "local" ? `heads run as processes on ${server.node}` : `heads in tmux sessions on ${server.node}`;

/** Under the count: the engine's unit for Snakemake, "known so far" while a Nextflow run runs (its
 * total grows as processes start), and the failed count (UX-PAR-17). */
function TasksCell({ run }: { run: Run }) {
  const failed = run.summary.tasks.failed;
  const note =
    run.workflow.engine === "snakemake" ? "jobs" : run.workflow.engine === "nextflow" && !isTerminal(run.state) && run.summary.tasks.total ? "known so far" : null;
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
const PAGE = 50;

type List = { rows: Run[]; next: string | null };

// The list's order (sort=-created_at): newest first, then by ID.
const older = (a: Run, b: Run) => a.created_at < b.created_at || (a.created_at === b.created_at && a.id < b.id);

/** A refresh on a stream frame: the fresh first page, then the rows "Load more" added past it
 * (older than its last row) and their cursor. */
function refresh(shown: List | null, page: Page<Run>): List {
  const fresh = page.items ?? [];
  const last = fresh[fresh.length - 1];
  const ids = new Set(fresh.map((r) => r.id));
  const tail = shown && last && page.next ? shown.rows.filter((r) => !ids.has(r.id) && older(r, last)) : [];
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
  // Each change keeps the other param: the name filter lands 250 ms after typing, a click may come between.
  const setSearch = (change: { state?: string; q?: string }) =>
    navigate({ search: (prev) => runsSearch({ ...prev, ...change }), replace: true });
  const setFilter = (i: number) => setSearch({ state: FILTERS[i].states ? FILTERS[i].key : undefined });
  const server = useServer();
  const [typed, setTyped] = useState(q);
  // The q this page last wrote: a q from elsewhere (a link that drops it) re-seeds the box, while
  // the page's own write never trims what the user is still typing (CR-P3PARA-09).
  const written = useRef(q);
  const [list, setList] = useState<List | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const states = FILTERS[filter].states?.join(",");

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
      Promise.all([listRuns({ state: states, q, limit: PAGE }, signal), runsSummary(signal)])
        .then(([page, sum]) => {
          if (stale()) return;
          setList((shown) => (merge ? refresh(shown, page) : { rows: page.items ?? [], next: page.next ?? null }));
          setSummary(sum);
          setError(null);
        })
        .catch((e: Error) => stale() || setError(e.message));
    },
    [states, q],
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
    listRuns({ state: states, q, limit: PAGE, cursor: next }, signal)
      .then((page) => {
        if (signal.aborted) return;
        setList((shown) => ({ rows: [...(shown?.rows ?? []), ...(page.items ?? [])], next: page.next ?? null }));
      })
      .catch((e: Error) => signal.aborted || setError(e.message));
  };

  const total = count(summary, null);
  const filtered = filter !== 0 || q !== "";
  // "of N" only while the filter's total is known from the summary (ui-spec §4.11).
  const shownTotal = q === "" && summary ? count(summary, FILTERS[filter].states) : null;
  return (
    <div className="sp-runs">
      <PageHead
        section="runs"
        title="Runs"
        sub={
          <>
            <span>
              {total} {total === 1 ? "run" : "runs"}
            </span>
            <span>{count(summary, ACTIVE)} active</span>
            {server && <span>{headsWhere(server)}</span>}
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
      {runs === null && !error && <p className="sp-muted">Loading the runs…</p>}
      {runs?.length === 0 && (filtered ? <p className="sp-empty">No run matches these filters.</p> : <NoRuns />)}
      {!!runs?.length && (
        <div className="sp-table-wrap">
          <table className="sp-table">
            <thead>
              <tr>
                <th scope="col">Run</th>
                <th scope="col">State</th>
                <th scope="col">Workflow</th>
                <th scope="col">Tasks</th>
                <th scope="col" data-wide="">
                  Started
                </th>
                <th scope="col">Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td data-rail="" data-tone={tone(run.state)}>
                    <RunLink run={run} />
                    <br />
                    {run.origin === "cli-observed" && (
                      <span className="sp-chip">
                        <Icon path={ICONS.terminal} size={12} /> From a terminal
                      </span>
                    )}
                    <span className="sp-id">{shortId(run.id)}</span>
                  </td>
                  <td>
                    <StateWord state={run.state} />
                    <span className="sp-muted">{stateContext(run)}</span>
                  </td>
                  <td>
                    <Pipeline run={run} />
                  </td>
                  <td>
                    <TasksCell run={run} />
                  </td>
                  <td data-wide="">{when(run.started_at ?? run.created_at)}</td>
                  <td>{duration(run.started_at, run.ended_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!!runs?.length && (
        <p className="sp-foot-line">
          {shownTotal !== null ? `${runs.length} of ${shownTotal} runs` : `${runs.length} ${runs.length === 1 ? "run" : "runs"}`} ·
          newest first
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
