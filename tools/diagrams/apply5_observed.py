#!/usr/bin/env python3
"""Figure for step APPLY5: runs started from a terminal in 0.0.1, before Thomas's 2026-10-28 decision and after.

Writes docs/assets/diagrams/apply5_observed_{light,dark}.{svg,png}.

Before (main at 9d0fa54): dev-environment-and-testing.md §15.1 (the terminal row: "no" in 0.0.1),
mvp-0.0.1.md §3 (runs started from a terminal deferred), P1 Task 21 (the bridges only as copies
bundled in the wheel).
After: architecture-plugins-and-packaging.md §13.8 (enabling it, the pointer file, discovery,
monitor only, publishing), dev-environment-and-testing.md §12 (Publishing) and §15.3 req. 12 (pointers
and launch directories are untrusted input), decision log 2026-10-28, inbox #65-#67, P1 Tasks 25 and 26.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 760
BX, AX, PW = 230, 930, 670  # before panel x, after panel x, panel width
ROWS = (130, 330, 530)  # top of each row


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=65)
    t = theme

    def note(x: float, y: float, *lines: str) -> None:
        for i, line in enumerate(lines):
            s.text(x, y + i * 21, line, size=14 if i == 0 else 13.5, anchor="start",
                   colour=t.ink if i == 0 else t.dim)

    s.heading(40, 52, "APPLY5 · runs started from a terminal in 0.0.1: before and after",
              "Thomas's decision of 2026-10-28 · architecture-plugins-and-packaging.md §13.8")

    s.shade(BX, 104, PW, 604, fill="neutral", opacity=0.5)
    s.text(BX + 20, 126, "before", size=22, anchor="start")
    s.shade(AX, 104, PW, 604, fill="done", opacity=0.3)
    s.text(AX + 20, 126, "after", size=22, anchor="start")

    labels = (("terminal runs", "what the user sees"), ("discovery", "how the server finds them"),
              ("the bridges", "where they come from"))
    for (title, sub), y in zip(labels, ROWS):
        s.text(40, y + 80, title, size=18, anchor="start", weight="bold")
        s.text(40, y + 104, sub, size=13.5, anchor="start", colour=t.dim)
        if y != ROWS[0]:
            s.line(40, y - 10, W - 40, y - 10, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- 1 what the user sees -------------------------------------------------------------------
    y = ROWS[0]
    s.terminal(BX + 30, y + 36, 250, 70, ("$ nextflow run nf-core/rnaseq",), size=12.5)
    s.cross(BX + 155, y + 140, size=12)
    s.text(BX + 176, y + 145, "not in the runs list", size=13, anchor="start", colour=t.dim)
    note(BX + 310, y + 56, "only runs launched from the UI",
         "a run typed by hand is invisible",
         "deferred, version not set (§15.1)")
    s.terminal(AX + 30, y + 30, 270, 70, ("$ nextflow run nf-core/rnaseq \\", "    -plugins nf-spectio@0.0.1"),
               size=12.5)
    b = s.browser(AX + 330, y + 30, 150, 96, url="127.0.0.1")
    s.chip(b.x + 14, b.cy - 4, 122, "terminal", fill="work", h=28)
    s.arrow(AX + 304, y + 66, b.x - 6, y + 66)
    note(AX + 500, y + 52, "monitor only:",
         "state, stages,",
         "tasks and logs;",
         "no Cancel (#65)")
    s.text(AX + 30, y + 140, "or once in ~/.nextflow/config; Snakemake: --logger spectio",
           size=13, anchor="start", colour=t.dim)

    # -- 2 discovery ------------------------------------------------------------------------------
    y = ROWS[1]
    f = s.folder(BX + 40, y + 36, 130, 96, fill="gate")
    s.text(f.x + 65, f.y + 50, "runs root", size=13.5)
    s.text(f.x + 65, f.y + 70, "run_<ULID>/", size=12, colour=t.dim)
    note(BX + 200, y + 56, "the server reads only run directories",
         "it created itself, under the runs root",
         "(§15.3 Where data lives)")
    s.page(AX + 30, y + 36, 170, 96, fill="surface", lines=0)
    s.text(AX + 115, y + 66, "~/.spectio/observed/", size=12)
    s.text(AX + 115, y + 88, "run_<ULID>.json", size=12.5)
    s.text(AX + 115, y + 110, "0600 · pointer", size=12, colour=t.dim)
    f2 = s.folder(AX + 250, y + 36, 150, 96, fill="gate")
    s.text(f2.x + 75, f2.y + 50, "launch dir", size=13.5)
    s.text(f2.x + 75, f2.y + 70, ".spectio/events", size=12, colour=t.dim)
    s.arrow(AX + 204, y + 84, f2.x - 6, y + 84)
    s.lock(AX + 225, y + 140, size=10)
    s.text(AX + 242, y + 145, "req. 12 checks on both", size=12.5, anchor="start", colour=t.dim)
    note(AX + 430, y + 52, "written by the bridge",
         "only if ~/.spectio exists;",
         "scanned when observed/ changes",
         "and at rebuild")

    # -- 3 the bridges --------------------------------------------------------------------------
    y = ROWS[2]
    s.bucket(BX + 90, y + 40, 90, 80, fill="orange")
    s.text(BX + 90, y + 148, "spectio wheel", size=13)
    note(BX + 180, y + 56, "copies bundled in the wheel",
         "the runner puts them on the run",
         "for UI launches only (P1 Task 21)")
    s.bucket(AX + 70, y + 40, 76, 70, fill="orange")
    s.text(AX + 70, y + 136, "wheel (UI)", size=12.5)
    s.page(AX + 150, y + 34, 150, 44, fill="work", lines=0)
    s.text(AX + 225, y + 61, "Nextflow registry", size=12.5)
    s.page(AX + 150, y + 92, 150, 44, fill="work", lines=0)
    s.text(AX + 225, y + 119, "PyPI → catalogue", size=12.5)
    s.text(AX + 225, y + 160, "names claimed by Thomas (#66)", size=12.5, colour=t.dim)
    note(AX + 330, y + 52, "nf-spectio: registry.nextflow.io",
         "snakemake-logger-plugin-spectio: PyPI,",
         "listed by the Snakemake plugin catalogue;",
         "released as dev-env §12 says;",
         "Claude builds and dry-runs only (Task 26)")

    s.text(40, H - 30, "Sources: dev-env §15.1, mvp-0.0.1.md §3 and P1 Task 21 at 9d0fa54 (before); "
                       "architecture §13.8, dev-env §12 and §15.3 req. 12, decision log 2026-10-28, inbox #65-#67, "
                       "P1 Tasks 25-26 (after) · tools/diagrams/apply5_observed.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply5_observed")
