#!/usr/bin/env python3
"""Environments a run keeps, imaging reads, rule order and a lighter sacct: batch P3-B10 (steps
P3-fu86a, P3-fu86bcd, P3-fu102a, P3-fu86e, P3-fu102b, P3-fu86e2, P3-fu102c, P3-fu86e3, P3-fu107,
P3-fu102d1, P3-fu86e4, P3-fu106a, wave W5), 2026-11-09.

Writes docs/assets/diagrams/p3-b10-environments-imaging_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B10 at a337361d (PRs 193, 197 to 202 and 204 to 208
merged into autopilot/integration between f0a070cb and d2147ede, then the batch
code-simplifier's commit a337361d). Steps are numbered in merge order:
- 1, P3-fu86a, PR 193: spectio/environments.py (`read_as`, `run_column`, RESERVED local, slurm,
  new), migration 0011_run_environment.py (`runs.environment`: name, label, executor, slurm,
  local, state); failure.py `on_slurm` and resume.py read the run's column; review record
  docs/reviews/code/P3-fu86a.md (majors CR-P3FU86A-01 round 1, fixed in ad5e2719, and
  CR-P3FU86A-02 round 2, fixed in 807ef5b1); gate pytest 1248 passed, 1 skipped;
- 2, P3-fu86bcd, PR 197: spectio/envfile.py (FILE environments.toml next to spectio.toml;
  State missing, ok, refused, invalid, unreachable), spectio_server/api/environments.py (the six
  routes, If-Match, `:make-default`); record P3-fu86bcd.md (major CR-P3FU86BCD-01, fixed in
  e111f87a);
- 3, P3-fu102a, PR 198: api/results.py MAX_RANGE (8 << 20) + 1, MAX_KEY 16 << 20, TIFF_HEADS
  (TIFF and BigTIFF, both byte orders), `_zarr_key` (`.zmetadata` refused); record P3-fu102a.md,
  no major;
- 4, P3-fu86e, PR 199: boards LiteEnvironments ("Saved in ~/.spectio/environments.toml",
  `mylab-long` Default, `gpu-test`), LiteEnvironmentEdit, MLiteEnvironments, LiteSidebar,
  MLiteTabbar, LiteLaunch; record P3-fu86e.md (majors CR-P3FU86E-01, -02, fixed in d6a3e4ab);
- 5, P3-fu102b, PR 200: api/results.py IMAGING_SLOTS 3, "busy reading images" 503, SCRIPT_DESTS
  script, worker, sharedworker, serviceworker; static.py CSP `script-src 'self'
  'wasm-unsafe-eval'; worker-src 'self'`; record P3-fu102b.md (blocker CR-P3FU102B-01 fixed in
  964057d2, major SEC-P3FU102B-R2-01 fixed in 8fe75bdd);
- 6, P3-fu86e2, PR 201: boards LiteEnvironmentsStates ("Delete mylab-long?", the 409
  `environments-file-changed` dialog, Cancel, Reload), MLiteEnvironmentEdit,
  LiteLaunchNewEnvironment; record P3-fu86e2.md (blocker CR-P3FU86E2-R2-04, fixed by 0524ec2c);
- 7, P3-fu102c, PR 202: boards LiteImageViewer (channels DAPI, TNNT2, WGA; "6 of 40 on") and
  MLiteImageViewer; record P3-fu102c.md, no major;
- 8, P3-fu86e3, PR 204: boards LiteLaunch, LiteLaunchSnakemake, MLiteLaunch (Pipeline, Where it
  runs, Parameters; the aside's summary, Before Launch, Launch); record P3-fu86e3.md (major
  CR-P3FU86E3-01, fixed in 146368ea);
- 9, P3-fu107, PR 205: stages/freeze.py and api/runs_read.py; test_process_status.py
  `test_rules_in_first_seen_order` (the lists drawn); record P3-fu107.md, no major;
- 10, P3-fu102d1, PR 206: web/src/runs/imaging/client.ts RANGE_MAX 8 MiB + 1, BUDGET 2000
  requests and 256 MiB, IN_FLIGHT 3; walk.ts IFDS_MAX 10000, ENTRIES_MAX 1024, DECODED_MAX 64 MiB;
  record P3-fu102d1.md (majors CR-P3FU102D1-01 to -08, SEC-P3FU102D1-01 to -05; fix commits
  a9cbda5b, 4188a282, 16e7f20c and 8e887d04);
- 11, P3-fu86e4, PR 207: boards LiteRunDetail ("partition htc · SLURM account mylab · 2 h per
  job · 8 GiB per job"), LiteStatesRun (six panels), MLiteLaunch; record P3-fu86e4.md, no major;
- 12, P3-fu106a, PR 208: spectio/runner/sacct.py TIMEOUT_S 30, INTERVAL_S 60, MAX_INTERVAL_S 600
  (doubled after a failed or slow call, SLOW_S 5), BATCH 100, SUBMIT_SKEW_S 300, `-S` and `-E`;
  failure.py FOLLOW_UP_S 600, GIVE_UP_S 86400; record P3-fu106a.md (rounds 2 to 4: blocker
  CR-06, majors CR-04, SEC-02, CR-05, SEC-03; heuristic removed in c177558b);
- lines per step: `git show --shortstat <merge> -- . ':!docs' ':!.autopilot'` for each merge
  commit; the simplifier: `git show --numstat a337361d` (+14 -14, environments.py);
- pytest counts: the gates in the records of P3-fu86a (1248), P3-fu86e (1382), P3-fu102c (1397),
  and the batch simplifier's report (1424 passed, 1 skipped, 30 deselected, before and after).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1940, 2090
COLS = tuple(45 + i * 312 for i in range(6))
CW = 292
ROW_A = 176  # the step's name, row A (environments)
ROW_B = 886  # row B (imaging, rule order, sacct)
LOW = 1660  # the simplifier and the bars


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 12.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, rows: tuple[str, ...], status: str,
        *, w: float = CW) -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it was closed."""
    h = 32 + 18 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 14, y + 13, size=5.5)
    s.text(x + 27, y + 18, fid, size=11.5, anchor="start", weight="bold")
    s.text(x + w - 8, y + 18, tag, size=11, anchor="end", colour=s.t.accent if "blocker" in tag
           else s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 10, y + 38 + i * 18, row, size=12, anchor="start")
    s.text(x + 10, y + 38 + len(rows) * 18, status, size=12, anchor="start", colour=s.t.dim)
    return y + h


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = CW,
         warn: bool = False) -> float:
    """A dashed note: the rounds and what is open."""
    h = 12 + 20 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 22 if warn else 0
    if warn:
        s.warning(x + 17, y + 18, size=7.5)
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 23 + i * 20, row, size=12, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def chip(s: Sketch, x: float, y: float, w: float, label: str, fill: str, *, h: float = 20,
         size: float = 10.5) -> None:
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.38, label, size=size)


