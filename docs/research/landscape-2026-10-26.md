# Landscape of workflow monitoring, launch and steering tools (2026-10-26)

**Question** (playbook round R9, [`next-phase.md`](../playbooks/next-phase.md)). What has changed since [`synthesis.md`](../specs/synthesis.md) was written (23–25/10/2026) among the tools next to Spectio? For each tool: licence, activity, overlap with Spectio, and anything worth reusing or integrating.

**Short answer.**
- Steering is still unclaimed **for Snakemake and for shared-file-system HPC**: no Snakemake tool read here launches, stops at a stage, gates or relaunches a run.
- Two things moved this month, and the positioning has to say exactly where Spectio differs:
  - **Flyte 2** now runs Nextflow pipelines (`flyteplugins-nextflow` + `nf-flyte`, first released 2026-10-16 and 2026-10-23) and pauses runs until a signal (`flyte.new_condition`). Its Nextflow path needs an object-store work directory and reaches Slurm over SSH with a shared key.
  - **FlowO** (MIT, Snakemake) has a versioned workflow catalogue, SSE monitoring, users and an MCP endpoint. It has no launch or steering in the sources read.
- Monitoring for Snakemake is no longer "panoptes only". Snakemake's current docs point to logger plugins, and the plugin catalogue lists 12 of them.
- Snakemake now has an RO-Crate exporter maintained in the `snakemake` organisation (unreleased, 0.1.0). Engine exporters emit WRROC 0.1 or 0.5 on RO-Crate 1.1, while the current WRROC 0.6 needs RO-Crate 1.3 and is not backward compatible.
- GA4GH: the edges agreed on 2026-10-26 ([decision log](../decisions/log.md), "GA4GH: no change") still hold. This note refines them: WES as a strict 1.1 facade, TRS as a client first, DRS through the engine where it can, TES never exposed by Spectio.

The spec changes these facts imply are findings FC-038 to FC-054 in [`R9-landscape.md`](../reviews/R9-landscape.md). This note is the source of truth for the "Spectio and other tools" comparison (§10).

**This note supersedes** row 5 of §1 in [`adoption-and-positioning-2026-10-26.md`](adoption-and-positioning-2026-10-26.md) (the Snakemake monitoring fact, see §3 and §12). Research notes are not rewritten, so that note stays as it is.

## 1. Method and sources

- **Reviewers:** fact-checker (Seqera and nf-tower, nf-shard, Sapporo and other WES servers, GA4GH WES/TES/TRS/DRS, WRROC, nf-prov) and constraints-hunter (panoptes, snkmt, FlowO, Galaxy, Arvados, Flyte, Prefect, Dagster), in parallel, on 2026-10-26. Both returned output.
- **Spectio repository:** `autopilot/integration` at `3b209d3`.
- **Code:** read from shallow clones under `/tmp/w1-scratch/repos/` and `/tmp/w1-scratch/fc2/` (scratch, not kept). Where docs and code disagree, the code is cited.
- **Release dates:** PyPI JSON API where a package exists (re-read for the merge on 2026-10-26), otherwise the last tag or commit.
- **Limits:** the GitHub REST API was blocked, so archive flags and star counts could not be read. The FlowO repository (`zhanghaomiao/flowo`) did not answer anonymously, so FlowO was read from its PyPI sdist and its docs site.

| Repository | Commit (date) | Used for |
|---|---|---|
| `seqeralabs/nf-tower` | `e2eb7d7` (2025-01-30) | archive notice, licence |
| `seqeralabs/tower-cli`, `seqeralabs/seqera-kit` | v0.42.0 (2026-10-08); last commit 2026-05-28 | Seqera clients |
| `AugustDev/nf-shard` | `f40ce84` (2024-09-19), tag 0.1.23 (2024-07-14) | activity |
| `snakemake/snakemake` | `1c67a66` (2026-10-19), stable 9.27.1 | `--logger`, monitoring docs |
| `panoptes-organization/panoptes`, `…/snakemake-logger-plugin-panoptes` | `cd40b8b`; `2062666` | panoptes server and plugin |
| `cademirch/snkmt`, `cademirch/snakemake-logger-plugin-snkmt` | `aa6ed1d`; `5b94373` | snkmt |
| `snakemake-logger-plugin-flowo` sdist | 2.2.0 (PyPI, 2026-07-27) | FlowO |
| `ga4gh/workflow-execution-service-schemas` | `c3fb9fb` (1.1.0) | WES |
| `ga4gh/task-execution-schemas` | `8c57e04` (2026-09-24) | TES |
| `ga4gh/tool-registry-service-schemas` | `d40e63b` | TRS |
| `ga4gh/data-repository-service-schemas` | `fe25c39` | DRS |
| `sapporo-wes/sapporo-service` | `14e6b5c` (2026-10-14), v2.4.0 | Sapporo |
| `galaxyproject/galaxy` | `fd43a3c` (`dev`, 2026-10-26); `release_26.1` at `5a58507` | Galaxy WES, pause step, licence |
| `arvados/arvados` | `78a35c3` (GitHub mirror, 2026-10-02) | Arvados |
| `flyteorg/flyte`, `flyteorg/flyte-sdk`, `flyteorg/flytekit`, `unionai/nf-flyte` | `ed74e57`; `0aabafa` (2026-10-26); `d0c64d5`; 0.2.1 | Flyte |
| `PrefectHQ/prefect` | `21a1f02` | Prefect |
| `dagster-io/dagster` | `c94186b` | Dagster |
| `nextflow-io/nf-prov` | `8aa8280` (2026-10-12) | nf-prov |
| `nextflow-io/nextflow` | `193a4c2` (26.10.3) | data lineage |
| `nextflow-io/nf-ga4gh` | 1.5.0 (2026-07-02) | TES executor, `drs://` |
| `snakemake/snakemake-report-plugin-rocrate` | `1989c5b` (2026-10-23) | Snakemake run crate |
| `ResearchObject/workflow-run-crate` | `31518a5` (2026-10-16) | WRROC profiles, implementations list |

