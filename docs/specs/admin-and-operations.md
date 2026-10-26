# Spectio — administration and operations

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)
Companion docs:
- [`api-and-data-model.md`](api-and-data-model.md): identity, tenancy, schema, §13 depictio.
- [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md): plugins, deployments, §7.6 tasks and brokers.
- [`cli-and-shared-libraries.md`](cli-and-shared-libraries.md): the CLI.
- [`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md): what is taken from depictio.
- [`ui-spec.md`](ui-spec.md): screens.

Source for every depictio reference: a code audit of depictio v1.19.2 (commit `0d1aa0a`, 2026-10-23). The working notes are [`research/depictio-admin-ops.md`](../research/depictio-admin-ops.md), [`research/depictio-frontend-admin.md`](../research/depictio-frontend-admin.md) and [`research/depictio-cli-packaging.md`](../research/depictio-cli-packaging.md).

## 0. Decisions in brief

1. **"Settings" becomes "Administration"**, with depictio's structure: the same four groups, People / Content / Activity / Instance, in the same order, as a 208 px section nav inside the page. Spectio keeps its fixed sidebar and full-width top bar, which match depictio's Glass chrome. Personal settings (tokens, preferences, avatar) live in Profile, as in depictio.
2. **Every admin screen has a CLI and an API equivalent.** Each page ends with a collapsible "CLI equivalent". Nothing an admin can do is UI-only, so the same operations work on a headless server, in CI and over SSH.
3. **Users, groups, project sharing and branding mirror depictio field for field.** Same names, same rules, same flows (P.I., pending P.I., SSO-managed groups, protected `admin` and `users` groups, Owner / Editor / Viewer, `BrandTheme`). Spectio adds only what it needs: principal kinds, deactivation, search, section colours.
4. **Operations take depictio's proven patterns and fix its documented gaps.**
   - Taken from depictio:
     - the split between the task ledger and user-facing jobs;
     - a log handler writing to a bounded store, with a capture floor;
     - agents that heartbeat and claim "Run now" requests;
     - periodic loops coordinated by an atomic database claim, with no Celery beat;
     - backup safety: checksums, validation before restore, typed confirmation, GFS retention, a "restored from" marker.
   - Fixed in Spectio:
     - schema revisions (Alembic) recorded in every backup;
     - one archive holding both the database and the file store;
     - restore of files too, not only the database;
     - optional encryption;
     - a real maintenance mode;
     - health checks beyond the workers.

## 1. Information architecture

| Group | Section | Mirrors in depictio | Spectio additions |
|---|---|---|---|
| **People** | Users | Admin → Users | principal kinds (people, service accounts, agents, runners), search, deactivate |
| | Groups | Admin → Groups and `/groups` | projects and environments shared with the group |
| | Service accounts | (none; depictio has a provisioning key) | LIMS, CI and robot identities with scoped tokens |
| **Content** | Projects | Admin → Projects | instance-wide list, including projects the admin is not a member of |
| | Workflows | (Dashboards in depictio) | catalogue and versions across projects |
| | Environments | (none) | clusters, runners and their owners |
| **Activity** | Tasks | Tasks | backend-independent ledger, schedules |
| | Runners | Watchers | heartbeat registry of runners (shown in Health) |
| | Events & webhooks | (none) | outbox, deliveries, event bridges |
| | Logs | Logs | runner, engine and plugin sources, persisted capture floor, live tail |
| | Health | Health | every component, not only workers |
| | Audit log | (none) | who did what, from which principal |
| **Instance** | Branding | Branding | section colours, sign-in and help texts, "shared with depictio" source |
| | Plugins | (none) | installed plugins, compatibility, instances, failures |
| | AI & agents | (none) | AI providers, agent policies |
| | Notifications | (none) | notifier instances and routing |
| | Backups | Backups | archive with files, encryption, destinations, restore wizard |
| | Maintenance | Maintenance | maintenance mode, announcements, schema, instance migrations, cleanup |
| | Settings | Settings | runtime-editable settings, with their source |

**Access** follows depictio's rule.
- A *trusted instance* is single-user, or neither public nor demo.
- Activity, Backups and Maintenance are hidden on untrusted instances.
- The API applies the same check, so this is not only a UI rule.
- Sections are URL-routed (`/admin/<section>`), and the last section is remembered per browser.

**Single-user mode.** Administration is always visible. People shows one user and the `personal` group, with a "Set up sign-in" call to action. Nothing changes structurally when the instance becomes multi-user.

## 2. People

### 2.1 Users (mirrors depictio `AdminUsersPanel`)

- **Rows.** One accordion row per principal, showing:
  - email or name;
  - badges: "You", "System admin" or "User", "Inactive";
  - the sign-in source: OIDC (EMBL SSO, LS Login), SAML, depictio token, or local.
- **Expanded facts:**
  - user ID, registration date, last login, account status, verified;
  - "Password must be changed at next sign-in", when it applies;
  - groups, with a crown where the user is P.I. and a shield where they are group admin;
  - number of projects and tokens.
- **Create user**, as in depictio:
  - fields: email, display name, a generated 14-character initial password (with Generate and Copy), "Ask for a new password at first sign-in", and "System admin";
  - with SSO only, the form explains that the person signs in with single sign-on.
- **Spectio additions:**
  - search;
  - a kind filter (People · Service accounts · Agents · Runners);
  - Invite, which sends an email when a notifier is configured;
  - Deactivate / Reactivate, which keeps the history and revokes the user's tokens;
  - Delete, behind a typed confirmation and refused for oneself.
- **The Delete rule is stricter than depictio's.** A principal referenced by decisions or audit entries is never hard-deleted. It is anonymised to `deleted-user-<id>`, so the audit trail stays readable.

### 2.2 Groups (mirrors depictio `GroupsWorkspace`)

- **One component, two scopes.** The same master–detail screen serves Administration → Groups (every group) and the Profile → My groups view (the caller's groups, editable where the caller is a group admin).
- **Left panel:** search, Create, and a list showing group and members.
- **Right panel:** name, description, and the P.I. block.
  - Pending state: "P.I. pending — `<email>` becomes P.I. and group admin at their first sign-in".
  - Members grid: Member, Name, Group admin, P.I., remove.
  - Add-member picker.
- **Rules, identical to depictio:**
  - only system admins set the P.I.;
  - group admins rename the group and manage members;
  - `admin` and `users` are protected and cannot be deleted;
  - SSO-managed groups carry an SSO badge and the notice "Synced from SSO — manual changes may be overwritten at next login".
- **Spectio addition.** A "Shared with this group" list of projects (with the group's role) and environments the group owns.

### 2.3 Service accounts

Non-human principals: LIMS, CI, robots, event bridges.
- Each has an owner group, scopes and tokens with an expiry, plus last use, rotation and revocation.
- **depictio has no equivalent.** Its pipelines use a provisioning key to create passwordless users. Spectio keeps that call only inside the depictio sink plugin ([`api-and-data-model.md`](api-and-data-model.md) §13).

### 2.4 Project sharing (mirrors depictio `PermissionsApp`)

- **Visibility.** A Public / Private switch, with the same sentences as depictio.
- **Members and Groups.** Each row has an Owner / Editor / Viewer segmented control. The same hint applies: "Owners manage members and visibility, editors change the project's content, viewers can only look."
- **Launcher and Reviewer are Spectio-only roles** ([`api-and-data-model.md`](api-and-data-model.md) §13.2). They appear as an "Advanced" row of capabilities on top of Editor, so the three-role surface stays identical to depictio's.

## 3. Activity

### 3.1 Tasks

**Two records, as in depictio.**
- **Task ledger (admin).** The `tasks` table is the source of truth whatever the backend. It also stores logs, error, traceback, worker and attempts.
- **Jobs (users).** The user-facing view of a task the user started. It carries an owner, an idempotency key, a structured result and the task's own terminal state.
- There is **no generic "enqueue any task" endpoint**. Task kinds are fixed by the code, exactly as depictio does (`JobKind`), because a generic enqueue would be a privilege-escalation surface.

| Field group | Fields |
|---|---|
| Identity | `id` (`task_…`), `kind`, `queue`, `priority` |
| Ownership | `project_id`, `created_by` (principal: user, service, system) |
| State | `queued`, `running`, `succeeded`, `failed`, `retrying`, `cancelled`; `attempts` / `max_attempts`; `run_after` |
| Execution | `worker_id`, `started_at`, `finished_at`, `duration_ms` |
| Outcome | `progress {done, total, message}`, `result_ref`, `error {type, message}`, `traceback_ref`, `logs` (capped, flushed at the end, as depictio does with its 500-line buffer) |
| Retention | `expires_at`: 14 days by default; failures 30 days |

- **Kinds in v1:** `check.evaluate`, `gate.notify`, `webhook.deliver`, `sink.depictio`, `sink.labid`, `rocrate.export`, `backup.create`, `backup.restore`, `workdir.cleanup`, `catalogue.import`, `bridge.publish`.
- **Screen:**
  - summary cards: queued, running, failed in the last 24 h, oldest queued, workers alive, backend;
  - filters: search, status, kind, project, auto-refresh;
  - rows: status, kind, task name, project, owner, attempts, duration, age;
  - an expanded row shows arguments, result, error, traceback and logs, with Retry now, Cancel and Open run.
- **Schedules** (periodic jobs) have their own tab, showing last run, next run and the process holding the claim. There is no Celery beat: each process runs the loops, and an atomic database claim per slot decides who runs it, as depictio does. This works unchanged with one SQLite process or several Postgres replicas.
- **With the Celery plugin,** signal handlers fill the same ledger (`task_prerun`, `task_postrun`, `task_failure`, `task_retry`, `task_revoked`, as in depictio), so the screen does not change.

### 3.2 Runners (depictio's Watchers, generalised)

- **Heartbeat and pull.** Runners heartbeat every 30 s with name, host, version, environments, status (`online` / `draining` / `offline`), active runs and last error. A runner is marked offline after 3 missed heartbeats.
- **Commands are pulled, never pushed** (launch, cancel, "Run diagnostics"). The server records the request and the runner claims it, exactly like depictio's "Run now" for watchers. The server never connects to a runner.
- **Version skew** beyond one minor version shows a warning.
- The registry appears in Health and in Environments.

### 3.3 Events & webhooks

- **Outbox view:** events by type, delivery status per subscriber (webhook, notifier, sink, bridge), and attempts.
- **Actions:** redeliver, and pause a subscriber.
- **Event bridges** (MQTT, AMQP, Kafka, NATS) show their connection state and lag ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.6).

### 3.4 Logs

- **Capture.** A logging handler, as in depictio, writes structured records to a bounded ring-buffer table (`log_records`). The buffer is capped by size (default 256 MB) and age (default 14 days). The writer never logs its own failures into the buffer, which would recurse.
- **Sources:**
  - `api`, `worker`;
  - `runner:<name>`: runners ship their daemon logs over HTTPS in batches;
  - `plugin:<name>`;
  - `engine:<run>`: the head-process log of a run, streamed by the runner.
- **Fields:** level, logger, source, message, timestamp, `request_id`, `run_id`, `task_id`, `principal_id`, `project_id`, and `extra` as JSON.
- **Capture floor.** It defaults to WARNING and can be changed in the UI. Unlike depictio, the change is persisted in `instance_settings` and broadcast to every process through pub/sub, so it survives a restart.
- **Live tail** over SSE. Correlation chips open the run, task or request.
- **External stacks.** When one is configured (Loki / Grafana, ELK), the page links to it with the same filters. Containers always log JSON to stdout as well, so the ring buffer is a convenience, never the only copy.
- **Audit log** is separate: append-only, never pruned automatically, and included in backups.

### 3.5 Health

**Component checks.** Each shows a status, a key metric and the time it was last checked.

| Check | ok / warn / fail examples |
|---|---|
| Database | latency, connections; SQLite version ≥ 3.51.3 and on a local disk |
| File store | reachable, used vs quota |
| Task backend | workers alive, queue depth, oldest queued age |
| Pub/sub | `LISTEN/NOTIFY` round trip |
| Identity providers | OIDC metadata reachable; SAML certificate expiry |
| Plugins | loaded / failed / incompatible |
| Runners | online / offline, version skew |
| Disk | data directory free space |
| Backups | age of the last successful, verified backup |
| Migrations | pending Alembic revisions |
| TLS certificate | expiry |
| Outbox | backlog and oldest undelivered event |

- **Endpoints for orchestrators:**
  - `/health/live`: the process is up;
  - `/health/ready`: database reachable and migrations at head;
  - `/metrics`: Prometheus format.
- **What depictio checks.** Its Health pane only checks Celery workers and the broker.

## 4. Instance

### 4.1 Branding and customisation (mirrors depictio)

- **Model.**
  - Spectio uses depictio's `BrandTheme` unchanged:
    - identity: `app_name`, `logo_mode`, `logo_url`, `logo_url_dark`;
    - brand colours: `primary`, `secondary`, `tertiary`;
    - status colours: `success`, `warning`, `danger`;
    - `tint_mode`;
    - surfaces: `surfaces_light` and `surfaces_dark` (page, cards and sections, header and sidebar, titles);
    - type and shape: fonts, `default_radius`;
    - figures: `plots` (template, colorway, sequential scale);
    - extra: `palettes`.
  - The model is pure Pydantic. It is shared as a package, or vendored until one exists ([`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md)).
