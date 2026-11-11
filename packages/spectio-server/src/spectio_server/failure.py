"""The failure summary and the resources per job (P1 Task 29; api §5 note of 2026-10-28, Run and
Resources; architecture §13.7, Failure reason and Resources per task; dev-env §15.3 req. 15).

Where a failure's facts come from:

- the engine's events, through the projector: the exit code, the job ID, the requested and the
  measured resources (the Nextflow trace; Snakemake's `job_info`), and on Snakemake the SLURM
  state and reason that the SLURM executor plugin wrote in its error text, parsed here
  (`parse_smk_slurm_message`) and stored as `attempts.scheduler`, the text never;
- `sacct`, through the server's one `Accounting` (its limiter and its own thread), cached in
  memory and in `<run dir>/.spectio/sacct.json`; nothing here waits for it. While a run is
  live, only a Nextflow failure when it is first opened and a job whose SLURM panel is opened
  are asked; every other ended job waits for the run's end, then one sweep and one follow-up
  (CON-SLURM-POLL-01; schedulers §3.8, the SLURM query budget), made with no view when the
  projector ends the run (`sweep_run`, FU-P3-105c, schedulers §3.7);
- the job's files: the last lines of its log, and a Snakemake job's benchmark file, read by
  the job-file reader of P1 Task 28 (`files.taskfiles`, confined, escape sequences removed) in
  the file pool, with its timeout.
"""

import json
import logging
import os
import re
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Connection, func, select

from spectio.config import Settings
from spectio.environments import executor_of, read_as
from spectio.runner import sacct
from spectio.runner.rundir import private_dir, read_small, run_paths, write_file
from spectio.runner.sacct import BATCH, JOB_ID, SacctLimiter, SacctRow
from spectio_sdk.events import NextflowTrace
from spectio_server import efficiency
from spectio_server.files.confine import NotAllowed, NotFound, open_confined, read_at, safe_rel
from spectio_server.files.pool import FilePool, Stalled
from spectio_server.files.taskfiles import (
    AttemptFiles,
    Binary,
    attempt_dir,
    read_task_file,
    run_root,
)
from spectio_server.projector.runs import TERMINAL as RUN_ENDED
from spectio_server.store.schema import attempts, runs, tasks, workflow_versions, workflows

log = logging.getLogger(__name__)

CACHE_FILE = "sacct.json"  # in <run dir>/.spectio/
MAX_CACHE_BYTES = 8388608
LOG_TAIL_LINES = 20
MAX_BENCHMARK_BYTES = 65536
MAX_MEASURES = 200_000  # attempts whose benchmark is kept in memory (CR-P3T34-01)
MAX_BENCHMARKS_PER_VIEW = 500  # read by one view; later views read the rest (SEC-P3T34-01)
BENCHMARK_CHUNK = 100  # benchmarks kept as each batch is read, even past a timeout (CR-P3T34-03)
ENDED = ("succeeded", "failed", "aborted")
MIB = 1048576
FOLLOW_UP_S = 600.0  # a job answered with no terminal row is asked once more this much later
GIVE_UP_S = 86400.0  # a job whose calls fail is asked again until this long after it ended
MAX_RESOLVE = BATCH  # directories one view resolves for new jobs; later views the rest (CON-PRE-14)
MAX_REAL = 200_000  # resolved directories kept; emptied when full (CR-P3FU53-01)
# The states a job ends in (`sacct(1)`, JOB STATE CODES); a row in any other is not kept.
TERMINAL = frozenset(
    {"COMPLETED", "FAILED", "OUT_OF_MEMORY", "TIMEOUT", "CANCELLED", "NODE_FAIL", "PREEMPTED"}
    | {"BOOT_FAIL", "DEADLINE"}
)
_MAX = 2**63 - 1
_RUNNING = object()  # a run's resolve that has started

Status = Literal["available", "pending", "unavailable"]
# Runs a job in the file pool with the view's timeout; False when it did not end in time.
InPool = Callable[[Callable[[], None]], bool]
Where = tuple[frozenset[str], float, float | None]  # a job's directories, launch, end


# --- Snakemake's SLURM executor plugin, in its own words -------------------------------------


@dataclass(frozen=True)
class SchedulerInfo:
    state: str
    reason: str | None
    state_source: str = "engine_message"


# The four forms of `snakemake-executor-plugin-slurm` 2.8.0 (`__init__.py:1546-1606`, read for
# architecture §13.7); versioned with that release, [to be validated] for the others.
_SLURM_STATE = re.compile(
    r"SLURM-job '[0-9_]{1,24}' failed(?P<node> due to a node failure)?, "
    r"SLURM status is: '(?P<state>[A-Z_]{1,32})'\.(?P<rest>[^\n]{0,600})"
)
_STEP = r"Step [0-9]{1,3}: [A-Za-z0-9_ ]{1,64}?"
_REASONS = re.compile(rf" Reasons?: ({_STEP}(?:, {_STEP})*)\.(?:\s|$)")


def parse_smk_slurm_message(text: str | None) -> SchedulerInfo | None:
    """The SLURM state and reason of a Snakemake job's error text, or None when it holds none.
    The reason is kept only as the plugin builds it ("Step <n>: <reason>, …"), else None."""
    if not text:
        return None
    found = _SLURM_STATE.search(text)  # the SDK cut it at MAX_MESSAGE_CHARS
    if found is None:
        return None
    if found["node"]:
        return SchedulerInfo(found["state"], "node failure")
    reasons = _REASONS.match(found["rest"])
    return SchedulerInfo(found["state"], reasons[1] if reasons else None)


# --- Resources from the events (the projector's side) ----------------------------------------


