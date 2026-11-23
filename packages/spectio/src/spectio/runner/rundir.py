"""Run directories: `<runs_root>/<run_id>/{.spectio/run.json, launch/.spectio/…, work}` (P1 Task 9,
Assumption 21).

Below the runs root, each directory is created 0700 and opened one path component at a time
with O_NOFOLLOW; it must be a real directory of the user with no group or other bits, and the
runs root must be the user's and not writable by group or others (dev-env §15.3 req. 10). Files
are opened relative to the checked descriptor, with O_NOFOLLOW, and the small ones read back
are size-capped and parsed strictly. The run ID, and so every path, is derived and checked,
never read from a file.
"""

import errno
import os
import re
import shutil
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from spectio.fsmodes import write_file as write_file  # its home before P1 Task 15
from spectio_sdk.targets import RunTarget

RUN_ID = re.compile(r"run_[0-7][0-9A-HJKMNP-TV-Z]{25}")  # a ULID with its prefix (api §7)
MAX_SMALL_FILE = 1048576  # a manifest, PID, exit or marker file is never larger

# A runs directory is on a nearly full disk when its file system is 90% used, or has less than
# 10 GiB free (FU-P3-74). The percentage catches a large shared file system that other people
# fill, as the EMBL /home was, 97% used (login-node audit 2026-11-08 §6); the floor catches a
# small disk whose percentage still looks fine, since one run's work directory can take GiBs.
FULL_PCT = 90
MIN_FREE = 10 * 2**30
_RUNS_ROOT_FIX = (
    "point SPECTIO_RUNS_ROOT (runs_root in spectio.toml, spectio init --runs-root) at a larger "
    "scratch or group file system"
)

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    launch_dir: Path
    work_dir: Path


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    location: str
    revision: str | None = None
    engine: Literal["nextflow", "snakemake"]


class RunManifest(BaseModel):
    """`.spectio/run.json`: what the index is rebuilt from (Assumption 21)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=rf"^{RUN_ID.pattern}$")
    name: str
    workflow: Workflow
    params: dict[str, JsonValue]
    profiles: list[str]
    created_at: AwareDatetime
    # A Resume's parent (P1 Task 30): the child runs in its lineage's directories
    parent_run_id: str | None = Field(None, pattern=rf"^{RUN_ID.pattern}$")
    # The run's environment as resolved at launch (FU-P3-86a, api §5.4): read at rebuild with
    # the validators of `spectio.environments`, so a bad one makes it `not_readable`, not the
    # run unreadable; none before FU-P3-86 (`not_recorded`).
    environment: dict[str, JsonValue] | None = None
    # One module or one rule (api §5.10, #161); None: the whole pipeline.
    target: RunTarget | None = None
    # The launch's `default_resources` and `config_file` (FU-P3-110a, api §5.7): read at rebuild
    # with the routes' validators, so a bad one is `not_readable` for that field only.
    default_resources: dict[str, JsonValue] | None = None
    config_file: dict[str, JsonValue] | None = None


def run_paths(runs_root: Path, run_id: str) -> RunPaths:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(f"{run_id!r} is not a run ID")
    run_dir = runs_root / run_id
    return RunPaths(run_dir, run_dir / "launch", run_dir / "work")


def open_private(root: Path, parts: Sequence[str], create: bool = False) -> int:
    """A descriptor on `root/parts…`, each part a private directory of the user, created 0700
    when `create`. `root` must be the user's and not writable by others. Raises
    PermissionError for a directory that is not private, OSError for a symlink or a file."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)  # the configured root, as given
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid() or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PermissionError(f"runs root {root}: not the user's, or writable by others")
        for part in parts:
            if not part or "/" in part or part in (".", ".."):
                raise ValueError(f"{part!r} is not one path component")
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            if st.st_uid != os.geteuid() or st.st_mode & 0o077:
                raise PermissionError(f"{part}: not a private directory of this user (req. 10)")
    except BaseException:
        os.close(fd)
        raise
    return fd


