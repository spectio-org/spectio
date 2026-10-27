# R8 · depictio and LabID drift

**Step page:** [R8](../progress/W1/R8.md)

**Round:** R8 (depictio and LabID drift) · **Date:** 2026-10-26 · **Found by:** depictio-liaison · **Status of the round:** triaged (TRIAGE1, 2026-10-27): 7 accepted, 0 rejected, 8 inbox (4 assumed) · triage: [TRIAGE1](../progress/W2/TRIAGE1.md) · APPLY1 (2026-10-27): 1 applied, 8 partly applied, 2 not applied

**Scope.** [`api-and-data-model.md`](../specs/api-and-data-model.md) §13, [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md), and the `docs/research/depictio-*.md` notes, checked against the current depictio and LabID code.

**Reviewers.** One reviewer was dispatched (depictio-liaison) and it returned a full report. No reviewer failed.

**Sources and commits read.** All clones were shallow and read only.
- **depictio** `main` = `0d1aa0a` (2026-10-23 13:40 UTC), version 1.19.2 (`pyproject.toml:3`; `Chart.yaml` `version: "20261023.1"`, `appVersion: "1.19.2"`).
  - Tag `v1.19.2` is `e40ca79`. `0d1aa0a` only adds the CHANGELOG commit on top of it (`git describe` gives `v1.19.2-1-g0d1aa0a`). R8b's "0d1aa0a (tag v1.19.2)" is off by one commit; the code is the same. R2 FC-011 already reports this.
  - `git ls-remote` on 2026-10-26: `HEAD` = `refs/heads/main` = `0d1aa0a`. **depictio has not changed since the dated audits.** Every finding below is about a claim that was wrong or incomplete when it was written, not about new upstream code.
- **LabID** (public, `gitlab.com/lab-integrated-data`):
  - `labid-server` `52d3952` (2026-10-23), read for the first time in this round;
  - `labid-lib` `cd14636` (2026-10-26);
  - `labid-cli` `5af9e16` (2026-09-23; pins `labidlib@v26.09.2`, `pyproject.toml:24`).
- **Paths.** depictio paths are relative to its repository root at `0d1aa0a`. LabID paths are relative to each repository. Spectio references give the spec, section and line on `autopilot/integration` today.

**Not repeated here, only cited:** R8b DEP-T-013 (co-hosting paths), DEP-T-014 (SeaweedFS identities), DEP-T-015 (JWT key on Kubernetes), DEP-T-016 (depictio-cli on runners), DEP-T-017 (pinning), DEP-T-031 (cite tags); R12 UX-101 and UX-102 (MultiQC bindings). See [R8b](R8b-depictio-tooling.md) and [R12](R12-ui-scenarios.md).

**Overlap with earlier rounds that are still open.** Four findings extend an earlier finding rather than repeat it. Each one states only what is new and should be triaged together with the earlier one:

| This round | Earlier finding | What this round adds |
|---|---|---|
| DL-101 | [R2](R2-open-validations.md) FC-003 (`--user` needs the provisioning key) | the CLI also needs depictio's S3 write secret, Compose S3 is unreachable from a runner, and the provisioning token is 1-year and shared. FC-003's own fix (runner ingests with a per-user token) is not enough on its own |
| DL-102 | [R5](R5-security.md) SEC-120 (depictio JWT trust, revocation, no `aud`) | no `email` or `iss` claim, and no browser hand-over: "one login for both" does not exist in the browser before SSO |
| DL-104 | [R1](R1-consistency.md) SR-023 (0.1 has no recipe runtime) | even with a runtime, MultiQC-section outputs have no columns and `dc_ref` recipes cannot run standalone |
| DL-112 | R5 SEC-121 (`instance` means everyone) | depictio's `embed_enabled` exposes `is_public` projects to anonymous callers even outside public mode |

---

## Summary

| Severity | Count |
|---|---|
| Blocker | 1 |
| Major | 6 |
| Minor | 8 |
| **Total** | **15** |

**Dropped as not reproducible:** 0. **Merged as duplicates within the round:** 0 (one reviewer). Every blocker and major finding was re-checked against the depictio clone at `0d1aa0a` during the merge. Two of them were corrected in the process:
- **DL-103 (embedding).** The reviewer said nginx sends `frame-ancestors 'self'` "for every location, `/dashboard/` included". That is not quite right: `location /dashboard/` declares its own `add_header Cache-Control`, so under nginx's inheritance rule the server-level framing headers do not reach that response **[to be validated: inference, not executed]**. The conclusion still holds, for a different reason (see DL-103).
- **DL-104 (catalogue).** The counts were re-run. My recount gives 413 output YAMLs (YAMLs with a `find:` block, out of 533 YAMLs), 346 with `recipe:`, 61 MultiQC-section outputs, and 339 recipe modules of which 186 use `dc_ref`. The reviewer had 338 and 185 modules. The finding is the same.

The provisioning citation in DL-101 was completed with `core_functions.py:872-911` (`_provision_user`), where the reuse of a valid token is visible.

**The five findings that matter most:**
1. **DL-101 · blocker.** Runner-side `depictio-cli ingest`, as written in api §13.3, needs depictio's instance provisioning key **and** its S3 write secret on every runner, which §13.1 forbids. On a Compose deployment the runner cannot reach depictio's S3 at all. This extends FC-003, whose fix does not cover the S3 secret.
2. **DL-102 · major.** Trusting depictio JWTs does not give Spectio an email, a revocation check or a browser session. v1 trust must be server-side introspection through `GET /auth/me`, and "one login for both" before SSO exists only in the CLI.
3. **DL-103 · major.** The gate-time **Dashboard** tab cannot embed a depictio dashboard from another origin: framing is refused, or the frame has no session. A filter-message protocol (`depictio-embed`) already exists, in another shape than request 9.
4. **DL-104 · major.** The catalogue as a gate-check source: 61 MultiQC outputs have no columns. 186 of 339 recipes have `dc_ref` sources, and the standalone runner skips them with **exit 0 and no table**. This affects 0.1, whose focus is checks.
5. **DL-105 · major.** `run_tag = Spectio run ID` cannot be set: a flat run is named after its directory. `--attach-run` recipe collections read only the first run, and `--result-json` returns no run ID.

