"""`spectio serve --detach` with the fake tmux of `packages/spectio/tests/fakebin` (FU-P3-44;
dev-env §15.3 req. 11; schedulers §3.1.1). The pane runs the real
`python -P -m spectio serve --pane`; the link prints in the calling terminal, never in the pane."""

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from spectio.cli import login
from spectio.cli.main import app
from spectio.config import Settings
from spectio_server.serve import start_text, started

FAKE = Path(__file__).resolve().parents[2] / "spectio" / "tests" / "fakebin" / "tmux"
SESSION = "spectio-server"
PANE_TAIL = [sys.executable, "-P", "-m", "spectio", "serve", "--pane"]


def wait_for(pred: Callable[[], object], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            pytest.fail("timed out")
        time.sleep(0.05)


def link_re(port: int) -> re.Pattern[str]:
    return re.compile(rf"http://127\.0\.0\.1:{port}/auth/link#[A-Za-z0-9_-]{{43}}")


class Tmux:
    """The fake's state directory and what it logged."""

    def __init__(self, state: Path) -> None:
        self.state = state

    def calls(self) -> list[list[str]]:
        path = self.state / "calls.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    def commands(self) -> list[str]:
        return [c[0] for c in self.calls()]

    def new_session(self) -> list[str]:
        (call,) = [c for c in self.calls() if c[0] == "new-session"]
        return call

    def pane(self, name: str = SESSION) -> tuple[str, int] | None:
        path = self.state / "sessions" / name
        if not path.exists():
            return None
        pane, pid = path.read_text().split()
        return pane, int(pid)

    def out(self, name: str = SESSION) -> str:
        path = self.state / f"{name}.out"
        return path.read_text(errors="replace") if path.exists() else ""

    def start(self, *argv: str, name: str = SESSION) -> int:
        """A session made by someone else, before `--detach` runs."""
        tmux = str(self.state.parent / "tmuxbin" / "tmux")
        made = subprocess.run(
            [tmux, "new-session", "-d", "-s", name, "-c", "/", *argv],
            capture_output=True,
            text=True,
            check=True,
        )
        assert made.returncode == 0
        found = self.pane(name)
        assert found is not None
        return found[1]


def _alive(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[0] != "Z"
    except OSError:
        return False


@pytest.fixture
def tmux(settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Tmux]:
    """The fake tmux first on PATH, its state in `$TMUX_TMPDIR`; every pane stopped at the end."""
    state = tmp_path / "tmux"
    state.mkdir()
    bindir = tmp_path / "tmuxbin"
    bindir.mkdir()
    shutil.copy(FAKE, bindir / "tmux")
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("TMUX_TMPDIR", str(state))
    monkeypatch.delenv("TMUX", raising=False)
    fake = Tmux(state)
    yield fake
    pids = [int(p.read_text().split()[1]) for p in (state / "sessions").glob("*")]
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 20
    while any(_alive(pid) for pid in pids) and time.monotonic() < deadline:
        time.sleep(0.05)
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def detach(*args: str) -> Any:
    return CliRunner().invoke(app, ["serve", "--detach", *args])


def plain(text: str) -> str:
    """Rich colours usage errors on CI (GITHUB_ACTIONS forces a terminal): drop the escapes."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def state_file(settings: Settings, **record: Any) -> None:
    body = {
        "host": login.hostname(),
        "port": settings.port,
        "pid": 1,
        "db_dir": str(settings.db_dir),
        "started_at": "2026-01-01T00:00:00+00:00",
    }
    path = settings.data_dir / "server.json"
    path.write_text(json.dumps({**body, **record}))
    path.chmod(0o600)


def test_detach_starts_tmux_session(settings: Settings, tmux: Tmux) -> None:
    result = detach()
    assert result.exit_code == 0, result.output
    call = tmux.new_session()
    assert call[:7] == ["new-session", "-d", "-P", "-F", call[4], "-s", SESSION]
    assert call[7:9] == ["-c", "/"]  # -c is a format: never a path of ours (SEC-P3T10-01)
    assert call[9:11] == ["/usr/bin/env", "-i"]  # an absolute env, a clean environment
    semi = call.index(";")
    assert call[semi - len(PANE_TAIL) : semi] == PANE_TAIL
    # in the same call: a global destroy-unattached never ends the session (CON-PRE-05)
    assert call[semi:] == [";", "set-option", "-t", f"={SESSION}:", "destroy-unattached", "off"]
    found = tmux.pane()
    assert found is not None and _alive(found[1])
    record = json.loads((settings.data_dir / "server.json").read_text())
    assert record["pid"] == found[1]  # the pane's PID is the server's (argv, no sh -c)
    assert "kill-session" not in tmux.commands()


def test_detach_link_in_calling_terminal_not_in_pane(settings: Settings, tmux: Tmux) -> None:
    result = detach()
    assert result.exit_code == 0, result.output
    assert link_re(settings.port).search(result.stdout), result.stdout
    assert "tmux attach -t spectio-server" in result.stdout
    assert "spectio login --print-link" in result.stdout
    wait_for(lambda: "is running on" in tmux.out())
    pane_text = tmux.out()
    assert "auth/link#" not in pane_text  # req. 11: never in the pane (SEC-PRE-05)
    assert settings.db_dir is not None
    key = (settings.db_dir / "server.key").read_text().strip()
    assert key and key not in pane_text
    assert all(key not in word and "auth/link" not in word for word in tmux.new_session())


def test_detach_waits_for_its_own_server_json(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale server.json of this node, naming a live process that is not the pane: the link
    is asked only of the server whose PID is the pane's (SEC-PRE-03, SEC-PRE-04)."""
    state_file(settings, pid=os.getpid(), started_at="2099-01-01T00:00:00+00:00")
    before = (settings.data_dir / "server.json").read_bytes()
    seen: list[int] = []
    real = login.new_link

    def spy(found: Settings, timeout: float = 10) -> str:
        seen.append(json.loads((found.data_dir / "server.json").read_text())["pid"])
        return real(found, timeout)

    monkeypatch.setattr(login, "new_link", spy)
    result = detach()
    assert result.exit_code == 0, result.output
    found = tmux.pane()
    assert found is not None
    assert seen[0] == os.getpid()  # step 2: is a server running already? (nothing listens)
    assert seen[1:] and set(seen[1:]) == {found[1]}
    assert (settings.data_dir / "server.json").read_bytes() != before  # the child replaced it


@pytest.fixture
def running_server(settings: Settings) -> Iterator[Settings]:
    with started(settings) as server:
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        wait_for(lambda: server.uvicorn.started, 20)
        try:
            yield settings
        finally:
            server.uvicorn.should_exit = True
            thread.join(20)


def test_detach_already_running_prints_new_link_exit_0(
    running_server: Settings, tmux: Tmux
) -> None:
    result = detach()
    assert result.exit_code == 0, result.output
    assert link_re(running_server.port).search(result.stdout)
    assert tmux.commands() == ["-V"]  # no session started or looked for


def test_detach_existing_session_is_waited_never_killed(settings: Settings, tmux: Tmux) -> None:
    """Another detach's pane that has not written server.json yet: waited for, never killed."""
    pid = tmux.start(sys.executable, "-c", "import time; time.sleep(60)", *PANE_TAIL[2:])
    result = detach("--wait", "1")
    assert result.exit_code == 3, result.output
    assert "still starting" in result.output and "spectio login --print-link" in result.output
    assert [c for c in tmux.commands() if c == "new-session"] == ["new-session"]  # the test's
    assert "kill-session" not in tmux.commands()
    assert _alive(pid)


def test_detach_session_running_something_else_exits_2(settings: Settings, tmux: Tmux) -> None:
    """A live pane that is not `spectio serve --pane` (CON-PRE-04): refused, not killed."""
    pid = tmux.start("sleep", "60")
    result = detach()
    assert result.exit_code == 2, result.output
    assert "tmux attach -t spectio-server" in result.output
    assert "kill-session" not in tmux.commands()
    assert _alive(pid)


def test_detach_session_of_dead_panes_is_replaced(settings: Settings, tmux: Tmux) -> None:
    """remain-on-exit on: a session whose panes all ended is the one kill (CON-PRE-04)."""
    (tmux.state / "remain").touch()
    dead = tmux.start("true")
    wait_for(lambda: not _alive(dead))
    result = detach()
    assert result.exit_code == 0, result.output
    pane = tmux.pane()
    assert pane is None or pane[1] != dead
    assert "kill-session" not in tmux.commands()
    (call,) = [c for c in tmux.calls() if c[0] == "kill-pane"]  # by pane ID (CR-P3FU44-01)
    assert call[1] == "-t" and re.fullmatch(r"%[0-9]+", call[2])
    found = tmux.pane()
    assert found is not None and found[1] != dead and _alive(found[1])


@pytest.mark.parametrize("listed", ["garbage\n", "", "%0 123 1\nnot a pane\n"])
def test_detach_unparseable_list_panes_kills_nothing(
    settings: Settings, tmux: Tmux, listed: str
) -> None:
    """An output it cannot parse (another tmux build): exit 2, nothing killed (SEC-P3FU44-03,
    CR-P3FU44-01)."""
    pid = tmux.start(sys.executable, "-c", "import time; time.sleep(60)", *PANE_TAIL[2:])
    (tmux.state / "panes.out").write_text(listed)
    result = detach()
    assert result.exit_code == 2, result.output
    assert "list-panes" in result.output
    assert not {"kill-session", "kill-pane", "new-session"} & set(tmux.commands()[1:])
    assert _alive(pid)


def test_detach_child_exits_at_start_exits_2(settings: Settings, tmux: Tmux) -> None:
    settings.runs_root.chmod(0o777)  # the child refuses: req. 10
    result = detach()
    assert result.exit_code == 2, result.output
    assert "runs root" in result.output  # the child's own refusal, from serve-detach.err
    assert "stopped at start" in result.output
    assert tmux.pane() is None


def test_detach_timeout_exits_3_session_left(settings: Settings, tmux: Tmux) -> None:
    result = detach("--wait", "0.05")  # no server boots in 50 ms
    assert result.exit_code == 3, result.output
    assert "still starting" in result.output
    found = tmux.pane()
    assert found is not None and _alive(found[1])
    assert "kill-session" not in tmux.commands()


def test_detach_other_node_refused_without_force(settings: Settings, tmux: Tmux) -> None:
    state_file(settings, host="login3")
    result = detach()
    assert result.exit_code == 2, result.output
    assert "login3" in result.output
    assert "new-session" not in tmux.commands()


def test_detach_force_passed_to_pane(settings: Settings, tmux: Tmux) -> None:
    state_file(settings, host="login3")
    result = detach("--force")
    assert result.exit_code == 0, result.output
    call = tmux.new_session()
    semi = call.index(";")
    assert call[semi - 7 : semi] == [*PANE_TAIL, "--force"]
    assert json.loads((settings.data_dir / "server.json").read_text())["host"] != "login3"


def test_detach_forwards_spectio_env_as_argv(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An allow-list, as `NAME=value` words of `env -i` (SEC-PRE-01, CON-PRE-03)."""
    monkeypatch.setenv("SPECTIO_RUNNER_SPOOL_S", "3")
    monkeypatch.setenv("SPECTIO_BOGUS", "x")
    monkeypatch.setenv("TMUX", "/run/elsewhere,1,0")
    monkeypatch.setenv("LD_PRELOAD", "/nope.so")
    result = detach()
    assert result.exit_code == 0, result.output
    call = tmux.new_session()
    words = call[11 : call.index(sys.executable)]
    assert "SPECTIO_RUNNER_SPOOL_S=3" in words
    assert f"SPECTIO_CONFIG={os.environ['SPECTIO_CONFIG']}" in words
    assert f"HOME={os.environ['HOME']}" in words and f"PATH={os.environ['PATH']}" in words
    assert f"TMUX_TMPDIR={tmux.state}" in words
    names = {word.partition("=")[0] for word in words}
    assert not names & {"SPECTIO_BOGUS", "TMUX", "LD_PRELOAD"}


def test_detach_relative_spectio_config_made_absolute(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pane runs in `/`: a relative SPECTIO_CONFIG is forwarded as the path the caller
    read (SEC-P3FU44-02)."""
    config = Path(os.environ["SPECTIO_CONFIG"])
    monkeypatch.chdir(config.parent)
    monkeypatch.setenv("SPECTIO_CONFIG", config.name)
    result = detach()
    assert result.exit_code == 0, result.output
    call = tmux.new_session()
    assert f"SPECTIO_CONFIG={config}" in call[11 : call.index(sys.executable)]


@pytest.mark.parametrize("wait", ["nan", "inf", "-inf", "3601"])
def test_detach_wait_must_be_finite(settings: Settings, tmux: Tmux, wait: str) -> None:
    """nan would make the deadline never pass (SEC-P3FU44-04)."""
    result = detach("--wait", wait)
    assert result.exit_code == 2, result.output
    assert "--wait" in plain(result.output)
    assert tmux.calls() == []


@pytest.mark.parametrize("args", [["--wait", "5"], ["--no-link"]])
def test_wait_and_no_link_need_detach(settings: Settings, tmux: Tmux, args: list[str]) -> None:
    """Never silently ignored: without --detach, they are refused (CR-P3FU44-05)."""
    result = CliRunner().invoke(app, ["serve", *args])
    assert result.exit_code == 2, result.output
    assert "--detach" in plain(result.output)
    assert not (settings.data_dir / "server.json").exists()


def test_detach_refuses_a_word_tmux_would_split(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tmux splits commands on an argument that ends in `;` (tmux 3.4, reproduced)."""
    monkeypatch.setenv("SPECTIO_ENGINES_NXF_OPTS", "-Xmx2g;")
    result = detach()
    assert result.exit_code == 2, result.output
    assert "SPECTIO_ENGINES_NXF_OPTS" in result.output
    assert "new-session" not in tmux.commands()


def test_detach_no_tmux_exits_2(
    settings: Settings, tmux: Tmux, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    result = detach()
    assert result.exit_code == 2, result.output
    assert "tmux" in result.output
    assert tmux.calls() == []


def test_detach_old_tmux_exits_2(settings: Settings, tmux: Tmux) -> None:
    (tmux.state / "version").write_text("tmux 2.0")
    result = detach()
    assert result.exit_code == 2, result.output
    assert "2.1" in result.output
    assert tmux.commands() == ["-V"]


def test_detach_tmux_failure_exits_2_with_its_stderr(settings: Settings, tmux: Tmux) -> None:
    """Only "no such session" means none (SEC-PRE-07): any other failure stops, nothing else
    is tried."""
    (tmux.state / "fail").write_text("server exited unexpectedly")
    result = detach()
    assert result.exit_code == 2, result.output
    assert "server exited unexpectedly" in result.output
    assert "new-session" not in tmux.commands()


def test_detach_listener_ours_without_link_waits(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    """server.json of this node and a listener of ours that gives no link yet (it is booting,
    CON-PRE-01): waited for, no second server started."""
    state_file(settings)
    with socket.create_server(("127.0.0.1", settings.port)):
        result = detach("--wait", "1")
    assert result.exit_code == 3, result.output
    assert "new-session" not in tmux.commands() and "list-panes" not in tmux.commands()


def test_detach_port_held_by_another_uid_exits_2(
    settings: Settings, tmux: Tmux, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_file(settings)
    monkeypatch.setattr(login, "port_owners", lambda port: {os.getuid() + 1})
    result = detach()
    assert result.exit_code == 2, result.output
    assert f"uid {os.getuid() + 1}" in result.output
    assert "new-session" not in tmux.commands()


def test_two_concurrent_detach_one_session_two_links(settings: Settings, tmux: Tmux) -> None:
    """SEC-PRE-08: the loser of the race waits for the winner's server; nothing is killed."""
    argv = [sys.executable, "-P", "-m", "spectio", "serve", "--detach"]
    procs = [
        subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    outs = [p.communicate(timeout=120) for p in procs]
    assert [p.returncode for p in procs] == [0, 0], outs
    links = {link_re(settings.port).search(out)[0] for out, _ in outs}  # type: ignore[index]
    assert len(links) == 2
    assert len(list((tmux.state / "sessions").glob("*"))) == 1
    assert "kill-session" not in tmux.commands()


def test_pane_start_text_has_no_link(settings: Settings) -> None:
    for executor in ("local", "slurm"):
        found = settings.model_copy(update={"executor": executor})
        text = start_text(found, "node1", "alice", None, None)
        assert "auth/link" not in text
        assert "spectio login --print-link" in text
    with started(settings, mint_link=False) as server:  # --pane mints no ticket (SEC-PRE-05)
        assert server.link is None


def test_python_m_spectio() -> None:
    done = subprocess.run(
        [sys.executable, "-P", "-m", "spectio", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0 and done.stdout.startswith("spectio "), done
