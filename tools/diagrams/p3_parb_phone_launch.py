#!/usr/bin/env python3
"""UI parity B, the phone, the Launch form and the Head word: step P3-parB, 2026-10-31.

Writes docs/assets/diagrams/p3-parb-phone-launch_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-parB at 1eb483ba (base 4ce91129):
- 20f2de99 (UX-PAR-08, 09, 10): web/src/shell/layout.tsx:23-36, the phone top bar's second row with
  the page title as the h1 and a 44 px back link named "Back to <screen>"; buttons, inputs, tabs and
  fold heads 44 px tall on the phone; runs, Home's lists, the run's processes as stacked cards;
  segments scroll sideways;
- d8988477 (UX-PAR-30 to 34): web/src/launch/LaunchPage.tsx:478-527, one FoldSection per schema
  group with an icon from its fa_icon and a status: "n required · filled", "n changed", "defaults";
  open when a required field is empty or a value changed; LaunchPage.tsx:229-240 and app.css:115-123,
  the phone's pinned bar: the summary (name version · engine · profile · n values changed) or the
  reason above a full-width 48 px Launch;
- web/src/launch/schemaFields.ts:180-200, buildParams: nested maps rebuilt from dotted keys, a map
  with one value set sent whole, its other keys at their defaults (CR-P3PARB-04 r2);
  LaunchPage.tsx:562-570, the preview built by the same buildParams, params.json for Nextflow,
  YAML for Snakemake (UX-PAR-32); 614b81f5: dotted sections for Snakemake only, Nextflow keeps a map
  as one JSON field (R3 CR-P3PARB-02); the example `ref` map with release 114 is the one of
  R2 CR-P3PARB-04, species is illustrative;
- 2f6809b5 reported an ended head at once; 7993752a reverts it (R3 CR-P3PARB-01): the early report
  set exited_at, the sink dropped the launch and the runner stopped reading the spool inside its
  60 s end grace (packages/spectio/src/spectio/runner/loop.py:87-93, 276-280);
  web/src/runs/RunHeader.tsx:33-39, headWord: "Ending" while the head is alive and the run terminal;
- 8c86467f (R1 SEC-P3PARB-01, major): null-prototype maps in buildParams; R2 re-filed it as a
  blocker with status fixed, verified; dcec010e (R4 CR-P3PARB-R4-01, major): a typed JSON null;
- the review rounds, from the step's worker result (rounds 1 to 3, every id and severity) and the
  round-4 review made by hand after two fix rounds without approval (CR-P3PARB-R4-01 to 04, its
  major closed at dcec010e, the minors in db620dc3; security approve, no finding).
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from sketch import MONO, Box, Sketch, Theme, main_for

W, H = 1600, 1640
PY, PW, PH = 176, 180, 370  # the phones
PX = (50, 290, 495, 700, 905)  # before; after: Runs, Home, Launch, the run
LAB = PY + PH + 28
S2 = 690  # the Launch form
S3 = 1240  # the Head word and the review rounds
SCALE = 166 / 390  # a phone screen drawn 166 px wide stands for 390 CSS px

# (round, CR verdict, CR severities, SEC verdict, SEC severities), in id order, from the reviews
ROUNDS = (
    ("R1", "approve", "mmmmsm", "changes", "Mm"),
    ("R2", "approve", "mmmmsm", "approve", "Bm"),
    ("R3", "changes", "Mmmmmmss", "approve", "mm"),
    ("R4", "changes", "Mmmm", "approve", ""),
)
SEV = {"B": "problem", "M": "problem", "m": "neutral", "s": "docs"}


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, amount: float = 0.4) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=amount)


def stroke(s: Sketch, x1: float, y: float, x2: float, *, width: float = 1.4) -> None:
    """A ruled stroke standing for a line of text."""
    s.line(x1, y, x2, y, colour=s.t.muted, amount=0.3, passes=1, width=width)


def mark(s: Sketch, cx: float, cy: float, r: float = 6) -> None:
    """The engine's mark, a small round logo."""
    s.circle(cx, cy, r, fill="input")
    s.dot(cx, cy, r * 0.35, colour=s.t.dim)


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start", first: bool = True) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 and first else s.t.dim)