def _number(value: object) -> float | None:
    """A non-negative finite number from a trace or `job_info` value, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = float(value) if re.fullmatch(r"[0-9]{1,19}(\.[0-9]{1,9})?", value) else None
    if isinstance(value, int | float) and 0 <= value <= _MAX:
        return float(value)
    return None


def _whole(value: object, scale: float = 1) -> int | None:
    found = _number(value)
    return None if found is None or found * scale > _MAX else int(found * scale)


def _seconds(value: object, scale: float) -> float | None:
    found = _number(value)
    return None if found is None else found * scale


def trace_resources(trace: NextflowTrace | None) -> dict[str, Any]:
    """The requested `cpus`, `memory` (bytes) and `time` (ms), and the measured `realtime`
    (ms), `%cpu` and `peak_rss` (bytes) of a trace record (`TraceRecord.groovy:69-112`); only
    the values it has."""
    if trace is None:
        return {}
    found = {
        "cpus": _whole(trace.cpus),
        "memory_bytes": _whole(trace.memory),
        "time_s": _seconds(trace.time, 0.001),
        "realtime_s": _seconds(trace.realtime, 0.001),
        "cpu_percent": _number(trace.pct_cpu),
        "peak_rss_bytes": _whole(trace.peak_rss),
    }
    return {k: v for k, v in found.items() if v is not None}


def smk_resources(threads: int | None, resources: dict[str, Any]) -> dict[str, Any]:
    """The requested `threads`, `mem_mb` (or `mem_mib`) and `runtime` (minutes) of `job_info`.
    `mem_mb` is read as MiB, as the SLURM executor plugin passes it to `--mem` [to be
    validated]."""
    memory = resources.get("mem_mb", resources.get("mem_mib"))
    found = {
        "cpus": _whole(threads),
        "memory_bytes": _whole(memory, MIB),
        "time_s": _seconds(resources.get("runtime"), 60),
    }
    return {k: v for k, v in found.items() if v is not None}


# The SLURM request (P1 Task 34; api §5 note of 2026-11-07): the keys, each null when not asked.
REQUEST = (
    "partition",
    "account",
    "qos",
    "cpus",
    "mem_bytes",
    "mem_per_cpu_bytes",
    "time_limit_s",
    "gres",
    "constraint",
    "nodes",
    "tasks",
)
_SLURM_TEXT = re.compile(r"[A-Za-z0-9_.,:+=/&|*\[\]-]{1,256}")  # a partition, a gres, a constraint


def _slurm_text(value: object) -> str | None:
    return value if isinstance(value, str) and _SLURM_TEXT.fullmatch(value) else None


def _request(found: dict[str, Any]) -> dict[str, Any] | None:
    """The request with only the values known, or None when it has none."""
    kept = {k: v for k, v in found.items() if v is not None}
    return kept or None


def smk_request(threads: int | None, resources: dict[str, Any]) -> dict[str, Any] | None:
    """What a Snakemake job asks SLURM for, from `job_info.resources` as the SLURM executor
    plugin reads them (api §5 note of 2026-11-07): `cpus_per_task` else `threads`, `mem_mb`
    (MiB) unless `mem_mb_per_cpu` is set, `runtime` (minutes), `gres` else `gpu`."""
    per_cpu = _whole(resources.get("mem_mb_per_cpu"), MIB)
    memory = None if per_cpu is not None else resources.get("mem_mb", resources.get("mem_mib"))
    cpus = _whole(resources["cpus_per_task"]) if "cpus_per_task" in resources else _whole(threads)
    gpus = _whole(resources.get("gpu"))
    return _request(
        {
            "partition": _slurm_text(resources.get("slurm_partition")),
            "account": _slurm_text(resources.get("slurm_account")),
            "qos": _slurm_text(resources.get("qos")),
            "cpus": cpus,
            "mem_bytes": _whole(memory, MIB),
            "mem_per_cpu_bytes": per_cpu,
            "time_limit_s": _whole(resources.get("runtime"), 60),
            "gres": _slurm_text(resources.get("gres")) or (f"gpu:{gpus}" if gpus else None),
            "constraint": _slurm_text(resources.get("constraint")),
            "nodes": _whole(resources.get("nodes")),
            "tasks": _whole(resources.get("tasks")),
        }
    )


def nf_request(trace: NextflowTrace | None) -> dict[str, Any] | None:
    """What a Nextflow task asks for, from its trace record: `queue`, `cpus`, `memory`
    (bytes), `time` (ms) and `accelerator`, read as `gpu:<n>` [to be validated] on
    `slurm-mini`. `executor.account` and `clusterOptions` are not in the trace."""
    if trace is None:
        return None
    gpus = _whole(trace.accelerator)
    return _request(
        {
            "partition": _slurm_text(trace.queue),
            "cpus": _whole(trace.cpus),
            "mem_bytes": _whole(trace.memory),
            "time_limit_s": _whole(trace.time, 0.001),
            "gres": f"gpu:{gpus}" if gpus else None,
        }
    )


# --- sacct: the server's one accounting ------------------------------------------------------


class _CachedRow(BaseModel):
    """One job of `sacct.json`, read back strictly."""

    model_config = ConfigDict(extra="forbid", strict=True)

    state: str | None = Field(None, pattern=r"^[A-Z_]{1,32}$")
    exit_code: int | None = Field(None, ge=0, le=255)
    reason: str | None = Field(None, max_length=sacct.MAX_REASON, pattern=r"^[ -~]*$")
    max_rss_bytes: int | None = Field(None, ge=0, le=_MAX)
    elapsed_s: int | None = Field(None, ge=0, le=_MAX)
    req_mem_bytes: int | None = Field(None, ge=0, le=_MAX)
    time_limit_s: int | None = Field(None, ge=0, le=_MAX)
    work_dir: str | None = Field(None, pattern=r"^/[^\x00-\x1f\x7f]{0,4095}$")
    total_cpu_s: float | None = Field(None, ge=0, le=_MAX)  # P1 Task 34: absent before it
    ncpus: int | None = Field(None, ge=0, le=_MAX)
    nnodes: int | None = Field(None, ge=0, le=_MAX)
    partition: str | None = Field(None, pattern=r"^[A-Za-z0-9_.,:+-]{1,128}$")
    account: str | None = Field(None, pattern=r"^[A-Za-z0-9_.,:+-]{1,128}$")
    qos: str | None = Field(None, pattern=r"^[A-Za-z0-9_.,:+-]{1,128}$")
    alloc_tres: str | None = Field(None, pattern=r"^[A-Za-z0-9_.,:/=+-]{1,1024}$")
    wait_s: int | None = Field(None, ge=0, le=_MAX)  # FU-P3-105c: absent before it


class Accounting:
    """`sacct` for the whole server (dev-env §15.3 req. 15): one `SacctLimiter`, run by a thread
    of its own, so a call that hangs holds neither the writer nor a request until its timeout
    kills it. Per run, what `sacct` said of each job (a row, or None when it knew no such job),
    in memory and in `<run dir>/.spectio/sacct.json`, 0600, written by a rename in the run's
    checked directory and read back with no link followed. A run's file is read (`load`, in
    the file pool) before any of its jobs is asked (`want`), so a cached job is never asked
    again, after a rebuild too. A job whose call failed (an error, a timeout) is put back in
    the queue unchanged, as the limiter backs off, until GIVE_UP_S after it ended; then it is
    given up in memory, never stored (CON-SLURM-POLL-02). A batch whose answer is over
    MAX_OUTPUT is split in two by the limiter; a call that would fail every time (a refused
    tool, too much output for one ID) gives its jobs up at once (SEC-P3FU106A-01), and so does
    a window the site's `MaxQueryTimeRange` refuses, with that reason (FU-P3-106b). Only a row
    in a TERMINAL state is kept: a job
    `sacct` does not know yet, or not as ended (slurmdbd records a job after it ends, with a
    lag, [to be validated] on `slurm-mini`, P1 Task 22), is asked once more FOLLOW_UP_S later,
    with no view; then it is kept as None when that answer had no line for it, else given up
    in memory. So is a job with no line whose WorkDir is the directory it was launched from
    (the Nextflow attempt's work directory, Snakemake's launch directory), as it was given or
    resolved, and whose Submit is not before the run's launch: the lines of other jobs with
    that number, such as a local PID read as a SLURM ID, are dropped (SEC-P3T29-01; inbox #116
    rule 10 (b); WorkDir [to be validated] on `slurm-mini`). A job with no directory is never
    asked. Each call asks the (run, job) pairs queued when it starts; a run that asks a job
    during that call is queued again, with no follow-up counted (CON-PRE-16). A run the
    projector ends is handed over by `ended` and swept on this thread by `sweeper` (FU-P3-105c);
    each run whose rows changed is given to `on_rows` (its `attempt_metrics`); `close` drops
    what is not made yet."""

    def __init__(
        self,
        runs_root: Path,
        sacct_path: Path | None,
        *,
        enabled: bool = True,
        start_thread: bool = True,
        interval_s: float = sacct.INTERVAL_S,
        timeout_s: float = sacct.TIMEOUT_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.runs_root = runs_root
        self.enabled = enabled and sacct_path is not None
        self._path = sacct_path
        self._timeout = timeout_s
        self._clock = clock
        self._limiter = SacctLimiter(self._call, interval_s=interval_s, clock=clock)
        self._lock = threading.Lock()
        self._rows: dict[str, dict[str, SacctRow | None]] = {}
        self._loaded: set[str] = set()
        self._failed: dict[str, dict[str, str]] = {}  # run → job given up → its reason
        self._asked: dict[str, set[str]] = {}  # job ID → the runs that wait for it
        # (run, job) asked → its directories (normalised, and resolved), the run's launch time
        # and its end (None while live), epoch seconds
        self._where: dict[tuple[str, str], Where] = {}
        self._called: dict[tuple[str, str], Where] = {}  # the last call's
        self._logged: set[str] = set()  # runs whose dropped lines were logged
        self._followed: set[tuple[str, str]] = set()  # (run, job) whose follow-up is due
        self._deadline: dict[tuple[str, str], float] = {}  # (run, job) → given up after (clock)
        self._real: dict[str, str] = {}  # directory → its `realpath`, kept as each is resolved
        self._resolving: dict[str, object] = {}  # run → its resolve in flight (CR-P3FU53-01)
        self._wake = threading.Event()
        self._start_thread = start_thread
        self._thread: threading.Thread | None = None
        self.sweeper: Callable[[str], None] | None = None  # set by `app.wire_sweep`
        self.on_rows: Callable[[str, dict[str, SacctRow | None]], None] | None = None
        self._ended: dict[str, None] = {}  # runs whose sweep is due, in the order they ended
        self._sweeping: set[str] = set()  # the runs handed to the sweep, not swept yet
        self._closed = False

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs: Any) -> "Accounting":
        """With `[slurm] accounting` on and a `sacct` path recorded by `spectio init` (which
        records one on a SLURM server only); otherwise off ("SLURM accounting unavailable").
        Whether a run's jobs are asked is the run's own executor (`on_slurm`, FU-P3-86a)."""
        slurm = settings.slurm
        return cls(settings.runs_root, slurm.sacct, enabled=slurm.accounting, **kwargs)

    def _call(self, ids: list[str]) -> sacct.Found | None:
        """The limiter's call: the pairs asked for `ids` are copied under the lock, and `sacct`
        runs outside it (CON-PRE-16)."""
        if self._path is None:  # never: `want` asks nothing when off
            return None
        with self._lock:
            called = {
                (run_id, job): self._where[run_id, job]
                for job in ids
                for run_id in self._asked.get(job, ())
            }
            self._called = called
        wanted: dict[str, dict[str, float]] = {}
        for (_, job), (dirs, since, _) in called.items():
            mine = wanted.setdefault(job, {})
            for where in dirs:  # two runs of one directory: the earlier launch (FU-P3-53)
                mine[where] = min(since, mine.get(where, since))
        if not wanted:
            return {}
        # -E: the latest end of the runs asked; now when one of them is live
        ends = [until for _, _, until in called.values() if until is not None]
        until = max(ends) if len(ends) == len(called) else None
        dropped: Counter[str] = Counter()
        found = sacct.sacct_jobs(
            wanted, self._timeout, sacct=self._path, dropped=dropped, until=until
        )
        by_run = Counter[str]()
        for run_id, job in called:
            by_run[run_id] += dropped[job]
        for run_id, count in by_run.items():
            if count and run_id not in self._logged:  # once per run (CON-PRE-14)
                self._logged.add(run_id)
                log.info("sacct: %d lines of %s dropped for their WorkDir", count, run_id)
        return found

    # Reads, from a request (no file system, no wait).

    def rows(self, run_id: str) -> dict[str, SacctRow | None]:
        with self._lock:
            return dict(self._rows.get(run_id, {}))

    def status(self, run_id: str, job: str | None) -> Status:
        with self._lock:
            if job is not None and self._rows.get(run_id, {}).get(job) is not None:
                return "available"
            if job is not None and run_id in self._asked.get(job, ()):
                return "pending"
        return "unavailable"

    def loaded(self, run_id: str) -> bool:
        """True once the run's cache file was read: a view need not enter the file pool for it."""
        with self._lock:
            return run_id in self._loaded

    def failed(self, run_id: str, job: str) -> str | None:
        """Why `job` was given up, None when it was not: `not_found` when its calls failed
        until GIVE_UP_S after it ended or its follow-up found it in no terminal state,
        `max_query_time_range` when the site refused the window its run's launch set
        (FU-P3-106b; the call's other jobs are asked again with a narrower -S,
        SEC-P3FU106B-01). This process does not ask it again."""
        with self._lock:
            return self._failed.get(run_id, {}).get(job)

    def waiting(self, run_id: str) -> set[str] | None:
        """The run's jobs asked and not answered yet, a follow-up included, a job given up
        not; None while the run's sweep is due or running: every job waits (CR-P3FU105D-01)."""
        with self._lock:
            if run_id in self._ended or run_id in self._sweeping:
                return None
            return {job for rid, job in self._where if rid == run_id}

    def want(
        self,
        run_id: str,
        jobs: Iterable[tuple[str | None, str | None]],
        since: float,
        in_pool: InPool | None = None,
        *,
        ended: float | None = None,
    ) -> bool:
        """Ask `sacct` for the run's jobs, (job ID, the directory it was launched from), it has
        not answered yet, once the run's cache file was read. `since` is the run's launch,
        `ended` when its jobs had ended at the latest (the run's end; now when None), epoch
        seconds. A job is asked once its directory's `realpath` is known: up to
        MAX_RESOLVE directories are resolved by one job sent through `in_pool` (the file pool,
        with the view's timeout; CON-PRE-14), at most one per run in flight, each kept as it
        is resolved, so a view that times out still leaves its work and a later view asks the
        rest (CR-P3FU53-01). With no `in_pool` (tests) the job runs here. A job with no
        directory (SEC-PRE-15) or whose ID is no SLURM job ID (SEC-P3FU53-01) is never asked.
        Returns once the jobs are queued: False when nothing could be asked (off, the file not
        read) or a resolve was refused or did not end in time."""
        if not self.enabled:
            return False
        given = {
            job: os.path.normpath(where)
            for job, where in jobs
            if job and where and JOB_ID.fullmatch(job)
        }
        token = object()
        with self._lock:
            if run_id not in self._loaded:  # its file could not be read in time: ask nothing
                return False
            new = self._new(run_id, given)
            dirs = [d for d in dict.fromkeys(new.values()) if d not in self._real][:MAX_RESOLVE]
            send = bool(dirs) and run_id not in self._resolving
            if send:
                self._resolving[run_id] = token
        resolved = True
        if send:
            job = self._resolve_job(run_id, token, dirs)
            if in_pool is None:
                job()
            elif not in_pool(job):
                resolved = False
                with self._lock:  # refused, or cancelled before it ran: it never will
                    if self._resolving.get(run_id) is token:
                        del self._resolving[run_id]
        with self._lock:
            new = {j: where for j, where in self._new(run_id, new).items() if where in self._real}
            queued = self._limiter.request(new)  # the job IDs it took, as the limit allows
            ago = 0.0 if ended is None else max(0.0, time.time() - ended)
            for job_id in queued:
                where = new[job_id]
                self._asked.setdefault(job_id, set()).add(run_id)
                self._where[run_id, job_id] = frozenset({where, self._real[where]}), since, ended
                self._deadline[run_id, job_id] = self._clock() + GIVE_UP_S - ago
        if queued:
            self._ensure_thread()
            self._wake.set()
        return resolved

    def _resolve_job(self, run_id: str, token: object, dirs: list[str]) -> Callable[[], None]:
        """The `realpath` of each absolute directory, kept as it is computed; never run on the
        accounting thread, and a WorkDir from `sacct` is never resolved (SEC-PRE-13)."""

        def job() -> None:
            with self._lock:
                if self._resolving.get(run_id) is not token:  # given up before it started
                    return
                self._resolving[run_id] = _RUNNING
            try:
                for where in dirs:
                    real = os.path.realpath(where) if os.path.isabs(where) else where
                    with self._lock:
                        if len(self._real) >= MAX_REAL:
                            self._real.clear()
                        self._real[where] = os.path.normpath(real)
            finally:
                with self._lock:
                    self._resolving.pop(run_id, None)

        return job

    def _new(self, run_id: str, given: dict[str, str]) -> dict[str, str]:
        """The jobs of `given` neither answered, failed nor asked for the run; under the lock."""
        known = self._rows.get(run_id, {})
        failed = self._failed.get(run_id, {})
        return {
            job: where
            for job, where in given.items()
            if job not in known and job not in failed and run_id not in self._asked.get(job, ())
        }

    # The run's cache file (file system: in the file pool, or on the accounting thread).

    def load(self, run_id: str) -> None:
        """Read the run's `sacct.json` once; a missing or refused file reads as empty."""
        with self._lock:
            if run_id in self._loaded:
                return
        found: dict[str, SacctRow | None] = {}
        try:
            found = read_cache(self.runs_root, run_id)
        except (OSError, ValueError, RecursionError) as exc:  # a symlink, another owner, too
            # large, not JSON, nested past the parser's depth (SEC-P3T29-02)
            log.warning("%s of %s not read: %s", CACHE_FILE, run_id, exc)
        with self._lock:
            mine = self._rows.setdefault(run_id, {})
            for job, row in found.items():
                mine.setdefault(job, row)
            self._loaded.add(run_id)

    def _save(self, run_id: str, rows: dict[str, SacctRow | None]) -> None:
        body = {"v": 1, "jobs": {job: asdict(r) if r else None for job, r in rows.items()}}
        try:
            with private_dir(self.runs_root, run_id, ".spectio") as fd:  # never created here
                write_file(fd, CACHE_FILE, json.dumps(body, sort_keys=True).encode())
        except (OSError, ValueError) as exc:
            log.warning("%s of %s not written: %s", CACHE_FILE, run_id, exc)

    # The end-of-run sweep (FU-P3-105c).

    def ended(self, run_ids: Iterable[str]) -> None:
        """The runs the projector just ended (the writer's `on_ended`, after the commit): each
        one is swept on the accounting thread. Never waits, never reads a file."""
        if not self.enabled or self.sweeper is None:
            return
        with self._lock:
            if self._closed:
                return
            for run_id in run_ids:
                if len(self._ended) < sacct.MAX_PENDING:
                    self._ended[run_id] = None
        self._ensure_thread()
        self._wake.set()

    def _sweep_ended(self) -> bool:
        """Sweep the runs handed over; False when there were none."""
        sweep = self.sweeper
        if sweep is None:  # never: `ended` hands nothing over without it
            return False
        with self._lock:
            todo, self._ended = list(self._ended), {}
            self._sweeping.update(todo)
        for run_id in todo:
            if self._closed:
                break
            try:
                sweep(run_id)
            except Exception:  # the next run is swept; a view still asks this one's jobs
                log.exception("the end-of-run sweep of %s failed", run_id)
            finally:
                with self._lock:
                    self._sweeping.discard(run_id)
        return bool(todo)

    def close(self) -> None:
        """The server stops: the sweeps and calls not made yet are dropped, the thread ends."""
        with self._lock:
            self._closed = True
            self._ended.clear()
        self._wake.set()

    # The accounting thread.

    def step(self) -> bool:
        """Make the due sweeps and the next due call, and keep its answer; False when none was
        due."""
        if self._closed:
            return False
        swept = self._sweep_ended()
        done = self._limiter.run_once()
        if done is None:
            return swept
        ids, found = done
        touched: dict[str, dict[str, SacctRow | None]] = {}
        with self._lock:
            called, self._called = self._called, {}
            now = self._clock()
            low = min((since for _, since, _ in called.values()), default=0.0)  # the call's -S
            for job in ids:
                answer = found.get(job, {}) if isinstance(found, dict) else {}
                again, follow = set(), set()  # the runs that wait: asked now, or later
                for run_id in self._asked.pop(job, set()):
                    key = run_id, job
                    if key not in called:  # asked during the call: not in it, no follow-up
                        again.add(run_id)
                        continue
                    # the site's window limit: only the jobs whose launch set -S are refused
                    later = found is sacct.SITE_LIMIT and called[key][1] > low
                    if isinstance(found, sacct.Unanswered) and not later:  # fails every time
                        self._give_up(key, found.value if found is sacct.SITE_LIMIT else None)
                        continue
                    if found is None or later:  # asked again, as the limiter backs off
                        if now < self._deadline.get(key, now):
                            again.add(run_id)
                        else:
                            self._give_up(key)
                        continue
                    dirs = called[key][0]
                    matches = [answer[where] for where in dirs if where in answer]
                    row = matches[0] if len(matches) == 1 else None
                    mine = row if _answers(row, dirs) else None
                    if mine is None and key not in self._followed:
                        self._followed.add(key)  # slurmdbd may lag: once more, later
                        follow.add(run_id)
                        continue
                    if mine is None and answer:  # known, but in no terminal state
                        self._give_up(key)
                        continue
                    self._final(key)  # a terminal row, or slurmdbd answered without the job
                    self._rows.setdefault(run_id, {})[job] = mine
                    touched[run_id] = dict(self._rows[run_id])
                # with a call due now, the follow-ups ride along with it
                queued = self._limiter.request([job]) if again else []
                if follow and not again:
                    queued = self._limiter.later([job], FOLLOW_UP_S)
                for run_id in again | follow:
                    if queued:
                        self._asked.setdefault(job, set()).add(run_id)
                    else:  # the queue is full: dropped, asked by a later view
                        self._final((run_id, job))
        for run_id, rows in touched.items():
            self._save(run_id, rows)
            if self.on_rows is not None:
                self.on_rows(run_id, rows)
        return True

    def _final(self, key: tuple[str, str]) -> None:
        """Forget what the (run, job) waited with; under the lock."""
        self._where.pop(key, None)
        self._deadline.pop(key, None)
        self._followed.discard(key)

    def _give_up(self, key: tuple[str, str], reason: str | None = None) -> None:
        self._final(key)
        self._failed.setdefault(key[0], {})[key[1]] = reason or "not_found"

    def _ensure_thread(self) -> None:
        with self._lock:
            if not self._start_thread or self._thread is not None:
                return
            self._thread = threading.Thread(target=self._run, name="spectio-sacct", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while not self._closed:
            wait = 0.0 if self._ended else self._limiter.wait_s()
            if wait is None or wait > 0:
                self._wake.wait(wait)
                self._wake.clear()
                continue
            try:
                self.step()
            except Exception:  # never ends the thread: the next call is tried
                log.exception("sacct step failed")
                time.sleep(1)


def _answers(row: SacctRow | None, dirs: frozenset[str]) -> bool:
    """The row is the job's end: a TERMINAL state, launched from an expected directory (a
    second guard: `parse_sacct` kept only such lines)."""
    if row is None or row.state not in TERMINAL or row.work_dir is None:
        return False
    return os.path.normpath(row.work_dir) in dirs


def _resolver(ctx: "Context") -> InPool:
    """A job in the file pool with the view's timeout: True when it ended in time."""

    def in_pool(job: Callable[[], None]) -> bool:
        try:
            ctx.files.run(job, ctx.timeout_s)
            return True
        except Stalled:
            return False

    return in_pool


def _launched(created_at: Any, started_at: Any) -> float:
    """The run's launch, epoch seconds: the earlier of its row's creation and the engine's
    start (a run started from a terminal is created after its first jobs)."""
    return float(min(t for t in (created_at, started_at) if t is not None).timestamp())


def read_cache(runs_root: Path, run_id: str) -> dict[str, SacctRow | None]:
    """The run's `sacct.json`, read strictly (no link followed, a regular file of the user
    that others cannot write, at most MAX_CACHE_BYTES; FU-P3-105a reads it too); empty when it
    or its directory is missing. Raises OSError or ValueError when it is refused."""
    try:
        with private_dir(runs_root, run_id, ".spectio") as fd:
            data = read_small(fd, CACHE_FILE, MAX_CACHE_BYTES)
    except FileNotFoundError:
        return {}
    return _parse_cache(data) if data is not None else {}


def _parse_cache(data: bytes) -> dict[str, SacctRow | None]:
    body = json.loads(data)
    jobs = body.get("jobs") if isinstance(body, dict) and body.get("v") == 1 else None
    found: dict[str, SacctRow | None] = {}
    for job, row in (jobs or {}).items() if isinstance(jobs, dict) else ():
        if not JOB_ID.fullmatch(job):
            continue
        if row is None:
            found[job] = None
            continue
        try:
            found[job] = SacctRow(**_CachedRow.model_validate(row).model_dump())
        except ValidationError:
            continue
    return found


# --- The run's failures (GET /runs/{id}) -----------------------------------------------------


class Measures:
    """What each ended attempt's benchmark file gave (None when it could not be read), by
    attempt ID, for the whole server: a job's benchmark does not change once it has ended, so
    it is read once, not on every view (CR-P3T34-01; dev-env §15.3 req. 15). Emptied when
    MAX_MEASURES attempts are kept. At most one sweep per run reads them at a time
    (SEC-P3T34-01)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._found: dict[str, dict[str, Any] | None] = {}
        self._sweeping: set[str] = set()

    def claim(self, run_id: str) -> bool:
        """True when no other sweep of the run is reading; then `release` it when done."""
        with self._lock:
            if run_id in self._sweeping:
                return False
            self._sweeping.add(run_id)
            return True

    def release(self, run_id: str) -> None:
        with self._lock:
            self._sweeping.discard(run_id)

    def get(self, ids: Iterable[str]) -> dict[str, dict[str, Any] | None]:
        with self._lock:
            return {a: self._found[a] for a in ids if a in self._found}

    def put(self, found: dict[str, dict[str, Any] | None]) -> None:
        with self._lock:
            if len(self._found) + len(found) > MAX_MEASURES:
                self._found.clear()
            self._found.update(found)


@dataclass(frozen=True)
class Context:
    """What a view reads with: the runs root, the file pool and its timeout, the accounting,
    the benchmarks already read."""

    runs_root: Path
    files: FilePool
    accounting: Accounting
    timeout_s: float
    settings: Settings  # for the run's command (P1 Task 30)
    measures: Measures


def on_slurm(environment: dict[str, Any] | None, settings: Settings) -> bool:
    """The run's executor is SLURM: from its `runs.environment`, never an `environments` row
    (SEC-PRE-FU86-R1-01); `not_recorded` is the server's built-in (`read_as`, api §5.4).
    `not_readable` and a run started from a terminal are not SLURM."""
    return executor_of(read_as(environment, settings)) == "slurm"


def sweep_run(conn: Connection, run_id: str, ctx: Context) -> None:
    """The end-of-run sweep (FU-P3-105c, schedulers §3.7), on the accounting thread once the
    projector ended the run: every ended attempt of a SLURM run with a job ID is queued once,
    as a view of the ended run would (`task_resources`), with the run's launch and end for
    `-S` and `-E`. Nothing for a live, deleted or terminal-started run, a run off SLURM, or
    with accounting off. The run's file is read and its directories resolved in the file pool,
    with its timeout; a pool that does not answer leaves the rest to a later view."""
    run = conn.execute(
        select(
            runs.c.id,
            runs.c.lineage_id,
            runs.c.state,
            runs.c.origin,
            runs.c.environment,
            runs.c.created_at,
            runs.c.started_at,
            runs.c.ended_at,
            workflows.c.engine,
        )
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .where(runs.c.id == run_id, runs.c.deleted_at.is_(None))
    ).one_or_none()
    if run is None or run.state not in RUN_ENDED or run.origin == "cli-observed":
        return
    if not ctx.accounting.enabled or not on_slurm(run.environment, ctx.settings):
        return
    try:
        ctx.files.run(partial(ctx.accounting.load, run_id), ctx.timeout_s)
    except Stalled:
        return
    ended = (
        select(attempts.c.native_id, attempts.c.work_dir)
        .join(tasks, tasks.c.id == attempts.c.task_id)
        .where(
            tasks.c.run_id == run_id,
            attempts.c.state.in_(ENDED),
            attempts.c.native_id.is_not(None),
        )
    )
    launch = str(run_paths(ctx.runs_root, dir_run_id(run)).launch_dir)
    smk = run.engine == "snakemake"
    jobs = [(r.native_id, launch if smk else r.work_dir) for r in conn.execute(ended)]
    since, until = _launched(run.created_at, run.started_at), _ended(run.ended_at)
    for _ in range(len(jobs) // MAX_RESOLVE + 1):  # MAX_RESOLVE directories per pass
        if not ctx.accounting.want(run_id, jobs, since, _resolver(ctx), ended=until):
            return


def _last_attempt() -> Any:
    """The ID of the task's last attempt (api §7.2: its state is the task's)."""
    other = attempts.alias("newest")
    newest = select(other.c.id).where(other.c.task_id == tasks.c.id).correlate(tasks)
    newest = newest.order_by(other.c.launch_n.desc(), other.c.n.desc()).limit(1)
    return newest.scalar_subquery()


def dir_run_id(row: Any) -> str:
    """The run whose launch and work directories its engine used: its lineage root for a
    Resume (P1 Task 30), else the run itself. Known limit of a Snakemake Resume
    (CR-P3T30-03): a job the child reruns writes its log at the same relative path, so the
    parent's failure tails then show the child's log."""
    return str(row.lineage_id or row.id)


def build_failures(
    conn: Connection,
    run_id: str,
    dirs: str,
    engine: str,
    failure: dict[str, Any] | None,
    ctx: Context,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    """Each job whose last attempt failed, the first `limit` in the order their failed attempt
    started, and how many there are. The file reads (log tails, the run's sacct cache) run in
    the file pool; a pool that does not answer in time leaves the tails null."""
    failed = tasks.c.run_id == run_id, tasks.c.state == "failed"
    total = conn.execute(select(func.count()).where(*failed)).scalar_one()
    rows = conn.execute(
        select(
            tasks.c.id.label("task_id"),
            tasks.c.process_or_rule,
            tasks.c.tag,
            attempts.c.n,
            attempts.c.state,
            attempts.c.exit,
            attempts.c.native_id,
            attempts.c.work_dir,
            attempts.c.logs,
            attempts.c.resources,
            attempts.c.scheduler,
        )
        .select_from(tasks)
        .join(attempts, attempts.c.id == _last_attempt())
        .where(*failed)
        .order_by(attempts.c.created_at, attempts.c.id)
        .limit(limit)
    ).all()
    files = [_files(ctx.runs_root, dirs, engine, r) for r in rows]

    def read() -> list[str | None]:
        ctx.accounting.load(run_id)
        return [_log_tail(f) for f in files]

    try:
        tails = ctx.files.run(read, ctx.timeout_s)
    except Stalled:
        tails = [None] * len(rows)
    run = conn.execute(
        select(runs.c.created_at, runs.c.started_at, runs.c.ended_at, runs.c.environment).where(
            runs.c.id == run_id
        )
    ).one()
    # Snakemake's state comes from its own message (§13.7); a run not on SLURM never asks
    if engine == "nextflow" and on_slurm(run.environment, ctx.settings):
        jobs = ((r.native_id, r.work_dir) for r in rows)
        since = _launched(run.created_at, run.started_at)
        ctx.accounting.want(run_id, jobs, since, _resolver(ctx), ended=_ended(run.ended_at))
    cached = ctx.accounting.rows(run_id)
    culprit = (failure or {}).get("task_id"), (failure or {}).get("attempt_n")
    message = (failure or {}).get("message") or None
    found = []
    for r, f, tail in zip(rows, files, tails, strict=True):
        found.append(
            {
                "task_id": r.task_id,
                "attempt_n": r.n,
                "process": r.process_or_rule,
                "tag": r.tag,
                "exit_code": r.exit,
                "message": message if culprit == (r.task_id, r.n) else None,
                "native_id": r.native_id,
                "scheduler": _scheduler(engine, r, cached.get(r.native_id or ""), ctx, run_id),
                "log_tail": tail,
                "work_dir": attempt_dir(f),
            }
        )
    return found, total


def _files(runs_root: Path, dir_run: str, engine: str, r: Any) -> AttemptFiles:
    logs = tuple(
        (x["path"], x["kind"]) for x in r.logs or [] if isinstance(x, dict) and "path" in x
    )
    return AttemptFiles(dir_run, engine, r.state, r.work_dir, r.native_id, logs, runs_root)


def _log_tail(attempt: AttemptFiles) -> str | None:
    """The last LOG_TAIL_LINES lines of the job's log: Nextflow's `.command.log`, else its
    `.command.err`; Snakemake's SLURM job log, else the rule's first log."""
    if attempt.engine == "snakemake":
        by_kind = {kind: path for path, kind in reversed(attempt.logs)}
        names = [by_kind[k] for k in ("slurm_log", "rule_log") if k in by_kind]
    else:
        names = [".command.log", ".command.err"]
    for name in names:
        try:
            text = read_task_file(attempt, name).text
        except (NotFound, NotAllowed, Binary, OSError):
            continue
        return "\n".join(text.splitlines()[-LOG_TAIL_LINES:])
    return None


def _scheduler(
    engine: str, r: Any, row: SacctRow | None, ctx: Context, run_id: str
) -> dict[str, Any]:
    resources = r.resources or {}
    own = r.scheduler or {}
    found: dict[str, Any] = {
        "state": None,
        "reason": None,
        "state_source": None,
        "req_mem_bytes": resources.get("memory_bytes"),
        "max_rss_bytes": None,
        "time_limit_s": _int(resources.get("time_s")),
        "elapsed_s": None,
        "usage_source": None,
        "accounting": ctx.accounting.status(run_id, r.native_id),
    }
    if engine == "snakemake" and own.get("state"):
        found.update(state=own["state"], reason=own.get("reason"), state_source="engine_message")
    elif row is not None:
        found.update(state=row.state, reason=row.reason, state_source="sacct")
    if row is not None:
        found.update(
            req_mem_bytes=row.req_mem_bytes,
            max_rss_bytes=row.max_rss_bytes,
            time_limit_s=row.time_limit_s,
            elapsed_s=row.elapsed_s,
            usage_source="sacct",
        )
    elif resources.get("peak_rss_bytes") is not None or resources.get("realtime_s") is not None:
        found.update(
            max_rss_bytes=resources.get("peak_rss_bytes"),
            elapsed_s=_int(resources.get("realtime_s")),
            usage_source="trace",
        )
    return found


def _int(value: Any) -> int | None:
    return None if value is None else int(value)


def _ended(ended_at: Any) -> float | None:
    return None if ended_at is None else float(ended_at.timestamp())


# --- Resources per task (GET /runs/{id}/tasks) -----------------------------------------------


REQUESTED = ("cpus", "memory_bytes", "time_s")
MEASURED = ("realtime_s", "cpu_percent", "peak_rss_bytes")


def task_resources(
    conn: Connection,
    run_id: str,
    dirs: str,
    engine: str,
    task_ids: list[str] | None,
    ctx: Context,
    opened: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Per task (the run's `task_ids`, or all of them), from its last attempt: its number,
    `resources` (api §5 note of 2026-10-28), `slurm` and `efficiency` (note of 2026-11-07),
    with the task's `process`, `state` and `requested` values for the aggregate. `resources`
    are the trace's on Nextflow; on Snakemake the requested values of `job_info`, measured by
    the job's benchmark file when it has one, else by `sacct`. On a SLURM run, ended jobs with
    a job ID are asked of `sacct` here (answered on a later read; schedulers §3.6), which a
    local run never is: all of them once the run has ended (its one sweep), and while it is
    live only the task `opened`, whose SLURM panel is open (CON-SLURM-POLL-01)."""
    run = conn.execute(
        select(
            runs.c.state,
            runs.c.environment,
            runs.c.engine_settings,
            runs.c.created_at,
            runs.c.started_at,
            runs.c.ended_at,
        ).where(runs.c.id == run_id)
    ).one()
    slurm_run, smk = on_slurm(run.environment, ctx.settings), engine == "snakemake"
    query = (
        select(
            tasks.c.id,
            tasks.c.process_or_rule,
            tasks.c.state.label("task_state"),
            attempts.c.id.label("attempt_id"),
            attempts.c.n,
            attempts.c.state,
            attempts.c.native_id,
            attempts.c.work_dir,
            attempts.c.resources,
            attempts.c.slurm,
        )
        .select_from(tasks)
        .outerjoin(attempts, attempts.c.id == _last_attempt())
        .where(tasks.c.run_id == run_id)
    )
    if task_ids is not None:
        query = query.where(tasks.c.id.in_(task_ids))
    rows = conn.execute(query).all()
    benches: dict[str, str] = {}  # attempt ID → its benchmark path
    if smk:
        benches = {
            r.attempt_id: (r.resources or {})["benchmark"]
            for r in rows
            if r.state in ENDED and isinstance((r.resources or {}).get("benchmark"), str)
        }
    known = ctx.measures.get(benches)
    unread = [(a, path) for a, path in benches.items() if a not in known]
    unread = unread[:MAX_BENCHMARKS_PER_VIEW]

    def read() -> dict[str, dict[str, Any] | None]:
        """In the pool thread: each batch is kept as it is read, so a read that outlasts the
        view's timeout still fills the cache (CR-P3T34-03); a run another sweep is reading
        is left to it (SEC-P3T34-01), and what a sweep just released has read is not read
        again (CR-P3T34-04, SEC-P3T34-02)."""
        if not ctx.measures.claim(run_id):
            return {}
        try:
            if slurm_run:
                ctx.accounting.load(run_id)
            seen = ctx.measures.get(a for a, _ in unread)
            todo = [(a, p) for a, p in unread if a not in seen]
            fresh: dict[str, dict[str, Any] | None] = dict(seen)
            for i in range(0, len(todo), BENCHMARK_CHUNK):
                batch = {a: _benchmark(ctx, dirs, p) for a, p in todo[i : i + BENCHMARK_CHUNK]}
                ctx.measures.put(batch)
                fresh.update(batch)
            return fresh
        finally:
            ctx.measures.release(run_id)

    try:
        if (slurm_run and not ctx.accounting.loaded(run_id)) or unread:
            known.update(ctx.files.run(read, ctx.timeout_s))
    except Stalled:
        pass
    measured = {a: m for a, m in known.items() if m is not None}
    cached: dict[str, SacctRow | None] = {}
    if slurm_run:
        launch = str(run_paths(ctx.runs_root, dirs).launch_dir)
        swept = run.state in RUN_ENDED
        ended = (r for r in rows if r.state in ENDED and (swept or r.id == opened))
        jobs = ((r.native_id, launch if smk else r.work_dir) for r in ended)
        since = _launched(run.created_at, run.started_at)
        ctx.accounting.want(run_id, jobs, since, _resolver(ctx), ended=_ended(run.ended_at))
        cached = ctx.accounting.rows(run_id)
    off = "local" if not slurm_run else None if ctx.accounting.enabled else "accounting_off"
    if (run.environment or {}).get("state") == "not_readable":
        off = "not_found"  # its executor is unknown: no `sacct` line binds its jobs, nor "local"
    cluster_options = True if (run.engine_settings or {}).get("cluster_options") is True else None
    found: dict[str, dict[str, Any]] = {}
    for r in rows:
        own = r.resources or {}
        values: dict[str, Any] = {k: own.get(k) for k in REQUESTED}
        values.update(dict.fromkeys(MEASURED), source=None)
        row = cached.get(r.native_id) if r.native_id and r.state in ENDED else None
        by_engine: tuple[str, dict[str, Any]] | None = None
        if engine == "nextflow" and any(own.get(k) is not None for k in MEASURED):
            values.update({k: own.get(k) for k in MEASURED}, source="trace")
            by_engine = "trace", own
        elif r.attempt_id in measured:
            bench = measured[r.attempt_id]
            values.update({k: bench[k] for k in MEASURED}, source="benchmark")
            by_engine = "benchmark", {**own, **bench}
        elif row is not None:
            elapsed = None if row.elapsed_s is None else float(row.elapsed_s)
            values.update(realtime_s=elapsed, peak_rss_bytes=row.max_rss_bytes, source="sacct")
        reason = off
        if reason is None and r.native_id is None:
            reason = "no_job_id"
        elif reason is None and (given_up := ctx.accounting.failed(run_id, r.native_id)):
            reason = given_up  # its call failed, or the site refused its window (FU-P3-106b)
        elif reason is None and (r.native_id in cached or (not smk and r.work_dir is None)):
            # sacct knew no such job after its tries, or no directory binds the job to a
            # line, so it is never asked (SEC-PRE-15)
            reason = "not_found"
        slurm = None
        if slurm_run and r.slurm is not None:
            slurm = {
                "request": {**dict.fromkeys(REQUEST), **(r.slurm.get("request") or {})},
                "allocated": efficiency.allocated(row) if row is not None else None,
                "custom_options": r.slurm.get("custom_options") if smk else cluster_options,
            }
        time_s = values["time_s"]
        found[r.id] = {
            "process": r.process_or_rule,
            "state": r.task_state,
            "attempt_n": r.n,
            "resources": values,
            "slurm": slurm,
            "efficiency": efficiency.job(r.state, by_engine, row, reason),
            "requested": {
                "cpus": values["cpus"],
                "mem_bytes": values["memory_bytes"],
                "time_limit_s": None if time_s is None else int(time_s),
            },
        }
    return found


def read_benchmark(runs_root: Path, dir_run: str, path: str) -> dict[str, str] | None:
    """The last row of a Snakemake benchmark file, column → text; None when it cannot be read.
    Read in the launch directory with no link followed, as a job file is: a regular file of the
    user (a FIFO is refused at its open), at most MAX_BENCHMARK_BYTES (a larger one is not read,
    FU-P3-105b)."""
    try:
        with (
            run_root(runs_root, dir_run, "launch") as root,
            open_confined(root, safe_rel(path)) as f,
        ):
            if os.fstat(f.fileno()).st_size > MAX_BENCHMARK_BYTES:
                return None
            text = read_at(f, 0, MAX_BENCHMARK_BYTES).decode("utf-8", "replace")
    except (NotFound, NotAllowed, OSError):
        return None
    lines = [line.split("\t") for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return dict(zip(lines[0], lines[-1], strict=False))


def _benchmark(ctx: Context, dir_run: str, path: str) -> dict[str, Any] | None:
    """`s` (wall seconds), `max_rss` (MiB), `mean_load` (CPU %) and `cpu_time` (seconds) of
    the benchmark's last row (`snakemake/benchmark.py`, [to be validated]); None when it
    cannot be read."""
    row = read_benchmark(ctx.runs_root, dir_run, path)
    if row is None:
        return None
    found = {
        "realtime_s": _number(row.get("s")),
        "cpu_percent": _number(row.get("mean_load")),
        "peak_rss_bytes": _whole(row.get("max_rss"), MIB),
    }
    if not any(v is not None for v in found.values()):
        return None
    return {**found, "cpu_time_s": _number(row.get("cpu_time"))}  # for the efficiency only
