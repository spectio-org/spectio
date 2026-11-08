"""On SLURM and on a shared host, `spectio serve` listens only on a Unix socket in its 0700
database directory, never on a TCP port; local mode on a machine only the user uses keeps TCP
(inbox #109 rule 5, decided by Thomas 2026-11-08; dev-env §15.3 req. 1, note 2026-11-08;
FU-P3-72). The session stays as a second barrier behind the socket."""

import http.client
import json
import os
import socket
import stat
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from spectio.cli import login
from spectio.cli.main import app as cli_app
from spectio.config import Settings
from spectio.ports import SOCKET, SUN_PATH_MAX
from spectio_server import app as app_mod
from spectio_server.app import create_app
from spectio_server.serve import STATE, ServeError, Started, start_text, started
from spectio_server.store.writer import Writer

EXCHANGE = "/api/v1/auth/magic-links:exchange"


class UnixHTTP(http.client.HTTPConnection):
    """HTTP over the server's socket, as the SSH tunnel carries it: `Host` stays the laptop's
    `127.0.0.1:<port>`."""

    def __init__(self, path: Path, port: int) -> None:
        super().__init__("127.0.0.1", port, timeout=10)
        self.socket_path = str(path)

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def ask(
    path: Path,
    port: int,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> http.client.HTTPResponse:
    conn = UnixHTTP(path, port)
    conn.request(method, url, body=body, headers=headers or {})
    return conn.getresponse()


def slurm(settings: Settings) -> Settings:
    return settings.model_copy(update={"executor": "slurm"})


def serving(server: Started) -> threading.Thread:
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.uvicorn.started:
        assert time.monotonic() < deadline, "the server did not start"
        time.sleep(0.05)
    return thread


@pytest.fixture
def on_socket(settings: Settings) -> Iterator[Started]:
    """`spectio serve` of a SLURM environment, serving."""
    with started(slurm(settings)) as server:
        thread = serving(server)
        try:
            yield server
        finally:
            server.uvicorn.should_exit = True
            thread.join(20)


def _tcp_listeners(port: int) -> int:
    count = 0
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        if table.exists():
            for line in table.read_text().splitlines()[1:]:
                fields = line.split()
                if int(fields[1].rsplit(":", 1)[1], 16) == port and fields[3] == "0A":
                    count += 1
    return count


def test_slurm_listens_on_a_socket_in_the_db_dir_only(
    settings: Settings, on_socket: Started
) -> None:
    assert settings.db_dir is not None
    path = settings.db_dir / SOCKET
    assert on_socket.sock.family == socket.AF_UNIX
    assert on_socket.sock.getsockname() == str(path)
    assert stat.S_ISSOCK(path.lstat().st_mode)
    assert stat.S_IMODE(path.lstat().st_mode) & 0o077 == 0  # 0600 or tighter
    assert stat.S_IMODE(settings.db_dir.stat().st_mode) == 0o700  # the boundary
    assert _tcp_listeners(settings.port) == 0  # never a TCP port (inbox #109 rule 5)
    record = json.loads((settings.data_dir / STATE).read_text())
    assert record["socket"] == str(path)
    assert record["port"] == settings.port  # the laptop's end of the tunnel


def test_the_api_and_screens_are_served_behind_the_socket(
    settings: Settings, on_socket: Started
) -> None:
    """The session stays a second barrier; the Host of the tunnel (`127.0.0.1:<port>` or
    `localhost:<port>`) passes the allow-list, and names the cookie."""
    assert settings.db_dir is not None
    path, port = settings.db_dir / SOCKET, settings.port
    assert on_socket.no_api is None
    assert ask(path, port, "GET", "/api/v1/runs").status == 401  # signed out
    assert ask(path, port, "GET", "/", {"Host": "evil.example"}).status == 400
    origin = f"http://127.0.0.1:{port}"
    ticket = on_socket.link.partition("#")[2] if on_socket.link else ""
    body = json.dumps({"ticket": ticket}).encode()
    headers = {"Origin": origin, "Content-Type": "application/json"}
    answer = ask(path, port, "POST", EXCHANGE, headers, body=body)
    assert answer.status == 204
    cookie = answer.getheader("set-cookie") or ""
    assert cookie.startswith(f"spectio_session_{port}=")  # the laptop's port (req. 3)
    session = {"Cookie": cookie.split(";")[0]}
    runs = ask(path, port, "GET", "/api/v1/runs", session)
    assert runs.status == 200, runs.read()
    local = ask(path, port, "GET", "/api/v1/runs", {**session, "Host": f"localhost:{port}"})
    assert local.status == 200  # the other loopback name of the tunnel's end (req. 4)


def test_the_event_stream_flows_over_the_socket(settings: Settings, on_socket: Started) -> None:
    assert settings.db_dir is not None
    app = on_socket.uvicorn.config.app
    assert isinstance(app, FastAPI)
    secret = app.state.sessions.create()
    conn = UnixHTTP(settings.db_dir / SOCKET, settings.port)
    conn.request(
        "GET",
        "/api/v1/events/stream",
        headers={"Cookie": f"spectio_session_{settings.port}={secret}"},
    )
    answer = conn.getresponse()
    assert answer.status == 200
    assert answer.getheader("content-type", "").startswith("text/event-stream")
    assert answer.read1(64)  # the first keep-alive frame
    conn.close()


def test_socket_removed_at_stop(settings: Settings) -> None:
    assert settings.db_dir is not None
    with started(slurm(settings)):
        assert (settings.db_dir / SOCKET).exists()
    assert not (settings.db_dir / SOCKET).exists()


def test_start_text_gives_the_tunnel_to_the_socket(settings: Settings) -> None:
    sock = Path("/tmp/spectio-1000/spectio.sock")  # noqa: S108
    link = f"http://127.0.0.1:{settings.port}/auth/link#" + "t" * 43
    text = start_text(slurm(settings), "login1", "alice", None, link, sock)
    assert f"running on login1, on the Unix socket {sock}." in text
    assert f"ssh -N -L 127.0.0.1:{settings.port}:{sock} alice@login1" in text
    assert f"2. Then open this link (single use, valid 15 minutes):\n   {link}\n" in text
    assert "spectio init --local" not in text  # the API is served
    shared = start_text(settings, "ws1", "alice", None, link, sock)  # local mode, shared host
    assert f"ssh -N -L 127.0.0.1:{settings.port}:{sock} alice@ws1" in shared
    assert "tmux attach" not in shared


def test_loose_db_dir_refused_and_left_as_it_is(settings: Settings) -> None:
    assert settings.db_dir is not None
    settings.db_dir.chmod(0o755)
    with pytest.raises(ServeError, match="0700"), started(slurm(settings)):
        pass
    assert stat.S_IMODE(settings.db_dir.stat().st_mode) == 0o755  # refused, nothing changed
    assert not (settings.db_dir / SOCKET).exists()
    assert not (settings.data_dir / STATE).exists()


def test_squatted_default_db_dir_refused_behind_a_socket(
    settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guide's tunnel names /tmp/spectio-<uid>/spectio.sock: a squatted default directory
    is refused behind a socket, never swapped for a mkdtemp one (SEC-P3FU72-01)."""
    base = tmp_path / "tmp"
    base.mkdir(mode=0o700)
    monkeypatch.setenv("TMPDIR", str(base))
    squatted = base / f"spectio-{os.getuid()}"
    squatted.mkdir(mode=0o755)
    found = slurm(settings).model_copy(update={"db_dir": None})
    with pytest.raises(ServeError, match=rf"{squatted}.*uid {os.getuid()}.*--db-dir"):
        with started(found):
            pass
    assert sorted(p.name for p in base.iterdir()) == [squatted.name]  # no fallback, no socket
    assert not any(squatted.iterdir())
    assert not (settings.data_dir / STATE).exists()


def test_stale_socket_replaced(settings: Settings) -> None:
    """A socket file a dead server left: nothing answers on it, so it is removed and bound."""
    assert settings.db_dir is not None
    path = settings.db_dir / SOCKET
    dead = socket.socket(socket.AF_UNIX)
    dead.bind(str(path))
    dead.close()  # the file stays, nothing listens
    with started(slurm(settings)) as server:
        assert server.sock.getsockname() == str(path)


def test_live_socket_refused(settings: Settings) -> None:
    assert settings.db_dir is not None
    path = settings.db_dir / SOCKET
    with socket.socket(socket.AF_UNIX) as live:
        live.bind(str(path))
        live.listen()
        with pytest.raises(ServeError, match="answers"), started(slurm(settings)):
            pass
        assert path.exists()  # kept
    assert not (settings.data_dir / STATE).exists()


def test_not_a_socket_refused(settings: Settings) -> None:
    assert settings.db_dir is not None
    path = settings.db_dir / SOCKET
    path.write_text("mine")
    with pytest.raises(ServeError, match="not a socket"), started(slurm(settings)):
        pass
    assert path.read_text() == "mine"


def test_path_too_long_for_af_unix_refused(settings: Settings, tmp_path: Path) -> None:
    deep = tmp_path / ("d" * (SUN_PATH_MAX - len(str(tmp_path))))
    deep.mkdir(mode=0o700)
    found = slurm(settings).model_copy(update={"db_dir": deep})
    with pytest.raises(ServeError, match=rf"{SUN_PATH_MAX} bytes.*--db-dir"), started(found):
        pass
    assert not (settings.data_dir / STATE).exists()


def test_shared_host_in_local_mode_goes_behind_a_socket(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_mod, "shared_host", lambda: "a process of uid 1001 runs here")
    assert settings.executor == "local" and settings.db_dir is not None
    with started(settings) as server:
        assert server.sock.family == socket.AF_UNIX
        assert server.no_api is None
        assert _tcp_listeners(settings.port) == 0


def test_lone_machine_in_local_mode_keeps_tcp(settings: Settings) -> None:
    assert settings.db_dir is not None
    with started(settings) as server:
        assert server.sock.family == socket.AF_INET
        assert server.sock.getsockname() == ("127.0.0.1", settings.port)
        assert not (settings.db_dir / SOCKET).exists()
        assert json.loads((settings.data_dir / STATE).read_text())["socket"] is None


@pytest.mark.parametrize("executor", ["local", "slurm"])
def test_tcp_never_mounts_the_api_on_a_shared_host(
    settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch, executor: str
) -> None:
    """Whatever the caller asks: on TCP, a SLURM environment or a shared host gets no API and no
    screens; behind the socket it gets both."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: "a process of uid 1001 runs here")
    found = settings.model_copy(update={"executor": executor})
    origin = f"http://127.0.0.1:{settings.port}"
    for on_socket, status in ((False, 404), (True, 200)):
        app = create_app(found, writer, on_socket=on_socket)
        client = TestClient(app, base_url=origin, headers={"Origin": origin})
        client.cookies.set(f"spectio_session_{settings.port}", app.state.sessions.create())
        assert client.get("/api/v1/version").status_code == status, on_socket


def test_login_print_link_over_the_socket(settings: Settings, on_socket: Started) -> None:
    assert settings.db_dir is not None
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 0, result.output
    url = result.stdout.strip()
    assert url.startswith(f"http://127.0.0.1:{settings.port}/auth/link#")
    body = json.dumps({"ticket": url.partition("#")[2]}).encode()
    origin = f"http://127.0.0.1:{settings.port}"
    headers = {"Origin": origin, "Content-Type": "application/json"}
    path = settings.db_dir / SOCKET
    assert ask(path, settings.port, "POST", EXCHANGE, headers, body=body).status == 204
    assert login.server_socket(settings) == path


def _state(settings: Settings, **record: object) -> None:
    body = {
        "host": login.hostname(),
        "port": settings.port,
        "pid": 1,
        "db_dir": str(settings.db_dir),
        "socket": str(settings.db_dir / SOCKET) if settings.db_dir else None,
    }
    path = settings.data_dir / STATE
    path.write_text(json.dumps({**body, **record}))
    path.chmod(0o600)


def test_login_refuses_a_socket_outside_the_db_dir(settings: Settings, tmp_path: Path) -> None:
    _state(settings, socket=str(tmp_path / SOCKET))
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2
    assert "socket" in result.output


def test_login_refuses_a_socket_file_that_is_not_one(settings: Settings) -> None:
    assert settings.db_dir is not None
    _state(settings)
    (settings.db_dir / "server.key").write_text("k" * 43)
    (settings.db_dir / "server.key").chmod(0o600)
    (settings.db_dir / SOCKET).write_text("not a socket")
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2
    assert "socket" in result.output
    os.unlink(settings.db_dir / SOCKET)
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])  # nothing listens
    assert result.exit_code == 2
    assert "nothing listens" in result.output
