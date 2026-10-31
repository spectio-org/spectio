import "../runs/runs.css";
import { Button } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { type Run, type RunState, type Summary, listRuns, runsSummary } from "../api";
import { LiveStatus, useFrames } from "../live";
import { RunLink, StateWord, runName, stateContext, tasksText } from "../runs/RunState";
import { ACTIVE, NoRuns } from "../runs/RunsPage";
import { when } from "../runs/stateWord";

const CARD_ORDER: RunState[] = ["running", "queued", "cancelling", "failed", "succeeded", "cancelled"];

function greeting(now = new Date()) {
  const hour = now.getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

/** Home (P1 Task 20, LiteHome): counts by state, the active runs, the runs that ended recently and
 * the pipeline directories of the recent runs, refreshed from the stream. */
export function HomePage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [active, setActive] = useState<Run[]>([]);
  const [ended, setEnded] = useState<Run[]>([]);
  const [recent, setRecent] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const loads = useRef(0); // only the latest refresh is shown: an older one can land last

  useEffect(() => {
    document.title = "Home · Spectio";
  }, []);
  const load = useCallback(() => {
    const mine = ++loads.current;
    Promise.all([
      runsSummary(),
      listRuns({ state: ACTIVE.join(","), limit: 20 }),
      listRuns({ sort: "-ended_at", limit: 5 }),
      listRuns({ limit: 50 }),
    ])
      .then(([sum, a, e, r]) => {
        if (mine !== loads.current) return;
        setSummary(sum);
        setActive(a.items ?? []);
        setEnded(e.items ?? []);
        setRecent(r.items ?? []);
        setError(null);
      })
      .catch((e: Error) => mine === loads.current && setError(e.message));
  }, []);
  useEffect(load, [load]);
  useFrames(load);

  const groups = summary?.groups ?? [];
  const total = groups.reduce((n, g) => n + g.count, 0);
  const activeCount = groups.filter((g) => ACTIVE.includes(g.key)).reduce((n, g) => n + g.count, 0);
  const pipelines = [...new Map(recent.map((r) => [r.workflow.location, r])).values()].slice(0, 6);

  return (
    <div className="sp-runs">
      <header className="sp-head">
        <div>
          <h1 className="sp-page-title">{greeting()}</h1>
          <p className="sp-sub sp-page-sub">
            <span>
              {activeCount} active {activeCount === 1 ? "run" : "runs"}
            </span>
            <LiveStatus />
          </p>
        </div>
        <Button component={Link} to="/launch">
          Launch a workflow
        </Button>
      </header>
      {error && (
        <div role="alert" className="sp-empty">
          <p>The runs could not be read: {error}</p>
          <Button variant="default" onClick={load}>
            Retry
          </Button>
        </div>
      )}
      {summary === null && !error && <p className="sp-muted">Loading…</p>}
      {summary !== null && total === 0 && <NoRuns />}
      {total > 0 && (
        <>
          <ul className="sp-cards" aria-label="Runs by state">
            {CARD_ORDER.filter((s) => groups.some((g) => g.key === s && g.count > 0)).map((state) => (
              <li key={state} data-rail={state}>
                <StateWord state={state} />
                <strong>{groups.find((g) => g.key === state)?.count}</strong>
              </li>
            ))}
          </ul>
          <div className="sp-home-grid">
            <div className="sp-runs">
              <section className="sp-section" aria-labelledby="home-active">
                <h2 id="home-active">Active runs</h2>
                {active.length === 0 ? (
                  <p className="sp-muted">No run is active.</p>
                ) : (
                  <ul className="sp-list">
                    {active.map((run) => (
                      <li key={run.id} data-rail={run.state}>
                        <span>
                          <RunLink run={run} />
                          <span className="sp-muted">
                            {run.workflow.name ?? run.workflow.location} · started {when(run.started_at ?? run.created_at)}
                          </span>
                        </span>
                        <span>
                          <StateWord state={run.state} />
                          <span className="sp-muted">
                            {run.state === "running" ? `${tasksText(run)} tasks` : stateContext(run)}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <Link to="/runs">All runs</Link>
              </section>
              <section className="sp-section" aria-labelledby="home-ended">
                <h2 id="home-ended">Finished recently</h2>
                {ended.length === 0 ? (
                  <p className="sp-muted">No run has ended yet.</p>
                ) : (
                  <ul className="sp-list">
                    {ended.map((run) => (
                      <li key={run.id} data-rail={run.state}>
                        <span>
                          <StateWord state={run.state} /> <RunLink run={run} />
                          <span className="sp-muted">
                            {[run.workflow.name ?? run.workflow.location, stateContext(run)].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <span>{when(run.ended_at)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
            <section className="sp-card" aria-labelledby="home-pipelines">
              <h2 id="home-pipelines">Your pipelines</h2>
              <p className="sp-muted">Pipeline directories of your recent runs.</p>
              <ul className="sp-list">
                {pipelines.map((run) => (
                  <li key={run.workflow.location}>
                    <span>
                      {run.workflow.name ?? runName(run)} {run.workflow.version}
                      <span className="sp-mono sp-muted">{run.workflow.location}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
