---
step: APPLY7
wave: W4
status: running
pr: null
review: approve
review_score: 11/14
review_ref: "doc-reviewer 2026-10-28, approve 11/14 on bbeff35; D1-D10 applied in the second commit, with UX-325 to UX-335 and SEC-150 to SEC-159 (docs/reviews/code/APPLY7.md)"
---
# APPLY7 · Job files and run tools in 0.0.1

!!! info "Running 2026-10-28 · branch `autopilot/apply7-logs-features` · Thomas: each job's own files from its work directory, and five more tools in 0.0.1 (resume, failure summary, results, copy, resources) · four choices assumed (inbox #70) · four new security requirements (dev-env §15.3 req. 13 to 16) · P1 gains milestone M8, Tasks 28 to 32 · review round on `bbeff35`: doc approve 11/14, 11 UX and 10 security findings, all applied"

![APPLY7 figure. A strip at the top, "before (5e2493e)": three tabs, head output, head errors and engine log, and the work directory as a path to copy with no files shown. Then three rows. A, job files: a SLURM job writes into its Nextflow work directory, work/9d/77c214…, the files .command.log (the SLURM output, opened first), .command.err and .command.out, .command.sh and .command.run (its exported values hidden), .exitcode and .command.trace; for Snakemake, .snakemake/slurm_logs/rule_<r>/…/<id>.log. The server reads them confined (requirement 13: an openat walk that follows no symlink out of the run or work directory, names from an allow-list, the last 64 KiB, 1 MiB at most) and shows them in a drawer on the desktop and a sheet on the phone, with focus back on the Files button; the run's own logs are .spectio/nextflow.log through NXF_LOG_FILE and the head's output and errors. B2 and B5: the Snakemake SLURM plugin's message "SLURM-job '48731209' failed, SLURM status is: 'OUT_OF_MEMORY'" and sacct give, to scale, 16 GB asked and 16.0 GB used, a 4 h limit and 1 h 12 used, for bwa_mem sample WGS-07, attempt 2 of 2, exit 0:125, with a "near limit" mark; the same columns on every task row; "Nextflow: sacct per failed attempt; Snakemake: batch", under one limiter (one call in flight, 60 s apart, 100 IDs a call), fetched when first opened and cached in .spectio/sacct.json; accounting = false turns it off (requirement 15). B1, Resume: the failed run wgs-cohort-12 stays Failed and a child run starts in the same launch directory; 143 jobs are reused and 32 run again, to scale; -resume or --rerun-incomplete (requirement 16). B3: the --outdir folder and multiqc_report.html in Spectio's report viewer, a locked, sandboxed iframe, read-only (requirement 14). B4: the command and params copied into a Launch form "Prefilled from wgs-cohort-12 (F5KZNW)" with "Clear and start empty"; Copy to a new launch makes a fresh run with its own directory](../../assets/diagrams/apply7_run_tools_light.png#only-light)
![APPLY7 figure. A strip at the top, "before (5e2493e)": three tabs, head output, head errors and engine log, and the work directory as a path to copy with no files shown. Then three rows. A, job files: a SLURM job writes into its Nextflow work directory, work/9d/77c214…, the files .command.log (the SLURM output, opened first), .command.err and .command.out, .command.sh and .command.run (its exported values hidden), .exitcode and .command.trace; for Snakemake, .snakemake/slurm_logs/rule_<r>/…/<id>.log. The server reads them confined (requirement 13: an openat walk that follows no symlink out of the run or work directory, names from an allow-list, the last 64 KiB, 1 MiB at most) and shows them in a drawer on the desktop and a sheet on the phone, with focus back on the Files button; the run's own logs are .spectio/nextflow.log through NXF_LOG_FILE and the head's output and errors. B2 and B5: the Snakemake SLURM plugin's message "SLURM-job '48731209' failed, SLURM status is: 'OUT_OF_MEMORY'" and sacct give, to scale, 16 GB asked and 16.0 GB used, a 4 h limit and 1 h 12 used, for bwa_mem sample WGS-07, attempt 2 of 2, exit 0:125, with a "near limit" mark; the same columns on every task row; "Nextflow: sacct per failed attempt; Snakemake: batch", under one limiter (one call in flight, 60 s apart, 100 IDs a call), fetched when first opened and cached in .spectio/sacct.json; accounting = false turns it off (requirement 15). B1, Resume: the failed run wgs-cohort-12 stays Failed and a child run starts in the same launch directory; 143 jobs are reused and 32 run again, to scale; -resume or --rerun-incomplete (requirement 16). B3: the --outdir folder and multiqc_report.html in Spectio's report viewer, a locked, sandboxed iframe, read-only (requirement 14). B4: the command and params copied into a Launch form "Prefilled from wgs-cohort-12 (F5KZNW)" with "Clear and start empty"; Copy to a new launch makes a fresh run with its own directory](../../assets/diagrams/apply7_run_tools_dark.png#only-dark)

*The memory and time values and the 143 of 175 jobs are the `LiteRunFailed` board's fixture. Before: `autopilot/integration` at `5e2493e`, where 0.0.1 showed the head's output, head errors and the engine log only, and each task's work directory as a path (P1 Assumption 20), with relaunch and resume deferred.*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml). Thomas, 2026-10-28: "Je veux également que ça soit possible de voir les logs globaux et les lots et stout err log sh et autres de chaque job si possible via workdir / Autres features basic mais utile en MVP ?", then, on the five tools proposed: "les 5 dans 0.0.1" ([decision log](../../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources)).

## What changed

Each item, then where it now lives.

- **A · global logs and each job's files.**
    - [Architecture §13.7](../../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine) keeps its table and gains a dated revision: the run's logs (Spectio sets `NXF_LOG_FILE` to `.spectio/nextflow.log`, because `.nextflow.log` rolls at every start), the files of a Nextflow work directory and what each holds, the Snakemake rule logs and SLURM job logs, all with sources.
    - [api](../../specs/api-and-data-model.md): `GET /tasks/{id}/attempts/{n}/files[/{name}]`, with the states `present`, `not_yet`, `absent`, `deleted_after_success` and `cleaned`, a 64 KiB tail, 1 MiB at most, `415` for binary files and `422` for a name outside the allow-list; `work_dir` on the run.
    - [ui-spec §4.4](../../specs/ui-spec.md#44-run-detail) note: a Files button per task row opens a drawer on the desktop and a sheet on the phone, with the work directory to copy and one tab per file; a failed attempt opens on `.command.log` (`.command.err` for array tasks). The Logs tab says the engine log is the run's own.
    - [P1](../../plans/P1-walking-skeleton.md): Assumption 20 is reversed; Task 28.
- **B1 · Resume a failed or cancelled run.** A child run with its own `.spectio/`, its head in the parent's launch directory, with `-resume` or `--rerun-incomplete`; the parent stays Failed or Cancelled. Owned by [api §5.1](../../specs/api-and-data-model.md) (note 2026-10-28: body `{mode:"resume"}` only, `parent_run_id`, `resumed_as`); P1 Task 30; dev-env §15.1 Relaunch row rewritten.
- **B2 · Failure summary with the SLURM reason.** Per failed job: exit code, SLURM state and reason, memory and time asked and used, and the last lines of `.command.log`. Nextflow gives the job ID; Spectio calls `sacct` once per failed attempt. For Snakemake, the plugin's own failure message is parsed. Owned by architecture §13.7 (Failure reason) and the api `failure` fields; P1 Task 29.
- **B3 · Results and reports, read only.** `GET /runs/{id}/results?path=` and `/results/raw/{path}` under the run's results directory; HTML opens in a sandboxed tab. Runs Spectio launched only. P1 Task 31.
- **B4 · Copy the command and parameters; Copy to a new launch.** A Copy menu, and `:launch-template`, which prefills the launch form from a run. P1 Task 30.
- **B5 · Resources per task.** CPUs, CPU %, memory, peak memory and time limit as numbers in the tasks table, from the Nextflow trace (nf-spectio turns metrics on) and from `sacct` in batches for Snakemake. Architecture §13.7 (Resources per task); P1 Task 29.
- **Everywhere:**
    - [dev-env §15.1](../../specs/dev-environment-and-testing.md#151-capabilities-by-version): five new rows and the Scheduler monitoring row; [§15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts): requirements 13 to 16, listed below.
    - [`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md) §2: two rows; the deferred relaunch line reworded; the screenshot captions updated.
    - [P1](../../plans/P1-walking-skeleton.md): Assumptions 1, 3 and 20 dated notes; milestone M8 with Tasks 28 to 32, each with named tests; Out of scope and Done when.
    - [Inbox](../../reviews/inbox.md): a note on #61, and #70.
    - [Decision log](../../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources): a new entry.
- **Boards** (`design/ui-canvas/`):
    - `LiteRunTasks`, `MLiteRunTasks`: resource columns, a "near limit" word, a Files button per row;
    - `LiteTaskFiles`, `MLiteTaskFilesSheet`, new: the drawer and the sheet, `aria-modal`, the page behind `inert`, focus back on the row's Files button;
    - `LiteRunFailed`: Resume, Copy to a new launch and Copy; one card per failed job with the SLURM state and reason, exit code, memory and time asked and used, last lines, Open job files; a Results and reports section;
    - `LiteRunDetail`, `MLiteRunDetail`: a Copy menu and a Results and reports section;
    - `LiteLaunch`: the "Prefilled from" banner with "Clear and start empty";
    - `LiteRunLogs`, `MLiteRunLogs`: the engine log is the run's own; each job's files open from Tasks;
    - `canvas.json` and [`design/README.md`](https://github.com/weber8thomas/spectio/blob/autopilot/apply7-logs-features/design/README.md) register the two new boards.

### New security requirements (dev-env §15.3)

13. **Confined reads.** Names, never paths; a component-by-component `openat` walk with `O_NOFOLLOW`, regular files of the user only; Snakemake names equal to the recorded path; a byte-capped tail in a file pool of its own; the files never served listed here only; `.command.run` with its values hidden by a shell lexer that fails closed, and `unset NXF_DEBUG`; plain text with `nosniff`, `no-store` and `no-referrer`.
14. **Reports in a sandbox.** HTML from the results directory opens only in Spectio's report viewer, in `<iframe sandbox="allow-scripts allow-downloads">`, served with a `sandbox` Content-Security-Policy without `allow-same-origin` and with `frame-ancestors 'self'`, so a report's script cannot call the API with the session cookie; listings, report search and streams are capped.
15. **Scheduler queries.** One limiter for the server (one `sacct` call in flight, 60 s apart, 100 IDs a call), none on rebuild or replay, a cache in `.spectio/sacct.json`; IDs checked, an argument list with an explicit environment and a 10 s timeout; `[slurm] accounting = false` turns it off.
16. **Resume and copy.** Resume is a state-changing request, refused on runs started from a terminal, while the parent's head is alive or cannot be checked, and while another child of the same directory runs (a lock file and `BEGIN IMMEDIATE`); the directory checks, its device and inode, run again before the child starts; values that load code are marked in Copy to a new launch.

## Review round on `bbeff35`

The coordinator relayed three reviews of `bbeff35` in one message: `doc-reviewer` approved with 11/14 (four required and six optional findings), `ux-reviewer` raised UX-325 to UX-335 and `security-reviewer` SEC-150 to SEC-159. Every finding was accepted and applied in a second commit on the same branch; each one and what was done with it is in [the review page](../../reviews/code/APPLY7.md). In short:

- **Specs.** The ui-spec note now owns one run header for every tab with Copy in every state, the Resume dialog and its four disabled reasons, the job file states and size line, the failure cap of 10, the results browser and the report viewer, and one banner format for Copy to a new launch. api gains `failures_total`, `actions.resume`, `resumed_as` and `code_loading`. Requirements 13 to 16 are rewritten with named tests (`test_req13_*` to `test_req16_*`), and checking-scenarios §11.1 gains the `openat` walk.
- **Six new boards:** `LiteTaskFilesStates` (nine states of a job's files), `LiteRunActions` (Resume dialog, disabled reasons, Resume links, the open Copy menu), `MLiteResumeSheet`, `MLiteRunFailed`, `LiteResults` (results browser) and `LiteReportViewer` (sandboxed report viewer).
- **Changed boards:** `LiteRunFailed`, `LiteTaskFiles`, `MLiteTaskFilesSheet`, `MLiteRunTasks`, `MLiteRunLogs`, `LiteRunDetail`, `MLiteRunDetail`, `LiteLaunch`, and the Copy menu added to `LiteRunTasks`, `LiteRunLogs`, `LiteRunDetailSnakemake`, `LiteRunObserved` and `MLiteRunObserved`.
- **Figure:** a "before (5e2493e)" strip above row A; row B2 says "Nextflow: sacct per failed attempt; Snakemake: batch" with the limiter.

## Why

On a cluster, the first question after a failure is "what did the job print, and did it run out of memory or time?". In 0.0.1 the answer meant opening a terminal on the login node and finding the work directory. The files already exist next to each job, and Nextflow and Snakemake already tell Spectio where; reading them on demand costs nothing until someone opens one. Resume and Copy to a new launch close the loop from a failure to a fixed run without retyping the parameters.

## Evidence

- **Sources:** the facts about Nextflow 26.10.4 (`691b821`) and 25.10.9 (`64d39b0`), Snakemake 9.27.1 and snakemake-executor-plugin-slurm 2.8.0 (`91f51af`) carry file:line references in architecture §13.7; a fact-checker pass on them was applied before the boards were drawn.
- **Boards:** every changed board was rendered with `node tools/canvas/render.js` (desktop 1440 × 1180, phone 390 × 844) and looked at. In the review round, the six new boards and the thirteen changed ones were rendered again and looked at, below the fold too, by scrolling `main` before the screenshot.
- **Docs gate**, `python3 tools/docs/check.py` on this branch:

    ```text
    mermaid: 5 blocks checked
    diagrams: 30 scripts re-run, 60 SVGs compared
    media: 146 outputs in the manifest
    progress: 43 pages checked
    docs gate: 0 failure(s)
    ```

- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0. The new anchors exist in the built pages: `2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources` and `70-assumed-what-the-job-file-viewer-shows-and-spectio-calling-sacct`.
- **Frontmatter:** `python3 tools/claude/check_frontmatter.py`: 14 agents, 22 skills, 0 problems.
- **Mermaid:** no diagram added or changed in this step.
- **Before:** `git show 5e2493e:docs/plans/P1-walking-skeleton.md` (Assumption 20: the work directory as a path only). **After:** `git diff 5e2493e -- docs/specs docs/plans docs/decisions docs/reviews/inbox.md design`.

## Figures and media

- `apply7_run_tools` (above), new: [`tools/diagrams/apply7_run_tools.py`](https://github.com/weber8thomas/spectio/blob/autopilot/apply7-logs-features/tools/diagrams/apply7_run_tools.py), entry `apply7-run-tools` in `docs/assets/media.yaml`. Rendered light and dark; both PNGs were opened.
- Review round: `apply7_run_tools` re-rendered with the "before" strip and the B2 wording, both PNGs opened; `lite-launch` regenerated (banner, outdir warning); `lite-run-detail` and `lite-run-detail-phone` regenerated with no change in the image, since their changes are below the fold; `lite-runs` unchanged.
- Screenshots `lite-run-detail`, `lite-launch` and `lite-run-detail-phone` regenerated with `python3 tools/media/shots.py run --shot <id> --theme light`, because their boards changed (Copy menu, prefilled banner); `lite-runs` is unchanged. A PR carrying them needs the `screenshots` label.

## Findings and open questions

- **Inbox #70** *(assumed)*: `.command.run` shown with its values hidden; the Snakemake job command not stored; runs Spectio launches keep every SLURM log; `sacct` as in requirement 15, to be checked with the EMBL cluster admins.
- **[to be validated]:**
    - the `sacct` field names and their load on the EMBL accounting database;
    - which `.snakemake/log/` file belongs to a run (spike T1);
    - whether `--unlock` is needed after a head was stopped (spike T1);
    - the plugin's submission message for releases other than 2.8.0;
    - the log path of array jobs (`--slurm-array-jobs`), a suspected plugin bug;
    - whether `sacct -B` shows job scripts at EMBL;
    - whether a MultiQC report renders under the sandbox policy (P1 Task 31).
