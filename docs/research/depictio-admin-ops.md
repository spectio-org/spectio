# depictio — administration and operations audit

Source: depictio checkout `scratchpad/dep` at v1.19.2 (`0d1aa0a`, 2026-10-23). Paths are relative to `dep/depictio/` unless they start with `docs/`, `deploy/`, `scripts/` or `docker-compose/` (repository root). "Inferred" marks anything not read directly in code.

## 1. Admin app

### 1.1 Shell and access
- **Entry point.** `viewer/src/admin/AdminApp.tsx`, route `/admin`, with deep links `/admin/<tab>` and `/admin/<pane>`. The URL codec is `adminUrl` / `parseAdminUrl` in `depictio-react-core`, and Ingestion filters live in the query string.
- **URL behaviour.** Switching tab is a `pushState` and changing a filter is a `replaceState` (l.130–140). The last tab is remembered in `localStorage` (`admin-active-tab`).
- **Navigation groups** (`NAV_GROUPS`, l.70–103), described in the code as "the four questions an admin comes with":
  - **People:** Users, Groups.
  - **Content:** Projects, Dashboards. These wear their section hue, as in the sidebar.
  - **Activity:** Tasks, Ingestion, Watchers, Logs, Health, all `trusted: true`.
  - **Instance:** Branding, Backups (trusted), Maintenance, Settings.
- **Older layout.** Screenshots up to v1.11 show a horizontal tab bar (Users · Projects · Dashboards · Branding · Log & Task · Backups · Maintenance) and a page header "Administration — Users, content, branding and the health of this instance." (`docs/images/glass-chrome/admin-light.png`). The current code renders grouped navigation inside `Tabs.List className="ga-nav"`, using Mantine `AppShell` with `layout="alt"` and a 64 px header (l.259–300).
- **Access rules** (`viewer/src/admin/access.ts`):
  - A **trusted instance** is single-user, or neither public nor demo.
  - `canSeeMonitoring`: a trusted instance, or a public-mode signed-in admin who is not temporary.
  - `canSeeBackups`: trusted instances only.
  - The API enforces the same rule in `_require_admin` (`api/v1/endpoints/monitoring_endpoints/routes.py` l.46–70). Demo mode gets 404, and a non-admin or temporary guest gets 403.

### 1.2 People
- **Users** (`AdminUsersPanel.tsx`, 341 lines):
  - Rows are an accordion, one per user: the email, plus badges "You", "System Admin" and status.
  - Expanding a row shows facts: User ID, Registration date, Last login, Account status, Verified, and "Password: must be changed at next sign-in" when flagged.
  - Role is set with a segmented control, Standard / System Admin (l.188–189).
  - Actions: delete, through `DeleteUserModal.tsx`; create, through `CreateUserModal.tsx`.
  - The underlying model is `UserBaseUI` (see [`research/depictio-harmonization.md`](../research/depictio-harmonization.md) §1.1).
- **Groups** (`AdminGroupsPanel.tsx`): only `<GroupsWorkspace scope="admin" />`.
  - It is a master-detail workspace for create, rename, delete, membership and P.I. designation.
  - The same component backs `/groups`, scoped there to the caller's own groups.
  - The model is `Group` (`users_ids`, `admin_ids`, `pi_id`, `pending_pi_email`, `sso_managed`). Screenshot: `docs/images/user-groups_admin-workspace.png`.

### 1.3 Content
- **Projects** (`AdminProjectsPanel.tsx`): accordion rows with Project ID, Owner, Description, Viewers, Dashboards (l.219–257).
- **Dashboards** (`AdminDashboardsPanel.tsx`): accordion rows with Dashboard ID, Owner, Viewers, Components, Last saved (l.158–183).

### 1.4 Activity (one component: `AdminMonitoringPanel.tsx`, 1108 lines; helpers in `viewer/src/monitoring/`)
**Refresh model.**
- Every pane polls on an interval, with an "Auto" toggle and a refresh button (`usePolling`).
- With `monitoring.live_updates` on, events pushed over the events WebSocket trigger a refetch, or patch the list in place for Ingestion, where each step emits an event (l.392–420).
- **Push path** (`api/v1/monitoring/publish.py`): synchronous code (Celery signals, API) publishes to the Redis channel `depictio:events:dashboard:__admin_monitoring__`. The FastAPI events listener fans it out to admin WebSockets. Push is best-effort, and polling is the baseline.

