# Open workflow steering platform (alternative to Seqera Platform): exploration synthesis

Date: 23/10/2026. Based on five parallel explorations (Nextflow, Snakemake, GA4GH and existing projects, viewers and QC, architecture and HPC). Points marked **[to be validated]** could not be confirmed in any source that was read.

## 1. Verdict

**It is feasible, and the niche is still open, but narrower than first written.** Both engines now expose native, structured mechanisms for emitting events (plugins), without parsing logs or going through `subprocess` for tracking. Monitoring is already covered: Seqera Platform for Nextflow, and MIT tools for Snakemake (panoptes, snkmt, FlowO; FlowO also has a workflow catalogue, users and MCP access). **Revised on 27/10/2026 (R9):** since October 2026, Flyte 2 with `flyteplugins-nextflow` and `nf-flyte` (Apache-2.0) can run a Nextflow pipeline, pause on a condition until a signal, and resume ([landscape note](../research/landscape-2026-10-26.md) §5). What is missing is **steering** with four properties together, which no tool read offers (non-exhaustive search, 2026-10-26): (1) shared POSIX file systems, not object stores (Flyte needs the Nextflow work directory on an object store on a cluster, `plugins/nextflow/README.md:90`); (2) the runner runs under the user's own account, not with a shared SSH key (Flyte's Slurm plugin submits over SSH with a configured key, `plugins/slurm/README.md:3,22-31`); (3) Snakemake as well as Nextflow; (4) gates are item-level QC reviews with evidence, not a typed value. Whether `flyteplugins-nextflow` can use a POSIX `work_dir` under Slurm is **[to be validated]** (R9 spike 4). The comparison is re-checked on the cadence set in [`documentation-system.md`](documentation-system.md) §1.

Three decisions shape everything else:

1. **An in-house, engine-independent event log** as the source of truth (append-only). Each engine has its own small engine plugin (`nf-spectio`, the Snakemake logger plugin) that writes to it.
2. **Implement the 5 ingestion routes of the Tower protocol on the server side** (revised on 23/10 after reading the code, see section 2bis). The `nf-tower` plugin ships with Nextflow: you just point `tower.endpoint` at our server, with nothing to install, as nf-shard does. The protocol remains undocumented and accepts no commands from the server, so steering goes through our launcher, not through this protocol.
   **Revised on 26/10/2026 ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)):** Nextflow reports only through Spectio's own plugin `nf-spectio`. The Tower routes are not implemented, so a run can report to Seqera Platform (`nf-tower`) and to Spectio at the same time (**[to be validated]** in spike T2).
3. **The QC gate is modelled in our application, not in the engine.** Neither engine has a native pause: the reliable pattern is "stop cleanly after step N, then relaunch with resume".

## 2. Integration per engine (without log parsing)

