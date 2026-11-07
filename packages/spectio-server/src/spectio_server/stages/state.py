"""The stored state of a stage (ui-spec §5.1.1, Order and state; api §7 `run_stages.state`)."""

from collections.abc import Mapping
from dataclasses import dataclass

from spectio_server.projector.runs import TERMINAL

STARTED = ("running", "succeeded", "failed", "cached", "stored", "aborted")
OPEN = ("not_scheduled", "pending", "submitted", "running")


def stage_state(counts: Mapping[str, int], ended: bool, run_state: str, failed_here: bool) -> str:
    """The state of a stage from its task counts (state → n). `ended`: every process of the
    stage has ended (Nextflow `onProcessTerminate`), or every rule has no job left (Snakemake);
    `failed_here`: the run failed on one of the stage's tasks.

    `running` from the first task that started; `completed` once it has ended with no task left
    open; `skipped` when it ended with no task; on a run that ended, `failed` when the run failed
    on one of its tasks, and also for a stage still under way when the run stopped, which has no
    state of its own (§7; the run detail shows it Stopped, ui-spec §4.4).
    """
    total = sum(counts.values())
    started = any(counts.get(s, 0) for s in STARTED)
    open_ = any(counts.get(s, 0) for s in OPEN)
    if run_state in TERMINAL:
        if failed_here:
            return "failed"
        if not started:
            return "skipped"
        if run_state == "succeeded" or (ended and not open_):
            return "completed"
        return "failed"
    if ended and total == 0:
        return "skipped"
    if ended and not open_:
        return "completed"
    return "running" if started else "not_started"


# --- Processes and rules (P1 Task 34; ui-spec §5.2; api §5 note of 2026-11-07) ---------------

DONE = ("succeeded", "cached", "stored")
RUNNING = ("submitted", "running")


def checkpoint_open(counts: Mapping[str, int], jobs_planned: int | None, run_state: str) -> bool:
    """A checkpoint rule is open while the run is under way and it has a job left: one not
    ended, or fewer done than Snakemake planned."""
    if run_state in TERMINAL:
        return False
    done = sum(counts.get(s, 0) for s in DONE)
    return any(counts.get(s, 0) for s in OPEN) or done < (jobs_planned or 0)


@dataclass(frozen=True)
class RunFacts:
    """What a process's status reads of its run: the engine and state; on Snakemake whether
    `run_info` came, the rules of the rule graph, and whether a checkpoint is open."""

    engine: str | None
    state: str
    planned: bool = False
    rulegraph: frozenset[str] = frozenset()
    checkpoint_open: bool = False


def process_status(
    name: str, counts: Mapping[str, int], ended: bool, jobs_planned: int | None, run: RunFacts
) -> str:
    """A process's or rule's `status` (api §5 note of 2026-11-07). With tasks: `running` while
    one runs or more are to come, then `failed`, `stopped` or `done`. Without: Nextflow's
    `no_tasks` once `onProcessTerminate` came; Snakemake's `pending` while jobs are planned or
    before `run_info`, then `up_to_date` (in the rule graph, or nothing to be done),
    `awaiting_checkpoint` while a checkpoint is open, else `not_needed` (ui-spec §5.2). A
    process left with work on a run that ended is `stopped`."""
    terminal = run.state in TERMINAL
    smk = run.engine == "snakemake"
    if sum(counts.values()):
        done = sum(counts.get(s, 0) for s in DONE)
        waiting = any(counts.get(s, 0) for s in ("pending", "not_scheduled"))
        more = done < (jobs_planned or 0) if smk else not ended
        if any(counts.get(s, 0) for s in RUNNING) or (
            not terminal and ((waiting and done) or more)
        ):
            return "running"
        if not terminal and waiting:
            return "pending"
        if counts.get("failed", 0):
            return "failed"
        if counts.get("aborted", 0) or waiting or (more and run.state != "succeeded"):
            return "stopped"
        return "done"
    if not smk:
        return "no_tasks" if ended else "stopped" if terminal else "pending"
    if not jobs_planned and not run.planned and run.state == "succeeded":
        return "up_to_date"  # no `run_info`: nothing was to be done
    if jobs_planned or not run.planned:
        return "stopped" if terminal else "pending"
    if name in run.rulegraph:
        return "up_to_date"
    return "awaiting_checkpoint" if run.checkpoint_open else "not_needed"