- **Layers**, as in depictio, each later one winning:
  1. environment defaults `SPECTIO_BRANDING_PRESET`, `SPECTIO_BRANDING_THEME` (JSON) and flat `SPECTIO_BRANDING_*` variables;
  2. instance overrides from the admin panel;
  3. a per-project override (depictio: per dashboard), limited to colours.
- **Panel**, as in depictio:
  - presets (Spectio, depictio, EMBL, TREC, Ocean), Import / Export of the JSON;
  - logo upload, light and dark: PNG, JPEG or WebP, ≤ 2 MB, never SVG;
  - an accordion form showing how many fields are set;
  - a live preview, then Reset and Save.
  - "Powered by Spectio" shows when the Spectio wordmark is hidden (`logo_mode` custom or none), the same rule as depictio.
- **Theme source when co-hosted.**
  - *Shared with depictio:* Spectio reads depictio's effective theme from `/depictio/api/v1/utils/public-config` and only Spectio's own section colours stay editable.
  - *Own theme:* Spectio keeps a theme of its own.
  - In both cases an institute brands the platform once.
- **Spectio additions:**
  - **Section colours** for Overview, Runs, Review, Launch, Workflows and Environments. They are validated to stay distinct from depictio's Dashboards orange and Projects teal ([`ui-spec.md`](ui-spec.md)).
  - **Sign-in and help:** login message, SSO button label (depictio has `saml_login_label`), help and docs URL, support email, footer links.
  - Announcements are set from Maintenance (§4.4). depictio has none.

