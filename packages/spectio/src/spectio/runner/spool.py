"""Read a launch's spool: api-and-data-model.md §14.1, dev-env §15.3 req. 6 (P1 Task 3).

Every line is untrusted input: it is validated, never executed, and a line that fails is dropped
and counted by reason. The reader opens `.spectio` and `events` with O_NOFOLLOW, checks that each
is a private directory of the user (req. 12, as req. 10 checks a run directory), then opens each
file relative to the `events` descriptor, so a directory or file swapped for a symlink after a
check is never followed. Each read is bounded in lines, bytes and directory entries. Pure: no
database; the caller stores the batch in one transaction.
"""

import errno
import hashlib
import os
import stat
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from spectio.runner.types import EXCESS, REFUSED, SpoolBatch
from spectio_sdk.events import (
    MAX_EVENT_DEPTH,
    MAX_EVENT_NODES,
    MAX_FILE_BYTES,
    MAX_LINE_BYTES,
    MAX_SPOOL_FILES,
    SPOOL_FILE_NAME,
    SpoolEvent,
    UnknownEventType,
    parse_data,
)

CHUNK_BYTES = 1048576  # read at a time: the line buffer holds at most this plus MAX_LINE_BYTES
MAX_READ_BYTES = 2097152  # bytes one read takes from the files, skipped ones included
MAX_DIR_ENTRIES = 16 * MAX_SPOOL_FILES  # directory entries one read looks at
MAX_BAD_NAMES = 64  # names outside the grammar counted one by one; later ones as too_many_files

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
# A file that fails with one of these is refused for good; any other error is retried.
_REFUSALS = {
    errno.ELOOP: "symlink",  # swapped for a symlink since the lstat
    errno.EACCES: "unreadable",
    errno.ENXIO: "unreadable",  # a socket
    errno.ENOTDIR: "unreadable",
}


def read_spool(
    launch_dir: Path,
    run_id: str,
    launch_n: int,
    cursor: dict[str, int],
    max_lines: int = 5000,
    max_bytes: int = MAX_READ_BYTES,
) -> SpoolBatch:
    """Read at most `max_lines` lines and `max_bytes` bytes past `cursor`, in file name order.

    The caller owns `launch_dir` and the path to it: the runner loop (P1 Task 9) and the boot
    rebuild (Task 11), which checks the run directory (req. 10). This reader checks `.spectio`
    and `events` below it. It raises PermissionError when either is not a private directory of
    the user, and OSError when either is a symlink or not a directory; it returns an empty batch
    when either is missing (nothing written yet). A file that cannot be read is dropped and
    counted (`unreadable`, or `read_error` and retried by the next read); a file that is gone is
    skipped; neither stops the other files. Raises ValueError when `max_lines` is under 1 or
    `max_bytes` cannot hold one line.
    """
    if max_lines < 1 or max_bytes <= MAX_LINE_BYTES:
        raise ValueError("max_lines must be at least 1 and max_bytes more than MAX_LINE_BYTES")
    events: list[SpoolEvent] = []
    drops: Counter[str] = Counter()
    new = _checked(cursor, drops)
    dir_fd = _open_events_dir(launch_dir)
    if dir_fd is None:
        return SpoolBatch(events, new, drops)
    try:
        for name in _admit(dir_fd, launch_n, new, drops):
            if max_lines <= 0 or max_bytes <= 0:
                break
            offset = new[name]
            try:
                fd = _open_regular(dir_fd, name)
                if isinstance(fd, str):
                    drops[fd] += 1
                    new[name] = REFUSED
                    continue
                try:
                    size = os.fstat(fd).st_size
                    end = min(size, MAX_FILE_BYTES)
                    lines, new[name], used = _lines(fd, offset, end, max_lines, max_bytes)
                finally:
                    os.close(fd)
            except FileNotFoundError:
                continue  # gone since the listing, or since an earlier read
            except OSError as e:
                reason = _REFUSALS.get(e.errno or 0)
                drops[reason or "read_error"] += 1
                if reason:
                    new[name] = REFUSED
                continue
            max_lines -= len(lines)
            max_bytes -= used
            for raw in lines:
                event = "line_too_large" if raw is None else _event(raw, run_id, launch_n)
                if isinstance(event, str):
                    drops[event] += 1
                else:
                    events.append(event)
            if size > MAX_FILE_BYTES and max_lines > 0 and max_bytes > 0:
                drops["file_too_large"] += 1  # every line before the cap is read
                new[name] = REFUSED
    finally:
        os.close(dir_fd)
    return SpoolBatch(events, new, drops)


def _checked(cursor: dict[str, int], drops: Counter[str]) -> dict[str, int]:
    """A copy of the cursor in which every value fits its key; others are counted and reset.

    A spool file name maps to REFUSED or an offset up to MAX_FILE_BYTES, a name hash to REFUSED,
    and EXCESS to a count. A wrong value is never trusted: its file is refused (a count is reset).
    """
    checked = {}
    for key, value in cursor.items():
        if type(value) is not int:  # a bool is an int, and is refused here
            valid = False
        elif key == EXCESS:
            valid = value >= 0
        elif key.startswith("#"):
            valid = value == REFUSED
        else:
            in_range = value == REFUSED or 0 <= value <= MAX_FILE_BYTES
            valid = in_range and SPOOL_FILE_NAME.fullmatch(key) is not None
        if not valid:
            drops["bad_cursor"] += 1
            value = 0 if key == EXCESS else REFUSED
        checked[key] = value
    return checked


def _open_events_dir(launch_dir: Path) -> int | None:
    spectio_fd = None
    try:
        spectio_fd = _private_dir(launch_dir / ".spectio")
        return _private_dir("events", spectio_fd)
    except FileNotFoundError:
        return None
    finally:
        if spectio_fd is not None:
            os.close(spectio_fd)


