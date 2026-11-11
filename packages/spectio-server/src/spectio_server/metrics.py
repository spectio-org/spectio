"""Performance measures per attempt (FU-P3-105a; api §5.5 owns the row, schedulers §3.7 the
values and their sources, §3.6 the efficiency formulas).

One `attempt_metrics` row per ended attempt, with the run's identity copied in:

- Nextflow: written by the projector at `onTaskComplete`, in the event's transaction, from the
  trace record (`trace_metrics`); a rebuild replays the same events, so it writes the same rows;
- the run's `sacct.json` (the cache `failure.Accounting` writes): added once per run after boot
  by `fill_sacct`, a background thread, for the runs already ended. Each file is read by the
  strict reader (`failure.read_cache`: no link followed, a regular file of the user, capped,
  parsed strictly) in the file pool with its timeout, never on the writer; the writer then
  updates the rows and sets the run's marker `runs.metrics_sacct_at`. No `sacct` call;
- Snakemake (FU-P3-105b): written by the projector at the job's end, in the event's transaction,
  with the requested values of `job_info`; the job's `benchmark:` file is then asked of
  `Benchmarks`, which reads it in the file pool on a thread of its own, never on the writer, and
  hands the values to the writer: a blocked file delays no event;
- the end-of-run sweep (FU-P3-105c, `failure.sweep_run`): each answer, as it comes, by
  `apply_sweep` on the writer, whatever the marker says (a run filled before its file existed
  gets its values too).

The rows of old runs come from the migration (0015), from the database only.
"""

import logging
import queue
import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, insert, select, update

