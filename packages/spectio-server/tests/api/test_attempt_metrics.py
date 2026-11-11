"""Performance measures per attempt, the server part (FU-P3-105a; api §5.5, schedulers §3.7):
the `attempt_metrics` table, its migration and fill, the Nextflow row at `onTaskComplete`,
the run's state and delete, and the background `sacct.json` fill; the Snakemake row at the
job's end and its benchmark file, read in the file pool (FU-P3-105b)."""

import json
import os
import threading
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import insert, inspect, select, update

from spectio.config import Settings
from spectio.runner.rundir import make_run_dirs, private_dir, write_file
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server import failure, metrics
from spectio_server.failure import read_benchmark, read_cache
from spectio_server.files.pool import FilePool
from spectio_server.projector.ingest import ingest
from spectio_server.stages.freeze import StageSources
from spectio_server.store.schema import attempt_metrics, attempts, runs, tasks
from spectio_server.store.writer import Writer

from .conftest import FLAKY_RUN, add_run, replay

RUN = "run_01K8T2F1XTVRES000000000001"
OTHER = "run_01K8T2F1XTVRES000000000002"
T0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
MS0 = int(T0.timestamp() * 1000)
COLUMNS = {
    "attempt_id",
    "run_id",
    "task_id",
    "attempt",
    "tag",
    "process_or_rule",
    "engine",
    "pipeline",
    "pipeline_version",
    "environment_id",
    "project_id",
    "owner_id",
    "run_state",
    "state",
    "submitted_at",
    "started_at",
    "ended_at",
    "partition",
    "source",
    "cpus",
    "mem_bytes",
    "time_limit_s",
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
}
TRACE = {
    "status": "COMPLETED",
    "native_id": "4242",
    "cpus": "2",
    "memory": "1073741824",
    "time": "3600000",
    "%cpu": "150.0",
    "peak_rss": "536870912",
    "peak_vmem": "805306368",
    "realtime": "900000",
    "submit": str(MS0 + 60_000),
    "start": str(MS0 + 90_000),
    "complete": str(MS0 + 990_000),
    "rchar": "1000",
    "wchar": "2000",
    "read_bytes": "3000",
    "write_bytes": "4000",
    "queue": "short",
}


def event(n: int, hook: str, run_id: str = RUN, **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_m{run_id[-3:]}{n}",
            "run": run_id,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": n,
            "time": (T0 + timedelta(minutes=20)).isoformat(),
            "type": f"nextflow.{hook}",
            "data": data,
        }
    )


def complete(n: int, run_id: str = RUN, tag: str = "S1", **trace: Any) -> SpoolEvent:
    values = {k: v for k, v in {**TRACE, **trace}.items() if v is not None}
    return event(n, "onTaskComplete", run_id, process="ALIGN", tag=tag, attempt=1, trace=values)


def ingest_all(writer: Writer, launch_id: str, *evs: SpoolEvent) -> None:
    batch = SpoolBatch(list(evs), {}, Counter())
    writer.submit(partial(ingest, launch_id=launch_id, batch=batch)).result()


def rows(writer: Writer, run_id: str | None = None) -> list[Any]:
    query = select(attempt_metrics).order_by(attempt_metrics.c.tag)
    if run_id is not None:
        query = query.where(attempt_metrics.c.run_id == run_id)
    return writer.submit(lambda c: list(c.execute(query).all())).result()


def nf_run(writer: Writer, settings: Settings, run_id: str = RUN, *evs: SpoolEvent) -> str:
    launch_id = add_run(writer, settings, run_id, "perf", created_at=T0)
    ingest_all(writer, launch_id, *evs)
    return launch_id


# --- The table -------------------------------------------------------------------------------


def test_the_table_holds_exactly_the_spec_columns(writer: Writer) -> None:
    assert set(attempt_metrics.c.keys()) == COLUMNS
    found = writer.submit(lambda c: inspect(c).get_indexes("attempt_metrics")).result()
    assert {tuple(i["column_names"]) for i in found} == {
        ("project_id", "ended_at"),
        ("project_id", "process_or_rule", "ended_at"),
        ("project_id", "pipeline", "process_or_rule", "ended_at"),
        ("project_id", "partition", "ended_at"),
        ("run_id",),
    }


