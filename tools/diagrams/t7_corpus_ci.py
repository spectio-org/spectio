#!/usr/bin/env python3
"""The real-pipeline corpus on GitHub runners: step T7, 2026-10-27.

Writes docs/assets/diagrams/t7-corpus-ci_{light,dark}.{svg,png}.

Every number comes from docs/research/corpus-ci-2026-10-27.md (runs 40555936925, PR tier, and
40562495868, nightly tier, on autopilot/T7 at fc4101c), from tests/pipelines/real/corpus.yaml and
from .github/workflows/ci.yml:
- runner disk on /: 72 GB, 15 GB free at job start, 45.5-47 GB free after `runner_probe.sh free`
  (drawn as 46); molkart dropped to 16.1 GB free and viralrecon to 12.3 GB, so each used about 30-34 GB;
- runner memory: MemTotal 7.75 GB, MemAvailable 6.84-6.96 GB before a run (drawn as 6.9),
  runner_limits.private 6 GB per task; FREYJA_BOOT peak RSS 6.7 GB;
- corpus.yaml tiers: pr 7, nightly 9, manual 7 (23 entries: 14 nf-core, 9 Snakemake catalog);
- ci.yml: ci-ok needs [changes, security, pipelines-synthetic, pipelines-real].
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1780, 1010

# -- to-scale constants ---------------------------------------------------------------------------
DISK_GB, FREE_START, FREE_AFTER = 72, 15, 46
KEPT = DISK_GB - FREE_AFTER  # 26 GB: the image itself
REMOVED = FREE_AFTER - FREE_START  # about 31 GB: toolchains and Docker images
JOB_LO, JOB_HI = 30, 34  # molkart, viralrecon
MEM_TOTAL, MEM_AVAIL, MEM_CAP, FREYJA = 7.75, 6.9, 6.0, 6.7


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=77)
    t = theme
    s.heading(50, 58, "T7 · The real-pipeline corpus on GitHub runners",
              "`ubuntu-latest`, private repository, 2 CPU · PR tier and nightly tier runs on `autopilot/T7`, 2026-10-27")

    # == left: the runner ===========================================================================
    s.hpc_node(70, 170, 90, 120, busy=2, slots=4)
    s.text(115, 318, "GitHub runner", size=16)
    s.text(115, 340, "`ubuntu-26.04` image", size=12.5, colour=t.dim)

    gx = 250  # left edge of the disk bars
    px = 8.0  # pixels per GB

    def seg(x: float, y: float, gb: float, h: float, fill: str, label: str = "", *, dashed: bool = False,
            colour: str | None = None) -> float:
        w = gb * px
        s.shade(x, y, w, h, fill=fill, opacity=1.0, colour=colour or t.ink, dashed=dashed)
        if label:
            s.text(x + w / 2, y + h / 2 + 5, label, size=13.5)
        return x + w

    # 1 -- disk before freeing
    s.text(gx, 162, "disk on /, at job start", size=15, anchor="start", weight="bold")
    y0 = 176
    x = seg(gx, y0, KEPT, 40, "neutral", "image, 26 GB")
    x = seg(x, y0, REMOVED, 40, "recomputed", "toolchains, Docker images")
    free0 = x
    seg(x, y0, FREE_START, 40, "bar_green", "15 free")
    s.text(gx + DISK_GB * px + 8, y0 + 26, "72 GB", size=13.5, anchor="start", colour=t.dim)
    # a big job laid on the free part: it runs off the disk
    jy = y0 + 52
    s.shade(free0, jy, FREE_START * px, 20, fill="bar_blue", opacity=1.0, colour=t.ink)
    s.shade(free0 + FREE_START * px, jy, (JOB_HI - FREE_START) * px, 20, fill="problem", opacity=1.0,
            colour=t.accent, dashed=True)
    s.cross(free0 + JOB_HI * px + 18, jy + 10, size=9)
    s.text(free0 + JOB_HI * px - 4, jy + 40, "no space left on device", size=13.5, anchor="end", colour=t.accent)
    s.text(free0 + JOB_HI * px - 4, jy + 58, "7 nf-core entries failed this way", size=13, anchor="end", colour=t.dim)
    s.text(gx, jy + 15, "viralrecon needs about 34 GB", size=13.5, anchor="start", colour=t.dim)

    # the freeing step
    ax0 = gx + (KEPT + REMOVED / 2) * px
    s.arrow(ax0, y0 + 46, ax0, 332, colour=t.dim)
    s.text(gx, 296, "`runner_probe.sh free` removes them:", size=13, anchor="start")
    s.text(gx, 314, "plain `rm`, 115 to 233 s", size=13, anchor="start", colour=t.dim)

    # 1 -- disk after freeing
    y1 = 340
    x = seg(gx, y1, KEPT, 40, "neutral", "image, 26 GB")
    seg(x, y1, FREE_AFTER, 40, "bar_green", "about 46 GB free")
    s.text(gx + DISK_GB * px + 8, y1 + 26, "72 GB", size=13.5, anchor="start", colour=t.dim)
    jy1 = y1 + 52
    s.shade(x, jy1, JOB_HI * px, 20, fill="bar_blue", opacity=1.0, colour=t.ink)
    s.line(x + JOB_LO * px, jy1 - 4, x + JOB_LO * px, jy1 + 24, width=1.4, passes=1, amount=0.3)
    s.tick(x + JOB_HI * px + 18, jy1 + 8)
    s.text(x + JOB_LO * px - 6, jy1 + 40, "molkart about 30", size=13, anchor="end", colour=t.dim)
    s.text(x + JOB_HI * px + 2, jy1 + 40, "viralrecon about 34, fits", size=13, anchor="start", colour=t.dim)
    s.text(gx, jy1 + 15, "the same job", size=13.5, anchor="start", colour=t.dim)

    # GB axis under the disk bars
    ay = 462
    s.line(gx, ay, gx + DISK_GB * px, ay, width=1.3, passes=1, amount=0.3, colour=t.dim)
    for gb in (0, 15, 30, 46, 60, 72):
        s.line(gx + gb * px, ay - 5, gx + gb * px, ay + 5, width=1.2, passes=1, amount=0.2, colour=t.dim)
        s.text(gx + gb * px, ay + 21, f"{gb}", size=12, colour=t.dim)
    s.text(gx + DISK_GB * px + 8, ay + 4, "GB", size=12, anchor="start", colour=t.dim)
    s.step(gx + DISK_GB * px / 2 - 40, 522, 1, "free the disk first: 15 to about 46 GB")

    # 2 -- memory -----------------------------------------------------------------------------------
    mx, mpx = gx, 74.0  # pixels per GB
    s.text(mx, 600, "memory, same runner", size=15, anchor="start", weight="bold")
    my = 616
    used = MEM_TOTAL - MEM_AVAIL
    s.shade(mx, my, used * mpx, 44, fill="neutral", opacity=1.0, colour=t.ink)
    s.shade(mx + used * mpx, my, MEM_AVAIL * mpx, 44, fill="bar_blue", opacity=1.0, colour=t.ink)
    s.text(mx + used * mpx / 2, my + 70, "in use", size=12.5, colour=t.dim)
    s.text(mx + used * mpx + MEM_AVAIL * mpx / 2, my + 28, "6.9 GB available before a run", size=14)
    s.text(mx + MEM_TOTAL * mpx + 8, my + 20, "7.75 GB", size=13.5, anchor="start", colour=t.dim)
    s.text(mx + MEM_TOTAL * mpx + 8, my + 38, "`MemTotal`", size=12, anchor="start", colour=t.dim)
    # the per-task cap, measured from zero
    cx = mx + MEM_CAP * mpx
    s.line(cx, my - 46, cx, my + 62, width=2.6, passes=1, amount=0.4, colour=t.accent, dashed=True)
    s.text(cx - 8, my - 28, "6 GB cap per task", size=14, anchor="end", colour=t.accent, weight="bold")
    s.text(cx - 8, my - 10, "`runner_limits.private`, unchanged", size=12, anchor="end", colour=t.dim)
    fx = mx + FREYJA * mpx
    s.poly([(fx, my + 50), (fx - 6, my + 60), (fx + 6, my + 60)], fill="gate", colour=t.warn)
    s.text(fx + 2, my + 76, "`FREYJA_BOOT` 6.7, finished", size=12, anchor="start", colour=t.dim)
    ay = my + 128
    s.line(mx, ay, mx + MEM_TOTAL * mpx, ay, width=1.3, passes=1, amount=0.3, colour=t.dim)
    for gb in range(0, 8):
        s.line(mx + gb * mpx, ay - 5, mx + gb * mpx, ay + 5, width=1.2, passes=1, amount=0.2, colour=t.dim)
        s.text(mx + gb * mpx, ay + 21, f"{gb}", size=12, colour=t.dim)
    s.text(mx + MEM_TOTAL * mpx + 8, ay + 4, "GB", size=12, anchor="start", colour=t.dim)
    s.text(mx, ay + 52, "the cap leaves room for the Nextflow JVM and Docker;", size=13.5, anchor="start",
           colour=t.dim)
    s.text(mx, ay + 72, "Nextflow counts against 7.7 GB, so two 6 GB tasks never overlap", size=13.5,
           anchor="start", colour=t.dim)
    s.step(gx + DISK_GB * px / 2 - 40, ay + 118, 2, "6 GB per task fits under 6.9 GB")

    # == right: the corpus ===========================================================================
    rx = 1010
    s.page(rx, 140, 46, 58, fill="input")
    s.text(rx + 60, 164, "`corpus.yaml` · 23 entries", size=16, anchor="start", weight="bold")
    s.text(rx + 60, 188, "14 nf-core, 9 Snakemake catalog", size=13.5, anchor="start", colour=t.dim)
    cell, gap = 18.0, 3.0
    sx0 = rx + 70
    s.task_strip(sx0, 222, ((7, "neutral", ""), (9, "neutral", ""), (7, "neutral", "")), cell=cell, gap=gap, h=22)
    pitch = cell + gap
    starts = (sx0, sx0 + 7 * pitch + 4 * gap, sx0 + 16 * pitch + 8 * gap)
    centres = [st + n * pitch / 2 for st, n in zip(starts, (7, 9, 7))]

    cols = (rx + 10, rx + 250, rx + 490)
    tiers = (("pr", 7, "every PR that touches it"), ("nightly", 9, "scheduled, every night"),
             ("manual", 7, "on demand only"))
    ty = 330
    for (name, n, when), col, c in zip(tiers, cols, centres):
        s.arrow(c, 252, col + 60, ty - 30, colour=t.dim)
        s.text(col, ty, f"{name} · {n}", size=19, anchor="start", weight="bold")
        s.text(col, ty + 22, when, size=13, anchor="start", colour=t.dim)

    sy = ty + 40
    s.task_strip(cols[0], sy, ((7, "bar_green", ""),), cell=cell, gap=gap, h=24)
    s.tick(cols[0] + 7 * pitch + 14, sy + 10)
    s.text(cols[0], sy + 50, "7 of 7 green", size=15, anchor="start")
    s.text(cols[0], sy + 70, "5 nf-core, 2 catalog", size=13, anchor="start", colour=t.dim)
    s.task_strip(cols[1], sy, ((9, "bar_green", ""),), cell=cell, gap=gap, h=24)
    s.tick(cols[1] + 9 * pitch + 14, sy + 10)
    s.text(cols[1], sy + 50, "9 of 9 passed", size=15, anchor="start")
    s.text(cols[1], sy + 70, "8 nf-core, 1 catalog", size=13, anchor="start", colour=t.dim)

    # manual: one cell per entry, a leader line to its cause
    causes = ((2, "problem", "conda pins no longer solve"), (1, "problem", "dead URL, 404"),
              (1, "problem", "missing package, pandas"), (1, "problem", "Ensembl timeout"),
              (1, "problem", "unmaintained since 2019"), (1, "neutral", "mcmicro, manual before T7"))
    for i, (n, fill, label) in enumerate(causes):
        ry = sy + i * 30
        s.task_strip(cols[2], ry, ((n, fill, ""),), cell=cell, gap=gap, h=22)
        s.text(cols[2] + 2 * pitch + 8, ry + 16, label, size=13.5, anchor="start",
               colour=t.accent if fill == "problem" else t.dim)
    s.step(rx + 440, 596, 3, "23 entries in three tiers")

    # == bottom right: the required check ===========================================================
    by = 660
    jobs = (("pipelines-real", "done"), ("changes", "neutral"), ("security", "neutral"),
            ("pipelines-synthetic", "neutral"))
    chip_w = 210
    for i, (name, fill) in enumerate(jobs):
        cy = by + 18 + i * 52
        s.chip(rx, cy, chip_w, name, fill=fill, h=38)
        s.arrow(rx + chip_w + 8, cy + 19, rx + 470, by + 112, colour=t.good if fill == "done" else t.dim,
                width=2.4 if fill == "done" else 1.5)
    s.text(rx + chip_w + 20, by + 8, "back in `needs`, left out in D4", size=13.5, anchor="start", colour=t.good)
    s.text(rx, by + 18 + 4 * 52 + 16, "`ci.yml`: `ci-ok` needs all four", size=13.5, anchor="start", colour=t.dim)
    s.arrow(rx + 70, sy + 84, rx + 70, by + 12, dashed=True, colour=t.dim)
    s.text(rx + 82, 540, "on a PR, it runs", size=13, anchor="start", colour=t.dim)
    s.text(rx + 82, 558, "the pr tier", size=13, anchor="start", colour=t.dim)
    s.gate(rx + 540, by + 150, w=90, h=80, state="passed")
    s.text(rx + 540, by + 180, "`ci-ok`", size=16)
    s.text(rx + 540, by + 202, "required check", size=13.5, colour=t.dim)
    s.text(rx + 600, by + 60, "skipped counts", size=12.5, anchor="start", colour=t.dim)
    s.text(rx + 600, by + 78, "as passing", size=12.5, anchor="start", colour=t.dim)
    s.step(rx + 380, by + 284, 4, "`pipelines-real` gates `ci-ok` again")

    s.text(W - 50, H - 20, "source: docs/research/corpus-ci-2026-10-27.md, runs 40555936925 and 40562495868 · "
           "corpus.yaml · ci.yml", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t7-corpus-ci")
