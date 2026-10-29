#!/usr/bin/env python3
"""The 0.0.1 walking skeleton planned in step P1, with its five milestones marked on it.

Writes docs/assets/diagrams/p1_skeleton_{light,dark}.{svg,png}.

Every fact comes from docs/plans/P1-walking-skeleton.md (draft, 2026-10-28) and the spec it cites,
docs/specs/dev-environment-and-testing.md §15.3:
- Architecture header: one process per user on the login node, a FastAPI app, an in-process runner
  thread and SQLite as an index in a node-local temporary directory, rebuilt from the run
  directories when it is missing (Assumption 21); the runner writes a head script, starts it in its own tmux
  session on the login node, watches its PID and exit files and tails the event spool the engine plugins write in the
  run directory; one writer thread validates spool events and projects them into runs, tasks and
  attempts; a three-screen UI refreshed live by one SSE stream (Assumption 7, decided 2026-10-28);
- Goal and §15.3: opened through an SSH tunnel with a one-time token link; the head runs Nextflow
  with nf-spectio or Snakemake with the logger plugin; its tasks go through the engine's own SLURM
  executor; the run directory and its spool `.spectio/events/*.jsonl` sit on the shared file system;
- Assumption 4 (D4): Cancel is Ctrl-C in the head's tmux pane, then SIGTERM, then SIGKILL after 60 s;
- Task 24: the tunnel is opened by `spectio open [--node]` or an SSH config entry (2026-10-28, one package 2026-10-29); done
  when, by hand on an EMBL login node, both open the runs list;
- Milestones table: M1 Events in, tasks 1-7; M2 Heads, 8-10; M3 Served safely, 11-16;
  M4 API and screens, 17-21; M5 On the cluster, 22-24 (24 tasks);
- §15.3 security requirements and their tasks: req. 6 is Task 3, req. 1 to 5 are Tasks 11 to 15,
  req. 7 is Task 16 (M3 header and task titles).
Which milestone builds which piece follows the task titles: spool contract, SQLite store, reader,
projector and both plugins (1-7); init, head script, runner loop, tmux launcher (8-10); serve and
the security tasks (11-16); launch and read API, UI, wheel (17-21); end to end on slurm-mini and the
laptop access (22-24).
The strip at the bottom is to scale: one cell per task.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1760, 1050

# (id, name, first task, last task, fill)
MILESTONES = (
    ("M1", "Events in", 1, 7, "bar_blue"),
    ("M2", "Heads", 8, 10, "bar_orange"),
    ("M3", "Served safely", 11, 16, "bar_violet"),
    ("M4", "API and screens", 17, 21, "bar_green"),
    ("M5", "On the cluster", 22, 24, "bar_grey"),
)
FILL = {m: f for m, _, _, _, f in MILESTONES}
# §15.3 requirement -> (the task that carries it, key text)
REQS = {
    1: (11, "bind to 127.0.0.1 only"),
    2: (12, "one-time token link, 256-bit secrets"),
    3: (13, "session cookie, HttpOnly, SameSite=Strict"),
    4: (14, "Host allow-list, loopback names only"),
    5: (15, "file modes, directories 0700, key and database 0600"),
    6: (3, "spool events untrusted, schema-checked, size-capped"),
    7: (16, "writes need Origin, bodies need JSON"),
}
TASK_REQ = {task: req for req, (task, _) in REQS.items()}


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=101)
    t = theme

    def shield(cx: float, cy: float, n: int, r: float = 11) -> None:
        """A §15.3 security requirement, numbered."""
        pts = [(cx - r, cy - r * 0.95), (cx, cy - r * 1.25), (cx + r, cy - r * 0.95),
               (cx + r, cy + r * 0.2), (cx, cy + r * 1.3), (cx - r, cy + r * 0.2)]
        s.poly(pts, fill="gate", width=1.6, amount=0.3)
        s.text(cx, cy + r * 0.45, str(n), size=r * 1.25, weight="bold")

    def badge(x: float, y: float, m: str) -> None:
        """Where a milestone builds this piece."""
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="40" height="23" rx="11" fill="{t.fill(FILL[m])}" '
              f'stroke="{t.ink}" stroke-width="1.4"/>')
        s.text(x + 20, y + 17, m, size=14, weight="bold")

    def cylinder(cx: float, top: float, w: float, h: float, fill: str) -> None:
        rx, ry = w / 2, 9
        s.ellipse(cx, top + h, rx, ry, fill=fill)
        s.raw(f'<rect x="{cx - rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{t.fill(fill)}"/>')
        s.line(cx - rx, top, cx - rx, top + h, amount=0.4, passes=1, width=1.5)
        s.line(cx + rx, top, cx + rx, top + h, amount=0.4, passes=1, width=1.5)
        s.ellipse(cx, top, rx, ry, fill=fill)

    def bar(x: float, y: float, w: float, fill: str = "bar_grey", h: float = 7) -> None:
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="2" fill="{t.fill(fill)}" '
              f'stroke="{t.ink}" stroke-width="0.7"/>')

    s.heading(40, 54, "P1 · the 0.0.1 walking skeleton, and where each milestone builds it",
              "one user, `spectio serve` on a SLURM login node, launch, monitor and cancel · "
              "a draft plan of 24 tasks, no code yet · shields: the seven §15.3 security requirements")

    # -- 1 · the laptop: a browser with the three plain screens -----------------------------------
    s.poly([(40, 160), (360, 160), (360, 440), (40, 440)], fill="neutral", width=1.8)
    s.poly([(28, 440), (372, 440), (392, 466), (8, 466)], fill="neutral", width=1.8)
    s.line(160, 453, 240, 453, width=1.2, amount=0.3, passes=1, colour=t.dim)
    b = s.browser(52, 172, 296, 256, url="127.0.0.1")
    s.text(312, 191, "cookie", size=12.5, anchor="end", colour=t.dim)
    shield(330, 186, 3, r=9)
    badge(40, 128, "M4")
    sy, sw, sh = 208, 88, 168
    labels = ("launch form", "runs list", "run detail")
    for k, lab in enumerate(labels):
        x = b.x + 8 + k * (sw + 8)
        s.rect(Box(x, sy, sw, sh, "surface"), colour=t.muted)
        s.text(x + sw / 2, sy + sh + 20, lab, size=12.5, colour=t.dim)
        if k == 0:  # three fields and a Launch button
            for r in range(3):
                bar(x + 8, sy + 12 + r * 34, 34, "bar_grey", 5)
                s.raw(f'<rect x="{x + 8:.1f}" y="{sy + 21 + r * 34:.1f}" width="72" height="14" rx="2" '
                      f'fill="{t.fill("surface")}" stroke="{t.ink}" stroke-width="0.9"/>')
            s.button(x + 8, sy + 128, 72, "Launch", fill="done", h=28)
        elif k == 1:  # one row per run, its state as a dot
            for r, c in enumerate((t.good, t.warn, t.good, t.accent, t.good, t.dim)):
                ry = sy + 16 + r * 24
                s.dot(x + 13, ry + 3, 4, colour=c)
                bar(x + 23, ry, 56 - (r % 3) * 8)
        else:  # state, counts per process, Cancel
            s.dot(x + 13, sy + 17, 4, colour=t.warn)
            bar(x + 23, sy + 14, 52, "bar_orange")
            for r in range(4):
                ry = sy + 38 + r * 18
                bar(x + 8, ry, 40)
                bar(x + 54, ry, 24 - r * 4, "bar_blue")
            s.button(x + 8, sy + 128, 72, "Cancel", fill="problem", h=28)
    s.step(200, 506, 1, "open the token link")
    s.text(200, 530, "tunnel: `spectio open [--node]`, or an SSH config entry", size=13.5, colour=t.dim)
    s.text(200, 550, "live refresh: one SSE stream per browser", size=13.5, colour=t.dim)
    s.text(200, 570, "a new link: `spectio login --print-link`", size=13.5, colour=t.dim)

    # -- the SSH tunnel, the token link, the checks at the door -----------------------------------
    py0, py1 = 318, 352
    s.line(372, py0, 648, py0, width=1.8, amount=0.6)
    s.line(372, py1, 648, py1, width=1.8, amount=0.6)
    s.ellipse(372, (py0 + py1) / 2, 7, (py1 - py0) / 2, fill="input")
    s.ellipse(648, (py0 + py1) / 2, 7, (py1 - py0) / 2, fill="input")
    s.arrow(392, 329, 630, 329, width=1.4)
    s.arrow(630, 342, 392, 342, width=1.2, colour=t.dim)
    badge(380, 236, "M3")
    s.link(400, 290, 15)
    s.text(420, 295, "one-time token link", size=14, anchor="start")
    shield(592, 289, 2)
    s.text(510, 382, "`ssh -L` tunnel", size=14)
    badge(404, 366, "M5")
    s.text(604, 414, "Host allow-list", size=13, anchor="end", colour=t.dim)
    shield(624, 409, 4)
    s.text(604, 450, "Origin on writes", size=13, anchor="end", colour=t.dim)
    shield(624, 445, 7)

    # -- 2 · the login node: one process, its runner, SQLite --------------------------------------
    s.frame(650, 130, 500, 460, fill="neutral", colour=t.muted)
    s.text(670, 162, "login node", size=20, anchor="start", weight="bold")
    s.text(1132, 162, "your own Unix account", size=13, anchor="end", colour=t.dim)
    s.terminal(670, 180, 290, 92, ("tmux: spectio-server", "$ spectio serve", "on 127.0.0.1, link printed"),
               size=13)
    shield(984, 214, 1)
    s.text(1002, 219, "loopback only", size=13, anchor="start", colour=t.dim)
    badge(974, 240, "M3")
    s.rect(Box(670, 300, 200, 70, "input"))
    s.text(770, 329, "FastAPI app", size=15.5, weight="bold")
    s.text(770, 353, "`/api/v1` and the UI", size=13, colour=t.dim)
    badge(880, 296, "M4")
    s.cog(946, 345, 10, fill="docs")
    s.text(968, 341, "runner thread", size=15, anchor="start", weight="bold")
    s.text(968, 362, "head script, PID watch", size=12.5, anchor="start", colour=t.dim)
    badge(1094, 296, "M2")
    # SQLite on node-local disk, read by the API, written by the runner
    cylinder(712, 430, 80, 56, "work")
    s.text(712, 468, "SQLite", size=14, weight="bold")
    s.arrow(712, 418, 712, 376, colour=t.dim, width=1.3)
    s.text(764, 452, "an index, node-local tmp", size=14, anchor="start")
    s.text(764, 472, "rebuilt from the run dirs", size=13, anchor="start", colour=t.dim)
    shield(774, 498, 5, r=9)
    s.text(790, 503, "0700 and 0600", size=13, anchor="start", colour=t.dim)
    badge(692, 506, "M1")
    s.arrow(944, 372, 770, 428)
    s.text(820, 432, "events → rows", size=13, anchor="start", colour=t.dim)
    s.step(790, 566, 2, "one server per user")
    # the engine head, in its own tmux session on the login node
    s.terminal(962, 396, 176, 104, ("tmux: spectio-<run>", "nextflow + nf-spectio", "or snakemake --logger"),
               size=11.5, line_h=19)
    s.arrow(1010, 372, 1018, 392, width=1.3)
    s.text(1050, 520, "engine head, in tmux", size=13.5, weight="bold")
    s.text(1052, 540, "Cancel: Ctrl-C in its pane,", size=12, colour=t.dim)
    s.text(1052, 556, "then SIGTERM, SIGKILL", size=12, colour=t.dim)
    s.text(1052, 572, "`tmux attach` to take over", size=12, colour=t.dim)
    badge(1098, 366, "M2")

    # -- 3 · SLURM: only the tasks --------------------------------------------------------------
    s.frame(1230, 130, 500, 460, fill="surface", colour=t.muted, dashed=True)
    s.text(1250, 162, "compute nodes, through SLURM", size=20, anchor="start", weight="bold")
    badge(1670, 144, "M5")
    for i in range(4):
        x = 1270 + i * 105
        s.hpc_node(x, 230, 60, 84, busy=3 - i % 3, slots=3)
        s.arrow(1140, 420, x + 30, 336, width=1.4)
    s.text(1690, 280, "tasks", size=14.5, weight="bold")
    s.step(1480, 456, 3, "the engine sends the tasks")
    s.text(1480, 482, "through its own SLURM executor; no `sbatch` for the head", size=13.5, colour=t.dim)

    # -- 4 · the shared file system: the spool -----------------------------------------------------
    fy = 640
    s.shade(650, fy, 1080, 172, fill="input", opacity=0.55)
    for k in range(3):
        cylinder(700, fy + 22 + k * 28, 64, 18, "input")
    s.text(700, fy + 136, "shared", size=14, weight="bold")
    s.text(700, fy + 154, "file system", size=14, weight="bold")
    fold = s.folder(790, fy + 16, 430, 142, fill="gate")
    s.text(fold.x + 16, fold.y + 38, "run directory", size=15.5, anchor="start", weight="bold")
    shield(fold.x + 134, fold.y + 32, 5, r=9)
    s.text(fold.x + 150, fold.y + 37, "0700", size=13, anchor="start", colour=t.dim)
    badge(fold.x + 370, fold.y + 20, "M1")
    for k in range(3):
        s.page(fold.x + 22 + k * 14, fold.y + 58 - k * 4, 50, 66, fill="surface", lines=4)
    s.text(fold.x + 120, fold.y + 76, "the spool", size=15, anchor="start")
    s.text(fold.x + 120, fold.y + 100, "`.spectio/events/*.jsonl`", size=14, anchor="start")
    s.text(fold.x + 120, fold.y + 122, "untrusted: schema-checked, size-capped", size=13, anchor="start",
           colour=t.dim)
    shield(fold.x + 408, fold.y + 117, 6)
    # the plugin appends, the runner reads
    s.arrow(1132, 502, 1196, fy + 12)
    s.text(1186, 622, "the plugins append events", size=13.5, anchor="start")
    s.arrow(944, fy + 14, 950, 378)
    s.text(934, 622, "the runner reads", size=13.5, anchor="end")
    s.step(1480, fy + 62, 4, "events come back as files")
    s.text(1480, fy + 88, "the runner tails the spool with a cursor", size=13.5, colour=t.dim)
    s.text(1480, fy + 108, "the plugins never post to the server", size=13.5, colour=t.dim)
    s.text(1480, fy + 128, "after a restart, the head is adopted by its tmux name", size=13.5, colour=t.dim)

    # -- the security key -------------------------------------------------------------------------
    ky = 604
    s.text(40, ky, "§15.3 security requirements, and the task that tests each", size=15, anchor="start",
           weight="bold")
    for i, (n, (task, text)) in enumerate(sorted(REQS.items())):
        y = ky + 30 + i * 26
        shield(54, y - 5, n, r=9)
        s.text(72, y, f"{text} · task {task}", size=13.5, anchor="start")

    # -- the plan, to scale: one cell per task ----------------------------------------------------
    cy0, cw, cgap, ggap = 872, 52, 4, 22
    s.text(40, cy0 - 18, "the plan, to scale: 24 tasks, one cell per task", size=17, anchor="start")
    x = 40
    for m, name, first, last, fill in MILESTONES:
        start = x
        for task in range(first, last + 1):
            s.raw(f'<rect x="{x:.1f}" y="{cy0}" width="{cw}" height="44" rx="3" fill="{t.fill(fill)}" '
                  f'stroke="{t.ink}" stroke-width="1.1"/>')
            s.text(x + cw / 2, cy0 + 29, str(task), size=16)
            if task in TASK_REQ:
                shield(x + cw / 2, cy0 + 66, TASK_REQ[task], r=9)
            x += cw + cgap
        mid = (start + x - cgap) / 2
        s.text(mid, cy0 + 112, f"{m} · {name}", size=15.5, weight="bold")
        s.text(mid, cy0 + 132, f"tasks {first}–{last}", size=13.5, colour=t.dim)
        x += ggap
    s.text(x + 6, cy0 + 16, "done when, on `slurm-mini` in CI,", size=13, anchor="start", colour=t.dim)
    s.text(x + 6, cy0 + 36, "both engines launch, succeed", size=13, anchor="start", colour=t.dim)
    s.text(x + 6, cy0 + 56, "and cancel, and a restarted", size=13, anchor="start", colour=t.dim)
    s.text(x + 6, cy0 + 76, "server adopts the running head;", size=13, anchor="start", colour=t.dim)
    s.text(x + 6, cy0 + 96, "by hand on an EMBL login node,", size=13, anchor="start", colour=t.dim)
    s.text(x + 6, cy0 + 116, "`spectio open` opens the runs list", size=13, anchor="start", colour=t.dim)

    s.text(40, H - 16, "Source: docs/plans/P1-walking-skeleton.md, Architecture, Assumptions 4, 7 and 21, Milestones, "
                       "Tasks 1–24 · docs/specs/dev-environment-and-testing.md §15.3 · "
                       "tools/diagrams/p1_skeleton.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p1_skeleton")
