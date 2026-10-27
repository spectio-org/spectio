# Spectio — administration and operations

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)
Companion docs:
- [`api-and-data-model.md`](api-and-data-model.md): identity, tenancy, schema, §13 depictio.
- [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md): plugins, deployments, §7.6 tasks and brokers.
- [`cli-and-shared-libraries.md`](cli-and-shared-libraries.md): the CLI.
- [`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md): what is taken from depictio.
- [`ui-spec.md`](ui-spec.md): screens.

Source for every depictio reference: a code audit of depictio `main` at `0d1aa0a` (2026-10-23), one commit after tag v1.19.2 (`e40ca79`). The working notes are [`research/depictio-admin-ops.md`](../research/depictio-admin-ops.md), [`research/depictio-frontend-admin.md`](../research/depictio-frontend-admin.md) and [`research/depictio-cli-packaging.md`](../research/depictio-cli-packaging.md).

## 0. Decisions in brief

1. **"Settings" becomes "Administration"**, with depictio's structure: the same four groups, People / Content / Activity / Instance, in the same order, as a 208 px section nav inside the page. Spectio keeps its fixed sidebar and full-width top bar, which match depictio's Glass chrome. Personal settings (tokens, preferences, avatar) live in Profile, as in depictio.
2. **Every admin screen has a CLI and an API equivalent.** Each page ends with a collapsible "CLI equivalent". Nothing an admin can do is UI-only, so the same operations work on a headless server, in CI and over SSH.
3. **Users, groups, project sharing and branding mirror depictio field for field.** Same names, same rules, same flows (P.I., pending P.I., SSO-managed groups, protected `admin` and `users` groups, Owner / Editor / Viewer, `BrandTheme`). Spectio adds only what it needs: principal kinds, deactivation, search, section colours.
4. **Operations take depictio's proven patterns and fix its documented gaps.**
   - Taken from depictio:
     - the split between the task ledger and user-facing jobs;
     - a log handler writing to a bounded store, with a capture floor;
     - runners (depictio's watcher agents) that heartbeat and claim "Run now" requests;
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
| **Content** | Projects | Admin → Projects | instance-wide list, including projects the admin is not a member of; rows the admin is not a member of carry a "Not a member · admin access" chip, and an "All projects (admin)" filter lists them |
| | Workflows | (Dashboards in depictio) | catalogue and versions across projects |
| | Environments | (none) | clusters, runners and their owners |
| **Activity** | Background tasks | Tasks | backend-independent ledger, schedules |
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
  - a kind filter (People · Service accounts · Agents · Runners); runner rows are read-only and link to their environment, where runners are connected and their tokens issued ([`ui-spec.md`](ui-spec.md) §4.8);
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

### 3.1 Background tasks

**Two records, as in depictio.**
- **Task ledger (admin).** The `background_tasks` table is the source of truth whatever the backend. It also stores logs, error, traceback, worker and attempts. *(assumed — pending Thomas, inbox #29)*
- **Jobs (users)** are the api §4 `Operation` (`/operations/{id}`): a projection of the ledger restricted to rows the caller created (`created_by` = caller), with no table of its own. They carry the owner, the idempotency key, a structured result and the task's terminal state. *(assumed — pending Thomas, inbox #29)*
- There is **no generic "enqueue any task" endpoint**. Task kinds are fixed by the code, exactly as depictio does (`JobKind`), because a generic enqueue would be a privilege-escalation surface.
- **Secrets in tasks.** Task arguments that carry a secret (a webhook URL with a token, a backup passphrase) use a `SecretRef` type, resolved by the worker and never stored in clear. Tracebacks are stored without local variables. Arguments, results and logs pass through the redaction of §3.4. *(assumed — pending Thomas, inbox #27)*

A run's engine tasks are a different table, `tasks` / `attempts`, with the prefix `task_` ([`api-and-data-model.md`](api-and-data-model.md) §7). *(assumed — pending Thomas, inbox #29)*

This section owns the ledger's columns and its screen; [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.6 owns the mechanism (backends, claiming). *(assumed — pending Thomas, inbox #29)*

| Field group | Fields |
|---|---|
| Identity | `id` (`btask_…`), `kind`, `queue`, `priority` |
| Ownership | `project_id`, `created_by` (principal: user, service, system) |
| State | `queued`, `running`, `succeeded`, `failed`, `retrying`, `cancelled`; `attempts` / `max_attempts`; `run_after` |
| Execution | `worker_id`, `started_at`, `finished_at`, `duration_ms` |
| Outcome | `progress {done, total, message}`, `result_ref`, `error {type, message}`, `traceback_ref`, `logs` (capped, flushed at the end, as depictio does with its 500-line buffer) |
| Retention | `expires_at`: 14 days by default; failures 30 days |

- **Kinds:** `check.dispatch`, `webhook.deliver`, `sink.depictio`, `sink.labid`, `rocrate.export`, `backup.create`, `backup.restore`, `workdir.cleanup`, `catalogue.import`, `bridge.publish`.
  - `check.dispatch` sends the evaluation of a check's source binding to the runner (runner protocol: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.7, pending inbox #12) and waits for `spectio.check.evaluated`; the server then computes the verdict ([`checking-scenarios.md`](checking-scenarios.md) §11.1). *(assumed — pending Thomas, inbox #28)*
  - Notifications are not a task kind: notifiers subscribe to events through the outbox ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §3.5).
- **Screen:**
  - summary cards: queued, running, failed in the last 24 h, oldest queued, workers alive, backend;
  - filters: search, status, kind, project, auto-refresh;
  - rows: status, kind, task name, project, owner, attempts, duration, age;
  - an expanded row shows arguments, result, error, traceback and logs, with Retry now, Cancel and Open run.
- **Schedules** (periodic jobs) have their own tab, showing last run, next run and the process holding the claim. There is no Celery beat. Only processes that run the `worker` role, alone or together with `api` ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.1), run the loops. Each slot is claimed by inserting a row into `schedules(schedule_key, slot_start)`, which is unique on the pair; the process whose insert succeeds runs the slot. This works unchanged with one SQLite process or several Postgres replicas, with no advisory lock. *(assumed — pending Thomas, inbox #29)*
- **With the Celery plugin,** signal handlers fill the same ledger (`task_prerun`, `task_postrun`, `task_failure`, `task_retry`, `task_revoked`, as in depictio), so the screen does not change.

### 3.2 Runners (depictio's Watchers, generalised)

- **Heartbeat and pull.** Runners heartbeat every 30 s with name, host, version, environments, status (`online` / `draining` / `offline`), active runs and last error. A runner is marked offline after 3 missed heartbeats. Each heartbeat carries the runner's clock; the server records the offset and warns above 5 s (Health → Runners). Heartbeats are sent from a dedicated thread, so a file-system stall on the runner does not make it look offline. Runner states are drawn with the system-state tokens of [`ui-spec.md`](ui-spec.md) §3.3: online as succeeded, draining as review, offline as failed.
- **Commands are pulled, never pushed** (launch, cancel, "Run diagnostics"). The server records the request and the runner claims it, exactly like depictio's "Run now" for watchers. The server never connects to a runner. Each command is a row of `runner_commands` ([`api-and-data-model.md`](api-and-data-model.md) §7), written in the same transaction as the decision or relaunch; the runner claims it with a lease and acknowledges it, and an expired lease makes it claimable again. *(assumed — pending Thomas, inbox #12)*
- **Version skew** follows [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §12: a runner outside the window is refused and shown as incompatible; inside it, a runner behind the server shows a warning. *(assumed — pending Thomas, inbox #28)* Both show on the runner row and on the environment header ("runner 0.4.1 · server 0.4.2 · update").
- **Restart storms.** After the server boots, no runner is marked offline until 3 heartbeat intervals have passed. Runners and bridges reconnect with jitter, and replays are admitted per runner (`429` with `Retry-After`) under a rate cap. Otherwise a server outage longer than 90 s marks every runner offline, sends `spectio.runner.offline` webhooks and notifications, and every runner and bridge replays its buffer at once.
- The registry appears in Health and in Environments.

### 3.3 Events & webhooks

- **Outbox view:** events by type, delivery status per subscriber (webhook, notifier, sink, bridge), and attempts.
- **Actions:** redeliver, and pause a subscriber.
- **Event bridges** (MQTT, AMQP, Kafka, NATS) show their connection state and lag ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.6).

### 3.4 Logs

- **Capture.** A logging handler, as in depictio, writes structured records to a bounded ring-buffer table (`log_records`), with SQLite in a separate database file attached to the main one (`ATTACH`), written in batches off the request path, with a cap per source and a drop counter. The buffer is capped by size (default 256 MB) and age (default 14 days). The writer never logs its own failures into the buffer, which would recurse.
- **Sources:**
  - `api`, `worker`;
  - `runner:<name>`: runners ship their daemon logs over HTTPS in batches;
  - `plugin:<name>`;
  - `engine:<run>`: only WARN and above from a run's head-process log; the full log stays on the runner and is fetched with range requests, like task logs. Why: `.nextflow.log` grows by about 1–3 KB per task at debug level, so a 100 000-task run produces 100–300 MB (estimate, **[to be validated in `fanout_stress`]**), which would evict every other source and compete with ingest for the single SQLite writer.
- **Fields:** level, logger, source, message, timestamp, `request_id`, `run_id`, `engine_task_id`, `background_task_id`, `principal_id`, `project_id`, and `extra` as JSON.
- **Capture floor.** It defaults to WARNING and can be changed in the UI. Unlike depictio, the change is persisted in `instance_settings` and broadcast to every process through pub/sub, so it survives a restart.
- **Live tail** over SSE. Correlation chips open the run, task or request.
- **External stacks.** When one is configured (Loki / Grafana, ELK), the page links to it with the same filters. Containers always log JSON to stdout as well, so the ring buffer is a convenience, never the only copy.
- **Redaction.** One redaction function, owned here, is applied before anything is written to or sent from these sinks: event ingest (`POST /ingest/events`), `log_records`, task arguments, results and logs (§3.1), audit-log diffs ([`api-and-data-model.md`](api-and-data-model.md) §7), RO-Crate export ([`synthesis.md`](synthesis.md) §7quinquies) and telemetry. *(assumed — pending Thomas, inbox #27)* Spectio cannot rely on the engine: `config show` masks secret keys (`ConfigCmdAdapter.groovy:650-651`), but `params` are not masked, and `nf-tower` sends them as is (`TowerObserver.groovy:383`, `session.getParams().toPlainMap()`). The function replaces with `[redacted]`:
  - known secret values: resolved secret references and live tokens;
  - any string with the `spk_` token prefix;
  - values whose key matches Nextflow's sensitive-name pattern: `SECRET_KEYS = ~/(?im)^AWS.+|.*TOKEN.*|.*PASSWORD.*|.*SECRET.*|.*accessKey.*|.*api_?key.*/` (nextflow `114f1fe`, `SecretHelper.groovy:35`), deprecated in favour of `StringUtils.isSensitiveName` (nf-commons `StringUtils.groovy:80`), whose pattern was not compared **[to be validated]**;
  - schema fields flagged `x-spectio-secret` or `format: password`.
  - **Test:** a canary secret seeded in params, env, a webhook URL and a backup passphrase appears in no sink, crate or database dump (proposed spike `sec-redaction-canary`, [R5](../reviews/R5-security.md)).
- **Audit log** is separate: append-only, never pruned automatically, and included in backups.

### 3.5 Health

**Component checks.** Each shows a status, a key metric and the time it was last checked.

| Check | ok / warn / fail examples |
|---|---|
| Database | latency, connections; SQLite with the WAL-reset fix ([`api-and-data-model.md`](api-and-data-model.md) §7) and on a local disk; WAL file size (warn when checkpoints fall behind, [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.2) |
| File store | reachable, used vs quota |
| Task backend | workers alive, queue depth, oldest queued age |
| Pub/sub | `LISTEN/NOTIFY` round trip; fail when listeners or advisory locks go through a pooler in transaction mode |
| Identity providers | OIDC metadata reachable; SAML certificate expiry |
| Plugins | loaded / failed / incompatible |
| Runners | online / offline, version skew, clock offset (warn above 5 s) |
| Disk | data directory free space |
| Backups | age of the last successful, verified backup |
| Migrations | pending Alembic revisions |
| TLS certificate | expiry |
| Outbox | backlog and oldest undelivered event |
| Engine bridges | bridge versions seen on active runs; warn "bridge too old" when one is outside the compatibility window ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §12) *(assumed — pending Thomas, inbox #28)* |

- **Endpoints for orchestrators:**
  - `/health/live`: the process is up;
  - `/health/ready`: database reachable and its schema revision within the range this release supports (not "at head": during a Helm pre-upgrade hook the old pods see a newer revision and would all turn unready at once, §4.3);
  - `/metrics`: Prometheus format.
- **Metrics** (`/metrics`, Prometheus format): runs by state; gate wait time; background task queue depth and age of the oldest queued task; outbox lag; runner heartbeats (age of the last one per runner); request latency per route template, not per raw path, so label cardinality stays bounded. The Helm chart has an optional `ServiceMonitor`. depictio has no Prometheus, OpenTelemetry or Sentry code and no ServiceMonitor (R8b DEP-T-029). *(assumed — pending Thomas, inbox #26)*
- **Tracing.** The server propagates W3C `traceparent` and its `request_id` on runner commands, and runners log them, so one request can be followed from the API to the runner. *(assumed — pending Thomas, inbox #26)*
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
  - **Status colours style alerts only** (toasts, banners, form messages). Run states and the other states of [`ui-spec.md`](ui-spec.md) §3 keep their own tokens (`--sp-state-*`) and are not brandable. The panel refuses a `success`, `warning` or `danger` value whose `-fg` falls below 4.5:1 on white or on the dark surface (WCAG 2.1 SC 1.4.3, https://www.w3.org/TR/WCAG21/#contrast-minimum). *(assumed — pending Thomas, inbox #30)*
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
- **No installation from the browser for now** ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §11).

### 4.3 Backups, restore and migration

**What a backup is.** One archive, `spectio-backup-<instance>-<UTC timestamp>.tar.zst`, containing:
- `manifest.json`: Spectio version, schema revision (Alembic), instance ID, creator, kind, the parts with SHA-256 and size, and encryption information; `signature`: an Ed25519 signature of the manifest by the instance key; the instance's public key is kept outside the archive, so verification never trusts the archive's own `keys/` *(assumed — pending Thomas, inbox #24)*;
- `db/`: by default a **native same-engine backup**: the SQLite online backup API run in steps (or `VACUUM INTO` in a quiet window), or `pg_dump -Fd -j` (CloudNativePG / barman on Kubernetes). A **portable logical export**, one JSON Lines file per table in foreign-key order, is made only for cross-engine migration (SQLite → Postgres) and project export. Why: at 2–4 GB of new data a day (estimate), a nightly Python export of every table takes hours and must read from one snapshot, which starves SQLite checkpoints and holds back Postgres `xmin`. *(assumed — pending Thomas, inbox #24)*
- `files/`: the file store (evidence copies, cached reports, branding assets, avatars, exported crates, archived raw event payloads ([`api-and-data-model.md`](api-and-data-model.md) §8.4), copied as files, not rows);
- `keys/`: token signing keys and the secret-store key. Without the keys, stored secrets cannot be decrypted. The same holds for depictio's Fernet-encrypted storage configs.
- `plugins/`: plugin instance settings. Secrets are stored as references by default. With "Include encrypted secrets", they are sealed with a passphrase or an age recipient.

**What a backup is not.**
- Run work directories and results on clusters. They stay where the engines wrote them and are referenced by path. A restored run whose directory is gone shows as archived.
- Tokens. As in depictio, they are not restored, so the admin's session survives a restore.
- Logs and the background-task ledger (`background_tasks`), which are derived or self-expiring. A run's engine tasks (`tasks`, `attempts`) are backed up with the run. *(assumed — pending Thomas, inbox #29)*
- The audit log and run lineage **are** included. depictio leaves out its ingestion history, a gap its own docs acknowledge.

**Coverage test.** As in depictio, a CI test fails when a new table is added without being classified as backed up or excluded.

**Kinds of backup.**

| Kind | Content | Typical use |
|---|---|---|
| Full | everything above | nightly, before an upgrade, before a migration |
| Pre-upgrade | full, taken automatically before `spectio db upgrade` (switch on by default); skipped when a verified backup is younger than N hours (setting) | rollback point |
| Project export | one project with its workflows, runs, gates, decisions, change sets, artifacts' metadata and files | move a project between instances (personal → team server). Mirrors depictio's `migrate --project` |

A restore always restores the whole archive; there is no partial restore by table (the project export covers one project). *(assumed — pending Thomas, inbox #24)*

**Recovery objectives.** Each deployment states its recovery point objective (RPO) and recovery time objective (RTO); Health → Backups compares the age of the last verified backup with the RPO. *(assumed — pending Thomas, inbox #24)*

**Destinations** are `spectio.backup` plugins: a local directory (built in), any S3-compatible store (SeaweedFS, as in depictio), or SFTP.

**Schedule and retention**, as in depictio.
- The defaults come from `SPECTIO_BACKUP_*` variables. UI overrides win over them and are shown with a "Settings source" line.
- Retention is "simple" (N days) or "smart" grandfather-father-son: 30 daily, 4 weekly, 12 monthly.
- The backup runs as a scheduled task claimed by exactly one process.

**Verify.** Checksums of every part, the manifest signature (Ed25519, checked against the instance's public key, never against `keys/` in the archive), a test decompression, and validation of the export against the models of its own schema revision.

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

**Restore mechanics.** The restore step runs as follows, so a crash or live traffic cannot leave a mixed state; this supersedes the "each table is wiped and replaced" wording of step 5. *(assumed — pending Thomas, inbox #24)*
- The backup is restored into a **new** database (a new SQLite file, or a new Postgres database or schema), verified and migrated there, then switched in atomically (a rename, or the `DATABASE_URL` pointer).
- A restore journal file in the data directory records each step, so a restart resumes or rolls back; the maintenance state lives in that journal, outside the restored tables.
- Ingest answers `503` with `Retry-After` while the restore runs, and the bridges keep their events in the spool ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §13).
- After the switch, each runner sends a full inventory (head jobs, launch directories, unsent spool); runs the server does not know become "orphaned after restore" for an admin to adopt, and runs that are gone are archived.

Why: restoring `instance_settings` in place would switch maintenance off mid-restore; one transaction across the whole database needs about twice the disk and hours on a large instance; runs created after the backup are still running and keep sending events.

**Instance migrations** (Maintenance → Migrate this instance):

| From → to | Command | How |
|---|---|---|
| Python bundle → Docker Compose | `spectio local export --out DIR` | stop, copy the data directory and keys, write `compose.yaml` + override + `.env` (0600), pinned to the running version. Mirrors depictio's `local export` and its CI job |
| SQLite → Postgres | `spectio migrate database --to postgresql://…` | portable export → import → row-count and checksum verification → switch `DATABASE_URL` |
| Local file store → S3 | `spectio migrate storage --to s3://…` | copy + verify (key count and sizes, like depictio's MinIO → SeaweedFS script), orphan cleanup paused, then switch |
| One project → another instance | `spectio migrate project <name> --to-server <profile>` | project export + import, as untrusted input (below); `--overwrite` matches only rows of the target project; owner remap; `--dry-run`; target S3 endpoints allow-listed (depictio's exfiltration guard) |

**Project imports are untrusted input.** An export may come from another instance or by email. *(assumed — pending Thomas, inbox #25)*
- Every ID is re-minted on import. `--overwrite` matches only rows that already belong to the target project, never an ID from another project.
- Imported decisions and audit entries become provenance (`imported_from`: source instance, original principal name and ID), never live principals of this instance.
- Webhooks, plugin instances, service accounts and tokens are never imported.
- Imported manifests (`spectio.yml` overlays) are inert: their gate policy, `script:` bindings and agent permissions stay off until an editor of the target project turns them on.
- Workflow sources and crates inside the export follow [`api-and-data-model.md`](api-and-data-model.md) §5 (Imports are untrusted input).

**Test:** an import with `--overwrite` that names a run of another project is refused.

**Schema migrations.**
- One Alembic tree for both SQLite and Postgres, with `render_as_batch` for SQLite. A revision branches on the dialect inside itself only where it must. Reason: one revision ID per schema state, which the backup manifest and the compatibility guard rely on. Prefect chose the other way, one tree per dialect (`src/prefect/server/database/_migrations/versions/sqlite/`, 115 entries, next to `…/postgresql/`, 120 entries, at `21a1f02`). Revisited after R9 spike 7 (three representative revisions, a JSON column, a partial index and an `ALTER` of a constraint, on SQLite and Postgres 18). *(assumed — pending Thomas, inbox #28)*
- In the bundle, migrations run automatically at start, after the pre-upgrade backup (skipped when a recent verified backup exists, see Kinds of backup). *(assumed — pending Thomas, inbox #24)*
- In Compose and Kubernetes they run explicitly: a `migrate` one-shot service or a Helm hook Job.
- Commands: `spectio db status | upgrade | history`. There are no down-migrations in production; a restore is the rollback.
- Data migrations live in Alembic too, so a backup's revision says exactly what its data looks like. depictio has no migration framework and relies on Pydantic defaults instead.
- **Expand and contract.** Release N only adds (tables, nullable columns, indexes); destructive steps (drop, rename, tighten) come in N+1, so old pods keep working while the Helm pre-upgrade hook migrates.
- **No table-copy migrations** on `events`, `tasks` or `attempts`: Alembic batch mode creates a new table, copies the data and drops the old one ([Alembic batch](https://alembic.sqlalchemy.org/en/latest/batch.html)), which on SQLite holds the write lock for the whole copy and needs twice the disk; add tables or nullable columns instead.
- **Migration-time budget**, checked in CI on a seeded database.

**Compatibility guard in CI**, copied from depictio:
- frozen backup fixtures from v0.1 onwards are restored on every CI run;
- a weekly job restores a backup made by the previous release into the current one.

### 4.4 Maintenance

- **Maintenance mode.**
  - Modes: `normal`, `no-launch` (no new launches or gate decisions), `read-only` (the API refuses writes) and `restoring` (set automatically by restore and migrations). Runners keep executing running jobs in every mode.
  - A banner message with a preview, and an optional end time.
  - Used automatically by restore and migrations; during a restore its state is kept in the restore journal, outside the restored tables (§4.3). *(assumed — pending Thomas, inbox #24)*
  - No option stops runners or clusters. The page header shows the maintenance state read-only; "Turn on now" and "Schedule" are the only actions.
  - **Everyone sees it.** One shared banner, below the top bar on desktop and below the phone top bar, shows the maintenance or announcement message, its style (info or warning) and its end time; announcements can be dismissed per user. While maintenance is on, the primary actions it blocks are disabled with the reason. On a phone it is never a one-tap switch ([`ui-spec.md`](ui-spec.md) §4.11).
  - What still works in each mode is in the table at the end of this section.
- **Announcement banner.** Info or warning style, dates, dismissible per user.
- **Database:** schema revision and history, pre-upgrade backup switch, ANALYZE / VACUUM (SQLite), integrity check.
- **Migrate this instance:** the four migrations in §4.3 (bundle → Compose, SQLite → Postgres, file store → S3, project → another instance). *(assumed — pending Thomas, inbox #24)*
- **Cleanup jobs:**
  - work directories, following each environment's lifecycle policy (rules: `GET/PUT /environments/{id}/lifecycle`, [`api-and-data-model.md`](api-and-data-model.md) §5; each clean emits `spectio.run.workdir_cleaned`) *(assumed — pending Thomas, inbox #30)*;
  - orphaned blobs, paused during restores;
  - expired tokens;
  - delivered outbox events older than the retention period;
  - the logs ring buffer;
  - raw event payloads of terminal runs, moved to the file store ([`api-and-data-model.md`](api-and-data-model.md) §8.4). *(assumed — pending Thomas, inbox #28)*
  
  Each shows its last run, space freed, next run and a Run now button.

**What still works in each mode.**

| Operation | normal | no-launch | read-only | restoring |
|---|---|---|---|---|
| Reads (GET, SSE) | yes | yes | yes | no |
| Sign-in and sessions | yes | yes | yes | only the admin running the restore |
| Launch, relaunch, resume | yes | no | no | no |
| Cancel a run | yes | yes | no | no |
| Gate decisions, proposals, change sets, bulk decide | yes | no | no | no |
| Robot and instrument signals (`POST /gates/{id}/signals`) | yes | no | no | no |
| Engine ingest (`POST /ingest/events`) | yes | yes | yes | no (the bridges buffer) |
| Runner channel (heartbeats, command claims, results, `spectio.check.evaluated`) | yes | yes, no new launch commands | yes, no new commands | no |
| Other writes (projects, workflows, tokens, settings) | yes | yes | no | no |
| Maintenance and backup endpoints (admins) | yes | yes | yes | only the running restore |
| Webhook and notifier delivery, scheduled loops | yes | yes | yes | paused |

- A refused request gets `503` with `Retry-After` and a problem type ending in `/maintenance` (RFC 9457, [`api-and-data-model.md`](api-and-data-model.md) §4).
- Gate timeouts are paused while the mode is not `normal`.
- An announced maintenance window has a maximum duration (proposed default 2 h) that the engine bridges' local buffer must cover (buffer bounds: ingest contract, [`api-and-data-model.md`](api-and-data-model.md) §14, pending inbox #11).

### 4.5 Settings

- **Runtime-editable settings** follow depictio's pattern: an environment value gives the default, the admin override is stored in `instance_settings` and wins.
- **Locked settings.** Where a site must enforce a value, an explicit environment value locks the control and the UI says so (depictio's version check does this with `locked_by_env`).
- Every setting shows its source (default, env, UI).
- **Restart required.** Settings that need a restart (database URL, auth modes) are shown read-only with their source.
- **Sub-panels:** Sign-in ([`authentication-and-access.md`](authentication-and-access.md) §5), Telemetry ([`telemetry-and-analytics.md`](telemetry-and-analytics.md) §2.3) and Version check ([`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md) §1.1). Other docs write paths as "Administration → <group> → <section>".

## 5. API and data

Only system admins may call these endpoints; everything else is in [`api-and-data-model.md`](api-and-data-model.md) §5. *(assumed — pending Thomas, inbox #29)*

| Area | Endpoints (prefix `{root}/api/v1/admin`) |
|---|---|
| Users, groups | `/users`, `/users/{id}` (`PATCH` state, admin flag), `/groups`, `/groups/{id}/pi`, `/groups/{id}/pending-pi` (member management is at the root, api §5) *(assumed — pending Thomas, inbox #29)* |
| Background tasks | `GET /background-tasks?state&kind&project&since`, `GET /background-tasks/{id}`, `POST /background-tasks/{id}/retry`, `POST /background-tasks/{id}/cancel`, `GET /schedules` *(assumed — pending Thomas, inbox #29)* |
| Runners | `GET /runners`, `POST /runners/{id}/diagnostics` (pulled by the runner) |
| Events & webhooks | `GET /outbox?type&state` (cursor), `POST /subscribers/{id}:pause`, `POST /subscribers/{id}:resume`, `GET /bridges` (connection state and lag, §3.3) |
| Audit log | `GET /audit-log?principal&action&object&since` (cursor; instance-wide; a project's audit log for its owners stays at the root, [`api-and-data-model.md`](api-and-data-model.md) §5) *(assumed — pending Thomas, inbox #29)* |
| Notifications | `GET/PUT /notification-routes` (notifier instances and routing, §1) |
| AI & agents | `GET/POST/PATCH/DELETE /ai/endpoints` (model endpoints, [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2), `GET/PUT /ai/agent-defaults` (default limits for agents: evidence size, environments agents may launch on, sending files to hosted models; a gate can be stricter, never looser, [`ui-spec.md`](ui-spec.md) §4.9) *(assumed — pending Thomas, inbox #29)* |
| Logs | `GET /logs?level&source&run&engine_task&background_task&since` (cursor), `GET /logs/stream` (SSE), `PUT /logs/capture-level` |
| Health | `GET /health` (all checks), plus `/health/live`, `/health/ready`, `/metrics` outside the API prefix |
| Branding | `GET/PUT/DELETE /branding`, `POST /branding/logo/{light\|dark}`, `GET /branding/presets` (the public branding is served by `GET /public-config`, api §5) *(assumed — pending Thomas, inbox #29)* |
| Plugins | `GET /plugins`, `GET/POST/PATCH/DELETE /plugin-instances` |
| Backups | `POST /backups` (202 + Operation), `GET /backups`, `GET /backups/{id}`, `GET /backups/{id}/download`, `POST /backups/{id}/verify`, `POST /backups/upload`, `POST /restores` (dry run by default; 202), `GET /restores/{id}`, `GET/PUT /backups/schedule` |
| Migrations | `GET /db/status`, `POST /migrations/project-export`, `POST /migrations/project-import` |
| Maintenance | `GET/PUT /maintenance`, `GET/PUT /announcements`, `GET /cleanup-jobs`, `POST /cleanup-jobs/{id}/run`; the active maintenance state and announcements are also public in `GET /public-config` (section `maintenance`), so every user's banner can be drawn |
| Settings | `GET /settings` (value + source + locked), `PATCH /settings` |

**New tables.** These extend [`api-and-data-model.md`](api-and-data-model.md) §7:
- `background_tasks` *(assumed — pending Thomas, inbox #29)*, `schedules` (`schedule_key`, `slot_start`, `claimed_by`, `claimed_at`; unique `(schedule_key, slot_start)`) *(assumed — pending Thomas, inbox #29)*, `log_records` (ring buffer);
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

- Not drawn yet: Events & webhooks (`AdminEvents`), Audit log (`AdminAudit`), Notifications (`AdminNotifications`) and Settings (`AdminSettings`, every setting with its source and lock, §4.5).
- Variants still to draw: single-user Administration (Users with one row and a "Set up sign-in" card; project switcher and sharing hidden, [`api-and-data-model.md`](api-and-data-model.md) §6), and AdminNav and the phone Administration screen without Activity, Backups and Maintenance on `public` / `demo` instances (§1).
