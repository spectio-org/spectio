# Documentation map

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
11. [Authentication and access](specs/authentication-and-access.md): instance modes, sign-in methods (password, magic links, share links, OIDC, SAML, depictio trust), sessions and tokens, pipeline provisioning, the auth test matrix.
12. [Telemetry and analytics](specs/telemetry-and-analytics.md): anonymous install telemetry, local activity analytics, and the web-analytics plugin kind (GA4, Umami, Plausible, Matomo, PostHog).
13. [Documentation system](specs/documentation-system.md): the docs site and landing page, docs written and reviewed at every step, sketch diagrams, screenshots, casts and combined captures, changelog, PR bodies, auto-merge.

## Playbooks and reviews

- [Progress](progress/index.md): one page per pipeline step, written while the step runs.
- [Autopilot](playbooks/autopilot.md): runs the whole pipeline ([`pipeline.yaml`](playbooks/pipeline.yaml)) unattended in five waves, with the [triage policy](playbooks/triage-policy.md) deciding what needs Thomas.
- [Next phase](playbooks/next-phase.md): the prompt behind each pipeline step (review rounds, development layer, test infrastructure, planning).
- [Inbox](reviews/inbox.md): the only place Thomas needs to look between runs.
- [Reviews](reviews/README.md): one file per review round, and the finding format.

## Decisions

The [decision log](decisions/log.md) is append-only and dated: what was decided, why, and where it is specified. New decisions use the [decision record template](decisions/README.md).

## Research

Working notes are dated and kept as written. Specs cite them. When something changes, a new note is added; old notes are not rewritten.
- [depictio harmonisation](research/depictio-harmonization.md): identity, tenancy and hand-off.
- [depictio administration and operations](research/depictio-admin-ops.md).
- [depictio CLI, models and packaging; LabID CLI](research/depictio-cli-packaging.md).
- [depictio frontend, branding, users and groups](research/depictio-frontend-admin.md).
- [depictio authentication](research/depictio-auth-2026-10-26.md), [depictio docs system](research/depictio-docs-system-2026-10-26.md), [test corpus and CI](research/corpus-and-ci-2026-10-26.md), [budget governor and telemetry](research/budget-and-telemetry-2026-10-26.md).
- Spikes: [synthetic pipelines](research/spike-synthetic-pipelines-2026-10-26.md), [docs media tooling](research/spike-docs-media-tooling-2026-10-26.md).
- `research/data/`: the nf-core survey behind the checking scenarios (`analysis.json`, `classes.json`, `nfcore_released.tsv`, `nfcore_repos.tsv`, and `fetch.sh`, which recreates the sparse clones).
- `research/depictio-shots/`: depictio screenshots used for comparison.

## Conventions

- **Language.** English for everything in this repository.
- **Spec header.** Every spec starts with a status line (`draft vX.Y · date · author`) and its companion docs.
- **Stable sections.** Section numbers are kept stable so other docs can cite `file.md §n`. A new section gets the next number; it does not renumber old ones.
- **Facts carry their source.** A fact about another tool (Nextflow, Snakemake, SLURM, depictio…) gives its source: a link, or a file and line in a dated audit. Anything not verified is marked **[to be validated]** or *inferred*.
- **Diagrams.** Explanatory figures are hand-drawn sketches from `tools/diagrams/` (light/dark PNG pairs, SVG committed). Small structural diagrams inside specs stay in Mermaid fenced blocks. See [documentation system §0](specs/documentation-system.md#0-decisions-in-brief).