**Tasks** ("Celery tasks", `TasksPane` l.108–300)
- **Not Celery inspect and not Flower.** The pane reads a MongoDB ledger, `task_events`, filled by **Celery signal handlers** in `api/v1/monitoring/task_signals.py`:
  - the signals are `task_prerun`, `task_postrun`, `task_failure`, `task_retry`, `task_revoked`;
  - a logging handler buffers up to 500 lines per task and flushes them on postrun;
  - args and results are stored as `repr` capped at 4000 characters;
  - every handler is wrapped so it never raises into Celery.
- **Model** `TaskEvent` (`models/models/monitoring.py` l.59–97):
  - `task_id` (PK), `task_name`, `kind`, `status`, `args_repr`;
  - links: `dashboard_id`, `dc_id`, `run_id`, `project_id`;
  - execution: `queue`, `worker`, `started_at`, `finished_at`, `duration_ms`;
  - outcome: `error`, `traceback`, `result_summary`, `logs[]`;
  - timestamps: `created_at`, `updated_at`.
- **Value sets.**
  - `TaskStatus` = pending | started | success | failure | retry | revoked.
  - `TaskKind` = figure | screenshot | multiqc | advanced_viz | deltatable | other, derived from the task name (`derive_task_kind`).
- **Retention.** A TTL index on `created_at` set by `monitoring.retention_days` (default 14), created in `store.ensure_monitoring_storage()` (`api/v1/monitoring/store.py` l.36–75).
- **Routes:** `GET /monitoring/tasks?status&kind&since_seconds&limit≤500&skip`, `GET /monitoring/tasks/{task_id}`.
- **UI:**
  - each row shows a status badge, a kind badge, the monospace task name, the duration and a relative time;
  - expanding a row shows Arguments, Result, Error, Traceback and Logs as code blocks;
  - filters: free-text search, Status, Kind;
  - screenshots: `docs/images/v0.12/react/admin_monitoring_tasks_*.png`, `admin_monitoring_task_detail_*.png`.
- **Separate Celery introspection routes** (`api/v1/endpoints/celery_endpoints/routes.py`): `GET /celery/health`, `/celery/active`, `/celery/stats`. These are admin-gated and use inspect.

**Ingestion** (`IngestionPane` l.365–730)
- **What it lists.** CLI ingestion runs reported by the CLI itself:
  - the CLI calls `POST /monitoring/ingestion/start`, then `/ingestion/{run_id}/step` (rate-limited, `monitoring/rate_limit.py`), then `/ingestion/{run_id}/finish`;
  - these write routes are authenticated but not admin-gated;
  - the reads are `GET /monitoring/ingestion` and `/ingestion/{run_id}`.
- **Models** (`IngestionRun`, `IngestionStep`, `IngestionDataCollection`, l.98–300):
  - `IngestionStatus` = running | success | partial | failed | interrupted | abandoned;
  - `IngestionTrigger` = manual | watch | schedule | ui;
  - `source` = cli | ui;
  - a step carries `name`, `status`, `index` / `total`, `progress`, `counters`, `job_id`, `error`, and per-data-collection file counters: `files_matched`, `files_new`, `files_changed`, `files_skipped`, `files_failed`, `rows_written`, `delta_version`, `write_mode`, and so on.
- **Stale runs.** A run still "running" with no update for `monitoring.ingestion_stale_after_hours` (24) becomes **abandoned**.
- **UI:**
  - filters: Status, Instance (CLI `instance_label`), Project;
  - the detail view shows Project, User, Source, Command, Instance, Host, CLI version, Duration, Started, Finished, Steps, Trigger;
  - it also shows IDs, config paths, the data root, a data-collection table (Tag, Type, Format, Scan, Pattern, Local paths, Files) and a step timeline;
  - screenshots: `admin_monitoring_ingestion_*.png`.

**Watchers** (`AgentsPane`, `viewer/src/monitoring/AgentsPane.tsx`)
- **What a watcher is.** `depictio watch` (`cli/cli/commands/watch.py`) is a long-running CLI process that reruns `ingest` when the data changes:
  - modes: incremental or full;
  - backends: native inotify, polling, or both;
  - timing: interval, debounce and settle windows;
  - a per-project lock and a scan-state cache under `~/.depictio/state`.
