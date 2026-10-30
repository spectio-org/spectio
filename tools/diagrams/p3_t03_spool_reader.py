#!/usr/bin/env python3
"""The spool reader's gates: step P3, P1 Task 3, 2026-10-30.

Writes docs/assets/diagrams/p3-t03-spool-reader_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t03 at a7a4610:
- packages/spectio/src/spectio/runner/spool.py:
  read_spool(launch_dir, run_id, launch_n, cursor, max_lines=5000, max_bytes=MAX_READ_BYTES 2097152);
  _checked: cursor keys that are not this launch's spool files, or wrong values: bad_cursor;
  _open_events_dir / _private_dir: `.spectio` then `events` opened O_RDONLY|O_DIRECTORY|O_NOFOLLOW,
  owner must be the effective uid and mode & 0o077 zero, else PermissionError; a symlink or not a
  directory: OSError; missing: an empty batch;
  _admit: os.scandir cut at MAX_DIR_ENTRIES = 16 * MAX_SPOOL_FILES = 16384; another launch's files
  skipped; a name outside SPOOL_FILE_NAME kept as "#" + 16 hex of sha256, bad_name, up to
  MAX_BAD_NAMES 64; no slot past MAX_SPOOL_FILES 1024, more bad names, or a cut listing:
  too_many_files, counted only when it rises (cursor "#excess");
  _open_regular: lstat (symlink, not_regular, a FIFO is never opened), open O_RDONLY|O_NOFOLLOW|
  O_NONBLOCK relative to the events descriptor, fstat (not_regular, foreign_owner,
  writable_by_others); ELOOP symlink, EACCES and ENXIO unreadable; other OSError read_error, retried;
  FileNotFoundError skipped; size past MAX_FILE_BYTES 67108864: the lines before it are read, then
  file_too_large; refused files get REFUSED (-1) in the cursor and are never read again;
  _lines: pread in chunks of 1 MiB, split on "\\n", a line over MAX_LINE_BYTES 65536 is
  line_too_large; _event: a count of "[", "{" and "," over 2 * (4096 + 16) is too_complex before
  parsing, then invalid, wrong_run, wrong_launch, too_complex (over MAX_EVENT_NODES 4096 values or
  deeper than MAX_EVENT_DEPTH 32), invalid (data outside the allow-list), data kept as parsed;
  SpoolBatch(events, cursor, drops), "Pure: no database; the caller stores the batch in one
  transaction";
- packages/spectio-sdk/src/spectio_sdk/events.py: SPOOL_FILE_NAME
  (nf-spectio|snakemake-logger-spectio)-<launch>-<nnnn>.jsonl and the MAX_* constants;
- `uv run --locked pytest -q packages/spectio/tests/test_spool_reader.py`: all pass (run
  2026-10-30; no test count, so that the figure does not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1024
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
TOP = 130  # the band where the files come from
ROW = 360  # the pictograms of the gates
TXT = ROW + 168  # the captions
BIN = ROW + 312  # the drop bins


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def sieve(s: Sketch, cx: float, top: float, w: float = 70, h: float = 46) -> None:
    """A funnel with holes: what passes goes on, the rest is held back."""
    s.poly([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.14, top + h), (cx - w * 0.14, top + h)],
           fill="gate", amount=0.8)
    for dx, dy in ((-18, 12), (0, 12), (18, 12), (-9, 26), (9, 26)):
        s.dot(cx + dx, top + dy, 2.4, colour=s.t.dim)


def drop_bin(s: Sketch, x: float, y: float, reasons: tuple[str, ...]) -> None:
    """The counters a gate feeds: a bin, and the reasons it counts, one per line."""
    s.arrow(x + 32, y - 34, x + 32, y - 6, dashed=True, colour=s.t.dim)
    s.bucket(x + 32, y + 8, 56, 50, fill="problem")
    s.text(x + 32, y + 82, "dropped,", size=12.5, colour=s.t.dim)
    s.text(x + 32, y + 99, "counted", size=12.5, colour=s.t.dim)
    for i, reason in enumerate(reasons):
        s.text(x + 78, y + 10 + i * 21, f"`{reason}`", size=13, anchor="start")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=73)
    t = theme
    s.heading(50, 58, "P3 Task 3 · the spool reader, every line untrusted",
              "`spectio.runner.spool.read_spool`, api 14.1, dev-env 15.3 req. 6 and 12 · "
              "each gate refuses, drops and counts by reason; no database access")

    # where the files come from -------------------------------------------------------------
    s.hpc_node(60, TOP, 56, 74, busy=3)
    s.hpc_node(126, TOP, 56, 74, busy=2)
    s.text(200, TOP + 20, "compute nodes", size=15, anchor="start", weight="bold")
    s.text(200, TOP + 42, "the engine bridges append", size=13.5, anchor="start", colour=t.dim)
    s.text(200, TOP + 64, "`nf-spectio`", size=13, anchor="start")
    s.text(200, TOP + 84, "`snakemake-logger-spectio`", size=13, anchor="start")
    s.arrow(430, TOP + 40, 560, TOP + 40)
    s.text(495, TOP + 30, "append", size=13, colour=t.dim)

    s.folder(580, TOP - 6, 250, 110, fill="input")
    s.text(705, TOP + 46, "`launch dir/.spectio/events/`", size=13)
    for i in range(3):
        s.page(650 + i * 40, TOP + 58, 34, 40, fill="surface", lines=2)
    s.text(705, TOP + 128, "a shared file system", size=13, colour=t.dim)

    s.arrow(850, TOP + 40, 990, TOP + 40)
    s.text(920, TOP + 30, "read", size=13, colour=t.dim)
    s.hpc_node(1010, TOP, 56, 74, busy=1)
    s.cog(1095, TOP + 36, 12, fill="docs")
    s.text(1125, TOP + 20, "login node", size=15, anchor="start", weight="bold")
    s.text(1125, TOP + 44, "`read_spool(launch_dir, run_id,`", size=13, anchor="start")
    s.text(1125, TOP + 64, "`launch_n, cursor)`", size=13, anchor="start")
    s.text(1125, TOP + 88, "called by the runner loop, Task 9,", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, TOP + 108, "and the boot rebuild, Task 11", size=13.5, anchor="start", colour=t.dim)

    s.line(30, ROW - 60, W - 30, ROW - 60, dashed=True, colour=t.muted)
    s.text(50, ROW - 70, "inside `read_spool`, in this order", size=14, anchor="start", colour=t.dim)

    # 1 -- the directories ---------------------------------------------------------------------
    x = COL[0]
    s.folder(x + 6, ROW + 6, 104, 76, fill="input", label="`.spectio`")
    s.lock(x + 100, ROW + 84, size=13)
    s.arrow(x + 120, ROW + 44, x + 150, ROW + 44)
    s.folder(x + 158, ROW + 6, 104, 76, fill="input", label="`events`")
    s.lock(x + 252, ROW + 84, size=13)
    s.text(x + 140, ROW + 120, "`O_DIRECTORY` `O_NOFOLLOW`", size=12.5)
    s.step(x + CW / 2, TXT, 1, "private directories")
    lines(s, x, TXT + 30, ("both owned by this user,",
                           "no group or other bits",
                           "missing: an empty batch",
                           "a symlink, not a directory: `OSError`"))
    s.cross(x + 26, BIN + 14, size=12)
    s.text(x + 50, BIN + 20, "`PermissionError`", size=13.5, anchor="start")
    s.text(x + 50, BIN + 44, "the whole read stops,", size=13.5, anchor="start", colour=t.dim)
    s.text(x + 50, BIN + 64, "nothing is counted", size=13.5, anchor="start", colour=t.dim)

    # 2 -- the listing -------------------------------------------------------------------------
    x = COL[1]
    names = (("`nf-spectio-2-0001.jsonl`", True), ("`nf-spectio-2-0002.jsonl`", True),
             ("`notes.txt`", False))
    for i, (name, ok) in enumerate(names):
        y = ROW + 10 + i * 34
        s.page(x + 6, y, 20, 26, fill="surface" if ok else "problem", lines=0)
        s.text(x + 34, y + 18, name, size=12.5, anchor="start")
        if ok:
            s.tick(x + 262, y + 12, size=7)
        else:
            s.cross(x + 262, y + 12, size=7)
    s.text(x + 140, ROW + 132, "at most 16 384 entries looked at", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "the names")
    lines(s, x, TXT + 30, ("`producer-launch-nnnn.jsonl` only",
                           "another launch's files: skipped",
                           "a bad name kept as a hash, up to 64",
                           "this launch: up to 1024 files"))
    drop_bin(s, x, BIN, ("bad_name", "too_many_files"))

    # 3 -- each file ---------------------------------------------------------------------------
    x = COL[2]
    s.page(x + 20, ROW + 4, 70, 92, fill="surface", lines=4)
    s.magnifier(x + 82, ROW + 64, 18)
    s.link(x + 168, ROW + 30, size=16)
    s.cross(x + 168, ROW + 30, size=14)
    s.text(x + 168, ROW + 66, "no symlink,", size=13, colour=t.dim)
    s.text(x + 168, ROW + 84, "no FIFO", size=13, colour=t.dim)
    s.lock(x + 238, ROW + 34, size=13, fill="done")
    s.text(x + 238, ROW + 66, "yours,", size=13, colour=t.dim)
    s.text(x + 238, ROW + 84, "not shared", size=13, colour=t.dim)
    s.text(x + 140, ROW + 132, "`lstat`, open `O_NOFOLLOW`, `fstat`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "each file")
    lines(s, x, TXT + 30, ("a regular file of this user",
                           "opened inside `events`, never by path",
                           "past 64 MiB: the rest is not read",
                           "refused files are never read again"))
    drop_bin(s, x, BIN, ("symlink", "not_regular", "foreign_owner", "writable_by_others",
                         "unreadable", "file_too_large"))

    # 4 -- each line ---------------------------------------------------------------------------
    x = COL[3]
    for i, (w, fill) in enumerate(((86, "surface"), (120, "problem"), (60, "surface"))):
        s.poly([(x + 6, ROW + 14 + i * 22), (x + 6 + w, ROW + 14 + i * 22),
                (x + 6 + w, ROW + 28 + i * 22), (x + 6, ROW + 28 + i * 22)], fill=fill, amount=0.4)
    s.arrow(x + 134, ROW + 46, x + 162, ROW + 46)
    sieve(s, x + 210, ROW + 18, w=80, h=54)
    s.arrow(x + 210, ROW + 76, x + 210, ROW + 104)
    s.text(x + 140, ROW + 132, "per read: 2 MiB or 5000 lines", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "each line")
    lines(s, x, TXT + 30, ("split on a newline, at most 64 KiB",
                           "4096 values, depth 32, checked",
                           "roughly before parsing, then exactly",
                           "the run and launch must match"))
    drop_bin(s, x, BIN, ("line_too_large", "too_complex", "invalid", "wrong_run", "wrong_launch"))

    # 5 -- the batch ---------------------------------------------------------------------------
    x = COL[4]
    parts = (("events", "done"), ("cursor", "input"), ("drops", "problem"))
    s.poly([(x + 6, ROW + 4), (x + 196, ROW + 4), (x + 196, ROW + 108), (x + 6, ROW + 108)],
           fill="neutral", amount=0.8)
    for i, (name, fill) in enumerate(parts):
        s.poly([(x + 16, ROW + 12 + i * 32), (x + 186, ROW + 12 + i * 32),
                (x + 186, ROW + 38 + i * 32), (x + 16, ROW + 38 + i * 32)], fill=fill, amount=0.5)
        s.text(x + 101, ROW + 30 + i * 32, f"`{name}`", size=13)
    s.arrow(x + 204, ROW + 56, x + 250, ROW + 56)
    s.text(x + 228, ROW + 84, "caller", size=13, colour=t.dim)
    s.text(x + 100, ROW + 132, "`SpoolBatch`", size=13.5)
    s.step(x + CW / 2, TXT, 5, "one batch out")
    lines(s, x, TXT + 30, ("events with allow-listed data only",
                           "cursor: bytes read per file, or -1",
                           "drops: a count per reason",
                           "stored in one transaction by the caller"))
    s.bucket(x + 40, BIN + 14, 48, 44, fill="neutral")
    s.text(x + 40, BIN + 16, "DB", size=12, colour=t.dim)
    s.cross(x + 40, BIN + 36, size=16)
    s.text(x + 80, BIN + 20, "no database access:", size=13.5, anchor="start")
    s.text(x + 80, BIN + 42, "a pure function of the", size=13.5, anchor="start", colour=t.dim)
    s.text(x + 80, BIN + 62, "files and the cursor", size=13.5, anchor="start", colour=t.dim)

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 46, cx + CW + 23, ROW + 46)

    # before and around the gates ----------------------------------------------------------------
    by = 860
    s.shade(50, by, 1000, 110, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(78, by + 30, size=11)
    s.text(100, by + 36, "first, the cursor that comes in is checked: a key that is not this launch's file,",
           size=13.5, anchor="start")
    s.text(100, by + 58, "or a value out of range, is dropped or reset and counted as `bad_cursor`",
           size=13.5, anchor="start", colour=t.dim)
    s.warning(78, by + 82, size=11)
    s.text(100, by + 88, "any other read error: `read_error`, retried next time · a file gone since the listing:"
           " skipped", size=13.5, anchor="start")
    s.terminal(1100, by, 450, 110, ("$ uv run --locked pytest -q \\",
                                     "    packages/spectio/tests/test_spool_reader.py",
                                     "all pass"), size=12.5)

    s.text(W - 50, H - 16, "source: spectio/runner/spool.py, spectio_sdk/events.py · api 14.1 · "
           "dev-env 15.3 req. 6 and 12 · P1 Task 3", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t03-spool-reader")
