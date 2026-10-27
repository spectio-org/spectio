# Spike T1 — fixture workflows, golden fixtures and resume identity (2026-10-27)

**Question.**
- Does every failure mode of the synthetic fixture workflows ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §3, §10.1) show up on the local executor, with the same outcome on every run, on each supported engine version?
- What does each engine do with the run's identity on a resume ([inbox #32](../reviews/inbox.md#32-relaunch-at-a-failed-gate-resume-after-a-failure-and-the-001-gate-verbs))?

**Answer.**
- **Scenarios.** All 11 PR scenarios pass on Nextflow 26.10.4, 25.10.9 and 25.04.8 and on Snakemake 9.27.1. Every suite ran twice, and the normalised task outcomes were identical both times. They are now golden fixtures, which CI compares on every run.
- **Fixes.** The runs found and fixed three faults in the fixtures: the Snakemake align gate, the `docker` profile, and a wrong claim about tool-error retries.
- **Resume identity.** Nextflow `-resume` gets a **new run name** and keeps the **same session ID**, and it only works from the **same launch directory**. A Snakemake rerun gets a fresh random `workflow_id`, and nothing links it to the previous invocation.
- **nf-core gate check.** The nf-core/rnaseq and nf-core/sarek gate stop-and-resume check was **not run**: Docker works here, but the measured cost is over this step's budget (see [below](#nf-corernaseq-and-nf-coresarek-not-run)).

## Setup

- **Machine:**
  - Claude Code cloud session: 4 CPUs, 15 GB RAM, 26 GB free disk;
  - Linux 6.18, OpenJDK 21.0.12;
  - Docker 29.9.2 started by hand (`dockerd --registry-mirror=https://mirror.gcr.io`, cgroup v1).
- **Engines.** Installed by `dev/bootstrap.sh` at the pins of `dev/versions.env`: Nextflow 26.10.4, 25.10.9 and 25.04.8, and Snakemake 9.27.1.
- **Commands** (from `tests/pipelines/synthetic/`):

  ```bash
  python3 run_scenarios.py --engine nextflow  --nextflow nextflow         --workdir $W/nf26   --golden record
  python3 run_scenarios.py --engine nextflow  --nextflow nextflow-25.10.9 --workdir $W/nf25   --golden record
  python3 run_scenarios.py --engine nextflow  --nextflow nextflow-25.04.8 --workdir $W/nf2504 --golden record
  python3 run_scenarios.py --engine snakemake                             --workdir $W/smk    --golden record
  # then the same four with --golden check in a fresh workdir: all exit 0
  python3 -m unittest tests/pipelines/synthetic/test_golden.py      # 5 tests, OK
  ```

## Golden fixtures

- **Where.** `tests/pipelines/synthetic/golden/<engine>-<version>/<scenario>.tsv`. There is one file per PR scenario: 11 per engine version, 44 in all, about 500 lines.
- **What each file holds:**
  - the exit code of each run;
  - the task outcomes, from the Nextflow trace (`execution_trace.txt`, read after each run) or from the Snakemake log;
  - the columns `run, process, status, exit, attempt, tag, count`.
- **Normalisation.** Timestamps, hashes, durations, task IDs and paths are dropped.
  - First-attempt `COMPLETED` and `CACHED` tasks are counted under the tag `*`.
  - Every other outcome keeps its tag (sample or wildcards).
- **Target filter.** When a scenario has a run that must fail, only the injected task is kept (process plus sample).
  - **Why:** after a fatal failure, which other tasks finished, were aborted or were cached depends on timing.
  - **Example:** in `tool_error_then_fixed_resume` the resume run had 62 cached tasks in one execution and 63 in the next, on each of the three Nextflow versions.
- **Checks:**
  - `run_scenarios.py --golden check` fails a scenario whose outcomes differ from its fixture, and writes `golden.actual.tsv` next to the run. Three cases fail the run: a missing fixture directory for the engine version, a version that does not read as `X.Y.Z`, and a missing file for a PR scenario. Only nightly scenarios may have no fixture.
  - A deliberately altered fixture (`happy`, ALIGN 24 → 23) failed the check, and the restored one passed.
  - `test_golden.py` unit-tests the normaliser on sample trace and log text, and checks that every engine version has exactly one fixture per PR scenario.
- **CI.** `pipelines-synthetic.yml` now runs the unit test and `--golden check`. Its Nextflow 26.10 pin moves from 26.10.3 to 26.10.4, so that it matches `NEXTFLOW_VERSION` in `dev/versions.env` and has fixtures. Nextflow 25.04.8 has fixtures but no CI leg (open item 4).

## Failure modes proven (local executor)

All rows are from the golden fixtures and are identical on both executions.

