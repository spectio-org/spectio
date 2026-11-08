#!/usr/bin/env python3
"""Five follow-ups from Thomas's login1 feedback: batch P3-B08 (steps P3-fu79 to P3-fu83,
wave W5), 2026-11-08.

Writes docs/assets/diagrams/p3-b08-login1-followups_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B08 at f3dca797 (PRs 175 to 179 merged into
autopilot/integration between f82fc692 and 17fc9c0f, then the batch code-simplifier's two
commits 80717b05 and f3dca797):
- P3-fu79, PR 177: web/index.html links `/src/assets/favicon.svg` (the emblem, four wedges);
  web/src/live.tsx `useLiveStatus()` opens the stream and returns its status
  (`connecting`, `live`, `reconnecting`); web/src/shell/AppShell.tsx: while `reconnecting` the
  shell is given `server=null` and "The live stream is reconnecting.", Sidebar.tsx and TopBar.tsx
  then read "Server not reached"; back to `live`, `GET /version` is read again; a failed re-read
  hides the last server (`reached` null);
- P3-fu80, PR 176: web/src/runs/DetailSheet.tsx `ProcessTasks`: an aria-hidden header row
  `Task` (Snakemake `Job`) and `State`, rows without the tag chip, the name "Open task ALIGN (S01),
  Succeeded" (DetailSheet.test.tsx:98), the first page read again by `useFrames` while the run is
  active, `refresh` keeps Load more's rows (stateWord.ts); runs.css `.sp-task-head` and
  `.sp-task-rows .sp-sheet-row`: grid `minmax(0, 1fr) 9.5rem`; RunDetailPage.tsx `LogTail` read
  again on each frame of an active run;
- P3-fu81, PR 178: spectio_server/files/taskfiles.py `run_root`: on a missing directory, the
  runs root not a directory, or `_check_recorded` (`os.path.realpath` of the recorded root
  against the runs root, nothing opened) differing: `Unreachable`; else `Cleaned`; both texts end
  `tried <runs root>/<run>/<part>`; `recorded_root(launch_dir, origin)`: the launch directory's
  grandparent, None for `cli-observed`; api/taskfiles.py `in_pool`: `409 run-dir-unreachable`,
  `410 log-cleaned`; api/logs.py `_launch_root` uses the same helper;
- P3-fu82, PR 175: spectio_server/api/runs_read.py `_pipeline_order` (topological on the rule
  graph's `links`, `sourcerule` before `targetrule`, ties by the recorded order, cycles last; no
  links and Nextflow: the recorded order), `pipeline_order` on each `/processes` item;
  web/src/runs/ByProcess.tsx: default key `pipeline`, a `radiogroup` "Order" of two native radios
  "Pipeline order" and "A to Z", neither checked under a column sort; the four rules drawn are a
  chain of tests/pipelines/synthetic/snakemake/workflow/Snakefile (make_reads, checkpoint split,
  align, align_done by their inputs); A to Z is by code point;
- P3-fu83, PR 179: tests/pipelines/synthetic/bin/synth.py `_log` (INFO on stdout, WARN, DEBUG and
  ERROR on stderr, flushed per line), `STEPS` quiet 0, normal 3, loud 1000; the Snakefile `logs()`
  declares `err` before `out`, `body()` is `( hook && cmd ) 2>&1 > {log.out} | tee {log.err} >&2`;
  nextflow.config profile `fail_demo` (fail_mode exit, fail_process COMPARE, fail_sample treatA)
  and snakemake/profiles/fail_demo/config.yaml (compare, treatA, exit);
- findings: docs/reviews/code/P3-fu79.md to P3-fu83.md. Every blocker and major is pinned:
  CR-P3FU81-01 r1, CR-P3FU81-02 r1, CR-P3FU81-03 r2, CR-P3FU83-01, CR-P3FU83-02, CR-P3FU83-R2-03
  (all major; none blocker). P3-fu79, P3-fu80 and P3-fu82 had none;
- the batch simplifier's report: 2 commits, -12 +4 (`git show --stat` 80717b05: -9 +4,
  f3dca797: -3); baseline pytest 1143 passed, 1 skipped, 30 deselected; after the edits only
  `pytest packages/spectio-server`, 713 passed; vitest 330 passed, tsc, ruff, format, mypy,
  lint-imports, `uv lock` clean before and after; re-review not needed.
"""

