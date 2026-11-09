"""`sacct` for failed jobs and job resources (P1 Task 29; dev-env §15.3 req. 15).

`fakebin` is a fake `sacct` in a directory of its own (`slurm-mini`, P1 Task 22, is not built):
it records its argument list and environment in `calls.jsonl`, and prints `out.txt`. The fields
asked for stay [to be validated] on a real SLURM.
"""

import itertools
import json
import os
import re
import sys
import threading
import time
from collections import Counter
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
delimiter = [a for a in sys.argv if a.startswith("--delimiter=")][0].split("=", 1)[1]
sys.stdout.write(open(os.path.join(here, "out.txt")).read().replace("{{D}}", delimiter))
"""

# What `sacct --parsable2 --noheader --delimiter=<D> --format=JobID,State,…,WorkDir,Submit`
# prints (the shape of the T3 probes, tests/fixtures/slurm/slurm-26.05.5/sacct-probes.json, with
# the efficiency fields of P1 Task 34 and Submit of FU-P3-53; real fields, WorkDir among them,
# and a 16-character delimiter, [to be validated] on slurm-mini). The fake prints `out.txt` with
# `D` replaced by the delimiter of its call; `parse_sacct` is called with `D` itself.
FIELDS = sacct.FORMAT.split(",")
D = "{D}"
SUBMIT = "2026-11-08T09:00:00"  # UTC (`TZ=UTC` in the call's environment)
LAUNCH = 1_794_128_400.0  # 2026-11-08T09:00:00Z: a run launched at the job's submit time


def line(**values: str) -> str:
    """One `--parsable2` line in FORMAT's order; a field not given is empty, except a job
    line's Submit (a step line, `<id>.<step>`, has none here)."""
    unknown = set(values) - set(FIELDS)
    assert not unknown, unknown
    if "." not in values.get("JobID", ""):
        values = {"Submit": SUBMIT, **values}
    return D.join(values.get(f, "") for f in FIELDS)


def want(*pairs: tuple[str, str], since: float = LAUNCH) -> dict[str, dict[str, float]]:
    """`parse_sacct`'s `wanted`: job ID → {WorkDir: the run's launch time}."""
    found: dict[str, dict[str, float]] = {}
    for job, where in pairs:
        found.setdefault(job, {})[where] = since
    return found


def parse(text: str, *pairs: tuple[str, str], since: float = LAUNCH) -> dict[str, Any]:
    return sacct.parse_sacct(text, want(*pairs, since=since), D)


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


ASKED = want(("8812477", "/data/work/ab/cd"), ("8812345_3", "/data/launch|x"), ("9999", "/w"))


def test_req15_argv_and_id_check(fakebin: Fake) -> None:
    found = sacct_jobs(ASKED, sacct=fakebin.path)
    (call,) = fakebin.calls()
    delimiter = call["argv"][3]
    assert re.fullmatch(r"--delimiter=[A-Za-z0-9]{16}", delimiter)  # SEC-PRE-11
    assert call["argv"] == [
        str(fakebin.path),
        "--parsable2",
        "--noheader",
        delimiter,
        "-j",
        "8812477,8812345_3,9999",
        f"--user={os.geteuid()}",  # the server user's own jobs only
        "-S",  # CON-SLURM-POLL-03: the run's launch less the submit skew, never Epoch 0
        "2026-11-08T08:55:00",
        "-E",
        "now",
        "--format=JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,TotalCPU,NCPUS,"
        "NNodes,Partition,Account,QOS,AllocTRES,WorkDir,Submit",
    ]
    assert "--duplicates" not in call["argv"] and "-D" not in call["argv"]  # CON-PRE-15
    assert found is not None and set(found) == {"8812477", "8812345_3"}
    for bad in (["1;rm"], ["1234567890123"], ["1_123456789"], ["8812477", "-j"], [""], [" 1"]):
        with pytest.raises(sacct.Refused):
            sacct_jobs({job: {"/w": LAUNCH} for job in bad}, sacct=fakebin.path)
    with pytest.raises(sacct.Refused):  # 100 IDs per call
        sacct_jobs({str(n): {"/w": LAUNCH} for n in range(101)}, sacct=fakebin.path)
    assert len(fakebin.calls()) == 1  # every refusal before any call


def test_sacct_window_from_earliest_launch(fakebin: Fake) -> None:
    """CON-SLURM-POLL-03: `-S` is the earliest launch of the batch less SUBMIT_SKEW_S."""
    sacct_jobs(
        {"8812477": {"/a": LAUNCH + 3600, "/b": LAUNCH}, "9999": {"/w": LAUNCH + 60}},
        sacct=fakebin.path,
    )
    argv = fakebin.calls()[0]["argv"]
    start = argv.index("-S")
    assert argv[start : start + 4] == ["-S", "2026-11-08T08:55:00", "-E", "now"]


