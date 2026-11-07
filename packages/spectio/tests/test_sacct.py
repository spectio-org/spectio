"""`sacct` for failed jobs and job resources (P1 Task 29; dev-env §15.3 req. 15).

`fakebin` is a fake `sacct` in a directory of its own (`slurm-mini`, P1 Task 22, is not built):
it records its argument list and environment in `calls.jsonl`, and prints `out.txt`. The fields
asked for stay [to be validated] on a real SLURM.
"""

import itertools
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings, config_path
from spectio.runner import sacct
from spectio.runner.sacct import SacctLimiter, SacctRow, sacct_jobs

FAKE = """#!{python}
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a") as f:
    f.write(json.dumps({{"argv": sys.argv, "env": dict(os.environ)}}) + "\\n")
delay = os.path.join(here, "delay")
if os.path.exists(delay):
    time.sleep(float(open(delay).read()))
sys.stdout.write(open(os.path.join(here, "out.txt")).read())
"""

# What `sacct --parsable2 --noheader --format=JobID,State,…,AllocTRES,WorkDir` prints (the shape
# of the T3 probes, tests/fixtures/slurm/slurm-26.05.5/sacct-probes.json, with the efficiency
# fields of P1 Task 34; real fields, WorkDir among them, [to be validated]).
FIELDS = sacct.FORMAT.split(",")


def line(**values: str) -> str:
    """One `--parsable2` line in FORMAT's order; a field not given is empty."""
    unknown = set(values) - set(FIELDS)
    assert not unknown, unknown
    return "|".join(values.get(f, "") for f in FIELDS)


OOM = {"State": "OUT_OF_MEMORY", "ExitCode": "0:125", "Elapsed": "00:01:05"}
ARRAY = {"State": "FAILED", "ExitCode": "137:0", "Elapsed": "1-02:03:04"}
OUT = (
    "\n".join(
        [
            line(
                JobID="8812477",
                **OOM,
                Reason="None",
                MaxRSS="0",
                ReqMem="2G",
                Timelimit="00:10:00",
                TotalCPU="00:40.500",
                NCPUS="4",
                NNodes="1",
                Partition="htc",
                Account="lab",
                QOS="normal",
                AllocTRES="billing=4,cpu=4,mem=2G,node=1",
                WorkDir="/data/work/ab/cd",
            ),
            line(
                JobID="8812477.batch",
                **OOM,
                MaxRSS="2147480K",
                TotalCPU="00:40.000",
                NCPUS="4",
                NNodes="1",
                WorkDir="/data/work/ab/cd",
            ),
            line(
                JobID="8812477.extern",
                State="COMPLETED",
                ExitCode="0:0",
                MaxRSS="1024K",
                Elapsed="00:01:05",
                TotalCPU="00:00.500",
                NCPUS="4",
                NNodes="1",
                WorkDir="/data/work/ab/cd",
            ),
            line(
                JobID="8812345_3",
                **ARRAY,
                Reason="None",
                ReqMem="4000M",
                Timelimit="2-00:00:00",
                NCPUS="1",
                NNodes="1",
                WorkDir="/data/launch|x",
            ),
            line(
                JobID="8812345_3.batch", **ARRAY, MaxRSS="1.5G", NCPUS="1", WorkDir="/data/launch|x"
            ),
        ]
    )
    + "\n"
)


class Fake:
    def __init__(self, root: Path) -> None:
        self.dir = root / "slurm" / "bin"
        self.dir.mkdir(parents=True)
        self.path = self.dir / "sacct"
        self.path.write_text(FAKE.format(python=sys.executable))
        self.path.chmod(0o755)
        self.output(OUT)

    def output(self, text: str) -> None:
        (self.dir / "out.txt").write_text(text)

    def delay(self, seconds: float) -> None:
        (self.dir / "delay").write_text(str(seconds))

    def calls(self) -> list[dict[str, Any]]:
        log = self.dir / "calls.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]


@pytest.fixture
def fakebin(tmp_path: Path) -> Fake:  # this module's: a fake sacct, not the engines' fakes
    return Fake(tmp_path)