from __future__ import annotations

import math

from sketch import Sketch, Theme, main_for

W, H = 1600, 1330
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
HEAD = 178  # the step's name above its pictogram
TOP = 200  # the pictograms
CAP = 412  # the numbered captions
PIN = 530  # the pins and notes
LOW = 980  # the batch simplifier and the tests


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, severity: str, rows: tuple[str, ...],
        status: str, *, w: float = 280, warn: bool = False) -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it was fixed."""
    h = 34 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="gate" if warn else "done",
           amount=0.5, width=1.2)
    if warn:
        s.warning(x + 16, y + 13, size=8)
    else:
        s.tick(x + 16, y + 13, size=6)
    s.text(x + 32, y + 18, fid, size=13, anchor="start", weight="bold")
    s.text(x + w - 10, y + 18, severity, size=12.5, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 40 + i * 19, row, size=12.5, anchor="start")
    s.text(x + 12, y + 40 + len(rows) * 19, status, size=12.5, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = 280,
         warn: bool = False) -> float:
    """A dashed note: the rounds, what is open; returns its bottom."""
    h = 14 + 21 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 0
    if warn:
        s.warning(x + 18, y + 19, size=8)
        ox = 18
    for i, row in enumerate(rows):
        s.text(x + 12 + (ox if i == 0 else 0), y + 24 + i * 21, row, size=12.5, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def emblem(s: Sketch, cx: float, cy: float, r: float) -> None:
    """The favicon: the brand emblem's four wedges of a half disc."""
    fills = ("bar_blue", "bar_violet", "pink", "bar_orange")
    for i, fill in enumerate(fills):
        a0, a1 = 180 + i * 45 + 4, 180 + (i + 1) * 45 - 4
        pts = [(cx, cy)] + [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                            for a in (a0, (a0 + a1) / 2, a1)]
        s.poly(pts, fill=fill, amount=0.1, width=1.0)


