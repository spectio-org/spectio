"""The local launcher, the run directory and the runner loop (P1 Task 9; schedulers §3.1.1;
dev-env §15.3 req. 10 and 11). Heads run a stub engine through the login shell."""

import json
import logging
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
    pid, pgid, start, *_ = (spectio_dir / "head.pid").read_text().split()
    assert pid == pgid  # setsid: the head leads its own group
    assert native_id == f"{pid}.{start}"  # unique per process, not a bare PID (SEC-P3T09-04)


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


@pytest.mark.parametrize("umask", [0o002, 0o000])
def test_head_files_private_whatever_the_umask(runs_root: Path, umask: int) -> None:
    """CR-P3T09-01, SEC-P3T09-01: under a umask of 002 (user-private groups) or 000, the head
    files are 0600, so the launch, a cancel and an adopt still read them."""
    body = "trap 'exit 143' TERM; touch started; while :; do sleep 0.05; done"
    engine = stub_engine(runs_root.parent / "bin", body)
    old = os.umask(umask)
    launcher = LocalLauncher()
    try:
        spec = spec_for(runs_root, engine)
        native_id = launcher.submit(spec)
        wait_for((spec.launch_dir / "started").exists)
        assert launcher.poll([native_id])[native_id].state == "running"
        assert LocalLauncher().adopt(ref_for(spec, native_id)).state == "running"
        launcher.cancel(native_id, grace_s=30)
        report = ended(launcher, native_id)
        assert report.state == "exited" and report.exit_code == 143
        spectio_dir = spec.launch_dir / ".spectio"
        for name in ("head.pid", "head.exit", "head.out", "head.err"):
            assert mode(spectio_dir / name) == 0o600, name
    finally:
        os.umask(old)
        for native_id in list(launcher._dirs):
            launcher.cancel(native_id, grace_s=0)
            launcher.poll([native_id])


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
        report = launcher.adopt(ref_for(spec))
        assert report.ended and report.exit_code is None  # not our head: gone, exit unknown
        assert report.native_id is not None
        launcher.cancel(report.native_id, grace_s=0)
        launcher.poll([report.native_id])
        time.sleep(0.2)
        assert sleeper.poll() is None  # never signalled
    finally:
        sleeper.kill()
        sleeper.wait()


def test_stale_kill_never_reaches_a_later_head(
    runs_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T09-02: launch A is cancelled and exits; launch B's head gets the same PID (so the
    same native ID); the poll after A's grace leaves B alive. PID reuse is simulated: one
    process that ignores TERM plays both heads, told apart by their recorded start times."""
    spec_a = spec_for(runs_root, runs_root.parent / "unused", RUN_A)
    spec_b = spec_for(runs_root, runs_root.parent / "unused", RUN_B)
    script = "trap '' TERM; echo ready; exec sleep 30"
    head = subprocess.Popen(
        ["/bin/bash", "-c", script], stdout=subprocess.PIPE, start_new_session=True
    )
    assert head.stdout is not None and head.stdout.readline() == b"ready\n"
    starts = {"now": "111"}
    monkeypatch.setattr(
        "spectio.runner.local._process",
        lambda pid: (head.pid, starts["now"]) if pid == head.pid and starts["now"] else None,
    )
    try:
        for spec, start in ((spec_a, "111"), (spec_b, "222")):
            pid_file = spec.launch_dir / ".spectio" / "head.pid"
            pid_file.write_text(head_pid_line(head.pid, start=start))
            pid_file.chmod(0o600)
        launcher = LocalLauncher()
        id_a, id_b = f"{head.pid}.111", f"{head.pid}.222"
        assert launcher.adopt(ref_for(spec_a, id_a)).state == "running"
        launcher.cancel(id_a, grace_s=0)  # SIGTERM to A, SIGKILL due at the next poll
        starts["now"] = "222"  # A exits, and B starts with A's PID
        assert launcher.adopt(ref_for(spec_b, id_b)).state == "running"
        reports = launcher.poll([id_a, id_b])
        time.sleep(0.2)
        assert head.poll() is None  # B never got A's SIGKILL
        assert reports[id_b].state == "running"
    finally:
        head.kill()
        head.communicate()


def test_reused_pid_keeps_two_launches_apart(runs_root: Path) -> None:
    """SEC-P3T09-04, CR-P3T09-08: launch A's head has ended, its launch still active (the spool
    grace), and launch B's head has A's PID. A cancel of A signals nothing in B's group, and a
    poll reports A and B apart. PID reuse is simulated: A's head.pid names B's PID with an
    earlier start time, and A's head.exit is there."""
    spec_a = spec_for(runs_root, runs_root.parent / "unused", RUN_A)
    spec_b = spec_for(runs_root, runs_root.parent / "unused", RUN_B)
    head_b = subprocess.Popen([SLEEP, "30"], start_new_session=True)
    try:
        for spec, name, text in (
            (spec_a, "head.pid", head_pid_line(head_b.pid, start="1")),
            (spec_a, "head.exit", "0 1\n"),
            (spec_b, "head.pid", head_pid_line(head_b.pid)),
        ):
            path = spec.launch_dir / ".spectio" / name
            path.write_text(text)
            path.chmod(0o600)
        launcher = LocalLauncher()
        id_a = launcher.adopt(ref_for(spec_a)).native_id
        id_b = launcher.adopt(ref_for(spec_b)).native_id
        assert id_a and id_b and id_a != id_b
        launcher.cancel(id_a, grace_s=0)
        reports = launcher.poll([id_a, id_b])
        time.sleep(0.2)
        assert head_b.poll() is None  # never signalled
        assert (reports[id_a].state, reports[id_a].exit_code) == ("exited", 0)
        assert reports[id_b].state == "running" and not reports[id_b].ended
    finally:
        head_b.kill()
        head_b.wait()