def code(s: Sketch, x: float, y: float, w: float, rows: tuple[str, ...], *, size: float = 12) -> float:
    """The app's code surface: monospace lines. Returns its bottom."""
    h = 12 + len(rows) * 17
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{s.t.term_bg}"/>')
    for i, text in enumerate(rows):
        s.raw(f'<text x="{x + 10:.1f}" y="{y + 19 + i * 17:.1f}" font-family="{MONO}" font-size="{size}" '
              f'fill="{s.t.term_ink}" xml:space="preserve">{escape(text)}</text>')
    return y + h


def topbar(s: Sketch, scr: Box) -> float:
    """The phone top bar's first row: the menu and the app name. Returns the y under it."""
    for k in range(3):
        s.line(scr.x + 8, scr.y + 9 + k * 5, scr.x + 20, scr.y + 9 + k * 5, amount=0.2, passes=1, width=1.4)
    s.text(scr.x + 28, scr.y + 18, "Spectio", size=11.5, anchor="start", weight="bold")
    s.line(scr.x, scr.y + 26, scr.right, scr.y + 26, colour=s.t.muted, amount=0.3, passes=1, width=1)
    return scr.y + 26


def title_row(s: Sketch, scr: Box, y: float, title: str, *, back: bool = False) -> float:
    """The second row (UX-PAR-08): a 44 px back link, the page title as the h1, its sub line."""
    t = 44 * SCALE
    x = scr.x + 8
    if back:
        bar(s, x, y + 5, t, t, "input", amount=0.2)
        s.text(x + t / 2, y + 5 + t / 2 + 5, "<", size=13, weight="bold")
        x += t + 6
    s.text(x, y + 20, title, size=13.5, anchor="start", weight="bold")
    stroke(s, x, y + 28, x + 70, width=1.1)
    s.line(scr.x, y + 34, scr.right, y + 34, colour=s.t.muted, amount=0.3, passes=1, width=1)
    return y + 34


def card(s: Sketch, x: float, y: float, w: float, rail: str, *, h: float = 40) -> None:
    """A stacked run card: a state rail, the engine mark, ruled strokes for its text."""
    bar(s, x, y, w, h, "surface", amount=0.3)
    bar(s, x, y, 4, h, rail, amount=0.2)
    mark(s, x + 16, y + 12, r=5)
    stroke(s, x + 26, y + 12, x + w * 0.72)
    stroke(s, x + 10, y + 26, x + w * 0.55, width=1.1)
    stroke(s, x + 10, y + 34, x + w * 0.40, width=1.1)


def pills(s: Sketch, x: float, y: float, right: float, h: float, *, first: str = "surface") -> None:
    """Segment pills scrolling sideways: the last one runs off the screen's edge."""
    gx = x
    for i, w in enumerate((30, 46, 44, 58, 56)):
        end = min(gx + w, right)
        bar(s, gx, y, end - gx, h, first if i == 0 else "surface", amount=0.2)
        if end < gx + w:
            break
        stroke(s, gx + 8, y + h / 2, gx + w - 8, width=1.2)
        gx += w + 4


def fold_head(s: Sketch, x: float, y: float, w: float, h: float, *, status: str = "") -> None:
    """A fold head on the phone, 44 px tall: tile, title stroke, status tint, chevron."""
    bar(s, x, y, w, h, "surface", amount=0.2)
    bar(s, x + 4, y + 4, h - 8, h - 8, "neutral", amount=0.2)
    stroke(s, x + h + 2, y + h / 2, x + w * 0.55)
    if status:
        bar(s, x + w - 46, y + 5, 30, h - 10, status, amount=0.2)
    s.text(x + w - 7, y + h / 2 + 4, ">", size=10, colour=s.t.dim)


