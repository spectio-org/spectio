#!/usr/bin/env python3
"""The progress hook output in the docs build check: step D6, 2026-10-27.

Writes docs/assets/diagrams/d6-progress-hook-check_{light,dark}.{svg,png}.

Every value comes from the D6 runs of tools/docs/check.py on 49c75e1:
- with hooks/progress.py enabled: "build: progress hook output checked on 3 pages", "docs gate: 0 failure(s)";
- with the hook commented out of mkdocs.yml: 6 failures, 3 unrendered placeholders and 3 missing outputs.
The three pages are the ones whose sources carry a placeholder: index.md, roadmap/index.md (strip)
and progress/index.md (table). The markers are the ones check.py looks for.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 770


def _strip(s: Sketch, x: float, y: float, done: tuple[float, ...]) -> None:
    """The landing strip: one small bar per wave, filled to its share of done steps."""
    for i, share in enumerate(done):
        bx = x + i * 26
        s.shade(bx, y, 20, 46, fill="neutral", opacity=1)
        s.shade(bx, y + 46 * (1 - share), 20, 46 * share, fill="bar_green", opacity=1)


def _table(s: Sketch, x: float, y: float, w: float, rows: int) -> None:
    """The Progress table: a header row and ruled step rows."""
    s.shade(x, y, w, 14, fill="docs", opacity=1)
    for i in range(rows + 1):
        s.line(x, y + 14 + i * 12, x + w, y + 14 + i * 12, colour=s.t.muted, amount=0.3, passes=1, width=1.1)
    for cx in (x + w * 0.3, x + w * 0.62):
        s.line(cx, y, cx, y + 14 + rows * 12, colour=s.t.muted, amount=0.3, passes=1, width=1.1)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=66)
    t = theme
    s.heading(60, 62, "The docs build now checks what the progress hook drew",
              "tools/docs/check.py, build check, step D6 · 2026-10-27")

    # 1 -- the build ---------------------------------------------------------------
    s.terminal(60, 150, 330, 190, (
        "mkdocs build --strict",
        "hook: progress.py",
        "  reads pipeline.yaml",
        "  and state.json",
        "site written",
    ), size=13)
    s.cog(370, 132, 14, fill="work")
    s.step(225, 440, 1, "build the site")

    # 2 -- three pages, filled in by the hook ----------------------------------------
    pages = (("landing", "`index.md`"), ("roadmap", "`roadmap/index.md`"), ("Progress tab", "`progress/index.md`"))
    px0, py, pw, ph = 470, 150, 130, 170
    for i, (label, src) in enumerate(pages):
        px = px0 + i * 175
        s.page(px, py, pw, ph, fill="surface", lines=0)
        if i < 2:
            _strip(s, px + 14, py + 90, (1.0, 1.0, 0.6, 0.2))
        else:
            _table(s, px + 12, py + 70, pw - 26, 6)
        s.text(px + pw / 2, py + ph + 30, label, size=16)
        s.text(px + pw / 2, py + ph + 52, src, size=13, colour=t.dim)
    for i, label in enumerate(("strip", "strip", "table")):
        s.text(px0 + i * 175 + pw / 2, py + 50, label, size=14, colour=t.dim)
    s.arrow(400, 245, px0 - 12, 245)
    s.text(645, 120, "each placeholder comment becomes HTML", size=14, colour=t.dim)
    s.step(645, 440, 2, "the hook fills three pages")

    # 3 -- the check -----------------------------------------------------------------
    mx, my = 1130, 230
    s.magnifier(mx, my, 56, fill="docs")
    s.text(mx, my - 6, "built", size=14)
    s.text(mx, my + 14, "HTML", size=14)
    s.arrow(px0 + 2 * 175 + pw + 14, 245, mx - 66, 245)
    s.text(1010, 360, "placeholder comment left", size=15, anchor="start")
    s.text(1010, 384, "rendered marker missing", size=15, anchor="start")
    s.text(1026, 406, "`sp-waves`  or  `<th>Kind</th>`", size=13, anchor="start", colour=t.dim)
    s.step(1130, 440, 3, "`check_progress_hook()`")

    # 4 -- the outcome -----------------------------------------------------------------
    rx = 1360
    s.frame(rx, 150, 230, 90, fill="done")
    s.tick(rx + 32, 192, size=11)
    s.text(rx + 56, 186, "hook on", size=16, anchor="start", weight="bold")
    s.text(rx + 56, 212, "0 failures", size=15, anchor="start")
    s.frame(rx, 270, 230, 90, fill="problem")
    s.cross(rx + 32, 312, size=10)
    s.text(rx + 56, 306, "hook off", size=16, anchor="start", weight="bold")
    s.text(rx + 56, 332, "6 failures", size=15, anchor="start")
    s.arrow(1225, 210, rx - 10, 195)
    s.arrow(1225, 270, rx - 10, 312)
    s.step(rx + 115, 440, 4, "pass or fail")

    # 5 -- the evidence ------------------------------------------------------------------
    s.terminal(60, 490, 1530, 210, (
        "$ python3 tools/docs/check.py --only build        # hooks/progress.py commented out of mkdocs.yml",
        "::error::[build] unrendered progress placeholder in index.html (hooks/progress.py did not run)",
        "::error::[build] unrendered progress placeholder in progress/index.html (hooks/progress.py did not run)",
        "::error::[build] index.html has no rendered progress strip (hooks/progress.py), source index.md",
        "::error::[build] progress/index.html has no rendered progress table (hooks/progress.py), source progress/index.md",
        "docs gate: 6 failure(s)         with the hook back on: docs gate: 0 failure(s)",
    ), size=13.5, line_h=28)

    s.text(W - 60, H - 30, "source: tools/docs/check.py runs on 49c75e1, 2026-10-27; 4 of the 6 error lines shown",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "d6-progress-hook-check")
