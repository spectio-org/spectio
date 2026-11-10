#!/usr/bin/env python3
"""Named documentation screenshots: one registry, one command per shot.

The pattern is depictio's dev/playwright_debug/docs_screenshots.py (MIT,
0d1aa0a): a REGISTRY of named shots, `list` and `run`, a fixed viewport, and
light/dark WebP pairs embedded with #only-light / #only-dark.

During the design phase the shots are the UI canvas boards, rendered by
tools/canvas/render.js. Once the app exists, a shot's `render` switches to a
Playwright session against a running instance (same names, same files), so the
docs pages that embed them do not change.

    python3 tools/media/shots.py list
    python3 tools/media/shots.py run --shot review-gate
    python3 tools/media/shots.py run --all --theme light

The boards have no dark variant yet, so `--theme dark` is skipped for them
(the page then embeds the light file without a #only-light suffix).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sanitize  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "assets" / "shots"
BOARDS = REPO / "design" / "ui-canvas"


@dataclass(frozen=True)
class Shot:
    name: str
    board: str  # design/ui-canvas/<board>.dc.html
    width: int
    height: int
    caption: str
    clicks: tuple[str, ...] = ()  # CSS selectors clicked before the capture
    themes: tuple[str, ...] = ("light",)  # boards: light only for now; live screens: both
    live: tuple[str, ...] | None = None  # a live page: steps of live.js; `board` is its path


# P3 UI parity D: the pipeline is picked from "Try a test pipeline" (the server's recent runs), and the
# copy's nextflow_schema.json builds the form; before, the path was typed and a parameter added by hand.
APP_LAUNCH = ("wait:Try a test pipeline", "click:Use Test pipeline (Nextflow), $SPECTIO_DEMO_PIPELINE",
              "wait:form from nextflow_schema.json")

# P1 Task 32: Launch checks each value before sending. `scale` has "minimum": 1, so 0 shows its error.
APP_LAUNCH_CHECKED = APP_LAUNCH + ("open:Scenario", "fill:scale=0", "wait:Must be at least 1", "view:Must be at least 1")

# The synthetic Snakemake pipeline (tests/pipelines/synthetic/snakemake) copied to
# $SPECTIO_DEMO_SMK_PIPELINE (tools/media/README.md, live shots). Its schema (workflow/schemas) names four
# groups, each a folded section; two are opened and one value is set. The nested map `ref` of the demo
# config.yaml is not in that schema, so the form no longer shows a dotted-key section (DW-P3B11-01 follow-up).
APP_LAUNCH_SMK = ("fill:Pipeline=$SPECTIO_DEMO_SMK_PIPELINE", "click:Load", "wait:Config preview, as YAML",
                  "open:Input/output options", "open:Scenario", "fill:outdir=results-smk")

# The report viewer, on the MultiQC fixture (tests/fixtures/results/multiqc-1.35_custom_content_report.html.gz).
REPORT_VIEWER = ("wait:Untrusted report", "frame:/data/demo/mqc/in")

REGISTRY: dict[str, Shot] = {
    s.name: s
    for s in (
        Shot("run-detail", "RunDetail", 1440, 1180, "A running nf-core/rnaseq run: stages, gates, busiest processes, lineage"),
        Shot("review-gate", "Review", 1440, 1180, "The review screen of a QC gate: checks, viewer, AI suggestion, pending changes"),
        Shot("review-gate-phone", "MReview", 390, 844, "The same gate on a phone"),
        Shot("overview", "Overview", 1440, 1180, "Overview: runs that need attention, gates waiting, environments"),
        Shot("launch", "Launch", 1440, 1180, "Launching a pipeline: parameters from its schema, samplesheet, environment, gates"),
        Shot("runs", "RunsTable", 1440, 1180, "Every run in one table, with stage, gates and cost"),
        Shot("review-queue", "ReviewQueue", 1440, 1180, "The review queue: gates waiting for a decision"),
        Shot("environments", "Environments", 1440, 1180, "Environments: SLURM and Kubernetes runners, capacity, health"),
        Shot("admin-plugins", "AdminPlugins", 1440, 1180, "Administration: plugins for engines, auth, storage and notifications"),
        Shot("lite-run-detail", "LiteRunDetail", 1440, 1180, "0.0.1: a running nf-core/rnaseq run with its detected stages, each opening to its processes, its head in tmux, Cancel and Copy"),
        Shot("lite-launch", "LiteLaunch", 1440, 1180, "0.0.1: launching a pipeline from its directory, the form built from nextflow_schema.json, here prefilled from an earlier run"),
        Shot("lite-runs", "LiteRuns", 1440, 1180, "0.0.1: every run with its state, workflow, tasks, start and duration"),
        Shot("lite-run-detail-phone", "MLiteRunDetail", 390, 844, "0.0.1: the same run on a phone"),
        # Live: from a running `spectio serve` at $SPECTIO_URL, with the synthetic Nextflow pipeline
        # copied to $SPECTIO_DEMO_PIPELINE (a path free of forbidden terms, fixtures.yaml).
        Shot("app-launch", "/launch", 1440, 1000,
             "0.0.1, live: the launch form, the synthetic Nextflow pipeline picked from Try a test pipeline and loaded",
             themes=("light", "dark"), live=APP_LAUNCH_CHECKED),
        Shot("app-launch-phone", "/launch", 390, 844, "0.0.1, live: the same launch form on a phone, from its top",
             themes=("light", "dark"), live=APP_LAUNCH + ("top:",)),
        # P1 Task 20: the same serve, after one run of the synthetic pipeline with profile `test` has
        # finished; $SPECTIO_DEMO_RUN is its ID.
        Shot("app-home", "/", 1440, 1000, "0.0.1, live: Home, with the count cards, the runs that ended and the pipelines",
             live=("wait:Finished recently",)),
        Shot("app-runs", "/runs", 1440, 1000, "0.0.1, live: the runs list with its state filters",
             live=("wait:Duration",)),
        Shot("app-home-phone", "/", 390, 844, "0.0.1, live: Home on a phone, its runs as cards",
             live=("wait:Finished recently",)),
        Shot("app-runs-phone", "/runs", 390, 844, "0.0.1, live: the runs list on a phone, one card per run",
             live=("wait:Succeeded",)),
        Shot("app-launch-snakemake", "/launch", 1440, 1380,
             "0.0.1, live: the launch form with the synthetic Snakemake pipeline loaded, its schema groups opened",
             live=APP_LAUNCH_SMK),
        Shot("app-run-detail", "/runs/$SPECTIO_DEMO_RUN", 1440, 1180,
             "0.0.1, live: a finished run of the synthetic Nextflow pipeline, its processes and facts",
             themes=("light", "dark"), live=("wait:65 / 65 tasks",)),
        Shot("app-run-detail-phone", "/runs/$SPECTIO_DEMO_RUN", 390, 844, "0.0.1, live: the same run on a phone",
             live=("wait:65 / 65 tasks",)),
        Shot("app-run-detail-failed", "/runs/$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: a failed run of the synthetic Nextflow pipeline, why it failed and the first task to fail",
             themes=("light", "dark"), live=("wait:Why it failed", "wait:First to fail")),
        # P1 Task 32: the failed run is launched with fail_mode=oom and fail_process=MERGE (three attempts, exit
        # code 137), so that Attempt shows. "Open the job files of" is the failure card's button; the task sheet
        # opens on the job log. The sacct values stay "unavailable" (no cluster): the honest state.
        Shot("app-run-job-files", "/runs/$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: the task sheet of a failed task open on .command.log, with Attempt and one tab per file",
             themes=("light", "dark"), live=("wait:Why it failed", "open:Open the job files of", "wait:Attempt")),
        Shot("app-run-job-files-phone", "/runs/$SPECTIO_DEMO_FAILED_RUN", 390, 844,
             "0.0.1, live: the same sheet on a phone, the files in a File select",
             themes=("light", "dark"), live=("wait:Why it failed", "open:Open the job files of", "wait:Attempt")),
        Shot("app-run-tasks", "/runs/$SPECTIO_DEMO_FAILED_RUN?tab=tasks", 1440, 1000,
             "0.0.1, live: the Tasks tab with Attempt, Duration, CPUs, Memory and Time limit columns",
             themes=("light", "dark"), live=("wait:Peak memory", "open:All")),
        # P3 UI parity D: the process sheet (LiteTaskFiles), opened from a process name on the same run.
        # `open:` waits for the sheet's slide-in to settle.
        Shot("app-run-process", "/runs/$SPECTIO_DEMO_RUN", 1440, 1180,
             "0.0.1, live: the sheet of one process, its counts, Open in Tasks and its tasks",
             themes=("light", "dark"), live=("wait:65 / 65 tasks", "open:Open process ALIGN", "wait:Open in Tasks")),
        # P3 UI parity C: the Logs tab of the same failed run, on the head's output, where Nextflow
        # writes the failed task's error. P3 UI parity D: searched for MERGE, four matches in that log.
        Shot("app-run-logs", "/runs/$SPECTIO_DEMO_FAILED_RUN?tab=logs&source=head-out", 1440, 1180,
             "0.0.1, live: the Logs tab of a failed run, searched: marked matches, the counter and the level buttons",
             themes=("light", "dark"), live=("wait:Download last 64 KiB", "wait:Command error",
                                             "fill:Search the head output=MERGE", "wait:1 / 4")),
        # P1 Task 32 part two. The synthetic pipeline's MULTIQC process writes only a stand-in table, so the
        # demo run's multiqc/multiqc_report.html is replaced by the regenerated MultiQC fixture first
        # (tools/media/README.md); `frame:` waits for its neutral input path inside the viewer. The failed run
        # is the Task 32 run above, which Resume and Copy start from. The report is stopped, not loaded: its
        # scripts throw on localStorage in the opaque-origin sandbox, so "Loading report.." stays (inbox #102).
        Shot("app-report-viewer", "/runs/$SPECTIO_DEMO_RUN/report?path=multiqc/multiqc_report.html", 1440, 1180,
             "0.0.1, live: a MultiQC report in the sandboxed report viewer, under its Untrusted report banner. "
             "Its tables show, but its scripts stop on localStorage: 'Loading report..' stays, the toolbox does not start",
             themes=("light", "dark"), live=REPORT_VIEWER),
        Shot("app-report-viewer-phone", "/runs/$SPECTIO_DEMO_RUN/report?path=multiqc/multiqc_report.html", 390, 844,
             "0.0.1, live: the same report on a phone, stopped the same way", themes=("light", "dark"), live=REPORT_VIEWER),
        Shot("app-run-results", "/runs/$SPECTIO_DEMO_RUN", 1440, 1180,
             "0.0.1, live: the Summary's Results and reports: the results directory, MultiQC first, the folders",
             themes=("light", "dark"), live=("wait:Browse all results", "view:Browse all results")),
        Shot("app-run-results-phone", "/runs/$SPECTIO_DEMO_RUN", 390, 844,
             "0.0.1, live: the same section on a phone",
             themes=("light", "dark"), live=("wait:Browse all results", "view:Browse all results")),
        Shot("app-results-browser", "/runs/$SPECTIO_DEMO_RUN/results?path=multiqc", 1440, 1000,
             "0.0.1, live: the results browser in one folder: path bar, Copy path, a report and files that download",
             themes=("light", "dark"), live=("wait:multiqc_report.html",)),
        Shot("app-run-resume", "/runs/$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: Resume this run? on a failed run: same launch directory, -resume, the tasks reused",
             themes=("light", "dark"), live=("wait:Why it failed", "open:Resume", "wait:Resume this run?")),
        Shot("app-run-resume-phone", "/runs/$SPECTIO_DEMO_FAILED_RUN", 390, 844,
             "0.0.1, live: the same question as a bottom sheet on a phone, Resume above Cancel",
             themes=("light", "dark"), live=("wait:Why it failed", "open:Resume", "wait:Resume this run?")),
        Shot("app-launch-copy", "/launch?from=$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: Copy to a new launch: the form prefilled from the failed run, the values that differ named",
             themes=("light", "dark"), live=("wait:Prefilled from",)),
        Shot("app-launch-copy-phone", "/launch?from=$SPECTIO_DEMO_FAILED_RUN", 390, 844,
             "0.0.1, live: the same prefilled form on a phone",
             themes=("light", "dark"), live=("wait:Prefilled from",)),
        # P1 Tasks 34 and 35 (batch P3-B04): $SPECTIO_DEMO_RUN is a finished run of the synthetic Nextflow pipeline, and
        # $SPECTIO_DEMO_SMK_RUN a finished run of the synthetic Snakemake pipeline (a copy with a config/config.yaml,
        # launched from the UI; chunks 0, so the `split` checkpoint grows the DAG). Both on a local executor: no
        # `sacct`, so no SLURM facts; the efficiency is the engine's own.
        Shot("app-run-rules", "/runs/$SPECTIO_DEMO_SMK_RUN", 1440, 1500,
             "0.0.1, live: a Snakemake run's rules: the Checkpoint chip on split, the DAG-updated line, the states legend",
             themes=("light", "dark"), live=("wait:Checkpoint",)),
        Shot("app-run-by-process", "/runs/$SPECTIO_DEMO_RUN?tab=tasks", 1680, 1000,
             "0.0.1, live: Tasks, By process: CPU and memory efficiency per process, the request and the sort button of each column",
             themes=("light", "dark"), live=("tab:By process", "wait:CPU eff. mean")),
        Shot("app-run-by-process-phone", "/runs/$SPECTIO_DEMO_RUN?tab=tasks", 390, 844,
             "0.0.1, live: By process on a phone: the waste lines and one card per process",
             themes=("light", "dark"), live=("tab:By process", "wait:Sort by", "view:Over each task")),
        Shot("app-run-job-outputs", "/runs/$SPECTIO_DEMO_SMK_RUN?tab=tasks&process=merge", 1440, 1000,
             "0.0.1, live: a Snakemake job's sheet on its Outputs tab (the rule has no log file): the file, present, and what Snakemake does not say",
             themes=("light", "dark"), live=("open:Files of", "wait:present")),
        Shot("app-run-task-efficiency", "/runs/$SPECTIO_DEMO_RUN?tab=tasks&process=FINAL_REPORT", 1440, 1000,
             "0.0.1, live: a Nextflow task's sheet: Efficiency from the engine's trace, with its source, and the 'low' flag",
             themes=("light", "dark"), live=("open:Files of", "wait:from the Nextflow trace")),
        # Batch P3-B08 (FU-P3-80, 82, 83): the same runs as above, and a Nextflow run launched with the profile
        # `fail_demo` ($SPECTIO_DEMO_FAILED_RUN; COMPARE for treatA exits 1). The order radios on a Snakemake run
        # (By rule, pipeline order), the process sheet with its named columns, and a failed task's stderr.
        Shot("app-run-by-rule-order", "/runs/$SPECTIO_DEMO_SMK_RUN?tab=tasks", 1440, 1000,
             "0.0.1, live: Tasks, By rule, in pipeline order: the Order radio group, Pipeline order checked, and A to Z beside it",
             themes=("light", "dark"), live=("tab:By rule", "wait:Pipeline order")),
        Shot("app-run-by-rule-order-phone", "/runs/$SPECTIO_DEMO_SMK_RUN?tab=tasks", 390, 844,
             "0.0.1, live: By rule on a phone: the Order radio group above the Sort by select, which also lists Pipeline order",
             themes=("light", "dark"), live=("tab:By rule", "wait:Sort by", "view:Sort by")),
        Shot("app-run-failed-synth", "/runs/$SPECTIO_DEMO_FAILED_RUN", 1440, 1180,
             "0.0.1, live: a run launched with the profile fail_demo: Why it failed, and the job files of the failed COMPARE task, with its ERROR lines",
             themes=("light", "dark"), live=("wait:Why it failed", "open:Open the job files of", "wait:Attempt")),
        Shot("app-run-process-columns", "/runs/$SPECTIO_DEMO_RUN", 1440, 1180,
             "0.0.1, live: the sheet of one process, its tasks in two columns, Task and State, under a header",
             themes=("light", "dark"), live=("wait:65 / 65 tasks", "open:Open process ALIGN", "wait:Open in Tasks")),
        # Batch P3-B09 (FU-P3-85c, 85d, 85e): the file explorer and preview, on the finished Nextflow run
        # ($SPECTIO_DEMO_RUN, launched from the UI with the profiles test,local) and the work directory of its
        # COMPARE task for treatA_vs_ctrl ($SPECTIO_DEMO_TASK, attempt 1).
        Shot("app-results-explorer", "/runs/$SPECTIO_DEMO_RUN/results", 1440, 1000,
             "0.0.1, live: the results explorer at the top of the results directory: sort buttons, the filter, a Kind badge and a Download button per entry",
             themes=("light", "dark"), live=("wait:final_report.html",)),
        Shot("app-file-preview", "/runs/$SPECTIO_DEMO_RUN/results/file?path=quant/counts_matrix.tsv", 1440, 1000,
             "0.0.1, live: the preview of a results file, a TSV shown as a table, with its path, size and the Download button",
             themes=("light", "dark"), live=("wait:counts_matrix.tsv",)),
        Shot("app-file-preview-phone", "/runs/$SPECTIO_DEMO_RUN/results/file?path=quant/counts_matrix.tsv", 390, 844,
             "0.0.1, live: the same preview on a phone",
             themes=("light", "dark"), live=("wait:counts_matrix.tsv",)),
        # Batch P3-B12 (FU-P3-102d3): a TIFF in the results of a seeded run, from `tools/media/tiff_demo.py` (it sets the
        # environment itself): one 16-bit grayscale plane of 512 by 384, so the page says "Contrast stretched for display".
        Shot("app-file-preview-tiff", "/runs/$SPECTIO_DEMO_RUN/results/file?path=imaging/cells.tif", 1440, 1000,
             "0.0.1, live: the preview of a TIFF, its first plane on a canvas with Actual size and the line of facts under it",
             themes=("light", "dark"), live=("wait:Actual size",)),
        Shot("app-file-preview-tiff-phone", "/runs/$SPECTIO_DEMO_RUN/results/file?path=imaging/cells.tif", 390, 844,
             "0.0.1, live: the same TIFF on a phone",
             themes=("light", "dark"), live=("wait:Actual size",)),
        # Batch P3-B13 (FU-P3-87e, 101a, 102g), from `tools/media/b13_demo.py` (it sets the environment itself): a catalog
        # of three entries, seven runs, and one run whose results hold a 30-row TSV and an OME-Zarr.
        Shot("app-launch-catalog", "/launch", 1440, 1100,
             "0.0.1, live: Launch with an entry chosen from the catalog picker and loaded: the entry line, the Loaded card with its catalog action",
             themes=("light", "dark"), live=("wait:From your catalog", "select:From your catalog=RNA-seq test \u00b7 Nextflow", "click:Load", "wait:Loaded")),
        Shot("app-launch-catalog-manage", "/launch", 1440, 900,
             "0.0.1, live: Manage catalog opened from Launch, the list of the user's pipelines in a dialog",
             themes=("light", "dark"), live=("wait:From your catalog", "open:Manage catalog", "wait:Add pipeline")),
        Shot("app-runs-grid", "/runs", 1440, 900,
             "0.0.1, live: the runs list as an AG Grid table, one row per run with a state rail, the filters above it",
             themes=("light", "dark"), live=("wait:rnaseq-treatA-ctrl",)),
        Shot("app-file-preview-grid", "/runs/$SPECTIO_DEMO_RUN/results/file?path=quant/counts_matrix.tsv", 1440, 1000,
             "0.0.1, live: a TSV in the AG Grid preview table: sortable headers, a filter row, rows drawn as they scroll",
             themes=("light", "dark"), live=("wait:counts_matrix.tsv", "wait:ctrl_1")),
        Shot("app-file-preview-zarr", "/runs/$SPECTIO_DEMO_RUN/results/file?path=imaging/cells.ome.zarr", 1440, 1000,
             "0.0.1, live: an OME-Zarr folder in the Viv viewer, read through the page's own capped Zarr store",
             themes=("light", "dark"), live=("wait:Channels",)),
        Shot("app-run-engine-log", "/runs/$SPECTIO_DEMO_LOGGED_RUN", 1440, 900,
             "0.0.1, live: the Summary of a run with its engine log's last lines and the button Open the full engine log",
             themes=("light", "dark"), live=("wait:Open the full engine log",)),
        # Batch P3-B14 (FU-P3-87d, 102e/f, 104, 111, 112), from `tools/media/b14_demo.py` (it sets the environment itself):
        # a catalog of three entries, environments.toml with two-cores (default) and eight-cores, and one run whose
        # results hold imaging/cells.ome.tif (three 16-bit channels).
        Shot("app-catalog", "/catalog", 1440, 900,
             "0.0.1, live: the Catalog page, one card per saved pipeline with Edit and Delete, and Add pipeline",
             themes=("light", "dark"), live=("wait:Liver QC",)),
        Shot("app-catalog-entry", "/catalog/rnaseq-test", 1440, 900,
             "0.0.1, live: the entry form of one catalog entry: name, label, engine, location, profile and params file",
             themes=("light", "dark"), live=("wait:Params file",)),
        Shot("app-environments-table", "/environments?view=table", 1440, 900,
             "0.0.1, live: Environments as a table, with the kind icon and the actions named per row, Duplicate to edit on the built-in",
             themes=("light", "dark"), live=("wait:Eight cores", "wait:Duplicate to edit")),
        Shot("app-environment-duplicate", "/environments/new?from=local", 1440, 900,
             "0.0.1, live: the form of a duplicate of the built-in local environment, filled in, with a unique name",
             themes=("light", "dark"), live=("wait:Default profiles",)),
        Shot("app-file-preview-ome-tiff", "/runs/$SPECTIO_DEMO_RUN/results/file?path=imaging/cells.ome.tif", 1440, 1000,
             "0.0.1, live: an OME-TIFF of three channels in the Viv viewer with the channel list, headless Chromium with software WebGL 2; the breadcrumb ends with the file name",
             themes=("light", "dark"), live=("wait:Channels", "wait:Reset contrast")),
        Shot("app-profile", "/", 1440, 900,
             "0.0.1, live: the Profile page in single-user mode, opened from the avatar (a direct visit to /profile is a 404, DW-P3B14-01): who the server runs as, this session, the config paths and the theme",
             themes=("light", "dark"), live=("link:Profile", "wait:Config paths")),
        Shot("app-profile-phone", "/", 390, 844,
             "0.0.1, live: the Profile page on a phone, opened from the avatar",
             themes=("light", "dark"), live=("link:Profile", "wait:Config paths")),
        Shot("app-workdir", "/runs/$SPECTIO_DEMO_RUN/workdir?task=$SPECTIO_DEMO_TASK&attempt=1", 1440, 1000,
             "0.0.1, live: the work directory of one Nextflow task attempt, in the same explorer, with the way back to the task's sheet",
             themes=("light", "dark"), live=("wait:treatA_vs_ctrl.tsv",)),
        # Batch P3-B11 (FU-P3-86f to -86h): a local server (`spectio init --local`) with `environments.toml` holding
        # two-cores (2 CPUs, 4 GiB, made the default) and eight-cores (8 CPUs, 16 GiB). $SPECTIO_DEMO_RUN is a finished
        # run of the synthetic Nextflow pipeline launched from the UI's body with `environment` eight-cores.
        Shot("app-environments", "/environments", 1440, 900,
             "0.0.1, live: Environments, the built-in and two of the user's, one of them the default",
             themes=("light", "dark"), live=("wait:Eight cores",)),
        Shot("app-environments-phone", "/environments", 390, 844,
             "0.0.1, live: the same list on a phone, one card per environment, each a link to its page",
             themes=("light", "dark"), live=("wait:Eight cores",)),
        Shot("app-environment-edit", "/environments/two-cores", 1440, 900,
             "0.0.1, live: one environment's form on a local server: the executor is fixed, the local caps and the default profiles",
             themes=("light", "dark"), live=("wait:Default profiles",)),
        Shot("app-launch-environment", "/launch", 1440, 1400,
             "0.0.1, live: Launch with Where it runs (the environment as radio cards), and the aside: Summary and Before Launch, here with a field error",
             themes=("light", "dark"), live=APP_LAUNCH_CHECKED + ("top:",)),
        Shot("app-run-environment", "/runs/$SPECTIO_DEMO_RUN", 1440, 700,
             "0.0.1, live: a run's Facts, with the Environment it ran with, from the copy stored at launch",
             themes=("light", "dark"), live=("wait:65 / 65 tasks", "wait:eight-cores")),
    )
}


def render(shot: Shot, theme: str) -> Path | None:
    if theme not in shot.themes:
        print(f"skip {shot.name} [{theme}]: board has no {theme} variant")
        return None
    if shot.live is not None and "SPECTIO_URL" not in os.environ:
        print(f"skip {shot.name}: a live shot needs SPECTIO_URL (a running spectio serve)")
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{shot.name}_{theme}.webp"
    with tempfile.TemporaryDirectory() as tmp, sanitize.sanitised_boards(BOARDS) as boards:
        png, text = Path(tmp) / "shot.png", Path(tmp) / "page.txt"
        preload = ["node", "--require", str(Path(__file__).resolve().parent / "page_text.js")]
        if shot.live is None:
            cmd = [*preload, str(REPO / "tools/canvas/render.js"), str(boards / f"{shot.board}.dc.html"),
                   str(shot.width), str(shot.height), str(png), *shot.clicks]
        else:  # the page text is checked as it is shown: a live page is never rewritten
            # live.js reads $SPECTIO_URL and expands $VARS in the steps itself: no environment value goes into argv
            cmd = [*preload, str(Path(__file__).resolve().parent / "live.js"), shot.board,
                   str(shot.width), str(shot.height), str(png), *shot.live]
        subprocess.run(cmd, check=True, capture_output=True, cwd=REPO,
                       env={**os.environ, "SPECTIO_PAGE_TEXT": str(text), "SPECTIO_THEME": theme})
        found = sanitize.leaks(text.read_text(encoding="utf-8"))
        if found:
            sys.exit(f"{shot.name}: forbidden term visible in the rendered page: {found}")
        print(f"hygiene ok: {shot.name} (no forbidden term in the rendered page text)")
        # lossless keeps UI text crisp; method 6 = smallest file
        subprocess.run(["convert", str(png), "-define", "webp:lossless=true", "-define", "webp:method=6",
                        str(out)], check=True)
    print(f"-> {out.relative_to(REPO)}  ({out.stat().st_size // 1024} KB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Documentation screenshots")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--shot", choices=sorted(REGISTRY))
    g.add_argument("--all", action="store_true")
    r.add_argument("--theme", choices=["light", "dark", "both"], default="both")
    a = ap.parse_args()

    if a.cmd == "list":
        for s in REGISTRY.values():
            print(f"{s.name:20} {s.board if s.live else s.board + '.dc.html':24} {s.width}x{s.height}  {'/'.join(s.themes):10} {s.caption}")
        return
    shots = REGISTRY.values() if a.all else [REGISTRY[a.shot]]
    themes = ("light", "dark") if a.theme == "both" else (a.theme,)
    for s in shots:
        for t in themes:
            render(s, t)


if __name__ == "__main__":
    sys.exit(main())