# --- Nextflow: the row at onTaskComplete -----------------------------------------------------


def test_nextflow_row_written_at_task_complete(writer: Writer, settings: Settings) -> None:
    nf_run(writer, settings, RUN, event(1, "onFlowBegin"), complete(2))
    [row] = rows(writer)
    run = writer.submit(lambda c: c.execute(select(runs).where(runs.c.id == RUN)).one()).result()
    attempt = writer.submit(lambda c: c.execute(select(attempts)).one()).result()
    assert row.attempt_id == attempt.id and row.task_id == attempt.task_id
    assert (row.run_id, row.attempt, row.tag, row.process_or_rule) == (RUN, 1, "S1", "ALIGN")
    assert (row.engine, row.pipeline, row.pipeline_version) == ("nextflow", "lab/nextflow", "1.2.0")
    assert (row.project_id, row.environment_id) == (run.project_id, run.environment_id)
    assert row.owner_id == run.created_by and row.owner_id is not None
    assert (row.run_state, row.state, row.source) == ("running", "succeeded", "trace")
    assert row.submitted_at == T0 + timedelta(seconds=60)
    assert row.started_at == T0 + timedelta(seconds=90)
    assert row.ended_at == T0 + timedelta(seconds=990)
    assert row.partition == "short"
    assert (row.cpus, row.mem_bytes, row.time_limit_s) == (2, 2**30, 3600.0)
    assert (row.cpu_percent, row.cpu_eff) == (150.0, 0.75)
    assert (row.peak_rss_bytes, row.peak_vmem_bytes, row.mem_eff) == (2**29, 3 * 2**28, 0.5)
    assert (row.realtime_s, row.time_eff, row.wait_s) == (900.0, 0.25, 30.0)
    assert (row.rchar_bytes, row.wchar_bytes) == (1000, 2000)
    assert (row.read_bytes, row.write_bytes) == (3000, 4000)


@pytest.mark.parametrize(
    ("trace", "nulls"),
    [
        ({"%cpu": "NaN", "peak_vmem": "-5", "rchar": "abc"}, ("cpu_percent", "cpu_eff")),
        (
            {"peak_vmem": "-5", "rchar": "1e3", "wchar": "inf"},
            ("peak_vmem_bytes", "rchar_bytes", "wchar_bytes"),
        ),
        ({"queue": "short;rm -rf"}, ("partition",)),
        ({"queue": "p" * 65}, ("partition",)),
        ({"start": str(MS0 + 30_000)}, ("wait_s",)),  # started before it was submitted
        ({"submit": str(MS0 - 3_600_000)}, ("wait_s",)),  # before the run's launch
        ({"%cpu": "300000000"}, ("cpu_eff",)),  # a ratio above 1,000,000
        ({"cpus": "0"}, ("cpu_eff",)),
    ],
)
def test_nextflow_values_checked(
    writer: Writer, settings: Settings, trace: dict[str, str], nulls: tuple[str, ...]
) -> None:
    nf_run(writer, settings, RUN, complete(1, **trace))
    [row] = rows(writer)
    for name in nulls:
        assert getattr(row, name) is None, name
    assert row.realtime_s == 900.0  # the others are kept


def test_a_bare_trace_gives_identity_only(writer: Writer, settings: Settings) -> None:
    bare: dict[str, Any] = {k: None for k in TRACE if k != "status"}
    nf_run(writer, settings, RUN, complete(1, **bare))
    [row] = rows(writer)
    assert row.source is None and row.cpus is None and row.wait_s is None
    assert row.ended_at == T0 + timedelta(minutes=20)  # the event's time


def test_a_retry_has_its_own_row(writer: Writer, settings: Settings) -> None:
    failed = {**TRACE, "status": "FAILED"}
    first = event(1, "onTaskComplete", process="ALIGN", tag="S1", attempt=1, trace=failed)
    second = event(2, "onTaskComplete", process="ALIGN", tag="S1", attempt=2, trace=TRACE)
    nf_run(writer, settings, RUN, first, second)
    found = sorted((r.attempt, r.state) for r in rows(writer))
    assert found == [(1, "failed"), (2, "succeeded")]


