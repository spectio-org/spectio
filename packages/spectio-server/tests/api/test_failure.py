"""The failure summary and the resources per job (P1 Task 29; api §5 note of 2026-10-28, Run
and Resources; architecture §13.7; dev-env §15.3 req. 15).

`sacct` is a fake on its own PATH directory (`slurm-mini`, P1 Task 22, is not built). The
Snakemake side is fed by synthetic event lines in the shape the logger plugin is to send (P1
Task 7 is not built).
"""

import json
import os
import stat
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from spectio.config import Settings
from spectio.runner.rundir import RunPaths, make_run_dirs
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.failure import Accounting, parse_smk_slurm_message
from spectio_server.files.pool import FilePool
from spectio_server.projector.ingest import ingest
from spectio_server.serve import boot
from spectio_server.stages.freeze import StageSources
from spectio_server.store.db import open_db
from spectio_server.store.schema import events, tasks
from spectio_server.store.writer import Writer

from ..test_serve import head_files, make_run, run_id, settle
from .conftest import add_run, client_for

API = "/api/v1"
RUN = "run_01K8T2F1XTVRES0000000000F9"
HASHES = [(f"{n:02x}", f"{n:030x}") for n in range(40)]

FAKE = """#!{python}
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a") as f:
    f.write(json.dumps(sys.argv) + "\\n")
delay = os.path.join(here, "delay")
if os.path.exists(delay):
    time.sleep(float(open(delay).read()))
ids = sys.argv[sys.argv.index("-j") + 1].split(",")
for job in ids:
    print(f"{{job}}|OUT_OF_MEMORY|0:125|None|0|00:01:05|2G|00:10:00")
    print(f"{{job}}.batch|OUT_OF_MEMORY|0:125||2097152K|00:01:05||")
"""


class Fake:
    """A fake `sacct` that answers OUT_OF_MEMORY for every ID it is asked."""

    def __init__(self, root: Path) -> None:
        self.dir = root / "slurm-bin"
        self.dir.mkdir()
        self.path = self.dir / "sacct"
        self.path.write_text(FAKE.format(python=sys.executable))
        self.path.chmod(0o755)

    def calls(self) -> list[list[str]]:
        log = self.dir / "calls.jsonl"
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    def ids(self) -> list[str]:
        return [job for argv in self.calls() for job in argv[argv.index("-j") + 1].split(",")]


@pytest.fixture
def fakebin(tmp_path: Path) -> Fake:
    return Fake(tmp_path)


def accounting(settings: Settings, fake: Fake, **kwargs: Any) -> Accounting:
    """Accounting on the fake, with no thread: a test runs each due call with `step()`."""
    return Accounting(settings.runs_root, fake.path, start_thread=False, interval_s=0, **kwargs)


def event(n: int, type_: str, run: str = RUN, **data: Any) -> SpoolEvent:
    nf = type_.startswith("nextflow.")
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_f{n}",
            "run": run,
            "launch": 1,
            "producer": "nf-spectio/0.0.1" if nf else "snakemake-logger-spectio/0.0.1",
            "seq": n,
            "time": "2026-10-31T09:00:00Z",
            "type": type_,
            "data": data,
        }
    )


