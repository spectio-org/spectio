#!/usr/bin/env python3
"""The decoder worker, the TIFF flat view, a prompt local cancel, focus, and the catalog design:
batch P3-B12 (steps P3-fu102d2, P3-fu87-spec, P3-fu108a, P3-fu102d3, P3-fu108b, wave W5),
2026-11-10.

Writes docs/assets/diagrams/p3-b12-tiff-cancel-catalog_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B12 at f148e430 (PRs 218 to 222, squash-merged into
autopilot/integration between a8bba4a7 and 9f11c6d9, then the batch code-simplifier's commit
f148e430). Steps are numbered in merge order:
- 1, P3-fu102d2, PR 218: web/src/runs/imaging/pool.ts (WORKERS 2, DECODE_TIMEOUT 10_000, a decode
  past it: the worker terminated and replaced; `destroy()`: timers cleared, jobs refused "the view
  was closed"; geotiff's Pool starts a blob: worker, refused by worker-src 'self');
  decoder.worker.ts (bundled by Vite into /assets/); decode.ts (ALLOWED 1, 5, 7, 8, 32946, 32773;
  old JPEG, LERC, WebImage and the rest refused; `declaredSize` width x height x bytes per pixel;
  `inflate` chunkSize 64 KiB, stops past the size; `lzwLength` counts code by code, only
  `code === size` past the dictionary; `packBitsLength`; `jpegFrames` sampling 1 to 4);
  decode.test.ts "a 64 MiB bomb in a 16 x 16 tile is refused" (under 128 KiB compressed, "decodes
  past the tile's 256 bytes"), 13 tests; record docs/reviews/code/P3-fu102d2.md (blocker
  CR-P3FU102D2-01 with SEC-P3FU102D2-01, majors SEC-P3FU102D2-02 and CR-P3FU102D2-02, fixed in
  6c9204a; round 2 ran decode.test.ts and tsc only; 5 minors open);
- 2, P3-fu87-spec, PR 219: design only, docs/specs/api-and-data-model.md 5.6 (`catalog.toml` next
  to `environments.toml`, `[pipelines.<name>]`, fields name, label, engine, location, revision,
  profile, params_file; 64 KiB and 100 entries; GET, POST, PUT, DELETE /catalog; inspect's
  `params_file` 256 KiB; an entry never reaches POST /runs; saving fetches nothing;
  `spectio.locations`, `spectio.catalog`; one file more through `spectio.envfile`) and ui-spec
  4.7.1; record P3-fu87-spec.md (R1: SEC changes 0/2/5, UX changes 0/4/8, every finding applied;
  majors SEC-PRE-FU87-01, -02, UX-PRE-FU87-01 to -04; no CODE line); mvp-0.0.1 boards to make
  in FU-P3-87c; inbox 147;
- 3, P3-fu108a, PR 220: runner/loop.py (`_starts`: heads start once the whole lease is applied;
  `_start` signals a head cancelled in its own lease; `_report` skips `end_grace_s` 60 when
  `_cancel_asked`); runner/headscript.py (`_ENGINE` "( [ -e cancel ] && exit 143; cmd )" after
  `trap : INT TERM`; a lock subshell ended by a cancel: code 143, not LOCKED 75); runner/local.py
  `cancel(grace_s=60)` SIGTERM then SIGKILL; test_local_launcher.py, 3 tests; record
  P3-fu108a.md (no blocker or major, 7 minors, bash 4.4 to be validated);
- 4, P3-fu102d3, PR 221: web/src/runs/imaging/flat.ts (PLANE_MAX 50_000_000, PHONE_SIDE_MAX 2048,
  `shownLevel`, `checkPlane` before any tile, `percentiles` 0.1 and 99.9 over 4,096 bins, `toRgba`,
  `imageState` TooLarge, Unsupported, Unreadable, Stopped with Reload, 413 "over 1 GiB", 422, else
  "could not be decoded"); FilePreview.tsx `TiffView` (2D canvas, Actual size, "Contrast stretched
  for display", the phone's "too large to show on a phone" with Copy link and Download); 10 tests;
  record P3-fu102d3.md (no blocker or major, 6 distinct open minors: CR-01 and SEC-01 are one,
  DW-P3B12-04; CR-P3FU102D3-02 the simplify one);
- 5, P3-fu108b, PR 222: EnvironmentsPage.tsx (New, Edit and Duplicate focus the h1 once loaded;
  Cancel to the opener "Edit <name>", "Duplicate <from>", "New environment", else the card's
  heading, then the h1); PageHead.tsx h1 tabIndex -1; LaunchPage.tsx `focusField(to, frames = 10)`
  with requestAnimationFrame and scrollIntoView block center, `setTimeout(0)` gone, Engine head
  "Not chosen yet"; 3 tests; record P3-fu108b.md (SEC skipped, 3 minors, login1 retest to be
  validated);
- lines per step: `git show --shortstat <merge> -- . ':!docs' ':!.autopilot'` and the same
  `--numstat` summed over test files; P3-fu87-spec has no line outside docs (+196 -1 in docs);
- tests: the batch simplifier's report (pytest 1429 passed, 4 skipped; vitest 544 of 544; ruff,
  format, mypy, lint-imports, uv lock and tsc clean, before and after); the simplifier
  `git show --numstat f148e430` (+3 -3, flat.ts).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1940, 1670
COLS = tuple(45 + i * 378 for i in range(5))
CW = 356
ROW = 170  # the step's name
LOW = 1250  # the simplifier and the bars


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
    for cx, cy, r, fill in ((0.3, 0.4, 0.16, "bar_blue"), (0.62, 0.55, 0.2, "bar_orange"),
                            (0.45, 0.72, 0.12, "bar_green")):
        s.circle(x + w * cx, y + h * cy, h * r, fill=fill, width=1.0)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def head(s: Sketch, x: float, y: float, title: str) -> None:
    s.text(x, y, title, size=14, anchor="start", weight="bold")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1212)
    t = theme
    s.heading(50, 58, "P3-B12 · a capped decoder, the TIFF flat view, a prompt cancel, focus, "
              "the catalog designed",
              "wave W5 · 5 steps · 2026-11-10 · PRs 218 to 222 into `autopilot/integration` · "
              "steps numbered in merge order")
    band(s, ROW - 36, "FU-P3-102 imaging in the browser, steps 1 and 4 · FU-P3-108 from Thomas's "
         "login1 retest, steps 3 and 5 · FU-P3-87 the pipeline catalog, step 2, design only")
    top, cap = ROW + 22, ROW + 300
    pin_y = cap + 124

    # 1 -- P3-fu102d2: the decoder worker pool ---------------------------------------------------
    x = COLS[0]
    head(s, x, ROW, "P3-fu102d2 · PR 218 · web")
    s.browser(x + 2, top, 124, 96)
    s.text(x + 64, top + 56, "geotiff", size=12)
    s.text(x + 64, top + 78, "`readRasters`", size=11)
    for i in range(2):
        y = top + 4 + i * 50
        s.arrow(x + 132, top + 48, x + 166, y + 20)
        cell(s, x + 172, y, 116, 40, "work")
        s.cog(x + 192, y + 20, 7, fill="work")
        s.text(x + 210, y + 25, f"worker {i + 1}", size=12, anchor="start")
    s.hourglass(x + 312, top + 30, size=8)
    s.text(x + 300, top + 62, "10 s, then", size=11, anchor="start", colour=t.dim)
    s.text(x + 300, top + 78, "replaced", size=11, anchor="start", colour=t.dim)
    s.text(x + 2, top + 122, "the allow-list, by compression", size=11.5, anchor="start")
    ok = (("none", 46), ("LZW", 42), ("JPEG", 46), ("Deflate 8, 32946", 104), ("PackBits", 70))
    ox = x + 2
    for label, w in ok:
        chip(s, ox, top + 132, w, label, "done", h=19)
        ox += w + 5
    s.tick(ox + 10, top + 140, size=5)
    no = (("old JPEG", 70), ("LERC", 46), ("WebImage", 76), ("the rest", 66))
    ox = x + 2
    for label, w in no:
        chip(s, ox, top + 158, w, label, "problem", h=19)
        ox += w + 5
    s.cross(ox + 8, top + 167, size=6)
    s.page(x + 2, top + 194, 40, 50, fill="problem", lines=0)
    s.text(x + 22, top + 226, "bomb", size=10.5)
    s.text(x + 52, top + 210, "64 MiB, under 128 KiB packed", size=11.5, anchor="start")
    s.arrow(x + 52, top + 222, x + 98, top + 222)
    cell(s, x + 104, top + 214, 18, 18, "input")
    s.cross(x + 113, top + 223, size=6)
    s.text(x + 130, top + 228, "stops past the 16 x 16 tile's", size=11.5, anchor="start",
           colour=t.dim)
    s.text(x + 130, top + 244, "256 bytes, in 64 KiB chunks", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 1, "the decoder worker pool", size=18)
    lines(s, x, cap + 28, ("our own worker, bundled into `/assets/`",
                           "`worker-src 'self'`: geotiff's pool used `blob:`",
                           "each decoder held to the tile's declared size",
                           "LZW lengths counted code by code first",
                           "`destroy()`: timers cleared, jobs refused"))
    y = pin(s, x, pin_y, "CR-P3FU102D2-01, SEC-01", "r1 blocker",
            ("the LZW check took any code past the", "dictionary: a cycle, memory exhausted"),
            "fixed in `6c9204a`: only the next code")
    y = pin(s, x, y + 10, "SEC-P3FU102D2-02", "r1 major",
            ("JPEG bounded the output, not the frame", "allocated at SOF, 255 components"),
            "fixed: frame within the tile, sampling 1 to 4")
    y = pin(s, x, y + 10, "CR-P3FU102D2-02", "r1 major",
            ("`destroy()` left timers running, one", "leaked worker per busy slot"),
            "fixed: timers cleared, a fake-timer test")
    note(s, x, y + 10, ("2 rounds · CR approve, SEC approve",
                        "round 2 ran `decode.test.ts` and `tsc` only",
                        "5 minors open, 13 tests added"))

    # 2 -- P3-fu87-spec: the pipeline catalog, designed -------------------------------------------
    x = COLS[1]
    head(s, x, ROW, "P3-fu87-spec · PR 219 · design")
    s.folder(x + 2, top + 4, 150, 104, fill="input")
    s.page(x + 16, top + 28, 50, 66, fill="docs", lines=3)
    s.page(x + 84, top + 28, 50, 66, fill="surface", lines=3)
    s.lock(x + 136, top + 96, size=10)
    s.text(x + 2, top + 128, "`catalog.toml`, new, next to", size=11.5, anchor="start")
    s.text(x + 2, top + 145, "`environments.toml`", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 172, top + 10, "one `pipelines` entry", size=11.5, anchor="start", colour=t.dim)
    fields = (("name", "input"), ("label", "neutral"), ("engine", "input"), ("location", "input"),
              ("revision", "neutral"), ("profile", "neutral"), ("params_file", "neutral"))
    for i, (name, fill) in enumerate(fields):
        chip(s, x + 172, top + 20 + i * 21, 116, f"`{name}`", fill, h=18)
    s.text(x + 296, top + 66, "input:", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 296, top + 80, "required", size=10.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 178, "64 KiB and 100 entries at most", size=11.5, anchor="start",
           colour=t.dim)
    for i, (verb, w) in enumerate((("GET", 42), ("POST", 46), ("PUT", 40), ("DELETE", 60))):
        chip(s, x + 2 + sum((42, 46, 40, 60)[:i]) + i * 5, top + 190, w, verb, "surface", h=20)
    s.text(x + 212, top + 205, "`/catalog`", size=11.5, anchor="start")
    s.text(x + 2, top + 236, "inspect gains `params_file`, 256 KiB", size=11.5, anchor="start")
    s.step(x + CW / 2, cap, 2, "the pipeline catalog, designed", size=18)
    lines(s, x, cap + 28, ("api 5.6 and ui-spec 4.7.1, new; nothing built",
                           "an entry is a shortcut: never in `POST /runs`",
                           "saving fetches nothing; Launch inspects it",
                           "the checks move into `spectio.locations`",
                           "the five file states of `spectio.envfile`"))
    y = pin_y
    for fid, row, status in (
        ("SEC-PRE-FU87-01", "the params file is an import, hidden keys too",
         "applied: every key listed before Launch"),
        ("SEC-PRE-FU87-02", "the core would import the server: a 500",
         "applied: `spectio.locations`, `ValueError`"),
        ("UX-PRE-FU87-01", "Manage catalog left Launch, the form lost",
         "applied: a dialog on Launch"),
        ("UX-PRE-FU87-02", "an arrow key on a closed select, a fetch",
         "applied: choosing fills, Load inspects"),
        ("UX-PRE-FU87-03", "the params prefill was silent on unplaced keys",
         "applied: a listing line"),
        ("UX-PRE-FU87-04", "missing states, a pipeline that is gone",
         "applied: board LiteCatalogStates"),
    ):
        y = pin(s, x, y, fid, "R1 major", (row,), status) + 8
    note(s, x, y + 2, ("no code: no CODE line, no tests",
                       "R1 · SEC changes 0/2/5, UX changes 0/4/8",
                       "boards next, FU-P3-87c · inbox 147",
                       "to be validated: `change` per arrow key"), warn=True)

    # 3 -- P3-fu108a: a local cancel, at once -----------------------------------------------------
    x = COLS[2]
    head(s, x, ROW, "P3-fu108a · PR 220 · runner")
    s.runner(x + 2, top + 22, 96, 50)
    s.text(x + 118, top + 18, "one lease", size=11.5, anchor="start", colour=t.dim)
    chip(s, x + 118, top + 28, 70, "launch", "input", h=22, size=11.5)
    chip(s, x + 194, top + 28, 70, "cancel", "problem", h=22, size=11.5)
    s.text(x + 118, top + 72, "a cancel leased after its launch", size=11, anchor="start",
           colour=t.dim)
    s.text(x + 2, top + 102, "before", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 132, "after", size=11.5, anchor="start", colour=t.dim)
    for k, row in enumerate(((("head starts", "work"), ("marker late", "problem"),
                              ("engine runs", "work")),
                             (("launch kept", "neutral"), ("marker", "problem"),
                              ("start: 143", "done")))):
        y = top + 88 + k * 30
        for i, (label, fill) in enumerate(row):
            chip(s, x + 52 + i * 94, y, 76, label, fill, h=22, size=11)
            if i:
                s.arrow(x + 52 + i * 94 - 16, y + 11, x + 52 + i * 94 - 3, y + 11)
    s.hourglass(x + 340, top + 99, size=6)
    s.tick(x + 342, top + 129, size=6)
    s.terminal(x + 2, top + 148, CW - 2, 50, ("( [ -e cancel ] && exit 143; cmd )",), size=12.5,
               line_h=20)
    k = 2.2  # px per second
    s.text(x + 2, top + 216, "head gone to cancelled, bars to scale", size=11.5, anchor="start")
    bar(s, x + 52, top + 224, 60 * k, 12, "bar_orange")
    s.text(x + 2, top + 235, "before", size=11, anchor="start", colour=t.dim)
    s.text(x + 58 + 60 * k, top + 235, "up to 60 s grace", size=11, anchor="start")
    s.text(x + 2, top + 253, "after", size=11, anchor="start", colour=t.dim)
    bar(s, x + 52, top + 242, 3, 12, "bar_green")
    s.text(x + 62, top + 253, "one last spool read, no grace", size=11, anchor="start")
    s.step(x + CW / 2, cap, 3, "a local cancel, at once", size=18)
    lines(s, x, cap + 28, ("heads start once the whole lease is applied",
                           "the engine in a subshell: no SIGTERM lost",
                           "to `trap :` before the engine started",
                           "a lock subshell a cancel ends: 143, not 75",
                           "ui-spec 4.4 updated · 3 tests added"))
    y = note(s, x, pin_y, ("no blocker, no major",
                           "1 round · CR approve, SEC approve",
                           "7 minors, one accepted: no grace on",
                           "SLURM may drop the last spool events"))
    note(s, x, y + 10, ("to be validated: on bash 4.4, RHEL 8,",
                        "a cancelled engine may report 143,",
                        "CR-P3FU108A-01"), warn=True)

    # 4 -- P3-fu102d3: the TIFF flat view ---------------------------------------------------------
    x = COLS[3]
    head(s, x, ROW, "P3-fu102d3 · PR 221 · web")
    s.page(x + 2, top + 34, 44, 58, fill="input", lines=3)
    s.text(x + 24, top + 110, "`.tif`", size=11)
    s.arrow(x + 50, top + 62, x + 74, top + 62)
    s.browser(x + 78, top, 192, 132)
    picture(s, x + 88, top + 38, 104, 82)
    chip(s, x + 198, top + 38, 64, "Actual size", "surface", h=20, size=10)
    s.text(x + 230, top + 112, "a 2D canvas", size=10.5, colour=t.dim)
    s.phone(x + 284, top + 4, 70, 128)
    picture(s, x + 294, top + 40, 50, 44)
    s.text(x + 319, top + 102, "2,048 px", size=10.5, colour=t.dim)
    for i, (label, w) in enumerate((("walk IFDs", 76), ("caps", 52), ("decoder pool", 98),
                                    ("stretch", 66))):
        px = x + 2 + sum((76, 52, 98, 66)[:i]) + i * 20
        chip(s, px, top + 146, w, label, "work", h=22, size=11)
        if i:
            s.arrow(px - 17, top + 157, px - 3, top + 157)
    s.text(x + 2, top + 188, "the states", size=11.5, anchor="start", colour=t.dim)
    states = (("TooLarge", 66, "problem"), ("Unsupported", 84, "problem"),
              ("Unreadable", 78, "problem"), ("Stopped, Reload", 104, "work"),
              ("not decoded", 84, "problem"), ("413 over 1 GiB", 104, "neutral"),
              ("422", 36, "neutral"))
    ox, oy = x + 2, top + 196
    for label, w, fill in states:
        if ox + w > x + CW:
            ox, oy = x + 2, oy + 25
        chip(s, ox, oy, w, label, fill, h=20)
        ox += w + 5
    s.step(x + CW / 2, cap, 4, "the TIFF flat view", size=18)
    lines(s, x, cap + 28, ("`TiffView`: the first plane on a 2D canvas",
                           "caps before any tile: 50 MP, the allow-list",
                           "not 8-bit: stretched, 0.1 to 99.9 percentile",
                           "phone: the largest level up to 2,048 px",
                           "a side, else too large, with Copy link"))
    y = note(s, x, pin_y, ("no blocker, no major",
                           "1 round · CR approve, SEC approve",
                           "6 minors open: every sample decoded,",
                           "a second pixel copy, the IFDs parsed",
                           "again after the walk · 10 tests added"))
    note(s, x, y + 10, ("until FU-P3-102e: an OME-TIFF shows",
                        "its first IFD; a SubIFD pyramid is",
                        "not seen"))

    # 5 -- P3-fu108b: focus where the user goes ---------------------------------------------------
    x = COLS[4]
    head(s, x, ROW, "P3-fu108b · PR 222 · web")
    s.browser(x + 2, top, 150, 118)
    s.text(x + 12, top + 46, "Environments", size=11.5, anchor="start", weight="bold")
    for i in range(2):
        y = top + 56 + i * 28
        cell(s, x + 12, y, 130, 22, "surface")
        s.line(x + 18, y + 11, x + 70, y + 11, colour=t.muted, passes=1, amount=0.3)
        chip(s, x + 100, y + 3, 36, "Edit", "input", h=16, size=10)
    ring(s, x + 100, top + 59, 36, 16)
    s.arrow(x + 158, top + 50, x + 200, top + 50)
    s.text(x + 179, top + 70, "New,", size=10.5, colour=t.dim)
    s.text(x + 179, top + 84, "Edit", size=10.5, colour=t.dim)
    s.browser(x + 206, top, 150, 118)
    s.text(x + 218, top + 52, "the form's h1", size=12, anchor="start", weight="bold")
    ring(s, x + 216, top + 38, 96, 20)
    for i in range(2):
        s.line(x + 218, top + 74 + i * 12, x + 330, top + 74 + i * 12, colour=t.muted, passes=1,
               amount=0.3)
    chip(s, x + 290, top + 94, 56, "Cancel", "surface", h=18, size=10.5)
    s.arc(x + 292, top + 116, x + 120, top + 82, lift=-26, colour=t.accent, dashed=True)
    s.text(x + 240, top + 146, "Cancel: back to the opener", size=11, colour=t.dim)
    chip(s, x + 2, top + 168, 104, "Before Launch", "docs", h=22, size=11)
    s.arrow(x + 110, top + 179, x + 128, top + 179)
    for i in range(10):
        cell(s, x + 132 + i * 13, top + 172, 10, 14, "work")
    s.arrow(x + 264, top + 179, x + 282, top + 179)
    cell(s, x + 290, top + 168, 62, 22, "surface")
    ring(s, x + 290, top + 168, 62, 22)
    s.text(x + 197, top + 206, "10 frames at most", size=10.5, colour=t.dim)
    s.text(x + 321, top + 206, "centred", size=10.5, colour=t.dim)
    s.text(x + 2, top + 236, "Engine head: Not chosen yet, until an engine", size=11.5,
           anchor="start")
    s.step(x + CW / 2, cap, 5, "focus where the user goes", size=18)
    lines(s, x, cap + 28, ("New, Edit, Duplicate focus the h1 once loaded",
                           "`PageHead` h1 `tabIndex -1`, not in Tab order",
                           "Cancel: `Edit <name>`, `Duplicate <from>`,",
                           "`New environment`, else the card heading",
                           "the `setTimeout(0)` gone · 3 tests added"))
    y = note(s, x, pin_y, ("no blocker, no major",
                           "1 round · CR approve, SEC skipped,",
                           "no sensitive path · 3 minors open"))
    note(s, x, y + 10, ("to be validated: jsdom cannot show",
                        "the folded-group race, a retest on",
                        "login1, CR-P3FU108B-02"), warn=True)

    for a, b in zip(COLS[:4], COLS[1:]):
        s.arrow(a + CW + 2, cap - 6, b - 3, cap - 6, colour=t.muted)

    # == the batch simplifier, the lines and the tests ============================================
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: not "
         "needed")
    y0 = LOW + 6

    # the simplifier: two parameters no caller passed
    x = 50
    s.text(x, y0 + 10, "`f148e430`, `imaging/flat.ts`", size=13.5, anchor="start", weight="bold")
    s.text(x, y0 + 36, "before", size=12.5, anchor="start", colour=t.dim)
    s.page(x, y0 + 46, 250, 84, fill="surface", lines=0)
    chip(s, x + 8, y0 + 62, 228, "`percentiles(values, lo, hi)`", "problem", h=22, size=10.5)
    s.text(x + 10, y0 + 112, "`lo = 0.001`, `hi = 0.999`, never passed", size=11, anchor="start",
           colour=t.dim)
    s.arrow(x + 258, y0 + 88, x + 284, y0 + 88)
    s.text(x + 292, y0 + 36, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 292, y0 + 46, 210, 84, fill="done", lines=0)
    chip(s, x + 300, y0 + 62, 186, "`percentiles(values)`", "done", h=22, size=10.5)
    s.text(x + 302, y0 + 112, "0.001 and 0.999 inline", size=11, anchor="start", colour=t.dim)
    lines(s, x, y0 + 158, ("+3 -3 in 1 file, git numstat · behaviour unchanged",
                           "left alone: CR-P3FU102D3-02, a second pixel copy,",
                           "needs a test change, jsdom has no `ImageData`;",
                           "the race fixes of `loop.py` and `headscript.py`;",
                           "the caps of `decode.ts` and `pool.ts`"), size=12)

    # the lines changed per step, to scale
    x = 640
    k = 0.4  # px per line
    s.text(x, y0 + 10, f"lines per step outside docs, to scale, {k} px a line", size=13.5,
           anchor="start", weight="bold")
    sizes = ((1, "P3-fu102d2", 285, 224, 0), (2, "P3-fu87-spec", 0, 0, 0),
             (3, "P3-fu108a", 63, 68, 13), (4, "P3-fu102d3", 245, 186, 10),
             (5, "P3-fu108b", 32, 37, 19))
    mid = x + 170
    for i, (n, name, code, tests, rem) in enumerate(sizes):
        ry = y0 + 30 + i * 30
        s.text(mid - 14, ry + 13, f"{n} `{name}`", size=11.5, anchor="end", colour=t.dim)
        if rem:
            bar(s, mid - 2 - rem * k, ry, rem * k, 16, "problem")
        if not code:
            s.text(mid + 8, ry + 13, "none: specs only, +196 -1 in docs", size=11.5,
                   anchor="start", colour=t.dim)
            continue
        bar(s, mid + 2, ry, code * k, 16, "done")
        bar(s, mid + 2 + code * k, ry, tests * k, 16, "input")
        s.text(mid + 8 + (code + tests) * k, ry + 13, f"+{code + tests} -{rem}", size=11.5,
               anchor="start")
    s.line(mid, y0 + 24, mid, y0 + 176, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y0 + 196, "removed", size=11, anchor="end", colour=t.dim)
    bar(s, mid + 8, y0 + 186, 18, 12, "done")
    s.text(mid + 32, y0 + 196, "code and config", size=11, anchor="start", colour=t.dim)
    bar(s, mid + 140, y0 + 186, 18, 12, "input")
    s.text(mid + 164, y0 + 196, "tests", size=11, anchor="start", colour=t.dim)
    s.text(x, y0 + 228, "tests added, one cell a test", size=12, anchor="start")
    s.task_strip(x, y0 + 240, ((13, "input", "1 · 13 vitest"), (3, "done", "3 · 3 pytest"),
                               (10, "input", "4 · 10 vitest"), (3, "input", "5 · 3 vitest")),
                 cell=11, h=16, label_size=11)

    # the tests, to scale
    x = 1280
    k = 0.2  # px per test
    s.text(x, y0 + 10, f"the batch's tests, before and after the simplifier, {k} px a test",
           size=13.5, anchor="start", weight="bold")
    runs_t = (("pytest, before", 1429), ("pytest, after", 1429), ("vitest, before", 544),
              ("vitest, after", 544))
    for i, (label, n) in enumerate(runs_t):
        by = y0 + 28 + i * 28
        s.text(x, by + 15, label, size=12, anchor="start")
        bar(s, x + 110, by, n * k, 19, "bar_green")
        s.text(x + 118 + n * k, by + 15, f"{n}", size=12, anchor="start")
    s.text(x + 110, y0 + 156, "pytest 4 skipped in each · vitest 544 of 544", size=12,
           anchor="start", colour=t.dim)
    s.tick(x + 8, y0 + 182, size=6)
    s.text(x + 24, y0 + 187, "ruff, format, mypy, lint-imports, `uv lock`, `tsc`:", size=12,
           anchor="start")
    s.text(x + 24, y0 + 206, "clean before and after", size=12, anchor="start", colour=t.dim)
    s.text(x + 24, y0 + 232, "per step: each PR ran its own suites, step 1's", size=12,
           anchor="start")
    s.text(x + 24, y0 + 251, "round 2 only `decode.test.ts` and `tsc`", size=12, anchor="start",
           colour=t.dim)

    s.text(50, H - 52, "pins: every blocker and major of the batch, all fixed or applied · r1, r2: "
           "code review rounds · R1: the design's independent pre-review", size=13.5,
           anchor="start", colour=t.dim)
    s.prefix_key(50, H - 28, ("CR", "SEC", "UX"))
    s.text(W - 50, H - 12, "source: web/src/runs/imaging decode.ts, pool.ts, flat.ts · "
           "FilePreview.tsx · runner/loop.py, headscript.py · EnvironmentsPage.tsx, LaunchPage.tsx · "
           "api 5.6 · review records P3-fu102d2 to P3-fu108b", size=12, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b12-tiff-cancel-catalog")