def picture(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    """An image: a frame, three blobs of colour, the channels."""
    cell(s, x, y, w, h, "neutral")
    for cx, cy, r, fill in ((0.3, 0.4, 0.16, "bar_blue"), (0.62, 0.55, 0.2, "bar_orange"),
                            (0.45, 0.72, 0.12, "bar_green")):
        s.circle(x + w * cx, y + h * cy, h * r, fill=fill, width=1.0)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def head(s: Sketch, x: float, y: float, title: str) -> None:
    s.text(x, y, title, size=14, anchor="start", weight="bold")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1010)
    t = theme
    s.heading(50, 58, "P3-B10 · environments a run keeps, imaging reads, rule order, a lighter sacct",
              "wave W5 · 12 steps · 2026-11-09 · PRs 193, 197 to 202, 204 to 208 into "
              "`autopilot/integration` · steps numbered in merge order, the two strands interleave")

    # == row A: FU-P3-86, environments ==========================================================
    band(s, 140, "FU-P3-86, environments: a run keeps what it ran with · the server first, then the "
         "boards the screens are built from · owner api 5.4 and ui-spec 4.8.1")
    top, cap = ROW_A + 20, ROW_A + 248
    pin_y = cap + 122

    # 1 -- P3-fu86a: the run's own snapshot ------------------------------------------------------
    x = COLS[0]
    head(s, x, ROW_A, "P3-fu86a · PR 193")
    s.page(x + 2, top + 6, 52, 68, fill="surface", lines=3)
    s.text(x + 28, top + 92, "a run", size=11.5, colour=t.dim)
    s.arrow(x + 60, top + 38, x + 88, top + 38)
    cell(s, x + 94, top + 2, 196, 72, "input")
    s.text(x + 102, top + 22, "`runs.environment`", size=12, anchor="start", weight="bold")
    s.text(x + 102, top + 42, "name · label · executor", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 102, top + 60, "slurm · local · state", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 116, "`read_as`, by its state:", size=11.5, anchor="start")
    states = (("recorded", "done", "its own snapshot"),
              ("not_recorded", "work", "the server kind's built-in"),
              ("not_readable", "problem", "no command, `not_found`"))
    for i, (name, fill, what) in enumerate(states):
        y = top + 124 + i * 22
        chip(s, x + 2, y, 104, f"`{name}`", fill, h=18)
        s.text(x + 114, y + 14, what, size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 204, "read by `on_slurm`, `sacct`, `resume.py`", size=11.5, anchor="start")
    s.step(x + CW / 2, cap, 1, "the run's own environment", size=18)
    lines(s, x, cap + 28, ("migration `0011`: the column, a backfill",
                           "never `settings.executor` for a run",
                           "`GET /runs` and `/runs/<id>` carry it",
                           "`--local-cores 2` last on Snakemake SLURM",
                           "partition, account: SLURM names only"))
    y = pin(s, x, pin_y, "CR-P3FU86A-01", "r1 major",
            ("the backfill read the `environments`", "row, a rebuild from the manifest not"),
            "fixed in `ad5e2719`: `run_column(None)`")
    y = pin(s, x, y + 10, "CR-P3FU86A-02", "r2 major",
            ("a run not `recorded` was read as", "local, against the Resume rule"),
            "fixed in `807ef5b1`: `read_as`")
    note(s, x, y + 10, ("3 rounds · CR changes, changes, approve",
                        "SEC approve 3 times · 2 open minors",
                        "to FU-P3-86c, closed by step 2"))

    # 2 -- P3-fu86bcd: the file, the launch, the routes -------------------------------------------
    x = COLS[1]
    head(s, x, ROW_A, "P3-fu86bcd · PR 197")
    s.folder(x + 2, top + 4, 134, 92, fill="input")
    s.page(x + 14, top + 26, 44, 58, fill="surface", lines=3)
    s.page(x + 72, top + 26, 44, 58, fill="docs", lines=3)
    s.lock(x + 112, top + 80, size=11)
    s.text(x + 2, top + 116, "`environments.toml`", size=11, anchor="start")
    s.text(x + 2, top + 133, "next to `spectio.toml`", size=11.5, anchor="start", colour=t.dim)
    fstates = (("missing", "neutral"), ("ok", "done"), ("refused", "problem"),
               ("invalid", "problem"), ("unreachable", "work"))
    for i, (name, fill) in enumerate(fstates):
        chip(s, x + 156, top + 2 + i * 23, 100, f"`{name}`", fill, h=19)
    s.tick(x + 270, top + 34, size=5)
    s.text(x + 156, top + 133, "5 states", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 2, top + 160, "`POST /runs` with `environment`: the", size=11.5, anchor="start")
    s.text(x + 2, top + 177, "manifest, the column, the payload", size=11.5, anchor="start",
           colour=t.dim)
    s.text(x + 2, top + 200, "`/environments` and `/environments/<name>`", size=11, anchor="start")
    s.step(x + CW / 2, cap, 2, "the file, the launch, the routes", size=18)
    lines(s, x, cap + 28, ("read with no link followed, 64 KiB + 1",
                           "a write: one lock, parsed back, the",
                           "SHA-256 checked again, then a rename",
                           "never over a `refused` or `invalid` file",
                           "`If-Match` on PUT, DELETE, `:make-default`"))
    y = pin(s, x, pin_y, "CR-P3FU86BCD-01", "r1 major",
            ("an `OSError` on the file was a 500,", "so a built-in launch failed too"),
            "fixed in `e111f87a`: `unreachable`, 503")
    note(s, x, y + 10, ("3 rounds · CR changes, approve, approve",
                        "SEC approve 3 times · open minors to",
                        "FU-P3-103 · inbox 136, assumed"))

    # 4 -- P3-fu86e: the environments boards, first part ------------------------------------------
    x = COLS[2]
    head(s, x, ROW_A, "P3-fu86e · PR 199 · boards")
    s.browser(x + 2, top, 206, 176)
    for i, (name, badge) in enumerate((("`local`", ""), ("`slurm`", ""), ("`mylab-long`", "Default"),
                                       ("`gpu-test`", ""))):
        y = top + 38 + i * 33
        cell(s, x + 12, y, 186, 26, "surface")
        s.text(x + 20, y + 18, name, size=11, anchor="start")
        if badge:
            chip(s, x + 132, y + 4, 58, badge, "done", h=18, size=10.5)
    s.phone(x + 220, top + 6, 70, 132)
    for i in range(4):
        cell(s, x + 230 + i * 12.5, top + 100, 11, 10, "input" if i == 3 else "surface")
    s.text(x + 255, top + 158, "4 tabs", size=11.5, colour=t.dim)
    s.text(x + 2, top + 200, "Saved in `~/.spectio/environments.toml`", size=11, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 4, "the environments boards", size=18)
    lines(s, x, cap + 28, ("`LiteEnvironments`, `LiteEnvironmentEdit`",
                           "`MLiteEnvironments` at 360 and 320 px",
                           "sidebar and tab bar gain Environments",
                           "Launch: an Environment row of radios",
                           "the Executor row goes"))
    y = pin(s, x, pin_y, "CR-P3FU86E-01", "r1 major",
            ("an unusable `gpu-test` entry, a", "state api 5.4 never returns"),
            "fixed in `d6a3e4ab`: the built-in `slurm` case")
    y = pin(s, x, y + 10, "CR-P3FU86E-02", "r1 major",
            ("the Launch radio names did not", "match ui-spec 4.8.1"),
            "fixed in `d6a3e4ab`: `aria-labelledby`")
    note(s, x, y + 10, ("3 rounds · CR changes, approve, approve",
                        "SEC approve 3 times · 7 boards",
                        "deferred to steps 6, 8 and 11"))

    # 6 -- P3-fu86e2: the file states and dialogs -------------------------------------------------
    x = COLS[3]
    head(s, x, ROW_A, "P3-fu86e2 · PR 201 · boards")
    s.browser(x + 2, top, 288, 150)
    for i in range(4):
        s.line(x + 14, top + 44 + i * 26, x + 100, top + 44 + i * 26, colour=t.muted, passes=1,
               amount=0.3)
    cell(s, x + 46, top + 38, 232, 102, "surface")
    s.text(x + 58, top + 58, "Delete mylab-long?", size=12, anchor="start", weight="bold")
    chip(s, x + 56, top + 68, 212, "`409 environments-file-changed`", "problem", h=22, size=10.5)
    chip(s, x + 146, top + 106, 58, "Cancel", "surface", h=24, size=11)
    chip(s, x + 210, top + 106, 58, "Reload", "input", h=24, size=11)
    for i, (name, w, fill) in enumerate((("refused", 62, "problem"), ("invalid", 58, "problem"),
                                         ("unreachable", 84, "work"), ("404", 34, "neutral"),
                                         ("412", 34, "neutral"))):
        px = x + 2 + sum((62, 58, 84, 34, 34)[:i]) + i * 4
        chip(s, px, top + 160, w, f"`{name}`", fill, h=20)
    s.text(x + 2, top + 200, "no state prints a value from either file", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 6, "the file states, the dialogs", size=18)
    lines(s, x, cap + 28, ("`LiteEnvironmentsStates`: loading, list",
                           "error, the file states, 404, Make default,",
                           "the delete dialog with its 412 and 409",
                           "`MLiteEnvironmentEdit`, the phone form",
                           "`LiteLaunchNewEnvironment`, a dialog"))
    y = pin(s, x, pin_y, "CR-P3FU86E2-R2-04", "r2 blocker",
            ("the review range was empty: the", "fix was an uncommitted edit"),
            "fixed: committed as `0524ec2c`, gate run")
    note(s, x, y + 10, ("3 rounds · CR approve, changes, approve",
                        "SEC skipped, no sensitive path",
                        "open: 5 minors · inbox 141"))

    # 8 -- P3-fu86e3: Launch in two columns --------------------------------------------------------
    x = COLS[4]
    head(s, x, ROW_A, "P3-fu86e3 · PR 204 · boards")
    s.browser(x + 2, top, 288, 180)
    s.text(x + 14, top + 50, "Launch", size=13, anchor="start", weight="bold")
    chip(s, x + 222, top + 36, 58, "Launch", "docs", h=22, size=11)
    for label, y, h, fill in (("Pipeline", 66, 26, "surface"), ("Where it runs", 98, 40, "input"),
                              ("Parameters", 144, 26, "surface")):
        chip(s, x + 12, top + y, 172, label, fill, h=h, size=11.5)
    for label, y, h, fill in (("summary", 66, 26, "surface"), ("Before Launch", 98, 40, "surface"),
                              ("Launch", 144, 26, "docs")):
        chip(s, x + 192, top + y, 88, label, fill, h=h, size=11)
    s.text(x + 2, top + 200, "Where it runs: from the aside to the main", size=11.5,
           anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 8, "Launch in two columns", size=18)
    lines(s, x, cap + 28, ("`LiteLaunch`, `LiteLaunchSnakemake`",
                           "Launch stays in the head and the aside",
                           "`MLiteLaunch`: one column at 360 and",
                           "320 px, Launch in the pinned bar",
                           "decided by Thomas, journal 2026-11-09"))
    y = pin(s, x, pin_y, "CR-P3FU86E3-01", "r1 major",
            ("the page-head Launch was removed", "from both desktop boards"),
            "fixed in `146368ea`: back in the head")
    note(s, x, y + 10, ("2 rounds · CR changes, approve",
                        "SEC skipped, no sensitive path",
                        "open minor closed by step 11"))

    # 11 -- P3-fu86e4: the Environment fact on Run detail -----------------------------------------
    x = COLS[5]
    head(s, x, ROW_A, "P3-fu86e4 · PR 207 · boards")
    s.browser(x + 2, top, 288, 132)
    s.text(x + 12, top + 48, "Environment", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 100, top + 48, "`mylab-long`", size=11, anchor="start")
    chip(s, x + 194, top + 35, 48, "SLURM", "input", h=18, size=10.5)
    s.text(x + 100, top + 66, "partition htc · SLURM account", size=11, anchor="start", colour=t.dim)
    s.text(x + 100, top + 82, "mylab · 2 h · 8 GiB per job", size=11, anchor="start", colour=t.dim)
    s.text(x + 12, top + 104, "Login node", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 100, top + 104, "login1 · runs the engine head", size=11, anchor="start")
    s.text(x + 12, top + 122, "Executor", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 100, top + 122, "SLURM · runs the tasks", size=11, anchor="start")
    panels = (("deleted or renamed", "done"), ("file unusable", "done"), ("not recorded", "neutral"),
              ("cannot be read", "problem"), ("from a terminal", "neutral"),
              ("Snakemake profile", "input"))
    for i, (label, fill) in enumerate(panels):
        chip(s, x + 2 + (i % 2) * 146, top + 140 + (i // 2) * 22, 142, label, fill, h=19, size=11)
    s.step(x + CW / 2, cap, 11, "the Environment fact", size=18)
    lines(s, x, cap + 28, ("`LiteRunDetail`: Environment, from the",
                           "run's own snapshot, not the file",
                           "`LiteStatesRun`: six panels, one a state",
                           "`MLiteLaunch`: the phone's `invalid` file",
                           "every environments board now drawn"))
    y = note(s, x, pin_y, ("no blocker, no major",
                           "2 rounds, CR approve both, fixed:",
                           "cannot be read, not not recorded",
                           "SEC skipped · inbox 143"))
    note(s, x, y + 10, ("open: CR-P3FU86E4-02, `LiteRunObserved`",
                        "still shows Executor SLURM for a",
                        "terminal run"))

    # == row B: FU-P3-102 imaging, FU-P3-107, FU-P3-106a ==========================================
    band(s, ROW_B - 36, "FU-P3-102, imaging viewers: the server, the boards, the browser's reader · "
         "FU-P3-107 and FU-P3-106a, from Thomas's login1 retest and the SLURM query budget")
    top, cap = ROW_B + 20, ROW_B + 248
    pin_y = cap + 122

    # 3 -- P3-fu102a: imaging reads on the raw route ----------------------------------------------
    x = COLS[0]
    head(s, x, ROW_B, "P3-fu102a · PR 198")
    s.text(x + 2, top + 12, "a TIFF, its bytes", size=11.5, anchor="start", colour=t.dim)
    cell(s, x + 2, top + 22, 286, 26, "surface")
    cell(s, x + 2, top + 22, 30, 26, "gate")
    cell(s, x + 150, top + 22, 64, 26, "input")
    s.text(x + 17, top + 66, "4 bytes", size=11, colour=t.dim)
    s.text(x + 182, top + 66, "`bytes=first-last`", size=11)
    s.arrow(x + 182, top + 72, x + 182, top + 92)
    s.text(x + 182, top + 108, "`206`, `Content-Range`", size=11)
    s.text(x + 17, top + 84, "TIFF or", size=11, colour=t.dim)
    s.text(x + 17, top + 99, "BigTIFF", size=11, colour=t.dim)
    s.folder(x + 2, top + 122, 104, 64, fill="input", label="`.ome.zarr`")
    for i, (key, ok) in enumerate((("`zarr.json`", True), ("`0/c/0.0`", True),
                                   ("`.zmetadata`", False))):
        y = top + 132 + i * 20
        (s.tick if ok else s.cross)(x + 122, y, size=5)
        s.text(x + 134, y + 5, key, size=11, anchor="start", colour=t.ink if ok else t.dim)
    s.text(x + 116, top + 202, "a key over 16 MiB: `413`", size=11.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 3, "imaging reads, raw route", size=18)
    lines(s, x, cap + 28, ("`as=tiff`: one closed Range, 8 MiB + 1,",
                           "past the 1 GiB cap",
                           "`as=zarr`: a key, whole or one range",
                           "open, suffix, two ranges: `422`",
                           "no `Sec-Fetch-Dest: empty`: attachment"))
    note(s, x, pin_y, ("no blocker, no major",
                       "1 round · CR approve, SEC approve",
                       "3 minors, all closed by step 5",
                       "CR-P3FU102A-03: style, left alone"))

    # 5 -- P3-fu102b: read slots, step 0, CSP ------------------------------------------------------
    x = COLS[1]
    head(s, x, ROW_B, "P3-fu102b · PR 200")
    s.text(x + 2, top + 12, "`IMAGING_SLOTS` 3", size=11.5, anchor="start", colour=t.dim)
    for i in range(3):
        cell(s, x + 2 + i * 40, top + 22, 34, 46, "work")
        s.page(x + 9 + i * 40, top + 30, 20, 28, fill="surface", lines=0)
    s.arrow(x + 186, top + 44, x + 128, top + 44, colour=t.dim)
    s.page(x + 192, top + 28, 22, 30, fill="surface", lines=0)
    s.cross(x + 203, top + 43, size=7)
    s.text(x + 222, top + 40, "`503`", size=11.5, anchor="start")
    s.text(x + 222, top + 58, "busy", size=11, anchor="start", colour=t.dim)
    s.hourglass(x + 12, top + 92, size=7)
    s.text(x + 26, top + 96, "a stalled read keeps its slot until", size=11.5, anchor="start")
    s.text(x + 26, top + 114, "its last pool job ends, `on_done`", size=11.5, anchor="start",
           colour=t.dim)
    s.text(x + 2, top + 146, "step 0, by `Sec-Fetch-Dest`: `422`", size=11.5, anchor="start")
    s.text(x + 2, top + 166, "`script` `worker` `sharedworker`", size=11, anchor="start", colour=t.dim)
    s.text(x + 2, top + 184, "`serviceworker`, on both raw routes", size=11, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 5, "read slots, step 0, CSP", size=18)
    lines(s, x, cap + 28, ("a slot taken without waiting, else `503`",
                           "one decision for the cap and dispatch",
                           "two `Range` fields: `422`",
                           "CSP on every screen: `'wasm-unsafe-eval'`",
                           "and `worker-src 'self'`, no `blob:`"))
    y = pin(s, x, pin_y, "CR-P3FU102B-01", "r1 blocker",
            ("a slot came back at the next cyclic", "GC: 3 aborted reads, then all 503"),
            "fixed in `964057d2`: released in `finally`")
    y = pin(s, x, y + 10, "SEC-P3FU102B-R2-01", "r2 major",
            ("the slot came back while the stalled", "read still held a pool thread"),
            "fixed in `8fe75bdd`: `_Slot`, `on_done`")
    note(s, x, y + 10, ("3 rounds · CR changes, approve, approve",
                        "SEC approve, changes, approve",
                        "inbox 138, assumed"))

    # 7 -- P3-fu102c: imaging viewer boards --------------------------------------------------------
    x = COLS[2]
    head(s, x, ROW_B, "P3-fu102c · PR 202 · boards")
    s.browser(x + 2, top, 288, 160)
    picture(s, x + 12, top + 38, 148, 112)
    s.text(x + 172, top + 50, "Channels", size=11.5, anchor="start", weight="bold")
    for i, name in enumerate(("DAPI", "TNNT2", "WGA")):
        y = top + 62 + i * 24
        s.text(x + 172, y + 13, f"{i + 1} {name}", size=11, anchor="start")
        cell(s, x + 248, y + 3, 28, 13, "done")
        s.dot(x + 270, y + 9.5, 4)
    chip(s, x + 172, top + 136, 104, "Reset contrast", "surface", h=18, size=10.5)
    s.text(x + 2, top + 180, "40 channels: Filter channels, 6 of 40 on", size=11.5, anchor="start")
    s.text(x + 2, top + 198, "an off channel reads Off, a grey swatch", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 7, "imaging viewer boards", size=18)
    lines(s, x, cap + 28, ("`LiteImageViewer`, four variants:",
                           "an OME-TIFF with 3 channels, 40",
                           "channels, an RGB slide, a flat `.tif`",
                           "`MLiteImageViewer` at 360 and 320 px",
                           "each switch names its channel"))
    note(s, x, pin_y, ("no blocker, no major",
                       "2 rounds · CR approve, SEC approve",
                       "fixed: 464 x 494 px, the off colour",
                       "open: CR-P3FU102C-03, a fragment link",
                       "inbox 140, assumed"))

    # 10 -- P3-fu102d1: the TIFF reader in the browser ---------------------------------------------
    x = COLS[3]
    head(s, x, ROW_B, "P3-fu102d1 · PR 206 · web")
    s.browser(x + 2, top + 4, 100, 74)
    s.text(x + 52, top + 60, "geotiff", size=11.5)
    for i in range(3):
        s.arrow(x + 108, top + 26 + i * 18, x + 178, top + 26 + i * 18)
    s.text(x + 143, top + 16, "3 at once", size=11, colour=t.dim)
    s.page(x + 186, top + 6, 50, 66, fill="input", lines=3)
    s.text(x + 211, top + 92, "`as=tiff`", size=11)
    for i, label in enumerate(("IFD 0", "IFD 1", "IFD 2")):
        chip(s, x + 2 + i * 70, top + 118, 52, label, "surface", h=22, size=11)
        if i < 2:
            s.arrow(x + 56 + i * 70, top + 129, x + 70 + i * 70, top + 129)
    s.arc(x + 168, top + 114, x + 28, top + 114, lift=28, colour=t.accent, dashed=True)
    s.cross(x + 98, top + 92, size=5)
    s.text(x + 200, top + 134, "a loop ends", size=11, anchor="start", colour=t.dim)
    s.text(x + 200, top + 149, "the walk", size=11, anchor="start", colour=t.dim)
    s.text(x + 2, top + 168, "at most 10,000 IFDs, 1,024 entries each", size=11.5, anchor="start")
    s.text(x + 2, top + 186, "a tile at most 64 MiB decoded; sizing", size=11.5, anchor="start",
           colour=t.dim)
    s.text(x + 2, top + 204, "tags one positive integer", size=11.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, cap, 10, "the TIFF reader, browser", size=18)
    lines(s, x, cap + 28, ("only the pinned raw URL, `as=tiff`",
                           "closed ranges of 8 MiB + 1, counted",
                           "first: 2,000 requests, 256 MiB a view",
                           "3 in flight, each until its body is read",
                           "a `503` asked again once, after 1 s"))
    y = pin(s, x, pin_y, "CR-P3FU102D1-08", "open at r4, major",
            ("the slot freed at the headers: more", "than 3 bodies, and the server 503"),
            "fixed in `8e887d04`, test first")
    y = pin(s, x, y + 10, "SEC-P3FU102D1-05", "open at r4, major",
            ("a per-IFD cap failed open on an", "array-valued tag or a 0"),
            "fixed in `8e887d04`, test first")
    y = pin(s, x, y + 10, "CR-P3FU102D1-01 to -07", "r1 to r4",
            ("and SEC-P3FU102D1-01 to -04, all", "majors, relayed in summary"),
            "fixed in `a9cbda5b` `4188a282` `16e7f20c`")
    note(s, x, y + 10, ("5 rounds · CR approve, SEC approve",
                        "vitest `imaging.test.ts`: 24 passed"))

    # 9 -- P3-fu107: Snakemake rules in first-seen order -------------------------------------------
    x = COLS[4]
    head(s, x, ROW_B, "P3-fu107 · PR 205")
    s.text(x + 2, top + 12, "before: by name", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 162, top + 12, "after: first seen", size=11.5, anchor="start", colour=t.dim)
    before = ("align", "all", "make_reads", "merge", "report", "split", "unused")
    after = ("make_reads", "split", "align", "all", "merge", "report", "unused")
    for k, (ox, order) in enumerate(((x + 2, before), (x + 162, after))):
        for i, rule in enumerate(order):
            y = top + 22 + i * 22
            fill = "work" if rule == "align" else ("neutral" if rule == "unused" else "input")
            chip(s, ox, y, 120, f"`{rule}`", fill, h=18)
    s.arrow(x + 128, top + 92, x + 156, top + 92)
    s.text(x + 2, top + 190, "a job for `make_reads`, `split`, `align`", size=11.5, anchor="start")
    s.text(x + 2, top + 208, "pipeline order: `align` after `split`", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 9, "rules in first-seen order", size=18)
    lines(s, x, cap + 28, ("`--list-rules` sorts by name, 9.27.1",
                           "the freeze takes the rule files' order;",
                           "`rules.txt` only says which belong",
                           "`/processes`: rules by their first job",
                           "Nextflow unchanged, API shape too"))
    note(s, x, pin_y, ("no blocker, no major",
                       "1 round · CR approve, SEC approve",
                       "the test fails on the base's code",
                       "open: CR-P3FU107-01, a stale comment",
                       "in `store/schema.py`; CR-P3FU107-02,",
                       "no test of a rule `rules.txt` adds"))

    # 12 -- P3-fu106a: a lighter SLURM footprint ---------------------------------------------------
    x = COLS[5]
    head(s, x, ROW_B, "P3-fu106a · PR 208")
    s.hpc_node(x + 2, top + 2, 48, 64, busy=1)
    s.text(x + 60, top + 16, "`sacct`, one call in flight,", size=11.5, anchor="start")
    s.text(x + 60, top + 34, "100 IDs a call, 30 s timeout", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 60, top + 52, "`-S` launch less 300 s, `-E now`", size=11, anchor="start",
           colour=t.dim)
    k = 0.38  # px per second
    s.text(x + 2, top + 92, f"the pace after a failed or slow call, {k} px a s", size=11.5,
           anchor="start")
    for i, sec in enumerate((60, 120, 240, 480, 600)):
        y = top + 102 + i * 17
        bar(s, x + 2, y, sec * k, 12, "bar_orange" if i else "bar_green")
        s.text(x + 8 + sec * k, y + 11, f"{sec} s", size=11, anchor="start")
    s.text(x + 2, top + 204, "slow: over 5 s · a quick answer resets", size=11.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, cap, 12, "a lighter SLURM footprint", size=18)
    lines(s, x, cap + 28, ("live: only an opened failure or panel",
                           "run end: one sweep, a follow-up 600 s on",
                           "null only when slurmdbd answered",
                           "without the job; give up 24 h after",
                           "only an over-cap batch is split"))
    y = pin(s, x, pin_y, "CR-P3FU106A-06", "r2 to r4 blocker",
            ("a livelock with two bad IDs, in", "the per-ID batch-halving heuristic"),
            "closed in `c177558b`: heuristic removed")
    y = pin(s, x, y + 10, "CR-P3FU106A-04, -05", "r2 to r4 majors",
            ("and SEC-P3FU106A-02, -03: a stat", "failure final, a bad ID not isolated,",
             "an outage drains one ID per call"),
            "closed in `c177558b`, verified")
    note(s, x, y + 10, ("accepted limit, to be validated: a",
                        "window over `MaxQueryTimeRange`",
                        "fails its batch until the give-up,",
                        "FU-P3-106b · inbox 144"), warn=True)

    for row in (ROW_A, ROW_B):
        for a, b in zip(COLS[:5], COLS[1:]):
            s.arrow(a + CW + 2, row + 232, b - 3, row + 232, colour=t.muted)

    # == the batch simplifier, the lines and the tests ============================================
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: approve, "
         "approve")
    y0 = LOW + 6

    # the simplifier: one helper where there were two copies
    x = 50
    s.text(x, y0 + 10, "`a337361d`, `api/environments.py`", size=13.5, anchor="start", weight="bold")
    s.text(x, y0 + 36, "before", size=12.5, anchor="start", colour=t.dim)
    s.page(x, y0 + 46, 210, 132, fill="surface", lines=0)
    for i, label in enumerate(("`view()` builds the list", "`make_default` builds it again",
                               "`view()`: an `ok` state check", "`BUILTIN` spelt out")):
        chip(s, x + 8, y0 + 64 + i * 26, 186, label, "problem", h=20, size=10.5)
    s.arrow(x + 218, y0 + 112, x + 244, y0 + 112)
    s.text(x + 252, y0 + 36, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(x + 252, y0 + 46, 236, 132, fill="done", lines=0)
    for i, label in enumerate(("`_entries(settings, defined)`", "used by both", "no state check",
                               "`BUILTIN = RESERVED - new`")):
        chip(s, x + 260, y0 + 64 + i * 26, 212, label, "done", h=20, size=10.5)
    lines(s, x, y0 + 202, ("+14 -14 in 1 file, git numstat · closes CR-P3FU86BCD-07, -08",
                           "a file that is not `ok` has no environments and no default",
                           "left alone: CR-P3FU86A-06, no unique `name`, would change",
                           "behaviour; CR-P3FU102B-R2-03, 5 lines after the formatter;",
                           "test-only and board items reported, not made"), size=12)

    # the lines changed per step, to scale
    x = 620
    k = 0.1  # px per line
    s.text(x, y0 + 10, f"lines per step outside docs, to scale, {k} px a line", size=13.5,
           anchor="start", weight="bold")
    sizes = ((1, "P3-fu86a", 1181, 94, "done"), (2, "P3-fu86bcd", 2464, 69, "done"),
             (3, "P3-fu102a", 535, 38, "done"), (4, "P3-fu86e", 372, 14, "docs"),
             (5, "P3-fu102b", 426, 39, "done"), (6, "P3-fu86e2", 400, 11, "docs"),
             (7, "P3-fu102c", 311, 0, "docs"), (8, "P3-fu86e3", 168, 59, "docs"),
             (9, "P3-fu107", 48, 15, "done"), (10, "P3-fu102d1", 917, 5, "done"),
             (11, "P3-fu86e4", 82, 13, "docs"), (12, "P3-fu106a", 663, 135, "done"))
    mid = x + 150
    for i, (n, name, add, rem, fill) in enumerate(sizes):
        ry = y0 + 26 + i * 19
        s.text(mid - 22, ry + 12, f"{n} `{name}`", size=11, anchor="end", colour=t.dim)
        if rem:
            bar(s, mid - 2 - rem * k, ry, rem * k, 13, "problem")
        bar(s, mid + 2, ry, add * k, 13, fill)
        s.text(mid + 8 + add * k, ry + 12, f"+{add} -{rem}", size=11, anchor="start")
    s.line(mid, y0 + 22, mid, y0 + 256, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y0 + 272, "removed", size=11, anchor="end", colour=t.dim)
    s.text(mid + 8, y0 + 272, "added", size=11, anchor="start", colour=t.dim)
    bar(s, x + 260, y0 + 262, 18, 12, "done")
    s.text(x + 284, y0 + 272, "code", size=11, anchor="start", colour=t.dim)
    bar(s, x + 330, y0 + 262, 18, 12, "docs")
    s.text(x + 354, y0 + 272, "design boards only", size=11, anchor="start", colour=t.dim)

    # the tests, to scale
    x = 1240
    k = 0.2  # px per test
    s.text(x, y0 + 10, f"pytest passed, as each gate reported it, {k} px a test", size=13.5,
           anchor="start", weight="bold")
    runs_t = (("after step 1", 1248), ("after step 4", 1382), ("after step 7", 1397),
              ("simplify, before", 1424), ("simplify, after", 1424))
    for i, (label, n) in enumerate(runs_t):
        by = y0 + 26 + i * 28
        s.text(x, by + 15, label, size=12, anchor="start")
        bar(s, x + 116, by, n * k, 19, "bar_green")
        s.text(x + 124 + n * k, by + 15, f"{n}", size=12, anchor="start")
    s.text(x + 116, y0 + 180, "1 skipped in each · the last two 30 deselected", size=12,
           anchor="start", colour=t.dim)
    s.tick(x + 8, y0 + 204, size=6)
    s.text(x + 24, y0 + 209, "ruff, format, mypy, lint-imports, `uv lock --check`:", size=12,
           anchor="start")
    s.text(x + 24, y0 + 228, "clean, as in the baseline", size=12, anchor="start", colour=t.dim)
    s.tick(x + 8, y0 + 250, size=6)
    s.text(x + 24, y0 + 255, "web gate, run by `doc-writer` after the commit:", size=12,
           anchor="start")
    s.text(x + 24, y0 + 274, "`vitest` 465 passed, `tsc --noEmit` exit 0", size=12, anchor="start",
           colour=t.dim)
    s.text(x + 24, y0 + 300, "re-review CR-P3B10-01 minor: `view()` now relies on a", size=12,
           anchor="start")
    s.text(x + 24, y0 + 319, "non-ok file having no environments; a comment guards it", size=12,
           anchor="start", colour=t.dim)

    s.text(50, H - 52, "pins: every blocker and major of the batch, all fixed or closed · r1 to r5: "
           "code review rounds · steps 4, 6, 7, 8, 11 change design boards only", size=13.5,
           anchor="start", colour=t.dim)
    s.prefix_key(50, H - 28, ("CR", "SEC"))
    s.text(W - 50, H - 12, "source: spectio environments.py, envfile.py, runner/sacct.py · "
           "spectio_server api/environments.py, api/results.py, failure.py · web/src/runs/imaging · "
           "design/ui-canvas · review records P3-fu86a to P3-fu106a", size=12, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b10-environments-imaging")
