# Runs

Launch, monitor and resume Nextflow and Snakemake runs from the browser. This is built in 0.0.1 ([installation](../installation/index.md)). The pages of [Usage](../usage/index.md) show each screen in turn.

- **Launch from a form.** The form is built from the pipeline's own parameter schema (nf-core `nextflow_schema.json`, Snakemake config schemas). You pick the engine (Spectio guesses it and you can change it), a profile, an [environment](../usage/environments.md), optional [resources and one extra config file](../usage/run-resources.md), or start from an entry of [your catalog](../usage/pipeline-catalog.md).
- **Follow every run** in one list: its state, its tasks, when it started and how long it ran. Filter by name and state, sort, pin a run, delete ended ones. The list updates live.
- **Open a run** to see its facts, its stages, its processes (Snakemake: rules) and tasks, its parameters and its logs. Each task has a sheet with its files, and its CPU and memory use against its request ([details](../usage/states-outputs-efficiency.md)).
- **Failures explained.** A failed run says why: out of memory, out of time, a tool error, a lost node, with the scheduler's state and reason on SLURM.
- **Cancel** a running run.
- **Resume** a failed or cancelled run: the engine starts again and finished work comes back from its cache. The dialog says what is reused.
- **Copy to a new launch** opens the launch form filled with a run's values, so you can change them. Relaunching with changed parameters in one step, and rerunning from one stage, come later.
- **Results and work directories** can be browsed and previewed in the browser ([details](../usage/browse-and-preview-files.md)).
- **Runs you started yourself** in a terminal show up too, for watching only ([details](../usage/runs-from-a-terminal.md)).

![The runs list](../assets/shots/app-runs-grid_light.webp#only-light)
![The runs list](../assets/shots/app-runs-grid_dark.webp#only-dark)

![Launching a pipeline](../assets/shots/app-launch_light.webp#only-light)
![Launching a pipeline](../assets/shots/app-launch_dark.webp#only-dark)

![A failed run: why it failed, and the log of the failing task](../assets/shots/app-run-detail-failed_light.webp#only-light)
![A failed run: why it failed, and the log of the failing task](../assets/shots/app-run-detail-failed_dark.webp#only-dark)
