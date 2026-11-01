"""The 0.0.1 read API (P1 Task 18; api §5 note of 2026-10-28, §7).

`GET /runs` and `GET /runs/{id}` return the run with its computed fields of api §7, as far as
0.0.1 has them: `workflow`, `head` (the last launch's, `null` until its head started) and
`summary.tasks`, where `total` is `tasks_expected` when set, else the sum of `task_counts`
(no `tasks_total` column, inbox #78). Lists are `{items, next}` (api §4.1), `next` an opaque
cursor. Every read opens its own connection on the writer's engine: SQLite WAL readers never wait
for the writer. The run's `Location` of `POST /runs` is served here (inbox #86, rule 9).
"""

import base64
import binascii
import json
import os
import pwd
import socket
from datetime import datetime
from importlib.metadata import version
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy import Connection, Row, Select, and_, func, select

from spectio.config import Settings
from spectio.runner.rundir import RUN_ID
from spectio_server.api import models
from spectio_server.api.problems import Invalid, not_found
from spectio_server.failure import Context, build_failures, task_resources
from spectio_server.files.pool import READ_TIMEOUT_S
from spectio_server.stages.freeze import FROZEN as STAGES_FROZEN
from spectio_server.store.schema import (
    RUN_STATES,
    TASK_STATES,
    attempts,
    events,
    launches,
    run_inputs,
    run_processes,
    run_stages,
    runner_commands,
    runs,
    tasks,
    workflow_versions,
    workflows,
)

router = APIRouter()

Limit = Annotated[int, Query(ge=1, le=200)]
Cursor = Annotated[str | None, Query(max_length=512)]
DONE_STATES = ("succeeded", "cached", "stored")  # the ends of a task that ran or was reused

_last_n = (
    select(launches.c.run_id, func.max(launches.c.n).label("n"))
    .group_by(launches.c.run_id)
    .subquery()
)
_RUN_COLUMNS = (
    runs.c.id,
    runs.c.name,
    runs.c.state,
    runs.c.origin,
    runs.c.created_at,
    runs.c.started_at,
    runs.c.ended_at,
    runs.c.failure,
    runs.c.task_counts,
    runs.c.tasks_expected,
    runs.c.engine_version,
    workflows.c.engine,
    workflows.c.location,
    workflows.c.name.label("workflow_name"),
    workflow_versions.c.version.label("workflow_version"),
    launches.c.head_native_id,
    launches.c.exited_at,
    launches.c.exit_code,
)


def _runs_query() -> Select[Any]:
    return (
        select(*_RUN_COLUMNS)
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .outerjoin(_last_n, _last_n.c.run_id == runs.c.id)
        .outerjoin(launches, and_(launches.c.run_id == runs.c.id, launches.c.n == _last_n.c.n))
    )


def read(request: Request) -> Connection:
    return request.app.state.writer.engine.connect()  # type: ignore[no-any-return]


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _profiles(conn: Connection, run_ids: list[str]) -> dict[str, list[str]]:
    """The profiles of each run's `launch` command (the store keeps them nowhere else)."""
    rows = conn.execute(
        select(runner_commands.c.run_id, runner_commands.c.payload).where(
            runner_commands.c.kind == "launch", runner_commands.c.run_id.in_(run_ids)
        )
    )
    return {r.run_id: list((r.payload or {}).get("profiles", [])) for r in rows}


def _stage_modes(conn: Connection, run_ids: list[str]) -> dict[str, str]:
    """`summary.stage_mode` (api §7): `declared` or `detected` from the run's frozen stages,
    `quarters` when it has none (the progress bar's four quarters, ui-spec §5.1.1)."""
    rows = conn.execute(
        select(run_stages.c.run_id, run_stages.c.source)
        .where(run_stages.c.run_id.in_(run_ids))
        .distinct()
    )
    return {r.run_id: r.source for r in rows}  # one source per run: the freeze writes one


def run_json(row: Row[Any], profiles: list[str], stage_mode: str | None = None) -> dict[str, Any]:
    counts: dict[str, int] = row.task_counts or {}
    total = row.tasks_expected if row.tasks_expected is not None else sum(counts.values())
    head = None
    if row.head_native_id is not None:  # the head started (a terminal's run: Task 25)
        observed = row.origin == "cli-observed"
        head = {
            "session": None if observed else row.head_native_id,
            "node": socket.gethostname(),  # the local launcher's node: the server's
            "alive": row.exited_at is None,
            "exit_code": row.exit_code,
        }
    return {
        "id": row.id,
        "name": row.name,
        "state": row.state,
        "origin": row.origin,
        "created_at": _iso(row.created_at),
        "started_at": _iso(row.started_at),
        "ended_at": _iso(row.ended_at),
        "workflow": {
            "engine": row.engine,
            "engine_version": row.engine_version,
            "location": row.location,
            "name": row.workflow_name,
            "version": row.workflow_version,
        },
        "profiles": profiles,
        "failure": row.failure,
        "head": head,
        "task_counts": counts,
        "summary": {
            "tasks": {
                "done": sum(counts.get(s, 0) for s in DONE_STATES),
                "total": total,
                "failed": counts.get("failed", 0),
                "cached": counts.get("cached", 0),
            },
            "last_failure": row.failure,
            "stage_mode": stage_mode or "quarters",
        },
    }


