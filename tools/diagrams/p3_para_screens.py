#!/usr/bin/env python3
"""UI parity A, the shell, Home, the runs list and the run: step P3-parA, 2026-10-31.

Writes docs/assets/diagrams/p3-para-screens_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-parA at 7a4811c2 (base 2785941f):
- 28a241cd: fixes UX-PAR-01 to 07, 11 to 27 and 29 of docs/reviews/ui-parity-0.0.1.md, engine
  marks only (no nf-core mark, inbox 91);
- web/src/shell/Sidebar.tsx: NAV Home (exact), Runs and Launch (also on the pages under them,
  UX-PAR-06); the Runs badge counts the ACTIVE groups of GET /runs:summary (UX-PAR-07); the foot
  "Spectio <version> · online" with a check icon;
- web/src/shell/PageHead.tsx: the 48 px icon tile, h1, sub line, action (UX-PAR-03);
- web/src/shell/FoldSection.tsx: h2 > button aria-expanded, icon tile, title, summary shown only
  while folded, chevron; open state kept in localStorage "spectio-open:<screen>:<id>" (UX-PAR-02);
- web/src/shell/EngineMark.tsx: the Nextflow and Snakemake marks, no nf-core mark (inbox 91);
- web/src/home/HomePage.tsx: count cards in CARD_ORDER, zero states hidden, each a Link to /runs
  with ?state= (UX-PAR-12), a detail line; Active runs, Finished recently, rows with data-rail and
  EngineMark; endedContext never blank (UX-PAR-16); Your pipelines; WhereRunsGo from GET /version
  (UX-PAR-11); "All runs" now to="/runs" with no state (ac5ae2ca, CR-P3PARA-02);
- web/src/runs/RunsPage.tsx: runsSearch keeps state and a non-empty q; setSearch(change) navigates
  with search (prev) => runsSearch({...prev, ...change}), replace; the name lands after 250 ms;
  `typed` is seeded once by useState(q) (R2 CR-P3PARA-09); segments with counts; TasksCell says
  "jobs" for Snakemake (UX-PAR-17);
- web/src/runs/RunHeader.tsx: the header card with data-rail, the mark tile, h1 and short ID, the
  state line, Cancel run, the Facts fold, the task chips (failed and retried always, UX-PAR-22);
  "Pipeline" fact as text only (CR-P3PARA-03); aria-label "Tasks by state" (CR-P3PARA-07);
- web/src/runs/RunDetailPage.tsx: tabs Summary, Tasks or Jobs, Parameters, Logs; WhyItFailed open
  first on a failed run (UX-PAR-25); stages and processes with Bar (UX-PAR-24); SummaryAside:
  HeadByHand only while the head is alive and not cli-observed, "ssh ${head.node}" and
  "tmux attach -t ${head.session}" unquoted (SEC-P3PARA-01), the LogTail, The head has ended,
  Parameters (UX-PAR-23); LogTail "Empty." once ended, "Empty so far." while running, lines through
  LogLines with data-tone from level() (ac5ae2ca, CR-P3PARA-04); Download: append the anchor to
  document.body, click, remove, revokeObjectURL in setTimeout 0 (ac5ae2ca, CR-P3PARA-08);
- web/src/runs/runs.css:750-755: the tint is `.sp-log span[data-tone=...]`; the tail's pre is
  `sp-code sp-log-tail`, not `sp-log`, so at 7a4811c2 the tail's data-tone is set but not styled
  (seen while checking this figure; not a review finding), so the figure draws the tail plain;
- a55c74d4 (CR-P3PARA-10, .sp-section selectors dropped) and 7a4811c2 (CR-P3PARA-11, one `sum` in
  stateWord.ts instead of three): the simplifier, 12 lines out, 8 in;
- the review rounds, from the step's worker report of 2026-10-31 (review record P3-parA):
  R1 CR approve 01 to 13, SEC approve 01; fixed CR-01, 02, 04 (the tint in part), 08 in ac5ae2ca,
  CR-10, 11 by the simplifier and CR-09 in the docs commit 2b4ef44 (tools/media/README.md:54
  documents SPECTIO_DEMO_FAILED_RUN), 7 of 14 ("Fixes by round" of the record); CR-04's tail tint
  stays open. R2 CR approve 09 and 10, SEC approve with none; none fixed. IDs repeat across rounds.
  Gate: vitest 89 passed, tsc and vite build clean; pytest 511 passed, ruff, mypy, lint-imports.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from sketch import MONO, Sketch, Theme, main_for

W, H = 1600, 1524
SCR = 132  # the screens, their browser windows
BH = 236  # browser height
COL = ((50, 300), (380, 360), (770, 360), (1160, 390))  # (x, width)
STEP = SCR + BH + 34
TXT = STEP + 30
PIN = TXT + 104
FIX = 912  # before and after
LOW = 1216  # the review rounds


# (round, (fixed in ac5ae2ca, by the simplifier, in the docs commit, left open), CR verdict, SEC verdict)
ROUNDS = (("R1", (4, 2, 1, 7), "approve", "approve"),
          ("R2", (0, 0, 0, 2), "approve", "approve"))
KINDS = (("done", "fixed, `ac5ae2ca`", 90), ("docs", "fixed, simplifier", 240),
         ("input", "fixed, docs commit", 390), ("neutral", "minor, left open", 550))  # (fill, legend, x)


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...], *, fixed: bool) -> float:
    """A finding pinned where it hits: a tick when the branch fixed it, a warning when it is open.

    Returns the y of the next pin."""
    if fixed:
        s.tick(x + 8, y - 5, size=7)
    else:
        s.warning(x + 8, y - 5, size=8)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)
    return y + 30 + len(rows) * 18


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, amount: float = 0.4) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=amount)


def stroke(s: Sketch, x1: float, y: float, x2: float, *, width: float = 1.4) -> None:
    """A ruled stroke standing for a line of text."""
    s.line(x1, y, x2, y, colour=s.t.muted, amount=0.3, passes=1, width=width)


def mark(s: Sketch, cx: float, cy: float, r: float = 6) -> None:
    """The engine's mark, a small round logo."""
    s.circle(cx, cy, r, fill="input")
    s.dot(cx, cy, r * 0.35, colour=s.t.dim)


