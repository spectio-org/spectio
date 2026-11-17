---
icon: material/chart-gantt
---
# States, outputs and efficiency

The run page says what each process (Nextflow) or rule (Snakemake) did, and how much of its request it used. This page also covers the runs list.

!!! note "Not checked on SLURM yet"
    The screens below come from runs on a local executor, so there is no `sacct` and no SLURM request to show. The SLURM parts are described from the code and are **[to be validated]** on a cluster.

## States and checkpoints

Open a run, then **Summary**. Each rule has a state word. Pending means "jobs are planned and none has started"; the other words are:

| Word | Engine | Means |
|---|---|---|
| Waiting for checkpoint | Snakemake | a checkpoint has not finished; this rule's jobs may appear after it |
| Not needed in this run | Snakemake | the targets or an input function left the rule out; greyed, listed last |
| Up to date | Snakemake | its outputs already exist, so there is nothing to run |
| No task (condition or empty input) | Nextflow | the process never got a task: a `when:` was false or its input was empty |

A checkpoint rule carries a **Checkpoint** mark. Its sheet adds one line: "A checkpoint: once its jobs succeed, Snakemake updates the DAG from their outputs." While one is open the count reads "done / at least n", and the bar is hatched past the jobs known so far. The Summary says "The DAG grows after checkpoint …" and, once the run ended, "DAG updated after a checkpoint (12 times): the job count includes the new jobs."

