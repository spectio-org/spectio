#!/usr/bin/env python3
"""The Paper shell in `web/`: step P3, P2 G4, 2026-10-30.

Writes docs/assets/diagrams/p3-g4-paper-shell_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-G4 at 7c5737c8 (base 330ae6b2):
- web/src/shell/AppShell.tsx: PHONE "(max-width: 767.98px)", TABLET "(max-width: 1199.98px)", read
  with useMediaQuery at first render (getInitialValueInEffect false); open = chosen ?? !tablet, so
  the tablet starts folded and the reader's fold wins; the phone renders TabBar and no Sidebar;
  getVersion() sets server, or down with the error message;
- web/src/api.ts: getVersion is `GET /api/v1/version`;
- web/src/shell/Sidebar.tsx: NAV Home, Runs, Launch; "Workspace" eyebrow; the fold key is a
  button with aria-expanded, named "Fold the sidebar" or "Unfold the sidebar"; folded, the labels
  are .sp-sr; foot: status "Spectio <version> · online", "Server not reached" or "Connecting…",
  data-down={!!down}; foot text "<EXECUTOR> · server on <node> · your account <account>",
  role status, .sp-sr when folded;
- web/src/shell/TopBar.tsx: crumbsFor(pathname): Home, then SECTIONS runs and launch, else the
  segment through label(), which keeps a malformed escape as it is (4e0d2868, CR-P3G4-01); the
  last crumb is aria-current page; search, notifications and account are disabled placeholders
  "(not in 0.0.1)"; ThemeSwitch is a button role switch aria-checked named "Dark theme"; phone:
  the node pill is role img, aria-label "Server on <node>, online", "Server not reached" or
  "Connecting", data-down={!!down || undefined} (7c5737c8, CR-P3G4-02 of round 2);
- web/src/shell/shell.css: sidebar 216 px, folded 72 px; top bar 56 px, phone top bar 48 px,
  phone keys 44 px, tab bar 64 px; search and bell hidden below 390 px (.sp-narrow-hide);
- web/src/shell/theme.ts: THEME_KEY "spectio-color-scheme", localStorageColorSchemeManager,
  defaultColorScheme "auto"; role tokens of design/tokens/spectio-tokens.css as --sp-* variables;
- web/src/shell/shell.test.tsx: VERSION node login1, executor slurm; the run id run_01K8T2F1XT;
  the drawn foot follows the app-launch shot instead, "LOCAL · server on login1 · your account
  alice": in 0.0.1 the screens are served only with executor local (inbox 86, dev-env §15.3 req. 17);
  "/runs/%E0" keeps the shell; widths 1440, 1024 and 390 px;
- inbox 89 (docs/reviews/inbox.md): rules 1 to 6, assumed (a), pending Thomas;
- the review rounds, from the step's worker report of 2026-10-30 (record docs/reviews/code/P3-G4.md):
  R1 CR changes, CR-P3G4-01 major and -02 to -05 minor, SEC approve, SEC-P3G4-01 minor;
  R2 both approve, CR-P3G4-02 to -05 and SEC-P3G4-01, -02, all minor; R3 both approve, CR-P3G4-03.
  IDs are numbered per round, so the same ID can name two findings: R1 CR-03 and R2 CR-02 are the
  node pill, fixed in 7c5737c8; R1 CR-01 and R1 SEC-01 are the malformed escape, fixed in 4e0d2868.
  The simplifier made no change (504 pytest passed).
- after round 3, R2 CR-P3G4-05 and SEC-P3G4-01 (the app-launch shots named the capture host's
  account root and host vm) are fixed: the four shots were retaken as the demo account alice on
  the node name login1, and tools/media/fixtures.yaml forbids "account root" and the bare `vm`.
- the desktop and tablet frames are at /launch, so crumbsFor gives Home, Launch, the page title is
  Launch and the sidebar highlights Launch, as in the app-launch shot.
"""

from __future__ import annotations

import math

from sketch import Box, Sketch, Theme, main_for

