#!/usr/bin/env python3
"""The file explorer and preview, and a rule in no rule graph: batch P3-B09 (steps P3-fu90,
P3-fu85-spec, P3-fu85a to P3-fu85e, wave W5), 2026-11-09.

Writes docs/assets/diagrams/p3-b09-file-explorer_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B09 at 73ca47a4 (PRs 182 to 186, 188 and 189 merged
into autopilot/integration between b5d846f8 and 9872f93b, then the batch code-simplifier's two
commits 66721c21 and 73ca47a4):
- P3-fu85-spec, PR 183: ui-spec 4.4.1, api 5.3, dev-env 15.3 req. 14 (notes 2026-11-08); review
  record docs/reviews/code/P3-fu85-spec.md: R0 self-review (not independent) security 0/2/7, UX
  0/1/9; R1 independent security 0/2/9, UX 0/5/15, all applied; no code, so no code-reviewer and
  no tests;
- P3-fu85a, PR 184: api/results.py `result_stat` (`ResultStat`: root, path, name, type, size,
  mtime) and `result_text`; files/confine.py TAIL 65536, MAX_READ 1048576;
  test_results.py:597 `test_req13_results_text_utf8_seam` ("abcé.def", `Range: bytes=0-3`, 206,
  `bytes 0-2/9`, next read from 3); CORP same-origin in api/taskfiles.py HEADERS;
- P3-fu85b, PR 185: api/results.py `_image_type` and `raw_response` (`as` = `image` and
  `Sec-Fetch-Dest: image`, else the attachment; MAX_IMAGE 20 MiB, MAX_SVG 5 MiB; `Vary:
  Sec-Fetch-Dest`); files/images.py MAX_PIXELS 50_000_000 and the PNG, GIF, WebP, JPEG
  signatures; files/results.py `open_raw` (size, `(st_dev, st_ino)`, first chunk) and
  `read_chunk` (`Replaced`);
- P3-fu85c, PR 186: web/src/runs/FilePreview.tsx (route `/runs/$id/results/file`, Start, End,
  Load more, "… cut at", "Whole file"), runs/preview.ts (READ 64 KiB, SHOWN_MAX 1 MiB,
  LINES_MAX 20000, LINE_MAX 10000, JSON_FORMATTED_MAX 2 MiB, ROWS_MAX 500, COLUMNS_MAX 50,
  KIND_WORDS);
- P3-fu85d, PR 188: web/src/runs/ResultsBrowser.tsx (COLUMNS Name, Size, Modified, Kind put in
  second; "Filter this folder"; a Download icon per file), runs/explorer.ts (SORTS),
  ResultsBrowser.test.tsx (`fastqc`, `S01_fastqc.html`, `versions.yml`, "Results · 1 folder,
  4 files"); `&sort=`, `&q=`, `&focus=`, `&task=`, `&attempt=`;
- P3-fu85e, PR 189: api/workdir.py (BASE `/tasks/{task_id}/attempts/{n}/workdir`, its stat,
  text and raw routes, `check_work_rel` refusing a part that starts with `.`), test_workdir.py:66
  to 74 and 134 (`.command.env`, `.command.run`, `counts.tsv`, `qc`, `x` linked to
  `.command.env`); TaskFiles.tsx "Browse work directory";
- P3-fu90, PR 182: api/runs_read.py `_rulegraphs` and `_pipeline_order`;
  test_process_status.py `test_pipeline_order_rule_missing_from_rulegraph` (the two orders drawn);
- findings: docs/reviews/code/P3-fu90.md, P3-fu85-spec.md, P3-fu85a.md to P3-fu85e.md. Every
  blocker and major is pinned under the step that built its fix: the ten design majors of
  P3-fu85-spec (SEC-PRE-FU85-01, -02, UX-PRE-FU85-01, SEC-PRE-FU85-R1-01, -R1-02,
  UX-PRE-FU85-R1-01 to -R1-05) and the six code majors of P3-fu85c (CR-P3FU85C-01, -02, -03,
  SEC-P3FU85C-01, CR-P3FU85C-R3-06, -R3-07). No blocker anywhere; P3-fu90, -85a, -85b, -85d and
  -85e had no major;
- the batch simplifier's report: `git diff --numstat 9872f93b..73ca47a4` (7 files, +54 -61);
  pytest 1189 passed, 1 skipped, before and after; vitest 432 passed, after only (no
  node_modules before); re-review approve both, minors CR-P3B09-01, -02, SEC-P3B09-01.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1850, 1700
COLS = ((50, 220), (292, 245), (559, 245), (826, 430), (1278, 245), (1545, 255))
HEAD = 182  # the step's name above its pictogram
TOP = 204  # the pictograms
CAP = 456  # the numbered captions
PIN = 566  # the pins and notes
LOW = 1152  # fu90, the batch simplifier and the tests


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, rows: tuple[str, ...], status: str,
        *, w: float) -> float:
    """A major pinned where it hit: its ID, what it was, how it was closed; returns its bottom."""
    h = 32 + 18 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 14, y + 13, size=5.5)
    s.text(x + 27, y + 18, fid, size=11.5, anchor="start", weight="bold")
    s.text(x + w - 8, y + 18, tag, size=11, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 10, y + 38 + i * 18, row, size=12, anchor="start")
    s.text(x + 10, y + 38 + len(rows) * 18, status, size=12, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float,
         warn: bool = False) -> float:
    """A dashed note: the rounds, what is open; returns its bottom."""
    h = 12 + 20 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 0
    if warn:
        s.warning(x + 17, y + 18, size=7.5)
        ox = 16
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 23 + i * 20, row, size=12, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, dashed: bool = False) -> None:
    if dashed:
        s.shade(x, y, w, h, fill="neutral", opacity=0.0, colour=s.t.muted, dashed=True)
        return
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def picture(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    """An image file: a frame, a sun, a hill."""
    cell(s, x, y, w, h, "input")
    s.circle(x + w * 0.72, y + h * 0.3, h * 0.11, fill="gate", width=1.1)
    s.poly([(x + 4, y + h - 4), (x + w * 0.38, y + h * 0.42), (x + w * 0.62, y + h * 0.72),
            (x + w * 0.76, y + h * 0.58), (x + w - 4, y + h - 4)], fill="done", amount=0.3, width=1.1)


def download(s: Sketch, cx: float, cy: float, size: float = 7) -> None:
    """The Download icon: an arrow into a tray."""
    s.arrow(cx, cy - size, cx, cy + size * 0.5, colour=s.t.ink)
    s.line(cx - size, cy + size, cx + size, cy + size, passes=1, amount=0.2, width=1.4)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=909)
    t = theme
    s.heading(50, 58, "P3-B09 · browse and preview a run's files, and a rule in no rule graph",
              "wave W5 · steps P3-fu90, P3-fu85-spec, P3-fu85a to P3-fu85e · 2026-11-08 to 11-09 · "
              "PRs 182 to 186, 188 and 189 into `autopilot/integration`")
    band(s, 140, "FU-P3-85, the file explorer and preview, in build order · design, then the server "
         "routes, then the pages · the results directory, then a task's work directory")

    # 1 -- P3-fu85-spec: the design first ------------------------------------------------------
    x, w = COLS[0]
    s.text(x, HEAD, "P3-fu85-spec · PR 183", size=14, anchor="start", weight="bold")
    for i, (name, part) in enumerate((("ui-spec", "4.4.1"), ("api", "5.3"), ("dev-env", "req. 14"))):
        px = x + 4 + i * 74
        s.page(px, TOP + 2, 62, 78, fill="docs", lines=3)
        s.text(px + 31, TOP + 100, name, size=12)
        s.text(px + 31, TOP + 117, part, size=11.5, colour=t.dim)
    s.browser(x + 4, TOP + 138, 110, 64)
    cell(s, x + 14, TOP + 152, 60, 14, "input")
    s.line(x + 14, TOP + 180, x + 94, TOP + 180, colour=t.muted, passes=1, amount=0.3)
    s.line(x + 14, TOP + 192, x + 70, TOP + 192, colour=t.muted, passes=1, amount=0.3)
    s.text(x + 126, TOP + 166, "boards", size=12.5, anchor="start")
    s.text(x + 126, TOP + 184, "before the", size=12, anchor="start", colour=t.dim)
    s.text(x + 126, TOP + 201, "screens", size=12, anchor="start", colour=t.dim)
    s.step(x + w / 2, CAP, 1, "design first", size=18)
    lines(s, x, CAP + 30, ("two new spec sections, no code",
                           "pre-review R0, then R1 independent",
                           "build plan 85a to 85e, inbox 127",
                           "no code-reviewer, no tests"))

    # 2 -- P3-fu85a: stat, and a text read that ends on a whole character ----------------------
    x, w = COLS[1]
    s.text(x, HEAD, "P3-fu85a · PR 184", size=14, anchor="start", weight="bold")
    s.folder(x + 2, TOP + 8, 82, 54, fill="input", label="results")
    s.arrow(x + 88, TOP + 36, x + 118, TOP + 36)
    s.text(x + 103, TOP + 28, "`stat`", size=11)
    cell(s, x + 122, TOP + 2, 122, 82)
    s.text(x + 130, TOP + 20, "`ResultStat`", size=11.5, anchor="start", weight="bold")
    for i, row in enumerate(("root · path", "name · type", "size · mtime")):
        s.text(x + 130, TOP + 40 + i * 17, row, size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, TOP + 108, "`text`, `Range: bytes=0-3`", size=11.5, anchor="start")
    for i, b in enumerate(("a", "b", "c", "C3", "A9", ".", "d", "e", "f")):
        cx = x + 4 + i * 26
        cell(s, cx, TOP + 124, 26, 26, "done" if i < 3 else ("work" if i in (3, 4) else "surface"))
        s.text(cx + 13, TOP + 142, f"`{b}`", size=10.5)
    s.line(x + 4, TOP + 118, x + 108, TOP + 118, dashed=True, colour=t.dim, passes=1)
    s.line(x + 82, TOP + 120, x + 82, TOP + 156, colour=t.accent, passes=1, width=2)
    s.text(x + 4, TOP + 172, "206 · `bytes 0-2/9`, then from 3", size=11.5, anchor="start")
    s.text(x + 4, TOP + 192, "`é` is never cut in two", size=11.5, anchor="start", colour=t.dim)
    s.step(x + w / 2, CAP, 2, "stat and text reads", size=18)
    lines(s, x, CAP + 30, ("`stat`: the listing's own entry",
                           "tail 64 KiB, `?tail=` or a Range, 1 MiB",
                           "one reader with the Job files",
                           "CORP `same-origin` on file routes"))

    # 3 -- P3-fu85b: image mode of the raw route -------------------------------------------------
    x, w = COLS[2]
    s.text(x, HEAD, "P3-fu85b · PR 185", size=14, anchor="start", weight="bold")
    picture(s, x + 2, TOP + 14, 70, 54)
    s.text(x + 37, TOP + 86, "`?as=image`", size=11)
    s.arrow(x + 76, TOP + 28, x + 112, TOP + 18)
    s.arrow(x + 76, TOP + 56, x + 112, TOP + 70)
    s.tick(x + 124, TOP + 12, size=5.5)
    s.text(x + 136, TOP + 10, "dest `image`", size=11.5, anchor="start")
    s.text(x + 136, TOP + 27, "inline, CSP `sandbox`", size=11.5, anchor="start", colour=t.dim)
    download(s, x + 124, TOP + 70, 6)
    s.text(x + 136, TOP + 68, "a navigation", size=11.5, anchor="start")
    s.text(x + 136, TOP + 85, "an attachment", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, TOP + 120, "one opening: size, inode, 1st chunk", size=11.5, anchor="start")
    for i in range(6):
        fill = "work" if i == 0 else ("problem" if i == 4 else "surface")
        cell(s, x + 2 + i * 38, TOP + 132, 36, 24, fill)
        if 0 < i < 4:
            s.tick(x + 20 + i * 38, TOP + 144, size=4.5)
    s.text(x + 20, TOP + 149, "1st", size=11)
    s.cross(x + 20 + 4 * 38, TOP + 144, size=6)
    s.text(x + 2, TOP + 176, "same `st_dev`, `st_ino` each chunk", size=11.5, anchor="start",
           colour=t.dim)
    s.text(x + 2, TOP + 194, "replaced: `Replaced`, body aborted", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + w / 2, CAP, 3, "image mode, raw route", size=18)
    lines(s, x, CAP + 30, ("inline only for `Sec-Fetch-Dest: image`",
                           "the name, its signature, 50 MP",
                           "20 MiB, an SVG 5 MiB",
                           "`Vary: Sec-Fetch-Dest` on every answer"))

    # 4 -- P3-fu85c: the file preview page -------------------------------------------------------
    x, w = COLS[3]
    s.text(x, HEAD, "P3-fu85c · PR 186", size=14, anchor="start", weight="bold")
    s.browser(x + 2, TOP, 296, 212, url="/runs/<id>/results/file")
    s.text(x + 14, TOP + 50, "`logs/big.log`", size=13, anchor="start", weight="bold")
    cell(s, x + 196, TOP + 36, 42, 22, "input")
    s.text(x + 217, TOP + 51, "Start", size=11.5)
    cell(s, x + 240, TOP + 36, 42, 22)
    s.text(x + 261, TOP + 51, "End", size=11.5)
    s.text(x + 14, TOP + 74, "Search covers the 64 KiB shown", size=11.5, anchor="start", colour=t.dim)
    for i, ln in enumerate(("INFO start", "INFO step 1", "WARN slow", "INFO step 2")):
        y = TOP + 96 + i * 17
        s.text(x + 30, y, str(i + 1), size=11, anchor="end", colour=t.dim)
        s.text(x + 40, y, f"`{ln}`", size=10.5, anchor="start")
    s.text(x + 40, TOP + 166, "… cut at 64 KiB", size=11.5, anchor="start", colour=t.dim)
    s.button(x + 14, TOP + 176, 96, "Load more", fill="neutral", h=26)
    s.text(x + 120, TOP + 194, "focus stays, `aria-busy`", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 312, TOP + 14, "one viewer by kind", size=12, anchor="start")
    kinds = (("Text", "surface"), ("JSON", "surface"), ("Table", "surface"), ("Image", "input"),
             ("PDF", "neutral"), ("Binary", "neutral"))
    for i, (k, fill) in enumerate(kinds):
        cell(s, x + 312 + (i % 2) * 58, TOP + 26 + (i // 2) * 30, 54, 24, fill)
        s.text(x + 339 + (i % 2) * 58, TOP + 43 + (i // 2) * 30, k, size=11.5)
    s.text(x + 312, TOP + 134, "PDF, binary:", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 312, TOP + 151, "Download only", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 312, TOP + 176, "`stat` first,", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 312, TOP + 193, "then one read", size=11.5, anchor="start", colour=t.dim)
    s.step(x + w / 2, CAP, 4, "the file preview page", size=18)
    lines(s, x, CAP + 30, ("whole up to 64 KiB, else Start or End, then Load more",
                           "caps: 1 MiB of text, 20,000 lines of 10,000 characters",
                           "a 2 MiB formatted JSON, 500 rows and 50 columns",
                           "Playwright: a hostile SVG in the `<img>` runs nothing"))

    # 5 -- P3-fu85d: the results explorer --------------------------------------------------------
    x, w = COLS[4]
    s.text(x, HEAD, "P3-fu85d · PR 188", size=14, anchor="start", weight="bold")
    cell(s, x + 2, TOP, 242, 172)
    s.text(x + 12, TOP + 20, "Results · 1 folder, 4 files", size=12, anchor="start", weight="bold")
    cell(s, x + 12, TOP + 30, 222, 22)
    s.text(x + 20, TOP + 46, "Filter this folder", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 12, TOP + 72, "Name", size=11.5, anchor="start", weight="bold")
    s.poly([(x + 52, TOP + 70), (x + 60, TOP + 70), (x + 56, TOP + 63)], fill="none", amount=0.1,
           width=1.2)
    s.text(x + 130, TOP + 72, "Kind", size=11.5, anchor="start", weight="bold")
    rows = (("`fastqc`", "Folder", False), ("`S01_fastqc.html`", "HTML report", True),
            ("`versions.yml`", "Text", True))
    for i, (name, kind, file) in enumerate(rows):
        y = TOP + 80 + i * 28
        s.line(x + 10, y, x + 236, y, colour=t.muted, passes=1, amount=0.3, width=1.0)
        s.text(x + 12, y + 19, name, size=10.5, anchor="start")
        cell(s, x + 128, y + 5, 78, 18, "neutral" if not file else "input")
        s.text(x + 167, y + 18, kind, size=10.5)
        if file:
            download(s, x + 224, y + 13, 5)
    s.text(x + 2, TOP + 192, "URL keeps `&sort=` `&q=` `&focus=`", size=11.5, anchor="start")
    s.step(x + w / 2, CAP, 5, "the results explorer", size=18)
    lines(s, x, CAP + 30, ("sort buttons with `aria-sort`",
                           "a name opens its preview",
                           "`&task=` `&attempt=`: the sheet",
                           "reopens, else a line says so"))

    # 6 -- P3-fu85e: a task's work directory -----------------------------------------------------
    x, w = COLS[5]
    s.text(x, HEAD, "P3-fu85e · PR 189", size=14, anchor="start", weight="bold")
    s.button(x + 2, TOP + 2, 186, "Browse work directory", fill="neutral", h=28)
    s.text(x + 196, TOP + 22, "sheet", size=11.5, anchor="start", colour=t.dim)
    s.arrow(x + 40, TOP + 34, x + 40, TOP + 52)
    s.folder(x + 2, TOP + 54, 76, 46, fill="input", label="work")
    entries = (("`counts.tsv`", True), ("`qc`", True), ("`.command.env`", False),
               ("`.command.run`", False), ("`x` to `.command.env`", False))
    for i, (name, ok) in enumerate(entries):
        y = TOP + 54 + i * 25
        if ok:
            s.tick(x + 96, y + 8, size=5)
        else:
            s.cross(x + 96, y + 8, size=5)
        s.text(x + 108, y + 13, name, size=11, anchor="start", colour=t.ink if ok else t.dim)
    s.text(x + 120, TOP + 182, "`link_outside`", size=11, anchor="start", colour=t.dim)
    for i, part in enumerate(("`/tasks/<id>/`", "`attempts/<n>/`", "`workdir`")):
        s.text(x + 2, TOP + 122 + i * 17, part, size=11, anchor="start")
    s.text(x + 2, TOP + 204, "a dot part: hidden, refused 422", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + w / 2, CAP, 6, "a task's work directory", size=18)
    lines(s, x, CAP + 30, ("the results routes on a second root",
                           "explorer and preview take a `WorkRoot`",
                           "HTML: always an attachment",
                           "Snakemake or a terminal run: 404"))

    for (a, aw), (b, _) in zip(COLS[:5], COLS[1:]):
        s.arrow(a + aw + 2, CAP - 30, b - 3, CAP - 30, colour=t.muted)

    # pins and notes: every major, under the step that built its fix ---------------------------
    x, w = COLS[0]
    y = pin(s, x, PIN, "UX-PRE-FU85-01", "R0",
            ("no board showed a preview,", "a sort or the phone list"), "applied: boards first",
            w=w)
    y = note(s, x, y + 10, ("pre-review of the design:", "R0 self-review, not independent:",
                            "security 0/2/7, UX 0/1/9", "R1 independent: security 0/2/9,",
                            "UX 0/5/15 · all applied"), w=w)
    note(s, x, y + 10, ("the 10 design majors are", "pinned under the step that",
                        "built what they asked for"), w=w)

    x, w = COLS[1]
    y = pin(s, x, PIN, "UX-PRE-FU85-R1-01", "R1",
            ("nothing fed the facts line;", "a parent listing stops at 1,000"),
            "applied: the `stat` routes", w=w)
    y = pin(s, x, y + 10, "UX-PRE-FU85-R1-05", "R1",
            ("Load more offsets and", "UTF-8 seams"), "applied: a read ends on a whole char",
            w=w)
    note(s, x, y + 10, ("1 round, approve both · open,", "minor: a CORP test on run logs,",
                        "CR-P3FU85A-01; SEC-P3FU85A-01", "to -03; inbox 128, an OSC may",
                        "hide 4 KiB, assumed"), w=w)

    x, w = COLS[2]
    y = pin(s, x, PIN, "SEC-PRE-FU85-02", "R0",
            ("an SVG served inline renders", "on the app's origin: stored XSS"),
            "applied: inline only in an `<img>`", w=w)
    y = pin(s, x, y + 10, "UX-PRE-FU85-R1-02", "R1",
            ("415 or 422 for a wrong image;", "an `<img>` cannot see a status"),
            "applied: 422, one error state", w=w)
    note(s, x, y + 10, ("1 round, approve both · open,", "minor: CR-P3FU85B-01, `Vary` on",
                        "problems; inbox 129: a GIF's", "first frame, a size of 0, a",
                        "reused inode, SEC-P3FU85B-01 to -03"), w=w)

    x, w = COLS[3]
    pw = (w - 10) / 2
    col = (x, x + pw + 10)
    y0 = pin(s, col[0], PIN, "SEC-PRE-FU85-R1-02", "R1",
             ("byte caps bound neither", "the DOM nor the CPU"),
             "applied: line, JSON, row caps", w=pw)
    y1 = pin(s, col[1], PIN, "UX-PRE-FU85-R1-04", "R1",
             ("`LogViewer` as it was fits", "logs, not files"),
             "applied: `start`, `levels`, `wrap`", w=pw)
    y0 = pin(s, col[0], y0 + 10, "CR-P3FU85C-01", "r1",
             ("Load more did not stop at", "the 20,000-line cap"), "fixed in 8ef254fb", w=pw)
    y1 = pin(s, col[1], y1 + 10, "CR-P3FU85C-02", "r1",
             ("a Load more in flight landed", "after End, Start or Reload"),
             "fixed in 8ef254fb: aborted", w=pw)
    y0 = pin(s, col[0], y0 + 10, "CR-P3FU85C-03", "r1",
             ("Mantine `loading` sets", "`disabled`: focus is lost"),
             "fixed in 8ef254fb: `aria-busy`", w=pw)
    y1 = pin(s, col[1], y1 + 10, "SEC-P3FU85C-01", "r1",
             ("the SVG test navigated without", "loading it in an `<img>` first"),
             "fixed in 8ef254fb", w=pw)
    y0 = pin(s, col[0], y0 + 10, "CR-P3FU85C-R3-06", "r3",
             ("the cap line took focus on", "the first read and after End"),
             "fixed in 35f4e6f2", w=pw)
    y1 = pin(s, col[1], y1 + 10, "CR-P3FU85C-R3-07", "r3",
             ("search open state set once,", "lost on a breakpoint change"),
             "fixed in 35f4e6f2", w=pw)
    y = note(s, col[0], max(y0, y1) + 10, ("4 rounds · code-reviewer:",
                                           "changes, approve, changes,",
                                           "approve · security: changes,",
                                           "then approve three times",
                                           "open: FU-P3-94, 95; inbox 130"), w=pw)
    note(s, col[1], max(y0, y1) + 10, ("not run: Firefox and WebKit", "for `preview.spec.ts`;",
                                       "CI has Chromium only"), w=pw, warn=True)

    x, w = COLS[4]
    y = pin(s, x, PIN, "UX-PRE-FU85-R1-03", "R1",
            ("no way back to the task sheet;", "work pages not specified"),
            "applied: `&task=` `&attempt=`", w=w)
    y = note(s, x, y + 10, ("2 rounds, approve both · open:", "FU-P3-96, past 2,000 tasks the",
                            "sheet is not found; FU-P3-97,", "the other minors; inbox 131"), w=w)
    note(s, x, y + 10, ("not done: the Playwright", "smoke on the explorer,", "CR-P3FU85D-05"),
         w=w, warn=True)

    x, w = COLS[5]
    y = pin(s, x, PIN, "SEC-PRE-FU85-01", "R0",
            ("a work dir would list and serve", "`.command.env`, `.command.run`"),
            "applied: a dot part is refused", w=w)
    y = pin(s, x, y + 10, "SEC-PRE-FU85-R1-01", "R1",
            ("staged inputs served, while", "req. 13 listed them unserved"),
            "applied: req. 13 note amended", w=w)
    y = note(s, x, y + 10, ("2 rounds, approve both · open:", "FU-P3-98; inbox 132, the card",
                            "heading keeps the counts"), w=w)
    note(s, x, y + 10, ("not done: a real Nextflow work", "dir on a cluster; Playwright on",
                        "the work-directory pages"), w=w, warn=True)

    # == P3-fu90, the batch simplifier, the tests ================================================
    band(s, LOW - 22, "also merged: P3-fu90 · then batch simplify, before and after · 2 commits, "
         "7 files, -61 +54 · re-review: approve both")

    # P3-fu90: a rule in no rule graph
    x, y = 50, LOW + 8
    s.text(x, y + 10, "P3-fu90 · PR 182 · pipeline order with a rule", size=13.5, anchor="start",
           weight="bold")
    s.text(x, y + 28, "in no rule graph, `api/runs_read.py`", size=13.5, anchor="start",
           weight="bold")
    orders = (("one graph, no `align`", ("make_reads", "split", "merge", "report", "all", "align",
                                         "unused")),
              ("a later graph places it", ("make_reads", "split", "align", "merge", "report", "all",
                                           "unused")))
    for k, (title, order) in enumerate(orders):
        ox = x + k * 240
        s.text(ox, y + 54, title, size=12.5, anchor="start", colour=t.dim)
        for i, rule in enumerate(order):
            ry = y + 64 + i * 25
            fill = "work" if rule == "align" else ("neutral" if rule == "unused" else "input")
            cell(s, ox + 20, ry, 116, 20, fill)
            s.text(ox + 12, ry + 15, str(i), size=11.5, anchor="end", colour=t.dim)
            s.text(ox + 78, ry + 15, f"`{rule}`", size=10.5)
        if k == 0:
            s.arrow(ox + 150, y + 140, ox + 214, y + 140, colour=t.dim)
            s.text(ox + 182, y + 130, "merged", size=11.5, colour=t.dim)
    s.cross(x + 8, y + 252, size=6)
    s.text(x + 22, y + 257, "before P3-fu90: `align` was listed first, DW-P3B08-01", size=12.5,
           anchor="start")
    s.text(x, y + 284, "`_rulegraphs`: every graph, oldest first; their links merged,", size=12.5,
           anchor="start")
    s.text(x, y + 304, "graph rules sorted, the rules in no graph after them", size=12.5,
           anchor="start", colour=t.dim)
    s.text(x, y + 330, "1 round, approve both · SEC-P3FU90-01 minor: every graph", size=12.5,
           anchor="start")
    s.text(x, y + 350, "read on each request, FU-P3-92 · inbox 126, assumed", size=12.5,
           anchor="start", colour=t.dim)

    # the batch simplifier: one copy where there were two or four
    x = 560
    s.text(x, y + 10, "batch simplify, one copy each", size=13.5, anchor="start", weight="bold")
    s.text(x, y + 36, "before", size=12.5, anchor="start", colour=t.dim)
    for i, fn in enumerate(("`results.py`", "`workdir.py`")):
        px = x + i * 122
        s.page(px, y + 46, 52, 66, fill="surface", lines=0)
        cell(s, px + 6, y + 64, 38, 14, "problem")
        cell(s, px + 6, y + 84, 38, 14, "problem")
        s.text(px + 26, y + 128, fn, size=11)
    s.text(x + 60, y + 76, "entries", size=11, anchor="start", colour=t.dim)
    s.text(x + 60, y + 96, "stat body", size=11, anchor="start", colour=t.dim)
    s.text(x + 182, y + 76, "the same", size=11, anchor="start", colour=t.dim)
    s.text(x + 182, y + 96, "twice", size=11, anchor="start", colour=t.dim)
    s.arrow(x + 254, y + 80, x + 284, y + 80)
    s.text(x + 300, y + 36, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 300, y + 46, 52, 66, fill="done", lines=0)
    cell(s, x + 306, y + 64, 38, 14, "done")
    cell(s, x + 306, y + 84, 38, 14, "done")
    s.text(x + 326, y + 128, "`results.py`", size=11)
    s.text(x + 362, y + 76, "`entry_dicts`", size=11, anchor="start")
    s.text(x + 362, y + 96, "`stat_response`", size=11, anchor="start")
    s.text(x + 362, y + 116, "`workdir.py` imports", size=11, anchor="start", colour=t.dim)
    web = (("`ATTACHMENT_CSP`", "`TEXT_CSP`, the same string"),
           ("the 503 words, 4 copies", "`OFFLINE` in `explorer.ts`"),
           ("`join`, 2 copies", "one, in `explorer.ts`"),
           ("`.sp-vh`", "the shell's `.sp-sr`"))
    for i, (old, new) in enumerate(web):
        ry = y + 160 + i * 22
        s.text(x, ry, old, size=11.5, anchor="start", colour=t.dim)
        s.line(x, ry - 4, x + 9 + len(old.replace("`", "")) * 6.3, ry - 4, colour=t.accent,
               passes=1, width=1.4)
        s.text(x + 200, ry, new, size=11.5, anchor="start")
    # the diff to scale, per file
    k = 2.4  # px per line
    s.text(x, y + 262, f"lines per file, to scale, {k} px a line", size=12.5, anchor="start")
    numstat = (("api/results.py", 35, 20), ("api/workdir.py", 3, 17), ("FilePreview.tsx", 3, 8),
               ("ResultsBrowser.tsx", 4, 5), ("TaskFiles.tsx", 3, 3), ("explorer.ts", 6, 0),
               ("runs.css", 0, 8))
    mid = x + 186
    for i, (name, add, rem) in enumerate(numstat):
        ry = y + 274 + i * 18
        s.text(x + 128, ry + 12, f"`{name}`", size=10.5, anchor="end", colour=t.dim)
        if rem:
            bar(s, mid - rem * k, ry, rem * k, 13, "problem")
        if add:
            bar(s, mid + 2, ry, add * k, 13, "done")
        s.text(mid + 8 + add * k, ry + 12, f"+{add} -{rem}", size=10.5, anchor="start")
    s.line(mid + 1, y + 270, mid + 1, y + 404, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y + 420, "removed", size=11, anchor="end", colour=t.dim)
    s.text(mid + 8, y + 420, "added", size=11, anchor="start", colour=t.dim)

    # re-review and what was left
    x2 = 1040
    s.text(x2, y + 10, "re-review: approve, approve", size=13.5, anchor="start", weight="bold")
    lines(s, x2, y + 36, ("CR-P3B09-01 minor: the shared helpers",
                          "take `Any`, mypy no longer checks `Entry`",
                          "CR-P3B09-02 minor: `_file_rel` moved",
                          "for nothing, a bigger diff"), size=12)
    lines(s, x2, y + 124, ("SEC-P3B09-01 minor: images and",
                           "attachments now follow the text CSP;",
                           "same string today, test_results.py:899"), size=12)
    lines(s, x2, y + 196, ("left alone: `!whole` in `stoppedByMore`,",
                           "the ReportViewer cycle, the Kind header,",
                           "the copied back link and Retry block,",
                           "`readResultText`'s refusal parsing"), size=12)

    # tests, to scale
    x = 1320
    k = 0.25  # px per test
    s.text(x, y + 10, "tests, to scale", size=13.5, anchor="start", weight="bold")
    s.text(x + 128, y + 10, f"{k} px per test", size=12.5, anchor="start", colour=t.dim)
    rows_t = (("pytest, before", 1189, "1189 passed", "bar_green", False),
              ("pytest, after", 1189, "1189 passed", "bar_green", False),
              ("vitest, before", 432, "not run", "bar_blue", True),
              ("vitest, after", 432, "432 passed", "bar_blue", False))
    for i, (label, n, txt, fill, dashed) in enumerate(rows_t):
        by = y + 28 + i * 32
        s.text(x, by + 16, label, size=12.5, anchor="start")
        bar(s, x + 104, by, n * k, 20, fill, dashed=dashed)
        s.text(x + 112 + n * k, by + 16, txt, size=12.5, anchor="start",
               colour=t.dim if dashed else t.ink)
    s.text(x + 104, y + 172, "pytest: 1 skipped, both runs", size=12, anchor="start", colour=t.dim)
    s.warning(x + 8, y + 198, size=8)
    s.text(x + 24, y + 203, "no `node_modules` before the edits:", size=12.5, anchor="start")
    s.text(x + 24, y + 223, "`npm ci`, then vitest and `tsc`", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x + 24, y + 243, "on the simplified tree only", size=12.5, anchor="start", colour=t.dim)
    s.tick(x + 8, y + 270, size=6)
    s.text(x + 24, y + 275, "ruff, format, mypy, lint-imports,", size=12.5, anchor="start")
    s.text(x + 24, y + 295, "`uv lock`: the same before and after", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x + 24, y + 315, "`tsc` clean after", size=12.5, anchor="start", colour=t.dim)

    s.text(50, H - 76, "pins: every major of the batch, all closed; no blocker · R0, R1: rounds "
           "of the design pre-review · r1, r3: code review rounds of P3-fu85c", size=13.5,
           anchor="start", colour=t.dim)
    s.prefix_key(50, H - 50, ("CR", "SEC", "UX"))
    s.text(W - 50, H - 18, "source: api/results.py, api/workdir.py, files/images.py, "
           "files/results.py, api/runs_read.py, web/src/runs at 73ca47a4 · review records "
           "P3-fu90, P3-fu85-spec, P3-fu85a to P3-fu85e", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b09-file-explorer")
