"""The spool reader: dev-env §15.3 req. 6, api-and-data-model.md §14.1 (P1 Task 3)."""

import errno
import json
import os
import signal
import socket
import stat
import time
import tracemalloc
from pathlib import Path
from typing import Any

import pytest

from spectio.runner import spool
from spectio.runner.spool import CHUNK_BYTES, MAX_BAD_NAMES, MAX_READ_BYTES, read_spool
from spectio.runner.types import REFUSED, SpoolBatch
from spectio_sdk.events import (
    MAX_EVENT_DEPTH,
    MAX_EVENT_NODES,
    MAX_FILE_BYTES,
    MAX_LINE_BYTES,
    MAX_SPOOL_FILES,
    SpoolEvent,
)

RUN_ID = "run_01K8T2F1XTVRES000000000000"
OTHER_RUN = "run_01K8T2F1XTVRES000000000001"
NF = "nf-spectio-1-0001.jsonl"


def line(n: int, *, run: str = RUN_ID, launch: int = 1, **data: Any) -> bytes:
    """One spool line, `\\n` included; `n` makes the event ID."""
    event = {
        "v": 1,
        "id": f"evt_{n:026d}",
        "run": run,
        "launch": launch,
        "producer": "nf-spectio/0.0.1",
        "seq": n,
        "time": "2026-10-28T07:18:46.182Z",
        "type": "nextflow.onTaskStart",
        "data": {"taskId": str(n), **data},
    }
    return json.dumps(event).encode() + b"\n"


@pytest.fixture
def events_dir(tmp_path: Path) -> Path:
    return private_events_dir(tmp_path)


def private_events_dir(launch_dir: Path) -> Path:
    """`.spectio/events` as the runner makes it: 0700 directories of the user (req. 12)."""
    (launch_dir / ".spectio").mkdir(mode=0o700)
    (launch_dir / ".spectio" / "events").mkdir(mode=0o700)
    return launch_dir / ".spectio" / "events"


def write(path: Path, *chunks: bytes) -> None:
    with path.open("ab") as f:
        for chunk in chunks:
            f.write(chunk)


def read(events_dir: Path, cursor: dict[str, int] | None = None, **kw: Any) -> SpoolBatch:
    return read_spool(events_dir.parent.parent, RUN_ID, 1, cursor or {}, **kw)


def ids(batch: SpoolBatch) -> list[str]:
    return [event.id for event in batch.events]


def test_req6_invalid_line_dropped_and_counted(events_dir: Path) -> None:
    write(events_dir / NF, b"not json\n", b'{"v": 1, "extra": true}\n', line(1))
    batch = read(events_dir)
    assert ids(batch) == ["evt_" + "1".zfill(26)]
    assert batch.drops == {"invalid": 2}
    assert batch.cursor == {NF: (events_dir / NF).stat().st_size}


def test_req6_unknown_type_and_bad_data_are_invalid(events_dir: Path) -> None:
    unknown = json.loads(line(1))
    unknown["type"] = "nextflow.onSomethingNew"
    write(
        events_dir / NF,
        json.dumps(unknown).encode() + b"\n",
        line(2, attempt="7"),  # a string where the allow-list wants an integer
        b"\n",  # an empty line
        b"\xff\xfe\n",  # not UTF-8
    )
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"invalid": 4}


def test_req6_oversized_line_dropped(events_dir: Path) -> None:
    write(events_dir / NF, b"x" * (MAX_LINE_BYTES + 1) + b"\n", line(1))
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.drops == {"line_too_large": 1}


def test_req6_line_of_exactly_max_bytes_kept(events_dir: Path) -> None:
    base = len(line(1, tag=""))
    exact = line(1, tag="t" * (MAX_LINE_BYTES + 1 - base))
    assert len(exact) == MAX_LINE_BYTES + 1  # with its "\n"
    write(events_dir / NF, exact)
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert not batch.drops


