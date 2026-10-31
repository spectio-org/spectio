#!/usr/bin/env python3
"""UI parity C, Launch rows and section icons, the pipeline's logo, the run's Copy menu and logs:
step P3-parC, 2026-10-31.

Writes docs/assets/diagrams/p3-parc-launch-logs_{light,dark}.{svg,png}.

Thomas asked (2026-10-31): one parameter per line instead of a grid, a light icon on every Launch
section, the logos ("je veux les logos, important"), and a way to open and read the logs.

Every fact comes from branch autopilot/P3-parC at 089adc38 (base f6c09fa3):
- eb464008, web/src/launch/LaunchPage.tsx: ParamGrid (SimpleGrid cols base 1, sm 2, lg 3, the help,
  type, format, changed and default in one Mantine description) becomes ParamRows; ParamField's
  inputContainer draws the meta (type, format, "changed", "default <json>") on the name's line, the
  input, then the help; app.css .launch-param is a grid, the meta in column 2 of row 1; the
  accessible description stays "help · meta" (sp-sr), the visible copies aria-hidden;
  FoldSection with icons ICONS.route (Pipeline, now full width above .launch-grid), ICONS.sliders
  (Parameters), ICONS.server (Where it runs), ICONS.fileCode (the preview, .launch-preview-card,
  dark); launchButton in the PageHead action and in .launch-bar; web/src/icons.tsx: the icon paths
  drawn here are read from that file, and the new group icons filter, tag, shield, building,
  signpost, download;
- ae60a735 (R1 CR-P3PARC-01, major): the boolean row, Checkbox inside .launch-param with the meta
  "boolean · default false" plus "changed", the description tied by aria-describedby;
- web/src/shell/EngineMark.tsx: markFor(engine, name), nf-core when name starts "nf-core/", else
  MARKS[engine], else null; PipelineMark at RunsPage.tsx:69 (16) and :298 (20), HomePage.tsx:202
  (22), :235 (20), :255 (18), RunHeader.tsx:155 (the tile, 26), :77 (the Pipeline fact, 18),
  LaunchPage.tsx:338 (the Loaded card, 24, else ICONS.folder); EngineMark stays at RunHeader.tsx:84
  (the Engine fact, 18), LaunchPage.tsx:438 (16) and EngineButtons.tsx:36 (16);
  docs/reviews/inbox.md #91, answer (b) 2026-10-31; the logo images are the bundled byte copies,
  web/src/assets/logos/*.png, drawn on white as the app does;
- web/src/runs/CopyMenu.tsx: role="menu" of native buttons, arrows, Home, End, Escape back to Copy,
  a role="status" line for 4 s, "Copied <what>"; RunHeader.tsx copyItems: "Config (params.json)"
  or "Config (config.yaml)" when params exist, "Run directory" for a driven run, "Run ID";
- web/src/runs/RunDetailPage.tsx: LOGS Head output, Head errors, Engine log; runSearch keeps
  ?tab=logs&source=…; LogsPanel: Reload, "Download last 64 KiB", "Open raw" (logUrl, a new tab),
  the File row from logFile (launch/.spectio/head.err, head.out, .nextflow.log,
  .snakemake/log/ "the newest .log there"), the viewer sp-nowrap, scrolled to its end, level():
  failed, review, ok, progress; the note "open a task in Tasks"; the log lines drawn are the test's
  fixture, RunDetailPage.test.tsx:506-511;
- 4506ab5f (CR-P3PARC-02, R1 and R2 minor): lastSource ref; test RunDetailPage.test.tsx:424;
- packages/spectio-server/src/spectio_server/api/logs.py:27, the raw response headers;
- the review rounds and the checks, from the step's worker, reviewer and simplifier reports:
  R1 CR changes (01 major, 02 to 05 minor, 06 simplify, 07 minor), SEC approve (01, 02 minor);
  R2 CR approve (02 to 04 minor, 05 simplify), SEC approve (01, 02 minor); R3 approve, approve, no finding;
  simplifier 089adc38, whitespace only; pytest 511 passed, vitest 140 of 140, tsc clean.
- 045e3991, the docs commit: R1 CR-P3PARC-07 fixed (inbox #91, rule 1 and the Assumed line marked
  superseded); R2 CR-P3PARC-03 recorded in the ui-spec §4.4 note "UI parity C" (docs/reviews/code/P3-parC.md).
Illustrative, not from a run: the pipeline names lab/chipseq and lab/variants, and the parameters
outdir and skip_trimming with their help lines.
"""

