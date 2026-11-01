"""`sacct` for failed jobs and job resources (P1 Task 29; dev-env §15.3 req. 15).

`sacct` loads the cluster's accounting database, which other users share, so every call is
bounded: job IDs of the form `^[0-9]{1,12}(_[0-9]{1,8})?$` only, checked before any call, at
most `BATCH` per call; the tool's path as `spectio init` stored it, run as a list of arguments
(no shell) with an explicit environment (`PATH` from that path, `SLURM_TIME_FORMAT=standard`,
nothing inherited) and `TIMEOUT_S`, after which its process group is killed; only the server
user's own jobs asked (`--user=<euid>`); its output read up to `MAX_OUTPUT` and parsed as data,
field by field, each row with its `WorkDir`, which the caller compares with the directory the
job was launched from (SEC-P3T29-01). `SacctLimiter` holds the server-wide pace: one call in
flight, one call per `INTERVAL_S`.

The fields asked for (`FORMAT`, `WorkDir` among them) and their units, and whether `-j` alone
returns other users' jobs, are [to be validated] on `slurm-mini` (P1 Task 22) and at EMBL: a
number with no unit is read as bytes, `K`, `M`, `G`, `T` as powers of 1024, and an older
`ReqMem` suffix `n` (per node) or `c` (per CPU) is dropped.
"""

import contextlib
import logging
import os
import re
import signal
import stat
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

log = logging.getLogger(__name__)

JOB_ID = re.compile(r"[0-9]{1,12}(_[0-9]{1,8})?")
FORMAT = "JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,WorkDir"
TIMEOUT_S = 10.0
INTERVAL_S = 60.0
BATCH = 100
MAX_PENDING = 100_000  # IDs waiting for a call; more are dropped until the queue drains
MAX_OUTPUT = 1048576
MAX_REASON = 256

_STATE = re.compile(r"[A-Z_]{1,32}")
_EXIT = re.compile(r"([0-9]{1,3}):[0-9]{1,3}")
_MEMORY = re.compile(r"([0-9]{1,15}(?:\.[0-9]{1,6})?)([KMGTP]?)[nc]?")
_DURATION = re.compile(
    r"(?:([0-9]{1,5})-)?(?:([0-9]{1,2}):)?([0-9]{1,2}):([0-9]{1,2})(?:\.[0-9]+)?"
)
_REASON = re.compile(rf"[A-Za-z0-9_.,:;()/ -]{{1,{MAX_REASON}}}")
_WORK_DIR = re.compile(r"/[^\x00-\x1f\x7f]{0,4095}")
_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}


class Refused(ValueError):
    """A job ID or a tool path that is never passed to `sacct`."""


@dataclass(frozen=True)
class SacctRow:
    state: str | None
    exit_code: int | None
    reason: str | None
    max_rss_bytes: int | None
    elapsed_s: int | None
    req_mem_bytes: int | None
    time_limit_s: int | None
    work_dir: str | None = None  # the job's WorkDir, as sacct gave it


def check_ids(ids: Iterable[str]) -> list[str]:
    """`ids` once each, in order; Refused unless each is a job ID and they are at most BATCH."""
    found = list(dict.fromkeys(ids))
    for job in found:
        if not isinstance(job, str) or not JOB_ID.fullmatch(job):
            raise Refused(f"not a SLURM job ID: {str(job)[:32]!r}")
    if not found or len(found) > BATCH:
        raise Refused(f"between 1 and {BATCH} job IDs per call, not {len(found)}")
    return found


def check_tool(path: Path) -> None:
    """The stored `sacct`: an absolute path to a regular file that only its owner (root or the
    user) can write."""
    if not path.is_absolute():
        raise Refused(f"the sacct path {path} is not absolute")
    try:
        st = os.stat(path)
    except OSError as exc:
        raise Refused(f"sacct at {path}: {exc.strerror}") from None
    if not stat.S_ISREG(st.st_mode) or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise Refused(f"sacct at {path} is not a regular file, or others can write it")
    if st.st_uid not in (0, os.geteuid()):
        raise Refused(f"sacct at {path} belongs to uid {st.st_uid}")


def sacct_env(path: Path) -> dict[str, str]:
    return {"PATH": str(path.parent), "SLURM_TIME_FORMAT": "standard"}


def sacct_argv(path: Path, ids: list[str]) -> list[str]:
    return [
        str(path),
        "--parsable2",
        "--noheader",
        "-j",
        ",".join(ids),
        f"--user={os.geteuid()}",
        f"--format={FORMAT}",
    ]


def sacct_jobs(
    ids: list[str], timeout_s: float = TIMEOUT_S, *, sacct: Path
) -> dict[str, SacctRow] | None:
    """One row per ID that `sacct` knows; None when it failed, timed out or said too much.
    Raises Refused, before any call, for an ID or a tool that is not accepted."""
    ids = check_ids(ids)
    check_tool(sacct)
    argv = sacct_argv(sacct, ids)
    with subprocess.Popen(  # noqa: S603 - an argument list of checked values, no shell
        argv,
        env=sacct_env(sacct),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    ) as proc:
        timer = threading.Timer(timeout_s, _kill, (proc,))
        timer.start()
        try:
            data = proc.stdout.read(MAX_OUTPUT + 1) if proc.stdout else b""
            if len(data) > MAX_OUTPUT:
                _kill(proc)
            code = proc.wait()
        finally:
            timer.cancel()
    if code != 0 or len(data) > MAX_OUTPUT:
        log.warning(
            "sacct gave no answer for %d IDs (exit %s, %d bytes)", len(ids), code, len(data)
        )
        return None
    return parse_sacct(data.decode("utf-8", "replace"), set(ids))


