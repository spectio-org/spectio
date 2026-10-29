This logger connects Snakemake to [Spectio](https://github.com/spectio-org/spectio), an open-source run manager for HPC and Kubernetes that launches, monitors and relaunches Nextflow and Snakemake runs on your own cluster.

Version `0.0.0` holds the name and already works on its own: it writes each Snakemake log event as one JSON line to a file, so another program can follow a run. The bridge that reports a run to a Spectio server comes with Spectio's first release, 0.0.1. Spectio's documentation is at <https://spectio.pages.dev>.
