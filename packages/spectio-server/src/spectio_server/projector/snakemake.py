"""The Snakemake mapping of api §7.2 (P1 Assumption 16), and the launch's end on the head's exit.

A task is keyed by rule + wildcards (synthesis §2ter), the wildcards as sorted `k=v` pairs joined
with ", " (no wildcard: no tag). `job_finished` and `job_error` carry the `jobid` only, so
`snakemake_jobs` keeps the task of each jobid in the launch.

Snakemake 9.27.1 logs `job_started` for the jobs it selects, then `job_info` as each one runs
(`scheduling/job_scheduler.py:333-338`; `snakemake-interface-executor-plugins` 9.4.0,
`executors/base.py:60-73,85-86,108-109`), and reports no separate submit. So `job_info` opens a
`running` attempt: the first for its task, or the next after a failed one, since a retried job
comes back with the same jobid and no attempt number (T2 note, row 16). `job_started` is logged
only. `job_finished` gives `succeeded`, `job_error` `failed`.

No engine event ends a Snakemake launch: its head's exit code does (`head_exit`). On a non-zero
exit the run's failure takes the text of the last `error` record, and blames the launch's last
failed job when no later attempt of its task ran.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import insert, select, update

from spectio_sdk.events import (
    SnakemakeJobError,
    SnakemakeJobFinished,
    SnakemakeJobInfo,
    SnakemakeProgress,
    SnakemakeRunInfo,
    SnakemakeWorkflowStarted,
)
from spectio_server.ids import new_id
from spectio_server.projector.runs import (
    OPEN_ATTEMPT_STATES,
    TERMINAL,
    Projection,
    failure_json,
)
from spectio_server.stages import freeze
from spectio_server.store.schema import (
    attempts,
    events,
    launches,
    runs,
    snakemake_jobs,
    tasks,
    workflow_versions,
    workflows,
)

ERROR_EVENT = "spectio.engine.snakemake.error"


def project(p: Projection, data: BaseModel) -> None:
    """Project one `snakemake.<kind>` event, already logged."""
    if isinstance(data, SnakemakeWorkflowStarted):
        p.set_started()
        p.pin_engine_version(data.snakemake_version)
        freeze.freeze(p, data.snakefile_main)
    elif isinstance(data, SnakemakeRunInfo):
        freeze.plan_jobs(p, data.stats)
    elif isinstance(data, SnakemakeProgress):  # the total grows past each checkpoint
        p.conn.execute(update(runs).where(runs.c.id == p.run_id).values(tasks_expected=data.total))
    elif p.state in TERMINAL:  # a late job event is logged only (api §8.2)
        return
    elif isinstance(data, SnakemakeJobInfo):
        _job_info(p, data)
    elif isinstance(data, SnakemakeJobFinished):
        _job_end(p, data.job_id, "succeeded")
    elif isinstance(data, SnakemakeJobError):
        _job_end(p, data.jobid, "failed")


def drives(p: Projection) -> bool:
    """True when the run's workflow is a Snakemake one: its head's exit ends the launch."""
    engine = p.conn.execute(
        select(workflows.c.engine)
        .join(workflow_versions, workflow_versions.c.workflow_id == workflows.c.id)
        .join(runs, runs.c.workflow_version_id == workflow_versions.c.id)
        .where(runs.c.id == p.run_id)
    ).scalar_one()
    return bool(engine == "snakemake")


def head_exit(p: Projection, exit_code: int) -> None:
    """End the launch on the head's exit code: 0 succeeds, anything else fails."""
    if p.state in TERMINAL:
        return
    # The engine's last record is its end; the clock only when it wrote none (inbox #79).
    p.event_time = p.conn.execute(
        select(events.c.engine_time)
        .where(events.c.run_id == p.run_id, events.c.engine_time.is_not(None))
        .order_by(events.c.seq.desc())
        .limit(1)
    ).scalar_one_or_none()
    p.move("running")  # a launch that wrote no event at all
    p.end_launch()
    if exit_code == 0:
        p.move("succeeded")
    else:
        p.move("failed", _failure(p, exit_code))


def _job_info(p: Projection, data: SnakemakeJobInfo) -> None:
    tag = ", ".join(f"{k}={v}" for k, v in sorted(data.wildcards.items())) or None
    task_id = p.task_id(data.rule_name, tag, None)
    key = (snakemake_jobs.c.launch_id == p.launch_id) & (snakemake_jobs.c.jobid == data.jobid)
    if not p.conn.execute(update(snakemake_jobs).where(key).values(task_id=task_id)).rowcount:
        p.conn.execute(
            insert(snakemake_jobs).values(launch_id=p.launch_id, jobid=data.jobid, task_id=task_id)
        )
    last = _last_attempt(p, task_id)
    if last is not None and last.state != "failed":
        return  # already running, or a re-announced job that has ended: no new attempt
    p.conn.execute(
        insert(attempts).values(
            id=new_id("att"),
            created_at=p.now,
            task_id=task_id,
            n=1 if last is None else last.n + 1,
            launch_n=p.launch_n,
            state="running",
        )
    )
    p.sync_tasks([task_id])


def _job_end(p: Projection, jobid: int, state: str) -> None:
    task_id = p.conn.execute(
        select(snakemake_jobs.c.task_id).where(
            snakemake_jobs.c.launch_id == p.launch_id, snakemake_jobs.c.jobid == jobid
        )
    ).scalar_one_or_none()
    if task_id is None:
        return  # an unknown job: logged, no change
    last = _last_attempt(p, task_id)
    if last is None or last.state not in OPEN_ATTEMPT_STATES:
        return  # a job already ended: logged, no change
    p.conn.execute(update(attempts).where(attempts.c.id == last.id).values(state=state))
    if state == "failed":  # on Snakemake, the culprit is the launch's last failed job
        p.set_launch(culprit_attempt_id=last.id)
    p.sync_tasks([task_id])


def _last_attempt(p: Projection, task_id: str) -> Any:
    return p.conn.execute(
        select(attempts.c.id, attempts.c.n, attempts.c.state)
        .where(attempts.c.task_id == task_id, attempts.c.launch_n == p.launch_n)
        .order_by(attempts.c.n.desc())
        .limit(1)
    ).one_or_none()


def _failure(p: Projection, exit_code: int) -> dict[str, Any]:
    """`tool_error` when the launch's last failed job is its task's last attempt, else
    `engine_fault`; the message is the last `error` record's text (already hidden, §14.1)."""
    payload = p.conn.execute(
        select(events.c.payload)
        .where(events.c.run_id == p.run_id, events.c.type == ERROR_EVENT)
        .order_by(events.c.seq.desc())
        .limit(1)
    ).scalar_one_or_none()
    message = (payload or {}).get("msg") or f"snakemake exited with code {exit_code}"
    culprit = p.conn.execute(
        select(attempts.c.id, attempts.c.task_id, attempts.c.n)
        .join(launches, launches.c.culprit_attempt_id == attempts.c.id)
        .join(tasks, tasks.c.id == attempts.c.task_id)
        .where(launches.c.id == p.launch_id, tasks.c.state == "failed")
    ).one_or_none()
    if culprit is None:
        return failure_json("engine_fault", message)
    p.conn.execute(
        update(attempts).where(attempts.c.id == culprit.id).values(failure_class="tool_error")
    )
    return failure_json("tool_error", message, culprit.task_id, culprit.n)
