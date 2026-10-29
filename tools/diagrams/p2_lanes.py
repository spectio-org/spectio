#!/usr/bin/env python3
"""How step P3 runs P1's 32 tasks: the critical path, the lanes beside it, and where each lane runs.

Writes docs/assets/diagrams/p2_lanes_{light,dark}.{svg,png}.

Every fact comes from docs/plans/P2-execution.md (step P2, 2026-10-29):
- §0 Order: the critical path is 1, 2, 4, 9, 10, 11, 12, 16, 17, 18, 20, 21, 22, 23; a task starts
  when the tasks it depends on are merged;
- §1 M1: Task 1 alone first, then four worktrees 2 then 4 then 5; 3; 6; 7. Task 4 waits for 3. Task 8
  (M2) starts as soon as 2 is merged;
- §2 M2: 9 after 4, 6, 7 and 8; 10 after 9; G6's init and doctor part goes with Task 8;
- §3 M3: 11 after 3, 8, 9 and 10; then 12 and 14 in parallel; then 13 and 15 (after 12) and 16 (after 12
  and 14); Task 24 may start once 11 and 12 are merged; G6's start-text part goes with Task 11 (§10.7);
- §4 M4: G1, then G2 and G3a, start at once, in parallel with M1 to M3; 17 after 9 and 16 with G5's
  API tests; 18 and 19 in parallel (19 also after G1 and G2, with G5's UI tests); G4 after 19; 20 after
  18, G3a and G4; 21 after 6, 7 and 20;
- §5 M5: 22 after 21, 23 after 22; G7 after 21, in parallel with 22; Task 24 in parallel from M3 on;
- §6 to §8: M6 (25, 26 in parallel), M7 (27, after 25), M8 (28, then 29, 30 and 31, then 32 after 27
  and G3b); none waits for M5; the slurm-mini lines of Step 4 in Tasks 28 to 30 run once Task 22's e2e
  job exists, batched in one CI iteration;
- §0.1 where each part runs: a cloud session for code and unit, API and Playwright tests; Tasks 22 and
  23 and the slurm-mini checks of 28 to 30 on a GitHub runner (job e2e of pipelines-slurm.yml), since
  cloud sessions boot with cgroup v1 and sind cannot run there (inbox #51); Task 24 Step 4 and inbox #64
  need a person on an EMBL login node;
- §9 review tracks: review-code for 1 to 20, 24 to 32, G4, G5, G6; tests and one review for 21, 22,
  23, G7; render, look and ux-reviewer for G1, G2, G3a, G3b.
Horizontal position is order, not duration: P2 gives no time estimates.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1800, 1110
SEED = 202

TESTS = {"21", "22", "23", "G7"}
BOARDS = {"G1", "G2", "G3a", "G3b"}
TRACK_FILL = {"code": "bar_orange", "tests": "bar_green", "ux": "bar_violet"}

# lane rows
Y_BOARD_A, Y_BOARD_B = 244, 300
Y_UP, Y_MAIN, Y_L1, Y_L2, Y_L3 = 386, 466, 546, 614, 682

# the critical path, x by task
CRIT = {"1": 95, "2": 185, "4": 290, "9": 445, "10": 525, "11": 610, "12": 690, "16": 840,
        "17": 905, "18": 985, "20": 1090, "21": 1160, "22": 1250, "23": 1390}
# milestone bands of the main area: (id, name, x0, x1)
BANDS = (("M1", "Events in", 50, 400), ("M2", "Heads", 400, 570), ("M3", "Served safely", 570, 870),
         ("M4", "API and screens", 870, 1200), ("M5", "On the cluster", 1200, 1490))


def track(label: str) -> str:
    return "tests" if label in TESTS else "ux" if label in BOARDS else "code"


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=SEED)
    t = theme
    pos: dict[str, tuple[float, float, float]] = {}  # label -> (cx, cy, half-width)

    def task(label: str, cx: float, cy: float, *, crit: bool = False) -> None:
        r = 20 if crit else 16.5
        rx = r + (7 if label.startswith("G") else 0) + (4 if len(label) > 2 else 0)
        s.ellipse(cx, cy, rx, r, fill=TRACK_FILL[track(label)], width=2.6 if crit else 1.5)
        s.text(cx, cy + 5.5, label, size=17 if crit else 15, weight="bold" if crit else "normal")
        pos[label] = (cx, cy, rx)

    def join(a: str, b: str, *, colour: str | None = None) -> None:
        """An arrow from task a to task b, edge to edge."""
        ax, ay, ar = pos[a]
        bx, by, br = pos[b]
        dx, dy = bx - ax, by - ay
        n = (dx * dx + dy * dy) ** 0.5
        s.arrow(ax + dx / n * (ar + 2), ay + dy / n * 18, bx - dx / n * (br + 4), by - dy / n * 21,
                width=1.4, colour=colour or t.dim)

    def marker(n: int, cx: float, cy: float) -> None:
        """A numbered spot, read with the caption of the same number."""
        s.dot(cx, cy, 12)
        s.text(cx, cy + 5, str(n), size=14, weight="bold", colour=t.bg)

    def cloud(cx: float, cy: float, w: float) -> None:
        u = w / 2
        d = (f"M{cx - u * 0.82:.1f},{cy + u * 0.32:.1f} "
             f"A{u * 0.3:.1f},{u * 0.3:.1f} 0 0 1 {cx - u * 0.62:.1f},{cy - u * 0.12:.1f} "
             f"A{u * 0.4:.1f},{u * 0.4:.1f} 0 0 1 {cx - u * 0.05:.1f},{cy - u * 0.38:.1f} "
             f"A{u * 0.36:.1f},{u * 0.36:.1f} 0 0 1 {cx + u * 0.62:.1f},{cy - u * 0.05:.1f} "
             f"A{u * 0.3:.1f},{u * 0.3:.1f} 0 0 1 {cx + u * 0.78:.1f},{cy + u * 0.32:.1f} Z")
        s.raw(f'<path d="{d}" fill="{t.fill("input")}" stroke="{t.ink}" stroke-width="1.8" '
              f'stroke-linejoin="round"/>')
        s.raw(f'<path d="{d}" fill="none" stroke="{t.ink}" stroke-width="1.1" '
              f'transform="translate(1.2 -0.8)" stroke-linejoin="round"/>')

    def person(cx: float, cy: float, r: float = 9) -> None:
        """A person: a head over shoulders."""
        s.circle(cx, cy, r, fill="docs")
        sh = [(cx - r * 1.7, cy + r * 3.1), (cx - r * 1.5, cy + r * 1.8), (cx - r * 0.8, cy + r * 1.3),
              (cx + r * 0.8, cy + r * 1.3), (cx + r * 1.5, cy + r * 1.8), (cx + r * 1.7, cy + r * 3.1)]
        s.poly(sh, fill="docs", amount=0.3)

    def mini_runner(x: float, y: float) -> None:
        """The CI runner glyph at mark size."""
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="26" height="17" rx="3" fill="{t.fill("violet")}" '
              f'stroke="{t.ink}" stroke-width="1.3"/>')
        s.circle(x + 9, y + 8.5, 3.6, fill="violet", width=1.2)
        s.line(x + 21, y, x + 21, y - 8, width=1.3, amount=0.2, passes=1)
        s.dot(x + 21, y - 9, 2.2)

    def lane(x0: float, x1: float, y: float, *, dashed: bool = False) -> None:
        s.line(x0, y, x1, y, width=1.3, amount=0.6, passes=1, colour=t.dim, dashed=dashed)

    # -- heading ----------------------------------------------------------------------------------
    s.heading(40, 50, "P2 · how step P3 runs P1's 32 tasks: one critical path, the lanes beside it",
              "a task starts when the tasks it depends on are merged · left to right is order, not time "
              "· the fill of each task is its review track")

    # -- where each lane runs -------------------------------------------------------------------
    ky = 112
    cloud(105, ky + 40, 104)
    s.text(172, ky + 34, "cloud session: every lane unless marked", size=16, anchor="start", weight="bold")
    s.text(172, ky + 56, "the code, and its unit, API and Playwright tests", size=13.5, anchor="start", colour=t.dim)
    s.runner(640, ky + 22, 104, 50, label="CI")
    s.text(762, ky + 34, "a GitHub runner: Tasks 22 and 23,", size=16, anchor="start", weight="bold")
    s.text(762, ky + 56, "the `slurm-mini` checks of Tasks 28 to 30;", size=13.5, anchor="start", colour=t.dim)
    s.text(762, ky + 76, "cloud sessions cannot run sind, inbox #51", size=13.5, anchor="start", colour=t.dim)
    s.hpc_node(1238, ky + 10, 40, 58, busy=1, slots=3)
    person(1302, ky + 20, 10)
    s.text(1340, ky + 34, "by hand on an EMBL login node:", size=16, anchor="start", weight="bold")
    s.text(1340, ky + 56, "Task 24 Step 4, and inbox #64", size=13.5, anchor="start", colour=t.dim)
    s.text(1340, ky + 76, "nothing in CI reaches EMBL", size=13.5, anchor="start", colour=t.dim)

    # -- milestone bands ------------------------------------------------------------------------
    for i, (m, name, x0, x1) in enumerate(BANDS):
        s.shade(x0, 330, x1 - x0 - 6, 400, fill="neutral" if i % 2 == 0 else "input", opacity=0.55)
        s.text((x0 + x1 - 6) / 2, 720, f"{m} · {name}", size=15.5, weight="bold")

    # -- the critical path ----------------------------------------------------------------------
    xs = list(CRIT.values())
    s.line(xs[0], Y_MAIN, xs[-1], Y_MAIN, width=4.5, amount=1.2, passes=1, colour=t.accent)
    s.text(60, Y_MAIN + 44, "critical path", size=14.5, anchor="start", colour=t.accent, weight="bold")
    for label, x in CRIT.items():
        task(label, x, Y_MAIN, crit=True)

    # -- M1: four lanes after Task 1, Task 8 after 2 ---------------------------------------------
    for label, y in (("3", Y_L1), ("6", Y_L2), ("7", Y_L3)):
        lane(CRIT["1"] + 10, 170, y)
        s.line(CRIT["1"], Y_MAIN + 20, CRIT["1"] + 10, y, width=1.3, amount=0.4, passes=1, colour=t.dim)
        task(label, 187, y)
    join("3", "4")
    lane(204, 412, Y_L2)
    s.arrow(412, Y_L2, 432, Y_MAIN + 22, width=1.4, colour=t.dim)
    lane(204, 422, Y_L3)
    s.arrow(422, Y_L3, 446, Y_MAIN + 22, width=1.4, colour=t.dim)
    task("5", 345, Y_L1)
    join("4", "5")
    task("8", 290, Y_UP)
    join("2", "8")
    join("8", "9")
    s.text(290, Y_UP - 26, "with G6", size=13, colour=t.dim)
    marker(1, CRIT["1"] - 28, Y_MAIN - 36)
    marker(2, 146, Y_L1 + 34)

    # -- the boards: G1, then G2 and G3a, waiting for 19 and 20 ----------------------------------
    task("G1", 100, (Y_BOARD_A + Y_BOARD_B) / 2)
    task("G2", 205, Y_BOARD_A)
    task("G3a", 205, Y_BOARD_B)
    join("G1", "G2")
    join("G1", "G3a")
    lane(234, CRIT["18"], Y_BOARD_A, dashed=True)
    s.arrow(CRIT["18"], Y_BOARD_A, CRIT["18"], Y_UP - 22, width=1.4, colour=t.dim)
    lane(240, CRIT["20"], Y_BOARD_B, dashed=True)
    s.arrow(CRIT["20"], Y_BOARD_B, CRIT["20"], Y_MAIN - 25, width=1.4, colour=t.dim)
    s.text(270, Y_BOARD_A - 10, "boards start at once, beside M1 to M3; G2 waits for Task 19", size=13.5,
           anchor="start", colour=t.dim)
    s.text(270, Y_BOARD_B - 10, "G3a waits for Task 20", size=13.5, anchor="start", colour=t.dim)
    marker(3, 52, Y_BOARD_A - 4)

    # -- M3: pairs, then Task 24 -----------------------------------------------------------------
    s.text(CRIT["11"], Y_MAIN + 42, "with G6", size=13, colour=t.dim)
    task("14", CRIT["12"], Y_UP)
    join("11", "14")
    join("14", "16")
    task("13", 772, Y_L1)
    task("15", 772, Y_L2)
    join("12", "13")
    join("12", "15")
    marker(4, 640, Y_UP - 4)
    task("24", 712, Y_L3)
    join("12", "24")
    lane(732, 1526, Y_L3, dashed=True)
    s.arrow(1526, Y_L3, 1548, Y_L3, width=1.4, colour=t.dim)
    s.text(744, Y_L3 - 12, "the code beside M4 and M5; its Step 4 waits for a person", size=13.5,
           anchor="start", colour=t.dim)
    marker(5, 668, Y_L3)

    # -- M4: 18 beside 19, G4 after 19, the screens join -----------------------------------------
    s.text(CRIT["17"], Y_MAIN + 42, "with G5", size=13, colour=t.dim)
    task("19", CRIT["18"], Y_UP)
    s.text(940, Y_UP - 22, "with G5", size=13, colour=t.dim)
    join("17", "19")
    task("G4", 1046, Y_UP)
    join("19", "G4")
    join("G4", "20")
    marker(6, 1046, Y_UP - 40)

    # -- M5: on a CI runner, G7 beside 22, then done --------------------------------------------
    b = s.runner(1262, Y_UP - 36, 114, 52, label="CI e2e")
    s.line(CRIT["22"] + 6, Y_MAIN - 22, b.x + 22, b.bottom, width=1.3, amount=0.4, passes=1, colour=t.dim,
           dashed=True)
    s.line(CRIT["23"] - 6, Y_MAIN - 22, b.right - 26, b.bottom, width=1.3, amount=0.4, passes=1, colour=t.dim,
           dashed=True)
    s.text(1384, Y_UP - 14, "runs pushed", size=13.5, anchor="start", colour=t.dim)
    s.text(1384, Y_UP + 4, "to job `e2e`", size=13.5, anchor="start", colour=t.dim)
    marker(7, 1236, Y_UP - 56)
    task("G7", CRIT["22"], Y_L1)
    join("21", "G7")
    s.arrow(CRIT["23"] + 24, Y_MAIN, 1520, Y_MAIN, width=3, colour=t.accent)
    s.gate(1560, Y_MAIN + 22, 62, 52, state="passed")
    s.text(1610, Y_MAIN - 2, "M5 done:", size=14.5, anchor="start", weight="bold")
    s.text(1610, Y_MAIN + 18, "job `e2e` green", size=13.5, anchor="start", colour=t.dim)
    s.text(1610, Y_MAIN + 37, "on both engines", size=13.5, anchor="start", colour=t.dim)
    # Task 24 Step 4 by hand
    s.hpc_node(1556, Y_L3 - 38, 44, 60, busy=1, slots=3)
    person(1630, Y_L3 - 28, 10)
    s.text(1658, Y_L3 - 12, "Task 24 Step 4", size=14.5, anchor="start", weight="bold")
    s.text(1658, Y_L3 + 8, "by hand, EMBL", size=13.5, anchor="start", colour=t.dim)

    # -- after M4: M6, M7, M8, not waiting for M5 ------------------------------------------------
    px0, py0, px1, py1 = 1000, 776, 1764, 1062
    s.frame(px0, py0, px1 - px0, py1 - py0, fill="none", colour=t.muted, dashed=True)
    s.arrow(CRIT["21"] + 6, Y_MAIN + 22, 1182, py0 - 4, width=2.2, colour=t.dim)
    marker(8, px0 + 24, py0 + 26)
    s.text(px0 + 44, py0 + 32, "after M4, beside M5: none of M6 to M8 waits for Task 22", size=15.5,
           anchor="start", weight="bold")
    # M6
    s.shade(px0 + 10, py0 + 50, 150, py1 - py0 - 60, fill="neutral", opacity=0.55)
    task("25", px0 + 85, py0 + 92)
    task("26", px0 + 85, py0 + 170)
    s.text(px0 + 85, py1 - 34, "M6", size=15.5, weight="bold")
    s.text(px0 + 85, py1 - 16, "Runs from a terminal", size=12.5, colour=t.dim)
    # M7
    s.shade(px0 + 170, py0 + 50, px1 - px0 - 180, 70, fill="input", opacity=0.55)
    task("27", 1260, py0 + 85)
    join("25", "27")
    s.text(px1 - 12, py0 + 90, "M7 · Stages", size=15.5, anchor="end", weight="bold")
    # M8
    s.shade(px0 + 170, py0 + 126, px1 - px0 - 180, py1 - py0 - 136, fill="neutral", opacity=0.55)
    task("28", 1260, 960)
    for label, y in (("29", 910), ("30", 960), ("31", 1010)):
        task(label, 1390, y)
        join("28", label)
    task("32", 1560, 960)
    for label in ("29", "30", "31"):
        join(label, "32")
    task("G3b", 1560, 1032)
    s.arrow(1560, 1014, 1560, 982, width=1.4, colour=t.dim)
    lane(1278, 1490, py0 + 85)
    s.arrow(1490, py0 + 85, 1546, 944, width=1.4, colour=t.dim)
    mini_runner(1610, 924)
    s.text(1646, 938, "on CI:", size=13.5, anchor="start", weight="bold")
    s.text(1606, 962, "the `slurm-mini` checks", size=13, anchor="start", colour=t.dim)
    s.text(1606, 980, "of 28, 29 and 30, one", size=13, anchor="start", colour=t.dim)
    s.text(1606, 998, "batch after Task 22", size=13, anchor="start", colour=t.dim)
    s.text(px0 + 182, py1 - 14, "M8 · Job files and run tools", size=15.5, anchor="start", weight="bold")

    # -- how to read it --------------------------------------------------------------------------
    cy0 = 776
    captions = (
        "Task 1 alone first: the workspace and the CI job everything uses",
        "then four worktrees at once: 2 then 4 then 5, 3, 6 and 7; Task 8 as soon as 2 is merged",
        "board gaps start at once: G1, then G2 and G3a, each waiting for the screen task that needs it",
        "M3 in pairs: 12 and 14, then 13 and 15 beside 16; every M3 task is a security boundary",
        "Task 24 once 11 and 12 are merged; its Step 4 by hand on an EMBL login node",
        "18 beside 19; G4 after 19; G5's tests ride with 17 and 19, G6's with 8 and 11",
        "M5 runs on a CI runner; G7 checks `happy-local` beside 22",
        "M6 to M8 start after M4; 29, 30 and 31 in parallel; 27 and G3b before 32",
    )
    for i, c in enumerate(captions):
        y = cy0 + i * 27
        marker(i + 1, 62, y - 5)
        s.text(84, y, c, size=14.5, anchor="start")
    ly = cy0 + len(captions) * 27 + 20
    s.text(50, ly, "review track, by fill:", size=14.5, anchor="start", weight="bold")
    for x, fill, lab in ((214, "code", "`review-code`"), (380, "tests", "tests and one review"),
                         (590, "ux", "render, look, `ux-reviewer`")):
        s.ellipse(x, ly - 5, 14, 11, fill=TRACK_FILL[fill], width=1.4)
        s.text(x + 22, ly, lab, size=14.5, anchor="start")

    s.text(40, H - 16, "Source: docs/plans/P2-execution.md, sections 0, 0.1, 1 to 10 · "
                       "tools/diagrams/p2_lanes.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p2_lanes")
