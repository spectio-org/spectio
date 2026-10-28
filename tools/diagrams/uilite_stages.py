#!/usr/bin/env python3
"""Figure for step UILITE: the 0.0.1 run detail, before the stages and after.

Writes docs/assets/diagrams/uilite_stages_{light,dark}.{svg,png}.

Before (autopilot/integration at 1abd5dd): the lite run detail draws four stage cards named by hand,
which no endpoint served (the API had /processes only), above a separate processes table with a Stage
column, and "stage 3 of 4" in the header. After (this step): the stages in order, each with its
state word, "n of m tasks" and a Detected badge, opening to its processes; the header
"3 of 8 stages done · 4 running"; the rules in the ui-spec §4.4 note of 2026-10-28. Stages: the stage-detection
spike's output for nf-core/rnaseq 3.27.0 (tests/pipelines/real/stages/expected/, merged with APPLY6);
counts: the fixture of the lite boards (803 known tasks for 20 samples).
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1640, 820
BX, AX, PW = 40, 840, 760  # before panel x, after panel x, panel width


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=28)
    t = theme

    def bar(x: float, y: float, w: float, done: int, total: int, fill: str) -> None:
        s.shade(x, y, w, 10, fill="bar_grey", opacity=1)
        if done:
            s.shade(x, y, w * done / total, 10, fill=fill, opacity=1)

    s.heading(40, 52, "UILITE · the 0.0.1 run detail: stage cards no API served, then stages with their processes",
              "Thomas, 2026-10-28: \"les 2 dans 0.0.1\" · ui-spec.md §4.4 note of 2026-10-28")

    s.shade(BX, 96, PW, 650, fill="neutral", opacity=0.5)
    s.text(BX + 20, 124, "before", size=22, anchor="start")
    s.shade(AX, 96, PW, 650, fill="done", opacity=0.3)
    s.text(AX + 20, 124, "after", size=22, anchor="start")

    # -- before: hand-named stage cards over a separate processes table -------------------------
    b = s.browser(BX + 30, 144, 470, 560, url="127.0.0.1:8765/runs/…")
    s.text(b.x + 20, b.y + 60, "rnaseq-2026-10-25 · Running", size=16, anchor="start", weight="bold")
    s.text(b.x + 20, b.y + 82, "stage 3 of 4 · 812 / 1,248 tasks", size=13, anchor="start", colour=t.dim)
    cards = (("1 Preprocessing", 288, 288), ("2 Alignment & QC", 336, 336), ("3 Quantification", 188, 300),
             ("4 Reporting", 0, 1))
    for i, (name, done, total) in enumerate(cards):
        y = b.y + 116 + i * 40
        s.rect(Box(b.x + 16, y - 20, 438, 32, "surface"), colour=t.muted)
        s.text(b.x + 28, y, name, size=13, anchor="start")
        bar(b.x + 220, y - 9, 150, done, total, "bar_violet")
    s.text(b.x + 20, b.y + 296, "Processes", size=14, anchor="start", weight="bold")
    s.text(b.x + 20, b.y + 322, "Process", size=12, anchor="start", colour=t.dim)
    s.text(b.x + 250, b.y + 322, "Stage", size=12, anchor="start", colour=t.dim)
    s.text(b.x + 450, b.y + 322, "Done", size=12, anchor="end", colour=t.dim)
    rows = (("SALMON_QUANT", "3 · Quantification", 48), ("SUBREAD_FEATURECOUNTS", "3 · Quantification", 140),
            ("STAR_ALIGN", "2 · Alignment & QC", 48), ("QUALIMAP_RNASEQ", "2 · Alignment & QC", 48),
            ("TRIMGALORE", "1 · Preprocessing", 96), ("FASTQC", "1 · Preprocessing", 96))
    for i, (name, stage, done) in enumerate(rows):
        y = b.y + 350 + i * 30
        s.text(b.x + 20, y, name, size=12.5, anchor="start")
        s.text(b.x + 250, y, stage, size=12.5, anchor="start", colour=t.dim)
        s.text(b.x + 450, y, str(done), size=12.5, anchor="end", colour=t.dim)
    s.text(BX + 520, 200, "stage cards named by hand:", size=14, anchor="start")
    s.text(BX + 520, 222, "no endpoint served them", size=13.5, anchor="start", colour=t.dim)
    s.text(BX + 520, 244, "(the API had /processes only)", size=13.5, anchor="start", colour=t.dim)
    s.text(BX + 520, 330, "\"stage 3 of 4\" reads as", size=14, anchor="start")
    s.text(BX + 520, 352, "one stage at a time", size=13.5, anchor="start", colour=t.dim)
    s.text(BX + 520, 470, "processes in a separate", size=14, anchor="start")
    s.text(BX + 520, 492, "table, a Stage column", size=13.5, anchor="start", colour=t.dim)
    s.text(BX + 520, 514, "of labels; 6 of 14 shown", size=13.5, anchor="start", colour=t.dim)

    # -- after: stages with their processes -----------------------------------------------------
    a = s.browser(AX + 20, 144, 530, 560, url="127.0.0.1:8765/runs/…")
    s.text(a.x + 20, a.y + 60, "rnaseq-2026-10-25 · Running", size=16, anchor="start", weight="bold")
    s.text(a.x + 20, a.y + 82, "3 of 8 stages done · 4 running · 524 / 803 tasks", size=13, anchor="start",
           colour=t.dim)
    stages = (("Prepare genome references + …", 9, 9, "Done"), ("Fastq qc trim filter setstr…", 205, 205, "Done"),
              ("Align star + Quantify bam s…", 145, 145, "Done"), ("Bam markduplicates picard", 96, 120, "Running"),
              ("Bam qc rnaseq", 46, 236, "Running"), ("Bedtools genomecov fw + …", 2, 62, "Running"),
              ("Quantify pseudo alignment", 21, 25, "Running"), ("Report", 0, 1, "Pending"))
    y = a.y + 114
    for i, (name, done, total, word) in enumerate(stages):
        s.text(a.x + 18, y, "⌄" if i == 3 else "›", size=15, anchor="start", colour=t.dim)
        if word == "Done":
            s.tick(a.x + 42, y - 5, size=6)
        else:
            s.hourglass(a.x + 42, y - 5, size=6)
        s.text(a.x + 56, y, name, size=13, anchor="start")
        s.shade(a.x + 250, y - 16, 62, 22, fill="input", opacity=1, colour=t.muted)
        s.text(a.x + 281, y, "Detected", size=11)
        bar(a.x + 320, y - 9, 56, done, total, "bar_violet" if word == "Done" else "bar_blue")
        s.text(a.x + 512, y, f"{done} of {total} · {word}", size=12, anchor="end", colour=t.dim)
        y += 32
        if i == 3:
            for pname, pd, pt in (("PICARD_MARKDUPLICATES", 20, 20), ("SAMTOOLS_INDEX", 20, 20), ("SAMTOOLS_STATS", 16, 20)):
                s.text(a.x + 72, y, pname, size=12.5, anchor="start", colour=t.dim)
                bar(a.x + 320, y - 9, 56, pd, pt, "bar_violet" if pd == pt else "bar_blue")
                s.text(a.x + 512, y, f"{pd} of {pt} · {'Done' if pd == pt else 'Running'}", size=12, anchor="end", colour=t.dim)
                y += 26
            s.text(a.x + 72, y, "… 3 more processes", size=12.5, anchor="start", colour=t.dim)
            y += 30
    s.text(a.x + 20, y + 8, "a process in no stage → \"Not in a stage\";", size=12.5, anchor="start", colour=t.dim)
    s.text(a.x + 20, y + 28, "no stage → the flat list, \"No stages for this pipeline\"", size=12.5, anchor="start", colour=t.dim)

    s.text(AX + 566, 200, "stages in order, each with", size=14, anchor="start")
    s.text(AX + 566, 222, "its word, n of m tasks and", size=13.5, anchor="start", colour=t.dim)
    s.text(AX + 566, 244, "Declared or Detected", size=13.5, anchor="start", colour=t.dim)
    s.text(AX + 566, 330, "state words (§4.4 note):", size=14, anchor="start")
    for i, (w, st) in enumerate((("Pending", "not_started"), ("Running", "running"), ("Done", "completed"),
                                 ("Failed", "failed"), ("Not run", "skipped"))):
        s.text(AX + 566, 354 + i * 22, f"{w} → {st}", size=13, anchor="start", colour=t.dim)
    s.text(AX + 566, 500, "processes keyed by", size=14, anchor="start")
    s.text(AX + 566, 522, "fully qualified name, shown", size=13.5, anchor="start", colour=t.dim)
    s.text(AX + 566, 544, "by its last segment", size=13.5, anchor="start", colour=t.dim)
    s.text(AX + 566, 600, "how stages are found:", size=14, anchor="start")
    s.text(AX + 566, 622, "ui-spec §5.1.1 (APPLY6)", size=13.5, anchor="start", colour=t.dim)

    s.text(40, H - 34, "Sources: design/ui-canvas/LiteRunDetail.dc.html at 1abd5dd (before) and after this step; "
                       "ui-spec §4.4 note 2026-10-28; P1 Assumption 6, Tasks 18 and 20; stages from the stage detector's expected output "
                       "(rnaseq-3.27.0_star_salmon_detected.json) · tools/diagrams/uilite_stages.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "uilite_stages")
