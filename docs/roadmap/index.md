---
icon: material/chart-timeline
hide: [navigation]
---
# Roadmap

**0.0.1 is built and not released yet.** This page says what it contains, what is left before the release, and what comes after. Spectio stays below 1.0 until it has been checked with several use cases and several groups.

## Built for 0.0.1

- **Engines:** Nextflow and Snakemake.
- **Where runs go:** SLURM through a login node, or one Linux machine. On a shared host the server listens on a Unix socket only.
- **Web interface:** the runs list; a run's detail (stages, tasks, logs, files, CPU and memory efficiency); launch from a schema-built form with resources and an extra config file; resume, copy to a new launch, cancel, pin and delete; environments; a pipeline catalog; file preview, including TIFF, OME-TIFF and OME-Zarr; search; notifications; a profile page.
- **Runs started from a terminal,** watched through the engine bridges.
- **Command line:** `init`, `doctor`, `serve`, `login` and `open`.
- **REST API** under `/api/v1`, with live events over SSE ([API and CLI](../api/index.md)).
- **Sign-in** with a single-use link, for one user per server.

## Before 0.0.1 is released

- **End-to-end checks on a SLURM test cluster,** including cancelling a run and restarting the server.
- **The publish workflow,** so the packages go to PyPI and the Nextflow bridge to its plugin registry.
- **The release setup on GitHub** (a release bot, a protected release environment, version tags).
- **A last clean-up of the interface styles.**
- **The owner's checks on the EMBL login node:** opening Spectio from a laptop, and deleting a run there.
- **Decisions** the owner still has to confirm on a few open choices.

Until it is released, [install it from a checkout](../installation/index.md).

## After 0.0.1

- **0.0.2:** pipeline version detection, and performance across runs.
- **Later, in no set order:**
    - QC gates between stages, with a review screen ([QC gates](../features/gates.md)).
    - Kubernetes, and a shared server with remote runners.
    - The hand-off of results to depictio ([depictio](../features/depictio.md)).
    - Accounts, roles and administration ([Administration](../features/administration.md)).
    - Relaunch with changed parameters in one step, and rerun from a stage.
    - Full scheduler monitoring.
    - Docker Compose and a Helm chart.
    - Webhooks and tokens for robots.
    - CWL and WDL engines.

## Ideas, not scheduled

- Other schedulers: LSF, PBS, SGE.
- GA4GH WES and TES interfaces.
