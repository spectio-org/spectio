"""Runs started from a terminal: the pointer scan, their spool and their head (P1 Task 25;
architecture §13.8, dev-env §15.3 req. 12).

The bridges' side (the pointer they write) is in the bridge tests of Tasks 6 and 7.
"""

import json
import os
import socket
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, select

from spectio.config import Settings
from spectio.runner.local import _boot_id
from spectio.runner.loop import RunnerLoop
from spectio.runner.observed import end_pointer, scan_observed
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio.runner.spool import read_spool
from spectio.runner.types import HeadReport, LaunchRef, LaunchSpec
from spectio_server import serve
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.files.pool import FilePool
from spectio_server.rebuild import rebuild_index
from spectio_server.sink import StoreSink
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import launches, runner_commands, runs, spool_drops
from spectio_server.store.writer import Writer

RUN_A = "run_01K9AAAAAAAAAAAAAAAAAAAAAA"
RUN_B = "run_01K9BBBBBBBBBBBBBBBBBBBBBB"
FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "engine-events"
    / "nextflow-26.10.4_plugin_resume.spool.jsonl"
)
FIXTURE_RUN = "run_01K8T2F1XTVRES000000000000"
OTHER_BOOT = "00000000-0000-4000-8000-000000000000"


# --- Fixtures and helpers ----------------------------------------------------------------------


@pytest.fixture
def tmp_home(home: Path) -> Path:
    """The test's HOME (conftest), with `~/.spectio/observed/` as a bridge makes it."""
    (home / ".spectio" / "observed").mkdir(mode=0o700, parents=True)
    (home / ".spectio").chmod(0o700)
    return home


@pytest.fixture
def runs_root(tmp_home: Path) -> Path:
    root = tmp_home / "spectio-runs"
    root.mkdir(mode=0o700)
    return root


@pytest.fixture
def project(tmp_home: Path) -> Path:
    """A launch directory as a lab's project directory often is: group-writable."""
    launch = tmp_home.parent / "project"
    launch.mkdir()
    launch.chmod(0o770)
    return launch


def pointer(run_id: str, launch_dir: Path | str, **over: Any) -> dict[str, Any]:
    head = Path("/proc/self/stat").read_text().rsplit(") ", 1)[1].split()
    found = {
        "run_id": run_id,
        "launch_dir": str(launch_dir),
        "engine": "nextflow",
        "engine_version": "26.10.4",
        "bridge_version": "0.0.1",
        "host": socket.gethostname(),
        "pid": os.getpid(),  # this test is the head: alive
        "pid_start_time": head[19],
        "boot_id": _boot_id(),
    }
    return {**found, **over}