### 4.2 Plugins

- **Installed packages:** version, kinds, SDK API compatibility per kind, source (built in, PyPI, config), instances with their scope, health and import time.
- **Failed plugins** show their traceback, with Disable and Docs.
- **Instances declared in config** are read-only, with a "set in config" badge.
- **No installation from the browser in v1** ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §11).

### 4.3 Backups, restore and migration

**What a backup is.** One archive, `spectio-backup-<instance>-<UTC timestamp>.tar.zst`, containing:
- `manifest.json`: Spectio version, schema revision (Alembic), instance ID, creator, kind, the parts with SHA-256 and size, and encryption information;
- `db/`: a **portable logical export**, one JSON Lines file per table in foreign-key order. The same backup restores into SQLite or Postgres, which makes it the SQLite → Postgres migration path too. A native `pg_dump` part can be added for speed on large instances.
- `files/`: the file store (evidence copies, cached reports, branding assets, avatars, exported crates);
- `keys/`: token signing keys and the secret-store key. Without the keys, stored secrets cannot be decrypted. The same holds for depictio's Fernet-encrypted storage configs.
- `plugins/`: plugin instance settings. Secrets are stored as references by default. With "Include encrypted secrets", they are sealed with a passphrase or an age recipient.

**What a backup is not.**
- Run work directories and results on clusters. They stay where the engines wrote them and are referenced by path. A restored run whose directory is gone shows as archived.
- Tokens. As in depictio, they are not restored, so the admin's session survives a restore.
- Logs and task ledgers (derived or self-expiring data).
- The audit log and run lineage **are** included. depictio leaves out its ingestion history, a gap its own docs acknowledge.

