#!/usr/bin/env python3
"""Named documentation screenshots: one registry, one command per shot.

The pattern is depictio's dev/playwright_debug/docs_screenshots.py (MIT,
0d1aa0a): a REGISTRY of named shots, `list` and `run`, a fixed viewport, and
light/dark WebP pairs embedded with #only-light / #only-dark.

During the design phase the shots are the UI canvas boards, rendered by
tools/canvas/render.js. Once the app exists, a shot's `render` switches to a
Playwright session against a running instance (same names, same files), so the
docs pages that embed them do not change.

    python3 tools/media/shots.py list
    python3 tools/media/shots.py run --shot review-gate
    python3 tools/media/shots.py run --all --theme light

The boards have no dark variant yet, so `--theme dark` is skipped for them
(the page then embeds the light file without a #only-light suffix).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "assets" / "shots"
BOARDS = REPO / "design" / "ui-canvas"


@dataclass(frozen=True)
class Shot:
    name: str
    board: str  # design/ui-canvas/<board>.dc.html
    width: int
    height: int
    caption: str
    clicks: tuple[str, ...] = ()  # CSS selectors clicked before the capture
    themes: tuple[str, ...] = ("light",)  # boards: light only for now


REGISTRY: dict[str, Shot] = {
    s.name: s
    for s in (
        Shot("run-detail", "RunDetail", 1440, 1180, "A running nf-core/rnaseq run: stages, gates, busiest processes, lineage"),
        Shot("review-gate", "Review", 1440, 1180, "The review screen of a QC gate: checks, viewer, AI suggestion, pending changes"),
        Shot("review-gate-phone", "MReview", 390, 844, "The same gate on a phone"),
    )
}


def render(shot: Shot, theme: str) -> Path | None:
    if theme not in shot.themes:
        print(f"skip {shot.name} [{theme}]: board has no {theme} variant")
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{shot.name}_{theme}.webp"
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "shot.png"
        cmd = ["node", str(REPO / "tools/canvas/render.js"), str(BOARDS / f"{shot.board}.dc.html"),
               str(shot.width), str(shot.height), str(png), *shot.clicks]
        subprocess.run(cmd, check=True, capture_output=True, cwd=REPO)
        # lossless keeps UI text crisp; method 6 = smallest file
        subprocess.run(["convert", str(png), "-define", "webp:lossless=true", "-define", "webp:method=6",
                        str(out)], check=True)
    print(f"-> {out.relative_to(REPO)}  ({out.stat().st_size // 1024} KB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Documentation screenshots")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--shot", choices=sorted(REGISTRY))
    g.add_argument("--all", action="store_true")
    r.add_argument("--theme", choices=["light", "dark", "both"], default="both")
    a = ap.parse_args()

    if a.cmd == "list":
        for s in REGISTRY.values():
            print(f"{s.name:20} {s.board + '.dc.html':24} {s.width}x{s.height}  {'/'.join(s.themes):10} {s.caption}")
        return
    shots = REGISTRY.values() if a.all else [REGISTRY[a.shot]]
    themes = ("light", "dark") if a.theme == "both" else (a.theme,)
    for s in shots:
        for t in themes:
            render(s, t)


if __name__ == "__main__":
    sys.exit(main())
