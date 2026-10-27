# R8b · depictio engineering tooling and ecosystem: what Spectio is missing

**Round:** R8b (tooling re-audit) · **Date:** 2026-10-26 · **Found by:** depictio-liaison · **Status of the round:** triaged (TRIAGE1, 2026-10-27): 19 accepted, 3 rejected, 10 inbox (7 assumed) · triage: [TRIAGE1](../progress/W2/TRIAGE1.md) · APPLY1 (2026-10-27): 1 applied, 22 partly applied, 3 not applied

**Sources.**
- **depictio** at `0d1aa0a` (2026-10-23 13:40 UTC, tag `v1.19.2`). `git fetch --all` showed that `origin/HEAD` has not moved since the earlier audits.
- **depictio-docs** at `1610ed8` (2026-10-12), also unchanged.
- **Release dates** come from tag creator dates in a treeless bare clone.
- **Paths:** depictio paths are relative to its repository root at `0d1aa0a`. Spectio references give the spec section, and a line number where it helps.

Both repositories were only read.

## Summary

| Area | Blocker | Major | Minor | Total |
|---|---|---|---|---|
| CI and required checks | 1 | 1 | 1 | 3 |
| Release and publishing | 1 | 1 | 2 | 4 |
| Images and supply chain | 0 | 3 | 1 | 4 |
| Helm and Kubernetes | 0 | 1 | 0 | 1 |
| Testing | 0 | 3 | 1 | 4 |
| Repository governance and dependencies | 0 | 2 | 2 | 4 |
| Ecosystem: co-hosting and depictio coupling | 0 | 5 | 3 | 8 |
| Operations and telemetry | 0 | 0 | 2 | 2 |
| Developer experience and tooling | 0 | 0 | 2 | 2 |
| **Total** | **2** | **16** | **14** | **32** |

**Corrections to earlier audits** (`docs/research/depictio-*.md`):
1. `scripts/security_audit_compose.sh` and `security_audit_helm.sh` are **not run by any workflow**, and one of their static checks already fails on the current `docker-compose.yaml` (DEP-T-020).
2. `repackage-helm-chart.yaml` **overwrites** an existing OCI chart tag (l.1–18, 71–75). The chart's OCI reference is `oci://ghcr.io/depictio/depictio-helm/depictio:<YYYYMMDD.N>` (`test-and-package-helm-chart.yaml:25,1299`).
3. depictio's default bucket is `depictio-bucket` (`docker-compose.yaml:62`), not `depictio` as `depictio-ecosystem-reuse.md` §2 item 6 says.
4. The Helm chart pins `mongo 8.0.5` (`values.yaml:113`) while Compose pins `mongo:8.0.14` (`docker-compose.yaml:14`). This is drift inside depictio, not an action for Spectio.
5. The release notes and `CHANGELOG.md` advertise image tags that are never published (DEP-T-021).

**Release cadence (last 6 months).**
- **Volume:** 120 tags since 2026-04-26: 103 version tags (73 stable, 30 betas) and 15 `backup/*` tags left by history rewrites.
- **Per month:** May 21, June 23, July 11, August 16, September 7, October 23.
- **Since 1.0:** `v1.0.0` was tagged on 2026-06-10, and 19 minor versions followed in 4.5 months.

---

## Blockers

### DEP-T-001 · blocker · Path-filtered workflows used as required checks block every PR they skip

- **Where:** `docs/playbooks/autopilot.md` §8 (branch protection contexts), `documentation-system.md` §8 ("plus the pipeline workflows the PR touches"), `.github/workflows/pipelines-synthetic.yml:6-7`.
- **Evidence:**
  - The protection payload requires `"nextflow 26.10.3", "nextflow 25.10.9", "snakemake 9.27.1"`, but those jobs only run on PRs touching `tests/pipelines/synthetic/**`.
  - depictio solves this with one aggregator job, `ci-ok` (`depictio-ci.yaml:3144-3174`). Its comment: "A job skipped on purpose … counts as passing here; required per-job checks would not survive that, because a matrix job skipped before it expands never reports under its leg names." It fails only on `failure` or `cancelled` (`:3166-3170`).
