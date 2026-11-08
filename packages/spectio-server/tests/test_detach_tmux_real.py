"""`spectio serve --detach` with a real tmux (FU-P3-44): `pytest -m tmux`, skipped where no tmux
is on PATH. The tmux server is private to the test (its own `TMUX_TMPDIR`, so its own socket)
and killed at the end. `--detach` starts that tmux server, which reads a `~/.tmux.conf` as a
user's could be: a global `SPECTIO_PORT` and `destroy-unattached on`, which ends a detached
session at once unless the same call turns it off for the session (tmux 3.4, reproduced)."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings

TMUX = shutil.which("tmux")
pytestmark = [
    pytest.mark.tmux,
    pytest.mark.skipif(TMUX is None, reason="no tmux on PATH"),
]


def wait_for(pred: Callable[[], object], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


@pytest.fixture
def tmux(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., str]]:
    """`tmux(*args)` on a tmux server of the test's own; a short socket path (108 bytes)."""
    sockets = tempfile.mkdtemp(prefix="sp-det-")
    monkeypatch.setenv("TMUX_TMPDIR", sockets)
    monkeypatch.delenv("TMUX", raising=False)

    def run(*args: str) -> str:
        done = subprocess.run([str(TMUX), *args], capture_output=True, text=True, check=False)
        return done.stdout

    yield run
    run("kill-server")
    shutil.rmtree(sockets, ignore_errors=True)


def test_real_tmux_detach_roundtrip(
    settings: Settings, tmux: Callable[..., str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mark = tmp_path / "mark"
    conf = "set-environment -g SPECTIO_PORT 1\nset-option -g destroy-unattached on\n"
    (Path.home() / ".tmux.conf").write_text(conf)  # SEC-PRE-01, CON-PRE-05
    odd = f"-Xmx2g #(touch {mark}) #{{session_name}}"  # tmux formats: arrive literally (SEC-PRE-06)
    monkeypatch.setenv("SPECTIO_ENGINES_NXF_OPTS", odd)

    result = CliRunner().invoke(app, ["serve", "--detach"])
    assert result.exit_code == 0, result.output
    port = settings.port
    assert re.search(rf"http://127\.0\.0\.1:{port}/auth/link#[A-Za-z0-9_-]{{43}}", result.stdout)

    (line,) = tmux("list-panes", "-s", "-t", "=spectio-server", "-F", "#{pane_pid}").split()
    pane_pid = int(line)
    record = json.loads((settings.data_dir / "server.json").read_text())
    assert record["pid"] == pane_pid and record["port"] == port  # argv: no sh -c; not port 1
    environ = Path(f"/proc/{pane_pid}/environ").read_bytes().split(b"\0")
    assert f"SPECTIO_ENGINES_NXF_OPTS={odd}".encode() in environ
    assert not [v for v in environ if v.startswith((b"SPECTIO_PORT=", b"TMUX="))]
    assert not mark.exists()

    start = tmux("list-panes", "-s", "-t", "=spectio-server", "-F", "#{pane_start_command}")
    assert settings.db_dir is not None
    key = (settings.db_dir / "server.key").read_text().strip()
    wait_for(lambda: "is running on" in tmux("capture-pane", "-p", "-t", "=spectio-server:"))
    screen = tmux("capture-pane", "-p", "-J", "-S", "-", "-t", "=spectio-server:")
    for text in (start, screen):
        assert "auth/link#" not in text and key not in text  # req. 11, SEC-PRE-05

    time.sleep(1)  # destroy-unattached on: the session stays
    assert "spectio-server" in tmux("list-sessions", "-F", "#{session_name}").split()

    again = CliRunner().invoke(app, ["serve", "--detach"])  # idempotent: a new link
    assert again.exit_code == 0, again.output
    assert again.stdout != result.stdout

    tmux("kill-session", "-t", "=spectio-server")  # the stop: SIGHUP, a clean one
    wait_for(lambda: not (settings.data_dir / "server.json").exists())
    wait_for(lambda: not os.path.exists(f"/proc/{pane_pid}"))
