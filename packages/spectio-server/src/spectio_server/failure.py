"""The failure summary and the resources per job (P1 Task 29; api §5 note of 2026-10-28, Run and
Resources; architecture §13.7, Failure reason and Resources per task; dev-env §15.3 req. 15).

Where a failure's facts come from:

- the engine's events, through the projector: the exit code, the job ID, the requested and the
  measured resources (the Nextflow trace; Snakemake's `job_info`), and on Snakemake the SLURM
  state and reason that the SLURM executor plugin wrote in its error text, parsed here
  (`parse_smk_slurm_message`) and stored as `attempts.scheduler`, the text never;
- `sacct`, for a Nextflow failure and for a Snakemake job's measures when it has no
  `benchmark:` file: asked only when someone opens the failure or the job, through the
  server's one `Accounting` (its limiter and its own thread), and cached in memory and in
  `<run dir>/.spectio/sacct.json`; nothing here waits for it;
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
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Connection, func, select

from spectio.config import Settings
from spectio.runner import sacct
from spectio.runner.rundir import private_dir, read_small, run_paths, write_file
from spectio.runner.sacct import JOB_ID, SacctLimiter, SacctRow
from spectio_sdk.events import NextflowTrace
from spectio_server.files.confine import NotAllowed, NotFound, open_confined, read_at, safe_rel
from spectio_server.files.pool import FilePool, Stalled
from spectio_server.files.taskfiles import AttemptFiles, Binary, read_task_file, run_root
from spectio_server.store.schema import attempts, tasks

log = logging.getLogger(__name__)

CACHE_FILE = "sacct.json"  # in <run dir>/.spectio/
MAX_CACHE_BYTES = 8388608
LOG_TAIL_LINES = 20
MAX_BENCHMARK_BYTES = 65536
ENDED = ("succeeded", "failed", "aborted")
MIB = 1048576
MAX_TRIES = 3  # sacct calls for a job it does not know yet, or not as ended; then null
# The states a job ends in (`sacct(1)`, JOB STATE CODES); a row in any other is not kept.
TERMINAL = frozenset(
    {"COMPLETED", "FAILED", "OUT_OF_MEMORY", "TIMEOUT", "CANCELLED", "NODE_FAIL", "PREEMPTED"}
    | {"BOOT_FAIL", "DEADLINE"}
)
_MAX = 2**63 - 1

Status = Literal["available", "pending", "unavailable"]


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


class Accounting:
    """`sacct` for the whole server (dev-env §15.3 req. 15): one `SacctLimiter`, run by a thread
    of its own, so a call that hangs holds neither the writer nor a request until its timeout
    kills it. Per run, what `sacct` said of each job (a row, or None when it knew no such job),
    in memory and in `<run dir>/.spectio/sacct.json`, 0600, written by a rename in the run's
    checked directory and read back with no link followed. A run's file is read (`load`, in
    the file pool) before any of its jobs is asked (`want`), so a cached job is never asked
    again, after a rebuild too. A job whose call failed is not asked again by this process.
    Only a row in a TERMINAL state is kept: a job `sacct` does not know yet, or not as ended
    (slurmdbd records a job after it ends, with a lag, [to be validated] on `slurm-mini`, P1
    Task 22), is asked again on the next view, up to MAX_TRIES calls, then kept as None. So is
    a row whose WorkDir is not the directory the job was launched from (the Nextflow attempt's
    work directory, Snakemake's launch directory): another job with that number, such as a
    local PID read as a SLURM ID (SEC-P3T29-01; WorkDir [to be validated] on `slurm-mini`)."""

    def __init__(
        self,
        runs_root: Path,
        sacct_path: Path | None,
        *,
        enabled: bool = True,
        start_thread: bool = True,
        interval_s: float = sacct.INTERVAL_S,
        timeout_s: float = sacct.TIMEOUT_S,
    ) -> None:
        self.runs_root = runs_root
        self.enabled = enabled and sacct_path is not None
        self._path = sacct_path
        self._timeout = timeout_s
        self._limiter = SacctLimiter(self._call, interval_s=interval_s)
        self._lock = threading.Lock()
        self._rows: dict[str, dict[str, SacctRow | None]] = {}
        self._loaded: set[str] = set()
        self._failed: dict[str, set[str]] = {}
        self._asked: dict[str, set[str]] = {}  # job ID → the runs that wait for it
        self._where: dict[tuple[str, str], str | None] = {}  # (run, job) asked → its directory
        self._tries: dict[tuple[str, str], int] = {}  # (run, job) → calls with no answer yet
        self._wake = threading.Event()
        self._start_thread = start_thread
        self._thread: threading.Thread | None = None

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs: Any) -> "Accounting":
        """On a SLURM environment with `[slurm] accounting` on and a `sacct` path recorded by
        `spectio init`; otherwise off ("SLURM accounting unavailable")."""
        slurm = settings.slurm
        on = settings.executor == "slurm" and slurm.accounting
        return cls(settings.runs_root, slurm.sacct, enabled=on, **kwargs)

    def _call(self, ids: list[str]) -> dict[str, SacctRow] | None:
        if self._path is None:  # never: `want` asks nothing when off
            return None
        return sacct.sacct_jobs(ids, self._timeout, sacct=self._path)

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

    def want(self, run_id: str, jobs: Iterable[tuple[str | None, str | None]]) -> None:
        """Ask `sacct` for the run's jobs, (job ID, the directory it was launched from), it has
        not answered yet, once the run's cache file was read; returns at once."""
        if not self.enabled:
            return
        with self._lock:
            if run_id not in self._loaded:  # its file could not be read in time: ask nothing
                return
            known = self._rows.get(run_id, {})
            failed = self._failed.get(run_id, set())
            where = dict(jobs)
            new = [
                job
                for job in where
                if job is not None
                and job not in known
                and job not in failed
                and run_id not in self._asked.get(job, ())
            ]
            queued = self._limiter.request(new)  # the job IDs it took, as the limit allows
            for job in queued:
                self._asked.setdefault(job, set()).add(run_id)
                self._where[run_id, job] = where[job]
        if queued:
            self._ensure_thread()
            self._wake.set()

    # The run's cache file (file system: in the file pool, or on the accounting thread).

    def load(self, run_id: str) -> None:
        """Read the run's `sacct.json` once; a missing or refused file reads as empty."""
        with self._lock:
            if run_id in self._loaded:
                return
        found: dict[str, SacctRow | None] = {}
        try:
            with private_dir(self.runs_root, run_id, ".spectio") as fd:
                data = read_small(fd, CACHE_FILE, MAX_CACHE_BYTES)
            found = _parse_cache(data) if data is not None else {}
        except FileNotFoundError:
            pass
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

    # The accounting thread.

    def step(self) -> bool:
        """Make the next due call and keep its answer; False when none was due."""
        done = self._limiter.run_once()
        if done is None:
            return False
        ids, found = done
        touched: dict[str, dict[str, SacctRow | None]] = {}
        with self._lock:
            for job in ids:
                row = found.get(job) if found is not None else None
                for run_id in self._asked.pop(job, set()):
                    key = run_id, job
                    where = self._where.pop(key, None)
                    if found is None:
                        self._failed.setdefault(run_id, set()).add(job)
                        continue
                    mine = row if _answers(row, where) else None
                    if mine is None:
                        tries = self._tries.get(key, 0) + 1
                        if tries < MAX_TRIES:
                            self._tries[key] = tries
                            continue  # not answered: the next view asks it again
                    self._tries.pop(key, None)  # final: a terminal row, or the cap reached
                    self._rows.setdefault(run_id, {})[job] = mine
                    touched[run_id] = dict(self._rows[run_id])
        for run_id, rows in touched.items():
            self._save(run_id, rows)
        return True

    def _ensure_thread(self) -> None:
        with self._lock:
            if not self._start_thread or self._thread is not None:
                return
            self._thread = threading.Thread(target=self._run, name="spectio-sacct", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while True:
            wait = self._limiter.wait_s()
            if wait is None or wait > 0:
                self._wake.wait(wait)
                self._wake.clear()
                continue
            try:
                self.step()
            except Exception:  # never ends the thread: the next call is tried
                log.exception("sacct step failed")
                time.sleep(1)


def _answers(row: SacctRow | None, where: str | None) -> bool:
    """The row is the job's end: a TERMINAL state, launched from the expected directory."""
    if row is None or row.state not in TERMINAL or row.work_dir is None or where is None:
        return False
    return os.path.normpath(row.work_dir) == os.path.normpath(where)


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


@dataclass(frozen=True)
class Context:
    """What a view reads with: the runs root, the file pool and its timeout, the accounting."""

    runs_root: Path
    files: FilePool
    accounting: Accounting
    timeout_s: float


def _last_attempt() -> Any:
    """The ID of the task's last attempt (api §7.2: its state is the task's)."""
    other = attempts.alias("newest")
    newest = select(other.c.id).where(other.c.task_id == tasks.c.id).correlate(tasks)
    newest = newest.order_by(other.c.launch_n.desc(), other.c.n.desc()).limit(1)
    return newest.scalar_subquery()


def build_failures(
    conn: Connection,
    run_id: str,
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
    files = [_files(ctx.runs_root, run_id, engine, r) for r in rows]

    def read() -> list[str | None]:
        ctx.accounting.load(run_id)
        return [_log_tail(f) for f in files]

    try:
        tails = ctx.files.run(read, ctx.timeout_s)
    except Stalled:
        tails = [None] * len(rows)
    if engine == "nextflow":  # Snakemake's state comes from its own message (§13.7)
        ctx.accounting.want(run_id, ((r.native_id, r.work_dir) for r in rows))
    cached = ctx.accounting.rows(run_id)
    culprit = (failure or {}).get("task_id"), (failure or {}).get("attempt_n")
    message = (failure or {}).get("message") or None
    found = []
    for r, tail in zip(rows, tails, strict=True):
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
            }
        )
    return found, total


def _files(runs_root: Path, run_id: str, engine: str, r: Any) -> AttemptFiles:
    logs = tuple(
        (x["path"], x["kind"]) for x in r.logs or [] if isinstance(x, dict) and "path" in x
    )
    return AttemptFiles(run_id, engine, r.state, r.work_dir, r.native_id, logs, runs_root)


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


# --- Resources per task (GET /runs/{id}/tasks) -----------------------------------------------


REQUESTED = ("cpus", "memory_bytes", "time_s")
MEASURED = ("realtime_s", "cpu_percent", "peak_rss_bytes")


def task_resources(
    conn: Connection, run_id: str, engine: str, task_ids: list[str], ctx: Context
) -> dict[str, tuple[int | None, dict[str, Any]]]:
    """Per task, its last attempt's number and `resources` (api §5 note, Resources): the
    trace's on Nextflow; on Snakemake the requested values of `job_info`, measured by the
    job's benchmark file when it has one, else by `sacct` once the job ended (asked here,
    answered on a later read)."""
    rows = conn.execute(
        select(
            tasks.c.id,
            attempts.c.n,
            attempts.c.state,
            attempts.c.native_id,
            attempts.c.resources,
        )
        .select_from(tasks)
        .outerjoin(attempts, attempts.c.id == _last_attempt())
        .where(tasks.c.run_id == run_id, tasks.c.id.in_(task_ids))
    ).all()
    benches: dict[str, str] = {}
    if engine == "snakemake":
        benches = {
            r.id: (r.resources or {})["benchmark"]
            for r in rows
            if r.state in ENDED and isinstance((r.resources or {}).get("benchmark"), str)
        }

    def read() -> dict[str, dict[str, Any]]:
        if engine == "snakemake":
            ctx.accounting.load(run_id)
        return {task: m for task, path in benches.items() if (m := _benchmark(ctx, run_id, path))}

    try:
        measured = ctx.files.run(read, ctx.timeout_s) if engine == "snakemake" else {}
    except Stalled:
        measured = {}
    if engine == "snakemake":
        launch = str(run_paths(ctx.runs_root, run_id).launch_dir)
        ended = ((r.native_id, launch) for r in rows if r.state in ENDED and r.id not in measured)
        ctx.accounting.want(run_id, ended)
    cached = ctx.accounting.rows(run_id) if engine == "snakemake" else {}
    found: dict[str, tuple[int | None, dict[str, Any]]] = {}
    for r in rows:
        own = r.resources or {}
        values: dict[str, Any] = {k: own.get(k) for k in REQUESTED}
        values.update(dict.fromkeys(MEASURED), source=None)
        if engine == "nextflow" and any(own.get(k) is not None for k in MEASURED):
            values.update({k: own.get(k) for k in MEASURED}, source="trace")
        elif r.id in measured:
            values.update(measured[r.id], source="benchmark")
        elif (row := cached.get(r.native_id or "")) is not None and r.state in ENDED:
            elapsed = None if row.elapsed_s is None else float(row.elapsed_s)
            values.update(realtime_s=elapsed, peak_rss_bytes=row.max_rss_bytes, source="sacct")
        found[r.id] = (r.n, values)
    return found


def _benchmark(ctx: Context, run_id: str, path: str) -> dict[str, Any] | None:
    """The last row of a Snakemake benchmark file, `s` (wall seconds), `max_rss` (MiB) and
    `mean_load` (CPU %) (`snakemake/benchmark.py`, [to be validated]); None when it cannot be
    read. Read in the launch directory with no link followed, as a job file is."""
    try:
        with (
            run_root(ctx.runs_root, run_id, "launch") as root,
            open_confined(root, safe_rel(path)) as f,
        ):
            text = read_at(f, 0, MAX_BENCHMARK_BYTES).decode("utf-8", "replace")
    except (NotFound, NotAllowed, OSError):
        return None
    lines = [line.split("\t") for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    row = dict(zip(lines[0], lines[-1], strict=False))
    found = {
        "realtime_s": _number(row.get("s")),
        "cpu_percent": _number(row.get("mean_load")),
        "peak_rss_bytes": _whole(row.get("max_rss"), MIB),
    }
    return found if any(v is not None for v in found.values()) else None