def test_req15_argv_and_id_check(fakebin: Fake) -> None:
    found = sacct_jobs(["8812477", "8812345_3"], sacct=fakebin.path)
    (call,) = fakebin.calls()
    assert call["argv"] == [
        str(fakebin.path),
        "--parsable2",
        "--noheader",
        "-j",
        "8812477,8812345_3",
        f"--user={os.geteuid()}",  # the server user's own jobs only
        "--format=JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,TotalCPU,NCPUS,"
        "NNodes,Partition,Account,QOS,AllocTRES,WorkDir",
    ]
    assert found is not None and set(found) == {"8812477", "8812345_3"}
    for bad in (["1;rm"], ["1234567890123"], ["1_123456789"], ["8812477", "-j"], [""], [" 1"]):
        with pytest.raises(sacct.Refused):
            sacct_jobs(bad, sacct=fakebin.path)
    with pytest.raises(sacct.Refused):
        sacct_jobs([str(n) for n in range(101)], sacct=fakebin.path)  # 100 IDs per call
    assert len(fakebin.calls()) == 1  # every refusal before any call


def test_req15_tool_checked(fakebin: Fake, tmp_path: Path) -> None:
    """The stored path must be absolute, a regular file, not writable by others."""
    fakebin.path.chmod(0o775)
    for path in (fakebin.path, Path("sacct"), tmp_path):
        with pytest.raises(sacct.Refused):
            sacct_jobs(["1"], sacct=path)
    assert fakebin.calls() == []


def test_req15_env_explicit(fakebin: Fake, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLURM_CONF", "/nonexistent/evil.conf")
    monkeypatch.setenv("LD_PRELOAD", "/nonexistent/evil.so")
    monkeypatch.setenv("SACCT_FORMAT", "JobID")
    sacct_jobs(["8812477"], sacct=fakebin.path)
    env = fakebin.calls()[0]["env"]
    env.pop("LC_CTYPE", None)  # Python itself may set it at start (PEP 538), not the caller
    assert env == {"PATH": str(fakebin.dir), "SLURM_TIME_FORMAT": "standard"}


def test_init_stores_the_sacct_path(home: Path, tools: Any, login: Any) -> None:
    """`spectio init` resolves `sacct` once, through the login shell, and records it."""
    fakes = tools("nextflow", "snakemake", "sbatch")
    (fakes / "sacct").write_text("#!/bin/sh\nexit 0\n")
    (fakes / "sacct").chmod(0o755)
    result = CliRunner().invoke(app, ["init"], input="")
    assert result.exit_code == 0, result.output
    assert Settings().slurm.sacct == fakes / "sacct"
    assert "sacct = " in config_path().read_text()
    login(home.parent / "empty")  # sacct no longer on the PATH: the recorded one stays
    assert CliRunner().invoke(app, ["init"], input="").exit_code == 0
    assert Settings().slurm.sacct == fakes / "sacct"


def test_init_warns_without_sacct(home: Path, tools: Any) -> None:
    tools("nextflow", "snakemake")
    result = CliRunner().invoke(app, ["init"], input="")
    assert result.exit_code == 0, result.output
    assert "sacct not found" in result.output
    assert Settings().slurm.sacct is None


def test_sacct_parse_and_timeout(fakebin: Fake) -> None:
    found = sacct_jobs(["8812477", "8812345_3", "9999"], sacct=fakebin.path)
    assert found == {
        "8812477": SacctRow(
            state="OUT_OF_MEMORY",
            exit_code=0,
            reason=None,
            max_rss_bytes=2147480 * 1024,  # the largest of its steps
            elapsed_s=65,
            req_mem_bytes=2 * 1024**3,
            time_limit_s=600,
            work_dir="/data/work/ab/cd",
            total_cpu_s=40.5,  # the sum of its steps, not the allocation row's as well
            ncpus=4,
            nnodes=1,
            partition="htc",
            account="lab",
            qos="normal",
            alloc_tres="billing=4,cpu=4,mem=2G,node=1",
        ),
        "8812345_3": SacctRow(
            state="FAILED",
            exit_code=137,
            reason=None,
            max_rss_bytes=int(1.5 * 1024**3),
            elapsed_s=86400 + 2 * 3600 + 3 * 60 + 4,
            req_mem_bytes=4000 * 1024**2,
            time_limit_s=2 * 86400,
            work_dir="/data/launch|x",  # the last field: a `|` in it stays
            ncpus=1,
            nnodes=1,
        ),
    }  # 9999: no row, so not in the result
    assert sacct.TIMEOUT_S == 10
    fakebin.delay(30)
    started = time.monotonic()
    assert sacct_jobs(["8812477"], timeout_s=0.5, sacct=fakebin.path) is None
    assert time.monotonic() - started < 5  # killed at the timeout, never waited for


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (
            {
                "State": "CANCELLED by 1000",
                "ExitCode": "0:15",
                "Reason": "None",
                "ReqMem": "4Gn",
                "NNodes": "2",
                "Timelimit": "UNLIMITED",
            },
            ("CANCELLED", 0, None, 2 * 4 * 1024**3, None),  # per node, times NNodes
        ),
        (
            {
                "State": "TIMEOUT",
                "ExitCode": "0:0",
                "Reason": "Reason=\x1b[31mx",
                "ReqMem": "1T",
                "Timelimit": "Partition_Limit",
            },
            ("TIMEOUT", 0, None, 1024**4, None),
        ),
        (
            {
                "State": "FAILED",
                "ExitCode": "1:0",
                "Reason": "JobLaunchFailure",
                "ReqMem": "16Mc",
                "NCPUS": "4",
                "Timelimit": "05:30",
            },
            ("FAILED", 1, "JobLaunchFailure", 4 * 16 * 1024**2, 330),  # per CPU, times NCPUS
        ),
        (
            {"State": "FAILED", "ReqMem": "16Mc"},  # per CPU with no NCPUS: not known
            ("FAILED", None, None, None, None),
        ),
        (
            {
                "State": "weird state!",
                "ExitCode": "x",
                "Reason": "R" * 300,
                "ReqMem": "-1",
                "Timelimit": "1-x",
                "TotalCPU": "x",
                "NCPUS": "-1",
                "Partition": "a b",
                "QOS": "\x1b",
                "AllocTRES": "cpu=4;rm",
                "WorkDir": "w\x1b",
            },
            (None, None, None, None, None),
        ),
    ],
)
def test_sacct_values_as_data(values: dict[str, str], expected: tuple[Any, ...]) -> None:
    """Every field is parsed as data: an odd or over-long value is None, never an error."""
    work_dir = values.pop("WorkDir", "/w")
    row = sacct.parse_sacct(line(JobID="1", WorkDir=work_dir, **values) + "\n", {"1"})["1"]
    assert (row.state, row.exit_code, row.reason, row.req_mem_bytes, row.time_limit_s) == expected
    assert row.work_dir == (None if work_dir != "/w" else "/w")  # relative or a control: None
    if expected[0] is None:
        assert (row.total_cpu_s, row.ncpus, row.partition, row.qos, row.alloc_tres) == (None,) * 5