def phones(s: Sketch) -> None:
    t = s.t
    s.text(50, PY - 26, "1 · the phone, before and after", size=19, anchor="start", weight="bold")
    s.text(380, PY - 26, "every target 44 px, drawn to scale: a screen 390 px wide", size=13.5,
           anchor="start", colour=t.dim)
    tgt, low = 44 * SCALE, 36 * SCALE

    # before: the runs list as a five-column table, 36 px targets, no title row
    scr = s.phone(PX[0], PY, PW, PH)
    y = topbar(s, scr) + 8
    gx = scr.x + 6
    for w in (30, 42, 44):
        bar(s, gx, y, w, low, "surface", amount=0.2)
        gx += w + 3
    y += low + 10
    cols = [scr.x + 4 + k * (scr.w - 8) / 5 for k in range(6)]
    for r in range(9):
        ry = y + r * 18
        if r == 0:
            bar(s, scr.x + 4, ry, scr.w - 8, 16, "neutral", amount=0.2)
        for k in range(5):
            stroke(s, cols[k] + 3, ry + 9, cols[k + 1] - 3 + (8 if k == 4 else 0), width=1.1)
    for c in cols[1:5]:
        s.line(c, y, c, y + 9 * 18, colour=t.muted, amount=0.2, passes=1, width=0.8)
    s.button(scr.x + scr.w - 66, scr.bottom - low - 10, 58, "Launch", fill="surface", h=low)
    s.cross(PX[0] + PW - 8, PY + 8, size=8)

    # after: Runs, stacked cards, pills scrolling sideways
    scr = s.phone(PX[1], PY, PW, PH)
    y = title_row(s, scr, topbar(s, scr), "Runs")
    pills(s, scr.x + 6, y + 8, scr.right, tgt, first="input")
    s.arrow(scr.x + 90, y + 8 + tgt + 9, scr.x + 140, y + 8 + tgt + 9, colour=t.dim)
    s.arrow(scr.x + 90, y + 8 + tgt + 9, scr.x + 50, y + 8 + tgt + 9, colour=t.dim)
    for j, rail in enumerate(("input", "input", "problem", "done", "done")):
        cy = y + 44 + j * 48
        if cy + 40 < scr.bottom - 4:
            card(s, scr.x + 6, cy, scr.w - 12, rail)

    # after: Home, count cards 2 by 2
    scr = s.phone(PX[2], PY, PW, PH)
    y = title_row(s, scr, topbar(s, scr), "Home")
    cw = (scr.w - 18) / 2
    for k, (word, fill) in enumerate((("Running", "input"), ("Queued", "neutral"),
                                      ("Failed", "problem"), ("Succeeded", "done"))):
        cx, cy = scr.x + 6 + (k % 2) * (cw + 6), y + 8 + (k // 2) * 50
        bar(s, cx, cy, cw, 44, "surface", amount=0.3)
        bar(s, cx, cy, 4, 44, fill, amount=0.2)
        s.text(cx + 10, cy + 15, word, size=11, anchor="start")
        s.line(cx + 10, cy + 27, cx + 24, cy + 27, width=2.6, amount=0.2, passes=1)
        stroke(s, cx + 10, cy + 37, cx + cw - 10, width=1.1)
    y += 116
    fold_head(s, scr.x + 6, y, scr.w - 12, tgt)
    for j, rail in enumerate(("input", "input", "problem")):
        cy = y + tgt + 6 + j * 46
        if cy + 40 < scr.bottom - 4:
            card(s, scr.x + 6, cy, scr.w - 12, rail)

    # after: Launch, the pinned bar with its summary above a full-width 48 px Launch
    scr = s.phone(PX[3], PY, PW, PH)
    y = title_row(s, scr, topbar(s, scr), "Launch")
    for j in range(2):
        bar(s, scr.x + 6, y + 8 + j * (tgt + 18), scr.w - 12, tgt, "surface", amount=0.2)
        stroke(s, scr.x + 12, y + 8 + j * (tgt + 18) + tgt / 2, scr.x + 80)
        stroke(s, scr.x + 6, y + 8 + j * (tgt + 18) + tgt + 8, scr.x + 60, width=1.0)
    y += 8 + 2 * (tgt + 18)
    for j, status in enumerate(("done", "input", "neutral")):
        fold_head(s, scr.x + 6, y + j * (tgt + 4), scr.w - 12, tgt, status=status)
    btn = 48 * SCALE
    by = scr.bottom - btn - 6
    s.line(scr.x, by - 22, scr.right, by - 22, colour=t.muted, amount=0.3, passes=1, width=1)
    stroke(s, scr.x + 8, by - 10, scr.right - 14, width=1.3)
    s.button(scr.x + 6, by, scr.w - 12, "Launch", fill="done", h=btn)

    # after: the run, with the back link in its title row
    scr = s.phone(PX[4], PY, PW, PH)
    y = title_row(s, scr, topbar(s, scr), "rnaseq-12", back=True)
    bar(s, scr.x + 6, y + 8, scr.w - 12, 52, "surface", amount=0.3)
    bar(s, scr.x + 6, y + 8, 4, 52, "input", amount=0.2)
    mark(s, scr.x + 22, y + 22, r=6)
    stroke(s, scr.x + 34, y + 22, scr.right - 20)
    stroke(s, scr.x + 16, y + 38, scr.right - 50, width=1.1)
    stroke(s, scr.x + 16, y + 50, scr.right - 70, width=1.1)
    y += 68
    gx = scr.x + 6
    for w in (46, 34, 60):
        bar(s, gx, y, w, tgt, "input" if gx == scr.x + 6 else "surface", amount=0.2)
        stroke(s, gx + 8, y + tgt / 2, gx + w - 8, width=1.1)
        gx += w + 4
    y += tgt + 8
    for j, done in enumerate((1.0, 1.0, 0.55, 0.2)):
        cy = y + j * 44
        if cy + 38 < scr.bottom - 4:
            bar(s, scr.x + 6, cy, scr.w - 12, 38, "surface", amount=0.3)
            stroke(s, scr.x + 12, cy + 12, scr.x + 100)
            bar(s, scr.x + 12, cy + 22, scr.w - 24, 8, "neutral", amount=0.1)
            bar(s, scr.x + 12, cy + 22, (scr.w - 24) * done, 8, "done" if done == 1.0 else "input", amount=0.1)

    s.arrow(PX[0] + PW + 10, PY + PH / 2, PX[1] - 10, PY + PH / 2, colour=t.dim)
    captions = (
        ("before: Runs", "five columns squeezed", "36 px targets, no title"),
        ("after: Runs", "stacked run cards, 10", "pills scroll sideways"),
        ("Home", "count cards 2 by 2, 10", "its lists as cards"),
        ("Launch", "fold heads 44 px, 09", "a full-width Launch, 34"),
        ("the run", "Back to Runs, 44 px, 08", "the title is the h1"),
    )
    for x, rows in zip(PX, captions):
        lines(s, x + PW / 2, LAB, rows, anchor="middle")

    # the two zooms
    zx, zw = 1140, 410
    s.magnifier(zx + 8, PY + 6, 6)
    s.text(zx + 26, PY + 12, "the run's title row, UX-PAR-08", size=14, anchor="start", weight="bold")
    y = PY + 30
    bar(s, zx, y, zw, 70, "surface", amount=0.3)
    bar(s, zx + 12, y + 13, 44, 44, "input", amount=0.3)
    s.text(zx + 34, y + 43, "<", size=22, weight="bold")
    s.text(zx + 70, y + 36, "rnaseq-12", size=22, anchor="start", weight="bold")
    s.text(zx + 70, y + 56, "nf-core/rnaseq 3.27.0 · Nextflow", size=12.5, anchor="start", colour=t.dim)
    s.line(zx - 10, y + 13, zx - 10, y + 57, colour=t.accent, amount=0.2, passes=1, width=1.4)
    s.text(zx - 16, y + 40, "44", size=12, anchor="end", colour=t.accent)
    lines(s, zx, y + 96, ("the link is named Back to Runs, from `back.label`",
                          "the page title is the h1, its sub line under it",
                          "buttons, inputs, tabs, fold heads: 44 px, 09"), size=13, first=False)

    y = PY + 200
    s.magnifier(zx + 8, y + 6, 6)
    s.text(zx + 26, y + 12, "Launch's pinned bar, UX-PAR-09 and 34", size=14, anchor="start", weight="bold")
    y += 28
    bar(s, zx, y, zw, 104, "surface", amount=0.3)
    s.text(zx + 12, y + 22, "nf-core/rnaseq 3.27.0 · Nextflow · singularity", size=12.5, anchor="start",
           colour=t.dim)
    s.text(zx + 12, y + 38, "2 values changed", size=12.5, anchor="start", colour=t.dim)
    s.button(zx + 12, y + 46, zw - 24, "Launch", fill="done", h=48)
    s.line(zx - 10, y + 46, zx - 10, y + 94, colour=t.accent, amount=0.2, passes=1, width=1.4)
    s.text(zx - 16, y + 75, "48", size=12, anchor="end", colour=t.accent)
    lines(s, zx, y + 128, ("the summary, or the reason it cannot launch:",
                           "Fill the required field: input",
                           "linked to the button by `aria-describedby`"), size=13, first=False)


def tile_icon(s: Sketch, x: float, y: float, size: float, kind: str) -> None:
    """A group's icon tile: a light line icon mapped from its `fa_icon`."""
    bar(s, x, y, size, size, "neutral", amount=0.2)
    c, k = (x + size / 2, y + size / 2), size * 0.28
    if kind == "folder":
        s.poly([(c[0] - k, c[1] - k * 0.6), (c[0] - k * 0.2, c[1] - k * 0.6), (c[0], c[1] - k * 0.2),
                (c[0] + k, c[1] - k * 0.2), (c[0] + k, c[1] + k), (c[0] - k, c[1] + k)], amount=0.2, width=1.3)
    elif kind == "dna":  # two strands crossing twice, with rungs
        for d in (-1, 1):
            pts = [(c[0] + d * k * 0.8 * math.sin(math.pi * j / 4), c[1] - k * 1.1 + j * k * 0.275)
                   for j in range(9)]
            s.poly(pts, close=False, amount=0.1, width=1.3)
        for j in (1, 3, 5, 7):
            w = k * 0.8 * abs(math.sin(math.pi * j / 4))
            s.line(c[0] - w, c[1] - k * 1.1 + j * k * 0.275, c[0] + w, c[1] - k * 1.1 + j * k * 0.275,
                   colour=s.t.dim, amount=0.1, passes=1, width=1)
    else:  # a gauge for the job limits
        s.circle(c[0], c[1] + k * 0.3, k, width=1.3)
        s.line(c[0], c[1] + k * 0.3, c[0] + k * 0.6, c[1] - k * 0.4, amount=0.2, passes=1, width=1.3)


def group(s: Sketch, x: float, y: float, w: float, icon: str, title: str, status: str, fill: str,
          *, open_: bool = False, mono: bool = False) -> None:
    """A schema group (UX-PAR-30) or a config map's section (UX-PAR-31): icon, title, status, chevron."""
    tile_icon(s, x, y, 26, icon) if icon else bar(s, x, y, 26, 26, "neutral", amount=0.2)
    s.text(x + 36, y + 18, f"`{title}`" if mono else title, size=14, anchor="start", weight="bold")
    sw = 16 + len(status) * 6.6
    bar(s, x + w - 30 - sw, y + 3, sw, 21, fill, amount=0.2)
    s.text(x + w - 30 - sw / 2, y + 18, status, size=12)
    s.text(x + w - 12, y + 18, "v" if open_ else ">", size=13, colour=s.t.dim)


def field(s: Sketch, x: float, y: float, w: float, label: str, value: str, *, changed: bool = False) -> None:
    s.text(x, y, f"`{label}`", size=13, anchor="start")
    if changed:
        s.text(x + w, y, "changed", size=11.5, anchor="end", colour=s.t.accent)
    bar(s, x, y + 7, w, 26, "input" if changed else "surface", amount=0.2)
    s.text(x + 9, y + 25, f"`{value}`", size=12.5, anchor="start", colour=s.t.ink if changed else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...]) -> float:
    """A blocker or major pinned where it hits, ticked: each was fixed on the branch."""
    s.tick(x + 8, y - 5, size=7)
    s.text(x + 24, y, fid, size=13.5, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)
    return y + 30 + len(rows) * 18