def test_req6_file_cap(events_dir: Path) -> None:
    # A kept line, one oversized filler line, then a line across the cap and one past it.
    first = line(1)
    across = line(2)
    filler = b"x" * (MAX_FILE_BYTES - len(first) - len(across) // 2 - 1) + b"\n"
    write(events_dir / NF, first, filler, across, line(3))
    assert (events_dir / NF).stat().st_size > MAX_FILE_BYTES
    batch = read(events_dir, max_lines=10, max_bytes=2 * MAX_FILE_BYTES)
    assert ids(batch) == [json.loads(first)["id"]]
    assert batch.drops == {"line_too_large": 1, "file_too_large": 1}
    assert batch.cursor == {NF: REFUSED}
    # Counted once: a later read, after more appends, ignores the file.
    write(events_dir / NF, line(4))
    again = read(events_dir, batch.cursor)
    assert again.events == []
    assert not again.drops
    assert again.cursor == batch.cursor


def test_req6_other_run_id_dropped(events_dir: Path) -> None:
    write(events_dir / NF, line(1, run=OTHER_RUN), line(2))
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.drops == {"wrong_run": 1}


def test_req6_other_launch_dropped(events_dir: Path) -> None:
    write(events_dir / NF, line(1, launch=2), line(2))
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.drops == {"wrong_launch": 1}


def test_req6_denied_keys_not_returned(events_dir: Path) -> None:
    # The reader returns the allow-listed data (§14.1, P1 Assumption 3), never the raw line's.
    write(events_dir / NF, line(1, script="rm -rf /", env={"SECRET": "x"}, tag="kept"))
    (event,) = read(events_dir).events
    assert event.data == {"taskId": "1", "tag": "kept"}


def test_partial_last_line_waits(events_dir: Path) -> None:
    second = line(2)
    write(events_dir / NF, line(1), second[:20])
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.cursor == {NF: len(line(1))}
    write(events_dir / NF, second[20:])
    after = read(events_dir, batch.cursor)
    assert ids(after) == [json.loads(second)["id"]]
    assert read(events_dir, after.cursor).events == []


def test_partial_line_at_max_bytes_still_waits(events_dir: Path) -> None:
    write(events_dir / NF, b"x" * MAX_LINE_BYTES)
    batch = read(events_dir)
    assert batch.events == []
    assert not batch.drops
    assert batch.cursor == {NF: 0}


def test_partial_line_over_max_bytes_dropped_once(events_dir: Path) -> None:
    # A writer that never ends its line: dropped once it passes the cap, never buffered whole.
    write(events_dir / NF, b"x" * (MAX_LINE_BYTES + 10))
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"line_too_large": 1}
    assert batch.cursor == {NF: MAX_LINE_BYTES + 10}
    # The rest of that line is skipped up to its "\n", without counting it again.
    write(events_dir / NF, b"x" * 100_000, b'{"v": 1}\n', line(1))
    after = read(events_dir, batch.cursor)
    assert len(after.events) == 1
    assert not after.drops


def test_max_lines(events_dir: Path) -> None:
    write(events_dir / NF, line(1), b"not json\n", line(2), line(3))
    batch = read(events_dir, max_lines=3)
    assert len(batch.events) == 2
    assert batch.drops == {"invalid": 1}
    rest = read(events_dir, batch.cursor, max_lines=3)
    assert len(rest.events) == 1


def test_files_read_in_name_order(events_dir: Path) -> None:
    write(events_dir / "nf-spectio-1-0002.jsonl", line(3))
    write(events_dir / NF, line(1), line(2))
    write(events_dir / "snakemake-logger-spectio-1-0001.jsonl")  # empty: nothing, no drop
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [1, 2, 3]
    assert not batch.drops


def test_cursor_resumes_without_duplicates(events_dir: Path) -> None:
    write(events_dir / NF, line(1), line(2))
    first = read(events_dir)
    write(events_dir / NF, line(3))  # the writer passes ROTATE_BYTES here and rotates
    write(events_dir / "nf-spectio-1-0002.jsonl", line(4), line(5))
    second = read(events_dir, first.cursor)
    seen = ids(first) + ids(second)
    assert len(seen) == 5
    assert len(set(seen)) == 5
    assert read(events_dir, second.cursor).events == []


def test_symlinked_spool_file_refused(events_dir: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.jsonl"
    write(outside, line(1))
    (events_dir / NF).symlink_to(outside)
    (events_dir / "nf-spectio-1-0002.jsonl").symlink_to("/etc/passwd")
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"symlink": 2}
    # Counted once.
    assert not read(events_dir, batch.cursor).drops


def test_fifo_refused_without_blocking(events_dir: Path) -> None:
    os.mkfifo(events_dir / NF)
    write(events_dir / "nf-spectio-1-0002.jsonl", line(1))
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.drops == {"not_regular": 1}
    assert not read(events_dir, batch.cursor).drops


def test_directory_named_as_spool_file_refused(events_dir: Path) -> None:
    (events_dir / NF).mkdir()
    batch = read(events_dir)
    assert batch.drops == {"not_regular": 1}


