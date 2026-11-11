---
icon: material/book-open-variant
---
# How Spectio works

Spectio sits between you and your workflow engine. It does not replace Nextflow or Snakemake: it launches them on your cluster, follows them through their own events, explains failures, and resumes them. 0.0.1 serves one user on one machine, from a browser.

## Four words

| Word | What it means |
|---|---|
| **Run** | One execution of a pipeline, with its parameters and outputs. |
| **Stage** | A group of steps in a pipeline: for example *qc*, then *align*, then *quantify*. Stages come from a `spectio.yml` file or are detected from the pipeline's structure. |
| **Environment** | Where a run's tasks go: this machine, or SLURM with a partition and an account. See [Environments](environments.md). |
| **Head** | The engine process that drives a run. On a SLURM login node, Spectio starts it in its own tmux session, where you can attach to it. |

## A run, from start to end

1. **Launch** from the web form. Pick a pipeline from [your catalog](pipeline-catalog.md) or type its path, fill its parameters (the form is built from the pipeline's own schema), choose the [environment and the resources](run-resources.md), and press Launch.
2. **Watch** it. The runs list updates as events arrive. A run shows its stages, its processes (Snakemake: rules) and tasks, its logs, and how much of its request each process used ([States, outputs and efficiency](states-outputs-efficiency.md)).
3. **When something fails,** the run page says why (out of memory, out of time, a tool error, a node lost). **Resume** it: finished work comes back from the engine's cache. Or **Copy to a new launch**, to change the parameters.
4. **When it finishes,** its results and work directories stay in the browser, with a preview for text, tables, JSON, images, TIFF and OME-Zarr ([Browsing and previewing files](browse-and-preview-files.md)).

Runs you start by hand in a terminal show up too, for watching only ([Runs started from a terminal](runs-from-a-terminal.md)).

!!! note "Not in 0.0.1"
    Quality gates (a stop between two stages for a check), Kubernetes, the hand-off to depictio, accounts and administration come in later versions. See the [roadmap](../roadmap/index.md).

## Where to start

- [Installation](../installation/index.md): the packages and how to try 0.0.1 from a checkout.
- [Signing in](sign-in.md): the link that opens Spectio on your own machine.
- [Keeping the server running](keep-the-server-running.md): `spectio serve --detach`.
- [Opening from your laptop](open-from-your-laptop.md): `spectio open` and the SSH tunnel.

## The screens

- [States, outputs and efficiency](states-outputs-efficiency.md): checkpoints, temporary files, CPU and memory use, the runs list.
- [Browsing and previewing files](browse-and-preview-files.md): the results and work directories, and the viewers.
- [Your pipeline catalog](pipeline-catalog.md): saved pipelines, picked on Launch.
- [Environments](environments.md): where a run's tasks go, kept in a file you own.
- [Your profile](profile.md): who the server runs as, your session, the config paths and the theme.
- [Search and notifications](search-and-notifications.md): find a run or a pipeline from the top bar; the bell.
- [Run resources and an extra config file](run-resources.md): CPUs, memory and time per task, and one config file, for one run.

See also [Features](../features/index.md) and the [API and CLI](../api/index.md).
