# Spectio — HPC schedulers, Kubernetes and monitoring

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)
Companion docs:
- [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md): launcher plugins, runner.
- [`synthesis.md`](synthesis.md): §2ter on retries and job arrays, §7 stack.
- [`admin-and-operations.md`](admin-and-operations.md): Health, the runner registry.
- [`ui-spec.md`](ui-spec.md): §4.4 Run detail, §4.8 Environments.

## 0. Decisions in brief

1. **Spectio does not re-poll the scheduler for task states.** The engines already do it:
   - Nextflow runs `squeue` every minute;
   - the Snakemake SLURM plugin runs `sacct` or `squeue`, backing off from 40 s up to 180 s.
   
   Task states reach Spectio from the engine (Tower protocol, logger plugin). The scheduler is asked only for what the engines do not report:
   - why a job waits, and when it will start;
   - what it really used;
   - why it died;
   - what the cluster can take right now.
2. **One batched query per runner, not per run.** A runner asks the scheduler once per interval about all jobs of its user and shares the answer across every run. The load on `slurmctld` and `slurmdbd` therefore does not grow with the number of runs, and each layer has a budget an admin can change.
3. **Three transports, tried in this order:**
   - **CLI with JSON output** (`squeue/sacct/sinfo --json`): works everywhere, runs as the user.
   - **slurmrestd**, when the site offers it.
   - **Push**, when the site enables it: Slurm's `jobcomp/kafka` read through Spectio's Kafka bridge, or HTCondor and Flux event logs.
   
   On Kubernetes the runner uses the **watch API** (no polling) and, if installed, Kueue's visibility API.
4. **Engine tasks are joined to scheduler jobs by the IDs the engines report.**
   - Nextflow sends each task's `nativeId`.
   - Snakemake names every SLURM job with a per-run UUID and an optional prefix, and puts the rule and wildcards in the job comment.
   - Nextflow labels every pod with `nextflow.io/runName`, `nextflow.io/taskName`, `nextflow.io/processName` and `nextflow.io/sessionId`.
   
   Spectio adds its own tags only to the head job and, on Kubernetes, a `spectio.io/run-id` label.
5. **The scheduler data turns into decisions.** Spectio shows plain-language pending reasons and estimated start times, classifies failures (out of memory, timeout, preempted, node failure), and proposes relaunch changes from accounting ("STAR_ALIGN died 3 times at 64 GB → 96 GB").
   - **Pre-flight checks before a launch:** walltime limits, partitions, maintenance reservations, storage quotas, scratch purge.
6. **Everything is a launcher plugin with an observer part.** Built-in: local and SLURM. Plugins: Kubernetes, LSF, PBS Pro / OpenPBS, Grid Engine, HTCondor, Flux. Each plugin declares which monitoring layers it supports, and the UI hides what is missing.

## 1. What the engines already do (verified)

| Engine · scheduler | How it tracks jobs | What it does not give Spectio |
|---|---|---|
| **Nextflow · SLURM** | `squeue --noheader -o '%i %t' -t all -u $USER` (optionally `-p <queue>`), or `--only-job-state` (SLURM ≥ 24.05, lighter on the controller) when `executor.onlyJobState`; every `executor.queueStatInterval` (default 1 min) (`SlurmExecutor.groovy`, Nextflow docs) | pending reason, estimated start, accounting beyond `trace` (`%cpu`, `peak_rss`), failure class from the scheduler, cluster capacity |
| **Nextflow · Kubernetes** | creates one Kubernetes `Job` per task (default since 26.10; `Pod` before) with labels `nextflow.io/app=nextflow`, `runName`, `taskName`, `processName`, `sessionId`, `queue`; successful pods are deleted (`k8s.cleanup`, default true) | scheduling reasons, image-pull errors, evictions, OOMKilled before the trace is written, quotas, Kueue queue position |
| **Snakemake · SLURM plugin** | `--slurm-status-command sacct\|squeue` (sacct by default when `MinJobAge` is too low for squeue); first check after 40 s, then +10 s per round without finished jobs up to 180 s; job name = run UUID (`SLURM run ID: …` in the log, optional `jobname_prefix`); comment `rule_<name>_wildcards_<…>`; optional efficiency report | pending reasons, capacity, efficiency during the run (the report comes only at the end) |
| **Snakemake · Kubernetes / Kueue plugins** | executor plugins `kubernetes` and `kueue` in the catalogue | to check: pod labels and how status is read |
| **Head process** | neither engine watches its own head job | Spectio's launcher does (§3.1) |