from __future__ import annotations

import base64
import re
from xml.sax.saxutils import escape

from sketch import MONO, REPO_ROOT, Sketch, Theme, main_for

W, H = 1600, 2235
S1, S2, S3, S4 = 150, 820, 1250, 1910  # the four sections' title lines

# The app's own icon paths, 24 x 24, read from the source so the figure draws what the screen draws.
_ICONS = dict(re.findall(r'^\s+(\w+): "([^"]+)",', (REPO_ROOT / "web/src/icons.tsx").read_text(), re.M))
_LOGOS = {k: base64.b64encode((REPO_ROOT / f"web/src/assets/logos/logo-{k}.png").read_bytes()).decode()
          for k in ("nf-core", "nextflow", "snakemake")}
# theme.ts code-failed, code-review, code-ok, code-progress: the same in both themes
TINT = {"failed": "#F59A9A", "review": "#F5C779", "ok": "#7FD3AA", "progress": "#9CC2FB"}

# (round, CR verdict, CR cells, SEC verdict, SEC cells); a cell: severity letter, fixed on the branch
ROUNDS = (
    ("R1", "changes", (("M", True), ("m", True), ("m", False), ("m", False), ("m", False),
                       ("s", True), ("m", True)), "approve", (("m", False), ("m", False))),
    ("R2", "approve", (("m", True), ("m", False), ("m", False), ("s", False)),
     "approve", (("m", False), ("m", False))),
    ("R3", "approve", (), "approve", ()),
)
SEV = {"M": "problem", "m": "neutral", "s": "docs"}


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, amount: float = 0.3) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=amount)


def stroke(s: Sketch, x1: float, y: float, x2: float, *, width: float = 1.3) -> None:
    """A ruled stroke standing for a line of text."""
    s.line(x1, y, x2, y, colour=s.t.muted, amount=0.3, passes=1, width=width)


def icon(s: Sketch, x: float, y: float, size: float, name: str, *, colour: str | None = None) -> None:
    """One of the app's line icons, top-left at x, y."""
    k = size / 24
    s.raw(f'<path d="{_ICONS[name]}" transform="translate({x:.1f} {y:.1f}) scale({k:.3f})" fill="none" '
          f'stroke="{colour or s.t.ink}" stroke-width="1.6" stroke-linecap="round" '
          f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')


def tile(s: Sketch, x: float, y: float, size: float, name: str, *, dark: bool = False) -> None:
    """A FoldSection's tile: a rounded square with the section's light line icon."""
    fill = "#ffffff1a" if dark else s.t.fill("neutral")
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{size * 0.3:.1f}" '
          f'fill="{fill}" stroke="{s.t.term_ink if dark else s.t.muted}" stroke-width="1"/>')
    pad = size * 0.18
    icon(s, x + pad, y + pad, size - 2 * pad, name, colour=s.t.term_ink if dark else s.t.ink)


def logo(s: Sketch, x: float, y: float, size: float, key: str | None) -> None:
    """A pipeline's mark as the app draws it: the bundled PNG on white, never recoloured."""
    if key is None:
        return
    s.raw(f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" width="{size + 4:.1f}" height="{size + 4:.1f}" rx="4" '
          f'fill="#ffffff" stroke="{s.t.muted}" stroke-width="0.8"/>')
    s.raw(f'<image x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
          f'href="data:image/png;base64,{_LOGOS[key]}"/>')


def code(s: Sketch, x: float, y: float, w: float, rows: tuple[tuple[str, str | None], ...], *,
         size: float = 11.5, step: float = 17, pad: float = 12) -> float:
    """The app's dark code surface; each row (text, tint). Returns its bottom."""
    h = pad + len(rows) * step
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{s.t.term_bg}"/>')
    for i, (text, tint) in enumerate(rows):
        s.raw(f'<text x="{x + 10:.1f}" y="{y + pad + 6 + i * step:.1f}" font-family="{MONO}" '
              f'font-size="{size}" fill="{TINT.get(tint or "", s.t.term_ink)}" xml:space="preserve">'
              f'{escape(text)}</text>')
    return y + h


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start", first: bool = True, step: float = 20) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * step, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 and first else s.t.dim)


