#!/usr/bin/env python3
"""A run's stages, frozen once from the first source that applies: step P3, P1 Task 27, 2026-10-31.

Writes docs/assets/diagrams/p3-t27-stages-freeze_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t27 at 3d4af9b2:
- packages/spectio/src/spectio/runner/headscript.py: LIST_RULES_S = 120, _LIST_RULES runs
  `timeout --foreground 120 <engine> --snakefile ... --configfile params.json --list-rules`
  into `.spectio/rules.txt.tmp`, then `mv` to `.spectio/rules.txt`; on failure no file and one
  line on stderr; then `[ -e .spectio/cancel ] && exit 143`, so the engine never starts after a
  Cancel; Snakemake only;
- packages/spectio-server/src/spectio_server/projector/nextflow.py: `freeze.freeze(p)` on
  `onFlowBegin`, `p.process` on `onProcessCreate`; projector/snakemake.py:
  `freeze.freeze(p, data.snakefile_main)` on `workflow_started`;
- packages/spectio-server/src/spectio_server/stages/freeze.py: freeze() returns at once when a
  `spectio.stages.frozen` event exists, and logs one; _declared: find_overlay first (one match;
  two or more: none, and the note "N lab overlays match this run"), then _own_file (the
  `spectio.yml` at the pipeline directory's root, ignored for another engine), then detection;
  an Overlap on the run's names refuses the file; a source that raises gives no stages ("never a
  failed ingest"); MAX_SPEC_BYTES 65536, MAX_OVERLAYS 100; overlays and their directory owned by
  the server user, not writable by group or others; _NoAliasLoader refuses aliases; _yaml_problem
  keeps PyYAML's problem text, printable only, at most 80, plus line and column, not the snippet;
  _run: the launch command's `location`, else the local location, else _git_copy,
  `data dir/pipelines/<git_url parts>/<quote(revision)>` when it is a directory (CR-P3T27-04);
  every name of the universe goes through assign(), tasks get their process's stage_id;
  refresh() at the end of each transaction;
- stages/assign.py: fnmatchcase, one stage or an Overlap, MAX_STAGES 8;
- stages/detect_nf.py: groups by scope of the fully qualified name, `meta.yml` descriptions,
  MULTIQC is "Report", last; no stages for a flat pipeline or fewer than 2 groups;
- stages/detect_smk.py: one group per included rule file (per sub-directory under `rules/`),
  "Final targets" (the main Snakefile) last; MAX_FILES 200, MAX_FILE_BYTES 1048576; read_confined
  takes regular files under the main Snakefile's directory;
- stages/state.py: stage_state(), the five states and their rules;
- packages/sdk spectio_sdk/stages.py applies(): engine and name, version range on Nextflow only;
- the bars: tests/pipelines/real/stages/expected/rnaseq-3.27.0_star_salmon_detected.json
  (67 processes, 8 stages: 9 11 12 6 13 9 6 1) and mosaicatcher-v2.5.1_detected.json
  (101 rules from `--list-rules`, 8 stages: 15 18 18 14 13 7 15 1), pinned by
  test_detect_nf_golden and test_detect_smk_golden in packages/spectio-server/tests/api/test_stages.py;
- `uv run --locked pytest -q packages/spectio-server/tests/api/test_stages.py
  packages/spectio/tests/test_headscript.py`: all pass (run 2026-10-31; no count, so that the
  figure does not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1236
TOP = 120  # band 1: the run starts
SRC = 446  # band 2: the sources, first that applies
COLS = (50, 580, 1110)  # three source columns, 440 wide
ASG = 866  # band 3: names and states
BOT = 1096  # band 4: the guards

RNASEQ = (9, 11, 12, 6, 13, 9, 6, 1)
MOSAICATCHER = (15, 18, 18, 14, 13, 7, 15, 1)


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 14) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 22, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def snowflake(s: Sketch, cx: float, cy: float, r: float) -> None:
    """Frozen: six arms with a small V near each tip."""
    import math

    for k in range(6):
        a = k * math.pi / 3
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        s.line(cx, cy, ex, ey, width=2.4, amount=0.3, passes=1, colour=s.t.ink)
        mx, my = cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a)
        for side in (-1, 1):
            b = a + side * math.pi / 4
            s.line(mx, my, mx + r * 0.3 * math.cos(b), my + r * 0.3 * math.sin(b),
                   width=2, amount=0.2, passes=1, colour=s.t.ink)
    s.circle(cx, cy, r * 0.16, fill="input")


def strip(s: Sketch, x: float, y: float, counts: tuple[int, ...], cell: float = 6.5,
          gap: float = 1.5, h: float = 24) -> float:
    """One cell per process or rule, grouped by stage; the stage number above, the count under."""
    fills = ("bar_blue", "bar_green")
    cx = x
    for n, count in enumerate(counts, 1):
        fill = "bar_violet" if n == len(counts) else fills[(n - 1) % 2]
        start = cx
        for _ in range(count):
            s.raw(f'<rect x="{cx:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{h:.1f}" rx="1.5" '
                  f'fill="{s.t.fill(fill)}" stroke="{s.t.ink}" stroke-width="0.7"/>')
            cx += cell + gap
        mid = (start + cx - gap) / 2
        s.text(mid, y - 8, f"{n}", size=12.5, colour=s.t.dim)
        s.text(mid, y + h + 17, f"{count}", size=13)
        cx += 10
    return cx


def state_row(s: Sketch, x: float, y: float, name: str, rule: str, mark: str) -> None:
    cx, cy = x + 14, y - 5
    if mark == "empty":
        s.circle(cx, cy, 10, fill="surface")
    elif mark == "running":
        s.circle(cx, cy, 12, fill="work")
        s.hourglass(cx, cy, size=6)
    elif mark == "done":
        s.circle(cx, cy, 12, fill="done")
        s.tick(cx, cy, size=6)
    elif mark == "skipped":
        s.circle(cx, cy, 12, fill="neutral")
        s.line(cx - 6, cy, cx + 6, cy, width=2.4, amount=0.2, passes=1)
    else:
        s.circle(cx, cy, 12, fill="problem")
        s.cross(cx, cy, size=6)
    s.text(x + 38, y, f"`{name}`", size=13.5, anchor="start")
    s.text(x + 150, y, rule, size=13.5, anchor="start", colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=27)
    t = theme
    s.heading(50, 58, "P3 Task 27 · a run's stages, frozen once, above its processes",
              "`spectio_server.stages`, api 7 `run_stages`, ui-spec 5.1.1, checking-scenarios 12.7 · "
              "the first source that applies gives every stage; nothing is guessed after the freeze")

    # 1 -- the run starts ------------------------------------------------------------------------
    s.text(50, TOP + 4, "the head, Snakemake only, before the engine", size=14, anchor="start",
           colour=t.dim)
    s.terminal(50, TOP + 16, 470, 112, ("$ timeout --foreground 120 snakemake \\",
                                        "    --configfile params.json --list-rules",
                                        "  > .spectio/rules.txt"), size=12.5)
    lines(s, 50, TOP + 152, ("fails or over 120 s: no file, the engine starts,",
                             "the server reads the rule files instead",
                             "a Cancel meanwhile: exit 143, no engine"), size=13.5)

    s.arrow(535, TOP + 70, 610, TOP + 70)
    s.envelope(625, TOP + 32, 96, 70, fill="input")
    s.text(740, TOP + 50, "`onFlowBegin`", size=14, anchor="start")
    s.text(740, TOP + 74, "or `workflow_started`", size=14, anchor="start")
    s.text(740, TOP + 98, "the run's first, before any task", size=13.5, anchor="start", colour=t.dim)
    s.text(625, TOP + 152, "Nextflow: its process names came earlier,", size=13.5, anchor="start",
           colour=t.dim)
    s.text(625, TOP + 174, "one per `onProcessCreate`", size=13.5, anchor="start", colour=t.dim)

    s.arrow(1010, TOP + 70, 1090, TOP + 70)
    snowflake(s, 1145, TOP + 68, 40)
    s.text(1205, TOP + 50, "freeze, once", size=17, anchor="start", weight="bold")
    s.text(1205, TOP + 74, "logged as `spectio.stages.frozen`:", size=13.5, anchor="start", colour=t.dim)
    s.text(1205, TOP + 96, "later launches keep these stages", size=13.5, anchor="start", colour=t.dim)
    s.step(800, TOP + 236, 1, "the run starts")

    s.line(30, SRC - 60, W - 30, SRC - 60, dashed=True, colour=t.muted)
    s.text(50, SRC - 44, "inside `freeze`, the first source that applies", size=14, anchor="start",
           colour=t.dim)

    # 2 -- a lab overlay -------------------------------------------------------------------------
    x = COLS[0]
    s.folder(x + 20, SRC - 30, 250, 120, fill="docs")
    s.text(x + 145, SRC + 6, "`~/.spectio/overlays/`", size=13)
    for i in range(3):
        s.page(x + 70 + i * 52, SRC + 22, 40, 52, fill="surface", lines=2)
    s.tick(x + 142, SRC + 56, size=8)
    s.lock(x + 345, SRC + 20, size=14, fill="done")
    s.text(x + 345, SRC + 56, "yours, not", size=13, colour=t.dim)
    s.text(x + 345, SRC + 74, "writable by others", size=13, colour=t.dim)
    s.step(x + 220, SRC + 128, 2, "one lab overlay")
    lines(s, x, SRC + 160, ("`*.spectio.yml`, at most 100, 64 KiB each",
                            "same engine and workflow name,",
                            "Nextflow: its version range too",
                            "exactly one matches: it applies",
                            "two match: none, the run detail says so"))

    # 3 -- the workflow's own spectio.yml -------------------------------------------------------
    x = COLS[1]
    s.folder(x + 20, SRC - 30, 250, 120, fill="input")
    s.text(x + 145, SRC + 6, "pipeline directory", size=13)
    s.page(x + 70, SRC + 22, 44, 56, fill="surface", lines=3)
    s.text(x + 124, SRC + 56, "`spectio.yml`", size=13, anchor="start")
    s.link(x + 345, SRC + 20, size=16)
    s.text(x + 345, SRC + 56, "Git: the copy", size=13, colour=t.dim)
    s.text(x + 345, SRC + 74, "`fetch` wrote", size=13, colour=t.dim)
    s.step(x + 220, SRC + 128, 3, "the workflow's own file")
    lines(s, x, SRC + 160, ("at the root of the directory the launch ran in",
                            "Git: `data dir/pipelines/repo/revision`,",
                            "found again for a rebuilt index, CR-P3T27-04",
                            "written for another engine: ignored",
                            "read under that directory only"))

    # 4 -- detection -----------------------------------------------------------------------------
    x = COLS[2]
    names = ("`NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN`",
             "`NFCORE_RNASEQ:RNASEQ:QUANTIFY_BAM_SALMON:`",
             "`include: rules/count.smk`")
    for i, name in enumerate(names):
        s.text(x + 10, SRC - 4 + i * 26, name, size=12.5, anchor="start", colour=t.dim)
    s.magnifier(x + 380, SRC + 30, 22)
    s.step(x + 220, SRC + 128, 4, "detection")
    lines(s, x, SRC + 160, ("Nextflow: one stage per subworkflow scope,",
                            "its `meta.yml` description, MULTIQC is Report",
                            "Snakemake: one per included rule file,",
                            "the main Snakefile's rules are Final targets",
                            "at most 8, under 2 groups: no stages"))

    s.arrow(COLS[0] + 445, SRC + 30, COLS[1] - 5, SRC + 30)
    s.text(COLS[0] + 487, SRC + 20, "none", size=13, colour=t.dim)
    s.arrow(COLS[1] + 445, SRC + 30, COLS[2] - 5, SRC + 30)
    s.text(COLS[1] + 487, SRC + 20, "none", size=13, colour=t.dim)

    # the overlap refusal, under the two declared sources
    oy = SRC + 272
    s.arc(COLS[0] + 220, oy, COLS[2] + 160, oy, lift=40, dashed=True, colour=t.accent)
    s.warning(COLS[1] + 30, oy + 38, size=11)
    s.text(COLS[1] + 50, oy + 44, "a declared file whose globs overlap on this run's names is refused:",
           size=13.5, anchor="start")
    s.text(COLS[1] + 50, oy + 66, "detection is used", size=13.5, anchor="start", colour=t.dim)

    s.line(30, ASG - 60, W - 30, ASG - 60, dashed=True, colour=t.muted)

    # 5 -- each name gets one stage, to scale ---------------------------------------------------
    s.step(510, ASG - 26, 5, "each name gets one stage, to scale")
    s.text(50, ASG + 14, "nf-core/rnaseq 3.27.0 star_salmon: 67 processes, 8 detected stages",
           size=14, anchor="start")
    strip(s, 60, ASG + 42, RNASEQ)
    s.text(50, ASG + 120, "mosaicatcher v2.5.1: 101 rules from `--list-rules`, 8 detected stages",
           size=14, anchor="start")
    strip(s, 60, ASG + 148, MOSAICATCHER)
    s.text(948, ASG + 62, "last: Report", size=13, anchor="start", colour=t.dim)
    s.text(948, ASG + 168, "last: Final targets", size=13, anchor="start", colour=t.dim)
    s.text(50, ASG + 222, "`fnmatchcase` on the full name; a name first seen after the freeze has no stage,"
           " listed under Not in a stage", size=13.5, anchor="start", colour=t.dim)

    # 6 -- each stage's state --------------------------------------------------------------------
    sx = 1090
    s.step(1320, ASG - 26, 6, "each stage's state")
    rows = (("not_started", "no task started yet", "empty"),
            ("running", "from its first started task", "running"),
            ("completed", "ended, no task left open", "done"),
            ("skipped", "ended with no task", "skipped"),
            ("failed", "the run failed in it, or stopped", "failed"))
    for i, (name, rule, mark) in enumerate(rows):
        state_row(s, sx, ASG + 16 + i * 40, name, rule, mark)
    s.text(sx, ASG + 222, "recounted at the end of each transaction", size=13.5, anchor="start",
           colour=t.dim)

    # the guards ------------------------------------------------------------------------------------
    s.shade(50, BOT, 1000, 110, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(78, BOT + 30, size=11)
    s.text(100, BOT + 36, "a source that fails gives no stages, never a failed ingest", size=13.5,
           anchor="start")
    s.warning(78, BOT + 62, size=11)
    s.text(100, BOT + 68, "YAML: no alias, at most 64 KiB; an error keeps PyYAML's problem, its line and"
           " column, not the quoted line", size=13.5, anchor="start", colour=t.dim)
    s.warning(78, BOT + 94, size=11)
    s.text(100, BOT + 100, "rule files: regular files under the main Snakefile's directory, at most 200"
           " of 1 MiB", size=13.5, anchor="start", colour=t.dim)
    s.terminal(1090, BOT, 460, 110, ("$ uv run --locked pytest -q \\",
                                      "    packages/spectio-server/tests/api/test_stages.py",
                                      "all pass"), size=12)

    s.text(W - 50, H - 14, "source: spectio_server/stages, spectio/runner/headscript.py · bars: "
           "tests/pipelines/real/stages/expected · P1 Task 27", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t27-stages-freeze")
