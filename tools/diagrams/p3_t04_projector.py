#!/usr/bin/env python3
"""The projector: step P3, P1 Task 4, 2026-10-30.

Writes docs/assets/diagrams/p3-t04-projector_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t04 at 318e30c:
- packages/spectio-server/src/spectio_server/projector/ingest.py: ingest(conn, launch_id, batch):
  a batch of another run or launch raises ValueError and writes nothing; an event ID already in
  the run's log is skipped; parse_data re-checks the data, failure counted `invalid`; each event
  is logged and projected in its own savepoint (begin_nested), `p.move("running")` on the first
  engine event; an exception is logged with log.exception, rolled back and counted
  `projection_error`; an OperationalError propagates and the whole batch rolls back;
  _store_cursor upserts each offset and adds each drop count; p.finish().
  apply_head_report(conn, launch_id, report): a running head starts a queued run; a failure
  fails a queued or running run, `head_lost` / `engine_fault` close open attempts as failed with
  class head_lost; a head that ends while `cancelling` makes it `cancelled`; head_state is not
  overwritten once the engine ended the launch (ENGINE_ENDED).
- projector/nextflow.py: task key process + tag, or process + Nextflow's task `name` when there
  is no tag; attempt key task, launch_n, attempt n; _RANK pending 0, submitted 1, running 2,
  every end state 3, a late event of lower or equal rank changes nothing; onTaskComplete takes
  its state from trace.status (COMPLETED succeeded, FAILED failed, ABORTED aborted); a failed
  attempt with errorAction TERMINATE gets failure_class `tool_error`, and the launch's
  culprit_attempt_id is set only while it is null (the first one, in seq order); _flow_complete:
  a terminal run is not moved (a second onFlowComplete is logged only), end_launch() aborts the
  open attempts, cancelling becomes cancelled, else succeeded or failed; _failure: tool_error with
  the culprit's task_id and attempt n, else `engine_fault`.
- projector/runs.py: Projection.log allocates seq; move() follows _NEXT (queued, running,
  cancelling) and never leaves a terminal state; sync_tasks: a task takes its last attempt's
  state; finish(): task_counts from the tasks' states, last_seq = projected_seq.
- store/writer.py: one thread, one connection, one `BEGIN IMMEDIATE` per submitted function.
- store/schema.py and migrations/versions/0002_task_name.py: tasks.name, launches.culprit_attempt_id.
- The numbers at the bottom: tests/fixtures/engine-events/nextflow-26.10.4_plugin_toolerr.spool.jsonl
  read with read_spool(max_lines=100) and ingested through the Writer, as
  packages/spectio-server/tests/test_projector_nextflow.py replay() does (run 2026-10-30): 3 reads,
  293 events (onTaskPending 65, onTaskSubmit 64, onTaskStart 64, onTaskComplete 64,
  onFilePublish 17, onProcessCreate 8, onProcessTerminate 7, onFlowCreate, onFlowBegin,
  onFlowError and onFlowComplete 1 each), 295 log rows (2 spectio.run.state_changed), seq 295 =
  projected_seq 295, no drops; task_counts succeeded 63, failed 1, aborted 1; runs.failure
  class tool_error, task COMPARE treatA_vs_ctrl attempt 1, message "synthetic failure: tool
  exited with code 1"; FINAL_REPORT aborted with no failure class.
- The culprit panel: test_first_terminate_in_a_batch_is_the_culprit (two TERMINATE failures,
  tags S01 then S02, in one batch: both tool_error, S01 blamed).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1230
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 380  # the pictograms of the steps
TXT = ROW + 150  # the captions
BIN = TXT + 128  # the drop counters
LOW = 815  # the replayed fixture and the side panels


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def counter(s: Sketch, x: float, y: float, reason: str, note: str) -> None:
    """A drop counter: a small bin and the reason it counts."""
    s.bucket(x + 22, y, 36, 32, fill="problem")
    s.text(x + 52, y + 12, f"`{reason}`", size=13, anchor="start")
    s.text(x + 52, y + 32, note, size=12.5, anchor="start", colour=s.t.dim)


def pill(s: Sketch, cx: float, cy: float, label: str, fill: str, rx: float = 44) -> None:
    s.ellipse(cx, cy, rx, 14, fill=fill)
    s.text(cx, cy + 5, label, size=13)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=74)
    t = theme
    s.heading(50, 58, "P3 Task 4 · the projector, spool events become runs, tasks and attempts",
              "`spectio_server.projector`, api 7.1, 7.2 and 8.2 · "
              "every write on the one writer, one transaction per call")

    # where the calls come from ------------------------------------------------------------------
    y0 = 118
    for i in range(3):
        s.page(60 + i * 14, y0 + i * 8, 46, 58, fill="input", lines=3)
    s.text(140, y0 + 22, "`ingest(conn, launch_id, batch)`", size=13.5, anchor="start")
    s.text(140, y0 + 44, "a `SpoolBatch` from `read_spool`, Task 3:", size=13.5, anchor="start", colour=t.dim)
    s.text(140, y0 + 64, "events, cursor, drops", size=13.5, anchor="start", colour=t.dim)

    s.runner(60, y0 + 104, 104, 48)
    s.text(184, y0 + 122, "`apply_head_report(conn, launch_id, report)`", size=13.5, anchor="start")
    s.text(184, y0 + 144, "what the runner saw of the head, Tasks 9 to 11", size=13.5, anchor="start",
           colour=t.dim)

    s.arrow(420, y0 + 40, 650, y0 + 72)
    s.arrow(520, y0 + 128, 650, y0 + 96)
    s.cog(690, y0 + 84, 22, fill="work")
    s.text(730, y0 + 70, "the one writer", size=15, anchor="start", weight="bold")
    s.text(730, y0 + 92, "one thread, one connection,", size=13.5, anchor="start", colour=t.dim)
    s.text(730, y0 + 112, "each call one `BEGIN IMMEDIATE`", size=13.5, anchor="start", colour=t.dim)

    s.arrow(985, y0 + 84, 1060, y0 + 84)
    s.bucket(1110, y0 + 46, 74, 70, fill="neutral")
    s.text(1110, y0 + 92, "store", size=13, colour=t.dim)
    tables = (("`events`", "the log, by seq"), ("`runs`", "state, failure, counts"),
              ("`launches`", "head, culprit"), ("`tasks` `attempts`", "the work"),
              ("`spool_cursors` `spool_drops`", ""))
    for i, (name, note) in enumerate(tables[:3]):
        s.text(1170, y0 + 30 + i * 24, name, size=13, anchor="start")
        s.text(1268, y0 + 30 + i * 24, note, size=13, anchor="start", colour=t.dim)
    s.text(1170, y0 + 102, tables[3][0], size=13, anchor="start")
    s.text(1170, y0 + 126, tables[4][0], size=13, anchor="start")

    s.line(30, ROW - 55, W - 30, ROW - 55, dashed=True, colour=t.muted)
    s.text(50, ROW - 66, "inside `ingest`, for each event of the batch, in order", size=14, anchor="start",
           colour=t.dim)

    # 1 -- skip, re-check --------------------------------------------------------------------------
    x = COL[0]
    s.page(x + 20, ROW + 8, 58, 74, fill="neutral", lines=3)
    s.text(x + 49, ROW + 104, "seen", size=13, colour=t.dim)
    s.cross(x + 49, ROW + 46, size=14)
    s.page(x + 128, ROW + 8, 58, 74, fill="surface", lines=3)
    s.magnifier(x + 184, ROW + 58, 17)
    s.text(x + 157, ROW + 104, "new", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "skip, re-check")
    lines(s, x, TXT + 30, ("an event ID already logged: skipped",
                           "the data is checked again",
                           "against the allow-list",
                           "another run or launch: nothing written"))
    counter(s, x, BIN, "invalid", "dropped, counted")

    # 2 -- one savepoint each ----------------------------------------------------------------------
    x = COL[1]
    for i in range(4):
        s.poly([(x + 10 + i * 40, ROW + 20), (x + 46 + i * 40, ROW + 20), (x + 46 + i * 40, ROW + 56),
                (x + 10 + i * 40, ROW + 56)], fill="docs", amount=0.4)
        s.text(x + 28 + i * 40, ROW + 44, str(i + 1), size=13)
    s.poly([(x + 172, ROW + 20), (x + 208, ROW + 20), (x + 208, ROW + 56), (x + 172, ROW + 56)],
           fill="surface", amount=0.4)
    s.text(x + 190, ROW + 44, "5", size=13)
    s.shade(x + 164, ROW + 10, 54, 56, fill="gate", opacity=0.35, colour=t.warn, dashed=True)
    s.arc(x + 262, ROW + 34, x + 222, ROW + 34, lift=-26)
    s.text(x + 252, ROW + 4, "new", size=12.5, colour=t.dim)
    s.arc(x + 200, ROW + 72, x + 236, ROW + 104, lift=-14, dashed=True, colour=t.accent)
    s.text(x + 100, ROW + 92, "its own savepoint", size=13, colour=t.dim)
    s.text(x + 244, ROW + 124, "or rolled back", size=12.5, colour=t.accent)
    s.step(x + CW / 2, TXT, 2, "one savepoint each")
    lines(s, x, TXT + 30, ("logged with the next `seq`",
                           "the first engine event starts the run",
                           "a projector error: that event only,",
                           "rolled back, with its traceback"))
    counter(s, x, BIN, "projection_error", "the cursor moves on")
    s.warning(x + 16, BIN + 64, size=9)
    s.text(x + 32, BIN + 68, "a storage fault: the batch rolls back,", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 32, BIN + 86, "the cursor stays", size=12.5, anchor="start", colour=t.dim)

    # 3 -- task and attempt ------------------------------------------------------------------------
    x = COL[2]
    stairs = (("pending", "input"), ("submitted", "input"), ("running", "work"), ("ended", "done"))
    for i, (name, fill) in enumerate(stairs):
        pill(s, x + 46 + i * 62, ROW + 92 - i * 24, name, fill, rx=38)
    s.arc(x + 214, ROW + 4, x + 46, ROW + 62, lift=-30, dashed=True, colour=t.muted)
    s.cross(x + 112, ROW + 6, size=9)
    s.text(x + 60, ROW + 8, "never back", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "task and attempt")
    lines(s, x, TXT + 30, ("task: process + tag, run-wide",
                           "no tag: process + task name",
                           "attempt: task, launch, attempt n",
                           "a task shows its last attempt"))
    s.text(x, BIN + 12, "`onTaskComplete` reads `trace.status`", size=13, anchor="start")
    s.text(x, BIN + 32, "COMPLETED, FAILED, ABORTED", size=12.5, anchor="start", colour=t.dim)
    s.text(x, BIN + 52, "failed and TERMINATE: `tool_error`", size=12.5, anchor="start", colour=t.dim)

    # 4 -- the launch ends -------------------------------------------------------------------------
    x = COL[3]
    pill(s, x + 44, ROW + 30, "queued", "neutral", rx=40)
    s.arrow(x + 86, ROW + 30, x + 112, ROW + 30)
    pill(s, x + 158, ROW + 30, "running", "work", rx=42)
    s.arrow(x + 190, ROW + 42, x + 214, ROW + 70)
    s.arrow(x + 150, ROW + 46, x + 120, ROW + 76)
    pill(s, x + 92, ROW + 92, "succeeded", "done", rx=52)
    pill(s, x + 226, ROW + 92, "failed", "problem", rx=40)
    s.step(x + CW / 2, TXT, 4, "the launch ends")
    lines(s, x, TXT + 30, ("`onFlowComplete` decides the end",
                           "open attempts become aborted",
                           "a terminal run never moves again:",
                           "a second end is only logged"))
    s.text(x, BIN + 12, "`runs.failure` when it failed:", size=13, anchor="start")
    s.text(x, BIN + 32, "`tool_error` and the launch's culprit,", size=12.5, anchor="start", colour=t.dim)
    s.text(x, BIN + 52, "or `engine_fault` when it has none", size=12.5, anchor="start", colour=t.dim)

    # 5 -- cursor, drops, summary -----------------------------------------------------------------
    x = COL[4]
    s.page(x + 14, ROW + 10, 66, 86, fill="surface", lines=4)
    s.poly([(x + 58, ROW + 10), (x + 72, ROW + 10), (x + 72, ROW + 46), (x + 65, ROW + 38), (x + 58, ROW + 46)],
           fill="input", amount=0.3)
    s.text(x + 47, ROW + 118, "cursor", size=12.5, colour=t.dim)
    s.bucket(x + 132, ROW + 48, 48, 42, fill="problem")
    s.text(x + 132, ROW + 118, "drops", size=12.5, colour=t.dim)
    for i, (hh, fill) in enumerate(((70, "bar_green"), (14, "problem"), (14, "neutral"))):
        s.poly([(x + 186 + i * 24, ROW + 96 - hh), (x + 204 + i * 24, ROW + 96 - hh),
                (x + 204 + i * 24, ROW + 96), (x + 186 + i * 24, ROW + 96)], fill=fill, amount=0.3)
    s.text(x + 222, ROW + 118, "counts", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "cursor, drops, summary")
    lines(s, x, TXT + 30, ("in the same transaction:",
                           "each file's offset stored",
                           "each drop count added",
                           "`task_counts` from the tasks"))
    s.text(x, BIN + 12, "`projected_seq` equals `last_seq`", size=13, anchor="start")
    s.text(x, BIN + 32, "the run is always current", size=12.5, anchor="start", colour=t.dim)
    s.text(x, BIN + 52, "with its log", size=12.5, anchor="start", colour=t.dim)

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 50, cx + CW + 23, ROW + 50)

    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)

    # the replayed fixture, to scale ----------------------------------------------------------------
    x0, px = 50, 2.4  # px per event
    s.text(x0, LOW, "replayed: the Nextflow 26.10.4 toolerr fixture, 3 reads of 100 lines", size=17,
           anchor="start", weight="bold")
    hooks = ((65, "bar_blue", "Pending 65"), (64, "bar_violet", "Submit 64"), (64, "bar_orange", "Start 64"),
             (64, "bar_green", "Complete 64"), (17, "bar_grey", "Publish 17"), (19, "neutral", "flow, process 19"))
    by = LOW + 30
    s.text(x0, by + 17, "293 events", size=14, anchor="start")
    bx = x0 + 100
    for n, fill, label in hooks:
        w = n * px
        s.poly([(bx, by), (bx + w, by), (bx + w, by + 24), (bx, by + 24)], fill=fill, amount=0.3, width=1.2)
        if n > 20:
            s.text(bx + w / 2, by + 44, label, size=12.5, colour=t.dim)
        bx += w
    s.text(bx + 10, by + 10, "Publish 17", size=12.5, anchor="start", colour=t.dim)
    s.text(bx + 10, by + 28, "flow, process 19", size=12.5, anchor="start", colour=t.dim)

    ly = by + 66
    s.text(x0, ly + 17, "295 log rows", size=14, anchor="start")
    s.poly([(x0 + 100, ly), (x0 + 100 + 293 * px, ly), (x0 + 100 + 293 * px, ly + 24), (x0 + 100, ly + 24)],
           fill="docs", amount=0.3, width=1.2)
    s.text(x0 + 100 + 293 * px / 2, ly + 17, "the 293 engine events, `seq` 1 to 295 with no gap", size=12.5)
    sx = x0 + 100 + 293 * px
    for i in range(2):
        s.poly([(sx + i * px * 4, ly), (sx + (i + 1) * px * 4, ly), (sx + (i + 1) * px * 4, ly + 24),
                (sx + i * px * 4, ly + 24)], fill="gate", amount=0.2, width=1.2)
    s.text(sx + 30, ly + 17, "+ 2 run state changes", size=12.5, anchor="start", colour=t.dim)

    ty = ly + 70
    s.text(x0, ty + 16, "65 tasks", size=14, anchor="start")
    cell, gap = 8, 2.6
    s.task_strip(x0 + 100, ty, ((63, "bar_green", "63 succeeded"), (1, "problem", ""), (1, "neutral", "")),
                 cell=cell, gap=gap, label_size=12.5)
    fx = x0 + 100 + 63 * (cell + gap) + 4 * gap + cell / 2  # the failed cell's centre
    ax = fx + cell + 5 * gap  # the aborted cell's centre
    s.arrow(fx - 14, ty + 62, fx - 2, ty + 28, colour=t.accent)
    s.text(fx - 16, ty + 78, "1 failed, COMPARE", size=12.5, anchor="end", colour=t.accent)
    s.arrow(ax + 18, ty + 62, ax + 2, ty + 28, colour=t.dim)
    s.text(ax + 12, ty + 78, "1 aborted, FINAL_REPORT", size=12.5, anchor="start", colour=t.dim)

    ry = ty + 112
    pill(s, x0 + 50, ry, "queued", "neutral", rx=40)
    s.arrow(x0 + 92, ry, x0 + 124, ry)
    pill(s, x0 + 170, ry, "running", "work", rx=42)
    s.arrow(x0 + 214, ry, x0 + 246, ry)
    pill(s, x0 + 288, ry, "failed", "problem", rx=38)
    s.text(x0 + 346, ry - 6, "`runs.failure`: `tool_error`, task COMPARE treatA_vs_ctrl, attempt 1",
           size=13, anchor="start")
    s.text(x0 + 346, ry + 15, "message: synthetic failure, tool exited with code 1 · no drops",
           size=12.5, anchor="start", colour=t.dim)

    # the culprit, CR-P3T04-08 --------------------------------------------------------------------
    cx0 = 1090
    s.text(cx0, LOW, "who is blamed when two fail", size=17, anchor="start", weight="bold")
    for i, tag in enumerate(("S01", "S02")):
        px0 = cx0 + 6 + i * 96
        s.page(px0, LOW + 40, 56, 70, fill="problem", lines=2)
        s.text(px0 + 28, LOW + 32, f"seq {i + 1}", size=12.5, colour=t.dim)
        s.text(px0 + 28, LOW + 130, f"ALIGN {tag}", size=12.5)
        s.text(px0 + 28, LOW + 148, "`tool_error`", size=12.5, colour=t.dim)
    s.arc(cx0 + 206, LOW + 148, cx0 + 34, LOW + 158, lift=-18, colour=t.accent)
    s.text(cx0 + 214, LOW + 42, "both failed, TERMINATE,", size=13, anchor="start")
    s.text(cx0 + 214, LOW + 62, "in one batch: each keeps", size=13, anchor="start", colour=t.dim)
    s.text(cx0 + 214, LOW + 82, "its own class", size=13, anchor="start", colour=t.dim)
    s.text(cx0 + 214, LOW + 112, "`launches.culprit_attempt_id`", size=13, anchor="start")
    s.text(cx0 + 214, LOW + 132, "set only while empty, so the", size=13, anchor="start", colour=t.dim)
    s.text(cx0 + 214, LOW + 152, "first in `seq` order is blamed", size=13, anchor="start", colour=t.dim)
    s.text(cx0 + 214, LOW + 176, "fixed by CR-P3T04-08", size=12.5, anchor="start", colour=t.dim)

    # the head reports -----------------------------------------------------------------------------
    hy = LOW + 212
    s.runner(cx0, hy, 92, 44)
    s.text(cx0 + 110, hy + 16, "head reports", size=17, anchor="start", weight="bold")
    s.text(cx0 + 110, hy + 38, "`apply_head_report`", size=13, anchor="start", colour=t.dim)
    rules = (("`running`: starts a queued run", True),
             ("a launch or head failure fails the run;", True),
             ("`head_lost`, `engine_fault`: open attempts failed", False),
             ("ended while cancelling: `cancelled`", True),
             ("after the engine's end: no state change", True))
    for i, (rule, first) in enumerate(rules):
        s.text(cx0 + (0 if first else 16), hy + 70 + i * 20, rule, size=13, anchor="start",
               colour=t.ink if first else t.dim)

    s.prefix_key(50, H - 40, ("CR",))
    s.text(W - 50, H - 16, "source: spectio_server/projector ingest.py, nextflow.py, runs.py · store/writer.py · "
           "tests/fixtures/engine-events, replayed 2026-10-30 · P1 Task 4", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t04-projector")
