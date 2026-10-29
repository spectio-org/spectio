#!/usr/bin/env python3
"""A tiny hand-drawn SVG toolkit for Spectio's diagrams.

Origin
------
Ported from depictio (MIT, Copyright (c) 2023-2026 Thomas Weber):

- ``depictio/depictio`` ``dev/diagrams/sketch.py`` at ``0d1aa0a`` (2026-10-23):
  primitives and the glyph helpers (terminal, browser, page, folder, bucket,
  magnifier, chip, lock, warning, hourglass...).
- ``depictio/depictio-docs`` ``dev/diagrams/sketch.py`` at ``1610ed8``
  (2026-10-12): the ``Theme`` / ``write_themed`` light-and-dark rendering.

The two were merged so every helper is theme-aware, and Spectio's own glyphs
were added: ``gate``, ``runner``, ``hpc_node``, ``k8s_pod``, ``pipeline``,
``phone``, ``envelope``, ``link``, ``gauge``, ``task_strip``.

The look
--------
Excalidraw's: every stroke is drawn twice along a jittered bezier and text is
set in Excalifont. Text in `backticks` is set in monospace, because handwriting
mangles code. Jitter comes from a fixed seed, so re-running a figure writes a
byte-identical file and a diff shows only real changes.

Figures are generated, not drawn, so they can be corrected in a diff when the
thing they show changes. A hand-made PNG goes stale silently.
"""

from __future__ import annotations

import asyncio
import math
import os
import random
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parents[2]
SKETCH_TTF = Path(os.environ.get("SPECTIO_SKETCH_TTF", REPO_ROOT / "docs" / "fonts" / "Excalifont.ttf"))
OUT_DIR = REPO_ROOT / "docs" / "assets" / "diagrams"

# The bundled face first, so the PNG render does not depend on installed fonts. Where it is
# missing (an SVG seen without the font) a plain sans follows, never a novelty face.
FONT = "Excalifont, ui-sans-serif, system-ui, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

_CODE = re.compile(r"`([^`]+)`")


def _spans(content: str, size: float) -> str:
    """``content`` with backticked runs set in monospace, on one baseline."""
    out = []
    for i, part in enumerate(_CODE.split(content)):
        if not part:
            continue
        if i % 2:
            out.append(f'<tspan font-family="{MONO}" font-size="{size * 0.88:.1f}">{escape(part)}</tspan>')
        else:
            out.append(escape(part))
    return "".join(out)


# -- themes -------------------------------------------------------------------


@dataclass(frozen=True)
class Theme:
    """A palette. Figures name fills by meaning and are drawn once per theme."""

    name: str
    bg: str
    ink: str  # strokes and primary text
    dim: str  # secondary text
    accent: str  # the "look here" stroke, and "does not happen"
    muted: str  # de-emphasised strokes
    good: str  # ticks, passing checks
    warn: str  # warning ink
    term_bg: str  # terminal body
    term_ink: str  # terminal text
    fills: dict[str, str] = field(default_factory=dict)

    def fill(self, key: str) -> str:
        """``"none"``, a raw ``#hex``, or a semantic key from ``fills``."""
        if key == "none" or key.startswith("#"):
            return key
        return self.fills[key]


# Excalidraw's defaults: near-black ink on white, pastel fills. Semantic keys
# ("input", "gate", "done"...) alias the colours so figures say what a fill means.
_LIGHT_BASE = {
    "blue": "#e7f5ff",
    "yellow": "#fff9db",
    "green": "#ebfbee",
    "violet": "#f3f0ff",
    "orange": "#ffe8cc",
    "pink": "#ffe3e3",
    "grey": "#f1f3f5",
    "white": "#ffffff",
    # stronger tints for to-scale bars and cells, which must read at a glance
    "bar_blue": "#a5d8ff",
    "bar_green": "#b2f2bb",
    "bar_violet": "#d0bfff",
    "bar_orange": "#ffd8a8",
    "bar_grey": "#dee2e6",
}
_DARK_BASE = {
    "blue": "#24303d",
    "yellow": "#363020",
    "green": "#23342a",
    "violet": "#2b2938",
    "orange": "#382c22",
    "pink": "#38262b",
    "grey": "#282b33",
    "white": "#24272f",
    "bar_blue": "#2f5577",
    "bar_green": "#2e5c3b",
    "bar_violet": "#4a3f78",
    "bar_orange": "#6b4a26",
    "bar_grey": "#3a3e48",
}
_SEMANTIC = {
    "input": "blue",
    "work": "orange",
    "gate": "yellow",
    "done": "green",
    "docs": "violet",
    "problem": "pink",
    "neutral": "grey",
    "surface": "white",
    "cached": "bar_grey",
    "recomputed": "bar_orange",
}


