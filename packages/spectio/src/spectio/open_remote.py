"""What `spectio open` sends to and reads from the cluster (P1 Task 24; dev-env §15.3 "Access",
req. 8): the `ssh` argument lists, the remote scripts quoted for both shell layers, and the
checks on every value that comes back.

The cluster is a trust boundary (dev-env §15.3, boundary (i)): a node, port, socket or PID read
from `server.json` is checked before use, a cluster value never goes inside `-o`, `--` comes before
every destination, and the browser link is built here from a checked ticket, never taken from
what the remote prints.
"""

import json
import re
import shlex
import socket
from dataclasses import dataclass
from typing import Any

from spectio.cli.login import NODE, SENTINEL, TICKET
from spectio.config import LOOPBACK
from spectio.ports import SOCKET, is_server_socket

STATE_MARK = "spectio-state-v1"  # tells the state file from what the remote profile prints
STARTING_MARK = "spectio-starting-v1"  # serve --detach exited 3: its server is still booting
# The remote end of `-L`: no `:` (ssh would cut the spec there), no space or control character.
_SOCKET_PATH = re.compile(r"/[A-Za-z0-9._/-]+")
_READ_STATE = f'echo {STATE_MARK}; cat -- "$HOME/.spectio/server.json" 2>/dev/null; exit 0'


class Unsafe(ValueError):
    """A value from the cluster, or for it, that fails the checks of req. 8."""


@dataclass(frozen=True)
class State:
    """The checked fields of `~/.spectio/server.json` that `spectio open` uses."""

    node: str
    port: int
    pid: int
    socket: str | None = None  # the server's Unix socket (SLURM and shared hosts, inbox #109)


def check_node(value: object, what: str) -> str:
    if not isinstance(value, str) or not NODE.fullmatch(value):
        raise Unsafe(f"{what} is not a host name: {value!r}")
    return value


def check_port(value: object, what: str) -> int:
    if type(value) is not int or not 1024 <= value <= 65535:
        raise Unsafe(f"{what} is not a port in 1024-65535: {value!r}")
    return value


def check_socket(value: object, db_dir: object) -> str:
    """The socket of server.json: `SOCKET` in its database directory, a path ssh's `-L` keeps
    whole, within the AF_UNIX limit."""
    if (
        not isinstance(value, str)
        or not _SOCKET_PATH.fullmatch(value)
        or not is_server_socket(value, db_dir)
    ):
        raise Unsafe(f"the socket in server.json is not {SOCKET} in its database directory")
    return value


def ssh_argv(ssh: str, node: str, script: str) -> list[str]:
    """`ssh -- node CMD`: sshd hands CMD to the user's shell (layer one), which runs `script`
    through `"$SHELL" -lc` (layer two), so PATH, modules and rc files apply."""
    return [ssh, "--", node, '"$SHELL" -lc ' + shlex.quote(script)]


def tunnel_argv(
    ssh: str, node: str, local_port: int, port: int, sock: str | None = None
) -> list[str]:
    """The tunnel from a laptop port to the server's socket, or to its port on the node."""
    forward = f"{LOOPBACK}:{local_port}:" + (f"{LOOPBACK}:{port}" if sock is None else sock)
    return [ssh, "-N", "-o", "ExitOnForwardFailure=yes", "-L", forward, "--", node]


def command(remote_cmd: str, *args: str) -> str:
    """`remote_cmd` (the user's own setting, shell text used as given) followed by `args`
    quoted as shell words, in a `{ ...; }` group: one shell unit, so `&&` or `||` inside
    `remote_cmd` stays inside it and a redirection covers all of it."""
    return f"{{ {remote_cmd} {shlex.join(args)}; }}"


def probe_script(remote_cmd: str) -> str:
    """Exit with the shell's status (127: not found) if the remote spectio cannot run, else
    print the state file after `STATE_MARK`."""
    return f"{command(remote_cmd, '--help')} >/dev/null || exit; {_READ_STATE}"


def start_script(remote_cmd: str) -> str:
    """`spectio init` if there is no data directory yet, `spectio serve --detach --no-link`
    (its link would land in ssh's captured output, SEC-PRE-10), then the state file as
    `probe_script` prints it. Exit 3 (started, no link yet) prints `STARTING_MARK` first."""
    init = command(remote_cmd, "init")
    serve = command(remote_cmd, "serve", "--detach", "--no-link")
    still = f'{{ s=$?; [ "$s" -eq 3 ] || exit "$s"; echo {STARTING_MARK}; }}'
    return f'[ -d "$HOME/.spectio" ] || {init} || exit; {serve} || {still}; {_READ_STATE}'


def login_script(remote_cmd: str) -> str:
    return command(remote_cmd, "login", "--print-link", "--json")


def parse_state(stdout: str) -> State | None:
    """The state file printed after `STATE_MARK`, checked; None if there is none."""
    _, mark, body = stdout.partition(f"{STATE_MARK}\n")
    if not mark:
        raise Unsafe("the cluster did not print the state file")
    if not body.strip():
        return None
    try:
        record: Any = json.loads(body)
    except ValueError as exc:
        raise Unsafe("~/.spectio/server.json on the cluster is not JSON") from exc
    if not isinstance(record, dict):
        raise Unsafe("~/.spectio/server.json on the cluster is not a server record")
    node = check_node(record.get("host"), "the node in server.json")
    port = check_port(record.get("port"), "the port in server.json")
    pid = record.get("pid")
    if type(pid) is not int:
        raise Unsafe(f"the PID in server.json is not an integer: {pid!r}")
    sock = record.get("socket")
    if sock is not None:
        sock = check_socket(sock, record.get("db_dir"))
    return State(node, port, pid, sock)


def parse_ticket(stdout: str) -> str:
    """The ticket of the `spectio login --print-link --json` line; any URL is ignored."""
    for line in stdout.splitlines():
        if line.startswith(f"{SENTINEL} "):
            try:
                ticket = json.loads(line.removeprefix(f"{SENTINEL} ")).get("ticket")
            except (ValueError, AttributeError):
                break
            if isinstance(ticket, str) and TICKET.fullmatch(ticket):
                return ticket
            break
    raise Unsafe("spectio login on the cluster printed no valid ticket")


def link(local_port: int, ticket: str) -> str:
    return f"http://{LOOPBACK}:{local_port}/auth/link#{ticket}"


def free_port() -> int:
    """A port of 127.0.0.1 that is free now; ssh's `ExitOnForwardFailure` covers the race."""
    with socket.socket() as sock:
        sock.bind((LOOPBACK, 0))
        port: int = sock.getsockname()[1]
        return port
