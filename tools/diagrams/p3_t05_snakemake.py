#!/usr/bin/env python3
"""The Snakemake mapping: step P3, P1 Task 5, 2026-10-30.

Writes docs/assets/diagrams/p3-t05-snakemake_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t05 at 0f9fcf9 (BASE 85bc086):
- packages/spectio-server/src/spectio_server/projector/snakemake.py: project(p, data):
  workflow_started: p.set_started() and pin_engine_version(snakemake_version); progress:
  runs.tasks_expected = total; then, once the run is terminal, a job event is logged only;
  job_info: task = rule + wildcards as sorted `k=v` joined by ", " (no wildcard: no tag), the
  jobid's task upserted in snakemake_jobs (launch_id, jobid), a `running` attempt opened when the
  task has none or its last one failed (n = last.n + 1); job_finished: succeeded, job_error:
  failed and launches.culprit_attempt_id = that attempt ("the launch's last failed job"); an
  unknown jobid or an attempt already ended: logged, no change; job_started is not handled
  (logged only). drives(p): the run's workflow engine is "snakemake". head_exit(p, exit_code):
  a terminal run does not move; p.event_time = engine_time of the run's last event that has one
  (None: the ingest clock); move running, end_launch() (open attempts aborted); 0 succeeded,
  else failed with _failure: the last spectio.engine.snakemake.error record's msg, else
  "snakemake exited with code N"; tool_error with the culprit's task_id and n when the
  culprit's task is still failed, else engine_fault.
- projector/ingest.py: an event whose type is not nextflow.* goes to snakemake.project;
  apply_head_report: cancelling + ended: cancelled; else ended + exit_code known + (no failure,
  or a head_lost / engine_fault failure) + drives(): snakemake.head_exit (CR-P3T05-01); a
  launch error such as engine_missing still fails the run.
- projector/runs.py: move() takes started_at / ended_at from event_time or the clock;
  set_started() replaces started_at only when launch_n == 1 (CR-P3T05-02).
- spectio_sdk/events.py: SnakemakeJobInfo._cut_params_detail cuts `reason` after "Params have
  changed since last execution" (CR-P3T05-03, SEC-P3T1-08); _drop_slurm_extra drops
  resources.slurm_extra (SEC-P3T1-11; snakemake-executor-plugin-slurm 2.8.0 submit_string.py
  :206-207, as cited in docs/reviews/code/P3-t05.md).
- store/schema.py and migrations/versions/0003_snakemake_jobs.py: snakemake_jobs.
- The numbers at the bottom: tests/fixtures/engine-events/snakemake-9.27.1_checkpoint_flaky_retry
  and _tool_error .spool.jsonl, read with read_spool(max_lines=100) and ingested through the
  Writer as test_projector_snakemake.py replay() does, then a head report with exit 0 and 1
  (run 2026-10-30):
  flaky: 5 reads, 469 events, no drops: log 122, job_info 69, shellcmd 69, job_finished 67,
  progress 67, job_started 66, error 2, job_error 2, resources_info 2, rulegraph 1, run_info 1,
  workflow_started 1; 67 tasks succeeded, tasks_expected 67, 69 attempts, the two failed ones
  attempt 1 of align "i=0000, sample=S07" and "i=0001, sample=S07"; exit 0: succeeded, failure
  None, engine_version 9.27.1.
  tool_error: 5 reads, 460 events, no drops: log 122, job_info 67, shellcmd 67, job_finished 64,
  job_started 64, progress 64, error 4, job_error 3, resources_info 2, rulegraph 1, run_info 1,
  workflow_started 1; 65 tasks, 64 succeeded and 1 failed, tasks_expected 67; compare
  "group=treatA" attempts 1, 2, 3 failed, attempt 3 failure_class tool_error; exit 1: failed,
  class tool_error, attempt_n 3, message "WorkflowError: At least one job did not complete
  successfully."
- Fixed during review and named in the figure: CR-P3T05-01, -02, -03 (majors) and SEC-P3T1-11,
  from docs/reviews/code/P3-t05.md. The items left open are listed without finding IDs, since
  the IDs are reused across rounds in the review rounds; the snakemake.error msg leak (tracebacks
  and Snakefile source lines reach runs.failure.message, api 14.1) is named by its follow-up,
  FU-P3-05.
"""

from __future__ import annotations

import math

from sketch import Sketch, Theme, main_for

