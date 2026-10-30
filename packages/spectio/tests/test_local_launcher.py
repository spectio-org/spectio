"""The local launcher, the run directory and the runner loop (P1 Task 9; schedulers §3.1.1;
dev-env §15.3 req. 10 and 11). Heads run a stub engine through the login shell."""

import json
import os
import shlex
import shutil
import socket
import stat
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from spectio.config import EngineOpts, Settings
from spectio.runner.local import LocalLauncher
from spectio.runner.loop import RunnerLoop
from spectio.runner.rundir import (
    RunManifest,
    make_run_dirs,
    read_run_manifest,
    write_run_manifest,
)
from spectio.runner.spool import SPOOL_REFUSED
from spectio.runner.types import Command, HeadReport, LaunchRef, LaunchSpec, SpoolBatch

RUN_A = "run_01K8T9HEAD0000000000000T0A"
RUN_B = "run_01K8T9HEAD0000000000000T0B"
NOW = datetime(2026, 10, 30, tzinfo=UTC)
SLEEP = shutil.which("sleep") or "/bin/sleep"
# The stub engine: answers the version check, then runs BODY in the launch directory.
STUB = """#!/bin/bash
case "$1" in -version) echo "      version 26.10.4 build 5960"; exit 0;; esac
BODY
"""


def stub_engine(where: Path, body: str) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / "engine"
    path.write_text(STUB.replace("BODY", body))
    path.chmod(0o755)
    return path


def mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def wait_for(pred: Callable[[], object], timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


@pytest.fixture
def runs_root(home: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch) -> Path:
    """A runs root, a nf-spectio copy to unpack, and a login PATH with the usual tools."""
    root = home / "runs"
    root.mkdir(mode=0o700)
    bridges = home / "bridges" / "nf-spectio-0.0.1"
    bridges.mkdir(parents=True)
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(bridges.parent))
    monkeypatch.setenv("NXF_HOME", str(home / ".nextflow"))
    login(Path("/usr/bin"), Path("/bin"))
    return root


def spec_for(runs_root: Path, engine: Path, run_id: str = RUN_A) -> LaunchSpec:
    paths = make_run_dirs(runs_root, run_id)
    return LaunchSpec(
        run_id=run_id,
        launch_n=1,
        engine="nextflow",
        engine_cmd=shlex.quote(str(engine)),
        location=runs_root.parent / "pipeline",
        launch_dir=paths.launch_dir,
        work_dir=paths.work_dir,
    )


def ref_for(spec: LaunchSpec, native_id: str | None = None) -> LaunchRef:
    return LaunchRef(
        "lch_" + spec.run_id[4:], spec.run_id, 1, "nextflow", spec.launch_dir, native_id
    )


@pytest.fixture
def launcher() -> Iterator[LocalLauncher]:
    launcher = LocalLauncher()
    yield launcher
    for native_id in list(launcher._dirs):  # a test that fails leaves no head behind
        launcher.cancel(native_id, grace_s=0)
        launcher.poll([native_id])


def ended(launcher: LocalLauncher, native_id: str) -> HeadReport:
    found: list[HeadReport] = []

    def done() -> bool:
        found.append(launcher.poll([native_id])[native_id])
        return found[-1].ended

    wait_for(done)
    return found[-1]


def test_local_launch_exit_file(runs_root: Path, launcher: LocalLauncher) -> None:
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "echo out; exit 3"))
    native_id = launcher.submit(spec)
    report = ended(launcher, native_id)
    assert report.exit_code == 3 and report.state == "exited" and report.failure is None
    assert report.node == socket.gethostname()
    spectio_dir = spec.launch_dir / ".spectio"
    code, epoch = (spectio_dir / "head.exit").read_text().split()
    assert code == "3" and abs(int(epoch) - time.time()) < 60
    assert "out" in (spectio_dir / "head.out").read_text()
    pid, pgid, *_ = (spectio_dir / "head.pid").read_text().split()
    assert pid == pgid == native_id  # setsid: the head leads its own group


def test_adopt_after_restart(runs_root: Path, launcher: LocalLauncher) -> None:
    body = "while [ ! -e release ]; do sleep 0.05; done; exit 0"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    native_id = launcher.submit(spec)
    head_pid = spec.launch_dir / ".spectio" / "head.pid"
    wait_for(head_pid.exists)
    restarted = LocalLauncher()  # a new server: it knows nothing of the head
    report = restarted.adopt(ref_for(spec, native_id))
    assert report.state == "running" and not report.ended and report.native_id == native_id
    assert restarted.poll([native_id])[native_id].state == "running"
    (spec.launch_dir / "release").touch()
    assert ended(restarted, native_id).exit_code == 0