def _with_semantic(base: dict[str, str]) -> dict[str, str]:
    return {**base, **{k: base[v] for k, v in _SEMANTIC.items()}}


LIGHT = Theme(
    name="light",
    bg="#ffffff",
    ink="#1e1e1e",
    dim="#5c5c5c",
    accent="#c92a2a",
    muted="#adb5bd",
    good="#2f9e44",
    warn="#e8590c",
    term_bg="#1e1e1e",
    term_ink="#f1f3f5",
    fills=_with_semantic(_LIGHT_BASE),
)

# Tuned against mkdocs-material's slate scheme rather than inverted from LIGHT:
# fills stay close to the page so they read as a tint on a surface.
DARK = Theme(
    name="dark",
    bg="#1f2129",
    ink="#e3e3e3",
    dim="#9aa0ac",
    accent="#ff8787",
    muted="#585e6b",
    good="#69db7c",
    warn="#ffa94d",
    term_bg="#121318",
    term_ink="#e3e3e3",
    fills=_with_semantic(_DARK_BASE),
)

THEMES = (LIGHT, DARK)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    fill: str = "none"  # a Theme fill key, a raw #hex, or "none"
    title: str = ""
    lines: tuple[str, ...] = ()

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


# -- the sketch ---------------------------------------------------------------



# Finding prefix -> reviewer, as in docs/glossary.md §2.1 (owner: docs/reviews/README.md).
FINDING_PREFIXES = {
    "SR": "spec-reviewer", "FC": "fact-checker", "CH": "constraints-hunter",
    "SEC": "security-reviewer", "UX": "ux-reviewer", "DL": "depictio-liaison",
    "DEP-T": "depictio-liaison (tooling)", "DOC": "doc-reviewer", "TA": "test-architect",
    "IE": "infra-engineer", "CR": "code-reviewer",
}


