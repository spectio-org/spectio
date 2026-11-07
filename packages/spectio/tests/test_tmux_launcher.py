"""The tmux launcher, with the fake tmux of `fakebin/` (P1 Task 10; schedulers §3.1.1, tmux
launcher; dev-env §15.3 req. 11). Heads run a stub engine through the login shell."""

import json
import os
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from spectio.config import EngineOpts, Settings
from spectio.runner.loop import RunnerLoop
from spectio.runner.rundir import make_run_dirs
from spectio.runner.tmux import TmuxLauncher
from spectio.runner.types import Command, HeadReport, LaunchRef, LaunchSpec, SpoolBatch

RUN_A = "run_01K8T9TMXX0000000000000T0A"
FAKE = Path(__file__).parent / "fakebin" / "tmux"
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


def wait_for(pred: Callable[[], object], timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


@pytest.fixture
def runs_root(home: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch) -> Path:
    root = home / "runs"
    root.mkdir(mode=0o700)
    bridges = home / "bridges" / "nf-spectio-0.0.1"
    bridges.mkdir(parents=True)
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(bridges.parent))
    monkeypatch.setenv("NXF_HOME", str(home / ".nextflow"))
    login(Path("/usr/bin"), Path("/bin"))
    return root


@pytest.fixture
def fake_tmux(runs_root: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """The fake's state directory, `$TMUX_TMPDIR`; no head is left behind."""
    state = runs_root.parent / "tmux"
    state.mkdir()
    monkeypatch.setenv("TMUX_TMPDIR", str(state))
    monkeypatch.delenv("TMUX", raising=False)
    yield state
    for session in (state / "sessions").glob("spectio-*"):
        pid = int(session.read_text().split()[1])
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def calls(state: Path) -> list[list[str]]:
    return [json.loads(line) for line in (state / "calls.jsonl").read_text().splitlines()]


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


def running_from(where: Path) -> list[int]:
    """The live processes whose command line names a file under `where`."""
    found = []
    for proc in Path("/proc").iterdir():
        try:
            argv = (proc / "cmdline").read_bytes().split(b"\0")
            state = (proc / "stat").read_text().rsplit(") ", 1)[1].split()[0]
        except (OSError, IndexError):
            continue
        if state != "Z" and any(str(where).encode() in a for a in argv):
            found.append(int(proc.name))
    return found


def ended(launcher: TmuxLauncher, native_id: str) -> HeadReport:
    found: list[HeadReport] = []

    def done() -> bool:
        found.append(launcher.poll([native_id])[native_id])
        return found[-1].ended

    wait_for(done)
    return found[-1]


def running(launcher: TmuxLauncher, native_id: str) -> None:
    wait_for(lambda: launcher.poll([native_id])[native_id].state == "running")


def test_submit_creates_named_session(runs_root: Path, fake_tmux: Path) -> None:
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "exit 0"))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    assert native_id == f"spectio-{RUN_A}"
    head = spec.launch_dir / ".spectio" / "head.sh"
    bash = shutil.which("bash") or "/bin/bash"
    first = calls(fake_tmux)[0]
    assert first == [
        "new-session",
        *("-d", "-P", "-F", "#{pane_id} #{pane_pid}"),
        *("-s", f"spectio-{RUN_A}", "-c", str(spec.launch_dir)),
        *(bash, str(head)),
    ]
    assert "sbatch" not in head.read_text() and "setsid" not in head.read_text()
    report = ended(launcher, native_id)
    assert report.state == "exited" and report.exit_code == 0 and report.native_id == native_id
    pid, pgid, *_ = (spec.launch_dir / ".spectio" / "head.pid").read_text().split()
    assert pid == pgid  # the pane's command leads the pane's group: no setsid of ours


class Sink:
    """The server side of `RunnerSink`, in memory: one launch, no spool."""

    def __init__(self, ref: LaunchRef, payload: dict[str, Any]) -> None:
        self.launches = {ref.launch_id: ref}
        self.commands = [Command("cmd_1", "launch", ref, payload)]
        self.acks: list[tuple[str, bool, str | None]] = []
        self.reports: list[HeadReport] = []

    def lease_commands(self) -> list[Command]:
        leased, self.commands = self.commands, []
        return leased

    def ack(self, command_id: str, ok: bool, detail: str | None) -> None:
        self.acks.append((command_id, ok, detail))

    def active_launches(self) -> list[LaunchRef]:
        return list(self.launches.values())

    def cursor(self, launch_id: str) -> dict[str, int]:
        return {}

    def ingest(self, launch_id: str, batch: SpoolBatch) -> None:
        pass

    def head_report(self, launch_id: str, report: HeadReport) -> None:
        self.reports.append(report)
        if report.native_id:
            self.launches[launch_id] = replace(self.launches[launch_id], native_id=report.native_id)
        if report.ended:
            del self.launches[launch_id]


