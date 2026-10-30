"""`spectio serve`: boot, refusals and the index rebuilt from the run directories (P1 Task 11,
Assumptions 9, 10 and 21; dev-env §15.3 "Server restart")."""

import json
import logging
import os
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, insert, select, update
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs, write_run_manifest
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.rebuild import rebuild_index
from spectio_server.serve import Booted, ServeError, boot, start_text, started
from spectio_server.sink import StoreSink
from spectio_server.store.db import DB_FILE, open_db
from spectio_server.store.schema import events, launches, run_inputs, runner_commands, runs
from spectio_server.store.writer import Writer

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "engine-events"
FIXTURE_RUN = "run_01K8T2F1XTVRES000000000000"  # the run of every converted T2 fixture
NF = ("nextflow-26.10.4_plugin_flaky.spool.jsonl", "nf-spectio-1-0001.jsonl")
SMK = (
    "snakemake-9.27.1_checkpoint_flaky_retry.spool.jsonl",
    "snakemake-logger-spectio-1-0001.jsonl",
)
DEAD_PID = 999999999  # above any pid_max: never a live process


def run_id(n: int) -> str:
    return f"run_01K8T2F1XT{n:016d}"


def make_run(
    root: Path,
    rid: str,
    engine: str = "nextflow",
    spool: tuple[str, str] | None = None,
    **extra: Any,
) -> Path:
    """A run directory as the runner leaves it: the manifest, and the spool of a T2 fixture
    rewritten to this run."""
    paths = make_run_dirs(root, rid)
    manifest = RunManifest(
        run_id=rid,
        name=f"name of {rid}",
        workflow=Workflow(location=f"/pipelines/happy-{engine}", engine=engine),
        params={"greeting": "hi"},
        profiles=[],
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    write_run_manifest(paths.run_dir, manifest)
    if extra:  # keys the manifest does not allow
        path = paths.run_dir / ".spectio" / "run.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), **extra}))
    if spool is not None:
        fixture, name = spool
        target = paths.launch_dir / ".spectio" / "events" / name
        target.write_text((FIXTURES / fixture).read_text().replace(FIXTURE_RUN, rid))
        target.chmod(0o600)
    return paths.launch_dir


def head_files(
    launch_dir: Path, pid: int = DEAD_PID, start: str | None = None, code: int | None = 0
) -> str:
    """head.pid (and head.exit when `code` is set) as the head script writes them; the native
    ID of that head (a dead one by default)."""
    start = start or str(int(launch_dir.parent.name[-6:]))  # one native ID per run
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    spectio = launch_dir / ".spectio"
    (spectio / "head.pid").write_text(f"{pid} {pid} {start} {boot_id} {socket.gethostname()}\n")
    (spectio / "head.pid").chmod(0o600)
    if code is not None:
        (spectio / "head.exit").write_text(f"{code} 1761800000\n")
        (spectio / "head.exit").chmod(0o600)
    return f"{pid}.{start}"


def write_private(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o600)


@pytest.fixture
def live_head() -> Iterator[subprocess.Popen[bytes]]:
    proc = subprocess.Popen(["sleep", "60"], start_new_session=True)  # noqa: S607
    yield proc
    proc.kill()
    proc.wait()


def start_of(pid: int) -> str:
    return Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[19]


def settle(booted: Booted, ticks: int = 3) -> None:
    """Tick the runner with no spool grace, as a minute after boot would."""
    assert booted.loop is not None
    booted.loop.end_grace_s = 0
    for _ in range(ticks):
        booted.loop.tick()


def rows(booted: Booted) -> dict[str, Any]:
    with booted.engine.connect() as conn:
        return {r.id: r for r in conn.execute(select(runs))}


@pytest.fixture
def replayed_runs(settings: Settings, live_head: subprocess.Popen[bytes]) -> dict[str, str]:
    """Two finished runs, one live head, one cancelled run and one failed launch."""
    root = settings.runs_root
    names = {
        "nextflow": run_id(1),
        "snakemake": run_id(2),
        "live": run_id(3),
        "cancelled": run_id(4),
        "failed": run_id(5),
    }
    head_files(make_run(root, names["nextflow"], spool=NF))
    head_files(make_run(root, names["snakemake"], "snakemake", spool=SMK))
    live = make_run(root, names["live"])
    head_files(live, live_head.pid, start_of(live_head.pid), code=None)
    cancelled = make_run(root, names["cancelled"])
    head_files(cancelled, code=130)
    write_private(cancelled / ".spectio" / "cancel", '{"time": "2026-10-30T00:00:00+00:00"}')
    failed = make_run(root, names["failed"])
    record = {"class": "engine_missing", "message": "nextflow not found", "time": "x"}
    write_private(failed / ".spectio" / "launch-failed.json", json.dumps(record))
    return names


def _check_rebuilt(booted: Booted, names: dict[str, str], live_native: str) -> None:
    found = rows(booted)
    assert set(found) == set(names.values())
    nf, smk = found[names["nextflow"]], found[names["snakemake"]]
    assert (nf.state, nf.task_counts) == ("succeeded", {"succeeded": 65})  # the T2 golden
    assert (smk.state, smk.task_counts) == ("succeeded", {"succeeded": 67}), smk.failure
    assert found[names["live"]].state == "running"
    assert found[names["cancelled"]].state == "cancelled"
    failed = found[names["failed"]]
    assert failed.state == "failed"
    assert failed.failure["class"] == "engine_missing"
    assert failed.failure["message"] == "nextflow not found"
    with booted.engine.connect() as conn:
        dupes = conn.execute(
            select(events.c.run_id, events.c.event_id)
            .group_by(events.c.run_id, events.c.event_id)
            .having(func.count() > 1)
        ).all()
        assert dupes == []
        native = conn.execute(
            select(launches.c.head_native_id).where(launches.c.run_id == names["live"])
        ).scalar()
        assert native == live_native
        params = conn.execute(
            select(run_inputs.c.content).where(
                run_inputs.c.run_id == names["nextflow"], run_inputs.c.kind == "params"
            )
        ).scalar()
        assert params == {"greeting": "hi"}


def test_rebuild_from_run_dirs(
    settings: Settings, replayed_runs: dict[str, str], live_head: subprocess.Popen[bytes]
) -> None:
    db_dir = settings.db_dir
    assert db_dir is not None
    live_native = f"{live_head.pid}.{start_of(live_head.pid)}"
    booted = boot(settings, db_dir)
    try:
        assert booted.rebuilt.added == 5 and booted.new
        settle(booted)
        _check_rebuilt(booted, replayed_runs, live_native)
    finally:
        booted.close()
    for name in os.listdir(db_dir):  # delete the database: the next boot rebuilds it
        if name.startswith(DB_FILE):
            (db_dir / name).unlink()
    booted = boot(settings, db_dir)
    try:
        assert booted.rebuilt.added == 5 and booted.new
        settle(booted)
        _check_rebuilt(booted, replayed_runs, live_native)
    finally:
        booted.close()
    assert live_head.poll() is None  # adopted, never signalled


def test_boot_reconciles_missing_runs(settings: Settings) -> None:
    db_dir = settings.db_dir
    assert db_dir is not None
    root = settings.runs_root
    head_files(make_run(root, run_id(1), spool=NF))
    booted = boot(settings, db_dir)
    settle(booted)
    booted.close()
    # A run directory absent from the existing index (the boot that would have added it was
    # interrupted, or it was made while no server ran): added at the next boot.
    head_files(make_run(root, run_id(2), spool=NF))
    booted = boot(settings, db_dir)
    try:
        assert (booted.new, booted.rebuilt.added) == (False, 1)
        settle(booted)
        found = rows(booted)
        assert set(found) == {run_id(1), run_id(2)}
        assert all(r.state == "succeeded" for r in found.values())
    finally:
        booted.close()


def _writer(settings: Settings) -> Iterator[Writer]:
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    writer = Writer(engine)
    writer.submit(
        lambda conn: ensure_tenancy(conn, "me", "local", {"runs_root": "/r"}, "0.0.1")
    ).result()
    yield writer
    writer.close()
    engine.dispose()


@pytest.fixture
def writer(settings: Settings) -> Iterator[Writer]:
    yield from _writer(settings)


NEEDS_ROOT = pytest.mark.skipif(os.geteuid() != 0, reason="chown to another uid needs root")


def test_rebuild_skips_symlinked_or_loose_dirs(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    make_run(root, run_id(1))  # the one good run
    make_run(root, run_id(9))
    (root / run_id(2)).symlink_to(root / run_id(9))  # a symlink to a good run
    make_run(root, run_id(4))
    (root / run_id(4)).chmod(0o755)  # loose
    (root / "not-a-run").mkdir(mode=0o700)  # a bad name
    found = rebuild_index(writer, root)
    assert (found.added, found.skipped, found.deferred) == (2, 3, 0)  # runs 1 and 9
    assert set(writer.submit(lambda c: list(c.execute(select(runs.c.id)).scalars())).result()) == {
        run_id(1),
        run_id(9),
    }


@NEEDS_ROOT
def test_rebuild_skips_foreign_dir(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    make_run(root, run_id(1))
    make_run(root, run_id(3))
    os.chown(root / run_id(3), 12345, 12345)  # another user's
    found = rebuild_index(writer, root)
    assert (found.added, found.skipped) == (1, 1)


def test_rebuild_run_id_must_match_dir(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    make_run(root, run_id(1))
    (root / run_id(1)).rename(root / run_id(2))  # run.json still says run 1
    found = rebuild_index(writer, root)
    assert (found.added, found.skipped) == (0, 1)


def test_rebuild_ignores_manifest_session_and_paths(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    make_run(root, run_id(1), launch_dir="/elsewhere", session="spectio-other")  # refused
    make_run(root, run_id(2))
    found = rebuild_index(writer, root)
    assert (found.added, found.skipped) == (1, 1)
    row = writer.submit(
        lambda c: c.execute(select(runs.c.launch_dir, runs.c.work_dir)).one()
    ).result()
    assert (row.launch_dir, row.work_dir) == (
        str(root / run_id(2) / "launch"),
        str(root / run_id(2) / "work"),
    )


def test_rebuild_caps(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    for n in (1, 2, 3):
        make_run(root, run_id(n))
    first = rebuild_index(writer, root, max_runs=2)
    assert (first.added, first.deferred) == (2, 1)
    second = rebuild_index(writer, root, max_runs=2)  # the next boot: the rest
    assert (second.added, second.deferred) == (1, 0)
    make_run(root, run_id(4))
    make_run(root, run_id(5))
    by_bytes = rebuild_index(writer, root, max_bytes=1)  # one manifest, then the cap
    assert (by_bytes.added, by_bytes.deferred) == (1, 1)


def test_runs_root_loose_refused(settings: Settings) -> None:
    settings.runs_root.chmod(0o770)
    with pytest.raises(ServeError, match="runs root"), started(settings):
        pass


@NEEDS_ROOT
def test_runs_root_foreign_refused(settings: Settings) -> None:
    os.chown(settings.runs_root, 12345, 12345)
    with pytest.raises(ServeError, match="runs root"), started(settings):
        pass


def test_second_serve_refused(settings: Settings) -> None:
    with started(settings):
        with pytest.raises(ServeError, match=f"pid {os.getpid()}"), started(settings):
            pass
    with started(settings):  # released at stop
        pass


def test_state_file_names_other_node(settings: Settings) -> None:
    state = settings.data_dir / "server.json"
    write_private(state, json.dumps({"host": "login2", "port": 8080, "pid": 1}))
    with pytest.raises(ServeError, match="login2"), started(settings):
        pass
    assert json.loads(state.read_text())["host"] == "login2"  # left as it was
    with started(settings, force=True):
        record = json.loads(state.read_text())
        assert record["host"] == socket.gethostname()
        assert record["port"] == settings.port and record["pid"] == os.getpid()
        assert record["db_dir"] == str(settings.db_dir)
        assert state.stat().st_mode & 0o777 == 0o600
    assert not state.exists()  # removed at a clean stop


def test_stale_state_file_of_this_node_replaced(settings: Settings) -> None:
    """The lock is free, so a state file naming this node is a server that died."""
    state = settings.data_dir / "server.json"
    write_private(state, json.dumps({"host": socket.gethostname(), "port": 1, "pid": 1}))
    with started(settings):
        assert json.loads(state.read_text())["pid"] == os.getpid()


def test_port_taken_refuses(settings: Settings) -> None:
    with socket.socket() as other:
        other.bind(("127.0.0.1", settings.port))
        other.listen()
        with (
            pytest.raises(ServeError, match=rf"port {settings.port}.*uid {os.getuid()}"),
            started(settings),
        ):
            pass
    assert not (settings.data_dir / "server.json").exists()


def test_cli_refusal_exits_2(settings: Settings) -> None:
    settings.runs_root.chmod(0o777)
    result = CliRunner().invoke(app, ["serve"])
    assert result.exit_code == 2
    assert "spectio serve: runs root" in result.output


def test_serve_local_start_text(settings: Settings) -> None:
    text = start_text(settings, "node1", "alice")
    assert f"http://127.0.0.1:{settings.port}/" in text
    assert "on this machine" in text
    assert "ssh -N -L" not in text
    assert "P1 Task 12" in text  # no token link yet: local-only (inbox #80)


def test_serve_slurm_start_text_and_no_runner(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    slurm = settings.model_copy(update={"executor": "slurm"})
    port = settings.port
    text = start_text(slurm, "login1", "alice")
    assert f"ssh -N -L 127.0.0.1:{port}:127.0.0.1:{port} alice@login1" in text
    assert f"http://127.0.0.1:{port}/" in text
    assert "P1 Task 10" in text
    assert slurm.db_dir is not None
    with caplog.at_level(logging.WARNING):
        booted = boot(slurm, slurm.db_dir)
    try:
        assert booted.loop is None
        assert "P1 Task 10" in caplog.text
    finally:
        booted.close()


def test_rebuild_one_engine_per_location(settings: Settings, writer: Writer) -> None:
    """One `workflows` row per location: a run of the other engine there is skipped, counted."""
    root = settings.runs_root
    make_run(root, run_id(1), "nextflow")
    paths = make_run_dirs(root, run_id(2))
    manifest = RunManifest(
        run_id=run_id(2),
        name="same place",
        workflow=Workflow(location="/pipelines/happy-nextflow", engine="snakemake"),
        params={},
        profiles=[],
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    write_run_manifest(paths.run_dir, manifest)
    found = rebuild_index(writer, root)
    assert (found.added, found.skipped) == (1, 1)


def test_sink_leases_once_until_the_lease_ends(settings: Settings, writer: Writer) -> None:
    root = settings.runs_root
    make_run(root, run_id(1))
    rebuild_index(writer, root)
    launch_id = writer.submit(lambda c: c.execute(select(launches.c.id)).scalar_one()).result()
    now = datetime.now(UTC)
    writer.submit(
        lambda c: c.execute(
            insert(runner_commands).values(
                id="cmd_1",
                launch_id=launch_id,
                run_id=run_id(1),
                kind="cancel",
                state="pending",
                created_at=now,
            )
        )
    ).result()
    sink = StoreSink(writer, root)
    (command,) = sink.lease_commands()
    assert (command.id, command.kind, command.launch.launch_id) == ("cmd_1", "cancel", launch_id)
    assert command.launch.launch_dir == root / run_id(1) / "launch"  # derived, not read
    assert sink.lease_commands() == []  # leased
    writer.submit(
        lambda c: c.execute(update(runner_commands).values(lease_until=now - timedelta(seconds=1)))
    ).result()
    assert [c.id for c in sink.lease_commands()] == ["cmd_1"]  # the lease ran out: again
    sink.ack("cmd_1", True, None)
    assert sink.lease_commands() == []
    row = writer.submit(
        lambda c: c.execute(select(runner_commands.c.state, runner_commands.c.attempts)).one()
    ).result()
    assert (row.state, row.attempts) == ("done", 2)
    assert [r.run_id for r in sink.active_launches()] == []  # its run failed: no head ran


def test_sigterm_stops_cleanly(settings: Settings) -> None:
    """`spectio serve` in the foreground: the start text, then SIGTERM stops it with the state
    file removed and the lock free."""
    spectio = Path(sys.executable).parent / "spectio"
    proc = subprocess.Popen(
        [str(spectio), "serve"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    try:
        assert proc.stdout is not None
        first = proc.stdout.readline()
        assert first.startswith("Spectio ") and f"port {settings.port}" in first
        assert (settings.data_dir / "server.json").exists()
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(20) == 0
    finally:
        proc.kill()
        proc.wait()
    assert not (settings.data_dir / "server.json").exists()
    with started(settings):  # the lock is free
        pass


def test_missing_data_dir_refused(settings: Settings) -> None:
    settings.data_dir.rename(settings.data_dir.with_name("moved"))
    with pytest.raises(ServeError, match=str(settings.data_dir)), started(settings):
        pass