def test_symlinked_spool_directory_refused(tmp_path: Path) -> None:
    # `.spectio` or `events` swapped for a symlink: the reader never follows it.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    write(private_events_dir(elsewhere) / NF, line(1))
    launch_a, launch_b = tmp_path / "a", tmp_path / "b"
    launch_a.mkdir()
    (launch_a / ".spectio").symlink_to(elsewhere / ".spectio")
    (launch_b / ".spectio").mkdir(mode=0o700, parents=True)
    (launch_b / ".spectio" / "events").symlink_to(elsewhere / ".spectio" / "events")
    for launch_dir in (launch_a, launch_b):
        with pytest.raises(OSError):
            read_spool(launch_dir, RUN_ID, 1, {})


def test_no_spool_yet(tmp_path: Path) -> None:
    batch = read_spool(tmp_path, RUN_ID, 1, {NF: 3})
    assert batch.events == []
    assert batch.cursor == {NF: 3}
    assert not batch.drops


def test_bad_file_names_skipped_and_counted_once(events_dir: Path) -> None:
    bad = [
        "x.jsonl",
        ".cursor",
        "nf-spectio-1-0000.jsonl",  # indexes start at 0001
        "nf-spectio-01-0001.jsonl",  # a launch number is written without a leading zero
        "nf-spectio-1-001.jsonl",
        "nf-tower-1-0001.jsonl",
        "nf-spectio-1-0001.jsonl.bak",
        f"{RUN_ID}-nf-spectio-0001.jsonl",  # a terminal run's name (architecture §13.8)
    ]
    for name in bad:
        write(events_dir / name, line(1))
    write(events_dir / os.fsdecode(b"nf-spectio-1-\xff.jsonl"), line(1))
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"bad_name": len(bad) + 1}
    assert_safe_keys(batch.cursor)
    assert not read(events_dir, batch.cursor).drops


def assert_safe_keys(cursor: dict[str, int]) -> None:
    # Keys are stored as text: a spool file name of this launch, or a short ASCII key of ours.
    for key in cursor:
        assert key.isascii() and key.isprintable() and len(key) <= 64, key


def test_junk_names_leave_the_slots_to_spool_files(events_dir: Path) -> None:
    for i in range(MAX_SPOOL_FILES):
        write(events_dir / f"junk-\x1b[31m-{i}", b"x\n")
    write(events_dir / NF, line(1))
    batch = read(events_dir)
    assert len(batch.events) == 1
    assert batch.drops == {
        "bad_name": MAX_BAD_NAMES,
        "too_many_files": MAX_SPOOL_FILES - MAX_BAD_NAMES,
    }
    assert_safe_keys(batch.cursor)
    assert len(batch.cursor) <= MAX_BAD_NAMES + 2
    assert not read(events_dir, batch.cursor).drops


def test_directory_listing_cap(events_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spool, "MAX_DIR_ENTRIES", 5)
    for i in range(1, 11):
        write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", line(i))
    batch = read(events_dir)
    assert len(batch.events) == 5
    assert batch.drops == {"too_many_files": 1}
    assert not read(events_dir, batch.cursor).drops


def test_other_launch_files_ignored(events_dir: Path) -> None:
    write(events_dir / "nf-spectio-2-0001.jsonl", line(1, launch=2))
    write(events_dir / "nf-spectio-11-0001.jsonl", line(2, launch=11))
    write(events_dir / NF, line(3))
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [3]
    assert not batch.drops
    assert batch.cursor == {NF: len(line(3))}


def test_spool_file_cap(events_dir: Path) -> None:
    for i in range(1, MAX_SPOOL_FILES + 4):
        write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", line(i))
    batch = read(events_dir, max_lines=10 * MAX_SPOOL_FILES)
    assert len(batch.events) == MAX_SPOOL_FILES
    assert batch.drops == {"too_many_files": 3}
    # Each file is counted once, and the cursor stays bounded.
    assert not read(events_dir, batch.cursor).drops
    write(events_dir / f"nf-spectio-1-{MAX_SPOOL_FILES + 4:04d}.jsonl", line(9999))
    again = read(events_dir, batch.cursor, max_lines=10 * MAX_SPOOL_FILES)
    assert again.events == []
    assert again.drops == {"too_many_files": 1}
    assert len(again.cursor) <= MAX_SPOOL_FILES + 1


