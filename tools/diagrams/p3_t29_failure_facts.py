#!/usr/bin/env python3
"""A failure's scheduler facts: step P3, P1 Task 29, 2026-11-01.

Writes docs/assets/diagrams/p3-t29-failure-facts_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t29 at 598522f:
- packages/spectio-server/src/spectio_server/failure.py: build_failures(limit=10), ordered by
  attempts.created_at then id, `failures_total` the count; LOG_TAIL_LINES 20 of `.command.log`,
  else `.command.err` (Snakemake: slurm_log, else rule_log), read in the file pool, a Stalled
  pool leaves the tails null; on Nextflow `want(run, (native_id, work_dir))`; on Snakemake the
  state comes from parse_smk_slurm_message (state_source "engine_message", the text never
  kept) and task_resources asks sacct, with `run_paths(...).launch_dir`, only for ended jobs
  that have no benchmark measure; `want` returns at once, `status` gives available, pending or
  unavailable; Accounting.step: a failed call goes to _failed; `_answers` keeps a row only in a
  TERMINAL state and with WorkDir equal to the expected directory after normpath; otherwise no
  row, asked again on the next view, up to MAX_TRIES 3, then None kept; `_tries` keyed by
  (run, job) and popped once final (CR-P3T29-04 of round 2); rows and None saved to
  `<run dir>/.spectio/sacct.json` (written by a rename, 0600, read back with no link followed,
  MAX_CACHE_BYTES 8 MiB); `load` catches RecursionError and reads the file as empty
  (SEC-P3T29-02 of round 2); _scheduler: usage_source "trace" while sacct has not answered;
- packages/spectio/src/spectio/runner/sacct.py: sacct_argv `--parsable2 --noheader -j <ids>
  --user=<euid> --format=JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit,WorkDir`
  (SEC-P3T29-01 of round 2); TIMEOUT_S 10, INTERVAL_S 60, BATCH 100, MAX_OUTPUT 1048576;
  sacct_env PATH and SLURM_TIME_FORMAT only; parse_sacct `split("|", 8)`, so a `|` in WorkDir
  is kept; SacctLimiter: one call in flight;
- the terminal lines and the bars are the fake sacct and the assertions of
  packages/spectio-server/tests/api/test_failure.py: test_nf_failure_summary (job 8812402,
  exit 137, trace memory 2147483648; the fake answers
  `8812402|OUT_OF_MEMORY|0:125|None|0|00:01:05|2G|00:10:00|<dir>` and
  `8812402.batch|...|2097152K|...`, giving req_mem 2 GiB, max_rss 2 GiB, time_limit 600 s,
  elapsed 65 s), test_sacct_other_workdir_not_kept (8812401, WorkDir /elsewhere),
  test_sacct_lag_asked_again (lag "-" and "RUNNING"), test_sacct_lag_capped (3 calls, then
  null), test_cache_file_too_deep; slurm-mini (P1 Task 22) is not built, so these are a fake's
  numbers, not a cluster's;
- `uv run --locked pytest -q packages/spectio-server/tests/api/test_failure.py
  packages/spectio/tests/test_sacct.py`: all pass (run 2026-11-01; no count, so that the figure
  does not go stale);
- the open items are round 3 of docs/reviews/code/P3-t29.md (both verdicts approve); the
  [to be validated] items are the sacct.py module docstring. Finding IDs restart per round, so
  each pin names its round.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1250
TOP = 122  # band 1: a request
CAP1 = 362  # its captions
DIV = 452  # the server's sacct thread starts here
ROW = 482  # band 2: the call and the check
CAP2 = 772  # its captions
PIN = 868  # the fixed findings, under what they fixed
LOW = 984  # band 3: what the failure shows, the tests, what is open


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start") -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...], *, fixed: bool = True) -> None:
    """A finding pinned where it hits: a tick when the branch fixed it, a warning when it is open."""
    if fixed:
        s.tick(x + 8, y - 5, size=7)
    else:
        s.warning(x + 8, y - 5, size=8)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=29)
    t = theme
    s.heading(50, 58, "P3 Task 29 · a failure's scheduler facts, asked of sacct and checked",
              "`spectio_server.failure`, `spectio.runner.sacct` · api 5 note 2026-11-01, architecture "
              "13.7, dev-env 15.3 req. 15 · no request ever waits for sacct")

    # 1 -- someone opens the run ----------------------------------------------------------------
    s.browser(50, TOP, 340, 196, url="`GET /api/v1/runs/run_id`")
    s.text(68, TOP + 56, "failures", size=15, anchor="start", weight="bold")
    s.shade(66, TOP + 70, 308, 110, fill="problem", opacity=0.55)
    s.text(80, TOP + 94, "`ALIGN` · S00 · attempt 2", size=13.5, anchor="start")
    s.text(80, TOP + 116, "exit 137 · job `8812402`", size=13.5, anchor="start")
    s.text(80, TOP + 138, "log tail: the last 20 lines", size=13, anchor="start", colour=t.dim)
    s.hourglass(88, TOP + 160, size=7)
    s.text(102, TOP + 165, "`accounting` pending", size=13, anchor="start", colour=t.dim)
    s.step(220, CAP1, 1, "a failure is opened")
    lines(s, 50, CAP1 + 30, ("up to 10 failed jobs, by when",
                             "their last attempt was created"))

    s.arrow(398, TOP + 98, 440, TOP + 98)

    # 2 -- what is already on hand --------------------------------------------------------------
    x = 452
    s.page(x, TOP + 4, 40, 50, fill="input", lines=3)
    s.text(x + 58, TOP + 20, "the engine's events, stored", size=14, anchor="start")
    s.text(x + 58, TOP + 40, "Nextflow trace: exit, `memory`, `time`, `peak_rss`",
           size=13, anchor="start", colour=t.dim)
    s.folder(x - 4, TOP + 78, 48, 40, fill="input")
    s.page(x + 14, TOP + 92, 20, 24, fill="surface", lines=0)
    s.text(x + 58, TOP + 94, "the job's files, in the file pool", size=14, anchor="start")
    s.text(x + 58, TOP + 114, "`.command.log`, else `.command.err`",
           size=13, anchor="start", colour=t.dim)
    s.envelope(x - 2, TOP + 150, 46, 32, fill="docs")
    s.text(x + 58, TOP + 164, "Snakemake: the SLURM plugin's error text", size=14, anchor="start")
    s.text(x + 58, TOP + 184, "state and reason parsed, the text never kept",
           size=13, anchor="start", colour=t.dim)
    s.step(705, CAP1, 2, "the facts already on hand")
    lines(s, x, CAP1 + 30, ("shown at once: `usage_source` trace,",
                            "Snakemake `state_source` engine_message"))

    s.arrow(962, TOP + 98, 1004, TOP + 98)

    # 3 -- the job is queued --------------------------------------------------------------------
    x = 1016
    for i, (job, where, fill) in enumerate((("`8812402`", "the attempt's `work_dir`", "input"),
                                            ("Snakemake job", "the run's `launch_dir`", "docs"))):
        y = TOP + 10 + i * 62
        s.poly([(x, y), (x + 250, y), (x + 250, y + 48), (x, y + 48)], fill=fill, amount=0.5)
        s.text(x + 12, y + 20, job, size=13.5, anchor="start")
        s.text(x + 12, y + 40, f"with {where}", size=12.5, anchor="start", colour=t.dim)
    s.arrow(x + 262, TOP + 66, x + 300, TOP + 66, dashed=True, colour=t.dim)
    s.cog(x + 336, TOP + 64, 18, fill="work")
    s.text(x + 374, TOP + 58, "the server's", size=13.5, anchor="start")
    s.text(x + 374, TOP + 78, "one `Accounting`", size=13.5, anchor="start")
    s.text(x + 12, TOP + 158, "`want(run, pairs of job ID and directory)`", size=13, anchor="start")
    s.text(x + 12, TOP + 180, "returns at once, before any call", size=13, anchor="start", colour=t.dim)
    s.step(1280, CAP1, 3, "the job is queued, nobody waits")
    lines(s, x, CAP1 + 30, ("Nextflow: a failure, when it is viewed",
                            "Snakemake: ended jobs with no benchmark file"))

    s.line(30, DIV, W - 30, DIV, dashed=True, colour=t.muted)
    s.text(1196, DIV + 24, "on the sacct thread of its own, never the writer's or a request's",
           size=14, anchor="end", colour=t.dim)  # under the divider: the middle row's heading

    # 4 -- one paced call -----------------------------------------------------------------------
    s.hourglass(64, ROW + 12, size=9)
    s.text(84, ROW + 18, "one call in flight, the next one 60 s later", size=14, anchor="start")
    s.text(84, ROW + 40, "up to 100 job IDs per call, killed after 10 s", size=13.5, anchor="start",
           colour=t.dim)
    s.terminal(50, ROW + 58, 610, 196, (
        "$ sacct --parsable2 --noheader -j 8812402 \\",
        "    --user=EUID \\",
        "    --format=JobID,State,ExitCode,Reason,MaxRSS,",
        "             Elapsed,ReqMem,Timelimit,WorkDir",
        "8812402|OUT_OF_MEMORY|0:125|None|0|00:01:05|2G|00:10:00|DIR",
        "8812402.batch|OUT_OF_MEMORY|0:125||2097152K|00:01:05|||DIR",
    ), size=12.5, line_h=24)
    s.step(355, CAP2, 4, "one paced sacct call")
    lines(s, 50, CAP2 + 30, ("only the server user's jobs, its own uid",
                             "WorkDir last, so a bar inside it is kept"))

    s.arrow(670, ROW + 156, 704, ROW + 156)

    # 5 -- the row is checked -------------------------------------------------------------------
    x = 716
    rows = (("`8812402` OUT_OF_MEMORY", "WorkDir is the attempt's work dir", "done", True),
            ("`8812401` same number", "WorkDir `/elsewhere`, a PID or another job", "problem", False),
            ("`RUNNING`, or no row yet", "slurmdbd records a job after it ends", "neutral", False))
    for i, (head, sub, fill, ok) in enumerate(rows):
        y = ROW + 36 + i * 76
        s.poly([(x, y), (x + 300, y), (x + 300, y + 56), (x, y + 56)], fill=fill, amount=0.5)
        s.text(x + 12, y + 23, head, size=13.5, anchor="start")
        s.text(x + 12, y + 44, sub, size=12.5, anchor="start", colour=t.dim)
        s.arrow(x + 306, y + 28, x + 344, ROW + 130 + (i - 1) * 14, colour=t.dim)

    gx, gtop = 1110, ROW + 96  # the sieve: an ended state, from the expected directory
    s.poly([(gx - 48, gtop), (gx + 48, gtop), (gx + 14, gtop + 66), (gx - 14, gtop + 66)],
           fill="gate", amount=0.8)
    for dx, dy in ((-22, 14), (0, 14), (22, 14), (-10, 34), (10, 34)):
        s.dot(gx + dx, gtop + dy, 2.4, colour=t.dim)
    s.text(gx - 6, gtop - 46, "an ended state", size=13.5)
    s.text(gx - 6, gtop - 26, "from that directory", size=13.5)

    kx = 1206  # kept
    s.arrow(gx + 50, gtop + 2, kx - 8, ROW + 46)
    s.tick(kx + 8, ROW + 34, size=9)
    s.folder(kx + 30, ROW + 4, 150, 66, fill="done", label="`sacct.json`")
    s.lock(kx + 170, ROW + 66, size=11)
    s.text(kx + 194, ROW + 26, "kept in memory", size=13.5, anchor="start")
    s.text(kx + 194, ROW + 46, "and in `.spectio`", size=13.5, anchor="start")
    s.text(kx + 30, ROW + 96, "`accounting` available, `state_source` sacct", size=13, anchor="start")
    s.text(kx + 30, ROW + 116, "never asked again, after a restart too", size=13, anchor="start",
           colour=t.dim)

    s.arrow(gx + 10, gtop + 72, kx - 8, ROW + 210)  # not kept
    s.cross(kx + 8, ROW + 206, size=9)
    s.text(kx + 30, ROW + 186, "counted as no row:", size=13.5, anchor="start")
    s.text(kx + 30, ROW + 206, "the next view asks again", size=13.5, anchor="start", colour=t.dim)
    for n in range(3):
        cx = kx + 46 + n * 52
        s.circle(cx, ROW + 246, 16, fill="neutral")
        s.text(cx, ROW + 251, str(n + 1), size=14)
        if n < 2:
            s.arrow(cx + 18, ROW + 246, cx + 33, ROW + 246, colour=t.dim)
    s.arrow(kx + 168, ROW + 246, kx + 198, ROW + 246)
    s.text(kx + 206, ROW + 242, "3 calls, then null", size=13.5, anchor="start")
    s.text(kx + 206, ROW + 262, "kept: unavailable", size=13.5, anchor="start", colour=t.dim)

    s.step(1110, CAP2, 5, "only an ended row from the right directory is kept")
    lines(s, 1110, CAP2 + 30, ("a failed call is not asked again by this server process",),
          anchor="middle")

    # the findings this branch fixed, under what they fixed ---------------------------------------
    pin(s, 50, PIN, "R2 SEC-P3T29-01", ("`--user` and the WorkDir match:", "no other job's facts"))
    pin(s, 716, PIN, "R1 CR-P3T29-01", ("only ended rows are kept,", "a lagging job is asked again"))
    pin(s, 1010, PIN, "R2 SEC-P3T29-02", ("a too deep `sacct.json` reads", "as empty, no answer 500"))
    pin(s, 1290, PIN, "R2 CR-P3T29-04", ("the call count is removed", "once the answer is final"))

    s.line(30, LOW - 32, W - 30, LOW - 32, dashed=True, colour=t.muted)

    # what the failure then shows, to scale ------------------------------------------------------
    s.text(50, LOW, "what the failure shows once sacct answered, from the test", size=14,
           anchor="start")
    s.text(50, LOW + 20, "`test_nf_failure_summary`, a fake sacct; slurm-mini is not built",
           size=13, anchor="start", colour=t.dim)
    bx, full = 150, 400  # 2 GiB and 600 s are both drawn 400 wide
    for i, (name, asked, used, w_used, fill) in enumerate((
            ("memory", "asked 2 GiB", "max RSS 2 GiB, OUT_OF_MEMORY", full, "problem"),
            ("time", "limit 600 s", "elapsed 65 s", full * 65 / 600, "work"))):
        y = LOW + 48 + i * 82
        s.text(bx - 12, y + 26, name, size=14, anchor="end")
        bar(s, bx, y, full, 22, "input")
        s.text(bx + full + 10, y + 16, asked, size=13, anchor="start")
        bar(s, bx, y + 28, w_used, 22, fill)
        s.text(bx + w_used + 10, y + 44, used, size=13, anchor="start")

    s.terminal(826, LOW - 14, 360, 160, ("$ uv run --locked pytest -q \\",
                                          "    packages/spectio-server/tests/api/\\",
                                          "    test_failure.py \\",
                                          "    packages/spectio/tests/test_sacct.py",
                                          "all pass"), size=12, line_h=21)

    # what is still open ----------------------------------------------------------------------------
    ox = 1214
    s.text(ox, LOW, "open after round 3, minor", size=14, anchor="start")
    for i, (fid, what) in enumerate((("R3 SEC-P3T29-03", "a newline in WorkDir forges a row"),
                                     ("R3 CR-P3T29-06", "a symlinked runs root: no match"),
                                     ("R3 CR-P3T29-07", "a failed call keeps its count"),
                                     ("R3 CR-P3T29-08", "no directory still costs 3 calls"))):
        y = LOW + 26 + i * 24
        s.warning(ox + 8, y - 5, size=7)
        s.text(ox + 22, y, fid, size=12.5, anchor="start", weight="bold", colour=t.accent)
        s.text(ox + 146, y, what, size=12.5, anchor="start", colour=t.dim)
    s.text(ox, LOW + 132, "to be validated on slurm-mini: WorkDir,", size=12.5, anchor="start")
    s.text(ox, LOW + 150, "`-j` with `--user`, where each engine", size=12.5, anchor="start",
           colour=t.dim)
    s.text(ox, LOW + 168, "submits from", size=12.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("SEC", "CR"))
    s.text(50, H - 18, "R1 to R3: the code review rounds, IDs restart in each round", size=12.5,
           anchor="start", colour=t.dim)
    s.text(W - 50, H - 18, "source: spectio_server/failure.py, spectio/runner/sacct.py, "
           "tests/api/test_failure.py · P1 Task 29", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t29-failure-facts")