def launch(s: Sketch) -> None:
    t = s.t
    s.line(30, S2 - 36, W - 30, S2 - 36, dashed=True, colour=t.muted)
    s.text(50, S2, "2 · the Launch form", size=19, anchor="start", weight="bold")
    s.text(260, S2, "groups that fold, nested maps as dotted sections, one buildParams", size=13.5,
           anchor="start", colour=t.dim)
    top, ch, cw = S2 + 20, 300, 390

    # Nextflow: one fold per schema group
    x = 50
    s.frame(x, top, cw, ch)
    mark(s, x + 20, top + 22, r=8)
    s.text(x + 36, top + 27, "nf-core/rnaseq 3.27.0 · Nextflow", size=14, anchor="start")
    gx, gw = x + 14, cw - 28
    group(s, gx, top + 46, gw, "folder", "Input/output options", "2 required · filled", "done")
    group(s, gx, top + 88, gw, "dna", "Reference genome options", "2 changed", "input", open_=True)
    field(s, gx + 36, top + 136, 160, "genome", "GRCh38", changed=True)
    field(s, gx + 210, top + 136, 140, "igenomes_base", "s3 path", changed=True)
    group(s, gx, top + 192, gw, "gauge", "Max job request options", "defaults", "neutral")
    s.line(x + 14, top + 236, x + cw - 14, top + 236, colour=t.muted, amount=0.3, passes=1, width=1)
    lines(s, x + 14, top + 258, ("a line icon from each group's `fa_icon`, 30",
                                 "open when a required field is empty or a value changed"), size=13, first=False)

    # Snakemake: a nested config map becomes a dotted section
    x = 470
    s.frame(x, top, cw, ch)
    mark(s, x + 20, top + 22, r=8)
    s.text(x + 36, top + 27, "a Snakemake workflow · its config.yaml", size=14, anchor="start")
    gx = x + 14
    group(s, gx, top + 46, gw, "", "ref", "1 changed", "input", open_=True, mono=True)
    field(s, gx + 36, top + 94, 150, "ref.species", "homo_sapiens")
    field(s, gx + 200, top + 94, 150, "ref.release", "114", changed=True)
    group(s, gx, top + 150, gw, "", "trimming", "defaults", "neutral", mono=True)
    group(s, gx, top + 192, gw, "", "pca", "defaults", "neutral", mono=True)
    s.line(x + 14, top + 236, x + cw - 14, top + 236, colour=t.muted, amount=0.3, passes=1, width=1)
    lines(s, x + 14, top + 258, ("one value set: the whole `ref` map is sent,",
                                 "the others at their defaults, CR-P3PARB-04 r2"), size=13, first=False)

    # the fork: both forms drop their values into one function, which feeds the request and the preview
    cx, cy = 1010, top + 130
    low = top + ch + 30
    for dx in (250, 665):
        s.line(dx, top + ch + 2, dx, low, amount=0.4, passes=1)
    s.line(250, low, cx, low, amount=0.4, passes=1)
    s.arrow(cx, low, cx, cy + 26)
    s.text(50, low + 24, "the form's values, either engine", size=12.5, anchor="start", colour=t.dim)
    s.text(470, low + 24, "on Nextflow a map stays one JSON field, R3 CR-P3PARB-02", size=12.5, anchor="start",
           colour=t.dim)
    s.cog(cx, cy, 16, fill="work")
    s.text(cx - 30, cy - 2, "`buildParams`", size=15, anchor="end", weight="bold")
    s.text(cx - 30, cy + 17, "one function, 32", size=12.5, anchor="end", colour=t.dim)

    ox = 1080
    s.arrow(cx + 20, cy - 16, ox - 6, top + 30)
    s.envelope(ox, top + 6, 64, 44, fill="surface")
    s.text(ox + 80, top + 22, "`POST /runs`, the request body", size=13.5, anchor="start", weight="bold")
    code(s, ox + 80, top + 32, 390, ('"params": {"ref": {',
                                     '  "species": "homo_sapiens",',
                                     '  "release": 114}}'))
    s.arrow(cx + 20, cy + 16, ox - 6, top + 186)
    s.page(ox + 6, top + 160, 52, 64, fill="surface")
    s.text(ox + 80, top + 172, "the preview in the aside", size=13.5, anchor="start", weight="bold")
    bot = code(s, ox + 80, top + 182, 390, ("ref:", "  species: homo_sapiens", "  release: 114"))
    lines(s, ox + 80, bot + 22, ("YAML for Snakemake; `params.json` for Nextflow",
                                 "what you read is what is sent"), size=13, first=False)

    y = pin(s, 940, top + ch + 30 + 64, "R1 SEC-P3PARB-01, major; R2 as a blocker, verified fixed",
            ("a schema key `__proto__` wrote into `Object.prototype`;",
             "unsafe keys skipped and named, null-prototype maps, `8c86467f`"))
    pin(s, 940, y, "R4 CR-P3PARB-R4-01, major", ("a JSON null typed in was sent as unset, `dcec010e`",))


