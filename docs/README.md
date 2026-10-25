# Spectio documentation

## Reading order

1. [Synthesis](specs/synthesis.md): feasibility, engines, existing tools, the recommended stack, risks and phasing.
2. [UI spec](specs/ui-spec.md): navigation, status system, every screen, phone and tablet.
3. [Checking scenarios](specs/checking-scenarios.md): the review model (items × checks × evidence × decisions) across the nf-core pipelines, and the five review views.
4. [API and data model](specs/api-and-data-model.md): headless use, endpoints, identity and tenancy, database schema, events, RO-Crate, depictio compatibility (§13).
5. [Plugin architecture and packaging](specs/architecture-plugins-and-packaging.md): plugin kinds and contract; Python bundle, Docker Compose and Kubernetes; tasks and message brokers (§7.6).
6. [Schedulers and monitoring](specs/schedulers-and-monitoring.md): SLURM and other HPC schedulers, Kubernetes, pending reasons, accounting, capacity and pre-flight checks.
7. [Administration and operations](specs/admin-and-operations.md): users and groups, branding, tasks, logs, health, backups, restore, migrations, maintenance.
8. [CLI and shared libraries](specs/cli-and-shared-libraries.md): the `spectio` command tree, server profiles, and the libraries shared with depictio and LabID.
9. [depictio ecosystem reuse](specs/depictio-ecosystem-reuse.md): what Spectio depends on, shares, copies, calls or leaves.
10. [Dev environment and testing](specs/dev-environment-and-testing.md): toolchain, local SLURM (sind) and Kubernetes (kind with Kueue), isolated scenarios, test tiers, staging behind Tailscale Funnel, Claude in the development loop.

## Playbooks and reviews

- [Next phase](playbooks/next-phase.md): ready-to-paste Claude Code prompts for review rounds, the development layer, the test infrastructure and planning.
- [Reviews](reviews/README.md): one file per review round, and the finding format.

## Decisions

The [decision log](decisions/log.md) is append-only and dated: what was decided, why, and where it is specified. New decisions use the [decision record template](decisions/README.md).

## Research

Working notes are dated and kept as written. Specs cite them. When something changes, a new note is added; old notes are not rewritten.
- [depictio harmonisation](research/depictio-harmonization.md): identity, tenancy and hand-off.
- [depictio administration and operations](research/depictio-admin-ops.md).
- [depictio CLI, models and packaging; LabID CLI](research/depictio-cli-packaging.md).
- [depictio frontend, branding, users and groups](research/depictio-frontend-admin.md).
- `research/data/`: the nf-core survey behind the checking scenarios (`analysis.json`, `classes.json`, `nfcore_released.tsv`, `nfcore_repos.tsv`, and `fetch.sh`, which recreates the sparse clones).
- `research/depictio-shots/`: depictio screenshots used for comparison.

## Conventions

- **Language.** English for everything in this repository.
- **Spec header.** Every spec starts with a status line (`draft vX.Y · date · author`) and its companion docs.
- **Stable sections.** Section numbers are kept stable so other docs can cite `file.md §n`. A new section gets the next number; it does not renumber old ones.
- **Facts carry their source.** A fact about another tool (Nextflow, Snakemake, SLURM, depictio…) gives its source: a link, or a file and line in a dated audit. Anything not verified is marked **[to be validated]** or *inferred*.
- **Diagrams.** Mermaid, in fenced `mermaid` blocks. They render on GitHub and in the docs site.