W, H = 1600, 1350
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 410  # the pictograms of the steps
TXT = ROW + 150  # the captions
BIN = TXT + 128  # the notes under the captions
LOW = 800  # the replayed fixtures and the side panel


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, colour: str | None = None) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=12.5, anchor="start", colour=colour or s.t.dim)


def pill(s: Sketch, cx: float, cy: float, label: str, fill: str, rx: float = 44) -> None:
    s.ellipse(cx, cy, rx, 14, fill=fill)
    s.text(cx, cy + 5, label, size=13)


def cell(s: Sketch, x: float, y: float, fill: str, *, w: float = 8, h: float = 20,
         dashed: bool = False) -> None:
    """One task or attempt, to scale."""
    dash = ' stroke-dasharray="2 2"' if dashed else ""
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" '
          f'fill="{s.t.fill(fill)}" stroke="{s.t.ink}" stroke-width="0.8"{dash}/>')


def attempts(s: Sketch, x: float, y: float, states: tuple[str, ...], *, w: float = 26) -> float:
    """A task's attempts in a row, numbered; returns the right edge."""
    for i, fill in enumerate(states):
        cx = x + i * (w + 6)
        s.poly([(cx, y), (cx + w, y), (cx + w, y + 24), (cx, y + 24)], fill=fill, amount=0.3, width=1.2)
        s.text(cx + w / 2, y + 17, str(i + 1), size=12.5)
    return x + len(states) * (w + 6) - 6


