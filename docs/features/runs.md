# Runs

!!! note "Designed, planned from 0.1"

- **Launch from a form.** The form is built from the pipeline's own parameter schema (nf-core `nextflow_schema.json`, Snakemake config schemas). The samplesheet is checked before anything starts.
- **Follow every run** in one table: its stage, its gates, its failures and how long it has been running.
- **Open a run** to see its stages, tasks, samples, logs, resources and what the cluster is doing with it.
- **Failures explained:** out of memory, out of time, a tool error, a lost node, with the change to make.
- **Relaunch** with changed parameters or more resources, and resume from the cache.
- **Observe runs you started yourself** from the command line: they show up too.

![Every run in one table](../assets/shots/runs_light.webp)

![Launching a pipeline](../assets/shots/launch_light.webp)

Design details: [UI spec](../specs/ui-spec.md), [API and data model](../specs/api-and-data-model.md).