def push(writer: Writer, settings: Settings, launch_id: str, *found: SpoolEvent) -> None:
    sources = StageSources(None, settings.runs_root)
    batch = SpoolBatch(list(found), {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()


class Run:
    """A run of `engine`, its directories made, fed with synthetic events."""

    def __init__(self, settings: Settings, writer: Writer, engine: str = "nextflow") -> None:
        self.settings, self.writer = settings, writer
        self.launch_id = add_run(writer, settings, RUN, "r", "running", engine=engine)
        self.paths: RunPaths = make_run_dirs(settings.runs_root, RUN)
        (self.paths.run_dir / ".spectio").mkdir(mode=0o700, exist_ok=True)
        self.seq = 0

    def push(self, type_: str, **data: Any) -> None:
        self.seq += 1
        push(self.writer, self.settings, self.launch_id, event(self.seq, type_, **data))

    def nf_task(
        self, i: int, attempt: int, status: str, action: str | None = None, **trace: Any
    ) -> Path:
        workdir = self.paths.work_dir.joinpath(*HASHES[i])
        workdir.mkdir(parents=True, exist_ok=True)
        common = {"process": "ALIGN", "tag": f"S{i:02d}", "attempt": attempt}
        native = trace.pop("native_id", str(8812400 + 10 * i + attempt))
        where = {"workdir": str(workdir), "native_id": native}
        self.push("nextflow.onTaskSubmit", **common, trace=where)
        exit_ = trace.pop("exit", "1" if status == "FAILED" else "0")
        self.push(
            "nextflow.onTaskComplete",
            **common,
            errorAction=action,
            trace={**where, "status": status, "exit": exit_, **trace},
        )
        return workdir

    def task_ids(self) -> list[str]:
        with self.writer.engine.connect() as conn:
            return list(conn.execute(select(tasks.c.id).order_by(tasks.c.id)).scalars())


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)


def detail(client: TestClient) -> dict[str, Any]:
    found = client.get(f"{API}/runs/{RUN}")
    assert found.status_code == 200, found.text
    return found.json()  # type: ignore[no-any-return]


def task_items(client: TestClient) -> list[dict[str, Any]]:
    found = client.get(f"{API}/runs/{RUN}/tasks")
    assert found.status_code == 200, found.text
    return found.json()["items"]  # type: ignore[no-any-return]


# --- Snakemake's own message (architecture §13.7, Failure reason) ----------------------------


def test_smk_message_parsed() -> None:
    one = parse_smk_slurm_message(
        "SLURM-job '8812477' failed, SLURM status is: 'OUT_OF_MEMORY'. Reason: Step 0: OutOfMemory."
    )
    assert one is not None
    assert (one.state, one.reason, one.state_source) == (
        "OUT_OF_MEMORY",
        "Step 0: OutOfMemory",
        "engine_message",
    )
    many = parse_smk_slurm_message(
        "Error in rule a\nSLURM-job '8812477' failed, SLURM status is: 'FAILED'. Reasons: "
        "Step 0: NonZeroExitCode, Step 1: OutOfMemory.\nmore"
    )
    assert many is not None
    assert (many.state, many.reason) == ("FAILED", "Step 0: NonZeroExitCode, Step 1: OutOfMemory")
    node = parse_smk_slurm_message(
        "SLURM-job '8812477' failed due to a node failure, SLURM status is: 'NODE_FAIL'. Failed "
        "nodes will be excluded from future job submissions. Consider enabling requeueing …"
    )
    assert node is not None
    assert (node.state, node.reason) == ("NODE_FAIL", "node failure")
    for text in (
        "Error in rule compare, jobid: 30",  # the local executor's text
        "SLURM-job '1' failed, SLURM status is: 'lower'. Reason: x.",
        "SLURM-job '1' failed, SLURM status is: 'FAILED'. Reason: \x1b]8;;http://e\x07.",
        "",
    ):
        found = parse_smk_slurm_message(text)
        assert found is None or found.reason is None, text  # never a control character kept


def test_smk_message_no_sacct() -> None:
    found = parse_smk_slurm_message(
        "SLURM-job '8812477' failed, SLURM status is: 'TIMEOUT'. Detailed failure reason "
        "unavailable (status command is not 'sacct')."
    )
    assert found is not None
    assert (found.state, found.reason) == ("TIMEOUT", None)


# --- Nextflow -------------------------------------------------------------------------------


def test_nf_failure_summary(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """Exit 137 on its last attempt: process, tag, exit code, job ID; the scheduler's fields
    from sacct on the first view; the last 20 lines of `.command.log`."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "RETRY")
    workdir = run.nf_task(0, 2, "FAILED", "TERMINATE", exit="137", memory="2147483648")
    lines = [f"line {n} \x1b[31mred\x1b[0m" for n in range(30)]
    write_private(workdir / ".command.log", "\n".join(lines) + "\n")
    run.push("nextflow.onFlowComplete", success=False)
    assert fakebin.calls() == []  # nothing asked before anyone looks

    first = detail(client)
    assert first["state"] == "failed" and first["failures_total"] == 1
    (failure,) = first["failures"]
    assert failure["task_id"] == run.task_ids()[0]
    assert (failure["process"], failure["tag"], failure["attempt_n"]) == ("ALIGN", "S00", 2)
    assert (failure["exit_code"], failure["native_id"]) == (137, "8812402")
    assert failure["log_tail"] == "\n".join(f"line {n} red" for n in range(10, 30))
    assert failure["scheduler"]["accounting"] == "pending"
    assert failure["scheduler"]["state_source"] is None
    assert failure["scheduler"]["req_mem_bytes"] == 2147483648  # the trace's, meanwhile
    assert failure["scheduler"]["usage_source"] is None  # no measure in this trace

    assert acct.step()  # the sacct thread's one call
    assert fakebin.ids() == ["8812402"]
    scheduler = detail(client)["failures"][0]["scheduler"]
    assert scheduler == {
        "state": "OUT_OF_MEMORY",
        "reason": None,
        "state_source": "sacct",
        "req_mem_bytes": 2 * 1024**3,
        "max_rss_bytes": 2 * 1024**3,
        "time_limit_s": 600,
        "elapsed_s": 65,
        "usage_source": "sacct",
        "accounting": "available",
    }
    assert not acct.step() and len(fakebin.calls()) == 1  # cached: never asked again


def test_nf_log_tail_falls_back_to_err(settings: Settings, writer: Writer) -> None:
    client = client_for(settings, writer)
    run = Run(settings, writer)
    workdir = run.nf_task(0, 1, "FAILED", "TERMINATE")
    write_private(workdir / ".command.err", "boom\n")
    (failure,) = detail(client)["failures"]
    assert failure["log_tail"] == "boom"
    assert failure["scheduler"]["accounting"] == "unavailable"  # a local server: no sacct


def test_nf_log_tail_confined(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """The tail goes through the job-file reader: a `.command.log` that links out is not read."""
    client = client_for(settings, writer)
    run = Run(settings, writer)
    workdir = run.nf_task(0, 1, "FAILED", "TERMINATE")
    secret = tmp_path / "secret"
    secret.write_text("TOKEN\n")
    (workdir / ".command.log").symlink_to(secret)
    assert detail(client)["failures"][0]["log_tail"] is None


def test_nf_log_tail_stalled(settings: Settings, writer: Writer) -> None:
    """A file system that does not answer: no tail, and the answer comes at once."""
    client = client_for(settings, writer)
    release = threading.Event()
    pool = client.app.state.files = FilePool(1, 0)  # type: ignore[attr-defined]
    threading.Thread(target=lambda: pool.run(lambda: release.wait(10), 10), daemon=True).start()
    time.sleep(0.2)
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "TERMINATE")
    started = time.monotonic()
    assert detail(client)["failures"][0]["log_tail"] is None
    assert time.monotonic() - started < 2
    release.set()


def test_failures_capped(settings: Settings, writer: Writer) -> None:
    """25 failed jobs: `failures` has the first 10, `failures_total` 25."""
    client = client_for(settings, writer)
    run = Run(settings, writer)
    for i in range(25):
        run.nf_task(i, 1, "FAILED", "IGNORE")
    run.nf_task(30, 1, "COMPLETED")
    found = detail(client)
    assert found["failures_total"] == 25
    assert [f["tag"] for f in found["failures"]] == [f"S{i:02d}" for i in range(10)]


def test_failure_retried_then_succeeded_not_listed(settings: Settings, writer: Writer) -> None:
    client = client_for(settings, writer)
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "RETRY")
    run.nf_task(0, 2, "COMPLETED")
    found = detail(client)
    assert (found["failures"], found["failures_total"]) == ([], 0)


def test_resources_nf(authed_client: TestClient, replayed_flaky: str) -> None:
    """Task items carry the trace's requested and measured values."""
    items = authed_client.get(f"{API}/runs/{replayed_flaky}/tasks", params={"limit": 200}).json()
    by_tag = {(i["process"], i["tag"]): i for i in items["items"]}
    item = by_tag[("MAKE_READS", "S04")]
    assert item["attempt_n"] == 1
    assert item["resources"] == {
        "cpus": 1,
        "memory_bytes": 536870912,
        "time_s": 120.0,
        "realtime_s": 0.058,
        "cpu_percent": 75.0,
        "peak_rss_bytes": 3375104,
        "source": "trace",
    }
    retried = by_tag[("ALIGN", "S07.chunk0000")]
    assert retried["attempt_n"] == 2 and retried["state"] == "succeeded"


def test_resources_null_until_known(settings: Settings, writer: Writer) -> None:
    client = client_for(settings, writer)
    run = Run(settings, writer)
    run.push(
        "nextflow.onTaskSubmit",
        process="ALIGN",
        tag="S1",
        attempt=1,
        trace={"native_id": "5", "cpus": "x", "memory": float("1e300")},
    )
    (item,) = task_items(client)
    assert item["resources"] == dict.fromkeys(
        ("cpus", "memory_bytes", "time_s", "realtime_s", "cpu_percent", "peak_rss_bytes", "source")
    )


# --- Snakemake ------------------------------------------------------------------------------


def smk_job(run: Run, jobid: int, rule: str, sample: str, **info: Any) -> None:
    run.push(
        "snakemake.job_info",
        jobid=jobid,
        rule_name=rule,
        wildcards={"sample": sample},
        threads=4,
        resources={"mem_mb": 2000, "runtime": 30, "_cores": 4},
        **info,
    )


def test_resources_smk(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """threads and mem_mb requested; a benchmark file gives the measures (source benchmark);
    without one, sacct for the job's SLURM ID, in a batch (source sacct)."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    run = Run(settings, writer, "snakemake")
    smk_job(run, 1, "align", "S1", benchmark="benchmarks/align_S1.tsv")
    write_private(
        run.paths.launch_dir / "benchmarks" / "align_S1.tsv",
        "s\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n"
        "12.5\t0:00:12\t300.25\t400\t1\t1\t0\t0\t87.5\t10.9\n",
    )
    run.push("snakemake.job_finished", job_id=1)
    smk_job(run, 2, "align", "S2", benchmark="/etc/passwd")  # outside: not kept
    run.push("snakemake.slurm_submitted", jobid=2, external_jobid="8812477")
    run.push("snakemake.job_finished", job_id=2)
    smk_job(run, 3, "align", "S3")  # still running: nothing measured, nothing asked
    run.push("snakemake.slurm_submitted", jobid=3, external_jobid="8812478")

    items = {i["tag"]: i for i in task_items(client)}
    requested = {"cpus": 4, "memory_bytes": 2000 * 1024**2, "time_s": 1800.0}
    assert items["sample=S1"]["resources"] == {
        **requested,
        "realtime_s": 12.5,
        "cpu_percent": 87.5,
        "peak_rss_bytes": int(300.25 * 1024**2),
        "source": "benchmark",
    }
    unknown = {"realtime_s": None, "cpu_percent": None, "peak_rss_bytes": None, "source": None}
    assert items["sample=S2"]["resources"] == {**requested, **unknown}
    assert items["sample=S3"]["resources"] == {**requested, **unknown}

    assert acct.step()
    assert fakebin.ids() == ["8812477"]  # the ended job without a benchmark, only
    items = {i["tag"]: i for i in task_items(client)}
    assert items["sample=S2"]["resources"] == {
        **requested,
        "realtime_s": 65.0,
        "cpu_percent": None,
        "peak_rss_bytes": 2 * 1024**3,
        "source": "sacct",
    }


def test_smk_failure_from_message(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """The SLURM state and reason come from the executor plugin's text, which is parsed and
    never stored; the tail is the job's SLURM log; Snakemake failures ask sacct nothing."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    run = Run(settings, writer, "snakemake")
    smk_job(run, 7, "align", "S1")
    log = ".snakemake/slurm_logs/rule_align/S1/8812477.log"
    write_private(run.paths.launch_dir / log, "start\nslurmstepd: error: Detected 1 oom_kill\n")
    text = (
        "SLURM-job '8812477' failed, SLURM status is: 'OUT_OF_MEMORY'. Reason: Step 0: "
        "OutOfMemory. export TOKEN=s3cret"
    )
    run.push(
        "snakemake.job_error",
        jobid=7,
        rule_name="align",
        log=[log],
        aux={"external_jobid": "8812477"},
        msg=text,
    )
    (failure,) = detail(client)["failures"]
    assert failure["scheduler"]["state"] == "OUT_OF_MEMORY"
    assert failure["scheduler"]["reason"] == "Step 0: OutOfMemory"
    assert failure["scheduler"]["state_source"] == "engine_message"
    assert failure["scheduler"]["req_mem_bytes"] == 2000 * 1024**2
    assert failure["scheduler"]["time_limit_s"] == 1800
    assert failure["native_id"] == "8812477"
    assert failure["log_tail"] == "start\nslurmstepd: error: Detected 1 oom_kill"
    assert not acct.step() and fakebin.calls() == []
    with writer.engine.connect() as conn:
        stored = json.dumps(list(conn.execute(select(events.c.payload)).scalars()))
    assert "s3cret" not in stored and "SLURM-job" not in stored


# --- dev-env §15.3 req. 15 ------------------------------------------------------------------


def test_req15_rebuild_no_calls(settings: Settings, fakebin: Fake) -> None:
    """An index rebuild and a spool replay call sacct never; the values come back from
    `.spectio/sacct.json`."""
    assert settings.db_dir is not None
    rid = run_id(7)
    spool = ("nextflow-26.10.4_plugin_toolerr.spool.jsonl", "nf-spectio-1-0001.jsonl")
    head_files(make_run(settings.runs_root, rid, spool=spool))
    row = {
        "state": "FAILED",
        "exit_code": 1,
        "reason": "NonZeroExitCode",
        "max_rss_bytes": 1048576,
        "elapsed_s": 3,
        "req_mem_bytes": 536870912,
        "time_limit_s": 120,
    }
    cache = settings.runs_root / rid / ".spectio" / "sacct.json"
    write_private(cache, json.dumps({"v": 1, "jobs": {"24903": row}}))
    booted = boot(settings, settings.db_dir)
    try:
        settle(booted)
        assert fakebin.calls() == []
        client = client_for(settings, booted.writer)
        acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
        found = client.get(f"{API}/runs/{rid}").json()
        (failure,) = found["failures"]
        assert (failure["process"], failure["native_id"]) == ("COMPARE", "24903")
        assert failure["scheduler"]["state"] == "FAILED"
        assert failure["scheduler"]["state_source"] == "sacct"
        assert not acct.step() and fakebin.calls() == []
    finally:
        booted.close()


def test_req15_cache_file(
    settings: Settings, writer: Writer, fakebin: Fake, tmp_path: Path
) -> None:
    """`.spectio/sacct.json` is written 0600, by a rename in the run's checked directory: a
    symlink planted there is replaced, never followed."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "TERMINATE")
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("{}")
    cache = run.paths.run_dir / ".spectio" / "sacct.json"
    cache.symlink_to(elsewhere)
    detail(client)
    assert acct.step()
    assert elsewhere.read_text() == "{}"
    st = os.lstat(cache)
    assert stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600
    assert json.loads(cache.read_text())["jobs"]["8812401"]["state"] == "OUT_OF_MEMORY"


def test_req15_cache_file_refused(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """A cache file others can write is not read: the job is asked again."""
    client = client_for(settings, writer)
    acct = client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "TERMINATE")
    cache = run.paths.run_dir / ".spectio" / "sacct.json"
    write_private(cache, json.dumps({"v": 1, "jobs": {"8812401": {"state": "COMPLETED"}}}))
    cache.chmod(0o622)
    assert detail(client)["failures"][0]["scheduler"]["accounting"] == "pending"
    assert acct.step() and fakebin.ids() == ["8812401"]


@pytest.mark.parametrize(
    "slurm",
    [{"accounting": False}, {}],  # turned off; on, but no sacct path recorded
)
def test_req15_off(
    settings: Settings, writer: Writer, fakebin: Fake, slurm: dict[str, Any]
) -> None:
    """`[slurm] accounting = false`: no call; usage_source null, accounting unavailable."""
    if "accounting" in slurm:
        slurm = {**slurm, "sacct": str(fakebin.path)}
    off = Settings(
        data_dir=settings.data_dir,
        db_dir=settings.db_dir,
        runs_root=settings.runs_root,
        executor="slurm",
        slurm=slurm,
    )
    acct = Accounting.from_settings(off, start_thread=False)
    assert not acct.enabled
    client = client_for(settings, writer)
    client.app.state.accounting = acct  # type: ignore[attr-defined]
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "TERMINATE")
    scheduler = detail(client)["failures"][0]["scheduler"]
    assert scheduler["usage_source"] is None and scheduler["accounting"] == "unavailable"
    assert not acct.step() and fakebin.calls() == []


def test_req15_on_from_settings(settings: Settings, fakebin: Fake) -> None:
    on = Settings(
        data_dir=settings.data_dir,
        db_dir=settings.db_dir,
        runs_root=settings.runs_root,
        executor="slurm",
        slurm={"sacct": str(fakebin.path)},
    )
    assert Accounting.from_settings(on, start_thread=False).enabled
    assert not Accounting.from_settings(settings, start_thread=False).enabled  # local mode


def test_req15_hung_sacct_never_blocks(settings: Settings, writer: Writer, fakebin: Fake) -> None:
    """A `sacct` that hangs runs on the accounting thread: requests and the writer go on, and
    it is killed at its timeout."""
    (fakebin.dir / "delay").write_text("30")
    client = client_for(settings, writer)
    acct = client.app.state.accounting = Accounting(  # type: ignore[attr-defined]
        settings.runs_root, fakebin.path, interval_s=0, timeout_s=1.0
    )
    run = Run(settings, writer)
    run.nf_task(0, 1, "FAILED", "TERMINATE")
    detail(client)  # asks; the thread calls the fake, which sleeps
    deadline = time.monotonic() + 5
    while not fakebin.calls() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert fakebin.calls()
    started = time.monotonic()
    assert detail(client)["failures"][0]["scheduler"]["accounting"] == "pending"
    writer.submit(lambda conn: None).result(timeout=1)
    assert time.monotonic() - started < 1
    deadline = time.monotonic() + 5
    while acct.status(RUN, "8812401") == "pending" and time.monotonic() < deadline:
        time.sleep(0.05)
    assert acct.status(RUN, "8812401") == "unavailable"  # killed at 1 s, not asked again


def test_old_database_opens(settings: Settings) -> None:
    """A database of P1 Task 28 (revision 0006) gains `attempts.scheduler` when it opens."""
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    config = Config()
    config.set_main_option("script_location", "spectio_server:migrations")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0006")
    with engine.connect() as conn:
        assert "scheduler" not in {c["name"] for c in inspect(conn).get_columns("attempts")}
    engine.dispose()
    engine, new = open_db(settings.db_dir)
    try:
        assert not new
        with engine.connect() as conn:
            assert "scheduler" in {c["name"] for c in inspect(conn).get_columns("attempts")}
    finally:
        engine.dispose()
