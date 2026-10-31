import "../runs/runs.css";
import { Button } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { type Run, type RunState, type ServerVersion, type Summary, listRuns, runsSummary } from "../api";
import { ICONS, Icon } from "../icons";
import { LiveStatus, useFrames } from "../live";
import { failureText, Pipeline, RunLink, StateWord, runName, stateContext, tasksText } from "../runs/RunState";
import { NoRuns, RunCard } from "../runs/RunsPage";
import { ACTIVE, isTerminal, plural, tone, when, words } from "../runs/stateWord";
import { useServer } from "../server";
import { EngineMark } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";

const CARD_ORDER: RunState[] = ["running", "queued", "cancelling", "failed", "succeeded", "cancelled"];
/** The words of the active states in the subtitle, in the cards' order (UX-PAR-13). */
const ACTIVE_WORDS: Partial<Record<RunState, string>> = {
  running: "running",
  queued: "queued",
  cancelling: "cancelling",
  pausing: "pausing",
  paused: "paused",
  awaiting_review: "awaiting review",
};

function greeting(now = new Date()) {
  const hour = now.getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

/** "4 runs running, 1 queued and 1 cancelling"; "No run is active" at zero. */
export function activeLine(groups: Summary["groups"]): string {
  const parts = (Object.keys(ACTIVE_WORDS) as RunState[])
    .map((state) => [state, groups.find((g) => g.key === state)?.count ?? 0] as const)
    .filter(([, n]) => n > 0)
    .map(([state, n], i) => (i === 0 ? `${plural(n, "run", "runs")} ${ACTIVE_WORDS[state]}` : `${n} ${ACTIVE_WORDS[state]}`));
  if (!parts.length) return "No run is active";
  return parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

/** A count card's detail line, from the lists Home already holds (UX-PAR-12). */
function cardDetail(state: RunState, active: Run[], ended: Run[]): string | null {
  if (state === "running") {
    const hand = active.filter((r) => r.state === "running" && r.origin === "cli-observed").length;
    return hand ? `${hand} started from a terminal` : null;
  }
  if (state === "queued") return active.some((r) => r.state === "queued" && !r.head) ? "head not started yet" : null;
  if (state === "cancelling") return "stopping the engine";
  const latest = ended.find((r) => r.state === state);
  return latest ? `latest: ${runName(latest)}` : null;
}

/** An active run's context: "from a terminal · 288 / 384 tasks", or its state's context line. */
function activeContext(run: Run): string {
  const own = run.state === "running" ? `${tasksText(run)} ${words(run.workflow.engine).units}` : stateContext(run);
  return run.origin === "cli-observed" ? `from a terminal · ${own}` : own;
}

/** A finished run's context: its tasks, or why it failed (never blank, UX-PAR-16). */
function endedContext(run: Run): string {
  if (run.state === "failed") return failureText(run);
  if (run.state === "succeeded" && run.summary.tasks.total) return `${tasksText(run)} ${words(run.workflow.engine).units}`;
  return stateContext(run);
}

/** Where heads, tasks and run directories are, from `GET /version` (UX-PAR-11). */
function WhereRunsGo({ server }: { server: ServerVersion }) {
  const local = server.executor === "local";
  const executor = server.executor.toUpperCase();
  return (
    <FoldSection id="home-where" screen="home" icon={ICONS.server} title="Where your runs go" summary={`${server.node} · ${executor}`} card>
      <ul className="sp-where">
        <li>
          <strong>Server</strong> Spectio {server.version} on {server.node}, under your account {server.account}
        </li>
        <li>
          <strong>Heads</strong>{" "}
          {local
            ? `one process per run on ${server.node}, in its own session; Cancel stops it with signals`
            : `one tmux session per run on ${server.node}, named spectio-<run ID>; attach to it by hand at any time`}
        </li>
        <li>
          <strong>Tasks</strong>{" "}
          {local ? `run on ${server.node} by Nextflow or Snakemake themselves` : `sent to ${executor} by Nextflow or Snakemake themselves`}
        </li>
        <li>
          <strong>Run directories</strong> <span className="sp-mono">{server.runs_root}</span>
        </li>
      </ul>
    </FoldSection>
  );
}

/** Home (P1 Task 20, LiteHome): counts by state, the active runs, the runs that ended recently,
 * the pipeline directories of the recent runs and where runs go, refreshed from the stream. */
export function HomePage() {
  const server = useServer();
  const phone = usePhone();
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
  const pipelines = [...new Map(recent.map((r) => [r.workflow.location, r])).values()].slice(0, 6);

  return (
    <div className="sp-runs">
      <PageHead
        section="home"
        title={greeting()}
        sub={
          <>
            <span>{activeLine(groups)}</span>
            <LiveStatus />
          </>
        }
        action={
          <Button component={Link} to="/launch">
            Launch a workflow
          </Button>
        }
      />
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
            {CARD_ORDER.filter((s) => groups.some((g) => g.key === s && g.count > 0)).map((state) => {
              const n = groups.find((g) => g.key === state)?.count ?? 0;
              const detail = cardDetail(state, active, ended);
              return (
                <li key={state} data-rail="" data-tone={tone(state)}>
                  <Link
                    to="/runs"
                    search={{ state: isTerminal(state) ? state : "active" }}
                    aria-label={`${plural(n, "run", "runs")} ${ACTIVE_WORDS[state] ?? state}, show them`}
                  >
                    <StateWord state={state} />
                    <strong>{n}</strong>
                    {detail && <span className="sp-muted">{detail}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="sp-home-grid">
            <div className="sp-runs">
              <FoldSection id="home-active" screen="home" icon={ICONS.pulse} title="Active runs" summary={`${active.length} active`}>
                <Link to="/runs" className="sp-link sp-link-end">
                  All runs <Icon path={ICONS.arrowRight} size={14} />
                </Link>
                {active.length === 0 ? (
                  <p className="sp-muted">No run is active.</p>
                ) : phone ? (
                  <ul className="sp-run-cards" aria-label="Active runs">
                    {active.map((run) => (
                      <RunCard key={run.id} run={run} />
                    ))}
                  </ul>
                ) : (
                  <ul className="sp-list">
                    {active.map((run) => (
                      <li key={run.id} data-rail="" data-tone={tone(run.state)} className="sp-row">
                        <EngineMark engine={run.workflow.engine} size={22} />
                        <span>
                          <RunLink run={run} />
                          <span className="sp-muted">
                            {[run.workflow.name ?? run.workflow.location, run.workflow.version].filter(Boolean).join(" ")} · started{" "}
                            {when(run.started_at ?? run.created_at)}
                          </span>
                        </span>
                        <span>
                          <StateWord state={run.state} />
                          <span className="sp-muted">{activeContext(run)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </FoldSection>
              <FoldSection id="home-ended" screen="home" icon={ICONS.history} title="Finished recently" summary={`${ended.length} runs`}>
                {ended.length === 0 ? (
                  <p className="sp-muted">No run has ended yet.</p>
                ) : phone ? (
                  <ul className="sp-run-cards" aria-label="Finished recently">
                    {ended.map((run) => (
                      <RunCard key={run.id} run={run} />
                    ))}
                  </ul>
                ) : (
                  <ul className="sp-list sp-ended">
                    {ended.map((run) => (
                      <li key={run.id} data-rail="" data-tone={tone(run.state)} className="sp-row">
                        <span className="sp-ended-state">
                          <StateWord state={run.state} />
                        </span>
                        <EngineMark engine={run.workflow.engine} size={20} />
                        <span>
                          <RunLink run={run} />
                          <span className="sp-muted">
                            <span>{run.workflow.name ?? run.workflow.location}</span> · {endedContext(run)}
                          </span>
                        </span>
                        <span>{when(run.ended_at)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </FoldSection>
            </div>
            <div className="sp-runs">
              <FoldSection id="home-pipelines" screen="home" icon={ICONS.route} title="Your pipelines" summary={`${pipelines.length} directories`} card>
                <p className="sp-muted">Pipeline directories of your recent runs.</p>
                <ul className="sp-quick">
                  {pipelines.map((run) => (
                    <li key={run.workflow.location}>
                      <Pipeline run={run} size={18} />
                      <span className="sp-mono sp-muted">{run.workflow.location}</span>
                    </li>
                  ))}
                </ul>
              </FoldSection>
              {server && <WhereRunsGo server={server} />}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