@contextmanager
def private_dir(root: Path, *parts: str, create: bool = False) -> Iterator[int]:
    fd = open_private(root, parts, create)
    try:
        yield fd
    finally:
        os.close(fd)


def make_run_dirs(runs_root: Path, run_id: str) -> RunPaths:
    """Create the run's directories, and the launch's `.spectio/events`, 0700 (SEC-P3T3-09)."""
    paths = run_paths(runs_root, run_id)
    for parts in ((run_id, "launch", ".spectio", "events"), (run_id, "work")):
        os.close(open_private(runs_root, parts, create=True))
    return paths


def runs_disk(runs_root: Path) -> tuple[str, str]:
    """`ok` or `warn`, and a detail, for the free space of the file system that holds
    `runs_root`, or its nearest existing parent before it is created; never raises. The used
    percentage is rounded up, as `df` shows it."""
    try:
        measured = next(p for p in (runs_root, *runs_root.parents) if p.is_dir())
        usage = shutil.disk_usage(measured)
    except OSError as exc:
        return "warn", f"cannot measure the free space of {runs_root}: {exc}"
    pct = -(-100 * usage.used // ((usage.used + usage.free) or 1))  # integer ceiling
    space = f"{usage.free / 2**30:.1f} GiB free, {pct}% used"
    if pct < FULL_PCT and usage.free >= MIN_FREE:
        return "ok", f"{space} at {measured}"
    where = (
        f"{runs_root}"
        if measured == runs_root
        else f"{runs_root} (not created yet, measured at {measured})"
    )
    return "warn", f"{where} is on a nearly full file system ({space}): {_RUNS_ROOT_FIX}"


def check_launch_dir(runs_root: Path, run_id: str, launch_dir: Path) -> None:
    """Refuse a launch directory that is not the run's, or whose path is not private."""
    if launch_dir != run_paths(runs_root, run_id).launch_dir:
        raise PermissionError(f"{launch_dir} is not the launch directory of {run_id}")
    os.close(open_private(runs_root, (run_id, "launch")))


def read_small(dir_fd: int, name: str, cap: int = MAX_SMALL_FILE) -> bytes | None:
    """The bytes of a regular file of the user that others cannot write, or None when missing.
    Raises PermissionError when it is refused, ValueError when larger than `cap`."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PermissionError(f"{name} is a symlink") from exc
        raise
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid():
            raise PermissionError(f"{name}: not a regular file of this user")
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PermissionError(f"{name}: writable by others")
        data = f.read(cap + 1)
    if len(data) > cap:
        raise ValueError(f"{name} is larger than {cap} bytes")
    return data


def write_run_manifest(run_dir: Path, manifest: RunManifest) -> None:
    """Write `<run_dir>/.spectio/run.json` (P1 Tasks 17 and 30 call it when the run is created)."""
    if run_dir.name != manifest.run_id:
        raise ValueError(f"the run ID {manifest.run_id} is not the directory's name")
    run_paths(run_dir.parent, manifest.run_id)
    with private_dir(run_dir.parent, manifest.run_id, ".spectio", create=True) as fd:
        write_file(fd, "run.json", manifest.model_dump_json().encode())


def read_run_manifest(run_dir: Path) -> RunManifest:
    """The manifest, parsed strictly; its run ID must be the directory's name (req. 10)."""
    run_paths(run_dir.parent, run_dir.name)
    with private_dir(run_dir.parent, run_dir.name, ".spectio") as fd:
        data = read_small(fd, "run.json")
    if data is None:
        raise FileNotFoundError(f"{run_dir}/.spectio/run.json")
    manifest = RunManifest.model_validate_json(data, strict=True)
    if manifest.run_id != run_dir.name:
        raise ValueError(f"the manifest's run ID {manifest.run_id} is not {run_dir.name}")
    return manifest
