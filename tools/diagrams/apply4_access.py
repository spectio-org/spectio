#!/usr/bin/env python3
"""Figure for step APPLY4: how 0.0.1 runs on the cluster before Thomas's 2026-10-28 answers, and after.

Writes docs/assets/diagrams/apply4_access_{light,dark}.{svg,png}.

Before (main at 6bf2fec, before PR #47): docs/plans/P1-walking-skeleton.md Tasks 10 and 11 and
Assumption 7 (the head as an `sbatch` head job, cancel by `scancel`; the tunnel typed by hand from
the start text of `spectio serve`; the UI polls every 5 s), architecture-plugins-and-packaging.md
§7.3 (the data directory, with SQLite, on node-local, non-purged storage).
After (PR #47, squash f51dca9, and its review fixes): dev-environment-and-testing.md §15.3 (head in
tmux on the login node, the state file `~/.spectio/server.json`, `spectio-open` or an SSH config
entry, Where data lives), schedulers-and-monitoring.md §3.1.1 (the head in the pane's foreground),
api-and-data-model.md §8.3 (SSE kept, decided by Thomas), decision log 2026-10-28 (both entries),
inbox #64 (the rebuildable index, assumed).
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1640, 900
BX, AX, PW = 230, 930, 670  # before panel x, after panel x, panel width
ROWS = (130, 310, 490, 670)  # top of each row
RH = 160


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=64)
    t = theme

    def cylinder(cx: float, top: float, w: float, h: float, fill: str, dashed: bool = False) -> None:
        """A disk: an upright drum."""
        rx = w / 2
        s.ellipse(cx, top + h, rx, 8, fill=fill)
        s.raw(f'<rect x="{cx - rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{t.fill(fill)}"/>')
        s.line(cx - rx, top, cx - rx, top + h, amount=0.4, passes=1, width=1.5)
        s.line(cx + rx, top, cx + rx, top + h, amount=0.4, passes=1, width=1.5)
        s.ellipse(cx, top, rx, 8, fill=fill)
        if dashed:
            s.rect(Box(cx - rx - 12, top - 18, w + 24, h + 34, "none"), colour=t.muted, dashed=True)

    def note(x: float, y: float, *lines: str) -> None:
        for i, line in enumerate(lines):
            s.text(x, y + i * 21, line, size=14 if i == 0 else 13.5, anchor="start",
                   colour=t.ink if i == 0 else t.dim)

    s.heading(40, 52, "APPLY4 · 0.0.1 on the EMBL cluster: before and after",
              "Thomas's answers of 2026-10-28, PR #47 and the fixes of its doc review · "
              "dev-environment-and-testing.md §15.3")

    s.shade(BX, 104, PW, 744, fill="neutral", opacity=0.5)
    s.text(BX + 20, 126, "before", size=22, anchor="start")
    s.shade(AX, 104, PW, 744, fill="done", opacity=0.3)
    s.text(AX + 20, 126, "after", size=22, anchor="start")

    labels = (("engine head", "where it runs"), ("laptop access", "how the tunnel opens"),
              ("database", "where SQLite lives"), ("live refresh", "how screens update"))
    for (title, sub), y in zip(labels, ROWS):
        s.text(40, y + 70, title, size=18, anchor="start", weight="bold")
        s.text(40, y + 94, sub, size=13.5, anchor="start", colour=t.dim)
        if y != ROWS[0]:
            s.line(40, y - 10, W - 40, y - 10, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- 1 the engine head ---------------------------------------------------------------------
    y = ROWS[0]
    s.hpc_node(BX + 40, y + 40, 58, 80, busy=1, slots=4)
    s.text(BX + 69, y + 142, "head job", size=13)
    note(BX + 140, y + 56, "an `sbatch` head job on a compute node",
         "it holds a SLURM allocation for the whole run",
         "Cancel: `scancel` of the head job")
    s.terminal(AX + 30, y + 34, 230, 92, ("tmux: spectio-<run>", "$ nextflow run ...", "head in the pane"), size=12.5)
    note(AX + 280, y + 56, "a tmux session on the login node",
         "the head in the pane's foreground, no `setsid`",
         "Cancel: Ctrl-C, then SIGTERM, SIGKILL",
         "`tmux attach` to watch or take over")

    # -- 2 laptop access -------------------------------------------------------------------------
    y = ROWS[1]
    s.terminal(BX + 30, y + 34, 300, 70, ("$ ssh -N -L 8080:127.0.0.1:8080 \\", "    user@login1"), size=12.5)
    s.warning(BX + 44, y + 128, size=10)
    note(BX + 360, y + 56, "typed by hand from the start text",
         "the user must know which login node",
         "and which port the server took")
    s.text(BX + 62, y + 133, "the wrong node: no server there", size=13, anchor="start", colour=t.dim)
    s.terminal(AX + 30, y + 30, 230, 56, ("$ spectio-open embl",), size=12.5)
    s.page(AX + 30, y + 98, 230, 54, fill="surface", lines=0)
    s.text(AX + 44, y + 120, "Host spectio-embl", size=12.5, anchor="start")
    s.text(AX + 44, y + 140, "LocalForward 127.0.0.1:<p> 127.0.0.1:<p>", size=10.5, anchor="start")
    note(AX + 280, y + 46, "`spectio-open <host> [--node <login node>]`",
         "reads `~/.spectio/server.json` to find the node,",
         "starts the server if none runs, opens the link;",
         "or an SSH config entry, nothing to install")
    s.text(AX + 280, y + 136, "standard library only, its own package", size=13.5, anchor="start", colour=t.dim)

    # -- 3 the database --------------------------------------------------------------------------
    y = ROWS[2]
    cylinder(BX + 80, y + 46, 64, 56, "work")
    s.text(BX + 80, y + 86, "SQLite", size=13)
    s.warning(BX + 160, y + 52, size=10)
    note(BX + 180, y + 56, "the source of truth, on node-local disk",
         "that persists and is never purged:",
         "at EMBL, where everything but some temporary",
         "directories is shared, it may not exist (#64)")
    cylinder(AX + 80, y + 46, 64, 56, "work", dashed=True)
    s.text(AX + 80, y + 86, "SQLite", size=13)
    s.text(AX + 80, y + 138, "node-local tmp", size=12.5, colour=t.dim)
    fold = s.folder(AX + 170, y + 40, 120, 92, fill="gate")
    s.text(fold.x + 60, fold.y + 52, "run dirs", size=13.5)
    s.text(fold.x + 60, fold.y + 72, "shared", size=12.5, colour=t.dim)
    s.arrow(fold.x - 4, fold.y + 46, AX + 120, y + 74)
    note(AX + 310, y + 46, "an index: rebuilt at boot when it is missing",
         "from each run's `.spectio/run.json`, spool,",
         "`head.pid` and `head.exit`; data dir stays",
         "in the shared home (assumed, inbox #64)")

    # -- 4 live refresh --------------------------------------------------------------------------
    y = ROWS[3]
    b = s.browser(BX + 30, y + 34, 150, 96, url="127.0.0.1")
    s.hourglass(b.cx, b.cy + 10, size=12)
    note(BX + 210, y + 56, "the UI polls the API every 5 s",
         "P1 Assumption 7, assumed:",
         "it dropped the `EventSource` cookie question")
    b2 = s.browser(AX + 30, y + 34, 150, 96, url="127.0.0.1")
    for k in range(3):
        s.arrow(AX + 250, b2.cy - 12 + k * 14, b2.right + 8, b2.cy - 12 + k * 14, width=1.3)
    s.text(AX + 252, b2.cy - 30, "frames", size=12.5, anchor="start", colour=t.dim)
    note(AX + 330, y + 56, "one SSE stream per browser",
         "behind the session cookie; the screen",
         "refetches the run a frame names",
         "decided by Thomas, 2026-10-28")

    s.text(40, H - 30, "Sources: docs/plans/P1-walking-skeleton.md and architecture §7.3 at 6bf2fec (before); "
                       "dev-env §15.3, schedulers §3.1.1, api §8.3, decision log 2026-10-28, inbox #64 (after) · "
                       "tools/diagrams/apply4_access.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply4_access")
