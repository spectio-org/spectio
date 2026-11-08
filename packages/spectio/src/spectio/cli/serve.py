"""`spectio serve` (P1 Task 11): the server on 127.0.0.1, in the foreground, or with `--detach`
in the tmux session `spectio-server` on this node (FU-P3-44; dev-env §15.3 req. 11). There is no
`--host` flag: 0.0.1 listens on 127.0.0.1 only (dev-env §15.3 req. 1).

`--detach`, in order:

1. A server of this user already runs on this node: print a new link, exit 0. server.json on
   another node: exit 2, unless `--force`. Its port held by another uid: exit 2. A listener of
   ours that gives no link yet (it is starting): wait for it, start nothing.
2. Otherwise start `python -P -m spectio serve --pane` in a new detached session, under an
   absolute `env -i` with an allow-list of variables as argv words (SEC-PRE-01): a running tmux
   server's global environment never reaches the child. The session exists already: wait for
   its pane if it runs `spectio serve --pane`, replace it if all its panes ended (the only
   kill), else exit 2. Two `--detach` at once make one session: the loser waits.
3. Wait for a server.json of this node whose PID is a live pane of the session and which was
   written after this call began, then print the link here, never in the pane. The pane ended:
   exit 2 with the child's refusal (`serve-detach.err`). No link in time: exit 3, the session
   left running.

The pane (`--pane`) mints no ticket and prints where to get a link instead. This command never
writes or removes server.json, and never signals or sends keys to a pane.
"""

import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime

import typer

from spectio import config
from spectio.cli import login
from spectio.config import Settings
from spectio.fsmodes import open_secure_dir, write_file
from spectio.loginshell import KEEP
from spectio.runner.rundir import private_dir, read_small
from spectio.runner.tmux import PANE_FORMAT, SERVER_SESSION, parse_pane, run_tmux

DETACH_WAIT_S = 120.0  # the first boot can rebuild a large index (CON-PRE-02)
POLL_S = 0.2
RETRY_S = 1.0  # between two link requests to a server that is not ready
SKEW_S = 2.0  # server.json's started_at against this call's start (SEC-PRE-03)
ERR_FILE = "serve-detach.err"  # the pane's refusal: its PID, then the message (CON-PRE-04)
ENV = "/usr/bin/env"
# What the pane gets: the launcher's variables, then the Spectio settings (config._ENV and
# SPECTIO_CONFIG), nothing else. Values are configuration, visible in `ps`: never a secret.
PANE_ENV = tuple(
    dict.fromkeys((*KEEP, "PATH", "LD_LIBRARY_PATH", "TMUX_TMPDIR", "SPECTIO_CONFIG", *config._ENV))
)
_SERVER_PANES = "#{pane_id} #{pane_pid} #{pane_dead}"
_SERVER_PANE = re.compile(r"%[0-9]{1,9} ([1-9][0-9]{0,9}) ([01])\n")
_VERSION = re.compile(r"tmux (?:next-)?([0-9]+)\.([0-9]+)")
# What tmux prints when there is no such session (or no tmux server at all); anything else
# stops --detach (SEC-PRE-07).
_NO_SESSION = (
    "can't find session",
    "can't find window",
    "no such session",
    "no server running",
    "error connecting to",
)
ATTACH = (
    f"The server runs in tmux session {SERVER_SESSION}: `tmux attach -t {SERVER_SESSION}` "
    f"shows it, `tmux kill-session -t {SERVER_SESSION}` stops it."
)
STILL = (
    f"the server is still starting in tmux session {SERVER_SESSION}: run "
    f"`spectio login --print-link` later for a link (`tmux attach -t {SERVER_SESSION}` shows it)"
)


