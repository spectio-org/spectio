---
icon: material/console
---
# Runs started from a terminal

!!! note "The bridges are not published yet"
    `nf-spectio` is not in the Nextflow plugin registry and `snakemake-logger-plugin-spectio` 0.0.1 is not on PyPI. The `spectio` wheel carries both bridges, and `spectio init` unpacks the Nextflow one. Until the Snakemake one is on PyPI, the `pip install` line below does not work. Nothing here has run on a cluster.

You can start a run by hand in a shell, as you always did, and still see it in Spectio. Spectio does not start it, so it can only **watch**: no Cancel, no Resume, no signal to the head.

This page says what you type and what you see.

## How it works

1. **A bridge runs inside your engine.** `nf-spectio` for Nextflow, `snakemake-logger-plugin-spectio` for Snakemake 9. With no `SPECTIO_*` variable set, each makes a run ID.
2. **It writes two things.** The run's events go to `<launch directory>/.spectio/events/`. A small pointer file goes to `~/.spectio/observed/<run ID>.json` (mode 0600). The pointer holds the run ID, the launch directory, the engine and its version, the host, and the head's PID fields. It holds no environment and no parameters.
3. **The server finds the pointer** when it starts and whenever `~/.spectio/observed/` changes, then reads the events. The run appears with the origin `cli-observed`.
4. **When the run ends,** the pointer moves to `~/.spectio/observed/ended/`.

If `~/.spectio` does not exist, the bridge writes nothing and says nothing. The run never fails because of the bridge.

## Nextflow

Name the bridge in one variable, in front of your usual command:

```console
$ NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 nextflow run <pipeline> …
```

- Nextflow merges that list with the plugins the pipeline declares, so an nf-core pipeline keeps its own. Never use `-plugins`, and never a `plugins` block in a config file: each replaces a list.
- **The plugin directory must exist.** `spectio init` unpacks it from the wheel into `$NXF_PLUGINS_DIR`, by default `$NXF_HOME/plugins`, and prints where. With wheels built from a checkout, in a fresh demo home, it printed `nf-spectio in ~/.nextflow/plugins/nf-spectio-0.0.1`, and the run above then wrote its pointer. What Nextflow does when the variable names a version with no directory and no registry release is **[to be validated]**.
- An `export` in your shell profile loads the bridge into every later run. It is opt-in; a helper that offers it (`spectio login`) comes later.
- On Seqera Platform, the same variable goes in the head job of the compute environment ([Seqera, HPC compute environments](https://docs.seqera.io/platform-cloud/compute-envs/hpc)). How Platform's launch command treats it is **[to be validated]** with a real launch.

## Snakemake 9

Install the logger in the environment Snakemake runs from, pinned, and name it:

```console
$ pip install snakemake-logger-plugin-spectio==0.0.1
$ snakemake --cores 2 --logger spectio
```

- `--logger` takes a list. If you already use another logger, name it too: `--logger <yours> spectio`. Whether `--logger spectio` alone replaces the loggers of a profile is **[to be validated]**.
- **`snakemake -d <dir>` is not handled yet:** the spool and the pointer go to the directory you ran the command in, not to `<dir>`, and the run's log is not found there.
- Snakemake writes no end event. See [how the end is decided](#how-the-end-is-decided).

## What you see

| Where | What |
|---|---|
| The runs list | the run, origin `cli-observed`, named after its launch directory |
| The run header | "Not checked (on `<node>`, started from a terminal)" when the server is not on that node and boot; otherwise the head's state |
| Actions | none: no Cancel, and a launch or cancel command for such a run is answered `failed` before any launcher is called |

The **workflow** of such a run is its launch directory, one engine per directory. A Snakemake run in a directory that already holds a Nextflow run, or the reverse, is not shown (assumed, not confirmed by the owner).

"Checked" means the pointer's host name and boot ID are the server's. Only then can the server tell that a head is gone. On another login node, only the engine's own end event ends the run.

### How the end is decided

- **Nextflow:** the bridge's terminal event ends the run. With no event and a head the server sees gone, the run ends `failed`.
- **Snakemake:** no event and no exit code. When the head is gone (same host and boot), the run is `succeeded` if the last progress shows done equal to total, no task failed and no error came after it. Otherwise it is `failed`, with a message that says the end is assumed. **This is a guess, not an observation** (assumed, not confirmed by the owner). A Snakemake run on another host or boot never ends, and a run with no progress record (an up-to-date rerun, `--dry-run`) ends `failed`.

## See it run

The cast runs real Nextflow on the synthetic test pipeline with the real `nf-spectio`, then a real `spectio serve` in a demo home on the demo host `demo-hpc-login1`. Steps: the run started by hand; the pointer (0600) and the spool; the server listing the run as `cli-observed`; the pointer moved to `ended/`. The ticket is masked by a visible `sed`. The cast shows `"alive":true` for the finished Nextflow run, which is the second limit below.

<div class="asciinema-cast" data-cast="assets/casts/spectio-terminal-run.cast"></div>

## Limits in 0.0.1

- **No cluster.** Nothing here ran on a login node, with an engine started in a login shell, or on a shared home. The Snakemake end rule was seen once, with Snakemake 9.27.1 on one machine: a run of the synthetic pipeline was still `running` 6 s after it finished and `succeeded` 75 s later, with the head not alive. What Snakemake 9 logs at the end of other runs is **[to be validated]**.
- **A finished Nextflow run can still show its head as alive.** The API says `"alive": true` and the run header says "Ending", minutes after the run ended and its pointer moved to `ended/`. A Snakemake run, ended from its spool, shows `"alive": false`. This is a known defect.
- **The Outputs tab is wrong for such a run.** For a run you started by hand, the job sheet names the Spectio run directory as the launch directory and reads an output as "absent" although the file is in your launch directory. Use runs launched from Spectio for that view.
- **Install lines pin a version by hand,** so check the version you installed.
