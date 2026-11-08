"""File modes of dev-env §15.3 req. 5 (P1 Task 15): private directories are 0700 and private
files 0600. Both are created at their mode and never chmod-ed after the write, so no umask can
loosen them, and an existing directory is checked, never tightened (inbox #83 rule 1).
"""

import errno
import os
import secrets
import stat
from pathlib import Path


def open_secure_dir(path: Path, *, create: bool = True) -> int:
    """A descriptor on `path`, a real directory of this user with no group or other bit, made
    with mode 0700 when it is missing and `create`. Raises PermissionError for a symlink, a
    file, or a directory that is another user's or has a group or other bit, naming its owner
    and mode; FileNotFoundError when it (or, with `create`, its parent) is missing."""
    if create:
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            pass
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"{path}: its parent directory does not exist") from exc
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PermissionError(
                f"{path} must be a real directory, not a symlink or a file: {exc.strerror}"
            ) from exc
        raise
    st = os.fstat(fd)
    if st.st_uid != os.geteuid() or st.st_mode & 0o077:
        os.close(fd)
        raise PermissionError(
            f"{path} must be a directory of yours with mode 0700 (owner uid {st.st_uid}, "
            f"mode {stat.S_IMODE(st.st_mode):o}): chmod 700 {path}"
        )
    return fd


def secure_dir(path: Path) -> None:
    """`path` created 0700, or an existing private directory of this user (`open_secure_dir`)."""
    os.close(open_secure_dir(path))


def write_file(dir_fd: int, name: str, data: bytes, *, exclusive: bool = False) -> None:
    """Write `data` to a new 0600 file under a temporary name in the directory, then move it
    to `name` atomically: replacing what is there, or, with `exclusive`, by a hard link that
    raises FileExistsError when `name` exists, so that the file can serve as a lock and is never
    seen empty or partial."""
    tmp = f".{name}.{secrets.token_hex(8)}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if exclusive:
            os.link(tmp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
        else:
            os.replace(tmp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    finally:
        try:
            os.unlink(tmp, dir_fd=dir_fd)
        except FileNotFoundError:
            pass


def write_secret(path: Path, data: bytes) -> None:
    """Replace `path` atomically with a 0600 file holding `data` (`write_file`); its directory
    must exist."""
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        write_file(fd, path.name, data)
    finally:
        os.close(fd)
