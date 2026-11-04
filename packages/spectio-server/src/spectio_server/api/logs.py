"""`GET /runs/{id}/logs?source=`: the last 64 KiB of a run log (P1 Tasks 18 and 28; api §5;
architecture §13.7).

Sources: `head-out` and `head-err` (`.spectio/head.out`, `.spectio/head.err`), and `engine`, the
engine's run log: for Nextflow, `.spectio/nextflow.log`, where the head script points
`NXF_LOG_FILE` (P1 Task 28), else `.nextflow.log` (a run launched before, or one from a terminal,
`cli-observed`, which keeps its own); for Snakemake, the newest `.snakemake/log/*.log` last
written between the run's creation and its head's exit (else the run's end; a terminal run with
neither has none: CR-P3T30-05), in the directory the engine ran in: a
Resume's lineage root's, which every run of the lineage shares (P1 Task 30, CR-P3T30-03). The
launch directory is derived from the runs root and the run ID, never read from a row (dev-env
§15.3 req. 10), and must be private. Below it, the read is the confined walk of `files.confine`
(checking-scenarios §11.1): no symlink is followed, only a regular file of the user is read,
and it runs in the file pool with a timeout (req. 13). Anything refused or missing is
`404 log-not-found`; a file system that does not answer is `503 runner-offline`. Escape
sequences are removed from the text.

`?follow=true` streams the same file: its last 64 KiB, then each line appended, read once per
`POLL_S` in the file pool, until the run has ended (api §5). At most `MAX_FOLLOWS` follow streams
are open at once (dev-env §15.3 req. 14: "a session holds at most 4 follow streams of files");
until sessions are built (P1 Tasks 12 to 16), the local API is one session (inbox #86 rule 1),
so the cap is the server's, and a fifth is `429 rate-limited`.
"""

import asyncio
import threading
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from spectio_server.api.problems import Problem
from spectio_server.api.runs_read import read, run_row
from spectio_server.api.taskfiles import HEADERS, in_pool
from spectio_server.failure import dir_run_id
from spectio_server.files.confine import (
    MAX_READ,
    TAIL,
    NotFound,
    Root,
    list_confined,
    open_confined,
    read_at,
    size_of,
)
from spectio_server.files.confine import tail as tail_of
from spectio_server.files.redact import strip_escapes
from spectio_server.files.taskfiles import run_root
from spectio_server.projector.runs import TERMINAL
from spectio_server.store.schema import runs

router = APIRouter()

HEAD_FILES = {"head-out": "head.out", "head-err": "head.err"}
SPECTIO_LOG = PurePosixPath(".spectio/nextflow.log")
NEXTFLOW_LOG = PurePosixPath(".nextflow.log")
SMK_LOGS = PurePosixPath(".snakemake/log")
MAX_SMK_LOGS = 1000  # entries of `.snakemake/log` looked at
MTIME_SLACK_S = 0.1  # a file's mtime comes from a coarser clock than `datetime.now`
MAX_FOLLOWS = 4  # follow streams open at once (req. 14)
POLL_S = 1.0  # a followed file is read again after this


class Follows:
    """The follow streams open: a slot is taken before the response and given back when it
    ends, so streams that open together cannot pass the cap."""

    def __init__(self, cap: int = MAX_FOLLOWS) -> None:
        self.cap, self.open = cap, 0
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            if self.open >= self.cap:
                return False
            self.open += 1
            return True

    def give(self) -> None:
        with self._lock:
            self.open -= 1


def _newest_log(launch: Root, since: datetime, until: datetime | None) -> PurePosixPath:
    """The run's own Snakemake log (CR-P3T30-03): the newest regular `*.log` of
    `.snakemake/log` last written between the run's creation and its head's exit; the runs of a
    lineage share the directory. NotFound when there is none."""
    found = list_confined(launch, SMK_LOGS, MAX_SMK_LOGS)
    low = since.timestamp() - MTIME_SLACK_S
    high = None if until is None else until.timestamp() + MTIME_SLACK_S
    logs = [
        e
        for e in found.entries
        if e.type == "file"
        and e.name.endswith(".log")
        and e.mtime is not None
        and e.mtime >= low
        and (high is None or e.mtime <= high)
    ]
    if not logs:
        raise NotFound("no Snakemake log of this run yet")
    newest = max(logs, key=lambda e: (e.mtime or 0, e.name))
    return SMK_LOGS / newest.name


