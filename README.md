# Spectio

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/weber8thomas/spectio?quickstart=1)

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
| how agents check their work: toolchain, local SLURM and Kubernetes, tests, dev previews | [`docs/specs/dev-environment-and-testing.md`](docs/specs/dev-environment-and-testing.md) |
| sign-in, magic links, share links, provisioning | [`docs/specs/authentication-and-access.md`](docs/specs/authentication-and-access.md) |
| telemetry, install tracking, external analytics | [`docs/specs/telemetry-and-analytics.md`](docs/specs/telemetry-and-analytics.md) |
| how docs are written, drawn, captured and reviewed at every step | [`docs/specs/documentation-system.md`](docs/specs/documentation-system.md) |
| what each step has done so far | [`docs/progress/`](docs/progress/index.md) |
| run the next phase unattended | [`docs/playbooks/autopilot.md`](docs/playbooks/autopilot.md) (`/autopilot`, driven by `/goal`) |
| what is waiting on you | [`docs/reviews/inbox.md`](docs/reviews/inbox.md) |
| why a choice was made, and when | [`docs/decisions/log.md`](docs/decisions/log.md) |

Full map: [`docs/map.md`](docs/map.md).

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
  progress/     one page per pipeline step, written while it runs
  assets/       generated figures, casts, screenshots and videos (media.yaml lists their generators)
tests/pipelines/ synthetic scenario pipelines (both engines) and the real nf-core / Snakemake corpus
tools/canvas/   local renderer for the canvas boards (Playwright) and board generators
tools/diagrams/ hand-drawn figure toolkit (sketch.py) and one script per figure
tools/media/    cast generator, screenshot registry, combined terminal + browser captures
tools/docs/     the docs gate (check.py)
mkdocs.yml      documentation site
CLAUDE.md       instructions for Claude Code
.claude/        project agents, skills (incl. vendored superpowers and Karpathy guidelines), settings
.autopilot/     pipeline state and journal (committed, so any session can resume)
tools/autopilot/ batch picker, budget governor, status-line tap and headless runner
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

Every pull request runs the docs gate, `python3 tools/docs/check.py`: strict build, Mermaid, diagram freshness, media manifest, Progress pages, and PR body.

## Licence

To be decided before the first code release. depictio is MIT.
