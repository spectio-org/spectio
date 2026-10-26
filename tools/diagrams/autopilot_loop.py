#!/usr/bin/env python3
"""The autopilot loop: one tick, from pipeline.yaml to an auto-merged PR.

Writes docs/assets/diagrams/autopilot-loop_{light,dark}.{svg,png}.
Source of truth: docs/playbooks/autopilot.md and docs/playbooks/pipeline.yaml.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 930


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=11)
    t = theme
    s.heading(60, 62, "One autopilot tick",
              "every step lands as a reviewed docs page in a PR that merges itself once CI is green")

    # -- row 1, left to right -------------------------------------------------
    cap_y = 400

    # 1 pipeline.yaml -> ready batch
    s.page(70, 130, 130, 170, fill="surface", lines=0)
    s.text(135, 158, "`pipeline.yaml`", size=13)
    for i, (wave, fill) in enumerate((("W1", "done"), ("W2", "done"), ("W3", "work"), ("W4", "neutral"), ("W5", "neutral"))):
        y = 176 + i * 23
        s.rect(Box(86, y, 98, 17, fill), rx=3)
        s.text(98, y + 13, wave, size=11.5, anchor="start")
    s.arrow(205, 230, 248, 230)
    for i, lab in enumerate(("D3", "T1", "D5")):
        s.chip(252, 170 + i * 46, 74, lab, fill="work", h=36)
    s.step(200, cap_y, 1, "next ready batch")
    s.text(200, cap_y + 24, "deps met, budget left", size=13.5, colour=t.dim)

    # 2 parallel workers
    s.arrow(338, 230, 378, 230)
    for i, (sid, cmd) in enumerate((("D5", "build"), ("T1", "build"), ("D3", "build"))):
        off = (2 - i) * 16
        s.terminal(388 + off, 140 + off, 210, 130,
                   (f"$ claude -p /{cmd}", f"  step {sid}", "  worktree ok", "  exit 0") if i == 2 else ())
    s.step(505, cap_y, 2, "parallel workers")
    s.text(505, cap_y + 24, "one session per step, own worktree", size=13.5, colour=t.dim)

    # 3 exit check
    s.arrow(650, 230, 690, 230)
    s.circle(745, 222, 44, fill="done", width=2)
    s.tick(745, 220, size=20, width=3.4)
    s.text(745, 300, "`bash dev/doctor.sh`", size=12.5, colour=t.dim)
    s.step(745, cap_y, 3, "exit check")
    s.text(745, cap_y + 24, "the step's own command", size=13.5, colour=t.dim)

    # 4 doc writer
    s.arrow(800, 230, 845, 230)
    s.page(860, 140, 118, 156, fill="docs", lines=5)
    # a pen writing the page
    s.poly([(992, 160), (1002, 168), (958, 238), (946, 244), (950, 230)], fill="yellow", width=1.5)
    s.text(919, 320, "`progress/W3/D3.md`", size=12.5, colour=t.dim)
    s.step(919, cap_y, 4, "doc writer")
    s.text(919, cap_y + 24, "page, cast, screenshots", size=13.5, colour=t.dim)

    # 5 doc reviewer
    s.arrow(1012, 230, 1052, 230)
    s.page(1066, 140, 118, 156, fill="docs", lines=5)
    s.magnifier(1140, 238, 30)
    s.text(1110, 334, "fresh agent, unseen work", size=12.5, colour=t.dim)
    s.step(1125, cap_y, 5, "doc reviewer")
    s.text(1125, cap_y + 24, "facts, links, rendering", size=13.5, colour=t.dim)

    # reviewer -> back to writer when it finds problems
    s.arc(1100, 136, 935, 136, lift=-34, colour=t.accent, dashed=True)
    s.text(1018, 104, "findings: rewrite", size=12.5, colour=t.accent)

    # turn the corner down to row 2
    s.arc(1232, 250, 1262, 532, lift=-46)

    # -- row 2, right to left -------------------------------------------------
    cap2 = 795

    # 6 strict build
    s.terminal(1010, 540, 280, 140, ("$ mkdocs build --strict", "INFO  Documentation built", "      in 4.1 seconds", "$ mmdc -i *.mmd  ok"), size=12.5)
    s.tick(1268, 650, size=11)
    s.step(1150, cap2, 6, "strict docs build")
    s.text(1150, cap2 + 24, "no warning, every diagram renders", size=13.5, colour=t.dim)

    # 7 PR with docs and diagrams
    s.arrow(1000, 610, 960, 610)
    b = s.browser(600, 520, 350, 230, url="github.com/.../pull/42")
    s.text(616, 572, "feat(runner): sind cluster", size=15, anchor="start", weight="bold")
    s.text(616, 594, "## What changed   ## Docs", size=12, anchor="start", colour=t.dim)
    # a tiny hand-drawn figure inside the PR body
    mini = Box(616, 606, 200, 116, "white")
    s.rect(mini, colour=t.muted)
    s.hpc_node(630, 624, 34, 46, busy=2, slots=3)
    s.hpc_node(672, 624, 34, 46, busy=3, slots=3)
    s.arrow(712, 646, 750, 646)
    s.gate(783, 680, 44, 42, state="closed")
    s.text(716, 712, "figure_light.png", size=10.5, colour=t.dim)
    s.page(836, 610, 50, 64, fill="docs", lines=3)
    s.page(896, 610, 40, 64, fill="surface", lines=3)
    s.text(870, 700, "page + cast", size=11, colour=t.dim)
    s.step(775, cap2, 7, "PR with docs in the body")
    s.text(775, cap2 + 24, "hand-drawn figures, not boxes", size=13.5, colour=t.dim)

    # 8 CI
    s.arrow(590, 610, 545, 610)
    for i, lab in enumerate(("docs", "synthetic x3", "real corpus", "`e2e`")):
        y = 548 + i * 44
        s.rect(Box(365, y, 170, 34, "done"), rx=4)
        s.tick(386, y + 16, size=7)
        s.text(404, y + 22, lab, size=13.5, anchor="start")
    s.step(450, cap2, 8, "required checks")
    s.text(450, cap2 + 24, "all green, or nothing merges", size=13.5, colour=t.dim)

    # 9 auto-merge to integration
    s.arrow(355, 610, 315, 610)
    # git graph: main line, a branch curving in
    y0 = 650
    s.line(90, y0, 300, y0, width=2.4, amount=0.8)
    for x in (110, 170, 230, 290):
        s.circle(x, y0, 8, fill="surface", width=1.8)
    s.arc(140, y0, 290, y0 - 4, lift=-55, head=False, colour=t.dim, width=2)
    s.circle(215, y0 - 52, 7, fill="work", width=1.6)
    s.circle(290, y0, 8, fill="done", width=2)
    s.text(195, y0 + 36, "`autopilot/integration`", size=12.5, colour=t.dim)
    s.text(195, y0 + 56, "Thomas merges to `main`", size=12.5, colour=t.dim)
    s.step(195, cap2, 9, "auto-merge")
    s.text(195, cap2 + 24, "squash, Conventional title", size=13.5, colour=t.dim)

    # loop back to 1
    s.arc(130, 560, 130, 430, lift=-60)
    s.text(150, 505, "next tick", size=14, anchor="start", colour=t.dim)

    # -- side panel: budget and inbox ----------------------------------------
    px = 1360
    s.frame(px, 120, 320, 330, fill="grey", colour=t.muted, dashed=True)
    s.text(px + 160, 156, "budget governor", size=19, weight="bold")
    s.gauge(px + 160, 330, 110, used=41, budget=55, start=25, label="weekly window, %")
    s.text(px + 160, 386, "start 25 %  ·  budget +30 pt", size=13.5)
    s.text(px + 160, 408, "a batch starts only if it fits", size=13.5, colour=t.dim)
    s.text(px + 160, 430, "or: run until the quota is gone", size=13.5, colour=t.dim)
    s.arrow(px - 8, 470, 300, 470, dashed=True, colour=t.dim)
    s.text(830, 462, "read before every batch: does the next one still fit?", size=13, colour=t.dim)

    s.frame(px, 520, 320, 230, fill="grey", colour=t.muted, dashed=True)
    s.text(px + 160, 556, "inbox for Thomas", size=19, weight="bold")
    s.envelope(px + 105, 580, 110, 70, fill="surface")
    s.dot(px + 212, 584, 9, colour=t.accent)
    s.text(px + 212, 588, "2", size=11, colour="#ffffff")
    s.text(px + 160, 680, "`docs/reviews/inbox.md`", size=13)
    s.text(px + 160, 704, "only what triage cannot decide", size=13.5, colour=t.dim)
    s.text(px + 160, 726, "the rest keeps going", size=13.5, colour=t.dim)
    s.arrow(1296, 600, px - 6, 620, dashed=True, colour=t.dim)
    s.text(1326, 586, "ask", size=13, colour=t.dim)

    s.text(60, 900, "Source: docs/playbooks/autopilot.md, pipeline.yaml · drawn by tools/diagrams/autopilot_loop.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "autopilot-loop")