**Coverage test.** As in depictio, a CI test fails when a new table is added without being classified as backed up or excluded.

**Kinds of backup.**

| Kind | Content | Typical use |
|---|---|---|
| Full | everything above | nightly, before an upgrade, before a migration |
| Pre-upgrade | full, taken automatically before `spectio db upgrade` (switch on by default) | rollback point |
| Project export | one project with its workflows, runs, gates, decisions, change sets, artifacts' metadata and files | move a project between instances (personal → team server). Mirrors depictio's `migrate --project` |

**Destinations** are `spectio.backup` plugins: a local directory (built in), any S3-compatible store (SeaweedFS, as in depictio), or SFTP.

**Schedule and retention**, as in depictio.
- The defaults come from `SPECTIO_BACKUP_*` variables. UI overrides win over them and are shown with a "Settings source" line.
- Retention is "simple" (N days) or "smart" grandfather-father-son: 30 daily, 4 weekly, 12 monthly.
- The backup runs as a scheduled task claimed by exactly one process.

**Verify.** Checksums of every part, the manifest signature, a test decompression, and validation of the export against the models of its own schema revision.

**Restore** (wizard in the UI, `spectio backup restore` in the CLI):
1. **Choose**: a backup from a destination, or an uploaded file.
2. **Inspect**: the manifest, checksums, encryption, and the schema plan. A backup at revision 0012 into a server at 0015 means "migrate forward 3 revisions". A newer backup into an older server is **refused**.
3. **Dry run** (the default): rows per table now and in the backup, files to restore and missing objects, warnings (work directories gone, tokens not restored), and what happens next.
4. **Confirm** by typing the instance name.
5. **Restore**, in this order:
   - maintenance mode turns on, runners stop picking up new launches, and orphan cleanup is paused, which avoids depictio's documented hazard of deleting newer data after a rewind;
   - each table is wiped and replaced, with rollback if anything fails;
   - files are restored;
   - Alembic migrates the database up to head;
   - "restored from `<backup id>`" is recorded;
   - maintenance mode turns off.