def test_eff_sacct() -> None:
    """P1 Task 34 (schedulers §3.6): TotalCPU summed over the job's steps (batch, extern and each
    srun step), never with the allocation row's, which already holds them; MaxRSS the largest
    of any step; ReqMem per CPU times NCPUS; the allocation's partition, account, QOS and TRES.
    Step rows have no WorkDir of their own [to be validated]: they join their job by ID."""
    text = "\n".join(
        [
            line(
                JobID="77",
                State="COMPLETED",
                ExitCode="0:0",
                Elapsed="00:01:05",
                ReqMem="1000Mc",
                Timelimit="01:00:00",
                TotalCPU="01:40.500",
                NCPUS="4",
                NNodes="1",
                Partition="gpu",
                Account="lab",
                QOS="high",
                AllocTRES="cpu=4,gres/gpu=1,mem=4000M,node=1",
                WorkDir="/data/launch",
            ),
            line(JobID="77.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:40.000", NCPUS="4"),
            line(JobID="77.extern", State="COMPLETED", MaxRSS="1M", TotalCPU="00:00.500"),
            line(JobID="77.0", State="COMPLETED", MaxRSS="3G", TotalCPU="01:00.000", NCPUS="4"),
            line(JobID="78.batch", State="COMPLETED", MaxRSS="9G"),  # not asked: ignored
        ]
    )
    row = sacct.parse_sacct(text, {"77"})["77"]
    assert row.total_cpu_s == 100.5
    assert row.max_rss_bytes == 3 * 1024**3
    assert row.req_mem_bytes == 4 * 1000 * 1024**2
    assert (row.ncpus, row.nnodes, row.elapsed_s, row.time_limit_s) == (4, 1, 65, 3600)
    assert (row.partition, row.account, row.qos) == ("gpu", "lab", "high")
    assert row.alloc_tres == "cpu=4,gres/gpu=1,mem=4000M,node=1"
    alone = sacct.parse_sacct(line(JobID="5", TotalCPU="2-01:00:00", WorkDir="/w"), {"5"})["5"]
    assert alone.total_cpu_s == 49 * 3600  # no step rows: the allocation row's own


