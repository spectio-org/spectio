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
10 (b), FU-P3-53). Each call is bounded in time too: `-S` the earliest launch of its jobs less
`SUBMIT_SKEW_S`, `-E now`, never from Epoch 0 (CON-SLURM-POLL-03). `SacctLimiter` holds the
server-wide pace: one call in flight, one call per `INTERVAL_S`, doubled up to `MAX_INTERVAL_S`
after a failed or slow call (CON-SLURM-POLL-02; schedulers §3.8, the SLURM query budget). A
call that would fail every time (a refused tool, too much output for one ID) is final; a batch
that says too much is split in two; any other failure is retried unchanged (SEC-P3FU106A-01).
A window the site's `MaxQueryTimeRange` refuses is final for the jobs whose launch set `-S`
(FU-P3-106b, SEC-P3FU106B-01): read from the first `MAX_STDERR` bytes of its error text,
`TOO_WIDE`.

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
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

log = logging.getLogger(__name__)

JOB_ID = re.compile(r"[0-9]{1,12}(_[0-9]{1,8})?")
FORMAT = (
    "JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,TotalCPU,NCPUS,NNodes,"
    "Partition,Account,QOS,AllocTRES,WorkDir,Submit"
)  # WorkDir not last: a newline in it leaves two fragments, neither with every field
_FIELDS = FORMAT.count(",") + 1
TIMEOUT_S = 30.0
INTERVAL_S = 60.0
MAX_INTERVAL_S = 600.0  # the back-off's ceiling
SLOW_S = 5.0  # a call slower than this is back-pressure: the next one waits longer
BATCH = 100
MAX_PENDING = 100_000  # IDs waiting for a call; more are dropped until the queue drains
MAX_OUTPUT = 1048576
MAX_REASON = 256
MAX_STDERR = 4096
# slurmdbd's text for a window over `MaxQueryTimeRange` (ESLURM_DB_QUERY_TOO_WIDE: SchedMD
# slurm src/common/slurm_errno.c, sent by src/slurmdbd/proc_req.c `_get_jobs_cond`), which sacct
# logs as an error and exits 1; the exact line is [to be validated] on slurm-mini.
TOO_WIDE = b"Too wide of a date range in query"
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


class TooMuch(Exception):
    """`sacct` said more than MAX_OUTPUT: asked again, the same IDs would say as much."""


class TooWide(Exception):
    """The site's `MaxQueryTimeRange` refused the call's window: any IDs would fail the same."""


class Unanswered(Enum):
    FINAL = "final"  # a call that fails every time it is made: its IDs are given up
    SITE_LIMIT = "max_query_time_range"  # final as well, for the site's limit (FU-P3-106b)


