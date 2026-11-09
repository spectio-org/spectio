"""`GET /runs/{id}/results?path=`, `GET /runs/{id}/results/raw/{path}`, and the `stat` and
`text` routes of the preview: a run's results, read only (P1 Task 31; api §5 note of
2026-10-28, Results; api §5.3, FU-P3-85a; dev-env §15.3 req. 13 and 14).

`stat` answers the listing's entry for one path; `text` reads a file as the Job files read does
(`files.taskfiles.read_text`: the tail, or one `Range`, at most 1 MiB, ended on a whole UTF-8
sequence), with the text CSP.

The listing is one folder of the results directory and the reports found below its root
(`files.results`); the search runs once per listing while the run is active, and its result is
kept once the run has ended. A raw file is served whole with its `Content-Length`, read in chunks
of at most 1 MiB, each in the file pool with its timeout; a read that fails or comes back short
once the headers are sent aborts the response (CR-P3T31-03). The first chunk is read at the
first opening, which records the file's `(st_dev, st_ino)`, and is sent as the first part of the
body; every later chunk that opens another file aborts the response too (api §5.3).
`?as=image` with `Sec-Fetch-Dest: image` serves an image inline, in the order of api §5.3's
table (`_image_type`, then the caps and `files.images.check`). `.html` and `.htm` carry the
sandbox CSP of req. 14 for the report viewer's `<iframe>`; every other file, and any file asked
with `?download=true`, is an attachment with the CSP `sandbox`. `404` when the run has no
results directory: unknown, or a run started from a terminal (`cli-observed`), whose files
0.0.1 does not serve.
"""

import logging
from collections.abc import Iterable, Iterator
from pathlib import PurePosixPath
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response, StreamingResponse

from spectio_server.api.models import Results, ResultStat
from spectio_server.api.problems import Invalid, Problem, not_found
from spectio_server.api.runs_read import read, results_of, run_row
from spectio_server.api.taskfiles import (
    HEADERS,
    TEXT_CSP,
    _byte_range,
    _iso,
    in_pool,
    text_response,
)
from spectio_server.failure import dir_run_id
from spectio_server.files import images
from spectio_server.files import results as files
from spectio_server.files.confine import MAX_READ, TAIL, NotAllowed
from spectio_server.files.pool import READ_TIMEOUT_S
from spectio_server.projector.runs import TERMINAL

log = logging.getLogger(__name__)
router = APIRouter()

MAX_RAW = 1 << 30  # the largest results file served, 1 GiB
MAX_IMAGE = 20 << 20  # the largest served as an image (api §5.3, step 6)
MAX_SVG = 5 << 20  # the largest SVG served as an image
KEPT_SEARCHES = 1000  # ended runs whose reports are kept in memory
REPORT_CSP = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)


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
            "entries": entry_dicts(entries),
            "truncated": truncated,
            "reports": [{"path": r.path, "title": r.title, "group": r.group} for r in reports],
        }
    )
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


def entry_dicts(entries: Iterable[Any]) -> list[dict[str, Any]]:
    """The listing's entries, as the `Results` and `WorkDir` models take them."""
    return [
        {"name": e.name, "type": e.type, "size": e.size, "mtime": _iso(e.mtime)} for e in entries
    ]


def stat_response(root: str | None, path: str, e: Any) -> Response:
    """The `ResultStat` answer for the entry `e` of `path` under `root`."""
    body = ResultStat.model_validate(
        {
            "root": root,
            "path": path,
            "name": e.name,
            "type": e.type,
            "size": e.size,
            "mtime": _iso(e.mtime),
        }
    )
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


def _file_rel(path: str) -> Any:
    rel = _rel(path)
    if rel is None:
        raise Problem(422, "file-not-allowed", "File not allowed", "not a file")
    return rel


@router.get("/runs/{run_id}/results/stat/{path:path}", response_model=ResultStat)
def result_stat(request: Request, run_id: str, path: str) -> Response:
    where, _ = _where(request, run_id)
    rel = _file_rel(path)
    e = in_pool(request, lambda: files.stat_result(where, rel), missing="not-found")
    return stat_response(where.results_dir, path, e)


