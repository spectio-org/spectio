---
step: OPEN1
wave: W4
status: running
pr: null
review: approve
review_score: 11/14
review_ref: "doc-reviewer 2026-10-29, approve 11/14 on the working tree; required changes 1 to 3 applied, 4 answered under Figures and media"
---
# OPEN1 · The laptop command becomes `spectio open`

!!! info "Running 2026-10-29 · branch `autopilot/fold-open` · Thomas decided: one package, `spectio`, carries the laptop command; the separate package `spectio-open` and its PyPI name are dropped"

![0.0.1 on the cluster: the laptop opens an SSH tunnel to one login node with spectio open or an SSH config entry, then a one-time token link to spectio serve; the built-in runner starts each engine head in its own tmux session on that login node, where a person can attach; the head sends its tasks through the engine's own SLURM executor, and events come back through a spool file on the shared file system](../../assets/diagrams/mvp001_cluster_light.png#only-light)
![0.0.1 on the cluster: the laptop opens an SSH tunnel to one login node with spectio open or an SSH config entry, then a one-time token link to spectio serve; the built-in runner starts each engine head in its own tmux session on that login node, where a person can attach; the head sends its tasks through the engine's own SLURM executor, and events come back through a spool file on the shared file system](../../assets/diagrams/mvp001_cluster_dark.png#only-dark)

*Before: `autopilot/integration` at `83d639b`, where the laptop tool was the package `spectio-open`, standard library only, with its own PyPI name.*

## Why

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml). Thomas, 2026-10-29: "pourquoi ne pas garder un seul package avec conditionnel spectio et spectio[runner] ou spectio[full] plutot que spectio et spectio-open ?" (why not one package with extras rather than `spectio` and `spectio-open`?). The answer: the design already has one package with extras (`spectio`, `spectio[server]`); `spectio-open` stood apart only to stay free of dependencies. Folding it in was recommended, and Thomas answered "oui go pour ceci" ([decision log](../../decisions/log.md#2026-10-29-the-laptop-command-becomes-spectio-open-in-the-spectio-package)).

## What changed

Each item: before, then after, then where it now lives.

- **The command.** Before: `spectio-open <host> [--node <login node>]`, the console script of a separate package. After: `spectio open <host> [--node <login node>]`, a command of the base `spectio` package, installed on the laptop with `uv tool install spectio` or `pipx`, without extras. Its row is in the [command tree](../../specs/cli-and-shared-libraries.md#2-the-spectio-command-tree) (cli §2), next to `local open`, which opens a server on the same machine; behaviour and security stay in [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Access).
- **What it costs.** Before: a few kilobytes on the laptop. After: the base package's environment, under 80 MB; in exchange, one name, one package, one install guide. Dev-env §15.3 and the decision log.
- **The security requirements.** Unchanged: req. 8 (values from the cluster, ssh argv, link built on the laptop) now names `spectio open`; so do the state file and trust boundary paragraphs.
- **The code layout.** Before: a `packages/spectio-open/` row, "standard library only". After: no such row; `spectio open` is listed under `packages/spectio/`. [Architecture §6](../../specs/architecture-plugins-and-packaging.md#6-code-layout).
- **P1 Task 24.** Before: create `packages/spectio-open/`, a CI check that it imports only the standard library, and `~/.config/spectio-open/clusters.toml`. After: `packages/spectio/src/spectio/cli/open.py` and `open_remote.py`, tests in `packages/spectio/tests/test_open.py`, `~/.config/spectio/clusters.toml`; the standard-library test is gone. Goal, Global Constraints, M5 and Done when follow. [P1](../../plans/P1-walking-skeleton.md).
- **The names.** Before: four names to claim. After: three (`nf-spectio`, `spectio`, `snakemake-logger-plugin-spectio`). [Claim the package names](../../developer/claim-package-names.md) says to delete the `spectio-open` pending publisher and the `pypi-spectio-open` environment. Inbox #66.
- **The publish workflow.** Before: three choices. After: `spectio` and `snakemake-logger-plugin-spectio`; `tools/release/pypi-placeholders/spectio-open/` is removed. `.github/workflows/pypi-publish.yml`.
- **The board and figures.** `LiteStates` (link-expired state) shows `spectio open embl`; `mvp001_cluster`, `p1_skeleton` and `name-claim` are redrawn.

## Evidence

- `git grep -n spectio-open` on the branch leaves only: anchors to the 2026-10-28 log entry, dated notes saying what it was, and records of earlier steps (APPLY4, APPLY5, NAMES, UILITE, their reviews and figure `apply4_access`), which describe what was true then.
- `LiteStates` rendered with `tools/canvas/render.js` at 1440×1180 and looked at: the link-expired panel reads `spectio open embl`.
- The three figures re-rendered from their scripts; the changed labels looked at in the light PNGs and the `name-claim` heading in the dark one.
- `python3 tools/docs/check.py --base origin/autopilot/integration` and `uvx --with mkdocs-material mkdocs build --strict`: see the PR's Checks.

## Figures and media

- Sketch pair at the top: `mvp001_cluster` (`tools/diagrams/mvp001_cluster.py`), the 0.0.1 access path with `spectio open`. It shows the result, not a before/after: the change is a rename and a packaging move, and the before is one word in the same picture.
- Redrawn: `p1_skeleton` (P1 page) and `name-claim` (three names, claim guide).
- Board: `design/ui-canvas/LiteStates.dc.html`, link-expired state, rendered at 1440×1180.

## Findings and open questions

- Thomas: on pypi.org, delete the `spectio-open` pending publisher; on GitHub, delete the `pypi-spectio-open` environment. Then check the `snakemake-logger-plugin-spectio` pending publisher, whose run failed with `invalid-publisher`, and run the workflow again for it.
- `.github/` is code-owned, so the PR waits for Thomas's review.