## 2. Nextflow: monitoring and launch

### Seqera Platform (Cloud, Enterprise)
- **Licence:** proprietary. **Activity:** Enterprise v26.1, released 2026-05-22 ([changelog](https://docs.seqera.io/changelog/seqera-enterprise/v26.1)).
- **How it reaches a cluster:** "Seqera requires SSH access to your HPC cluster to run pipelines"; Tower Agent is used for clusters without direct SSH access. Schedulers: PBS Pro, Grid Engine, LSF, Moab and Slurm ([HPC docs](https://docs.seqera.io/platform-cloud/compute-envs/hpc)). That Tower Agent uses an outgoing WebSocket is **[to be validated]**.
- **Steering:** Resume and Relaunch, only for runs launched from the Platform; no pause and no approval step ([cache and resume docs](https://docs.seqera.io/platform-cloud/launch/cache-resume)).
- "There is no free self-hosted edition" is **[to be validated]**: no Seqera page saying so was read.
- **For Spectio:** coexist ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)).

### `tw` (tower-cli) and seqerakit
- Apache-2.0. tower-cli v0.42.0 (2026-10-08); seqera-kit last commit 2026-05-28.
- Clients of the Seqera API only. Emulating that API so these clients drive Spectio would be the "replacement" positioning that decision 0001 rejects (finding FC-051).

### nf-tower Community Edition
- MPL-2.0 (`LICENSE.txt`). Archived: the README at `e2eb7d7` (2025-01-30, "Update readme with deprecation") says "This project has been archived and it's not maintained anymore". The GitHub archive flag could not be read.
- **For Spectio:** none.

### nf-shard
- MIT. Last tag 0.1.23 (2024-07-14); last commit `f40ce84` (2024-09-19). Star count not checked (API blocked).
- Speaks the Tower protocol; monitoring only, no steering. Unmaintained for two years.
- **For Spectio:** none beyond the design notes already in synthesis §2bis.

## 3. Snakemake: monitoring

**The docs.** The page `snakemake.readthedocs.io/en/master/executing/monitoring.html` is a frozen Snakemake 6.1.0 build (`build_date` 2021-04-07). It still says Snakemake talks to panoptes through `--wms-monitor`. The current docs (`docs/executing/monitoring.rst:7-26` at `1c67a66`) say: "Since Snakemake 9.0, Snakemake supports monitoring workflow execution through logger plugins", point to the plugin catalogue, and say several loggers can be used at once.

**The CLI.** `--logger` takes `nargs="+"` ("Specify one or more custom loggers", `src/snakemake/cli.py:1623-1628`). `--wms-monitor` and `--log-handler-script` are gone from `cli.py`. The docs speak of "specifying the `--logger` option multiple times", but with `nargs="+"` and the default `store` action, a repeated `--logger` may keep only the last value **[to be validated]** (spike 1 in R9).

**The catalogue** ([Snakemake plugin catalog](https://snakemake.github.io/snakemake-plugin-catalog/), 2026-10-26) lists 12 logger plugins: dart, flowo, github-status, panoptes, prometheus, pypsa, rich, rich-loguru, snakesee, snkmt, stomp, sumerrs. It also lists 28 executor plugins.

### panoptes
- MIT. Server `panoptes-ui` 1.6.2 (PyPI, 2026-10-24); logger plugin `snakemake-logger-plugin-panoptes` 0.3.0 (2026-07-02). About 35 commits between May and October 2026: active again.
- HTTP server, dashboard and REST. The plugin README says it replaces "the legacy `--wms-monitor` integration that was removed in Snakemake 9" (`2062666`).
- **Steering:** none. `POST /api/workflow/<id>/cancel` only marks the database row "Cancelled" (`panoptes/routes/api.py:119-127`, `server_utilities/db_queries.py:220-230`, `cd40b8b`).
- **Transport:** one synchronous `session.post(..., timeout=10.0)` per event, a warning on failure, no retry and no spool (`log_handler.py:115-130`, `2062666`).

### snkmt
- MIT. `snkmt` 0.4.0 (2026-03-13); plugin 0.1.9 (2026-10-12).
- Local SQLite and a Textual TUI. Built for network file systems: WAL is disabled because "the database may live on a network filesystem (NFS/Lustre/GPFS)", and `busy_timeout` is 30 s after concurrent instances failed with "database is locked" (`log_handler.py:45,83-103`, `5b94373`).
- Pins `snakemake-interface-logger-plugins<3,>=1.2.0` (PyPI `requires_dist`).
- **Steering:** none.

### FlowO
- MIT (sdist `LICENSE`, © 2024-2026 H. Zhang, J. Zhang). `snakemake-logger-plugin-flowo` 2.2.0 (PyPI, 2026-07-27). Repository not anonymously reachable **[to be validated: private or moved]**.
- FastAPI, Postgres, SSE monitoring, per-run DAG, jobs, timeline and code views, a "Catalog [that] stores Snakemake templates… with versioning", users (`fastapi-users`) and an MCP endpoint (`fastapi-mcp` in the server extra) (PyPI description; [FlowO docs](https://flowo-docs.pages.dev/)). Server extra needs Snakemake ≥ 9.23. The server reads outputs through a shared `FLOWO_WORKING_PATH` mount.
- **Version churn it has to absorb:** it probes `DefaultFilter.__init__` because its signature changed three times within Snakemake 9.x ("<=9.2.x … >=9.10.0 … >=9.23", `plugin/client/log_handler.py:156-176`).
- **Transport:** `self._client.post(url, json=payload)`, `timeout=10.0`, no retry and no spool, plus a heartbeat thread (`log_handler.py:218-251`).
- **Steering:** none found in the sdist or the docs **[to be validated]** (a 30-minute install would confirm it).
- **For Spectio:** the closest Snakemake neighbour. A possible collaborator on logger-event conventions.

### snakesee and the other loggers
- snakesee: MIT, 0.9.0 (2026-07-19), a TUI monitor. Not read in detail.
- The other loggers (dart, github-status, prometheus, pypsa, rich, rich-loguru, stomp, sumerrs) were not read.

**For Spectio.** Monitoring, a workflow catalogue and MCP access for Snakemake already exist in MIT tools. Launching, gates and steering do not. Users may already run one of these loggers, so Spectio has to add its logger to theirs, not replace them (FC-039).

## 4. WES servers and multi-engine platforms

### Sapporo
- Apache-2.0. `sapporo-service` v2.4.0 (`14e6b5c`, 2026-10-14), active.
- Engines: cwltool, Nextflow 26.10.0, Toil, Cromwell, Snakemake 9.27.0, ep3 and StreamFlow (README).
- **Not strictly WES 1.1** (`docs/wes-compatibility.md`):
  - row 1-1: `ServiceInfo.default_workflow_engine_parameters` becomes a dict keyed by engine (breaking);
  - row 1-2: `RunLog.outputs` becomes a list of `FileObject` (breaking);
  - row 2-2: `workflow_engine` is required on `POST /runs`;
  - row 4-1: `GET /runs/{run_id}/tasks` returns 400.
- **HPC:** none built in. Engines run in Docker through the host socket (`docs/architecture.md:73,100`); Slurm appears only as something a custom `cancel_<engine>()` hook must handle. A site would write its own `run.sh`.
- **Provenance:** writes RO-Crate 1.1 + WRROC 0.5 (`sapporo/ro_crate.py:47-50`); `docs/ro-crate.md` explains why it does not claim the Provenance profile.
- **Steering:** cancel and delete.
- **For Spectio:** reuse its WES compatibility matrix and `ro_crate.py` as references.

### sapporo-web
- Apache-2.0. Last commit 2022-09-13. A stale WES client: not a target for Spectio's facade.

### Galaxy
- **Licence:** "Galaxy is provided from 2026-02-25 onwards entirely under the MIT License" (`LICENSE.txt`, `fd43a3c`). Copies from before that date carry the previous licence, AFL-3.0 **[to be validated]**.
- **Activity:** `galaxy-app` 26.1.2 (PyPI, 2026-10-26); a `release_26.2` branch exists.
- **WES:** `lib/galaxy/webapps/galaxy/api/wes.py:64-151` serves every WES 1.1 route, including `/tasks` and `/tasks/{task_id}`, and ships in `release_26.1` (`5a58507`) next to `drs.py` and `trs_consumer.py`. But:
  - service-info declares `supported_wes_versions=["1.0.0"]` (`services/wes.py:412`);
  - `workflow_type` is a Galaxy format (`gx_workflow_ga`, `gx_workflow_format2`), "not CWL/Nextflow/WDL";
  - auth is "`x-api-key` (the WES spec's bearer-token scheme is not used)" (`doc/source/dev/ga4gh_wes.md:12,57,77`).
  - The WES pydantic models are generated (`lib/galaxy/schema/wes/gen.sh`): with the MIT licence they are a usable reference.
- **HPC:** job runners `slurm`, `drmaa`, `pbs`, `condor`/`htcondor`, `kubernetes`, `pulsar` and others (`lib/galaxy/jobs/runners/`).
- **Steering:** a "Pause for dataset review" workflow step (`PauseModule`, `lib/galaxy/workflow/modules.py:2041-2110`) that records approve or cancel per invocation step. It is the bioinformatics precedent for a review gate.
- **For Spectio:** WES reference implementation; prior art for gates; a possible later engine adapter (idea only, not in the MVP).

### Arvados
- AGPL-3.0 for servers, Apache-2.0 for `sdk/`, CC-BY-SA-3.0 for docs (`COPYING`, `78a35c3`). 3.2.1 (PyPI `arvados-cwl-runner`, 2026-03-02); mirror commit 2026-10-02.
- CWL through `arvados-cwl-runner`; Slurm and LSF dispatchers (`services/crunch-dispatch-slurm`, `lib/lsf`); needs Keep storage and its own API server. No WES in the tree.
- **Steering:** none found **[to be validated]**.
- **For Spectio:** provenance and content-addressed data ideas. Call only the Apache-2.0 SDK; never copy server code (AGPL).

### Toil and Cromwell
- Toil: Apache-2.0, `releases/9.6.0`; CWL and WDL; `toil server` exposes WES (its swagger says `version: 1.0.0`). HPC batch systems not re-read.
- Cromwell: BSD-3 per README, release 92 (2026-01-30); WDL. A future WDL target.

### proWES and cwl-WES
- Apache-2.0 (ELIXIR Cloud). Last commits 2026-01-09 and 2026-01-19. WES gateway and federation; no direct overlap.

## 5. General orchestrators with human-in-the-loop

### Flyte 2 and nf-flyte
- Apache-2.0 (flyte, flyte-sdk, nf-flyte `COPYING`). PyPI `flyte` 2.12.1 (2026-10-21); flyte-sdk last commit `0aabafa` (2026-10-26); "Flyte 2 GA" in the README (`ed74e57`).
- **Nextflow:** `flyteplugins-nextflow` (first PyPI release 2026-10-16) runs the Nextflow head inside a Flyte task, and `nf-flyte` 0.2.1 (2026-10-23, first commit 2026-09-25) runs every Nextflow task as a child action. "Aborting the Flyte run aborts the pipeline and its running tasks"; `-resume` needs a fixed `work_dir`; "On a cluster, the work directory must be on an object store Flyte can read (S3, GCS or Azure)" (`plugins/nextflow/README.md:1-12,44-66,90`).
- **Slurm:** `flyteplugins-slurm` (first PyPI release 2026-10-03) submits "over SSH" with a configured key and needs Pyxis/Enroot or Apptainer on the nodes (`plugins/slurm/README.md:3,22-31`).
- **Steering:** `flyte.new_condition(name, prompt, data_type)` pauses a run until it is signalled from the UI, the CLI (`flyte signal condition …`) or the API, with a timeout and a webhook that POSTs a `{callback_uri}` (`src/flyte/_condition.py:15-69`; `plugins/hitl/README.md:4-12`). An MCP tool lists "the points where it is paused for external input" (`src/flyte/ai/mcp/_tools.py:1133`). Flyte 1 had `approve`, `wait_for_input` and `sleep` (`flytekit/core/gate.py:136-166`, `d0c64d5`).
- **For Spectio:** the closest design to Spectio's `Intervention` + webhook + MCP, and since this month a direct overlap on "stop, decide, resume" around Nextflow runs. Differences that still hold: object store vs shared POSIX file systems; a shared SSH key vs the user's own account; no Snakemake; a typed value vs item-level QC review (FC-043).

### Prefect 3
- Apache-2.0. 3.9.0 (PyPI, 2026-10-21).
- **Two mechanisms** (`src/prefect/flow_runs.py`, `21a1f02`):
  - `pause_flow_run` blocks the process until resumed, `timeout: int = 3600`, after which the flow fails (l.166-200);
  - `suspend_flow_run` exits and the run "will be rescheduled"; it needs persisted results (l.505-511).
  - Both accept a Pydantic `RunInput` form (`wait_for_input`; `docs/v3/advanced/interactive.mdx:29`).
- **HPC:** community `EBI-Metagenomics/prefect-slurm` (Apache-2.0, slurmrestd 0.0.40–0.0.42); `prefect-dask` with `dask-jobqueue` (0.9.0, last release 2024-08-22).
- **Migrations:** one tree per dialect, `src/prefect/server/database/_migrations/versions/sqlite/` (115 entries) and `…/postgresql/` (120 entries).
- **For Spectio:** `suspend` is Spectio's "stop and relaunch with cache"; `pause` is the rejected "short wait". A pattern for `parameter_edit` forms.

### Dagster
- Apache-2.0. 1.13.27 (PyPI, 2026-10-26); community `dagster-slurm` 1.22.0 (2026-09-29). External processes through Dagster Pipes.
- **Checks:** `blocking` asset checks are automatic, with no human; "if no result is emitted for the check, downstream execution proceeds" with a warning (`asset_check_spec.py:77-82`, `c94186b`). No human-in-the-loop module found **[to be validated]**.
- **For Spectio:** the check vocabulary, and a warning: Spectio's gate should fail closed when a blocking check errors or emits nothing (evidence for UX-103, R12).

## 6. TES backends

- **Funnel:** MIT, v0.12.2 (2026-02-23), moved to `calypr/funnel`. Backends Slurm, PBS, Grid Engine, HTCondor, Kubernetes (`compute/`).
- **TESK:** Apache-2.0, last tag v0.2 (2018-03-05), main 2026-01-26. Kubernetes only.
- **Engine side:** Nextflow's TES executor is in `nf-ga4gh` 1.5.0 (2026-07-02, active). `snakemake-executor-plugin-tes` was last committed 2024-09-07 (v0.1.3): stale.

## 7. Provenance: engine exporters and WRROC

| Exporter | Licence · version | Engine | Declares | Notes |
|---|---|---|---|---|
| **nf-prov** | Apache-2.0 · 1.8.0 (2026-10-12) | Nextflow | RO-Crate 1.1, Workflow RO-Crate 1.0, wfrun process/workflow/provenance **0.1** (`WrrocRenderer.groovy:590-611`) | WRROC since 1.4.0 (CHANGELOG, 2025-02-06). README: "1.8.x · 26.10 \| 1.7.x · 25.10 \| 1.6.x · 25.10"; `prov.directory` is new in 1.8.0. Also writes BCO |
| **snakemake-report-plugin-rocrate** | MIT · 0.1.0, **not on PyPI** (404 on 2026-10-26) | Snakemake | RO-Crate 1.1, wfrun process/workflow/provenance **0.5** (`rocrate_builder.py:294-305`) | In the `snakemake` organisation (`1989c5b`, 2026-10-23). Listed as the Snakemake Provenance implementation in `workflow-run-crate` `docs/index.md:103` (`31518a5`). Validates with `crs4/rocrate-validator` |
| snakemake-report-plugin-fairscape | Apache-2.0 · 0.1.0 (PyPI, 2026-08-18) | Snakemake | FAIRSCAPE EVI RO-Crate | Not WRROC |
| Sapporo `ro_crate.py` | Apache-2.0 · 2.4.0 | any (WES) | RO-Crate 1.1, wfrun **0.5** (`sapporo/ro_crate.py:47-50`) | Does not claim the Provenance profile (`docs/ro-crate.md`) |
| Nextflow data lineage | Apache-2.0 · since 25.04, experimental | Nextflow | own data model `v1beta1` | `lineage.enabled = true`; records runs, tasks and outputs with LIDs (`docs/tutorials/data-lineage.mdx`, `193a4c2`) **[to be validated]** as an input for Spectio |

**WRROC profiles.** The current release is **0.6 (2026-09-07)**, with 0.7-DRAFT in progress. The changelog (`docs/profiles/changelog.md`, `31518a5`) says that from 0.6 "Workflow Run Crate and Provenance Run Crate are not backward compatible with RO-Crate 1.1/Workflow RO-Crate 1.0", because the IRIs of `ComputationalWorkflow`, `FormalParameter`, `input` and `output` changed in the RO-Crate 1.3 context. Compatibility: RO-Crate 1.1 ↔ WRROC 0.1–0.5; RO-Crate 1.3 ↔ 0.6.

**For Spectio.** Every engine exporter in use today emits RO-Crate 1.1 with WRROC 0.1 or 0.5. A crate that merges an engine crate with Spectio's gate provenance must pick one version set (FC-041). For Snakemake, the upstream plugin can replace most of Spectio's own builder once it is released (FC-038).

## 8. GA4GH standards and Spectio

| Standard | Current version (2026-10-26) | Role for Spectio | Notes |
|---|---|---|---|
| **WES** | 1.1.0 (2023-09-14); `develop` unchanged (`c3fb9fb`) | **Facade.** When it ships is left to R1 (SR-010) | Paths at `wes.yaml:138-565`, base path `/ga4gh/wes/v1` (l.22-30); no pause endpoint; `State` has 11 values including `PAUSED` (l.673-686). `workflow_type` allows "another alternative supported by this WES instance" (l.271). Declare `NFL` and `SMK`, which the TRS `DescriptorType` enum defines (`tool-registry-service-schemas` `openapi/openapi.yaml:729-739`) and Sapporo's `service_info.json` uses. Spectio stores tasks, so it can implement `/tasks`, which Sapporo does not. Choose strict 1.1 or Sapporo 2.x (FC-044). References: Galaxy (MIT, generated pydantic models) and Sapporo (Apache-2.0) |
| **TES** | 1.1.0 (tag `v1.1`, 2022-11-14); `develop` still 1.1.0 (`8c57e04`, 2026-09-24) | **A later backend, reached through the engines' executors; never exposed by Spectio** | Nextflow: `nf-ga4gh` 1.5.0. Snakemake: stale plugin. Spectio needs at most a TES environment kind and a state adapter (FC-050) |
| **TRS** | tag 2.0.2 (2025-09-02; its file says `version: 2.1.0`) | **Client first (catalogue import), server later** | `DescriptorType` includes NFL and SMK. README:34-37: "TRS has largely reached a stable state … actively used by Galaxy, WorkflowHub.eu, … Sapporo". Whether WorkflowHub's TRS endpoint serves Nextflow and Snakemake entries is **[to be validated]** (FC-048) |
| **DRS** | 1.5.0 (2025-03-24, `fe25c39`) | **Input resolver at the periphery; a DRS server for artefacts later** | Nextflow resolves `drs://` natively through `nf-ga4gh` (read-only; under TES the URI is passed straight through, README:120-153). The Snakemake storage catalogue has no DRS plugin (FC-049) |
| service-info | part of WES | Required by the WES facade | — |
| WRROC / RO-Crate (not GA4GH) | WRROC 0.6 / RO-Crate 1.3 | **Core export format** | Pin the version set (FC-041) |

This agrees with the decision log entry "GA4GH: no change" (2026-10-26). The refinements are: TRS as a client, DRS through the engine where possible, and TES never as a Spectio interface.

## 9. Summary table

| Tool | Licence | Last release · activity | Engines | HPC | Steering | Overlap with Spectio · reuse |
|---|---|---|---|---|---|---|
| Seqera Platform | proprietary | Enterprise 26.1 (2026-05-22) | Nextflow | Slurm, LSF, PBS Pro, Grid Engine, Moab; SSH or Tower Agent | Resume, Relaunch (Platform launches only) | launch, monitoring, catalogue · coexist |
| `tw` / seqerakit | Apache-2.0 | v0.42.0 (2026-10-08); 2026-05-28 | — | — | — | Seqera clients only |
| nf-tower CE | MPL-2.0 | archived, 2025-01-30 | Nextflow | — | — | none |
| nf-shard | MIT | 0.1.23 (2024-07-14); last commit 2024-09-19 | Nextflow (Tower protocol) | — | none | monitoring; unmaintained |
| panoptes | MIT | 1.6.2 (2026-10-24); plugin 0.3.0 | Snakemake ≥ 9 | — | none (cancel marks a DB row) | monitoring · coexist |
| snkmt | MIT | 0.4.0 (2026-03-13); plugin 0.1.9 (2026-10-12) | Snakemake ≥ 9 | NFS-aware SQLite | none | local TUI · coexist |
| FlowO | MIT | plugin 2.2.0 (2026-07-27) | Snakemake ≥ 9 (server ≥ 9.23) | shared mount | none found | monitoring, catalogue, users, MCP · closest Snakemake neighbour |
| snakesee | MIT | 0.9.0 (2026-07-19) | Snakemake | — | none (not read) | TUI |
| Sapporo | Apache-2.0 | 2.4.0 (2026-10-14) | cwltool, Nextflow, Toil, Cromwell, Snakemake, ep3, StreamFlow | none built in (Docker socket) | cancel, delete | WES (extended), WRROC 0.5 · reference |
| sapporo-web | Apache-2.0 | last commit 2022-09-13 | — | — | — | stale client |
| Galaxy | MIT since 2026-02-25 | 26.1.2 (2026-10-26) | Galaxy workflows | slurm, drmaa, pbs, condor, kubernetes, pulsar… | "Pause for dataset review" step | WES routes (declares 1.0.0), DRS, TRS consumer, WRROC · reference, gate precedent |
| Arvados | AGPL-3.0 server / Apache-2.0 SDK | 3.2.1 (2026-03-02) | CWL | Slurm, LSF | none found | provenance · SDK only |
| Flyte 2 + nf-flyte | Apache-2.0 | flyte 2.12.1 (2026-10-21); nf-flyte 0.2.1 (2026-10-23) | Python; Nextflow (since 2026-10) | Kubernetes; Slurm over SSH | conditions (signal, timeout, webhook), MCP listing | closest design · watch |
| Prefect 3 | Apache-2.0 | 3.9.0 (2026-10-21) | Python | community Slurm worker | pause (blocking) or suspend (reschedule), typed input | gate patterns |
| Dagster | Apache-2.0 | 1.13.27 (2026-10-26) | Python | community `dagster-slurm` | automatic blocking checks only | check vocabulary |
| Toil | Apache-2.0 | 9.6.0 | CWL, WDL | yes (not re-read) | — | WES server (1.0.0) |
| Cromwell | BSD-3 | 92 (2026-01-30) | WDL | yes (not re-read) | — | future WDL target |
| Funnel | MIT | v0.12.2 (2026-02-23) | — (TES) | Slurm, PBS, Grid Engine, HTCondor, Kubernetes | — | TES backend |
| TESK | Apache-2.0 | v0.2 (2018) | — (TES) | Kubernetes | — | TES backend |
| proWES / cwl-WES | Apache-2.0 | 2026-01 | — | — | — | WES gateway |
| nf-prov | Apache-2.0 | 1.8.0 (2026-10-12; needs 26.10) | Nextflow | — | — | WRROC 0.1, BCO |
| snakemake-report-plugin-rocrate | MIT | 0.1.0, unreleased (2026-10-23) | Snakemake | — | — | WRROC 0.5 Provenance |

## 10. Spectio and other tools (neutral comparison, draft)

The draft below is the starting point for the docs page that FC-047 proposes. Facts are as of 2026-10-26 and each cell is sourced in §2–§7 of this note. Spectio is in design: its row describes what is specified, not what ships. The wording is neutral, with no pricing and no "alternative to" phrasing ([adoption note](adoption-and-positioning-2026-10-26.md) §2).

| | Engines | Where it runs | Launch from UI / API | Live monitoring | Stop at a stage, review evidence, resume | Standards | Licence |
|---|---|---|---|---|---|---|---|
| Spectio (planned) | Nextflow, Snakemake (CWL and WDL later) | self-hosted; runners on Slurm and Kubernetes under the user's account | yes | yes (engine plugins) | yes (gates with checks and evidence) | WES facade (planned), RO-Crate export | MIT |
| Seqera Platform | Nextflow | Seqera Cloud, or Enterprise on premises | yes | yes | resume and relaunch; no review gate | — | proprietary |
| nf-shard | Nextflow | self-hosted | no | yes | no | — | MIT |
| panoptes | Snakemake | self-hosted | no | yes | no | — | MIT |
| snkmt | Snakemake | local terminal | no | yes | no | — | MIT |
| FlowO | Snakemake | self-hosted (Docker Compose) | no | yes, plus a workflow catalogue | no (none found) | — | MIT |
| Sapporo | CWL, Nextflow, Snakemake, WDL, others | self-hosted (Docker) | yes (WES) | run state | no (cancel only) | WES 1.1 (extended), WRROC | Apache-2.0 |
| Galaxy | Galaxy workflows | self-hosted or public servers; HPC runners | yes | yes | pause-for-review step | WES, TRS, DRS, WRROC | MIT |
| Arvados | CWL | self-hosted or cloud; Slurm, LSF | yes | yes | not found | — | AGPL-3.0 / Apache-2.0 |
| Flyte 2 | Python; Nextflow through a plugin | Kubernetes (Slurm plugin over SSH) | yes | yes | yes (conditions and signals) | — | Apache-2.0 |
| Prefect 3 | Python | self-hosted or cloud (community Slurm worker) | yes | yes | yes (pause or suspend with input) | — | Apache-2.0 |

## 11. What this means for Spectio

| Topic | Implication | Finding |
|---|---|---|
| Positioning | State the differentiators precisely: shared POSIX file systems, the user's own account, Snakemake, item-level QC gates | FC-043, FC-042 |
| Snakemake logger | Add `spectio` to the user's loggers; support a stated version range and test it | FC-039, FC-040 |
| Provenance | Use the Snakemake exporter when installed; pin RO-Crate 1.1 + WRROC 0.5 for 0.x; pin nf-prov per Nextflow version | FC-038, FC-041, FC-045 |
| WES | Strict 1.1.0; Sapporo 2.x is a non-goal; Galaxy is a reference, not a conformance target for auth | FC-044, FC-046 |
| TRS, DRS, TES | TRS client first; `drs://` passed through to Nextflow; TES only through engine executors | FC-048, FC-049, FC-050 |
| Prior art | Flyte conditions, Galaxy pause, Prefect suspend, Dagster blocking checks | FC-053 |
| Docs | One owner for the comparison page, refreshed each release stage and each quarter | FC-047 |
| Transport | panoptes and FlowO post synchronously per event with no spool: evidence for the open ingest-contract findings | SR-001, SR-017, CH-005 (cited in R9) |
| Licences | Arvados server code is AGPL; Galaxy is MIT only from 2026-02-25: evidence for the open licence finding | CH-034 (cited in R9) |

## 12. Corrections to earlier documents

| Claim | Where | Verdict (2026-10-26) |
|---|---|---|
| nf-tower CE (MPL-2.0) archived on 2025-01-30 | adoption §1 | verified |
| Seqera Platform is Cloud plus Enterprise; no free self-hosted edition | adoption §1 | partly true: Enterprise is current; "no free self-hosted edition" **[to be validated]** |
| nf-shard is MIT; last commit 19/09/2024 | synthesis §2bis, adoption §1 | verified ("79 stars" not checked) |
| "Snakemake's own docs list a single monitoring option: panoptes … through `--wms-monitor`" | adoption §1 | **wrong**: the cited page is a 2021 build of 6.1.0; current docs describe logger plugins (12 in the catalogue) |
| `--log-handler-script` and `--wms-monitor` are gone | synthesis §2 | verified |
| panoptes: MIT, plugin 0.3 | synthesis §2 | verified |
| snkmt (SQLite + TUI); flowo, stomp, prometheus exist | synthesis §2 | verified; FlowO is much more than a logger |
| "Mature for tracking, nothing for steering" | synthesis §2 | partly true: true for panoptes, snkmt and FlowO; the other 9 loggers were not read |
| WES 1.1.0 has `/runs`, `/status`, `/tasks`, `cancel`, no pause | synthesis §3, §7bis | verified |
| WES `workflow_type` `NFL` / `SMK`; base path `/ga4gh/wes/v1` | api §2.B, §5 | verified (resolves the **[to be validated]** in SR-010) |
| TES 1.1.0 | synthesis §3 | verified |
| Sapporo is a multi-engine WES | synthesis §3 | verified, but it deviates from WES 1.1 and adds ep3 and StreamFlow |
| Sapporo: "HPC schedulers not mentioned" | synthesis §7quater | partly true: no built-in HPC support |
| Galaxy "as an example of a minimal WES" | synthesis §3 | outdated: all WES routes including tasks, declared as 1.0.0; MIT since 2026-02-25 |
| nf-prov writes a WRROC since 1.4.0 | synthesis §7quinquies | verified; declares 0.1; 1.8.x needs Nextflow 26.10 |
| "For Snakemake no native exporter was found" | synthesis §7quinquies | **wrong**: `snakemake-report-plugin-rocrate` (unreleased) |
| Tower Agent: outgoing WebSocket, user's account, Slurm/LSF/PBS/SGE | synthesis §7quater | partly true: SSH by default, Tower Agent without SSH; PBS Pro, Grid Engine, LSF, Moab, Slurm; WebSocket **[to be validated]** |
| Seqera Platform: relaunch, no interventions | synthesis §7quater | verified |
| Prefect 3 can pause with input | synthesis §5 | verified, but there are two mechanisms (pause and suspend) |
| 28 Snakemake executor plugins, including tes, kueue, flux | schedulers §1 (l.48) | verified; the TES plugin is stale since 2024-09-07 |

## 13. Not checked, or to be validated

- Seqera: "no free self-hosted edition"; Tower Agent transport (WebSocket).
- Star counts and archive flags (GitHub API blocked).
- FlowO: steering absent (only the sdist and docs were read); repository location.
- The nine other Snakemake loggers.
- Arvados and Dagster: no steering or human-in-the-loop found.
- Galaxy's licence before 2026-02-25 (AFL-3.0 is the reviewer's memory).
- WorkflowHub's TRS endpoint for Nextflow and Snakemake entries.
- Whether a repeated `--logger` keeps every value, and how a profile's `logger:` list combines with an explicit `--logger`.
- Nextflow data lineage as an input for Spectio's post-hoc collector.
- Whether `flyteplugins-nextflow` can use a POSIX `work_dir` under the Slurm connector.

**Re-check cadence.** Flyte and nf-flyte, FlowO, panoptes, Seqera Platform and the Snakemake RO-Crate plugin move fast. Re-check this note every quarter and at each release stage ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §14), and write a new dated note rather than editing this one.
