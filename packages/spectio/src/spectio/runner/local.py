"""The local launcher: `setsid bash head.sh` (schedulers §3.1.1; P1 Task 9, Assumptions 4 and 15).

The head runs in its own session, stdin `/dev/null`, its own stderr in `.spectio/head.err`
(the engine's output goes to `.spectio/head.out` through the head script), so it outlives the
server, and the next server adopts it. A head is alive while `.spectio/head.pid` matches a
live process on this host and boot: same start time and process group. That check is made
again before every signal, and no signal crosses a boot or a host (dev-env §15.3 req. 11).
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
from dataclasses import dataclass
from pathlib import Path

from spectio.loginshell import KEEP
from spectio.runner.headscript import write_launch_files
from spectio.runner.rundir import private_dir, read_small
from spectio.runner.types import HeadReport, LaunchRef, LaunchSpec

log = logging.getLogger(__name__)

_PID_LINE = re.compile(
    r"([1-9][0-9]{0,9}) ([1-9][0-9]{0,9}) ([0-9]{1,20}) ([0-9a-f-]{36}) ([A-Za-z0-9._-]{1,255})\n"
)
_EXIT_LINE = re.compile(r"([0-9]{1,3}) ([0-9]{1,20})\n")


@dataclass(frozen=True)
class HeadPid:
    """`.spectio/head.pid`: PID, process group, start time (clock ticks), boot ID, host."""

    pid: int
    pgid: int
    start: str
    boot_id: str
    host: str


def _boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def _process(pid: int) -> tuple[int, str] | None:
    """The process group and start time of a live process, or None (gone, or a zombie)."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    except (OSError, IndexError):
        return None
    return None if fields[0] == "Z" else (int(fields[2]), fields[19])


