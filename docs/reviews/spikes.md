# Spikes round (W3) — differences found by T2, T3, T4, T7

**Round:** spikes (TRIAGE3) · **Date:** 2026-10-28 · **Found by:** the W3 steps T2, T3, T4 and T7, their spikes and their code reviews · **Status of the round:** triaged on 2026-10-28; the orchestrator re-ran the checks of every accepted finding.

**Applied:** [APPLY3](../progress/W3/APPLY3.md) (2026-10-28): 44 applied (42 by APPLY3, 2 by PR #36), 5 partly applied, 0 not applied. Not for APPLY3: 8 rejected, 9 waiting for Thomas (reserved), 3 applied by T3.

**What this round is.** The W3 steps measured real engines and clusters. Their Progress pages and research notes list where the specs disagree with what was measured, without editing the specs. This file turns each difference into one finding and proposes a triage under [`triage-policy.md`](../playbooks/triage-policy.md). Specs are not edited here.

**Sources.**
- **T2:** [Progress page](../progress/W3/T2.md) (24 differences, 2 open questions) and the [research note](../research/spike-engine-events-2026-10-28.md), "Differences with the specs" and "What it changes". Fixtures: branch `spike/engine-events`, `spikes/engine-events/fixtures/`.
- **T3:** the T3 worktree (`autopilot/T3`, head `41428f5`): [Progress page](../progress/W3/T3.md) (16 differences, 2 open questions), the [spike t3-ci note](../research/spike-t3-ci-2026-10-28.md) and the [review record](code/T3.md). Fixtures: `tests/fixtures/slurm/slurm-26.05.5/`.
- **T4:** [Progress page](../progress/W3/T4.md) ("Findings and open questions", "Inputs for TRIAGE3 from the security review"), the [review record](code/T4.md) (SEC-T4-03, SEC-T4-05) and the [spike t4-ci note](../research/spike-t4-ci-2026-10-28.md). Fixtures: `tests/fixtures/k8s/`.
- **T7:** [Progress page](../progress/W3/T7.md), the [review record](code/T7.md) and the [corpus note](../research/corpus-ci-2026-10-27.md).

**How the evidence was checked.**
- The T2 facts were re-read from the committed fixtures with [`tools/triage/check_t2.py`](https://github.com/weber8thomas/spectio/blob/main/tools/triage/check_t2.py) (`python3 -I tools/triage/check_t2.py all`; the `check_t2.py <check>` names below are its blocks); every one reproduced.
- The Snakemake line numbers were re-read in the Snakemake 9.27.1 wheel and `snakemake-interface-logger-plugins` 2.1.0 that `dev/bootstrap.sh` installs.
- The T4 facts were re-read in `tests/fixtures/k8s/`, `tests/k8s/rbac.yaml`, and the logs of spike runs 40662141233 and 40663207755 (`gh run view --log`).
- The Kueue v0.20.3 `manifests.yaml` was downloaded and its sha256 matched `KUEUE_MANIFEST_SHA256`. That re-check found one wrong claim in the T4 note (SPK-T4-17).
- The T3 facts were re-read from `tests/fixtures/slurm/slurm-26.05.5/` with [`tools/triage/check_t3.py`](https://github.com/weber8thomas/spectio/blob/main/tools/triage/check_t3.py) (`python3 -I tools/triage/check_t3.py tests/fixtures/slurm/slurm-26.05.5`), and from the job logs of run 40680736055 and spike runs 40667769713 and 40670286528.
- **Repository visibility:** public on 2026-10-28 (`gh api repos/weber8thomas/spectio`: `"visibility":"public"`). This matters for SPK-T7-02.

**Not counted as differences:** the steps' follow-ups that change no spec. For T2: a Gradle build and registry publication of `nf-spectio`, transport with the server down, `/heartbeat`, Nextflow 25.04.8, and whether 2.6 MB of fixtures go to `main`. For T4: the CPU-limit default.

**ID scheme.** `SPK-<step>-nn`. A security finding keeps its original ID in brackets.

## T2

### SPK-T2-01 · major · End of stage on Nextflow: the last `onTaskComplete` arrives after `onProcessTerminate`

- **Where:** checking-scenarios.md §11.5 (Order): "\"End of stage\" means every process matching the stage's `match` globs has fired `onProcessTerminate` (`TraceObserverV2.groovy:63-69`, fired from `TaskProcessor.terminateProcess` at `:2003-2006`, nextflow `114f1fe`)."
- **Evidence:** in all 6 plugin runs, on both 26.10.4 and 25.10.9, 1–2 `onTaskComplete` of 2–8 processes came after that process's `onProcessTerminate`. For example, 26.10.4 flaky: QC_STATS 1, ALIGN 1, MERGE 1, COMPARE 2 ([T2 note](../research/spike-engine-events-2026-10-28.md#differences-with-the-specs), row 1; `check_t2.py after_terminate`). The cause is probably the dataflow thread against the task-monitor thread **[to be validated in the Nextflow source]** (note, follow-up 1).
- **Problem:** a `stage_done` watch or a gate fires before the stage's last task has finished, so its last outputs are missed.
- **Proposal:** §11.5 Order: "End of stage" means every matching process has fired `onProcessTerminate` **and** every task of those processes that `nf-spectio` has seen (from `onTaskPending` on) has had its `onTaskComplete` or `onTaskCached`. Cite the T2 note. This answers T2's open question: a deterministic rule, not a timed drain.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by the 6 plugin fixtures, `check_t2.py after_terminate`; local fix in checking-scenarios §11.5) → applied (APPLY3, 2026-10-28): checking-scenarios §11.5

### SPK-T2-02 · minor · A stage after a fatal error never ends

- **Where:** checking-scenarios.md §11.5 (Order, as quoted in SPK-T2-01). It says nothing about failures.
- **Evidence:** after a fatal error, the processes downstream of the failure never fire `onProcessTerminate`. 26.10.4 toolerr: 7 of 8 terminate (FINAL_REPORT never does). 25.10.9 toolerr: 6 of 8 (COMPARE and FINAL_REPORT never do). Source: `check_t2.py downstream_terminate`, note row 2.
- **Problem:** without a rule, a stage stays `running` after the run has failed, and a `stage_done` watch waits forever.
- **Proposal:** a new bullet in §11.5. When the run reaches a terminal state, every stage that has not ended is closed with that terminal state, `failed` or `skipped` (the `run_stages.state` values of [api §7](../specs/api-and-data-model.md), linked). Its `stage_done` watches do not fire.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py downstream_terminate`; local fix in checking-scenarios §11.5) → applied (APPLY3, 2026-10-28): checking-scenarios §11.5

### SPK-T2-03 · minor · Task outputs: keys are `OutParam` objects, and `path` outputs have no name

- **Where:** checking-scenarios.md §11.1, row `onTaskComplete(TaskEvent)`: "…so `event.handler.task.outputs` holds them."
- **Evidence:** the outputs are present on both versions, in `onTaskComplete` and also in `onTaskCached`. The map's keys print as `fileoutparam<0:1>` and `valueoutparam<0:0>`. A `path` output has `name` null; a `val` output keeps its name (`sample`). The values are absolute work-directory paths, as a list when the output matches several files. Example, SPLIT S04 on 26.10.4: two chunk paths. Source: `check_t2.py outputs`, note row 3.
- **Problem:** a matcher that keys on the output name finds nothing for files.
- **Proposal:** add to §11.1, under the table: watched files are matched by output index and a glob on the file name, never by output name. On a resume, `onTaskCached` carries the same outputs.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py outputs`; local fix in checking-scenarios §11.1) → applied (APPLY3, 2026-10-28): checking-scenarios §11.1

### SPK-T2-04 · minor · Snakemake `JOB_INFO` citation is at an old commit

- **Where:** checking-scenarios.md §11.1, row `JOB_INFO`: "snakemake `1c67a66` (2026-10-19), `src/snakemake/jobs.py:1028-1045`".
- **Evidence:** at the pinned 9.27.1 the record is built by `Job.log_info` at `jobs.py:1060` onwards. It also carries `reason`, `resources`, `threads`, `priority`, `benchmark`, `shellcmd`, `is_checkpoint` and `is_handover` (note row 4; re-read in the 9.27.1 wheel).
- **Problem:** the citation points to another version than the one tested.
- **Proposal:** in §11.1, cite `jobs.py:1060-1101` at v9.27.1 and add the extra fields.
- **Found by:** T2 spike
- **Status:** accepted (auto: fact correction backed by the code at v9.27.1; local fix in checking-scenarios §11.1) → applied (APPLY3, 2026-10-28): checking-scenarios §11.1

### SPK-T2-05 · minor · `onFlowError` arrives after `onFlowComplete`

- **Where:** architecture-plugins-and-packaging.md §13.3: "Hooks only enqueue; a sender thread batches and sends (§13.2)". It does not say when the sender may stop. synthesis.md §2 lists `onFlowError` with no order.
- **Evidence:** 26.10.4 toolerr sends `onFlowComplete` (success false, exit 1), then `onFlowError`. 25.10.9 toolerr sends `onFlowComplete`, `onFlowError`, `onFlowComplete`. The `TaskEvent` of `onFlowError` has no handler. Source: `check_t2.py flow_end`, note row 5.
- **Problem:** a bridge that flushes and stops at `onFlowComplete` loses the events that follow it.
- **Proposal:** add to §13.3: the sender flushes and stops at observer shutdown, not at `onFlowComplete`. Events after `onFlowComplete` (`onFlowError`, a second `onFlowComplete`) are sent like any other. synthesis §2 links to it.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py flow_end`; local fix in architecture §13.3) → applied (APPLY3, 2026-10-28): architecture §13.3

### SPK-T2-06 · minor · Two `onFlowComplete` in one failed run (25.10.9)

- **Where:** api-and-data-model.md §8.2: "**State lattice.** Projections never move a terminal state back. The run lattice applies per run; launch outcomes live on `launches`;"
- **Evidence:** in the 25.10.9 toolerr run, `onFlowComplete` arrives twice and the Tower client sends `PUT /trace/{id}/complete` twice. 26.10.4 sends it once. Source: `check_t2.py flow_end`, note row 6.
- **Problem:** without a stated rule, the projector could emit `spectio.run.failed` twice, or overwrite `launches.exited_at`.
- **Proposal:** add one sentence to §8.2: a repeated engine flow-completion for the same launch is logged but changes nothing (the first one sets `head_state` and `exited_at`). Cite 25.10.9.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py flow_end`; local fix in api §8.2) → applied (APPLY3, 2026-10-28): api §8.2

### SPK-T2-07 · major · Nextflow attempt state: read the trace record, never `handler.status`

- **Where:** api-and-data-model.md §7.2: "Engine mapping: Nextflow trace status `NEW` / `SUBMITTED` / `RUNNING` / `COMPLETED` / `FAILED` / `CACHED` / `ABORTED` and Snakemake job events map to these values **[to be validated]** (spike T2)." Related: [R6 SR-083](R6-contract.md) ("engine mapping checked in spike T2").
- **Evidence:** in `onTaskComplete` of a failed attempt, `handler.status` is `COMPLETED`, while `trace.status` is `FAILED`, `exitStatus` is 1 and `errorAction` is `RETRY` or `TERMINATE`, on both versions. Once, on 25.10.9, `handler.status` is `RUNNING` while `trace.status` is `ABORTED`. Source: `check_t2.py failed_status`, note row 7.
- **Problem:** a bridge or projector that reads `handler.status` records failed attempts as succeeded.
- **Proposal:** §7.2 Engine mapping, Nextflow part:
  - hooks `onTaskPending`, `onTaskSubmit` and `onTaskStart` give `pending`, `submitted` and `running`;
  - `onTaskComplete` gives the state from `trace.status`: `COMPLETED` → `succeeded`, `FAILED` → `failed`, with `ignored` when `errorAction` is `IGNORE`;
  - `onTaskCached` gives `cached`;
  - `handler.status` is never read.
  - Drop the mark for Nextflow and keep it for Snakemake. `ABORTED` follows SPK-T2-09.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py failed_status`; local fix in api §7.2) → applied (APPLY3, 2026-10-28): api §7.2

### SPK-T2-08 · minor · A resume republishes every cached file

- **Where:** checking-scenarios.md §11.4: "A gate at the end of the same stage reuses a result when the file hash has not changed, so the numbers seen during the run and at the gate are the same." It says nothing about a resume.
- **Evidence:** in a resume, cached tasks fire only `onTaskCached` (63 on 26.10.4, 62 on 25.10.9). `onFilePublish` fires again for every published file of a cached task: 19 events, the same count as the first run. Source: `check_t2.py resume`, note row 8.
- **Problem:** every watched file is evaluated again on each resume, at the cost of one file read each (§11.5 Cost).
- **Proposal:** in §11.4, extend the reuse rule to live checks. A published file whose target path and hash match a stored result is not evaluated again: in the same run, or in the parent run when the run is a resume (child-run model of api §5.1, *assumed — pending Thomas, inbox #32*).
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py resume`; local fix in checking-scenarios §11.4) → applied (APPLY3, 2026-10-28): checking-scenarios §11.4 (assumed — pending Thomas, inbox #32)

### SPK-T2-09 · major · Tasks left open when the run ends

- **Where:** api-and-data-model.md §7.2: "`attempts.state` ∈ {`pending`, `submitted`, `running`, `succeeded`, `failed`, `cached`, `stored`}" and "`tasks.state` is the state of its last attempt, or `not_scheduled` when the engine planned the task but never created an attempt." ui-spec.md §3.1 lists the task labels.
- **Evidence:**
  - 26.10.4 toolerr: FINAL_REPORT gets `onTaskPending` and nothing after, and Tower leaves it `NEW`.
  - 25.10.9 toolerr: COMPARE treatB_vs_ctrl ends `ABORTED` in Tower and in the plugin's trace, and FINAL_REPORT never appears.
  - Source: `check_t2.py pending_only` and `failed_status`, note row 9.
- **Problem:** §7.2 has no terminal state for an attempt that the engine stops because of another failure. The attempt stays `pending` or `running` forever, and `ABORTED` has no mapping.
- **Proposal:** see [proposed inbox #56](inbox.md#56-assumed-the-state-of-a-task-still-open-when-the-run-ends). The recommendation is a terminal attempt state `aborted` in §7.2, with its label in ui-spec §3.1. At flow end the projector moves every open attempt to `aborted`; a task with no attempt stays `not_scheduled`.
- **Found by:** T2 spike
- **Status:** inbox (assumed: (a) a terminal attempt state `aborted`). The fix is not local: it adds a state to api §7.2 and a label to ui-spec §3.1. → applied (APPLY3, 2026-10-28): api §7.2; ui-spec §3.1 (assumed — pending Thomas, inbox #56)

### SPK-T2-10 · minor · Tower `begin` carries `dag` on 26.10 only

- **Where:** synthesis.md §2bis, `onFlowBegin` row: "`workflow` (full metadata, `params`, `configText`, manifest…), `processNames`, `towerLaunch`, `dag` (new, optional)".
- **Evidence:** `dag` is present in `begin` on 26.10.4 and absent on 25.10.9. The `workflow` object has 42 keys on 26.10.4 and 41 on 25.10.9, which has no `platform`. Source: `check_t2.py tower_begin_and_tasks`, note row 10.
- **Problem:** the table does not say which versions send `dag`. This is minor because the Tower route is not used ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)).
- **Proposal:** in the §2bis row: "`dag` (26.10 only; absent on 25.10.9, T2)".
- **Found by:** T2 spike
- **Status:** accepted (auto: fact correction backed by the fixtures; local fix in synthesis §2bis) → applied (APPLY3, 2026-10-28): synthesis §2bis

### SPK-T2-11 · major · Task `script` and `env` in engine events

- **Where:** architecture-plugins-and-packaging.md §13.5: "`nf-spectio` sends `script` and `env` at most once per task, or never (the runner reads `.command.sh` on demand)" *(assumed — pending Thomas, inbox #28)*. api §8.4 already says that "`env` may contain secrets".
- **Evidence:** the Tower client sends `script` (the task command) and `env` in every task record of `progress`, from `NEW` on, on both versions (`check_t2.py tower_begin_and_tasks`, note row 11). T2's open question: "Should `nf-spectio` send the task `script` and `env` at all?"
- **Problem:** §13.5 leaves two options open. Commands and environments can hold secrets, and in 0.0.1 they would be stored in SQLite on a shared login node.
- **Proposal:** see [proposed inbox #55](inbox.md#55-what-engine-events-may-carry-task-script-and-env-user-host-and-command-line).
- **Found by:** T2 spike
- **Status:** inbox (reserved: security posture defaults)

### SPK-T2-12 · minor · `nf-tower` is not shipped with Nextflow; it is downloaded on first use

- **Where:** synthesis.md §2: "`nf-tower` (shipped with Nextflow) calls `/trace/create`…"; synthesis.md §1, item 2: "The `nf-tower` plugin ships with Nextflow".
- **Evidence:** `nf-tower` is listed as a core plugin, but it is downloaded from the registry into `~/.nextflow/plugins` on first use: 1.32.2 for 26.10.4 (manifest `Plugin-Requires: >=26.10.2`), 1.17.8 for 25.10.9 (note, Setup and row 12).
- **Problem:** an offline login node cannot run `-with-tower`. Spectio users who also report to Seqera Platform hit this.
- **Proposal:** in synthesis §2 and §1 item 2, "a core plugin, downloaded from the plugin registry on first use (T2)". How Spectio's own plugin gets there offline is SPK-T2-25.
- **Found by:** T2 spike
- **Status:** accepted (auto: fact correction backed by the plugin cache and its manifest; local fix in synthesis §1 and §2) → applied (APPLY3, 2026-10-28): synthesis §1 and §2

### SPK-T2-13 · minor · `/heartbeat` and the abort on server errors were not observed

- **Where:** synthesis.md §2bis: "`PUT /trace/{id}/heartbeat` | `progress`, every **1 min** when there is no activity" and "An error on `create`, `begin` or `progress` **aborts the run**".
- **Evidence:** no run lasted a minute and the capture server never failed (note row 13, follow-ups 3 and 4).
- **Problem:** none shown; the spec is neither confirmed nor contradicted.
- **Proposal:** none; it stays a follow-up of the T2 note.
- **Found by:** T2 spike
- **Status:** rejected (cannot be reproduced from the evidence: not observed)

### SPK-T2-14 · minor · `nf-spectio` next to `nf-tower`: the mark can go

- **Where:**
  - [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md), Context: "Running both in one run is **[to be validated]** in spike T2."
  - synthesis.md §1, item 2: "…so a run can report to Seqera Platform (`nf-tower`) and to Spectio at the same time (**[to be validated]** in spike T2)."
  - api-and-data-model.md §10, the Tower protocol row, with the same mark.
- **Evidence:** both observers ran in each of the 6 runs, on both versions, with the same run name, the same session ID and the same task IDs (note, "nf-spectio next to nf-tower" table; T2 Progress, Evidence).
- **Problem:** a verified claim still carries the mark.
- **Proposal:**
  - add a dated "Update 2026-10-28" line to decision 0001 that cites the T2 note;
  - replace the two marks with a link to the note;
  - add a decision-log entry.
- **Found by:** T2 spike
- **Status:** accepted (auto: measured in 6 of 6 runs; this confirms decision 0001 and reverses nothing; only marks become links) → applied (APPLY3, 2026-10-28): decision 0001 (Update 2026-10-28); synthesis §1 and api §10, marks turned into links

### SPK-T2-15 · minor · Snakemake: the 14 `LogEvent` types, and untyped records

- **Where:** synthesis.md §2 (Snakemake): "receives typed `LogRecord`s: `WORKFLOW_STARTED`, `RUN_INFO`, `JOB_INFO`, `JOB_STARTED`, `JOB_FINISHED`, `JOB_ERROR`, `PROGRESS`, `ERROR`, etc."
- **Evidence:**
  - `LogEvent` has 14 members: `RUN_INFO`, `WORKFLOW_STARTED`, `SHELLCMD`, `JOB_INFO`, `JOB_ERROR`, `JOB_STARTED`, `JOB_FINISHED`, `GROUP_INFO`, `GROUP_ERROR`, `RESOURCES_INFO`, `DEBUG_DAG`, `PROGRESS`, `RULEGRAPH`, `ERROR` (`snakemake_interface_logger_plugins/common.py:33-47`, v2.1.0).
  - In the flaky run, 122 of 469 records have no event type (`check_t2.py smk`; note row 15).
- **Problem:** "etc." hides `SHELLCMD`, `RESOURCES_INFO` and `RULEGRAPH`, and the spec does not say what happens to untyped records.
- **Proposal:** in §2, list the 14 members with the citation, and add: "untyped records are kept as text; a few become typed events (§2ter, Consequences 2)".
- **Found by:** T2 spike
- **Status:** accepted (auto: fact correction backed by the code at v2.1.0; local fix in synthesis §2) → applied (APPLY3, 2026-10-28): synthesis §2

### SPK-T2-16 · minor · Snakemake attempts: count `JOB_ERROR` per `jobid`

- **Where:** synthesis.md §2ter, Retries row: "Attempt number not sent; same `jobid` re-emitted after \"Trying to restart job N\"". Its fix column says: "Count attempts in the Snakemake plugin".
- **Evidence:**
  - the claim is confirmed;
  - the restart message is untyped text (`scheduling/job_scheduler.py:566`, v9.27.1);
  - `JOB_ERROR` is sent once per failed attempt: the tool error with 3 attempts gives 3 for job 30 (`check_t2.py smk_attempts`; note row 16).
- **Problem:** the spec does not say how to count, which invites a regex on the restart text.
- **Proposal:** in the §2ter Retries row, "attempt n = 1 + number of `JOB_ERROR` already seen for that `jobid` in this launch; no text parsing".
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py smk_attempts`; local fix in synthesis §2ter) → applied (APPLY3, 2026-10-28): synthesis §2ter

### SPK-T2-17 · minor · No exit code in Snakemake `JOB_ERROR`

- **Where:** api-and-data-model.md §7, the `tasks, attempts…` row: "· task_id, n, launch_n, state (§7.2), ignored, exit, resources (JSON) ·". Nullability is not stated. synthesis.md §2ter, "Extended data model" (now superseded by api §7), says "**Attempt**: number, requested and measured resources, exit code, error action."
- **Evidence:**
  - `JOB_ERROR` carries `rule_name`, `jobid`, `input`, `output`, `log`, `shellcmd`, `conda_env`, `container_img` and `aux`, but no exit code (`jobs.py:1129-1142`, v9.27.1; `check_t2.py smk`);
  - the code is only in the text of the matching `ERROR` record: "returned non-zero exit status 1." (note row 17).
- **Problem:** a `NOT NULL` or a default 0 would record wrong exit codes for Snakemake.
- **Proposal:** in api §7, write `exit` as "nullable; on Snakemake it is known only when the versioned regex on the `ERROR` text matches (synthesis §2ter, Consequences 2)". Cite the T2 note.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by the 9.27.1 code and the fixture; local fix in api §7) → applied (APPLY3, 2026-10-28): api §7

### SPK-T2-18 · minor · Checkpoints: two text messages mark "the DAG may change"

- **Where:** synthesis.md §2ter, dynamic-DAG row: "no \"DAG updated\" event; the new total only appears at the next `PROGRESS`". Its fix column says: "Display \"at least N\" while a checkpoint is open".
- **Evidence:**
  - each checkpoint job logs "DAG of jobs will be updated after completion." (`jobs.py:1107`) and "Updating checkpoint dependencies." (`dag.py:2245`), 12 each;
  - `progress.total` climbs from 32 to 67 in 12 steps;
  - source: `check_t2.py smk`, note row 18.
- **Problem:** the spec does not say how Spectio knows that a checkpoint is open.
- **Proposal:** in that row, the first message sets "DAG may change" (the "at least N" display) until the next `PROGRESS`. It is one of the typed text messages of Consequences 2.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py smk` and the 9.27.1 code; local fix in synthesis §2ter) → applied (APPLY3, 2026-10-28): synthesis §2ter

### SPK-T2-19 · minor · "Removing temporary output" is logged twice

- **Where:** synthesis.md §2ter, Temporary files row: "deletion = a plain text message \"Removing temporary output\"" and "message turned into a `temp_removed` event".
- **Evidence:** in the flaky run, all 12 messages appear twice (`dag.py:1055`, v9.27.1; `check_t2.py smk`; note row 19).
- **Problem:** without deduplication, every deletion is counted twice.
- **Proposal:** in that row, "`temp_removed` is deduplicated by (run, path)".
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by `check_t2.py smk`; local fix in synthesis §2ter) → applied (APPLY3, 2026-10-28): synthesis §2ter

### SPK-T2-20 · minor · Snakemake executor: only `local`

- **Where:** synthesis.md §2ter, Executors row: "Executor name absent from events; only `local` (true/false)".
- **Evidence:** confirmed; `JOB_STARTED` carries `jobs` (job IDs). Job groups were not tested (note row 20).
- **Problem:** none: the run matches the spec.
- **Proposal:** none.
- **Found by:** T2 spike
- **Status:** rejected (cannot be reproduced as a difference: the observation matches synthesis §2ter)

### SPK-T2-21 · minor · Logger plugin contract: `baseFilename` is needed when `writes_to_file = True`

- **Where:** synthesis.md §2bis ("Snakemake: no built-in equivalent"): "**Pitfall**: if the plugin does not declare `has_filter = True`, Snakemake applies its default filter to it…". This is the only plugin-contract note.
- **Evidence:** with `writes_to_file = True`, Snakemake reads `handler.baseFilename` (`logging.py:663`, v9.27.1), which `LogHandlerBase` does not declare (`base.py`, v2.1.0). The first spike run crashed with `AttributeError` (note, Plugin contract gaps; row 21).
- **Problem:** whoever writes `snakemake-logger-plugin-spectio` hits the same crash.
- **Proposal:** add a second pitfall to §2bis: "a handler with `writes_to_file = True` must set `baseFilename`".
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by the 9.27.1 and 2.1.0 code; local fix in synthesis §2bis) → applied (APPLY3, 2026-10-28): synthesis §2bis

