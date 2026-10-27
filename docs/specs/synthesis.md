# Open workflow steering platform (alternative to Seqera Platform): exploration synthesis

Date: 23/10/2026. Based on five parallel explorations (Nextflow, Snakemake, GA4GH and existing projects, viewers and QC, architecture and HPC). Points marked **[to be validated]** could not be confirmed in any source that was read.

## 1. Verdict

**It is feasible, and the niche appears to be open.** Both engines now expose native, structured mechanisms for emitting events (plugins), without parsing logs or going through `subprocess` for tracking. Monitoring is already covered by partial tools. What is missing is **steering**: QC gates, relaunching with new parameters, stage-by-stage execution, all independent of the engine. No project found targets exactly this (non-exhaustive search).

Three decisions shape everything else:

1. **An in-house, engine-independent event log** as the source of truth (append-only). Each engine has its own small agent that writes to it.
2. **Implement the 5 ingestion routes of the Tower protocol on the server side** (revised on 23/10 after reading the code, see section 2bis). The `nf-tower` plugin ships with Nextflow: you just point `tower.endpoint` at our server, with nothing to install, as nf-shard does. The protocol remains undocumented and accepts no commands from the server, so steering goes through our launcher, not through this protocol.
   **Revised on 26/10/2026 ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)):** Nextflow reports only through Spectio's own plugin `nf-spectio`. The Tower routes are not implemented, so a run can report to Seqera Platform (`nf-tower`) and to Spectio at the same time (**[to be validated]** in spike T2).
3. **The QC gate is modelled in our application, not in the engine.** Neither engine has a native pause: the reliable pattern is "stop cleanly after step N, then relaunch with resume".

## 2. Integration per engine (without log parsing)

### Nextflow
- **In-house plugin** based on `TraceObserverV2` (interface marked `@Beta`, verified). Available hooks: `onFlowCreate`, `onFlowBegin`, `onFlowComplete`, `onFlowError`, `onProcessCreate`, `onProcessTerminate`, `onTaskPending`, `onTaskSubmit`, `onTaskStart`, `onTaskComplete`, `onTaskCached`, `onWorkflowOutput`, `onFilePublish`.
- This gives us control over the event schema and the transport (HTTP with retry, or a buffered JSONL file).
- **Quick prototype**: the official `nf-weblog` 1.2.0 plugin (Apache-2.0, Nextflow ≥ 25.10, verified) sends JSON POSTs. According to the reports, `-with-weblog` is deprecated in 26.10 in favour of the plugin **[to be validated]**. Announced events: `started`, `process_submitted`, `process_started`, `process_completed`, `error`, `completed`.
- `nf-tower` (shipped with Nextflow) calls `/trace/create`, `/begin`, `/progress`, `/heartbeat`, `/complete` via `tower.endpoint`. Reimplementing this server would be fragile reverse engineering.
- Plugin distribution: official registry (since 25.10) or a private JSON repository.
- **Points of attention**: the `-resume` cache depends on the launch directory; changing a parameter that feeds into the hash invalidates tasks; in 26.04 the first `-resume` after an upgrade may re-run everything.

