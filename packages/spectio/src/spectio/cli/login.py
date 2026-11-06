"""`spectio login --print-link` (P1 Task 12; dev-env §15.3 "Access", req. 8 and 9).

It reads the state file `<data dir>/server.json` and checks each value before use: the node
(req. 8's pattern), the port (1024 to 65535) and the database directory. On another login node it
names the node to `ssh` to and sends nothing. On this one it sends the server key only to a
listener of the user's own uid (req. 9): `POST /api/v1/auth/links` on 127.0.0.1 with the
loopback `Origin`, never through a proxy that the environment names. It prints the link, or
with `--json` one line: `SENTINEL`, a space, then `{"ticket": …}`, for `spectio open`.
"""

import json
import os
import re
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import typer

from spectio.config import LOOPBACK, Settings
from spectio.ports import port_owner
from spectio.runner.rundir import private_dir, read_small

STATE = "server.json"
KEY_FILE = "server.key"
SENTINEL = "spectio-ticket-v1"
NODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}")
TICKET = re.compile(r"[A-Za-z0-9_-]{43}")
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never a proxy: the key


def hostname() -> str:
    return socket.gethostname()


class Refused(Exception):
    """Why no link is printed."""


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


def _checked(record: dict[str, Any]) -> tuple[str, int, Path]:
    node, port, db_dir = record.get("host"), record.get("port"), record.get("db_dir")
    if not isinstance(node, str) or not NODE.fullmatch(node):
        raise Refused("server.json names a node that is not a host name: check it")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise Refused("server.json names a port outside 1024-65535: check it")
    if not isinstance(db_dir, str) or not db_dir.startswith("/"):
        raise Refused("server.json names no absolute database directory: check it")
    return node, port, Path(db_dir)


def new_link(settings: Settings) -> str:
    """A fresh link from the running server of this node."""
    node, port, db_dir = _checked(_record(settings))
    if node != hostname():
        raise Refused(f"The server runs on {node}: run `ssh {node} spectio login --print-link`.")
    owner = port_owner(port)
    if owner != os.getuid():
        who = "nothing listens there" if owner is None else f"it is held by uid {owner}"
        raise Refused(f"no server of yours on port {port} ({who}): the key is not sent")
    try:
        with private_dir(db_dir) as fd:
            key = (read_small(fd, KEY_FILE, cap=256) or b"").decode().strip()
    except (OSError, ValueError) as exc:
        raise Refused(f"the server key in {db_dir} cannot be read: {exc}") from exc
    origin = f"http://{LOOPBACK}:{port}"
    request = urllib.request.Request(  # noqa: S310 (a loopback http URL built here)
        f"{origin}/api/v1/auth/links",
        data=b"",
        headers={"Authorization": f"Bearer {key}", "Origin": origin},
        method="POST",
    )
    try:
        with DIRECT.open(request, timeout=10) as answer:
            url = json.load(answer)["url"]
    except (OSError, ValueError, KeyError, TypeError) as exc:  # HTTPError and URLError too
        raise Refused(f"the server on port {port} gave no link: {exc}") from exc
    if not isinstance(url, str) or not TICKET.fullmatch(url.partition("#")[2]):
        raise Refused(f"the server on port {port} gave no link")
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