- **How it is deployed:**
  - as a systemd template unit `deploy/depictio-watch@.service`, one instance per project, configured from `/etc/depictio/%i.env`;
  - or as a container, `deploy/docker-compose.watcher.yaml` (image `ghcr.io/depictio/depictio-cli`, data root mounted read-only, polling by default).
- **Registry.** A watcher heartbeats `POST /monitoring/agents/heartbeat` and is stored in `cli_agents`, where a TTL on `expires_at` (default `agent_ttl_seconds` 300) evicts dead agents. Its id is scoped by owner (`{user_id}:{agent_id}`).
- **Model** `CliAgent` (l.307–347):
  - identity: `kind = watcher`, `instance_label`, `hostname`, `pid`, `cli_version`, `user_id`, `email`, `project_id` / `project_name`;
  - configuration: `mode`, `backend`, `watching[]`;
  - state: `status` (idle | settling | scanning | ingesting | error), `last_error`, `last_run_id`, `runs_total`.
- **"Run now".** `POST /agents/{id}/trigger` stores `run_requested_at` / `run_requested_by`, and the watcher picks the request up on its next command poll with `POST /agents/{id}/claim`. The server never connects to the agent: it is pull-only.
- **Other routes.** `DELETE /agents/{id}` on clean shutdown, and `GET /agents`.

**Logs** (`LogsPane` l.732–905)
- **Storage.** A logging handler, `AppLogMongoHandler` (`api/v1/monitoring/log_handler.py`), is attached to the root `depictio` logger in the API **and** the Celery worker, tagged `source` = api | celery. It writes to the **capped collection** `app_logs` (default 64 MB, `monitoring.app_log_capped_mb`).
- **Record fields:** `level`, `logger`, `source`, `message`, `pathname`, `lineno`, timestamp.
- **Safety.** pymongo loggers and the handler's own store are skipped to avoid recursion.
- **Capture floor.** It defaults to `WARNING` (`monitoring.app_log_min_level`) and can be changed live with `POST /monitoring/logs/level`. The change applies to the API process and is broadcast to the workers (`celery_app.control.broadcast("set_app_log_capture_level")`). It is **not persisted**, so a restart reverts it (routes l.528–550).
- **Reads:** `GET /monitoring/logs?level&source&limit≤1000`.
- **UI:** Level and Source filters, a capture-floor selector, up to 400 rows. Screenshots: `admin_monitoring_logs_*.png`.

**Health** (`HealthPane` l.911–990)
- **Route:** `GET /monitoring/health`. It returns `hostname`, `events_enabled`, `live_updates`, and from `celery_app.control.inspect(timeout=0.75).active()`: `workers[]`, `worker_count`, `active_count`.
- **Status values:** ok, no_workers, broker_unreachable (routes l.553–585).
- **Scope.** There is no database, S3 or disk check in this pane. Infrastructure checks live elsewhere (`utils_endpoints/infrastructure_diagnostics.py`, not read in detail).
- Screenshots: `admin_monitoring_health_*.png`.

### 1.5 Instance
- **Branding** (`AdminBrandingPanel.tsx`, 457 lines):
  - it edits `BrandTheme`;
  - the document is stored in `instance_settings` under `_id: "branding"` (`api/v1/services/branding.py` l.49–160), and logo bytes in `branding_assets`;
  - a startup step migrates legacy logo files (`migrate_legacy_logo_files`, l.384–440).
- **Backups:** see §2.
- **Maintenance** (`AdminMaintenancePanel.tsx`): one action today, "Clean example projects". It deletes the bundled seed projects and cascades, behind a typed `DELETE` confirmation. There is no maintenance mode, no reindex and no cache purge in the UI.
- **Settings** (`AdminSettingsPanel.tsx`):
  - instance-wide settings in collapsible sections, each with its own Save / Reset (`SettingsSections`);
  - one section today, **Version check**: toggle, interval, repository, current version, latest release, last check, last error, "Check now";
  - routes `/utils/version-check` (GET / PUT / reset / run, `utils_endpoints/routes.py` ~l.1170–1200).

## 2. Backup, restore and migration

