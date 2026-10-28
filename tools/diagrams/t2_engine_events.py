#!/usr/bin/env python3
"""Engine event capture (golden fixtures): spike T2, 2026-10-28.

Writes docs/assets/diagrams/t2-engine-events_{light,dark}.{svg,png}.

Every number comes from docs/research/spike-engine-events-2026-10-28.md and the fixtures under
spikes/engine-events/fixtures/ (branch spike/engine-events):
- Snakemake 9.27.1, logger plugin `spectio`: flaky run 469 records; the checkpoint grows the total
  from 32 to 67 jobs; a retried job is re-announced with the same jobid (103, 104);
- Nextflow 26.10.4 and 25.10.9, Tower observer and nf-spectio in the same run: same run name and
  session ID in all 6 runs; flaky run on 26.10.4: 10 Tower requests (create, begin, 7 progress,
  complete) and 306 plugin events; 67 task IDs on both sides;
- the last onTaskComplete of a process arrives after its onProcessTerminate (every run, both versions).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1780, 1000


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=43)
    t = theme
    s.heading(50, 58, "T2 · What the engines send, captured as golden fixtures",
              "synthetic pipelines, local executor · Snakemake 9.27.1 · Nextflow 26.10.4 and 25.10.9 · "
              "a failed task, a retry, a resume or rerun")

    # == lane geometry ==================================================================================
    ex, ox, cx, fx = 120, 520, 1010, 1420   # engine, observer, capture server, fixtures
    ny, sy = 230, 640                       # Nextflow lane, Snakemake lane

    # -- engines (terminals) ------------------------------------------------------------------------
    s.terminal(ex - 70, ny - 50, 250, 96, ("$ nextflow run main.nf", "  -with-tower", "  -plugins nf-spectio"), size=12.5)
    s.text(ex + 55, ny + 72, "Nextflow 26.10.4, 25.10.9", size=14, colour=t.dim)
    s.terminal(ex - 70, sy - 50, 250, 96, ("$ snakemake", "  --logger spectio", "  --retries 2"), size=12.5)
    s.text(ex + 55, sy + 72, "Snakemake 9.27.1", size=14, colour=t.dim)

    # -- observers inside the engine process ---------------------------------------------------------
    s.arrow(ex + 190, ny - 20, ox - 70, ny - 80)
    s.arrow(ex + 190, ny + 20, ox - 70, ny + 80)
    s.cog(ox - 40, ny - 92, 15, fill="work")
    s.text(ox - 14, ny - 86, "nf-tower observer", size=15, anchor="start", weight="bold")
    s.text(ox - 14, ny - 64, "create · begin · progress · complete", size=12.5, anchor="start", colour=t.dim)
    s.cog(ox - 40, ny + 80, 15, fill="docs")
    s.text(ox - 14, ny + 86, "nf-spectio (TraceObserverV2)", size=15, anchor="start", weight="bold")
    s.text(ox - 14, ny + 108, "one POST per hook, built without Gradle", size=12.5, anchor="start", colour=t.dim)
    s.link(ox + 70, ny + 4, 16, colour=t.good)
    s.text(ox + 92, ny + 10, "same run name + session ID, 6 of 6 runs", size=13.5, anchor="start", colour=t.good)

    s.arrow(ex + 190, sy, ox - 70, sy)
    s.cog(ox - 40, sy, 15, fill="docs")
    s.text(ox - 14, sy + 6, "logger plugin `spectio`", size=15, anchor="start", weight="bold")
    s.text(ox - 14, sy + 28, "every LogRecord as one JSON line", size=12.5, anchor="start", colour=t.dim)

    # -- capture server ------------------------------------------------------------------------------
    s.arrow(ox + 250, ny - 80, cx - 60, ny - 10)
    s.arrow(ox + 250, ny + 80, cx - 60, ny + 10)
    s.envelope(cx - 50, ny - 30, 100, 64, fill="input")
    s.text(cx, ny + 64, "capture server", size=15, weight="bold")
    s.text(cx, ny + 84, "Python stdlib, logs every body", size=12.5, colour=t.dim)
    s.text(cx, ny + 104, "`/trace/*` and `/spectio/events`", size=12.5, colour=t.dim)

    s.arrow(ox + 250, sy, cx - 60, sy)
    s.page(cx - 26, sy - 34, 52, 66, fill="input")
    s.text(cx, sy + 58, "`$SPECTIO_EVENTS` file", size=14, weight="bold")

    # -- normalise -> fixtures -------------------------------------------------------------------------
    s.arrow(cx + 70, ny, fx - 60, ny)
    s.arrow(cx + 70, sy, fx - 60, sy)
    s.bucket(fx - 120 + 60, (ny + sy) / 2 - 40, 90, 60, fill="work")
    s.text(fx - 60, (ny + sy) / 2 + 42, "normalise:", size=13, colour=t.dim)
    s.text(fx - 60, (ny + sy) / 2 + 60, "paths, host, user, token", size=13, colour=t.dim)
    # the normaliser sits on both capture -> fixture flows
    s.arrow(fx - 60, (ny + sy) / 2 - 48, fx - 60, ny + 12, dashed=True)
    s.arrow(fx - 60, (ny + sy) / 2 + 72, fx - 60, sy - 12, dashed=True)
    for i, (y, n, label) in enumerate(((ny - 40, 12, "12 Nextflow fixtures"), (sy - 40, 3, "3 Snakemake fixtures"))):
        s.folder(fx, y, 54, 40, fill="done")
        s.task_strip(fx + 66, y + 10, ((n, "done", ""),), cell=12, gap=4, h=20)
        s.text(fx, y + 66, label, size=14, anchor="start")
    s.text(fx, ny + 50, "tower + plugin × flaky, tool error, resume", size=12.5, anchor="start", colour=t.dim)
    s.text(fx, sy + 50, "checkpoint + retry, tool error, rerun", size=12.5, anchor="start", colour=t.dim)
    s.step(780, 455, 1, "both engines report from the main process; we keep every payload")

    # == what differed from the specs (bottom band) ==================================================
    by = 790
    s.text(50, by, "differences that change a spec", size=15.5, anchor="start", weight="bold")
    items = (
        ("warning", "last `onTaskComplete` of a process arrives after its `onProcessTerminate`",
         "checking-scenarios §11.5: end of stage needs both"),
        ("warning", "Snakemake: no attempt number, no exit code in `job_error`",
         "synthesis §2ter retries row; exit code only in the error text"),
        ("warning", "checkpoint: total grows 32 → 67 through `progress`, no DAG event",
         "matches §2ter; two untyped messages per checkpoint"),
    )
    for i, (_, head, sub) in enumerate(items):
        x = 50 + i * 570
        s.warning(x + 12, by + 42, size=11)
        s.text(x + 34, by + 47, head, size=13.5, anchor="start")
        s.text(x + 34, by + 68, sub, size=12.5, anchor="start", colour=t.dim)
    s.step(890, 905, 2, "every difference is listed in the research note; TRIAGE3 decides the spec changes")

    s.text(W - 50, H - 20, "source: docs/research/spike-engine-events-2026-10-28.md · "
           "spikes/engine-events/fixtures/", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t2-engine-events")
