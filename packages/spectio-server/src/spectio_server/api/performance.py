"""`GET /runs/{id}/performance` (FU-P3-105d; api §5.5 owns the route, schedulers §3.7 what each
column means, §3.6 the efficiency formulas and the aggregate).

It reads Spectio's database only (the run's `attempt_metrics` rows), never `sacct`, the
runner or the engine. Who may read is the other run routes' rule: the session (and Host and
Origin) checks of the middleware, then the run by its ID, `404` when unknown or deleted; 0.0.2
has one user, so no project scoping. Statistics are computed on read over every counted
attempt (each task's last by default, `attempts=all` on request), never over the capped points.
The answer of an ended run with nothing pending accounting is kept in a bounded `Cache`.
Load (api §5.5): the run's row count is checked first, the reads run under a time budget;
past either the answer is `422 range-too-wide`.
"""

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Hashable, Iterable, Iterator
from contextlib import contextmanager
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy import Connection, Row, func, select
from sqlalchemy.exc import OperationalError

from spectio_server import efficiency
from spectio_server.api import models
from spectio_server.api.problems import Invalid, Problem
from spectio_server.api.runs_read import _rulegraphs, process_order, read, run_row
from spectio_server.failure import _last_attempt, on_slurm
from spectio_server.projector.runs import TERMINAL
from spectio_server.store import schema
from spectio_server.store.schema import attempt_metrics, runs, tasks
from spectio_server.store.writer import Changes

router = APIRouter()

# The fixed map from wire names to columns (api §5.5, Input checks): the measured values only.
METRICS = {
    name: attempt_metrics.c[name]
    for name in (
        "cpu_percent",
        "cpu_eff",
        "peak_rss_bytes",
        "peak_vmem_bytes",
        "mem_eff",
        "realtime_s",
        "time_eff",
        "wait_s",
        "rchar_bytes",
        "wchar_bytes",
        "read_bytes",
        "write_bytes",
    )
}
DEFAULT_METRIC = "cpu_eff"  # the Performance tab opens on CPU (ui-spec §4.12)
MAX_METRICS = 4
MAX_FILTER, MAX_VALUE = 20, 256  # a repeatable filter: values, characters each
POINTS_PER_PROCESS, POINTS_PER_ANSWER = 2_000, 20_000
MAX_PROCESSES = 200
WASTE_BELOW, WASTE_JOBS = 0.25, 3  # schedulers §3.6, Waste
CACHE_ENTRIES, CACHE_POINTS, CACHE_RUNS = 32, 200_000, 4_096
MAX_ROWS = 200_000  # a run's attempt_metrics rows read into memory at most (api §5.5, Load)
BUDGET_S, PROGRESS_OPS = 5.0, 10_000  # the reads' time budget, checked every PROGRESS_OPS ops


def too_wide(detail: str, **extra: Any) -> Problem:
    return Problem(422, "range-too-wide", "Range too wide", detail, **extra)


@contextmanager
def budget(conn: Connection) -> Iterator[None]:
    """SQLite stops a statement still running BUDGET_S after this began (api §5.5, Load)."""
    raw: Any = conn.connection.driver_connection  # sqlite3.Connection
    end = time.monotonic() + BUDGET_S
    raw.set_progress_handler(lambda: time.monotonic() > end, PROGRESS_OPS)
    try:
        yield
    except OperationalError as exc:
        if time.monotonic() > end:  # interrupted by the handler
            raise too_wide(f"the run's performance was not read within {BUDGET_S:g} s") from exc
        raise
    finally:
        raw.set_progress_handler(None, 0)  # the connection goes back to the pool without it


def quantile(values: list[float], p: float) -> float:
    """Linear interpolation between the closest ranks of sorted `values` (numpy.percentile's
    default method)."""
    at = (len(values) - 1) * p
    low = math.floor(at)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (at - low)


