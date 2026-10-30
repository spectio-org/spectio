#!/usr/bin/env python3
"""`spectio init` and `spectio doctor`: step P3, P1 Task 8, 2026-10-30.

Writes docs/assets/diagrams/p3-t08-init-doctor_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t08 at 179b80a:
- packages/spectio/src/spectio/config.py: Settings layers (flags, then SPECTIO_* variables, then
  spectio.toml, then defaults); config_path() is $SPECTIO_CONFIG or ~/.spectio/spectio.toml;
  port Field(8080, ge=1024, le=65535); db_dir None means default_db_dir() at each start;
  write_config renders, tomllib.loads the text, writes a temp file O_EXCL|O_NOFOLLOW 0600, fsync,
  os.replace;
- packages/spectio/src/spectio/cli/init.py: run_init refuses local mode off Linux ("Local mode
  needs Linux in 0.0.1"), --partition/--account with local, a bad flag or spectio.toml (exit 2);
  _init imports spectio_server.bootstrap first ("install spectio[server]"); _runs_root (a chosen
  one must exist; others cannot write, 0o022); _private_dir(strict=True) for the config directory
  and the data directory (O_DIRECTORY|O_NOFOLLOW, fstat, this uid, mask 0o077, "chmod 700");
  db_dir: --db-dir checked, else server.default_db_dir(), never recorded; _free_port(8080) on
  127.0.0.1 unless a port is set (kept by spectio.toml on the next init); host gethostname();
  _engines via loginshell.which (bash -l, cleared environment, command -v), warning "give it with
  --nextflow"; _unix_user() from pwd.getpwuid(os.getuid()); server.init_store; write_config;
- packages/spectio/src/spectio/loginshell.py: KEEP = HOME USER LOGNAME SHELL LANG TMPDIR;
- packages/spectio-server/src/spectio_server/bootstrap.py: init_store / _tenancy (principal
  kind user, project default, environment kind and config runs_root, runner with version; run
  again: environment updated, nothing added); db_checks (sqlite, db_dir: missing warn, not private
  warn when the default else fail, NETWORK_FS fail, else ok);
- packages/spectio-server/src/spectio_server/store/db.py: preferred_db_dir $TMPDIR or
  /tmp/spectio-<uid>; default_db_dir mkdtemp fallback for a squatted path;
- packages/spectio/src/spectio/cli/doctor.py: checks() order and statuses, exit 1 on any fail;
- tests: packages/spectio/tests/test_init.py and test_doctor.py.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 990
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
TOP = 128  # the command and its settings
ROW = 400  # the pictograms of what init creates
TXT = ROW + 150  # the captions
DOC = 770  # doctor


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=81)
    t = theme
    s.heading(50, 58, "P3 Task 8 · spectio init sets a login node up, spectio doctor checks it",
              "`spectio.cli.init`, `spectio.cli.doctor`, `spectio_server.bootstrap` · "
              "architecture 7.3, dev-env 15.3 · P1 Assumptions 10, 13, 18, 21, 23")

    # the command and where its settings come from -----------------------------------------------
    s.hpc_node(50, TOP + 10, 56, 74, busy=1)
    s.text(78, TOP + 108, "login node", size=13.5, colour=t.dim)
    s.terminal(124, TOP, 330, 112, ("$ spectio init",
                                    "# every flag has a default,",
                                    "# so spectio open runs it",
                                    "# unattended"), size=13)
    s.arrow(466, TOP + 56, 520, TOP + 56)

    layers = (("flags", "work"), ("`SPECTIO_` variables", "input"),
              ("`spectio.toml`", "docs"), ("built-in defaults", "neutral"))
    for i, (label, fill) in enumerate(layers):
        y = TOP - 6 + i * 30
        s.poly([(540 + i * 8, y), (790 + i * 8, y), (790 + i * 8, y + 26), (540 + i * 8, y + 26)],
               fill=fill, amount=0.5)
        s.text(665 + i * 8, y + 18, label, size=13.5)
    s.text(820, TOP + 14, "the upper", size=13.5, anchor="start", colour=t.dim)
    s.text(820, TOP + 34, "one wins", size=13.5, anchor="start", colour=t.dim)
    s.text(670, TOP + 134, "`spectio.toml`: `$SPECTIO_CONFIG`, else `~/.spectio/`", size=13,
           colour=t.dim)

    s.shade(940, TOP - 14, 610, 160, fill="problem", opacity=0.35, colour=t.muted, dashed=True)
    s.text(962, TOP + 12, "refused before anything is written, exit 2", size=15, anchor="start",
           weight="bold")
    refusals = ("local mode off Linux, from the flag, a variable or the file",
                "a port below 1024, which spectio open would refuse",
                "`--partition` or `--account` together with local mode",
                "a bad flag or `spectio.toml` value; no server package")
    for i, row in enumerate(refusals):
        s.cross(976, TOP + 38 + i * 26, size=7)
        s.text(996, TOP + 43 + i * 26, row, size=13.5, anchor="start")

    s.line(30, ROW - 66, W - 30, ROW - 66, dashed=True, colour=t.muted)
    s.text(50, ROW - 76, "then `spectio init` makes, in this order", size=14, anchor="start",
           colour=t.dim)

    # 1 -- the directories ---------------------------------------------------------------------
    x = COL[0]
    s.folder(x + 10, ROW, 120, 80, fill="input", label="`~/.spectio`")
    s.lock(x + 120, ROW + 80, size=13, fill="done")
    s.text(x + 70, ROW + 108, "0700", size=13, colour=t.dim)
    s.folder(x + 152, ROW, 120, 80, fill="input", label="`~/spectio-runs`")
    s.text(x + 212, ROW + 108, "shared disk", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "the directories")
    lines(s, x, TXT + 30, ("data and config: yours, 0700,",
                           "opened without following a symlink",
                           "an open one is refused: chmod 700",
                           "runs root: others cannot write it,",
                           "a chosen one must already exist"))

    # 2 -- the database directory ----------------------------------------------------------------
    x = COL[1]
    s.folder(x + 6, ROW + 4, 100, 70, fill="problem", label="taken")
    s.cross(x + 56, ROW + 92, size=8)
    s.arrow(x + 114, ROW + 40, x + 156, ROW + 40)
    s.text(x + 135, ROW + 30, "then", size=12.5, colour=t.dim)
    s.folder(x + 164, ROW + 4, 110, 70, fill="done", label="`mkdtemp`")
    s.lock(x + 264, ROW + 74, size=13, fill="done")
    s.text(x + 140, ROW + 116, "`$TMPDIR/spectio-<uid>`, node-local", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "the database directory")
    lines(s, x, TXT + 30, ("the default is found again at each start",
                           "and never written to `spectio.toml`",
                           "taken by another user: a fresh",
                           "private `mkdtemp` directory instead",
                           "`--db-dir`: checked, then recorded"))

    # 3 -- engines, port, host -------------------------------------------------------------------
    x = COL[2]
    s.terminal(x + 6, ROW - 8, 268, 92, ("$ bash -l", "command -v nextflow", "command -v snakemake"),
               size=12.5, line_h=19)
    s.text(x + 140, ROW + 108, "port 8080, else a free one", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "engines, port, host")
    lines(s, x, TXT + 30, ("engines from the login shell's PATH,",
                           "environment cleared but for HOME, USER,",
                           "LOGNAME, SHELL, LANG and TMPDIR",
                           "not found: a warning, give `--nextflow`",
                           "host: this node; the port is kept"))

    # 4 -- the first rows ------------------------------------------------------------------------
    x = COL[3]
    s.bucket(x + 58, ROW + 6, 92, 90, fill="neutral")
    s.text(x + 58, ROW + 52, "SQLite", size=13, colour=t.dim)
    rows = (("principal", "done"), ("project default", "input"), ("environment", "work"),
            ("runner", "docs"))
    for i, (name, fill) in enumerate(rows):
        y = ROW - 4 + i * 28
        s.poly([(x + 120, y), (x + 276, y), (x + 276, y + 22), (x + 120, y + 22)], fill=fill,
               amount=0.4)
        s.text(x + 198, y + 16, name, size=13)
    s.arrow(x + 106, ROW + 46, x + 118, ROW + 46)
    s.text(x + 140, ROW + 118, "`init_store`, P1 Assumption 18", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "the first rows")
    lines(s, x, TXT + 30, ("principal: the Unix user of the uid,",
                           "never USER or LOGNAME",
                           "environment: slurm or local,",
                           "and the runs root",
                           "run again: updated, nothing added"))

    # 5 -- spectio.toml --------------------------------------------------------------------------
    x = COL[4]
    s.page(x + 16, ROW - 8, 74, 98, fill="docs", lines=4)
    s.lock(x + 86, ROW + 86, size=13, fill="done")
    s.text(x + 54, ROW + 116, "0600", size=13, colour=t.dim)
    s.text(x + 116, ROW + 10, "rendered", size=13.5, anchor="start")
    s.arrow(x + 150, ROW + 18, x + 150, ROW + 36)
    s.text(x + 116, ROW + 54, "loaded back", size=13.5, anchor="start")
    s.arrow(x + 150, ROW + 62, x + 150, ROW + 80)
    s.text(x + 116, ROW + 98, "temp file, fsync,", size=13.5, anchor="start")
    s.text(x + 116, ROW + 118, "then replace", size=13.5, anchor="start")
    s.step(x + CW / 2, TXT, 5, "spectio.toml, last")
    lines(s, x, TXT + 30, ("a render that fails never replaces",
                           "the file that was there",
                           "records data dir, runs root, port,",
                           "host, executor and the engines",
                           "no `db_dir` unless it was given"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 40, cx + CW + 23, ROW + 40)

    # doctor ---------------------------------------------------------------------------------------
    s.line(30, DOC - 50, W - 30, DOC - 50, dashed=True, colour=t.muted)
    s.text(50, DOC - 60, "`spectio doctor` reads it all back: one line per check, "
           "exit 1 on any fail", size=14, anchor="start", colour=t.dim)
    checks = (
        ("config", (1, 0, 1), "`spectio.toml` is there"),
        ("sqlite", (1, 0, 1), "the library carries the WAL-reset fix"),
        ("db_dir", (1, 1, 1), "0700, on no network file system"),
        ("host", (1, 1, 0), "the login node init recorded"),
        ("nextflow", (1, 0, 1), "`-version` through the login shell"),
        ("snakemake", (1, 0, 1), "`--version` through the login shell"),
        ("java", (1, 1, 0), "found; Nextflow needs it"),
        ("tmux", (1, 1, 1), "on PATH; local mode: a warning"),
        ("sbatch", (1, 0, 1), "on PATH; local mode: not needed"),
        ("nxf_plugins_default", (1, 1, 1), "names `nf-spectio@0.0.1`, copy there"),
    )
    for half in range(2):
        x0 = 50 + half * 760
        s.text(x0 + 196, DOC - 18, "ok", size=13, colour=t.dim)
        s.text(x0 + 226, DOC - 18, "warn", size=13, colour=t.dim)
        s.text(x0 + 258, DOC - 18, "fail", size=13, colour=t.dim)
        for i, (name, can, gist) in enumerate(checks[half * 5:half * 5 + 5]):
            y = DOC + 14 + i * 36
            s.text(x0, y + 5, f"`{name}`", size=14, anchor="start")
            if can[0]:
                s.tick(x0 + 196, y, size=7)
            if can[1]:
                s.warning(x0 + 226, y, size=9)
            if can[2]:
                s.cross(x0 + 258, y, size=7)
            s.text(x0 + 290, y + 5, gist, size=13.5, anchor="start", colour=t.dim)

    s.text(W - 50, H - 16, "source: spectio/cli/init.py, cli/doctor.py, config.py, loginshell.py, "
           "spectio_server/bootstrap.py · tests test_init.py, test_doctor.py · P1 Task 8",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t08-init-doctor")