FINAL = Unanswered.FINAL
SITE_LIMIT = Unanswered.SITE_LIMIT


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
Answer = Found | None | Unanswered  # None: failed, to be asked again


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
    user) can write. An OSError of the stat itself (ENOENT, EIO, ESTALE) may pass, so it is
    raised as is, not Refused: the call is retried (CR-P3FU106A-04)."""
    if not path.is_absolute():
        raise Refused(f"the sacct path {path} is not absolute")
    st = os.stat(path)
    if not stat.S_ISREG(st.st_mode) or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise Refused(f"sacct at {path} is not a regular file, or others can write it")
    if st.st_uid not in (0, os.geteuid()):
        raise Refused(f"sacct at {path} belongs to uid {st.st_uid}")


def sacct_env(path: Path) -> dict[str, str]:
    return {"PATH": str(path.parent), "SLURM_TIME_FORMAT": "standard", "TZ": "UTC"}


def new_delimiter() -> str:
    """SEC-PRE-11: a delimiter no WorkDir can carry on purpose, since it is drawn per call."""
    return "".join(secrets.choice(_DELIMITER_CHARS) for _ in range(DELIMITER_LEN))


def sacct_argv(path: Path, ids: list[str], delimiter: str, start: float) -> list[str]:
    """The call; `start` (epoch seconds) is its `-S`, written in UTC as `TZ=UTC` reads it."""
    since = datetime.fromtimestamp(max(0.0, start), UTC).strftime("%Y-%m-%dT%H:%M:%S")
    return [
        str(path),
        "--parsable2",
        "--noheader",
        f"--delimiter={delimiter}",
        "-j",
        ",".join(ids),
        f"--user={os.geteuid()}",
        "-S",
        since,
        "-E",
        "now",
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
    it failed or timed out. Raises Refused, before any call, for an ID or a tool that is not
    accepted, OSError when the tool cannot be read for now, TooMuch when it said more than
    MAX_OUTPUT, and TooWide when it failed with the site's `TOO_WIDE`."""
    ids = check_ids(wanted)
    check_tool(sacct)
    delimiter = new_delimiter()
    start = min(since for dirs in wanted.values() for since in dirs.values()) - SUBMIT_SKEW_S
    argv = sacct_argv(sacct, ids, delimiter, start)
    with (
        tempfile.TemporaryFile() as err,  # a file, not a pipe: it never blocks the tool
        subprocess.Popen(  # noqa: S603 - an argument list of checked values, no shell
            argv,
            env=sacct_env(sacct),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=err,
            start_new_session=True,
        ) as proc,
    ):
        timer = threading.Timer(timeout_s, _kill, (proc,))
        timer.start()
        try:
            data = proc.stdout.read(MAX_OUTPUT + 1) if proc.stdout else b""
            if len(data) > MAX_OUTPUT:
                _kill(proc)
            code = proc.wait()
        finally:
            timer.cancel()
        err.seek(0)
        said = err.read(MAX_STDERR)
    if len(data) > MAX_OUTPUT:
        raise TooMuch(f"sacct said over {MAX_OUTPUT} bytes for {len(ids)} IDs")
    if code != 0 and TOO_WIDE in said:
        raise TooWide(f"sacct refused the window of {len(ids)} IDs: the site's MaxQueryTimeRange")
    if code != 0:
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
    `run_once` makes one call for the next `batch` of them when the interval has passed since
    the last call started and no call is in flight. The interval is `interval_s`, doubled after
    a call that failed or took over `slow_s`, up to `max_interval_s`, and reset by a quick
    answer. `later` queues IDs once a delay has passed (a follow-up). The caller's thread runs
    the call: the server runs it on a thread of its own, never the writer's or a request's.
    A Refused call (a policy refusal of the tool or an ID) is FINAL, logged at warning (the same
    text at most once per `max_interval_s`, CR-P3FU106A-04), and one sacct refused for the
    site's `MaxQueryTimeRange` (TooWide) is SITE_LIMIT: the caller gives up the jobs whose
    launch set `-S` and puts the rest back (SEC-P3FU106B-01).
    Too much output is the only failure that points at the IDs: the batch is split in two, each
    of its IDs recorded with half its size until it is next taken, and one ID alone is FINAL.
    Any other failure (a timeout, a non-zero exit, an OSError of the tool's stat) answers None:
    the caller puts the batch back unchanged under the back-off, until it gives up (GIVE_UP_S in
    `spectio_server.failure`); an outage splits nothing (SEC-P3FU106A-01, CR-P3FU106A-05)."""

    def __init__(
        self,
        call: Call,
        *,
        interval_s: float = INTERVAL_S,
        batch: int = BATCH,
        max_pending: int = MAX_PENDING,
        max_interval_s: float = MAX_INTERVAL_S,
        slow_s: float = SLOW_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._call = call
        self._base = self._interval = interval_s
        self._max_interval = max_interval_s
        self._slow = slow_s
        self._later: dict[str, float] = {}  # job ID → when it is queued
        self._batch = batch
        self._max_pending = max_pending
        self._clock = clock
        self._pending: dict[str, None] = {}  # insertion order: first asked, first called
        self._size: dict[str, int] = {}  # job ID of a split batch → at most this many per call
        self._last: float | None = None
        self._busy = False
        self._warned: tuple[str, float] | None = None  # the last refusal logged, and when
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
                self._later.pop(job, None)  # its follow-up rides along with this call
                queued.append(job)
        return queued

    def later(self, ids: Iterable[str], delay_s: float) -> list[str]:
        """Queue the job IDs among `ids` once `delay_s` has passed; returns those taken (none
        past `max_pending`)."""
        taken = []
        with self._lock:
            due = self._clock() + delay_s
            for job in ids:
                if JOB_ID.fullmatch(job) and len(self._later) < self._max_pending:
                    self._later[job] = due
                    taken.append(job)
        return taken

    def _due(self, now: float) -> None:
        """Move the follow-ups due by `now` into the queue; under the lock."""
        for job, due in list(self._later.items()):
            if due <= now and (job in self._pending or len(self._pending) < self._max_pending):
                self._pending[job] = None
                del self._later[job]

    def pending(self) -> int:
        with self._lock:
            return len(self._pending)

    def wait_s(self) -> float | None:
        """Seconds until the next call may start; None when nothing is queued or due later."""
        with self._lock:
            now = self._clock()
            self._due(now)
            if not self._pending and not self._later:
                return None
            ready = 0.0 if self._pending else min(self._later.values()) - now
            pace = 0.0 if self._last is None else self._last + self._interval - now
            return max(0.0, ready, pace)

    def run_once(self) -> tuple[list[str], Answer] | None:
        """One call when one is due: the IDs asked and the rows (None: the call failed, FINAL:
        it would fail every time). None when nothing is queued, it is too soon, or a call is
        in flight."""
        with self._lock:
            self._due(self._clock())
            if self._busy or not self._pending:
                return None
            if self._last is not None and self._clock() < self._last + self._interval:
                return None
            ids: list[str] = []
            cap = self._batch  # the smallest recorded size among the IDs taken
            for job in self._pending:
                cap = min(cap, self._size.get(job, self._batch))
                if len(ids) >= cap:
                    break
                ids.append(job)
            sizes = {job: self._size.pop(job) for job in ids if job in self._size}
            for job in ids:
                del self._pending[job]
            started = self._clock()
            self._busy, self._last = True, started
        rows: Answer = None
        try:
            rows = self._call(ids)
        except Refused as exc:  # the tool or an ID: every call of them would be refused
            self._log_refused(len(ids), str(exc))
            rows = FINAL
        except TooWide as exc:  # the site's window limit: the caller gives up the oldest jobs
            log.warning("%s", exc)
            rows = SITE_LIMIT
        except TooMuch as exc:  # split in two, until one ID alone says too much
            log.warning("%s", exc)
            if len(ids) == 1:
                rows = FINAL
            else:
                sizes = dict.fromkeys(ids, (len(ids) + 1) // 2)  # two calls, not three
        except OSError as exc:  # the tool's stat, for now (ENOENT, EIO, ESTALE): retried
            log.warning("sacct not called for %d IDs: %s", len(ids), exc)
        except Exception:  # a crash: those IDs get no answer, the next call runs
            log.exception("sacct call failed")
        finally:
            with self._lock:
                self._busy = False
                # the sizes of IDs the caller gave up are dropped; a batch put back keeps its own
                self._size = {j: n for j, n in self._size.items() if j in self._pending}
                if rows is None:
                    self._size.update(sizes)
                if not isinstance(rows, dict) or self._clock() - started > self._slow:
                    self._interval = min(self._max_interval, 2 * self._interval)
                else:
                    self._interval = self._base
        return ids, rows

    def _log_refused(self, count: int, why: str) -> None:
        """At warning, unless the same text was logged less than `max_interval_s` ago: then at
        debug, as a refused tool refuses every call (CR-P3FU106A-04). Only one call is in
        flight, so this needs no lock."""
        now = self._clock()
        last = self._warned
        warn = last is None or last[0] != why or now - last[1] >= self._max_interval
        if warn:
            self._warned = (why, now)
        level = logging.WARNING if warn else logging.DEBUG
        log.log(level, "sacct not called for %d IDs: %s", count, why)