- **Problem:** a PR that does not touch those paths never reports the contexts and stays "Expected — waiting" forever. Auto-merge never fires, and the autopilot stalls on its first docs-only PR.
- **Proposal:**
  - In **dev-environment §11**, add one `ci.yml` with a change-detection job (depictio `depictio-ci.yaml:89-159`) and a final `ci-ok` job that `needs:` every job.
  - Turn the pipeline workflows into reusable workflows (`workflow_call`).
  - In **autopilot.md §8 / documentation-system §8**, require only `ci-ok`, `docs-gate` and `pr-body`.
  - Consider a merge queue for parallel step PRs **[to be validated: availability on this plan]**.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11; documentation-system §8 (assumed — pending Thomas, inbox #26); pending: autopilot.md §8 branch-protection payload (inbox #8, #26); CI: `ci.yml` and `workflow_call` pipelines

### DEP-T-002 · blocker · release-please with `GITHUB_TOKEN` cannot trigger release builds or run checks on its own PR

- **Where:** dev-environment §12 ("Merging the release PR … triggers the image, Helm chart and PyPI builds"); `.github/workflows/release-please.yml:17-20` (no `token:`); `release-guard.yml`; documentation-system §8 and §9.
- **Evidence:**
  - GitHub: events triggered by `GITHUB_TOKEN` "will not create a new workflow run", except `workflow_dispatch` and `repository_dispatch` ([GitHub docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)).
  - release-please-action README: resources created with `GITHUB_TOKEN` "will not trigger future GitHub actions workflows" ([release-please-action](https://github.com/GoogleCloudPlatform/release-please-action)).
  - depictio avoids this because a human pushes its tags (`bump-with-helm.sh:16-60`). Its bot PRs opened with `GITHUB_TOKEN` (`depictio-docs/.github/workflows/update-on-release.yaml:111-114`, `nfcore-release-monitor.yaml:120-122`) get no CI.
- **Problem:**
  - Tag-triggered builds never start.
  - The release PR gets no required checks, so it can never auto-merge, and `release-guard.yml` never runs on it.
  - The generated OpenAPI docs PR has the same problem.
  - autopilot.md and documentation-system §8 disagree on whether 0.x release PRs auto-merge.
- **Proposal:**
  - In **dev-environment §12**, run release-please with a GitHub App installation token (`actions/create-github-app-token`), scoped to `contents` and `pull-requests`. Alternatively, chain the builds in the same workflow, gated on the action's `releases_created` output **[to be validated: output name]**.
  - Use the same App token for every bot PR.
  - Settle the release-PR rule once, in documentation-system §8, and link to it from autopilot.md.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11, §12; documentation-system §9 (assumed — pending Thomas, inbox #26); pending: release-PR merge rule (inbox #26); CI: app token in `release-please.yml`; GitHub App (Thomas, inbox #8)

---

## Major

### DEP-T-003 · major · "Image built from the published wheel" is not reproducible and cannot produce `sha`, `edge` or `pr` images

- **Where:** architecture §7.4 (`FROM python:3.13-slim`, then `uv pip install "spectio[…]==X.Y.Z"`); dev-environment §12 (image tags); `staging.yml`.
- **Evidence:**
  - depictio uses `uv sync --frozen …` (`docker-images/Dockerfile.api:102,115`), but falls back silently to an unlocked resolve, `|| uv sync …` (`:104,117`).
  - Its base image is pinned by digest (`Dockerfile.api:45`).
  - Its PyPI-based "try" image has to poll the index up to 30 × 30 s (`build-try-image.yaml:58-59`).
  - pixi runs unlocked in CI (`depictio-ci.yaml:356-363`).
- **Problem:**
  - The same tag builds differently on different days.
  - No wheel exists on PyPI for `edge`, `pr-<n>` or `sha-<7>`.
  - Building right after publishing races the index propagation.
  - The base image tag moves.
- **Proposal:** in **architecture §7.4**, add "Image build":
  1. CI builds the wheel once per commit.
  2. The image installs that wheel with `--no-deps`, plus `uv export --frozen --require-hashes` constraints.
  3. A release publishes the same wheel bytes to PyPI, with the wheel's sha256 in an OCI label.
  4. The base image is pinned by digest and updated by a bot.
  5. No unlocked fallback.
  6. `pixi.lock` is committed for the `-engines` image.
- **Found by:** depictio-liaison
- **Status:** accepted (TRIAGE1, 2026-10-27); not applied (APPLY1): blocked by inbox #26 (architecture §7.4)

### DEP-T-004 · major · Image architectures are not specified

- **Where:** architecture §7.4 and §7.5; dev-environment §11 and §12.
- **Evidence:**
  - depictio builds amd64 on PRs, and amd64 + arm64 on releases, on native runners (`ubuntu-24.04-arm`, no QEMU), merged by digest (`build-images.yaml:66-81,156,231-294`).
  - It runs a smoke test per architecture (`:296-312`).
- **Problem:** Apple Silicon laptops, and arm64 HPC or Kubernetes nodes, would run emulated or fail. The `-engines` runner image is the most exposed.
- **Proposal:**
  - In **architecture §7.4**, publish multi-arch images for `spectio`, `spectio-runner` and `-engines` on releases, and amd64 on PRs.
  - In **dev-environment §11**, add a quick-start smoke test per architecture (DEP-T-021).
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11 (quick-start.yml); pending: architecture §7.4 multi-arch publishing (inbox #26); CI: quick-start.yml, multi-arch builds

### DEP-T-005 · major · Supply-chain evidence (SBOM, provenance, signatures, scanning) is deferred to phase 3

- **Where:** architecture §9 ("phase 3 … signed images (cosign), SBOM"); dev-environment §11.
- **Evidence:**
  - depictio has no CodeQL, Trivy or Grype, no dependency review, no SBOM, no cosign and no attestations.
  - `bandit` is installed (`pyproject.toml:100`) but runs nowhere.
  - PyPI uses trusted publishing (`publish-pypi.yaml:152-153,190-191`).
- **Problem:**
  - Institutions, and a runner holding cluster credentials, need provenance from the first artifact.
  - Adding it later changes tags and digests that users have already pinned.
- **Proposal:**
  - **`security.yml` in dev-environment §11:**
    - CodeQL (Python, JS) and dependency review on PRs;
    - Trivy or Grype on images, failing on fixable critical issues;
    - `zizmor` on workflows.
  - **From 0.1.0, in architecture §7.4 and §7.5:**
    - SBOM and provenance attestations on images and the chart (buildx `provenance: mode=max`, `sbom: true`, `actions/attest-build-provenance`);
    - keyless cosign;
    - `gh attestation verify` in the install docs.
  - Move this row out of phase 3.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): installation/index.md; architecture §9; dev-env §11, §12 (assumed — pending Thomas, inbox #26); pending: architecture §7.4 link (inbox #26); CI: security.yml, attestation and signing steps

### DEP-T-006 · major · Publishing about 30 artifacts per release has no specified order, publishers or upgrade test

- **Where:** dev-environment §12; architecture §6 (the core packages, about 24 plugins, `nf-spectio`, `snakemake-logger-plugin-spectio`, the npm packages); architecture §10 risk 6.
- **Evidence:** depictio's `publish-pypi.yaml` has:
  - a tag/version check (l.36-43);
  - `twine check --strict` and a wheel-content check (l.77-80);
  - an upgrade-from-published matrix with pip and uv that fails if any file went missing (l.92-138);
  - one GitHub environment per project, with trusted publishing (l.145-207);
  - a strict order through `needs:` (l.184, 203).
- **Problem:** Spectio has the same alias and file-move risk, ten times as many projects, an SDK that plugins pin, and no stated release path for the Nextflow plugin registry.
- **Proposal:** in **dev-environment §12**, add "Publishing":
  - the order `spectio-sdk` → `spectio` → `spectio-server` → plugins → `spectio-cli`, with `skip-existing`;
  - one trusted publisher and environment per project, registered before 0.1.0;
  - the tag/version check and `twine check --strict`;
  - an upgrade-from-previous-release job;
  - the `nf-spectio` release steps **[to be validated]**;
  - npm provenance.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §12; pending: CI: publishing workflow; trusted publishers (Thomas)

### DEP-T-007 · major · Repository secrets are readable from any branch an agent pushes

- **Where:** dev-environment §7 ("agents never receive tailnet keys") and §8; `staging.yml` (repository secrets `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `STAGING_ADMIN_TOKEN`).
- **Evidence:**
  - depictio scopes its sensitive jobs to GitHub environments: `embl-demo-dev` and `embl-demo` (`deploy-embl-selfhosted.yaml:50,148`), and `pypi-*` (`publish-pypi.yaml:149-208`).
  - Its EMBL deploy runs only on `workflow_dispatch`.
- **Problem:** a workflow edited on any pushed branch can read repository-level secrets, which defeats "agents never hold tailnet credentials".
- **Proposal:** in **dev-environment §7 and §8**:
  - move every deploy and publish secret into environments (`staging`, `pypi-*`, `ghcr-release`) restricted to `main` and tags, with required reviewers where needed;
  - keep no repository-level secrets other than read-only ones;
  - add a `zizmor` check against `pull_request_target` and secrets in untrusted contexts.
- **Found by:** depictio-liaison
- **Status:** rejected (TRIAGE1, 2026-10-27): not reproducible: `staging.yml`, its tailnet secrets and the tailnet VM no longer exist (decision log 2026-10-26, dev previews); dev-env §8 already keeps deploy credentials in GitHub environments (citing DEP-T-007), and `previews.yml` reads its secrets from the `previews` environment

### DEP-T-008 · major · "Never auto-merged" paths are a convention, not an enforced rule

- **Where:** documentation-system §8; autopilot.md §8.
- **Evidence:**
  - depictio has `CODEOWNERS` (`* @weber8thomas`). Spectio has none.
  - The protection payload in autopilot.md does not set `require_code_owner_reviews`.
- **Problem:** a workflow change that passes the checks and the bot review would auto-merge.
- **Proposal:**
  - Add `.github/CODEOWNERS` assigning `@weber8thomas` to `.github/**`, `.claude/**`, `docs/playbooks/pipeline.yaml`, the server's auth code, `plugins/auth-*/**` and `**/secrets*`.
  - Set `"require_code_owner_reviews": true`.
  - Check whether a bot approval counts when the same identity opens the PRs **[to be validated]**.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DEP-T-009 · major · No dependency bot, and Spectio's workflows still use v4 actions

- **Where:** dev-environment §1 and §11; `.github/workflows/*.yml` (`checkout@v4`, `upload-artifact@v4`, `setup-node@v4`, `setup-uv@v6`, `github-script@v7`).
- **Evidence:**
  - depictio's `.github/dependabot.yml` updates uv monthly in two groups and github-actions monthly: "Keep CI action versions current (e.g. the Node 20 -> 24 runner deprecation)" (l.20-59).
  - Its actions are at `checkout@v7`, `upload-artifact@v7` and `setup-uv@v7`.
- **Problem:** digest-pinned images and the engine pins (`dev/versions.env`, `corpus.yaml`) drift without a bot, and Node 20 actions face deprecation **[to be validated: date]**.
- **Proposal:** in **dev-environment §1**, add "Dependency updates":
  - Renovate (or Dependabot) for uv, npm, github-actions (pinned by SHA), docker digests, helm and pre-commit;
  - regex managers for `dev/versions.env` and `corpus.yaml`;
  - grouped monthly PRs, plus security updates as they come;
  - everything through the `ci-ok` gate.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §1; pending: CI: `renovate.json`, action bumps and SHA pins

### DEP-T-010 · major · The Helm chart has no CI, no values schema and no immutability rule

- **Where:** architecture §7.5; dev-environment §11; `depictio-ecosystem-reuse.md` §1.5.
- **Evidence:**
  - **Chart CI** (`test-and-package-helm-chart.yaml`):
    - minikube from `medyagh/setup-minikube@master` (l.62);
    - lint, package and template with a grep (l.160-195);
    - shell probes after install (l.213-1290);
    - a push on every main push that touches the chart (l.3-11, 1296-1299), while the version only changes at release (`bump-with-helm.sh:28`).
  - **Not there:** no `values.schema.json`, no `templates/tests/`, no `ct`, no upgrade test.
  - **Secrets via `lookup`** (`templates/secrets.yaml:12,44-50`), which breaks `helm template` and GitOps.
  - **No probes on the backend and worker** (`templates/deployments.yaml`).
- **Problem:**
  - Spectio's claims are not verified: PodSecurity `restricted`, NetworkPolicies, the migrate hook and the probes.
  - An umbrella chart pinned to depictio's mutable date versions is not reproducible.
- **Proposal:**
  - **`chart.yml` in dev-environment §11:**
    - `helm lint --strict`;
    - `values.schema.json` generated from the Pydantic settings;
    - `kubeconform` against the supported minors;
    - `ct install` and `ct upgrade` on kind with `pod-security.kubernetes.io/enforce=restricted`;
    - `helm test` hooks calling `/health/ready`.
  - **In architecture §7.5:**
    - semver chart versions that are immutable;
    - `existingSecret` for every Secret, and no `lookup`;
    - the depictio dependency pinned by digest.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §7.5; dev-env §11; pending: depictio chart digest pin (inbox #21); CI: chart.yml

### DEP-T-011 · major · In-place upgrades are tested only through restore

- **Where:** dev-environment §6 tier 5 and §14 (1.0 gate item 5); admin §4.3.
- **Evidence:**
  - depictio restores weekly a backup made by the previous stable image (`backup-compat-cross-version.yaml:45-60`), and tests package upgrades (`publish-pypi.yaml:92-138`).
  - It has no in-place stack upgrade test.
- **Problem:** the real upgrade path, in place with a pre-upgrade backup and then migrations, is never exercised, and neither is skipping versions.
- **Proposal:** in **dev-environment §6 tier 5 and §11**, add `upgrade.yml`, weekly and on release PRs:
  - N-1 → N and N-3 → N, on bundle, Compose and Helm (`ct upgrade`);
  - seed with synthetic runs, then assert the schema is at head, the backup exists, runs and gates are intact, and tokens behave as specified;
  - report the results on the 1.0-gate checklist.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §6, §11, §14; pending: CI: upgrade.yml

### DEP-T-012 · major · Component tests run on SQLite only; the Postgres-only code paths go untested

- **Where:** dev-environment §6 (tier 2 "server with SQLite"); architecture §7.2 and §7.6 (`SKIP LOCKED`, `LISTEN/NOTIFY`, advisory locks); admin §4.3 (Alembic batch mode).
- **Evidence:**
  - depictio's unit suite runs on mongomock (`pyproject.toml:109-110`), and its comments admit runtime-only regressions the suite cannot see (`pyproject.toml:79-80`).
  - `testcontainers` is used in a single test.
- **Proposal:** in **dev-environment §6**:
  - run tiers 1–2 on both SQLite and Postgres 18, marked `@pytest.mark.db(...)`;
  - add a migration test from empty and from each frozen fixture on both dialects;
  - run the two-replica tests on Postgres in tier 3.
- **Found by:** depictio-liaison
- **Status:** applied (APPLY1, 2026-10-27): dev-env §6

### DEP-T-013 · major · Co-hosting assumes depictio lives under `/depictio`, but depictio's UI owns the root

- **Where:** api-and-data-model §13 ("`/depictio/…` and `/spectio/…` on one domain"); architecture §8; dev-environment §7 (Caddy); ecosystem-reuse §2 item 7.
- **Evidence:**
  - Only depictio's API is prefixed (`/depictio/api/v1`).
  - The SPA is built with Vite `base: '/dashboard/'` (`depictio/viewer/vite.config.*:77`).
  - nginx claims `/dashboard/`, `/(auth|dashboards|dashboard-edit|projects|about|admin|profile|groups|cli-agents)`, `/static/`, `/assets/` and `= /` (`docker-images/nginx.conf.template:84-102,171,178,190`).
  - The Helm ingress is host-based, with path `/` for each host (`templates/ingress.yaml:49-76`).
- **Problem:** a `/depictio` UI prefix needs a depictio rebuild, and Spectio at the root would collide with depictio's paths.
- **Proposal:**
  - In **api-and-data-model §13** (owner): depictio keeps the root of its host, and Spectio is always under `/spectio/` (UI, API, assets), or on its own host.
  - Ask depictio for a configurable base path only if ever needed.
  - Point dev-environment §7 and architecture §8 to §13.
- **Found by:** depictio-liaison
- **Status:** accepted (TRIAGE1, 2026-10-27) — the co-hosting default (separate hosts or one origin) stays with R5 SEC-109; not applied (APPLY1): blocked by inbox #23 (co-hosting default, SEC-109)

### DEP-T-014 · major · Sharing depictio's SeaweedFS needs per-bucket identities that depictio's Compose does not configure

- **Where:** architecture §7.4 ("share one SeaweedFS with separate buckets and credentials"); ecosystem-reuse §1.5 and §2 item 6.
- **Evidence:**
  - `weed mini` runs with one static admin identity, defaults `minio` / `minio123`, a single bucket `depictio-bucket` and no identities file (`docker-compose.yaml:57-63`).
  - depictio's orphan cleanup deletes every top-level prefix of its bucket that is not registered (`api/v1/endpoints/utils_endpoints/core_functions.py:179-189`, run by `api/v1/tasks/cleanup_tasks.py:198`).
  - depictio's own deploy notes that sharing a bucket "would delete demo's data" (`deploy-embl-selfhosted.yaml:79-83`).
- **Proposal:**
  - In **architecture §7.4**, when co-hosted:
    - Spectio uses its own bucket `spectio`, with its own S3 identity limited to it, through an identities file mounted by `compose.depictio.yaml` **[to be validated: `weed mini` support]**;
    - otherwise Spectio runs its own SeaweedFS;
    - Spectio never receives depictio's root keys.
  - In **ecosystem-reuse §2**:
    - fix the bucket name;
    - request that depictio's Compose accept an identities file.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): depictio-ecosystem-reuse §2 item 6 (assumed — pending Thomas, inbox #22); pending: architecture §7.4 bucket and identity (inbox #26); identities-file request to depictio (Thomas, inbox #22, #27)

### DEP-T-015 · major · How Spectio gets depictio's JWT public key on Kubernetes is undefined

- **Where:** architecture §8 (Compose only); authentication-and-access (depictio trust); ecosystem-reuse §3 item 5.
- **Evidence:**
  - Keys are generated at first boot into `keys_dir` (`api/v1/key_utils.py:134`).
  - On Kubernetes they sit on a ReadWriteMany PVC (`values.yaml:48-50`, `templates/pvcs.yaml:44`).
  - There is no JWKS or public-key route.
  - The demo `wipe` erases the keys volume (`deploy-embl-selfhosted.yaml:27-31`).
- **Proposal:** in **authentication-and-access** and **architecture §7.5**:
  - on Kubernetes, verify depictio tokens through `GET /depictio/api/v1/auth/me` (cached per token) until depictio exposes JWKS;
  - never mount depictio's keys volume;
  - on a signature failure, refetch at most once a minute, and raise a Health warning on key rotation;
  - keep the JWKS request in ecosystem-reuse §3, needed for Helm.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DEP-T-016 · major · How `depictio-cli` gets onto runners, and at which version, is unspecified

- **Where:** api-and-data-model §13.3 (the runner runs `depictio-cli ingest`); cli-and-shared-libraries §6 (runner under 80 MB).
- **Evidence:**
  - depictio's base install is about 0.9 GB (research `depictio-cli-packaging.md` §3.1).
  - depictio publishes a CLI image, `ghcr.io/depictio/depictio-cli` (`build-images.yaml:14-16`, `docker-images/Dockerfile.cli:103`).
  - There is no version negotiation; the server reports its version at `/depictio/api/v1/utils/status`.
- **Proposal:** in **api-and-data-model §13.3**, the sink reads the depictio version from `utils/status`, then uses, in this order:
  1. a site-configured `depictio_cli_executable`;
  2. `ghcr.io/depictio/depictio-cli:<server version>` through Apptainer or Docker;
  3. `uvx depictio-cli==<server version>`.

  The choice is recorded in the hand-off record, and a `spectio doctor` check is added.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.3 step 6; pending: cli §2 `doctor` depictio-cli check (inbox #22)

### DEP-T-017 · major · depictio is not pinned anywhere in Spectio's toolchain or CI

- **Where:** dev-environment §1 (toolchain table), §6 tier 5, §7, §8.
- **Evidence:**
  - 23 version tags between 2026-10-05 and 2026-10-23.
  - Image tags are only `<version>` and `next`, and `next` also moves on betas (`build-images.yaml:280-282`).
  - `stable` is a git tag moved by force (`bump-with-helm.sh:55-60`).
- **Proposal:**
  - Add `DEPICTIO_VERSION` to `dev/versions.env`.
  - Test tier 5 against the minimum supported version and the latest stable.
  - Declare `depictio >=X,<2` in `spectio-plugin-depictio`.
  - The weekly `depictio-liaison` routine opens the bump PRs.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §8; dev-env §1, §6, §8 (assumed — pending Thomas, inbox #22); pending: tool: `DEPICTIO_VERSION` in `dev/versions.env`

### DEP-T-018 · major · No Python or OS/architecture matrix for the base install and the runner

- **Where:** architecture §7.3 ("Python ≥ 3.11"); cli-and-shared-libraries §6; dev-environment §1 and §11.
- **Evidence:**
  - depictio runs its base-install job on the minimum Python, 3.11, asserting that server dependencies are absent (`cli-base-install.yaml:38-56`).
  - Its local-server smoke runs on `ubuntu-24.04`, `ubuntu-24.04-arm` and `macos-15` (`local-server-smoke.yaml:45`).
- **Proposal:**
  - Run the base-install and runner tests on Python {3.11, 3.13, 3.14} × {linux-x86_64, linux-aarch64, macOS-arm64}: the full grid nightly, a subset on PRs.
  - Test the server on 3.13.
  - Declare the supported Python range once, in architecture §7.3.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §4, §7.3; cli §6; dev-env §11 (assumed — pending Thomas, inbox #26); pending: macOS-arm64 leg (inbox #26); CI: base-install.yml

---

## Minor

### DEP-T-019 · minor · CI hygiene: concurrency, timeouts, fork guards, docs-only skips

- **Where:** dev-environment §11; Spectio's workflows (only `staging.yml` sets `concurrency`; only `pipelines-real.yml` sets `timeout-minutes`).
- **Evidence:** `depictio-ci.yaml`:
  - concurrency (`:20-28`);
  - timeouts, because "a stalled registry push would otherwise sit here for six hours" (`:437-439`);
  - fork guards (`:412-416`);
  - docs-only skips (`:116-121`);
  - image reuse by content hash (`:161-202`).
- **Proposal:** add "Workflow conventions" to dev-environment §11:
  - concurrency per PR and ref;
  - `timeout-minutes` on every job;
  - a fork guard;
  - docs-only detection;
  - `permissions:` per job;
  - actions pinned by SHA.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11; pending: CI: apply the conventions to the existing workflows

### DEP-T-020 · minor · depictio's security audit scripts are manual and have already drifted

- **Where:** ecosystem-reuse §1.5 ("copy all, same guards").
- **Evidence:**
  - No workflow calls `scripts/security_audit_*.sh`.
  - Static check 1.10 expects `DEPICTIO_S3_ROOT_PASSWORD:?…` (`security_audit_compose.sh:188-196`), while Compose uses `:-minio123` (`docker-compose.yaml:59-60`).
- **Proposal:**
  - In ecosystem-reuse §1.5, change "copy" to "copy and run in CI".
  - In dev-environment §11, run the static audit on PRs and the live audit nightly.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11; pending: depictio-ecosystem-reuse §1.5 verdict (inbox #26); CI: deploy-audit.yml

### DEP-T-021 · minor · Make release notes and the quick start provably true

- **Where:** documentation-system §6; dev-environment §12 and §13.
- **Evidence:**
  - `changelog_generator.sh:29-32` lists `ghcr.io/depictio/depictio:{version,latest,stable,edge}`, while only `depictio-{api,worker,viewer,cli}:{version,next}` are published (`build-images.yaml:280-282`).
  - depictio does boot its Compose quick start with no `.env`, per architecture, and asserts the version, `/openapi.json` and first-boot seeding (`build-images.yaml:335-467`).
- **Proposal:**
  - Generate the release-note artifact list from `docker/metadata-action` output, and verify each entry with `docker manifest inspect`.
  - Add a quick-start job per architecture, run from the docs' `compose.yaml` alone.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §11; documentation-system §6; pending: CI: release-notes artifact check, quick-start.yml

### DEP-T-022 · minor · Pick the type checker now, and keep one source for tool versions

- **Where:** dev-environment §6 tier 0 ("ty or mypy").
- **Evidence:**
  - depictio's ty gate is narrowed to `depictio/models/` after about 280 diagnostics (`depictio-ci.yaml:242-250`).
  - Its pre-commit ruff `v0.15.16` differs from `ruff==0.16.1` in the dev dependencies.
  - `pre-commit run --all-files` is commented out in CI (`:252-255`).
- **Proposal:**
  - Choose one type checker and gate every package from the first commit, with `--strict` on `spectio-sdk`.
  - Use `language: system` pre-commit hooks through `uv run`.
  - Run pre-commit in tier 0.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §6; pending: tool: `.pre-commit-config.yaml`

### DEP-T-023 · minor · Test-suite safety nets: collection guard, coverage, flaky tests, destructive e2e

- **Where:** dev-environment §6.
- **Evidence:**
  - Recipe tests were "written but never run in CI", because their directory was missing from `testpaths` (`pyproject.toml:293-297`).
  - `pytest-cov` is installed but not enforced.
  - Playwright retries twice in CI, and the destructive specs run in their own project (`playwright.config.ts:16-17,50-58,80-87`).
- **Proposal:**
  - Check that every `test_*.py` is collected.
  - Report diff coverage, advisory before 0.2.
  - Quarantine flaky tests, mirroring `engine_faults`: a marker, an issue, removal within 2 weeks.
  - Run destructive e2e specs last, in an isolated Playwright project.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): dev-env §6; pending: tool: collection guard, diff-coverage report

### DEP-T-024 · minor · Generate the telemetry field docs, and snapshot GitHub traffic weekly

- **Where:** telemetry-and-analytics §2.3 and §2.4.
- **Evidence:**
  - `scripts/gen_telemetry_docs.py --check` runs in CI (`telemetry-ci.yaml:96-102`).
  - A weekly traffic snapshot exists, because "GitHub retains only the last 14 days" (`telemetry-metrics.yaml:1-15,112-123`).
- **Proposal:**
  - Generate the field page from the Pydantic schema, with `--check` in CI.
  - Snapshot traffic weekly, with a token kept in an environment.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): telemetry §2.3, §2.4; pending: tool: field-docs generator, weekly traffic snapshot workflow

### DEP-T-025 · minor · SECURITY.md, issue templates and a support channel

- **Where:** dev-environment §14.
- **Evidence:**
  - depictio has issue templates and a config linking the docs and Discussions.
  - It has neither `SECURITY.md` nor `CONTRIBUTING.md`.
  - Spectio has neither `SECURITY.md` nor issue templates.
- **Proposal:** as a private-alpha entry condition, add:
  - `SECURITY.md`, with private vulnerability reporting;
  - issue forms (a bug with `spectio doctor` output, gate feedback, a plugin request);
  - Discussions.
- **Found by:** depictio-liaison
- **Status:** accepted (TRIAGE1, 2026-10-27); not applied (APPLY1): blocked by inbox #17 (dev-env §14 private-alpha list); repo files are outside docs

### DEP-T-026 · minor · Decide the GitHub organisation and reserve names before the first publish

- **Where:** architecture §7.4 (`ghcr.io/<org>/spectio`); cli-and-shared-libraries §4.
- **Evidence:**
  - On 2026-10-26, PyPI returned 404 (free) for `spectio`, `spectio-server`, `spectio-sdk`, `spectio-cli`, `bioplatform-client`, `bioplatform-models` and `snakemake-logger-plugin-spectio`.
  - npm returned 404 for `@spectio/client`.
- **Proposal:**
  - Add an inbox item: create the organisation before 0.1.0.
  - Register PyPI pending publishers and the npm scope **[to be validated: what breaks on a transfer]**.
- **Found by:** depictio-liaison
- **Status:** rejected (TRIAGE1, 2026-10-27): already handled: inbox #9 was opened from this finding and answered (Thomas, 2026-10-26: stay under `weber8thomas` for now, move later); reserving the names goes with that move

### DEP-T-027 · minor · release-please settings cannot hold a separately versioned SDK

- **Where:** dev-environment §12; `release-please-config.json` (`include-component-in-tag: false`); architecture §7.5.
- **Problem:** a second component would also tag `vX.Y.Z` and collide **[to be validated with a dry run]**. The chart's version policy is not stated.
- **Proposal:**
  - Use component tags for `spectio-sdk` (`spectio-sdk-v1.2.0`), and keep `vX.Y.Z` for the core.
  - The chart `version` equals the app version, with no date versions.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §7.5; dev-env §12; pending: tool: `include-component-in-tag` in release-please-config.json

### DEP-T-028 · minor · A "Try Spectio" Codespace for design partners

- **Where:** dev-environment §14.
- **Evidence:**
  - `.devcontainer/try/devcontainer.json:1-9` opens `ghcr.io/depictio/depictio-try:latest`.
  - The image is rebuilt after each stable release and smoke-tested (`build-try-image.yaml:11,36-40,95-104`).
- **Proposal:**
  - Build a try image: `spectio[server]`, a local runner and the synthetic pipelines.
  - Open it with one Codespaces link from the landing page.
- **Found by:** depictio-liaison
- **Status:** inbox (TRIAGE1, 2026-10-27)

### DEP-T-029 · minor · `/metrics` is a line, not a contract

- **Where:** admin-and-operations §3.5.
- **Evidence:** depictio has no Prometheus, OpenTelemetry or Sentry code, and no ServiceMonitor.
- **Proposal:**
  - Name the metrics: runs by state, gate wait time, task queue depth and age, outbox lag, runner heartbeats, request latency per route template.
  - State who may scrape: a separate port or a token.
  - Add an optional ServiceMonitor.
  - Propagate `traceparent` and `request_id` to runners.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): admin §3.5 (assumed — pending Thomas, inbox #26); pending: who may scrape `/metrics` (inbox #26)

### DEP-T-030 · minor · The depictio plugin is one package in §8 but two directories in §6

- **Where:** architecture §6 (`auth-depictio/`, `sink-depictio/`) vs §8 ("two plugins in one package, `spectio-plugin-depictio`").
- **Proposal:** use one directory, `plugins/depictio/`.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §6 (plugins/ line); pending: auth §2 `auth-depictio` (inbox #21)

### DEP-T-031 · minor · depictio rewrites history, so audits should cite tags, not only SHAs

- **Where:** every `docs/research/depictio-*.md`; CLAUDE.md, external facts.
- **Evidence:** `backup-before-author-rewrite` (2026-08-04) and `backup/pre-*` tags show history rewritten on the default branch.
- **Proposal:**
  - Cite `tag + SHA`.
  - Record `git archive <sha> | sha256sum` in each audit note.
  - Add this to documentation-system §10.
- **Found by:** depictio-liaison
- **Status:** partly applied (APPLY1, 2026-10-27): documentation-system §10; pending: CLAUDE.md External facts rule; retrofit research notes at next re-audit

### DEP-T-032 · minor · Two demo targets that the specs never reconcile

- **Where:** ecosystem-reuse §1.5 ("reuse the EMBL deployment target") vs dev-environment §7 (tailnet VM) and §14 (public beta demo).
- **Evidence:** depictio deploys its demos with `workflow_dispatch` on `[self-hosted, embl-deploy]`, with values files on the runner's disk, `helm --atomic --wait` and `--insecure-skip-tls-verify` (`deploy-embl-selfhosted.yaml:12-13,49,96-108,130-142`).
- **Proposal:**
  - Staging and previews run on the tailnet VM; the public beta demo runs on the EMBL target.
  - The EMBL deploy is `workflow_dispatch`-only, with an environment and a reviewer, and without `--insecure-skip-tls-verify`.
- **Found by:** depictio-liaison
- **Status:** rejected (TRIAGE1, 2026-10-27): not reproducible: the 2026-10-26 dev-previews decision dropped the tailnet VM; dev-env §7.4 now puts the public instance on EMBL Kubernetes, `workflow_dispatch` only, behind an environment with a reviewer and without `--insecure-skip-tls-verify` (citing DEP-T-032), which matches ecosystem §1.5

---

## Things depictio does that Spectio should deliberately not copy

1. **One broad PAT for everything.** `secrets.GHCR_PAT` is used 17 times. Use `GITHUB_TOKEN` with `packages: write`, and a GitHub App token for cross-repository calls.
2. **Silent unlocked fallbacks in image builds** (`uv sync --frozen … || uv sync …`).
3. **Unpinned or branch-pinned actions** (`medyagh/setup-minikube@master`); pin by SHA.
4. **Mutable chart versions,** and OCI tags that get overwritten.
5. **A release job that pushes to `main`** and rewrites a 4.2 MB `CHANGELOG.md`.
6. **Moving pointers with mixed meaning:** a force-moved `stable` git tag, and a `next` image tag that also moves on betas.
7. **Site-specific values in the public chart** (seven `values-embl-*.yaml` files).
8. **`lookup`-based secret generation.**
9. **Signing keys on a ReadWriteMany PVC,** generated at first boot.
10. **No probes on the API and worker** in the chart.
11. **Narrowing quality gates instead of paying the debt.**
12. **Manual audit scripts that drift, and tests outside `testpaths`.**
13. **Bot PRs opened with `GITHUB_TOKEN`,** so no CI runs on them.
14. **`helm --insecure-skip-tls-verify`,** and secrets files on a self-hosted runner's disk.
15. **History rewrites on a shared default branch.** Spectio's own clean-up (inbox #5) happened once, before anyone cloned.
16. **Dead workflows kept** instead of deleted.
17. **Release notes that list artifacts nobody checked.**

## Sources (external)

- [GitHub Docs: triggering a workflow (GITHUB_TOKEN events)](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [release-please-action README (tokens, outputs)](https://github.com/GoogleCloudPlatform/release-please-action)
- [GitHub community discussion #27194: a push from a workflow does not trigger `on.push.tags`](https://github.com/orgs/community/discussions/27194)
- PyPI JSON API and npm registry, queried on 2026-10-26.
