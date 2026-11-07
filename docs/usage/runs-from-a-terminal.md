---
icon: material/console
---
# Runs started from a terminal

!!! note "Built on the integration branch, not released yet"

    This works today from a checkout (batch [P3-B03](../progress/W5/P3-M6.md#task-25-pointer-file-in-both-bridges-the-server-finds-and-shows-the-run), 2026-11-07). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **Neither bridge is published yet:** `nf-spectio` is not in the Nextflow plugin registry and `snakemake-logger-plugin-spectio` 0.0.1 is not on PyPI ([FU-P3-51](../progress/W5/P3-M6.md#follow-ups-of-tasks-25-and-26), [inbox #66](../reviews/inbox.md#66-claim-the-four-package-names-and-confirm-how-the-bridges-are-released)). The commands below were run with the wheels the batch built. Nothing here ran on a cluster.

You can start a run by hand in a shell, as you always did, and still see it in Spectio. Spectio does not start it, so it can only **watch**: no Cancel, no Resume, no signal to the head.

The rules are owned by [architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal) and [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (requirement 12). This page says what you type and what you see.

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

- Nextflow merges that list with the plugins the pipeline declares, so an nf-core pipeline keeps its own. Never use `-plugins`, and never a `plugins` block in a config file: each replaces a list ([architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal)).
- **The plugin directory must exist.** `spectio init` unpacks it from the wheel into `$NXF_PLUGINS_DIR`, by default `$NXF_HOME/plugins`, and prints where. With the wheels the batch built, in a fresh demo home, it printed `nf-spectio in ~/.nextflow/plugins/nf-spectio-0.0.1`, and the run above then wrote its pointer. What Nextflow does when the variable names a version with no directory and no registry release is **[to be validated]**.
- An `export` in your shell profile loads the bridge into every later run. It is opt-in; a helper that offers it (`spectio login`) comes later ([architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal)).
- On Seqera Platform, the same variable goes in the head job of the compute environment ([Seqera, HPC compute environments](https://docs.seqera.io/platform-cloud/compute-envs/hpc)). How Platform's launch command treats it is **[to be validated]** with a real launch.

## Snakemake 9

Install the logger in the environment Snakemake runs from, pinned, and name it:

```console
$ pip install snakemake-logger-plugin-spectio==0.0.1
$ snakemake --cores 2 --logger spectio
```

- `--logger` takes a list. If you already use another logger, name it too: `--logger <yours> spectio`. Whether `--logger spectio` alone replaces the loggers of a profile is **[to be validated]**.
- **`snakemake -d <dir>` is not handled yet:** the spool and the pointer go to the directory you ran the command in, not to `<dir>`, and the run's log is not found there (CR-P3T25-08 (r1), FU-P3-50).
- Snakemake writes no end event. See [how the end is decided](#how-the-end-is-decided).

## What you see

| Where | What |
|---|---|
| The runs list | the run, origin `cli-observed`, named after its launch directory |
| The run header | "Not checked (on `<node>`, started from a terminal)" when the server is not on that node and boot; otherwise the head's state |
| Actions | none: no Cancel, and a launch or cancel command for such a run is answered `failed` before any launcher is called |

The **workflow** of such a run is its launch directory, one engine per directory. A Snakemake run in a directory that already holds a Nextflow run, or the reverse, is not shown ([inbox #113](../reviews/inbox.md#113-assumed-how-a-snakemake-run-started-from-a-terminal-ends-p3-task-25) rule 2, assumed).

"Checked" means the pointer's host name and boot ID are the server's. Only then can the server tell that a head is gone. On another login node, only the engine's own end event ends the run.

### How the end is decided

- **Nextflow:** the bridge's terminal event ends the run. With no event and a head the server sees gone, the run ends `failed`.
- **Snakemake:** no event and no exit code. When the head is gone (same host and boot), the run is `succeeded` if the last progress shows done equal to total, no task failed and no error came after it. Otherwise it is `failed`, with a message that says the end is assumed. **This is a guess, not an observation** ([inbox #113](../reviews/inbox.md#113-assumed-how-a-snakemake-run-started-from-a-terminal-ends-p3-task-25) rule 1, assumed). A Snakemake run on another host or boot never ends, and a run with no progress record (an up-to-date rerun, `--dry-run`) ends `failed` (FU-P3-50).

## See it run

The cast runs real Nextflow on the synthetic test pipeline with the real `nf-spectio`, then a real `spectio serve` in a demo home on the demo host `demo-hpc-login1`. Steps: the run started by hand; the pointer (0600) and the spool; the server listing the run as `cli-observed`; the pointer moved to `ended/`. The ticket is masked by a visible `sed`. The cast shows `"alive":true` for the finished Nextflow run, which is the second open point below.

<div class="asciinema-cast" data-cast="assets/casts/spectio-terminal-run.cast"></div>

## Not built or not checked

- **A cluster.** Nothing here ran on a login node, with an engine started in a login shell, or on a shared home. The Snakemake end rule was seen once, with Snakemake 9.27.1 on one machine: a run of the synthetic pipeline was still `running` 6 s after it finished and `succeeded` 75 s later, with the head not alive. What Snakemake 9 logs at the end of other runs is **[to be validated]**.
- **A finished Nextflow run still shows its head as alive.** The API says `"alive": true` and the run header says "Ending", minutes after the run ended and its pointer moved to `ended/`. The API reads `alive` as "the launch has no `exited_at`" (`runs_read.py:138`), and `exited_at` is set only by a head report (`projector/ingest.py:123-126`); a run that ended on the engine's own event seems never to get one (read in the code, not traced further). A Snakemake run, ended from its spool, shows `"alive": false`. Found while writing this page (DW-P3B03-01, FU-P3-50).
- **No screenshot.** The "Not checked" header has no screenshot yet: the Playwright smoke has no terminal run (FU-P3-50).
- **Pins.** Every install line on this page pins a version by hand. The test the plan names, `test_guide_pins_bridge_versions`, is not written (FU-P3-50).
- **The rest of the open list:** [FU-P3-50 on the milestone page](../progress/W5/P3-M6.md#follow-ups-of-tasks-25-and-26).