@pytest.mark.parametrize("why", ["missing", "exists"])
def test_tmux_start_failure_fails_run(runs_root: Path, fake_tmux: Path, why: str) -> None:
    engine = stub_engine(runs_root.parent / "bin", "exit 0")
    tmux = str(FAKE) if why == "exists" else str(runs_root.parent / "no-tmux")
    if why == "exists":
        (fake_tmux / "fail").write_text(f"duplicate session: spectio-{RUN_A}")
    ref = LaunchRef("lch_1", RUN_A, 1, "nextflow", runs_root / RUN_A / "launch")
    sink = Sink(ref, {"location": str(runs_root.parent / "pipeline")})
    settings = Settings(
        runs_root=runs_root, executor="slurm", engines=EngineOpts(nextflow_cmd=str(engine))
    )
    RunnerLoop(sink, TmuxLauncher(tmux), settings, end_grace_s=0).tick()
    assert not sink.launches  # the run ended at once: nothing stays queued
    (report,) = sink.reports
    assert report.ended and report.failure is not None
    assert report.failure.class_ == "launch_error"
    if why == "exists":
        assert report.failure.message.startswith(f"duplicate session: spectio-{RUN_A}")
    assert sink.acks[0][1] is False


@pytest.mark.parametrize("why", ["garbage", "timeout"])
def test_unparsed_or_slow_start_kills_its_session(
    runs_root: Path, fake_tmux: Path, monkeypatch: pytest.MonkeyPatch, why: str
) -> None:
    """A session started but not confirmed is ended: no engine runs on with no owner
    (CR-P3T10-01)."""
    engine = stub_engine(runs_root.parent / "bin", "touch started; sleep 30")
    if why == "garbage":
        (fake_tmux / "garbage").write_text("no pane here")
    else:
        monkeypatch.setattr("spectio.runner.tmux.TMUX_TIMEOUT_S", 2)
        (fake_tmux / "slow").write_text("4")
    ref = LaunchRef("lch_1", RUN_A, 1, "nextflow", runs_root / RUN_A / "launch")
    sink = Sink(ref, {"location": str(runs_root.parent / "pipeline")})
    settings = Settings(
        runs_root=runs_root, executor="slurm", engines=EngineOpts(nextflow_cmd=str(engine))
    )
    RunnerLoop(sink, TmuxLauncher(str(FAKE)), settings, end_grace_s=0).tick()
    (report,) = sink.reports
    assert report.ended and report.failure is not None
    assert report.failure.class_ == "launch_error"
    assert ["kill-session", "-t", f"=spectio-{RUN_A}"] in calls(fake_tmux)
    assert not (fake_tmux / "sessions" / f"spectio-{RUN_A}").exists()
    wait_for(lambda: not running_from(engine.parent))  # the engine went with its session


def test_kill_never_on_a_failed_start(runs_root: Path, fake_tmux: Path) -> None:
    """A non-zero new-session may be another launch's live session: it is never killed."""
    (fake_tmux / "fail").write_text(f"duplicate session: spectio-{RUN_A}")
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "exit 0"))
    with pytest.raises(OSError, match="duplicate session"):
        TmuxLauncher(str(FAKE)).submit(spec)
    assert [c[0] for c in calls(fake_tmux)] == ["new-session"]


def test_adopt_by_session_and_pid(runs_root: Path, fake_tmux: Path) -> None:
    body = "while [ ! -e release ]; do sleep 0.05; done; exit 0"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    native_id = TmuxLauncher(str(FAKE)).submit(spec)
    wait_for((spec.launch_dir / ".spectio" / "head.pid").exists)
    started = len(calls(fake_tmux))
    # A new server: the stored ID may be the local form a rebuilt index wrote (CR-P3T11-04).
    fresh = TmuxLauncher(str(FAKE))
    report = fresh.adopt(ref_for(spec, "1234.5678"))
    assert report.state == "running" and not report.ended and report.native_id == native_id
    assert [c[0] for c in calls(fake_tmux)[started:]] == ["list-panes"]  # no second start
    (spec.launch_dir / "release").touch()
    assert ended(fresh, native_id).exit_code == 0


