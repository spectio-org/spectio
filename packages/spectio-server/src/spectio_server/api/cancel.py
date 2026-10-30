"""`POST /runs/{id}:cancel` (P1 Task 18; api §5.1, §7.1).

From `queued` or `running` the run moves to `cancelling`, and a `cancel` command is queued for
its last launch: the runner writes `.spectio/cancel` before any signal (P1 Task 9, Assumption 4),
and the run becomes `cancelled` when its head is reported ended. `202` with the run; `200` with
it, unchanged, when it is already `cancelling` or terminal. A run started from a terminal is
monitor only: `422 not-in-this-version` (api §5.1 note of 2026-10-28).
"""

from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import Connection, insert, select

from spectio_server.api.problems import Problem
from spectio_server.api.runs_read import read, run_detail, run_row
from spectio_server.ids import new_id
from spectio_server.projector.runs import Projection
from spectio_server.store.runs import first
from spectio_server.store.schema import launches, principals, runner_commands
from spectio_server.store.writer import Writer

router = APIRouter()

CANCELLABLE = frozenset({"queued", "running"})  # api §5.1 also lists paused, awaiting_review


def _cancel(conn: Connection, run_id: str) -> int:
    run = run_row(conn, run_id)
    if run.origin == "cli-observed":
        raise Problem(
            422,
            "not-in-this-version",
            "Not in this version",
            "Spectio did not start this run's head, so it cannot cancel it in 0.0.1.",
        )
    if run.state not in CANCELLABLE:
        return 200
    launch_id = conn.execute(
        select(launches.c.id)
        .where(launches.c.run_id == run_id)
        .order_by(launches.c.n.desc())
        .limit(1)
    ).scalar_one()
    p = Projection.load(conn, launch_id)
    person = first(conn, principals)  # the one principal of 0.0.1 (sign-in: P1 Task 16)
    p.move("cancelling", source="api", actor_kind="person", actor_principal_id=person)
    p.finish()
    conn.execute(
        insert(runner_commands).values(
            id=new_id("cmd"),
            run_id=run_id,
            launch_id=launch_id,
            kind="cancel",
            payload={},
            state="pending",
            created_at=p.now,
            created_by=person,
        )
    )
    return 202


@router.post("/runs/{run_id}:cancel", status_code=202)
def cancel_run(request: Request, run_id: str, response: Response) -> dict[str, Any]:
    writer: Writer = request.app.state.writer
    response.status_code = writer.submit(lambda conn: _cancel(conn, run_id)).result()
    with read(request) as conn:
        return run_detail(conn, run_id)