def test_sacct_delimiter_random_per_call(fakebin: Fake) -> None:
    """SEC-PRE-11: a new 16-character delimiter for each call, so a WorkDir cannot carry one
    known in advance."""
    for _ in range(3):
        assert sacct_jobs(ASKED, sacct=fakebin.path) is not None
    delimiters = [call["argv"][3] for call in fakebin.calls()]
    assert len(set(delimiters)) == 3


def test_req15_tool_checked(fakebin: Fake, tmp_path: Path) -> None:
    """The stored path must be absolute, a regular file, not writable by others."""
    fakebin.path.chmod(0o775)
    for path in (fakebin.path, Path("sacct"), tmp_path):
        with pytest.raises(sacct.Refused):
            sacct_jobs(want(("1", "/w")), sacct=path)
    assert fakebin.calls() == []


def test_req15_env_explicit(fakebin: Fake, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLURM_CONF", "/nonexistent/evil.conf")
    monkeypatch.setenv("LD_PRELOAD", "/nonexistent/evil.so")
    monkeypatch.setenv("SACCT_FORMAT", "JobID")
    monkeypatch.setenv("TZ", "Asia/Kolkata")
    sacct_jobs(want(("8812477", "/data/work/ab/cd")), sacct=fakebin.path)
    env = fakebin.calls()[0]["env"]
    env.pop("LC_CTYPE", None)  # Python itself may set it at start (PEP 538), not the caller
    # Submit in UTC, whatever the server's or the node's zone ([to be validated] on slurm-mini)
    assert env == {"PATH": str(fakebin.dir), "SLURM_TIME_FORMAT": "standard", "TZ": "UTC"}


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
    found = sacct_jobs(ASKED, sacct=fakebin.path)
    assert found == {
        "8812477": {
            "/data/work/ab/cd": SacctRow(
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
            )
        },
        "8812345_3": {
            "/data/launch|x": SacctRow(
                state="FAILED",
                exit_code=137,
                reason=None,
                max_rss_bytes=int(1.5 * 1024**3),
                elapsed_s=86400 + 2 * 3600 + 3 * 60 + 4,
                req_mem_bytes=4000 * 1024**2,
                time_limit_s=2 * 86400,
                work_dir="/data/launch|x",  # a `|` is data: the delimiter is the call's own
                ncpus=1,
                nnodes=1,
            )
        },
    }  # 9999: no row, so not in the result
    assert sacct.TIMEOUT_S == 30  # CON-SLURM-POLL-02
    fakebin.delay(30)
    started = time.monotonic()
    assert sacct_jobs(ASKED, timeout_s=0.5, sacct=fakebin.path) is None
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
            },
            (None, None, None, None, None),
        ),
    ],
)
def test_sacct_values_as_data(values: dict[str, str], expected: tuple[Any, ...]) -> None:
    """Every field is parsed as data: an odd or over-long value is None, never an error."""
    row = parse(line(JobID="1", WorkDir="/w", **values) + "\n", ("1", "/w"))["1"]["/w"]
    assert (row.state, row.exit_code, row.reason, row.req_mem_bytes, row.time_limit_s) == expected
    assert row.work_dir == "/w"
    if expected[0] is None:
        assert (row.total_cpu_s, row.ncpus, row.partition, row.qos, row.alloc_tres) == (None,) * 5


@pytest.mark.parametrize("work_dir", ["w", "w\x1b", "", "/w\x00x"])
def test_sacct_bad_workdir_no_row(work_dir: str) -> None:
    """A WorkDir that is not absolute or holds a control character is no candidate (and so
    never `normpath`ed into one, SEC-PRE-13)."""
    assert parse(line(JobID="1", State="FAILED", WorkDir=work_dir), ("1", "/w")) == {}