def tile(s: Sketch, x: float, y: float, size: float, fill: str) -> None:
    """An icon tile: a tinted square with a light line icon."""
    bar(s, x, y, size, size, fill, amount=0.3)
    s.line(x + size * 0.28, y + size * 0.5, x + size * 0.72, y + size * 0.5, amount=0.2, passes=1, width=1.6)
    s.line(x + size * 0.5, y + size * 0.28, x + size * 0.5, y + size * 0.72, amount=0.2, passes=1, width=1.6)


def fold(s: Sketch, x: float, y: float, w: float, title: str, *, open_: bool = True, summary: str = "") -> None:
    """A FoldSection head: tile, title, the summary while folded, the chevron."""
    tile(s, x, y - 11, 16, "neutral")
    s.text(x + 22, y + 2, title, size=11.5, anchor="start", weight="bold")
    if summary and not open_:
        s.text(x + w - 22, y + 2, summary, size=11, anchor="end", colour=s.t.dim)
    s.text(x + w - 6, y + 3, "v" if open_ else ">", size=11.5, colour=s.t.dim)


def row(s: Sketch, x: float, y: float, w: float, rail: str, *, with_mark: bool = True) -> None:
    """A list row: a coloured state rail, the engine mark, then ruled strokes for its text."""
    bar(s, x, y, 5, 18, rail, amount=0.2)
    left = x + 12
    if with_mark:
        mark(s, x + 19, y + 9)
        left = x + 32
    stroke(s, left, y + 6, x + w * 0.58)
    stroke(s, left, y + 14, x + w * 0.42, width=1.1)
    stroke(s, x + w * 0.72, y + 9, x + w - 6)


def code(s: Sketch, x: float, y: float, w: float, rows: tuple[tuple[str, str | None], ...]) -> None:
    """The app's code surface (sp-code): monospace lines, each in its own colour."""
    h = 12 + len(rows) * 17
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{s.t.term_bg}"/>')
    for i, (text, colour) in enumerate(rows):
        s.raw(f'<text x="{x + 9:.1f}" y="{y + 19 + i * 17:.1f}" font-family="{MONO}" font-size="11.5" '
              f'fill="{colour or s.t.term_ink}" xml:space="preserve">{escape(text)}</text>')


