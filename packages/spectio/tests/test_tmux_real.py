"""The tmux launcher with a real tmux (P1 Task 10): `pytest -m tmux`, skipped where no tmux is on
PATH. The tmux server is private to the test (`TMUX_TMPDIR`) and killed at the end."""

import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from spectio.runner.rundir import make_run_dirs
from spectio.runner.tmux import TmuxLauncher
from spectio.runner.types import HeadReport, LaunchRef, LaunchSpec

TMUX = shutil.which("tmux")
pytestmark = [
    pytest.mark.tmux,
    pytest.mark.skipif(TMUX is None, reason="no tmux on PATH"),
]
RUN_A = "run_01K8T9TMXX0000000000000R0A"
ENGINE = """#!/bin/bash
case "$1" in -version) echo "      version 26.10.4 build 5960"; exit 0;; esac
touch started; exec sleep 60
"""


def wait_for(pred: Callable[[], object], timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


@pytest.fixture
def server(
    home: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[..., subprocess.CompletedProcess[str]]]:
    """`tmux(*args)` on a tmux server of the test's own; a short socket path (108 bytes)."""
    sockets = tempfile.mkdtemp(prefix="sp-tmux-")
    monkeypatch.setenv("TMUX_TMPDIR", sockets)
    monkeypatch.delenv("TMUX", raising=False)
    bridges = home / "bridges" / "nf-spectio-0.0.1"
    bridges.mkdir(parents=True)
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(bridges.parent))
    monkeypatch.setenv("NXF_HOME", str(home / ".nextflow"))
    login(Path("/usr/bin"), Path("/bin"))

    def tmux(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(TMUX), *args], capture_output=True, text=True, check=False)

    yield tmux
    tmux("kill-server")
    shutil.rmtree(sockets, ignore_errors=True)


def test_real_tmux_roundtrip(
    home: Path, server: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    root = home / "runs"
    root.mkdir(mode=0o700)
    engine = home / "bin" / "engine"
    engine.parent.mkdir()
    engine.write_text(ENGINE)
    engine.chmod(0o755)
    paths = make_run_dirs(root, RUN_A)
    spec = LaunchSpec(
        run_id=RUN_A,
        launch_n=1,
        engine="nextflow",
        engine_cmd=shlex.quote(str(engine)),
        location=home / "pipeline",
        launch_dir=paths.launch_dir,
        work_dir=paths.work_dir,
    )
    launcher = TmuxLauncher(str(TMUX))
    session = launcher.submit(spec)
    wait_for((spec.launch_dir / "started").exists)
    assert session in server("ls", "-F", "#{session_name}").stdout.split()  # attach-able
    # The head leads the pane's process group, the terminal's foreground group.
    (pane_pid,) = server("list-panes", "-t", f"={session}", "-F", "#{pane_pid}").stdout.split()
    fields = Path(f"/proc/{pane_pid}/stat").read_text().rsplit(") ", 1)[1].split()
    pgid, tpgid = fields[2], fields[5]
    assert pgid == pane_pid == tpgid
    head_pid = (spec.launch_dir / ".spectio" / "head.pid").read_text().split()
    assert head_pid[:2] == [pane_pid, pane_pid]
    # A server restart: a new launcher adopts the head by its session and the PID check.
    fresh = TmuxLauncher(str(TMUX))
    ref = LaunchRef("lch_1", RUN_A, 1, "nextflow", spec.launch_dir, session)
    assert fresh.adopt(ref).state == "running"
    fresh.cancel(session, grace_s=60)  # send-keys C-c: the engine stops at once
    found: list[HeadReport] = []

    def ended() -> bool:
        found.append(fresh.poll([session])[session])
        return found[-1].ended

    wait_for(ended)
    assert found[-1].state == "exited" and found[-1].exit_code == 130
    code = (spec.launch_dir / ".spectio" / "head.exit").read_text().split()[0]
    assert code == "130"
    wait_for(lambda: session not in server("ls", "-F", "#{session_name}").stdout.split())