def run_row(conn: Connection, run_id: str) -> Row[Any]:
    """The run's row, or 404 `not-found`."""
    row = None
    if RUN_ID.fullmatch(run_id):
        row = conn.execute(_runs_query().where(runs.c.id == run_id)).one_or_none()
    if row is None:
        raise not_found(f"no run {run_id[:64]!r}")
    return row


def context(request: Request) -> Context:
    """What a view reads files and accounting with (P1 Task 29)."""
    state = request.app.state
    return Context(state.settings.runs_root, state.files, state.accounting, READ_TIMEOUT_S)


def run_detail(conn: Connection, run_id: str, ctx: Context) -> dict[str, Any]:
    """The run, with its failures (P1 Task 29): each job that failed on its last attempt."""
    row = run_row(conn, run_id)
    found = run_json(
        row, _profiles(conn, [run_id]).get(run_id, []), _stage_modes(conn, [run_id]).get(run_id)
    )
    frozen = conn.execute(
        select(events.c.payload).where(events.c.run_id == run_id, events.c.type == STAGES_FROZEN)
    ).scalar()
    note = (frozen or {}).get("note")
    params = conn.execute(
        select(run_inputs.c.content)
        .where(run_inputs.c.run_id == run_id, run_inputs.c.kind == "params")
        .order_by(run_inputs.c.version.desc())
        .limit(1)
    ).scalar()
    failures, total = build_failures(conn, run_id, row.engine, row.failure, ctx)
    return {
        **found,
        "params": params or {},
        "stages_note": note if isinstance(note, str) else None,
        "failures": failures,
        "failures_total": total,
    }


# --- Cursors: base64url of [sort value, id], or of the id alone when it is the sort key -----


def _encode(value: Any) -> str:
    raw = json.dumps(value)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode(cursor: str, timestamp: bool) -> tuple[Any, str]:
    try:
        found = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        if not timestamp:
            if not isinstance(found, str):
                raise ValueError("not an ID")
            return found, found
        value, id_ = found
        if not isinstance(id_, str):
            raise ValueError("no ID")
        at = datetime.fromisoformat(value)
        if at.utcoffset() is None:  # the store takes aware times only
            raise ValueError("naive")
        return at, id_
    except (ValueError, TypeError, binascii.Error):
        raise Invalid("cursor", "not a cursor this server gave") from None


def _page(
    query: Select[Any],
    key: Any,
    id_col: Any,
    cursor: str | None,
    limit: int,
    descending: bool,
    timestamp: bool,
) -> Select[Any]:
    if cursor is not None:
        value, id_ = _decode(cursor, timestamp)
        if not timestamp:  # the ID is the key (tasks): one comparison
            query = query.where(key < value if descending else key > value)
        elif descending:
            query = query.where((key < value) | ((key == value) & (id_col < id_)))
        else:
            query = query.where((key > value) | ((key == value) & (id_col > id_)))
    order = (key.desc(), id_col.desc()) if descending else (key.asc(), id_col.asc())
    return query.order_by(*order).limit(limit + 1)


def _states(value: str | None, allowed: tuple[str, ...]) -> list[str] | None:
    if value is None:
        return None
    found = value.split(",")
    bad = [s for s in found if s not in allowed]
    if bad:
        raise Invalid("state", f"not a state: {', '.join(repr(b[:32]) for b in bad[:5])}")
    return found


# --- Routes ----------------------------------------------------------------------------------


