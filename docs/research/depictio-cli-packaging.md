# depictio CLI, shared models and packaging — audit for Spectio (+ LabID CLI)

Source: depictio checkout `scratchpad/dep` at v1.19.2 (commit 0d1aa0a, 2026-10-23). Paths are relative to the repo root. LabID read from gitlab.com/lab-integrated-data via the GitLab API on 2026-10-25 (copies in `research/labid/`). "Inference" marks what is not read directly.

## 1. CLI (`depictio/cli/`)

### 1.1 App structure
- Typer app `app = typer.Typer(... rich_markup_mode="rich")` in `depictio/cli/depictio_cli.py:117`. Entry `main()` at `:481` wraps `app()` with telemetry (`CommandTimer`, `send_command_event`) and brand-coloured help.
- Root callback `verbose_callback` (`:169`): `-v/-vv` (count), `--log-level <level>`, hidden legacy `-vl/--verbose-level`, eager `--version/-V`. `depictio` alone prints a landing page (`invoke_without_command=True`).
- Help panels declared once (`HELP_PANELS`, `:50-55`): **Get started** (local, ingest, watch) · **Projects and data** (config, data, dashboard, template, manifest) · **Administration** (migrate, backup) · **Reference** (catalog, commands, version). Hidden groups: `images` (old names), `dev` (maintainer tooling).
- Renames are handled by keeping hidden aliases and printing a note (`utils/renamed.py`, `note_renamed`); e.g. `run` → `ingest` (`commands/run.py:3409-3418`), `--CLI-config-path` → `--server`.
- Size: ~36.5 k lines under `depictio/cli/`; the biggest pieces are `commands/run.py` (3.4 k), `utils/compose.py` (3 k), `utils/scan.py` (2.7 k), `local_stack.py` (2.1 k).

### 1.2 Command tree (key options)
| Command | Sub-commands / key options |
|---|---|
| `ingest DATA_DIR` (`commands/run.py`) | `--template`, `--var K=V`, `--project`, `--project-config-path`, `--manifest`, `--attach-run`, `--update-config`, `--pipeline-id`, `--triggered-by`, `--user` + `--provisioning-key`, `--provenance-file`, `--result-json`, `--compose`, `--dry-run`, `--skip-scan/-process/-join/-sync`, `--write-mode`, `--concurrency`, `--continue-on-error`, `--streaming`. Exit 1 if any step failed (`run.py:3400-3407`) |
| `watch` (`commands/watch.py`) | `ingest` on a loop; registers as a **CLI agent** with the server (`api_agent_heartbeat` → `POST /monitoring/agents/heartbeat`, `api_agent_claim_trigger` → `/monitoring/agents/{id}/claim` for a "Run now" pressed in the UI, `api_agent_deregister`; `utils/api_calls.py:721-781`). Project lock file. systemd template `deploy/depictio-watch@.service`, compose `deploy/docker-compose.watcher.yaml` |
| `local` (`commands/local.py`) | `up` (`--examples`, `--port`, `--screenshots`, `--no-open`), `open`, `down`, `status`, `wipe`, `export --out` (hand-over to Compose) |
| `config` (`commands/config.py`) | `show`, `check`, `sync` (`--project-config-path`, `--update`), `nextflow` (`--install/--uninstall/--print`) |
| `data` (`commands/data.py`) | `scan`, `process`, `join`, `push-images`, `versions`, `vacuum` (`--retention-hours`), `link list/create/resolve/delete`; `--json` on some |
| `dashboard` | `validate`, `import`, `export` (`--offline`, `--api`, `--overwrite`) |
| `template` | `export`, `compose` |
| `manifest from-table` | samplesheet/table → data manifest |
| `migrate --project` | `--server`, `--to-server`, `--mode`, `--dry-run`, `--overwrite`; admin on both sides (`commands/migrate.py:100-140`) |
| `backup` | `create` (`--include-s3-data`, `--s3-backup-prefix`, `--dry-run`), `list`, `validate`, `restore` (`--collections`, `--force`, `--allow-unverified`, `--skip-validation`); admins only (`commands/backup.py:52-352`) |
| `catalog` | `list`, `info`, `preview`, `gallery` (+ hidden `dev` sub-commands) |
| `version`, `commands` | `commands/standalone.py` |