def write_pointer(home: Path, data: dict[str, Any], name: str | None = None) -> Path:
    path = home / ".spectio" / "observed" / (name or f"{data['run_id']}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, json.dumps(data).encode())
    os.close(fd)
    return path


def write_spool(
    launch_dir: Path, run_id: str, lines: list[str], index: int = 1, producer: str = "nf-spectio"
) -> Path:
    events = launch_dir / ".spectio" / "events"
    events.mkdir(mode=0o700, parents=True, exist_ok=True)
    (launch_dir / ".spectio").chmod(0o700)
    path = events / f"{run_id}-{producer}-{index:04d}.jsonl"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.write(fd, "".join(line + "\n" for line in lines).encode())
    os.close(fd)
    return path


def fixture_lines(run_id: str, last: int | None = None) -> list[str]:
    """The Nextflow resume fixture, ending `succeeded`, as run `run_id`; its first `last` lines
    (no terminal event) when given."""
    lines = FIXTURE.read_text().replace(FIXTURE_RUN, run_id).splitlines()
    return lines if last is None else lines[:last]


def smk_lines(run_id: str, name: str) -> list[str]:
    """A Snakemake 9.27.1 fixture of spike T2 as run `run_id`: it holds no terminal event."""
    found = FIXTURE.with_name(f"snakemake-9.27.1_{name}.spool.jsonl").read_text()
    return found.replace(FIXTURE_RUN, run_id).splitlines()


class Launcher:
    """Records every call: a run from a terminal must never reach one (req. 12, No signal)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def submit(self, spec: LaunchSpec) -> str:
        self.calls.append(("submit", spec.run_id))
        return "1.1"

    def poll(self, ids: list[str]) -> dict[str, HeadReport]:
        if ids:
            self.calls.append(("poll", ids))
        return {}

    def cancel(self, native_id: str, grace_s: int = 60) -> None:
        self.calls.append(("cancel", native_id))

    def adopt(self, launch: LaunchRef) -> HeadReport:
        self.calls.append(("adopt", launch.run_id))
        return HeadReport("running", launch.native_id, None, None, False, None)

    def forget(self, ids: Any) -> None:
        if list(ids):
            self.calls.append(("forget", list(ids)))


@pytest.fixture
def store(tmp_home: Path) -> Iterator[tuple[Engine, Writer]]:
    db_dir = tmp_home.parent / "db"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    writer.submit(lambda c: ensure_tenancy(c, "me", "local", {}, "0.0.1")).result()
    yield engine, writer
    writer.close()
    engine.dispose()


def make_loop(
    store: tuple[Engine, Writer], runs_root: Path, home: Path, end_grace_s: float = 0
) -> tuple[RunnerLoop, Launcher]:
    launcher = Launcher()
    settings = Settings(runs_root=runs_root, executor="local")
    sink = StoreSink(store[1], runs_root)
    return RunnerLoop(sink, launcher, settings, end_grace_s=end_grace_s, home=home), launcher


def run_row(store: tuple[Engine, Writer], run_id: str) -> Any:
    with store[0].connect() as conn:
        return conn.execute(select(runs).where(runs.c.id == run_id)).one_or_none()


def ticks(loop: RunnerLoop, n: int = 3) -> None:
    for _ in range(n):
        loop.tick()


# --- The scan -------------------------------------------------------------------------------


def test_scan_finds_pointer(tmp_home: Path, runs_root: Path, project: Path) -> None:
    """A valid pointer → one run; its spool, read like a driven run's, replays to succeeded."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert [r.run_id for r in scan.runs] == [RUN_A] and not scan.skipped
    assert scan.runs[0].launch_dir == str(project) and scan.runs[0].engine == "nextflow"
    write_spool(project, RUN_A, fixture_lines(RUN_A))
    batch = read_spool(project, RUN_A, 1, {}, observed=True)
    assert len(batch.events) == 109 and batch.events[-1].type == "nextflow.onFlowComplete"


def _symlink(home: Path, observed: Path) -> None:
    target = home / "elsewhere.json"
    target.write_text(json.dumps(pointer(RUN_A, "/p")))
    target.chmod(0o600)
    (observed / f"{RUN_A}.json").symlink_to(target)


def _write(home: Path, data: Any, mode: int = 0o600, name: str = f"{RUN_A}.json") -> None:
    path = home / ".spectio" / "observed" / name
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
    path.chmod(mode)


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("symlink", "symlink"),
        ("other_owner", "foreign_owner"),
        ("group_read", "loose_mode"),
        ("other_read", "loose_mode"),
        ("too_large", "too_large"),
        ("bad_json", "invalid"),
        ("extra_key", "invalid"),
        ("missing_key", "invalid"),
        ("name_differs", "name_mismatch"),
        ("fifo", "not_regular"),
    ],
)
def test_req12_pointer_checks(
    tmp_home: Path, runs_root: Path, project: Path, case: str, reason: str
) -> None:
    """Each pointer gets the file checks of req. 10, any group or other bit refused, and its
    file name must be its run ID: else skipped and counted."""
    observed = tmp_home / ".spectio" / "observed"
    good = pointer(RUN_A, project)
    if case == "symlink":
        _symlink(tmp_home, observed)
    elif case == "other_owner":
        if os.geteuid() != 0:
            pytest.skip("needs root to make another user's file")
        _write(tmp_home, good)
        os.chown(observed / f"{RUN_A}.json", 4242, 4242)
    elif case in ("group_read", "other_read"):
        _write(tmp_home, good, 0o640 if case == "group_read" else 0o604)
    elif case == "too_large":
        _write(tmp_home, {**good, "host": "h" * 5000})
    elif case == "bad_json":
        _write(tmp_home, b"{not json")
    elif case == "extra_key":
        _write(tmp_home, {**good, "env": {"SECRET": "x"}})
    elif case == "missing_key":
        _write(tmp_home, {k: v for k, v in good.items() if k != "boot_id"})
    elif case == "name_differs":
        _write(tmp_home, pointer(RUN_B, project))
    elif case == "fifo":
        os.mkfifo(observed / f"{RUN_A}.json", 0o600)
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and scan.skipped == {reason: 1}
    assert RUN_A in scan.seen  # not read again at the next scan


