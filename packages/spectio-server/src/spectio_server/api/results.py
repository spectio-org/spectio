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

`?as=tiff` and `?as=zarr` with `Sec-Fetch-Dest: empty` serve the imaging viewers' reads in the
order of api §5.3.1's table (`_imaging`): a TIFF by one closed `Range`, past the 1 GiB cap; a
Zarr key below a `.ome.zarr` folder, whole or by one `Range`, at most 16 MiB. A range is read
from its own first byte (the TIFF's 4-byte header aside), each chunk with the identity check.
Each imaging read holds one of the server's `IMAGING_SLOTS` until its body ends or aborts; with
none free it is `503` at once (step 9). No raw file is served to a script or a worker (step 0).
"""

import logging
import re
import threading
from collections.abc import Iterable, Iterator
from pathlib import PurePosixPath
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Header, Query, Request
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
MAX_KEY = 16 << 20  # the largest Zarr key (api §5.3.1, step 7)
MAX_RANGE = (8 << 20) + 1  # the most bytes of one imaging range (step 8)
AS = ("image", "tiff", "zarr")
IMAGING_SLOTS = 3  # imaging reads at once, per server (step 9)
SCRIPT_DESTS = frozenset({"script", "worker", "sharedworker", "serviceworker"})  # step 0
TIFF_HEADS = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")  # TIFF 6.0 and BigTIFF (step 10)
_CLOSED = re.compile(r"bytes=([0-9]{1,19})-([0-9]{1,19})")
_KEY_PART = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,254}")  # a middle part of a Zarr key
_CHUNK_PART = re.compile(r"c|[0-9]{1,10}(\.[0-9]{1,10}){0,9}")
_METADATA = frozenset({".zattrs", ".zgroup", ".zarray", "zarr.json"})  # no `.zmetadata`
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
    if as_ not in AS:
        raise Invalid("as", "one of `image`, `tiff`, `zarr`")
    if as_ != "image":
        return None
    media = images.MEDIA.get(rel.suffix.lower())
    if media is None:
        raise Problem(422, "file-not-allowed", "File not allowed", "not an image's name")
    if request.headers.get("sec-fetch-dest") != "image":
        return None
    return media


AsQuery = Annotated[str | None, Query(alias="as", json_schema_extra={"enum": list(AS)})]
RangeHeader = Annotated[
    str | None,
    Header(alias="range", description="with as=tiff or as=zarr: one closed bytes=<first>-<last>"),
]


@router.get("/runs/{run_id}/results/raw/{path:path}", response_class=Response)
def result_file(
    request: Request,
    run_id: str,
    path: str,
    download: bool = False,
    as_: AsQuery = None,
    range_: RangeHeader = None,
) -> Response:
    refuse_script(request)
    where, _ = _where(request, run_id)
    return raw_response(request, where, _file_rel(path), download, as_, range_, reports=True)


def refuse_script(request: Request) -> None:
    """Step 0 of api §5.3.1, first on every raw route: no run file becomes a script or a worker
    (dev-env §15.3 req. 19, SEC-PRE-FU102-R1-07)."""
    if request.headers.get("sec-fetch-dest") in SCRIPT_DESTS:
        raise Problem(
            422, "file-not-allowed", "File not allowed", "not served to a script or a worker"
        )


def raw_response(
    request: Request,
    where: files.Tree,
    rel: PurePosixPath,
    download: bool,
    as_: str | None,
    range_: str | None,
    *,
    reports: bool,
) -> StreamingResponse:
    """The raw route's answer for the file `rel` below `where` (results, or a work directory,
    FU-P3-85e): the image of api §5.3's table, an imaging read of §5.3.1's, a report with the
    sandbox CSP when `reports`, else an attachment."""
    fetched = request.headers.get("sec-fetch-dest") == "empty"
    # One decision lifts the cap and dispatches: an uncapped read is never an attachment
    # (SEC-P3FU102A-01).
    if as_ in ("tiff", "zarr") and not download and fetched:
        return _imaging(request, where, rel, as_, range_)
    raw = in_pool(
        request, lambda: files.open_raw(where, rel, MAX_RAW, files.CHUNK), missing="not-found"
    )
    if raw.size > MAX_RAW:
        raise Problem(413, "file-too-large", "File too large", f"more than {MAX_RAW} bytes")
    media = _image_type(request, rel, download, as_)
    if as_ in ("tiff", "zarr") and not download:
        _imaging_name(rel, as_)  # steps 4 and 5, before step 6's attachment (CR-P3FU102A-01)
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
    body = _chunks(request, where, rel, raw, raw.first, len(raw.first), raw.size)
    return StreamingResponse(body, media_type=media, headers=headers)


def _imaging_name(rel: PurePosixPath, as_: str) -> None:
    """Steps 4 and 5 of api §5.3.1: a TIFF's name, or a Zarr key below a `.ome.zarr` folder."""
    if as_ == "tiff" and not rel.name.lower().endswith((".tif", ".tiff")):
        raise Problem(422, "file-not-allowed", "File not allowed", "not a TIFF's name")
    if as_ == "zarr" and not _zarr_key(rel.parts):
        raise Problem(422, "file-not-allowed", "File not allowed", "not a key of an OME-Zarr")


