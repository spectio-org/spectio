"""`GET /runs/{id}/logs?source=`: the last 64 KiB of a run log (P1 Tasks 18 and 28; api §5;
architecture §13.7).

Sources: `head-out` and `head-err` (`.spectio/head.out`, `.spectio/head.err`), and `engine`, the
engine's run log: for Nextflow, `.spectio/nextflow.log`, where the head script points
`NXF_LOG_FILE` (P1 Task 28), else `.nextflow.log` (a run launched before, or one from a terminal,
`cli-observed`, which keeps its own); for Snakemake, the newest `.snakemake/log/*.log`. The launch
directory is derived from the runs root and the run ID, never read from a row (dev-env §15.3
req. 10), and must be private. Below it, the read is the confined walk of `files.confine`
(checking-scenarios §11.1): no symlink is followed, only a regular file of the user is read, and
it runs in the file pool with a timeout (req. 13). Anything refused or missing is
`404 log-not-found`; a file system that does not answer is `503 runner-offline`. Escape
sequences are removed from the text.
"""

from pathlib import Path, PurePosixPath
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from spectio_server.api.problems import Problem, not_found
from spectio_server.api.runs_read import read, run_row
from spectio_server.api.taskfiles import HEADERS, READ_TIMEOUT_S
from spectio_server.files.confine import (
    TAIL,
    NotAllowed,
    NotFound,
    Root,
    list_confined,
    open_confined,
)
from spectio_server.files.confine import tail as tail_of
from spectio_server.files.pool import Stalled
from spectio_server.files.redact import strip_escapes
from spectio_server.files.taskfiles import run_root

router = APIRouter()

HEAD_FILES = {"head-out": "head.out", "head-err": "head.err"}
SPECTIO_LOG = PurePosixPath(".spectio/nextflow.log")
NEXTFLOW_LOG = PurePosixPath(".nextflow.log")
SMK_LOGS = PurePosixPath(".snakemake/log")
MAX_SMK_LOGS = 1000  # entries of `.snakemake/log` looked at


def _newest_log(launch: Root) -> PurePosixPath:
    """The newest regular `*.log` of `.snakemake/log`; NotFound when there is none."""
    found = list_confined(launch, SMK_LOGS, MAX_SMK_LOGS)
    logs = [e for e in found.entries if e.type == "file" and e.name.endswith(".log")]
    if not logs:
        raise NotFound("no Snakemake log yet")
    newest = max(logs, key=lambda e: (e.mtime or 0, e.name))
    return SMK_LOGS / newest.name


def _read(runs_root: Path, run_id: str, engine: str | None, origin: str | None, source: str) -> str:
    with run_root(runs_root, run_id, "launch") as launch:
        if source in HEAD_FILES:
            candidates = [PurePosixPath(".spectio", HEAD_FILES[source])]
        elif engine == "nextflow":
            own = origin != "cli-observed"
            candidates = [SPECTIO_LOG, NEXTFLOW_LOG] if own else [NEXTFLOW_LOG]
        else:
            candidates = [_newest_log(launch)]
        for i, rel in enumerate(candidates):
            try:
                with open_confined(launch, rel) as f:
                    return strip_escapes(tail_of(f, TAIL).decode("utf-8", "replace"))
            except NotFound:
                if i == len(candidates) - 1:
                    raise
    raise NotFound(source)  # not reached: there is always one candidate


@router.get("/runs/{run_id}/logs", response_class=PlainTextResponse)
def run_log(
    request: Request, run_id: str, source: Literal["head-out", "head-err", "engine"] = "engine"
) -> PlainTextResponse:
    with read(request) as conn:
        row = run_row(conn, run_id)
    runs_root = request.app.state.settings.runs_root
    try:
        text = request.app.state.files.run(
            lambda: _read(runs_root, run_id, row.engine, row.origin, source), READ_TIMEOUT_S
        )
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None
    except (NotAllowed, NotFound, OSError) as exc:  # missing, a symlink, not private, not a file
        raise not_found(f"no {source} log for this run: {exc}", "log-not-found") from None
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8", headers=HEADERS)