def _kill(proc: "subprocess.Popen[bytes]") -> None:
    with contextlib.suppress(ProcessLookupError):  # it ended just then
        os.killpg(proc.pid, signal.SIGKILL)


# --- Parsing, field by field --------------------------------------------------------------


def parse_sacct(text: str, wanted: set[str]) -> dict[str, SacctRow]:
    """The rows of `--parsable2 --noheader` output for the `wanted` jobs: the job's own line for
    its state, limits and WorkDir, the largest `MaxRSS` of its steps (`<id>.batch`, `<id>.0` …).
    WorkDir is the last field: a `|` in it is kept."""
    rows: dict[str, SacctRow] = {}
    rss: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split("|", 8)
        if len(parts) != 9:
            continue
        job, state, exit_code, reason, max_rss, elapsed, req_mem, time_limit, work_dir = parts
        base, _, step = job.partition(".")
        if base not in wanted:
            continue
        if (used := _memory(max_rss)) is not None:
            rss[base] = max(used, rss.get(base, 0))
        if step:
            continue
        rows[base] = SacctRow(
            state=_state(state),
            exit_code=_exit(exit_code),
            reason=_reason(reason),
            max_rss_bytes=None,
            elapsed_s=_duration(elapsed),
            req_mem_bytes=_memory(req_mem),
            time_limit_s=_duration(time_limit),
            work_dir=work_dir if _WORK_DIR.fullmatch(work_dir) else None,
        )
    return {job: replace(row, max_rss_bytes=rss.get(job)) for job, row in rows.items()}


def _state(value: str) -> str | None:
    word = value.split(" ", 1)[0]  # "CANCELLED by 1000"
    return word if _STATE.fullmatch(word) else None


def _exit(value: str) -> int | None:
    found = _EXIT.fullmatch(value)
    return int(found[1]) if found else None


def _reason(value: str) -> str | None:
    if value in ("", "None") or not _REASON.fullmatch(value):
        return None
    return value


def _memory(value: str) -> int | None:
    found = _MEMORY.fullmatch(value)
    if found is None:
        return None
    return int(float(found[1]) * _UNITS[found[2]])


def _duration(value: str) -> int | None:
    """`[D-]HH:MM:SS` or `MM:SS[.ms]`; None for `UNLIMITED`, `Partition_Limit` or anything else."""
    found = _DURATION.fullmatch(value)
    if found is None:
        return None
    days, hours, minutes, seconds = (int(g) if g else 0 for g in found.groups())
    if found[1] and not found[2]:  # "D-MM:SS" is not a sacct form
        return None
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


# --- The limiter ----------------------------------------------------------------------------


Call = Callable[[list[str]], dict[str, SacctRow] | None]


class SacctLimiter:
    """The server's one gate to `sacct`: IDs are queued once each (at most `max_pending`), and
    `run_once` makes one call for the next `batch` of them when `interval_s` has passed since
    the last call started and no call is in flight. The caller's thread runs the call: the
    server runs it on a thread of its own, never the writer's or a request's."""

    def __init__(
        self,
        call: Call,
        *,
        interval_s: float = INTERVAL_S,
        batch: int = BATCH,
        max_pending: int = MAX_PENDING,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._call = call
        self._interval = interval_s
        self._batch = batch
        self._max_pending = max_pending
        self._clock = clock
        self._pending: dict[str, None] = {}  # insertion order: first asked, first called
        self._last: float | None = None
        self._busy = False
        self._lock = threading.Lock()

    def request(self, ids: Iterable[str]) -> list[str]:
        """Queue the job IDs among `ids`; returns those now queued (none past `max_pending`)."""
        queued = []
        with self._lock:
            for job in ids:
                if not isinstance(job, str) or not JOB_ID.fullmatch(job):
                    continue
                if job not in self._pending and len(self._pending) >= self._max_pending:
                    break
                self._pending[job] = None
                queued.append(job)
        return queued

    def pending(self) -> int:
        with self._lock:
            return len(self._pending)

    def wait_s(self) -> float | None:
        """Seconds until the next call may start; None when nothing is queued."""
        with self._lock:
            if not self._pending:
                return None
            if self._last is None:
                return 0.0
            return max(0.0, self._last + self._interval - self._clock())

    def run_once(self) -> tuple[list[str], dict[str, SacctRow] | None] | None:
        """One call when one is due: the IDs asked and the rows (None: the call failed).
        None when nothing is queued, it is too soon, or a call is in flight."""
        with self._lock:
            if self._busy or not self._pending:
                return None
            if self._last is not None and self._clock() < self._last + self._interval:
                return None
            ids = list(self._pending)[: self._batch]
            for job in ids:
                del self._pending[job]
            self._busy, self._last = True, self._clock()
        try:
            rows = self._call(ids)
        except Exception:  # a refusal or a crash: those IDs get no answer, the next call runs
            log.exception("sacct call failed")
            rows = None
        finally:
            with self._lock:
                self._busy = False
        return ids, rows
