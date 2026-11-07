# snakemake-logger-plugin-spectio

A Snakemake logger plugin that writes each run's events to the spool of
[Spectio](https://github.com/spectio-org/spectio), which launches, monitors and steers
Nextflow and Snakemake runs. Spectio reads the spool to show the run, its rules and its jobs.

It is added to Snakemake's own output, never in its place: Snakemake keeps its terminal output
and its `.snakemake/log/` file. It never fails a run: when the spool cannot be written, events
are lost, not the run.

## Requirements

Snakemake 9 or later (the logger plugin interface, `snakemake-interface-logger-plugins` 1.1
to 2.x).

## Usage

Install it in the environment that runs Snakemake, then name it with `--logger`:

```bash
pip install snakemake-logger-plugin-spectio
snakemake --logger spectio --cores 4
```

A run that Spectio launches sets `SPECTIO_RUN_ID`, `SPECTIO_LAUNCH_N` and `SPECTIO_SPOOL_DIR`,
and the plugin writes there. A run started by hand sets none of them: the plugin then writes the
spool in `.spectio/events/` of the directory Snakemake starts in and, when `~/.spectio/` exists,
a pointer in `~/.spectio/observed/` so that a Spectio server of the same user finds the run.

The plugin has no settings. It sends only the fields Spectio needs and never the job's shell
command or its environment.