def test_run_state_follows_the_run(writer: Writer, settings: Settings) -> None:
    launch = nf_run(writer, settings, RUN, complete(1))
    assert rows(writer)[0].run_state == "running"
    ingest_all(writer, launch, event(2, "onFlowComplete", success=True))
    assert rows(writer)[0].run_state == "succeeded"


def test_flaky_run_has_a_row_per_attempt(
    writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    launch_id = add_run(writer, settings, FLAKY_RUN, "flaky")
    replay(writer, tmp_path, launch_id, "nextflow-26.10.4_plugin_flaky.spool.jsonl", FLAKY_RUN)
    found = rows(writer, FLAKY_RUN)
    assert Counter(r.state for r in found) == {"succeeded": 65, "failed": 2}
    assert {r.run_state for r in found} == {"succeeded"}
    assert all(r.source == "trace" and r.realtime_s is not None for r in found)
    assert all(r.peak_vmem_bytes is not None for r in found if r.state == "succeeded")


# --- Deleted with the run (FU-P3-115a's delete) ----------------------------------------------


def test_rows_deleted_with_the_run(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    for run_id in (RUN, OTHER):
        launch = nf_run(writer, settings, run_id, complete(1, run_id))
        ingest_all(writer, launch, event(2, "onFlowComplete", run_id, success=True))
    response = authed_client.post("/api/v1/runs:delete", json={"ids": [RUN]})
    assert response.status_code == 200, response.text
    assert rows(writer, RUN) == []
    assert len(rows(writer, OTHER)) == 1


# --- The migration ---------------------------------------------------------------------------


def _alembic() -> Config:
    config = Config()
    config.set_main_option("script_location", "spectio_server:migrations")
    return config


def _attempt(conn: Any, run_id: str, n: int, state: str, resources: dict[str, Any] | None) -> None:
    task_id = f"tsk_{run_id[-3:]}{n}"
    conn.execute(
        insert(tasks).values(
            id=task_id,
            created_at=T0,
            run_id=run_id,
            process_or_rule="ALIGN",
            tag=f"S{n}",
            state=state,
        )
    )
    conn.execute(
        insert(attempts).values(
            id=f"att_{run_id[-3:]}{n}",
            created_at=T0 + timedelta(minutes=n),
            task_id=task_id,
            n=1,
            launch_n=1,
            state=state,
            resources=resources,
            slurm={"request": {"partition": "short"}},
        )
    )


def test_migration_fills_old_runs_from_the_database(writer: Writer, settings: Settings) -> None:
    ended = T0 + timedelta(hours=1)
    add_run(writer, settings, RUN, "old", "succeeded", ended_at=ended)
    add_run(writer, settings, OTHER, "gone", "succeeded", deleted_at=ended)
    add_run(
        writer, settings, "run_01K8T2F1XTVRES000000000003", "smk", "running", engine="snakemake"
    )
    trace = {
        "cpus": 2,
        "memory_bytes": 2**30,
        "time_s": 3600.0,
        "realtime_s": 900.0,
        "cpu_percent": 150.0,
        "peak_rss_bytes": 2**29,
    }

    def old(conn: Any) -> None:
        _attempt(conn, RUN, 1, "succeeded", trace)
        _attempt(conn, RUN, 2, "running", trace)  # not ended: no row
        _attempt(conn, RUN, 3, "cached", None)  # did not run: no row
        _attempt(conn, OTHER, 1, "succeeded", trace)  # a deleted run: no row
        smk = {"cpus": 4, "memory_bytes": 2**31, "time_s": 600.0, "benchmark": "b.tsv"}
        _attempt(conn, "run_01K8T2F1XTVRES000000000003", 1, "failed", smk)

    writer.submit(old).result()
    engine = writer.engine
    with engine.begin() as conn:
        config = _alembic()
        config.attributes["connection"] = conn
        command.downgrade(config, "0014")
    with engine.connect() as conn:
        assert "attempt_metrics" not in inspect(conn).get_table_names()
        assert "metrics_sacct_at" not in {c["name"] for c in inspect(conn).get_columns("runs")}
    with engine.begin() as conn:
        config = _alembic()
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    found = {r.attempt_id: r for r in rows(writer)}
    assert set(found) == {f"att_{RUN[-3:]}1", "att_0031"}
    nf = found[f"att_{RUN[-3:]}1"]
    assert (nf.engine, nf.run_state, nf.state, nf.source) == (
        "nextflow",
        "succeeded",
        "succeeded",
        "trace",
    )
    assert (nf.pipeline, nf.pipeline_version, nf.partition) == ("lab/nextflow", "1.2.0", "short")
    assert (nf.cpus, nf.mem_bytes, nf.time_limit_s) == (2, 2**30, 3600.0)
    assert (nf.cpu_eff, nf.mem_eff, nf.time_eff) == (0.75, 0.5, 0.25)
    assert nf.ended_at == ended  # the run's end: the attempt's own is not stored
    assert nf.peak_vmem_bytes is None and nf.wait_s is None and nf.submitted_at is None
    smk = found["att_0031"]
    assert (smk.engine, smk.run_state, smk.state, smk.source) == (
        "snakemake",
        "running",
        "failed",
        None,
    )
    assert (smk.cpus, smk.mem_bytes, smk.time_limit_s, smk.partition) == (4, 2**31, 600.0, None)
    assert smk.ended_at == T0 + timedelta(minutes=1)  # a live run: when the attempt was seen
    assert smk.realtime_s is None and smk.cpu_eff is None


# --- The background sacct.json fill ----------------------------------------------------------

SACCT_ROW = {
    "state": "COMPLETED",
    "exit_code": 0,
    "reason": None,
    "max_rss_bytes": 2**30,
    "elapsed_s": 1000,
    "req_mem_bytes": 2**31,
    "time_limit_s": 4000,
    "work_dir": "/somewhere",
    "total_cpu_s": 1500.0,
    "ncpus": 2,
    "nnodes": 1,
    "partition": "long",
    "account": "lab",
    "qos": "normal",
    "alloc_tres": "cpu=2",
}


def ended_run(writer: Writer, settings: Settings, run_id: str = RUN) -> None:
    launch = nf_run(writer, settings, run_id, complete(1, run_id))
    ingest_all(writer, launch, event(2, "onFlowComplete", run_id, success=True))


def write_cache(settings: Settings, run_id: str, jobs: dict[str, Any]) -> Path:
    body = json.dumps({"v": 1, "jobs": jobs}).encode()
    with private_dir(settings.runs_root, run_id, ".spectio", create=True) as fd:
        write_file(fd, "sacct.json", body)
    return settings.runs_root / run_id / ".spectio" / "sacct.json"


def marker(writer: Writer, run_id: str = RUN) -> datetime | None:
    query = select(runs.c.metrics_sacct_at).where(runs.c.id == run_id)
    return writer.submit(lambda c: c.execute(query).scalar_one()).result()  # type: ignore[no-any-return]


def fill(writer: Writer, settings: Settings, timeout_s: float = 5.0) -> int:
    return metrics.fill_sacct(writer, settings.runs_root, FilePool(), timeout_s=timeout_s)


def test_fill_adds_the_sacct_values_once(writer: Writer, settings: Settings) -> None:
    ended_run(writer, settings)
    write_cache(settings, RUN, {"4242": SACCT_ROW, "9999": None})
    assert fill(writer, settings) == 1
    [row] = rows(writer)
    assert (row.source, row.partition) == ("sacct", "long")
    assert (row.realtime_s, row.peak_rss_bytes) == (1000.0, 2**30)
    assert (row.cpus, row.mem_bytes, row.time_limit_s) == (2, 2**30, 3600.0)  # the engine's
    # the ratios against the row's own requested columns
    assert (row.cpu_percent, row.cpu_eff) == (150.0, 0.75)
    assert row.mem_eff == row.peak_rss_bytes / row.mem_bytes == 1.0
    assert row.time_eff == round(row.realtime_s / row.time_limit_s, 4)
    assert row.peak_vmem_bytes == 3 * 2**28 and row.wait_s == 30.0  # sacct gives neither yet
    assert marker(writer) is not None
    write_cache(settings, RUN, {"4242": {**SACCT_ROW, "elapsed_s": 5}})
    assert fill(writer, settings) == 0  # its marker: read once
    assert rows(writer)[0].realtime_s == 1000.0


def test_fill_keeps_the_trace_values_sacct_lacks(writer: Writer, settings: Settings) -> None:
    ended_run(writer, settings)
    lacking = {**SACCT_ROW, "max_rss_bytes": None, "partition": None}  # jobacct_gather/none
    write_cache(settings, RUN, {"4242": lacking})
    assert fill(writer, settings) == 1
    [row] = rows(writer)
    assert (row.peak_rss_bytes, row.mem_eff, row.partition) == (2**29, 0.5, "short")
    assert row.realtime_s == 1000.0 and row.source == "sacct"


def test_fill_requested_values_from_sacct_where_the_engine_gave_none(
    writer: Writer, settings: Settings
) -> None:
    launch = nf_run(writer, settings, RUN, complete(1, cpus=None, memory=None, time=None))
    ingest_all(writer, launch, event(2, "onFlowComplete", success=True))
    write_cache(settings, RUN, {"4242": SACCT_ROW})
    assert fill(writer, settings) == 1
    [row] = rows(writer)
    assert (row.cpus, row.mem_bytes, row.time_limit_s) == (2, 2**31, 4000.0)
    assert (row.cpu_eff, row.mem_eff, row.time_eff) == (0.75, 0.5, 0.25)


def test_fill_skips_live_and_deleted_runs(writer: Writer, settings: Settings) -> None:
    nf_run(writer, settings, RUN, complete(1))  # still running
    ended_run(writer, settings, OTHER)
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == OTHER).values(deleted_at=T0))
    ).result()
    for run_id in (RUN, OTHER):
        write_cache(settings, run_id, {"4242": SACCT_ROW})
    assert fill(writer, settings) == 0
    assert {r.source for r in rows(writer)} == {"trace"}


