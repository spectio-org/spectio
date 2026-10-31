"""The stored state of a stage (ui-spec §5.1.1, Order and state; api §7 `run_stages.state`)."""

from collections.abc import Mapping

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