### 2.1 Database backups (Admin → Backups, CLI, API)
- **Routes** (`api/v1/endpoints/backup_endpoints/routes.py`):
  - `POST /backup/create`, `GET /backup/list`, `POST /backup/validate`;
  - `GET /backup/download/{backup_id}`, `POST /backup/upload` (≤ 200 MB, validated on upload);
  - `POST /backup/restore`, `GET|PUT /backup/schedule`.
- **CLI** (`cli/cli/commands/backup.py`): `depictio backup create | list | validate | restore`, with `--dry-run`, `--collections`, `--force`, `--allow-unverified`, `--skip-validation`, and the developer command `check-coverage`. It logs in as an admin through the CLI config (`_login_as_admin`).
- **Format.**
  - One JSON document, `depictio_backup_<YYYYMMDD_HHMMSS>.json`, in `backup.backup_dir`.
  - It carries `backup_metadata` (`timestamp`, `created_by`, `automatic`, `depictio_version`, `total_documents`, `excluded_documents`, `collections`, `backup_id`) and `data` (l.690–705).
  - A `.sha256` sidecar is written alongside. A missing sidecar can be waived (`allow_unverified`); a mismatch never can.
  - The id is validated against a strict regex and the path is checked for containment, against path traversal (l.45–80).
  - **No encryption** of the file was found.
- **Collections included** (`_create_mongodb_backup`, l.540–610):
  - `users` (temporary users excluded), `projects`, `dashboards`, `data_collections`, `workflows`, `files`, `deltatables`, `runs`, `groups`;
  - `instance_settings`, `branding_assets`, `user_avatars`, `comment_threads`;
  - `dashboard_versions` (only versions worth keeping) and `dashboard_version_counters`;
  - `project_storage_configs`, whose S3 secrets are Fernet-encrypted, so the keys volume must be restored with it.
  - Resources owned by temporary users are excluded.
  - Note: `docs/backup-restore.md` still says "eleven collections". The code has more.
- **Excluded on purpose:**
  - `tokens`, so the admin session survives a restore;
  - derived or self-expiring collections: `jbrowse`, `multiqc`, `multiqc_prerender`, `task_events`, `app_logs`, telemetry;
  - `ingestion_runs`, a gap the docs acknowledge.
  - A test (`check_backup_collections_coverage`) fails CI when a new collection is added without being classified.
- **Restore** (l.1443–1659):
  - per collection, **wipe and replace** (`delete_many` then `insert_many`), rolled back to the previous contents if the insert fails;
  - `dry_run` defaults to true in the API;
  - a `collections` subset can be selected;
  - before touching data, every document is validated against the current Pydantic models, and the restore is refused if any fails unless `skip_validation` is set;
  - `record_last_restore` keeps a marker of which backup the live data came from, outside the restored collections.
- **Restore UI** (`RestoreBackupModal.tsx`): validate → per-collection validation table → type `RESTORE` → restore → result.
- **Backward-compatibility guard** (docs): frozen backup fixtures from v1.0.0 onward are validated on every CI run, and a weekly job restores a backup from the previous release into the current code.
- **Schedule and retention:**
  - **Defaults** come from env (`DEPICTIO_BACKUP_*`): `auto_backup_enabled`, `auto_backup_interval_hours` (24), `auto_backup_time_of_day`, `backup_file_retention_days` (30), `backup_retention_weekly_weeks`, `backup_retention_monthly_months`.
  - **UI overrides** are stored in the DB and take precedence. `is_customized` and "Settings source" show where values come from. `get_backup_schedule_config`, l.478–505.
  - Retention is **grandfather-father-son**: the "smart" preset keeps 30 days, then 4 weekly, then 12 monthly.
  - The loop `periodic_backup` (`api/v1/tasks/backup_tasks.py` l.58) runs in **every API worker**. Exactly one wins each slot through an atomic `find_one_and_update` on `last_run_at` (`claim_auto_backup_slot`, l.383–420).
- **Backups panel UI** (`AdminBackupsPanel.tsx`):
  - a "Create database backup" card (create, download);
  - the "Backups on the server" table: Backup, Created, Version, Size, Documents, Created by, and badges "Automatic", "Restored from", "No checksum";
  - an "Automated backups" card: master switch, interval, preferred time (UTC), simple or smart retention, last and next run, backups on server, disk used, policy in force, settings source;
  - "Restore from file" through upload.

