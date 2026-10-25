# Spectio

**Status: design phase, no code yet.** This repository holds the specifications, the decision log, the research behind them and the UI design sources. Code will follow in the same repository (see [`docs/specs/architecture-plugins-and-packaging.md`](docs/specs/architecture-plugins-and-packaging.md) §6 for the planned layout).

Spectio is an open-source tool for launching, monitoring and steering workflow runs. It works with Nextflow and Snakemake today, and with CWL and WDL later.
- **Checkpoints.** Gates pause a run at quality-control checkpoints, where a person, an AI agent or a robot decides how it continues.
- **Headless.** A complete API for LIMS such as LabID, portals and CI.
- **Shared platform.** Runs on a laptop, a lab server, Docker Compose or Kubernetes, and forms one platform with [depictio](https://github.com/depictio/depictio): same accounts, groups, branding, and results that become dashboards.

## Where to start

| If you want… | Read |
|---|---|
| the big picture and the reasons | [`docs/specs/synthesis.md`](docs/specs/synthesis.md) |
| what the screens look like and do | [`docs/specs/ui-spec.md`](docs/specs/ui-spec.md) and the UI canvas (below) |
| the API, identity, tenancy and database | [`docs/specs/api-and-data-model.md`](docs/specs/api-and-data-model.md) |
| plugins and how Spectio is installed | [`docs/specs/architecture-plugins-and-packaging.md`](docs/specs/architecture-plugins-and-packaging.md) |
| quality-control gates across nf-core | [`docs/specs/checking-scenarios.md`](docs/specs/checking-scenarios.md) |
| SLURM, other schedulers, Kubernetes and monitoring | [`docs/specs/schedulers-and-monitoring.md`](docs/specs/schedulers-and-monitoring.md) |
| administration, backups and migrations | [`docs/specs/admin-and-operations.md`](docs/specs/admin-and-operations.md) |
| the CLI and the libraries shared with depictio and LabID | [`docs/specs/cli-and-shared-libraries.md`](docs/specs/cli-and-shared-libraries.md) |
| what is reused from depictio | [`docs/specs/depictio-ecosystem-reuse.md`](docs/specs/depictio-ecosystem-reuse.md) |
| how agents check their work: toolchain, local SLURM and Kubernetes, tests, staging | [`docs/specs/dev-environment-and-testing.md`](docs/specs/dev-environment-and-testing.md) |
| what to do next, with ready-to-paste Claude Code prompts | [`docs/playbooks/next-phase.md`](docs/playbooks/next-phase.md) |
| why a choice was made, and when | [`docs/decisions/log.md`](docs/decisions/log.md) |

Full map: [`docs/README.md`](docs/README.md).

## Repository layout

```
docs/
  specs/        living specifications (English), one topic per file
  playbooks/    step-by-step prompts for the next phases
  reviews/      review round results (findings, triage)
  decisions/    decision log (append-only) and new decision records
  research/     dated working notes and data the specs cite (code audits, nf-core survey)
design/
  tokens/       design tokens (CSS custom properties)
  ui-canvas/    source of the UI canvas: one .dc.html per board + canvas.json
  brand-canvas/ logo and colour explorations
tools/canvas/   local renderer for the canvas boards (Playwright) and board generators
mkdocs.yml      documentation site
CLAUDE.md       instructions for Claude Code
.claude/        project agents, skills (incl. vendored superpowers and Karpathy guidelines), settings
```

## Viewing the design

- **The live canvas.** It is a private claude.ai artifact owned by the author. Ask for access.
- **Rendering boards locally.** `design/ui-canvas/` is a snapshot of that canvas, taken at each milestone. To render a board:

  ```bash
  npm install playwright        # Chromium included
  node tools/canvas/render.js design/ui-canvas/RunDetail.dc.html 1440 1180 out.png
  ```

## Building the documentation site

```bash
uv tool install mkdocs --with mkdocs-material
mkdocs serve      # http://127.0.0.1:8000
```

The site builds in CI on every pull request (`mkdocs build --strict`, which also fails on broken internal links).

## Licence

To be decided before the first code release. depictio is MIT.
