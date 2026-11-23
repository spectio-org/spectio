---
icon: material/chart-timeline
hide: [navigation]
---
# Roadmap

**0.0.1 is built; its release candidate, 0.0.1-rc1, is being prepared.** This page says what it contains, what is left before the release, and what comes after. Spectio stays below 1.0 until it has been checked with several use cases and several groups.

## Built for 0.0.1

- **Engines:** Nextflow and Snakemake.
- **Where runs go:** SLURM through a login node, or one Linux machine. On a shared host the server listens on a Unix socket only.
- **Web interface:** the runs list; a run's detail (stages, tasks, logs, files, CPU and memory efficiency); launch from a schema-built form with resources and an extra config file; resume, copy to a new launch, cancel, pin and delete; environments; a pipeline catalog; file preview, including TIFF, OME-TIFF and OME-Zarr; search; notifications; a profile page.
- **Runs started from a terminal,** watched through the engine bridges.
- **Command line:** `init`, `doctor`, `serve`, `login` and `open`.
- **REST API** under `/api/v1`, with live events over SSE ([API and CLI](../api/index.md)).
- **Sign-in** with a single-use link, for one user per server.

## 0.0.1-rc1, the release candidate

The first tag is a release candidate, `v0.0.1-rc1` (`0.0.1rc1` on PyPI), so that people outside the project can install it from PyPI and try it before `0.0.1`. Its test campaign is the [RC1 acceptance matrix](../reviews/RC1-acceptance.md): unit tests, the browser tests against a real server, the SLURM test cluster, and the EMBL login node. It is tagged only when no cell of that matrix is a FAIL.

Known limits of the release candidate:

- **Snakemake on SLURM needs `snakemake-executor-plugin-slurm` 2.8.0 or later.** With an older plugin Spectio sees none of the run's jobs. The EMBL module `snakemake/9.23.1-foss-2025b` ships 2.6.1, so install Snakemake yourself there ([Installation](../installation/index.md#what-001-is-made-of)). `spectio doctor` prints the plugin's version.
- **The Nextflow bridge is not in the Nextflow plugin registry.** It ships inside the `spectio` package and `spectio init` puts it in place, so nothing is missing for a run Spectio launches.
- **One user per server,** signed in with a single-use link.
- **0.0.1 targets the EMBL cluster.** Other SLURM sites are not checked.

## Before 0.0.1 is released

- **Feedback on the release candidate,** and the fixes it calls for.
- **The publish setup** that the owner does on PyPI and GitHub: the trusted publisher and the protected release environment.
- **The owner's own checks on the EMBL login node:** opening Spectio from a laptop through the SSH tunnel, in a browser.
- **Decisions** the owner still has to confirm on a few open choices.

Until it is released, [install it from a checkout](../installation/index.md).

## After 0.0.1

- **0.0.2:** pipeline version detection, performance across runs, and, behind flags, the interactive workflow graph and runs that target one Nextflow module or one Snakemake rule.
- **Later, in no set order:**
    - QC gates between stages, with a review screen ([QC gates](../features/gates.md)).
    - Kubernetes, and a shared server with remote runners.
    - The hand-off of results to Depictio ([Depictio](../features/depictio.md)).
    - Accounts, roles and administration ([Administration](../features/administration.md)).
    - Relaunch with changed parameters in one step, and rerun from a stage.
    - Full scheduler monitoring.
    - Docker Compose and a Helm chart.
    - Webhooks and tokens for robots.
    - CWL and WDL engines.

## Ideas, not scheduled

- Other schedulers: LSF, PBS, SGE.
- GA4GH WES and TES interfaces.
