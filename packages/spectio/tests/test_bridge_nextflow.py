"""`nf-spectio` writes the spool: architecture §13.1, §13.3, §13.4, api §14.1 (P1 Task 6).

Real local Nextflow runs of the synthetic pipeline, with the plugin built by `build.sh` and run by
`engine-bridges/nf-spectio/tests/run_local.sh`. Marked `engines`: Nextflow comes from `NEXTFLOW`
or the PATH, Java with it. The default `pytest` run skips them; `-m engines` runs them.
"""

import json
import os
import shutil
import stat
import subprocess
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, insert, select

from spectio.runner.observed import ObservedRun
from spectio.runner.rundir import RUN_ID as RUN_ID_RE
from spectio.runner.spool import read_spool
from spectio_sdk.events import (
    MAX_LINE_BYTES,
    TERMINAL_SPOOL_FILE_NAME,
    SpoolEvent,
    parse_data,
)
from spectio_server.projector.ingest import ingest
from spectio_server.store.db import open_db
from spectio_server.store.schema import (
    attempts,
    environments,
    launches,
    projects,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

pytestmark = pytest.mark.engines

REPO = Path(__file__).resolve().parents[3]
BRIDGE = REPO / "engine-bridges" / "nf-spectio"
RUN_LOCAL = BRIDGE / "tests" / "run_local.sh"
RUN_ID = "run_01K8T6NFSPEC000000000000T6"
NO_EXIT = 2147483647  # Integer.MAX_VALUE: Nextflow's "no exit status yet" (FU-P3-07)
TOOL_STDERR = "synthetic failure: tool exited with code 1"  # what synth.py prints on stderr
NOW = datetime(2026, 10, 30, tzinfo=UTC)


@pytest.fixture(scope="session")
def nextflow() -> str:
    nf = os.environ.get("NEXTFLOW") or shutil.which("nextflow")
    if not nf:
        pytest.fail("Nextflow not found: set NEXTFLOW or put nextflow on the PATH")
    return nf


def run_nf(
    nextflow: str,
    launch_dir: Path,
    *args: str,
    spool_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        **(env or {}),
        "NEXTFLOW": nextflow,
        "SPECTIO_RUN_ID": RUN_ID,
        "SPECTIO_LAUNCH_N": "1",
        "SPECTIO_SPOOL_DIR": str(spool_dir or launch_dir / ".spectio" / "events"),
    }
    launch_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return subprocess.run(
        [str(RUN_LOCAL), str(launch_dir), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def build(nextflow: str, arg: str) -> str:
    """`build.sh OUT_DIR` builds the plugin there; `build.sh --classpath` prints the jar."""
    return subprocess.run(
        [str(BRIDGE / "build.sh"), arg],
        env={**os.environ, "NEXTFLOW": nextflow},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def spool_lines(launch_dir: Path) -> list[str]:
    files = sorted((launch_dir / ".spectio" / "events").glob("nf-spectio-1-*.jsonl"))
    assert files, f"no spool file in {launch_dir}"
    return [line for f in files for line in f.read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="session")
def nf_run(nextflow: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The synthetic `happy` scenario, local executor: one launch directory."""
    launch_dir = tmp_path_factory.mktemp("happy") / "launch"
    done = run_nf(nextflow, launch_dir)
    assert done.returncode == 0, done.stdout + done.stderr
    return launch_dir


@pytest.fixture(scope="session")
def nf_failed_run(nextflow: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The `tool_error_then_fixed_resume` scenario's first run: COMPARE fails, not retried."""
    launch_dir = tmp_path_factory.mktemp("toolerr") / "launch"
    args = ["--fail_mode", "exit", "--fail_process", "COMPARE", "--fail_sample", "treatA"]
    done = run_nf(nextflow, launch_dir, *args)
    assert done.returncode != 0, done.stdout + done.stderr
    return launch_dir


# --- Replay through the real reader and ingest (Tasks 2 to 4) ------------------------------


@pytest.fixture
def writer(tmp_path: Path) -> Iterator[tuple[Engine, Writer]]:
    db_dir = tmp_path / "db"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    w = Writer(engine)
    w.submit(_seed).result()
    yield engine, w
    w.close()
    engine.dispose()


def _seed(conn: Connection) -> None:
    conn.execute(insert(projects).values(id="prj_1", owning_group_id="grp_1", created_at=NOW))
    conn.execute(insert(environments).values(id="env_1", kind="local", created_at=NOW))
    conn.execute(
        insert(workflows).values(
            id="wfl_1", project_id="prj_1", source="local", location="/w", created_at=NOW
        )
    )
    conn.execute(insert(workflow_versions).values(id="wfv_1", workflow_id="wfl_1", created_at=NOW))
    conn.execute(
        insert(runs).values(
            id=RUN_ID,
            project_id="prj_1",
            workflow_version_id="wfv_1",
            environment_id="env_1",
            state="queued",
            created_at=NOW,
        )
    )
    conn.execute(insert(launches).values(id="lch_1", run_id=RUN_ID, n=1, created_at=NOW))


def replay(launch_dir: Path, engine: Engine, w: Writer) -> tuple[Any, Counter[str], int]:
    """Drain the spool as the runner reads it; return the run row, the drops, the events."""
    cursor: dict[str, int] = {}
    drops: Counter[str] = Counter()
    count = 0
    while True:
        batch = read_spool(launch_dir, RUN_ID, 1, cursor, max_lines=200)
        drops += batch.drops
        if not batch.events:
            break
        count += len(batch.events)
        w.submit(partial(ingest, launch_id="lch_1", batch=batch)).result()
        cursor = batch.cursor
    with engine.connect() as conn:
        run = conn.execute(select(runs).where(runs.c.id == RUN_ID)).one()
    return run, drops, count


def stored_exits(engine: Engine) -> set[int | None]:
    with engine.connect() as conn:
        return {r.exit for r in conn.execute(select(attempts.c.exit)).all()}


# --- P1 Task 6, Step 1 ----------------------------------------------------------------------


def test_happy_local_spool_validates(nf_run: Path, writer: tuple[Engine, Writer]) -> None:
    lines = spool_lines(nf_run)
    events = [SpoolEvent.model_validate_json(line) for line in lines]
    for ev in events:
        parse_data(ev)
    assert [ev.seq for ev in events] == list(range(1, len(events) + 1))
    assert len({ev.id for ev in events}) == len(events)
    assert {ev.run for ev in events} == {RUN_ID}
    assert {ev.launch for ev in events} == {1}
    assert {ev.producer for ev in events} == {"nf-spectio/0.0.1"}
    assert all(len(line.encode()) <= MAX_LINE_BYTES for line in lines)
    types = Counter(ev.type for ev in events)
    assert types["nextflow.onFlowCreate"] == 1
    assert types["nextflow.onFlowComplete"] >= 1
    assert types["nextflow.onTaskComplete"] == 65

    engine, w = writer
    run, drops, count = replay(nf_run, engine, w)
    assert drops == Counter()
    assert count == len(events)
    assert run.state == "succeeded"
    assert run.task_counts == {"succeeded": 65}
    assert stored_exits(engine) == {0}


def test_no_script_or_env_keys(nf_run: Path) -> None:
    raw = "\n".join(spool_lines(nf_run))
    assert '"script"' not in raw
    assert '"env"' not in raw
    assert "export SPECTIO_ATTEMPT" not in raw  # the synthetic task script's first line


def test_metrics_enabled(nextflow: str, tmp_path: Path) -> None:
    """`enableMetrics()` is true (P1 Task 28): the trace of a finished task has its measures,
    even with the pipeline's trace, report and timeline off, whose observers enable them too."""
    off = tmp_path / "off.config"
    off.write_text("trace.enabled = false\nreport.enabled = false\ntimeline.enabled = false\n")
    launch_dir = tmp_path / "launch"
    done = run_nf(nextflow, launch_dir, "-c", str(off))
    assert done.returncode == 0, done.stdout + done.stderr
    events = [SpoolEvent.model_validate_json(line) for line in spool_lines(launch_dir)]
    traces = [ev.data["trace"] for ev in events if ev.type == "nextflow.onTaskComplete"]
    assert traces
    for trace in traces:
        assert isinstance(trace, dict)
        for key in ("realtime", "%cpu", "peak_rss"):
            assert trace.get(key) is not None, (key, trace)


def test_task_events_carry_workdir_and_native_id(nf_run: Path) -> None:
    """Every task event sends the work directory and the executor's job ID (P1 Task 28); on
    SLURM the ID is known at submit already (GridTaskHandler), checked on slurm-mini (Task 22)."""
    events = [SpoolEvent.model_validate_json(line) for line in spool_lines(nf_run)]
    hooks = ("onTaskSubmit", "onTaskStart", "onTaskComplete")
    for ev in (e for e in events if e.type.split(".")[1] in hooks):
        trace = ev.data["trace"]
        assert isinstance(trace, dict), ev.type
        assert trace.get("workdir") == ev.data["workDir"], ev.type
        if not ev.type.endswith("onTaskSubmit"):  # the local executor has no PID before start
            assert trace.get("native_id"), ev.type


REQUEST_KEYS = {"cpus", "memory", "time", "disk", "queue", "accelerator", "accelerator_type"}
CLUSTER_OPTIONS = "--qos=planted-cluster-options-7f3a"  # never sent: only that it is set


def flow_create(launch_dir: Path) -> dict[str, Any]:
    (create,) = [
        json.loads(x)["data"] for x in spool_lines(launch_dir) if '"nextflow.onFlowCreate"' in x
    ]
    return create  # type: ignore[no-any-return]


def test_nf_flow_create_cleanup(nextflow: str, nf_run: Path, tmp_path: Path) -> None:
    """P1 Task 33: `onFlowCreate` sends `cleanup` (the session's `config.cleanup`) and
    `clusterOptionsSet`, true when the process config sets `clusterOptions`, here in a
    `withName` selector; the text itself is never sent (SEC-P3T1-11)."""
    default = flow_create(nf_run)
    assert (default["cleanup"], default["clusterOptionsSet"]) == (False, False)
    extra = tmp_path / "extra.config"
    extra.write_text(
        "cleanup = true\n"
        f"process {{ withName: 'MAKE_READS' {{ clusterOptions = '{CLUSTER_OPTIONS}' }} }}\n"
    )
    launch_dir = tmp_path / "launch"
    done = run_nf(nextflow, launch_dir, "-c", str(extra))
    assert done.returncode == 0, done.stdout + done.stderr
    create = flow_create(launch_dir)
    assert (create["cleanup"], create["clusterOptionsSet"]) == (True, True)
    raw = "\n".join(spool_lines(launch_dir))
    assert CLUSTER_OPTIONS not in raw and 'clusterOptions"' not in raw


def test_nf_request_at_submit(nf_run: Path) -> None:
    """P1 Task 33: the pending, submit and start hooks send the request keys of the trace
    record (`TaskHandler.groovy:203-231`, v26.10.4) beside `native_id` and `workdir`; the
    measured keys stay for the final hooks."""
    events = [SpoolEvent.model_validate_json(line) for line in spool_lines(nf_run)]
    hooks = ("onTaskPending", "onTaskSubmit", "onTaskStart")
    early = [e for e in events if e.type.split(".")[1] in hooks]
    assert {e.type.split(".")[1] for e in early} == set(hooks)
    for ev in early:
        trace = ev.data["trace"]
        assert isinstance(trace, dict), ev.type
        assert set(trace) <= REQUEST_KEYS | {"attempt", "native_id", "workdir"}, ev.type
        for key in ("cpus", "memory", "time", "attempt"):
            assert trace.get(key), (ev.type, key, trace)
        assert "queue" in trace, ev.type  # null on the local executor
        for measured in ("%cpu", "peak_rss", "realtime"):
            assert measured not in trace, ev.type


@pytest.mark.parametrize("how", ["mode_0500", "events_is_a_file"])
def test_unwritable_spool_never_fails_run(nextflow: str, tmp_path: Path, how: str) -> None:
    launch_dir = tmp_path / "launch"
    events = launch_dir / ".spectio" / "events"
    events.parent.mkdir(mode=0o700, parents=True)
    if how == "mode_0500":
        if os.geteuid() == 0:
            pytest.skip("root writes into a 0500 directory; events_is_a_file covers root")
        events.mkdir(mode=0o500)
    else:
        events.write_text("")
    done = run_nf(nextflow, launch_dir)
    assert done.returncode == 0, done.stdout + done.stderr
    err = launch_dir / ".spectio" / "bridge.err"
    assert err.is_file() and err.stat().st_size > 0
    assert not list(launch_dir.rglob("nf-spectio-*.jsonl"))


# --- Spike first-look findings and SEC-P3T1-09 ---------------------------------------------


def test_no_exit_yet_is_never_an_exit_code(
    nf_run: Path, nf_failed_run: Path, writer: tuple[Engine, Writer]
) -> None:
    """FU-P3-07: pending, submitted and running tasks carry exit 2147483647 in Nextflow."""
    for launch_dir in (nf_run, nf_failed_run):
        for line in spool_lines(launch_dir):
            data = json.loads(line)["data"]
            assert data.get("exitStatus") != NO_EXIT
            assert (data.get("trace") or {}).get("exit") not in (NO_EXIT, str(NO_EXIT))
    engine, w = writer
    replay(nf_failed_run, engine, w)
    assert NO_EXIT not in stored_exits(engine)


def test_task_stderr_kept_out_of_the_spool(
    nf_failed_run: Path, writer: tuple[Engine, Writer]
) -> None:
    """FU-P3-08, SEC-P3T1-09: `errorMessage` is the failing task's stderr; it is not sent."""
    lines = spool_lines(nf_failed_run)
    assert not any(TOOL_STDERR in line for line in lines)
    assert not any('"errorReport"' in line for line in lines)
    complete = [json.loads(x) for x in lines if '"nextflow.onFlowComplete"' in x]
    assert complete and all(c["data"]["success"] is False for c in complete)
    assert all(c["data"].get("errorMessage") is None for c in complete)

    engine, w = writer
    run, drops, _ = replay(nf_failed_run, engine, w)
    assert drops == Counter()
    assert run.state == "failed"
    assert run.failure["class"] == "tool_error"
    assert TOOL_STDERR not in json.dumps(run.failure)


def test_engine_error_message_is_sent(nextflow: str, tmp_path: Path) -> None:
    """With no failed task, `errorMessage` is Nextflow's own error, and it is kept."""
    launch_dir = tmp_path / "launch"
    done = run_nf(nextflow, launch_dir, "--input", str(tmp_path / "missing.csv"))
    assert done.returncode != 0
    complete = [json.loads(x) for x in spool_lines(launch_dir) if '"nextflow.onFlowComplete"' in x]
    assert complete
    assert "missing.csv" in complete[0]["data"]["errorMessage"]


def test_requires_the_floor(tmp_path: Path, nextflow: str) -> None:
    """architecture §13.4: Nextflow 25.04 is the floor, in the plugin's `requires`."""
    build(nextflow, str(tmp_path))
    manifest = (tmp_path / "nf-spectio-0.0.1" / "classes" / "META-INF" / "MANIFEST.MF").read_text()
    assert "Plugin-Requires: >=25.04.0" in manifest.splitlines()


# --- The writer alone, through Groovy (rotation and the line cap) --------------------------

WRITER_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 4096L)
200.times { w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'r' * 100]) }
w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'x' * 70000])
w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'last'])
"""


def run_writer(
    nextflow: str,
    tmp_path: Path,
    spool: Path,
    script: str = WRITER_SCRIPT,
    ulimit_kb: int = 0,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    jar = build(nextflow, "--classpath")
    build(nextflow, str(tmp_path / "plugin"))
    classes = tmp_path / "plugin" / "nf-spectio-0.0.1" / "classes"
    cmd = ["java", "-cp", f"{jar}:{classes}", "groovy.ui.GroovyMain", "-e", script]
    if ulimit_kb:  # bash's `ulimit -f` counts 1024-byte blocks; the JVM ignores SIGXFSZ (EFBIG)
        cmd = ["bash", "-c", f'ulimit -f {ulimit_kb} && exec "$@"', "bash", *cmd]
    return subprocess.run(
        [*cmd, str(spool), RUN_ID], check=True, capture_output=True, text=True, timeout=timeout
    )


def test_writer_rotates_and_drops_long_lines(nextflow: str, tmp_path: Path) -> None:
    spool = tmp_path / "launch" / ".spectio" / "events"
    run_writer(nextflow, tmp_path, spool)
    for d in (spool, spool.parent):
        assert d.stat().st_mode & 0o777 == 0o700
    files = sorted(spool.iterdir())
    assert len(files) > 5
    assert files[0].name == "nf-spectio-1-0001.jsonl"
    for f in files:
        assert f.stat().st_mode & 0o777 == 0o600
        assert f.stat().st_size <= 4096
    lines = [line for f in files for line in f.read_text(encoding="utf-8").splitlines()]
    events = [SpoolEvent.model_validate_json(line) for line in lines]
    assert [ev.seq for ev in events] == list(range(1, 202))
    assert events[-1].data["runName"] == "last"
    assert "line over" in (spool.parent / "bridge.err").read_text()

    batch = read_spool(spool.parent.parent, RUN_ID, 1, {})
    assert len(batch.events) == 201
    assert batch.drops == Counter()


FULL_DISK_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 1048576L)
2000.times { w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'r' * 100]) }
w.write('nextflow.onFlowComplete', 1793172224454L, [success: true])
"""


