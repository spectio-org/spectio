"""`GET /me/notifications` and `POST /me/notifications:mark-read` in 0.0.1 (FU-P3-113, api §5.9).

No notification table: an item is derived from a run the store has, one that succeeded, failed,
was cancelled or waits at a gate (`awaiting_review`), at its `state_changed_at` (the server's
clock). Newest first, at most 50. The one principal's `notifications_read_at` is the mark: an
item newer than it is unread. Behind the session, as every route; `mark-read` is a write
(Origin and JSON body, dev-env §15.3 req. 7).
"""

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import Connection, func, select, type_coerce, update

from spectio_server.api import models
from spectio_server.api.runs_read import read
from spectio_server.store.runs import first
from spectio_server.store.schema import UTCDateTime, principals, runs
from spectio_server.store.writer import Writer

router = APIRouter(tags=["me"])

LIMIT = 50
KINDS = {
    "succeeded": "run_succeeded",
    "failed": "run_failed",
    "cancelled": "run_cancelled",
    "awaiting_review": "gate_waiting",
}
AT = type_coerce(
    func.coalesce(runs.c.state_changed_at, runs.c.ended_at, runs.c.created_at), UTCDateTime()
)
NOTIFYING = runs.c.state.in_(KINDS) & runs.c.deleted_at.is_(None)


class MarkReadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    up_to: AwareDatetime


def _read_at(conn: Connection) -> Any:
    who = principals.c.id == first(conn, principals)  # the one principal of 0.0.1
    return conn.execute(select(principals.c.notifications_read_at).where(who)).scalar()


def _answer(conn: Connection, after: AwareDatetime | None = None) -> dict[str, Any]:
    mark = _read_at(conn)
    query = select(runs.c.id, runs.c.name, runs.c.state, AT.label("at")).where(NOTIFYING)
    if after is not None:
        query = query.where(AT > after)
    rows = conn.execute(query.order_by(AT.desc(), runs.c.id.desc()).limit(LIMIT)).all()
    unread = select(func.count()).select_from(runs).where(NOTIFYING)
    if mark is not None:
        unread = unread.where(AT > mark)
    items = [
        {
            "id": f"{KINDS[row.state]}:{row.id}",
            "kind": KINDS[row.state],
            "run_id": row.id,
            "run_name": row.name,
            "at": row.at.isoformat(),
            "read": mark is not None and row.at <= mark,
        }
        for row in rows
    ]
    return {
        "items": items,
        "unread": conn.execute(unread).scalar_one(),
        "read_up_to": None if mark is None else mark.isoformat(),
    }


@router.get("/me/notifications", response_model=models.Notifications)
def notifications(
    request: Request, response: Response, after: AwareDatetime | None = None
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    with read(request) as conn:
        return _answer(conn, after)


def _mark(conn: Connection, up_to: AwareDatetime) -> dict[str, Any]:
    mark = _read_at(conn)
    if mark is None or up_to > mark:
        who = principals.c.id == first(conn, principals)
        conn.execute(update(principals).where(who).values(notifications_read_at=up_to))
    return _answer(conn)


@router.post("/me/notifications:mark-read", response_model=models.Notifications)
def mark_read(body: MarkReadIn, request: Request, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    writer: Writer = request.app.state.writer
    return writer.submit(lambda conn: _mark(conn, body.up_to)).result()
