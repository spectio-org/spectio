# nf-spectio

## Summary

`nf-spectio` is a Nextflow plugin that writes each run's events to the spool of
[Spectio](https://github.com/spectio-org/spectio), which launches, monitors and steers
Nextflow and Snakemake runs. Spectio reads the spool to show the run, its processes and its
tasks.

It observes the run through Nextflow's trace observer interface and is added next to the
pipeline's own plugins, never in their place. It never fails a run: when the spool cannot be
written, events are lost, not the run, and the error goes to `.spectio/bridge.err`. It sends
only the fields Spectio needs, never a task's script, its environment or its error report.

## Get Started

Requirements: Nextflow 25.04.0 or later (the plugin's manifest says
`Plugin-Requires: >=25.04.0`) and Java as Nextflow requires it.

A run that Spectio launches needs no setup: Spectio unpacks its own copy of the plugin into
Nextflow's plugins directory and enables it for that run.

For a run started from a terminal, enable the plugin for that run with the environment variable
`NXF_PLUGINS_DEFAULT`. Nextflow merges that list with the plugins the pipeline declares, so a
pipeline keeps its pinned plugins (tested on Nextflow 26.10.4 and 25.10.9,
[verification](https://github.com/spectio-org/spectio/blob/main/docs/reviews/verification-2026-10-29-nextflow-attach.md),
FC-318). Do not use `-plugins` or a `plugins` block in a config file for it: either replaces
the pipeline's plugin list
([Spectio architecture §13.8](https://github.com/spectio-org/spectio/blob/main/docs/specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal)).

When no copy of that version is in its plugins directory (`$NXF_PLUGINS_DIR`, by default
`$NXF_HOME/plugins`), Nextflow downloads the plugin; from Nextflow 25.10 it downloads plugins
only from the [Nextflow plugin registry](https://registry.nextflow.io/)
([migrating plugins](https://docs.seqera.io/nextflow/guides/migrate-plugin)). With a copy there, the run
starts with no registry contact, also with `NXF_OFFLINE=true`, which suits a cluster head job
without network (Nextflow `PluginUpdater.groovy:274-286` at `v26.10.4`, tested on 26.10.4 and
25.10.9 in the same verification, claim 11). Whether Nextflow 25.04 finds a plugin published
only to the registry is **[to be validated]**.

The plugin has no settings. With no Spectio variables set, it makes a run ID and writes:

- the spool, `.spectio/events/<run ID>-nf-spectio-<nnnn>.jsonl` in the launch directory;
- when `~/.spectio/` exists, a pointer `~/.spectio/observed/<run ID>.json`, so that a Spectio
  server of the same user finds the run.

`.spectio/` and every directory under it must be private to the user (mode 0700); the plugin
writes nothing through a symbolic link.

## Examples

Run a pipeline with the plugin added to its own plugins:

```bash
NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 nextflow run nf-core/rnaseq -profile test,docker --outdir results
```

Run it on a node without network, from a copy already in the plugins directory:

```bash
export NXF_PLUGINS_DIR=$HOME/.nextflow/plugins   # holds nf-spectio-0.0.1/
NXF_OFFLINE=true NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 nextflow run main.nf --outdir results
```

See what the run wrote:

```bash
ls .spectio/events/
head -n 1 .spectio/events/*-nf-spectio-0001.jsonl
```

## License

MIT, like the rest of [Spectio](https://github.com/spectio-org/spectio).
