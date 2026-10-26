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
3. **The base install is light.** `pip install spectio` is the CLI, the Python client and the runner: httpx, pydantic, typer, rich and nothing else. CI fails if the environment grows past 80 MB. depictio's base CLI pulls polars, deltalake and pandas and weighs about 0.9 GB. That is a lesson to learn from, not a pattern to copy.
4. **Clients are generated, not hand-written.** The Python client and the TypeScript client (UI, embedded elements) are generated from the OpenAPI schema in CI. A thin hand-written layer adds pagination, idempotency, waiting and streaming. depictio's 255 hand-written TypeScript types and 1,500-line `api_calls.py` show how the two sides drift otherwise.

## 1. What depictio and LabID do today

| Concern | depictio CLI | LabID (`labidcli` + `labidlib`) | Spectio choice |
|---|---|---|---|
| Framework | Typer, Rich help, help panels Get started / Projects and data / Administration / Reference, hidden aliases for renamed commands | Typer, JSON output meant for `jq` | Typer, the same panel scheme, JSON everywhere |
| Servers | one YAML file per server (`~/.depictio/CLI.yaml`); `--server local\|<file>`; env `DEPICTIO_CLI_TOKEN`, `DEPICTIO_CLI_API_BASE_URL` | **one file with several servers keyed by URL plus `default`** (`~/.labid/labidapi.yml`); `labid config setup\|show\|switch\|refresh` | LabID's model: one file, named profiles, a default |
| Auth | Bearer JWT; named long-lived tokens; provisioning key for pipelines | `POST token-auth/` with username and password; then `Bearer` (JWT) or `Token` (DRF) | Bearer; OIDC device code for SSH/HPC; token paste; depictio token exchange |
| HTTP | one httpx client; hand-rolled retries on 408/425/429/5xx; connect errors always retried; timeouts retried only on endpoints marked idempotent; headers with CLI version, host, instance | requests session, `list_all` pagination | depictio's policy, plus `Idempotency-Key` so POSTs become safe to retry, RFC 9457 errors, cursor pagination |
| Machine output | `--result-json FILE` on `ingest` (status, IDs, URLs); `--json` on some commands; meaningful exit codes | JSON by default | `--json` on every command, `--result-json FILE` on long ones, documented exit codes |
| Version check | the CLI sends its version; no negotiation | — | `GET /version` at start, warning on skew, error past the supported window |
| Telemetry | PostHog, opt-out, `DO_NOT_TRACK`, command path only | — | same ethics and the same opt-out default ([`telemetry-and-analytics.md`](telemetry-and-analytics.md) §0.4) |
| Run-directory readers | `RunInfoReader` protocol (name, priority, footprint, markers, `read`), Nextflow and Snakemake, module list | sniffers for Nextflow runs, samplesheets, nf-prov / Galaxy RO-Crates, loaded from directories on `sys.path` | one shared package, readers through entry points |

## 2. The `spectio` command tree

Help panels follow depictio's scheme. Every command accepts `--server`, `--json`, `-v/-vv`, `--log-level` and `--no-color`. Write commands also accept `--dry-run` where it makes sense and `--yes` for non-interactive use.

