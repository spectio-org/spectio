"""dev-env §15.3 req. 1: the server listens on 127.0.0.1 only (P1 Task 11)."""

import threading
import time
import urllib.request
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings
from spectio_server.serve import started


def _listeners(port: int) -> set[str]:
    """The local addresses (hex, as /proc/net/tcp* writes them) listening on `port`."""
    found = set()
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        if not table.exists():  # no IPv6 on this machine
            continue
        for line in table.read_text().splitlines()[1:]:
            fields = line.split()
            address, hex_port = fields[1].rsplit(":", 1)
            if int(hex_port, 16) == port and fields[3] == "0A":  # LISTEN
                found.add(address)
    return found


def test_req1_binds_loopback_only(settings: Settings) -> None:
    with started(settings) as server:
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 20
        while not server.uvicorn.started:
            assert time.monotonic() < deadline, "the server did not start"
            time.sleep(0.05)
        try:
            assert server.sock.getsockname() == ("127.0.0.1", settings.port)
            assert _listeners(settings.port) == {"0100007F"}  # 127.0.0.1, and nothing else
            with urllib.request.urlopen(f"http://127.0.0.1:{settings.port}/") as response:
                assert response.status == 200
        finally:
            server.uvicorn.should_exit = True
            thread.join(20)
    assert not thread.is_alive()


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "localhost", "192.0.2.1"])  # noqa: S104
@pytest.mark.parametrize("where", ["toml", "env"])
def test_req1_refuses_other_bind(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, host: str, where: str
) -> None:
    if where == "env":
        monkeypatch.setenv("SPECTIO_SERVER_HOST", host)
    else:
        config = Path(settings.data_dir / "spectio.toml")
        config.write_text(config.read_text() + f'\n[server]\nhost = "{host}"\n')
    result = CliRunner().invoke(app, ["serve"])
    assert result.exit_code == 2, result.output
    assert "0.0.1 binds to 127.0.0.1 only" in result.output
    assert not (settings.data_dir / "server.json").exists()  # refused before anything started


def test_req1_has_no_host_flag(settings: Settings) -> None:
    result = CliRunner().invoke(app, ["serve", "--host", "0.0.0.0"])  # noqa: S104
    assert result.exit_code == 2
    assert "No such option" in result.output
