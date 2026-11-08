#!/usr/bin/env python3
"""Why a job failed, its files and its resources, in the web UI: step P3, P1 Task 32, 2026-11-01.

Writes docs/assets/diagrams/p3-t32-failed-job_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t32 at 00f38eaa (base b690bea7):
- web/src/runs/FailureSummary.tsx: one card per entry of `run.failures` (the first 10 of
  `failures_total`, "Showing 1 of 1 failed task."), its facts Attempt, SLURM job, Exit code,
  "Memory, asked · used", "Time, limit · used", the engine's message unchanged, the log tail,
  Open job files (the task sheet), Copy work directory, and `sources()`: "SLURM state: from sacct
  · Reason: ... · used: from sacct"; RunDetailPage.tsx WhyItFailed: the run-level message left
  out when a card has the same message after trimming (CR-P3T32-04);
- web/src/runs/TaskFiles.tsx: ORDER (job_log, stderr, stdout, script, wrapper, exit, marker,
  trace), MORE (marker, trace) behind "More files", FAILED_FIRST (a failed attempt opens on its
  job log), tabs `<button role="tab">`, a native select labelled File on the phone; STATE_WORDS
  not yet, missing, deleted, gone and the WHY titles; a read is the last TAIL 65536 bytes,
  "last 64 KiB of 3.1 MiB", "Download last 1 MiB" past DOWNLOAD 1048576; the answers 415, 410,
  503, 404 (Retry reloads the listing and reads again, CR-P3T32-02), any other with Retry;
  "Loading the files…" while `listing?.attempt !== n` (CR-P3T32-03); the Attempt select only
  when `attempt_n` is over 1; the work directory row from `listing?.work_dir`;
- web/src/runs/resources.ts: `bytes` in powers of 1024 written GB, `seconds` "6 min", "8 h",
  `nearLimit` above 0.9 of the asked value, `resourcesLine` for the phone; RunState.tsx
  NearLimit, the one badge (CR-P3T32-07, the simplifier's commit 00f38eaa);
  RunDetailPage.tsx TasksPanel: the columns Attempt, Duration, CPUs, CPU %, Memory, Peak memory,
  Time limit, and a Files button named "Files of <task>, attempt <n>";
- web/src/launch/schemaFields.ts `checkValue` (REQUIRED "Required: give a value.", JSON, enum,
  whole number, number, minimum, maximum, `pattern` unanchored, null when the browser cannot
  compile it) and LaunchPage.tsx: "(required)" or "(optional)" in each label, no asterisk
  (CR-P3T32-01), errors shown once a field is touched or Launch pressed, `reason()`
  "Fill the required field: input" with Launch aria-disabled;
- the run, the job and the numbers are the route mocks of tests/e2e/skeleton.spec.ts
  `mockFailed` and the Launch test (job 8812477, exit 137, OUT_OF_MEMORY, 8 GiB asked and
  8 GiB peak, 360 s of an 8 h limit, 6 CPUs at 412 %, `.command.out` 3250586 bytes, `.command.log`
  2458 bytes; `depth` minimum 1 maximum 9 filled with 12), not a cluster's;
- `npx vitest run`, `npx tsc --noEmit` and `uv run pytest -q`: all pass (worker report of
  2026-11-01; no count, so that the figure does not go stale); the Playwright e2e was not re-run
  after the fixes;
- the findings are rounds 1 and 2 of the P3-t32 code review (every verdict approve). Finding IDs
  restart per round, so each pin names its round.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1620
TOP = 124  # band 1: the failed run, the drawer, the phone
CAP1 = TOP + 384
PIN1 = CAP1 + 98
DIV1 = PIN1 + 62
TOP2 = DIV1 + 40  # band 2: resources, and a file that cannot be shown
CAP2 = TOP2 + 312
PIN2 = CAP2 + 76
DIV2 = PIN2 + 56
TOP3 = DIV2 + 36  # band 3: Launch checks, tests, what is open
GIB = 1024 ** 3


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start") -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...]) -> None:
    """A finding the branch fixed, pinned under what it fixed."""
    s.tick(x + 8, y - 5, size=7)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4)


def near(s: Sketch, x: float, y: float, size: float = 12) -> float:
    """The "near limit" badge, words on a tint; returns its right edge."""
    w = size * 5.6
    s.poly([(x, y - size + 1), (x + w, y - size + 1), (x + w, y + 5), (x, y + 5)], fill="work",
           amount=0.3)
    s.text(x + w / 2, y, "near limit", size=size)
    return x + w


def tab(s: Sketch, x: float, y: float, w: float, label: str, *, on: bool = False,
        fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + 26), (x, y + 26)], fill="input" if on else fill,
           amount=0.3)
    if on:
        s.line(x + 4, y + 25, x + w - 4, y + 25, width=3, amount=0.2, passes=1, colour=s.t.accent)
    s.text(x + w / 2, y + 18, label, size=12)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=32)
    t = theme
    s.heading(50, 58, "P3 Task 32 · why a job failed, its files and resources, in the web UI",
              "`web/src/runs` FailureSummary, TaskFiles, resources · `web/src/launch` checkValue · "
              "ui-spec 4.4 note 2026-10-28 · on the routes of P1 Tasks 28 and 29")

    # 1 -- Why it failed: one card per failed job -------------------------------------------------
    x, y = 50, TOP
    s.browser(x, y, 480, 346, url="`/runs/run_id`, Why it failed open first")
    s.text(x + 16, y + 54, "Why it failed", size=15, anchor="start", weight="bold")
    s.text(x + 464, y + 54, "Showing 1 of 1 failed task.", size=12.5, anchor="end", colour=t.dim)
    s.shade(x + 12, y + 66, 456, 268, fill="problem", opacity=0.42)
    s.text(x + 26, y + 92, "`SUBREAD_FEATURECOUNTS`  `S19`", size=14, anchor="start", weight="bold")
    s.poly([(x + 336, y + 76), (x + 456, y + 76), (x + 456, y + 98), (x + 336, y + 98)],
           fill="problem", amount=0.3)
    s.text(x + 396, y + 92, "`OUT_OF_MEMORY`", size=12.5)
    s.text(x + 26, y + 118, "Attempt 1 · SLURM job `8812477` · Exit code `137`", size=13,
           anchor="start")
    s.text(x + 26, y + 142, "Memory, asked · used:  8 GB · 8 GB", size=13, anchor="start")
    near(s, x + 262, y + 142)
    s.text(x + 26, y + 166, "Time, limit · used:  8 h · 6 min", size=13, anchor="start")
    s.text(x + 26, y + 192, "Process `SUBREAD_FEATURECOUNTS (S19)` terminated", size=12.5,
           anchor="start", colour=t.dim)
    s.text(x + 26, y + 210, "with an error exit status (137)", size=12.5, anchor="start",
           colour=t.dim)
    s.shade(x + 24, y + 220, 432, 30, fill="neutral", opacity=0.9)
    s.text(x + 34, y + 240, "`slurmstepd: error: Detected 1 oom_kill event in StepId`", size=12,
           anchor="start")
    s.button(x + 24, y + 260, 140, "Open job files", fill="input", h=28)
    s.button(x + 176, y + 260, 170, "Copy work directory", fill="neutral", h=28)
    s.text(x + 26, y + 306, "SLURM state: from sacct · Reason: Step 0: OutOfMemory", size=12.5,
           anchor="start", colour=t.dim)
    s.text(x + 26, y + 324, "used: from sacct", size=12.5, anchor="start", colour=t.dim)
    s.step(x + 240, CAP1, 1, "one card per job that failed")
    lines(s, x, CAP1 + 30, ("the first 10 of `failures_total`, by attempt",
                            "the engine's message unchanged, then the log tail"))

    # Open job files leads to the drawer
    s.arrow(536, y + 274, 592, y + 274, colour=t.dim)  # Open job files opens the drawer
    s.text(565, y + 296, "Open", size=12, colour=t.dim)
    s.text(565, y + 312, "job files", size=12, colour=t.dim)

    # 2 -- the drawer: the job's files ------------------------------------------------------------
    x = 600
    s.frame(x, y, 580, 346)
    s.line(x, y + 36, x + 580, y + 36, amount=0.8, passes=1)
    s.text(x + 16, y + 25, "SUBREAD_FEATURECOUNTS (S19)", size=14.5, anchor="start", weight="bold")
    s.cross(x + 556, y + 18, size=7)
    s.text(x + 16, y + 60, "ID `tsk_19` · failed · Last attempt 1 · CPUs 6 · 412 %", size=12.5,
           anchor="start", colour=t.dim)
    s.text(x + 16, y + 82, "Memory, asked · peak 8 GB · 8 GB", size=12.5, anchor="start",
           colour=t.dim)
    near(s, x + 240, y + 82, size=11.5)
    s.text(x + 314, y + 82, "· Time limit · duration 8 h · 6 min", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x + 16, y + 112, "Files", size=14, anchor="start", weight="bold")
    s.folder(x + 16, y + 122, 26, 20, fill="input")
    s.text(x + 52, y + 138, "Work directory  `work/9d/77c2140f5be3a1c96e04d2b88a7f13`", size=12.5,
           anchor="start")
    s.button(x + 500, y + 122, 62, "Copy", fill="neutral", h=24)
    tabs = ((".command.log", 104), (".command.err", 102), (".command.out", 104),
            (".command.sh", 96), (".command.run", 104))
    tx = x + 16
    for i, (name, w) in enumerate(tabs):
        tab(s, tx, y + 154, w, f"`{name}`", on=i == 0)
        tx += w + 4
    tab(s, x + 16, y + 184, 84, "`.exitcode`")
    s.text(x + 112, y + 202, "More files", size=12.5, anchor="start", colour=t.accent)
    s.text(x + 190, y + 202, "then `.command.begin`, `.command.trace · missing`", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 16, y + 236, "whole file · 2.4 KiB", size=12.5, anchor="start", colour=t.dim)
    s.button(x + 392, y + 220, 76, "Reload", fill="neutral", h=24)
    s.button(x + 476, y + 220, 88, "Download", fill="neutral", h=24)
    s.shade(x + 16, y + 254, 548, 78, fill="neutral", opacity=0.9)
    s.text(x + 26, y + 278, "`Process BAM file S19.markdup.sorted.bam`", size=12, anchor="start")
    s.text(x + 26, y + 300, "`slurmstepd: error: Detected 1 oom_kill event in`", size=12,
           anchor="start")
    s.text(x + 26, y + 322, "`StepId=8812477.batch`", size=12, anchor="start")
    s.step(x + 290, CAP1, 2, "the drawer opens on the job log")
    lines(s, x, CAP1 + 30, ("a failed attempt opens on `.command.log`; tabs are buttons,",
                            "arrow keys move; Attempt picks an earlier one; Escape returns"))

    # the phone: the same sheet, full screen, a native select
    px = 1210
    scr = s.phone(px, y, 180, 346)
    sx = scr.x + 8
    s.text(sx, scr.y + 22, "SUBREAD_FEATURECOUNTS", size=10, anchor="start", weight="bold")
    s.text(sx, scr.y + 40, "(S19) · full screen", size=11.5, anchor="start", colour=t.dim)
    s.text(sx, scr.y + 70, "File", size=12.5, anchor="start")
    s.poly([(sx, scr.y + 78), (sx + 148, scr.y + 78), (sx + 148, scr.y + 102), (sx, scr.y + 102)],
           fill="input", amount=0.3)
    s.text(sx + 8, scr.y + 95, "`.command.log`", size=12, anchor="start")
    s.line(sx + 128, scr.y + 87, sx + 134, scr.y + 93, amount=0.1, passes=1, width=1.8)
    s.line(sx + 134, scr.y + 93, sx + 140, scr.y + 87, amount=0.1, passes=1, width=1.8)
    s.text(sx, scr.y + 124, "an option per file:", size=11.5, anchor="start", colour=t.dim)
    s.text(sx, scr.y + 142, "`.command.trace · missing`", size=10.5, anchor="start")
    s.shade(sx, scr.y + 156, 150, 70, fill="neutral", opacity=0.9)
    for i, row in enumerate(("`slurmstepd: error:`", "`Detected 1 oom_kill`", "`event in StepId`")):
        s.text(sx + 6, scr.y + 176 + i * 19, row, size=11, anchor="start")
    s.button(sx, scr.y + 240, 148, "Download", fill="neutral", h=26)
    s.text(px + 90, CAP1, "on the phone", size=17)
    lines(s, px + 90, CAP1 + 30, ("a select labelled File,", "not tabs"), anchor="middle")

    s.text(1416, y + 40, "both reach it:", size=13.5, anchor="start")
    lines(s, 1416, y + 62, ("Open job files on", "the card, or a row's", "Files button, named",
                            "Files of `S19`,", "attempt 1"), size=12.5)
    s.text(1416, y + 186, "the sheet is", size=13.5, anchor="start")
    lines(s, 1416, y + 208, ("`aria-modal`, focus", "goes back to the", "button that opened it"),
          size=12.5)

    pin(s, 50, PIN1, "R1 CR-P3T32-04", ("the run's message is left out when a card",
                                       "shows the same one: said once, not twice"))
    pin(s, 600, PIN1, "R1 CR-P3T32-03", ("another attempt picked: Loading the files,",
                                        "not This attempt has no file to show"))
    pin(s, 900, PIN1, "R1 CR-P3T32-02", ("Retry after a 404 reloads the list",
                                        "and reads the file again"))

    s.line(30, DIV1, W - 30, DIV1, dashed=True, colour=t.muted)

    # 3 -- resources per job, to scale -------------------------------------------------------------
    x, y = 50, TOP2
    cols = (("Task", 210), ("State", 50), ("Attempt", 56), ("Duration", 60), ("CPUs", 42),
            ("CPU %", 48), ("Memory", 58), ("Peak memory", 112), ("Time limit", 62), ("", 46))
    cx = x
    s.frame(x, y, sum(w for _, w in cols), 70)
    s.line(x, y + 30, x + sum(w for _, w in cols), y + 30, amount=0.6, passes=1)
    vals = ("SUBREAD_FEATURECOUNTS (S19)", "failed", "1", "6 min", "6", "412 %", "8 GB", "8 GB",
            "8 h", "")
    for (head, w), val in zip(cols, vals, strict=True):
        s.text(cx + 6, y + 20, head, size=12, anchor="start", colour=t.dim)
        s.text(cx + 6, y + 56, val, size=11 if cx == x else 12.5, anchor="start")
        cx += w
    s.line(x + 3, y + 36, x + 3, y + 66, width=4, amount=0.1, passes=1, colour=t.accent)
    near(s, x + sum(w for _, w in cols[:7]) + 44, y + 56, size=11.5)
    s.button(cx - 46 + 2, y + 40, 42, "Files", fill="input", h=24)
    s.text(x, y + 98, "phone, a line per job:", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 146, y + 98, "`attempt 1 · asked 8 GB · peak 8 GB, near limit · limit 8 h`",
           size=12, anchor="start")

    bx, full = x + 70, 440  # the asked value is drawn 440 wide, the used one to scale
    s.text(x, y + 136, "asked, then used, drawn to scale; the badge comes past 90 % of the asked value",
           size=13, anchor="start")
    for i, (name, asked, used, frac, fill) in enumerate((
            ("memory", "asked 8 GB", "peak 8 GB, near limit", 1.0, "problem"),
            ("time", "limit 8 h", "6 min, 1.25 % of it", 360 / (8 * 3600), "work"))):
        yy = y + 152 + i * 50
        s.text(bx - 10, yy + 26, name, size=13.5, anchor="end")
        bar(s, bx, yy, full, 18, "input")
        s.text(bx + full + 8, yy + 14, asked, size=12.5, anchor="start")
        bar(s, bx, yy + 22, max(full * frac, 3), 18, fill)
        s.text(bx + max(full * frac, 3) + 8, yy + 36, used, size=12.5, anchor="start",
               colour=t.dim)
    s.line(bx + full * 0.9, y + 146, bx + full * 0.9, y + 250, dashed=True, colour=t.accent)
    s.text(bx + full * 0.9, y + 262, "90 %", size=12, colour=t.accent)
    s.step(x + 365, CAP2, 3, "resources per job, near limit in words")
    lines(s, x + 365, CAP2 + 30, ("sizes in powers of 1024 written GB, as Nextflow writes them",),
          anchor="middle")

    # 4 -- when a file cannot be shown ---------------------------------------------------------------
    x = 830
    size_b = 3250586
    fw = 560
    s.text(x, y + 16, "`.command.out`, 3 250 586 bytes, to scale", size=13, anchor="start")
    bar(s, x, y + 28, fw, 22, "input")
    s.text(x + fw + 8, y + 44, "3.1 MiB", size=12.5, anchor="start")
    dl = fw * 1048576 / size_b
    tail = fw * 65536 / size_b
    bar(s, x + fw - dl, y + 56, dl, 16, "docs")
    s.text(x + fw - dl - 8, y + 69, "Download last 1 MiB", size=12.5, anchor="end")
    bar(s, x + fw - tail, y + 78, tail, 16, "done")
    s.text(x + fw - tail - 8, y + 91, "shown: last 64 KiB of 3.1 MiB", size=12.5, anchor="end")

    s.text(x, y + 128, "in the listing, the label says the state", size=13, anchor="start")
    states = (("`.command.out · not yet`", "Reload"), ("`.command.trace · missing`", ""),
              ("`SLURM log · deleted`", ""), ("`.command.log · gone`", ""))
    for i, (label, extra) in enumerate(states):
        yy = y + 140 + i * 30
        s.poly([(x, yy), (x + 200, yy), (x + 200, yy + 24), (x, yy + 24)], fill="neutral",
               amount=0.3)
        s.text(x + 100, yy + 17, label, size=11.5)
        if extra:
            s.text(x + 208, yy + 17, "and Reload", size=12, anchor="start", colour=t.dim)
    s.text(x, y + 280, "the panel says why in words", size=12.5, anchor="start",
           colour=t.dim)

    rx = 1130
    s.text(rx, y + 128, "on a read, the answer in words", size=13, anchor="start")
    answers = (("`503`", "Spectio cannot read the cluster's files", "right now · Retry"),
               ("`404`", "This file is not there now", "Retry reads the list and the file"),
               ("`415`", "This file is not text. Download it", "to open it · Download"),
               ("`410`", "The work directory was removed", "nothing to retry"))
    for i, (code, head, sub) in enumerate(answers):
        yy = y + 152 + i * 36
        s.text(rx, yy + 4, code, size=12.5, anchor="start", weight="bold")
        s.text(rx + 40, yy - 3, head, size=12, anchor="start")
        s.text(rx + 40, yy + 12, sub, size=11.5, anchor="start", colour=t.dim)
    s.step(1190, CAP2, 4, "a file that cannot be shown says why")
    lines(s, 1190, CAP2 + 30, ("never a blank panel, never a stack trace",), anchor="middle")

    pin(s, 50, PIN2, "R1 CR-P3T32-07", ("the near limit badge is one component,",
                                       "`NearLimit`, used in all four places"))

    s.line(30, DIV2, W - 30, DIV2, dashed=True, colour=t.muted)

    # 5 -- Launch checks each value before it is sent ----------------------------------------------
    x, y = 50, TOP3
    s.browser(x, y, 520, 250, url="`/launch`, Launch pressed")
    s.text(x + 20, y + 58, "input (required)", size=13.5, anchor="start")
    s.poly([(x + 20, y + 66), (x + 300, y + 66), (x + 300, y + 92), (x + 20, y + 92)],
           fill="problem", amount=0.3)
    s.text(x + 20, y + 110, "Required: give a value.", size=12.5, anchor="start", colour=t.accent)
    s.text(x + 20, y + 140, "depth (optional)", size=13.5, anchor="start")
    s.poly([(x + 20, y + 148), (x + 300, y + 148), (x + 300, y + 174), (x + 20, y + 174)],
           fill="problem", amount=0.3)
    s.text(x + 30, y + 166, "12", size=13, anchor="start")
    s.text(x + 20, y + 192, "Must be at most 9.", size=12.5, anchor="start", colour=t.accent)
    s.button(x + 340, y + 146, 150, "Launch", fill="neutral", h=30)
    s.text(x + 415, y + 194, "`aria-disabled`, its reason:", size=12, colour=t.dim)
    s.text(x + 415, y + 214, "Fill the required field: input", size=12.5)
    s.text(x + 340, y + 68, "no asterisk: the word", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 340, y + 86, "is in the label and in", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 340, y + 104, "the accessible name", size=12.5, anchor="start", colour=t.dim)
    s.step(x + 260, y + 290, 5, "Launch checks each value first")
    pin(s, x, y + 330, "R1 CR-P3T32-01", ("`withAsterisk` false: the label reads",
                                         "depth (optional), no extra star"))

    x = 610
    s.text(x, y + 20, "checked in the browser, from the schema:", size=13.5, anchor="start")
    for i, row in enumerate(("required, not empty", "JSON that parses", "one of the enum values",
                             "a whole number, or a number", "at least `minimum`, at most `maximum`",
                             "matches `pattern`, unanchored")):
        s.tick(x + 8, y + 44 + i * 22 - 4, size=6)
        s.text(x + 22, y + 44 + i * 22, row, size=12.5, anchor="start")
    lines(s, x, y + 186, ("errors show once a field is touched,", "or after Launch is pressed",
                          "the server still checks every value"), size=12.5)
    s.text(x, y + 262, "a pattern the browser cannot compile", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, y + 280, "is left to the server", size=12.5, anchor="start", colour=t.dim)

    # the tests ----------------------------------------------------------------------------------
    s.terminal(950, y - 4, 290, 150, ("$ npx vitest run", "$ npx tsc --noEmit", "$ uv run pytest -q",
                                      "all pass"), size=12.5, line_h=22)
    lines(s, 950, y + 172, ("e2e smoke: route mocks,", "re-run on 00f38eaa: 24 passed"), size=12.5)

    # what is still open -------------------------------------------------------------------------
    ox = 1270
    s.text(ox, y + 12, "open, all minor", size=14, anchor="start")
    opened = (("R1 SEC-P3T32-01", "a schema `pattern` runs", "unbounded: ReDoS"),
              ("R1 SEC-P3T32-02", "Attempt has one option", "per attempt, no cap"),
              ("R2 CR-P3T32-05", "work directory row can", "show another attempt's"),
              ("R1 CR-P3T32-06", "the sheet's Name fact", "was removed"),
              ("R1 CR-P3T32-08", "two time formatters,", "left: outputs differ"))
    for i, (fid, a, b) in enumerate(opened):
        yy = y + 40 + i * 50
        s.warning(ox + 8, yy - 5, size=7)
        s.text(ox + 22, yy, fid, size=12.5, anchor="start", weight="bold", colour=t.accent)
        s.text(ox + 22, yy + 17, a, size=12, anchor="start", colour=t.dim)
        s.text(ox + 22, yy + 32, b, size=12, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 18, "R1, R2: the code review rounds, IDs restart in each round; "
           "the job and its numbers are the e2e mocks", size=12.5, anchor="start", colour=t.dim)
    s.text(W - 50, H - 18, "source: web/src/runs, web/src/launch, tests/e2e/skeleton.spec.ts · "
           "P1 Task 32", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t32-failed-job")