| Mode | Scenario | NF 26.10.4 | NF 25.10.9 | NF 25.04.8 | Snakemake 9.27.1 |
|---|---|---|---|---|---|
| flaky (fails on attempt 1) | `flaky_retry` | ALIGN S07, 2 chunks: FAILED exit 1 at attempt 1, COMPLETED at attempt 2; run exit 0 | same | same | same |
| OOM once (exit 137) | `oom_once_retry` | QC_STATS S05: FAILED 137 at attempt 1, COMPLETED at attempt 2; run exit 0 | same | same | same |
| OOM, fatal | `oom_fatal` | QC_STATS S05: FAILED 137 at attempts 1, 2, 3; run exit 1 | same | same | same |
| time limit, fatal | `timeout_fatal` | FAILED **143** at attempts 1–3; run exit 1 | FAILED with **no exit code** (`-`) at attempts 1–3 | same as 25.10.9 | FAILED **124** (`timeout` in the shell) at attempts 1–3 |
| non-zero exit, then fix and resume | `tool_error_then_fixed_resume` | COMPARE treatA FAILED exit 1, **1 attempt**; run exit 1; resume: COMPLETED, exit 0 | same | same | FAILED exit 1 at **attempts 1, 2, 3**; rerun: COMPLETED, exit 0 |
| checkpoint / dynamic fan-out | `dynamic_fanout` | 45 ALIGN tasks | 45 | 45 | 45 (the `split` checkpoint) |
| fan-out, PR size | `fanout_medium` | 180 ALIGN tasks | 180 | 180 | 180 |
| gate stop, then resume | `gate_qc_then_resume` | resume: 25 cached, 40 run | same | same | rerun: 42 jobs, nothing upstream of the gate |
| | `gate_align_then_resume` | resume: 61 cached, 4 run | same | same | rerun: 5 jobs (after fix 1) |
| | `exclude_sample_and_resume` | resume: 22 cached, 38 run | same | same | rerun: 40 jobs |
| real OOM (allocate beyond the limit) | `oom_real`, by hand (not a scenario) | QC_STATS S05: FAILED **137** at attempts 1–3 under `docker run --memory 512m / 1024m / 1536m` (2 GB allocated); run exit 1 | not run | not run | not run |

The `happy` scenario runs 65 tasks on Nextflow and 67 jobs on Snakemake (the extra two are the `all` and `align_done` target rules). The Snakemake engine fault listed in `scenarios.yaml` (`lost-retry-at-checkpoint-update`) did not occur: `oom_once_retry` ran 4 times without it.

The `oom_real` run used this command, after fix 3:

```bash
nextflow -q run tests/pipelines/synthetic/nextflow/main.nf -profile test,local,docker --outdir results \
  --fail_mode oom_real --fail_process QC_STATS --fail_sample S05
```

The `--memory 512m` flag is visible in the task's `.command.run`.

## Findings and fixes

