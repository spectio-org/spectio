"""The Snakemake logger plugin writes the spool (P1 Task 7; architecture §13.1, §13.4; api §14.1).

Snakemake 9.27.1 runs with the plugin on PYTHONPATH, never installed; every line it writes must
pass `spectio_sdk.events` (the reader's models) unchanged. The fields P1 Tasks 28 and 29 read
(`log`, `threads`, `resources`, `benchmark`, `job_error.msg` and `aux.external_jobid`,
`snakemake.slurm_submitted`) each have a test; the SLURM ones run on the executor plugin's
documented text, since no cluster runs here (P1 Task 22 checks it live).
"""

import errno
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from snakemake_interface_logger_plugins.base import LogHandlerBase
from snakemake_interface_logger_plugins.common import LogEvent
from snakemake_interface_logger_plugins.settings import LogHandlerSettingsBase
from snakemake_interface_logger_plugins.tests import MockOutputSettings, TestLogHandlerBase

import snakemake_logger_plugin_spectio as plugin
from spectio_sdk.events import (
    DATA_MODELS,
    MAX_LINE_BYTES,
    MAX_MESSAGE_CHARS,
    SPOOL_FILE_NAME,
    SnakemakeJobError,
    SnakemakeJobInfo,
    SnakemakeSlurmSubmitted,
    SpoolEvent,
    parse_data,
)

from .conftest import FILES, PLANTED, REPO, ROOT, RUN_ID, SmkRun, snakemake, synthetic_happy

FIXTURE = (
    REPO
    / "tests"
    / "fixtures"
    / "engine-events"
    / "logger-plugin"
    / "snakemake-9.27.1_files.spool.jsonl"
)
FIXTURE_RUN = "run_01K8T2F1XTVRES000000000000"  # the run of every engine-events fixture
# The SLURM executor plugin 2.8.0's submission text (`__init__.py:1224-1227`), as it formats it.
SUBMITTED = (
    "Job 7 has been submitted with SLURM jobid 8812477 "
    "(log: /scratch/launch/.snakemake/slurm_logs/rule_align/S1/8812477.log)."
)


def check_spool(run: SmkRun) -> list[Any]:
    """Every file named as §14.1 says, 0600 in a 0700 directory; every line under the cap and
    valid; `seq` from 1 with no gap. Returns the parsed data models."""
    assert stat.S_IMODE(os.lstat(run.spool).st_mode) == 0o700
    assert run.files(), run.proc.stderr[-2000:]
    parsed = []
    for f in run.files():
        assert SPOOL_FILE_NAME.fullmatch(f.name), f.name
        assert stat.S_IMODE(os.lstat(f).st_mode) == 0o600
        for line in f.read_bytes().splitlines():
            assert len(line) <= MAX_LINE_BYTES
            event = SpoolEvent.model_validate_json(line)
            assert (event.run, event.launch) == (RUN_ID, 1)
            assert event.producer == plugin.PRODUCER
            parsed.append((event, parse_data(event)))
    assert [e.seq for e, _ in parsed] == list(range(1, len(parsed) + 1))
    assert all(e.type in DATA_MODELS for e, _ in parsed)
    text = "".join(f.read_text() for f in run.files())
    assert PLANTED not in text  # nothing from the environment
    return [data for _, data in parsed]


def handler(monkeypatch: pytest.MonkeyPatch, spool: Path) -> plugin.LogHandler:
    monkeypatch.setenv("SPECTIO_RUN_ID", RUN_ID)
    monkeypatch.setenv("SPECTIO_LAUNCH_N", "1")
    monkeypatch.setenv("SPECTIO_SPOOL_DIR", str(spool))
    return plugin.LogHandler(MockOutputSettings(), plugin.LogHandlerSettings())