def test_adopt_head_gone_without_exit_file(runs_root: Path, launcher: LocalLauncher) -> None:
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "exit 0"))
    ended(launcher, launcher.submit(spec))
    (spec.launch_dir / ".spectio" / "head.exit").unlink()  # as after a SIGKILL
    report = LocalLauncher().adopt(ref_for(spec))
    assert report.ended and report.exit_code is None and report.state == "unknown"


def test_run_manifest_written(runs_root: Path) -> None:
    manifest = RunManifest(
        run_id=RUN_A,
        name="synthetic-000T0A",
        workflow={"location": "/p/a b", "engine": "nextflow"},
        params={"x": "$(y)", "n": 2},
        profiles=["test"],
        created_at=NOW,
    )
    run_dir = runs_root / RUN_A
    write_run_manifest(run_dir, manifest)
    path = run_dir / ".spectio" / "run.json"
    assert mode(path) == 0o600 and mode(run_dir / ".spectio") == 0o700 and mode(run_dir) == 0o700
    assert read_run_manifest(run_dir) == manifest
    other = runs_root / RUN_B
    other.mkdir(mode=0o700)
    (other / ".spectio").mkdir(mode=0o700)
    (other / ".spectio" / "run.json").write_text(path.read_text())
    os.chmod(other / ".spectio" / "run.json", 0o600)
    with pytest.raises(ValueError, match="run ID"):
        read_run_manifest(other)  # the run ID must equal the directory name (req. 10)


def test_run_dirs_private_and_walked(runs_root: Path) -> None:
    paths = make_run_dirs(runs_root, RUN_A)
    for path in (
        paths.run_dir,
        paths.launch_dir,
        paths.work_dir,
        paths.launch_dir / ".spectio",
        paths.launch_dir / ".spectio" / "events",
    ):
        assert mode(path) == 0o700, path
    paths.run_dir.chmod(0o770)
    with pytest.raises(PermissionError, match="private"):
        make_run_dirs(runs_root, RUN_A)
    paths.run_dir.chmod(0o700)
    swapped = runs_root / RUN_B
    swapped.symlink_to(paths.run_dir)
    with pytest.raises(OSError):
        make_run_dirs(runs_root, RUN_B)  # never followed
    with pytest.raises(ValueError, match="run ID"):
        make_run_dirs(runs_root, "../x")
    runs_root.chmod(0o770)
    with pytest.raises(PermissionError, match="runs root"):
        make_run_dirs(runs_root, RUN_A)


def head_pid_line(pid: int, boot_id: str | None = None, start: str | None = None) -> str:
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    boot = boot_id or Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return f"{pid} {fields[2]} {start or fields[19]} {boot} {socket.gethostname()}\n"


@pytest.mark.parametrize("wrong", ["boot_id", "start"])
def test_cancel_never_signals_other_boot_id(runs_root: Path, wrong: str) -> None:
    spec = spec_for(runs_root, runs_root.parent / "unused")
    sleeper = subprocess.Popen([SLEEP, "30"], start_new_session=True)
    try:
        line = head_pid_line(
            sleeper.pid,
            boot_id="00000000-0000-0000-0000-000000000000" if wrong == "boot_id" else None,
            start="1" if wrong == "start" else None,
        )
        pid_file = spec.launch_dir / ".spectio" / "head.pid"
        pid_file.write_text(line)
        pid_file.chmod(0o600)
        launcher = LocalLauncher()
        report = launcher.adopt(ref_for(spec, str(sleeper.pid)))
        assert report.ended and report.exit_code is None  # not our head: gone, exit unknown
        launcher.cancel(str(sleeper.pid), grace_s=0)
        launcher.poll([str(sleeper.pid)])
        time.sleep(0.2)
        assert sleeper.poll() is None  # never signalled
    finally:
        sleeper.kill()
        sleeper.wait()


def test_cancel_term_then_kill(runs_root: Path, launcher: LocalLauncher) -> None:
    body = "trap '' TERM; touch started; while :; do sleep 0.05; done"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    launcher.cancel(native_id, grace_s=0)
    report = ended(launcher, native_id)  # TERM ignored by the engine: SIGKILL after the grace
    assert report.exit_code is None or report.exit_code != 0


# --- The runner loop ------------------------------------------------------------------------


