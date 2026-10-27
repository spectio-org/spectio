#!/usr/bin/env python3
"""Sorting figure for step TRIAGE2: 61 findings of R3 and R6 in, four decisions out.

Writes docs/assets/diagrams/triage2_sort_{light,dark}.{svg,png}.

One cell is one finding, the same size on both sides, so the figure is to
scale. Cell colour is the finding's severity; the row it lands in is the
triage decision. IDs, severities, decisions and inbox numbers come from the
Status lines of R3-journeys.md and R6-contract.md (TRIAGE2, 2026-10-27).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 820
CELL, GAP = 22, 4
B, M, N = "blocker", "major", "minor"

# (id, severity, decision, inbox #); decision: A accepted, S inbox assumed, W inbox waiting
R3 = (
    ("SR-062", B, "S", 32), ("SR-055", B, "S", 35), ("CH-041", B, "S", 35), ("CH-042", B, "S", 32),
    ("SR-057", B, "W", 34), ("SR-058", B, "W", 34), ("SR-054", B, "W", 36),
    ("SR-063", M, "S", 32), ("SR-059", M, "S", 33), ("UX-243", M, "S", 32),
    ("SR-056", M, "W", 34), ("SR-067", M, "W", 35),
    ("SR-061", M, "S", 40), ("CH-047", M, "S", 40), ("CH-043", M, "S", 40), ("SR-064", M, "A", 0),
    ("CH-044", M, "A", 0), ("CH-046", M, "S", 40), ("CH-048", M, "S", 40), ("CH-049", M, "A", 0),
    ("CH-050", M, "S", 40), ("SR-065", M, "S", 40), ("UX-250", M, "S", 40), ("CH-045", M, "A", 0),
    ("SR-066", M, "A", 0), ("CH-051", N, "S", 40), ("UX-249", N, "A", 0),
)
R6 = (
    ("SR-080", M, "W", 36), ("SR-091", M, "W", 37),
    ("SR-081", M, "S", 32), ("SR-084", M, "S", 38), ("SR-085", M, "S", 32), ("SR-088", M, "S", 38),
    ("UX-272", M, "S", 38), ("UX-274", M, "S", 39), ("UX-275", M, "S", 39), ("UX-278", M, "S", 39),
    ("UX-279", M, "S", 39), ("UX-280", M, "S", 32), ("UX-281", M, "S", 32), ("UX-282", M, "S", 32),
    ("UX-284", M, "S", 32), ("UX-285", M, "S", 39), ("UX-286", M, "S", 39), ("UX-291", N, "S", 39),
    ("SR-082", M, "S", 40), ("SR-083", M, "A", 0), ("SR-086", M, "A", 0), ("SR-087", M, "A", 0),
    ("SR-089", M, "A", 0), ("SR-090", M, "A", 0), ("UX-270", M, "A", 0), ("UX-271", M, "A", 0),
    ("UX-273", M, "A", 0), ("UX-276", M, "A", 0), ("UX-277", M, "A", 0), ("UX-283", M, "A", 0),
    ("UX-287", N, "A", 0), ("UX-288", N, "A", 0), ("UX-289", N, "A", 0), ("UX-290", N, "A", 0),
)
SEV_ORDER = {B: 0, M: 1, N: 2}


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=53)
    t = theme
    sev_fill = {B: "problem", M: "bar_orange", N: "bar_grey"}

    def cell(x: float, y: float, sev: str) -> None:
        # a blocker gets a thick red edge, so severity does not rely on hue alone
        stroke, sw = (t.accent, 2.4) if sev == B else (t.ink, 0.9)
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{t.fill(sev_fill[sev])}" stroke="{stroke}" stroke-width="{sw}"/>')

    def grid(x: float, y: float, items, per_row: int) -> float:
        items = sorted(items, key=lambda f: SEV_ORDER[f[1]])
        for i, f in enumerate(items):
            cell(x + (i % per_row) * (CELL + GAP), y + (i // per_row) * (CELL + GAP), f[1])
        return y + ((len(items) - 1) // per_row + 1) * (CELL + GAP)

    s.heading(40, 52, "TRIAGE2 · 61 findings sorted, none left open",
              "R3 journeys and R6 API contract, triage policy applied as written · one cell = one finding, "
              "same size on both sides")

    # -- in: the two rounds -------------------------------------------------------------------
    for k, (name, sub, items) in enumerate((("R3", "journeys", R3), ("R6", "API contract", R6))):
        y0 = 150 + k * 250
        s.shade(30, y0, 300, 220 if k else 200, fill="neutral", opacity=0.55)
        s.text(48, y0 + 34, f"{name} · {sub}", size=20, anchor="start")
        s.text(48, y0 + 58, f"{len(items)} findings", size=15, anchor="start", colour=t.dim)
        grid(48, y0 + 76, items, per_row=10)

    # -- the policy in the middle ---------------------------------------------------------------
    px, py = 400, 330
    s.page(px, py - 60, 92, 120, fill="docs", lines=4)
    s.cog(px + 86, py + 50, 16)
    s.text(px + 46, py + 92, "triage-policy.md", size=15)
    s.arrow(338, py, px - 10, py, colour=t.muted, width=1.6)

    # -- out: four decision rows ------------------------------------------------------------------
    rows = (
        ("A", "accepted", "applied to the specs in APPLY2", "done", t.good),
        ("S", "inbox, assumed", "proceeds now, marked “pending Thomas”", "gate", t.warn),
        ("W", "inbox, waiting", "reserved: scope, auth, security posture, engine delivery", "problem", t.accent),
        ("R", "rejected", "nothing was a duplicate, style-only or not reproducible", "neutral", t.muted),
    )
    every = R3 + R6
    x0, ry, rh = 640, 110, 130
    for j, (code, label, note, fill, ink) in enumerate(rows):
        y = ry + j * (rh + 14)
        mine = [f for f in every if f[2] == code]
        s.shade(x0, y, W - x0 - 30, rh, fill=fill, opacity=0.5)
        s.arrow(px + 112, py, x0 - 8, y + rh / 2, colour=t.muted, width=1.3)
        s.text(x0 + 20, y + 34, f"{len(mine)} · {label}", size=22, anchor="start", colour=t.ink)
        s.text(x0 + 20, y + 58, note, size=15, anchor="start", colour=t.dim)
        if code == "A":
            s.tick(W - 70, y + 30, size=10)
        elif code == "S":
            s.hourglass(W - 70, y + 30, size=11)
        elif code == "W":
            s.lock(W - 70, y + 30, size=12)
        if not mine:
            s.raw(f'<rect x="{x0 + 20}" y="{y + 76}" width="{CELL}" height="{CELL}" rx="3" fill="none" '
                  f'stroke="{t.muted}" stroke-width="1" stroke-dasharray="3 3"/>')
            s.text(x0 + 56, y + 93, "0", size=15, anchor="start", colour=t.dim)
            continue
        end = grid(x0 + 20, y + 76, mine, per_row=35)
        inbox = sorted({f[3] for f in mine if f[3]})
        if code == "S":
            s.text(x0 + 20, end + 20, "inbox " + " · ".join(f"#{n}" for n in inbox)
                   + "  (assumed option recorded on each entry)", size=14, anchor="start", colour=t.dim)
        elif code == "W":
            ids = " · ".join(f[0] for f in sorted(mine, key=lambda f: (SEV_ORDER[f[1]], f[0])))
            s.text(x0 + 220, y + 93, ids, size=14.5, anchor="start", colour=t.ink)
            s.text(x0 + 20, end + 20, "inbox " + " · ".join(f"#{n}" for n in inbox)
                   + "  → APPLY2 leaves the sections they block untouched", size=14, anchor="start",
                   colour=t.dim)
        elif code == "A":
            s.text(x0 + 20, end + 20, "minor or major, at most two sections of the owning spec; never a blocker",
                   size=14, anchor="start", colour=t.dim)

    # -- keys --------------------------------------------------------------------------------------
    kx, ky = 40, H - 92
    for i, (sev, meaning) in enumerate(((B, "blocker · implementation cannot start, or would build the wrong thing"),
                                        (M, "major · a real problem that will cost rework"),
                                        (N, "minor · worth fixing, low risk"))):
        x = kx + (0, 640, 1060)[i]
        cell(x, ky - 16, sev)
        s.text(x + CELL + 10, ky, meaning, size=14, anchor="start", colour=t.ink)
    s.prefix_key(kx, ky + 34, ("SR", "CH", "UX"))
    s.text(kx, H - 20, "Source: Status lines of docs/reviews/R3-journeys.md and R6-contract.md "
                       "(TRIAGE2, 2026-10-27) · tools/diagrams/triage2_sort.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "triage2_sort")