### SPK-T2-22 · minor · `resources` is a `Namedlist` and `workflow_id` is a `uuid.UUID`

- **Where:** synthesis.md §2 (Snakemake): "Fields may change between versions: read defensively." §2bis says nothing about serialisation.
- **Evidence:** `resources` arrives as `snakemake.io.Namedlist` and loses its names in naive JSON. `workflow_started.workflow_id` is a `uuid.UUID` (`workflow.py:303`, v9.27.1), which plain `json.dumps` refuses (note row 22).
- **Problem:** a naive plugin fails, or drops resource names.
- **Proposal:** add to the §2bis pitfalls: "the plugin serialises defensively: `Namedlist` → dict, `UUID` → string, unknown types → `str()`".
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by the 9.27.1 code and the spike's first run; local fix in synthesis §2bis) → applied (APPLY3, 2026-10-28): synthesis §2bis

### SPK-T2-23 · major · Engine events carry user, host, home directory and command line

- **Where:** gap. admin-and-operations.md §3.4 owns redaction: "One redaction function, owned here, is applied before anything is written to or sent from these sinks: event ingest (`POST /ingest/events`)…" It covers secrets only (secret values, `spk_` tokens, sensitive key names), not personal identifiers. The ingest payload rules belong to api §14, which is not written yet (inbox #36).
- **Evidence:** Snakemake `WORKFLOW_STARTED` carries `host`, `user`, `cmd`, `cwd`, `rundir` and `platform` (`check_t2.py smk`). Tower `begin.workflow` carries `userName`, `homeDir`, `commandLine` and `configText` (note row 23).
- **Problem:** no spec says which identity fields Spectio stores, shows or drops.
- **Proposal:** see [proposed inbox #55](inbox.md#55-what-engine-events-may-carry-task-script-and-env-user-host-and-command-line).
- **Found by:** T2 spike
- **Status:** inbox (reserved: security posture defaults, personal data)

### SPK-T2-24 · minor · The settings class is `LogHandlerSettings`, not `LoggerSettings`

- **Where:** gap: no spec names the settings class. The plugin-contract note is synthesis §2bis (SPK-T2-21).
- **Evidence:** the registry reads `LogHandlerSettings` (`registry/__init__.py:38`, v2.1.0), while the `settings.py` docstring says "named 'LoggerSettings'" (`settings.py:33`) (note row 24).
- **Problem:** a plugin that follows the docstring loses its settings without an error.
- **Proposal:** one clause in the same §2bis pitfall note: "settings class `LogHandlerSettings` (the docstring is wrong)". The upstream docstring fix is optional and is not sent without Thomas.
- **Found by:** T2 spike
- **Status:** accepted (auto: confirmed by the 2.1.0 code; local fix in synthesis §2bis, the same note as SPK-T2-21) → applied (APPLY3, 2026-10-28): synthesis §2bis

### SPK-T2-25 · minor · A local `nf-spectio` loads from the plugins directory with no registry lookup

- **Where:** architecture-plugins-and-packaging.md §7.3, "0.0.1 prerequisites": "nf-spectio ships as a jar inside the `spectio` wheel and is passed to Nextflow from there, so it works offline and matches the server version **[to be validated: how a local plugin jar is loaded, in spike T2]**" *(decided — Thomas, 2026-10-27, inbox #35)*.
- **Evidence:** T2 installed `nf-spectio` 0.0.1 as an unpacked plugin (`classes/META-INF/MANIFEST.MF`, `extensions.idx`) in `~/.nextflow/plugins`. `-plugins nf-spectio@0.0.1` loaded it with no registry lookup, and the same class files ran on 26.10.4 and 25.10.9 (note, "What was built"). The coordinator found this in the note; it is not in T2's table.
- **Problem:** "passed to Nextflow from there" is not how it worked. The plugin was installed into Nextflow's plugins directory first.
- **Proposal:** replace the mark in §7.3: the runner unpacks the jar from the wheel into the plugins directory (`$NXF_HOME/plugins/nf-spectio-<ver>/`) before launch and passes `-plugins nf-spectio@<ver>`. Whether `NXF_PLUGINS_DIR` can point to a read-only copy is **[to be validated]**. This keeps #35's decision (jar in the wheel) and refines the how.
- **Found by:** T2 spike (coordinator, from the note)
- **Status:** accepted (auto: confirmed by the T2 note and the 6 plugin runs; local fix in architecture §7.3; #35 is not reversed) → applied (APPLY3, 2026-10-28): architecture §7.3

### SPK-T2-26 · minor · The Snakemake logger plugin is found on `PYTHONPATH` by module prefix

- **Where:**
  - architecture-plugins-and-packaging.md §13.4: "the runner puts the logger plugin on `PYTHONPATH`; plugin discovery on module prefixes (§1) is **[to be validated]**";
  - §7.3: "how the Snakemake logger plugin reaches the user's Snakemake environment … is settled in spike T2 **[to be validated]**".
- **Evidence:** the spike plugin `snakemake_logger_plugin_spectio` was found through `PYTHONPATH` with no install. Discovery uses the module prefix `snakemake_logger_plugin_` (`common.py:8`, `registry/__init__.py:29-30`, v2.1.0) (note, "What was built"). The coordinator found this in the note; it is not in T2's table.
- **Problem:** two marks remain on something the spike did.
- **Proposal:** in §13.4 and §7.3, replace both marks with "verified in spike T2 (Snakemake 9.27.1, interface 2.1.0)" and a link.
- **Found by:** T2 spike (coordinator, from the note)
- **Status:** accepted (auto: confirmed by the note and the 2.1.0 code; local fix in architecture §7.3 and §13.4) → applied (APPLY3, 2026-10-28): architecture §7.3 and §13.4

### SPK-T2-27 · minor · `runs.failure` on Nextflow: the message is in `onFlowComplete`, not in `onFlowError`

- **Where:** api-and-data-model.md §7, `runs` row: "failure (JSON: `class`, `task_id`, `attempt_n`, `message`; set by the projector from the Nextflow `onFlowError` event or the Snakemake logger `ERROR` / `JOB_ERROR` records **[to be validated]**)".
- **Evidence:**
  - in both toolerr runs, `onFlowComplete` carries `success` false, `exitStatus` 1 and `errorMessage` "synthetic failure: tool exited with code 1";
  - the `TaskEvent` of `onFlowError` has no handler, so no task;
  - the failing task is the `onTaskComplete` with `errorAction` `TERMINATE` (COMPARE treatA_vs_ctrl);
  - source: `check_t2.py flow_end` and `failed_status`. This follows from note row 5; the coordinator split it out because api §7 is another owner.
- **Problem:** `onFlowError` cannot fill `task_id` or `attempt_n`.
- **Proposal:** in the api §7 `runs` row, for Nextflow, `message` comes from `onFlowComplete.errorMessage`, and `task_id` and `attempt_n` from the attempt whose `errorAction` is `TERMINATE`. Drop the mark for Nextflow.
- **Found by:** T2 spike (coordinator, from the fixtures)
- **Status:** accepted (auto: confirmed by `check_t2.py flow_end` and `failed_status`; local fix in api §7) → applied (APPLY3, 2026-10-28): api §7

## T3

**Sources:**
- the T3 worktree (`autopilot/T3`, head `41428f5`): the [Progress page](../progress/W3/T3.md) "Findings and open questions" (16 differences, 2 open questions), the [spike t3-ci note](../research/spike-t3-ci-2026-10-28.md) and the [review record](code/T3.md);
- fixtures: `tests/fixtures/slurm/slurm-26.05.5/*.json`, re-read with [`tools/triage/check_t3.py`](https://github.com/weber8thomas/spectio/blob/main/tools/triage/check_t3.py) (`python3 -I tools/triage/check_t3.py tests/fixtures/slurm/slurm-26.05.5`);
- the logs of CI run [40680736055](https://github.com/weber8thomas/spectio/actions/runs/40680736055) (`autopilot/T3`, `e2a9f6d`, success) and of spike runs 40667769713 and 40670286528.

Items 1 to 16 of the Progress page are SPK-T3-01 to SPK-T3-16, in the same order. SPK-T3-17 to SPK-T3-20 come from item 16 (the deferred review items that a spec still states), from open question 2, and from the coordinator's re-check.

### SPK-T3-01 · minor · Snakemake on SLURM: every failed task job is `FAILED 1:0`

- **Where:** schedulers-and-monitoring.md §3.5, failure classes, `tool_error` row: "`FAILED` with an exit code".
- **Evidence:**
  - Each Snakemake task job runs `python -m snakemake … --executor slurm-jobstep`, so the job ends `FAILED 1:0` whatever the rule returned. The tool's code is only in the task's Slurm log ([note](../research/spike-t3-ci-2026-10-28.md#differences-with-the-specs-and-the-harness), item 1).
  - Fixtures `snakemake-{oom_fatal,timeout_fatal,flaky_retry,tool_error_then_fixed_resume}-sacct.json` all say `FAILED`, `1:0`, status `ERROR` (`check_t3.py scenarios`).
  - The run 40680736055 log says: "RESULT snakemake: oom_fatal=pass;not-completed:[3×FAILED|1:0 ] timeout_fatal=pass;not-completed:[3×FAILED|1:0 ] …".
- **Problem:** the scheduler record's exit code is meaningless for Snakemake tasks. The class is still right (`tool_error`), but the code shown is wrong, and an `oom` or `timeout` injected by the tool itself cannot be told apart.
- **Proposal:** add a bullet to §3.5, "Classify from the record": "Snakemake on SLURM (executor plugin 2.8.0): a task job runs `snakemake --executor slurm-jobstep`, so a failing rule ends `FAILED 1:0` whatever the tool returned. The tool's code is only in the task's Slurm log, so `attempts.exit` stays null (api §7, SPK-T2-17) unless that log is read (T3)."
- **Found by:** T3 build (spike t3-ci)
- **Status:** accepted (auto: confirmed by the four Snakemake `-sacct.json` fixtures and the run 40680736055 log; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-02 · minor · The synthetic `oom` mode is not an OOM for Slurm

- **Where:** dev-environment-and-testing.md §3, Failure injection: "*OOM, timeout, flaky:* §10.1 scenarios (`oom`, `oom_once`, `oom_real`, `timeout`, `flaky`). On a cluster, SLURM reports `OUT_OF_MEMORY` and Kubernetes reports `OOMKilled`."
- **Evidence:**
  - Nextflow `oom_fatal` on `slurm-site` ends `FAILED 137:0` (`nextflow-oom_fatal-sacct.json`): the `oom` mode exits 137 by itself.
  - Only the probe's real allocation gives `OUT_OF_MEMORY` (`sacct-probes.json`, job `probe-oom`), with `ConstrainRAMSpace=yes` (`check_t3.py scenarios`, `probes`; note item 2).
- **Problem:** the sentence promises a Slurm OOM from every OOM scenario. Only `oom_real` (or the probe) gives one.
- **Proposal:** in §3: "On a cluster, only `oom_real` makes the scheduler report the kill (SLURM `OUT_OF_MEMORY` with `ConstrainRAMSpace=yes`; Kubernetes `OOMKilled`). `oom` and `oom_once` exit 137 themselves, so SLURM records `FAILED 137:0` (Nextflow) or `FAILED 1:0` (Snakemake, SPK-T3-01) (T3)."
- **Found by:** T3 build (spike t3-ci)
- **Status:** accepted (auto: confirmed by `nextflow-oom_fatal-sacct.json` and `sacct-probes.json`; local fix in dev-env §3) → applied (APPLY3, 2026-10-28): dev-env §3

### SPK-T3-03 · minor · SLURM `OUT_OF_MEMORY` with exit 0:125: the mark can go

- **Where:** schedulers-and-monitoring.md §3.5, "Classify from the record": "an OOM kill gives 137 locally, but `OUT_OF_MEMORY` with exit code 0:125 under SLURM **[to be validated on sind]**".
- **Evidence:** `sacct-probes.json`, job `probe-oom`:
  - state `OUT_OF_MEMORY`;
  - `exit_code.return_code` unset, `signal.id` 125, status `SIGNALED`;
  - Slurm 26.05.5, run 40680736055 (`check_t3.py probes`).
  - The spike note's probe result agrees.
- **Problem:** a verified fact still carries the mark. The JSON form (signal 125, no return code) is not stated.
- **Proposal:** replace the mark with "(verified on sind, Slurm 26.05.5, T3; in `sacct --json`: `return_code` unset, `signal.id` 125, status `SIGNALED`)".
- **Found by:** coordinator (TRIAGE3 re-check of the T3 fixtures)
- **Status:** accepted (auto: fact correction backed by `sacct-probes.json`; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-04 · minor · Snakemake's own SLURM status polling delays task ends by 40 to 180 s

- **Where:** gap. schedulers-and-monitoring.md §3.2 (Batched observation and budgets) budgets Spectio's polling. No spec says that the Snakemake executor polls on its own clock.
- **Evidence:**
  - Executor plugin 2.8.0 waits `init_seconds_before_status_checks` (default 40 s) before the first check, and again after each check that sees a job finish. It waits up to 180 s when nothing finishes ([`__init__.py:244-251, 1611-1617` at v2.8.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/blob/v2.8.0/snakemake_executor_plugin_slurm/__init__.py#L1611-L1617), note item 3).
  - `happy` took 762.6 s with the default and 222 to 338 s with 5 s.
  - The tests pass `--slurm-init-seconds-before-status-checks 5` (`tests/slurm/scenarios.sh:24`).
- **Problem:** Snakemake's engine events about SLURM task ends lag the scheduler by up to 3 minutes. The runner's own `sacct` poll can see an end first, and nothing says that this is expected.
- **Proposal:** add one sentence to §3.2: "Snakemake on SLURM learns of task ends only at its own status checks (plugin 2.8.0: 40 s after a submission or a finish, up to 180 s), so the runner's poll may see a job end before the engine reports it. The state lattice (api §8.2) keeps that order harmless. The sind tests pass `--slurm-init-seconds-before-status-checks 5`." Whether Spectio's generated Snakemake profile lowers the value on real sites is left open **[to be validated: site load]**.
- **Found by:** T3 build (spike t3-ci)
- **Status:** accepted (auto: confirmed by the plugin source at v2.8.0 and `scenarios.sh:24`; local fix in schedulers §3.2) → applied (APPLY3, 2026-10-28): schedulers §3.2

### SPK-T3-05 · major · Nextflow's own cleanup reads as "Cancelled by someone else"

- **Where:** schedulers-and-monitoring.md §3.5, `cancelled_external` row: "`CANCELLED by <uid>` | deleted by another principal | show who; no automatic retry".
- **Evidence:**
  - After a fatal failure, Nextflow cancels its own pending jobs, and `sacct` shows them `CANCELLED by 1001`: the submitting user's uid.
  - Spike runs 40667769713 ("108_[0-3]|nf-ALIGN_(21)|CANCELLED by 1001") and 40670286528 ("129|nf-COMPARE_(treatA_vs_ctrl)|CANCELLED by 1001"), from the job logs.
  - T3 run 40680736055: "oom_fatal=pass;not-completed:[1×CANCELLED 3×FAILED|137:0 ]" (note item 4; Progress item 4).
- **Problem:** every fatal Nextflow run on SLURM would show "Cancelled by someone else" on its cleaned-up tasks.
- **Proposal:** in the §3.5 `cancelled_external` row, SLURM column: "`CANCELLED` by a user other than the run's user (text: `by <uid>`; JSON: `kill_request_user`, SPK-T3-16)". Add a sentence under the table: "A cancel by the run's own user after the engine has reported the run's failure is engine cleanup. It is shown as 'cancelled by the engine', with no class."
- **Found by:** T3 build (spike t3-ci)
- **Status:** accepted (auto: confirmed by the logs of spike runs 40667769713 and 40670286528; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-06 · minor · Pending reasons in `--json`: `state_reason` and `state_description`; `sacct` keeps the last reason

- **Where:** schedulers-and-monitoring.md §3.5, pending-reasons table, row "`ReqNodeNotAvail, Reserved for maintenance`". That is the text (`%r`) form. §2 L2 row: "`--json` for details: `job_state`, `state_reason`, `start_time`".
- **Evidence:**
  - `squeue-pending-reasons.json`:
    - the maintenance job has `state_reason` "ReqNodeNotAvail" and `state_description` "ReqNodeNotAvail, Reserved for maintenance";
    - the other probe jobs have an empty `state_description`: `AssocMaxJobsLimit`, `Resources`, `Priority`, `PartitionTimeLimit`, `Dependency`, `DependencyNeverSatisfied`, `JobHeldUser`, `JobHeldAdmin`.
  - `sacct-probes.json` keeps a pending reason on finished jobs: `probe-cap2` is `COMPLETED` with reason `AssocMaxJobsLimit`, and `probe-maint` is `COMPLETED` with `ReqNodeNotAvail`.
  - Sources: `check_t3.py pending` and `probes`; note item 5.
- **Problem:** a JSON parser that matches the table's text finds no maintenance row. One that reads `sacct`'s reason on a finished job shows history as a current wait.
- **Proposal:** under the §3.5 pending-reasons table, add:
  - "With `--json`, match `state_reason`. `ReqNodeNotAvail` needs `state_description` to tell a maintenance window from other cases; it is the only probe reason with a description (Slurm 26.05.5, T3).
  - A `sacct` reason on a job in a terminal state is history, not a wait."
- **Found by:** T3 build (spike t3-ci)
- **Status:** accepted (auto: confirmed by `squeue-pending-reasons.json` and `sacct-probes.json`; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-07 · minor · `sacct -s FAILED,… -S <time>` returned nothing once

- **Where:** gap: no spec uses `sacct -s`.
- **Evidence:** spike run 2 (40665414538) found nothing with `-s`; later runs filtered states themselves. T3 did not retest, and the cause is **[to be validated]** (note item 6; Progress item 6).
- **Problem:** none in a spec. The harness already filters states itself.
- **Proposal:** none; it stays a follow-up of the note.
- **Found by:** T3 build (spike t3-ci)
- **Status:** rejected (cannot be reproduced: one spike run, not retested; no spec text affected)

### SPK-T3-08 · minor · `NODE_FAIL` carries exit 1, status `ERROR`

- **Where:** schedulers-and-monitoring.md §3.5: "**Classify from the record, not from the exit code alone.**" `node_failure` row: "`NODE_FAIL`, `BOOT_FAIL`".
- **Evidence:** `sacct-probes.json`, `probe-nodefail`: `NODE_FAIL`, `1:0`, `ERROR` (`check_t3.py probes`; note item 7).
- **Problem:** none: classification by state, as §3.5 says, handles it.
- **Proposal:** none.
- **Found by:** T3 build (spike t3-ci)
- **Status:** rejected (no difference: the observation matches §3.5)

### SPK-T3-09 · major · A Nextflow task over its time ends `FAILED 140:0`, not `TIMEOUT`

- **Where:** schedulers-and-monitoring.md §3.5, `timeout` row, SLURM column: "`TIMEOUT`".
- **Evidence:**
  - `nextflow-timeout_fatal-sacct.json` (job 150, `nf-QC_STATS_(S05)`): `FAILED`, `return_code` 140, time limit 1 min, elapsed 5 s (`check_t3.py scenarios`).
  - The run 40680736055 log says: "timeout_fatal=pass;not-completed:[3×FAILED|140:0 ]".
  - Nextflow adds `--signal B:USR2@30` unless the user sets `--signal` ([`SlurmExecutor.groovy:71-75` at v26.10.4](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/groovy/nextflow/executor/SlurmExecutor.groovy#L71-L75)), and the wrapper traps `USR2` ([`command-run.txt:192`](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/resources/nextflow/executor/command-run.txt#L192)). 140 = 128 + 12 (`USR2`) (Progress item 8).
  - The signal came after 5 s, under a 1-minute limit. That fits sbatch's note that a `--signal` may be sent up to 60 s early **[to be validated: sbatch man page]**.
- **Problem:** every Nextflow task timeout on SLURM would be classed `tool_error`, and Spectio would suggest no time increase.
- **Proposal:** in the §3.5 `timeout` row, SLURM column: "`TIMEOUT`; for a Nextflow task also `FAILED` with exit 140 (Nextflow's `--signal B:USR2@30`, trapped by its wrapper; T3)". Whether this holds for limits well above a minute is **[to be validated]**, as T3 says.
- **Found by:** T3 build
- **Status:** accepted (auto: confirmed by `nextflow-timeout_fatal-sacct.json`, the run log and the Nextflow source at v26.10.4; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-10 · minor · On SLURM the fatal scenarios give other exit codes than §10.1 lists

- **Where:** dev-environment-and-testing.md §10.1, row "`oom_fatal`, `timeout_fatal`": "failure after 3 attempts with the right exit codes: 137; for the time limit, 143 on Nextflow 26.10, none on Nextflow 25.04 and 25.10, 124 on Snakemake". These are the local executor's codes. `pipelines-slurm.yml` runs both scenarios (§11 row).
- **Evidence:**
  - On `slurm-site`:
    - Nextflow `oom_fatal` gives `FAILED 137:0` and `timeout_fatal` gives `FAILED 140:0`;
    - every Snakemake failed task job gives `FAILED 1:0`, because the Snakefile wraps the task in `timeout` and the jobstep hides the code (SPK-T3-01).
  - Only the probe produces a Slurm `TIMEOUT` (`check_t3.py scenarios`, `probes`; Progress item 9).
- **Problem:** the row reads as if the same codes held on a cluster.
- **Proposal:** add to that §10.1 row: "On SLURM (T3): Nextflow 137 and 140 (SPK-T3-09); Snakemake `FAILED 1:0` for both, the tool's code only in the task log. A Slurm `TIMEOUT` needs a `runtime` the job really exceeds (only the probe has one today)."
- **Found by:** T3 build
- **Status:** accepted (auto: confirmed by the eight scenario `-sacct.json` fixtures; local fix in dev-env §10.1) → applied (APPLY3, 2026-10-28): dev-env §10.1

### SPK-T3-11 · minor · `slurm-mini` needs partition `htc`

- **Where:** dev-environment-and-testing.md §4.1, `slurm-mini` row.
- **Evidence:** both engines' `slurm` profiles name `htc`. T3 added it to `dev/slurm/mini.yaml`, and the row now says "controller + 1 worker (partition `htc`)" (Progress item 10).
- **Problem:** none left.
- **Proposal:** none.
- **Found by:** T3 build
- **Status:** applied (T3, dev-env §4.1 `slurm-mini` row)

### SPK-T3-12 · minor · `slurm-site` has no `gpu` partition yet; the `slurm-mini` signal drain is not built

- **Where:** dev-environment-and-testing.md §4.1, `slurm-site` and `slurm-mini` rows (deferred review item CR-T3-03).
- **Evidence:** both rows now say "Planned, not built yet": partition `gpu` with fake GRES, and on `slurm-mini` the signal drain then cancel (Progress items 11 and 16).
- **Problem:** none left in the rows. When they get built is part of [proposed inbox #60](inbox.md#60-assumed-who-builds-the-deferred-slurm-coverage).
- **Proposal:** none.
- **Found by:** T3 build, code-reviewer (CR-T3-03)
- **Status:** applied (T3, dev-env §4.1 `slurm-site` and `slurm-mini` rows)

### SPK-T3-13 · minor · The `pipelines-slurm.yml` row

- **Where:** dev-environment-and-testing.md §11, `pipelines-slurm.yml` row (before T3: called by `ci.yml`, `GSI-HPC/sind-action@v2`).
- **Evidence:** T3 rewrote the row. The workflow is standalone (push with a path filter, nightly, manual), outside `ci-ok`, and gets sind from `dev/bootstrap.sh` (Progress item 12).
- **Problem:** the row is fixed. The §11 **Required checks** paragraph (*decided — Thomas, 2026-10-27, inbox #26*) still says `ci.yml` calls `pipelines-slurm.yml`. This is the same difference as SPK-T4-09 for `pipelines-k8s.yml`, so it is merged there and in [proposed #57](inbox.md#57-assumed-pipelines-k8syml-and-pipelines-slurmyml-join-ciyml-as-inbox-26-decided), together with T3's open question "Should `pipelines-slurm.yml` join `ci.yml` and `ci-ok`?". There is no separate finding.
- **Proposal:** none here.
- **Found by:** T3 build
- **Status:** applied (T3, dev-env §11 `pipelines-slurm.yml` row). The Required-checks part is merged into SPK-T4-09 / proposed #57.

### SPK-T3-14 · minor · slurmrestd on 26.05.5 serves `v0.0.43` to `v0.0.45`

- **Where:** schedulers-and-monitoring.md §3.3, slurmrestd row: "the OpenAPI plugin versions in use on Slurm 26.05 are `data_parser` v0.0.42 to v0.0.45 … the range shared with 26.05 is v0.0.42 to v0.0.44".
- **Evidence:** `ping` gives 200 on `v0.0.43`, `v0.0.44` and `v0.0.45` (run 40680736055, `rest` job: "ping-v0.0.43 200 732 ping-v0.0.44 200 731 ping-v0.0.45 200 712"). `v0.0.42` was not probed. The dev-env §4.1 `slurm-rest` row already records the three (T3).
- **Problem:** none: the observation agrees with §3.3, and v0.0.42 was not tried.
- **Proposal:** none. Probing `v0.0.42` is a follow-up for the `slurm-versions` step (proposed #60).
- **Found by:** T3 build
- **Status:** rejected (no difference with schedulers §3.3; the measurement is already recorded in the dev-env §4.1 `slurm-rest` row)

### SPK-T3-15 · major · `X-SLURM-USER-NAME` with a user's own token: no clean refusal

- **Where:** gap. schedulers-and-monitoring.md §3.3, slurmrestd row: "the site runs it with JWT auth … Lets a runner live off the login node". It does not say which token the runner holds, or what it sends in `X-SLURM-USER-NAME`.
- **Evidence:**
  - spx's token with `X-SLURM-USER-NAME: root` gets 200 on `GET ping` (run 40679302148; review record, CR-T3-04).
  - It gets 511 on a `DELETE` of a held job of root's, and the job stays `PENDING`. Run 40680736055 log: "no-token=401 spx-token-as-root:DELETE-root-job=511,root-job=PENDING".
  - Why `ping` passes, and what 511 means here, is **[to be validated]** (Progress item 14).
- **Problem:** the transport's identity model is unspecified. A 2xx proves nothing about whose identity a call ran under, and the runner could run with a token wider than the user's.
- **Proposal:** see [proposed inbox #59](inbox.md#59-slurmrestd-which-token-the-runner-holds-and-which-user-it-names).
- **Found by:** T3 build, code-reviewer (CR-T3-04), security-reviewer (SEC-T3-02)
- **Status:** inbox (reserved: auth modes and security posture defaults of the slurmrestd transport)

### SPK-T3-16 · minor · In `sacct --json` the canceller is a user name, `kill_request_user`

- **Where:** schedulers-and-monitoring.md §3.5, `cancelled_external` row: "`CANCELLED by <uid>`". That is `sacct`'s text form.
- **Evidence:**
  - `sacct-probes.json`: the five jobs cancelled by root (`probe-partlimit`, `probe-dep`, `probe-depnever`, `probe-held`, `probe-adminhold`) have state `CANCELLED` and `kill_request_user: "root"`. The other six have `""`.
  - The text form reads "CANCELLED by 0" (run 40680736055: "root scancel=CANCELLED by 0") (`check_t3.py probes`; Progress item 15).
- **Problem:** a JSON parser finds no uid in the state, and must compare a user name, not a uid.
- **Proposal:** folded into SPK-T3-05's change to the same row: "JSON: `kill_request_user` (a user name), compared with the run's user name; text: `by <uid>`".
- **Found by:** T3 build
- **Status:** accepted (auto: confirmed by `sacct-probes.json`; local fix in schedulers §3.5, the same row as SPK-T3-05) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T3-17 · minor · Preemption is listed as "run in T3", but it was not built

- **Where:** dev-environment-and-testing.md §3, Failure injection: "Cluster-level cases, run in T3: … *Preemption:* a higher-priority partition and QoS in the sind cluster."
- **Evidence:** `PREEMPTED` is not produced. Preemption needs a QoS or partition-priority setup that `dev/slurm/site.yaml` does not have (Progress item 16 and "Deferred"; review record, CR-T3-02). Node failure, the other case in that list, was run (`probe-nodefail`, `NODE_FAIL`).
- **Problem:** the spec claims coverage that does not exist.
- **Proposal:** in §3: "*Preemption:* planned, not built yet (T3 deferred it; it needs a preemption setup in `slurm-site`)". When it is built is part of proposed #60.
- **Found by:** code-reviewer (CR-T3-02, deferred)
- **Status:** accepted (auto: confirmed by `dev/slurm/site.yaml` and `sacct-probes.json`, which has no `PREEMPTED`; local fix in dev-env §3) → applied (APPLY3, 2026-10-28): dev-env §3

The other deferred items of Progress item 16 are not findings:
- head `OUT_OF_MEMORY`, head `TIMEOUT` and `BOOT_FAIL` are product mappings in schedulers §3.5, and no test-coverage text claims them;
- `gpu` and the signal drain are already marked planned (SPK-T3-12);
- `oom_once_retry` is not in the §11 list of SLURM scenarios.

### SPK-T3-18 · minor · `slurm-versions` (25.11) is described as if built, and no step owns the deferred SLURM coverage

- **Where:** dev-environment-and-testing.md §4.1, `slurm-versions` row: "`slurm-site` on 25.11 and 26.05 | version matrix; the 25.11 leg covers the CLI transport only". It has no "planned" marker, unlike the other rows.
- **Evidence:**
  - T3 built `slurm-mini`, `slurm-site` and `slurm-rest` only (Progress, What changed).
  - T3's open question 2: "`slurm-versions` (25.11) and partition `gpu`: in T3's §4.1 rows, but not in its prompt. Build them in a later step?"
  - The T3 prompt ([next-phase.md](../playbooks/next-phase.md#t3-mini-slurm-with-sind)) names only the three profiles.
- **Problem:** the row claims a version matrix that does not run. Nothing in the pipeline builds it, or the other deferred SLURM coverage (`gpu`, preemption, signal drain, head OOM and walltime).
- **Proposal:** see [proposed inbox #60](inbox.md#60-assumed-who-builds-the-deferred-slurm-coverage). Under the assumed option, the row gets "Planned, not built yet" now.
- **Found by:** T3 build (open question 2), coordinator (row not marked)
- **Status:** inbox (assumed: (a) mark the rows planned now; each deferred item is built by the first build step that needs it). Which steps do the work is pipeline planning, not a local spec fix. → applied (APPLY3, 2026-10-28): dev-env §4.1 `slurm-versions` row, and the §3 preemption item links to inbox #60 (assumed — pending Thomas, inbox #60)

### SPK-T3-19 · minor · A Snakemake head in `sbatch` works on `slurm-site`

- **Where:**
  - schedulers-and-monitoring.md §3.1, "Snakemake heads": "whether Snakemake heads use a head job or the service-node alternative is **[to be validated]** in T3";
  - dev-environment-and-testing.md §15.1, Snakemake row: "the head submitted with `sbatch` **[to be validated]** in spike T3".
- **Evidence:** run 40680736055, `snakemake-b` job: "RESULT heads: snakemake head in sbatch: happy pass, head COMPLETED|0:0; plugin says: You are running snakemake in a SLURM job context. This is not recommended…". The head ran in `sbatch --wait` on `bigmem` (Progress, What was built).
- **Problem:** both marks remain on something T3 did. The §15.1 fallback (head on the login node) applies only "if spike T3 rules it out", and T3 did not.
- **Proposal:** replace both marks with "works on `slurm-site` for the synthetic `happy` scenario; the plugin warns but runs (T3, run 40680736055)". Failure scenarios and long runs stay **[to be validated]**. The §15.1 row links to schedulers §3.1, which owns head jobs.
- **Found by:** coordinator (from the T3 run log)
- **Status:** accepted (auto: confirmed by the run 40680736055 log; local fix in schedulers §3.1, plus the mark in dev-env §15.1 replaced by a link; this follows the §15.1 rule and reverses nothing) → applied (APPLY3, 2026-10-28): schedulers §3.1; dev-env §15.1 and §15.3

### SPK-T3-20 (SEC-T3-01) · minor · Nodes run tools from a directory that cluster jobs can write

- **Where:**
  - dev-environment-and-testing.md §4 (Local clusters), which has no rule on where node tools come from;
  - the §11 `pipelines-slurm.yml` row: "each `dev/bootstrap.sh --ci` into the data directory that every sind node mounts".
- **Evidence:**
  - `dev/slurm/env.sh:8` puts `$DATA/tools/bin` and `$DATA/tools/jdk/bin` on `PATH` in every node.
  - `dev/slurm/site.yaml:15-18` mounts `@DATA@` read-write into every node, and the job user `spx` gets the runner's uid, so it owns those files (`site.yaml` header; note, Setup).
  - Security-reviewer, T3 round 1, deferred to TRIAGE3 ([review record](code/T3.md), SEC-T3-01). T4 has the same pattern: the repository is mounted into the kind nodes, and task pods mount it as a hostPath (SEC-T4-01).
- **Problem:** a job on the test cluster can replace a tool that later steps of the same CI job run (for example `nextflow`, or `python3` in the venv). This includes the steps that write the fixtures.
- **Proposal:** add a rule under §4: "Tools that cluster nodes execute come from a location the cluster's job user cannot write:
  - on kind, a separate `extraMounts` entry with `readOnly: true`;
  - on sind, a second read-only mount **[to be validated: sind v0.15.0 storage options]**, or else the tools tree owned by root with no write bits.

  The data directory stays writable for work directories." The code is a follow-up for the step that next edits `dev/slurm/` and `dev/k8s/`.
- **Policy reasoning:** not reserved.
  - The reserved topic is the product's security posture defaults, meaning what a deployer gets. This rule only changes how the throwaway sind and kind clusters on GitHub-hosted runners are wired.
  - It is docs-only, reversible, local to dev-env §4 (one new paragraph), and reverses no decision. It is in the spirit of D3 (checked downloads).
  - Precedent: SPK-T4-15 (dev-tooling supply chain) was accepted on the same grounds.
  - If Thomas counts dev-cluster hardening as security posture, it moves to the inbox unchanged.
- **Found by:** security-reviewer (SEC-T3-01)
- **Status:** accepted (auto: confirmed by `dev/slurm/env.sh:8` and `dev/slurm/site.yaml:15-18`; local fix in dev-env §4; dev-tooling convention, not a product security default) → partly applied (APPLY3, 2026-10-28): dev-env §4, rule "Node tools are read-only for jobs"; pending: the code in `dev/slurm/` and `dev/k8s/` (not built yet)

## T4

### SPK-T4-01 · major · Nextflow 26.10 head Role: not sufficient, and broader than needed

- **Where:** schedulers-and-monitoring.md §4, RBAC: "26.10 creates one `Job` per task (§1): `jobs`: create, delete, get, list, watch; `pods`: get, list, watch; `pods/log`: get;"
- **Evidence:**
  - Under the §4 Role, the success run exits 1 in 7 s: `pods/status get` and `pods delete` are refused (403), and Jobs are left behind. Spike runs [40662141233](https://github.com/weber8thomas/spectio/actions/runs/40662141233) and [40663207755](https://github.com/weber8thomas/spectio/actions/runs/40663207755); log line "Request GET …/pods/…/status returned an error code=403".
  - The calls made are `jobs` create and delete, `jobs/status` get (only under Kueue), `pods` list and delete, and `pods/status` get. Sources in nf-k8s at v26.10.4: `K8sClient.groovy` L327–L333, L411–L445 and L234–L262 ([note, ServiceAccounts](../research/spike-t4-ci-2026-10-28.md#serviceaccounts-4)).
  - `watch`, plain `get`, `list` on Jobs and `pods/log` are never used.
  - T4 run [40674240654](https://github.com/weber8thomas/spectio/actions/runs/40674240654) with `tests/k8s/rbac.yaml`: 0 refusals, `unused-grants=[]`.
- **Problem:** the specified Role breaks every 26.10 run and grants calls that the head never makes.
- **Proposal:** replace the 26.10 line of §4 with the measured set from `tests/k8s/rbac.yaml`: `jobs`: create, delete; `jobs/status`: get; `pods`: list, delete; `pods/status`: get. Note the paths these runs did not hit (`fetchNodeName`, `kuberun`). Details in [proposed inbox #53](inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads).
- **Found by:** T4 build (spike t4-ci)
- **Status:** inbox (reserved: roles and permission defaults)

### SPK-T4-02 · major · Nextflow 25.10 head Role lacks `pods/status: get`

- **Where:** schedulers §4: "25.10 creates `Pod`s: `pods`: create, delete, get, list, watch; `pods/log`: get." and "25.10 needing `pods: create` is **[to be validated on k8s-mini]**".
- **Evidence:** under the §4 Role, the run exits 1 in 8 s with `pods/status get` refused (403). The measured set is `pods`: create, delete and `pods/status`: get, and gives 0 refusals (T4 `RESULT nf25: … {"refused":[],"used":["pods create","pods delete","pods/status get"]} unused-grants=[]`, run 40672184666). `pods: create` is therefore verified.
- **Problem:** as in SPK-T4-01, the specified Role breaks every 25.10 run.
- **Proposal:**
  - replace the 25.10 line with `pods`: create, delete; `pods/status`: get;
  - drop the "[to be validated on k8s-mini]" mark (a fact, so it could be applied alone);
  - see [proposed inbox #53](inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads).
- **Found by:** T4 build (spike t4-ci)
- **Status:** inbox (reserved: roles and permission defaults) → partly applied (APPLY3, 2026-10-28): schedulers §4, the fact part (`pods: create` verified on `k8s-mini`); pending: the Role lists wait for inbox #53

### SPK-T4-03 · major · The runner Role cannot read Kueue Workloads

- **Where:** schedulers §4, "What the runner watches": "When Kueue is installed: `Workload` objects (conditions `QuotaReserved`, `Admitted`, `Evicted`, `Preempted`) and the visibility API…". The Runner Role lists `pods`, `pods/log`, `events`, `jobs`, `resourcequotas`, `limitranges` and `persistentvolumeclaims` only.
- **Evidence:** with its own token, the runner gets "workloads.kueue.x-k8s.io is forbidden" (spike run 40663207755: `RESULT rbac runner: … workloads:REFUSED(Error from server (Forbidden)…`). The T4 runner Role adds `workloads.kueue.x-k8s.io`: get, list, watch, and the `runner` scenario passes (run 40674240654).
- **Problem:** the spec asks the runner to watch objects that its Role forbids.
- **Proposal:** add `workloads.kueue.x-k8s.io`: get, list, watch to the runner Role, as an optional rule when Kueue is installed (like the visibility rule). See [proposed inbox #53](inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads).
- **Found by:** T4 build (spike t4-ci)
- **Status:** inbox (reserved: roles and permission defaults)

### SPK-T4-04 · minor · Runner Role: visibility needs only `get`; minimality is not measured

- **Where:** schedulers §4, optional runner rule: "`visibility.kueue.x-k8s.io` `localqueues/pendingworkloads` (get, list, watch) for queue positions."
- **Evidence:**
  - `tests/k8s/rbac.yaml` grants the visibility rule `get` only, and the `runner` scenario reads the pending-workloads answer with it (run 40674240654);
  - `persistentvolumeclaims: get` and `watch` on pods, events and Workloads are granted and never used, because no runner code exists yet (T4 Progress, "Differences with the specs").
- **Problem:** the visibility grant is wider than the one call needs. The rest of the runner Role cannot be judged until runner code exists.
- **Proposal:** narrow the visibility rule to `get`. Leave the other runner grants until the runner exists, with a note "minimality not measured (T4)". Part of [proposed inbox #53](inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads).
- **Found by:** T4 build
- **Status:** inbox (reserved: roles and permission defaults)

### SPK-T4-05 · major · Nextflow 25.10 needs `nf-k8s` named for the k8s executor

- **Where:** gap. schedulers §4 ("Kueue and Nextflow") and architecture §7.5 (runner sub-chart) do not say which plugin the Kubernetes executor needs.
- **Evidence:**
  - Without the plugin, 25.10.9 stops with "Unknown executor name: k8s"; its log says `Plugins default=[]` (spike run 40662141233, job `k8s-mini rbac`: "ERROR ~ Unknown executor name: k8s").
  - With `-plugins nf-k8s@1.2.3`, the version that 25.10.9's own log lists among its core plugins, it runs (`tests/k8s/scenarios.sh:116`, `NF_K8S_25_10_VERSION=1.2.3` in `dev/versions.env:85`).
  - 26.10.4 needs nothing: its log says `Extension executors providers=[K8sExecutor]`. Where 26.10 bundles the executor is **[to be validated: source location]** (spike note).
  - The synthetic pipeline's `k8s` profile does not name the plugin (`tests/pipelines/synthetic/nextflow/nextflow.config:73-76`).
- **Problem:** every Spectio launch of Nextflow 25.10 on Kubernetes would fail. Offline clusters would also need the plugin pre-installed.
- **Proposal:** add a bullet to schedulers §4: on Nextflow 25.10, the generated config names `nf-k8s` at the version that Nextflow release lists as core (`plugins { id 'nf-k8s@1.2.3' }` for 25.10.9); 26.10 needs nothing. Offline sites pre-install it in the plugins directory, as for `nf-spectio` (SPK-T2-25). The synthetic `k8s` profile follows in the next step that edits it (code, not spec).
- **Found by:** T4 build (spike t4-ci)
- **Status:** accepted (auto: confirmed by the log of run 40662141233 and `scenarios.sh:116`; local fix in schedulers §4) → applied (APPLY3, 2026-10-28): schedulers §4

### SPK-T4-06 · minor · "Queued" comes from the visibility API, not from Workload conditions

- **Where:** schedulers §4, "What the runner watches" (Kueue bullet, quoted in SPK-T4-03). It reads Workload conditions and the visibility API side by side, with no rule for which one says "queued".
- **Evidence:** the visibility API lists a pending Workload before it has its `QuotaReserved=False` condition:
  - `tests/fixtures/k8s/kueue-pending-workloads.json` has `job-fx-kq-1-04f50` at position 0, while `kueue-workloads.json` shows that Workload with only `PodsReady=False/WaitForStart`;
  - the same in runs 40669626241 and 40668895003;
  - during `nf-kueue`, 3 of 4 Workloads had only `PodsReady` (spike note, Kueue timing).
- **Problem:** a runner that reads conditions only shows "queued" late, or never.
- **Proposal:** in the §4 Kueue bullet: "A task is queued when the visibility API lists its Workload; Workload conditions give the reason (`WaitingForQuota`) when present. Without visibility permission, the runner falls back to `QuotaReserved=False`."
- **Found by:** T4 build (spike t4-ci)
- **Status:** accepted (auto: confirmed by `tests/fixtures/k8s/kueue-*.json`; local fix in schedulers §4) → applied (APPLY3, 2026-10-28): schedulers §4

### SPK-T4-07 · minor · An OOM kill produces no event; a Job deadline deletes its pod

- **Where:** schedulers §4, "What the runner watches" (Events): "…so the runner keeps the last terminal state of each pod itself; otherwise a runner offline for more than an hour loses `FailedScheduling` and OOM reasons."
- **Evidence:**
  - `tests/fixtures/k8s/failures-events.json` has no OOM event; `fx-oom` appears only in the pod's `state.terminated.reason: OOMKilled`, exit 137 (`failures-pods.json`);
  - `fx-job-deadline`'s pod is deleted by the Job controller (event `SuccessfulDelete`), and only the Job condition `DeadlineExceeded` remains (spike note, "Plain failure objects").
- **Problem:** the sentence suggests that OOM reasons are in events, and it misses the Job-deadline case.
- **Proposal:** reword the sentence in §4: "An OOM kill is only in the container's `state.terminated` (no event), and a Job deadline deletes the Job's pod, leaving only the Job condition. So the runner keeps the last terminal state of each pod and Job itself; events expire after an hour (`FailedScheduling`)."
- **Found by:** T4 build (spike t4-ci)
- **Status:** accepted (auto: confirmed by `tests/fixtures/k8s/failures-*.json`; local fix in schedulers §4) → applied (APPLY3, 2026-10-28): schedulers §4

### SPK-T4-08 · minor · A 404 on `jobs/status` is not a refusal

- **Where:** gap. No spec describes the RBAC check's refusal criterion; it lives in `tests/k8s/api_calls.py`.
- **Evidence:** in run [40669626241](https://github.com/weber8thomas/spectio/actions/runs/40669626241), one `jobs/status` read got 404, because the Job was already deleted, and the check counted it as a refusal. Fixed in `9f516a4`: only 403 counts (T4 Progress, Evidence).
- **Problem:** none left in a spec; the test check is already fixed.
- **Proposal:** none.
- **Found by:** T4 build
- **Status:** rejected (no spec contradicted: a test-harness fix already applied in `9f516a4`)

### SPK-T4-09 · minor · `pipelines-k8s.yml` is standalone, while "Required checks" says `ci.yml` calls it

- **Where:** dev-environment-and-testing.md §11, "Required checks": "The pipeline workflows (`pipelines-synthetic.yml`, `pipelines-real.yml`, `pipelines-slurm.yml`, `pipelines-k8s.yml`) are reusable workflows (`on: workflow_call`, plus their own schedule) that `ci.yml` calls." *(decided — Thomas, 2026-10-27, inbox #26)*. The `pipelines-k8s.yml` row (edited in T4) says: "Standalone: `ci.yml` does not call it, so it is outside `ci-ok`."
- **Evidence:** `.github/workflows/pipelines-k8s.yml` runs on push with a path filter, nightly and on manual dispatch, and `ci.yml` does not call it (T4 Progress item 8). T4's open question: "Should `pipelines-k8s.yml` join `ci.yml` and `ci-ok`? It takes about 3 to 4 minutes, but kind adds a flake risk."
- **Problem:** the §11 row and the decided paragraph contradict each other. Fixing the paragraph would reverse the inbox #26 decision. T3 left `pipelines-slurm.yml` in the same state (SPK-T3-13); that part is merged here.
- **Proposal:** see [proposed inbox #57](inbox.md#57-assumed-pipelines-k8syml-and-pipelines-slurmyml-join-ciyml-as-inbox-26-decided).
- **Found by:** T4 build
- **Status:** inbox (assumed: (a) keep the #26 rule; `pipelines-k8s.yml` and `pipelines-slurm.yml` become reusable workflows called by `ci.yml` on their paths, and their §11 rows say "standalone until then") → partly applied (APPLY3, 2026-10-28): dev-env §11, `pipelines-slurm.yml` and `pipelines-k8s.yml` rows say "standalone until `ci.yml` calls it" (assumed — pending Thomas, inbox #57); pending: `ci.yml` does not call them yet

### SPK-T4-10 · minor · The `k8s-mini` row listed SeaweedFS, the Snakemake executor and a runner Role

- **Where:** dev-environment-and-testing.md §4.2, `k8s-mini` row (before T4).
- **Evidence:** T4 already rewrote the row. SeaweedFS and the Snakemake executor are "Planned, not built yet", and the Roles "are applied by the scenarios, not by `up`" (CR-T4-03; T4 Progress item 9).
- **Problem:** none left.
- **Proposal:** none.
- **Found by:** T4 build, code-reviewer (CR-T4-03)
- **Status:** rejected (duplicates a change already applied by T4 in dev-env §4.2, PR #33)

### SPK-T4-11 · minor · `FailedScheduling: Insufficient cpu` is back-pressure, not a failure

- **Where:** schedulers-and-monitoring.md §3.5: "**Pending reasons** are mapped to plain language." The table has SLURM reasons only. §2's L2 row already lists "events `FailedScheduling`" as a waiting source.
- **Evidence:** on the one-node `k8s-mini`, 58 of 65 pods first got `FailedScheduling: 0/1 nodes are available: 1 Insufficient cpu`, then ran (spike note, Scheduling; item 6).
- **Problem:** the plain-language table has no Kubernetes row, so the UI has no wording for the most common Kubernetes wait.
- **Proposal:** add Kubernetes rows to the §3.5 pending-reasons table:
  - `FailedScheduling … Insufficient cpu|memory` → "waiting for free CPU / memory" (not a failure);
  - Kueue `WaitingForQuota` → "waiting for queue quota", with its position (SPK-T4-06).
- **Found by:** T4 build (spike t4-ci)
- **Status:** accepted (auto: confirmed by the spike note and run 40663207755; local fix in schedulers §3.5) → applied (APPLY3, 2026-10-28): schedulers §3.5

### SPK-T4-12 (SEC-T4-02) · major · Task pods get the namespace's `default` ServiceAccount token

- **Where:** gap. schedulers §4 (RBAC) and architecture §7.5 (runner sub-chart, "in a work namespace") say nothing about the task pods' token.
- **Evidence:**
  - In spike run 40663207755 and T4 run 40670116723, every task pod had a `kube-api-access-*` volume.
  - T4 turned it off for the test cluster (`automountServiceAccountToken: false` on `default` in `dev/k8s/base.yaml:29`). No fixture of run 40672184666 has the volume.
  - Nextflow leaves `automountServiceAccountToken` unset unless `k8s.pod` sets it (`dev/k8s/base.yaml:21` cites `PodSpecBuilder.groovy` L469–L470 at v26.10.4).
- **Problem:** a pipeline task (third-party code) could call the API as `default`. The product's default is not specified.
- **Proposal:** see [proposed inbox #54](inbox.md#54-kubernetes-work-namespace-task-pod-tokens-and-a-shared-namespace).
- **Found by:** T4 build (spike item 7), security-reviewer (SEC-T4-02, fixed for the test cluster)
- **Status:** inbox (reserved: security posture defaults)

### SPK-T4-13 · minor · Inbox #51: "cannot download artifacts" does not hold

- **Where:** inbox #51, Context: "The GitHub tools available here read job logs but cannot download artifacts."
- **Evidence:** the T4 fixtures come from the artifacts of run 40672184666 (T4 Progress item 10; spike note, "Artifacts work too").
- **Problem:** none left: #51 already says so, in "Update (2026-10-28, 09:50): … this session could also download full logs and an artifact, contrary to the context above".
- **Proposal:** none.
- **Found by:** T4 build
- **Status:** rejected (duplicates the update already recorded in inbox #51)

### SPK-T4-14 (SEC-T4-03) · major · A shared work namespace lets any Job run as any ServiceAccount there

- **Where:** architecture-plugins-and-packaging.md §7.5, runner sub-chart: "A runner Deployment and the two ServiceAccounts with their Roles (runner, engine head) defined in [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) §4, in a work namespace, used by the `kubernetes` launcher." It says nothing about isolation inside that namespace.
- **Evidence:** security-reviewer, T4 round 1 ([review record](code/T4.md), SEC-T4-03): "whoever can create Jobs or Pods in the shared `spectio-work` can run as any ServiceAccount there, mount a hostPath, and delete another run's pods." The T4 heads may create Jobs or Pods, and `nf-head-25` needs `pods: create` (SPK-T4-02). The reviewer rated it minor for the dev cluster; it is major for the product spec, where it costs rework.
- **Problem:** one run's head (or task) can impersonate another ServiceAccount, read the node through a hostPath, or kill another run.
- **Proposal:** see [proposed inbox #54](inbox.md#54-kubernetes-work-namespace-task-pod-tokens-and-a-shared-namespace). The reviewer proposed one namespace per run or per user, PodSecurity `restricted`, and a policy that pins `serviceAccountName`.
- **Found by:** security-reviewer (SEC-T4-03)
- **Status:** inbox (reserved: security posture defaults; related to inbox #14, where the Kubernetes identity model is deferred)

### SPK-T4-15 (SEC-T4-05) · minor · Supply chain: `nf-k8s` by version, Kueue image by tag, full bootstrap in the job

- **Where:** dev-environment-and-testing.md §1, "Checked downloads": "Binaries and tarballs: against their sha256 in `versions.env`, before they are moved into place." The rule does not cover artefacts fetched by a tool at run time. Decision log 2026-10-27, D3: "Downloads are checked … Every image the doctor runs is pinned by digest."
- **Evidence:**
  - `NF_K8S_25_10_VERSION=1.2.3` is a version only (`dev/versions.env:85`); Nextflow downloads the plugin at run time.
  - The Kueue manifest is sha256-checked (`KUEUE_MANIFEST_SHA256`, `versions.env:81`; re-checked 2026-10-28: `646840e4…`), but it references the controller image by tag: `image: registry.k8s.io/kueue/kueue:v0.20.3` (`manifests.yaml` L27290 at v0.20.3).
  - `pipelines-k8s.yml` runs the whole `dev/bootstrap.sh`, not only the tools its jobs use ([review record](code/T4.md), SEC-T4-05).
- **Problem:** two downloads escape the D3 rule. Fixing them applies that decision; it does not reverse it.
- **Proposal:** in §1 "Checked downloads", add:
  - "Images named inside a pinned manifest (the Kueue controller) are pinned by digest: the manifest is rewritten to `image@sha256:…` before `apply`";
  - "Nextflow plugins needed at run time (`nf-k8s` on 25.10) are fetched by bootstrap from the plugin registry with a sha256 in `versions.env` and installed into the plugins directory; whether the registry publishes a checksum is **[to be validated]**";
  - "`bootstrap.sh --only <tools>` for CI jobs".
  - The code is a follow-up of the same kind as inbox #46; see the proposed update to #46 below.
- **Found by:** security-reviewer (SEC-T4-05)
- **Status:** accepted (auto: confirmed by `versions.env:81,85` and the v0.20.3 manifest L27290; local fix in dev-env §1; agrees with the D3 decision; code follow-up joins inbox #46) → partly applied (APPLY3, 2026-10-28): dev-env §1, "Checked downloads"; pending: the code (manifest images by digest, `nf-k8s` sha256, `bootstrap.sh --only`), with inbox #46

### SPK-T4-16 · minor · `k8s-kueue`: one Kueue version and no preemption, against two versions and preemption in the spec

- **Where:**
  - dev-environment-and-testing.md §1, Kueue row: "two pinned manifest versions: the newest supported Kueue minor (v0.20 at the time of R4) and an older one, both run in `k8s-kueue`";
  - §4.2, `k8s-kueue` row: "queue positions, admission, preemption".
- **Evidence:** T4 ran Kueue 0.20.3 only; `KUEUE_PREVIOUS_VERSION` 0.19.10 is pinned but not run. There is no preemption scenario. T4 Progress, "Not done here": "Kueue preemption, and the previous Kueue minor: none of them is in T4's prompt." T4 marked the `k8s-mini` row as planned, but not these two.
- **Problem:** the spec describes coverage that does not exist.
- **Proposal:**
  - in the §4.2 `k8s-kueue` row: "built: queue positions and admission (T4); planned, not built yet: preemption";
  - in the §1 Kueue row: "the older version is pinned, not run yet".
- **Found by:** T4 build (coordinator, from "Not done here")
- **Status:** accepted (auto: confirmed by `.github/workflows/pipelines-k8s.yml` and `dev/k8s/cluster.sh`, which use `KUEUE_VERSION` only; local fix in dev-env §1 and §4.2) → applied (APPLY3, 2026-10-28): dev-env §1 Kueue row and §4.2 `k8s-kueue` row

### SPK-T4-17 · minor · Kueue's default configuration does include the `pod` integration (the T4 note is wrong)

- **Where:** schedulers §4, "Kueue and Nextflow": "On Nextflow 25.10, which creates Pods, Kueue sees tasks only through its opt-in pod integration **[to be validated]**." The T4 note, Setup, says: "Its default `integrations.frameworks` contains `batch/job` and not `pod` (`manifests.yaml` L27147–L27154 at v0.20.3)."
- **Evidence:** in the v0.20.3 `manifests.yaml` (sha256 `646840e4…`, equal to `KUEUE_MANIFEST_SHA256`), the active `controller_manager_config.yaml` lists `integrations.frameworks` from L27148 to L27166. It includes `- "pod"` at L27163, uncommented, after the lines the note cited. 25.10's bare Pods were not tried through Kueue (note).
- **Problem:** the note's claim would turn the §4 mark into a wrong "off by default". The §4 word "opt-in" is also doubtful for v0.20.3.
- **Proposal:** §4: "the pod integration is listed in Kueue's default configuration (v0.20.3 `manifests.yaml` L27163); whether a 25.10 task Pod is admitted with only the queue-name label is **[to be validated]**". The note is dated and stays as written; this finding records the correction.
- **Found by:** coordinator (TRIAGE3 re-check of the T4 note's source)
- **Status:** accepted (auto: fact correction backed by the Kueue v0.20.3 manifest; local fix in schedulers §4) → applied (APPLY3, 2026-10-28): schedulers §4

## T7

T7 edited its own specs (dev-env §10.2 and §11) and sent its decisions to the inbox (#45, decided; #46, open). These are the differences left.

### SPK-T7-01 · minor · Nobody watches the nightly runs

- **Where:** gap. dev-environment-and-testing.md §11 (`pipelines-real.yml` and the other nightly rows) and [`autopilot.md`](../playbooks/autopilot.md) do not say who looks at a red nightly.
- **Evidence:**
  - T7 Progress, "For Thomas" item 2: "Nobody is notified when the nightly goes red."
  - The nightly on `main` on 2026-10-28, run [40649538349](https://github.com/weber8thomas/spectio/actions/runs/40649538349) (`schedule`, 07:21 UTC), failed on rna-seq-star-deseq2 and taxprofiler. `.autopilot/journal.md` does not mention it.
  - Diagnosis (coordinator, 2026-10-28, from the job logs and the check-run annotations): both failures are transient. taxprofiler (job 122686173132): `quay.io/v2/biocontainers/krakentools/blobs/sha256:de0d9ee3…: 502 Bad Gateway`, exit 125, not in the pipeline's retry list (`conf/base.config` L17 at [2.0.1](https://raw.githubusercontent.com/nf-core/taxprofiler/2.0.1/conf/base.config)); it passed in run 40562495868. rna-seq-star-deseq2 (job 122686172951): "The hosted runner lost communication with the server" during "Free runner disk"; no log was uploaded (the 404); it passed in run 40555936925. See SPK-T7-05.
- **Problem:** the nightly tier holds the heavy entries since inbox #45, and nothing reads its results.
- **Proposal:** see [proposed inbox #58](inbox.md#58-assumed-who-watches-the-nightly-runs).
- **Found by:** T7 build
- **Status:** inbox (assumed: (b) the autopilot reads the last scheduled run of each pipeline workflow at each tick and reports a red one in the journal and the step report) → partly applied (APPLY3, 2026-10-28): dev-env §11, "Nightly runs" (assumed — pending Thomas, inbox #58); pending: the autopilot playbook and skill do not read the scheduled runs yet

### SPK-T7-02 · minor · The repository is public: the corpus now runs with the unmeasured `public` limits

- **Where:** dev-environment-and-testing.md §10.2, Constraints: "private-repository GitHub runners have 2 CPU and 7.75 GB (6.9 GB free before a run; …), so nf-core runs get `process.resourceLimits` from `runner_limits.private` (2 CPU, 6 GB);". The T7 note §1 says: "`runner_limits.public` (4 CPU / 15 GB) is not measured … **[to be validated]**."
- **Evidence:**
  - `gh api repos/weber8thomas/spectio` gives `"visibility":"public"` (2026-10-28; inbox #49 already said "The repository is public now").
  - `pipelines-real.yml:63` chooses `LIMITS: ${{ github.event.repository.private && 'private' || 'public' }}`, so the corpus now uses `public: {cpus: 4, memory: "15.GB"}` (`corpus.yaml:18`).
  - The 2026-10-28 nightly (run 40649538349) ran with `LIMITS: public` on runners with `MemTotal: 16366644 kB`, 14.66 GB available at start (taxprofiler job), and a highest measured `run_peak_gb` of 8.35 (viralrecon).
  - Spike t4-ci measured a public `ubuntu-24.04` runner of this repository: 4 CPUs, 15 GB RAM, 86 GB free on `/`. GitHub documents 4 CPU and 16 GB ([runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), cited in the spike note).
- **Problem:** a 15 GB per-task cap on a 15 GB machine leaves no headroom for the JVM and Docker. T7 kept 0.9 GB under the free memory on private runners. The §10.2 text describes runners that the corpus no longer uses.
- **Proposal:** in the §10.2 Constraints bullet:
  - say that the repository is public since 2026-10-28, so `runner_limits.public` applies;
  - record the t4-ci measurement;
  - set `public` to leave headroom as `private` does (13 GB, under the 14.66 GB measured free at start in run 40649538349).
  - The tiers of inbox #45 are not touched. The `corpus.yaml` value is a follow-up in code.
- **Found by:** T7 build (open item 3), coordinator (repository now public; t4-ci measurement)
- **Status:** accepted (auto: confirmed by the REST API, `pipelines-real.yml:63` and `corpus.yaml:18`; local fix in dev-env §10.2; inbox #45 is not reversed) → applied by PR #36 (corpus retry, 2026-10-28): dev-env §10.2

### SPK-T7-03 · minor · `pipelines-real.yml` pins Nextflow 26.10.3, against 26.10.4 in `versions.env`

- **Where:**
  - dev-environment-and-testing.md §11, `pipelines-real.yml` row: "nf-core with `nf-core/setup-nextflow@v3`". No version is named, while the `pipelines-synthetic.yml` row says "Nextflow 26.10.4 (the `dev/versions.env` pin, since T1)";
  - §1: "`dev/versions.env` holds the exact value of every pin below".
- **Evidence:** `.github/workflows/pipelines-real.yml:58` has `with: {version: "26.10.3"}`; `tests/pipelines/real/corpus.yaml:8` has `current: "26.10.3"`; `dev/versions.env:39` has `NEXTFLOW_VERSION=26.10.4` (T7 Progress item 4; corpus note §4).
- **Problem:** the corpus tests another Nextflow than the pinned one. Inbox #42's answer (a) moved only the synthetic matrix.
- **Proposal:** in the §11 `pipelines-real.yml` row: "Nextflow at the `dev/versions.env` pin". The step that next edits `pipelines-real.yml` reads it from there, as #42 (a) did for the synthetic matrix. No required check is renamed: only `ci-ok` is required.
- **Found by:** T7 build
- **Status:** accepted (auto: confirmed by `pipelines-real.yml:58`, `corpus.yaml:8` and `versions.env:39`; local fix in dev-env §11; in line with #42 (a)) → applied (APPLY3, 2026-10-28): dev-env §11 `pipelines-real.yml` row; the workflow pin moves to `versions.env` in the next step that edits `pipelines-real.yml`, as proposed

### SPK-T7-04 (SEC-T7-01, SEC-T7-04) · minor · Corpus pinned by tag; unpinned conda inside the Snakemake action

- **Where:** dev-environment-and-testing.md §10.2: "every ref must be a release tag or a commit SHA". §11, `pipelines-real.yml` row: "the catalog with `snakemake/snakemake-github-action@v2`".
- **Evidence:** [review record](code/T7.md), SEC-T7-01 and SEC-T7-04, deferred to inbox #46.
- **Problem:** as stated in #46.
- **Proposal:** as in #46, plus the SEC-T4-05 code part (proposed update below).
- **Found by:** security-reviewer (SEC-T7-01, SEC-T7-04)
- **Status:** inbox (existing #46; nothing assumed; no new entry)

### SPK-T7-05 · minor · One registry error ends a corpus run

- **Where:** dev-environment-and-testing.md §10.2 (the corpus harness) says nothing about transient failures.
- **Evidence:** run 40649538349, taxprofiler: one quay.io 502 during a pull gave exit 125 and ended the run after 596 s, although every finished task was cached. Run 40562495868: rna-seq-star-deseq2 failed on a `conda.anaconda.org` 502. Each entry passed in another run (above).
- **Problem:** a red nightly then means "a CDN hiccupped" as often as "a pipeline broke", which defeats SPK-T7-01.
- **Proposal:** §10.2: "a failed Nextflow entry is retried once with `-resume` (cached tasks are not re-run); a retried pass is reported as `pass (retried)`". Code follow-up: `tests/pipelines/real/run_corpus.py` around L176, with a unit test. No retry for Snakemake entries until one is measured.
- **Found by:** coordinator (nightly diagnosis)
- **Status:** accepted (auto: confirmed by the job logs of run 40649538349; local fix in dev-env §10.2; reverses no decision) → applied by PR #36 (corpus retry, 2026-10-28): dev-env §10.2

## Inbox entries

The inbox items of this round are [#53 to #60](inbox.md#triage3-2026-10-28), plus an update to [#46](inbox.md#46-follow-up-pin-the-corpus-by-commit-and-replace-the-snakemake-composite-action).

## Counts

| Step | Findings | Accepted | Rejected | Applied by the step | Inbox | of which assumed | of which reserved |
|---|---|---|---|---|---|---|---|
| T2 | 27 | 22 | 2 | 0 | 3 | 1 (#56) | 2 (#55) |
| T3 | 20 | 12 | 3 | 3 | 2 | 1 (#60) | 1 (#59) |
| T4 | 17 | 7 | 3 | 0 | 7 | 1 (#57) | 6 (#53, #54) |
| T7 | 5 | 3 | 0 | 0 | 2 | 1 (#58) | 0 (1 already in #46) |
| **Total** | **69** | **44** | **8** | **3** | **14** | **4** | **9** |

- **New inbox entries:** #53 to #60 (8), plus an update to #46. #57 now also covers `pipelines-slurm.yml` (SPK-T3-13).
- **"Applied by the step":** T3 already made these changes in the dev-env §4.1 and §11 rows it built (SPK-T3-11 to SPK-T3-13). SPK-T4-10, the T4 equivalent, was triaged before this column existed and stays "rejected (already applied)".
- **Severities:** 14 major (T2 5, T3 3, T4 6), 55 minor, 0 blocker, counted from the finding titles. The earlier "13 major" was a miscount: it should have been 11.
- **Where the 44 accepted fixes land:**
  - checking-scenarios: §11.1, §11.4, §11.5;
  - synthesis: §1, §2, §2bis, §2ter;
  - api-and-data-model: §7, §7.2, §8.2;
  - architecture-plugins-and-packaging: §7.3, §13.3, §13.4;
  - schedulers-and-monitoring: §3.1, §3.2, §3.5, §4;
  - dev-environment-and-testing: §1, §3, §4, §4.2, §10.1, §10.2, §11, plus a link in §15.1;
  - decision 0001: a dated update line, and a decision-log entry.
- **schedulers §3.5 gets six T3 fixes** (SPK-T3-01, -03, -05, -06, -09, -16). Each is local to §3.5, but whoever applies them should do so in one pass, since -05 and -16 change the same row.
