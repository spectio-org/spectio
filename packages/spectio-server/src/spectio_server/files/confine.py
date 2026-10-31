"""Reads confined to a run's roots: the walk of checking-scenarios §11.1 (revised 2026-10-28,
SEC-150) and dev-env §15.3 req. 13.

A path is a name relative to a root, never absolute and with no `.` or `..` part. It is walked
one component at a time from the root's descriptor, so no directory can be swapped for a
symlink between a check and the open:

- each directory with `openat(dirfd, name, O_RDONLY|O_DIRECTORY|O_NOFOLLOW)`;
- the last component with `O_RDONLY|O_NOFOLLOW|O_NONBLOCK`, so a FIFO never blocks the open;
- `fstat` on each: owned by the user, and the last one a regular file (or a directory, for a
  listing); a FIFO, a device or another owner's file is refused;
- a last component that is a symlink (`ELOOP`) is read with `readlinkat` and followed only when
  its target lies in the run's work directory (Nextflow's `publishDir` in `'symlink'` mode); the
  target is then walked the same way from the work directory's descriptor, and a second symlink
  is refused.

The test of the link target is on its text (the work directory's path as the run was given it):
no `realpath`, which would follow links on the way. Listings read entries with
`fstatat(AT_SYMLINK_NOFOLLOW)`, hide those of another owner and anything but files, folders and
links, and show a link to anywhere but the work directory as `link_outside`.
"""

import errno
import os
import posixpath
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Literal

TAIL = 65536  # the bytes a read returns by default
MAX_READ = 1048576  # the most one read or one Range response returns
NAME_MAX = 255  # bytes in one path component (Linux `NAME_MAX`)
PATH_MAX = 4096  # bytes in a whole name (Linux `PATH_MAX`)

_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC


class NotAllowed(Exception):
    """A name or a file that is never served: the reason is safe to show."""


class NotFound(Exception):
    """Nothing there (yet, or any more)."""


@dataclass(frozen=True)
class Root:
    """An open root of a run and its path as the run was given it (for link targets)."""

    fd: int
    path: PurePosixPath


@dataclass(frozen=True)
class Entry:
    name: str
    type: Literal["dir", "file", "link_outside"]
    size: int | None
    mtime: float | None


@dataclass(frozen=True)
class Listing:
    entries: list[Entry]
    truncated: bool


def safe_rel(name: str) -> PurePosixPath:
    """`name` as a relative path of plain components; raises NotAllowed for an absolute path, an
    empty, `.` or `..` component, a control character (NUL included), or a name longer than
    `NAME_MAX` bytes a component or `PATH_MAX` bytes in all (SEC-P3T28-04)."""
    if not name or name.startswith("/") or any(ord(c) < 0x20 or ord(c) == 0x7F for c in name):
        raise NotAllowed("not a name this server serves")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise NotAllowed("not a name this server serves")
    if len(name.encode(errors="surrogatepass")) > PATH_MAX or any(
        len(part.encode(errors="surrogatepass")) > NAME_MAX for part in parts
    ):
        raise NotAllowed("not a name this server serves")
    return PurePosixPath(*parts)


@contextmanager
def opened_root(path: Path) -> Iterator[Root]:
    """A root, opened as configured (the runs root's own path is trusted, req. 10)."""
    fd = os.open(path, _DIR & ~os.O_NOFOLLOW)
    try:
        yield Root(fd, PurePosixPath(path))
    finally:
        os.close(fd)


def _mine(fd: int, what: str) -> os.stat_result:
    st = os.fstat(fd)
    if st.st_uid != os.geteuid():
        raise NotAllowed(f"{what}: not yours")
    return st