def pin(s: Sketch, x: float, y: float, title: str, rows: tuple[str, ...], *, fixed: bool) -> None:
    """A finding pinned where it hits: a tick when fixed on the branch, a dot when left open."""
    if fixed:
        s.tick(x + 7, y - 5, size=7, colour=s.t.good)
    else:
        s.dot(x + 7, y - 5, 4, colour=s.t.dim)
    s.text(x + 22, y, title, size=13.5, anchor="start", colour=s.t.accent if fixed else s.t.ink)
    for i, row in enumerate(rows):
        s.text(x + 22, y + 20 + i * 19, row, size=12.5, anchor="start", colour=s.t.dim)


def section(s: Sketch, y: float, title: str, sub: str, sub_x: float) -> None:
    s.text(50, y, title, size=19, anchor="start", weight="bold")
    s.text(sub_x, y, sub, size=13.5, anchor="start", colour=s.t.dim)


# -- 1 · Launch -------------------------------------------------------------------------------------

def field(s: Sketch, x: float, y: float, w: float) -> None:
    """A field of the old grid: the label, the grey description above the input, the input."""
    stroke(s, x, y, x + w * 0.5, width=1.6)
    stroke(s, x, y + 9, x + w * 0.95, width=1)
    stroke(s, x, y + 16, x + w * 0.7, width=1)
    bar(s, x, y + 22, w, 15, "surface", amount=0.15)