def test_writer_does_not_rotate_on_a_failed_write(nextflow: str, tmp_path: Path) -> None:
    """CR-P3T06-01: under `ulimit -f` every write past the limit fails (EFBIG): one file, not
    one new file per event, so the reader never counts the launch's files as too_many_files."""
    spool = tmp_path / "launch" / ".spectio" / "events"
    run_writer(nextflow, tmp_path, spool, FULL_DISK_SCRIPT, ulimit_kb=16)
    files = sorted(spool.iterdir())
    assert 1 <= len(files) <= 2, [f.name for f in files]
    assert files[0].name == "nf-spectio-1-0001.jsonl"
    assert "not written" in (spool.parent / "bridge.err").read_text()

    batch = read_spool(spool.parent.parent, RUN_ID, 1, {})
    assert batch.events
    assert [ev.seq for ev in batch.events] == list(range(1, len(batch.events) + 1))
    assert "too_many_files" not in batch.drops


TORN_THEN_ROTATE_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 17000L)
100.times { w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'r' * 100]) }
w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'b' * 2000])
w.write('nextflow.onFlowBegin', 1793172224454L, [runName: 'last'])
"""


def test_writer_truncates_a_failed_write(nextflow: str, tmp_path: Path) -> None:
    """CR-P3T06-02: a write cut short by EFBIG (`ulimit -f 16`, files rotate at 17000 bytes) is
    truncated away, so a rotation right after it leaves no unterminated line behind."""
    spool = tmp_path / "launch" / ".spectio" / "events"
    run_writer(nextflow, tmp_path, spool, TORN_THEN_ROTATE_SCRIPT, ulimit_kb=16)
    assert "not written" in (spool.parent / "bridge.err").read_text()
    files = sorted(spool.iterdir())
    assert len(files) == 2, [f.name for f in files]
    for f in files:
        assert f.read_bytes().endswith(b"\n"), f.name

    batch = read_spool(spool.parent.parent, RUN_ID, 1, {})
    assert batch.drops == Counter()
    assert [ev.seq for ev in batch.events] == list(range(1, len(batch.events) + 1))
    assert batch.events[-1].data["runName"] == "last"


ERROR_CAP_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 1048576L)
150.times { w.error("e$it") }
w.finish(7L)
"""