class FakeSink:
    """The server side of `RunnerSink`, in memory."""

    def __init__(self) -> None:
        self.commands: list[Command] = []
        self.acks: list[tuple[str, bool, str | None]] = []
        self.launches: dict[str, LaunchRef] = {}
        self.cursors: dict[str, dict[str, int]] = {}
        self.batches: list[tuple[str, SpoolBatch]] = []
        self.reports: list[tuple[str, HeadReport]] = []

    def lease_commands(self) -> list[Command]:
        leased, self.commands = self.commands, []
        return leased

    def ack(self, command_id: str, ok: bool, detail: str | None) -> None:
        self.acks.append((command_id, ok, detail))

    def active_launches(self) -> list[LaunchRef]:
        return list(self.launches.values())

    def cursor(self, launch_id: str) -> dict[str, int]:
        return self.cursors.get(launch_id, {})

    def ingest(self, launch_id: str, batch: SpoolBatch) -> None:
        self.batches.append((launch_id, batch))
        self.cursors[launch_id] = batch.cursor

    def head_report(self, launch_id: str, report: HeadReport) -> None:
        self.reports.append((launch_id, report))
        if report.native_id:
            self.launches[launch_id] = replace(self.launches[launch_id], native_id=report.native_id)
        if report.ended:
            del self.launches[launch_id]  # the run ends: no longer active

    def last(self, launch_id: str) -> HeadReport:
        return [r for lid, r in self.reports if lid == launch_id][-1]

    def launch(self, runs_root: Path, run_id: str) -> LaunchRef:
        ref = LaunchRef("lch_" + run_id[4:], run_id, 1, "nextflow", runs_root / run_id / "launch")
        self.launches[ref.launch_id] = ref
        payload = {"location": str(runs_root.parent / "pipeline"), "profiles": [], "params": {}}
        self.commands.append(Command("cmd_" + run_id[4:], "launch", ref, payload))
        return ref


def make_loop(sink: FakeSink, runs_root: Path, engine: Path, launcher: LocalLauncher) -> RunnerLoop:
    settings = Settings(
        runs_root=runs_root,
        executor="local",
        engines=EngineOpts(nextflow_cmd=shlex.quote(str(engine))),
    )
    return RunnerLoop(sink, launcher, settings, tick_s=0.05, end_grace_s=0)


