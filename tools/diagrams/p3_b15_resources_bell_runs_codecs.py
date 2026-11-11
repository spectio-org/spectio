#!/usr/bin/env python3
"""Run resources and an extra config file end to end, search and the bell in the top bar, select,
delete, pin and sort runs, Blosc, LZ4 and zstd Zarr chunks, and five sweeps of open minors: batch
P3-B15 (steps FU-P3-89, -110a, -113, -115b, -110b, -108c, -110c, -116, -118, -102h, -117, -119,
-110d, -120, wave W5), 2026-11-11.

Writes docs/assets/diagrams/p3-b15-resources-bell-runs-codecs_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B15 at dafcaf26 (the 14 PRs squash-merged into
autopilot/integration between bf240d20 and 35d6a6d8, then the batch simplifier's three commits;
the P3-B14 docs and journal commits in that range are not drawn). Steps are numbered in merge
order. PR numbers are those of the squash commits' subjects (the GitHub API was not reachable from
this session, so the PR pages were not read):
- 1, FU-P3-89, PR 243: web/src/shell/SearchDialog.tsx (GET /runs?q= limit 5, GET /runs/<id>,
  GET /catalog, six pages; placeholder "Run name or ID, pipeline, page"; groups Runs, Pipelines,
  Pages; ArrowDown and ArrowUp, Enter opens); TopBar.tsx Ctrl or Cmd plus K; progress P3-M9
  (150 ms debounce, AbortSignal); record P3-fu89.md (CR-P3FU89-01 major fixed in 08a22dff);
- 2, FU-P3-110a, PR 245: spectio_server/api/extras.py (DefaultResources cpus 1 to 256, mem_mib,
  time_min 1 to 43 200; MAX_CONFIG_FILE 256 KiB; KEPT_AS; `_read` O_NOFOLLOW walk with fstat owner
  and mode; UTF-8, no NUL; Snakemake: a map without __use_yte__); spectio/locations.py
  `check_config_file` (home or the pipeline's directory, MAX_CONFIG_PARTS 32); runs_write.py
  (422 Invalid, 503 offline); migration 0013_run_extras; test message "At most 2 CPUs in Login
  node" (tests/api/test_config_file.py:160); record P3-fu110a.md (minors only);
- 3, FU-P3-113, PR 247: spectio_server/api/notifications.py (GET /me/notifications, LIMIT 50,
  succeeded, failed, cancelled, awaiting_review; POST /me/notifications:mark-read up_to, never
  back); migration 0014_notifications_read; web/src/shell/NotificationsBell.tsx (useFrames, Mark
  all as read); record P3-fu113.md (CR-P3FU113-01 major fixed in 4c6cf602, not re-reviewed);
- 4, FU-P3-115b, PR 248: web/src/runs/RunsPage.tsx (SORTS name, state, started_at, duration, and
  their minus; bulk bar "n selected", Clear selection; PinButton), DeleteRuns.tsx ("Delete n
  runs?", "Their files stay where they are.", "Also delete their run directories", 409 "Nothing
  was deleted."); record P3-fu115b.md (CR-P3FU115B-01 and UX-P3FU115B-01 to -04 majors, fixed);
- 5, FU-P3-110b, PR 250: spectio/runner/headscript.py (KEPT_AS, SHA256, `_extra_bytes`; Nextflow
  `-c extra.config,spectio.config`, Spectio's own last; Snakemake `--configfile extra.yaml
  params.json`; `--default-resources mem_mb= runtime=`; process.cpus, memory, time; the banner's
  sha256[:12]); spectio_server/sink.py `_cleared`; api/relaunch.py (Resume copies the parent's
  kept file, SHA-256 checked, else 422; GET /runs/<id>/config-file with an ETag); record
  P3-fu110b.md (CR-P3FU110B-01, CR-P3FU110B-02 majors fixed);
- 6, FU-P3-108c, PR 256: spectio/runner/sacct.py `_log_refused` (warning once per
  max_interval_s, else debug); spectio/environments.py `check_on_server` ("This run asks for
  SLURM; this server has no SLURM"); daemon threads in the engine check; record P3-fu108c.md;
- 7, FU-P3-110c, PR 257: design/ui-canvas LiteLaunch, LiteLaunchSnakemake, LiteRunDetail,
  MLiteLaunch; record P3-fu110c.md and commit 552d5839 (CR-P3FU110C-01 hint ids rs4-o and sx2-o;
  UX-P3FU110C-01 and -02 majors fixed);
- 8, FU-P3-116, PR 258: web/src/runs/DataGrid.tsx ICONS sortAscending, sortDescending,
  sortUnSort, filter, filterActive, cancel); LazyGrid.tsx (one shared lazy wrapper); SearchDialog
  SHORT_ID among NEWEST 200; record P3-fu116.md (5 minors, 2 fixed);
- 9, FU-P3-118, PR 259: web/src/environments/fields.ts plural CPUs; Edit and Duplicate links
  encodeURIComponent, test with a/b?c; tests/e2e/environments.spec.ts isLocal guard; record
  P3-fu118.md;
- 10, FU-P3-102h, PR 260: web/src/runs/imaging/codecs.ts (Blosc 1, blosclz, LZ4, zlib, zstd
  through fzstd 0.1.1, byte and bit shuffle; numcodecs 0.3.2 glue refused by the CSP), zarr.ts
  (CHUNK_READ_MAX 16 MiB; the reserve taken in the slot; blosc snappy refused at open), client.ts
  (BUDGET 2000 requests and 256 MiB per view, IN_FLIGHT 3); record P3-fu102h.md (CR-P3FU102H-01
  blocker with SEC-P3FU102H-01 major, fixed test first);
- 11, FU-P3-117, PR 261: web/src/launch/LaunchPage.tsx (a params file warning only while
  `buildParams` sends that value), FilePreview.tsx (unknown size: Download); 5 boards; record
  P3-fu117.md;
- 12, FU-P3-119, PR 264: web/src/runs/accounting.ts (ACCOUNTING_READ_MS 30 000, ACCOUNTING_READS
  10; sacct at most once a minute), RunsPage.tsx (indeterminate select-all, sortingOrder asc,
  desc, null, "pinned first, then"), runs.css (pin 25 px, phone pin 44 px); record P3-fu119.md;
- 13, FU-P3-110d, PR 263: web/src/launch/RunExtras.tsx (CPUs per task, Memory per task MiB or
  GiB, Time per task h and min; Extra config file; "Read once at Launch and kept with the run");
  web/src/runs/RunDetailExtras.tsx (View, Copy SHA-256, "Changed since the launch"); api.ts
  getConfigFile (ETag); ResumeDialog.tsx extrasWords; record P3-fu110d.md;
- 14, FU-P3-120, PR 265: spectio_server/api/environments.py (envfile.WRITE waited for in the
  request's thread, released by on_done), files/pool.py (the slot given back when no reader thread
  starts); board MLiteEnvironmentNew new; record P3-fu120.md;
- lines per step: `git show --numstat <merge> -- . ':!docs' ':!.autopilot'`, split into tests
  (paths with `test`, `tests/` or `fixtures`), boards (`design/`), lockfile and notices
  (`package.json`, `package-lock.json`, `THIRD_PARTY_NOTICES`, the wheel manifest) and the rest;
- pytest: `uv run --locked pytest -q --collect-only` at bf240d20 and at each merge that changed
  Python, run 2026-11-11 for this figure: 1,607 at bf240d20, 1,674 after step 2, 1,681 after 3,
  1,701 after 5 (deselected 30 to 32: two engine order fixtures), 1,712 after 6, 1,714 after 14
  and after the simplifier; web cases added: lines that open an `it(` or `test(` in the step's
  diff of .ts and .tsx files (vitest not run for this figure);
- the batch simplifier: 3 commits, -9 +10 (extras.py `_checked`, headscript.py
  `write_launch_files`, ResumeDialog.tsx `Ask`); pytest 1,710 passed, 4 skipped, 32 deselected
  before and after; ruff, mypy, lint-imports, `uv lock --check` pass; web: no node_modules in the
  worktree, a borrowed one lacked fzstd, so tsc and 6 imaging vitest files failed before and after.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 2000, 3230
COLS = tuple(40 + i * 490 for i in range(4))
CW = 450
R1, R2, R3, R4, LOW = 165, 925, 1645, 2235, 2705  # each row's step names; LOW the bottom band


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13) -> float:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)
    return y + 20 * len(rows)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, what: str, status: str, *,
        w: float = CW, state: str = "fixed") -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it ended."""
    h = 62
    fill = {"fixed": "done", "open": "problem", "none": "neutral"}[state]
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.5, width=1.2)
    if state == "fixed":
        s.tick(x + 14, y + 13, size=5.5)
    elif state == "open":
        s.warning(x + 14, y + 14, size=7)
    else:
        s.circle(x + 14, y + 14, 5.5)
    s.text(x + 28, y + 19, fid, size=12, anchor="start", weight="bold")
    s.text(x + w - 8, y + 19, tag, size=11.5, anchor="end",
           colour=s.t.accent if "blocker" in tag else s.t.dim)
    s.text(x + 10, y + 38, what, size=12, anchor="start")
    s.text(x + 10, y + 55, status, size=12, anchor="start", colour=s.t.dim)
    return y + h + 8


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = CW,
         warn: bool = False) -> float:
    """A dashed note: the rounds and what is open."""
    h = 12 + 19 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 22 if warn else 0
    if warn:
        s.warning(x + 16, y + 17, size=7)
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 22 + i * 19, row, size=12, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14.5, anchor="start", colour=s.t.dim)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def chip(s: Sketch, x: float, y: float, w: float, label: str, fill: str, *, h: float = 20,
         size: float = 10.5) -> None:
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.38, label, size=size)


