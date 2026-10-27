# Verification of external claims · 2026-10-26

**Step page:** [R2](../progress/W1/R2.md)

**Round:** R2 · Fact verification · **Date:** 2026-10-26 · **Produced by:** three `fact-checker` runs (`/verify-claims`), merged in [R2-open-validations.md](R2-open-validations.md) · **Status:** waiting for triage (TRIAGE1)

This is the full claim table that `verify-claims` asks for. It covers eight specs:
- **Run 1:** [schedulers-and-monitoring.md](../specs/schedulers-and-monitoring.md) and [synthesis.md](../specs/synthesis.md).
- **Run 2:** [architecture-plugins-and-packaging.md](../specs/architecture-plugins-and-packaging.md), [dev-environment-and-testing.md](../specs/dev-environment-and-testing.md) and [cli-and-shared-libraries.md](../specs/cli-and-shared-libraries.md).
- **Run 3:** [api-and-data-model.md](../specs/api-and-data-model.md), [checking-scenarios.md](../specs/checking-scenarios.md) and [admin-and-operations.md](../specs/admin-and-operations.md).

All three runs returned output; none failed. The specs were not edited.

The "Correction" column points to the merged finding in [R2-open-validations.md](R2-open-validations.md), which has the exact replacement text. Where a correction has no finding of its own, it is collected in FC-037.

## Sources and commits read

Each run cloned the sources shallowly under `/tmp/w1-scratch/` or read them on the web, all on 2026-10-26.

| Source | Revision |
|---|---|
| Nextflow | `master` `114f1fe` (26.10.x line; newest tag v26.10.4); `dfa5c1c` (cited by checking-scenarios) |
| Snakemake | `main` `1c67a66` (2026-10-19; CHANGELOG head 9.27.0; tag v9.27.1) |
| snakemake-executor-plugin-slurm | `8c2af56` (v2.8.0) |
| snakemake-executor-plugin-kubernetes | `d5f720e` |
| snakemake-executor-plugin-kueue | `c09bf0d` (wheel 0.1.0) |
| snakemake-interface-logger-plugins | `f27aaf1` (v2.1.0) |
| snakemake-interface-common / -executor-plugins | `92e5024` / `05712ed` |
| snakedeploy / snakemake-plugin-catalog | `55e916e` / `d2c11a2` |
| Slurm | tags `slurm-26-05-5-1` (`ad46cad`) and `slurm-25-11-8-1` |
| Kueue | `main` `c331366`, tags v0.13.0 to v0.20.0 |
| sind / kind | `0065750` / `2b29beb` |
| depictio | `main` `0d1aa0a` (2026-10-23); tag v1.19.2 = `e40ca79` |
| labid-cli / labid-lib | `5af9e16` / `cd14636` |
| nf-weblog, nf-prov, nf-shard | `013dac3`, `8aa8280`, `f40ce84` |
| FastAPI | `79cab5b` (0.162.0) |
| sapporo-service | `14e6b5c` |
| python-build-standalone | `a3f2146` |
| cloudevents/spec | `1025510`, tag `v1.0.2` |
| release-please | `c589293` |
| minio | `9e49d5e` |
| GA4GH WES | OpenAPI 1.1.0 (`develop` and tag `1.1.0`) |
| nf-core | `https://nf-co.re/pipelines.json` (2026-10-26); nf-core/rnaseq tag 3.27.0 |
| MultiQC | 1.35 from PyPI, run on a synthetic `S1.Log.final.out` |
| Web pages | sqlite.org, rfc-editor.org, IETF datatracker, helm.sh, docs.astral.sh, Cloudflare, GitHub, Kubernetes, Kueue and Node.js release pages, PEPs 619 and 790 |

**Path abbreviations in run 1:**
- `NF` = `modules/nextflow/src/main/groovy/nextflow`;
- `K8S` = `plugins/nf-k8s/src/main/nextflow/k8s`;
- `SMK` = `src/snakemake`;
- `PLG` = `snakemake_executor_plugin_slurm`.

**Claim IDs in run 2:** `A-` is architecture-plugins-and-packaging, `D-` is dev-environment-and-testing and `C-` is cli-and-shared-libraries. Run 2 has no row D-2.

## Totals

| Run | Claims | True | Partly | Wrong | Unverifiable |
|---|---|---|---|---|---|
| 1 · schedulers, synthesis | 69 | 51 | 13 | 4 | 1 |
| 2 · architecture, dev-environment, cli | 74 | 54 | 16 | 3 | 1 |
| 3 · api, checking, admin | 63 | 48 | 11 | 1 | 3 |
| **Total** | **206** | **153** | **40** | **8** | **5** |

Notes on the counts:
- Run 1 reported 50 true and 14 partly. Recounting its rows gives 51 and 13, and the table above uses the recount.
- Run 3 gave no totals; the merge counted its rows.
- checking-scenarios-15 ("partly / wrong method") is counted as partly.
- synthesis-24 ("wrong for Snakemake, true for Nextflow") is counted as wrong.

**The eight wrong claims:**
- schedulers-and-monitoring-5, -7 and -8;
- synthesis-24;
- A-16, A-24 and D-22;
- api-and-data-model-22.

## Run 1 · schedulers-and-monitoring.md and synthesis.md