1. **The Snakemake align gate skipped the qc stage.**
   - **Cause.** `--until align_done` "only runs jobs that are dependencies of the specified rule or files, does not run sibling DAGs" ([`cli.py` L892–L902 at v9.27.1](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/cli.py#L892-L902)).
   - **Effect.** `qc_stats` and `qc_report` never ran before the gate. On the rerun, the `temp()` reads had already been deleted, so 12 `make_reads` and 2 `split` jobs ran again.
   - **Fix.** The harness now stops at that gate with `--until qc_report align_done`. The rerun then runs only the 5 quant jobs, and the first run must now produce `multiqc/general_stats.tsv` (a new `scenarios.yaml` expectation).
   - **For Spectio.** A Snakemake gate after stage N must name the last target of every stage up to N, not only stage N's.
   - **Spec.** §10.1 now records the harness fact. The generation rule belongs to `checking-scenarios.md` §12.3, which needs a change: [inbox #48](../reviews/inbox.md#48-gate-targets-must-include-every-earlier-stages-last-targets-until-runs-only-the-targets-own-dependencies).
2. **Snakemake retries tool errors; Nextflow does not.**
   - `--retries` is the "Number of times to restart failing jobs" ([`cli.py` L1508–L1513 at v9.27.1](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/cli.py#L1508-L1513)), whatever the exit code. So `tool_error_then_fixed_resume` runs 3 attempts on Snakemake.
   - On Nextflow, the `errorStrategy` closure in `nextflow.config` retries only 137, 140, 143 and `Integer.MAX_VALUE`.
   - **Spec.** §10.1 said "a non-retried tool error"; that row is now corrected, and so is the `scenarios.yaml` title.
   - **For Spectio.** On Snakemake, failures are retried by count, not by class, unless the workflow's `retries` or resources logic says otherwise **[to be validated: per-rule retry conditions in Snakemake 9]**.
3. **The `docker` profile of the Nextflow twin could not run any task.** Two causes:
   - **`ps` missing.** `python:3.12-slim` has no `ps`, and Nextflow stops every task with "Command 'ps' required by nextflow to collect task metrics cannot be found" (observed on 26.10.4).
     - Fix: the `docker` and `k8s` profiles now use `python:3.12`, pinned by digest (`sha256:98d8fe4e…`). It ships procps-ng 4.0.4 (`docker run --rm python:3.12 ps --version`), but it is 1.62 GB against 182 MB for `-slim`.
   - **Dangling link.** Nextflow mounts `nextflow/bin` into the container, but `nextflow/bin/synth.py` is a link to `../../bin`, which was not mounted, so the task saw "synth.py: command not found".
     - Fix: `docker.runOptions` mounts the shared `bin/` read-only.
     - The `k8s` profile has the same layout problem; T4 must solve it with its own storage.
   - **After both fixes,** `oom_real` gives exit 137 under Docker's memory limit (table above). Spec §3 lists `oom_real` among the failure modes, and this is its first proof.
4. **No exit code on a Nextflow 25.x time limit.** Nextflow 25.04.8 behaves like 25.10.9 here: no exit code, so the trace shows `-` (the 2026-10-26 spike saw it on 25.10.9 only). Only 26.10.4 reports 143.
   - **Spec.** The §10.1 row named 143 for every version; it now gives the code per version.

## Resume identity (inbox #32)

### Nextflow

Observed on 26.10.4 and 25.10.9 (same results):
- **The commands:** `gate_qc_then_resume` (a stop with `conf/stop_after_qc.config`, then `-resume`), then `nextflow log` and `.nextflow/history`.

| What | Observation | Source |
|---|---|---|
| Run name | **New** on every launch, resume included: `sharp_meninsky` then `dreamy_mclean` (26.10.4); `festering_picasso` then `infallible_elion` (25.10.9). Reusing one with `-resume -name dreamy_mclean` fails: "Run name \`dreamy_mclean\` has been already used -- Specify a different one", exit 1. | `checkRunName()`, [`CmdRun.groovy` L551–L566 at v25.10.9](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/cli/CmdRun.groovy#L551-L566). At v26.10.4 the file is not at that path; the 26.10.4 behaviour is observed only **[to be validated: source location in 26.10]** |
| Session ID | **Reused.** Both rows of `nextflow log` carry the same session ID (`2816c414-…` on 26.10.4, `c2170367-…` on 25.10.9). `.nextflow/cache/` holds one directory, named after it. | `-resume` with no ID, or `last`, takes the last session ID in the history ([`ConfigBuilder.groovy` L536–L550 at v25.10.9](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/config/ConfigBuilder.groovy#L536-L550)). The session then takes that ID as its `uniqueId`; a launch without resume gets `NXF_UUID` or a random UUID ([`Session.groovy` L374–L379 at v25.10.9](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/Session.groovy#L374-L379); [L431–L435 at v26.10.4](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/groovy/nextflow/Session.groovy#L431-L435)). Docs: "Nextflow resumes from the previous run by default" ([cache and resume](https://docs.seqera.io/nextflow/cache-and-resume), "Resuming from a specific run") |
| History | Each launch appends one line to `.nextflow/history`: the run name, the session ID, the revision and the command line. | [`ScriptRunner.groovy` L281–L287 at v25.10.9](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/script/ScriptRunner.groovy#L281-L287) ([L281–L285 at v26.10.4](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/groovy/nextflow/script/ScriptRunner.groovy#L281-L285)) |
| Launch directory | **The same one is required.** From another directory, `-resume <session-id> -w <old work dir>` fails with "Can't find a run with the specified id: … -- Execution can't be resumed", exit 1. | The resume check looks the ID up in the history ([`ScriptRunner.groovy` L282–L284 at v25.10.9](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/script/ScriptRunner.groovy#L282-L284)). The history and the cache sit under `NXF_CACHE_DIR`, by default `.nextflow` in the launch directory ([`Const.groovy` L70](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nf-commons/src/main/nextflow/Const.groovy#L70); [`HistoryFile.groovy` L38](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/util/HistoryFile.groovy#L38); [`DefaultCacheStore.groovy` L67](https://github.com/nextflow-io/nextflow/blob/v25.10.9/modules/nextflow/src/main/groovy/nextflow/cache/DefaultCacheStore.groovy#L67)). Docs: "The default cache store uses the `.nextflow/cache` directory, relative to the launch directory" |

**Consequence for #32 (option B).**
- A Nextflow resume is a new *run* (new run name, new history line) of the same *session* (same session ID, same task cache), in the same launch directory.
- A child run per resume therefore matches Nextflow's own model, provided Spectio records both IDs:
  - the run name, unique per launch;
  - the session ID, shared by the whole lineage.
- Spectio could also set the session ID of a first launch itself, through `NXF_UUID` (`Session.groovy` L379 above).

### Snakemake

Observed on 9.27.1, with `gate_qc_then_resume` (`--until qc_report`, then a plain rerun in the same directory):

| What | Observation | Source |
|---|---|---|
| Run identity | **Each invocation has its own random `workflow_id`**: `486ceb8b-…` for the first run, then `8e78c667-…` for the rerun. It is printed in the log header ("Workflow ID") and sent to logger plugins in the `WORKFLOW_STARTED` event. Nothing derives it from, or links it to, the previous invocation. | `"workflow_id": uuid.uuid4()` in `info_header` ([`workflow.py` L303 at v9.27.1](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/workflow.py#L303)), emitted with `LogEvent.WORKFLOW_STARTED` ([L1292–L1299](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/workflow.py#L1292-L1299)); printed by [`logging.py` L168](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/logging.py#L168) |
| Per-invocation state | One log file per invocation, named by its start time (`.snakemake/log/2026-10-27T215502.610861.snakemake.log`, then `…T215506…`). The per-output records in `.snakemake/metadata/` have no run or workflow ID. Their keys are `code`, `conda_env`, `container_img_url`, `endtime`, `external_jobid`, `incomplete`, `input`, `input_checksums`, `job_hash`, `log`, `params`, `record_format_version`, `rule`, `shellcmd`, `software_stack_hash` and `starttime`. | observed |
| Job identity | Stable across invocations: a job's UUID is a UUID5 of its rule name and wildcards. | [`jobs.py` L1202–L1207](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/jobs.py#L1202-L1207), [`common/__init__.py` L268–L269](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/common/__init__.py#L268-L269) at v9.27.1 |
| What links the runs | Only the working directory: its outputs and their metadata decide what reruns. | observed (`gate_*` rows above) |

**Consequence for #32.**
- A Snakemake rerun is a new invocation with a new `workflow_id`, and nothing in the engine records a lineage.
- With option B, a child run per resume maps one-to-one onto Snakemake invocations, and Spectio has to record the parent link and the shared directory itself.
- Option A (the same run continues) would have to hide two `workflow_id`s behind one Spectio run on Snakemake, and two run names on Nextflow.

## nf-core/rnaseq and nf-core/sarek: not run

- **Not the blocker: Docker.** `dockerd` starts in this session (Docker 29.9.2, cgroup v1).
- **The blocker: the cost**, measured on CI runners in [corpus-ci-2026-10-27](corpus-ci-2026-10-27.md):
  - **nf-core/rnaseq 3.27.0:** 18–23 min per full run. The lowest free disk was 23.0 GB on a runner that starts with about 46 GB free, so the run used about 23 GB. This session has 26 GB free.
  - **nf-core/sarek 3.10.0:** 9 min. The lowest free disk was 27.3 GB on the same kind of runner.
  - **Missing tooling.** `tests/pipelines/real/run_corpus.py` cannot stop at a gate or resume yet: it runs `-profile test,docker` once.
- **Total.** A stop run, a resume run and the gate configs for both pipelines would take well over the 20 minutes set for this step. So this step did not run them.
- **Where they should run instead.** `pipelines-real.yml` already runs rnaseq and sarek nightly. Two changes would turn those entries into the gate check, at about the cost of one full run each:
  - give `run_corpus.py` a per-entry `gate` key: a generated `ext.when = false` config for the processes after alignment, then `-resume` without it, recording the cached-task count and the exit code of each run;
  - use it in those two nightly entries.

  No new job is needed. This is open item 1.

## Open items

1. **Gate stop-and-resume on rnaseq and sarek.** Add `gate` support to `run_corpus.py` and use it in their nightly entries (above). This closes CH-016 ([inbox #28](../reviews/inbox.md#28-assumed-engine-bridges-runner-and-scheduler)). Tracked as [inbox #47](../reviews/inbox.md#47-assumed-the-rnaseq-and-sarek-gate-stop-and-resume-check-moves-to-the-nightly-corpus).
2. **Job arrays in the `slurm` profile** (`array = 20` on ALIGN): not provable with the local executor. To be proven in T3 on sind.
3. **`fanout_stress`** (about 12 000 ALIGN tasks, nightly): not run here. It has no golden fixture, which `--golden check` allows for nightly scenarios.
4. **Nextflow 25.04.8**, the supported floor (§1), passes and has fixtures, but has no CI leg in `pipelines-synthetic.yml`. Adding one costs about 5 min per run.
5. **`oom_real` on Snakemake**, and `oom_real` as a scenario: needs a memory limit that is actually enforced (Docker, SLURM or Kubernetes). To be proven in T3 (`OUT_OF_MEMORY`) and T4 (`OOMKilled`).
6. **The `k8s` profile** needs the shared `bin/` inside the pod (finding 3). T4 must solve it.
7. **Inbox #32.** The observations above support option B. The decision stays with Thomas.