def test_fill_without_a_file_marks_the_run(writer: Writer, settings: Settings) -> None:
    ended_run(writer, settings)
    assert fill(writer, settings) == 1
    assert rows(writer)[0].source == "trace" and marker(writer) is not None


def test_a_symlinked_sacct_json_fills_nothing(
    writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    ended_run(writer, settings)
    real = write_cache(settings, RUN, {"4242": SACCT_ROW})
    elsewhere = tmp_path / "elsewhere.json"
    real.rename(elsewhere)
    real.symlink_to(elsewhere)
    assert fill(writer, settings) == 1
    assert rows(writer)[0].source == "trace"


def test_a_fifo_sacct_json_fills_nothing_and_does_not_wait(
    writer: Writer, settings: Settings
) -> None:
    ended_run(writer, settings)
    path = write_cache(settings, RUN, {})
    path.unlink()
    os.mkfifo(path, 0o600)  # nothing ever writes to it
    began = time.monotonic()
    assert fill(writer, settings) == 1
    assert time.monotonic() - began < 2.0
    assert rows(writer)[0].source == "trace"


def test_a_stalled_read_is_left_for_the_next_boot(
    writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    ended_run(writer, settings)
    write_cache(settings, RUN, {"4242": SACCT_ROW})

    def slow(*args: Any) -> Any:
        time.sleep(1)
        return read_cache(*args)

    monkeypatch.setattr(metrics, "read_cache", slow)
    assert fill(writer, settings, timeout_s=0.05) == 0
    assert marker(writer) is None


def test_the_fill_stops_at_the_first_stalled_read(
    writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    for run_id in (RUN, OTHER):
        ended_run(writer, settings, run_id)
        write_cache(settings, run_id, {"4242": SACCT_ROW})
    asked: list[str] = []

    def slow(root: Path, run_id: str) -> Any:
        asked.append(run_id)
        time.sleep(1)
        return read_cache(root, run_id)

    monkeypatch.setattr(metrics, "read_cache", slow)
    assert fill(writer, settings, timeout_s=0.05) == 0
    assert asked == [RUN]  # the second read is never submitted: the pool is the routes'
    assert marker(writer, RUN) is None and marker(writer, OTHER) is None


def test_an_observed_run_holds_no_launch_window(writer: Writer, settings: Settings) -> None:
    launch = add_run(writer, settings, RUN, "cli", created_at=T0, origin="cli-observed")
    ingest_all(writer, launch, complete(1, submit=str(MS0 - 3_600_000), start=str(MS0)))
    [row] = rows(writer)
    assert row.wait_s == 3600.0  # submitted an hour before the server saw the run


# --- Snakemake: the row at the job's end, the benchmark read in the file pool (FU-P3-105b) ---

MIB = 2**20
BENCH_HEAD = "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"
# 60 s, 1024 MiB resident, 2048 MiB virtual, 10 MiB in, 20 MiB out, 90 CPU seconds
BENCH_ROW = "60.00\t0:01:00\t1024.00\t2048.00\t1\t1\t10.00\t20.00\t150.00\t90.00\n"
BENCH = "benchmarks/S1.tsv"


def smk_event(n: int, type_: str, run_id: str = RUN, **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_s{run_id[-3:]}{n}",
            "run": run_id,
            "launch": 1,
            "producer": "snakemake-logger-spectio/0.0.1",
            "seq": n,
            "time": (T0 + timedelta(minutes=20)).isoformat(),
            "type": f"snakemake.{type_}",
            "data": data,
        }
    )


def job_info(settings: Settings, n: int, jobid: int, run_id: str = RUN, **more: Any) -> SpoolEvent:
    launch_dir = make_run_dirs(settings.runs_root, run_id).launch_dir
    return smk_event(
        n,
        "job_info",
        run_id,
        jobid=jobid,
        rule_name="align",
        wildcards={"sample": f"S{jobid}"},
        threads=2,
        resources={"mem_mb": 2048, "runtime": 10},
        benchmark=str(launch_dir / f"benchmarks/S{jobid}.tsv"),
        **more,
    )


def bench_file(settings: Settings, text: str, jobid: int = 1, run_id: str = RUN) -> Path:
    path = make_run_dirs(settings.runs_root, run_id).launch_dir / f"benchmarks/S{jobid}.tsv"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)
    return path


def smk_ingest(
    writer: Writer, settings: Settings, launch_id: str, bench: Any, *evs: SpoolEvent
) -> None:
    sources = StageSources(None, settings.runs_root, benchmarks=bench)
    batch = SpoolBatch(list(evs), {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()


class Wanted:
    """A benchmark reader that only records what the projector asks."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str, str]] = []

    def want(self, attempt_id: str, dir_run: str, path: str) -> None:
        self.asked.append((attempt_id, dir_run, path))


def smk_job(writer: Writer, settings: Settings, bench: Any = None, **more: Any) -> str:
    launch = add_run(writer, settings, RUN, "smk", created_at=T0, engine="snakemake")
    smk_ingest(
        writer,
        settings,
        launch,
        bench,
        job_info(settings, 1, 1, **more),
        smk_event(2, "job_finished", job_id=1),
    )
    return launch


def benchmarks(writer: Writer, settings: Settings, timeout_s: float = 5.0) -> metrics.Benchmarks:
    return metrics.Benchmarks(writer, settings.runs_root, FilePool(), timeout_s=timeout_s)


def read_wanted(writer: Writer, settings: Settings, wanted: Wanted) -> bool:
    [(attempt_id, dir_run, path)] = wanted.asked
    return benchmarks(writer, settings).read(attempt_id, dir_run, path)


def test_snakemake_row_at_job_end_asks_its_benchmark(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    [row] = rows(writer)
    attempt = writer.submit(lambda c: c.execute(select(attempts)).one()).result()
    assert wanted.asked == [(attempt.id, RUN, BENCH)]
    assert row.attempt_id == attempt.id and (row.engine, row.tag) == ("snakemake", "sample=S1")
    assert (row.run_state, row.state, row.source) == ("running", "succeeded", None)
    assert (row.cpus, row.mem_bytes, row.time_limit_s) == (2, 2048 * MIB, 600.0)
    assert row.ended_at == T0 + timedelta(minutes=20)
    assert row.realtime_s is None and row.wait_s is None and row.partition is None


def test_snakemake_failed_job_has_its_row(writer: Writer, settings: Settings) -> None:
    launch = add_run(writer, settings, RUN, "smk", created_at=T0, engine="snakemake")
    smk_ingest(
        writer,
        settings,
        launch,
        None,  # no reader (a test, a rebuild): the row has no measure
        job_info(settings, 1, 1),
        smk_event(2, "job_error", jobid=1),
    )
    [row] = rows(writer)
    assert (row.state, row.source, row.cpus) == ("failed", None, 2)


def test_benchmark_values_and_units(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    bench_file(settings, BENCH_HEAD + BENCH_ROW)
    assert read_wanted(writer, settings, wanted)
    [row] = rows(writer)
    assert row.source == "benchmark"
    assert (row.realtime_s, row.time_eff) == (60.0, 0.1)
    assert (row.cpu_percent, row.cpu_eff) == (150.0, 0.75)  # cpu_time / s x 100, of 2 CPUs
    assert (row.peak_rss_bytes, row.mem_eff) == (1024 * MIB, 0.5)  # MiB
    assert row.peak_vmem_bytes == 2048 * MIB  # MiB
    assert (row.read_bytes, row.write_bytes) == (10 * MIB, 20 * MIB)  # MiB
    assert row.rchar_bytes is None and row.wchar_bytes is None


@pytest.mark.parametrize("null", ["NA", "-", ""])
def test_benchmark_nulls(writer: Writer, settings: Settings, null: str) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    fields = BENCH_ROW.rstrip("\n").split("\t")
    for i in (3, 6, 7, 9):  # max_vms, io_in, io_out, cpu_time
        fields[i] = null
    bench_file(settings, BENCH_HEAD + "\t".join(fields) + "\n")
    assert read_wanted(writer, settings, wanted)
    [row] = rows(writer)
    assert (row.source, row.realtime_s, row.peak_rss_bytes) == ("benchmark", 60.0, 1024 * MIB)
    assert row.peak_vmem_bytes is None and row.read_bytes is None and row.write_bytes is None
    assert row.cpu_percent is None and row.cpu_eff is None


def test_an_all_na_benchmark_measures_nothing(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    bench_file(settings, BENCH_HEAD + "\t".join(["NA"] * 10) + "\n")
    read_wanted(writer, settings, wanted)
    [row] = rows(writer)
    assert row.source is None and row.realtime_s is None and row.cpus == 2


def test_a_symlinked_benchmark_is_ignored(
    writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    elsewhere = tmp_path / "elsewhere.tsv"
    elsewhere.write_text(BENCH_HEAD + BENCH_ROW)
    bench_file(settings, "").unlink()
    (make_run_dirs(settings.runs_root, RUN).launch_dir / BENCH).symlink_to(elsewhere)
    assert not read_wanted(writer, settings, wanted)
    assert rows(writer)[0].source is None


def test_an_oversize_benchmark_is_ignored(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    padding = "".join(BENCH_ROW for _ in range(failure.MAX_BENCHMARK_BYTES // len(BENCH_ROW)))
    bench_file(settings, BENCH_HEAD + padding + BENCH_ROW)
    assert not read_wanted(writer, settings, wanted)
    assert rows(writer)[0].source is None


def test_a_fifo_benchmark_is_ignored_at_once(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    path = bench_file(settings, "")
    path.unlink()
    os.mkfifo(path, 0o600)  # nothing ever writes to it
    began = time.monotonic()
    assert not read_wanted(writer, settings, wanted)
    assert time.monotonic() - began < 2.0
    assert rows(writer)[0].source is None


def wait_for(check: Any, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not check():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.02)


def test_a_blocked_benchmark_delays_no_event(
    writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = threading.Event()

    def blocked(*args: Any) -> Any:
        gate.wait(10)  # a file system that does not answer
        return read_benchmark(*args)

    monkeypatch.setattr(metrics, "read_benchmark", blocked)
    stop = threading.Event()
    reader = benchmarks(writer, settings, timeout_s=30)
    reader.start(stop)
    try:
        bench_file(settings, BENCH_HEAD + BENCH_ROW)
        began = time.monotonic()
        launch = smk_job(writer, settings, reader)  # job 1: its read blocks
        smk_ingest(
            writer,
            settings,
            launch,
            reader,
            job_info(settings, 3, 2),
            smk_event(4, "job_finished", job_id=2),
        )
        assert time.monotonic() - began < 2.0  # the events went on
        assert [r.state for r in rows(writer)] == ["succeeded", "succeeded"]
        assert {r.source for r in rows(writer)} == {None}
        gate.set()
        wait_for(lambda: rows(writer)[0].source == "benchmark")
    finally:
        gate.set()
        stop.set()


def test_a_stalled_benchmark_keeps_one_route_slot_only(
    writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-P3FU105B-01, SEC-P3FU105B-01: after a stall, no further read is submitted until the
    stuck one ends, so the routes' file pool keeps its slots (dev-env §15.3 req. 13)."""
    gate = threading.Event()
    calls: list[str] = []

    def blocked(*args: Any) -> Any:
        calls.append(args[2])
        gate.wait(10)  # a mount that does not answer
        return None

    monkeypatch.setattr(metrics, "read_benchmark", blocked)
    pool = FilePool(2, 0)  # the routes' pool, small: two stuck benchmark reads would fill it
    reader = metrics.Benchmarks(writer, settings.runs_root, pool, timeout_s=0.05)
    stop = threading.Event()
    reader.start(stop)
    try:
        for i in range(4):
            reader.want(f"att_{i}", RUN, f"b{i}.tsv")
        time.sleep(0.5)  # well past several timeouts
        assert calls == ["b0.tsv"]  # one read in flight, the others wait
        assert pool.run(lambda: "route", 1.0) == "route"  # a route read still has its slot
        gate.set()
        wait_for(lambda: len(calls) == 4)  # the stuck read ended: the queue goes on
    finally:
        gate.set()
        stop.set()


def test_a_tiny_benchmark_time_gives_no_huge_cpu_percent(
    writer: Writer, settings: Settings
) -> None:
    """SEC-P3FU105B-02: CPU % is a ratio computed here, capped as §3.7's Ingest checks say."""
    wanted = Wanted()
    smk_job(writer, settings, wanted)
    fields = BENCH_ROW.rstrip("\n").split("\t")
    fields[0], fields[9] = "0.000000001", "1000"  # s, cpu_time: 1e14 %
    bench_file(settings, BENCH_HEAD + "\t".join(fields) + "\n")
    assert read_wanted(writer, settings, wanted)
    [row] = rows(writer)
    assert row.cpu_percent is None and row.cpu_eff is None


def test_the_reader_drops_what_its_queue_cannot_hold(writer: Writer, settings: Settings) -> None:
    reader = metrics.Benchmarks(writer, settings.runs_root, FilePool(), backlog=1)
    began = time.monotonic()
    for i in range(3):  # no thread drains it: never waits
        reader.want(f"att_{i}", RUN, BENCH)
    assert time.monotonic() - began < 1.0


def test_snakemake_on_slurm_sacct_measures_first(writer: Writer, settings: Settings) -> None:
    wanted = Wanted()
    smk_job(writer, settings, wanted, local=False)
    writer.submit(lambda c: c.execute(update(attempts).values(native_id="4242"))).result()
    bench_file(settings, BENCH_HEAD + BENCH_ROW)
    assert read_wanted(writer, settings, wanted)
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(state="succeeded"))
    ).result()
    write_cache(settings, RUN, {"4242": SACCT_ROW})
    assert fill(writer, settings) == 1
    [row] = rows(writer)
    assert row.source == "sacct"
    assert (row.realtime_s, row.peak_rss_bytes) == (1000.0, 2**30)  # sacct's
    assert row.peak_vmem_bytes == 2048 * MIB and row.read_bytes == 10 * MIB  # the benchmark's
    # a benchmark read after the sweep keeps sacct's measures
    assert benchmarks(writer, settings).read(row.attempt_id, RUN, BENCH)
    after = rows(writer)[0]
    assert (after.source, after.realtime_s, after.peak_rss_bytes) == ("sacct", 1000.0, 2**30)