from spectio.runner.sacct import SacctRow
from spectio_sdk.events import NextflowTrace
from spectio_server import efficiency
from spectio_server.failure import MIB, _number, _whole, read_benchmark, read_cache
from spectio_server.files.pool import READ_TIMEOUT_S, FilePool, Stalled
from spectio_server.projector.runs import TERMINAL
from spectio_server.store.schema import (
    attempt_metrics,
    attempts,
    runs,
    tasks,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer, note_change

log = logging.getLogger(__name__)

MAX_RATIO = 1_000_000  # a larger ratio is null (schedulers §3.7, Ingest checks)
PARTITION = re.compile(r"[A-Za-z0-9_.-]{1,64}")
WINDOW = timedelta(minutes=5)  # a wait whose ends fall outside the run's window is null
FILL_CHUNK = 100  # runs selected per round of the fill
BENCH_BACKLOG = 10_000  # benchmark reads waiting; one more is dropped, with a warning


def capped(found: float | None) -> float | None:
    return None if found is None or found > MAX_RATIO else found


def ratio(part: float | None, whole: float | None) -> float | None:
    return capped(efficiency.ratio(part, whole))


def partition(value: object) -> str | None:
    return value if isinstance(value, str) and PARTITION.fullmatch(value) else None


def _moment(value: object) -> datetime | None:
    """A trace time (epoch milliseconds) as UTC, or None."""
    ms = _number(value)
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _seconds(value: object) -> float | None:
    ms = _number(value)
    return None if ms is None else ms / 1000


def trace_metrics(
    trace: NextflowTrace | None, launched: datetime | None, seen: datetime
) -> dict[str, Any]:
    """The §3.7 values of a trace record, each through `_number` (a NaN, a negative, an
    infinite or a non-numeric value is null). `launched` is the run's launch (None for a run
    started from a terminal, which holds no launch window) and `seen` the event's time: a
    wait whose submit or start falls outside them by more than WINDOW, or that starts before
    its submit, is null."""
    t = trace or NextflowTrace()
    cpus, memory, time_s = _whole(t.cpus), _whole(t.memory), _seconds(t.time)
    cpu, peak, real = _number(t.pct_cpu), _whole(t.peak_rss), _seconds(t.realtime)
    submitted, started = _moment(t.submit), _moment(t.start)
    wait = None
    if submitted and started and submitted <= started <= seen + WINDOW:
        if launched is None or launched - WINDOW <= submitted:
            wait = (started - submitted).total_seconds()
    measured = {
        "cpu_percent": cpu,
        "cpu_eff": ratio(cpu, None if cpus is None else 100 * cpus),
        "peak_rss_bytes": peak,
        "peak_vmem_bytes": _whole(t.peak_vmem),
        "mem_eff": ratio(peak, memory),
        "realtime_s": real,
        "time_eff": ratio(real, time_s),
        "rchar_bytes": _whole(t.rchar),
        "wchar_bytes": _whole(t.wchar),
        "read_bytes": _whole(t.read_bytes),
        "write_bytes": _whole(t.write_bytes),
    }
    return {
        "submitted_at": submitted,
        "started_at": started,
        "ended_at": _moment(t.complete) or seen,
        "partition": partition(t.queue),
        "source": "trace" if any(v is not None for v in measured.values()) else None,
        "cpus": cpus,
        "mem_bytes": memory,
        "time_limit_s": time_s,
        "wait_s": wait,
        **measured,
    }


def write(
    conn: Connection,
    attempt_id: str,
    task_id: str,
    attempt: int,
    state: str,
    run_state: str,
    engine: str,
    values: dict[str, Any],
) -> None:
    """Insert or replace the attempt's row: `values`, and the run's identity read here."""
    who = conn.execute(
        select(
            tasks.c.run_id,
            tasks.c.tag,
            tasks.c.process_or_rule,
            runs.c.project_id,
            runs.c.environment_id,
            runs.c.created_by,
            workflows.c.name,
            workflow_versions.c.version,
        )
        .select_from(tasks)
        .join(runs, runs.c.id == tasks.c.run_id)
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .where(tasks.c.id == task_id)
    ).one()
    row = {
        "run_id": who.run_id,
        "task_id": task_id,
        "attempt": attempt,
        "tag": who.tag,
        "process_or_rule": who.process_or_rule,
        "engine": engine,
        "pipeline": who.name,
        "pipeline_version": who.version,
        "environment_id": who.environment_id,
        "project_id": who.project_id,
        "owner_id": who.created_by,
        "run_state": run_state,
        "state": state,
        **values,
    }
    key = attempt_metrics.c.attempt_id == attempt_id
    if not conn.execute(update(attempt_metrics).where(key).values(**row)).rowcount:
        conn.execute(insert(attempt_metrics).values(attempt_id=attempt_id, **row))


def _first(*values: Any) -> Any:
    return next((v for v in values if v is not None), None)


def sacct_values(row: SacctRow, stored: Any) -> dict[str, Any]:
    """What a `sacct` row gives (schedulers §3.7, SLURM column) over the `stored` row: §3.6's
    source order puts its measures first, the engine's requested values first. A value the
    `sacct` row lacks keeps the stored one, and the ratios are taken against the requested
    values the row keeps, as the trace's are."""
    elapsed = None if row.elapsed_s is None else float(row.elapsed_s)
    used = None if row.total_cpu_s is None else row.total_cpu_s * 100
    cpu = efficiency.ratio(used, elapsed)  # % of one CPU
    measured = (cpu, row.max_rss_bytes, elapsed)
    cpus = _first(stored.cpus, row.ncpus)
    memory = _first(stored.mem_bytes, row.req_mem_bytes)
    limit = _first(stored.time_limit_s, row.time_limit_s)
    cpu = _first(cpu, stored.cpu_percent)
    peak = _first(row.max_rss_bytes, stored.peak_rss_bytes)
    real = _first(elapsed, stored.realtime_s)
    return {
        "source": "sacct" if any(v is not None for v in measured) else stored.source,
        "partition": _first(partition(row.partition), stored.partition),
        "cpus": cpus,
        "mem_bytes": memory,
        "time_limit_s": limit,
        "cpu_percent": cpu,
        "cpu_eff": ratio(cpu, None if cpus is None else 100 * cpus),
        "peak_rss_bytes": peak,
        "mem_eff": ratio(peak, memory),
        "realtime_s": real,
        "time_eff": ratio(real, limit),
        "wait_s": _first(row.wait_s, stored.wait_s),
    }


def smk_values(resources: dict[str, Any] | None, ended: datetime) -> dict[str, Any]:
    """The values of a Snakemake job at its end: the requested ones `smk_resources` kept on
    the attempt; its measures come from its benchmark file (`benchmark_values`) or `sacct`."""
    own = resources or {}
    return {
        "ended_at": ended,
        "cpus": own.get("cpus"),
        "mem_bytes": own.get("memory_bytes"),
        "time_limit_s": own.get("time_s"),
    }


SACCT_MEASURES = ("cpu_percent", "peak_rss_bytes", "realtime_s")  # what `sacct` measures too


def benchmark_values(row: dict[str, str], stored: Any) -> dict[str, Any]:
    """What a benchmark row gives (schedulers §3.7, Snakemake local column), each through
    `_number` (`NA`, `-` or empty is null): `s` in seconds, CPU % as `cpu_time` / `s` x 100,
    `max_rss`, `max_vms`, `io_in` and `io_out` in MiB (Snakemake 9.27.1 divides each by
    1024 x 1024, `benchmark.py:446-453`, §3.7 note 2026-11-11; whether `io_in` and `io_out`
    count disk bytes only is [to be validated]). Over a row `sacct` measured, its measures stay
    first (§3.6's source order); the ratios are taken against the row's requested values."""
    real = _number(row.get("s"))
    cpu_time = _number(row.get("cpu_time"))
    measured: dict[str, Any] = {
        "cpu_percent": ratio(None if cpu_time is None else cpu_time * 100, real),  # capped
        "peak_rss_bytes": _whole(row.get("max_rss"), MIB),
        "peak_vmem_bytes": _whole(row.get("max_vms"), MIB),
        "realtime_s": real,
        "read_bytes": _whole(row.get("io_in"), MIB),
        "write_bytes": _whole(row.get("io_out"), MIB),
    }
    source = "benchmark" if any(v is not None for v in measured.values()) else stored.source
    if stored.source == "sacct":
        source = "sacct"
        for name in SACCT_MEASURES:
            measured[name] = _first(getattr(stored, name), measured[name])
    cpu, peak, real = (measured[k] for k in SACCT_MEASURES)
    return {
        **measured,
        "source": source,
        "cpu_eff": ratio(cpu, None if stored.cpus is None else 100 * stored.cpus),
        "mem_eff": ratio(peak, stored.mem_bytes),
        "time_eff": ratio(real, stored.time_limit_s),
    }


def _apply_benchmark(conn: Connection, attempt_id: str, row: dict[str, str]) -> bool:
    key = attempt_metrics.c.attempt_id == attempt_id
    stored = conn.execute(select(attempt_metrics).where(key)).one_or_none()
    if stored is None:  # the run was deleted meanwhile
        return False
    conn.execute(update(attempt_metrics).where(key).values(**benchmark_values(row, stored)))
    note_change(conn, stored.run_id)  # the run's performance answer is read again (api §5.5)
    return True


class Benchmarks:
    """The Snakemake benchmark files, each read once at its job's end. `want` only queues
    (it runs on the writer, in the event's transaction); a thread of its own reads each file in
    the file pool with its timeout (`read_benchmark`: no link followed, a regular file, capped),
    then submits the values to the writer, after the event's transaction. A read that does not
    answer, or a file refused, leaves the row's measures null. After a read that did not answer,
    the next waits until it ends: one stuck read at most keeps a slot of the routes' file pool
    (dev-env §15.3 req. 13, CR-P3FU105B-01)."""

    def __init__(
        self,
        writer: Writer,
        runs_root: Path,
        files: FilePool,
        *,
        timeout_s: float = READ_TIMEOUT_S,
        backlog: int = BENCH_BACKLOG,
    ) -> None:
        self.writer, self.runs_root, self.files = writer, runs_root, files
        self.timeout_s = timeout_s
        self._todo: queue.Queue[tuple[str, str, str]] = queue.Queue(backlog)
        self._idle = threading.Event()  # set when no read of ours is in the pool
        self._idle.set()

    def want(self, attempt_id: str, dir_run: str, path: str) -> None:
        try:
            self._todo.put_nowait((attempt_id, dir_run, path))
        except queue.Full:
            log.warning("benchmark of %s not read: too many waiting", attempt_id)

    def read(self, attempt_id: str, dir_run: str, path: str) -> bool:
        """Read one file and store its values; False when nothing was stored."""
        job: Callable[[], dict[str, str] | None] = partial(
            read_benchmark, self.runs_root, dir_run, path
        )
        ended = threading.Event()
        try:
            found = self.files.run(job, self.timeout_s, on_done=ended.set)
        except Stalled as exc:
            self._idle = ended  # still in the pool: `run` waits for its end
            log.warning("benchmark of %s not read: %s", attempt_id, exc)
            return False
        if found is None:
            return False
        stored = partial(_apply_benchmark, attempt_id=attempt_id, row=found)
        return self.writer.submit(stored).result()

    def start(self, stop: threading.Event) -> threading.Thread:
        def run() -> None:
            while not stop.is_set():
                if not self._idle.wait(0.2):
                    continue
                try:
                    wanted = self._todo.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    self.read(*wanted)
                except RuntimeError:  # the writer closed
                    return
                except Exception:
                    log.exception("benchmark of %s not read", wanted[0])

        thread = threading.Thread(target=run, name="spectio-metrics-benchmarks", daemon=True)
        thread.start()
        return thread


# --- The background fill of sacct.json --------------------------------------------------------


def _unfilled(conn: Connection, after: str) -> list[str]:
    """The next ended, not deleted runs whose file was not read, in ID order."""
    return list(
        conn.execute(
            select(runs.c.id)
            .where(
                runs.c.id > after,
                runs.c.state.in_(TERMINAL),
                runs.c.deleted_at.is_(None),
                runs.c.metrics_sacct_at.is_(None),
            )
            .order_by(runs.c.id)
            .limit(FILL_CHUNK)
        ).scalars()
    )


def _apply(conn: Connection, run_id: str, found: dict[str, SacctRow | None]) -> None:
    """Update the run's rows from its jobs' `sacct` rows, bound by job ID, then mark it; once."""
    _update(conn, run_id, found, runs.c.metrics_sacct_at.is_(None))


def apply_sweep(conn: Connection, run_id: str, found: dict[str, SacctRow | None]) -> None:
    """The sweep's answers (FU-P3-105c): as `_apply`, marked or not."""
    _update(conn, run_id, found)


def _update(conn: Connection, run_id: str, found: dict[str, SacctRow | None], *when: Any) -> None:
    still = conn.execute(
        select(runs.c.id).where(runs.c.id == run_id, runs.c.deleted_at.is_(None), *when)
    ).one_or_none()
    if still is None:  # deleted meanwhile, or filled
        return
    jobs = conn.execute(
        select(attempts.c.native_id, attempt_metrics)
        .join(attempt_metrics, attempt_metrics.c.attempt_id == attempts.c.id)
        .where(attempt_metrics.c.run_id == run_id, attempts.c.native_id.is_not(None))
    ).all()
    for stored in jobs:
        if (row := found.get(stored.native_id)) is not None:
            key = attempt_metrics.c.attempt_id == stored.attempt_id
            conn.execute(update(attempt_metrics).where(key).values(**sacct_values(row, stored)))
    marked = update(runs).where(runs.c.id == run_id).values(metrics_sacct_at=datetime.now(UTC))
    conn.execute(marked)


def fill_sacct(
    writer: Writer,
    runs_root: Path,
    files: FilePool,
    *,
    timeout_s: float = READ_TIMEOUT_S,
    stop: threading.Event | None = None,
) -> int:
    """Add the `sacct.json` values of every ended run not filled yet, run by run; the number of
    runs marked. A missing or refused file (a symlink, a FIFO, another owner, too large, not
    JSON) marks its run with nothing added; a read that does not answer within `timeout_s`
    stops the fill, this run and the rest left for the next boot: its stuck read keeps a slot
    of the routes' file pool (dev-env §15.3 req. 13), so no further read is submitted."""
    done, after = 0, ""
    while not (stop is not None and stop.is_set()):
        todo = writer.submit(partial(_unfilled, after=after)).result()
        if not todo:
            break
        for run_id in todo:
            if stop is not None and stop.is_set():
                break
            after = run_id
            read: Callable[[], dict[str, SacctRow | None]] = partial(read_cache, runs_root, run_id)
            try:
                found = files.run(read, timeout_s)
            except Stalled as exc:
                log.warning("sacct.json of %s not read, the fill stops: %s", run_id, exc)
                return done
            except (OSError, ValueError, RecursionError) as exc:
                log.warning("sacct.json of %s not read: %s", run_id, exc)
                found = {}
            writer.submit(partial(_apply, run_id=run_id, found=found)).result()
            done += 1
    return done


def start_fill(
    writer: Writer, runs_root: Path, files: FilePool, stop: threading.Event
) -> threading.Thread:
    """`fill_sacct` on a thread of its own, so that no file delays the boot."""

    def run() -> None:
        try:
            filled = fill_sacct(writer, runs_root, files, stop=stop)
            log.info("performance: sacct.json of %d runs added", filled)
        except RuntimeError:  # the writer closed: the next boot goes on
            pass
        except Exception:
            log.exception("performance: the sacct.json fill failed")

    thread = threading.Thread(target=run, name="spectio-metrics-fill", daemon=True)
    thread.start()
    return thread
