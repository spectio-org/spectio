#!/usr/bin/env python3
"""The Environments screens, the Launch aside and three fixes from Thomas's try: batch P3-B11
(steps P3-fu86f, P3-fu86g, P3-fu86h, P3-fu109, wave W5), 2026-11-09.

Writes docs/assets/diagrams/p3-b11-environments-screens_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B11 at 45cc279c (PRs 209, 211, 213 and 214 merged into
autopilot/integration between d2147ede and b35198e2, then the batch code-simplifier's commit
45cc279c). The names mylab-long, gpu-test, htc and demo-hpc-login1 are the example values of the
boards (LiteEnvironments, LiteRunDetail) and of the demo host; the code does not hold them.
- 1, P3-fu86f, PR 209: web/src/environments/EnvironmentsPage.tsx (chips SLURM, Local, Default,
  Built-in; Edit and Delete only when not `builtin`; Make default when not default and usable;
  the DeleteAsk dialog "Delete <name>?", "Runs that used it keep their settings.", Cancel, Reload
  after a 412 or `environments-file-changed`; WAITS: a `refused`, `invalid` or `unreachable` file
  makes every action `aria-disabled`, described by `env-waits`; the phone card is one link, the
  page's group "More for this environment"; "Saved in" the file's path); EnvironmentForm.tsx
  (a rule shows under its field once typed in, a 422 lands on its field, other errors in a
  `role="alert"` banner); fields.ts `summary()` ("partition htc · 2 h per job · 8 GiB per job");
  routes.tsx and static.py: `/environments`, `/environments/new?from=`, `/environments/{name}`;
  record docs/reviews/code/P3-fu86f.md (majors CR-P3FU86F-01, -02, round 1, fixed in 99915676);
- 2, P3-fu86g, PR 211: web/src/launch/EnvironmentRow.tsx (one usable: a text row "Environment:
  ..."; two to six: radio cards; more: a native select; only `usable` ones offered, the rest "Not
  offered: ..."; New environment opens the shared form, "Save and choose it", and the dialog stays
  mounted while the list reloads, CR-P3FU86G-03); LaunchPage.tsx `chosen` (the user's, else the
  default); RunHeader.tsx `environmentFacts` (the run's own snapshot, never `GET /version`);
  ResumeDialog.tsx `whereWords` ("Runs on <name> as before."; "Its recorded environment cannot
  be read."); record P3-fu86g.md (blocker CR-P3FU86G-01 fixed in 0f6b9c7e, major CR-P3FU86G-02
  split out to FU-P3-86h);
- 3, P3-fu86h, PR 213: LaunchPage.tsx the aside's Summary (Pipeline, Engine, Environment, Engine
  head, Tasks, Run directory; "Not chosen yet"), `reasons()` and "Before Launch" ("Choose the
  engine", "Choose where it runs", "Fill the required field: <key>", "Nothing is missing.", the
  outdir warning that does not block), `focusField` and FoldSection `reveal`, both Launch buttons
  `aria-describedby="launch-missing"`, the preview `defaultOpen={false}`; record P3-fu86h.md
  (no blocker, no major; CR-P3FU86H-01, -02, -04 fixed in 0aced17f);
- 4, P3-fu109, PR 214: RunDetailPage.tsx `navigate` without `replace` (the vitest "Back and
  Forward step through the tabs and log sources": Summary, Logs with Engine log, Logs with Head
  errors, Parameters); spectio_server/api/workflows.py `EngineVersions` (`warm()` from serve.py
  at server start, both engines through a ThreadPoolExecutor, a stale answer returned while one
  background refresh runs, VERSIONS_TTL_S 300.0, VERSIONS_FAILED_TTL_S 10.0); TryPipelines.tsx
  `isSynthetic` and "Test pipeline"; runs.css `minmax(0, 1fr)` and `overflow-wrap: anywhere`,
  the ellipsis removed; record P3-fu109.md (major CR-P3FU109-01, fixed in a01fdc2f);
- lines per step: `git show --shortstat <merge> -- . ':!docs' ':!.autopilot'` for a4f22ad6,
  be551cfc, f5d132a9 and b35198e2; the simplifier: `git show --shortstat 45cc279c` (+2 -2);
- tests: before the batch, the P3-B10 record (pytest 1424 passed, the simplifier's run; vitest
  465 passed, doc-writer's run); after, the P3-B11 gate re-run by doc-writer on the final tree
  6a829ea2 (pytest 1429 passed, vitest 519 passed, ruff, mypy, lint-imports, tsc clean; docs/
  reviews/code/P3-B11.md "Gate"). The Playwright specs were not run there.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1940, 1510
COLS = (45, 520, 995, 1470)
CW = 430
TOP = 150  # the pictograms
CAP = 640  # the step captions
PIN = 790  # the pinned findings
LOW = 1120  # the simplifier and the bars


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, rows: tuple[str, ...], status: str,
        *, w: float = CW) -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it was closed."""
    h = 32 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 14, y + 13, size=5.5)
    s.text(x + 27, y + 18, fid, size=12, anchor="start", weight="bold")
    s.text(x + w - 8, y + 18, tag, size=11.5, anchor="end",
           colour=s.t.accent if "blocker" in tag else s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 10, y + 39 + i * 19, row, size=12.5, anchor="start")
    s.text(x + 10, y + 39 + len(rows) * 19, status, size=12.5, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = CW,
         warn: bool = False) -> float:
    """A dashed note: the rounds and what is open."""
    h = 12 + 20 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 22 if warn else 0
    if warn:
        s.warning(x + 17, y + 18, size=7.5)
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 23 + i * 20, row, size=12.5, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def tag(s: Sketch, x: float, y: float, w: float, label: str, fill: str = "neutral",
        *, h: float = 17, size: float = 10.5) -> float:
    """A small chip, as the screens draw SLURM, Default or Built-in."""
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size)
    return x + w + 5