def stats(rows: list[Row[Any]], metric: str) -> dict[str, Any] | None:
    """`metric` over `rows` (in task order) that have it; None when none has."""
    found = [(getattr(r, metric), r) for r in rows if getattr(r, metric) is not None]
    if not found:
        return None
    low = min(found, key=lambda v: v[0])  # the first of equal values
    high = max(found, key=lambda v: v[0])
    values = sorted(v for v, _ in found)
    return {
        "n": len(values),
        "min": low[0],
        "q1": round(quantile(values, 0.25), 4),
        "median": round(quantile(values, 0.5), 4),
        "q3": round(quantile(values, 0.75), 4),
        "max": high[0],
        "mean": round(sum(values) / len(values), 4),
        "min_task": {"task_id": low[1].task_id, "tag": low[1].tag},
        "max_task": {"task_id": high[1].task_id, "tag": high[1].tag},
    }


def stride(sizes: list[int]) -> int:
    """The smallest step that keeps every process at most POINTS_PER_PROCESS points and the
    answer at most POINTS_PER_ANSWER, each process taking its attempts 0, step, 2 step…"""
    step = max(
        1,
        math.ceil(max(sizes, default=0) / POINTS_PER_PROCESS),
        math.ceil(sum(sizes) / POINTS_PER_ANSWER),
    )
    while (
        max((math.ceil(n / step) for n in sizes), default=0) > POINTS_PER_PROCESS
        or sum(math.ceil(n / step) for n in sizes) > POINTS_PER_ANSWER
    ):
        step += 1
    return step


def waste(rows: list[Row[Any]]) -> list[dict[str, Any]]:
    """§3.6's lines: the jobs whose memory (or CPU) efficiency is below 0.25, when 3 or more."""
    lines = []
    for metric in ("mem_eff", "cpu_eff"):
        below = sum(1 for r in rows if (v := getattr(r, metric)) is not None and v < WASTE_BELOW)
        if below >= WASTE_JOBS:
            lines.append({"metric": metric, "below": WASTE_BELOW, "jobs": below})
    return lines


class Cache:
    """The answers of ended runs, bounded by `entries` and by `points` items in all. An entry
    holds the stamp read before its rows were; it is good while the run's stamp is the same.
    `changed` (the writer's commits) gives each changed run a new stamp; `runs` stamps are
    kept, and a forgotten run's stamp is the last forgotten one's, so it never comes back."""

    def __init__(
        self, entries: int = CACHE_ENTRIES, points: int = CACHE_POINTS, runs: int = CACHE_RUNS
    ) -> None:
        self.entries, self.points, self.runs = entries, points, runs
        self._lock = threading.Lock()
        self._items: OrderedDict[Hashable, tuple[Hashable, dict[str, Any], int]] = OrderedDict()
        self._size = 0
        self._stamps: OrderedDict[str, int] = OrderedDict()
        self._commits = self._floor = 0

    def stamp(self, run_id: str) -> int:
        with self._lock:
            return self._stamps.get(run_id, self._floor)

    def changed(self, changes: Changes) -> None:
        """On the writer thread, after a commit: never blocks for long."""
        with self._lock:
            self._commits += 1
            for run_id in changes:
                self._stamps[run_id] = self._commits
                self._stamps.move_to_end(run_id)
            while len(self._stamps) > self.runs:
                self._floor = self._stamps.popitem(last=False)[1]

    def get(self, key: Hashable, stamp: Hashable) -> dict[str, Any] | None:
        with self._lock:
            found = self._items.get(key)
            if found is None or found[0] != stamp:
                return None
            self._items.move_to_end(key)
            return found[1]

    def put(self, key: Hashable, stamp: Hashable, answer: dict[str, Any], size: int) -> None:
        if size > self.points:
            return
        with self._lock:
            if (old := self._items.pop(key, None)) is not None:
                self._size -= old[2]
            self._items[key] = (stamp, answer, size)
            self._size += size
            while len(self._items) > self.entries or self._size > self.points:
                self._size -= self._items.popitem(last=False)[1][2]