def url_pill(s: Sketch, x: float, y: float, text: str, *, fill: str = "surface") -> None:
    w = 22 + len(text) * 7.3
    bar(s, x, y, w, 24, fill, amount=0.3)
    s.text(x + 11, y + 17, f"`{text}`", size=13.5, anchor="start")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=131)
    t = theme
    s.heading(50, 58, "P3 UI parity A · the shell, Home, the runs list and the run, against the Lite boards",
              "`web/src` only, within the 0.0.1 API · fixes UX-PAR-01 to 07, 11 to 27 and 29 of "
              "ui-parity-0.0.1 · the engine mark only, no nf-core mark yet, inbox 91")

    # 1 -- the shell -----------------------------------------------------------------------------
    x, cw = COL[0]
    s.browser(x, SCR, cw, BH, url="/runs/id")
    sx, sy = x + 6, SCR + 34
    s.shade(sx, sy, 92, BH - 40, fill="neutral", opacity=0.7, colour=t.muted)
    s.text(sx + 8, sy + 18, "Workspace", size=11, anchor="start", colour=t.dim)
    for i, name in enumerate(("Home", "Runs", "Launch")):
        y = sy + 34 + i * 30
        if name == "Runs":
            bar(s, sx + 4, y - 4, 84, 24, "input", amount=0.3)
            s.circle(sx + 76, y + 8, 8, fill="problem")
            s.text(sx + 76, y + 12, "2", size=11, weight="bold")
        bar(s, sx + 10, y + 1, 13, 13, "surface", amount=0.2)
        s.text(sx + 30, y + 13, name, size=12, anchor="start", weight="bold" if name == "Runs" else "normal")
    s.tick(sx + 14, sy + BH - 62, size=5)
    s.text(sx + 24, sy + BH - 58, "online", size=11, anchor="start", colour=t.good)
    mx, mw = x + 108, cw - 118
    s.text(mx, SCR + 50, "Runs  /  the run", size=11, anchor="start", colour=t.dim)
    tile(s, mx, SCR + 60, 30, "input")
    s.line(mx + 40, SCR + 70, mx + 150, SCR + 70, width=3, amount=0.3, passes=1)
    stroke(s, mx + 40, SCR + 84, mx + 170)
    fold(s, mx, SCR + 124, mw, "Facts")
    for j in range(2):
        stroke(s, mx + 4, SCR + 140 + j * 14, mx + mw * 0.45)
        stroke(s, mx + mw * 0.55, SCR + 140 + j * 14, mx + mw - 4)
    fold(s, mx, SCR + 186, mw, "Stages", open_=False, summary="8 stages")
    fold(s, mx, SCR + 214, mw, "Parameters", open_=False, summary="4 set")
    s.step(x + cw / 2, STEP, 1, "the shell")
    lines(s, x, TXT, ("Runs stays lit on a run's page, 06", "a badge counts the active runs, 07",
                      "page heads with a 48 px tile, 03", "sections fold, kept per screen, 02"))
    y = pin(s, x, PIN, "R1 CR-P3PARA-06", ("four role tokens in `theme.ts` are", "not in `spectio-tokens.css`"),
            fixed=False)
    y = pin(s, x, y, "R1 CR-P3PARA-05", ("the rail test passes by rule order,", "jsdom ignores specificity"),
            fixed=False)
    pin(s, x, y, "R1 CR-P3PARA-10", ("simplify: orphaned `.sp-section`", "rules, dropped, `a55c74d4`"),
        fixed=True)

    # 2 -- Home ----------------------------------------------------------------------------------
    x, cw = COL[1]
    bx, by = x, SCR
    s.browser(bx, by, cw, BH, url="/")
    tile(s, bx + 12, by + 38, 28, "done")
    s.text(bx + 48, by + 52, "Good morning", size=12.5, anchor="start", weight="bold")
    s.text(bx + 48, by + 66, "2 runs running and 1 queued", size=10.5, anchor="start", colour=t.dim)
    for i, (word, fill) in enumerate((("Running", "input"), ("Failed", "problem"), ("Succeeded", "done"))):
        cx = bx + 12 + i * 114
        bar(s, cx, by + 78, 106, 40, "surface", amount=0.3)
        bar(s, cx, by + 78, 5, 40, fill, amount=0.2)
        s.text(cx + 12, by + 93, word, size=11, anchor="start")
        s.line(cx + 12, by + 103, cx + 28, by + 103, width=2.6, amount=0.2, passes=1)
        stroke(s, cx + 12, by + 112, cx + 92, width=1.1)
    lx, lw = bx + 12, 196
    fold(s, lx, by + 138, lw, "Active runs")
    s.text(lx + lw - 20, by + 156, "All runs >", size=11, anchor="end", colour=t.accent)
    row(s, lx, by + 162, lw, "input")
    fold(s, lx, by + 200, lw, "Finished recently")
    row(s, lx, by + 210, lw, "problem")
    rx, rw = bx + 222, 126
    bar(s, rx, by + 126, rw, 50, "surface", amount=0.3)
    fold(s, rx + 6, by + 142, rw - 12, "Your pipelines")
    for j in range(2):
        mark(s, rx + 14, by + 156 + j * 12, r=4)
        stroke(s, rx + 24, by + 156 + j * 12, rx + rw - 10, width=1.1)
    bar(s, rx, by + 182, rw, 48, "surface", amount=0.3)
    fold(s, rx + 6, by + 198, rw - 12, "Where runs go")
    stroke(s, rx + 10, by + 212, rx + rw - 10, width=1.1)
    stroke(s, rx + 10, by + 222, rx + rw - 30, width=1.1)
    s.step(x + cw / 2, STEP, 2, "Home at `/`")
    lines(s, x, TXT, ("count cards by state, each a link to `/runs`", "a rail and the engine mark on each row",
                      "a failed run says why, never blank, 16", "Where your runs go, from `GET /version`"))
    pin(s, x, PIN, "R1 CR-P3PARA-02", ("All runs went to `/runs?state=active`,", "now to `/runs`, `ac5ae2ca`"),
        fixed=True)

    # 3 -- the runs list -------------------------------------------------------------------------
    x, cw = COL[2]
    bx = x
    s.browser(bx, by, cw, BH, url="/runs?state=failed&q=sar")
    tile(s, bx + 12, by + 38, 28, "input")
    s.text(bx + 48, by + 52, "Runs", size=12.5, anchor="start", weight="bold")
    stroke(s, bx + 48, by + 64, bx + 190)
    bar(s, bx + 12, by + 78, 120, 24, "surface", amount=0.3)
    s.magnifier(bx + 26, by + 89, 5)
    s.text(bx + 40, by + 95, "sar", size=12, anchor="start")
    words = (("All", 32), ("Active", 46), ("Failed", 46), ("Succeeded", 64), ("Cancelled", 62))
    gx = bx + 12
    for word, w in words:
        bar(s, gx, by + 112, w, 22, "problem" if word == "Failed" else "surface", amount=0.3)
        s.text(gx + w / 2, by + 127, word, size=10.5, weight="bold" if word == "Failed" else "normal")
        gx += w + 4
    for j in range(3):
        row(s, bx + 12, by + 146 + j * 24, cw - 24, "problem")
    s.text(bx + 12, by + 228, "3 runs · newest first", size=10.5, anchor="start", colour=t.dim)
    s.step(x + cw / 2, STEP, 3, "the runs list, `/runs`")
    lines(s, x, TXT, ("the state filter and the name, in the URL", "the name lands 250 ms after typing",
                      "each segment shows its count", "Snakemake runs counted in jobs, 17"))
    y = pin(s, x, PIN, "R1 CR-P3PARA-01", ("the name `q` was not kept in the URL;", "now it is, `ac5ae2ca`"),
            fixed=True)
    pin(s, x, y, "R2 CR-P3PARA-09", ("a Runs link drops `q`, but the box", "still shows sar over every run"),
        fixed=False)

    # 4 -- the run -------------------------------------------------------------------------------
    x, cw = COL[3]
    bx = x
    s.browser(bx, by, cw, BH, url="/runs/id")
    hx, hw = bx + 10, cw - 20
    bar(s, hx, by + 36, hw, 92, "surface", amount=0.3)
    bar(s, hx, by + 36, 5, 92, "problem", amount=0.2)
    bar(s, hx + 14, by + 44, 28, 28, "neutral", amount=0.3)
    mark(s, hx + 28, by + 58, r=8)
    s.line(hx + 52, by + 52, hx + 160, by + 52, width=3, amount=0.3, passes=1)
    s.text(hx + 170, by + 56, "a1b2c3", size=10.5, anchor="start", colour=t.dim)
    s.text(hx + 52, by + 70, "Failed", size=11, anchor="start", colour=t.accent, weight="bold")
    stroke(s, hx + 92, by + 66, hx + 230)
    s.button(hx + hw - 84, by + 44, 74, "Cancel run", fill="surface", h=22)
    fold(s, hx + 14, by + 92, hw - 24, "Facts", open_=False, summary="pipeline · engine · head")
    s.text(hx + 14, by + 120, "Tasks", size=10.5, anchor="start", colour=t.dim)
    for i, (word, fill) in enumerate((("succeeded", "done"), ("failed", "problem"), ("retried", "gate"))):
        cx = hx + 50 + i * 72
        bar(s, cx, by + 108, 66, 16, fill, amount=0.2)
        s.text(cx + 33, by + 120, word, size=10.5)
    for i, tab in enumerate(("Summary", "Tasks", "Parameters", "Logs")):
        tx = bx + 12 + (0, 66, 112, 194)[i]
        s.text(tx, by + 148, tab, size=11, anchor="start", weight="bold" if i == 0 else "normal")
    s.line(bx + 12, by + 154, bx + 62, by + 154, width=2.4, amount=0.2, passes=1, colour=t.accent)
    lx, lw = bx + 12, 200
    fold(s, lx, by + 172, lw, "Why it failed")
    bar(s, lx, by + 180, lw, 20, "problem", amount=0.2)
    s.text(lx + 8, by + 194, "`tool_error`", size=11, anchor="start")
    for j, done in enumerate((1.0, 0.6)):
        y = by + 208 + j * 12
        stroke(s, lx, y + 3, lx + 70, width=1.1)
        bar(s, lx + 80, y, 110, 7, "neutral", amount=0.1)
        bar(s, lx + 80, y, 110 * done, 7, "done" if done == 1.0 else "problem", amount=0.1)
    ax = bx + 222
    fold(s, ax, by + 172, cw - 234, "Head errors")
    # the tail's lines carry data-tone but runs.css does not style it there: drawn plain
    code(s, ax, by + 180, cw - 234, (("Error in rule", None), ("WARN retry 2", None)))
    s.step(x + cw / 2, STEP, 4, "the run, `/runs/id`")
    lines(s, x, TXT, ("one header on every tab: facts, task chips", "Why it failed opens first on a failed run",
                      "stages and processes with bars, 24", "an aside: log tails, the head by hand, 23"))
    # fixed in part: the Empty. text is fixed, the tint is not, so it takes the open mark
    y = pin(s, x, PIN, "R1 CR-P3PARA-04, in part", ("Empty. once ended, `ac5ae2ca`;",
                                                   "the tail's lines still untinted"), fixed=False)
    y = pin(s, x, y, "R1 CR-P3PARA-08", ("Download clicked a detached anchor,", "`ac5ae2ca`"), fixed=True)
    y = pin(s, x, y, "R1 SEC-P3PARA-01", ("the copied `ssh` and `tmux attach` lines",
                                          "carry server values unquoted"), fixed=False)
    y = pin(s, x, y, "R1 CR-P3PARA-03", ("no mark beside the Pipeline fact",), fixed=False)
    pin(s, x, y, "R1 CR-P3PARA-07", ("Tasks by state, on a Snakemake run",), fixed=False)

    for (cx, cw), (nx, _) in zip(COL[:3], COL[1:]):
        s.arrow(cx + cw + 6, STEP - 6, nx - 8, STEP - 6, colour=t.dim)

    # before and after -----------------------------------------------------------------------------
    s.line(30, FIX - 58, W - 30, FIX - 58, dashed=True, colour=t.muted)
    s.text(50, FIX - 68, "the four fixes after round 1, before and after, `ac5ae2ca`", size=14,
           anchor="start", colour=t.dim)
    fx = (50, 440, 830, 1220)

    def before_after(x: float, fid: str, title: str) -> None:
        s.text(x, FIX - 26, fid, size=14, anchor="start", weight="bold", colour=t.accent)
        s.text(x + 150, FIX - 26, title, size=14, anchor="start")
        s.text(x, FIX + 16, "before", size=12.5, anchor="start", colour=t.dim)
        s.text(x, FIX + 116, "after", size=12.5, anchor="start", colour=t.dim)
        s.arrow(x + 20, FIX + 66, x + 20, FIX + 98, colour=t.dim)

    # CR-01: the name in the URL
    x = fx[0]
    before_after(x, "CR-P3PARA-01", "the name filter")
    url_pill(s, x + 52, FIX, "/runs?state=failed")
    s.cross(x + 230, FIX + 12, size=7)
    s.text(x + 52, FIX + 46, "`q` lived in the page only: a reload", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 64, "or a shared link lost the name", size=13, anchor="start", colour=t.dim)
    url_pill(s, x + 52, FIX + 100, "/runs?state=failed&q=sar", fill="done")
    s.text(x + 52, FIX + 146, "one `setSearch` merges each change", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 164, "into the URL; a click in the 250 ms", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 182, "wait keeps the other value", size=13, anchor="start", colour=t.dim)

    # CR-02: All runs
    x = fx[1]
    before_after(x, "CR-P3PARA-02", "All runs on Home")
    s.text(x + 52, FIX + 17, "All runs >", size=13.5, anchor="start", colour=t.accent)
    s.arrow(x + 124, FIX + 12, x + 146, FIX + 12)
    url_pill(s, x + 152, FIX, "/runs?state=active", fill="problem")
    s.text(x + 52, FIX + 46, "the label says all, the list showed", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 64, "only the active runs", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 117, "All runs >", size=13.5, anchor="start", colour=t.accent)
    s.arrow(x + 124, FIX + 112, x + 146, FIX + 112)
    url_pill(s, x + 152, FIX + 100, "/runs", fill="done")
    s.text(x + 52, FIX + 146, "every run; the count cards still", size=13, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 164, "link to their own state", size=13, anchor="start", colour=t.dim)

    # CR-04: the log tail
    x = fx[2]
    before_after(x, "CR-P3PARA-04", "the log tail")
    code(s, x + 52, FIX - 6, 150, (("Empty so far.", None),))
    s.text(x + 212, FIX + 14, "on a run that", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 212, FIX + 31, "has ended", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 52, FIX + 64, "and no level tint on the tail's lines", size=13, anchor="start", colour=t.dim)
    code(s, x + 52, FIX + 94, 90, (("Empty.", None),))
    code(s, x + 156, FIX + 94, 170, (("Error in rule", None), ("WARN retry 2", None)))
    s.text(x + 52, FIX + 162, "ended: `Empty.`; running: `Empty so far.`", size=13, anchor="start", colour=t.dim)
    s.warning(x + 60, FIX + 182, size=8)
    s.text(x + 76, FIX + 188, "lines get `data-tone`, but `runs.css` tints", size=13, anchor="start",
           colour=t.dim)
    s.text(x + 76, FIX + 206, "it under `.sp-log` only: the tail stays plain", size=13, anchor="start",
           colour=t.dim)

    # CR-08: Download
    x = fx[3]
    before_after(x, "CR-P3PARA-08", "Download the log")
    s.page(x + 60, FIX - 8, 58, 60, fill="surface", lines=0)
    s.text(x + 89, FIX + 60, "page", size=11.5, colour=t.dim)
    s.link(x + 160, FIX + 16, size=14)
    s.text(x + 188, FIX + 12, "an anchor off the page,", size=13, anchor="start", colour=t.dim)
    s.text(x + 188, FIX + 30, "clicked, URL revoked", size=13, anchor="start", colour=t.dim)
    s.text(x + 188, FIX + 48, "at once: Firefox and some", size=13, anchor="start", colour=t.dim)
    s.text(x + 188, FIX + 66, "Safari versions drop it", size=13, anchor="start", colour=t.dim)
    s.page(x + 60, FIX + 96, 58, 60, fill="done", lines=0)
    s.link(x + 89, FIX + 126, size=12)
    s.text(x + 89, FIX + 172, "`document.body`", size=12)
    s.text(x + 140, FIX + 112, "appended, clicked, removed,", size=13, anchor="start", colour=t.dim)
    s.text(x + 140, FIX + 130, "then `revokeObjectURL` in", size=13, anchor="start", colour=t.dim)
    s.text(x + 140, FIX + 148, "a `setTimeout` of 0", size=13, anchor="start", colour=t.dim)

    # the review rounds, to scale ------------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW, "2 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(50, LOW + 22, "code-reviewer and security-reviewer in parallel, then the simplifier",
           size=13.5, anchor="start", colour=t.dim)
    cell, rh = 22, 40
    for i, (rnd, counts, cr, sec) in enumerate(ROUNDS):
        y = LOW + 48 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, (fill, _, _) in zip(counts, KINDS) if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=3, h=22)
        cx = 90.0
        for n, (fill, _, _) in zip(counts, KINDS):
            for _ in range(n):
                if fill != "neutral":  # a tick in each fixed cell, so the cells read without colour
                    s.tick(cx + cell / 2, y + 11, size=5, width=1.8)
                cx += cell + 3
            if n:
                cx += 12
        s.text(right + 4, y + 16, f"{sum(counts)}", size=14, anchor="start")
        s.text(530, y + 16, f"CR {cr}, SEC {sec}", size=13.5, anchor="start")
        s.tick(712, y + 10, size=7)
    ly = LOW + 48 + 2 * rh + 6
    for fill, label, lx in KINDS:
        bar(s, lx, ly, 16, 16, fill, amount=0.3)
        if fill != "neutral":
            s.tick(lx + 8, ly + 8, size=5, width=1.8)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)
    lines(s, 50, ly + 48, ("no blocker, no major · simplifier: 12 lines out, 8 in,",
                           "`.sp-section` rules dropped, one `sum` instead of three",
                           "vitest 89 passed, `tsc` and `vite build` clean",
                           "pytest 511 passed, ruff, mypy, lint-imports clean"))

    bx, bw = 760, 790
    s.shade(bx, LOW - 18, bw, 232, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(bx + 28, LOW + 8, size=11)
    s.text(bx + 50, LOW + 14, "left open after round 2, both approve", size=15, anchor="start", weight="bold")
    s.text(bx + bw - 20, LOW + 14, "IDs repeat across rounds", size=12.5, anchor="end", colour=t.dim)
    open_items = (
        ("no mark beside the Pipeline fact", "R1 CR-P3PARA-03"),
        ("the log tail: `data-tone` set, not tinted", "R1 CR-P3PARA-04, in part"),
        ("the rail test passes by rule order", "R1 CR-P3PARA-05"),
        ("four role tokens not in the token source", "R1 CR-P3PARA-06"),
        ("Nextflow words in Snakemake labels", "R1 CR-P3PARA-07"),
        ("simplify: WhyItFailed repeats `failureText`", "R1 CR-P3PARA-12"),
        ("simplify: `TONES` mixes states and words", "R1 CR-P3PARA-13"),
        ("copied shell lines are not quoted", "R1 SEC-P3PARA-01"),
        ("the box shows a `q` the URL dropped", "R2 CR-P3PARA-09"),
        ("a test leaves the URL stubs in place", "R2 CR-P3PARA-10"),
    )
    for i, (what, fid) in enumerate(open_items):
        col, r = divmod(i, 5)
        cx = bx + 20 + col * 390
        y = LOW + 48 + r * 34
        s.dot(cx + 6, y - 5, 2.6, colour=t.dim)
        s.text(cx + 18, y, what, size=13, anchor="start")
        s.text(cx + 18, y + 16, fid, size=11.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch · a warning: left open or fixed in part · R1, R2: the round · "
           "a bare number: its UX-PAR finding", size=13, anchor="start", colour=t.dim)
    s.text(W - 50, H - 16, "source: web/src shell, home, runs at 7a4811c2 · review record P3-parA · "
           "ui-parity-0.0.1", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-para-screens")
