#!/usr/bin/env python3
"""DAG updates, temporary outputs, the SLURM request and efficiency: batch P3-B04 (P1 Tasks 33,
34 and 35, milestone M9), step P3, 2026-11-08.

Writes docs/assets/diagrams/p3-b04-dag-temp-efficiency_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B04 at 5105cbb (PRs 151, 152 and 153 merged into
autopilot/integration between ccda94b and f5c26a9, plus the batch code-simplifier's commit):
- Task 33: engine-bridges/snakemake-logger-plugin-spectio/.../__init__.py SNAKEMAKE_TEXTS
  (SNAKEMAKE_TEXTS_VERSION 9.27.1; "Removing temporary output <path>." dag.py:1054-1056,
  "Write-protecting output file <path>." dag.py:932-936, "Updating checkpoint dependencies."
  dag.py:2245; `fullmatch`), `read_text` (only for a record with no `event`), the set
  `temp_removed` and MAX_TEMP_PATHS 65536, "Snakemake logs some removals twice (T2, row 19)";
  `_job_info` `custom_options = bool(resources.pop("slurm_extra"))` (Task 34);
  engine-bridges/nf-spectio/.../SpectioPlugin.groovy WHERE_KEYS + REQUEST_KEYS (cpus, memory,
  time, disk, queue, accelerator, accelerator_type, attempt) on the hooks without the full trace,
  `setsClusterOptions` (MAX_CONFIG_DEPTH 8, the `process` config and its selectors, "a directive
  written in the script itself is not in the config"), `onFlowCreate` `cleanup`,
  `clusterOptionsSet`; spectio_sdk/events.py SnakemakeOutputPath (`path` required),
  SnakemakeDagUpdated (empty), NextflowFlowCreate; the example paths are the rules of
  tests/workflows/dag/Snakefile (seed, checkpoint fan_out, part, summary);
- Task 34: spectio/runner/sacct.py FORMAT (16 fields), `parse_sacct` (TotalCPU summed over the
  step rows, the largest MaxRSS, a step only after its job's line, two job lines for one ID give
  no row), `_req_mem`; spectio_server/efficiency.py `sacct_measure` ("as seff does"),
  `engine_measure` (trace or benchmark), `job` (running, available, unavailable with a reason,
  pending_accounting), `aggregate` (last attempts, mean and max, the most common request, one
  `varies`); stages/state.py `process_status`, `checkpoint_open`; api/models.py ProcessStatus,
  `lower_bound`, `open_checkpoints`, `dag_updates`; failure.py `Measures` (`claim`, `release`),
  MAX_BENCHMARKS_PER_VIEW 500, BENCHMARK_CHUNK 100, files/pool.py READ_TIMEOUT_S 5.0;
  projector/snakemake.py `_output_event` (kept once, for an output of the run's jobs only);
- Task 35: web/src/runs/stateWord.ts `processState` (Waiting for checkpoint <name>, Not needed
  in this run, Up to date, No task (condition or empty input)); RunDetailPage.tsx (Checkpoint
  chip, "at least", the hatched bar, "Nothing to run: all outputs are up to date", "The DAG grows
  after checkpoint <name>: more jobs may come."); RunState.tsx `Low`, `tasksText`;
  resources.ts `isLow` < 0.25, `isNear` > 0.9; ByProcess.tsx COLUMNS (Mem eff. mean, Requests
  "vary"), `wasteLines`, Sort by; SlurmFacts.tsx (the request fields that are set, "Allocated" and
  "differs from the request", "Custom sbatch options set", "Waiting for SLURM accounting (sacct)",
  "from sacct"); TaskFiles.tsx OUTPUT_WORDS, "Outputs (n)", the drawer on Outputs with no file,
  CLEANUP; RunHeader.tsx `engineSettings`;
- findings: docs/reviews/code/P3-t33.md, P3-t34.md, P3-t35.md (every blocker and major, by
  round; IDs restart per round, so each pin names its round);
- test counts from the same records and the simplifier's report: the Python suite 981 passed,
  30 deselected, at 33ec45f and as the simplifier's baseline; Vitest 320 passed in 27 files at
  62dabd1, before and after 5105cbb; the Snakemake logger 69 passed at ba74236;
  test_efficiency.py and test_process_status.py 37, web/src/api.test.ts 31, test_sacct.py 18, at
  33ec45f; the simplifier: 3 files, -27 +8 (`git show --stat 5105cbb`).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 2160
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280

TOP1, CAP1 = 165, 385  # Task 33
TOP2, CAP2, PIN2 = 615, 835, 950  # Task 34
TOP3, CAP3, PIN3 = 1340, 1560, 1675  # Task 35
LOW = 1840  # tests and the simplifier


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, severity: str, rows: tuple[str, ...],
        status: str, *, w: float = 280) -> None:
    """A blocker or major pinned where it hit: its ID and round, what it was, its fix."""
    h = 34 + 19 * (len(rows) + 1)
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill="done", amount=0.5, width=1.2)
    s.tick(x + 16, y + 13, size=6)
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


def hatched(s: Sketch, x: float, y: float, w: float, h: float, done: float) -> None:
    """The bar of a lower bound: done filled, the rest hatched, never full."""
    bar(s, x, y, w * done, h, "bar_green")
    s.shade(x + w * done, y, w * (1 - done), h, fill="neutral", opacity=0.5, colour=s.t.muted, dashed=True)
    step = 8
    start = x + w * done
    for i in range(int(w * (1 - done) // step)):
        x0 = start + i * step + 2
        s.line(x0, y + h - 2, min(x0 + h - 4, x + w - 2), y + 2, colour=s.t.muted, amount=0.2, passes=1,
               width=1.0)


def strip(s: Sketch, x: float, y: float, w: float, text: str, fill: str, *, h: float = 22) -> None:
    """One line of output or of a list, drawn as a strip with its text."""
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.1)
    s.text(x + 8, y + h - 6, text, size=12, anchor="start")


def badge(s: Sketch, x: float, y: float, word: str, fill: str) -> float:
    """A word on a tint, as the screens draw "low" and "near limit"; returns its right edge."""
    w = 8 + len(word) * 6.6
    s.poly([(x, y - 12), (x + w, y - 12), (x + w, y + 4), (x, y + 4)], fill=fill, amount=0.3, width=1.0)
    s.text(x + 4, y, word, size=11.5, anchor="start")
    return x + w


def arrows(s: Sketch, y: float) -> None:
    for a, b in zip(COL[:4], COL[1:]):
        s.arrow(a + CW + 2, y, b - 3, y)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=404)
    t = theme
    s.heading(50, 58, "P3-B04 · DAG updates, temporary outputs, SLURM request and efficiency, "
              "P1 Tasks 33, 34, 35",
              "milestone M9 · api 5 and 14.1 · schedulers 3.6 · ui-spec 4.4 and 5.2 · "
              "PRs 151, 152 and 153 into `autopilot/integration`")

    # == Task 33: the bridges send what only they see ==========================================
    band(s, 140, "Task 33, PR 151 · the engine bridges send what only they see: "
         "Snakemake's own texts, and Nextflow's request from submission")

    # 1 three Snakemake texts
    x = COL[0]
    s.terminal(x, TOP1, CW, 140, ("Removing temporary output",
                                  "  tmp/seed.txt.",
                                  "Write-protecting output file",
                                  "  out/summary.txt.",
                                  "Updating checkpoint dependencies."), size=12, line_h=19)
    s.text(x, TOP1 + 168, "`temp_removed` · `protected` · `dag_updated`", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 1, "three Snakemake texts")
    lines(s, x, CAP1 + 30, ("pinned to Snakemake 9.27.1, `dag.py`",
                            "each matches the whole message",
                            "only a record with no event is read",
                            "reworded: stays `snakemake.log`"))

    # 2 each removal once
    x = COL[1]
    strip(s, x, TOP1 + 6, 150, "`tmp/seed.txt`", "neutral")
    strip(s, x, TOP1 + 34, 150, "`tmp/seed.txt`", "neutral")
    s.text(x + 75, TOP1 + 82, "logged twice", size=12.5, colour=t.dim)
    s.arrow(x + 156, TOP1 + 32, x + 186, TOP1 + 32)
    s.bucket(x + 232, TOP1 + 12, 76, 56, fill="gate")
    s.text(x + 232, TOP1 + 46, "sent", size=12.5)
    s.text(x + 232, TOP1 + 96, "a set of paths", size=12.5, colour=t.dim)
    s.arrow(x + 232, TOP1 + 108, x + 232, TOP1 + 128)
    strip(s, x + 130, TOP1 + 134, 150, "`tmp/seed.txt`", "done")
    s.tick(x + 112, TOP1 + 145, size=7)
    s.text(x, TOP1 + 178, "one `snakemake.temp_removed`", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP1, 2, "each removal once")
    lines(s, x, CAP1 + 30, ("Snakemake 9.27.1 logs some twice",
                            "the plugin remembers up to 65536",
                            "paths per launch, then sends all",
                            "bounded in paths, not bytes: open"))

    # 3 two flags at flow create
    x = COL[2]
    s.page(x + 4, TOP1 + 4, 132, 116, fill="input", lines=0)
    s.text(x + 14, TOP1 + 32, "`nextflow.config`", size=12, anchor="start", colour=t.dim)
    s.text(x + 14, TOP1 + 58, "`cleanup = true`", size=12, anchor="start")
    s.text(x + 14, TOP1 + 82, "`process`", size=12, anchor="start")
    s.text(x + 24, TOP1 + 104, "`clusterOptions`", size=12, anchor="start")
    s.arrow(x + 142, TOP1 + 62, x + 168, TOP1 + 62)
    s.text(x + 176, TOP1 + 40, "`cleanup`", size=12, anchor="start")
    s.tick(x + 260, TOP1 + 35, size=6)
    s.text(x + 176, TOP1 + 70, "`clusterOptionsSet`", size=11.5, anchor="start")
    s.lock(x + 196, TOP1 + 102, size=11)
    s.text(x + 212, TOP1 + 106, "no text", size=12.5, anchor="start", colour=t.dim)
    s.text(x, TOP1 + 150, "`setsClusterOptions`: the config and", size=12.5, anchor="start")
    s.text(x, TOP1 + 170, "its selectors, at most 8 deep", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP1, 3, "two flags at flow create")
    lines(s, x, CAP1 + 30, ("`cleanup` as `Session.cleanup` reads it",
                            "only whether `clusterOptions` is set",
                            "a directive in the script: not seen,",
                            "open, CR-P3T33-01, SEC-P3T33-02"))

    # 4 the request from submission
    x = COL[3]
    hooks = ("pending", "submit", "start", "complete")
    s.line(x + 20, TOP1 + 40, x + 260, TOP1 + 40, colour=t.dim)
    for i, hook in enumerate(hooks):
        hx = x + 30 + i * 74
        s.circle(hx, TOP1 + 40, 8, fill="done" if i == 3 else "input")
        s.text(hx, TOP1 + 22, hook, size=12.5)
    s.text(x, TOP1 + 76, "first three: `native_id`, `workdir` and", size=12.5, anchor="start")
    for i, keys in enumerate(("`cpus` `memory` `time` `disk`",
                              "`queue` `accelerator`",
                              "`accelerator_type` `attempt`")):
        s.text(x + 14, TOP1 + 100 + i * 21, keys, size=12.5, anchor="start")
    s.text(x, TOP1 + 172, "complete: the whole trace, as before", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP1, 4, "the request from submission")
    lines(s, x, CAP1 + 30, ("`REQUEST_KEYS` on the early hooks",
                            "measured keys: the final ones only",
                            "on the local executor `queue` is null",
                            "real SLURM: waits for Task 22"))

    # 5 allow-listed in the SDK
    x = COL[4]
    s.folder(x + 4, TOP1 + 2, 270, 92, fill="input")
    s.text(x + 139, TOP1 + 36, "`.spectio/events`", size=12.5)
    for i in range(3):
        s.page(x + 92 + i * 38, TOP1 + 48, 30, 36, fill="surface", lines=1)
    for i, row in enumerate(("`snakemake.temp_removed`, `path`",
                             "`snakemake.protected`, `path`",
                             "`snakemake.dag_updated`, empty")):
        s.tick(x + 10, TOP1 + 116 + i * 22, size=5)
        s.text(x + 22, TOP1 + 121 + i * 22, row, size=12, anchor="start")
    s.step(x + CW / 2, CAP1, 5, "allow-listed in the SDK")
    lines(s, x, CAP1 + 30, ("`spectio_sdk/events.py`",
                            "`flow_create` gains the two flags",
                            "Task 34 projects the new types"))

    arrows(s, TOP1 + 60)
    s.tick(COL[0] + 8, CAP1 + 125, size=7)
    s.text(COL[0] + 24, CAP1 + 130, "approve in 1 round · no blocker, no major · 7 minors, all open, "
           "FU-P3-52, inbox 115", size=13.5, anchor="start", colour=t.dim)

    # == Task 34: the server ===================================================================
    band(s, 590, "Task 34, PR 152 · the server asks `sacct` for every ended SLURM job of both engines, "
         "then the efficiency per job and per process, and each rule's state")

    # 6 sacct
    x = COL[0]
    strip(s, x, TOP2 + 4, 240, "`123`  state, limits, allocation", "input")
    strip(s, x + 24, TOP2 + 30, 216, "`123.batch`  `TotalCPU` `MaxRSS`", "neutral")
    strip(s, x + 24, TOP2 + 56, 216, "`123.extern`  `TotalCPU` `MaxRSS`", "neutral")
    s.text(x + 252, TOP2 + 60, "sum,", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 252, TOP2 + 78, "max", size=12.5, anchor="start", colour=t.dim)
    strip(s, x, TOP2 + 104, 116, "`456`", "problem")
    strip(s, x, TOP2 + 130, 116, "`456`", "problem")
    s.arrow(x + 124, TOP2 + 128, x + 158, TOP2 + 128)
    s.cross(x + 176, TOP2 + 128, size=9)
    s.text(x + 194, TOP2 + 133, "no row", size=13, anchor="start")
    s.text(x, TOP2 + 180, "16 fields, `--parsable2`", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP2, 6, "`sacct`, both engines")
    lines(s, x, CAP2 + 30, ("every ended job with a job ID",
                            "`ReqMem` per CPU or node made whole",
                            "a step counts after its job's line",
                            "two job lines for an ID: no row"))

    # 7 one job's efficiency
    x = COL[1]
    for i, (name, top, bottom) in enumerate((("CPU", "`TotalCPU`", "`Elapsed` x `NCPUS`"),
                                             ("memory", "`MaxRSS`", "`ReqMem`"))):
        fx = x + 4 + i * 150
        s.text(fx, TOP2 + 14, name, size=13, anchor="start", weight="bold")
        s.text(fx + 62, TOP2 + 40, top, size=12)
        s.line(fx, TOP2 + 48, fx + 124, TOP2 + 48, amount=0.3, passes=1)
        s.text(fx + 62, TOP2 + 66, bottom, size=12)
    s.text(x + 4, TOP2 + 92, "as `seff` does, never clamped", size=12.5, anchor="start", colour=t.dim)
    states = (("`running`", "input", "until it ends"), ("`available`", "done", "from sacct"),
              ("`pending_accounting`", "gate", "sacct not yet"),
              ("`unavailable`", "problem", "and a reason"))
    for i, (word, fill, why) in enumerate(states):
        y = TOP2 + 108 + i * 22
        strip(s, x + 4, y, 150, word, fill, h=19)
        s.text(x + 164, y + 14, why, size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP2, 7, "one job's efficiency")
    lines(s, x, CAP2 + 30, ("`sacct` first, once the job ended",
                            "else the Nextflow trace or",
                            "the Snakemake benchmark",
                            "a reused job: no value, `cached`"))

    # 8 per process or rule
    x = COL[2]
    for i in range(4):
        s.page(x + 8 + i * 22, TOP2 + 8 + i * 10, 46, 58, fill="surface", lines=2)
    s.text(x + 66, TOP2 + 128, "last attempts", size=12.5, colour=t.dim)
    s.arrow(x + 136, TOP2 + 56, x + 162, TOP2 + 56)
    s.poly([(x + 168, TOP2 + 6), (x + 278, TOP2 + 6), (x + 278, TOP2 + 150), (x + 168, TOP2 + 150)],
           fill="done", amount=0.5, width=1.2)
    for i, row in enumerate(("mean", "max", "requested", "`varies`", "used")):
        s.text(x + 178, TOP2 + 30 + i * 26, row, size=12.5, anchor="start")
    s.text(x + 140, TOP2 + 180, "`aggregate`, one row per process", size=12.5, colour=t.dim)
    s.step(x + CW / 2, CAP2, 8, "per process or rule")
    lines(s, x, CAP2 + 30, ("CPU and memory, mean and max",
                            "requested: the most common value",
                            "one `varies` flag for all three",
                            "jobs total: at least Snakemake's plan"))

    # 9 the state of each rule
    x = COL[3]
    nodes = ((x + 30, TOP2 + 40, "`seed`", "done"), (x + 112, TOP2 + 40, "`fan_out`", "gate"),
             (x + 194, TOP2 + 40, "`part`", "neutral"), (x + 252, TOP2 + 104, "`summary`", "neutral"))
    s.arrow(x + 46, TOP2 + 40, x + 94, TOP2 + 40)
    s.arrow(x + 130, TOP2 + 40, x + 176, TOP2 + 40, dashed=True)
    s.arrow(x + 204, TOP2 + 54, x + 240, TOP2 + 90, dashed=True)
    for nx, ny, name, fill in nodes:
        s.circle(nx, ny, 15, fill=fill)
        s.text(nx, ny + 34, name, size=12)
    s.text(x + 112, TOP2 + 12, "checkpoint", size=12, colour=t.accent)
    s.text(x + 4, TOP2 + 116, "`awaiting_checkpoint`", size=12, anchor="start")
    s.text(x + 4, TOP2 + 136, "while `fan_out` is open", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 4, TOP2 + 166, "`lower_bound`, `open_checkpoints`,", size=12, anchor="start")
    s.text(x + 4, TOP2 + 186, "`dag_updates` in the run summary", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP2, 9, "the state of each rule")
    lines(s, x, CAP2 + 30, ("new: `awaiting_checkpoint`, `not_needed`,",
                            "`up_to_date` and Nextflow's `no_tasks`",
                            "after a DAG update, jobs to come:",
                            "`pending`, not `not_needed`"))

    # 10 benchmarks read once
    x = COL[4]
    s.folder(x + 2, TOP2 + 6, 96, 70, fill="input", label="benchmarks")
    s.arrow(x + 104, TOP2 + 42, x + 128, TOP2 + 42)
    s.cog(x + 148, TOP2 + 42, 14, fill="work")
    s.text(x + 148, TOP2 + 80, "pool thread", size=12.5, colour=t.dim)
    s.arrow(x + 168, TOP2 + 42, x + 194, TOP2 + 42)
    s.bucket(x + 236, TOP2 + 22, 76, 56, fill="done")
    s.text(x + 236, TOP2 + 56, "`Measures`", size=11.5)
    s.text(x + 236, TOP2 + 100, "by attempt ID", size=12.5, colour=t.dim)
    for i, row in enumerate(("one sweep per run at a time",
                             "at most 500 per view, 100 per batch",
                             "each batch kept as soon as read")):
        s.tick(x + 10, TOP2 + 126 + i * 22, size=5)
        s.text(x + 22, TOP2 + 131 + i * 22, row, size=12.5, anchor="start")
    s.step(x + CW / 2, CAP2, 10, "benchmarks read once")
    lines(s, x, CAP2 + 30, ("the By process view, fetched about",
                            "once a second, opens no file twice",
                            "`READ_TIMEOUT_S` 5 s, a shared pool",
                            "cached until a restart: open"))

    arrows(s, TOP2 + 60)

    pin(s, COL[3], PIN2, "CR-P3T34-02 r1", "major",
        ("after a DAG update rules read", "`not_needed` while jobs were to come"),
        "fixed in 4d1965c, `pending`")
    pin(s, COL[4], PIN2, "CR-P3T34-01 r1", "major",
        ("every view read every benchmark", "and queued every ended SLURM job"),
        "fixed in 4d1965c, `Measures`")
    pin(s, COL[4], PIN2 + 102, "CR-P3T34-03 r2", "major",
        ("a read past the 5 s timeout was", "thrown away: the cache never filled"),
        "fixed in 1abf966, batches kept")
    pin(s, COL[4], PIN2 + 204, "SEC-P3T34-01 r2", "major",
        ("each poll queued another sweep:", "the shared pool full, file routes 503"),
        "fixed in 1abf966, one sweep per run")

    nx, ny = COL[0], PIN2
    s.shade(nx, ny, 890, 150, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.text(nx + 14, ny + 26, "4 rounds: code-reviewer changes, changes, approve, approve · "
           "security-reviewer approve, changes, approve, approve", size=13.5, anchor="start")
    s.warning(nx + 24, ny + 54, size=10)
    s.text(nx + 44, ny + 60, "not run: the `slurm-mini` check, P1 Task 22 is not built; "
           "the `sacct` output in the tests is synthetic", size=13.5, anchor="start")
    s.text(nx + 44, ny + 82, "to be validated there: step rows come after their job, one job line "
           "per ID without `--duplicates`", size=13.5, anchor="start", colour=t.dim)
    s.warning(nx + 24, ny + 110, size=10)
    s.text(nx + 44, ny + 116, "open trade-off, SEC-P3T34-06 r4: a job SLURM resized gets no row, "
           "its state and reason lost", size=13.5, anchor="start")
    s.text(nx + 44, ny + 138, "every open minor: FU-P3-53 · assumed: inbox 116", size=13.5,
           anchor="start", colour=t.dim)

    # == Task 35: the screens ==================================================================
    band(s, 1315, "Task 35, PR 153 · the screens show what Task 34 serves: states and checkpoints, "
         "efficiency by process or rule, the SLURM request, the outputs")

    # 11 states and checkpoints
    x = COL[0]
    s.browser(x, TOP3, CW, 196, url="run page")
    rows = (("`seed`", "Done", None), ("`fan_out`", "Running", "Checkpoint"),
            ("`part`", "Waiting for checkpoint fan_out", None),
            ("`other`", "Not needed in this run", None))
    for i, (name, word, chip) in enumerate(rows):
        y = TOP3 + 50 + i * 22
        greyed = i == 3
        s.text(x + 12, y, name, size=12, anchor="start", colour=t.dim if greyed else t.ink)
        wx = x + 84
        if chip:
            wx = badge(s, wx, y, chip, "gate") + 8
        s.text(wx, y, word, size=12.5, anchor="start", colour=t.dim if greyed else t.ink)
    hatched(s, x + 12, TOP3 + 126, 130, 16, 0.55)
    s.text(x + 152, TOP3 + 139, "done / at least n", size=12.5, anchor="start")
    s.text(x + 12, TOP3 + 166, "The DAG grows after checkpoint", size=12.5, anchor="start")
    s.text(x + 12, TOP3 + 185, "fan_out: more jobs may come.", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP3, 11, "states and checkpoints")
    lines(s, x, CAP3 + 30, ("Not needed: greyed, listed last",
                            "Up to date, No task, condition or",
                            "empty input · Nothing to run: all",
                            "outputs are up to date"))

    # 12 By process, By rule
    x = COL[1]
    s.button(x, TOP3, 100, "Task list", fill="surface", h=28)
    s.button(x + 106, TOP3, 100, "By rule", fill="input", h=28)
    hy = TOP3 + 56
    s.line(x, hy + 8, x + CW, hy + 8, colour=t.muted, amount=0.3, passes=1)
    for cx, head in ((x + 4, "Rule"), (x + 76, "Mem eff. mean"), (x + 200, "Requests")):
        s.text(cx, hy, head, size=12.5, anchor="start", weight="bold")
    s.text(x + 182, hy, "v", size=12, anchor="start", colour=t.accent)
    for i, (name, word, fill, vary) in enumerate((("`part`", "low", "neutral", "vary"),
                                                  ("`summary`", "near limit", "work", ""))):
        y = hy + 32 + i * 28
        s.text(x + 4, y, name, size=12, anchor="start")
        badge(s, x + 76, y, word, fill)
        s.text(x + 200, y, vary, size=12.5, anchor="start")
    s.text(x, TOP3 + 158, "n jobs of `part` used under 25 %", size=12.5, anchor="start")
    s.text(x, TOP3 + 178, "of their memory", size=12.5, anchor="start", colour=t.dim)
    s.step(x + CW / 2, CAP3, 12, "By process, By rule")
    lines(s, x, CAP3 + 30, ("a sort button in every header",
                            "low under 25 %, near limit over 90 %",
                            "Requests: vary, one mark per row",
                            "phone: cards and a Sort by select"))

    # 13 the job's SLURM and efficiency
    x = COL[2]
    s.frame(x, TOP3, CW, 196)
    s.text(x + 12, TOP3 + 22, "SLURM", size=13, anchor="start", weight="bold")
    for i, label in enumerate(("Partition", "CPUs", "Memory", "Time limit")):
        s.text(x + 12 + (i % 2) * 130, TOP3 + 44 + (i // 2) * 20, label, size=12.5, anchor="start",
               colour=t.dim)
    s.text(x + 12, TOP3 + 92, "Allocated", size=12.5, anchor="start", colour=t.dim)
    badge(s, x + 86, TOP3 + 92, "differs from the request", "work")
    s.text(x + 12, TOP3 + 114, "Custom sbatch options set", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 190, TOP3 + 114, "yes", size=12.5, anchor="start")
    s.lock(x + 230, TOP3 + 110, size=9)
    s.line(x + 10, TOP3 + 126, x + CW - 10, TOP3 + 126, colour=t.muted, amount=0.3, passes=1)
    s.text(x + 12, TOP3 + 148, "Efficiency", size=13, anchor="start", weight="bold")
    s.text(x + 12, TOP3 + 170, "CPU · memory", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 120, TOP3 + 170, "from sacct", size=12.5, anchor="start")
    s.text(x + 12, TOP3 + 189, "Waiting for SLURM accounting (sacct)", size=12, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP3, 13, "the job's SLURM facts")
    lines(s, x, CAP3 + 30, ("only the fields the engine set",
                            "Allocated only when it differs",
                            "options set, never their text",
                            "a local run: no SLURM block"))

    # 14 the Outputs tab
    x = COL[3]
    s.frame(x, TOP3, CW, 140)
    s.text(x + 14, TOP3 + 24, "job log", size=12.5, anchor="start", colour=t.dim)
    s.text(x + 90, TOP3 + 24, "Outputs (2)", size=12.5, anchor="start", weight="bold")
    s.line(x + 88, TOP3 + 32, x + 172, TOP3 + 32, colour=t.accent, amount=0.2, passes=1, width=2)
    s.text(x + 14, TOP3 + 58, "`out/summary.txt`", size=12, anchor="start")
    s.text(x + 26, TOP3 + 78, "present · write-protected", size=12.5, anchor="start", colour=t.dim)
    s.lock(x + 238, TOP3 + 74, size=9)
    s.text(x + 14, TOP3 + 106, "`tmp/seed.txt`", size=12, anchor="start")
    s.text(x + 26, TOP3 + 126, "deleted by Snakemake (temporary)", size=12.5, anchor="start",
           colour=t.dim)
    s.text(x, TOP3 + 164, "Nextflow: removed by cleanup = true", size=12.5, anchor="start")
    s.text(x, TOP3 + 184, "kept once, for a known output only", size=12.5, anchor="start",
           colour=t.dim)
    s.step(x + CW / 2, CAP3, 14, "the Outputs tab")
    lines(s, x, CAP3 + 30, ("on a Snakemake attempt, after the files",
                            "no log file: the drawer opens on it",
                            "the cleanup message on any run state:",
                            "open, CR-P3T35-07 r1"))

    # 15 header and phone
    x = COL[4]
    scr = s.phone(x + 4, TOP3 - 4, 112, 206)
    s.text(scr.x + 6, scr.y + 18, "Sort by", size=11.5, anchor="start", colour=t.dim)
    s.poly([(scr.x + 6, scr.y + 24), (scr.right - 6, scr.y + 24), (scr.right - 6, scr.y + 40),
            (scr.x + 6, scr.y + 40)], fill="input", amount=0.2, width=1.0)
    for i in range(2):
        cy = scr.y + 50 + i * 58
        s.poly([(scr.x + 4, cy), (scr.right - 4, cy), (scr.right - 4, cy + 50), (scr.x + 4, cy + 50)],
               fill="surface", amount=0.3, width=1.0)
        for j in range(3):
            s.line(scr.x + 10, cy + 12 + j * 13, scr.right - 14 - (j % 2) * 18, cy + 12 + j * 13,
                   colour=t.muted, amount=0.2, passes=1, width=1.1)
    hx = x + 130
    s.text(hx, TOP3 + 16, "Jobs", size=12.5, anchor="start", colour=t.dim)
    s.text(hx, TOP3 + 36, "done / at least n", size=12.5, anchor="start")
    s.text(hx, TOP3 + 66, "Engine settings", size=12.5, anchor="start", colour=t.dim)
    s.text(hx, TOP3 + 86, "Work directory", size=12.5, anchor="start")
    s.text(hx, TOP3 + 104, "cleaned after", size=12.5, anchor="start")
    s.text(hx, TOP3 + 122, "success", size=12.5, anchor="start")
    s.text(hx, TOP3 + 148, "Temporary files", size=12.5, anchor="start")
    s.text(hx, TOP3 + 166, "kept, `--notemp`", size=12.5, anchor="start")
    s.step(x + CW / 2, CAP3, 15, "the header, the phone")
    lines(s, x, CAP3 + 30, ("the run's facts, when it says so",
                            "phone cards: label and value rows",
                            "no Sort by Peak memory: open",
                            "SLURM, Efficiency: no disclosure"))

    pin(s, COL[1], PIN3, "CR-P3T35-05 r3", "major",
        ("one `varies` flag wrote varies on", "CPUs, memory and time limit"),
        "fixed in 62dabd1, Requests: vary")
    pin(s, COL[3], PIN3, "CR-P3T35-01 r1", "blocker",
        ("no log file, no tabs: a job without", "`log:` could not show its outputs"),
        "fixed in 4bde178, opens on Outputs")
    s.shade(COL[0], PIN3, 280, 91, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    for i, row in enumerate(("4 rounds: code-reviewer changes,", "approve, changes, approve;",
                             "security-reviewer approve in each")):
        s.text(COL[0] + 12, PIN3 + 24 + i * 21, row, size=12.5, anchor="start",
               colour=t.ink if i == 0 else t.dim)
    s.shade(COL[2], PIN3, 280, 91, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    for i, row in enumerate(("open, FU-P3-54: focus after Show", "the tasks, the grey low badge,",
                             "Home and End on the two tabs")):
        s.text(COL[2] + 12, PIN3 + 24 + i * 21, row, size=12.5, anchor="start",
               colour=t.ink if i == 0 else t.dim)
    s.shade(COL[4], PIN3, 280, 91, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    for i, row in enumerate(("not run: a SLURM run on the screens,", "`slurm-mini` waits for Task 22;",
                             "values in the tests are synthetic")):
        s.text(COL[4] + 12, PIN3 + 24 + i * 21, row, size=12.5, anchor="start",
               colour=t.ink if i == 0 else t.dim)

    # == tests, to scale, and the batch simplifier =============================================
    s.line(30, LOW - 14, W - 30, LOW - 14, dashed=True, colour=t.muted)
    s.text(50, LOW + 18, "tests passed, to scale", size=14, anchor="start", weight="bold")
    tests = (("Python suite", "Task 34, 33ec45f, and batch", 981, "981, 30 deselected"),
             ("web, Vitest", "Task 35, 62dabd1, and 5105cbb", 320, "320 in 27 files"),
             ("Snakemake logger", "Task 33, ba74236", 69, "69"),
             ("efficiency, states", "Task 34, 33ec45f", 37, "37"),
             ("web API types", "Task 34, 33ec45f", 31, "31"),
             ("`test_sacct.py`", "Task 34, 33ec45f", 18, "18"))
    for i, (name, where, n, label) in enumerate(tests):
        y = LOW + 34 + i * 34
        s.text(50, y + 17, name, size=13, anchor="start")
        s.text(196, y + 17, where, size=12.5, anchor="start", colour=t.dim)
        bw = n * 0.45
        bar(s, 400, y, bw, 22, "bar_green")
        s.text(410 + bw, y + 17, label, size=13.5, anchor="start")

    sx, sy, sw, sh = 1030, LOW + 2, 520, 250
    s.shade(sx, sy, sw, sh, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 26, "batch simplify, 5105cbb, 3 files: one `Facts`", size=13.5, anchor="start",
           weight="bold")
    # before: one private Facts and three hand-written lists
    s.text(sx + 14, sy + 54, "before", size=12.5, anchor="start", colour=t.dim)
    before = (("`Facts`, private", "done"), ("`DetailSheet` efficiency", "problem"),
              ("`DetailSheet` task facts", "problem"), ("`ByProcess` phone card", "problem"))
    for i, (name, fill) in enumerate(before):
        y = sy + 64 + i * 28
        s.page(sx + 14, y, 18, 22, fill=fill, lines=0)
        s.text(sx + 40, y + 16, name, size=12, anchor="start")
    s.arrow(sx + 222, sy + 120, sx + 262, sy + 120)
    s.text(sx + 280, sy + 54, "after", size=12.5, anchor="start", colour=t.dim)
    s.page(sx + 280, sy + 66, 40, 52, fill="done", lines=2)
    s.text(sx + 330, sy + 84, "`Facts`, exported,", size=12, anchor="start")
    s.text(sx + 330, sy + 104, "`variant` for the card", size=12, anchor="start", colour=t.dim)
    s.arrow(sx + 300, sy + 122, sx + 300, sy + 134)
    for i, name in enumerate(("`DetailSheet` x2", "`ByProcess`")):
        s.text(sx + 290, sy + 148 + i * 22, name, size=12, anchor="start")
    px = 6  # px per line, to scale
    bar(s, sx + 56, sy + 186, 27 * px, 16, "problem")
    s.text(sx + 14, sy + 199, "-27", size=13.5, anchor="start")
    bar(s, sx + 56, sy + 208, 8 * px, 16, "done")
    s.text(sx + 14, sy + 221, "+8", size=13.5, anchor="start")
    s.text(sx + 290, sy + 199, "Vitest 320 and `tsc`, before and after", size=12, anchor="start",
           colour=t.dim)
    s.text(sx + 290, sy + 219, "re-review approve, CR-P3B04-01 minor:", size=12, anchor="start",
           colour=t.dim)
    s.text(sx + 290, sy + 239, "`Facts` sits in `SlurmFacts.tsx`", size=12, anchor="start",
           colour=t.dim)

    s.prefix_key(50, H - 16, ("CR", "SEC"))
    s.text(W - 50, H - 16, "source: the bridges, `sacct.py`, `efficiency.py`, `state.py`, `failure.py`, "
           "`web/src/runs` at 5105cbb · review records P3-t33 to t35", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b04-dag-temp-efficiency")
