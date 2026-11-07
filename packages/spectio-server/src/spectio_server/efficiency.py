"""CPU and memory efficiency, per job and per process or rule (P1 Task 34; schedulers §3.6 owns
the formulas and the timing; the fields are api §5 note of 2026-11-07).

Pure functions: `failure.task_resources` gathers each job's values (its attempt, its engine's
measure, what `sacct` said) and calls these. Ratios are 0.63 for 63 %, rounded to 4 places and
never clamped; a ratio with a missing or zero part is None.
"""

from collections import Counter
from typing import Any

from spectio.runner.sacct import SacctRow

OPEN = ("pending", "submitted", "running")
REUSED = ("cached", "stored")  # a job that did not run: no value (schedulers §3.6)
DONE = ("succeeded", *REUSED)


def ratio(part: float | None, whole: float | None) -> float | None:
    if part is None or not whole:
        return None
    return round(part / whole, 4)


def _measure(
    cpu: float | None, mem: float | None, elapsed: float | None, peak: int | None
) -> dict[str, Any]:
    return {"cpu": cpu, "mem": mem, "elapsed_s": elapsed, "peak_rss_bytes": peak}


def engine_measure(source: str, values: dict[str, Any]) -> dict[str, Any]:
    """The engine's own measure of a job from its `resources`: the trace's `%cpu` / (100 *
    `cpus`), or the benchmark's `cpu_time` / (`s` * `threads`); `peak_rss` / the request."""
    cpus, wall = values.get("cpus"), values.get("realtime_s")
    if source == "trace":
        cpu = ratio(values.get("cpu_percent"), None if cpus is None else 100 * cpus)
    else:
        cpu = ratio(values.get("cpu_time_s"), None if cpus is None or wall is None else wall * cpus)
    peak = values.get("peak_rss_bytes")
    return _measure(cpu, ratio(peak, values.get("memory_bytes")), wall, peak)


def sacct_measure(row: SacctRow) -> dict[str, Any]:
    """`TotalCPU` over the steps / (`Elapsed` * `NCPUS`), `MaxRSS` / `ReqMem`, as `seff` does."""
    elapsed = None if row.elapsed_s is None else float(row.elapsed_s)
    spent = None if elapsed is None or row.ncpus is None else elapsed * row.ncpus
    return _measure(
        ratio(row.total_cpu_s, spent),
        ratio(row.max_rss_bytes, row.req_mem_bytes),
        elapsed,
        row.max_rss_bytes,
    )


def allocated(row: SacctRow) -> dict[str, Any]:
    """What SLURM gave the job, from its allocation row."""
    return {
        "partition": row.partition,
        "account": row.account,
        "qos": row.qos,
        "ncpus": row.ncpus,
        "req_mem_bytes": row.req_mem_bytes,
        "time_limit_s": row.time_limit_s,
        "alloc_tres": row.alloc_tres,
        "nnodes": row.nnodes,
    }


def job(
    attempt_state: str | None,
    engine: tuple[str, dict[str, Any]] | None,
    row: SacctRow | None,
    reason: str | None,
) -> dict[str, Any]:
    """One job's `efficiency`: `running` while it runs; once ended, `sacct`'s values
    (`available`), else the engine's measure (`engine`: its source and `resources`) with
    `unavailable` and the `reason` sacct will not answer, or `pending_accounting`."""
    found = {**_measure(None, None, None, None), "source": None, "reason": None}
    if attempt_state is None or attempt_state in OPEN:
        return {**found, "state": "running"}
    if attempt_state in REUSED:
        return {**found, "state": "unavailable", "reason": "cached"}
    if row is not None:
        return {**found, **sacct_measure(row), "state": "available", "source": "sacct"}
    if engine is not None:
        found.update(engine_measure(*engine), source=engine[0])
    if reason is not None:
        return {**found, "state": "unavailable", "reason": reason}
    return {**found, "state": "pending_accounting"}


def _common(values: list[Any]) -> tuple[Any, bool]:
    """The most common known value (the first seen on a tie), and whether they differ."""
    counts = Counter(v for v in values if v is not None)
    return (counts.most_common(1)[0][0] if counts else None), len(counts) > 1


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def aggregate(jobs: list[dict[str, Any]], planned: int | None) -> dict[str, Any]:
    """A process's or rule's `efficiency` over its tasks' last attempts: each job is
    {state (the task's), requested {cpus, mem_bytes, time_limit_s}, efficiency}. `planned` is
    Snakemake's planned job count, when larger than the tasks known."""
    measured = [j["efficiency"] for j in jobs if j["state"] not in REUSED]
    measured = [e for e in measured if e["cpu"] is not None or e["mem"] is not None]
    cpu = [e["cpu"] for e in measured if e["cpu"] is not None]
    mem = [e["mem"] for e in measured if e["mem"] is not None]
    requested: dict[str, Any] = {}
    varies = False
    for key in ("cpus", "mem_bytes", "time_limit_s"):
        requested[key], differ = _common([j["requested"].get(key) for j in jobs])
        varies = varies or differ
    peaks = [e["peak_rss_bytes"] for e in measured if e["peak_rss_bytes"] is not None]
    walls = [e["elapsed_s"] for e in measured if e["elapsed_s"] is not None]
    return {
        "jobs": {
            "done": sum(j["state"] in DONE for j in jobs),
            "total": max(len(jobs), planned or 0),
        },
        "measured": len(measured),
        "cpu_mean": _mean(cpu),
        "cpu_max": max(cpu, default=None),
        "mem_mean": _mean(mem),
        "mem_max": max(mem, default=None),
        "requested": {**requested, "varies": varies},
        "used": {
            "peak_rss_bytes_max": max(peaks, default=None),
            "elapsed_s_max": max(walls, default=None),
        },
    }