def record(event: LogEvent | None, msg: str = "", **extra: Any) -> logging.LogRecord:
    rec = logging.LogRecord("snakemake", logging.INFO, "x.py", 1, msg, None, None)
    if event is not None:
        rec.event = event
    for key, value in extra.items():
        setattr(rec, key, value)
    return rec


def spool_lines(spool: Path) -> list[dict[str, Any]]:
    return [
        json.loads(x) for f in sorted(spool.glob("*.jsonl")) for x in f.read_text().splitlines()
    ]


# --- The interface ---------------------------------------------------------------------------


class TestInterfaceSuite(TestLogHandlerBase):
    """`snakemake_interface_logger_plugins.tests` (2.1.0) against the plugin, driven."""

    __test__ = True

    @pytest.fixture(autouse=True)
    def _driven(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
        (tmp_path / ".spectio").mkdir(mode=0o700)
        self.spool = tmp_path / ".spectio" / "events"
        monkeypatch.setenv("SPECTIO_RUN_ID", RUN_ID)
        monkeypatch.setenv("SPECTIO_LAUNCH_N", "1")
        monkeypatch.setenv("SPECTIO_SPOOL_DIR", str(self.spool))
        yield
        for line in spool_lines(self.spool):  # what the suite's records wrote is valid
            parse_data(SpoolEvent.model_validate(line))

    def get_log_handler_cls(self) -> type[LogHandlerBase]:
        return plugin.LogHandler

    def get_log_handler_settings(self) -> LogHandlerSettingsBase:
        return plugin.LogHandlerSettings()


def test_interface_suite() -> None:
    """The plan's name for the suite above; also the contract T2 found: the settings class name
    the registry reads, no file Snakemake would ask `baseFilename` of, and every record."""
    from snakemake_interface_logger_plugins.registry import LoggerPluginRegistry

    found = LoggerPluginRegistry().get_plugin("spectio")  # by module name, on sys.path
    assert found.log_handler is plugin.LogHandler
    assert found.settings_cls is plugin.LogHandlerSettings
    one = plugin.LogHandler(MockOutputSettings(), plugin.LogHandlerSettings())
    assert (one.writes_to_file, one.writes_to_stream, one.has_filter) == (False, False, True)
    assert one.needs_rulegraph and one.has_formatter


LOWEST_1X = """
import json, logging, sys
sys.path.insert(0, sys.argv[1])
from importlib.metadata import version
from snakemake_interface_logger_plugins.common import LogEvent
from snakemake_interface_logger_plugins.registry import LoggerPluginRegistry
assert version("snakemake-interface-logger-plugins") == "1.1.0"
plugin = LoggerPluginRegistry().get_plugin("spectio")
h = plugin.log_handler(object(), plugin.settings_cls())
assert isinstance(h, logging.Handler) and h.filters == []
for event in LogEvent:  # through Handler.handle, as the QueueListener calls it
    rec = logging.LogRecord("snakemake", logging.INFO, "x", 1, "m", None, None)
    rec.event = event
    rec.jobid = 1
    rec.rule_name = "r"
    h.handle(rec)
h.handle(logging.LogRecord("snakemake", logging.INFO, "x", 1, "no event", None, None))
h.close()
"""


def test_interface_lowest_1x(tmp_path: Path) -> None:
    """The lowest interface Snakemake 9.27.1 allows (>=1.1.0,<3) has no `tests` module (it came
    with 2.0.0), and its base class does not call `Handler.__init__`: the plugin loads through
    the registry, handles one record of every LogEvent and writes valid lines there too."""
    uv = shutil.which("uv")
    assert uv is not None, "uv is needed to build the 1.1.0 environment"
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SPECTIO_", "VIRTUAL_ENV"))}
    env |= {"SPECTIO_RUN_ID": RUN_ID, "SPECTIO_LAUNCH_N": "1", "SPECTIO_SPOOL_DIR": str(spool)}
    cmd = [uv, "run", "--no-project", "--isolated", "--python", sys.executable]
    cmd += ["--with", "snakemake-interface-logger-plugins==1.1.0", "python", "-I", "-c"]
    proc = subprocess.run(
        [*cmd, LOWEST_1X, str(ROOT)], env=env, capture_output=True, text=True, timeout=300
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    lines = spool_lines(spool)
    assert len(lines) == len(LogEvent) + 1
    for line in lines:
        parse_data(SpoolEvent.model_validate(line))


# --- Real runs -------------------------------------------------------------------------------


def test_happy_local_spool_validates(smk_run: SmkRun) -> None:
    assert smk_run.proc.returncode == 0, smk_run.proc.stderr[-3000:]
    parsed = check_spool(smk_run)
    types = [type(d).__name__ for d in parsed]
    for name in ("SnakemakeWorkflowStarted", "SnakemakeRunInfo", "SnakemakeRulegraph"):
        assert types.count(name) == 1, name
    infos = [d for d in parsed if isinstance(d, SnakemakeJobInfo)]
    finished = smk_run.of("snakemake.job_finished")
    assert infos and len(infos) == len(finished)
    assert {d.jobid for d in infos} == {d["job_id"] for d in finished}
    (started,) = smk_run.of("snakemake.workflow_started")
    assert started["snakemake_version"] == "9.27.1"
    assert started["snakefile_main"].endswith("synthetic/snakemake/workflow/Snakefile")
    progress = smk_run.of("snakemake.progress")
    assert progress[-1]["done"] == progress[-1]["total"]
    text = "".join(f.read_text() for f in smk_run.files())
    for never in ("SPECTIO_ATTEMPT", '"shellcmd":', '"cmd":', '"rule_msg":', "slurm_extra"):
        assert never not in text  # the jobs' commands and the denied keys are not sent


def test_logger_added_not_replacing(smk_run: SmkRun) -> None:
    """Snakemake's own log file and stderr are still written, in full."""
    (log,) = (smk_run.launch / ".snakemake" / "log").glob("*.snakemake.log")
    text = log.read_text()
    assert "Finished jobid" in text and "steps (100%) done" in text
    assert "steps (100%) done" in smk_run.proc.stderr


def test_unwritable_spool_never_fails_run(tmp_path: Path) -> None:
    """SPECTIO_SPOOL_DIR under a regular file (unwritable even for root): the run succeeds,
    nothing is written, and the plugin says why on stderr, once."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    run = synthetic_happy(tmp_path / "launch", spool=blocker / "events")
    assert run.proc.returncode == 0, run.proc.stderr[-3000:]
    assert (run.launch / "results").is_dir()
    assert run.proc.stderr.count("the spool directory is refused") == 1


def test_unwritable_spool_symlink_not_followed(tmp_path: Path) -> None:
    """`events` a symlink to another directory: refused, nothing written at the target; the
    reason goes to `.spectio/bridge.err`."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    (tmp_path / ".spectio" / "events").symlink_to(target)
    run = snakemake(
        tmp_path / "launch", FILES, "--cores", "1", spool=tmp_path / ".spectio" / "events"
    )
    assert run.proc.returncode == 0, run.proc.stderr[-3000:]
    assert list(target.iterdir()) == []
    err = (tmp_path / ".spectio" / "bridge.err").read_text()
    assert err.count("the spool directory is refused") == 1
    assert stat.S_IMODE(os.lstat(tmp_path / ".spectio" / "bridge.err").st_mode) == 0o600


def test_full_spool_cut_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ENOSPC mid-line: the file is cut back to its last full line, no exception reaches the
    caller, the same file takes the next line once the disk has room, and `seq` has no gap."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    h.handle(record(LogEvent.PROGRESS, done=1, total=3))
    real = os.write

    def full(fd: int, data: Any) -> int:
        if h.spool is None or fd != h.spool.fd:  # bridge.err
            return real(fd, data)
        real(fd, bytes(data[:10]))  # a partial line, then the disk is full
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(plugin.os, "write", full)
    h.handle(record(LogEvent.PROGRESS, done=2, total=3))
    monkeypatch.setattr(plugin.os, "write", real)
    h.handle(record(LogEvent.PROGRESS, done=3, total=3))
    h.close()
    assert len(list(spool.glob("*.jsonl"))) == 1  # the same file throughout
    lines = spool_lines(spool)
    assert [(e["seq"], e["data"]["done"]) for e in lines] == [(1, 1), (2, 3)]
    assert "No space left on device" in (tmp_path / ".spectio" / "bridge.err").read_text()


def test_other_writers_file_never_appended(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    spool.mkdir(mode=0o700)
    theirs = spool / "snakemake-logger-spectio-1-0001.jsonl"
    theirs.write_text("")
    (spool / "snakemake-logger-spectio-1-0002.jsonl").symlink_to(tmp_path / "target")
    h = handler(monkeypatch, spool)
    h.handle(record(None, "hello"))
    h.close()
    assert theirs.read_text() == "" and not (tmp_path / "target").exists()
    assert (spool / "snakemake-logger-spectio-1-0003.jsonl").read_text().count("\n") == 1


def test_failed_create_keeps_the_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CR-P3T7-01: a create that fails (EACCES, EDQUOT) does not use up an index; only
    an existing file does (as nf-spectio)."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    real = os.open
    failures = [2]

    def refused(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if str(path).endswith(".jsonl") and failures[0]:
            failures[0] -= 1
            raise PermissionError(errno.EACCES, "Permission denied")
        return real(path, flags, *args, **kwargs)

    monkeypatch.setattr(plugin.os, "open", refused)
    for n in range(3):
        h.handle(record(LogEvent.PROGRESS, done=n, total=3))
    h.close()
    assert [f.name for f in spool.glob("*.jsonl")] == ["snakemake-logger-spectio-1-0001.jsonl"]
    assert [e["data"]["done"] for e in spool_lines(spool)] == [2]


def test_rotates_before_the_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    monkeypatch.setattr(plugin, "ROTATE_BYTES", 600)
    h = handler(monkeypatch, spool)
    for n in range(6):
        h.handle(record(LogEvent.PROGRESS, done=n, total=6))
    h.close()
    files = sorted(spool.glob("*.jsonl"))
    assert len(files) > 1 and all(f.stat().st_size <= 600 for f in files)
    assert [e["seq"] for e in spool_lines(spool)] == list(range(1, 7))


@pytest.mark.parametrize(
    ("env", "said"),
    [
        ({}, ""),  # not driven: silent
        ({"SPECTIO_RUN_ID": "run_x", "SPECTIO_LAUNCH_N": "1"}, "SPECTIO_RUN_ID"),
        ({"SPECTIO_RUN_ID": RUN_ID, "SPECTIO_LAUNCH_N": "01"}, "SPECTIO_LAUNCH_N"),
        ({"SPECTIO_RUN_ID": RUN_ID, "SPECTIO_LAUNCH_N": "1", "SPECTIO_SPOOL_DIR": "rel"}, "abs"),
    ],
)
def test_silent_unless_driven(
    env: dict[str, str], said: str, monkeypatch: pytest.MonkeyPatch, capsys: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("SPECTIO_RUN_ID", "SPECTIO_LAUNCH_N", "SPECTIO_SPOOL_DIR"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    h = plugin.LogHandler(MockOutputSettings(), plugin.LogHandlerSettings())
    h.handle(record(None, "hello"))
    assert h.spool is None and list(tmp_path.iterdir()) == []
    err = capsys.readouterr().err
    assert (said in err) if said else err == ""


# --- The fields P1 Tasks 28 and 29 read --------------------------------------------------------


def test_job_info_threads_resources_benchmark(files_run: SmkRun) -> None:
    """Task 29: `threads`, `resources` (a Namedlist, sent as a map, without `slurm_extra`) and
    `benchmark`, from a real run."""
    check_spool(files_run)
    (info,) = [d for d in files_run.of("snakemake.job_info") if d["rule_name"] == "measured"]
    assert info["threads"] == 2
    assert info["benchmark"] == "benchmarks/measured.tsv"
    resources = info["resources"]
    assert (resources["mem_mb"], resources["runtime"], resources["_cores"]) == (100, 5, 2)
    assert "slurm_extra" not in resources
    assert SnakemakeJobInfo.model_validate(info).resources == resources


def test_job_info_log(files_run: SmkRun) -> None:
    """Task 28: the rule's logs on `job_info`, relative to the launch directory."""
    infos = {d["rule_name"]: d for d in files_run.of("snakemake.job_info")}
    assert infos["measured"]["log"] == ["logs/measured.log"]
    assert infos["broken"]["log"] == ["logs/broken.log"]


def test_job_error_log(files_run: SmkRun) -> None:
    """Task 28: `log` on `job_error`; a local job has no executor text (`msg`) nor `aux`."""
    assert files_run.proc.returncode == 1
    (error,) = files_run.of("snakemake.job_error")
    assert (error["rule_name"], error["log"]) == ("broken", ["logs/broken.log"])
    assert "msg" not in error and "aux" not in error


def test_job_error_msg_and_external_jobid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tasks 28 and 29: on a remote executor, the error text is the record's `rule_msg`
    (`remote.py:259-267` appends the cluster hint) and `aux` holds `external_jobid`. `msg` is
    cut at MAX_MESSAGE_CHARS, as the server cuts it; nothing else of `aux` is sent."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    text = "SLURM-job '8812477' failed, SLURM status is: 'OUT_OF_MEMORY'. " + "x" * 9000
    aux = {"external_jobid": "8812477", "slurm_logfile": "/x", "token": PLANTED}
    h.handle(
        record(
            LogEvent.JOB_ERROR,
            "Error in rule align, jobid: 7",
            jobid=7,
            rule_name="align",
            rule_msg=text,
            aux=aux,
            log=["a.log", "/l/8812477.log"],
            input=[],
            output=["o"],
            shellcmd="export T=1; run",
        )
    )
    h.close()
    (line,) = spool_lines(spool)
    assert line["data"]["aux"] == {"external_jobid": "8812477"}
    assert line["data"]["msg"] == text[:MAX_MESSAGE_CHARS]
    data = parse_data(SpoolEvent.model_validate(line))
    assert isinstance(data, SnakemakeJobError) and data.aux is not None
    assert (data.aux.external_jobid, data.log) == ("8812477", ["a.log", "/l/8812477.log"])
    assert "shellcmd" not in line["data"] and PLANTED not in json.dumps(line)


def test_job_info_reason_params_detail_cut(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CR-P3T7-02: the "Params have changed" detail quotes param values (SEC-P3T1-08): the
    reason is cut after the marker at the source, as the server cuts it."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    reason = f"Params have changed since last execution: params.token: old -> {PLANTED}"
    h.handle(record(LogEvent.JOB_INFO, jobid=3, rule_name="align", reason=reason))
    h.close()
    (line,) = spool_lines(spool)
    assert line["data"]["reason"] == "Params have changed since last execution"
    assert PLANTED not in json.dumps(line)


def test_slurm_submitted_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tasks 7 and 28: the submission text becomes `snakemake.slurm_submitted` after its own
    `snakemake.log`; its text is not sent. The format is snakemake-executor-plugin-slurm 2.8.0's
    (`__init__.py:1224-1227`) [to be validated] live on `slurm-mini` (P1 Task 22)."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    h.handle(record(None, SUBMITTED))
    h.handle(record(None, "Job 7 has been submitted with SLURM jobid 1 (log: x"))  # not closed
    h.handle(record(None, SUBMITTED + " trailing"))  # not the whole text
    h.close()
    lines = spool_lines(spool)
    assert [e["type"] for e in lines] == ["snakemake.log", "snakemake.slurm_submitted"] + [
        "snakemake.log"
    ] * 2
    data = parse_data(SpoolEvent.model_validate(lines[1]))
    assert data == SnakemakeSlurmSubmitted(
        jobid=7,
        external_jobid="8812477",
        log="/scratch/launch/.snakemake/slurm_logs/rule_align/S1/8812477.log",
    )
    assert "has been submitted" not in json.dumps(lines)


# --- Bounds ----------------------------------------------------------------------------------


def test_bounded_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Strings, lists and maps are cut; a gather job too large for one line keeps its jobid
    without its file lists; "highest" priority and a NUL are never sent as such."""
    (tmp_path / ".spectio").mkdir(mode=0o700)
    spool = tmp_path / ".spectio" / "events"
    h = handler(monkeypatch, spool)
    many = [f"results/{'d' * 200}/{n}.txt" for n in range(2000)]
    h.handle(
        record(
            LogEvent.JOB_INFO,
            jobid=1,
            rule_name="gather",
            input=many,
            output=["o"],
            log=[],
            wildcards={"s": "a\x00b"},
            priority="highest",
            threads=1,
            reason="r" * 10000,
            resources={"k": {"d": {"e": list(range(9999))}}},
        )
    )
    h.handle(record(LogEvent.RULEGRAPH, rulegraph={"nodes": [{"rule": "r" * 4000}] * 2000}))
    h.close()
    (info,) = spool_lines(spool)  # the rulegraph line does not fit: dropped, said
    data = parse_data(SpoolEvent.model_validate(info))
    assert isinstance(data, SnakemakeJobInfo)
    assert (data.jobid, data.input, data.output, data.priority) == (1, [], [], None)
    assert data.wildcards == {"s": "a�b"} and len(data.reason or "") == 4096
    assert "line over" in (tmp_path / ".spectio" / "bridge.err").read_text()


def test_emit_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Bad:
        def __str__(self) -> str:
            raise RuntimeError("boom")

    (tmp_path / ".spectio").mkdir(mode=0o700)
    h = handler(monkeypatch, tmp_path / ".spectio" / "events")
    h.emit(record(LogEvent.JOB_INFO, jobid=1, rule_name=Bad()))
    h.close()
    assert "boom" in (tmp_path / ".spectio" / "bridge.err").read_text()


# --- The recorded fixture the server's tests replay -----------------------------------------


def normalise(run: SmkRun) -> str:
    """The run's spool as the committed fixture holds it: the fixture run, `<launch>` and
    `<repo>` for the paths, and no host or user name."""
    out = []
    for line in run.lines():
        if line["type"] == "snakemake.workflow_started":
            line["data"] |= {"host": "<host>", "user": "<user>"}
        out.append(json.dumps(line, ensure_ascii=False))
    text = "\n".join(out) + "\n"
    return (
        text.replace(str(run.launch), "<launch>")
        .replace(str(REPO), "<repo>")
        .replace(RUN_ID, FIXTURE_RUN)
    )


def shape(text: str) -> list[tuple[str, list[str]]]:
    lines = [json.loads(x) for x in text.splitlines()]
    return [(e["type"], sorted(e["data"])) for e in lines if e["type"] != "snakemake.log"]


def test_recorded_fixture_current(files_run: SmkRun) -> None:
    """`tests/fixtures/engine-events/logger-plugin/snakemake-9.27.1_files.spool.jsonl` is this run's
    spool (the server's Task 28 and 29 tests replay it): same events, same keys. Rewrite it
    with SPECTIO_RECORD=1."""
    text = normalise(files_run)
    if os.environ.get("SPECTIO_RECORD") == "1":
        FIXTURE.write_text(text)
    assert shape(FIXTURE.read_text()) == shape(text)