### 1.3 Configuration and server selection
- Model `CLIConfig` (`depictio/models/models/cli.py:84-110`), `extra="forbid"`: `api_base_url` (regex-validated), `user` (`UserBaseCLIConfig` = `UserBase` + `token: TokenBase`), `s3_storage` (`S3DepictioCLIConfig`, credentials for direct Delta writes), `instance_label` (shown in admin monitoring), `remote_storage_options` (`ProjectS3Config`, read-only credentials for remote sources, deliberately separate from the write credentials).
- **One file per server**, no profile list inside a file. `--server` takes `local` (the `depictio local up` server) or a path to a CLI config file (`utils/server_target.py:19-33`, `SERVER_HELP`). Resolution order: `--server` → `$DEPICTIO_CLI_CONFIG_PATH` → `~/.depictio/CLI.yaml` → the local server. `migrate --to-server` defaults to `~/.depictio/CLI_remote.yaml`.
- Env overrides applied on top of the file: `DEPICTIO_CLI_TOKEN` → `user.token.access_token`, `DEPICTIO_CLI_API_BASE_URL` → `api_base_url` (`utils/common.py:317-341`). Either one set means "remote": without a file the command fails instead of falling back to `local` (`server_target.py:30-33`).
- The file is generated server-side (`POST /auth/generate_agent_config`, see the earlier harmonisation note) and contains the S3 secret.

### 1.4 HTTP client
- One process-wide `httpx.Client` created lazily, pool sized to the concurrency, closed `atexit` (`utils/common.py:33-56`). Synchronous; worker threads for parallel uploads/deletes.
- Headers (`generate_api_headers`, `common.py:59-101`): `Authorization: Bearer <JWT>`, `X-Depictio-CLI-Host` (hostname), `X-Depictio-CLI-Instance` (`instance_label`), `X-Depictio-CLI-Version`. The version header lets the server report CLI versions in use even with telemetry off.
- Retries hand-rolled in `utils/http_retry.py` (`request_with_retry`), deliberately without tenacity to keep the install small. Retries `408/425/429/500/502/503/504`; connect errors always (never delivered); read/write timeouts only for endpoints marked idempotent. The module documents which endpoints are idempotent (`POST /files/upsert_batch`, `/runs/upsert_batch` yes; `POST /deltatables/upsert` **no**, it appends a version).
- Timeouts set per call (60 s "cold-start safety net", 120 s for batches; `utils/api_calls.py`).
- API calls are free functions (`api_login`, `api_create_project`, `api_upsert_runs_batch`, `api_monitoring_ingestion_start/step/finish`…) in one 1.5 k-line module, taking `CLIConfig`. No generated client.
- Version check against the server: no explicit negotiation was found. The CLI sends its version; the ingestion monitoring payload carries `cli_version` (`api_calls.py:635-660`). Inference: compatibility is handled by keeping old routes and hidden option aliases.

### 1.5 Output, logging, telemetry
- Human output with Rich (`utils/rich_utils.py`, 834 lines: checked statements, section separators, Polars tables). Machine output: `--result-json FILE` on `ingest` (`run.py:135-181`: `status`, `project{name,id,url,locations}`, `dashboards[{title,id,url,status}]`, `template_id`, `composed`), never fails the run; `--json` on some `data` commands. Exit codes are meaningful for CI.
- Logging: stdlib logger `depictio-cli` (`cli/cli_logging.py:9`) plus the models' logger, same level (`depictio_cli.py:208-211`); colorlog.
- Telemetry (`cli/cli/utils/telemetry.py`, `depictio/telemetry/`): anonymous PostHog EU endpoint (`telemetry/constants.py:15`), events `cli.install` and `cli.command` with the command path rebuilt only from registered command names (no argv leaks), 2 s cap, skipped on Ctrl-C. Opt-out `DEPICTIO_TELEMETRY_ENABLED=false` or `DO_NOT_TRACK=1`; first-run notice; `DEPICTIO_TELEMETRY_DEPLOYMENT_KIND` set by Helm.

