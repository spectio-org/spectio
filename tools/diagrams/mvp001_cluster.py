#!/usr/bin/env python3
"""0.0.1 "everything on the cluster": where each piece runs, and how events come back.

Writes docs/assets/diagrams/mvp001_cluster_{light,dark}.{svg,png}.

Drawn only from what the owner says, no measurements involved:
- docs/specs/dev-environment-and-testing.md §15.3 (architecture, access, security
  requirements) and §15.1 (what is not in 0.0.1);
- docs/decisions/log.md, "2026-10-27 — 0.0.1 revised: on the cluster, no gates, a token link"
  and "2026-10-28 — 0.0.1: head in tmux on the login node; SSH config and `spectio open`"
  (the laptop command is named `spectio-open`, review of PR #47);
- inbox #64 (SQLite as a rebuildable index in a node-local temporary directory, assumed).
Facts drawn: the laptop reaches one login node through an SSH tunnel, opened by
`spectio-open <host> [--node <login node>]` or by an SSH config entry with `LocalForward`,
then a one-time token link (single use, 15 minutes, then a session cookie);
one `spectio serve` per user under their own Unix account, bound to 127.0.0.1, holding
UI + API + built-in runner, SQLite as an index in a node-local temporary directory (0600),
rebuilt from the run directories when it is missing; the runner starts each engine
head (Nextflow with nf-spectio, or Snakemake with the Spectio logger plugin) in its own
detached tmux session on the same login node and watches its PID; a person can attach to it;
the head sends its tasks through the engine's own SLURM executor; the plugin appends events
to the spool `.spectio/events/*.jsonl` in the run directory (0700) on the shared file system,
the runner reads it with a cursor; the server itself runs in a tmux session `spectio-server`;
0.0.1 targets the EMBL cluster (Thomas, 2026-10-28): tmux installed, no time limit on login-node
processes, home, software and storage shared except temporary directories; not in 0.0.1: QC checks
and gates, accounts and sign-in, Kubernetes.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 960


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=41)
    t = theme
    s.heading(60, 62, "0.0.1: everything on the cluster",
              "one `spectio serve` per user on a login node, each engine head in a tmux there, "
              "tasks go to SLURM, events come back as files")

    def person(cx: float, cy: float, r: float = 9, fill: str = "docs") -> None:
        """A user: a head over shoulders."""
        s.circle(cx, cy, r, fill=fill)
        sh = [(cx - r * 1.7, cy + r * 3.1), (cx - r * 1.5, cy + r * 1.8), (cx - r * 0.8, cy + r * 1.3),
              (cx + r * 0.8, cy + r * 1.3), (cx + r * 1.5, cy + r * 1.8), (cx + r * 1.7, cy + r * 3.1)]
        s.poly(sh, fill=fill, amount=0.3)

    def cylinder(cx: float, top: float, w: float, h: float, fill: str) -> None:
        """A disk: an upright drum."""
        rx, ry = w / 2, 9
        s.ellipse(cx, top + h, rx, ry, fill=fill)
        s.raw(f'<rect x="{cx - rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{t.fill(fill)}"/>')
        s.line(cx - rx, top, cx - rx, top + h, amount=0.4, passes=1, width=1.5)
        s.line(cx + rx, top, cx + rx, top + h, amount=0.4, passes=1, width=1.5)
        s.ellipse(cx, top, rx, ry, fill=fill)

    # -- 1 the laptop, a browser on its screen ----------------------------------
    s.poly([(92, 196), (332, 196), (332, 360), (92, 360)], fill="neutral", width=1.8)
    b = s.browser(104, 208, 216, 140, url="127.0.0.1")
    s.link(130, 262, 16)
    s.text(152, 268, "token link", size=14, anchor="start")
    for i, w in enumerate((150, 120, 136)):
        s.raw(f'<rect x="{b.x + 18:.1f}" y="{b.y + 82 + i * 16:.1f}" width="{w}" height="9" rx="2" '
              f'fill="{t.fill("bar_blue")}" stroke="{t.ink}" stroke-width="0.7"/>')
    s.poly([(80, 360), (344, 360), (366, 388), (58, 388)], fill="neutral", width=1.8)
    s.line(176, 375, 248, 375, width=1.2, amount=0.3, passes=1, colour=t.dim)
    s.step(212, 432, 1, "open it from the laptop")
    s.text(212, 458, "`spectio-open <host> [--node <login node>]`", size=13, colour=t.dim)
    s.text(212, 478, "or, with nothing to install, an SSH config entry", size=13.5, colour=t.dim)
    s.text(212, 498, "then a one-time token link: single use, 15 min", size=13.5, colour=t.dim)

    # the SSH tunnel: a pipe from the laptop to one login node
    ty0, ty1 = 262, 294
    s.line(374, ty0, 544, ty0, width=1.8, amount=0.6)
    s.line(374, ty1, 544, ty1, width=1.8, amount=0.6)
    s.ellipse(374, (ty0 + ty1) / 2, 7, (ty1 - ty0) / 2, fill="input")
    s.ellipse(544, (ty0 + ty1) / 2, 7, (ty1 - ty0) / 2, fill="input")
    s.arrow(394, (ty0 + ty1) / 2, 526, (ty0 + ty1) / 2, width=1.5)
    s.text(459, 246, "SSH tunnel", size=15)
    s.text(459, 318, "to one login node", size=13, colour=t.dim)

    # -- 2 the login node: the server, and one tmux per engine head ---------------
    s.frame(560, 128, 600, 512, fill="neutral", colour=t.muted)
    s.text(580, 160, "login node", size=20, anchor="start", weight="bold")
    person(1124, 146, 8)
    s.text(1092, 190, "your own Unix account", size=12.5, anchor="middle", colour=t.dim)
    s.terminal(580, 206, 280, 98, ("tmux: spectio-server", "$ spectio serve", "127.0.0.1, token link printed"), size=13)
    s.text(580, 334, "one process", size=14, anchor="start", colour=t.dim)
    ui = s.browser(580, 344, 78, 62)
    s.text(ui.cx, ui.y + 50, "UI", size=14, weight="bold")
    s.rect(Box(668, 344, 78, 62, "input"))
    s.text(707, 382, "API", size=14, weight="bold")
    s.rect(Box(756, 344, 110, 62, "docs"))
    s.cog(776, 375, 8, fill="docs")
    s.text(794, 370, "built-in", size=13.5, anchor="start")
    s.text(794, 390, "runner", size=13.5, anchor="start")
    cylinder(616, 432, 56, 46, "work")
    s.text(616, 466, "SQLite", size=13)
    s.text(656, 446, "an index, node-local tmp", size=13.5, anchor="start")
    s.text(656, 466, "rebuilt from run dirs", size=13, anchor="start", colour=t.dim)
    s.text(656, 484, "if missing; files 0600", size=13, anchor="start", colour=t.dim)
    s.step(680, 528, 2, "one server per user")
    s.text(680, 554, "`spectio serve`, nothing shared", size=13.5, colour=t.dim)
    # the engine head, in its own tmux session
    s.terminal(890, 206, 250, 124, ("tmux: spectio-<run>", "$ nextflow run ...", "  -plugins nf-spectio",
                                    "or snakemake --logger spectio"), size=12.5)
    s.arrow(866, 360, 886, 318)
    s.text(1015, 352, "engine head, one tmux per run", size=14, weight="bold")
    person(912, 396, 8)
    s.text(934, 404, "attach to watch or stop it", size=13, anchor="start")
    s.text(890, 432, "`tmux attach -t spectio-<run>`", size=12.5, anchor="start", colour=t.dim)
    s.step(1010, 496, 3, "the head runs here")
    s.text(1010, 522, "started and watched by the runner", size=13.5, colour=t.dim)
    s.text(1010, 542, "no `sbatch` for the head in 0.0.1", size=13.5, colour=t.dim)

    # -- 3 SLURM: only the tasks ---------------------------------------------------
    s.frame(1200, 128, 460, 512, fill="surface", colour=t.muted, dashed=True)
    s.text(1220, 160, "compute nodes, through SLURM", size=20, anchor="start", weight="bold")
    s.text(1220, 216, "only the tasks run here; the head never does", size=14, anchor="start", colour=t.dim)
    # the EMBL facts belong to the login nodes, so their callout sits in the login-node box
    s.shade(866, 574, 278, 58, fill="gate", opacity=0.9, colour=t.warn, dashed=True)
    s.warning(882, 590, size=9)
    s.text(898, 594, "0.0.1 targets the EMBL cluster", size=13, anchor="start", colour=t.warn)
    s.text(878, 620, "tmux installed, no time limit, all shared", size=12.5, anchor="start")
    for i in range(4):
        x = 1250 + i * 100
        s.hpc_node(x, 366, 58, 80, busy=3 - i % 3, slots=4)
        s.arrow(1142, 300, x + 29, 360)
    s.text(1455, 474, "tasks", size=14.5, weight="bold")
    s.step(1430, 512, 4, "tasks go to SLURM")
    s.text(1430, 538, "through the engine's own SLURM executor", size=13.5, colour=t.dim)
    s.text(1430, 558, "Nextflow `slurm`, or `snakemake-executor-plugin-slurm`", size=13, colour=t.dim)

    # -- 4 the shared file system: the spool -------------------------------------
    fy = 700
    s.shade(560, fy, 1100, 196, fill="input", opacity=0.6)
    for k in range(3):
        cylinder(616, fy + 34 + k * 30, 70, 22, "input")
    s.text(616, fy + 160, "shared", size=14, weight="bold")
    s.text(616, fy + 178, "file system", size=14, weight="bold")
    fold = s.folder(790, fy + 26, 360, 148, fill="gate")
    s.text(fold.x + 16, fold.y + 38, "run directory, 0700", size=15, anchor="start", weight="bold")
    for k in range(3):
        s.page(fold.x + 24 + k * 14, fold.y + 56 - k * 4, 54, 70, fill="surface", lines=4)
    s.text(fold.x + 120, fold.y + 80, "the spool", size=15, anchor="start")
    s.text(fold.x + 120, fold.y + 104, "`.spectio/events/*.jsonl`", size=14, anchor="start")
    # the plugin appends, the runner reads
    s.line(1142, 326, 1180, 344, width=1.6)
    s.line(1180, 344, 1180, fy - 36, width=1.6)
    s.arrow(1180, fy - 36, 1154, fy + 56)
    s.text(1192, fy - 22, "the plugin appends events", size=14, anchor="start")
    s.arrow(848, fy + 28, 848, 412)
    s.text(838, fy - 22, "the runner reads them, with a cursor", size=14, anchor="end")
    s.step(1410, fy + 92, 5, "events go through files")
    s.text(1410, fy + 120, "spool events are untrusted input:", size=13.5, colour=t.dim)
    s.text(1410, fy + 140, "schema-checked, size-capped, never run", size=13.5, colour=t.dim)

    # -- 5 not in 0.0.1 --------------------------------------------------------------
    s.shade(60, fy, 480, 196, fill="problem", opacity=0.9, colour=t.muted, dashed=True)
    s.step(300, fy + 30, 6, "not in 0.0.1")
    s.gate(140, fy + 128, 70, 60, state="closed")
    s.cross(140, fy + 92, size=22)
    s.text(140, fy + 164, "QC checks, gates", size=14)
    person(300, fy + 72, 10)
    person(326, fy + 80, 10)
    s.cross(312, fy + 92, size=22)
    s.text(312, fy + 164, "accounts, sign-in", size=14)
    s.k8s_pod(460, fy + 94, 28, fill="input")
    s.cross(460, fy + 94, size=22)
    s.text(460, fy + 164, "Kubernetes", size=14)

    s.text(60, H - 34, "Source: docs/specs/dev-environment-and-testing.md §15.3, and the decision log entries "
                       "2026-10-27 (0.0.1 revised) and 2026-10-28 (head in tmux, `spectio-open`) · "
                       "tools/diagrams/mvp001_cluster.py",
           size=12.5, anchor="start", colour=t.dim)
    s.text(60, H - 12, "EMBL login nodes (Thomas, 2026-10-28): tmux installed, no time limit, everything shared but temporary directories; "
                       "SQLite is a rebuildable index in a node-local temp dir (assumed, inbox #64)", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "mvp001_cluster")