def head(s: Sketch) -> None:
    t = s.t
    s.line(30, S3 - 36, W - 30, S3 - 36, dashed=True, colour=t.muted)
    s.text(50, S3, "3 · the Head word, after a run ends", size=19, anchor="start", weight="bold")
    s.runner(50, S3 + 70, label="runner")
    s.page(160, S3 + 66, 36, 46, fill="gate")
    s.text(178, S3 + 128, "spool", size=12.5, colour=t.dim)

    x0, xe, xr, x1 = 230, 330, 690, 890  # axis start, the run ends, the end reported, axis end
    y = S3 + 40
    s.text(x0, y - 8, "the run page says Head:", size=12.5, anchor="start", colour=t.dim)
    for a, b, word, fill in ((x0, xe, "Alive", "done"), (xe, xr, "Ending", "gate"), (xr, x1, "Exited", "neutral")):
        bar(s, a + 2, y, b - a - 4, 26, fill, amount=0.3)
        s.text((a + b) / 2, y + 18, word, size=14, weight="bold")
    s.text(xr - 10, y + 18, "was Alive", size=12, anchor="end", colour=t.dim)
    s.line(xr - 72, y + 13, xr - 8, y + 13, colour=t.accent, amount=0.3, passes=1, width=1.5)

    ay = S3 + 110
    s.shade(xe, ay - 30, xr - xe, 28, fill="gate", opacity=0.8, colour=t.muted)
    s.text((xe + xr) / 2, ay - 11, "60 s end grace: the runner still reads the spool", size=13)
    s.arrow(x0, ay, x1, ay, colour=t.ink)
    for x, label in ((xe, "the run ends"), (xr, "then the head's end, `exited_at`")):
        s.line(x, ay - 6, x, ay + 6, amount=0.2, passes=1, width=2)
        s.text(x, ay + 22, label, size=13)
    s.text(x1, ay + 22, "time", size=12, anchor="end", colour=t.dim)

    # the rejected alternative, crossed out
    ry = S3 + 178
    s.text(x0, ry, "rejected: report the head's end at once, `2f6809b5`, reverted in `7993752a`", size=13.5,
           anchor="start", colour=t.dim)
    by = ry + 16
    s.shade(xe, by, xr - xe, 26, fill="problem", opacity=0.6, colour=t.muted, dashed=True)
    s.line(x0, by + 13, xe, by + 13, amount=0.3, passes=1)
    s.dot(xe, by + 13, 4, colour=t.accent)
    s.text(xe - 8, by + 44, "`exited_at` set here", size=12.5, anchor="start", colour=t.dim)
    s.text((xe + xr) / 2, by + 18, "spool no longer read", size=13)
    s.cross(xr - 22, by + 13, size=9)
    s.text(xr + 10, by + 10, "the server drops the launch,", size=12.5, anchor="start", colour=t.dim)
    s.text(xr + 10, by + 27, "events after `onFlowComplete`", size=12.5, anchor="start", colour=t.dim)
    s.text(xr + 10, by + 44, "can be lost", size=12.5, anchor="start", colour=t.dim)
    pin(s, 50, by + 82, "R3 CR-P3PARB-01, major", ("the end grace is kept whole; the screen says Ending instead, "
                                                    "`614b81f5`",))