def _openat(dir_fd: int, name: str, flags: int) -> int:
    try:
        return os.open(name, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        raise NotFound(name) from None
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise NotAllowed(f"{name}: a link or not a folder on the way") from None
        if exc.errno in (errno.EACCES, errno.EPERM, errno.ENXIO):
            raise NotAllowed(f"{name}: cannot be opened ({exc.strerror})") from None
        raise


def _walk_dirs(root: Root, parts: tuple[str, ...]) -> int:
    """A descriptor on `root/parts…`, each a directory of the user opened with O_NOFOLLOW."""
    fd = os.dup(root.fd)
    try:
        for part in parts:
            child = _openat(fd, part, _DIR)
            os.close(fd)
            fd = child
            _mine(fd, part)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _link_target(root: Root, rel: PurePosixPath, dir_fd: int, work: Root | None) -> PurePosixPath:
    """The path, relative to the work directory, that the symlink `rel` points to; raises
    NotAllowed when it points anywhere else."""
    target = os.readlink(rel.name, dir_fd=dir_fd)
    whole = posixpath.normpath(posixpath.join(str(root.path / rel.parent), target))
    base = None if work is None else str(work.path)
    if base is None or not whole.startswith(base.rstrip("/") + "/"):
        raise NotAllowed(f"{rel.name}: a link outside the run")
    return safe_rel(whole[len(base.rstrip("/")) + 1 :])


def _open_fd(root: Root, rel: PurePosixPath, work: Root | None, follow: bool) -> int:
    dir_fd = _walk_dirs(root, rel.parts[:-1])
    try:
        try:
            fd = _openat(dir_fd, rel.name, _FILE)
        except NotAllowed:
            st = os.stat(rel.name, dir_fd=dir_fd, follow_symlinks=False)
            if not stat.S_ISLNK(st.st_mode) or not follow or work is None:
                raise
            inside = _link_target(root, rel, dir_fd, work)
            return _open_fd(work, inside, None, follow=False)  # a second link is refused
    finally:
        os.close(dir_fd)
    try:
        st = _mine(fd, rel.name)
        if not stat.S_ISREG(st.st_mode):
            raise NotAllowed(f"{rel.name}: not a regular file")
    except BaseException:
        os.close(fd)
        raise
    return fd


def open_confined(root: Root, rel: PurePosixPath, *, work: Root | None = None) -> BinaryIO:
    """The regular file `rel` below `root`, walked as the module says; raises NotAllowed or
    NotFound. A last-component link is followed only into `work`."""
    fd = _open_fd(root, safe_rel(str(rel)), work, follow=True)
    return os.fdopen(fd, "rb", buffering=0)


def list_confined(root: Root, rel: PurePosixPath, cap: int, *, work: Root | None = None) -> Listing:
    """The entries of the folder `rel` below `root` (`.` for the root), at most `cap`, in the
    order the file system gives them."""
    parts = () if str(rel) == "." else safe_rel(str(rel)).parts
    fd = _walk_dirs(root, parts)
    entries: list[Entry] = []
    truncated = False
    try:
        with os.scandir(fd) as found:
            for item in found:
                if len(entries) >= cap:
                    truncated = True
                    break
                entry = _entry(root, PurePosixPath(*parts, item.name), fd, work)
                if entry is not None:
                    entries.append(entry)
    finally:
        os.close(fd)
    return Listing(entries, truncated)


def _entry(root: Root, rel: PurePosixPath, dir_fd: int, work: Root | None) -> Entry | None:
    try:
        st = os.stat(rel.name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError:
        return None  # gone since the listing
    if st.st_uid != os.geteuid():
        return None
    if stat.S_ISLNK(st.st_mode):
        try:
            with open_confined(root, rel, work=work) as f:
                st = os.fstat(f.fileno())
        except (NotAllowed, NotFound, OSError):
            return Entry(rel.name, "link_outside", None, None)
    if stat.S_ISDIR(st.st_mode):
        return Entry(rel.name, "dir", None, st.st_mtime)
    if stat.S_ISREG(st.st_mode):
        return Entry(rel.name, "file", st.st_size, st.st_mtime)
    return None  # a FIFO, a socket, a device: not shown


def stat_confined(root: Root, rel: PurePosixPath) -> os.stat_result | None:
    """`fstatat(AT_SYMLINK_NOFOLLOW)` of `rel` below `root`, None when it is missing; raises
    NotAllowed when a folder on the way is refused, NotFound when one is missing."""
    rel = safe_rel(str(rel))
    dir_fd = _walk_dirs(root, rel.parts[:-1])
    try:
        return os.stat(rel.name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    finally:
        os.close(dir_fd)


def size_of(f: BinaryIO) -> int:
    return os.fstat(f.fileno()).st_size


def tail(f: BinaryIO, max_bytes: int = TAIL) -> bytes:
    """The last `max_bytes` (at most MAX_READ) of the file."""
    n = min(max_bytes, MAX_READ)
    return os.pread(f.fileno(), n, max(0, size_of(f) - n))


def read_at(f: BinaryIO, start: int, n: int) -> bytes:
    """At most `n` bytes (at most MAX_READ) from `start`."""
    return os.pread(f.fileno(), min(n, MAX_READ), start)
