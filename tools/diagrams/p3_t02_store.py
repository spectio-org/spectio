#!/usr/bin/env python3
"""The checks before the SQLite index is used: step P3, P1 Task 2, 2026-10-30.

Writes docs/assets/diagrams/p3-t02-store_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t02 at af8b4bf:
- packages/spectio-server/src/spectio_server/store/db.py:
  default_db_dir(): the base is $TMPDIR when it is absolute and passes the owner and mode rule, else
  /tmp with a warning; an unsafe /tmp is refused ("choose the database directory with --db-dir");
  spectio-<uid> made with os.mkdir 0700 and checked with O_DIRECTORY|O_NOFOLLOW; a squatted path is
  left as it is and tempfile.mkdtemp(prefix="spectio-<uid>-") is used, with a warning;
  open_db(): check_sqlite_version (3.51.3, 3.50.7, 3.44.6), the private directory (no fallback),
  realpath of the parent once (SEC-P3T2-13), _check_parents (_trusted: owner root or the user, not
  writable by group or others unless sticky), fs_type from /proc/self/mountinfo by st_dev, then the
  longest mount point, refused on Linux without a usable table; NETWORK_FS nfs, nfs4, lustre, gpfs,
  beegfs, cifs, smb3, ceph, fuse.sshfs, autofs; spectio.db created O_CREAT|O_EXCL|O_NOFOLLOW 0600,
  spectio.db, -wal, -shm checked by _check_private_file; pins (st_dev, st_ino) of the directory and
  of spectio.db, checked by _check_pins on the first raw connection and in the connect hook;
  busy_timeout 5000, foreign_keys ON; created is True when no Alembic revision is found;
- packages/spectio-server/src/spectio_server/store/writer.py: one thread "spectio-writer", one
  connection, each job in BEGIN IMMEDIATE, in submit order; readers keep a deferred BEGIN (db.py);
- `uv run --locked pytest -q`: all pass (re-run 2026-10-30; no test count, so that the figure does
  not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1040
COL = (50, 440, 830, 1220)  # four columns, 340 wide, 50 apart
ROW1, ROW2 = 130, 520


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, first_bold: bool = True) -> None:
    for i, row in enumerate(rows):
        bold = first_bold and i == 0
        s.text(x, y + i * 22, row, size=15 if bold else 13.5, anchor="start",
               weight="bold" if bold else "normal", colour=None if bold or i == 1 else s.t.dim)


def pushpin(s: Sketch, cx: float, cy: float) -> None:
    s.line(cx, cy, cx, cy + 22, width=2, amount=0.3, passes=1)
    s.circle(cx, cy - 4, 8, fill="problem")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=72)
    t = theme
    s.heading(50, 58, "P3 Task 2 · the checks before the SQLite index is used",
              "`spectio_server.store`, architecture 7.2 and api 7 · each check refuses, "
              "or falls back where a default allows it")

    # row 1 ----------------------------------------------------------------------------------
    # 1 -- the base
    x = COL[0]
    s.folder(x + 10, ROW1 + 10, 120, 84, fill="input", label="`$TMPDIR`")
    s.tick(x + 150, ROW1 + 40, size=8)
    s.folder(x + 180, ROW1 + 10, 120, 84, fill="neutral", label="`/tmp`")
    s.text(x + 240, ROW1 + 118, "else", size=13, colour=t.dim)
    lines(s, x, ROW1 + 150, ("the base: `$TMPDIR`, else `/tmp`",
                             "absolute, owned by root or this user,",
                             "writable by others only if sticky",
                             "a refused `$TMPDIR`: a warning, then `/tmp`",
                             "an unsafe `/tmp`: refused, use `--db-dir`"))
    s.step(x + 170, ROW1 + 300, 1, "the base")

    # 2 -- the private directory
    x = COL[1]
    s.folder(x + 30, ROW1 + 4, 180, 100, fill="done", label="`/tmp/spectio-<uid>`")
    s.lock(x + 240, ROW1 + 56, size=16)
    s.text(x + 268, ROW1 + 62, "0700", size=14, anchor="start")
    lines(s, x, ROW1 + 150, ("a private directory, mode 0700",
                             "opened with `O_NOFOLLOW`: a real directory",
                             "of this user, no group or other bits",
                             "squatted: left alone, a fresh `mkdtemp`",
                             "one with a warning; `--db-dir`: refused"))
    s.step(x + 170, ROW1 + 300, 2, "the directory")

    # 3 -- the parents
    x = COL[2]
    chain = (("`/`", "root"), ("`tmp`", "root, sticky"))
    for i, (name, owner) in enumerate(chain):
        fx = x + i * 112
        s.folder(fx, ROW1 + 20, 84, 60, fill="neutral" if i < 2 else "done")
        s.text(fx + 42, ROW1 + 100, name, size=13)
        s.text(fx + 42, ROW1 + 120, owner, size=12.5, colour=t.dim)
        s.tick(fx + 42, ROW1 + 4, size=7)
        if i:
            s.arrow(fx - 26, ROW1 + 52, fx - 4, ROW1 + 52)
    lines(s, x, ROW1 + 150, ("every parent, up to `/`",
                             "owned by root or this user, not writable",
                             "by group or others unless sticky",
                             "as OpenSSH StrictModes, plus the sticky case",
                             "else refused: someone could swap the directory"))
    s.step(x + 170, ROW1 + 300, 3, "the parents")

    # 4 -- the canonical path
    x = COL[3]
    s.folder(x, ROW1 + 24, 96, 64, fill="problem")
    s.text(x + 48, ROW1 + 110, "`shared/link`", size=13)
    s.link(x + 134, ROW1 + 56, size=18)
    s.arrow(x + 160, ROW1 + 56, x + 214, ROW1 + 56)
    s.folder(x + 224, ROW1 + 24, 96, 64, fill="done")
    s.text(x + 272, ROW1 + 110, "`real/path`", size=13)
    lines(s, x, ROW1 + 150, ("the canonical path, resolved once",
                             "the parent goes through `realpath` once,",
                             "and only that path is used afterwards",
                             "a link in a shared directory cannot be",
                             "flipped under the checks, SEC-P3T2-13"))
    s.step(x + 170, ROW1 + 300, 4, "one path")

    for cx in COL[:3]:
        s.arrow(cx + 344, ROW1 + 56, cx + 384, ROW1 + 56)
    # from 4 down and back to 5
    s.line(1570, ROW1 + 56, 1570, ROW2 - 40, dashed=True, colour=t.dim)
    s.line(1570, ROW2 - 40, 30, ROW2 - 40, dashed=True, colour=t.dim)
    s.arrow(30, ROW2 - 40, 30, ROW2 + 50, dashed=True, colour=t.dim)

    # row 2 ----------------------------------------------------------------------------------
    # 5 -- the file system type
    x = COL[0]
    s.page(x + 20, ROW2, 72, 92, fill="input", lines=4)
    s.text(x + 56, ROW2 + 116, "`mountinfo`", size=13)
    s.magnifier(x + 120, ROW2 + 40, 20)
    s.cross(x + 210, ROW2 + 30, size=8)
    s.text(x + 226, ROW2 + 36, "`nfs` `nfs4`", size=13, anchor="start")
    s.text(x + 226, ROW2 + 58, "`lustre` `gpfs`", size=13, anchor="start")
    s.text(x + 226, ROW2 + 80, "`ceph` `autofs`", size=13, anchor="start")
    s.text(x + 226, ROW2 + 102, "and 4 more", size=13, anchor="start", colour=t.dim)
    lines(s, x, ROW2 + 150, ("the file system, network ones refused",
                             "the mount of the directory's device, the top",
                             "of a stack; else the longest mount point",
                             "no usable `mountinfo` on Linux: refused",
                             "also `beegfs` `cifs` `smb3` `fuse.sshfs`"))
    s.step(x + 170, ROW2 + 300, 5, "the file system")

    # 6 -- the files
    x = COL[1]
    for i, name in enumerate(("`spectio.db`", "`-wal`", "`-shm`")):
        px = x + 20 + i * 104
        s.page(px, ROW2 + 4, 56, 74, fill="done", lines=3)
        s.lock(px + 56, ROW2 + 76, size=11)
        s.text(px + 28, ROW2 + 110, name, size=13)
    lines(s, x, ROW2 + 150, ("the files, mode 0600",
                             "`spectio.db` made with `O_EXCL` at 0600,",
                             "never chmod-ed; WAL and SHM inherit it",
                             "a symlink, another owner, a group or other",
                             "bit: refused"))
    s.step(x + 170, ROW2 + 300, 6, "the files")

    # 7 -- the pins
    x = COL[2]
    s.folder(x + 20, ROW2 + 26, 100, 64, fill="done")
    pushpin(s, x + 70, ROW2 + 14)
    s.page(x + 160, ROW2 + 20, 56, 74, fill="done", lines=3)
    pushpin(s, x + 188, ROW2 + 10)
    s.text(x + 70, ROW2 + 116, "device, inode", size=13, colour=t.dim)
    s.text(x + 188, ROW2 + 116, "device, inode", size=13, colour=t.dim)
    s.cross(x + 268, ROW2 + 50, size=9)
    s.text(x + 268, ROW2 + 84, "replaced", size=13)
    lines(s, x, ROW2 + 150, ("pins, checked on each connection",
                             "the directory and `spectio.db`, pinned",
                             "after the checks; every new connection",
                             "compares them before it reads anything",
                             "replaced: the connection is closed, refused"))
    s.step(x + 170, ROW2 + 300, 7, "the pins")

    # 8 -- one writer
    x = COL[3]
    for i in range(3):
        s.envelope(x + 4, ROW2 + 8 + i * 30, 44, 24, fill="work")
    s.arrow(x + 58, ROW2 + 50, x + 104, ROW2 + 50)
    s.cog(x + 130, ROW2 + 50, 16, fill="violet")
    s.text(x + 130, ROW2 + 100, "`spectio-writer`", size=13)
    s.arrow(x + 158, ROW2 + 50, x + 214, ROW2 + 50)
    s.page(x + 226, ROW2 + 12, 56, 74, fill="done", lines=3)
    s.text(x + 254, ROW2 + 110, "`spectio.db`", size=13)
    lines(s, x, ROW2 + 150, ("one writer thread, `BEGIN IMMEDIATE`",
                             "one connection; each job is one transaction,",
                             "in submit order, so no lock upgrade",
                             "readers keep a deferred `BEGIN`; WAL,",
                             "`busy_timeout` 5000, foreign keys on"))
    s.step(x + 170, ROW2 + 300, 8, "one writer")

    for cx in COL[:3]:
        s.arrow(cx + 344, ROW2 + 50, cx + 384, ROW2 + 50)

    # before and after the chain ---------------------------------------------------------------
    by = 870
    s.shade(50, by, 960, 120, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(78, by + 34, size=11)
    s.text(100, by + 40, "before the chain: the SQLite that Python loads needs the WAL-reset fix,",
           size=13.5, anchor="start")
    s.text(100, by + 62, "3.51.3 or later, or 3.50.7 in the 3.50 series, or 3.44.6 in the 3.44 series",
           size=13.5, anchor="start", colour=t.dim)
    s.tick(78, by + 92, size=7)
    s.text(100, by + 98, "after it: `open_db` says the index is new, a new file or no Alembic revision,"
           " and boot rebuilds it, Task 11", size=13.5, anchor="start")
    s.terminal(1060, by, 490, 120, ("$ uv run --locked pytest -q", "pytest: all pass",
                                     "ruff, mypy, lint-imports: clean, 3 kept"), size=12.5)

    s.text(W - 50, H - 16, "source: spectio_server/store/db.py, writer.py · architecture 7.2 · api 7 · "
           "P1 Task 2 · OpenSSH `misc.c` `safe_path`", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t02-store")