### 2.2 Data (S3 / Delta) backups (`docs/backup-restore.md`, `api/v1/backup_strategy_manager.py`)
- **The admin UI covers the database only.**
- **Data copies** run through the CLI or API with `--include-s3-data`. `backup.s3_backup_strategy` chooses `s3_to_s3` (a second bucket, `backup_s3_*` settings), `local` (gzip optional) or `both`. This option is not in the UI on purpose: it runs synchronously and needs deployment credentials.
- **No S3 restore path exists.** Recovery means restoring the bucket by hand (`mc mirror`, `aws s3 sync`, object versioning, volume snapshot), then the matching database backup.
- **Documented hazard.** `periodic_cleanup_orphaned_s3_files` (`api/v1/tasks/cleanup_tasks.py` l.198) deletes prefixes that no data collection references. After a database rewind, newer tables look orphaned and get deleted.
- **CI store.** `docker-compose/docker-compose.backup-minio.yaml` runs a second SeaweedFS (`weed mini`, image `chrislusf/seaweedfs:4.46`) as the backup bucket for CI. It keeps the historical service name `minio-backup`.

### 2.3 Project migration between instances
- **CLI.** `depictio migrate --project <name> --server <src> --to-server <dst> [--mode all|metadata|dashboard|files] [--dry-run]` (`cli/cli/commands/migrate.py`). It is project-scoped, **upserts, and never wipes** the target.
- **API** (`migrate_endpoints/routes.py`):
  - **Export.** `POST /migrate/export-project` cascades project → workflows → data_collections → files / deltatables / runs → dashboards. It streams a ZIP (`bundle.json` + `migrate_metadata.json`, with S3 objects bundled), or copies server-to-server to `target_s3_config`. That target must be in the `backup.migration_allowed_s3_endpoints` allow-list (an exfiltration guard).
  - **Import.** `POST /migrate/import-project` and `/import-project-zip`, with `owner_user_id`, `force_owner_remap`, `overwrite` (needed to replace an existing project) and `dry_run`. A conflict without `overwrite` comes back as `conflict: true`.
  - **Access.** Admin-only on standard instances. In public mode a non-admin can export the projects they can read, never with a target S3.

### 2.4 Storage and stack migrations
- **MinIO → SeaweedFS** (`scripts/migrate_minio_to_seaweedfs.py`, `docs/migrate-minio-to-seaweedfs.md`):
  - objects are copied through the S3 API, because MinIO's `xl.meta` layout cannot be read by anything else;
  - the old MinIO runs as a side-car (`docker-compose/docker-compose.minio-legacy.yaml`);
  - flags: `--dry-run`, `--verify` (key count and sizes);
  - on Kubernetes with RWO PVCs, it runs in two hops (`--export-dir`, then `--import-dir`);
  - MongoDB is untouched because keys are identical.
  - Config names moved from `DEPICTIO_MINIO_*` to `DEPICTIO_S3_*`, with the old names still accepted (CLAUDE.md).
- **YAML → JSON dashboards** (`scripts/migrate_yaml_to_json.py`): a one-off converter, with a backup and a report.
- **Local → Compose** (`depictio local export --out DIR`, `dev/design/local-server-profile.md`):
  - stops the local server, then copies the MongoDB and SeaweedFS data and the keys;
  - writes `docker-compose.yaml` for that version, an override pinning the image versions that wrote the data, and a `.env` with mode `0600`;
  - CI job `local-to-compose` checks the hand-over end to end.
- **`dev/depictio_restore/`:** a developer script and notebook, not product.

### 2.5 Database schema migrations
- **No migration framework and no schema version stamp** on documents (no Alembic or mongo-migrate equivalent).
- Evolution relies on:
  1. Pydantic defaults that keep old documents valid ("Defaults keep every pre-groups document valid without migration", `models/models/users.py` l.376);
  2. normalising validators (e.g. engine name in `models/models/projects.py` l.54);
  3. idempotent startup steps in `api/v1/services/lifespan.py`: index creation (`start_core_indexes`, dashboard-version and monitoring storage, comment indexes) and one-off data fixes such as `migrate_legacy_logo_files`;
  4. backup validation against current models before a restore.
- One explicit record version exists: `RECORD_SCHEMA_VERSION = 2` for dashboard version snapshots (`models/models/dashboard_versions.py` l.55).
- **Start-up coordination.** One worker wins an initialization lock (`check_and_set_initialization`). The others wait (`wait_for_initialization_complete`).

