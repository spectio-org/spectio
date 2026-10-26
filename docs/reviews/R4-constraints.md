# R4 · Implementation constraints and risks

**Round:** R4 (constraints) · **Date:** 2026-10-26 · **Found by:** constraints-hunter, two instances in parallel · **Status of the round:** waiting for triage (TRIAGE1)

**Sources.**
- **Branch and commit:** `autopilot/integration` at `3b209d3`. Line numbers ("l.") refer to that commit.
- **Round brief:** [`next-phase.md`](../playbooks/next-phase.md) R4. Each risk names the cheapest spike that would confirm or kill it.
- **Reviewer scopes:**
  - (a) server, data model, events, SQLite and Postgres, SSE, outbox, background tasks, backups, with numbers for a run of 100 000 tasks and 50 concurrent runs: [`api-and-data-model.md`](../specs/api-and-data-model.md), [`admin-and-operations.md`](../specs/admin-and-operations.md), [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md), [`synthesis.md`](../specs/synthesis.md);
  - (b) runner, engines, schedulers, Kubernetes, HPC site policies and the stability of third-party APIs: [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md), [`synthesis.md`](../specs/synthesis.md), [`checking-scenarios.md`](../specs/checking-scenarios.md), [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md).
- **Reviewer status:** both reviewers returned output. None failed.
- **External code read by the reviewers** (read-only, scratch work in `/tmp/w1-scratch/`, not kept in the repository):
  - **Nextflow** `114f1fe` (26.10.3), plus the trees of the tags `v24.10.0`, `v25.04.0`, `v25.10.0` and `v25.10.9`;
  - **snakemake** `1c67a66` (2026-10-19), **snakemake-interface-logger-plugins** `f27aaf1` (2026-05-20), **snakemake-executor-plugin-slurm** `8c2af56` (2026-09-28);
  - **Slurm 26.05** man pages (`squeue`, `slurm.conf`, `scrontab`) and the REST release notes;
  - **SQLite** [WAL](https://www.sqlite.org/wal.html) and [transaction](https://www.sqlite.org/lang_transaction.html) docs, the [Postgres 18 NOTIFY](https://www.postgresql.org/docs/18/sql-notify.html) docs, [PgBouncer features](https://www.pgbouncer.org/features.html), [Alembic batch mode](https://alembic.sqlalchemy.org/en/latest/batch.html), [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource), the [kube-apiserver reference](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver/), the [Kueue docs](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/), [systemd.kill](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html), and PyPI metadata (checked 2026-10-26).
- **Earlier rounds:** findings open in [R1](R1-consistency.md) (`SR-`, same tick, also waiting for triage), [R12](R12-ui-scenarios.md) (`UX-`) and [R8b](R8b-depictio-tooling.md) (`DEP-T-`) are cited, not repeated. Where an R4 finding adds a constraint (numbers, failure mechanics) to an R1 finding, it stays here with a **Related** line; both should be triaged together.

**Merge method** (review-round skill, steps 3-4):
- **Input:** reviewer (a) returned 25 findings (0 blockers, 17 majors, 8 minors) as CH-101 to CH-125. Reviewer (b) returned 25 findings (1 blocker, 17 majors, 7 minors) as CH-201 to CH-225. Every finding below lists its original IDs under "Found by".
- **De-duplication inside R4:** six pairs or triples describe the same problem and were merged:
  - the compatibility window of the bridge and runner protocols (CH-115, CH-216);
  - durable, idempotent runner commands (CH-108, CH-209 in part);
  - Continue or relaunch racing the previous head (CH-109, CH-209 in part);
  - restore while runs and engines are still live (CH-112, CH-217);
  - head logs flooding the log ring buffer (CH-118, CH-221);
  - clock skew (CH-120, CH-223);
  - licences (CH-123, CH-225).
- **Cited, not repeated (already in R1):** four findings restate an R1 finding with no new constraint. They are listed in [§ Cited, not repeated](#cited-not-repeated) and are not counted below:
  - CH-116 → SR-005;
  - CH-205 → SR-014;
  - CH-220 → SR-037;
  - CH-222 → SR-035.
- **Verification:** every quoted spec passage of every blocker and major was opened at `3b209d3` and confirmed. All of them reproduced, so **0 findings were dropped**. The SQLite benchmark of reviewer (a) was re-run for this merge (Python 3, SQLite 3.45.1, 500 000 events): 733 MB, 27.3 k events/s, 6.6 s to rewrite one run's events to another project. That matches the reviewer's figures. Claims about other tools keep the reviewer's source, or are marked **[to be validated]**.
- **Ranking:** by severity, then by the number of documents the finding touches (specs, the decision log, decision 0001), shown in the findings table.
- **Proposed new sections:** this file reuses the numbers that R1 already assigned (api §14 ingest contract, architecture §7.7 runner protocol, architecture §12 compatibility between components) and assigns free numbers for the rest:
  - api §8.1: the server's event pipeline (append, project, publish) and back-pressure;
  - api §15: scale model and performance budgets;
  - architecture §13: engine bridges (spool, sender, failure semantics). Reviewer (b) proposed §12, which R1 already gives to compatibility.

Format: [`README.md`](README.md). Prefix `CH` (constraints hunter). Specs were not edited in this round.

## Summary

| Severity | Count |
|---|---|
| Blocker | 1 |
| Major | 29 |
| Minor | 10 |
| **Total** | **40** |
| Cited, not repeated (in R1) | 4 |
| Dropped (not reproducible) | 0 |

**What the numbers say.** Raw SQLite write throughput is not the problem: about 27 k events/s per stream, measured, against a peak need in the low thousands per second. The risks are elsewhere: long write locks and long readers, storage growth (about 0.7–0.9 GB per 100 000-task run), the single event loop, the ordering and delivery semantics, and what the HPC site allows the engine and the runner to do.

**The five findings that matter most:**
1. **CH-001: the recommended head job puts the engine bridge on a compute node, where outbound network is often blocked.** synthesis §10 says the network risk is "not the compute nodes", but a head job *is* on a compute node. The only fallback (a server-side forwarder) contradicts "the server never mounts storage". Plugin download, image pulls and conda builds fail there too. At such a site there is no monitoring and no gate.
2. **CH-006: a break in `TraceObserverV2` (`@Beta`) would be silent.** Nextflow swallows any `Throwable` from an observer and logs it at debug level, so a `NoSuchMethodError` stops all events with nothing to explain it. Nextflow < 25.04 has no `TraceObserverV2` at all, and no spec states a minimum version.
3. **CH-007 and CH-003: duplicate head jobs.** No commands table, no lease and no idempotent launch: a runner that dies between `sbatch` and its acknowledgement submits a second head into the same launch directory. Continue or relaunch can start while the previous JVM still holds the cache lock, which automation (`agent_auto`) makes likely.
4. **CH-004: no scale model and no performance budgets.** Nobody can tell when "migration to Postgres if needed" applies, the Runs list needs per-run counters the schema does not have, and the graph endpoint has no granularity for 100 000 tasks.
5. **CH-011: the event log grows without bound, and raw Nextflow trace records carry `script` and `env`.** That size then drives backup time (CH-022), migration time (CH-023) and a possible secret leak (R5).

## Findings table

| ID | Severity | Title | Documents touched |
|---|---|---|---|
| CH-001 | blocker | The recommended head job puts the engine and its event bridge on a compute node, where outbound network is often blocked | 5 |
| CH-002 | major | No compatibility window for the ingest and runner protocols across bridge, runner and server versions | 5 |
| CH-003 | major | Continue or relaunch can start while the previous head is still finishing | 5 |
| CH-004 | major | No scale model and no performance budgets in any spec | 4 |
| CH-005 | major | No traffic budget for the engine bridges: batching, back-pressure and spool limits | 4 |
| CH-006 | major | `nf-spectio` failure semantics are unspecified, and a break in the `@Beta` interface would be silent | 4 |
| CH-007 | major | Runner commands have no table, three transports and no idempotent launch | 4 |
| CH-008 | major | SSE fan-out: no coalescing, a 6-connection limit per browser, the full task stream to every tab | 4 |
| CH-009 | major | Snakemake: the logger interface keeps moving, only Snakemake ≥ 9 works, and `SnakemakeApi` cannot run from the runner's environment | 4 |
| CH-010 | major | Gate waits run against the scratch purge, and Nextflow cannot estimate cache hits beforehand | 4 |
| CH-011 | major | The event log grows without bound, and raw Nextflow trace records carry `script` and `env` | 3 |
| CH-012 | major | Projection in the ingest transaction, in one process and one event loop, stalls the UI and SSE during bursts | 3 |
| CH-013 | major | SQLite lock discipline: `SQLITE_BUSY` on lock upgrade, long write locks, checkpoint starvation | 3 |
| CH-014 | major | Gate concurrency beyond `If-Match`: quorum, bulk decisions, whole change-set replacement, timeout races | 3 |
| CH-015 | major | Personal mode "on a login node" conflicts with the local-disk rule | 3 |
| CH-016 | major | Stopping at a gate through `ext.when` is proven only on synthetic pipelines | 3 |
| CH-017 | major | Live checks on the runner: one MultiQC call per file on login nodes | 3 |
| CH-018 | major | Resumable streams have no sound cursor | 2 |
| CH-019 | major | Event order: `seq` is the server's arrival order, with no source sequence and no merge rule | 2 |
| CH-020 | major | Postgres `LISTEN/NOTIFY` as the cross-process bus: payload cap, commit-time lock, poolers | 2 |
| CH-021 | major | Restore failure modes while runs and engines are still live | 2 |
| CH-022 | major | Logical JSON Lines backups do not scale, need one snapshot, and have no RPO or RTO | 2 |
| CH-023 | major | Schema migrations with live traffic: Helm hook against old pods, readiness "at head", SQLite table copies | 2 |
| CH-024 | major | Kubernetes: Kueue API versions, the one-hour lifetime of Events, the head pod's RBAC, Kueue and Nextflow Pods | 2 |
| CH-025 | major | Apptainer, the usual HPC container runtime, is untested; the whole matrix uses Docker | 2 |
| CH-026 | major | 50 concurrent runs under one account break SLURM per-user limits; the §0.2 sentence overstates | 1 |
| CH-027 | major | `squeue` and `sacct --json` are heavy, and their schema changes with each Slurm version on the CLI path too | 1 |
| CH-028 | major | Hosting the runner on login nodes: `scrontab` does not run there, systemd kills supervised heads, duplicate runners | 1 |
| CH-029 | major | Head job sizing and the walltime limit | 1 |
| CH-030 | major | Moving a run between projects rewrites millions of rows, and contradicts the append-only log | 1 |
| CH-031 | minor | Clock skew has no rule: engine-host time, server time, ULIDs, freshness checks | 4 |
| CH-032 | minor | Runner channel in practice: proxies, idle timeouts, the JVM and internal CAs | 3 |
| CH-033 | minor | Restart storms: false "offline" runners and simultaneous replays | 3 |
| CH-034 | minor | Licences of server dependencies, scheduler integrations and copied code are not tracked | 3 |
| CH-035 | minor | A Provenance Run Crate of 100 000 tasks has no size budget | 3 |
| CH-036 | minor | Outbox: ordering against 24 h retries, one queue for every subscriber, storms of task events | 2 |
| CH-037 | minor | A Lustre stall blocks the runner's event loop, and the server marks it offline | 2 |
| CH-038 | minor | Engine head logs will flood the log ring buffer, which shares the database | 1 |
| CH-039 | minor | Search across runs, tasks and samples has no portable implementation | 1 |
| CH-040 | minor | Idempotency keys have no storage, scope, retention or race rule | 1 |

## Scale model used in this round

No spec has a scale model (CH-004), so the reviewers used these assumptions. "Measured" means a scratch benchmark by reviewer (a), re-run for this merge.

| Quantity | Value | Basis |
|---|---|---|
| Events per Nextflow task | about 4–5 lifecycle events (pending, submit, start, complete; cached on resume), +10 % for retries, plus one `onFilePublish` per published file | `TraceObserverV2.groovy:77-140` (Nextflow `114f1fe`). The burst shape is **[to be validated]** in T2 and `fanout_stress` |
| One run of 100 000 tasks | about 0.45–0.6 M events | from the line above |
| Size of those events in SQLite | **733 MB for 500 000 events**, about 1 KB payloads including a 600-byte synthetic `script` field (measured) | WAL, `synchronous=NORMAL`, batches of 100, events table plus 2 indexes, task upsert |
| Ingest throughput, one stream, SQLite | **27–29 k events/s** with raw `sqlite3`; **27.7 k events/s** with Pydantic v2 plus SQLAlchemy Core (measured, 4 cores) | as above |
| Team server, low scenario | 75–150 runs a day of about 5 000 tasks: 2–4 M events and 2–4 GB a day, about 1 TB a year unpruned; average 30–45 events/s, bursts of 1–10 k events/s per run at stage boundaries and array completions | estimate, reviewer (a) |
| Team server, high scenario | 50 concurrent runs of 100 000 tasks over 24 h: about 250–350 events/s sustained, bursts in the low thousands per second | estimate, reviewer (b) |
| Bridge buffer for a 1-hour outage | 20 000–30 000 events per 100 000-task run | estimate, reviewer (b) |
| Moving one 100 000-task run to another project | **5.9–6.6 s** holding the SQLite write lock, for the event rows alone (measured) | as above |

---

## Blockers

### CH-001 · blocker · The recommended head job puts the engine and its event bridge on a compute node, where outbound network is often blocked

- **Where:** schedulers-and-monitoring.md §3.1 and §12; synthesis.md §8 and §10 (item 2); checking-scenarios.md §11.1; decision [0001](../decisions/0001-nextflow-through-nf-spectio.md) (consequences); architecture (no owner today).
- **Evidence:**
  - "On HPC the engine's head process is run as a **head job** … This is the recommended mode because login nodes usually kill long processes" (schedulers §3.1, l.64).
  - "The risk therefore concerns the node where that process runs (login node or `sbatch` head job), not the compute nodes" (synthesis §10, l.396). A head job runs *on* a compute node.
  - "**Egress from compute nodes** is often filtered: test early. Fallback: the agent writes JSONL to the shared file system, and a server-side forwarder reads it" (synthesis §8, l.367), against "The server never mounts storage" (checking §11.1, l.261). The server-side forwarder cannot exist.
  - The Snakemake SLURM executor warns against this mode: "You are running snakemake in a SLURM job context. This is not recommended … please run Snakemake directly on the login node" (`snakemake_executor_plugin_slurm/__init__.py:459-467`, `8c2af56`).
  - Nextflow downloads plugins into `$NXF_HOME/plugins` at start; "plugin versions MUST be specified in offline mode" (`nf-commons/.../PluginUpdater.groovy:54, 477-478`, `114f1fe`).
  - The head also pulls container images, builds conda environments, and reads the pipeline manifest through the GitHub API, which was rate-limited in the spike ([spike note](../research/spike-synthetic-pipelines-2026-10-26.md), addendum).
  - The EMBL questions (schedulers §12, l.297-303) do not ask about outbound network from compute nodes.
- **Problem:** at a site that filters compute-node egress, `nf-spectio` and the Snakemake logger cannot reach `POST /ingest/events`, and plugin download, image pulls and conda builds fail too. No component relays events, so the MVP's only ingestion path does not work in the mode the spec recommends. The ingest credential also has to exist on a compute node, which is not specified (credential side: R5, and SR-001).
- **Proposal:**
  - **architecture §13 "Engine bridges" (new):** each bridge appends its events to a spool in the launch directory (`.spectio/events/*.jsonl`, append-only, rotated). It also posts directly when the network allows. The **runner** tails the spool from the login node and forwards it. Event IDs make both paths idempotent. The wire format belongs to the ingest contract (api §14, SR-001).
  - **schedulers §3.1:** the runner does all network-dependent preparation on the login node before `sbatch`: git clone at a pinned commit, plugins into `NXF_PLUGINS_DIR` at pinned versions, the `NXF_VER` distribution, image pre-pull, and `--conda-create-envs-only`. The head then runs with `NXF_OFFLINE=true`.
  - **synthesis §10 item 2 and §8:** rewrite them to match, and remove the server-side forwarder.
  - **schedulers §12:** add "Is outbound HTTPS allowed from compute nodes, and through which proxy?"
- **Likelihood · impact:** high (common HPC policy) · high (no monitoring, no gates).
- **Cheapest test:** one hour at EMBL. A one-minute `sbatch` job runs `curl` to an external endpoint, `registry.nextflow.io`, `quay.io` and `github.com`, with and without `$https_proxy`. On sind, put the compute nodes on a Docker network without egress and run nf-toy offline with a pre-filled `NXF_PLUGINS_DIR`.
- **Related:** SR-017 (R1) on the spool fallback.
- **Found by:** constraints-hunter (b) as CH-201
- **Status:** open

---

## Majors

### CH-002 · major · No compatibility window for the ingest and runner protocols across bridge, runner and server versions

- **Where:** api-and-data-model.md §4 (Versioning), §8; admin-and-operations.md §3.2 (Version skew); synthesis.md §10 item 4; architecture §2, §4; dev-environment-and-testing.md §12.
- **Evidence:**
  - "only additive changes within v1" covers the REST API (api §4, l.80).
  - "**Version skew** beyond one minor version shows a warning" (admin §3.2, l.147): this covers runners, not the engine bridges.
  - "Pin versions, test in CI, version the event schema" (synthesis §10, l.398).
  - "`snakemake-logger-plugin-spectio` on PyPI, installed in the Snakemake environment" (architecture §2, l.61); `nf-spectio` lives in the Nextflow plugin registry.
  - "**Pre-1.0 policy:** minor versions may break the API" (dev-env §12, l.377).
- **Problem:** bridge versions are pinned in user environments, sometimes for years (conda locks, `nextflow.config` plugin pins), and are not upgraded with the server. With no accepted range and no typed refusal, a server upgrade silently drops events from old bridges, a newer bridge sends fields an older server rejects, and runs in flight break during an upgrade.
- **Proposal:**
  - The ingest schema is versioned on its own (`Spectio-Ingest-Version` header, or a `schema_version` per batch) in api §14 (SR-001).
  - architecture §12 (SR-022) states the window: for example every bridge released in the last 12 months, and the current and previous server minor. Servers ignore unknown fields. Outside the window the server answers `problem+json` type `ingest-version-unsupported`.
  - The server records bridge versions per run; Health shows "bridge too old". Runner capabilities are negotiated at registration.
  - Tier 1 or 2 replays the golden fixtures of every released bridge version against the current server. Upgrade tests: DEP-T-011.
- **Likelihood · impact:** high · high (silent data loss).
- **Cheapest test:** after T2, replay the golden fixtures against a schema with one field renamed (2 h). Define the contract test now; it costs nothing until there is code.
- **Related:** SR-022 (R1) owns the overall compatibility table; this finding adds the bridge-specific window and the refusal type.
- **Found by:** constraints-hunter (a) as CH-115, constraints-hunter (b) as CH-216
- **Status:** open

### CH-003 · major · Continue or relaunch can start while the previous head is still finishing

- **Where:** synthesis.md §5ter.2 (state machine), §5ter.4–6; api-and-data-model.md §5 (`:resume`, `:relaunch`), §7 (`runs`); schedulers-and-monitoring.md §3.1; checking-scenarios.md §11.3; ui-spec.md §4.6.
- **Evidence:**
  - "`continue` → `RUNNING(k+1)`" (synthesis §5ter.2, l.221).
  - The end of a stage is detected from "Nextflow `onFlowComplete` reported by `nf-spectio`" (synthesis §5ter.4, l.235).
  - A live-check stop lets "tasks already running finish" (checking §11.3, l.324).
  - Nextflow fails with "Unable to acquire lock on session with ID … You are trying to resume the execution of an already running pipeline", and on file systems without locks with "Can't open cache DB … common for network file systems (NFS, Lustre, GPFS, …)" (`cache/DefaultCacheStore.groovy:80-94`, `114f1fe`).
  - Snakemake needs "`unlock` + `rerun_incomplete` after an abrupt stop" (synthesis §5ter).
  - api §7 has no per-launch entity (l.222: `runs` has `stage_index`, `parent_run_id`, `relaunch_mode` only).
- **Problem:**
  - `onFlowComplete` arrives before the JVM exits and releases its LevelDB cache lock. A fast approver, an AI agent with `agent_auto`, a double click, or a `:relaunch` after `:cancel` starts `-resume` or a second Snakemake in the same directory: a lock error, or two engines on one directory. The exact behaviour of the `.nextflow/cache/<session>` lock and `.snakemake/locks` is **[to be validated]**.
  - "Which head is alive" cannot be expressed in the schema.
  - Sites where Lustre is mounted without `flock` cannot resume at all.
- **Proposal:**
  - api §7: add `launches` (or `run_attempts`): `run_id, n, head_native_id, head_state, started_at, exited_at, exit_code`.
  - synthesis §5ter.2: add a `CONTINUE_REQUESTED` state. The resume command is released only after the runner reports that the previous head has left the queue and its process is gone, and the lock is free.
  - The runner keeps a mutex per launch directory.
  - schedulers §3.5 pre-flight checks file-lock support in the launch directory (fallback `NXF_CACHE_DIR` on a locking file system **[to be validated]**).
- **Likelihood · impact:** high with automation · high (double runs, failed resumes).
- **Cheapest test** (half a day, sind, nf-toy and smk-toy from T1): resume 0 s, 1 s and 5 s after the last event; `kill -9` the head, then `-resume`; nf-toy with its launch directory on an NFS export mounted `nolock`.
- **Found by:** constraints-hunter (a) as CH-109, constraints-hunter (b) as CH-209 (relaunch and lock parts)
- **Status:** open

### CH-004 · major · No scale model and no performance budgets in any spec

- **Where:** api-and-data-model.md §4, §5, §7; ui-spec.md (Data); dev-environment-and-testing.md §6, §10; synthesis.md §10 item 7.
- **Evidence:**
  - "A single SQLite writer under heavy load: batched inserts, migration to Postgres if needed." (synthesis §10, l.401)
  - "Pagination on Runs and Tasks (depictio lists have none; Spectio lists grow without bound)." (ui-spec l.226)
  - The Runs list shows "2 of 4 stages · 63 % tasks" (ui-spec l.81); `runs` only has `stage_index` (api l.222).
  - `GET /runs/{id}/graph` (api l.93) has no stated granularity.
  - The only scale fixture is "`fanout_stress` | about 12 000 ALIGN tasks (nightly)" (dev-env l.282), and it was "not run in this session" ([spike note](../research/spike-synthetic-pipelines-2026-10-26.md), l.79).
- **Problem:** no spec sets events per second, rows per day, database size per run, or latency targets, so nobody can tell when "migration to Postgres if needed" applies. At 10 000 runs, the Runs list needs counters stored per run; computing them from `tasks` on every list query will not meet any reasonable target. A task-level graph of 100 000 nodes cannot be served or drawn.
- **Proposal:** add api §15 "Scale model and budgets", with the table in [§ Scale model](#scale-model-used-in-this-round) as defaults:
  - `GET /runs` p95 < 300 ms at 10 000 runs and 200 visible projects;
  - Run detail first paint < 1 s, and `GET /runs/{id}/tasks` p95 < 300 ms at 100 000 tasks, with keyset pagination on every sortable column;
  - per-run and per-process counters by state, kept in the projection;
  - a process-level graph only;
  - ingest p99 < 100 ms per batch of 100;
  - SSE lag p95 < 2 s.

  Add a tier-5 benchmark to dev-env §6, on SQLite and Postgres (overlaps DEP-T-012; metric names belong to DEP-T-029).
- **Likelihood · impact:** high · high (rework of the schema and the projections).
- **Cheapest test:** spike S1 (seed generator plus a 300-line FastAPI prototype; see [§ Proposed spikes](#proposed-spikes)).
- **Found by:** constraints-hunter (a) as CH-101; the high scenario comes from constraints-hunter (b) CH-203
- **Status:** open

### CH-005 · major · No traffic budget for the engine bridges: batching, back-pressure and spool limits

- **Where:** synthesis.md §2bis, §2ter (item 4); api-and-data-model.md §7–8; architecture (bridges, no owner today); decision [0001](../decisions/0001-nextflow-through-nf-spectio.md) ("batching and local buffer").
- **Evidence:**
  - Each task fires `onTaskPending`, `onTaskSubmit`, `onTaskStart` and `onTaskComplete`, plus one `onFilePublish` per published file (`TraceObserverV2.groovy:77-140`, `114f1fe`).
  - Nextflow grid executors default to `queueSize` 100 and a 1-minute `queueStatInterval` (`AbstractGridExecutor.groovy:68`; schedulers §1), so completions arrive in bursts after each queue refresh.
  - Decision 0001 promises "batching and local buffer" with no numbers.
- **Problem:** at 0.45–0.6 M events per 100 000-task run (scale model), the bridges have no batch size, no compression, no rule to send deltas instead of the full record each time, no back-pressure contract (`429` + `Retry-After`), and no cap or drop rule on the buffer. A 1-hour outage means 20 000–30 000 events per run: too much for an in-JVM queue in a 4 GB head.
- **Proposal:** in architecture §13 (new, see CH-001), with the wire side in api §14 (SR-001):
  - batches of at most 500 events or 1 s, gzip;
  - the full trace only on terminal events, deltas otherwise;
  - `429` and `503` honoured with `Retry-After`; the bridges never fail the run on ingest errors;
  - a disk spool capped at 1 GB by default; the oldest non-terminal events are dropped first, terminal events never;
  - a dropped-event counter in each heartbeat.
- **Likelihood · impact:** high · medium–high.
- **Cheapest test:** from the T2 golden stream, measure bytes per event. Run `fanout_stress` (about 12 000 tasks) against a capture server and count events and the peak rate.
- **Related:** SR-017 (R1) sets the bounds for an unreachable server; this finding sets the volume budget.
- **Found by:** constraints-hunter (b) as CH-203; the back-pressure part also in constraints-hunter (a) CH-103 and CH-121
- **Status:** open

### CH-006 · major · `nf-spectio` failure semantics are unspecified, and a break in the `@Beta` interface would be silent

- **Where:** synthesis.md §2, §2bis and §10 (item 4); decision [0001](../decisions/0001-nextflow-through-nf-spectio.md); dev-environment-and-testing.md §1, §11; architecture (bridges).
- **Evidence:**
  - `TraceObserverV2` is `@Beta` (`trace/TraceObserverV2.groovy:32`, `114f1fe`; synthesis l.19). It first appears in `v25.04.0`; the `v24.10.0` tree has no `*ObserverV2*` file.
  - Observers are called synchronously in a loop; any `Throwable` other than `AbortRunException` is logged **at debug level** and swallowed (`Session.groovy:1347-1361`).
  - A plugin whose `requires` range excludes the running Nextflow aborts the launch: "Failed requirement - Plugin $name requires Nextflow version …" (`nf-commons/.../BasePlugin.groovy:52-53`).
  - `TaskEvent` carries the internal classes `TaskHandler handler` and `TraceRecord trace` (`trace/event/TaskEvent.groovy:35,39`).
  - synthesis still describes `nf-tower` behaviour as if it applied: "On the Nextflow side, a server outage during `create`, `begin` or `progress` aborts the run" (§10, l.396; also §2bis, l.46).
- **Problem:**
  - A slow HTTP call inside a hook blocks Nextflow's own thread; in `onTaskComplete` that is the task-polling thread.
  - An interface change shows up only as "head silent", with nothing to explain it.
  - Reading outputs "through the handler" (checking §11.1) depends on internals beyond the `@Beta` interface.
  - Pipelines and sites on Nextflow < 25.04 cannot use Spectio at all, and no spec says so.
- **Proposal:**
  - **architecture §13 (new):** hooks only enqueue; a sender thread batches; the plugin never throws, and never throws `AbortRunException`. Each heartbeat carries the plugin and Nextflow versions, hook counters and an internal-error counter, so the server shows "bridge degraded" rather than "head silent".
  - State the minimum supported Nextflow (25.04 or 25.10) in the docs; the runner checks it before launch; `requires` equals the tested range.
  - **dev-env §11:** a weekly job runs nf-toy with `nf-spectio` against Nextflow `edge` and the latest stable and diffs the events against the golden fixtures.
  - **synthesis §10 item 2:** remove the abort sentence (it describes `nf-tower`).
- **Likelihood · impact:** medium (Beta API, internals) · high (silent loss of all Nextflow data).
- **Cheapest test:** extend T2 by half a day: a hook that throws and a hook that sleeps 30 s; the server down for 10 minutes; the plugin built against 25.10 run on 26.10 and on 25.04; a `requires` mismatch. Record whether the run aborts, stalls or goes silent.
- **Related:** SR-017 (R1).
- **Found by:** constraints-hunter (b) as CH-202
- **Status:** open

### CH-007 · major · Runner commands have no table, three transports and no idempotent launch

- **Where:** api-and-data-model.md §5 (Environments and runners), §7; admin-and-operations.md §3.2; architecture-plugins-and-packaging.md §7.6; schedulers-and-monitoring.md §3.1.
- **Evidence:**
  - "runner channel `WS /runners/{id}/channel` (commands, heartbeats, file streaming)" (api §5, l.92).
  - "runner pulls over outbound HTTPS (long poll or SSE)" (architecture §7.6, l.385).
  - "The server records the request and the runner claims it" (admin §3.2, l.146).
  - api §7 has no commands table.
  - Head jobs are named `spectio-<run_id>` (schedulers §3.1, l.64).
- **Problem:** delivery of launch, cancel and resume is at least once at best. A runner that crashes between `sbatch` and its acknowledgement gets the launch again and starts a **second head job in the same launch directory**. A decision or relaunch committed without its command in the same transaction can be lost. With several API replicas, the replica holding the runner's long poll must be woken.
- **Proposal:**
  - api §7: add `runner_commands(id, runner_id, run_id, launch_id, kind, payload, idempotency_key, state (pending, leased, acked, done, failed), lease_until, attempts)`, written in the same transaction as the decision or relaunch.
  - architecture §7.7 (SR-002): one transport.
  - Launch is idempotent on the runner side: the head job is named `spectio-<run>-<launch>`; before `sbatch` the runner looks for that name in its `squeue --me` / `sacct` snapshot and adopts the job if it exists (name filtering: SR-037).
- **Likelihood · impact:** medium · high (duplicate runs, corrupted engine state).
- **Cheapest test** (half a day, sind `slurm-mini`): `kill -9` the runner right after `sbatch`, restart it, and count head jobs.
- **Related:** SR-002 (R1) owns the protocol (catalogue, ack, replay); this finding adds the table, the lease and the duplicate-launch mechanics.
- **Found by:** constraints-hunter (a) as CH-108, constraints-hunter (b) as CH-209 (exactly-once launch part)
- **Status:** open

### CH-008 · major · SSE fan-out: no coalescing, a 6-connection limit per browser, the full task stream to every tab

- **Where:** api-and-data-model.md §8, §9 (embedded elements); synthesis.md §7; ui-spec.md (Data: TanStack Query plus SSE); admin-and-operations.md §3.4 (log tail).
- **Evidence:**
  - `spectio.task.failed`, `.retried`: "noteworthy task events (full task stream via SSE only)" (api §8, l.246).
  - "one multiplexed stream per tab" (synthesis §7, l.269).
  - MDN: "When **not used over HTTP/2**, SSE suffers from a limitation to the maximum number of open connections … per browser and set to a very low number (6) … marked as 'Won't fix'" ([MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)).
  - Browsers use HTTP/2 only over TLS, so `http://127.0.0.1` and SSH tunnels stay on HTTP/1.1 **[to be validated in S5]**.
- **Problem:**
  - At 1–10 k events/s for one run, every watching tab parses and applies each event; the TanStack Query cache churn freezes the tab.
  - In personal mode or behind an SSH tunnel, the seventh connection hangs; tabs, the admin log tail and embedded elements in a LabID page all count.
  - On Kubernetes with an HPA, long-lived streams pin to pods, and every rollout or scale-down causes a reconnect storm of replay queries.
- **Proposal:**
  - api §8: the server sends one coalesced delta per run at most once per second (counters per process and state, IDs of changed rows). Raw task events go only to a client that has that task open.
  - One `EventSource` per browser (SharedWorker, or BroadcastChannel with leader election); embedded elements reuse it.
  - Document HTTP/2 through Caddy or the Ingress for team servers.
  - A per-process cap on SSE clients, and jittered reconnects.
- **Likelihood · impact:** high · high (the UI is unusable on big runs).
- **Cheapest test** (2 h, spike S5): seven tabs on a local uvicorn; replay a 100 000-event burst into a Vite and TanStack prototype; record dropped frames.
- **Found by:** constraints-hunter (a) as CH-106
- **Status:** open

### CH-009 · major · Snakemake: the logger interface keeps moving, only Snakemake ≥ 9 works, and `SnakemakeApi` cannot run from the runner's environment

- **Where:** synthesis.md §2 (l.29) and §5ter.6; architecture-plugins-and-packaging.md §3.6, §6; cli-and-shared-libraries.md §6 (< 80 MB); dev-environment-and-testing.md §1.
- **Evidence:**
  - "one Python worker per run that calls the API (`SnakemakeApi`, `DAGSettings(until=…)`, `ConfigSettings`) rather than a `subprocess` on the CLI" (synthesis §2, l.29).
  - The logger plugin interface arrived in Snakemake **9.0.0** (2025-03-14, "Logging refactor & add LoggerPluginInterface", `CHANGELOG.md` at `1c67a66`).
  - `snakemake-interface-logger-plugins` has had three breaking releases: 0.2.0 (2025-02-12), 1.0.0 (2025-03-10), 2.0.0 (2025-09-28: "All LogHandlerBase subclasses must now implement the emit() method") (`CHANGELOG.md`, `f27aaf1`).
  - Snakemake accepts interface versions `>=1.1.0,<3.0.0` (`pyproject.toml:57`, `1c67a66`).
  - The runner ships in the base install: "httpx, pydantic, typer, rich and nothing else", under 80 MB (cli §0, l.19; §6, l.170).
- **Problem:**
  - Importing Snakemake into the runner ties every workflow to the runner's Snakemake and executor-plugin versions; a lab with workflows pinned to different Snakemake versions cannot share one runner, and the 80 MB budget breaks.
  - Snakemake ≤ 8, still common in site modules **[to be validated]**, is not supported, and no spec says so.
  - A Snakemake from a site module is read-only, so `pip install snakemake-logger-plugin-spectio` fails there.
- **Proposal:**
  - synthesis §2 and §5ter.6, architecture §3.6: Snakemake runs as a CLI subprocess in a per-workflow environment (pixi, conda or module), its version pinned per lineage as `NXF_VER` does for Nextflow. The Python API is used only through a small shim inside that environment.
  - Support Snakemake ≥ 9.0 and logger interface 1.x and 2.x, tested in CI.
  - Inject the logger plugin through `PYTHONPATH` when the environment is read-only; discovery scans module prefixes (architecture §1) **[to be validated]**.
  - Python and OS matrix: DEP-T-018.
- **Likelihood · impact:** high · high (otherwise the runner is built around the wrong process model).
- **Cheapest test** (half a day): a runner environment without Snakemake launches smk-toy in a pixi environment pinned to 9.27.1, and in a read-only environment with the plugin on `PYTHONPATH`; repeat with interface 1.2.5 and 2.1.0.
- **Related:** SR-008 (R1) asks Thomas to choose API worker or CLI head job; this finding adds the version facts that argue for the CLI.
- **Found by:** constraints-hunter (b) as CH-204
- **Status:** open

### CH-010 · major · Gate waits run against the scratch purge, and Nextflow cannot estimate cache hits beforehand

- **Where:** schedulers-and-monitoring.md §3.5 (pre-flight); synthesis.md §5ter.1 (`timeout: 48h`), §5bis (`external_wait`); ui-spec.md §4.6; checking-scenarios.md §5.
- **Evidence:**
  - Pre-flight lists "work directories that the scratch purge policy will delete before a `-resume`" (schedulers §3.5, l.152): checked only before launch.
  - `policy: { mode: agent_proposes_human_confirms, timeout: 48h, on_timeout: stop }` (synthesis §5ter.1, l.213).
  - The relaunch dialog promises "an estimate of reused vs to-run tasks" (ui-spec §4.6, l.124). The UI need is UX-113.
- **Problem:** during a long gate or a wet-lab wait, nothing touches the work directories. A partial purge then makes `-resume` silently recompute upstream stages, or removes a gated stage's outputs. Snakemake can count jobs with `--dry-run`; Nextflow has no command that predicts cache hits **[to be validated]**, so the estimate has to come from inspecting work directories. Touching files to dodge the purge breaks many sites' policies **[site-dependent]**.
- **Proposal:** in schedulers §3.5 and checking §5:
  - when the gate opens, the runner records the stage's cached outputs and the purge deadline;
  - the gate shows "work directory purged in N days";
  - at Continue, the runner checks a sample of outputs, and the UI labels the Nextflow figure an estimate.
- **Likelihood · impact:** medium · medium–high (lost compute, wrong estimates).
- **Cheapest test** (1 h): delete half the work directories of nf-toy stage A after a gate stop, `-resume`, and compare the cached count with a work-directory scan.
- **Found by:** constraints-hunter (b) as CH-212
- **Status:** open

### CH-011 · major · The event log grows without bound, and raw Nextflow trace records carry `script` and `env`

- **Where:** synthesis.md §2ter "Consequences" item 4, §4; api-and-data-model.md §7 (`events`), §8; admin-and-operations.md §4.4 (cleanup jobs).
- **Evidence:**
  - "**Keep the raw JSON** of each event alongside the normalised columns." (synthesis l.97)
  - Events are "append-only" (synthesis l.133).
  - Cleanup covers only "delivered outbox events older than the retention period" (admin §4.4, l.316).
  - Nextflow `TraceRecord.FIELDS` has 45 fields, including `script`, `env` and `workdir` (`modules/nextflow/src/main/groovy/nextflow/trace/TraceRecord.groovy:69-112`, `114f1fe`).
- **Problem:**
  - About 0.7–0.9 GB per 100 000-task run (measured 733 MB per 500 000 events), and about 1 TB a year on a team server in the low scenario.
  - `script` (often KBs for nf-core modules) and `env`, repeated on every lifecycle event, multiply that.
  - `env` may contain secrets (tenancy and secrets angle: R5).
  - The database size then drives backup time (CH-022) and migration time (CH-023).
- **Proposal:**
  - api §7 and §8: an event retention class. While a run is active, keep the full raw payload. Once the run is terminal (plus N days), move the raw payloads to one compressed `events-<run>.jsonl.zst` in the file store and keep only the normalised rows.
  - The raw payload kept per task is the terminal one (CH-005).
  - `nf-spectio` sends `script` and `env` at most once per task, or never (the runner reads `.command.sh` on demand), with a payload cap per event.
  - Amend synthesis §2ter item 4 to match.
- **Likelihood · impact:** high · high.
- **Cheapest test:** in S1, with real T2 payloads, compare bytes per event with and without `script` and `env`.
- **Found by:** constraints-hunter (a) as CH-102; the terminal-payload rule from constraints-hunter (b) CH-203
- **Status:** open

### CH-012 · major · Projection in the ingest transaction, in one process and one event loop, stalls the UI and SSE during bursts

- **Where:** synthesis.md §4, §7; architecture-plugins-and-packaging.md §7.1–7.2, §7.6 (`inprocess` backend); api-and-data-model.md §7–8.
- **Evidence:**
  - "The `runs` and `tasks` tables are projections updated in the same transaction." (synthesis §4, l.133)
  - "uvicorn with a single worker for the MVP" (synthesis §7, l.267).
  - The bundle runs "1 (api + worker + local runner)" process (architecture §7.2, l.308).
  - Background tasks run as "asyncio workers inside `spectio serve`" (architecture §7.6, l.400).
- **Problem:**
  - Measured: 200 000 events take 7.2 s of CPU with Pydantic plus Core. Throughput is fine.
  - But `sqlite3` calls are synchronous. A 100 000-event burst, or a CPU-heavy task (RO-Crate export, backup, check evaluation), blocks the loop that also serves SSE and the UI for seconds.
  - Slower acknowledgements make the bridges time out and retry, which adds load (idempotent through `unique (run_id, event_id)`, but not free).
  - Every new projection (counters, live checks, scheduler links) becomes a cost on the ingest hot path.
- **Proposal:** add api §8.1 "Event pipeline":
  1. ingest validates, appends the raw batch and acknowledges;
  2. one projector, on a dedicated writer thread or process with one write connection, builds the projections from the log;
  3. SSE reads the projections.

  Heavy tasks run in a subprocess pool, even in the bundle. Ingest returns `429` with `Retry-After` under back-pressure (bridge side: CH-005).
- **Likelihood · impact:** high in personal mode · medium to high.
- **Cheapest test:** S1/S2: UI p95 during a 100 000-event burst, with and without a separate writer.
- **Found by:** constraints-hunter (a) as CH-103
- **Status:** open

### CH-013 · major · SQLite lock discipline: `SQLITE_BUSY` on lock upgrade, long write locks, checkpoint starvation

- **Where:** architecture-plugins-and-packaging.md §7.2 ("SQLite runs in one process only"); admin-and-operations.md §3.5 (Health), §4.4 (VACUUM); synthesis.md §7.
- **Evidence:**
  - "**SQLite runs in one process only.**" (architecture §7.2, l.319), with no rule on connections or transactions.
  - SQLite: "there can only be one writer at a time" ([wal.html](https://www.sqlite.org/wal.html) §2.2). Upgrading a read transaction to a write one "is not possible and the write statement will fail with SQLITE_BUSY" when another connection is writing ([lang_transaction.html](https://www.sqlite.org/lang_transaction.html) §2.1). With "always at least one active reader … the WAL file will grow without bound" (wal.html §6).
  - Spectio adds long writers (CH-030, CH-021, CH-023, CH-038) and long readers (logical backup, `VACUUM INTO` in synthesis l.270, SSE replay).
- **Problem:** "one process" is not "one connection". A threadpool of SQLAlchemy connections opening deferred transactions will hit `database is locked` under load. Multi-second write locks stall ingest. A nightly export holding a read transaction lets the WAL grow by a whole day's ingest.
- **Proposal:** in architecture §7.2:
  - one writer connection or queue, `BEGIN IMMEDIATE`, `busy_timeout`;
  - every maintenance write chunked (at most about 50 ms per transaction);
  - a scheduled `wal_checkpoint(TRUNCATE)` in reader gaps;
  - `auto_vacuum=INCREMENTAL` set when the database is created.

  Add a WAL-size check to admin §3.5.
- **Likelihood · impact:** high · medium (stalls, disk full).
- **Cheapest test** (2 h, spike S3): one writer at 5 k events/s plus a 10-minute reader, plotting WAL size; then a naive threadpool, counting `SQLITE_BUSY`.
- **Found by:** constraints-hunter (a) as CH-104
- **Status:** open

### CH-014 · major · Gate concurrency beyond `If-Match`: quorum, bulk decisions, whole change-set replacement, timeout races

- **Where:** api-and-data-model.md §4 (Writes), §5 (Gates), §7 (`gates`, `change_sets`, `decisions`); synthesis.md §5bis (Policy); checking-scenarios.md §3.
- **Evidence:**
  - "`ETag` / `If-Match` on gates, change sets and settings to prevent lost updates when two reviewers act at once" (api §4, l.77).
  - "`GET/PUT /gates/{id}/change-set`" and `POST /gates:bulk-decide` (api §5, l.96).
  - "optional quorum, timeout, default action on expiry, escalation" (synthesis §5bis, l.169).
- **Problem:**
  - A quorum of two approvals cannot work if every decision does compare-and-swap on the gate ETag: the second approver always gets a 412.
  - `PUT` of the whole change set makes two reviewers editing *different* items of a 10 000-item gate (checking §3, "Many") fight with 412s.
  - `bulk-decide` has no atomicity rule (all or nothing, or per gate).
  - The timeout loop and a human decision race.
  - The decision and its runner command must commit together (CH-007).
- **Proposal:**
  - api §7: `decisions` become votes. The policy resolves the gate state in one conditional update (`UPDATE gates … WHERE id=? AND state='open' AND etag=?`); the timeout uses the same compare-and-swap.
  - `PATCH /gates/{id}/change-set/items/{item}` with a version per item.
  - `bulk-decide` returns one result per gate and is atomic within each gate.
- **Likelihood · impact:** high · medium.
- **Cheapest test** (2 h): a property-based test with two concurrent clients against the S1 prototype.
- **Related:** SR-012 (R1) on decision verbs and resource names.
- **Found by:** constraints-hunter (a) as CH-110
- **Status:** open

### CH-015 · major · Personal mode "on a login node" conflicts with the local-disk rule

- **Where:** api-and-data-model.md §1 (Personal row); architecture-plugins-and-packaging.md §7.2–7.3; synthesis.md §7, §8.
- **Evidence:**
  - "`spectio serve` on a laptop or a login node" (api §1, l.18).
  - The server "refuses to start if the database file is on a network file system" (architecture §7.2, l.319).
  - The default data directory is under `~/.local/share/spectio` (architecture §7.2, l.314).
  - "WAL does not work over a network filesystem" ([wal.html](https://www.sqlite.org/wal.html) §1).
- **Problem:** on most HPC systems `$HOME` and project space are NFS, GPFS or Lustre, so the default data directory is refused. Node-local disks (`/tmp`, `/local`) are usually purged, and login aliases round-robin, so the next SSH may land on a node without the database. Docker Desktop bind mounts may also defeat WAL shared memory **[to be validated]**. EMBL's file systems are **[to be validated]**.
- **Proposal:** in api §1 and architecture §7.3: personal mode on a login node needs an explicit `--data-dir` on node-local, non-purged storage, pinned to one hostname. `spectio doctor` prints the file-system type (statfs) and the host pin. Otherwise, recommend a laptop, a VM or a service node, and name those in the refusal message.
- **Likelihood · impact:** high at HPC sites · medium (the documented mode does not work).
- **Cheapest test** (30 min with EMBL IT, spike S12): `stat -f -c %T` on `$HOME`, `/scratch`, `/tmp` and `$TMPDIR` on each login node; record the purge policies and how the alias rotates.
- **Related:** SR-031 (R1) on loopback trust on a shared login node.
- **Found by:** constraints-hunter (a) as CH-117
- **Status:** open

### CH-016 · major · Stopping at a gate through `ext.when` is proven only on synthetic pipelines

- **Where:** ui-spec.md §5.1; checking-scenarios.md §11.3; dev-environment-and-testing.md §3, §10.1.
- **Evidence:**
  - "nf-core modules honour `task.ext.when`, so the run ends after the gated stage" (ui-spec §5.1, l.189).
  - The verification used synthetic pipelines only: "The gate mechanisms hold on both engines" ([spike note](../research/spike-synthetic-pipelines-2026-10-26.md), finding 7, l.70).
  - The nf-core/rnaseq gate scenario is nightly on kind (dev-env §3).
- **Problem:** real nf-core pipelines combine outputs of skipped processes with `collect`, `join`, `ifEmpty` and `mix`, run completion hooks and summaries, and contain local or non-nf-core processes without `when:`. Any of these can make the "stopped" run fail or keep running. Gates are the MVP's focus.
- **Proposal:**
  - dev-env §3: move a local-executor stop-and-resume check on rnaseq and sarek (test profiles) into T1/T2, before the walking skeleton.
  - ui-spec §5.1: list the pipeline requirements, and show "gates unavailable" when the requirements check fails.
- **Likelihood · impact:** medium · high.
- **Cheapest test** (half a day, local Docker): rnaseq `-profile test,docker` with a generated config that stops after alignment, then `-resume` without it; count cached tasks and check the exit code. Repeat on sarek.
- **Related:** SR-011 (R1) on `--stage` against `ext.when`.
- **Found by:** constraints-hunter (b) as CH-211
- **Status:** open

### CH-017 · major · Live checks on the runner: one MultiQC call per file on login nodes

- **Where:** checking-scenarios.md §11.1, §11.2, §11.5; cli-and-shared-libraries.md §6; api-and-data-model.md §3.
- **Evidence:**
  - "**The runner is the only component that reads files.**" (checking §11.1, l.261).
  - "On a watched file, `multiqc:<module>.<column>` means 'run that MultiQC module on this one file'" (checking §11.2, l.308).
  - The base install is under 80 MB (cli §6, l.170).
  - api §3 lists the check provider as running on the "server" (l.64).
- **Problem:** 1 000 samples × 2 watched files = 2 000 MultiQC calls. At a few seconds of start-up and a few hundred MB each **[to be validated]**, that is about 2–3 CPU-hours on a login node that may cap per-user CPU **[site-dependent]**. MultiQC and polars are not in the runner's install. Login-node limits will throttle the checks or kill the runner. Where the check runtime is installed is the same open question as DEP-T-016.
- **Proposal:** in checking §11.2 and §11.5:
  - batch the files of one module per call;
  - above a threshold, run checks in a short-lived `sbatch` "check worker", or on the head's node;
  - define the check runtime as a separate environment with a pinned version.
- **Likelihood · impact:** high · medium.
- **Cheapest test** (1 h): time `multiqc -m star` on one `Log.final.out` from `tests/fixtures/megatests/rnaseq`, then on 100 files in one call; record RSS.
- **Related:** SR-003 (R1) owns the server-or-runner contradiction (api §3 against checking §11.1); this finding adds the cost on the runner.
- **Found by:** constraints-hunter (b) as CH-214
- **Status:** open

### CH-018 · major · Resumable streams have no sound cursor

- **Where:** api-and-data-model.md §5 (Events), §8; synthesis.md §4, §7.
- **Evidence:**
  - "The `seq` also serves as the SSE identifier for resuming after a disconnection." (synthesis §4, l.133)
  - "one multiplexed stream per tab" (synthesis §7, l.269).
  - `GET /events/stream` is "resumable with `Last-Event-ID`" (api §5, l.97).
  - Events are "ordered per run by `spectiosequence`" (api §8, l.252).
- **Problem:**
  - `seq` is per run, and a multiplexed stream has one `Last-Event-ID` string. Resuming a stream that covers many runs (Overview, Review queue, `/events` without `run=`) is undefined.
  - A global `bigserial` does not fix it: on Postgres, concurrent writers commit out of order, and a reader resuming from `id > N` silently skips rows with lower IDs that commit later.
  - Allocating per-run `seq` without a row lock gives duplicates or gaps.
  - Result: missed state changes and gate openings in UIs and integrations.
- **Proposal:** in api §8:
  1. allocate per-run `seq` under the run row lock (`UPDATE runs SET last_seq = last_seq + n RETURNING`), so commit order equals `seq` order within a run;
  2. resume multi-run streams by "snapshot then tail": on reconnect the client refetches the runs it shows through REST, then subscribes from now;
  3. or, if a global cursor is needed, publish rows only below a visibility fence (`pg_snapshot_xmin`). Say which.
- **Likelihood · impact:** certain on Postgres with more than one writer · high.
- **Cheapest test** (2 h, spike S4): two writers on Postgres 18 with `bigserial` and random commit delays, one poller on `id > last`; count missed rows.
- **Found by:** constraints-hunter (a) as CH-105
- **Status:** open

### CH-019 · major · Event order: `seq` is the server's arrival order, with no source sequence and no merge rule

- **Where:** synthesis.md §4 and §2ter.3; api-and-data-model.md §7–8.
- **Evidence:**
  - "`(run_id, seq, event_id ULID, ts, type, payload)` … The `seq` also serves as the SSE identifier" (synthesis §4, l.133).
  - "Upsert per `(run, task_id)`" (synthesis §2ter.3).
- **Problem:** each run has three producers: the engine bridge, the runner's scheduler observer (`squeue`/`sacct`, the Kubernetes watch) and the live checks. Retried batches arrive out of order, and spooled events (CH-001) arrive minutes late. With arrival-order upserts a task can go back from `SUCCEEDED` to `RUNNING`, and `sacct` can mark a task `COMPLETED` before the engine has decided on a retry.
- **Proposal:** in api §7–8:
  - every event carries `source` and `source_seq`, monotonic per producer and run;
  - projections apply a state lattice: terminal states never go back, a retry creates a new attempt, and only the engine sets task success while the scheduler adds `failure_class` and usage;
  - the arrival `seq` stays as the SSE cursor only (CH-018).
- **Likelihood · impact:** high · medium (wrong states, wrong gate triggers).
- **Cheapest test** (half a day, after T2): a property-based test that replays the golden streams shuffled and duplicated into a prototype reducer and asserts the final projection.
- **Found by:** constraints-hunter (b) as CH-210
- **Status:** open

### CH-020 · major · Postgres `LISTEN/NOTIFY` as the cross-process bus: payload cap, commit-time lock, poolers

- **Where:** architecture-plugins-and-packaging.md §2, §7.2, §7.6 (`sql` backend, advisory locks); admin-and-operations.md §3.5 (Pub/sub check).
- **Evidence:**
  - Live events across processes use "Postgres `LISTEN/NOTIFY`" (architecture §7.2, l.311); the `sql` backend workers "are woken by `LISTEN/NOTIFY`, and run scheduled tasks under a Postgres advisory lock" (§7.6, l.401).
  - Postgres: "In the default configuration it must be shorter than 8000 bytes"; "If this queue becomes full, transactions calling `NOTIFY` will fail at commit" ([NOTIFY, PG 18](https://www.postgresql.org/docs/18/sql-notify.html)).
  - PgBouncer in transaction pooling: LISTEN "Never", session-level advisory locks "Never" ([PgBouncer features](https://www.pgbouncer.org/features.html)).
  - Recall.ai reports that NOTIFY inside a transaction takes a global lock at commit that serialises commits ([Recall.ai](https://recall.ai/blog/postgres-listen-notify-does-not-scale)); DBOS disputes the scaling conclusion ([DBOS](https://dbos.dev/blog/postgres-listen-notify-scalability)). Behaviour on Postgres 18 is **[to be validated]**.
- **Problem:** a NOTIFY per ingest transaction at burst rates may serialise commits; event payloads above 8 kB fail; managed Postgres and CloudNativePG setups often put PgBouncer in transaction mode, which silently breaks listeners and the advisory-lock schedule claims.
- **Proposal:** in architecture §7.6:
  - NOTIFY is a coalesced wake-up only (run ID and max `seq`, at most every 100 ms, from one notifier, not in the ingest transaction); consumers read the tables;
  - listeners and advisory locks use a direct session connection (Helm value `database.directUrl`);
  - Health checks the pooler mode.
- **Likelihood · impact:** medium · high on team servers.
- **Cheapest test** (half a day, spike S6): 50 concurrent ingest writers on Postgres 18, NOTIFY in and out of the transaction, then through PgBouncer in transaction mode.
- **Related:** SR-015 (R1) on the two locking designs for schedules; DEP-T-012.
- **Found by:** constraints-hunter (a) as CH-107
- **Status:** open

### CH-021 · major · Restore failure modes while runs and engines are still live

- **Where:** admin-and-operations.md §4.3 (What a backup is not, Restore), §4.4 (Maintenance); api-and-data-model.md §5 (ingest).
- **Evidence:**
  - "Tokens. As in depictio, they are not restored, so the admin's session survives a restore." (admin §4.3, l.247)
  - "each table is wiped and replaced, with rollback if anything fails" (admin §4.3, l.277), then files are restored and Alembic migrates.
  - "Runners keep executing running jobs either way" (admin §4.4, l.306).
  - In the bundle, "migrations run automatically at start, after the pre-upgrade backup" (admin §4.3, l.294).
- **Problem:**
  1. If the maintenance flag lives in a restored table (`instance_settings`), restoring that table switches maintenance off mid-restore.
  2. Tokens are kept while `principals` are replaced, so principals created after the backup leave orphan tokens (foreign-key violation).
  3. Runners registered after the backup lose their row but keep their credential.
  4. Runs created after the backup are still running. Their events arrive for unknown run IDs, or for run states that were rewound, with no policy; after the restore the server's view and the runners' (heads in `squeue`, spooled events) differ and nothing reconciles them.
  5. One transaction across the whole database needs about twice the disk and hours on a large instance.
  6. A crash between the database commit, the file restore and the migration leaves a mixed state with no journal to resume from.
- **Proposal:** in admin §4.3:
  - restore into a **new** database (a new SQLite file, or a new Postgres database or schema); verify, migrate, then switch atomically (rename, or a `DATABASE_URL` pointer);
  - keep a restore journal file and the maintenance state outside the restored tables;
  - define what happens to tokens and runners created after the backup;
  - ingest returns `503` with `Retry-After` while restoring, and the bridges spool (CH-005);
  - after the switch, each runner sends a full inventory (heads, launch directories, unsent spool); runs the server does not know become "orphaned after restore" for an admin to adopt, and runs that are gone are archived.
- **Likelihood · impact:** medium · high.
- **Cheapest test** (1 day, spike S9): a seeded 5 GB database; `kill -9` at each restore step; check the server restarts consistent. A `restore-during-run` scenario (dev-env §5 has only `restore-during-idle`) once the walking skeleton exists.
- **Related:** SR-030 and SR-038 (R1) cover the token contradiction and the maintenance write table; journey (4) of round R3 (not run yet) will walk the same user story; DEP-T-011 and DEP-T-012 the test scope. This finding is about the mechanics.
- **Found by:** constraints-hunter (a) as CH-112, constraints-hunter (b) as CH-217
- **Status:** open

### CH-022 · major · Logical JSON Lines backups do not scale, need one snapshot, and have no RPO or RTO

- **Where:** admin-and-operations.md §4.3 (What a backup is, Kinds, Verify); synthesis.md §7.
- **Evidence:**
  - "`db/`: a **portable logical export**, one JSON Lines file per table in foreign-key order … A native `pg_dump` part can be added for speed on large instances." (admin §4.3, l.240)
  - "backup via `VACUUM INTO`" (synthesis §7, l.270): two methods in two specs.
  - "Pre-upgrade | full, taken automatically before `spectio db upgrade` (switch on by default)" (admin §4.3, l.258); "In the bundle, migrations run automatically at start, after the pre-upgrade backup" (l.294).
- **Problem:** at 2–4 GB of new data a day (CH-011), a nightly Python export of every table takes hours. For foreign-key-consistent output it must read from one snapshot: in SQLite that read transaction starves checkpoints (CH-013); in Postgres it holds back `xmin` and bloats the hot `tasks` and `runs` tables. The pre-upgrade backup blocks every bundle start for that long while runners buffer. No recovery point or recovery time objective is stated.
- **Proposal:** in admin §4.3:
  - the default same-engine backup is native: the SQLite online backup API in steps, or `VACUUM INTO` in a quiet window; `pg_dump -Fd -j` or CloudNativePG/barman for Postgres;
  - JSON Lines only for cross-engine migration and project export;
  - archived event payloads (CH-011) are copied as files, not rows;
  - an RPO and RTO per deployment;
  - the pre-upgrade backup is skipped when a verified backup is younger than N hours.
- **Likelihood · impact:** high on team servers · medium to high.
- **Cheapest test** (half a day, spike S10): export a seeded 10 GB database both ways while S1 ingest runs; measure time and WAL growth.
- **Related:** SR-050 (R1) on the CLI and admin backup contracts.
- **Found by:** constraints-hunter (a) as CH-113
- **Status:** open

### CH-023 · major · Schema migrations with live traffic: Helm hook against old pods, readiness "at head", SQLite table copies

- **Where:** admin-and-operations.md §3.5 (`/health/ready`), §4.3 (Schema migrations); architecture-plugins-and-packaging.md §7.5.
- **Evidence:**
  - "`/health/ready`: database reachable and migrations at head" (admin §3.5, l.191).
  - "migrate Job as a Helm pre-install / pre-upgrade hook" (architecture §7.5, l.365).
  - "Alembic with `render_as_batch` (SQLite)" (admin §4.3, l.293). Alembic batch mode: "a new version of this table is created … data is copied from the old table to the new table … the old table is dropped and the new one renamed" ([Alembic batch](https://alembic.sqlalchemy.org/en/latest/batch.html)).
- **Problem:** on Kubernetes the hook migrates while the old pods still serve. Those pods then see a revision newer than their own head; if readiness means "at head", **every old pod becomes unready at once**, which is a full outage during the rollout. No expand/contract rule protects old code from the new schema. In SQLite, any batch migration of `events` copies gigabytes under the write lock and needs twice the disk while runners buffer. (The in-place upgrade test is DEP-T-011.)
- **Proposal:** in admin §4.3:
  - expand/contract: release N only adds; destructive steps come in N+1;
  - readiness is "the database revision is within my compatible range";
  - no table-copy migrations on `events`, `tasks` or `attempts` (add tables or nullable columns instead);
  - a migration-time budget, checked in CI on a seeded database.
- **Likelihood · impact:** high · high.
- **Cheapest test** (1 day, spike S11): an Alembic migration adding a column and an index on a 10 GB `events` table (SQLite batch, Postgres); `helm upgrade` on kind while old pods serve.
- **Found by:** constraints-hunter (a) as CH-114
- **Status:** open

### CH-024 · major · Kubernetes: Kueue API versions, the one-hour lifetime of Events, the head pod's RBAC, Kueue and Nextflow Pods

- **Where:** schedulers-and-monitoring.md §4 and §11; dev-environment-and-testing.md §1, §4.2.
- **Evidence:**
  - The spec hard-codes "`/apis/visibility.kueue.x-k8s.io/v1beta2/namespac…`" (schedulers §4, l.163).
  - Kueue v0.20.0 "no longer serves the v1beta1 API version (`kueue.x-k8s.io/v1beta1`)" ([release mirror](https://newreleases.io/project/github/kubernetes-sigs/kueue/release/v0.20.0)). Pending workloads default to `limit` 1 000 ([Kueue docs](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/)).
  - kube-apiserver `--event-ttl` "Default: 1h0m0s" ([reference](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver/)).
  - Nextflow builds Jobs from the pod metadata (`buildAsJob`, `nf-k8s/.../PodSpecBuilder.groovy:597-616`) and uses Jobs by default (`K8sConfig.groovy:224`, `114f1fe`).
- **Problem:**
  - A runner that hard-codes one Kueue version breaks across a Kueue upgrade. Which Kueue version introduced v1beta2 is **[to be validated]**.
  - Events cannot be selected by the object's labels **[to be validated]**, so the watch on "Events for those objects" (§4) must be namespace-wide.
  - A runner offline for more than an hour loses `FailedScheduling` and OOM reasons, while `k8s.cleanup` has already deleted the successful pods.
  - On Nextflow 25.10 (Pods, not Jobs), Kueue sees tasks only through its opt-in pod integration **[to be validated]**.
- **Proposal:** in schedulers §4:
  - discover API versions through `/apis` before use;
  - watch Events namespace-wide and filter by `involvedObject`;
  - keep the last terminal state of each pod in the runner;
  - write the queue-name label through the `k8s.pod` labels Spectio generates.

  Add the Kueue version range to dev-env §1.
- **Likelihood · impact:** medium · medium.
- **Cheapest test** (1 day, folded into T4): kind with Kueue v0.20 and an older minor; `--event-ttl=5m`; nf-toy on 26.10 and 25.10 with the queue label; the runner offline for 10 minutes.
- **Related:** SR-051 (R1) owns the head pod's RBAC, which reviewer (b) also raised.
- **Found by:** constraints-hunter (b) as CH-215
- **Status:** open

### CH-025 · major · Apptainer, the usual HPC container runtime, is untested; the whole matrix uses Docker

- **Where:** dev-environment-and-testing.md §1, §3, §5, §10.2; schedulers-and-monitoring.md §3.5, §7.
- **Evidence:**
  - "Apptainer | optional, later" (dev-env §1, l.54).
  - Scenarios and corpus entries use Docker, e.g. "`-profile test,docker`" (dev-env l.90). The alpha targets EMBL HPC (dev-env §14).
  - schedulers §7 already watches "Apptainer / Singularity cache size and `NXF_SINGULARITY_CACHEDIR` presence" (l.221), and synthesis requires "user namespaces" for Apptainer delivery (l.364).
- **Problem:** pulling Singularity images on the head (CH-001), `NXF_SINGULARITY_CACHEDIR` quotas, the `apptainer` failure classes and user-namespace requirements never reach a test.
- **Proposal:**
  - dev-env §1 and §5: add Apptainer to the toolchain and an `engine × runtime {docker, apptainer}` axis on `slurm-site` nightly.
  - schedulers §3.5: add the Apptainer failure classes.
- **Likelihood · impact:** high · medium.
- **Cheapest test** (half a day): Apptainer inside the sind submitter node, running nf-toy `-profile singularity`. Whether this works in nested containers is itself **[to be validated]**.
- **Found by:** constraints-hunter (b) as CH-218
- **Status:** open

### CH-026 · major · 50 concurrent runs under one account break SLURM per-user limits; the §0.2 sentence overstates

- **Where:** schedulers-and-monitoring.md §0.2 and §3.2.
- **Evidence:**
  - "The load on `slurmctld` and `slurmdbd` therefore does not grow with the number of runs" (schedulers §0.2, l.21), next to "Spectio's `squeue` adds one call per minute per user on top of the engine's" (§3.2, l.84).
  - Each Nextflow head runs `squeue` every minute and each Snakemake head runs `sacct` every 40–180 s (§1). The Nextflow grid default is `queueSize` 100 (`AbstractGridExecutor.groovy:68`).
  - Slurm `rl_enable` is "per-user RPC rate-limiting", with `rl_bucket_size` 30 and `rl_refill_rate` 2 per `rl_refill_period` of 1 s; the default `MaxJobCount` is 10 000 (`slurm.conf`, 26.05).
- **Problem:** 50 runs × `queueSize` 100 = 5 000 queued jobs per user: above common `MaxSubmitJobs` association limits **[site-dependent]** and half the default cluster-wide `MaxJobCount`. At 2 RPC/s, 100 000 non-array `sbatch` calls take about 14 h, and all the `squeue` calls from 50 heads plus Spectio's share one token bucket. Submissions are rejected with `QOSMaxSubmitJobPerUserLimit` and status commands fail. A polling failure is only a warning (`AbstractGridExecutor.groovy:323-337`); how Nextflow treats a rejected `sbatch` is **[to be validated]** (likely retries, then a failed run).
- **Proposal:** in schedulers §3.2, a per-(environment, account) budget that Spectio enforces:
  - an admission limit on concurrent runs (ties to UX-120 and UX-126);
  - generated `executor.queueSize`, `submitRateLimit`, `queueStatInterval` and `onlyJobState`, apportioned across active runs;
  - job arrays preferred.

  Correct §0.2: the engines' load grows with runs; Spectio's own does not. Which account a launch runs under is SR-014.
- **Likelihood · impact:** high at 50 runs · high.
- **Cheapest test** (half a day, sind `slurm-site`): `MaxSubmitJobs=50` on the association and `rl_enable`; 5 nf-toy `fanout=200` and 5 smk-toy runs at once; record rejections and engine behaviour.
- **Found by:** constraints-hunter (b) as CH-206
- **Status:** open

### CH-027 · major · `squeue` and `sacct --json` are heavy, and their schema changes with each Slurm version on the CLI path too

- **Where:** schedulers-and-monitoring.md §3.2, §3.3 and §8 (`raw_ref`).
- **Evidence:**
  - `squeue` man page (26.05): `--json, --json=list, --json=<data_parser>` … "All information is dumped, even if it would normally not be … most filtering arguments are still used."
  - The REST release notes say the data_parser plugins "are also used to generate JSON or YAML output for multiple CLI commands", and that 26.05 carries v0.0.42–v0.0.45.
  - schedulers §3.3 negotiates the version only for slurmrestd.
- **Problem:** at about 5 KB per job record (estimate), 5 000 active jobs give 25 MB per 60 s poll, about 36 GB a day parsed on a login node. `sacct` for a 100 000-task run, including the batch and extern steps that carry max RSS, is about 300 000 records, roughly 1 GB of JSON. Storing `raw_ref` for every job adds 100 000 blobs per run. A site upgrade changes field shapes and silently breaks parsing. Pending arrays appear as one `123_[5-1000]` record to expand.
- **Proposal:**
  - schedulers §3.3: choose the version with `--json=list` and pin it with `--json=<data_parser>`; keep golden fixtures per parser version (`slurm-versions` profile).
  - schedulers §3.2: the 60 s poll uses the text format (`-h -o '%i|%T|%r|%S|%P|%N'`, about 60 B per job); JSON only for detail views. Use slurmrestd incremental queries where available **[to be validated]**.
  - schedulers §8: keep `raw_ref` only for failed jobs.
- **Likelihood · impact:** high · medium.
- **Cheapest test** (2 h, sind): 5 000 held jobs, bytes and time of `squeue --me --json` against the text format; `sacct --json -j <1000-element array>` with steps; diff the JSON keys between 25.11 and 26.05.
- **Found by:** constraints-hunter (b) as CH-207
- **Status:** open

### CH-028 · major · Hosting the runner on login nodes: `scrontab` does not run there, systemd kills supervised heads, duplicate runners

- **Where:** schedulers-and-monitoring.md §6 and §3.1 (head as a supervised process).
- **Evidence:**
  - "**Login node, cron watchdog** | `scrontab` or `crontab` restarts the runner if its PID is gone" (schedulers §6, l.209).
  - `scrontab` "can define a number of recurring **batch jobs**" (scrontab man page, 26.05): they run on compute nodes and cannot see a login-node PID.
  - systemd's `KillMode=` "Defaults to control-group": every process of the unit is killed when it stops ([systemd.kill](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)).
- **Problem:** restarting or upgrading a `systemd --user` runner kills every head it supervises as a child process. Login nodes behind a round-robin alias let two runners start for the same account (cron on each node, or a user reconnecting), and both claim commands. Per-user CPU and memory caps on login nodes **[site-dependent]** also apply to the runner's own work (CH-017).
- **Proposal:** in schedulers §6:
  - drop `scrontab`;
  - heads launched by a local launcher use `systemd-run --user --scope` or `setsid`, outside the runner's cgroup; document a `KillMode=process` unit;
  - one active runner per (environment, account), held by a server-side lease with a fencing token; a second instance stays on standby.
- **Likelihood · impact:** high · high.
- **Cheapest test** (2 h, container with systemd): a `systemd --user` unit supervising `sleep 600` as a "head", then `systemctl --user restart`; then two runner stubs against one lease.
- **Found by:** constraints-hunter (b) as CH-208
- **Status:** open

### CH-029 · major · Head job sizing and the walltime limit

- **Where:** schedulers-and-monitoring.md §3.1, §3.5.
- **Evidence:**
  - "`sbatch` with few resources (e.g. 2 CPUs, 4 GB) and a long walltime" (schedulers §3.1, l.64); "Twelve hours before the limit it warns, so the user can let it end and resume" (l.66).
  - `KillWait` is "The interval … between the SIGTERM and SIGKILL signals upon reaching its time limit … default value is 30 seconds" (`slurm.conf`, 26.05).
- **Problem:** a Nextflow JVM tracking 100 000 tasks, or a Snakemake DAG of 100 000 jobs, plus the bridge buffers, likely needs more than 4 GB **[to be validated]**. An OOM kill of the head ends without `onFlowComplete`. At the walltime limit, cancelling thousands of tasks within 30 s may not finish, leaving orphan jobs **[to be validated]**. A warning alone does not stop a run from being killed overnight.
- **Proposal:** in schedulers §3.1:
  - size the head from the expected task count (a workflow profile), with `NXF_OPTS -Xmx` at about 75 % of the head's memory;
  - the runner performs a controlled stop well before the limit and, if policy allows, resubmits the head with `-resume`;
  - head OOM and head walltime become their own failure classes (§3.5).
- **Likelihood · impact:** medium · high.
- **Cheapest test** (2 h): `fanout_stress` head RSS and heap; `snakemake -n` on a generated 100 000-job DAG (RSS, DAG-build time); `scancel` time for 1 000 running jobs on sind.
- **Found by:** constraints-hunter (b) as CH-213
- **Status:** open

### CH-030 · major · Moving a run between projects rewrites millions of rows, and contradicts the append-only log

- **Where:** api-and-data-model.md §0 item 3, §4 ("Ownership is data, not path"), §5 (`PATCH /runs/{id}`), §7, §8 (`spectioproject`).
- **Evidence:**
  - "Every tenant table has `project_id`" (api §7, l.170).
  - "moving a run between projects or adding users never changes URLs" (api §4, l.75).
  - Events are an "append-only log" (api §7, l.196) and carry the `spectioproject` extension (api §8, l.240).
- **Problem:** measured: 5.9–6.6 s of exclusive SQLite write lock for one run's 500 000 events, before tasks, attempts, `scheduler_jobs`, `check_results` and artifacts. Either events are rewritten, which breaks "append-only" and makes webhooks already sent disagree with history; or they keep the old project, and members of the old project can still read them through `/events`.
- **Proposal:**
  - api §7: `project_id` is authoritative only on root objects (runs, workflows, environments, webhooks). Child tables (tasks, attempts, events, `check_results`, `scheduler_jobs`, artifacts) get it through `run_id`, or keep a copy never used for authorisation.
  - The move is a `202 Operation`, done in chunks.
  - State what past deliveries mean after a move. The tenancy angle goes to R5.
- **Likelihood · impact:** medium (moves are rare) · high (a stall or a tenancy leak).
- **Cheapest test** (1 h): already measured on SQLite; repeat on Postgres with 10 M rows.
- **Found by:** constraints-hunter (a) as CH-111
- **Status:** open

---

## Minors

### CH-031 · minor · Clock skew has no rule: engine-host time, server time, ULIDs, freshness checks

- **Where:** api-and-data-model.md §4, §7 (`events`), §8; architecture §7.3 (`spectio doctor`); admin-and-operations.md §3.2 (heartbeats); schedulers-and-monitoring.md §7 ("head silent").
- **Evidence:** "`spectio doctor` checks … clock skew" (architecture §7.3, l.343), with no tolerance. Events carry `time`, and IDs are ULIDs that embed the clock of the host that mints them (api §4).
- **Problem:** login nodes, head jobs on compute nodes and the server drift apart. Ordering by ULID or `time` across hosts, durations from mixed clocks, the HMAC timestamp window and gate timeouts then disagree. Comparing engine `ts` with server time gives false "head silent" or "runner offline" states.
- **Proposal:** in api §8: store `engine_time` and `received_at`; order only by `seq` (CH-018, CH-019); compute durations from one clock source; freshness and timeouts always use server receive time. The runner sends its clock with each heartbeat; the server records the offset and warns above 5 s (Health → Runners, and `spectio doctor`).
- **Cheapest test:** unit tests only.
- **Found by:** constraints-hunter (a) as CH-120, constraints-hunter (b) as CH-223
- **Status:** open

### CH-032 · minor · Runner channel in practice: proxies, idle timeouts, the JVM and internal CAs

- **Where:** api §5 (`WS /runners/{id}/channel`, l.92); architecture §7.6 ("long poll or SSE", l.385); admin §3.2 ("pulled", l.146).
- **Problem:** whichever transport SR-002 picks, site proxies close idle connections and some do not upgrade WebSockets. The JVM ignores `https_proxy` unless the plugin maps it **[to be validated]**. An institute CA is often missing from Java's trust store and from certifi.
- **Proposal:** in architecture §7.7 (SR-002): HTTPS long poll (≤ 55 s) with heartbeats. The bridges and the runner read the proxy variables and a configurable CA bundle; `spectio doctor` checks both.
- **Likelihood · impact:** medium · medium.
- **Cheapest test:** squid with a 60 s idle timeout in front of a stub server.
- **Related:** SR-002 (R1).
- **Found by:** constraints-hunter (b) as CH-219
- **Status:** open

### CH-033 · minor · Restart storms: false "offline" runners and simultaneous replays

- **Where:** admin-and-operations.md §3.2; api-and-data-model.md §8 (`spectio.runner.offline`); schedulers-and-monitoring.md §7 (events buffered locally).
- **Evidence:** "A runner is marked offline after 3 missed heartbeats" (admin §3.2, l.145), with heartbeats every 30 s.
- **Problem:** after a server outage longer than 90 s, the first sweep marks every runner offline and sends `runner.offline` webhooks and notifications. Then every runner and bridge replays its buffer at once: the worst burst of CH-012.
- **Proposal:** in admin §3.2: no offline transitions until 3 heartbeat intervals after the server boots; reconnects with jitter; admission control per runner (`429`, `Retry-After`) and a rate cap on replays.
- **Cheapest test:** in the S2 harness, stop the server for 5 minutes with 50 simulated runs; measure catch-up time and spurious events.
- **Found by:** constraints-hunter (a) as CH-121
- **Status:** open

### CH-034 · minor · Licences of server dependencies, scheduler integrations and copied code are not tracked

- **Where:** architecture §7.3 (extras), §7.4 (image), §8 (Redis); depictio-ecosystem-reuse.md §1 (the Copy rows); schedulers-and-monitoring.md §5, §9.
- **Evidence:**
  - Spectio is MIT (synthesis §11 item 4, l.408).
  - `psycopg` 3.3.6 is `LGPL-3.0-only` (PyPI, checked 2026-10-26) and sits in `spectio[postgres]` (architecture §7.3, l.333) and the image.
  - `paho-mqtt` 2.1.0 is "EPL-2.0 OR BSD-3-Clause" (PyPI). Redis Open Source 8 is "RSALv2 or SSPLv1 or AGPLv3" ([redis.io](https://redis.io/legal/licenses/)).
  - pyslurm is GPL-2.0 (`COPYING.txt`, PySlurm/pyslurm main, 2026-10-26); flux-core is LGPL-3.0 (`LICENSE`, master, 2026-10-26).
  - depictio code is marked "**Copy**" (depictio-ecosystem-reuse l.43-57), but depictio's licence is not recorded anywhere **[to be validated]**. sind (LGPL-3.0, per dev-env §0.2) is used only as a test tool.
- **Problem:** no licence allow-list, no notices in the wheel or image, no record of what was copied under which licence.
- **Proposal:**
  - architecture §7.4: a CI licence scan with an allow-list, and `THIRD_PARTY_NOTICES` in the wheel and the image. Consider `asyncpg` (Apache-2.0) if LGPL in the image is a concern. Images never bundle Redis 8; say so.
  - schedulers §5: plugins call CLIs or REST and never link pyslurm; Flux bindings stay an optional, dynamically imported dependency of a separate plugin.
  - depictio-ecosystem-reuse §1: record depictio's licence and the attribution for copied code.
- **Cheapest test:** a 15-minute `pip-licenses` run over the planned dependency set.
- **Found by:** constraints-hunter (a) as CH-123, constraints-hunter (b) as CH-225
- **Status:** open

### CH-035 · minor · A Provenance Run Crate of 100 000 tasks has no size budget

- **Where:** synthesis.md §7quinquies; api-and-data-model.md §5 (Provenance), §10; admin-and-operations.md §3.1 (`rocrate.export`).
- **Evidence:** "the **Provenance Run Crate** when step-level detail is available (it is: Spectio stores tasks)" (synthesis l.313).
- **Problem:** one action per task gives hundreds of MB of JSON-LD (estimate), built in a worker, that consumers such as LabID must import. In the bundle this runs in the API process (CH-012).
- **Proposal:** in api §10 (owner), linked from synthesis §7quinquies: step level up to N tasks, aggregated per process above that; a streaming writer and a stated size budget.
- **Cheapest test** (2 h): generate a crate for 100 000 synthetic tasks with ro-crate-py; measure size, memory and time **[to be validated]**.
- **Found by:** constraints-hunter (a) as CH-124
- **Status:** open

### CH-036 · minor · Outbox: ordering against 24 h retries, one queue for every subscriber, storms of task events

- **Where:** api-and-data-model.md §8; architecture §3.5, §7.6 (bridges).
- **Evidence:** "at least once … ordered per run by `spectiosequence` … exponential retry for 24 h" (api §8, l.252); sinks, notifiers and bridges use "the same outbox as webhooks" (architecture §3.5).
- **Problem:** strict order plus retries means one failing endpoint blocks that run's later events for up to 24 h (head-of-line blocking); otherwise order is broken, and the spec does not choose. A slow sink (the depictio hand-off) delays webhooks. With `errorStrategy 'ignore'`, a run with 10 000 `task.failed` creates 10 000 deliveries per subscriber.
- **Proposal:** in api §8: each subscriber has its own cursor over the event log; ordered subscribers block only per (subscriber, run); a subscriber pauses after N consecutive failures; delivery rows only for failed attempts; noteworthy task events coalesced per run per minute.
- **Cheapest test:** in the S1 harness, a failing endpoint plus 10 000 failures; measure table growth and lag.
- **Found by:** constraints-hunter (a) as CH-119
- **Status:** open

### CH-037 · minor · A Lustre stall blocks the runner's event loop, and the server marks it offline

- **Where:** admin-and-operations.md §3.2 (offline after 3 missed 30 s heartbeats); checking-scenarios.md §11.1.
- **Problem:** synchronous file I/O (live checks, listings, log tails) on a hung metadata server freezes asyncio; heartbeats stop and the server marks the runner offline.
- **Proposal:** all file-system work in a bounded thread pool with timeouts; heartbeats from a dedicated thread.
- **Cheapest test:** a FUSE file system that sleeps 120 s on `stat`.
- **Found by:** constraints-hunter (b) as CH-224
- **Status:** open

### CH-038 · minor · Engine head logs will flood the log ring buffer, which shares the database

- **Where:** admin-and-operations.md §3.4.
- **Evidence:** "bounded ring-buffer table (`log_records`) … capped by size (default 256 MB)" (admin §3.4, l.158); sources include "`engine:<run>`: the head-process log of a run, streamed by the runner" (l.163).
- **Problem:** `.nextflow.log` grows by about 1–3 KB per task at debug level, so a 100 000-task run produces 100–300 MB (estimate, **[to be validated in `fanout_stress`]**) and evicts every other source. Log inserts and pruning deletes compete with ingest for the single SQLite writer, and delete churn grows the file unless incremental vacuum is on. A database log handler on the request path amplifies load when things go wrong.
- **Proposal:** in admin §3.4: engine head logs stay on the runner and are fetched with range requests, like task logs; only WARN and above are streamed. The ring buffer keeps `api`, `worker`, `runner` and `plugin` logs with a cap per source, in a separate SQLite file (`ATTACH`), written in batches off the request path, with a drop counter.
- **Cheapest test:** in S1, write 1 GB of logs during ingest and compare ingest p99; measure `.nextflow.log` after `fanout_stress`.
- **Found by:** constraints-hunter (a) as CH-118, constraints-hunter (b) as CH-221
- **Status:** open

### CH-039 · minor · Search across runs, tasks and samples has no portable implementation

- **Where:** api-and-data-model.md §5 (Search), §7.
- **Evidence:** "`GET /search?q=` (runs, workflows, tasks, samples by external ref)" (api §5, l.100); "no SQLite-only features" (api §7, l.170).
- **Problem:** tasks reach 10⁷–10⁸ rows a year. `LIKE '%q%'` does not scale, and full-text search is engine-specific (FTS5 in SQLite, `tsvector` or `pg_trgm` in Postgres), which breaks the portability rule unless it sits behind an interface with two implementations.
- **Proposal:** in api §5 and §7: exact and prefix matches on indexed keys only (IDs, external refs, names, tags); task search scoped to one run; an optional FTS adapter per engine allowed by name.
- **Cheapest test:** in S1, prefix search over 10 M seeded task rows on both engines.
- **Found by:** constraints-hunter (a) as CH-122
- **Status:** open

### CH-040 · minor · Idempotency keys have no storage, scope, retention or race rule

- **Where:** api-and-data-model.md §4 (Writes), §7 (`runs.idempotency_key`, `decisions.idempotency_key`).
- **Evidence:** "`Idempotency-Key` on every POST that creates or triggers something" (api §4, l.77); only two tables have the column (api §7, l.222 and the `decisions` row).
- **Problem:** which other POSTs are covered, and per which principal? How long are keys kept, and what happens when the body differs? Two concurrent requests with the same key both pass a "check then insert".
- **Proposal:** api §7: `idempotency_keys(principal_id, key, request_hash, response_ref, expires_at)` with `unique (principal_id, key)`; insert first and return the stored response; `422` on a body mismatch (the CLI already maps this conflict to exit code 5, cli l.79); 24 h retention.
- **Cheapest test:** a unit test with two concurrent requests.
- **Found by:** constraints-hunter (a) as CH-125
- **Status:** open

---

## Cited, not repeated

These R4 findings restate an R1 finding. Their constraint content is folded into the R1 finding's triage, not raised again here.

| R4 original | R1 finding | Note |
|---|---|---|
| CH-116 · two tables named `tasks` | SR-005 (blocker) | Same rename proposal (`background_tasks`, prefix `bgt_`). |
| CH-205 · which runner, under which Unix account, runs whose runs | SR-014 (major) | Same proposal (one runner per environment × account, or a declared service account). CH-026 and CH-028 depend on its outcome. |
| CH-220 · `squeue --name 'spectio-*'` matches nothing | SR-037 (major) | Same evidence and fix (client-side prefix filter, capture the "SLURM run ID" log line). |
| CH-222 · `jobcomp/kafka` consumed by a bridge that only publishes | SR-035 (major) | Same direction and phase conflict; the tenant filter goes to R5. |

## Questions for Thomas

1. **Event path at sites that block compute-node egress (CH-001).** Should the spool in the launch directory, forwarded by the runner, be the *default* bridge path (with direct posting as an optimisation), and should the runner prepare everything network-dependent on the login node so the head runs offline? This decides the shape of both bridges before T2 ends.
2. **Minimum engine versions (CH-006, CH-009).** May the docs state Nextflow ≥ 25.04 (or ≥ 25.10, the oldest tested) and Snakemake ≥ 9.0 as the supported floor? Older site modules would then be unsupported.
3. **Scale targets (CH-004).** Are "one run of 100 000 tasks" and "50 concurrent runs" targets for the 0.2 alpha, or for 1.0? The answer decides whether the projector split (CH-012), the SSE coalescing (CH-008) and native backups (CH-022) are in the walking skeleton or later.
4. **EMBL probe (CH-001, CH-015, CH-028, CH-026).** Can you run, or ask EMBL IT to run, the one-hour cluster probe (spike 1 below): egress from an `sbatch` job, file-system types and purge on login nodes, lingering, cron, cgroup caps, file locks in scratch, `MaxSubmitJobs`? It needs an EMBL account and cannot be done from here.
5. **Raw event payloads (CH-011).** Is it acceptable to archive raw payloads to the file store once a run is terminal, and to stop `nf-spectio` from sending `script` and `env` on every event? This changes synthesis §2ter item 4 ("keep the raw JSON").
6. **Backup format (CH-022).** Should the default same-engine backup become native (SQLite backup API, `pg_dump`), keeping JSON Lines only for SQLite → Postgres migration and project export? This departs from depictio's JSON backup model, which admin §4.3 copies.

## Proposed spikes

One ranked list, merged from both reviewers, ordered by risk removed per hour (likelihood × impact ÷ cost). "S" numbers are reviewer (a)'s names, kept for reference from the findings.

| # | Spike | Settles | Cost | Needs |
|---|---|---|---|---|
| 1 | **EMBL cluster probe.** From an `sbatch` job: HTTPS to an external endpoint, `registry.nextflow.io`, `quay.io`, GitHub, with and without the proxy. On each login node: `stat -f -c %T` on `$HOME`, `/scratch`, `/tmp`, `$TMPDIR`; purge policy; alias rotation; lingering, `KillUserProcesses`, cron, cgroup CPU and memory caps, `ulimit -u`; file locks in scratch; association `MaxSubmitJobs` (includes S12) | CH-001, CH-015, CH-026, CH-028 | 1–1.5 h | an EMBL account (question 4) |
| 2 | **`nf-spectio` failure modes and volume** (extends T2). Throwing and sleeping hooks; a 10-minute server outage; a 25.10 build on 26.10 and on 25.04; a `requires` mismatch; offline plugins; bytes and events per task, with and without `script`/`env` | CH-006, CH-005, CH-011 | ½ day | T2 |
| 3 | **S1/S2 ingest and SSE load harness.** Seed generator plus a 300-line FastAPI prototype (append, projector, SSE) on SQLite and Postgres 18. Load: 50 synthetic runs, one 100 000-task burst, a 5-minute server outage. Measure ingest p99, SSE lag, `GET /runs` p95 at 10 000 runs, `GET /runs/{id}/tasks` p95 at 100 000 tasks, bytes per event. Baseline from this round: 27.7 k events/s per stream, 733 MB per 500 000 events | CH-004, CH-011, CH-012, CH-033, CH-036, CH-038, CH-039 | 1–2 days | nothing (T2 payloads improve it) |
| 4 | **S4 cursor-gap test.** Two writers with `bigserial` on Postgres 18 and a poller on `id > last` | CH-018 | 2 h | docker `postgres:18` |
| 5 | **Gate stop on real nf-core pipelines.** rnaseq and sarek test profiles with a generated `ext.when` stop, then `-resume` | CH-016 | ½ day | local Docker |
| 6 | **Launch and relaunch races (S7, S8).** `kill -9` the runner between `sbatch` and its acknowledgement; resume 0, 1 and 5 s after the final event on nf-toy and smk-toy; `kill -9` the head then resume; a `nolock` NFS launch directory; Snakemake after SIGKILL | CH-007, CH-003 | 1 day | T1, T3 (sind) |
| 7 | **S3 SQLite lock discipline.** A 10-minute reader during ingest (WAL growth); a naive threadpool (`SQLITE_BUSY` count) | CH-013 | 2 h | nothing |
| 8 | **Licence scan** of the planned dependencies with `pip-licenses` | CH-034 | 15 min | nothing |
| 9 | **Snakemake environment isolation.** A runner without Snakemake; pixi-pinned 9.27.1; a read-only environment with the logger on `PYTHONPATH`; interface 1.2.5 and 2.1.0 | CH-009 | ½ day | nothing |
| 10 | **S5 browser SSE.** Seven tabs on `http://127.0.0.1`; render a 100 000-event burst in a Vite and TanStack prototype | CH-008 | 2 h | spike 3 |
| 11 | **Ordering reducer.** Shuffled and duplicated golden streams into a property-tested projection | CH-019 | ½ day | T2 |
| 12 | **SLURM scale and limits on sind.** 5 000 held jobs: `squeue --json` against the text format; `sacct --json` for a 1 000-element array; a JSON key diff between 25.11 and 26.05; `MaxSubmitJobs=50` with `rl_enable` and 10 concurrent runs | CH-026, CH-027 | 1–1.5 days | T3 (sind, in GitHub Actions for cgroup v2) |
| 13 | **Head sizing.** `fanout_stress` head RSS, heap and `.nextflow.log` size; `snakemake -n` on a 100 000-job DAG; `scancel` time for 1 000 jobs on sind | CH-029, CH-038 | 2 h | T3 for the last part |
| 14 | **systemd and leases.** `systemctl --user restart` with a supervised child; two runner stubs on one lease | CH-028 | 2 h | a container with systemd |
| 15 | **Live-check cost.** `multiqc -m star` on 1 file against 100 files from the megatest fixtures | CH-017 | 1 h | nothing |
| 16 | **Purge after a gate.** Delete half the stage-A work directories after a stop, `-resume`, compare counts | CH-010 | 1 h | T1 |
| 17 | **Golden-fixture compatibility replay** across bridge versions | CH-002 | 2 h | T2 |
| 18 | **S9/S10 backup and restore at 10 GB.** JSON Lines against native backup during ingest; `kill -9` at each restore step | CH-021, CH-022 | 1 day | spike 3 seed |
| 19 | **S11 migrations.** Batch migration on a 10 GB `events` table; `helm upgrade` on kind with old pods serving | CH-023 (and DEP-T-011) | 1 day | T4 (kind), spike 3 seed |
| 20 | **S6 LISTEN/NOTIFY.** 50 writers on Postgres 18, NOTIFY in and out of the transaction, through PgBouncer in transaction mode | CH-020 (and DEP-T-012) | ½ day | docker |
| 21 | **Kubernetes and Kueue versions** (in T4). Kueue v0.20 and an older minor; `/apis` discovery; `--event-ttl=5m`; runner offline; Nextflow 25.10 Pods against 26.10 Jobs with the queue label | CH-024 | 1 day | T4 |
| 22 | **Apptainer in sind**, nf-toy `-profile singularity` | CH-025 | ½ day | T3 |
| 23 | **Project move on Postgres** with 10 M rows | CH-030 | 1 h | spike 3 seed |
| 24 | **RO-Crate size** at 100 000 tasks with ro-crate-py | CH-035 | 2 h | nothing |
| 25 | **Restore during a run** (scenario `restore-during-run`) | CH-021, CH-002 | ½ day | the walking skeleton |

Unit-level checks with no spike: CH-014 (property test against the spike 3 prototype, 2 h), CH-031, CH-040 (unit tests), CH-032 (squid stub), CH-037 (FUSE stub).

Cited, not repeated: DEP-T-011 (in-place upgrade test), DEP-T-012 (Postgres-only paths untested), DEP-T-016 (check runtime on runners), DEP-T-018 (Python and OS matrix), DEP-T-029 (metrics contract), UX-113 (relaunch estimate), UX-120 and UX-126 (queueing and quotas behind the admission control of CH-012, CH-026 and CH-033).
