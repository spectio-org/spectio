"""Performance measures per attempt (FU-P3-105a; api §5.5 owns the row, schedulers §3.7 the
values and their sources, §3.6 the efficiency formulas).

One `attempt_metrics` row per ended attempt, with the run's identity copied in:

- Nextflow: written by the projector at `onTaskComplete`, in the event's transaction, from the
  trace record (`trace_metrics`); a rebuild replays the same events, so it writes the same rows;
- the run's `sacct.json` (the cache `failure.Accounting` writes): added once per run after boot
  by `fill_sacct`, a background thread, for the runs already ended. Each file is read by the
  strict reader (`failure.read_cache`: no link followed, a regular file of the user, capped,
  parsed strictly) in the file pool with its timeout, never on the writer; the writer then
  updates the rows and sets the run's marker `runs.metrics_sacct_at`. No `sacct` call.

The rows of old runs come from the migration (0015), from the database only.
"""

import logging
import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, func, insert, select, update

from spectio.runner.sacct import SacctRow
from spectio_sdk.events import NextflowTrace
from spectio_server import efficiency
from spectio_server.failure import _number, _whole, read_cache
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
from spectio_server.store.writer import Writer

log = logging.getLogger(__name__)

MAX_RATIO = 1_000_000  # a larger ratio is null (schedulers §3.7, Ingest checks)
PARTITION = re.compile(r"[A-Za-z0-9_.-]{1,64}")
WINDOW = timedelta(minutes=5)  # a wait whose ends fall outside the run's window is null
FILL_CHUNK = 100  # runs selected per round of the fill


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
    trace: NextflowTrace | None, launched: datetime, seen: datetime
) -> dict[str, Any]:
    """The §3.7 values of a trace record, each through `_number` (a NaN, a negative, an
    infinite or a non-numeric value is null). `launched` is the run's launch and `seen` the
    event's time: a wait whose submit or start falls outside them by more than WINDOW, or
    that starts before its submit, is null."""
    t = trace or NextflowTrace()
    cpus, memory, time_s = _whole(t.cpus), _whole(t.memory), _seconds(t.time)
    cpu, peak, real = _number(t.pct_cpu), _whole(t.peak_rss), _seconds(t.realtime)
    submitted, started = _moment(t.submit), _moment(t.start)
    wait = None
    if submitted and started and launched - WINDOW <= submitted <= started <= seen + WINDOW:
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


def sacct_values(row: SacctRow) -> dict[str, Any]:
    """What a `sacct` row gives (schedulers §3.7, SLURM column), §3.6's source order putting
    it first; the requested values only where the engine gave none."""
    elapsed = None if row.elapsed_s is None else float(row.elapsed_s)
    measure = efficiency.sacct_measure(row)
    used = None if row.total_cpu_s is None else row.total_cpu_s * 100
    c = attempt_metrics.c
    return {
        "source": "sacct",
        "partition": func.coalesce(partition(row.partition), c.partition),
        "cpus": func.coalesce(c.cpus, row.ncpus),
        "mem_bytes": func.coalesce(c.mem_bytes, row.req_mem_bytes),
        "time_limit_s": func.coalesce(c.time_limit_s, row.time_limit_s),
        "cpu_percent": efficiency.ratio(used, elapsed),  # % of one CPU
        "cpu_eff": capped(measure["cpu"]),
        "peak_rss_bytes": row.max_rss_bytes,
        "mem_eff": capped(measure["mem"]),
        "realtime_s": elapsed,
        "time_eff": ratio(elapsed, row.time_limit_s),
    }


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
    """Update the run's rows from its jobs' `sacct` rows, bound by job ID, then mark it."""
    still = conn.execute(
        select(runs.c.id).where(
            runs.c.id == run_id, runs.c.deleted_at.is_(None), runs.c.metrics_sacct_at.is_(None)
        )
    ).one_or_none()
    if still is None:  # deleted meanwhile, or filled
        return
    jobs = conn.execute(
        select(attempts.c.id, attempts.c.native_id)
        .join(attempt_metrics, attempt_metrics.c.attempt_id == attempts.c.id)
        .where(attempt_metrics.c.run_id == run_id, attempts.c.native_id.is_not(None))
    ).all()
    for attempt_id, job in jobs:
        if (row := found.get(job)) is not None:
            key = attempt_metrics.c.attempt_id == attempt_id
            conn.execute(update(attempt_metrics).where(key).values(**sacct_values(row)))
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
    leaves the run for the next boot."""
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
                log.warning("sacct.json of %s not read: %s", run_id, exc)
                continue
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
