---
icon: material/book-open-variant
---
# How Spectio works

Spectio sits between you and your workflow engine. It does not replace Nextflow or Snakemake: it launches them on your cluster, follows them through their own events, explains failures, and relaunches them. Most pipelines simply run from start to end. Gates, stops between stages for a quality check, are optional.

## Five words

| Word | What it means |
|---|---|
| **Run** | One execution of a pipeline, with its parameters, samples and outputs. |
| **Stage** | A group of steps in a pipeline: for example *qc*, then *align*, then *quantify*. |
| **Gate** | *Optional.* A stop between two stages. The run waits there until someone decides. |
| **Decision** | Approve, exclude samples, change a parameter and rerun the stage, or stop. A person, an AI agent or a robot can decide. |
| **Runner** | The small program next to the compute (a SLURM login node, a Kubernetes cluster, a laptop) that starts the engine and reports back. |

## A run without gates

1. **Launch** from the web form, the CLI or the API, on the environment you choose.
2. **Watch** its stages, tasks, samples and logs, and what the scheduler does with its jobs.
3. **When something fails,** Spectio tells you why (out of memory, out of time, a tool error, a node lost) and proposes a change. Relaunch: finished work comes back from the cache.
4. **When it finishes,** outputs, reports and logs stay attached to the run, and can be handed to depictio.

## A run with a gate (optional)


![Stop at the QC gate, drop a sample, resume](../assets/diagrams/gate-resume_light.png#only-light)
![Stop at the QC gate, drop a sample, resume](../assets/diagrams/gate-resume_dark.png#only-dark)

1. **Launch.** You pick a pipeline and its parameters, and say "stop after *qc*".
2. **Stop at the gate.** Spectio uses the engine's own way of stopping, so the run ends cleanly after *qc*.
3. **Decide.** The gate shows the QC evidence. Here, sample S03 has 40 reads instead of 400, so the reviewer excludes it and approves.
4. **Resume.** Spectio starts the engine again with the new samplesheet. Everything already computed comes back from the cache.

This has been tested on a small test pipeline with both engines: after the QC gate, 25 of the 65 tasks come back from the cache. The cluster, the runner and the phone in the figure are the planned flow; they are not built yet.

## What it looks like in a terminal

The same stop and resume, with Snakemake, recorded from a real run:

<div class="asciinema-cast" data-cast="assets/casts/synthetic-gate.cast"></div>

## Next

- [Features](../features/index.md): what each part does.
- [API and CLI](../api/index.md): doing it without the web interface.