W, H = 1600, 1300
DEV_Y = 150  # top of the three device frames
DEV_H = 330
CAP = DEV_Y + DEV_H + 46  # the numbered captions under the devices
MID = 740  # the three mechanisms
REV = 1000  # the review rounds


def bar(s: Sketch, x: float, y: float, w: float, h: float, *, fill: str = "surface", rx: float = 8) -> None:
    """A floating paper bar or panel of the shell."""
    s.rect(Box(x, y, w, h, fill), rx=rx, colour=s.t.dim)


def pill(s: Sketch, x: float, y: float, w: float, label: str, fill: str, *, size: float = 11.5, h: float = 20) -> None:
    """A rounded status pill with its dot, as .sp-status and .sp-node."""
    s.rect(Box(x, y, w, h, fill), rx=h / 2, colour=s.t.dim)
    ink = {"done": s.t.good, "problem": s.t.accent}.get(fill, s.t.dim)
    s.dot(x + 10, y + h / 2, 3, colour=ink)
    s.text(x + 18, y + h / 2 + size * 0.36, label, size=size, anchor="start")


def key(s: Sketch, cx: float, cy: float, r: float = 7) -> None:
    """A round key of the top bar: a placeholder or the theme switch."""
    s.circle(cx, cy, r, fill="neutral")


def mark(s: Sketch, cx: float, base: float, r: float) -> None:
    """The four-colour fan of the Spectio mark (indigo, violet, coral, amber), drawn small."""
    for i, colour in enumerate(("#5A4FCF", "#8B5CF6", "#EC5F87", "#F9A947")):
        a0, a1 = 180 + i * 45, 180 + (i + 1) * 45
        p0 = (cx + r * math.cos(math.radians(a0)), base + r * math.sin(math.radians(a0)))
        p1 = (cx + r * math.cos(math.radians(a1)), base + r * math.sin(math.radians(a1)))
        s.raw(f'<path d="M{cx:.1f},{base:.1f} L{p0[0]:.1f},{p0[1]:.1f} A{r},{r} 0 0 1 {p1[0]:.1f},{p1[1]:.1f} Z" '
              f'fill="{colour}"/>')


def chevron(s: Sketch, x: float, y: float) -> None:
    s.line(x - 2, y - 4, x + 2, y, amount=0.3, passes=1, width=1.3, colour=s.t.dim)
    s.line(x + 2, y, x - 2, y + 4, amount=0.3, passes=1, width=1.3, colour=s.t.dim)


def nav_icon(s: Sketch, kind: str, cx: float, cy: float, *, size: float = 6) -> None:
    """The section icons of NAV: four tiles, a play triangle, an upload arrow."""
    if kind == "home":
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            s.rect(Box(cx + dx * size * 0.55 - size * 0.4, cy + dy * size * 0.55 - size * 0.4, size * 0.8,
                       size * 0.8), rx=1)
    elif kind == "runs":
        s.poly([(cx - size * 0.6, cy - size), (cx + size, cy), (cx - size * 0.6, cy + size)], fill="docs", amount=0.3)
    else:
        s.line(cx, cy + size * 0.5, cx, cy - size, amount=0.3, passes=1, width=1.4)
        s.line(cx - size * 0.6, cy - size * 0.4, cx, cy - size, amount=0.3, passes=1, width=1.4)
        s.line(cx + size * 0.6, cy - size * 0.4, cx, cy - size, amount=0.3, passes=1, width=1.4)
        s.line(cx - size, cy + size, cx + size, cy + size, amount=0.3, passes=1, width=1.4)