**Recurring themes.**
- **The hand-off command line of api §13.3 does not work as written:** DL-101, DL-105, DL-106, DL-107, DL-114.
- **depictio has no place to store Spectio's links or decisions:** DL-107, DL-108.
- **Identity trust must go through `GET /auth/me`, which needs care:** DL-102, DL-110, DL-113.
- **The request list to depictio is out of date:** request 1 is done, requests 8, 9 and 10 are partly done, and seven new requests come from this round (DL-111, Appendix B).

## Findings table

| ID | Sev. | Title | Specs touched | Reviewer draft ID |
|---|---|---|---|---|
| DL-101 | blocker | Runner-side `depictio-cli ingest` needs two instance-wide secrets that §13.1 forbids on runners | api §13.1, §13.3; ecosystem §1.2, §3; cli §2–3 | DL-101 |
| DL-102 | major | Trusting depictio JWTs: no `iss`, `aud` or email claims, revocation only in depictio's database, no browser hand-over | api §13.1; ecosystem §3; cli §2; auth §1–2 | DL-105 |
| DL-103 | major | A depictio dashboard can be embedded only from the same origin; a filter-message protocol already exists in another shape | api §13.6; ecosystem §1.3, §3; QC research note §1.4 | DL-106 |
| DL-104 | major | The catalogue as a gate-check source: MultiQC outputs have no columns, and half of the recipes cannot run standalone | api §13.6; ecosystem §3; QC research note §1.1, §2 | DL-107 |
| DL-105 | major | `run_tag = Spectio run ID` cannot be set, and `--attach-run` does not give one complete run per Spectio run | api §13.3, §13.6; ecosystem §2 | DL-103 |
| DL-106 | major | `--pipeline-id` needs an exact shipped template; "nothing needs mapping" is wrong | api §13.3; ecosystem §2 | DL-102 |
| DL-107 | major | `--provenance-file` is a display-only key/value list; it cannot carry gate filters or an RO-Crate | api §13.3; ecosystem §3 | DL-104 |
| DL-108 | minor | depictio has no field for Spectio back-references | api §13.2, §13.4, §13.5, §13.6; ecosystem §2 | DL-111 |
| DL-109 | minor | LabID facts are now checkable in `labid-server` and differ from §1.6 | ecosystem §1.6; api §13.1 | DL-113 |
| DL-110 | minor | `/groups/list` returns summaries; the identity migration needs per-group detail | ecosystem §2; api §13.2 | DL-110 |
| DL-111 | minor | Corrections to the research notes and to the request list | ecosystem §1.4, §3; QC and harmonisation research notes | DL-115 |
| DL-112 | minor | `instance ↔ is_public` over-exposes data on public-mode depictio or when embedding is on | api §13.2 | DL-112 |
| DL-113 | minor | `GET /auth/me` returns the full `User` model, password hash included | api §13.1 | DL-109 |
| DL-114 | minor | Server-side ingestion already exists, for a refresh only | api §13.3 | DL-108 |
| DL-115 | minor | "Same SeaweedFS image and version" ties Spectio's storage patches to depictio's bump cadence | ecosystem §1.5 | DL-114 |

Spec abbreviations: **api** = [`api-and-data-model.md`](../specs/api-and-data-model.md); **ecosystem** = [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md); **cli** = [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md); **auth** = [`authentication-and-access.md`](../specs/authentication-and-access.md); **QC research note** = [`depictio-qc-integration-2026-10-26.md`](../research/depictio-qc-integration-2026-10-26.md).

---

## Blockers

### DL-101 · blocker · Runner-side `depictio-cli ingest` needs two instance-wide secrets that §13.1 forbids on runners

- **Where:** api §13.1 l.296 ("runners get a scoped token, never depictio's S3 root secret"); api §13.3 l.320 (the runner runs `… --user <owner email> …` "with a short-lived credential from the server"); ecosystem §1.2 l.66 (verdict **Call**); cli §2 (`handoff depictio`) and §3.
- **Evidence:**
  - **Provisioning key.** `--user`: "Provision (create-or-get) this user's account and run the pipeline as them … **Requires --provisioning-key**". The option reads `envvar="DEPICTIO_AUTH_PROVISIONING_API_KEY"` (`depictio/cli/cli/commands/run.py:3102-3124`). R2 FC-003 already reports this part.
  - **What the key can do.** The key is instance-wide and compared with `!=` (`api/v1/endpoints/user_endpoints/routes.py:296-309`). `POST /auth/provision_user` returns a **1-year** token named `pipeline_provision` (`routes.py:327-357`; lifetime in `core_functions.py:697-745`).
    - The token is reused while still valid, so every provisioning of that user shares it (`core_functions.py:872-911`).
    - "Create-or-get" returns an existing account as is, admins included (`core_functions.py:805-811`).
  - **S3 write secret.** `CLIConfig.s3_storage: S3DepictioCLIConfig` is **required** (`depictio/models/models/cli.py:84-87`). The CLI writes Delta tables directly to `s3://{CLI_config.s3_storage.bucket}/{dc_id}` with those credentials (`depictio/cli/cli/utils/deltatables.py:1083-1088`). The config that `generate_agent_config` produces "carries the S3 ROOT secret (deliberate …)" (`routes.py:1422-1447`).
  - **Network.** In Compose, S3 is "Internal-only, no host port" (`docker-compose.yaml:41-45`). A runner on an HPC login node cannot reach it.
- **Problem:**
  - As written, the hand-off puts on every runner the provisioning key, which can mint 1-year tokens for any email, admins included, and depictio's S3 write secret. This contradicts §13.1.
  - FC-003's proposal (the server provisions, and the runner ingests without `--user`) removes the first secret only. The CLI still needs the S3 secret.
  - Against a Compose deployment the runner cannot reach S3 at all.
  - The hand-off is post-0.1 ([decision log](../decisions/log.md), 2026-10-26), but building `sink.depictio` from today's text would build the wrong thing.