def _read(launch_dir: Path, name: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """A head file, parsed strictly; None when it is missing. Raises OSError or ValueError."""
    with private_dir(launch_dir, ".spectio") as fd:
        raw = read_small(fd, name, cap=4096)
    if raw is None:
        return None
    match = pattern.fullmatch(raw.decode("ascii"))
    if not match:
        raise ValueError(f"{launch_dir}/.spectio/{name} is not as the head script writes it")
    return match


def read_head_pid(launch_dir: Path) -> HeadPid | None:
    match = _read(launch_dir, "head.pid", _PID_LINE)
    if match is None:
        return None
    pid, pgid, start, boot_id, host = match.groups()
    return HeadPid(int(pid), int(pgid), start, boot_id, host)


def alive(head: HeadPid) -> bool:
    """The PID check: this host, this boot, and the same process and group still live."""
    return (
        head.host == socket.gethostname()
        and head.boot_id == _boot_id()
        and _process(head.pid) == (head.pgid, head.start)
    )


class LocalLauncher:
    """Implements `Launcher`; a head's native ID is its PID."""

    def __init__(self) -> None:
        self._dirs: dict[str, Path] = {}  # native ID → launch directory
        self._procs: dict[str, subprocess.Popen[bytes]] = {}  # the heads this one started
        # native ID → when SIGKILL follows SIGTERM, and the head SIGTERM went to: SIGKILL goes
        # to that head only, never to a later one that reuses its PID (SEC-P3T09-02)
        self._kill_at: dict[str, tuple[float, HeadPid]] = {}
        self._warned: set[str] = set()  # heads whose unreadable files are already logged

    def submit(self, spec: LaunchSpec) -> str:
        head = write_launch_files(spec)
        env = {k: os.environ[k] for k in (*KEEP, "PATH") if k in os.environ}
        with private_dir(spec.launch_dir, ".spectio") as fd:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
            err = os.open("head.err", flags, 0o600, dir_fd=fd)
        try:
            proc = subprocess.Popen(  # noqa: S603 - an argument list, no shell of ours
                [shutil.which("bash") or "/bin/bash", str(head)],
                cwd=spec.launch_dir,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=err,
                start_new_session=True,
            )
        finally:
            os.close(err)
        native_id = str(proc.pid)
        self._dirs[native_id] = spec.launch_dir
        self._procs[native_id] = proc
        return native_id

    def adopt(self, launch: LaunchRef) -> HeadReport:
        native_id = launch.native_id
        if native_id is None:
            try:
                head = read_head_pid(launch.launch_dir)
            except (OSError, ValueError) as exc:
                log.warning("head of %s not read: %r", launch.launch_dir, exc)
                return HeadReport("unknown", None, None, None, False, None)
            if head is None:
                return HeadReport("unknown", None, None, None, True, None)  # never started
            native_id = str(head.pid)
        self._dirs[native_id] = launch.launch_dir
        return self._report(native_id)

    def poll(self, ids: list[str]) -> dict[str, HeadReport]:
        now = time.monotonic()
        for native_id in ids:
            due = self._kill_at.get(native_id)
            if due is not None and due[0] <= now:
                del self._kill_at[native_id]
                self._signal(native_id, signal.SIGKILL, due[1])
        reports = {native_id: self._report(native_id) for native_id in ids}
        for native_id, report in reports.items():
            if report.ended:
                self._kill_at.pop(native_id, None)
        return reports

    def cancel(self, native_id: str, grace_s: int = 60) -> None:
        """SIGTERM to the head's process group now, SIGKILL at the first poll after the grace
        period if it still lives (Assumption 4, local executor)."""
        head = self._signal(native_id, signal.SIGTERM)
        if head is not None:
            self._kill_at[native_id] = (time.monotonic() + grace_s, head)

    def _signal(
        self, native_id: str, sig: signal.Signals, only: HeadPid | None = None
    ) -> HeadPid | None:
        """Signal the head's group if `head.pid` names a live head with this native ID (and is
        `only`, when given); returns the head signalled."""
        try:
            head = read_head_pid(self._dirs[native_id])
        except (KeyError, OSError, ValueError) as exc:
            log.warning("head %s not signalled: %r", native_id, exc)
            return None
        if head is None or str(head.pid) != native_id or not alive(head):
            return None
        if only is not None and head != only:
            return None
        with contextlib.suppress(ProcessLookupError):
            os.killpg(head.pgid, sig)
        return head

    def _report(self, native_id: str) -> HeadReport:
        launch_dir = self._dirs.get(native_id)
        proc = self._procs.get(native_id)
        if proc is not None:
            proc.poll()  # reap it: a zombie would pass for a live head
        if launch_dir is None:
            return HeadReport("unknown", native_id, None, None, False, None)
        try:
            head = read_head_pid(launch_dir)
            if head is not None and str(head.pid) != native_id:
                raise ValueError(f"head.pid names PID {head.pid}, not {native_id}")
            if head is not None and head.host != socket.gethostname():
                # Another machine's head cannot be checked: never ended from here.
                return HeadReport("unknown", native_id, head.host, None, False, None)
            node = socket.gethostname()
            if head is not None and alive(head):
                return HeadReport("running", native_id, node, None, False, None)
            done = _read(launch_dir, "head.exit", _EXIT_LINE)  # after the PID check: no race
        except (OSError, ValueError) as exc:
            if native_id not in self._warned:  # once per head, not once per tick
                self._warned.add(native_id)
                log.warning("head %s of %s not read: %r", native_id, launch_dir, exc)
            return HeadReport("unknown", native_id, None, None, False, None)
        self._warned.discard(native_id)
        if done is not None:
            return HeadReport("exited", native_id, node, int(done[1]), True, None)
        if head is None and proc is not None:
            if proc.returncode is None:
                return HeadReport("starting", native_id, node, None, False, None)
            # The script ended before it wrote head.pid: its own exit code.
            return HeadReport("exited", native_id, node, proc.returncode, True, None)
        return HeadReport("unknown", native_id, node, None, True, None)  # gone, no exit file
