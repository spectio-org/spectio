"""`GET /runs/{id}/logs?source=`: the last 64 KiB of a run log (P1 Task 18; api §5; arch §13.7).

Sources: `head-out` and `head-err` (`.spectio/head.out`, `.spectio/head.err`), and `engine`, the
engine's run log: `.nextflow.log`, or the newest `.snakemake/log/*.log`. The launch directory is
derived from the runs root and the run ID, never read from a row (dev-env §15.3 req. 10), and
must be private (`rundir.private_dir`). Below it, each path part is opened from the descriptor of
the one before with O_NOFOLLOW, so no symlink is followed, in the tree or out of it: the walk is
the real-path check of P1 Task 18 Step 3, made at open time (checking-scenarios §11.1). Only a
regular file is read; anything else is `404 log-not-found`.
"""

import os
import stat
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from spectio.runner.rundir import private_dir
from spectio_server.api.problems import not_found
from spectio_server.api.runs_read import read, run_row

router = APIRouter()

TAIL = 65536
HEAD_FILES = {"head-out": "head.out", "head-err": "head.err"}
HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}
_NO_FOLLOW = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK  # a FIFO does not block the open


def _open(dir_fd: int, *parts: str, directory: bool = False) -> int:
    """`parts` below `dir_fd`, each opened with O_NOFOLLOW; raises OSError."""
    fd = os.dup(dir_fd)
    try:
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            flags = _NO_FOLLOW | (os.O_DIRECTORY if directory or not last else 0)
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
    except OSError:
        os.close(fd)
        raise
    return fd


def _newest_log(dir_fd: int) -> str:
    """The newest regular `*.log` in `.snakemake/log`; raises FileNotFoundError when none."""
    log_fd = _open(dir_fd, ".snakemake", "log", directory=True)
    try:
        found = []
        for name in os.listdir(log_fd):
            if name.endswith(".log"):
                st = os.stat(name, dir_fd=log_fd, follow_symlinks=False)
                if stat.S_ISREG(st.st_mode):
                    found.append((st.st_mtime_ns, name))
    finally:
        os.close(log_fd)
    if not found:
        raise FileNotFoundError("no Snakemake log yet")
    return max(found)[1]


def _tail(fd: int) -> bytes:
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        raise FileNotFoundError("not a regular file")
    return os.pread(fd, TAIL, max(0, st.st_size - TAIL))


@router.get("/runs/{run_id}/logs", response_class=PlainTextResponse)
def run_log(
    request: Request, run_id: str, source: Literal["head-out", "head-err", "engine"] = "engine"
) -> PlainTextResponse:
    with read(request) as conn:
        engine = run_row(conn, run_id).engine
    try:
        with private_dir(request.app.state.settings.runs_root, run_id, "launch") as launch_fd:
            if source in HEAD_FILES:
                parts: tuple[str, ...] = (".spectio", HEAD_FILES[source])
            elif engine == "nextflow":
                parts = (".nextflow.log",)
            else:
                parts = (".snakemake", "log", _newest_log(launch_fd))
            fd = _open(launch_fd, *parts)
            try:
                data = _tail(fd)
            finally:
                os.close(fd)
    except (OSError, ValueError) as exc:  # missing, a symlink (ELOOP), not private, not a file
        reason = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
        raise not_found(f"no {source} log for this run: {reason}", "log-not-found") from None
    return PlainTextResponse(
        data.decode("utf-8", "replace"), media_type="text/plain; charset=utf-8", headers=HEADERS
    )
