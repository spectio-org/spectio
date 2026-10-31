import { useEffect, useId, useState } from "react";
import { type Run, listRuns } from "../api";
import { PipelineMark } from "../shell/EngineMark";

// "Try a test pipeline" (P3-parD, Thomas 2026-10-31: "pas de wf par défaut de test dans launch pour
// tester"): the pipelines this server ran recently, newest first, from GET /runs; nothing invented.
// With none, a link to the docs that say how to get the synthetic test pipelines. A server-side list
// of example pipelines would be an API change (a follow-up).

const DOCS = "https://spectio.pages.dev/specs/dev-environment-and-testing/#101-synthetic-scenario-pipelines-testspipelinessynthetic";

/** The distinct pipeline locations of `runs` (newest first, as GET /runs sorts them), at most five. */
export function recentPipelines(runs: Run[]): Run[] {
  const seen = new Set<string>();
  return runs.filter((r) => !seen.has(r.workflow.location) && seen.add(r.workflow.location)).slice(0, 5);
}

/** The server's recent runs, read once; null while loading, or when they cannot be read. */
export function useRecentRuns(): Run[] | null {
  const [runs, setRuns] = useState<Run[] | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    listRuns({ limit: 50 }, controller.signal)
      .then((page) => setRuns(page.items ?? []))
      .catch(() => undefined); // the list is a shortcut: without it, the field still works
    return () => controller.abort();
  }, []);
  return runs;
}

export function TryPipelines({ runs, onPick }: { runs: Run[] | null; onPick: (location: string) => void }) {
  const id = useId();
  if (runs === null) return null;
  const pipelines = recentPipelines(runs);
  if (!pipelines.length) {
    return (
      <p className="launch-try-none">
        No pipeline has run on this server yet.{" "}
        <a href={DOCS} target="_blank" rel="noopener noreferrer">
          How to get the synthetic test pipelines<span className="sp-sr"> (opens in a new tab)</span>
        </a>
      </p>
    );
  }
  return (
    <div className="launch-try" role="group" aria-labelledby={id}>
      <span id={id} className="launch-try-label">
        Try a test pipeline
      </span>
      {pipelines.map((run) => {
        const w = run.workflow;
        const name = w.name ?? w.location;
        return (
          <button key={w.location} type="button" className="launch-try-item" aria-label={`Use ${name}, ${w.location}`} onClick={() => onPick(w.location)}>
            <PipelineMark engine={w.engine} name={w.name} size={18} />
            <span className="launch-try-name">{name}</span>
            <span className="launch-try-where">{w.location}</span>
          </button>
        );
      })}
    </div>
  );
}
