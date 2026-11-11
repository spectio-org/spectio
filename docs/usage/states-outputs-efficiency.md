---
icon: material/chart-gantt
---
# States, outputs and efficiency

!!! note "Built on the integration branch, not released yet"

    This works today from a checkout (batch [P3-B04](../progress/W5/P3-M9.md#batch-p3-b04), 2026-11-08; the order of the rows, the process sheet and the unreadable-log answers come from batch [P3-B08](../progress/W5/P3-M9.md#batch-p3-b08)). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **Nothing here ran on SLURM:** the screens below come from runs on a local executor, so there is no `sacct` and no SLURM request to show. The `slurm-mini` check waits for P1 Task 22.

The run page says more about what each process (Nextflow) or rule (Snakemake) did, and how much of its request it used. The rules are owned by [ui-spec §4.4](../specs/ui-spec.md#44-run-detail) and [§5.2](../specs/ui-spec.md#52-checkpoints-conditional-execution-and-temporary-outputs); the formulas by [schedulers §3.6](../specs/schedulers-and-monitoring.md#36-efficiency-per-job-and-per-process-or-rule). This page says what you see.

## States and checkpoints

Open a run, then **Summary**. Each rule has a state word. Pending means "jobs are planned and none has started"; the new words are:

| Word | Engine | Means |
|---|---|---|
| Waiting for checkpoint | Snakemake | a checkpoint has not finished; this rule's jobs may appear after it |
| Not needed in this run | Snakemake | the targets or an input function left the rule out; greyed, listed last |
| Up to date | Snakemake | its outputs already exist, so there is nothing to run |
| No task (condition or empty input) | Nextflow | the process never got a task: a `when:` was false or its input was empty |

A checkpoint rule carries a **Checkpoint** mark: a small signpost icon and the word, in muted text with no fill (a filled chip before batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13), step FU-P3-88a; the shot below still shows the old chip). Its sheet adds one line, "A checkpoint: once its jobs succeed, Snakemake updates the DAG from their outputs." While one is open the count reads "done / at least n", and the bar is hatched past the jobs known so far. The Summary says "The DAG grows after checkpoint …" and, once it ended, "DAG updated after a checkpoint (12 times): the job count includes the new jobs."

![A Snakemake run's Summary: the rules, the Checkpoint chip on split, the DAG-updated line, the states legend](../assets/shots/app-run-rules_light.webp#only-light)
![A Snakemake run's Summary: the rules, the Checkpoint chip on split, the DAG-updated line, the states legend](../assets/shots/app-run-rules_dark.webp#only-dark)

*A finished Snakemake 9.27.1 run of the synthetic pipeline, launched from Spectio on a local executor: 88 jobs, 12 DAG updates.*

Nextflow does not report a task that `when:` filtered out, and a process left out by a Groovy `if` is never created ([source: research note, section 4](../research/dag-temp-slurm-efficiency-2026-11-07.md#4-nextflow-conditional-execution-and-processes-that-never-run)). Spectio cannot tell these apart, so the list says "Processes the script does not call in this run are not listed."

## Efficiency by process or rule

On **Tasks** (Snakemake: **Jobs**), pick **By process** (**By rule**). Each column header is a sort button.

### Order of the rows

The table opens in **Pipeline order**: the rules in the order the pipeline runs them, no longer the least efficient first. Above the table, the radio group **Order** has two choices, **Pipeline order** and **A to Z**. They are native radio buttons: Tab reaches the group and the arrow keys move between them. A click on a column header sorts by that column and leaves both radios unchecked ([ui-spec §4.4](../specs/ui-spec.md#44-run-detail), note 2026-11-08).

- **Snakemake:** the order comes from the links of the rule graph (a rule after the rules it reads from). Rules with no link to each other keep the order of the rule files.
- **Nextflow:** the order is the order in which the processes were first seen.
- **A to Z** compares the last part of the name by code point, so capital letters sort before small ones.
- **A rule that joins the DAG after a checkpoint is not placed by its links.** The first rule graph does not hold it, so it has no link and comes first. In the shot below, `align` runs after the checkpoint `split` and is listed above `make_reads` ([FU-P3-90](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b08)).

![By rule on a finished Snakemake run, Pipeline order checked, the radio group Pipeline order and A to Z above the table; align is listed first](../assets/shots/app-run-by-rule-order_light.webp#only-light)
![By rule on a finished Snakemake run, Pipeline order checked, the radio group Pipeline order and A to Z above the table; align is listed first](../assets/shots/app-run-by-rule-order_dark.webp#only-dark)

*The synthetic Snakemake pipeline, launched from Spectio on a local executor, 88 jobs.*

![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_light.webp#only-light)
![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_dark.webp#only-dark)

- **CPU eff.** and **Mem eff.** are shown as a mean and a maximum over the jobs measured. "low" and "near limit" are words, not only colours.
- **CPUs asked, Memory asked, Time limit** show the most common request. **Requests** reads "vary" on a row when the jobs of the process asked for different values. The API has one flag for the three, so the page does not say which ([FU-P3-55](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b04)).
- A line above the table lists the processes whose jobs used under 25 % of their memory.
- **Read the screenshot with care:** it is a local run of very short jobs, so every process is flagged "low" with 0 % to 1 % memory and a 0 B peak. Real jobs on a cluster will not look like this.
- The numbers come from `sacct` once a SLURM job has ended, else from the engine's trace (Nextflow) or its benchmark file (Snakemake). On a local executor there is no `sacct`. A Snakemake rule with no `benchmark:` shows "—", as in the synthetic pipeline.

On a phone the table becomes one card per process, with a **Sort by** select. The select lists the column sorts and also **Pipeline order**, so Pipeline order and A to Z can be chosen from the radio group and from the select ([CR-P3FU82-03](../reviews/code/P3-fu82.md#findings): kept on purpose in the spec, **[to be validated]** with a user). The first shot below is scrolled to the first card, which is cut by the tab bar. **It was taken before FU-P3-82 and shows the older phone layout:** it has no Sort by select and no Pipeline order. The second shot (By rule) shows the new layout, the radio group above the select.

![By process on a phone, scrolled to the waste lines and the first process card](../assets/shots/app-run-by-process-phone_light.webp#only-light)
![By process on a phone, scrolled to the waste lines and the first process card](../assets/shots/app-run-by-process-phone_dark.webp#only-dark)

![By rule on a phone: the radio group, then the Sort by select showing Pipeline order, then the first rule card](../assets/shots/app-run-by-rule-order-phone_light.webp#only-light)
![By rule on a phone: the radio group, then the Sort by select showing Pipeline order, then the first rule card](../assets/shots/app-run-by-rule-order-phone_dark.webp#only-dark)

## One process and its tasks

Open a process name from the Summary. The sheet shows its counts and efficiency, then **Tasks** (Snakemake: **Jobs**) in two columns of the same width on every row, under a header: **Task** (Snakemake: **Job**) and **State**. The label already carries the tag ("ALIGN (S01.chunk0000)"), so the tag is not repeated.

- Each row is a button. Its accessible name ends with its state, "Open task ALIGN (S01.chunk0000), Succeeded"; the header is not read aloud, because every row already says what it is.
- **Load more** adds rows below.
- **While the run is active** the sheet reads the first page again on each live frame and keeps the rows that Load more added. The Summary's log tail is read again too. Neither is read once the run has ended.
- **A failed read** puts an alert above the rows. The rows and the focused button stay, so keyboard focus is not lost; the next good read clears the alert.

![The sheet of process ALIGN: counts, efficiency, then Tasks under a Task and State header](../assets/shots/app-run-process-columns_light.webp#only-light)
![The sheet of process ALIGN: counts, efficiency, then Tasks under a Task and State header](../assets/shots/app-run-process-columns_dark.webp#only-dark)

*Not shown: how the columns look on a phone. The State column is 9.5rem wide, an assumed value; that it fits at phone width is* **[to be validated]**.

## One job

Open a job with its **Files** button. The sheet has the job's **Efficiency**, with its source or the reason it is missing, then its files.

![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_light.webp#only-light)
![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_dark.webp#only-dark)

On SLURM the sheet also shows the request that is set (partition, CPUs, memory, time limit and the others), **Allocated** when it differs from the request, and "Custom sbatch options set". **It never shows the text of those options.** None of this was run on a cluster **[to be validated]**.

When SLURM accounting cannot answer, the Efficiency block says "No accounting for this job" and the reason in brackets: "local run", "sacct not found or accounting off", "no SLURM job ID", "not in SLURM accounting", "reused from an earlier run, no job ran", or, since FU-P3-106b (batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14)), "the window is over the site's sacct limit (MaxQueryTimeRange)". The last one means the site's slurmdbd refused the time window of the `sacct` call, so Spectio stops asking for that job instead of asking again every 10 minutes. It applies only to a job whose launch set the window; the other jobs of the same call are asked again with a narrower one. The rule is owned by [schedulers §3.8](../specs/schedulers-and-monitoring.md#38-slurm-query-budget). The test `test_sacct_site_time_range_limit_is_final` and its server-side twins pass; **no real slurmdbd with a `MaxQueryTimeRange` was run** **[to be validated]**.

## Measured fills in after `sacct`

The server sends no event when `sacct` answers a job that has ended, so the run page reads the processes again. It does so only while the run has ended and at least one job is waiting for `sacct`: `efficiency.pending_accounting` of a process, in [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1), the processes route, is above 0. It reads every 30 s and at most 10 times for a run in one visit, and a read that fails counts toward the 10 and is tried again (step FU-P3-122, batch [P3-B16](../progress/W5/P3-M9.md#batch-p3-b16); the first version, FU-P3-119, tested `measured < done`). A resumed run's reused tasks count in `done` and never in `measured`, so they no longer keep the page reading. **[Tested in `accounting.test.ts`; not run against a real slurmdbd.]**

## A log that cannot be read

When the Logs tab or a job's files cannot find the run's directory, the answer now says which case it is. Both messages name the directory that was tried, a path under your own runs root.

| Answer | Means |
|---|---|
| `410 log-cleaned` | the runs root is there and is the one the run was recorded under, and the run's directory is gone |
| `409 run-dir-unreachable` | the runs root is not there, or the run was recorded under another runs root (for example after `runs_root` changed) |

A run you started in a terminal has no recorded runs root and always answers `410`. The rule is owned by [api-and-data-model §5](../specs/api-and-data-model.md) (note 2026-11-08). **The login1 case that raised it (a `410` while the file exists) was not reproduced**; the cause is **[to be validated]** ([inbox #125](../reviews/inbox.md#125-question-login1-checks-for-the-runs-launch-directory-is-gone-fu-p3-81)).

## A run that fails on purpose, with logs to read

For the synthetic test pipelines, the profile `fail_demo` makes `COMPARE` (Snakemake: `compare`) for `treatA` exit 1, so the run ends **Failed** with a tool error. Every synthetic task also writes lines to its stdout and stderr, so the log views have something to show: the parameter `verbosity` is `quiet`, `normal` (the default) or `loud` (about 1000 lines and 90 KB per stream, more than the 64 KiB a log view shows first). The owner is [dev-env §10.1](../specs/dev-environment-and-testing.md#101-synthetic-scenario-pipelines-testspipelinessynthetic), note 2026-11-08; the Snakemake profile is for the local executor only.

![A failed run launched with the profile fail_demo: Why it failed, and the sheet of the COMPARE task with its WARN, INFO and ERROR lines](../assets/shots/app-run-failed-synth_light.webp#only-light)
![A failed run launched with the profile fail_demo: Why it failed, and the sheet of the COMPARE task with its WARN, INFO and ERROR lines](../assets/shots/app-run-failed-synth_dark.webp#only-dark)

*Nextflow 26.10.4 on a local executor. The SLURM job log of a Snakemake run, where the tool's stderr is copied, was not run* **[to be validated]**.

## The Summary's last lines and the full log

*Built on the integration branch (step FU-P3-88a, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13), 2026-11-10). Owned by [ui-spec §4.4](../specs/ui-spec.md#44-run-detail).*

![The Summary of a run: Facts, Processes, and on the right the Engine log with its last lines and the button Open the full engine log](../assets/shots/app-run-engine-log_light.webp#only-light)
![The Summary of a run: Facts, Processes, and on the right the Engine log with its last lines and the button Open the full engine log](../assets/shots/app-run-engine-log_dark.webp#only-dark)

*A seeded run record whose launch directory holds a `.nextflow.log` of nine lines, written for this shot. No head ran, so Facts and Processes are empty; only the log card is real.*

- **The last lines open the log.** A click on them, or the button **Open the full engine log →** (on a failed run, "head errors"), opens the Logs tab on the same source, with focus on its panel.
- **A click that ends a text selection does not open it,** so you can still copy a line.
- **Back to Summary** sits above the log's tools and returns to the Summary with focus on the button that opened it. Opened from its own tab, Logs has no such button. The address carries `&from=summary`, so Back to Summary survives a reload.

## The runs list

*Built on the integration branch (step FU-P3-101a, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13)). Owned by [ui-spec §4.13](../specs/ui-spec.md#413-tables-in-ag-grid) and [§4.3](../specs/ui-spec.md).*

![The runs list as a grid: seven demo runs, a coloured rail on each row, filters above](../assets/shots/app-runs-grid_light.webp#only-light)
![The runs list as a grid: seven demo runs, a coloured rail on each row, filters above](../assets/shots/app-runs-grid_dark.webp#only-dark)

*Seven seeded run records (succeeded, running, failed, cancelled), not pipeline runs: Tasks, Started and Duration read "—" because no head reported. The state rail on each row's left edge is as before.*

- **The default order is newest first, pinned runs first,** with filters above the table (name and state). The headers of Run, State, Started and Duration sort on the server; see [Select, sort, pin and delete runs](#select-sort-pin-and-delete-runs). **Load more** adds rows.
- **Keyboard.** The grid takes Tab and Enter for its cells, so a run's name is not a tab stop of its own. Move to the Run cell with the arrow keys and press **Enter** to open the run (a blocker found in review, fixed before merge).
- **Below 1100 px** the Started column drops, so the table fits at 1024 px.
- **On a phone** the list stays one card per run, and the grid is not loaded.

### Select, sort, pin and delete runs

*Built on the integration branch: the API in step FU-P3-115a (batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14)), the screens in FU-P3-115b, -116 and -119 (batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15)). Owned by the runs-table note of [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1) and [ui-spec §4.3](../specs/ui-spec.md#43-runs-table-and-rows).*

![The runs table with two rows selected: a bar above the table reads "2 selected" with Delete... and Clear selection; liver-qc-batch-7 is pinned and first; Run, State, Started and Duration have a sort icon](../assets/shots/app-runs-actions_light.webp#only-light)
![The runs table with two rows selected, dark](../assets/shots/app-runs-actions_dark.webp#only-dark)

*A seeded server with seven run records, two of them selected. The records have no pipeline behind them: Tasks reads "—".*

- **Select.** Each row has a checkbox named "Select run <name>"; the header box, "Select all runs on this page", selects the page. A bar then shows "n selected", **Delete…** and **Clear selection**.
- **Sort.** Click the header of Run, State, Started or Duration; a second click reverses it and a third clears it, back to newest first. Every sortable header shows an icon, sorted or not. The address keeps it (`/runs?sort=name`). The footer says it in words: "pinned first, then newest first".
- **Pin.** The pin button in a row (named "Pin run <name>") pins or unpins one run. **Pin** and **Unpin** are also in Run detail's header. Pinned runs come first in every sort.
- **Delete.** **Delete…** opens a sheet: the runs it names, "Spectio forgets these runs: they leave the list, the counts and Home. Their files stay where they are.", and a box, off by default, **Also delete their run directories**. **Cancel** has the focus. A live run cannot be deleted; a refusal names the run and why, and nothing is deleted. **Delete…** is also in Run detail's header, for an ended run; the result lines then show on the Runs page.

![The Delete sheet for two runs: rnaseq-treatC-ctrl Failed and rnaseq-pilot Cancelled, the box Also delete their run directories unchecked, and a note on what it removes](../assets/shots/app-runs-delete_light.webp#only-light)
![The Delete sheet for two runs, dark](../assets/shots/app-runs-delete_dark.webp#only-dark)

*The sheet was opened and not confirmed: the demo runs stay for the next shot.*

- **On a phone** the list stays one card per run. The box in a card sits in a 44 px target and the bar's buttons are at least 44 px high. The cards have no pin yet (UX-P3FU115B-06, open).

What the screens call, and what the API does:

- **Delete.** `POST /runs:delete` with `{"ids": [...], "directories": false}` marks 1 to 200 ended runs deleted, all or nothing. A deleted run leaves the list, the summary and every `/runs/{id}` route (`404`). The run's directory stays unless `directories` is `true`.
- **With `directories: true`** Spectio also removes each run's own directory, `<runs root>/<run ID>`, and nothing else, without following a link. It refuses, before deleting anything, a run that started from a terminal (its launch directory is yours), a run whose head has not been seen to exit, a directory that is not where the runs root says, and a directory that a run you did not select shares (a Resume child shares its parent's: delete them together). A Resume child's delete also removes the lineage root's directory, listed as its own entry.
- **Pin.** `PATCH /runs/{id}` with `{"pinned": true}` pins a run of any state. `GET /runs` lists pinned runs first in every sort but `-ended_at`; `sort=` takes `-created_at` (the default), `-ended_at`, `name`, `state`, `started_at` and `duration`, each also with `-`, and anything else is `422`.

From a demo server with three runs (`demo-imaging` succeeded and the oldest, `rnaseq-treatB` running, `rnaseq-treatC` failed):

```console
GET /runs                  200  [rnaseq-treatC failed, rnaseq-treatB running, demo-imaging succeeded]
PATCH /runs/<demo-imaging> {"pinned": true}   200  pinned = true
GET /runs                  200  [demo-imaging pinned, rnaseq-treatC, rnaseq-treatB]
GET /runs?sort=name        200  [demo-imaging pinned, rnaseq-treatB, rnaseq-treatC]
GET /runs?sort=bogus       422
POST /runs:delete {"ids": [<rnaseq-treatB>]}            409 run-not-ended: "the run is running"
POST /runs:delete {"ids": [<rnaseq-treatC>, <unknown>]} 404 not-found
POST /runs:delete {"ids": [<rnaseq-treatC>], "directories": true}
                           200  {"deleted": [...], "directories": [{"id": "<rnaseq-treatC>", "result": "removed"}]}
GET /runs/<rnaseq-treatC>  404
```

The run directory was gone from the demo runs root after the last delete. Every call needs the session cookie and the loopback `Origin`. The screens above use these routes. Open: the log line of a delete does not name who deleted (CR-P3FU115A-03), up to 200 `rmtree` calls run inside one request (-04), and the task-file routes still serve a deleted run's files (-05, SEC-P3FU115A-03).

## Temporary and protected outputs

For a Snakemake job, the sheet has an **Outputs** tab. It opens first when the rule has no log file. Each output shows "present", "not yet", "absent", "deleted by Snakemake (temporary)" or "write-protected".

![A Snakemake job's sheet on its Outputs tab](../assets/shots/app-run-job-outputs_light.webp#only-light)
![A Snakemake job's sheet on its Outputs tab](../assets/shots/app-run-job-outputs_dark.webp#only-dark)

- Snakemake's events do not say that an output is `temp()`. Spectio shows it only after Snakemake deleted the file, and never guesses.
- With `--notemp` nothing is deleted; the run's facts say "Temporary files kept (--notemp)".
- For Nextflow the run's facts say "Work directory cleaned after success (cleanup = true)" when it is set, and a cleaned job's files say so.

!!! warning "Runs started from a terminal"

    For a run you started by hand ([Runs started from a terminal](runs-from-a-terminal.md)), the job sheet names the Spectio run directory as the launch directory and reads an output as "absent" although the file is in your launch directory (DW-P3B04-01, seen on a Snakemake run). Use runs launched from Spectio for this view until it is fixed.

## Next

- [Runs started from a terminal](runs-from-a-terminal.md).
- [Progress page of milestone M9](../progress/W5/P3-M9.md).