def test_spool_file_cap_reached_before_the_excess(events_dir: Path) -> None:
    for i in range(1, MAX_SPOOL_FILES + 1):
        write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", line(i))
    full = read(events_dir, max_lines=10 * MAX_SPOOL_FILES)
    assert not full.drops
    for i in range(MAX_SPOOL_FILES + 1, MAX_SPOOL_FILES + 3):
        write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", line(i))
    batch = read(events_dir, full.cursor)
    assert batch.events == []
    assert batch.drops == {"too_many_files": 2}


def test_req6_file_cap_counted_after_the_lines_before_it(events_dir: Path) -> None:
    # A read that stops on max_lines before the cap does not skip the lines left before it.
    first = line(1)
    filler = b"x" * (MAX_FILE_BYTES - len(first) - 10) + b"\n"
    write(events_dir / NF, first, filler, line(2))
    batch = read(events_dir, max_lines=1)
    assert len(batch.events) == 1
    assert not batch.drops
    rest = read(events_dir, batch.cursor, max_bytes=2 * MAX_FILE_BYTES)
    assert rest.drops == {"line_too_large": 1, "file_too_large": 1}


def test_req6_file_of_exactly_max_bytes_counted_when_it_grows(events_dir: Path) -> None:
    first = line(1)
    filler = b"x" * (MAX_FILE_BYTES - len(first) - 1) + b"\n"
    write(events_dir / NF, first, filler)
    assert (events_dir / NF).stat().st_size == MAX_FILE_BYTES
    batch = read(events_dir, max_bytes=2 * MAX_FILE_BYTES)
    assert batch.drops == {"line_too_large": 1}
    write(events_dir / NF, line(2))
    grown = read(events_dir, batch.cursor)
    assert grown.events == []
    assert grown.drops == {"file_too_large": 1}
    assert not read(events_dir, grown.cursor).drops


