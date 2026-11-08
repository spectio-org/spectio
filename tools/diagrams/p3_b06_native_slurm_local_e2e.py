#!/usr/bin/env python3
"""A native one-node Slurm in the cloud session, and `happy-local` end to end on both engines:
batch P3-B06 (steps P3-fu66 and P3-g7, wave W5), 2026-11-08.

Writes docs/assets/diagrams/p3-b06-native-slurm-local-e2e_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B06 at 09582fe0 (PRs 163 and 165 merged into
autopilot/integration between 0343f539 and 09582fe0; the batch code-simplifier made no commit):
- P3-fu66, PR 163: dev/slurm/native.sh `guard` (root by `id -u`; an inherited SLURM_CONF not its
  own; a slurm.conf or slurmdbd.conf whose first line is not MARK, a dangling link included;
  `down` without its own slurm.conf; `up` while /proc shows slurmctld, slurmd or slurmdbd, or a
  configless cache exists; built-ins and `id` only), PACKAGES slurm-wlm slurmdbd mariadb-server
  munge, `install_packages` (only the missing ones), `db_user` (umask 077, the password through
  `sed` into `mysql` on stdin and into slurmdbd.conf), `start_db` (`--bind-address=127.0.0.1`),
  `up` (munge, MariaDB, slurmdbd, cluster local, slurmctld, slurmd, node idle), `wait_for` (60
  tries, 1 s apart), `down` (daemons and MariaDB stopped; packages and configs kept), `status`;
  the header (Ubuntu 24.04, Slurm 23.11.4, MariaDB 10.11, cgroup v1);
  packages/spectio/tests/test_sacct_native.py and the P3-M9 Progress section FU-P3-66 (`up`
  logged "up in 1 s: cluster local, node vm (4 CPUs, 15574 MiB), partition debug"; 1 passed in
  42.63s; 35 server tests failing with a slurm.conf until `lone_host` was imported; 1038 passed,
  1 skipped, 30 deselected); tests/slurm/test_native.py 11 tests;
- P3-g7, PR 165: tests/local/e2e.sh (temporary home, mode 700, wheels 0.0.1, `uv tool install`,
  `spectio init --local`, `spectio serve --detach`, TMUX_TMPDIR in the home, HOME kept, home
  removed on a pass and kept on a fail, `RESULT e2e-local-<engine> pass|fail`; Nextflow
  `--profile test --profile local`, Snakemake `--profile local` and chunks 2);
  tests/slurm/e2e_client.py LOCAL_CHECKS (six names, as drawn); tests/scenarios/happy-local.yaml
  and happy-local-snakemake.yaml (each expect line names a check);
  spectio_server/sink.py `engine_ended=row.engine == "nextflow" and row.head_state in
  ENGINE_ENDED` (succeeded, failed; set by `onFlowComplete` in projector/nextflow.py);
  spectio/runner/types.py `LaunchRef.engine_ended: bool = False`; spectio/runner/loop.py
  `_report` (one `_read` then the report, no `end_grace_s` 60 wait and no `ended_failure` when
  engine_ended); api 7.1 note 2026-11-08; the client also waits 60 s (review record, commit
  55f03f4);
- findings: docs/reviews/code/P3-fu66.md and P3-g7.md. Every blocker and major is pinned:
  SEC-P3FU66-01 r1 (major), CR-P3FU66-01 r2 (blocker), CR-P3G7-07 r3 (major). IDs restart per
  round in P3-fu66, so each pin names its round;
- counts: the Python suite 1038 passed (P3-fu66) and 1043 passed, 1 skipped, 30 deselected at
  28ddcaa (P3-g7); `happy` end to end: Nextflow 65 tasks succeeded, Snakemake 67; 4 of 4 runs per
  engine after the fix; test_e2e_client.py run directly: 22 tests at 4fd93a7, 27 at b1be588;
- the batch simplifier: no change, -0 +0, HEAD still 09582fe0 (its report).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1780
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
WIDE = COL[3] + CW - COL[2]  # step 8 spans two columns

TOP1, CAP1, PIN1 = 165, 390, 510  # P3-fu66
TOP2, CAP2, PIN2 = 840, 1075, 1195  # P3-g7
LOW = 1420  # tests and the simplifier


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


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def strip(s: Sketch, x: float, y: float, w: float, text: str, fill: str, *, h: float = 22) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.1)
    s.text(x + 8, y + h - 6, text, size=12, anchor="start")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=606)
    t = theme
    s.heading(50, 58, "P3-B06 · a native Slurm in the cloud session, and `happy-local` on both engines",
              "wave W5 · steps P3-fu66 and P3-g7 · dev-env 4.1, 5 and 15.3 · api 7.1 · "
              "PRs 163 and 165 into `autopilot/integration`")

    # == P3-fu66: dev/slurm/native.sh =========================================================
    band(s, 140, "P3-fu66, PR 163, inbox 120 a · `dev/slurm/native.sh up` runs a real one-node Slurm "
         "with accounting in the session's own container, where sind cannot start on cgroup v1")

    # 1 guards, before anything
    x = COL[0]
    s.page(x + 4, TOP1 + 4, 118, 86, fill="done", lines=0)
    s.text(x + 14, TOP1 + 28, "`slurm.conf`", size=12, anchor="start")
    s.text(x + 14, TOP1 + 52, "line 1: the", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 14, TOP1 + 70, "marker", size=12.5, anchor="start", colour=t.dim)
    s.tick(x + 104, TOP1 + 70, size=7)
    s.page(x + 158, TOP1 + 4, 118, 86, fill="problem", lines=0)
    s.text(x + 168, TOP1 + 28, "`slurm.conf`", size=12, anchor="start")
    s.text(x + 168, TOP1 + 52, "a site's, or", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 168, TOP1 + 70, "a dead link", size=12.5, anchor="start", colour=t.dim)
    s.cross(x + 258, TOP1 + 70, size=8)
    s.lock(x + 14, TOP1 + 118, size=10, fill="gate")
    s.text(x + 32, TOP1 + 124, "root only, `id -u` is 0", size=12.5, anchor="start")
    s.cross(x + 14, TOP1 + 150, size=6)
    s.text(x + 32, TOP1 + 155, "refused: no apt, no daemon, no write", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 1, "guards, before anything")
    lines(s, x, CAP1 + 30, ("built-ins and `id` only, then refused:",
                            "a config without the marker line",
                            "a `SLURM_CONF` of a site, a configless",
                            "cache, Slurm daemons already running"))

    # 2 install what is missing
    x = COL[1]
    s.folder(x + 4, TOP1 + 8, 118, 92, fill="input")
    for i in range(3):
        s.page(x + 18 + i * 32, TOP1 + 40, 26, 34, fill="surface", lines=2)
    s.text(x + 63, TOP1 + 118, "`apt-get`", size=12.5)
    for i, name in enumerate(("`slurm-wlm`", "`slurmdbd`", "`mariadb-server`", "`munge`")):
        s.text(x + 136, TOP1 + 24 + i * 24, name, size=12, anchor="start")
    s.text(x, TOP1 + 150, "Ubuntu 24.04: Slurm 23.11.4,", size=12.5, anchor="start")
    s.text(x, TOP1 + 170, "MariaDB 10.11", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 2, "install what is missing")
    lines(s, x, CAP1 + 30, ("as root, the Ubuntu packages",
                            "a package already there: skipped",
                            "`down` stops the daemons only,",
                            "packages and configs stay"))

    # 3 configs and a secret
    x = COL[2]
    s.page(x + 4, TOP1 + 22, 58, 74, fill="gate", lines=2)
    s.lock(x + 54, TOP1 + 92, size=10, fill="gate")
    s.text(x, TOP1 + 124, "`native-db.pass`", size=12, anchor="start")
    s.text(x, TOP1 + 144, "root-only, made per install", size=12.5, anchor="start", colour=t.dim)
    s.arrow(x + 70, TOP1 + 40, x + 146, TOP1 + 32)
    s.text(x + 106, TOP1 + 26, "`sed`", size=12)
    s.page(x + 152, TOP1 + 2, 54, 66, fill="surface", lines=3)
    s.text(x + 179, TOP1 + 84, "`slurmdbd`", size=11)
    s.page(x + 220, TOP1 + 2, 54, 66, fill="surface", lines=3)
    s.text(x + 247, TOP1 + 84, "`slurm`", size=11)
    s.arrow(x + 70, TOP1 + 72, x + 172, TOP1 + 112)
    s.text(x + 112, TOP1 + 76, "stdin", size=12, colour=t.dim)
    s.bucket(x + 214, TOP1 + 100, 70, 44, fill="neutral")
    s.text(x + 214, TOP1 + 126, "MariaDB", size=12)
    s.text(x, TOP1 + 172, "never printed, never on a command line", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 3, "two configs and a secret")
    lines(s, x, CAP1 + 30, ("both configs begin with the marker",
                            "the password: in no shell variable,",
                            "so neither `ps` nor `set -x` shows it",
                            "MariaDB listens on 127.0.0.1"))

    # 4 start, then wait for idle
    x = COL[3]
    s.hpc_node(x + 4, TOP1 + 6, 62, 112, busy=4, slots=5)
    for i, name in enumerate(("`munged`", "MariaDB", "`slurmdbd`", "`slurmctld`", "`slurmd`")):
        y = TOP1 + 18 + i * 24
        s.cog(x + 92, y, 7, fill="work")
        s.text(x + 106, y + 5, name, size=12.5, anchor="start")
    s.text(x, TOP1 + 150, "`sacctmgr add cluster local`", size=12, anchor="start")
    s.hourglass(x + 8, TOP1 + 167, size=6)
    s.text(x + 22, TOP1 + 172, "each wait: 60 tries, 1 s apart", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 4, "start, then wait for idle")
    lines(s, x, CAP1 + 30, ("in this order, until idle",
                            "logged: up in 1 s, `demo-hpc-node1`,",
                            "4 CPUs, 15574 MiB, partition `debug`",
                            "`status`: daemons, node, cluster"))

    # 5 sacct on a real Slurm
    x = COL[4]
    s.terminal(x, TOP1, CW, 100, ("$ SPECTIO_NATIVE_SLURM=1 uv run",
                                  "  pytest -m native_slurm",
                                  "1 passed in 42.63s"), size=11.5, line_h=19)
    strip(s, x, TOP1 + 116, 236, "its WorkDir: its `sacct` row", "done")
    s.tick(x + 256, TOP1 + 127, size=7)
    strip(s, x, TOP1 + 146, 236, "another WorkDir: no row", "neutral")
    s.tick(x + 256, TOP1 + 157, size=7)
    s.step(x + CW / 2, CAP1, 5, "`sacct` on a real Slurm")
    lines(s, x, CAP1 + 30, ("one `sbatch` job of about 100 MB",
                            "`sacct_jobs` of FU-P3-53, bound",
                            "to the WorkDir, on 23.11 only;",
                            "25.11 and 26.05 to be validated"))

    for a, b in zip(COL[:4], COL[1:]):
        s.arrow(a + CW + 2, TOP1 + 50, b - 3, TOP1 + 50)

    y = pin(s, COL[0], PIN1, "SEC-P3FU66-01 r1", "major",
            ("the guard looked for a foreign config", "only: a site `SLURM_CONF`, a configless",
             "node, running daemons got past it"),
            "fixed in ff0bf276, all refused first")
    pin(s, COL[0], y + 10, "CR-P3FU66-01 r2", "blocker",
        ("that fix made `native.sh` fail", "shellcheck, SC1007 on `own=`"),
        "fixed in b3ab671d, an explicit empty value")
    note(s, COL[1], PIN1, ("3 rounds · code-reviewer: approve,", "changes, approve · security-reviewer:",
                           "changes, approve; not asked in r3"))
    note(s, COL[2], PIN1, ("open, FU-P3-67: a reused password", "file is not checked, SEC-03 r1 and r2;",
                           "the MariaDB log sits in a directory", "the `slurm` user owns, SEC-04 r1"))
    note(s, COL[3], PIN1, ("open, FU-P3-67: Slurm ports 6817 to", "6819 on every interface, the munge",
                           "key reused, SEC-02 r1; daemons found", "by name only, SEC-05 r1"))
    y = note(s, COL[4], PIN1, ("side effect, fixed: with a `slurm.conf`", "35 server tests failed, This machine",
                               "looks shared; two test modules now", "import the `lone_host` fixture"))
    note(s, COL[4], y + 10, ("not run: a first install from nothing,", "the `slurm-mini` cases, FU-P3-60"))

    # == P3-g7: happy-local on both engines ======================================================
    band(s, TOP2 - 25, "P3-g7, PR 165, P2 10.8 · `tests/local/e2e.sh` runs the synthetic `happy` from the "
         "wheels on Nextflow and on Snakemake, and the runner now reports a Nextflow end at once")

    # 6 from the wheels, in a temporary home
    x = COL[0]
    s.folder(x + 4, TOP2 + 4, 150, 100, fill="input")
    for i in range(3):
        s.page(x + 22 + i * 40, TOP2 + 40, 30, 40, fill="surface", lines=2)
    s.lock(x + 148, TOP2 + 100, size=10, fill="gate")
    s.text(x + 172, TOP2 + 24, "temp home", size=13.5, anchor="start", weight="bold")
    s.text(x + 172, TOP2 + 46, "mode 700,", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 172, TOP2 + 66, "three wheels", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 172, TOP2 + 86, "at 0.0.1", size=12.5, anchor="start", colour=t.dim)
    s.text(x, TOP2 + 134, "`spectio init --local`", size=12, anchor="start")
    s.text(x, TOP2 + 156, "`spectio serve --detach`", size=12, anchor="start")
    s.text(x, TOP2 + 178, "tmux on a socket in that home", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP2, 6, "a throwaway home")
    lines(s, x, CAP2 + 30, ("`uv build`, then `uv tool install`",
                            "config, database, runs all inside",
                            "removed on a pass, kept on a fail",
                            "`HOME` kept: uv and Nextflow caches"))

    # 7 launched through the API
    x = COL[1]
    s.page(x + 4, TOP2 + 14, 58, 76, fill="surface", lines=3)
    s.text(x + 33, TOP2 + 110, "`e2e_client.py`", size=11.5)
    s.arrow(x + 70, TOP2 + 52, x + 118, TOP2 + 52)
    s.text(x + 94, TOP2 + 42, "API", size=12, colour=t.dim)
    s.text(x + 128, TOP2 + 14, "Nextflow", size=12.5, anchor="start")
    s.pipeline(x + 128, TOP2 + 22, ("", "", ""), w=28, h=20, gap=16)
    s.text(x + 128, TOP2 + 74, "Snakemake", size=12.5, anchor="start")
    s.pipeline(x + 128, TOP2 + 82, ("", "", ""), w=28, h=20, gap=16, fills=("docs", "docs", "docs"))
    s.text(x, TOP2 + 156, "`-profile test,local`", size=12, anchor="start")
    s.text(x, TOP2 + 178, "profile `local`, `chunks=2`", size=12, anchor="start")
    s.step(x + CW / 2, CAP2, 7, "launched through the API")
    lines(s, x, CAP2 + 30, ("`e2e_client.py`, stdlib only,",
                            "the client P1 Task 22 will reuse",
                            "the synthetic `happy` pipeline,",
                            "counts compared with its golden"))

    # 8 a Nextflow end, reported at once (two columns wide)
    x = COL[2]
    s.page(x + 4, TOP2, 40, 50, fill="input", lines=2)
    s.text(x + 54, TOP2 + 20, "`onFlowComplete`", size=12, anchor="start")
    s.text(x + 54, TOP2 + 40, "in the spool", size=12.5, anchor="start", colour=t.dim)
    s.arrow(x + 186, TOP2 + 22, x + 220, TOP2 + 22)
    s.text(x + 228, TOP2 + 20, "`head_state`", size=12, anchor="start")
    s.text(x + 228, TOP2 + 40, "succeeded or failed", size=12.5, anchor="start", colour=t.dim)
    s.arrow(x + 372, TOP2 + 22, x + 406, TOP2 + 22)
    s.text(x + 414, TOP2 + 20, "`engine_ended`", size=12, anchor="start")
    s.text(x + 414, TOP2 + 40, "Nextflow only", size=12.5, anchor="start", colour=t.dim)

    x0, px = x + 110, 6  # the head exits at x0; 6 px per second
    s.text(x, TOP2 + 92, "before", size=13, anchor="start")
    bar(s, x0, TOP2 + 76, 60 * px, 22, "neutral")
    s.hourglass(x0 + 14, TOP2 + 87, size=6)
    s.text(x0 + 30, TOP2 + 92, "held for the spool grace, 60 s", size=12.5, anchor="start")
    s.text(x, TOP2 + 122, "the client", size=12.5, anchor="start", colour=t.dim)
    s.line(x0, TOP2 + 117, x0 + 60 * px, TOP2 + 117, dashed=True, colour=t.dim)
    s.text(x0 + 30, TOP2 + 112, "waits 60 s too", size=12, anchor="start", colour=t.dim)
    s.cross(x0 + 60 * px + 14, TOP2 + 104, size=7)
    s.text(x0 + 60 * px + 28, TOP2 + 100, "failed once:", size=12, anchor="start")
    s.text(x0 + 60 * px + 28, TOP2 + 118, "`head.exit 0`", size=11.5, anchor="start")
    for sec in (0, 30, 60):
        s.line(x0 + sec * px, TOP2 + 126, x0 + sec * px, TOP2 + 132, colour=t.dim, passes=1)
        s.text(x0 + sec * px, TOP2 + 146, f"{sec} s", size=12, colour=t.dim)
    s.text(x0 + 16, TOP2 + 146, "the head exits", size=12, anchor="start", colour=t.dim)
    s.text(x, TOP2 + 180, "now", size=13, anchor="start")
    s.page(x0, TOP2 + 160, 22, 28, fill="done", lines=0)
    s.text(x0 + 32, TOP2 + 180, "one last spool read", size=12.5, anchor="start")
    s.tick(x0 + 168, TOP2 + 175, size=7)
    s.text(x0 + 184, TOP2 + 180, "the exit reported at once, no failure", size=12.5, anchor="start")
    s.text(x, TOP2 + 208, "a Snakemake exit code already ends its launch, Assumption 16, unchanged",
           size=12.5, anchor="start", colour=t.dim)
    s.step(x + WIDE / 2, CAP2, 8, "a Nextflow end, reported at once")
    lines(s, x, CAP2 + 30, ("`sink.py`: `engine_ended` only when",
                            "the engine is `nextflow` and its",
                            "`head_state` is succeeded or failed",
                            "`types.py`: the field, default False"))
    lines(s, COL[3], CAP2 + 30, ("`loop.py` `_report`: one last read,",
                                 "then the exit code, with no grace",
                                 "and no `ended_failure`",
                                 "api 7.1, note 2026-11-08"))

    # 9 six checks, then RESULT
    x = COL[4]
    checks = ("run succeeded", "head in its own session", "counts equal the golden",
              "head.exit 0, as the run reads it", "no spool drop", "no head left")
    for i, check in enumerate(checks):
        y = TOP2 + 10 + i * 22
        s.tick(x + 8, y, size=5)
        s.text(x + 22, y + 5, check, size=12.5, anchor="start")
    s.terminal(x, TOP2 + 146, CW, 60, ("RESULT e2e-local-nextflow pass",), size=11.5)
    s.step(x + CW / 2, CAP2, 9, "six checks, then RESULT")
    lines(s, x, CAP2 + 30, ("each `expect` line of the scenario",
                            "names a check, or the run fails",
                            "Nextflow 65 tasks, Snakemake 67",
                            "after the fix: 4 of 4 pass each"))

    s.arrow(COL[0] + CW + 2, TOP2 + 52, COL[1] - 3, TOP2 + 52)
    s.arrow(COL[1] + CW + 2, TOP2 + 52, COL[2] - 3, TOP2 + 52)
    s.arrow(COL[2] + WIDE + 2, TOP2 + 52, COL[4] - 3, TOP2 + 52)

    note(s, COL[0], PIN2, ("needs a host that is not shared:", "with `/etc/slurm` or `sinfo`, serve",
                           "refuses the API, so the runs here", "hid them under `unshare -m`"), warn=True)
    note(s, COL[1], PIN2, ("4 rounds · code-reviewer approve", "in each · security-reviewer in r3",
                           "and r4, on the runner fix: approve"))
    pin(s, COL[2], PIN2, "CR-P3G7-07 r3", "major",
        ("no last spool read before the report:", "an `onFlowError` written after",
         "`onFlowComplete` could be lost"),
        "fixed in 28ddcaa, `LateEventLauncher`")
    y = note(s, COL[3], PIN2, ("fixed in 28ddcaa, SEC-P3G7-01:", "`nextflow` only, so a Snakemake",
                               "spool never skips its last read"))
    note(s, COL[3], y + 10, ("open, FU-P3-69: the last read is one", "capped read, 5000 lines, SEC-05;",
                             "ended means terminal: no test, SEC-04"))
    y = note(s, COL[4], PIN2, ("fixed in b1be588, CR-P3G7-01:", "`Local` sat after `unittest.main`, so",
                               "run directly 22 of 27 tests ran"))
    note(s, COL[4], y + 10, ("open, FU-P3-68: no head left checks", "the head only, CR-02; a failed run",
                             "leaves its head, CR-03; not in `ci.yml`"))

    # == tests, to scale, and the batch simplifier =============================================
    s.line(30, LOW - 14, W - 30, LOW - 14, dashed=True, colour=t.muted)
    s.text(50, LOW + 18, "tests, to scale", size=14, anchor="start", weight="bold")
    s.text(220, LOW + 18, "the Python suite, 0.38 px per test", size=12.5, anchor="start", colour=t.dim)
    suite = (("P3-fu66", 1038, "1038 passed, 1 skipped, 30 deselected"),
             ("P3-g7, 28ddcaa", 1043, "1043 passed, 1 skipped, 30 deselected"))
    for i, (where, n, label) in enumerate(suite):
        y = LOW + 32 + i * 30
        s.text(50, y + 16, where, size=12.5, anchor="start")
        bw = n * 0.38
        bar(s, 220, y, bw, 20, "bar_green")
        s.text(230 + bw, y + 16, label, size=13, anchor="start")

    y0 = LOW + 116
    s.text(50, y0 + 4, "`happy` end to end, tasks succeeded, 3 px per task", size=12.5, anchor="start",
           colour=t.dim)
    for i, (engine, n) in enumerate((("Nextflow", 65), ("Snakemake", 67))):
        y = y0 + 16 + i * 30
        s.text(50, y + 16, engine, size=12.5, anchor="start")
        bar(s, 220, y, n * 3, 20, "done")
        s.text(230 + n * 3, y + 16, f"{n} tasks, RESULT pass", size=12.5, anchor="start")

    y0 = LOW + 210
    s.text(50, y0 + 4, "`test_e2e_client.py` run directly, 6 px per test", size=12.5, anchor="start",
           colour=t.dim)
    for i, (where, n, fill, label) in enumerate((("4fd93a7", 22, "problem", "22 ran, `Local` skipped"),
                                                 ("b1be588", 27, "bar_green", "27 ran, OK"))):
        y = y0 + 16 + i * 30
        s.text(50, y + 16, where, size=12.5, anchor="start")
        bar(s, 220, y, n * 6, 20, fill)
        s.text(230 + n * 6, y + 16, label, size=12.5, anchor="start")

    sx, sy, sw, sh = 1000, LOW + 2, 550, 262
    s.shade(sx, sy, sw, sh, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 26, "batch simplify: no change, -0 +0", size=13.5, anchor="start", weight="bold")
    s.text(sx + 14, sy + 52, "read: the non-test diff, 3 files, about 12 lines added", size=12.5,
           anchor="start", colour=t.dim)
    for i, (code, what) in enumerate((("`sink.py`", "selects `head_state`, sets `engine_ended`"),
                                      ("`types.py`", "the `engine_ended` field, its docstring"),
                                      ("`loop.py`", "the `engine_ended` branch in `_report`"))):
        y = sy + 64 + i * 28
        s.page(sx + 14, y, 18, 22, fill="surface", lines=0)
        s.text(sx + 40, y + 16, code, size=12, anchor="start")
        s.text(sx + 130, y + 16, what, size=12.5, anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 168, "kept, each carries behaviour:", size=12.5, anchor="start")
    kept = ("the `nextflow` test in `sink.py`: no skip for Snakemake",
            "the two `engine_ended` branches of `_report`",
            "the field, two users; the comments say why")
    for i, row in enumerate(kept):
        s.tick(sx + 22, sy + 186 + i * 22, size=5)
        s.text(sx + 36, sy + 191 + i * 22, row, size=12.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: `native.sh`, `e2e.sh`, `e2e_client.py`, `sink.py`, `loop.py`, "
           "`types.py` at 09582fe0 · review records P3-fu66, P3-g7", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b06-native-slurm-local-e2e")
