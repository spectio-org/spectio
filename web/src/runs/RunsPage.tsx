import { Button } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { type Run, type Summary, listRuns, runsSummary } from "../api";
import { LiveStatus, useFrames } from "../live";
import { RunLink, StateWord, stateContext, tasksText } from "./RunState";
import { duration, shortId, when } from "./stateWord";

export const ACTIVE = ["queued", "running", "pausing", "paused", "awaiting_review", "cancelling"];
const FILTERS: { label: string; states: string[] | null }[] = [
  { label: "All", states: null },
  { label: "Active", states: ACTIVE },
  { label: "Failed", states: ["failed"] },
  { label: "Succeeded", states: ["succeeded"] },
  { label: "Cancelled", states: ["cancelled"] },
];
const PAGE = 50;

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
  const [filter, setFilter] = useState(0);
  const [typed, setTyped] = useState("");
  const [q, setQ] = useState("");
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [next, setNext] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const states = FILTERS[filter].states?.join(",");

  useEffect(() => {
    document.title = "Runs · Spectio";
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => setQ(typed.trim()), 250);
    return () => clearTimeout(timer);
  }, [typed]);

  // The first page, or as many rows as are shown (a refresh keeps what "Load more" added).
  const load = useCallback(
    (shown = 0) => {
      const limit = Math.min(200, Math.max(PAGE, shown));
      Promise.all([listRuns({ state: states, q, limit }), runsSummary()])
        .then(([page, sum]) => {
          setRuns(page.items ?? []);
          setNext(page.next ?? null);
          setSummary(sum);
          setError(null);
        })
        .catch((e: Error) => setError(e.message));
    },
    [states, q],
  );
  useEffect(() => load(), [load]);
  useFrames(() => load(runs?.length ?? 0));

  const more = () =>
    listRuns({ state: states, q, limit: PAGE, cursor: next })
      .then((page) => {
        setRuns((shown) => [...(shown ?? []), ...(page.items ?? [])]);
        setNext(page.next ?? null);
      })
      .catch((e: Error) => setError(e.message));

  const total = count(summary, null);
  const filtered = filter !== 0 || q !== "";
  return (
    <div className="sp-runs">
      <header className="sp-head">
        <div>
          <h1 className="sp-page-title">Runs</h1>
          <p className="sp-sub sp-page-sub">
            <span>
              {total} {total === 1 ? "run" : "runs"}
            </span>
            <span>{count(summary, ACTIVE)} active</span>
            <LiveStatus />
          </p>
        </div>
        <Button component={Link} to="/launch">
          Launch a workflow
        </Button>
      </header>

      <div className="sp-filters">
        <input
          type="search"
          aria-label="Filter by run name"
          placeholder="Filter by run name"
          value={typed}
          onChange={(e) => setTyped(e.currentTarget.value)}
        />
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
                  <td data-rail={run.state}>
                    <RunLink run={run} />
                    <br />
                    {run.origin === "cli-observed" && <span className="sp-chip">From a terminal</span>}
                    <span className="sp-id">{shortId(run.id)}</span>
                  </td>
                  <td>
                    <StateWord state={run.state} />
                    <span className="sp-muted">{stateContext(run)}</span>
                  </td>
                  <td>
                    {run.workflow.name ?? run.workflow.location}
                    {run.workflow.version && <span className="sp-muted">{run.workflow.version}</span>}
                  </td>
                  <td>
                    {tasksText(run)}
                    {run.summary.tasks.failed > 0 && (
                      <span className="sp-bad">{run.summary.tasks.failed} failed</span>
                    )}
                  </td>
                  <td data-wide="">{when(run.started_at ?? run.created_at)}</td>
                  <td>{duration(run.started_at, run.ended_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