def topbar(s: Sketch, x: float, y: float, w: float, crumbs: tuple[str, ...]) -> None:
    """LiteTopbar at half scale: 56 px tall, 10 px margins; `crumbs` as crumbsFor gives them."""
    bar(s, x + 5, y + 5, w - 10, 28, rx=9)
    mark(s, x + 20, y + 25, 10)
    s.text(x + 34, y + 24, "Spectio", size=12, anchor="start", weight="bold")
    s.line(x + 82, y + 12, x + 82, y + 26, amount=0.2, passes=1, colour=s.t.muted, width=1)
    cx = x + 90
    for i, crumb in enumerate(crumbs):
        if i:
            chevron(s, cx, y + 19)
            cx += 8
        last = i == len(crumbs) - 1
        s.text(cx, y + 23, crumb, size=10.5, anchor="start", colour=s.t.ink if last else s.t.dim,
               weight="bold" if last else "normal")
        cx += len(crumb) * 6.3 + 8
    sx = x + w - 10 - 66 - 120
    s.rect(Box(sx, y + 10, 120, 18, "neutral"), rx=5, colour=s.t.muted)
    s.text(sx + 8, y + 23, "Search", size=10, anchor="start", colour=s.t.dim)
    for i in range(3):
        key(s, x + w - 64 + i * 20, y + 19)


def sidebar(s: Sketch, x: float, y: float, h: float, *, open_: bool) -> None:
    """LiteSidebar at half scale: 216 px open, the 72 px rail folded."""
    w = 108 if open_ else 36
    bar(s, x, y, w, h, rx=11)
    if open_:
        s.text(x + 10, y + 18, "WORKSPACE", size=9.5, anchor="start", colour=s.t.dim)
    s.rect(Box(x + w - 22, y + 7, 14, 13), rx=3, colour=s.t.dim)
    for i, (kind, label) in enumerate((("home", "Home"), ("runs", "Runs"), ("launch", "Launch"))):
        cy = y + 42 + i * 26
        if i == 2:
            s.rect(Box(x + 4, cy - 10, w - 8, 20, "work"), rx=6, colour=s.t.muted)
        nav_icon(s, kind, x + 17, cy, size=5)
        if open_:
            s.text(x + 32, cy + 4, label, size=11.5, anchor="start")
    s.line(x + 6, y + h - 62, x + w - 6, y + h - 62, amount=0.3, passes=1, colour=s.t.muted, width=1)
    if open_:
        pill(s, x + 6, y + h - 54, w - 12, "0.0.1 online", "done", size=10.5, h=18)
        s.text(x + 9, y + h - 20, "LOCAL · server", size=9.5, anchor="start", colour=s.t.dim)
        s.text(x + 9, y + h - 8, "on login1", size=9.5, anchor="start", colour=s.t.dim)
    else:
        s.rect(Box(x + 8, y + h - 52, 20, 16, "done"), rx=8, colour=s.t.dim)
        s.dot(x + 18, y + h - 44, 3, colour=s.t.good)