def test_error_cap_keeps_the_summary(nextflow: str, tmp_path: Path) -> None:
    """CR-P3T06-04: past MAX_ERROR_LINES, one line counts the rest, and the queue-full summary
    is still written."""
    spool = tmp_path / "launch" / ".spectio" / "events"
    spool.parent.mkdir(mode=0o700, parents=True)
    run_writer(nextflow, tmp_path, spool, ERROR_CAP_SCRIPT)
    lines = (spool.parent / "bridge.err").read_text().splitlines()
    assert len(lines) == 102
    assert lines[99].endswith("nf-spectio: e99")
    assert lines[100].endswith("50 further errors not logged")
    assert lines[101].endswith("7 events dropped: the queue was full")


FIFO_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 1048576L)
new spectio.Spool(w).enqueue('nextflow.onFlowBegin', [runName: 'x' * 70000])
"""

STUCK_WRITER_SCRIPT = """
def w = new spectio.SpoolWriter(java.nio.file.Paths.get(args[0]), args[1], 1L, 1048576L) {
    synchronized void write(String type, long ms, Map data) { Thread.sleep(Long.MAX_VALUE) }
}
new spectio.Spool(w).enqueue('nextflow.onFlowBegin', [:])
"""


def test_bridge_err_fifo_does_not_hang_the_head(nextflow: str, tmp_path: Path) -> None:
    """SEC-P3T06-02: bridge.err is a FIFO; the error goes to stderr and the JVM exits."""
    spool = tmp_path / "launch" / ".spectio" / "events"
    spool.parent.mkdir(mode=0o700, parents=True)
    os.mkfifo(spool.parent / "bridge.err", 0o600)
    done = run_writer(nextflow, tmp_path, spool, FIFO_SCRIPT, timeout=30)
    assert "line over" in done.stderr


def test_stuck_writer_does_not_hang_the_head(nextflow: str, tmp_path: Path) -> None:
    """SEC-P3T06-02: a writer thread that never returns holds its monitor; the shutdown hook
    gives up after its join timeout instead of waiting on the monitor forever."""
    spool = tmp_path / "launch" / ".spectio" / "events"
    done = run_writer(nextflow, tmp_path, spool, STUCK_WRITER_SCRIPT, timeout=30)
    assert "nf-spectio: close: the writer thread is still running" in done.stderr


# --- Runs started from a terminal (P1 Task 25; architecture §13.8, dev-env §15.3 req. 12) ------

POINTER_KEYS = {
    "run_id",
    "launch_dir",
    "engine",
    "engine_version",
    "bridge_version",
    "host",
    "pid",
    "pid_start_time",
    "boot_id",
}
PLANTED = "PLANTED-7f3a"  # in the run's environment and parameters, never in a pointer


def run_nf_terminal(
    nextflow: str, launch_dir: Path, home: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    """A run started by hand: no SPECTIO_* variable, HOME `home` (Nextflow's own home kept),
    the plugin enabled with NXF_PLUGINS_DEFAULT (`run_local.sh --terminal`)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SPECTIO_")}
    nxf_home = os.environ.get("NXF_HOME") or str(Path.home() / ".nextflow")
    env |= {"NEXTFLOW": nextflow, "HOME": str(home), "NXF_HOME": nxf_home, "TEST_TOKEN": PLANTED}
    launch_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return subprocess.run(
        [str(RUN_LOCAL), "--terminal", str(launch_dir), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """A home where Spectio is installed: `~/.spectio/` 0700, no `observed/` yet."""
    home = tmp_path / "home"
    (home / ".spectio").mkdir(mode=0o700, parents=True)
    home.chmod(0o700)
    return home


def pointers(home: Path) -> list[Path]:
    observed = home / ".spectio" / "observed"
    return sorted(observed.iterdir()) if observed.is_dir() else []


def terminal_files(launch_dir: Path) -> list[Path]:
    events = launch_dir / ".spectio" / "events"
    return sorted(events.glob("*.jsonl")) if events.is_dir() else []


def test_terminal_run_writes_pointer(nextflow: str, tmp_home: Path, tmp_path: Path) -> None:
    """No SPECTIO_RUN_ID: a run ID, the spool `<run ID>-nf-spectio-0001.jsonl` in the launch
    directory, read whole by the runner's reader, and `~/.spectio/observed/<run ID>.json`, 0600,
    in `observed/` made 0700."""
    launch_dir = tmp_path / "launch"
    done = run_nf_terminal(nextflow, launch_dir, tmp_home)
    assert done.returncode == 0, done.stdout + done.stderr
    [found] = pointers(tmp_home)
    data = json.loads(found.read_text())
    run_id = data["run_id"]
    assert found.name == f"{run_id}.json" and RUN_ID_RE.fullmatch(run_id)
    assert stat.S_IMODE(found.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_home / ".spectio" / "observed").stat().st_mode) == 0o700
    assert stat.S_IMODE((launch_dir / ".spectio").stat().st_mode) == 0o700
    assert [f.name for f in terminal_files(launch_dir)] == [f"{run_id}-nf-spectio-0001.jsonl"]
    assert TERMINAL_SPOOL_FILE_NAME.fullmatch(f"{run_id}-nf-spectio-0001.jsonl")
    batch = read_spool(launch_dir, run_id, 1, {}, max_lines=100000, observed=True)
    assert batch.drops == Counter() and batch.events
    assert {(ev.run, ev.launch) for ev in batch.events} == {(run_id, 1)}
    assert Counter(ev.type for ev in batch.events)["nextflow.onTaskComplete"] == 65
    assert data["launch_dir"] == str(launch_dir) and data["engine"] == "nextflow"
    assert data["engine_version"] == next(
        ev.data["nextflow"] for ev in batch.events if ev.type == "nextflow.onFlowCreate"
    )
    assert data["bridge_version"] == "0.0.1" and data["pid"] > 1
    ObservedRun.model_validate(data)


def test_pointer_keys_exact(nextflow: str, tmp_home: Path, tmp_path: Path) -> None:
    """Exactly the keys of architecture §13.8: no environment, arguments or parameters."""
    done = run_nf_terminal(nextflow, tmp_path / "launch", tmp_home, "--secret_param", PLANTED)
    assert done.returncode == 0, done.stdout + done.stderr
    [found] = pointers(tmp_home)
    text = found.read_text()
    assert set(json.loads(text)) == POINTER_KEYS
    assert PLANTED not in text


def test_no_spectio_home_run_unaffected(nextflow: str, tmp_path: Path) -> None:
    """No `~/.spectio/`: no pointer, and none made; the spool is written; exit 0."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    launch_dir = tmp_path / "launch"
    done = run_nf_terminal(nextflow, launch_dir, home)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not (home / ".spectio").exists() and terminal_files(launch_dir)


def test_unwritable_home_run_unaffected(nextflow: str, tmp_home: Path, tmp_path: Path) -> None:
    """`observed/` that cannot be written (a file in its place, which even root cannot write
    into; mode 0500): exit 0, the spool written, the reason in `bridge.err`."""
    (tmp_home / ".spectio" / "observed").write_text("")
    launch_dir = tmp_path / "launch"
    done = run_nf_terminal(nextflow, launch_dir, tmp_home)
    assert done.returncode == 0, done.stdout + done.stderr
    assert terminal_files(launch_dir)
    assert "no pointer written" in (launch_dir / ".spectio" / "bridge.err").read_text()
    os.unlink(tmp_home / ".spectio" / "observed")
    (tmp_home / ".spectio" / "observed").mkdir(mode=0o500)
    again = run_nf_terminal(nextflow, tmp_path / "launch2", tmp_home)
    assert again.returncode == 0, again.stdout + again.stderr


def test_driven_run_writes_no_pointer(nextflow: str, tmp_home: Path, tmp_path: Path) -> None:
    """SPECTIO_RUN_ID set (a run Spectio launched): no pointer, the driven file names."""
    launch_dir = tmp_path / "launch"
    nxf_home = os.environ.get("NXF_HOME") or str(Path.home() / ".nextflow")
    done = run_nf(nextflow, launch_dir, env={"HOME": str(tmp_home), "NXF_HOME": nxf_home})
    assert done.returncode == 0, done.stdout + done.stderr
    assert pointers(tmp_home) == []
    assert spool_lines(launch_dir)


@pytest.mark.parametrize("how", ["symlink", "other_owner", "mode_0777", "bridge_err_symlink"])
def test_bridge_refuses_foreign_spectio_dir(
    nextflow: str, tmp_home: Path, tmp_path: Path, how: str
) -> None:
    """`.spectio` a symlink, another user's or 0777, or `bridge.err` a symlink: nothing is
    written outside it, the targets are unchanged, and the run exits 0."""
    launch_dir = tmp_path / "launch"
    launch_dir.mkdir()
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    victim = tmp_path / "victim"
    victim.write_text("unchanged\n")
    if how == "symlink":
        (launch_dir / ".spectio").symlink_to(target)
    elif how == "other_owner":
        if os.geteuid() != 0:
            pytest.skip("needs root to make another user's directory")
        (launch_dir / ".spectio").mkdir(mode=0o700)
        os.chown(launch_dir / ".spectio", 4242, 4242)
    elif how == "mode_0777":
        (launch_dir / ".spectio").mkdir()
        (launch_dir / ".spectio").chmod(0o777)
    else:  # the spool refused (events a file) makes the bridge say why in bridge.err
        (launch_dir / ".spectio").mkdir(mode=0o700)
        (launch_dir / ".spectio" / "events").write_text("")
        (launch_dir / ".spectio" / "bridge.err").symlink_to(victim)
    done = run_nf_terminal(nextflow, launch_dir, tmp_home)
    assert done.returncode == 0, done.stdout + done.stderr
    assert list(target.iterdir()) == [] and victim.read_text() == "unchanged\n"
    assert pointers(tmp_home) == []  # no spool, no pointer: nothing to show
    if how in ("other_owner", "mode_0777"):
        assert list((launch_dir / ".spectio").iterdir()) == []
    assert "the spool directory is refused" in done.stderr


@pytest.mark.parametrize("how", ["mode_0777", "symlink"])
def test_loose_spectio_home_no_pointer(
    nextflow: str, tmp_home: Path, tmp_path: Path, how: str
) -> None:
    """`~/.spectio/` 0777 or a symlink: no pointer anywhere; the run and its spool go on."""
    if how == "mode_0777":
        (tmp_home / ".spectio").chmod(0o777)
        where = tmp_home / ".spectio"
    else:
        where = tmp_path / "real-spectio"
        (tmp_home / ".spectio").rename(where)
        (tmp_home / ".spectio").symlink_to(where)
    launch_dir = tmp_path / "launch"
    done = run_nf_terminal(nextflow, launch_dir, tmp_home)
    assert done.returncode == 0, done.stdout + done.stderr
    assert list(where.iterdir()) == [] and terminal_files(launch_dir)
    assert "no pointer written" in (launch_dir / ".spectio" / "bridge.err").read_text()


# --- Run targets: `nextflow module run` (api §5.10, architecture §13.8; #161) ----------------

MODULE = REPO / "tests" / "pipelines" / "synthetic" / "modules" / "synth_stats"
TARGET_SCRIPT = """
import java.nio.file.Paths
def at = { String cmd, String file -> groovy.json.JsonOutput.toJson(
    spectio.SpectioObserver.moduleTarget(cmd, file ? Paths.get(file) : null, 'abc123')) }
println at('nextflow run main.nf -profile test', null)
def p = args[0] + '/main.nf'
println at('nextflow module run nf-core/fastqc -version 1.2 -params-file p.json', p)
println at('nextflow -c x.config module run nf-core/fastqc', p)
println at('nextflow module run ' + args[1], args[1] + '/main.nf')
println at('nextflow run x --tool module run', null)
"""


def test_module_target_from_the_command_line(nextflow: str, tmp_path: Path) -> None:
    installed = tmp_path / "modules" / "nf-core" / "fastqc"
    installed.mkdir(parents=True)
    checksum = "b" * 64
    (installed / ".module-info").write_text(f"#date\nchecksum={checksum}\nregistryUrl=x\n")
    jar = build(nextflow, "--classpath")
    build(nextflow, str(tmp_path / "plugin"))
    classes = tmp_path / "plugin" / "nf-spectio-0.0.1" / "classes"
    out = subprocess.run(
        ["java", "-cp", f"{jar}:{classes}", "groovy.ui.GroovyMain", "-e", TARGET_SCRIPT,  # noqa: S607
         str(installed), str(MODULE)],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    pipeline, pinned, unpinned, local, param = (json.loads(x) for x in out.splitlines()[-5:])
    assert pipeline is None and param is None
    assert pinned == {
        "kind": "module", "name": "nf-core/fastqc", "version": "1.2", "source": "registry",
        "hash": checksum,
    }  # fmt: skip
    assert unpinned["version"] is None and unpinned["hash"] == checksum
    assert local == {
        "kind": "module", "name": "synth_stats", "version": "1.0.0", "source": "local",
        "path": str(MODULE), "hash": "abc123",
    }  # fmt: skip


def test_local_module_run_reports_its_target(nextflow: str, tmp_path: Path) -> None:
    """The single-module fixture, run alone, driven: `onFlowCreate` carries the target."""
    plugins = tmp_path / "plugins"
    build(nextflow, str(plugins))
    launch = tmp_path / "launch"
    (launch / ".spectio").mkdir(mode=0o700, parents=True)
    (launch / "S1.reads.txt").write_text("r1\nr2\n")
    (launch / "params.json").write_text('{"meta": {"id": "S1"}, "reads": "S1.reads.txt"}')
    env = {
        **os.environ,
        "NXF_PLUGINS_DIR": str(plugins),
        "NXF_ANSI_LOG": "false",
        "SPECTIO_RUN_ID": RUN_ID,
        "SPECTIO_LAUNCH_N": "1",
        "SPECTIO_SPOOL_DIR": str(launch / ".spectio" / "events"),
    }
    argv = [nextflow, "module", "run", str(MODULE), "-plugins", "nf-spectio@0.0.1"]
    proc = subprocess.run(
        [*argv, "-params-file", "params.json"],
        cwd=launch, env=env, capture_output=True, text=True, timeout=600, check=False,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    events = [SpoolEvent.model_validate_json(line) for line in spool_lines(launch)]
    (create,) = [parse_data(e) for e in events if e.type == "nextflow.onFlowCreate"]
    target = getattr(create, "target", None)
    assert target is not None and (target.kind, target.source) == ("module", "local")
    assert (target.name, target.version, target.path) == ("synth_stats", "1.0.0", str(MODULE))
    assert target.hash and "commandLine" not in "".join(spool_lines(launch))
