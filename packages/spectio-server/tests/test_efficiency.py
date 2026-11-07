"""The SLURM request and the CPU and memory efficiency, per job and per process or rule (P1
Task 34; api §5 note of 2026-11-07; schedulers §3.6; dev-env §15.3 req. 15, note 2026-11-07).

Both engines are handled alike (Thomas, 2026-11-07): Snakemake's request comes from
`job_info.resources` and its efficiency from `sacct`, then the job's benchmark file; Nextflow's
request from the trace record at submit, its efficiency from `sacct`, then the trace. `sacct`
is `test_failure`'s fake (`slurm-mini`, P1 Task 22, is not built).
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, update

from spectio.config import Settings
from spectio.runner.sacct import SacctRow
from spectio_server import efficiency, failure
from spectio_server.store.schema import attempts, environments, tasks
from spectio_server.store.writer import Writer

from .api.conftest import client_for
from .api.test_failure import (
    API,
    HASHES,
    RUN,
    Fake,
    Run,
    accounting,
    task_items,
    write_private,
)

MIB, GIB = 1024**2, 1024**3
NATIVE = "8812477"
ENGINES = ["snakemake", "nextflow"]
BENCH_HEAD = "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"


@pytest.fixture
def fakebin(tmp_path: Path) -> Fake:
    return Fake(tmp_path)


def on_slurm(writer: Writer) -> None:
    """The run's environment is a SLURM one (the test settings are local)."""
    writer.submit(lambda c: c.execute(update(environments).values(kind="slurm"))).result()


def processes(client: TestClient) -> dict[str, dict[str, Any]]:
    found = client.get(f"{API}/runs/{RUN}/processes")
    assert found.status_code == 200, found.text
    return {p["process"]: p for p in found.json()["items"]}


# --- One job of each engine: 2 CPUs, 2 GiB, 10 minutes ----------------------------------------


