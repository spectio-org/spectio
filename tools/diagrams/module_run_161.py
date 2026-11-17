#!/usr/bin/env python3
"""A run can target one step: one Nextflow module or one Snakemake rule (issue #161, 0.0.2).

Writes docs/assets/diagrams/module-run-161_{light,dark}.{svg,png}.

Every fact comes from the branch claude/module-run-161:
- docs/specs/api-and-data-model.md §5.10: the `target` object (kind, name, version, hash,
  checksum_changed); a registry module needs a pinned version, never latest; the checksum is
  known once the head has installed the module and is the one nf-spectio reports; an earlier
  run of the same registry name@version with another checksum sets `checksum_changed`; a target
  run has no stages and no gates; `POST /targets:inspect` runs `snakemake -n <rule>` in an empty
  temporary directory; a module run's graph is one node; rules outside the target come as
  `not_needed`; `GET /runs?target=none` and `?target=any`;
- docs/specs/ui-spec.md §4.15: the Scope colours (grey for a pipeline, the accent for a module,
  sky for a rule or a file), the Scope badge's cells (three grey, one lit, the second of two
  lit), the "Same version, different content" warning, "checksum changed" in the runs list, the
  Scope filter (Any scope, Pipelines, Single steps), the dry-run preview (a failed one still
  lets the user launch);
- docs/research/spike-module-run-2026-11-10.md: run 3 (`nextflow module run nf-core/fastqc
  -version 0.0.0-6d1763b`, process FASTQC), findings 4 (outputs stay in work), 5 (installed into
  `./modules/nf-core/fastqc/`, `.module-info` holds `checksum=b64b18ed...` of 64 hex and
  `registryUrl=`), 8 (`-params-file`); module run is in Nextflow 26.04 and later;
- spikes/module-run/smk-qc_report-empty.txt: `snakemake -n qc_report` from an empty directory
  plans make_reads 12, qc_stats 12, qc_report 1, total 25 (Snakemake 9.27.1);
- tests/pipelines/synthetic/snakemake/workflow/Snakefile: the other rules (all, split, align,
  align_done, merge, compare, final_report).

The earlier run's checksum is not drawn as a value: the spike recorded only one.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1600, 1330
MID = 800  # the line between the two halves
LX, RX = 50, 840  # left edges of the halves
YA, CAPA = 150, 330  # row A and its caption
YB, CAPB = 420, 606  # row B
YC, CAPC = 690, 872  # row C
DIV = 944  # above the runs list
TOP3 = 972
CAP3 = 1236

# The Scope colours of ui-spec 4.15: the badge's fill and its lit cell.
SCOPE = {
    "Pipeline": ("neutral", "bar_grey", (True, True, True)),
    "Module": ("violet", "bar_violet", (True,)),
    "Rule": ("input", "bar_blue", (False, True)),
}
RULE_JOB = "bar_blue"  # a job of a Rule-scoped run, in the Rule scope colour


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "middle") -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor=anchor, colour=s.t.dim)


def scope_badge(s: Sketch, x: float, y: float, kind: str) -> None:
    """The runs list's Scope badge: the word, then the cells that repeat it."""
    fill, lit, cells = SCOPE[kind]
    s.shade(x, y, 136, 28, fill=fill, opacity=1.0, colour=s.t.ink)
    s.text(x + 12, y + 19, kind, size=14, anchor="start", weight="bold")
    for i, on in enumerate(cells):
        cx = x + 88 + i * 15
        s.raw(f'<rect x="{cx:.1f}" y="{y + 8:.1f}" width="11" height="12" rx="2" '
              f'fill="{s.t.fill(lit if on else "surface")}" stroke="{s.t.ink}" stroke-width="0.9"/>')


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=161)
    t = theme
    s.heading(LX, 58, "#161 · A run can target one step: one Nextflow module, or one Snakemake rule",
              "the run's `target`, behind the `single_target` feature flag in 0.0.2 · api 5.10, "
              "ui-spec 4.15, spike module-run of 2026-11-10")

    s.line(MID, 112, MID, DIV - 24, dashed=True, colour=t.muted)
    s.text(LX, 128, "Nextflow module: one process, outside any pipeline", size=19, anchor="start",
           weight="bold")
    s.text(RX, 128, "Snakemake rule: the rule and only the jobs it needs", size=19, anchor="start",
           weight="bold")

    # 1 -- installed from the registry ------------------------------------------------------------
    s.terminal(LX, YA + 4, 420, 104, ("$ nextflow module run nf-core/fastqc \\",
                                       "    -version 0.0.0-6d1763b \\",
                                       "    -params-file params.json"), size=13, line_h=20)
    s.text(LX + 420, YA + 136, "the registry serves the module", size=12.5, anchor="end",
           colour=t.dim)
    s.arrow(LX + 432, YA + 56, 506, YA + 56)
    fx = 516
    s.folder(fx, YA - 6, 250, 166, fill="input")
    s.text(fx + 14, YA + 30, "`./modules/nf-core/fastqc/`", size=12.5, anchor="start", weight="bold")
    s.text(fx + 14, YA + 54, "`main.nf`  `meta.yml`", size=12.5, anchor="start", colour=t.dim)
    s.page(fx + 14, YA + 70, 40, 52, fill="docs", lines=2)
    s.text(fx + 66, YA + 86, "`.module-info`", size=12.5, anchor="start")
    s.text(fx + 66, YA + 106, "`checksum=b64b18ed`", size=12, anchor="start", colour=t.dim)
    s.text(fx + 66, YA + 124, "64 hex in all", size=12, anchor="start", colour=t.dim)
    s.text(fx + 14, YA + 148, "in the launch directory", size=12.5, anchor="start", colour=t.dim)
    s.step(405, CAPA, 1, "installed from the registry, with its checksum")
    lines(s, 405, CAPA + 28, ("a pinned version, never latest: Spectio runs only what it showed",
                              "`nextflow module run` exists from Nextflow 26.04"))

    # 2 -- one process, one node ------------------------------------------------------------------
    nx = 160
    s.circle(nx, YB + 62, 44, fill="surface", width=2)
    s.cog(nx, YB + 62, 14, fill="work")
    s.text(nx, YB + 134, "`FASTQC`", size=14)
    s.text(nx, YB + 154, "the whole graph", size=12.5, colour=t.dim)
    s.step(nx, CAPB, 2, "one process, one node")
    lines(s, nx, CAPB + 28, ("no stages, no gates", "outputs stay in `work/`"))

    # 3 -- nf-spectio reports the target ----------------------------------------------------------
    ex = 330
    s.envelope(ex, YB + 18, 92, 62, fill="docs")
    s.text(ex + 46, YB + 104, "nf-spectio", size=13.5)
    s.text(ex + 46, YB + 124, "`onFlowCreate`", size=12.5, colour=t.dim)
    tx = ex + 120
    s.text(tx, YB + 14, "`target`", size=14, anchor="start", weight="bold")
    for i, row in enumerate(("`kind` module", "`name` nf-core/fastqc", "`version` 0.0.0-6d1763b",
                             "`hash` the checksum, b64b18ed")):
        y = YB + 40 + i * 22
        s.dot(tx + 4, y - 4, 2.6, colour=t.dim)
        s.text(tx + 14, y, row, size=13, anchor="start")
    s.step(565, CAPB, 3, "nf-spectio reports the target")
    lines(s, 565, CAPB + 28, ("for a run Spectio launched, and for one", "started from a terminal"))

    # 4 -- the checksum is compared ---------------------------------------------------------------
    for px, title, check, fill in ((LX + 10, "an earlier run", "another checksum", "neutral"),
                                   (LX + 200, "this run", "checksum `b64b18ed`", "surface")):
        s.page(px, YC, 150, 118, fill=fill, lines=0)
        s.text(px + 14, YC + 30, title, size=14, anchor="start", weight="bold")
        s.text(px + 14, YC + 54, "`nf-core/fastqc`", size=12.5, anchor="start")
        s.text(px + 14, YC + 74, "`0.0.0-6d1763b`", size=12.5, anchor="start")
        s.text(px + 14, YC + 98, check, size=12.5, anchor="start", colour=t.dim)
    s.magnifier(LX + 176, YC + 48, 11)
    s.text(LX + 180, YC + 140, "same `name@version`", size=12.5, colour=t.dim)
    wx = 470
    s.shade(wx, YC + 6, 300, 108, fill="gate", opacity=1.0, colour=t.warn)
    s.warning(wx + 24, YC + 34, size=11)
    s.text(wx + 44, YC + 40, "Same version, different content", size=15, anchor="start",
           weight="bold")
    s.text(wx + 16, YC + 66, "the registry served other files,", size=13, anchor="start")
    s.text(wx + 16, YC + 86, "so results may not match", size=13, anchor="start")
    s.text(wx + 16, YC + 106, "on the run's header", size=12, anchor="start", colour=t.dim)
    s.arrow(LX + 360, YC + 60, wx - 10, YC + 60)
    s.step(405, CAPC, 4, "Spectio compares the checksum with earlier runs")
    lines(s, 405, CAPC + 28, ("another checksum for the same registry `name@version`",
                              "sets `checksum_changed` on the run"))

    # 5 -- the dry run, before launch -------------------------------------------------------------
    s.terminal(RX, YA + 4, 330, 150, ("$ snakemake -n qc_report",
                                      "job          count",
                                      "make_reads      12",
                                      "qc_stats        12",
                                      "qc_report        1",
                                      "total           25"), size=13, line_h=17)
    ix = RX + 360
    s.text(ix, YA + 20, "`POST /targets:inspect`", size=14, anchor="start", weight="bold")
    s.text(ix, YA + 40, "nothing is written", size=12.5, anchor="start", colour=t.dim)
    for i, row in enumerate(("in an empty temporary directory,",
                             "so it counts every job the rule needs",
                             "shown on the Launch form; a failed",
                             "dry run still lets you launch")):
        s.text(ix, YA + 70 + i * 20 + (8 if i > 1 else 0), row, size=13, anchor="start",
               colour=t.ink if i < 2 else t.dim)
    s.step(1195, CAPA, 5, "before launch, a dry run counts 25 jobs")
    lines(s, 1195, CAPA + 28, ("Snakemake 9.27.1, the synthetic test pipeline",
                               "spike output `smk-qc_report-empty.txt`"))

    # 6 -- only the jobs the target needs, to scale ----------------------------------------------
    s.terminal(RX, YB - 6, 300, 64, ("$ snakemake qc_report",), size=13)
    cell, gap, ch = 11, 2, 26
    jy = YB + 120
    g1 = RX + 20
    g2 = g1 + 12 * (cell + gap) + 48
    g3 = g2 + 12 * (cell + gap) + 48
    s.line(g1, jy - 16, g3 + cell, jy - 16, colour=t.dim, amount=0.6, passes=1)
    for x in (g1, g3 + cell):
        s.line(x, jy - 22, x, jy - 10, colour=t.dim, amount=0.3, passes=1)
    s.text((g1 + g3 + cell) / 2, jy - 26, "25 jobs, one cell each", size=13, colour=t.dim)
    s.task_strip(g1, jy, ((12, RULE_JOB, ""),), cell=cell, gap=gap, h=ch)
    s.task_strip(g2, jy, ((12, RULE_JOB, ""),), cell=cell, gap=gap, h=ch)
    s.task_strip(g3, jy, ((1, RULE_JOB, ""),), cell=cell, gap=gap, h=ch)
    s.rect(Box(g3 - 5, jy - 5, cell + 10, ch + 10), rx=4)  # the target
    for a, b in ((g1 + 12 * (cell + gap) + 6, g2 - 10), (g2 + 12 * (cell + gap) + 6, g3 - 12)):
        s.arrow(a, jy + ch / 2, b, jy + ch / 2)
    for cx, name, n in ((g1 + 77, "`make_reads`", "12 jobs"), (g2 + 77, "`qc_stats`", "12 jobs"),
                        (g3 + 5, "`qc_report`", "1 job, the target")):
        s.text(cx, jy + ch + 24, name, size=13)
        s.text(cx, jy + ch + 44, n, size=12.5, colour=t.dim)

    s.text(RX, YC + 2, "not needed, so not run", size=14, anchor="start")
    nx0, ny = RX, YC + 20
    for name in ("all", "split", "align", "align_done", "merge", "compare", "final_report"):
        w = 26 + len(name) * 8.2
        if nx0 + w > W - 50:
            nx0, ny = RX, ny + 46
        s.shade(nx0, ny, w, 32, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
        s.text(nx0 + w / 2, ny + 21, f"`{name}`", size=12.5, colour=t.dim)
        nx0 += w + 12
    s.text(RX, ny + 64, "`split` is a checkpoint; `all` is the default target", size=12.5,
           anchor="start", colour=t.dim)
    s.step(1195, CAPC, 6, "only the jobs the target needs run")
    lines(s, 1195, CAPC + 28, ("the target and what it needs; the run's other rules",
                               "come as `not_needed`, shown dashed and faded"))

    # 7 -- the runs list ---------------------------------------------------------------------------
    s.line(30, DIV, W - 30, DIV, dashed=True, colour=t.muted)
    bw = 1040
    s.browser(LX, TOP3, bw, 226, url="`GET /runs`  ·  Runs")
    hy = TOP3 + 58
    cols = (LX + 22, LX + 200, LX + 760, LX + 900)
    for x, head in zip(cols, ("Scope", "Workflow", "What ran", "Steps")):
        s.text(x, hy, head, size=13.5, anchor="start", colour=t.dim, weight="bold")
    s.line(LX + 14, hy + 10, LX + bw - 14, hy + 10, colour=t.muted, amount=0.5, passes=1)
    for i, (kind, ran, steps) in enumerate((("Pipeline", "every rule", ""),
                                            ("Module", "1 process", "1 to 4"),
                                            ("Rule", "25 jobs", "5 and 6"))):
        ry = hy + 50 + i * 48
        scope_badge(s, cols[0], ry - 19, kind)
        s.text(cols[2], ry, ran, size=14, anchor="start")
        s.text(cols[3], ry, steps, size=13.5, anchor="start", colour=t.dim)
        if kind == "Module":
            s.text(cols[1], ry, "`nf-core/fastqc`  `0.0.0-6d1763b`", size=13.5, anchor="start")
            cx = cols[1] + 300
            s.shade(cx, ry - 19, 190, 28, fill="gate", opacity=1.0, colour=t.warn)
            s.warning(cx + 18, ry - 6, size=8)
            s.text(cx + 34, ry, "checksum changed", size=13.5, anchor="start")
        else:
            s.text(cols[1], ry, "the `synthetic` Snakemake pipeline", size=13.5, anchor="start")
            if kind == "Rule":
                ax = cols[1] + 300
                s.arrow(ax, ry - 5, ax + 26, ry - 5)
                s.text(ax + 36, ry, "`qc_report`", size=13.5, anchor="start")

    fx = LX + bw + 50
    s.text(fx, TOP3 + 16, "the Scope filter, beside the state filter", size=14, anchor="start")
    for i, (label, query, w) in enumerate((("Any scope", "", 110), ("Pipelines", "`?target=none`", 112),
                                           ("Single steps", "`?target=any`", 132))):
        bx = fx + sum((110, 112, 132)[:i]) + i * 10
        s.button(bx, TOP3 + 34, w, label, fill="input" if i == 0 else "surface")
        if query:
            s.text(bx + w / 2, TOP3 + 88, query, size=12.5, colour=t.dim)
    s.text(fx, TOP3 + 136, "colour never carries the scope alone:", size=13, anchor="start")
    s.text(fx, TOP3 + 157, "the word is written, and the cells repeat it,", size=13,
           anchor="start", colour=t.dim)
    s.text(fx, TOP3 + 178, "three for a pipeline, one for a module,", size=13, anchor="start",
           colour=t.dim)
    s.text(fx, TOP3 + 199, "the second of two for a rule or a file", size=13, anchor="start",
           colour=t.dim)

    s.step(LX + bw / 2, CAP3, 7, "both runs land in the runs list, with a Scope badge")
    lines(s, LX + bw / 2, CAP3 + 28, ("grey for a whole pipeline, the violet accent for a module, "
                                      "sky blue for a rule or a file",))

    s.text(W - 50, H - 18, "source: api 5.10, ui-spec 4.15, spike module-run 2026-11-10 "
           "and its `smk-qc_report-empty.txt` · issue #161", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "module-run-161")