def small(s: Sketch, x: float, y: float, text: str, *, size: float = 11, dim: bool = True,
          anchor: str = "start") -> None:
    s.text(x, y, text, size=size, anchor=anchor, colour=s.t.dim if dim else s.t.ink)


def head(s: Sketch, x: float, y: float, title: str) -> None:
    s.text(x, y, title, size=14.5, anchor="start", weight="bold")


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def field(s: Sketch, x: float, y: float, w: float, label: str, *, fill: str = "input",
          size: float = 10) -> None:
    """A labelled form input: the label above, the box below."""
    small(s, x, y, label, size=size)
    cell(s, x, y + 5, w, 16, fill)


def checkbox(s: Sketch, x: float, y: float, state: str = "off") -> None:
    cell(s, x, y, 11, 11, "done" if state == "on" else "surface")
    if state == "on":
        s.tick(x + 5.5, y + 5.5, size=3.5, width=1.6)
    elif state == "mixed":
        s.line(x + 2.5, y + 5.5, x + 8.5, y + 5.5, passes=1, amount=0.1, width=1.8)


def pushpin(s: Sketch, cx: float, cy: float, *, on: bool = True) -> None:
    s.circle(cx, cy - 3, 4.5, fill="problem" if on else "surface", width=1.1)
    s.line(cx, cy + 1, cx, cy + 9, colour=s.t.ink if on else s.t.muted, passes=1, amount=0.1, width=1.4)


def bell(s: Sketch, cx: float, cy: float, r: float = 14, *, badge: bool = True) -> None:
    """A bell, and a dot for unread items."""
    s.poly([(cx - r * 0.7, cy + r * 0.5), (cx - r * 0.55, cy - r * 0.45), (cx - r * 0.2, cy - r * 0.8),
            (cx + r * 0.2, cy - r * 0.8), (cx + r * 0.55, cy - r * 0.45), (cx + r * 0.7, cy + r * 0.5)],
           fill="gate", amount=0.3, width=1.4)
    s.line(cx - r * 0.95, cy + r * 0.5, cx + r * 0.95, cy + r * 0.5, passes=1, amount=0.2, width=1.6)
    s.circle(cx, cy + r * 0.75, r * 0.2, width=1.2)
    if badge:
        s.circle(cx + r * 0.75, cy - r * 0.7, r * 0.32, fill="problem", width=1.1)


def arrows_icon(s: Sketch, x: float, y: float, kind: str) -> None:
    """The grid's header icons, drawn as AG Grid is now given them (inline SVG)."""
    ln = dict(passes=1, amount=0.1, width=1.4)
    if kind == "up":
        s.line(x, y + 6, x, y - 6, **ln)
        s.line(x - 4, y - 2, x, y - 6, **ln)
        s.line(x + 4, y - 2, x, y - 6, **ln)
    elif kind == "down":
        s.line(x, y - 6, x, y + 6, **ln)
        s.line(x - 4, y + 2, x, y + 6, **ln)
        s.line(x + 4, y + 2, x, y + 6, **ln)
    elif kind == "unsort":
        s.line(x - 4, y - 2, x, y - 6, **ln)
        s.line(x + 4, y - 2, x, y - 6, **ln)
        s.line(x - 4, y + 2, x, y + 6, **ln)
        s.line(x + 4, y + 2, x, y + 6, **ln)
    elif kind in ("filter", "filter_on"):
        s.poly([(x - 6, y - 6), (x + 6, y - 6), (x + 1.5, y), (x + 1.5, y + 6), (x - 1.5, y + 4),
                (x - 1.5, y)], fill="input" if kind == "filter_on" else "none", amount=0.1, width=1.3)
    elif kind == "cancel":
        s.line(x - 5, y - 5, x + 5, y + 5, **ln)
        s.line(x + 5, y - 5, x - 5, y + 5, **ln)


