#!/usr/bin/env python3
"""Figure for step APPLY2: what the R3 and R6 findings changed in the specs, and what is left.

Writes docs/assets/diagrams/apply2_specs_{light,dark}.{svg,png}.

Left: one cell per finding (to scale), applied in full, partly applied, or untouched
because it waits for Thomas; a dot marks a fix assumed pending an inbox answer.
Middle: lines added and removed per spec (`git diff --numstat docs/specs`, to scale),
then the parts left untouched because an inbox entry blocks them. Right: the parts
deferred to UI boards and tools, one bar unit per finding. Sources: the Status lines of
R3-journeys.md and R6-contract.md, and the APPLY2 entry of docs/decisions/log.md
(2026-10-27).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 870
CELL, GAP = 22, 4

APPLIED = ("CH-043", "SR-064", "CH-046", "SR-059", "SR-065", "CH-045", "SR-066")
R3_PARTLY = ("SR-062", "SR-055", "CH-041", "CH-042", "SR-063", "UX-243", "SR-061", "CH-047", "CH-044",
             "CH-048", "CH-049", "CH-050", "UX-250", "CH-051", "UX-249")
R3_WAITING = ("SR-054", "SR-056", "SR-057", "SR-058", "SR-067")
R6_PARTLY = tuple(f"SR-0{n}" for n in range(81, 91)) + tuple(f"UX-{n}" for n in range(270, 292))
R6_WAITING = ("SR-080", "SR-091")
ASSUMED = {
    "SR-062", "CH-042", "SR-063", "UX-243", "SR-081", "SR-085", "UX-280", "UX-281", "UX-282", "UX-284",  # 32
    "SR-059",  # 33
    "SR-055", "CH-041",  # 35
    "SR-084", "SR-088", "UX-272",  # 38
    "UX-274", "UX-275", "UX-278", "UX-279", "UX-285", "UX-286", "UX-291",  # 39
    "SR-061", "CH-047", "CH-043", "CH-046", "CH-048", "CH-050", "SR-065", "UX-250", "CH-051", "SR-082",  # 40
}
# git diff --numstat docs/specs (APPLY2 working tree, 2026-10-27): (spec, added, removed)
SPECS = (
    ("api-and-data-model", 151, 49), ("ui-spec", 44, 25), ("architecture-plugins-and-packaging", 18, 0),
    ("schedulers-and-monitoring", 14, 0), ("synthesis", 10, 4), ("checking-scenarios", 6, 2),
    ("cli-and-shared-libraries", 4, 4), ("admin-and-operations", 3, 1), ("mvp-0.0.1", 2, 1),
    ("dev-environment-and-testing", 1, 1),
)
# findings per deferred target, from the "Deferred" lines of the APPLY2 log entry
BOARDS = (
    ("RunDetail", 17), ("ReviewReport", 5), ("Launch", 5), ("RunsRows", 5), ("RelaunchDialog", 4),
    ("RunsTable", 4), ("LaunchSnakemake", 3), ("RunDetailReconnect", 2), ("RunsCompare", 2), ("Legend", 2),
    ("AppSidebar, AppTopbar", 2), ("RunFailed (local)", 1), ("RunTasks, RunLogs (new)", 1),
    ("Manifest", 1), ("EnvLocal (0.0.1)", 1),
)
TOOLS = (("openapi draft spike", 8), ("engine mapping, spike T2", 1), ("spectio-sdk schemas", 1),
         ("later compare endpoints", 1))
BLOCKED = (("#36 ingest contract", 5), ("#34 rnaseq stages, gates file", 4), ("#16 pause and stop", 4),
           ("#37 loopback protection", 1), ("#13 API limits", 1), ("#19 gate verbs", 1),
           ("#20 environment files", 1), ("#25 lease renewal", 1))


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=61)
    t = theme

    def cell(x: float, y: float, fid: str, kind: str) -> None:
        if kind == "waiting":
            s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" fill="none" '
                  f'stroke="{t.muted}" stroke-width="1.2" stroke-dasharray="3 3"/>')
            return
        fill = t.fill("done" if kind == "applied" else "work")
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{fill}" stroke="{t.ink}" stroke-width="0.9"/>')
        if fid in ASSUMED:
            s.dot(x + CELL / 2, y + CELL / 2, 3.6, colour=t.ink)

    def grid(x: float, y: float, groups, per_row: int = 12) -> float:
        i = 0
        for kind, ids in groups:
            for fid in ids:
                cell(x + (i % per_row) * (CELL + GAP), y + (i // per_row) * (CELL + GAP), fid, kind)
                i += 1
        return y + ((i - 1) // per_row + 1) * (CELL + GAP)

    def bars(x: float, y: float, rows, unit: float, fill: str, label_w: float, step: float = 24) -> float:
        for k, (label, n) in enumerate(rows):
            yy = y + k * step
            s.text(x + label_w - 8, yy + 14, label, size=14, anchor="end", colour=t.ink)
            s.raw(f'<rect x="{x + label_w:.1f}" y="{yy + 2:.1f}" width="{n * unit:.1f}" height="16" rx="2" '
                  f'fill="{t.fill(fill)}" stroke="{t.ink}" stroke-width="0.8"/>')
            s.text(x + label_w + n * unit + 8, yy + 15, str(n), size=13.5, anchor="start", colour=t.dim)
        return y + len(rows) * step

    s.heading(40, 52, "APPLY2 · 54 of 61 findings reached the specs",
              "R3 journeys and R6 API contract · 7 applied in full, 47 partly, 7 untouched (waiting for Thomas) "
              "· 33 fixes assumed pending an inbox answer")

    # -- left: the findings ---------------------------------------------------------------------
    s.shade(30, 120, 350, 650, fill="neutral", opacity=0.5)
    s.text(48, 152, "R3 · journeys", size=20, anchor="start")
    s.text(48, 176, "27 findings", size=15, anchor="start", colour=t.dim)
    end = grid(48, 192, (("applied", APPLIED), ("partly", R3_PARTLY), ("waiting", R3_WAITING)))
    s.text(48, end + 46, "R6 · API contract", size=20, anchor="start")
    s.text(48, end + 70, "34 findings", size=15, anchor="start", colour=t.dim)
    end = grid(48, end + 86, (("partly", R6_PARTLY), ("waiting", R6_WAITING)))
    ky = end + 40
    for k, (kind, label) in enumerate((("applied", "applied in full (7)"),
                                       ("partly", "partly applied (47)"),
                                       ("waiting", "untouched, waits for Thomas (7)"))):
        cell(48, ky + k * 32, "", kind)
        s.text(80, ky + k * 32 + 16, label, size=14, anchor="start", colour=t.ink)
    cell(48, ky + 96, "SR-062", "partly")
    s.text(80, ky + 96 + 16, "dot: assumed, pending inbox (33)", size=14, anchor="start",
           colour=t.ink)

    # -- middle: specs edited, then blocked parts --------------------------------------------------
    mx = 410
    s.shade(mx, 120, 640, 400, fill="docs", opacity=0.45)
    s.page(mx + 18, 136, 34, 44, fill="surface", lines=3)
    s.text(mx + 64, 156, "10 specs edited", size=20, anchor="start")
    s.text(mx + 64, 178, "lines added + and removed − (to scale)", size=14, anchor="start", colour=t.dim)
    unit, lx = 1.9, mx + 250
    for k, (name, add, rem) in enumerate(SPECS):
        y = 200 + k * 30
        s.text(lx - 10, y + 15, name, size=13.5, anchor="end", colour=t.ink)
        s.raw(f'<rect x="{lx:.1f}" y="{y + 2:.1f}" width="{add * unit:.1f}" height="9" rx="2" '
              f'fill="{t.fill("done")}" stroke="{t.ink}" stroke-width="0.7"/>')
        s.raw(f'<rect x="{lx:.1f}" y="{y + 13:.1f}" width="{max(rem * unit, 1):.1f}" height="9" rx="2" '
              f'fill="{t.fill("problem")}" stroke="{t.ink}" stroke-width="0.7"/>')
        s.text(lx + add * unit + 8, y + 16, f"+{add} −{rem}", size=13, anchor="start", colour=t.dim)

    s.shade(mx, 540, 640, 230, fill="violet", opacity=0.35)
    s.lock(mx + 32, 566, size=12)
    s.text(mx + 56, 572, "left untouched: an inbox entry blocks the section", size=17, anchor="start")
    bars(mx + 10, 588, BLOCKED, 18, "violet", 250, step=22)

    # -- right: deferred to boards and tools -------------------------------------------------------
    rx = 1080
    s.shade(rx, 120, W - rx - 30, 650, fill="gate", opacity=0.4)
    s.hourglass(rx + 26, 148, size=10)
    s.text(rx + 48, 156, "deferred: one bar unit = one finding", size=17, anchor="start")
    s.text(rx + 20, 190, "UI boards (15)", size=16, anchor="start", colour=t.ink)
    end = bars(rx + 10, 200, BOARDS, 13, "work", 190, step=23)
    s.text(rx + 20, end + 30, "tools and spikes (4)", size=16, anchor="start", colour=t.ink)
    bars(rx + 10, end + 40, TOOLS, 13, "blue", 190, step=23)

    s.arrow(384, 330, mx - 6, 330, colour=t.muted, width=1.4)
    s.arrow(mx + 640, 330, rx - 6, 330, colour=t.muted, width=1.4)

    # -- keys --------------------------------------------------------------------------------------
    s.prefix_key(40, H - 70, ("SR", "CH", "UX"))
    s.text(40, H - 26, "Sources: Status lines of docs/reviews/R3-journeys.md and R6-contract.md, "
                       "the APPLY2 entry of docs/decisions/log.md, git diff --numstat docs/specs (2026-10-27) "
                       "· tools/diagrams/apply2_specs.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply2_specs")
