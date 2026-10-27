#!/usr/bin/env python3
"""0.0.1 "everything on the cluster": where each piece runs, and how events come back.

Writes docs/assets/diagrams/mvp001_cluster_{light,dark}.{svg,png}.

Drawn only from what the owner says, no measurements involved:
- docs/specs/dev-environment-and-testing.md §15.3 (architecture, access, security
  requirements) and §15.1 (what is not in 0.0.1);
- docs/decisions/log.md, "2026-10-27 — 0.0.1 revised: on the cluster, no gates, a token link".
Facts drawn: the laptop opens a token link through `ssh -L` to the login node (printed by
`spectio serve` or `spectio login --print-link`, a single-use 15-minute link ticket swapped
for a session cookie);
one `spectio serve` per user under their own Unix account, bound to 127.0.0.1, holding
UI + API + built-in runner, SQLite on node-local disk (0600); the runner submits the
engine head with `sbatch` and watches only the head (`squeue --me`, `sacct -j`); the
head (Nextflow with nf-spectio, or Snakemake with the Spectio logger plugin) sends its
tasks through the engine's own SLURM executor (the Snakemake head as a SLURM job is to be
validated in spike T3, fallback: the head on the login node); the plugin appends events to the spool
`.spectio/events/*.jsonl` in the run directory (0700) on the shared file system, the
runner reads it with a cursor; no network from compute nodes to the server; not in
0.0.1: QC checks and gates, accounts and sign-in, Kubernetes.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 900


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=41)
    t = theme
    s.heading(60, 62, "0.0.1: everything on the cluster",
              "one `spectio serve` per user on the login node, runs go to SLURM, events come back as files")

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
    s.step(212, 432, 1, "open the token link")
    s.text(212, 456, "printed by `spectio serve`", size=13.5, colour=t.dim)
    s.text(212, 476, "or `spectio login --print-link`", size=13.5, colour=t.dim)
    s.text(212, 496, "single use, 15 min, then a session cookie", size=13.5, colour=t.dim)

    # the SSH tunnel: a pipe from the laptop to the login node
    ty0, ty1 = 262, 294
    s.line(370, ty0, 566, ty0, width=1.8, amount=0.6)
    s.line(370, ty1, 566, ty1, width=1.8, amount=0.6)
    s.ellipse(370, (ty0 + ty1) / 2, 7, (ty1 - ty0) / 2, fill="input")
    s.ellipse(566, (ty0 + ty1) / 2, 7, (ty1 - ty0) / 2, fill="input")
    s.arrow(392, (ty0 + ty1) / 2, 548, (ty0 + ty1) / 2, width=1.5)
    s.text(468, 246, "SSH tunnel", size=15)
    s.text(468, 318, "`ssh -L port:127.0.0.1:port`", size=13)

    # -- 2 the login node --------------------------------------------------------
    s.frame(584, 128, 352, 452, fill="neutral", colour=t.muted)
    s.text(604, 160, "login node", size=20, anchor="start", weight="bold")
    person(866, 146, 8)
    s.text(838, 190, "your own Unix account", size=12.5, anchor="middle", colour=t.dim)
    s.terminal(604, 206, 312, 98, ("$ spectio serve", "bound to 127.0.0.1", "token link printed"), size=13)
    # what the one process holds
    s.text(604, 334, "one process", size=14, anchor="start", colour=t.dim)
    ui = s.browser(604, 344, 82, 62)
    s.text(ui.cx, ui.y + 50, "UI", size=14, weight="bold")
    s.rect(Box(698, 344, 82, 62, "input"))
    s.text(739, 382, "API", size=14, weight="bold")
    s.rect(Box(792, 344, 124, 62, "docs"))
    s.cog(818, 375, 8, fill="docs")
    s.text(840, 370, "built-in", size=13.5, anchor="start")
    s.text(840, 390, "runner", size=13.5, anchor="start")
    # SQLite on node-local disk
    cylinder(650, 432, 64, 46, "work")
    s.text(650, 466, "SQLite", size=13.5)
    s.text(696, 452, "node-local disk", size=13.5, anchor="start")
    s.text(696, 472, "database files 0600", size=13, anchor="start", colour=t.dim)
    s.step(720, 528, 2, "one server per user")
    s.text(720, 554, "`spectio serve`, nothing shared", size=13.5, colour=t.dim)

    # -- 3 SLURM: the head job, then its tasks -----------------------------------
    s.frame(1044, 128, 616, 452, fill="surface", colour=t.muted, dashed=True)
    s.text(1064, 160, "compute nodes, through SLURM", size=20, anchor="start", weight="bold")
    # the head job
    s.hpc_node(1080, 206, 66, 96, busy=1, slots=4)
    s.text(1113, 324, "engine head", size=14.5, weight="bold")
    s.chip(1168, 206, 196, "Nextflow + `nf-spectio`", fill="work", h=40)
    s.text(1266, 268, "or", size=13.5, colour=t.dim)
    s.chip(1168, 280, 196, "Snakemake + logger plugin", fill="work", h=40)
    # not settled: the Snakemake SLURM executor plugin advises against Snakemake inside a SLURM job
    s.shade(1382, 268, 266, 64, fill="gate", opacity=0.9, colour=t.warn, dashed=True)
    s.warning(1402, 292, size=10)
    s.text(1420, 296, "to be validated in spike T3", size=13.5, anchor="start", colour=t.warn)
    s.text(1394, 320, "fallback: head on the login node", size=13.5, anchor="start")
    # sbatch from the runner to the head
    s.arrow(916, 366, 1072, 262)
    s.text(978, 290, "`sbatch`", size=15, anchor="middle")
    s.text(990, 420, "`squeue --me`", size=12.5, colour=t.dim)
    s.text(990, 438, "`sacct -j` head", size=12.5, colour=t.dim)
    s.text(990, 456, "head job only", size=12.5, colour=t.dim)
    # tasks: the engine's own SLURM executor
    for i in range(4):
        x = 1200 + i * 100
        s.hpc_node(x, 370, 58, 80, busy=3 - i % 3, slots=4)
        s.arrow(1266, 324, x + 29, 364)
    s.text(1590, 416, "tasks", size=14.5, anchor="start", weight="bold")
    s.step(1430, 500, 3, "the head runs as a SLURM job")
    s.text(1430, 526, "its tasks go through the engine's own SLURM executor", size=13.5, colour=t.dim)
    s.text(1430, 546, "`snakemake-executor-plugin-slurm`, or Nextflow `slurm`", size=13.5,
           colour=t.dim)

    # -- 4 the shared file system: the spool -------------------------------------
    fy = 640
    s.shade(584, fy, 1076, 196, fill="input", opacity=0.6)
    for k in range(3):
        cylinder(640, fy + 34 + k * 30, 70, 22, "input")
    s.text(640, fy + 160, "shared", size=14, weight="bold")
    s.text(640, fy + 178, "file system", size=14, weight="bold")
    fold = s.folder(866, fy + 26, 340, 148, fill="gate")
    s.text(fold.x + 16, fold.y + 38, "run directory, 0700", size=15, anchor="start", weight="bold")
    for k in range(3):
        s.page(fold.x + 24 + k * 14, fold.y + 56 - k * 4, 54, 70, fill="surface", lines=4)
    s.text(fold.x + 120, fold.y + 80, "the spool", size=15, anchor="start")
    s.text(fold.x + 120, fold.y + 104, "`.spectio/events/*.jsonl`", size=14, anchor="start")
    # the plugin appends, the runner reads
    s.arc(1113, 336, 1180, fy + 64, lift=-30)
    s.text(1186, 612, "the plugin appends events", size=14, anchor="start")
    s.arrow(fold.x + 30, fold.y + 2, fold.x + 30, 412)
    s.text(fold.x + 20, 612, "the runner reads them, with a cursor", size=14, anchor="end")
    # no network from compute nodes to the server
    s.arc(1044, 142, 936, 142, lift=26, dashed=True, colour=t.accent)
    s.cross(990, 162, size=9)
    s.text(990, 112, "no network from compute nodes", size=13.5, colour=t.accent)
    s.step(1440, fy + 92, 4, "events go through files, not the network")
    s.text(1440, fy + 120, "spool events are untrusted input:", size=13.5, colour=t.dim)
    s.text(1440, fy + 140, "schema-checked, size-capped, never run", size=13.5, colour=t.dim)

    # -- 5 not in 0.0.1 --------------------------------------------------------------
    s.shade(60, fy, 480, 196, fill="problem", opacity=0.9, colour=t.muted, dashed=True)
    s.step(300, fy + 30, 5, "not in 0.0.1")
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

    s.text(60, H - 34, "Source: docs/specs/dev-environment-and-testing.md §15.3, and the decision log entry "
                       "2026-10-27, 0.0.1 revised · tools/diagrams/mvp001_cluster.py",
           size=12.5, anchor="start", colour=t.dim)
    s.text(60, H - 12, "Per site, to be validated: persistent node-local disk and a long-running user process "
                       "on the login node", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "mvp001_cluster")