def radio(s: Sketch, cx: float, cy: float, checked: bool) -> None:
    s.circle(cx, cy, 7, width=1.4)
    if checked:
        s.dot(cx, cy, 3.6, colour=s.t.ink)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=808)
    t = theme
    s.heading(50, 58, "P3-B08 · five follow-ups from the login1 demo",
              "wave W5 · steps P3-fu79 to P3-fu83 · Thomas's feedback, 2026-11-08 · "
              "PRs 175 to 179 into `autopilot/integration`")
    band(s, 140, "what each step added, where the reader meets it · the web shell, the run's "
         "sheets and tabs, the server's file routes, the synthetic test pipelines")

    # 1 -- P3-fu79: the tab icon, and a status that follows the stream -------------------------
    x = COL[0]
    s.text(x, HEAD, "P3-fu79 · PR 177", size=14, anchor="start", weight="bold")
    s.poly([(x + 4, TOP + 6), (x + 112, TOP + 6), (x + 118, TOP + 28), (x - 2, TOP + 28)],
           fill="surface", amount=0.4, width=1.3)
    emblem(s, x + 22, TOP + 23, 11)
    s.text(x + 40, TOP + 22, "Spectio", size=12.5, anchor="start")
    s.browser(x - 2, TOP + 28, 176, 100)
    s.poly([(x + 10, TOP + 70), (x + 162, TOP + 70), (x + 162, TOP + 96), (x + 10, TOP + 96)],
           fill="problem", amount=0.4, width=1.2)
    s.text(x + 86, TOP + 88, "Server not reached", size=12.5)
    s.text(x + 86, TOP + 118, "sidebar foot, phone pill", size=11.5, colour=t.dim)
    s.hpc_node(x + 226, TOP + 30, 46, 60, busy=2)
    s.text(x + 249, TOP + 20, "server", size=12, colour=t.dim)
    s.line(x + 180, TOP + 60, x + 222, TOP + 60, dashed=True, colour=t.dim)
    s.cross(x + 201, TOP + 60, size=7)
    s.text(x + 280, TOP + 116, "`reconnecting`", size=11, anchor="end")
    s.arrow(x + 222, TOP + 148, x + 180, TOP + 148)
    s.tick(x + 238, TOP + 148, size=6)
    s.text(x + 4, TOP + 152, "back `live`: `GET /version` again", size=11.5, anchor="start")
    s.step(x + CW / 2, CAP, 1, "a status that follows")
    lines(s, x, CAP + 30, ("the tab shows the emblem, `favicon.svg`",
                           "`useLiveStatus` opens the stream",
                           "on every page, not one read at load",
                           "a failed re-read hides the old server"))

    # 2 -- P3-fu80: a process's tasks in two named columns, read live ------------------------
    x = COL[1]
    s.text(x, HEAD, "P3-fu80 · PR 176", size=14, anchor="start", weight="bold")
    sx, sw = x + 4, 244
    s.poly([(sx, TOP), (sx + sw, TOP), (sx + sw, TOP + 150), (sx, TOP + 150)], fill="surface",
           amount=0.5, width=1.4)
    split = sx + sw - 106  # 9.5rem of the State column
    s.text(sx + 10, TOP + 22, "Task", size=12, anchor="start", colour=t.dim, weight="bold")
    s.text(split + 8, TOP + 22, "State", size=12, anchor="start", colour=t.dim, weight="bold")
    rows = (("`ALIGN (S01)`", "Succeeded", "done"), ("`ALIGN (S02)`", "Running", "work"),
            ("`ALIGN (S03)`", "Failed", "problem"), ("`ALIGN (S04)`", "Not scheduled", "neutral"))
    for i, (label, word, fill) in enumerate(rows):
        y = TOP + 32 + i * 27
        s.line(sx + 6, y, sx + sw - 6, y, colour=t.muted, passes=1, amount=0.3, width=1.0)
        s.text(sx + 10, y + 19, label, size=11, anchor="start")
        dot = {"done": t.good, "work": t.warn, "problem": t.accent}.get(fill, t.muted)
        s.dot(split + 12, y + 14, 4.5, colour=dot)
        s.text(split + 21, y + 19, word, size=11, anchor="start")
    s.line(split, TOP + 8, split, TOP + 146, dashed=True, colour=t.accent, passes=1)
    s.text(split + 40, TOP + 168, "`9.5rem`", size=11.5, colour=t.dim)
    s.text(sx, TOP + 168, "one grid, every row", size=11.5, anchor="start", colour=t.dim)
    s.arc(x + 258, TOP + 30, x + 258, TOP + 104, lift=16, colour=t.good)
    s.text(x + 282, TOP + 124, "each", size=11.5, anchor="end", colour=t.dim)
    s.text(x + 282, TOP + 140, "frame", size=11.5, anchor="end", colour=t.dim)
    s.step(x + CW / 2, CAP, 2, "task rows, named columns")
    lines(s, x, CAP + 30, ("`Task` or `Job`, then `State`; no tag chip",
                           "read again on each frame while active",
                           "rows Load more added are kept",
                           "the Summary's log tail, the same"))

    # 3 -- P3-fu81: 409 or 410, and the directory tried ---------------------------------------
    x = COL[2]
    s.text(x, HEAD, "P3-fu81 · PR 178", size=14, anchor="start", weight="bold")
    s.folder(x + 4, TOP + 4, 98, 62, fill="input", label="recorded")
    s.text(x + 53, TOP + 84, "the run's row", size=11.5, colour=t.dim)
    s.folder(x + 178, TOP + 4, 98, 62, fill="input", label="runs root")
    s.text(x + 227, TOP + 84, "this server's", size=11.5, colour=t.dim)
    s.text(x + 140, TOP + 30, "`realpath`", size=11.5)
    s.text(x + 140, TOP + 50, "same?", size=12.5, weight="bold")
    s.tick(x + 12, TOP + 110, size=6)
    s.text(x + 26, TOP + 115, "same, dir gone:", size=12, anchor="start")
    s.text(x + 136, TOP + 115, "`410 log-cleaned`", size=11.5, anchor="start")
    s.cross(x + 12, TOP + 136, size=6)
    s.text(x + 26, TOP + 141, "missing or other:", size=12, anchor="start")
    s.text(x + 26, TOP + 162, "`409 run-dir-unreachable`", size=11.5, anchor="start")
    s.step(x + CW / 2, CAP, 3, "say which dir is missing")
    lines(s, x, CAP + 30, ("both end `tried <root>/<run>/launch`",
                           "`recorded_root`: the launch dir's",
                           "grandparent; none for a terminal run",
                           "Logs tab and job files, one rule"))

    # 4 -- P3-fu82: pipeline order, or A to Z --------------------------------------------------
    x = COL[3]
    s.text(x, HEAD, "P3-fu82 · PR 175", size=14, anchor="start", weight="bold")
    chain = ("make_reads", "split", "align", "align_done")
    for i, rule in enumerate(chain):
        y = TOP + 4 + i * 37
        s.poly([(x + 4, y), (x + 112, y), (x + 112, y + 22), (x + 4, y + 22)], fill="work",
               amount=0.4, width=1.2)
        s.text(x + 58, y + 16, f"`{rule}`", size=11)
        s.text(x + 120, y + 16, str(i), size=12.5, anchor="start", colour=t.dim)
        if i:
            s.arrow(x + 58, y - 14, x + 58, y - 1, colour=t.dim)
    s.text(x + 4, TOP + 160, "rule graph `links`", size=11.5, anchor="start", colour=t.dim)
    radio(s, x + 152, TOP + 20, True)
    s.text(x + 166, TOP + 25, "Pipeline order", size=12.5, anchor="start")
    radio(s, x + 152, TOP + 46, False)
    s.text(x + 166, TOP + 51, "A to Z", size=12.5, anchor="start")
    for i, rule in enumerate(sorted(chain)):
        s.text(x + 166, TOP + 80 + i * 19, f"`{rule}`", size=11, anchor="start", colour=t.dim)
    s.text(x + 148, TOP + 160, "A to Z, by code point", size=11.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP, 4, "pipeline order, or A to Z")
    lines(s, x, CAP + 30, ("`pipeline_order` on each `/processes`",
                           "item: a rule before the rules it feeds",
                           "ties, Nextflow: the recorded order",
                           "a column sort checks neither radio"))

    # 5 -- P3-fu83: task logs, and a run that fails ------------------------------------------
    x = COL[4]
    s.text(x, HEAD, "P3-fu83 · PR 179", size=14, anchor="start", weight="bold")
    s.cog(x + 24, TOP + 64, 16, fill="work")
    s.text(x + 24, TOP + 104, "`synth.py`", size=11)
    s.arrow(x + 44, TOP + 52, x + 94, TOP + 24)
    s.arrow(x + 44, TOP + 76, x + 94, TOP + 98)
    s.page(x + 100, TOP + 2, 96, 50, fill="surface", lines=0)
    s.text(x + 108, TOP + 20, "`.out`", size=11, anchor="start", weight="bold")
    s.text(x + 108, TOP + 40, "`INFO`", size=11, anchor="start", colour=t.dim)
    s.page(x + 100, TOP + 70, 96, 62, fill="problem", lines=0)
    s.text(x + 108, TOP + 88, "`.err`", size=11, anchor="start", weight="bold")
    s.text(x + 108, TOP + 106, "`WARN`", size=11, anchor="start", colour=t.dim)
    s.text(x + 108, TOP + 124, "`ERROR`", size=11, anchor="start", colour=t.dim)
    s.arrow(x + 200, TOP + 100, x + 226, TOP + 100, dashed=True)
    s.text(x + 213, TOP + 90, "`tee`", size=11)
    s.hpc_node(x + 232, TOP + 72, 40, 54, busy=1)
    s.text(x + 252, TOP + 146, "job log", size=11.5, colour=t.dim)
    s.text(x + 4, TOP + 168, "`fail_demo`: COMPARE, treatA, exit 1", size=11.5, anchor="start")
    s.cross(x + 268, TOP + 164, size=6)
    s.step(x + CW / 2, CAP, 5, "task logs, a failing run")
    lines(s, x, CAP + 30, ("`verbosity` quiet, normal or loud",
                           "loud: 1000 lines a stream, past 64 KiB",
                           "Snakemake: `err` log first, stderr teed",
                           "`fail_demo` profile in both engines"))

    for a, b in zip(COL[:4], COL[1:]):
        s.arrow(a + CW + 2, CAP - 6, b - 3, CAP - 6, colour=t.muted)

    # pins and notes ----------------------------------------------------------------------------
    note(s, COL[0], PIN, ("2 rounds, approve both · no blocker", "or major · security skipped,",
                          "no sensitive path"))
    note(s, COL[0], PIN + 92, ("open, minor: a 429 reads as not", "reached, CR-P3FU79-03; open then",
                               "fail is not re-read, -04; a flaky", "`TaskFiles` test, -05"))

    note(s, COL[1], PIN, ("2 rounds, approve both · no blocker", "or major · CR-P3FU80-02 minor:",
                          "a failed re-read hid the rows and", "the focus, fixed in 0c60369b"))
    note(s, COL[1], PIN + 112, ("open, minor: CR-P3FU80-01, a test", "fixture the server never sends;",
                                "the dead CSS rule: below, closed", "by the batch simplifier"))
    note(s, COL[1], PIN + 224, ("to be validated: 9.5rem at phone", "width; the sheet not rendered"),
         warn=True)

    y = pin(s, COL[2], PIN, "CR-P3FU81-01 r1", "major",
            ("job-file routes still said 410 or 404",), "fixed in aea6ef6e, one check")
    y = pin(s, COL[2], y + 10, "CR-P3FU81-02 r1", "major",
            ("a stale index named as the cause,", "untracked; it did not explain it"),
            "inbox 125 asks Thomas; cause unproven")
    y = pin(s, COL[2], y + 10, "CR-P3FU81-03 r2", "major",
            ("a terminal run got a false 409:", "its project taken for a runs root"),
            "fixed in a233575c: none for it")
    note(s, COL[2], y + 10, ("3 rounds · code-reviewer: changes,", "changes, approve · security:",
                             "approve, nothing open"))

    note(s, COL[3], PIN, ("1 round, approve both · no blocker", "or major"))
    note(s, COL[3], PIN + 70, ("open, minor: CR-P3FU82-02, Tab", "never pressed in the keyboard test;",
                               "-03, the phone has the order in", "the radios and in Sort by"))
    note(s, COL[3], PIN + 182, ("not done: the By process boards", "do not show the radio group yet"),
         warn=True)

    y = pin(s, COL[4], PIN, "CR-P3FU83-01", "major",
            ("the failure tail showed stdout:", "`out` was the first rule log"),
            "fixed in 6fee0092: `err` first")
    y = pin(s, COL[4], y + 10, "CR-P3FU83-02", "major",
            ("on SLURM, errors left the job log", "once `2>` took all of stderr"),
            "fixed in 6fee0092: the `tee`")
    y = pin(s, COL[4], y + 10, "CR-P3FU83-R2-03", "major",
            ("spec and Snakefile header still said", "the job log gets nothing"),
            "fixed in dcda5b62, not re-reviewed", warn=True)
    note(s, COL[4], y + 10, ("open, minor: CR-P3FU83-04, -R2-04,", "-R2-05; SEC-P3FU83-01, an",
                             "unchecked `verbosity` in `main.nf`"))

    # == the batch simplifier, before and after; the tests =====================================
    band(s, LOW - 22, "batch simplify, before and after · 2 commits, 2 files, -12 +4 · "
         "re-review not needed")

    # the recorded-root check, one function
    x, y = 50, LOW + 8
    s.text(x, y + 10, "the recorded-root check, `files/taskfiles.py`", size=13.5, anchor="start",
           weight="bold")
    s.text(x, y + 40, "before", size=12.5, anchor="start", colour=t.dim)
    for i, fn in enumerate(("`_check_recorded`", "`_same_dir`")):
        px = x + 60 + i * 190
        s.page(px, y + 24, 30, 40, fill="surface", lines=2)
        s.text(px + 38, y + 48, fn, size=11.5, anchor="start")
    s.cross(x + 250 + 15, y + 44, size=9)
    s.text(x, y + 112, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 60, y + 96, 30, 40, fill="done", lines=2)
    s.text(x + 98, y + 120, "`_check_recorded`", size=11.5, anchor="start")
    s.text(x, y + 168, "80717b05: one caller, folded in; a `from None`", size=12.5, anchor="start")
    s.text(x, y + 188, "outside any `except` dropped; same comparison,", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, y + 208, "same error", size=12.5, anchor="start", colour=t.dim)

    # the dead CSS rule
    x = 560
    s.text(x, y + 10, "a dead rule, `web/src/runs/runs.css`", size=13.5, anchor="start", weight="bold")
    s.page(x, y + 24, 60, 76, fill="surface", lines=3)
    s.text(x + 76, y + 50, "`.sp-sheet-row .sp-chip`", size=11.5, anchor="start")
    s.text(x + 76, y + 70, "`margin: 0`", size=11.5, anchor="start")
    s.line(x + 72, y + 46, x + 266, y + 46, colour=t.accent, passes=1, width=1.8)
    s.line(x + 72, y + 66, x + 160, y + 66, colour=t.accent, passes=1, width=1.8)
    s.text(x + 76, y + 96, "no chip left in a sheet row", size=12, anchor="start", colour=t.dim)
    s.text(x, y + 132, "f3dca797: the open simplify finding of", size=12.5, anchor="start")
    s.text(x, y + 152, "P3-fu80; checked in `DetailSheet.tsx` and", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, y + 172, "`TaskFiles.tsx`", size=12.5, anchor="start", colour=t.dim)
    s.text(x, y + 200, "left alone: the type checks of", size=12.5, anchor="start")
    s.text(x, y + 220, "`_pipeline_order`, the payload comes", size=12.5, anchor="start", colour=t.dim)
    s.text(x, y + 240, "from a plugin; CR-P3FU82-03, a UI choice", size=12.5, anchor="start",
           colour=t.dim)

    # tests, to scale
    x = 1000
    k = 0.3  # px per test
    s.text(x, y + 10, "tests, to scale", size=13.5, anchor="start", weight="bold")
    s.text(x + 128, y + 10, f"{k} px per test", size=12.5, anchor="start", colour=t.dim)
    rows_t = (("pytest, before", 1143, "1143 passed, all", "bar_green"),
              ("pytest, after", 713, "713, the server only", "bar_green"),
              ("vitest", 330, "330 passed", "bar_blue"))
    for i, (label, n, txt, fill) in enumerate(rows_t):
        by = y + 26 + i * 32
        s.text(x, by + 16, label, size=12.5, anchor="start")
        bar(s, x + 108, by, n * k, 20, fill)
        s.text(x + 116 + n * k, by + 16, txt, size=12.5, anchor="start")
    s.text(x + 108, y + 136, "pytest before: and 1 skipped, 30 deselected", size=12, anchor="start",
           colour=t.dim)
    s.warning(x + 8, y + 160, size=8)
    s.text(x + 24, y + 165, "after the edits only `packages/spectio-server`", size=12.5,
           anchor="start")
    s.text(x + 24, y + 185, "was re-run: the full suite overlapped them", size=12.5, anchor="start",
           colour=t.dim)
    s.tick(x + 8, y + 210, size=6)
    s.text(x + 24, y + 215, "vitest, `tsc`, ruff, format, mypy, lint-imports,", size=12.5,
           anchor="start")
    s.text(x + 24, y + 235, "`uv lock`: the same, before and after", size=12.5, anchor="start",
           colour=t.dim)

    s.prefix_key(50, H - 50, ("CR", "SEC"))
    s.text(W - 50, H - 18, "source: web/src shell and runs, files/taskfiles.py, api/taskfiles.py, "
           "api/runs_read.py, tests/pipelines/synthetic at f3dca797 · review records P3-fu79 to "
           "P3-fu83", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b08-login1-followups")