def test_never_signals_a_group_the_head_does_not_lead(runs_root: Path) -> None:
    """SEC-P3T09-08: a local head leads its own group; a head.pid whose group is another's
    (head.sh started by hand in a shell's job) is never signalled, and reported unknown."""
    spec = spec_for(runs_root, runs_root.parent / "unused")
    leader = subprocess.Popen([SLEEP, "30"], process_group=0)
    member = subprocess.Popen([SLEEP, "30"], process_group=leader.pid)
    try:
        pid_file = spec.launch_dir / ".spectio" / "head.pid"
        pid_file.write_text(head_pid_line(member.pid))  # its group is the leader's
        pid_file.chmod(0o600)
        fields = pid_file.read_text().split()
        native_id = f"{fields[0]}.{fields[2]}"
        launcher = LocalLauncher()
        report = launcher.adopt(ref_for(spec, native_id))
        assert report.state == "unknown" and not report.ended
        launcher.cancel(native_id, grace_s=0)
        launcher.poll([native_id])
        time.sleep(0.2)
        assert leader.poll() is None and member.poll() is None
    finally:
        for proc in (member, leader):
            proc.kill()
            proc.wait()


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


def make_loop(
    sink: FakeSink, runs_root: Path, engine: Path, launcher: LocalLauncher, end_grace_s: float = 0
) -> RunnerLoop:
    settings = Settings(
        runs_root=runs_root,
        executor="local",
        engines=EngineOpts(nextflow_cmd=shlex.quote(str(engine))),
    )
    return RunnerLoop(sink, launcher, settings, tick_s=0.05, end_grace_s=end_grace_s)


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
    # umask 077: the bridges create spool files 0600 whatever the umask, as this stub must
    body = f'umask 077; printf {shlex.quote(line + chr(10))} "$SPECTIO_RUN_ID" > {spool}; exit 0'
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
    loop.tick()  # the launch is no longer active: the launcher forgets it (CR-P3T09-07)
    assert not launcher._dirs and not launcher._procs and not launcher._warned


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


def test_cancel_before_the_head_starts(runs_root: Path, launcher: LocalLauncher) -> None:
    """CR-P3T09-02: a cancel leased with the launch (no native ID yet) is acked, and the launch
    that follows starts no head and ends with none."""
    engine = stub_engine(runs_root.parent / "bin", "touch started; exit 0")
    sink = FakeSink()
    loop = make_loop(sink, runs_root, engine, launcher)
    ref = sink.launch(runs_root, RUN_A)
    sink.commands.insert(0, Command("cmd_cancel", "cancel", ref))  # the stale ref, before it
    loop.tick()
    assert ("cmd_cancel", True, None) in sink.acks
    assert ("cmd_" + RUN_A[4:], True, None) in sink.acks
    assert (ref.launch_dir / ".spectio" / "cancel").is_file()
    assert not (ref.launch_dir / ".spectio" / "head.sh").exists()
    report = sink.last(ref.launch_id)
    assert report.ended and report.native_id is None
    assert not launcher._dirs
    time.sleep(0.2)
    assert not (ref.launch_dir / "started").exists()


def test_cancel_before_the_head_starts_skips_the_spool_grace(
    runs_root: Path, launcher: LocalLauncher
) -> None:
    """CR-P3T09-03: with the default spool grace (60 s), a launch cancelled before its head
    starts still ends in one tick: no engine ran, so there is no spool to wait for."""
    engine = stub_engine(runs_root.parent / "bin", "exit 0")
    sink = FakeSink()
    loop = make_loop(sink, runs_root, engine, launcher, end_grace_s=60)
    ref = sink.launch(runs_root, RUN_A)
    sink.commands.insert(0, Command("cmd_cancel", "cancel", ref))
    loop.tick()
    assert ref.launch_id not in sink.launches
    report = sink.last(ref.launch_id)
    assert report.ended and report.failure is not None
    assert report.failure.class_ == "head_lost"


