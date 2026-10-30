#!/usr/bin/env python3
"""The head script, the local launcher and the runner loop: step P3, P1 Task 9, 2026-10-30.

Writes docs/assets/diagrams/p3-t09-head-loop_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t09 at 78d409e:
- packages/spectio/src/spectio/runner/loop.py: RunnerLoop.tick leases `launch` and `cancel`
  commands from the sink and acks each; tick_s default 2; a launch whose `head.pid` or
  `head.exit` is there is adopted, never started twice; check_engine before submit; _read calls
  try_read_spool from the sink's cursor, a refused spool counted once; _report holds an ended
  head end_grace_s (default 60) for its last events, then head_report; _cancel writes the
  `.spectio/cancel` marker first, then launcher.cancel;
- runner/rundir.py: make_run_dirs creates `<run_id>/launch/.spectio/events` and `<run_id>/work`
  0700, one component at a time with O_NOFOLLOW; write_file: temp file 0600, fsync, rename;
- runner/headscript.py: write_launch_files writes params.json, spectio.config (Nextflow) or
  pylib (the Snakemake logger), and head.sh; _HEAD: umask 077, head.pid (pid, pgid, start time,
  boot ID, host), the cancel marker check (exit 143), `env -i` with KEEP, `bash -l -c` inner,
  output tee'd to head.out, head.exit (code, epoch); inner exports SPECTIO_* and NXF_* and,
  for Snakemake, PYTHONPATH with .spectio/pylib first; engine_env pins NXF_PLUGINS_DIR to the
  private nf-spectio copy and NXF_PLUGINS_DEFAULT to nf-spectio@0.0.1;
- runner/engines.py: unpack_nf_spectio copies nf-spectio-0.0.1 into NXF_PLUGINS_DIR (default
  NXF_HOME/plugins) once, refuses a copy group or others can write;
- runner/local.py: submit runs `bash head.sh` with start_new_session (setsid), stdin /dev/null,
  stderr to head.err; native ID `<pid>.<start time>`; poll: running while head.pid names a live
  process on this host and boot with the same start time and group; cancel: SIGTERM to the
  group, SIGKILL at the first poll after grace_s (default 60), each only after _is_head (the
  native ID, and the head leads its group) and alive, SIGKILL only to the head SIGTERM went to;
- packages/spectio-sdk/src/spectio_sdk/events.py: spool file `<producer>-<launch>-<nnnn>.jsonl`.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 960
COL = tuple(50 + i * 252 for i in range(6))  # six caption columns, 246 wide
TXT = 742  # the captions


def badge(s: Sketch, x: float, y: float, n: int) -> None:
    s.circle(x, y, 12, fill="gate")
    s.text(x, y + 5, str(n), size=14, weight="bold")


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=13.5, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def file(s: Sketch, x: float, y: float, name: str, fill: str) -> None:
    s.page(x, y, 32, 40, fill=fill, lines=2)
    s.text(x + 16, y + 58, f"`{name}`", size=12.5)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=93)
    t = theme
    s.heading(50, 58, "P3 Task 9 · the runner loop starts a head, watches it, and stops it",
              "`spectio.runner`: loop, local, headscript, rundir, engines · schedulers 3.1.1, "
              "dev-env 15.3 req. 10 and 11, architecture 13.8 · P1 Assumptions 4, 13, 15, 17, 21")

    # the server and the loop --------------------------------------------------------------------
    s.bucket(120, 214, 112, 100, fill="neutral")
    s.text(120, 272, "server", size=15)
    s.text(120, 346, "`runner_commands`", size=13, colour=t.dim)
    s.text(120, 366, "and the run store", size=13, colour=t.dim)

    s.envelope(232, 196, 42, 26, fill="input")
    s.text(253, 188, "`launch`", size=12.5, colour=t.dim)
    s.arrow(186, 232, 318, 232)
    badge(s, 300, 206, 1)
    s.arrow(318, 266, 186, 266)
    badge(s, 206, 292, 5)
    s.text(186, 318, "`ingest`, `head_report`", size=12.5, anchor="start", colour=t.dim)

    s.runner(330, 214, 170, 70, label="runner loop")
    s.text(415, 196, "a tick every 2 s", size=13, colour=t.dim)

    # the launch directory -----------------------------------------------------------------------
    s.folder(330, 410, 580, 236, fill="surface")
    s.text(348, 446, "`<runs_root>/run_ID/launch/.spectio/`", size=14, anchor="start")
    s.lock(636, 440, size=13, fill="done")
    s.text(652, 446, "0700", size=13, anchor="start", colour=t.dim)

    s.arrow(392, 296, 392, 404)
    badge(s, 372, 350, 2)
    s.text(410, 340, "writes", size=13, anchor="start", colour=t.dim)
    s.arrow(474, 404, 474, 296)
    badge(s, 494, 380, 5)
    s.text(410, 362, "reads", size=13, anchor="start", colour=t.dim)

    # row a: the loop's files, then the head's
    for i, (name, fill) in enumerate((("params.json", "input"), ("spectio.config", "input"),
                                      ("head.sh", "input"))):
        file(s, 352 + i * 96, 466, name, fill)
    for i, name in enumerate(("head.pid", "head.exit", "head.out")):
        file(s, 660 + i * 84, 466, name, "work")
    # row b: pylib, the cancel marker, the spool
    s.folder(346, 556, 56, 40, fill="input")
    s.text(374, 614, "`pylib/`", size=12.5)
    file(s, 446, 556, "cancel", "problem")
    s.folder(560, 546, 330, 76, fill="docs")
    s.text(578, 590, "`events/`", size=13, anchor="start")
    for i in range(3):
        s.page(668 + i * 44, 562, 30, 38, fill="surface", lines=2)
    s.text(800, 615, "`nf-spectio-1-0001.jsonl`", size=12)

    # what head.pid and head.exit hold
    s.text(560, 334, "`head.pid`: pid, group, start time, boot ID, host", size=13,
           anchor="start", colour=t.dim)
    s.text(560, 354, "`head.exit`: exit code, epoch", size=13, anchor="start", colour=t.dim)

    # legend
    for i, (fill, label) in enumerate((("input", "the loop writes"), ("work", "the head writes"),
                                       ("docs", "the engine writes"), ("problem", "cancel marker"))):
        x = 340 + i * 146
        s.poly([(x, 664), (x + 16, 664), (x + 16, 680), (x, 680)], fill=fill, amount=0.3)
        s.text(x + 24, 677, label, size=12.5, anchor="start", colour=t.dim)

    # the private nf-spectio copy -----------------------------------------------------------------
    s.folder(56, 452, 150, 80, fill="input", label="`nf-spectio-0.0.1`")
    s.lock(198, 530, size=12, fill="done")
    s.text(130, 556, "`$NXF_PLUGINS_DIR`", size=12.5, colour=t.dim)
    s.text(130, 575, "unpacked once, kept", size=12.5, colour=t.dim)
    s.text(130, 594, "only you can write it", size=12.5, colour=t.dim)
    s.arrow(376, 294, 204, 444, dashed=True)

    # the head's session -------------------------------------------------------------------------
    zx, zy, zw, zh = 990, 140, 560, 330
    s.shade(zx, zy, zw, zh, fill="work", opacity=0.3, colour=t.muted, dashed=True)
    s.text(zx + 18, zy + 24, "its own session and process group, led by the head", size=13.5,
           anchor="start", colour=t.dim)

    s.cog(zx + 34, 214, 10, fill="work")
    s.text(zx + 58, 220, "`bash head.sh`, the head", size=15, anchor="start")
    s.text(zx + 58, 241, "umask 077, writes `head.pid`, checks `cancel`", size=12.5,
           anchor="start", colour=t.dim)
    s.arrow(zx + 34, 252, zx + 34, 284)
    s.cog(zx + 34, 304, 10, fill="work")
    s.text(zx + 58, 300, "`env -i` keeps HOME USER LOGNAME SHELL LANG TMPDIR,", size=12.5,
           anchor="start", colour=t.dim)
    s.text(zx + 58, 320, "then `bash -l -c`: the login profile, then the exports", size=14,
           anchor="start")
    s.arrow(zx + 34, 330, zx + 34, 356)

    s.chip(zx + 18, 362, 236, "`nextflow run`", fill="work")
    s.text(zx + 272, 388, "or", size=14, colour=t.dim)
    s.chip(zx + 290, 362, 236, "`snakemake --logger spectio`", fill="work")
    s.text(zx + 136, 424, "nf-spectio from its private copy:", size=12.5, colour=t.dim)
    s.text(zx + 136, 443, "`NXF_PLUGINS_DIR`, never the registry", size=12.5, colour=t.dim)
    s.text(zx + 408, 424, "`PYTHONPATH`: `.spectio/pylib`", size=12.5, colour=t.dim)
    s.text(zx + 408, 443, "first, then the profile's own", size=12.5, colour=t.dim)

    # 3 and 6, loop to head
    s.arrow(504, 232, zx + 16, 214)
    badge(s, 540, 206, 3)
    s.text(560, 212, "`bash head.sh`, setsid, stdin `/dev/null`", size=13, anchor="start")
    s.arrow(504, 268, zx - 4, 268, colour=t.accent)
    badge(s, 540, 294, 6)
    s.text(560, 290, "SIGTERM, then SIGKILL, to the group", size=13, anchor="start",
           colour=t.accent)
    s.magnifier(570, 310, 6)
    s.text(588, 314, "only if `head.pid` still names `<pid>.<start>`", size=12.5, anchor="start",
           colour=t.dim)

    # 4, head and engine to the files
    s.arc(zx + 22, 236, 846, 460, lift=40)
    s.arrow(zx - 4, 460, 896, 574)
    badge(s, 958, 452, 4)

    # cancel, to scale --------------------------------------------------------------------------
    x0, px_s, ay = 1010, 7.5, 600  # 7.5 px per second
    s.text(zx, 514, "cancel, to scale: the default 60 s grace, a poll every 2 s", size=13.5,
           anchor="start")
    s.shade(x0, ay - 16, 60 * px_s, 32, fill="gate", opacity=0.7)
    s.line(x0 - 6, ay, x0 + 64 * px_s, ay, width=1.6, amount=0.6, passes=1)
    for k in range(33):
        s.line(x0 + k * 2 * px_s, ay - 5, x0 + k * 2 * px_s, ay + 5, width=1.1, amount=0.2,
               passes=1, colour=t.dim)
    s.arrow(x0, ay - 46, x0, ay - 18, colour=t.accent)
    s.text(x0 + 8, ay - 34, "SIGTERM", size=13, anchor="start", colour=t.accent)
    s.text(x0 + 225, ay + 30, "the engine stops its tasks", size=12.5, colour=t.dim)
    kill = x0 + 60 * px_s
    s.arrow(kill, ay - 46, kill, ay - 18, colour=t.accent)
    s.text(kill - 8, ay - 34, "SIGKILL if it still lives", size=13, anchor="end",
           colour=t.accent)
    s.text(x0, ay + 30, "0 s", size=12.5, colour=t.dim)
    s.text(kill, ay + 30, "60 s, next poll", size=12.5, colour=t.dim)

    # captions ------------------------------------------------------------------------------------
    s.line(30, TXT - 40, W - 30, TXT - 40, dashed=True, colour=t.muted)
    captions = (
        ("the loop leases", ("`launch` and `cancel` commands,",
                             "each acked, ok or with its error",
                             "the engine is checked through",
                             "`bash -l`: missing or too old fails",
                             "`head.pid` there: adopted, not",
                             "started a second time")),
        ("run dirs and head.sh", ("`.spectio/events` and `work`, 0700,",
                                  "opened without following links",
                                  "files 0600: temp, fsync, rename",
                                  "params go in a file, never in",
                                  "shell words; nf-spectio unpacked",
                                  "or the logger copied to `pylib`")),
        ("the head starts", ("its own session through setsid,",
                             "so it outlives the server",
                             "native ID `<pid>.<start time>`",
                             "the login profile runs, then",
                             "Spectio's exports, so the profile",
                             "cannot move the plugin or `pylib`")),
        ("what the run leaves", ("the engine appends to `events/`",
                                 "the head writes `head.pid` first,",
                                 "copies the output to `head.out`,",
                                 "and writes `head.exit` once the",
                                 "engine has ended: never before",
                                 "")),
        ("poll and read", ("`try_read_spool` from the cursor,",
                           "a refused spool counted once",
                           "running: `head.pid` names a live",
                           "process, same host, boot and start",
                           "ended: 60 s more for its last events,",
                           "then `head_report` to the server")),
        ("cancel", ("the `cancel` marker first: a head",
                    "not yet started never runs the engine",
                    "each signal only if `head.pid` is",
                    "`<pid>.<start>`, leads its group,",
                    "on this host and boot; SIGKILL",
                    "only to the head SIGTERM reached")),
    )
    for i, (title, rows) in enumerate(captions):
        x = COL[i]
        s.step(x + 123, TXT, i + 1, title)
        lines(s, x, TXT + 32, tuple(r for r in rows if r))

    s.text(W - 50, H - 18, "source: spectio/runner/loop.py, local.py, headscript.py, rundir.py, "
           "engines.py · defaults tick 2 s, cancel grace 60 s, end grace 60 s · P1 Task 9 at 78d409e",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t09-head-loop")