### 1.6 `depictio-cli` alias and Nextflow trigger
- `depictio/cli/pyproject.toml`: package `depictio-cli` = `dependencies = ["depictio==1.19.2"]`, both scripts `depictio` and `depictio-cli`, and a copy of the files older `depictio-cli` releases installed so an upgrade over them does not delete files now owned by `depictio`. `scripts/check_depictio_wheel.py` checks both wheels are consistent.
- Nextflow hook `depictio/cli/configs/nextflow/depictio.config`: `workflow.onComplete` runs `depictio-cli ingest` on `params.outdir`; params `depictio_enabled`, `depictio_template`, `depictio_project`, `depictio_attach`, `depictio_user`, `depictio_data_root`, `depictio_cli_executable` (name, absolute path or a container image); installed with `depictio config nextflow --install`. Clear warnings when the CLI is missing on the head job.

## 2. Shared models (`depictio/models/`)
- Layout: `models/models/*.py` (one module per domain: `users`, `projects`, `workflows`, `run_info`, `nextflow`, `snakemake`, `jobs`, `monitoring`, `branding`, `dashboards` (2.6 k lines), `data_collections` + `data_collections_types/`, `deltatables`, `files`, `links`, `comments`, `realtime`, `s3`, `cli`, `templates`…), plus helpers `models/config.py`, `logging.py`, `s3_access.py`, `local_access.py`, `validation/`, `yaml_serialization/`, `components/`. ~10.3 k lines in `models/models`.
- Shared by API, worker and CLI. The CLI wheel ships `depictio.models`, `depictio.api.v1.configs` (settings), `catalog`, `recipes`, `projects` templates (`depictio/cli/pyproject.toml` `packages`). CI job `cli-base-install.yaml` runs the CLI and models tests on the base install, so a server-only import on the CLI side fails in CI.
- Base classes (`models/models/base.py`): `PyObjectId(ObjectId)` with a Pydantic core schema (`:40`); `MongoModel` (`:70`) with `id`, `description`, `flexible_metadata`, `hash`, `extra="forbid"`, `from_mongo` / `mongo()` id conversion, description sanitising; `DirectoryPath`, `HashModel`. Beanie documents live server-side (`UserBeanie`…). Consequence: the models depend on `bson`, so the CLI's base install pulls `beanie` and `pymongo` (base dependencies, `pyproject.toml:15-34`).
- Validation conventions: `extra="forbid"` almost everywhere; regex validators (email, URL, JWT shape in `TokenData`); `validate_call` on helpers.
- Context switch: `DEPICTIO_CONTEXT` = `server` (default) or `cli` (`models/utils.py:17-20`). Models branch on it for path handling (`workflows.py:61,150`, `files.py:126`, `data_collections.py:91`, `image.py:113`), logging (`api/v1/configs/logging_init.py:31`) and the local-data policy (`settings_models.py:1204`). Note `workflows.py:150` compares with `"CLI"` (upper case) while others use `.lower() == "cli"`: an inconsistency.
- Settings: pydantic-settings classes in `depictio/api/v1/configs/settings_models.py`, one prefix each: `DEPICTIO_FASTAPI_`, `_VIEWER_`, `_MONGODB_`, `_S3_` (legacy `_MINIO_` still read, `:370-385`), `_AUTH_`, `_BOOTSTRAP_`, `_LOGGING_`, `_CACHE_`, `_CELERY_`, `_MULTIQC_`, `_REMOTE_`, `_LOCAL_DATA_`, `_JBROWSE_`, `_STRUCTURE_RESOLVER_`, `_BACKUP_` (`:103-1425`).
- OpenAPI: FastAPI serves `/openapi.json`. `scripts/extract_openapi.py` only downloads it from a running server for the docs site. **No generated clients**: no TS generation (no openapi-typescript/orval in any `package.json`); `packages/depictio-react-core/src/api.ts` holds ~255 hand-written exported types/interfaces; the Python CLI uses hand-written `api_*` functions.
- **Pluggable run-info readers** (`models/models/run_info.py:108-185`): `RunInfoReader` Protocol with `name`, `priority`, `footprint` (globs of files read), `markers` (globs only tested for existence; lets an `s3://` run be recognised from a sparse local copy), `read(run_dir) -> WorkflowRunInfo | None`. Registry `register_run_info_reader` (idempotent by name, sorted by priority); bundled connectors listed in `_CONNECTOR_MODULES` and imported lazily: Nextflow (`nextflow.py`) and **Snakemake** (`snakemake.py:93`, priority 50, reads config files and `.snakemake` conda envs, markers `.snakemake` + Snakefiles). Discovery is by module list, not entry points.

