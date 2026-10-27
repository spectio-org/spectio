# R5 · Security and threat model (STRIDE per trust boundary)

**Step page:** [R5](../progress/W1/R5.md)

**Round:** R5 (security) · **Date:** 2026-10-26 · **Found by:** security-reviewer · **Status of the round:** triaged (TRIAGE1, 2026-10-27): 4 accepted, 0 rejected, 26 inbox (6 assumed) · triage: [TRIAGE1](../progress/W2/TRIAGE1.md)

**Sources.**
- **Branch and commit:** `autopilot/integration` at `3b209d3`. Line numbers ("l.") and `§n:line` references refer to that commit.
- **Read:** every spec in [`docs/specs/`](../specs/synthesis.md), the decision log ([`log.md`](../decisions/log.md)), decision [0001](../decisions/0001-nextflow-through-nf-spectio.md), and the research notes [`depictio-auth-2026-10-26.md`](../research/depictio-auth-2026-10-26.md) and [`depictio-harmonization.md`](../research/depictio-harmonization.md).
- **Reviewers dispatched:** one, security-reviewer, with the whole design in scope. It returned a full report, so no reviewer failed.
- **Upstream code read** (scratch clones, read only):
  - **nextflow `114f1fe` (2026-10-26):**
    - `ConfigCmdAdapter.groovy:650-651` calls `SecretHelper.hideSecrets(config)` before printing the config.
    - `SecretHelper.groovy:35` defines `SECRET_KEYS = ~/(?im)^AWS.+|.*TOKEN.*|.*PASSWORD.*|.*SECRET.*|.*accessKey.*|.*api_?key.*/`. **Correction made during the merge:** the constant is marked `@deprecated` in favour of `StringUtils.isSensitiveName` (nf-commons `StringUtils.groovy:80`). Whether that function's pattern is the same was not compared **[to be validated]**.
    - `TowerObserver.groovy:383` sends `workflow.params = session.getParams().toPlainMap()`, with no masking.
    - `docs/reference/process/directives/publish-dir.mdx:89` says that `'symlink'` is the default publishDir mode.
  - **nf-core/rnaseq `95dbcd9`:** `nextflow.config:154,331` sets `custom_config_base` to a remote URL, then calls `includeConfig "${params.custom_config_base}/nfcore_custom.config"`.
  - **Slurm** `slurm.conf` ([docs](https://slurm.schedmd.com/slurm.conf.html), read 2026-10-26):
    - `PrivateData`: "By default, all information is visible to all users."
    - `AccountingStoreFlags=job_env` stores "a batch job's environment variables used at job submission".
- **Merge checks.** I opened every quoted passage for each blocker and major finding at `3b209d3` and reproduced all of them, so **none was dropped**.
  - The external file:line claims above were spot-checked in the scratch clones.
  - Claims marked **[to be validated]** keep that mark.
- **Overlap with earlier rounds.** I read the open findings of [R1](R1-consistency.md), [R8b](R8b-depictio-tooling.md) and [R12](R12-ui-scenarios.md).
  - **Not repeated, cited instead:**
    - R8b: DEP-T-007, DEP-T-008, DEP-T-013, DEP-T-014, DEP-T-015, DEP-T-020, DEP-T-025, DEP-T-029.
    - R12: UX-117, UX-124, UX-126, UX-129.
  - **Shared with R1, kept because R5 adds the threat, the attacker and security controls:** SR-031 (loopback), SR-014 (runner Unix account), SR-002 and SR-024 (runner credential, scopes), SR-012 (stale scopes), SR-029 (visibility), SR-004 (`spectio.yml` owner), SR-001 (ingest contract). Each such finding has a **Related** line, and the two should be triaged together.
  - **Removed as duplicates of R1:** two sub-points of the reviewer's report. One is the runner-credential lifetime contradiction, kept in SR-002 and SR-024. The other is the runner channel transport conflict, kept in SR-002.
- **Numbering.** IDs were renumbered in rank order. The reviewer's draft IDs appear as `d1nn` in the table's last column, for traceability only.
- **Risk notation.** L is likelihood and I is impact, each H, M or L.

## Summary

| Severity | Count |
|---|---|
| Blocker | 2 |
| Major | 23 |
| Minor | 5 |
| **Total** | **30** |

Dropped as not reproducible: 0. Merged as duplicates within the round: 0 (one reviewer).

**The five findings that matter most:**
1. **SEC-101 · blocker.** A runner's Unix account is not tied to the people who launch on it. On a group environment, any `launcher`, and any editor who adds a `script:` binding, runs code as a colleague's or an admin's cluster account.
2. **SEC-102 · blocker.** `single` mode trusts `127.0.0.1`. On an HPC login node, which the MVP targets, every other user can drive the owner's runs and get code execution as the owner. A malicious web page can do the same through DNS rebinding.
3. **SEC-104 · major.** No endpoint → action → scope → role matrix exists, so the rule "every endpoint has a principal and a `can()`" cannot be implemented or tested. IDs given in a request body and plugin routes are the likely gaps.
4. **SEC-113 · major.** Identities are linked by email across IdPs, including depictio, which cannot verify email. Group sync is not namespaced, so an IdP group named `admin` can lead to account takeover or admin rights.
5. **SEC-115 · major.** A server compromise means code execution on every runner's Unix account, because runners enforce no local policy. The blast radius is the whole user base on every cluster.

**Recurring themes.**
- Runners are trusted in both directions: SEC-101, 105, 106, 115.
- Bearer artefacts can be forwarded or over-scoped: SEC-108, 117, 122, 123.
- Secrets reach sinks that viewers read: SEC-103, 107, 108.
- Tenancy is stated as a principle but has no enforcement contract per route or per stream: SEC-104, 112, 121, 125.

## Findings table

| ID | Sev. | Title | Boundary | Specs touched | Draft |
|---|---|---|---|---|---|
| SEC-101 | blocker | A runner's Unix account is not tied to the principals who launch on it | Runner ↔ cluster | synthesis, api, ui-spec, schedulers, checking | d102 |
| SEC-102 | blocker | `single` mode trusts loopback, but loopback is shared by every user of a login node | Browser ↔ server | auth, api, architecture | d101 |
| SEC-103 | major | Group credentials reach runners and jobs where any pipeline or scheduler user can read them | Runner ↔ cluster | architecture, checking, ui-spec, schedulers, api | d119 |
| SEC-104 | major | No endpoint → action → scope → role matrix | Service accounts ↔ API | api, auth, admin, architecture | d103 |
| SEC-105 | major | Runner file access is not confined to the run's roots | Runner ↔ cluster | checking, api, ui-spec, synthesis | d114 |
| SEC-106 | major | The runner credential has no route allow-list and can forge the values behind auto-approval | Runner ↔ server | auth, api, checking, synthesis | d115 |
| SEC-107 | major | Secrets can reach params, logs, the task ledger, audit diffs and RO-Crate exports | Tenancy surfaces | architecture, admin, api, synthesis | d118 |
| SEC-108 | major | Ingest credentials for observed runs are undefined and can leak through command lines and captured config | Engine plugins ↔ ingest | ui-spec, auth, api, synthesis | d117 |
| SEC-109 | major | Co-hosting on one origin merges depictio's and Spectio's trust; the reports' "separate origin" is undefined | Co-hosting proxy | api, synthesis, checking, architecture | d108 |
| SEC-110 | major | RO-Crate, project and workflow imports are unvalidated paths for code, paths and forged history | Backups and imports | api, synthesis, admin, cli | d121 |
| SEC-111 | major | Agent gate decisions are not bounded or reversible, and record a self-reported identity | AI agents ↔ gates | synthesis, ui-spec, api, checking | d123 |
| SEC-112 | major | SSE, the event log and search have no tenancy filter, revocation rule or rule for events without a project | Tenancy surfaces | api, schedulers, synthesis, admin | d111 |
| SEC-113 | major | Identities are linked by email across IdPs; group sync is not namespaced or kept away from protected groups | Sign-in methods | auth, api, admin | d106 |
| SEC-114 | major | `spectio.yml` from a workflow repository can loosen gate policy and add code with each new version | AI agents ↔ gates | ui-spec, checking, api | d122 |
| SEC-115 | major | A server compromise is code execution on every runner's account; runners hold no local policy | Runner ↔ server | synthesis, architecture, api | d116 |
| SEC-116 | major | Event bridges share one principal across devices and send every project to one topic | Event bridges | architecture, admin, schedulers | d125 |
| SEC-117 | major | Share links contradict the guest, grant and gate-policy rules, and can be forwarded as bearer invitations | Sign-in methods | auth, api | d104 |
| SEC-118 | major | Outbound HTTP from webhooks, plugins, WES and imports has no SSRF policy | Plugins ↔ core | api, architecture | d112 |
| SEC-119 | major | Backups put signing and secret-store keys in an archive whose encryption is optional; restore accepts uploads | Backups and imports | admin, cli | d120 |
| SEC-120 | major | depictio JWT trust accepts tokens Spectio cannot audience-check or revoke, and mirrors depictio admin | depictio trust | auth, api | d107 |
| SEC-121 | major | `instance` visibility means "everyone", so anonymous guests can read internal projects on public instances | Tenancy surfaces | api, auth | d109 |
| SEC-122 | major | Gate decisions through embed tokens are attributed to the host's service account | Host page ↔ embeds | api, auth | d124 |
| SEC-123 | major | Provisioning returns a full sign-in link for the provisioned email to the calling service account | Sign-in methods | auth | d105 |
| SEC-124 | major | Plugins run in-process with full trust; "no database session" is a convention, not a boundary | Plugins ↔ core | architecture | d126 |
| SEC-125 | major | Idempotency keys are not scoped to the caller | Service accounts ↔ API | api | d110 |
| SEC-126 | minor | Browser hardening defaults are not written down | Browser ↔ server | auth, telemetry, admin, ui-spec | d127 |
| SEC-127 | minor | Admins can sign in as any user without a record; sensitive admin actions have no step-up | Sign-in methods | auth, api, admin | d128 |
| SEC-128 | minor | Revocation latency, deactivation, and abuse limits on ingest and SSE | Engine plugins ↔ ingest | auth, admin, api | d130 |
| SEC-129 | minor | OIDC device flow and IdP-initiated SAML need explicit safeguards | Sign-in methods | auth, api | d129 |
| SEC-130 | minor | `webhooks.secret_hash` cannot produce HMAC signatures | Tenancy surfaces | api | d113 |

Spec short names: [auth](../specs/authentication-and-access.md), [api](../specs/api-and-data-model.md), [architecture](../specs/architecture-plugins-and-packaging.md), [admin](../specs/admin-and-operations.md), [checking](../specs/checking-scenarios.md), [schedulers](../specs/schedulers-and-monitoring.md), [synthesis](../specs/synthesis.md), [ui-spec](../specs/ui-spec.md), [cli](../specs/cli-and-shared-libraries.md), [telemetry](../specs/telemetry-and-analytics.md), [ecosystem-reuse](../specs/depictio-ecosystem-reuse.md).

---

## Blockers

### SEC-101 · blocker · A runner's Unix account is not tied to the principals who launch on it

- **Where:** synthesis §7quater l.339 and l.353; api §6 l.141, l.149, §12 item 4 (l.283); ui-spec §4.8 l.132 and l.137; schedulers §6 l.210; checking §7 l.192.
- **Evidence:**
  - The runner "runs on the login node, under the user's account" (synthesis l.339), and "An administrator can do this for everyone" (l.353).
  - "Clusters and their credentials belong to groups, not to users" (api §6, l.141). Environment grants go to projects or groups.
  - "Move to another runner on the same cluster" (ui-spec §4.8, l.137).
  - "the runner submits through `ssh login` or REST" (schedulers §6, l.210), with no identity stated.
  - "`script:<command>`: any program printing `{item: {metric: value}}` as JSON" (checking §7, l.192). Editors "edit workflow manifests" (api §6, l.149).
- **Problem.**
  - **Attacker and asset:** any principal with `launcher` on a project granted a group environment, or any `editor` who writes an overlay with a `script:` binding. They get code execution and data access as the runner owner's Unix account, which may belong to a colleague, a P.I. or an admin.
  - **What follows on the cluster:**
    - other people use one person's files, quotas and fairshare;
    - accounting is attributed to the wrong person;
    - the site's rules on account sharing are likely breached **[to be validated per site AUP]**.
  - Moving a run to another runner silently changes the Unix identity it runs under.
  - **Existing mitigation:** none. Open question api §12.4 names the gap but does not answer it.
- **Risk:** L H × I H. This is the default way a group would use a shared cluster.
- **Proposal:**
  - **Design (api §6 owns it; schedulers §6):** an environment records `run_as`, either a Unix uid@host or a Kubernetes ServiceAccount. A launch on it needs a grant **and** one of two links:
    - the launching principal is linked to that Unix identity (an `identities` row `unix:<host>/<uid>`, proven by registering the runner as that user);
    - that user has explicitly delegated to the principal, and the delegation is listed and revocable.
  - **Group clusters:** either one runner per user, or a service-node runner that submits per user through slurmrestd with per-user JWTs. Never one shared account.
  - **Runner moves:** "Move to another runner" is allowed only between runners with the same `run_as`.
  - **`script:` bindings** stay off unless the runner's local policy enables them (SEC-115).
  - **Test:** principal B with `launcher` on A's environment gets 403 unless A has delegated to B.
- **Related:** R1 SR-014 covers the same gap as a consistency problem. It proposes `execution_identity` (`per_user` or `shared`) and `runners.principal_id`. This finding adds the threat, delegation, the runner-move rule and the `script:` control. Triage them together; SR-014's `shared` option would need the explicit delegation above.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-102 · blocker · `single` mode trusts loopback, but loopback is shared by every user of a login node

- **Where:** auth §1 l.43; api §1 l.18 and §6 l.159; architecture §7.1 l.301 (`--with-runner` is the default in personal mode) and §9 (MVP: Python bundle with `single` auth).
- **Evidence:**
  - "binds to `127.0.0.1` by default. On any other interface it requires a token" (auth §1, l.43).
  - "Requests from `127.0.0.1` / a Unix socket without a token are treated as that user" (api §6, l.159).
  - Personal mode runs "on a laptop or a login node" (api §1, l.18).
  - depictio "admits anonymous requests from any host" ([research](../research/depictio-auth-2026-10-26.md) §10).
- **Problem.**
  - **Attacker and asset:** any other account on the same login node, or a web page open in the owner's browser. They reach the owner's runs, data and Unix account.
  - **Path 1, other users on the node.** Every local user can connect to `127.0.0.1:8080` and become the owner without a token. They launch a run, and the in-process runner executes it as the owner. That is code execution as another HPC user.
  - **Path 2, DNS rebinding and CSRF from the browser.** A malicious page can drive a tokenless localhost API through DNS rebinding, as in the Transmission case ([Project Zero 1447](https://bugs.chromium.org/p/project-zero/issues/detail?id=1447)).
  - **Existing mitigation:** loopback binding, which only keeps out remote hosts.
- **Risk:** L H × I H. It is in MVP scope, on exactly the hosts Spectio targets.
- **Proposal:**
  - **Design (auth §1 owns it):** `single` mode never trusts the network peer. It accepts one of two things:
    - a Unix socket in a `0700` directory, with an `SO_PEERCRED` uid equal to the owner's;
    - a local token. `spectio init` writes it to `~/.config/spectio/local-token` (mode 0600). The CLI reads it, and `spectio local open` turns it into a one-time browser link.
  - **Defaults:**
    - a `Host` header allow-list (`127.0.0.1`, `localhost`, the configured name) against rebinding;
    - CSRF protection on every write, even in `single` mode.
  - **Tests (auth §6):**
    - a second Unix user on the same host gets 401;
    - `Host: evil.example` gets 421 or 403;
    - a cross-site POST without the CSRF token is refused.
- **Related:** R1 SR-031 reports the same core problem as a major and asks for a cross-check with R5. This finding adds the browser path (rebinding, CSRF) and rates it a blocker, because the MVP would otherwise build tokenless loopback trust. SR-031's alternative, limiting the mode to laptops, is a question for Thomas below.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

---

## Majors

### SEC-103 · major · Group credentials reach runners and jobs where any pipeline or scheduler user can read them

- **Where:** api §3 l.68 (secret backend runs on "server, runner"); checking §11.1 l.267; ui-spec §4.8 l.135 (Credentials "scoped to environments"); schedulers §3.1 l.64 (job name `spectio-<run_id>`, `--comment=spectio:<run_id>`); api §12 item 4.
- **Evidence:**
  - Files on object storage "are read through the same storage credentials the run uses **[to be validated]**" (checking l.267).
  - Slurm shows all jobs to all users by default (`PrivateData`), and can store job environments in slurmdbd (`AccountingStoreFlags=job_env`) ([slurm.conf](https://slurm.schedmd.com/slurm.conf.html)).
- **Problem.**
  - **Attacker and asset:** any launcher, through pipeline code, or any cluster user or Slurm operator. The asset is the group's S3, registry and LabID credentials, plus run metadata.
  - **Paths:**
    - the pipeline can read secrets exported as job environment variables, and so can slurmdbd readers if `job_env` is set;
    - job names and comments show run IDs to every user of the cluster.
  - **Existing mitigation:** runners get "never depictio's S3 root secret" (api §13.1, l.296).
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (owner: architecture §3.2, secret backend):**
    - Resolvers and sinks get per-run derived credentials, with the run's TTL. These are STS sessions with a prefix policy, or Vault dynamic secrets.
    - They are delivered as 0600 files in the run directory, not through `sbatch --export`.
    - Head jobs use `--export=NONE` plus a 0600 env file.
    - Job names and comments carry no project or sample names.
    - The site prerequisite is documented: `PrivateData=jobs` is recommended.
  - **Test:** a synthetic pipeline that dumps `env` finds no long-lived secret.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: per-run credentials delivered as 0600 files in the run directory, never through `sbatch --export`; head jobs use `--export=NONE`; derived short-lived credentials where the secret backend supports them; job names and comments carry no project or sample names; `PrivateData=jobs` documented as a recommended site prerequisite (owner architecture §3.2, linked from schedulers) — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-104 · major · No endpoint → action → scope → role matrix, so "every endpoint has a principal and a `can()`" cannot be checked

- **Where:** api §5 (catalogue), §6 (roles, scopes, enforcement); auth §3, §4; admin §5; architecture §2 l.57 (`spectio.api` routes).
- **Evidence:**
  - The scopes are `runs:read`, `runs:launch`, `gates:decide`, `gates:propose`, `artifacts:read` and `admin` (api §6, l.155). `principals:provision` appears only in auth §4 (l.111), and `interventions:resolve` only in synthesis §7bis (l.280).
  - The role table has five rows (api l.144-150). The catalogue has about 100 endpoints. Among them are webhooks, embed tokens, share links, events, search, `workflows:import`, `runs:import-crate`, WES, `/mcp`, `/ingest/events` and `/api/v1/ext/<plugin>/`.
  - No rule says how token rights combine. The project restriction is optional, so a token covers every project unless the creator restricts it (api §5, l.90).
- **Problem.**
  - **Attacker and asset:** any token holder or plugin route, against resources in other projects.
  - **Path:**
    - routes that are not mapped fall back to "authenticated is enough";
    - IDs passed in a body are not checked against the parent project, for example `notify.webhook_ids` in `POST /runs`, `POST /deliveries/{id}:redeliver` and `change_set_id`;
    - plugin routes skip the auth dependency.
  - **Existing mitigation:** one `can()` function and `visible_projects()` joins (api §6, l.166).
  - **Gap:** nothing ties each route to an action.
- **Risk:** L H × I H.
- **Proposal:**
  - **Design (api §6 owns it):** add a matrix with these columns: endpoint, action, required scope, minimum role, resource resolver, and allowed principal kinds (user, service, agent, runner, guest, link).
  - **Effective rights** = the principal's role ∩ the token scopes ∩ the token's project restriction ∩ the gate policy.
  - **Token defaults:** a new PAT or service token is restricted to one project unless "all my projects" is ticked.
  - **Scopes** (in the single registry of SR-024): add `webhooks:manage`, `workflows:import`, `events:read`, `ingest:write`, `principals:provision`, `embed:mint` and `share:create`. Drop `interventions:resolve`.
  - **Every ID referenced in a body** is resolved through `can()`.
  - **Test (tier 2):**
    - enumerate `openapi.json`. A route fails the test if it declares no action and is not on the public allow-list (`/auth/config`, `/public-config`, `/health/live`, `/.well-known/jwks.json`, `/auth/magic-links`, the share-link exchange);
    - a two-tenant fixture calls every route with a foreign ID and expects 404.
- **Related:** R1 SR-024 (one scope registry, owned by auth §3) and SR-012 (`interventions:resolve` → `gates:decide`). The matrix is new; its scope column uses SR-024's registry.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-105 · major · Runner file access is not confined: event paths, globs and symlinks can make the runner read any file of its Unix user

- **Where:** checking §11.1 l.261-280, §7 (`evidence`, `editable`, `watch.files`); api §5 l.95 (artefact content "streamed through the runner"), task logs; ui-spec §4.4; synthesis §6 l.263. The `list_dir` shape is UX-117 and is not repeated; this finding adds confinement.
- **Evidence:**
  - "The runner is the only component that reads files" (checking l.261).
  - In the sequence diagram, the server tells the runner to "evaluate check(s) on path" (l.278), and the path comes from engine events.
  - The data proxy that "forbids paths outside the root" (synthesis §6, l.263) is specified for Zarr serving only.
  - Nextflow publishes as `'symlink'` by default (`publish-dir.mdx:89`, nextflow `114f1fe`).
- **Problem.**
  - **Attacker and asset:** a project viewer, an ingest-token holder or an overlay author. The asset is everything the runner's Unix user can read: `~/.ssh`, other projects' results, the runner credential.
  - **Paths:**
    - globs with `..` or absolute paths in `spectio.yml`;
    - forged `onFilePublish` targets;
    - a symlink in the results dir that points to `~`;
    - an artefact URI edited through an import (SEC-110).
  - **Existing mitigation:** the 50 MB size cap.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (checking §11.1, schedulers §6):** the runner holds per-run roots: the launch dir, work dir and results dir, plus the input and reference roles that the environment declares (ui-spec §4.8). Every read:
    - resolves `realpath`;
    - must fall inside a root;
    - follows a symlink only when its target is inside a root, or is an engine work directory of the same run.
  - The server never sends an absolute path, only (run, root, relative path).
  - Credentials and Spectio's own files are always denied.
  - **Tests:** the glob `../../.ssh/*`, a symlink to `$HOME` and an absolute path in a forged event are all refused.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: runner reads confined to per-run roots (realpath, symlinks followed only inside a root or the run's engine work directory), server sends (run, root, relative path) only; owner checking §11.1, linked from schedulers §6; compatibility with symlink publishDir checked in spike `sec-runner-confinement` — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-106 · major · The runner credential has no route allow-list, and it can forge the check values that drive auto-approval

- **Where:** auth §3 l.103; api §6 l.155, §5 l.92; checking §11.1 l.265; synthesis §5 l.140, §5ter l.238 (auto-approval under threshold). Registration values are UX-124 and are not repeated.
- **Evidence:**
  - "Runner token | until revoked | … Can only act for its environment's runs" (auth §3, l.103).
  - The runner "sends back the values only … as a `check.evaluated` event" (checking l.265).
  - The policy "applies the policy (auto-approval under threshold …)" (synthesis l.238).
- **Problem.**
  - **Attacker and asset:** someone who reads the credential from a home directory on a shared file system: root, admins, or anyone if file modes are wrong.
  - **What they gain:**
    - they pull launch commands and resolved secrets (SEC-103);
    - they post forged `check.evaluated` values or task states for any run of the environment, so that a gate auto-approves;
    - with no route allow-list stated, they may call ordinary API routes.
  - **Existing mitigation:** "bound to one environment".
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (auth §3 owns it):**
    - The secret rotates every 24 h, with overlap, and is refreshed over the channel. "Until revoked" applies to the registration, not to the secret. This also settles the lifetime question of SR-002 and SR-024.
    - It is stored with mode 0600, and in the OS keyring where one exists.
    - It is accepted only on `/runners/{id}/*`.
    - Every event it posts must name a run whose `environment_id` and `assigned_runner_id` match.
    - A gate policy can turn off auto-approval from runner-computed values. Values carry the runner ID and the file hash.
  - Only admins of the environment's owning group may mint registration tokens.
  - **Tests:** a runner token calling `/gates/*/decisions` gets 403; posting for a run of another environment gets 403.
- **Related:** R1 SR-002 and SR-024 already report that auth §3 ("until revoked") and api §6 ("rotating") contradict each other. That sub-point was removed here; this finding keeps the allow-list, the run binding and forged values.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-107 · major · Secrets can reach parameters, logs, the task ledger, audit diffs and RO-Crate exports

- **Where:** architecture §3.2 l.131; admin §3.1 l.139, §3.4 l.163 (sources `engine:<run>`, `runner:<name>`); api §7 (`audit_log.diff`, l.234), §5 (`GET /runs/{id}/ro-crate`, l.99); synthesis §7quinquies l.313 (crate content).
- **Evidence:**
  - "Secret values are references, never plain text in the database" (architecture l.131). This covers plugin settings only.
  - An expanded task row "shows arguments, result, error, traceback and logs" (admin l.139).
  - The crate contains the "params file, samplesheet …" (synthesis l.313).
- **Problem.**
  - **Attacker and asset:**
    - viewers, who see logs and crates;
    - admins of another team, who see the task ledger and the audit log;
    - LabID and WorkflowHub, which receive the crate.
  - The asset is credentials passed as pipeline params or env (API keys, S3 keys), and task arguments such as webhook URLs with tokens or backup passphrases. Nextflow does not mask `params` (SEC-108).
  - **Existing mitigation:** plugin secrets are references, and `config show` masks them.
- **Risk:** L H × I M.
- **Proposal:**
  - **Design (admin §3.4 and api §7):** one redaction function, used by event ingest, `log_records`, task arguments and results, audit diffs, crate export and telemetry. It covers:
    - known secret values (resolved refs and live tokens);
    - the `spk_` prefix;
    - key patterns aligned with Nextflow's (`SECRET_KEYS` / `StringUtils.isSensitiveName`, see Sources);
    - schema fields flagged `x-spectio-secret` or `format: password`.
  - Task arguments use a `SecretRef` type. Tracebacks are stored without local variables.
  - Register the `spk_` prefix with GitHub secret scanning **[to be validated: partner programme terms]**.
  - **Test:** seed a canary secret in params, env, a webhook URL and a backup passphrase. Then grep every sink, the crate and the DB dump for it.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: one redaction function owned by admin §3.4, applied to event ingest, logs, task arguments and results, audit diffs, crate export and telemetry; `SecretRef` task arguments; GitHub secret-scanning registration left to Thomas — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-108 · major · Ingest credentials for observed runs are undefined, and tokens may land on command lines, in configs and in captured run metadata

- **Where:** ui-spec §6 l.196 and l.208; auth §3 l.104; api §2D l.50; synthesis §9 l.377.
- **Evidence:**
  - Nextflow gets "a `spectio` config profile/env set once by `spectio login`" (ui-spec l.196).
  - "Parameters, command line, config and software versions captured from the run are kept" (ui-spec l.208).
  - The run token is "Issued to a provisioned run (§4) or an engine plugin" (auth l.104).
  - The MVP has "one ingestion token" (synthesis l.377).
- **Problem.**
  - **Attacker and asset:** another login-node user or a project viewer. The asset is a user token with broad scopes.
  - **Paths:**
    - `--logger-spectio-token=…`, or `-c` with an inline token, appears in `/proc/<pid>/cmdline`. Every local user can read it unless `/proc` is mounted with `hidepid` ([proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)).
    - The token is captured in "command line" and config text, which project viewers see.
    - Nextflow masks config keys such as `TOKEN` or `SECRET` (`ConfigCmdAdapter.groovy:650-651` → `SecretHelper.groovy:35`, nextflow `114f1fe`). But when `nf-tower` also runs, it sends `params` unmasked to Seqera (`TowerObserver.groovy:383`).
    - A token that can create observed runs in any project lets its holder fill other projects with fake runs.
  - **Existing mitigation:** run tokens for runs that Spectio launches.
- **Risk:** L H × I M.
- **Proposal:**
  - **Design (auth §3, new row `ingest token`):**
    - scope `ingest:write`, one project;
    - it can create observed runs and post their events, nothing else;
    - 30 days, rotatable;
    - `spectio login` writes it to a 0600 file.
  - `nf-spectio` and the Snakemake logger read the token from `SPECTIO_TOKEN` or that file, never from flags. If `nf-spectio` has a config key for it, the key matches Nextflow's mask pattern (`spectio.token`).
  - Server-side redaction runs on captured command lines and config (SEC-107).
  - Event paths are checked as in SEC-105.
  - **Tests:** `ps` shows no token; the captured config shows `[secret]`.
- **Related:** R1 SR-001 (ingest contract undefined) and SR-024 (no ingest scope). This finding defines the credential.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-109 · major · Co-hosting on one origin merges depictio's and Spectio's trust; the reports' "separate origin" is undefined

- **Where:** api §13.4 l.329; research `depictio-harmonization.md` l.99; synthesis §6 l.260; checking §3 l.77; architecture §7.2, §8 l.430. Path collisions are DEP-T-013 and SeaweedFS identities are DEP-T-014; neither is repeated.
- **Evidence:**
  - "`/depictio/…` and `/spectio/…` on one domain, shared SSO session" (api l.329).
  - "share cookies/SSO" (research l.99).
  - HTML reports run "ideally from a **separate origin**" (synthesis l.260), or "from a separate origin" (checking l.77).
  - "Spectio can use [depictio's Redis] … on a separate database index" (architecture l.430).
- **Problem.**
  - **Attacker and asset:** an XSS in either application. It reaches the other application's session and the gates.
  - **Path: one origin.** Script on the same origin can call Spectio, because the browser sends the HttpOnly cookie, and can read the CSRF token from the DOM. It can also read depictio's localStorage bearer (auth §3, l.98). Cookie paths are not an isolation boundary ([RFC 6265 §8.5](https://www.rfc-editor.org/rfc/rfc6265#section-8.5)).
  - **Path: reports.** No second origin is defined for the bundle (`127.0.0.1:8080`) or for one-domain co-hosting, so the report sandbox falls back to the app origin.
  - **Path: shared Redis.** A Redis database index is not an authorization boundary unless ACLs restrict `SELECT` and keys ([Redis ACL](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/); exact semantics **[to be validated]**). A compromised depictio could then inject Spectio pub/sub messages, or Celery tasks such as `backup.restore`.
  - **Path: client IPs.** Rate limits depend on which proxy headers are trusted ([uvicorn `--forwarded-allow-ips`](https://www.uvicorn.org/settings/)). depictio trusts `X-Real-IP` (research `depictio-auth` §8).
  - **Existing mitigation:** HttpOnly cookie, sandboxed iframe.
- **Risk:** L M × I H.
- **Proposal:**
  - **Default (api §13.4 owns it):** separate hosts (`spectio.<site>` and `depictio.<site>`), with SSO through the IdP rather than a shared cookie.
  - **Reports:** a mandatory `usercontent` origin for reports and level-3 viewers: a second host, or a second port in the bundle.
  - **If path co-hosting is kept:** document that it merges the two trust domains, and require `Content-Security-Policy` plus Trusted Types in both apps.
  - **Redis:** never shared without one ACL user per application.
  - **Proxies:** trusted proxies are configured explicitly. With no proxy configured, the peer address is used.
  - **Tests:** the report iframe's origin differs from the app origin; the rate limiter ignores a spoofed `X-Forwarded-For` from an untrusted peer.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-110 · major · RO-Crate, project and workflow imports are unvalidated paths for code, paths and forged history

- **Where:** api §5 l.91, l.99; synthesis §7quinquies l.316 ("Reproduce from a crate"); admin §4.3 l.290 (project export and import, `--overwrite`, owner remap); cli §2 (`migrate project … --overwrite`).
- **Evidence:**
  - `POST /workflows:import` takes git, nf-core, a Snakemake catalog or an RO-Crate (api l.91).
  - "importing a run crate pre-fills a launch" (synthesis l.316).
  - "upsert with `--overwrite`, owner remap" (admin l.290).
  - nf-core/rnaseq loads config code from `params.custom_config_base` (`nextflow.config:154,331`, `95dbcd9`).
- **Problem.**
  - **Attacker and asset:** the author of a crate or an export, from WorkflowHub, email or another instance. The assets are the launcher's account, other projects' rows and the audit history.
  - **Crate paths:**
    - zip slip and zip bombs ([Snyk](https://security.snyk.io/research/zip-slip-vulnerability));
    - fetching a remote JSON-LD `@context`, which is SSRF if the library loads contexts by default ([JSON-LD 1.1 API](https://www.w3.org/TR/json-ld11-api/#remote-document-and-context-retrieval); library default **[to be validated]**);
    - `file://` or `ext::` git URLs ([git `protocol.allow`](https://git-scm.com/docs/git-config#Documentation/git-config.txt-protocolallow));
    - prefilled params that load code (`custom_config_base`, `config_profile_url`), hidden under "Show hidden".
  - **Project import paths:**
    - IDs that collide with existing rows, combined with `--overwrite`, overwrite another project's rows;
    - decisions attributed to arbitrary principals;
    - manifests with `script:` or `agents: approve`;
    - webhooks.
  - **Existing mitigation:** `--dry-run`, an S3 allow-list.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (api §5 and admin §4.3):**
    - Imports re-mint every ID, and `--overwrite` matches only inside the target project.
    - Imported decisions and audit entries become `imported_from` provenance, never live principals.
    - Webhooks, plugin instances, service accounts and tokens are never imported.
    - Manifests go through the policy review of SEC-114.
    - Crates are extracted with path and size limits, and JSON-LD is processed with remote loading off.
    - Git URLs must be https or ssh.
    - A prefilled launch shows every non-default param and flags the params that load code.
  - **Tests:** a zip-slip crate, an `ext::` URL and an import with a foreign run ID are all refused.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: imports treated as untrusted input: IDs re-minted, `--overwrite` only inside the target project, imported decisions as `imported_from` provenance, no webhooks, plugin instances, service accounts or tokens imported, imported manifests inert, safe crate extraction with JSON-LD remote loading off, git URLs https or ssh only, code-loading params flagged (api §5, admin §4.3) — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-111 · major · Agent decisions on gates are not bounded or reversible, and they record a self-reported identity

- **Where:** synthesis §5bis l.170, l.193; ui-spec §4.5 l.100, §4.9 l.148-151; api §5 (`gates:bulk-decide` l.96, `/mcp` l.103); checking §3 l.77. Agents on clinical data are UX-129 and are not repeated.
- **Evidence:**
  - "a human can revert them as long as the next stage has not started" (synthesis l.193).
  - A decision records "**model and version** for an agent" (synthesis l.170).
  - The bulk action can "approve the selected gates whose checks all pass" (ui-spec l.100).
  - The MVP default AI path is "**Your own agent** (MVP default): a coding assistant …" (ui-spec l.148).
  - Agents get "extracted text, never the raw HTML" (checking l.77).
- **Problem.**
  - **Attacker and asset:** a prompt-injected or compromised agent. The assets are gate outcomes and the user's machine.
  - **Paths:**
    - an agent approval continues the run at once, so the revert window is close to zero;
    - bulk decisions across projects;
    - the model and version are claims made by the client;
    - sample names and extracted text from pipeline outputs reach a coding assistant that has shell access;
    - nothing requires MCP tokens to be audience-bound ([MCP authorization, 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization); the 2026-07-28 text is **[to be validated]**).
  - **Existing mitigation:** scoped agent tokens, "propose" by default, costly actions reserved to humans.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (owner: checking §5 decisions, plus api §6):**
    - An agent `approve` waits for a configurable hold before the run continues (default 15 min), with a notification. A human can cancel it during the hold.
    - Agents may not apply change sets that edit params beyond the schema, edit files, or exclude more than N % of items (default 10 %). Larger changes become proposals.
    - Rate limits per agent.
    - `bulk-decide` checks `can()` and the policy for each gate, and is refused to agents.
    - `model` is stored as `claimed_model`.
    - MCP results wrap untrusted strings in a marked data envelope.
    - MCP tokens carry `aud=<instance>/mcp`.
    - No MCP tool mints tokens or edits policy.
  - **Tests:** an agent approval cancelled inside the hold does not continue the run; an agent excluding 50 % of items produces a proposal only.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-112 · major · SSE, the event log and search have no stated tenancy filter, revocation behaviour or rule for events with no project

- **Where:** api §5 l.97, l.100; api §8 l.250 (`spectio.runner.offline`, `.online`); schedulers §8 l.241 (`spectio.environment.capacity_low`); synthesis §7 l.269; admin §3.4 (live log tail).
- **Evidence:**
  - "`GET /events/stream` (SSE, resumable with `Last-Event-ID`)" (api l.97).
  - "one multiplexed stream per tab" (synthesis l.269).
  - "`GET /search?q=` (runs, workflows, tasks, samples by external ref)" (api l.100).
  - Runner and environment events are about environments, not projects, so they have no project to filter on.
- **Problem.**
  - **Attacker and asset:** a principal whose grant was revoked, or a member of another group. The assets are events, sample names and environment capacity.
  - **Paths:**
    - a stream authorised when it connects keeps delivering after the grant, the token or the session is revoked;
    - events with no project are either sent to everyone or filtered ad hoc;
    - search counts, facets and autocomplete reveal that other projects' runs or samples exist;
    - the browser's `EventSource` cannot send headers ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html#the-eventsource-interface)), so embeds with bearer tokens would put them in query strings and proxy logs.
  - **Existing mitigation:** `visible_projects()` on list queries.
- **Risk:** L M × I M.
- **Proposal:**
  - **Design (api §8 owns it):**
    - Every event carries `project_id` or `environment_id`. Environment events go to principals that hold an environment grant.
    - Fan-out filters each event against an authorization cache. A "grants changed" pub/sub message invalidates the cache, and streams end within 30 s of a revocation.
    - Search is a union of per-type list queries joined on `visible_projects`, never an unfiltered index. Counts are computed after the filter.
    - Embeds stream with `fetch()` and a header, or with a single-use stream ticket valid for 60 s.
  - **Tests:** two-tenant search and SSE fixtures; revoking a grant during a stream closes it; no `token=` appears in access logs.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: every event carries `project_id` or `environment_id`; SSE fan-out filtered per event against an authorization cache invalidated on grant changes; search built from per-type list queries joined on `visible_projects`; embeds stream with `fetch()` and a header or a single-use 60 s ticket (owner api §8) — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-113 · major · Identities are linked by email across IdPs, and group sync is not namespaced or kept away from protected groups

- **Where:** auth §2 l.68-70; api §13.1 l.293, §13.2 l.302; admin §2.2 l.100 (protected `admin` and `users` groups); research `depictio-auth-2026-10-26.md`: §1 l.23 (`registration_disabled` defaults to false), §4 l.114 ("no email sending anywhere"), §6 l.172 ("a sync failure never blocks the login").
- **Evidence:**
  - "matched by email, linked by `depictio:user/<id>`" (api l.302).
  - "same email: one login for both" (api l.293).
  - OIDC providers are "Google, EMBL SSO, LS Login, Keycloak", with "group claim sync like SAML" (auth l.68).
  - SAML group sync maps "`memberOf` → `sso_managed`" (auth l.69).
- **Problem.**
  - **Attacker and asset:** someone who can get any trusted issuer to assert a victim's email. That could be a depictio self-registration, which cannot be verified because depictio sends no email, or a weaker IdP. The asset is the victim's Spectio principal.
  - **Takeover:** on first login, the identity is linked to the existing principal by email.
  - **Group escalation:** an IdP group named `admin`, or named like another lab's group, joins that Spectio group. Only `can()` stands in the way.
  - **Mix-up:** with several OIDC providers and no issuer check, the attacks in [RFC 9207](https://www.rfc-editor.org/rfc/rfc9207) and [RFC 9700 §4.4](https://www.rfc-editor.org/rfc/rfc9700#section-4.4) apply.
  - **Stale admin rights:** if a failed group sync does not block login, as in depictio, removals from admin groups are skipped and the rights stay.
  - **Existing mitigation:** `identities` unique on (provider, subject) (api §7, l.215), PKCE, nonce.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (auth §2 owns it):**
    - Identities are linked only by (provider, subject).
    - Email-based linking happens only for providers flagged `trusted_email` that send `email_verified=true`, and always behind a confirmation in an existing session. depictio is never `trusted_email`.
    - Synced groups are namespaced per provider (`oidc:embl/rnaseq-core`) and mapped to Spectio groups through an allow-list that admins maintain.
    - `admin` and `users` are never synced.
    - Check `iss` (RFC 9207), or use one redirect URI per provider.
    - A failed sync denies elevated groups for that session.
  - **Tests:** a Keycloak group named `admin` gives no admin rights; a second IdP asserting an existing email is not linked automatically.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-114 · major · `spectio.yml` from a workflow repository can widen gate policy, add code and add editable paths with each new version

- **Where:** ui-spec §4.9 l.151, §5.1 l.187; checking §7 l.151-192, §11.1 l.269; api §6 l.149, l.152.
- **Evidence:**
  - The manifest's `decide` block holds `humans: [group:rnaseq-core]` and `agents: propose` (checking l.181-182).
  - Agents "approve gates only where `spectio.yml` allows" (ui-spec l.151).
  - "A gate can be stricter than the defaults, never looser" (ui-spec l.151).
  - "An overlay can add watches, never remove an author's `block` check" (checking l.269).
  - `script:<command>` (checking l.192) and `editable` (l.183).
- **Problem.**
  - **Attacker and asset:** a third-party pipeline author or a project editor. Just by publishing a new release, they can:
    - loosen the policy (`agents: approve`, lower thresholds, wider `humans`);
    - add `script:` code (SEC-101);
    - add `editable` paths outside the results (SEC-105).
  - **Existing mitigation:** instance defaults cap what agents may do.
  - **Gap:** there is no change review, and no merge rule for `decide`.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (checking §7 owns it):**
    - Policy keys from a repository manifest (`decide.*`, `script:` bindings, `editable`) stay **inert** until a project editor approves them for that workflow version. Each version change shows a diff.
    - Merge rule for policy: the strictest of instance, project, overlay and author wins.
    - Names in `humans` and `agents` resolve inside the project only.
  - **Test:** a new version that adds `agents: approve` leaves the effective policy unchanged until it is approved.
- **Related:** R1 SR-004 (`spectio.yml` has four shapes and no schema owner). The merge rule belongs in the schema that SR-004 asks for.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-115 · major · A server compromise is code execution on every runner's Unix account; runners hold no local policy

- **Where:** synthesis §7quater l.339; architecture §3.6 (`Engine.plan` → "command, env, generated config"); schedulers §6.
- **Evidence:**
  - The runner "receives orders (launch, cancel, resume, read a log, browse a directory)" (synthesis l.339) and runs the plan as the user.
- **Problem.**
  - **Attacker and asset:** whoever controls the server, through RCE, a stolen admin token or a malicious plugin (SEC-124). The asset is every HPC and Kubernetes account that runs a runner.
  - **Existing mitigation:** connections are outbound only. That protects the runner from inbound attacks, but not from the server it trusts.
- **Risk:** L L-M × I H. The blast radius is the whole user base.
- **Proposal:**
  - **Design (schedulers §6, new subsection):** a runner-side `runner.toml`, owned by the Unix user. The runner enforces it whatever the server says. It lists:
    - allowed workflow sources (git hosts and organisations, local paths);
    - allowed launch, work and results roots;
    - whether `script:` bindings are allowed (default off);
    - maximum resources;
    - allowed launchers.
  - The runner verifies the server's TLS identity, with optional pinning.
  - **Test:** a server command outside `runner.toml` is refused and reported in Health.
- **Related:** the reviewer also noted that the channel transport differs between api §5 (WebSocket) and architecture §7.6 (long poll or SSE). That is R1 SR-002 and was removed here.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-116 · major · Event bridges hand authentication to broker ACLs, share one principal across all devices, and send every project to one topic

- **Where:** architecture §7.6 l.413-421; admin §2.3 l.106 (event bridges as service accounts); schedulers §0 item 3 (l.25), §3.3 l.92 (`jobcomp/kafka`).
- **Evidence:**
  - "Inbound, a robot can publish a gate signal or a launch request. The bridge maps it to the same API call with the bridge instance's service principal" (architecture l.416).
  - "Outbound topics follow `spectio/<project>/<type>`" (l.415).
  - Kafka has "One topic per event family" (l.418).
- **Problem.**
  - **Attacker and asset:** anyone with publish rights on the broker, a device on the lab network, or a Kafka consumer. The assets are launches, gate signals and events from other tenants.
  - **Inbound:** every publisher acts as the same principal, so there is no attribution per device and no protection against replays.
  - **Outbound:** project data reaches every subscriber unless the broker has per-topic ACLs ([Mosquitto ACL](https://mosquitto.org/man/mosquitto-conf-5.html), [Kafka authorization](https://kafka.apache.org/documentation/#security_authz)). Kafka topics per event family mix all projects.
  - **Slurm records:** `jobcomp/kafka` records cover every user of the cluster.
  - **Existing mitigation:** "policy and the audit log apply unchanged"; CloudEvents IDs for dedupe.
- **Risk:** L M × I M-H.
- **Proposal:**
  - **Design (architecture §7.6 owns it):**
    - By default, inbound bridges accept signals only. Launches need an explicit flag.
    - Each device gets its own credential, mapped to its own service principal: a broker client ID or certificate, or a signed CloudEvent.
    - Replay protection: dedupe on event ID plus a ±5 min time window.
    - Outbound is opt-in per project, with a type filter and a minimal payload (IDs and states, no sample names or params).
    - Kafka topics are per project, or use a documented ACL prefix.
    - Spectio keeps only the `jobcomp` records of jobs whose native ID it submitted.
  - **Tests:** an MQTT launch request is refused by default; a replayed signal does nothing; another user's `jobcomp` record is dropped.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-117 · major · Share links contradict the guest, grant and gate-policy rules, and work as forwardable bearer invitations

- **Where:** auth §1 l.45, §2 l.67, §2.1 l.81-85, §5 l.130, §6 l.146; api §6 l.150, l.152.
- **Evidence:**
  - Links are created "by a project owner or editor" (auth l.67), while only owners "Manage grants" (api l.150).
  - "**Guests are read-only:** no launches, no gate decisions" (auth l.45). Yet the share-link recipient becomes "a **guest principal bound to that link**" with role `reviewer` (l.67), and the test says "open a gate as an external reviewer, decide" (l.146).
  - §2.1 says "**Single use,** burned atomically" (l.84), yet a share link has `max_uses`. `email?` is optional, yet the flow relies on a "Continue as `<email>`" screen (l.81).
  - The recipient "signs in to keep the access" (l.67).
  - The expiry may be up to 30 days (l.85), on a whole `project`.
- **Problem.**
  - **Attacker and asset:** whoever receives a forwarded link. They gain gate decisions or project data, which may be clinical (UX-129).
  - **Path:** an editor mints a `project`/`reviewer` link with no email and no `max_uses`, and it gets forwarded. Any holder can then:
    - decide gates as a guest;
    - turn the link into a permanent grant by signing in.
  - It is unclear whether a guest's decision satisfies `humans: [group:rnaseq-core]`. Either the policy is bypassed or the advertised flow fails.
  - Revoking a link does not say whether sessions already opened from it end.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (auth §2 owns it):**
    - Link guests are a principal kind of their own (`link`), distinct from public guests.
    - Only owners mint `reviewer` links. A `reviewer` link requires `email` and `resource=gate`, and defaults to `max_uses: 1`. At redemption, the address is verified with a one-time code sent to it.
    - `project` links are `viewer` only.
    - Gate policies name link principals explicitly (`humans: [link:*]`, or a specific email). They are not matched by default.
    - "Sign in to keep access" creates a pending grant that an owner approves.
    - Sessions store `link_id`, and revoking the link ends them.
  - **Tests:** deciding through a link on a gate whose policy names a group gets 403; after a revoke, the live session gets 401; a link forwarded to a second browser asks for the verification code.
- **Related:** R1 SR-019 (guests are outside the `principals.kind` enum). The `link` kind would be added to that enum.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-118 · major · Outbound HTTP from webhooks, plugins, WES and imports has no SSRF policy

- **Where:** api §5 (webhooks l.98, `workflows:import` l.91, WES l.103), §2B l.44; architecture §3.2 l.108 (`webhook_url`), §3.3 l.142 (instances scoped to a group or project), §3.4 l.153 (`ctx.http`).
- **Evidence:**
  - Project owners manage webhooks (api l.150).
  - "Notifier, sink, resolver, check, viewer and AI provider can also be scoped to a group or a project" (architecture l.142).
  - "`http`: a shared `httpx.AsyncClient` with the instance proxy, CA bundle, timeouts and retries" (architecture l.153).
  - `POST /workflows:import` takes git URLs and crates. `GET /webhooks/{id}/deliveries` shows delivery results.
- **Problem.**
  - **Attacker and asset:** a project owner or group admin who is not an instance admin. The targets are the server's internal network: cloud metadata, the Postgres side services, depictio's internal API, SeaweedFS.
  - **Path:** point a webhook, a Mattermost URL, a LabID endpoint or a WES `workflow_url` at an internal address, then read the response through delivery logs or errors. DNS rebinding gets past a check made only when the URL is saved.
  - **Existing mitigation:** none.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (architecture §3.4, which owns `ctx.http`):** one egress policy for every server-side outbound call:
    - deny loopback, link-local, RFC 1918 and ULA addresses unless an admin allow-lists them;
    - resolve the name first, then connect to that pinned IP;
    - no redirects that leave the policy;
    - store response bodies truncated, and show them to admins only.
  - The WES facade accepts registered workflow versions only.
  - **Tests:** a webhook to `169.254.169.254` is refused; a hostname that rebinds to `127.0.0.1` is refused.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-119 · major · Backups put signing and secret-store keys in an archive whose encryption is optional, and restore accepts uploaded archives

- **Where:** admin §0 l.29, §4.3 l.242, l.268, l.271, §5 l.339 (`/backups/upload`, `/backups/{id}/download`); cli §2 l.98 (`spectio backup create --include db,files,keys --destination seaweedfs`).
- **Evidence:**
  - "`keys/`: token signing keys and the secret-store key" (admin l.242).
  - "optional encryption" (l.29).
  - "the manifest signature" (l.268), with no key named.
  - "a backup from a destination, or an uploaded file" (l.271).
  - The spec's own CLI example ships keys to SeaweedFS without `--encrypt` (cli l.98).
- **Problem.**
  - **Attacker and asset:** a reader of the backup bucket (shared SeaweedFS, DEP-T-014) or of a downloaded archive. They get the keys, so they can mint any token and decrypt every stored secret.
  - **Injection on restore:** an uploaded archive can carry the attacker's `keys/` and principals. Once it is restored, the attacker's signing key is trusted.
  - **Existing mitigation:** checksums, dry run, typed confirmation, admins only.
- **Risk:** L M × I H.
- **Proposal:**
  - **Defaults (admin §4.3 owns them):**
    - `keys/` and sealed secrets are always encrypted to an age recipient whose private key is kept off the instance.
    - A backup to a remote destination with no recipient is refused.
    - The manifest is signed with an instance backup key whose public half is pinned in config.
    - Restoring an archive signed by another instance requires explicitly trusting that instance's public key.
    - `keys/` is restored only with an explicit flag and a second confirmation.
    - Download and restore require a fresh re-authentication (SEC-127).
  - **Tests:** an unsigned upload is refused; a backup to S3 without a recipient is refused; the archive holds no plaintext key bytes.
- **Related:** R1 SR-030 (restore and token handling) and SR-050 (backup contract differs between cli and admin).
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-120 · major · depictio JWT trust accepts tokens Spectio cannot audience-check or revoke, and maps depictio admin to Spectio admin

- **Where:** auth §2 l.70, §6 l.150; api §13.1 l.293-297; research `depictio-auth-2026-10-26.md` §3 l.83-92. Key distribution is DEP-T-015 and is not repeated.
- **Evidence:**
  - Spectio "verify depictio's RS256 JWT with its public key, or call `/depictio/api/v1/auth/me`" (auth l.70).
  - The test row asks for "signature and audience checks" (auth l.150).
  - depictio's claims are "the `TokenData` fields plus `exp`" (`name`, `token_lifetime`, `token_type`, `sub`), with no `aud`. Revocation works only because "The token must then also exist in `TokenBeanie`" (research l.84-85).
  - depictio tokens can be short-lived, long-lived or "permanent" (a 1-year JWT, research l.92).
  - "`User.is_admin` bypasses permissions | same flag and meaning" (api l.294).
- **Problem.**
  - **Attacker and asset:** the holder of any depictio token, such as a leaked CLI token or the provisioning token `pipeline_provision`. The asset is access to Spectio, including admin access.
  - **Paths:**
    - offline signature checks accept revoked depictio tokens for up to a year;
    - depictio tokens have no audience claim, so the planned audience test cannot pass;
    - depictio admins become Spectio admins.
  - **Existing mitigation:** signature checks, the `depictio:user/<id>` link.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (auth §2 and api §13.1):**
    - depictio tokens are accepted only at a dedicated exchange endpoint, and verified online through `/auth/me`, which honours revocation.
    - Only `token_lifetime=short-lived` is accepted.
    - The exchange mints a Spectio session with Spectio's own lifetimes and `iss`.
    - Bearer depictio tokens are never accepted on other routes.
    - `is_admin` is not mirrored unless the instance setting `depictio.trust_admin=true` is set (default false).
  - Drop "audience" from the auth §6 test row, or ask depictio to add `aud` (ecosystem-reuse §3, item 5).
  - **Tests:** a revoked depictio token gets 401; a long-lived token is refused at the exchange; a depictio admin is not a Spectio admin by default.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-121 · major · `instance` visibility means "everyone", so on a public or demo instance internal projects are readable by anonymous guests

- **Where:** api §6 l.139, §13.2 l.306; auth §1 l.45-50.
- **Evidence:**
  - "Visibility … `instance` (everyone can read)" (api l.139).
  - "`instance` ↔ `is_public`" (api l.306).
  - "In `public` and `demo`, signed-in users keep their roles and guests stay read-only" (auth l.50).
- **Problem.**
  - **Attacker and asset:** an anonymous guest on a `public` instance. The asset is projects that members marked `instance` meaning "my colleagues", whose data may be unpublished or clinical.
  - **Existing mitigation:** guests are read-only, which does not stop them reading.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (api §6 owns it):** split `instance` (signed-in principals that are not guests) from `public` (also guests and anonymous visitors).
  - Map depictio's `is_public` to `public`.
  - On `public` and `demo` instances, `public` projects need the admin setting `allow_public_projects`.
  - **Test:** when a guest lists projects, the `instance` projects are absent.
- **Related:** R1 SR-029 proposes the opposite move: two values only (`private`, `instance`), as depictio does. The two proposals must be reconciled; see the questions for Thomas.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-122 · major · Gate decisions through embed tokens are attributed to the host's service account, which bypasses human policies

- **Where:** api §2C l.47, §9 l.256-258, §13.6 rule 3 (l.354); auth §3 l.105.
- **Evidence:**
  - The host "exchanges its service token for a short-lived **embed token**" (api l.47).
  - `actions: ["read", "decide"]`, `ttl: 900` (api l.257).
  - The embed token is a "JWT bound to one resource and origin" (auth l.105).
  - The elements "emit `postMessage` events" (api l.47).
  - "Selections are kept in step both ways by messages between the two frames" (api l.354).
- **Problem.**
  - **Attacker and asset:** a host application such as LabID, or an XSS on the host page. The assets are gate decisions and their audit trail.
  - **Paths:**
    - every LabID user's decision is recorded under the service principal, so `humans: [group:…]` is either impossible to satisfy or satisfied by a robot;
    - the "origin" binding cannot be enforced against clients that are not browsers;
    - `postMessage` without a fixed `targetOrigin` and a check of the sender's origin leaks events or accepts forged selections.
  - **Existing mitigation:** `frame-ancestors` and a CORS allow-list, TTL ≤ 1 h.
- **Risk:** L M × I M-H.
- **Proposal:**
  - **Design (api §9 owns it):**
    - `decide` embed tokens require an `act` claim that names the end user (an email or `depictio:user/<id>`). The host's service account signs it, and Spectio resolves it to a Spectio principal. Policy is evaluated against that principal.
    - Unknown users are refused.
    - The TTL for `decide` is 5 min.
    - `postMessage` uses an explicit `targetOrigin` from the allow-list, and checks `event.origin` on receipt.
  - **Tests:** a `decide` token without `act` gets 403; a message from an origin not on the allow-list is ignored.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-123 · major · Provisioning returns a full sign-in link for the provisioned email to the calling service account

- **Where:** auth §4 l.111-117.
- **Evidence:**
  - Provisioning "**never** returns credentials for an existing admin or for any principal with more rights than the grant" (l.114).
  - "At the end of the run, Spectio sends a sign-in magic link to the user, by email and in the run's `--result-json`" (l.117).
- **Problem.**
  - **Attacker and asset:** a compromised LIMS or CI service account that holds `principals:provision`. The asset is the account of an existing user with wider rights, such as a P.I. with access to many projects.
  - **Path:** provision `pi@embl.de` on a project the service account may share, run anything, and read the sign-in magic link from `--result-json`. That link opens a full session for the user, with more rights than the grant, which l.114 forbids.
  - **Pre-account hijacking:** provisioning an address that has no account yet creates a principal the attacker can drive. When the real person later signs in with SSO, it is merged by email ([Sudhodanan & Paverd, USENIX Security 2022](https://www.usenix.org/conference/usenixsecurity22/presentation/sudhodanan)).
  - **Existing mitigation:** no admin escalation, idempotency, audit.
- **Risk:** L M × I H.
- **Proposal:**
  - **Design (auth §4):** `--result-json` carries only a **scoped share link**: the run or gate as resource, the granted role, and the provisioned email bound to it. A full sign-in link is sent by email only.
  - Provisioned principals stay `unverified` until that email link is used.
  - Linking an SSO identity to an `unverified` principal ends all of its sessions and asks for confirmation (SEC-113).
  - **Tests:** provisioning an existing user with wider grants puts only a scoped link in the result JSON; the first SSO login on a provisioned principal revokes earlier sessions.
- **Found by:** security-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### SEC-124 · major · Plugins run in-process with full trust; "plugins never touch the database" is a convention, not a boundary

- **Where:** architecture §0, §2 l.57, §3.4 l.153-159, §7.4 l.357, §10 risk 2 (l.444).
- **Evidence:**
  - "The rule 'no database session for plugins' is what keeps multi-user safe" (l.159).
  - The plugin's `api` client acts "as the plugin instance's service principal, limited to the scopes the plugin declared" (l.154).
  - `spectio.api`: "inbound routes under `/api/v1/ext/<plugin>/`" (l.57).
  - `SPECTIO_EXTRA_PLUGINS` is "installed at start" (l.357).
  - Risk 2, "A plugin bypasses tenancy", is answered with "No database access, a scoped API client" (l.444).
- **Problem.**
  - **Attacker and asset:** a malicious or compromised plugin package (a supply-chain attack). The assets are the database, the keys and all tenants.
  - CPython has no in-process sandbox ([PEP 578](https://peps.python.org/pep-0578/#why-not-a-sandbox)). A plugin can read `DATABASE_URL` or the secret-store key, or patch `can()`.
  - **Confused deputy:** an instance-wide sink principal reads any project when a project event triggers it.
  - Extension routes may skip authentication.
  - **Existing mitigation:** an allow-list and a deny-list, safe mode, no installs from the browser.
- **Risk:** L L-M × I H.
- **Proposal:**
  - **Design (architecture §3 owns it):**
    - State plainly that installed server plugins are trusted like admins, and that the scoped `ctx.api` is about correctness, not security. Reword risk 2 to match.
    - In production, `SPECTIO_EXTRA_PLUGINS` is refused unless `allow_runtime_install=true`.
    - `plugins.allow` pins the distribution, version and wheel hash.
    - Calls triggered by an event run as the triggering principal ∩ the plugin's scopes.
    - Extension routes are mounted behind the same auth dependency. Unauthenticated callbacks must be declared, are HMAC-verified, and are listed in Settings → Plugins.
  - **Tests:** an extension route called without a token gets 401 unless it is declared; a sink triggered by project A cannot read project B.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-125 · major · Idempotency keys are not scoped to the caller: a replayed key returns another tenant's run

- **Where:** api §4 l.77, §5 l.109 and l.130, §7 l.222 (`runs.idempotency_key`).
- **Evidence:**
  - "Retrying with the same `Idempotency-Key` returns the same run" (l.130).
  - The example key is `labid-order-8812` (l.109), which is predictable.
  - No uniqueness scope is stated.
- **Problem.**
  - **Attacker and asset:** any principal that can launch. If keys are global, sending a guessed key such as `labid-order-8813` returns someone else's run. That discloses its ID, project and parameters, and later calls may treat the run as the caller's.
  - **Existing mitigation:** none stated.
- **Risk:** L M × I M.
- **Proposal:**
  - **Design (api §4):** keys are unique per (principal, or the owning group of a service account; method; route).
  - Replaying a key with a different body gets 422 (the CLI already has exit code 5 for this).
  - A replay must still pass `can(read)` on the stored result.
  - **Test:** tenant B reuses tenant A's key and gets a new run, or 422, never A's run.
- **Found by:** security-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

---

## Minors

Minor findings were checked for their quotes but less deeply than blockers and majors.

### SEC-126 · minor · Browser hardening defaults are not written down

- **Where:** auth §3; telemetry §4.2 l.133-144; admin §4.1 l.201 (`logo_url`); ui-spec §4.7 l.127 (README).
- **Evidence:**
  - Only a CSP driven by analytics, and "never needs `unsafe-inline`", are specified (telemetry l.133-134).
  - Workflow READMEs from git are rendered (ui-spec l.127).
  - Trackers are kept off sign-in, share-link and embed pages (telemetry l.144), but not off admin or review pages.
- **Problem:**
  - Stored XSS through README Markdown, or through workflow, sample or process names.
  - A third-party analytics script on admin pages could mint tokens or download backups.
  - Session fixation across "share link → sign in".
- **Risk:** L M × I M.
- **Proposal:**
  - **Defaults (auth §3):**
    - a baseline CSP: `default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`, except on embed routes;
    - Trusted Types;
    - Markdown sanitised, with no raw HTML;
    - a `__Host-` cookie on separate hosts (SEC-109);
    - the session ID rotated on login and on every privilege change;
    - no analytics on `/admin/*` or on gate decision routes.
  - **Test:** a README containing `<img onerror>` does not execute.
- **Found by:** security-reviewer
- **Status:** inbox, assumed: baseline browser hardening written in auth §3 (CSP baseline except embed routes, Trusted Types, sanitised Markdown with no raw HTML, session ID rotated on login and privilege change) and no analytics on `/admin/*` or gate decision routes (telemetry §4.2); the `__Host-` cookie waits for the co-hosting answer (SEC-109) — pending Thomas (TRIAGE1, 2026-10-27)

### SEC-127 · minor · Admins can sign in as any user without that being recorded, and sensitive admin actions have no step-up

- **Where:** auth §2 l.65; api §13.1 l.294; admin §3.4 l.168 (audit log "append-only").
- **Evidence:**
  - Sign-in links can be "also shown on screen by an admin as a copyable link" (auth l.65).
  - "`User.is_admin` bypasses permissions" (api l.294).
- **Problem:**
  - An admin-minted sign-in link lets the admin act as the user, and gate decisions show the user's name, so non-repudiation is lost.
  - Downloading or restoring a backup, `admin`-scope tokens and key operations need no re-authentication.
  - The audit log is "append-only" by convention only, in the same database.
- **Risk:** L L × I H.
- **Proposal:**
  - **Design:**
    - Admin-minted links are allowed only in `demo` mode or when explicitly enabled. The session they open carries `act=<admin>`, which History shows.
    - Step-up re-authentication, no more than 5 min old, for backups, restore, keys and `admin` tokens.
    - Audit rows are hash-chained, and the head hash is written into each backup manifest.
  - **Test:** a decision made in an admin-minted session shows the admin as the actor.
- **Related:** R1 SR-020 (the admin flag is missing from the schema).
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-128 · minor · Revocation latency, deactivation, and abuse limits on ingest and SSE

- **Where:** auth §3 l.99, l.105; admin §2.1 l.85 (Deactivate "revokes the user's tokens"); api §4 l.81 (limits), §5 l.101 (`GET /version`).
- **Evidence:**
  - Access JWTs live 1 h (auth l.99).
  - An embed token may also carry `decide` for 1 h.
  - Lockout is per account (auth l.64).
- **Problem:**
  - A deactivated principal keeps a valid JWT for up to 1 h.
  - Per-account lockout lets an attacker lock admins out.
  - With no per-run ingest rate limit and no SSE connection cap, one leaked ingest token can saturate the single SQLite writer.
  - An unauthenticated `/version` reveals the exact build.
- **Risk:** L M × I M.
- **Proposal:**
  - **Defaults:**
    - check `principals.disabled_at` and the token `jti` revocation list on every request, cached for at most 30 s;
    - back-off, not lockout;
    - ingest limited to N events/s per run token, with 429 and buffering on the client (synthesis §8 already buffers);
    - SSE connections capped per principal;
    - `/version` details shown to authenticated users only.
  - **Test:** after deactivation, the next request gets 401.
- **Found by:** security-reviewer
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SEC-129 · minor · OIDC device flow and IdP-initiated SAML need explicit safeguards

- **Where:** auth §2 l.69, l.71; api §5 l.87 (`/auth/device`).
- **Evidence:**
  - "**OIDC device code** over SSH or HPC" (auth l.71).
  - "IdP-initiated only when explicitly enabled" (auth l.69).
- **Problem:**
  - Device-code phishing ([RFC 8628 §5.4](https://www.rfc-editor.org/rfc/rfc8628#section-5.4)).
  - IdP-initiated SAML has no `InResponseTo`, so replay protection depends on an assertion-ID cache that is not specified.
- **Risk:** L M × I M.
- **Proposal:**
  - **Design (auth §2):**
    - The device approval page shows the requesting host, IP and time.
    - Device codes expire in 10 min or less.
    - Tokens from the device flow are limited to CLI scopes.
    - IdP-initiated SAML keeps an assertion-ID cache until `NotOnOrAfter`, and requires a matching `Audience`.
  - **Test:** replaying the same IdP-initiated assertion is refused.
- **Found by:** security-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### SEC-130 · minor · `webhooks.secret_hash` cannot produce HMAC signatures

- **Where:** api §7 l.232 vs §8 l.252.
- **Evidence:** the table has "`secret_hash`" (l.232), while delivery uses an "HMAC-SHA256 signature in `Spectio-Signature`" (l.252).
- **Problem:**
  - An HMAC needs the plaintext secret.
  - An implementer will either store the secret in clear, so that a DB or backup leak lets anyone forge callbacks to the LIMS, or sign with the hash, which turns the hash into the secret.
- **Risk:** L M × I M.
- **Proposal:**
  - **Design (api §7):** store `secret_ref` through the secret backend, encrypted at rest. Show the secret once. Rotate it with 24 h of dual signatures.
  - **Test:** the DB dump does not contain the webhook secret.
- **Related:** R1 SR-026 (webhooks are both a project table and a notifier plugin instance).
- **Found by:** security-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

---

## Questions for Thomas

1. **`single` mode on login nodes (SEC-102, R1 SR-031).** There are two options:
   - keep the mode on login nodes, with a Unix socket plus a local token, a `Host` allow-list and CSRF;
   - restrict it to laptops and service nodes.

   The first keeps the "no setup on HPC" story; the second is simpler.
2. **Running as a Unix identity on group clusters (SEC-101, R1 SR-014).** There are three options:
   - one runner per user;
   - a service-node runner that submits per user through slurmrestd with per-user JWTs;
   - a declared shared account with explicit delegation.

   Two facts are unknown: whether EMBL's acceptable-use policy forbids shared accounts, and whether slurmrestd is available with per-user JWTs **[to be validated at EMBL]**.
3. **Project visibility (SEC-121 vs R1 SR-029).** SR-029 proposes two values, `private` and `instance`, like depictio. SEC-121 proposes splitting `instance` (signed-in users) from `public` (guests too). Which model, and does depictio's `is_public` map to `public`?
4. **depictio trust (SEC-120).**
   - Should a depictio admin ever become a Spectio admin automatically? The proposed default is no.
   - Should we ask depictio for `aud` and a JWKS endpoint (ecosystem-reuse §3, item 5), or drop the audience test?
5. **Co-hosting default (SEC-109, DEP-T-013).** Should the default be separate hosts with IdP SSO, or path co-hosting on one domain? Path co-hosting merges the two applications' trust domains.
6. **Agent approvals (SEC-111).** Are the defaults acceptable: a 15-minute hold before an agent approval takes effect, and a 10 % cap on items an agent may exclude?
7. **Plugins as trusted code (SEC-124).** Do you accept stating that installed server plugins are as trusted as admins, and rewording architecture §10 risk 2 to match?
8. **Threat-model spec.** The R5 playbook asks for a draft `docs/specs/security-and-threat-model.md`. This step wrote only this review file, so the reviewer's outline is in the appendix below. Should `/apply-findings R5-security` create the spec from it, with the ownership rule stated there?

## Proposed spikes

| Spike | Question it answers | Findings | Exit |
|---|---|---|---|
| `spikes/sec-single-mode/` | Can `single` mode on a multi-user host refuse a second Unix user, a rebinding page and a cross-site POST, without hurting the first-run experience? | SEC-102 | A container with two Unix users: `SO_PEERCRED` check, `Host` allow-list, CSRF, `spectio local open` one-time link; research note |
| `spikes/sec-runner-confinement/` | Can realpath roots coexist with Nextflow's default absolute-symlink publishDir and Snakemake outputs, and with `runner.toml`? | SEC-105, SEC-115 | On sind, the synthetic pipelines pass, while forged paths, `..` globs and a symlink to `$HOME` are refused |
| `spikes/sec-redaction-canary/` | Where does a canary secret in params or env end up? | SEC-107, SEC-108 | Run the nf-core/rnaseq test profile with an `nf-spectio` stub and `nf-tower`, then grep the logs, the captured config, the crate and the Seqera payload. Also compare `StringUtils.isSensitiveName` with `SECRET_KEYS` **[to be validated]** |
| `spikes/sec-authz-matrix/` | Can a FastAPI route declaration force an action on every route, and catch IDORs automatically? | SEC-104, SEC-125, SEC-112 | A route decorator, a test that enumerates `openapi.json`, and a two-tenant fixture that expects 404 on foreign IDs, all on a toy app |
| `spikes/sec-slurm-identity/` | Does a service-node runner with per-user slurmrestd JWTs work on a local Slurm, and what do `PrivateData` and `AccountingStoreFlags=job_env` expose? | SEC-101, SEC-103 | sind with slurmrestd and JWT auth: jobs submitted as two users, plus `env` and `sacct` dumps; research note |

---

## Appendix · Draft outline for a future `docs/specs/security-and-threat-model.md`

This is the reviewer's one-page outline, not a spec yet. Finding IDs have been updated to the numbering of this file.

**0. Decisions in brief.**
- Separate hosts by default.
- Runners act as a declared Unix identity.
- Every route is in the authorization matrix.
- Secrets are references everywhere.
- Plugins are trusted code.
- Imports are untrusted input.
- Agents propose by default.

**1. Assets.**
- Gate decisions and the audit trail.
- Run data and evidence, some of it clinical (UX-129).
- Cluster accounts.
- Token-signing and secret-store keys.
- Group credentials (S3, registries, LabID).
- Webhook secrets.
- Backups.

**2. Actors.**
- Users, link guests and public guests.
- Service accounts (LIMS, CI, robots), AI agents and runners.
- Plugin code and host applications (LabID, depictio).
- Brokers, cluster co-users, server and instance admins, site admins.

**3. Trust boundaries and STRIDE summary.** One row per boundary: S, T, R, I, D and E threats, with the finding that controls each.

| Boundary | Main threats | Controls (findings) |
|---|---|---|
| Browser ↔ server | XSS, CSRF, session fixation, rebinding | SEC-102, 109, 126 |
| Sign-in methods (password, magic, share, provisioning, OIDC, SAML, device) | takeover, forwarding, phishing | SEC-113, 117, 123, 127, 129 |
| depictio JWT trust | revoked or over-privileged tokens | SEC-120; DEP-T-015 |
| Co-hosting proxy | shared origin, header spoofing, shared Redis and S3 | SEC-109; DEP-T-013, DEP-T-014 |
| Host page ↔ embeds | attribution, postMessage | SEC-122 |
| Service accounts ↔ API | scope gaps, IDOR, idempotency | SEC-104, 125 |
| Runner ↔ server | forged values, credential theft, server → runner RCE | SEC-106, 115 |
| Runner ↔ cluster | identity sharing, path escape, secret exposure | SEC-101, 103, 105 |
| Engine plugins ↔ ingest | token leakage, forged events, flooding | SEC-108, 128 |
| AI agents ↔ gates | injection, unbounded approval | SEC-111, 114 |
| Event bridges | shared principal, cross-tenant topics | SEC-116 |
| Plugins ↔ core | full trust, confused deputy, SSRF | SEC-118, 124 |
| Backups and imports | key exposure, injection | SEC-110, 119 |
| Tenancy surfaces (search, SSE, webhooks, exports, logs, task ledger) | cross-project leaks | SEC-107, 112, 121, 130 |

**4. Security invariants.** Numbered and testable. Examples:
- I1: no route without an action.
- I2: no event without a project or an environment.
- I3: no secret value in any sink.
- I4: no runner read outside its roots.
- I5: no decision without a resolved human or agent principal.
- I6: no restore of unsigned keys.

**5. Secure defaults table.** Setting, default, why, and the finding behind it.

**6. Token and credential catalogue.** Owned by auth §3; linked from here, not duplicated. Add an ingest-token row (SEC-108).

**7. Security test matrix.** It extends auth §6:
- a two-tenant fixture across every route;
- a canary-secret grep over every sink;
- runner confinement tests;
- bridge replay tests;
- import fuzzing (zip, JSON-LD, git URLs).

**8. Site prerequisites and operator guide.**
- Slurm `PrivateData`, `hidepid`, trusted proxies.
- Redis ACLs and broker ACLs.
- Backup recipients.

**9. Out of scope and accepted risks.**
- Admins are fully trusted.
- A malicious pipeline runs as its launcher.

**10. Open questions.**
- The site AUP on shared accounts.
- slurmrestd per-user JWTs at EMBL.
- `aud` and JWKS in depictio.
- The MCP authorization version.

**Ownership rule.** This file would own the boundaries, the invariants and the test matrix. Mechanisms stay in the specs that own them: auth (§2–§4), api (§6, §8, §9), architecture (§3, §7.6), admin (§4.3), checking (§7, §11) and schedulers (§6).
