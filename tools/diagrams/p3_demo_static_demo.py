#!/usr/bin/env python3
"""The public read-only demo of the 0.0.1 screens: step P3-demo, wave W5, 2026-10-31.

Writes docs/assets/diagrams/p3-demo-static-demo_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-demo at 8244642 (base 4c4e3ba):
- tools/media/record_demo.py: `--base http://127.0.0.1:8766`; records /version,
  /runs:summary?group_by=state, the whole runs list, per run the run, /processes, /stages, every
  task and the logs head-out, head-err, engine; /workflows:inspect of synthetic, synthetic-smk,
  nf-core-demo under /g/demo-lab/pipelines; neutral() cuts "System: Linux <release>" to
  "System: Linux"; problems(): sanitize.leaks, the recorder's host name unless login1, its
  platform.release(); MAX_BYTES 1_500_000; "not written" otherwise;
- web/demo/fixtures.json: 41 answers, 773 205 bytes (wc -c); decoded bodies: tasks 371 690 bytes,
  of which cohort-2026-scale 333 029 for 2069 tasks; logs 328 643; the rest 11 909; the remaining
  60 963 bytes are keys and JSON quoting; 5 runs: 4 succeeded, 1 failed (computed from the file);
- web/src/demo/stub.ts: not GET: 403 read-only-demo with READ_ONLY "Read-only demo: launching and
  cancelling are disabled"; a path outside /api/v1 or not recorded: 404; /runs and /runs/id/tasks
  filtered and paged; /workflows:inspect of an unrecorded pipeline: 422 naming the recorded ones;
  another origin: 404; QuietEventSource opens and stays quiet; shiftTimes(): the newest run ended
  an hour before now, logs keep their times;
- web/src/main.tsx, routes.tsx, vite.config.ts, LaunchPage.tsx, RunDetailPage.tsx: mode "demo" only:
  startDemo and DemoBanner, createHashHistory, base "./", outDir dist-demo, READ_ONLY as the last
  disabled reason, Open raw as a blob URL;
- web/scripts/check-dist.mjs, run by `npm run build`: fails on any recorded run ID or "Demo:
  recorded data", "Read-only demo", "read-only-demo" in web/dist;
- .github/workflows/previews.yml: `npm --prefix web run build:demo`, `cp -R web/dist-demo
  site/demo`, then `curl -fsS "$URL/demo/"`;
- web/src/demo/DemoBanner.tsx, demo.css, shell/shell.css:222: the banner measured in a layout effect
  and a ResizeObserver into --sp-demo-banner-h; .sp-sidebar height
  calc(100vh - 86px - var(--sp-demo-banner-h, 0px));
- the banner heights, from the worker reports of 06b1117a and 25aa0c99 (Playwright on the demo
  build): one 31 px line with an ellipsis, then 49 px at 1280 px wide with the sidebar ending at 790
  of 800; 121 px at 375 px as doc-writer measured it on 8244642 (docs/progress/W5/P3-M4.md,
  Evidence; the worker reported 103 px); the R1 cut of about 31 px is from CR-P3DEMO-02; the
  sidebar top, 76 px under the banner, follows from 49 + 76 + 665 = 790 (665 = 800 - 86 - 49);
- the review rounds, docs/reviews/code/P3-demo.md as given in the step's report: R1 CR approve 01 to
  05, SEC approve 01 to 04, fixed CR-02 and SEC-02 in 06b1117a; R2 CR changes, 03 major, 04, 05,
  SEC approve 05 to 07, fixed CR-03 in 25aa0c99; R3 CR approve 04 to 07, SEC approve 03 and 04,
  fixed CR-05 (simplify) in 8244642. IDs repeat across rounds. Simplifier: 4 lines out, 1 in;
  pytest 511 passed, vitest 158 passed, before and after.
The recorded kernel release itself is never written here: it is the leak SEC-P3DEMO-02 removed.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1760
TOP = 128  # the recording, the file, the builds
COL = (50, 580, 1080)
CW = (480, 450, 470)
STEP = TOP + 404
BRW = 712  # the demo in the browser
BAN = BRW + 470  # the banner, before and after
LOW = BAN + 364  # the review rounds

# (round, fixed, fixed major, left open, code-reviewer verdict, security-reviewer verdict)
ROUNDS = (("R1", 2, 0, 7, "approve", "approve"),
          ("R2", 0, 1, 5, "changes", "approve"),
          ("R3", 1, 0, 5, "approve", "approve"))

FILE = 773_205
BUDGET = 1_500_000
PARTS = ((371_690, "bar_orange", "tasks"), (328_643, "bar_blue", "logs"),
         (11_909, "bar_violet", ""), (60_963, "bar_grey", ""))


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


def sieve(s: Sketch, cx: float, top: float, w: float = 70, h: float = 48) -> None:
    """A funnel with holes: what passes goes on, the rest is held back."""
    s.poly([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.14, top + h), (cx - w * 0.14, top + h)],
           fill="gate", amount=0.8)
    for dx, dy in ((-16, 12), (0, 12), (16, 12), (-8, 27), (8, 27)):
        s.dot(cx + dx, top + dy, 2.4, colour=s.t.dim)


def viewport(s: Sketch, x: float, y: float, banner: float, side_end: float, *, cut: bool,
             scale: float = 0.25) -> None:
    """A 1280 by 800 desktop window to scale: the banner, the sticky sidebar and its foot."""
    w, h = 1280 * scale, 800 * scale
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="surface", amount=0.5)
    bar(s, x, y, w, banner * scale, "gate", amount=0.2)
    for i in range(1 if cut else 2):
        lw = w - 30 if not cut else w - 46
        s.line(x + 8, y + 5 + i * 5, x + 8 + lw * (0.95 if i == 0 else 0.6), y + 5 + i * 5,
               colour=s.t.dim, amount=0.2, passes=1, width=1.2)
    if cut:
        s.text(x + w - 22, y + 7, "...", size=12, anchor="start", colour=s.t.accent)
    sy = y + (banner + 76) * scale  # the sidebar starts 76 px under the banner in all three
    bottom = min(y + side_end * scale, y + h + 18)
    s.poly([(x + 3, sy), (x + 57, sy), (x + 57, bottom), (x + 3, bottom)], fill="neutral", amount=0.4)
    foot = y + (side_end - 22) * scale
    s.poly([(x + 9, foot), (x + 51, foot), (x + 51, foot + 7), (x + 9, foot + 7)], fill="done", amount=0.2)
    for i in range(3):
        s.line(x + 70, y + 40 + i * 14 + (banner - 31) * scale, x + w - 14, y + 40 + i * 14 + (banner - 31) * scale,
               colour=s.t.muted, amount=0.3, passes=1, width=1.3)
    s.line(x - 8, y + h, x + w + 8, y + h, dashed=True, colour=s.t.accent if side_end > 800 else s.t.muted)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=131)
    t = theme
    s.heading(50, 58, "P3-demo · the real screens as a public demo, answered from a recording",
              "`npm run build:demo`, `vite --mode demo` · at `spectio.pages.dev/demo/` and on every "
              "PR preview · reads only, nothing leaves the page")

    # 1 -- record ----------------------------------------------------------------------------------
    x = COL[0]
    s.hpc_node(x, TOP, 56, 74, busy=2)
    s.text(x + 76, TOP + 18, "a demo `spectio serve`", size=15, anchor="start", weight="bold")
    lines(s, x + 76, TOP + 42, ("node `login1`, account `alice`", "`HOME=/g/demo-lab`, on 127.0.0.1"),
          size=13)
    s.terminal(x, TOP + 96, 400, 74, ("$ python3 tools/media/record_demo.py \\",
                                      "    --base http://127.0.0.1:8766"), size=12)
    lines(s, x, TOP + 196, ("every GET, each list whole, every page",
                            "per run: processes, stages, tasks, 3 logs",
                            "3 pipeline inspections"), size=13)
    s.arrow(x + 410, TOP + 132, x + 470, TOP + 132)
    sieve(s, x + 440, TOP + 166, w=56, h=40)
    s.text(x + 440, TOP + 228, "before", size=12.5, colour=t.dim)
    s.text(x + 440, TOP + 244, "writing", size=12.5, colour=t.dim)
    s.cross(x + 300, TOP + 278, size=8)
    lines(s, x + 316, TOP + 283, ("not written if", "`sanitize.leaks` hits,", "or its host name,",
                                  "or its kernel release"), size=12.5)
    s.text(x, TOP + 278, "`System: Linux release` cut to", size=13, anchor="start")
    s.text(x, TOP + 298, "`System: Linux` in the engine logs", size=13, anchor="start", colour=t.dim)
    s.step(x + 210, STEP, 1, "record a demo server")

    # 2 -- one public file -------------------------------------------------------------------------
    x = COL[1]
    s.page(x + 10, TOP - 4, 64, 84, fill="input", lines=4)
    s.text(x + 92, TOP + 18, "`web/demo/fixtures.json`", size=15, anchor="start", weight="bold")
    lines(s, x + 92, TOP + 42, ("committed, public: demo data only", "41 answers, 773 205 bytes"), size=13)
    scale = 420 / BUDGET
    by = TOP + 116
    s.text(x, by - 10, "to scale, against the 1.5 MB budget", size=13, anchor="start", colour=t.dim)
    bar(s, x, by, BUDGET * scale, 28, "surface", amount=0.3)
    cx = x
    for n, fill, label in PARTS:
        bar(s, cx, by, n * scale, 28, fill, amount=0.2)
        if label:
            s.text(cx + n * scale / 2, by + 19, label, size=12.5)
        cx += n * scale
    s.line(cx, by - 6, cx, by + 40, colour=t.accent, amount=0.3, passes=1, width=1.6)
    s.text(cx + 6, by + 52, "773 205", size=12.5, anchor="start", colour=t.accent)
    s.text(x + 420, by + 52, "1 500 000", size=12.5, anchor="end", colour=t.dim)
    lines(s, x, by + 80, ("tasks 371 690, logs 328 643, the rest 11 909", "grey: keys and JSON quoting"),
          size=12.5)
    s.text(x, by + 136, "5 runs recorded", size=13.5, anchor="start")
    s.task_strip(x + 118, by + 120, ((4, "done", ""), (1, "problem", "")), cell=22, gap=3, h=20)
    lines(s, x, by + 166, ("4 succeeded, 1 failed in `MERGE`",
                           "`cohort-2026-scale`: 2069 tasks, 333 029 bytes"), size=12.5)
    s.step(x + CW[1] / 2, STEP, 2, "one public file")

    # 3 -- two builds ------------------------------------------------------------------------------
    x = COL[2]
    s.text(x, TOP + 6, "`npm run build:demo`", size=14, anchor="start", weight="bold")
    s.arrow(x + 4, TOP + 18, x + 4, TOP + 46)
    s.folder(x - 6, TOP + 50, 150, 70, fill="work", label="`web/dist-demo`")
    lines(s, x + 156, TOP + 72, ("relative asset paths,", "routes in the hash"), size=12.5)
    s.arrow(x + 300, TOP + 84, x + 336, TOP + 84)
    s.browser(x + 340, TOP + 40, 132, 90, url="")
    s.text(x + 406, TOP + 92, "`/demo/`", size=13)
    s.text(x + 406, TOP + 112, "on Pages", size=12.5, colour=t.dim)
    lines(s, x, TOP + 148, ("`previews.yml`: `cp -R web/dist-demo site/demo`",
                            "then `curl $URL/demo/` must answer"), size=12.5)

    y2 = TOP + 216
    s.text(x, y2 + 6, "`npm run build`, the normal one", size=14, anchor="start", weight="bold")
    s.arrow(x + 4, y2 + 18, x + 4, y2 + 46)
    s.folder(x - 6, y2 + 50, 150, 70, fill="done", label="`web/dist`")
    s.arrow(x + 154, y2 + 84, x + 190, y2 + 84)
    s.magnifier(x + 214, y2 + 78, 14)
    lines(s, x + 252, y2 + 66, ("`check-dist.mjs` fails on", "any of the 5 run IDs or",
                                "the 3 demo texts"), size=12.5)
    s.text(x, y2 + 146, "`spectio serve` ships no demo inside", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW[2] / 2, STEP, 3, "two builds, kept apart")

    for i in range(2):
        s.arrow(COL[i] + CW[i] + 8, STEP - 6, COL[i + 1] - 16, STEP - 6, colour=t.dim)

    pin(s, COL[0], STEP + 44, "R1 SEC-P3DEMO-02", ("the sandbox kernel build was published",
                                                   "in 4 engine logs, now cut, `06b1117a`"), fixed=True)
    pin(s, COL[0] + 250, STEP + 44, "R2 SEC-P3DEMO-07", ("still in the history of `f769837a`",
                                                         "the branch is not pushed yet"), fixed=False)
    pin(s, COL[1], STEP + 44, "R3 CR-P3DEMO-07, SEC-P3DEMO-03", ("no CI job runs `test_record_demo.py`,",
                                                                 "so a hand edit of the file passes"),
        fixed=False)
    pin(s, COL[2], STEP + 44, "R1 CR-P3DEMO-01", ("if the docs get a demo page, `cp -R`",
                                                  "lands in `site/demo/dist-demo`"), fixed=False)

    # 4, 5 -- the demo in the browser, and the stub -----------------------------------------------------------------
    s.line(30, BRW - 40, W - 30, BRW - 40, dashed=True, colour=t.muted)
    s.text(50, BRW - 50, "in the visitor's browser, the demo build only", size=14, anchor="start", colour=t.dim)
    bx, bw, bh = 50, 640, 300
    s.browser(bx, BRW, bw, bh, url="spectio.pages.dev/demo/#/runs")
    bar(s, bx + 2, BRW + 30, bw - 4, 58, "gate", amount=0.2)
    s.text(bx + 14, BRW + 46, "Demo: recorded data from a test server, read-only. Times are moved so that",
           size=12.5, anchor="start")
    s.text(bx + 14, BRW + 63, "the newest run ended an hour ago; nf-core/demo is a renamed copy of the",
           size=12.5, anchor="start", colour=t.dim)
    s.text(bx + 14, BRW + 80, "synthetic test pipeline, not an nf-core pipeline.",
           size=12.5, anchor="start", colour=t.dim)
    bar(s, bx + 12, BRW + 98, 130, bh - 108, "neutral", amount=0.3)
    for i in range(4):
        s.line(bx + 24, BRW + 120 + i * 22, bx + 118, BRW + 120 + i * 22, colour=t.muted, amount=0.3,
               passes=1, width=1.4)
    bar(s, bx + 22, BRW + bh - 36, 80, 14, "done", amount=0.2)
    s.text(bx + 156, BRW + 116, "Runs", size=15, anchor="start", weight="bold")
    for i, rail in enumerate(("done", "problem", "done", "done", "done")):
        ry = BRW + 128 + i * 23
        bar(s, bx + 156, ry, 5, 16, rail, amount=0.2)
        s.line(bx + 170, ry + 8, bx + 400, ry + 8, colour=t.muted, amount=0.3, passes=1, width=1.4)
        s.line(bx + 470, ry + 8, bx + 560, ry + 8, colour=t.muted, amount=0.3, passes=1, width=1.4)
    s.button(bx + 156, BRW + bh - 48, 110, "Launch", fill="neutral")
    s.text(bx + 278, BRW + bh - 28, "disabled: `READ_ONLY`, launching and", size=12.5, anchor="start",
           colour=t.dim)
    s.text(bx + 278, BRW + bh - 10, "cancelling are disabled", size=12.5, anchor="start", colour=t.dim)
    s.text(bx + bw / 2, BRW + bh + 64, "the banner on every page · Open raw: a blob of the text shown",
           size=13, colour=t.dim)

    # the stub
    sx = 770
    s.arrow(bx + bw + 6, BRW + 150, sx - 8, BRW + 150)
    s.text((bx + bw + sx) / 2, BRW + 140, "`fetch`", size=12.5, colour=t.dim)
    s.cog(sx + 26, BRW + 150, 16, fill="docs")
    s.text(sx + 26, BRW + 196, "`stub.ts`", size=13)
    s.text(sx + 26, BRW + 214, "`answer()`", size=13, colour=t.dim)
    s.text(sx + 70, BRW + 6, "the API answered in the page, no server behind it", size=15, anchor="start",
           weight="bold")
    rows = (
        ("tick", "a recorded GET: its answer", "runs and tasks filtered and paged, as the server does"),
        ("cross", "any write: 403 `read-only-demo`", "with the `READ_ONLY` text"),
        ("cross", "not recorded, another origin: 404", "an unrecorded pipeline inspected: 422, naming the 3"),
        ("env", "`EventSource`: opens, stays quiet", "nothing changes in a recording"),
        ("clock", "every JSON time moved by one offset", "the newest run ended an hour before now, logs keep theirs"),
    )
    for i, (mark, head, sub) in enumerate(rows):
        ry = BRW + 44 + i * 50
        mx = sx + 88
        if mark == "tick":
            s.tick(mx, ry - 4, size=7)
        elif mark == "cross":
            s.cross(mx, ry - 4, size=7)
        elif mark == "env":
            s.envelope(mx - 10, ry - 12, 20, 14, fill="input")
        else:
            s.hourglass(mx, ry - 4, size=8)
        s.text(mx + 20, ry, head, size=13.5, anchor="start")
        s.text(mx + 20, ry + 19, sub, size=12.5, anchor="start", colour=t.dim)
        s.arrow(sx + 46, BRW + 150, mx - 14, ry - 4, colour=t.muted)
    s.step(sx + 360, BRW + bh + 38, 5, "the stub answers every request")
    pin(s, 1260, BRW + 44, "R1 SEC-P3DEMO-04", ("only the stub keeps requests in", "no CSP on `/demo/`"),
        fixed=False)
    pin(s, 1260, BRW + 124, "R1 CR-P3DEMO-03", ("the 422 is beyond the brief,", "which said 404"),
        fixed=False)
    pin(s, 1260, BRW + 204, "R1 CR-P3DEMO-04", ("`READ_ONLY` is the last reason:", "a form first,",
                                                "then launch is off"), fixed=False)
    s.step(bx + bw / 2, BRW + bh + 38, 4, "the real screens, read-only")

    # 6 -- the banner, before and after ------------------------------------------------------------
    s.line(30, BAN - 66, W - 30, BAN - 66, dashed=True, colour=t.muted)
    s.text(50, BAN - 76, "the banner and the sticky sidebar, a 1280 by 800 window to scale",
           size=14, anchor="start", colour=t.dim)
    panels = ((50, "`f769837a`", 31, 821, False, "the sidebar foot about 31 px", "under the fold"),
              (560, "`06b1117a`", 31, 790, True, "one 31 px line, the rest cut", "by an ellipsis"),
              (1070, "`25aa0c99` `8244642`", 49, 790, False, "49 px, the whole text", "sidebar ends at 790 of 800"))
    for px, sha, ban, end, cut, a, b in panels:
        s.text(px, BAN - 30, sha, size=13.5, anchor="start", weight="bold")
        viewport(s, px, BAN - 14, ban, end, cut=cut)
        s.text(px, BAN + 222, a, size=13, anchor="start")
        s.text(px, BAN + 240, b, size=13, anchor="start", colour=t.dim)
    s.arrow(392, BAN + 86, 548, BAN + 86, colour=t.dim)
    s.arrow(902, BAN + 86, 1058, BAN + 86, colour=t.dim)
    pin(s, 404, BAN + 26, "R1 CR-P3DEMO-02", ("pill and account line", "below the fold"), fixed=True)

    # phones
    ph = s.phone(914, BAN + 150, 80, 150)
    bar(s, ph.x, ph.y, ph.w, 121 * ph.w / 375 * 0.5, "neutral", amount=0.2)
    s.cross(ph.cx, ph.y + 30, size=10)
    s.text(ph.cx, ph.bottom + 34, "phone: the disclosure hidden", size=12.5, colour=t.accent)
    pin(s, 560, BAN + 268, "R2 CR-P3DEMO-03 · major", ("the disclosure was cut from about",
                                                       "768 to 1350 px, and hidden from",
                                                       "screen readers on the phone"),
        fixed=True)
    ph = s.phone(1404, BAN + 4, 84, 170)
    bar(s, ph.x, ph.y, ph.w, 121 * ph.w / 375, "gate", amount=0.2)
    for i in range(4):
        s.line(ph.x + 5, ph.y + 5 + i * 5, ph.right - 8, ph.y + 5 + i * 5, colour=t.dim, amount=0.2,
               passes=1, width=1.1)
    s.text(1500, BAN + 40, "375 px", size=12.5, anchor="start", colour=t.dim)
    s.text(1500, BAN + 58, "121 px,", size=12.5, anchor="start")
    s.text(1500, BAN + 76, "all of it", size=12.5, anchor="start", colour=t.dim)
    lines(s, 1070, BAN + 274, ("measured, `--sp-demo-banner-h`, a ResizeObserver",
                               "`.sp-sidebar` takes it off `100vh - 86px`"), size=12.5)
    s.step(800, BAN + 350, 6, "the disclosure stays whole, the sidebar foot stays on screen")

    # the review rounds, to scale -------------------------------------------------------------------
    s.line(30, LOW - 6, W - 30, LOW - 6, dashed=True, colour=t.muted)
    s.text(50, LOW + 30, "3 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.prefix_key(50, LOW + 52, ("CR", "SEC"))
    cell, rh = 22, 36
    for i, (rnd, fixed, major, left, cr, sec) in enumerate(ROUNDS):
        y = LOW + 72 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, fill in ((fixed, "done"), (major, "problem"), (left, "neutral")) if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=3, h=22)
        s.text(right + 4, y + 16, f"{fixed + major + left}", size=14, anchor="start")
        s.text(400, y + 16, f"CR {cr}, SEC {sec}", size=13.5, anchor="start")
        if cr == "changes":
            s.warning(590, y + 9, size=8)
        else:
            s.tick(590, y + 10, size=7)
    lx0, ly = 660, LOW + 88
    for j, (fill, label) in enumerate((("done", "fixed"), ("problem", "major, fixed"),
                                       ("neutral", "minor, left open"))):
        bar(s, lx0, ly + j * 26, 16, 16, fill, amount=0.3)
        s.text(lx0 + 24, ly + j * 26 + 13, label, size=13, anchor="start", colour=t.dim)
    lines(s, 900, LOW + 90, ("no blocker · simplifier: the sidebar offset in one rule,",
                             "`shell.css`, 4 lines out, 1 in",
                             "pytest 511 passed, vitest 158 passed, `tsc` clean,",
                             "before and after"), size=13.5)

    s.text(W - 50, H - 16, "source: branch autopilot/P3-demo at 8244642 · web/src/demo, record_demo.py, "
           "previews.yml · docs/reviews/code/P3-demo.md", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-demo-static-demo")
