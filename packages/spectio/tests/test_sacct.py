"""`sacct` for failed jobs and job resources (P1 Task 29; dev-env §15.3 req. 15).

`fakebin` is a fake `sacct` in a directory of its own (`slurm-mini`, P1 Task 22, is not built):
it records its argument list and environment in `calls.jsonl`, and prints `out.txt`. The fields
asked for stay [to be validated] on a real SLURM.
"""

import itertools
import json
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

# What `sacct --parsable2 --noheader --format=JobID,State,…,Timelimit` prints (the shape of the
# T3 probes, tests/fixtures/slurm/slurm-26.05.5/sacct-probes.json; real fields [to be validated]).
OUT = """8812477|OUT_OF_MEMORY|0:125|None|0|00:01:05|2G|00:10:00
8812477.batch|OUT_OF_MEMORY|0:125||2147480K|00:01:05||
8812477.extern|COMPLETED|0:0||1024K|00:01:05||
8812345_3|FAILED|137:0|None||1-02:03:04|4000M|2-00:00:00
8812345_3.batch|FAILED|137:0||1.5G|1-02:03:04||
"""


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
        "--format=JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit",
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
        ),
        "8812345_3": SacctRow(
            state="FAILED",
            exit_code=137,
            reason=None,
            max_rss_bytes=int(1.5 * 1024**3),
            elapsed_s=86400 + 2 * 3600 + 3 * 60 + 4,
            req_mem_bytes=4000 * 1024**2,
            time_limit_s=2 * 86400,
        ),
    }  # 9999: no row, so not in the result
    assert sacct.TIMEOUT_S == 10
    fakebin.delay(30)
    started = time.monotonic()
    assert sacct_jobs(["8812477"], timeout_s=0.5, sacct=fakebin.path) is None
    assert time.monotonic() - started < 5  # killed at the timeout, never waited for


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "1|CANCELLED by 1000|0:15|None|||4Gn|UNLIMITED",
            ("CANCELLED", 0, None, 4 * 1024**3, None),
        ),
        (
            "1|TIMEOUT|0:0|Reason=\x1b[31mx|||1T|Partition_Limit",
            ("TIMEOUT", 0, None, 1024**4, None),
        ),
        (
            "1|FAILED|1:0|JobLaunchFailure|||16Mc|05:30",
            ("FAILED", 1, "JobLaunchFailure", 16 * 1024**2, 330),
        ),
        ("1|weird state!|x|" + "R" * 300 + "|||-1|1-x", (None, None, None, None, None)),
    ],
)
def test_sacct_values_as_data(line: str, expected: tuple[Any, ...]) -> None:
    """Every field is parsed as data: an odd or over-long value is None, never an error."""
    row = sacct.parse_sacct(line + "\n", {"1"})["1"]
    assert (row.state, row.exit_code, row.reason, row.req_mem_bytes, row.time_limit_s) == expected


def test_sacct_output_capped(fakebin: Fake) -> None:
    fakebin.output("8812477|FAILED|1:0|None||00:00:01|1G|00:01:00\n" * 40000)  # > 1 MiB
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
