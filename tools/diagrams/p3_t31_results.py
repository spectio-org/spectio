#!/usr/bin/env python3
"""A run's results and reports, read only: step P3, P1 Task 31, 2026-11-04.

Writes docs/assets/diagrams/p3-t31-results_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t31 at d4417dc (BASE eb6f7c0):
- packages/spectio-server/src/spectio_server/files/results.py: `results_dir` at launch,
  Snakemake's launch directory, Nextflow's `params.outdir` else the schema default, resolved
  against the launch directory; None for an outdir that holds the runs root or the home
  directory, lies in the runs root outside the launch directory (a work directory, another
  run), has an ENGINE_DIRS part (`.spectio`, `.snakemake`, `.nextflow`), a `..` part or a dot
  directory; `_roots` / `_refuse_aliases`: a root outside the launch directory is opened by its
  path and checked again by inode (runs root, home, `~/.nextflow`, a hidden folder on the
  kernel's path); `list_results`: one folder, MAX_ENTRIES 1000, folders first, engine
  directories and unservable names hidden; a last-component link followed only into a task
  directory of the run's work directory (`open_confined(..., work=work)`); `find_reports`:
  `.html` and `.htm`, breadth first, REPORT_DEPTH 4, SEARCH_ENTRIES 10 000 or SEARCH_S 5 s,
  MultiQC first, MAX_REPORTS 50 kept; CHUNK = MAX_READ 1 MiB;
- packages/spectio-server/src/spectio_server/api/results.py: `GET /runs/ID/results?path=` and
  `GET /runs/ID/results/raw/PATH`; KEPT_SEARCHES 1000 ended runs' reports kept in memory, an
  active run searched on every listing; MAX_RAW 1 GiB, else 413 file-too-large; the whole file
  with its Content-Length, in chunks read in the file pool, a cut or shrunk file aborts the
  response (ShortFile); `.html`/`.htm` carry REPORT_CSP (`sandbox allow-scripts
  allow-downloads`, `connect-src 'none'`, `frame-ancestors 'self'`), other files and
  `?download=true` are an attachment with `sandbox; default-src 'none'`; 404 when the run has
  no results directory (a `cli-observed` run);
- packages/spectio-server/src/spectio_server/files/pool.py: WORKERS 4, BACKLOG 16;
- packages/spectio-server/src/spectio_server/static.py: `/runs/ID/report` answers index.html,
  every screen allows `frame-src 'self'` (CR-P3T31-02);
- web/src/runs/ReportViewer.tsx: the banner "Untrusted report: PATH", "Spectio never asks you
  to paste a link", a Download button, `<iframe sandbox="allow-scripts allow-downloads">`;
- tests/e2e/report.spec.ts with tests/fixtures/results/hostile_report.html: window.open, top
  navigation, the API fetch and document.cookie each read "blocked"; the MultiQC 1.35 fixture
  renders and its frame's origin is "null";
- packages/spectio-server/src/spectio_server/files/redact.py `_Lexer._directive`: in a
  `#SBATCH`, `#PBS`, `#$` or `#BSUB` line, each `NAME=value` item of `--export`, `-v`, `-env`
  is hidden (at BASE the comment said "`#SBATCH` lines are kept");
- the timing bars: measured 2026-11-04 by this script's author with redact.py taken from each
  commit (`git show REV:...redact.py`), `redact_command_run` on the round 6 probe line
  "#SBATCH" + "\\v-v\\vA=x," * 4000 (32 007 characters): ec0e824 5.7 s and 1140 MiB peak RSS,
  d4417dc 0.002 s and 13 MiB; BASE 0.000 s but it kept `A=x` in clear.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1036
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
TOP = 130  # where the files come from
ROW = 360  # the pictograms of each part
TXT = ROW + 168  # the captions
LOW = 756  # the band about the job-file redaction


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=31)
    t = theme
    s.heading(50, 58, "P3 Task 31 · a run's results and reports, read only",
              "`GET /runs/ID/results` and `/results/raw/PATH`, the report viewer `/runs/ID/report` · "
              "dev-env 15.3 req. 13 and 14, api 5")

    # where the files come from -------------------------------------------------------------
    s.hpc_node(60, TOP, 56, 74, busy=3)
    s.hpc_node(126, TOP, 56, 74, busy=2)
    s.text(200, TOP + 20, "the pipeline's tasks", size=15, anchor="start", weight="bold")
    s.text(200, TOP + 42, "publish their outputs to", size=13.5, anchor="start", colour=t.dim)
    s.text(200, TOP + 64, "`params.outdir`, MultiQC,", size=13, anchor="start")
    s.text(200, TOP + 84, "FastQC, any HTML report", size=13.5, anchor="start", colour=t.dim)
    s.arrow(430, TOP + 40, 560, TOP + 40)
    s.text(495, TOP + 30, "write", size=13, colour=t.dim)

    s.folder(580, TOP - 6, 250, 110, fill="input")
    s.text(705, TOP + 46, "the results directory", size=14)
    for i in range(3):
        s.page(650 + i * 40, TOP + 58, 34, 40, fill="surface", lines=2)
    s.text(705, TOP + 128, "files Spectio did not write", size=13, colour=t.dim)

    s.arrow(850, TOP + 40, 990, TOP + 40)
    s.text(920, TOP + 30, "read only", size=13, colour=t.dim)
    s.hpc_node(1010, TOP, 56, 74, busy=1)
    s.cog(1095, TOP + 36, 12, fill="docs")
    s.text(1125, TOP + 20, "`spectio serve`", size=15, anchor="start")
    s.text(1125, TOP + 44, "every read in the file pool:", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, TOP + 64, "4 threads, 16 waiting", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, TOP + 88, "confined below the results root,", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, TOP + 108, "data out, never an open file", size=13.5, anchor="start", colour=t.dim)

    s.line(30, ROW - 60, W - 30, ROW - 60, dashed=True, colour=t.muted)
    s.text(50, ROW - 70, "from launch to the screen, in this order", size=14, anchor="start", colour=t.dim)

    # 1 -- the results directory, fixed at launch ----------------------------------------------
    x = COL[0]
    s.folder(x + 4, ROW, 150, 112, fill="neutral")
    s.text(x + 79, ROW + 30, "launch dir", size=13, colour=t.dim)
    s.folder(x + 30, ROW + 44, 98, 56, fill="input", label="`results`")
    s.tick(x + 140, ROW + 50, size=8, colour=t.good)
    for i, name in enumerate(("`work/`", "`.nextflow/`", "`~/.ssh`", "`../..`")):
        y = ROW + 10 + i * 27
        s.cross(x + 180, y + 4, size=6, colour=t.accent)
        s.text(x + 194, y + 9, name, size=12.5, anchor="start")
    s.text(x + 140, ROW + 140, "checked on the text, then by inode", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "the results directory")
    lines(s, x, TXT + 30, ("fixed at launch, stored on the run",
                           "`outdir`, else the schema default",
                           "Snakemake: the launch directory",
                           "refused: runs root, home, `..`,",
                           "a dot folder, an engine folder"))

    # 2 -- one folder listed ----------------------------------------------------------------------
    x = COL[1]
    rows = (("folder", "`fastqc/`", True), ("folder", "`multiqc/`", True),
            ("page", "`summary.tsv`", True), ("folder", "`.nextflow/`", False))
    for i, (kind, name, ok) in enumerate(rows):
        y = ROW + 8 + i * 30
        if kind == "folder":
            s.folder(x + 6, y, 26, 22, fill="input" if ok else "problem")
        else:
            s.page(x + 9, y - 2, 20, 26, fill="surface", lines=0)
        s.text(x + 42, y + 17, name, size=12.5, anchor="start")
        if ok:
            s.tick(x + 222, y + 11, size=7, colour=t.good)
        else:
            s.cross(x + 222, y + 11, size=7, colour=t.accent)
    s.text(x + 140, ROW + 140, "at most 1000 entries, folders first", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "one folder listed")
    lines(s, x, TXT + 30, ("`?path=` names one folder",
                           "`.spectio` `.snakemake` `.nextflow`",
                           "never listed, never served",
                           "a symlink is followed only into",
                           "a task directory of the run"))

    # 3 -- the reports found ------------------------------------------------------------------------
    x = COL[2]
    # a tree four levels deep, searched breadth first
    levels = ((x + 30, (ROW + 40,)), (x + 70, (ROW + 14, ROW + 66)),
              (x + 110, (ROW + 4, ROW + 30, ROW + 58, ROW + 84)),
              (x + 150, (ROW + 4, ROW + 22, ROW + 40, ROW + 58, ROW + 76, ROW + 94)))
    for (lx, ys), nxt in zip(levels, levels[1:] + ((None, ()),)):
        for y in ys:
            s.dot(lx, y, 4, colour=t.ink)
        if nxt[0] is not None:
            for j, ny in enumerate(nxt[1]):
                py = ys[min(j * len(ys) // len(nxt[1]), len(ys) - 1)]
                s.line(lx + 4, py, nxt[0] - 4, ny, colour=t.muted, amount=0.3, passes=1, width=1.2)
    for i, lx in enumerate((x + 30, x + 70, x + 110, x + 150)):
        s.text(lx, ROW + 124, str(i + 1), size=12, colour=t.dim)
    s.magnifier(x + 112, ROW + 46, 16)
    stack = (("MultiQC", "done"), ("fastqc 1", "surface"), ("fastqc 2", "surface"))
    for i, (name, fill) in enumerate(stack):
        y = ROW + 6 + i * 34
        s.page(x + 190, y, 22, 28, fill=fill, lines=0)
        s.text(x + 218, y + 19, name, size=12.5, anchor="start")
    s.text(x + 140, ROW + 140, "4 levels, 10 000 entries or 5 s", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "the reports found")
    lines(s, x, TXT + 30, ("`.html` and `.htm`, breadth first",
                           "MultiQC first, then by path,",
                           "50 kept, sorted after the search",
                           "active run: searched each listing",
                           "ended run: kept, up to 1000 runs"))

    # 4 -- a raw file -------------------------------------------------------------------------------
    x = COL[3]
    s.page(x + 8, ROW + 2, 58, 76, fill="surface", lines=4)
    s.arrow(x + 74, ROW + 40, x + 100, ROW + 40)
    for i in range(5):
        s.poly([(x + 106 + i * 32, ROW + 28), (x + 134 + i * 32, ROW + 28),
                (x + 134 + i * 32, ROW + 52), (x + 106 + i * 32, ROW + 52)],
               fill="input" if i < 4 else "problem", amount=0.4)
    s.text(x + 120, ROW + 20, "1 MiB", size=12, colour=t.dim)
    s.cross(x + 250, ROW + 40, size=7, colour=t.accent)
    s.text(x + 200, ROW + 74, "cut or shrank:", size=12.5, colour=t.dim)
    s.text(x + 200, ROW + 92, "the download fails", size=12.5, colour=t.dim)
    s.text(x + 140, ROW + 140, "`Content-Length` sent first", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "a raw file")
    lines(s, x, TXT + 30, ("the whole file, up to 1 GiB",
                           "bigger: `413 file-too-large`",
                           "`.html`: the report sandbox CSP",
                           "any other file, or `?download`:",
                           "an attachment, CSP `sandbox`"))

    # 5 -- the report viewer ------------------------------------------------------------------------
    x = COL[4]
    s.browser(x, ROW - 8, 280, 136, url="/runs/ID/report?path=...")
    s.shade(x + 8, ROW + 26, 264, 26, fill="gate", opacity=0.9)
    s.lock(x + 22, ROW + 39, size=8, fill="gate")
    s.text(x + 36, ROW + 44, "Untrusted report: PATH", size=12.5, anchor="start")
    s.shade(x + 8, ROW + 58, 150, 62, fill="neutral", opacity=0.6, colour=t.ink, dashed=True)
    s.page(x + 14, ROW + 64, 30, 46, fill="surface", lines=3)
    s.text(x + 102, ROW + 84, "`iframe sandbox`", size=12)
    s.text(x + 102, ROW + 104, "origin `null`", size=12, colour=t.dim)
    s.arrow(x + 164, ROW + 90, x + 214, ROW + 90, dashed=True, colour=t.dim)
    s.cross(x + 189, ROW + 90, size=8, colour=t.accent)
    s.text(x + 222, ROW + 95, "the API", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 140, ROW + 148, "sandboxed twice: attribute and CSP", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "the report viewer")
    lines(s, x, TXT + 30, ("scripts run, in an opaque origin",
                           "blocked: the API, a new window,",
                           "moving the page, the cookies",
                           "the banner says it is the pipeline's,",
                           "with a Download button"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 46, cx + CW + 23, ROW + 46)

    # the job-file route: directive values now hidden ---------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW - 50, "also in this step: the job-file route's `.command.run`", size=14, anchor="start",
           colour=t.dim)
    s.page(60, LOW, 54, 70, fill="surface", lines=4)
    s.text(87, LOW + 92, "`.command.run`", size=12)
    s.text(140, LOW + 14, "BASE, a scheduler directive was kept as written", size=13.5, anchor="start",
           colour=t.dim)
    s.terminal(140, LOW + 24, 470, 46, (), size=13)
    s.text(160, LOW + 54, "`#SBATCH --export=ALL,TOKEN=s1,B=s2`", size=14, anchor="start",
           colour=t.term_ink)
    s.cross(630, LOW + 47, size=9, colour=t.accent)
    s.text(140, LOW + 100, "now, each value of `--export`, `-v`, `-env` is hidden", size=13.5,
           anchor="start", colour=t.dim)
    s.terminal(140, LOW + 110, 470, 46, (), size=13)
    s.text(160, LOW + 140, "`#SBATCH --export=ALL,TOKEN=«hidden»,B=«hidden»`", size=14,
           anchor="start", colour=t.term_ink)
    s.tick(630, LOW + 133, size=9, colour=t.good)
    s.text(140, LOW + 186, "a quote or a backslash in a value hides the rest of the line: it fails closed",
           size=13.5, anchor="start", colour=t.dim)

    # bars to scale: one crafted line, time and memory -------------------------------------------
    bx, bw = 1000, 500  # 500 px = 6 s
    s.text(720, LOW + 14, "one crafted `#SBATCH` line, 32 007 characters", size=14, anchor="start")
    s.text(720, LOW + 36, "time to redact, drawn to scale, 500 px = 6 s", size=13, anchor="start",
           colour=t.dim)
    bars = (("`ec0e824`, round 6", 5.7, "problem", "5.7 s, 1140 MiB peak memory"),
            ("`d4417dc`, now", 0.002, "done", "0.002 s, 13 MiB"))
    for i, (who, secs, fill, label) in enumerate(bars):
        y = LOW + 62 + i * 52
        s.text(bx - 14, y + 20, who, size=13.5, anchor="end")
        w = max(4.0, bw * secs / 6)
        s.poly([(bx, y), (bx + w, y), (bx + w, y + 28), (bx, y + 28)], fill=fill, amount=0.4)
        lx = bx + w + 10 if w < 200 else bx + 12
        s.text(lx, y + 20, label, size=13, anchor="start")
    s.line(bx, LOW + 54, bx, LOW + 152, colour=t.muted, amount=0.3, passes=1)
    s.text(720, LOW + 180, "an option inside the value before it is skipped, items are split without a regex:",
           size=13, anchor="start", colour=t.dim)
    s.text(720, LOW + 200, "linear again, as BASE was, which kept every value in clear",
           size=13, anchor="start", colour=t.dim)

    s.text(W - 50, H - 16, "source: spectio_server/files/results.py, api/results.py, files/redact.py, "
           "web/src/runs/ReportViewer.tsx, tests/e2e/report.spec.ts · timing measured 2026-11-04 · "
           "P1 Task 31", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t31-results")