Nextflow's grid executors also cover LSF, SGE, PBS Pro and others. Snakemake's catalogue lists 28 executor plugins, including `lsf`, `sge`, `htcondor`, `flux`, `kubernetes`, `kueue`, `tes`, `googlebatch`, `aws-batch` and `azure-batch`. Spectio's scheduler plugins sit next to these, not in place of them: the engine still submits the tasks.

## 2. Five things Spectio asks a scheduler

| Layer | Question | SLURM | Kubernetes | Used in |
|---|---|---|---|---|
| **L1 · Head job** | is the engine's head process alive, and where? | `sbatch --parsable` (head job), `squeue -j`, `sacct -j`, `scancel` | head pod or Job: watch, logs, delete | launch, cancel, relaunch, runner restart |
| **L2 · Waiting** | why is it pending, and until when? | `squeue --me --json` (state, `reason`, `start_time` estimated by the backfill scheduler), `sprio` (priority factors), `sshare -U` (fairshare) | pod condition `PodScheduled=False` (reason, message), events `FailedScheduling`, Kueue `Workload` conditions and visibility positions | task rows, Run detail → Scheduler |
| **L3 · Outcome** | what did it use, and why did it end? | `sacct --json -j <ids>` (state, exit code, reason, elapsed, `TotalCPU`, TRES requested and used: `mem` max RSS, `gres/gpu`, energy when accounting is enabled) | container `lastState.terminated.reason` (`OOMKilled`, `Error`), Job `BackoffLimitExceeded` / `DeadlineExceeded`, eviction and preemption events, `metrics.k8s.io` usage while running | failure classes, relaunch suggestions, efficiency |
| **L4 · Capacity** | can this environment take the launch? | `sinfo --json` (partitions, node states, free CPUs/GPUs, `MaxTime`), `scontrol show reservation`, association and QoS limits (`sacctmgr show assoc where user=$USER`), storage quotas | `ResourceQuota` status (used / hard), `LimitRange`, node pools and allocatable GPUs (needs cluster read), Kueue `ClusterQueue` quota and usage, PVC capacity | Environments, launch pre-flight |
| **L5 · Reachability** | can the runner talk to the scheduler, and how fast? | command latency and errors, `slurmctld` timeouts | API latency, watch reconnects | Health → Runners |

## 3. How the runner observes

### 3.1 Head job

On HPC the engine's head process is run as a **head job**: `sbatch` with few resources (e.g. 2 CPUs, 4 GB) and a long walltime, named `spectio-<run_id>`, with `--comment=spectio:<run_id>`. This is the recommended mode because login nodes usually kill long processes.
- **Alternative:** head on a service node allowed by the site, as a plain process supervised by the runner.
- **Walltime.** The launcher watches the head job's walltime. Twelve hours before the limit it warns, so the user can let it end and resume. Resuming is safe because the engine caches the completed work.
- **Runner restart.** When a runner restarts, it reconciles: running head jobs from `squeue --me --name 'spectio-*'`, finished ones from `sacct`. No run is lost (synthesis §7 risk register).

### 3.2 Batched observation and budgets

One `SchedulerObserver` per runner keeps a cache of all jobs of its user. Each layer has its own default interval:

| Query (SLURM) | Default interval | Scope |
|---|---|---|
| `squeue --me --json` | 60 s, only while the runner has active runs | every pending and running job of the user, all runs at once |
| `sacct --json -j <ids>` | when jobs leave `squeue`, batched by 200; once more when a run ends | finished jobs only |
| `sinfo --json`, partitions | 5 min | partitions used by this environment |
| `scontrol show reservation` | 15 min | maintenance windows |
| `sshare -U`, `sacctmgr show assoc` | 30 min | fairshare and limits of the user |
| Storage quotas (`lfs quota -u`, `mmlsquota`, `beegfs-ctl --getquota`, `df` / `df -i`) | 15 min | work and results directories |

- **Back-off.** On a timeout the interval doubles, up to 10 min, and the layer shows as stale in the UI.
- **Site policy.** Some sites rate-limit controller RPCs (`SlurmctldParameters=rl_enable`). The admin lowers or switches off any layer in the environment settings, e.g. `observer.squeue_interval: 120s`, `observer.capacity: off`.
- **One extra call, not one per run.** Spectio's `squeue` adds one call per minute per user on top of the engine's, whatever the number of runs. For L1 and L2 it can replace a Nextflow run's own polling only if a future companion plugin feeds states back; that is not planned.

