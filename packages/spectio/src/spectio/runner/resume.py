"""The checks before a Resume runs in its parent's directories (P1 Task 30; api §5.1 note of
2026-10-28; dev-env §15.3 req. 10 and 16).

The server makes them when `:relaunch` is asked (and for `actions.resume`), the runner again
just before the child's head starts. A head that cannot be checked counts as alive: it is gone
only when it never wrote `head.pid`, or wrote it on this host and boot and its process is gone
(the PID check of `local.alive`). A process of the user whose working directory is in the launch
directory (a Snakemake started by hand) also holds it. This host only: `/proc` shows no other.
"""

import os
import stat
from pathlib import Path

from spectio.runner.headscript import LOCK
from spectio.runner.local import alive, checkable, read_head_pid
from spectio.runner.rundir import RUN_ID, private_dir, read_small, run_paths

CONFIGS = ("nextflow.config", ".nextflow")  # what Nextflow loads from its launch directory


class NotResumable(ValueError):
    """Why a Resume cannot run now; `reason` is one of `actions.resume`'s (api §5)."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def check_dirs(runs_root: Path, run_id: str) -> tuple[int, int]:
    """The run's launch and work directories under req. 10 again, and no planted Nextflow
    configuration in the launch directory; returns its device and inode."""
    try:
        with private_dir(runs_root, run_id, "work"):
            pass
        with private_dir(runs_root, run_id, "launch") as fd:
            for name in CONFIGS:
                try:
                    st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                kind = stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)
                if not kind or st.st_uid != os.geteuid() or st.st_mode & 0o022:
                    raise NotResumable(
                        "launch_dir_refused",
                        f"{name} in the launch directory is not the user's, or others can write it",
                    )
            st = os.fstat(fd)
            return st.st_dev, st.st_ino
    except NotResumable:
        raise
    except (OSError, ValueError) as exc:
        raise NotResumable("launch_dir_refused", f"the directories of {run_id}: {exc}") from None


def head_gone(runs_root: Path, run_id: str) -> None:
    """Raise NotResumable unless the run's head is proven gone."""
    try:
        head = read_head_pid(run_paths(runs_root, run_id).launch_dir)
    except (OSError, ValueError) as exc:
        message = f"the head of {run_id} cannot be checked: {exc}"
        raise NotResumable("head_unverified", message) from None
    if head is None:
        return  # it never started
    if not checkable(head.host, head.boot_id):
        message = f"the head of {run_id} ran on {head.host} or before a restart: not checkable"
        raise NotResumable("head_unverified", message)
    if alive(head):
        raise NotResumable("running", f"the head of {run_id} still runs (PID {head.pid})")


def processes_in(path: Path) -> list[int]:
    """The processes, other than this one, whose working directory is `path` or below it."""
    target = os.path.realpath(path)
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cwd = os.readlink(entry / "cwd")
        except OSError:  # ended, or not ours
            continue
        if cwd == target or cwd.startswith(target + "/"):
            found.append(int(entry.name))
    return found


def _lock_holder(runs_root: Path, run_id: str) -> str | None:
    with private_dir(runs_root, run_id, "launch") as fd:
        raw = read_small(fd, LOCK, cap=64)
    if raw is None:
        return None
    holder = raw.decode("ascii", "replace").strip()
    if not RUN_ID.fullmatch(holder):
        raise NotResumable("launch_dir_refused", f"{LOCK} does not hold a run ID")
    return holder


def prove(runs_root: Path, dir_run_id: str, parent_run_id: str) -> tuple[int, int]:
    """Whether a Resume of `parent_run_id` may run in `dir_run_id`'s directories now: their
    device and inode, or NotResumable."""
    found = check_dirs(runs_root, dir_run_id)
    head_gone(runs_root, parent_run_id)
    try:
        holder = _lock_holder(runs_root, dir_run_id)
    except NotResumable:
        raise
    except (OSError, ValueError) as exc:
        raise NotResumable("launch_dir_refused", f"{LOCK}: {exc}") from None
    if holder is not None and holder != parent_run_id:
        head_gone(runs_root, holder)
    launch_dir = run_paths(runs_root, dir_run_id).launch_dir
    pids = processes_in(launch_dir)
    if pids:
        raise NotResumable("running", f"a process (PID {pids[0]}) runs in {launch_dir}")
    return found


def clear_stale_lock(runs_root: Path, run_id: str) -> None:
    """Remove the lock a killed head left; only after `prove`, which found its head gone."""
    with private_dir(runs_root, run_id, "launch") as fd:
        try:
            os.unlink(LOCK, dir_fd=fd)
        except FileNotFoundError:
            pass
