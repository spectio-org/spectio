#!/usr/bin/env python3
"""The Snakemake logger plugin writes the spool: step P3, P1 Task 7, 2026-11-01.

Writes docs/assets/diagrams/p3-t7-snakemake-logger_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t7 at 607dbdee (BASE 4eff69e):
- engine-bridges/snakemake-logger-plugin-spectio/snakemake_logger_plugin_spectio/__init__.py:
  found by module name through PYTHONPATH (`--logger spectio`), no install; silent with none of
  SPECTIO_RUN_ID, SPECTIO_LAUNCH_N, SPECTIO_SPOOL_DIR set, one stderr line when one is wrong;
  `emit` runs on Snakemake's QueueListener thread (snakemake 9.27.1 logging.py:671-679, cited in
  the module docstring); _EVENTS: 11 builders (workflow_started, run_info, resources_info,
  rulegraph, job_info, job_started, job_finished, job_error, shellcmd as an empty map, progress,
  error); a record with no event, an unlisted one, or one missing a _REQUIRED key becomes
  snakemake.log with its level only; slurm_submitted() parses the SLURM executor plugin 2.8.0
  submission text into snakemake.slurm_submitted; _job_info pops resources.slurm_extra and cuts
  reason after _PARAMS_CHANGED "Params have changed since last execution"; _job_error sends only
  aux.external_jobid; Spool.write: a line over MAX_LINE_BYTES 65536 is retried for job_info and
  job_error with empty input and output, else dropped; ROTATE_BYTES 33554432; one os.write loop
  per line on O_APPEND; a failed write calls _cut_back (ftruncate to the last full line);
  _open_dir: events/ made 0700, opened O_DIRECTORY|O_NOFOLLOW, refused unless owned by the
  effective uid with no group or other bits; _next: O_CREAT|O_EXCL|O_NOFOLLOW 0600 relative to
  the directory descriptor, index + 1 tried, advanced only on success or FileExistsError, up to
  LAST_INDEX 9999; error(): .spectio/bridge.err, MAX_ERROR_LINES 100, not a regular file:
  stderr; emit catches every Exception.
- The fixes (commit b9459710): CR-P3T7-01 round 1 (a failed create used up an index) and
  CR-P3T7-02 round 1 (reason carried the param values). Tests test_failed_create_keeps_the_index
  (two PermissionError creates, then the only file is snakemake-logger-spectio-1-0001.jsonl
  holding the third event) and test_job_info_reason_params_detail_cut.
- Not fixed in this step, minor (worker report and review rounds, docs/reviews/code/P3-t7.md):
  round 1 SEC-P3T7-01 (a pre-existing bridge.err is appended to unchecked), SEC-P3T7-02 (any
  record's text can forge a slurm_submitted), SEC-P3T7-03 (interface 1.1.0 resolved without
  hashes in CI), SEC-P3T7-04 (a stalled file system holds Snakemake's exit), CR-P3T7-03 (the
  fixture test compares types and keys only); round 2 CR-P3T7-03 and SEC-P3T7-01 (the marker copy
  is kept equal to spectio_sdk.events by a comment only).
- The bars: tests/fixtures/engine-events/logger-plugin/snakemake-9.27.1_files.spool.jsonl, the
  `files` workflow with config fail=1 on Snakemake 9.27.1 (recorded by test_recorded_fixture_
  current, paths normalised): 25 lines, 8058 bytes, longest line 652 bytes; snakemake.log 9;
  job_info, job_started, shellcmd, error, resources_info 2 each; workflow_started, rulegraph,
  run_info, job_finished, progress, job_error 1 each.
- `uv run --locked --directory engine-bridges/snakemake-logger-plugin-spectio pytest -q`:
  43 passed, run 2026-11-01.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1320
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 140  # the pictograms of the flow
TXT = ROW + 150  # the captions
FIX = 530  # the before and after panels
LOW = 1060  # the measured run and the notes


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          step: float = 21) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * step, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, label: str) -> None:
    """A finding pinned where it hits: a red dot and its ID."""
    s.circle(x, y - 5, 6, fill="problem", colour=s.t.accent, width=1.6)
    s.text(x + 13, y, label, size=13, anchor="start", colour=s.t.accent)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s._parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 1.5):.1f}" height="{h:.1f}" rx="2" '
        f'fill="{s.t.fill(fill)}" stroke="{s.t.ink}" stroke-width="0.9"/>'
    )


def sieve(s: Sketch, cx: float, top: float, w: float = 70, h: float = 46) -> None:
    """A funnel with holes: the allow-listed keys pass, the rest is held back."""
    s.poly([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.14, top + h), (cx - w * 0.14, top + h)],
           fill="gate", amount=0.8)
    for dx, dy in ((-18, 12), (0, 12), (18, 12), (-9, 26), (9, 26)):
        s.dot(cx + dx, top + dy, 2.4, colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=77)
    t = theme
    s.heading(50, 58, "P3 Task 7 · the Snakemake logger plugin writes the spool, and never fails the run",
              "`engine-bridges/snakemake-logger-plugin-spectio`, api 14.1, architecture 13.1 and 13.4 · "
              "each log record becomes one allow-listed event; stdlib and the interface only")

    # 1 -- Snakemake ---------------------------------------------------------------------------
    x = COL[0]
    s.terminal(x, ROW - 14, 270, 58, ("$ snakemake --logger spectio",), size=12.5)
    for i in range(4):
        s.envelope(x + 20 + i * 34, ROW + 62, 26, 22, fill="input")
    s.arrow(x + 162, ROW + 73, x + 196, ROW + 73)
    s.cog(x + 222, ROW + 73, 13, fill="work")
    s.text(x + 140, ROW + 116, "records, on the QueueListener thread", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "Snakemake logs")
    lines(s, x, TXT + 30, ("found on `PYTHONPATH`, never installed",
                           "added next to Snakemake's own log",
                           "silent unless `SPECTIO_RUN_ID`,",
                           "`_LAUNCH_N`, `_SPOOL_DIR` are set"))

    # 2 -- the allow-list ----------------------------------------------------------------------
    x = COL[1]
    for i, (key, ok) in enumerate((("`jobid`", True), ("`threads`", True), ("`slurm_extra`", False))):
        y = ROW + 6 + i * 30
        s.text(x + 6, y + 14, key, size=12.5, anchor="start")
        if ok:
            s.tick(x + 116, y + 8, size=6)
        else:
            s.cross(x + 116, y + 8, size=6)
    s.arrow(x + 134, ROW + 40, x + 168, ROW + 40)
    sieve(s, x + 216, ROW + 14, w=82, h=56)
    s.text(x + 140, ROW + 116, "one builder per Snakemake event, 11", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "allow-listed keys")
    lines(s, x, TXT + 30, ("each type keeps its api 14.1 keys",
                           "unknown or incomplete: `snakemake.log`,",
                           "its level only; `shellcmd` sent empty",
                           "SLURM submission text: `slurm_submitted`"))

    # 3 -- one line ----------------------------------------------------------------------------
    x = COL[2]
    s.page(x + 70, ROW - 4, 150, 86, fill="surface", lines=0)
    for i, row in enumerate(("`v id run launch`", "`producer seq time`", "`type data`")):
        s.text(x + 82, ROW + 24 + i * 20, row, size=12, anchor="start")
    s.text(x + 140, ROW + 116, "`snakemake-logger-spectio/0.0.1`", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "one line per event")
    lines(s, x, TXT + 30, ("one `write` per line, `seq` without gaps",
                           "over 64 KiB: a job's file lists dropped,",
                           "then the whole line, logged",
                           "every error caught, the run goes on"))

    # 4 -- the spool files ---------------------------------------------------------------------
    x = COL[3]
    s.folder(x + 6, ROW - 4, 268, 106, fill="input")
    s.text(x + 140, ROW + 30, "`.spectio/events/`", size=13)
    for i in range(3):
        s.page(x + 70 + i * 50, ROW + 42, 40, 50, fill="surface", lines=3)
    s.lock(x + 238, ROW + 70, size=13, fill="done")
    s.text(x + 140, ROW + 124, "`snakemake-logger-spectio-1-0001.jsonl`", size=12, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "the spool files")
    lines(s, x, TXT + 30, ("a new file before 32 MiB, up to 9999",
                           "exclusive create, 0600, no symlink",
                           "`events` 0700 and yours, else refused",
                           "a failed write cut to the last full line"))

    # 5 -- bridge.err --------------------------------------------------------------------------
    x = COL[4]
    s.page(x + 20, ROW - 2, 96, 110, fill="problem", lines=5)
    s.warning(x + 68, ROW + 22, size=12)
    s.text(x + 136, ROW + 34, "`.spectio/bridge.err`", size=12.5, anchor="start")
    s.text(x + 136, ROW + 58, "next to `events`", size=13, anchor="start", colour=t.dim)
    s.text(x + 136, ROW + 80, "not a regular file:", size=13, anchor="start", colour=t.dim)
    s.text(x + 136, ROW + 98, "stderr instead", size=13, anchor="start", colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "errors on the side")
    lines(s, x, TXT + 30, ("at most 100 lines",
                           "nothing raises into Snakemake:",
                           "a lost event, never a lost run"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 42, cx + CW + 23, ROW + 42)

    # what the review changed ------------------------------------------------------------------
    s.line(30, FIX - 62, W - 30, FIX - 62, dashed=True, colour=t.muted)
    s.text(50, FIX - 72, "what review round 1 changed, before and after", size=14,
           anchor="start", colour=t.dim)
    PX = (50, 560, 1070)

    # A -- a failed create
    x = PX[0]
    s.text(x, FIX, "A · a create fails: no permission, inode quota", size=17, anchor="start")
    s.text(x, FIX + 30, "the test: the first two creates refused, three events", size=13,
           anchor="start", colour=t.dim)
    for row, (label, names) in enumerate((("before", ("0001", "0002", "0003")),
                                          ("after", ("0001", "0001", "0001")))):
        y = FIX + 52 + row * 84
        s.text(x, y + 30, label, size=14, anchor="start", weight="bold")
        for i, name in enumerate(names):
            px = x + 76 + i * 96
            ok = i == 2
            s.page(px, y, 30, 38, fill="surface" if ok else "problem", lines=0 if not ok else 2)
            s.text(px + 15, y + 56, f"`{name}`", size=12.5, colour=t.ink if ok else t.dim)
            if ok:
                s.tick(px + 52, y + 18, size=8)
            else:
                s.cross(px + 15, y + 19, size=8)
            if i < 2:
                s.arrow(px + 40, y + 19, px + 92, y + 19, colour=t.dim)
    lines(s, x, FIX + 222, ("before: one index used up per refused event,",
                            "after 9999 none left for the rest of the launch",
                            "after: the index moves only on success or on a",
                            "file that exists, as `nf-spectio` does"), size=13, step=19)
    pin(s, x + 8, FIX + 314, "CR-P3T7-01, round 1")

    # B -- the reason text
    x = PX[1]
    s.text(x, FIX, "B · a job's reason quotes its param values", size=17, anchor="start")
    s.text(x, FIX + 30, "a param built from the environment would reach the spool", size=13,
           anchor="start", colour=t.dim)
    y = FIX + 64
    s.text(x, y + 16, "before", size=14, anchor="start", weight="bold")
    bar(s, x + 70, y, 316, 24, "neutral")
    bar(s, x + 386, y, 92, 24, "problem")
    s.text(x + 228, y + 17, "`Params have changed since last execution`", size=11.5, anchor="middle")
    s.text(x + 432, y + 17, "the values", size=12.5, anchor="middle")
    s.text(x + 70, y + 46, "written to the 0600 spool as it came", size=13, anchor="start", colour=t.dim)

    y = FIX + 140
    s.text(x, y + 16, "after", size=14, anchor="start", weight="bold")
    bar(s, x + 70, y, 316, 24, "neutral")
    s.text(x + 228, y + 17, "`Params have changed since last execution`", size=11.5, anchor="middle")
    s.shade(x + 390, y, 88, 24, fill="neutral", opacity=0.3, colour=t.muted, dashed=True)
    s.line(x + 389, y - 10, x + 389, y + 34, dashed=True, colour=t.accent, passes=1, amount=0.3)
    s.cross(x + 434, y + 12, size=8)
    lines(s, x + 70, y + 50, ("cut after the marker, at the source,",
                              "the same cut the server makes:",
                              "`_cut_params_detail` in `spectio_sdk.events`"), size=13, step=19)
    s.text(x, FIX + 274, "`slurm_extra` was already removed the same way", size=13, anchor="start",
           colour=t.dim)
    pin(s, x + 8, FIX + 314, "CR-P3T7-02, round 1")

    # C -- still open
    x = PX[2]
    s.text(x, FIX, "C · still open, minor", size=17, anchor="start")
    s.text(x, FIX + 30, "not changed in this step", size=13, anchor="start", colour=t.dim)
    open_ = (
        ("SEC-P3T7-01, round 1", "a `bridge.err` already there is appended to,", "its owner and mode unchecked"),
        ("SEC-P3T7-02, round 1", "any record's text can forge a", "`slurm_submitted` job ID and log"),
        ("SEC-P3T7-04, round 1", "a stalled file system holds", "Snakemake's exit, no test for it"),
        ("CR-P3T7-03, round 2", "the marker copy is kept equal", "to the SDK's by a comment only"),
    )
    for i, (fid, a, b) in enumerate(open_):
        y = FIX + 62 + i * 60
        s.warning(x + 8, y - 5, size=7)
        s.text(x + 24, y, fid, size=13, anchor="start", colour=t.warn)
        s.text(x + 24, y + 19, a, size=13, anchor="start", colour=t.dim)
        s.text(x + 24, y + 37, b, size=13, anchor="start", colour=t.dim)
    s.text(x, FIX + 314, "also round 1: CR-P3T7-03 fixture values, SEC-P3T7-03 no hashes in CI",
           size=12.5, anchor="start", colour=t.dim)

    for px in PX[1:]:
        s.line(px - 16, FIX - 14, px - 16, FIX + 324, dashed=True, colour=t.muted, passes=1)

    # the recorded run -------------------------------------------------------------------------
    s.line(30, LOW - 130, W - 30, LOW - 130, dashed=True, colour=t.muted)
    s.text(50, LOW - 140, "a real run: the two-rule `files` workflow, `broken` made to fail, Snakemake 9.27.1, "
           "recorded as the fixture", size=14, anchor="start", colour=t.dim)
    counts = (("log", 9), ("job_info", 2), ("job_started", 2), ("shellcmd", 2), ("error", 2),
              ("resources_info", 2), ("workflow_started", 1), ("rulegraph", 1), ("run_info", 1),
              ("job_finished", 1), ("progress", 1), ("job_error", 1))
    per = 26.0  # px per event
    y0 = LOW - 92
    s.text(50, y0, "25 events, one bar each type, 26 px per event", size=14.5, anchor="start")
    for i, (name, n) in enumerate(counts):
        y = y0 + 14 + i * 20
        s.text(260, y + 13, f"`snakemake.{name}`", size=12, anchor="end")
        fill = "neutral" if name == "log" else "problem" if name in ("error", "job_error") else "input"
        bar(s, 270, y, n * per, 14, fill)
        s.text(278 + n * per, y + 13, str(n), size=12.5, anchor="start", colour=t.dim)
    s.text(50, y0 + 270, "8058 bytes in one file, longest line 652 of 65 536", size=13,
           anchor="start", colour=t.dim)

    nx = 820
    s.text(nx, y0, "never in the spool", size=14.5, anchor="start")
    for i, (row, sub) in enumerate((
            ("a value from the environment", "a planted token, checked on every real run"),
            ("`slurm_extra`, the raw sbatch flags", "popped from `resources` before the line"),
            ("the job's command as a key", "`shellcmd` is sent as an empty map"))):
        y = y0 + 28 + i * 44
        s.cross(nx + 10, y - 4, size=7)
        s.text(nx + 28, y, row, size=13.5, anchor="start")
        s.text(nx + 28, y + 18, sub, size=13, anchor="start", colour=t.dim)
    s.text(nx + 380, y0 + 28, "`snakemake.error` text can quote", size=13, anchor="start", colour=t.dim)
    s.text(nx + 380, y0 + 48, "the failed command: the server", size=13, anchor="start", colour=t.dim)
    s.text(nx + 380, y0 + 68, "hides it before storing, api 14.1", size=13, anchor="start", colour=t.dim)

    s.terminal(nx, y0 + 160, 730, 96, ("$ uv run --locked --directory \\",
                                        "    engine-bridges/snakemake-logger-plugin-spectio pytest -q",
                                        "43 passed"), size=12.5, line_h=19)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: plugin `__init__.py`, `test_plugin.py`, the recorded fixture, pytest on 2026-11-01 · "
           "docs/reviews/code/P3-t7.md · api 14.1 · P1 Task 7", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t7-snakemake-logger")