## 3. Packaging and deployment

### 3.1 Python package
- One distribution `depictio` (`pyproject.toml`, setuptools, version `1.19.2` static, `requires-python >=3.11`). **The base install is the CLI**; extras add the rest (`:8-14`): `[multiqc]`, `[server]` (FastAPI, Celery, Redis client, pymongo, Playwright, gunicorn…), `[local]` (`py-rattler`, fetches MongoDB/Redis/SeaweedFS from conda-forge), `[saml]` (`python3-saml`, `defusedxml`), `[watch]`, `[dev]`. Dependency group `worker-reload` (watchdog) for the worker image only.
- Even the base CLI is heavy (polars ×2 runtimes, deltalake, pandas, boto3, plotly): ~0.9 GB env, 11 s cold (`dev/design/local-server-profile.md:69`).
- Scripts `depictio` and `depictio-cli` (`:128-133`).
- Wheel: `include-package-data = false` + explicit `package-data` globs (`viewer/dist/**/*` — the React build, nf-core templates, iris/penguins seeds incl. `.db_seeds`, catalog, Nextflow config) and `exclude-package-data` (sourcemaps, reference datasets) (`:147-215`). `scripts/check_depictio_wheel.py`: fails above **15 MB** or when required files are missing (`viewer/dist/index.html`, seeds, rnaseq template).
- Version: `VERSION` file at the root + `depictio/version.py` falls back to `importlib.metadata.version("depictio")` from a wheel. Bumps with `bump2version` via `bump-with-helm.sh` (also pins `docker-compose.yaml`, sets the Helm chart version to `YYYYMMDD.N`, `uv lock`). App versions semver incl. betas (`1.18.0-b1`).
- uv everywhere (`uv.lock`, `uv tool install`, `uvx`); `pixi.toml` is a developer alternative (Docker-free infra); py-rattler replaces pixi for end users.
- `uv` sources point `plotly-upset` / `plotly-complexheatmap` at `packages/` (editable); published to PyPI by `publish-pypi.yaml` with trusted publishing (depictio-cli still uses a token).

### 3.2 Images
- `docker-images/Dockerfile.api` (node 20 stage for the catalog preview, then `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` pinned by digest, `USER depictio`, port 8058, `run_fastapi.sh` = gunicorn), `Dockerfile.worker` (same base, `run_celery_worker.sh`: `DEPICTIO_CELERY_WORKERS` 4, `MAX_TASKS_PER_CHILD` 50, `QUEUES`, `PREFETCH` 1), `Dockerfile.viewer` (node build → `nginx-unprivileged:1.27-alpine`, port 8080, `nginx.conf.template`), `Dockerfile.cli` (ENTRYPOINT `depictio-cli`). Images copy the source tree, they are not built from the wheel (`local-server-profile.md:155-162`).
- `build-images.yaml`: four images to `ghcr.io/depictio/depictio-{api,worker,viewer,cli}`, multi-arch resolution job, smoke checks (`/openapi.json` 200).

