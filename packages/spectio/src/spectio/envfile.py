"""The environments file, `environments.toml` next to `spectio.toml` (FU-P3-86b; api §5.4,
Where definitions live; dev-env §15.3 req. 18).

Read without following a symbolic link: the directory opened `O_DIRECTORY|O_NOFOLLOW`, the file
`openat` with `O_NOFOLLOW|O_NONBLOCK` (a FIFO never blocks), both checked with `fstat` (this
user's, or root's for the directory, and not writable by group or others), at most 64 KiB + 1
byte read. Five states: `missing`, `ok`, `refused` (the owner or mode checks, or an open that
fails with EACCES, EPERM, ELOOP or ENOTDIR), `invalid` (it does not parse, breaks a rule or is
over a cap) and `unreachable`: any other I/O error opening or reading the file or its directory
(ESTALE or EIO on NFS), or the server's file pool's timeout. `check_config` follows links, so
it is not used here.

A write (`update`) holds one process lock: it reads the file again, applies the change, renders
the text and parses it back strictly, checks that the file's identity (`fstat` fields and the
SHA-256 of its bytes) is still that of its read, then writes a 0600 temporary through the
directory's descriptor and renames it into place (`fsmodes.write_file`, req. 5). A `refused` or
`invalid` file is never overwritten; an `unreachable` one raises Stalled, and an I/O error of
the write itself (ENOSPC, EDQUOT) is raised as it is. Accepted risk (api §5.4): the lock is per
process, so a hand edit on NFS in the few milliseconds between the check and the rename is lost.

The same code reads and writes the catalog file, `catalog.toml` (api §5.6): a `Kind` names the
file, its table, its entry model and its caps; `read_kind` and `update_kind` take one, and
`read_file`, `update` and `parse` are those of `environments.toml`.
"""

import errno
import hashlib
import os
import re
import stat
import threading
import tomllib
import unicodedata
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from spectio.config import _toml_value, config_path
from spectio.environments import NAME, RESERVED, Environment
from spectio.fsmodes import write_file
from spectio.runner.types import Stalled

FILE = "environments.toml"
MAX_BYTES = 64 * 1024
MAX_ENVIRONMENTS = 32
MAX_DETAIL = 200
LOCK_TIMEOUT_S = 5.0  # a write waits this long for the one before it, then gives up
State = Literal["missing", "ok", "refused", "invalid", "unreachable"]
Identity = tuple[int, int, int, int, str]  # st_dev, st_ino, st_size, st_mtime_ns, SHA-256
E = TypeVar("E", bound=BaseModel)
_AT = re.compile(r" ?\((at line \d+, column \d+|at end of document)\)\Z")  # tomllib's place
_REFUSED = (errno.EACCES, errno.EPERM, errno.ELOOP, errno.ENOTDIR)  # else an open is unreachable
_WRITE = threading.Lock()  # one write at a time in this process


@dataclass(frozen=True)
class Kind(Generic[E]):
    """A definitions file next to `spectio.toml`: one `[<table>.<name>]` per entry."""

    file: str
    table: str
    model: type[E]
    max_entries: int
    reserved: frozenset[str]  # names no entry may take
    has_default: bool  # a top-level `default`
    max_bytes: int = MAX_BYTES

    def path(self) -> Path:
        """The one path of the file: next to `spectio.toml`, whatever `data_dir` says."""
        return config_path().parent / self.file


@dataclass(frozen=True)
class File(Generic[E]):
    state: State
    detail: str | None = None
    default: str | None = None
    entries: tuple[E, ...] = ()  # in name order
    identity: Identity | None = None  # None when missing

    @property
    def environments(self) -> tuple[E, ...]:
        return self.entries


ENVIRONMENTS = Kind(FILE, "environments", Environment, MAX_ENVIRONMENTS, RESERVED, True)
EnvFile = File[Environment]
Change = Callable[[EnvFile], tuple[str | None, list[Environment]]]


class Unusable(Exception):
    """A write over a file that is `refused` or `invalid`, or in a directory that cannot be
    used: nothing is written."""

    def __init__(self, state: State, detail: str | None) -> None:
        super().__init__(detail or state)
        self.state, self.detail = state, detail


class Changed(Exception):
    """The file changed between the write's read and its rename: nothing is written."""


def environments_path() -> Path:
    return ENVIRONMENTS.path()


def _clean(text: str) -> str:
    """No control or format character, at most MAX_DETAIL characters."""
    kept = "".join(" " if unicodedata.category(c)[0] in "CZ" else c for c in text)
    return " ".join(kept.split())[:MAX_DETAIL]


def _mode(st: os.stat_result) -> str:
    return f"owner uid {st.st_uid}, mode {stat.S_IMODE(st.st_mode):o}"


class _Refused(Exception):
    pass


class _Unreachable(Exception):
    pass


