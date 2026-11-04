"""`GET /runs/{id}/results?path=` and `GET /runs/{id}/results/raw/{path}`: a run's results,
read only (P1 Task 31; api §5 note of 2026-10-28, Results; dev-env §15.3 req. 13 and 14).

The listing is one folder of the results directory and the reports found below its root
(`files.results`); the search runs once per listing while the run is active, and its result is
kept once the run has ended. A raw file is served whole with its `Content-Length`, read in chunks
of at most 1 MiB, each in the file pool with its timeout; a read that fails or comes back short
once the headers are sent aborts the response (CR-P3T31-03). `.html` and `.htm` carry the
sandbox CSP of req. 14 for the report viewer's `<iframe>`; every other file, and any file asked
with `?download=true`, is an attachment with the CSP `sandbox`. `404` when the run has no
results directory: unknown, or a run started from a terminal (`cli-observed`), whose files
0.0.1 does not serve.
"""

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from spectio_server.api.models import Results
from spectio_server.api.problems import Problem, not_found
from spectio_server.api.runs_read import read, results_of, run_row
from spectio_server.api.taskfiles import HEADERS, in_pool
from spectio_server.failure import dir_run_id
from spectio_server.files import results as files
from spectio_server.files.confine import NotAllowed
from spectio_server.files.pool import READ_TIMEOUT_S
from spectio_server.projector.runs import TERMINAL

log = logging.getLogger(__name__)
router = APIRouter()

MAX_RAW = 1 << 30  # the largest results file served, 1 GiB
KEPT_SEARCHES = 1000  # ended runs whose reports are kept in memory
REPORT_CSP = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)
ATTACHMENT_CSP = "sandbox; default-src 'none'"


def _where(request: Request, run_id: str) -> tuple[files.Where, bool]:
    """The run's results directory, and whether the run has ended; 404 when it has none."""
    with read(request) as conn:
        row = run_row(conn, run_id)
    found = results_of(row)
    if found is None:
        raise not_found("this run has no results directory Spectio can show")
    runs_root = request.app.state.settings.runs_root
    return files.Where(runs_root, dir_run_id(row), found), row.state in TERMINAL


def _rel(path: str) -> Any:
    try:
        return files.check_rel(path)
    except NotAllowed as exc:
        raise Problem(422, "file-not-allowed", "File not allowed", str(exc)) from None


def _iso(mtime: float | None) -> str | None:
    return None if mtime is None else datetime.fromtimestamp(mtime, UTC).isoformat()


def _reports(request: Request, run_id: str, where: files.Where, ended: bool) -> Any:
    kept: dict[str, Any] = request.app.state.reports
    if run_id in kept:
        return kept[run_id]
    found = in_pool(request, lambda: files.find_reports(where), files.SEARCH_S + READ_TIMEOUT_S)
    if ended:  # nothing is written to it any more (req. 14, SEC-157)
        if len(kept) >= KEPT_SEARCHES:
            kept.pop(next(iter(kept)))
        kept[run_id] = found
    return found


@router.get("/runs/{run_id}/results", response_model=Results)
def run_results(request: Request, run_id: str, path: str = "") -> Response:
    where, ended = _where(request, run_id)
    rel = _rel(path)
    exists, entries, truncated = in_pool(
        request, lambda: files.list_results(where, rel), missing="not-found"
    )
    reports = _reports(request, run_id, where, ended) if exists else []
    body = Results.model_validate(
        {
            "root": where.results_dir,
            "path": path,
            "exists": exists,
            "entries": [
                {"name": e.name, "type": e.type, "size": e.size, "mtime": _iso(e.mtime)}
                for e in entries
            ],
            "truncated": truncated,
            "reports": [{"path": r.path, "title": r.title, "group": r.group} for r in reports],
        }
    )
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


@router.get("/runs/{run_id}/results/raw/{path:path}", response_class=Response)
def result_file(request: Request, run_id: str, path: str, download: bool = False) -> Response:
    where, _ = _where(request, run_id)
    rel = _rel(path)
    if rel is None:
        raise Problem(422, "file-not-allowed", "File not allowed", "not a file")
    size = in_pool(request, lambda: files.file_size(where, rel), missing="not-found")
    if size > MAX_RAW:
        raise Problem(413, "file-too-large", "File too large", f"more than {MAX_RAW} bytes")
    headers = dict(HEADERS)
    if rel.suffix.lower() in files.REPORT_SUFFIXES and not download:
        media = "text/html; charset=utf-8"
        headers["Content-Security-Policy"] = REPORT_CSP
    else:
        media = "application/octet-stream"
        headers["Content-Security-Policy"] = ATTACHMENT_CSP
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(rel.name, safe='')}"

    headers["Content-Length"] = str(size)

    def chunks() -> Iterator[bytes]:
        start = 0
        while start < size:
            try:
                data = in_pool(
                    request, lambda at=start: files.read_chunk(where, rel, at, size - at)
                )
            except Problem as exc:
                log.warning("results file %s of %s cut at %d: %s", rel, run_id, start, exc)
                raise
            if not data:
                log.warning("results file %s of %s cut at %d: it shrank", rel, run_id, start)
                raise ShortFile(f"{rel}: shrank at {start}")
            yield data
            start += len(data)

    return StreamingResponse(chunks(), media_type=media, headers=headers)


class ShortFile(Exception):
    """A results file ended before the size its headers sent: the server aborts the response,
    so the client sees a failed download, not a short file that looks whole (CR-P3T31-03)."""