| Panel | Command | Sub-commands and key options |
|---|---|---|
| **Get started** | `init` | create the data directory, config, first user and project `default` |
| | `serve` | `--role all\|api\|worker`, `--with-runner`, `--safe-mode`, `--no-ui` (needs `spectio[server]`) |
| | `local` | `up`, `open`, `status`, `down`, `wipe`, `export --out DIR` (hand-over to Compose, as in depictio) |
| | `login` / `logout` / `whoami` | `--server`, `--device` (OIDC device code), `--token -` (stdin), `--with-depictio` (exchange a depictio token when the server trusts depictio) |
| | `server` | `add <name> <url>`, `list`, `use <name>`, `remove`, `import --from depictio\|labid` |
| | `runner` | `connect <server> --token …`, `status`, `list`, `drain`, `logs` |
| **Runs and review** | `run` | `launch <org/name@version>` (`--env`, `--params FILE`, `--samplesheet FILE`, `--project`, `--profile`, `--gates spectio.yml`, `--external-ref labid:sample/123`, `--wait`, `--until-gate`, `--idempotency-key`); `list` (`--state`, `--workflow`, `--external-ref`); `show`; `logs --follow`; `tasks`; `cancel`; `relaunch` (`--resume`, `--from-stage N`, `--samplesheet v2.csv`, `--params`); `adopt <launch dir>`; `watch` |
| | `gate` | `list --assigned-to me`; `show`; `decide <gate> --approve\|--reject\|--hold` (`--exclude T1,C4`, `--rule "completeness>50,contamination<10"`, `--comment`); `signal` (robots and agents add evidence); `changes` (change set, samplesheet v2 diff) |
| | `workflow` | `list`, `show`, `import nf-core/rnaseq --versions 3.27.0`, `validate spectio.yml`, `schema` |
| | `env` | `list`, `show`, `test` (dry submit on the cluster) |
| | `project` | `list`, `create`, `use`, `share --user\|--group … --role owner\|editor\|viewer [--launcher] [--reviewer]`, `export`, `import` |
| **Data and integrations** | `export` | `rocrate <run> --out crate.zip`, `report <run>` |
| | `handoff` | `depictio <run>` (runs `depictio-cli ingest` as the sink plugin would), `labid <run>` |
| | `engine` | `nextflow config` (prints the `tower`/plugin config for observed runs, like depictio's `config nextflow --install`), `snakemake profile` |
| | `events` | `tail --type spectio.gate.*`, `replay` |
| **Administration** | `user` | `list`, `create`, `deactivate`, `set-admin` |
| | `group` | `list`, `create`, `add`, `remove`, `set-admin`, `set-pi` |
| | `service-account` | `create`, `list`, `rotate`, `revoke` |
| | `token` | `create --name --expires`, `list`, `revoke` |
| | `admin` | `tasks list\|show\|retry\|cancel`, `logs (--level --source --run --follow)`, `health`, `maintenance on\|off\|status`, `cleanup run <job>`, `settings get\|set` |
| | `backup` | `create (--include db,files,keys,secrets --destination --encrypt)`, `list`, `validate`, `download`, `restore (--dry-run default, --tables, --force)`, `prune`, `schedule show\|set` (verbs aligned with depictio's `backup`) |
| | `migrate` | `project <name> --to-server <profile> (--mode all\|metadata\|files, --overwrite, --dry-run)` (as depictio's `migrate --project`), `database --to postgresql://…`, `storage --to s3://…` |
| | `db` | `status`, `upgrade`, `history` |
| | `branding` | `show`, `export`, `import`, `reset` |
| | `plugin` | `list`, `install`, `new --kind --name`, `doctor` |
| **Reference** | `config` | `show --effective` (with sources, secrets masked), `path` |
| | `doctor` | local checks (SQLite, disk, Python, plugins, server reachability, clock) |
| | `version`, `commands`, `completion` | |

**Exit codes.**

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
spectio run launch nf-core/rnaseq@3.27.0 --env embl-slurm --project liver-tc \
  --params params.yaml --samplesheet samples.csv --external-ref labid:study/77 \
  --idempotency-key "labid-study-77-v1" --wait --result-json run.json

# a reviewer on a phone-free day: what is waiting for me
spectio gate list --assigned-to me --json | jq -r '.[] | "\(.id) \(.run.name) \(.title)"'
spectio gate decide gate_01JB… --approve --exclude T1 --comment "T1 rRNA 14.8 %"

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
    token: keyring:spectio/embl  # or file:…, env:…, or the token itself
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
| **`bioplatform-client`** (client core) | server profiles file and resolver; token sources (keyring, file, env, command); login flows (password → token, OIDC device code, token exchange); httpx client with depictio's retry policy + `Idempotency-Key`; RFC 9457 errors → typed exceptions; cursor and page iterators; identity headers (`X-<App>-Client-Version`, `-Host`, `-Instance`); `/version` check; Rich / `--json` / `--result-json` output helpers; Typer app factory with help panels and renamed-command aliases; `-v/--log-level`; telemetry consent helper (`DO_NOT_TRACK`) | replaces `utils/common.py`, `http_retry.py`, `server_target.py` | base of `spectio` CLI and client | could replace `LabidClient` session handling |
| **`bioplatform-models`** (shared schemas, storage-agnostic, string IDs, no bson) | `UserRef`, `Group` (members, admins, `pi`, `pending_pi_email`, `sso_managed`), `Role` (owner / editor / viewer), `Grant`, `TokenInfo`, `BrandTheme` + presets + `merge_brand_themes` / `resolve_brand_theme` (moved from depictio), `PipelineRef` (`<org>/<name>/<version>`), `ExternalRef` (`labid:sample/123`, `depictio:project/…`, `spectio:run/…`), CloudEvent envelope, `Problem` (RFC 9457), `Page[T]` | API schemas become field-compatible; branding model moves here | API schemas built on them | references and run objects |
| **`bioplatform-runinfo`** (run-directory provenance) | depictio's `RunInfoReader` protocol (`name`, `priority`, `footprint`, `markers`, `read(run_dir) → WorkflowRunInfo`); readers for Nextflow (`pipeline_info`, `.nextflow.log`, trace), Snakemake (`.snakemake`, configs), Workflow Run RO-Crates (nf-prov, Galaxy; from LabID's sniffers); entry-point group `bioplatform.runinfo_readers` | template auto-selection in `ingest` | adopting observed runs, RO-Crate export, depictio hand-off | registering workflow runs |

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
    workflow="nf-core/rnaseq@3.27.0", environment="embl-slurm", project="liver-tc",
    params={"aligner": "star_salmon"}, samplesheet="samples.csv",
    external_refs=["labid:study/77"], idempotency_key="labid-study-77-v1",
)
for event in sp.events.stream(run=run.id, types=["spectio.gate.opened", "spectio.run.*"]):
    ...
run.wait(until="gate")                          # or "end"
```

- **TypeScript: `@spectio/client`.**
  - Generated with `openapi-typescript` plus a small fetch wrapper.
  - The wrapper handles the bearer token, refresh on 401 and retry, as depictio's `authFetch` does, and it takes a configurable `apiBase`. depictio hard-codes `/depictio/api/v1`; here the base is configurable so co-hosting under `/spectio` works.
  - Used by the UI, the embeddable elements and host plugins (LabID).

## 6. Packaging of the CLI

| Install | Gives | Size target |
|---|---|---|
| `uv tool install spectio` | CLI + Python client + runner | < 80 MB environment, CI-checked |
| `uv tool install "spectio[server]"` | + server (FastAPI, SQLAlchemy, Alembic, bundled UI) | — |
| `spectio[postgres]`, `[s3]`, `[oidc]`, `[saml]`, `[celery]` | backends | — |
| `spectio-cli` | alias package that depends on `spectio`, for discoverability (as `depictio-cli`) | — |

- **The runner ships in the base package** ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §6). Its dependencies are the CLI's, so a login node needs one `uv tool install spectio`, and the server extras never land on a cluster.
- **CI checks, borrowed from depictio:**
  - a base-install job that runs the CLI tests without server extras, so a server-only import in client code fails;
  - a wheel size and contents check;
  - the local → Compose hand-over test.