def submit(run: Run, engine: str, i: int = 0, native: str | None = NATIVE, **asked: Any) -> Path:
    """Job `i` submitted; returns the directory `sacct`'s WorkDir must name."""
    cpus, mem = asked.get("cpus", 2), asked.get("mem", 2 * GIB)
    if engine == "nextflow":
        workdir = run.paths.work_dir.joinpath(*HASHES[i])
        workdir.mkdir(parents=True, exist_ok=True)
        trace = {"workdir": str(workdir), "cpus": cpus, "memory": mem, "time": 600000}
        if native is not None:
            trace["native_id"] = native
        run.push("nextflow.onTaskSubmit", process="ALIGN", tag=f"S{i}", attempt=1, trace=trace)
        return workdir
    run.push(
        "snakemake.job_info",
        jobid=i + 1,
        rule_name="ALIGN",
        wildcards={"sample": f"S{i}"},
        threads=cpus,
        resources={"mem_mb": mem // MIB, "runtime": 10},
        benchmark=f"benchmarks/S{i}.tsv",
    )
    if native is not None:
        run.push("snakemake.slurm_submitted", jobid=i + 1, external_jobid=native)
    return run.paths.launch_dir


def finish(
    run: Run,
    engine: str,
    i: int = 0,
    cpu_s: float = 90,
    wall_s: float = 60,
    peak: int = GIB,
    mem: int = 2 * GIB,
) -> None:
    """Job `i` ended with the engine's measure: by default 90 CPU seconds over 60 s on 2 CPUs
    (0.75) and 1 GiB of 2 GiB (0.5). A Nextflow trace at the end repeats the request."""
    if engine == "nextflow":
        workdir = run.paths.work_dir.joinpath(*HASHES[i])
        trace = {
            "workdir": str(workdir),
            "cpus": 2,
            "memory": mem,
            "time": 600000,
            "status": "COMPLETED",
            "exit": "0",
            "%cpu": 100 * cpu_s / wall_s,
            "peak_rss": peak,
            "realtime": int(wall_s * 1000),
        }
        run.push("nextflow.onTaskComplete", process="ALIGN", tag=f"S{i}", attempt=1, trace=trace)
        return
    write_private(
        run.paths.launch_dir / "benchmarks" / f"S{i}.tsv",
        BENCH_HEAD + f"{wall_s}\t0:01:00\t{peak / MIB}\t1\t1\t1\t0\t0\t150\t{cpu_s}\n",
    )
    run.push("snakemake.job_finished", job_id=i + 1)


ENGINE_SOURCE = {"nextflow": "trace", "snakemake": "benchmark"}
MEASURED = {"cpu": 0.75, "mem": 0.5, "elapsed_s": 60.0, "peak_rss_bytes": GIB}
# The fake's answer: TotalCPU 52 s over 65 s on 2 CPUs, MaxRSS 2 GiB of ReqMem 2G.
FROM_SACCT = {"cpu": 0.4, "mem": 1.0, "elapsed_s": 65.0, "peak_rss_bytes": 2 * GIB}
NOTHING = dict.fromkeys(("cpu", "mem", "elapsed_s", "peak_rss_bytes", "source", "reason"))


# --- The request (api §5 note 2026-11-07, Task items) -----------------------------------------


REQUEST_KEYS = (
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


def request(**values: Any) -> dict[str, Any]:
    return {**dict.fromkeys(REQUEST_KEYS), **values}


def test_slurm_request_smk(settings: Settings, writer: Writer) -> None:
    """From `job_info.resources`; `slurm_extra` set gives `custom_options` true, never its text;
    a text value out of charset is null; a `localrule` job has no SLURM request."""
    client = client_for(settings, writer)
    on_slurm(writer)
    run = Run(settings, writer, "snakemake")
    asked = {
        "slurm_partition": "htc",
        "slurm_account": "lab",
        "qos": "normal",
        "cpus_per_task": 4,
        "mem_mb": 2048,
        "runtime": 30,
        "gpu": 1,
        "constraint": "skylake",
        "nodes": 1,
        "tasks": 1,
        "slurm_extra": "--export=ALL,TOKEN=secret",  # dropped by the SDK, flagged by the plugin
    }
    common = {"rule_name": "align", "threads": 2}
    run.push(
        "snakemake.job_info",
        jobid=1,
        wildcards={"s": "1"},
        resources=asked,
        custom_options=True,
        **common,
    )
    per_cpu = {"mem_mb_per_cpu": 1000, "gres": "gpu:a100:2", "slurm_partition": "a b;c"}
    run.push(
        "snakemake.job_info",
        jobid=2,
        wildcards={"s": "2"},
        resources=per_cpu,
        custom_options=False,
        **common,
    )
    run.push("snakemake.job_info", jobid=3, wildcards={"s": "3"}, local=True, **common)
    found = client.get(f"{API}/runs/{RUN}/tasks")
    assert "secret" not in found.text and "slurm_extra" not in found.text
    items = {i["tag"]: i["slurm"] for i in found.json()["items"]}
    assert items["s=1"] == {
        "request": request(
            partition="htc",
            account="lab",
            qos="normal",
            cpus=4,  # cpus_per_task wins over threads
            mem_bytes=2048 * MIB,
            time_limit_s=1800,
            gres="gpu:1",
            constraint="skylake",
            nodes=1,
            tasks=1,
        ),
        "allocated": None,
        "custom_options": True,
    }
    assert items["s=2"] == {
        "request": request(cpus=2, mem_per_cpu_bytes=1000 * MIB, gres="gpu:a100:2"),
        "allocated": None,
        "custom_options": False,
    }
    assert items["s=3"] is None


def test_slurm_request_nf(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """From the trace record at submit (`queue`, `cpus`, `memory`, `time`, `accelerator`;
    `account` is not sent); `custom_options` from `onFlowCreate`'s `clusterOptionsSet`, null
    while not known; `allocated` from `sacct` once the job ended."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    on_slurm(writer)
    run = Run(settings, writer)
    workdir = run.paths.work_dir.joinpath(*HASHES[0])
    workdir.mkdir(parents=True)
    trace = {
        "workdir": str(workdir),
        "native_id": NATIVE,
        "queue": "htc",
        "cpus": 4,
        "memory": 4 * GIB,
        "time": 3600000,
        "accelerator": 1,
    }
    run.push("nextflow.onTaskSubmit", process="ALIGN", tag="S0", attempt=1, trace=trace)
    asked = request(partition="htc", cpus=4, mem_bytes=4 * GIB, time_limit_s=3600, gres="gpu:1")
    (item,) = task_items(client)
    assert item["slurm"] == {"request": asked, "allocated": None, "custom_options": None}
    run.push("nextflow.onFlowCreate", clusterOptionsSet=True)
    fakebin.at(NATIVE, workdir)
    finish(run, "nextflow")
    task_items(client)
    assert acct.step()
    (item,) = task_items(client)
    assert item["slurm"] == {
        "request": asked,
        "allocated": {
            "partition": "htc",
            "account": "lab",
            "qos": "normal",
            "ncpus": 2,
            "req_mem_bytes": 2 * GIB,
            "time_limit_s": 600,
            "alloc_tres": "billing=2,cpu=2,mem=2G,node=1",
            "nnodes": 1,
        },
        "custom_options": True,
    }


@pytest.mark.parametrize("engine", ENGINES)
def test_slurm_null_on_local_run(settings: Settings, writer: Writer, engine: str) -> None:
    client = client_for(settings, writer)
    run = Run(settings, writer, engine)
    submit(run, engine)
    (item,) = task_items(client)
    assert item["slurm"] is None


# --- The formulas (schedulers §3.6) -----------------------------------------------------------


def test_eff_trace_and_benchmark() -> None:
    trace = {
        "cpus": 8,
        "cpu_percent": 400.0,
        "memory_bytes": 4 * GIB,
        "peak_rss_bytes": GIB,
        "realtime_s": 10.0,
    }
    assert efficiency.engine_measure("trace", trace) == {
        "cpu": 0.5,
        "mem": 0.25,
        "elapsed_s": 10.0,
        "peak_rss_bytes": GIB,
    }
    bench = {
        "cpus": 4,
        "cpu_time_s": 30.0,
        "realtime_s": 10.0,
        "memory_bytes": 1000 * MIB,
        "peak_rss_bytes": 250 * MIB,
        "cpu_percent": 300.0,
    }
    found = efficiency.engine_measure("benchmark", bench)
    assert (found["cpu"], found["mem"]) == (0.75, 0.25)
    over = efficiency.engine_measure("trace", {"cpus": 2, "cpu_percent": 300.0})
    assert over["cpu"] == 1.5  # never clamped
    assert efficiency.engine_measure("trace", {"cpus": 0, "cpu_percent": 300.0})["cpu"] is None
    assert efficiency.engine_measure("benchmark", {"cpus": 2})["mem"] is None


def test_eff_sacct_row() -> None:
    """`TotalCPU` / (`Elapsed` * `NCPUS`); `MaxRSS` / `ReqMem` (both made whole by the parser)."""
    row = SacctRow(
        state="COMPLETED",
        exit_code=0,
        reason=None,
        max_rss_bytes=2 * GIB,
        elapsed_s=65,
        req_mem_bytes=4 * GIB,
        time_limit_s=600,
        total_cpu_s=52.0,
        ncpus=2,
    )
    assert efficiency.sacct_measure(row) == {
        "cpu": 0.4,
        "mem": 0.5,
        "elapsed_s": 65.0,
        "peak_rss_bytes": 2 * GIB,
    }
    empty = SacctRow("COMPLETED", 0, None, None, None, None, None)
    assert efficiency.sacct_measure(empty) == dict.fromkeys(
        ("cpu", "mem", "elapsed_s", "peak_rss_bytes")
    )


# --- Per job: the states (schedulers §3.6, Timing) --------------------------------------------


@pytest.mark.parametrize("engine", ENGINES)
def test_eff_states(settings: Settings, writer: Writer, fakebin: Fake, engine: str) -> None:
    """running → pending_accounting with the engine's measure → available with sacct's."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    on_slurm(writer)
    run = Run(settings, writer, engine)
    fakebin.at(NATIVE, submit(run, engine))
    (item,) = task_items(client)
    assert item["efficiency"] == {**NOTHING, "state": "running"}
    assert not acct.step()  # nothing is asked while the job runs
    finish(run, engine)
    (item,) = task_items(client)
    assert item["efficiency"] == {
        **NOTHING,
        **MEASURED,
        "state": "pending_accounting",
        "source": ENGINE_SOURCE[engine],
    }
    assert acct.step() and fakebin.ids() == [NATIVE]
    (item,) = task_items(client)
    assert item["efficiency"] == {**NOTHING, **FROM_SACCT, "state": "available", "source": "sacct"}
    assert item["resources"]["source"] == ENGINE_SOURCE[engine]  # as P1 Task 29 shows it


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("case", ["local", "accounting_off", "no_job_id", "not_found"])
def test_eff_unavailable(
    settings: Settings, writer: Writer, fakebin: Fake, engine: str, case: str
) -> None:
    """`unavailable` with its reason, the engine's measure kept; a local run never asks."""
    client = client_for(settings, writer)
    acct = accounting(settings, fakebin, enabled=case != "accounting_off")
    client.app.state.accounting = acct  # type: ignore[attr-defined]
    if case != "local":
        on_slurm(writer)
    if case == "not_found":
        (fakebin.dir / "lag").write_text("-,-,-")
    run = Run(settings, writer, engine)
    fakebin.at(NATIVE, submit(run, engine, native=None if case == "no_job_id" else NATIVE))
    finish(run, engine)
    for _ in range(3 if case == "not_found" else 1):
        task_items(client)
        acct.step()
    (item,) = task_items(client)
    assert item["efficiency"] == {
        **NOTHING,
        **MEASURED,
        "state": "unavailable",
        "source": ENGINE_SOURCE[engine],
        "reason": case,
    }
    assert len(fakebin.calls()) == (3 if case == "not_found" else 0)


@pytest.mark.parametrize("engine", ENGINES)
def test_aggregate(settings: Settings, writer: Writer, engine: str) -> None:
    """Over each task's last attempt: jobs done of total, measured, mean and max of the ratios,
    the most common request with `varies`, the largest peak and elapsed time used."""
    client = client_for(settings, writer)
    run = Run(settings, writer, engine)
    submit(run, engine, 0)
    finish(run, engine, 0)  # 0.75, 0.5, 60 s, 1 GiB
    submit(run, engine, 1, mem=4 * GIB)
    finish(run, engine, 1, cpu_s=60, wall_s=120, mem=4 * GIB)  # 0.25, 0.25, 120 s
    submit(run, engine, 2)  # running
    found = processes(client)["ALIGN"]["efficiency"]
    assert found == {
        "jobs": {"done": 2, "total": 3},
        "measured": 2,
        "cpu_mean": 0.5,
        "cpu_max": 0.75,
        "mem_mean": 0.375,
        "mem_max": 0.5,
        "requested": {"cpus": 2, "mem_bytes": 2 * GIB, "time_limit_s": 600, "varies": True},
        "used": {"peak_rss_bytes_max": GIB, "elapsed_s_max": 120.0},
    }


@pytest.mark.parametrize("engine", ENGINES)
def test_aggregate_empty(settings: Settings, writer: Writer, engine: str) -> None:
    client = client_for(settings, writer)
    run = Run(settings, writer, engine)
    submit(run, engine)
    found = processes(client)["ALIGN"]["efficiency"]
    assert found == {
        "jobs": {"done": 0, "total": 1},
        "measured": 0,
        "cpu_mean": None,
        "cpu_max": None,
        "mem_mean": None,
        "mem_max": None,
        "requested": {"cpus": 2, "mem_bytes": 2 * GIB, "time_limit_s": 600, "varies": False},
        "used": {"peak_rss_bytes_max": None, "elapsed_s_max": None},
    }


# --- dev-env §15.3 req. 15, note 2026-11-07 ---------------------------------------------------


@pytest.mark.parametrize("engine", ENGINES)
def test_req15_5000_jobs(settings: Settings, writer: Writer, fakebin: Fake, engine: str) -> None:
    """The By process view queues every ended job with a SLURM ID: 5,000 jobs take 50 calls of
    at most 100 IDs, each asked once."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    on_slurm(writer)
    Run(settings, writer, engine)
    now = datetime.now(UTC)

    def many(conn: Any) -> None:
        rows = [
            {
                "id": f"tsk_{n:06d}",
                "created_at": now,
                "run_id": RUN,
                "process_or_rule": "ALIGN",
                "tag": f"S{n}",
                "state": "succeeded",
            }
            for n in range(5000)
        ]
        conn.execute(insert(tasks), rows)
        conn.execute(
            insert(attempts),
            [
                {
                    "id": f"att_{n:06d}",
                    "created_at": now,
                    "task_id": f"tsk_{n:06d}",
                    "n": 1,
                    "launch_n": 1,
                    "state": "succeeded",
                    "native_id": str(9000000 + n),
                    "work_dir": "/w",
                }
                for n in range(5000)
            ],
        )

    writer.submit(many).result()
    processes(client)
    processes(client)  # a second view queues nothing again
    calls = 0
    while acct.step():
        calls += 1
    assert calls == 50
    asked = fakebin.ids()
    assert len(asked) == len(set(asked)) == 5000
    assert max(len(argv[argv.index("-j") + 1].split(",")) for argv in fakebin.calls()) == 100


def test_req15_benchmark_read_once(
    settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ended attempt's benchmark is read once (CR-P3T34-01): a second By process view, as
    each live frame fetches, opens no benchmark file and gives the same measures."""
    client = client_for(settings, writer)
    run = Run(settings, writer, "snakemake")
    submit(run, "snakemake", 0, native=None)
    finish(run, "snakemake", 0)
    opened: list[str] = []
    real = failure._benchmark

    def spy(ctx: Any, dirs: str, path: str) -> dict[str, Any] | None:
        opened.append(path)
        return real(ctx, dirs, path)

    monkeypatch.setattr(failure, "_benchmark", spy)
    first = processes(client)["ALIGN"]["efficiency"]
    assert opened == ["benchmarks/S0.tsv"]
    assert processes(client)["ALIGN"]["efficiency"] == first
    assert opened == ["benchmarks/S0.tsv"]  # the second view opened nothing
    assert first["measured"] == 1
