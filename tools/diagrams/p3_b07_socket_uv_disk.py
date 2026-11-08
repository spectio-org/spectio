#!/usr/bin/env python3
"""The server behind a Unix socket, a way out of an old uv or SQLite, a warning on a nearly full
runs disk: batch P3-B07 (steps P3-fu72, P3-fu73 and P3-fu74, wave W5), 2026-11-08.

Writes docs/assets/diagrams/p3-b07-socket-uv-disk_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B07 at d49f8450 (PRs 169, 170 and 171 merged into
autopilot/integration between 7886354d and 47d78c4c, then the batch code-simplifier's two
commits 4ff68b38 and d49f8450):
- P3-fu72, PR 169: spectio_server/serve.py (`started`: `no_api_reason` decides, `SOCKET` in the
  checked database directory, `_bind_unix` refuses a path over `SUN_PATH_MAX` 107 bytes,
  `_clear_stale` removes a socket nothing answers on and refuses a non-socket or a live one,
  chmod 0600 before listen, `_remove_socket` at a clean stop; `_record` writes `socket` beside
  `port`; `start_text` prints `ssh -N -L 127.0.0.1:<port>:<socket> <user>@<node>`);
  spectio_server/app.py (`create_app(on_socket=...)`: on TCP `no_api_reason` still leaves the API
  unmounted on SLURM and shared hosts); store/db.py (`default_db_dir(fixed=True)` refuses a
  squatted default); spectio/ports.py (`SOCKET = "spectio.sock"`, `SUN_PATH_MAX = 107`,
  `is_server_socket`); cli/login.py (`_checked`, `_own_socket`, `_UnixHTTP`, `new_link`: a
  refused or missing socket is `Refused`; `http.client`, no proxy; `POST /api/v1/auth/links`);
  open_remote.py (`check_socket`, `_SOCKET_PATH` no `:` or space, `tunnel_argv`); config.py
  `DEFAULT_PORT = 8080`; tests/security/test_unix_socket.py 17 cases with a real uvicorn;
- P3-fu73, PR 170: config.py `MIN_UV = (0, 13, 7)`; store/db.py `check_sqlite_version`
  (accepted: >= 3.51.3, 3.50.7 to 3.51, 3.44.6 to 3.45; the refusal adds the Python and the way
  out); cli/doctor.py `_uv` (ok with version and path, ok when none, warn when older, non-zero or
  no version; never fail); login-node audit 2026-11-08 §8 (uv 0.9.29: Python 3.13.11, SQLite
  3.50.4 refused; uv 0.13.7 with Python 3.13.14: SQLite 3.53.1);
- P3-fu74, PR 171: runner/rundir.py `runs_disk` (`FULL_PCT = 90`, `MIN_FREE = 10 * 2**30`, the
  percentage rounded up, the nearest existing parent, warn when unmeasurable, never raises),
  cli/doctor.py (the `runs_disk` line), runner/loop.py `_launch` (log.warning, then submit);
  the audit §6 `df` of the EMBL /home in KiB: 25501368320 blocks, 24486338560 used, 1015029760
  available, 97% (test_doctor.py: "968.0 GiB free, 97% used"); the bar is drawn to scale from
  those numbers: 96.02% used exactly, 23.75 TiB, so 10 GiB is 0.04% of it;
- findings: docs/reviews/code/P3-fu72.md, P3-fu73.md, P3-fu74.md. Every blocker and major is
  pinned: CR-P3FU72-01 r1 (blocker), SEC-P3FU72-01 r1 (major); IDs restart per round in P3-fu72,
  so each pin names its round. P3-fu73 and P3-fu74 had none;
- the batch simplifier's report: 2 commits, 4 files, -13 +17; pytest 1096 passed, 1 skipped, 30
  deselected before and after; ruff, mypy, lint-imports, uv lock --check pass; the web step not
  run (node_modules not installed in the worktree; no web/src change); re-review approve, no
  findings, from both reviewers.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1530
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
TOP1, CAP1, PIN1 = 170, 392, 505  # P3-fu72
QX = (50, 420, 830, 1210)  # four columns, 340 wide: P3-fu73 left, P3-fu74 right
QW = 340
TOP2, CAP2, NOTE2 = 740, 950, 1062  # P3-fu73 and P3-fu74
LOW = 1200  # the batch simplifier and the tests


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, severity: str, rows: tuple[str, ...],
        status: str, *, w: float = 280) -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it was fixed."""
    h = 34 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 16, y + 13, size=6)
    s.text(x + 32, y + 18, fid, size=13, anchor="start", weight="bold")
    s.text(x + w - 10, y + 18, severity, size=12.5, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 40 + i * 19, row, size=12.5, anchor="start")
    s.text(x + 12, y + 40 + len(rows) * 19, status, size=12.5, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = 280,
         warn: bool = False) -> float:
    """A dashed note: the rounds, what is open, what was not run; returns its bottom."""
    h = 14 + 21 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 0
    if warn:
        s.warning(x + 18, y + 19, size=8)
        ox = 18
    for i, row in enumerate(rows):
        s.text(x + 12 + (ox if i == 0 else 0), y + 24 + i * 21, row, size=12.5, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str, *, x0: float = 30, x1: float = W - 30, tx: float = 50) -> None:
    s.line(x0, y, x1, y, dashed=True, colour=s.t.muted)
    s.text(tx, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def outlet(s: Sketch, cx: float, cy: float, r: float = 13, *, fill: str = "done") -> None:
    """A Unix socket, drawn as a wall socket: two slots in a square plate."""
    s.poly([(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)], fill=fill,
           amount=0.4, width=1.6)
    s.circle(cx, cy, r * 0.7, width=1.2)
    for dx in (-r * 0.28, r * 0.28):
        s.line(cx + dx, cy - r * 0.3, cx + dx, cy + r * 0.3, width=2.4, passes=1, amount=0.1)


def person(s: Sketch, cx: float, top: float, *, fill: str = "problem") -> None:
    """Another user of the node: a head and shoulders."""
    s.circle(cx, top + 8, 8, fill=fill)
    s.poly([(cx - 14, top + 38), (cx - 12, top + 24), (cx, top + 19), (cx + 12, top + 24),
            (cx + 14, top + 38)], fill=fill, amount=0.5)


def shell(s: Sketch, x: float, y: float, w: float, text: str) -> None:
    """One `bash -l`: a small terminal with the script it runs."""
    s.terminal(x, y, w, 50, (text,), size=11)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=707)
    t = theme
    s.heading(50, 58, "P3-B07 · behind a Unix socket, a way out of an old uv, a nearly full runs disk",
              "wave W5 · steps P3-fu72, P3-fu73 and P3-fu74 · dev-env 15.3 req. 1 · architecture 7.3 · "
              "PRs 169, 170 and 171 into `autopilot/integration`")

    # == P3-fu72: spectio serve on a Unix socket ===============================================
    band(s, 140, "P3-fu72, PR 169, inbox 109 rule 5 · on SLURM and shared hosts `spectio serve` "
         "listens on `spectio.sock` in its 0700 database directory, never on a TCP port")

    # 1 which transport
    x = COL[0]
    s.hpc_node(x + 4, TOP1, 46, 60, busy=3)
    s.hpc_node(x + 56, TOP1, 46, 60, busy=2)
    s.arrow(x + 112, TOP1 + 30, x + 200, TOP1 + 30)
    s.text(x + 156, TOP1 + 20, "shared", size=12.5, colour=t.dim)
    outlet(s, x + 226, TOP1 + 30)
    s.text(x + 226, TOP1 + 66, "`spectio.sock`", size=11.5)
    s.terminal(x + 4, TOP1 + 92, 98, 56, ("$",), size=11)
    s.text(x + 53, TOP1 + 166, "only you", size=12.5, colour=t.dim)
    s.arrow(x + 112, TOP1 + 120, x + 160, TOP1 + 120)
    s.text(x + 166, TOP1 + 116, "`127.0.0.1`", size=11.5, anchor="start")
    s.text(x + 166, TOP1 + 134, "`:8080`, as before", size=11.5, anchor="start")
    s.step(x + CW / 2, CAP1, 1, "which transport")
    lines(s, x, CAP1 + 30, ("SLURM, or local mode on a host",
                            "`shared_host()` calls shared: the socket",
                            "local, a machine only you use: TCP",
                            "on TCP a shared host still gets no API"))

    # 2 the socket in the 0700 database directory
    x = COL[1]
    s.folder(x + 4, TOP1 + 4, 170, 118, fill="input")
    s.text(x + 89, TOP1 + 38, "`/tmp/spectio-<uid>`", size=11.5)
    s.lock(x + 160, TOP1 + 116, size=11, fill="gate")
    s.text(x + 136, TOP1 + 140, "0700", size=12.5, colour=t.dim)
    outlet(s, x + 64, TOP1 + 80, r=15)
    s.text(x + 88, TOP1 + 76, "0600", size=12, anchor="start", colour=t.dim)
    s.text(x + 88, TOP1 + 94, "this user", size=12, anchor="start", colour=t.dim)
    person(s, x + 246, TOP1 + 52)
    s.text(x + 246, TOP1 + 40, "another user", size=12, colour=t.dim)
    s.arrow(x + 228, TOP1 + 78, x + 184, TOP1 + 78, dashed=True, colour=t.dim)
    s.cross(x + 206, TOP1 + 78, size=8)
    s.text(x + 230, TOP1 + 116, "refused at", size=12, anchor="start")
    s.text(x + 230, TOP1 + 134, "`connect`", size=12, anchor="start")
    s.text(x, TOP1 + 166, "by the kernel, at the directory", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 2, "a socket in the 0700 dir")
    lines(s, x, CAP1 + 30, ("refused, exit 2: a directory not 0700",
                            "and yours, a path over 107 bytes,",
                            "a file not a socket, a live socket",
                            "a dead server's socket: bound again"))

    # 3 server.json names the socket
    x = COL[2]
    s.page(x + 4, TOP1, 232, 128, fill="surface", lines=0)
    s.text(x + 16, TOP1 + 24, "`server.json`", size=12.5, anchor="start", weight="bold")
    rows = (("`host`", "`<node>`", "surface"), ("`port`", "`8080`", "surface"),
            ("`socket`", "`<db dir>/spectio.sock`", "done"))
    for i, (key, value, fill) in enumerate(rows):
        y = TOP1 + 38 + i * 26
        if fill == "done":
            s.poly([(x + 10, y), (x + 230, y), (x + 230, y + 22), (x + 10, y + 22)], fill="done",
                   amount=0.3, width=1.0)
        s.text(x + 16, y + 16, key, size=11, anchor="start")
        s.text(x + 72, y + 16, value, size=10.5, anchor="start")
    s.text(x + 244, TOP1 + 108, "new", size=12.5, anchor="start", colour=t.dim)
    s.text(x, TOP1 + 156, "the laptop end: `port`, `spectio_session_<port>`", size=12, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP1, 3, "`socket` beside `port`")
    lines(s, x, CAP1 + 30, ("`port` now names the laptop's end",
                            "of the tunnel, the link, the cookie",
                            "the socket and `server.json` are",
                            "removed at a clean stop"))

    # 4 the tunnel ends on the socket
    x = COL[3]
    s.browser(x + 4, TOP1 + 4, 120, 70)
    s.text(x + 64, TOP1 + 56, "`127.0.0.1:<port>`", size=10.5)
    s.text(x + 64, TOP1 + 92, "laptop", size=12.5, colour=t.dim)
    s.line(x + 130, TOP1 + 40, x + 228, TOP1 + 40, dashed=True, colour=t.dim)
    s.line(x + 130, TOP1 + 50, x + 228, TOP1 + 50, dashed=True, colour=t.dim)
    s.text(x + 179, TOP1 + 30, "`ssh -L`", size=11.5)
    outlet(s, x + 252, TOP1 + 45)
    s.text(x, TOP1 + 124, "`ssh -N -L 127.0.0.1:<port>:<socket>`", size=11, anchor="start")
    s.text(x, TOP1 + 144, "`    <user>@<node>`", size=11, anchor="start")
    s.text(x, TOP1 + 166, "printed by `spectio serve` at start", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 4, "the tunnel ends on it")
    lines(s, x, CAP1 + 30, ("`spectio open` checks the path:",
                            "no colon, no space, at most 107 bytes",
                            "`Host` allow-list: a loopback name",
                            "on any port, as a tunnel's may differ"))

    # 5 a link over the socket
    x = COL[4]
    s.terminal(x, TOP1, CW, 74, ("$ spectio login --print-link",), size=11.5)
    s.link(x + 30, TOP1 + 58, size=13, colour=t.term_ink)
    s.lock(x + 24, TOP1 + 106, size=10, fill="gate")
    s.text(x + 42, TOP1 + 111, "the server key, only to `spectio.sock`", size=12, anchor="start")
    s.text(x + 42, TOP1 + 131, "in the database directory, a socket", size=12, anchor="start",
           colour=t.dim)
    s.text(x + 42, TOP1 + 149, "of this user", size=12, anchor="start", colour=t.dim)
    s.text(x, TOP1 + 166, "`http.client`, never a proxy", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 5, "a link over the socket")
    lines(s, x, CAP1 + 30, ("`login --print-link`, `serve --detach`",
                            "and `spectio open` read the socket",
                            "from `server.json`, check it, then",
                            "`POST /api/v1/auth/links` on it"))

    for a, b in zip(COL[:4], COL[1:]):
        s.arrow(a + CW + 2, TOP1 + 192, b - 3, TOP1 + 192, colour=t.muted)

    note(s, COL[0], PIN1, ("3 rounds · code-reviewer: changes,", "approve, approve · security-reviewer:",
                           "changes, approve, approve"))
    y = note(s, COL[0], PIN1 + 88, ("`test_unix_socket.py`: 17 cases,", "a real uvicorn on a socket;",
                                    "`test_open.py` 8, `test_detach.py` 2"))
    pin(s, COL[1], PIN1, "SEC-P3FU72-01 r1", "major",
        ("a squatted default `/tmp/spectio-<uid>`", "was swapped for a `mkdtemp` one, while",
         "the tunnel names that path: a co-user", "listening there got the browser"),
        "fixed in 743ae0ea: refused, exit 2")
    note(s, COL[2], PIN1, ("open, FU-P3-75, all minor: a TCP line", "`start_text` can still print; the",
                           "listener's uid unchecked; the path", "unquoted in the `ssh` line; `init` and",
                           "the squatted default; `-L` regex untested"))
    note(s, COL[3], PIN1, ("not run here, for Thomas on login1:", "a second account refused at",
                           "`connect`, `spectio serve` on a socket", "there, the server after a logout"),
         warn=True)
    pin(s, COL[4], PIN1, "CR-P3FU72-01 r1", "blocker",
        ("after an unclean stop, `serve --detach`", "took the dead socket for a server",
         "starting: it waited, exited 3, and", "never started a new one"),
        "fixed in 743ae0ea: `Refused`, a new start")

    # == P3-fu73 and P3-fu74 ======================================================================
    band(s, 712, "P3-fu73, PR 170, audit 8 · a too old uv or SQLite names a way out", x1=780)
    band(s, 712, "P3-fu74, PR 171, audit 6 · the runs root on a nearly full disk warns", x0=820,
         tx=830)

    # 6 the SQLite refusal, versions on a line
    x = QX[0]
    x0, unit, ay = x + 12, 31, TOP2 + 92  # one minor release per 31 px, a tenth of it per patch

    def at(minor: int, patch: int) -> float:
        return x0 + (minor - 44) * unit + patch / 10 * unit

    bar(s, x0, ay - 8, 10 * unit, 16, "neutral")
    for (m0, p0), (m1, p1) in (((44, 6), (45, 0)), ((50, 7), (51, 0)), ((51, 3), (54, 0))):
        bar(s, at(m0, p0), ay - 8, at(m1, p1) - at(m0, p0), 16, "done")
    s.arrow(at(54, 0), ay, at(54, 0) + 12, ay, colour=t.good)
    for minor in (44, 47, 50, 51, 54):
        s.line(at(minor, 0), ay + 9, at(minor, 0), ay + 15, colour=t.dim, passes=1)
        s.text(at(minor, 0), ay + 30, f"3.{minor}", size=11.5, colour=t.dim)
    bad, good = at(50, 4), at(53, 1)
    s.line(bad, ay - 34, bad, ay - 10, colour=t.accent, passes=1)
    s.cross(bad, ay - 44, size=6)
    s.text(bad - 12, ay - 62, "uv 0.9.29, Python 3.13.11:", size=12, anchor="end")
    s.text(bad - 12, ay - 44, "SQLite 3.50.4, refused", size=12, anchor="end", colour=t.dim)
    s.line(good, ay + 10, good, ay + 40, colour=t.good, passes=1)
    s.tick(good, ay + 50, size=6)
    s.text(good - 12, ay + 56, "uv 0.13.7, Python 3.13.14: 3.53.1", size=12, anchor="end")
    s.text(x, TOP2 + 10, "SQLite with the WAL-reset fix, accepted", size=12.5, anchor="start")
    bar(s, x + 262, TOP2, 22, 12, "done")
    s.text(x, TOP2 + 172, "a minor release per tick, a tenth per patch", size=12, anchor="start",
           colour=t.dim)
    s.step(x + QW / 2, CAP2, 6, "the refusal shows a way out")
    lines(s, x, CAP2 + 30, ("it names the Python it came from, then:",
                            "upgrade uv to 0.13.7 or later,",
                            "`uv python install 3.13`, reinstall Spectio",
                            "the minimum lives once: `MIN_UV`"))

    # 7 the uv line in spectio doctor
    x = QX[1]
    s.terminal(x, TOP2, QW, 74, ("$ spectio doctor", "ok uv 0.13.7 <path>"), size=11.5)
    outcomes = (("tick", "0.13.7 or newer: its version and path"),
                ("tick", "no uv at all: only installing needs it"),
                ("warn", "older, a non-zero exit, or no version"),
                ("cross", "never a `fail`"))
    for i, (mark, text) in enumerate(outcomes):
        y = TOP2 + 96 + i * 22
        if mark == "tick":
            s.tick(x + 10, y, size=5)
        elif mark == "warn":
            s.warning(x + 10, y, size=6)
        else:
            s.cross(x + 10, y, size=5)
        s.text(x + 26, y + 5, text, size=12.5, anchor="start")
    s.step(x + QW / 2, CAP2, 7, "a `uv` line in `spectio doctor`")
    lines(s, x, CAP2 + 30, ("the `uv` on the login PATH, found",
                            "by the same login shell as `tmux`",
                            "and `sbatch` since the simplify",
                            "a warning at most"))

    # 8 how full the runs disk is, to scale
    x = QX[2]
    s.folder(x + 4, TOP2 - 2, 110, 66, fill="input", label="`~/spectio-runs`")
    s.text(x + 128, TOP2 + 16, "the default runs root,", size=12.5, anchor="start")
    s.text(x + 128, TOP2 + 36, "on the EMBL `/home`, NFS", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 128, TOP2 + 56, "23.75 TiB, from `df` in KiB", size=12.5, anchor="start", colour=t.dim)
    used, total = 24486338560, 25501368320
    bx, by, bw = x + 4, TOP2 + 96, 320
    uw = bw * used / total
    bar(s, bx, by, uw, 26, "problem")
    bar(s, bx + uw, by, bw - uw, 26, "done")
    s.text(bx + 10, by + 18, "used, 96.02%: `df` shows 97%", size=12, anchor="start")
    th = bx + bw * 0.90
    s.line(th, by - 12, th, by + 38, dashed=True, colour=t.warn, passes=1)
    s.text(th - 4, by - 16, "90%, `FULL_PCT`", size=12, anchor="end")
    s.text(bx + bw, by + 64, "the green sliver: 968.0 GiB free", size=12, anchor="end", colour=t.dim)
    for pct in (0, 50, 100):
        s.text(bx + bw * pct / 100, by + 44, f"{pct}%", size=11, colour=t.dim)
    s.text(x, TOP2 + 184, "10 GiB, `MIN_FREE`: 0.04% of this disk", size=12, anchor="start",
           colour=t.dim)
    s.step(x + QW / 2, CAP2, 8, "a nearly full runs disk, to scale")
    lines(s, x, CAP2 + 30, ("`runs_disk`: 90% used, rounded up",
                            "as `df` does, or under 10 GiB free",
                            "a runs root not made yet: its nearest",
                            "existing parent; unmeasurable: warn"))

    # 9 where it warns
    x = QX[3]
    s.terminal(x, TOP2 - 6, QW, 134, ("$ spectio doctor",
                                      "warn runs_disk <runs root> is on a nearly full",
                                      "  file system (968.0 GiB free, 97% used): point",
                                      "  SPECTIO_RUNS_ROOT (runs_root in spectio.toml,",
                                      "  spectio init --runs-root) at a larger scratch",
                                      "  or group file system"), size=10.5, line_h=16)
    s.cog(x + 16, TOP2 + 150, 8, fill="work")
    s.text(x + 34, TOP2 + 155, "`RunnerLoop._launch` logs it as a warning,", size=12, anchor="start")
    s.tick(x + 16, TOP2 + 176, size=6)
    s.text(x + 34, TOP2 + 181, "then submits the head anyway", size=12, anchor="start")
    s.step(x + QW / 2, CAP2, 9, "a warning, never a refusal")
    lines(s, x, CAP2 + 30, ("doctor: one `runs_disk` line, `ok` with",
                            "the free GiB, or `warn` with the way out",
                            "a launch: one warning just before the",
                            "head; a redelivered launch adds none"))

    note(s, QX[0], NOTE2, ("1 round, both approve · no blocker or", "major · CR-01 and -02 fixed in the docs,",
                           "CR-03 open"), w=QW)
    note(s, QX[1], NOTE2, ("to be validated, CR-01 and -02: that", "`3.13` replaces an installed 3.13.11,",
                           "the reinstall flags, other platforms"), w=QW, warn=True)
    note(s, QX[2], NOTE2, ("2 rounds, both approve · no blocker or", "major · SEC-P3FU74-01 minor, fixed in",
                           "7c338a02: an unsearchable parent crashed"), w=QW)
    note(s, QX[3], NOTE2, ("open: the 10 GiB floor is a guess, to be", "validated; quotas are not seen;",
                           "CR-P3FU74-01 to -03, minor"), w=QW)

    # == the batch simplifier, before and after; the tests =====================================
    band(s, LOW - 22, "batch simplify, before and after · 2 commits, 4 files, -13 +17 · re-review: "
         "code-reviewer and security-reviewer approve, no findings")

    # login shells of spectio doctor
    x, y = 50, LOW + 8
    s.text(x, y + 10, "`spectio doctor`, login shells", size=13.5, anchor="start", weight="bold")
    s.text(x, y + 34, "before, 3", size=12.5, anchor="start", colour=t.dim)
    for i, text in enumerate(("`which tmux sbatch`", "`which uv`", "`uv --version`")):
        shell(s, x + 72 + i * 132, y + 22, 124, "$ bash -l")
        s.text(x + 72 + i * 132 + 62, y + 90, text, size=11.5)
    s.cross(x + 72 + 132 + 62, y + 47, size=9)
    s.text(x, y + 124, "after, 2", size=12.5, anchor="start", colour=t.dim)
    for i, text in enumerate(("`which tmux sbatch uv`", "`uv --version`")):
        shell(s, x + 72 + i * 198, y + 112, 190, "$ bash -l")
        s.text(x + 72 + i * 198 + 95, y + 180, text, size=11.5)
    s.text(x, y + 212, "4ff68b38, CR-P3FU73-04: the paths go to", size=12.5, anchor="start")
    s.text(x, y + 232, "`_tools` and `_uv`; same lines, same order", size=12.5, anchor="start",
           colour=t.dim)

    # the socket rule, once
    x = 560
    s.text(x, y + 10, "the socket rule, written once", size=13.5, anchor="start", weight="bold")
    s.text(x, y + 34, "before", size=12.5, anchor="start", colour=t.dim)
    for i, where in enumerate(("`login._checked`", "`open_remote.check_socket`")):
        px = x + 60 + i * 190
        s.page(px, y + 22, 34, 44, fill="surface", lines=2)
        outlet(s, px + 50, y + 44, r=9, fill="problem")
        s.text(px + 66, y + 34, where.split(".")[0] + "`", size=11, anchor="start")
        s.text(px + 66, y + 52, "`." + where.split(".")[1], size=11, anchor="start")
    s.text(x, y + 124, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 60, y + 104, 34, 44, fill="surface", lines=2)
    outlet(s, x + 110, y + 126, r=9)
    s.text(x + 126, y + 118, "`ports.`", size=11, anchor="start")
    s.text(x + 126, y + 136, "`is_server_socket`", size=11, anchor="start")
    s.arrow(x + 252, y + 120, x + 300, y + 104)
    s.arrow(x + 252, y + 132, x + 300, y + 150)
    s.text(x + 306, y + 106, "`login`", size=11, anchor="start")
    s.text(x + 306, y + 156, "`open_remote`", size=11, anchor="start")
    s.text(x, y + 190, "`SOCKET` in `db_dir`, at most 107 bytes", size=12.5, anchor="start")
    s.text(x, y + 212, "d49f8450, CR-P3FU72-05 first half: the", size=12.5, anchor="start")
    s.text(x, y + 232, "messages and the `-L` regex unchanged", size=12.5, anchor="start", colour=t.dim)

    # tests, to scale
    x = 1030
    s.text(x, y + 10, "tests, to scale", size=13.5, anchor="start", weight="bold")
    s.text(x + 128, y + 10, "pytest, 0.25 px per test", size=12.5, anchor="start", colour=t.dim)
    for i, when in enumerate(("before", "after")):
        by = y + 24 + i * 30
        s.text(x, by + 16, when, size=12.5, anchor="start")
        bar(s, x + 60, by, 1096 * 0.25, 20, "bar_green")
        s.text(x + 70 + 1096 * 0.25, by + 16, "1096 passed", size=12.5, anchor="start")
    s.text(x + 60, y + 102, "and 1 skipped, 30 deselected, each time", size=12.5, anchor="start",
           colour=t.dim)
    s.tick(x + 8, y + 126, size=6)
    s.text(x + 24, y + 131, "ruff, mypy, lint-imports, `uv lock --check`", size=12.5, anchor="start")
    s.warning(x + 8, y + 154, size=8)
    s.text(x + 24, y + 159, "the web step not run: no `node_modules`", size=12.5, anchor="start")
    s.text(x + 24, y + 179, "in the worktree, and no `web/src` change", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, y + 212, "left alone: CR-P3FU73-05 and the test `UnixHTTP`,", size=12.5, anchor="start")
    s.text(x, y + 232, "both in tests of kept code", size=12.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: `serve.py`, `login.py`, `open_remote.py`, `ports.py`, `doctor.py`, "
           "`rundir.py` at d49f8450 · review records P3-fu72 to P3-fu74 · login-node audit 6 and 8",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b07-socket-uv-disk")
