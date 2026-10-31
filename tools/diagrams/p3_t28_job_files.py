#!/usr/bin/env python3
"""Each job's files, read confined and hidden where needed: step P3, P1 Task 28, 2026-10-31.

Writes docs/assets/diagrams/p3-t28-job-files_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t28 at d4f41fce:
- packages/spectio-server/src/spectio_server/projector/nextflow.py `_where`: the event's
  `workDir` (or the trace's) kept as `attempts.work_dir` only when `task_work_rel` accepts it,
  else `path_outside_run` is counted; the trace's `native_id` through `native_id()`, else
  `bad_native_id`; projector/snakemake.py `_logs`: the `log:` paths of `job_info` and
  `job_error`, and the log of `snakemake.slurm_submitted`, through `launch_rel`, kept once each
  as `{path, kind}`, else `path_outside_run`; projector/runs.py `roots()`: from the runs root
  and the run ID; store/schema.py and migrations 0006_attempt_files: `attempts.work_dir`,
  `native_id`, `logs`;
- files/taskfiles.py: `task_work_rel` (exactly two parts, 2 hex then 30 hex, below the run's
  work directory); `launch_rel` (inside the launch directory; `.spectio/` only `head.out`,
  `head.err`, `nextflow.log`); `_NATIVE_ID` up to 128 plain characters; NF_FILES, the eight
  names served (`.command.sh`, `.command.run`, `.command.out`, `.command.err`, `.command.log`,
  `.exitcode`, `.command.begin`, `.command.trace`), and the comment that `.command.env`,
  `.command.in`, `.command.stage` and staged inputs are not; the five states present, not_yet,
  absent, deleted_after_success, cleaned; `check_name` (Snakemake: a recorded path, byte for
  byte); `run_root` (open_private from the runs root and run ID, Cleaned when gone);
  `read_task_file`: `open_confined(root, rel)` with no `work`, so no link is followed; a NUL in
  the first SNIFF 8192 bytes is Binary; `.command.run` goes through `redact_command_run`; others
  through `strip_escapes`; tail TAIL 65536 by default, or one Range, at most MAX_READ 1048576;
- files/confine.py: `_walk_dirs` opens each folder `O_DIRECTORY|O_NOFOLLOW` and `_mine` checks
  the owner; the last component `O_NOFOLLOW|O_NONBLOCK`, regular and yours; `safe_rel` refuses
  a component over NAME_MAX 255 bytes or a name over PATH_MAX 4096 bytes;
- files/pool.py: WORKERS 4, BACKLOG 16, refuses at once when full, Stalled after the timeout;
  api/taskfiles.py: READ_TIMEOUT_S 5.0; `_in_pool` maps Stalled to 503 runner-offline, Binary
  415 binary-file, Cleaned 410 log-cleaned, NotAllowed 422 file-not-allowed, NotFound 404
  log-not-found, OSError EIO and ESTALE to 503 "the file system failed", any other OSError to
  404 "the file could not be read" (fixed text); a Range answer is 206;
- serve.py: `FilePool()` for the routes and `FilePool(FREEZE_WORKERS, 0)` for the StoreSink;
  stages/freeze.py: FREEZE_WORKERS 2, FREEZE_TIMEOUT_S 10.0, a Stalled freeze gives no stages and
  the note "The stage sources were not read in time";
- files/redact.py: the before and after panels are the real output of `redact_command_run` on
  the text shown (run 2026-10-31); the fail-closed panel is its output on `echo ok`,
  `export A=1`, then a line of 70 nested `$(` (MAX_NESTING 64): every line from there hidden;
- in packages/spectio-server, `uv run --locked pytest -q tests/test_taskfiles.py
  tests/test_serve.py tests/api/test_taskfiles_api.py`: all pass (run 2026-10-31; no count, so
  that the figure does not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1330
TOP = 128  # band 1: where the paths come from
COL = (50, 355, 660, 965, 1270)  # band 2: five columns, 280 wide, 25 apart
CW = 280
ROW = 490  # the pictograms of a request
TXT = ROW + 168  # the captions
BIN = ROW + 318  # what each gate answers
RED = 960  # band 3: `.command.run`, before and after
ERR = 1190  # band 4: file system errors


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def answers(s: Sketch, x: float, y: float, rows: tuple[tuple[str, str], ...], *,
            fill: str = "problem", ok: bool = False) -> None:
    """What a gate answers: a bin (or a tray of good answers), the status and its type."""
    s.arrow(x + 32, y - 34, x + 32, y - 6, dashed=True, colour=s.t.dim)
    s.bucket(x + 32, y + 8, 56, 50, fill=fill)
    if ok:
        s.tick(x + 32, y + 30, size=10)
    for i, (code, slug) in enumerate(rows):
        s.text(x + 78, y + 12 + i * 22, f"{code}  `{slug}`", size=13.5, anchor="start")


def lanes(s: Sketch, x: float, y: float, threads: int, waiting: int, *, busy: int, w: float = 150,
          cell: float = 11) -> float:
    """A pool: its threads as lanes with a cog, then its waiting slots as small cells."""
    for i in range(threads):
        ly = y + i * 18
        s.poly([(x, ly), (x + w, ly), (x + w, ly + 13), (x, ly + 13)],
               fill="bar_orange" if i < busy else "surface", amount=0.4, width=1.2)
        s.dot(x - 10, ly + 6.5, 3.2, colour=s.t.good if i < busy else s.t.muted)
    cy = y + threads * 18 + 6
    for k in range(waiting):
        cx = x + (k % 8) * (cell + 4)
        ry = cy + (k // 8) * (cell + 4)
        s.poly([(cx, ry), (cx + cell, ry), (cx + cell, ry + cell), (cx, ry + cell)],
               fill="neutral", amount=0.3, width=1.0)
    return cy + ((waiting + 7) // 8) * (cell + 4)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=281)
    t = theme
    s.heading(50, 58, "P3 Task 28 · each job's files, read inside the run and hidden where needed",
              "`GET /tasks/ID/attempts/n/files` and `.../files/NAME` · api 5 Job files, architecture 13.7, "
              "dev-env 15.3 req. 10 and 13")

    # band 1 -- where the paths come from ------------------------------------------------------
    s.hpc_node(60, TOP, 56, 74, busy=3)
    s.hpc_node(126, TOP, 56, 74, busy=2)
    s.text(200, TOP + 18, "the engine's events", size=15, anchor="start", weight="bold")
    lines(s, 200, TOP + 42, ("Nextflow: `workDir`, `native_id`",
                             "Snakemake: `log:` paths,",
                             "the SLURM job ID and log"))
    s.arrow(430, TOP + 36, 500, TOP + 36)

    s.cog(530, TOP + 36, 14, fill="docs")
    s.text(560, TOP + 18, "the projector, on the writer", size=15, anchor="start", weight="bold")
    lines(s, 560, TOP + 42, ("Nextflow: a task folder, two levels below",
                             "the run's work folder, 2 hex then 30 hex",
                             "Snakemake: a path in the launch folder;",
                             "in `.spectio/` only `head.out`, `head.err`, `nextflow.log`",
                             "a job ID: up to 128 plain characters"))
    answers(s, 560, TOP + 172, (("", "path_outside_run"), ("", "bad_native_id")), fill="problem")
    s.text(560 + 78, TOP + 172 + 56, "counted, not kept", size=13, anchor="start", colour=t.dim)

    s.arrow(985, TOP + 36, 1035, TOP + 36)
    s.text(1045, TOP + 18, "`attempts` row, migration 0006", size=14, anchor="start")
    for i, col in enumerate(("work_dir", "native_id", "logs")):
        cx = 1045 + i * 72
        s.poly([(cx, TOP + 32), (cx + 68, TOP + 32), (cx + 68, TOP + 62), (cx, TOP + 62)],
               fill="input", amount=0.5)
        s.text(cx + 34, TOP + 52, f"`{col}`", size=11.5)
    s.text(1045, TOP + 88, "the roots: from the runs root and", size=13.5, anchor="start", colour=t.dim)
    s.text(1045, TOP + 108, "the run ID, never from a stored path", size=13.5, anchor="start",
           colour=t.dim)

    # the freeze pool, beside the writer
    fx, fy = 1045, TOP + 150
    s.text(fx, fy, "the stage freeze has its own pool", size=14.5, anchor="start", weight="bold")
    lanes(s, fx + 18, fy + 16, 2, 0, busy=0, w=120)
    lines(s, fx + 160, fy + 26, ("2 threads, none waiting,",
                                 "10 s at most for one run"))
    s.text(fx, fy + 76, "route reads never take its slots; a freeze that", size=13, anchor="start",
           colour=t.dim)
    s.text(fx, fy + 95, "stalls holds the writer 10 s, then no stages", size=13, anchor="start",
           colour=t.dim)

    s.line(30, ROW - 66, W - 30, ROW - 66, dashed=True, colour=t.muted)
    s.text(50, ROW - 76, "one request for a job's files, in this order", size=14, anchor="start",
           colour=t.dim)

    # 1 -- ask -----------------------------------------------------------------------------------
    x = COL[0]
    b = s.browser(x, ROW - 10, 270, 140, url="attempts/1/files")
    rows = (("`.command.sh`", "present", True), ("`.command.err`", "present", True),
            ("`.command.log`", "not_yet", False), ("`.command.trace`", "absent", False))
    for i, (name, state, ok) in enumerate(rows):
        ry = b.y + 52 + i * 23
        s.text(x + 14, ry, name, size=12.5, anchor="start")
        s.text(x + 256, ry, state, size=12.5, anchor="end", colour=t.ink if ok else t.dim)
    s.step(x + CW / 2, TXT, 1, "ask for a job's files")
    lines(s, x, TXT + 30, ("the listing names every file it may have",
                           "with a state: present, not_yet, absent,",
                           "deleted_after_success, cleaned",
                           "a read: `.../files/NAME`, as `text/plain`",
                           "`n`: the latest launch that has it"))

    # 2 -- the file pool --------------------------------------------------------------------------
    x = COL[1]
    end = lanes(s, x + 40, ROW + 4, 4, 16, busy=2, w=170)
    s.hourglass(x + 240, ROW + 30, size=11)
    s.text(x + 240, ROW + 62, "5 s", size=14)
    s.text(x + 130, end + 18, "4 threads, 16 waiting", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "in the file pool")
    lines(s, x, TXT + 30, ("its own threads: not the writer's,",
                           "nor the runner's, so a stuck mount",
                           "never stops a run's events",
                           "each listing or read: 5 s at most",
                           "full: refused at once"))
    answers(s, x, BIN, (("503", "runner-offline"),))

    # 3 -- the name -----------------------------------------------------------------------------
    x = COL[2]
    names = (".command.sh", ".command.run", ".command.out", ".command.err",
             ".command.log", ".exitcode", ".command.begin", ".command.trace")
    for i, name in enumerate(names):
        nx, ny = x + (i % 2) * 142, ROW + 4 + (i // 2) * 24
        s.tick(nx + 8, ny + 6, size=5.5)
        s.text(nx + 20, ny + 12, f"`{name}`", size=12.5, anchor="start")
    for i, name in enumerate((".command.env", ".command.in", ".command.stage")):
        nx, ny = x - 4 + i * 104, ROW + 112
        s.cross(nx + 8, ny + 6, size=5)
        s.text(nx + 18, ny + 12, f"`{name}`", size=12, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "the name")
    lines(s, x, TXT + 30, ("Nextflow: these eight names only",
                           "never `.command.env`, `.command.in`,",
                           "`.command.stage` or a staged input",
                           "Snakemake: a path its events",
                           "recorded, byte for byte"))
    answers(s, x, BIN, (("422", "file-not-allowed"),))

    # 4 -- the walk -----------------------------------------------------------------------------
    x = COL[3]
    for i, label in enumerate(("`work`", "`ab`", "`c3f`")):
        fx2 = x + i * 70
        s.folder(fx2, ROW + 10, 56, 46, fill="input", label=label)
        s.lock(fx2 + 50, ROW + 62, size=10)
        s.arrow(fx2 + 58, ROW + 36, fx2 + 68, ROW + 36)
    s.page(x + 214, ROW + 4, 44, 56, fill="surface", lines=3)
    s.lock(x + 254, ROW + 62, size=10, fill="done")
    s.link(x + 70, ROW + 104, size=15)
    s.cross(x + 70, ROW + 104, size=13)
    s.text(x + 100, ROW + 100, "no link followed,", size=13, anchor="start", colour=t.dim)
    s.text(x + 100, ROW + 118, "not even inside the run", size=13, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "the walk")
    lines(s, x, TXT + 30, ("from the run's own folder, by run ID",
                           "one folder at a time, `O_NOFOLLOW`,",
                           "each one yours; then a regular file",
                           "of yours: no FIFO, no device",
                           "a part over 255 bytes, a name over 4096"))
    answers(s, x, BIN, (("422", "file-not-allowed"), ("404", "log-not-found"),
                        ("410", "log-cleaned")))

    # 5 -- what is shown -----------------------------------------------------------------------
    x = COL[4]
    s.page(x + 10, ROW + 4, 70, 92, fill="surface", lines=4)
    s.magnifier(x + 70, ROW + 64, 17)
    s.arrow(x + 104, ROW + 46, x + 134, ROW + 46)
    s.terminal(x + 142, ROW + 4, 132, 92, ("TOKEN=«hidden»", "plain text"), size=11)
    s.text(x + 140, ROW + 126, "last 64 KiB, or one `Range`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "what is shown")
    lines(s, x, TXT + 30, ("a NUL in the first 8 KiB: not text",
                           "escape sequences removed",
                           "`.command.run`: every value hidden",
                           "`?tail=` or one `Range`: 1 MiB at most",
                           "a `Range` answer is 206"))
    answers(s, x, BIN, (("200", "text/plain"), ("206", "a Range")), fill="done", ok=True)
    s.cross(x + 86, BIN + 61, size=6)
    s.text(x + 100, BIN + 66, "415  `binary-file`", size=13.5, anchor="start")

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 46, cx + CW + 23, ROW + 46)

    # band 3 -- `.command.run`, before and after -----------------------------------------------------
    s.line(30, RED - 50, W - 30, RED - 50, dashed=True, colour=t.muted)
    s.text(50, RED - 22, "`.command.run`, read with a shell lexer, not a line pattern:", size=15,
           anchor="start")
    s.text(560, RED - 22, "every assignment value is hidden, here-documents included", size=15,
           anchor="start", colour=t.dim)
    before = ("export TOKEN=s3cret",
              "FOO=bar ./run.sh",
              "docker run -e API_KEY=abc --env=DB_PW=xyz img",
              "cat << EOF > .command.env",
              'export AWS_SECRET="k3y"',
              "EOF",
              "arr=(sec1 sec2)")
    after = ("export TOKEN=«hidden»",
             "FOO=«hidden» ./run.sh",
             "docker run -e API_KEY=«hidden» --env=DB_PW=«hidden» img",
             "cat << EOF > .command.env",
             "export AWS_SECRET=«hidden»",
             "EOF",
             "arr=«hidden»")
    s.text(50, RED + 14, "on disk", size=14, anchor="start", weight="bold")
    s.terminal(50, RED + 24, 440, 182, before, size=12.5, line_h=19)
    s.arrow(500, RED + 115, 548, RED + 115)
    s.text(560, RED + 14, "as served", size=14, anchor="start", weight="bold")
    s.terminal(560, RED + 24, 490, 182, after, size=12.5, line_h=19)

    s.warning(1110, RED + 8, size=10)
    s.text(1128, RED + 14, "fails closed", size=14, anchor="start", weight="bold")
    s.terminal(1110, RED + 24, 220, 150, ("echo ok", "export A=«hidden»", "«hidden»", "«hidden»"),
               size=12.5, line_h=19)
    lines(s, 1346, RED + 44, ("from the line it",
                              "cannot read, all",
                              "is hidden: here",
                              "70 nested `$(`,",
                              "past the 64 limit;",
                              "an open quote or",
                              "here-document too"), size=13)

    # band 4 -- file system errors ---------------------------------------------------------------
    s.shade(50, ERR, 1000, 90, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(78, ERR + 28, size=11)
    s.text(100, ERR + 34, "a file system error the walk does not map: `EIO` or `ESTALE` gives "
           "503 `runner-offline`,", size=13.5, anchor="start")
    s.text(100, ERR + 56, "any other errno 404 `log-not-found`, both with a fixed text:"
           " never the path, never the system's message", size=13.5, anchor="start", colour=t.dim)
    s.terminal(1100, ERR - 22, 450, 122, ("$ cd packages/spectio-server",
                                          "$ uv run --locked pytest -q tests/test_taskfiles.py \\",
                                          "    tests/test_serve.py tests/api/test_taskfiles_api.py",
                                          "all pass"),
               size=12.5, line_h=19)

    s.text(W - 50, H - 16, "source: spectio_server files/, api/taskfiles.py, projector/, serve.py, "
           "stages/freeze.py at d4f41fce · dev-env 15.3 req. 13 · P1 Task 28", size=12.5,
           anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t28-job-files")
