# Spectio and other tools

!!! note "Spectio is in design: its row describes what is specified, not what ships"

    What ships in which version: [development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version). Owner of this page: [documentation system §1](../specs/documentation-system.md#1-site-structure). Every cell is sourced in the [landscape note of 2026-10-26](../research/landscape-2026-10-26.md).

A neutral, factual comparison, with no pricing. Spectio is meant to sit next to these tools, not to replace them ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)).

| Tool | Engines | Where it runs | Launch from UI or API | Live monitoring | Stop at a stage, review evidence, resume | Standards | Licence | Checked on |
|---|---|---|---|---|---|---|---|---|
| Spectio (in design) | Nextflow, Snakemake; CWL and WDL later | self-hosted; runners next to the compute (local, Slurm, Kubernetes) under the user's own account | yes | yes (engine plugins) | yes (gates with checks and evidence) | RO-Crate export; GA4GH WES facade (planned) | MIT | [specs](../map.md) |
| Seqera Platform | Nextflow | Seqera Cloud, or Enterprise on premises; reaches HPC over SSH by default, Tower Agent where SSH is not allowed; Slurm, LSF, PBS Pro, Grid Engine, Moab ([Seqera HPC docs](https://docs.seqera.io/platform-cloud/compute-envs/hpc)) | yes | yes | resume and relaunch, for Platform launches only; no review gate | — | proprietary | [2026-10-26](../research/landscape-2026-10-26.md#seqera-platform-cloud-enterprise) |
| nf-shard | Nextflow (Tower protocol) | self-hosted | no | yes | no | — | MIT; unmaintained since 2024 | [2026-10-26](../research/landscape-2026-10-26.md#nf-shard) |
| panoptes | Snakemake ≥ 9 (logger plugin 0.3.0; server 1.6.2, 2026-10-24) | self-hosted | no | yes | no (its cancel endpoint only marks a database row) | — | MIT | [2026-10-26](../research/landscape-2026-10-26.md#panoptes) |
| snkmt | Snakemake ≥ 9 | local terminal (SQLite, NFS-aware) | no | yes | no | — | MIT | [2026-10-26](../research/landscape-2026-10-26.md#snkmt) |
| FlowO | Snakemake ≥ 9 (server ≥ 9.23) | self-hosted (Docker Compose), reads outputs through a shared mount | no | yes (SSE), plus a versioned workflow catalogue, users and an MCP endpoint | none found **[to be validated]** | — | MIT | [2026-10-26](../research/landscape-2026-10-26.md#flowo) |
| Sapporo | CWL, Nextflow, Snakemake, WDL, others | self-hosted, engines in Docker; no built-in HPC | yes (WES) | run state | no (cancel only) | WES 1.1 with deviations, WRROC 0.5 | Apache-2.0 | [2026-10-26](../research/landscape-2026-10-26.md#sapporo) |
| Galaxy | Galaxy workflows | self-hosted or public servers; HPC job runners | yes | yes | "Pause for dataset review" step | WES routes (declares 1.0.0), TRS consumer, DRS, WRROC | MIT since 2026-02-25 | [2026-10-26](../research/landscape-2026-10-26.md#galaxy) |
| Arvados | CWL | self-hosted or cloud; Slurm, LSF | yes | yes | not found **[to be validated]** | — | AGPL-3.0 server, Apache-2.0 SDK | [2026-10-26](../research/landscape-2026-10-26.md#arvados) |
| Flyte 2 | Python; Nextflow through `flyteplugins-nextflow` and `nf-flyte` (since 2026-10) | Kubernetes; Slurm over SSH with a configured key; on a cluster the Nextflow work directory must be on an object store | yes | yes | yes (conditions and signals, typed value) | — | Apache-2.0 | [2026-10-26](../research/landscape-2026-10-26.md#flyte-2-and-nf-flyte) |
| Prefect 3 | Python | self-hosted or cloud; community Slurm worker | yes | yes | yes (pause or suspend, with typed input) | — | Apache-2.0 | [2026-10-26](../research/landscape-2026-10-26.md#prefect-3) |

For Snakemake, the panoptes and FlowO rows carry the corrections of 2026-10-26: monitoring tools exist, but there is no gate-and-steer tool for Snakemake. *(assumed — pending Thomas, inbox #27)*

Where Spectio differs: shared POSIX file systems, the user's own account, Snakemake as well as Nextflow, and item-level QC gates with evidence ([synthesis §1](../specs/synthesis.md#1-verdict)).