def _launch_of(row: Any, source: str) -> str:
    """The run whose launch directory holds the log: a Snakemake engine log is in the lineage
    root's (CR-P3T30-03)."""
    return dir_run_id(row) if source not in HEAD_FILES and row.engine != "nextflow" else row.id


def _read(runs_root: Path, row: Any, source: str) -> tuple[str, PurePosixPath, int]:
    """The log's tail, its path in the launch directory and its size."""
    engine, origin = row.engine, row.origin
    with run_root(runs_root, _launch_of(row, source), "launch") as launch:
        if source in HEAD_FILES:
            candidates = [PurePosixPath(".spectio", HEAD_FILES[source])]
        elif engine == "nextflow":
            own = origin != "cli-observed"
            candidates = [SPECTIO_LOG, NEXTFLOW_LOG] if own else [NEXTFLOW_LOG]
        else:
            until = row.exited_at or row.ended_at
            if until is None and row.state in TERMINAL:
                raise NotFound("the run ended, but not when: its own log is not known")
            candidates = [_newest_log(launch, row.created_at, until)]
        for i, rel in enumerate(candidates):
            try:
                with open_confined(launch, rel) as f:
                    text = strip_escapes(tail_of(f, TAIL).decode("utf-8", "replace"))
                    return text, rel, size_of(f)
            except NotFound:
                if i == len(candidates) - 1:
                    raise
    raise NotFound(source)  # not reached: there is always one candidate


def _read_from(runs_root: Path, run_id: str, rel: PurePosixPath, at: int) -> tuple[int, bytes]:
    """The bytes of the log from `at` (at most MAX_READ), and where they start: from 0 when the
    file is now shorter (replaced)."""
    with run_root(runs_root, run_id, "launch") as launch, open_confined(launch, rel) as f:
        start = at if size_of(f) >= at else 0
        return start, read_at(f, start, MAX_READ)


def _ended(request: Request, run_id: str) -> bool:
    with read(request) as conn:
        state = conn.execute(select(runs.c.state).where(runs.c.id == run_id)).scalar()
    return state is None or state in TERMINAL


async def _follow(
    request: Request, row: Any, source: str, rel: PurePosixPath, at: int
) -> AsyncIterator[str]:
    """Each line appended after `at`, until the run has ended (then the rest, whole)."""
    runs_root, run_id = request.app.state.settings.runs_root, _launch_of(row, source)
    pending = b""
    while True:
        ended = await run_in_threadpool(_ended, request, row.id)
        try:
            start, data = await run_in_threadpool(
                in_pool, request, lambda at=at: _read_from(runs_root, run_id, rel, at)
            )
        except Problem:  # gone or not answering: the stream ends
            return
        pending, at = (b"" if start < at else pending) + data, start + len(data)
        cut = len(pending) if ended or len(pending) >= MAX_READ else pending.rfind(b"\n") + 1
        if cut:
            yield strip_escapes(pending[:cut].decode("utf-8", "replace"))
            pending = pending[cut:]
        if ended:
            return
        await asyncio.sleep(POLL_S)


class _Followed(StreamingResponse):
    """Gives its follow slot back when the response ends, even if its body never starts."""

    def __init__(self, follows: Follows, body: AsyncIterator[str]) -> None:
        super().__init__(body, media_type="text/plain; charset=utf-8", headers=HEADERS)
        self.follows = follows

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.follows.give()


@router.get("/runs/{run_id}/logs", response_class=PlainTextResponse)
def run_log(
    request: Request,
    run_id: str,
    source: Literal["head-out", "head-err", "engine"] = "engine",
    follow: bool = False,
) -> Response:
    with read(request) as conn:
        row = run_row(conn, run_id)
    runs_root = request.app.state.settings.runs_root
    follows: Follows = request.app.state.follows
    if follow and not follows.take():
        raise Problem(
            429, "rate-limited", "Too many streams", f"At most {MAX_FOLLOWS} logs follow at once."
        )
    try:
        text, rel, size = in_pool(
            request, lambda: _read(runs_root, row, source), refused_missing=True
        )
    except BaseException:
        if follow:
            follows.give()
        raise
    if not follow:
        return PlainTextResponse(text, media_type="text/plain; charset=utf-8", headers=HEADERS)

    async def body() -> AsyncIterator[str]:
        yield text
        async for more in _follow(request, row, source, rel, size):
            yield more

    return _Followed(follows, body())