def _zarr_key(parts: tuple[str, ...]) -> bool:
    """The parts after the first `.ome.zarr` part before the last are a Zarr key."""
    for i, part in enumerate(parts[:-1]):
        if part.lower().endswith(".ome.zarr"):
            *middle, last = parts[i + 1 :]
            if not all(_KEY_PART.fullmatch(p) for p in middle):
                return False
            return last in _METADATA or _CHUNK_PART.fullmatch(last) is not None
    return False


def _closed_range(value: str | None, size: int) -> tuple[int, int]:
    """Step 8: the one closed range asked, its last byte capped at the file's end."""
    found = None if value is None else _CLOSED.fullmatch(value)
    if found is None:
        raise Invalid("Range", "one closed range, bytes=<first>-<last>")
    first, last = int(found[1]), int(found[2])
    if last < first or last - first + 1 > MAX_RANGE:
        raise Invalid("Range", f"from 1 to {MAX_RANGE} bytes, first to last")
    if first >= size:
        raise Invalid("Range", "starts at or past the end of the file")
    return first, min(last, size - 1)


def _imaging(
    request: Request, where: files.Tree, rel: PurePosixPath, as_: str, range_: str | None
) -> StreamingResponse:
    """An imaging read, holding a read slot (step 9, taken before the pool) until its body ends,
    aborts or is dropped: the TIFF range or the Zarr key, never an attachment."""
    slot: threading.BoundedSemaphore = request.app.state.imaging_slots
    if not slot.acquire(blocking=False):
        raise Problem(503, "runner-offline", "Busy reading images", "busy reading images")
    try:
        body, status, headers = _imaging_body(request, where, rel, as_, range_)
    except BaseException:
        slot.release()
        raise
    return StreamingResponse(
        _Held(slot, body),
        status_code=status,
        media_type="application/octet-stream",
        headers=headers,
    )


def _imaging_body(
    request: Request, where: files.Tree, rel: PurePosixPath, as_: str, range_: str | None
) -> tuple[Iterator[bytes], int, dict[str, str]]:
    """Steps 1, 4, 5, 7, 8, 10 and 11 of api §5.3.1: the body, status and headers. The 1 GiB
    cap is lifted only for a TIFF range, whose read step 8 caps."""
    cap = None if as_ == "tiff" and range_ is not None else MAX_RAW
    head = 4 if as_ == "tiff" else 0 if range_ is not None else files.CHUNK
    raw = in_pool(request, lambda: files.open_raw(where, rel, cap, head), missing="not-found")
    if cap is not None and raw.size > cap:
        raise Problem(413, "file-too-large", "File too large", f"more than {cap} bytes")
    _imaging_name(rel, as_)
    if as_ == "zarr" and raw.size > MAX_KEY:
        raise Problem(413, "file-too-large", "File too large", f"a Zarr key over {MAX_KEY} bytes")
    headers = {**HEADERS, "Vary": "Sec-Fetch-Dest", "Accept-Ranges": "bytes"}
    headers["Content-Security-Policy"] = TEXT_CSP
    if as_ == "zarr" and range_ is None:
        headers["Content-Length"] = str(raw.size)
        return _chunks(request, where, rel, raw, raw.first, len(raw.first), raw.size), 200, headers
    if len(request.headers.getlist("range")) > 1:  # two fields are two ranges (SEC-P3FU102A-02)
        raise Invalid("Range", "one closed range, bytes=<first>-<last>")
    first, last = _closed_range(range_, raw.size)
    if as_ == "tiff" and raw.first not in TIFF_HEADS:
        raise Problem(422, "file-not-allowed", "File not allowed", "not the TIFF its name says")
    headers["Content-Length"] = str(last + 1 - first)
    headers["Content-Range"] = f"bytes {first}-{last}/{raw.size}"
    return _chunks(request, where, rel, raw, b"", first, last + 1), 206, headers


class _Held:
    """An imaging answer's body: its read slot is given back once, when the body ends or fails,
    or when the response drops it unread (a client gone before the first chunk)."""

    def __init__(self, slot: threading.BoundedSemaphore, body: Iterator[bytes]) -> None:
        self._slot: threading.BoundedSemaphore | None = slot
        self._body = body

    def __iter__(self) -> "_Held":
        return self

    def __next__(self) -> bytes:
        try:
            return next(self._body)
        except BaseException:  # StopIteration too: the body ended
            self.release()
            raise

    def release(self) -> None:
        slot, self._slot = self._slot, None
        if slot is not None:
            slot.release()

    __del__ = release


def _chunks(
    request: Request,
    where: files.Tree,
    rel: PurePosixPath,
    raw: files.Raw,
    prefix: bytes,
    start: int,
    end: int,
) -> Iterator[bytes]:
    """`prefix`, then bytes `start` to `end` of the file first opened as `raw`, chunk by chunk;
    a chunk that fails, comes back empty or opens another file aborts the response."""
    if prefix:
        yield prefix  # the bytes checked are the bytes sent: no second open
    while start < end:
        try:
            data = in_pool(
                request,
                lambda at=start: files.read_chunk(where, rel, at, end - at, raw.ident),
            )
        except Problem as exc:
            log.warning("%s cut at %d: %s", request.url.path, start, exc)
            raise
        if not data:
            log.warning("%s cut at %d: it shrank", request.url.path, start)
            raise ShortFile(f"{rel}: shrank at {start}")
        yield data
        start += len(data)


class ShortFile(Exception):
    """A results file ended before the size its headers sent: the server aborts the response,
    so the client sees a failed download, not a short file that looks whole (CR-P3T31-03)."""
