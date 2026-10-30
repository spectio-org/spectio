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
import secrets
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

RUN_ID = re.compile(r"run_[0-7][0-9A-HJKMNP-TV-Z]{25}")  # a ULID with its prefix (api §7)
MAX_SMALL_FILE = 1048576  # a manifest, PID, exit or marker file is never larger

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


def check_launch_dir(runs_root: Path, run_id: str, launch_dir: Path) -> None:
    """Refuse a launch directory that is not the run's, or whose path is not private."""
    if launch_dir != run_paths(runs_root, run_id).launch_dir:
        raise PermissionError(f"{launch_dir} is not the launch directory of {run_id}")
    os.close(open_private(runs_root, (run_id, "launch")))


def write_file(dir_fd: int, name: str, data: bytes) -> None:
    """Replace `name` in the directory atomically with a 0600 file holding `data`."""
    tmp = f".{name}.{secrets.token_hex(8)}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    except BaseException:
        try:
            os.unlink(tmp, dir_fd=dir_fd)
        except FileNotFoundError:
            pass
        raise


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
    """Write `<run_dir>/.spectio/run.json` (P1 Task 17 calls it when the run is created)."""
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
