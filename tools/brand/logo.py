"""Draw the complete Spectio logo (emblem + "Spectio" wordmark) as two SVGs, light and dark.

The wordmark is Outfit SemiBold outlined into paths, so the SVG renders the same everywhere
(GitHub, PyPI) without the font. Layout follows the app bar (design/ui-canvas/LiteTopbar.dc.html):
emblem 44 x 22 for a 23 px wordmark, 9 px apart, letter-spacing -0.035 em, the emblem's box 1 px
above the wordmark baseline. Outfit's one kerning pair in the word (c-t, -8 units) is applied by hand,
as a browser would.

    python3 tools/brand/logo.py Outfit-600.ttf   # writes docs/assets/brand/logo_{light,dark}.svg

Outfit 600 (OFL): https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4e6yC4E.ttf
Needs fontTools: uv run --with fonttools python3 tools/brand/logo.py <ttf>
"""

import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

EMBLEM = [  # same paths as docs/assets/brand/emblem.svg (viewBox 0 0 200 100)
    ("#5A4FCF", "M86.09 94.24L4.17 94.24A96 96 0 0 1 28.17 36.31Z"),
    ("#8B5CF6", "M94.24 86.09L36.31 28.17A96 96 0 0 1 94.24 4.17Z"),
    ("#EC5F87", "M105.76 86.09L105.76 4.17A96 96 0 0 1 163.69 28.17Z"),
    ("#F9A947", "M113.91 94.24L171.83 36.31A96 96 0 0 1 195.83 94.24Z"),
]
INK = {"light": "#0F1020", "dark": "#FFFFFF"}
SIZE, EMBLEM_W, GAP, TRACK, PAD, LIFT = 23.0, 44.0, 9.0, -0.035, 2.0, 1.0
KERN = {("c", "t"): -8}  # Outfit GPOS, font units


def wordmark(font):
    """Outline 'Spectio' at SIZE px with the app's tracking; return (path data, width, ascent, descent)."""
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    k = SIZE / font["head"].unitsPerEm
    pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    bounds, x = BoundsPen(glyphs), 0.0
    for ch, nxt in zip("Spectio", "pectio "):
        name = cmap[ord(ch)]
        # font units, y up -> px, y down; the baseline is y = 0
        for p in (pen, bounds):
            glyphs[name].draw(TransformPen(p, (k, 0, 0, -k, x, 0)))
        x += (glyphs[name].width + KERN.get((ch, nxt), 0)) * k + TRACK * SIZE
    x -= TRACK * SIZE
    _, y_min, _, y_max = bounds.bounds  # y down: y_min is the top of the tallest letter
    return pen.getCommands(), x, -y_min, y_max


def main():
    font = TTFont(sys.argv[1])
    d, word_w, ascent, descent = wordmark(font)
    eh = EMBLEM_W / 2  # the emblem is a half disc: height = width / 2
    top = max(ascent, eh + LIFT)
    w, h = PAD * 2 + EMBLEM_W + GAP + word_w, PAD * 2 + top + descent
    base = PAD + top  # shared baseline: the emblem's horizon and the wordmark's
    emblem = "".join(f'<path fill="{c}" d="{p}"/>' for c, p in EMBLEM)
    out = Path(__file__).resolve().parents[2] / "docs/assets/brand"
    for mode, ink in INK.items():
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
            f'width="{w * 4:.0f}" height="{h * 4:.0f}" role="img" aria-label="Spectio">'
            f'<g transform="translate({PAD} {base - eh - LIFT:.2f}) scale({EMBLEM_W / 200})">{emblem}</g>'
            f'<path fill="{ink}" transform="translate({PAD + EMBLEM_W + GAP:.2f} {base:.2f})" d="{d}"/>'
            "</svg>\n"
        )
        (out / f"logo_{mode}.svg").write_text(svg)
        print(f"-> docs/assets/brand/logo_{mode}.svg")


if __name__ == "__main__":
    main()