def test_eff_sacct() -> None:
    """P1 Task 34 (schedulers §3.6): TotalCPU summed over the job's steps (batch, extern and each
    srun step), never with the allocation row's, which already holds them; MaxRSS the largest
    of any step; ReqMem per CPU times NCPUS; the allocation's partition, account, QOS and TRES.
    Step rows have an empty WorkDir (sacct/print.c, CON-PRE-15): they join the job line just
    before them."""
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
    row = parse(text, ("77", "/data/launch"))["77"]["/data/launch"]
    assert row.total_cpu_s == 100.5
    assert row.max_rss_bytes == 3 * 1024**3
    assert row.req_mem_bytes == 4 * 1000 * 1024**2
    assert (row.ncpus, row.nnodes, row.elapsed_s, row.time_limit_s) == (4, 1, 65, 3600)
    assert (row.partition, row.account, row.qos) == ("gpu", "lab", "high")
    assert row.alloc_tres == "cpu=4,gres/gpu=1,mem=4000M,node=1"
    alone = parse(line(JobID="5", TotalCPU="2-01:00:00", WorkDir="/w"), ("5", "/w"))["5"]["/w"]
    assert alone.total_cpu_s == 49 * 3600  # no step rows: the allocation row's own


def test_eff_sacct_steps_join_their_own_job() -> None:
    """SEC-PRE-12, CON-PRE-15: a step line counts only for the job line printed just before it,
    with the same base ID, and only when that job line is a candidate. A step after another
    job's line (a forged `<id>.batch`), after a dropped line, or before any job line adds no
    CPU and no memory."""
    text = "\n".join(
        [
            line(JobID="9.batch", State="COMPLETED", MaxRSS="9G", TotalCPU="10:00.000"),
            line(JobID="9", State="COMPLETED", TotalCPU="00:02.000", WorkDir="/data/launch"),
            line(JobID="9.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:02.000"),
            line(JobID="8", State="COMPLETED", TotalCPU="00:01.000", WorkDir="/other"),
            line(JobID="9.batch", State="COMPLETED", MaxRSS="8G", TotalCPU="20:00.000"),
            line(JobID="9", State="RUNNING", WorkDir="/elsewhere"),  # dropped: not a candidate
            line(JobID="9.0", State="COMPLETED", MaxRSS="7G", TotalCPU="30:00.000"),
        ]
    )
    row = parse(text, ("9", "/data/launch"), ("8", "/other"))["9"]["/data/launch"]
    assert (row.total_cpu_s, row.max_rss_bytes, row.work_dir) == (2.0, 1024**3, "/data/launch")


def test_eff_sacct_line_of_other_workdir_ignored() -> None:
    """SEC-P3T34-04 answered: a job line with another WorkDir (a reused ID, a forged line) is
    dropped, and no longer removes the job's own row."""
    text = "\n".join(
        [
            line(JobID="123", State="COMPLETED", TotalCPU="00:01.000", WorkDir="/old"),
            line(JobID="123.batch", State="COMPLETED", MaxRSS="9G", TotalCPU="10:00.000"),
            line(JobID="123", State="COMPLETED", TotalCPU="00:02.000", WorkDir="/data/launch"),
            line(JobID="123.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:02.000"),
        ]
    )
    dropped: Counter[str] = Counter()
    found = sacct.parse_sacct(text, want(("123", "/data/launch")), D, dropped)
    row = found["123"]["/data/launch"]
    assert (row.total_cpu_s, row.max_rss_bytes) == (2.0, 1024**3)
    assert dropped == {"123": 1}  # counted, for the run's one log line (CON-PRE-14)


def test_eff_sacct_resizing_record_skipped() -> None:
    """CON-PRE-15: a resized job prints its older RESIZING records too (they come first). The
    final record is the row; its CPU and memory are None, since the steps under the RESIZING
    record are not summed (B1 of the security pre-review)."""
    text = "\n".join(
        [
            line(JobID="42", State="RESIZING", TotalCPU="05:00.000", WorkDir="/w"),
            line(JobID="42.batch", State="RESIZING", MaxRSS="4G", TotalCPU="05:00.000"),
            line(JobID="42", State="COMPLETED", ExitCode="0:0", NCPUS="2", WorkDir="/w"),
            line(JobID="42.batch", State="COMPLETED", MaxRSS="1G", TotalCPU="00:30.000"),
        ]
    )
    row = parse(text, ("42", "/w"))["42"]["/w"]
    assert (row.state, row.exit_code, row.ncpus) == ("COMPLETED", 0, 2)
    assert (row.total_cpu_s, row.max_rss_bytes) == (None, None)
    only = line(JobID="42", State="RESIZING", WorkDir="/w")
    assert parse(only, ("42", "/w")) == {}  # only a RESIZING record: not the job's end


def test_eff_sacct_two_final_lines_same_dir_no_row() -> None:
    """Two non-RESIZING job lines for one ID in the expected directory: which is the job is not
    known (order between instances is not verified), so no row."""
    text = "\n".join(
        [
            line(JobID="7", State="FAILED", WorkDir="/w"),
            line(JobID="7", State="COMPLETED", WorkDir="/w/"),  # the same directory, normalised
        ]
    )
    assert parse(text, ("7", "/w")) == {}


