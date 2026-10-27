# Spectio — command-line interface and libraries shared with depictio and LabID

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)
Companion docs: [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) (packages, plugins), [`admin-and-operations.md`](admin-and-operations.md) (admin commands), [`api-and-data-model.md`](api-and-data-model.md) (API rules), [`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md).

Sources:
- **depictio:** code audit of v1.19.2 ([`research/depictio-cli-packaging.md`](../research/depictio-cli-packaging.md)).
- **LabID:** the public repositories `labid-lib` and `labid-cli` on gitlab.com/lab-integrated-data, read through the GitLab API on 2026-10-25.

## 0. Decisions in brief

1. **One CLI, `spectio`, for users, scripts, CI, robots and admins.** It covers the whole API: launch, monitor, review, export, administer. JSON output on every command means LIMS scripts and LabID-style pipelines can drive it without writing HTTP code.
2. **Three small libraries shared by depictio, Spectio and LabID.** These are working names; the two other teams need to agree.
   - **client core:** server profiles, login, HTTP client, errors, output;
   - **shared models:** identity, tenancy, branding, references, events;
   - **run-directory readers:** Nextflow, Snakemake, RO-Crate.

   Each tool keeps its own CLI and API, but they behave the same and exchange the same objects.
3. **The base install is light.** `pip install spectio` is the CLI, the Python client and the runner: the dependencies on the allow-list of §6 (httpx, pydantic, typer, rich and a few small ones), and nothing else. The OS keyring is an optional extra (`spectio[keyring]`), because `keyring` on Linux pulls `SecretStorage` and `cryptography` (keyring 25.7.0 requires `SecretStorage>=3.2` on Linux and `jeepney`; secretstorage 3.5.0 requires `cryptography>=2.0`; PyPI metadata, 2026-10-26) and needs a D-Bus Secret Service, which HPC login nodes usually lack **[to be validated on EMBL login nodes]**; without it, tokens come from `file:` or `env:`. CI fails if the environment grows past 80 MB. depictio's base CLI pulls polars, deltalake and pandas and weighs about 0.9 GB. That is a lesson to learn from, not a pattern to copy.
4. **Clients are generated, not hand-written.** The Python client and the TypeScript client (UI, embedded elements) are generated from the OpenAPI schema in CI. A thin hand-written layer adds pagination, idempotency, waiting and streaming. depictio's 255 hand-written TypeScript types and 1,500-line `api_calls.py` show how the two sides drift otherwise.

## 1. What depictio and LabID do today

| Concern | depictio CLI | LabID (`labidcli` + `labidlib`) | Spectio choice |
|---|---|---|---|
| Framework | Typer, Rich help, help panels Get started / Projects and data / Administration / Reference, hidden aliases for renamed commands | Typer, JSON output meant for `jq` | Typer, the same panel scheme, JSON everywhere |
| Servers | one YAML file per server (`~/.depictio/CLI.yaml`); `--server local\|<file>`; env `DEPICTIO_CLI_TOKEN`, `DEPICTIO_CLI_API_BASE_URL` | **one file with several servers keyed by URL plus `default`** (`~/.labid/labidapi.yml`); `labid config setup\|show\|switch\|refresh` | LabID's model: one file, named profiles, a default |
| Auth | Bearer JWT; named long-lived tokens; provisioning key for pipelines | `POST token-auth/` with username and password; then `Bearer` (JWT) or `Token` (DRF) | Bearer; OIDC device code for SSH/HPC; token paste; depictio token exchange |
| HTTP | one httpx client; hand-rolled retries on 408/425/429/500/502/503/504 (`depictio/cli/cli/utils/http_retry.py:50`, depictio `0d1aa0a`); connect errors always retried; timeouts retried only on endpoints marked idempotent; headers with CLI version, host, instance | requests session, `list_all` pagination | depictio's policy, plus `Idempotency-Key` so POSTs become safe to retry, RFC 9457 errors, cursor pagination |
| Machine output | `--result-json FILE` on `ingest` (status, IDs, URLs); `--json` on some commands; meaningful exit codes | JSON by default | `--json` on every command, `--result-json FILE` on long ones, documented exit codes |
| Version check | the CLI sends its version; no negotiation | — | `GET /version` at start; the window and the behaviour are in [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §12 (exit code 6 outside it) *(assumed — pending Thomas, inbox #28)* |
| Telemetry | PostHog, opt-out, `DO_NOT_TRACK`, command path only | — | same ethics and the same opt-out default ([`telemetry-and-analytics.md`](telemetry-and-analytics.md) §0.4) |
| Run-directory readers | `RunInfoReader` protocol (name, priority, footprint, markers, `read`), Nextflow and Snakemake, module list | sniffers for Nextflow runs, samplesheets, nf-prov / Galaxy RO-Crates, loaded from directories on `sys.path` | one shared package, readers through entry points, plus a Snakemake run-crate reader (§4) *(assumed — pending Thomas, inbox #28)* |

## 2. The `spectio` command tree

Help panels follow depictio's scheme. Every command accepts `--server`, `--json`, `-v/-vv`, `--log-level` and `--no-color`. Write commands also accept `--dry-run` where it makes sense and `--yes` for non-interactive use.

**Names and IDs.** Options that take a project, an environment or a workflow (`--project`, `--env`, `launch`) accept a prefixed ID or a name. A name is resolved through the list endpoints: one match is used; several matches stop with exit code 2 and list the candidates with their IDs; no match gives exit code 4. *(assumed — pending Thomas, inbox #29)*

| Panel | Command | Sub-commands and key options |
|---|---|---|
| **Get started** | `init` | create the data directory, config, first user and project `default` |
| | `serve` | `--role all\|api\|worker`, `--with-runner`, `--safe-mode`, `--no-ui`, `--tls` (HTTPS without a reverse proxy; [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.2) *(assumed — pending Thomas, inbox #28)* (needs `spectio[server]`) |
| | `local` | `up`, `open`, `status`, `down`, `wipe`, `export --out DIR` (hand-over to Compose, as in depictio) |
| | `login` / `logout` / `whoami` | `--server`, `--device` (OIDC device code), `--token -` (stdin), `--with-depictio` (exchange a depictio token when the server trusts depictio), `--print-link` (hand-over magic link; [`authentication-and-access.md`](authentication-and-access.md) §2). `login` also sets up the engines once, by running `engine nextflow config --install` and `engine snakemake profile --install`; the credential it writes follows the ingest contract ([`api-and-data-model.md`](api-and-data-model.md) §14, pending inbox #11) *(assumed — pending Thomas, inbox #28)* |
| | `server` | `add <name> <url>`, `list`, `use <name>`, `remove`, `import --from depictio\|labid` |
| | `runner` | `connect <server> --token …`, `run` (the foreground daemon; the command the systemd unit `spectio-runner@.service` executes, [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §6) *(assumed — pending Thomas, inbox #28)*, `status`, `list`, `drain`, `logs` |
| **Runs and review** | `run` | `launch <org>/<name>/<version>` (also accepts `<org>/<name>@<version>` as input; output always prints the canonical form *(assumed — pending Thomas, inbox #29)*; `--env`, `--params FILE`, `--samplesheet FILE`, `--project`, `--profile`, `--gates spectio.yml`, `--external-ref labid:sample/123`, `--wait`, `--until-gate`, `--idempotency-key`); `list` (`--state`, `--workflow`, `--external-ref`); `show`; `logs --follow`; `tasks`; `cancel`; `relaunch` (`--resume`, `--from-stage <stage id>`, `--fresh`, `--samplesheet v2.csv`, `--params`; maps to `:relaunch`, [`api-and-data-model.md`](api-and-data-model.md) §5.1; always a new child run, the parent stays terminal) *(assumed — pending Thomas, inbox #32)*; `params <id> [--diff <other>]` (mirrors `GET /runs/{id}/params`; `--diff` shows the changed values against another run); `adopt <launch dir>`; `watch` |
| | `gate` | `list --assigned-to me`; `show`; `decide <gate> approve\|apply\|stop\|go-back --stage <stage id>` (stage ids: [`api-and-data-model.md`](api-and-data-model.md) §7 `run_stages`) *(assumed — pending Thomas, inbox #40)* (item options `--keep`, `--exclude T1,C4`, `--redo`, `--flag`; `--rule "completeness>50,contamination<10"`; `--comment`); `--reject` is accepted as an alias of `stop`; there is no `--hold` *(assumed — pending Thomas, inbox #29)*; sends the gate etag as `If-Match`; `apply` and `go-back` exit with the code of problem `not-in-this-version` on a server without change sets ([`api-and-data-model.md`](api-and-data-model.md) §4.1) *(assumed — pending Thomas, inbox #32)*; `signal` (robots and agents add evidence); `changes` (change set, samplesheet v2 diff) |
| | `workflow` | `list`, `show`, `import nf-core/rnaseq --versions 3.27.0`, `validate spectio.yml` (against the JSON Schema of [`checking-scenarios.md`](checking-scenarios.md) §12, shipped in `spectio-sdk`) *(assumed — pending Thomas, inbox #29)*; it also rejects a rule matched by two stages ([`checking-scenarios.md`](checking-scenarios.md) §12.3), `schema` |
| | `env` | `list`, `show`, `test` (dry submit on the cluster) |
| | `project` | `list`, `create`, `use`, `share --user\|--group … --role owner\|editor\|viewer [--launcher] [--reviewer]`, `export`, `import` |
| **Data and integrations** | `export` | `rocrate <run> --out crate.zip`, `report <run>` |
| | `handoff` | `depictio <run>` (runs `depictio-cli ingest` as the sink plugin would), `labid <run>` |
| | `engine` | `nextflow config [--install]` (prints, or with `--install` writes, the `nf-spectio` plugin config for runs started from a terminal, like depictio's `config nextflow --install`), `snakemake profile [--install]` (the same for `--logger spectio`) *(assumed — pending Thomas, inbox #28)* |
| | `events` | `tail --type spectio.gate.*`, `replay` |
| **Administration** | `user` | `list`, `create`, `deactivate`, `set-admin`, `import --from depictio` ([`depictio-ecosystem-reuse.md`](depictio-ecosystem-reuse.md) §2, item 1) *(assumed — pending Thomas, inbox #28)* |
| | `group` | `list`, `create`, `add`, `remove`, `set-admin`, `set-pi` |
| | `service-account` | `create`, `list`, `rotate`, `revoke` |
| | `token` | `create --name --expires`, `list`, `revoke` |
| | `auth` | `method list`, `method enable oidc --issuer … --client-id …`, `method enable saml …`, `method disable <method>`, `method test <method>` ([`authentication-and-access.md`](authentication-and-access.md) §1, §5) *(assumed — pending Thomas, inbox #28)* |
| | `admin` | `background-tasks list\|show\|retry\|cancel` (the background-task ledger; `run tasks` lists engine tasks) *(assumed — pending Thomas, inbox #29)*, `logs (--level --source --run --follow)`, `logs capture-level <LEVEL>` ([`admin-and-operations.md`](admin-and-operations.md) §3.4, `PUT /logs/capture-level`), `health`, `maintenance on\|off\|status`, `announcements show\|set\|clear` (admin §4.4) *(assumed — pending Thomas, inbox #28)*, `cleanup run <job>`, `settings get\|set` |
| | `backup` | `create (--include db,files,keys,secrets --destination --encrypt)`, `list`, `verify`, `download`, `restore (--dry-run default, --force)` *(assumed — pending Thomas, inbox #24)*, `prune`, `schedule show\|set` (verbs aligned with depictio's `backup`) |
| | `migrate` | `project <name> --to-server <profile> (--mode all\|metadata\|files, --overwrite, --dry-run)` (as depictio's `migrate --project`), `database --to postgresql://…`, `storage --to s3://…` |
| | `db` | `status`, `upgrade`, `history` |
| | `branding` | `show`, `export`, `import`, `reset` |
| | `plugin` | `list`, `install`, `new --kind --name`, `doctor`, `instance list\|add\|update\|remove` (admin §5, `/plugin-instances`) *(assumed — pending Thomas, inbox #28)* |
| | `ai` | `serve --env … --model … --gpus N --idle-stop 2h` (starts a model server as a GPU job through the runner and registers it as an endpoint; [`ui-spec.md`](ui-spec.md) §4.9), `endpoint list\|add\|remove`, `limits show\|set` *(assumed — pending Thomas, inbox #29)* |
| **Reference** | `config` | `show --effective` (with sources, secrets masked), `path` |
| | `doctor` | local checks (SQLite, disk, the data directory's file-system type and host pin, Python, plugins, server reachability, clock, proxy and CA bundle *(assumed — pending Thomas, inbox #12)*; full list in [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.3) |
| | `version`, `commands`, `completion` | |

**Exit codes.** Exit codes follow the problem catalogue of [`api-and-data-model.md`](api-and-data-model.md) §4.1.

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | the operation failed (for `run launch --wait`: the run failed) |
| 2 | usage error |
| 3 | not authenticated or not allowed |
| 4 | not found |
| 5 | conflict (idempotency key reused with a different body, `If-Match` failed) |
| 6 | client and server versions incompatible |
| 10 | `--until-gate` stopped at an open gate |
| 130 | interrupted |

**Examples.**

```bash
# a LIMS or CI job: launch, wait, keep the IDs
spectio run launch nf-core/rnaseq/3.27.0 --env embl-slurm --project liver-tc \
  --params params.yaml --samplesheet samples.csv --external-ref labid:study/77 \
  --idempotency-key "labid-study-77-v1" --wait --result-json run.json

# a reviewer on a phone-free day: what is waiting for me
spectio gate list --assigned-to me --json | jq -r '.[] | "\(.id) \(.run.name) \(.title)"'
spectio gate decide gate_01JB… apply --exclude T1 --comment "T1 rRNA 14.8 %"

# an admin over SSH
spectio admin health --json | jq '.checks[] | select(.status != "ok")'
spectio backup create --include db,files,keys --destination seaweedfs
```

**Plugins extend the CLI.** A `spectio.cli` entry point adds a sub-command group (e.g. `spectio labid …` from `spectio-plugin-labid`). It appears in its own help panel, "Plugins".

## 3. Configuration: one file, named servers

```yaml
# ~/.config/spectio/servers.yaml   (0600)
default: embl
servers:
  local:
    url: http://127.0.0.1:8080
    auth: single                 # single-user server on this machine, no token
  embl:
    url: https://platform.embl.de/spectio
    label: EMBL production
    token: keyring:spectio/embl  # needs spectio[keyring] (§0.3); or file:…, env:…, or the token itself
    depictio: https://platform.embl.de/depictio   # optional: enables --with-depictio and handoff
```

- **Server resolution.** Order: `--server <name|url|file|local>`, then `SPECTIO_SERVER`, then `default`, then `local` if a local server is running.
- **Overrides.** `SPECTIO_TOKEN` and `SPECTIO_API_URL` work without a file, for CI.
  - Unlike depictio, setting only one of them is valid when the other can be derived. For example, `SPECTIO_API_URL` with `auth: single` on localhost needs no token.
- **Import.** `spectio server import --from depictio` reads `~/.depictio/CLI.yaml` (URL, label). `--from labid` reads `~/.labid/labidapi.yml`, all servers. Tokens are never copied between tools: the user signs in again, or uses `--with-depictio`.
- **No storage secret in the file.** depictio's `CLI.yaml` carries the S3 write secret. Spectio's CLI never needs one, because files go through the API or are read by the runner next to the data.

## 4. Shared libraries (depictio · Spectio · LabID)

Working names below. Two shared names need agreement with MODIS, the team behind LabID: the PyPI prefix and the GitHub organisation. A neutral prefix that is free on PyPI today is `bioplatform-`.

| Package | Content | depictio | Spectio | LabID |
|---|---|---|---|---|
| **`bioplatform-client`** (client core) | server profiles file and resolver; token sources (file, env, command; keyring through the optional `[keyring]` extra, §0.3); login flows (password → token, OIDC device code, token exchange); httpx client with depictio's retry policy (408/425/429/500/502/503/504, §1) + `Idempotency-Key`; RFC 9457 errors → typed exceptions; cursor and page iterators; identity headers (`X-<App>-Client-Version`, `-Host`, `-Instance`); `/version` check; Rich / `--json` / `--result-json` output helpers; Typer app factory with help panels and renamed-command aliases; `-v/--log-level`; telemetry consent helper (`DO_NOT_TRACK`) | replaces `utils/common.py`, `http_retry.py`, `server_target.py` | base of `spectio` CLI and client | could replace `LabidClient` session handling |
| **`bioplatform-models`** (shared schemas, storage-agnostic, string IDs, no bson) | `UserRef`, `Group` (members, admins, `pi`, `pending_pi_email`, `sso_managed`), `Role` (owner / editor / viewer), `Grant`, `TokenInfo`, `BrandTheme` + presets + `merge_brand_themes` / `resolve_brand_theme` (moved from depictio), `PipelineRef` (`<org>/<name>/<version>`), `ExternalRef` (`labid:sample/123`, `depictio:project/…`, `spectio:run/…`), CloudEvent envelope, `Problem` (RFC 9457), `Page[T]` | API schemas become field-compatible; branding model moves here | API schemas built on them | references and run objects |
| **`bioplatform-runinfo`** (run-directory provenance) | depictio's `RunInfoReader` protocol (`name`, `priority`, `footprint`, `markers`, `read(run_dir) → WorkflowRunInfo`); readers for Nextflow (`pipeline_info`, `.nextflow.log`, trace), Snakemake (`.snakemake`, configs), Workflow Run RO-Crates (nf-prov, Galaxy, from LabID's sniffers; plus a new reader for Snakemake run crates written by `snakemake-report-plugin-rocrate`, a WRROC 0.5 Provenance Run Crate on RO-Crate 1.1, see [`synthesis.md`](synthesis.md) §7quinquies) *(assumed — pending Thomas, inbox #28)*; entry-point group `bioplatform.runinfo_readers` | template auto-selection in `ingest` | adopting observed runs, RO-Crate export, depictio hand-off | registering workflow runs |

**Rules for the shared packages.**
- Pure Python. The only dependencies are pydantic, httpx and typer/rich (client only).
- Semver with deprecation windows.
- Each package ships a conformance suite, so each app can test against it.
- They contain no server code and no database code.
- **Transition.** Until the packages exist, Spectio keeps the same modules under `spectio._shared` with the same public names. Extracting them later is then a rename.

## 5. Python and TypeScript clients

- **Python: `spectio.client`.**
  - The generated part is built from `/api/v1/openapi.json` with `openapi-python-client`, checked in CI, then wrapped:

```python
from spectio.client import Spectio

sp = Spectio.from_profile("embl")              # same resolution as the CLI
run = sp.runs.launch(
    workflow="nf-core/rnaseq/3.27.0", environment="embl-slurm", project="liver-tc",
    params={"aligner": "star_salmon"}, samplesheet="samples.csv",
    external_refs=["labid:study/77"], idempotency_key="labid-study-77-v1",
)
for event in sp.events.stream(run=run.id, types=["spectio.gate.opened", "spectio.run.*"]):
    ...
run.wait(until="gate")                          # or "end"
```

- **TypeScript: `@spectio/client`.**
  - Generated with `openapi-typescript` plus a small fetch wrapper.
  - The wrapper has two modes, both with a configurable `apiBase` (depictio hard-codes `/depictio/api/v1`; here it is configurable so co-hosting under `/spectio` works):
    - `session`: same origin, the HttpOnly session cookie and a CSRF header on writes ([`authentication-and-access.md`](authentication-and-access.md) §3); no token is ever readable by JavaScript; used by the web UI.
    - `bearer`: an embed token or a host plugin's token, with refresh on 401 and retry as depictio's `authFetch` does; used by the embeddable elements and host plugins (LabID).

## 6. Packaging of the CLI

| Install | Gives | Size target |
|---|---|---|
| `uv tool install spectio` | CLI + Python client + runner | < 80 MB environment, CI-checked |
| `uv tool install --managed-python "spectio[server]"` | + server (FastAPI, SQLAlchemy, Alembic, bundled UI) | — |
| `spectio[keyring]` | OS keyring token source (adds `cryptography`, needs a D-Bus Secret Service; §0.3) | — |
| other extras | backends, check bindings, keyring: the list is in [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.3 *(assumed — pending Thomas, inbox #29)* | — |
| `spectio-cli` | alias package that depends on `spectio`, for discoverability (as `depictio-cli`) | — |

**Base-install allow-list.** The base `spectio` package depends only on `spectio-sdk`, pydantic, pydantic-settings, httpx, typer, rich, a YAML parser (for `servers.yaml`, §3), and a WebSocket client only if the runner transport needs one ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §7.7, pending inbox #12). The runtime dependencies of the generated client (`openapi-python-client`, §5) must fit this list **[to be validated]**. Everything else is an extra: `spectio[keyring]` for OS-keyring token storage (§3) and `spectio[checks]` for heavy check bindings (MultiQC, anndata; [`checking-scenarios.md`](checking-scenarios.md) §11.1). Copier runs through `uvx copier` and is not a dependency. The < 80 MB environment check stays the testable rule; the base-install job and import-linter enforce this list.

- **The runner ships in the base package**, with the built-in engines and launchers as modules ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §6) *(assumed — pending Thomas, inbox #29)*. Its dependencies are the CLI's, so a login node needs one `uv tool install spectio`, and the server extras never land on a cluster.
- **CI checks, borrowed from depictio:**
  - a base-install job that runs the CLI tests without server extras, so a server-only import in client code fails, on every supported Python and Linux architecture ([`dev-environment-and-testing.md`](dev-environment-and-testing.md) §11) *(assumed — pending Thomas, inbox #26)*;
  - a wheel size and contents check;
  - the local → Compose hand-over test;
  - a test that every `/admin/*` operation of the OpenAPI document maps to a CLI command ([`admin-and-operations.md`](admin-and-operations.md) §0, item 2) *(assumed — pending Thomas, inbox #28)*.
