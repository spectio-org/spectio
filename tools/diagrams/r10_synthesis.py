#!/usr/bin/env python3
"""Synthesis and go / no-go for step R10: the review backlog narrowed against the 0.0.1 cut.

Writes docs/assets/diagrams/r10_synthesis_{light,dark}.{svg,png}.

Every number comes from docs/reviews/R10-synthesis.md (2026-10-28):
- §1 status table: 450 findings read; 114 applied, 200 partly applied, 123 open (93 inbox and
  30 accepted, not applied), 12 rejected, 1 closed without edit;
- §2 totals: the 123 open are 8 blockers, 74 majors, 41 minors; blockers that touch 0.0.1 with an
  open status are SR-001, SR-054 and SEC-102, so the 5 other open blockers are deferred by the cut:
  SR-057 and SR-058 (gates), SR-002 and SEC-101 (shared server), DL-101 (depictio);
- §3a: 12 of the 82 open blockers and majors touch the cut (3 blockers, 9 majors); 13 rows for P1;
- §3b: the other 70 by the feature that left the cut (gates 16, relaunch 3, users 17, shared
  server 11, Kubernetes 6, depictio 6, later features 4, operations 7);
- §5: 7 of the 12 are decided or applied; GO for P1 now, code after P1 under C1-C4; the no-go
  trigger (login nodes forbid long-running user processes or SSH forwarding, Q1 and Q3).

The funnel rows share one scale (PX pixels per finding). The bins and the 12 cells zoom in: one
cell is one finding.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 1100
X0, PX, BAR = 70, 2.6, 38  # funnel: left edge, pixels per finding, bar height

STATUS = ((123, "problem", ""), (200, "work", "200 partly applied"),
          (114, "done", "114 applied"), (13, "neutral", ""))  # 12 rejected + 1 closed
OPEN = (("blocker", 8), ("major", 74), ("minor", 41))
TOUCH, DECIDED = 12, 7
# §3b: (count, open blockers among them, name, detail)
BINS = (
    (17, 0, "users", "sign-in, roles, sharing"),
    (16, 2, "QC gates", "checks, stages"),
    (11, 2, "shared server", "remote runners"),
    (7, 0, "operations", "packaging, backup"),
    (6, 0, "Kubernetes", "and slurmrestd"),
    (6, 1, "depictio", "hand-off"),
    (4, 0, "later features", "WES, batches"),
    (3, 0, "relaunch", "history, pause"),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=10)
    t = theme
    sev_fill = {"blocker": "problem", "major": "bar_orange", "minor": "bar_grey"}

    def cell(x: float, y: float, size: float, fill: str, blocker: bool = False) -> None:
        # a blocker gets a thick red edge, so severity does not rely on hue alone
        edge, sw = (t.accent, 2.6) if blocker else (t.ink, 0.9)
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" rx="2.5" '
              f'fill="{t.fill(fill)}" stroke="{edge}" stroke-width="{sw}"/>')

    def bar(y: float, segments) -> None:
        x = X0
        for n, fill, label in segments:
            w = n * PX
            s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR}" rx="3" '
                  f'fill="{t.fill(fill)}" stroke="{t.ink}" stroke-width="1.2"/>')
            if label:
                s.text(x + w / 2, y + BAR + 22, label, size=15, colour=t.dim)
            x += w

    def carry(y1: float, y2: float, n: int) -> None:
        """The part of a bar that goes on to the next row, as a pale column."""
        s.shade(X0, y1, n * PX, y2 - y1, fill="neutral", opacity=0.7)
        for x in (X0, X0 + n * PX):
            s.line(x, y1, x, y2, colour=t.muted, width=1.2, passes=1, amount=0.5, dashed=True)

    def swatch(x: float, y: float, fill: str, label: str, blocker: bool = False) -> float:
        cell(x, y - 13, 16, fill, blocker)
        s.text(x + 24, y, label, size=16, anchor="start")
        return x + 24 + len(label) * 8.6 + 26

    s.heading(X0, 52, "R10 · what in 450 review findings still stands before 0.0.1",
              "the narrowed 0.0.1: one user, `spectio serve` on a SLURM login node, launch and monitor, "
              "three plain screens · funnel rows to one scale")

    # -- 1 · all findings read ---------------------------------------------------------------------
    y1 = 150
    s.text(X0, y1 - 14, "1 · 450 findings read, by their Status line", size=19, anchor="start")
    bar(y1, STATUS)
    end = X0 + 450 * PX
    s.text(end + 12, y1 + BAR / 2 + 5, "13 rejected or closed", size=14, anchor="start", colour=t.dim)
    for k in range(3):
        s.page(1460 + k * 16, y1 - 52 + k * 12, 64, 84, fill="docs", lines=4)
    s.text(1530, y1 + 74, "12 round files", size=14, colour=t.dim)
    s.text(1530, y1 + 92, "R1 to R12", size=14, colour=t.dim)

    # -- 2 · still open ----------------------------------------------------------------------------
    y2 = 300
    carry(y1 + BAR, y2 - 30, 123)
    s.text(X0 + 123 * PX / 2, y1 + BAR + 22, "123 open", size=15, colour=t.ink)
    s.text(X0, y2 - 14, "2 · 123 still open: inbox, or accepted and not applied", size=19, anchor="start")
    bar(y2, [(n, sev_fill[sev], "") for sev, n in OPEN])
    x = X0 + 123 * PX + 30
    for sev, n in OPEN:
        x = swatch(x, y2 + BAR / 2 + 6, sev_fill[sev], f"{n} {sev}s", blocker=sev == "blocker")
    s.text(X0 + 123 * PX + 30, y2 + BAR + 22,
           "the 41 minors stop here: none is a precondition for 0.0.1",
           size=14.5, anchor="start", colour=t.dim)

    # the 0.0.1 cut itself: one user, a login node, a tunnel, three screens
    ux = 1180
    s.text(ux, y2 - 14, "the 0.0.1 cut", size=17, anchor="start")
    s.hpc_node(ux, y2 + 4, w=54, h=70, busy=2, slots=3)
    s.text(ux + 27, y2 + 96, "login node", size=14, colour=t.dim)
    s.text(ux + 27, y2 + 114, "`spectio serve`", size=13)
    s.arrow(ux + 66, y2 + 40, ux + 196, y2 + 40, colour=t.ink, width=1.5)
    s.link(ux + 131, y2 + 22, 12)
    s.text(ux + 131, y2 + 66, "SSH tunnel,", size=13, colour=t.dim)
    s.text(ux + 131, y2 + 83, "token link", size=13, colour=t.dim)
    s.browser(ux + 206, y2 + 4, 170, 104)
    for k, w in enumerate((120, 96, 132)):
        s.line(ux + 222, y2 + 50 + k * 18, ux + 222 + w, y2 + 50 + k * 18, colour=t.muted, width=1.6,
               passes=1, amount=0.4)
    s.text(ux + 291, y2 + 132, "three plain screens", size=14, colour=t.dim)

    # -- 3 · blockers and majors sorted against the cut ------------------------------------------
    y3 = 440
    carry(y2 + BAR, y3 - 30, 82)
    s.text(X0, y3 - 14, "3 · 82 open blockers and majors, held against the 0.0.1 cut",
           size=19, anchor="start")
    bar(y3, ((TOUCH, "input", ""), (82 - TOUCH, "cached", "")))
    s.text(X0 + 82 * PX + 20, y3 + BAR / 2 + 6, "12 touch 0.0.1  ·  70 left with their feature",
           size=16, anchor="start")

    # the 70, zoomed: one bin per feature that left the cut
    bx0, bw, bgap, btop = 320, 124, 34, 580
    s.text(bx0, btop - 46, "70 wait for features that left 0.0.1", size=17, anchor="start")
    s.text(bx0 + 420, btop - 46, "zoom: one cell = one finding, red edge = blocker",
           size=14, anchor="start", colour=t.dim)
    s.arrow(X0 + TOUCH * PX + 60, y3 + BAR + 6, bx0 - 14, btop + 20, colour=t.muted, width=1.4)
    for i, (n, blockers, name, detail) in enumerate(BINS):
        cx = bx0 + bw / 2 + i * (bw + bgap)
        s.bucket(cx, btop, bw, 84, fill="neutral")
        per_row, c, g = 6, 11, 3
        gx = cx - (per_row * (c + g) - g) / 2
        for k in range(n):
            cell(gx + (k % per_row) * (c + g), btop + 14 + (k // per_row) * (c + g), c,
                 "problem" if k < blockers else "bar_orange", blocker=k < blockers)
        s.text(cx, btop + 112, f"{n} · {name}", size=16)
        s.text(cx, btop + 132, detail, size=13, colour=t.dim)
    assert sum(b[0] for b in BINS) == 82 - TOUCH

    # -- 4 · what touches 0.0.1 ----------------------------------------------------------------------
    y4 = 790
    carry(y3 + BAR, y4 - 30, TOUCH)
    s.text(X0, y4 - 14, "4 · 12 touch 0.0.1: 3 blockers, 9 majors", size=19, anchor="start")
    bar(y4, ((DECIDED, "done", ""), (TOUCH - DECIDED, "work", "")))
    cx0, cs = X0 + TOUCH * PX + 40, 24
    for k in range(TOUCH):
        x = cx0 + k * (cs + 6)
        cell(x, y4 + (BAR - cs) / 2, cs, "done" if k < DECIDED else "work", blocker=k < 3)
        if k < DECIDED:
            s.tick(x + cs / 2, y4 + BAR / 2, size=6, colour=t.ink, width=1.8)
    tx = cx0 + TOUCH * (cs + 6) + 14
    s.text(tx, y4 + 14, "7 already decided or applied in their 0.0.1 part", size=15.5, anchor="start")
    s.text(tx, y4 + 36, "5 still to settle, three of them waiting on Thomas (D2, D3)", size=15.5,
           anchor="start", colour=t.dim)

    # -- 5 · P1 ----------------------------------------------------------------------------------------
    py = 880
    s.arrow(X0 + 15, y4 + BAR + 4, X0 + 15, py - 4, colour=t.muted, width=1.4)
    s.page(X0 - 16, py, 84, 108, fill="docs", lines=5)
    s.cog(X0 + 60, py + 96, 11)
    s.text(X0 + 96, py + 24, "5 · P1 turns the 13 rows of §3a", size=19, anchor="start")
    s.text(X0 + 96, py + 48, "into tasks with tests", size=19, anchor="start")
    s.text(X0 + 96, py + 76, "first task: api §14, the driven-run spool events", size=14.5,
           anchor="start", colour=t.dim)
    s.text(X0 + 96, py + 98, "one test per §15.3 security requirement", size=14.5,
           anchor="start", colour=t.dim)
    s.arrow(560, py + 54, 600, py + 54, colour=t.muted, width=1.4)

    # -- 6 · the GO gate ---------------------------------------------------------------------------------
    g1, g2, gb = 650, 830, py + 82
    s.gate(g1, gb, w=80, h=70, state="passed")
    s.text(g1, gb + 24, "GO for P1 now", size=16, colour=t.good)
    s.arrow(g1 + 60, gb - 30, g2 - 60, gb - 30, colour=t.muted, width=1.4)
    s.gate(g2, gb, w=80, h=70, state="closed")
    s.text(g2, gb + 24, "code after P1", size=16)
    cx = g2 + 66
    for i, cond in enumerate(("C1 · Thomas answers inbox #52",
                              "C2 · api §14 driven part is the first task",
                              "C3 · D1 to D4 answered, or recorded as assumed",
                              "C4 · rows 1 to 13 become tasks with tests")):
        s.text(cx, py + 6 + i * 21, cond, size=14, anchor="start", colour=t.dim)
    s.step((g1 + g2) / 2 + 60, py + 140, 6, "GO for P1 now; code after P1 under conditions C1–C4", size=18)

    # -- no-go trigger -------------------------------------------------------------------------------------
    nx = 1290
    s.hpc_node(nx, py - 6, w=50, h=64, busy=1, slots=3)
    s.cross(nx + 25, py + 26, size=20)
    s.text(nx + 25, py + 82, "login node", size=13, colour=t.dim)
    s.warning(nx + 70, py + 6, size=12)
    s.text(nx + 90, py + 12, "no-go trigger", size=17, anchor="start", colour=t.accent)
    for i, ln in enumerate(("the login node forbids", "long-running processes", "or SSH forwarding (Q1, Q3):",
                            "the cut goes back to Thomas")):
        s.text(nx + 90, py + 36 + i * 20, ln, size=14, anchor="start", colour=t.dim)

    s.text(W - 40, H - 18, "Source: docs/reviews/R10-synthesis.md §1, §2, §3, §5 (2026-10-28) · "
                           "tools/diagrams/r10_synthesis.py", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    assert sum(n for n, *_ in STATUS) == 450
    assert sum(n for _, n in OPEN) == 123 and OPEN[0][1] + OPEN[1][1] == 82
    main_for(build, "r10_synthesis")