- **Proposal:**
  - In **api §13.3** (owner):
    - The **server** holds the provisioning key and calls `POST /auth/provision_user` itself.
    - It passes only the returned user token to the runner, through `DEPICTIO_CLI_TOKEN` (`depictio/cli/cli/utils/common.py:306-331`), never `--user` or `--provisioning-key`.
    - After ingestion, the server mints the login link with `POST /auth/me/magic_link`, using that token.
    - S3 writes need one of two things:
      - a bucket-scoped S3 identity in the runner's CLI config (ties to DEP-T-014; **[to be validated]**: `weed mini` identities);
      - or `depictio-cli` running on a host that can reach depictio's S3 (an "ingest relay").
    - State plainly that the token lives one year and is shared: Spectio must never revoke `pipeline_provision`.
  - Add to **ecosystem §3**:
    - (12) `provision_user` with `expiry_hours` and a per-call token name;
    - (13) ingestion without client-side S3 credentials (an upload through the API, or a server-side ingest of a new location).
  - Triage together with FC-003; this finding supersedes FC-003's proposal.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

---

## Majors

### DL-102 · major · Trusting depictio JWTs: no `iss`, `aud` or email claims, revocation lives only in depictio's database, and there is no browser hand-over

- **Where:** api §13.1 l.293 ("public key or `GET /depictio/api/v1/auth/me` … one login for both"); ecosystem §3 item 5; cli §2 (`--with-depictio`); auth §1 (trust of depictio tokens). Key distribution on Kubernetes is DEP-T-015. Revocation and the missing `aud` are already in R5 SEC-120; this finding adds the missing email, the replay risk and the browser gap.
- **Evidence:**
  - **Claims.** A depictio JWT carries only `name`, `token_lifetime`, `token_type`, `sub` (ObjectId) and `exp` (`depictio/models/models/users.py:12-53`; `user_endpoints/utils.py:119-142`: `to_encode = token_data.model_dump(); to_encode.update({"exp": expire})`).
  - **Revocation.** Verification checks the signature, **then** looks the token up in `TokenBeanie` (`core_functions.py:416-465`, `TokenBeanie.find_one({"access_token": token})`).
  - **Lifetime.** CLI tokens and provisioning tokens live one year (`core_functions.py:697-745`).
  - **No JWKS.** No JWKS endpoint exists (no match for `jwks` under `depictio/api`).
  - **Browser session.** The session is kept in `localStorage['local-store']` (`packages/depictio-react-core/src/api.ts:25,3723`). depictio offers no redirect or token-exchange endpoint.
- **Problem:**
  - With the public key alone, Spectio would accept revoked tokens and every 1-year CLI token.
  - It would not learn the email it needs to match principals.
  - Any token it accepts can be replayed against depictio.
  - On a separate origin, Spectio's UI cannot obtain the depictio session at all, so "one login for both" before SSO does not exist in the browser.
- **Proposal:**
  - In **api §13.1** (owner):
    - v1 trust is server-side introspection through `GET /auth/me` only, with a cache of at most 60 s and the whitelist `id`, `email`, `is_admin`, `display_name` (see DL-113).
    - Never verify with the public key alone.
    - Before SSO, "one login" exists only in the CLI (`spectio login --with-depictio`); in the browser, it comes from SSO through the same identity provider.
    - Fold in SEC-120's exchange-endpoint design.
  - Reword **request 5**: add `iss`, `aud`, `email` and `jti` claims and a JWKS, plus a token-exchange or redirect endpoint.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DL-103 · major · A depictio dashboard can be embedded only from the same origin; a filter-message protocol already exists in another shape

- **Where:** api §13.6 rule 3 l.354 (the Dashboard tab "embeds the depictio dashboard … messages between the two frames"); ecosystem §1.3 l.86 ("deep link or embed"), §3 item 9 l.155; QC research note §1.4 ("There is no message for a selection or a filter yet").
- **Evidence:**
  - **Framing headers.**
    - When the API serves the SPA (`depictio/api/main.py:269`), its baseline headers apply: `X-Frame-Options: SAMEORIGIN` and CSP `frame-ancestors 'self'` (`api/v1/configs/security_headers.py:121,133`).
    - nginx sets the same headers at server level (`docker-images/nginx.conf.template:231,234`).
  - **Merge correction.** `location /dashboard/` declares its own `add_header Cache-Control "no-cache"` (`nginx.conf.template:94-98`). nginx inherits `add_header` "if and only if there are no `add_header` directives defined on the current level" ([nginx docs](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header)). depictio's own comments say the same ("inheritance is all-or-nothing per block", `nginx.conf.template:110-112`), and the image is `nginx-unprivileged:1.27`, which has no `add_header_inherit` (`docker-images/Dockerfile.viewer:50`). So in the Compose viewer container the `/dashboard/` HTML is probably served **without** framing headers **[to be validated: inference, not executed]**.
  - **Session.** Even where framing is allowed, the session lives in depictio-origin `localStorage` (DL-102). Browsers partition storage in third-party frames, so a frame inside Spectio's origin would load without the user's session **[to be validated]**.
  - **Export API.** Only the component export API is meant to be framed from elsewhere. It is off by default and allow-listed (`settings_models.py:176-195`, `embed_enabled`, `embed_allowed_origins`).
  - **Existing protocol.**
    - The embed shell already posts `{source: "depictio-embed", type: "filter", componentId, dcId, filter: {interactive_component_type, column_name, value}}` and `type: "ready"` to its parent (`depictio/viewer/src/embed/EmbedApp.tsx:12-33,69-104`).
    - The only inbound message is `depictio:set-color-scheme` (`viewer/src/lib/embedColorScheme.ts:14,27`).
  - **Filter state.** Per-user filter state can be written at viewer level: `PUT /dashboards/filter_state/{dashboard_id}` (`dashboards_endpoints/filter_state_routes.py:1-8,71-77`).
- **Problem:**
  - With Spectio on its own host, the Dashboard tab is either blocked by the browser or anonymous, depending on the deployment.
  - Request 9 invents names (`depictio:set-filter`) beside an existing protocol.
  - The missing headers on `/dashboard/`, if confirmed, are a clickjacking gap in depictio itself.
