#!/usr/bin/env python3
"""`sacct` rows bound to the run's WorkDir, and `spectio serve --detach`: batch P3-B05 (steps
P3-fu53 and P3-fu44, wave W5), 2026-11-08.

Writes docs/assets/diagrams/p3-b05-sacct-bind-detach_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B05 at 56feaeb (PRs 156 and 157 merged into
autopilot/integration between b70eb4d and 8eef45b, plus the batch code-simplifier's commit):
- P3-fu53, PR 156: spectio/runner/sacct.py FORMAT (17 fields, `WorkDir` before `Submit`, "not
  last"), SUBMIT_SKEW_S 300, DELIMITER_LEN 16 and `new_delimiter` (letters and digits, drawn per
  call), `sacct_argv` (`--parsable2 --noheader --delimiter= -j --user=<euid> --format=`, never
  `--duplicates`), `sacct_env` (PATH, SLURM_TIME_FORMAT=standard, TZ=UTC), INTERVAL_S 60, BATCH
  100; `parse_sacct` (a line not of 17 fields dropped; a job line a candidate only when its
  `normpath`ed WorkDir, never resolved, is wanted for the ID and Submit is not before the launch
  less 300 s; another WorkDir counted in `dropped`; a step joins the job line just before it with
  the same base ID; RESIZING left out; exactly one final candidate is the row, CPU and memory None
  when a RESIZING one was there; none, or two or more, no row);
  spectio_server/failure.py `Accounting.want` (JOB_ID filter first, a job with no directory never
  asked, `_resolve_job` `realpath` in the file pool, MAX_RESOLVE = BATCH 100 per view, one resolve
  per run in flight, each kept in `_real`), `_launched` (the earlier of created_at and started_at),
  `_call` (pairs copied under the lock, the dropped lines logged once per run, CON-PRE-16),
  MAX_TRIES 3, `_answers` (a second guard), CACHE_FILE sacct.json;
- P3-fu44, PR 157: spectio/cli/serve.py `_detach` (`login.new_link` first: OtherNode exit 2
  unless --force, PortHeld exit 2, NotReady wait, Refused start), `_check_version` (tmux 2.1),
  `_pane_argv` (ENV /usr/bin/env -i, PANE_ENV = KEEP, PATH, LD_LIBRARY_PATH, TMUX_TMPDIR,
  SPECTIO_CONFIG made absolute, config._ENV; `python -P -m spectio serve --pane`; a word ending
  in `;` refused), `_start` (`new-session -d -P -F -s spectio-server -c /` chained with
  `set-option -t =spectio-server: destroy-unattached off`; a session that runs `serve --pane`:
  wait; every pane dead: `kill-pane -t %N` each; else exit 2; "duplicate session": once more),
  `_wait_own` / `_ours` (host, a PID of a live pane, started_at >= t0 - SKEW_S 2 s; POLL_S 0.2,
  RETRY_S 1), `_why` and ERR_FILE serve-detach.err, DETACH_WAIT_S 120; cli/main.py `--wait`
  0 to 3600 and finite, exit 0, 2, 3; spectio_server/serve.py `start_text` with no link
  ("spectio login --print-link"), SIGHUP; cli/open.py `--no-link`, TICKET_WAIT_S 120;
- findings: docs/reviews/code/P3-fu53.md and P3-fu44.md, with their pre-reviews. Every major is
  pinned: the code-review majors of P3-fu53 (CR-P3FU53-01 r1, SEC-P3FU53-01 r1) and the
  pre-review majors of each design (SEC-PRE-01, CON-PRE-01 to -06, CON-PRE-14). P3-fu44's code
  review had no blocker and no major. IDs restart per round, so each code-review pin names its
  round;
- test counts: test_sacct.py 24 failed and 7 passed before the step, 31 passed at 2af08fe;
  test_failure.py 12 failed and 19 passed before, 34 at 2af08fe; test_detach.py 21 failing first,
  31 at 9ca6ef1 (P3-M9 and P3-M2 Progress pages, the review records); the Python suite 1002
  passed at 2af08fe, 1017 at 9ca6ef1, 1038 passed and 30 deselected on the batch, before and
  after the simplifier (its report); the simplifier: login.py, -6 +2 (`git show --stat 56feaeb`).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1990
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280

TOP1, CAP1, PIN1 = 165, 385, 505  # P3-fu53
TOP2, CAP2, PIN2 = 925, 1145, 1265  # P3-fu44
LOW = 1660  # tests and the simplifier


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, severity: str, rows: tuple[str, ...],
        status: str, *, built: bool = True, w: float = 280) -> float:
    """A major pinned where it hit: its ID, what it was, what the code does; returns its bottom."""
    h = 34 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done" if built else "problem",
           amount=0.5, width=1.2)
    if built:
        s.tick(x + 16, y + 13, size=6)
    else:
        s.warning(x + 16, y + 13, size=8)
    s.text(x + 32, y + 18, fid, size=13, anchor="start", weight="bold")
    s.text(x + w - 10, y + 18, severity, size=12.5, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 40 + i * 19, row, size=12.5, anchor="start")
    s.text(x + 12, y + 40 + len(rows) * 19, status, size=12.5, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = 280) -> float:
    """A dashed note: the review rounds, what is open, what was not run; returns its bottom."""
    h = 14 + 21 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 24 + i * 21, row, size=12.5, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def strip(s: Sketch, x: float, y: float, w: float, text: str, fill: str, *, h: float = 22) -> None:
    """One line of output, drawn as a strip with its text."""
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.1)
    s.text(x + 8, y + h - 6, text, size=12, anchor="start")


def arrows(s: Sketch, y: float) -> None:
    for a, b in zip(COL[:4], COL[1:]):
        s.arrow(a + CW + 2, y, b - 3, y)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=505)
    t = theme
    s.heading(50, 58, "P3-B05 · `sacct` rows bound to the run's WorkDir, and `spectio serve --detach`",
              "wave W5 · steps P3-fu53 and P3-fu44 · dev-env 15.3 req. 11 and 15 · schedulers 3.6 · "
              "PRs 156 and 157 into `autopilot/integration`")

    # == P3-fu53: sacct lines bound to the job's directory ======================================
    band(s, 140, "P3-fu53, PR 156, inbox 116 rule 10 b · a `sacct` line counts only for the "
         "directory the job was launched from, after the run's launch")

    # 1 the directories a job may use
    x = COL[0]
    s.folder(x + 4, TOP1 + 4, 120, 82, fill="input", label="task dir")
    s.link(x + 146, TOP1 + 44, size=14)
    s.arrow(x + 162, TOP1 + 44, x + 184, TOP1 + 44)
    s.folder(x + 190, TOP1 + 4, 88, 82, fill="input", label="`realpath`")
    s.cog(x + 234, TOP1 + 112, 12, fill="work")
    s.text(x + 212, TOP1 + 116, "file pool", size=12.5, anchor="end", colour=t.dim)
    s.text(x, TOP1 + 150, "expected: `normpath` and `realpath`", size=12.5, anchor="start")
    s.text(x, TOP1 + 170, "with the run's launch time", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 1, "where the job may be")
    lines(s, x, CAP1 + 30, ("Nextflow's task dir, Snakemake's",
                            "launch dir · 100 per view, one",
                            "resolve per run at a time, each kept",
                            "no dir, no SLURM job ID: not asked"))

    # 2 one sacct call
    x = COL[1]
    s.terminal(x, TOP1, CW, 150, ("$ sacct --parsable2 --noheader",
                                  "  --delimiter=RANDOM16",
                                  "  -j IDS --user=EUID",
                                  "  --format=17 fields",
                                  "env: PATH, TZ=UTC,",
                                  "  SLURM_TIME_FORMAT=standard"), size=11.5, line_h=18)
    s.cross(x + 18, TOP1 + 172, size=7)
    s.text(x + 34, TOP1 + 177, "never `--duplicates`", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 2, "one `sacct` call")
    lines(s, x, CAP1 + 30, ("a new 16-character delimiter",
                            "per call, letters and digits",
                            "the server user's own jobs only",
                            "one call in flight, one per 60 s"))

    # 3 each line
    x = COL[2]
    rows = (("`123`   `/w`   after launch", "done", 0, "tick"),
            ("`123.batch`   CPU, memory", "neutral", 22, "tick"),
            ("`123`   `/x`", "problem", 0, "cross"),
            ("`123`   `/w`   before launch", "problem", 0, "cross"),
            ("`/w` cut by a newline", "problem", 0, "cross"))
    for i, (text, fill, indent, mark) in enumerate(rows):
        y = TOP1 + 2 + i * 30
        strip(s, x + indent, y, 236 - indent, text, fill)
        if mark == "tick":
            s.tick(x + 256, y + 11, size=7)
        else:
            s.cross(x + 256, y + 11, size=7)
    s.text(x, TOP1 + 170, "dropped: other WorkDir, counted", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 3, "each line, bound")
    lines(s, x, CAP1 + 30, ("WorkDir `normpath`ed, never resolved",
                            "Submit at most 300 s before launch",
                            "a step joins the job line before it",
                            "`WorkDir` before `Submit`, not last"))

    # 4 one row per job and directory, before and after
    x = COL[3]
    s.text(x, TOP1 + 12, "before", size=12.5, anchor="start", colour=t.dim)
    strip(s, x + 52, TOP1, 100, "RESIZING", "neutral", h=20)
    strip(s, x + 52, TOP1 + 24, 100, "COMPLETED", "neutral", h=20)
    s.arrow(x + 158, TOP1 + 22, x + 184, TOP1 + 22)
    s.cross(x + 198, TOP1 + 22, size=8)
    s.text(x + 212, TOP1 + 27, "no row", size=12.5, anchor="start")
    s.line(x, TOP1 + 58, x + CW, TOP1 + 58, colour=t.muted, amount=0.3, passes=1)
    s.text(x, TOP1 + 84, "now", size=12.5, anchor="start", colour=t.dim)
    strip(s, x + 52, TOP1 + 72, 100, "RESIZING", "neutral", h=20)
    s.line(x + 56, TOP1 + 82, x + 148, TOP1 + 82, colour=t.accent, amount=0.3, passes=1, width=1.6)
    strip(s, x + 52, TOP1 + 96, 100, "COMPLETED", "done", h=20)
    s.arrow(x + 158, TOP1 + 106, x + 184, TOP1 + 106)
    s.tick(x + 198, TOP1 + 106, size=7)
    s.text(x + 212, TOP1 + 104, "the row,", size=12.5, anchor="start")
    s.text(x + 212, TOP1 + 122, "CPU and", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 212, TOP1 + 140, "memory None", size=12.5, anchor="start", colour=t.dim)
    s.text(x, TOP1 + 170, "a forged line no longer removes it", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 4, "one row per job and dir")
    lines(s, x, CAP1 + 30, ("RESIZING records left out",
                            "one final record: the row",
                            "two final records: still no row",
                            "SEC-P3T34-04 and -06 answered"))

    # 5 asked again, then kept
    x = COL[4]
    for i in range(3):
        cx = x + 30 + i * 52
        s.circle(cx, TOP1 + 36, 16, fill="gate")
        s.text(cx, TOP1 + 41, str(i + 1), size=13)
    s.arrow(x + 176, TOP1 + 36, x + 204, TOP1 + 36)
    s.text(x + 242, TOP1 + 41, "None", size=13.5)
    s.text(x + 82, TOP1 + 76, "calls with no row", size=12.5, colour=t.dim)
    s.page(x + 6, TOP1 + 96, 40, 52, fill="surface", lines=2)
    s.text(x + 56, TOP1 + 116, "`sacct.json`, format", size=12.5, anchor="start")
    s.text(x + 56, TOP1 + 136, "unchanged", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 5, "asked again, then kept")
    lines(s, x, CAP1 + 30, ("no row: up to 3 calls, then None",
                            "asked during a call: queued again,",
                            "no try counted, CON-PRE-16",
                            "dropped lines logged once per run"))

    arrows(s, TOP1 + 70)

    y = pin(s, COL[0], PIN1, "CON-PRE-14", "major, pre-review",
            ("Slurm may record a resolved WorkDir", "where the engine gives a symlink"),
            "built: `normpath` and `realpath` both")
    y = pin(s, COL[0], y + 10, "CR-P3FU53-01 r1", "major",
            ("no per-run guard: a slow file system", "got another 500 `realpath` per view"),
            "fixed in e97cfdf, one resolve per run")
    pin(s, COL[0], y + 10, "SEC-P3FU53-01 r1", "major",
        ("IDs never queued were resolved", "on every view: real jobs starved"),
        "fixed in e97cfdf, `JOB_ID` first")
    note(s, COL[1], PIN1, ("open, FU-P3-62: `realpath` follows", "links the pipeline makes,",
                           "SEC-P3FU53-03 r1 and r2, minor"))
    note(s, COL[2], PIN1, ("fixed in 2af08fe, SEC-P3FU53-02:", "a newline in WorkDir bound a cut",
                           "`/w`; only the newline is tested"))
    note(s, COL[3], PIN1, ("3 rounds: code-reviewer changes,", "approve, approve; security-reviewer",
                           "changes, approve, approve"))
    note(s, COL[4], PIN1, ("not run: the `slurm-mini` cases,", "FU-P3-60; `sacct` output in the",
                           "tests is synthetic, `TZ` to be", "validated"))

    # == P3-fu44: spectio serve --detach ========================================================
    band(s, 900, "P3-fu44, PR 157 · `spectio serve --detach` starts the server in the tmux session "
         "`spectio-server` and prints the link in the calling terminal, never in the pane")

    # 6 a server already runs?
    x = COL[0]
    s.terminal(x, TOP2, CW, 64, ("$ spectio serve --detach",), size=12.5)
    s.text(x, TOP2 + 90, "`login.new_link` first:", size=12.5, anchor="start")
    answers = (("tick", "a link: print it, exit 0"), ("cross", "other node: exit 2, or `--force`"),
               ("cross", "port held by another uid: exit 2"), ("wait", "starting: wait, start nothing"))
    for i, (mark, text) in enumerate(answers):
        y = TOP2 + 112 + i * 21
        if mark == "tick":
            s.tick(x + 8, y - 4, size=5)
        elif mark == "cross":
            s.cross(x + 8, y - 4, size=5)
        else:
            s.hourglass(x + 8, y - 4, size=6)
        s.text(x + 22, y, text, size=12.5, anchor="start")
    s.step(x + CW / 2, CAP2, 6, "a server already runs")
    lines(s, x, CAP2 + 30, ("a foreground `spectio serve` counts",
                            "none runs: start one in tmux",
                            "tmux 2.1 or later, else exit 2",
                            "`spectio_server` importable first"))

    # 7 the pane's command
    x = COL[1]
    s.page(x + 4, TOP2, 180, 132, fill="input", lines=0)
    for i, word in enumerate(("`/usr/bin/env -i`", "`NAME=value`, allowed", "`python -P -m spectio`",
                              "`serve --pane`")):
        s.text(x + 14, TOP2 + 28 + i * 28, word, size=12, anchor="start")
    s.cog(x + 232, TOP2 + 40, 16, fill="neutral")
    s.cross(x + 232, TOP2 + 40, size=20)
    s.text(x + 232, TOP2 + 82, "tmux's global", size=12.5, colour=t.dim)
    s.text(x + 232, TOP2 + 100, "environment", size=12.5, colour=t.dim)
    s.text(x, TOP2 + 160, "argv words, no shell, no secret", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP2, 7, "the pane's command")
    lines(s, x, CAP2 + 30, ("`KEEP`, `PATH`, `TMUX_TMPDIR` and",
                            "the settings variables, by name",
                            "`SPECTIO_CONFIG` made absolute",
                            "a word ending in `;`: exit 2"))

    # 8 the session spectio-server
    x = COL[2]
    tb = s.terminal(x, TOP2, CW, 104, ("$ spectio serve --pane",), size=12)
    s.poly([(x + 2, tb.bottom - 22), (x + CW - 2, tb.bottom - 22), (x + CW - 2, tb.bottom - 2),
            (x + 2, tb.bottom - 2)], fill="done", amount=0.3, width=1.0)
    s.text(x + 10, tb.bottom - 7, "spectio-server", size=12, anchor="start")
    s.text(x, TOP2 + 128, "`new-session -d -c /`, then", size=12.5, anchor="start")
    s.text(x, TOP2 + 148, "`destroy-unattached off`, chained", size=12.5, anchor="start")
    s.cross(x + 8, TOP2 + 168, size=5)
    s.text(x + 22, TOP2 + 172, "all panes ended: `kill-pane` by ID", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP2, 8, "the session `spectio-server`")
    lines(s, x, CAP2 + 30, ("it runs `serve --pane`: wait for it",
                            "something else: exit 2, never kill",
                            "the only kill: dead panes, by ID",
                            "duplicate session: the loser waits"))

    # 9 wait for its own server
    x = COL[3]
    s.page(x + 4, TOP2, 150, 118, fill="surface", lines=0)
    s.text(x + 14, TOP2 + 24, "`server.json`", size=12.5, anchor="start", weight="bold")
    for i, key in enumerate(("`host`", "`pid`", "`started_at`")):
        s.text(x + 14, TOP2 + 52 + i * 24, key, size=12, anchor="start")
        s.tick(x + 140, TOP2 + 48 + i * 24, size=5)
    for i, why in enumerate(("this node", "a live pane", "after this call")):
        s.text(x + 166, TOP2 + 52 + i * 24, why, size=12.5, anchor="start", colour=t.dim)
    s.hourglass(x + 14, TOP2 + 150, size=8)
    s.text(x + 30, TOP2 + 155, "polled each 0.2 s, a link try", size=12.5, anchor="start")
    s.text(x + 30, TOP2 + 175, "each 1 s, while the server boots", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP2, 9, "wait for its own server")
    lines(s, x, CAP2 + 30, ("never writes or removes `server.json`",
                            "started_at, 2 s of clock skew",
                            "`--wait`: 120 s default, 0 to 3600",
                            "`nan` or `inf`: exit 2"))

    # 10 the link here
    x = COL[4]
    s.terminal(x, TOP2, CW, 72, ("$ spectio serve --detach", "Open this link"), size=12)
    s.link(x + 250, TOP2 + 56, size=12, colour=t.term_ink)
    s.terminal(x, TOP2 + 86, CW, 72, ("in the pane: no link,", "spectio login --print-link"),
               size=11.5)
    s.cross(x + 262, TOP2 + 142, size=8)
    s.text(x, TOP2 + 180, "exit 0 here, with the attach hint", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP2, 10, "the link here, never there")
    lines(s, x, CAP2 + 30, ("exit 2: the pane ended, its reason",
                            "read from `serve-detach.err`",
                            "exit 3: no link in time, it runs on",
                            "`spectio open`: `--no-link`, 120 s"))

    arrows(s, TOP2 + 40)

    note(s, COL[0], PIN2, ("2 rounds, both reviewers approve:", "no blocker, no major, 16 minors;",
                           "5 fixed in 9ca6ef1, 10 open FU-P3-64"))
    pin(s, COL[1], PIN2, "SEC-PRE-01", "major, pre-review",
        ("a running tmux server's environment", "could reconfigure the child"),
        "built: `env -i` and an allow-list")
    y = pin(s, COL[2], PIN2, "CON-PRE-04", "major, pre-review",
            ("a dead pane lost the refusal and,", "with `remain-on-exit`, blocked starts"),
            "built: `serve-detach.err`, `kill-pane`")
    y = pin(s, COL[2], y + 10, "CON-PRE-05", "major, pre-review",
            ("`destroy-unattached on` ends a", "detached session at once"),
            "built: `off`, chained in the same call")
    pin(s, COL[2], y + 10, "CON-PRE-06", "major, pre-review",
        ("logind may kill a tmux server", "started from a non-interactive ssh"),
        "not built: a `doctor` line, FU-P3-58", built=False)
    y = pin(s, COL[3], PIN2, "CON-PRE-01", "major, pre-review",
            ("`server.json` comes before the key:", "the first link request is refused"),
            "built: retried until the deadline")
    note(s, COL[3], y + 10, ("open, FU-P3-64: pane IDs restart", "with a new tmux server,",
                             "SEC-P3FU44-05; values in tmux's", "cmdline, SEC-P3FU44-01"))
    y = pin(s, COL[4], PIN2, "CON-PRE-02", "major, pre-review",
            ("a first boot can take over 60 s", "and the caller gave up"),
            "built: `--wait` 120 s, then exit 3")
    note(s, COL[4], y + 10, ("not run: SLURM, an EMBL login node;", "tmux 3.4 only; `kill-pane`",
                             "against the fake tmux only"))

    # == tests, to scale, and the batch simplifier =============================================
    s.line(30, LOW - 14, W - 30, LOW - 14, dashed=True, colour=t.muted)
    s.text(50, LOW + 18, "tests, to scale", size=14, anchor="start", weight="bold")
    s.text(200, LOW + 18, "the Python suite, 0.38 px per test", size=12.5, anchor="start", colour=t.dim)
    suite = (("P3-fu53, 2af08fe", 1002, "1002 passed"), ("P3-fu44, 9ca6ef1", 1017, "1017 passed"),
             ("the batch, 56feaeb", 1038, "1038 passed, 30 deselected"))
    for i, (where, n, label) in enumerate(suite):
        y = LOW + 32 + i * 30
        s.text(50, y + 16, where, size=12.5, anchor="start")
        bw = n * 0.38
        bar(s, 200, y, bw, 20, "bar_green")
        s.text(210 + bw, y + 16, label, size=13, anchor="start")

    py = LOW + 140
    s.text(50, py + 4, "each step's own tests, written first, 6 px per test", size=12.5, anchor="start",
           colour=t.dim)
    files = (("`test_sacct.py`", 24, 31), ("`test_failure.py`", 12, 34), ("`test_detach.py`", 21, 31))
    for i, (name, failed, passed) in enumerate(files):
        y = py + 16 + i * 30
        s.text(50, y + 16, name, size=12.5, anchor="start")
        bar(s, 200, y, failed * 6, 20, "problem")
        s.text(208 + failed * 6, y + 16, f"{failed} failed first", size=12.5, anchor="start")
        bar(s, 480, y, passed * 6, 20, "bar_green")
        s.text(488 + passed * 6, y + 16, f"{passed} pass", size=12.5, anchor="start")

    sx, sy, sw, sh = 1000, LOW + 2, 550, 250
    s.shade(sx, sy, sw, sh, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 26, "batch simplify, 56feaeb, `cli/login.py`", size=13.5, anchor="start",
           weight="bold")
    s.text(sx + 14, sy + 54, "before", size=12.5, anchor="start", colour=t.dim)
    for i, (code, fill) in enumerate((("`class NoServer(Refused)`", "problem"),
                                      ("`raise NoServer`, twice", "problem"),
                                      ("caught nowhere", "neutral"))):
        y = sy + 64 + i * 28
        s.page(sx + 14, y, 18, 22, fill=fill, lines=0)
        s.text(sx + 40, y + 16, code, size=12, anchor="start")
    s.arrow(sx + 246, sy + 104, sx + 286, sy + 104)
    s.text(sx + 300, sy + 54, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(sx + 300, sy + 64, 18, 22, fill="done", lines=0)
    s.text(sx + 326, sy + 80, "`raise Refused`, twice", size=12, anchor="start")
    s.text(sx + 300, sy + 112, "same messages, same exit codes", size=12, anchor="start", colour=t.dim)
    s.text(sx + 300, sy + 132, "kept: `OtherNode`, `PortHeld`,", size=12, anchor="start", colour=t.dim)
    s.text(sx + 300, sy + 152, "`NotReady`, all caught", size=12, anchor="start", colour=t.dim)
    px = 14  # px per line, to scale
    bar(s, sx + 56, sy + 186, 6 * px, 16, "problem")
    s.text(sx + 14, sy + 199, "-6", size=13.5, anchor="start")
    bar(s, sx + 56, sy + 208, 2 * px, 16, "done")
    s.text(sx + 14, sy + 221, "+2", size=13.5, anchor="start")
    s.text(sx + 300, sy + 199, "1038 passed before and after;", size=12, anchor="start", colour=t.dim)
    s.text(sx + 300, sy + 219, "ruff, mypy, lint-imports clean", size=12, anchor="start", colour=t.dim)
    s.text(sx + 300, sy + 239, "no re-review needed", size=12, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 64, ("CR", "SEC"))
    s.text(50, H - 40, "pre-review IDs: SEC-PRE security-reviewer · CON-PRE constraints-hunter, "
           "on the design before any code", size=13.5, anchor="start", colour=t.dim)
    s.text(W - 50, H - 16, "source: `sacct.py`, `failure.py`, `cli/serve.py`, `cli/login.py` at 56feaeb "
           "· review records P3-fu53, P3-fu44", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b05-sacct-bind-detach")
