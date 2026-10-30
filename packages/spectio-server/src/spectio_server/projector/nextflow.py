"""The Nextflow mapping of api §7.2, and the run's end on `onFlowComplete` (§7.1, §8.2).

A task is keyed by process + tag (synthesis §2ter); an attempt by its task, the launch and the
engine's `attempt` number. Attempt states only move forward. `handler.status` is never read:
`onTaskComplete` takes its state from the trace record's `status` (api §7.2).
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import insert, select, update

from spectio_sdk.events import NextflowFlowComplete, NextflowFlowCreate, NextflowTask
from spectio_server.ids import new_id
from spectio_server.projector.runs import ENGINE_ENDED, TERMINAL, Projection, failure_json
from spectio_server.store.schema import attempts, runs, tasks

HOOK_STATES = {
    "onTaskPending": "pending",
    "onTaskSubmit": "submitted",
    "onTaskStart": "running",
    "onTaskCached": "cached",
}
TRACE_STATES = {"COMPLETED": "succeeded", "FAILED": "failed", "ABORTED": "aborted"}
_RANK = {"pending": 0, "submitted": 1, "running": 2}  # every end state ranks 3 (api §7.2)


def project(p: Projection, hook: str, data: BaseModel) -> None:
    """Project one `nextflow.<hook>` event, already logged."""
    if isinstance(data, NextflowFlowCreate) and hook == "onFlowCreate":
        _flow_create(p, data)
    elif isinstance(data, NextflowTask) and hook != "onFlowError":  # onFlowError has no task
        if p.state not in TERMINAL:  # a late task event is logged only (api §8.2)
            _task(p, hook, data)
    elif isinstance(data, NextflowFlowComplete):
        _flow_complete(p, data)


def _flow_create(p: Projection, data: NextflowFlowCreate) -> None:
    if data.sessionId:
        p.set_launch(engine_session_id=data.sessionId)
    if data.nextflow:  # pinned at the first launch (api §7 `runs.engine_version`)
        p.conn.execute(
            update(runs)
            .where(runs.c.id == p.run_id, runs.c.engine_version.is_(None))
            .values(engine_version=data.nextflow)
        )


def _task(p: Projection, hook: str, data: NextflowTask) -> None:
    if not data.process:
        return
    if hook == "onTaskComplete":
        status = data.trace.status if data.trace else None
        state = TRACE_STATES.get(status) if isinstance(status, str) else None
    else:
        state = HOOK_STATES.get(hook)
    if state is None:
        return
    task_id = _task_id(p, data.process, data.tag)
    n = data.attempt or 1
    values: dict[str, Any] = {"state": state}
    if state == "failed":
        values["ignored"] = data.errorAction == "IGNORE"
        if data.errorAction == "TERMINATE":
            values["failure_class"] = "tool_error"
    if (code := _exit(data)) is not None:
        values["exit"] = code
    row = p.conn.execute(
        select(attempts.c.id, attempts.c.state).where(
            attempts.c.task_id == task_id, attempts.c.launch_n == p.launch_n, attempts.c.n == n
        )
    ).one_or_none()
    if row is None:
        p.conn.execute(
            insert(attempts).values(
                id=new_id("att"),
                created_at=p.now,
                task_id=task_id,
                n=n,
                launch_n=p.launch_n,
                **values,
            )
        )
    elif _RANK.get(state, 3) > _RANK.get(row.state, 3):
        p.conn.execute(update(attempts).where(attempts.c.id == row.id).values(**values))
    else:
        return  # a late event of a lower or equal rank: logged, no change
    p.sync_tasks(task_id)


def _task_id(p: Projection, process: str, tag: str | None) -> str:
    """The task of this process + tag in the run, created on first sight."""
    match = tasks.c.tag.is_(None) if tag is None else tasks.c.tag == tag
    found = p.conn.execute(
        select(tasks.c.id).where(
            tasks.c.run_id == p.run_id, tasks.c.process_or_rule == process, match
        )
    ).scalar_one_or_none()
    if found is not None:
        return str(found)
    task_id = new_id("tsk")
    p.conn.execute(
        insert(tasks).values(
            id=task_id,
            created_at=p.now,
            run_id=p.run_id,
            process_or_rule=process,
            tag=tag,
            state="not_scheduled",
        )
    )
    return task_id


def _exit(data: NextflowTask) -> int | None:
    if data.exitStatus is not None:
        return data.exitStatus
    raw = data.trace.exit if data.trace else None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.lstrip("-").isdigit():
        return int(raw)
    return None


def _flow_complete(p: Projection, data: NextflowFlowComplete) -> None:
    """The launch's end. A second completion of the same launch is logged only (api §8.2)."""
    if p.state in TERMINAL or p.head_state in ENGINE_ENDED:
        return
    p.set_launch(head_state="succeeded" if data.success else "failed")
    p.end_launch()
    if p.state == "cancelling":
        p.move("cancelled")
    elif data.success:
        p.move("succeeded")
    else:
        p.move("failed", _failure(p, data.errorMessage or ""))


def _failure(p: Projection, message: str) -> dict[str, Any]:
    """`tool_error` from the attempt whose `errorAction` is TERMINATE, else `engine_fault`."""
    culprit = p.conn.execute(
        select(attempts.c.task_id, attempts.c.n)
        .join(tasks, tasks.c.id == attempts.c.task_id)
        .where(
            tasks.c.run_id == p.run_id,
            attempts.c.launch_n == p.launch_n,
            attempts.c.failure_class == "tool_error",
        )
        .order_by(attempts.c.created_at, attempts.c.id)
        .limit(1)
    ).one_or_none()
    if culprit is None:
        return failure_json("engine_fault", message)
    return failure_json("tool_error", message, culprit.task_id, culprit.n)
