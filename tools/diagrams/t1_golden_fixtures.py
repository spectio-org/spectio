#!/usr/bin/env python3
"""Fixture workflows, golden fixtures and resume identity: step T1, 2026-10-27.

Writes docs/assets/diagrams/t1-golden-fixtures_{light,dark}.{svg,png}.

Every number comes from docs/research/spike-t1-fixture-workflows-2026-10-27.md, from
tests/pipelines/synthetic/golden/ and from tests/pipelines/synthetic/scenarios.yaml:
- golden/: 4 version folders (nextflow-26.10.4, nextflow-25.10.9, nextflow-25.04.8, snakemake-9.27.1),
  11 PR scenarios each, 44 TSV files; fanout_stress is nightly and has none;
- timeout_fatal.tsv: QC_STATS S05 FAILED at attempts 1-3 with exit 143 (NF 26.10.4), `-` (NF 25.10.9 and
  25.04.8) and 124 (Snakemake 9.27.1);
- tool_error_then_fixed_resume.tsv: COMPARE treatA FAILED exit 1 at attempt 1 only on Nextflow, at
  attempts 1, 2, 3 on Snakemake (run_scenarios.py passes `--retries 2`);
- resume identity (research note, inbox #32): NF 26.10.4 run names sharp_meninsky then dreamy_mclean,
  session 2816c414 on both; Snakemake 9.27.1 workflow_id 486ceb8b then 8e78c667;
- the deliberately altered fixture: happy, ALIGN 24 to 23, failed the check.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1780, 1060

VERSIONS = ("nextflow-26.10.4", "nextflow-25.10.9", "nextflow-25.04.8", "snakemake-9.27.1")
SCENARIOS = 11  # PR scenarios per version folder
TIMEOUT_EXIT = (("Nextflow 26.10.4", "143"), ("Nextflow 25.10.9", "-"), ("Nextflow 25.04.8", "-"),
                ("Snakemake 9.27.1", "124"))
TOOL_ERROR_ATTEMPTS = (("Nextflow, all three", 1), ("Snakemake 9.27.1", 3))


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=31)
    t = theme
    s.heading(50, 58, "T1 · Fixture workflows become golden fixtures",
              "synthetic pipelines on the local executor, 3 Nextflow versions and Snakemake 9.27.1 · "
              "every suite ran twice, identical both times")

    # == 1 -- the fixture loop (top band) =============================================================
    top = 150
    s.terminal(50, top, 250, 110, ("$ run_scenarios.py", "  --engine nextflow", "  --golden record"), size=13)
    s.text(175, top + 138, "synthetic pipeline,", size=14, colour=t.dim)
    s.text(175, top + 157, "local executor", size=14, colour=t.dim)
    s.arrow(310, top + 55, 368, top + 55)

    # what the engine leaves behind
    s.page(380, top - 4, 40, 50, fill="input")
    s.text(430, top + 20, "Nextflow trace", size=14.5, anchor="start")
    s.text(430, top + 39, "`execution_trace.txt`", size=12, anchor="start", colour=t.dim)
    s.page(380, top + 66, 40, 50, fill="input")
    s.text(430, top + 90, "Snakemake log", size=14.5, anchor="start")
    s.text(430, top + 109, "`.snakemake/log/`", size=12, anchor="start", colour=t.dim)
    s.arrow(590, top + 55, 640, top + 55)

    # the normaliser: a funnel that drops the noise
    fx = 720
    s.bucket(fx, top + 10, 120, 82, fill="work")
    s.text(fx, top + 60, "normalise", size=15, weight="bold")
    dropped = ("timestamps", "hashes", "durations", "paths")
    for i, word in enumerate(dropped):
        wy = top + 128 + i * 21
        s.text(fx - 30, wy, word, size=13.5, anchor="start", colour=t.dim)
        s.line(fx - 34, wy - 5, fx - 26 + len(word) * 5.9, wy - 5, width=1.4, passes=1, amount=0.3,
               colour=t.accent)
    s.text(fx - 60, top + 128, "drops", size=13.5, anchor="end", colour=t.accent)
    s.text(fx, top + 128 + 4 * 21 + 8, "first-try successes: one count, tag `*`", size=13.5, colour=t.good)
    s.arrow(800, top + 55, 858, top + 55)

    # golden/<engine>-<version>/: one folder per version, one page per scenario (to scale)
    gx = 872
    s.text(gx, top - 12, "`golden/<engine>-<version>/` · one TSV per scenario", size=14, anchor="start",
           weight="bold")
    cell, gap = 14.0, 4.0
    for i, name in enumerate(VERSIONS):
        ry = top + 8 + i * 46
        s.folder(gx, ry, 44, 32, fill="done")
        s.text(gx + 54, ry + 23, f"`{name}`", size=13, anchor="start")
        s.task_strip(gx + 196, ry + 6, ((SCENARIOS, "done", ""),), cell=cell, gap=gap, h=22)
        s.text(gx + 196 + SCENARIOS * (cell + gap) + 6, ry + 23, "11", size=14, anchor="start", colour=t.dim)
    s.text(gx + 196, top + 8 + 4 * 46 + 18, "4 versions x 11 scenarios = 44 files", size=14, anchor="start")

    # CI: --golden check
    s.arrow(1310, top + 85, 1390, top + 85)
    cx = 1480
    s.gate(cx, top + 130, w=96, h=86, state="closed")
    s.text(cx, top + 158, "`--golden check` in CI", size=14)
    s.text(cx + 70, top + 30, "fails on any drift,", size=13.5, anchor="start", colour=t.accent)
    s.text(cx + 70, top + 50, "or a version", size=13.5, anchor="start", colour=t.accent)
    s.text(cx + 70, top + 70, "with no fixtures", size=13.5, anchor="start", colour=t.accent)
    s.cross(cx + 80, top + 104, size=8)
    s.text(cx + 96, top + 102, "`happy` altered,", size=12.5, anchor="start", colour=t.dim)
    s.text(cx + 96, top + 120, "ALIGN 24 to 23: failed", size=12.5, anchor="start", colour=t.dim)
    s.step(890, 440, 1, "run, normalise, record one TSV per scenario, check it on every CI run")

    # == 2 -- one concrete difference: the time-limit exit code (bottom left) ==========================
    lx, by = 50, 520
    s.text(lx, by, "time limit · `timeout_fatal`, QC_STATS for S05", size=15.5, anchor="start", weight="bold")
    cw, ch, cg = 62, 34, 8
    x0 = 240
    for k in range(3):
        s.text(x0 + k * (cw + cg) + cw / 2, by + 30, f"attempt {k + 1}", size=12, colour=t.dim)
    for i, (eng, code) in enumerate(TIMEOUT_EXIT):
        ry = by + 42 + i * 46
        s.text(lx, ry + 23, eng, size=14.5, anchor="start")
        none = code == "-"
        for k in range(3):
            x = x0 + k * (cw + cg)
            s.shade(x, ry, cw, ch, fill="problem", opacity=1.0, colour=t.ink, dashed=none)
            s.text(x + cw / 2, ry + 23, f"`{code}`" if none else code, size=16, weight="bold",
                   colour=t.dim if none else t.ink)
    nx = x0 + 3 * (cw + cg) + 14
    s.text(nx, by + 42 + 23, "exit 143", size=14, anchor="start")
    s.text(nx, by + 42 + 46 + 23, "no exit code, the trace shows a dash", size=14, anchor="start", colour=t.accent)
    s.text(nx, by + 42 + 2 * 46 + 23, "same as 25.10.9", size=14, anchor="start", colour=t.accent)
    s.text(nx, by + 42 + 3 * 46 + 23, "124, from `timeout` in the shell", size=14, anchor="start")

    ty = by + 260
    s.text(lx, ty, "tool error · COMPARE treatA exits 1", size=15.5, anchor="start", weight="bold")
    for i, (eng, n) in enumerate(TOOL_ERROR_ATTEMPTS):
        ry = ty + 18 + i * 46
        s.text(lx, ry + 23, eng, size=14.5, anchor="start")
        for k in range(n):
            x = x0 + k * (cw + cg)
            s.shade(x, ry, cw, ch, fill="problem", opacity=1.0, colour=t.ink)
            s.text(x + cw / 2, ry + 23, "1", size=16, weight="bold")
    s.text(x0 + cw + 14, ty + 18 + 23, "1 attempt, not retried:", size=14, anchor="start")
    s.text(x0 + cw + 14, ty + 18 + 42, "`errorStrategy` does not retry exit 1", size=13, anchor="start", colour=t.dim)
    s.text(nx, ty + 64 + 23, "`--retries 2`: retried by count,", size=14, anchor="start")
    s.text(nx, ty + 64 + 42, "whatever the exit code", size=13, anchor="start", colour=t.dim)
    s.step(410, 985, 2, "the same failure, a different trace per version")

    # == 3 -- resume identity, inbox #32 (bottom right) ================================================
    rx = 920
    s.text(rx, by, "resume identity · inbox #32", size=15.5, anchor="start", weight="bold")
    tw, th, tg = 250, 60, 104

    def lineage(y: float, engine: str, cmds: tuple[str, str], ids: tuple[str, str], linked: bool,
                between: str, under: str, footer: str) -> None:
        s.shade(rx, y, 2 * tw + tg + 40, 196, fill="input", opacity=0.45, colour=t.dim, dashed=True)
        s.text(rx + 16, y + 26, engine, size=15, anchor="start", weight="bold")
        ax = rx + 20
        for k, (cmd, ident) in enumerate(zip(cmds, ids)):
            x = ax + k * (tw + tg)
            s.terminal(x, y + 38, tw, th, (cmd,), size=12.5)
            s.text(x + tw / 2, y + th + 62, ident, size=13.5)
        s.arrow(ax + tw + 8, y + 38 + th / 2, ax + tw + tg - 8, y + 38 + th / 2)
        s.text(ax + tw + tg / 2, y + 38 + th / 2 - 10, between, size=12.5, colour=t.dim)
        mx, my = ax + tw + tg / 2, y + th + 70
        if linked:
            s.link(mx, my, 16, colour=t.good)
        else:
            s.link(mx, my, 16, colour=t.dim)
            s.cross(mx, my, size=10)
        s.text(mx, y + th + 104, under, size=14, colour=t.good if linked else t.accent)
        s.text(rx + 16, y + 186, footer, size=13, anchor="start", colour=t.dim)

    ny = by + 14
    lineage(ny, "Nextflow -resume", ("$ nextflow run", "$ nextflow run -resume"),
            ("run name `sharp_meninsky`", "run name `dreamy_mclean`, new"), True,
            "gate stop", "same session ID `2816c414`",
            "works only from the same launch directory, `.nextflow/history` and cache")
    sy = ny + 222
    lineage(sy, "Snakemake rerun", ("$ snakemake --until qc_report", "$ snakemake"),
            ("`workflow_id` `486ceb8b`", "`workflow_id` `8e78c667`, new"), False,
            "gate stop", "random each time, nothing links them",
            "only the directory links them: its outputs decide what reruns")

    # another directory: Nextflow cannot find the session
    ox = rx + 2 * tw + tg + 70
    s.folder(ox, ny + 40, 54, 38, fill="neutral")
    s.cross(ox + 27, ny + 63, size=9)
    s.text(ox, ny + 104, "another directory:", size=13, anchor="start", colour=t.dim)
    s.text(ox, ny + 122, "Can't find a run", size=13, anchor="start", colour=t.accent)
    # what Spectio does about it
    px, py = ox + 4, sy + 30
    s.page(px, py, 50, 64, fill="docs")
    s.link(px + 25, py + 44, 13, colour=t.ink)
    s.arrow(rx + 2 * tw + tg + 44, ny + 150, px - 6, py + 10, colour=t.dim)
    s.arrow(rx + 2 * tw + tg + 44, sy + 98, px - 6, py + 38, colour=t.dim)
    s.text(px, py + 92, "Spectio records", size=14.5, anchor="start", weight="bold")
    s.text(px, py + 112, "the parent link", size=14.5, anchor="start", weight="bold")
    s.text(px, py + 132, "itself", size=14.5, anchor="start", weight="bold")
    s.step(1290, 985, 3, "a resume is a new run, the engine keeps no lineage")

    s.text(W - 50, H - 20, "source: docs/research/spike-t1-fixture-workflows-2026-10-27.md · "
           "tests/pipelines/synthetic/golden/ · scenarios.yaml", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t1-golden-fixtures")
