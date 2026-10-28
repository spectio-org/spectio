#!/usr/bin/env python3
"""Figure for step APPLY6: stages in 0.0.1, declared or detected, above the processes or rules list.

Writes docs/assets/diagrams/apply6_stages_{light,dark}.{svg,png}.

Sources: ui-spec.md §5.1 and §5.1.1 (sources, detection rules), the stage-detection spike note of
2026-10-28 (process names, detector output), tests/pipelines/real/stages/expected/
rnaseq-3.27.0_star_salmon_detected.json and mosaicatcher-v2.5.1_detected.json (stage sizes, to scale),
decision log 2026-10-28, inbox #68.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 860
STRIP_X = 1110  # left edge of the to-scale process cells

# (processes or rules, stage name), from tests/pipelines/real/stages/expected/
RNASEQ = ((9, "Prepare genome references + indices"), (11, "Fastq qc trim filter setstrandedness"),
          (12, "Align star + Quantify bam salmon"), (6, "Bam markduplicates picard"), (13, "Bam qc rnaseq"),
          (9, "Bedtools genomecov … + Bedgraph …"), (6, "Quantify pseudo alignment"), (1, "Report"))
MOSAIC = ((15, "External data"), (18, "Setup + Utils"), (18, "Count + Segmentation"), (14, "Plots"),
          (13, "Regenotyping + Strandphaser"), (7, "Breakpointr + Haplotagging"),
          (15, "Mosaiclassifier + … + Stats"), (1, "Final targets"))


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=68)
    t = theme

    def stages(y: float, rows: tuple[tuple[int, str], ...], fill: str) -> None:
        for i, (n, name) in enumerate(rows):
            yy = y + i * 30
            s.text(STRIP_X - 14, yy + 15, name, size=13, anchor="end")
            s.task_strip(STRIP_X, yy, ((n, fill, ""),), cell=9, gap=2, h=18)
            s.text(STRIP_X + n * 11 + 10, yy + 14, str(n), size=12.5, anchor="start", colour=t.dim)

    s.heading(40, 52, "APPLY6 · 0.0.1 shows stages, declared or detected, above the processes or rules",
              "Thomas's decision of 2026-10-28 · ui-spec.md §5.1 and §5.1.1 · one cell = one process or rule")

    # -- 1 Nextflow: nf-core/rnaseq ------------------------------------------------------------------
    y = 110
    s.text(40, y + 20, "Nextflow", size=18, anchor="start", weight="bold")
    s.text(40, y + 44, "nf-core/rnaseq 3.27.0", size=13.5, anchor="start", colour=t.dim)
    s.terminal(40, y + 64, 420, 150, (
        "onProcessCreate  NFCORE_RNASEQ:PREPARE_GENOME:…",
        "onProcessCreate  NFCORE_RNASEQ:RNASEQ:",
        "    FASTQ_QC_TRIM_FILTER_SETSTRANDEDNESS:FASTP",
        "onProcessCreate  …:RNASEQ:ALIGN_STAR:STAR_ALIGN",
        "… 67 processes, then onFlowBegin",
    ), size=12)
    s.text(40, y + 240, "every name, scoped by its subworkflows,", size=13, anchor="start", colour=t.dim)
    s.text(40, y + 260, "reaches nf-spectio before the first task", size=13, anchor="start", colour=t.dim)
    s.arrow(468, y + 140, 530, y + 140)
    s.cog(560, y + 140, 16, fill="work")
    for i, line in enumerate(("skip the wrapper and", "pipeline scopes;", "one stage per subworkflow;",
                              "aliases merged; Report kept;", "at most 8, by merging", "the smallest neighbours")):
        s.text(590, y + 112 + i * 20, line, size=13, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.arrow(790, y + 140, 830, y + 140)
    stages(y + 20, RNASEQ, "bar_orange")

    s.line(40, y + 285, W - 40, y + 285, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- 2 Snakemake: mosaicatcher-pipeline ----------------------------------------------------------
    y = 410
    s.text(40, y + 20, "Snakemake", size=18, anchor="start", weight="bold")
    s.text(40, y + 44, "mosaicatcher-pipeline v2.5.1", size=13.5, anchor="start", colour=t.dim)
    s.page(40, y + 64, 210, 150, fill="surface", lines=0)
    for i, line in enumerate(("workflow/Snakefile", 'include: "rules/count.smk"',
                              'include: "rules/plots.smk"', "… 26 includes", "rule all: …")):
        s.text(54, y + 92 + i * 24, line, size=12.5, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.arrow(256, y + 140, 300, y + 140)
    for i in range(3):
        s.page(310 + i * 14, y + 90 + i * 12, 110, 70, fill="input", lines=2)
    s.text(375, y + 196, "rule files", size=12.5, colour=t.dim)
    s.text(40, y + 240, "the logger sees rule names only: the server reads the", size=13, anchor="start",
           colour=t.dim)
    s.text(40, y + 260, "files from snakefile_main; --list-rules drops unused ones", size=13, anchor="start",
           colour=t.dim)
    s.arrow(468, y + 140, 530, y + 140)
    s.cog(560, y + 140, 16, fill="work")
    for i, line in enumerate(("one stage per rule file,", "in include order;", "a rules/ sub-directory",
                              "is one stage; the main", "Snakefile's rules last;", "at most 8")):
        s.text(590, y + 112 + i * 20, line, size=13, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.arrow(790, y + 140, 830, y + 140)
    stages(y + 20, MOSAIC, "bar_blue")

    s.line(40, y + 285, W - 40, y + 285, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- 3 precedence --------------------------------------------------------------------------------
    y = 715
    s.text(40, y + 22, "per run", size=18, anchor="start", weight="bold")
    s.page(170, y, 230, 64, fill="docs", lines=0)
    s.text(285, y + 26, "1 · declared", size=14, weight="bold")
    s.text(285, y + 48, "spectio.yml or a lab overlay", size=12.5, colour=t.dim)
    s.text(420, y + 38, ">", size=22)
    s.frame(440, y, 230, 64, fill="work")
    s.text(555, y + 26, "2 · detected", size=14, weight="bold")
    s.text(555, y + 48, "display only, no gates", size=12.5, colour=t.dim)
    s.text(690, y + 38, ">", size=22)
    s.frame(710, y, 230, 64, fill="neutral")
    s.text(825, y + 26, "3 · none", size=14, weight="bold")
    s.text(825, y + 48, "flat pipelines: the list only", size=12.5, colour=t.dim)
    s.tick(980, y + 30)
    s.text(1000, y + 26, "always: the processes or rules list, grouped", size=13.5, anchor="start")
    s.text(1000, y + 48, "under the stages; names in no stage in their own group", size=13.5, anchor="start")

    s.text(40, H - 24, "Sources: ui-spec §5.1, §5.1.1; spike note 2026-10-28; tests/pipelines/real/stages/expected/ "
                       "(stage sizes); decision log 2026-10-28; inbox #68 · tools/diagrams/apply6_stages.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply6_stages")
