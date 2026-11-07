"""The tmux launcher: each head in its own tmux session on the login node (P1 Task 10,
Assumptions 4, 13 and 15; schedulers §3.1.1, tmux launcher; dev-env §15.3 req. 11).

`submit` starts `bash <launch>/.spectio/head.sh` as the command of a new detached session
`spectio-<run_id>`: only the tmux server is detached. The pane's command leads the pane's process
group, the terminal's foreground group, with no `setsid` of ours, so that a Ctrl-C typed in the
pane, or sent by `send-keys`, reaches the engine. A person can attach to the session at any time.

The native ID is the session name. The head's own identity is the pane's PID, which `head.pid`
must name (the head script writes `$$`), with the start time and boot ID of the local launcher's
PID check, made again before every signal (SEC-P3T09-R5-03). Every tmux call is an argument
list; every target is the exact session `=spectio-<run_id>`, or the pane ID that `new-session`
printed, found again in that session before `send-keys` (req. 11). A head this launcher did not
find in its session's pane is never signalled, and is never reported ended while it lives.
"""

import contextlib
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from spectio.loginshell import KEEP
from spectio.runner.headscript import write_launch_files
from spectio.runner.local import HeadPid, _process, alive, read_head_exit, read_head_pid
from spectio.runner.rundir import RUN_ID
from spectio.runner.types import HeadReport, LaunchRef, LaunchSpec

log = logging.getLogger(__name__)

PANE_FORMAT = "#{pane_id} #{pane_pid}"
_PANE_LINE = re.compile(r"(%[0-9]{1,9}) ([1-9][0-9]{0,9})\n")
TMUX_TIMEOUT_S = 10
# What the tmux client gets of the server's environment: a tmux server it starts keeps it for
# every later pane of the user, so no SPECTIO_* setting goes there; no `TMUX` either, so that
# the user's default server is used, not the one of a pane `spectio serve` runs in.
_TMUX_ENV = (*KEEP, "PATH", "TMUX_TMPDIR")


def session_name(run_id: str) -> str:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(f"{run_id!r} is not a run ID")
    return f"spectio-{run_id}"


@dataclass(frozen=True)
class _Pane:
    """Where a head is: its launch directory, and its pane ID and PID, or None when its session's
    pane was not found to be the head (at adopt)."""

    launch_dir: Path
    pane: str | None
    pid: int | None


