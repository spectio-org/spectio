# R2 · Fact verification and open validations

**Step page:** [R2](../progress/W1/R2.md)

**Round:** R2 · Fact verification · **Date:** 2026-10-26 · **Found by:** fact-checker (three runs) · **Status of the round:** waiting for triage (TRIAGE1)

**Scope.** Eight specs, checked in three parallel `/verify-claims` runs:
- **Run 1:** [schedulers-and-monitoring.md](../specs/schedulers-and-monitoring.md) and [synthesis.md](../specs/synthesis.md).
- **Run 2:** [architecture-plugins-and-packaging.md](../specs/architecture-plugins-and-packaging.md), [dev-environment-and-testing.md](../specs/dev-environment-and-testing.md) and [cli-and-shared-libraries.md](../specs/cli-and-shared-libraries.md).
- **Run 3:** [api-and-data-model.md](../specs/api-and-data-model.md), [checking-scenarios.md](../specs/checking-scenarios.md) and [admin-and-operations.md](../specs/admin-and-operations.md).

All three runs returned output; none failed. Part B then lists every `[to be validated]` marker still in `docs/specs`, including those in specs outside this scope.

**Sources and commits read.** The full list is in [verification-2026-10-26.md](verification-2026-10-26.md#sources-and-commits-read). The main ones:
- **Engines:** Nextflow `114f1fe` (26.10.x) and Snakemake `1c67a66` (9.27.x).
- **Snakemake plugins:**
  - `snakemake-executor-plugin-slurm` `8c2af56` (v2.8.0);
  - `-kubernetes` `d5f720e`;
  - `-kueue` `c09bf0d` (0.1.0).
- **Schedulers and tools:**
  - Slurm `slurm-26-05-5-1` and `slurm-25-11-8-1`;
  - Kueue `c331366` and tags v0.13.0 to v0.20.0;
  - sind `0065750`.
- **depictio:** `0d1aa0a` (tag v1.19.2 is `e40ca79`).
- **Standards:**
  - WES OpenAPI 1.1.0;
  - CloudEvents `v1.0.2`;
  - sqlite.org/wal.html;
  - the Helm hooks page;
  - the uv Python-versions page.

Clones are under `/tmp/w1-scratch/`, all read on 2026-10-26.

**How the merge checked the findings.** Every blocker and major was checked again by the merge on 2026-10-26:
- the quoted spec passages were opened on `autopilot/integration`;
- the external evidence was read again in the reviewers' clones, or on the web for Helm, uv and PyPI.

All ten majors reproduced, so **none was dropped**. Two details were added during this check:
- **FC-005:** Snakemake raises its error only when the executor also has `can_transfer_local_files` false. That flag defaults to `False` (`snakemake_interface_executor_plugins/settings.py:75`), and the Kubernetes plugin does not set it, so the finding stands.
- **FC-007:** the plugin limits the prefix to `^[A-Za-z0-9_-]{1,50}$` (`__init__.py:483-492`). Spectio run IDs are `run_` plus a ULID ([api-and-data-model.md](../specs/api-and-data-model.md) §4), so `spectio-head-run_<ULID>` is 43 characters and fits.

## Summary

| Severity | Count |
|---|---|
| Blocker | 0 |
| Major | 9 |
| Minor | 28 |
| **Total** | **37** |
| Dropped (could not be reproduced) | 0 |

**Merges and ID changes.** The three runs reported 38 findings: 10 majors and 28 minors.
- **Merged:**
  - run 1 FC-103 and run 3 FC-302 → **FC-001** (Snakemake drains on SIGTERM);
  - run 1 FC-112 and run 3 FC-307 → **FC-010** (SQLite floor). The floor part of run 2 FC-202 is folded into FC-010 too.
- **Added:** **FC-037** collects the table corrections that had no finding of their own, so that triage can accept them as one block.
- **Renumbered:** all IDs run in one sequence. The table below gives each run's original IDs.

**Verification totals** (206 claims): 153 true, 40 partly, 8 wrong and 5 unverifiable. Details are in [verification-2026-10-26.md](verification-2026-10-26.md#totals).

**The five findings that matter most:**
1. **FC-001.** Snakemake already drains on SIGTERM, and SIGINT throws away running cluster jobs. A plain `scancel` gives a head job only `KillWait` (30 s by default) before SIGKILL. The pause, stage-boundary and cancel designs in three specs use the wrong signal, and a head can die without cancelling its task jobs.
2. **FC-006 and FC-007.** `squeue --name` and `sacct --name` match exact names only. Runner-restart reconciliation (`--name 'spectio-*'`) finds nothing, so the "no run is lost" guarantee fails. The Snakemake task-job lookup also misses every task job, because the plugin names them `<prefix>_<uuid>`.
3. **FC-002.** The generated `ext.when` stop closure replaces a pipeline's own `ext.when`. nf-core/rnaseq 3.27.0 already sets one on MARKDUPLICATES, so a live check would change what the pipeline does.
4. **FC-003.** `depictio-cli ingest --user` requires depictio's instance-wide provisioning key. As written, the runner on the cluster would need that long-lived secret, which breaks the scoped-token rule.
5. **FC-005.** Snakemake's Kubernetes executor *requires* object storage (`implies_no_shared_fs=True`). The chart's "RWX or S3" choice only exists for Nextflow, so every Snakemake run on Kubernetes needs S3 credentials and a storage prefix.

**Duplicates of earlier rounds.** None of these findings repeats an open finding in [R8b-depictio-tooling.md](R8b-depictio-tooling.md) or [R12-ui-scenarios.md](R12-ui-scenarios.md). Several are related:
- **FC-008:** the concrete failure behind DEP-T-010.
- **FC-011:** DEP-T-031 sets the citation policy for depictio tags.
- **FC-020:** feeds UX-109 and UX-113.
- **FC-033:** column naming stays with UX-101.

**Overlap with R1, written in parallel.** [R1-consistency.md](R1-consistency.md) was written on the same day and is not triaged yet. R2's findings are kept, because they bring primary-source evidence that R1 does not have. Triage should merge each pair so that every problem is applied once:

| R2 | R1 | Relation | Suggested triage |
|---|---|---|---|
| FC-006, FC-007 | SR-037 | **Same problem.** R1 marks "no wildcards" **[to be validated on sind]**; R2 settles it from `src/squeue/print.c:3263-3275` (exact, case-insensitive match) and the slurmdbd query | Accept one of the two, citing R2's sources; the proposals agree (`spectio-head-<run_id>`, client-side prefix filter) |
| FC-021 | SR-017 | **Same sentence** (synthesis §10 risk 2, Tower-era abort). SR-017 is wider: testable buffer bounds | Apply SR-017; FC-021's text covers only the risk-2 sentence |
| FC-014 | SR-027 | **Overlap.** Both move keyring to `[keyring]`; SR-027 also lists YAML, pydantic-settings and Copier | Apply SR-027's allow-list, with FC-014's dependency evidence |
| FC-034 | SR-017 | FC-034 resolves the "reading declared outputs through the handler" marker that SR-017 rewords around (checking §11.1) | Apply FC-034 first; SR-017 then needs no workaround wording |
| FC-001 | SR-018, SR-008 | **Related.** SR-018 asks for `:pause` vs `:stop`; SR-008 asks CLI head job vs Python API. FC-001 gives the signal for each: SIGTERM drains Snakemake, Nextflow has no drain | Decide SR-008 first; FC-001's text holds for the CLI head job |
| FC-002 | SR-011 | **Complementary.** SR-011 picks `ext.when` as the only Nextflow boundary; FC-002 says the generated value must wrap the pipeline's own `ext.when`. FC-002 also gives the nf-core source that SR-011 asks for | Apply both |

## Findings table

| ID | Severity | Title | Specs touched | Run IDs |
|---|---|---|---|---|
| FC-001 | major | Snakemake drains on SIGTERM; SIGINT and a plain `scancel` lose running work | synthesis, schedulers-and-monitoring, checking-scenarios | FC-103, FC-302 |
| FC-002 | major | The generated `ext.when` overrides a pipeline's own `ext.when` | checking-scenarios (also ui-spec §5.1, synthesis §5ter) | FC-303 |
| FC-003 | major | `depictio-cli ingest --user` needs the provisioning key, not a short-lived credential | api-and-data-model, admin-and-operations, depictio-ecosystem-reuse | FC-301 |
| FC-004 | major | `uv tool install` does not guarantee a uv-managed Python or its SQLite | architecture-plugins-and-packaging, dev-environment-and-testing | FC-202 |
| FC-005 | major | Snakemake's Kubernetes executor requires remote storage | architecture-plugins-and-packaging, dev-environment-and-testing | FC-201 |
| FC-006 | major | `squeue --name` takes no wildcards: restart reconciliation finds no head jobs | schedulers-and-monitoring | FC-101 |
| FC-007 | major | The Snakemake job-name lookup cannot work and collides with head-job names | schedulers-and-monitoring | FC-102 |
| FC-008 | major | A pre-install migrate hook runs before the chart's ConfigMap and Secrets exist | architecture-plugins-and-packaging | FC-203 |
| FC-009 | major | `snakemake-executor-plugin-kueue` is an unmaintained 0.1.0 prototype | dev-environment-and-testing | FC-204 |
| FC-010 | minor | The SQLite version floor rejects fixed backports and does not say which library is checked | synthesis, architecture-plugins-and-packaging, api-and-data-model, admin-and-operations | FC-112, FC-307 (part of FC-202) |
| FC-011 | minor | Counts and versions that do not match their sources | api-and-data-model, checking-scenarios, admin-and-operations | FC-310 |
| FC-012 | minor | Version floors are missing for five external features | schedulers-and-monitoring, synthesis | FC-105 |
| FC-013 | minor | Python and Node version facts went stale this month | architecture-plugins-and-packaging, dev-environment-and-testing | FC-207 |
| FC-014 | minor | The `keyring:` token source breaks the "pure-Python base install" claim | cli-and-shared-libraries, architecture-plugins-and-packaging | FC-209 |
| FC-015 | minor | The SLURM plugin's default status command is not driven by `MinJobAge` | schedulers-and-monitoring | FC-104 |
| FC-016 | minor | Slurm JSON field names: `state_reason`, and usage is per step | schedulers-and-monitoring | FC-106 |
| FC-017 | minor | `AssocGrpCPULimit` is not a Slurm reason; the string is `AssocGrpCpuLimit` | schedulers-and-monitoring | FC-107 |
| FC-018 | minor | Kubernetes failure reasons are in `state`, not `lastState`; the Job reason is always `BackoffLimitExceeded` | schedulers-and-monitoring | FC-108 |
| FC-019 | minor | The `-with-weblog` marker can be resolved | synthesis | FC-109 |
| FC-020 | minor | Cache-breaking upgrades hit some processes in 25.10, 26.04 and 26.10 | synthesis | FC-110 |
| FC-021 | minor | "A server outage aborts the run" is about `nf-tower`, not Spectio | synthesis | FC-111 |
| FC-022 | minor | The `[saml]` system dependency depends on a library not chosen yet | architecture-plugins-and-packaging | FC-208 |
| FC-023 | minor | Snakemake also has a scheduler plugin interface | architecture-plugins-and-packaging | FC-210 |
| FC-024 | minor | respx mocks HTTP; it does not record it | architecture-plugins-and-packaging | FC-211 |
| FC-025 | minor | "Mantine 7" is two majors behind, and the import map makes the major part of the plugin contract | architecture-plugins-and-packaging | FC-212 |
| FC-026 | minor | depictio retries five specific 5xx codes, not every 5xx | cli-and-shared-libraries | FC-213 |
| FC-027 | minor | sind ships slurmrestd only in its 26.05 images | dev-environment-and-testing | FC-205 |
| FC-028 | minor | Megatest outputs come from full-size public data, not nf-core/test-datasets | dev-environment-and-testing | FC-206 |
| FC-029 | minor | Current Kueue recommends Kubernetes ≥ 1.34; Spectio targets ≥ 1.33 | dev-environment-and-testing | FC-214 |
| FC-030 | minor | Nextflow install: the real asset names and hosts | dev-environment-and-testing | FC-215 |
| FC-031 | minor | Cloudflare's preview access policy does not cover the production URL | dev-environment-and-testing | FC-216 |
| FC-032 | minor | `--quiet` also hides `JOB_INFO` from logger plugins; plain `-q` suppresses `JOB_FINISHED` | checking-scenarios | FC-304 |
| FC-033 | minor | MultiQC on a single file works; start-up dominates, so batch the files | checking-scenarios | FC-305 |
| FC-034 | minor | Two Nextflow `[to be validated]` markers can be resolved from the source | checking-scenarios | FC-306 |
| FC-035 | minor | The CloudEvents envelope omits the required `specversion` | api-and-data-model | FC-308 |
| FC-036 | minor | Wording of standards: `RateLimit-*` and WES `workflow_type` | api-and-data-model | FC-309 |
| FC-037 | minor | Table corrections with no finding of their own (batch) | schedulers-and-monitoring, synthesis, architecture-plugins-and-packaging, dev-environment-and-testing, api-and-data-model | table rows |

**Order.** Findings are ranked by severity, then by the number of specs they touch. FC-006 comes before FC-007 because FC-007 builds on it. FC-037 is a batch of unrelated one-line corrections, so it comes last even though it touches five specs.

---

## Part A · Findings

### Majors

### FC-001 · major · Snakemake drains on SIGTERM; SIGINT and a plain `scancel` lose running work

- **Where:**
  - synthesis.md §5ter.3 (Unplanned pause, l.232) and §8 (Cancellation, l.370);
  - schedulers-and-monitoring.md §2 L1 (`scancel`, l.54) and §3.1;
  - checking-scenarios.md §11.3 (Snakemake bullet, l.325).
- **Evidence:**
  - **The specs:**
    - "SIGINT to Snakemake (which cancels cluster jobs via `cancel_jobs`) … No native 'finish running tasks without submitting new ones' mode **[to be validated]**" (synthesis §5ter.3);
    - "Cancellation: `scancel` or SIGTERM **[to be validated in practice]**" (synthesis §8);
    - "no conditional `--until` exists **[to be validated]**, so Spectio stops the run (SIGINT) once the last job of the stage has finished; running jobs of later stages are lost" (checking §11.3).
  - **Snakemake** `1c67a66`, `src/snakemake/scheduling/job_scheduler.py`:
    - `:171` registers `signal.signal(signal.SIGTERM, self.exit_gracefully)`;
    - `:574-577` sets `_user_kill = "graceful"`;
    - `:241-245` logs "Will exit after finishing currently running jobs (scheduler)." and keeps looping until nothing runs;
    - `:398-403`: on `KeyboardInterrupt` (SIGINT) it logs "Terminating processes on user request" and calls `self._executor.cancel()`;
    - `cli.py:893-915`: `--until` and `--omit-from` are static, so "no conditional `--until`" is true.
  - **Nextflow** `114f1fe`: `Session.groovy:609-615` maps TERM and HUP to `abort()`, so there is no drain.
  - **Slurm** 26.05.5:
    - `scancel.1:375-379`: without `--signal`, scancel sends SIGCONT, then SIGTERM, "then wait the KillWait duration … and finally … SIGKILL"; `KillWait` defaults to 30 s (`slurm.conf.5:2396-2401`);
    - `scancel.1:182-184`: with `--signal`, the job is not terminated;
    - `scancel.1:65-75`: "By default, signals other than SIGKILL are not sent to the batch step"; use `--batch` or `--full`.
  - The merge re-read all of these lines in the clones.
- **Problem:**
  - The pause design and the stage-boundary stop use SIGINT. SIGINT cancels running cluster jobs and loses their work. SIGTERM, the native drain, is exactly what `pause_after_stage` needs.
  - Cancelling a head job with a plain `scancel` gives the engine only `KillWait` (often 30 s). A draining Snakemake is then SIGKILLed. A Nextflow head may die before it cancels its own task jobs, which leaves orphan jobs.
- **Proposal:**
  - **synthesis §5ter.3 "Unplanned" bullet:** "**Unplanned**: Snakemake drains on SIGTERM (it submits nothing new and exits once running jobs finish, `job_scheduler.py:171, 241-245`, Snakemake `1c67a66`); SIGINT cancels running cluster jobs. Nextflow has no drain: SIGTERM or SIGINT aborts the run. On SLURM the launcher signals the head job with `scancel --signal=TERM --full <head>`, which reaches the engine without terminating the job; a plain `scancel` follows SIGTERM with SIGKILL after `KillWait` (default 30 s)."
  - **synthesis §8:** "Cancellation: `scancel --signal=TERM --full <head>` (or SIGTERM to a local head), then a plain `scancel` only if the head is still alive after a grace period; any task jobs left behind are cancelled from `scheduler_jobs`."
  - **schedulers §2 L1:** change `scancel` to "`scancel --signal=TERM --full`, then `scancel`".
  - **checking §11.3 Snakemake bullet:** "**Snakemake**: there is no conditional `--until` (`cli.py:893-915`). Once the last job of the stage has finished, the runner sends **SIGTERM** to the Snakemake process. Snakemake then schedules no new jobs and exits after the running ones finish (`job_scheduler.py:171, 241-245, 574-577`; Snakemake `1c67a66`). Jobs of later stages that were already running complete and are reused on resume."
  - **Tests:** add one sind test per engine (spike T3): the head job is drained by signal, then cancelled after the grace period.
- **Found by:** fact-checker (run 1, run 3)
- **Status:** open

### FC-002 · major · The generated `ext.when` overrides a pipeline's own `ext.when` (nf-core/rnaseq 3.27.0 already sets one)

- **Where:** checking-scenarios.md §11.3, Nextflow bullet (l.324). The static boundary `ext.when = false` cited at l.323 has the same problem ([ui-spec.md](../specs/ui-spec.md) §5.1, [synthesis.md](../specs/synthesis.md) §5ter).
- **Evidence:**
  - **The spec:** "the generated config sets `ext.when` on later stages to a closure that tests a stop file … That nf-core modules evaluate such a closure per task, at task creation, is **[to be validated]**" (checking §11.3).
  - **Per-task evaluation is true** in Nextflow `114f1fe`:
    - `TaskProcessor.groovy:692-694`: `invokeTask` calls `checkWhenGuard(task)` before submitting; see also `:1908-1913`;
    - `TaskConfig.groovy:132-134` binds the `ext` LazyMap to the task context;
    - nf-core modules use `when: task.ext.when == null || task.ext.when` (`modules/nf-core/star/align/main.nf:38-39`).
  - **The pipeline already sets one:** nf-core/rnaseq 3.27.0, `conf/modules/markduplicates.config:30`: `ext.when = { !params.use_rustqc }`. The merge re-read this line.
  - **Parser:** `file()` inside a config closure passes the v2 config scope check (`nf-lang/.../VariableScopeVisitor.java:124-127`; v2 is the default parser, `NF.groovy:32`). Whether it works at runtime was not tested.
- **Problem:**
  - A `withName` override with `ext.when = { !file(stop).exists() }` replaces the pipeline's own condition. Until the stop file exists, MARKDUPLICATES would then run even when `use_rustqc` is true, which changes what the pipeline does.
  - The static `ext.when = false` boundary also overwrites the original value, but there it only matters for processes that are meant to be skipped anyway.
- **Proposal:**
  - Replace the last sentence of the bullet with: "Nextflow evaluates `when` once per task, before submission (`TaskProcessor.groovy:692-694`, nextflow `114f1fe`). Because pipelines set `ext.when` themselves (nf-core/rnaseq 3.27.0 `conf/modules/markduplicates.config:30`), the generated config must wrap the resolved original value (`{ (<original>) && !file(…).exists() }`), never replace it. That this works at runtime under the v2 config parser is **[to be validated]** on `nf-toy` and on rnaseq MARKDUPLICATES."
  - Say where the runner reads the original value from: `nextflow config -flat` on the launch config.
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-003 · major · `depictio-cli ingest --user` needs depictio's instance provisioning key, not a short-lived credential

- **Where:** api-and-data-model.md §13.3 step 1 (l.320). It conflicts with api §13.1 (Service identity, l.296) and with admin-and-operations.md §2.3 (l.108).
- **Evidence:**
  - **The specs:**
    - "runs `depictio-cli ingest <outdir> … --user <owner email> …`, with a short-lived credential from the server" (api §13.3);
    - "runners get a scoped token, never depictio's S3 root secret" (api §13.1);
    - "Spectio keeps that call only inside the depictio sink plugin" (admin §2.3).
  - **depictio** `0d1aa0a`, `depictio/cli/cli/commands/run.py:1637-1643`: `if user and not provisioning_key:` → "--user requires --provisioning-key (or the DEPICTIO_AUTH_PROVISIONING_API_KEY environment variable)." The help text at `:3104-3108` says the same. The merge re-read these lines.
- **Problem:** the command as written only works if the runner holds depictio's provisioning key, a long-lived secret for the whole instance, on the cluster. That breaks two rules: the scoped-token rule, and keeping the provisioning call "only inside the sink plugin". Implementers will either leak the key to runners or find that the hand-off fails.
- **Proposal:**
  - Rewrite step 1:
    - the server-side sink plugin provisions (or looks up) the owner through depictio's provisioning API and obtains a token for that user;
    - the runner then runs `depictio-cli ingest` **without** `--user`, with a CLI config that carries that per-user token.
  - In [depictio-ecosystem-reuse.md](../specs/depictio-ecosystem-reuse.md) §3, add a request for run-scoped, short-lived depictio tokens, as [depictio-auth-2026-10-26.md](../research/depictio-auth-2026-10-26.md) §5 already suggests.
  - The hand-off is post-0.1 ([decision log](../decisions/log.md), 2026-10-26, "MVP scope"), so triage may lower the urgency.
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-004 · major · `uv tool install` does not guarantee a uv-managed Python, so the SQLite floor is not guaranteed either

- **Where:** architecture-plugins-and-packaging.md §7.3 (l.331, l.335); dev-environment-and-testing.md §1 (l.43).
- **Evidence:**
  - **The spec:** "`uv tool install` brings its own managed Python, which also embeds a recent SQLite (≥ 3.51.3, checked at start)." (A §7.3)
  - **uv** ([Python versions](https://docs.astral.sh/uv/concepts/python-versions/), read again by the merge on 2026-10-26): "By default, the python-preference is set to managed which prefers managed Python installations over system Python installations. However, system Python installations are still preferred over downloading a managed Python version."
  - **uv 0.13.5:** the CLI reference has `uv tool install --managed-python`.
  - **python-build-standalone** `a3f2146` (`pythonbuild/downloads.json`) embeds SQLite 3.53.1.
- **Problem:** on a laptop or login node that already has Python ≥ 3.11, `uv tool install "spectio[server]"` uses the system interpreter and its SQLite, which is often older than 3.51.3. The start-up check then refuses to run, or users hit the WAL bug.
- **Proposal:**
  - Install with `uv tool install --managed-python "spectio[server]"`.
  - Replace the sentence with: "`uv tool install --managed-python` installs into a uv-managed Python, which embeds a recent SQLite; without the flag, uv uses a compatible system Python and its SQLite."
  - The version check itself is FC-010.
  - The SQLite pin in D §1 l.43 is true for current builds and needs no change.
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-005 · major · Snakemake's Kubernetes executor requires remote storage; the RWX option does not apply to it

- **Where:** architecture-plugins-and-packaging.md §7.5 (l.373-374); dev-environment-and-testing.md §4.2 (`k8s-mini`).
- **Evidence:**
  - **The spec:** "Snakemake's Kubernetes executor can use a remote storage plugin (S3) as the default storage provider instead of a shared file system **[to be validated against the executor plugin's docs]**." / "The chart exposes both options." (A §7.5)
  - **snakemake-executor-plugin-kubernetes** `d5f720e`, `__init__.py:120-125`: `implies_no_shared_fs=True` and `auto_deploy_default_storage_provider=True`. The plugin does not set `can_transfer_local_files`, whose default is `False` (`snakemake_interface_executor_plugins/settings.py:75`).
  - **Snakemake** `1c67a66`:
    - `src/snakemake/api.py:546-548` then sets `shared_fs_usage = frozenset()`;
    - `:559-575` raises `ApiError`: "If no shared filesystem is assumed for input and output files, a default storage provider (--default-storage-provider) and default storage prefix (--default-storage-prefix) has to be set."
  - **Kueue executor:** it sets the same flag (wheel 0.1.0, `__init__.py:56`).
  - The merge re-read the plugin and the Snakemake lines.
- **Problem:**
  - For Snakemake on Kubernetes, object storage is mandatory, not one of two options. An RWX PVC alone fails at startup.
  - The chart's "both options" and the `k8s-rwx` profile only serve Nextflow.
  - Every Snakemake run on Kubernetes needs S3 credentials and a storage prefix: in the runner sub-chart, in the `launcher-kubernetes` plugin and in Snakemake's generated config. This bears on open question §11.3.
- **Proposal:**
  - Replace l.373 with: "Snakemake's Kubernetes executor assumes no shared file system (`implies_no_shared_fs=True`, snakemake-executor-plugin-kubernetes `d5f720e`): every run needs `--default-storage-provider` and `--default-storage-prefix` (e.g. `s3` and a bucket prefix), which the runner sub-chart provides. An RWX volume serves Nextflow only."
  - Add an S3-backed Snakemake scenario (SeaweedFS in kind) to the `k8s-mini` profile in dev-environment-and-testing.md §4.2.
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-006 · major · `squeue --name` does not take wildcards, so runner-restart reconciliation finds no head jobs

- **Where:** schedulers-and-monitoring.md §3.1 (Runner restart, l.67).
- **Evidence:**
  - **The spec:** "running head jobs from `squeue --me --name 'spectio-*'`, finished ones from `sacct`. No run is lost".
  - **squeue:** Slurm 26.05.5 `squeue.1:1423-1425`: "Request jobs or job steps having one of the specified names. The list consists of a comma separated list of job names." The filter is an exact, case-insensitive match: `src/squeue/print.c:3263-3275` (`xstrcasecmp(name, job->name) == 0`). The merge re-read these lines.
  - **sacct:** `--name` is exact too (slurmdbd `as_mysql_jobacct_process.c:1608`: `t1.job_name='%s'`).
- **Problem:** the query only matches a job literally named `spectio-*`. After a restart the runner sees no running head jobs, and the "no run is lost" guarantee (synthesis risk register) fails.
- **Proposal:**
  - Replace the sentence with: "When a runner restarts, it reconciles: it lists the user's jobs with `squeue --me --json` and keeps those whose name starts with `spectio-head-` (filtered client-side, since `--name` only matches exact names), then reads finished head jobs with `sacct --json -j <ids>` for the IDs stored in `scheduler_jobs`."
  - The prefix is `spectio-head-` rather than `spectio-` because of FC-007.
  - Add one sind conformance test that restarts a runner while a head job runs (spike T3).
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-007 · major · The Snakemake job-name lookup cannot work as written, and it collides with the head-job names

- **Where:** schedulers-and-monitoring.md §3.4 (Snakemake SLURM row, l.102); §3.1 (head job named `spectio-<run_id>`).
- **Evidence:**
  - **The spec:** "Spectio sets `--slurm-jobname-prefix spectio-<run_id>`, then `sacct --name` / `squeue --name`".
  - **Plugin** v2.8.0, `__init__.py`:
    - `:493-495`: `self.run_uuid = "_".join([jobname_prefix, self.run_uuid])`, so every task job is named `spectio-<run_id>_<uuid4>`;
    - `:473`: the UUID is random per Snakemake invocation;
    - `:496`: it appears only in the log line `SLURM run ID: …`;
    - `:483-492`: the prefix must match `^[A-Za-z0-9_-]{1,50}$`.
  - **`--name`** is an exact match (FC-006).
  - **Version:** the prefix option needs plugin ≥ 2.2.0 (plugin CHANGELOG l.133-138).
  - The merge re-read `:470-497`.
- **Problem:**
  - `sacct --name spectio-<run_id>` and `squeue --name spectio-<run_id>` return nothing for task jobs.
  - The same names do return the head job, so a lookup can attach the head job to task attempts.
  - A client-side `spectio-` prefix filter (FC-006) would also catch every Snakemake task job.
- **Proposal:**
  - Replace the §3.4 Snakemake key cell with: "job name = `<prefix>_<run UUID>`. Spectio sets `--slurm-jobname-prefix spectio-<run_id>` (plugin ≥ 2.2.0) and reads the full name from the `SLURM run ID: …` line the logger receives, then queries `sacct --name <full name>` / `squeue --name <full name>` (exact match). The comment `rule_<rule>_wildcards_<…>` maps a job to the rule."
  - In §3.1, name head jobs `spectio-head-<run_id>` (43 characters with a `run_` ULID) and filter on `spectio-head-`, so task jobs never match.
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-008 · major · A pre-install migrate hook runs before the chart's ConfigMap and Secrets exist

- **Where:** architecture-plugins-and-packaging.md §7.5 (l.365, l.367); §7.2 table (l.308).
- **Evidence:**
  - **The spec:** "migrate Job as a Helm pre-install / pre-upgrade hook" and "a ConfigMap rendered from `values.yaml` into `spectio.toml`, and Secrets for keys" (§7.5).
  - **Helm** ([chart hooks](https://helm.sh/docs/topics/charts_hooks/), read again by the merge on 2026-10-26):
    - pre-install "Executes after templates are rendered, but before any resources are created in Kubernetes";
    - "The resources that a hook creates are currently not tracked or managed as part of the release."
- **Problem:**
  - On a first install, the migrate Job cannot mount the ConfigMap (`DATABASE_URL`, config) or the key Secrets, because they do not exist yet. `helm install` then fails or hangs on the hook.
  - Making those resources hooks too takes them out of release management.
  - DEP-T-010 ([R8b](R8b-depictio-tooling.md)) says the chart has no CI. This finding is the concrete failure that CI would catch, not a duplicate.
- **Proposal:**
  - Replace l.365 with: "migrate Job as a Helm pre-install / pre-upgrade hook. The ConfigMap and Secret it reads are rendered as hooks with a lower `helm.sh/hook-weight` (or the Job reads only an existing Secret named in values), because pre-install hooks run before the chart's other resources are created."
  - Add a first-install case to the chart CI that DEP-T-010 asks for.
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-009 · major · `snakemake-executor-plugin-kueue` is an unmaintained 0.1.0 prototype

- **Where:** dev-environment-and-testing.md §1 (l.48), §0.1 (l.13), §5 matrix (l.133: snakemake 9 × `k8s-kueue`).
- **Evidence:**
  - **The spec:** "Snakemake | 9.x + `snakemake-executor-plugin-slurm`, `-kubernetes`, `-kueue` …" (D §1).
  - **PyPI:** version 0.1.0 is the only release, uploaded 2024-01-03 (the merge checked the PyPI JSON again on 2026-10-26).
  - **Repository:** HEAD `c09bf0d` is dated 2024-03-21.
  - **Wheel metadata:** it says "**under development** note that the base container is a custom build under my namespace (`vanessa`)". It declares no `snakemake-interface-executor-plugins` requirement and pins `kubernetes <29`.
- **Problem:**
  - The matrix cell "snakemake 9 × k8s-kueue", and the claim that it is "tested against the real tool at a pinned version", rest on a prototype.
  - Nothing shows that it works with Snakemake 9.27 or a current Kueue (v0.20.3) **[to be validated]**.
  - If it does not, Snakemake on Kueue needs another path, for example the `kubernetes` executor with Kueue's pod integration **[to be validated]**.
- **Proposal:**
  - Replace the row with: "Snakemake | 9.x + `snakemake-executor-plugin-slurm`, `-kubernetes`, plus `snakemake-logger-plugin-spectio` (ours); `-kueue` (0.1.0, unmaintained since 2024-03) only if spike D2 shows it runs on Snakemake 9 **[to be validated]**".
  - Until then, mark "snakemake × k8s-kueue" in §5 as pending a spike.
- **Found by:** fact-checker (run 2)
- **Status:** open

### Minors

### FC-010 · minor · The SQLite version floor rejects fixed backports and does not say which library is checked

- **Where:**
  - synthesis.md §7 (Storage) and §7ter;
  - architecture-plugins-and-packaging.md §7.3 (l.331);
  - api-and-data-model.md §7 (l.170);
  - admin-and-operations.md §3.5 (Database row).
- **Evidence:**
  - **The specs:** "Require SQLite ≥ 3.51.3 (WAL-reset bug fix)" (synthesis §7); "≥ 3.51.3, checked at start" (A §7.3); "SQLite (WAL, local disk, ≥ 3.51.3)" (api §7); "SQLite version ≥ 3.51.3" (admin §3.5).
  - **sqlite.org** ([wal.html](https://www.sqlite.org/wal.html) §11): the bug is present "from 3.7.0 … through 3.51.2. It is fixed in version 3.51.3 (2026-03-13) and later. Backports of the fix are available for some earlier releases: 3.44.6 and 3.50.7."
  - **This sandbox:** the system Python reports `sqlite3.sqlite_version` 3.45.1.
- **Problem:**
  - A plain `>= 3.51.3` check refuses distribution builds that carry the fix. It pushes those sites to the `apsw` fallback when they do not need it.
  - No spec says that the version that matters is the library Python loads, not a system `sqlite3` binary (see FC-004).
- **Proposal:**
  - State the rule once, in the owning spec, and link to it from the others. The owner is api-and-data-model.md §7 (storage), unless triage picks synthesis §7.
  - The rule: "SQLite with the WAL-reset fix: ≥ 3.51.3, or ≥ 3.50.7 / ≥ 3.44.6 in those series (https://www.sqlite.org/wal.html §11), checked on `sqlite3.sqlite_version` at start."
- **Found by:** fact-checker (run 1, run 2, run 3)
- **Status:** open

### FC-011 · minor · Counts and versions that do not match their sources

- **Where:** api-and-data-model.md §13.3; checking-scenarios.md §0 and §9; admin-and-operations.md header.
- **Evidence:**
  - **depictio templates:** "versioned templates for about 35 nf-core pipelines" (api §13.3). depictio `0d1aa0a` has 32 pipeline directories with 41 `template.yaml` files under `depictio/projects/nf-core/`.
  - **Bulk row:** "Bulk sample | 45 | … | yes (MultiQC)" (checking §9). differentialabundance, which is in the bulk list in §1, has no `multiqc` in `modules.json` or `docs/output.md` (default branch, 2026-10-26).
  - **Report counts:** "86 produce other HTML reports … 25 declare groups" (checking §0). These come from hand criteria; mechanical counts over the same files give 98 and 19. The data is in `docs/research/data/analysis.json`.
  - **depictio version:** "depictio v1.19.2 (commit `0d1aa0a`, 2026-10-23)" (admin header). Tag `v1.19.2` resolves to `e40ca79`; `0d1aa0a` is the later "Update CHANGELOG.md for v1.19.2" commit.
- **Problem:** these are small errors in numbers that readers will quote, and one coverage row is wrong for one pipeline.
- **Proposal:**
  - **api §13.3:** "versioned templates for 32 nf-core pipelines (41 templates at depictio `0d1aa0a`)".
  - **checking §9 bulk row:** "yes (MultiQC), except differentialabundance (table binding)".
  - **checking §0:** append "(counts from hand classification; data in `docs/research/data/`)".
  - **admin header:** "depictio `main` at `0d1aa0a` (2026-10-23), one commit after tag v1.19.2 (`e40ca79`)". The citation policy is DEP-T-031; this finding only corrects the text.
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-012 · minor · Version floors are missing for five external features

- **Where:**
  - schedulers-and-monitoring.md §1 (Nextflow · SLURM row; Snakemake · SLURM row) and §4 (Kueue visibility API);
  - synthesis.md §2ter (`--slurm-array-jobs`) and §2ter Consequences 2 (`--persistence-backend db`).
- **Evidence:**
  - **Nextflow:** `docs/reference/config/executor.mdx:76-84`: `executor.onlyJobState` is `AddedInVersion 26.04`. With it, `squeue` runs without `-u` or `-p` (`SlurmExecutor.groovy:163-166`).
  - **SLURM plugin CHANGELOG:** job-name prefix in 2.2.0 (l.133-138); job arrays in 2.6.0 (l.45-50).
  - **Snakemake CHANGELOG** l.283: database metadata storage in 9.17.0.
  - **Kueue** `apis/visibility/`: only `v1beta1` from v0.13.0 to v0.14.0; `v1beta2` added in v0.15.0; only `v1beta2` on `main` (`c331366`).
- **Problem:** Spectio targets Nextflow ≥ 25.10 and Snakemake ≥ 9. On older versions in that range these features are missing or use a different API path, so the runner would fail with no clear reason.
- **Proposal:**
  - **schedulers §1, Nextflow row:** "or `--only-job-state` without `-u`/`-p` (Nextflow ≥ 26.04, SLURM ≥ 24.05) when `executor.onlyJobState`".
  - **schedulers §1, Snakemake row:** add "job-name prefix needs plugin ≥ 2.2.0; job arrays ≥ 2.6.0".
  - **schedulers §4:** "That API is `/apis/visibility.kueue.x-k8s.io/v1beta2/…` on Kueue ≥ v0.15 (`v1beta1` on v0.9 to v0.14) …".
  - **synthesis §2ter:** "(`--persistence-backend db`, Snakemake ≥ 9.17)".
  - Have the runner's capability probe record these versions.
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-013 · minor · Python and Node version facts went stale this month

- **Where:** architecture-plugins-and-packaging.md §7.3 (l.331) and §4 (l.204); dev-environment-and-testing.md §1 (l.45).
- **Evidence:**
  - **The specs:** "Python 3.10 reaches end of life in October 2026"; "Python 3.11–3.14"; "Node.js | 22 LTS".
  - **[PEP 619](https://peps.python.org/pep-0619/):** "As of 2026-10-01, 3.10 has reached the end-of-life phase".
  - **[PEP 790](https://peps.python.org/pep-0790/):** 3.15.0 final was released on 2026-10-09.
  - **[Node schedule](https://github.com/nodejs/Release/blob/main/schedule.json):**
    - v22 in maintenance since 2025-10-21, end of life 2027-04-30;
    - v24 in maintenance from 2026-10-20;
    - v26 LTS from 2026-10-28.
- **Problem:** the scaffold's CI matrix leaves out the current CPython, and Node 22 reaches end of life during the planned alpha and beta.
- **Proposal:**
  - **A §7.3:** "Python 3.10 reached end of life on 2026-10-01 (PEP 619)."
  - **A §4:** "(Python 3.11–3.15 × supported SDK majors)".
  - **D §1:** "Node.js | 24 LTS (maintenance until 2028-04-30); move to 26 once it is Active LTS (2026-10-28)".
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-014 · minor · The `keyring:` token source breaks the "pure-Python base install" claim

- **Where:** cli-and-shared-libraries.md §0.3 (l.19), §3 (l.115) and §4 `bioplatform-client` (l.131); architecture-plugins-and-packaging.md §7.3 (l.335).
- **Evidence:**
  - **The specs:** "httpx, pydantic, typer, rich and nothing else" (C §0.3); "token: keyring:spectio/embl" (C §3); "It has no compiled dependencies beyond Pydantic's wheels" (A §7.3).
  - **PyPI metadata:**
    - `keyring` 25.7.0 requires `SecretStorage>=3.2; sys_platform == "linux"` and `jeepney`;
    - `secretstorage` 3.5.0 requires `cryptography>=2.0`.
- **Problem:**
  - Supporting `keyring:` in the base install adds a compiled dependency (`cryptography`) and four more packages.
  - HPC login nodes usually have no D-Bus Secret Service, so the keyring backend fails there anyway **[to be validated on EMBL login nodes]**.
- **Proposal:** "The base install depends on httpx, pydantic, typer and rich. The OS keyring is an optional extra (`spectio[keyring]`), because `keyring` on Linux pulls `SecretStorage` and `cryptography` and needs a D-Bus Secret Service; without it, tokens come from `file:` or `env:`."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-015 · minor · The Snakemake SLURM plugin's default status command is not driven by `MinJobAge`

- **Where:** schedulers-and-monitoring.md §1 (Snakemake · SLURM plugin row).
- **Evidence:**
  - **The spec:** "(sacct by default when `MinJobAge` is too low for squeue)".
  - **Plugin:** `PLG/__init__.py:77-97` returns `"sacct"` whenever `sacct` is on PATH, and `"squeue"` otherwise. `PLG/validation.py:157-168` only logs warnings that compare `MinJobAge` with 3× the initial interval.
- **Problem:** the spec suggests that squeue is the usual default. Spectio's load model then assumes the wrong command on most clusters.
- **Proposal:** "`--slurm-status-command`, `sacct` or `squeue` (default `sacct` whenever it is installed, else `squeue`; the plugin only warns when `MinJobAge` is below 3× the first-check interval)".
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-016 · minor · Slurm JSON field names: `state_reason`, and usage is per step

- **Where:** schedulers-and-monitoring.md §2 (L2, L3) and §5 (SLURM row).
- **Evidence:**
  - **The spec:** "`squeue --me --json` (state, `reason`, `start_time` …)" and "`sacct --json -j <ids>` (…`TotalCPU`, TRES requested and used: `mem` max RSS, `gres/gpu`, energy …)".
  - **data_parser** v0.0.45, `parsers.c`:
    - job info: field `state_reason` (`:10069`); `start_time` is "Time execution began, or is expected to begin" (`:10066`);
    - sacct job: `state/current`, `state/reason`, `time/total`, `tres/requested`, `tres/allocated` (`:9050-9063`);
    - usage is per step only: `steps[].tres.requested.max` / `tres/consumed/*` (`:9437-9444`) and `steps[].statistics.energy.consumed` (`:9417`).
- **Problem:** an implementer who reads `reason` or a job-level max RSS gets empty values, so efficiency and OOM sizing would be zero.
- **Proposal:**
  - **§2 L2:** "`squeue --me --json` (`job_state`, `state_reason`, `start_time`, which is the backfill estimate while pending)".
  - **§2 L3:** "`sacct --json -j <ids>` (job: `state.current`, `state.reason`, `exit_code`, `time.elapsed`, `time.total`, `tres.requested` / `tres.allocated`; per step: `tres.requested.max` for max RSS, `statistics.energy.consumed` when energy accounting is on)".
  - **§5:** use the same names.
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-017 · minor · `AssocGrpCPULimit` is not a Slurm reason; the string is `AssocGrpCpuLimit`

- **Where:** schedulers-and-monitoring.md §3.5 (pending reasons table).
- **Evidence:**
  - **The spec:** "`QOSMaxJobsPerUserLimit`, `AssocGrpCPULimit`, `AssocGrpMemLimit`, …".
  - **Slurm:** `src/common/job_state_reason.c:254` has `.str = "AssocGrpCpuLimit"`. The `CPUMinutes` and `CPURunMinutes` variants are upper-case (l.258-262).
- **Problem:** an exact-match mapping table would never match this reason.
- **Proposal:** "`QOSMaxJobsPerUserLimit`, `AssocGrpCpuLimit`, `AssocGrpMemLimit`, … (exact strings from `job_state_reason.c`; match them case-sensitively and fall back to the raw reason)".
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-018 · minor · Kubernetes failure reasons for Nextflow tasks are in `state`, not `lastState`, and the Job reason is always `BackoffLimitExceeded`

- **Where:** schedulers-and-monitoring.md §2 L3 and §3.5 (failure classes, Kubernetes column).
- **Evidence:**
  - **The spec:** "container `lastState.terminated.reason` (`OOMKilled`, `Error`), Job `BackoffLimitExceeded` / `DeadlineExceeded`".
  - **Nextflow:**
    - `PodSpecBuilder.groovy:415`: `restartPolicy` defaults to `Never`;
    - `:600`: Jobs get `backoffLimit: 0`;
    - `:493-494` and `K8sTaskHandler.groovy:263` put the task time limit into the pod's `activeDeadlineSeconds`.
  - **Kubernetes** ([PodStatus reference](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#PodStatus)): `lastState` describes the previous termination after a restart; `state` describes the current one.
- **Problem:**
  - With no restarts `lastState` is empty, so OOMKilled would be missed.
  - Every failed Job reports `BackoffLimitExceeded`, so the timeout class would never come from the Job.
- **Proposal:** "container `state.terminated.reason` (`OOMKilled`, `Error`) and exit code; pod `status.reason` `DeadlineExceeded` for Nextflow time limits (set as pod `activeDeadlineSeconds`); the Job's `Failed` condition (`BackoffLimitExceeded`, since Nextflow sets `backoffLimit: 0`) only says that the task failed". Spike T4 captures the real objects.
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-019 · minor · The `-with-weblog` marker can be resolved

- **Where:** synthesis.md §2 (Quick prototype, l.21) and §10.4.
- **Evidence:**
  - **The spec:** "`-with-weblog` is deprecated in 26.10 in favour of the plugin **[to be validated]**" (§2) and "`-with-weblog` is deprecated" (§10.4, unmarked).
  - **Nextflow** `docs/reference/cli/run.mdx:226-230`: `<DeprecatedInVersion version="26.10">` "This option is no longer supported. Use the nf-weblog plugin explicitly instead."
- **Problem:** the marker is still open, and §10.4 states the same fact without a source.
- **Proposal:**
  - **§2:** "`-with-weblog` is deprecated in 26.10 and no longer supported; use the `nf-weblog` plugin (Nextflow `docs/reference/cli/run.mdx:226-230`, read 2026-10-26)".
  - **§10.4:** link to §2.
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-020 · minor · Cache-breaking upgrades affect some processes in 25.10, 26.04 and 26.10, not everything in 26.04

- **Where:** synthesis.md §2 (Points of attention) and §5ter.5 (Settings to fix).
- **Evidence:**
  - **The spec:** "in 26.04 the first `-resume` after an upgrade may re-run everything" and "(the hash changes in 26.04)".
  - **Nextflow migration notes:**
    - `docs/migrations/25-10.mdx:284`: every process with an `eval` output re-executes;
    - `26-04.mdx:405-409`: "any process with a map input will be re-executed on the first resume after upgrading";
    - `26-10.mdx:225-227`: every process with an `eval` output re-executes.
- **Problem:** the claim overstates the 26.04 case and misses two other releases inside the supported range. A relaunch-cost estimate (UX-109, UX-113) would be wrong.
- **Proposal:**
  - **§2:** "a Nextflow upgrade can break the cache for some processes: `eval` outputs in 25.10 and 26.10, map inputs in 26.04 (see each release's 'Cache-breaking changes' migration note)".
  - **§5ter.5:** "same Nextflow version across stages (25.10, 26.04 and 26.10 each changed task hashes)".
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-021 · minor · The "server outage aborts the run" risk is about `nf-tower`, not Spectio

- **Where:** synthesis.md §10.2 (Main risks).
- **Evidence:**
  - **The spec:** "On the Nextflow side, a server outage during `create`, `begin` or `progress` aborts the run."
  - **nf-tower:** this is true of nf-tower, whose `TowerClient.groovy:145-180, 432` throw `AbortRunException`.
  - **Decision:** since [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md), Spectio's server is reached only through `nf-spectio`.
- **Problem:** the risk register states this as a property of Spectio. `nf-spectio`'s behaviour is Spectio's own design choice (synthesis §8: "never block the workflow if the server is unreachable").
- **Proposal:** "On the Nextflow side, `nf-spectio` must not abort the run when the server is unreachable (unlike `nf-tower`, which aborts on errors from `create`, `begin` or `progress`, `TowerClient.groovy:145-180`); it buffers to disk."
- **Found by:** fact-checker (run 1)
- **Status:** open

### FC-022 · minor · The `[saml]` system dependency depends on a library that is not chosen yet

- **Where:** architecture-plugins-and-packaging.md §7.3 (l.334).
- **Evidence:**
  - **The spec:** "`[saml]` is the only extra that needs a system library, `xmlsec1`."
  - **pysaml2** 7.5.5: `saml2/sigver.py:160` (`get_xmlsec_binary`) calls the `xmlsec1` binary.
  - **xmlsec** 1.3.17: the cp313 manylinux wheels carry a single 12.5 MB extension and no `.libs`, so libxmlsec1 is linked statically.
  - **python3-saml** README l.129: "To avoid `libxml2` library version incompatibilities between `xmlsec` and `lxml` it is recommended that `lxml` is not installed from binary."
- **Problem:** the statement holds for pysaml2 only. With python3-saml, the dependency is a compiler and libxml2-dev for lxml, not `xmlsec1`. The container recipe and the docs differ between the two.
- **Proposal:** "`[saml]` needs a system dependency whichever library is chosen: pysaml2 calls the `xmlsec1` binary, and python3-saml needs `lxml` built from source against the same libxml2 as `xmlsec` **[library to be chosen]**. The docs say so, and the container image includes it."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-023 · minor · Snakemake also has a scheduler plugin interface

- **Where:** architecture-plugins-and-packaging.md §1 (l.21).
- **Evidence:**
  - **The spec** lists executor, storage, report, logger and software-deployment.
  - **Snakemake** `1c67a66` `pyproject.toml:58` also has `snakemake-interface-scheduler-plugins>=2.0.0,<3.0.0`.
  - **Snakedeploy** `55e916e` templates include `scheduler-plugins`.
- **Problem:** the comparison that justifies "per-kind API versions inside one SDK" understates how many interfaces Snakemake splits out.
- **Proposal:** "…`-report-`, `-logger-`, `-software-deployment-` and `-scheduler-plugins`, plus `snakemake-interface-common` for the shared registry."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-024 · minor · respx mocks HTTP; it does not record it

- **Where:** architecture-plugins-and-packaging.md §4 (l.202).
- **Evidence:**
  - **The spec:** "It also provides a `FakeContext` and recorded HTTP (respx)."
  - **[respx on PyPI](https://pypi.org/project/respx/):** "A utility for mocking out the Python HTTPX and HTTP Core libraries."
- **Problem:** plugin authors would expect a record-and-replay workflow (cassettes) that respx does not provide.
- **Proposal:** "It also provides a `FakeContext` and HTTP mocking with respx; recorded cassettes, if wanted, need a recorder such as vcrpy or pytest-recording **[to be validated]**."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-025 · minor · "Mantine 7" is two majors behind, and the import map makes the major part of the plugin contract

- **Where:** architecture-plugins-and-packaging.md §5 (l.220) and §6 (l.247).
- **Evidence:**
  - **The spec:** "React + Vite + Mantine 7 + TanStack" (§6); "React, Mantine and `@spectio/ui-kit` are exposed through an import map, so a plugin shares the host's instances" (§5).
  - **npm:** `@mantine/core` latest is 9.7.4 (2026-10-25).
  - **depictio** `0d1aa0a` `viewer/package.json:29`: `"@mantine/core": "^7.14.0"`.
- **Problem:**
  - Choosing 7 matches depictio but starts on an old major.
  - Viewer plugins import the host's Mantine, so every later Mantine major upgrade breaks level-2 viewer plugins and needs a viewer API major bump.
- **Proposal:**
  - Record the choice explicitly: "Mantine 7 (depictio's major; upstream is at 9.x) **[decision: align with depictio or start on 9]**" (question 2).
  - In §4, add that the shared-module versions in the import map are part of the `viewer` API version.
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-026 · minor · depictio retries five specific 5xx codes, not every 5xx

- **Where:** cli-and-shared-libraries.md §1 (l.29) and §4 `bioplatform-client` (l.131, "depictio's retry policy").
- **Evidence:**
  - **The spec:** "hand-rolled retries on 408/425/429/5xx".
  - **depictio** `0d1aa0a` `depictio/cli/cli/utils/http_retry.py:50`: `RETRYABLE_STATUS … frozenset({408, 425, 429, 500, 502, 503, 504})`.
- **Problem:** Spectio adopts "depictio's policy". Copying "5xx" would also retry 501 and 505, which are not transient.
- **Proposal:** "hand-rolled retries on 408/425/429/500/502/503/504".
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-027 · minor · sind ships slurmrestd only in its 26.05 images

- **Where:** dev-environment-and-testing.md §0.2 (l.17); §4.1 `slurm-versions` (l.109).
- **Evidence:**
  - **The spec:** "Slurm 25.11 and 26.05 images; slurmdbd; slurmrestd with JWT" (D §0).
  - **sind** `0065750` `docs/content/guides/rest-api.md:36`: "slurmrestd comes with the Slurm 26.05 images … The 25.11 images have none: `sind create cluster` then fails". `README:28` says "(Slurm 26.05)".
- **Problem:** the slurmrestd transport cannot be tested on 25.11 locally, although Spectio targets both versions. The `slurm-versions` profile only covers the CLI path on 25.11.
- **Proposal:**
  - **§0.2:** "Slurm 25.11 and 26.05 images; slurmdbd; slurmrestd with JWT on the 26.05 images only".
  - **§4.1:** state that the 25.11 leg covers the CLI transport only.
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-028 · minor · Megatest outputs come from full-size public data, not from nf-core/test-datasets

- **Where:** dev-environment-and-testing.md §10.3 (l.331).
- **Evidence:**
  - **The spec:** "Licence of the outputs: they are derived from nf-core/test-datasets **[to be validated]**."
  - **rnaseq** 3.27.0 `conf/test_full.config:17-18`: `input = …/nf-core/test-datasets/…/samplesheet_full.csv` and `genome = 'GRCh37'`. That samplesheet lists `s3://ngi-igenomes/test-data/rnaseq/SRX1603629_T1_1.fastq.gz…`, which are public SRA runs.
  - **sarek** 3.10.0 `test_full.config:18-23` follows the same pattern.
  - **nf-core/test-datasets** is MIT.
- **Problem:** the marker points at the wrong source. Only the samplesheets are in test-datasets; the data are public archive runs and iGenomes references, each with its own terms.
- **Proposal:** "Licence of the outputs: they are derived from full-size public datasets (e.g. SRA runs mirrored under `s3://ngi-igenomes/test-data/`, AWS iGenomes references), listed in samplesheets from nf-core/test-datasets (MIT); each source's terms apply **[to be validated per pipeline]**."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-029 · minor · Current Kueue recommends Kubernetes ≥ 1.34; Spectio targets ≥ 1.33

- **Where:** dev-environment-and-testing.md §1 (l.51) and §4.2 `k8s-kueue`.
- **Evidence:**
  - **The spec:** "Kueue | pinned manifest version".
  - **[Kueue install page](https://kueue.sigs.k8s.io/docs/getting-started/installation/)** (v0.20.3): it recommends "Version 1.34 or newer" as the officially supported and tested versions.
  - **Spectio** targets Kubernetes ≥ 1.33.
- **Problem:** the pinned Kueue may not be supported on the lowest Kubernetes that Spectio claims. The kind node image and the Kueue version must be pinned as a pair.
- **Proposal:** "Kueue | pinned manifest version, chosen to support the lowest targeted Kubernetes (1.33), with the kind node image pinned to match **[to be validated: Kueue release supporting 1.33]**".
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-030 · minor · Nextflow install: the real asset names and hosts

- **Where:** dev-environment-and-testing.md §1 (l.47).
- **Evidence:**
  - **The spec:** "release launcher from GitHub releases, `NXF_VER` pinned **[to be validated: asset names and whether the cloud allowlist reaches `get.nextflow.io` / `www.nextflow.io`]**".
  - **GitHub release v26.10.3:** `nextflow` and `nextflow-26.10.3-dist` return HTTP 206; `-all` and `-one.jar` return 404.
  - **Launcher:** the get.nextflow.io script (l.23, 284-289) downloads `nextflow-$NXF_VER-one.jar` from `www.nextflow.io/releases`.
  - **[Install docs](https://docs.seqera.io/nextflow/install):** the `dist` build is "a self-contained `nextflow` executable" that "still downloads plugins at runtime".
  - **Plugins** come from `registry.nextflow.io` (`PluginsFacade.groovy:48`).
  - **Reachability:** all of these hosts answered HTTP 200 from this cloud session on 2026-10-26.
- **Problem:** the launcher fetches its jar from `www.nextflow.io`, not from GitHub. For an offline or allowlisted pin, the right asset is `-dist`.
- **Proposal:** "Nextflow | 26.10.x and 25.10.x | the self-contained `nextflow-<ver>-dist` from GitHub releases (offline-capable), or the `get.nextflow.io` launcher with `NXF_VER` pinned, which downloads `nextflow-<ver>-one.jar` from `www.nextflow.io/releases`; plugins come from `registry.nextflow.io`. All reachable from a cloud session (checked 2026-10-26)."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-031 · minor · Cloudflare's preview access policy does not cover the production URL

- **Where:** dev-environment-and-testing.md §7.1 (l.180).
- **Evidence:**
  - **The spec:** "Previews are public by default. Cloudflare Access can restrict them to Thomas."
  - **[Preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/):** "Enabling the access policy will restrict viewing project deployments to your Cloudflare account". The same page says this covers preview deployments only, not the `*.pages.dev` or custom domain.
- **Problem:** `https://spectio.pages.dev` (main) stays public even with the preview policy on, and its `/versions` page lists every preview URL.
- **Proposal:** "Previews are public by default. Cloudflare Pages' access policy restricts preview deployments to members of the Cloudflare account; the production URL (`spectio.pages.dev`) needs a separate Cloudflare Access application."
- **Found by:** fact-checker (run 2)
- **Status:** open

### FC-032 · minor · `--quiet` also hides `JOB_INFO` from logger plugins, and plain `-q` suppresses `JOB_FINISHED`

- **Where:** checking-scenarios.md §11.1, Snakemake rows.
- **Evidence:**
  - **The spec:** "`JOB_FINISHED` … Not emitted under `--quiet progress` or in a dry run" (§11.1).
  - **Snakemake** `1c67a66`:
    - `logging.py:404-424` maps `JOB_INFO` to `Quietness.RULES` and `JOB_FINISHED` to `Quietness.PROGRESS`;
    - `logging.py:691` applies that `DefaultFilter` to any logger plugin whose `has_filter` is false;
    - `cli.py:1308-1317`: `-q` without arguments means "do not output any progress or rule information".
- **Problem:** under `-q` or `--quiet rules`, the Spectio logger receives no `JOB_INFO`, so `published` and `task_done` watches never fire. The user cannot see why.
- **Proposal:**
  - Change the cell to: "`job_id` only … Not emitted under `--quiet progress` or plain `-q`, or in a dry run (`job_scheduler.py:90-92`)".
  - Add: "The `spectio` logger plugin sets `has_filter = True`, so the default quiet filter does not drop `JOB_INFO` (`logging.py:691`). The runner refuses or strips `-q` and `--quiet progress` on watched runs."
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-033 · minor · MultiQC on a single file works; start-up dominates, so batch the files

- **Where:** checking-scenarios.md §11.2, `watch[].checks` row (l.308).
- **Evidence:**
  - **The spec:** "the same parser as the final report **[to be validated]**: start-up time per call, and that `multiqc -m <module> <file>` parses a single file" (§11.2).
  - **Test** on 2026-10-26 with MultiQC 1.35 (PyPI), on 4 vCPU:
    - `multiqc -m star --no-report -o out star_salmon/log/S1.Log.final.out` reports "star | Found 1 reports";
    - it writes `multiqc_general_stats.txt` with sample `S1` and column `star-uniquely_mapped_percent`;
    - wall time was 2.3 s cold and 2.6 s warm;
    - 50 files in one call took 2.7 s.
- **Problem:** the marker can be resolved. One process per file costs about 2.5 s of start-up each time, which adds up when many items are watched.
- **Proposal:** replace the marker with "Verified with MultiQC 1.35 (2026-10-26): `multiqc -m <module> <file>` parses a single file and names the item from the file name. Each call costs about 2.5 s of start-up, so the runner batches the files that finish within a short window into one call." Column naming stays with UX-101.
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-034 · minor · Two Nextflow `[to be validated]` markers can be resolved from the source

- **Where:** checking-scenarios.md §11.1 (`onTaskComplete` row, l.253) and §11.5 (Order, l.340).
- **Evidence:**
  - **The spec:** "reading the declared outputs through the handler is **[to be validated]**" (§11.1); "only known once the upstream channel is closed **[to be validated]**" (§11.5).
  - **Nextflow** `114f1fe`:
    - `TaskPollingMonitor.groovy:765-770` calls `processor.finalizeTask(handler)` before `session.notifyTaskComplete(handler)`;
    - `TaskProcessor.groovy:1484-1520` (`collectOutputsV1` and `collectOutputsV2`) fills `task.outputs` (`TaskRun.groovy:100`);
    - `TraceObserverV2.groovy:63-69` defines `onProcessTerminate` ("all process tasks have completed"), fired from `TaskProcessor.terminateProcess` at `:2003-2006`.
- **Problem:** both markers are open although the code answers them. The second claim also misses an existing hook that gives an exact "end of stage" signal.
- **Proposal:**
  - **§11.1:** "outputs are collected before `onTaskComplete` fires (`TaskPollingMonitor.groovy:765-770`, nextflow `114f1fe`), so `event.handler.task.outputs` holds them. This is internal API, outside the `@Beta` observer contract: covered by the R4 version-pin tests."
  - **§11.5:** "'End of stage' means every process matching the stage's `match` globs has fired `onProcessTerminate` (`TraceObserverV2.groovy:63-69`)."
  - Spike T2 records both in golden fixtures.
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-035 · minor · The CloudEvents envelope omits the required `specversion`

- **Where:** api-and-data-model.md §8.
- **Evidence:**
  - **The spec:** "CloudEvents 1.0 envelope (`id`, `source`, `type`, `time`, `subject`, `data`), plus `spectioproject` and `spectiosequence` extensions" (§8).
  - **CloudEvents** `v1.0.2` `cloudevents/spec.md:248-315` lists `id`, `source`, `specversion` and `type` as REQUIRED. `extensions/sequence.md` defines a standard `sequence` attribute.
- **Problem:** events built from this list are not valid CloudEvents, so generic consumers and SDKs reject them.
- **Proposal:** "CloudEvents 1.0.2 envelope (`specversion: "1.0"`, `id`, `source`, `type`, `time`, `subject`, `datacontenttype: application/json`, `data`), plus the `spectioproject` extension and a per-run sequence (`spectiosequence`, or the documented `sequence` extension)."
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-036 · minor · Wording of HTTP and GA4GH standards: `RateLimit-*` and WES `workflow_type`

- **Where:** api-and-data-model.md §4 (Limits) and §2B.
- **Evidence:**
  - **Rate limits:**
    - the spec says "per-token rate limits with `RateLimit-*` headers" (§4);
    - draft-ietf-httpapi-ratelimit-headers-11 (2026-05-23) "defines the RateLimit-Policy and RateLimit HTTP header fields" (line 19);
    - the `-Limit`, `-Remaining` and `-Reset` names come from older drafts and the X- convention (line 1766).
  - **WES:**
    - the spec says "`workflow_type: NFL` or `SMK`" (§2B);
    - WES 1.1.0 OpenAPI `:753`: "must be "CWL" or "WDL" currently (or another alternative supported by this WES instance)".
- **Problem:**
  - `RateLimit-*` points implementers at superseded field names, in a document that is still a draft.
  - NFL and SMK are allowed, but the spec does not say that they are instance-specific values that must be advertised.
- **Proposal:**
  - **§4:** "per-token rate limits announced with the `RateLimit-Policy` and `RateLimit` fields of draft-ietf-httpapi-ratelimit-headers-11 (an Internet-Draft; re-check at implementation) **[to be validated]**".
  - **§2B:** "…with `workflow_type: NFL` or `SMK` (TRS descriptor types, which WES 1.1 accepts as instance-specific values; listed in `service-info.workflow_type_versions`)".
- **Found by:** fact-checker (run 3)
- **Status:** open

### FC-037 · minor · Table corrections with no finding of their own (batch)

- **Where:** see the list below; the rows are in [verification-2026-10-26.md](verification-2026-10-26.md).
- **Evidence:** the fact-checker runs proposed these corrections in their verification tables but did not raise findings for them. The merge collected them here so that they are not lost at triage. Each item is one sentence, and each can be accepted or rejected on its own.
- **Problem:** without a finding, `/apply-findings` would skip them, and four of them close `[to be validated]` markers.
- **Proposal:**
  1. **schedulers-and-monitoring.md §3.3 (row schedulers-and-monitoring-14):** add "Slurm 25.11 ships `data_parser` v0.0.41 to v0.0.44 (@slurm-25-11-8-1), so the range shared with 26.05 is v0.0.42 to v0.0.44; the runner negotiates within it."
  2. **schedulers-and-monitoring.md §3.5 (row schedulers-and-monitoring-22):** keep **[to be validated on sind]** and add the source "consistent with `SIG_OOM 253` in `src/common/slurm_protocol_defs.h:875` (253 & 0x7f = 125), Slurm 26.05.5".
  3. **synthesis.md §7 (row synthesis-31):** add "FastAPI sends `id:` fields, but the application reads `Last-Event-ID` itself to resume (`fastapi/sse.py:236-241`, FastAPI 0.162.0)."
  4. **architecture-plugins-and-packaging.md §7.4 (row A-20):** "…switched to source-only releases on 2025-10-15 ([commit 9e49d5e](https://github.com/minio/minio/commit/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a)) and was archived on 2026-04-25."
  5. **dev-environment-and-testing.md §1 l.49 (row D-7):** "sind | latest release, pinned | release binary `sind-linux-<arch>` from GitHub releases; needs Docker ≥ 28 on cgroup v2 | SLURM clusters". This closes the marker.
  6. **dev-environment-and-testing.md §10.4 l.351 (row D-23):** "IDR studies idr0033, idr0062, idr0066 and idr0076 are CC BY 4.0 (study files, checked 2026-10-26); idr0001, idr0054 and idr0073 **[to be validated]**."
  7. **dev-environment-and-testing.md §12 l.388 (row D-27):** "A commit in a visible changelog section is releasable: release-please skips a release only when the generated changelog is empty (release-please `c589293`, `src/strategies/base.ts:331-337`)." This closes the marker.
  8. **api-and-data-model.md §4 (row api-and-data-model-2):** "…`Deprecation` (RFC 9745) and `Sunset` (RFC 8594) headers."
- **Found by:** fact-checker (runs 1, 2 and 3; collected by the merge)
- **Status:** open

---

## Part B · Every remaining `[to be validated]` in `docs/specs`

**How this list was built:** a grep on `autopilot/integration` (2026-10-26) for "to be validated", "to be checked" and "to check". It found 34 places. Two of them describe the marker convention itself and are not open items (synthesis.md l.3, documentation-system.md l.196). Three of them are the same question (B1).

**How to settle:**
- **doc lookup** = read a primary page;
- **code read** = read a pinned source;
- **spike** = run something;
- **ask** = a decision or a fact only a person can give.

**"After R2"** says what R2 already settled. "Resolved" means the proposed text in the named finding removes the marker once it is applied.

| # | Spec, line | Open item | Cheapest way to settle | After R2 | Proposed home |
|---|---|---|---|---|---|
| B1 | api-and-data-model l.267; synthesis l.13; ui-spec l.196 | `nf-spectio` and `nf-tower` report the same run | spike (the code read is done) | The code supports it (`Session.groovy:581-590` registers every `TraceObserverFactoryV2`) | **T2** (already planned) |
| B2 | architecture-plugins-and-packaging l.373 | Snakemake on Kubernetes can use S3 instead of a shared FS | code read | **Resolved, wrong**: S3 is mandatory (FC-005) | A spike checks the S3 path in **T4** |
| B3 | checking-scenarios l.253 | Declared outputs are readable through the handler in `onTaskComplete` | code read | **Resolved** (FC-034) | Confirmed by the **T2** fixtures |
| B4 | checking-scenarios l.267 | Files on object storage are read with the run's own credentials | code read (Snakemake storage plugins, Nextflow `nf-amazon`), then spike | Open | **T4**, with SeaweedFS in kind |
| B5 | checking-scenarios l.308 | `multiqc -m <module> <file>` parses one file; start-up time | spike (measured) | **Resolved** (FC-033) | — |
| B6 | checking-scenarios l.324 | The `ext.when` stop closure is evaluated per task | code read, then spike | Per-task evaluation is **resolved**. New marker: wrapping the original `ext.when` with `file()` under the v2 parser (FC-002) | **T1** (nf-toy) plus rnaseq MARKDUPLICATES |
| B7 | checking-scenarios l.325 | No conditional `--until` in Snakemake | code read | **Resolved**: true; the stop signal becomes SIGTERM (FC-001) | SIGTERM drain under the SLURM plugin is checked in **T3** |
| B8 | checking-scenarios l.340 | "End of stage" is known only when the upstream channel closes | code read | **Resolved**: `onProcessTerminate` (FC-034) | Confirmed by the **T2** fixtures |
| B9 | depictio-ecosystem-reuse l.155 | `depictio:set-filter` / `depictio:selection` embed messages | ask (depictio maintainers) | Open (not in R2 scope) | Question 7 |
| B10 | dev-environment-and-testing l.47 | Nextflow asset names; cloud allowlist reaches `get.nextflow.io` / `www.nextflow.io` | doc lookup plus `curl` | **Resolved** (FC-030) | Re-checked in passing by **D2** |
| B11 | dev-environment-and-testing l.49 | sind install method | doc lookup | **Resolved** (FC-037 item 5) | Used in **D2** |
| B12 | dev-environment-and-testing l.182 | Cloudflare direct uploads count as builds | spike (the docs say nothing) | Open | **D5** (already in its prompt: compare the monthly build counter before and after one `wrangler pages deploy`) |
| B13 | dev-environment-and-testing l.331 | Megatest output licence | doc lookup | Source **resolved** (FC-028). Per-pipeline terms (SRA, iGenomes) remain a doc lookup | Doc lookup during **T7** |
| B14 | dev-environment-and-testing l.351 | IDR study licences | doc lookup | 4 of 7 **resolved** (FC-037 item 6); idr0001, idr0054 and idr0073 remain | Doc lookup (IDR study pages); no spike |
| B15 | dev-environment-and-testing l.388 | A visible changelog section makes a commit releasable | code read | **Resolved** (FC-037 item 7) | — |
| B16 | dev-environment-and-testing l.428 | Adoption target (3 groups, 10 users, a second site) | ask | Open (a goal, not a fact) | Question 8 |
| B17 | schedulers-and-monitoring l.45 | Snakemake Kubernetes / Kueue plugins: pod labels and how status is read | code read (plugin `d5f720e`) | Open | Code read before **T4**; **T4** captures pods |
| B18 | schedulers-and-monitoring l.135 | SLURM OOM gives `OUT_OF_MEMORY` with exit 0:125 | spike | Consistent with `SIG_OOM 253` (FC-037 item 2) | **T3** |
| B19 | schedulers-and-monitoring l.202 | LSF, PBS, Grid Engine and HTCondor flags | doc lookup at the first site that asks | Deferred by design | None now |
| B20 | synthesis l.21 | `-with-weblog` deprecated in 26.10 | doc lookup | **Resolved** (FC-019) | — |
| B21 | synthesis l.124 | nf-shard maturity | code read (git log) | **Resolved**: last commit 2024-09-19 (synthesis-17). Suggested text: "inactive since 2024-09" | Can go with FC-037 at triage |
| B22 | synthesis l.232 | No native "finish running tasks" mode | code read | **Resolved**: Snakemake drains on SIGTERM; Nextflow does not (FC-001) | **T3** checks it on SLURM |
| B23 | synthesis l.244 | Forcing a Nextflow stage needs a "salt" parameter read by that process | code read (`TaskProcessor` hash inputs), then spike | Open | **T1** (nf-toy with a `salt` param; check that `-resume` reruns only that process and its downstream) |
| B24 | synthesis l.365 | The server runs on a service node or a VM, not a login node | ask (EMBL HPC admins) | Open | Question 9 |
| B25 | synthesis l.370 | Cancellation by `scancel` or SIGTERM in practice | code and man-page read, then spike | Semantics **resolved** (FC-001) | **T3**, both engines |
| B26 | telemetry-and-analytics l.121 | GA4 sets cookies; consent is needed in the EU | doc lookup (Google Analytics help, EDPB guidance) | Open (not in R2 scope) | Doc lookup in the next fact pass |
| B27 | telemetry-and-analytics l.122 | Umami is cookieless | doc lookup (Umami docs) | Open | Doc lookup |
| B28 | telemetry-and-analytics l.125 | PostHog uses cookies or localStorage by default | doc lookup (posthog-js `persistence` default) | Open | Doc lookup |
| B29 | telemetry-and-analytics l.138 | History auto-tracking can be turned off per provider | doc lookup, then a quick browser check | Open | Doc lookup; the browser check can ride on **T6** |
| B30 | telemetry-and-analytics l.154 | EMBL's data-protection policy applies to EMBL instances | ask (EMBL data protection) | Open | Question 10 |
| B31 | (new, FC-009) | `snakemake-executor-plugin-kueue` 0.1.0 runs on Snakemake 9.27 | spike (`pip install`, `snakemake --executor kueue` against kind) | New | **D2** (install), **T4** (run) |
| B32 | (new, FC-029) | A Kueue release that supports Kubernetes 1.33 | doc lookup (Kueue release notes) | New | Doc lookup before **T4** pins |
| B33 | (new, FC-014) | D-Bus Secret Service on EMBL login nodes | spike (one `python -c "import keyring; keyring.get_keyring()"`) | New | **D2**, or ask Thomas to run it on a login node |
| B34 | (new, FC-004, FC-010) | `uv tool install --managed-python` gives SQLite ≥ 3.51.3 | spike (one command) | New | **D2** |

**Counts.** B1 to B30 are the 30 distinct items in existing specs; B19 is deferred, which leaves 29. R2 resolves 14 of them by doc lookup, code read or measurement: B2, B3, B5, B7, B8, B10, B11, B15, B20, B21 and B22, plus the core of B6, B13 and B25. Of the others:
- 7 need a spike: B1, B4, B12, B18 and B23, plus the remainder of B6 and B25;
- 6 need a doc lookup: B14, B17, B26 to B29 (the rest of B13 is also a doc lookup);
- 4 need a person: B9, B16, B24 and B30.

The findings add four new items (B31 to B34) and some new markers in their proposals: FC-002, FC-009, FC-014, FC-022, FC-024, FC-029 and FC-036.

## Proposed spikes (phases D and T)

Every item is attached to a step that already exists in `docs/playbooks/next-phase.md`, so no new pipeline step is needed. Each addition is a few lines in that step's prompt.

| Step | What R2 adds | Settles |
|---|---|---|
| **D2** · cloud environment | `uv tool install --managed-python` and print `sqlite3.sqlite_version`; install `snakemake-executor-plugin-kueue` 0.1.0 next to Snakemake 9.27.1 and run `snakemake --executor kueue --help`; download `nextflow-<ver>-dist` from GitHub releases; `keyring.get_keyring()` in the container | B31, B33, B34, FC-030 (confirmation) |
| **D5** · Cloudflare previews | Direct-upload build counting (already listed); check that the production URL stays public with the preview policy on | B12, FC-031 |
| **T1** · fixture workflows | nf-toy: a stage boundary that wraps an existing `ext.when` with a stop-file test under the v2 parser, and the `salt` parameter for forcing a stage. smk-toy: SIGTERM mid-stage, then check that running jobs finish and nothing new starts | B6, B23, FC-001 (local), FC-002 |
| **T2** · engine event capture | Keep the dual-observer run (B1); also record `event.handler.task.outputs` in `onTaskComplete` and `onProcessTerminate` order; run the Snakemake logger under `-q` and `--quiet rules`, with and without `has_filter` | B1, B3, B8, FC-032, FC-034 |
| **T3** · sind (R1 also extends it for SR-037) | `scancel --signal=TERM --full` versus a plain `scancel` on a Nextflow and a Snakemake head (orphan task jobs, `KillWait`); runner restart with a head job running, reconciled by `squeue --me --json` with a prefix filter; Snakemake `--slurm-jobname-prefix` and the `SLURM run ID` lookup; OOM exit 0:125; field names `state_reason` and per-step TRES; slurmrestd on 26.05 only | B18, B22, B25, FC-001, FC-006, FC-007, FC-016, FC-027 |
| **T4** · kind and Kueue | Snakemake on Kubernetes with `--default-storage-provider s3` against SeaweedFS; Snakemake on Kueue (plugin 0.1.0, or `kubernetes` executor plus Kueue pod integration); a Kueue release and kind node image at 1.33; Nextflow pod `state.terminated.reason` and `DeadlineExceeded`; first `helm install` with the pre-install migrate hook; object-storage credentials for live checks | B4, B17, B31, B32, FC-005, FC-008, FC-009, FC-018, FC-029 |

**Priority.** T3 and T4 carry the most weight: they settle five of the nine majors (FC-001, FC-005, FC-006, FC-007, FC-008) and FC-009 goes with them. D2's additions are single commands and cost almost nothing.

## Questions for Thomas

These belong in [inbox.md](inbox.md). This step writes only the two review files, so the autopilot copies them there at triage.

1. **FC-003, depictio hand-off credential.** Keep the provisioning key on the Spectio server only: the sink plugin mints a per-user depictio token, and the runner runs `ingest` without `--user`. Should depictio also get run-scoped, short-lived tokens? You maintain depictio, so this is a depictio change as much as a Spectio one. **Recommendation:** yes to both; the depictio change can come after 0.1.
2. **FC-025, Mantine major.** Align with depictio's Mantine 7, or start on 9.x? The import map makes the major part of the viewer plugin API. **Recommendation:** start on 9 unless shared components with depictio are planned before 1.0.
3. **FC-022, SAML library.** pysaml2 (needs the `xmlsec1` binary) or python3-saml (needs `lxml` built from source)? **Recommendation:** pysaml2, whose system dependency is one package.
4. **FC-014, keyring.** Make the OS keyring an optional extra (`spectio[keyring]`), so the base install stays pure Python? **Recommendation:** yes.
5. **FC-009, Snakemake on Kueue.** Mark the matrix cell "snakemake × k8s-kueue" as pending until spike D2/T4 shows the 0.1.0 plugin runs? **Recommendation:** yes. If it does not run, test the `kubernetes` executor with Kueue's pod integration instead.
6. **FC-013, Node.** Pin Node 24 LTS now and move to 26 when it becomes Active LTS (2026-10-28)? **Recommendation:** yes.
7. **B9, embed messages.** Should depictio accept `depictio:set-filter` and `depictio:selection` messages next to `depictio:set-color-scheme`? This is your call as depictio maintainer.
8. **B16, adoption target.** Is "3 groups, 2 outside your team, 10 active users for 8 weeks, one site other than EMBL" the target you want to commit to?
9. **B24, hosting.** Can you ask the EMBL HPC admins whether a long-running Spectio server may run on a service node or needs a VM?
10. **B30, data protection.** Who at EMBL confirms which data-protection policy applies to an EMBL-hosted instance's telemetry?