## 3. Background tasks
- **Celery** (`api/celery_app.py`):
  - broker Redis DB 1, result backend Redis DB 2;
  - `result_expires` at least 86400;
  - `task_default_queue="celery"`, plus an `ingestion` queue for `depictio.deltatable.finalize_upsert` and `depictio.ingestion.run_project` (l.27–50);
  - limits and pools in `CeleryConfig` (`settings_models.py` l.831–885): `worker_concurrency` 4, `worker_pool`, `worker_prefetch_multiplier` 1, `worker_max_tasks_per_child`, soft and hard limits (hard 600 s), `worker_send_task_events`, `task_send_sent_event`.
- **Tasks:**
  - figures: `depictio.figure.build_preview`, `depictio.figure.analyze_code`;
  - MultiQC: `depictio.multiqc.build_preview`, `build_multiqc_prerender`, `prewarm_multiqc_*`;
  - tables: `depictio.deltatables.preview`, `depictio.deltatable.finalize_upsert`, `depictio.manifest.refresh_dc`;
  - ingestion: `depictio.ingestion.run_project`;
  - advanced views: seven `depictio.advanced_viz.compute_*` (heatmap, contact map, coverage track, embedding, group compare, sankey, upset);
  - other: `generate_dashboard_screenshot(_dual)`, `health_check`.
  - Locks use Redis `set_nx` to dedup concurrent enqueues.
- **No Celery beat.** Periodic work runs as **asyncio loops inside the API workers**, each one coordinated by an atomic claim in MongoDB:
  - `periodic_backup`, `periodic_version_check`, `periodic_telemetry_heartbeat`;
  - cleanup of expired temporary users, analytics data, orphaned S3 files and expired tokens (`api/v1/tasks/*.py`).
- **Jobs** (`models/models/jobs.py`): the user-facing record for offloaded work, kept separate from `TaskEvent` for five documented reasons:
  - `TaskEvent` appears only when a worker picks the task up;
  - it has no owner;
  - its result is a truncated `repr`;
  - it has no idempotency key;
  - it is `extra="forbid"`.
- **Job fields and states.** `job_id`, `kind`, `status`, `api_version`, `user_id`, `idempotency_key`, `project_id`, progress, and a structured result.
  - `JobState` = pending | running | success | failed | cancelled.
  - `JobKind` = `deltatable.upsert` | `project.ingest` only. There is deliberately no generic `POST /jobs`, which would be a privilege-escalation surface.
- **Job behaviour.**
  - Retention is a TTL on `expires_at`, so failures can be kept longer.
  - The task writes its own terminal state, which makes `acks_late` safe. The result backend is only a hint.
  - Routes: `GET /jobs/{id}` (404 for non-owners), `GET /jobs`, `POST /jobs/{id}/cancel`.
- **Flower** is an optional `monitoring` profile in `docker-compose.dev.yaml` (l.396–415): `mher/flower:2.0`, persistent DB, bound to 127.0.0.1.
- **Local mode** (`local-server-profile.md`):
  - Celery runs as a native process with `--concurrency=2` (prefork on Linux, threads on macOS because of fork crashes), with `redis-server` from conda-forge through py-rattler;
  - running Celery without Redis (`task_always_eager`) was rejected: 14 call sites, and it would block requests.

## 4. Telemetry
- **What it is.** Anonymous, opt-out telemetry shared by the API and the CLI (`telemetry/`, server parts in `api/v1/telemetry/`, PostHog client `telemetry/posthog.py`).
- **Events:**
  - `server_install` and `server_heartbeat`, with feature booleans, bucketed usage and Kubernetes resources;
  - `cli_install` and `cli_command`.
- **Guarantees.** It never blocks the work it measures, and it sends nothing identifying (`docs/telemetry.md`).
- **Opt-out:**
  - by setting `DEPICTIO_TELEMETRY_ENABLED=false` or `DO_NOT_TRACK=1`;
  - `DEPICTIO_TELEMETRY_INCLUDE_USAGE_METRICS=false` keeps only the install count;
  - `DEPICTIO_TELEMETRY_DEBUG=true` logs instead of sending;
  - automatically off in CI, under pytest, in dev mode, with `MONGODB_WIPE`, or without a collector key.
- **Not the same as analytics.** `analytics_service` records per-user sessions in each deployment's own MongoDB and never transmits anything.

