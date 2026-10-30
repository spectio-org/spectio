#!/usr/bin/env python3
"""nf-spectio writes the spool: step P3, P1 Task 6, 2026-10-30.

Writes docs/assets/diagrams/p3-t06-nf-spectio_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t06 at 17281b7 (BASE a758cf3):
- engine-bridges/nf-spectio/src/spectio/SpectioPlugin.groovy:
  SpectioFactory: silent unless SPECTIO_RUN_ID, SPECTIO_LAUNCH_N or SPECTIO_SPOOL_DIR is set;
  SpectioObserver: 12 hooks call emit() (onFlowCreate, onFlowBegin, onFlowComplete,
  onProcessCreate, onProcessTerminate, onTaskPending, onTaskSubmit, onTaskStart, onTaskComplete,
  onTaskCached, onFlowError, onFilePublish); onWorkflowOutput is empty; emit() catches every
  Throwable; TRACE_KEYS has no script, env or hostname; onFlowComplete sends errorMessage null
  when session.fault.task is set, else Nextflow's own error, take(MAX_MESSAGE_CHARS 4096);
  Spool: LinkedBlockingQueue(QUEUE_CAPACITY 100000), enqueue() uses offer() and counts a drop;
  one daemon thread 'nf-spectio-writer'; a JVM shutdown hook calls close(): offer(STOP, 5 s),
  join(10000), then if the thread is alive one stderr line and return, else finish(dropped)
  and close();
  SpoolWriter: envelope v, id evt_ + ULID, run, launch, producer nf-spectio/0.0.1, seq, time,
  type, data; a line over MAX_LINE_BYTES 65536 is dropped and logged; rotates past
  ROTATE_BYTES 33554432; next() uses createFile (never a file that exists) up to index 9999,
  dirs rwx------, files rw-------, and reopens the current file while it is still empty;
  a failed write logs, truncate(size), and closes only when the truncate fails or the file
  is gone; error() logs at most MAX_ERROR_LINES 100; finish() writes past the cap
  "N further errors not logged" and "N events dropped: the queue was full"; log() writes
  bridge.err only when it is a regular file, else stderr.
- packages/spectio/tests/test_bridge_nextflow.py: test_error_cap_keeps_the_summary (150
  errors, finish(7): lines 101 and 102 are "50 further errors not logged" and "7 events
  dropped: the queue was full"); test_writer_does_not_rotate_on_a_failed_write,
  test_writer_truncates_a_failed_write (ulimit -f 16, EFBIG); test_bridge_err_fifo_does_not_
  hang_the_head; test_stuck_writer_does_not_hang_the_head; test_task_stderr_kept_out_of_the_
  spool; test_no_script_or_env_keys.
- The bars: engine-bridges/nf-spectio/tests/run_local.sh on the synthetic pipeline, profile
  test,local, Nextflow 26.10.4, run 2026-10-30. happy: one file nf-spectio-1-0001.jsonl,
  298 lines, 239600 bytes, longest line 1545 bytes; onTaskPending, onTaskSubmit, onTaskStart,
  onTaskComplete 65 each, onFilePublish 19, onProcessCreate 8, onProcessTerminate 8,
  onFlowCreate, onFlowBegin, onFlowComplete 1 each; onFlowComplete data success true,
  exitStatus 0. The COMPARE failure (--fail_mode exit --fail_process COMPARE --fail_sample
  treatA): 293 lines, onFlowComplete success false, exitStatus 1, errorMessage null.
- `pytest -m engines packages/spectio/tests/test_bridge_nextflow.py` with that launcher:
  13 passed, 1 skipped (mode_0500 is skipped as root), run 2026-10-30.
- Finding IDs: docs/reviews/code/P3-t06.md. The IDs are reused across rounds, so each pin
  names its round: round 1 CR-P3T06-01 (major, a new file per failed write); round 2
  CR-P3T06-02 (torn line before a rotation), CR-P3T06-04 (the cap hides the close summary),
  SEC-P3T06-02 (the shutdown hook can hang; reproduced with bridge.err as a FIFO, the JVM
  alive past SIGTERM at 60 s). Still open, minor: round 2 SEC-P3T06-04 (queue bounded by
  count, about 0.5 GB of heap, an estimate), round 3 SEC-P3T06-03 (check then open on
  bridge.err in the hook thread), round 2 SEC-P3T06-03 (fd-relative writes, plan Task 25),
  round 2 SEC-P3T06-05 (Nextflow's own error text is sent, api 14.1 [to be validated]).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1280
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 140  # the pictograms of the flow
TXT = ROW + 150  # the captions
FIX = 500  # the before and after panels
LOW = 960  # the measured run and the notes


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          step: float = 21) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * step, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, label: str) -> None:
    """A finding pinned where it hits: a red dot and its ID."""
    s.circle(x, y - 5, 6, fill="problem", colour=s.t.accent, width=1.6)
    s.text(x + 13, y, label, size=13, anchor="start", colour=s.t.accent)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s._parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 1.5):.1f}" height="{h:.1f}" rx="2" '
        f'fill="{s.t.fill(fill)}" stroke="{s.t.ink}" stroke-width="0.9"/>'
    )


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=61)
    t = theme
    s.heading(50, 58, "P3 Task 6 · `nf-spectio` writes the spool, and never fails the run",
              "`engine-bridges/nf-spectio`, api 14.1, architecture 13.1 and 13.3 · the hooks only enqueue; "
              "one writer thread appends; the JVM's shutdown ends the stream")

    # 1 -- the hooks -------------------------------------------------------------------------
    x = COL[0]
    s.hpc_node(x + 6, ROW - 6, 66, 92, busy=3)
    for i, hook in enumerate(("`onFlowCreate`", "`onTaskStart`", "`onTaskComplete`", "`onFilePublish`")):
        s.line(x + 80, ROW + 8 + i * 22, x + 96, ROW + 8 + i * 22, colour=t.dim, passes=1, amount=0.4)
        s.text(x + 102, ROW + 13 + i * 22, hook, size=12.5, anchor="start")
    s.text(x + 140, ROW + 116, "the Nextflow head, one JVM", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "the hooks only enqueue")
    lines(s, x, TXT + 30, ("12 hooks, allow-listed values only",
                           "never block, never throw",
                           "writes only when `SPECTIO_RUN_ID`,",
                           "`_LAUNCH_N`, `_SPOOL_DIR` are valid"))

    # 2 -- the queue -------------------------------------------------------------------------
    x = COL[1]
    s.line(x + 10, ROW + 20, x + 200, ROW + 20, passes=1, amount=0.6)
    s.line(x + 10, ROW + 64, x + 200, ROW + 64, passes=1, amount=0.6)
    for i in range(6):
        s.envelope(x + 18 + i * 30, ROW + 30, 24, 24, fill="input")
    s.text(x + 105, ROW + 10, "at most 100 000 items", size=13, colour=t.dim)
    s.arrow(x + 200, ROW + 70, x + 232, ROW + 92, dashed=True, colour=t.dim)
    s.bucket(x + 250, ROW + 88, 46, 36, fill="problem")
    s.text(x + 120, ROW + 104, "full: dropped,", size=13, colour=t.dim)
    s.text(x + 120, ROW + 122, "counted", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "a bounded queue")
    lines(s, x, TXT + 30, ("`offer`, never `put`: a hook never waits",
                           "a full queue drops the event and",
                           "counts it for the close summary"))

    # 3 -- the writer thread -----------------------------------------------------------------
    x = COL[2]
    s.cog(x + 50, ROW + 42, 20, fill="work")
    s.arrow(x + 86, ROW + 42, x + 120, ROW + 42)
    s.page(x + 128, ROW + 4, 140, 80, fill="surface", lines=0)
    for i, row in enumerate(("`v id run launch`", "`producer seq time`", "`type data`")):
        s.text(x + 138, ROW + 30 + i * 20, row, size=12, anchor="start")
    s.text(x + 140, ROW + 116, "one thread, `nf-spectio-writer`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "one line per event")
    lines(s, x, TXT + 30, ("an envelope v1, `seq` without gaps",
                           "a line over 64 KiB: dropped, logged",
                           "every error caught, the run goes on"))

    # 4 -- the spool files -------------------------------------------------------------------
    x = COL[3]
    s.folder(x + 6, ROW - 4, 268, 106, fill="input")
    s.text(x + 140, ROW + 30, "`.spectio/events/`", size=13)
    for i in range(3):
        s.page(x + 70 + i * 50, ROW + 42, 40, 50, fill="surface", lines=3)
    s.lock(x + 238, ROW + 70, size=13, fill="done")
    s.text(x + 140, ROW + 124, "`nf-spectio-1-0001.jsonl`, 0002", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "the spool files")
    lines(s, x, TXT + 30, ("a new file past 32 MiB",
                           "`createFile`: never one that exists",
                           "directories 0700, files 0600",
                           "files opened `NOFOLLOW_LINKS`"))

    # 5 -- bridge.err ------------------------------------------------------------------------
    x = COL[4]
    s.page(x + 20, ROW - 2, 96, 110, fill="problem", lines=5)
    s.warning(x + 68, ROW + 22, size=12)
    s.text(x + 136, ROW + 34, "`.spectio/bridge.err`", size=12.5, anchor="start")
    s.text(x + 136, ROW + 58, "next to `events`", size=13, anchor="start", colour=t.dim)
    s.text(x + 136, ROW + 80, "not a regular file:", size=13, anchor="start", colour=t.dim)
    s.text(x + 136, ROW + 98, "stderr instead", size=13, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "errors on the side")
    lines(s, x, TXT + 30, ("at most 100 lines while running",
                           "then the close summary,",
                           "past the cap"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 42, cx + CW + 23, ROW + 42)

    # what the review rounds changed ---------------------------------------------------------
    s.line(30, FIX - 52, W - 30, FIX - 52, dashed=True, colour=t.muted)
    s.text(50, FIX - 62, "what the three review rounds changed, before and after", size=14,
           anchor="start", colour=t.dim)
    PW = 480
    PX = (50, 560, 1070)

    # A -- a failed write
    x = PX[0]
    s.text(x, FIX, "A · a write fails: disk full, file size limit, quota", size=17, anchor="start")
    s.text(x, FIX + 32, "before", size=14, anchor="start", weight="bold")
    for i in range(10):
        s.page(x + 4 + (i % 5) * 34, FIX + 46 + (i // 5) * 40, 26, 32, fill="problem", lines=0)
    s.text(x + 186, FIX + 70, "one new file", size=13, anchor="start", colour=t.dim)
    s.text(x + 186, FIX + 88, "per event", size=13, anchor="start", colour=t.dim)
    lines(s, x, FIX + 152, ("past 1024 files the reader counts",
                            "`too_many_files` and reads no more",
                            "of the launch, `onFlowComplete` too"), size=13, step=19)
    pin(s, x + 8, FIX + 252, "CR-P3T06-01, round 1, major")

    ax = x + 268
    s.text(ax, FIX + 32, "after", size=14, anchor="start", weight="bold")
    s.page(ax, FIX + 46, 110, 112, fill="surface", lines=0)
    for i in range(4):
        s.line(ax + 8, FIX + 70 + i * 16, ax + 96, FIX + 70 + i * 16, colour=t.muted, passes=1, amount=0.3,
               width=3)
    bar(s, ax + 8, FIX + 132, 58, 7, "problem")
    s.line(ax + 4, FIX + 125, ax + 104, FIX + 125, dashed=True, colour=t.accent, passes=1, amount=0.3)
    s.tick(ax + 132, FIX + 76, size=9)
    s.text(ax + 120, FIX + 106, "same file", size=13, anchor="start")
    s.text(ax + 120, FIX + 128, "partial line cut:", size=13, anchor="start", colour=t.dim)
    s.text(ax + 120, FIX + 146, "`truncate(size)`", size=13, anchor="start")
    lines(s, ax, FIX + 182, ("a new file only when",
                             "the file itself is gone"), size=13, step=19)
    pin(s, ax + 8, FIX + 252, "CR-P3T06-02, round 2")

    # B -- the error cap
    x = PX[1]
    s.text(x, FIX, "B · more than 100 errors", size=17, anchor="start")
    s.text(x, FIX + 32, "a test writes 150 errors, then the close summary with 7 drops",
           size=13, anchor="start", colour=t.dim)
    cell, gap = 2.0, 0.9
    y = FIX + 56
    s.text(x, y + 14, "before", size=14, anchor="start", weight="bold")
    bx = x + 70
    for i in range(100):
        bar(s, bx + i * (cell + gap), y, cell, 20, "neutral")
    s.cross(bx + 101 * (cell + gap) + 4, y + 10, size=7)
    s.text(bx + 102 * (cell + gap) + 12, y + 15, "summary lost", size=13, anchor="start", colour=t.accent)

    y = FIX + 104
    s.text(x, y + 14, "after", size=14, anchor="start", weight="bold")
    for i in range(102):
        bar(s, bx + i * (cell + gap), y, cell, 20, "neutral" if i < 100 else "done")
    s.tick(bx + 102 * (cell + gap) + 14, y + 8, size=8)
    s.text(bx + 155, y + 40, "100 lines, the cap", size=13, colour=t.dim)
    s.arrow(bx + 102 * (cell + gap) - 2, y + 54, bx + 102 * (cell + gap) - 2, y + 26, colour=t.dim)
    lines(s, x, y + 76, ("line 101: `50 further errors not logged`",
                         "line 102: `7 events dropped: the queue was full`",
                         "`finish()` writes both, past the cap"), size=13, step=19)
    pin(s, x + 8, FIX + 252, "CR-P3T06-04, round 2")

    # C -- the head's exit
    x = PX[2]
    s.text(x, FIX, "C · the head exits, even with a stuck writer", size=17, anchor="start")
    s.text(x, FIX + 32, "the shutdown hook, to scale in seconds", size=13, anchor="start", colour=t.dim)
    ox, px_s, y = x + 10, 22.0, FIX + 70
    s.line(ox, y + 26, ox + 15 * px_s + 4, y + 26, passes=1, amount=0.3, colour=t.dim)
    for sec in (0, 5, 15):
        s.line(ox + sec * px_s, y + 22, ox + sec * px_s, y + 30, passes=1, amount=0.2, colour=t.dim)
        s.text(ox + sec * px_s, y + 46, f"{sec} s", size=12.5, colour=t.dim)
    bar(s, ox, y, 5 * px_s, 20, "gate")
    bar(s, ox + 5 * px_s, y, 10 * px_s, 20, "work")
    s.text(ox + 2.5 * px_s, y - 8, "`STOP`, up to 5 s", size=12.5)
    s.text(ox + 10 * px_s, y - 8, "`join`, up to 10 s", size=12.5)

    yb = y + 72
    s.text(x, yb, "before", size=14, anchor="start", weight="bold")
    s.arrow(x + 60, yb - 5, x + 300, yb - 5, dashed=True, colour=t.accent)
    s.text(x + 310, yb, "waits on its lock", size=13, anchor="start", colour=t.accent)
    s.text(x + 60, yb + 20, "the head never exits: alive at 60 s, only `SIGKILL`", size=13,
           anchor="start", colour=t.dim)
    ya = yb + 50
    s.text(x, ya, "after", size=14, anchor="start", weight="bold")
    s.tick(x + 72, ya - 6, size=8)
    s.text(x + 90, ya, "writer still alive at 15 s: one stderr line, return", size=13, anchor="start")
    s.text(x + 90, ya + 20, "a FIFO as `bridge.err`: the message goes to stderr", size=13,
           anchor="start", colour=t.dim)
    pin(s, x + 8, FIX + 252, "SEC-P3T06-02, round 2")

    for px in PX[1:]:
        s.line(px - 16, FIX - 14, px - 16, FIX + 262, dashed=True, colour=t.muted, passes=1)

    # the happy run, measured ----------------------------------------------------------------
    s.line(30, LOW - 150, W - 30, LOW - 160, dashed=True, colour=t.muted)
    s.text(50, LOW - 160, "a real run: the synthetic pipeline, 65 tasks, local executor, Nextflow 26.10.4",
           size=14, anchor="start", colour=t.dim)
    counts = (("onTaskPending", 65), ("onTaskSubmit", 65), ("onTaskStart", 65), ("onTaskComplete", 65),
              ("onFilePublish", 19), ("onProcessCreate", 8), ("onProcessTerminate", 8),
              ("onFlowCreate", 1), ("onFlowBegin", 1), ("onFlowComplete", 1))
    per = 4.0  # px per event
    y0 = LOW - 110
    s.text(50, y0 - 6, "298 events, one bar each type, 4 px per event", size=14.5, anchor="start")
    for i, (name, n) in enumerate(counts):
        y = y0 + 12 + i * 21
        s.text(230, y + 13, f"`{name}`", size=12.5, anchor="end")
        bar(s, 240, y, n * per, 15, "input" if n == 65 else "docs" if n > 1 else "done")
        s.text(248 + n * per, y + 13, str(n), size=12.5, anchor="start", colour=t.dim)

    # the file, to scale against the rotation size
    fy = y0 + 250
    s.text(50, fy, "the whole spool against one file's 32 MiB", size=14.5, anchor="start")
    s.shade(50, fy + 14, 680, 24, fill="neutral", opacity=0.7, colour=t.muted)
    bar(s, 50, fy + 14, 680 * 239600 / 33554432, 24, "input")
    s.text(64, fy + 31, "239 600 bytes, 0.7 %, one file: `nf-spectio-1-0001.jsonl`", size=13,
           anchor="start")
    s.text(50, fy + 60, "longest line 1545 bytes of the 65 536 allowed", size=13, anchor="start",
           colour=t.dim)

    # what is never sent, what stays open, the tests -----------------------------------------
    nx = 820
    s.text(nx, y0 - 6, "never in the spool", size=14.5, anchor="start")
    for i, (row, sub) in enumerate((
            ("the task's script and env", "no such key in the trace allow-list"),
            ("the failed task's stderr", "with a failed task, `errorMessage` is null"),
            ("Nextflow's error report", "not one of the sent fields"))):
        y = y0 + 22 + i * 44
        s.cross(nx + 10, y - 4, size=7)
        s.text(nx + 28, y, row, size=13.5, anchor="start")
        s.text(nx + 28, y + 18, sub, size=13, anchor="start", colour=t.dim)
    s.text(nx + 380, y0 + 22, "the COMPARE failure, 293 events:", size=13, anchor="start", colour=t.dim)
    s.text(nx + 380, y0 + 42, "`success false, exitStatus 1,`", size=12.5, anchor="start")
    s.text(nx + 380, y0 + 62, "`errorMessage null`", size=12.5, anchor="start")

    oy = y0 + 160
    s.text(nx, oy, "still open, minor", size=14.5, anchor="start")
    for i, row in enumerate((
            "Nextflow's own error text is sent, up to 4096 characters: api 14.1, to be validated",
            "the queue is bounded by count, not bytes: about 0.5 GB of head heap, an estimate",
            "the launch directory is not checked, writes are not fd-relative: plan Task 25",
            "`bridge.err` is checked, then opened: a same-user FIFO swap can still hang the hook")):
        y = oy + 26 + i * 22
        s.warning(nx + 10, y - 5, size=7)
        s.text(nx + 26, y, row, size=13, anchor="start", colour=t.dim)

    s.terminal(nx, oy + 122, 730, 92, ("$ pytest -m engines packages/spectio/tests/test_bridge_nextflow.py",
                                        "13 passed, 1 skipped    Nextflow 26.10.4, mode_0500 skipped as root"),
               size=12.5)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: `SpectioPlugin.groovy`, `test_bridge_nextflow.py`, `run_local.sh` on 2026-10-30 · "
           "docs/reviews/code/P3-t06.md · api 14.1 · P1 Task 6", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t06-nf-spectio")
