import { useEffect, useRef, useState } from "react";
import type { Process } from "../api";

// Once a SLURM run has ended, its jobs are asked of sacct on a read of it and answered on a
// later read (`failure.task_resources`; schedulers §3.6), and no stream frame says so: the
// ended run's page reads again while a job is not measured yet, a bounded number of times
// (FU-P3-119, the login1 retest of inbox #146 item 10). sacct is called at most once a minute
// (`sacct.INTERVAL_S`), so 10 reads 30 s apart cover its first calls.
export const ACCOUNTING_READ_MS = 30_000;
export const ACCOUNTING_READS = 10;

/** Whether an ended job sacct has not answered yet: not `measured < jobs.done`, which a resumed
 * run's cached tasks keep true and a measured failed job can hide (CR-P3FU119-01). */
const unmeasured = (processes: Process[]) => processes.some((p) => (p.efficiency?.pending_accounting ?? 0) > 0);

/** `read` again ACCOUNTING_READ_MS after each read of an ended run that still has a job waiting
 * for sacct, at most ACCOUNTING_READS times per run. A read that fails counts and is tried again
 * (CR-P3FU119-02). */
export function useAccountingReads(read: () => void, runId: string, ended: boolean, processes: Process[]) {
  const reads = useRef({ runId, n: 0 });
  if (reads.current.runId !== runId) reads.current = { runId, n: 0 };
  const [fired, setFired] = useState(0); // the next timer follows each read, whatever it gave
  const due = ended && unmeasured(processes) && reads.current.n < ACCOUNTING_READS;
  useEffect(() => {
    if (!due) return;
    const timer = setTimeout(() => {
      reads.current.n++;
      read();
      setFired((f) => f + 1);
    }, ACCOUNTING_READ_MS);
    return () => clearTimeout(timer);
  }, [due, fired, read]);
}
