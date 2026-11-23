#!/usr/bin/env python3
"""Spectio end to end on slurm-mini (launch, cancel, restart) and the rest of runs.css on the design
tokens: batch P3-B18 (steps P3-ui19c, P3-t22, P3-t23, wave W5), 2026-11-23.

Writes docs/assets/diagrams/p3-b18-slurm-e2e-css-sweep_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B18 at 4124268 (the PRs squash-merged into
autopilot/integration between 6876ae6 and 4124268; the batch simplifier changed nothing):
- P3-t22, PR 164, and P3-t23, PR 313: tests/slurm/e2e.sh (cases install, launch nextflow or
  snakemake, cancel nextflow or snakemake, restart; `sind exec` as spx on the submitter, partition
  htc; setup: `spectio init`, `spectio serve --detach`; the tmux shim first on PATH logs each call
  to $e/tmux.log, umask 077; the EXIT trap `finish`: diagnostics on a fail, `e2e_client.py
  teardown`, the server session killed, `RESULT e2e-<case> pass|fail`); tests/slurm/e2e_client.py
  (CHECKS, CANCEL_CHECKS, RESTART_CHECKS; SUCCEEDED_PATH, CANCELLED_PATH, OPEN_ATTEMPTS;
  CANCEL_GRACE_S 60, CANCEL_WINDOW_S grace plus 120; RESTART_WAIT_S 20; signed_in through
  `spectio login --print-link --json`; POST /api/v1/runs and POST /api/v1/runs/<id>:cancel;
  server_address with socket_only, tcp_listener, same_socket; kill_server through
  os.pidfd_open and signal.pidfd_send_signal; new_sessions; teardown kills the heads' tmux
  sessions and scancels the jobs under the runs root); .github/workflows/pipelines-slurm.yml (job
  e2e: five cases, E2E_TIMEOUT 900, step 55 min, job 90 min);
- the CI numbers: pipelines-slurm run 44276045780, job e2e, on 06211d2 (autopilot/P3-t23, the
  review fix), 2026-11-18, success; `git diff 06211d2 4124268 -- tests/slurm dev/slurm
  .github/workflows/pipelines-slurm.yml` is empty. TIMING lines: launch nextflow 123 s, launch
  snakemake 316 s, cancel nextflow 89 s, cancel snakemake 16 s, restart 117 s. Tasks: 65 and 67
  succeeded. Cancel asked to cancelled: 09:37:56.7 to 09:38:00.8 (Nextflow), 09:38:11.3 to
  09:38:15.4 (Snakemake). squeue --states=all when it ended: CANCELLED 90, COMPLETED 54
  (Nextflow); CANCELLED 46, COMPLETING 2 (Snakemake). Restart: SIGKILL at 5 succeeded tasks,
  09:38:38.2; server on its socket again 09:39:01.5; succeeded, 65 tasks;
- review records docs/reviews/code/P3-t22.md (CR-P3T22-01 blocker, the API answered 404 on SLURM,
  gone with FU-P3-72) and P3-t23.md (SEC-P3T23-01, CR-P3T23-01, -02, -03 majors, fixed);
- P3-ui19c, PR 307: web/src/runs/runs.css; the rawPx regexes of web/src/rawPx.ts run on the file at
  6876ae6 and at 4124268 with tokens.test.ts GEOMETRY: 167 declarations with a raw px value, then 0;
  web/src/shell/theme.ts spacing xs 4, sm 8, md 12, lg 16, xl 24.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1230
Y0 = 120  # the harness band
Y1 = 470  # the three cases
Y2 = 965  # CI timings and the CSS sweep
COLS = (50, 565, 1080)  # the three cases, 470 wide
CW = 470


def pill(s: Sketch, x: float, y: float, label: str, *, fill: str = "surface", w: float | None = None) -> float:
    """A small rounded tag; returns its right edge."""
    w = w or 18 + 7.2 * len(label.strip("`"))
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="26" rx="13" fill="{s.t.fill(fill)}" '
          f'stroke="{s.t.ink}" stroke-width="1.3"/>')
    s.text(x + w / 2, y + 18, label, size=13)
    return x + w


def path(s: Sketch, x: float, y: float, states: tuple[tuple[str, str], ...], gap: float = 26) -> list[float]:
    """A run's states as tags joined by arrows; returns the right edge of each tag."""
    edges = []
    for i, (name, fill) in enumerate(states):
        if i:
            s.arrow(x + 3, y + 13, x + gap - 4, y + 13, width=1.4)
            x += gap
        x = pill(s, x, y, f"`{name}`", fill=fill)
        edges.append(x)
    return edges


