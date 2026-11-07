#!/usr/bin/env python3
"""One wheel, runs from a terminal, release packages: batch P3-B03 (P1 Tasks 21, 25 and 26),
step P3, 2026-11-07.

Writes docs/assets/diagrams/p3-b03-wheel-terminal-release_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B03 at f69437e (PRs 141, 142, 147 and 148 merged into
autopilot/integration between f2b3d23 and d7c69a1, plus the batch code-simplifier's commit):
- Task 21: packages/spectio/hatch_build.py `BridgesHook` (engine-bridges/nf-spectio/build.sh
  builds the unpacked plugin, the Snakemake logger module is copied; the sdist carries them in
  src/spectio/_bridges, the wheel in spectio/_bridges; an sdist without them fails);
  packages/spectio-server/hatch_build.py `WebHook` (web/dist as spectio_server/web);
  tests/packaging/test_wheel.sh: `uv build --all-packages`, every listing compared with
  tests/packaging/contents/, `uv tool install` of spectio without [server], `spectio --version`
  = `spectio 0.0.1`, the runner finds both bridges in its own package, MAX_MB=80, then the three
  wheels in one venv and the server reads its packaged screens; spectio_server/static.py
  `find_dist` and `_owned` (the checkout only from the workspace, owned, no group or other
  write; a warning naming `chmod g-w,o-w`); 20 MB from docs/reviews/code/P3-t21.md;
- Task 25: snakemake_logger_plugin_spectio/__init__.py (no SPECTIO_* variable: `terminal_spool`
  in the launch directory, `<run ID>-<producer>-<nnnn>.jsonl`, pointer
  ~/.spectio/observed/<run ID>.json 0600, temporary name then rename, only when ~/.spectio
  exists); runner/observed.py `ObservedRun` (strict, MAX_POINTER_BYTES 4096, the runs root
  wins), `scan_observed`, `end_pointer` to observed/ended/; runner/loop.py `_observe` (when the
  mtime changed), `_fs` (one job per key, files_timeout_s 5.0), `_watch_terminal` (only when
  `checkable`, then `same_process`; nothing is signalled); runner/local.py `checkable(host,
  boot_id)`; files/pool.py WORKERS 4, READ_TIMEOUT_S 5.0; projector/snakemake.py `spool_end`;
  rebuild.py reads observed then ended; web/src/runs/RunHeader.tsx "Not checked (on <node>,
  started from a terminal)"; origin `cli-observed`;
- Task 26: engine-bridges/nf-spectio/build.gradle (`io.nextflow.nextflow-plugin` 1.0.0-beta.16,
  version 0.0.1, provider 'spectio'), gradle-wrapper.properties (gradle-8.14.3,
  distributionSha256Sum), gradle/verification-metadata.xml (145 components), build.sh REQUIRES
  '>=25.04.0'; tests/packaging/test_bridges_release.sh (environment guard, fresh
  GRADLE_USER_HOME, manifest lines, Nextflow loads the zip for the synthetic `happy`, `uv build`,
  `twine check --strict`, `--require-hashes -r dev/snakemake.lock.txt`, `--logger spectio`,
  `RESULT bridges-release dry-run pass`);
- findings: docs/reviews/code/P3-t21.md, P3-t25.md, P3-t26.md (every blocker and major);
- test counts, from the same records and the simplifier's report: spectio-server 594 passed at
  21005f3; test_observed.py and test_read.py 75 passed, Nextflow bridge 26 passed and 1 skipped,
  at d5e2193; the Snakemake logger's suite 53 passed at 6e9d080; the whole suite 939 passed,
  28 deselected, before and after f69437e (5 files, +11 -24).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 2030
COL5 = (50, 355, 660, 965, 1270)  # five columns, 280 wide
CW5 = 280
COL4 = (50, 440, 830, 1220)  # four columns, 330 wide
CW4 = 330

TOP1, CAP1, PIN1 = 165, 395, 512  # Task 21
TOP2, CAP2, PIN2 = 780, 1010, 1127  # Task 25
TOP3, CAP3, PIN3 = 1292, 1505, 1600  # Task 26
LOW = 1750  # tests and the simplifier


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, severity: str, rows: tuple[str, ...],
        status: str, *, fixed: bool, w: float = 276) -> None:
    """A finding pinned where it hits: its ID and severity, what it was, what became of it."""
    h = 34 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
           fill="done" if fixed else "problem", amount=0.5, width=1.2)
    if fixed:
        s.tick(x + 16, y + 13, size=6)
    else:
        s.warning(x + 16, y + 14, size=8)
    s.text(x + 32, y + 18, fid, size=13, anchor="start", weight="bold")
    s.text(x + w - 10, y + 18, severity, size=12.5, anchor="end", colour=s.t.dim)
    for i, row in enumerate(rows):
        s.text(x + 12, y + 40 + i * 19, row, size=12.5, anchor="start")
    s.text(x + 12, y + 40 + len(rows) * 19, status, size=12.5, anchor="start", colour=s.t.dim)


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14, anchor="start", colour=s.t.dim)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=303)
    t = theme
    s.heading(50, 58, "P3-B03 · one wheel, runs from a terminal, release packages, P1 Tasks 21, 25, 26",
              "milestones M4 and M6 · architecture 7.3 and 13.8 · dev-env 12 and 15.3 · "
              "PRs 141, 142, 147 and 148 into `autopilot/integration`")

    # == Task 21: one wheel with the UI and both bridges ======================================
    band(s, 140, "Task 21, PRs 141 and 142 · one wheel carries both engine bridges, "
         "the server's wheel carries the screens · no Node, no Nextflow at install")

    # 1 the sources
    x = COL5[0]
    s.folder(x, TOP1, 134, 84, fill="input", label="`engine-bridges`")
    s.folder(x + 146, TOP1, 134, 84, fill="input", label="`web/dist`")
    s.text(x, TOP1 + 116, "`build.sh`: nf-spectio, unpacked", size=12.5, anchor="start")
    s.text(x, TOP1 + 138, "the Snakemake logger, as it is", size=12.5, anchor="start", colour=t.dim)
    s.text(x, TOP1 + 166, "`npm ci`, `vite build`: the screens", size=12.5, anchor="start")
    s.step(x + CW5 / 2, CAP1, 1, "the sources")
    lines(s, x, CAP1 + 30, ("`build.sh` needs Java and Nextflow,",
                            "the screens need Node:",
                            "only to make the sdists"))

    # 2 two build hooks
    x = COL5[1]
    for i, name in enumerate(("`BridgesHook`", "`WebHook`")):
        px = x + 14 + i * 140
        s.page(px, TOP1, 74, 92, fill="surface", lines=3)
        s.cog(px + 70, TOP1 + 82, 11, fill="work")
        s.text(px + 37, TOP1 + 124, name, size=12.5)
    s.text(x + 140, TOP1 + 160, "`hatch_build.py` · `hatchling==1.32.4`", size=12)
    s.step(x + CW5 / 2, CAP1, 2, "two build hooks")
    lines(s, x, CAP1 + 30, ("spectio: `spectio/_bridges/`",
                            "server: `spectio_server/web/`",
                            "`uv build --all-packages`",
                            "an sdist without them fails"))

    # 3 sdist, then the wheel
    x = COL5[2]
    s.page(x + 14, TOP1 + 4, 70, 88, fill="neutral", lines=3)
    s.text(x + 49, TOP1 + 116, "sdist", size=13.5)
    s.arrow(x + 96, TOP1 + 48, x + 170, TOP1 + 48)
    s.page(x + 184, TOP1 + 4, 70, 88, fill="done", lines=3)
    s.text(x + 219, TOP1 + 116, "wheel", size=13.5)
    s.text(x + 140, TOP1 + 146, "only `src` and `hatch_build.py`", size=12.5, colour=t.dim)
    s.text(x + 140, TOP1 + 168, "listings in `tests/packaging/contents/`", size=12, colour=t.dim)
    s.step(x + CW5 / 2, CAP1, 3, "sdist, then the wheel")
    lines(s, x, CAP1 + 30, ("every wheel is built from its sdist",
                            "every listing compared:",
                            "nothing more, nothing less"))

    # 4 spectio alone, to scale
    x = COL5[3]
    s.terminal(x, TOP1, 276, 76, ("$ spectio --version", "spectio 0.0.1"), size=12.5)
    bx, by, mb = x + 4, TOP1 + 116, 3.2  # 3.2 px per MB
    s.shade(bx, by, 80 * mb, 22, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    bar(s, bx, by, 20 * mb, 22, "bar_green")
    s.text(bx + 20 * mb + 8, by + 16, "20 MB", size=13, anchor="start")
    s.text(bx + 80 * mb, by + 44, "limit 80 MB", size=12.5, anchor="end", colour=t.dim)
    s.text(bx, by + 44, "the install, to scale", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW5 / 2, CAP1, 4, "spectio alone")
    lines(s, x, CAP1 + 30, ("`uv tool install`, without server",
                            "the runner finds both bridges",
                            "in its own package, not the checkout",
                            "`RESULT wheel pass`"))

    # 5 the server's screens
    x = COL5[4]
    s.browser(x, TOP1, 276, 92, url="the screens")
    s.tick(x + 22, TOP1 + 52, size=7)
    s.text(x + 40, TOP1 + 57, "the packaged copy first", size=13, anchor="start")
    s.text(x + 40, TOP1 + 78, "`spectio_server/web/`", size=12, anchor="start", colour=t.dim)
    s.folder(x + 6, TOP1 + 112, 70, 50, fill="input")
    s.lock(x + 66, TOP1 + 158, size=11)
    s.text(x + 92, TOP1 + 128, "else a checkout's `web/dist`:", size=12.5, anchor="start")
    s.text(x + 92, TOP1 + 148, "the workspace, yours,", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 92, TOP1 + 168, "no group or other write", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW5 / 2, CAP1, 5, "the server's screens")
    lines(s, x, CAP1 + 30, ("`find_dist`, once at import",
                            "a refused checkout: one warning",
                            "naming `chmod g-w,o-w`",
                            "else the not-built page"))

    for a, b in zip(COL5[:4], COL5[1:]):
        s.arrow(a + CW5 - 4, TOP1 + 40, b - 6, TOP1 + 40)

    pin(s, COL5[1], PIN1, "CR-P3T21-01 r3", "blocker",
        ("`uv build` stopped in the sdist hook:",
         "the logger of Task 7 was on PR 122"), "resolved: PR 122 merged", fixed=True)
    pin(s, COL5[2], PIN1, "SEC-P3T21-01 r1", "major",
        ("an sdist took untracked files, such",
         "as `.env.local`, plus `tests/`"), "fixed in eed532a, `only-include`", fixed=True)
    pin(s, COL5[4], PIN1, "SEC-P3T21-02 r2", "major",
        ("no screens: `/tmp/web/dist`, which any",
         "user can create, was served"), "fixed in 11fef49, `find_dist`", fixed=True)
    pin(s, COL5[4], PIN1 + 100, "CR-P3T21-02 r3", "major",
        ("a group-writable checkout showed not",
         "built, with no reason given"), "fixed in 21005f3, the warning", fixed=True)

    # == Task 25: runs started from a terminal ================================================
    band(s, 750, "Task 25, PR 147 · a run started by hand shows up, read from its spool · "
         "its head is checked only on its own host and boot")

    # 6 started from a terminal
    x = COL5[0]
    s.terminal(x, TOP2, 276, 76, ("$ snakemake --logger spectio",), size=12.5)
    s.cross(x + 18, TOP2 + 104, size=7)
    s.text(x + 34, TOP2 + 109, "no `SPECTIO_*` variable set", size=13, anchor="start")
    s.text(x + 34, TOP2 + 133, "the bridge makes the run ID", size=13, anchor="start",
           colour=t.dim)
    s.text(x + 34, TOP2 + 157, "nf-spectio does the same", size=13, anchor="start", colour=t.dim)
    s.step(x + CW5 / 2, CAP2, 6, "started from a terminal")
    lines(s, x, CAP2 + 30, ("no Spectio command in between",
                            "launch 1, origin `cli-observed`",
                            "no Cancel from the screens"))

    # 7 spool and pointer
    x = COL5[1]
    s.folder(x, TOP2, 134, 76, fill="input", label="`.spectio/events`")
    s.folder(x + 146, TOP2, 134, 76, fill="input", label="`observed`")
    s.lock(x + 266, TOP2 + 72, size=11)
    s.text(x + 67, TOP2 + 96, "in the launch dir", size=12.5, colour=t.dim)
    s.text(x + 213, TOP2 + 96, "in `~/.spectio`", size=12.5, colour=t.dim)
    s.text(x, TOP2 + 126, "spool `<run ID>-<producer>-<nnnn>.jsonl`", size=12, anchor="start")
    s.text(x, TOP2 + 150, "pointer `<run ID>.json`, 0600", size=12, anchor="start")
    s.text(x, TOP2 + 172, "temporary name, then rename", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW5 / 2, CAP2, 7, "spool and pointer")
    lines(s, x, CAP2 + 30, ("written relative to checked dirs",
                            "pointer only if `~/.spectio` exists",
                            "run ID, launch dir, host, PID,",
                            "start time, boot ID; nothing else"))

    # 8 the runner's scan
    x = COL5[2]
    s.page(x + 8, TOP2 + 4, 64, 84, fill="input", lines=3)
    s.magnifier(x + 62, TOP2 + 66, 16)
    checks = ("private dirs, no symlink", "under 4096 bytes", "strict keys only",
              "named by its run ID", "not in the runs root")
    for i, row in enumerate(checks):
        s.tick(x + 116, TOP2 + 8 + i * 25, size=6)
        s.text(x + 130, TOP2 + 13 + i * 25, row, size=12.5, anchor="start")
    s.text(x + 140, TOP2 + 160, "`scan_observed`, when the mtime moved", size=12)
    s.step(x + CW5 / 2, CAP2, 8, "the runner's scan")
    lines(s, x, CAP2 + 30, ("each pointer is untrusted input",
                            "a refused one: skipped, counted",
                            "the boot rebuild reads `observed`,",
                            "then `observed/ended`"))

    # 9 this host, this boot
    x = COL5[3]
    s.hpc_node(x + 4, TOP2, 50, 68, busy=2)
    s.text(x + 68, TOP2 + 18, "`checkable(host, boot_id)`", size=12, anchor="start")
    s.tick(x + 78, TOP2 + 42, size=6)
    s.text(x + 92, TOP2 + 47, "yes: PID and start time", size=12.5, anchor="start")
    s.cross(x + 78, TOP2 + 66, size=6)
    s.text(x + 92, TOP2 + 71, "no: never checked here", size=12.5, anchor="start")
    s.browser(x, TOP2 + 94, 276, 82, url="run page")
    s.text(x + 14, TOP2 + 146, "Not checked (on node-7,", size=13, anchor="start")
    s.text(x + 14, TOP2 + 166, "started from a terminal)", size=13, anchor="start")
    s.step(x + CW5 / 2, CAP2, 9, "this host, this boot")
    lines(s, x, CAP2 + 30, ("one `checkable`, runner and API",
                            "`head.checked` false elsewhere",
                            "only an end event ends it there",
                            "nothing is ever signalled"))

    # 10 the end
    x = COL5[4]
    s.text(x, TOP2 + 14, "Snakemake writes no end event:", size=12.5, anchor="start")
    s.text(x, TOP2 + 34, "its last progress decides", size=12.5, anchor="start", colour=t.dim)
    bar(s, x + 4, TOP2 + 48, 150, 18, "bar_green")
    s.text(x + 166, TOP2 + 62, "done = total", size=12.5, anchor="start")
    s.page(x + 14, TOP2 + 96, 40, 52, fill="input", lines=2)
    s.arrow(x + 64, TOP2 + 124, x + 120, TOP2 + 124)
    s.folder(x + 130, TOP2 + 94, 140, 66, fill="done", label="`ended`")
    s.text(x + 138, TOP2 + 180, "the pointer, moved", size=12.5, colour=t.dim)
    s.step(x + CW5 / 2, CAP2, 10, "the end")
    lines(s, x, CAP2 + 30, ("`spool_end`, head gone: succeeded",
                            "if no task failed, no error after,",
                            "else failed; assumed, inbox 113",
                            "another host or boot: open, FU-P3-50"))

    for a, b in zip(COL5[:4], COL5[1:]):
        s.arrow(a + CW5 - 4, TOP2 + 30, b - 6, TOP2 + 30)

    pin(s, COL5[0], PIN2, "CR-P3T25-02 r1", "major",
        ("no Playwright smoke of a terminal run,",
         "no guide and its version pin test"), "open, FU-P3-50", fixed=False)
    pin(s, COL5[1], PIN2, "CR-P3T25-03 r2", "major",
        ("one stuck launch dir took all 4 file",
         "threads; now one job per directory"), "fixed in 3279826", fixed=True)
    pin(s, COL5[2], PIN2, "SEC-P3T25-01 r1", "major",
        ("`realpath` ran inside the writer's",
         "transaction; a stale mount stopped it"), "fixed in 42f3a5e, a text check there",
        fixed=True)
    pin(s, COL5[4], PIN2, "CR-P3T25-01 r1", "blocker",
        ("every Snakemake terminal run ended",
         "failed; no exit code, no end event"), "fixed in 42f3a5e, `spool_end`", fixed=True)

    # == Task 26: release packages, dry run =====================================================
    band(s, 1262, "Task 26, PR 148 · both bridges build as release packages, dry run only · "
         "a registry key or PyPI token in the environment: it refuses to start")

    # 11 the Nextflow plugin zip
    x = COL4[0]
    s.terminal(x, TOP3, 300, 60, ("$ ./gradlew packagePlugin",), size=12.5)
    s.page(x + 10, TOP3 + 80, 56, 72, fill="done", lines=3)
    s.text(x + 82, TOP3 + 98, "`nf-spectio-0.0.1.zip`", size=12.5, anchor="start")
    s.lock(x + 90, TOP3 + 124, size=10)
    s.text(x + 106, TOP3 + 128, "Gradle 8.14.3, by its sha256", size=12.5, anchor="start")
    s.lock(x + 90, TOP3 + 148, size=10)
    s.text(x + 106, TOP3 + 152, "145 components hashed", size=12.5, anchor="start")
    s.step(x + CW4 / 2, CAP3, 11, "the Nextflow plugin zip")
    lines(s, x, CAP3 + 30, ("`io.nextflow.nextflow-plugin` 1.0.0-beta.16",
                            "fresh `GRADLE_USER_HOME`, tracked files",
                            "hashes trusted on first use"))

    # 12 the manifest, then Nextflow
    x = COL4[1]
    s.page(x + 4, TOP3, 230, 112, fill="input", lines=0)
    for i, row in enumerate(("Plugin-Id: nf-spectio", "Plugin-Version: 0.0.1",
                             "Plugin-Requires: >=25.04.0", "Plugin-Provider: spectio")):
        s.text(x + 16, TOP3 + 26 + i * 22, f"`{row}`", size=12, anchor="start",
               colour=t.accent if row.endswith("spectio") and "Provider" in row else t.ink)
    s.tick(x + 14, TOP3 + 136, size=7)
    s.text(x + 30, TOP3 + 141, "Nextflow loads the zip and runs", size=13, anchor="start")
    s.text(x + 30, TOP3 + 162, "the synthetic `happy`", size=13, anchor="start", colour=t.dim)
    s.step(x + CW4 / 2, CAP3, 12, "the manifest, then Nextflow")
    lines(s, x, CAP3 + 30, ("each line asserted by the dry run",
                            "the floor of architecture 13.4",
                            "the provider must match the claim"))

    # 13 the logger, sdist and wheel
    x = COL4[2]
    s.terminal(x, TOP3, 300, 80, ("$ uv build", "$ twine check --strict"), size=12.5)
    s.page(x + 30, TOP3 + 96, 52, 64, fill="neutral", lines=2)
    s.text(x + 56, TOP3 + 178, "sdist", size=13)
    s.arrow(x + 92, TOP3 + 128, x + 142, TOP3 + 128)
    s.page(x + 152, TOP3 + 96, 52, 64, fill="done", lines=2)
    s.text(x + 178, TOP3 + 178, "wheel", size=13)
    s.text(x + 222, TOP3 + 120, "files and", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 222, TOP3 + 140, "metadata", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW4 / 2, CAP3, 13, "the logger, sdist and wheel")
    lines(s, x, CAP3 + 30, ("`snakemake-logger-plugin-spectio`",
                            "`README.md` is the PyPI description",
                            "the root `docs/intro.md`: the catalogue"))

    # 14 into a fresh Snakemake 9
    x = COL4[3]
    s.terminal(x, TOP3, 330, 80, ("$ snakemake --logger spectio", "  synthetic happy"), size=12.5)
    s.lock(x + 14, TOP3 + 106, size=10)
    s.text(x + 30, TOP3 + 110, "`--require-hashes -r dev/snakemake.lock.txt`", size=11.5,
           anchor="start")
    s.envelope(x + 6, TOP3 + 130, 50, 34)
    s.cross(x + 31, TOP3 + 147, size=12)
    s.text(x + 70, TOP3 + 144, "nothing uploaded, no key,", size=13, anchor="start")
    s.text(x + 70, TOP3 + 164, "no release task", size=13, anchor="start", colour=t.dim)
    s.step(x + CW4 / 2, CAP3, 14, "into a fresh Snakemake 9")
    lines(s, x, CAP3 + 30, ("the built wheel writes the events",
                            "`RESULT bridges-release dry-run pass`",
                            "first run here: 429 and 403, network"))

    for a, b in zip(COL4[:3], COL4[1:]):
        s.arrow(a + CW4 - 22, TOP3 + 30, b - 8, TOP3 + 30)

    pin(s, COL4[1], PIN3, "DW-P3T26-01", "major, release",
        ("the claim's provider is `spectio-org`;",
         "the build and the test say `spectio`"), "open, FU-P3-51", fixed=False, w=300)
    pin(s, COL4[2], PIN3, "CR-P3T26-01 r1", "major",
        ("a second `docs/intro.md` in the package;",
         "the real page stayed on 0.0.0"), "fixed in 6e9d080, `README.md`", fixed=True, w=300)

    # == tests, to scale, and the batch simplifier ===============================================
    s.line(30, LOW - 14, W - 30, LOW - 14, dashed=True, colour=t.muted)
    s.text(50, LOW + 18, "tests passed, to scale", size=14, anchor="start", weight="bold")
    tests = (("whole suite", "batch, f69437e", 939, "939, 28 deselected"),
             ("`spectio-server`", "Task 21, 21005f3", 594, "594"),
             ("observed, read API", "Task 25, d5e2193", 75, "75"),
             ("Snakemake logger", "Task 26, 6e9d080", 53, "53"),
             ("Nextflow bridge", "Task 25, d5e2193", 26, "26, 1 skipped"))
    for i, (name, where, n, label) in enumerate(tests):
        y = LOW + 36 + i * 34
        s.text(50, y + 17, name, size=13, anchor="start")
        s.text(220, y + 17, where, size=12.5, anchor="start", colour=t.dim)
        bw = n * 0.55
        bar(s, 370, y, bw, 22, "bar_green")
        s.text(380 + bw, y + 17, label, size=13.5, anchor="start")
    s.text(50, LOW + 222, "web tests not run here: no `node_modules`", size=12.5, anchor="start",
           colour=t.dim)

    sx, sy = 1090, LOW + 2
    s.shade(sx, sy, 460, 216, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 26, "batch simplify, f69437e, 5 files", size=13.5, anchor="start",
           weight="bold")
    px = 8  # px per line, to scale
    bar(s, sx + 56, sy + 40, 24 * px, 18, "problem")
    s.text(sx + 14, sy + 54, "-24", size=13.5, anchor="start")
    bar(s, sx + 56, sy + 64, 11 * px, 18, "done")
    s.text(sx + 14, sy + 78, "+11", size=13.5, anchor="start")
    s.text(sx + 262, sy + 66, "939 passed,", size=12.5, anchor="start", colour=t.dim)
    s.text(sx + 262, sy + 84, "before and after", size=12.5, anchor="start", colour=t.dim)
    for i, row in enumerate(("`alive`, `head_gone` call `checkable`",
                             "`rebuild_index` loses `timeout_s`",
                             "`insert_observed_run` returns None")):
        s.text(sx + 14, sy + 112 + i * 20, row, size=12.5, anchor="start")
    s.text(sx + 14, sy + 178, "re-review approve; CR-P3B03-01, -02 minor:", size=12.5,
           anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 198, "a test's patch no longer reaches the rebuild", size=12.5,
           anchor="start", colour=t.dim)

    s.prefix_key(50, H - 16, ("CR", "SEC"))
    s.text(350, H - 16, "· DW doc-writer", size=13.5, anchor="start", colour=t.dim)
    s.text(W - 50, H - 16, "source: hatch_build.py · static.py · runner/observed.py, loop.py, "
           "local.py · build.gradle · tests/packaging at f69437e", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b03-wheel-terminal-release")
