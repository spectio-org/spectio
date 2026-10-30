"""The Nextflow mapping of api §7.2, and the run's end on `onFlowComplete` (§7.1, §8.2).

A task is keyed by process + tag (synthesis §2ter), or by process + Nextflow's task `name` when it
has no tag, so untagged instances of one process stay apart (that the name is stable across
retries is [to be validated], inbox #77); an attempt by its task, the launch and the engine's
`attempt` number. Attempt states only move forward. `handler.status` is never read:
`onTaskComplete` takes its state from the trace record's `status` (api §7.2).
"""

import re
from typing import Any

from pydantic import BaseModel
from sqlalchemy import insert, select, update

from spectio_sdk.events import NextflowFlowComplete, NextflowFlowCreate, NextflowTask
from spectio_server.ids import new_id
from spectio_server.projector.runs import TERMINAL, Projection, failure_json
from spectio_server.store.schema import attempts, launches, runs, tasks

HOOK_STATES = {
    "onTaskPending": "pending",
    "onTaskSubmit": "submitted",
    "onTaskStart": "running",
    "onTaskCached": "cached",
}
TRACE_STATES = {"COMPLETED": "succeeded", "FAILED": "failed", "ABORTED": "aborted"}
_RANK = {"pending": 0, "submitted": 1, "running": 2}  # every end state ranks 3 (api §7.2)
_INT = re.compile(r"-?[0-9]{1,19}")  # ASCII digits only: `str.isdigit` also takes "²"
_INT64 = range(-(2**63), 2**63)


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
    task_id = _task_id(p, data.process, data.tag, data.name)
    n = data.attempt or 1
    values: dict[str, Any] = {"state": state}
    terminated = state == "failed" and data.errorAction == "TERMINATE"
    if state == "failed":
        values["ignored"] = data.errorAction == "IGNORE"
    if terminated:
        values["failure_class"] = "tool_error"
    if (code := _exit(data)) is not None:
        values["exit"] = code
    row = p.conn.execute(
        select(attempts.c.id, attempts.c.state).where(
            attempts.c.task_id == task_id, attempts.c.launch_n == p.launch_n, attempts.c.n == n
        )
    ).one_or_none()
    if row is None:
        attempt_id = new_id("att")
        p.conn.execute(
            insert(attempts).values(
                id=attempt_id,
                created_at=p.now,
                task_id=task_id,
                n=n,
                launch_n=p.launch_n,
                **values,
            )
        )
    elif _RANK.get(state, 3) > _RANK.get(row.state, 3):
        attempt_id = row.id
        p.conn.execute(update(attempts).where(attempts.c.id == attempt_id).values(**values))
    else:
        return  # a late event of a lower or equal rank: logged, no change
    if terminated:  # the first one: seq order
        p.conn.execute(
            update(launches)
            .where(launches.c.id == p.launch_id, launches.c.culprit_attempt_id.is_(None))
            .values(culprit_attempt_id=attempt_id)
        )
    p.sync_tasks([task_id])


def _task_id(p: Projection, process: str, tag: str | None, name: str | None) -> str:
    """The task of this process + tag (+ name when untagged) in the run, created on first sight."""
    if tag is not None:
        match = tasks.c.tag == tag
    else:
        match = tasks.c.tag.is_(None) & (
            tasks.c.name.is_(None) if name is None else tasks.c.name == name
        )
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
            name=name,
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
    if isinstance(raw, str) and _INT.fullmatch(raw) and int(raw) in _INT64:
        return int(raw)
    return None


def _flow_complete(p: Projection, data: NextflowFlowComplete) -> None:
    """The launch's end. A second completion of the same launch is logged only (api §8.2): the
    first always leaves the run terminal, since ingest has already moved it out of `queued`."""
    if p.state in TERMINAL:
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
    """`tool_error` from the launch's culprit, its first TERMINATE failure, else `engine_fault`."""
    culprit = p.conn.execute(
        select(attempts.c.task_id, attempts.c.n)
        .join(launches, launches.c.culprit_attempt_id == attempts.c.id)
        .where(launches.c.id == p.launch_id)
    ).one_or_none()
    if culprit is None:
        return failure_json("engine_fault", message)
    return failure_json("tool_error", message, culprit.task_id, culprit.n)
