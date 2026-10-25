# Spectio — instructions for Claude Code

## What this repository is

- **Status.** Spectio is in its **design phase**. The repository holds specifications, a decision log, research notes and UI design sources. There is no product code yet. The planned code layout is in `docs/specs/architecture-plugins-and-packaging.md` §6.
- **The product.** Spectio launches, monitors and steers Nextflow and Snakemake runs, later CWL and WDL. It has QC gates, a headless API, runners on HPC and Kubernetes, and integrates with depictio.
- **Where to look.** `docs/README.md` maps every spec and says which one owns which topic.

## Current phase: review before implementation

Do not start writing product code unless the task explicitly says so. The current work is review rounds, spikes and planning, driven by `docs/playbooks/next-phase.md`.
- **Review findings** go to `docs/reviews/<round>.md`, in the format of `docs/reviews/README.md`. Specs are not edited during a review round.
- **Accepted findings** are applied in a separate step (`/apply-findings`): spec changes, plus a dated entry in `docs/decisions/log.md`.
- **Spikes** (throwaway experiments) run in a git worktree under `spikes/<name>/`. Each one ends with a dated note in `docs/research/`.

## Rules

- **Language.** English for every file in the repository. Replies to Thomas may be in French.
- **External facts.** Every fact about another tool (Nextflow, Snakemake, SLURM, Kubernetes, depictio, LabID…) needs a source: a link, or file:line in a dated audit. Mark anything unverified **[to be validated]**. Never present memory as verified.
- **One owner per topic.** Change the spec that owns a topic and link to it from elsewhere. Do not duplicate content.
- **Stable sections.** Keep section numbers stable. Add a new number rather than renumbering.
- **Diagrams.** Mermaid diagrams must render: check them with `npx -y @mermaid-js/mermaid-cli@11 -i file.mmd -o out.svg`.
- **Docs build.** It must pass: `uvx --with mkdocs-material mkdocs build --strict`.
- **UI boards.** Render them with `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180 /tmp/out.png`, then look at the PNG before claiming a UI change works. Board conventions: `main > *{flex-shrink:0}`, no `sc-for` inside `<svg>` (draw charts in HTML), shared components through `dc-import` (`AppSidebar`, `AppTopbar`, `AdminNav`, `MobileTopbar`, `MobileTabbar`).
- **Coding behaviour.** Follow the `karpathy-guidelines` skill: think before coding, simplicity first, surgical changes, goal-driven execution with explicit verification.
- **Engineering workflow.** Use the vendored superpowers skills: `brainstorming`, `writing-plans`, `subagent-driven-development`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `using-git-worktrees`.

## Agents in `.claude/agents/`

| Agent | Use it for |
|---|---|
| `spec-reviewer` | contradictions, gaps and unclear contracts across specs |
| `fact-checker` | verifying external claims against primary sources |
| `constraints-hunter` | implementation risks, scale limits, operational constraints, things that will break |
| `security-reviewer` | threat model, authz, secrets, multi-tenancy, supply chain |
| `ux-reviewer` | UI boards against the UI spec: states, accessibility, consistency, phone |
| `depictio-liaison` | compatibility claims against the real depictio and LabID code |
| `test-architect` | test strategy, fixtures, scenario matrix, local SLURM and Kubernetes clusters |
| `infra-engineer` | dev environments, CI, staging, containers, sind / kind, Tailscale |

Reviewers are read-only and report findings. They never edit specs.

## Useful commands

```bash
uvx --with mkdocs-material mkdocs serve              # docs site
node tools/canvas/render.js design/ui-canvas/RunDetail.dc.html 1440 1180 /tmp/run.png
grep -rn "to be validated" docs/specs                # open verification items
```
