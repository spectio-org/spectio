# MVP 0.0.1 — what the first version does

Status: draft v0.2 · 2026-10-27 · author: Thomas Weber (with Claude)
Companion docs:
- [`dev-environment-and-testing.md`](dev-environment-and-testing.md#15-what-ships-in-which-version) §15: the single owner of what each version contains. §15.1 holds the 0.0.1 cut and §15.3 how 0.0.1 runs on a cluster and stays safe without accounts. This page only maps the 0.0.1 cut to specs and boards; it adds no requirement.
- [Decision log, 2026-10-27, revised the same day](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link): why the cut is this one. It replaces the [first 0.0.1 cut](../decisions/log.md#2026-10-27-first-version-is-001-a-basic-local-mvp) where they differ.
- [`ui-spec.md`](ui-spec.md): the screens. Boards are in `design/ui-canvas/`; render one with `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180 /tmp/out.png`.

## 1. The frame

Thomas, 2026-10-27: the simplest version to start with, easy to share with users who test it, without the complexity of the full product.

- **One user per server, no sign-in, no accounts, no roles.** Each user runs `spectio serve` under their own Unix account on the cluster login node and opens it through an SSH tunnel with a one-time token link: [`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3 (access and security requirements); [`authentication-and-access.md`](authentication-and-access.md) §1 (`single` mode).
- **Runs go to SLURM.** The built-in runner submits each engine head with `sbatch`; the engine sends its tasks through its own SLURM executor; the plugins' events come back through the spool in the run directory: §15.3; [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1 (head job), §3.3 (CLI transport); [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.1 (spool).
- **One process on the login node**, with SQLite on node-local disk: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.1–§7.3.
- **Board:** Environments (the one SLURM environment of the login node). Not drawn yet: the token-link page and the "open this link" text printed by `spectio serve`.

The boards were drawn for the full product. They also show things 0.0.1 does not have: projects, who may decide, gates, review queues, several environments. Marking them is UX-227 (inbox #16, open).

## 2. Features and where they are specified

| Feature | Owning spec sections | Boards (`design/ui-canvas/`) |
|---|---|---|
| **Snakemake**, always through the Spectio logger plugin (`--logger spectio`), tasks through its SLURM executor | [`synthesis.md`](synthesis.md) §2, §2bis; [`ui-spec.md`](ui-spec.md) §5; [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1 (the Snakemake head in a SLURM job is **[to be validated]** in T3) | LaunchSnakemake |
| **Nextflow**, always through `nf-spectio`, tasks through its `slurm` executor | [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md); [`synthesis.md`](synthesis.md) §2bis; [`ui-spec.md`](ui-spec.md) §5 | Launch |
| **Launch a run from the UI**, its head submitted with `sbatch` | [`ui-spec.md`](ui-spec.md) §4.6 (launch form); [`api-and-data-model.md`](api-and-data-model.md) §5 (`POST /runs`, workflow schema); [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1 | Launch, LaunchSnakemake, LaunchReview |
| **Monitor it**: run state, number of jobs / tasks, stages as the engine reports them, and the head job's state | [`ui-spec.md`](ui-spec.md) §3.1, §3.2, §4.3, §4.4 (Summary, Tasks); [`api-and-data-model.md`](api-and-data-model.md) §5, §8; head job only: [`dev-environment-and-testing.md`](dev-environment-and-testing.md#151-capabilities-by-version) §15.1 (scheduler monitoring row) | RunsTable, RunsRows, RunDetail, Legend, RunFailed *(assumed — pending Thomas, inbox #40)*, RunScheduler (head job only), RunTasks and RunLogs (to be drawn; log sources: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.7) *(assumed — pending Thomas, inbox #40)* |
| **Relaunch**, including with changed parameters; every relaunch is a new child run *(assumed — pending Thomas, inbox #32)* | [`ui-spec.md`](ui-spec.md) §4.6 (relaunch dialog); [`api-and-data-model.md`](api-and-data-model.md) §5, §5.1 (`:relaunch` with parameter overrides); [`synthesis.md`](synthesis.md) §5ter | RelaunchDialog |
| **Parameter history**: which parameters each run used, what changed | [`ui-spec.md`](ui-spec.md) §4.4 (Parameters and Lineage tabs); [`api-and-data-model.md`](api-and-data-model.md) §5 (`/params`, `/lineage`), §7 (`run_inputs`) | RunDetail (parameters changed vs. the previous run, lineage), RunsCompare |

## 3. Deferred

Not in 0.0.1, version not set:
- QC checks and gates in every form, including live checks and the review queue (still the product direction, decision of 2026-10-26);
- Kubernetes, and a shared server with remote runners;
- users, sign-in, accounts and roles;
- full scheduler monitoring (task jobs, pending reasons, accounting, capacity);
- Postgres, Compose and Helm;
- the depictio hand-off;
- WES, MCP and embedded elements;
- runs started from a terminal (observed runs);
- LabID.

The full list, with owners, is in [`dev-environment-and-testing.md`](dev-environment-and-testing.md#15-what-ships-in-which-version) §15.

## 4. Cheap extras that keep the way open

Thomas, 2026-10-27: 0.0.1 stays small so that it can be checked by hand, and bugs, defects and visual problems are fixed from the start. One choice costs almost nothing now and avoids rework later. It is not a promise for 0.0.1.
- **The data model stays multi-user ready.** It keeps the existing rule "single-user first, multi-user ready" ([decision log](../decisions/log.md), 2026-10-25): every tenant row carries its `project_id`, and `spectio init` creates the one user, group and project. 0.0.1 builds no sign-in and no roles on top.
