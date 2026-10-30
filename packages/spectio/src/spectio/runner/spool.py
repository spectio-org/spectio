"""Read a launch's spool: api-and-data-model.md §14.1, dev-env §15.3 req. 6 (P1 Task 3).

Every line is untrusted input: it is validated, never executed, and a line that fails is dropped
and counted by reason. The reader opens `.spectio` and `events` with O_NOFOLLOW, then each file
relative to the `events` descriptor, so a directory or file swapped for a symlink after a check
is never followed. Pure: no database; the caller stores the batch in one transaction.
"""

import errno
import os
import stat
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from spectio.runner.types import REFUSED, SpoolBatch
from spectio_sdk.events import (
    MAX_FILE_BYTES,
    MAX_LINE_BYTES,
    MAX_SPOOL_FILES,
    SPOOL_FILE_NAME,
    SpoolEvent,
    UnknownEventType,
    parse_data,
)

CHUNK_BYTES = 1048576  # read at a time: a reader holds at most this plus MAX_LINE_BYTES
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def read_spool(
    launch_dir: Path, run_id: str, launch_n: int, cursor: dict[str, int], max_lines: int = 5000
) -> SpoolBatch:
    """Read at most `max_lines` lines past `cursor`, in file name order.

    Raises OSError when `.spectio` or `.spectio/events` is there but is not a directory, a
    symlink included; returns an empty batch when either is missing (nothing written yet).
    """
    events: list[SpoolEvent] = []
    drops: Counter[str] = Counter()
    new = dict(cursor)
    dir_fd = _open_events_dir(launch_dir)
    if dir_fd is None:
        return SpoolBatch(events, new, drops)
    try:
        names = sorted(os.listdir(dir_fd))
        _admit(names, launch_n, cursor, new, drops)
        for name in names:
            offset = new.get(name, REFUSED)
            if not 0 <= offset < MAX_FILE_BYTES or max_lines <= 0:
                continue
            try:
                fd = _open_regular(dir_fd, name)
            except FileNotFoundError:
                continue  # gone since the listing
            if isinstance(fd, str):
                drops[fd] += 1
                new[name] = REFUSED
                continue
            try:
                size = os.fstat(fd).st_size
                lines, new[name] = _lines(fd, offset, min(size, MAX_FILE_BYTES), max_lines)
            finally:
                os.close(fd)
            max_lines -= len(lines)
            for raw in lines:
                event = "line_too_large" if raw is None else _event(raw, run_id, launch_n)
                if isinstance(event, str):
                    drops[event] += 1
                else:
                    events.append(event)
            if size > MAX_FILE_BYTES and max_lines > 0:  # every line before the cap is read
                drops["file_too_large"] += 1
                new[name] = MAX_FILE_BYTES
    finally:
        os.close(dir_fd)
    return SpoolBatch(events, new, drops)


def _open_events_dir(launch_dir: Path) -> int | None:
    spectio_fd = None
    try:
        spectio_fd = os.open(launch_dir / ".spectio", _DIR_FLAGS)
        return os.open("events", _DIR_FLAGS, dir_fd=spectio_fd)
    except FileNotFoundError:
        return None
    finally:
        if spectio_fd is not None:
            os.close(spectio_fd)


def _admit(
    names: list[str],
    launch_n: int,
    cursor: dict[str, int],
    new: dict[str, int],
    drops: Counter[str],
) -> None:
    """Give each new name of this launch a cursor entry; count the names refused, once each.

    The cursor holds at most MAX_SPOOL_FILES entries plus one marker: the excess is counted by
    the read that first meets the cap, which adds the marker, and never again.
    """
    for name in names:
        # A name that is not UTF-8 is kept as a text key (the cursor is stored as text).
        key = os.fsencode(name).decode("utf-8", "backslashreplace")
        if key in new:
            continue
        match = SPOOL_FILE_NAME.fullmatch(name)
        if match and int(match[2]) != launch_n:
            continue  # another launch's file
        if len(new) >= MAX_SPOOL_FILES:
            if len(cursor) <= MAX_SPOOL_FILES:
                drops["too_many_files"] += 1
            if len(new) == MAX_SPOOL_FILES:
                new[key] = REFUSED
        elif match:
            new[key] = 0
        else:
            drops["bad_name"] += 1
            new[key] = REFUSED


def _open_regular(dir_fd: int, name: str) -> int | str:
    """A descriptor on a regular file, or the reason it is refused."""
    mode = os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if not stat.S_ISREG(mode):
        return "not_regular"  # never opened: opening a FIFO would wait for a writer
    try:
        # O_NONBLOCK: a FIFO swapped in since the stat opens at once, then fails the fstat.
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    except OSError as e:
        if e.errno == errno.ELOOP:
            return "symlink"  # swapped since the stat
        raise
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        return "not_regular"
    return fd


def _lines(fd: int, offset: int, end: int, max_lines: int) -> tuple[list[bytes | None], int]:
    """The ended lines in [offset, end), at most `max_lines`, and the offset after them.

    A line longer than MAX_LINE_BYTES is None. It is cut short as soon as it passes the cap,
    ended or not, and the offset then points inside it: the next read skips to its "\\n".
    A shorter unended line is left for the next read, which finds it complete.
    """
    lines: list[bytes | None] = []
    skipping = offset > 0 and os.pread(fd, 1, offset - 1) != b"\n"
    buf = b""  # the file's bytes from `offset` on, not yet split
    while len(lines) < max_lines and offset + len(buf) < end:
        chunk = os.pread(fd, min(CHUNK_BYTES, end - offset - len(buf)), offset + len(buf))
        if not chunk:
            break  # the file shrank: an append-only spool never does
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
    return lines, offset


def _event(raw: bytes, run_id: str, launch_n: int) -> SpoolEvent | str:
    """The event with its allow-listed data only, or the reason the line is dropped."""
    try:
        event = SpoolEvent.model_validate_json(raw)
    except ValidationError:
        return "invalid"
    if event.run != run_id:
        return "wrong_run"
    if event.launch != launch_n:
        return "wrong_launch"
    try:
        data = parse_data(event).model_dump(mode="json", by_alias=True, exclude_unset=True)
    except (ValidationError, UnknownEventType):
        return "invalid"
    return event.model_copy(update={"data": data})
