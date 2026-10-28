#!/usr/bin/env python3
"""Figure for step APPLY3: what the spikes-round findings changed in the specs, and what waits.

Writes docs/assets/diagrams/apply3_specs_{light,dark}.{svg,png}.

Left: one cell per finding of docs/reviews/spikes.md (to scale), grouped by step, by the
outcome on its Status line; a dot marks a fix applied on an assumed inbox answer.
Middle: lines added and removed per file (`git diff --numstat 90180cb <APPLY3 head> --
docs/specs docs/decisions/0001-nextflow-through-nf-spectio.md`, to scale), then the work
left outside the specs. Right: what waits for Thomas, one bar unit per finding, and the
assumed answers already applied. Sources: the Status lines of spikes.md (2026-10-28) and
the TRIAGE3 inbox block of docs/reviews/inbox.md.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 860
CELL, GAP = 22, 4


def ids(step: str, nums: str) -> tuple[str, ...]:
    return tuple(f"SPK-{step}-{n}" for n in nums.split())


# Outcome per finding, read from the Status lines of docs/reviews/spikes.md after APPLY3.
STEPS = (
    ("T2 · engine events", 27, (
        ("applied", ids("T2", "01 02 03 04 05 06 07 08 09 10 12 14 15 16 17 18 19 21 22 24 25 26 27"),),
        ("waiting", ids("T2", "11 23")),
        ("rejected", ids("T2", "13 20")),
    )),
    ("T3 · SLURM", 20, (
        ("applied", ids("T3", "01 02 03 04 05 06 09 10 16 17 18 19")),
        ("partly", ids("T3", "20")),
        ("by_t3", ids("T3", "11 12 13")),
        ("waiting", ids("T3", "15")),
        ("rejected", ids("T3", "07 08 14")),
    )),
    ("T4 · Kubernetes", 17, (
        ("applied", ids("T4", "05 06 07 11 16 17")),
        ("partly", ids("T4", "02 09 15")),
        ("waiting", ids("T4", "01 03 04 12 14")),
        ("rejected", ids("T4", "08 10 13")),
    )),
    ("T7 · corpus", 5, (
        ("applied", ids("T7", "03")),
        ("pr36", ids("T7", "02 05")),
        ("partly", ids("T7", "01")),
        ("waiting", ids("T7", "04")),
    )),
)
# applied on an assumed answer (marker "assumed — pending Thomas, inbox #n" in the spec text)
ASSUMED = {"SPK-T2-08", "SPK-T2-09", "SPK-T3-18", "SPK-T4-09", "SPK-T7-01"}

# git diff --numstat 90180cb <APPLY3 head> (90180cb = autopilot/integration merged into APPLY3)
SPECS = (
    ("dev-environment-and-testing", 25, 13), ("schedulers-and-monitoring", 22, 11),
    ("api-and-data-model", 13, 7), ("synthesis", 13, 9), ("checking-scenarios", 7, 3),
    ("architecture-plugins-and-packaging", 3, 3), ("decision 0001 (nf-spectio)", 3, 1),
    ("ui-spec", 1, 1),
)
# work left outside the specs, from the "pending:" part of the partly-applied Status lines
FOLLOW_UPS = (
    "SPK-T3-20 · read-only node tools in dev/slurm, dev/k8s",
    "SPK-T4-15 · digests, nf-k8s sha256, --only (with #46)",
    "SPK-T4-09 · ci.yml calls pipelines-slurm / -k8s",
    "SPK-T7-01 · autopilot reads the nightly runs",
    "SPK-T4-02 · the Role lists, after inbox #53",
)
# waits for Thomas: not in the specs (inbox entry, findings)
WAITING = (
    ("#53 Kubernetes Roles", 4), ("#54 task-pod tokens, shared namespace", 2),
    ("#55 what engine events may carry", 2), ("#59 slurmrestd token and user", 1),
    ("#46 corpus pins (existing)", 1),
)
ASSUMED_BARS = (
    ("#32 resume reuses checks", 1), ("#56 attempt state aborted", 1),
    ("#57 pipeline workflows standalone", 1), ("#58 nightly runs read", 1),
    ("#60 slurm-versions planned", 1),
)
LEGEND = (
    ("applied", "applied by APPLY3 (42)"),
    ("pr36", "applied by PR #36, corpus retry (2)"),
    ("partly", "partly applied (5)"),
    ("waiting", "waits for Thomas (9)"),
    ("by_t3", "applied by T3 before triage (3)"),
    ("rejected", "rejected (8)"),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=63)
    t = theme

    def cell(x: float, y: float, fid: str, kind: str) -> None:
        if kind == "waiting":
            s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" fill="{t.fill("violet")}" '
                  f'stroke="{t.muted}" stroke-width="1.3" stroke-dasharray="3 3"/>')
            return
        if kind == "rejected":
            s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" fill="none" '
                  f'stroke="{t.muted}" stroke-width="0.9"/>')
            s.raw(f'<line x1="{x + 6:.1f}" y1="{y + 6:.1f}" x2="{x + CELL - 6:.1f}" y2="{y + CELL - 6:.1f}" '
                  f'stroke="{t.muted}" stroke-width="1.2"/>')
            return
        fill = {"applied": "bar_green", "pr36": "bar_blue", "partly": "bar_orange", "by_t3": "bar_grey"}[kind]
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{t.fill(fill)}" stroke="{t.ink}" stroke-width="0.9"/>')
        if fid in ASSUMED:
            s.dot(x + CELL / 2, y + CELL / 2, 3.6, colour=t.ink)

    def bars(x: float, y: float, rows, unit: float, fill: str, label_w: float, step: float = 26) -> float:
        for k, (label, n) in enumerate(rows):
            yy = y + k * step
            s.text(x + label_w - 8, yy + 14, label, size=14, anchor="end", colour=t.ink)
            s.raw(f'<rect x="{x + label_w:.1f}" y="{yy + 2:.1f}" width="{n * unit:.1f}" height="16" rx="2" '
                  f'fill="{t.fill(fill)}" stroke="{t.ink}" stroke-width="0.8"/>')
            s.text(x + label_w + n * unit + 8, yy + 15, str(n), size=13.5, anchor="start", colour=t.dim)
        return y + len(rows) * step

    s.heading(40, 52, "APPLY3 · 49 of 69 spikes-round findings reached the specs",
              "T2, T3, T4, T7 · 44 applied (2 of them by PR #36), 5 partly, 0 not applied "
              "· 5 fixes rest on an assumed inbox answer · 9 findings wait for Thomas")

    # -- left: the findings, one cell each ---------------------------------------------------------
    s.shade(30, 116, 370, 680, fill="neutral", opacity=0.5)
    y = 146
    for name, total, groups in STEPS:
        s.text(48, y, name, size=18, anchor="start")
        s.text(380, y, f"{total}", size=15, anchor="end", colour=t.dim)
        i = 0
        for kind, fids in groups:
            for fid in fids:
                cell(48 + (i % 12) * (CELL + GAP), y + 12 + (i // 12) * (CELL + GAP), fid, kind)
                i += 1
        y += 12 + ((i - 1) // 12 + 1) * (CELL + GAP) + 34
    ky = y - 8
    for k, (kind, label) in enumerate(LEGEND):
        cell(48, ky + k * 28, "", kind)
        s.text(80, ky + k * 28 + 16, label, size=14, anchor="start", colour=t.ink)
    cell(48, ky + len(LEGEND) * 28, "SPK-T2-08", "applied")
    s.text(80, ky + len(LEGEND) * 28 + 16, "dot: assumed answer, pending (5)", size=14, anchor="start",
           colour=t.ink)

    # -- middle: files changed, to scale, then follow-ups outside the specs ------------------------
    mx = 430
    s.shade(mx, 116, 640, 400, fill="docs", opacity=0.45)
    s.page(mx + 18, 132, 34, 44, fill="surface", lines=3)
    s.text(mx + 64, 152, "7 specs and decision 0001 changed", size=20, anchor="start")
    s.text(mx + 64, 174, "lines added + and removed − (to scale; most lines are long paragraphs)", size=14,
           anchor="start", colour=t.dim)
    unit, lx = 10.0, mx + 270
    for k, (name, add, rem) in enumerate(SPECS):
        yy = 200 + k * 38
        s.text(lx - 10, yy + 17, name, size=14, anchor="end", colour=t.ink)
        s.raw(f'<rect x="{lx:.1f}" y="{yy + 2:.1f}" width="{add * unit:.1f}" height="12" rx="2" '
              f'fill="{t.fill("bar_green")}" stroke="{t.ink}" stroke-width="0.7"/>')
        s.raw(f'<rect x="{lx:.1f}" y="{yy + 16:.1f}" width="{rem * unit:.1f}" height="12" rx="2" '
              f'fill="{t.fill("problem")}" stroke="{t.ink}" stroke-width="0.7"/>')
        s.text(lx + add * unit + 8, yy + 17, f"+{add} −{rem}", size=13, anchor="start", colour=t.dim)

    s.shade(mx, 536, 640, 260, fill="work", opacity=0.35)
    s.cog(mx + 32, 566, r=10)
    s.text(mx + 56, 572, "partly applied: work left outside the specs", size=17, anchor="start")
    for k, label in enumerate(FOLLOW_UPS):
        cell(mx + 30, 594 + k * 38, "", "partly")
        s.text(mx + 64, 594 + k * 38 + 16, label, size=15, anchor="start", colour=t.ink)

    # -- right: what waits for Thomas, then the assumed answers already applied --------------------
    rx = 1100
    s.shade(rx, 116, W - rx - 30, 400, fill="violet", opacity=0.4)
    s.lock(rx + 30, 146, size=12)
    s.text(rx + 54, 152, "waits for Thomas: not in the specs", size=17, anchor="start")
    s.text(rx + 54, 174, "one bar unit = one finding", size=14, anchor="start", colour=t.dim)
    bars(rx + 10, 196, WAITING, 40, "bar_violet", 300, step=30)
    s.text(rx + 20, 372, "#53 holds the Role part of SPK-T4-02;", size=13.5, anchor="start", colour=t.dim)
    s.text(rx + 20, 392, "its fact part (pods: create) is applied.", size=13.5, anchor="start", colour=t.dim)

    s.shade(rx, 536, W - rx - 30, 260, fill="gate", opacity=0.45)
    s.hourglass(rx + 30, 566, size=10)
    s.text(rx + 54, 572, "applied on an assumed answer", size=17, anchor="start")
    s.text(rx + 54, 594, "marked in the text; reverted if Thomas disagrees", size=14, anchor="start",
           colour=t.dim)
    bars(rx + 10, 612, ASSUMED_BARS, 40, "bar_orange", 300, step=30)

    s.arrow(404, 330, mx - 6, 330, colour=t.muted, width=1.4)
    s.arrow(mx + 640, 330, rx - 6, 330, colour=t.muted, width=1.4)

    # -- source key --------------------------------------------------------------------------------
    s.text(40, H - 26, "Sources: Status lines of docs/reviews/spikes.md, the TRIAGE3 block of docs/reviews/inbox.md, "
                       "git diff --numstat 90180cb..APPLY3 -- docs/specs docs/decisions/0001 (2026-10-28) "
                       "· tools/diagrams/apply3_specs.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply3_specs")
