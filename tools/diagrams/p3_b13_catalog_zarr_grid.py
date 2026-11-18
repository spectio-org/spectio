#!/usr/bin/env python3
"""The catalog picker on Launch, the run detail pass, the OME-Zarr viewer through a capped store, run
resources designed, and AG Grid: batch P3-B13 (steps P3-fu87e, P3-fu88a, P3-fu102g, P3-fu110-spec,
P3-fu101a, wave W5), 2026-11-10.

Writes docs/assets/diagrams/p3-b13-catalog-zarr-grid_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B13 at baaee4e8 (PRs 231, 233, 234, 235 and 236,
squash-merged into autopilot/integration between b0c783d2 and baaee4e8; the batch code-simplifier
changed nothing). Steps are numbered in merge order:
- 1, P3-fu87e, PR 231: web/src/launch/CatalogPicker.tsx (`CatalogPicker`: NativeSelect "From your
  catalog", None first, "Manage catalog", "Clear and start empty", the line "From the catalog:
  <name> · profile <p> · parameters from <file>"; `Sheet`: a Modal, a bottom Drawer at 100% on the
  phone; `SaveToCatalog`: "Save to catalog", or "In your catalog as <name>" with Edit);
  LaunchPage.tsx (`choose` fills location, revision and engine, Load inspects; `inspect(...,
  from?.params_file)`; `fromName` kept, the entry read from `catalog.items`, CR-P3FU87E-01;
  `paramsFile` state, CR-P3FU87E-02; values the form does not place listed and not sent;
  code_loading items as "Warning, not a blocker"); the example entry is LaunchCatalog.test.tsx:17-18
  (rnaseq-test, nf-core/rnaseq 3.27.0, profile test, conf/test.yaml); record
  docs/reviews/code/P3-fu87e.md (2 majors fixed, 3 minors open);
- 2, P3-fu88a, PR 233: RunDetailPage.tsx (`LogTail`: a click on the last lines opens the full log
  unless `window.getSelection()` holds text, CR-P3FU88A-02; button "Open the full <log>"; Logs with
  `from=summary` shows "Back to Summary", focus back to the opener); RunState.tsx `CheckpointMark`
  (signpost icon and the word, was an `sp-chip`); FilePreview.tsx `html` case (Navigate to
  /runs/$id/report; `view=text` shows the source; over `REPORT_MAX` 1 GiB: Download);
  ReportViewer.tsx "Show the source as text"; record P3-fu88a.md (1 major fixed, 4 minors open);
- 3, P3-fu102g, PR 234: web/src/runs/imaging/zarr.ts (`ZarrStore.get`, `fetchKey` one request per
  key with as=zarr, META_MAX 1 MiB, CHUNK_READ_MAX 16 MiB, CHUNK_VALUES_MAX 16 M, SIDE_MAX 2^31 - 1,
  LEVELS_MAX 32, IFDS_MAX 10,000 planes, COMPRESSORS zlib and gzip, `.zmetadata` never asked,
  `checkChunk` against the decoded size, `openZarr` rebuilds `.zattrs`, `.zgroup`, `.zarray`);
  client.ts BUDGET 2000 requests and 256 MiB, IN_FLIGHT 3; jitless.ts `config({ jitless: true })`;
  viv.ts `openZarrPixels`, `loadOmeZarrFromStore`; FilePreview.tsx `OmeZarrView` (phone and no
  WebGL 2: a note with Browse folder); tests/e2e/seed_stages.py `cells.ome.zarr` (a raw level and a
  zlib level); record P3-fu102g.md (blocker CR-P3FU102G-01 with SEC-P3FU102G-01, majors
  SEC-P3FU102G-02, CR-P3FU102G-02, CR-P3FU102G-03; 4 minors open; CSP unchanged);
- 4, P3-fu110-spec, PR 235: design only, docs/specs/api-and-data-model.md 5.7 (`default_resources`
  cpus 1 to 256, mem_mib up to 4,194,304, time_min up to 43,200; `config_file` under the home from
  the password database or the pipeline's directory, read at launch, at most 256 KiB, kept 0600 as
  .spectio/extra.config or extra.yaml or extra.json with its SHA-256; `-c .spectio/extra.config,
  .spectio/spectio.config`; `--configfile <extra> .spectio/params.json`; `__use_yte__` refused;
  payload text set to null at the sink's ack); record P3-fu110-spec.md (2 majors fixed; minors
  carried to FU-P3-110a to 110d; open PRAGMA secure_delete); inbox 151;
- 5, P3-fu101a, PR 236: web/src/runs/DataGrid.tsx (ag-grid-community and ag-grid-react 36.2.0,
  five modules, `themeQuartz.withoutPart("iconSet")` with the app tokens, inline SVG sort arrows,
  `ensureDomOrder`); RunsPage.tsx (COLUMNS Run, State, Workflow, Tasks, Started, Duration;
  `openOnEnter`: Enter on the Run cell clicks its link, CR-P3FU101A-01; Started dropped below
  1100 px; the phone keeps its cards); FilePreview.tsx `TableView` (a text filter per column,
  `compareText` from gridText.ts, fixed height past 15 rows); 7 lockfile packages added; record
  P3-fu101a.md (1 blocker fixed, 4 minors and 2 simplify open);
- lines per step: `git show --numstat <merge> -- . ':!docs' ':!.autopilot'`, split into tests
  (`*.test.ts(x)`, `testing.tsx`, `tests/e2e/*`, `imaging/fixtures/`), lockfile and notices
  (`package.json`, `package-lock.json`, `THIRD_PARTY_NOTICES.txt`, the wheel manifest) and the rest;
  P3-fu110-spec has no line outside docs (+153 -1 in docs);
- tests: `npx vitest run --reporter=json` at b0c783d2 (589 tests in 47 files) and at baaee4e8 (643
  in 50 files), run 2026-11-10 for this figure; the per-file difference gives the tests per step
  (LaunchCatalog 16; RunDetailPage 4 and FilePreview 3; zarr 23, OmeView 1, jitless 1, viv 1;
  RunsPage 3 and FilePreview 2); in a full parallel run FilePreview.test.tsx and
  SlurmFacts.test.tsx timed out once at both commits and passed alone; e2e cases: one added in
  launch-environment.spec.ts, viewer.spec.ts and preview.spec.ts; the batch simplifier's baseline
  (vitest 643 of 643 in 50 files, `tsc --noEmit` clean; no Python touched, so pytest, ruff, mypy,
  lint-imports and `uv lock --check` not run) and its result, no change.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1940, 1530
COLS = tuple(45 + i * 378 for i in range(5))
CW = 356
ROW = 170  # the step's name
LOW = 1110  # the simplifier and the bars


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 12.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, rows: tuple[str, ...], status: str,
        *, w: float = CW) -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it was closed."""
    h = 32 + 18 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 14, y + 13, size=5.5)
    s.text(x + 27, y + 18, fid, size=11.5, anchor="start", weight="bold")
    s.text(x + w - 8, y + 18, tag, size=11, anchor="end", colour=s.t.accent if "blocker" in tag
           else s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 10, y + 38 + i * 18, row, size=12, anchor="start")
    s.text(x + 10, y + 38 + len(rows) * 18, status, size=12, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = CW,
         warn: bool = False) -> float:
    """A dashed note: the rounds and what is open."""
    h = 12 + 20 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 22 if warn else 0
    if warn:
        s.warning(x + 17, y + 18, size=7.5)
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 23 + i * 20, row, size=12, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def chip(s: Sketch, x: float, y: float, w: float, label: str, fill: str, *, h: float = 20,
         size: float = 10.5) -> None:
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.38, label, size=size)


