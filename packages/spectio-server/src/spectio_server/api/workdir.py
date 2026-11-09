"""`GET /tasks/{id}/attempts/{n}/workdir?path=` and its `stat`, `text` and `raw` routes: a
Nextflow attempt's work directory, read only (FU-P3-85e; api §5.3; dev-env §15.3 req. 13, note
of 2026-11-08, and req. 14).

The routes are the results routes on another root (`files.taskfiles.TaskDir`), found as the Job
files routes find it: attempt `n` of the task's latest launch with one, its directory two levels
below the run's work directory. A name with a part that starts with `.` is hidden from the
listing and refused by the others, so the job files are served only by the Job files routes; a
work directory has no report viewer, so `.html` and `.htm` are attachments. Problems as the Job
files routes: `404 not-found` (a Snakemake attempt, one of a run started from a terminal, no
work directory recorded, no such file), `410 log-cleaned`, `409 run-dir-unreachable`.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from spectio_server.api.models import ResultStat, WorkDir
from spectio_server.api.problems import Problem
from spectio_server.api.results import (
    AsQuery,
    RangeHeader,
    entry_dicts,
    raw_response,
    stat_response,
)
from spectio_server.api.taskfiles import (
    HEADERS,
    _attempt,
    _byte_range,
    in_pool,
    text_response,
)
from spectio_server.files import results as files
from spectio_server.files.confine import MAX_READ, TAIL, NotAllowed
from spectio_server.files.taskfiles import TaskDir, attempt_dir, check_work_rel

router = APIRouter()
BASE = "/tasks/{task_id}/attempts/{n}/workdir"


def _rel(path: str, *, file: bool = True) -> Any:
    try:
        rel = check_work_rel(path)
    except NotAllowed as exc:
        raise Problem(422, "file-not-allowed", "File not allowed", str(exc)) from None
    if rel is None and file:
        raise Problem(422, "file-not-allowed", "File not allowed", "not a file")
    return rel


def _tree(request: Request, task_id: str, n: int) -> tuple[TaskDir, str | None]:
    attempt = _attempt(request, task_id, n)
    return TaskDir(attempt), attempt_dir(attempt)


@router.get(BASE, response_model=WorkDir)
def workdir(request: Request, task_id: str, n: int, path: str = "") -> Response:
    tree, root = _tree(request, task_id, n)
    rel = _rel(path, file=False)
    exists, entries, truncated = in_pool(
        request, lambda: files.list_results(tree, rel), missing="not-found"
    )
    body = WorkDir.model_validate(
        {
            "root": root,
            "path": path,
            "exists": exists,
            "entries": entry_dicts(entries),
            "truncated": truncated,
        }
    )
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


@router.get(f"{BASE}/stat/{{path:path}}", response_model=ResultStat)
def workdir_stat(request: Request, task_id: str, n: int, path: str) -> Response:
    tree, root = _tree(request, task_id, n)
    rel = _rel(path)
    e = in_pool(request, lambda: files.stat_result(tree, rel), missing="not-found")
    return stat_response(root, path, e)


@router.get(f"{BASE}/text/{{path:path}}", response_class=Response)
def workdir_text(
    request: Request,
    task_id: str,
    n: int,
    path: str,
    tail: Annotated[int, Query(ge=1, le=MAX_READ)] = TAIL,
) -> Response:
    tree, _ = _tree(request, task_id, n)
    rel = _rel(path)
    byte_range = _byte_range(request.headers.get("range"))
    served = in_pool(
        request,
        lambda: files.read_result_text(tree, rel, max_bytes=tail, byte_range=byte_range),
        missing="not-found",
    )
    return text_response(served, HEADERS)


@router.get(f"{BASE}/raw/{{path:path}}", response_class=Response)
def workdir_raw(
    request: Request,
    task_id: str,
    n: int,
    path: str,
    download: bool = False,
    as_: AsQuery = None,
    range_: RangeHeader = None,
) -> Response:
    tree, _ = _tree(request, task_id, n)
    return raw_response(request, tree, _rel(path), download, as_, range_, reports=False)