def _chosen(value: str | None) -> list[str]:
    names = list(dict.fromkeys(n.strip() for n in (value or DEFAULT_METRIC).split(",")))
    for name in names:
        if name not in METRICS:
            raise Invalid("metrics", f"unknown metric {name[:64]!r}")
    if len(names) > MAX_METRICS:
        raise Invalid("metrics", f"at most {MAX_METRICS} metrics")
    return names


def _filter(values: list[str] | None) -> tuple[str, ...] | None:
    if values is None:
        return None
    if len(values) > MAX_FILTER:
        raise Invalid("process", f"at most {MAX_FILTER} values")
    if any(len(v) > MAX_VALUE for v in values):
        raise Invalid("process", f"at most {MAX_VALUE} characters a value")
    return tuple(sorted(set(values)))


def _rows(conn: Any, run_id: str, chosen: list[str], every: bool) -> list[Row[Any]]:
    """The run's counted attempts in task order, with what the answer needs."""
    am = attempt_metrics.c
    names = ("cpus", "mem_bytes", "time_limit_s", "cpu_eff", "mem_eff", "realtime_s")
    wanted = dict.fromkeys([*names, "peak_rss_bytes", *chosen])
    query = (
        select(
            am.task_id,
            am.attempt,
            am.tag,
            am.process_or_rule,
            am.partition,
            am.source,
            schema.attempts.c.native_id,
            *(am[name] for name in wanted),
        )
        .select_from(attempt_metrics)
        .join(schema.attempts, schema.attempts.c.id == am.attempt_id)
        .join(tasks, tasks.c.id == am.task_id)
        .where(am.run_id == run_id)
        .order_by(am.task_id, schema.attempts.c.launch_n, schema.attempts.c.n)
    )
    if not every:
        query = query.where(am.attempt_id == _last_attempt())
    return list(conn.execute(query).all())


def _pending(conn: Any, run_id: str, waiting: set[str] | None) -> int:
    """The rows of every attempt, not only those counted, whose job the accounting waits for:
    `waiting` from its memory, or None for every job with an ID `sacct` has not answered."""
    am = attempt_metrics.c
    query = (
        select(schema.attempts.c.native_id, am.source)
        .join(attempt_metrics, am.attempt_id == schema.attempts.c.id)
        .where(am.run_id == run_id, schema.attempts.c.native_id.is_not(None))
    )
    if waiting is None:
        return sum(1 for job, source in conn.execute(query) if source != "sacct")
    return sum(1 for job, _ in conn.execute(query) if job in waiting)


def _jobs(conn: Any, run_id: str) -> dict[str, dict[str, int]]:
    """Per process: its tasks' count and those done (§3.6's `jobs`, before the planned count)."""
    found: dict[str, dict[str, int]] = {}
    query = (
        select(tasks.c.process_or_rule, tasks.c.state, func.count())
        .where(tasks.c.run_id == run_id)
        .group_by(tasks.c.process_or_rule, tasks.c.state)
    )
    for process, state, n in conn.execute(query):
        mine = found.setdefault(process, {"done": 0, "total": 0, "cached": 0})
        mine["total"] += n
        mine["done"] += n if state in efficiency.DONE else 0
        mine["cached"] += n if state in efficiency.REUSED else 0
    return found


def _process(
    name: str,
    stage_id: str | None,
    rank: int,
    rows: list[Row[Any]],
    jobs: dict[str, int],
    planned: int | None,
    chosen: list[str],
) -> dict[str, Any]:
    by_job = [
        {
            "state": "succeeded",  # an attempt that ran: §3.6's `state` only sets cached ones apart
            "requested": {k: getattr(r, k) for k in ("cpus", "mem_bytes", "time_limit_s")},
            "efficiency": {
                "cpu": r.cpu_eff,
                "mem": r.mem_eff,
                "peak_rss_bytes": r.peak_rss_bytes,
                "elapsed_s": r.realtime_s,
            },
        }
        for r in rows
    ]
    found = efficiency.aggregate(by_job, None)
    sources: dict[str, int] = {}
    for r in rows:
        if r.source is not None:
            sources[r.source] = sources.get(r.source, 0) + 1
    return {
        "process_or_rule": name,
        "stage_id": stage_id,
        "pipeline_order": rank,
        "n": len(rows),
        "measured": found["measured"],
        "jobs": {"done": jobs["done"], "total": max(jobs["total"], planned or 0)},
        "sources": sources,
        "requested": found["requested"],
        "stats": {metric: stats(rows, metric) for metric in chosen},
        "waste": waste(rows),
    }