def _private_dir(path: Path | str, dir_fd: int | None = None) -> int:
    fd = os.open(path, _DIR_FLAGS, dir_fd=dir_fd)
    st = os.fstat(fd)
    if st.st_uid != os.geteuid() or st.st_mode & 0o077:
        os.close(fd)
        raise PermissionError(f"{path}: not a private directory of this user (dev-env req. 12)")
    return fd


def _admit(dir_fd: int, launch_n: int, new: dict[str, int], drops: Counter[str]) -> list[str]:
    """This launch's spool files to read, in name order; count the other names once.

    Only this launch's names get a slot, up to MAX_SPOOL_FILES. A name outside the grammar is
    kept as a short hash (never the name itself), up to MAX_BAD_NAMES. What finds no slot, and a
    listing cut at MAX_DIR_ENTRIES, is excess: `cursor[EXCESS]` holds the most seen, so that
    only an increase is counted.
    """
    seen = new.get(EXCESS, 0)
    files = sum(not key.startswith("#") for key in new)
    bad = len(new) - files - (EXCESS in new)
    excess = 0
    with os.scandir(dir_fd) as entries:
        for i, entry in enumerate(entries):
            if i == MAX_DIR_ENTRIES:
                excess += 1
                break
            match = SPOOL_FILE_NAME.fullmatch(entry.name)
            if match and int(match[2]) != launch_n:
                continue  # another launch's file
            key = (
                entry.name
                if match
                else "#" + hashlib.sha256(os.fsencode(entry.name)).hexdigest()[:16]
            )
            if key in new:
                continue
            if match and files < MAX_SPOOL_FILES:
                new[key] = 0
                files += 1
            elif not match and bad < MAX_BAD_NAMES:
                drops["bad_name"] += 1
                new[key] = REFUSED
                bad += 1
            else:
                excess += 1
    if excess > seen:
        drops["too_many_files"] += excess - seen
        new[EXCESS] = excess
    # From the cursor, not the listing: a cut listing may miss a file admitted earlier.
    return sorted(
        key for key, offset in new.items() if not key.startswith("#") and offset != REFUSED
    )


def _open_regular(dir_fd: int, name: str) -> int | str:
    """A descriptor on a private regular file of the user, or the reason it is refused."""
    mode = os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if not stat.S_ISREG(mode):
        return "not_regular"  # never opened: opening a FIFO would wait for a writer
    # O_NONBLOCK: a FIFO swapped in since the stat opens at once, then fails the fstat.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    st = os.fstat(fd)
    reason = None
    if not stat.S_ISREG(st.st_mode):
        reason = "not_regular"
    elif st.st_uid != os.geteuid():
        reason = "foreign_owner"
    elif st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        reason = "writable_by_others"
    if reason:
        os.close(fd)
        return reason
    return fd


def _lines(
    fd: int, offset: int, end: int, max_lines: int, max_bytes: int
) -> tuple[list[bytes | None], int, int]:
    """The ended lines in [offset, end), the offset after them, and the bytes read.

    Stops at `max_lines` lines or once `max_bytes` bytes are read. A line longer than
    MAX_LINE_BYTES is None. It is cut short as soon as it passes the cap, ended or not, and the
    offset then points inside it: the next read skips to its "\\n". A shorter unended line is
    left for the next read, which finds it complete.
    """
    lines: list[bytes | None] = []
    read = 0
    skipping = offset > 0 and os.pread(fd, 1, offset - 1) != b"\n"
    buf = b""  # the file's bytes from `offset` on, not yet split
    while len(lines) < max_lines and read < max_bytes and offset + len(buf) < end:
        size = min(CHUNK_BYTES, max_bytes - read, end - offset - len(buf))
        chunk = os.pread(fd, size, offset + len(buf))
        if not chunk:
            break  # the file shrank: an append-only spool never does
        read += len(chunk)
        buf += chunk
        start = 0
        while len(lines) < max_lines and (nl := buf.find(b"\n", start)) >= 0:
            if skipping:
                skipping = False
            else:
                lines.append(buf[start:nl] if nl - start <= MAX_LINE_BYTES else None)
            start = nl + 1
        offset += start
        buf = buf[start:]
        if len(lines) < max_lines and len(buf) > MAX_LINE_BYTES:
            if not skipping:
                lines.append(None)
            skipping = True
            offset += len(buf)
            buf = b""
    return lines, offset, read


def _too_large(data: Any) -> bool:
    """More than MAX_EVENT_NODES JSON values, or deeper than MAX_EVENT_DEPTH."""
    nodes = 0
    stack = [(data, 1)]
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_EVENT_NODES or depth > MAX_EVENT_DEPTH:
            return True
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    return False


def _event(raw: bytes, run_id: str, launch_n: int) -> SpoolEvent | str:
    """The event with its allow-listed data only, or the reason the line is dropped."""
    # Cheap bound before parsing: a value adds at most two of "[", "{" and ",", and the envelope
    # under 16. Commas inside strings count too, so this only refuses far past the cap (the
    # largest T2 line has 91 of them).
    if raw.count(b"[") + raw.count(b"{") + raw.count(b",") > 2 * (MAX_EVENT_NODES + 16):
        return "too_complex"
    try:
        event = SpoolEvent.model_validate_json(raw)
    except ValidationError:
        return "invalid"
    if event.run != run_id:
        return "wrong_run"
    if event.launch != launch_n:
        return "wrong_launch"
    if _too_large(event.data):
        return "too_complex"
    try:
        data = parse_data(event).model_dump(mode="json", by_alias=True, exclude_unset=True)
    except (ValidationError, UnknownEventType):
        return "invalid"
    return event.model_copy(update={"data": data})