def rounds(s: Sketch) -> None:
    t = s.t
    x0 = 960
    s.text(x0, S3, "4 · four review rounds, one cell per finding", size=19, anchor="start", weight="bold")
    s.text(x0, S3 + 22, "round 4 by hand, after two fix rounds without approval", size=13, anchor="start",
           colour=t.dim)
    cell, gap, cx_cr, cx_sec, vx = 20, 3, x0 + 40, x0 + 250, x0 + 320
    s.text(cx_cr, S3 + 50, "code-reviewer", size=12.5, anchor="start", colour=t.dim)
    s.text(cx_sec, S3 + 50, "security", size=12.5, anchor="start", colour=t.dim)
    s.text(vx + 30, S3 + 50, "verdicts", size=12.5, anchor="start", colour=t.dim)
    for i, (rnd, crv, cr, secv, sec) in enumerate(ROUNDS):
        y = S3 + 62 + i * 34
        s.text(x0, y + 16, rnd, size=15, anchor="start", weight="bold")
        for start, sevs in ((cx_cr, cr), (cx_sec, sec)):
            for k, c in enumerate(sevs):  # one cell per finding, in id order
                s.raw(f'<rect x="{start + k * (cell + gap):.1f}" y="{y:.1f}" width="{cell}" height="22" rx="2" '
                      f'fill="{t.fill(SEV[c])}" stroke="{t.ink}" stroke-width="0.8"/>')
                if c == "B":
                    s.text(start + k * (cell + gap) + cell / 2, y + 16, "B", size=12, weight="bold",
                           colour=t.accent)
            if not sevs:
                s.text(start, y + 16, "none", size=12.5, anchor="start", colour=t.dim)
        s.text(vx + 30, y + 16, f"{crv}, {secv}", size=13.5, anchor="start")
        if crv == "approve" and secv == "approve":
            s.tick(vx + 12, y + 10, size=7)
    ly = S3 + 62 + 4 * 34 + 8
    for k, (fill, label) in enumerate((("problem", "blocker, B, or major"), ("neutral", "minor"),
                                       ("docs", "simplify"))):
        lx = x0 + (0, 190, 290)[k]
        bar(s, lx, ly, 16, 16, fill, amount=0.3)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)
    lines(s, x0, ly + 46, ("the red cells are pinned where they hit:",
                           "SEC-P3PARB-01 and CR-P3PARB-R4-01 in 2,",
                           "CR-P3PARB-01 in 3; all four fixed on the branch",
                           "IDs repeat across rounds; R4 IDs carry R4"), size=13, first=False)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=233)
    s.heading(50, 58, "P3 UI parity B · the phone, the Launch form and the Head word, against the Lite boards",
              "`web/src` and one runner revert · fixes UX-PAR-08 to 10 and 30 to 34 of ui-parity-0.0.1 · "
              "four review rounds")
    phones(s)
    launch(s)
    head(s)
    rounds(s)
    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch, or both reviewers approve · R1 to R4: the round · "
           "a bare number: its UX-PAR finding", size=13, anchor="start", colour=s.t.dim)
    s.text(W - 50, H - 16, "source: web/src at 1eb483ba · runner loop.py · P3-parB reviews, rounds 1 to 4",
           size=12.5, anchor="end", colour=s.t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-parb-phone-launch")
