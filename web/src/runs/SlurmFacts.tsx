import { type ReactNode, useId } from "react";
import type { Efficiency, Slurm, SlurmAllocated, SlurmRequest, Task } from "../api";
import { bytes, isLow, isNear, percent, seconds } from "./resources";
import { Low, NearLimit } from "./RunState";

// A job's SLURM request and efficiency, in the task view of the detail sheet (ui-spec §4.4 note
// 2026-11-07; boards LiteTaskFiles, MLiteTaskFilesSheet, LiteTaskFilesStates L and M): the request
// as the engine asked, each field only when set; what sacct allocated when it differs; "Custom
// sbatch options set", never their text (SEC-P3T1-11); then the efficiency with its source, or why
// it is not there yet.

const SOURCES: Record<NonNullable<Efficiency["source"]>, string> = {
  sacct: "from sacct",
  trace: "from the Nextflow trace",
  benchmark: "from the Snakemake benchmark",
};
const REASONS: Record<NonNullable<Efficiency["reason"]>, string> = {
  local: "local run",
  accounting_off: "sacct not found or accounting off",
  no_job_id: "no SLURM job ID",
  not_found: "not in SLURM accounting",
  cached: "reused from an earlier run, no job ran",
  max_query_time_range: "the window is over the site's sacct limit (MaxQueryTimeRange)",
};

const memory = (r: SlurmRequest): string | null =>
  r.mem_bytes !== null ? bytes(r.mem_bytes) : r.mem_per_cpu_bytes !== null ? `${bytes(r.mem_per_cpu_bytes)} per CPU` : null;

function requested(r: SlurmRequest): [string, string | null][] {
  return [
    ["Partition", r.partition],
    ["Account", r.account],
    ["QOS", r.qos],
    ["CPUs", r.cpus === null ? null : String(r.cpus)],
    ["Memory", memory(r)],
    ["Time limit", r.time_limit_s === null ? null : seconds(r.time_limit_s)],
    ["GPUs or other gres", r.gres],
    ["Constraint", r.constraint],
    ["Nodes", r.nodes === null ? null : String(r.nodes)],
    ["Tasks", r.tasks === null ? null : String(r.tasks)],
  ];
}

/** Whether sacct's values differ from the request, on a field both have. */
function differs(r: SlurmRequest, a: SlurmAllocated): boolean {
  const pairs: [unknown, unknown][] = [
    [r.partition, a.partition],
    [r.account, a.account],
    [r.qos, a.qos],
    [r.cpus, a.ncpus],
    [r.mem_bytes, a.req_mem_bytes],
    [r.time_limit_s, a.time_limit_s],
  ];
  return pairs.some(([x, y]) => x !== null && y !== null && x !== y);
}

const allocated = (a: SlurmAllocated): string =>
  [
    a.partition,
    a.account,
    a.qos,
    a.ncpus === null ? null : `${a.ncpus} CPUs`,
    a.req_mem_bytes === null ? null : bytes(a.req_mem_bytes),
    a.time_limit_s === null ? null : seconds(a.time_limit_s),
    a.alloc_tres,
  ]
    .filter(Boolean)
    .join(" · ");

/** A label/value list; `variant` is the CSS class of its place (sheet or card). */
export function Facts({ facts, variant = "sp-sheet-facts" }: { facts: [string, ReactNode][]; variant?: string }) {
  return (
    <dl className={`sp-facts ${variant}`}>
      {facts.map(([name, value]) => (
        <div key={name}>
          <dt>{name}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id}>
      <h3 id={id} className="sp-sheet-h">
        {title}
      </h3>
      {children}
    </section>
  );
}

function SlurmBlock({ slurm }: { slurm: Slurm }) {
  const { request, allocated: given } = slurm;
  const facts: [string, ReactNode][] = requested(request).filter((f): f is [string, string] => f[1] !== null);
  if (given && differs(request, given)) {
    facts.push(["Allocated", <>{allocated(given)} <span className="sp-near">differs from the request</span></>]);
  }
  if (slurm.custom_options) facts.push(["Custom sbatch options set", "yes"]);
  return (
    <Block title="SLURM">
      {facts.length ? <Facts facts={facts} /> : <p className="sp-muted">The engine set no request of its own.</p>}
    </Block>
  );
}

function EfficiencyBlock({ task, e }: { task: Task; e: Efficiency }) {
  const r = task.resources;
  const elapsed = `${seconds(e.elapsed_s ?? r.realtime_s)} of ${seconds(r.time_s)}`;
  const measured = e.cpu !== null || e.mem !== null;
  const ratios = (
    <>
      {percent(e.cpu)}
      <Low on={isLow(e.cpu)} /> · {percent(e.mem)}
      <Low on={isLow(e.mem)} />
      <NearLimit on={isNear(e.mem)} />
      {e.source && ` · ${SOURCES[e.source]}`}
    </>
  );
  const facts: [string, ReactNode][] = [];
  if (e.state !== "running" && measured) facts.push(["CPU · memory", ratios]);
  facts.push(["Elapsed · time limit", elapsed]);
  if (e.state !== "running") facts.push(["Peak · memory asked", `${bytes(e.peak_rss_bytes ?? r.peak_rss_bytes)} of ${bytes(r.memory_bytes)}`]);
  const status =
    e.state === "running"
      ? "Measured when the job ends"
      : e.state === "pending_accounting"
        ? "Waiting for SLURM accounting (sacct)"
        : e.state === "unavailable"
          ? `No accounting for this job${e.reason ? ` (${REASONS[e.reason]})` : ""}`
          : null;
  return (
    <Block title="Efficiency">
      {status && <p className="sp-muted">{status}</p>}
      <Facts facts={facts} />
    </Block>
  );
}

/** The SLURM block (none on a local run) and the Efficiency block of one job. */
export function SlurmFacts({ task }: { task: Task }) {
  return (
    <>
      {task.slurm && <SlurmBlock slurm={task.slurm} />}
      {task.efficiency && <EfficiencyBlock task={task} e={task.efficiency} />}
    </>
  );
}