def clock(s: Sketch, cx: float, cy: float, r: float) -> None:
    s.circle(cx, cy, r, fill="surface")
    for k in range(12):
        a = math.pi * 2 * k / 12
        s.line(cx + r * 0.82 * math.cos(a), cy + r * 0.82 * math.sin(a),
               cx + r * 0.94 * math.cos(a), cy + r * 0.94 * math.sin(a), width=1.1, amount=0.1, passes=1)
    s.line(cx, cy, cx, cy - r * 0.62, width=2, amount=0.2, passes=1)
    s.line(cx, cy, cx + r * 0.45, cy + r * 0.18, width=2, amount=0.2, passes=1)
    s.dot(cx, cy, 3)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=75)
    t = theme
    s.heading(50, 58, "P3 Task 5 · Snakemake events become tasks and attempts, the head's exit ends the launch",
              "`spectio_server.projector.snakemake`, api 7.2 and 14.1, P1 Assumption 16 · Snakemake 9.27.1 · "
              "no engine event ends a Snakemake launch")

    # where the calls come from ------------------------------------------------------------------
    y0 = 128
    s.hpc_node(60, y0, 56, 74, busy=3)
    s.text(136, y0 + 18, "Snakemake head", size=15, anchor="start", weight="bold")
    s.text(136, y0 + 40, "the logger plugin", size=13.5, anchor="start", colour=t.dim)
    s.text(136, y0 + 60, "`snakemake-logger-spectio`", size=13, anchor="start")
    s.arrow(330, y0 + 34, 404, y0 + 34)
    for i in range(3):
        s.page(418 + i * 14, y0 + 6 + i * 8, 40, 52, fill="input", lines=3)
    s.text(500, y0 + 22, "`snakemake.*` spool events", size=13.5, anchor="start")
    s.text(500, y0 + 44, "`ingest` sends every event that is", size=13.5, anchor="start", colour=t.dim)
    s.text(500, y0 + 64, "not `nextflow.*` to `snakemake.project`", size=13.5, anchor="start", colour=t.dim)

    s.terminal(60, y0 + 108, 196, 74, ("$ snakemake ...", "exit 1"), size=12.5)
    s.arrow(266, y0 + 146, 316, y0 + 146)
    s.runner(326, y0 + 120, 100, 48)
    s.text(446, y0 + 132, "`apply_head_report`, exit code known", size=13.5, anchor="start")
    s.text(446, y0 + 154, "and the run's workflow is Snakemake:", size=13.5, anchor="start", colour=t.dim)
    s.text(446, y0 + 174, "`snakemake.head_exit`", size=13.5, anchor="start")

    s.arrow(820, y0 + 40, 900, y0 + 78)
    s.arrow(760, y0 + 146, 900, y0 + 104)
    s.cog(938, y0 + 92, 22, fill="work")
    s.text(976, y0 + 80, "the projector", size=15, anchor="start", weight="bold")
    s.text(976, y0 + 102, "on the one writer,", size=13.5, anchor="start", colour=t.dim)
    s.text(976, y0 + 122, "one transaction per call", size=13.5, anchor="start", colour=t.dim)
    s.arrow(1160, y0 + 92, 1220, y0 + 92)
    s.bucket(1262, y0 + 56, 70, 66, fill="neutral")
    s.text(1262, y0 + 100, "store", size=13, colour=t.dim)
    s.text(1316, y0 + 40, "`runs` `tasks` `attempts`", size=13, anchor="start")
    s.text(1316, y0 + 64, "`launches`, the culprit", size=13, anchor="start")
    s.text(1316, y0 + 92, "`snakemake_jobs`, new:", size=13, anchor="start")
    s.text(1316, y0 + 112, "launch + jobid, its task", size=13, anchor="start", colour=t.dim)
    s.text(1316, y0 + 132, "migration 0003", size=13, anchor="start", colour=t.dim)

    s.line(30, ROW - 60, W - 30, ROW - 60, dashed=True, colour=t.muted)
    s.text(50, ROW - 71, "one launch, from start to exit", size=14, anchor="start", colour=t.dim)

    # 1 -- the workflow starts ---------------------------------------------------------------------
    x = COL[0]
    clock(s, x + 48, ROW + 46, 34)
    s.text(x + 48, ROW + 108, "engine time", size=12.5, colour=t.dim)
    s.text(x + 104, ROW + 18, "`progress` total", size=12.5, anchor="start", colour=t.dim)
    s.poly([(x + 104, ROW + 30), (x + 264, ROW + 30), (x + 264, ROW + 52), (x + 104, ROW + 52)],
           fill="surface", amount=0.3, width=1.2)
    s.poly([(x + 104, ROW + 30), (x + 210, ROW + 30), (x + 210, ROW + 52), (x + 104, ROW + 52)],
           fill="bar_violet", amount=0.3, width=1.2)
    s.text(x + 104, ROW + 76, "grows past each checkpoint", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "the workflow starts")
    lines(s, x, TXT + 30, ("`workflow_started`: the run's start",
                           "is its engine time, not the clock",
                           "`engine_version` pinned, 9.27.1",
                           "`progress`: `tasks_expected`"))
    note(s, x, BIN + 12, ("only launch 1 sets the start:",
                          "a Continue keeps it · CR-P3T05-02"))

    # 2 -- a job runs --------------------------------------------------------------------------------
    x = COL[1]
    s.page(x + 8, ROW + 8, 62, 80, fill="input", lines=3)
    s.text(x + 39, ROW + 108, "`job_info`", size=12.5, colour=t.dim)
    s.arrow(x + 80, ROW + 40, x + 124, ROW + 40)
    pill(s, x + 184, ROW + 40, "running", "work", rx=50)
    s.text(x + 184, ROW + 76, "attempt 1 opened", size=12.5, colour=t.dim)
    s.text(x + 184, ROW + 98, "`align` `i=0001, sample=S07`", size=12)
    s.step(x + CW / 2, TXT, 2, "a job runs")
    lines(s, x, TXT + 30, ("`job_info` opens a running attempt",
                           "task: rule + its wildcards, sorted",
                           "`job_started` is logged only:",
                           "Snakemake reports no separate submit"))
    note(s, x, BIN + 12, ("`snakemake_jobs` keeps each jobid's task,",
                          "the job ends carry the jobid only"))

    # 3 -- a job ends ----------------------------------------------------------------------------
    x = COL[2]
    s.text(x + 6, ROW + 2, "same jobid 7, no attempt number", size=12.5, anchor="start", colour=t.dim)
    right = attempts(s, x + 30, ROW + 34, ("problem", "done"), w=46)
    s.text(x + 53, ROW + 80, "`job_error`", size=12.5)
    s.text(x + 105, ROW + 98, "`job_finished`", size=12.5)
    s.arc(x + 76, ROW + 32, x + 104, ROW + 32, lift=-14, width=1.2)
    s.text(right + 22, ROW + 46, "retried:", size=12.5, anchor="start", colour=t.dim)
    s.text(right + 22, ROW + 64, "attempt n + 1", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "a job ends")
    lines(s, x, TXT + 30, ("`job_finished`: succeeded",
                           "`job_error`: failed, and that attempt",
                           "becomes the launch's culprit,",
                           "the last failed job wins"))
    note(s, x, BIN + 12, ("an unknown jobid, or a job already ended:",
                          "logged, no change"))

    # 4 -- the head exits ------------------------------------------------------------------------
    x = COL[3]
    s.terminal(x + 6, ROW + 4, 150, 82, ("$ snakemake", "exit 0 or 1"), size=12.5)
    s.arrow(x + 164, ROW + 44, x + 190, ROW + 22)
    s.arrow(x + 164, ROW + 50, x + 190, ROW + 78)
    pill(s, x + 236, ROW + 18, "succeeded", "done", rx=48)
    pill(s, x + 236, ROW + 82, "failed", "problem", rx=40)
    s.text(x + 236, ROW + 50, "0", size=13, colour=t.dim)
    s.text(x + 236, ROW + 116, "anything else", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "the head exits")
    lines(s, x, TXT + 30, ("its exit code ends the launch",
                           "open attempts become aborted",
                           "`ended_at`: the run's last engine time",
                           "a terminal run never moves again"))
    note(s, x, BIN + 12, ("the exit code wins over a runner's",
                          "`head_lost` or `engine_fault` · CR-P3T05-01"))

    # 5 -- who is blamed -------------------------------------------------------------------------
    x = COL[4]
    s.text(x + 4, ROW + 16, "the launch's last failed job", size=12.5, anchor="start", colour=t.dim)
    end = attempts(s, x + 4, ROW + 30, ("problem", "problem", "problem"))
    s.arc(end + 8, ROW + 42, end + 40, ROW + 42, lift=-10, width=1.2, colour=t.accent)
    s.text(end + 46, ROW + 47, "`tool_error`", size=13, anchor="start", colour=t.accent)
    end = attempts(s, x + 4, ROW + 76, ("problem", "done"))
    s.arc(end + 8, ROW + 88, end + 72, ROW + 88, lift=-10, width=1.2)
    s.text(end + 78, ROW + 93, "`engine_fault`", size=13, anchor="start")
    s.text(x + 4, ROW + 124, "its task still failed, or retried and ran", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "who is blamed")
    lines(s, x, TXT + 30, ("on a non-zero exit only",
                           "task still failed: `tool_error`,",
                           "that attempt is named",
                           "else `engine_fault`, no task"))
    note(s, x, BIN + 12, ("message: the last `error` record,",
                          "else `snakemake exited with code N`"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 50, cx + CW + 23, ROW + 50)

    s.line(30, LOW - 46, W - 30, LOW - 46, dashed=True, colour=t.muted)

    # the replayed fixtures, to scale --------------------------------------------------------------
    x0, px = 50, 1.6  # px per event
    cw, cg = 8, 2.6  # task cell and gap
    s.text(x0, LOW, "replayed: two Snakemake 9.27.1 fixtures, read 100 lines at a time, then the head's exit",
           size=17, anchor="start", weight="bold")

    def fixture(y: float, title: str, segs: tuple[tuple[int, str, str], ...], small: str) -> None:
        s.text(x0, y, title, size=14, anchor="start")
        bx, by = x0, y + 14
        for n, fill, label in segs:
            w = n * px
            s.poly([(bx, by), (bx + w, by), (bx + w, by + 24), (bx, by + 24)], fill=fill, amount=0.3, width=1.2)
            if label:
                s.text(bx + w / 2, by + 42, label, size=12.5, colour=t.dim)
            bx += w
        s.text(bx + 10, by + 17, small, size=12.5, anchor="start", colour=t.dim)

    # the event kinds, in bar order: logged only, job_info, job_finished, progress, then the small ones
    fy = LOW + 40
    fixture(fy, "`checkpoint_flaky_retry`, 469 events, no drops",
            ((261, "neutral", "logged only 261"), (69, "bar_blue", "job_info 69"),
             (67, "bar_green", "finished 67"), (67, "bar_violet", "progress 67"),
             (2, "problem", ""), (2, "bar_orange", ""), (1, "gate", "")),
            "job_error 2, error 2, start 1")
    ty = fy + 84
    for i in range(67):
        cell(s, x0 + i * (cw + cg), ty, "bar_green")
    for i in (65, 66):  # the two retried tasks: attempt 1 failed, under the task
        cell(s, x0 + i * (cw + cg), ty + 24, "problem", h=12)
    rx = x0 + 67 * (cw + cg)
    s.text(rx + 8, ty + 15, "67 tasks succeeded, 69 attempts", size=12.5, anchor="start")
    s.text(rx + 8, ty + 34, "2 tasks of `align` S07 failed once, then ran", size=12.5, anchor="start",
           colour=t.dim)
    oy = ty + 70
    s.text(x0, oy + 5, "head exit 0", size=13.5, anchor="start")
    s.arrow(x0 + 92, oy, x0 + 124, oy)
    pill(s, x0 + 176, oy, "succeeded", "done", rx=50)
    s.text(x0 + 240, oy + 5, "2 `error` records arrived, the exit code decides",
           size=12.5, anchor="start", colour=t.dim)

    fy = oy + 46
    fixture(fy, "`tool_error`, 460 events, no drops",
            ((257, "neutral", "logged only 257"), (67, "bar_blue", "job_info 67"),
             (64, "bar_green", "finished 64"), (64, "bar_violet", "progress 64"),
             (3, "problem", ""), (4, "bar_orange", ""), (1, "gate", "")),
            "job_error 3, error 4, start 1")
    ty = fy + 84
    for i in range(64):
        cell(s, x0 + i * (cw + cg), ty, "bar_green")
    fx = x0 + 64 * (cw + cg)
    cell(s, fx, ty, "problem")
    for k in (1, 2):  # attempts 1 and 2 of the failed task, under it
        cell(s, fx, ty + 10 + k * 14, "problem", h=12)
    for k in (1, 2):  # tasks_expected 67: two never ran
        cell(s, fx + k * (cw + cg), ty, "surface", dashed=True)
    rx = fx + 3 * (cw + cg)
    s.text(rx + 8, ty + 15, "65 tasks of 67 expected: 64 succeeded,", size=12.5, anchor="start")
    s.text(rx + 8, ty + 34, "`compare` group=treatA failed 3 times, 2 never ran", size=12.5,
           anchor="start", colour=t.dim)
    oy = ty + 76
    s.text(x0, oy + 5, "head exit 1", size=13.5, anchor="start")
    s.arrow(x0 + 92, oy, x0 + 124, oy)
    pill(s, x0 + 166, oy, "failed", "problem", rx=40)
    s.text(x0 + 220, oy - 3, "`tool_error`, task `compare` group=treatA, attempt 3", size=13, anchor="start")
    s.text(x0 + 220, oy + 17, "message: WorkflowError, At least one job did not complete successfully",
           size=12.5, anchor="start", colour=t.dim)

    # never stored --------------------------------------------------------------------------------------
    px0 = 1110
    s.line(px0 - 24, LOW - 18, px0 - 24, H - 70, dashed=True, colour=t.muted)
    s.text(px0, LOW, "kept out of the store", size=17, anchor="start", weight="bold")
    s.page(px0, LOW + 22, 44, 56, fill="surface", lines=3)
    s.lock(px0 + 40, LOW + 74, size=12)
    s.text(px0 + 64, LOW + 36, "parsed before the projector, so", size=13, anchor="start", colour=t.dim)
    s.text(px0 + 64, LOW + 56, "free text and raw flags never land", size=13, anchor="start", colour=t.dim)
    items = (
        ("`resources`: `slurm_extra` dropped", "raw `sbatch` flags, plugin-slurm 2.8.0",
         "SEC-P3T1-11"),
        ("`reason`: cut after the label", "Params have changed since last execution,",
         "its detail quoted a shell command · CR-P3T05-03"),
        ("`error` `msg`: only a quoted `Command` hidden", "tracebacks and Snakefile source lines",
         "still stored, a known leak · FU-P3-05"),
        ("`msg` of `log`, `shellcmd`, `job_error`", "not in the allow-list, dropped at parse", ""),
    )
    iy = LOW + 112
    for head, sub, extra in items:
        s.cross(px0 + 8, iy - 4, size=7, colour=t.accent)
        s.text(px0 + 24, iy, head, size=13, anchor="start")
        s.text(px0 + 24, iy + 20, sub, size=12.5, anchor="start", colour=t.dim)
        if extra:
            s.text(px0 + 24, iy + 40, extra, size=12.5, anchor="start", colour=t.dim)
        iy += 72 if extra else 56

    iy += 8
    s.warning(px0 + 8, iy - 4, size=9)
    s.text(px0 + 24, iy, "left open, in the review record:", size=13, anchor="start")
    note(s, px0 + 24, iy + 22, ("`error` `msg` leak, first-line cut: FU-P3-05",
                                "spool times trusted within 1970 to 9999",
                                "routed by type prefix, not the run's engine",
                                "`head_exit` reads the run's events,",
                                "not only the launch's"))

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: spectio_server/projector/snakemake.py, ingest.py, runs.py · spectio_sdk/events.py · "
           "tests/fixtures/engine-events, replayed 2026-10-30 · P1 Task 5", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t05-snakemake")