def launch_before(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    s.browser(x, y, w, h, url="/launch")
    s.text(x + 14, y + 52, "Launch a workflow", size=13, anchor="start", weight="bold")
    s.text(x + 14, y + 82, "Pipeline", size=12, anchor="start", weight="bold")
    bar(s, x + 14, y + 92, w - 90, 17, "surface", amount=0.15)
    s.button(x + w - 68, y + 91, 54, "Load", fill="surface", h=19)
    s.text(x + 14, y + 134, "Parameters", size=12, anchor="start", weight="bold")
    cw = (w - 28 - 2 * 12) / 3
    for r in range(3):
        for c in range(3):
            field(s, x + 14 + c * (cw + 12), y + 150 + r * 52, cw)
    s.text(x + 14, y + 324, "Where it runs", size=12, anchor="start", weight="bold")
    for k in range(3):
        stroke(s, x + 14, y + 340 + k * 11, x + 14 + (200, 160, 230)[k], width=1)
    s.cross(x + w - 10, y + 10, size=8)


def param_row(s: Sketch, x: float, y: float, w: float, name: str, *, changed: bool = False,
              check: bool = False) -> None:
    """A Launch row in miniature: the name and its meta on one line, the input, the help."""
    if check:
        bar(s, x, y - 9, 10, 10, "input", amount=0.1)
        s.tick(x + 5, y - 4, size=4, width=1.6)
        s.text(x + 16, y, name, size=11, anchor="start")
    else:
        s.text(x, y, name, size=11, anchor="start")
    if changed:
        s.text(x + w - 60, y, "changed", size=10, anchor="end", colour=s.t.accent)
    stroke(s, x + w - 56, y - 4, x + w, width=1)
    if not check:
        bar(s, x, y + 6, w, 15, "input" if changed else "surface", amount=0.15)
    stroke(s, x, y + (30 if not check else 12), x + w * 0.6, width=1)


def launch_after(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    t = s.t
    s.browser(x, y, w, h, url="/launch")
    s.text(x + 14, y + 52, "Launch a workflow", size=13, anchor="start", weight="bold")
    stroke(s, x + w - 220, y + 50, x + w - 100, width=1)
    s.button(x + w - 88, y + 37, 74, "Launch", fill="done", h=24)
    # the Pipeline card, full width, above the grid
    px, pw = x + 12, w - 24
    bar(s, px, y + 70, pw, 66, "surface", amount=0.2)
    tile(s, px + 8, y + 78, 24, "route")
    s.text(px + 40, y + 95, "Pipeline", size=12.5, anchor="start", weight="bold")
    bar(s, px + 120, y + 84, 200, 15, "surface", amount=0.15)
    bar(s, px + 40, y + 106, pw - 52, 24, "neutral", amount=0.15)
    logo(s, px + 48, y + 110, 16, "nf-core")
    s.text(px + 72, y + 123, "nf-core/rnaseq", size=11.5, anchor="start", weight="bold")
    s.tick(px + pw - 62, y + 117, size=5, colour=t.good)
    s.text(px + pw - 52, y + 122, "Loaded", size=11, anchor="start")
    # Parameters, one row per parameter
    lw = 400
    bar(s, px, y + 146, lw, 226, "surface", amount=0.2)
    tile(s, px + 8, y + 154, 24, "sliders")
    s.text(px + 40, y + 171, "Parameters", size=12.5, anchor="start", weight="bold")
    rows = (("outdir", False, False), ("genome", True, False), ("max_memory", False, False),
            ("skip_trimming", True, True))
    ry = y + 202
    for i, (name, changed, check) in enumerate(rows):
        if i:
            s.line(px + 12, ry - 16, px + lw - 12, ry - 16, colour=t.muted, amount=0.2, passes=1, width=0.8)
        param_row(s, px + 12, ry, lw - 24, name, changed=changed, check=check)
        ry += 46
    # the aside: Where it runs, the dark preview, Launch again
    ax, aw = px + lw + 12, pw - lw - 12
    bar(s, ax, y + 146, aw, 92, "surface", amount=0.2)
    tile(s, ax + 8, y + 154, 24, "server")
    s.text(ax + 40, y + 171, "Where it runs", size=12.5, anchor="start", weight="bold")
    for k in range(3):
        stroke(s, ax + 12, y + 192 + k * 13, ax + 12 + (150, 120, 170)[k], width=1)
    s.raw(f'<rect x="{ax:.1f}" y="{y + 246:.1f}" width="{aw:.1f}" height="96" rx="8" fill="{t.term_bg}"/>')
    tile(s, ax + 8, y + 254, 24, "fileCode", dark=True)
    s.raw(f'<text x="{ax + 40:.1f}" y="{y + 271:.1f}" font-family="{MONO}" font-size="11.5" '
          f'fill="{t.term_ink}">params.json</text>')
    code(s, ax + 8, y + 284, aw - 16, (('"genome": "…",', None), ('"skip_trimming": true', None)),
         size=10.5, step=15, pad=8)
    s.button(ax, y + 350, 90, "Launch", fill="done", h=22)
    stroke(s, ax + 98, y + 361, ax + aw - 10, width=1)


def row_zoom(s: Sketch, x: float, y: float, w: float) -> None:
    """One `.launch-param` row, drawn large: what each line of the row holds."""
    t = s.t
    s.magnifier(x + 10, y - 6, 8)
    s.text(x + 34, y, "one row, `.launch-param`, drawn large", size=14.5, anchor="start", weight="bold")
    # a text row
    ty = y + 40
    s.text(x, ty, "`outdir`", size=15, anchor="start")
    s.text(x + w, ty, "string · directory-path", size=13, anchor="end", colour=t.dim)
    bar(s, x, ty + 10, w, 30, "surface", amount=0.2)
    s.raw(f'<text x="{x + 10:.1f}" y="{ty + 30:.1f}" font-family="{MONO}" font-size="12" '
          f'fill="{t.dim}">./results</text>')
    s.text(x, ty + 60, "where the results are written", size=13, anchor="start", colour=t.dim)
    s.line(x, ty + 78, x + w, ty + 78, colour=t.muted, amount=0.3, passes=1, width=1)
    # the boolean row, CR-P3PARC-01
    by = ty + 110
    bar(s, x, by - 14, 17, 17, "input", amount=0.15)
    s.tick(x + 8.5, by - 5.5, size=6, width=2)
    s.text(x + 26, by, "`skip_trimming`", size=15, anchor="start")
    s.text(x + w, by, "boolean · changed · default false", size=13, anchor="end", colour=t.accent)
    s.text(x, by + 26, "skip the adapter trimming step", size=13, anchor="start", colour=t.dim)
    # what each part is
    lines(s, x, by + 64, ("line 1: the name, and its meta on the right:",
                          "type, format, changed, the default",
                          "line 2: the input, full width",
                          "line 3: the help",
                          "a screen reader hears one text, help · meta"), size=13)
    pin(s, x, by + 182, "R1 CR-P3PARC-01, major",
        ("a boolean row had no meta: a changed `skip_` flag", "did not show; fixed in ae60a735"), fixed=True)
    pin(s, x, by + 250, "R2 CR-P3PARC-04, minor, open",
        ("an error shows after the help; the boards", "put it under the input"), fixed=False)


def launch(s: Sketch) -> None:
    section(s, S1, "1 · Launch: one parameter per line, an icon on every section",
            "Thomas, 2026-10-31: why a grid, not one per line? no light icons on the sections", 640)
    top = S1 + 30
    launch_before(s, 50, top, 360, 400)
    s.arrow(420, top + 200, 456, top + 200)
    launch_after(s, 466, top, 640, 400)
    row_zoom(s, 1150, top + 18, 400)
    cy = top + 430
    lines(s, 230, cy, ("before: Parameters in a grid of 3 columns",
                       "the help and the meta in one grey line",
                       "plain section titles, no icon"), anchor="middle")
    lines(s, 786, cy, ("after: one parameter per row, the input full width",
                       "a line icon on every section: Pipeline, Parameters,",
                       "Where it runs, and the preview on its dark card",
                       "the Pipeline card above the grid; Launch in the page head too"),
          anchor="middle")
    s.text(786, cy + 92, "new group icons: filter, tag, shield, building, signpost, download",
           size=12.5, colour=s.t.dim)
    for i, name in enumerate(("filter", "tag", "shield", "building", "signpost", "download")):
        tile(s, 618 + i * 58, cy + 106, 26, name)


# -- 2 · the logos -----------------------------------------------------------------------------------

def logos(s: Sketch) -> None:
    t = s.t
    section(s, S2, "2 · the logos: one rule, `markFor`", "Thomas, inbox #91, answer (b): "
            "\"je veux les logos, important\"", 430)
    y0 = S2 + 44
    s.text(50, y0, "`workflow.name`", size=13.5, anchor="start", colour=t.dim)
    s.text(250, y0, "engine", size=13.5, anchor="start", colour=t.dim)
    s.text(470, y0, "the mark", size=13.5, anchor="start", colour=t.dim)
    rows = (("nf-core/rnaseq", "nextflow", "nf-core", "nf-core: the name starts with `nf-core/`"),
            ("lab/chipseq", "nextflow", "nextflow", "Nextflow, the engine's"),
            ("lab/variants", "snakemake", "snakemake", "Snakemake, the engine's"),
            ("any name", "unknown", None, "none; Launch shows a folder icon"))
    for i, (name, engine, key, says) in enumerate(rows):
        y = y0 + 44 + i * 54
        s.text(50, y, f"`{name}`", size=14, anchor="start")
        s.text(250, y, f"`{engine}`", size=14, anchor="start")
        s.arrow(370, y - 5, 450, y - 5, colour=t.dim)
        if key:
            logo(s, 474, y - 22, 34, key)
        else:
            icon(s, 474, y - 22, 34, "folder", colour=t.dim)
        s.text(526, y, says, size=13.5, anchor="start")
    pin(s, 50, y0 + 262, "R1 and R2 SEC-P3PARC-02, minor, open",
        ("the name is a claim: any fork can call itself `nf-core/…`; Thomas chose this rule and",
         "the mark gates no permission. The upstream source of the three logos stays",
         "[to be validated] in `media.yaml` before a release ships them, inbox #91"), fixed=False)

    # where the marks show, each at its size in the app, drawn 1.5 times larger
    x0 = 930
    s.text(x0, y0, "where it shows, at its size in the app", size=13.5, anchor="start", colour=t.dim)
    places = (("the runs list", "16 to 20 px", 20), ("Home", "18 to 22 px", 22),
              ("the run header tile", "26 px", 26), ("the Pipeline fact", "18 px", 18),
              ("the Launch Loaded card", "24 px", 24))
    for i, (where, px, size) in enumerate(places):
        y = y0 + 36 + i * 44
        logo(s, x0, y - size * 0.75, size * 1.5, "nf-core")
        s.text(x0 + 50, y + 8, where, size=13.5, anchor="start")
        s.text(x0 + 250, y + 8, px, size=12.5, anchor="start", colour=t.dim)
    yx = y0 + 36 + 5 * 44 + 8
    s.line(x0, yx - 22, 1550, yx - 22, dashed=True, colour=t.muted)
    s.text(x0, yx, "the engine's own places keep the engine's mark:", size=13.5, anchor="start",
           colour=t.dim)
    logo(s, x0, yx + 14, 24, "nextflow")
    logo(s, x0 + 32, yx + 14, 24, "snakemake")
    s.text(x0 + 70, yx + 32, "the Engine fact, the Launch engine buttons, 16 px", size=13.5,
           anchor="start")


# -- 3 · the run page --------------------------------------------------------------------------------

def copy_menu(s: Sketch, x: float, y: float) -> None:
    t = s.t
    s.text(x, y, "the run header, with Copy", size=14.5, anchor="start", weight="bold")
    hy = y + 22
    bar(s, x, hy, 470, 64, "surface", amount=0.2)
    bar(s, x, hy, 5, 64, "input", amount=0.1)
    s.raw(f'<rect x="{x + 16:.1f}" y="{hy + 12:.1f}" width="40" height="40" rx="10" fill="{t.fill("neutral")}" '
          f'stroke="{t.muted}" stroke-width="1"/>')
    logo(s, x + 23, hy + 19, 26, "nf-core")
    s.text(x + 68, hy + 30, "rnaseq-12", size=15, anchor="start", weight="bold")
    stroke(s, x + 68, hy + 46, x + 220, width=1.1)
    s.button(x + 262, hy + 18, 104, "Cancel run", fill="problem", h=28)
    s.button(x + 376, hy + 18, 82, "Copy      ", fill="surface", h=28)
    icon(s, x + 436, hy + 25, 14, "chevronDown")
    # the open menu under Copy
    mx, my = x + 290, hy + 56
    bar(s, mx, my, 176, 102, "surface", amount=0.3)
    for i, item in enumerate(("Config (params.json)", "Run directory", "Run ID")):
        if i == 2:
            bar(s, mx + 4, my + 6 + i * 31, 168, 28, "input", amount=0.1)
        s.text(mx + 12, my + 26 + i * 31, item, size=13, anchor="start")
    s.text(mx + 88, my + 122, "status, 4 s: Copied the run ID", size=12.5, colour=t.dim)
    lines(s, x, hy + 92, ("a menu of native buttons:",
                          "arrows and Home, End move,",
                          "Escape closes, focus back on Copy",
                          "Snakemake: Config (config.yaml)",
                          "a run from a terminal: no Run directory"), size=13)
    pin(s, x, hy + 214, "R2 CR-P3PARC-03, minor, open",
        ("the board says Parameters (params.json);", "recorded in ui-spec §4.4; the board",
         "follows at the next /apply-findings"), fixed=False)
    pin(s, x, hy + 296, "R1 CR-P3PARC-04, minor, open",
        ("the status line is `display:none` while empty,", "so Copied may go unannounced"), fixed=False)


def logs_tab(s: Sketch, x: float, y: float, w: float) -> None:
    t = s.t
    s.text(x, y, "the Logs tab, opened and read", size=14.5, anchor="start", weight="bold")
    by = y + 18
    h = 375
    s.browser(x, by, w, h, url="/runs/run_…?tab=logs&source=head-err")
    tx = x + 14
    for i, tab in enumerate(("Summary", "Tasks", "Parameters", "Logs")):
        s.text(tx, by + 54, tab, size=12.5, anchor="start", weight="bold" if tab == "Logs" else "normal",
               colour=t.ink if tab == "Logs" else t.dim)
        if tab == "Logs":
            s.line(tx, by + 61, tx + 32, by + 61, width=2.4, amount=0.2, passes=1)
        tx += {"Summary": 74, "Tasks": 52, "Parameters": 92}.get(tab, 0)
    # the source segments
    sx = x + 14
    for label in ("Head output", "Head errors", "Engine log"):
        sw = 92
        bar(s, sx, by + 76, sw, 24, "input" if label == "Head errors" else "surface", amount=0.15)
        s.text(sx + sw / 2, by + 93, label, size=12, weight="bold" if label == "Head errors" else "normal")
        sx += sw + 4
    s.text(sx + 8, by + 93, "last 64 KiB · loaded when you open it", size=11.5, anchor="start",
           colour=t.dim)
    # the actions
    ax = x + 14
    for label, name, aw in (("Reload", "reload", 84), ("Download last 64 KiB", "download", 176),
                            ("Open raw", "externalLink", 104)):
        bar(s, ax, by + 110, aw, 26, "surface", amount=0.15)
        icon(s, ax + 8, by + 115, 15, name)
        s.text(ax + 28, by + 128, label, size=12, anchor="start")
        ax += aw + 8
    # the File row
    s.text(x + 14, by + 166, "File", size=12, anchor="start", colour=t.dim)
    bar(s, x + 46, by + 150, w - 140, 24, "neutral", amount=0.1)
    s.raw(f'<text x="{x + 54:.1f}" y="{by + 166:.1f}" font-family="{MONO}" font-size="11" '
          f'fill="{t.ink}">runs_root/run_…/launch/.spectio/head.err</text>')
    s.button(x + w - 84, by + 149, 70, "Copy", fill="surface", h=26)
    # the viewer, the test's fixture lines
    rows = (("Oct-25 07:40:12 [main] INFO  nextflow.cli.CmdRun - N E X", None),
            ("[88/f1d0e2] STAR_ALIGN (S04) completed", "ok"),
            ("retry 1/3 with memory 8 GB", "review"),
            ("ERROR nextflow.processor.TaskProcessor - exit 137", "failed"),
            ("nextflow.Session - progress 524 / 803 tasks", "progress"),
            ("Finished job 12.", "ok"))
    vb = code(s, x + 14, by + 186, w - 28, rows, size=11.5, step=19, pad=12)
    s.arrow(x + w - 22, by + 196, x + w - 22, vb - 8, colour=TINT["progress"])
    s.text(x + w - 30, vb + 18, "opened at its end, no wrap, scrolls sideways", size=12, anchor="end",
           colour=t.dim)
    icon(s, x + 14, vb + 30, 15, "file", colour=t.dim)
    s.text(x + 36, vb + 43, "each task's own files stay in its work directory:", size=12, anchor="start",
           colour=t.dim)
    s.text(x + 332, vb + 43, "open a task in Tasks", size=12, anchor="start", colour=t.accent)
    icon(s, x + 456, vb + 32, 13, "arrowRight", colour=t.accent)


def raw_tab(s: Sketch, x: float, y: float) -> None:
    t = s.t
    s.text(x, y, "Open raw: a new tab", size=14.5, anchor="start", weight="bold")
    s.page(x + 6, y + 22, 90, 116, fill="surface", lines=5)
    lines(s, x + 112, y + 44, ("the same text as a page,",
                               "`GET /api/v1/runs/id/logs`",
                               "`?source=head-err`",
                               "`text/plain`, `nosniff`,",
                               "`no-store`"), size=12.5)
    pin(s, x, y + 172, "R1 and R2 SEC-P3PARC-01,", ("minor, open: the raw page", "has no CSP and no",
                                                     "Referrer-Policy; text/plain", "and nosniff keep it",
                                                     "safe today"), fixed=False)
    s.text(x, y + 300, "level tints, a second cue:", size=13.5, anchor="start", weight="bold")
    for i, (tint, word) in enumerate((("failed", "ERROR, Error, exception"), ("review", "WARN, retry"),
                                      ("ok", "completed, Finished job"), ("progress", "progress N"))):
        s.dot(x + 8, y + 320 + i * 20, 5, colour=TINT[tint])
        s.text(x + 20, y + 325 + i * 20, word, size=12.5, anchor="start")
    pin(s, x, y + 424, "R1 CR-P3PARC-05, minor,", ("open: any line with the", "word completed is green"),
        fixed=False)


def journey(s: Sketch, x: float, y: float) -> None:
    """CR-P3PARC-02: the log source survives a tab switch."""
    t = s.t
    s.text(x, y, "the URL keeps the tab and the source, and the page remembers the last source:",
           size=14.5, anchor="start", weight="bold")
    steps = (("Logs", "`?tab=logs&source=engine`"), ("pick Head errors", "`?tab=logs&source=head-err`"),
             ("Summary", "`?` no source in the URL"), ("Logs again", "`?tab=logs&source=head-err`"))
    for i, (word, url) in enumerate(steps):
        cx = x + 110 + i * 270
        s.step(cx, y + 40, i + 1, word, size=16)
        s.text(cx, y + 62, url, size=12.5, colour=t.dim)
        if i < 3:
            s.arrow(cx + 96, y + 35, cx + 172, y + 35, colour=t.dim)
    s.tick(x + 640, y + 96, size=7, colour=t.good)
    s.text(x + 654, y + 101, "back on Head errors, from the ref `lastSource`", size=13.5, anchor="start")
    s.text(x + 654, y + 121, "before the fix: back on the Engine log", size=12.5, anchor="start",
           colour=t.dim)
    pin(s, x, y + 101, "R1 and R2 CR-P3PARC-02, minor", ("fixed in 4506ab5f, with a test written first",),
        fixed=True)


def run_page(s: Sketch) -> None:
    section(s, S3, "3 · the run page: Copy, then opening and reading the logs",
            "Thomas: run detail UI? opening and reading the logs?", 650)
    copy_menu(s, 50, S3 + 40)
    logs_tab(s, 560, S3 + 40, 620)
    raw_tab(s, 1220, S3 + 40)
    journey(s, 50, S3 + 480)


# -- 4 · the review rounds ---------------------------------------------------------------------------

def rounds(s: Sketch) -> None:
    t = s.t
    x0 = 50
    s.text(x0, S4, "4 · three review rounds, one cell per finding", size=19, anchor="start", weight="bold")
    cx_cr, cx_sec, cx_v = x0 + 60, x0 + 360, x0 + 500
    s.text(cx_cr, S4 + 36, "code-reviewer", size=12.5, anchor="start", colour=t.dim)
    s.text(cx_sec, S4 + 36, "security", size=12.5, anchor="start", colour=t.dim)
    s.text(cx_v, S4 + 36, "verdicts", size=12.5, anchor="start", colour=t.dim)
    cell = 30
    for i, (rnd, crv, cr, secv, sec) in enumerate(ROUNDS):
        y = S4 + 52 + i * 44
        s.text(x0, y + 21, rnd, size=15, anchor="start", weight="bold")
        for j, (sev, fixed) in enumerate(cr):
            bar(s, cx_cr + j * (cell + 4), y, cell, cell, SEV[sev], amount=0.2)
            if fixed:
                s.tick(cx_cr + j * (cell + 4) + cell / 2, y + cell / 2, size=6, colour=t.good)
        for j, (sev, fixed) in enumerate(sec):
            bar(s, cx_sec + j * (cell + 4), y, cell, cell, SEV[sev], amount=0.2)
        if not cr and not sec:
            s.text(cx_cr, y + 21, "no finding", size=13, anchor="start", colour=t.dim)
            s.text(cx_sec, y + 21, "none", size=13, anchor="start", colour=t.dim)
        s.text(cx_v, y + 21, f"{crv}, {secv}", size=13.5, anchor="start")
    ky = S4 + 52 + 3 * 44 + 18
    for k, (fill, word) in enumerate((("problem", "major"), ("neutral", "minor"), ("docs", "simplify"))):
        bar(s, x0 + k * 130, ky - 14, 18, 18, fill, amount=0.15)
        s.text(x0 + 26 + k * 130, ky, word, size=13, anchor="start")
    s.tick(x0 + 400, ky - 5, size=6, colour=t.good)
    s.text(x0 + 414, ky, "fixed on the branch", size=13, anchor="start")
    lines(s, x0, ky + 30, ("IDs restart in each round; R2's cells are 02 to 05: 02 is R1's 02 again, and 05",
                           "repeats R1's 06, whose indentation part 089adc38 fixed; the rest: docs/reviews/code/P3-parC.md"),
          size=12.5,
          first=False)
    s.terminal(800, S4 + 20, 750, 190, (
        "simplifier, 089adc38: the Pipeline section's indentation,",
        "  whitespace only, 101 lines out, 101 in",
        "pytest                     511 passed, 15 deselected",
        "tsc --noEmit               clean",
        "vitest                     140 of 140, 15 files",
        "eslint: not run, the web package has no config"), size=12.5)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=91)
    s.heading(50, 58, "P3 UI parity C · Launch rows and icons, the logos, the run's Copy menu and logs",
              "web/src and the two Launch boards · what Thomas asked on 2026-10-31, against the Lite boards"
              " · three review rounds")
    launch(s)
    s.line(30, S2 - 40, W - 30, S2 - 40, dashed=True, colour=theme.muted)
    logos(s)
    s.line(30, S3 - 40, W - 30, S3 - 40, dashed=True, colour=theme.muted)
    run_page(s)
    s.line(30, S4 - 40, W - 30, S4 - 40, dashed=True, colour=theme.muted)
    rounds(s)
    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch · a dot: left open · R1 to R3: the round · "
           "names and parameters illustrative, the log lines from the step's test", size=12.5,
           anchor="start", colour=theme.dim)
    s.text(W - 50, H - 16, "source: web/src at 089adc38 · api/logs.py · P3-parC reviews, rounds 1 to 3",
           size=12.5, anchor="end", colour=theme.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-parc-launch-logs")