| ID | Location | Claim | Verdict | Source | Correction |
|---|---|---|---|---|---|
| schedulers-and-monitoring-1 | §0.1, §1 | Nextflow polls `squeue` every `executor.queueStatInterval`, default 1 min | true | `NF/executor/ExecutorConfig.groovy:187`; `docs/reference/config/executor.mdx:112-116` | — |
| schedulers-and-monitoring-2 | §1 | Command is `squeue --noheader -o '%i %t' -t all -u $USER`, with optional `-p` | true | `NF/executor/SlurmExecutor.groovy:159-178` | — |
| schedulers-and-monitoring-3 | §1 | `--only-job-state` (SLURM ≥ 24.05) is used when `executor.onlyJobState` is set | partly | `executor.mdx:76-84` (`AddedInVersion 26.04`); `SlurmExecutor.groovy:163-166` drops `-u` and `-p` | FC-012 |
| schedulers-and-monitoring-4 | §0.1, §1 | The Snakemake SLURM plugin checks first after 40 s, then adds 10 s per round with no finished jobs, up to 180 s | true | `PLG/__init__.py:246, 1288, 1292-1300, 1602-1608` | — |
| schedulers-and-monitoring-5 | §1 | "sacct by default when `MinJobAge` is too low for squeue" | wrong | `PLG/__init__.py:77-97` (sacct whenever it is on PATH); `PLG/validation.py:138-168` (`MinJobAge` only triggers warnings) | FC-015 |
| schedulers-and-monitoring-6 | §0.4, §1 | Job name = run UUID with an optional prefix, logged as "SLURM run ID"; the comment is `rule_<name>_wildcards_<…>` | true | `PLG/__init__.py:473-496, 837-848, 1098-1104` | The prefix is joined with `_` (FC-007) |
| schedulers-and-monitoring-7 | §3.4 | Spectio sets `--slurm-jobname-prefix spectio-<run_id>`, then queries `sacct --name` / `squeue --name` | wrong | `PLG/__init__.py:493-495`; squeue `src/squeue/print.c:3263-3275` (`xstrcasecmp`); slurmdbd `as_mysql_jobacct_process.c:1608` (`job_name='%s'`) | FC-007 |
| schedulers-and-monitoring-8 | §3.1 | Reconcile head jobs with `squeue --me --name 'spectio-*'` | wrong | `squeue.1:1423-1425`; `print.c:3263-3275` (exact, case-insensitive match; no wildcards) | FC-006 |
| schedulers-and-monitoring-9 | §1 | The efficiency report is optional and comes only at the end | true | `PLG/__init__.py:575-595` (written in `shutdown()`) | — |
| schedulers-and-monitoring-10 | §0.4, §1 | Pod labels `nextflow.io/app`, `runName`, `taskName`, `processName`, `sessionId`, `queue` | true | `K8S/K8sTaskHandler.groovy:296-313`; values are sanitised (`K8S/model/PodSpecBuilder.groovy:487, 747-790`) | — |
| schedulers-and-monitoring-11 | §1 | One Kubernetes `Job` per task by default since 26.10; a `Pod` before | true | `docs/reference/config/k8s.mdx:45-51`; `K8S/K8sConfig.groovy:224` | — |
| schedulers-and-monitoring-12 | §1, §4 | Successful pods are deleted (`k8s.cleanup`, default true); failed pods are kept | true | `K8S/K8sConfig.groovy:286-287`; `K8sTaskHandler.groovy:584-597` | — |
| schedulers-and-monitoring-13 | §1 | The catalogue lists 28 executor plugins, including lsf, sge, htcondor, flux, kubernetes, kueue, tes, googlebatch, aws-batch and azure-batch | true (2026-10-26) | https://snakemake.github.io/snakemake-plugin-catalog/ | — |
| schedulers-and-monitoring-14 | §3.3 | Slurm 26.05 ships `data_parser` v0.0.42 to v0.0.45; `GET /openapi/v3` serves the spec | true | `src/plugins/data_parser/` @slurm-26-05-5-1; https://slurm.schedmd.com/rest_release_notes.html | 25.11 ships v0.0.41 to v0.0.44, so the range shared by both versions is v0.0.42 to v0.0.44 (FC-037) |
| schedulers-and-monitoring-15 | §3.3 | jobcomp/kafka sends records at completion and, since 25.05, optionally at start; the topic defaults to the cluster name | true | `doc/html/jobcomp_kafka.shtml:7-8, 147-149` @slurm-26-05-5-1 | — |
| schedulers-and-monitoring-16 | §3.3 | `condor_watch_q` follows the job event log files instead of querying the schedd | true | https://www.mankier.com/1/condor_watch_q | — |
| schedulers-and-monitoring-17 | §3.3 | Flux job event logs can be watched from Python | true | flux-core docs: `flux.job.event_watch`, `event_watch_async` | — |
| schedulers-and-monitoring-18 | §3.2 | `SlurmctldParameters=rl_enable` rate-limits RPCs per user | true | `doc/man/man5/slurm.conf.5:5573-5579` | — |
| schedulers-and-monitoring-19 | §2, §5 | `squeue --json` gives `reason` and an estimated `start_time` | partly | `src/plugins/data_parser/v0.0.45/parsers.c:10066, 10069` (the field is `state_reason`) | FC-016 |
| schedulers-and-monitoring-20 | §2 L3 | `sacct --json` gives `TotalCPU` and TRES requested and used (max RSS, energy) | partly | `parsers.c:9050-9063` (job level); `9417, 9437-9444` (usage is per step) | FC-016 |
| schedulers-and-monitoring-21 | §3.5 | Pending reasons `Priority`, `Resources`, `QOSMaxJobsPerUserLimit`, `AssocGrpCPULimit`, `AssocGrpMemLimit`, `ReqNodeNotAvail, Reserved for maintenance`, `PartitionTimeLimit`, `Dependency`, `DependencyNeverSatisfied`, `JobHeldUser`, `JobHeldAdmin` | partly | `src/common/job_state_reason.c`: all present except `AssocGrpCPULimit`, whose real string is `AssocGrpCpuLimit` (l.254); `src/slurmctld/node_scheduler.c:2845` | FC-017 |
| schedulers-and-monitoring-22 | §3.5 | Under SLURM an OOM kill gives `OUT_OF_MEMORY` with exit code 0:125 **[to be validated on sind]** | unverifiable (consistent with the code) | `src/common/slurm_protocol_defs.h:875`: `SIG_OOM 253`, and 253 & 0x7f = 125 | Keep the marker and add this source (FC-037); spike T3 settles it |
| schedulers-and-monitoring-23 | §3.5 | A local time limit gives exit 143 on 26.10.3 and `Integer.MAX_VALUE` on 25.10.9, with the message "Process exceeded running time limit" | true (message); the exit codes come from the dated spike and were not re-run | `NF/executor/local/LocalTaskHandler.groovy:240`; [spike-synthetic-pipelines-2026-10-26.md](../research/spike-synthetic-pipelines-2026-10-26.md) | — |
| schedulers-and-monitoring-24 | §3.5 | Snakemake 9.27.1 prints "BUG: Out of jobs ready to be started" | true (message); the cause is a spike observation | `SMK/scheduling/job_scheduler.py:52` | — |
| schedulers-and-monitoring-25 | §3.5 | The Snakemake SLURM plugin has `exclude_failed_nodes` | true | `PLG/__init__.py:277, 474-480` | — |
| schedulers-and-monitoring-26 | §3.4 | The Nextflow grid job name is `nf-<PROCESS>_(<tag>)` | true | `NF/executor/AbstractGridExecutor.groovy:49, 179-189` (also maps `:` to `_`; `executor.jobName` overrides it) | — |
| schedulers-and-monitoring-27 | §3.4 | The `k8s.pod` label option can add `spectio.io/run-id` | true | `K8S/model/PodOptions.groovy:135-136` | — |
| schedulers-and-monitoring-28 | §3.4 | An array element's ID is `<id>_<n>` on SLURM | true | `NF/executor/SlurmExecutor.groovy:247-249` | — |
| schedulers-and-monitoring-29 | §2 L3, §3.5, §4 | Kubernetes OOM is read from `lastState.terminated.reason`; Job `BackoffLimitExceeded` / `DeadlineExceeded`; timeout = `DeadlineExceeded` | partly | `K8S/model/PodSpecBuilder.groovy:415` (`restartPolicy` `Never`), `:600` (`backoffLimit: 0`), `:493-494`; `K8sTaskHandler.groovy:263` | FC-018 |
| schedulers-and-monitoring-30 | §4 | Kueue visibility path `/apis/visibility.kueue.x-k8s.io/v1beta2/…`; `VisibilityOnDemand` is beta and on by default since v0.9 | partly | `pkg/features/kube_features.go:973-976` (gate true); `apis/visibility/` per tag: only `v1beta1` up to v0.14.0, `v1beta2` added in v0.15.0, only `v1beta2` on `main` | FC-012 |
| schedulers-and-monitoring-31 | §4 | Workload conditions `QuotaReserved`, `Admitted`, `Evicted`, `Preempted`; `positionInLocalQueue` / `positionInClusterQueue` | true | `apis/kueue/v1beta2/workload_types.go:935-1047`; `apis/visibility/v1beta2/types.go:76-79` | — |
| schedulers-and-monitoring-32 | §2 L1, §11 | `scancel` cancels the head job (cancel, relaunch) | partly | `scancel.1:65-75, 182-184, 375-379`; `slurm.conf.5:2396-2401` (`KillWait` 30 s) | FC-001 |
| synthesis-1 | §2 | `TraceObserverV2` is `@Beta`, with the 13 listed hooks | true | `NF/trace/TraceObserverV2.groovy:32-140` | — |
| synthesis-2 | §2 | nf-weblog 1.2.0, Apache-2.0, Nextflow ≥ 25.10, events `started` … `completed` | true | nf-weblog `VERSION`, `COPYING`, `build.gradle:9`, `WebLogObserver.groovy:171` | — |
| synthesis-3 | §2, §10.4 | `-with-weblog` is deprecated in 26.10 **[to be validated]** | true | `docs/reference/cli/run.mdx:226-230` | FC-019 |
| synthesis-4 | §2, §2bis | nf-tower routes `create`/`begin`/`progress`/`heartbeat`/`complete`; `TowerObserver` implements V2; 1 s / 100 tasks; heartbeat every 1 min | true | `plugins/nf-tower/.../TowerObserver.groovy:55-61, 600-633`; `TowerClient.groovy:186-214` | — |
| synthesis-5 | §2bis, §10.2 | An error on `create`, `begin` or `progress` aborts the run | partly (true of nf-tower only) | `TowerClient.groovy:145-180, 432` | FC-021 |
| synthesis-6 | §2bis | `workflowId` is read from `TOWER_WORKFLOW_ID` | true | `TowerObserver.groovy:229` | — |
| synthesis-7 | §2 | The official plugin registry exists since 25.10 | true | `docs/plugins/plugin-registry.mdx:10` | — |
| synthesis-8 | §2, §5ter.5 | "In 26.04 the first `-resume` after an upgrade may re-run everything"; "the hash changes in 26.04" | partly | `docs/migrations/25-10.mdx:282-284`, `26-04.mdx:405-409`, `26-10.mdx:225-227` | FC-020 |
| synthesis-9 | §2 | The `-resume` cache depends on the launch directory | true | `docs/cache-and-resume.mdx:52` | — |
| synthesis-10 | §2 | `--log-handler-script` and `--wms-monitor` are gone; `--logger` exists | true | no match in `SMK/` @1c67a66 | — |
| synthesis-11 | §2 | `LogEvent` names `WORKFLOW_STARTED`, `RUN_INFO`, `JOB_*`, `PROGRESS`, `ERROR` | true | logger-plugins `common.py:33-47` (the values are lower-case strings via `auto()`) | — |
| synthesis-12 | §2, §5, §5ter | `DAGSettings` has `until`, `omit_from`, `forcerun`, `forceall`, `rerun_triggers` | true | `SMK/settings/types.py:203-209` | — |
| synthesis-13 | §2bis | `--logger` is not passed on to remote jobs | true | `SMK/spawn_jobs.py` general args (about l.280-360) carry no logger options | — |
| synthesis-14 | §2bis | Without `has_filter`, Snakemake's default filter applies (`--quiet`) | true | `SMK/logging.py:691-700` | — |
| synthesis-15 | §2bis | Events go through a `QueueListener` | true | `SMK/logging.py:671-679` | — |
| synthesis-16 | §2bis | The API has `printd3dag`, `printrulegraph`, `summary`, `list_changes`, `unlock`, `create_report` | true | `SMK/api.py:726-823` | — |
| synthesis-17 | §2bis | nf-shard is MIT; last commit 19/09/2024 | true | nf-shard `f40ce84` (2024-09-19), `LICENSE` | — |
| synthesis-18 | §2ter | Snakemake SLURM job arrays via `--slurm-array-jobs` | true | `PLG/__init__.py:169`; plugin CHANGELOG l.45-50 (added in 2.6.0) | FC-012 (version floor) |
| synthesis-19 | §2ter | `cleanup = true` runs only after a successful run and breaks `-resume` | true | `docs/reference/config/unscoped.mdx:14-20` | — |
| synthesis-20 | §2ter | Module registry in Nextflow ≥ 26.04 | true | `docs/migrations/26-04.mdx:14` | — |
| synthesis-21 | §2ter, §5ter.5 | `--persistence-backend db` | partly | `SMK/cli.py:1642-1656`; Snakemake CHANGELOG l.283 (added in 9.17.0) | FC-012 |
| synthesis-22 | §5 | `-entry` is deprecated since 24.10 | true | `docs/reference/cli/run.mdx:66-72` | — |
| synthesis-23 | §5ter.3 | SIGINT makes Snakemake cancel cluster jobs | true | `SMK/scheduling/job_scheduler.py:398-402` | — |
| synthesis-24 | §5ter.3 | No native "finish running tasks without submitting new ones" mode **[to be validated]** | wrong (Snakemake) / true (Nextflow) | `job_scheduler.py:171, 241-245, 574-577`; `NF/Session.groovy:609-615, 1024-1054` | FC-001 |
| synthesis-25 | §8 | Cancellation by `scancel` or SIGTERM **[to be validated in practice]** | partly | `scancel.1:65-75, 182-184, 375-379`; `slurm.conf.5:2396-2401` | FC-001 |
| synthesis-26 | §5ter.5 | `cache 'lenient'` on NFS | true | `docs/cache-and-resume.mdx:135-141` | — |
| synthesis-27 | §3, §4, §7bis | WES 1.1.0 has `/runs`, `/status`, `/tasks`, `/cancel`, `/service-info`; 11 states; no pause | true | WES OpenAPI l.5, 138-565, `State` enum l.676-686 | There is a `PAUSED` state but no pause operation |
| synthesis-28 | §3 | Sapporo is Apache-2.0 | true | sapporo-service `14e6b5c` `LICENSE` | — |
| synthesis-29 | §5bis | MCP 2026-07-28 is stateless, with `input_required` and a `tasks` extension | true | https://modelcontextprotocol.io/specification/2026-07-28/changelog (major changes 1, 2, 6, 7) | — |
| synthesis-30 | §6 | NGFF 0.6 is the current release | true | https://ngff.openmicroscopy.org/specifications/index.html | — |
| synthesis-31 | §7 | FastAPI has native SSE since 0.135, a 15 s keep-alive and `Last-Event-ID` | true | `docs/en/docs/tutorial/server-sent-events.md:9`; `fastapi/sse.py:117, 236-241` | The app must read `Last-Event-ID` itself (FC-037) |
| synthesis-32 | §7 | Require SQLite ≥ 3.51.3 for the WAL-reset bug fix | partly | https://www.sqlite.org/wal.html (fixed in 3.51.3; backports 3.44.6 and 3.50.7) | FC-010 |
| synthesis-33 | §7, §10.1 | WAL does not work on network file systems | true | https://www.sqlite.org/wal.html §1, §2.2 | — |
| synthesis-34 | §7ter | The `apsw` wheel embeds SQLite 3.54.1 | true | PyPI `apsw` 3.54.1.0 | — |
| synthesis-35 | §7quinquies | nf-prov writes a Workflow Run RO-Crate since 1.4.0 | true | nf-prov `CHANGELOG.md:52-56` | — |
| synthesis-36 | §7quinquies | nf-core requires a pipeline RO-Crate that describes the pipeline, not runs | true | https://nf-co.re/docs/guidelines/pipelines/requirements/ro_crate | — |
| synthesis-37 | §1 item 2 (decision 0001) | A run can report to nf-tower and nf-spectio at once **[to be validated]** | partly (the code supports it) | `NF/Session.groovy:581-588` registers every `TraceObserverFactoryV2` | Keep the marker until spike T2 |

