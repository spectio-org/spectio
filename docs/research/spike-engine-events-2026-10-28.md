# Spike T2 — engine event capture and golden fixtures (2026-10-28)

**Question.**
- Can a minimal Snakemake 9 logger plugin capture every event of the synthetic pipeline, a checkpoint, a failed job and a retry included? **Yes.**
- Does `-with-tower` against a ~50-line capture server deliver the Tower protocol payloads on Nextflow 26.10.x and 25.10.x, with a failed task, a retry and `-resume`? **Yes.**
- Can a first `nf-spectio` (`TraceObserverV2`) be built and run in the time box, next to `nf-tower` in the same run, and do both report the same run ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md))? **Yes:** built without Gradle in minutes; same run name and session ID in **6 of 6** runs, and the same task IDs.
- Does `onTaskComplete` expose `event.handler.task.outputs`, and in which order do `onProcessTerminate` events arrive ([`checking-scenarios.md`](../specs/checking-scenarios.md) §11.1, §11.5)? **Outputs: yes**, on both versions, also in `onTaskCached`. **Order: in dataflow order, and the last `onTaskComplete` of a process arrives *after* that process's `onProcessTerminate`** in every run on both versions.

**Answer in one line.** All three captures work; **24 differences** with the specs, listed [below](#differences-with-the-specs). The ones that change behaviour: end of stage (§11.5), the task status to read in `nf-spectio`, `onFlowError` after `onFlowComplete`, and the Snakemake exit code that is only in error text.

Time box: about 60 minutes of work, met. Nothing was edited in the specs: TRIAGE3 decides.

## Setup

- **Machine.** Claude Code cloud session, Linux 6.18, OpenJDK 21. No Docker: every run used the `local` executor.
- **Engines,** at the pins of `dev/versions.env`, installed as `dev/bootstrap.sh` does (download + `sha256sum -c`; `uv pip sync --require-hashes dev/snakemake.lock.txt`): `spikes/engine-events/install.sh`.
  - Nextflow **26.10.4** and **25.10.9**. `nf-tower` is downloaded from the registry on first use: **1.32.2** for 26.10.4 (its manifest says `Plugin-Requires: >=26.10.2`), **1.17.8** for 25.10.9 (`~/.nextflow/plugins/`).
  - Snakemake **9.27.1**, with `snakemake-interface-logger-plugins` **2.1.0** (the version in the lock file).
- **Pipelines.** `tests/pipelines/synthetic/{snakemake,nextflow}` with the flags of `run_scenarios.py` (`chunks=2`, `--retries 2` on Snakemake, `-profile test,local` on Nextflow).
- **Runs**, the same three on each engine version:

  | Run | Fault | Expected |
  |---|---|---|
  | `flaky` | ALIGN / `align` for S07 fails at attempt 1 (both chunks) | retried, run exit 0; the Snakemake run also crosses the `split` checkpoint |
  | `toolerr` | COMPARE / `compare` for treatA exits 1 | run exit 1; 1 attempt on Nextflow, 3 on Snakemake (T1 finding 2) |
  | `resume` / `rerun` | none, same launch directory | Nextflow `-resume`; Snakemake plain rerun |

  All nine runs ended with the expected exit code (`spikes/engine-events/LOG.md` §2, §3, §5, branch `spike/engine-events` only: of the spike, only `fixtures/` is meant to be integrated).

## What was built (branch `spike/engine-events`, throwaway)

| Piece | Where | Notes |
|---|---|---|
| Snakemake logger plugin `spectio` | `spikes/engine-events/snakemake/snakemake_logger_plugin_spectio/__init__.py` | Subclass of `LogHandlerBase` (`snakemake_interface_logger_plugins/base.py`, v2.1.0): `emit` plus the five abstract properties; `has_filter = True`, `needs_rulegraph = True`. Discovered by the module prefix `snakemake_logger_plugin_` (`common.py`, `registry/__init__.py` of the same package) through `PYTHONPATH`: no install. Writes every `LogRecord` (message plus all `extra=` fields) as one JSON line. |
| Capture server | `spikes/engine-events/capture_server.py` (48 lines, stdlib) | Logs method, path, body, user agent and whether an `Authorization` header was present (not its value). Answers `POST /trace/create` with `{"workflowId": ...}` and everything else with `{}`. |
| `nf-spectio` 0.0.1 | `spikes/engine-events/nextflow/nf-spectio/` | One Groovy file: `SpectioPlugin` (`BasePlugin`), `SpectioFactory` (`TraceObserverFactoryV2`), `SpectioObserver` (`TraceObserverV2`), one JSON `POST` per hook to `$SPECTIO_ENDPOINT`. The interface was read with `javap` from both `-dist` jars: identical method lists. `build.sh` compiles with the Groovy compiler inside the Nextflow jar and writes the unpacked layout of the registry-installed `nf-tower` (`classes/META-INF/MANIFEST.MF`, `extensions.idx`). `-plugins nf-spectio@0.0.1` loads it from `~/.nextflow/plugins` with no registry lookup. The same class files run on 26.10.4 and 25.10.9. |

**Not done (out of the time box):** a Gradle build with the Nextflow plugin Gradle plugin, a signed zip and publication to the registry; batching, retry and a local buffer; the failure modes of the Tower client (an error on `create`, `begin` or `progress`).

## Results

### Snakemake 9.27.1 (logger plugin)

- **Event mix**, flaky run (469 records): `job_info` 69, `shellcmd` 69, `job_finished` 67, `progress` 67, `job_started` 66, `job_error` 2, `error` 2, `resources_info` 2, `workflow_started`, `rulegraph`, `run_info` 1 each, and **122 untyped records** (`event` absent): "Select jobs to execute..." 66, "DAG of jobs will be updated after completion." 12, "Updating checkpoint dependencies." 12, "Removing temporary output ..." (logged **twice** per file), "Trying to restart job N." and log-file paths.
- **Checkpoint.** `run_info` says 32 jobs; `progress.total` then climbs 32 → 33 … 43 (one step per `split` job) → 67. No typed event marks the DAG update; the two text messages come from `jobs.py:1107` and `dag.py:2245` (Snakemake 9.27.1 wheel). `job_info.is_checkpoint` is `true` for the 12 `split` jobs.
- **Retry.** A retried job is re-announced with the **same `jobid`**: `job_started` → `job_info` → `job_error` → text "Trying to restart job 103." (`scheduling/job_scheduler.py:566`) → `job_started` → `job_info` → `job_finished`. No attempt number in any typed field. The synthetic Snakefile happens to expose one through its own `attempt` resource (`job_info.resources.attempt`), which a real workflow will not have.
- **Failure.** `job_error` carries `rule_name`, `jobid`, `input`, `output`, `log`, `shellcmd`, `conda_env`, `container_img`, `aux` (`jobs.py:1129-1142`), **no exit code**. The exit code is only in the text of the matching `error` record: "CalledProcessError ... returned non-zero exit status 1." A fatal run ends with a last `error`: "WorkflowError: At least one job did not complete successfully."
- **Identity.** `workflow_started.workflow_id` is a `uuid.UUID` object (`workflow.py:303`); the rerun gets a new one (`6a5d370a…` → `88d1b16b…`), as T1 found. `workflow_started` also carries `host`, `user`, `cmd`, `cwd`, `rundir` and `platform`.
- **Plugin contract gaps.** With `writes_to_file = True`, Snakemake reads `handler.baseFilename` (`logging.py:661-663`), which `LogHandlerBase` does not declare: the first run crashed with `AttributeError`. `resources` arrives as a `snakemake.io.Namedlist` and loses its names unless converted. The registry reads a settings class named `LogHandlerSettings` (`registry/__init__.py`), while the `settings.py` docstring says `LoggerSettings`. Records reach the handler through a `QueueListener` thread (`logging.py:673-679`), as [`synthesis.md`](../specs/synthesis.md) §2bis says.

### Nextflow, Tower protocol (26.10.4 and 25.10.9)

- **Routes.** Every run: `POST /trace/create`, `PUT /trace/{id}/begin`, 2 to 12 `PUT /trace/{id}/progress`, `PUT /trace/{id}/complete`. The failed 25.10.9 run (`toolerr`) sent `PUT /trace/{id}/complete` **twice**: the Tower counterpart of its double `onFlowComplete` (below). No `/heartbeat` (no run lasted a minute) and no `GET`. User agent `Nextflow/<version>`; the token goes in an `Authorization` header.
- **create** body: `instant`, `projectName`, `repository`, `runName`, `sessionId`, `workflowId` (null without `TOWER_WORKFLOW_ID`). A reply holding only `workflowId` is enough.
- **begin** body: `workflow` (42 keys on 26.10.4, 41 on 25.10.9, which has no `platform`; including `params`, `configText`, `manifest`, `launchDir`, `workDir`, `userName`, `homeDir`, `commandLine`), `processNames`, `towerLaunch` (false), `instant`, and `dag` **on 26.10.4 only**.
- **progress** body: `tasks`, `progress` (with a per-`processes` breakdown), `containers`, `instant`. Task records have 33–53 keys on 26.10.4 and 26–46 on 25.10.9 (fewer on early records), among them `script` (the task command) and `env`. Tasks are sent from `NEW` on: in the shipped fixture `nextflow-26.10.4_tower_flaky.jsonl` (`analyse_tower.py`), the flaky run sent 59 `NEW`, 3 `SUBMITTED`, 8 `RUNNING`, 65 `COMPLETED` and 2 `FAILED` records for 67 task IDs.
- **Retry.** The failed attempt is `FAILED`, `exit` 1, `attempt` 1, `errorAction` `RETRY`; the retry is a new `taskId` with `attempt` 2. `complete.progress`: `failed` 2, `retries` 2, `succeeded` 65.
- **Tool error.** COMPARE treatA `FAILED`, `errorAction` `TERMINATE`. On 26.10.4, FINAL_REPORT stays `NEW` in the last record. On 25.10.9, the last record of COMPARE treatB_vs_ctrl is `ABORTED` and FINAL_REPORT never appears. In both, `complete.workflow.success` false, `errorMessage` "synthetic failure: tool exited with code 1".
- **Resume.** `begin.workflow.resume` true, new run name, same session ID; tasks arrive as `CACHED` (63 on 26.10.4, 62 on 25.10.9: the count depends on timing, as in T1).

### Nextflow, `nf-spectio` next to `nf-tower`

| Version | Run | Run name (both observers) | Session ID (both) | Task IDs Tower / plugin |
|---|---|---|---|---|
| 26.10.4 | flaky | `intergalactic_montalcini` | `d138a5c4-…` | 67 / 67, equal |
| 26.10.4 | toolerr | `soggy_payne` | `38960569-…` | 65 / 65, equal |
| 26.10.4 | resume | `irreverent_yalow` | `38960569-…` | 65 / 65, equal |
| 25.10.9 | flaky | `pedantic_gauss` | `ea241900-…` | 67 / 67, equal |
| 25.10.9 | toolerr | `scruffy_hodgkin` | `ac71c9a0-…` | 64 / 64, equal |
| 25.10.9 | resume | `fervent_mendel` | `ac71c9a0-…` | 65 / 65, equal |

- **Hooks**, flaky run on 26.10.4: `onFlowCreate`, 8 `onProcessCreate`, `onFlowBegin`, 67 each of `onTaskPending`, `onTaskSubmit`, `onTaskStart`, `onTaskComplete`, 8 `onProcessTerminate`, 19 `onFilePublish`, `onFlowComplete`. No `onWorkflowOutput`: the synthetic pipeline uses `publishDir`, not workflow outputs.
- **`event.handler.task.outputs` in `onTaskComplete`** (§11.1): present on both versions, and in `onTaskCached` too. A `Map<OutParam, Object>`: keys print as `fileoutparam<0:1>` or `valueoutparam<0:0>`; a `path` output has **no name** (`name` null), a `val` output has its name (`sample`); values are absolute work-directory paths, a list when the output matches several files. Example, SPLIT S04: `fileoutparam<0:1>` → `[<launch>/work/d5/f05437…/chunks/S04.chunk0000.txt, …chunk0001.txt]`.
- **`onProcessTerminate` order** (§11.5): dataflow order, not declaration order, and not the same from run to run. 26.10.4 flaky: MAKE_READS, QC_STATS, **SPLIT, QC_REPORT**, ALIGN, MERGE, COMPARE, FINAL_REPORT; 26.10.4 toolerr: MAKE_READS, **SPLIT, QC_STATS, ALIGN, QC_REPORT**, MERGE, COMPARE.
- **The last task of a process completes after the process terminates.** In all 6 runs, for 2 to 8 processes per run, one or two `onTaskComplete` events of a process arrived **after** its `onProcessTerminate` (`analyse_plugin.py`, "task events … AFTER its onProcessTerminate"). The plugin posts synchronously and numbers events in arrival order, so this is the order in which Nextflow called the observer. Why: probably the processor terminates on the dataflow thread once its outputs are bound, while the task monitor thread calls `onTaskComplete` **[to be validated in the Nextflow source]**.
- **Failed attempt.** `handler.status` is `COMPLETED` (the handler's lifecycle) while `trace.status` is `FAILED`, with `exitStatus` 1 and `task.errorAction` `RETRY` or `TERMINATE`. On 25.10.9 one `onTaskComplete` came with `handler.status` `RUNNING`.
- **Run failure.** 26.10.4: `onFlowComplete` (success false, exit 1), **then** `onFlowError`. 25.10.9: `onFlowComplete`, `onFlowError`, `onFlowComplete` again: **two** `onFlowComplete`. In both, the `TaskEvent` passed to `onFlowError` has no handler. Processes downstream of the failure never fire `onProcessTerminate` (7 of 8 on 26.10.4, 6 of 8 on 25.10.9), and on 26.10.4 FINAL_REPORT had `onTaskPending` and nothing after.
- **Resume.** Cached tasks fire only `onTaskCached` (no pending, submit or start), with `handler.status` `NEW` and their outputs. `onFilePublish` fires again for every published file of a cached task (19 events in the resume run).
- **`onFilePublish`.** One event per file: `source` in the work directory, `target` under `results/`, `labels` null for `publishDir`.

## Evidence

Fixtures, branch `spike/engine-events`, `spikes/engine-events/fixtures/` (15 files, 2.6 MB: 12 Nextflow, 3 Snakemake):

| Engine | Files |
|---|---|
| Snakemake 9.27.1 | `snakemake-9.27.1_checkpoint_flaky_retry.jsonl`, `snakemake-9.27.1_tool_error.jsonl`, `snakemake-9.27.1_tool_error_rerun.jsonl` |
| Nextflow 26.10.4 | `nextflow-26.10.4_{tower,plugin}_{flaky,toolerr,resume}.jsonl` |
| Nextflow 25.10.9 | `nextflow-25.10.9_{tower,plugin}_{flaky,toolerr,resume}.jsonl` |

- **Normalisation** (`spikes/engine-events/normalise.py`, branch `spike/engine-events` only): the launch directory, the repository root, the scratch directory and `$HOME` become `<launch>`, `<repo>`, `<scratch>`, `<home>`; the Snakemake `platform` string (kernel version) becomes `<platform>` (`--token-key platform`); the host name (whole word) becomes `<host>`, the user name in a path or command becomes `<user>`; the values of `userName`, `user`, `hostname`, `homeDir`, `token` and similar keys become `<redacted>`; the dummy token becomes `<token>` (it never appears: the server logs only that the header was there). Timestamps, IDs and run names are kept: the same-run check needs them. In the plugin fixtures, the trace record is dropped from `onTaskPending`, `onTaskSubmit` and `onTaskStart` (`--slim`, size only: it is repeated on `onTaskComplete`). A grep for the host, user, token, home and scratch paths over the fixtures finds nothing.
- **Summaries:** `analyse_snakemake.py`, `analyse_tower.py`, `analyse_plugin.py` (branch `spike/engine-events` only; the plugin one compares a plugin fixture with the Tower fixture of the same run). Their output is in `LOG.md`.
- **Commands and outputs:** `spikes/engine-events/LOG.md` (branch `spike/engine-events` only).

## Differences with the specs

Compared with [`synthesis.md`](../specs/synthesis.md) §2, §2bis, §2ter and [`checking-scenarios.md`](../specs/checking-scenarios.md) §11.1, §11.5. Rows that matched are not listed (examples: the five Tower routes, the `create` fields, `JOB_FINISHED` with `job_id` only, `--logger` events from the main process, the `QueueListener`, `is_checkpoint`, no attempt number on Snakemake, `attempt` and new `taskId` on a Nextflow retry).

| # | Spec, section | Spec says | Observed | Spec impact |
|---|---|---|---|---|
| 1 | checking-scenarios §11.5 | "End of stage" means every matching process has fired `onProcessTerminate` | The last 1–2 `onTaskComplete` of a process arrive **after** its `onProcessTerminate`, in all 6 runs, both versions | §11.5: end of stage = every matching process terminated **and** every task of those processes has had its `onTaskComplete` (or `onTaskCached`); live checks on the last task must not be skipped |
| 2 | checking-scenarios §11.5 | (silent on failures) | After a fatal error, downstream processes never fire `onProcessTerminate` | §11.5: a stage after a failure never "ends"; the gate logic needs the run's terminal state too |
| 3 | checking-scenarios §11.1 | `event.handler.task.outputs` "holds them" | Present (both versions), also in `onTaskCached`; keys are `OutParam` objects; `path` outputs have **no name**; values are absolute work-dir paths, lists for multi-file outputs | §11.1: match outputs by declared index (`fileoutparam<0:1>`) and glob on the file name, not by an output name; note `onTaskCached` as a second source on resume |
| 4 | checking-scenarios §11.1 | Snakemake `JOB_INFO`: `jobs.py:1028-1045` at `1c67a66` | At v9.27.1 the emission is `Job.log_info`, `jobs.py:1060-1101`; it also carries `reason`, `resources`, `threads`, `priority`, `benchmark`, `shellcmd`, `is_checkpoint`, `is_handover` | §11.1: refresh the citation to the pinned version |
| 5 | synthesis §2 (Nextflow hooks) | Lists `onFlowError` as a hook | `onFlowError` comes **after** `onFlowComplete` (26.10.4), and its `TaskEvent` has no handler | §2 / `nf-spectio` design: do not treat `onFlowComplete` as the last event; wait for observer shutdown or a short drain |
| 6 | synthesis §2 | One `onFlowComplete` per run (implied) | 25.10.9, failed run: `onFlowComplete` **twice**, and the Tower client sent `PUT /trace/{id}/complete` twice in the same run | `nf-spectio` must be idempotent on flow completion (api-and-data-model §8.2 lattice) |
| 7 | synthesis §2ter (Nextflow column, retries) | Status per task from the trace | In `nf-spectio`, `handler.status` is `COMPLETED` on a failed attempt (once `RUNNING` on 25.10.9); the failure is in `trace.status` `FAILED`, `exitStatus`, `task.errorAction` | §2ter / `nf-spectio`: derive the attempt state from the trace record and `errorAction`, never from `handler.status` |
| 8 | synthesis §2ter (Nextflow, resume) | Cached tasks: `onTaskCached` | Cached tasks fire only `onTaskCached` (no pending/submit/start), with outputs; `onFilePublish` fires again for every published file of a cached task | §2ter: a resume republishes; the server must dedupe `onFilePublish` by target (and checks must not re-run on unchanged files) |
| 9 | synthesis §2ter (conditional execution) | A task filtered by `when:` produces no event | Also: on a fatal error a task can get `onTaskPending` and nothing else (FINAL_REPORT, 26.10.4); Tower leaves it `NEW`. On 25.10.9 a running task ends `ABORTED` in Tower (COMPARE treatB_vs_ctrl) and FINAL_REPORT never appears | §2ter: close tasks still pending at flow end (`not_scheduled` or `cancelled`, api-and-data-model §7.2) |
| 10 | synthesis §2bis (begin) | `dag` (new, optional) | Present on 26.10.4, **absent** on 25.10.9 | §2bis: say which versions send it |
| 11 | synthesis §2bis (progress) | Tasks with "all trace record fields" | Includes `script` (the task command) and `env`; tasks are sent from `NEW` on | §2bis note (Tower column only, decision 0001); for `nf-spectio`, decide whether `script` and `env` leave the cluster (secrets in commands) — security-reviewer |
| 12 | synthesis §2bis | `nf-tower` "shipped with Nextflow" | Listed as a core plugin, but **downloaded from the registry on first use** into `~/.nextflow/plugins` (1.32.2 for 26.10.4, 1.17.8 for 25.10.9) | §2bis; matters for offline HPC (and for `nf-spectio`, which needs the same plugin cache) |
| 13 | synthesis §2bis (heartbeat, abort) | `/heartbeat` every minute; an error on create/begin/progress aborts | Not observed: runs under a minute; the server never failed | No change; follow-up 4 |
| 14 | decision 0001 | Running `nf-spectio` next to `nf-tower` is **[to be validated]** | Both observers in one run, 6 of 6 runs, same run name, session ID and task IDs | decision 0001 and synthesis §2bis: drop the mark, cite this note |
| 15 | synthesis §2 (Snakemake events) | `WORKFLOW_STARTED`, `RUN_INFO`, `JOB_INFO`, `JOB_STARTED`, `JOB_FINISHED`, `JOB_ERROR`, `PROGRESS`, `ERROR`, etc. | Also `SHELLCMD`, `RESOURCES_INFO`, `RULEGRAPH` (with `needs_rulegraph`); `LogEvent` has 14 members (`common.py`); and 122 of 469 records have **no event type** | §2: list the 14 members; the plugin keeps untyped records as text |
| 16 | synthesis §2ter (Snakemake, retries) | "Attempt number not sent; same jobid re-emitted after 'Trying to restart job N'" | Confirmed; the restart message is untyped text; `JOB_ERROR` is emitted once per attempt | §2ter: count `JOB_ERROR`s per `jobid` to number attempts (no regex needed) |
| 17 | synthesis §2ter / extended data model (Attempt exit code) | Attempt has an exit code | Snakemake `JOB_ERROR` has **no exit code**; it is only in the `ERROR` record text ("returned non-zero exit status 1") | §2ter: a versioned regex on the `ERROR` text, or the exit code stays unknown on Snakemake; data model: exit code nullable |
| 18 | synthesis §2ter (Snakemake, dynamic DAG) | No "DAG updated" event; the new total appears at the next `PROGRESS` | Confirmed, plus two text messages per checkpoint job ("DAG of jobs will be updated after completion.", "Updating checkpoint dependencies."); total 32 → 67 in 12 steps | §2ter: the text messages can mark "DAG may change" for the "at least N" display |
| 19 | synthesis §2ter (temporary files) | Deletion is a text message "Removing temporary output" | Confirmed (`dag.py:1055`), and each one is logged **twice** | §2ter: dedupe `temp_removed` |
| 20 | synthesis §2ter (Snakemake, executor) | Only `local` (true/false) | Confirmed; `JOB_STARTED` carries `jobs` (job IDs) | No change (groups untested) |
| 21 | synthesis §2bis (Snakemake plugin) | `has_filter = True` to see everything | Also needed: `baseFilename` on any handler with `writes_to_file = True` (`logging.py:661-663`), not in `LogHandlerBase` | §2bis / `cli-and-shared-libraries.md`: plugin contract note |
| 22 | synthesis §2bis (Snakemake plugin) | (silent) | `resources` is a `Namedlist` and `workflow_id` a `uuid.UUID`: naive JSON loses names or fails | §2bis: the plugin serialises defensively ("read defensively" already in §2) |
| 23 | synthesis §2 / security | (silent) | `WORKFLOW_STARTED` carries `host`, `user`, `cmd`, `cwd`; Tower `begin` carries `userName`, `homeDir`, `commandLine`, `configText` | Data-protection note for the ingest gateway (what is stored, what is redacted) — security-reviewer |
| 24 | interface docs | `settings.py` docstring: settings class `LoggerSettings` | The registry reads `LogHandlerSettings` (`registry/__init__.py`, v2.1.0) | None for Spectio; upstream docstring fix |

**Count: 24** (rows 13 and 20 are recorded as "not observed / no change" but kept, because they were in the question).

## What it changes (for TRIAGE3; no spec was edited)

- [`checking-scenarios.md`](../specs/checking-scenarios.md) §11.5 (rows 1, 2) and §11.1 (rows 3, 4).
- [`synthesis.md`](../specs/synthesis.md) §2 (rows 5, 6, 15), §2bis (rows 10–14, 21, 22), §2ter (rows 7–9, 16–20) and the extended data model (row 17).
- [Decision 0001](../decisions/0001-nextflow-through-nf-spectio.md): the coexistence mark can go (row 14).
- [`api-and-data-model.md`](../specs/api-and-data-model.md) §7.2 / §8.2: pending tasks at flow end, a second flow completion, republished files (rows 6, 8, 9).
- Security review of event content (rows 11, 23).

## Follow-ups

1. **Source check** of row 1 (why `onTaskComplete` follows `onProcessTerminate`) in `TaskProcessor` and `TaskPollingMonitor` at v26.10.4 and v25.10.9.
2. **Packaging `nf-spectio`:** Gradle build with the Nextflow plugin Gradle plugin, zip, `Plugin-Requires`, a private plugin index and the registry; offline install on HPC (row 12).
3. **Transport:** batching, retry and a local buffer in `nf-spectio` and the logger (synthesis §2bis), then a run with the capture server down or slow: does `nf-spectio` slow or abort the run? Same question for `nf-tower` (row 13).
4. **Longer runs:** a run over a minute for `/heartbeat`; `fanout_medium` for batch sizes; a Snakemake job group for `GROUP_INFO`; a workflow `output {}` block for `onWorkflowOutput`.
5. **Turn the fixtures into parser tests** once the ingest code exists (`tests/` layout of `dev-environment-and-testing.md` §10), and decide whether 2.6 MB of fixtures go to `main` or are cut down further.
6. **Nextflow 25.04.8**, the floor of the tested range: `TraceObserverV2` was not checked there.

## Open questions

- Should `nf-spectio` send the task `script` and `env` at all (row 11)?
- Is end of stage on Nextflow "all processes terminated and all their tasks completed", or does Spectio wait for a short drain after the last `onProcessTerminate` (row 1)?
