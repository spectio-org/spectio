#!/usr/bin/env python3
"""Round map for review R3-journeys: four 0.0.1 journeys, where they break.

Writes docs/assets/diagrams/r3_journeys_map_{light,dark}.{svg,png}.

Scope and findings come from the round's findings table (R3-journeys,
2026-10-27): each journey is walked step by step; a step is either specified
(tick) or a gap pinned with the finding that hits it. Red pin = blocker,
amber pin = major, grey pin = minor. The headline counts (7 blockers,
18 majors, 2 minors) are the round's totals; the map pins the findings that land on a
journey step, the rest are in the table.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1600, 960
X0, X1 = 250, 1575  # step columns span
STRIP_TOP, STRIP_H, STRIP_GAP = 122, 190, 10

B, M, N = "blocker", "major", "minor"

# (title, subtitle, steps); a step is (caption, note, pictogram, pins)
JOURNEYS = (
    ("Nextflow", "gate passes", (
        ("install bundle", "local env, runner", "laptop", (("SR-055", B),)),
        ("register repo", "nf-core/rnaseq", "repo", (("SR-056", M),)),
        ("gate after stage 1", "stage, gate config", "stages", (("SR-057", B),)),
        ("launch, events", "ingest contract", "runner", (("SR-054", B),)),
        ("stage ends", "run state", "state", (("CH-042", B),)),
        ("checks read", "MultiQC report", "report", (("SR-058", B),)),
        ("approve, continue", "specified", "gate_ok", ()),
    )),
    ("Snakemake", "gate fails", (
        ("launch form", "built from config", "form", (("SR-065", M),)),
        ("until targets", "partial runs", "until", (("SR-066", M),)),
        ("gate fails", "specified", "gate_fail", ()),
        ("edit 2 params", "and relaunch", "relaunch", (("SR-062", B),)),
        ("relaunch contract", "what run 2 reuses", "runs", (("SR-063", M),)),
        ("compare params", "run 1 against run 2", "compare", (("SR-064", M), ("UX-250", M))),
    )),
    ("A task fails", "find it, fix, resume", (
        ("run fails", "failed, yet resumable", "failed", (("CH-042", B),)),
        ("find failing task", "which task, which sample", "find", (("CH-047", M),)),
        ("read its log", "where the log lives", "log", (("CH-048", M),)),
        ("resume from cache", "what is reused", "resume", (("CH-043", M),)),
    )),
    ("Server restarts", "mid-run", (
        ("server stops", "engine head fate", "server", (("CH-041", B),)),
        ("events while down", "spool cursor", "spool", (("CH-044", M),)),
        ("projector catch-up", "replay order", "projector", (("CH-045", M),)),
        ("head lost", "run stuck running", "stuck", (("CH-046", M),)),
        ("gate across restart", "wait survives", "gate_restart", (("CH-049", M),)),
        ("UI catching up", "stale view", "ui", (("CH-051", N),)),
    )),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=41)
    t = theme
    sev_colour = {B: t.accent, M: t.warn, N: t.muted}

    def cell(x: float, y: float, fill: str, w: float = 14, h: float = 18, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="3 3"' if dashed else ""
        stroke = t.muted if dashed else t.ink
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx="2" fill="{t.fill(fill)}" '
              f'stroke="{stroke}" stroke-width="0.9"{dash}/>')

    def strip(x: float, y: float, fills: tuple[str, ...], w: float = 14, gap: float = 3) -> float:
        for i, f in enumerate(fills):
            cell(x + i * (w + gap), y, "none" if f == "empty" else f, w=w, dashed=f == "empty")
        return x + len(fills) * (w + gap) - gap

    def pin(px: float, py: float, sev: str) -> None:
        c = sev_colour[sev]
        s.poly([(px - 7, py + 2), (px + 7, py + 2), (px, py + 17)], fill=c, colour=c, width=1.2, amount=0.3)
        s.circle(px, py, 9, fill=c, colour=c, width=1.4)
        s.dot(px, py, 3.2, colour=t.bg)

    def pins(cx: float, y: float, items: tuple[tuple[str, str], ...]) -> None:
        if not items:
            s.circle(cx, y + 2, 13, fill="done", colour=t.good, width=1.6)
            s.tick(cx, y + 2, size=7)
            return
        tag_w = 92
        start = cx - tag_w * len(items) / 2
        for i, (fid, sev) in enumerate(items):
            px = start + i * tag_w + 12
            pin(px, y - 2, sev)
            tag(px + 15, y + 4, fid, sev)

    def tag(x: float, y: float, fid: str, sev: str) -> None:
        """The finding ID; a blocker's sits in a red-edged pill so it does not rely on hue alone."""
        if sev == B:
            s.shade(x - 4, y - 16, 11 * len(fid) + 6, 22, fill="problem", opacity=1, colour=t.accent)
        s.text(x, y, fid, size=15, anchor="start", colour=t.ink if sev == B else sev_colour[sev],
               weight="bold" if sev == B else "normal")

    def pictogram(kind: str, cx: float, my: float) -> None:
        if kind == "laptop":
            s.terminal(cx - 52, my - 40, 104, 64, ("$ spectio",), size=12)
            s.poly([(cx - 62, my + 26), (cx + 62, my + 26), (cx + 70, my + 36), (cx - 70, my + 36)], fill="neutral")
        elif kind == "repo":
            s.folder(cx - 48, my - 30, 96, 62, fill="input", label="rnaseq")
        elif kind == "stages":
            cell(cx - 60, my - 4, "done", w=30, h=28)
            s.text(cx - 45, my + 15, "1", size=13)
            s.gate(cx, my + 26, 40, 46, state="closed")
            cell(cx + 30, my - 4, "none", w=30, h=28, dashed=True)
            s.text(cx + 45, my + 15, "2", size=13, colour=t.dim)
        elif kind == "runner":
            s.runner(cx - 56, my - 12, 96, 46, label="runner")
            for k in range(3):
                s.dot(cx + 48 + k * 9, my + 11 - k * 9, 3, colour=t.dim)
        elif kind == "state":
            strip(cx - 52, my + 4, ("done", "done", "done", "empty", "empty", "empty"))
            s.circle(cx, my - 22, 13, fill="gate")
            s.text(cx, my - 16, "?", size=17, weight="bold")
        elif kind == "report":
            s.page(cx - 42, my - 36, 56, 72, fill="docs", lines=3)
            s.magnifier(cx + 18, my + 2, 15)
        elif kind == "gate_ok":
            s.gate(cx - 6, my + 38, 60, 50, state="passed")
        elif kind == "gate_fail":
            s.gate(cx, my + 34, 72, 66, state="closed")
        elif kind == "form":
            s.browser(cx - 58, my - 40, 116, 80)
            for k in range(2):
                s.frame(cx - 46, my - 4 + k * 17, 92, 12, fill="input", colour=t.muted)
        elif kind == "until":
            s.terminal(cx - 60, my - 38, 120, 76, ("$ snakemake", "  --until rule"), size=12)
        elif kind == "relaunch":
            s.page(cx - 46, my - 34, 54, 68, fill="input", lines=0)
            for k in range(4):
                ly = my - 14 + k * 12
                if k in (1, 3):
                    s.shade(cx - 42, ly - 5, 44, 10, fill="recomputed", opacity=0.9)
                s.line(cx - 40, ly, cx - 2, ly, colour=t.muted, amount=0.3, passes=1, width=1.2)
            s.arc(cx + 30, my + 22, cx + 30, my - 22, lift=28, width=2)
        elif kind == "runs":
            s.text(cx - 44, my - 16, "1", size=13, colour=t.dim)
            strip(cx - 32, my - 30, ("done",) * 5)
            s.text(cx - 44, my + 24, "2", size=13, colour=t.dim)
            strip(cx - 32, my + 10, ("cached",) * 3 + ("recomputed",) * 2)
            s.arc(cx + 54, my - 20, cx + 54, my + 20, lift=-18, width=1.6)
        elif kind == "compare":
            for k, x in enumerate((cx - 56, cx + 6)):
                s.page(x, my - 34, 50, 68, fill="surface", lines=0)
                for r in range(4):
                    ly = my - 14 + r * 12
                    if r == 2:
                        s.shade(x + 3, ly - 5, 42, 10, fill="recomputed", opacity=0.9)
                    s.line(x + 6, ly, x + 42, ly, colour=t.muted, amount=0.3, passes=1, width=1.2)
        elif kind == "failed":
            strip(cx - 52, my - 4, ("done", "done", "problem", "empty", "empty", "empty"))
            s.cross(cx - 52 + 2 * 17 + 7, my + 5, size=6)
        elif kind == "find":
            strip(cx - 60, my + 4, ("done", "done", "problem", "empty", "empty"))
            s.magnifier(cx - 19, my - 12, 14)
        elif kind == "log":
            s.page(cx - 34, my - 38, 68, 78, fill="surface", lines=0)
            for k in range(5):
                ly = my - 18 + k * 11
                if k == 3:
                    s.shade(cx - 30, ly - 5, 58, 10, fill="problem", opacity=1)
                s.line(cx - 26, ly, cx + 22, ly, colour=t.muted, amount=0.3, passes=1, width=1.2)
        elif kind == "resume":
            strip(cx - 50, my + 6, ("cached", "cached", "recomputed", "recomputed", "recomputed", "recomputed"))
            s.arc(cx - 40, my - 4, cx + 40, my - 4, lift=-26, width=1.8)
        elif kind == "server":
            s.hpc_node(cx - 28, my - 36, 56, 72, busy=0, slots=4)
            s.cross(cx, my, size=20)
        elif kind == "spool":
            s.bucket(cx, my - 2, 64, 38, fill="work")
            for k, (dx, dy) in enumerate(((-30, -36), (-6, -42), (18, -36))):
                s.envelope(cx + dx, my + dy, 22, 14)
        elif kind == "projector":
            s.bucket(cx - 36, my - 14, 46, 32, fill="work")
            s.arrow(cx - 8, my + 2, cx + 18, my + 2)
            s.page(cx + 24, my - 30, 38, 54, fill="surface", lines=3)
        elif kind == "stuck":
            s.hourglass(cx - 42, my, size=12)
            b = Box(cx - 22, my - 14, 78, 28, "gate")
            s.rect(b)
            s.text(b.cx, my + 5, "running", size=14)
        elif kind == "gate_restart":
            s.gate(cx - 12, my + 34, 64, 60, state="closed")
            s.hourglass(cx + 44, my - 6, size=10)
        elif kind == "ui":
            s.browser(cx - 58, my - 40, 116, 80)
            s.frame(cx - 44, my + 6, 88, 14, fill="surface", colour=t.muted)
            s.shade(cx - 43, my + 7, 44, 12, fill="bar_blue", opacity=1)
        else:
            raise ValueError(kind)

    # -- header ------------------------------------------------------------------
    s.heading(40, 54, "R3 · four 0.0.1 journeys, where they break",
              "27 findings: 7 blockers, 18 majors, 2 minors; see the findings table")

    lx, ly = 1010, 50
    s.circle(lx, ly, 11, fill="done", colour=t.good, width=1.5)
    s.tick(lx, ly, size=6)
    s.text(lx + 20, ly + 5, "specified", size=15, anchor="start", colour=t.dim)
    for i, (sev, lab) in enumerate(((B, "blocker"), (M, "major"), (N, "minor"))):
        px = lx + 140 + i * 140
        pin(px, ly - 4, sev)
        if sev == B:
            tag(px + 15, ly + 5, lab, sev)
        else:
            s.text(px + 15, ly + 5, lab, size=15, anchor="start", colour=t.dim)

    s.prefix_key(lx - 11, ly + 38, ("SR", "CH", "UX"))

    # -- the four strips ---------------------------------------------------------------
    for j, (title, sub, steps) in enumerate(JOURNEYS):
        y0 = STRIP_TOP + j * (STRIP_H + STRIP_GAP)
        s.shade(30, y0, W - 50, STRIP_H, fill="neutral", opacity=0.55)
        s.text(48, y0 + 34, f"journey {j + 1}", size=14, anchor="start", colour=t.dim)
        s.text(48, y0 + 68, title, size=22, anchor="start")
        s.text(48, y0 + 94, sub, size=15, anchor="start", colour=t.dim)

        n = len(steps)
        span = (X1 - X0) / n
        my = y0 + 92
        centres = [X0 + span * (i + 0.5) for i in range(n)]
        for i, (cap, note, kind, items) in enumerate(steps):
            cx = centres[i]
            pins(cx, y0 + 24, items)
            pictogram(kind, cx, my)
            s.step(cx, y0 + 156, i + 1, cap, size=16)
            s.text(cx, y0 + 177, note, size=13, colour=t.dim)
            if i:
                s.arrow(centres[i - 1] + 76, my, cx - 76, my, colour=t.muted, width=1.4)

    s.text(40, H - 22, "Source: the R3-journeys findings table, 2026-10-27 · the map pins the findings that hit "
                       "a journey step, the others are in the table · tools/diagrams/r3_journeys_map.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "r3_journeys_map")