def page(s: Sketch, x: float, y: float, w: float) -> None:
    """The routed page: a title and a few lines."""
    s.text(x, y, "Launch", size=14, anchor="start", weight="bold")
    for i, lw in enumerate((0.9, 0.7, 0.8, 0.5)):
        s.line(x, y + 22 + i * 18, x + w * lw, y + 22 + i * 18, amount=0.4, passes=1, colour=s.t.muted, width=5)


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=41)
    t = theme
    s.heading(50, 58, "P3 G4 · the Paper shell in `web/`, one shell at three widths",
              "`web/src/shell/` after the G1 boards LiteTopbar, LiteSidebar, MLiteTopbar, MLiteTabbar · "
              "ui-spec 7 and 4.11 · inbox 89")
    s.text(50, DEV_Y - 20, "widths at half scale · the layout is picked with `matchMedia` at the first render,"
           " so a phone never shows the sidebar for a frame", size=13.5, anchor="start", colour=t.dim)

    # 1 -- desktop, 1440 px ----------------------------------------------------------------------
    x, w = 50, 720
    s.browser(x, DEV_Y, w, DEV_H, url="1440 px · /launch")
    vy = DEV_Y + 28
    topbar(s, x, vy, w, ("Home", "Launch"))
    sidebar(s, x + 5, vy + 38, DEV_H - 28 - 43, open_=True)
    page(s, x + 140, vy + 64, w - 170)
    s.step(x + w / 2, CAP, 1, "desktop, 1200 px and up")
    lines(s, x + 40, CAP + 30, ("a floating top bar: home, breadcrumbs, the theme switch",
                                "search, alerts and account wait, disabled, not in 0.0.1",
                                "the sidebar open, 216 px, server status in its foot"))

    # 2 -- tablet, 1024 px -----------------------------------------------------------------------
    x, w = 820, 512
    s.browser(x, DEV_Y, w, DEV_H, url="1024 px")
    topbar(s, x, vy, w, ("Home", "Launch"))
    sidebar(s, x + 5, vy + 38, DEV_H - 28 - 43, open_=False)
    page(s, x + 62, vy + 64, w - 90)
    s.step(x + w / 2, CAP, 2, "tablet, 768 to 1199 px")
    lines(s, x + 20, CAP + 30, ("the sidebar starts folded to the 72 px rail",
                                "a button with `aria-expanded` unfolds it,",
                                "and the reader's own fold wins until reload"))
    s.arrow(x + 108, vy + DEV_H - 72, x + 40, vy + DEV_H - 84, dashed=True, colour=t.warn)
    s.warning(x + 120, vy + DEV_H - 70, size=10)
    s.text(x + 136, vy + DEV_H - 66, "the node text is hidden on the rail, R1 CR-P3G4-04", size=12,
           anchor="start", colour=t.warn)

    # 3 -- phone, 390 px -------------------------------------------------------------------------
    scr = s.phone(1352, DEV_Y - 12, 209, DEV_H + 26)
    sx, sy, sw = scr.x, scr.y, scr.w  # 195 wide: 390 px at half scale
    s.line(sx, sy + 24, sx + sw, sy + 24, amount=0.3, passes=1, colour=t.muted, width=1)
    mark(s, sx + 12, sy + 17, 8)
    s.text(sx + 23, sy + 17, "Spectio", size=11, anchor="start", weight="bold")
    pill(s, sx + 68, sy + 5, 52, "login1", "done", size=9.5, h=15)
    for i in range(4):
        key(s, sx + 136 + i * 15, sy + 12, r=5.5)
    page(s, sx + 10, sy + 50, sw - 20)
    ty = scr.bottom - 40
    bar(s, sx + 4, ty, sw - 8, 32, rx=12)
    for i, (kind, label) in enumerate((("home", "Home"), ("runs", "Runs"), ("launch", "Launch"))):
        cx = sx + 4 + (sw - 8) * (i + 0.5) / 3
        if i == 2:
            s.rect(Box(cx - 28, ty + 3, 56, 26, "work"), rx=9, colour=t.muted)
        nav_icon(s, kind, cx, ty + 11, size=4.5)
        s.text(cx, ty + 27, label, size=9.5)
    s.step(1352 + 104, CAP, 3, "phone, under 768 px")
    lines(s, 1372, CAP + 30, ("no sidebar: a 64 px tab bar",
                              "a 48 px top bar with",
                              "the node pill, 44 px keys"))

    s.line(30, MID - 72, W - 30, MID - 72, dashed=True, colour=t.muted)
    s.text(50, MID - 82, "inside the shell", size=14, anchor="start", colour=t.dim)

    # A -- server status -------------------------------------------------------------------------
    x = 50
    s.hpc_node(x, MID - 10, 48, 64, busy=1)
    s.text(x + 24, MID + 78, "`spectio serve`", size=12.5)
    s.arrow(x + 70, MID + 22, x + 216, MID + 22)
    s.text(x + 143, MID + 10, "`GET /api/v1/version`", size=12)
    s.text(x + 143, MID + 42, "once, at load", size=12.5, colour=t.dim)
    px = x + 228
    pill(s, px, MID - 30, 160, "Connecting", "neutral", size=13, h=24)
    s.text(px + 172, MID - 13, "while waiting", size=12.5, anchor="start", colour=t.dim)
    pill(s, px, MID + 10, 160, "login1 · online", "done", size=13, h=24)
    s.text(px + 172, MID + 27, "it answered", size=12.5, anchor="start", colour=t.dim)
    pill(s, px, MID + 50, 160, "not reached", "problem", size=13, h=24)
    s.text(px + 172, MID + 67, "it failed", size=12.5, anchor="start", colour=t.dim)
    s.text(x, MID + 118, "A · server status, in the sidebar foot or the phone pill", size=15, anchor="start",
           weight="bold")
    s.tick(x + 10, MID + 146, size=7)
    s.text(x + 26, MID + 150, "R2 CR-P3G4-02: the phone pill was red while connecting;", size=13, anchor="start")
    s.text(x + 26, MID + 170, "now it turns red only once the call failed, as the sidebar, 7c5737c8",
           size=13, anchor="start", colour=t.dim)

    # B -- breadcrumbs ---------------------------------------------------------------------------
    x = 610
    rows = (("`/runs/run_01K8T2F1XT`", "run_01K8T2F1XT", "neutral"),
            ("`/runs/%E0`", "%E0", "problem"))
    for i, (url, last, fill) in enumerate(rows):
        y = MID - 22 + i * 56
        s.link(x + 12, y + 12, size=13)
        s.text(x + 32, y + 17, url, size=12.5, anchor="start")
        s.arrow(x + 196, y + 12, x + 226, y + 12)
        s.rect(Box(x + 236, y - 2, 300, 28, fill), rx=8, colour=t.dim)
        s.text(x + 248, y + 17, "Home", size=12.5, anchor="start", colour=t.dim)
        chevron(s, x + 292, y + 12)
        s.text(x + 302, y + 17, "Runs", size=12.5, anchor="start", colour=t.dim)
        chevron(s, x + 342, y + 12)
        s.text(x + 352, y + 17, last, size=12.5, anchor="start", weight="bold")
    s.text(x + 236, MID + 82, "the last crumb is the page, `aria-current`", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, MID + 118, "B · breadcrumbs from the path", size=15, anchor="start", weight="bold")
    s.tick(x + 10, MID + 146, size=7)
    s.text(x + 26, MID + 150, "R1 CR-P3G4-01 major, SEC-P3G4-01: a malformed escape", size=13,
           anchor="start")
    s.text(x + 26, MID + 170, "blanked the whole app; now shown as typed, 4e0d2868", size=13,
           anchor="start", colour=t.dim)

    # C -- theme ---------------------------------------------------------------------------------
    x = 1190
    s.circle(x + 22, MID + 8, 16, fill="gate")
    for k in range(8):
        a = k * math.pi / 4
        s.line(x + 22 + 21 * math.cos(a), MID + 8 + 21 * math.sin(a), x + 22 + 27 * math.cos(a),
               MID + 8 + 27 * math.sin(a), amount=0.2, passes=1, width=2)
    s.rect(Box(x + 62, MID - 4, 52, 24, "docs"), rx=12, colour=t.ink)
    s.circle(x + 102, MID + 8, 9, fill="surface")
    s.circle(x + 168, MID + 8, 16, fill="neutral")
    s.circle(x + 176, MID + 2, 13, fill="surface")
    s.text(x + 88, MID + 50, "`role=switch` `aria-checked`", size=12)
    s.text(x + 88, MID + 70, "named Dark theme", size=12.5, colour=t.dim)
    s.text(x, MID + 118, "C · light and dark", size=15, anchor="start", weight="bold")
    lines(s, x, MID + 150, ("follows the system until pressed,",
                            "then kept in `localStorage`",
                            "the `--sp-*` tokens of spectio-tokens.css"), size=13)

    s.line(30, REV - 60, W - 30, REV - 60, dashed=True, colour=t.muted)

    # review rounds ------------------------------------------------------------------------------
    x = 50
    s.text(x, REV - 18, "3 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(x, REV + 4, "code-reviewer and security-reviewer in parallel, then the simplifier", size=13,
           anchor="start", colour=t.dim)
    # (fixed on the branch?, major?) per finding, CR then SEC, as the worker report lists them
    rounds = (("R1", "CR changes, SEC approve", ((True, True), (False, False), (True, False), (False, False),
                                                 (False, False)), ((True, False),)),
              ("R2", "both approve", ((True, False), (False, False), (False, False), (True, False)),
               ((True, False), (False, False))),
              ("R3", "both approve", ((False, False),), ()))
    s.text(x + 44, REV + 28, "code-reviewer", size=12, anchor="start", colour=t.dim)
    s.text(x + 208, REV + 28, "security", size=12, anchor="start", colour=t.dim)
    for r, (name, verdict, cr, sec) in enumerate(rounds):
        y = REV + 40 + r * 44
        s.text(x, y + 18, name, size=16, anchor="start", weight="bold")
        for cx, group in ((x + 44, cr), (x + 208, sec)):
            for fixed, major in group:
                s.rect(Box(cx, y, 26, 26, "done" if fixed else "neutral"), rx=3,
                       colour=t.accent if major else None)
                if major:
                    s.text(cx + 9, y + 19, "M", size=13, weight="bold", colour=t.accent)
                if fixed:
                    s.tick(cx + (19 if major else 13), y + 12, size=4 if major else 6, width=2)
                cx += 30
        s.text(x + 300, y + 18, verdict, size=13.5, anchor="start")
    ly = REV + 186
    s.rect(Box(x + 44, ly - 14, 18, 18, "done"), rx=3)
    s.tick(x + 53, ly - 6, size=5, width=2)
    s.text(x + 70, ly, "fixed on the branch", size=12.5, anchor="start", colour=t.dim)
    s.rect(Box(x + 220, ly - 14, 18, 18, "neutral"), rx=3)
    s.text(x + 246, ly, "minor, left open", size=12.5, anchor="start", colour=t.dim)
    s.rect(Box(x + 390, ly - 14, 18, 18, "neutral"), rx=3, colour=t.accent)
    s.text(x + 399, ly, "M", size=11, weight="bold", colour=t.accent)
    s.text(x + 416, ly, "major", size=12.5, anchor="start", colour=t.dim)
    s.text(x, ly + 30, "IDs restart each round: R1 CR-03 and R2 CR-02 are the same pill fix,", size=13,
           anchor="start", colour=t.dim)
    s.text(x, ly + 50, "R1 CR-01 and SEC-01 the same escape fix · the simplifier changed nothing",
           size=13, anchor="start", colour=t.dim)
    s.text(x, ly + 70, "R2 CR-05 and SEC-01 are one screenshot fix: retaken as alice on login1", size=13,
           anchor="start", colour=t.dim)

    # left open ----------------------------------------------------------------------------------
    bx, bw = 700, 850
    s.shade(bx, REV - 34, bw, 250, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(bx + 30, REV - 6, size=11)
    s.text(bx + 52, REV, "left open after round 3, all minor", size=17, anchor="start", weight="bold")
    items = (("jsdom prints a scrollTo warning per router render in the tests", "R3 CR-P3G4-03"),
             ("the tablet rail hides the node text from sighted readers", "R1 CR-P3G4-04"),
             ("a long node name ends in an ellipsis, full name only in `aria-label`", "R1 CR-P3G4-05"),
             ("the phone pill is `role=img`, so a status change is not announced", "R2 CR-P3G4-04"),
             ("any decoded path segment becomes the page crumb, no limit", "R2 SEC-P3G4-02"))
    for i, (what, ref) in enumerate(items):
        y = REV + 34 + i * 29
        s.dot(bx + 30, y - 4, 3)
        s.text(bx + 44, y, what, size=13.5, anchor="start")
        s.text(bx + bw - 20, y, ref, size=12.5, anchor="end", colour=t.dim)

    s.prefix_key(50, H - 16, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: web/src/shell, web/src/api.ts at 7c5737c8 · worker report and review "
           "rounds of 2026-10-30 · inbox 89 · P2 G4", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-g4-paper-shell")
