# snakemake-logger-plugin-spectio

A Snakemake logger plugin for [Spectio](https://github.com/weber8thomas/spectio), the tool that launches, monitors and steers Nextflow and Snakemake runs.

This early `0.0.0` release writes every Snakemake log event as one JSON line to a file, so another program can follow a run:

```bash
pip install snakemake-logger-plugin-spectio
snakemake --cores 1 --logger spectio --logger-spectio-file events.jsonl
```

Each line holds the time, the level, the event name (`job_info`, `job_finished`, `error`…), the message and the event's own fields (rule name, job ID…). The full Spectio bridge comes with Spectio's first release.