### 3.3 Docker Compose
- `docker-compose.yaml`: `mongo:8.0.14` (port 27018), `redis:8.2.1`, **`s3` = `chrislusf/seaweedfs:4.46` `weed mini`** (S3 on 9000, admin UI off, volume `seaweedfs_data`, `minio` network alias kept), `depictio-backend` (127.0.0.1:8058), `depictio-viewer` (5080), `depictio-celery-worker`, profile `ingestion` → `depictio-ingestion-worker` (its default tag is still `1.14.0`, stale vs 1.19.2 — observation).
- `docker-compose.dev.yaml` adds `depictio-viewer-dev` (Vite HMR), profile `ci` (nginx viewer), profile `monitoring` → **Flower** (`mher/flower:2.0`, broker `redis://redis:6379/1`, port 5555).
- Variants `docker-compose/`: `no-minio`, `minio-legacy` (old MinIO kept only to migrate from), `backup-minio` (a second SeaweedFS as backup target), `bench`, `e2e-manifest`. Migration tool `scripts/migrate_minio_to_seaweedfs.py` + `docs/migrate-minio-to-seaweedfs.md`.
- Watcher: `deploy/docker-compose.watcher.yaml` (`depictio-cli watch --server /config/CLI.yaml …`).
- Local → Compose hand-over: `depictio local export` (`depictio/cli/cli/local_compose.py`) copies MongoDB and SeaweedFS data + keys, writes compose + override + `.env`; CI job `local-to-compose`.

### 3.4 Helm (`helm-charts/depictio/`)
- `Chart.yaml`: `version: "20261023.1"` (date-based), `appVersion: "1.19.2"`; pushed as an OCI chart to GHCR (`repackage-helm-chart.yaml`, `tag-helm-chart.yaml` add tags such as the app version).
- Templates: `deployments.yaml`, `services.yaml`, `configmaps.yaml`, `secrets.yaml`, `pvcs.yaml`, `ingress.yaml`, `httproutes.yaml` + `snippetsfilters.yaml` (Gateway API / NGINX Gateway Fabric), `mongo-init-job.yaml`, `mongo-operator.yaml` (Percona PSMDB operator optional), `poddisruptionbudget.yaml`, `wipe-job.yaml`, `NOTES.txt`.
- Values top-level keys: `persistence`, `secrets`, `demo`, `mongo` (`useOperator`, `auth.enabled`, pinned image), `redis`, `s3` (SeaweedFS `4.46`, `service.httpPort: 9000`, `adminPort: 23646`, admin UI off by default; legacy `minio:` merged in, k8s object names keep `-minio`), `backend`, `celery`, `viewer`, `podDisruptionBudget`, `gateway`, `ingress` (`ingressClassName: nginx`), init-container images.
- `kubernetes/multiline-secrets.yaml`: example Secret with `AUTH_PUBLIC_KEY`, `AUTH_PRIVATE_KEY`, `AUTH_TMP_TOKEN`.
- `test-and-package-helm-chart.yaml` deploys the chart in CI and probes endpoints; `deploy-embl-selfhosted.yaml` deploys to EMBL (self-hosted runner, environments `trec-demo`, `demo`).

### 3.5 CI and quality gates relevant to packaging
- `publish-pypi.yaml` (tag → depictio, depictio-cli, plotly-upset, plotly-complexheatmap), `release.yaml`, `build-images.yaml`, `local-server-smoke.yaml` (wheel size/contents, `uvx … local up`, Playwright, linux-64/aarch64/osx-arm64), `cli-base-install.yaml`, `backup-compat-cross-version.yaml` (weekly: restore a backup made by the previous stable image into the current one), `minimal-deploy.yaml`, `telemetry-ci.yaml`.
- `scripts/security_audit_compose.sh` and `security_audit_helm.sh`: PASS/FAIL/SKIP checks against a static config or a live stack.

