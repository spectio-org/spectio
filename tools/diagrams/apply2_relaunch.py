#!/usr/bin/env python3
"""Figure for step APPLY2: how relaunch and resume worked before the step, and after it.

Writes docs/assets/diagrams/apply2_relaunch_{light,dark}.{svg,png}.

Before (api-and-data-model.md at cf5357b~1): `POST /runs/{id}:resume` was listed with no
source state, no transition left `failed` (§7.1), and a gate decision was one of
approve, apply, go_back or stop (§7 `decisions`).
After (cf5357b, assumed pending inbox #32): `failed` is terminal; Resume and Relaunch...
create a child run with `parent_run_id`, and mode `resume` reuses the parent's
`launch_dir` and engine cache (api §5.1, §7.1). The 0.0.1 gate verbs are approve and
stop; Relaunch... at a gate records `stop` with reason `relaunched` (the run becomes
`cancelled`), then calls `:relaunch` (api §5.1, mvp-0.0.1.md §2).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 800
STAGES = ("stage 1", "stage 2", "stage 3")
SW, SG = 112, 30  # stage card width and gap


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=32)
    t = theme

    def run(x: float, y: float, fills: tuple[str, str, str], failed: bool) -> list:
        boxes = s.pipeline(x, y, STAGES, w=SW, h=40, gap=SG, fills=fills)
        if failed:
            s.cross(boxes[1].right - 12, y + 11, size=7)
        return boxes

    s.heading(40, 52, "APPLY2 · Relaunch and Resume: before and after",
              "R3 blockers SR-062 and CH-042, assumed option (B) of inbox #32 · api-and-data-model.md §5.1, §7.1")

    # -- before ------------------------------------------------------------------------------------
    bx = 30
    s.shade(bx, 112, 770, 600, fill="neutral", opacity=0.5)
    s.text(bx + 24, 148, "before", size=24, anchor="start")
    s.text(bx + 24, 172, "one run, resumed in place", size=15, anchor="start", colour=t.dim)

    s.text(bx + 24, 222, "after a failure", size=17, anchor="start")
    s.text(bx + 40, 256, "run A · failed", size=14, anchor="start", colour=t.dim)
    a = run(bx + 40, 268, ("done", "problem", "neutral"), failed=True)
    s.arc(a[2].cx, a[2].y - 4, a[1].cx, a[1].y - 4, lift=40)
    s.text(a[2].x - SG / 2, 226, "`:resume`", size=14)
    s.warning(bx + 52, 352, size=11)
    s.text(bx + 74, 346, "the same run goes back to running, but no transition", size=14,
           anchor="start", colour=t.dim)
    s.text(bx + 74, 366, "out of `failed` was defined (api §7.1)", size=14, anchor="start", colour=t.dim)

    s.text(bx + 24, 430, "at the gate", size=17, anchor="start")
    s.gate(bx + 90, 540, 78, 66)
    for k, verb in enumerate(("approve", "apply", "go_back", "stop")):
        s.button(bx + 170 + k * 128, 490, 112, verb, fill="neutral" if verb != "approve" else "done")
    s.text(bx + 170, 560, "four verbs: `apply` and `go_back` restart the same run", size=14,
           anchor="start", colour=t.dim)
    s.text(bx + 170, 580, "with a change set or from an earlier stage (api §7 decisions)", size=14,
           anchor="start", colour=t.dim)
    s.step(bx + 385, 680, 1, "one run carries every retry")

    # -- after -------------------------------------------------------------------------------------
    ax = 840
    s.shade(ax, 112, 770, 600, fill="done", opacity=0.3)
    s.text(ax + 24, 148, "after", size=24, anchor="start")
    s.text(ax + 24, 172, "the parent stays terminal; each retry is a child run", size=15, anchor="start",
           colour=t.dim)

    s.text(ax + 24, 222, "after a failure", size=17, anchor="start")
    s.lock(ax + 48, 250, size=9)
    s.text(ax + 64, 256, "run A · failed, terminal", size=14, anchor="start", colour=t.dim)
    p = run(ax + 40, 268, ("done", "problem", "neutral"), failed=True)
    c = run(ax + 40, 368, ("cached", "work", "neutral"), failed=False)
    s.arrow(p[1].cx, p[1].bottom + 4, c[1].cx, c[1].y - 26)
    s.text(p[1].cx + 12, 334, "Resume", size=14, anchor="start")
    s.text(c[2].right + 22, 380, "run B", size=15, anchor="start")
    s.text(c[2].right + 22, 400, "`parent_run_id` = A", size=13, anchor="start", colour=t.dim)
    s.text(ax + 40, 440, "stage 1 cached: mode `resume` reuses A's `launch_dir` and engine cache", size=14,
           anchor="start", colour=t.dim)

    s.text(ax + 24, 490, "at the gate (0.0.1)", size=17, anchor="start")
    s.gate(ax + 90, 590, 78, 66)
    s.button(ax + 170, 530, 112, "approve")
    s.button(ax + 298, 530, 112, "stop", fill="neutral")
    s.button(ax + 470, 530, 132, "Relaunch…", fill="work")
    s.arrow(ax + 426, 545, ax + 466, 545, colour=t.muted, width=1.3)
    s.text(ax + 170, 600, "Relaunch… = `stop` with reason `relaunched` (run cancelled),", size=14,
           anchor="start", colour=t.dim)
    s.text(ax + 170, 620, "then `:relaunch` creates the child run with the changed parameters", size=14,
           anchor="start", colour=t.dim)
    s.step(ax + 385, 680, 2, "a lineage of runs, each one unchanged")

    s.text(40, H - 30, "Sources: docs/specs/api-and-data-model.md before and after commit cf5357b (§5, §5.1, §7, "
                       "§7.1), docs/specs/mvp-0.0.1.md §2 · tools/diagrams/apply2_relaunch.py", size=12.5,
           anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply2_relaunch")