### Snakemake
- **Logger plugin** (`snakemake-interface-logger-plugins`, enabled with `--logger <name>`, verified). `--log-handler-script` and `--wms-monitor` have disappeared from the recent CLI (read in the code, not in the docs).
- The handler runs inside the Snakemake process and receives typed `LogRecord`s: `WORKFLOW_STARTED`, `RUN_INFO`, `JOB_INFO`, `JOB_STARTED`, `JOB_FINISHED`, `JOB_ERROR`, `PROGRESS`, `ERROR`, etc. Fields may change between versions: read defensively and pin the version.
- **Clean steering**: one Python worker per run that calls the API (`SnakemakeApi`, `DAGSettings(until=…)`, `ConfigSettings`) rather than a `subprocess` on the CLI. The logger and the working directory are global to the process, hence **one process per run**.
- Existing tools: `panoptes` (HTTP server + dashboard, MIT, plugin 0.3), `snkmt` (SQLite + TUI), `flowo`, `stomp`, `prometheus`. Mature for tracking, nothing for steering.

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
| **SLURM job arrays** | Supported (`--slurm-array-jobs`); the SLURM ID (`123` or `123_4`) reaches the logger **only on error** | `array` directive: one record per child task, `nativeId` = `123_4` on SLURM (other formats for LSF, SGE, PBS, AWS, Google); the parent is never reported | Snakemake: read `.snakemake/incomplete/` or the persistence database, then `sacct --name <run_uuid>`. Nextflow: parse `nativeId` per executor |
| **Retries** | Attempt number not sent; same `jobid` re-emitted after "Trying to restart job N" | `attempt` present; a retry = new `taskId` and new `work` directory; raw `failed` includes retries and ignored tasks | Count attempts in the Snakemake plugin; link Nextflow attempts by process + tag |
| **Executors / backends** | Executor name absent from events; only `local` (true/false) | `executor` per task (per-process override visible), `queue`, `nativeId`, `machineType`/`cloudZone` in the cloud; no hostname or effective partition on HPC | Snakemake: read `--executor` from the command line. HPC: `sacct` from the native ID |
| **Storage** | Visible in paths (`retrieve from storage`, `send to storage`); transfers as text messages; credentials masked | `workDir`, `outputDir`, `workdir` per task; **no published files sent over HTTP** | Snakemake: URI scheme = provider. Nextflow: companion plugin (`onFilePublish`, `onWorkflowOutput`) |
| **Wrappers / modules** | Nothing in events; renamed rule visible (`as M_*`), originating module absent | `process` = qualified name (`NFCORE_RNASEQ:RNASEQ:FASTQC`); nothing on module version or source; the `module` field = Lmod | Snakemake: API (`rule.wrapper`, `script`, `software_env_specs`). Nextflow: companion plugin (`meta.yml`, module registry ≥ 26.04) + `modules.json` on the server side |
| **Software environment** | Absent from events; present in `.snakemake` metadata after execution (`software[]`, hash) | `containers[]` (rich with Wave, otherwise only the image); conda and spack absent; no digest | Snakemake: metadata. Nextflow: companion plugin |
| **Job groups** | `GROUP_INFO` + instance UUID in `JOB_STARTED`: 1 group = 1 scheduler job | Not applicable | n:m model between attempts and scheduler jobs |
| **Measured resources** | Absent; TSV from the `benchmark` directive | `%cpu`, `rss`, durations, etc. in each task | Read the benchmark TSV; `sacct` for efficiency |

### Consequences

1. **Nextflow: hybrid approach.** The Tower protocol covers basic tracking with no installation. A `TraceObserverV2` **companion plugin** is still needed for modules and versions, published files, conda/spack, `storeDir` and tasks filtered out by `when:`. It pushes to an extension route.
   **Revised on 26/10/2026 ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)):** the companion plugin `nf-spectio` becomes the only Nextflow route. The Tower column of the matrix above still shows what the `TowerObserver` sends; it is itself a `TraceObserverV2`, so `nf-spectio` sees the same hooks and more.
2. **Snakemake: three sources.** The logger plugin (with `has_filter = True`), a few text messages turned into typed events (versioned regexes, raw message kept), and a collector that reads `.snakemake` (or the `--persistence-backend db` database) and `sacct`.
3. **Never assume every transition is seen**: Nextflow only sends the latest state per task every second. Upsert per `(run, task_id)`.
4. **Keep the raw JSON** of each event alongside the normalised columns.

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

## 3. Standards and existing projects

| Item | Verdict |
|---|---|
| **GA4GH WES 1.1.0** | A good **facade**: `/runs`, `/runs/{id}/status`, `/tasks`, `cancel`. No pause, no gate, no resume, poor task detail. To be exposed as a thin layer, with extensions for the rest. |
| **GA4GH TES 1.1.0** | Task-centred model. Useful as an execution target later, not as the core. |
| **DRS / TRS** | Periphery: DRS for artefacts, TRS for resolving a workflow. |
| **Sapporo** (DDBJ, Apache-2.0) | The best reference for a multi-engine WES (Nextflow, Snakemake, CWL, Toil, Cromwell). To be studied before deciding what we reimplement. |
| **Arvados, Galaxy, Seqera Platform** | Too monolithic to serve as a base. Arvados for provenance, Galaxy as an example of a minimal WES. |
| **nf-shard** (MIT) | Community `nf-tower`-compatible server. Maturity to be checked. |
| **Cromwell, Toil, Funnel, TESK** | Engines or task servers: future targets for WDL/CWL/TES. |