## 4. LabID (EMBL, MODIS)
- Public repositories at gitlab.com/lab-integrated-data: `labid-server`, `labid-ui`, `labid-lib`, `labid-cli`, `labid-user-docs` (all active October 2026). Docs: grp-gbcs.embl-community.io/labid-user-docs; site labintegrateddata.org; MIT licence for lib and CLI. Neither is on PyPI under `labid*` (checked `labid`, `labid-client`, `labid-cli`, `pylabid`, `labid-sdk`: 404); installed from git tags.
- **Two-layer pattern, same as what Spectio needs**:
  - `labidlib` (`src/labidlib/`): `api/client.py` `LabidClient` (requests Session, `get/post/patch/put/put_file/delete/list/list_all/resolve/search/fetch`), `api/manager.py` `LabidManager`, `api/models.py` + `core/models.py` (Pydantic 2), `api/exceptions.py`, `core/assaysniffer/registry.py` (`SnifferRegistry`, plugins loaded from directories added to `sys.path`), `core/workflows/workflowrun_sniffers.py` (`NextflowRunSniffer`, `SampleSheetWorkflowRunSniffer`, `GenericWorkflowRunSniffer`) and `workflowruncrate_sniffers.py` (`WorkflowRunCrateSniffer`, `NextflowRunCrateSniffer` for nf-prov crates, `GalaxyRunCrateSniffer`), `utils/rocrate_utils.py`. Depends on `rocrate`, `requests`, `PyJWT`, `pydantic`, `fsspec`, `universal_pathlib`, bioio readers.
  - `labidcli` (`labidcli/__main__.py`): Typer app `labid` with modules `assays`, `config`, `create`, `export`, `manage`, `get`, `register`, `validate`, `job`, `transfer`; `--version` callback; outputs JSON meant for `jq` (README examples).