def code(s: Sketch, x: float, y: float, w: float, rows: tuple[str, ...], fill: str) -> float:
    """A code excerpt on a fill, one monospace line per row."""
    h = 10 + 17 * len(rows)
    cell(s, x, y, w, h, fill)
    for i, row in enumerate(rows):
        s.text(x + 8, y + 19 + i * 17, f"`{row}`", size=10.5, anchor="start")
    return y + h


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1515)
    t = theme
    s.heading(50, 58, "P3-B15 · run resources and an extra config file end to end, search and the "
              "bell, select, delete, pin and sort runs, Zarr codecs",
              "wave W5 · 14 steps · 2026-11-11 · PRs 243 to 265 into `autopilot/integration` · "
              "steps numbered in merge order · then five sweeps of open minors")

    # ================================================================================================
    # row 1: FU-P3-110, run resources and an extra config file
    band(s, R1 - 38, "FU-P3-110 run resources and an extra config file, end to end: checked and read "
         "by the server, handed to the engine, drawn, then built · steps 2, 5, 7 and 13")
    top = R1 + 20
    cap = top + 270

    # 2 -- FU-P3-110a -------------------------------------------------------------------------------
    x = COLS[0]
    head(s, x, R1, "FU-P3-110a · PR 245 · server")
    s.terminal(x + 2, top + 4, 216, 116, ("POST /runs", "default_resources", "  cpus mem_mib time_min",
                                          "config_file", "  an absolute path"), size=10.5, line_h=15)
    s.arrow(x + 224, top + 60, x + 248, top + 60)
    s.folder(x + 254, top + 22, 70, 52, fill="gate", label="home")
    s.arrow(x + 328, top + 48, x + 344, top + 48)
    s.folder(x + 348, top + 22, 52, 52, fill="gate")
    s.arrow(x + 404, top + 48, x + 418, top + 48)
    s.page(x + 420, top + 22, 28, 40, fill="input", lines=2)
    small(s, x + 254, top + 92, "or the pipeline's directory, then", size=10.5)
    small(s, x + 254, top + 107, "each part `O_NOFOLLOW`, then `fstat`:", size=10.5)
    small(s, x + 254, top + 122, "this user's, not group-writable", size=10.5)
    small(s, x + 2, top + 148, "refused in words, a 422:", size=11, dim=False)
    for i, why in enumerate(("At most 2 CPUs in Login node", "a symbolic link, which is not read",
                             "larger than 256 KiB, or not UTF-8", "a Snakemake file that sets `__use_yte__`")):
        s.cross(x + 10, top + 164 + i * 21, size=5)
        small(s, x + 22, top + 168 + i * 21, why, size=10.5)
    cell(s, x + 262, top + 140, 186, 108, "done")
    small(s, x + 272, top + 158, "what the run keeps", size=11, dim=False)
    for i, key in enumerate(("path", "kept_as", "sha256", "size", "includes")):
        small(s, x + 272 + (i % 2) * 86, top + 178 + (i // 2) * 18, f"`{key}`", size=10.5)
    small(s, x + 272, top + 238, "two `runs` columns, 0013", size=10.5)
    s.step(x + CW / 2, cap, 2, "the fields and the file's checks", size=18)
    y = lines(s, x, cap + 28, ("cpus 1 to 256, memory, time up to 30 days, all optional",
                               "the file read once, at launch, in the file pool",
                               "the bytes reach the runner in step 5"))
    note(s, x, y + 6, ("no blocker, no major · 2 rounds",
                       "CR approve, SEC approve, 4 minors each",
                       "fixed test first: a home written with a trailing /",
                       "gave a 500, CR-01 with SEC-01"))

    # 5 -- FU-P3-110b -------------------------------------------------------------------------------
    x = COLS[1]
    head(s, x, R1, "FU-P3-110b · PR 250 · runner")
    s.envelope(x + 2, top + 14, 82, 54, fill="input")
    small(s, x + 43, top + 86, "the launch", size=10, anchor="middle")
    small(s, x + 43, top + 99, "command", size=10, anchor="middle")
    s.arrow(x + 90, top + 42, x + 128, top + 42)
    small(s, x + 109, top + 32, "SHA-256", size=9.5, anchor="middle")
    small(s, x + 109, top + 60, "checked", size=9.5, anchor="middle")
    s.folder(x + 134, top + 2, 196, 112, fill="gate")
    for i, (name, fill) in enumerate((("extra.config", "input"), ("spectio.config", "surface"),
                                      ("params.json", "surface"))):
        s.page(x + 146 + i * 62, top + 24, 52, 62, fill=fill, lines=2)
        small(s, x + 172 + i * 62, top + 102, f"`{name}`", size=8.5, anchor="middle", dim=False)
    s.lock(x + 318, top + 22, size=10)
    small(s, x + 340, top + 34, "`.spectio`,", size=10.5, dim=False)
    small(s, x + 340, top + 50, "yours only", size=10.5)
    s.terminal(x + 2, top + 128, 330, 74, ("-c extra.config,spectio.config",
                                            "--configfile extra.yaml params.json"),
               size=10.5, line_h=16)
    small(s, x + 342, top + 176, "Nextflow", size=10.5, dim=False)
    small(s, x + 342, top + 192, "Snakemake", size=10.5, dim=False)
    small(s, x + 2, top + 222, "the later file wins: Spectio's own on Nextflow, the form's on", size=10.5)
    small(s, x + 2, top + 238, "Snakemake · a Resume copies the parent's kept file, hash checked", size=10.5)
    s.step(x + CW / 2, cap, 5, "the engines get the values and the file", size=18)
    y = lines(s, x, cap + 28, ("the run's time and memory replace the environment's",
                               "a command done or failed: its bytes set to null",
                               "head.out's first line names them, the hash's first 12"))
    y = pin(s, x, y + 6, "CR-P3FU110B-01", "r1 major",
            "the order fixtures never ran; `-c` sat after `config`",
            "fixed: `engines` mark, `nextflow -q -c files config -flat`")
    y = pin(s, x, y, "CR-P3FU110B-02, SEC-01", "r1 major",
            "a launch failed in the lease path kept the file's bytes",
            "fixed: `_cleared(payload)` in `sink.py`, test added")
    note(s, x, y, ("2 rounds · CR approve, SEC approve",
                   "the CI step held for Thomas, Nextflow 26.10",
                   "not run here: to be validated"), warn=True)

    # 7 -- FU-P3-110c -------------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R1, "FU-P3-110c · PR 257 · boards")
    for i, name in enumerate(("LiteLaunch", "LiteLaunchSnakemake", "LiteRunDetail")):
        bx, by = x + 2 + i * 118, top + 4
        s.browser(bx, by, 108, 92)
        for r in range(3):
            cell(s, bx + 10, by + 40 + r * 15, 88 - (r % 2) * 22, 10,
                 "input" if i < 2 else ("done" if r == 0 else "surface"))
        small(s, bx + 54, by + 110, name, size=9.5, anchor="middle", dim=False)
    s.phone(x + 362, top, 64, 116)
    for r in range(3):
        cell(s, x + 376, top + 32 + r * 16, 36, 10, "input")
    small(s, x + 394, top + 132, "MLiteLaunch", size=10, anchor="middle", dim=False)
    s.page(x + 2, top + 146, 260, 100, fill="surface", lines=0)
    small(s, x + 12, top + 164, "Resources", size=10.5, dim=False)
    field(s, x + 12, top + 182, 60, "CPUs per task", size=9)
    field(s, x + 92, top + 182, 60, "Memory per task", size=9)
    field(s, x + 180, top + 182, 60, "Time per task", size=9)
    small(s, x + 12, top + 222, "Extra config file", size=10.5, dim=False)
    cell(s, x + 110, top + 211, 140, 16, "input")
    s.page(x + 276, top + 146, 172, 100, fill="problem", lines=0)
    small(s, x + 286, top + 166, "a 422 panel:", size=10.5, dim=False)
    small(s, x + 286, top + 184, "the server's words exactly,", size=10)
    small(s, x + 286, top + 200, "the client's hint below", size=10)
    small(s, x + 286, top + 222, "a 503 banner above the form", size=10)
    s.step(x + CW / 2, cap, 7, "the boards for Launch and Run detail", size=18)
    y = lines(s, x, cap + 28, ("two folding rows in Launch's Where it runs",
                               "Run detail facts: Default resources, Extra config file",
                               "design only: four boards and ui-spec 4.6"))
    y = pin(s, x, y + 6, "CR-P3FU110C-01", "r1 major",
            "the 422 panels' hints reused the heading's id",
            "fixed: their own ids, `rs4-o` and `sx2-o`")
    y = pin(s, x, y, "UX-P3FU110C-01", "ux major",
            "the time inputs had no label and no description",
            "fixed: `aria-describedby`, a hidden label per unit")
    y = pin(s, x, y, "UX-P3FU110C-02", "ux major",
            "where Changed since the launch and gone showed",
            "fixed: only in View's sheet")
    note(s, x, y, ("2 rounds · CR approve, SEC skipped",
                   "ux changes 2 major 12 minor, then approve",
                   "open: UX-07 naming, -13 to step 13, -14"))

    # 13 -- FU-P3-110d ------------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R1, "FU-P3-110d · PR 263 · web")
    s.browser(x + 2, top + 4, 250, 150, url="/launch")
    small(s, x + 12, top + 48, "Resources", size=10.5, dim=False)
    field(s, x + 12, top + 66, 64, "CPUs per task", size=8.5)
    field(s, x + 88, top + 66, 44, "Memory", size=8.5)
    chip(s, x + 134, top + 71, 30, "GiB", "neutral", h=16, size=8.5)
    field(s, x + 176, top + 66, 30, "Time", size=8.5)
    cell(s, x + 210, top + 71, 30, 16, "input")
    small(s, x + 12, top + 108, "Extra config file", size=10.5, dim=False)
    cell(s, x + 12, top + 114, 228, 16, "input")
    s.lock(x + 20, top + 142, size=6)
    small(s, x + 30, top + 146, "read once at Launch, kept 0600", size=9)
    s.arrow(x + 258, top + 70, x + 284, top + 70)
    cell(s, x + 290, top + 4, 158, 108, "surface")
    small(s, x + 298, top + 22, "Run detail", size=10.5, dim=False)
    small(s, x + 298, top + 40, "Extra config file", size=10)
    chip(s, x + 298, top + 48, 84, "View extra.config", "neutral", h=16, size=8.5)
    chip(s, x + 386, top + 48, 56, "Copy SHA-256", "neutral", h=16, size=7.5)
    s.page(x + 298, top + 72, 40, 34, fill="input", lines=2)
    small(s, x + 346, top + 86, "the ETag", size=9.5)
    small(s, x + 346, top + 100, "against `sha256`", size=9.5)
    s.warning(x + 300, top + 132, size=7)
    small(s, x + 312, top + 136, "Changed since the launch", size=10, dim=False)
    small(s, x + 300, top + 152, "in View's sheet, when they differ", size=9.5)
    cell(s, x + 2, top + 176, 446, 56, "docs")
    small(s, x + 12, top + 194, "Resume says: Same resources and the same kept config", size=10.5,
          dim=False)
    small(s, x + 12, top + 210, "file, `extra.config`, as before.", size=10.5, dim=False)
    small(s, x + 12, top + 226, "the parent's copy, checked against its SHA-256", size=9.5)
    s.step(x + CW / 2, cap, 13, "Launch, Run detail and Resume show them", size=18)
    y = lines(s, x, cap + 28, ("memory in MiB or GiB, time in h and min, checked first",
                               "four of the server's refusals get a hint, chmod go-w",
                               "the kept file read only when View opens"))
    note(s, x, y + 6, ("no blocker, no major · 1 round",
                       "CR approve 5 minors, SEC approve 3",
                       "fixed by the orchestrator: CR-01, CR-03 with SEC-02",
                       "not done: the Playwright launch smoke"))

    for i in (0, 2):  # the flow: read, then kept and run; drawn, then built
        s.arrow(COLS[i] + CW + 6, top + 60, COLS[i + 1] - 6, top + 60)

    # ================================================================================================
    # row 2: the top bar and the runs table
    band(s, R2 - 38, "the top bar and the runs table: search, the bell, then select, delete, pin and "
         "sort runs · steps 1, 3 and 4")
    top = R2 + 20
    cap = top + 270

    # 1 -- FU-P3-89 ---------------------------------------------------------------------------------
    x = COLS[0]
    head(s, x, R2, "FU-P3-89 · PR 243 · web")
    cell(s, x + 2, top + 4, 300, 30, "surface")
    s.magnifier(x + 20, top + 18, 7)
    small(s, x + 34, top + 24, "Search", size=11, dim=False)
    chip(s, x + 88, top + 10, 46, "Ctrl K", "neutral", h=18, size=9.5)
    bell(s, x + 270, top + 20, 9)
    s.arrow(x + 60, top + 38, x + 60, top + 58)
    s.page(x + 2, top + 62, 300, 176, fill="surface", lines=0)
    cell(s, x + 12, top + 74, 270, 20, "input")
    small(s, x + 18, top + 88, "Run name or ID, pipeline, page", size=10)
    for i, (group, rows) in enumerate((("Runs", 2), ("Pipelines", 1), ("Pages", 2))):
        gy = top + 112 + (0, 52, 86)[i]
        small(s, x + 14, gy, group, size=10.5, dim=False)
        for r in range(rows):
            cell(s, x + 22, gy + 6 + r * 16, 200 - r * 40, 13, "done" if i == r == 0 else "surface")
    small(s, x + 232, top + 128, "Enter", size=10, anchor="start")
    small(s, x + 232, top + 144, "opens", size=10, anchor="start")
    small(s, x + 314, top + 74, "`GET /runs?q=`", size=10, dim=False)
    small(s, x + 314, top + 88, "a name prefix, 5", size=10)
    small(s, x + 314, top + 108, "`GET /runs/<id>`", size=10, dim=False)
    small(s, x + 314, top + 122, "the exact ID", size=10)
    small(s, x + 314, top + 142, "`GET /catalog`", size=10, dim=False)
    small(s, x + 314, top + 156, "and six pages", size=10)
    small(s, x + 314, top + 180, "150 ms debounce,", size=10)
    small(s, x + 314, top + 194, "the last search's", size=10)
    small(s, x + 314, top + 208, "requests aborted", size=10)
    sc = s.phone(x + 386, top - 8, 54, 60)
    s.magnifier(sc.x + 12, sc.y + 8, 4)
    small(s, x + 413, top + 66, "360 px", size=9.5, anchor="middle")
    s.step(x + CW / 2, cap, 1, "search in the top bar", size=18)
    y = lines(s, x, cap + 28, ("Search, Ctrl or Cmd K, or the phone's icon",
                               "results are buttons; the arrow keys move between them",
                               "no new server route: what the API already serves"))
    y = pin(s, x, y + 6, "CR-P3FU89-01", "r1 major",
            "below 390 px the search icon was hidden: no search",
            "fixed test first: shown at 360 and 320 px, board too")
    note(s, x, y, ("2 rounds · CR changes, then fixed · SEC skipped",
                   "3 minors open: every rejection dropped, the",
                   "catalog fetched again per keystroke, RUN_ID"))

    # 3 -- FU-P3-113 --------------------------------------------------------------------------------
    x = COLS[1]
    head(s, x, R2, "FU-P3-113 · PR 247 · server and web")
    bell(s, x + 26, top + 26, 18)
    s.arrow(x + 50, top + 26, x + 76, top + 26)
    s.page(x + 82, top + 4, 200, 160, fill="surface", lines=0)
    small(s, x + 92, top + 24, "Notifications", size=11, dim=False)
    for i, (what, fill) in enumerate((("a run failed", "problem"), ("a run waits at a gate", "gate"),
                                      ("a run succeeded", "done"), ("a run was cancelled", "neutral"))):
        ry = top + 34 + i * 24
        cell(s, x + 92, ry, 180, 20, fill)
        small(s, x + 100, ry + 14, what, size=10)
    chip(s, x + 92, top + 134, 120, "Mark all as read", "neutral", h=18, size=9.5)
    small(s, x + 294, top + 20, "`GET`", size=10.5, dim=False)
    small(s, x + 294, top + 36, "`/me/notifications`", size=10)
    small(s, x + 294, top + 52, "newest first, 50 at most", size=10)
    small(s, x + 294, top + 76, "`POST .../mark-read`", size=10, dim=False)
    small(s, x + 294, top + 92, "`up_to` moves the mark", size=10)
    small(s, x + 294, top + 108, "forward, never back", size=10)
    s.bucket(x + 318, top + 128, 34, 30, fill="neutral")
    s.cross(x + 318, top + 142, size=8)
    small(s, x + 342, top + 140, "no table: items", size=10)
    small(s, x + 342, top + 154, "derived from runs", size=10)
    s.line(x + 2, top + 196, x + 440, top + 196, colour=t.muted, passes=1, amount=0.2)
    for i in range(7):
        s.dot(x + 20 + i * 62, top + 196, 3.5, colour=t.dim)
    small(s, x + 2, top + 220, "the event stream: each run change reads the count again,", size=10.5)
    small(s, x + 2, top + 236, "no poll · `principals.notifications_read_at`, migration 0014", size=10.5)
    s.step(x + CW / 2, cap, 3, "the bell: notifications derived from runs", size=18)
    y = lines(s, x, cap + 28, ("succeeded, failed, cancelled, or waiting at a gate",
                               "unread: newer than the one principal's mark",
                               "a modal panel, full screen on the phone"))
    y = pin(s, x, y + 6, "CR-P3FU113-01", "r1 major",
            "the phone bell kept `sp-narrow-hide`: hidden below 390 px",
            "fixed: the theme switch hides instead, test at 360 px")
    note(s, x, y, ("fix checked by the worker, not re-reviewed:",
                   "to be validated · SEC approve, 3 minors",
                   "open: a future `up_to` hides later items, SEC-01"), warn=True)

    # 4 -- FU-P3-115b (double width) ----------------------------------------------------------------
    x = COLS[2]
    wide = COLS[3] + CW - x
    head(s, x, R2, "FU-P3-115b · PR 248 · web")
    s.browser(x + 2, top + 4, 470, 200, url="/runs?sort=-duration")
    hy = top + 46
    cell(s, x + 12, hy - 12, 450, 22, "neutral")
    checkbox(s, x + 20, hy - 6, "mixed")
    for cx_, label, icon in ((44, "Run", "unsort"), (170, "State", "unsort"), (270, "Started", "unsort"),
                             (380, "Duration", "down")):
        small(s, x + cx_, hy + 4, label, size=10.5, dim=False)
        arrows_icon(s, x + cx_ + 7.2 * len(label) + 8, hy - 1, icon)
    for r, (sel, pinned) in enumerate(((True, True), (True, False), (False, False), (False, False))):
        ry = top + 64 + r * 26
        cell(s, x + 12, ry, 450, 22, "input" if sel else "surface")
        checkbox(s, x + 20, ry + 5, "on" if sel else "off")
        pushpin(s, x + 44, ry + 10, on=pinned)
        s.line(x + 58, ry + 11, x + 130 + (r % 2) * 20, ry + 11, colour=t.muted, passes=1, amount=0.2,
               width=1.6)
    cell(s, x + 12, top + 172, 450, 24, "docs")
    small(s, x + 20, top + 188, "2 selected", size=10.5, dim=False)
    chip(s, x + 96, top + 175, 56, "Delete", "problem", h=18, size=10)
    chip(s, x + 160, top + 175, 104, "Clear selection", "neutral", h=18, size=9.5)
    small(s, x + 12, top + 228, "pinned first, then the `?sort=` order: Run, State, Started,", size=10.5)
    small(s, x + 12, top + 244, "Duration, each up or down; one column at a time", size=10.5)
    s.arrow(x + 478, top + 120, x + 504, top + 120)
    sx = x + 510
    s.page(sx, top + 4, 260, 200, fill="surface", lines=0)
    s.text(sx + 12, top + 28, "Delete 2 runs?", size=12, anchor="start", weight="bold")
    small(s, sx + 12, top + 48, "Spectio forgets these runs: they leave", size=10)
    small(s, sx + 12, top + 62, "the list, the counts and Home. Their", size=10)
    small(s, sx + 12, top + 76, "files stay where they are.", size=10)
    checkbox(s, sx + 12, top + 88)
    small(s, sx + 30, top + 98, "Also delete their run directories", size=10, dim=False)
    chip(s, sx + 12, top + 112, 60, "Cancel", "neutral", h=18, size=10)
    chip(s, sx + 80, top + 112, 60, "Delete", "problem", h=18, size=10)
    cell(s, sx + 12, top + 140, 238, 54, "problem")
    small(s, sx + 20, top + 156, "a 409: Nothing was deleted.", size=10, dim=False)
    small(s, sx + 20, top + 172, "each refused run named, and why;", size=10)
    small(s, sx + 20, top + 186, "the sheet stays open", size=10)
    sc = s.phone(x + wide - 92, top + 4, 86, 150)
    for r in range(3):
        ry = sc.y + 10 + r * 30
        cell(s, sc.x + 4, ry, sc.w - 8, 26, "surface")
        checkbox(s, sc.x + 9, ry + 8, "on" if r == 0 else "off")
        s.line(sc.x + 26, ry + 13, sc.x + sc.w - 12, ry + 13, colour=t.muted, passes=1, amount=0.2)
    small(s, x + wide - 49, top + 172, "phone cards,", size=10, anchor="middle")
    small(s, x + wide - 49, top + 186, "a 44 px box", size=10, anchor="middle")
    s.step(x + wide / 2, cap, 4, "select, delete, pin and sort runs in the table", size=18)
    y = lines(s, x, cap + 28, ("a box per row and one for the page, a bulk bar · Delete asks "
                               "first, Cancel focused",
                               "the same sheet on Run detail · Pin per row · a role=status line "
                               "says what happened, no toast",
                               "the server side, `POST /runs:delete` and `PATCH /runs/<id>`, "
                               "came in step FU-P3-115a, batch P3-B14"))
    y0 = y + 6
    half = (wide - 16) / 2
    left = (("CR-P3FU115B-01", "r1 major", "a run deleted from Load more rows stayed listed",
             "fixed: `onDeleted` gets the IDs, removed first"),
            ("UX-P3FU115B-01", "ux major", "the row box took a select's full width under 768 px",
             "fixed: its own class, `sp-row-check`"),
            ("UX-P3FU115B-02", "ux major", "phone: the card's box and bulk buttons too small",
             "fixed: a 44 by 44 px label, 44 px buttons"))
    right = (("UX-P3FU115B-03", "ux major", "a column not sorted showed no sort mark",
              "fixed: `unSortIcon`, the board's chevrons"),
             ("UX-P3FU115B-04", "ux major", "Delete on Run detail: its words lost on /runs",
              "fixed: carried in history state, focused"))
    for col, items in ((x, left), (x + half + 16, right)):
        yy = y0
        for fid, tag, what, status in items:
            yy = pin(s, col, yy, fid, tag, what, status, w=half)
    note(s, x + half + 16, y0 + 140, ("2 rounds · CR changes, then approve",
                                      "SEC skipped · ux changes, 4 majors fixed",
                                      "8 ux minors left to step 12"), w=half)

    # ================================================================================================
    # row 3: imaging, and the runs table again
    band(s, R3 - 38, "FU-P3-102h imaging, step 10: Zarr chunks decoded in our worker, without "
         "unsafe-eval · the runs table again, steps 8 and 12")
    top = R3 + 20
    cap = top + 270

    # 10 -- FU-P3-102h (double width) ---------------------------------------------------------------
    x = COLS[0]
    wide = COLS[1] + CW - x
    head(s, x, R3, "FU-P3-102h · PR 260 · web")
    for i, (name, fill) in enumerate((("blosc", "input"), ("lz4", "input"), ("zstd", "input"),
                                      ("zlib", "neutral"))):
        s.page(x + 2 + i * 14, top + 10 + i * 10, 64, 70, fill=fill, lines=0)
    small(s, x + 2, top + 132, "`blosc` `lz4` `zstd` `zlib`", size=10, dim=False)
    small(s, x + 2, top + 150, "Blosc 1: blosclz, LZ4,", size=10)
    small(s, x + 2, top + 164, "zlib, zstd inside, byte", size=10)
    small(s, x + 2, top + 178, "and bit shuffle", size=10)
    small(s, x + 2, top + 196, "zstd: fzstd 0.1.1", size=10)
    s.arrow(x + 120, top + 50, x + 168, top + 50)
    cell(s, x + 174, top + 14, 128, 74, "work")
    s.cog(x + 192, top + 32, 9, fill="surface")
    small(s, x + 212, top + 38, "our decoder", size=10.5, dim=False)
    small(s, x + 212, top + 54, "worker,", size=10.5, dim=False)
    small(s, x + 184, top + 78, "in JavaScript", size=10)
    s.arrow(x + 306, top + 50, x + 350, top + 50)
    cell(s, x + 356, top + 14, 84, 74, "neutral")
    for cx_, cy_, r_, fill in ((0.3, 0.4, 0.18, "bar_blue"), (0.62, 0.55, 0.22, "bar_green")):
        s.circle(x + 356 + 84 * cx_, top + 14 + 74 * cy_, 74 * r_, fill=fill, width=1.0)
    small(s, x + 174, top + 110, "numcodecs 0.3.2 runs its glue through", size=10)
    small(s, x + 174, top + 124, "`Function`, which the CSP refuses:", size=10)
    s.cross(x + 360, top + 120, size=6)
    small(s, x + 174, top + 144, "each output held to the level's decoded", size=10)
    small(s, x + 174, top + 158, "size, read from the header first", size=10)
    small(s, x + 174, top + 178, "blosc with snappy: refused at open", size=10, dim=False)
    # the byte budget, to scale
    bx, k = x + 470, 1.6  # 1.6 px a MiB
    small(s, bx, top + 8, "one view's budget, to scale: 256 MiB, 1.6 px a MiB", size=11, dim=False)
    small(s, bx, top + 26, "a chunk reserves up to 16 MiB; 3 reads in flight", size=10)
    small(s, bx, top + 50, "before: reserved, then the wait for a slot", size=10.5)
    for i in range(16):
        bar(s, bx + i * 16 * k, top + 58, 16 * k, 18, "problem" if i >= 3 else "work")
    bar(s, bx + 256 * k + 6, top + 58, 16 * k, 18, "neutral")
    s.cross(bx + 256 * k + 6 + 8 * k, top + 67, size=7)
    small(s, bx + 256 * k + 6, top + 92, "17th get:", size=9.5)
    small(s, bx + 256 * k + 6, top + 104, "Stopped", size=9.5)
    small(s, bx, top + 92, "16 reserves of 16 MiB fill it, 13 of them only queued", size=10)
    small(s, bx, top + 128, "after: reserved inside the slot", size=10.5)
    for i in range(3):
        bar(s, bx + i * 16 * k, top + 136, 16 * k, 18, "work")
    bar(s, bx + 48 * k, top + 136, 208 * k, 18, "done")
    small(s, bx, top + 170, "at most 3 times 16 MiB held, the rest free; unused", size=10)
    small(s, bx, top + 184, "reserve given back; 2000 requests a view", size=10)
    small(s, bx, top + 214, "a body past a cut reserve: `Stopped(bytes)`;", size=10)
    small(s, bx, top + 228, "past 16 MiB: `TooLarge`", size=10)
    s.step(x + wide / 2, cap, 10, "Blosc, LZ4 and zstd chunks in the OME-Zarr viewer", size=18)
    y = lines(s, x, cap + 28, ("decoded off the main thread, in the existing worker pool · the "
                               "CSP unchanged, no unsafe-eval",
                               "a chunk that lies about its size, or decodes past it: "
                               "`NotDecoded`, a crafted-case suite",
                               "one new runtime package, fzstd 0.1.1, in the notices"))
    y = pin(s, x, y + 6, "CR-P3FU102H-01, SEC-P3FU102H-01", "r1 blocker and major",
            "the 16 MiB reserve was taken before the wait for one of 3 slots: a multi-channel "
            "first paint stopped",
            "fixed test first: reserved in the slot, 40 concurrent gets succeed, a 2 MiB chunk "
            "with 1 MiB left stops", w=wide)
    note(s, x, y, ("2 rounds · CR changes, SEC changes, fixed and checked",
                   "fixed too: blosc snappy refused at open, CR-02 · open: fzstd can loop on a "
                   "crafted table, bounded by the worker's 10 s timeout, CR-03"),
         w=wide)

    # 8 -- FU-P3-116 --------------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R3, "FU-P3-116 · PR 258 · web")
    small(s, x + 2, top + 12, "before: an icon not given", size=10.5)
    cell(s, x + 2, top + 22, 210, 30, "neutral")
    small(s, x + 12, top + 42, "State", size=10.5, dim=False)
    s.poly([(x + 60, top + 30), (x + 74, top + 30), (x + 74, top + 44), (x + 60, top + 44)],
           fill="#1e1e1e" if t.name == "light" else "#e3e3e3", amount=0.1, width=1)
    small(s, x + 84, top + 42, "a solid square", size=10)
    small(s, x + 232, top + 12, "after: six icons, inline SVG", size=10.5, dim=False)
    for i, (kind, label) in enumerate((("up", "up"), ("down", "down"), ("unsort", "none"),
                                       ("filter", "filter"), ("filter_on", "on"), ("cancel", "clear"))):
        cx_ = x + 246 + i * 34
        cell(s, cx_ - 14, top + 22, 28, 30, "surface")
        arrows_icon(s, cx_, top + 37, kind)
        small(s, cx_, top + 68, label, size=9, anchor="middle")
    small(s, x + 2, top + 98, "the CSP's `img-src 'self'` refuses AG Grid's `data:` icons,", size=10.5)
    small(s, x + 2, top + 114, "so each icon a grid shows is given as SVG", size=10.5)
    cell(s, x + 2, top + 134, 150, 20, "input")
    small(s, x + 10, top + 148, "6 characters", size=10.5, dim=False)
    s.arrow(x + 158, top + 144, x + 186, top + 144)
    small(s, x + 192, top + 140, "a 6-character short ID is looked", size=10.5)
    small(s, x + 192, top + 156, "for among the 200 newest runs", size=10.5)
    small(s, x + 2, top + 186, "the grid's lazy chunk: one wrapper for every mount,", size=10.5)
    small(s, x + 2, top + 202, "Retry replaces it · pin keeps focus on its row's button", size=10.5)
    small(s, x + 2, top + 218, "Mark all as read moves focus to the panel's heading", size=10.5)
    small(s, x + 2, top + 234, "Delete words in the singular for one run", size=10.5)
    s.step(x + CW / 2, cap, 8, "sort icons and the login1 retest g minors", size=18)
    y = lines(s, x, cap + 28, ("square icons in every runs table, now drawn",
                               "search, bell, Delete, pin, file preview touched",
                               "older runs by short ID need a server-side search"))
    note(s, x, y + 6, ("no blocker, no major · 1 round",
                       "CR approve, 5 minors: 2 fixed, 3 open",
                       "SEC skipped: no sensitive path"))

    # 12 -- FU-P3-119 -------------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R3, "FU-P3-119 · PR 264 · web")
    small(s, x + 2, top + 12, "an ended SLURM run, to scale, 1.2 px a second", size=10.5, dim=False)
    k = 1.2
    tx = x + 20
    s.line(tx, top + 52, tx + 360 * k, top + 52, colour=t.muted, passes=1, amount=0.2, width=1.6)
    for i in range(1, 11):
        s.dot(tx + i * 30 * k, top + 52, 4, colour=t.ink)
    for i in range(0, 7):
        s.line(tx + i * 60 * k, top + 62, tx + i * 60 * k, top + 72, colour=t.dim, passes=1, amount=0.1)
    small(s, tx - 8, top + 40, "ended", size=9.5)
    small(s, tx + 30 * k - 10, top + 40, "re-read every 30 s, at most 10", size=9.5)
    small(s, tx, top + 88, "sacct called at most once a minute", size=9.5)
    small(s, tx + 300 * k, top + 88, "5 min", size=9.5, anchor="middle")
    cell(s, x + 2, top + 104, 214, 52, "surface")
    small(s, x + 10, top + 122, "Measured", size=10.5, dim=False)
    bar(s, x + 80, top + 112, 60, 12, "done")
    bar(s, x + 140, top + 112, 66, 12, "neutral")
    small(s, x + 10, top + 146, "fills in as jobs are measured", size=9.5)
    checkbox(s, x + 234, top + 108, "mixed")
    small(s, x + 252, top + 118, "the page's box: mixed", size=10)
    pushpin(s, x + 240, top + 140)
    small(s, x + 252, top + 144, "pin: a 25 px target", size=10)
    s.phone(x + 402, top + 96, 44, 70)
    small(s, x + 252, top + 162, "phone cards: a 44 px pin", size=10)
    small(s, x + 2, top + 190, "a third press on a header clears `?sort=` · the footer says", size=10.5)
    small(s, x + 2, top + 206, "pinned first, then · the status line clears on the next", size=10.5)
    small(s, x + 2, top + 222, "action · a 409 tied to the directories box", size=10.5)
    s.step(x + CW / 2, cap, 12, "table minors, and Measured after sacct", size=18)
    y = lines(s, x, cap + 28, ("no stream frame says sacct answered: the page reads",
                               "again while a job has no measure yet",
                               "closes UX-P3FU115B-05 to -12 of step 4"))
    note(s, x, y + 6, ("no blocker, no major · 1 round · CR approve",
                       "2 minors open: a resumed run re-reads 10 times",
                       "on every visit, CR-01; one failed re-read ends",
                       "the loop, CR-02 · SEC skipped"), warn=True)

    # ================================================================================================
    # row 4: the sweeps of open minors
    band(s, R4 - 38, "open minors closed before 0.0.1: environments and sacct, Environments screens, "
         "Launch and run detail, server, tests and boards · steps 6, 9, 11 and 14")
    top = R4 + 20
    cap = top + 252

    # 6 -- FU-P3-108c -------------------------------------------------------------------------------
    x = COLS[0]
    head(s, x, R4, "FU-P3-108c · PR 256 · server")
    s.terminal(x + 2, top + 4, 446, 90, ("WARNING sacct not called for n IDs: why",
                                          "DEBUG   sacct not called for n IDs: why",
                                          "DEBUG   sacct not called for n IDs: why"),
               size=10.5, line_h=16)
    small(s, x + 2, top + 114, "the same refusal: at warning once per interval, then at debug", size=10.5)
    s.hpc_node(x + 6, top + 128, 40, 52, busy=2)
    s.cross(x + 64, top + 154, size=8)
    small(s, x + 82, top + 146, "This run asks for SLURM; this server", size=10.5, dim=False)
    small(s, x + 82, top + 162, "has no SLURM: the runner checks again", size=10.5)
    small(s, x + 2, top + 214, "engine checks on daemon threads: a slow one no longer holds", size=10.5)
    small(s, x + 2, top + 230, "a SIGTERM'd `spectio serve`", size=10.5)
    s.step(x + CW / 2, cap, 6, "environments file and sacct sweep minors", size=17)
    y = lines(s, x, cap + 28, ("a run whose file cannot be read: the default, said",
                               "an unknown key in the file is not echoed back"))
    note(s, x, y + 6, ("no blocker, no major · 1 round · CR approve",
                       "3 minors: 1 fixed, 2 accepted · SEC skipped"))

    # 9 -- FU-P3-118 --------------------------------------------------------------------------------
    x = COLS[1]
    head(s, x, R4, "FU-P3-118 · PR 259 · web")
    s.browser(x + 2, top + 4, 230, 110, url="/environments")
    for i, words in enumerate(("1 CPU", "2 CPUs")):
        ry = top + 40 + i * 34
        cell(s, x + 12, ry, 210, 28, "surface")
        s.line(x + 20, ry + 14, x + 70, ry + 14, colour=s.t.muted, passes=1, amount=0.2, width=1.6)
        small(s, x + 90, ry + 18, words, size=10.5, dim=False)
        chip(s, x + 168, ry + 6, 46, "Edit", "neutral", h=16, size=9.5)
    small(s, x + 246, top + 26, "one CPU, two CPUs:", size=10.5, dim=False)
    small(s, x + 246, top + 42, "`plural` in the summary", size=10.5)
    small(s, x + 246, top + 70, "Edit and Duplicate links:", size=10.5, dim=False)
    chip(s, x + 246, top + 80, 50, "a/b?c", "problem", h=18, size=10)
    s.arrow(x + 302, top + 89, x + 324, top + 89)
    chip(s, x + 330, top + 80, 92, "a%2Fb%3Fc", "done", h=18, size=10)
    s.terminal(x + 2, top + 138, 58, 38)
    small(s, x + 70, top + 152, "the e2e spec skips a server not on loopback,", size=10.5)
    small(s, x + 70, top + 168, "and puts the default back afterwards", size=10.5)
    small(s, x + 2, top + 214, "a test title fixed, a JSX block re-indented, `NAMES`", size=10.5)
    small(s, x + 2, top + 230, "replaced by `engineName`", size=10.5)
    s.step(x + CW / 2, cap, 9, "Environments screen minors", size=17)
    y = lines(s, x, cap + 28, ("closes DW-P3B11-02, CR-P3FU86G-05 and -06,",
                               "CR-P3FU86H-03, SEC-P3FU86F-01 and -02"))
    note(s, x, y + 6, ("no blocker, no major · 1 round · CR approve",
                       "open: desktop and phone can race on the default"))

    # 11 -- FU-P3-117 -------------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R4, "FU-P3-117 · PR 261 · web")
    s.page(x + 2, top + 4, 52, 62, fill="input", lines=3)
    small(s, x + 28, top + 82, "params file", size=9.5, anchor="middle")
    s.arrow(x + 60, top + 34, x + 88, top + 34)
    cell(s, x + 94, top + 10, 354, 48, "gate")
    s.warning(x + 108, top + 26, size=7)
    small(s, x + 120, top + 30, "Warning, not a blocker: the file sets a key", size=10.5, dim=False)
    small(s, x + 104, top + 50, "shown only while Launch sends that value as read", size=10)
    s.page(x + 2, top + 100, 52, 62, fill="neutral", lines=0)
    small(s, x + 28, top + 138, "?", size=20, anchor="middle", dim=False)
    small(s, x + 28, top + 180, "an HTML report", size=9.5, anchor="middle")
    s.arrow(x + 60, top + 130, x + 88, top + 130)
    cell(s, x + 94, top + 106, 354, 48, "surface")
    small(s, x + 104, top + 124, "Spectio cannot tell this file's size, so the report", size=10,
          dim=False)
    small(s, x + 104, top + 140, "viewer does not open it. Download it to open it.", size=10,
          dim=False)
    small(s, x + 94, top + 176, "fail closed: an unknown size counts as large", size=10.5)
    small(s, x + 94, top + 196, "5 run detail boards and ui-spec 4.4.1, 4.7.1, 5.2", size=10.5)
    s.step(x + CW / 2, cap, 11, "catalog picker and run detail minors", size=17)
    y = lines(s, x, cap + 28, ("eight open findings of FU-P3-87e and -88a closed",
                               "the profile warning names the profile selected"))
    note(s, x, y + 6, ("no blocker, no major · 1 round · CR approve",
                       "3 minors open · SEC skipped"))

    # 14 -- FU-P3-120 -------------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R4, "FU-P3-120 · PR 265 · server, tests, boards")
    s.page(x + 2, top + 4, 60, 72, fill="input", lines=3)
    s.lock(x + 52, top + 66, size=10)
    small(s, x + 32, top + 94, "the file's", size=9.5, anchor="middle")
    small(s, x + 32, top + 106, "write lock", size=9.5, anchor="middle")
    small(s, x + 78, top + 20, "waited for in the request's thread,", size=10.5, dim=False)
    small(s, x + 78, top + 36, "never in a pool worker; released by", size=10.5)
    small(s, x + 78, top + 52, "the pool's `on_done` when the write ends", size=10.5)
    small(s, x + 78, top + 76, "no reader thread started: the slot", size=10.5, dim=False)
    small(s, x + 78, top + 92, "and the lock given back, CR-01", size=10.5)
    sc = s.phone(x + 2, top + 122, 50, 86)
    for r in range(3):
        cell(s, sc.x + 3, sc.y + 6 + r * 14, sc.w - 6, 10, "input")
    small(s, x + 66, top + 140, "`MLiteEnvironmentNew`, a new board,", size=10.5, dim=False)
    small(s, x + 66, top + 156, "5 boards fixed; Duplicate waits in", size=10.5)
    small(s, x + 66, top + 172, "the refused panel, ui-spec 4.8.1", size=10.5)
    small(s, x + 66, top + 196, "e2e: the phone by keyboard, a SLURM server's Tab order", size=10.5)
    s.step(x + CW / 2, cap, 14, "server, tests and boards minors", size=17)
    y = lines(s, x, cap + 28, ("a failed thread start no longer leaves writes",
                               "answering 503 until a restart"))
    note(s, x, y + 6, ("no blocker, no major · 1 round",
                       "CR approve 3 minors, SEC approve 2 · CR-01 fixed"))

    # ================================================================================================
    # the batch simplifier, the lines and the tests
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: not needed")
    y0 = LOW + 8

    x = 50
    s.text(x, y0 + 12, "`code-simplifier`: 3 commits, -9 +10", size=14, anchor="start", weight="bold")
    small(s, x, y0 + 36, "before, `35d6a6d8`", size=12)
    small(s, x + 300, y0 + 36, "after, `dafcaf26`", size=12)
    pairs = (("`extras.py`", ("_checked(fd, what, uid, owners)", "  -> os.stat_result"),
              ("_checked(fd, what, owners)", "  -> None")),
             ("`headscript.py`", ("if spec.config_file is not None", "    and kept is not None:",
                                  "  write_file(fd,", "    spec.config_file.kept_as, kept)"),
              ("if kept is not None:", "  write_file(fd, *kept)")),
             ("`ResumeDialog.tsx`", ("extrasWords(run), called twice",),
              ("const extras = extrasWords(run)",)))
    yy = y0 + 46
    for name, before, after in pairs:
        end_b = code(s, x, yy, 270, before, "problem")
        code(s, x + 300, yy, 270, after, "done")
        s.arrow(x + 274, yy + 16, x + 296, yy + 16)
        small(s, x + 580, yy + 18, name, size=10.5, dim=False)
        yy = end_b + 10
    small(s, x, yy + 12, "an unused `uid`, an unread return, a guard kept for type", size=11)
    small(s, x, yy + 28, "narrowing, a call made twice: same errors, same order", size=11)

    # lines per step, to scale
    x = 720
    k = 0.25
    s.text(x, y0 + 12, f"lines per step outside docs, to scale, {k} px a line", size=14,
           anchor="start", weight="bold")
    sizes = ((1, "89", 252, 131, 1, 0, 6), (2, "110a", 661, 502, 0, 2, 9),
             (3, "113", 562, 254, 0, 2, 18), (4, "115b", 486, 312, 36, 0, 58),
             (5, "110b", 342, 343, 0, 0, 77), (6, "108c", 59, 143, 0, 0, 12),
             (7, "110c", 0, 0, 358, 0, 1), (8, "116", 174, 97, 0, 0, 68),
             (9, "118", 22, 53, 0, 0, 30), (10, "102h", 292, 575, 0, 34, 46),
             (11, "117", 9, 74, 9, 0, 20), (12, "119", 94, 166, 43, 0, 58),
             (13, "110d", 858, 557, 0, 0, 19), (14, "120", 21, 117, 104, 0, 28))
    mid = x + 110
    for i, (n, name, code_, tests, boards, lock, rem) in enumerate(sizes):
        ry = y0 + 28 + i * 19
        s.text(mid - 26, ry + 11, f"{n} · {name}", size=11, anchor="end", colour=t.dim)
        bar(s, mid - 2 - rem * k, ry, rem * k, 13, "problem")
        ox = mid + 2
        for n_, fill in ((code_, "done"), (tests, "input"), (boards, "docs"), (lock, "neutral")):
            if n_:
                bar(s, ox, ry, n_ * k, 13, fill)
                ox += n_ * k
        s.text(ox + 6, ry + 11, f"+{code_ + tests + boards + lock} -{rem}", size=10.5, anchor="start")
    s.line(mid, y0 + 22, mid, y0 + 296, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y0 + 314, "removed", size=11, anchor="end", colour=t.dim)
    for lx, fill, label in ((mid + 8, "done", "code, schema, CSS"), (mid + 150, "input", "tests"),
                            (mid + 218, "docs", "boards"), (mid + 296, "neutral", "lockfile, notices")):
        bar(s, lx, y0 + 304, 18, 12, fill)
        s.text(lx + 24, y0 + 314, label, size=11, anchor="start", colour=t.dim)

    # the tests, to scale
    x = 1330
    k = 0.22
    s.text(x, y0 + 12, f"pytest cases collected, to scale, {k} px a case", size=14,
           anchor="start", weight="bold")
    runs_t = (("before step 1, `bf240d20`", 1607, "bar_grey"), ("head `35d6a6d8`", 1714, "bar_green"),
              ("after simplify", 1714, "bar_green"))
    for i, (label, n, fill) in enumerate(runs_t):
        by = y0 + 28 + i * 24
        s.text(x, by + 13, label, size=11, anchor="start")
        bar(s, x + 160, by, n * k, 16, fill)
        s.text(x + 166 + n * k, by + 13, f"{n:,}", size=11, anchor="start")
    small(s, x, y0 + 118, "added per step, 2 px a case", size=12, dim=False)
    small(s, x + 160, y0 + 138, "pytest", size=11)
    small(s, x + 330, y0 + 138, "web, from the diff", size=11)
    py = {2: 67, 3: 7, 5: 20, 6: 11, 14: 2}
    web = {1: 9, 3: 8, 4: 16, 8: 6, 9: 5, 10: 11, 11: 4, 12: 9, 13: 28, 14: 2}
    names = {n: name for n, name, *_ in sizes}
    for i, n in enumerate(sorted(set(py) | set(web))):
        by = y0 + 148 + i * 15
        s.text(x + 150, by + 10, f"{n} · {names[n]}", size=10.5, anchor="end", colour=t.dim)
        if n in py:
            bar(s, x + 160, by, py[n] * 2, 11, "input")
            s.text(x + 166 + py[n] * 2, by + 10, f"+{py[n]}", size=10.5, anchor="start")
        if n in web:
            bar(s, x + 330, by, web[n] * 2, 11, "docs")
            s.text(x + 336 + web[n] * 2, by + 10, f"+{web[n]}", size=10.5, anchor="start")
    s.tick(x + 8, y0 + 374, size=6)
    small(s, x + 24, y0 + 380, "simplifier gate: 1,710 passed, 4 skipped, 32 deselected,", size=11,
          dim=False)
    small(s, x + 24, y0 + 396, "before and after; ruff, mypy, lint-imports, `uv lock --check`", size=11)
    s.warning(x + 8, y0 + 418, size=7)
    small(s, x + 24, y0 + 422, "web: a borrowed `node_modules` lacked fzstd, so tsc and", size=11,
          dim=False)
    small(s, x + 24, y0 + 438, "6 imaging vitest files failed before and after; 52 pass", size=11)

    s.text(50, H - 52, "pins: every blocker and major of the batch, all fixed · r1: the first code "
           "review round · ux: the ux-reviewer pass · step 7 has no product code",
           size=13.5, anchor="start", colour=t.dim)
    s.prefix_key(50, H - 28, ("CR", "SEC", "UX"))
    s.text(W - 50, H - 12, "source: spectio_server api extras.py, notifications.py, relaunch.py, sink.py · "
           "spectio runner headscript.py, sacct.py · web launch, runs, shell, imaging · review "
           "records P3-fu89 to P3-fu120", size=12, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b15-resources-bell-runs-codecs")