def test_scan_ignores_temporary_and_other_names(
    tmp_home: Path, runs_root: Path, project: Path
) -> None:
    """A bridge's temporary file (a dot name) and `ended/` are not pointers; a name outside the
    grammar is counted."""
    write_pointer(tmp_home, pointer(RUN_A, project), name=f".{RUN_A}.json.tmp")
    (tmp_home / ".spectio" / "observed" / "ended").mkdir(mode=0o700)
    write_pointer(tmp_home, pointer(RUN_A, project), name="notes.json")
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and scan.skipped == {"bad_name": 1}


@pytest.mark.parametrize("how", ["0777", "symlink", "spectio_0755"])
def test_loose_observed_dir_not_scanned(
    tmp_home: Path, runs_root: Path, project: Path, how: str
) -> None:
    """A loose `observed/` (or `~/.spectio/`) is skipped whole; nothing in it is read."""
    observed = tmp_home / ".spectio" / "observed"
    write_pointer(tmp_home, pointer(RUN_A, project))
    if how == "0777":
        observed.chmod(0o777)
    elif how == "symlink":
        real = tmp_home / "real-observed"
        observed.rename(real)
        observed.symlink_to(real)
    else:
        (tmp_home / ".spectio").chmod(0o755)
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and scan.skipped == {"observed_refused": 1}


def test_no_observed_dir(tmp_home: Path, runs_root: Path) -> None:
    (tmp_home / ".spectio" / "observed").rmdir()
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and not scan.skipped and scan.mtime_ns is None


