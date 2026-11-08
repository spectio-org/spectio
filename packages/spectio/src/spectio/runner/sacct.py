"""`sacct` for failed jobs and job resources (P1 Task 29; dev-env §15.3 req. 15).

`sacct` loads the cluster's accounting database, which other users share, so every call is
bounded: job IDs of the form `^[0-9]{1,12}(_[0-9]{1,8})?$` only, checked before any call, at
most `BATCH` per call; the tool's path as `spectio init` stored it, run as a list of arguments
(no shell) with an explicit environment (`PATH` from that path, `SLURM_TIME_FORMAT=standard`,
`TZ=UTC`, nothing inherited) and `TIMEOUT_S`, after which its process group is killed; only the
server user's own jobs asked (`--user=<euid>`), never with `--duplicates`; its output read up to
`MAX_OUTPUT` and parsed as data, field by field, with a random delimiter per call. A job line is
kept only when its `WorkDir` is one the caller expects for that job (the directory it was
launched from, SEC-P3T29-01) and its `Submit` is not before the run's launch (inbox #116 rule
10 (b), FU-P3-53). `SacctLimiter` holds the server-wide pace: one call in flight, one call per
`INTERVAL_S`.

The fields asked for (`FORMAT`, `WorkDir` among them) and their units, and whether `-j` alone
returns other users' jobs, are [to be validated] on `slurm-mini` (P1 Task 22) and at EMBL: a
number with no unit is read as bytes, `K`, `M`, `G`, `T` as powers of 1024, and an older
`ReqMem` suffix `n` (per node) or `c` (per CPU) is multiplied by `NNodes` or `NCPUS`, so
`req_mem_bytes` is the job's whole request. The efficiency fields (P1 Task 34, schedulers §3.6):
`TotalCPU` is summed over the job's step rows (`<id>.batch`, `<id>.extern`, `<id>.<n>`), as `seff`
does, and the allocation row's own is used only when no step row has one; a step row joins the
job line printed just before it, with the same base ID, having an empty WorkDir of its own
(SchedMD's sacct/options.c and sacct/print.c, CON-PRE-15; [to be validated] on `slurm-mini`).
"""

import contextlib
import logging
import os
import re
import secrets
import signal
import stat
import subprocess
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

JOB_ID = re.compile(r"[0-9]{1,12}(_[0-9]{1,8})?")
FORMAT = (
    "JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,TotalCPU,NCPUS,NNodes,"
    "Partition,Account,QOS,AllocTRES,WorkDir,Submit"
)  # WorkDir not last: a newline in it leaves two fragments, neither with every field
_FIELDS = FORMAT.count(",") + 1
TIMEOUT_S = 10.0
INTERVAL_S = 60.0
BATCH = 100
MAX_PENDING = 100_000  # IDs waiting for a call; more are dropped until the queue drains
MAX_OUTPUT = 1048576
MAX_REASON = 256
SUBMIT_SKEW_S = 300.0  # a job's Submit may read this much before the run's launch (clocks)
DELIMITER_LEN = 16  # a multi-character `--delimiter` [to be validated] on slurm-mini
_DELIMITER_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

_STATE = re.compile(r"[A-Z_]{1,32}")
_EXIT = re.compile(r"([0-9]{1,3}):[0-9]{1,3}")
_MEMORY = re.compile(r"([0-9]{1,15}(?:\.[0-9]{1,6})?)([KMGTP]?)([nc]?)")
_DURATION = re.compile(
    r"(?:([0-9]{1,5})-)?(?:([0-9]{1,2}):)?([0-9]{1,2}):([0-9]{1,2})(\.[0-9]{1,6})?"
)
_COUNT = re.compile(r"[0-9]{1,9}")
_NAME = re.compile(r"[A-Za-z0-9_.,:+-]{1,128}")  # a partition, an account, a QOS
_TRES = re.compile(r"[A-Za-z0-9_.,:/=+-]{1,1024}")
_REASON = re.compile(rf"[A-Za-z0-9_.,:;()/ -]{{1,{MAX_REASON}}}")
_WORK_DIR = re.compile(r"/[^\x00-\x1f\x7f]{0,4095}")
_SUBMIT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")
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
    # The efficiency fields (P1 Task 34): CPU seconds over the job's steps, the allocation's
    # CPUs and nodes, and where and as whom SLURM ran it.
    total_cpu_s: float | None = None
    ncpus: int | None = None
    nnodes: int | None = None
    partition: str | None = None
    account: str | None = None
    qos: str | None = None
    alloc_tres: str | None = None


