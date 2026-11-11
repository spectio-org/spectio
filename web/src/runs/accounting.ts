import { useEffect, useRef } from "react";
import type { Process } from "../api";

// Once a SLURM run has ended, its jobs are asked of sacct on a read of it and answered on a
// later read (`failure.task_resources`; schedulers §3.6), and no stream frame says so: the
// ended run's page reads again while a job is not measured yet, a bounded number of times
// (FU-P3-119, the login1 retest of inbox #146 item 10). sacct is called at most once a minute
// (`sacct.INTERVAL_S`), so 10 reads 30 s apart cover its first calls.
export const ACCOUNTING_READ_MS = 30_000;
export const ACCOUNTING_READS = 10;

/** Whether an ended job of a process has no measure yet. */
const unmeasured = (processes: Process[]) => processes.some((p) => p.efficiency && p.efficiency.measured < p.efficiency.jobs.done);

/** `read` again ACCOUNTING_READ_MS after each read of an ended run that still has an unmeasured
 * job, at most ACCOUNTING_READS times per run. A local run whose jobs have no measure stops there. */
export function useAccountingReads(read: () => void, runId: string, ended: boolean, processes: Process[]) {
  const reads = useRef({ runId, n: 0 });
  if (reads.current.runId !== runId) reads.current = { runId, n: 0 };
  const due = ended && unmeasured(processes) && reads.current.n < ACCOUNTING_READS;
  useEffect(() => {
    if (!due) return;
    const timer = setTimeout(() => {
      reads.current.n++;
      read();
    }, ACCOUNTING_READ_MS);
    return () => clearTimeout(timer);
  }, [due, processes, read]);
}