### Nextflow
- **In-house plugin** based on `TraceObserverV2` (interface marked `@Beta`, verified). Available hooks: `onFlowCreate`, `onFlowBegin`, `onFlowComplete`, `onFlowError`, `onProcessCreate`, `onProcessTerminate`, `onTaskPending`, `onTaskSubmit`, `onTaskStart`, `onTaskComplete`, `onTaskCached`, `onWorkflowOutput`, `onFilePublish`.
- This gives us control over the event schema and the transport (HTTP with retry, or a buffered JSONL file).
- **Quick prototype**: the official `nf-weblog` 1.2.0 plugin (Apache-2.0, Nextflow ≥ 25.10, verified) sends JSON POSTs. `-with-weblog` is deprecated in 26.10 and no longer supported; use the `nf-weblog` plugin (Nextflow `docs/reference/cli/run.mdx:226-230`, read 2026-10-26). Announced events: `started`, `process_submitted`, `process_started`, `process_completed`, `error`, `completed`.
- `nf-tower` (shipped with Nextflow) calls `/trace/create`, `/begin`, `/progress`, `/heartbeat`, `/complete` via `tower.endpoint`. Reimplementing this server would be fragile reverse engineering.
- Plugin distribution: official registry (since 25.10) or a private JSON repository.
- **Points of attention**: the `-resume` cache depends on the launch directory; changing a parameter that feeds into the hash invalidates tasks; a Nextflow upgrade can break the cache for some processes: `eval` outputs in 25.10 and 26.10, map inputs in 26.04 (see each release's 'Cache-breaking changes' migration note: `docs/migrations/25-10.mdx:284`, `26-04.mdx:405-409`, `26-10.mdx:225-227`).

### Snakemake
- **Logger plugin** (`snakemake-interface-logger-plugins`, enabled with `--logger <name>`, verified). `--log-handler-script` and `--wms-monitor` have disappeared from the recent CLI (read in the code, not in the docs).
- The handler runs inside the Snakemake process and receives typed `LogRecord`s: `WORKFLOW_STARTED`, `RUN_INFO`, `JOB_INFO`, `JOB_STARTED`, `JOB_FINISHED`, `JOB_ERROR`, `PROGRESS`, `ERROR`, etc. Fields may change between versions: read defensively. The supported Snakemake range and the two tested versions are in [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §1. *(assumed — pending Thomas, inbox #28)*
- **Steering through the CLI** (revised on 27/10/2026; was one Python worker per run calling `SnakemakeApi`): Snakemake runs as a CLI subprocess, or as an `sbatch` head job, in a per-workflow environment (pixi, conda or an environment module), its version pinned per lineage as `NXF_VER` does for Nextflow; `snakemake --until <last rules of the stage>` stops at a stage and `--forcerun` reruns from one. The Python API is used only through a small shim inside that environment. The runner never imports Snakemake, so workflows pinned to different Snakemake versions share one runner, and the runner stays within its 80 MB budget ([`cli-and-shared-libraries.md`](cli-and-shared-libraries.md) §6). The constraint is "no parsing of process output for tracking": tracking comes only from the logger plugin. The logger and the working directory are global to the process, hence **one process per run**. Supported versions: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.4. *(assumed — pending Thomas, inbox #28)*
- Existing tools (checked 2026-10-26, [landscape note](../research/landscape-2026-10-26.md) §3): the [plugin catalogue](https://snakemake.github.io/snakemake-plugin-catalog/) lists 12 logger plugins, and several can run at once. `panoptes` (MIT; server `panoptes-ui` 1.6.2, 2026-10-24; logger plugin 0.3.0; active again, its plugin README says it replaces "the legacy `--wms-monitor` integration that was removed in Snakemake 9"); `snkmt` (MIT; 0.4.0, plugin 0.1.9; SQLite + TUI built for network file systems); FlowO (MIT; plugin 2.2.0, 2026-07-27; SSE monitoring, per-run DAG, jobs and timeline views, a versioned workflow catalogue, users and an MCP endpoint, [FlowO docs](https://flowo-docs.pages.dev/)); `snakesee`, `stomp`, `prometheus` and others. Monitoring, a catalogue and MCP access already exist in MIT tools; **no gate-and-steer tool for Snakemake** was found: none of those read launches, stops at a stage, gates or relaunches (FlowO: none found in its sdist and docs **[to be validated]**). FlowO is the closest neighbour. Comparison: [Spectio and other tools](../features/other-tools.md). *(assumed — pending Thomas, inbox #27)*

## 2bis. Code reading: nf-tower, nf-shard, Snakemake (23/10/2026)

### nf-tower protocol (Nextflow `master` code, 22/10/2026)
`TowerObserver` now implements `TraceObserverV2`.

| Hook | Call | Content |
|---|---|---|
| `onFlowCreate` | `POST /trace/create` | `sessionId`, `runName`, `projectName`, `repository`, `workflowId` (read from `TOWER_WORKFLOW_ID`), `instant`. Expected response: `workflowId` (+ optional `watchUrl`) |
| `onFlowBegin` | `PUT /trace/{id}/begin` | `workflow` (full metadata, `params`, `configText`, manifest…), `processNames`, `towerLaunch`, `dag` (new, optional) |
| sender thread | `PUT /trace/{id}/progress` | batches of `tasks` (all trace record fields in camelCase, plus `executor`, `numAttempts`, `gpuMetrics`…), `progress`, `containers`. Sent every **1 s** or per **100 tasks** |
| same | `PUT /trace/{id}/heartbeat` | `progress`, every **1 min** when there is no activity |
| `onFlowComplete` | `PUT /trace/{id}/complete` | final `workflow`, `metrics` aggregated per process, `progress` |

- `progress`: `succeeded`, `failed`, `ignored`, `cached`, `pending`, `submitted`, `running`, `retries`, `aborted`, CPU/memory load and peaks, per-process breakdown.
- An error on `create`, `begin` or `progress` **aborts the run** (`AbortRunException`): our server must be available and respond quickly.
- `TOWER_WORKFLOW_ID` lets our launcher set the identifier before launch, to link the run to our record.
- Reports: `tower.yml` (`reports` section) describes the published files to display. The plugin writes a local TSV (`key, path, size, display, mime_type`) without sending it over HTTP. A good model for declaring QC artefacts.

### nf-shard
- Next.js + Prisma + PostgreSQL, MIT. It implements exactly these 5 routes, in about 200 lines.
- `create` generates an identifier, `begin` creates the workflow, `progress` does an upsert per `(workflowId, taskId)` with the raw task JSON, `complete` stores stats and metrics.
- **No token verification** (any non-empty string). No steering apart from a beta submission feature via a separate "shard-worker" project.
- Last commit: **19/09/2024**. Little maintained, but it proves the approach works.

### Snakemake: no built-in equivalent
- No built-in monitoring protocol, no bridge to the Tower protocol found. A **logger plugin** must be installed in the environment (`pip install snakemake-logger-plugin-<name>`) and enabled with `--logger`.
- **Good news**: `--logger` is not passed on to remote jobs (verified in `spawn_jobs.py`). Events are therefore sent **only from the main process**, not from the compute nodes. The same applies to Nextflow, where the observer runs in the main JVM.
- **Pitfall**: if the plugin does not declare `has_filter = True`, Snakemake applies its default filter to it, and `--quiet` suppresses events.
- Events are emitted via a `QueueListener`: a slow handler does not block jobs, but delays subsequent events.
- `JOB_FINISHED` does not include resource usage: the `benchmark` directive is required (an asymmetry with Nextflow, which sends `%cpu`, `rss`, etc.).
- The panoptes plugin makes one synchronous HTTP call per event, without retry, with a JSON message encoded in a form. Not to be reused. Better to copy the Tower model: batches every second, heartbeat, local buffer.
- Useful Python API on the launcher side: `printd3dag`, `printrulegraph`, `summary`, `list_changes`, `unlock`, `create_report`. The logger must be a registered package (an instance cannot be passed directly).

### Consequence for the architecture
Two ingestion gateways that write to the same event log:
1. **`/api/tower/*`**: Tower compatibility for Nextflow, with no installation, storing the raw JSON and reading fields tolerantly.
2. **`/api/v1/ingest/events`**: our native format, for the Snakemake plugin (and possibly an in-house Nextflow plugin later, if the Tower protocol changes or if extra hooks such as `onWorkflowOutput` are needed).

**Revised on 26/10/2026 ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)):** only the second gateway is built. `nf-spectio` and the Snakemake logger both post to `/api/v1/ingest/events`.

## 2ter. Advanced scenarios: what each engine exposes (code read on 23/10/2026)

Versions read: Snakemake 9.27 (main), Snakemake SLURM plugin (main), Nextflow 26.10.3 (main).

### Matrix

| Scenario | Snakemake (logger plugin) | Nextflow (Tower protocol) | How to fill the gap |
|---|---|---|---|
| **Conditional execution / dynamic DAG** | `is_checkpoint` on the job; `<TBD>` inputs; no "DAG updated" event; the new total only appears at the next `PROGRESS` | Full static DAG in `begin`; a task filtered out by `when:` produces **no** event | Display "at least N" while a checkpoint is open; keep a history of totals. On the Nextflow side, a companion plugin to report unscheduled tasks |
| **Temporary files** | `temp()` invisible in events; deletion = a plain text message "Removing temporary output"; deletions deferred while a checkpoint is open | No temporary files in the Snakemake sense; `cleanup = true` only at the end of a successful run, and it breaks `-resume`; no "eager" cleanup in the code | Snakemake: flags read via the API at launch + message turned into a `temp_removed` event. "Deleted" status ≠ "missing" |
| **SLURM job arrays** | Supported (`--slurm-array-jobs`, SLURM plugin ≥ 2.6.0); the SLURM ID (`123` or `123_4`) reaches the logger **only on error** | `array` directive: one record per child task, `nativeId` = `123_4` on SLURM (other formats for LSF, SGE, PBS, AWS, Google); the parent is never reported | Snakemake: read `.snakemake/incomplete/` or the persistence database, then `sacct --name <run_uuid>`. Nextflow: parse `nativeId` per executor |
| **Retries** | Attempt number not sent; same `jobid` re-emitted after "Trying to restart job N" | `attempt` present; a retry = new `taskId` and new `work` directory; raw `failed` includes retries and ignored tasks | Count attempts in the Snakemake plugin; link Nextflow attempts by process + tag |
| **Executors / backends** | Executor name absent from events; only `local` (true/false) | `executor` per task (per-process override visible), `queue`, `nativeId`, `machineType`/`cloudZone` in the cloud; no hostname or effective partition on HPC | Snakemake: read `--executor` from the command line. HPC: `sacct` from the native ID |
| **Storage** | Visible in paths (`retrieve from storage`, `send to storage`); transfers as text messages; credentials masked | `workDir`, `outputDir`, `workdir` per task; **no published files sent over HTTP** | Snakemake: URI scheme = provider. Nextflow: companion plugin (`onFilePublish`, `onWorkflowOutput`) |
| **Wrappers / modules** | Nothing in events; renamed rule visible (`as M_*`), originating module absent | `process` = qualified name (`NFCORE_RNASEQ:RNASEQ:FASTQC`); nothing on module version or source; the `module` field = Lmod | Snakemake: API (`rule.wrapper`, `script`, `software_env_specs`). Nextflow: companion plugin (`meta.yml`, module registry ≥ 26.04) + `modules.json` on the server side |
| **Software environment** | Absent from events; present in `.snakemake` metadata after execution (`software[]`, hash) | `containers[]` (rich with Wave, otherwise only the image); conda and spack absent; no digest | Snakemake: metadata. Nextflow: companion plugin |
| **Job groups** | `GROUP_INFO` + instance UUID in `JOB_STARTED`: 1 group = 1 scheduler job | Not applicable | n:m model between attempts and scheduler jobs |
| **Measured resources** | Absent; TSV from the `benchmark` directive | `%cpu`, `rss`, durations, etc. in each task | Read the benchmark TSV; `sacct` for efficiency |
| **Logical task key** | rule + wildcards **[to be validated]** | process + tag **[to be validated]** | One `Task` per key; retries are `Attempt`s under it *(assumed — pending Thomas, inbox #40)* |

### Consequences

1. **Nextflow: hybrid approach.** The Tower protocol covers basic tracking with no installation. A `TraceObserverV2` **companion plugin** is still needed for modules and versions, published files, conda/spack, `storeDir` and tasks filtered out by `when:`. It pushes to an extension route.
   **Revised on 26/10/2026 ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)):** the companion plugin `nf-spectio` becomes the only Nextflow route. The Tower column of the matrix above still shows what the `TowerObserver` sends; it is itself a `TraceObserverV2`, so `nf-spectio` sees the same hooks and more.
2. **Snakemake: three sources.** The logger plugin (with `has_filter = True`), a few text messages turned into typed events (versioned regexes, raw message kept), and a collector that reads `.snakemake` (or the `--persistence-backend db` database, Snakemake ≥ 9.17, Snakemake CHANGELOG l.283) and `sacct`.
3. **Never assume every transition is seen**: Nextflow only sends the latest state per task every second. Upsert per `(run, task_id)`, applying the state lattice of [`api-and-data-model.md`](api-and-data-model.md) §8.2.
4. **Keep the raw JSON** of each event alongside the normalised columns while the run is active; once it is terminal, raw payloads move to a compressed archive in the file store and the terminal payload of each task is kept ([`api-and-data-model.md`](api-and-data-model.md) §8.4). *(assumed — pending Thomas, inbox #28)*

### Extended data model

- **Lineage**: chain of linked runs (resume, new parameters, next stage).
- **Run**: engine and version, workflow source (repo, revision, commit), directories, parameters, resolved config, default executor, state.
- **DagSnapshot**: successive versions of the DAG; "known" total or "at least N".
- **Component**: Nextflow process, module or subworkflow; Snakemake rule, wrapper or module; qualified name, source, version, sha.
- **SoftwareEnv**: container (image, digest if known, Wave), conda, spack, envmodules.
- **Task**: logical instance (hash or wildcards), reason for execution, normalised status.
- **Attempt**: number, requested and measured resources, exit code, error action.
- **SchedulerJob**: executor, native ID, array parent ID and index, partition, node, machine type. **n:m** relationship with Attempt (groups, arrays).
- **ComputeEnv**: cluster or cloud, executor type, partition, region.
- **Artifact**: URI, storage provider, role (input, output, published, report, QC), lifecycle (created → published | temporary → deleted, and by whom).
- **Event**: append-only log, raw + normalised payload.

Normalised statuses: `QUEUED`, `SUBMITTED`, `RUNNING`, `SUCCEEDED`, `RETRIED`, `FAILED`, `FAILED_IGNORED`, `CANCELLED`, `SKIPPED_CACHED`, `STORED`, `NOT_SCHEDULED`.

**Superseded (27/10/2026).** The task and attempt state enums are owned by [`api-and-data-model.md`](api-and-data-model.md) §7.2 (lower case; "retried" and "failed (ignored)" are display flags, not states).

## 3. Standards and existing projects

| Item | Verdict |
|---|---|
| **GA4GH WES 1.1.0** | A good **facade**: `/runs`, `/runs/{id}/status`, `/tasks`, `cancel`. No pause, no gate, no resume, poor task detail. To be exposed as a thin layer, with extensions for the rest. |
| **GA4GH TES 1.1.0** | Task-centred model. Useful as an execution target later, not as the core. |
| **DRS / TRS** | Periphery: DRS for artefacts, TRS for resolving a workflow. |
| **Sapporo** (DDBJ, Apache-2.0) | 2.4.0 (2026-10-14), active. Multi-engine WES (cwltool, Nextflow, Toil, Cromwell, Snakemake, ep3, StreamFlow), but not strictly WES 1.1 (`docs/wes-compatibility.md`: engine-keyed `default_workflow_engine_parameters`, `RunLog.outputs` as a list of `FileObject`, `workflow_engine` required, `/tasks` returns 400). No built-in HPC (engines run in Docker). Writes RO-Crate 1.1 + WRROC 0.5. Its `ro_crate.py` and WES compatibility matrix are references, not a conformance target ([`api-and-data-model.md`](api-and-data-model.md) §10). *(assumed — pending Thomas, inbox #17)* |
| **Arvados, Seqera Platform** | Too monolithic to serve as a base. Arvados for provenance ideas. |
| **Galaxy** (MIT from 2026-02-25, `LICENSE.txt` at `fd43a3c`) | Serves every WES 1.1 route including `/tasks` (`lib/galaxy/webapps/galaxy/api/wes.py:64-151`) but declares `supported_wes_versions=["1.0.0"]` (`services/wes.py:412`) and uses `x-api-key`; ships DRS and a TRS consumer in `release_26.1` (`5a58507`). Galaxy WES (MIT): reference for the facade's pydantic models (generated, `lib/galaxy/schema/wes/gen.sh`). Its `PauseModule` ("Pause for dataset review", `lib/galaxy/workflow/modules.py:2041-2110`) records approve or cancel per invocation step: the bioinformatics precedent for a review gate. *(assumed — pending Thomas, inbox #17)* |
| **Flyte 2** + `flyteplugins-nextflow`, `nf-flyte` (Apache-2.0) | `flyte` 2.12.1 (2026-10-21). Since 2026-10 runs Nextflow pipelines: `flyteplugins-nextflow` (first PyPI release 2026-10-16) runs the head in a Flyte task, `nf-flyte` 0.2.1 (2026-10-23) runs each task as a Flyte child action; "Aborting the Flyte run aborts the pipeline and its running tasks" (flyte-sdk `0aabafa`, `plugins/nextflow/README.md:1-12`). `flyte.new_condition` pauses a run until signalled from the UI, the CLI or the API (`plugins/hitl/README.md:4-12`). Limits: on a cluster the work directory must be on an object store (S3, GCS, Azure) (`plugins/nextflow/README.md:90`); Slurm is reached over SSH with a configured key and needs Pyxis/Enroot or Apptainer (`plugins/slurm/README.md:3,22-31`). The closest design to Spectio's interventions; watched. |
| **nf-shard** (MIT) | Community `nf-tower`-compatible server, monitoring only; unmaintained since 2024 (last commit `f40ce84`, 2024-09-19; last tag 0.1.23, 2024-07-14). *(assumed — pending Thomas, inbox #17)* |
| **Cromwell, Toil, Funnel, TESK** | Engines or task servers: future targets for WDL/CWL/TES. Funnel moved to `calypr/funnel` (v0.12.2, MIT, 2026-02-23); TESK's last release is v0.2 (2018). *(assumed — pending Thomas, inbox #17)* |

Rows refreshed on 27/10/2026 from the [landscape note](../research/landscape-2026-10-26.md) (facts as of 2026-10-26; every source is there). The Flyte 2 row is added by R9 FC-043. *(assumed — pending Thomas, inbox #17)*

The internal model could be aligned with **OpenLineage** (lineage, via an optional exporter) and **OpenTelemetry** (traces and metrics), without putting them in the core.

## 4. Engine-agnostic data model (proposal)

- **Run**: engine, workflow, typed parameters, state, dates, `stages`.
- **Task** (Nextflow process / Snakemake rule), **Attempt** (attempt, with retry), **ResourceUsage** (requested and measured), **Artifact** (URI, type, checksum).
- **Event**: `(run_id, seq, event_id ULID, ts, type, payload)`, append-only, uniqueness constraint on `(run_id, event_id)` for idempotent ingestion. The `runs` and `tasks` tables are projections, built from the log by one projector after ingest has acknowledged ([`api-and-data-model.md`](api-and-data-model.md) §8.1) *(assumed — pending Thomas, inbox #28)*. The per-run `seq` resumes a single-run SSE stream; streams over many runs resume by snapshot then tail ([`api-and-data-model.md`](api-and-data-model.md) §8.2).
- **States**: superseded by [`api-and-data-model.md`](api-and-data-model.md) §7.1 (run and gate enums, WES mapping). *(assumed — pending Thomas, inbox #29)*

## 5. QC gates and stage-by-stage execution

Engine-independent model:
- **Stage**: a logical unit (alignment, segmentation…) linked to a set of tasks.
- **Checkpoint**: placed after a stage, with the QC artefacts to display, a policy (mandatory, auto-approval on threshold, timeout) and a lifecycle `pending → awaiting_review → approved | rejected | params_changed → rerun | continue`.
  **Superseded (27/10/2026):** Intervention = Gate. Decisions are `approve`, `apply`, `go_back`, `stop` ([`api-and-data-model.md`](api-and-data-model.md) §7, `decisions`); external signals go to `POST /gates/{id}/signals` (api §5). States superseded by api §7.1 (27/10/2026). *(assumed — pending Thomas, inbox #29)*
- **Decision**: author, date, comment, modified parameters, stage to resume from. Append-only audit trail.

The three desired scenarios:
1. **Change the parameters and relaunch everything**: a new run linked to the previous one.
2. **Continue to the end**: relaunch with resume, with no stage limit.
3. **Iterative, in parts 1, 2, 3, 4**: a chain of short, idempotent runs.

An **adapter per engine** translates "stop after N" and "resume from X":
- Snakemake: `until` / `omit_from`, then a new run with the modified config. The `.snakemake` metadata avoids redoing everything. Snakemake `checkpoints` are reserved for data-dependent DAGs.
- Nextflow: `--stage` parameter (or separate workflows) plus `-params-file`, then `-resume` with the session preserved. `-entry` has been deprecated since 24.10. Keep control parameters out of the task hash. A task that waits for approval in a loop would block an executor slot: to be avoided on HPC. **Revised on 25/10/2026 (decision log, UI review round 2):** Nextflow stops at a stage through a generated `ext.when = false` config; pipelines do not cooperate through `params.stage` ([`checking-scenarios.md`](checking-scenarios.md) §12).

Prior art for gates (checked 2026-10-26, [landscape note](../research/landscape-2026-10-26.md) §4, §5):

| Mechanism | Blocking or suspending | Who decides | Typed input | Timeout default | Source |
|---|---|---|---|---|---|
| Prefect 3 `suspend_flow_run` | suspends: the process exits and the run "will be rescheduled"; needs persisted results | a person or an API call | Pydantic `RunInput` (`wait_for_input`, `docs/v3/advanced/interactive.mdx:29`) | not read **[to be validated]** | `src/prefect/flow_runs.py:505-511`, `21a1f02` |
| Prefect 3 `pause_flow_run` | blocks: the process stays alive until resumed | a person or an API call | Pydantic `RunInput` | `timeout: int = 3600`, then the flow fails | `flow_runs.py:166-200` |
| Flyte 2 `flyte.new_condition(name, prompt, data_type)` | pauses the run until signalled | the UI, the CLI (`flyte signal condition …`) or a program; an MCP tool lists "the points where it is paused for external input" (`src/flyte/ai/mcp/_tools.py:1133`) | `data_type` | a timeout (default not read **[to be validated]**), and a webhook that POSTs a `{callback_uri}` | `src/flyte/_condition.py:15-69`, flyte-sdk `0aabafa`; Flyte 1 had `approve`, `wait_for_input`, `sleep` (`flytekit/core/gate.py:136-166`) |
| Galaxy "Pause for dataset review" (`PauseModule`) | pauses the invocation step | a person: approve or cancel per invocation step | none | not read | `lib/galaxy/workflow/modules.py:2041-2110`, `fd43a3c` |
| Dagster `blocking` asset checks | blocks downstream automatically | no human; if no result is emitted, downstream proceeds with a warning | — | — | `asset_check_spec.py:77-82`, `c94186b` |
| Airflow 3.1 approval operators, Argo `suspend` | (earlier entries, not re-read in R9) | | | | — |

Spectio's choice is Prefect's `suspend`: stop and relaunch with the cache (§5bis, long wait). Prefect's `pause` is the rejected short wait: it keeps the process alive and holds an HPC slot or a login-node process. Flyte ships the closest combination (typed intervention, outgoing webhook with a signal URL, MCP listing): its callback-URI pattern is the reference to compare with `POST /api/v1/gates/{id}/signals` ([`api-and-data-model.md`](api-and-data-model.md) §2 E, §5); the signal semantics are still open (R12, UX-110). Prefect's fail-after-timeout default is evidence for the `timeout` and `action` vocabulary. Galaxy is the bioinformatics precedent for a review gate.

## 5bis. Intervention points: humans, AI agents and external systems (added 23/10)

Goal: the same stopping point can be resolved by a human, by an AI agent, or by an external system (lab robot, instrument, LIMS, script). The pipeline does not need to know who decides.

### The concept: `Intervention` (generalises the Checkpoint)
**Superseded (27/10/2026):** Intervention = Gate. Decisions are `approve`, `apply`, `go_back`, `stop` ([`api-and-data-model.md`](api-and-data-model.md) §7, `decisions`); external signals go to `POST /gates/{id}/signals` (api §5). States superseded by api §7.1 (27/10/2026). The MCP tool names below are historical. *(assumed — pending Thomas, inbox #29)*

- **Type**:
  - `approval`: approve or reject;
  - `choice`: choose a branch;
  - `parameter_edit`: modify parameters via a form generated from a **JSON Schema**;
  - `data_input`: provide a file or a value;
  - `external_wait`: wait for a signal from an external system, for example "plate ready";
  - `external_action`: the platform triggers an external action and waits for it to finish.
- **Evidence**: QC artefacts (thumbnails, reports), machine-readable **QC metrics in JSON**, a text summary. An agent does not read a 20 MB HTML report; it reads the metrics and the thumbnails.
- **Policy**:
  - who can resolve (human roles, agent identity, robot service account);
  - mode: `human_only`, `agent_proposes_human_confirms`, `agent_auto` under thresholds, `system`;
  - optional quorum, timeout, default action on expiry, escalation.
- **Decision**: actor type (`human`, `agent`, `system`), identifier, **model and version** for an agent, justification, **evidence consulted** (artefact IDs and hashes), parameter diff, idempotency key. Append-only, hence a complete audit.

### One API, three facades
1. **REST API + OpenAPI**: the single source; everything the UI does goes through it.
2. **Web UI** (humans): intervention queue, viewers, parameter form, decision history.
3. **MCP server** (AI agents):
   - tools `list_interventions`, `get_intervention` (evidence + thumbnails as images), `propose_decision`, `submit_decision`, `get_run`, `compare_runs`, `relaunch`;
   - the MCP 2026-07-28 specification is **stateless**, with handles passed as arguments, which fits intervention IDs well;
   - it also defines `input_required` requests and a `tasks` extension for long-running operations.
4. **Webhooks + events (SSE)** (systems and robots):
   - outgoing notification when an intervention opens;
   - authenticated incoming signal (`POST /interventions/{id}/signal`) when the system has finished; **superseded (27/10/2026):** `POST /gates/{id}/signals` (api §5) *(assumed — pending Thomas, inbox #29)*;
   - **SiLA 2** adapter (lab automation standard, Python library `sila2`) in a later phase.

An agent can also be **called** by the platform: a "reviewer agent" configured per pipeline, which receives the intervention, reads the evidence via MCP and proposes a decision.

### Engine-side mechanics
- **Long wait** (hours, days, a wet-lab step): the pipeline stops after step N (`until` for Snakemake, `--stage` parameter for Nextflow). The platform holds the `AWAITING_INTERVENTION` state, then the launcher relaunches the next stage with the new parameters or new data. Nothing runs during the wait. **Revised on 25/10/2026 (decision log, UI review round 2):** Nextflow stops at a stage through a generated `ext.when = false` config; pipelines do not cooperate through `params.stage` ([`checking-scenarios.md`](checking-scenarios.md) §12). States superseded by api §7.1 (27/10/2026) *(assumed — pending Thomas, inbox #29)*.
- **Short wait** (minutes): option of a **local** wait task (Snakemake `localrule` rule, Nextflow `executor 'local'` process) that polls the API. It does not consume a cluster slot, but keeps the main process alive.
- **External intervention within the flow**: part 1 → `external_action` (the robot prepares, the instrument acquires) → "done" signal with the path to the new data → part 2. This is the generalised "iterative in parts" mode.

### Safeguards for AI
- **Limited-scope** agent tokens: an agent can propose anywhere, but only approves on its own where the policy allows it. Costly or irreversible actions (deletion, large launch) require a human.
- AI decisions are flagged as such, with a justification, and a human can revert them as long as the next stage has not started.
- Artefact content (logs, HTML reports, metadata) is **untrusted** for an agent: it is presented as data, never as instructions (prompt injection risk).
- External signals are idempotent; a late signal after expiry is logged without changing the decision.

Prior art: Temporal (approval pattern: structured signal, timeout, escalation, idempotency). The gate mechanisms of Prefect, Flyte 2, Galaxy, Dagster, Airflow 3.1 and Argo are compared in the table of §5.

## 5ter. Implementing pause, check and resume

Principle: **an engine is never frozen mid-run.** A pause is a clean stop at a stage boundary. Each relaunch, including a Resume after a failure, is a new `Run` in the same lineage that reuses the engine's cache; each Continue after a gate is a new launch of the same `Run` ([`api-and-data-model.md`](api-and-data-model.md) §5.1, §7 `launches`). *(assumed — pending Thomas, inbox #32)*

### 1. Declare the stages: a manifest next to the pipeline (`spectio.yml`, modelled on `tower.yml`)
```yaml
stages:
  - id: preprocess
    snakemake: { until: [qc_report] }   # rule or target file
    nextflow:  { params: { stage: preprocess } }
    intervention:
      type: parameter_edit               # approval | choice | parameter_edit | external_wait …
      evidence: ["results/qc/*.json", "results/qc/*.png", "results/multiqc.html"]
      params_schema: schema/segmentation.json
      policy: { mode: agent_proposes_human_confirms, timeout: 48h, on_timeout: stop }
  - id: analysis
    snakemake: { until: [] }             # until the end
    nextflow:  { params: { stage: analysis } }
```

**Superseded (27/10/2026).** The `spectio.yml` schema is owned by [`checking-scenarios.md`](checking-scenarios.md) §12: stages are defined by `match` globs, a gate is linked with `stages[].gate`, the policy is the `decide` block and evidence uses the object form. The `snakemake:`, `nextflow:` and `intervention:` keys above are historical. *(assumed — pending Thomas, inbox #29)* **Revised on 25/10/2026 (decision log, UI review round 2):** Nextflow stops at a stage through a generated `ext.when = false` config; pipelines do not cooperate through `params.stage`, so the `nextflow: { params: { stage: … } }` keys are not used ([`checking-scenarios.md`](checking-scenarios.md) §12).

### 2. Platform-side state machine
`QUEUED → RUNNING(stage k) → STAGE_DONE → AWAITING_INTERVENTION → decision →`
- `continue` → `CONTINUE_REQUESTED` → `RUNNING(k+1)`;
- `params_changed` → `RUNNING(k or chosen stage)` with the new parameters;
- `rerun_all` → new run without cache;
- `reject` → `STOPPED`.

`CONTINUE_REQUESTED` holds the resume command until the runner reports that the previous head has left the queue, its process is gone and the engine's lock in the launch directory is free. The same wait applies to every launch into the same directory (Continue, rerun from a stage, a relaunch after a cancel). Why: `onFlowComplete` arrives before the JVM exits and releases its cache lock, and Nextflow then fails with 'Unable to acquire lock on session with ID … You are trying to resume the execution of an already running pipeline' (`cache/DefaultCacheStore.groovy:80-94`, Nextflow `114f1fe`); Snakemake needs `unlock` + `rerun_incomplete` after an abrupt stop (§5ter.5). The exact behaviour of the `.nextflow/cache/<session>` lock and of `.snakemake/locks` is **[to be validated]**. *(assumed — pending Thomas, inbox #28)*

For an unplanned pause ("Pause" button): `PAUSING → PAUSED`, then `resume`.

**Superseded (27/10/2026):** Intervention = Gate. Decisions are `approve`, `apply`, `go_back`, `stop` ([`api-and-data-model.md`](api-and-data-model.md) §7, `decisions`); external signals go to `POST /gates/{id}/signals` (api §5). States superseded by api §7.1 (27/10/2026): the state names above are historical. *(assumed — pending Thomas, inbox #29)*

Leaving a gate to change parameters is a new child run (`stop` with reason `relaunched`, then `:relaunch`); contract in [`api-and-data-model.md`](api-and-data-model.md) §5 and §7.1. *(assumed — pending Thomas, inbox #32)*

### 3. Pause
- **Planned (stage boundary)**:
  - Snakemake launches the stage with `--until …` on the CLI (§2). *(assumed — pending Thomas, inbox #28)*
  - Nextflow launches with the `--stage` parameter, and the pipeline tests `params.stage` in its `workflow` block. Nextflow has no native equivalent to `until`, so **the pipeline must cooperate**. *Revised on 25/10/2026:* Nextflow launches with a generated config that sets `ext.when = false` on the processes of later stages; no pipeline change ([`checking-scenarios.md`](checking-scenarios.md) §12).
- **Unplanned**: Snakemake drains on SIGTERM (it submits nothing new and exits once running jobs finish, `job_scheduler.py:171, 241-245`, Snakemake `1c67a66`); SIGINT cancels running cluster jobs (`job_scheduler.py:398-403`). Nextflow has no drain: SIGTERM or SIGINT aborts the run (`Session.groovy:609-615`, Nextflow `114f1fe`). On SLURM the launcher signals the head job with `scancel --signal=TERM --full <head>`, which reaches the engine without terminating the job (`scancel.1:65-75, 182-184`, Slurm 26.05.5); a plain `scancel` follows SIGTERM with SIGKILL after `KillWait` (default 30 s, `scancel.1:375-379`, `slurm.conf.5:2396-2401`). Finished tasks remain in the cache. *(assumed — pending Thomas, inbox #28)*

### 4. Check
At the end of a stage (last Snakemake `PROGRESS`, Nextflow `onFlowComplete` reported by `nf-spectio`, [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)), the platform:
1. collects the declared evidence (globs) and the QC metrics in JSON;
2. creates the gate ([`api-and-data-model.md`](api-and-data-model.md) §7.1), notifies the UI, the MCP server and the webhooks; *(assumed — pending Thomas, inbox #32)*
3. applies the policy (auto-approval under threshold, timeout, escalation).

### 5. Resume
| Decision | Snakemake | Nextflow |
|---|---|---|
| Continue | same directory, next stage; `.snakemake` avoids redoing finished jobs | same launch directory, `-resume <sessionId>`, without the `ext.when` override |
| Change the parameters and restart from stage X | the runner writes the non-default values to `<launch_dir>/.spectio/config.<n>.yaml` and passes it with `--configfile` after the workflow's own configfile (the later file wins on conflicting keys **[to be validated]**), never `--config`, plus `--forcerun <rule X>`; downstream is invalidated automatically *(assumed — pending Thomas, inbox #40)* | new `-params-file` + `-resume`; only tasks whose hash changes are relaunched. Rerun from a stage uses a generated per-process `ext` key that enters the task hash (checking-scenarios §12) **[to be validated]** in spike T2 |
| Relaunch everything | `forceall` or new directory | without `-resume`, or new directory |
| Resume after failure | `--unlock` only after the "head gone" check (§5ter.2), then `--rerun-incomplete` with the run's `rerun_triggers` *(assumed — pending Thomas, inbox #40)* | `-resume <stored engine_session_id>` with `NXF_VER` set to the stored `engine_version`; refused with a reason if that version is unavailable *(assumed — pending Thomas, inbox #40)* |

Snakemake column revised 27/10/2026: command-line flags, not the Python API (§2) *(assumed — pending Thomas, inbox #28)*. Nextflow column revised 25/10/2026 (log).

Settings to fix:
- Snakemake: explicit `rerun_triggers`; `unlock` + `rerun_incomplete` after an abrupt stop.
- Nextflow: `cleanup = false`; same Nextflow version across stages (25.10, 26.04 and 26.10 each changed task hashes); control parameters such as `stage` must not enter the task hash; `cache 'lenient'` on NFS.

### 6. Launcher
- One supervisor per run, persisted in the database. Snakemake: the `snakemake` command line in the workflow's own environment, launched as a process or as an `sbatch` head job (revised 27/10/2026, §2) *(assumed — pending Thomas, inbox #28)*. Nextflow: `nextflow run` (JVM) launched as a process or as an `sbatch` head job, with the Spectio run ID passed to `nf-spectio` by us (was `TOWER_WORKFLOW_ID`, see [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)). Tracking is always done through events, never by reading the process output.
- The runner holds a mutex per launch directory and never starts a second engine in a directory whose head is still alive (table `launches`, [`api-and-data-model.md`](api-and-data-model.md) §7). *(assumed — pending Thomas, inbox #28)*
- On server restart: heads are adopted or their exit read as in [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1.1 (local) and §3.1 (SLURM, `sacct`). *(assumed — pending Thomas, inbox #35)*
- Short wait (minutes): option of a local wait task that polls the API (section 5bis).

## 6. Results visualisation

- **PNG/JPEG**: WebP thumbnails generated by the pipeline, `loading="lazy"`.
- **PDF**: `pdf.js` in a worker with range loading.
- **HTML (MultiQC, reports)**: `iframe sandbox="allow-scripts"` **without** `allow-same-origin`, ideally from a **separate origin** without cookies, with a strict CSP header on the server side.
- **Tables**: server-side pagination and virtualisation.
- **Imaging**: OME-Zarr (NGFF **0.6** current, 0.5 widely supported; read 0.4 to 0.6). **Viv** (deck.gl components, Zarr v3 since 0.19) for fine-grained channel control, **Vizarr** for speed (iframe `?source=`), Neuroglancer as an "open in" link for 3D. Only one active WebGL viewer at a time; on tablet and mobile, fall back to a thumbnail and an "open on desktop" link.
- **Serving the data**: a small read-only proxy (FastAPI or nginx) that checks the token and an allowed prefix, forbids paths outside the root, and handles `Range` and CORS. S3 presigned URLs only cover a single object, so they are unsuitable for a Zarr.

## 7. Recommended stack

- **Backend**: FastAPI (native SSE since 0.135, 15 s keep-alive, `Last-Event-ID`), shared Pydantic, SQLAlchemy 2, uvicorn with a single worker for the MVP. FastAPI sends `id:` fields, but the application reads `Last-Event-ID` itself to resume (`fastapi/sse.py:236-241`, FastAPI 0.162.0).
- **Frontend**: React + Vite + Mantine 7 (shared with depictio) + TanStack Router and Query. An SSE event updates the cache. Tables become cards below 768 px. The static bundle is served by FastAPI: a single process, no Node in production.
- **Real time**: **SSE** (unidirectional, passes through proxies and SSH tunnels), one stream per browser, shared by its tabs, carrying coalesced deltas per run ([`api-and-data-model.md`](api-and-data-model.md) §8.3) *(assumed — pending Thomas, inbox #28)*.
- **Storage**: **SQLite WAL** for the MVP, Postgres later via `DATABASE_URL` (portable SQLAlchemy Core, Alembic with `render_as_batch`). Require an SQLite with the WAL-reset fix (version rule: [`api-and-data-model.md`](api-and-data-model.md) §7); native backups (SQLite online backup API or `VACUUM INTO`; [`admin-and-operations.md`](admin-and-operations.md) §4.3) *(assumed — pending Thomas, inbox #24)*.
- **Critical constraint**: WAL does not work on NFS/Lustre/GPFS. The file must be on the **local disk** of the service node.

## 7bis. Third-party integration (trigger and track via our API)

High priority: a third-party tool (LIMS, portal, orchestrator, AI agent, script) must be able to launch and track a run without going through the UI.

1. **Native `/api/v1` API**: stable, versioned contract, published OpenAPI, generated Python and TypeScript SDKs. Launch with an **idempotency key** (`Idempotency-Key`) to avoid duplicates on retry. Cursor-based pagination, structured errors.
2. **GA4GH WES 1.1 facade**: `POST /runs` (multipart: `workflow_url`, `workflow_type`, `workflow_params`, `workflow_engine_parameters`, `tags`), `GET /runs`, `/status`, `/tasks`, `/cancel`, `/service-info`. The spec mentions CWL and WDL but allows other types declared by the instance: we will declare Nextflow and Snakemake in `service-info`. Pause, interventions and resume go into extensions.
3. **Outgoing events**: signed webhooks (HMAC) with retry, subscriptions filtered by project and event type; SSE stream for real time. Standard envelope format (CloudEvents, to be decided).
4. **Scoped tokens** (`runs:launch`, `runs:read`, `gates:decide`…) *(assumed — pending Thomas, inbox #29)* per user, service or agent.
5. **MCP** for AI agents (section 5bis), on the same API.
6. **Partial compatibility with the Seqera API** (to reuse `tw` or seqerakit): to be studied later. Public OpenAPI specification, but subject to Seqera's terms of use: legal check first.

## 7quinquies. Spectio as a headless execution layer: plugins in other interfaces, LabID, RO-Crate (25/10)

Goal: Spectio must also work **without its own UI**, as an engine-agnostic layer that other systems use to launch and monitor Nextflow and Snakemake runs (later CWL and WDL). The web UI is one client among others; everything it does goes through the public API (principle of §7bis).

### Headless mode
- `spectio serve --no-ui` (or simply never opening the UI): same server, same runners, same API. Typical callers: LIMS and ELNs (LabID at EMBL), portals, core-facility dashboards, Jupyter, CI, AI agents.
- Stable public resources: `Workflow`, `WorkflowVersion`, `Environment`, `Run`, `Task`, `Gate` / `Intervention`, `Artifact`, `Event`. Each carries **`external_refs`** (e.g. `labid:sample/123`, `labid:dataset/456`, project or order IDs), at run level and per samplesheet row, so the caller can map results back to its own records.
- Launch contract: workflow + version + params file + samplesheet (rows may reference external IDs that the caller resolves to paths, or that a resolver plugin resolves through the runner), environment, optional gates policy; `Idempotency-Key`; response = run ID + links. Everything else (states, tasks, gates, artefacts) is read or subscribed to.

### Surfaces for other interfaces
| Surface | For | Notes |
|---|---|---|
| REST `/api/v1` + OpenAPI, Python / TypeScript SDKs, `spectio` CLI | any system | the reference contract |
| GA4GH **WES 1.1** facade (later **TRS** for the catalogue, **DRS** for artefacts) | standard WES 1.1 clients (workflow portals); strict WES 1.1.0, see [`api-and-data-model.md`](api-and-data-model.md) §10 *(assumed — pending Thomas, inbox #17)* | no gates in WES: exposed as extensions |
| Webhooks (signed, CloudEvents envelope) + SSE stream | systems that react | run state, gate opened / decided, artefact published |
| MCP server | AI agents | same scopes as tokens |
| **Embeddable elements** (web components, iframe fallback) | other web UIs | `<spectio-run-card run=…>`, `<spectio-run-timeline>`, `<spectio-launch-form workflow=… prefill=…>`, `<spectio-review gate=…>`, `<spectio-artifact-viewer>`; scoped short-lived token; events via `postMessage`; themeable with the design tokens |
| Host plugins | specific platforms | thin adapters on the host side (e.g. a LabID plugin) that call the API and embed the elements |

### LabID (EMBL)
What is known (from the RO-Crate project page on LabID): LabID is EMBL Heidelberg's FAIR data-management platform (MODIS group) for samples, datasets, inventory and an ELN; it imports and exports workflows and workflow runs from Galaxy, WorkflowHub and Git using the **Workflow RO-Crate** and **Workflow Run RO-Crate** profiles. Its public API surface is not documented on that page: to confirm with the MODIS team.

Proposed integration, in both directions:
1. **LabID → Spectio**: from a LabID project, select samples / datasets, pick a registered workflow, fill the embedded launch form (or call the API); Spectio receives the samplesheet with LabID IDs in `external_refs`; the runner resolves dataset locations on EMBL storage.
2. **During the run**: LabID shows the embedded run card; gate notifications can be routed to LabID users; review can be done in Spectio or in the embedded review element.
3. **Spectio → LabID**: on completion (or at each gate), Spectio produces a **Workflow Run RO-Crate**; LabID imports it, registers outputs as datasets linked to the input samples, and keeps the provenance, including the review decisions.

### RO-Crate compatibility
- **Import a workflow from a crate**: nf-core requires every pipeline to ship its own RO-Crate (describing the pipeline, not runs); WorkflowHub entries are Workflow RO-Crates. Spectio registers a workflow from such a crate (name, version, repository, licence, inputs).
- **Export every run as a crate**: `GET /api/v1/runs/{id}/ro-crate` (JSON-LD or zip). Target the Workflow Run Crate profile, and the **Provenance Run Crate** when step-level detail is present (per-step `HowToStep` / `ControlAction` entities; Spectio stores tasks; size limits and per-process aggregation: [`api-and-data-model.md`](api-and-data-model.md) §10). The version set is pinned in [`api-and-data-model.md`](api-and-data-model.md) §10: RO-Crate 1.1 + WRROC 0.5, because WRROC 0.6 is not backward compatible. Content: workflow version (repository + commit), engine and version, params file, samplesheet (with `external_refs`), environment and containers / conda environments, inputs and outputs with checksums, timings. Params, samplesheet and environment pass through the redaction of [`admin-and-operations.md`](admin-and-operations.md) §3.4 before export. *(assumed — pending Thomas, inbox #27)*
- **Spectio-specific provenance in the crate**: gates, checks and their results, decisions with their actor (person, AI agent with model, robot), excluded items with reasons, edited samplesheet / parameter / file versions. Encoded as additional actions in the crate so a generic RO-Crate reader still understands the run.
- **Engines**: Nextflow's `nf-prov` plugin can already write a Workflow Run RO-Crate (WRROC, since 1.4.0). Spectio enables it through its generated config and merges its output with the gate provenance. The generated config pins nf-prov by Nextflow version: 1.7.x on 25.10, 1.8.x on 26.10 (nf-prov README at `8aa8280`: "1.8.x · 26.10 | 1.7.x · 25.10 | 1.6.x · 25.10"; `prov.directory` is new in 1.8.0), and the CI matrix covers both ([`dev-environment-and-testing.md`](dev-environment-and-testing.md) §11). For Snakemake, `snakemake-report-plugin-rocrate` (in the `snakemake` GitHub organisation, MIT, commit `1989c5b`, 2026-10-23) is the counterpart of nf-prov: it writes a Provenance Run Crate after a run, declaring RO-Crate 1.1 and WRROC process, workflow and provenance 0.5 (`rocrate_builder.py:294-305`), and it is listed as the Snakemake implementation in `ResearchObject/workflow-run-crate` `docs/index.md:103` (`31518a5`). It is unreleased (version 0.1.0, not on PyPI on 2026-10-26) **[to be validated before relying on it]**. Spectio's own builder, from its event store, therefore stays the primary path. Once the plugin is on PyPI it becomes an optional input: when it is installed Spectio enables it (`--reporter rocrate --report-rocrate-metadata-only`, flag names **[to be validated]**) and merges its output with the gate provenance, under the version rules of [`api-and-data-model.md`](api-and-data-model.md) §10. A second exporter, `snakemake-report-plugin-fairscape` 0.1.0 (PyPI, Apache-2.0, 2026-08-18), writes a FAIRSCAPE EVI RO-Crate, not a WRROC. Sources: [landscape note](../research/landscape-2026-10-26.md) §7. *(assumed — pending Thomas, inbox #28)*
- **Reproduce from a crate**: importing a run crate pre-fills a launch (same workflow version, params, samplesheet). The crate is untrusted input ([`api-and-data-model.md`](api-and-data-model.md) §5). *(assumed — pending Thomas, inbox #25)*

Full design (deployment modes, plugins, endpoint catalogue, identity and tenancy, database schema, events): see [`api-and-data-model.md`](api-and-data-model.md). Plugin contract and packaging (Python bundle, Docker Compose, Helm): see [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md). Administration and operations (users and groups, branding, tasks, logs, health, backups, restore, migrations, maintenance): [`admin-and-operations.md`](admin-and-operations.md). CLI and libraries shared with depictio and LabID: [`cli-and-shared-libraries.md`](cli-and-shared-libraries.md). What is reused from depictio: [`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md). HPC schedulers, Kubernetes and monitoring (pending reasons, accounting, capacity, pre-flight): [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md).

### Phasing
MVP: native API, SDK, webhooks (already planned). Phase 1b: RO-Crate export and import, WES facade. Phase 2: embeddable elements, LabID plugin (after confirming LabID's API with MODIS), TRS / DRS.

Sources: [LabID on researchobject.org](https://www.researchobject.org/ro-crate/labid), [Workflow Run RO-Crate profiles](https://www.researchobject.org/workflow-run-crate/profiles/), [nf-prov](https://www.researchobject.org/ro-crate/nf-prov), [nf-core RO-Crate requirement](https://nf-co.re/docs/guidelines/pipelines/requirements/ro_crate).

## 7quater. Register, launch and track without a terminal (24/10)

Goal: the end user no longer touches the terminal. They register a workflow, launch it on their machine or on a remote cluster, track it, debug it and relaunch it from the interface.

### Two coexisting modes
- **Observed** (Tower/Panoptes model): the user launches from the command line, and the plugin reports the events. Useful for experts, but not sufficient.
- **Driven** (Seqera Launchpad, Sapporo/WES model): the platform does the launching. This is the default mode for the end user.

### Three building blocks
1. **Workflow catalogue.** A workflow is registered once: git URL + revision (pinned to a commit), or a path on the cluster. Spectio reads its description:
   - Nextflow: `nextflow_schema.json` (nf-core convention) → generated form;
   - Snakemake: `config/config.yaml` + `workflow/schemas/config.schema.yaml` (Snakemake workflow catalogue convention) → generated form;
   - optional: `spectio.yml` (stages, interventions, QC evidence, parameter presets).
   Can later be exposed as GA4GH **TRS**, the registry standard (WES has no registry).
2. **Execution environments + runner.** A Spectio **runner** (`spectio runner`, same pip package, a single logical binary) runs on the login node, under the user's account. It opens an **outgoing** connection to the server, so no inbound port on the cluster. It receives orders (launch, cancel, resume, read a log, browse a directory), submits the head job to the scheduler and configures the plugins automatically (`nf-spectio` config, [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md); `spectio` appended to the user's own `--logger` list, [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2). Seqera Platform reaches a cluster over SSH by default ("Seqera requires SSH access to your HPC cluster to run pipelines"), and through Tower Agent where SSH is not allowed; supported schedulers are Slurm, LSF, PBS Pro, Grid Engine and Moab ([Seqera HPC docs](https://docs.seqera.io/platform-cloud/compute-envs/hpc)). That Tower Agent uses an outgoing WebSocket is **[to be validated]**. Spectio's runner follows the Tower Agent principle: an outgoing connection, under the user's account. Locally, server and runner run in the same process (`spectio serve --with-runner`).
3. **Launching from the interface.** Choose the workflow → the environment → fill in the form (sample sheet uploaded or selected via the runner) → Launch. Then: tracking, per-task debugging page (command, stdout/stderr, exit code, working directory files read on demand via the runner), relaunch with a prefilled form, resume, interventions.

### Comparison
Spectio's own modes are the two above (observed and driven). The comparison with other tools (Seqera Platform, nf-shard, panoptes, snkmt, FlowO, Sapporo, Galaxy, Arvados, Flyte 2, Prefect) lives on one page, [Spectio and other tools](../features/other-tools.md), owned by [`documentation-system.md`](documentation-system.md) §1 and refreshed from the dated landscape notes.

Spectio also exposes a strict GA4GH WES 1.1.0 facade ([`api-and-data-model.md`](api-and-data-model.md) §10): a WES client can launch and track runs. Sapporo 2.x compatibility is a non-goal. *(assumed — pending Thomas, inbox #17)*

### The terminal, just once
Install the runner on the cluster: `pip install spectio`, then `spectio runner connect <server> --token …` (token generated in the interface). An administrator can do this for everyone. After that, no more terminal for the user.

## 7ter. Distribution

- **Server = pip-installable Python package** (`pip install`, `uv tool install` or `pixi`), with a `serve` command. The React build is embedded in the wheel; Node is only used in CI. Compiled dependencies (pydantic-core…) are available as manylinux wheels.
- **SQLite**: the uv-managed Python embeds SQLite 3.53.1, tested on 23/10 (compliant). The system Python in this container has SQLite 3.45.1, which is affected by the WAL-reset bug. Possible fallback with the `apsw` wheel (SQLite 3.54.1 embedded). Version check at startup (rule: [`api-and-data-model.md`](api-and-data-model.md) §7).
- **Engine plugins distributed separately**: Snakemake logger plugin = pip package `snakemake-logger-plugin-<name>` in the Snakemake environment; Nextflow companion plugin (Groovy) via the Nextflow plugin registry, downloaded automatically if declared in the config.
- **No PR required** at Snakemake or Nextflow: both engines provide for these extensions. Upstream PRs are **useful but optional**, especially on the Snakemake side: `external_jobid` and `attempt` in events, typed events for temporary file deletion and for DAG updates after a checkpoint, an end-of-workflow event, the executor name. They would reduce text message parsing.

## 8. HPC constraints

- Delivery without root: `uv` or `pixi` environment, or Apptainer image (user namespaces required).
- Host on a **service node** or a dedicated VM rather than on a login node (often forbidden for long-running services). To be validated with the admins.
- Access by listening on `127.0.0.1` and an SSH tunnel, or via the site's reverse proxy (`proxy_buffering off` for SSE).
- **Egress from compute nodes** is often filtered, and a head job runs on a compute node. The bridges therefore write their events to a spool in the launch directory, which the runner forwards from the login node; a direct post is only an optimisation. The runner prepares everything network-dependent (clone, plugins, images, conda environments) on the login node, and the head runs offline (`NXF_OFFLINE=true`). There is no server-side forwarder: the server never mounts storage. See [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13 and [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1. *(assumed — pending Thomas, inbox #28)*
- Restart: state replayed from the database, reconciliation with `sacct` or `squeue`. Launched via `systemd --user` (if `linger` is allowed) or a loop in `tmux`.
- Engine plugins: disk buffer, batched sending, retry with exponential backoff, never block the workflow if the server is unreachable. Hooks only enqueue and never throw; a run never fails because of Spectio (bounds: api §14). *(assumed — pending Thomas, inbox #28)*
- Launching runs (later stage): `sbatch` of a head job rather than `-bg` on the login node. Cancellation: `scancel --signal=TERM --full <head>` (or SIGTERM to a local head), then a plain `scancel` only if the head is still alive after a grace period; any task jobs left behind are cancelled from `scheduler_jobs` (signal semantics: §5ter.3; Slurm 26.05.5 `scancel.1:65-75, 182-184, 375-379`). The sequence is checked on sind in spike T3 **[to be validated in practice]**. *(assumed — pending Thomas, inbox #28)*

## 9. Proposed roadmap

| Phase | Content | Indicative duration |
|---|---|---|
| **0** | Network reachability test on the target cluster, database schema, idempotent ingestion | 2 to 3 weeks |
| **1 (MVP)** | Snakemake engine plugin (logger), run list and detail, SSE, responsive UI, `uv` and Apptainer deployment, one ingestion token | 4 to 6 weeks |
| **1b** | Nextflow engine plugin (`nf-spectio`), `sacct` reconciliation, documented SSH tunnel | |
| **1c** | Stages, checkpoints and decisions: QC gates, relaunch with new parameters, standard viewers | |
| **2** | Users, groups, projects, RBAC, CLI tokens generated from the UI (hashed, scoped, expiring, revocable), OIDC/LDAP, audit log | |
| **3** | Postgres, WES facade, advanced OME-Zarr viewers, notifications, SGE, WDL/CWL | |

Durations come from an agent report and should be taken as orders of magnitude.

**Revised on 26/10/2026 (Thomas):**
- The MVP covers **both engines from the start**: Snakemake through the logger plugin, and Nextflow through `nf-spectio` ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)).
- It focuses on checks and QC: the checks of a stage, the evidence, and the gate (phase 1c above).
- Sending results to depictio comes later.
- The release stages are owned by [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §14.

**Revised on 27/10/2026 (Thomas):** the first version is **0.0.1**, a basic local MVP: one user without sign-in, the engines on the same machine as Spectio (local executor), no SLURM or Kubernetes. It launches, monitors and relaunches runs with changed parameters, keeps the parameter history, and has one simple QC gate. What ships in which version is owned by [`dev-environment-and-testing.md`](dev-environment-and-testing.md#15-what-ships-in-which-version) §15; the phase table above is historical. Summary: [`mvp-0.0.1.md`](mvp-0.0.1.md).

I propose to **start with read-only tracking of both engines**, then add steering (phase 1c). QC gates are what sets the project apart, but they rely on a reliable event log.

## 10. Main risks

1. SQLite WAL on a shared file system: corruption. Enforce local disk and check it at startup.
2. Network access: only the engine's main process needs to reach Spectio (verified for Snakemake and Nextflow), but in the recommended head-job mode that process runs on a compute node, where egress is often filtered. Events therefore go through the launch-directory spool, forwarded by the runner, and the head runs offline after the runner's preparation on the login node ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.1, [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.1). The bridges never fail a run when Spectio is unreachable (architecture §13.3). *(assumed — pending Thomas, inbox #28)*
3. Site policy on long-running services.
4. Unstable engine APIs: `TraceObserverV2` is beta, Snakemake logger fields may change, `-with-weblog` is deprecated (§2). Pin versions, test in CI, version the ingest schema on its own, with a stated compatibility window ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §12). Supported versions, the weekly run against Nextflow `edge`, and what a failing hook does: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.3–§13.4. *(assumed — pending Thomas, inbox #28)*
5. Different granularity between engines (Nextflow process/task, Snakemake jobs and grouped jobs): document the mapping.
6. The `-resume` cache can lead to inconsistent resumes after parameter changes: validate case by case.
7. A single SQLite writer under heavy load: batched inserts, migration to Postgres if needed.

## 11. Open questions

1. Target cluster: SLURM, SGE, Kubernetes? Login node or dedicated machine?
2. Launching: does the interface submit runs, or does it only track those launched from the CLI with the plugin?
3. Imaging: formats (OME-Zarr, OME-TIFF…) and typical sizes?
4. Project name and licence (MIT, Apache, AGPL)? *Answered 26/10/2026: MIT; the public date is not set yet.*
5. Is a WES facade needed from the MVP, or later?

## 12. Main sources

- Nextflow: [plugins](https://docs.seqera.io/nextflow/plugins/developing-plugins), [TraceObserverV2](https://raw.githubusercontent.com/nextflow-io/nextflow/master/modules/nextflow/src/main/groovy/nextflow/trace/TraceObserverV2.groovy), [nf-weblog](https://registry.nextflow.io/plugins/nf-weblog), [cache and resume](https://docs.seqera.io/nextflow/cache-and-resume), [tower config](https://docs.seqera.io/nextflow/reference/config/tower)
- Snakemake: [monitoring](https://snakemake.readthedocs.io/en/stable/executing/monitoring.html), [logger interface](https://github.com/snakemake/snakemake-interface-logger-plugins), [API](https://snakemake-api.readthedocs.io/en/latest/api_reference/snakemake_api.html), [panoptes](https://github.com/panoptes-organization/panoptes), [plugin catalogue](https://snakemake.github.io/snakemake-plugin-catalog/)
- GA4GH: [WES](https://ga4gh.github.io/workflow-execution-service-schemas/docs/), [TES](https://ga4gh.github.io/task-execution-schemas/docs/), [Sapporo](https://github.com/sapporo-wes/sapporo-service/), [nf-shard](https://github.com/AugustDev/nf-shard)
- Viewers: [NGFF](https://ngff.openmicroscopy.org/specifications/index.html), [Viv](https://github.com/hms-dbmi/viv), [Vizarr](https://github.com/hms-dbmi/vizarr), [Neuroglancer](https://github.com/google/neuroglancer), [iframe sandbox (MDN)](https://developer.mozilla.org/en-us/web/html/element/iframe/), [Airflow HITL](https://airflow.apache.org/docs/apache-airflow/3.1.1/tutorial/hitl.html), [Argo suspend](https://argo-workflows.readthedocs.io/en/latest/intermediate-inputs/)
- Architecture: [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/), [SQLite WAL](https://www.sqlite.org/wal.html), [Alembic batch](https://alembic.sqlalchemy.org/en/latest/batch.html), [Apptainer userns](https://apptainer.org/docs/admin/1.5/user_namespace.html), [Slurm REST](https://slurm.schedmd.com/rest.html)
