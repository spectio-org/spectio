#!/usr/bin/env python3
"""From the laptop to a head in tmux: batch P3-B02 (P1 Tasks 24 and 10), step P3, 2026-11-07.

Writes docs/assets/diagrams/p3-b02-open-tmux_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B02 at ec9271f (PRs 140 and 143 merged into
autopilot/integration on 263cd00; the batch code-simplifier changed nothing):
- spectio/cli/open.py: `_open` probes over `ssh <host>` (`Remote.state`), else `Remote.start` on
  `--node`, the `node` of clusters.toml, or `<host>`; target = `--node` or the state's node;
  `free_port()` unless `--local-port`; `_wait_up` up to TUNNEL_WAIT_S 120; `Remote.ticket`; the
  stale-file hint only when `probed`, `target == probed.node` and status != SSH_ERROR 255;
  NOT_FOUND 127 gives exit 2 with `uv tool install spectio==<version>`; other failures exit 3;
  `typer.echo` of the link, `webbrowser.open` unless `--no-browser`; Ctrl-C closes the tunnel;
- spectio/open_remote.py: STATE_MARK `spectio-state-v1`; parse_state checks node (NODE), port
  1024-65535 and an integer PID; ssh_argv `ssh -- node "$SHELL" -lc <script>`; tunnel_argv
  `-N -o ExitOnForwardFailure=yes -L 127.0.0.1:<local>:127.0.0.1:<port> -- node`; `command()`
  wraps `remote_cmd` in one shell group (CR-P3T24-01, fixed in 6f625fc); start_script: `init`
  only if `$HOME/.spectio` is missing, then `serve --detach`; login_script
  `login --print-link --json`; parse_ticket ignores any URL; link() builds
  `http://127.0.0.1:<local>/auth/link#<ticket>`;
- spectio/cli/serve.py: `--detach` is not built yet, FU-P3-44;
- spectio_server/serve.py: `LocalLauncher()` on executor local, else `TmuxLauncher()`; the loop and
  its thread always start; `Booted.loop: RunnerLoop`; the start text names `tmux attach`;
- spectio/runner/tmux.py: `new-session -d -P -F '#{pane_id} #{pane_pid}' -s spectio-<run_id>
  -c <launch dir> bash <head.sh>`, an argument list, TMUX_TIMEOUT_S 10; on a timeout or an
  unparsed output `_kill_unconfirmed` runs `kill-session -t =<session>` (CR-P3T10-01, fixed in
  d961cd5), never after a non-zero exit; adopt/_report: the pane PID must be head.pid, which leads
  its group and passes `alive` (start time, boot ID); head.exit read after the check; states
  running, starting, exited, unknown; cancel: `send-keys C-c` to the pane found again, then SIGTERM
  to the group at the first poll after grace_s (default 60, the loop passes none), SIGKILL after
  another, `_live` checked before each signal;
- web/src/runs/RunDetailPage.tsx: HOST_NAME, SESSION_NAME, LOCAL_HEAD; no commands when a value
  fails; `ssh -- '<node>'` and `tmux attach -t '=<session>'` (SEC-P3PARA-01);
- test counts: docs/reviews/code/P3-t10.md (46 passed for the tmux tests and test_serve.py at
  d961cd5), docs/reviews/code/P3-t24.md (test_open.py 39 passed at 09eb64e); the whole suite
  877 passed, 17 deselected at ec9271f (the batch code-simplifier's baseline, 2026-11-07).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1420
COLA = (50, 440, 830, 1220)  # spectio open, four columns 330 wide
CWA = 330
TOPA = 165
CAPA = 410
COLB = (50, 355, 660, 965, 1270)  # the tmux launcher, five columns 280 wide
CWB = 280
TOPB = 730
CAPB = 960
LOW = 1200


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, verdict: str, rows: tuple[str, ...],
        *, fixed: bool) -> None:
    """A finding pinned where it hits: a tag with the ID, then what it was."""
    w = 300
    s.poly([(x, y), (x + w, y), (x + w, y + 32 + 19 * len(rows)), (x, y + 32 + 19 * len(rows))],
           fill="done" if fixed else "problem", amount=0.5, width=1.2)
    if fixed:
        s.tick(x + 16, y + 13, size=6)
    else:
        s.warning(x + 16, y + 14, size=8)
    s.text(x + 32, y + 18, fid, size=13, anchor="start", weight="bold")
    s.text(x + w - 10, y + 18, verdict, size=12.5, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 40 + i * 19, row, size=12.5, anchor="start")


def tube(s: Sketch, x1: float, x2: float, y: float) -> None:
    """The ssh tunnel: a pipe between the laptop and the login node."""
    s.line(x1, y - 9, x2, y - 9, width=1.6)
    s.line(x1, y + 9, x2, y + 9, width=1.6)
    s.ellipse(x1, y, 5, 9, fill="input")
    s.ellipse(x2, y, 5, 9, fill="input")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=202)
    t = theme
    s.heading(50, 58, "P3-B02 · from the laptop to a head in tmux, P1 Tasks 24 and 10",
              "milestones M5 and M2 · dev-env 15.3 Access, req. 8 and 11 · schedulers 3.1.1 · "
              "PRs 143 and 140 into `autopilot/integration`")

    # -- spectio open, Task 24 ----------------------------------------------------------------
    s.line(30, 136, W - 30, 136, dashed=True, colour=t.muted)
    s.text(50, 126, "on the laptop: `spectio open <host>`, Task 24 · every value from the cluster "
           "is checked before use", size=14, anchor="start", colour=t.dim)

    # 1 the probe
    x = COLA[0]
    s.terminal(x, TOPA, 300, 66, ("$ spectio open <host>",), size=13)
    s.page(x + 8, TOPA + 96, 52, 66, fill="input", lines=3)
    s.text(x + 34, TOPA + 184, "`server.json`", size=12.5)
    for i, row in enumerate(("node: a host name", "port: 1024 to 65535", "PID: an integer")):
        s.tick(x + 88, TOPA + 104 + i * 26, size=6)
        s.text(x + 102, TOPA + 109 + i * 26, row, size=13, anchor="start")
    s.text(x + 88, TOPA + 184, "read after `spectio-state-v1`", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + 150, CAPA, 1, "probe over ssh")
    lines(s, x, CAPA + 30, ("`spectio --help`, then `~/.spectio/server.json`",
                            "through the login shell, `$SHELL -lc`",
                            "status 127: exit 2 and the install line",
                            "a value that fails a check: exit 3"))

    # 2 or start a server
    x = COLA[1]
    s.hpc_node(x + 6, TOPA + 4, 60, 82, busy=1)
    s.cog(x + 84, TOPA + 16, 10, fill="docs")
    s.text(x + 104, TOPA + 22, "no `server.json`: start one", size=14, anchor="start", weight="bold")
    s.text(x + 104, TOPA + 46, "on `--node`, else the `node` of", size=13, anchor="start",
           colour=t.dim)
    s.text(x + 104, TOPA + 66, "`clusters.toml`, else `<host>`", size=13, anchor="start",
           colour=t.dim)
    s.text(x + 10, TOPA + 120, "`spectio init`", size=13.5, anchor="start")
    s.text(x + 150, TOPA + 120, "only if `~/.spectio` is missing", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x + 10, TOPA + 150, "`spectio serve --detach`", size=13.5, anchor="start")
    s.warning(x + 228, TOPA + 145, size=10)
    s.text(x + 244, TOPA + 150, "not built yet", size=12.5, anchor="start", colour=t.warn)
    s.text(x + 10, TOPA + 180, "then the `server.json` it wrote", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + 160, CAPA, 2, "or start one")
    lines(s, x, CAPA + 30, ("`remote_cmd`, the user's own text, such as",
                            "`module load spectio && spectio`, runs",
                            "as one shell group, the guard covers it",
                            "`--detach` is follow-up FU-P3-44"))

    # 3 the tunnel
    x = COLA[2]
    s.terminal(x + 4, TOPA + 20, 76, 56, ("$",), size=12)
    s.text(x + 42, TOPA + 98, "laptop", size=13, colour=t.dim)
    tube(s, x + 92, x + 238, TOPA + 48)
    s.lock(x + 165, TOPA + 22, size=11)
    s.hpc_node(x + 252, TOPA + 8, 54, 74, busy=2)
    s.text(x + 279, TOPA + 98, "the node", size=13, colour=t.dim)
    s.text(x + 165, TOPA + 128, "`127.0.0.1:local` to `127.0.0.1:port`", size=12.5)
    s.text(x + 165, TOPA + 154, "a free local port, `ExitOnForwardFailure=yes`", size=12.5,
           colour=t.dim)
    s.hourglass(x + 24, TOPA + 180, size=8)
    s.text(x + 42, TOPA + 185, "waits up to 120 s: a password, a second factor", size=13,
           anchor="start")
    s.step(x + 165, CAPA, 3, "the tunnel")
    lines(s, x, CAPA + 30, ("`ssh -N -L`, with `--` before the node",
                            "no cluster value ever inside `-o`",
                            "Ctrl-C closes it; the server and",
                            "its runs keep going"))

    # 4 the browser
    x = COLA[3]
    s.browser(x, TOPA, CWA, 150, url="`127.0.0.1:local/auth/link#ticket`")
    s.link(x + 44, TOPA + 66, size=22)
    s.text(x + 82, TOPA + 62, "the ticket of `spectio login`", size=13, anchor="start")
    s.text(x + 82, TOPA + 82, "`--print-link --json`, checked", size=13, anchor="start",
           colour=t.dim)
    s.text(x + 20, TOPA + 124, "the link is built on the laptop", size=13, anchor="start")
    s.text(x + 165, TOPA + 184, "any URL the cluster prints is ignored", size=12.5, colour=t.dim)
    s.step(x + 165, CAPA, 4, "the browser opens")
    lines(s, x, CAPA + 30, ("a ticket from that node, single use",
                            "`--no-browser`: print the link only",
                            "the sign-in of batch P3-B01 follows",
                            "exit 0 once the tunnel ends"))

    for a, b in zip(COLA[:3], COLA[1:]):
        s.arrow(a + CWA - 22, TOPA + 34, b - 8, TOPA + 34)

    # the findings that hit Task 24
    pin(s, COLA[0], CAPA + 118, "CR-P3T24-02", "major, open",
        ("any `server.json` is taken as live; a failed",
         "login only hints it may be stale, FU-P3-48"), fixed=False)
    pin(s, COLA[1], CAPA + 118, "CR-P3T24-01", "blocker, fixed 6f625fc",
        ("with `&&` in `remote_cmd`, `init` ran again",
         "past the `~/.spectio` guard"), fixed=True)

    # -- the tmux launcher, Task 10 -----------------------------------------------------------
    s.line(30, TOPB - 54, W - 30, TOPB - 54, dashed=True, colour=t.muted)
    s.text(50, TOPB - 64, "on the login node: the tmux launcher, Task 10 · one session per run, "
           "the PID check before every signal", size=14, anchor="start", colour=t.dim)

    # 5 the loop starts on SLURM
    x = COLB[0]
    s.text(x + 4, TOPB + 22, "`spectio serve`", size=14, anchor="start")
    s.dot(x + 60, TOPB + 52, 4)
    s.line(x + 60, TOPB + 32, x + 60, TOPB + 48, width=1.4)
    s.arrow(x + 60, TOPB + 52, x + 92, TOPB + 84, colour=t.dim)
    s.arrow(x + 60, TOPB + 52, x + 92, TOPB + 146, colour=t.dim)
    s.poly([(x + 96, TOPB + 66), (x + 270, TOPB + 66), (x + 270, TOPB + 102), (x + 96, TOPB + 102)],
           fill="neutral", amount=0.5)
    s.text(x + 106, TOPB + 89, "local: `LocalLauncher`", size=13, anchor="start")
    s.poly([(x + 96, TOPB + 128), (x + 270, TOPB + 128), (x + 270, TOPB + 164),
            (x + 96, TOPB + 164)], fill="done", amount=0.5)
    s.text(x + 106, TOPB + 151, "slurm: `TmuxLauncher`", size=13, anchor="start")
    s.text(x + 183, TOPB + 186, "new in this batch", size=12.5, colour=t.dim)
    s.step(x + CWB / 2, CAPB, 5, "the loop on SLURM")
    lines(s, x, CAPB + 30, ("one launcher per executor",
                            "first tick, then the runner thread",
                            "it no longer stays off on SLURM",
                            "the start text names `tmux attach`"))

    # 6 one session per run
    x = COLB[1]
    s.terminal(x, TOPB, 266, 120, ("bash .spectio/head.sh",), size=12.5)
    s.poly([(x + 2, TOPB + 96), (x + 264, TOPB + 96), (x + 264, TOPB + 118), (x + 2, TOPB + 118)],
           fill="done", amount=0.3, width=1)
    s.text(x + 12, TOPB + 112, "`spectio-<run ID>`", size=12, anchor="start")
    s.text(x + 133, TOPB + 150, "`tmux new-session -d -P`", size=12.5)
    s.text(x + 133, TOPB + 172, "`-s spectio-<run ID> -c <launch dir>`", size=12)
    s.step(x + CWB / 2, CAPB, 6, "one session per run")
    lines(s, x, CAPB + 30, ("an argument list, no shell",
                            "it prints the pane ID and PID",
                            "native ID: the session name",
                            "the head leads its group, no `setsid`"))

    # 7 adopt and poll
    x = COLB[2]
    s.poly([(x + 6, TOPB + 20), (x + 100, TOPB + 20), (x + 100, TOPB + 96), (x + 6, TOPB + 96)],
           fill="surface", amount=0.6)
    s.poly([(x + 6, TOPB + 20), (x + 100, TOPB + 20), (x + 100, TOPB + 36), (x + 6, TOPB + 36)],
           fill="done", amount=0.3, width=1)
    s.text(x + 53, TOPB + 66, "pane PID", size=13.5)
    s.text(x + 128, TOPB + 66, "=", size=26, weight="bold")
    s.page(x + 156, TOPB + 14, 92, 88, fill="input", lines=0)
    s.text(x + 202, TOPB + 44, "`head.pid`", size=12)
    s.text(x + 202, TOPB + 66, "group, start", size=12, colour=t.dim)
    s.text(x + 202, TOPB + 84, "time, boot ID", size=12, colour=t.dim)
    s.text(x + 140, TOPB + 134, "running · starting · exited · unknown", size=13)
    s.text(x + 140, TOPB + 160, "`head.exit` read after the check", size=12.5, colour=t.dim)
    s.step(x + CWB / 2, CAPB, 7, "adopt and poll")
    lines(s, x, CAPB + 30, ("the pane's PID must be `head.pid`",
                            "and still live: this host, this boot",
                            "another node's head: never ended",
                            "from here, only `unknown`"))

    # 8 cancel, to scale
    x = COLB[3]
    ax0, ax1, ay = x + 20, x + 236, TOPB + 86  # 0 to 120 s, 1.8 px per second
    s.arrow(ax0 - 6, ay, ax1 + 12, ay, colour=t.dim)
    marks = ((0, "`C-c`", "now"), (60, "SIGTERM", "60 s"), (120, "SIGKILL", "120 s"))
    for sec, what, when in marks:
        mx = ax0 + sec * 1.8
        s.line(mx, ay - 8, mx, ay + 8, width=1.8)
        s.dot(mx, ay, 4.5, colour=t.accent if sec else t.good)
        s.text(mx, ay - 22, what, size=13)
        s.text(mx, ay + 28, when, size=12.5, colour=t.dim)
    s.text(x + 20, TOPB + 20, "to the head's pane, then its group", size=13, anchor="start")
    s.text(x + 140, TOPB + 150, "to scale, the default grace 60 s", size=12.5, colour=t.dim)
    s.text(x + 140, TOPB + 172, "each at the first poll after it", size=12.5, colour=t.dim)
    s.step(x + CWB / 2, CAPB, 8, "cancel")
    lines(s, x, CAPB + 30, ("`send-keys C-c` to the pane found",
                            "again, then `killpg`",
                            "the PID check before each signal",
                            "a head not in its pane: never signalled"))

    # 9 attach by hand
    x = COLB[4]
    s.browser(x, TOPB, 280, 132, url="run page")
    s.text(x + 14, TOPB + 52, "Open the head by hand", size=13.5, anchor="start", weight="bold")
    s.text(x + 14, TOPB + 78, "`ssh -- 'node'`", size=12.5, anchor="start")
    s.text(x + 14, TOPB + 100, "`tmux attach -t '=spectio-id'`", size=12.5, anchor="start")
    s.cross(x + 22, TOPB + 160, size=8)
    s.text(x + 40, TOPB + 165, "an odd node or session name:", size=12.5, anchor="start")
    s.text(x + 40, TOPB + 185, "no commands shown", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CWB / 2, CAPB, 9, "attach by hand")
    lines(s, x, CAPB + 30, ("each value quoted, the exact session",
                            "SEC-P3PARA-01 closed",
                            "a person can attach at any time",
                            "Ctrl-C typed there reaches the engine"))

    for a, b in zip(COLB[1:3], COLB[2:4]):  # 9 is aside: a person, at any time
        s.arrow(a + CWB - 6, TOPB + 56, b - 2, TOPB + 56)
    s.arrow(COLB[0] + 274, TOPB + 146, COLB[1] - 4, TOPB + 100)

    # the finding that hit Task 10
    pin(s, COLB[1], CAPB + 118, "CR-P3T10-01", "major, fixed d961cd5",
        ("no answer in 10 s, or no pane printed: the",
         "session ran on, unwatched. Now `kill-session`"), fixed=True)
    s.text(COLB[3], CAPB + 136, "never after a non-zero exit: that session", size=12.5,
           anchor="start", colour=t.dim)
    s.text(COLB[3], CAPB + 156, "may be another launch's, still live", size=12.5, anchor="start",
           colour=t.dim)
    s.arrow(COLB[3] - 8, CAPB + 140, COLB[1] + 306, CAPB + 140, dashed=True, colour=t.dim)

    # -- tests and the batch simplifier -----------------------------------------------------
    s.line(30, LOW - 14, W - 30, LOW - 14, dashed=True, colour=t.muted)
    s.text(50, LOW + 18, "tests passed, to scale", size=14, anchor="start", weight="bold")
    bars = (("`test_open.py`", "Task 24, 09eb64e", 39),
            ("tmux, real tmux, serve", "Task 10, d961cd5", 46),
            ("whole suite", "batch, ec9271f", 877))
    for i, (name, where, n) in enumerate(bars):
        y = LOW + 38 + i * 36
        s.text(50, y + 18, name, size=13, anchor="start")
        s.text(240, y + 18, where, size=12.5, anchor="start", colour=t.dim)
        bw = n * 0.62
        s.poly([(380, y), (380 + bw, y), (380 + bw, y + 24), (380, y + 24)], fill="bar_green",
               amount=0.4, width=1.2)
        s.text(390 + bw, y + 18, f"{n}" + (", 17 deselected" if n == 877 else ""), size=13.5,
               anchor="start")

    sx, sy = 1060, LOW + 4
    s.shade(sx, sy, 490, 150, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 26, "batch simplify: none, -0 +0, tests pass", size=13.5, anchor="start",
           weight="bold")
    s.text(sx + 14, sy + 50, "left as they are, test-only: CR-P3T10-05, -06, -07", size=12.5,
           anchor="start")
    s.text(sx + 14, sy + 72, "open minors: FU-P3-45 tmux, FU-P3-48 spectio open", size=12.5,
           anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 94, "Task 24 security review after the workflow:", size=12.5,
           anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 114, "approve, 5 minors, all to FU-P3-48", size=12.5, anchor="start",
           colour=t.dim)
    s.text(sx + 14, sy + 136, "not run: a real sshd, an EMBL login node", size=12.5,
           anchor="start", colour=t.dim)

    s.prefix_key(50, H - 16, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: cli/open.py · open_remote.py · runner/tmux.py · "
           "spectio_server/serve.py · RunDetailPage.tsx at ec9271f · dev-env 15.3",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b02-open-tmux")