The internal model could be aligned with **OpenLineage** (lineage, via an optional exporter) and **OpenTelemetry** (traces and metrics), without putting them in the core.

## 4. Engine-agnostic data model (proposal)

- **Run**: engine, workflow, typed parameters, state, dates, `stages`.
- **Task** (Nextflow process / Snakemake rule), **Attempt** (attempt, with retry), **ResourceUsage** (requested and measured), **Artifact** (URI, type, checksum).
- **Event**: `(run_id, seq, event_id ULID, ts, type, payload)`, append-only, uniqueness constraint on `(run_id, event_id)` for idempotent ingestion. The `runs` and `tasks` tables are projections updated in the same transaction. The `seq` also serves as the SSE identifier for resuming after a disconnection.
- **States**: a common subset with WES (11 states), plus internal states: `AWAITING_QC`, `PAUSED`.

## 5. QC gates and stage-by-stage execution

Engine-independent model:
- **Stage**: a logical unit (alignment, segmentation…) linked to a set of tasks.
- **Checkpoint**: placed after a stage, with the QC artefacts to display, a policy (mandatory, auto-approval on threshold, timeout) and a lifecycle `pending → awaiting_review → approved | rejected | params_changed → rerun | continue`.
- **Decision**: author, date, comment, modified parameters, stage to resume from. Append-only audit trail.

The three desired scenarios:
1. **Change the parameters and relaunch everything**: a new run linked to the previous one.
2. **Continue to the end**: relaunch with resume, with no stage limit.
3. **Iterative, in parts 1, 2, 3, 4**: a chain of short, idempotent runs.

An **adapter per engine** translates "stop after N" and "resume from X":
- Snakemake: `until` / `omit_from`, then a new run with the modified config. The `.snakemake` metadata avoids redoing everything. Snakemake `checkpoints` are reserved for data-dependent DAGs.
- Nextflow: `--stage` parameter (or separate workflows) plus `-params-file`, then `-resume` with the session preserved. `-entry` has been deprecated since 24.10. Keep control parameters out of the task hash. A task that waits for approval in a loop would block an executor slot: to be avoided on HPC.
- Prior art: Airflow 3.1 (approval operators), Argo (`suspend`), Prefect 3 (pause with input).

## 5bis. Intervention points: humans, AI agents and external systems (added 23/10)

Goal: the same stopping point can be resolved by a human, by an AI agent, or by an external system (lab robot, instrument, LIMS, script). The pipeline does not need to know who decides.

### The concept: `Intervention` (generalises the Checkpoint)
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
   - authenticated incoming signal (`POST /interventions/{id}/signal`) when the system has finished;
   - **SiLA 2** adapter (lab automation standard, Python library `sila2`) in a later phase.

An agent can also be **called** by the platform: a "reviewer agent" configured per pipeline, which receives the intervention, reads the evidence via MCP and proposes a decision.

### Engine-side mechanics
- **Long wait** (hours, days, a wet-lab step): the pipeline stops after step N (`until` for Snakemake, `--stage` parameter for Nextflow). The platform holds the `AWAITING_INTERVENTION` state, then the launcher relaunches the next stage with the new parameters or new data. Nothing runs during the wait.
- **Short wait** (minutes): option of a **local** wait task (Snakemake `localrule` rule, Nextflow `executor 'local'` process) that polls the API. It does not consume a cluster slot, but keeps the main process alive.
- **External intervention within the flow**: part 1 → `external_action` (the robot prepares, the instrument acquires) → "done" signal with the path to the new data → part 2. This is the generalised "iterative in parts" mode.

### Safeguards for AI
- **Limited-scope** agent tokens: an agent can propose anywhere, but only approves on its own where the policy allows it. Costly or irreversible actions (deletion, large launch) require a human.
- AI decisions are flagged as such, with a justification, and a human can revert them as long as the next stage has not started.
- Artefact content (logs, HTML reports, metadata) is **untrusted** for an agent: it is presented as data, never as instructions (prompt injection risk).
- External signals are idempotent; a late signal after expiry is logged without changing the decision.

