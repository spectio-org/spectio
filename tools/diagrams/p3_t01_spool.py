#!/usr/bin/env python3
"""The spool event contract of driven runs: step P3, P1 Task 1, 2026-10-29.

Writes docs/assets/diagrams/p3-t01-spool_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t01 at b730180:
- docs/specs/api-and-data-model.md 14.1: SPECTIO_RUN_ID, SPECTIO_LAUNCH_N and SPECTIO_SPOOL_DIR from the head
  script; files <producer>-<launch>-<nnnn>.jsonl in <launch dir>/.spectio/events/, UTF-8, append-only, one JSON
  object per line, read in name order; the envelope keys v, id, run, launch, producer, seq, time, type, data and
  no other; seq increases within one (run, launch, producer); the allow-lists and the fields never stored;
  snakemake.error keeps msg with the quoted command hidden; error texts cut at 4096 characters; the reader's
  drop reasons invalid, line_too_large, file_too_large, wrong_run, symlink;
- packages/spectio-sdk/src/spectio_sdk/events.py: MAX_LINE_BYTES 65536, ROTATE_BYTES 33554432,
  MAX_FILE_BYTES 67108864, MAX_MESSAGE_CHARS 4096;
- the bridges that write the spool are P1 Tasks 6 and 7; the reader that drops and counts is P1 Task 3
  (docs/plans/P1-walking-skeleton.md);
- spikes/engine-events/fixtures/: 15 captures, 6 Nextflow plugin, 3 Snakemake, 6 Tower protocol;
  tests/fixtures/engine-events/: 9 spool files, `wc -l` 2375 lines;
- `uv run --locked pytest -v`: 38 passed in 0.38s; `lint-imports`: 3 kept, 0 broken (re-run 2026-10-29).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 960


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=71)
    t = theme
    s.heading(50, 58, "P3 Task 1 · the spool event contract of driven runs",
              "`spectio_sdk.events`, api 14.1 · the bridges append to files, the runner reads them; "
              "nothing posts over the network in 0.0.1")

    # 1 -- a bridge appends ---------------------------------------------------------------
    x1 = 50
    s.hpc_node(x1 + 4, 140, 60, 80, busy=2, slots=4)
    s.text(x1 + 82, 160, "the engine's head process", size=15, anchor="start", weight="bold")
    s.text(x1 + 82, 183, "Nextflow with `nf-spectio`, or", size=14, anchor="start")
    s.text(x1 + 82, 204, "Snakemake with its logger plugin", size=14, anchor="start")
    s.text(x1 + 82, 226, "the bridges come in Tasks 6 and 7", size=13, anchor="start", colour=t.dim)
    s.terminal(x1, 250, 330, 112, ("SPECTIO_RUN_ID=run_01JD8X…", "SPECTIO_LAUNCH_N=2",
                                   "SPECTIO_SPOOL_DIR=…/.spectio/events"), size=12.5)
    s.text(x1, 388, "set by the head script", size=13.5, anchor="start", colour=t.dim)
    s.arrow(x1 + 340, 300, x1 + 384, 300)
    s.step(x1 + 165, 510, 1, "a bridge appends")

    # 2 -- the spool files --------------------------------------------------------------------
    x2 = 440
    s.folder(x2, 136, 320, 236, fill="yellow")
    s.text(x2 + 16, 172, "`<launch dir>/.spectio/events/`", size=14, anchor="start")
    files = (("`nf-spectio-1-0001.jsonl`", "launch 1, full at 32 MiB", "done"),
             ("`nf-spectio-1-0002.jsonl`", "launch 1, after rotation", "done"),
             ("`nf-spectio-2-0001.jsonl`", "launch 2: `seq` starts at 1", "input"))
    for i, (name, note, fill) in enumerate(files):
        fy = 190 + i * 58
        s.page(x2 + 16, fy, 30, 40, fill=fill, lines=2)
        s.text(x2 + 58, fy + 17, name, size=13, anchor="start")
        s.text(x2 + 58, fy + 36, note, size=13, anchor="start", colour=t.dim)
    s.text(x2, 400, "UTF-8, append-only, one JSON object per line", size=13.5, anchor="start")
    s.text(x2, 422, "a line is at most 64 KiB; a file rotates at 32 MiB;", size=13.5, anchor="start", colour=t.dim)
    s.text(x2, 444, "the reader ignores what lies past 64 MiB in a file", size=13.5, anchor="start", colour=t.dim)
    s.arrow(x2 + 330, 300, x2 + 372, 300)
    s.step(x2 + 160, 510, 2, "the spool, in the launch directory")

    # 3 -- the envelope -------------------------------------------------------------------
    x3 = 822
    s.envelope(x3, 140, 84, 56, fill="input")
    s.text(x3 + 100, 162, "one line, one envelope", size=15, anchor="start", weight="bold")
    s.text(x3 + 100, 184, "exactly these 9 keys", size=13.5, anchor="start", colour=t.dim)
    keys = (("`v`", "1"), ("`id`", "`evt_` and a ULID"), ("`run`", "`run_` and a ULID"),
            ("`launch`", "1, 2, and so on"), ("`producer`", "`nf-spectio/<version>`"),
            ("`seq`", "counts up per run, launch, producer"), ("`time`", "an RFC 3339 string"),
            ("`type`", "`nextflow.<hook>`, `snakemake.<event>`"), ("`data`", "the hook's fields"))
    for i, (k, rule) in enumerate(keys):
        ky = 226 + i * 22
        s.text(x3, ky, k, size=13.5, anchor="start")
        s.text(x3 + 84, ky, rule, size=13, anchor="start", colour=t.dim)
    s.cross(x3 + 6, 432, size=6)
    s.text(x3 + 20, 437, "another key: the line is invalid", size=13.5, anchor="start")
    s.text(x3 + 20, 459, "strict: 64-bit integers, no NaN, no NUL", size=13.5, anchor="start", colour=t.dim)
    s.arrow(x3 + 322, 300, x3 + 360, 300)
    s.step(x3 + 160, 510, 3, "the envelope")

    # 4 -- one allow-list per type ----------------------------------------------------------
    x4 = 1196
    s.page(x4 + 12, 132, 40, 50, fill="input", lines=3)
    s.arrow(x4 + 32, 186, x4 + 32, 204)
    s.poly([(x4, 208), (x4 + 64, 208), (x4 + 40, 238), (x4 + 40, 258), (x4 + 24, 258), (x4 + 24, 238)],
           fill="neutral")
    s.arrow(x4 + 32, 262, x4 + 32, 282)
    s.tick(x4 + 32, 294, size=7)
    s.text(x4 + 80, 158, "one allow-list per type", size=15, anchor="start", weight="bold")
    s.text(x4 + 80, 181, "other keys in `data` are dropped", size=13.5, anchor="start", colour=t.dim)
    s.text(x4 + 80, 202, "when the line is parsed,", size=13.5, anchor="start", colour=t.dim)
    s.text(x4 + 80, 223, "before anything is stored", size=13.5, anchor="start", colour=t.dim)
    s.text(x4 + 80, 258, "kept, for example:", size=13.5, anchor="start")
    s.text(x4 + 80, 279, "`taskId` `status` `exitStatus`", size=13.5, anchor="start")
    s.cross(x4 + 6, 320, size=6)
    s.text(x4 + 20, 325, "never stored, whoever sends them:", size=13.5, anchor="start")
    s.text(x4 + 20, 346, "`script` `env` `homeDir` `commandLine`", size=13, anchor="start")
    s.text(x4 + 20, 366, "`configText` `cmd` `shellcmd` `rule_msg`", size=13, anchor="start")
    s.text(x4, 400, "`snakemake.error` keeps its text, the command hidden:", size=13.5, anchor="start")
    s.text(x4, 422, "`Command «hidden» returned non-zero exit status 1.`", size=12.5, anchor="start")
    s.text(x4, 446, "error texts are cut at 4096 characters", size=13.5, anchor="start", colour=t.dim)
    s.step(x4 + 180, 510, 4, "what is kept")

    # 5 -- the reader (Task 3) drops and counts --------------------------------------------
    ry = 560
    s.shade(50, ry, 960, 330, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.text(70, ry + 32, "the reader, built in Task 3; the contract above fixes what it checks",
           size=15, anchor="start", weight="bold")
    s.runner(80, ry + 92, 150, 66, label="runner")
    s.text(155, ry + 192, "inside `spectio serve`,", size=13.5, colour=t.dim)
    s.text(155, ry + 212, "reads the files in name order", size=13.5, colour=t.dim)
    s.arrow(244, ry + 125, 300, ry + 125)
    reasons = ("`invalid`", "`line_too_large`", "`file_too_large`", "`wrong_run`", "`symlink`")
    for i, r in enumerate(reasons):
        cx = 360 + i * 140
        s.bucket(cx, ry + 100, 72, 56, fill="problem")
        s.text(cx, ry + 182, r, size=13)
    s.text(640, ry + 212, "a counter per reason, kept with the reader's cursor", size=13.5, colour=t.dim)
    s.text(70, ry + 254, "a line that is not JSON, fails the envelope or the allow-list, has an unknown type,",
           size=13.5, anchor="start")
    s.text(70, ry + 276, "is too long, lies past 64 MiB, names another run or sits in a symbolic link is dropped;",
           size=13.5, anchor="start")
    s.text(70, ry + 298, "the next line is read. Nothing in an event is executed; its paths are only names under "
           "the run root.", size=13.5, anchor="start", colour=t.dim)
    s.step(530, ry + 362, 5, "dropped and counted, never executed")

    # evidence: the T2 captures, to scale, and the tests ------------------------------------
    ex = 1060
    s.text(ex, ry + 32, "spike T2 captures, one cell each", size=15, anchor="start", weight="bold")
    s.task_strip(ex, ry + 52, ((6, "input", "Nextflow plugin"), (3, "work", "Snakemake"),
                               (6, "neutral", "Tower protocol")), cell=24, gap=4, h=30, label_size=12.5)
    s.text(ex, ry + 140, "9 converted to spool files by `convert_t2.py`:", size=13.5, anchor="start")
    s.text(ex, ry + 161, "2375 lines, every one parses", size=13.5, anchor="start")
    s.text(ex, ry + 183, "the 6 Tower captures are not spool events", size=13.5, anchor="start", colour=t.dim)
    s.terminal(ex, ry + 206, 470, 112, ("$ uv run --locked pytest -v", "38 passed in 0.38s",
                                        "ruff, mypy, lint-imports: clean, 3 kept"), size=12.5)
    s.text(ex + 235, ry + 344, "the same checks run in the new CI job `product`", size=13.5, colour=t.dim)

    s.text(W - 50, H - 16, "source: spectio_sdk/events.py · api-and-data-model.md 14.1 · "
           "tests/fixtures/engine-events/ · P1 Tasks 1, 3, 6, 7", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t01-spool")