def _open_dir(directory: Path) -> int:
    """A descriptor on the file's directory: this user's or root's, not writable by group or
    others, not a symbolic link. Raises FileNotFoundError, or _Refused or _Unreachable with the
    reason."""
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        raise
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise _Refused(f"{directory} is not a real directory (a symbolic link?)") from None
        if exc.errno in _REFUSED:
            raise _Refused(f"{directory} cannot be opened: {exc.strerror}") from None
        raise _Unreachable(f"{directory} cannot be opened: {exc.strerror}") from None
    try:
        st = os.fstat(fd)
    except OSError as exc:
        os.close(fd)
        raise _Unreachable(f"{directory} cannot be read: {exc.strerror}") from None
    if st.st_uid not in (0, os.geteuid()) or st.st_mode & 0o022:
        os.close(fd)
        raise _Refused(f"{directory} must be yours and not writable by others ({_mode(st)})")
    return fd


def _read_in(kind: Kind[E], dir_fd: int, name: str, cached: File[E] | None) -> File[E]:
    """The file in the directory `dir_fd`, parsed; `cached` when its identity is unchanged."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        return File("missing")
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return File("refused", f"{name} is a symbolic link")
        state: State = "refused" if exc.errno in _REFUSED else "unreachable"
        return File(state, _clean(f"{name} cannot be opened: {exc.strerror}"))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return File("refused", f"{name} is not a regular file")
        if st.st_uid != os.geteuid() or st.st_mode & 0o022:
            return File(
                "refused", f"{name} must be a file of yours that others cannot write ({_mode(st)})"
            )
        key = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        if cached is not None and cached.identity is not None and cached.identity[:4] == key:
            return cached
        chunks, size = [], 0
        while size <= kind.max_bytes and (chunk := os.read(fd, kind.max_bytes + 1 - size)):
            chunks.append(chunk)
            size += len(chunk)
    except OSError as exc:  # ESTALE, EIO: only the built-ins are listed (CR-P3FU86BCD-01)
        return File("unreachable", _clean(f"{name} cannot be read: {exc.strerror}"))
    finally:
        os.close(fd)
    data = b"".join(chunks)
    found = _parse(kind, data)
    return replace(found, identity=(*key, hashlib.sha256(data).hexdigest()))


def _invalid(detail: str) -> File[Any]:
    return File("invalid", _clean(detail))


def _place(loc: tuple[int | str, ...]) -> str:
    """A pydantic location, keeping only parts that are names of a closed character set."""
    return ".".join(str(p) if NAME.fullmatch(str(p).replace("_", "-")) else "?" for p in loc)


def parse(data: bytes, builtin_names: Collection[str] | None = None) -> EnvFile:
    """The environments file's bytes, checked whole: any mistake makes it `invalid`, with a
    short detail that never holds the file's bytes. `builtin_names`, when given, are what
    `default` may name besides the file's own environments (`check_default`)."""
    result = _parse(ENVIRONMENTS, data)
    return result if builtin_names is None else check_default(result, builtin_names)


def _parse(kind: Kind[E], data: bytes) -> File[E]:
    if len(data) > kind.max_bytes:
        return _invalid(f"over {kind.max_bytes // 1024} KiB")
    try:
        doc = tomllib.loads(data.decode("utf-8"))
    except UnicodeDecodeError:
        return _invalid("not UTF-8 text")
    except tomllib.TOMLDecodeError as exc:  # its message may quote the file: keep its place only
        message = str(exc)
        place = _AT.search(message)
        head = re.split(r"['\"(]", message[: place.start() if place else len(message)])[0]
        return _invalid(f"not TOML: {head.strip()} {place.group(0).strip() if place else ''}")
    except (RecursionError, ValueError):  # deep nesting (SEC-PRE-FU86-R1-05)
        return _invalid("not TOML: nested too deeply")
    top = {kind.table, "default"} if kind.has_default else {kind.table}
    unknown = set(doc) - top
    if unknown:
        allowed = " and ".join(sorted(top))
        return _invalid(f"{len(unknown)} unknown top-level key(s): only {allowed}")
    default, tables = doc.get("default"), doc.get(kind.table, {})
    if default is not None and not (isinstance(default, str) and NAME.fullmatch(default)):
        return _invalid("default is not an environment name")
    if not isinstance(tables, dict):
        return _invalid(f"{kind.table} is not a table")
    if len(tables) > kind.max_entries:
        return _invalid(f"more than {kind.max_entries} {kind.table}")
    found = []
    for key, table in sorted(tables.items()):
        if not NAME.fullmatch(key):
            return _invalid(f"a name in {kind.table} is not valid: a-z, 0-9 and '-', at most 32")
        if key in kind.reserved:
            return _invalid(f"{kind.table}.{key}: {key} is a reserved name")
        if not isinstance(table, dict) or "name" in table:
            return _invalid(f"{kind.table}.{key}: a table, named by its key")
        try:
            found.append(kind.model.model_validate({**table, "name": key}))
        except ValidationError as exc:
            first = exc.errors()[0]
            message = "not a valid value" if first["type"] == "value_error" else first["msg"]
            where = ".".join(p for p in (kind.table, key, _place(first["loc"])) if p)
            return _invalid(f"{where}: {message}")
    return File("ok", default=default, entries=tuple(found))


