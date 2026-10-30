"""The spool reader: dev-env §15.3 req. 6, api-and-data-model.md §14.1 (P1 Task 3)."""

import json
import os
import signal
import socket
from pathlib import Path
from typing import Any

import pytest

from spectio.runner.spool import read_spool
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import MAX_FILE_BYTES, MAX_LINE_BYTES, MAX_SPOOL_FILES

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
    path = tmp_path / ".spectio" / "events"
    path.mkdir(parents=True)
    return path


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
    batch = read(events_dir, max_lines=10)
    assert ids(batch) == [json.loads(first)["id"]]
    assert batch.drops == {"line_too_large": 1, "file_too_large": 1}
    assert batch.cursor == {NF: MAX_FILE_BYTES}
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
    (elsewhere / "events").mkdir(parents=True)
    write(elsewhere / "events" / NF, line(1))
    launch_a, launch_b = tmp_path / "a", tmp_path / "b"
    launch_a.mkdir()
    (launch_a / ".spectio").symlink_to(elsewhere)
    (launch_b / ".spectio").mkdir(parents=True)
    (launch_b / ".spectio" / "events").symlink_to(elsewhere / "events")
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
    # Every cursor key can be stored as UTF-8 text.
    for key in batch.cursor:
        key.encode()
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
    # Counted once, and the cursor stays bounded.
    write(events_dir / f"nf-spectio-1-{MAX_SPOOL_FILES + 4:04d}.jsonl", line(9999))
    again = read(events_dir, batch.cursor, max_lines=10 * MAX_SPOOL_FILES)
    assert again.events == []
    assert not again.drops
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
    rest = read(events_dir, batch.cursor)
    assert rest.drops == {"line_too_large": 1, "file_too_large": 1}


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