@router.get("/runs/{run_id}/results/text/{path:path}", response_class=Response)
def result_text(
    request: Request,
    run_id: str,
    path: str,
    tail: Annotated[int, Query(ge=1, le=MAX_READ)] = TAIL,
) -> Response:
    where, _ = _where(request, run_id)
    rel = _file_rel(path)
    byte_range = _byte_range(request.headers.get("range"))
    served = in_pool(
        request,
        lambda: files.read_result_text(where, rel, max_bytes=tail, byte_range=byte_range),
        missing="not-found",
    )
    return text_response(served, HEADERS)


def _image_type(
    request: Request, rel: PurePosixPath, download: bool, as_: str | None
) -> str | None:
    """Steps 2 to 5 of the image table (api §5.3): the type to serve the file as an image with,
    or None for the raw route's other answers. `Sec-Fetch-Dest` decides only how a file is
    served: a request without `image` (a navigation, or a client that sends no Fetch Metadata)
    gets the attachment."""
    if download or as_ is None:
        return None
    if as_ != "image":
        raise Invalid("as", "the only value is `image`")
    media = images.MEDIA.get(rel.suffix.lower())
    if media is None:
        raise Problem(422, "file-not-allowed", "File not allowed", "not an image's name")
    if request.headers.get("sec-fetch-dest") != "image":
        return None
    return media


@router.get("/runs/{run_id}/results/raw/{path:path}", response_class=Response)
def result_file(
    request: Request,
    run_id: str,
    path: str,
    download: bool = False,
    as_: Annotated[str | None, Query(alias="as")] = None,
) -> Response:
    where, _ = _where(request, run_id)
    return raw_response(request, where, _file_rel(path), download, as_, reports=True)


def raw_response(
    request: Request,
    where: files.Tree,
    rel: PurePosixPath,
    download: bool,
    as_: str | None,
    *,
    reports: bool,
) -> StreamingResponse:
    """The raw route's answer for the file `rel` below `where` (results, or a work directory,
    FU-P3-85e): the image of api §5.3's table, a report with the sandbox CSP when `reports`,
    else an attachment."""
    raw = in_pool(request, lambda: files.open_raw(where, rel, MAX_RAW), missing="not-found")
    if raw.size > MAX_RAW:
        raise Problem(413, "file-too-large", "File too large", f"more than {MAX_RAW} bytes")
    media = _image_type(request, rel, download, as_)
    headers = {**HEADERS, "Vary": "Sec-Fetch-Dest", "Content-Length": str(raw.size)}
    if media is not None:
        cap = MAX_SVG if media == images.SVG else MAX_IMAGE
        if raw.size > cap:
            raise Problem(413, "file-too-large", "File too large", f"an image over {cap} bytes")
        try:
            images.check(media, raw.first)
        except NotAllowed as exc:
            raise Problem(422, "file-not-allowed", "File not allowed", str(exc)) from None
        headers["Content-Security-Policy"] = TEXT_CSP
    elif reports and rel.suffix.lower() in files.REPORT_SUFFIXES and not download:
        media = "text/html; charset=utf-8"
        headers["Content-Security-Policy"] = REPORT_CSP
    else:
        media = "application/octet-stream"
        headers["Content-Security-Policy"] = TEXT_CSP
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(rel.name, safe='')}"

    def chunks() -> Iterator[bytes]:
        if raw.first:
            yield raw.first  # the bytes checked are the bytes sent: no second open
        start = len(raw.first)
        while start < raw.size:
            try:
                data = in_pool(
                    request,
                    lambda at=start: files.read_chunk(where, rel, at, raw.size - at, raw.ident),
                )
            except Problem as exc:
                log.warning("%s cut at %d: %s", request.url.path, start, exc)
                raise
            if not data:
                log.warning("%s cut at %d: it shrank", request.url.path, start)
                raise ShortFile(f"{rel}: shrank at {start}")
            yield data
            start += len(data)

    return StreamingResponse(chunks(), media_type=media, headers=headers)


class ShortFile(Exception):
    """A results file ended before the size its headers sent: the server aborts the response,
    so the client sees a failed download, not a short file that looks whole (CR-P3T31-03)."""
