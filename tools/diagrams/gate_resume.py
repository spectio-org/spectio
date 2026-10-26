#!/usr/bin/env python3
"""Stop at the QC gate, exclude a sample from a phone, resume with the cache.

Writes docs/assets/diagrams/gate-resume_{light,dark}.{svg,png}.

Every number is measured, not invented: the synthetic pipeline
(tests/pipelines/synthetic) on Nextflow 26.10.3, scenario
`exclude_sample_and_resume`, 2026-10-26.
- run 1 stops after the qc gate: 12 MAKE_READS + 12 QC_STATS + 1 QC_REPORT = 25 tasks
- run 2 resumes with samplesheet v2 (S03 removed): 22 CACHED (11 + 11),
  38 run (QC_REPORT 1, SPLIT 11, ALIGN 22, MERGE 1, COMPARE 2, FINAL_REPORT 1)
- reads per sample come from data/samplesheet.csv (S03: 40, others: 400)
The scenario ran on the local executor; the SLURM cluster is the sind profile
the same pipeline runs on in T3.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 1000
READS = [400, 400, 40, 400, 400, 400, 400, 400, 400, 400, 400, 400]


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=23)
    t = theme
    s.heading(60, 62, "Stop at the QC gate, drop a sample, resume",
              "the synthetic pipeline: 12 samples, a reviewer decides from a phone, nothing upstream is recomputed")
    cap_y = 452

    # 1 · the run on the cluster -------------------------------------------------
    s.frame(60, 128, 360, 268, fill="grey", colour=t.muted, dashed=True)
    s.text(76, 152, "SLURM cluster", size=14, anchor="start", colour=t.dim)
    for i, busy in enumerate((4, 3, 4, 2)):
        s.hpc_node(84 + i * 72, 170, 56, 92, busy=busy, slots=4)
    s.text(240, 288, "`MAKE_READS` · `QC_STATS`  x12", size=13)
    s.runner(130, 330, 180, 54, label="spectio runner")
    s.step(240, cap_y, 1, "run on the cluster")
    s.text(240, cap_y + 24, "jobs go through the runner", size=13.5, colour=t.dim)

    # 2 · stops at the gate ------------------------------------------------------
    s.arrow(430, 262, 470, 262)
    s.chip(474, 238, 122, "QC_REPORT", fill="done")
    s.arrow(600, 258, 624, 258)
    s.gate(674, 300, 82, 92, state="closed")
    s.text(674, 196, "qc gate", size=16, weight="bold")
    for i, lab in enumerate(("SPLIT", "ALIGN", "MERGE")):
        b = Box(740, 176 + i * 52, 86, 36, "none")
        s.rect(b, colour=t.muted, dashed=True)
        s.text(b.cx, b.y + 24, lab, size=12.5, colour=t.muted)
    s.text(650, 350, "later stages: `ext.when = false`", size=13, colour=t.dim)
    s.text(650, 372, "the run ends cleanly, exit 0", size=13, colour=t.dim)
    s.step(650, cap_y, 2, "stops at the gate")
    s.text(650, cap_y + 24, "25 tasks done, nothing beyond", size=13.5, colour=t.dim)

    # 3 · reviewer on a phone, through a share link -------------------------------
    s.arrow(842, 262, 882, 262)
    s.envelope(890, 226, 74, 50, fill="surface")
    s.link(927, 300, 16)
    s.text(927, 344, "share link", size=13, colour=t.dim)
    s.text(927, 364, "reviewer · 72 h", size=13, colour=t.dim)
    s.arrow(974, 250, 1012, 250)
    scr = s.phone(1020, 112, 190, 316)
    s.text(scr.cx, scr.y + 24, "QC gate · reads", size=14, weight="bold")
    # reads per sample, to scale (max 400 reads = 150 px)
    base = scr.y + 206
    bw = 10
    for i, n in enumerate(READS):
        bx = scr.x + 12 + i * 13.4
        bh = n / 400 * 150
        fill = "problem" if n < 100 else "bar_blue"
        s.raw(f'<rect x="{bx:.1f}" y="{base - bh:.1f}" width="{bw}" height="{bh:.1f}" rx="2" '
              f'fill="{t.fill(fill)}" stroke="{t.ink}" stroke-width="0.8"/>')
    s.line(scr.x + 8, base, scr.right - 8, base, width=1.3, amount=0.4, passes=1)
    s.text(scr.x + 12 + 2 * 13.4 + 5, base - 26, "S03", size=12, colour=t.accent, weight="bold")
    s.text(scr.cx, base + 20, "S01 … S12", size=11, colour=t.dim)
    s.button(scr.x + 10, scr.bottom - 48, scr.w - 20, "exclude S03, approve", fill="done", h=34)
    s.step(1115, cap_y, 3, "decides from a phone")
    s.text(1115, cap_y + 24, "S03 has 40 reads, the others 400", size=13.5, colour=t.dim)

    # 4 · resume -----------------------------------------------------------------
    s.arrow(1222, 262, 1262, 262)
    s.page(1272, 150, 112, 150, fill="input", lines=0)
    s.text(1328, 176, "samplesheet v2", size=12.5)
    for i, smp in enumerate(("S01", "S02", "S03", "S04", "S05")):
        y = 200 + i * 19
        s.text(1290, y, smp, size=12.5, anchor="start", colour=t.dim if smp != "S03" else t.accent)
    s.line(1286, 236, 1324, 234, colour=t.accent, width=2, amount=0.6, passes=1)
    s.gate(1470, 300, 82, 92, state="passed")
    s.terminal(1396, 322, 270, 74, ("$ nextflow run . -resume",), size=12.5)
    s.step(1500, cap_y, 4, "resumes with the cache")
    s.text(1500, cap_y + 24, "same work dir, samplesheet v2", size=13.5, colour=t.dim)

    # -- row 2: the two runs, one cell per task, to scale ------------------------------
    s.text(60, 562, "every task of both runs, one cell each", size=22, anchor="start")
    cell, gap = 16, 3
    x0 = 300

    def axis(y: float) -> None:
        for n in range(0, 61, 10):
            x = x0 + n * (cell + gap)
            s.line(x, y, x, y + 7, amount=0.3, passes=1, width=1.2, colour=t.dim)
            s.text(x, y + 24, f"{n}", size=12, colour=t.dim)

    y1 = 610
    s.text(x0 - 20, y1 + 17, "run 1 · to the gate", size=16, anchor="end")
    s.task_strip(x0, y1, ((12, "done", "MAKE_READS x12"), (12, "done", "QC_STATS x12"), (1, "gate", "")),
                 cell=cell, gap=gap, h=24, label_size=13)
    s.text(x0 + 25 * (cell + gap) + 46, y1 + 18, "25 run", size=15, anchor="start", weight="bold")

    y2 = 704
    s.text(x0 - 20, y2 + 17, "run 2 · resume, no S03", size=16, anchor="end")
    right = s.task_strip(x0, y2, ((22, "cached", "22 cached: reads and QC of 11 samples"),
                                  (38, "recomputed", "38 run: QC report, split, align, merge, compare, report")),
                         cell=cell, gap=gap, h=24, label_size=13)
    # S03's two upstream tasks are not reused: they are dropped
    for k in range(2):
        cx = right + 14 + k * (cell + gap)
        s.raw(f'<rect x="{cx:.1f}" y="{y2:.1f}" width="{cell}" height="24" rx="2" fill="none" '
              f'stroke="{t.muted}" stroke-width="1" stroke-dasharray="3 3"/>')
        s.cross(cx + cell / 2, y2 + 12, size=6)
    s.text(right + 14 + cell + 2, y2 + 48, "S03", size=13, colour=t.accent)
    axis(y2 + 72)
    s.text(x0 + 30 * (cell + gap), y2 + 118, "tasks", size=13, colour=t.dim)

    # legend
    ly = 880
    for i, (fill, lab) in enumerate((("done", "ran in run 1"), ("gate", "QC report the gate reads"),
                                     ("cached", "cached, not rerun"), ("recomputed", "run in run 2"))):
        lx = 300 + i * 290
        s.raw(f'<rect x="{lx}" y="{ly}" width="{cell}" height="18" rx="2" fill="{t.fill(fill)}" '
              f'stroke="{t.ink}" stroke-width="0.8"/>')
        s.text(lx + 26, ly + 14, lab, size=14, anchor="start", colour=t.dim)

    s.text(60, 960, "Measured: tests/pipelines/synthetic, scenario exclude_sample_and_resume, "
                    "Nextflow 26.10.3, 2026-10-26 · tools/diagrams/gate_resume.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "gate-resume")
