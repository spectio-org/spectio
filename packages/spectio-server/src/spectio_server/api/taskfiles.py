"""`GET /tasks/{id}/attempts/{n}/files` and `GET …/files/{name}`: each job's files (P1 Task 28;
api §5 note of 2026-10-28, Job files; architecture §13.7; dev-env §15.3 req. 13).

The listing names every file the attempt has or may have, with its state; a read returns the
last 64 KiB as `text/plain`, `?tail=` bytes (at most 1 MiB), or one `Range` (at most 1 MiB, 206).
What may be read and how is `files.taskfiles`; this module reads the attempt's row, runs the
file system part in the file pool (`app.state.files`) with `READ_TIMEOUT_S`, and maps refusals
to problems: `422 file-not-allowed`, `404 log-not-found`, `410 log-cleaned`, `415 binary-file`,
and `503 runner-offline` when the file system did not answer in time.

`n` is the attempt number the task's attempts show; when a resumed run has an attempt `n` in
more than one launch, the latest launch's is served (assumed, inbox #94). A `Content-Range`
counts the file's bytes, while the body has its escape sequences removed (and, for
`.command.run`, counts the bytes of the hidden text): assumed, inbox #94.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from sqlalchemy import Connection, select

from spectio_server.api.models import TaskFiles
from spectio_server.api.problems import Invalid, Problem, not_found
from spectio_server.api.runs_read import read
from spectio_server.files.confine import MAX_READ, TAIL, NotAllowed, NotFound
from spectio_server.files.pool import FilePool, Stalled
from spectio_server.files.taskfiles import (
    AttemptFiles,
    Binary,
    Cleaned,
    attempt_dir,
    list_task_files,
    read_task_file,
)
from spectio_server.store.schema import attempts, runs, tasks, workflow_versions, workflows

__all__ = ["READ_TIMEOUT_S", "FilePool", "load_attempt", "router"]

router = APIRouter()

READ_TIMEOUT_S = 5.0  # one listing or one read, in the file pool
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}
_RANGE = re.compile(r"bytes=([0-9]{1,15})-([0-9]{0,15})")


def load_attempt(conn: Connection, task_id: str, n: int, runs_root: Path) -> AttemptFiles | None:
    """Attempt `n` of the task (of its latest launch with one), or None."""
    row = conn.execute(
        select(
            tasks.c.run_id,
            workflows.c.engine,
            attempts.c.state,
            attempts.c.work_dir,
            attempts.c.native_id,
            attempts.c.logs,
        )
        .join(tasks, tasks.c.id == attempts.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .where(attempts.c.task_id == task_id, attempts.c.n == n)
        .order_by(attempts.c.launch_n.desc())
        .limit(1)
    ).one_or_none()
    if row is None:
        return None
    logs = tuple(
        (log["path"], log["kind"])
        for log in row.logs or []
        if isinstance(log, dict) and isinstance(log.get("path"), str)
    )
    return AttemptFiles(
        row.run_id, row.engine, row.state, row.work_dir, row.native_id, logs, runs_root
    )


def _attempt(request: Request, task_id: str, n: int) -> AttemptFiles:
    with read(request) as conn:
        found = load_attempt(conn, task_id, n, request.app.state.settings.runs_root)
    if found is None:
        raise not_found(f"no attempt {n} of task {task_id[:64]!r}")
    return found


def _in_pool(request: Request, job: Any) -> Any:
    try:
        return request.app.state.files.run(job, READ_TIMEOUT_S)
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None
    except Binary as exc:
        raise Problem(415, "binary-file", "Binary file", f"{exc}: not shown as text") from None
    except Cleaned as exc:
        raise Problem(410, "log-cleaned", "Cleaned", str(exc)) from None
    except NotAllowed as exc:
        raise Problem(422, "file-not-allowed", "File not allowed", str(exc)) from None
    except NotFound as exc:
        raise not_found(str(exc), "log-not-found") from None


def _iso(mtime: float | None) -> str | None:
    return None if mtime is None else datetime.fromtimestamp(mtime, UTC).isoformat()


@router.get("/tasks/{task_id}/attempts/{n}/files", response_model=TaskFiles)
def task_files(request: Request, task_id: str, n: int) -> Response:
    attempt = _attempt(request, task_id, n)
    files = _in_pool(request, lambda: list_task_files(attempt))
    body = TaskFiles.model_validate(
        {
            "task_id": task_id,
            "attempt": n,
            "work_dir": attempt_dir(attempt),
            "native_id": attempt.native_id,
            "files": [
                {
                    "name": f.name,
                    "kind": f.kind,
                    "size": f.size,
                    "mtime": _iso(f.mtime),
                    "state": f.state,
                    "note": f.note,
                }
                for f in files
            ],
        }
    )
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


def _byte_range(value: str | None) -> tuple[int, int | None] | None:
    if value is None:
        return None
    found = _RANGE.fullmatch(value.strip())
    if found is None:
        raise Invalid("Range", "one range, bytes=<start>-[<last>]")
    start, last = int(found[1]), int(found[2]) if found[2] else None
    if last is not None and last < start:
        raise Invalid("Range", "the last byte is before the first")
    return start, last


@router.get("/tasks/{task_id}/attempts/{n}/files/{name:path}", response_class=Response)
def task_file(
    request: Request,
    task_id: str,
    n: int,
    name: str,
    tail: Annotated[int, Query(ge=1, le=MAX_READ)] = TAIL,
    download: bool = False,
) -> Response:
    attempt = _attempt(request, task_id, n)
    byte_range = _byte_range(request.headers.get("range"))
    served = _in_pool(
        request,
        lambda: read_task_file(attempt, name, max_bytes=tail, byte_range=byte_range),
    )
    headers = dict(HEADERS)
    if download:
        base = name.rsplit("/", 1)[-1]
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(base, safe='')}"
    status = 200
    if served.partial and served.start >= served.size:
        raise Invalid("Range", f"the file has {served.size} bytes")
    if served.partial:
        status = 206
        last = max(served.start, served.end - 1)
        headers["Content-Range"] = f"bytes {served.start}-{last}/{served.size}"
    return Response(served.text, status, headers=headers, media_type="text/plain; charset=utf-8")