def test_loose_observed_dir_server_starts(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """The runner warns and goes on: the server starts, and no run is added."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    (tmp_home / ".spectio" / "observed").chmod(0o777)
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    assert run_row(store, RUN_A) is None


@pytest.mark.parametrize(
    "launch_dir",
    ["relative/dir", "/a/../b", "/a//b", "/a/./b", "/a/b/", "RUNS", "RUNS/run_x/launch"],
)
def test_pointer_cannot_alias_driven_run(tmp_home: Path, runs_root: Path, launch_dir: str) -> None:
    """A launch directory that is not absolute and normalised, or lies in the runs root, is
    skipped and counted: the runs root wins."""
    launch_dir = launch_dir.replace("RUNS", str(runs_root))
    write_pointer(tmp_home, pointer(RUN_A, launch_dir))
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and scan.skipped == {"launch_dir": 1}


def test_pointer_cannot_name_a_run_directory(
    tmp_home: Path, runs_root: Path, project: Path
) -> None:
    make_run_dirs(runs_root, RUN_A)
    write_pointer(tmp_home, pointer(RUN_A, project))
    scan = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert scan.runs == [] and scan.skipped == {"run_dir": 1}


def test_pointer_cannot_take_a_driven_runs_row(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """A run ID the index already holds for a driven run (its directory cleaned) stays that
    run's: the pointer is not taken."""
    manifest = RunManifest(
        run_id=RUN_A,
        name="driven",
        workflow=Workflow(location="/pipelines/nf", engine="nextflow"),
        params={},
        profiles=[],
        created_at=datetime.now(UTC),
    )
    now = manifest.created_at
    store[1].submit(
        lambda c: insert_run(
            c, manifest, source="local", runs_root=runs_root, now=now, state="succeeded"
        )
    ).result()
    write_pointer(tmp_home, pointer(RUN_A, project))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.origin is None and row.state == "succeeded" and row.name == "driven"
    assert (tmp_home / ".spectio" / "observed" / f"{RUN_A}.json").exists()  # not moved


def test_group_writable_launch_dir_accepted(tmp_home: Path, runs_root: Path, project: Path) -> None:
    """The launch directory itself is not checked (0770); its `.spectio/` is (0700)."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    assert [r.run_id for r in scan_observed(tmp_home, runs_root, set(), cap=10).runs] == [RUN_A]
    assert len(read_spool(project, RUN_A, 1, {}, observed=True).events) == 3


def test_loose_spectio_dir_of_launch_not_read(project: Path) -> None:
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    (project / ".spectio").chmod(0o770)
    with pytest.raises(PermissionError):
        read_spool(project, RUN_A, 1, {}, observed=True)


def test_spectio_dir_swapped_after_check_not_read(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """`.spectio` replaced by a symlink after a first read: no further read through it."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop, 1)
    swapped = project.parent / "swapped"
    swapped.mkdir(mode=0o700)
    write_spool(swapped, RUN_A, fixture_lines(RUN_A))  # a whole run, ended
    (project / ".spectio").rename(project / "old")
    (project / ".spectio").symlink_to(swapped / ".spectio")
    ticks(loop)
    assert run_row(store, RUN_A).state != "succeeded"
    with pytest.raises(OSError):
        read_spool(project, RUN_A, 1, {}, observed=True)


def test_two_terminal_runs_same_launch_dir_kept_apart(
    tmp_home: Path, runs_root: Path, project: Path
) -> None:
    """Each run reads its own files only; an envelope of the other run in its file is dropped
    and counted."""
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=5))
    write_spool(project, RUN_B, fixture_lines(RUN_B, last=2))
    write_spool(project, RUN_A, fixture_lines(RUN_B, last=1), index=2)  # B's line in A's file
    a = read_spool(project, RUN_A, 1, {}, observed=True)
    b = read_spool(project, RUN_B, 1, {}, observed=True)
    assert len(a.events) == 5 and {e.run for e in a.events} == {RUN_A}
    assert a.drops == {"wrong_run": 1}
    assert len(b.events) == 2 and {e.run for e in b.events} == {RUN_B} and not b.drops
    assert all(name.startswith(RUN_A) for name in a.cursor)


def test_driven_names_not_read_for_a_terminal_run(project: Path) -> None:
    """Only the files named for the pointer's run ID are read: a driven run's name is not."""
    events = project / ".spectio" / "events"
    write_spool(project, RUN_A, [])
    driven = events / "nf-spectio-1-0001.jsonl"
    driven.write_text("\n".join(fixture_lines(RUN_A, last=3)) + "\n")
    driven.chmod(0o600)
    batch = read_spool(project, RUN_A, 1, {}, observed=True)
    assert batch.events == [] and batch.drops == {"bad_name": 1}


# --- The runner loop --------------------------------------------------------------------------


