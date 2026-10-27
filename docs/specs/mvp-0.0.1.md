# MVP 0.0.1 — what the first version does

Status: draft v0.1 · 2026-10-27 · author: Thomas Weber (with Claude)
Companion docs:
- [`dev-environment-and-testing.md`](dev-environment-and-testing.md#15-what-ships-in-which-version) §15: the single owner of what each version contains. This page only maps the 0.0.1 cut to specs and boards; it adds no requirement.
- [Decision log, 2026-10-27](../decisions/log.md#2026-10-27-first-version-is-001-a-basic-local-mvp): why the cut is this small.
- [`ui-spec.md`](ui-spec.md): the screens. Boards are in `design/ui-canvas/`; render one with `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180 /tmp/out.png`.

## 1. The frame

- **One user, no sign-in, no roles.** `spectio serve` in personal mode, auth mode `single`, bound to 127.0.0.1: [`api-and-data-model.md`](api-and-data-model.md) §1, [`authentication-and-access.md`](authentication-and-access.md) §1. Shared login nodes are not covered (inbox #15, open).
- **Everything on one machine.** One process with the local runner (`spectio serve --with-runner`), SQLite, Python bundle: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.1–§7.3. The engines use their local executor.
- **Board:** EnvLocal (single machine).

The boards were drawn for the full product. They also show things 0.0.1 does not have: projects, who may decide, SLURM environments, review queues. Marking them is UX-227 (inbox #16, open).

## 2. Features and where they are specified

| Feature | Owning spec sections | Boards (`design/ui-canvas/`) |
|---|---|---|
| **Snakemake**, through the Spectio logger plugin (`--logger spectio`) | [`synthesis.md`](synthesis.md) §2, §2bis; [`ui-spec.md`](ui-spec.md) §5, §5.1 (how a gate stops Snakemake: `--until`) | LaunchSnakemake |
| **Nextflow**, through `nf-spectio` | [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md); [`synthesis.md`](synthesis.md) §2bis; [`ui-spec.md`](ui-spec.md) §5, §5.1 (how a gate stops Nextflow: `ext.when`) | Launch |
| **Launch a run from the UI** | [`ui-spec.md`](ui-spec.md) §4.6 (launch form); [`api-and-data-model.md`](api-and-data-model.md) §5 (`POST /runs`, workflow schema) | Launch, LaunchSnakemake |
| **Monitor it**: run state, number of jobs / tasks, stages | [`ui-spec.md`](ui-spec.md) §3.1, §3.2, §4.3, §4.4 (Summary, Stages & gates, Tasks); [`api-and-data-model.md`](api-and-data-model.md) §5, §8 | RunsTable, RunsRows, RunDetail, Legend |
| **Relaunch**, including with changed parameters | [`ui-spec.md`](ui-spec.md) §4.6 (relaunch dialog); [`api-and-data-model.md`](api-and-data-model.md) §5 (`:relaunch` with parameter overrides); [`synthesis.md`](synthesis.md) §5ter | RelaunchDialog |
| **Parameter history**: which parameters each run used, what changed | [`ui-spec.md`](ui-spec.md) §4.4 (Parameters and Lineage tabs); [`api-and-data-model.md`](api-and-data-model.md) §5 (`/params`, `/lineage`), §7 (`run_inputs`) | RunDetail (parameters changed vs. the previous run, lineage), RunsCompare |
| **A simple QC check and gate on one stage**, then resume or relaunch | [`checking-scenarios.md`](checking-scenarios.md) §4, §5, §7; [`ui-spec.md`](ui-spec.md) §5.1; [`synthesis.md`](synthesis.md) §5ter; [`api-and-data-model.md`](api-and-data-model.md) §5 (gates) | Manifest, RunDetail, ReviewReport |

For the gate, 0.0.1 keeps the simplest form: the checks of one stage, one gate, approve then continue, or relaunch with changed parameters. ReviewReport also draws item decisions and a report reader, which 0.0.1 does not need.

## 3. Deferred

Not in 0.0.1, version not set: runs started from a terminal, users and sign-in, SLURM and Kubernetes, scheduler monitoring, Postgres, Compose and Helm, the depictio hand-off, WES, MCP, embedded elements, LabID. The full list, with owners, is in [`dev-environment-and-testing.md`](dev-environment-and-testing.md#15-what-ships-in-which-version) §15.

## 4. Cheap extras that keep the way open

Thomas, 2026-10-27: 0.0.1 stays small so that it can be checked by hand, and bugs, defects and visual problems are fixed from the start. Two choices cost almost nothing now and avoid rework later. Neither one is a promise for 0.0.1.
- **The data model stays multi-user ready.** It keeps the existing rule "single-user first, multi-user ready" ([decision log](../decisions/log.md), 2026-10-25): every tenant row carries its `project_id`, and `spectio init` creates the one user, group and project. 0.0.1 builds no sign-in and no roles on top.
- **A run that the engine sends to a cluster is still monitored.** Spectio itself submits nothing to SLURM in 0.0.1. But when the engine uses its own executor (Snakemake `--executor slurm`, Nextflow `executor = 'slurm'`) from the same machine, its events still reach Spectio through the logger plugin or `nf-spectio`, because only the engine's main process talks to Spectio ([`synthesis.md`](synthesis.md) §10, risk 2). This is a bonus to try on a real cluster, not a tested feature **[to be validated]**.