def run_until(loop: RunnerLoop, pred: Callable[[], object], timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while True:
        loop.tick()
        if pred():
            return
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


def spool_line(run_id: str, seq: int, hook: str) -> str:
    return json.dumps(
        {
            "v": 1,
            "id": f"evt-{seq}",
            "run": run_id,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": seq,
            "time": "2026-10-30T00:00:00Z",
            "type": f"nextflow.{hook}",
            "data": {},
        }
    )


def test_loop_launches_reads_spool_and_ends(runs_root: Path, launcher: LocalLauncher) -> None:
    line = spool_line("RUN", 1, "onFlowCreate").replace('"RUN"', '"%s"')
    spool = '"$SPECTIO_SPOOL_DIR/nf-spectio-1-0001.jsonl"'
    body = f'printf {shlex.quote(line + chr(10))} "$SPECTIO_RUN_ID" > {spool}; exit 0'
    engine = stub_engine(runs_root.parent / "bin", body)
    sink = FakeSink()
    loop = make_loop(sink, runs_root, engine, launcher)
    ref = sink.launch(runs_root, RUN_A)
    run_until(loop, lambda: ref.launch_id not in sink.launches)
    assert sink.acks == [("cmd_" + RUN_A[4:], True, None)]
    events = [e for lid, b in sink.batches if lid == ref.launch_id for e in b.events]
    assert [e.type for e in events] == ["nextflow.onFlowCreate"]
    first, last = sink.reports[0][1], sink.last(ref.launch_id)
    assert first.state == "starting" and first.native_id
    # Nextflow ended with no terminal engine event: the runner names the class (Assumption 15).
    assert last.ended and last.exit_code == 0
    assert last.failure is not None and last.failure.class_ == "engine_fault"


def test_cancel_and_launch_failure_markers(runs_root: Path, launcher: LocalLauncher) -> None:
    body = (
        "trap '[ -e .spectio/cancel ] && touch marker-seen; exit 143' TERM; "
        "touch started; while :; do sleep 0.05; done"
    )
    sink = FakeSink()
    loop = make_loop(sink, runs_root, stub_engine(runs_root.parent / "bin", body), launcher)
    ref = sink.launch(runs_root, RUN_A)
    launch_dir = ref.launch_dir
    run_until(loop, (launch_dir / "started").exists)
    sink.commands.append(Command("cmd_cancel", "cancel", sink.launches[ref.launch_id]))
    run_until(loop, lambda: ref.launch_id not in sink.launches)
    assert (launch_dir / ".spectio" / "cancel").is_file()
    assert (launch_dir / "marker-seen").exists()  # the marker was there before the signal
    assert sink.last(ref.launch_id).exit_code == 143
    assert ("cmd_cancel", True, None) in sink.acks
    # A missing engine: launch-failed.json, class engine_missing, and the run's failure.
    missing = make_loop(sink, runs_root, runs_root.parent / "no-such-engine", launcher)
    ref_b = sink.launch(runs_root, RUN_B)
    missing.tick()
    failed = json.loads((ref_b.launch_dir / ".spectio" / "launch-failed.json").read_text())
    assert failed["class"] == "engine_missing"
    assert mode(ref_b.launch_dir / ".spectio" / "launch-failed.json") == 0o600
    report = sink.last(ref_b.launch_id)
    assert report.ended and report.failure is not None
    assert report.failure.class_ == "engine_missing"
    assert sink.acks[-1][0] == "cmd_" + RUN_B[4:] and not sink.acks[-1][1]


def test_redelivered_launch_never_starts_twice(runs_root: Path, launcher: LocalLauncher) -> None:
    """schedulers §3.1.1: after a restart, a launch command delivered again adopts the head."""
    body = "echo x >> starts; while [ ! -e release ]; do sleep 0.05; done"
    engine = stub_engine(runs_root.parent / "bin", body)
    sink = FakeSink()
    ref = sink.launch(runs_root, RUN_A)
    command = sink.commands[0]
    run_until(make_loop(sink, runs_root, engine, launcher), (ref.launch_dir / "starts").exists)
    native_id = sink.last(ref.launch_id).native_id
    wait_for((ref.launch_dir / ".spectio" / "head.pid").exists)
    sink.commands.append(replace(command, launch=sink.launches[ref.launch_id]))
    restarted = LocalLauncher()
    make_loop(sink, runs_root, engine, restarted).tick()
    assert (ref.launch_dir / "starts").read_text() == "x\n"
    assert sink.last(ref.launch_id).state == "running"
    assert sink.last(ref.launch_id).native_id == native_id
    (ref.launch_dir / "release").touch()


def test_loop_refused_spool_never_stops_the_loop(runs_root: Path, launcher: LocalLauncher) -> None:
    """SEC-P3T3-09, CR-P3T04-05 and -11: a refused spool is counted once; the others go on."""
    sink = FakeSink()
    loop = make_loop(sink, runs_root, runs_root.parent / "unused", launcher)
    refs = []
    for run_id in (RUN_A, RUN_B):
        paths = make_run_dirs(runs_root, run_id)
        ref = LaunchRef("lch_" + run_id[4:], run_id, 1, "nextflow", paths.launch_dir, None)
        sink.launches[ref.launch_id] = ref
        refs.append(ref)
        spool = paths.launch_dir / ".spectio" / "events" / "nf-spectio-1-0001.jsonl"
        spool.write_text(spool_line(run_id, 1, "onFlowCreate") + "\n")
        spool.chmod(0o600)
    (refs[0].launch_dir / ".spectio" / "events").chmod(0o755)
    for _ in range(3):
        loop.tick()
    refused = [b for lid, b in sink.batches if lid == refs[0].launch_id]
    assert [b.drops for b in refused] == [{SPOOL_REFUSED: 1}]  # once, not once per tick
    read = [e for lid, b in sink.batches if lid == refs[1].launch_id for e in b.events]
    assert len(read) == 1
    (refs[0].launch_dir / ".spectio" / "events").chmod(0o700)
    loop.tick()
    events = [e for lid, b in sink.batches if lid == refs[0].launch_id for e in b.events]
    assert len(events) == 1  # read again once the directory is private


def test_loop_refuses_a_launch_dir_off_the_runs_root(
    runs_root: Path, launcher: LocalLauncher
) -> None:
    sink = FakeSink()
    loop = make_loop(sink, runs_root, runs_root.parent / "unused", launcher)
    elsewhere = runs_root.parent / "elsewhere"
    ref = LaunchRef("lch_x", RUN_A, 1, "nextflow", elsewhere, None)
    sink.launches[ref.launch_id] = ref
    loop.tick()
    assert [b.drops for _, b in sink.batches] == [{SPOOL_REFUSED: 1}]
    assert not elsewhere.exists()
