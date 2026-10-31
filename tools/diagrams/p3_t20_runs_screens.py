#!/usr/bin/env python3
"""The runs screens, Cancel and the Playwright smoke: step P3, P1 Task 20, 2026-10-31.

Writes docs/assets/diagrams/p3-t20-runs-screens_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t20 at 4a70188 (base b0e2edf):
- web/src/live.tsx: one EventSource per tab on STREAM "/api/v1/events/stream"; event
  "spectio.run.delta" whose frame carries run_id; RETRY_MS 5000 after a refusal; useFrames refetches
  at most once a second, on each (re)connection everything, `enabled` false for a terminal run;
  LiveStatus "live, updated N s ago" or "Reconnecting…";
- web/src/home/HomePage.tsx: runsSummary, listRuns(state ACTIVE, limit 20), (sort -ended_at, limit 5),
  (limit 50) for "Your pipelines"; cards by state; a load counter drops an older refresh;
- web/src/runs/RunsPage.tsx: FILTERS All, Active, Failed, Succeeded, Cancelled; name filter after
  250 ms; PAGE 50; one AbortController per query and a load counter (e6dc116, CR-P3T20-03);
  refresh(): a frame refetches page 1 and keeps the Load more rows past its last row (e6dc116,
  CR-P3T20-04); "Load more";
- web/src/runs/RunDetailPage.tsx: getRun, listProcesses, listStages on each frame for this run;
  tabs Summary, Tasks, Parameters, Logs; stages in position order, else "No stages for this
  pipeline"; CANCELLABLE queued, running, not cli-observed; Modal "Cancel this run?", Keep running
  (data-autofocus), "Cancel the run"; after cancelRun the h1 takes focus (e6dc116, CR-P3T20-01);
  the unread cancelButton ref dropped by the simplifier (4a70188, CR-P3T20-02); NotFound "No such
  run"; routes.tsx and the NotFound comment still disagree on /runs/%E0 (CR-P3T20-06, round 1);
- packages/spectio-server/src/spectio_server/api/models.py: response models on the read routes and
  :cancel, the snapshot openapi/0.0.1.json (FU-P3-21);
- tests/e2e/serve-local.sh: mktemp -d, chmod 700, spectio init --local, spectio serve; stop():
  SIGTERM to the server, then heads(): head.pid not a symlink, one line of the runner's _PID_LINE
  grammar, pid > 1, pid = pgid, boot ID = /proc/sys/kernel/random/boot_id, /proc/pid/stat not Z,
  pgrp = pid, start time unchanged; `kill -TERM -- -pid` per head, wait up to 10 s, rm -rf, else
  the directory is kept and the PIDs printed (e6dc116 SEC-P3T20-01, 2f30646 SEC-P3T20-02);
  packages/spectio/tests/test_serve_local.py: a forged `1 1 <start of PID 1>` line is refused;
- tests/e2e/skeleton.spec.ts: 11 tests; 3 test.fixme (Snakemake cancel, TODO P1 Task 7; reused
  link and no cookie, TODO P1 Task 16); 3 skipped unless SPECTIO_E2E_ENGINES=1 (launch, cancel a
  Nextflow run, the detail updates without a reload); playwright.config.ts projects desktop, phone;
- .github/workflows/ci.yml job e2e-local: nf-core/setup-nextflow at NEXTFLOW_VERSION, serve-local.sh
  --port 8765, desktop and phone, artifact e2e-local-report 14 days, not in ci-ok (inbox 90);
- the review rounds, from the step's worker report of 2026-10-31 (review record P3-t20):
  R1 CR approve 01 to 06, SEC approve 01 to 05; fixed: CR-01, 03, 04, SEC-01 in e6dc116, CR-02 in
  4a70188. R2 CR approve 05 to 08, SEC changes with SEC-02 major; fixed: SEC-02 in 2f30646.
  R3 CR approve 05 to 08, SEC approve 03; none fixed. IDs repeat across rounds. Simplifier: 2 lines
  out, 1 in; pytest 511 passed, vitest 63 of 63, before and after.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1675
TOP = 118  # the stream band
SCR = 380  # the screens, their browser windows
COL = (50, 440, 830, 1220)  # four columns, 340 wide
CW = 340
STEP = SCR + 214
TXT = STEP + 30
PIN = TXT + 104
LOC = 985  # serve-local.sh and the smoke
LOW = 1375  # the review rounds

# (round, fixed minor, fixed major, left open, code-reviewer verdict, security-reviewer verdict)
ROUNDS = (("R1", 5, 0, 6, "approve", "approve"),
          ("R2", 0, 1, 4, "approve", "changes"),
          ("R3", 0, 0, 5, "approve", "approve"))


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...], *, fixed: bool) -> None:
    """A finding pinned where it hits: a tick when the branch fixed it, a warning when it is open."""
    if fixed:
        s.tick(x + 8, y - 5, size=7)
    else:
        s.warning(x + 8, y - 5, size=8)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, amount: float = 0.4) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=amount)


def row(s: Sketch, x: float, y: float, w: float, rail: str) -> None:
    """A list row: a coloured state rail, then two ruled strokes for its text."""
    bar(s, x, y, 5, 16, rail, amount=0.2)
    s.line(x + 12, y + 6, x + w * 0.55, y + 6, colour=s.t.muted, amount=0.3, passes=1, width=1.4)
    s.line(x + 12, y + 13, x + w * 0.35, y + 13, colour=s.t.muted, amount=0.3, passes=1, width=1.1)
    s.line(x + w * 0.7, y + 9, x + w - 6, y + 9, colour=s.t.muted, amount=0.3, passes=1, width=1.4)


def sieve(s: Sketch, cx: float, top: float, w: float = 76, h: float = 52) -> None:
    """A funnel with holes: what passes goes on, the rest is held back."""
    s.poly([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.14, top + h), (cx - w * 0.14, top + h)],
           fill="gate", amount=0.8)
    for dx, dy in ((-18, 12), (0, 12), (18, 12), (-9, 28), (9, 28)):
        s.dot(cx + dx, top + dy, 2.4, colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=120)
    t = theme
    s.heading(50, 58, "P3 Task 20 · the runs screens, Cancel, and the Playwright smoke",
              "Home, `/runs` and `/runs/id` in the Paper shell, refreshed from one stream · "
              "ui-spec 4.3, 4.4 and 11 · typed read responses, FU-P3-21 · inbox 90")

    # the stream ---------------------------------------------------------------------------------
    s.hpc_node(50, TOP + 4, 56, 74, busy=2)
    s.cog(132, TOP + 26, 11, fill="docs")
    s.text(160, TOP + 20, "`spectio serve`", size=15, anchor="start", weight="bold")
    lines(s, 160, TOP + 44, ("read routes and `:cancel` now typed", "by `api.models`, in the snapshot",
                             "`openapi/0.0.1.json`"), size=13)
    pin(s, 50, TOP + 138, "R1 SEC-P3T20-02", ("a store drift would log whole inputs",
                                              "through `ResponseValidationError`"), fixed=False)

    s.arrow(430, TOP + 40, 470, TOP + 40)
    for i in range(3):
        s.envelope(480 + i * 48, TOP + 26, 38, 28, fill="input")
    s.arrow(626, TOP + 40, 676, TOP + 40)
    s.text(553, TOP + 12, "`GET /api/v1/events/stream`", size=12.5)
    s.text(553, TOP + 76, "`spectio.run.delta` frames", size=13, colour=t.dim)
    s.text(553, TOP + 95, "carry only the `run_id`", size=13, colour=t.dim)

    s.browser(686, TOP - 4, 260, 116, url="one tab")
    s.text(816, TOP + 52, "one `EventSource`", size=14)
    s.text(816, TOP + 78, "live, updated N s ago", size=12.5, colour=t.good)
    s.text(816, TOP + 98, "or Reconnecting", size=12.5, colour=t.dim)

    s.text(980, TOP + 16, "each screen refetches what it shows", size=15, anchor="start", weight="bold")
    lines(s, 980, TOP + 40, ("at most once a second, `useFrames`", "on each reconnection: everything",
                             "after a refusal: a new stream in 5 s",
                             "the run page stops once the run ended"), size=13)
    pin(s, 1300, TOP + 40, "R2 CR-P3T20-05", ("only the latest request wins: a", "server slower than 1 s, with",
                                             "frames coming, never updates"), fixed=False)

    for cx in COL:
        s.arrow(816, TOP + 118, cx + CW / 2, SCR - 10, dashed=True, colour=t.dim)
    s.text(625, TOP + 186, "a frame: refetch", size=13, colour=t.dim)

    # 1 -- Home ----------------------------------------------------------------------------------
    x = COL[0]
    bx, by, bw = x + 10, SCR, 320
    s.browser(bx, by, bw, 170, url="/")
    for i, (word, fill) in enumerate((("Running", "input"), ("Failed", "problem"), ("Succeeded", "done"))):
        cx = bx + 12 + i * 100
        bar(s, cx, by + 38, 90, 34, fill)
        s.text(cx + 8, by + 53, word, size=11.5, anchor="start")
        s.line(cx + 8, by + 63, cx + 26, by + 63, width=2.6, amount=0.2, passes=1)
    s.text(bx + 12, by + 90, "Active runs", size=11, anchor="start", weight="bold")
    row(s, bx + 12, by + 96, 180, "input")
    s.text(bx + 12, by + 130, "Finished recently", size=11, anchor="start", weight="bold")
    row(s, bx + 12, by + 136, 180, "done")
    s.page(bx + 204, by + 84, 106, 76, fill="docs", lines=0)
    s.text(bx + 210, by + 104, "Your pipelines", size=10.5, anchor="start", weight="bold")
    for j in range(3):
        s.line(bx + 222, by + 116 + j * 13, bx + 290, by + 116 + j * 13, colour=t.muted, amount=0.3,
               passes=1, width=1.2)
    s.step(x + CW / 2, STEP, 1, "Home at `/`")
    lines(s, x, TXT, ("counts by state, over all runs", "the active runs, up to 20",
                      "the 5 that ended last", "pipeline directories of the last 50"))
    pin(s, x, PIN, "R2 R3 CR-P3T20-06", ("its race test waits on a list that",
                                         "cannot render: a hidden 1 s sleep"), fixed=False)

    # 2 -- the runs list -------------------------------------------------------------------------
    x = COL[1]
    bx = x + 10
    s.browser(bx, by, bw, 170, url="/runs")
    bar(s, bx + 12, by + 38, 296, 20, "surface")
    s.text(bx + 20, by + 52, "Filter by run name", size=10.5, anchor="start", colour=t.dim)
    for i, (word, w) in enumerate((("All", 40), ("Active", 56), ("Failed", 54), ("Succeeded", 72),
                                   ("Cancelled", 66))):
        sx = bx + 12 + sum((40, 56, 54, 72, 66)[:i]) + i * 2
        bar(s, sx, by + 64, w, 20, "input" if i == 1 else "surface", amount=0.3)
        s.text(sx + w / 2, by + 78, word, size=10.5, weight="bold" if i == 1 else "normal")
    for j, rail in enumerate(("input", "done")):
        row(s, bx + 12, by + 94 + j * 22, 296, rail)
    s.button(bx + 12, by + 142, 80, "Load more", fill="surface", h=20)
    s.step(x + CW / 2, STEP, 2, "the runs list, `/runs`")
    lines(s, x, TXT, ("50 a page, newest first", "state and name filters, 250 ms pause",
                      "a frame refetches page 1, keeps", "the rows Load more added past it"))
    pin(s, x, PIN, "R1 CR-P3T20-03", ("an older answer landed last; now a", "counter and an AbortController"),
        fixed=True)
    pin(s, x, PIN + 64, "R1 CR-P3T20-04", ("past 200 rows a frame dropped the rest",), fixed=True)
    pin(s, x, PIN + 108, "R3 CR-P3T20-05", ("Load more rows are never refetched",), fixed=False)

    # 3 -- the run -------------------------------------------------------------------------------
    x = COL[2]
    bx = x + 10
    s.browser(bx, by, bw, 170, url="/runs/id")
    s.line(bx + 12, by + 46, bx + 120, by + 46, width=3, amount=0.3, passes=1)
    s.text(bx + 12, by + 66, "Running", size=11.5, anchor="start", colour=t.good)
    s.text(bx + 70, by + 66, "1 of 2 stages done", size=11, anchor="start", colour=t.dim)
    bar(s, bx + 222, by + 38, 86, 24, "problem", amount=0.3)
    s.text(bx + 265, by + 55, "Cancel run", size=11.5, weight="bold", colour=t.accent)
    for i, tab in enumerate(("Summary", "Tasks", "Parameters", "Logs")):
        tx = bx + 12 + (0, 70, 120, 208)[i]
        s.text(tx, by + 92, tab, size=11, anchor="start", weight="bold" if i == 0 else "normal")
    s.line(bx + 12, by + 98, bx + 64, by + 98, width=2.4, amount=0.2, passes=1, colour=t.accent)
    for j in range(3):
        y = by + 112 + j * 18
        s.text(bx + 16, y + 10, "v" if j == 1 else ">", size=11, colour=t.dim)
        s.line(bx + 30, y + 6, bx + 170, y + 6, colour=t.muted, amount=0.3, passes=1, width=1.4)
        s.line(bx + 220, y + 6, bx + 300, y + 6, colour=t.muted, amount=0.3, passes=1, width=1.4)
    s.step(x + CW / 2, STEP, 3, "the run, `/runs/id`")
    lines(s, x, TXT, ("run, processes, stages on a frame", "for this run, until it has ended",
                      "stages in order, else the processes", "unknown id: No such run, in the shell"))
    pin(s, x, PIN, "R1 CR-P3T20-06", ("two comments disagree on how", "`/runs/%E0` is routed"), fixed=False)

    # 4 -- Cancel --------------------------------------------------------------------------------
    x = COL[3]
    bx = x + 10
    s.shade(bx, by, bw, 170, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    bar(s, bx + 30, by + 14, 260, 92, "surface", amount=0.6)
    s.text(bx + 44, by + 40, "Cancel this run?", size=13.5, anchor="start", weight="bold")
    s.button(bx + 44, by + 60, 104, "Keep running", fill="surface", h=30)
    s.button(bx + 160, by + 60, 116, "Cancel the run", fill="problem", h=30)
    s.text(bx + 96, by + 124, "`aria-modal`", size=12, colour=t.dim)
    s.arrow(bx + 200, by + 94, bx + 200, by + 118)
    bar(s, bx + 150, by + 124, 86, 22, "work", amount=0.3)
    s.text(bx + 193, by + 140, "Cancelling", size=11.5)
    s.arrow(bx + 240, by + 135, bx + 254, by + 135)
    s.text(bx + 258, by + 140, "Cancelled", size=11.5, anchor="start", weight="bold")
    s.text(bx + 200, by + 164, "`POST :cancel` 202", size=11.5, colour=t.dim)
    s.step(x + CW / 2, STEP, 4, "Cancel, behind a confirm")
    lines(s, x, TXT, ("queued or running, not from a terminal", "Keep running has the focus",
                      "SIGTERM to the head's process group", "then the focus moves to the run title"))
    pin(s, x, PIN, "R1 CR-P3T20-01", ("focus fell to the page body", "once Cancel was gone"), fixed=True)
    pin(s, x, PIN + 64, "R1 CR-P3T20-02", ("simplify: an unread ref, dropped",), fixed=True)

    for cx in COL[:3]:
        s.arrow(cx + CW + 4, STEP - 6, cx + CW + 36, STEP - 6, colour=t.dim)

    # serve-local.sh and the smoke ----------------------------------------------------------------
    s.line(30, LOC - 62, W - 30, LOC - 62, dashed=True, colour=t.muted)
    s.text(50, LOC - 72, "try it here, `tests/e2e/serve-local.sh`, and the smoke that CI runs against it",
           size=14, anchor="start", colour=t.dim)

    s.terminal(50, LOC, 300, 100, ("$ bash tests/e2e/serve-local.sh", "  Spectio is running. Open ...",
                                   "^C"), size=12)
    lines(s, 50, LOC + 126, ("a 0700 temp dir, `spectio init --local`", "`spectio serve`, on 127.0.0.1 only"),
          size=13)
    s.arrow(360, LOC + 50, 400, LOC + 50)
    s.text(380, LOC + 40, "stop", size=12.5, colour=t.dim)

    s.folder(410, LOC - 4, 220, 112, fill="input")
    s.text(520, LOC + 26, "`runs/*/launch/.spectio`", size=12)
    s.page(450, LOC + 38, 46, 60, fill="surface", lines=2)
    s.page(540, LOC + 38, 46, 60, fill="problem", lines=2)
    s.text(473, LOC + 126, "`pid pgid start boot host`", size=12)
    s.text(563, LOC + 146, "forged: `1 1 start of PID 1 ...`", size=12, colour=t.accent)

    s.arrow(640, LOC + 50, 680, LOC + 50)
    sieve(s, 726, LOC + 24)
    s.text(726, LOC + 96, "`heads()`", size=13)
    s.text(790, LOC + 10, "names a PID only when", size=14, anchor="start", weight="bold")
    lines(s, 790, LOC + 32, ("head.pid is no symlink, one strict line", "pid above 1, pid = pgid",
                             "this boot, by `boot_id`", "in /proc: alive, group = pid,",
                             "the same start time"), size=13)

    s.arrow(726, LOC + 110, 726, LOC + 164)
    s.text(740, LOC + 150, "`kill -TERM -- -pid`, each head's group", size=13, anchor="start")
    s.text(740, LOC + 170, "wait up to 10 s, then remove the dir", size=13, anchor="start", colour=t.dim)
    s.text(740, LOC + 190, "a head still up: dir kept, PIDs printed", size=13, anchor="start",
           colour=t.dim)
    s.cross(578, LOC + 186, size=10)
    s.text(596, LOC + 182, "`kill -TERM -- -1`", size=12, anchor="start", colour=t.accent)
    s.text(596, LOC + 200, "every process", size=12, anchor="start", colour=t.dim)
    s.text(596, LOC + 216, "of the user", size=12, anchor="start", colour=t.dim)

    pin(s, 50, LOC + 210, "R2 SEC-P3T20-02 · major", ("a forged PID 1 line passed and stop() would",
                                                      "have signalled every group, `2f30646`"), fixed=True)
    pin(s, 50, LOC + 276, "R1 SEC-P3T20-01", ("Ctrl-C removed the runs root under", "heads still running"),
        fixed=True)
    pin(s, 400, LOC + 276, "R3 SEC-P3T20-03", ("any group leader of the user, with", "its real start time"),
        fixed=False)
    pin(s, 740, LOC + 236, "R3 CR-P3T20-07, 08", ("the comment still claims parity; the", "grammar is a second copy",
                                                  "in shell"), fixed=False)

    # the smoke ---------------------------------------------------------------------------------
    x = 1090
    s.browser(x, LOC - 4, 170, 100, url="desktop")
    bar(s, x + 14, LOC + 40, 60, 14, "done", amount=0.3)
    row(s, x + 14, LOC + 64, 140, "input")
    s.phone(x + 186, LOC - 10, 60, 112)
    s.text(x + 216, LOC + 50, "phone", size=11, colour=t.dim)
    s.text(x + 266, LOC + 14, "CI job `e2e-local`", size=15, anchor="start", weight="bold")
    lines(s, x + 266, LOC + 38, ("Playwright, a real serve", "Nextflow, `setup-nextflow`",
                                 "not in `ci-ok` yet, inbox 90"), size=13)

    sy = LOC + 132
    s.text(x, sy, "the 11 tests of `skeleton.spec.ts`, to scale", size=13.5, anchor="start")
    s.task_strip(x, sy + 12, ((5, "done", "run always"), (3, "work", "need Nextflow"),
                              (3, "neutral", "fixme")), cell=30, gap=3, h=24, label_size=12.5)
    s.text(x, sy + 82, "fixme: two wait for sign-in, Task 16;", size=12.5, anchor="start", colour=t.dim)
    s.text(x, sy + 100, "Snakemake cancel waits for Task 7", size=12.5, anchor="start", colour=t.dim)
    pin(s, x, sy + 140, "R1 SEC-P3T20-03", ("the Nextflow download is not checked", "against `NEXTFLOW_SHA256`"),
        fixed=False)

    # the review rounds, to scale ----------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW, "3 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(50, LOW + 22, "code-reviewer and security-reviewer in parallel, then the simplifier",
           size=13.5, anchor="start", colour=t.dim)
    cell, rh = 22, 38
    for i, (rnd, fixed, major, left, cr, sec) in enumerate(ROUNDS):
        y = LOW + 46 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, fill in ((fixed, "done"), (major, "problem"), (left, "neutral"))
                       if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=3, h=22)
        s.text(right + 4, y + 16, f"{fixed + major + left}", size=14, anchor="start")
        s.text(420, y + 16, f"CR {cr}, SEC {sec}", size=13.5, anchor="start")
        if sec == "changes":
            s.warning(612, y + 9, size=8)
        else:
            s.tick(612, y + 10, size=7)
    ly = LOW + 46 + 3 * rh + 4
    for j, (fill, label) in enumerate((("done", "fixed"), ("problem", "major, fixed"),
                                       ("neutral", "minor, left open"))):
        lx = 90 + j * 150
        bar(s, lx, ly, 16, 16, fill, amount=0.3)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)
    s.text(50, ly + 46, "no blocker · simplifier: 2 lines out, 1 in", size=13.5, anchor="start")
    s.text(50, ly + 68, "pytest 511 passed, vitest 63 of 63, before and after", size=13.5, anchor="start",
           colour=t.dim)

    bx, bw = 650, 900
    s.shade(bx, LOW - 18, bw, 230, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(bx + 28, LOW + 8, size=11)
    s.text(bx + 50, LOW + 14, "left open after round 3, both approve", size=15, anchor="start",
           weight="bold")
    s.text(bx + bw - 20, LOW + 14, "IDs repeat across rounds", size=12.5, anchor="end", colour=t.dim)
    open_items = (
        ("an unrelated edit in `test_stream.py`", "R1 CR-P3T20-05"),
        ("comments disagree on `/runs/%E0`", "R1 CR-P3T20-06"),
        ("a model drift logs whole inputs", "R1 SEC-P3T20-02"),
        ("Nextflow on CI, no sha256 check", "R1 SEC-P3T20-03"),
        ("the banner understates the exposure", "R1 SEC-P3T20-04"),
        ("host residue: user `alice`, `/g/demo-lab`", "R1 SEC-P3T20-05"),
        ("latest wins: a slow server never updates", "R2 CR-P3T20-05"),
        ("the Home test swallows a failed wait", "R2 CR-P3T20-06"),
        ("a header test races a later render", "R2 CR-P3T20-07"),
        ("a throwaway AbortController per render", "R2 CR-P3T20-08"),
        ("Load more rows are never refetched", "R3 CR-P3T20-05"),
        ("that wait is a hidden 1 s sleep", "R3 CR-P3T20-06"),
        ("the heads comment still overclaims", "R3 CR-P3T20-07"),
        ("heads repeats the runner grammar", "R3 CR-P3T20-08"),
        ("heads does not tie a PID to its run", "R3 SEC-P3T20-03"),
    )
    for i, (what, fid) in enumerate(open_items):
        col, r = divmod(i, 8)
        cx = bx + 20 + col * 445
        y = LOW + 44 + r * 22
        s.dot(cx + 6, y - 5, 2.6, colour=t.dim)
        s.text(cx + 18, y, what, size=13, anchor="start")
        s.text(cx + 425, y, fid, size=12, anchor="end", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch · a warning: left open · R1 to R3: the round",
           size=13, anchor="start", colour=t.dim)
    s.text(W - 50, H - 16, "source: web/src/live.tsx, home, runs, api/models.py, serve-local.sh, "
           "skeleton.spec.ts, ci.yml at 4a70188 · review record P3-t20 · P1 Task 20", size=12.5,
           anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t20-runs-screens")