def btn(s: Sketch, x: float, y: float, w: float, label: str, fill: str = "surface",
        *, h: float = 20, size: float = 10.5, dim: bool = False) -> None:
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size, colour=s.t.dim if dim else None)


def radio(s: Sketch, cx: float, cy: float, on: bool) -> None:
    s.circle(cx, cy, 5, fill="surface", width=1.1)
    if on:
        s.dot(cx, cy, 2.6)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    if w <= 0:
        return
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.0)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=111)
    t = theme
    s.heading(50, 56, "Batch P3-B11 · the Environments screens, the Launch aside, three fixes",
              "steps P3-fu86f, -86g, -86h and P3-fu109, PRs 209, 211, 213, 214 · ui-spec 4.6 and "
              "4.8.1, api 5.4 · example names from the boards")
    band(s, TOP - 22, "the four steps, in merge order")

    # == 1 · the Environments pages ================================================================
    x, y = COLS[0], TOP
    s.browser(x, y, 300, 318, url="/environments")
    s.text(x + 14, y + 54, "Environments", size=15, anchor="start", weight="bold")
    btn(s, x + 186, y + 40, 104, "New environment", "input")
    cards = (("mylab-long", ("SLURM", "Default"), "partition htc · 2 h per job · 8 GiB per job",
              ("Edit", "Duplicate", "Delete")),
             ("gpu-test", ("SLURM",), "partition gpu · 30 min per job",
              ("Edit", "Duplicate", "Make default", "Delete")),
             ("Login node", ("Local", "Built-in"), "on demo-hpc-login1 (the login node)",
              ("Duplicate", "Make default")))
    for i, (name, chips, line, actions) in enumerate(cards):
        cy = y + 68 + i * 80
        cell(s, x + 10, cy, 280, 72, "done" if "Default" in chips else "surface")
        s.text(x + 20, cy + 18, name, size=12.5, anchor="start", weight="bold")
        cx = x + 104
        for c in chips:
            cx = tag(s, cx, cy + 5, 50 if c != "Built-in" else 56, c)
        s.text(x + 20, cy + 38, line, size=10.5, anchor="start", colour=t.dim)
        ax = x + 20
        for a in actions:
            w = 22 + len(a) * 4.6
            btn(s, ax, cy + 46, w, a, "problem" if a == "Delete" else "surface", h=18, size=10)
            ax += w + 6
    s.text(x + 14, y + 308, "Saved in, and the file's path", size=10.5,
           anchor="start", colour=t.dim)

    # the phone: a card is one link, the actions are on its page
    px = x + 318
    s.phone(px, y + 6, 104, 196)
    cell(s, px + 10, y + 34, 84, 36, "done")
    s.text(px + 52, y + 50, "mylab-long", size=10.5)
    s.link(px + 52, y + 62, size=8)
    s.arrow(px + 52, y + 76, px + 52, y + 94, colour=t.dim)
    s.text(px + 52, y + 108, "More for this", size=9.5, colour=t.dim)
    s.text(px + 52, y + 120, "environment", size=9.5, colour=t.dim)
    for j, (a, f) in enumerate((("Duplicate", "surface"), ("Delete", "problem"))):
        btn(s, px + 12, y + 130 + j * 24, 80, a, f, h=19, size=9.5)
    s.text(px + 52, y + 222, "the phone: a card", size=11, colour=t.dim)
    s.text(px + 52, y + 238, "is one link", size=11, colour=t.dim)

    # Delete asks first
    dy = y + 334
    cell(s, x, dy, 262, 96, "surface")
    s.text(x + 12, dy + 22, "Delete gpu-test?", size=13, anchor="start", weight="bold")
    s.text(x + 12, dy + 44, "Runs that used it keep their settings.", size=11, anchor="start",
           colour=t.dim)
    btn(s, x + 12, dy + 62, 64, "Cancel")
    btn(s, x + 84, dy + 62, 110, "Delete gpu-test", "problem")
    s.text(x + 200, dy + 76, "or Reload", size=10.5, anchor="start", colour=t.dim)
    s.warning(x + 290, dy + 16, size=9)
    s.text(x + 306, dy + 21, "the file `refused`,", size=11.5, anchor="start")
    s.text(x + 306, dy + 39, "`invalid`, `unreachable`:", size=11.5, anchor="start")
    s.text(x + 284, dy + 60, "every action waits", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 284, dy + 78, "and says why", size=11.5, anchor="start", colour=t.dim)

    s.step(x + CW / 2, CAP, 1, "the Environments pages")
    lines(s, x, CAP + 30, ("list, form, Delete and Make default, three routes",
                           "a built-in has no Edit and no Delete, only Duplicate",
                           "a rule shows under its field as soon as it is typed",
                           "a server 422 lands on its field; Save says why it waits",
                           "a 412 or a changed file: Reload, in place"))
    yy = pin(s, x, PIN, "CR-P3FU86F-01", "r1 major",
             ("the phone: a card as one link, the actions", "on its page, one shared `DeleteAsk`"),
             "fixed in `99915676`, verified r2")
    yy = pin(s, x, yy + 10, "CR-P3FU86F-02", "r1 major",
             ("a 422 on a field the form does not show",),
             "fixed in `99915676`: a `role=alert` banner")
    note(s, x, yy + 10, ("open, minor: CR-P3FU86F-03 to -05 simplify,",
                         "-09 a Playwright gap, -10 branch behind base;",
                         "SEC-P3FU86F-01 a spec with no cleanup, -02"))

    # == 2 · an Environment at Launch and on the run ===============================================
    x, y = COLS[1], TOP
    s.text(x, y + 10, "Launch, Where it runs: by how many are usable", size=13, anchor="start",
           weight="bold")
    vw, vg = 136, 11
    # one usable: a text row
    vx = x
    cell(s, vx, y + 24, vw, 92, "input")
    s.text(vx + 8, y + 46, "Environment:", size=11, anchor="start")
    s.text(vx + 8, y + 64, "mylab-long · partition", size=10.5, anchor="start", colour=t.dim)
    s.text(vx + 8, y + 80, "htc · 2 h per job", size=10.5, anchor="start", colour=t.dim)
    s.text(vx + vw / 2, y + 136, "1: a text row", size=12, colour=t.dim)
    # two to six: radio cards
    vx = x + vw + vg
    cell(s, vx, y + 24, vw, 92, "input")
    for j, (name, on) in enumerate((("mylab-long", True), ("gpu-test", False), ("Login node", False))):
        ry = y + 42 + j * 26
        radio(s, vx + 14, ry, on)
        s.text(vx + 26, ry + 4, name, size=11, anchor="start")
    tag(s, vx + 96, y + 34, 34, "SLURM", h=15, size=8.5)
    s.text(vx + vw / 2, y + 136, "2 to 6: radio cards", size=12, colour=t.dim)
    # more: a native select
    vx = x + 2 * (vw + vg)
    cell(s, vx, y + 24, vw, 92, "input")
    s.text(vx + 8, y + 46, "Environment", size=11, anchor="start")
    cell(s, vx + 8, y + 56, vw - 16, 24, "surface")
    s.text(vx + 14, y + 72, "mylab-long, SLURM", size=10.5, anchor="start")
    s.line(vx + vw - 24, y + 66, vx + vw - 19, y + 71, passes=1, amount=0.2)
    s.line(vx + vw - 19, y + 71, vx + vw - 14, y + 66, passes=1, amount=0.2)
    s.text(vx + 8, y + 100, "and its summary", size=10.5, anchor="start", colour=t.dim)
    s.text(vx + vw / 2, y + 136, "7 or more: a select", size=12, colour=t.dim)

    # New environment: the shared form in a dialog
    fy = y + 160
    btn(s, x, fy + 30, 124, "New environment", "input", h=24, size=11.5)
    s.arrow(x + 130, fy + 42, x + 170, fy + 42)
    cell(s, x + 178, fy, 252, 116, "surface")
    s.text(x + 190, fy + 20, "New environment", size=12.5, anchor="start", weight="bold")
    for j, f in enumerate(("Name", "Partition", "Time per job")):
        s.text(x + 190, fy + 42 + j * 20, f, size=10.5, anchor="start", colour=t.dim)
        cell(s, x + 270, fy + 31 + j * 20, 148, 14, "neutral")
    btn(s, x + 300, fy + 90, 118, "Save and choose it", "done", h=19, size=10)
    s.text(x, fy + 84, "the form of the pages;", size=11.5, anchor="start", colour=t.dim)
    s.text(x, fy + 101, "a failed Reload keeps", size=11.5, anchor="start", colour=t.dim)
    s.text(x, fy + 118, "its values", size=11.5, anchor="start", colour=t.dim)

    # Run detail: the run's own snapshot
    ry = y + 296
    s.browser(x, ry, 300, 134, url="/runs/run ID")
    s.text(x + 12, ry + 52, "Environment", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 100, ry + 52, "mylab-long", size=12, anchor="start", weight="bold")
    tag(s, x + 178, ry + 40, 44, "SLURM", h=16, size=9.5)
    s.text(x + 100, ry + 70, "partition htc · 2 h per job", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 12, ry + 92, "Executor", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 100, ry + 92, "SLURM", size=12, anchor="start")
    s.text(x + 12, ry + 120, "Resume: Runs on mylab-long as before.", size=11, anchor="start")
    s.page(x + 324, ry + 6, 40, 50, fill="docs", lines=3)
    s.tick(x + 356, ry + 48, size=6)
    s.text(x + 344, ry + 74, "the run's", size=11, colour=t.dim)
    s.text(x + 344, ry + 89, "snapshot", size=11, colour=t.dim)
    s.arrow(x + 318, ry + 40, x + 290, ry + 54, colour=t.dim)
    s.cross(x + 344, ry + 108, size=8)
    s.text(x + 362, ry + 113, "`GET /version`", size=10.5, anchor="start", colour=t.dim)

    s.step(x + CW / 2, CAP, 2, "an Environment on Launch and Run")
    lines(s, x, CAP + 30, ("Launch offers the usable ones; the rest: Not offered",
                           "the default is chosen until you pick another",
                           "New environment saves, lists it again and chooses it",
                           "Run detail names the run's own environment",
                           "unreadable: Resume waits, the reason said"))
    yy = pin(s, x, PIN, "CR-P3FU86G-01", "r1 blocker",
             ("`shell.test.tsx` stubbed every URL with", "VERSION: `listEnvironments()` on Launch threw"),
             "fixed in `0f6b9c7e`: the stub routes by URL")
    yy = pin(s, x, yy + 10, "CR-P3FU86G-02", "r1 major",
             ("the board's aside summary and Before", "Launch list were missing"),
             "split out: built in step 3, FU-P3-86h")
    s.arrow(x + CW + 4, yy - 40, COLS[2] - 6, yy - 40, dashed=True, colour=t.dim)
    note(s, x, yy + 10, ("open, minor: CR-P3FU86G-05, -06 a test title,",
                         "an indent; -07 board differences, disclosed"))

    # == 3 · the Launch aside ======================================================================
    x, y = COLS[2], TOP
    s.browser(x, y, CW, 452, url="/launch")
    s.text(x + 14, y + 56, "Launch", size=16, anchor="start", weight="bold")
    btn(s, x + 344, y + 40, 74, "Launch", "neutral", h=24, size=12, dim=True)
    # the left: folded sections
    lx, lw = x + 12, 196
    cell(s, lx, y + 76, lw, 128, "input")
    s.text(lx + 10, y + 96, "Pipeline", size=12.5, anchor="start", weight="bold")
    s.text(lx + 10, y + 116, "rnaseq, loaded", size=11, anchor="start", colour=t.dim)
    s.text(lx + 10, y + 140, "Engine", size=11, anchor="start", colour=t.dim)
    s.shade(lx + 6, y + 148, 176, 32, fill="gate", opacity=0.9, colour=t.accent)
    btn(s, lx + 12, y + 154, 76, "Nextflow", h=20, size=10.5)
    btn(s, lx + 96, y + 154, 80, "Snakemake", h=20, size=10.5)
    s.text(lx + 10, y + 196, "focus moves here", size=10.5, anchor="start", colour=t.accent)
    cell(s, lx, y + 212, lw, 34, "input")
    s.text(lx + 10, y + 234, "Where it runs", size=12.5, anchor="start", weight="bold")
    s.text(lx + lw - 12, y + 234, "open", size=10.5, anchor="end", colour=t.dim)
    cell(s, lx, y + 254, lw, 34, "neutral")
    s.text(lx + 10, y + 276, "Parameters", size=12.5, anchor="start", weight="bold")
    s.text(lx + lw - 12, y + 276, "folded", size=10.5, anchor="end", colour=t.dim)
    s.text(lx, y + 312, "a link opens the folded", size=11, anchor="start", colour=t.dim)
    s.text(lx, y + 328, "sections of its field first", size=11, anchor="start", colour=t.dim)
    # the aside: Summary and Before Launch
    ax, aw = x + 220, 198
    cell(s, ax, y + 76, aw, 180, "surface")
    s.text(ax + 10, y + 96, "Summary", size=13, anchor="start", weight="bold")
    rows = (("Pipeline", "rnaseq"), ("Engine", "Not chosen yet"),
            ("Environment", "mylab-long · SLURM"), ("Engine head", "a tmux session on"),
            ("", "demo-hpc-login1"), ("Tasks", "sent to SLURM by the"), ("", "engine · partition htc"),
            ("Run directory", "runs root, run ID"))
    for j, (k, v) in enumerate(rows):
        s.text(ax + 10, y + 116 + j * 17, k, size=9.5, anchor="start", colour=t.dim)
        s.text(ax + 82, y + 116 + j * 17, v, size=9.5, anchor="start")
    cell(s, ax, y + 266, aw, 110, "gate")
    s.text(ax + 10, y + 286, "Before Launch", size=12.5, anchor="start", weight="bold")
    reasons = ("Choose the engine", "Fill the required field:", "input")
    s.text(ax + 12, y + 308, "· " + reasons[0], size=11, anchor="start", colour=t.accent)
    s.line(ax + 22, y + 311, ax + 128, y + 311, colour=t.accent, passes=1, amount=0.2, width=1)
    s.text(ax + 12, y + 330, "· " + reasons[1], size=11, anchor="start", colour=t.accent)
    s.text(ax + 22, y + 346, reasons[2], size=11, anchor="start", colour=t.accent)
    s.text(ax + 12, y + 366, "a warning that does not block", size=9.5, anchor="start", colour=t.dim)
    s.arc(ax + 6, y + 306, lx + lw - 10, y + 166, lift=-30, colour=t.accent)
    btn(s, ax, y + 388, aw, "Launch", "neutral", h=26, size=12, dim=True)
    # both buttons are described by the list
    s.line(x + 410, y + 64, x + 424, y + 80, dashed=True, colour=t.dim, passes=1, amount=0.3)
    s.line(x + 424, y + 80, x + 424, y + 300, dashed=True, colour=t.dim, passes=1, amount=0.3)
    s.line(x + 424, y + 300, ax + aw, y + 300, dashed=True, colour=t.dim, passes=1, amount=0.3)
    s.line(ax + aw / 2, y + 388, ax + aw / 2, y + 376, dashed=True, colour=t.dim, passes=1)
    s.text(ax + aw / 2, y + 436, "both described by the list", size=11, colour=t.dim)

    s.step(x + CW / 2, CAP, 3, "the Launch aside")
    lines(s, x, CAP + 30, ("Summary: pipeline, engine, environment, head, tasks",
                           "Before Launch lists every reason Launch waits",
                           "a reason is a link: its section opens, focus moves",
                           "none left: Nothing is missing.",
                           "the preview in the aside is folded at first"))
    yy = note(s, x, PIN, ("no blocker, no major: round 1 approve, 6 minors",
                          "CR-P3FU86H-01, a link into a folded group with",
                          "a server error; -02, the Environment row; -04:",
                          "fixed in `0aced17f`, -01 and -02 test first"))
    note(s, x, yy + 10, ("open, minor: CR-P3FU86H-03 engine text written",
                         "twice; -05 no test of Choose where it runs and",
                         "no browser run; -06 inbox 146 item 2, later"))

    # == 4 · three fixes from Thomas's try =========================================================
    x, y = COLS[3], TOP
    # a) the pager follows the URL
    s.text(x, y + 10, "each view is a history entry", size=13, anchor="start", weight="bold")
    views = (("Summary", ""), ("Logs", "Engine log"), ("Logs", "Head errors"), ("Parameters", ""))
    vw = 98
    for j, (tab, src) in enumerate(views):
        vx = x + j * (vw + 13)
        s.page(vx, y + 24, vw, 58, fill="input" if j < 3 else "done", lines=0)
        s.text(vx + vw / 2 - 4, y + 46, tab, size=11.5, weight="bold")
        if src:
            s.text(vx + vw / 2 - 4, y + 66, src, size=10, colour=t.dim)
        if j < 3:
            s.arrow(vx + vw + 1, y + 46, vx + vw + 12, y + 46, colour=t.dim)
    s.arc(x + 3 * (vw + 13) + 30, y + 88, x + 30, y + 88, lift=26, colour=t.accent)
    s.text(x + 215, y + 128, "Back steps through them, Forward again", size=11.5,
           colour=t.accent)

    # b) the engines' versions, off the request path
    by = y + 152
    s.text(x, by, "the engines' versions, off the first click", size=13, anchor="start",
           weight="bold")
    s.hpc_node(x, by + 14, 40, 54, busy=2)
    s.text(x + 48, by + 30, "`warm()` at", size=11, anchor="start")
    s.text(x + 48, by + 46, "server start", size=11, anchor="start", colour=t.dim)
    for j, eng in enumerate(("Nextflow", "Snakemake")):
        ly = by + 20 + j * 24
        s.text(x + 136, ly + 12, eng, size=11, anchor="start")
        cell(s, x + 206, ly, 150, 16, "work")
    s.text(x + 362, by + 34, "both at", size=11, anchor="start", colour=t.dim)
    s.text(x + 362, by + 50, "once", size=11, anchor="start", colour=t.dim)
    # the time an answer is kept, to scale
    k = 1.3  # px per second
    ty = by + 92
    s.text(x, ty, f"kept, to scale, {k} px a second", size=11, anchor="start", colour=t.dim)
    bar(s, x, ty + 8, 300 * k, 16, "bar_green")
    s.text(x + 300 * k + 6, ty + 21, "300 s", size=11, anchor="start")
    s.text(x + 6, ty + 21, "both found", size=10.5, anchor="start")
    bar(s, x, ty + 30, 10 * k, 16, "bar_orange")
    s.text(x + 10 * k + 6, ty + 43, "10 s, an engine not found", size=11, anchor="start")
    s.text(x, ty + 70, "after that: the stale answer at once, and one", size=11.5, anchor="start")
    s.text(x, ty + 86, "refresh behind it; only the very first call waits", size=11.5,
           anchor="start", colour=t.dim)

    # c) Home and the test pipelines
    hy = y + 352
    s.text(x, hy, "Home and Launch", size=13, anchor="start", weight="bold")
    cell(s, x, hy + 12, 196, 72, "surface")
    s.text(x + 8, hy + 30, "`/g/demo-lab/a-very-long-`", size=10.5, anchor="start")
    s.text(x + 8, hy + 46, "`directory-name-without-`", size=10.5, anchor="start")
    s.text(x + 8, hy + 62, "`any-break/rnaseq`", size=10.5, anchor="start")
    s.tick(x + 184, hy + 74, size=5.5)
    s.text(x + 98, hy + 100, "wraps, shown whole", size=11, colour=t.dim)
    cell(s, x + 214, hy + 12, 216, 34, "input")
    s.text(x + 226, hy + 34, "Test pipeline", size=12, anchor="start", weight="bold")
    s.text(x + 318, hy + 34, "synthetic", size=10, anchor="start", colour=t.dim)
    s.text(x + 214, hy + 64, "named Test pipeline, with or", size=11, anchor="start", colour=t.dim)
    s.text(x + 214, hy + 80, "without a trailing slash", size=11, anchor="start", colour=t.dim)

    s.step(x + CW / 2, CAP, 4, "three fixes from Thomas's try")
    lines(s, x, CAP + 30, ("the URL is the source of truth for tab and log source",
                           "two login shells checked at once, not one by one",
                           "a check that failed is retried after 10 s, not 5 min",
                           "Home's long paths no longer run past the page",
                           "inbox 146, items 1 and 3"))
    yy = pin(s, x, PIN, "CR-P3FU109-01", "r1 major",
             ("the inspect ran both login-shell version", "checks one after the other, on the first click"),
             "fixed in `a01fdc2f`: `EngineVersions`, verified r2")
    note(s, x, yy + 10, ("first-click time on login1 not measured,",
                         "to be validated"), warn=True)
    note(s, x, yy + 74, ("open, minor: SEC-P3FU109-01, the shipped-with",
                         "label comes from a name anyone can set"))
    s.tick(x + 6, yy + 142, size=6)
    s.text(x + 20, yy + 147, "closed by the docs PR: CR-P3FU109-02,", size=12, anchor="start")
    s.text(x + 20, yy + 165, "ui-spec 4.4 now says a tab change adds", size=12, anchor="start",
           colour=t.dim)
    s.text(x + 20, yy + 183, "a history entry", size=12, anchor="start", colour=t.dim)

    for a, b in zip(COLS[:3], COLS[1:]):
        s.arrow(a + CW + 6, CAP - 6, b - 8, CAP - 6, colour=t.muted)

    # == the batch simplifier, the lines and the tests =============================================
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: not "
         "needed")
    y0 = LOW + 6

    x = 50
    s.text(x, y0 + 12, "`45cc279c`, `web/src/launch/TryPipelines.tsx`", size=13.5, anchor="start",
           weight="bold")
    s.text(x, y0 + 38, "before", size=12.5, anchor="start", colour=t.dim)
    s.page(x, y0 + 48, 236, 100, fill="surface", lines=0)
    cell(s, x + 8, y0 + 66, 212, 22, "problem")
    s.text(x + 16, y0 + 81, "`const ENGINE` a 4th name map", size=11, anchor="start")
    cell(s, x + 8, y0 + 96, 212, 22, "problem")
    s.text(x + 16, y0 + 111, "`ENGINE[w.engine] ?? w.engine`", size=11, anchor="start")
    s.arrow(x + 244, y0 + 98, x + 272, y0 + 98)
    s.text(x + 280, y0 + 38, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 280, y0 + 48, 236, 100, fill="done", lines=0)
    cell(s, x + 288, y0 + 66, 212, 22, "done")
    s.text(x + 296, y0 + 81, "`import engineName`", size=11, anchor="start")
    cell(s, x + 288, y0 + 96, 212, 22, "done")
    s.text(x + 296, y0 + 111, "`engineName(w.engine)`", size=11, anchor="start")
    lines(s, x, y0 + 176, ("+2 -2 in 1 file · closes CR-P3FU109-04, the same label:",
                           "it is built only when the engine is set, and both",
                           "fall back to the raw name",
                           "left alone: `NAMES` in LaunchPage.tsx, a line outside",
                           "the diff, likely CR-P3FU86H-03; `EngineVersions`'",
                           "`clock` and `spawn`, kept as test seams"), size=12)

    # the lines changed per step, to scale
    x = 640
    k = 0.3  # px per line
    s.text(x, y0 + 12, f"lines per step outside docs, to scale, {k} px a line", size=13.5,
           anchor="start", weight="bold")
    sizes = ((1, "P3-fu86f", 1232, 11), (2, "P3-fu86g", 870, 160), (3, "P3-fu86h", 273, 37),
             (4, "P3-fu109", 252, 25), (5, "simplify", 2, 2))
    mid = x + 200
    for i, (n, name, add, rem) in enumerate(sizes):
        ry = y0 + 34 + i * 30
        label = f"{n} `{name}`" if n < 5 else "the simplifier"
        s.text(mid - 4 - max(rem * k, 0) - 8, ry + 14, label, size=12, anchor="end", colour=t.dim)
        bar(s, mid - 2 - rem * k, ry, rem * k, 18, "problem")
        bar(s, mid + 2, ry, max(add * k, 1.5), 18, "done")
        s.text(mid + 10 + add * k, ry + 14, f"+{add} -{rem}", size=12, anchor="start")
    s.line(mid, y0 + 28, mid, y0 + 186, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 8, y0 + 204, "removed", size=11.5, anchor="end", colour=t.dim)
    s.text(mid + 8, y0 + 204, "added", size=11.5, anchor="start", colour=t.dim)
    s.text(x, y0 + 236, "steps 1 to 3 are web only; step 4 changes 79 lines of", size=12,
           anchor="start", colour=t.dim)
    s.text(x, y0 + 256, "`api/workflows.py`, adds 73 to `test_launch.py`", size=12,
           anchor="start", colour=t.dim)

    # the tests, to scale
    x = 1340
    k = 0.24  # px per test
    s.text(x, y0 + 12, f"tests passed, before and after, {k} px a test", size=13.5,
           anchor="start", weight="bold")
    runs_t = (("pytest", "before, P3-B10", 1424, "bar_blue"), ("", "after, P3-B11", 1429, "bar_blue"),
              ("vitest", "before, P3-B10", 465, "bar_green"), ("", "after, P3-B11", 519, "bar_green"))
    for i, (tool, label, n, fill) in enumerate(runs_t):
        ty = y0 + 34 + i * 30 + (10 if i >= 2 else 0)
        if tool:
            s.text(x, ty + 14, f"`{tool}`", size=12, anchor="start")
        s.text(x + 54, ty + 14, label, size=11.5, anchor="start", colour=t.dim)
        bar(s, x + 158, ty, n * k, 19, fill)
        s.text(x + 164 + n * k, ty + 14, f"{n}", size=12, anchor="start")
    s.tick(x + 6, y0 + 186, size=6)
    s.text(x + 20, y0 + 191, "full gate re-run on the final tree (`6a829ea2`):", size=12,
           anchor="start")
    s.text(x + 20, y0 + 209, "pytest 1429, ruff, format, mypy, lint-imports,", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 20, y0 + 227, "`uv lock --check`, vitest 519, `tsc --noEmit`", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 20, y0 + 255, "Playwright specs: not run here, ran in each PR's CI", size=12,
           anchor="start", colour=t.dim)

    s.text(50, H - 50, "pins: every blocker and major of the batch, all fixed or split out · r1, r2: "
           "code review rounds · security-reviewer: minors only, skipped on P3-fu86h", size=13.5,
           anchor="start", colour=t.dim)
    s.prefix_key(50, H - 26, ("CR", "SEC"))
    s.text(W - 50, H - 12, "source: web/src/environments, web/src/launch, web/src/runs, "
           "spectio_server api/workflows.py · review records P3-fu86f to P3-fu109", size=12,
           anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b11-environments-screens")