class Stop(Exception):
    """Why `--detach` prints no link; `code` is the exit code."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def _settings() -> Settings | None:
    try:
        return Settings()
    except ValueError as exc:  # a bad spectio.toml or SPECTIO_* value
        typer.echo(f"spectio serve: {exc}", err=True)
        return None


def run_serve(force: bool, pane: bool = False) -> int:
    settings = _settings()
    if settings is None:
        return 2
    try:
        from spectio_server.serve import ServeError, serve  # the server (architecture §6)
    except ImportError:
        typer.echo(
            "spectio serve: the server package is missing: install spectio[server]", err=True
        )
        return 2
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        serve(settings, force=force, mint_link=not pane)
    except ServeError as exc:
        typer.echo(f"spectio serve: {exc}", err=True)
        if pane:  # the pane closes with it: the caller reads why
            _write_err(settings, str(exc))
        return 2
    return 0


def _write_err(settings: Settings, message: str) -> None:
    try:
        fd = open_secure_dir(settings.data_dir, create=False)
    except OSError:
        return
    try:
        write_file(fd, ERR_FILE, f"{os.getpid()}\n{message}\n".encode())
    except OSError:
        pass
    finally:
        os.close(fd)


def run_detach(force: bool, wait_s: float, show_link: bool) -> int:
    settings = _settings()
    if settings is None:
        return 2
    try:
        from spectio_server.serve import _user, start_text  # before tmux starts (CON-PRE-11)
    except ImportError:
        typer.echo(
            "spectio serve: the server package is missing: install spectio[server]", err=True
        )
        return 2
    try:
        url, in_tmux = _detach(settings, force, wait_s)
    except Stop as exc:
        typer.echo(f"spectio serve: {exc}", err=True)
        return exc.code
    # The calling terminal only (req. 11); with --no-link (spectio open), no link at all.
    typer.echo(
        start_text(settings, socket.gethostname(), _user(), None, url if show_link else None)
    )
    if in_tmux:
        typer.echo(ATTACH)
    return 0


def _detach(settings: Settings, force: bool, wait_s: float) -> tuple[str, bool]:
    """The link, and whether the server is the session's."""
    tmux = shutil.which("tmux")
    if tmux is None:
        raise Stop("tmux is not on PATH: --detach runs the server in a tmux session")
    _check_version(tmux)
    t0, deadline = time.time(), time.monotonic() + wait_s
    try:
        return login.new_link(settings, _left(deadline)), False
    except login.OtherNode as exc:
        if not force:
            raise Stop(f"{exc} Or start one here with --force.") from exc
    except login.PortHeld as exc:
        raise Stop(str(exc)) from exc
    except login.NotReady:  # a server of ours is starting: never a second one (CON-PRE-01)
        return _wait_link(settings, deadline), False
    except login.Refused:
        pass  # none runs (or server.json is bad: the child says why)
    argv = _pane_argv(force)
    seen = _start(tmux, argv)
    return _wait_own(settings, tmux, seen, t0, deadline), True


def _left(deadline: float) -> float:
    return max(0.1, min(10.0, deadline - time.monotonic()))


