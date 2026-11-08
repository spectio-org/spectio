---
icon: material/chart-gantt
---
# States, outputs and efficiency

!!! note "Built on the integration branch, not released yet"

    This works today from a checkout (batch [P3-B04](../progress/W5/P3-M9.md#batch-p3-b04), 2026-11-08). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **Nothing here ran on SLURM:** the screens below come from runs on a local executor, so there is no `sacct` and no SLURM request to show. The `slurm-mini` check waits for P1 Task 22.

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

![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_light.webp#only-light)
![Tasks, By process: CPU and memory efficiency, the request and the usage of each process](../assets/shots/app-run-by-process_dark.webp#only-dark)

- **CPU eff.** and **Mem eff.** are shown as a mean and a maximum over the jobs measured. "low" and "near limit" are words, not only colours.
- **CPUs asked, Memory asked, Time limit** show the most common request. **Requests** reads "vary" on a row when the jobs of the process asked for different values. The API has one flag for the three, so the page does not say which ([FU-P3-55](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b04)).
- A line above the table lists the processes whose jobs used under 25 % of their memory.
- **Read the screenshot with care:** it is a local run of very short jobs, so every process is flagged "low" with 0 % to 1 % memory and a 0 B peak. Real jobs on a cluster will not look like this.
- The numbers come from `sacct` once a SLURM job has ended, else from the engine's trace (Nextflow) or its benchmark file (Snakemake). On a local executor there is no `sacct`. A Snakemake rule with no `benchmark:` shows "—", as in the synthetic pipeline.

On a phone the table becomes one card per process, with a **Sort by** select. The shot below is scrolled to the first card, which is cut by the tab bar.

![By process on a phone, scrolled to the waste lines and the first process card](../assets/shots/app-run-by-process-phone_light.webp#only-light)
![By process on a phone, scrolled to the waste lines and the first process card](../assets/shots/app-run-by-process-phone_dark.webp#only-dark)

## One job

Open a job with its **Files** button. The sheet has the job's **Efficiency**, with its source or the reason it is missing, then its files.

![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_light.webp#only-light)
![A Nextflow task's sheet: Efficiency from the trace, the low flag, the work directory and its files](../assets/shots/app-run-task-efficiency_dark.webp#only-dark)

On SLURM the sheet also shows the request that is set (partition, CPUs, memory, time limit and the others), **Allocated** when it differs from the request, and "Custom sbatch options set". **It never shows the text of those options.** None of this was run on a cluster **[to be validated]**.

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