class Sketch:
    """Accumulates SVG fragments drawn with a hand-drawn wobble."""

    def __init__(self, width: float, height: float, theme: Theme = LIGHT, seed: int = 7) -> None:
        self.width = width
        self.height = height
        self.theme = theme
        self.t = theme
        self._rng = random.Random(seed)
        self._parts: list[str] = []

    def raw(self, fragment: str) -> None:
        """Append raw SVG (for the rare mark no helper draws)."""
        self._parts.append(fragment)

    # -- primitives -----------------------------------------------------------

    def _jitter(self, amount: float) -> float:
        return self._rng.uniform(-amount, amount)

    def _wobble(self, x1: float, y1: float, x2: float, y2: float, amount: float) -> str:
        """One stroke as a cubic bezier whose control points wander off the line.

        Bending the curve rather than moving the endpoints keeps corners meeting
        while edges still bow.
        """
        cx1 = x1 + (x2 - x1) / 3 + self._jitter(amount)
        cy1 = y1 + (y2 - y1) / 3 + self._jitter(amount)
        cx2 = x1 + 2 * (x2 - x1) / 3 + self._jitter(amount)
        cy2 = y1 + 2 * (y2 - y1) / 3 + self._jitter(amount)
        sx, sy = x1 + self._jitter(amount / 2), y1 + self._jitter(amount / 2)
        ex, ey = x2 + self._jitter(amount / 2), y2 + self._jitter(amount / 2)
        return f"M{sx:.1f},{sy:.1f} C{cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {ex:.1f},{ey:.1f}"

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        width: float = 1.7,
        colour: str | None = None,
        amount: float = 2.0,
        dashed: bool = False,
        passes: int = 2,
    ) -> None:
        colour = colour or self.t.ink
        dash = ' stroke-dasharray="9 7"' if dashed else ""
        for _ in range(passes):
            d = self._wobble(x1, y1, x2, y2, amount)
            self._parts.append(
                f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
                f'stroke-linecap="round"{dash}/>'
            )

    def rect(self, box: Box, *, colour: str | None = None, dashed: bool = False, rx: float = 6) -> None:
        # Fill first as a plain rounded rect: a wobbling fill edge reads as a
        # smudge, a wobbling outline on top reads as a pen stroke.
        fill = self.t.fill(box.fill)
        if fill != "none":
            self._parts.append(
                f'<rect x="{box.x:.1f}" y="{box.y:.1f}" width="{box.w:.1f}" '
                f'height="{box.h:.1f}" rx="{rx}" fill="{fill}"/>'
            )
        for x1, y1, x2, y2 in (
            (box.x, box.y, box.right, box.y),
            (box.right, box.y, box.right, box.bottom),
            (box.right, box.bottom, box.x, box.bottom),
            (box.x, box.bottom, box.x, box.y),
        ):
            self.line(x1, y1, x2, y2, amount=1.6, colour=colour, dashed=dashed)

    def frame(self, x: float, y: float, w: float, h: float, *, fill: str = "surface",
              colour: str | None = None, dashed: bool = False) -> Box:
        """A titleless sketched panel: a place to draw inside."""
        b = Box(x, y, w, h, fill)
        self.rect(b, colour=colour, dashed=dashed)
        return b

    def poly(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str = "none",
        colour: str | None = None,
        width: float = 1.5,
        amount: float = 0.8,
        close: bool = True,
        passes: int = 1,
    ) -> None:
        """A filled polygon (plain fill) under a wobbly single-pass outline."""
        f = self.t.fill(fill)
        if f != "none" and close:
            d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in points) + " Z"
            self._parts.append(f'<path d="{d}" fill="{f}" stroke="none"/>')
        pts = [*points, points[0]] if close else points
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.line(x1, y1, x2, y2, colour=colour, width=width, amount=amount, passes=passes)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, *, fill: str = "none",
                colour: str | None = None, width: float = 1.5, n: int = 28) -> None:
        pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.poly(pts, fill=fill, colour=colour, width=width, amount=0.35)

    def circle(self, cx: float, cy: float, r: float, **kw) -> None:
        self.ellipse(cx, cy, r, r, **kw)

    def dot(self, cx: float, cy: float, r: float = 5, *, colour: str | None = None) -> None:
        """A solid dot, no outline, so it reads as ink rather than a shape."""
        self._parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:g}" fill="{colour or self.t.ink}"/>')

    def arrow(self, x1: float, y1: float, x2: float, y2: float, *, dashed: bool = False,
              colour: str | None = None, width: float = 1.7) -> None:
        self.line(x1, y1, x2, y2, dashed=dashed, colour=colour, width=width)
        self._head(x1, y1, x2, y2, colour)

    def _head(self, x1: float, y1: float, x2: float, y2: float, colour: str | None) -> None:
        angle = math.atan2(y2 - y1, x2 - x1)
        for sign in (1, -1):
            h = angle + sign * math.radians(28)
            self.line(x2, y2, x2 - 14 * math.cos(h), y2 - 14 * math.sin(h), amount=1.0, colour=colour, passes=1)

    def arc(self, x1: float, y1: float, x2: float, y2: float, *, lift: float = -40,
            colour: str | None = None, dashed: bool = False, head: bool = True, width: float = 1.7) -> None:
        """A bowed arrow, for a relation that hops over what lies between.

        ``lift`` is the sideways bulge in pixels; negative bows upwards for a
        left-to-right arc.
        """
        colour = colour or self.t.ink
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1.0
        qx, qy = mx + lift * (-dy / norm), my + lift * (dx / norm)
        n = 24
        pts = [
            ((1 - t) ** 2 * x1 + 2 * (1 - t) * t * qx + t**2 * x2, (1 - t) ** 2 * y1 + 2 * (1 - t) * t * qy + t**2 * y2)
            for t in (i / n for i in range(n + 1))
        ]
        dash = ' stroke-dasharray="9 7"' if dashed else ""
        for _ in range(2):
            d = " ".join(
                f"{'M' if i == 0 else 'L'}{px + self._jitter(1.1):.1f},{py + self._jitter(1.1):.1f}"
                for i, (px, py) in enumerate(pts)
            )
            self._parts.append(
                f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"{dash}/>'
            )
        if head:
            (ax, ay), (bx, by) = pts[-3], pts[-1]
            self._head(ax, ay, bx, by, colour)

    def shade(self, x: float, y: float, w: float, h: float, *, fill: str, opacity: float = 0.6,
              colour: str | None = None, dashed: bool = False) -> None:
        """A translucent band for a span or a zone; marks underneath stay readable."""
        self._parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" '
            f'fill="{self.t.fill(fill)}" fill-opacity="{opacity}"/>'
        )
        if colour:
            for x1, y1, x2, y2 in ((x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)):
                self.line(x1, y1, x2, y2, amount=1.0, width=1.3, colour=colour, passes=1, dashed=dashed)

    def text(self, x: float, y: float, content: str, *, size: float = 16, colour: str | None = None,
             anchor: str = "middle", weight: str = "normal") -> None:
        colour = colour or self.t.ink
        self._parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'fill="{colour}" text-anchor="{anchor}" font-weight="{weight}">{_spans(content, size)}</text>'
        )

    def text_rotated(self, x: float, y: float, content: str, *, rotate: float, size: float = 12,
                     colour: str | None = None, anchor: str = "middle") -> None:
        self._parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'fill="{colour or self.t.dim}" text-anchor="{anchor}" '
            f'transform="rotate({rotate:.0f} {x:.1f} {y:.1f})">{_spans(content, size)}</text>'
        )

    def box(self, box: Box, *, colour: str | None = None, dashed: bool = False) -> None:
        self.rect(box, colour=colour, dashed=dashed)
        self.text(box.cx, box.y + 27, box.title, size=18, weight="bold")
        for i, ln in enumerate(box.lines):
            self.text(box.cx, box.y + 51 + i * 21, ln, size=14, colour=self.t.dim)

    def heading(self, x: float, y: float, title: str, subtitle: str = "") -> None:
        self.text(x, y, title, size=27, anchor="start")
        if subtitle:
            self.text(x, y + 28, subtitle, size=15.5, colour=self.t.dim, anchor="start")

    def prefix_key(self, x: float, y: float, prefixes: tuple[str, ...], *, size: float = 13.5) -> None:
        """One line naming the reviewer behind each finding prefix used in the figure (glossary §2.1)."""
        parts = " · ".join(f"{p} {FINDING_PREFIXES[p]}" for p in prefixes)
        self.text(x, y, f"IDs: {parts}", size=size, anchor="start", colour=self.t.dim)

    def step(self, cx: float, y: float, n: int, label: str, *, size: float = 19) -> None:
        """A numbered caption under a pictogram: ``1 · label``."""
        self.text(cx, y, f"{n} · {label}", size=size)

    # -- marks ----------------------------------------------------------------

    def tick(self, cx: float, cy: float, *, size: float = 8, colour: str | None = None, width: float = 2.4) -> None:
        """A check mark: passed, verified."""
        c = colour or self.t.good
        self.line(cx - size, cy, cx - size / 3, cy + size * 0.8, colour=c, width=width, passes=1, amount=0.6)
        self.line(cx - size / 3, cy + size * 0.8, cx + size, cy - size, colour=c, width=width, passes=1, amount=0.6)

    def cross(self, cx: float, cy: float, *, size: float = 11, colour: str | None = None) -> None:
        """The "this does not happen" mark."""
        c = colour or self.t.accent
        self.line(cx - size, cy - size, cx + size, cy + size, colour=c, amount=1.2, passes=1, width=2)
        self.line(cx - size, cy + size, cx + size, cy - size, colour=c, amount=1.2, passes=1, width=2)

    def warning(self, cx: float, cy: float, *, size: float = 11) -> None:
        self.poly([(cx, cy - size), (cx + size, cy + size * 0.8), (cx - size, cy + size * 0.8)],
                  fill="yellow", colour=self.t.warn)
        self.text(cx, cy + size * 0.6, "!", size=size * 1.2, weight="bold", colour=self.t.warn)

    def hourglass(self, cx: float, cy: float, *, size: float = 9) -> None:
        self.poly([(cx - size, cy - size), (cx + size, cy - size), (cx, cy)], fill="yellow")
        self.poly([(cx, cy), (cx + size, cy + size), (cx - size, cy + size)], fill="yellow")

    def lock(self, cx: float, cy: float, size: float = 11, *, fill: str = "violet") -> None:
        w, h = size * 1.5, size * 1.1
        top = cy - h / 2 + size * 0.25
        r = w * 0.32
        ink = self.t.ink
        self._parts.append(
            f'<path d="M{cx - r:.1f},{top:.1f} V{top - size * 0.45:.1f} a{r:.1f},{r:.1f} 0 0 1 {2 * r:.1f},0 '
            f'V{top:.1f}" fill="none" stroke="{ink}" stroke-width="1.6" stroke-linecap="round"/>'
        )
        self._parts.append(
            f'<rect x="{cx - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2.5" '
            f'fill="{self.t.fill(fill)}" stroke="{ink}" stroke-width="1.5"/>'
        )
        self._parts.append(f'<circle cx="{cx:.1f}" cy="{top + h / 2:.1f}" r="1.6" fill="{ink}"/>')

    def cog(self, cx: float, cy: float, r: float = 9, *, fill: str = "surface") -> None:
        for k in range(8):
            a = k * math.pi / 4
            self.line(cx + r * math.cos(a), cy + r * math.sin(a), cx + (r + 5) * math.cos(a),
                      cy + (r + 5) * math.sin(a), amount=0.3, passes=1, width=3)
        self.circle(cx, cy, r, fill=fill)
        self.circle(cx, cy, r * 0.38)

    # -- objects (draw the thing, not a box naming it) ------------------------

    def page(self, x: float, y: float, w: float, h: float, *, fill: str = "surface", lines: int = 3) -> None:
        """A sheet with a folded corner and a few ruled lines."""
        fold = min(12.0, w * 0.3)
        self.poly([(x, y), (x + w - fold, y), (x + w, y + fold), (x + w, y + h), (x, y + h)], fill=fill)
        self.poly([(x + w - fold, y), (x + w - fold, y + fold), (x + w, y + fold)], close=False)
        for i in range(lines):
            ly = y + h * 0.35 + i * (h * 0.17)
            if ly < y + h - 5:
                self.line(x + 5, ly, x + w - 6, ly, colour=self.t.muted, amount=0.4, passes=1, width=1.2)

    def folder(self, x: float, y: float, w: float, h: float, *, fill: str = "yellow", label: str = "") -> Box:
        tab = 9
        self.poly([(x, y + tab), (x + w * 0.34, y + tab), (x + w * 0.40, y), (x + w * 0.62, y),
                   (x + w * 0.68, y + tab), (x + w, y + tab), (x + w, y + h), (x, y + h)], fill=fill, amount=1.0)
        if label:
            self.text(x + w / 2, y + h / 2 + tab / 2 + 5, label, size=13)
        return Box(x, y, w, h, fill, label)

    def magnifier(self, cx: float, cy: float, r: float, *, fill: str = "surface") -> None:
        self.circle(cx, cy, r, fill=fill, width=2.2)
        self.line(cx + r * 0.72, cy + r * 0.72, cx + r * 1.7, cy + r * 1.7, width=5, amount=0.8, passes=1)

    def _traffic(self, x: float, y: float, step: float = 15) -> None:
        for i, c in enumerate(("#ff8787", "#ffd43b", "#69db7c")):
            self.dot(x + i * step, y, 4.5, colour=c)

    def browser(self, x: float, y: float, w: float, h: float, *, url: str = "") -> Box:
        frame = Box(x, y, w, h, "surface")
        self.rect(frame)
        self.line(x, y + 28, x + w, y + 28, amount=0.8, passes=1)
        self._traffic(x + 16, y + 14)
        if url:
            self.text(x + 66, y + 19, url, size=12, anchor="start", colour=self.t.dim)
        return frame

    def terminal(self, x: float, y: float, w: float, h: float, lines: tuple[str, ...] = (),
                 *, size: float = 13, line_h: float = 21) -> Box:
        """A dark terminal window; ``lines`` are typed in monospace."""
        self._parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5" fill="{self.t.term_bg}"/>'
        )
        self.rect(Box(x, y, w, h))
        self._traffic(x + 15, y + 14, 14)
        for i, ln in enumerate(lines):
            ty = y + 44 + i * line_h
            self._parts.append(
                f'<text x="{x + 14:.1f}" y="{ty:.1f}" font-family="{MONO}" font-size="{size}" '
                f'fill="{self.t.term_ink}" xml:space="preserve">{escape(ln)}</text>'
            )
        return Box(x, y, w, h)

    def chip(self, x: float, y: float, w: float, label: str, *, fill: str = "work", h: float = 40) -> Box:
        """A worker task: a small card with a cog in the corner."""
        b = Box(x, y, w, h, fill)
        self.rect(b)
        self.cog(x + w - 15, y + 14, 4.5)
        self.text(x + 9, y + h - 12, label, size=12.5, anchor="start")
        return b

    def button(self, x: float, y: float, w: float, label: str, *, fill: str = "done", h: float = 30) -> Box:
        b = Box(x, y, w, h, fill)
        self.rect(b)
        self.text(b.cx, y + h / 2 + 5, label, size=13.5, weight="bold")
        return b

    def bucket(self, cx: float, top: float, w: float, h: float, *, fill: str = "orange") -> None:
        body = [(cx - w / 2, top), (cx + w / 2, top), (cx + w / 2 - 12, top + h), (cx - w / 2 + 12, top + h)]
        self.poly(body, fill=fill, amount=1.2)
        self.ellipse(cx, top, w / 2, 9, fill=fill)

    def envelope(self, x: float, y: float, w: float, h: float, *, fill: str = "surface") -> None:
        """A letter: the inbox, an e-mailed link."""
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill)
        self.poly([(x, y), (x + w / 2, y + h * 0.55), (x + w, y)], close=False)

    def link(self, cx: float, cy: float, size: float = 14, *, colour: str | None = None) -> None:
        """Two interlocked chain links: a (magic) link."""
        c = colour or self.t.ink
        for dx, rot in ((-size * 0.45, -35), (size * 0.45, -35)):
            self._parts.append(
                f'<rect x="{cx + dx - size * 0.55:.1f}" y="{cy - size * 0.28:.1f}" width="{size * 1.1:.1f}" '
                f'height="{size * 0.56:.1f}" rx="{size * 0.28:.1f}" fill="none" stroke="{c}" stroke-width="2.2" '
                f'transform="rotate({rot} {cx + dx:.1f} {cy:.1f})"/>'
            )

    def phone(self, x: float, y: float, w: float, h: float, *, fill: str = "surface") -> Box:
        """A phone held upright; returns the screen box to draw inside."""
        self._parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{w * 0.16:.1f}" '
            f'fill="{self.t.fill("grey")}"/>'
        )
        self.rect(Box(x, y, w, h), rx=w * 0.16)
        self.line(x + w * 0.38, y + 10, x + w * 0.62, y + 10, width=3, amount=0.3, passes=1)
        screen = Box(x + 7, y + 20, w - 14, h - 38, fill)
        self.rect(screen, colour=self.t.muted)
        self.circle(x + w / 2, y + h - 10, 4)
        return screen

    def gauge(self, cx: float, cy: float, r: float, used: float, budget: float, *, start: float = 0,
              label: str = "") -> None:
        """A half-dial in percent of a window: grey up to ``start``, green from
        ``start`` to ``budget`` (the allowance), needle at ``used``.

        The picture answers "how much is left" without reading the numbers.
        """
        def at(p: float, rr: float) -> tuple[float, float]:
            a = math.pi * (1 - p / 100)
            return cx + rr * math.cos(a), cy - rr * math.sin(a)

        def band(p0: float, p1: float, fill: str) -> None:
            n = 24
            outer = [at(p0 + (p1 - p0) * i / n, r) for i in range(n + 1)]
            inner = [at(p1 - (p1 - p0) * i / n, r * 0.72) for i in range(n + 1)]
            d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in outer + inner) + " Z"
            self._parts.append(f'<path d="{d}" fill="{self.t.fill(fill)}" stroke="none"/>')

        if start > 0:
            band(0, start, "bar_grey")
        band(start, budget, "bar_green")
        # dial outline
        arc_pts = [at(p, r) for p in range(0, 101, 5)]
        self.poly(arc_pts, close=False, width=1.8)
        self.line(cx - r, cy, cx + r, cy, amount=0.6, passes=1)
        for p in (0, 25, 50, 75, 100):
            (x1, y1), (x2, y2) = at(p, r), at(p, r * 0.86)
            self.line(x1, y1, x2, y2, amount=0.2, passes=1, width=1.3)
            lx, ly = at(p, r + 15)
            self.text(lx, ly + 4, f"{p}", size=11, colour=self.t.dim)
        nx, ny = at(used, r * 0.82)
        self.line(cx, cy, nx, ny, width=3, amount=0.4, passes=1, colour=self.t.accent)
        self.dot(cx, cy, 5)
        if label:
            self.text(cx, cy + 24, label, size=13, colour=self.t.dim)

    # -- Spectio glyphs -------------------------------------------------------

    def gate(self, cx: float, base: float, w: float = 70, h: float = 60, *, state: str = "closed") -> None:
        """A QC gate: two posts and a striped boom; ``state`` closed/open/passed.

        Closed = boom across (the run waits). Open = boom raised. Passed = raised
        with a tick over it.
        """
        post_w = 9
        lx, rx = cx - w / 2, cx + w / 2 - post_w
        for px in (lx, rx):
            self.poly([(px, base), (px, base - h), (px + post_w, base - h), (px + post_w, base)], fill="grey")
        by = base - h * 0.62
        if state == "closed":
            pts = [(lx + post_w, by - 6), (rx, by - 6), (rx, by + 6), (lx + post_w, by + 6)]
            self.poly(pts, fill="yellow", width=1.7)
            seg = (rx - lx - post_w) / 5
            for i in range(1, 5, 2):
                x0 = lx + post_w + i * seg
                self.poly([(x0, by - 6), (x0 + seg, by - 6), (x0 + seg, by + 6), (x0, by + 6)], fill="#c92a2a" if self.t is LIGHT else "#a33a3a", amount=0.4)
        else:
            hx, hy = lx + post_w / 2, by
            ang = math.radians(-68)
            L = w * 0.95
            ex, ey = hx + L * math.cos(ang), hy + L * math.sin(ang)
            nx, ny = -math.sin(ang) * 6, math.cos(ang) * 6
            self.poly([(hx - nx, hy - ny), (ex - nx, ey - ny), (ex + nx, ey + ny), (hx + nx, hy + ny)], fill="yellow")
            if state == "passed":
                self.tick(cx + 8, base - h * 0.45, size=11)
        self.line(cx - w / 2 - 12, base, cx + w / 2 + 12, base, width=1.8, amount=0.8, passes=1)

    def hpc_node(self, x: float, y: float, w: float = 54, h: float = 70, *, busy: int = 3, slots: int = 4) -> None:
        """A rack server: ``slots`` blades, ``busy`` of them lit."""
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="grey")
        sh = (h - 10) / slots
        for i in range(slots):
            by = y + 5 + i * sh
            self.poly([(x + 5, by), (x + w - 5, by), (x + w - 5, by + sh - 4), (x + 5, by + sh - 4)],
                      fill="bar_blue" if i < busy else "surface", amount=0.4, width=1.2)
            self.dot(x + 11, by + (sh - 4) / 2, 2.6, colour=self.t.good if i < busy else self.t.muted)

    def k8s_pod(self, cx: float, cy: float, r: float = 22, *, fill: str = "blue") -> None:
        """A pod as a hexagon with a cube inside."""
        pts = [(cx + r * math.cos(math.pi / 6 + k * math.pi / 3), cy + r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
        self.poly(pts, fill=fill, width=1.7)
        s = r * 0.42
        self.poly([(cx, cy - s), (cx + s, cy - s / 2), (cx, cy), (cx - s, cy - s / 2)], amount=0.3, width=1.2)
        self.poly([(cx - s, cy - s / 2), (cx, cy), (cx, cy + s), (cx - s, cy + s / 2)], amount=0.3, width=1.2)
        self.poly([(cx + s, cy - s / 2), (cx, cy), (cx, cy + s), (cx + s, cy + s / 2)], amount=0.3, width=1.2)

    def runner(self, x: float, y: float, w: float = 92, h: float = 62, *, label: str = "runner") -> Box:
        """The Spectio runner: a small box with an outbound-only antenna."""
        b = Box(x, y, w, h, "violet")
        self.rect(b)
        self.cog(x + 22, y + h / 2, 8, fill="violet")
        self.text(x + 40, y + h / 2 + 5, label, size=14, anchor="start")
        # antenna with outbound waves: it dials out, nothing dials in
        ax = x + w - 14
        self.line(ax, y, ax, y - 18, width=1.6, amount=0.3, passes=1)
        self.dot(ax, y - 20, 3)
        for k, rr in enumerate((8, 14)):
            self.arc(ax + 2, y - 20 - rr * 0.6, ax + 2, y - 20 + rr * 0.6, lift=-rr * 0.7, head=False, width=1.2,
                     colour=self.t.dim)
        return b

    def pipeline(self, x: float, y: float, labels: tuple[str, ...], *, w: float = 64, h: float = 34,
                 gap: float = 22, fills: tuple[str, ...] | None = None) -> list[Box]:
        """A chain of task cards joined by short arrows."""
        out = []
        for i, lab in enumerate(labels):
            bx = x + i * (w + gap)
            b = Box(bx, y, w, h, (fills[i] if fills else "work"))
            self.rect(b)
            self.text(b.cx, y + h / 2 + 5, lab, size=12.5)
            if i:
                self.arrow(bx - gap + 3, y + h / 2, bx - 3, y + h / 2)
            out.append(b)
        return out

    def task_strip(self, x: float, y: float, groups: tuple[tuple[int, str, str], ...], *, cell: float = 11,
                   gap: float = 2, h: float = 22, label_size: float = 14) -> float:
        """Tasks drawn to scale: one cell per task, grouped as (count, fill, label).

        Returns the right edge. Each group's label sits under its span.
        """
        cx = x
        for count, fill, label in groups:
            start = cx
            for _ in range(count):
                self._parts.append(
                    f'<rect x="{cx:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{h:.1f}" rx="2" '
                    f'fill="{self.t.fill(fill)}" stroke="{self.t.ink}" stroke-width="0.8"/>'
                )
                cx += cell + gap
            if label:
                self.text((start + cx - gap) / 2, y + h + 20, label, size=label_size, colour=self.t.dim)
            cx += gap * 4
        return cx

    def svg(self) -> str:
        body = "\n  ".join(self._parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:g}" height="{self.height:g}" '
            f'viewBox="0 0 {self.width:g} {self.height:g}">\n'
            f'  <rect width="{self.width:g}" height="{self.height:g}" fill="{self.t.bg}"/>\n'
            f"  {body}\n</svg>\n"
        )


# -- output -------------------------------------------------------------------


def _png_host_page(svg: str) -> str:
    """An HTML shell that inlines the SVG and declares the bundled Excalifont.

    An <img>-embedded SVG cannot see an @font-face, and a file:// SVG renders
    with whatever fonts are installed, so the PNG is taken from this page.
    """
    face = f"@font-face{{font-family:'Excalifont';src:url('{SKETCH_TTF.resolve().as_uri()}') format('truetype');}}"
    return (
        "<!doctype html><meta charset='utf-8'><style>"
        f"{face}html,body{{margin:0;padding:0}}svg{{display:block}}</style><body>{svg}</body>"
    )


async def _render_png(svg: str, png_path: Path, width: float, height: float) -> None:
    from playwright.async_api import async_playwright

    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as fh:
        fh.write(_png_host_page(svg))
        host = Path(fh.name)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": int(width), "height": int(height)}, device_scale_factor=2)
            await page.goto(host.as_uri())
            await page.evaluate("document.fonts.ready")
            await page.wait_for_timeout(300)
            await page.screenshot(path=str(png_path))
            await browser.close()
    finally:
        host.unlink(missing_ok=True)


def _quantize(png_path: Path) -> None:
    """Shrink a PNG to 256 colours with ImageMagick (about 3x smaller); a no-op without it.

    Flat pastel fills and thin ink survive palette reduction unchanged to the eye.
    """
    import shutil
    import subprocess

    exe = shutil.which("magick") or shutil.which("convert")
    if exe:
        subprocess.run([exe, str(png_path), "-strip", "-colors", "256", f"PNG8:{png_path}"], check=True)


def write(sketch: Sketch, out_dir: Path, name: str, *, png: bool = True) -> Path:
    """Write ``<out_dir>/<name>.svg`` and, unless ``png=False``, its PNG."""
    if png and not SKETCH_TTF.exists():
        raise SystemExit(f"{SKETCH_TTF} is missing: set SPECTIO_SKETCH_TTF (tools/diagrams/FONT-LICENSE.md), or pass --no-png")
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / f"{name}.svg"
    svg = sketch.svg()
    svg_path.write_text(svg, encoding="utf-8")
    print(f"-> {svg_path.relative_to(REPO_ROOT) if svg_path.is_relative_to(REPO_ROOT) else svg_path}")
    if png:
        png_path = svg_path.with_suffix(".png")
        asyncio.run(_render_png(svg, png_path, sketch.width, sketch.height))
        _quantize(png_path)
        print(f"-> {png_path.relative_to(REPO_ROOT) if png_path.is_relative_to(REPO_ROOT) else png_path}")
    return svg_path


def write_themed(build, out_dir: Path, name: str, *, png: bool = True) -> None:
    """Render ``build(theme) -> Sketch`` once per palette: ``<name>_light.*``, ``<name>_dark.*``."""
    for theme in THEMES:
        write(build(theme), out_dir, f"{name}_{theme.name}", png=png)


def main_for(build, name: str) -> None:
    """Shared ``__main__`` for figure scripts: ``--no-png`` and ``--out DIR``."""
    import argparse

    ap = argparse.ArgumentParser(description=f"Render the {name} figure (light and dark).")
    ap.add_argument("--no-png", action="store_true", help="write the SVGs only")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args()
    write_themed(build, a.out, name, png=not a.no_png)