def _tmux(tmux: str, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return run_tmux(tmux, *args)
    except OSError as exc:  # TimeoutError too
        raise Stop(f"tmux {args[0]}: {exc}") from exc


def _check_version(tmux: str) -> None:
    """Argument lists need tmux 2.0, the `=` exact target 2.1 (CON-PRE-07)."""
    out = _tmux(tmux, "-V").stdout.strip()
    found = _VERSION.match(out)
    if out != "tmux master" and (found is None or (int(found[1]), int(found[2])) < (2, 1)):
        raise Stop(f"--detach needs tmux 2.1 or later, this is {out[:80]!r}")


def _pane_argv(force: bool) -> list[str]:
    if not os.access(ENV, os.X_OK):
        raise Stop(f"{ENV} is missing: --detach starts the server through it")
    words = [f"{name}={os.environ[name]}" for name in PANE_ENV if name in os.environ]
    argv = [ENV, "-i", *words, sys.executable, "-P", "-m", "spectio", "serve", "--pane"]
    argv += ["--force"] if force else []
    for word in argv:  # tmux takes an argument that ends in `;` as a command separator
        if word.endswith(";"):
            raise Stop(f"{word.partition('=')[0]} ends with ';', which tmux cuts: change it")
    return argv


def _server_panes(tmux: str) -> list[tuple[int, bool]] | None:
    """The session's panes, (PID, dead), or None when there is no session."""
    found = _tmux(tmux, "list-panes", "-s", "-t", f"={SERVER_SESSION}", "-F", _SERVER_PANES)
    if found.returncode != 0:
        stderr = found.stderr.strip()
        if stderr.lower().startswith(_NO_SESSION):
            return None
        raise Stop(f"tmux list-panes failed: {stderr[:500] or found.returncode}")
    lines = (_SERVER_PANE.fullmatch(line) for line in found.stdout.splitlines(keepends=True))
    return [(int(m[1]), m[2] == "1") for m in lines if m is not None]


def _runs_pane_serve(pid: int) -> bool:
    """Whether the process runs `... -m spectio serve --pane` (or the env that execs it)."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            words = f.read().decode(errors="replace").split("\0")
    except OSError:
        return False
    tail = ["-m", "spectio", "serve", "--pane"]
    return any(words[i : i + len(tail)] == tail for i in range(len(words)))


def _start(tmux: str, argv: list[str], again: bool = True) -> set[int]:
    """The PIDs of the panes to wait for: the session's, or the new session's one pane."""
    panes = _server_panes(tmux)
    if panes is not None:
        live = {pid for pid, dead in panes if not dead}
        if not live:  # remain-on-exit: every pane ended, the session would block every start
            killed = _tmux(tmux, "kill-session", "-t", f"={SERVER_SESSION}")
            if killed.returncode != 0:
                raise Stop(f"tmux kill-session failed: {killed.stderr.strip()[:500]}")
        elif any(_runs_pane_serve(pid) for pid in live):
            return live  # another --detach's server, starting: wait for it, never kill
        else:
            raise Stop(
                f"tmux session {SERVER_SESSION} exists and does not run the server: see "
                f"`tmux attach -t {SERVER_SESSION}`"
            )
    started = _tmux(
        tmux,
        *("new-session", "-d", "-P", "-F", PANE_FORMAT, "-s", SERVER_SESSION, "-c", "/"),
        *argv,
        *(";", "set-option", "-t", f"={SERVER_SESSION}:", "destroy-unattached", "off"),
    )
    pane = parse_pane(started.stdout)
    if pane is not None:
        return {pane[1]}
    stderr = started.stderr.strip()
    if again and stderr.startswith("duplicate session"):  # a race with another --detach
        return _start(tmux, argv, again=False)
    raise Stop(f"tmux new-session failed: {stderr[:500] or started.stdout[:200]!r}")


def _wait_link(settings: Settings, deadline: float) -> str:
    while True:
        try:
            return login.new_link(settings, _left(deadline))
        except login.NotReady:
            pass
        except login.Refused as exc:
            raise Stop(str(exc)) from exc
        if time.monotonic() >= deadline:
            raise Stop(STILL, 3)
        time.sleep(RETRY_S)


def _wait_own(settings: Settings, tmux: str, seen: set[int], t0: float, deadline: float) -> str:
    retry_at = 0.0
    while True:
        live = {pid for pid, dead in _server_panes(tmux) or [] if not dead}
        if not live:
            raise Stop(f"the server stopped at start: {_why(settings, seen)}")
        seen |= live
        now = time.monotonic()
        if now >= retry_at and _ours(settings, live, t0):
            try:
                return login.new_link(settings, _left(deadline))
            except login.Refused:  # booting: server.json comes before the key (CON-PRE-01)
                retry_at = time.monotonic() + RETRY_S
        if time.monotonic() >= deadline:
            raise Stop(STILL, 3)
        time.sleep(POLL_S)


def _ours(settings: Settings, live: set[int], t0: float) -> bool:
    """server.json names this node, a live pane of the session, and a start after `t0`."""
    try:
        record = login._record(settings)
        started = datetime.fromisoformat(record["started_at"]).timestamp()
    except (login.Refused, KeyError, TypeError, ValueError):
        return False
    pid = record.get("pid")
    return (
        record.get("host") == login.hostname()
        and type(pid) is int
        and pid in live
        and started >= t0 - SKEW_S
    )


def _why(settings: Settings, seen: set[int]) -> str:
    """The pane's own refusal, if one of `seen` wrote it."""
    try:
        with private_dir(settings.data_dir) as fd:
            raw = read_small(fd, ERR_FILE, cap=8192) or b""
    except (OSError, ValueError):
        raw = b""
    pid, _, message = raw.decode(errors="replace").partition("\n")
    if pid.isdigit() and int(pid) in seen and message.strip():
        return "".join(c if c.isprintable() else "?" for c in message.strip())
    return "run `spectio serve` here to see why"