def test_adopt_refused_when_the_pane_is_not_the_head(runs_root: Path, fake_tmux: Path) -> None:
    body = "while [ ! -e release ]; do sleep 0.05; done; exit 0"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    native_id = TmuxLauncher(str(FAKE)).submit(spec)
    head_pid = spec.launch_dir / ".spectio" / "head.pid"
    wait_for(head_pid.exists)
    session = fake_tmux / "sessions" / native_id
    pane, pid = session.read_text().split()
    other = subprocess.Popen(["sleep", "30"], start_new_session=True)  # noqa: S607
    session.write_text(f"{pane} {other.pid}")  # a session of that name whose pane is another
    fresh = TmuxLauncher(str(FAKE))
    report = fresh.adopt(ref_for(spec))
    assert report.state == "unknown" and not report.ended
    fresh.cancel(native_id, grace_s=0)
    assert all(c[0] != "send-keys" for c in calls(fake_tmux))
    session.write_text(f"{pane} {pid}")
    (spec.launch_dir / "release").touch()
    other.kill()
    other.wait()


def test_adopt_with_no_session_reads_the_exit_file(runs_root: Path, fake_tmux: Path) -> None:
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "exit 4"))
    native_id = TmuxLauncher(str(FAKE)).submit(spec)
    wait_for((spec.launch_dir / ".spectio" / "head.exit").exists)
    report = TmuxLauncher(str(FAKE)).adopt(ref_for(spec, native_id))
    assert report.ended and report.exit_code == 4


def test_head_stopped_by_hand(runs_root: Path, fake_tmux: Path) -> None:
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", "touch started; sleep 30"))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    running(launcher, native_id)
    pane = (fake_tmux / "sessions" / native_id).read_text().split()[0]
    # A person attached to the session presses Ctrl-C.
    subprocess.run([str(FAKE), "send-keys", "-t", pane, "C-c"], check=True)
    report = ended(launcher, native_id)
    assert report.exit_code == 130 and report.failure is None


def test_cancel_interrupt_then_term(runs_root: Path, fake_tmux: Path) -> None:
    body = (
        "trap 'echo int >> got' INT; trap 'echo term >> got' TERM; touch started; "
        "while :; do sleep 0.05; done"
    )
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    running(launcher, native_id)
    got = spec.launch_dir / "got"
    launcher.cancel(native_id, grace_s=0)
    wait_for(lambda: got.exists() and "int" in got.read_text())
    assert "term" not in got.read_text()  # the interrupt first, alone
    report = ended(launcher, native_id)  # INT and TERM ignored: SIGKILL after the grace
    assert got.read_text().split() == ["int", "term"]
    assert report.exit_code is None  # killed: no head.exit


def test_cancel_waits_for_the_grace(runs_root: Path, fake_tmux: Path) -> None:
    body = "trap 'echo int >> got' INT; touch started; while :; do sleep 0.05; done"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    running(launcher, native_id)
    launcher.cancel(native_id, grace_s=60)
    wait_for(lambda: (spec.launch_dir / "got").exists())
    for _ in range(5):
        assert launcher.poll([native_id])[native_id].state == "running"  # no TERM before 60 s
    launcher.cancel(native_id, grace_s=0)  # a second cancel: the grace already started
    assert launcher.poll([native_id])[native_id].state == "running"


def test_targets_exact_and_pane_id(runs_root: Path, fake_tmux: Path) -> None:
    body = "trap '' INT; touch started; while :; do sleep 0.05; done"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    TmuxLauncher(str(FAKE)).adopt(ref_for(spec, native_id))
    running(launcher, native_id)
    launcher.cancel(native_id, grace_s=0)
    ended(launcher, native_id)
    made = calls(fake_tmux)
    targets = [c[c.index("-t") + 1] for c in made if "-t" in c]
    pane = "%" + (fake_tmux / "panes").read_text()  # the pane ID new-session printed
    assert targets and set(targets) <= {f"=spectio-{RUN_A}", pane}
    assert [c for c in made if c[0] == "send-keys"] == [["send-keys", "-t", pane, "C-c"]]


def test_argv_never_single_string(
    runs_root: Path, fake_tmux: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, dict[str, object]]] = []
    real = subprocess.run

    def spy(argv: object, **kwargs: Any) -> Any:
        seen.append((argv, kwargs))
        return real(argv, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr("spectio.runner.tmux.subprocess.run", spy)
    body = "touch started; sleep 30"
    spec = spec_for(runs_root, stub_engine(runs_root.parent / "bin", body))
    launcher = TmuxLauncher(str(FAKE))
    native_id = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    launcher.adopt(ref_for(spec, native_id))
    launcher.cancel(native_id, grace_s=0)
    ended(launcher, native_id)
    assert seen
    for argv, kwargs in seen:
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        assert argv[0] == str(FAKE) and not kwargs.get("shell")
        env = kwargs["env"]
        assert isinstance(env, dict) and not any(k.startswith("SPECTIO_") for k in env)
        assert "TMUX" not in env  # the user's default server, not the one of any calling pane
