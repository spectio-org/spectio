<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/logo_dark.svg">
    <img alt="Spectio" src="docs/assets/brand/logo_light.svg" width="320">
  </picture>
</p>

<p align="center">
  <b>Launch, monitor and relaunch your Nextflow and Snakemake runs, on your own cluster.</b><br>
  Open-source run manager for HPC and Kubernetes, part of the <a href="https://github.com/depictio/depictio">depictio</a> platform.
</p>

<p align="center">
  <img alt="Stage: design, first release 0.0.1 in preparation" src="https://img.shields.io/badge/stage-design%20%E2%86%92%200.0.1-8B5CF6">
  <img alt="Engines: Nextflow and Snakemake" src="https://img.shields.io/badge/engines-Nextflow%20%C2%B7%20Snakemake-5A4FCF">
  <img alt="Runs on SLURM and Kubernetes" src="https://img.shields.io/badge/runs%20on-SLURM%20%C2%B7%20Kubernetes-EC5F87">
</p>

## What Spectio is for

- **Launch.** Start a pipeline from the browser, the CLI or the API, on a laptop, a SLURM cluster or Kubernetes.
- **Monitor.** Follow every run live, stage by stage, from one place, including runs you started yourself in a terminal.
- **Relaunch.** Fix a parameter and resume from the engine's cache, without starting over.
- **Check, only where you want.** Optional quality gates between stages pause a run until a person, an AI agent or a robot decides how it continues.
- **Headless.** Everything the UI does goes through a documented API, for LIMS, portals and CI.

Spectio adds itself next to your setup rather than replacing it. On Nextflow it runs as one more plugin, `nf-spectio`, alongside the ones a pipeline already loads ([decision 0001](docs/decisions/0001-nextflow-through-nf-spectio.md)). On Snakemake it is one more logger added to the ones you already use ([architecture and packaging §2](docs/specs/architecture-plugins-and-packaging.md#2-plugin-kinds)).

## Where the project stands

Spectio is being designed in the open. The specifications, the UI design and the test pipelines are written first, and each step is reviewed before code is built on it. The first release, **0.0.1**, covers launch, monitor and relaunch from the browser on a SLURM cluster; its scope is in the [MVP page](docs/specs/mvp-0.0.1.md) and the [roadmap](docs/roadmap/index.md).

The package names are being reserved:

| Name | Where | What it will be |
|---|---|---|
| [`spectio`](https://pypi.org/project/spectio/) | PyPI | the CLI, the runner and, with `spectio[server]`, the server |
| `snakemake-logger-plugin-spectio` | PyPI | the Snakemake bridge |
| `nf-spectio` | Nextflow plugin registry | the Nextflow bridge |

The `0.0.0` releases only hold the names. Do not install them yet.

## Read more

| If you want… | Read |
|---|---|
| how a run goes, from launch to results | [Usage](docs/usage/index.md) |
| the big picture and the reasons behind it | [Synthesis](docs/specs/synthesis.md) |
| the screens | [UI spec](docs/specs/ui-spec.md), boards in [`design/ui-canvas/`](design/ui-canvas/) |
| the API and the data model | [API and data model](docs/specs/api-and-data-model.md) |
| plugins, packages and installs | [Architecture and packaging](docs/specs/architecture-plugins-and-packaging.md) |
| why a choice was made, and when | [Decision log](docs/decisions/log.md) |
| every page and who owns which topic | [Map](docs/map.md) |

## Repository

```
docs/      specs, decisions, research notes, reviews and progress pages (MkDocs site)
design/    UI boards, design tokens and brand
tests/     synthetic and real pipelines that every engine adapter will be tested against
tools/     dev tooling: docs gate, figures, media, board renderer, release
```

Build the documentation site locally:

```bash
uvx --with mkdocs-material mkdocs serve     # http://127.0.0.1:8000
```

Every pull request runs the docs gate (`python3 tools/docs/check.py`) and a strict site build. Much of the design work is done with Claude Code agents, under review; [`CLAUDE.md`](CLAUDE.md) holds their instructions.

## Licence

The released packages are MIT. The licence for the repository as a whole will be set before the first code release.
