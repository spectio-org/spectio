# depictio ecosystem — what Spectio reuses, shares, copies or leaves

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)

**Source.**
- A full read of the depictio repository at v1.19.2 (commit `0d1aa0a`, 2026-10-23). Detailed notes are in [`research/depictio-admin-ops.md`](../research/depictio-admin-ops.md), [`research/depictio-cli-packaging.md`](../research/depictio-cli-packaging.md) and [`research/depictio-frontend-admin.md`](../research/depictio-frontend-admin.md), all with file and line references.
- LabID read from gitlab.com/lab-integrated-data on the same day.

**Companion docs:** [`api-and-data-model.md`](api-and-data-model.md) §13 (identity, roles, hand-off), [`admin-and-operations.md`](admin-and-operations.md), [`cli-and-shared-libraries.md`](cli-and-shared-libraries.md), [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md).

**Verdicts used below:**
- **Depend:** use the published artifact as is.
- **Share:** move it to a package both projects depend on.
- **Copy:** reimplement the pattern in Spectio's code, keeping names and behaviour.
- **Call:** use it at runtime through its CLI or API.
- **Leave:** not relevant, or a pattern to avoid.

## 0. Summary

- **The code is not shared, the design and the contracts are.** depictio is MongoDB / Beanie / Celery / Delta Lake. Spectio is SQL with a task backend that does not require Redis. Very little server code carries over.
- **What carries over is a lot:**
  - the identity and tenancy model;
  - branding;
  - the admin information architecture and its screens;
  - backups and migrations;
  - task and log monitoring;
  - CLI conventions;
  - packaging (wheel with the UI inside, `local up` / `local export`, Compose with SeaweedFS, Helm on GHCR);
  - CI guards.
- **Three things should become shared packages:**
  - the branding theme (Python model and React theme engine and editor);
  - a client core for CLIs;
  - run-directory readers, which LabID needs too.
- **First joint use case.** depictio's own nf-core validation campaign (`scripts/nfcore_validation_hpc.py`) submits sbatch head jobs on the EMBL cluster, polls `.nextflow.log` and `squeue`, rsyncs the outputs back and ingests them. That is exactly Spectio's job. Running that campaign through Spectio, with the depictio hand-off at the end, is the first real test of both tools together.

## 1. Inventory and verdicts

### 1.1 Python: models and server