def pin(s: Sketch, x: float, y: float, fid: str, note: str) -> None:
    """A finding pinned where it hit: its ID on a tag, then what became of it."""
    w = 14 + 7.4 * len(fid)
    s.raw(f'<rect x="{x:.1f}" y="{y - 15:.1f}" width="{w:.1f}" height="21" rx="4" '
          f'fill="{s.t.fill("problem")}" stroke="{s.t.accent}" stroke-width="1.3"/>')
    s.text(x + w / 2, y, fid, size=12.5, weight="bold")
    s.text(x + w + 8, y, note, size=12.5, anchor="start", colour=s.t.dim)


def checks(s: Sketch, x: float, y: float, items: tuple[str, ...], step: float = 23) -> float:
    """The `ok` lines of a case, as they came in CI; returns the y under the last."""
    for i, item in enumerate(items):
        s.tick(x + 8, y + i * step - 4, size=6, width=2.1)
        s.text(x + 24, y + i * step, item, size=13.5, anchor="start")
    return y + len(items) * step


def bar(s: Sketch, x: float, y: float, w: float, fill: str, h: float = 18) -> None:
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 1.5):.1f}" height="{h:.1f}" rx="2" '
          f'fill="{s.t.fill(fill)}" stroke="{s.t.ink}" stroke-width="1"/>')


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1818)
    t = theme
    s.heading(50, 58, "Batch P3-B18 · Spectio end to end on slurm-mini, and runs.css on the tokens",
              "P3-t22 PR 164, launch and monitor · P3-t23 PR 313, cancel and restart · P3-ui19c PR 307, "
              "the CSS sweep part 3 · wave W5 · merged into `autopilot/integration`, 6876ae6 to 4124268")

    # the harness ------------------------------------------------------------------------------
    y = Y0
    s.terminal(50, y + 14, 330, 112, ("$ bash tests/slurm/e2e.sh install",
                                       "$ bash tests/slurm/e2e.sh cancel nextflow",
                                       "RESULT e2e-cancel-nextflow pass"), size=12)
    s.arrow(392, y + 70, 478, y + 70)
    s.text(435, y + 58, "`sind exec`", size=13, colour=t.dim)
    s.text(435, y + 92, "as `spx`", size=13, colour=t.dim)

    s.shade(488, y - 4, 688, 286, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.text(504, y + 18, "the submitter of slurm-mini, its login node", size=13.5, anchor="start", colour=t.dim)

    s.page(512, y + 44, 52, 66, fill="surface", lines=3)
    s.text(538, y + 130, "`e2e_client.py`", size=13)
    s.arrow(574, y + 78, 664, y + 78)
    s.text(619, y + 66, "HTTP", size=13, colour=t.dim)

    s.folder(672, y + 34, 176, 100, fill="input")
    s.text(760, y + 72, "db dir, `0700`", size=13.5)
    s.circle(714, y + 106, 9, fill="done")
    s.dot(714, y + 106, 2.5)
    s.text(730, y + 111, "`spectio.sock`", size=13, anchor="start")
    s.lock(836, y + 40, size=12)
    s.cross(706, y + 158, size=7)
    s.text(722, y + 163, "TCP `127.0.0.1` port: refused", size=12.5, anchor="start", colour=t.dim)

    s.line(858, y + 96, 892, y + 86, dashed=True, colour=t.dim)
    s.cog(912, y + 80, 15, fill="docs")
    s.text(912, y + 130, "`spectio serve`", size=13)
    s.arrow(936, y + 80, 976, y + 80)
    s.terminal(984, y + 40, 176, 80, ("tmux spectio-<run_id>", "  the head"), size=12)
    s.text(1072, y + 140, "the `tmux` shim logs each call", size=12.5, colour=t.dim)

    s.arrow(1170, y + 80, 1240, y + 80)
    s.text(1205, y + 68, "`sbatch`", size=13, colour=t.dim)
    s.hpc_node(1252, y + 40, 52, 70, busy=3)
    s.hpc_node(1314, y + 40, 52, 70, busy=2)
    s.text(1384, y + 62, "compute nodes", size=15, anchor="start", weight="bold")
    s.text(1384, y + 84, "partition `htc`", size=13.5, anchor="start", colour=t.dim)
    s.text(1384, y + 104, "the engine's task jobs", size=13.5, anchor="start", colour=t.dim)

    cap = y + 204
    for cx, n, label, rows in (
        (215, 1, "a case starts", ("from the wheels in `$SLURM_DATA/tools`", "new directories, a new database")),
        (578, 2, "sign in, launch", ("a link from `spectio login`", "`POST /api/v1/runs`")),
        (760, 3, "the socket only", ("`server.json` names it", "no TCP fallback on SLURM")),
        (1040, 4, "the head in tmux", ("`spectio-<run_id>`, never in `sbatch`", "`init`, `serve --detach` as `spx`")),
        (1420, 5, "tasks in SLURM", ("`nextflow -profile slurm`", "Snakemake `profiles/slurm`")),
    ):
        s.step(cx, cap, n, label, size=17)
        for i, row in enumerate(rows):
            s.text(cx, cap + 22 + i * 19, row, size=12.5, colour=t.dim)
    pin(s, 504, y + 314, "CR-P3T22-01", "blocker: 404 on SLURM, gone with the socket of FU-P3-72")
    pin(s, 1000, y + 314, "SEC-P3T23-01", "major, fixed: checked by every case")

    # the three cases ----------------------------------------------------------------------------
    s.line(30, Y1 - 22, W - 30, Y1 - 22, dashed=True, colour=t.muted)
    s.text(50, Y1 + 6, "6 · the checks of each case, as they passed in CI", size=17, anchor="start")
    s.text(510, Y1 + 6, "then, pass or fail, the `EXIT` trap prints `RESULT`, kills the heads' sessions, "
           "`scancel`s the run's jobs and stops the server", size=13.5, anchor="start", colour=t.dim)

    top = Y1 + 44
    # launch
    x = COLS[0]
    s.text(x, top, "`launch nextflow`, `launch snakemake`", size=16, anchor="start", weight="bold")
    s.text(x, top + 22, "P3-t22 · the synthetic `happy`", size=13.5, anchor="start", colour=t.dim)
    path(s, x, top + 38, (("queued", "neutral"), ("running", "work"), ("succeeded", "done")))
    for i, (n, engine, secs) in enumerate(((65, "Nextflow", 123), (67, "Snakemake", 316))):
        sy = top + 86 + i * 46
        s.task_strip(x, sy, ((n, "done", ""),), cell=4.6, gap=1.2, h=16)
        s.text(x, sy + 36, f"{engine}: {n} tasks succeeded, equal to the golden", size=12.5,
               anchor="start", colour=t.dim)
    checks(s, x, top + 200, ("run succeeded", "head in tmux, no sbatch", "counts equal the golden",
                             "head.exit 0, as the run reads it", "no spool drop",
                             "no job or session left", "socket only, no TCP port"))

    # cancel
    x = COLS[1]
    s.text(x, top, "`cancel nextflow`, `cancel snakemake`", size=16, anchor="start", weight="bold")
    s.text(x, top + 22, "P3-t23 · `happy` at scale 4, cancelled once a task runs", size=13.5,
           anchor="start", colour=t.dim)
    edges = path(s, x, top + 38, (("queued", "neutral"), ("running", "work"), ("cancelling", "gate"),
                                  ("cancelled", "problem")), gap=22)
    s.text((edges[1] + edges[2]) / 2 - 50, top + 86, "`POST :cancel`", size=12.5, colour=t.dim)
    # the window, to scale: 2 px a second
    wy, px_s = top + 108, 2.0
    bar(s, x, wy, 180 * px_s, "done", h=14)
    s.line(x + 60 * px_s, wy - 4, x + 60 * px_s, wy + 18, colour=t.dim, amount=0.2)
    s.arrow(x + 4 * px_s, wy + 36, x + 4 * px_s, wy + 18, colour=t.accent, width=2)
    s.text(x + 2, wy + 53, "4 s on both engines", size=13, anchor="start", colour=t.accent)
    s.text(x + 60 * px_s + 6, wy + 34, "grace 60 s, then 120 s", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 180 * px_s + 8, wy + 12, "180 s allowed", size=12.5, anchor="start", colour=t.dim)
    # the jobs in squeue --states=all when the run ended, to scale: 2.6 px a job
    jy, px_j = top + 186, 2.6
    s.text(x, jy, "its SLURM jobs when it ended, `squeue --states=all`", size=13, anchor="start", colour=t.dim)
    for i, (engine, parts) in enumerate((("Nextflow", ((90, "problem", "CANCELLED 90"), (54, "done", "COMPLETED 54"))),
                                         ("Snakemake", ((46, "problem", "CANCELLED 46"), (2, "done", "COMPLETING 2"))))):
        by = jy + 14 + i * 44
        bx = x + 84
        s.text(x, by + 14, engine, size=12.5, anchor="start")
        for n, fill, label in parts:
            bar(s, bx, by, n * px_j, fill)
            bx += n * px_j
        s.text(x + 84, by + 34, " · ".join(p[2] for p in parts), size=12.5, anchor="start", colour=t.dim)
    end = checks(s, x, top + 302, ("run cancelled in time", "no job or session left",
                                   "no attempt left pending, submitted or running", "socket only, no TCP port"))
    pin(s, x, end + 6, "CR-P3T23-03", "major, fixed: not only running")

    # restart
    x = COLS[2]
    s.text(x, top, "`restart`", size=16, anchor="start", weight="bold")
    s.text(x, top + 22, "P3-t23 · Nextflow `happy`, its server killed mid run", size=13.5, anchor="start",
           colour=t.dim)
    ry = top + 52
    s.cog(x + 22, ry + 4, 11, fill="docs")
    s.cross(x + 22, ry + 4, size=13)
    s.text(x + 44, ry - 6, "`SIGKILL` through a pidfd", size=12.5, anchor="start")
    s.text(x + 44, ry + 12, "at the first succeeded task", size=12.5, anchor="start", colour=t.dim)
    s.hourglass(x + 252, ry + 4, size=9)
    s.text(x + 268, ry - 6, "20 s", size=12.5, anchor="start")
    s.text(x + 268, ry + 12, "back after 23 s", size=12.5, anchor="start", colour=t.dim)
    s.cog(x + 392, ry + 4, 11, fill="docs")
    s.text(x + 410, ry - 6, "`serve`", size=12.5, anchor="start")
    s.text(x + 410, ry + 12, "`--detach`", size=12.5, anchor="start", colour=t.dim)
    # the head keeps running in tmux all along
    hy = ry + 36
    s.shade(x, hy, 460, 26, fill="work", opacity=0.75, colour=t.ink)
    s.text(x + 12, hy + 18, "the head in `tmux spectio-<run_id>` runs on, then succeeds: 65 tasks",
           size=12.5, anchor="start")
    s.text(x, hy + 52, "adopted: one `new-session` for the run in `tmux.log`", size=13, anchor="start", colour=t.dim)
    s.link(x + 12, hy + 82, size=12)
    s.text(x + 30, hy + 87, "old cookie: `401` · a new link signs in · the same socket", size=13,
           anchor="start", colour=t.dim)
    end = checks(s, x, top + 200, ("run succeeded", "head adopted, not started again", "counts equal the golden",
                                   "no duplicate event_id", "no spool drop", "old cookie refused, new link works",
                                   "no job or session left", "socket only, no TCP port"))
    pin(s, x + 200, top + 200 + 3 * 23, "CR-P3T23-02", "major, fixed")

    # CI, to scale ---------------------------------------------------------------------------------
    s.line(30, Y2 - 30, W - 30, Y2 - 30, dashed=True, colour=t.muted)
    s.text(50, Y2, "the `e2e` job, run 44276045780 on 06211d2, 2026-11-18: five cases pass", size=16,
           anchor="start", weight="bold")
    px = 1.1  # a second
    for i, (case, secs) in enumerate((("launch nextflow", 123), ("launch snakemake", 316),
                                      ("cancel nextflow", 89), ("cancel snakemake", 16), ("restart", 117))):
        by = Y2 + 22 + i * 29
        s.text(50, by + 14, f"`{case}`", size=13, anchor="start")
        bar(s, 210, by, secs * px, "done")
        s.text(210 + secs * px + 8, by + 14, f"{secs} s", size=13, anchor="start", colour=t.dim)
    s.gauge(700, Y2 + 120, 62, 661 / 3300 * 100, 100, label="661 s of the step's 55 min")
    s.text(700, Y2 + 186, "the job has 90 min", size=12.5, colour=t.dim)

    # the CSS sweep --------------------------------------------------------------------------------
    x = 860
    s.text(x, Y2, "P3-ui19c · the rest of `runs.css` reads the tokens", size=16, anchor="start", weight="bold")
    s.page(x, Y2 + 20, 54, 70, fill="surface", lines=3)
    s.text(x + 72, Y2 + 42, "`gap: 8px`", size=13, anchor="start", colour=t.dim)
    s.line(x + 70, Y2 + 37, x + 150, Y2 + 37, colour=t.accent, width=1.8, amount=0.3)
    s.arrow(x + 160, Y2 + 37, x + 196, Y2 + 37, width=1.4)
    s.text(x + 204, Y2 + 42, "`gap: var(--mantine-spacing-sm)`", size=13, anchor="start")
    s.text(x + 72, Y2 + 74, "raw px in spacing, radius or font size, to scale:", size=13, anchor="start",
           colour=t.dim)
    pxd = 2.0  # a declaration
    s.text(x + 72, Y2 + 102, "before", size=12.5, anchor="start")
    bar(s, x + 130, Y2 + 89, 167 * pxd, "problem")
    s.text(x + 130 + 167 * pxd + 8, Y2 + 103, "167", size=13, anchor="start")
    s.text(x + 72, Y2 + 130, "after", size=12.5, anchor="start")
    s.tick(x + 140, Y2 + 124, size=6)
    s.text(x + 154, Y2 + 130, "0", size=13, anchor="start")
    # the spacing scale, to scale: 3 px a px
    sx = x
    s.text(sx, Y2 + 166, "spacing", size=12.5, anchor="start", colour=t.dim)
    sx += 62
    for name, v in (("xs", 4), ("sm", 8), ("md", 12), ("lg", 16), ("xl", 24)):
        bar(s, sx, Y2 + 154, v * 3, "input", h=14)
        s.text(sx + v * 3 / 2, Y2 + 186, f"{name} {v}", size=12.5, colour=t.dim)
        sx += v * 3 + 28
    s.text(x + 380, Y2 + 166, "one lint, `rawPx`, for `theme.test.ts`", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 380, Y2 + 186, "and `tokens.test.ts`; 5 geometry fragments kept", size=12.5, anchor="start",
           colour=t.dim)

    s.prefix_key(50, H - 16, ("CR", "SEC"), size=12.5)
    s.text(W - 50, H - 16, "source: tests/slurm/e2e.sh, e2e_client.py, pipelines-slurm.yml, web/src/runs/runs.css, "
           "web/src/rawPx.ts · CI run 44276045780", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b18-slurm-e2e-css-sweep")