### 3.3 Transports

| Transport | When | Notes |
|---|---|---|
| **CLI with `--json`** (default) | always on a login node | runs as the user, so it sees exactly what the user is allowed to see; JSON avoids parsing fragile text formats |
| **slurmrestd** | the site runs it with JWT auth | the OpenAPI plugin versions in use on Slurm 26.05 are `data_parser` v0.0.42 to v0.0.45. The runner reads `GET /openapi/v3` at start and picks the newest version both sides know ([Slurm REST release notes](https://slurm.schedmd.com/rest_release_notes.html)). Lets a runner live off the login node |
| **jobcomp/kafka** (push, site-installed) | the site publishes job records to Kafka | `JobCompType=jobcomp/kafka`; JSON job records at completion and, since Slurm 25.05, optionally at start; topic defaults to the cluster name ([jobcomp/kafka guide](https://slurm.schedmd.com/jobcomp_kafka.html)). Spectio's Kafka bridge consumes it, so terminal states and accounting arrive within seconds and `sacct` calls drop |
| **HTCondor job event logs** | HTCondor | the job event log file can be followed instead of querying the schedd, as `condor_watch_q` does ([man page](https://www.mankier.com/1/condor_watch_q)) |
| **Flux event logs** | Flux | job event logs can be watched through the Python bindings (`flux.job` watchers) ([Flux docs](https://flux-framework.readthedocs.io/projects/flux-core/en/stable/python/job_submission.html)) |
| **Kubernetes watch** | Kubernetes | informers on pods, jobs and events in the work namespace, with label selectors and resource versions; no polling |

### 3.4 Joining engine tasks and scheduler jobs

| Engine | Key | Fallback |
|---|---|---|
| Nextflow on a grid | task `nativeId` (Tower protocol, trace `native_id`) = scheduler job ID | job name `nf-<PROCESS>_(<tag>)` + submit time |
| Snakemake SLURM | job name = run UUID; Spectio sets `--slurm-jobname-prefix spectio-<run_id>`, then `sacct --name` / `squeue --name`; comment `rule_<rule>_wildcards_<…>` maps a job to the rule | the logger's job submission events |
| Nextflow on Kubernetes | labels `nextflow.io/runName` + `taskName`; Spectio adds `spectio.io/run-id` through the generated `k8s.pod` label option | — |
| Job arrays | the parent job ID plus each array element (`<id>_<n>`) are stored n:m with engine attempts (synthesis §2ter) | — |

### 3.5 Turning records into meaning

**Pending reasons** are mapped to plain language. The raw reason stays visible.

| SLURM reason | Shown as | Hint |
|---|---|---|
| `Priority` | waiting for higher-priority jobs | estimated start (backfill), your fairshare |
| `Resources` | waiting for free nodes | partition load |
| `QOSMaxJobsPerUserLimit`, `AssocGrpCPULimit`, `AssocGrpMemLimit`, … | at your group's or QoS limit | which limit, how much is used |
| `ReqNodeNotAvail, Reserved for maintenance` | blocked by a maintenance window | reservation start and end |
| `PartitionTimeLimit` | will never start: walltime above the partition maximum | suggest the right partition or time (pre-flight catches this) |
| `Dependency`, `DependencyNeverSatisfied` | waiting for another job / will never start | link to that job |
| `JobHeldUser`, `JobHeldAdmin` | held | who can release it |

**Failure classes** come from the `sacct` state, exit code and reason, or from the Kubernetes container state and events:

| Class | SLURM | Kubernetes | Relaunch suggestion |
|---|---|---|---|
| Out of memory | `OUT_OF_MEMORY` | `OOMKilled` | raise memory for this process, sized from max RSS and the attempts so far |
| Timeout | `TIMEOUT` | `DeadlineExceeded` | raise time; use a longer partition if the limit is reached |
| Preempted / evicted | `PREEMPTED` | eviction, preemption event | retry is usually enough; avoid preemptible queues or spot nodes for long tasks |
| Node failure | `NODE_FAIL`, `BOOT_FAIL` | node lost, pod deleted | retry; exclude the node (Snakemake has `exclude_failed_nodes`) |
| Cancelled by someone else | `CANCELLED by <uid>` | deleted by another principal | show who; no automatic retry |
| Image or environment | — | `ImagePullBackOff`, `ErrImagePull`, `CreateContainerConfigError` | registry credentials or rate limit, image name |
| Tool error | `FAILED` with an exit code | `Error` with an exit code | open the task log; no resource change |

**Efficiency.**
- CPU efficiency = `TotalCPU / (Elapsed × AllocCPUS)`.
- Memory efficiency = max RSS / requested memory.
- GPU usage comes from TRES when the site accounts for it.
- Energy comes from `ConsumedEnergy` when energy accounting is enabled. It can feed a carbon estimate alongside the Nextflow `nf-co2footprint` plugin.

Spectio reports the waste too: for example "17 tasks used under 25 % of their memory: lowering it helps the group's fairshare".

**Pre-flight checks** run before a launch, using L4 data:
- requested walltimes against partition maxima;
- memory or GPU requests that no partition can satisfy;
- maintenance reservations that start before the estimated run time ends;
- storage quota and inode headroom against the estimated output;
- work directories that the scratch purge policy will delete before a `-resume` (e.g. "files untouched for 30 days are deleted");
- container cache presence.

Each check gives ✓ / ⚠ / ✗, and ✗ blocks the launch unless overridden.

## 4. Kubernetes in detail

- **What the runner watches.**
  - Pods and Jobs in the work namespace with `labelSelector=spectio.io/run-id=<run>` or `nextflow.io/runName=<name>`.
  - Events for those objects.
  - The `ResourceQuota` objects of the namespace.
  - When Kueue is installed: `Workload` objects (conditions `QuotaReserved`, `Admitted`, `Evicted`, `Preempted`) and the visibility API, which gives each pending workload's `positionInLocalQueue` and `positionInClusterQueue`. That API is `/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/<ns>/localqueues/<q>/pendingworkloads`, behind the `VisibilityOnDemand` feature gate, which is beta and on by default since Kueue v0.9 ([Kueue docs](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand)).
  - Volcano and YuniKorn queues can be added as plugins later.
- **Logs.**
  - The head pod's log is streamed by the runner.
  - Failed task pods are kept by Nextflow and their logs fetched on demand.
  - Successful pods are deleted by default (`k8s.cleanup`), so their logs exist only in the task directory or in a cluster log stack.
- **Usage.**
  - Live usage comes from `metrics.k8s.io` (metrics-server), when present.
  - History comes from Prometheus (cAdvisor, kube-state-metrics) through an optional plugin.
  - Nextflow's trace still gives per-task `peak_rss` and `%cpu`.
- **Storage.**
  - The work PVC's capacity and usage come from kubelet volume stats, or from `df` in the head pod.
  - Nextflow on Kubernetes needs a shared (RWX) work directory or Fusion ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.5).
- **Minimal RBAC for the runner** (namespaced Role):
  - `pods`, `pods/log`, `events`: get, list, watch;
  - `jobs`: create, get, list, watch, delete;
  - `resourcequotas`, `limitranges`: get, list;
  - `persistentvolumeclaims`: get.
  
  Optional, each enabling one more piece of information:
  - a ClusterRole for `nodes` (get, list) to show node pools and GPUs;
  - `visibility.kueue.x-k8s.io` `localqueues/pendingworkloads` (get, list, watch) for queue positions.
  
  Without them the UI says "not visible with the runner's permissions" rather than showing zeros.

## 5. Other schedulers

Every scheduler below is reached through a launcher plugin with the same observer layers. The commands are the native, machine-readable ones; JSON output is used where the scheduler has it.

| Scheduler | Submit / cancel | State and reason (L2) | Accounting (L3) | Capacity (L4) | Push option |
|---|---|---|---|---|---|
| **SLURM** (built in) | `sbatch --parsable` / `scancel` | `squeue --me --json` (`reason`, estimated `start_time`), `sprio`, `sshare` | `sacct --json` | `sinfo --json`, reservations, associations | `jobcomp/kafka`, slurmrestd |
| **LSF** | `bsub` / `bkill` | `bjobs -json -o "jobid stat pend_reason …"`, `bjobs -p` | `bacct`, `bhist` | `bqueues`, `bhosts` | — |
| **PBS Pro / OpenPBS** | `qsub` / `qdel` | `qstat -f -F json` (comment, estimated start) | `qstat -x -f -F json` (finished), `tracejob` | `pbsnodes -a -F json` | — |
| **Grid Engine** (SGE, UGE, Altair GE) | `qsub` / `qdel` | `qstat -xml`, `qstat -j` (scheduling info, often disabled by sites) | `qacct -j` | `qhost -xml` | — |
| **HTCondor** | `condor_submit` / `condor_rm` | `condor_q -json`, `-better-analyze` for idle reasons | `condor_history -json` | `condor_status -json` | job event logs |
| **Flux** | `flux submit` / `flux cancel` | `flux jobs --json` | job eventlog | `flux resource list` | eventlog watch |
| **Cloud batch** (AWS Batch, Google Batch, Azure Batch) | through the engine's executor | cloud API, via an optional plugin | cloud API | quotas API | cloud events |

Command names and flags for LSF, PBS, Grid Engine and HTCondor are to be checked against the versions at the first site that asks. Each plugin's conformance tests run on a containerised scheduler where one exists.

## 6. Running the runner on HPC

| Where | How it stays up | When |
|---|---|---|
| **Login node, user service** | `systemd --user` unit (`spectio-runner@.service`), needs lingering (`loginctl enable-linger`) | sites that allow it |
| **Login node, cron watchdog** | `scrontab` or `crontab` restarts the runner if its PID is gone | sites without lingering |
| **Service or VM node** with SSH or slurmrestd | systemd system unit | institute deployments; the runner submits through `ssh login` or REST |
| **Long, small SLURM job** | resubmits itself before its walltime ends | last resort; costs a slot |
| **Kubernetes** | runner Deployment in the cluster | Kubernetes environments |

**Open OnDemand.** At a site with Open OnDemand, a dashboard link or a Passenger app can open Spectio next to the user's files and jobs. Spectio does not depend on it.

## 7. Monitoring beyond the scheduler

- **Engine liveness.** The Tower protocol heartbeat and the logger's events. When they stop while the head job is still `RUNNING`, the run shows as "head silent" and the runner checks the head's log.
- **Storage.** Quotas and inodes (Lustre, GPFS, BeeGFS, NFS), free space on the work directory, and scratch purge policies with the work directories at risk. Quotas are the most common cause of failed nf-core runs that a scheduler does not explain.
- **Software.**
  - Apptainer / Singularity cache size and `NXF_SINGULARITY_CACHEDIR` presence.
  - Conda environment build failures.
  - Container registry rate limits, which show as `ImagePullBackOff`, or as pull errors in the task log on HPC.
- **Network to the server.** The runner's outbound connection: latency, reconnects, events buffered locally when the server is unreachable (synthesis: local buffer).
- **Site monitoring, optional and read-only.** Links from the environment page to the site's Grafana (Prometheus SLURM exporter), XDMoD or OpenCost (Kubernetes cost), when configured. Spectio never needs them.

## 8. Data model and events

- **`scheduler_jobs`.** Columns:
  - identity: `id`, `environment_id`, `runner_id`, `native_id`, `array_parent_id`, `kind` (head / task);
  - links: `run_id`, `task_attempt_id`;
  - queue state: `state`, `reason`, `queue` (partition), `nodes`;
  - timing: `submit_at`, `est_start_at`, `start_at`, `end_at`;
  - resources: `requested` {cpus, mem, gpus, time}, `used` {cpu_time, max_rss, gpu, energy};
  - outcome: `exit_code`, `failure_class`, `raw_ref` (the last raw record, in the file store);
  - project ownership: `project_id`, as on every tenant table.
- **`environment_snapshots`.** `environment_id`, `taken_at`, `capacity` JSON (partitions, limits, quotas, reservations). Kept 30 days for "usual wait at this time" hints.
- **Events.**
  - `spectio.task.waiting_changed` (reason, estimated start): coalesced, only on change.
  - `spectio.task.failed` gains `failure_class`.
  - `spectio.environment.capacity_low`: quota above 90 %, maintenance within 24 h.
- **API.**
  - `GET /runs/{id}/scheduler` (jobs, summary, suggestions);
  - `GET /environments/{id}/capacity`;
  - `POST /environments/{id}/preflight` (body: launch spec; returns the checklist).

## 9. Plugin interface (sketch)

```python
class Launcher:                                        # spectio.launcher (architecture §3.6)
    def submit(self, plan) -> Handle: ...
    def status(self, handle) -> HeadState: ...
    def cancel(self, handle) -> None: ...
    def reconcile(self, handles) -> Iterable[Correction]: ...
    observer: type["SchedulerObserver"] | None = None   # optional monitoring part

class SchedulerObserver:
    layers: set[Literal["waiting", "outcome", "capacity", "reachability"]]
    def snapshot(self, ctx) -> list[JobRecord]: ...          # one batched query for all jobs of the user
    def outcomes(self, native_ids, ctx) -> list[JobOutcome]: ...
    def capacity(self, ctx) -> Capacity: ...                 # partitions or quotas, limits, reservations
    def explain(self, record) -> Explanation: ...            # plain-language reason and hint
    def classify(self, outcome) -> FailureClass: ...
    def stream(self, ctx) -> AsyncIterator[JobRecord] | None: ...   # push transports (Kafka, event logs, watch)
```

The observer's settings follow the common model ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §3.2): intervals, transport, layers on or off, quota commands per mount.

## 10. UI

- **Run detail → Scheduler tab** (board `RunScheduler`):
  - the head job (ID, partition, node, walltime left);
  - tasks by scheduler state, and a "why pending" breakdown;
  - a task table with job ID, partition, state, reason or estimated start, requested vs used, efficiency, node and elapsed time;
  - relaunch suggestions with "Apply to relaunch";
  - the raw record of a job;
  - a data source footer (which queries, how often, last update).
- **Environment → Capacity** (board `EnvCapacity`):
  - partitions (node states, free CPUs and GPUs, maximum walltime, your jobs, estimated wait);
  - your limits and fairshare;
  - storage quotas and the purge risk;
  - reservations;
  - an example of the pre-flight checklist;
  - a link to the Kubernetes equivalent (quota, Kueue queue, node pools, PVC).
- **Task rows everywhere** show "Pending · waiting for higher-priority jobs · ~14:20" instead of a bare "pending".
- **Health → Runners** shows each observer's layers, interval, last success and latency.

## 11. Phasing

| Phase | SLURM | Kubernetes | Others |
|---|---|---|---|
| MVP | head job (L1), `squeue --me --json` (L2), `sacct` for outcomes (L3), failure classes | head Job, watch, pod reasons and OOMKilled | — |
| 1b | capacity (L4), quotas, reservations, pre-flight, relaunch suggestions | ResourceQuota, PVC usage, pre-flight | — |
| 2 | slurmrestd transport, `jobcomp/kafka` via the Kafka bridge | Kueue visibility, metrics-server, Prometheus plugin | LSF, PBS Pro / OpenPBS, HTCondor, Flux plugins |
| 3 | energy and carbon | OpenCost | Grid Engine, cloud batch |

## 12. Open questions for EMBL

1. Is slurmrestd available to users, and with which auth?
2. Are long-running processes allowed on login nodes (`loginctl enable-linger`), or is a service node needed for runners?
3. Does the site rate-limit `squeue` and `sacct`, and is `jobcomp/kafka` an option?
4. What are the scratch file system, quota command and purge policy?
5. Is Kueue (or another batch queue) installed on EMBL's Kubernetes, and can runners read node pools?

## Sources

- **Nextflow:**
  - [executor options](https://docs.seqera.io/nextflow/reference/config/executor) (`queueStatInterval`, `onlyJobState`, `submitRateLimit`);
  - [k8s options](https://docs.seqera.io/nextflow/reference/config/k8s) (`computeResourceType`, `cleanup`, `debug.yaml`);
  - source of `SlurmExecutor.groovy` and `K8sTaskHandler.groovy` (labels), read on 2026-10-25.
- **Snakemake:**
  - [SLURM executor plugin](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html) and its source (`__init__.py`: run UUID job names, prefix, comment);
  - [plugin catalogue](https://snakemake.github.io/snakemake-plugin-catalog/).
- **Slurm:** [OpenAPI plugin release notes](https://slurm.schedmd.com/rest_release_notes.html), [slurmrestd](https://slurm.schedmd.com/slurmrestd.html), [jobcomp/kafka](https://slurm.schedmd.com/jobcomp_kafka.html), [RPC rate-limit discussion](https://support.schedmd.com/show_bug.cgi?id=18067).
- **Kueue:** [pending workloads on demand](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand).
- **HTCondor:** [condor_watch_q](https://www.mankier.com/1/condor_watch_q).
- **Flux:** [job submission and monitoring](https://flux-framework.readthedocs.io/projects/flux-core/en/stable/python/job_submission.html).
