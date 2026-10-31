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
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sanitize  # noqa: E402

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
    themes: tuple[str, ...] = ("light",)  # boards: light only for now; live screens: both
    live: tuple[str, ...] | None = None  # a live page: steps of live.js; `board` is its path


APP_LAUNCH = ("fill:Pipeline=$SPECTIO_DEMO_PIPELINE", "click:Load", "wait:no parameter schema",
              "click:Add a parameter", "fill:Name, row 1=outdir", "fill:Value, row 1=results")

REGISTRY: dict[str, Shot] = {
    s.name: s
    for s in (
        Shot("run-detail", "RunDetail", 1440, 1180, "A running nf-core/rnaseq run: stages, gates, busiest processes, lineage"),
        Shot("review-gate", "Review", 1440, 1180, "The review screen of a QC gate: checks, viewer, AI suggestion, pending changes"),
        Shot("review-gate-phone", "MReview", 390, 844, "The same gate on a phone"),
        Shot("overview", "Overview", 1440, 1180, "Overview: runs that need attention, gates waiting, environments"),
        Shot("launch", "Launch", 1440, 1180, "Launching a pipeline: parameters from its schema, samplesheet, environment, gates"),
        Shot("runs", "RunsTable", 1440, 1180, "Every run in one table, with stage, gates and cost"),
        Shot("review-queue", "ReviewQueue", 1440, 1180, "The review queue: gates waiting for a decision"),
        Shot("environments", "Environments", 1440, 1180, "Environments: SLURM and Kubernetes runners, capacity, health"),
        Shot("admin-plugins", "AdminPlugins", 1440, 1180, "Administration: plugins for engines, auth, storage and notifications"),
        Shot("lite-run-detail", "LiteRunDetail", 1440, 1180, "0.0.1: a running nf-core/rnaseq run with its detected stages, each opening to its processes, its head in tmux, Cancel and Copy"),
        Shot("lite-launch", "LiteLaunch", 1440, 1180, "0.0.1: launching a pipeline from its directory, the form built from nextflow_schema.json, here prefilled from an earlier run"),
        Shot("lite-runs", "LiteRuns", 1440, 1180, "0.0.1: every run with its state, workflow, tasks, start and duration"),
        Shot("lite-run-detail-phone", "MLiteRunDetail", 390, 844, "0.0.1: the same run on a phone"),
        # Live: from a running `spectio serve` at $SPECTIO_URL, with the synthetic Nextflow pipeline
        # copied to $SPECTIO_DEMO_PIPELINE (a path free of forbidden terms, fixtures.yaml).
        Shot("app-launch", "/launch", 1440, 1000, "0.0.1, live: the launch form with the synthetic Nextflow pipeline loaded",
             themes=("light", "dark"), live=APP_LAUNCH),
        Shot("app-launch-phone", "/launch", 390, 844, "0.0.1, live: the same launch form on a phone",
             themes=("light", "dark"), live=APP_LAUNCH),
        # P1 Task 20: the same serve, after one run of the synthetic pipeline with profile `test` has
        # finished; $SPECTIO_DEMO_RUN is its ID.
        Shot("app-home", "/", 1440, 1000, "0.0.1, live: Home, with the count cards, the runs that ended and the pipelines",
             live=("wait:Finished recently",)),
        Shot("app-runs", "/runs", 1440, 1000, "0.0.1, live: the runs list with its state filters",
             live=("wait:Duration",)),
        Shot("app-run-detail", "/runs/$SPECTIO_DEMO_RUN", 1440, 1180,
             "0.0.1, live: a finished run of the synthetic Nextflow pipeline, its processes and facts",
             live=("wait:65 / 65 tasks",)),
        Shot("app-run-detail-phone", "/runs/$SPECTIO_DEMO_RUN", 390, 844, "0.0.1, live: the same run on a phone",
             live=("wait:65 / 65 tasks",)),
        Shot("app-run-detail-failed", "/runs/$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: a failed run of the synthetic Nextflow pipeline, why it failed, open and folded sections",
             live=("wait:Why it failed",)),
    )
}


def render(shot: Shot, theme: str) -> Path | None:
    if theme not in shot.themes:
        print(f"skip {shot.name} [{theme}]: board has no {theme} variant")
        return None
    if shot.live is not None and "SPECTIO_URL" not in os.environ:
        print(f"skip {shot.name}: a live shot needs SPECTIO_URL (a running spectio serve)")
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{shot.name}_{theme}.webp"
    with tempfile.TemporaryDirectory() as tmp, sanitize.sanitised_boards(BOARDS) as boards:
        png, text = Path(tmp) / "shot.png", Path(tmp) / "page.txt"
        preload = ["node", "--require", str(Path(__file__).resolve().parent / "page_text.js")]
        if shot.live is None:
            cmd = [*preload, str(REPO / "tools/canvas/render.js"), str(boards / f"{shot.board}.dc.html"),
                   str(shot.width), str(shot.height), str(png), *shot.clicks]
        else:  # the page text is checked as it is shown: a live page is never rewritten
            # live.js reads $SPECTIO_URL and expands $VARS in the steps itself: no environment value goes into argv
            cmd = [*preload, str(Path(__file__).resolve().parent / "live.js"), shot.board,
                   str(shot.width), str(shot.height), str(png), *shot.live]
        subprocess.run(cmd, check=True, capture_output=True, cwd=REPO,
                       env={**os.environ, "SPECTIO_PAGE_TEXT": str(text), "SPECTIO_THEME": theme})
        found = sanitize.leaks(text.read_text(encoding="utf-8"))
        if found:
            sys.exit(f"{shot.name}: forbidden term visible in the rendered page: {found}")
        print(f"hygiene ok: {shot.name} (no forbidden term in the rendered page text)")
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
            print(f"{s.name:20} {s.board if s.live else s.board + '.dc.html':24} {s.width}x{s.height}  {'/'.join(s.themes):10} {s.caption}")
        return
    shots = REGISTRY.values() if a.all else [REGISTRY[a.shot]]
    themes = ("light", "dark") if a.theme == "both" else (a.theme,)
    for s in shots:
        for t in themes:
            render(s, t)


if __name__ == "__main__":
    sys.exit(main())
