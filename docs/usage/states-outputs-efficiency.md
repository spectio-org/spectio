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

A checkpoint rule carries a **Checkpoint** chip. While one is open the count reads "done / at least n", and the bar is hatched past the jobs known so far. The Summary says "The DAG grows after checkpoint …" and, once it ended, "DAG updated after a checkpoint (12 times): the job count includes the new jobs."

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