Prior art: Temporal (approval pattern: structured signal, timeout, escalation, idempotency), Airflow 3.1 (HITL operators), Argo (`suspend`).

## 5ter. Implementing pause, check and resume

Principle: **an engine is never frozen mid-run.** A pause is a clean stop at a stage boundary. Resuming is a new launch that reuses the engine's cache. Each launch is a `Run` within the same `Lineage`.

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

### 2. Platform-side state machine
`QUEUED → RUNNING(stage k) → STAGE_DONE → AWAITING_INTERVENTION → decision →`
- `continue` → `RUNNING(k+1)`;
- `params_changed` → `RUNNING(k or chosen stage)` with the new parameters;
- `rerun_all` → new run without cache;
- `reject` → `STOPPED`.

For an unplanned pause ("Pause" button): `PAUSING → PAUSED`, then `resume`.

### 3. Pause
- **Planned (stage boundary)**:
  - Snakemake launches the stage with `DAGSettings(until=[…])` via the Python API.
  - Nextflow launches with the `--stage` parameter, and the pipeline tests `params.stage` in its `workflow` block. Nextflow has no native equivalent to `until`, so **the pipeline must cooperate**.
- **Unplanned**: SIGINT to Snakemake (which cancels cluster jobs via `cancel_jobs`), SIGTERM to Nextflow (or `scancel` of the head job). Running tasks are lost; finished ones remain in the cache. No native "finish running tasks without submitting new ones" mode **[to be validated]**.

### 4. Check
At the end of a stage (last Snakemake `PROGRESS`, Nextflow `onFlowComplete` reported by `nf-spectio`, [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)), the platform:
1. collects the declared evidence (globs) and the QC metrics in JSON;
2. creates the `Intervention`, notifies the UI, the MCP server and the webhooks;
3. applies the policy (auto-approval under threshold, timeout, escalation).

### 5. Resume
| Decision | Snakemake | Nextflow |
|---|---|---|
| Continue | same directory, next stage; `.snakemake` avoids redoing finished jobs | same launch directory, `-resume <sessionId>`, next `--stage` |
| Change the parameters and restart from stage X | new config (`ConfigSettings`) + `forcerun=[rule X]`; downstream is invalidated automatically | new `-params-file` + `-resume`; only tasks whose hash changes are relaunched. Forcing a specific stage requires a "salt" parameter read by that process **[to be validated]** |
| Relaunch everything | `forceall` or new directory | without `-resume`, or new directory |

Settings to fix:
- Snakemake: explicit `rerun_triggers`; `unlock` + `rerun_incomplete` after an abrupt stop.
- Nextflow: `cleanup = false`; same Nextflow version across stages (the hash changes in 26.04); control parameters such as `stage` must not enter the task hash; `cache 'lenient'` on NFS.

### 6. Launcher
- One supervisor per run, persisted in the database. Snakemake: a Python worker process that calls the API. Nextflow: `nextflow run` (JVM) launched as a process or as an `sbatch` head job, with the Spectio run ID passed to `nf-spectio` by us (was `TOWER_WORKFLOW_ID`, see [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)). Tracking is always done through events, never by reading the process output.
- On server restart: reconciliation with the database, PIDs and `sacct`.
- Short wait (minutes): option of a local wait task that polls the API (section 5bis).

## 6. Results visualisation

- **PNG/JPEG**: WebP thumbnails generated by the pipeline, `loading="lazy"`.
- **PDF**: `pdf.js` in a worker with range loading.
- **HTML (MultiQC, reports)**: `iframe sandbox="allow-scripts"` **without** `allow-same-origin`, ideally from a **separate origin** without cookies, with a strict CSP header on the server side.
- **Tables**: server-side pagination and virtualisation.
- **Imaging**: OME-Zarr (NGFF **0.6** current, 0.5 widely supported; read 0.4 to 0.6). **Viv** (deck.gl components, Zarr v3 since 0.19) for fine-grained channel control, **Vizarr** for speed (iframe `?source=`), Neuroglancer as an "open in" link for 3D. Only one active WebGL viewer at a time; on tablet and mobile, fall back to a thumbnail and an "open on desktop" link.
- **Serving the data**: a small read-only proxy (FastAPI or nginx) that checks the token and an allowed prefix, forbids paths outside the root, and handles `Range` and CORS. S3 presigned URLs only cover a single object, so they are unsuitable for a Zarr.