def test_eff_sacct_no_matching_line_no_row() -> None:
    """No candidate: no entry (the caller asks again, up to MAX_TRIES); an empty expected set
    never means any directory (SEC-PRE-15)."""
    text = line(JobID="7", State="FAILED", WorkDir="/w")
    assert parse(text, ("7", "/v")) == {}
    assert sacct.parse_sacct(text, {"7": {}}, D) == {}


def test_eff_sacct_one_id_two_dirs() -> None:
    """One job ID asked for two directories (two runs, one a local PID read as an ID): each
    directory gets its own line's row."""
    text = "\n".join(
        [
            line(JobID="7", State="FAILED", WorkDir="/a"),
            line(JobID="7.batch", State="FAILED", TotalCPU="00:01.000"),
            line(JobID="7", State="COMPLETED", WorkDir="/b"),
            line(JobID="7.batch", State="COMPLETED", TotalCPU="00:03.000"),
        ]
    )
    found = parse(text, ("7", "/a"), ("7", "/b"))["7"]
    assert (found["/a"].state, found["/a"].total_cpu_s) == ("FAILED", 1.0)
    assert (found["/b"].state, found["/b"].total_cpu_s) == ("COMPLETED", 3.0)


def test_eff_sacct_workdir_normalised() -> None:
    """WorkDir is `normpath`ed, never resolved (SEC-PRE-13): `/w/./x/` is `/w/x`, the row keeps
    sacct's text, and `..` is folded as text (no file system is asked)."""
    text = line(JobID="7", State="FAILED", WorkDir="/w/./x/")
    row = parse(text, ("7", "/w/x"))["7"]["/w/x"]
    assert row.work_dir == "/w/./x/"
    assert set(parse(line(JobID="7", State="FAILED", WorkDir="/w/y/../x"), ("7", "/w/x"))) == {"7"}


def test_eff_sacct_submit_before_launch_dropped() -> None:
    """SEC-PRE-14: a job line submitted before the run's launch (less SUBMIT_SKEW_S) is another
    job with that ID; a Submit that does not parse is no candidate either."""
    text = line(JobID="7", State="FAILED", WorkDir="/w")  # submitted at LAUNCH
    assert parse(text, ("7", "/w"), since=LAUNCH + sacct.SUBMIT_SKEW_S + 1) == {}
    assert set(parse(text, ("7", "/w"), since=LAUNCH + sacct.SUBMIT_SKEW_S)) == {"7"}
    for submit in ("Unknown", "", "2026-11-08 09:00:00", "2026-13-40T09:00:00"):
        assert parse(line(JobID="7", Submit=submit, WorkDir="/w"), ("7", "/w")) == {}


def test_sacct_line_split_wrongly_dropped() -> None:
    """SEC-PRE-11, SEC-P3FU53-02: a line with more or fewer fields than FORMAT is dropped. WorkDir
    is not the last field, so a newline in it splits its line into two fragments, neither with
    FORMAT's fields: no truncated WorkDir binds, and the forger, who does not know the call's
    delimiter, cannot forge a line. A `|` there is data."""
    forged = "|".join(["7", "COMPLETED", "0:0"] + [""] * 13 + ["/w"])
    assert parse(line(JobID="7", State="FAILED", WorkDir="/w\nzzz"), ("7", "/w")) == {}
    text = "\n".join(
        [
            line(JobID="7", State="FAILED", WorkDir="/x\n" + forged),  # two fragments, both dropped
            line(JobID="8", State="FAILED", WorkDir="/w" + D + "x"),  # one field too many
            line(JobID="9", State="FAILED", WorkDir="/w|y"),
        ]
    )
    found = parse(text, ("7", "/w"), ("8", "/w"), ("9", "/w|y"))
    assert set(found) == {"9"}


def test_req15_eff_fields(fakebin: Fake) -> None:
    """The new format is asked and parsed from the tool's output; a line with fewer fields (the
    format before FU-P3-53) is no row."""
    fakebin.output(OUT + D.join(["8812999", "FAILED", "1:0", "None", "", "00:00:01", "/w"]) + "\n")
    found = sacct_jobs({**ASKED, "8812999": {"/w": LAUNCH}}, sacct=fakebin.path)
    assert found is not None and set(found) == {"8812477", "8812345_3"}
    assert fakebin.calls()[0]["argv"][-1] == f"--format={sacct.FORMAT}"
    assert sacct.FORMAT.endswith(",WorkDir,Submit") and sacct.FORMAT.count(",") == 16