- **Proposal:**
  - In **api §13.6 rule 3**:
    - The Dashboard tab exists only when Spectio is served from depictio's origin (with DEP-T-013; note the merged trust domain of SEC-109). Otherwise it is a deep link.
    - Before deep-linking, the server may preset excluded items through `PUT /dashboards/filter_state/{id}`, acting as the user (**[to be validated]**: payload in `depictio/models/models/dashboard_filter_state.py`).
  - Reword **request 9**:
    - extend `depictio-embed` with an inbound `set-filter` and an outbound `selection` for full dashboards;
    - make `frame-ancestors` for `/dashboard/` configurable.
  - Report the `/dashboard/` header inheritance to depictio once the spike confirms it.
- **Found by:** depictio-liaison (merge corrected the nginx evidence)
- **Status:** partly applied (APPLY1, 2026-10-27): research/depictio-qc-integration-2026-10-26.md §2; api §13.6; depictio-ecosystem-reuse §3 row 9; ui-spec §10.1, §10.2 (assumed — pending Thomas, inbox #23); pending: depictio-ecosystem-reuse §1.3 (inbox #26); board ReviewDashboard (deep-link variant)

### DL-104 · major · The catalogue as a gate-check source: MultiQC outputs have no columns, and half of the recipes cannot run standalone

- **Where:** api §13.6 table ("`find` glob → recipe (`OUTPUT_SCHEMA`) → columns") and rule 1 l.352; ecosystem §3 item 8; QC research note §1.1 and §2 ("A Spectio check binds to a catalogue output's column"). Related: R1 SR-023 (0.1 has no runtime), R12 UX-101 and UX-102.
- **Evidence:**
  - **MultiQC outputs.** Of 413 output YAMLs (with a `find:` block), 346 declare `recipe:`. 61 render as `{component: multiqc, section: …}` with no recipe and no columns, for example `depictio/catalog/multiqc/frip_score.yaml:1-15`.
  - **`dc_ref` sources.** 186 of 339 recipe modules have `dc_ref` sources (merge recount; examples: `catalog/cellranger/cell_qc.py`, `catalog/mosdepth/summary.py`). `resolve_sources` skips them: "caller must inject these" (`depictio/recipes/__init__.py:375-379`).
  - **Standalone runner.** One exists, but it is a maintainer command, under a group labelled "Maintainer / CI tooling (not needed for day-to-day use)": `depictio dev recipe run <module>/<name>.py --data-dir --version --output <parquet>` (`depictio/cli/cli/commands/dev.py:17-21`, `commands/recipe.py:17-40`).
  - **Silent success.** On `dc_ref` recipes it prints "Skipped dc_ref sources (not available standalone)" and **exits 0 with no output** (`recipe.py:64-74`).
- **Problem:**
  - The headline QC outputs named in the QC note (FRiP, STAR, Salmon, `cell_qc`, mosdepth) cannot serve as column bindings computed by the runner.
  - A runner that trusts the exit code would record success with no table.
  - This affects 0.1, whose focus is checks.
- **Proposal:**
  - In **api §13.6 rule 1**: catalogue bindings are allowed only for recipes with file or glob sources. MultiQC-section outputs use Spectio's own `multiqc.parquet` bindings (UX-101).
  - Correct the QC research note §1.1 and §2.
  - Reword **request 8**:
    - a stable public `depictio recipe run` that resolves `dc_ref` sources from the output YAML's `find` glob;
    - a non-zero exit when it cannot;
    - a documented parquet contract.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DL-105 · major · `run_tag = Spectio run ID` cannot be set, and `--attach-run` does not give one complete run per Spectio run

- **Where:** api §13.3 l.317-318 (`project: linked`, `attach_run: true … run_tag = Spectio run ID`); api §13.6 rule 1 l.352 ("the hand-off … ingests the same tables"); ecosystem §2 item 3.
- **Evidence:**
  - **Run tag.** "A flat run is named after its directory": `flat_run_tag = os.path.basename(os.path.normpath(location))`. `/scratch/a/results` and `/scratch/b/results` clash, and the clash stops the ingestion (`depictio/cli/cli/utils/scan.py:798-825`, `run.py:966-975`).
  - **Flat templates.** 40 of the 41 nf-core `template.yaml` files are `structure: "flat"`; only viralrecon 3.0.0 is not (merge re-ran the grep).
  - **`--attach-run`.** "The project is found by --project, else by the template's own name … collections a recipe computes still read the project's first run only" (`run.py:2928-2939`). `--project` is a name, not an ID (`run.py:2918-2925`).
  - **`--result-json`.** It holds status, project, dashboards and `template_id`, with **no run ID or run tag** (`run.py:157-177`).
- **Problem:**
  - Spectio cannot set the run tag or read it back.
  - Two Spectio runs with outdir `results` clash.
  - The link is by project name, so a rename breaks it.
  - For the second and later runs of a linked project, recipe-computed tables (the §13.6 catalogue tables) show the first run's data.
- **Proposal:**
  - In **api §13.3**:
    - The runner ingests a path whose last segment is the Spectio run ID, for example a symlink `<…>/<run-id>` pointing to the outdir. `flat_run_tag` uses `normpath`, not `realpath`, so the tag would be the symlink name (**[to be validated]**: the scan follows the symlink).
    - Pass `--project <depictio project name>`, resolved from the stored link at each hand-off.
    - Until depictio fixes recipe collections across runs, use **one depictio project per Spectio run** for QC dashboards, and keep `attach_run` for file-based collections only.
  - Requests:
    - (15) a `--run-tag` option, and `run{id,tag}` in `--result-json`;
    - (16) recipe-computed collections built from every attached run;
    - project lookup by ID.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.3; depictio-ecosystem-reuse §3 rows 15, 16 (assumed — pending Thomas, inbox #22); pending: api §13.3 step 1 (inbox #22); api §13.6 rule 1 (inbox #16); spike `depictio-handoff` scope (inbox #22)

### DL-106 · major · `--pipeline-id` needs an exact shipped template; "nothing needs mapping" is wrong

- **Where:** api §13.3 l.311 ("about 35 nf-core pipelines"), l.316 (`template: auto … e.g. nf-core/rnaseq/3.27.0`), l.320; ecosystem §2 item 4 l.136 ("the same string … so nothing needs mapping"). The count is already in R2 FC-011; the exact-match behaviour is new.
- **Evidence:**
  - **No fallback.** `if pipeline_id and not template and not project_config_path: … locate_template(pipeline_id) … except FileNotFoundError: … raise typer.Exit(code=1)` (`run.py:1384-1400`). `TemplateNotFoundError` subclasses `FileNotFoundError` (`depictio/cli/cli/utils/templates.py:131`).
  - **Accepted versions.** `locate_template` accepts only an exact version, `latest`, or no version (`templates.py:214-257`).
  - **Closest version.** The "closest shipped version not newer than the run" rule applies only to auto-detection **without** `--pipeline-id` (`templates.py:291-313`).
  - **`--compose`.** It cannot rescue the call: once the pipeline ID resolves, `template` is set, and "--compose builds the template itself: drop --template / --project-config-path" (`run.py:1464-1468`).
  - **Shipped templates.** 41 templates for 32 pipelines. rnaseq has only `3.26.0`, so `nf-core/rnaseq/3.27.0` exits 1 (`find depictio/projects/nf-core -name template.yaml`).
  - **Same behaviour in depictio's hook.** It forwards `workflow.manifest` name and version as `--pipeline-id` (`depictio/cli/configs/nextflow/depictio.config:217-226`).
- **Problem:** `template: auto`, passing Spectio's workflow version, fails for every release depictio has not templated, which is most of them.
- **Proposal:**
  - In **api §13.3**:
    - `template: auto` means do **not** pass `--pipeline-id`. Either let depictio detect the template from the run directory (closest not-newer, then compose), or pass an explicit `--template <id>` that Spectio resolved beforehand.
    - Fix the example to `3.26.0`, and the count to "32 pipelines, 41 templates" (FC-011).
  - In **ecosystem §2 item 4**: the string format is the same but the version set is sparse, so map to the closest shipped template not newer than the run.
  - Request (14): `--pipeline-id` falls back the way detection does.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.3; depictio-ecosystem-reuse §2 item 4, §3 row 14; pending: api §13.3 step 1 `--pipeline-id` (inbox #22)

### DL-107 · major · `--provenance-file` is a display-only key/value list; it cannot carry gate filters or an RO-Crate

- **Where:** api §13.3 step 5 l.324 ("Filter artifacts from gates … are passed to depictio as part of the provenance, so dashboards show the reviewed data"), l.320 (`<run summary or RO-Crate>`); ecosystem §3 item 6.
- **Evidence:**
  - **Help text.** "Extra provenance/recap file (json, yaml, or 2-column tsv of key/value) whose entries are listed in the project's run-provenance report under 'User provided'" (`run.py:2951-2962`).
  - **Truncation.** Each value is cut at `_PROVENANCE_VALUE_MAX = 500` characters (`templates.py:1003,1053-1065`) and tagged `("user", "User provided", key, value)` (`templates.py:1149-1162`).
  - **Storage.** It is stored once per project, in `template_origin.run_provenance` (`depictio/models/models/templates.py:368,400-412`; `projects.py:45`), not per run.
- **Problem:**
  - A keep list of 8,000 cell IDs becomes a truncated string in a report card, and nothing filters the dashboards.
  - An RO-Crate cannot be passed (request 6 is still open).
  - With `attach_run`, the provenance describes only the latest ingestion.
- **Proposal:**
  - In **api §13.3 step 5**, decisions and keep lists travel **as data**:
    - the runner writes `spectio/spectio_checks.tsv` and `spectio/spectio_decisions.tsv` into the ingested directory;
    - they become data collections through a template overlay (`--project-config-path`), or through `--compose --include 'spectio/*.tsv'` (`run.py:3055-3072`; only when composing);
    - joins are declared on the item key.
  - `--provenance-file` carries only short scalars: the Spectio run URL, gate IDs, decision counts.
  - Keep request 6 and reword it: "per-run provenance; accept a WRROC crate".
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.3 step 5; depictio-ecosystem-reuse §3 row 6; pending: api §13.3 step 1 `--provenance-file` (inbox #22)

---

## Minors

These were spot-checked during the merge (`/auth/me` return type, `GroupSummary`, the ingestion trigger route, the absence of `external_ref`, the PyPI dates, the megatest count) but not every line was re-read.

### DL-108 · minor · depictio has no field for Spectio back-references

- **Where:** api §13.2 l.305 (linked "by `external_refs` (`depictio:project/<id>` ↔ `spectio:project/<id>`)"); api §13.4 l.328 ("links both ways through `external_refs`"); api §13.5 l.337 (dashboard → producing run); api §13.6 rule 4 l.355 (gate tile); ecosystem §2 item 3 l.135 ("linked both ways").
- **Evidence:**
  - `external_ref` appears nowhere in depictio (grep over `*.py`: 0 matches).
  - `Project` has `data_management_platform_project_url` (one URL, meant for a data-management platform such as LabID) and `triggered_by` (`depictio/models/models/projects.py:27-68`).
  - `WorkflowRun` has no free link field (`workflows.py:125-139`).
- **Problem:** the depictio → Spectio direction and the gate tile have nowhere to be stored.
- **Proposal:**
  - In **api §13.2**: for now, links are stored on the Spectio side only.
  - A back-link is a `spectio_run_url` entry in `--provenance-file`. It shows under "User provided" (**[to be validated]**: rendered as a link).
  - Leave `data_management_platform_project_url` to the LabID plugin.
  - Request (18): `external_refs` on `Project` and `WorkflowRun`, plus `--external-ref`.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.5, §13.6; depictio-ecosystem-reuse §2 item 3, §3 row 18; pending: api §13.2 Project row (inbox #18, #21); api §13.4 IDs (inbox #23); board DepictioDecisions

### DL-109 · minor · LabID facts are now checkable in `labid-server` and differ from §1.6

- **Where:** ecosystem §1.6 l.122 ("REST under `/api/`, `token-auth/`, Bearer or `Token` headers (DRF, inferred)"); api §13.1 (one identity provider).
- **Evidence:** all from `labid-server@52d3952` unless stated otherwise.
  - **REST.** Routes match `^api/(?P<version>(v2))/…`; OpenAPI is at `/api/schema/` (drf-spectacular); SSO is at `api/v2/sso/` (`labid/labid/urls.py:57-97`).
  - **SSO.** OIDC **or** SAML, one per instance (`SSO_PROVIDER`, `labid/core/urls_sso.py:12-35`).
  - **Auth classes.** simplejwt `Bearer`, DRF `Token`, Session and Basic (`labid/labid/settings/base.py:470-486,526-531`). The default JWT lifetime is 14 days; refresh tokens last 365 days, with rotation.
  - **Query-string credentials.** `?jwt=` and `?key=` are also accepted (`labid/core/auth/backends.py:154-194`).
  - **Impersonation.** `api/v2/token-auth/impersonate/` is superuser-only (`labid/core/api/auth.py:78`).
  - **WorkflowRun API.** At `api/v2/workflows/workflowruns/` (`labid/workflows/urls.py:23`).
  - **PyPI.** `labidlib` and `labidcli` are still not on PyPI (404 on 2026-10-26; `labidlib` re-checked during the merge).
- **Proposal:**
  - Update **ecosystem §1.6**: `spectio-plugin-labid` uses a client generated from `/api/schema/` and header credentials only, never `?jwt=` or `?key=`. The sink targets `workflows/workflowruns`.
  - In **api §13.1**: depictio is SAML-only (besides Google), while LabID can do OIDC or SAML. Recommend SAML for all three, or Keycloak as a broker.
- **Found by:** depictio-liaison
- **Status:** accepted (TRIAGE1, 2026-10-27); not applied (APPLY1): blocked by inbox #26 (depictio-ecosystem-reuse §1.6) and #21 (api §13.1); LabID facts recorded in research/depictio-audit-2026-10-26.md

### DL-110 · minor · `/groups/list` returns summaries; the identity migration needs per-group detail

- **Where:** ecosystem §2 item 1 l.128; api §13.2 l.304.
- **Evidence:**
  - `GroupSummary` holds `id`, `name`, `description`, `member_count` and `sso_managed`: "no member identities leaked" (`groups_endpoints/models.py:14-21`, `routes.py:192-198`).
  - Members, `admin_ids`, `pi_id` and `pending_pi_email` come only from `GET /groups/{id}`, for sysadmins or members (`routes.py:220-230`, `models.py:39-49`).
  - `/auth/list` is admin-only (`user_endpoints/routes.py:1462-1477`).
- **Proposal:**
  - In ecosystem §2 item 1, call `GET /auth/list`, then `GET /groups/list`, then `GET /groups/{id}` for each group, with an admin token.
  - Import `pending_pi_email` too. It is also missing from api §13.2 l.304; R1 notes it is absent from the schema.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): depictio-ecosystem-reuse §2 item 1; pending: api §13.2 Group row (inbox #21); users/groups schema (inbox #20)

### DL-111 · minor · Corrections to the research notes and to the request list

- **Where:** ecosystem §1.4 l.99, §3; QC research note §1.2, §1.4, §3; [`depictio-harmonization.md`](../research/depictio-harmonization.md) §1.3.
- **Evidence:**
  - **PyPI.** `plotly-upset` and `plotly-complexheatmap` 0.1.0 have been on PyPI since 2026-10-05 (pypi.org JSON API, upload times 2026-10-05T17:37; re-checked during the merge). Yet ecosystem §1.4 says "PyPI pending" and request 1 says "already planned".
  - **Selection message.** It exists (DL-103).
  - **Megatests.** Only 35 of the 38 version templates have a `megatest.yaml`; ampliseq 2.14.0 and 2.16.0 and viralrecon 3.0.0 have none. The other 3 of the 41 `template.yaml` files are variantbenchmarking category sub-templates. The QC note says "Each template has a `megatest.yaml`" (§1.2 l.34).
  - **Pipeline count.** The harmonisation note says "~35 pipelines"; there are 32.
  - **Request dropped.** The QC note's request 4 (publish the renderers) was not carried into ecosystem §3.
  - **mosdepth.** The per-file recipe already exists (`catalog/mosdepth/summary.yaml:14-16`, `**/*.mosdepth.summary.txt`), although it depends on `dc_ref` (DL-104).
- **Proposal:** write the dated research note drafted in Appendix A, and replace ecosystem §3 with the status table of Appendix B.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): map; research/depictio-audit-2026-10-26.md (new); research/depictio-harmonization.md §1.3; research/depictio-qc-integration-2026-10-26.md §1.2, §1.4, §3; depictio-ecosystem-reuse §3; pending: depictio-ecosystem-reuse §1.4 (inbox #26); Appendix B rows from DL-101, DL-102, DL-104 (inbox); mkdocs.yml nav entry

### DL-112 · minor · `instance ↔ is_public` over-exposes data on public-mode depictio or when embedding is on

- **Where:** api §13.2 l.306. The Spectio-side split of `instance` and `public` is R5 SEC-121, with the open question against R1 SR-029; this finding adds the depictio-side conditions.
- **Evidence:**
  - Anonymous users get `"viewer" if is_public` (`api/v1/permissions.py:142-144`).
  - The anonymous fallback exists in public and single-user modes (`user_endpoints/routes.py:147-151`).
  - `embed_enabled` "lets anonymous callers read PUBLIC projects even on instances that are not in public mode" (`settings_models.py:176-183`).
- **Problem:** in Spectio, `instance` is meant as "my colleagues" (api §6 l.139: "everyone can read"; SEC-121). Mirroring it to `is_public` can publish the project to anonymous visitors.
- **Proposal:**
  - Mirror `instance` → `is_public` only when depictio is in standard mode with embedding off.
  - Otherwise, grant viewer to an instance-wide group (**[to be validated]**: whether depictio's protected `users` group, `groups_endpoints/routes.py:49-53`, holds every user).
  - Apply after the SEC-121 / SR-029 decision.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DL-113 · minor · `GET /auth/me` returns the full `User` model, password hash included [inference, not executed]

- **Where:** api §13.1 l.293; DEP-T-015 and DL-102, which both propose `/auth/me` as the verification path.
- **Evidence:**
  - `async def get_current_user_info(current_user: User = Depends(get_user_or_anonymous)) -> User: … return current_user` (`user_endpoints/routes.py:600-616`).
  - `class User(UserBaseUI): password: str`, with no exclusion or serializer (`users.py:321-322`).
  - FastAPI uses the return annotation as the response model ([FastAPI docs](https://fastapi.tiangolo.com/tutorial/response-model/#return-type-annotation)).
  - The only "password not in" test covers `get_all_users` (`tests/api/v1/endpoints/user_endpoints/test_user_management.py:180-196`).
- **Problem:** introspection would hand Spectio bcrypt hashes, which it could then cache or log.
- **Proposal:**
  - The depictio adapter parses only whitelisted fields and never logs response bodies.
  - Report it to depictio as request (17): return `UserBaseUI`.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): depictio-ecosystem-reuse §3 row 17 (assumed — pending Thomas, inbox #27); pending: api §13.1 `/auth/me` whitelist (inbox #21); report to depictio (Thomas, inbox #27)

### DL-114 · minor · Server-side ingestion already exists, for a refresh only

- **Where:** api §13.3 step 4 l.323 ("Later, a server-to-server ingestion call can replace the CLI").
- **Evidence:** `POST /depictio/api/v1/projects/ingestion/trigger/{project_id}` starts a `project.ingest` job (`api/v1/endpoints/projects_endpoints/routes.py:659-760`). It:
  - is off by default (`DEPICTIO_INGESTION_BROWSER_TRIGGER`);
  - is confined to `DEPICTIO_INGESTION_ALLOWED_DATA_ROOTS`;
  - needs editor rights;
  - returns 409 when the server cannot read the locations.
- **Problem:** the spec treats as future something that exists today. It only re-ingests an existing project's locations; it cannot create a project or add a run.
- **Proposal:**
  - Name it in **api §13.3 step 4**.
  - Use it to refresh a gate-time project at completion when depictio reads the same storage.
  - Keep request (13) for new locations (DL-101).
- **Found by:** depictio-liaison
- **Status:** applied (APPLY1, 2026-10-27): api §13.3 step 4

### DL-115 · minor · "Same SeaweedFS image and version" ties Spectio's storage patches to depictio's bump cadence

- **Where:** ecosystem §1.5 l.105.
- **Evidence:**
  - depictio pins `chrislusf/seaweedfs:4.46` (`docker-compose.yaml:47`, `helm-charts/depictio/values.yaml:194-198`).
  - Upstream tags go up to `4.51` (`git ls-remote https://github.com/seaweedfs/seaweedfs`, 2026-10-26). Release dates **[to be validated]**.
- **Proposal:**
  - Use the same image family, with depictio's pin as the floor.
  - Spectio keeps its own pin, bumped by the dependency bot (DEP-T-009).
  - When co-hosted, the shared instance follows whichever pin is newer.
- **Found by:** depictio-liaison
- **Status:** inbox, assumed: the same SeaweedFS image family with depictio's pin as the floor; Spectio keeps its own pin, bumped by the dependency bot (DEP-T-009); a shared instance follows the newer pin; the 2026-10-25 log entry is amended — pending Thomas (TRIAGE1, 2026-10-27); not applied (APPLY1): blocked by inbox #26 (depictio-ecosystem-reuse §1.5 and architecture §7.4)

---

## Questions for Thomas

1. **Where does depictio ingestion run (DL-101, R2 FC-003)?** There are three options:
   - on the runner, with a bucket-scoped SeaweedFS identity (needs DEP-T-014);
   - on an "ingest relay" host next to depictio, which reads the results through shared storage or a copy;
   - wait for depictio to accept ingestion without client S3 credentials (new request 13).

   Should DL-101 supersede FC-003's proposal, and does it stay a blocker given that the hand-off is post-0.1?
2. **One depictio project per Spectio run, or one per Spectio project (DL-105)?** Until depictio builds recipe collections from every attached run, `attach_run` shows the first run's QC tables. The proposal is one project per run for QC dashboards.
3. **"One login for both" before SSO (DL-102, R5 SEC-120).** Do you accept that, without a shared identity provider, the single login exists only in the CLI (`--with-depictio`), and that the browser needs SSO?
4. **Gate-time Dashboard tab (DL-103, R5 SEC-109, DEP-T-013).** Should the tab exist only when co-hosted on one origin, with a deep link plus a preset filter state otherwise? This ties into the open co-hosting default question of R5.
5. **Reporting to depictio.** Two items are security-relevant for depictio itself:
   - `/auth/me` returning the password hash (DL-113);
   - `/dashboard/` probably served without framing headers in the Compose viewer container (DL-103).

   Should they go to depictio's maintainers now, privately, ahead of the request list? And should the 18 requests be filed as one tracking issue or one issue each?
6. **Catalogue bindings in 0.1 (DL-104, R1 SR-023).** Do you confirm that 0.1 binds checks only to Spectio's own bindings and `multiqc.parquet`, and that catalogue bindings wait for a public `depictio recipe run` that resolves `dc_ref`?

## Proposed spikes

| Spike | Question it answers | Findings | Exit |
|---|---|---|---|
| `spikes/depictio-handoff/` | Can a runner ingest into a Compose depictio with a provisioned user token (`DEPICTIO_CLI_TOKEN`) and a bucket-scoped `weed mini` identity, with no provisioning key or root S3 secret? Does a `<run-id>` symlink become the flat run tag, and what do `--attach-run` and `--result-json` return for two runs? | DL-101, DL-105, DL-106, DL-107, DL-114 | depictio 1.19.2 in Compose, nf-core/rnaseq megatest tables: the commands, the resulting run tags, the JSON, and the S3 identity file; research note |
| `spikes/depictio-embed/` | Which headers does `/dashboard/<id>` really send from the Compose viewer container and from the API? Does a cross-origin frame get a session in Chrome and Firefox? Does `PUT /dashboards/filter_state/{id}` preset excluded samples before a deep link? | DL-103, DL-102 | `curl -I` on both paths, a two-origin test page with browser captures, the filter-state payload; research note |
| `spikes/depictio-recipe-runner/` | Which catalogue outputs for rnaseq, scrnaseq and sarek produce a table with `depictio dev recipe run`, and which silently produce nothing? | DL-104 | A table, output → produced / skipped (`dc_ref`) / MultiQC-only, with exit codes; research note |
| `spikes/depictio-introspection/` | What exactly does `GET /auth/me` return for a CLI token, a provisioning token and a revoked token? | DL-102, DL-113 | Recorded responses (hashes redacted), the field whitelist and the cache rule for api §13.1; can be folded into `depictio-handoff` |

---

## Appendix A · Proposed research note `docs/research/depictio-audit-2026-10-26.md`

This draft is from the reviewer, renumbered to this file's IDs and with the embedding line corrected during the merge. `/apply-findings R8-depictio` writes it if DL-111 is accepted. It is not a file yet.

```markdown
# depictio and LabID re-audit (2026-10-26)

Sources: depictio `main` 0d1aa0a (2026-10-23; = tag v1.19.2 `e40ca79` + CHANGELOG commit);
labid-server 52d3952 (2026-10-23), labid-lib cd14636 (2026-10-26), labid-cli 5af9e16
(2026-09-23). Shallow clones, read only. Findings: R8 DL-101..DL-115.

## 1. What changed upstream since the 2026-10-25 audits
- depictio: nothing. `origin/HEAD` is still 0d1aa0a. Cite `v1.19.2 (e40ca79)` for code and
  0d1aa0a for the tree (DEP-T-031).
- LabID: labid-server is public and was read for the first time; labid-lib moved to cd14636
  (no new tag since v26.09.2).

## 2. What the earlier notes got wrong or left out
- plotly-upset / plotly-complexheatmap are on PyPI (0.1.0, 2026-10-05).
- Embeds already post `{source:"depictio-embed", type:"filter"|"ready"}` (EmbedApp.tsx:12-104).
  The API and nginx send `frame-ancestors 'self'` (security_headers.py:121;
  nginx.conf.template:231,234), but nginx's `location /dashboard/` re-declares `add_header`
  (l.94-98), so its HTML probably carries no framing header [to be validated]. Either way a
  cross-origin frame has no session (localStorage, partitioned storage) [to be validated].
- A standalone recipe runner exists as a maintainer command: `depictio dev recipe run`
  (dev.py:17-21); it skips `dc_ref` recipes (186/339) with exit 0 (recipe.py:64-74).
  61 MultiQC outputs have no recipe.
- `--pipeline-id` needs an exact shipped template (run.py:1384-1400); 41 templates, 32 pipelines.
- Run tag = directory basename (scan.py:798-825); `--attach-run` recipe collections read the
  first run only (run.py:2928-2939); `--result-json` has no run ID (run.py:157-177).
- `--provenance-file` = flat key/value, 500 chars, project-level, "User provided"
  (templates.py:1003,1149-1162).
- `--user` requires the instance provisioning key (run.py:3102-3124); CLIConfig requires S3
  write credentials (cli.py:84-87; deltatables.py:1083-1088).
- JWT claims: name, token_lifetime, token_type, sub, exp; no iss/aud/email; revocation via
  TokenBeanie lookup (core_functions.py:416-465). `/auth/me` returns `User` (password field,
  inference).
- `/groups/list` = summaries; detail via `/groups/{id}`.
- Server-side refresh ingestion exists: `POST /projects/ingestion/trigger/{id}`, off by default.
- Per-user filter state: `PUT /dashboards/filter_state/{dashboard_id}`.
- LabID: `/api/v2/`, OpenAPI `/api/schema/`, simplejwt Bearer (14 d) + DRF Token + `?jwt=`/`?key=`,
  SSO OIDC or SAML, superuser impersonation, WorkflowRun API.
- megatest.yaml: 35 of 38 version templates.

## 3. Requests to depictio: status on 2026-10-26
See the table in R8-depictio.md, Appendix B.
```

## Appendix B · Requests to depictio: status on 2026-10-26

This table is proposed to replace ecosystem §3 (DL-111). Finding IDs are this file's.

| # | Request | Status | Evidence / next step |
|---|---|---|---|
| 1 | Publish plotly-upset, plotly-complexheatmap | **Done** | PyPI 0.1.0, 2026-10-05 |
| 2 | Extract the branding model and theme engine | Open | `depictio-react-core` private, `main: src/index.ts` |
| 3 | Configurable `API_BASE` | Open | `packages/depictio-react-core/src/api.ts:22` |
| 4 | OpenAPI-generated TS client | Open | no generator in any `package.json` |
| 5 | `/auth/me` for Spectio tokens, or JWKS | Open, **reword** | add `iss`/`aud`/`email`/`jti` + token exchange (DL-102) |
| 6 | RO-Crate `--provenance-file` | Open, **reword** | per-run provenance + WRROC (DL-107) |
| 7 | `checks_as` beside `renders_as` | Open | no match in `depictio/catalog/` |
| 8 | Runnable recipe without a server | **Partly done** | maintainer-only `depictio dev recipe run`; ask: public, resolves `dc_ref`, non-zero exit (DL-104) |
| 9 | Selection and filter messages | **Partly done**, **reword** | extend `depictio-embed`; same origin only today (DL-103) |
| 10 | Per-file recipes (STAR, Trim Galore, fastp, Salmon, mosdepth) | **Partly done** | mosdepth summary exists (`dc_ref`); the others are open |
| 11 | Shared megatest fetcher | Open | `scripts/nfcore_megatest.py` unchanged |
| QC-4 | Publish the renderers (`@bioplatform/viz`) | Dropped from §3: **restore** | QC research note §3 item 4 |
| 12 | Short-lived, per-call provisioning token | **New** | DL-101 |
| 13 | Ingestion without client S3 credentials | **New** | DL-101, DL-114 |
| 14 | `--pipeline-id` closest-version fallback | **New** | DL-106 |
| 15 | `--run-tag`, run ID in `--result-json` | **New** | DL-105 |
| 16 | Recipe collections across attached runs | **New** | DL-105 |
| 17 | `/auth/me` returns `UserBaseUI` | **New** | DL-113 |
| 18 | `external_refs` on Project and WorkflowRun | **New** | DL-108 |
| R8b | Configurable UI base path (DEP-T-013); SeaweedFS identities file (DEP-T-014) | Open | see [R8b](R8b-depictio-tooling.md) |

No in-flight depictio branch was found that changes any row above. Branch tips checked by the reviewer: `feat/shareable-filter-urls` 2026-09-11, `nextflow-trigger/cli-auth` 2026-09-04, `fix/s3-startup-check-least-privilege` 2026-08-24 **[to be validated: merged or stale]**.