## 7. Recommended stack

- **Backend**: FastAPI (native SSE since 0.135, 15 s keep-alive, `Last-Event-ID`), shared Pydantic, SQLAlchemy 2, uvicorn with a single worker for the MVP.
- **Frontend**: React + Vite + Mantine 7 (shared with depictio) + TanStack Router and Query. An SSE event updates the cache. Tables become cards below 768 px. The static bundle is served by FastAPI: a single process, no Node in production.
- **Real time**: **SSE** (unidirectional, passes through proxies and SSH tunnels), one multiplexed stream per tab.
- **Storage**: **SQLite WAL** for the MVP, Postgres later via `DATABASE_URL` (portable SQLAlchemy Core, Alembic with `render_as_batch`). Require SQLite ≥ 3.51.3 (WAL-reset bug fix); backup via `VACUUM INTO`.
- **Critical constraint**: WAL does not work on NFS/Lustre/GPFS. The file must be on the **local disk** of the service node.

## 7bis. Third-party integration (trigger and track via our API)

High priority: a third-party tool (LIMS, portal, orchestrator, AI agent, script) must be able to launch and track a run without going through the UI.

1. **Native `/api/v1` API**: stable, versioned contract, published OpenAPI, generated Python and TypeScript SDKs. Launch with an **idempotency key** (`Idempotency-Key`) to avoid duplicates on retry. Cursor-based pagination, structured errors.
2. **GA4GH WES 1.1 facade**: `POST /runs` (multipart: `workflow_url`, `workflow_type`, `workflow_params`, `workflow_engine_parameters`, `tags`), `GET /runs`, `/status`, `/tasks`, `/cancel`, `/service-info`. The spec mentions CWL and WDL but allows other types declared by the instance: we will declare Nextflow and Snakemake in `service-info`. Pause, interventions and resume go into extensions.
3. **Outgoing events**: signed webhooks (HMAC) with retry, subscriptions filtered by project and event type; SSE stream for real time. Standard envelope format (CloudEvents, to be decided).
4. **Scoped tokens** (`runs:launch`, `runs:read`, `interventions:resolve`…) per user, service or agent.
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
| GA4GH **WES 1.1** facade (later **TRS** for the catalogue, **DRS** for artefacts) | standard clients (Sapporo-style, workflow portals) | no gates in WES: exposed as extensions |
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
- **Export every run as a crate**: `GET /api/v1/runs/{id}/ro-crate` (JSON-LD or zip). Target the Workflow Run Crate profile, and the **Provenance Run Crate** when step-level detail is available (it is: Spectio stores tasks). Content: workflow version (repository + commit), engine and version, params file, samplesheet (with `external_refs`), environment and containers / conda environments, inputs and outputs with checksums, timings.
- **Spectio-specific provenance in the crate**: gates, checks and their results, decisions with their actor (person, AI agent with model, robot), excluded items with reasons, edited samplesheet / parameter / file versions. Encoded as additional actions in the crate so a generic RO-Crate reader still understands the run.
- **Engines**: Nextflow's `nf-prov` plugin can already write a Workflow Run RO-Crate (WRROC, since 1.4.0); Spectio can enable it through its generated config and merge its output with the gate provenance. For Snakemake no native exporter was found, so Spectio builds the crate from its own event store.
- **Reproduce from a crate**: importing a run crate pre-fills a launch (same workflow version, params, samplesheet).

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
2. **Execution environments + runner.** A Spectio **runner** (`spectio runner`, same pip package, a single logical binary) runs on the login node, under the user's account. It opens an **outgoing** connection to the server, so no inbound port on the cluster. It receives orders (launch, cancel, resume, read a log, browse a directory), submits the head job to the scheduler and configures the plugins automatically (`nf-spectio` config, `--logger`; [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)). This is the same principle as Seqera's Tower Agent (outgoing WebSocket, user's account, Slurm/LSF/PBS/SGE). Locally, server and agent run in the same process (`perspectio serve`).
3. **Launching from the interface.** Choose the workflow → the environment → fill in the form (sample sheet uploaded or selected via the agent) → Launch. Then: tracking, per-task debugging page (command, stdout/stderr, exit code, working directory files read on demand via the agent), relaunch with a prefilled form, resume, interventions.

### Comparison
| | Registration | Remote launch | Tracking | Steering (pause, QC, relaunch) |
|---|---|---|---|---|
| Tower / Panoptes (plugin mode) | none | no (terminal) | yes | no |
| Seqera Platform | Launchpad | yes, Tower Agent | rich | relaunch, no interventions |
| Sapporo (WES) | list of executable workflows in the config | `POST /runs`, engines in Docker containers; HPC schedulers not mentioned | run state, logs | cancellation |
| **Spectio** | catalogue + generated forms | outgoing agent, local or cluster | rich (events) | pause, interventions, relaunch, resume |

Spectio also exposes the WES facade: a Sapporo or WES client can launch and track runs.

### The terminal, just once
Install the runner on the cluster: `pip install spectio`, then `spectio runner connect <token>` (token generated in the interface). An administrator can do this for everyone. After that, no more terminal for the user.

## 7ter. Distribution

- **Server = pip-installable Python package** (`pip install`, `uv tool install` or `pixi`), with a `serve` command. The React build is embedded in the wheel; Node is only used in CI. Compiled dependencies (pydantic-core…) are available as manylinux wheels.
- **SQLite**: the uv-managed Python embeds SQLite 3.53.1, tested on 23/10 (compliant). The system Python in this container has SQLite 3.45.1, which is affected by the WAL-reset bug. Possible fallback with the `apsw` wheel (SQLite 3.54.1 embedded). Version check at startup.
- **Engine plugins distributed separately**: Snakemake logger plugin = pip package `snakemake-logger-plugin-<name>` in the Snakemake environment; Nextflow companion plugin (Groovy) via the Nextflow plugin registry, downloaded automatically if declared in the config.
- **No PR required** at Snakemake or Nextflow: both engines provide for these extensions. Upstream PRs are **useful but optional**, especially on the Snakemake side: `external_jobid` and `attempt` in events, typed events for temporary file deletion and for DAG updates after a checkpoint, an end-of-workflow event, the executor name. They would reduce text message parsing.

## 8. HPC constraints

- Delivery without root: `uv` or `pixi` environment, or Apptainer image (user namespaces required).
- Host on a **service node** or a dedicated VM rather than on a login node (often forbidden for long-running services). To be validated with the admins.
- Access by listening on `127.0.0.1` and an SSH tunnel, or via the site's reverse proxy (`proxy_buffering off` for SSE).
- **Egress from compute nodes** is often filtered: test early. Fallback: the agent writes JSONL to the shared file system, and a server-side forwarder reads it.
- Restart: state replayed from the database, reconciliation with `sacct` or `squeue`. Launched via `systemd --user` (if `linger` is allowed) or a loop in `tmux`.
- Agents: disk buffer, batched sending, retry with exponential backoff, never block the workflow if the server is unreachable.
- Launching runs (later stage): `sbatch` of a head job rather than `-bg` on the login node. Cancellation: `scancel` or SIGTERM **[to be validated in practice]**.

## 9. Proposed roadmap

| Phase | Content | Indicative duration |
|---|---|---|
| **0** | Network reachability test on the target cluster, database schema, idempotent ingestion | 2 to 3 weeks |
| **1 (MVP)** | Snakemake agent, run list and detail, SSE, responsive UI, `uv` and Apptainer deployment, one ingestion token | 4 to 6 weeks |
| **1b** | Nextflow agent (V2 plugin), `sacct` reconciliation, documented SSH tunnel | |
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
2. Network access: only the engine's main process needs to reach the server (verified for Snakemake and Nextflow). The risk therefore concerns the node where that process runs (login node or `sbatch` head job), not the compute nodes. Keep the spool fallback. On the Nextflow side, a server outage during `create`, `begin` or `progress` aborts the run.
3. Site policy on long-running services.
4. Unstable engine APIs: `TraceObserverV2` is beta, Snakemake logger fields may change, `-with-weblog` is deprecated. Pin versions, test in CI, version the event schema.
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