![A Snakemake run's Summary: the rules, the Checkpoint mark on split, the DAG-updated line, the states legend](../assets/shots/app-run-rules_light.webp#only-light)
![A Snakemake run's Summary: the rules, the Checkpoint mark on split, the DAG-updated line, the states legend](../assets/shots/app-run-rules_dark.webp#only-dark)

*A finished Snakemake 9.27.1 run of the synthetic test pipeline, launched from Spectio on a local executor: 88 jobs, 12 DAG updates.*

Nextflow does not report a task that `when:` filtered out, and a process left out by a Groovy `if` is never created ([research note of 2026-11-07](https://github.com/spectio-org/spectio/blob/main/docs/research/dag-temp-slurm-efficiency-2026-11-07.md#4-nextflow-conditional-execution-and-processes-that-never-run)). Spectio cannot tell these apart, so the list says "Processes the script does not call in this run are not listed."

## Efficiency by process or rule

On **Tasks** (Snakemake: **Jobs**), pick **By process** (**By rule**). Each column header is a sort button.

### Order of the rows { #order-of-the-rows }

The table opens in **Pipeline order**: the rules in the order the pipeline runs them. Above the table, the radio group **Order** offers **Pipeline order** and **A to Z**. A click on a column header sorts by that column and leaves both radios unchecked.

- **Snakemake:** the order comes from the links of the rule graph (a rule after the rules it reads from). Rules with no link to each other keep the order of the rule files.
- **Nextflow:** the order is the order in which the processes were first seen.
- **A to Z** compares the last part of the name by code point, so capital letters sort before small ones.
- **A rule that joins the DAG after a checkpoint is not placed by its links.** It has no link in the first rule graph, so it comes first. In the shot below, `align` runs after the checkpoint `split` and is listed above `make_reads`.

![By rule on a finished Snakemake run, Pipeline order checked; align is listed first](../assets/shots/app-run-by-rule-order_light.webp#only-light)
![By rule on a finished Snakemake run, Pipeline order checked; align is listed first](../assets/shots/app-run-by-rule-order_dark.webp#only-dark)

![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_light.webp#only-light)
![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_dark.webp#only-dark)

- **CPU eff.** and **Mem eff.** are a mean and a maximum over the jobs measured. "low" and "near limit" are words, not only colours.
- **CPUs asked, Memory asked, Time limit** show the most common request. **Requests** reads "vary" on a row when the jobs of the process asked for different values.
- A line above the table lists the processes whose jobs used under 25 % of their memory.
- **Read the screenshot with care:** it is a local run of very short jobs, so every process is flagged "low" with 0 % to 1 % memory. Real jobs on a cluster will not look like this.
- The numbers come from `sacct` once a SLURM job has ended, else from the engine's trace (Nextflow) or its benchmark file (Snakemake). On a local executor there is no `sacct`. A Snakemake rule with no `benchmark:` shows "—".

On a phone the table becomes one card per process, with a **Sort by** select that also offers **Pipeline order**.

![By rule on a phone: the radio group, then the Sort by select showing Pipeline order, then the first rule card](../assets/shots/app-run-by-rule-order-phone_light.webp#only-light)
![By rule on a phone: the radio group, then the Sort by select showing Pipeline order, then the first rule card](../assets/shots/app-run-by-rule-order-phone_dark.webp#only-dark)

## One process and its tasks

Open a process name from the Summary. The sheet shows its counts and efficiency, then **Tasks** (Snakemake: **Jobs**) under a header: **Task** (Snakemake: **Job**) and **State**.

- Each row is a button. Its accessible name ends with its state, "Open task ALIGN (S01.chunk0000), Succeeded".
- **Load more** adds rows below.
- **While the run is active** the sheet refreshes on each live update and keeps the rows that Load more added.
- **A failed read** puts an alert above the rows. The rows and the focused button stay.

![The sheet of process ALIGN: counts, efficiency, then Tasks under a Task and State header](../assets/shots/app-run-process-columns_light.webp#only-light)
![The sheet of process ALIGN: counts, efficiency, then Tasks under a Task and State header](../assets/shots/app-run-process-columns_dark.webp#only-dark)

## One job

Open a job with its **Files** button. The sheet has the job's **Efficiency**, with its source or the reason it is missing, then its files.

![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_light.webp#only-light)
![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_dark.webp#only-dark)

On SLURM the sheet also shows the request that is set (partition, CPUs, memory, time limit and the others), **Allocated** when it differs from the request, and "Custom sbatch options set". It never shows the text of those options.

When SLURM accounting cannot answer, the Efficiency block says "No accounting for this job" and gives the reason: "local run", "sacct not found or accounting off", "no SLURM job ID", "not in SLURM accounting", "reused from an earlier run, no job ran", or "the window is over the site's sacct limit (MaxQueryTimeRange)". The last one means the site's accounting database refused the time window of the `sacct` call, so Spectio stops asking for that job instead of asking again every 10 minutes. That case was tested without a real accounting database that sets `MaxQueryTimeRange`: **[to be validated]**.

### Measured numbers fill in after `sacct` { #measured-fills-in-after-sacct }

Spectio sends no event when `sacct` answers a job that has ended, so after a run ends the page reads the processes again every 30 s, up to 10 times in one visit, while at least one job is still waiting for `sacct`. Reused tasks of a resumed run never keep the page reading.

## A log that cannot be read

When the Logs tab or a job's files cannot find the run's directory, the answer says which case it is. Both messages name the directory that was tried, a path under your own runs root.

| Answer | Means |
|---|---|
| `410 log-cleaned` | the runs root is there and is the one the run was recorded under, and the run's directory is gone |
| `409 run-dir-unreachable` | the runs root is not there, or the run was recorded under another runs root (for example after `runs_root` changed) |

A run you started in a terminal has no recorded runs root and always answers `410`. A case seen once on a login node, a `410` while the file exists, was not reproduced: the cause is **[to be validated]**.

## The Summary's last lines and the full log

![The Summary of a run: Facts, Processes, and on the right the Engine log with its last lines and the button Open the full engine log](../assets/shots/app-run-engine-log_light.webp#only-light)
![The Summary of a run: Facts, Processes, and on the right the Engine log with its last lines and the button Open the full engine log](../assets/shots/app-run-engine-log_dark.webp#only-dark)

- **The last lines open the log.** A click on them, or the button **Open the full engine log →** (on a failed run, "head errors"), opens the Logs tab on the same source.
- **A click that ends a text selection does not open it,** so you can still copy a line.
- **Back to Summary** sits above the log's tools and returns to the Summary. The address carries `&from=summary`, so it survives a reload.

## The runs list

![The runs list as a grid: seven demo runs, a coloured rail on each row, filters above](../assets/shots/app-runs-grid_light.webp#only-light)
![The runs list as a grid: seven demo runs, a coloured rail on each row, filters above](../assets/shots/app-runs-grid_dark.webp#only-dark)

*Seven seeded run records, not pipeline runs: Tasks, Started and Duration read "—".*

- **The default order is newest first, pinned runs first,** with filters above the table (name and state). The headers of Run, State, Started and Duration sort on the server. **Load more** adds rows.
- **Keyboard.** The grid takes Tab and Enter for its cells. Move to the Run cell with the arrow keys and press **Enter** to open the run.
- **Below 1100 px** the Started column drops.
- **On a phone** the list is one card per run.

### Select, sort, pin and delete runs

![The runs table with two rows selected: a bar above the table reads "2 selected" with Delete... and Clear selection; liver-qc-batch-7 is pinned and first](../assets/shots/app-runs-actions_light.webp#only-light)
![The runs table with two rows selected, dark](../assets/shots/app-runs-actions_dark.webp#only-dark)

- **Select.** Each row has a checkbox named "Select run <name>"; the header box selects the page. A bar then shows "n selected", **Delete…** and **Clear selection**.
- **Sort.** Click the header of Run, State, Started or Duration; a second click reverses it and a third clears it, back to newest first. The address keeps it (`/runs?sort=name`).
- **Pin.** The pin button in a row pins or unpins one run. **Pin** and **Unpin** are also in Run detail's header. Pinned runs come first in every sort.
- **Delete.** **Delete…** opens a sheet: the runs it names, "Spectio forgets these runs: they leave the list, the counts and Home. Their files stay where they are.", and a box, off by default, **Also delete their run directories**. **Cancel** has the focus. A live run cannot be deleted; a refusal names the run and why, and nothing is deleted. **Delete…** is also in Run detail's header, for an ended run.
- **On a phone** the cards have a checkbox and the bar's buttons are at least 44 px high. They have no pin yet.

![The Delete sheet for two runs: rnaseq-treatC-ctrl Failed and rnaseq-pilot Cancelled, the box Also delete their run directories unchecked, and a note on what it removes](../assets/shots/app-runs-delete_light.webp#only-light)
![The Delete sheet for two runs, dark](../assets/shots/app-runs-delete_dark.webp#only-dark)

What the screens call, and what the API does:

- **Delete.** `POST /runs:delete` with `{"ids": [...], "directories": false}` marks 1 to 200 ended runs deleted, all or nothing. A deleted run leaves the list, the summary and every `/runs/{id}` route (`404`). The run's directory stays unless `directories` is `true`.
- **With `directories: true`** Spectio also removes each run's own directory, `<runs root>/<run ID>`, and nothing else, without following a link. It refuses, before deleting anything, a run that started from a terminal (its launch directory is yours), a run whose head has not been seen to exit, a directory that is not where the runs root says, and a directory that a run you did not select shares (a resumed run shares its parent's: delete them together).
- **Pin.** `PATCH /runs/{id}` with `{"pinned": true}`. `GET /runs` lists pinned runs first in every sort but `-ended_at`; `sort=` takes `-created_at` (the default), `-ended_at`, `name`, `state`, `started_at` and `duration`, each also with `-`, and anything else is `422`.
- A delete against a real login node is **[to be validated]**.

## A run that fails on purpose

For the synthetic test pipelines of the repository, the profile `fail_demo` makes `COMPARE` (Snakemake: `compare`) for `treatA` exit 1, so the run ends **Failed** with a tool error. Every synthetic task also writes lines to its stdout and stderr, so the log views have something to show: the parameter `verbosity` is `quiet`, `normal` (the default) or `loud` (about 1000 lines and 90 KB per stream, more than the 64 KiB a log view shows first). The Snakemake profile is for the local executor only.

![A failed run launched with the profile fail_demo: Why it failed, and the sheet of the COMPARE task with its WARN, INFO and ERROR lines](../assets/shots/app-run-failed-synth_light.webp#only-light)
![A failed run launched with the profile fail_demo: Why it failed, and the sheet of the COMPARE task with its WARN, INFO and ERROR lines](../assets/shots/app-run-failed-synth_dark.webp#only-dark)

*Nextflow 26.10.4 on a local executor. The SLURM job log of a Snakemake run, where the tool's stderr is copied, was not run:* **[to be validated]**.

## Temporary and protected outputs

For a Snakemake job, the sheet has an **Outputs** tab. It opens first when the rule has no log file. Each output shows "present", "not yet", "absent", "deleted by Snakemake (temporary)" or "write-protected".

![A Snakemake job's sheet on its Outputs tab](../assets/shots/app-run-job-outputs_light.webp#only-light)
![A Snakemake job's sheet on its Outputs tab](../assets/shots/app-run-job-outputs_dark.webp#only-dark)

- Snakemake's events do not say that an output is `temp()`. Spectio shows it only after Snakemake deleted the file, and never guesses.
- With `--notemp` nothing is deleted; the run's facts say "Temporary files kept (--notemp)".
- For Nextflow the run's facts say "Work directory cleaned after success (cleanup = true)" when it is set, and a cleaned job's files say so.

!!! warning "Runs started from a terminal"
    For a run you started by hand ([Runs started from a terminal](runs-from-a-terminal.md)), the job sheet names the Spectio run directory as the launch directory and reads an output as "absent" although the file is in your launch directory. Use runs launched from Spectio for this view.

## Next

- [Runs started from a terminal](runs-from-a-terminal.md).
- [Browsing and previewing files](browse-and-preview-files.md).
