#!/usr/bin/env python3
"""Figure for step APPLY7: each job's files, and the run tools added to 0.0.1.

Writes docs/assets/diagrams/apply7_run_tools_{light,dark}.{svg,png}.

Sources: architecture-plugins-and-packaging.md §13.7 (revised 2026-10-28: the work-directory files,
SLURM log paths, failure reason, resources), api-and-data-model.md (Job files, Results, Resume, Copy to a
new launch), dev-environment-and-testing.md §15.1 and §15.3 requirements 13-16, decision log 2026-10-28,
inbox #70. Memory and time values are those of the LiteRunFailed board's fixture (bwa_mem, WGS-07);
the 143 of 175 jobs are its counts.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 1010


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=70)
    t = theme

    s.heading(40, 52, "APPLY7 · 0.0.1 shows each job's files, and gains resume, failure summary, "
                      "results, copy and resources",
              "Thomas's decision of 2026-10-28 · architecture §13.7 · api Job files · dev-env §15.3 req. 13-16")

    # -- before · what 5e2493e showed ---------------------------------------------------------------
    y = 96
    s.text(40, y + 22, "before (5e2493e)", size=15, anchor="start", weight="bold", colour=t.dim)
    for i, tab in enumerate(("head output", "head errors", "engine log")):
        s.frame(200 + i * 150, y + 2, 136, 32, fill="neutral")
        s.text(268 + i * 150, y + 23, tab, size=12.5, colour=t.dim)
    s.text(668, y + 23, "work dir: a path to copy, no files shown", size=13, anchor="start", colour=t.dim)
    s.text(1600, y + 23, "after: every job's own files, below", size=13, anchor="end", colour=t.dim)
    s.line(40, y + 52, W - 40, y + 52, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- A · each job's files -----------------------------------------------------------------------
    y = 180
    s.text(40, y + 20, "A · job files", size=18, anchor="start", weight="bold")
    s.hpc_node(40, y + 50, w=60, h=84, busy=3)
    s.text(70, y + 160, "SLURM job", size=12.5, colour=t.dim)
    s.arrow(112, y + 92, 160, y + 92)
    s.folder(170, y + 40, 330, 190, fill="input")
    s.text(186, y + 76, "work/9d/77c214…  (Nextflow)", size=13, anchor="start", weight="bold")
    files = (".command.log   SLURM output, opens first", ".command.err · .command.out",
             ".command.sh · .command.run  «hidden» values", ".exitcode · .command.trace")
    for i, f in enumerate(files):
        s.text(186, y + 104 + i * 24, f, size=12.5, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.text(186, y + 212, "Snakemake: .snakemake/slurm_logs/rule_<r>/…/<id>.log",
           size=12, anchor="start", colour=t.dim)
    s.arrow(510, y + 130, 570, y + 130)
    s.cog(600, y + 130, 16, fill="work")
    s.lock(640, y + 130, 11)
    for i, line in enumerate(("confined reads (req. 13):", "openat walk, no symlink out", "of the run or work directory;",
                              "names from an allow-list;", "last 64 KiB, 1 MiB at most")):
        s.text(664, y + 100 + i * 20, line, size=13, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.arrow(860, y + 130, 910, y + 130)
    s.browser(920, y + 40, 420, 200, url="runs/7T9V1W · Tasks")
    s.frame(1140, y + 76, 190, 156, fill="surface")
    s.text(1235, y + 98, "Files · attempt 1", size=13, weight="bold")
    for i, tab in enumerate((".log", ".err", ".out", ".sh", ".run")):
        s.text(1152 + i * 36, y + 122, tab, size=11.5, anchor="start", colour=t.ink if i == 0 else t.dim)
    s.terminal(1150, y + 132, 170, 90, ("…Killed", "oom_kill event"), size=11, line_h=18)
    s.text(1020, y + 120, "drawer on desktop,", size=12.5, colour=t.dim)
    s.text(1020, y + 140, "sheet on the phone,", size=12.5, colour=t.dim)
    s.text(1020, y + 160, "focus back on Files", size=12.5, colour=t.dim)
    s.phone(1380, y + 40, 110, 200)
    s.shade(1388, y + 140, 94, 78, fill="docs", opacity=0.9)
    s.text(1435, y + 168, "Files sheet", size=12, colour=t.dim)
    s.text(1440, y + 268, "run logs: .spectio/nextflow.log (NXF_LOG_FILE), the head's output and errors",
           size=12.5, anchor="end", colour=t.dim)

    s.line(40, y + 290, W - 40, y + 290, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- B2 and B5 · failure summary and resources ---------------------------------------------------
    y = 490
    s.text(40, y + 20, "B2 · why it failed", size=18, anchor="start", weight="bold")
    s.text(40, y + 44, "B5 · resources per task", size=18, anchor="start", weight="bold")
    s.terminal(40, y + 64, 520, 120, (
        "SLURM-job '48731209' failed, SLURM status is:",
        "'OUT_OF_MEMORY'   (Snakemake SLURM plugin)",
        "sacct  → ReqMem, MaxRSS, Elapsed, Timelimit",
    ), size=12)
    s.text(40, y + 204, "Nextflow: sacct per failed attempt; Snakemake: batch", size=13, anchor="start")
    s.text(40, y + 224, "one limiter: 1 call in flight, 60 s apart, 100 IDs a call; fetched when", size=13,
           anchor="start", colour=t.dim)
    s.text(40, y + 244, "first opened, cached in .spectio/sacct.json; off with accounting = false (req. 15)",
           size=13, anchor="start", colour=t.dim)
    s.arrow(570, y + 124, 630, y + 124)
    # to scale: 25 px per GB, 75 px per hour
    bx = 760
    s.text(bx - 14, y + 82, "memory", size=13.5, anchor="end")
    s.frame(bx, y + 66, 16 * 25, 26, fill="neutral")
    s.shade(bx, y + 66, 16.0 * 25, 26, fill="problem", opacity=0.9)
    s.text(bx + 16 * 25 + 12, y + 84, "16 GB asked · 16.0 GB used", size=13, anchor="start")
    s.text(bx - 14, y + 132, "time", size=13.5, anchor="end")
    s.frame(bx, y + 116, 4 * 75, 26, fill="neutral")
    s.shade(bx, y + 116, 1.2 * 75, 26, fill="bar_blue", opacity=0.9)
    s.text(bx + 4 * 75 + 12, y + 134, "4 h limit · 1 h 12 used", size=13, anchor="start")
    s.text(bx, y + 180, "bwa_mem (sample=WGS-07), attempt 2 of 2 · OUT_OF_MEMORY · exit 0:125", size=13,
           anchor="start")
    s.text(bx, y + 202, "the same columns on every task row: CPUs, CPU %, memory, peak memory, time limit",
           size=12.5, anchor="start", colour=t.dim)
    s.warning(1500, y + 80)
    s.text(1500, y + 112, "near limit", size=12.5, colour=t.dim)

    s.line(40, y + 260, W - 40, y + 260, width=1, amount=0.3, passes=1, colour=t.muted)

    # -- B1, B3, B4 ---------------------------------------------------------------------------------
    y = 780
    s.text(40, y + 20, "B1 · Resume", size=18, anchor="start", weight="bold")
    s.frame(40, y + 40, 200, 56, fill="problem")
    s.text(140, y + 64, "wgs-cohort-12", size=13.5, weight="bold")
    s.text(140, y + 84, "Failed, stays Failed", size=12.5, colour=t.dim)
    s.arrow(248, y + 68, 300, y + 68)
    s.frame(310, y + 40, 200, 56, fill="input")
    s.text(410, y + 64, "child run", size=13.5, weight="bold")
    s.text(410, y + 84, "same launch directory", size=12.5, colour=t.dim)
    # to scale: 2 px per job
    s.shade(40, y + 116, 143 * 2, 22, fill="cached", opacity=1)
    s.shade(40 + 143 * 2 + 4, y + 116, 32 * 2, 22, fill="recomputed", opacity=1)
    s.text(40, y + 160, "143 jobs reused · 32 run again", size=13, anchor="start", colour=t.dim)
    s.text(40, y + 182, "-resume, or --rerun-incomplete (req. 16)", size=13, anchor="start", colour=t.dim)

    s.text(600, y + 20, "B3 · results and reports", size=18, anchor="start", weight="bold")
    s.folder(600, y + 40, 150, 90, fill="yellow", label="--outdir")
    s.arrow(758, y + 86, 808, y + 86)
    s.browser(816, y + 40, 230, 120, url="multiqc_report.html")
    s.lock(1020, y + 120, 10)
    s.text(600, y + 182, "read-only; HTML in Spectio's report viewer, a sandboxed iframe (req. 14)", size=13,
           anchor="start", colour=t.dim)

    s.text(1110, y + 20, "B4 · copy", size=18, anchor="start", weight="bold")
    s.page(1110, y + 40, 120, 100, fill="docs", lines=3)
    s.text(1170, y + 158, "command, params", size=12.5, colour=t.dim)
    s.arrow(1240, y + 90, 1290, y + 90)
    s.frame(1300, y + 40, 300, 100, fill="surface")
    s.text(1450, y + 68, "Launch", size=14, weight="bold")
    s.text(1450, y + 92, "Prefilled from wgs-cohort-12 (F5KZNW)", size=12.5, colour=t.dim)
    s.button(1360, y + 104, 180, "Clear and start empty", fill="neutral", h=28)
    s.text(1110, y + 182, "Copy to a new launch: a fresh run, its own directory", size=13, anchor="start",
           colour=t.dim)

    s.text(40, H - 24, "Sources: architecture §13.7 (revised 2026-10-28); api Job files, Results, Resume, Copy; "
                       "dev-env §15.1, §15.3 req. 13-16; decision log 2026-10-28; inbox #70; LiteRunFailed fixture "
                       "· tools/diagrams/apply7_run_tools.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "apply7_run_tools")