def ring(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    """Keyboard focus: a dashed ring around the control."""
    s.shade(x - 4, y - 4, w + 8, h + 8, fill="none", opacity=0, colour=s.t.accent, dashed=True)


def picture(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    """An image: a frame and three blobs of colour."""
    cell(s, x, y, w, h, "neutral")
    for cx, cy, r, fill in ((0.3, 0.4, 0.16, "bar_blue"), (0.62, 0.55, 0.2, "bar_green"),
                            (0.45, 0.72, 0.12, "bar_violet")):
        s.circle(x + w * cx, y + h * cy, h * r, fill=fill, width=1.0)


def caret(s: Sketch, cx: float, cy: float) -> None:
    """A select's drop-down mark."""
    s.poly([(cx - 4, cy - 2), (cx + 4, cy - 2), (cx, cy + 3)], fill="none", amount=0.1, width=1.1)


def signpost(s: Sketch, x: float, y: float) -> None:
    """The checkpoint mark's icon: a post and its sign."""
    s.line(x + 5, y, x + 5, y + 16, colour=s.t.ink, passes=1, amount=0.2, width=1.4)
    s.poly([(x, y + 2), (x + 11, y + 2), (x + 14, y + 5), (x + 11, y + 8), (x, y + 8)], fill="none",
           amount=0.1, width=1.1)


def log_lines(s: Sketch, x: float, y: float, w: float, n: int) -> None:
    for i in range(n):
        s.line(x, y + i * 9, x + w * (0.9 - 0.18 * (i % 3)), y + i * 9, colour=s.t.muted, passes=1,
               amount=0.2, width=1.6)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def head(s: Sketch, x: float, y: float, title: str) -> None:
    s.text(x, y, title, size=14, anchor="start", weight="bold")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1313)
    t = theme
    s.heading(50, 58, "P3-B13 · a catalog picker, the run detail pass, OME-Zarr through a capped "
              "store, run resources designed, AG Grid",
              "wave W5 · 5 steps · 2026-11-10 · PRs 231 and 233 to 236 into "
              "`autopilot/integration` · steps numbered in merge order")
    band(s, ROW - 36, "FU-P3-87 the pipeline catalog, step 1 · FU-P3-88 the run detail, step 2 · "
         "FU-P3-102 imaging, step 3 · FU-P3-110 run resources, step 4, design only · "
         "FU-P3-101 tables, step 5")
    top, cap = ROW + 22, ROW + 300
    pin_y = cap + 124

    # 1 -- P3-fu87e: the catalog picker on Launch ---------------------------------------------------
    x = COLS[0]
    head(s, x, ROW, "P3-fu87e · PR 231 · web")
    s.browser(x + 2, top, 236, 150)
    s.text(x + 14, top + 46, "Launch · Pipeline", size=11.5, anchor="start", weight="bold")
    s.text(x + 14, top + 64, "From your catalog", size=10.5, anchor="start", colour=t.dim)
    cell(s, x + 14, top + 70, 150, 22, "input")
    s.text(x + 20, top + 85, "rnaseq-test · Nextflow", size=10.5, anchor="start")
    caret(s, x + 154, top + 81)
    chip(s, x + 170, top + 70, 60, "Manage", "surface", h=22, size=10.5)
    s.text(x + 14, top + 110, "`nf-core/rnaseq` `3.27.0`", size=10, anchor="start", colour=t.dim)
    chip(s, x + 14, top + 118, 44, "Load", "done", h=20, size=10.5)
    s.text(x + 66, top + 133, "profile test", size=10.5, anchor="start", colour=t.dim)
    s.arrow(x + 244, top + 128, x + 272, top + 128)
    s.text(x + 258, top + 116, "inspect", size=10, colour=t.dim)
    s.page(x + 280, top + 92, 64, 78, fill="input", lines=0)
    s.text(x + 312, top + 112, "params", size=10, colour=t.dim)
    for i, fill in enumerate(("done", "done", "neutral", "problem")):
        cell(s, x + 288, top + 120 + i * 11, 48, 8, fill)
    s.text(x + 312, top + 186, "`conf/test.yaml`", size=10)
    s.text(x + 280, top + 18, "an entry fills", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 280, top + 34, "location, revision,", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 280, top + 50, "engine; Load", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 280, top + 66, "inspects it", size=10.5, anchor="start", colour=t.dim)
    legend = (("done", "fills the form"), ("neutral", "no field: listed, not sent"),
              ("problem", "code loading: Warning, not a blocker"))
    for i, (fill, label) in enumerate(legend):
        cell(s, x + 2, top + 164 + i * 19, 22, 12, fill)
        s.text(x + 32, top + 174 + i * 19, label, size=11, anchor="start")
    chip(s, x + 2, top + 228, 110, "Save to catalog", "docs", h=22, size=11)
    s.text(x + 120, top + 243, "or In your catalog as rnaseq-test, Edit", size=10.5,
           anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 1, "the catalog picker on Launch", size=18)
    lines(s, x, cap + 28, ("choosing an entry only fills the form",
                           "Load inspects with the entry's `params_file`",
                           "None and Clear and start empty keep it simple",
                           "Manage catalog, Save to catalog: dialogs,",
                           "full-height sheets on the phone"))
    y = pin(s, x, pin_y, "CR-P3FU87E-01", "r1 major",
            ("the loaded entry was a copy taken at Load,", "stale after an edit or a delete"),
            "fixed: the name kept, the entry read afresh")
    y = pin(s, x, y + 10, "CR-P3FU87E-02", "r1 major",
            ("choosing None dropped the unplaced-values", "line and the code_loading warnings"),
            "fixed: the params report is its own state")
    note(s, x, y + 10, ("2 rounds · CR approve, SEC approve",
                        "fixes test first · 16 tests, 1 e2e case",
                        "3 minors open: focus and phone tests,",
                        "profile note, warnings as read"))

    # 2 -- P3-fu88a: the run detail pass ------------------------------------------------------------
    x = COLS[1]
    head(s, x, ROW, "P3-fu88a · PR 233 · web")
    s.browser(x + 2, top, 160, 116)
    s.text(x + 12, top + 46, "Summary", size=11.5, anchor="start", weight="bold")
    s.text(x + 12, top + 62, "Engine log · last lines", size=10, anchor="start", colour=t.dim)
    cell(s, x + 12, top + 68, 140, 26, "neutral")
    log_lines(s, x + 18, top + 76, 124, 2)
    s.text(x + 12, top + 108, "Open the full engine log", size=10, anchor="start",
           colour=t.accent)
    ring(s, x + 12, top + 98, 124, 12)
    s.arrow(x + 168, top + 56, x + 200, top + 56)
    s.text(x + 184, top + 46, "click", size=10, colour=t.dim)
    s.browser(x + 206, top, 150, 116)
    s.text(x + 216, top + 46, "Logs", size=11.5, anchor="start", weight="bold")
    s.text(x + 216, top + 64, "Back to Summary", size=10.5, anchor="start", colour=t.accent)
    cell(s, x + 216, top + 72, 130, 36, "neutral")
    log_lines(s, x + 222, top + 80, 114, 3)
    s.arc(x + 230, top + 122, x + 80, top + 122, lift=-22, colour=t.accent, dashed=True)
    s.text(x + 156, top + 160, "focus back to the opener", size=10.5, colour=t.dim)
    s.text(x + 2, top + 186, "before", size=11, anchor="start", colour=t.dim)
    chip(s, x + 50, top + 172, 82, "Checkpoint", "work", h=20, size=10.5)
    s.arrow(x + 140, top + 182, x + 162, top + 182)
    signpost(s, x + 172, top + 174)
    s.text(x + 190, top + 187, "Checkpoint", size=10.5, anchor="start")
    s.text(x + 262, top + 187, "lighter", size=10.5, anchor="start", colour=t.dim)
    s.page(x + 2, top + 204, 32, 40, fill="input", lines=2)
    s.text(x + 18, top + 258, "`.html`", size=10)
    s.arrow(x + 40, top + 224, x + 64, top + 224)
    chip(s, x + 70, top + 212, 96, "report viewer", "docs", h=22, size=10.5)
    s.text(x + 176, top + 221, "Show the source as text:", size=10.5, anchor="start")
    s.text(x + 176, top + 237, "`view=text`, over 1 GiB: Download", size=10, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 2, "the run detail pass", size=18)
    lines(s, x, cap + 28, ("the last lines open the full log",
                           "not when a click ends a text selection",
                           "Logs from the Summary: Back to Summary",
                           "the Checkpoint mark: an icon and the word",
                           "HTML in the preview: the report viewer"))
    y = pin(s, x, pin_y, "CR-P3FU88A-01", "r1 major",
            ("FU-P3-104 had 3 more items than Search;", "ui-spec said Search was the only one"),
            "fixed: listed open for FU-P3-88b, ui-spec 4.4.1")
    y = note(s, x, y + 10, ("2 rounds · CR approve, SEC approve",
                            "the selection fix test first · 7 tests",
                            "4 minors open: change note order, boards",
                            "not updated, unknown size in the report gate"))
    note(s, x, y + 10, ("to be validated: the resume sentence",
                        "of ui-spec 5.2, Snakemake 9.27.1",
                        "checkpoint rerun, CR-P3FU88A-04"), warn=True)

    # 3 -- P3-fu102g: OME-Zarr through the capped store ---------------------------------------------
    x = COLS[2]
    head(s, x, ROW, "P3-fu102g · PR 234 · web")
    s.folder(x + 2, top + 4, 124, 128, fill="input")
    for i, key in enumerate(("`.zattrs`", "`.zgroup`", "`0/.zarray`")):
        s.text(x + 14, top + 46 + i * 18, key, size=10, anchor="start")
    for i in range(6):
        cell(s, x + 14 + (i % 3) * 22, top + 98 + (i // 3) * 14, 18, 10, "surface")
    s.text(x + 64, top + 148, "an OME-Zarr folder", size=10.5, colour=t.dim)
    s.arrow(x + 132, top + 60, x + 166, top + 60)
    s.text(x + 149, top + 50, "a key", size=10, colour=t.dim)
    # the store: a funnel with holes
    cx = x + 196
    s.poly([(cx - 26, top + 34), (cx + 26, top + 34), (cx + 8, top + 80), (cx - 8, top + 80)],
           fill="gate", amount=0.8)
    for dx, dy in ((-12, 46), (0, 46), (12, 46), (-5, 60), (5, 60)):
        s.dot(cx + dx, top + dy, 2.2, colour=t.dim)
    s.text(cx, top + 22, "`ZarrStore`", size=10.5)
    s.text(cx, top + 98, "as=zarr", size=10, colour=t.dim)
    s.arrow(x + 226, top + 60, x + 252, top + 60)
    s.browser(x + 256, top + 10, 100, 96)
    picture(s, x + 266, top + 46, 80, 50)
    s.text(x + 306, top + 122, "Viv, WebGL 2", size=10.5, colour=t.dim)
    s.text(x + 136, top + 142, "a view: 2,000 requests,", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 136, top + 158, "256 MiB, 3 in flight", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 176, "chunks, by compressor", size=11, anchor="start")
    ox = x + 2
    for label, w in (("none", 42), ("zlib", 40), ("gzip", 40)):
        chip(s, ox, top + 184, w, label, "done", h=19)
        ox += w + 5
    s.tick(ox + 6, top + 193, size=5)
    ox += 22
    for label, w in (("blosc", 44), ("lz4", 34), ("zstd", 38)):
        chip(s, ox, top + 184, w, label, "problem", h=19)
        ox += w + 5
    s.cross(ox + 6, top + 193, size=6)
    s.text(x + 2, top + 222, "caps before any allocation: C x Z x T up to 10,000,", size=10.5,
           anchor="start", colour=t.dim)
    s.text(x + 2, top + 238, "a side up to 2^31 - 1 px, a chunk up to 16 M values", size=10.5,
           anchor="start", colour=t.dim)
    s.text(x + 2, top + 254, "`.zmetadata` never asked", size=10.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 3, "the OME-Zarr viewer, capped", size=18)
    lines(s, x, cap + 28, ("metadata at most 1 MiB, depth checked, rebuilt",
                           "then only it and the checked chunks served",
                           "each chunk held to its decoded size",
                           "zod jitless: no eval probe under the CSP",
                           "phone, no WebGL 2: a note, Browse folder"))
    y = pin(s, x, pin_y, "CR-P3FU102G-01, SEC-01", "r1 blocker",
            ("Blosc and LZ4 glue runs through `Function`:", "needs `unsafe-eval`, the CSP refuses"),
            "interim: zlib and gzip only, inbox 150")
    y = pin(s, x, y + 8, "SEC-P3FU102G-02", "r1 major",
            ("array sizes uncapped: c = 10^9 froze the tab",),
            "fixed test first: the caps above")
    y = pin(s, x, y + 8, "CR-P3FU102G-02", "r1 major",
            ("three spec items undone, none recorded",),
            "work dir v2 state built, the rest to 102h")
    y = pin(s, x, y + 8, "CR-P3FU102G-03", "r1 major",
            ("zod's `new Function` probe: a CSP report",),
            "fixed: `jitless.ts`, first import of `viv.ts`")
    note(s, x, y + 8, ("2 rounds · CR and SEC: fixes verified",
                       "26 tests, 1 e2e case: zero CSP violations",
                       "4 minors open · CSP unchanged",
                       "Firefox and WebKit not run, inbox 148"), warn=True)

    # 4 -- P3-fu110-spec: run resources and an extra config file, designed --------------------------
    x = COLS[3]
    head(s, x, ROW, "P3-fu110-spec · PR 235 · design")
    s.page(x + 2, top + 4, 140, 150, fill="surface", lines=0)
    s.text(x + 12, top + 26, "Launch, designed", size=11, anchor="start", weight="bold")
    for i, (label, value) in enumerate((("CPUs", "1 to 256"), ("memory", "up to 4 TiB"),
                                        ("time", "up to 30 days"))):
        s.text(x + 12, top + 50 + i * 24, label, size=10.5, anchor="start", colour=t.dim)
        chip(s, x + 58, top + 38 + i * 24, 76, value, "input", h=18, size=10)
    s.text(x + 12, top + 124, "extra config file", size=10.5, anchor="start", colour=t.dim)
    chip(s, x + 12, top + 130, 122, "`/home/u/x.config`", "input", h=18, size=10)
    s.arrow(x + 148, top + 76, x + 176, top + 76)
    s.folder(x + 182, top + 30, 100, 84, fill="input")
    s.page(x + 200, top + 56, 30, 40, fill="docs", lines=2)
    s.lock(x + 248, top + 92, size=10)
    s.text(x + 232, top + 132, "kept 0600", size=10.5, colour=t.dim)
    s.text(x + 232, top + 148, "with its SHA-256", size=10.5, colour=t.dim)
    s.bucket(x + 324, top + 48, 40, 38, fill="neutral")
    s.text(x + 324, top + 50, "DB", size=10, colour=t.dim)
    s.cross(x + 324, top + 70, size=11)
    s.text(x + 324, top + 108, "bytes nulled", size=10, colour=t.dim)
    s.text(x + 324, top + 122, "at the ack", size=10, colour=t.dim)
    s.text(x + 2, top + 178, "the engines get the kept copy, never the user's file", size=11,
           anchor="start")
    s.terminal(x + 2, top + 188, CW - 2, 66, ("-c .spectio/extra.config,.spectio/spectio.config",
                                              "--configfile .spectio/extra.yaml .spectio/params.json"),
               size=10, line_h=16)
    s.step(x + CW / 2, cap, 4, "run resources, designed", size=18)
    lines(s, x, cap + 28, ("api 5.7 new: assumed, inbox 151, nothing built",
                           "a default: a process's own values still win",
                           "roots: home from the password database,",
                           "or the pipeline's directory; no link followed",
                           "a Snakemake file stays data: `__use_yte__` refused"))
    y = pin(s, x, pin_y, "CR-P3FU110-SPEC-01", "r1 major",
            ("Snakemake merges config deeply: a form map", "would overwrite the extra file's keys"),
            "fixed: only the leaf keys the user set")
    y = pin(s, x, y + 10, "SEC-P3FU110-SPEC-01", "r1 major",
            ("file bytes kept in `runner_commands.payload`,", "they may hold credentials"),
            "fixed: set to null at the sink's ack")
    y = note(s, x, y + 10, ("design: no code, tests skipped",
                            "2 rounds · CR approve, SEC approve",
                            "minors carried to FU-P3-110a to 110d",
                            "open: `PRAGMA secure_delete`, in 110a"))
    note(s, x, y + 10, ("next: 110a server, 110b runner,",
                        "110c boards, 110d form; several lines",
                        "to be validated on Nextflow 25.10, 26.10"), warn=True)

    # 5 -- P3-fu101a: AG Grid -----------------------------------------------------------------------
    x = COLS[4]
    head(s, x, ROW, "P3-fu101a · PR 236 · web")
    s.browser(x + 2, top, 236, 130)
    s.text(x + 12, top + 46, "Runs", size=11.5, anchor="start", weight="bold")
    cols = (("Run", 42), ("State", 40), ("Workflow", 52), ("Tasks", 36), ("Duration", 54))
    ox = x + 12
    for label, w in cols:
        cell(s, ox, top + 54, w, 16, "neutral")
        s.text(ox + 4, top + 66, label, size=9, anchor="start", colour=t.dim)
        ox += w
    for r, fill in enumerate(("done", "work", "problem")):
        y = top + 70 + r * 18
        cell(s, x + 12, y, 224, 18, "surface")
        cell(s, x + 12, y, 4, 18, fill)
        s.line(x + 20, y + 9, x + 54, y + 9, colour=s.t.muted, passes=1, amount=0.2, width=1.6)
    ring(s, x + 16, top + 88, 44, 18)
    chip(s, x + 248, top + 84, 44, "Enter", "surface", h=22, size=10.5)
    s.arrow(x + 296, top + 95, x + 320, top + 95)
    s.text(x + 338, top + 82, "the", size=10, colour=t.dim)
    s.text(x + 338, top + 96, "run", size=10, colour=t.dim)
    s.text(x + 248, top + 128, "`/runs/<id>`", size=10, anchor="start")
    s.text(x + 248, top + 30, "no Started", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 248, top + 46, "below 1100 px", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 248, top + 62, "phone: cards", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 154, "a TSV preview", size=11, anchor="start")
    ox = x + 2
    for i in range(3):
        cell(s, ox + i * 80, top + 162, 80, 18, "neutral")
        s.text(ox + i * 80 + 6, top + 175, f"col {i + 1}", size=9.5, anchor="start", colour=t.dim)
        cell(s, ox + i * 80 + 4, top + 182, 72, 14, "input")
    s.text(x + 248, top + 176, "sort: a2", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 248, top + 192, "before a10", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 248, top + 208, "a filter each", size=10.5, anchor="start", colour=t.dim)
    for r in range(2):
        cell(s, x + 2, top + 198 + r * 16, 240, 16, "surface")
    s.text(x + 2, top + 254, "AG Grid in its own chunk, loaded with the first table",
           size=10.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 5, "AG Grid for two tables", size=18)
    lines(s, x, cap + 28, ("ag-grid-community and -react `36.2.0`",
                           "the theme takes the app tokens, light and dark",
                           "no icon set: its data images break `img-src`",
                           "cells are text: no HTML from the data",
                           "7 lockfile packages, none with an install script"))
    y = pin(s, x, pin_y, "CR-P3FU101A-01", "r1 blocker",
            ("AG Grid takes Tab and Enter: a keyboard", "user could not open a run"),
            "fixed in `a3b279da`: Enter on the Run cell")
    note(s, x, y + 10, ("2 rounds · CR approve, SEC approve",
                        "the fix test first · 5 tests, 1 e2e case",
                        "4 minors and 2 simplify open, one",
                        "SEC: `props` spread last, for 101b"))

    for a, b in zip(COLS[:4], COLS[1:]):
        s.arrow(a + CW + 2, cap - 6, b - 3, cap - 6, colour=t.muted)

    # == the batch simplifier, the lines and the tests ==============================================
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: "
         "not needed")
    y0 = LOW + 6

    # the simplifier: nothing changed
    x = 50
    s.text(x, y0 + 10, "`code-simplifier`, web only: no change", size=13.5, anchor="start",
           weight="bold")
    s.text(x, y0 + 36, "before, `baaee4e8`", size=12.5, anchor="start", colour=t.dim)
    s.page(x, y0 + 46, 200, 84, fill="surface", lines=4)
    s.text(x + 228, y0 + 94, "=", size=22, colour=t.dim)
    s.text(x + 262, y0 + 36, "after, `baaee4e8`", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 262, y0 + 46, 200, 84, fill="done", lines=4)
    lines(s, x, y0 + 158, ("-0 +0 · HEAD unchanged, nothing to re-review",
                           "left alone: `where` and `LEVELS_MAX` exported,",
                           "used in their own file only; the WebGL 2 note",
                           "twice in `OmeZarrView`, about one line to save",
                           "simplify findings still open: CR-P3FU102G-06,",
                           "CR-P3FU101A-04 and -05"), size=12)

    # the lines changed per step, to scale
    x = 600
    k = 0.3  # px per line
    s.text(x, y0 + 10, f"lines per step outside docs, to scale, {k} px a line", size=13.5,
           anchor="start", weight="bold")
    sizes = ((1, "P3-fu87e", 413, 341, 0, 19), (2, "P3-fu88a", 107, 94, 0, 40),
             (3, "P3-fu102g", 308, 332, 8, 47), (4, "P3-fu110-spec", 0, 0, 0, 0),
             (5, "P3-fu101a", 188, 118, 249, 112))
    mid = x + 160
    for i, (n, name, code, tests, lock, rem) in enumerate(sizes):
        ry = y0 + 30 + i * 30
        s.text(mid - 44, ry + 13, f"{n} `{name}`", size=11.5, anchor="end", colour=t.dim)
        if rem:
            bar(s, mid - 2 - rem * k, ry, rem * k, 16, "problem")
        if not code:
            s.text(mid + 8, ry + 13, "none: specs only, +153 -1 in docs", size=11.5,
                   anchor="start", colour=t.dim)
            continue
        ox = mid + 2
        for n_, fill in ((code, "done"), (tests, "input"), (lock, "neutral")):
            if n_:
                bar(s, ox, ry, n_ * k, 16, fill)
                ox += n_ * k
        s.text(ox + 6, ry + 13, f"+{code + tests + lock} -{rem}", size=11.5, anchor="start")
    s.line(mid, y0 + 24, mid, y0 + 176, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y0 + 196, "removed", size=11, anchor="end", colour=t.dim)
    for lx, fill, label in ((mid + 8, "done", "code and CSS"), (mid + 126, "input", "tests"),
                            (mid + 196, "neutral", "lockfile, notices, manifests")):
        bar(s, lx, y0 + 186, 18, 12, fill)
        s.text(lx + 24, y0 + 196, label, size=11, anchor="start", colour=t.dim)
    s.text(x, y0 + 228, "vitest cases added, one cell a test", size=12, anchor="start")
    s.task_strip(x, y0 + 240, ((16, "input", "1 · 16"), (7, "input", "2 · 7"),
                               (26, "input", "3 · 26"), (5, "input", "5 · 5")),
                 cell=9, h=16, label_size=11)
    s.text(x, y0 + 300, "plus one Playwright case each in steps 1, 3 and 5 · step 4: none",
           size=11.5, anchor="start", colour=t.dim)

    # the tests, to scale
    x = 1320
    k = 0.3  # px per test
    s.text(x, y0 + 10, f"vitest, to scale, {k} px a test", size=13.5, anchor="start",
           weight="bold")
    runs_t = (("base `b0c783d2`", 589, "bar_grey"), ("head `baaee4e8`", 643, "bar_green"),
              ("after simplify", 643, "bar_green"))
    for i, (label, n, fill) in enumerate(runs_t):
        by = y0 + 28 + i * 28
        s.text(x, by + 15, label, size=12, anchor="start")
        bar(s, x + 130, by, n * k, 19, fill)
        s.text(x + 138 + n * k, by + 15, f"{n}", size=12, anchor="start")
    s.text(x + 130, y0 + 128, "47 files, then 50 · 54 tests added", size=12, anchor="start",
           colour=t.dim)
    s.tick(x + 8, y0 + 154, size=6)
    s.text(x + 24, y0 + 159, "the simplifier's run: 643 of 643, `tsc --noEmit`", size=12,
           anchor="start")
    s.text(x + 24, y0 + 178, "clean; no Python touched, so pytest, ruff,", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 24, y0 + 197, "mypy and `uv lock --check` not run", size=12, anchor="start",
           colour=t.dim)
    s.warning(x + 8, y0 + 222, size=7)
    s.text(x + 24, y0 + 228, "a full parallel run timed out two files once,", size=12,
           anchor="start")
    s.text(x + 24, y0 + 247, "at both commits; each passed alone", size=12, anchor="start",
           colour=t.dim)

    s.text(50, H - 52, "pins: every blocker and major of the batch, each fixed, applied or "
           "recorded as deferred · r1: the first code review round", size=13.5,
           anchor="start", colour=t.dim)
    s.prefix_key(50, H - 28, ("CR", "SEC"))
    s.text(W - 50, H - 12, "source: web/src/launch CatalogPicker.tsx, LaunchPage.tsx · "
           "runs RunDetailPage.tsx, FilePreview.tsx, DataGrid.tsx, RunsPage.tsx · imaging zarr.ts, "
           "jitless.ts · api 5.7 · review records P3-fu87e to P3-fu101a", size=12, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b13-catalog-zarr-grid")
