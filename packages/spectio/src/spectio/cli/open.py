"""`spectio open <host>` (P1 Task 24): run on the laptop, it opens the user's server on a cluster
login node through an SSH tunnel and a one-time link (dev-env §15.3 "Access", steps 1 to 5, and
req. 8; cli §2).

1. Over `ssh <host>`, check that the remote `spectio` runs and read `~/.spectio/server.json`.
2. With a state file, reach its node (`--node` overrides it). Without one, on `--node`, the
   `node` of `clusters.toml` or `<host>`: `spectio init` if there is no data directory, then
   `spectio serve --detach`, and the state file it wrote.
3. Open the tunnel to that node on a free local port, get a ticket from `spectio login
   --print-link --json` there, build the link and open the browser. Wait until the tunnel ends
   or Ctrl-C; the server and its runs keep going.

`~/.config/spectio/clusters.toml` holds one table per `<host>`: `node` (the first-start node)
and `remote_cmd` (shell text run instead of `spectio`, such as `module load spectio &&
spectio`). Flags win over it. Exit codes: 0, the browser was opened and the tunnel has ended;
2, the remote `spectio` is missing (the install line is printed, nothing is installed); 3, any
other failure: ssh, a remote command, or a value that fails the checks of req. 8.
"""

import shutil
import socket
import subprocess
import time
import tomllib
import webbrowser
from importlib.metadata import version
from pathlib import Path
from typing import Any

import typer

from spectio.config import LOOPBACK, check_config
from spectio.open_remote import (
    State,
    Unsafe,
    check_node,
    check_port,
    free_port,
    link,
    login_script,
    parse_state,
    parse_ticket,
    probe_script,
    ssh_argv,
    start_script,
    tunnel_argv,
)

NOT_FOUND = 127  # the shell's status for a command it cannot find
TUNNEL_WAIT_S = 120  # ssh may ask for a password or a second factor first


class Failed(Exception):
    """Why `spectio open` stops; `code` is its exit code."""

    def __init__(self, message: str, code: int = 3) -> None:
        super().__init__(message)
        self.code = code


def clusters_path() -> Path:
    return Path.home() / ".config" / "spectio" / "clusters.toml"


def cluster_config(host: str) -> dict[str, str]:
    """The `[host]` table of `clusters.toml`: `node` and `remote_cmd`, both strings. The file
    holds a command run on the cluster, so it gets the checks of `spectio.toml`."""
    path = clusters_path()
    try:
        check_config(path)
        with path.open("rb") as f:
            data: dict[str, Any] = tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:  # UnsafeConfig and TOMLDecodeError are ValueErrors
        raise Failed(f"{path}: {exc}") from exc
    table = data.get(host, {})
    if not isinstance(table, dict) or not set(table) <= {"node", "remote_cmd"}:
        raise Failed(f"{path}: [{host}] takes node and remote_cmd only")
    if not all(isinstance(v, str) for v in table.values()):
        raise Failed(f"{path}: [{host}] node and remote_cmd are strings")
    return table


def _printable(text: str) -> str:
    """Text from the cluster as it may reach the terminal: no control sequences."""
    return "".join(c if c.isprintable() or c == "\n" else "?" for c in text).strip()


class Remote:
    """ssh calls to one cluster, each through the login shell, `remote_cmd` as `spectio`."""

    def __init__(self, ssh: str, host: str, remote_cmd: str) -> None:
        self.ssh, self.host, self.remote_cmd = ssh, host, remote_cmd

    def run(self, node: str, script: str) -> str:
        argv = ssh_argv(self.ssh, node, script)
        done = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
        if done.returncode == NOT_FOUND:
            raise Failed(
                f"spectio is not installed on {node}. Install it once into your shared home:\n"
                f"  ssh {self.host} uv tool install spectio=={version('spectio')}\n"
                "or give the command that runs it with --remote-cmd.",
                code=2,
            )
        if done.returncode != 0:
            raise Failed(f"ssh {node} failed ({done.returncode}): {_printable(done.stderr)}")
        return done.stdout

    def state(self) -> State | None:
        return parse_state(self.run(self.host, probe_script(self.remote_cmd)))

    def start(self, node: str) -> State:
        state = parse_state(self.run(node, start_script(self.remote_cmd)))
        if state is None:
            raise Failed(f"spectio serve --detach on {node} wrote no server.json")
        return state

    def ticket(self, node: str) -> str:
        try:
            return parse_ticket(self.run(node, login_script(self.remote_cmd)))
        except Failed as exc:  # server.json is not checked for a live server yet (FU-P3-48)
            raise Failed(
                f"{exc}\n~/.spectio/server.json on the cluster may be stale (its server may have "
                "stopped): if so, remove it and run spectio open again.",
                code=exc.code,
            ) from exc


def _wait_up(tunnel: subprocess.Popen[bytes], local_port: int) -> None:
    deadline = time.monotonic() + TUNNEL_WAIT_S
    while time.monotonic() < deadline:
        if tunnel.poll() is not None:
            raise Failed(f"the tunnel failed (ssh exit {tunnel.returncode})")
        try:
            socket.create_connection((LOOPBACK, local_port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.1)
    raise Failed(f"the tunnel was not up after {TUNNEL_WAIT_S} s")


def _open(
    host: str, node: str | None, remote_cmd: str | None, local_port: int | None, browser: bool
) -> None:
    host = check_node(host, "<host>")
    config = cluster_config(host)
    if node is not None:
        node = check_node(node, "--node")
    first = check_node(config["node"], "node in clusters.toml") if "node" in config else None
    ssh = shutil.which("ssh")
    if ssh is None:
        raise Failed("ssh is not on PATH")
    remote = Remote(ssh, host, remote_cmd or config.get("remote_cmd") or "spectio")
    state = remote.state()
    if state is None:
        state = remote.start(node or first or host)
    target = node or state.node
    lport = free_port() if local_port is None else check_port(local_port, "--local-port")
    with subprocess.Popen(tunnel_argv(ssh, target, lport, state.port)) as tunnel:  # noqa: S603
        try:
            _wait_up(tunnel, lport)
            url = link(lport, remote.ticket(target))
            if tunnel.poll() is not None:
                raise Failed(f"the tunnel to {target} closed (ssh exit {tunnel.returncode})")
            typer.echo(f"Spectio on {target}: {url}\nCtrl-C closes the tunnel.")
            if browser:
                webbrowser.open(url)
            tunnel.wait()
        except KeyboardInterrupt:
            pass
        finally:
            if tunnel.poll() is None:
                tunnel.terminate()


def run_open(
    host: str, node: str | None, remote_cmd: str | None, local_port: int | None, browser: bool
) -> int:
    try:
        _open(host, node, remote_cmd, local_port, browser)
    except Unsafe as exc:
        typer.echo(f"spectio open: {exc}", err=True)
        return 3
    except Failed as exc:
        typer.echo(f"spectio open: {exc}", err=True)
        return exc.code
    return 0