def test_cancel_with_a_stale_ref_after_the_launch(runs_root: Path, launcher: LocalLauncher) -> None:
    """CR-P3T09-02: a launch and then a cancel in one lease, the cancel's ref still without a
    native ID: the head just started is cancelled, and its engine never runs."""
    engine = stub_engine(runs_root.parent / "bin", "touch started; sleep 30")
    sink = FakeSink()
    loop = make_loop(sink, runs_root, engine, launcher)
    ref = sink.launch(runs_root, RUN_A)
    sink.commands.append(Command("cmd_cancel", "cancel", ref))
    run_until(loop, lambda: ref.launch_id not in sink.launches)
    assert ("cmd_cancel", True, None) in sink.acks
    assert sink.last(ref.launch_id).exit_code == 143
    assert not (ref.launch_dir / "started").exists()


def test_unreadable_head_logged_once(runs_root: Path, caplog: pytest.LogCaptureFixture) -> None:
    """SEC-P3T09-01: a refused head.pid is logged once per head, not at every poll."""
    spec = spec_for(runs_root, runs_root.parent / "unused")
    pid_file = spec.launch_dir / ".spectio" / "head.pid"
    pid_file.write_text(head_pid_line(os.getpid()))
    pid_file.chmod(0o620)
    launcher = LocalLauncher()
    launcher.adopt(ref_for(spec, "1"))
    for _ in range(3):
        assert launcher.poll(["1"])["1"].state == "unknown"
    assert len([r for r in caplog.records if "not read" in r.getMessage()]) == 1


def test_refused_adopt_logged_once(
    runs_root: Path, launcher: LocalLauncher, caplog: pytest.LogCaptureFixture
) -> None:
    """CR-P3T09-09: an active launch whose adopt is refused (its directory is not the run's) is
    logged once, not at every tick."""
    sink = FakeSink()
    loop = make_loop(sink, runs_root, runs_root.parent / "unused", launcher)
    ref = LaunchRef("lch_x", RUN_A, 1, "nextflow", runs_root.parent / "elsewhere", "1.1")
    sink.launches[ref.launch_id] = ref
    for _ in range(3):
        loop.tick()
    logged = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len([m for m in logged if "spool" not in m]) == 1  # the spool's own: once too


def test_redelivered_launch_after_a_cancel_with_no_native_id(
    runs_root: Path, launcher: LocalLauncher
) -> None:
    """CR-P3T09-04 (r2): the server lost the native ID (it stopped between submit and the
    report); after a restart, a cancel with no native ID only writes the marker, and the launch
    delivered again adopts the running head and cancels it."""
    engine = stub_engine(runs_root.parent / "bin", "touch started; while :; do sleep 0.05; done")
    sink = FakeSink()
    ref = sink.launch(runs_root, RUN_A)
    command = sink.commands[0]
    run_until(make_loop(sink, runs_root, engine, launcher), (ref.launch_dir / "started").exists)
    sink.launches[ref.launch_id] = ref  # no native ID
    sink.commands = [Command("cmd_cancel", "cancel", ref), command]
    run_until(
        make_loop(sink, runs_root, engine, LocalLauncher()),
        lambda: ref.launch_id not in sink.launches,
    )
    assert ("cmd_cancel", True, None) in sink.acks
    assert sink.last(ref.launch_id).exit_code == 143


def test_snakemake_end_skips_the_spool_grace(runs_root: Path, launcher: LocalLauncher) -> None:
    """FU-P3-14 (CR-P3T09-04): with the default spool grace (60 s), a Snakemake head that exits
    with a code ends its launch at the poll that sees it, after one more read of its spool, so
    the events it wrote just before it exited are ingested first."""
    line = spool_line("RUN", 1, "x").replace('"RUN"', '"%s"')
    line = line.replace('"nf-spectio/0.0.1"', '"snakemake-logger-spectio/0.0.1"')
    line = line.replace('"nextflow.x"', '"snakemake.log"')
    spool = '"$SPECTIO_SPOOL_DIR/snakemake-logger-spectio-1-0001.jsonl"'
    body = f'umask 077; sleep 0.5; printf {shlex.quote(line + chr(10))} "$SPECTIO_RUN_ID" > {spool}'
    logger = runs_root.parent / "bridges" / "snakemake_logger_plugin_spectio"  # Task 7's place
    logger.mkdir()
    (logger / "__init__.py").write_text("")
    version = 'case "$1" in --version) echo 9.27.1; exit 0;; esac\n'
    engine = stub_engine(runs_root.parent / "bin", version + body + "; exit 0")
    sink = FakeSink()
    settings = Settings(
        runs_root=runs_root,
        executor="local",
        engines=EngineOpts(snakemake_cmd=shlex.quote(str(engine))),
    )
    loop = RunnerLoop(sink, launcher, settings, tick_s=0.05, end_grace_s=60)
    ref = sink.launch(runs_root, RUN_A)
    sink.launches[ref.launch_id] = ref = replace(ref, engine="snakemake")
    sink.commands[-1] = replace(sink.commands[-1], launch=ref)
    run_until(loop, lambda: ref.launch_id not in sink.launches, timeout=30)
    report = sink.last(ref.launch_id)
    assert (report.ended, report.exit_code, report.failure) == (True, 0, None), report
    assert [len(b.events) for _, b in sink.batches if b.events] == [1]  # read before the end
