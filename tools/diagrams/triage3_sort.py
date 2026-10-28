#!/usr/bin/env python3
"""Sorting figure for step TRIAGE3: 69 findings of the spikes round in, five decisions out.

Writes docs/assets/diagrams/triage3_sort_{light,dark}.{svg,png}.

One cell is one finding, the same size on both sides, so the figure is to
scale. Cell colour is the finding's severity; the row it lands in is the
triage decision. IDs, severities, decisions and inbox numbers come from the
Status lines and the Counts table of docs/reviews/spikes.md (TRIAGE3, 2026-10-28).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 960
CELL, GAP = 22, 4
M, N = "major", "minor"

# Findings that are not "minor, accepted": SPK-<step>-nn -> (severity, decision, inbox #).
# Decision: A accepted, P applied by the step, S inbox assumed, W inbox waiting, R rejected.
OTHER = {
    "T2-01": (M, "A", 0), "T2-07": (M, "A", 0), "T2-09": (M, "S", 56), "T2-11": (M, "W", 55),
    "T2-13": (N, "R", 0), "T2-20": (N, "R", 0), "T2-23": (M, "W", 55),
    "T3-05": (M, "A", 0), "T3-07": (N, "R", 0), "T3-08": (N, "R", 0), "T3-09": (M, "A", 0),
    "T3-11": (N, "P", 0), "T3-12": (N, "P", 0), "T3-13": (N, "P", 0), "T3-14": (N, "R", 0),
    "T3-15": (M, "W", 59), "T3-18": (N, "S", 60),
    "T4-01": (M, "W", 53), "T4-02": (M, "W", 53), "T4-03": (M, "W", 53), "T4-04": (N, "W", 53),
    "T4-05": (M, "A", 0), "T4-08": (N, "R", 0), "T4-09": (N, "S", 57), "T4-10": (N, "R", 0),
    "T4-12": (M, "W", 54), "T4-13": (N, "R", 0), "T4-14": (M, "W", 54),
    "T7-01": (N, "S", 58), "T7-04": (N, "W", 46),
}
STEPS = (("T2", "engine events", 27), ("T3", "SLURM clusters", 20),
         ("T4", "kind and Kueue", 17), ("T7", "real-pipeline corpus", 5))
FINDINGS = tuple(
    (f"SPK-{step}-{n:02d}",) + OTHER.get(f"{step}-{n:02d}", (N, "A", 0))
    for step, _, count in STEPS for n in range(1, count + 1)
)
SEV_ORDER = {M: 0, N: 1}


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=69)
    t = theme
    sev_fill = {M: "bar_orange", N: "bar_grey"}

    def cell(x: float, y: float, sev: str) -> None:
        # a major gets a thicker edge, so severity does not rely on hue alone
        sw = 2.2 if sev == M else 0.9
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{t.fill(sev_fill[sev])}" stroke="{t.ink}" stroke-width="{sw}"/>')

    def grid(x: float, y: float, items, per_row: int) -> float:
        items = sorted(items, key=lambda f: SEV_ORDER[f[1]])
        for i, f in enumerate(items):
            cell(x + (i % per_row) * (CELL + GAP), y + (i // per_row) * (CELL + GAP), f[1])
        return y + ((len(items) - 1) // per_row + 1) * (CELL + GAP)

    s.heading(40, 52, "TRIAGE3 · 69 findings of the spikes round sorted, none left open",
              "what T2, T3, T4 and T7 measured against the specs · triage policy applied as written · "
              "one cell = one finding, same size on both sides")

    # -- in: the four steps ---------------------------------------------------------------------
    y0 = 120
    for step, sub, count in STEPS:
        items = [f for f in FINDINGS if f[0].startswith(f"SPK-{step}-")]
        majors = sum(1 for f in items if f[1] == M)
        rows = (len(items) - 1) // 10 + 1
        h = 76 + rows * (CELL + GAP) + 8
        s.shade(30, y0, 300, h, fill="neutral", opacity=0.55)
        s.text(48, y0 + 32, f"{step} · {sub}", size=19, anchor="start")
        s.text(48, y0 + 56, f"{count} findings, {majors} major", size=15, anchor="start", colour=t.dim)
        grid(48, y0 + 72, items, per_row=10)
        s.arrow(336, y0 + h / 2, 392, 470, colour=t.muted, width=1.3)
        y0 += h + 14

    # -- the policy in the middle ---------------------------------------------------------------
    px, py = 400, 470
    s.page(px, py - 60, 92, 120, fill="docs", lines=4)
    s.cog(px + 86, py + 50, 16)
    s.text(px + 46, py + 92, "triage-policy.md", size=15)
    s.text(px + 46, py + 114, "re-checked with", size=13, colour=t.dim)
    s.text(px + 46, py + 132, "check_t2 and check_t3", size=13, colour=t.dim)

    # -- out: five decision rows ------------------------------------------------------------------
    rows = (
        ("A", "accepted", "confirmed by fixtures or job logs, minor or major, local fix", "done", "tick"),
        ("P", "applied by the step", "T3 already changed the dev-env rows it built", "blue", "tick"),
        ("S", "inbox, assumed", "proceeds now, marked “pending Thomas”", "gate", "hourglass"),
        ("W", "inbox, waiting", "reserved: roles and permissions, security posture, auth modes", "problem", "lock"),
        ("R", "rejected", "not reproduced, no difference with the spec, or a duplicate", "neutral", ""),
    )
    x0, y = 640, 96
    for code, label, note, fill, icon in rows:
        mine = [f for f in FINDINGS if f[2] == code]
        n_rows = (len(mine) - 1) // 35 + 1
        rh = 76 + n_rows * (CELL + GAP) + 30
        s.shade(x0, y, W - x0 - 30, rh, fill=fill, opacity=0.5)
        s.arrow(px + 112, py, x0 - 8, y + rh / 2, colour=t.muted, width=1.3)
        s.text(x0 + 20, y + 34, f"{len(mine)} · {label}", size=22, anchor="start", colour=t.ink)
        s.text(x0 + 20, y + 58, note, size=15, anchor="start", colour=t.dim)
        if icon == "tick":
            s.tick(W - 70, y + 30, size=10)
        elif icon == "hourglass":
            s.hourglass(W - 70, y + 30, size=11)
        elif icon == "lock":
            s.lock(W - 70, y + 30, size=12)
        else:
            s.cross(W - 70, y + 30, size=10, colour=t.muted)
        end = grid(x0 + 20, y + 72, mine, per_row=35)
        inbox = sorted({f[3] for f in mine if f[3]})
        if code == "A":
            s.text(x0 + 20, end + 18, "fixes land in six specs and decision 0001, in APPLY3",
                   size=14, anchor="start", colour=t.dim)
        elif code == "S":
            s.text(x0 + 20, end + 18, "inbox " + " · ".join(f"#{n}" for n in inbox)
                   + "  (assumed option recorded on each entry)", size=14, anchor="start", colour=t.dim)
        elif code == "W":
            s.text(x0 + 20, end + 18, "new inbox " + " · ".join(f"#{n}" for n in inbox if n != 46)
                   + ", and SPK-T7-04 joins the open #46  → APPLY3 leaves the sections they block untouched",
                   size=14, anchor="start", colour=t.dim)
        y += rh + 12

    # -- keys --------------------------------------------------------------------------------------
    kx, ky = 40, H - 60
    for i, (sev, meaning) in enumerate(((M, "major · 14, a real problem that will cost rework"),
                                        (N, "minor · 55, worth fixing, low risk   ·   no blocker in this round"))):
        x = kx + (0, 600)[i]
        cell(x, ky - 16, sev)
        s.text(x + CELL + 10, ky, meaning, size=14, anchor="start", colour=t.ink)
    s.text(kx, H - 20, "Source: Status lines and Counts table of docs/reviews/spikes.md "
                       "(TRIAGE3, 2026-10-28) · tools/diagrams/triage3_sort.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    assert len(FINDINGS) == 69
    main_for(build, "triage3_sort")
