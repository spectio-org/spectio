#!/usr/bin/env python3
"""`spectio serve`, its start and the index rebuilt from the run directories: step P3, P1 Task 11,
2026-10-30.

Writes docs/assets/diagrams/p3-t11-serve_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t11 at fd2ae94:
- packages/spectio-server/src/spectio_server/serve.py: started() refuses, as ServeError (exit 2 in
  cli/serve.py), a server.host other than LOOPBACK 127.0.0.1, and a runs root that open_private
  refuses (not the user's, or group or other write bits); _lock: `<db dir>/serve.lock`, flock
  LOCK_EX|LOCK_NB, "another spectio serve (pid N) runs on this node", then the pid written;
  _bind: 127.0.0.1 and the recorded port only, a taken port refused naming the owner's uid from
  /proc/net/tcp, "Spectio never picks one itself"; _write_state: `<data dir>/server.json` created
  with O_EXCL; one that names another host is refused unless --force; one of this host is
  replaced (the lock was free); _remove_state removes it at a clean stop if it is still ours;
  boot(): open_db, ensure_tenancy, rebuild_index, then on executor local one loop.tick() and the
  `spectio-runner` thread; on SLURM no runner loop (P1 Task 10); uvicorn on the bound socket,
  proxy_headers False; start_text: local "Open this page in a browser on this machine", SLURM an
  `ssh -N -L` tunnel line; "Sign-in comes with P1 Task 12";
- spectio/config.py: DEFAULT_PORT 8080, LOOPBACK; cli/main.py: `spectio serve --force`;
- spectio_server/app.py: the only route is GET /, a plain page, docs, redoc and openapi off;
- spectio_server/rebuild.py: MAX_RUNS 1000, MAX_BYTES 64 MiB per boot, the rest `deferred`;
  names already in the index passed over, a name that is not RUN_ID, a refused directory or a bad
  manifest `skipped`; manifest `.spectio/run.json` strict (extra forbid), run ID must be the
  directory's name, paths from run_paths; _state: launch-failed.json gives failed with its class
  (launch_error if unknown) and, with no message, "The launch failed (index rebuilt)."
  (CR-P3T11-06, b9b94f2); no head.pid gives cancelled under the `cancel` marker, else failed
  head_lost; else queued, or cancelling under the marker, the launch keeping `<pid>.<start>`;
  _add: one transaction per run with its launch; source "local" when the location starts with
  "/", else "git" (CR-P3T11-04, b9b94f2), one workflows row per location and engine;
- tests: packages/spectio-server/tests/test_serve.py and tests/security/test_req1_bind.py (no
  test count, so that the figure does not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1140
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 150  # the pictograms of the start
TXT = ROW + 150  # the captions
NO = TXT + 128  # the refusals
LOW = 580  # the rebuild band
FOOT = 980  # the start text and the SLURM note


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def refusal(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    """What the step refuses: exit 2, nothing left behind."""
    s.cross(x + 14, y - 5, size=9)
    for i, row in enumerate(rows):
        s.text(x + 34, y + i * 20, row, size=13, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def socket_plug(s: Sketch, cx: float, cy: float, r: float = 34) -> None:
    """A wall socket: the port, bound on loopback."""
    s.circle(cx, cy, r, fill="input", width=2.2)
    s.poly([(cx - 13, cy - 12), (cx - 7, cy - 12), (cx - 7, cy + 4), (cx - 13, cy + 4)], fill="surface")
    s.poly([(cx + 7, cy - 12), (cx + 13, cy - 12), (cx + 13, cy + 4), (cx + 7, cy + 4)], fill="surface")
    s.circle(cx, cy + 16, 4, fill="surface")


def state_tag(s: Sketch, x: float, y: float, w: float, label: str, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + 28), (x, y + 28)], fill=fill, amount=0.5)
    s.text(x + w / 2, y + 19, label, size=13.5)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=111)
    t = theme
    s.heading(50, 58, "P3 Task 11 · `spectio serve`, one process on 127.0.0.1",
              "the app, the runner loop and the index · architecture 7.1 and 7.2 · dev-env 15.3 req. 1 "
              "and 10 · every refusal exits 2 before anything is left behind")

    # 1 -- loopback, a private runs root ---------------------------------------------------------
    x = COL[0]
    s.hpc_node(x + 20, ROW - 6, 56, 74, busy=1)
    s.text(x + 48, ROW + 92, "`127.0.0.1`", size=13)
    s.folder(x + 130, ROW + 4, 120, 70, fill="input", label="runs root")
    s.lock(x + 238, ROW + 76, size=13, fill="done")
    s.text(x + 190, ROW + 104, "yours, others cannot write", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "loopback only")
    lines(s, x, TXT + 30, ("no `--host` flag",
                           "`[server] host` exists only",
                           "to be refused by name",
                           "the runs root: dev-env req. 10"))
    refusal(s, x, NO, ("a host other than 127.0.0.1,",
                       "a runs root not yours, or loose"))

    # 2 -- one server per node -------------------------------------------------------------------
    x = COL[1]
    s.folder(x + 30, ROW + 4, 140, 84, fill="neutral", label="")
    s.text(x + 100, ROW + 36, "db dir", size=13, colour=t.dim)
    s.page(x + 78, ROW + 44, 40, 50, fill="surface", lines=1)
    s.lock(x + 98, ROW + 78, size=11, fill="gate")
    s.text(x + 220, ROW + 30, "`flock`", size=13)
    s.text(x + 220, ROW + 52, "holds", size=12.5, colour=t.dim)
    s.text(x + 220, ROW + 70, "this pid", size=12.5, colour=t.dim)
    s.text(x + 100, ROW + 118, "`serve.lock`, node-local", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "one server per node")
    lines(s, x, TXT + 30, ("per user and per node",
                           "held until the process ends",
                           "a free lock: no server here,",
                           "so a stale state file is dead"))
    refusal(s, x, NO, ("held: another `spectio serve`",
                       "pid N runs on this node"))

    # 3 -- the recorded port ---------------------------------------------------------------------
    x = COL[2]
    socket_plug(s, x + 80, ROW + 42)
    s.text(x + 80, ROW + 104, "`127.0.0.1:8080`", size=13)
    s.text(x + 200, ROW + 30, "the port", size=13.5, colour=t.dim)
    s.text(x + 200, ROW + 50, "`spectio init`", size=13)
    s.text(x + 200, ROW + 70, "recorded", size=13.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "the recorded port")
    lines(s, x, TXT + 30, ("bound before the boot",
                           "default 8080, or `--port` at init",
                           "the owner's uid read from",
                           "`/proc/net/tcp`"))
    refusal(s, x, NO, ("taken: refused, its uid named",
                       "Spectio never picks another"))

    # 4 -- the state file ------------------------------------------------------------------------
    x = COL[3]
    s.folder(x + 20, ROW + 4, 140, 84, fill="docs", label="")
    s.text(x + 90, ROW + 36, "data dir", size=13, colour=t.dim)
    s.page(x + 70, ROW + 44, 40, 50, fill="surface", lines=2)
    s.text(x + 90, ROW + 118, "`server.json`, `O_EXCL`", size=13, colour=t.dim)
    s.text(x + 180, ROW + 24, "host, port, pid,", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 180, ROW + 42, "db dir, start", size=12.5, anchor="start", colour=t.dim)
    s.hpc_node(x + 196, ROW + 56, 30, 40, busy=1, slots=2)
    s.hpc_node(x + 236, ROW + 56, 30, 40, busy=0, slots=2)
    s.step(x + CW / 2, TXT, 4, "the state file")
    lines(s, x, TXT + 30, ("this node's: a dead server's,",
                           "replaced",
                           "removed at a clean stop,",
                           "if it is still ours"))
    refusal(s, x, NO, ("another node's: refused,",
                       "unless `spectio serve --force`"))

    # 5 -- boot ----------------------------------------------------------------------------------
    x = COL[4]
    s.bucket(x + 40, ROW + 14, 54, 58, fill="neutral")
    s.text(x + 40, ROW + 50, "DB", size=13, colour=t.dim)
    s.cog(x + 120, ROW + 40, 13, fill="work")
    s.browser(x + 160, ROW, 116, 84, url="")
    s.text(x + 218, ROW + 50, "GET /", size=12.5)
    s.text(x + 218, ROW + 70, "a plain page", size=12, colour=t.dim)
    s.text(x + 140, ROW + 118, "uvicorn on the bound socket", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "boot, then serve")
    lines(s, x, TXT + 30, ("the database, the tenancy rows",
                           "the index rebuilt, below",
                           "one runner tick: adopt heads,",
                           "replay spools, then its thread"))
    s.tick(x + 14, NO - 5, size=8, colour=t.ink)
    s.text(x + 34, NO, "no data route yet:", size=13, anchor="start")
    s.text(x + 34, NO + 20, "sign-in comes with Task 12", size=13, anchor="start", colour=t.dim)

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 42, cx + CW + 23, ROW + 42)

    # the rebuild ---------------------------------------------------------------------------------
    s.line(30, LOW - 64, W - 30, LOW - 64, dashed=True, colour=t.muted)
    s.text(50, LOW - 74, "inside the boot: `rebuild_index`, the run directories the index lacks, "
           "oldest first", size=14, anchor="start", colour=t.dim)
    s.arc(COL[4] + 60, NO + 40, 200, LOW - 30, lift=-30, dashed=True, colour=t.dim)

    # a -- walk the runs root
    s.folder(50, LOW - 20, 330, 250, fill="input")
    s.text(70, LOW + 14, "runs root", size=14, anchor="start", weight="bold")
    entries = (("`run_01K8T2F1`", "new: read it", True, "folder"),
               ("`run_01K8T0AA`", "in the index: passed over", None, "folder"),
               ("`notes`", "not a run ID: skipped", False, "page"),
               ("`run_01K8T1ZZ`", "symlink, loose or not yours", False, "link"))
    for i, (name, note, ok, kind) in enumerate(entries):
        y = LOW + 34 + i * 46
        if kind == "folder":
            s.folder(70, y, 34, 26, fill="surface" if ok is not False else "problem")
        elif kind == "page":
            s.page(76, y - 2, 22, 30, fill="problem", lines=0)
        else:
            s.link(87, y + 13, size=13)
        s.text(116, y + 13, name, size=12.5, anchor="start")
        s.text(116, y + 31, note, size=12.5, anchor="start", colour=t.dim)
        if ok is True:
            s.tick(352, y + 14, size=7)
        elif ok is False:
            s.cross(352, y + 14, size=7)
        else:
            s.text(352, y + 20, "-", size=16, colour=t.dim)
    s.text(215, LOW + 260, "a · walk under req. 10", size=17)
    s.text(215, LOW + 284, "refused: skipped and counted", size=12.5, colour=t.dim)

    # b -- caps
    s.arrow(392, LOW + 70, 432, LOW + 70)
    s.text(500, LOW - 4, "at most 1000 runs", size=14)
    s.text(500, LOW + 16, "and 64 MiB of manifests", size=14)
    s.poly([(440, LOW + 30), (560, LOW + 30), (520, LOW + 100), (480, LOW + 100)], fill="gate", amount=0.8)
    s.text(500, LOW + 58, "per boot", size=12.5, colour=t.dim)
    s.arrow(500, LOW + 104, 500, LOW + 140, dashed=True, colour=t.dim)
    s.hourglass(500, LOW + 160, size=12)
    s.text(500, LOW + 196, "the rest waits", size=13.5, colour=t.dim)
    s.text(500, LOW + 216, "for the next boot", size=13.5, colour=t.dim)
    s.text(500, LOW + 260, "b · caps", size=17)
    s.text(500, LOW + 284, "counted as deferred", size=12.5, colour=t.dim)

    # c -- the manifest
    s.arrow(540, LOW + 66, 690, LOW + 66)
    s.page(700, LOW + 20, 74, 96, fill="surface", lines=4)
    s.magnifier(764, LOW + 86, 18)
    s.text(740, LOW + 150, "`.spectio/run.json`", size=13)
    lines(s, 660, LOW + 178, ("strict, extra fields refused",
                              "run ID is the dir's name",
                              "paths derived, never read"), size=12.5)
    s.text(740, LOW + 260, "c · the manifest", size=17)

    # d -- what the launch directory holds decides the row
    fan = 840
    rows = (
        (LOW - 14, "`launch-failed.json`", "problem",
         (("failed", "problem", 90),),
         ("its class, else `launch_error`;", "no message: the launch failed,", "index rebuilt"),
         "CR-P3T11-06"),
        (LOW + 92, "no `head.pid`", "neutral",
         (("cancelled", "neutral", 104), ("failed", "problem", 90)),
         ("under a `cancel` marker,", "else failed `head_lost`"),
         None),
        (LOW + 182, "`head.pid`", "done",
         (("queued", "work", 90), ("cancelling", "neutral", 112)),
         ("the launch keeps `pid.start`:", "the runner adopts the head", "and replays its spool from 0"),
         None),
    )
    for y, file, fill, tags, notes, finding in rows:
        s.arrow(fan, LOW + 70, 900, y + 26, colour=t.dim)
        s.page(910, y, 34, 44, fill=fill, lines=2)
        if file == "no `head.pid`":
            s.cross(927, y + 22, size=10)
        s.text(956, y + 18, file, size=13, anchor="start")
        tx = 956
        for label, tfill, w in tags:
            state_tag(s, tx, y + 30, w, f"`{label}`", tfill)
            tx += w + 12
        for i, note in enumerate(notes):
            s.text(1250, y + 14 + i * 20, note, size=12.5, anchor="start",
                   colour=t.ink if i == 0 else t.dim)
        if finding:
            s.text(956, y + 82, f"fixed: {finding}", size=12, anchor="start", colour=t.accent)
    s.text(1200, LOW + 284, "d · the launch directory decides the state", size=17)

    # the workflow row and the transaction
    s.shade(50, LOW + 306, 1500, 70, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(78, LOW + 330, size=11)
    s.text(100, LOW + 336, "one transaction per run, with its launch: an interrupted boot leaves whole "
           "runs only, the next boot adds the rest", size=13.5, anchor="start")
    s.folder(66, LOW + 348, 26, 20, fill="docs")
    s.text(100, LOW + 364, "the workflow: a location starting with a slash is `local`, any other is "
           "`git`; one `workflows` row per location, one engine", size=13.5, anchor="start",
           colour=t.dim)
    s.text(1530, LOW + 364, "fixed: CR-P3T11-04", size=12, anchor="end", colour=t.accent)

    # start text, local and SLURM -------------------------------------------------------------------
    s.terminal(50, FOOT, 760, 118, ("$ spectio serve",
                                    "Spectio 0.0.1 is running on node1, port 8080.",
                                    "Open this page in a browser on this machine:  http://127.0.0.1:8080/",
                                    "Sign-in comes with P1 Task 12: until then this build is local-only."),
               size=12.5, line_h=20)
    s.text(840, FOOT + 20, "executor local", size=15, anchor="start", weight="bold")
    s.text(840, FOOT + 42, "the runner thread starts with the server", size=13.5, anchor="start",
           colour=t.dim)
    s.hpc_node(1180, FOOT + 4, 44, 58, busy=2)
    s.text(1240, FOOT + 20, "executor slurm", size=15, anchor="start", weight="bold")
    s.text(1240, FOOT + 42, "the start text adds an `ssh -N -L` tunnel;", size=13.5, anchor="start",
           colour=t.dim)
    s.text(1240, FOOT + 62, "no runner loop until the tmux", size=13.5, anchor="start", colour=t.dim)
    s.text(1240, FOOT + 82, "launcher, P1 Task 10", size=13.5, anchor="start", colour=t.dim)
    s.text(840, FOOT + 82, "Ctrl-C or SIGTERM: a clean stop,", size=13.5, anchor="start", colour=t.dim)
    s.text(840, FOOT + 102, "undone in reverse order", size=13.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 16, ("CR",))
    s.text(W - 50, H - 16, "source: spectio_server/serve.py, rebuild.py, app.py · dev-env 15.3 · "
           "P1 Task 11", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t11-serve")