## 5. Settings: runtime vs environment
- **Source of truth.** `api/v1/configs/settings_models.py`: pydantic-settings, one class per area with env prefixes `DEPICTIO_<AREA>_` (auth, mongodb, s3, celery, backup, monitoring, events, version_check, telemetry, performance…).
- **Pattern for runtime-editable settings:** env gives the default, a document in `instance_settings` stores the admin override, and the override wins. Only a few settings use it today:
  - **Branding** (`_id: "branding"`), fully editable.
  - **Backup schedule and retention**: the override wins, so a click is never reverted by a hidden env var; `is_customized` is surfaced.
  - **Version check** (`_id: "version_check"`): three layers. An explicit env value is final and **locks** the UI toggle (`locked_by_env`), then the admin override, then on.
  - **Log capture floor**: runtime only, not persisted.
- **Everything else is env-only** and needs a restart: auth modes, SAML, Google, database, S3, Celery, monitoring retention and sizes, telemetry.
- **Multi-worker reads.** Runtime settings are read fresh or through a short TTL cache (5 s for version check), so all workers converge without a restart.

## 6. Reusable for Spectio
**Copy as patterns**
1. **Admin information architecture.** People / Content / Activity / Instance, deep-linkable views, trusted-instance gating mirrored in UI and API. Spectio's own Activity items are Runs, Tasks, Runner agents, Events and webhooks, Logs, Health.
2. **Two-record task model.** A user-facing `Job` (owner, idempotency key, structured result, self-written terminal state, domain-specific kinds only, no generic enqueue) next to an admin-facing `TaskEvent` ledger with logs, traceback and worker. This is independent of Celery and fits Spectio's queue abstraction directly.
3. **Logs.**
   - A logging handler writing to a bounded store, tagged by source, with a runtime capture floor broadcast to workers.
   - For Spectio: a ring-buffer table in SQLite or Postgres, pruned by size, instead of a Mongo capped collection.
4. **Heartbeat-and-claim agents.**
   - Agents with a TTL heartbeat, an owner-scoped id, and pull-only "Run now" (the server records a request, the agent claims it).
   - Spectio runners already connect outward; the same registry shape (status, host, version, last error, run counts) works for them.
5. **Periodic jobs without beat.** Loops in every process, with an atomic DB claim per slot. This runs unchanged on SQLite (single process) and on Postgres (several replicas).
6. **Backups.**
   - Timestamp ids, a SHA-256 sidecar, validation against current models before a restore, a typed confirmation phrase, per-collection rollback, a "restored from" marker.
   - GFS retention presets; env defaults with UI overrides and a visible "settings source"; a CI coverage test that forces every new table to be classified; frozen fixtures for backward compatibility.
7. **Project migration** separate from a full backup: project-scoped export/import bundle, upsert with `overwrite` and `dry_run`, owner remap, S3 target allow-list.
8. **Local → Compose hand-over** (`local export`) and a CI job that tests it.
9. **Telemetry ethics:** opt-out, `DO_NOT_TRACK`, debug mode, auto-off in CI, documented payloads.

**Do better**
- **Real schema migrations.** Spectio is SQL, so Alembic, with the revision recorded in each backup manifest. Restore then means migrating the backup forward to head; validation is not enough on its own.
- **One backup for database *and* files** in a versioned manifest archive (`manifest.json` + DB dump + blobs + checksums), optionally encrypted. Restore of the file store too, with a guard that pauses orphan cleanup during a restore (depictio's documented hazard).
- **Back up the audit and lineage tables**, the equivalent of `ingestion_runs`, which depictio leaves out.
- **Health covers more than workers:** database, file store, broker, runners, disk, migrations pending.
- **Maintenance does more than delete examples:** maintenance mode (read-only API with a banner), vacuum / `VACUUM INTO`, pruning of work directories and logs, reindex.

**Could be shared as code (inferred, to confirm with the frontend audit)**
- Mantine components from `depictio-react-core` and the admin glass chrome (`GlassPage`, `admin.css`, `SettingsSections`, `usePolling`, monitoring primitives and format helpers).
- The `GroupsWorkspace` UX.
- The Python side is tied to MongoDB / Beanie and is not reusable as code, only as design. Spectio should reimplement the patterns over SQLAlchemy.