**Not checked in run 1:**
- **Deferred by schedulers §5:** LSF, PBS, Grid Engine and HTCondor command flags.
- **Open "to check" item:** Kueue and kubernetes Snakemake plugin labels (schedulers §1).
- **Minor or common-knowledge claims:**
  - `sshare -U`, `scrontab`, `loginctl enable-linger`;
  - `nf-co2footprint`, `ConsumedEnergy`;
  - TES 1.1.0, Airflow 3.1 HITL, Argo `suspend`, Prefect 3;
  - the Seqera Tower Agent transport;
  - Viv "Zarr v3 since 0.19";
  - S3 presigned URLs, Apptainer userns;
  - panoptes, snkmt and flowo details.
- **Engine event details:** Snakemake "SLURM ID reaches the logger only on error"; "JOB_FINISHED has no resource usage".
- **Internal environment tests:** uv Python SQLite 3.53.1, container SQLite 3.45.1.
- **Left to `depictio-liaison`:** Mantine 7 shared with depictio.

## Run 2 · architecture-plugins-and-packaging.md, dev-environment-and-testing.md, cli-and-shared-libraries.md

| ID | Location | Claim | Verdict | Source | Correction |
|---|---|---|---|---|---|
| A-1 | A §1 l.21 | Snakemake has one interface package per type: executor, storage, report, logger, software-deployment, plus common | partly | snakemake `1c67a66` `pyproject.toml:52-58` (also `snakemake-interface-scheduler-plugins`); snakedeploy templates `scheduler-plugins` | FC-023 |
| A-2 | A §1 l.23 | The registry walks `pkgutil.iter_modules()` and imports packages with the type's prefix | true | snakemake-interface-common `92e5024` `plugin_registry/__init__.py:92-98` | — |
| A-3 | A §1 l.24 | No entry points; a code comment says editable installs are not detected | true | same file `:86-91` | — |
| A-4 | A §1 l.25 | A missing or wrongly typed attribute raises `InvalidPluginException` | true | same file `:118-140` | — |
| A-5 | A §1 l.27 | Settings metadata: `help` required; `required`, `env_var`, `type`, `choices`, `nargs`, `parse_func`/`unparse_func`, `subgroup` optional | true | `plugin.py:49, 120-127, 146-148, 195, 268-273` | — |
| A-6 | A §1 l.28 | Derived names are `--<prefix>-<field>` and `SNAKEMAKE_<PREFIX>_<FIELD>` | true | `plugin.py:326-333` | — |
| A-7 | A §1 l.29 | `support_tagged_values` accepts `TAG::VALUE`; untagged values are the default | true (bool fields cannot be tagged, `plugin.py:292`) | `plugin.py:96, 193, 296-319` | — |
| A-8 | A §1 l.31 | Snakedeploy scaffolds a plugin with tests, CI and release automation | true | snakedeploy `55e916e` `client.py:245`; templates `ci.yml.j2`, `release_please.yml.j2` | — |
| A-9 | A §1 l.32 | The catalogue is built from PyPI and uses `docs/intro.md` / `docs/further.md` | true | catalog `d2c11a2` `source/collect_plugins.py:178-196, 283-284` | — |
| A-10 | A §2 l.68 | Airflow, Prefect and MLflow use one SQLAlchemy URL and a short list of backends | true | [Airflow DB](https://airflow.apache.org/docs/apache-airflow/stable/howto/set-up-database.html), [Prefect server](https://docs.prefect.io/v3/manage/server/index), [MLflow backend store](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/) | — |
| A-11 | A §2 l.62 | `nf-spectio` can be published in the Nextflow plugin registry | true | nextflow `114f1fe` `PluginsFacade.groovy:48` (`registry.nextflow.io/api`); the registry API returned 200 | — |
| A-12 | A §3.1 l.94 | `entry_points(group=…)` lists components without importing them | true | checked on CPython 3.13.17: listing 23 entry points imported 0 modules | — |
| A-13 | A §7.2 l.309 | Postgres 18 is used | true | [postgresql.org/support/versioning](https://www.postgresql.org/support/versioning/): released 2025-09-25, supported until 2030-11-14 | — |
| A-14 | A §7.2 l.319 | SQLite must not sit on a network file system | true | [sqlite.org/wal.html](https://www.sqlite.org/wal.html) §1 | — |
| A-15 | A §7.3 l.331 | "Python 3.10 reaches end of life in October 2026" | partly (stale tense) | [PEP 619](https://peps.python.org/pep-0619/): end of life since 2026-10-01 | FC-013 |
| A-16 | A §7.3 l.331 | "`uv tool install` brings its own managed Python" | wrong as a general statement | [uv: Python versions](https://docs.astral.sh/uv/concepts/python-versions/): with the default preference, a compatible system Python is used before uv downloads one | FC-004 |
| A-17 | A §7.3 l.331; D §1 l.43 | uv-managed Python embeds SQLite ≥ 3.51.3 | true for current builds | python-build-standalone `a3f2146` `pythonbuild/downloads.json`: SQLite 3.53.1 | — |
| A-18 | A §7.3 l.334 | `[saml]` is the only extra needing a system library, `xmlsec1` | partly (depends on the SAML library) | pysaml2 7.5.5 `saml2/sigver.py:160` calls the `xmlsec1` binary; xmlsec 1.3.17 manylinux wheels link libxmlsec1 statically; [python3-saml README](https://github.com/SAML-Toolkits/python3-saml) l.129 | FC-022 |
| A-19 | A §7.3 l.335 | The base install has no compiled dependencies beyond Pydantic's wheels | partly | PyPI metadata: httpx, typer and rich are pure Python, but `keyring` pulls `SecretStorage` and then `cryptography` on Linux | FC-014 |
| A-20 | A §7.4 l.358 | MinIO CE stopped publishing binaries in October 2025, and its repository is archived | true (the cited source is secondary) | minio `9e49d5e` (2025-10-15) "point to source only releases"; GitHub shows the repository archived on 2026-04-25 | Cite the primary sources (FC-037) |
| A-21 | A §7.4 l.358 | depictio: `chrislusf/seaweedfs` with `weed mini`, service `s3` with alias `minio`, `DEPICTIO_S3_*`, migration script | true | depictio `e40ca79` (v1.19.2) `docker-compose.yaml:41-64`; `scripts/migrate_minio_to_seaweedfs.py` | — |
| A-22 | A §7.5 l.365 | The migrate Job runs as a Helm pre-install / pre-upgrade hook and reads the chart's ConfigMap and Secrets | partly | [Helm hooks](https://helm.sh/docs/topics/charts_hooks/): pre-install "executes … before any resources are created" | FC-008 |
| A-23 | A §7.5 l.372 | Nextflow's Kubernetes executor needs an RWX PVC or Fusion | true | [docs.seqera.io/nextflow/kubernetes](https://docs.seqera.io/nextflow/kubernetes) | — |
| A-24 | A §7.5 l.373 | Snakemake's Kubernetes executor *can* use S3 storage instead of a shared file system **[to be validated]** | wrong (it must) | executor `d5f720e` `__init__.py:120-125` (`implies_no_shared_fs=True`); snakemake `1c67a66` `api.py:546-575` | FC-005 |
| A-25 | A §7.6 l.386 | CloudEvents has bindings for HTTP, MQTT, AMQP, Kafka and NATS | true | cloudevents/spec `1025510` `cloudevents/bindings/` | — |
| A-26 | A §7.6 l.405 | Celery: RabbitMQ, Redis and SQS are stable, Kafka is experimental, there is no SQL broker | true | [Celery 5.6.3 brokers](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/) | — |
| A-27 | A §7.6 l.406 | `depictio local up` runs Redis through py-rattler | true ("14 call sites" not checked) | depictio `0d1aa0a` `depictio/cli/cli/local_stack.py:45, 246-249` | — |
| A-28 | A §7.6 l.409 | Huey has SQLite, Postgres and Redis storage and is not asyncio-native | true | [Huey API](https://huey.readthedocs.io/en/latest/api.html) | — |
| A-29 | A §7.6 l.410 | Procrastinate is Postgres-only | true | [Procrastinate docs](https://procrastinate.readthedocs.io/en/stable/): "leveraging PostgreSQL 13+" | — |
| A-30 | A §7.6 l.411 | taskiq is async-native, with brokers for Redis, RabbitMQ, NATS and Kafka | true | [taskiq README](https://github.com/taskiq-python/taskiq) l.14, 38 | — |
| A-31 | A §4 l.202 | "recorded HTTP (respx)" | partly | [respx on PyPI](https://pypi.org/project/respx/): "utility for mocking", not recording | FC-024 |
| A-32 | A §4 l.204 | The scaffold CI tests Python 3.11–3.14 | partly (stale) | [PEP 790](https://peps.python.org/pep-0790/): 3.15.0 released 2026-10-09 | FC-013 |
| A-33 | A §6 l.247 | The web UI uses "Mantine 7" | partly (stale) | npm `@mantine/core` latest 9.7.4 (2026-10-25); depictio `0d1aa0a` `viewer/package.json:29` is `^7.14.0` | FC-025 |
| D-1 | D §0 l.17 | sind: Slurm 25.11 and 26.05 images, slurmdbd, slurmrestd with JWT, power-cycle, Action, MCP, no privileged containers, LGPL-3.0 | partly | sind `0065750` `README:25-36` and `LICENSE`; `docs/content/guides/rest-api.md:36` ("The 25.11 images have none") | FC-027 |
| D-3 | D §1 l.45 | Node.js 22 LTS | partly (stale) | [nodejs/Release schedule.json](https://github.com/nodejs/Release/blob/main/schedule.json): v22 in maintenance since 2025-10-21, end of life 2027-04-30; v26 Active LTS from 2026-10-28 | FC-013 |
| D-4 | D §1 l.46 | Java 21 (Temurin) for Nextflow | true | [docs.seqera.io/nextflow/install](https://docs.seqera.io/nextflow/install): "Java 17 (or later, up to 26)" | — |
| D-5 | D §1 l.47 | Nextflow is installed with the release launcher from GitHub releases **[to be validated: asset names, hosts]** | partly (marker resolved) | GitHub release v26.10.3 assets `nextflow` and `nextflow-26.10.3-dist` (HTTP 206); `-all` and `-one.jar` return 404; `get.nextflow.io:23, 284-289` downloads `nextflow-<v>-one.jar` from `www.nextflow.io/releases` | FC-030 |
| D-6 | D §1 l.48 | Snakemake 9 + `snakemake-executor-plugin-slurm`, `-kubernetes`, `-kueue` | partly | PyPI: slurm 2.8.0, kubernetes 0.5.1, **kueue 0.1.0 (2024-01-03)**; repository HEAD `c09bf0d` is from 2024-03-21; the README says "under development" | FC-009 |
| D-7 | D §1 l.49 | sind install method **[to be validated]** | true (marker resolved) | sind `README:40-44`: `curl -fLo sind …/releases/latest/download/sind-linux-amd64`; needs Docker ≥ 28 on cgroup v2 | FC-037 |
| D-8 | D §1 l.51 | Kueue is installed with `kubectl apply --server-side -f` | true | [Kueue install](https://kueue.sigs.k8s.io/docs/getting-started/installation/) (v0.20.3) | The same page recommends Kubernetes ≥ 1.34 (FC-029) |
| D-9 | D §2 l.71 | Cloud sessions: setup cached at about 5 min; 2 min default timeout, 10 max, 30 more in the background; `BASH_DEFAULT_TIMEOUT_MS`; Trusted / Custom / Full; plugins not loaded | true (a fourth network level, None, also exists) | [cloud-environments.md](https://code.claude.com/docs/en/cloud-environments.md) l.220-223, 293, 418-425, 449-455 | — |
| D-10 | D §2 l.77 | D2 hosts are added to the default list | true (`ghcr.io` and `conda.anaconda.org` are already in Trusted) | same page l.601, 765 | — |
| D-11 | D §2 l.74, §7.2 l.196 | Codespaces Free: 120 h and 15 GB, 2-core counts double, stops without a payment method | true | [Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces) | — |
| D-12 | D §4.2 l.121 | kind needs privileged node containers | true | kind `2b29beb` `pkg/cluster/internal/providers/docker/provision.go:221-226` | — |
| D-13 | D §7.1 l.166-168 | Cloudflare Pages: hash URLs stay reachable; the branch alias follows the latest deployment | true | [Preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/) | — |
| D-14 | D §7.1 l.180 | "Cloudflare Access can restrict them to Thomas" | partly | same page: the access policy restricts *preview* deployments and does not protect the production `*.pages.dev` | FC-031 |
| D-15 | D §7.1 l.182 | Free plan: 500 builds, 20 000 files, 25 MiB per file; whether direct uploads count as builds **[to be validated]** | limits true; counting unverifiable | [limits](https://developers.cloudflare.com/pages/platform/limits/), [direct upload](https://developers.cloudflare.com/pages/get-started/direct-upload/) (both silent on counting) | Keep the marker; step D5 settles it |
| D-16 | D §7.2 l.194 | `codespaces.new/<o>/<r>/tree/<branch>?quickstart=1` | true | [GitHub docs](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/setting-up-your-repository/facilitating-quick-creation-and-resumption-of-codespaces) | — |
| D-17 | D §7.2 l.197 | A public forwarded port at `<codespace>-<port>.app.github.dev` needs no sign-in | true | [Forwarding ports](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace) | — |
| D-18 | D §2 l.78, §8 | Claude Code features: agent-teams environment variable, auto-fix needs the GitHub App, `isolation: worktree`, routines | true | code.claude.com `agent-teams.md` l.11, 48; `claude-code-on-the-web.md` l.50-55; `sub-agents.md` l.223, 270; `routines.md` (HTTP 200) | — |
| D-19 | D §10.2 l.313 | mag 5.5.0 and ampliseq 3.0.0 need Nextflow ≥ 26.04 | true | nf-core/mag@5.5.0 `nextflow.config:539`; nf-core/ampliseq@3.0.0 `nextflow.config:285` | — |
| D-20 | D §10.2 l.314 | Private-repository GitHub runners have 2 CPU / 8 GB | true | [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) | — |
| D-21 | D §10.3 l.319 | Megatests are at `s3://nf-core-awsmegatests/<pipeline>/results-<commit>/` | true | S3 ListObjectsV2 on `rnaseq/results-`, 2026-10-26 | — |
| D-22 | D §10.3 l.331 | Megatest outputs "are derived from nf-core/test-datasets" **[to be validated]** | wrong | nf-core/rnaseq@3.27.0 `conf/test_full.config:17` points to a test-datasets samplesheet whose reads are `s3://ngi-igenomes/test-data/rnaseq/SRX…` (public SRA), with genome `GRCh37` (iGenomes) | FC-028 |
| D-23 | D §10.4 l.351 | IDR studies are CC BY 4.0 as a rule **[to be validated per study]** | partly | IDR study files: idr0033, idr0062, idr0066 and idr0076 say "Study License CC BY 4.0"; idr0001, idr0054 and idr0073 were not resolved | FC-037 |
| D-24 | D §11 l.359-361, §12 l.371 | `nf-core/setup-nextflow@v3`, `snakemake-github-action@v2`, `sind-action@v2`, `kind-action@v1`, `metadata-action@v6` | true | `git ls-remote --tags` on each repository (floating major tags exist) | — |
| D-25 | D §11 l.360 | sind needs cgroup v2 Docker; GitHub runners have it; this session is cgroup v1 | true | sind-action@v2 `README:31-42`; `stat -fc %T /sys/fs/cgroup` returned `tmpfs` | — |
| D-26 | D §12 l.370-389 | release-please: `bump-minor-pre-major`, `release-as`, `linked-versions`, `release-type: simple`, `release-pr --dry-run` | true | release-please `c589293` `docs/manifest-releaser.md:171-175`; `src/plugins/linked-versions.ts`; `docs/cli.md:20, 206` | — |
| D-27 | D §12 l.388 | Whether a visible changelog section alone makes a commit releasable **[to be validated]** | true (marker resolved) | `c589293` `src/strategies/base.ts:331-337`: a release is skipped only when the generated changelog is empty | FC-037 |
| D-28 | D §10.1 l.288-290, §11 l.358 | Nextflow 26.10.3 and 25.10.9 and Snakemake 9.27.1 exist | true (26.10.4 is also out) | Nextflow tags; PyPI snakemake 9.27.1 (2026-10-21) | — |
| D-29 | D §3, §10.1 | Snakemake `--until`, `--forcerun`, `--workflow-profile`, `--sdm`, `--logger` | true | snakemake `1c67a66` `src/snakemake/cli.py:498, 839, 893, 1623, 1712` | — |
| C-1 | C §0.3 l.19 | The base install is "httpx, pydantic, typer, rich and nothing else" | partly | see A-19; C §3 l.115 uses `keyring:` | FC-014 |
| C-2 | C §0.3 l.19 | depictio's base CLI pulls polars, deltalake and pandas, about 0.9 GB | true | depictio `e40ca79` `pyproject.toml`; `dev/design/local-server-profile.md:69` | — |
| C-3 | C §0.4 l.20 | depictio's `api_calls.py` is about 1,500 lines | true (1,521) | depictio `0d1aa0a` `depictio/cli/cli/utils/api_calls.py` ("255 TS types" not checked) | — |
| C-4 | C §1 l.27 | depictio uses `~/.depictio/CLI.yaml`, `DEPICTIO_CLI_TOKEN`, `DEPICTIO_CLI_API_BASE_URL` | true | `depictio/cli/cli/utils/common.py:266-318` | — |
| C-5 | C §1 l.27 | LabID uses `~/.labid/labidapi.yml` and `labid config` with `setup`, `show`, `switch`, `refresh` | true | labid-cli `5af9e16` `labidcli/__init__.py:120`; `config.py:62, 127, 157, 187` | — |
| C-6 | C §1 l.28-29 | LabID: `POST token-auth/`, then `Bearer` or `Token`; requests session; `list_all` | true | labid-lib `cd14636` `src/labidlib/api/client.py:242, 261-278, 414` | — |
| C-7 | C §1 l.29 | depictio retries on "408/425/429/5xx" | partly | `depictio/cli/cli/utils/http_retry.py:50` is `{408, 425, 429, 500, 502, 503, 504}` | FC-026 |
| C-8 | C §1 l.32 | depictio telemetry uses PostHog, opt-out, `DO_NOT_TRACK` | true | `depictio/cli/cli/utils/telemetry.py:170, 249` | — |
| C-9 | C §1 l.33 | LabID sniffers load from directories on `sys.path` | true | labid-lib `src/labidlib/core/assaysniffer/registry.py:101` | — |
| C-10 | C §4 l.127 | The `bioplatform-` prefix is free on PyPI | true (2026-10-26) | PyPI JSON returns 404 for `bioplatform`, `-client`, `-models`, `-runinfo` (also `spectio` and `spectio-sdk`) | — |
| C-11 | C §5 l.163 | depictio hard-codes `/depictio/api/v1`; `authFetch` handles refresh | true | depictio `viewer/src/EditorApp.tsx:191`; `packages/depictio-react-core/src/api.ts:6` | — |
| C-12 | C §5 l.145, 162 | `openapi-python-client` and `openapi-typescript` | true | PyPI 0.29.1; npm 7.13.0 | — |
| C-13 | C §6 l.173 | `depictio-cli` is an alias package | true | PyPI depictio-cli 1.19.2 requires `depictio==1.19.2` | — |

**Not checked in run 2:**
- Snakemake codebase docs quote "strongly typed abstract base classes" (A §1).
- PodSecurity `restricted`; Postgres `SKIP LOCKED`, `LISTEN/NOTIFY` and advisory locks; RFC 9457 and RFC 8628.
- pydantic-settings `__` nesting (a configuration choice: `env_nested_delimiter` has no default).
- `copier update`, PyPI trusted publishing, CloudNativePG `Cluster`.
- Landsat public domain and IDR image dimensions (D §10.4).
- depictio's "14 call sites", "255 TS types" and Typer help-panel names.

## Run 3 · api-and-data-model.md, checking-scenarios.md, admin-and-operations.md

| ID | Location | Claim | Verdict | Source | Correction |
|---|---|---|---|---|---|
| api-and-data-model-1 | §4 | Errors use RFC 9457 `application/problem+json` | true | rfc-editor.org/rfc/rfc9457 (obsoletes 7807) | — |
| api-and-data-model-2 | §4 | `Deprecation` and `Sunset` headers | true | RFC 9745 (March 2025), RFC 8594 | Cite them (FC-037) |
| api-and-data-model-3 | §4 | Per-token rate limits with `RateLimit-*` headers | partly | draft-ietf-httpapi-ratelimit-headers-11 (2026-05-23; still an Internet-Draft, expires 2026-11-24) defines only `RateLimit-Policy` and `RateLimit` | FC-036 |
| api-and-data-model-4 | §5 | SSE can resume with `Last-Event-ID` | true | html.spec.whatwg.org/multipage/server-sent-events.html | — |
| api-and-data-model-5 | §2B, §10 | WES 1.1 has a `PAUSED` state | true | WES 1.1.0 `workflow_execution_service.openapi.yaml:666, 685` | — |
| api-and-data-model-6 | §2B | WES clients send `workflow_type: NFL` or `SMK` | partly | WES 1.1.0 `:753`: "must be "CWL" or "WDL" currently (or another alternative supported by this WES instance)"; NFL and SMK are TRS descriptor types | FC-036 |
| api-and-data-model-7 | §7; admin §3.5 | SQLite ≥ 3.51.3 is required | partly | sqlite.org/wal.html §11: fixed in 3.51.3, backported to 3.44.6 and 3.50.7; releaselog/3_51_3 | FC-010 |
| api-and-data-model-8 | §7 | JSON stored in TEXT through SQLite JSON1 | true | sqlite.org/json1.html §2: built in by default since 3.38.0 | — |
| api-and-data-model-9 | §8 | CloudEvents 1.0 envelope (`id`, `source`, `type`, `time`, `subject`, `data`) | partly | CloudEvents v1.0.2 `spec.md:248-315` lists `specversion` as REQUIRED; `extensions/sequence.md` defines `sequence` | FC-035 |
| api-and-data-model-10 | §8 | Extensions named `spectioproject` and `spectiosequence` | true | `spec.md:173-175`: lower-case a–z and 0–9, SHOULD be ≤ 20 characters | — |
| api-and-data-model-11 | §10 | Workflow RO-Crates can be imported from nf-core | true | rnaseq 3.27.0 `ro-crate-metadata.json` conforms to `workflowhub/workflow-ro-crate/1.0` | — |
| api-and-data-model-12 | §10 | Workflow Run and Provenance Run Crate profiles | true | w3id.org/ro/wfrun/workflow/0.5 and …/provenance/0.5 resolve (HTTP 200) | — |
| api-and-data-model-13 | §5 | The example uses nf-core/rnaseq 3.27.0 | true | pipelines.json: 3.27.0 published 2026-09-23 | — |
| api-and-data-model-14 | §10 | `nf-spectio` and `nf-tower` can report in the same run **[to be validated]** | unverifiable (the code supports it) | `Session.groovy:581-590` registers every `TraceObserverFactoryV2`; `TowerFactory.groovy:38`, enabled at `:84` | Keep the marker; spike T2 settles it |
| api-and-data-model-15 | §13.1 | depictio login: password, Google OAuth, SAML, magic links; no OIDC | true | `depictio/api/v1/endpoints/auth_endpoints/` has only `google_oauth_routes.py` and `saml_routes.py` | — |
| api-and-data-model-16 | §13.1 | depictio issues RS256 JWTs | true (the default) | `settings_models.py:419-420` (`keys_algorithm` default RS256; RS512 and ES256 also allowed); `user_endpoints/utils.py:141` | Optional: "RS256 by default (configurable)" |
| api-and-data-model-17 | §13.1 | Anonymous admin `anonymous@depict.io` | true | `settings_models.py:483` | — |
| api-and-data-model-18 | §13.1 | The depictio CLI uses `~/.depictio/CLI.yaml` and `DEPICTIO_CLI_*` | true | `projects/test/catalog_cli_smoke/README.md:48`; `penguins_versioned/rebuild_demo.py:840` | — |
| api-and-data-model-19 | §13.2 | Group fields `users_ids`, `admin_ids`, `pi_id`, `sso_managed` | true | `models/models/users.py:188-195` | — |
| api-and-data-model-20 | §13.2 | Project has `is_public` and `viewers`/`editors`/`owners`/`group_viewers` | true | `projects.py:36`; `users.py:371-379` | — |
| api-and-data-model-21 | §13.3 | depictio has templates for about 35 nf-core pipelines | partly | 32 pipelines and 41 versioned `template.yaml` under `depictio/projects/nf-core/` | FC-011 |
| api-and-data-model-22 | §13.3 | The runner runs `depictio-cli ingest … --user <owner email>` with a short-lived credential | wrong | `cli/cli/commands/run.py:1637-1643`: "--user requires --provisioning-key (or the DEPICTIO_AUTH_PROVISIONING_API_KEY environment variable)"; help text `:3104-3108` | FC-003 |
| api-and-data-model-23 | §13.3 | depictio's Nextflow `onComplete` trigger can be turned off with `--depictio_enabled false` | true | `cli/configs/nextflow/depictio.config:36, 72, 112` | — |
| api-and-data-model-24 | §13.3 | depictio has no Snakemake trigger | true | `cli/configs/` holds only `nextflow/` and `nf-core/` | — |
| api-and-data-model-25 | §13.5; admin §4.1 | `BrandTheme` field list | true | `models/models/branding.py:320-368` | — |
| api-and-data-model-26 | §13.6; checking §11.6 | Catalogue STAR/Salmon read `**/multiqc/multiqc_data/multiqc.parquet` | true | `depictio/catalog/multiqc/star.yaml:8`, `salmon.yaml:8` | — |
| checking-scenarios-1 | §0, §10 | 159 repositories, 106 released and not archived | true | pipelines.json fetched 2026-10-26: 159 / 106 | — |
| checking-scenarios-2 | §0 | 96 of 106 produce MultiQC | true | reproduced from `modules.json` and `docs/output.md`; the 10 without: bacmodel, diaproteomics, differentialabundance, drugresponseeval, genomeassembler, imcyto, pixelator, plasmodiumdrugres, proteogenomicsdb, sopa | — |
| checking-scenarios-3 | §0 | 86 produce other HTML reports; 25 declare groups | unverifiable as stated | hand criteria (`docs/research/data/analysis.json`); mechanical counts give 98 and 19 | FC-011 |
| checking-scenarios-4 | §1 | Every named pipeline is released and not archived | true | all 72 named pipelines are in the 106-set | — |
| checking-scenarios-5 | §9 | Bulk sample (45): checks with no extra code, from MultiQC | partly | differentialabundance (in the bulk list) has no MultiQC; neither does pixelator (cells class) | FC-011 |
| checking-scenarios-6 | §11.1 | `onFilePublish(FilePublishEvent)` carries `source`, `target`, `labels` | true | `dfa5c1c` and `114f1fe`: `TraceObserverV2.groovy:140`, `FilePublishEvent.groovy:32-48`; emitted after the copy, `FilePublisher.groovy:301` | — |
| checking-scenarios-7 | §11.1 | `onTaskComplete(TaskEvent)` carries the handler and trace record | true | `TraceObserverV2.groovy:99`, `TaskEvent.groovy:31-40` | — |
| checking-scenarios-8 | §11.1 | Declared outputs can be read through the handler **[to be validated]** | true in code (internal API) | `TaskPollingMonitor.groovy:765-770` (`finalizeTask` before `notifyTaskComplete`); `TaskProcessor.groovy:1484-1520`; `TaskRun.groovy:100` | FC-034 |
| checking-scenarios-9 | §11.1 | `onWorkflowOutput` is emitted when the output is complete | true | `TraceObserverV2.groovy:123-132` | — |
| checking-scenarios-10 | §11.1 | `JOB_INFO` fields `jobid`, `rule_name`, `input`, `output`, `log`, `wildcards` | true | `src/snakemake/jobs.py:1028-1045` | — |
| checking-scenarios-11 | §11.1 | `JOB_FINISHED` is not emitted under `--quiet progress` or in a dry run | partly | `job_scheduler.py:90-92, 474-484`; a plain `-q` also suppresses it; `logging.py:404-424, 691`: `JOB_INFO` is dropped under `--quiet rules` for plugins without `has_filter` | FC-032 |
| checking-scenarios-12 | §11.2 | `multiqc -m <module> <file>` parses a single file; start-up time unknown **[to be validated]** | true, measured | MultiQC 1.35: `multiqc -m star S1.Log.final.out` gives sample `S1`; 2.3–2.6 s per call; 50 files in one call took 2.7 s | FC-033 (column names: see UX-101 in [R12-ui-scenarios.md](R12-ui-scenarios.md)) |
| checking-scenarios-13 | §11.1 | Files on object storage are read with the run's own credentials **[to be validated]** | unverifiable | — | Needs a per-provider spike (see [R2-open-validations.md](R2-open-validations.md), part B) |
| checking-scenarios-14 | §11.3 | An `ext.when` closure is evaluated per task, at task creation **[to be validated]** | partly | per task, before submit: `TaskProcessor.groovy:692-694, 1908-1913`; `TaskConfig.groovy:132-134`; but rnaseq 3.27.0 already sets `ext.when = { !params.use_rustqc }` (`conf/modules/markduplicates.config:30`) | FC-002 |
| checking-scenarios-15 | §11.3 | Snakemake has no conditional `--until`, so Spectio stops the run with SIGINT **[to be validated]** | partly (the method is wrong) | `--until` and `--omit-from` are static (`cli.py:893-915`); SIGTERM gives a graceful stop (`job_scheduler.py:171, 241-245, 574-577`); SIGINT cancels running jobs (`:398-403`) | FC-001 |
| checking-scenarios-16 | §11.5 | The end of a stage is only known when the upstream channel closes **[to be validated]** | partly | `TraceObserverV2.onProcessTerminate` fires when "all process tasks have completed": `TraceObserverV2.groovy:63-69`, `TaskProcessor.groovy:2003-2006` | FC-034 |
| checking-scenarios-17 | §6.2 | Snakemake `--forcerun` accepts the item's output files | true | `cli.py:839-849` ("given rules or files") | — |
| checking-scenarios-18 | §11.1 | `--logger spectio` | true | `cli.py:1623-1628` (logger plugin registry) | — |
| admin-and-operations-1 | header | depictio v1.19.2 (commit `0d1aa0a`) | partly | `0d1aa0a` is "Update CHANGELOG.md for v1.19.2"; tag `v1.19.2` (object `cf022cb`) points to `e40ca79` | FC-011 (citation policy: DEP-T-031 in [R8b-depictio-tooling.md](R8b-depictio-tooling.md)) |
| admin-and-operations-2 | §2.1 | 14-character generated password | true | `viewer/src/admin/CreateUserModal.tsx:36` | — |
| admin-and-operations-3 | §2.2 | `admin` and `users` groups are protected | true | `groups_endpoints/routes.py:49-54` | — |
| admin-and-operations-4 | §3.1 | Task kinds are fixed (`JobKind`) | true | `models/models/jobs.py:48` | — |
| admin-and-operations-5 | §3.1 | 500-line log buffer; Celery signals | true | `monitoring/task_signals.py:20-24, 35` | — |
| admin-and-operations-6 | §3.1 | Atomic DB claim per slot, no Celery beat | true | `tasks/cleanup_tasks.py:169-184` | — |
| admin-and-operations-7 | §3.4 | depictio's capture floor defaults to WARNING and is not persisted | true | `monitoring/log_handler.py:66`; `monitoring_endpoints/routes.py:529-533` | — |
| admin-and-operations-8 | §3.5 | depictio's Health checks only workers and broker | true | `monitoring_endpoints/routes.py:554-555` | — |
| admin-and-operations-9 | §4.1 | Presets depictio, TREC, EMBL, Ocean | true | `branding.py:507-535` | — |
| admin-and-operations-10 | §4.1 | Logo: PNG, JPEG or WebP, ≤ 2 MB, never SVG | true | `services/branding.py:231-241` | — |
| admin-and-operations-11 | §4.1 | `/depictio/api/v1/utils/public-config` | true | `utils_endpoints/routes.py:171`; `routers.py:100-101`; `main.py:264-265` | (co-hosting: DEP-T-013) |
| admin-and-operations-12 | §4.1, §4.5 | `saml_login_label`, `locked_by_env` | true | `settings_models.py:546`; `AdminSettingsPanel.tsx:149` | — |
| admin-and-operations-13 | §4.3 | Smart GFS retention: 30 daily, 4 weekly, 12 monthly | true (as a UI preset) | `AdminBackupsPanel.tsx:82-86`; the environment defaults are 30 / 0 / 0 (`settings_models.py:1319-1337`) | — |
| admin-and-operations-14 | §4.3 | Tokens are not restored; ingestion history is excluded, and the docs say so | true | `backup_endpoints/routes.py:555`; `docs/backup-restore.md:35-43` | — |
| admin-and-operations-15 | §4.3 | A coverage test checks backed-up tables; a weekly cross-version restore job | true | `cli/cli/utils/backup_validation.py:275-300`; `.github/workflows/backup-compat-cross-version.yaml:22-24` | — |
| admin-and-operations-16 | §4.3 | The orphan-cleanup hazard after a rewind is documented | true | `docs/backup-restore.md:190-194` | — |
| admin-and-operations-17 | §4.3 | `migrate --project`, `local export`, MinIO → SeaweedFS script, S3 allow-list | true | `cli/commands/migrate.py:110`; `local.py:660`; `scripts/migrate_minio_to_seaweedfs.py`; `migrate_endpoints/routes.py:189-193` | — |
| admin-and-operations-18 | §4.3 | Fernet-encrypted storage configs; no migration framework in depictio | true | `api/v1/crypto.py`, `storage_config.py`; no Alembic or migration library in the tree | — |
| admin-and-operations-19 | §4.3 | Alembic `render_as_batch` for SQLite | true | alembic.sqlalchemy.org/en/latest/batch.html | — |

**Not checked in run 3:**
- **api-and-data-model:** §6 SCIM, LDAP and the RFC 8628 device flow; §9 `frame-ancestors`; §13.1 Keycloak testing.
- **checking-scenarios:**
  - the §3 evidence tool list;
  - §4 preset metrics (MIMAG, FRiP, NSC/RSC, TSS);
  - §6.1 and §6.2 Nextflow `-resume` invalidation;
  - §6.4 scrnaseq outputs;
  - §11.5 `temp()`.
- **admin-and-operations:**
  - §1 trusted-instance rule;
  - §2.2 and §2.4 UI strings;
  - §3.2 watchers "Run now";
  - §4.1 "Powered by" rule;
  - Helm hook Job, `age`, `tar.zst`, Celery-plugin parity.

## Not covered by this round

[telemetry-and-analytics.md](../specs/telemetry-and-analytics.md), [ui-spec.md](../specs/ui-spec.md), [authentication-and-access.md](../specs/authentication-and-access.md), [depictio-ecosystem-reuse.md](../specs/depictio-ecosystem-reuse.md) and [documentation-system.md](../specs/documentation-system.md) were not in R2's scope (`docs/playbooks/next-phase.md`). Their `[to be validated]` markers are still listed, with a way to settle each, in [R2-open-validations.md](R2-open-validations.md), part B.
