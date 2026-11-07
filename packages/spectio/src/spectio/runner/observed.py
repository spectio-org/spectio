"""Runs started from a terminal: the pointers in `~/.spectio/observed/` (P1 Task 25;
architecture §13.8, dev-env §15.3 req. 12, "Server, scan").

A bridge that starts without `SPECTIO_RUN_ID` writes `<run ID>.json` there. Every pointer is
untrusted input: `~/.spectio` and `observed` must be private directories of the user (a loose one
is skipped whole), each pointer a private regular file of the user under `MAX_POINTER_BYTES`,
opened relative to the checked directory with O_NOFOLLOW, parsed strictly, its file name its run
ID. The runs root wins: a pointer whose run ID names a run directory, or whose launch directory
is not absolute and normalised or lies in the runs root, is skipped and counted. The launch
directory itself is not checked (a project directory is often group-writable); its `.spectio/`
is, by the spool reader.
"""

import errno
import json
import os
import posixpath
import stat
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from spectio.runner.rundir import RUN_ID

MAX_POINTER_BYTES = 4096
ENDED = "ended"

_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC


class ObservedRun(BaseModel):
    """A pointer: exactly the keys of architecture §13.8, and the PID fields of the head's PID
    file (schedulers §3.1.1). Nothing from the run's environment, arguments or parameters."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str = Field(pattern=rf"^{RUN_ID.pattern}$")
    launch_dir: str = Field(max_length=4096)
    engine: Literal["nextflow", "snakemake"]
    engine_version: str | None = Field(max_length=64, pattern=r"^[0-9A-Za-z.+_-]*$")
    bridge_version: str = Field(max_length=64, pattern=r"^[0-9A-Za-z.+_-]*$")
    host: str = Field(pattern=r"^[A-Za-z0-9._-]{1,255}$")
    pid: int = Field(ge=1, le=2**31 - 1)
    pid_start_time: str = Field(pattern=r"^[0-9]{1,20}$")
    boot_id: str = Field(pattern=r"^[0-9a-f-]{36}$")


@dataclass(frozen=True)
class ObservedScan:
    """One scan. `skipped` counts the pointers refused, by reason; `seen` holds the run IDs
    looked at (read or refused), so that the caller does not read them again. `mtime_ns` is
    the directory's mtime when it was listed whole, else None: the next scan lists it again."""

    runs: list[ObservedRun]
    skipped: Counter[str]
    seen: frozenset[str]
    mtime_ns: int | None


def check_observed_launch_dir(runs_root: Path, launch_dir: str) -> Path:
    """The launch directory of a pointer, refused (ValueError) unless absolute and normalised,
    and outside the runs root, as configured and as the system resolves it."""
    if not launch_dir.startswith("/") or posixpath.normpath(launch_dir) != launch_dir:
        raise ValueError(f"{launch_dir!r} is not an absolute, normalised path")
    roots = {posixpath.normpath(str(runs_root)), os.path.realpath(runs_root)}
    for path in {launch_dir, os.path.realpath(launch_dir)}:
        if any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots):
            raise ValueError(f"{launch_dir} lies in the runs root")
    return Path(launch_dir)


def _private(name: str, dir_fd: int) -> int:
    fd = os.open(name, _DIR, dir_fd=dir_fd)
    st = os.fstat(fd)
    if st.st_uid != os.geteuid() or st.st_mode & 0o077:
        os.close(fd)
        raise PermissionError(f"{name}: not a private directory of this user (req. 12)")
    return fd


@contextmanager
def _observed_dir(home: Path, *parts: str, create: bool = False) -> Iterator[int]:
    """`home/.spectio/observed/parts…`, each a private directory of the user; the last part is
    made 0700 when `create`. Raises FileNotFoundError, PermissionError or OSError."""
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)  # the home, as given
    try:
        names = (".spectio", "observed", *parts)
        for i, name in enumerate(names):
            if create and i == len(names) - 1:
                with suppress(FileExistsError):
                    os.mkdir(name, 0o700, dir_fd=fd)
            child = _private(name, fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def scan_observed(
    home: Path,
    runs_root: Path,
    known: set[str],
    cap: int,
    *,
    since_ns: int | None = None,
    ended: bool = False,
) -> ObservedScan:
    """Read at most `cap` pointers of `~/.spectio/observed/` (of `ended/` with `ended`, which
    only a rebuild reads) whose run ID is not in `known`, in name order. When the directory's
    mtime is `since_ns`, nothing is listed."""
    skipped: Counter[str] = Counter()
    try:
        with _observed_dir(home, *((ENDED,) if ended else ())) as fd:
            mtime_ns: int | None = os.fstat(fd).st_mtime_ns
            if since_ns is not None and mtime_ns == since_ns:
                return ObservedScan([], skipped, frozenset(), mtime_ns)
            names = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    name = entry.name
                    if name.startswith(".") or name == ENDED:
                        continue  # a bridge's temporary file; the ended pointers
                    if not name.endswith(".json") or not RUN_ID.fullmatch(name[:-5]):
                        skipped["bad_name"] += 1
                    elif name[:-5] not in known:
                        names.append(name)
            names.sort()
            if len(names) > cap:
                mtime_ns = None  # the rest is read at the next scans
            runs, seen = [], set()
            for name in names[:cap]:
                seen.add(name[:-5])
                found = _pointer(fd, name, runs_root)
                if isinstance(found, str):
                    skipped[found] += 1
                else:
                    runs.append(found)
    except FileNotFoundError:
        return ObservedScan([], skipped, frozenset(), None)
    except OSError:  # PermissionError, a symlink (ELOOP), not a directory
        skipped["observed_refused"] += 1
        return ObservedScan([], skipped, frozenset(), None)
    return ObservedScan(runs, skipped, frozenset(seen), mtime_ns)


def _pointer(dir_fd: int, name: str, runs_root: Path) -> ObservedRun | str:
    """The pointer `name`, or the reason it is skipped."""
    try:
        fd = os.open(name, _FILE, dir_fd=dir_fd)
    except FileNotFoundError:
        return "gone"
    except OSError as exc:
        return "symlink" if exc.errno == errno.ELOOP else "unreadable"
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return "not_regular"
        if st.st_uid != os.geteuid():
            return "foreign_owner"
        if st.st_mode & 0o077:
            return "loose_mode"
        data = os.read(fd, MAX_POINTER_BYTES + 1)
    except OSError:
        return "unreadable"
    finally:
        os.close(fd)
    if len(data) > MAX_POINTER_BYTES:
        return "too_large"
    try:
        run = ObservedRun.model_validate(json.loads(data))
    except (ValueError, ValidationError):  # bad JSON or UTF-8 included
        return "invalid"
    if f"{run.run_id}.json" != name:
        return "name_mismatch"
    try:
        check_observed_launch_dir(runs_root, run.launch_dir)
    except ValueError:
        return "launch_dir"
    if os.path.lexists(runs_root / run.run_id):
        return "run_dir"
    return run


def end_pointer(home: Path, run_id: str) -> None:
    """Move an ended run's pointer to `observed/ended/` (made 0700); a missing one is left."""
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(f"{run_id!r} is not a run ID")
    name = f"{run_id}.json"
    with _observed_dir(home) as observed, _observed_dir(home, ENDED, create=True) as ended:
        with suppress(FileNotFoundError):
            os.rename(name, name, src_dir_fd=observed, dst_dir_fd=ended)