def _point(r: Row[Any], chosen: Iterable[str]) -> dict[str, Any]:
    keys = ("task_id", "attempt", "process_or_rule", "tag", "partition", "source")
    return {k: getattr(r, k) for k in (*keys, *chosen)}


@router.get("/runs/{run_id}/performance", response_model=models.RunPerformance)
def run_performance(
    request: Request,
    run_id: str,
    process: Annotated[list[str] | None, Query()] = None,
    metrics: Annotated[str | None, Query(max_length=1024)] = None,
    points: bool = True,
    attempts: Literal["last", "all"] = "last",
) -> dict[str, Any]:
    chosen, only = _chosen(metrics), _filter(process)
    state = request.app.state
    cache: Cache = state.performance
    stamp: Hashable = cache.stamp(run_id)  # before any row is read
    key = (run_id, only, tuple(chosen), points, attempts)
    with read(request) as conn, budget(conn):
        run = run_row(conn, run_id)
        swept = conn.execute(select(runs.c.metrics_sacct_at).where(runs.c.id == run_id)).scalar()
        stamp = (stamp, swept)
        if (found := cache.get(key, stamp)) is not None:
            return found
        count = select(func.count()).where(attempt_metrics.c.run_id == run_id)
        if (n := conn.execute(count).scalar_one()) > MAX_ROWS:
            raise too_wide(f"the run has {n} attempt rows, over {MAX_ROWS}", count=n)
        rows = _rows(conn, run_id, chosen, attempts == "all")
        order, ranks, known = process_order(conn, run, _rulegraphs(conn, run))
        jobs = _jobs(conn, run_id)
        pending = 0
        if on_slurm(run.environment, state.settings) and state.accounting.enabled:
            # an ended run the boot fill has not reached: every job it may answer still waits
            unfilled = run.state in TERMINAL and swept is None and state.fill.ahead(run_id)
            waiting = None if unfilled else state.accounting.waiting(run_id)
            pending = _pending(conn, run_id, waiting)
    of: dict[str, list[Row[Any]]] = {}
    for r in rows:
        of.setdefault(r.process_or_rule, []).append(r)
    for name in of:
        order.setdefault(name, None)  # a row whose task is known to no list: kept, last
        ranks.setdefault(name, len(ranks))
    names = sorted((n for n in order if only is None or n in only), key=lambda n: ranks[n])
    empty = {"done": 0, "total": 0, "cached": 0}
    processes = [
        _process(
            name,
            order[name],
            ranks[name],
            of.get(name, []),
            jobs.get(name, empty),
            known[name].jobs_planned if name in known else None,
            chosen,
        )
        for name in names
    ]
    answer: dict[str, Any] = {
        "run_id": run_id,
        "measured": sum(1 for r in rows if r.cpu_eff is not None or r.mem_eff is not None),
        "total": len(rows),
        "cached": sum(j["cached"] for j in jobs.values()),
        "pending_accounting": pending,
        "processes_truncated": len(processes) > MAX_PROCESSES,
        "processes": processes[:MAX_PROCESSES],
        "points": None,
    }
    if points:
        shown = [of.get(p["process_or_rule"], []) for p in answer["processes"]]
        step = stride([len(s) for s in shown])
        items = [_point(r, chosen) for s in shown for r in s[::step]]
        answer["points"] = {"items": items, "truncated": step > 1, "stride": step}
    if run.state in TERMINAL and pending == 0:
        size = len(answer["processes"]) + len((answer["points"] or {}).get("items", []))
        cache.put(key, stamp, answer, size)
    return answer