@router.get("/runs", response_model=models.RunList)
def list_runs(
    request: Request,
    state: Annotated[str | None, Query(max_length=200)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: Literal["-created_at", "-ended_at"] = "-created_at",
    limit: Limit = 50,
    cursor: Cursor = None,
) -> dict[str, Any]:
    """Newest first by `created_at`, or by `ended_at` (`sort=-ended_at`: ended runs only)."""
    states = _states(state, RUN_STATES)
    key = runs.c.ended_at if sort == "-ended_at" else runs.c.created_at
    query = _runs_query()
    if sort == "-ended_at":
        query = query.where(runs.c.ended_at.is_not(None))
    if states is not None:
        query = query.where(runs.c.state.in_(states))
    if q:  # a prefix, compared as text: no LIKE pattern
        query = query.where(func.substr(runs.c.name, 1, len(q)) == q)
    query = _page(query, key, runs.c.id, cursor, limit, descending=True, timestamp=True)
    with read(request) as conn:
        rows = conn.execute(query).all()
        page = [r.id for r in rows[:limit]]
        profiles, modes = _profiles(conn, page), _stage_modes(conn, page)
    items = [run_json(r, profiles.get(r.id, []), modes.get(r.id)) for r in rows[:limit]]
    last = rows[limit - 1] if len(rows) > limit else None
    next_ = None if last is None else _encode([getattr(last, key.name).isoformat(), last.id])
    return {"items": items, "next": next_}


@router.get("/runs:summary", response_model=models.Summary)
def runs_summary(request: Request, group_by: Literal["state"] = "state") -> dict[str, Any]:
    """Counts by state over all the runs, with no time window (0.0.1: no `since`, `project`)."""
    with read(request) as conn:
        rows = conn.execute(select(runs.c.state, func.count()).group_by(runs.c.state)).all()
    return {"groups": [{"key": key, "count": n} for key, n in rows]}


@router.get("/version", response_model=models.ServerVersion)
def server_version(request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    try:
        account = pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        account = str(os.getuid())
    return {
        "version": version("spectio"),
        "node": socket.gethostname(),
        "runs_root": str(settings.runs_root),
        "account": account,
        "executor": settings.executor,
    }


@router.get("/runs/{run_id}", response_model=models.RunDetail)
def get_run(request: Request, run_id: str) -> dict[str, Any]:
    with read(request) as conn:
        return run_detail(conn, run_id, context(request))


@router.get("/runs/{run_id}/processes", response_model=models.ProcessList)
def list_processes(request: Request, run_id: str) -> dict[str, Any]:
    """One item per process or rule: those the projector recorded (`onProcessCreate`, the rule
    files at the freeze, a first task), in that order, with the stage they froze with; then any
    known from tasks only (a database from before P1 Task 27), in their first task's order."""
    with read(request) as conn:
        run_row(conn, run_id)
        mine = tasks.c.run_id == run_id
        known = conn.execute(
            select(run_processes.c.name, run_processes.c.stage_id)
            .where(run_processes.c.run_id == run_id)
            .order_by(run_processes.c.position)
        ).all()
        from_tasks = conn.execute(
            select(tasks.c.process_or_rule, func.max(tasks.c.stage_id))
            .where(mine)
            .group_by(tasks.c.process_or_rule)
            .order_by(func.min(tasks.c.id))
        ).all()
        counts = conn.execute(
            select(tasks.c.process_or_rule, tasks.c.state, func.count())
            .where(mine)
            .group_by(tasks.c.process_or_rule, tasks.c.state)
        ).all()
        retries: dict[str, int] = dict(
            conn.execute(
                select(tasks.c.process_or_rule, func.count())
                .join(attempts, attempts.c.task_id == tasks.c.id)
                .where(mine, attempts.c.n > 1)
                .group_by(tasks.c.process_or_rule)
            ).all()
        )
    by_process: dict[str, dict[str, int]] = {}
    for process, state, n in counts:
        by_process.setdefault(process, {})[state] = n
    order: dict[str, str | None] = dict(known)
    for process, stage_id in from_tasks:
        order.setdefault(process, stage_id)
    return {
        "items": [
            {
                "process": process,
                "stage_id": stage_id,
                "counts": by_process.get(process, {}),
                "retries": retries.get(process, 0),
            }
            for process, stage_id in order.items()
        ]
    }


@router.get("/runs/{run_id}/stages", response_model=models.StageList)
def list_stages(request: Request, run_id: str) -> dict[str, Any]:
    with read(request) as conn:
        run_row(conn, run_id)
        rows = conn.execute(
            select(run_stages).where(run_stages.c.run_id == run_id).order_by(run_stages.c.position)
        ).all()
    return {
        "items": [
            {
                "id": r.stage_id,
                "position": r.position,
                "name": r.name,
                "source": r.source,
                "state": r.state,
                "task_counts": r.task_counts or {},
            }
            for r in rows
        ]
    }


@router.get("/runs/{run_id}/tasks", response_model=models.TaskList)
def list_tasks(
    request: Request,
    run_id: str,
    state: Annotated[str | None, Query(max_length=200)] = None,
    process: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> dict[str, Any]:
    """The run's tasks in first-seen order (by ID)."""
    states = _states(state, TASK_STATES)
    query = select(tasks).where(tasks.c.run_id == run_id)
    if states is not None:
        query = query.where(tasks.c.state.in_(states))
    if process is not None:
        query = query.where(tasks.c.process_or_rule == process)
    query = _page(query, tasks.c.id, tasks.c.id, cursor, limit, descending=False, timestamp=False)
    with read(request) as conn:
        run = run_row(conn, run_id)
        rows = conn.execute(query).all()[: limit + 1]
        page = [r.id for r in rows[:limit]]
        resources = task_resources(conn, run_id, run.engine, page, context(request))
    items = [
        {
            "id": r.id,
            "process": r.process_or_rule,
            "tag": r.tag,
            "name": r.name,
            "state": r.state,
            "stage_id": r.stage_id,
            "attempt_n": resources[r.id][0],
            "resources": resources[r.id][1],
        }
        for r in rows[:limit]
    ]
    next_ = _encode(rows[limit - 1].id) if len(rows) > limit else None
    return {"items": items, "next": next_}