def test_sacct_output_capped(fakebin: Fake) -> None:
    fakebin.output((line(JobID="8812477", State="FAILED", WorkDir="/w") + "\n") * 40000)  # > 1 MiB
    with pytest.raises(sacct.TooMuch):  # final for one ID; the limiter splits a batch
        sacct_jobs(want(("8812477", "/w")), sacct=fakebin.path)


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

    def call(ids: list[str]) -> sacct.Found:
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

    def call(ids: list[str]) -> sacct.Found:
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


def test_sacct_limiter_backs_off() -> None:
    """CON-SLURM-POLL-02: a failed call doubles the interval from 60 s up to 600 s, a success
    resets it, and a call slower than SLOW_S counts as back-pressure."""
    clock = Clock()
    answers: list[sacct.Found | None] = [None, None, None, None, None, {}, {}, {}]
    slow = [False] * 6 + [True, False]
    starts: list[float] = []

    def call(ids: list[str]) -> sacct.Found | None:
        starts.append(clock.now)
        if slow[len(starts) - 1]:
            clock.now += 6
        return answers[len(starts) - 1]

    limiter = SacctLimiter(call, clock=clock)
    limiter.request(["1"])
    for _ in answers:
        wait = limiter.wait_s()
        assert wait is not None
        clock.now += wait
        done = limiter.run_once()
        assert done is not None
        limiter.request(done[0])  # the caller puts a failed call's IDs back
    gaps = [b - a for a, b in itertools.pairwise(starts)]
    assert gaps == [120, 240, 480, 600, 600, 60, 120]


def test_sacct_limiter_follow_up() -> None:
    """A follow-up is queued once its delay has passed, not before."""
    clock = Clock()
    limiter = SacctLimiter(lambda ids: {}, clock=clock)
    limiter.later(["7"], 600)
    assert limiter.wait_s() == 600 and limiter.pending() == 0
    assert limiter.run_once() is None
    clock.now += 600
    assert limiter.run_once() == (["7"], {})
    assert limiter.wait_s() is None


def test_sacct_limiter_request_takes_follow_up() -> None:
    """CR-P3FU106A-03: a job asked again before its follow-up is due rides along with that
    call; the follow-up never fires on its own later."""
    clock = Clock()
    limiter = SacctLimiter(lambda ids: {}, clock=clock)
    limiter.later(["7"], 600)
    limiter.request(["7"])
    assert limiter.run_once() == (["7"], {})
    assert limiter.wait_s() is None


def test_sacct_limiter_classifies_failures() -> None:
    """SEC-P3FU106A-01: a refused call is final; an answer over the cap splits its batch at
    once and is final for one ID; a call that fails twice is split, so one ID that fails
    every call cannot hold its batch-mates."""

    def call(ids: list[str]) -> sacct.Found | None:
        if "9" in ids:
            raise sacct.Refused("not a tool")
        if "5" in ids:
            raise sacct.TooMuch("over the cap")
        return None if "3" in ids else {}

    limiter = SacctLimiter(call, interval_s=0)
    limiter.request(["9"])
    assert limiter.run_once() == (["9"], sacct.FINAL)
    limiter.request(["5", "6"])
    assert limiter.run_once() == (["5", "6"], None)
    limiter.request(["5", "6"])  # the caller puts them back: halved at once
    assert limiter.run_once() == (["5"], sacct.FINAL)
    assert limiter.run_once() == (["6"], {})
    answered = []
    limiter.request(["1", "2", "3", "4"])
    for _ in range(6):
        done = limiter.run_once()
        assert done is not None
        if done[1] is None:
            limiter.request(done[0])
        else:
            answered += done[0]
    assert sorted(answered) == ["1", "2", "4"] and limiter.pending() == 1


def test_sacct_limiter_bad_id_isolated_in_busy_queue() -> None:
    """SEC-P3FU106A-02: new IDs arriving before every call do not undo the split: once the bad
    ID has failed twice, no call that holds it is larger than its recorded size."""
    limiter = SacctLimiter(lambda ids: None if "9" in ids else {}, interval_s=0)
    limiter.request(["9"])
    fresh = itertools.count(1000)
    failures = 0
    for _ in range(60):
        limiter.request(str(next(fresh)) for _ in range(30))
        size = limiter._size.get("9", sacct.BATCH)
        done = limiter.run_once()
        assert done is not None
        if done[1] is None:
            failures += 1
            if failures > 2:
                assert len(done[0]) <= size
            limiter.request(done[0])  # the caller puts a failed call's IDs back
    assert failures > 2 and limiter._size["9"] == 1
