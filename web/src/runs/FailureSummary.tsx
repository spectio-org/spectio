import { Button } from "@mantine/core";
import type { ReactNode } from "react";
import type { Failure, Process, RunDetail, Scheduler, Task } from "../api";
import { ICONS, Icon } from "../icons";
import { useServer } from "../server";
import { CopyButton } from "./CopyMenu";
import type { Detail } from "./DetailSheet";
import { LogLines } from "./LogViewer";
import { bytes, nearLimit, seconds } from "./resources";
import { NearLimit } from "./RunState";
import { lastSegment, words } from "./stateWord";

// "Why it failed", one card per job that failed on its last attempt (P1 Task 32 on Task 29's
// `failures`; ui-spec §4.4 note 2026-10-28, Failure summary; boards LiteRunFailed, MLiteRunFailed):
// the attempt, the job ID, the exit code, the SLURM state and reason with where they came from,
// memory and time asked and used side by side, the engine's message unchanged, the last lines of
// the job's log, Open job files (the task sheet on its job log) and Copy work or launch directory.

const label = (f: Failure) => (f.tag ? `${lastSegment(f.process)} (${f.tag})` : lastSegment(f.process));

/** Where the SLURM facts came from, in words; "SLURM accounting unavailable" when nowhere. */
function sources(s: Scheduler, slurm: boolean, engine: string | null): string {
  const asking = s.accounting === "pending" ? "asking sacct" : slurm ? "SLURM accounting unavailable" : "not measured";
  const used =
    s.usage_source === "sacct"
      ? "from sacct"
      : s.usage_source === "trace"
        ? engine === "snakemake"
          ? "from the benchmark file"
          : "from the Nextflow trace"
        : asking;
  if (!slurm) return `used: ${used}`;
  const state =
    s.state_source === "sacct" ? "from sacct" : s.state_source === "engine_message" ? "from the Snakemake SLURM plugin's message" : asking;
  return [`SLURM state: ${state}`, s.reason && `Reason: ${s.reason}`, `used: ${used}`].filter(Boolean).join(" · ");
}

/** The task the sheet opens on: what the failure knows of it, its stage from its process. */
function asTask(f: Failure, processes: Process[]): Task {
  const s = f.scheduler;
  return {
    id: f.task_id,
    process: f.process,
    tag: f.tag,
    name: null,
    state: "failed",
    stage_id: processes.find((p) => p.process === f.process)?.stage_id ?? null,
    attempt_n: f.attempt_n,
    resources: {
      cpus: null,
      memory_bytes: s.req_mem_bytes,
      time_s: s.time_limit_s,
      realtime_s: s.elapsed_s,
      cpu_percent: null,
      peak_rss_bytes: s.max_rss_bytes,
      source: null,
    },
  };
}

function FailureCard({ run, failure, processes, slurm, onOpen }: { run: RunDetail; failure: Failure; processes: Process[]; slurm: boolean; onOpen: (d: Detail) => void }) {
  const s = failure.scheduler;
  const name = label(failure);
  const snakemake = run.workflow.engine === "snakemake";
  const task = asTask(failure, processes);
  const near = nearLimit(task.resources);
  const facts: [string, ReactNode][] = [
    ["Attempt", failure.attempt_n],
    [slurm ? "SLURM job" : "Job ID", <span className="sp-mono">{failure.native_id ?? "—"}</span>],
    ["Exit code", <span className="sp-mono">{failure.exit_code ?? "—"}</span>],
    [
      "Memory, asked · used",
      <>
        {bytes(s.req_mem_bytes)} · {bytes(s.max_rss_bytes)}
        <NearLimit on={near.memory} />
      </>,
    ],
    [
      "Time, limit · used",
      <>
        {seconds(s.time_limit_s)} · {seconds(s.elapsed_s)}
        <NearLimit on={near.time} />
      </>,
    ],
  ];
  return (
    <article className="sp-card sp-failure" aria-label={`${name}, attempt ${failure.attempt_n}`}>
      <p className="sp-failure-head">
        <strong>{lastSegment(failure.process)}</strong>
        {failure.tag && <span className="sp-mono sp-muted">{failure.tag}</span>}
        <span className="sp-grow" />
        {s.state && (
          <span className="sp-chip sp-mono" data-tone="failed">
            {s.state}
          </span>
        )}
      </p>
      <dl className="sp-facts sp-failure-facts">
        {facts.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {failure.message && <p className="sp-why-message sp-failure-message">{failure.message}</p>}
      {failure.log_tail && (
        <pre className="sp-code sp-log-tail sp-nowrap" tabIndex={0} aria-label={`${name}, last lines`}>
          <LogLines text={failure.log_tail} />
        </pre>
      )}
      <div className="sp-failure-actions">
        <Button variant="default" size="xs" leftSection={<Icon path={ICONS.file} size={14} />} aria-label={`Open the job files of ${name}`} onClick={() => onOpen({ kind: "task", task })}>
          Open job files
        </Button>
        {failure.work_dir && (
          <CopyButton
            text={failure.work_dir}
            label={snakemake ? "Copy launch directory" : "Copy work directory"}
            name={`Copy the ${snakemake ? "launch" : "work"} directory of ${name}`}
          />
        )}
        <span className="sp-muted">{sources(s, slurm, run.workflow.engine)}</span>
      </div>
    </article>
  );
}

/** The cards of the jobs that failed on their last attempt: the first 10 of `failures_total`. */
export function FailureSummary({ run, processes, onOpen }: { run: RunDetail; processes: Process[]; onOpen: (d: Detail) => void }) {
  const server = useServer();
  const slurm = server?.executor === "slurm";
  const w = words(run.workflow.engine);
  if (!run.failures.length) return null;
  return (
    <>
      <p className="sp-muted">
        Showing {run.failures.length} of {run.failures_total} failed {run.failures_total === 1 ? w.unit : w.units}.
      </p>
      {run.failures.map((failure) => (
        <FailureCard key={failure.task_id} run={run} failure={failure} processes={processes} slurm={slurm} onOpen={onOpen} />
      ))}
    </>
  );
}
