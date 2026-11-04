#!/usr/bin/env python3
"""Resume a run as a child in its lineage's directories: step P3, P1 Task 30, 2026-11-04.

Writes docs/assets/diagrams/p3-t30-resume-lineage_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t30 at 2a4c9b6:
- packages/spectio-server/src/spectio_server/api/relaunch.py: `POST /runs/{id}:relaunch` takes
  `mode: resume` and no other field (else 422 not-in-this-version); row_refusal, then
  profiles (launch command, else `.spectio/run.json`, else 409 profiles_unknown), then check_dirs
  in the file pool; the child manifest with parent_run_id; payload `resume_of` = run_id
  (dir_run_id), parent_run_id, engine_session_id, device, inode; _insert_child runs row_refusal
  again inside the writer's BEGIN IMMEDIATE transaction, state "queued"; 409 run-state-conflict
  with the reason; `GET :launch-template` gives workflow, profiles, params, non_default (params
  unlike the schema defaults) and code_loading (workflow.location when local,
  params.custom_config_base, engine `-c` / `-config` / `--configfile` / `--configfiles`);
  writable_by_others walks the path one component at a time with lstat, flags another owner
  than the user and root, group or other write (sticky excepted above the nearest existing
  part), a link owned by another user, more than 40 links;
- packages/spectio-server/src/spectio_server/resume.py: row_refusal (cli_observed, running,
  not_failed_or_cancelled, resume_in_progress, session_id_refused), resume_refusal is
  `actions.resume` and the 409;
- packages/spectio/src/spectio/runner/resume.py: check_dirs (req. 10 dirs, `nextflow.config`
  and `.nextflow` regular or dir, owned by the user, no 0o022), head_gone (no head.pid: never
  started; other host or boot: head_unverified; alive: running), the lock holder's head gone
  too, processes_in (`/proc/*/cwd` under the launch dir), clear_stale_lock;
- packages/spectio/src/spectio/runner/loop.py `_resume_source`: prove again, device and inode
  must match, clear_stale_lock, unlock for Snakemake;
- packages/spectio/src/spectio/runner/headscript.py: `_RESUME` checks `stat -c %d:%i .`, umask
  022; head.pid written or exit 1 (SEC-P3T30-03); `.spectio-launch.lock` under `set -C`;
  Nextflow `-resume SESSION`, Snakemake `--unlock` then `--rerun-incomplete`;
  write_launch_files makes `.nextflow/` 0700 (CR-P3T30-02); NXF_LOG_FILE in the run's own
  `.spectio/`;
- packages/spectio-server/src/spectio_server/store/runs.py insert_run: a child takes its
  parent's launch_dir, work_dir and lineage_id (or the parent's ID); failure.dir_run_id is
  `lineage_id or id`, used by the projector roots, job files, failure tails, task resources;
- packages/spectio-server/src/spectio_server/api/logs.py: head files from the run's own
  `.spectio/`, Nextflow's log too; Snakemake: the newest `.snakemake/log/*.log` with mtime
  between created_at and `exited_at or ended_at` (plus MTIME_SLACK_S each side), a terminal run
  with neither is 404 log-not-found;
- the time line is test_logs_snakemake_lineage_own_log (tests/api/test_read.py): old.log at
  T0 - 1 h, the parent created at T0, parent.log at T0 + 0.5 h, its head exit at T0 + 1 h, the
  child created at T0 + 2 h, child.log at T0 + 3 h; the lineage is
  test_resume_of_a_resume_keeps_the_first_directories; the link case is "link in shared" of
  test_req16_code_loading_flagged_paths;
- `uv run --locked pytest -q packages/spectio-server/tests/api/test_relaunch.py
  packages/spectio/tests/test_headscript.py packages/spectio-server/tests/api/test_read.py
  packages/spectio-server/tests/api/test_taskfiles_api.py`: all pass (run 2026-11-04; no count,
  so that the figure does not go stale);
- the pins are docs/reviews/code/P3-t30.md: the blocker and the majors fixed in rounds 1 to 3,
  the minors still open after round 4 (both verdicts approve). IDs restart per round, so each
  pin names its round.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1560
TOP = 128  # band 1: the Resume, asked and run
CAP1 = TOP + 252
PIN1 = 500
DIV1 = 566
TOP2 = 606  # band 2: the lineage on disk
CAP2 = 944
DIV2 = 1020
TOP3 = 1050  # band 3: the Snakemake log, and Copy to a new launch
CAP3 = 1268
DIV3 = 1352


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start") -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...]) -> None:
    """A finding the branch fixed, pinned where it hit."""
    s.tick(x + 8, y - 5, size=7)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)


def run_folder(s: Sketch, x: float, y: float, w: float, name: str, state: str, fill: str,
               spectio: str) -> None:
    """A child's run directory: its own `.spectio/`, a launch dir holding its head files only,
    and a work dir nobody uses."""
    s.folder(x, y, w, 226, fill="neutral")
    s.text(x + 16, y + 36, f"`{name}`", size=15, anchor="start", weight="bold")
    s.text(x + 90, y + 36, state, size=13, anchor="start", colour=s.t.dim)
    s.text(x + 16, y + 58, "`.spectio/run.json`", size=12.5, anchor="start", colour=s.t.dim)
    s.folder(x + 14, y + 70, w - 28, 84, fill=fill)
    s.text(x + 28, y + 100, "`launch/`", size=13, anchor="start")
    s.text(x + 28, y + 122, spectio, size=12.5, anchor="start", colour=s.t.dim)
    s.text(x + 28, y + 140, "`nextflow.log` too", size=12.5, anchor="start", colour=s.t.dim)
    s.shade(x + 14, y + 166, w - 28, 46, fill="neutral", opacity=0.3, colour=s.t.muted, dashed=True)
    s.text(x + 28, y + 194, "`work/` unused", size=13, anchor="start", colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=30)
    t = theme
    s.heading(50, 58, "P3 Task 30 · Resume a run as a child, in its first run's directories",
              "`POST /runs/run_id:relaunch`, `GET :launch-template` · api 5 and 5.1, notes of "
              "2026-10-28, dev-env 15.3 req. 7, 10 and 16 · the parent keeps its state")

    # 1 -- Resume is asked ----------------------------------------------------------------------
    s.browser(50, TOP, 330, 214, url="`GET /runs/run_A`")
    s.text(70, TOP + 60, "`run A`", size=15, anchor="start", weight="bold")
    s.shade(150, TOP + 42, 90, 26, fill="problem", opacity=0.7)
    s.text(195, TOP + 60, "failed", size=13.5)
    s.text(70, TOP + 92, "`command`: the engine's argv,", size=13, anchor="start")
    s.text(70, TOP + 112, "quoted for a shell", size=13, anchor="start", colour=t.dim)
    s.tick(78, TOP + 140, size=7)
    s.text(94, TOP + 146, "`actions.resume` allowed", size=13, anchor="start")
    s.button(66, TOP + 166, 96, "Resume", fill="done")
    s.button(174, TOP + 166, 192, "Copy to a new launch", fill="input")
    s.step(215, CAP1, 1, "Resume is asked")
    lines(s, 50, CAP1 + 30, ("`POST /runs/run_A:relaunch`",
                             "`mode: resume` and nothing else, else 422",
                             "from a failed or cancelled run only"))

    s.arrow(390, TOP + 100, 424, TOP + 100)

    # 2 -- proven safe ----------------------------------------------------------------------------
    x = 436
    s.folder(x, TOP + 4, 124, 86, fill="input", label="`launch/`")
    s.magnifier(x + 112, TOP + 72, 17)
    s.text(x + 156, TOP + 30, "the lineage's", size=13.5, anchor="start")
    s.text(x + 156, TOP + 50, "launch directory,", size=13.5, anchor="start")
    s.text(x + 156, TOP + 70, "read in the file pool", size=13, anchor="start", colour=t.dim)
    for i, row in enumerate(("the parent's head is proven gone",
                             "no process has its cwd in there",
                             "the lock's holder is gone too",
                             "no planted `.nextflow` or `nextflow.config`",
                             "a Nextflow session ID is a UUID")):
        y = TOP + 124 + i * 22
        s.tick(x + 8, y - 5, size=6)
        s.text(x + 22, y, row, size=13, anchor="start")
    s.step(x + 180, CAP1, 2, "proven safe, twice")
    lines(s, x, CAP1 + 30, ("on the run's row, then its directories",
                            "a refusal is 409 with its reason,",
                            "the same as `actions.resume`"))

    s.arrow(806, TOP + 100, 840, TOP + 100)

    # 3 -- one queued child ---------------------------------------------------------------------
    x = 852
    s.page(x, TOP + 30, 92, 104, fill="problem", lines=0)
    s.text(x + 46, TOP + 72, "`run A`", size=14)
    s.text(x + 46, TOP + 94, "failed", size=13, colour=t.dim)
    s.page(x + 210, TOP + 30, 92, 104, fill="input", lines=0)
    s.text(x + 256, TOP + 72, "`run B`", size=14)
    s.text(x + 256, TOP + 94, "queued", size=13, colour=t.dim)
    s.arc(x + 206, TOP + 60, x + 98, TOP + 60, lift=-30, colour=t.dim)
    s.text(x + 152, TOP + 20, "`parent_run_id`", size=12.5, colour=t.dim)
    s.cog(x + 152, TOP + 104, 10, fill="work")
    s.text(x + 152, TOP + 134, "the writer", size=12.5, colour=t.dim)
    s.envelope(x, TOP + 160, 44, 30, fill="docs")
    s.text(x + 56, TOP + 170, "its `launch` command: `resume_of`", size=13, anchor="start")
    s.text(x + 56, TOP + 190, "first run, session, device, inode", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + 152, CAP1, 3, "one queued child run")
    lines(s, x, CAP1 + 30, ("checked again in `BEGIN IMMEDIATE`:",
                            "two clicks make one child",
                            "the child has its own run directory"))

    s.arrow(1176, TOP + 100, 1210, TOP + 100)

    # 4 -- the runner, and the head in place --------------------------------------------------
    x = 1222
    s.runner(x, TOP + 18, 108, 54)
    s.text(x + 126, TOP + 22, "proves it all again,", size=13, anchor="start")
    s.text(x + 126, TOP + 42, "same device and inode,", size=13, anchor="start", colour=t.dim)
    s.text(x + 126, TOP + 62, "a dead head's lock removed", size=13, anchor="start", colour=t.dim)
    s.terminal(x, TOP + 86, 338, 128, ("cd run_A/launch",
                                       "stat -c %d:%i . is DEV:INO",
                                       "umask 022, set -C the lock",
                                       "nextflow run ... -resume SESSION",
                                       "snakemake --unlock, --rerun-incomplete"),
               size=12, line_h=17)
    s.step(x + 169, CAP1, 4, "the head runs in place")
    lines(s, x, CAP1 + 30, ("in run A's launch and work directories",
                            "the engine only behind `.spectio-launch.lock`",
                            "no `head.pid` written: the head stops"))

    # the fixed findings of band 1, under what they fixed ---------------------------------------
    pin(s, 436, PIN1, "R1 CR-P3T30-02", ("`.nextflow/` made 0700 at launch:",
                                         "a umask 002 no longer refuses Resume"))
    pin(s, 852, PIN1, "R2 CR-P3T30-04", ("a rebuilt run has no launch command:",
                                         "profiles read from `run.json`"))
    pin(s, 1222, PIN1, "R3 SEC-P3T30-03", ("`head.pid` not written, no engine, so",
                                           "a missing one proves never started"))

    s.line(30, DIV1, W - 30, DIV1, dashed=True, colour=t.muted)
    s.text(50, DIV1 + 24, "on disk, under the runs root: a Resume of a Resume", size=14,
           anchor="start", colour=t.dim)

    # 5 -- the lineage on disk ------------------------------------------------------------------
    y = TOP2 + 6
    s.folder(50, y, 440, 226, fill="neutral")
    s.text(66, y + 36, "`run A`", size=15, anchor="start", weight="bold")
    s.text(140, y + 36, "failed, the first run", size=13, anchor="start", colour=t.dim)
    s.text(66, y + 58, "`.spectio/run.json`", size=12.5, anchor="start", colour=t.dim)
    s.folder(64, y + 70, 236, 142, fill="input")
    s.text(78, y + 100, "`launch/`", size=13, anchor="start")
    for i, row in enumerate(("`.spectio/` head of A", "`.nextflow/` 0700, `.snakemake/`",
                             "`.spectio-launch.lock`")):
        s.text(78, y + 124 + i * 20, row, size=12.5, anchor="start", colour=t.dim)
    s.lock(282, y + 192, size=11)
    s.folder(312, y + 70, 164, 142, fill="work")
    s.text(326, y + 100, "`work/`", size=13, anchor="start")
    s.task_strip(326, y + 116, ((10, "bar_orange", ""),), cell=10, gap=3, h=14)
    s.task_strip(326, y + 136, ((7, "bar_orange", ""),), cell=10, gap=3, h=14)
    s.text(394, y + 188, "task dirs, reused", size=12.5, colour=t.dim)

    run_folder(s, 560, y, 236, "run B", "failed, of A", "input", "`.spectio/` head of B")
    run_folder(s, 830, y, 236, "run C", "queued, of B", "input", "`.spectio/` head of C")

    by = y + 232
    s.arc(670, by, 210, by, lift=-36, colour=t.ink)
    s.arc(940, by, 380, by, lift=-62, colour=t.ink)

    s.step(558, CAP2, 5, "a lineage runs in its first run's directories")
    lines(s, 558, CAP2 + 28, ("B and C run their engines in A's directories, `lineage_id` A",
                              "each run keeps its own `.spectio/`, head files and state"),
          anchor="middle")

    rx = 1112
    s.text(rx, TOP2 + 20, "read from the first run's directories", size=14, anchor="start",
           weight="bold")
    s.text(rx, TOP2 + 40, "`dir_run_id`: `lineage_id`, else the run's own ID", size=12.5,
           anchor="start", colour=t.dim)
    for i, row in enumerate(("the projector's paths from events",
                             "a job's files, the failures' log tails",
                             "Snakemake benchmarks, sacct's directory",
                             "the Snakemake engine log, see 6")):
        yy = TOP2 + 66 + i * 21
        s.dot(rx + 6, yy - 4, 2.6, colour=t.dim)
        s.text(rx + 18, yy, row, size=13, anchor="start")
    s.text(rx, TOP2 + 172, "read from the run's own `.spectio/`", size=14, anchor="start",
           weight="bold")
    for i, row in enumerate(("`head-out`, `head-err`", "the Nextflow engine log")):
        yy = TOP2 + 196 + i * 21
        s.dot(rx + 6, yy - 4, 2.6, colour=t.dim)
        s.text(rx + 18, yy, row, size=13, anchor="start")
    pin(s, rx, TOP2 + 274, "R1 CR-P3T30-01 blocker", ("a child looked in its own empty dirs:",
                                                       "no job files, no failure tails"))

    s.line(30, DIV2, W - 30, DIV2, dashed=True, colour=t.muted)

    # 6 -- the Snakemake log, to scale ------------------------------------------------------------
    s.text(50, TOP3, "one `.snakemake/log/` for the lineage, from the test", size=14, anchor="start")
    s.text(50, TOP3 + 20, "`test_logs_snakemake_lineage_own_log`, hours from T0", size=13,
           anchor="start", colour=t.dim)
    ph = 100  # pixels per hour; the axis runs from T0 - 1.5 h to T0 + 3.6 h
    x0 = 80 + 1.5 * ph

    def at(hours: float) -> float:
        return x0 + hours * ph

    ay = TOP3 + 112
    s.shade(at(0), TOP3 + 40, ph, 58, fill="problem", opacity=0.6)
    s.text(at(0) + 8, TOP3 + 60, "`run A`", size=13, anchor="start")
    s.text(at(0) + 8, TOP3 + 80, "to its exit", size=12, anchor="start", colour=t.dim)
    s.shade(at(2), TOP3 + 40, at(3.6) - at(2), 58, fill="input", opacity=0.8)
    s.text(at(2) + 8, TOP3 + 60, "`run B`, from its creation", size=13, anchor="start")
    s.text(at(2) + 8, TOP3 + 80, "no exit yet", size=12, anchor="start", colour=t.dim)
    s.arrow(at(-1.5), ay, at(3.6), ay, colour=t.dim)
    for h in range(-1, 4):
        s.line(at(h), ay - 5, at(h), ay + 5, colour=t.dim, passes=1, amount=0.3)
        s.text(at(h), ay + 22, "T0" if h == 0 else f"{h:+d} h", size=12, colour=t.dim)
    for name, hours, picked in (("old.log", -1, False), ("parent.log", 0.5, True),
                                ("child.log", 3, True)):
        cx = at(hours)
        s.page(cx - 12, ay + 32, 24, 30, fill="surface" if picked else "neutral", lines=2)
        s.text(cx, ay + 80, f"`{name}`", size=12.5, colour=t.ink if picked else t.dim)
        if picked:
            s.tick(cx + 22, ay + 44, size=6)
    s.step(at(1.05), CAP3, 6, "each run reads its own Snakemake log")
    lines(s, at(1.05), CAP3 + 28, ("the newest written between its creation and its exit",
                                   "no exit known: the run's end, neither: 404"),
          anchor="middle", size=13)

    pin(s, 600, TOP3 + 60, "R2 CR-P3T30-03", ("every run of the lineage", "read its newest log"))
    pin(s, 600, TOP3 + 140, "R3 CR-P3T30-05", ("the window is closed when", "`exited_at` is null"))

    # 7 -- Copy to a new launch -------------------------------------------------------------------
    x = 836
    s.browser(x, TOP3 - 6, 330, 196, url="`GET :launch-template`")
    s.text(x + 18, TOP3 + 46, "a `POST /runs` body, prefilled", size=13.5, anchor="start")
    s.text(x + 18, TOP3 + 66, "`non_default`: params unlike defaults", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x + 18, TOP3 + 92, "`code_loading`", size=13.5, anchor="start", weight="bold")
    for i, (field, flagged) in enumerate((("`workflow.location`", True),
                                          ("`params.custom_config_base`", False),
                                          ("`engine.-c`", False))):
        yy = TOP3 + 116 + i * 22
        if flagged:
            s.warning(x + 26, yy - 5, size=7)
        else:
            s.tick(x + 26, yy - 5, size=6)
        s.text(x + 40, yy, field, size=12.5, anchor="start")
    s.text(x + 312, TOP3 + 116, "writable by others", size=12, anchor="end", colour=t.warn)

    lx = 1196
    s.folder(lx, TOP3 + 2, 156, 76, fill="problem")
    s.text(lx + 14, TOP3 + 34, "`open/` 0777", size=13, anchor="start")
    s.link(lx + 44, TOP3 + 58, size=13)
    s.text(lx + 66, TOP3 + 64, "`current`", size=12.5, anchor="start")
    s.arrow(lx + 136, TOP3 + 58, lx + 196, TOP3 + 44)
    s.folder(lx + 206, TOP3 + 2, 150, 76, fill="done")
    s.text(lx + 220, TOP3 + 34, "`mine/` 0700", size=13, anchor="start")
    s.lock(lx + 236, TOP3 + 58, size=11, fill="done")
    s.text(lx + 254, TOP3 + 64, "`main.nf`", size=12.5, anchor="start")
    s.warning(lx + 10, TOP3 + 104, size=9)
    s.text(lx + 28, TOP3 + 110, "flagged: others can repoint the link", size=13, anchor="start")
    pin(s, lx, TOP3 + 150, "R1 SEC-P3T30-01", ("another owner, or a missing", "file in a shared dir"))
    pin(s, lx + 196, TOP3 + 150, "R2 SEC-P3T30-02", ("each part `lstat`ed, links", "one by one, 40 at most"))

    s.step(1196, CAP3, 7, "Copy to a new launch")
    lines(s, 1196, CAP3 + 28, ("each value that loads code is listed,",
                               "flagged when someone else could change it"),
          anchor="middle", size=13)

    s.line(30, DIV3, W - 30, DIV3, dashed=True, colour=t.muted)

    # the tests, and what is still open -----------------------------------------------------------
    s.terminal(50, DIV3 + 22, 470, 120, ("$ uv run --locked pytest \\",
                                          "    packages/spectio-server/tests/api/test_relaunch.py \\",
                                          "    packages/spectio/tests/test_headscript.py",
                                          "75 passed, 1 deselected"), size=12, line_h=19)
    ox = 560
    s.text(ox, DIV3 + 36, "open after round 4, all minor, both verdicts approve", size=14,
           anchor="start")
    opened = (("R3 CR-P3T30-06", "`run.json` read in the request thread"),
              ("R3 CR-P3T30-07", "`profiles_unknown` only from the POST"),
              ("R3 CR-P3T30-08", "a rebuilt run's detail shows no profiles"),
              ("R4 CR-P3T30-06", "no test for the upper bound's slack"),
              ("R3 SEC-P3T30-04", "`--unlock` sees this host's `/proc` only"),
              ("R3 SEC-P3T30-05", "a 0775 `modules/` in a 0755 location"),
              ("R3 SEC-P3T30-06", "`--configfile=x`, and later values, missed"),
              ("R3 SEC-P3T30-07", "adopt and rebuild ignore `.spectio/launch`"))
    for i, (fid, what) in enumerate(opened):
        cx = ox + (i // 4) * 500
        yy = DIV3 + 64 + (i % 4) * 24
        s.warning(cx + 8, yy - 5, size=7)
        s.text(cx + 22, yy, fid, size=12.5, anchor="start", weight="bold", colour=t.accent)
        s.text(cx + 150, yy, what, size=12.5, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 40, ("SEC", "CR"))
    s.text(50, H - 18, "R1 to R4: the code review rounds, IDs restart in each round; a tick: fixed "
           "on the branch", size=12.5, anchor="start", colour=t.dim)
    s.text(W - 50, H - 18, "source: spectio_server/api/relaunch.py, resume.py, api/logs.py, "
           "spectio/runner/resume.py, headscript.py · P1 Task 30", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t30-resume-lineage")