| depictio item | What it is | Verdict | Spectio use |
|---|---|---|---|
| `models/models/branding.py` (`BrandTheme`, `merge_brand_themes`, `resolve_brand_theme`, `BRAND_PRESETS`) | pure Pydantic theme, three layers, presets | **Share** (move to `bioplatform-models`; vendor until then) | identical branding model and JSON |
| `models/models/users.py` (`UserBase`, `Group`, `Permission`, `TokenBase`) | identity and permissions on MongoDB documents | **Copy** as field-compatible API schemas (no `bson`) | users, groups (P.I., pending P.I., `sso_managed`), Owner / Editor / Viewer |
| `api/v1/permissions.py` (`resolve_effective_role`, highest role wins, public = viewer floor) | access rules | **Copy** | same semantics in `can()` |
| `models/models/jobs.py` (`Job`) and `monitoring.py` (`TaskEvent`) | user job vs admin task ledger | **Copy** | `tasks` table + jobs view ([`admin-and-operations.md`](admin-and-operations.md) §3.1) |
| `monitoring.py` (`CliAgent`) + heartbeat / claim routes | watcher registry, pull-only "Run now" | **Copy** | runner registry and pulled commands |
| `api/v1/monitoring/log_handler.py` (capped collection, capture floor) | admin logs | **Copy**, improved | ring-buffer table, persisted floor, runner / engine / plugin sources |
| `api/v1/monitoring/task_signals.py` | Celery signals → ledger | **Copy** inside `spectio-plugin-celery` | same ledger whatever the backend |
| `api/v1/endpoints/backup_endpoints` + `backup_strategy_manager.py` | DB backup JSON + SHA-256, validation, GFS retention, schedule claim | **Copy**, extended | archive with files, schema revision, encryption, file restore |
| `migrate_endpoints` + `cli/commands/migrate.py` | project bundles between instances, S3 allow-list | **Copy** | `spectio migrate project` |
| `api/v1/tasks/*` (periodic loops with an atomic claim) | scheduling without Celery beat | **Copy** | schedules on SQLite and Postgres |
| `settings_models.py` (one env prefix per area; runtime overrides with source; `locked_by_env`) | configuration | **Copy** | `SPECTIO_<AREA>_*`, Settings page with source |
| Version check (`VersionCheckConfig`, admin toggle) | "a new version is available" | **Copy** | Settings → Version check |
| `models/models/run_info.py` (`RunInfoReader`) + `nextflow.py` + `snakemake.py` readers | run-directory provenance | **Share** (`bioplatform-runinfo`, with LabID's sniffers) | adopting observed runs, RO-Crate, hand-off |
| `MongoModel`, `PyObjectId`, `DEPICTIO_CONTEXT` branches in models | storage-bound models | **Leave** | storage-agnostic models, explicit context |
| Server code (Beanie, Delta, Celery tasks, dashboards) | depictio's own domain | **Leave** | — |
| `telemetry/` | opt-out PostHog, `DO_NOT_TRACK`, auto-off in CI | **Copy** the ethics, off by default | — |

### 1.2 CLI and clients

| depictio item | Verdict | Spectio use |
|---|---|---|
| Typer app with help panels, hidden renamed aliases, `-v/-vv/--log-level` | **Copy** | `spectio` command tree ([`cli-and-shared-libraries.md`](cli-and-shared-libraries.md) §2) |
| `utils/http_retry.py` (retry only idempotent calls; status list; connect errors always) | **Share** (`bioplatform-client`) + `Idempotency-Key` | every client |
| `--result-json` shape (status, IDs, URLs) | **Copy** | long commands |
| `depictio-cli ingest --pipeline-id --triggered-by --attach-run --user --provenance-file --result-json` | **Call** | the `sink.depictio` hand-off ([`api-and-data-model.md`](api-and-data-model.md) §13.3) |
| `depictio.config` Nextflow `onComplete` hook | **Call / Leave**: Spectio sets `depictio_enabled=false` for the runs it launches and triggers the hand-off itself; the hook stays for runs Spectio does not manage | — |
| `depictio watch` (watcher agents, systemd and container units) | **Copy** the deployment pattern | `spectio runner` as a systemd template unit and container |
| `depictio local up/down/status/open/wipe/export` | **Copy** (simpler: SQLite and files, no binaries to fetch) | `spectio local …`, hand-over to Compose |
| `backup create/list/validate/restore` verbs and options | **Copy** names | `spectio backup …` |
| `CLIConfig` (one file per server, S3 secret inside) | **Leave** | LabID-style multi-server file, no storage secret |
| Hand-written `api_calls.py` and `api.ts` types | **Leave** | clients generated from OpenAPI |
| Heavy base install (~0.9 GB) | **Leave** | < 80 MB base, CI-checked |

### 1.3 Frontend

| depictio item | Verdict | Spectio use |
|---|---|---|
| `depictio-react-core` theme engine (`buildDepictioTheme`, `brandCssVariablesResolver`, `BrandingContext`, `mergeBrandThemes`, `BRAND_PALETTES`) and editor (`BrandThemeForm`, `BrandThemePreview`) | **Share**: extract a small published `@bioplatform/theme` (Mantine as only peer); vendor the five files until then | same theme at runtime, same Branding panel |
| `authFetch` (bearer token, refresh on 401, retry) | **Copy** into `@spectio/client` with a configurable `apiBase` | — |
| `adminUrlState` (URL-routed admin sections), `usePolling`, `Facts`, typed-delete confirmation, `SettingsSections` | **Copy** | Administration |
| `GroupsWorkspace` (one master–detail for admin and "my groups") | **Copy** field for field | Groups |
| `PermissionsApp` (Visibility / Members / Groups with Owner / Editor / Viewer) | **Copy** field for field | project sharing |
| `ProfileApp`, `CliAgentsPanel` (create token → show config once) | **Copy** | Profile → Tokens |
| Glass chrome (`Shell.tsx`: top bar, WORKSPACE sidebar, icon rail, status at the bottom) | **Copy**: Spectio's shell already follows it; a shared `@bioplatform/chrome` later if both want it | — |
| Dashboard renderers (`MultiQCRenderer`, `TableRenderer`, `ImageRenderer`, `JBrowseRenderer`, `FigureRenderer`) | **Call** first (deep link or embed a depictio dashboard from Run detail); a viewer plugin later if the packages are published | evidence and review views |
| `depictio-components`, `tool-studio` | **Leave** for now | — |
| Blockers on reuse as code: `depictio-react-core` is private and unbuilt TypeScript, hard-codes `API_BASE = '/depictio/api/v1'`, and pulls Plotly, AG Grid, genome-spy and 3dmol | to solve with the theme extraction | — |

### 1.4 Data and knowledge

| depictio item | Verdict | Spectio use |
|---|---|---|
| nf-core project templates: 32 pipelines, each with pinned versions (`projects/nf-core/<pipeline>/<version>/template.yaml`, template id `nf-core/<pipeline>/<version>`) | **Call** | Workflows catalogue badge "depictio dashboard available"; `depictio: template: auto` picks it by pipeline ID |
| Tool catalogue (`depictio/catalog/`, ~120 module folders mapping nf-core outputs → recipes → components, anchored on bio.tools, nf-core and EDAM) | **Share** the knowledge: output file patterns per module | evidence `match` globs and check presets in `spectio.yml` ([`checking-scenarios.md`](checking-scenarios.md)) |
| `scripts/nfcore_megatest.py` (resolves nf-core AWS megatest results per release) | **Copy** the idea | reference QC distributions per pipeline version for check presets ("this sample is below the megatest's 5th percentile") |
| `scripts/nfcore_monitor.py` (new nf-core releases, output drift) | **Call** / align | catalogue "new version available" and drift warnings for gates whose evidence paths moved |
| `scripts/nfcore_validation_hpc.py` (sbatch head jobs, status from `.nextflow.log`, rsync back) | **Replace with Spectio** | first joint use case (§0) |
| `plotly-upset`, `plotly-complexheatmap` (Python, PyPI pending) | **Depend**, optionally, in a viewer plugin | an upset of failed checks across samples in review |

### 1.5 Deployment and CI

| depictio item | Verdict | Spectio use |
|---|---|---|
| SeaweedFS `weed mini` (`chrislusf/seaweedfs:4.46`, Compose service `s3` with a `minio` alias, `DEPICTIO_S3_*`, Helm `s3:` values with the legacy `minio:` key merged) | **Copy** exactly, same image and version; one shared instance when co-hosted, separate buckets | Compose `s3` profile, Helm |
| `scripts/migrate_minio_to_seaweedfs.py` (copy through the S3 API, `--verify`, two-hop export/import for RWO PVCs) | **Copy** | `spectio migrate storage` |
| Docker images (uv base pinned by digest, non-root, `nginx-unprivileged`) | **Copy** hardening; **Leave** building from the source tree | one image built from the wheel |
| Helm chart (OCI on GHCR, Gateway API `httproutes`, PDB, init jobs, optional Percona operator) | **Copy** conventions; use chart semver instead of date versions | `spectio` chart; later an umbrella `platform` chart (depictio + Spectio + SeaweedFS + one ingress) |
| Flower under a `monitoring` profile | **Copy** for the Celery plugin only | — |
| `deploy/depictio-watch@.service` | **Copy** | `spectio-runner@.service` |
| `deploy-embl-selfhosted.yaml` (self-hosted runner, environments `trec-demo`, `demo`) | **Reuse** the EMBL deployment target | Spectio demo next to depictio's |
| CI: `local-server-smoke` (3 platforms), `local-to-compose`, `cli-base-install`, `backup-compat-cross-version` (weekly), frozen backup fixtures, wheel size check, `security_audit_compose.sh` / `security_audit_helm.sh` | **Copy** all | same guards |
| Playwright as the only e2e suite | **Copy** | — |

### 1.6 LabID

| LabID item | Verdict | Spectio use |
|---|---|---|
| `labidlib` / `labidcli` split (library + Typer CLI with JSON for `jq`) | **Copy** the split | `spectio.client` + `spectio` CLI |
| `~/.labid/labidapi.yml`: several servers keyed by URL plus `default` | **Copy** | `servers.yaml` with named profiles |
| Workflow-run sniffers (`NextflowRunSniffer`, `NextflowRunCrateSniffer`, `GalaxyRunCrateSniffer`, samplesheet sniffer) | **Share** (`bioplatform-runinfo`) | RO-Crate import and export, observed runs |
| REST under `/api/`, `token-auth/`, Bearer or `Token` headers (DRF, inferred) | **Call** from `spectio-plugin-labid` | resolver `labid://`, sink, inbound launches |
| Sniffer plugins loaded from directories on `sys.path` | **Leave** | entry points |

## 2. Migration paths between the two tools

1. **Identity, once co-hosted.**
   - `spectio user import --from depictio` reads depictio's users and groups (`GET /auth/list`, `/groups/list`) with an admin token.
   - It creates Spectio principals linked as `depictio:user/<id>`, and groups with members, admins, P.I. and `sso_managed`.
   - SSO groups match by name and need no import once both use the same identity provider.
2. **Branding.** Export JSON in depictio, import in Spectio: it is the same model. Or select "Shared with depictio".
3. **Run history.**
   - depictio's registered `WorkflowRun`s (results directories) can be adopted in Spectio as read-only historical runs.
   - Adoption reads each `run_location` with the shared run-directory readers.
   - The adopted runs are linked both ways (`depictio:run/<id>` ↔ `spectio:run/<id>`).
4. **Pipeline identifiers.** depictio template IDs and Spectio workflow version keys are the same string, `<org>/<name>/<version>`, so nothing needs mapping.
5. **Ingestion triggers.**
   - For runs launched by Spectio, the hand-off replaces both the `onComplete` hook and `depictio watch`.
   - The hook and watchers stay for folders Spectio does not manage.
6. **Storage.** One SeaweedFS with buckets `depictio` and `spectio`, each with its own credentials.
7. **Deployment.**
   - `compose.depictio.yaml` joins both stacks behind one proxy (`/depictio`, `/spectio`).
   - An umbrella Helm chart later does the same on Kubernetes.

## 3. Requests to make to depictio (small, reversible)

1. Publish `plotly-upset` and `plotly-complexheatmap` (already planned).
2. Extract the branding model and theme engine into a small shared package.
3. Make `API_BASE` configurable in the React client.
4. Add an OpenAPI-generated TypeScript client.
5. Let `/auth/me` be called with a token issued for Spectio once trust is configured, or expose the JWKS public key for RS256 verification.
6. Accept a `--provenance-file` in Workflow Run RO-Crate format, so Spectio can pass its crate directly.
7. Add `checks_as` beside `renders_as` in catalogue output YAMLs: check presets such as `{kind: outlier, column: pct_mito, by: sample, k: 3}`, validated against `OUTPUT_SCHEMA` like `renders_as`. Spectio reads them as its presets ([`checking-scenarios.md`](checking-scenarios.md) §4).
8. A runnable recipe entry point without a server, for example `depictio catalog run <module>/<output> <results dir> --out <parquet>`, so the runner computes the same tables at gate time ([`api-and-data-model.md`](api-and-data-model.md) §13.6).
9. Selection and filter messages for embedded dashboards, next to `depictio:set-color-scheme`: for example `depictio:set-filter {column, values}` and `depictio:selection {key, values}` **[to be validated]** with depictio's maintainers.
10. Per-file recipes for the tools labs watch during a run (STAR `Log.final.out`, Trim Galore and fastp reports, Salmon `meta_info.json`, mosdepth summaries), with the column names of the MultiQC route ([`checking-scenarios.md`](checking-scenarios.md) §11.6).
11. One shared nf-core megatest fetcher instead of `scripts/nfcore_megatest.py` and Spectio's `tools/fixtures/megatests.py`, pinning the same release per pipeline.

Details and file references for 7–11: [research note, 2026-10-26](../research/depictio-qc-integration-2026-10-26.md).