- API style: REST under `<server>/api/` (example `https://stocks.embl.de`, LabID's former name STOCKS). Auth: `POST token-auth/` with username + password returns a token; the client sends `Authorization: Bearer <jwt>` when the token decodes as a JWT, else `Authorization: Token <token>` (`client.py:251-284`). Inference: Django REST Framework (the `Token` scheme and `token-auth/` are DRF conventions).
- Config: `~/.labid/labidapi.yml`, **several servers in one file keyed by URL** with a `default` key (`{"default": url, url: {username, unix_group, token}}`, `labidcli/config.py:260-294`); `labid config setup | show | clean | switch --server-api-url | refresh`; global `labidcli.ini` (institution, sniffer plugin dirs) and `log_config.ini`.
- Versions `YY.MM.N` (`v26.09.2`); CLI pins the lib by git tag.
- Sources: [LabID on RO-Crate](https://www.researchobject.org/ro-crate/labid), [MODIS](https://www.embl.org/groups/modis), [labid-cli](https://gitlab.com/lab-integrated-data/labid-cli), [labid-lib](https://gitlab.com/lab-integrated-data/labid-lib).

## 5. Reusable for Spectio

### 5.1 A shared client foundation (new small package, proposed name `embl-cli-core` or `bioplatform-client`; inference: needs agreement with depictio and MODIS)
- **Server profiles**: LabID's single file keyed by URL with `default` beats depictio's one-file-per-server. Proposal: `~/.config/<app>/servers.yaml` with named profiles (`default`, `local`, `embl-prod`…), each `url`, `token` (or `token_cmd` / keyring), `label`; `--server <name|url|file|local>`; env `<APP>_SERVER`, `<APP>_TOKEN`, `<APP>_API_URL`, `<APP>_CONFIG`. Read depictio's `CLI.yaml` and LabID's `labidapi.yml` as import sources.
- **HTTP client**: one `httpx` client with depictio's policy as is (retry only idempotent calls, the status list, connect errors always, per-call timeouts), plus `Idempotency-Key` so POSTs become retryable (Spectio API rule), RFC 9457 error parsing, cursor pagination iterator, identity headers (`X-<App>-Client-Version`, `-Host`, `-Instance`) and a server-version check against `GET /version` with a warning on mismatch.
- **Auth helpers**: bearer JWT, DRF `Token`, provisioning-key exchange (depictio `POST /auth/provision_user`), device-code or browser login for OIDC later.
- **Output conventions**: Rich for humans; `--json` on every read command and `--result-json FILE` on long commands (depictio's schema shape: `status`, ids, URLs); meaningful exit codes; `-v/-vv/--log-level`; JSON suitable for `jq` (LabID).
- **Telemetry**: copy depictio's design (command path from the command tree only, `DO_NOT_TRACK`, first-run notice, 2 s cap), off by default for institutional installs (inference).
- **Help layout**: Typer + `rich_markup_mode="rich"` + panels declared in one dict; hidden aliases with rename notes.

### 5.2 Models to share or align
- `WorkflowRunInfo` + `RunInfoReader` Protocol (depictio) and LabID's `NextflowRunSniffer` / `NextflowRunCrateSniffer` parse the same nf-core `pipeline_info` / `.nextflow.log` / nf-prov crates. A shared "run directory provenance" package (readers for Nextflow, Snakemake, WRROC crates) would serve all three tools. Expose readers through entry points (`<pkg>.run_info_readers`) instead of a hard-coded module list.
- Identity and tenancy shapes: `UserBase`, `Group` (`users_ids`, `admin_ids`, `pi_id`, `sso_managed`), `Permission` (owners/editors/viewers + group_*), `TokenBase`, `BrandTheme` — define Spectio's API schemas field-compatible (names, enums), not by importing depictio's `MongoModel` (ObjectId/bson dependency).
- Pipeline id `<org>/<name>/<version>` and the `--result-json` / `--provenance-file` contracts already used by depictio's ingest.

### 5.3 Packaging patterns to copy
- Base install = CLI, extras = server/local; `-cli` alias package depending on the main one for discoverability.
- Viewer `dist/` in the wheel, explicit package-data globs, wheel size and required-files check in CI.
- `<app> local up/down/status/open/wipe/export` with sticky ports, `state.json` PIDs with start times, owner-only home, `export` to a Compose directory (depictio's `local export`) — Spectio's equivalent is simpler (SQLite + files, no external binaries).
- CI: base-install test job, cross-version backup restore job, local-server smoke on three platforms, local→Compose hand-over job, security audit scripts for Compose and Helm.
- Helm: OCI chart on GHCR, `s3:` values with legacy key merge, Gateway API option, PDB, init jobs; images pinned by digest, non-root, `nginx-unprivileged`.
- Nextflow `onComplete` hook pattern for observed runs (Spectio: generate it from the runner rather than asking users to install it).

### 5.4 Things to avoid
- Heavy base CLI (~0.9 GB): keep `spectio`'s client side to httpx + pydantic + typer + rich; data libraries in extras.
- Models tied to the storage layer (`MongoModel`, `PyObjectId`) and `DEPICTIO_CONTEXT` branches inside models (with an upper/lower-case inconsistency): keep client models storage-agnostic and pass context explicitly.
- Hand-written API functions and hand-written TS types drifting from the server: generate the Python and TypeScript clients from OpenAPI in CI.
- A config file carrying the S3 root secret (`generate_agent_config`): Spectio tokens only, scoped.
- Plugins loaded from directories put on `sys.path` (LabID sniffers) or a hard-coded module list (depictio readers): use entry points.
- Images built from the source tree rather than the wheel (depictio's choice for reference data): Spectio builds images from the published wheel.
- Date-based chart versions decoupled from app versions make support harder to read (inference); prefer chart semver + `appVersion`.