def test_eff_sacct_steps_join_their_own_job() -> None:
    """SEC-P3T34-04: a step row counts only for the allocation row printed before it (sacct
    prints steps after their job [to be validated] on slurm-mini). Two allocation rows for one
    ID (a reused ID, or a forged line) are ambiguous: no row, so no other job's CPU or memory is
    mixed in, and a step before any allocation row is ignored."""
    reused = "\n".join(
        [
            line(JobID="123", State="COMPLETED", TotalCPU="00:01.000", WorkDir="/old"),
            line(JobID="123.batch", State="COMPLETED", MaxRSS="9G", TotalCPU="10:00.000"),
            line(JobID="123", State="COMPLETED", TotalCPU="00:02.000", WorkDir="/data/launch"),
            line(JobID="123.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:02.000"),
        ]
    )
    assert sacct.parse_sacct(reused, {"123"}) == {}
    early = "\n".join(
        [
            line(JobID="9.batch", State="COMPLETED", MaxRSS="9G", TotalCPU="10:00.000"),
            line(JobID="9", State="COMPLETED", TotalCPU="00:02.000", WorkDir="/data/launch"),
            line(JobID="9.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:02.000"),
        ]
    )
    row = sacct.parse_sacct(early, {"9"})["9"]
    assert (row.total_cpu_s, row.max_rss_bytes, row.work_dir) == (2.0, 1024**3, "/data/launch")


def test_req15_eff_fields(fakebin: Fake) -> None:
    """The new format is asked and parsed from the tool's output, a `|` inside WorkDir kept;
    a line with fewer fields (the format before P1 Task 34) is no row."""
    fakebin.output(OUT + "8812999|FAILED|1:0|None||00:00:01|1G|00:01:00|/w\n")
    found = sacct_jobs(["8812477", "8812345_3", "8812999"], sacct=fakebin.path)
    assert found is not None and set(found) == {"8812477", "8812345_3"}
    assert found["8812345_3"].work_dir == "/data/launch|x"
    assert fakebin.calls()[0]["argv"][-1] == f"--format={sacct.FORMAT}"
    assert sacct.FORMAT.endswith(",WorkDir") and sacct.FORMAT.count(",") == 15


def test_sacct_output_capped(fakebin: Fake) -> None:
    fakebin.output((line(JobID="8812477", State="FAILED", WorkDir="/w") + "\n") * 40000)  # > 1 MiB
    assert sacct_jobs(["8812477"], sacct=fakebin.path) is None


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_req15_limiter(fakebin: Fake) -> None:
    """5,000 failed attempts opened: at most 50 calls, one in flight, 60 s apart."""
    clock = Clock()
    starts: list[float] = []
    in_flight = 0

    def call(ids: list[str]) -> dict[str, SacctRow]:
        nonlocal in_flight
        in_flight += 1
        assert in_flight == 1 and len(ids) <= 100
        starts.append(clock.now)
        in_flight -= 1
        return {}

    limiter = SacctLimiter(call, clock=clock)
    for n in range(5000):
        limiter.request([str(1000000 + n)])  # each opened once
        limiter.request([str(1000000 + n)])  # and again: never asked twice while pending
    while (wait := limiter.wait_s()) is not None:
        clock.now += wait
        assert limiter.run_once() is not None
        assert limiter.run_once() is None  # not due again at once
    assert len(starts) == 50
    assert all(b - a >= 60 for a, b in itertools.pairwise(starts))
    limiter.request(["1;rm", "x"])  # not job IDs: never queued
    assert limiter.wait_s() is None


def test_req15_limiter_one_in_flight() -> None:
    """Two threads that find the limiter due: one call runs, the other returns at once."""
    entered, release = threading.Event(), threading.Event()

    def call(ids: list[str]) -> dict[str, SacctRow]:
        entered.set()
        release.wait(5)
        return {}

    limiter = SacctLimiter(call, interval_s=0)
    limiter.request(["1", "2"])
    first = threading.Thread(target=limiter.run_once)
    first.start()
    assert entered.wait(5)
    limiter.request(["3"])
    assert limiter.run_once() is None  # one call in flight: refused, not queued behind it
    release.set()
    first.join(5)
    assert limiter.run_once() == (["3"], {})


def test_req15_limiter_bounded() -> None:
    limiter = SacctLimiter(lambda ids: {}, max_pending=10)
    limiter.request([str(n) for n in range(1, 50)])
    assert limiter.pending() == 10