def test_socket_refused(events_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(events_dir)  # a socket path is limited to 108 bytes
    with socket.socket(socket.AF_UNIX) as sock:
        sock.bind(NF)
        batch = read(events_dir)
    assert batch.drops == {"not_regular": 1}


@pytest.fixture
def swapped_after_stat(monkeypatch: pytest.MonkeyPatch) -> None:
    """The writer swaps the file after the reader's stat, which saw a regular file."""
    real_stat = os.stat

    def stat_before_swap(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> os.stat_result:
        if dir_fd is None:
            return real_stat(path, follow_symlinks=follow_symlinks)
        return real_stat(__file__)

    monkeypatch.setattr(os, "stat", stat_before_swap)  # only calls with dir_fd: the reader's


@pytest.mark.usefixtures("swapped_after_stat")
def test_symlink_swapped_in_after_the_check_refused(events_dir: Path) -> None:
    (events_dir / NF).symlink_to("/etc/passwd")
    assert read(events_dir).drops == {"symlink": 1}


@pytest.mark.usefixtures("swapped_after_stat")
def test_fifo_swapped_in_after_the_check_refused(events_dir: Path) -> None:
    os.mkfifo(events_dir / NF)

    def timeout(*_: Any) -> None:
        raise TimeoutError("the reader waited on a FIFO")

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(5)
    try:
        batch = read(events_dir)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    assert batch.drops == {"not_regular": 1}


# --- Budgets per read (SEC-P3T3-01) --------------------------------------------------------


def nested_line(n: int, size: int) -> bytes:
    """A line of at most `size` bytes, its "\\n" apart, holding a long list of empty lists."""
    head = line(n, x=[])[: -len(b"]}}\n")]
    return head + b"[]," * ((size - len(head) - 5) // 3) + b"[]]}}\n"


def test_req6_event_node_cap(events_dir: Path) -> None:
    # `data`, `taskId`, `x` and its items: exactly MAX_EVENT_NODES values, then one more.
    write(
        events_dir / NF,
        line(1, x=[None] * (MAX_EVENT_NODES - 3)),
        line(2, x=[None] * (MAX_EVENT_NODES - 2)),
    )
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [1]
    assert batch.drops == {"too_complex": 1}


def test_req6_event_depth_cap(events_dir: Path) -> None:
    def nested(depth: int) -> Any:  # `data` is depth 1, the value of `x` depth 2
        value: Any = None
        for _ in range(depth - 2):
            value = [value]
        return value

    write(
        events_dir / NF,
        line(1, x=nested(MAX_EVENT_DEPTH)),
        line(2, x=nested(MAX_EVENT_DEPTH + 1)),
    )
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [1]
    assert batch.drops == {"too_complex": 1}


def test_req6_read_stops_at_max_bytes(events_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Files with no "\n" at all: one read consumes no more than its byte budget.
    for i in range(1, 4):
        with (events_dir / f"nf-spectio-1-{i:04d}.jsonl").open("wb") as f:
            f.truncate(MAX_FILE_BYTES)
    read_bytes = 0
    real_pread = os.pread

    def counting_pread(fd: int, n: int, offset: int) -> bytes:
        nonlocal read_bytes
        data = real_pread(fd, n, offset)
        read_bytes += len(data)
        return data

    monkeypatch.setattr(os, "pread", counting_pread)
    batch = read(events_dir)
    assert read_bytes <= MAX_READ_BYTES
    assert sum(batch.cursor.values()) <= MAX_READ_BYTES
    assert batch.drops == {"line_too_large": 1}
    # The next read goes on from there.
    after = read(events_dir, batch.cursor)
    assert sum(after.cursor.values()) > sum(batch.cursor.values())
    # A budget that is not a whole number of chunks.
    read_bytes = 0
    read(events_dir, max_bytes=CHUNK_BYTES + 12345)
    assert read_bytes == CHUNK_BYTES + 12345


@pytest.mark.parametrize("kept", [False, True])
def test_req6_memory_bounded_on_nested_lines(events_dir: Path, kept: bool) -> None:
    if kept:
        # Events at the node cap in a free-form field that the allow-list keeps, all returned.
        event = json.loads(line(1))
        event.update(producer="snakemake-logger-spectio/0.0.1", type="snakemake.rulegraph")
        event["data"] = {"rulegraph": {"r": [[]] * (MAX_EVENT_NODES - 3)}}
        one = json.dumps(event, separators=(",", ":")).encode() + b"\n"
        write(events_dir / NF, one * (2 * MAX_READ_BYTES // len(one)))
    else:
        # Lines at the line cap, each holding the most JSON nodes it can, in several files.
        big = b"".join(nested_line(i, MAX_LINE_BYTES) for i in range(40))
        for i in range(1, 5):
            write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", big)
    tracemalloc.start()
    try:
        batch = read(events_dir)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert batch.drops if not kept else len(batch.events) > 100
    assert not (kept and batch.drops)
    assert peak < 64 * 2**20, f"peak {peak / 2**20:.0f} MiB"


# --- Owner and mode (SEC-P3T3-02) ----------------------------------------------------------


def other_owner(monkeypatch: pytest.MonkeyPatch, kind: int) -> None:
    """fstat reports another owner for every inode of this kind (S_IFREG or S_IFDIR)."""
    real_fstat = os.fstat

    def fstat(fd: int) -> os.stat_result:
        st = real_fstat(fd)
        if stat.S_IFMT(st.st_mode) != kind:
            return st
        fields = list(st[:10])
        fields[4] = st.st_uid + 1
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", fstat)


def test_req12_file_of_another_owner_refused(
    events_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(events_dir / NF, line(1))
    other_owner(monkeypatch, stat.S_IFREG)
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"foreign_owner": 1}
    assert batch.cursor == {NF: REFUSED}


def test_req12_file_writable_by_others_refused(events_dir: Path) -> None:
    write(events_dir / NF, line(1))
    (events_dir / NF).chmod(0o664)
    write(events_dir / "nf-spectio-1-0002.jsonl", line(2))
    (events_dir / "nf-spectio-1-0002.jsonl").chmod(0o602)
    batch = read(events_dir)
    assert batch.events == []
    assert batch.drops == {"writable_by_others": 2}


@pytest.mark.parametrize("opened", [".spectio", ".spectio/events"])
def test_req12_open_spool_directory_refused(tmp_path: Path, opened: str) -> None:
    write(private_events_dir(tmp_path) / NF, line(1))
    (tmp_path / opened).chmod(0o777)
    with pytest.raises(PermissionError):
        read_spool(tmp_path, RUN_ID, 1, {})


def test_req12_spool_directory_of_another_owner_refused(
    events_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(events_dir / NF, line(1))
    other_owner(monkeypatch, stat.S_IFDIR)
    with pytest.raises(PermissionError):
        read(events_dir)


# --- One bad file never stops the reader (CR-P3T3-01, SEC-P3T3-03) -------------------------


@pytest.mark.parametrize("error", [errno.EACCES, errno.ENXIO])
def test_unreadable_file_refused_and_the_next_one_read(
    events_dir: Path, monkeypatch: pytest.MonkeyPatch, error: int
) -> None:
    write(events_dir / NF, line(1))
    write(events_dir / "nf-spectio-1-0002.jsonl", line(2))
    real_open = os.open

    def failing_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        if path == NF:
            raise OSError(error, os.strerror(error), path)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", failing_open)
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [2]
    assert batch.drops == {"unreadable": 1}
    assert batch.cursor[NF] == REFUSED


def test_read_error_retried_next_read(events_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(events_dir / NF, line(1))
    write(events_dir / "nf-spectio-1-0002.jsonl", line(2))
    real_pread = os.pread
    failing = True

    def flaky_pread(fd: int, n: int, offset: int) -> bytes:
        if failing and os.readlink(f"/proc/self/fd/{fd}").endswith(NF):
            raise OSError(errno.EIO, os.strerror(errno.EIO))
        return real_pread(fd, n, offset)

    monkeypatch.setattr(os, "pread", flaky_pread)
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [2]
    assert batch.drops == {"read_error": 1}
    assert batch.cursor[NF] == 0
    failing = False
    assert [e.seq for e in read(events_dir, batch.cursor).events] == [1]


# --- Round 2 -------------------------------------------------------------------------------


def test_file_gone_after_listing_skipped_silently(events_dir: Path) -> None:
    # An admitted file that is gone (or goes between the listing and the open): no drop.
    write(events_dir / "nf-spectio-1-0002.jsonl", line(2))
    batch = read(events_dir, {NF: 10})
    assert [e.seq for e in batch.events] == [2]
    assert not batch.drops
    assert batch.cursor[NF] == 10


@pytest.mark.parametrize(
    "cursor",
    [
        {NF: -5},
        {NF: 1.5},
        {NF: "x"},
        {NF: True},
        {NF: MAX_FILE_BYTES + 1},
        {"../outside.jsonl": 0},
        {"#0123456789abcdef": 0},
        {"#excess": -3},
    ],
)
def test_bad_cursor_values_refused(events_dir: Path, cursor: dict[str, Any]) -> None:
    write(events_dir / NF, line(1))
    write(events_dir.parent.parent / "outside.jsonl", line(9))
    batch = read(events_dir, cursor)
    assert batch.drops["bad_cursor"] == 1
    key = next(iter(cursor))
    assert batch.cursor[key] == (0 if key == "#excess" else REFUSED)
    assert all(e.seq != 9 for e in batch.events)


@pytest.mark.parametrize(
    "budget", [{"max_bytes": 10}, {"max_bytes": MAX_LINE_BYTES}, {"max_lines": 0}]
)
def test_budgets_too_small_refused(events_dir: Path, budget: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        read_spool(events_dir.parent.parent, RUN_ID, 1, {}, **budget)


def test_admitted_files_read_past_the_listing_cap(
    events_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    names = [f"nf-spectio-1-{i:04d}.jsonl" for i in range(1, 6)]
    for i, name in enumerate(names, 1):
        write(events_dir / name, line(i))
    first = read(events_dir)
    monkeypatch.setattr(spool, "MAX_DIR_ENTRIES", 2)
    for i, name in enumerate(names, 11):
        write(events_dir / name, line(i))
    batch = read(events_dir, first.cursor)
    assert [e.seq for e in batch.events] == [11, 12, 13, 14, 15]


def test_too_complex_line_not_parsed(events_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_parse(*_: Any, **__: Any) -> None:
        raise AssertionError("parsed")

    write(events_dir / NF, line(1, x=[0] * (3 * MAX_EVENT_NODES)))
    monkeypatch.setattr(SpoolEvent, "model_validate_json", no_parse)
    assert read(events_dir).drops == {"too_complex": 1}


def test_worst_read_is_fast(events_dir: Path) -> None:
    big = b"".join(nested_line(i, MAX_LINE_BYTES) for i in range(40))
    for i in range(1, 5):
        write(events_dir / f"nf-spectio-1-{i:04d}.jsonl", big)
    start = time.perf_counter()
    batch = read(events_dir)
    assert time.perf_counter() - start < 1.0
    assert batch.drops["too_complex"] > 20


def test_file_gone_between_listing_and_open(
    events_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(events_dir / NF, line(1))
    write(events_dir / "nf-spectio-1-0002.jsonl", line(2))
    real_stat = os.stat

    def gone(path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True) -> Any:
        if path == NF:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "stat", gone)
    batch = read(events_dir)
    assert [e.seq for e in batch.events] == [2]
    assert not batch.drops
    assert batch.cursor[NF] == 0
