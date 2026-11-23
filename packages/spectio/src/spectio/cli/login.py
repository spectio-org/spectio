"""`spectio login --print-link` (P1 Task 12; dev-env §15.3 "Access", req. 8 and 9).

It reads the state file `<data dir>/server.json` and checks each value before use: the node
(req. 8's pattern), the port (1024 to 65535), the database directory and the socket. On another
login node it names the node to `ssh` to and sends nothing. On this one it sends the server key
only to a listener of the user's own uid (req. 9): `POST /api/v1/auth/links` with the loopback
`Origin`, never through a proxy that the environment names. That listener is the Unix socket of
server.json when it names one (SLURM and shared hosts, inbox #109 rule 5): a socket of this
user, `SOCKET` in the database directory the key is read from; else 127.0.0.1 and the port. It
prints the link, or with `--json` one line: `SENTINEL`, a space, then `{"ticket": …}`, for
`spectio open`.
"""

import http.client
import json
import os
import re
import socket
import stat
from pathlib import Path
from typing import Any

import typer

from spectio.config import LOOPBACK, Settings
from spectio.ports import SOCKET, is_server_socket, port_owners
from spectio.runner.rundir import private_dir, read_small

STATE = "server.json"
KEY_FILE = "server.key"
SENTINEL = "spectio-ticket-v1"
NODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}")
TICKET = re.compile(r"[A-Za-z0-9_-]{43}")


def hostname() -> str:
    return socket.gethostname()


class Refused(Exception):
    """Why no link is printed."""


class OtherNode(Refused):
    """server.json names a server on another node."""


class PortHeld(Refused):
    """Another uid listens on the port of server.json."""


class NotReady(Refused):
    """A listener of this uid on the port, but no link from it yet: it may still be starting."""


def _record(settings: Settings) -> dict[str, Any]:
    try:
        with private_dir(settings.data_dir) as fd:
            raw = read_small(fd, STATE, cap=65536)
    except (OSError, ValueError) as exc:
        raise Refused(f"{settings.data_dir / STATE} cannot be read: {exc}") from exc
    if raw is None:
        raise Refused("no server runs (no server.json): start one with spectio serve")
    try:
        record = json.loads(raw)
    except ValueError as exc:
        raise Refused(f"{settings.data_dir / STATE} is not JSON") from exc
    if not isinstance(record, dict):
        raise Refused(f"{settings.data_dir / STATE} is not a server record")
    return record


class _UnixHTTP(http.client.HTTPConnection):
    """HTTP on a Unix socket; `Host` stays `127.0.0.1:<port>`, as through the tunnel."""

    def __init__(self, path: Path, port: int, timeout: float) -> None:
        super().__init__(LOOPBACK, port, timeout=timeout)
        self.socket_path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(str(self.socket_path))
        except BaseException:
            sock.close()
            raise
        self.sock = sock


def _connection(port: int, socket_path: Path | None, timeout: float) -> http.client.HTTPConnection:
    """To the server: its socket, or 127.0.0.1 and the port; never a proxy (the key goes out)."""
    if socket_path is None:
        return http.client.HTTPConnection(LOOPBACK, port, timeout=timeout)
    return _UnixHTTP(socket_path, port, timeout)


def _checked(record: dict[str, Any]) -> tuple[str, int, Path, Path | None]:
    node, port, db_dir = record.get("host"), record.get("port"), record.get("db_dir")
    sock = record.get("socket")
    if not isinstance(node, str) or not NODE.fullmatch(node):
        raise Refused("server.json names a node that is not a host name: check it")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise Refused("server.json names a port outside 1024-65535: check it")
    if not isinstance(db_dir, str) or not db_dir.startswith("/"):
        raise Refused("server.json names no absolute database directory: check it")
    if sock is not None and not is_server_socket(sock, db_dir):
        raise Refused(f"server.json names a socket other than {SOCKET} in {db_dir}: check it")
    return node, port, Path(db_dir), None if sock is None else Path(sock)


def server_socket(settings: Settings) -> Path | None:
    """The socket server.json names, checked; None for a TCP port or no usable record."""
    try:
        return _checked(_record(settings))[3]
    except Refused:
        return None


def _own_socket(dir_fd: int, socket_path: Path) -> None:
    """The server's socket: a socket of this user in the checked database directory."""
    try:
        st = os.stat(SOCKET, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        raise Refused(f"no server of yours on {socket_path} (nothing listens there)") from None
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid != os.getuid():
        raise Refused(f"{socket_path} is not a socket of yours: the key is not sent")


def new_link(settings: Settings, timeout: float = 10) -> str:
    """A fresh link from the running server of this node; `timeout` bounds the request."""
    node, port, db_dir, socket_path = _checked(_record(settings))
    if node != hostname():
        raise OtherNode(f"The server runs on {node}: run `ssh {node} spectio login --print-link`.")
    if socket_path is None:
        owners = port_owners(port)
        if not owners:
            raise Refused(f"no server of yours on port {port} (nothing listens there)")
        if owners != {os.getuid()}:
            who = f"it is held by uid {min(owners - {os.getuid()})}"
            raise PortHeld(f"no server of yours on port {port} ({who}): the key is not sent")
    try:
        with private_dir(db_dir) as fd:  # 0700 and this user's: the socket's boundary too
            if socket_path is not None:
                _own_socket(fd, socket_path)
            key = (read_small(fd, KEY_FILE, cap=256) or b"").decode().strip()
    except (OSError, ValueError) as exc:
        raise Refused(f"the server key in {db_dir} cannot be read: {exc}") from exc
    if not key:  # written once the server has booted
        raise NotReady(f"no server key in {db_dir} yet")
    where = f"port {port}" if socket_path is None else str(socket_path)
    origin = f"http://{LOOPBACK}:{port}"
    conn = _connection(port, socket_path, timeout)
    if socket_path is not None:  # a dead server's socket file: none runs, as no owner on TCP
        try:
            conn.connect()
        except (ConnectionRefusedError, FileNotFoundError):
            conn.close()
            raise Refused(f"no server of yours on {socket_path} (nothing listens there)") from None
    try:
        conn.request(
            "POST",
            "/api/v1/auth/links",
            body=b"",
            headers={"Authorization": f"Bearer {key}", "Origin": origin},
        )
        answer = conn.getresponse()
        if answer.status != 200:
            raise ValueError(f"HTTP {answer.status}")
        url = json.load(answer)["url"]
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException) as exc:
        raise NotReady(f"the server on {where} gave no link: {exc}") from exc
    finally:
        conn.close()
    if not isinstance(url, str) or not TICKET.fullmatch(url.partition("#")[2]):
        raise Refused(f"the server on {where} gave no link")
    return url


def run_login(print_link: bool, as_json: bool) -> int:
    if not print_link:
        typer.echo("spectio login: 0.0.1 has --print-link only", err=True)
        return 2
    try:
        settings = Settings()
    except ValueError as exc:  # a bad spectio.toml or SPECTIO_* value
        typer.echo(f"spectio login: {exc}", err=True)
        return 2
    try:
        url = new_link(settings)
    except Refused as exc:
        typer.echo(f"spectio login: {exc}", err=True)
        return 2
    if as_json:
        typer.echo(f"{SENTINEL} {json.dumps({'ticket': url.partition('#')[2]})}")
    else:
        typer.echo(url)
    return 0