# Job ID → {normalised WorkDir it may have: the run's launch time, epoch seconds}.
Wanted = Mapping[str, Mapping[str, float]]
# Job ID → {normalised WorkDir: its row}; a job or a directory with no row is absent.
Found = dict[str, dict[str, SacctRow]]


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
    return {"PATH": str(path.parent), "SLURM_TIME_FORMAT": "standard", "TZ": "UTC"}


def new_delimiter() -> str:
    """SEC-PRE-11: a delimiter no WorkDir can carry on purpose, since it is drawn per call."""
    return "".join(secrets.choice(_DELIMITER_CHARS) for _ in range(DELIMITER_LEN))


def sacct_argv(path: Path, ids: list[str], delimiter: str) -> list[str]:
    return [
        str(path),
        "--parsable2",
        "--noheader",
        f"--delimiter={delimiter}",
        "-j",
        ",".join(ids),
        f"--user={os.geteuid()}",
        f"--format={FORMAT}",
    ]


def sacct_jobs(
    wanted: Wanted,
    timeout_s: float = TIMEOUT_S,
    *,
    sacct: Path,
    dropped: Counter[str] | None = None,
) -> Found | None:
    """The rows `sacct` gives for the `wanted` jobs and directories (`parse_sacct`); None when
    it failed, timed out or said too much. Raises Refused, before any call, for an ID or a
    tool that is not accepted."""
    ids = check_ids(wanted)
    check_tool(sacct)
    delimiter = new_delimiter()
    argv = sacct_argv(sacct, ids, delimiter)
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
    return parse_sacct(data.decode("utf-8", "replace"), wanted, delimiter, dropped)


def _kill(proc: "subprocess.Popen[bytes]") -> None:
    with contextlib.suppress(ProcessLookupError):  # it ended just then
        os.killpg(proc.pid, signal.SIGKILL)


# --- Parsing, field by field --------------------------------------------------------------


@dataclass
class _Candidate:
    row: SacctRow
    rss: int | None
    cpu: float | None = None  # the sum over its steps, None until a step has one