def test_terminal_run_shown_and_ended(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """The scan adds the run with origin `cli-observed`; its spool ends it `succeeded`; the
    pointer then moves to `observed/ended/` (test_ended_pointer_moved)."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    write_spool(project, RUN_A, fixture_lines(RUN_A))
    loop, launcher = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.origin == "cli-observed" and row.state == "succeeded"
    assert row.launch_dir == str(project) and row.results_dir is None
    observed = tmp_home / ".spectio" / "observed"
    assert not (observed / f"{RUN_A}.json").exists()
    assert (observed / "ended" / f"{RUN_A}.json").exists()
    assert (observed / "ended").stat().st_mode & 0o777 == 0o700
    assert launcher.calls == []


test_ended_pointer_moved = test_terminal_run_shown_and_ended


def test_ended_pointer_moved_at_next_boot(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """A run that ended while its pointer was not moved (the server stopped): moved at boot."""
    write_pointer(tmp_home, pointer(RUN_A, project))
    write_spool(project, RUN_A, fixture_lines(RUN_A))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    ended = tmp_home / ".spectio" / "observed" / "ended" / f"{RUN_A}.json"
    ended.rename(tmp_home / ".spectio" / "observed" / f"{RUN_A}.json")
    again, _ = make_loop(store, runs_root, tmp_home)
    ticks(again, 1)
    assert ended.exists()


def test_scan_skips_unchanged_dir(tmp_home: Path, runs_root: Path, project: Path) -> None:
    """`observed/` is listed again only when its mtime changes."""
    first = scan_observed(tmp_home, runs_root, set(), cap=10)
    assert first.mtime_ns is not None
    write_pointer(tmp_home, pointer(RUN_A, project))
    observed = tmp_home / ".spectio" / "observed"
    os.utime(observed, ns=(first.mtime_ns, first.mtime_ns))
    same = scan_observed(tmp_home, runs_root, set(), cap=10, since_ns=first.mtime_ns)
    assert same.runs == [] and same.mtime_ns == first.mtime_ns
    os.utime(observed, ns=(first.mtime_ns + 10**9, first.mtime_ns + 10**9))
    changed = scan_observed(tmp_home, runs_root, set(), cap=10, since_ns=first.mtime_ns)
    assert [r.run_id for r in changed.runs] == [RUN_A]


def test_scan_cap(tmp_home: Path, runs_root: Path, project: Path) -> None:
    """10 000 pointers → at most `cap` read per scan; the rest wait for the next scans, which
    do not need a change of mtime."""
    base = int(time.time() * 1000)
    for i in range(10000):
        n = (base << 80) | i
        crockford = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        run_id = "run_" + "".join(crockford[(n >> (5 * k)) & 31] for k in reversed(range(26)))
        write_pointer(tmp_home, pointer(run_id, project))
    known: set[str] = set()
    first = scan_observed(tmp_home, runs_root, known, cap=100)
    assert len(first.runs) == 100 and first.mtime_ns is None  # cut: scan again
    known |= first.seen
    second = scan_observed(tmp_home, runs_root, known, cap=100, since_ns=first.mtime_ns)
    assert len(second.runs) == 100 and not {r.run_id for r in second.runs} & known


def test_terminal_run_other_boot_id_never_head_lost(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """Another boot ID (or another host): the head is not checked, the run stays running."""
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT, pid=2**22 + 7))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.state == "running" and row.failure is None
    with store[0].connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.run_id == RUN_A)).one()
    assert launch.exited_at is None and launch.host_boot_id == OTHER_BOOT
    assert launch.head_host == socket.gethostname()


def test_terminal_run_same_boot_head_gone_is_head_lost(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """Same boot ID and host: the PID check runs, and a head gone with no terminal event ends
    the run `failed` (`head_lost`), as for a driven run."""
    write_pointer(tmp_home, pointer(RUN_A, project, pid_start_time="1"))  # not this process
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.state == "failed" and row.failure["class"] == "head_lost"


@pytest.mark.parametrize(
    ("name", "state", "class_"),
    [
        ("tool_error_rerun", "succeeded", None),  # last progress 3 of 3, no failed task
        ("checkpoint_flaky_retry", "succeeded", None),  # a failed attempt, retried: no failed task
        ("tool_error", "failed", "engine_fault"),  # a failed task and `error` records
    ],
)
def test_terminal_snakemake_run_ends_from_its_spool(
    tmp_home: Path,
    runs_root: Path,
    project: Path,
    store: tuple[Engine, Writer],
    name: str,
    state: str,
    class_: str | None,
) -> None:
    """Snakemake writes no terminal event, and a terminal run has no exit code: once the PID
    check sees its head gone, the run ends from what its spool shows, never `head_lost`
    (CR-P3T25-01, assumed: inbox #113)."""
    data = pointer(RUN_A, project, engine="snakemake", engine_version="9.27.1", pid_start_time="1")
    write_pointer(tmp_home, data)
    lines = smk_lines(RUN_A, name)
    write_spool(project, RUN_A, lines, producer="snakemake-logger-spectio")
    loop, launcher = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.state == state
    if class_ is None:
        assert row.failure is None
    else:
        assert row.failure["class"] == class_ and "assumed" in row.failure["message"]
    assert launcher.calls == []


def test_terminal_snakemake_run_no_progress_fails(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """No progress record (a dry run, or a head killed early): `failed`, `engine_fault`."""
    data = pointer(RUN_A, project, engine="snakemake", engine_version="9.27.1", pid_start_time="1")
    write_pointer(tmp_home, data)
    write_spool(
        project,
        RUN_A,
        smk_lines(RUN_A, "tool_error_rerun")[:2],
        producer="snakemake-logger-spectio",
    )
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    row = run_row(store, RUN_A)
    assert row.state == "failed" and row.failure["class"] == "engine_fault"
    message = row.failure["message"]
    assert "no progress record" in message and "None" not in message  # CR-P3T25-06


def test_terminal_run_same_boot_head_alive_stays_running(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    write_pointer(tmp_home, pointer(RUN_A, project))  # this test's own process: alive
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    assert run_row(store, RUN_A).state == "running"


def test_runner_never_signals_cli_observed(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """No launcher or tmux call for a `cli-observed` run, boot reconciliation and a `cancel`
    command written behind the API's back included: the command fails."""
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    loop, launcher = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    with store[0].connect() as conn:
        launch_id = conn.execute(select(launches.c.id).where(launches.c.run_id == RUN_A)).scalar()
    now = datetime.now(UTC)
    store[1].submit(
        lambda c: c.execute(
            runner_commands.insert().values(
                id="cmd_1",
                run_id=RUN_A,
                launch_id=launch_id,
                kind="cancel",
                payload={},
                state="pending",
                created_at=now,
            )
        )
    ).result()
    ticks(loop)
    rebuild_index(store[1], runs_root, home=tmp_home)  # boot reconciliation
    again, launcher2 = make_loop(store, runs_root, tmp_home)
    ticks(again)
    assert launcher.calls == [] and launcher2.calls == []
    with store[0].connect() as conn:
        state = conn.execute(select(runner_commands.c.state)).scalar()
    assert state == "failed"
    assert run_row(store, RUN_A).state == "running"


def test_rebuild_keeps_terminal_run_id(
    tmp_home: Path, runs_root: Path, project: Path, tmp_path: Path
) -> None:
    """The index deleted: the rebuild reads the pointers, `ended/` included, so each run keeps
    its ID, and its spool replays."""
    other = tmp_path / "other-project"
    other.mkdir()
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    ended = tmp_home / ".spectio" / "observed" / "ended"
    ended.mkdir(mode=0o700)
    write_pointer(tmp_home, pointer(RUN_B, other), name=f"ended/{RUN_B}.json")
    write_spool(other, RUN_B, fixture_lines(RUN_B))
    db_dir = tmp_path / "fresh-db"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    try:
        writer.submit(lambda c: ensure_tenancy(c, "me", "local", {}, "0.0.1")).result()
        rebuilt = rebuild_index(writer, runs_root, home=tmp_home)
        assert rebuilt.added == 2
        fresh = (engine, writer)
        assert run_row(fresh, RUN_A).origin == "cli-observed"
        assert run_row(fresh, RUN_B).origin == "cli-observed"
        loop, launcher = make_loop(fresh, runs_root, tmp_home)
        ticks(loop)
        assert run_row(fresh, RUN_B).state == "succeeded"
        assert run_row(fresh, RUN_A).state == "running"
        assert launcher.calls == []
    finally:
        writer.close()
        engine.dispose()


def test_server_down_events_wait(
    tmp_home: Path, runs_root: Path, project: Path, store: tuple[Engine, Writer]
) -> None:
    """The run started and ended while no server ran: its pointer and spool are read whole at
    the next start."""
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    write_spool(project, RUN_A, fixture_lines(RUN_A))
    loop, _ = make_loop(store, runs_root, tmp_home)
    ticks(loop)
    assert run_row(store, RUN_A).state == "succeeded"


def test_end_pointer_missing_is_a_no_op(tmp_home: Path) -> None:
    end_pointer(tmp_home, RUN_A)
    assert (tmp_home / ".spectio" / "observed" / "ended").is_dir()


# --- A stuck launch directory (SEC-P3T25-01) --------------------------------------------------


@pytest.fixture
def stuck(project: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:
    """`os.path.realpath` of the launch directory never answers, as on a stale NFS mount or a
    FUSE mount put there by a group member; released at teardown."""
    release = threading.Event()
    real = os.path.realpath

    def realpath(path: Any, *args: Any, **kwargs: Any) -> str:
        if str(path).startswith(str(project)):
            release.wait(30)
        return str(real(path, *args, **kwargs))

    monkeypatch.setattr(os.path, "realpath", realpath)
    yield release
    release.set()


def test_stuck_launch_dir_never_holds_the_writer(
    tmp_home: Path,
    runs_root: Path,
    project: Path,
    store: tuple[Engine, Writer],
    stuck: threading.Event,
) -> None:
    """The writer touches no file of a terminal run: `active_launches` returns, another write
    goes through, and a runner tick skips the stuck run and counts it."""
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    files = FilePool(backlog=0)
    sink = StoreSink(store[1], runs_root)
    loop = RunnerLoop(
        sink,
        Launcher(),
        Settings(runs_root=runs_root, executor="local"),
        home=tmp_home,
        files=files,
        files_timeout_s=0.2,
    )
    started = time.monotonic()
    loop.tick()
    assert time.monotonic() - started < 5
    assert [r.run_id for r in sink.active_launches()] == [RUN_A]
    store[1].submit(lambda c: None).result(timeout=1)
    with store[0].connect() as conn:
        drops = dict(conn.execute(select(spool_drops.c.reason, spool_drops.c.count)).all())
    assert drops.get("spool_stalled", 0) >= 1
    assert run_row(store, RUN_A).state == "queued"


def test_stuck_launch_dir_never_holds_the_boot(
    tmp_home: Path,
    runs_root: Path,
    project: Path,
    stuck: threading.Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The boot's rebuild and first tick finish while the launch directory does not answer."""
    monkeypatch.setattr(serve, "READ_TIMEOUT_S", 0.2)
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    write_spool(project, RUN_A, fixture_lines(RUN_A, last=3))
    db_dir = tmp_home.parent / "db"
    db_dir.mkdir(mode=0o700)
    started = time.monotonic()
    booted = serve.boot(Settings(runs_root=runs_root, executor="local"), db_dir)
    try:
        assert time.monotonic() - started < 10
        assert booted.rebuilt.added == 1
    finally:
        booted.close()


def stuck_loop(
    store: tuple[Engine, Writer], runs_root: Path, home: Path, end_grace_s: float = 0
) -> RunnerLoop:
    """A loop with the server's observed pool: 4 threads, no backlog (serve.boot)."""
    return RunnerLoop(
        StoreSink(store[1], runs_root),
        Launcher(),
        Settings(runs_root=runs_root, executor="local"),
        end_grace_s=end_grace_s,
        home=home,
        files=FilePool(backlog=0),
        files_timeout_s=0.2,
    )


def test_stuck_launch_dir_holds_one_reader(
    tmp_home: Path,
    runs_root: Path,
    project: Path,
    store: tuple[Engine, Writer],
    stuck: threading.Event,
) -> None:
    """A stuck launch directory holds one file reader, not one per tick (CR-P3T25-03): after
    many ticks, a new pointer is still found and another terminal run's spool still read."""
    write_pointer(tmp_home, pointer(RUN_A, project, boot_id=OTHER_BOOT))
    loop = stuck_loop(store, runs_root, tmp_home)
    ticks(loop, 6)
    other = tmp_home.parent / "other"
    other.mkdir()
    write_pointer(tmp_home, pointer(RUN_B, other, boot_id=OTHER_BOOT))
    write_spool(other, RUN_B, fixture_lines(RUN_B))
    ticks(loop, 3)
    assert run_row(store, RUN_B).state == "succeeded"
    assert run_row(store, RUN_A).state == "queued"


def test_stuck_launch_dir_end_grace_waits(
    tmp_home: Path,
    runs_root: Path,
    project: Path,
    store: tuple[Engine, Writer],
    stuck: threading.Event,
) -> None:
    """A terminal run whose head is gone while its spool does not answer is not ended: its end
    grace starts again at each stalled read, as its last events are still unread."""
    write_pointer(tmp_home, pointer(RUN_A, project, pid_start_time="1"))  # this boot: gone
    loop = stuck_loop(store, runs_root, tmp_home, end_grace_s=0.3)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        loop.tick()
        time.sleep(0.05)
    assert run_row(store, RUN_A).state not in ("failed", "succeeded")
