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
   
   Task states reach Spectio from the engine (the `nf-spectio` plugin, the Snakemake logger plugin). The scheduler is asked only for what the engines do not report:
   - why a job waits, and when it will start;
   - what it really used;
   - why it died;
   - what the cluster can take right now.
2. **One batched query per runner, not per run.** A runner asks the scheduler once per interval about all jobs of its user and shares the answer across every run. Spectio's own load on `slurmctld` and `slurmdbd` therefore does not grow with the number of runs. The engines' load does (each Nextflow head runs `squeue` every minute, each Snakemake head `sacct`), so Spectio also budgets the engines per environment and account (§3.2). Each layer has a budget an admin can change.
3. **Three transports, tried in this order:**
   - **CLI** (`squeue` text format for the periodic poll; `sacct` and `sinfo` `--json` with a pinned data_parser, §3.3): works everywhere, runs as the user. *(assumed — pending Thomas, inbox #28)*
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
| **Nextflow · SLURM** | `squeue --noheader -o '%i %t' -t all -u $USER` (optionally `-p <queue>`), or `--only-job-state` without `-u`/`-p` (Nextflow ≥ 26.04, SLURM ≥ 24.05 per Nextflow's docs; `squeue` has the option since 23.11.5, cluster-wide, an admin's opt-in only, §3.8; lighter on the controller) when `executor.onlyJobState` (Nextflow `114f1fe` `docs/reference/config/executor.mdx:76-84`, `SlurmExecutor.groovy:163-166`); every `executor.queueStatInterval` (default 1 min) (`SlurmExecutor.groovy`, Nextflow docs) | pending reason, estimated start, accounting beyond `trace` (`%cpu`, `peak_rss`), failure class from the scheduler, cluster capacity |
| **Nextflow · Kubernetes** | creates one Kubernetes `Job` per task (default since 26.10; `Pod` before) with labels `nextflow.io/app=nextflow`, `runName`, `taskName`, `processName`, `sessionId`, `queue`; successful pods are deleted (`k8s.cleanup`, default true) | scheduling reasons, image-pull errors, evictions, OOMKilled before the trace is written, quotas, Kueue queue position |
| **Snakemake · SLURM plugin** | `--slurm-status-command`, `sacct` or `squeue` (default `sacct` whenever it is installed, else `squeue`; the plugin only warns when `MinJobAge` is below 3× the first-check interval; plugin `__init__.py:77-97`, `validation.py:157-168`); first check after 40 s, then +10 s per round without finished jobs up to 180 s; job name = `<jobname_prefix>_<run UUID>` (`SLURM run ID: …` in the log; §3.4); comment `rule_<name>_wildcards_<…>`; optional efficiency report; job-name prefix needs plugin ≥ 2.2.0, job arrays ≥ 2.6.0 (plugin CHANGELOG l.133-138, l.45-50) | pending reasons, capacity, efficiency during the run (the report comes only at the end) |
| **Snakemake · Kubernetes / Kueue plugins** | executor plugins `kubernetes` and `kueue` in the catalogue | to check: pod labels and how status is read |
| **Head process** | neither engine watches its own head job | Spectio's launcher does (§3.1) |

Nextflow's grid executors also cover LSF, SGE, PBS Pro and others. Snakemake's catalogue lists 28 executor plugins, including `lsf`, `sge`, `htcondor`, `flux`, `kubernetes`, `kueue`, `tes`, `googlebatch`, `aws-batch` and `azure-batch`. Spectio's scheduler plugins sit next to these, not in place of them: the engine still submits the tasks. The runner records the engine and plugin versions it finds and turns off a feature whose version floor is not met, with the reason shown in the UI.

## 2. Five things Spectio asks a scheduler

| Layer | Question | SLURM | Kubernetes | Used in |
|---|---|---|---|---|
| **L1 · Head job** | is the engine's head process alive, and where? | `sbatch --parsable` (head job), the `squeue --me` snapshot (never `squeue -j` with a list, §3.8), `sacct -j`, `scancel --signal=TERM --full`, then `scancel` after a grace period (synthesis §5ter.3) *(assumed — pending Thomas, inbox #28)* | head pod or Job: watch, logs, delete | launch, cancel, relaunch, runner restart |
| **L2 · Waiting** | why is it pending, and until when? | `squeue --me` text poll (state, `reason`, `start_time`, §3.2; `--json` for details: `job_state`, `state_reason`, `start_time`, which is the backfill estimate while pending; Slurm `data_parser` v0.0.45 `parsers.c:10066-10069`) *(assumed — pending Thomas, inbox #28)*, `sprio` (priority factors), `sshare -U` (fairshare) | pod condition `PodScheduled=False` (reason, message), events `FailedScheduling`, Kueue `Workload` conditions and visibility positions | task rows, Run detail → Scheduler |
| **L3 · Outcome** | what did it use, and why did it end? | `sacct --json -j <ids>` (job: `state.current`, `state.reason`, `exit_code`, `time.elapsed`, `time.total`, `tres.requested` / `tres.allocated`; per step: `tres.requested.max` for max RSS, `statistics.energy.consumed` when energy accounting is on; `parsers.c:9050-9063, 9417, 9437-9444`) | container `state.terminated.reason` (`OOMKilled`, `Error`) and exit code; pod `status.reason` `DeadlineExceeded` for Nextflow time limits (set as pod `activeDeadlineSeconds`); the Job's `Failed` condition (`BackoffLimitExceeded`, since Nextflow sets `backoffLimit: 0`) only says that the task failed (Nextflow `114f1fe` `PodSpecBuilder.groovy:415, 493-494, 600`, `K8sTaskHandler.groovy:263`; [PodStatus](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#PodStatus): `lastState` is only set after a restart); eviction and preemption events, `metrics.k8s.io` usage while running | failure classes, relaunch suggestions, efficiency |
| **L4 · Capacity** | can this environment take the launch? | `sinfo --json` (partitions, node states, free CPUs/GPUs, `MaxTime`), `scontrol show reservation`, association and QoS limits (`sacctmgr show assoc where user=$USER`), storage quotas | `ResourceQuota` status (used / hard), `LimitRange`, node pools and allocatable GPUs (needs cluster read), Kueue `ClusterQueue` quota and usage, PVC capacity | Environments, launch pre-flight |
| **L5 · Reachability** | can the runner talk to the scheduler, and how fast? | command latency and errors, `slurmctld` timeouts | API latency, watch reconnects | Health → Runners |

## 3. How the runner observes

### 3.1 Head job

> **Note 2026-10-28 (0.0.1).** In 0.0.1 the head does not run as a head job: it runs on the login node, in its own tmux session, started by the tmux launcher of §3.1.1 (Thomas, [decision log](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open); [`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3). The head job below stays the design for a later version, for sites that forbid long-running processes on login nodes.

On HPC the engine's head process is run as a **head job**: `sbatch` sized from the expected task count (a workflow profile; 2 CPUs and 4 GB for small runs), with `NXF_OPTS -Xmx` at about 75 % of the head's memory, and a long walltime, named `spectio-head-<run_id>-<launch>` (launch = `launches.n`, [`api-and-data-model.md`](api-and-data-model.md) §7) *(assumed — pending Thomas, inbox #12)*, with `--comment=spectio:<run_id>`. The `spectio-head-` prefix (43 characters up to the end of a `run_` ULID) means Snakemake task jobs (named `spectio-<run_id>_<uuid>`, §3.4) never match the head-job prefix. This is the recommended mode because login nodes usually kill long processes. A JVM tracking 100 000 tasks, or a Snakemake DAG of 100 000 jobs, plus the bridge buffers, likely needs more than 4 GB **[to be validated]**; an OOM-killed head ends without `onFlowComplete`.

Job names and comments carry the run ID only, never project, sample or workflow names. Head jobs are submitted with `--export=NONE`, and credentials reach the job as 0600 files in the run directory ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2.1). *(assumed — pending Thomas, inbox #14)*
- **Offline head.** Before `sbatch`, the runner does every network-dependent step on the login node: git clone at a pinned commit; Nextflow plugins into `NXF_PLUGINS_DIR` at pinned versions (`nf-spectio` among them, enabled in the head by `NXF_PLUGINS_DEFAULT`, [architecture §13.8](architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), inbox #69); the `NXF_VER` distribution; container image pre-pull; Snakemake `--conda-create-envs-only`. The head job then runs with `NXF_OFFLINE=true`, and its events leave through the launch-directory spool forwarded by the runner ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.1). Nextflow downloads plugins into `$NXF_HOME/plugins` at start, and "plugin versions MUST be specified in offline mode" (`nf-commons/.../PluginUpdater.groovy:54, 477-478`, Nextflow `114f1fe`). The head also pulls images, builds conda environments and reads the pipeline manifest through the GitHub API, which was rate-limited in the synthetic-pipelines spike. *(assumed — pending Thomas, inbox #28)*
- **Snakemake heads.** The Snakemake SLURM executor warns against running Snakemake inside a SLURM job ("You are running snakemake in a SLURM job context. This is not recommended … please run Snakemake directly on the login node", `snakemake_executor_plugin_slurm/__init__.py:459-467`, `8c2af56`). A Snakemake head in `sbatch` works on `slurm-site` for the synthetic `happy` scenario: the plugin warns but runs, and the head job ends `COMPLETED 0:0` (T3, run [40680736055](https://github.com/weber8thomas/spectio/actions/runs/40680736055); [T3 note](../research/spike-t3-ci-2026-10-28.md#result)). Failure scenarios, a cancelled head and long runs in a head job are **[to be validated]**. *(assumed — pending Thomas, inbox #28)*
- **Alternative:** head on a service node allowed by the site, as a plain process supervised by the runner.
- **Idempotent launch.** Before `sbatch`, the runner looks for the head job's name in its `squeue --me` / `sacct` snapshot (client-side name match, as in Runner restart below) and adopts the job if it exists. A runner that crashed between `sbatch` and its acknowledgement therefore never submits a second head job into the same launch directory. *(assumed — pending Thomas, inbox #12)*
- **Walltime.** The runner performs a controlled stop well before the head job's limit and, if the policy allows, resubmits the head with `-resume`; a warning alone does not stop a run from being killed overnight. At the limit Slurm waits only `KillWait` between SIGTERM and SIGKILL (default 30 s, `slurm.conf`, Slurm 26.05), which may not be enough to cancel thousands of tasks, leaving orphan jobs **[to be validated]**. Resuming is safe because the engine caches the completed work.
- **Runner restart.** When a runner restarts, it reconciles: it lists the user's jobs with `squeue --me --json` and keeps those whose name starts with `spectio-head-` and whose comment is `spectio:<run_id>` (filtered client-side, since `--name` only matches exact names: Slurm 26.05.5 `squeue.1:1423-1425`, `src/squeue/print.c:3263-3275`; `sacct --name` too, slurmdbd `as_mysql_jobacct_process.c:1608`), then reads finished head jobs with `sacct --json -j <ids>` for the IDs stored in `scheduler_jobs`. No run is lost ([`synthesis.md`](synthesis.md) §10, main risks) *(assumed — pending Thomas, inbox #29)*.

#### 3.1.1 Local launcher: detach, adopt, exit

*(decided — Thomas, 2026-10-27, inbox #35)* On the local executor (the in-process runner of `spectio serve`) the engine heads keep running detached when the server stops, and the next start re-adopts them.
- **Detach.** The local launcher starts each head in its own session (`setsid` / `start_new_session=True`) and outside the server's cgroup with `systemd-run --user --scope` where available, because systemd's default `KillMode=control-group` kills every process of the unit ([R4 CH-028](../reviews/R4-constraints.md#ch-028-major-hosting-the-runner-on-login-nodes-scrontab-does-not-run-there-systemd-kills-supervised-heads-duplicate-runners)). stdin is `/dev/null`; stdout and stderr go to `<launch_dir>/.spectio/head.out` and `.spectio/head.err`, never to pipes.
  - *Note 2026-10-30 ([P3 Task 11](../progress/W5/P3-M3.md#task-11-spectio-serve-bind-and-boot)):* `systemd-run --user --scope` is not built in 0.0.1. Heads start with `setsid` only. In 0.0.1, local mode runs `spectio serve` in a terminal, not under a systemd unit, so no `KillMode=control-group` applies to it. A login node often has no user manager for `systemd-run --user` to reach **[to be validated]**. When a release runs the server under a systemd unit, the wrapper comes back *(assumed — pending Thomas, [inbox #85](../reviews/inbox.md#85-assumed-spectio-serve-in-the-local-only-order-and-what-p3-task-11-leaves-to-tasks-10-and-12) rule 7, option (e) of [#84](../reviews/inbox.md#84-assumed-the-private-nf-spectio-copy-and-the-snakemake-concurrency-of-p3-task-9))*.
- **PID and exit files.** A wrapper, `spectio-head-wrap`, writes `.spectio/head.pid` (PID, process group, process start time, host boot ID, host name) before it execs the head, and `.spectio/head.exit` (exit code, time) when the head ends, so the exit code survives the server. The values are stored on the `launches` row ([`api-and-data-model.md`](api-and-data-model.md) §7).
  - *Note 2026-11-08 (FU-P3-77, step P3-fu77):* the head script (`spectio.runner.headscript`) takes `head.exit`'s epoch from bash's own `printf '%(%s)T' -1`, not from `$(date +%s)`. A Cancel's SIGTERM goes to the whole process group; the head traps it, but a child of its tail does not, so a `date` killed there left `130 \n`, a `head.exit` the runner refuses, and a run that never ended (the timeouts of the tmux launcher's `test_argv_never_single_string`; the open DW-P3B06-02 of the [batch record](../reviews/code/P3-B06.md) is another symptom this does not explain). `%(fmt)T` is new in bash 4.2 ([bash NEWS](https://tiswww.case.edu/php/chet/bash/NEWS), bash-4.2 item m); `-1` is the current time ([Bash manual, `printf`](https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html)). The head script therefore needs bash 4.2 or later. The EMBL login node runs Rocky Linux 8.10 ([login-node audit](../research/2026-11-08-embl-login-node-audit.md#scope-and-method)); its bash version was not recorded there, so that it is 4.2 or later is **[to be validated]**. What the group's SIGTERM still does to the tail's other children: a killed `mv` of `head.exit.tmp` leaves no `head.exit`, and the dead head is reported ended with no exit code, as any head gone without one (checked with a `mv` that SIGTERMs its group, both launchers); a killed `rm` of the lock, or a killed `$(< "$lock")` subshell, leaves `.spectio-launch.lock`, and `head.exit` is written as usual; a Resume removes that lock once the head is proven gone (`resume.clear_stale_lock`). Not changed here, FU-P3-78: a dead head whose `head.exit` does not parse is still reported `unknown`, never ended; counting it as ended is a policy change for Thomas, and until then any future malformed `head.exit` hangs its run.
- **Adopt on boot.** For every `launches` row not in a terminal state, Spectio checks PID + start time + boot ID: if they match, it adopts the running process; otherwise it reads `head.exit`. The same check makes a re-delivered `launch` command idempotent, as the `squeue` name match does on SLURM (§3.1).
- **Head exit with no terminal event.** *(assumed — pending Thomas, inbox #40)* This is the local counterpart of the head-job watch: when `head.exit` exists, or the PID is gone, and no terminal engine event was received, the launcher reports the head exit (`launches.exited_at`, `exit_code`), and the run transition of [`api-and-data-model.md`](api-and-data-model.md) §7.1 (`head_lost` / `engine_fault`) applies.
- **Why the head must not be signalled.** Nextflow aborts the run on SIGTERM or SIGINT (`Session.groovy:609-615`, Nextflow `114f1fe`); Snakemake drains running jobs on SIGTERM (`job_scheduler.py:171, 241-245`, Snakemake `1c67a66`) ([`synthesis.md`](synthesis.md) §5ter.3). Whether a server stop (systemd restart, Ctrl-C in the terminal of `spectio serve`) still delivers a signal to a detached head is **[to be validated]**.
- **tmux launcher (0.0.1 on a cluster).** *(decided — Thomas, 2026-10-28, [decision log](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open))* On a SLURM login node, the launcher starts the same wrapper inside a new detached tmux session, `tmux new-session -d -s spectio-<run_id> …`, as the pane's command, so a person can attach to the head, watch the engine's output and stop it by hand ([`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3). The engine's tasks go to SLURM through its own SLURM executor.
  - The wrapper writes `head.pid` and `head.exit` as above and copies the engine's output to `.spectio/head.out` while the pane shows it, so the logs survive the pane.
  - Only the tmux server is detached; the head is not. The head runs in the pane's foreground process group, without `setsid`, so a Ctrl-C typed in the pane, or `tmux send-keys C-c`, reaches the engine. The wrapper still writes the PID and exit files.
  - Adopt on boot: a launch is adopted when its tmux session `spectio-<run_id>` exists and the PID check above matches; otherwise `head.exit` is read. Whether the tmux server, when `spectio serve` starts it, stays in the server's cgroup, so that a stop of `spectio serve` under a systemd unit would kill it, is **[to be validated]**; if so, the launcher starts the tmux server through `systemd-run --user --scope` where available. Whether the EMBL login nodes kill a user's processes at logout (systemd `KillUserProcesses=yes` or a session cleanup) is **[to be validated]**.
  - Cancel: an interrupt to the engine, as a person pressing Ctrl-C in the pane would (`tmux send-keys -t <pane id> C-c`, the pane ID recorded from `new-session -P -F '#{pane_id}'`; every other tmux call targets `=spectio-<run_id>` exactly), then SIGTERM to the head's process group, then SIGKILL after the grace period; the PID check is repeated before each signal, and no signal is sent across a boot ID change ([`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3 req. 11). Snakemake cancels its running cluster jobs on SIGINT (`job_scheduler.py:398-403`, Snakemake `1c67a66`; [`synthesis.md`](synthesis.md) §5ter.3); whether Nextflow's abort cancels the SLURM jobs it submitted is **[to be validated]**.
  - The session name carries the run ID only, as job names do (§3.1). The server runs the same way, in a tmux session named `spectio-server` ([`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3).
  - What the EMBL login nodes provide for this launcher (tmux, no time limit on user processes) is in [`dev-environment-and-testing.md`](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) §15.3, Prerequisites at EMBL.
  - *Note 2026-11-07 ([P3 Task 10](../progress/W5/P3-M2.md#task-10-tmux-launcher-on-the-login-node), [inbox #110](../reviews/inbox.md#110-assumed-the-tmux-launcher-as-built-p3-task-10)):* as built in `spectio.runner.tmux`. The native ID is the session name `spectio-<run_id>`; a rebuilt index holds the local form `<pid>.<start>`, and adopt takes the session from the launch's run ID, so it accepts either. The head's identity is the pane PID printed by `new-session -P -F '#{pane_id} #{pane_pid}'`, which `head.pid` must name; the PID check of the local launcher (host, boot ID, start time, group leader) is repeated before every signal. The tmux client gets only `HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG`, `TMPDIR`, `PATH` and `TMUX_TMPDIR`, never `TMUX` or a `SPECTIO_*` setting, because a tmux server it starts keeps that environment for every later pane of the user. A `new-session` that exits non-zero (tmux missing, session exists) fails the run with `launch_error` and kills nothing, since the session may be another launch's. A `new-session` that does not answer in 10 s, or exits 0 with output that is not a pane, is followed by a best-effort `kill-session -t =spectio-<run_id>`, then `launch_error`, so no engine runs on with no owner; it assumes that a session found under the run's name after a timeout is the one just started *(assumed — standing rule, inbox #110)*. The kill goes to the tmux server that did not answer, so it can fail too; it is then only logged. After a restart, a head whose pane is not found in its session is not signalled, even when `head.pid` passes the PID check (CR-P3T10-05 (r1), FU-P3-45). Which tmux versions pass a command given as separate arguments without a shell, and honour the `=` exact target, is **[to be validated]**: the tests ran on tmux 3.4 only, and the version on the EMBL login nodes is unknown. `spectio serve --detach` is not built (FU-P3-44). *Note 2026-11-08:* built; its rules are in [dev-env §15.3](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 11, note 2026-11-08.

### 3.2 Batched observation and budgets

One `SchedulerObserver` per runner keeps a cache of all jobs of its user. Each layer has its own default interval:

| Query (SLURM) | Default interval | Scope |
|---|---|---|
| `squeue --me -h -o '%i\|%T\|%r\|%S\|%P\|%N\|%j'` (text, about 100 B per job; `--json` only for detail views) | as §3.8 says (L2: `-t PD`, 120 s, only while jobs are pending and a UI client watches; corrected 2026-11-09, CON-SLURM-POLL-06) | every pending job of the user, all runs at once |
| `sacct -j <ids>` | as §3.8 says (built: on opening, and one sweep and one follow-up when a run ends, at most 100 IDs) | finished jobs only |
| `sinfo --json`, partitions | 5 min | partitions used by this environment |
| `scontrol show reservation` | 15 min | maintenance windows |
| `sshare -U`, `sacctmgr show assoc` | 30 min | fairshare and limits of the user |
| Storage quotas (`lfs quota -u`, `mmlsquota`, `beegfs-ctl --getquota`, `df` / `df -i`) | 15 min | work and results directories |

- **Why text for the poll.** `squeue --json` dumps all information ('All information is dumped, even if it would normally not be … most filtering arguments are still used', `squeue` man page, Slurm 26.05): at about 5 KB per job record (estimate), 5 000 active jobs give 25 MB per 60 s poll on a login node. Pending arrays appear as one `123_[5-1000]` record, which the runner expands. The job name (`%j`, last because it may contain the separator) serves the head-job match of §3.1. *(assumed — pending Thomas, inbox #28)*
- **Back-off.** As §3.8 says; the layer shows as stale in the UI ([`ui-spec.md`](ui-spec.md) §11).
- **Site policy.** Some sites rate-limit controller RPCs (`SlurmctldParameters=rl_enable`). The admin lowers or switches off any layer in the environment settings, e.g. `observer.squeue_interval: 120s`, `observer.capacity: off`.
- **One extra call, not one per run.** Spectio's `squeue` adds at most one call every 120 s per user, and only while someone watches (§3.8), on top of the engine's, whatever the number of runs. For L1 and L2 it can replace a Nextflow run's own polling only if `nf-spectio` fed scheduler states back into Nextflow; that is not planned. *(assumed — pending Thomas, inbox #28)*
- **Engine budget per (environment, account).** Spectio enforces: an admission limit on concurrent runs; generated `executor.queueSize`, `submitRateLimit`, `queueStatInterval` and `onlyJobState`, apportioned across the active runs; job arrays where the workflow allows. Why: 50 runs × the default `queueSize` 100 (`AbstractGridExecutor.groovy:68`, Nextflow `114f1fe`) is 5 000 queued jobs for one user, above common `MaxSubmitJobs` association limits **[site-dependent]** and half the default `MaxJobCount` of 10 000; with `rl_enable` (per-user RPC rate limiting: `rl_bucket_size` 30, `rl_refill_rate` 2 per `rl_refill_period` of 1 s; `slurm.conf`, Slurm 26.05), 100 000 non-array `sbatch` calls take about 14 h and share one token bucket with every head's `squeue`. Nextflow treats a polling failure only as a warning (`AbstractGridExecutor.groovy:323-337`); how it treats a rejected `sbatch` (e.g. `QOSMaxSubmitJobPerUserLimit`) is **[to be validated]**.
- **Snakemake's own clock.** Snakemake on SLURM learns of task ends only at its own status checks: plugin 2.8.0 waits 40 s after a submission or a finish, and up to 180 s when nothing finishes ([`__init__.py:244-251, 1611-1617` at v2.8.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/blob/v2.8.0/snakemake_executor_plugin_slurm/__init__.py#L1611-L1617)). So the runner's `sacct` may see a job end before the engine reports it; the state lattice ([`api-and-data-model.md`](api-and-data-model.md) §8.2) keeps that order harmless. In T3, `happy` took 762.6 s with the default and 222 to 338 s with 5 s, and the sind tests pass `--slurm-init-seconds-before-status-checks 5` (`tests/slurm/scenarios.sh:24`; [T3 note](../research/spike-t3-ci-2026-10-28.md#differences-with-the-specs-and-the-harness), item 3). Whether Spectio's generated Snakemake profile lowers it on real sites is **[to be validated: site load]**.

### 3.3 Transports

| Transport | When | Notes |
|---|---|---|
| **CLI** (default) | always on a login node | runs as the user, so it sees exactly what the user is allowed to see; the periodic poll uses a fixed text format (§3.2); JSON for details, with the data_parser chosen by `--json=list` and pinned with `--json=<data_parser>`, because the data_parser plugins also generate the CLI's JSON output and Slurm 26.05 carries v0.0.42–v0.0.45 ([Slurm REST release notes](https://slurm.schedmd.com/rest_release_notes.html)); golden fixtures per parser version (`slurm-versions` profile). slurmrestd incremental queries where available **[to be validated]** *(assumed — pending Thomas, inbox #28)* |
| **slurmrestd** | the site runs it with JWT auth | the OpenAPI plugin versions in use on Slurm 26.05 are `data_parser` v0.0.42 to v0.0.45. Slurm 25.11 ships `data_parser` v0.0.41 to v0.0.44 (Slurm tag `slurm-25-11-8-1`), so the range shared with 26.05 is v0.0.42 to v0.0.44; the runner negotiates within it. The runner reads `GET /openapi/v3` at start and picks the newest version both sides know ([Slurm REST release notes](https://slurm.schedmd.com/rest_release_notes.html)). Lets a runner live off the login node |
| **jobcomp/kafka** (push, site-installed) | the site publishes job records to Kafka | `JobCompType=jobcomp/kafka`; JSON job records at completion and, since Slurm 25.05, optionally at start; topic defaults to the cluster name ([jobcomp/kafka guide](https://slurm.schedmd.com/jobcomp_kafka.html)). Spectio's Kafka bridge consumes it, so terminal states and accounting arrive within seconds and `sacct` calls drop |
| **HTCondor job event logs** | HTCondor | the job event log file can be followed instead of querying the schedd, as `condor_watch_q` does ([man page](https://www.mankier.com/1/condor_watch_q)) |
| **Flux event logs** | Flux | job event logs can be watched through the Python bindings (`flux.job` watchers) ([Flux docs](https://flux-framework.readthedocs.io/projects/flux-core/en/stable/python/job_submission.html)) |
| **Kubernetes watch** | Kubernetes | informers on pods, jobs and events in the work namespace, with label selectors and resource versions; no polling |

### 3.4 Joining engine tasks and scheduler jobs

| Engine | Key | Fallback |
|---|---|---|
| Nextflow on a grid | task `nativeId` (trace `native_id`, reported by `nf-spectio`) = scheduler job ID | job name `nf-<PROCESS>_(<tag>)` + submit time |
| Snakemake SLURM | job name = `<prefix>_<run UUID>`. Spectio sets `--slurm-jobname-prefix spectio-<run_id>` (plugin ≥ 2.2.0) and reads the full name from the `SLURM run ID: …` line the logger receives, then queries `sacct --name <full name>` / `squeue --name <full name>` (exact match). The comment `rule_<rule>_wildcards_<…>` maps a job to the rule (snakemake-executor-plugin-slurm v2.8.0 `__init__.py:473, 483-496`; the UUID is random per invocation, the prefix must match `^[A-Za-z0-9_-]{1,50}$`) | the logger's job submission events |
| Nextflow on Kubernetes | labels `nextflow.io/runName` + `taskName`; Spectio adds `spectio.io/run-id` through the generated `k8s.pod` label option | — |
| Job arrays | the parent job ID plus each array element (`<id>_<n>`) are stored n:m with engine attempts (synthesis §2ter) | — |

### 3.5 Turning records into meaning

**Pending reasons** are mapped to plain language. The raw reason stays visible.

| Reason (SLURM unless marked) | Shown as | Hint |
|---|---|---|
| `Priority` | waiting for higher-priority jobs | estimated start (backfill), your fairshare |
| `Resources` | waiting for free nodes | partition load |
| `QOSMaxJobsPerUserLimit`, `AssocGrpCpuLimit`, `AssocGrpMemLimit`, … (exact strings from `src/common/job_state_reason.c`, e.g. l.254; match them case-sensitively and fall back to the raw reason) | at your group's or QoS limit | which limit, how much is used |
| `ReqNodeNotAvail, Reserved for maintenance` | blocked by a maintenance window | reservation start and end |
| `PartitionTimeLimit` | will never start: walltime above the partition maximum | suggest the right partition or time (pre-flight catches this) |
| `Dependency`, `DependencyNeverSatisfied` | waiting for another job / will never start | link to that job |
| `JobHeldUser`, `JobHeldAdmin` | held | who can release it |
| Kubernetes: event `FailedScheduling` with `Insufficient cpu` or `Insufficient memory` | waiting for free CPU / memory (not a failure) | namespace quota and node capacity |
| Kueue: Workload `QuotaReserved=False`, reason `WaitingForQuota` | waiting for queue quota | position in the queue (§4) |

- With `--json`, match `state_reason`. `ReqNodeNotAvail` needs `state_description` to tell a maintenance window from other cases: it is the only probe reason with a description (`squeue-pending-reasons.json` in `tests/fixtures/slurm/slurm-26.05.5/`, T3).
- A `sacct` reason on a job in a terminal state is history, not a wait: `sacct-probes.json` keeps `AssocMaxJobsLimit` and `ReqNodeNotAvail` on `COMPLETED` jobs (T3; [T3 note](../research/spike-t3-ci-2026-10-28.md#differences-with-the-specs-and-the-harness), item 5).
- `FailedScheduling: Insufficient cpu` is ordinary back-pressure: on the one-node `k8s-mini`, 58 of 65 pods got it first and then ran ([T4 note](../research/spike-t4-ci-2026-10-28.md#the-k8s-profile-runs-on-kind-and-its-bin-open-item-is-solved), Scheduling; run [40663207755](https://github.com/weber8thomas/spectio/actions/runs/40663207755)).

**Failure classes** come from the `sacct` state, exit code and reason, or from the Kubernetes container state and events. The `failure_class` values are owned by [`api-and-data-model.md`](api-and-data-model.md) §7 *(assumed — pending Thomas, inbox #29)*:

| Class | Value | SLURM | Kubernetes | Relaunch suggestion |
|---|---|---|---|---|
| Out of memory | `oom` | `OUT_OF_MEMORY` | container `state.terminated.reason` `OOMKilled` | raise memory for this process, sized from max RSS and the attempts so far |
| Timeout | `timeout` | `TIMEOUT`; for a Nextflow task also `FAILED` with exit 140, because Nextflow adds `--signal B:USR2@30` and its wrapper traps `USR2` (128 + 12) ([`SlurmExecutor.groovy:71-75`](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/groovy/nextflow/executor/SlurmExecutor.groovy#L71-L75), [`command-run.txt:192`](https://github.com/nextflow-io/nextflow/blob/v26.10.4/modules/nextflow/src/main/resources/nextflow/executor/command-run.txt#L192), v26.10.4; `nextflow-timeout_fatal-sacct.json`, T3). Whether this holds for limits well above a minute is **[to be validated]** | pod `status.reason` `DeadlineExceeded` (Nextflow's `activeDeadlineSeconds`), not the Job reason | raise time; use a longer partition if the limit is reached |
| Preempted / evicted | `preempted` | `PREEMPTED` | eviction, preemption event | retry is usually enough; avoid preemptible queues or spot nodes for long tasks |
| Node failure | `node_failure` | `NODE_FAIL`, `BOOT_FAIL` | node lost, pod deleted | retry; exclude the node (Snakemake has `exclude_failed_nodes`) |
| Cancelled by someone else | `cancelled_external` | `CANCELLED` by a user other than the run's user (JSON: `kill_request_user`, a user name, compared with the run's user name; text: `CANCELLED by <uid>`; `sacct-probes.json`, T3) | deleted by another principal | show who; no automatic retry |
| Image or environment | `image` | — | `ImagePullBackOff`, `ErrImagePull`, `CreateContainerConfigError` | registry credentials or rate limit, image name |
| Tool error | `tool_error` | `FAILED` with an exit code (other than 140 on a Nextflow task) | `Error` with an exit code | open the task log; no resource change |
| Engine scheduling fault | `engine_fault` | — | — | the engine itself lost track of work (Snakemake 9.27.1: "BUG: Out of jobs ready to be started" after a retry raced a checkpoint update); a plain rerun completes |
| Container runtime (Apptainer / Singularity) | `image` | — (task log) | — | image pull or conversion failed, `NXF_SINGULARITY_CACHEDIR` missing or over quota, user namespaces unavailable ([`synthesis.md`](synthesis.md) §8): fix the cache directory or pre-pull the image on the login node (§3.1); ask the site about user namespaces. Exact error texts **[to be validated on sind]** *(assumed — pending Thomas, inbox #28)* |
| Head out of memory | `oom` | head job `OUT_OF_MEMORY` | head pod `OOMKilled` | size the head from the task count; raise its memory and `-Xmx` (§3.1) |
| Head walltime | `timeout` | head job `TIMEOUT` | head Job `DeadlineExceeded` | controlled stop and resume before the limit (§3.1); a longer partition |

**Engine cleanup is not an external cancel.** After a fatal failure, Nextflow cancels its own pending jobs, and `sacct` shows them `CANCELLED by <uid>` with the run's own uid (spike runs [40667769713](https://github.com/weber8thomas/spectio/actions/runs/40667769713) and [40670286528](https://github.com/weber8thomas/spectio/actions/runs/40670286528); T3 run [40680736055](https://github.com/weber8thomas/spectio/actions/runs/40680736055)). A cancel by the run's own user after the engine has reported the run's failure is engine cleanup. It is shown as "cancelled by the engine", with no class.

**Classify from the record, not from the exit code alone.** The synthetic scenarios showed that the same cause reaches the engine differently:
- a time limit on the local executor ends with exit 143 on Nextflow 26.10.3, but with no exit code at all on 25.10.9 (`exitStatus` is `Integer.MAX_VALUE`; the error message is "Process exceeded running time limit");
- an OOM kill gives 137 locally, but `OUT_OF_MEMORY` with exit code 0:125 under SLURM (consistent with `SIG_OOM 253` in `src/common/slurm_protocol_defs.h:875`, 253 & 0x7f = 125, Slurm 26.05.5). Verified on sind, Slurm 26.05.5, in T3: in `sacct --json`, `return_code` is unset, `signal.id` is 125 and the status is `SIGNALED` (`sacct-probes.json`, job `probe-oom`);
- Snakemake on SLURM (executor plugin 2.8.0): a task job runs `snakemake --executor slurm-jobstep`, so a failing rule ends `FAILED 1:0` whatever the tool returned. The tool's code is only in the task's Slurm log, so `attempts.exit` stays null ([`api-and-data-model.md`](api-and-data-model.md) §7) unless that log is read (T3: the four Snakemake `-sacct.json` fixtures and run [40680736055](https://github.com/weber8thomas/spectio/actions/runs/40680736055); [T3 note](../research/spike-t3-ci-2026-10-28.md#differences-with-the-specs-and-the-harness), item 1).

The engine plugin therefore combines the trace status, the error text, the scheduler record and the exit code (`docs/research/spike-synthetic-pipelines-2026-10-26.md`). The T3 fixtures cited in §3.5 are in `tests/fixtures/slurm/slurm-26.05.5/` ([T3 Progress](../progress/W3/T3.md#findings-and-open-questions)).

**Local executor.** With no scheduler record, a local task failure is classed as follows *(assumed — pending Thomas, inbox #40)*:
- a non-zero exit is `tool_error`;
- SIGKILL or exit 137 is shown as "killed (memory?)", only where the engine reports it **[to be validated]**;
- otherwise the class is unknown, and the UI shows "n/a · no scheduler accounting on a local run".

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
- file-lock support in the launch directory: on file systems without locks Nextflow fails with 'Can't open cache DB … common for network file systems (NFS, Lustre, GPFS, …)' (`cache/DefaultCacheStore.groovy:80-94`, Nextflow `114f1fe`), so such a site cannot resume; fallback `NXF_CACHE_DIR` on a locking file system **[to be validated]** *(assumed — pending Thomas, inbox #28)*;
- container cache presence.

Each check gives ✓ / ⚠ / ✗, and ✗ blocks the launch unless overridden.

**Purge during a gate.** The purge check does not stop at launch. When a gate opens, the runner records the stage's cached outputs and the purge deadline of their work directories, and the gate shows 'work directory purged in N days'. At Continue, the runner checks a sample of those outputs before resuming, because a partial purge makes `-resume` silently recompute upstream stages or removes a gated stage's outputs. Snakemake counts the jobs to run with `--dry-run`; Nextflow has no command that predicts cache hits **[to be validated]**, so its reused-vs-to-run figure comes from inspecting work directories and the UI labels it an estimate. Spectio never touches files to dodge the purge, which breaks many sites' policies **[site-dependent]**.

### 3.6 Efficiency per job and per process or rule

Added 2026-11-07 (Thomas, 2026-11-07, "je veux voir efficiency + params slurm par job et par rule", [decision log](../decisions/log.md#2026-11-07-checkpoints-conditional-and-skipped-jobs-temp-outputs-and-slurm-efficiency-per-job-and-per-rule-thomas); sources: [research note](../research/dag-temp-slurm-efficiency-2026-11-07.md) §6 and §7). This section owns the formulas and when each value is available; the fields are in [`api-and-data-model.md`](api-and-data-model.md) §5 (note 2026-11-07), the words in [ui-spec §4.4](ui-spec.md#44-run-detail) (note 2026-11-07), the `sacct` call in [dev-env §15.3](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 15. It makes the "Efficiency" bullets of §3.5 precise.

**Per job, by source.** A job is a task's last attempt with one SLURM job ID. Spectio shows the best source it has, in this order: `sacct`, then the engine's own measure.

| Source | CPU efficiency | Memory efficiency | Available |
|---|---|---|---|
| `sacct` (both engines) | sum over the job's steps of `TotalCPU` / (`Elapsed` × `NCPUS`) of the allocation row, as `seff` computes it ([`seff`](https://github.com/SchedMD/slurm/blob/master/contribs/seff/seff) lines 119-126, 171-179) | largest `MaxRSS` over the steps / `ReqMem` (per node × `NNodes`, or per CPU × `NCPUS`) | after the job has ended and accounting has recorded it ([`sacct(1)`](https://slurm.schedmd.com/sacct.html); `seff` lines 199-203) |
| Nextflow trace | `%cpu` / (100 × `cpus`); `%cpu` is "relative to a single CPU" ([`trace` config](https://docs.seqera.io/nextflow/reference/config/trace)) | `peak_rss` / `memory` | at `onTaskComplete` |
| Snakemake benchmark | `cpu_time` / (`s` × `threads`) | `max_rss` (MiB) / `mem_mb` | when the job has ended and its benchmark file is read (`benchmark.py:28-40`, Snakemake 9.27.1) |

- `TotalCPU` "may not include CPU time of child processes" for steps stopped by a signal, a time-out or `scancel` ([`sacct(1)`](https://slurm.schedmd.com/sacct.html)): a timed-out job's CPU efficiency is marked "may be low (stopped job)".
- `ReqMem` is "only from the job allocation, not the step" (same page); a Snakemake job with `mem_mb_per_cpu` has its request per CPU.
- The `batch` and `extern` rows count in the sum, as `seff` does; the SLURM plugin's own report drops them (`efficiency_report.py`, 2.8.0). On a job that runs its tool in the batch step (Nextflow, Snakemake's job step) the values match **[to be validated]** on `slurm-mini`.
- A value above 100 % is shown as measured, never clamped (a tool using more threads than asked).

**Timing.**
1. **Submitted or pending:** the request only (from the engine's event); the efficiency state is `running` with no value.
2. **Running:** the request, elapsed time against the time limit (from the engine's start time). Live values from `sstat` on running steps are later **[to be validated]**.
3. **Ended:** the engine's measure at once when it has one (Nextflow trace, Snakemake benchmark), state `pending_accounting`, until `sacct` answers through the limiter of §15.3 req. 15, at the pace and with the follow-up of §3.8 (on a live run, only for a job whose facts are opened); then `available`. A job that `sacct` does not know after its follow-up, or gave up on, reads `unavailable`.
4. **Local run:** the engine's measure only; `sacct` is never called.

**Per process or rule (the aggregate).** Over the last attempts of a process's or rule's tasks: `jobs` (done / total, total a lower bound while a checkpoint is open), `measured` (jobs with a CPU or memory value), the mean and the maximum of the CPU efficiency and of the memory efficiency over measured jobs, the requested CPUs, memory and time (the most common value, with `varies` when jobs differ, which happens with Snakemake resources computed from inputs or Nextflow retries that raise memory; one flag for the three values, so the UI cannot say which one varied: per-value flags `varies: {cpus, mem_bytes, time_limit_s}` are FU-P3-55, CR-P3T35-05), and the largest peak memory and elapsed time used. Each job counts with the source it has; the aggregate does not mix in a job's older source once `sacct` has answered. A job of a cached or up-to-date task has no value and is not counted in `measured`.

**Waste.** "<n> jobs of <rule> used under 25 % of their memory" (§3.5) is read from the aggregate: the measured jobs whose memory efficiency is below 0.25, shown when there are at least 3 such jobs *(assumed — threshold from §3.5's example)*. *Added 2026-11-09 (FU-P3-105, assumed — inbox #139):* the CPU line reads the same way from CPU efficiency: "<n> jobs of <rule> used under 25 % of their CPUs".

*Note 2026-11-07 (as built, [P3 Task 34](../progress/W5/P3-M9.md#task-34-server-process-and-rule-states-outputs-slurm-request-and-efficiency); assumed — pending Thomas, [inbox #116](../reviews/inbox.md#116-assumed-process-states-outputs-slurm-request-and-efficiency-as-built-p3-task-34)):* the formulas above are built in `spectio_server/efficiency.py`, ratios rounded to 4 places. A local run is one whose environment kind is not `slurm`. The aggregate's mean and maximum count every measured job with the best source it has. The waste line is not built (P1 Task 35 shows the aggregate). The `sacct` values are checked on `slurm-mini` only when P1 Task 22 is built.

*Note 2026-11-08, which `sacct` row is the job's (Thomas, [inbox #116](../reviews/inbox.md#116-assumed-process-states-outputs-slurm-request-and-efficiency-as-built-p3-task-34) rule 10 (b); the call is in [dev-env §15.3](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 15, note 2026-11-08):* a job's `sacct` row is the one whose WorkDir is the directory it was launched from and whose `Submit` is not before the run's launch. A resized job's row is its final record, with CPU and memory efficiency null: the steps it ran before the resize sit under the RESIZING record and are not summed. **The Snakemake binding is weaker.** All the jobs of a Snakemake run have the run's launch directory as WorkDir, so the WorkDir ties a line to the run, not to the job; only the job ID and the `Submit` check tell two of the run's jobs apart. A Nextflow job has a work directory of its own.

### 3.7 Performance measures per attempt

Added 2026-11-09 (Thomas, 2026-11-09: a performance part like Nextflow's execution report, plots across the jobs of one step, for one run and across runs, with filters on time, date and partition; in 0.0.2, [decision log](../decisions/log.md#2026-11-09-performance-per-run-and-across-runs-fu-p3-105); design assumed, [inbox #139](../reviews/inbox.md#139-assumed-performance-per-run-and-across-runs-fu-p3-105)). This section owns **what is measured per attempt for performance, from which source, and what that may cost the scheduler**. The CPU and memory efficiency formulas, the source order and the timing stay in §3.6; the stored row and the routes are [api §5.5](api-and-data-model.md#55-performance-002); the screens are [ui-spec §4.12](ui-spec.md#412-performance-002). Nothing here is built.

**Rule: no new load on SLURM** (Thomas, 2026-11-09: the site admins dislike frequent or saturating SLURM polling, and Nextflow and Snakemake already poll; revised the same day after the SLURM polling audit and the R1 reviews, [record](../reviews/code/P3-fu105-spec.md#r1-independent)). Performance values come from (1) what the engines already send (the Nextflow trace through `nf-spectio`, Snakemake's logger events and `benchmark:` files), and (2) for SLURM jobs, **one `sacct` sweep per run, at its end**, through the server's one `SacctLimiter` (`spectio/runner/sacct.py:368-439`: one call in flight, one call per 60 s, at most 100 job IDs a call): the run's job IDs in batches of 100, `--user`, and a bounded window, `-S` the run's launch − 5 min and `-E` its end + 5 min (without `-S`, `sacct -j` searches from the Epoch, [`sacct(1)`](https://slurm.schedmd.com/sacct.html) DEFAULT TIME WINDOW). The job IDs that `slurmdbd` did not answer are asked once more, the same way, 10 min later; then their SLURM values stay null. Performance adds no call while the run is active, no periodic poll, no `squeue`, no `sstat`, and no call for a run that ended before 0.0.2. With `[slurm] accounting = false` the sweep is not made and the SLURM values are absent. The across-runs page and its routes read only Spectio's own database, never SLURM. A general SLURM query budget for every Spectio call is a separate step **[to be validated]**.

**What is kept per attempt** (the last attempt and every earlier one; units as stored):

| Value | Unit | Nextflow (trace at `onTaskComplete`) | Snakemake, local | Snakemake on SLURM |
|---|---|---|---|---|
| requested CPUs, memory, time | count, bytes, s | `cpus`, `memory`, `time` | `threads`, `mem_mb`, `runtime` of `job_info` | the same, then `NCPUS`, `ReqMem`, `Timelimit` of the sweep |
| CPU used | % of one CPU | `%cpu`, "relative to a single CPU" | `cpu_time` / `s` × 100 of the benchmark | `TotalCPU` / `Elapsed` × 100 |
| CPU and memory efficiency | ratio | §3.6 | §3.6 | §3.6 |
| peak resident memory | bytes | `peak_rss` (`VmHWM`) | `max_rss` (MiB) of the benchmark | `MaxRSS` (largest step) |
| peak virtual memory | bytes | `peak_vmem` (`VmPeak`) | `max_vms` (MiB) of the benchmark | none |
| run time | s | `realtime`, "wall-clock time of the task script" | `s` of the benchmark | `Elapsed` |
| time efficiency | ratio | `realtime` / `time` | `s` / `runtime` | `Elapsed` / `Timelimit` |
| wait in queue | s | `start` − `submit` | none | `Start` − `Submit` of the sweep |
| bytes read and written (all reads and writes) | bytes | `rchar`, `wchar` | none | none |
| bytes read from and written to disk | bytes | `read_bytes`, `write_bytes` | `io_in`, `io_out` (MB) of the benchmark | none |
| partition | text | `queue`, "the queue that the executor attempted to run the process on" | none | `Partition` of `sacct` |
| source | `trace`, `benchmark`, `sacct` | | | |

Sources: the trace fields and their meanings, [Nextflow trace reference](https://docs.seqera.io/nextflow/reference/config/trace); the benchmark columns, [`benchmark.py:28-40`](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/benchmark.py#L28-L40) (Snakemake 9.27.1, as §3.6); `sacct` fields, [`sacct(1)`](https://slurm.schedmd.com/sacct.html). The units of the benchmark's `io_in` and `io_out` (MB) and of `max_vms` (MiB) are **[to be validated]**.

- **Nextflow: no plugin change.** `nf-spectio` already sends every trace key above at `onTaskComplete` (`TRACE_KEYS`, `engine-bridges/nf-spectio/src/spectio/SpectioPlugin.groovy:430-435`, read 2026-11-09), with metrics on (`enableMetrics()`, same file `:541-543`); `hostname` is left out on purpose and is set only on Kubernetes anyway ([trace reference](https://docs.seqera.io/nextflow/reference/config/trace)). The server keeps six of them today (`trace_resources`, `spectio_server/failure.py:137-151`); FU-P3-105a keeps the rest. Nextflow's own report draws the same values: `%cpu`, `peak_rss`, `peak_vmem`, `realtime`, `rchar`, `wchar`, and `%cpu` / `cpus`, `peak_rss` / `memory`, `realtime` / `time` as "% of the request" ([`ReportSummary.groovy`](https://github.com/nextflow-io/nextflow/blob/master/modules/nextflow/src/main/groovy/nextflow/trace/ReportSummary.groovy) lines 36-65), as plotly box plots per process, mean shown, no points ([`ReportTemplate.js`](https://github.com/nextflow-io/nextflow/blob/master/modules/nextflow/src/main/resources/nextflow/trace/assets/ReportTemplate.js) lines 90-127; [reports page](https://docs.seqera.io/nextflow/reports): "CPU, memory, job duration, and disk I/O", each "in raw form and as a percentage of the requested resources"). Line numbers read on `master`, 2026-11-09; a tagged release is **[to be validated]**.
- **SLURM jobs: the end-of-run sweep.** Its `--format` is the req. 15 one ([dev-env §15.3](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)) plus `Start` (for the wait); `Partition`, `Submit`, `NCPUS`, `ReqMem`, `TotalCPU`, `MaxRSS`, `Elapsed`, `Timelimit` are already in `sacct.FORMAT`. A row binds to a job by §3.6's WorkDir and `Submit` rule. It covers the SLURM jobs of both engines; for Nextflow it adds the wait and the accounting values that §3.6's source order prefers. Disk I/O from `sacct` (`MaxDiskRead`, `MaxDiskWrite`) is not asked in 0.0.2: those need the site's I/O accounting plugin **[to be validated]**.
- **Snakemake `benchmark:` files** are read when the rule declares one (the path is already on `attempts.resources`, [api §7](api-and-data-model.md#7-database-schema) note 2026-11-01), once at the job's end, as a file-pool task with the pool's timeout, reusing `_benchmark` (`open_confined`, `MAX_BENCHMARK_BYTES`, `spectio_server/failure.py:57, 959-969`), never on the event writer: the writer updates the row when the task returns, so a blocked file delays no other event. They cost SLURM nothing. A rule without one has no peak virtual memory or disk I/O.
- **The Snakemake SLURM plugin's efficiency report is not used.** `--slurm-efficiency-report` makes one more `sacct --name=<run_uuid>` per run, with no `-j` and no `-S` (so it starts at 00:00 today and misses the jobs before midnight), drops the `batch` and `extern` rows, keeps no WorkDir or `Submit` to bind a row, and runs only on a clean shutdown ([`efficiency_report.py:46-47`](https://github.com/snakemake/snakemake-executor-plugin-slurm/blob/v2.8.0/snakemake_executor_plugin_slurm/efficiency_report.py#L46-L47), v2.8.0). Launch never passes it and refuses it in `extra_args` ([api §5.4](api-and-data-model.md#54-environments-001) note 2026-11-09).
- **Ingest checks.** Every new key (`peak_vmem`, `rchar`, `wchar`, `read_bytes`, `write_bytes`, `submit`, `start`; the benchmark's `max_vms`, `io_in`, `io_out`) goes through `_number` and `_whole` (`failure.py:116-130`): a NaN, a negative, an infinite or a non-numeric value is null. `wait_s` is null when `start` is before `submit` or outside the run's window; a ratio above 1,000,000 is null. `partition` is kept only when it matches `[A-Za-z0-9_.-]{1,64}`, else null.
- **A run started from a terminal** has the engine's own measures (the Nextflow trace when `nf-spectio` is loaded, the Snakemake benchmark files the logger plugin names) and no sweep: Spectio did not launch it and holds no launch window *(assumed — inbox #139)*.
- **Local runs** have the engine's measure only, as §3.6 says.
- **When values change.** A row is written at the attempt's end with the engine's measure (the screens say "accounting at run end" for a SLURM job meanwhile), then updated once by the sweep, the source following §3.6's order. Values already stored are never re-read from SLURM.

### 3.8 SLURM query budget

Added 2026-11-09 (Thomas, 2026-11-09: do not saturate or over-poll SLURM, the engines already poll often; constraints audit of the same day, findings CON-SLURM-POLL-01 to -12, [inbox #142](../reviews/inbox.md#142-assumed-the-slurm-query-budget-fu-p3-106a)). Numbered 3.8 because FU-P3-105 adds §3.7, whose end-of-run sweep runs at this section's pace. **This section owns every call Spectio makes to SLURM** (CON-SLURM-POLL-04): its pace, its bounds and who triggers it. §2, §3.2, §3.6 and [dev-env §15.3](dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 15 link here and do not repeat its numbers. Status per line: **built** (FU-P3-106a: the `sacct` part, in `spectio/runner/sacct.py` and `spectio_server/failure.py`) or **planned** (the observer of §3.2, not built; the rest in FU-P3-106b).

**Why a budget.** SchedMD's man pages ask that client commands not be run in loops, as each call costs the daemon ([`squeue(1)`](https://slurm.schedmd.com/squeue.html) and [`sacct(1)`](https://slurm.schedmd.com/sacct.html), PERFORMANCE). Site advice is a minute or more between polls ([NERSC, monitoring jobs](https://docs.nersc.gov/jobs/monitoring/); slurm-users, February 2023, threads 009724 and 009728, which advise 5 min **[to be validated]**: the archive links are not recorded). EMBL runs `rl_enable` ([EMBL login-node audit](../research/2026-11-08-embl-login-node-audit.md), line 67): per-user token bucket of 30, refilled at 2 per second (`slurm.conf`, Slurm 26.05; EMBL's own `rl_*` values are asked in inbox #142), shared by every `sbatch` and `squeue` of the user, the engines' included. Spectio makes no `slurmctld` call today; its only SLURM call is `sacct`, to `slurmdbd`.

**Policy** (proposed by the audit; built where marked):

| Rule | Status |
|---|---|
| One limiter per daemon and server: at most one call in flight to `slurmdbd`, and one to `slurmctld` | built for `slurmdbd` (`SacctLimiter`); `slurmctld` planned |
| At most one call per minute per daemon per server; a burst of at most 3 calls per 5 min | the minute built for `sacct` (`INTERVAL_S` 60 s); the burst rule planned |
| A failed or timed-out call puts its IDs back in the queue, as one batch, unchanged, and doubles the interval from 60 s up to 600 s (`MAX_INTERVAL_S`); a quick answer resets it. A call slower than 5 s (`SLOW_S`) is back-pressure: it doubles the interval too. Timeout 30 s (`TIMEOUT_S`), then the process group is killed (CON-SLURM-POLL-02). Only an answer over `MAX_OUTPUT` (1 MiB) points at its IDs: that batch is split in two, and one ID alone over it is given up; a refused tool path is given up at once (SEC-P3FU106A-01). So a window over the site's `MaxQueryTimeRange` fails its batch until `GIVE_UP_S` **[to be validated]** (FU-P3-106b) | built for `sacct` |
| `sacct` always `--user=<euid>`, `-j` with at most 100 IDs (or `--name` for one Snakemake run), and `-S <earliest launch of the call's jobs − SUBMIT_SKEW_S (300 s)> -E now`: never without `-S`, which searches from Epoch 0 when `-j` is given ([`sacct(1)`](https://slurm.schedmd.com/sacct.html), DEFAULT TIME WINDOW) (CON-SLURM-POLL-03). `-S` is written `YYYY-MM-DDTHH:MM:SS` in UTC, as `TZ=UTC` in the call's environment reads it **[to be validated]** on `slurm-mini`, with `MaxQueryTimeRange` (`slurmdbd.conf`, inbox #142) | built (`-j`, `-S`, `-E`); `--name` planned (FU-P3-105) |
| `--parsable2` with a fixed format for bulk calls; `--json` only for one job's detail; `-X` when only the state is needed | built (`--parsable2`); the rest planned |
| `squeue` always `--me`, never `-j` with a list: `squeue -j a,b` asks `slurmctld` for the whole job table (`REQUEST_JOB_INFO`) and filters on the client (Slurm source, `src/squeue/opts.c:541-545`, `src/squeue/squeue.c:354-356`, as read by the audit; revision not recorded, **[to be validated]**) (CON-SLURM-POLL-05) | planned |
| `--only-job-state` (lighter on `slurmctld`) exists in `squeue` since Slurm 23.11.5 (Slurm NEWS, as read by the audit **[to be validated]**), cannot be combined with `-u` and applies cluster-wide, so it is an admin's opt-in, never a default (CON-SLURM-POLL-08) | planned |
| `slurmrestd` gets the same budget; it is not cheaper; never a bare `GET /jobs/` (CON-SLURM-POLL-10) | planned |

**Who triggers each call.**

| Call | When | Status |
|---|---|---|
| `sacct` for a Nextflow failure | when the failure summary is first opened, live or ended | built |
| `sacct` for one job | when its SLURM facts are opened (the task sheet asks `GET /runs/{id}/tasks?task=<id>`), live or ended | built |
| `sacct`, end-of-run sweep (L3) | every ended job of a run is queued once, on the first Tasks or By process view after the run reached a terminal state; while the run is live these views queue nothing, and efficiency shows the engine's own measure (Nextflow trace, Snakemake benchmark) with its source, in the words of [ui-spec §4.4](ui-spec.md#44-run-detail) (`pending_accounting`) (CON-SLURM-POLL-01) | built |
| `sacct` follow-up | a job answered with no row in a terminal state (slurmdbd lags) is asked once more `FOLLOW_UP_S` (600 s) later, with no view; then `null` is stored only when that answer had no line for the job, and a job still in another state is given up in memory, never stored | built |
| Giving up | a job whose calls fail is asked again, as the interval backs off, until `GIVE_UP_S` (24 h) after it ended (the run's end, or the time it was queued), not after a number of views; it then reads `not_found` and nothing is stored | built |
| `squeue --me -t PD`, pending reasons (L2) | every 120 s, only while the user has pending jobs **and** a UI client is subscribed to one of their runs; a slow call is back-pressure (CON-SLURM-POLL-06) | planned |
| `sinfo` (L4) | on demand, cached 5 min | planned |
| `scontrol show reservation` | at launch, cached 15 min | planned |
| `sshare` | on demand, cached 30 min | planned |

**Never called.** Task states (the engines report them); `sstat`; one call per job; `squeue -i`; background `sinfo -N` or `sprio`; `sacct` without a job filter or from Epoch 0; anything during an index rebuild or a spool replay; anything for a local run; anything when no page is open, except a run's pending follow-ups and the retries of a failed call. No periodic call is added: the follow-up is one more call per job, and the planned L2 poll runs only while someone watches.

**The engines' own load** (not Spectio's, but it shares the user's `rl_enable` bucket; CON-SLURM-POLL-07):

| Engine | Calls | Source |
|---|---|---|
| Nextflow 26.10.4 · SLURM | one `squeue -u` per head per queue every `executor.queueStatInterval` (1 min); task states read from files, every `pollInterval` (5 s), not from SLURM; `executor.queueGlobalStatus` makes it one call for all queues | §1; [executor options](https://docs.seqera.io/nextflow/reference/config/executor) |
| Snakemake SLURM plugin 2.8.0 | one `sacct -X --name <run UUID>` per status check, 40 s after a submission, then +10 s up to 180 s, up to 5 attempts when it fails; `scontrol show config` at every check; up to 10 more `sacct` per failed job, outside its own limiter; the efficiency report is one `sacct --name` at shutdown, with no `-S`, dropping `batch` and `extern` | §1; [plugin v2.8.0](https://github.com/snakemake/snakemake-executor-plugin-slurm/blob/v2.8.0/snakemake_executor_plugin_slurm/__init__.py) (the call sites as read by the audit, **[to be validated]** line by line) |

What Spectio generates to keep the engines in budget (`queueGlobalStatus`, a shared `submitRateLimit`, `--slurm-status-command sacct`, never `init-seconds` below 40), counting its own calls per command and daemon in the log and on the Health page, and one budget per user and site shared by the servers of a user are FU-P3-106b (CON-SLURM-POLL-09, -11, -12), with the spikes S1 to S5 (footprint in sind with `sdiag` and `sacctmgr show stats`, `MaxQueryTimeRange`, `rl_enable` with a burst of 300 `sbatch`, RPC types, `sacct` bytes and latency).

## 4. Kubernetes in detail

- **What the runner watches.**
  - Pods and Jobs in the work namespace with `labelSelector=spectio.io/run-id=<run>` or `nextflow.io/runName=<name>`.
  - Events, watched namespace-wide and filtered by `involvedObject` (Events cannot be selected by the object's labels **[to be validated]**). Events live one hour by default (kube-apiserver `--event-ttl`, 'Default: 1h0m0s', [reference](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver/)), and `k8s.cleanup` deletes successful pods. An OOM kill is only in the container's `state.terminated` (no event), and a Job deadline deletes the Job's pod, leaving only the Job condition `DeadlineExceeded` (`tests/fixtures/k8s/failures-{pods,jobs,events}.json`; [T4 note](../research/spike-t4-ci-2026-10-28.md#plain-failure-objects-k8s-mini-row-of-42)). So the runner keeps the last terminal state of each pod and Job itself; events expire after an hour (`FailedScheduling`).
  - The `ResourceQuota` objects of the namespace.
  - When Kueue is installed: `Workload` objects (conditions `QuotaReserved`, `Admitted`, `Evicted`, `Preempted`) and the visibility API, which gives each pending workload's `positionInLocalQueue` and `positionInClusterQueue`. The runner discovers the served API versions through `/apis` before use and never hard-codes one: Kueue v0.20.0 no longer serves `kueue.x-k8s.io/v1beta1` ([release mirror](https://newreleases.io/project/github/kubernetes-sigs/kueue/release/v0.20.0)), and the visibility API is `v1beta2` on Kueue ≥ v0.15, `v1beta1` on v0.9 to v0.14 (Kueue `apis/visibility/` at tags v0.13.0 to v0.20.0 and `main` `c331366`). The path is `/apis/visibility.kueue.x-k8s.io/<version>/namespaces/<ns>/localqueues/<q>/pendingworkloads`, behind the `VisibilityOnDemand` feature gate, beta and on by default since Kueue v0.9; pending workloads are returned with a default `limit` of 1 000 ([Kueue docs](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand)). A task is queued when the visibility API lists its Workload; Workload conditions give the reason (`WaitingForQuota`) when present. Without visibility permission, the runner falls back to `QuotaReserved=False`. Why: the visibility API lists a pending Workload before it has its `QuotaReserved=False` condition (`tests/fixtures/k8s/kueue-pending-workloads.json` and `kueue-workloads.json`, Kueue v0.20.3; [T4 note](../research/spike-t4-ci-2026-10-28.md#kueue-workloads-waiting-for-quota-with-positions)).
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
  - Nextflow on Kubernetes needs a shared (RWX) work directory or Fusion; Snakemake on Kubernetes needs object storage (S3) instead ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.5).
- **RBAC: two ServiceAccounts.** This section owns them; architecture §7.5 links here.
  - **Runner** (namespaced Role; creates the engine's head Job and watches):
    - `pods`, `pods/log`, `events`: get, list, watch;
    - `jobs`: create, get, list, watch, delete;
    - `resourcequotas`, `limitranges`: get, list;
    - `persistentvolumeclaims`: get.
  - **Engine head** (the head pod's ServiceAccount, namespaced Role), by Nextflow version:
    - 26.10 creates one `Job` per task (§1): `jobs`: create, delete, get, list, watch; `pods`: get, list, watch; `pods/log`: get;
    - 25.10 creates `Pod`s: `pods`: create, delete, get, list, watch; `pods/log`: get.
  
  Optional for the runner, each enabling one more piece of information:
  - a ClusterRole for `nodes` (get, list) to show node pools and GPUs;
  - `visibility.kueue.x-k8s.io` `localqueues/pendingworkloads` (get, list, watch) for queue positions.
  
  Without them the UI says "not visible with the runner's permissions" rather than showing zeros. Nextflow's required permissions are **[to be validated]** ([Nextflow on Kubernetes](https://docs.seqera.io/nextflow/kubernetes)). 25.10 needing `pods: create` is verified on `k8s-mini` (T4, run [40672184666](https://github.com/weber8thomas/spectio/actions/runs/40672184666)). T4 measured head and runner Roles that differ from the lists above; they wait for Thomas ([inbox #53](../reviews/inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads)).
- **Kueue and Nextflow.** Nextflow builds Kubernetes Jobs from the pod metadata (`buildAsJob`, `nf-k8s/.../PodSpecBuilder.groovy:597-616`) and uses Jobs by default (`K8sConfig.groovy:224`, Nextflow `114f1fe`). Spectio writes the Kueue queue-name label through the `k8s.pod` labels it generates. On Nextflow 25.10, which creates Pods, Kueue sees tasks only through its pod integration. That integration is listed in Kueue's default configuration (`manifests.yaml` L27163 at [v0.20.3](https://github.com/kubernetes-sigs/kueue/releases/tag/v0.20.3), the file pinned by `KUEUE_MANIFEST_SHA256` in `dev/versions.env`); the T4 note says otherwise and is corrected by [SPK-T4-17](../reviews/spikes.md#spk-t4-17-minor-kueues-default-configuration-does-include-the-pod-integration-the-t4-note-is-wrong). Whether a 25.10 task Pod is admitted with only the queue-name label is **[to be validated]**.
- **Nextflow 25.10 needs `nf-k8s`.** Without it, 25.10.9 stops with "Unknown executor name: k8s" (spike run [40662141233](https://github.com/weber8thomas/spectio/actions/runs/40662141233)). So on 25.10 the head script adds `nf-k8s@<version>` to `NXF_PLUGINS_DEFAULT`, at the version that the Nextflow release lists as core: 1.2.3 for 25.10.9 (`NF_K8S_25_10_VERSION` in `dev/versions.env:85`), never a `plugins` block, which would replace the pipeline's own ([architecture §13.8](architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), inbox #69, revised 2026-10-29). The dev cluster's synthetic pipeline, which declares no plugin, still passes it with `-plugins` (`tests/k8s/scenarios.sh:116`). 26.10 needs nothing: its log lists `K8sExecutor` among its executors ([T4 note](../research/spike-t4-ci-2026-10-28.md#the-k8s-profile-runs-on-kind-and-its-bin-open-item-is-solved)); 26.10 bundles it in the CLI (`modules/nf-cli-v1/build.gradle:18` at `691b821`, [attach verification](../reviews/verification-2026-10-29-nextflow-attach.md), claim 7). Offline sites pre-install it in the plugins directory, as §3.1 (Offline head) does for every Nextflow plugin.

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

- **Engine liveness.** When no event arrives from the engine plugin for 5 min (idle heartbeats included; the heartbeat is part of the ingest contract, api §14, proposed every 60 s as `nf-tower` sends its heartbeat every minute, synthesis §2bis; pending inbox #11) while the last `squeue` snapshot shows the head job `RUNNING`, the run carries the flag "head silent" ([`ui-spec.md`](ui-spec.md) §11; a flag, not a state, api §7.1) and the runner checks the head's log. *(assumed — pending Thomas, inbox #28)* When heartbeats still arrive but report internal errors or stalled hook counters, the run shows 'bridge degraded' instead ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.3). *(assumed — pending Thomas, inbox #28)*
- **Storage.** Quotas and inodes (Lustre, GPFS, BeeGFS, NFS), free space on the work directory, and scratch purge policies with the work directories at risk. Quotas are the most common cause of failed nf-core runs that a scheduler does not explain.
- **Software.**
  - Apptainer / Singularity cache size and `NXF_SINGULARITY_CACHEDIR` presence.
  - Conda environment build failures.
  - Container registry rate limits, which show as `ImagePullBackOff`, or as pull errors in the task log on HPC.
- **Network to the server.** The runner's outbound connection: latency, reconnects, events buffered locally when the server is unreachable (synthesis: local buffer).
- **Site monitoring, optional and read-only.** Links from the environment page to the site's Grafana (Prometheus SLURM exporter), XDMoD or OpenCost (Kubernetes cost), when configured. Spectio never needs them.

## 8. Data model and events

The contracts (tables, events, endpoints) are owned by [`api-and-data-model.md`](api-and-data-model.md) §5, §7 and §8; this section explains them. *(assumed — pending Thomas, inbox #29)*

- **`scheduler_jobs`.** Columns:
  - identity: `id`, `environment_id`, `runner_id`, `native_id`, `array_parent_id`, `kind` (head / task);
  - links: `run_id`; engine attempts through the n:m `attempt_jobs` table (api §7) *(assumed — pending Thomas, inbox #29)*;
  - queue state: `state`, `reason`, `queue` (partition), `nodes`;
  - timing: `submit_at`, `est_start_at`, `start_at`, `end_at`;
  - resources: `requested` {cpus, mem, gpus, time}, `used` {cpu_time, max_rss, gpu, energy};
  - outcome: `exit_code`, `failure_class`, `raw_ref` (the last raw record, in the file store, kept only for failed jobs) *(assumed — pending Thomas, inbox #28)*;
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
- **Environment → Capacity** (board `EnvCapacity`, a tab of the environment page ([`ui-spec.md`](ui-spec.md) §4.8)):
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
| MVP | head job (L1), `squeue --me` poll (L2), `sacct` for outcomes (L3), failure classes | head Job, watch, pod reasons and OOMKilled | — |
| 1b | capacity (L4), quotas, reservations, pre-flight, relaunch suggestions | ResourceQuota, PVC usage, pre-flight | — |
| 2 | slurmrestd transport, `jobcomp/kafka` via the Kafka bridge | Kueue visibility, metrics-server, Prometheus plugin | LSF, PBS Pro / OpenPBS, HTCondor, Flux plugins |
| 3 | energy and carbon | OpenCost | Grid Engine, cloud batch |

## 12. Open questions for EMBL

1. Is slurmrestd available to users, and with which auth?
2. Are long-running processes allowed on login nodes (`loginctl enable-linger`), or is a service node needed for runners?
3. Does the site rate-limit `squeue` and `sacct`, and is `jobcomp/kafka` an option?
4. What are the scratch file system, quota command and purge policy?
5. Is Kueue (or another batch queue) installed on EMBL's Kubernetes, and can runners read node pools?
6. Is outbound HTTPS allowed from compute nodes, and through which proxy? (decides whether the bridges' direct post works; [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13.1) *(assumed — pending Thomas, inbox #28)*
7. Does the site set `PrivateData=jobs`, and is `AccountingStoreFlags=job_env` enabled in slurmdbd? ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2.1) *(assumed — pending Thomas, inbox #14)*

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