**Instance migrations** (Maintenance → Migrate this instance):

| From → to | Command | How |
|---|---|---|
| Python bundle → Docker Compose | `spectio local export --out DIR` | stop, copy the data directory and keys, write `compose.yaml` + override + `.env` (0600), pinned to the running version. Mirrors depictio's `local export` and its CI job |
| SQLite → Postgres | `spectio migrate database --to postgresql://…` | portable export → import → row-count and checksum verification → switch `DATABASE_URL` |
| Local file store → S3 | `spectio migrate storage --to s3://…` | copy + verify (key count and sizes, like depictio's MinIO → SeaweedFS script), orphan cleanup paused, then switch |
| One project → another instance | `spectio migrate project <name> --to-server <profile>` | project export + import; upsert with `--overwrite`, owner remap, `--dry-run`; target S3 endpoints allow-listed (depictio's exfiltration guard) |

**Schema migrations.**
- Alembic with `render_as_batch` (SQLite).
- In the bundle, migrations run automatically at start, after the pre-upgrade backup.
- In Compose and Kubernetes they run explicitly: a `migrate` one-shot service or a Helm hook Job.
- Commands: `spectio db status | upgrade | history`. There are no down-migrations in production; a restore is the rollback.
- Data migrations live in Alembic too, so a backup's revision says exactly what its data looks like. depictio has no migration framework and relies on Pydantic defaults instead.

**Compatibility guard in CI**, copied from depictio:
- frozen backup fixtures from v0.1 onwards are restored on every CI run;
- a weekly job restores a backup made by the previous release into the current one.

### 4.4 Maintenance

- **Maintenance mode.**
  - Choices: block new launches and gate decisions, or make the API read-only. Runners keep executing running jobs either way.
  - A banner message with a preview, and an optional end time.
  - Used automatically by restore and migrations.
- **Announcement banner.** Info or warning style, dates, dismissible per user.
- **Database:** schema revision and history, pre-upgrade backup switch, ANALYZE / VACUUM (SQLite), integrity check.
- **Migrate this instance:** the three wizards in §4.3.
- **Cleanup jobs:**
  - work directories, following each environment's lifecycle policy;
  - orphaned blobs, paused during restores;
  - expired tokens;
  - delivered outbox events older than the retention period;
  - the logs ring buffer.
  
  Each shows its last run, space freed, next run and a Run now button.

### 4.5 Settings

- **Runtime-editable settings** follow depictio's pattern: an environment value gives the default, the admin override is stored in `instance_settings` and wins.
- **Locked settings.** Where a site must enforce a value, an explicit environment value locks the control and the UI says so (depictio's version check does this with `locked_by_env`).
- Every setting shows its source (default, env, UI).
- **Restart required.** Settings that need a restart (database URL, auth modes) are shown read-only with their source.

## 5. API and data

| Area | Endpoints (prefix `{root}/api/v1/admin`) |
|---|---|
| Users, groups | `/users`, `/users/{id}` (`PATCH` state, admin flag), `/groups`, `/groups/{id}/members/{principal}`, `/groups/{id}/pi`, `/groups/{id}/pending-pi` |
| Tasks | `GET /tasks?state&kind&project&since`, `GET /tasks/{id}`, `POST /tasks/{id}/retry`, `POST /tasks/{id}/cancel`, `GET /schedules` |
| Runners | `GET /runners`, `POST /runners/{id}/diagnostics` (pulled by the runner) |
| Logs | `GET /logs?level&source&run&task&since` (cursor), `GET /logs/stream` (SSE), `PUT /logs/capture-level` |
| Health | `GET /health` (all checks), plus `/health/live`, `/health/ready`, `/metrics` outside the API prefix |
| Branding | `GET/PUT/DELETE /branding`, `POST /branding/logo/{light\|dark}`, `GET /branding/presets`; public `GET /public-config` |
| Plugins | `GET /plugins`, `GET/POST/PATCH/DELETE /plugin-instances` |
| Backups | `POST /backups` (202 + Operation), `GET /backups`, `GET /backups/{id}`, `GET /backups/{id}/download`, `POST /backups/{id}/verify`, `POST /backups/upload`, `POST /restores` (dry run by default; 202), `GET /restores/{id}`, `GET/PUT /backups/schedule` |
| Migrations | `GET /db/status`, `POST /migrations/project-export`, `POST /migrations/project-import` |
| Maintenance | `GET/PUT /maintenance`, `GET/PUT /announcements`, `GET /cleanup-jobs`, `POST /cleanup-jobs/{id}/run` |
| Settings | `GET /settings` (value + source + locked), `PATCH /settings` |

**New tables.** These extend [`api-and-data-model.md`](api-and-data-model.md) §7:
- `tasks`, `schedules` (slot claims), `log_records` (ring buffer);
- `runner_heartbeats`, folded into `runners`;
- `instance_settings` (key, value JSON, updated_by, updated_at);
- `branding_assets`;
- `backups` (id, kind, destination, manifest JSON, size, verified_at, created_by), `restores` (id, backup_id, dry_run report, state, started_by);
- `announcements`, `plugin_instances`.

## 6. UI boards

The canvas has a new "Administration" row:
- Users, Groups, Service accounts, Projects (reworked);
- Tasks, Logs, Health with Runners;
- Branding, Plugins, AI & agents (reworked);
- Backups, Restore wizard, Maintenance;
- a phone Administration screen.

All share the `AdminNav` component.