def check_default(found: File[E], builtin_names: Collection[str]) -> File[E]:
    """`invalid` when the file's `default` names no environment, the built-ins included."""
    if found.state != "ok" or found.default is None:
        return found
    if found.default not in {*builtin_names, *(_table(e)[0] for e in found.entries)}:
        return replace(_invalid(f"default {found.default} names no environment"), identity=None)
    return found


def read_file(path: Path, builtin_names: Collection[str], cached: EnvFile | None = None) -> EnvFile:
    """The environments file at `path` (`environments_path()`), in one of its five states."""
    return read_kind(ENVIRONMENTS, path, builtin_names, cached)


def read_kind(
    kind: Kind[E], path: Path, builtin_names: Collection[str], cached: File[E] | None = None
) -> File[E]:
    """The file of `kind` at `path` (`kind.path()`), in one of its five states."""
    try:
        dir_fd = _open_dir(path.parent)
    except FileNotFoundError:
        return File("missing")
    except _Refused as exc:
        return File("refused", str(exc))
    except _Unreachable as exc:
        return File("unreachable", _clean(str(exc)))
    try:
        return check_default(_read_in(kind, dir_fd, path.name, cached), builtin_names)
    finally:
        os.close(dir_fd)


def _table(entry: BaseModel) -> tuple[str, dict[str, Any]]:
    """An entry's name (its key) and its TOML table: no unset value or empty sub-table."""
    data = entry.model_dump(exclude_none=True)
    name = data.pop("name")
    return name, {k: v for k, v in data.items() if v or not isinstance(v, dict)}


def render(default: str | None, entries: Iterable[BaseModel], table: str = "environments") -> bytes:
    lines = ["# Written by Spectio: a write keeps no comment."]
    if default is not None:
        lines.append(f"default = {_toml_value(default)}")
    for name, values in sorted(map(_table, entries), key=lambda t: t[0]):
        head = f"{table}.{name}"
        subs = [k for k, v in values.items() if isinstance(v, dict)]
        lines += ["", f"[{head}]"]
        lines += [f"{k} = {_toml_value(v)}" for k, v in values.items() if k not in subs]
        for sub in subs:
            lines += ["", f"[{head}.{sub}]"]
            lines += [f"{k} = {_toml_value(v)}" for k, v in values[sub].items()]
    return ("\n".join(lines) + "\n").encode()


def update(path: Path, builtin_names: Collection[str], change: Change) -> EnvFile:
    """`update_kind` of the environments file."""
    return update_kind(ENVIRONMENTS, path, builtin_names, change)


def update_kind(
    kind: Kind[E],
    path: Path,
    builtin_names: Collection[str],
    change: Callable[[File[E]], tuple[str | None, list[E]]],
) -> File[E]:
    """Apply `change` (the current file → its new default and entries) and write the file
    whole. Raises Unusable, Changed, Stalled when an earlier write still holds the lock or the
    file is `unreachable`, OSError when the write fails, and whatever `change` raises (nothing
    is written then). Returns the file as written."""
    if not _WRITE.acquire(timeout=LOCK_TIMEOUT_S):
        raise Stalled(f"another write of {kind.file} has not ended")
    try:
        try:
            dir_fd = _open_dir(path.parent)
        except FileNotFoundError:
            raise Unusable("missing", f"{path.parent} does not exist: run spectio init") from None
        except _Refused as exc:
            raise Unusable("refused", str(exc)) from None
        except _Unreachable as exc:
            raise Stalled(str(exc)) from None
        try:
            current = check_default(_read_in(kind, dir_fd, path.name, None), builtin_names)
            if current.state == "unreachable":
                raise Stalled(current.detail or f"{kind.file} cannot be read")
            if current.state not in ("missing", "ok"):
                raise Unusable(current.state, current.detail)
            default, entries = change(current)
            data = render(default, entries, kind.table)
            written = check_default(_parse(kind, data), builtin_names)
            # what was rendered must read back as it was asked: a render bug never lands
            tables = sorted(map(_table, entries), key=lambda t: t[0])
            asked = [kind.model.model_validate({**t, "name": n}) for n, t in tables]
            if written.state != "ok" or list(written.entries) != asked:
                raise ValueError(f"the rendered file does not read back: {written.detail}")
            again = _read_in(kind, dir_fd, path.name, None)
            if again.state == "unreachable":
                raise Stalled(again.detail or f"{kind.file} cannot be read")
            if again.identity != current.identity:
                raise Changed(f"{kind.file} changed since it was read: read it again")
            write_file(dir_fd, path.name, data)
        finally:
            os.close(dir_fd)
    finally:
        _WRITE.release()
    return written