class TmuxLauncher:
    """Implements `Launcher`; a head's native ID is its session name, `spectio-<run_id>`."""

    def __init__(self, tmux: str = "tmux") -> None:
        self.tmux = tmux
        self._panes: dict[str, _Pane] = {}  # session → its head's pane
        # session → when the next signal is due, which one, the head it goes to (never a later
        # process that reuses its PID) and the grace period (Assumption 4)
        self._due: dict[str, tuple[float, signal.Signals, HeadPid, float]] = {}
        self._warned: set[str] = set()  # heads whose unreadable files are already logged

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {k: os.environ[k] for k in _TMUX_ENV if k in os.environ}
        try:
            return subprocess.run(  # noqa: S603 - an argument list, no shell
                [self.tmux, *args],
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=TMUX_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise OSError(f"tmux {args[0]} did not answer in {TMUX_TIMEOUT_S} s") from None

    def _list_panes(self, session: str) -> dict[int, str]:
        """The panes of the session, pane PID → pane ID; empty when there is no such session."""
        found = self._run("list-panes", "-s", "-t", f"={session}", "-F", PANE_FORMAT)
        if found.returncode != 0:
            return {}
        lines = (_PANE_LINE.fullmatch(line) for line in found.stdout.splitlines(keepends=True))
        return {int(m[2]): m[1] for m in lines if m is not None}

    def submit(self, spec: LaunchSpec) -> str:
        """Start the head; raises OSError, whose message starts with tmux's stderr, when tmux
        is missing or the session exists (P1 Edge case 3)."""
        session = session_name(spec.run_id)
        head = write_launch_files(spec)
        bash = shutil.which("bash") or "/bin/bash"
        started = self._run(
            *("new-session", "-d", "-P", "-F", PANE_FORMAT, "-s", session),
            *("-c", str(spec.launch_dir), bash, str(head)),
        )
        if started.returncode != 0:
            stderr = started.stderr.strip() or f"tmux new-session exited {started.returncode}"
            raise OSError(stderr[:4096])
        match = _PANE_LINE.fullmatch(started.stdout)
        if match is None:
            raise OSError(f"tmux new-session printed {started.stdout[:200]!r}, not a pane")
        self._panes[session] = _Pane(spec.launch_dir, match[1], int(match[2]))
        return session

    def adopt(self, launch: LaunchRef) -> HeadReport:
        """The head of `spectio-<run_id>`, whatever native ID the index holds (a rebuilt index
        holds the local form, CR-P3T11-04): its session's pane must be the head of head.pid,
        or the one pane while head.pid is not written yet."""
        session = session_name(launch.run_id)
        panes = self._list_panes(session)
        pid = None
        with contextlib.suppress(OSError, ValueError):  # _report logs it
            head = read_head_pid(launch.launch_dir)
            pid = head.pid if head is not None else None
        if pid is None and len(panes) == 1:
            pid = next(iter(panes))
        pane = panes.get(pid) if pid is not None else None
        self._panes[session] = _Pane(launch.launch_dir, pane, pid if pane is not None else None)
        return self._report(session)

    def poll(self, ids: list[str]) -> dict[str, HeadReport]:
        now = time.monotonic()
        for session in ids:
            due = self._due.get(session)
            if due is not None and due[0] <= now:
                del self._due[session]
                _, sig, head, grace = due
                if self._signal(session, sig, head) and sig == signal.SIGTERM:
                    self._due[session] = (now + grace, signal.SIGKILL, head, grace)
        reports = {session: self._report(session) for session in ids}
        for session, report in reports.items():
            if report.ended:
                self._due.pop(session, None)
        return reports

    def cancel(self, native_id: str, grace_s: int = 60) -> None:
        """Ctrl-C in the head's pane now, SIGTERM to its process group at the first poll after
        the grace period, SIGKILL after another (Assumption 4). A cancel already under way
        keeps its own grace."""
        if native_id in self._due:
            return
        head = self._live(native_id)
        if head is None:
            log.warning("head %s not interrupted: not a live head in its tmux pane", native_id)
            return
        pane = self._panes[native_id].pane
        if pane is not None and self._list_panes(native_id).get(head.pid) == pane:
            sent = self._run("send-keys", "-t", pane, "C-c")
            if sent.returncode != 0:
                log.warning("C-c not sent to %s: %s", native_id, sent.stderr.strip()[:200])
        else:
            log.warning("pane of %s not found: SIGTERM after the grace period", native_id)
        self._due[native_id] = (time.monotonic() + grace_s, signal.SIGTERM, head, grace_s)

    def forget(self, ids: Iterable[str]) -> None:
        for session in ids:
            for by_session in (self._panes, self._due):
                by_session.pop(session, None)
            self._warned.discard(session)

    def _live(self, session: str) -> HeadPid | None:
        """head.pid, when it names this session's pane, leads its group and lives."""
        found = self._panes.get(session)
        if found is None or found.pid is None:
            return None
        try:
            head = read_head_pid(found.launch_dir)
        except (OSError, ValueError):
            return None
        if head is None or head.pid != found.pid or head.pgid != head.pid or not alive(head):
            return None
        return head

    def _signal(self, session: str, sig: signal.Signals, only: HeadPid) -> bool:
        """Signal the head's group if it is still `only` and lives; whether it was signalled."""
        if self._live(session) != only:
            return False
        with contextlib.suppress(ProcessLookupError):
            os.killpg(only.pgid, sig)
        return True

    def _report(self, session: str) -> HeadReport:
        found = self._panes.get(session)
        if found is None:
            return HeadReport("unknown", session, None, None, False, None)
        try:
            head = read_head_pid(found.launch_dir)
            if head is not None and head.host != socket.gethostname():
                # Another machine's head cannot be checked: never ended from here.
                return HeadReport("unknown", session, head.host, None, False, None)
            node = socket.gethostname()
            if head is not None and alive(head):
                if head.pid != found.pid or head.pgid != head.pid:
                    raise ValueError(f"head {head.pid} lives, but not in the pane of {session}")
                return HeadReport("running", session, node, None, False, None)
            code = read_head_exit(found.launch_dir)  # after the PID check: no race
        except (OSError, ValueError) as exc:
            if session not in self._warned:  # once per head, not once per tick
                self._warned.add(session)
                log.warning("head %s of %s not read: %r", session, found.launch_dir, exc)
            return HeadReport("unknown", session, None, None, False, None)
        self._warned.discard(session)
        if code is not None:
            return HeadReport("exited", session, node, code, True, None)
        if head is None and found.pid is not None:
            process = _process(found.pid)
            if process is not None and process[0] == found.pid:  # head.pid not written yet
                return HeadReport("starting", session, node, None, False, None)
        return HeadReport("unknown", session, node, None, True, None)  # gone, no exit file