def parse_sacct(
    text: str, wanted: Wanted, delimiter: str, dropped: Counter[str] | None = None
) -> Found:
    """The rows of `--parsable2 --noheader --delimiter=<delimiter>` output for the `wanted` jobs
    (inbox #116 rule 10 (b)). A line that does not split into FORMAT's fields is dropped. A job
    line is a candidate for (ID, directory) only when its WorkDir, `normpath`ed and never
    resolved, is one `wanted` lists for the ID and its Submit is not before that run's launch
    less SUBMIT_SKEW_S; a job line of another WorkDir is counted in `dropped`. A step line
    (`<id>.batch`, `<id>.0` …) adds its MaxRSS and TotalCPU to the candidate printed just before
    it with the same base ID, and to nothing else. Of the candidates for (ID, directory), the
    RESIZING ones are left out; exactly one other is the row, and its CPU and memory are None
    when a RESIZING one was there (its steps are not summed); none, or two or more, give no row."""
    found: dict[tuple[str, str], list[_Candidate]] = {}
    current: tuple[str, _Candidate] | None = None  # the last job line's base ID and candidate
    for line in text.splitlines():
        parts = line.split(delimiter)
        if len(parts) != _FIELDS:
            current = None
            continue
        job, state, exit_code, reason, max_rss, elapsed, req_mem, time_limit = parts[:8]
        total_cpu, ncpus, nnodes, partition, account, qos, tres, work_dir, submit = parts[8:]
        base, _, step = job.partition(".")
        if step:
            if current is not None and current[0] == base:
                _add_step(current[1], max_rss, total_cpu)
            else:
                current = None
            continue
        current = None
        dirs = wanted.get(base)
        if dirs is None:
            continue
        where = os.path.normpath(work_dir) if _WORK_DIR.fullmatch(work_dir) else None
        if where is None or where not in dirs:
            if dropped is not None:
                dropped[base] += 1
            continue
        submitted = _submit(submit)
        if submitted is None or submitted < dirs[where] - SUBMIT_SKEW_S:
            continue
        cpus, nodes = _count(ncpus), _count(nnodes)
        row = SacctRow(
            state=_state(state),
            exit_code=_exit(exit_code),
            reason=_reason(reason),
            max_rss_bytes=None,
            elapsed_s=_duration(elapsed),
            req_mem_bytes=_req_mem(req_mem, cpus, nodes),
            time_limit_s=_duration(time_limit),
            work_dir=work_dir,
            total_cpu_s=_cpu_seconds(total_cpu),
            ncpus=cpus,
            nnodes=nodes,
            partition=_text(partition, _NAME),
            account=_text(account, _NAME),
            qos=_text(qos, _NAME),
            alloc_tres=_text(tres, _TRES),
        )
        candidate = _Candidate(row, _memory(max_rss))
        found.setdefault((base, where), []).append(candidate)
        current = base, candidate
    rows: Found = {}
    for (job, where), candidates in found.items():
        final = [c for c in candidates if c.row.state != "RESIZING"]
        if len(final) != 1:
            continue
        (one,) = final
        if len(final) < len(candidates):  # resized: the RESIZING record's steps are elsewhere
            row = replace(one.row, max_rss_bytes=None, total_cpu_s=None)
        else:
            cpu = one.row.total_cpu_s if one.cpu is None else round(one.cpu, 6)
            row = replace(one.row, max_rss_bytes=one.rss, total_cpu_s=cpu)
        rows.setdefault(job, {})[where] = row
    return rows


def _add_step(candidate: _Candidate, max_rss: str, total_cpu: str) -> None:
    if (used := _memory(max_rss)) is not None:
        candidate.rss = max(used, candidate.rss or 0)
    if (spent := _cpu_seconds(total_cpu)) is not None:
        candidate.cpu = (candidate.cpu or 0.0) + spent


def _submit(value: str) -> float | None:
    """Submit, `YYYY-MM-DDTHH:MM:SS` in UTC (`TZ=UTC` in the call's environment), as epoch
    seconds; None for `Unknown` or anything else."""
    if not _SUBMIT.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return None


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


def _req_mem(value: str, cpus: int | None, nodes: int | None) -> int | None:
    """The job's whole memory request: an older `ReqMem` per CPU (`c`) or per node (`n`) times
    NCPUS or NNodes, None when that count is not known."""
    found = _MEMORY.fullmatch(value)
    amount = _memory(value)
    if found is None or amount is None or not found[3]:
        return amount
    times = cpus if found[3] == "c" else nodes
    return None if times is None else amount * times


def _count(value: str) -> int | None:
    return int(value) if _COUNT.fullmatch(value) else None


def _text(value: str, pattern: re.Pattern[str]) -> str | None:
    return value if pattern.fullmatch(value) else None


def _duration(value: str) -> int | None:
    """`[D-]HH:MM:SS` or `MM:SS[.ms]`; None for `UNLIMITED`, `Partition_Limit` or anything else."""
    seconds = _cpu_seconds(value)
    return None if seconds is None else int(seconds)


def _cpu_seconds(value: str) -> float | None:
    """A duration with its fraction (`TotalCPU` is `[D-][HH:]MM:SS.mmm`), None when it is not."""
    found = _DURATION.fullmatch(value)
    if found is None:
        return None
    days, hours, minutes, seconds = (int(g) if g else 0 for g in found.groups()[:4])
    if found[1] and not found[2]:  # "D-MM:SS" is not a sacct form
        return None
    whole = ((days * 24 + hours) * 60 + minutes) * 60 + seconds
    return whole + float(found[5]) if found[5] else float(whole)


# --- The limiter ----------------------------------------------------------------------------


Call = Callable[[list[str]], Found | None]


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

    def run_once(self) -> tuple[list[str], Found | None] | None:
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
