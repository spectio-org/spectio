# Inbox — questions for Thomas

The autopilot adds entries here; answer inline with `Answer: <option>` (and a sentence if useful). Entries marked **assumed** already proceed with the recommended option; your answer overrides it on the next tick.

<!-- autopilot: append entries below this line -->

### #1 · Virgil font licence (blocks publishing the hand-drawn figures' font)

- **Context:** `tools/diagrams/FONT-LICENSE.md`. The file copied from depictio says "Copyright (c) Jason Smith … All rights reserved", while Excalidraw's page says OFL-1.1, and also MIT.
- **Options:**
  - (a) check `github.com/excalidraw/virgil` yourself and, if it is OFL, commit the font with `OFL.txt`;
  - (b) switch to Excalifont;
  - (c) keep the font local only (`SPECTIO_VIRGIL_TTF`), so CI renders SVG only and PNGs are rendered locally.
- **Recommendation:** (a), with (c) until then. **Assumed:** (c), so the font is not committed.
- **Answer (Thomas, 2026-10-26):** Virgil is set aside for now. Read as (c): the font stays local and is not committed, and figures are rendered locally. *Handled.*

### #2 · Install telemetry: opt-in (current) or opt-out like depictio?

- **Context:** `telemetry-and-analytics.md` §0.4.
- **Options:**
  - (a) opt-in with a prompt at `spectio init` and at the first admin sign-in (current);
  - (b) opt-out like depictio, with a notice and the payload preview.
- **Recommendation:** (a) for institutional installs. **Assumed:** (a).
- **Answer (Thomas, 2026-10-26):** (b) opt-out, like depictio. Applied in `telemetry-and-analytics.md` §0.4 and §2.3. *Handled.*

### #3 · Let CI merge into `main`?

- **Context:** `documentation-system.md` §8, `autopilot.md` §8. PRs into `autopilot/integration` auto-merge after the checks and the doc review. Merging into `main` needs `AUTOMERGE_MAIN=true`, and branch protection set up with the `gh` commands in `autopilot.md` §8.
- **Options:**
  - (a) keep human merges into `main` for now;
  - (b) set the variable now.
- **Recommendation:** (a) until W1 has run once; then (b). **Assumed:** (a).
- **Answer (Thomas, 2026-10-26):** Claude may merge into `main` for now. The autopilot merges the promotion PR (merge commit) once every check passed and doc-reviewer approved. Applied in `CLAUDE.md`, the autopilot skill and `autopilot.md` §5 and §8. *Handled.*

### #4 · Permissions, status line and hook for unattended runs

- **What to add:** the JSON in `autopilot.md` §4, which covers the permission rules, the budget status line and the `StopFailure` hook. Agents cannot add it themselves.
- **Answer with:** `done` when added.
- **Status (2026-10-26):** a ready file is in `tools/autopilot/claude-settings.json` (the current `.claude/settings.json` plus the rules of `autopilot.md` §4; `git push origin main` is not denied, per #3). An agent may not write `.claude/settings.json` itself (refused as self-modification). Copy it with `cp tools/autopilot/claude-settings.json .claude/settings.json` and commit.
- **Answer (Thomas, 2026-10-26):** the file was copied to `.claude/settings.json` on `main` (`7dd8488`), at Thomas's request. The permissions themselves are to be discussed again. *Open.*

### #5 · Clean git history before the repository is shared

- **Context.**
  - The remote has a single branch, `claude/foundations-2026-10-26`, which is also its default. Nobody else has cloned it.
  - Its history holds, in commit `b2687d8`, screenshots and a video that show the owner's name, initials, `/scratch/tw/…` and "EMBL SLURM".
  - It also holds a 3.3 MB GIF committed in `0e5b97a` and removed later.
  - The design boards themselves (`design/ui-canvas`, current tree) still show those names. Media are now rendered with fixture names.
- **Done (additive, nothing deleted).** A new branch `main` with one clean commit holding the current tree was pushed. The old history is kept as the local branch `archive/history-2026-10-26` and on the remote branch above.
- **Your part.** In GitHub settings, make `main` the default branch. Then delete the old branch (`git push origin --delete claude/foundations-2026-10-26`), or tell the autopilot to do it.
- **Optional.** Also replace the real names in the boards with fixtures before going public.
- **Answer (Thomas, 2026-10-27, dashboard):** "make `main` the default branch, done?" Yes: the remote's default branch is `main` (checked with `git ls-remote --symref origin HEAD`). The old remote branch `claude/foundations-2026-10-26` still exists; it is deleted only on Thomas's explicit go (the history stays as the local `archive/history-2026-10-26`). *Open (branch deletion).*

### #6 · Nextflow ingestion: keep the Tower protocol, or only Spectio's own plugin?

- **Context.** `docs/research/adoption-and-positioning-2026-10-26.md` §2 and `synthesis.md` §1 and §2bis. Accepting Nextflow's built-in Tower protocol gives zero-install monitoring, as nf-shard does, but the protocol is undocumented and positions Spectio closer to Seqera.
- **Options:**
  - (a) keep both, with the Tower route labelled unofficial and best effort;
  - (b) `nf-spectio` only.
- **Recommendation:** (a) for the alpha, revisited before the public beta. **Assumed:** (a).
- **Answer (Thomas, 2026-10-26):** to discuss, choosing the best balance of sustainability, features, access to information and ease of connection. Proposal sent in the session: `nf-spectio` as the main route, set up once by `spectio login`; the Tower protocol kept as a best-effort fallback for monitoring only. *Open.*
- **Answer (Thomas, 2026-10-26, later):** (b) `nf-spectio` only, for Nextflow and from the MVP on. The Tower protocol is not implemented. The reason is coexistence rather than replacement: a run can report to Seqera Platform and to Spectio at the same time, so users can move between the two. See [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md). *Handled.*

### #7 · Licence and the date the repository goes public

- **Context.** JOSS needs more than six months of public history, and an OSI licence (adoption note §4).
- **Options:**
  - (a) MIT, public at the start of the private alpha (0.2);
  - (b) MIT, public at the beta.
- **Recommendation:** (a). **Assumed:** none. This needs your decision before the repository becomes public.
- **Answer (Thomas, 2026-10-26):** MIT. The date the repository goes public is not set; it depends on progress. *Licence handled; date open.*

### #8 · Do not set branch protection yet (R8b blockers)

- **Context:** `docs/reviews/R8b-depictio-tooling.md`, findings DEP-T-001 and DEP-T-002.
  - The required checks listed in `autopilot.md` §8 include path-filtered workflows, so docs-only PRs would wait forever.
  - release-please with the default token can trigger neither the release builds nor the checks on its own PR.
- **Recommendation:** run the `gh` protection commands of `autopilot.md` §8 only after APPLY1 has added:
  - a single `ci-ok` check;
  - a GitHub App token for release-please and the other bot PRs.
- **Your part, meanwhile:** create a GitHub App for the repository (contents and pull requests: write), and store its ID and key as environment secrets.
- **Assumed:** protection is not set.
- **Answer (Thomas, 2026-10-27, dashboard):** asked what to do concretely. Steps sent in the session: create the GitHub App (Contents and Pull requests: read and write, Issues: read and write for the release-please labels **[to be validated]**, webhook off), install it on this repository only, generate a private key, store the App ID and the key as environment secrets, as this entry and dev-env §12 say (the `release` environment name and the secret names are D4's proposal); D4 wires it with `actions/create-github-app-token` **[inputs to be validated from its README]**. *Open (waiting for the App).*

### #9 · GitHub organisation for packages and images (DEP-T-026)

- **Context:** the names `spectio`, `spectio-server`, `spectio-sdk`, `spectio-cli` and `@spectio/client` were free on PyPI and npm on 2026-10-26. Trusted publishers and GHCR packages are bound to the owner and the repository.
- **Options:**
  - (a) a `spectio` organisation;
  - (b) one organisation shared with depictio;
  - (c) stay under `weber8thomas` until 0.1.0.
- **Recommendation:** (a) or (b), decided before 0.1.0, with the names reserved then. **Assumed:** (c).
- **Answer (Thomas, 2026-10-26):** (c) for now; to be moved later. *Handled.*

### #10 · Create the Cloudflare account and the two secrets (dev previews)

- **Context:** `dev-environment-and-testing.md` §7.1. Without these secrets, `previews.yml` builds but does not deploy.
- **Your part (about 10 minutes):**
  1. Create a free account at dash.cloudflare.com.
  2. Go to *My Profile → API Tokens → Create token → Custom* and give the token the permission *Account · Cloudflare Pages · Edit*, on your account only.
  3. Copy the *Account ID* shown on the dashboard.
  4. In GitHub, go to *Settings → Environments → New environment* `previews`, and add the secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
  5. Optional: in *Zero Trust → Access*, restrict `*.spectio.pages.dev` previews to your email.
- **Answer with:** `done`. Step D5 then checks everything end to end.
- **Answer (Thomas, 2026-10-26):** done, the secrets are set in the repository. *Handled.*

## TRIAGE1 (2026-10-27)

**Step page:** [TRIAGE1](../progress/W2/TRIAGE1.md)

- **Triaged:** 320 findings from R1, R2, R4, R5, R7, R8, R8b, R9, R11 and R12. 163 accepted, 4 rejected, 153 sent here.
- **Assumed:** 88 of the 153 already proceed on the recommended option, marked `assumed — pending Thomas`. The other 65 wait for your answer.
- **How to answer:** the 153 are grouped by decision into #11 to #30. #11 to #27 hold the reserved questions: #11 to #26 block parts of APPLY1 and come first; #27 only holds messages to other teams and blocks nothing. #28 to #30 only list assumptions to confirm. One `Answer:` line per entry is enough; name a finding ID to make an exception.

APPLY1 applies the accepted and assumed findings of R1 to R11 and leaves the sections named under **Blocked** untouched until you answer. R12 findings are outside APPLY1's rounds, so they block a later apply step, not APPLY1.

### #11 · Ingest credential for observed runs, and are observed runs in 0.1?

- **Covers:** [SR-001](../reviews/R1-consistency.md#sr-001-blocker-the-engine-server-ingest-contract-is-undefined) (blocker), [SEC-108](../reviews/R5-security.md#sec-108-major-ingest-credentials-for-observed-runs-are-undefined-and-tokens-may-land-on-command-lines-in-configs-and-in-captured-run-metadata).
- **Context:** api §14 (the engine → server ingest contract: envelope, run handshake, driven-run variables, batching, logs) cannot be written until we know how a run started in a terminal gets a credential. SEC-108 proposes a dedicated ingest token: scope `ingest:write`, one project, may only create observed runs and post their events, 30 days, rotatable, a 0600 file written by `spectio login`, never on a command line.
- **Options:**
  - (a) api §14 as proposed; observed runs use the SEC-108 ingest token, written once by `spectio login` / `engine … --install`;
  - (b) api §14 as proposed; observed runs only through a wrapper (`spectio run nextflow …`) that gets a per-run token;
  - (c) driven runs only in 0.1; observed runs from the alpha.
- **Recommendation:** (a), with the scope registered once in auth §3 (see #13).
- **Assumed:** none.
- **Blocked:** APPLY1 for api §14 and the auth §3 ingest-token row; nf-spectio and the Snakemake logger credential handling (spike T2 envelope); the walking skeleton. Related assumptions that already proceed: [SR-006](../reviews/R1-consistency.md#sr-006-major-the-cli-command-tree-lacks-commands-that-other-specs-cite) (no wrapper, setup by `spectio login`, see #28) and [CH-002](../reviews/R4-constraints.md#ch-002-major-no-compatibility-window-for-the-ingest-and-runner-protocols-across-bridge-runner-and-server-versions) (separate ingest version, see #28).
- **Note:** Not needed for 0.0.1 (single user, local engines; Thomas 2026-10-27); stays open for later versions.
- **Note (2026-10-27, cut revised):** 0.0.1 now runs on SLURM from a per-user server on the login node ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), not with local engines. Still not needed for 0.0.1: observed runs are out of it, and the plugins only write to the spool.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. Not needed for 0.0.1; applied to api §14 and auth §3 in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #12 · Runner ↔ server transport and runner credential lifetime

- **Covers:** [SR-002](../reviews/R1-consistency.md#sr-002-blocker-runner-server-protocol-no-owner-two-transports-two-credential-lifetimes) (blocker), [SEC-106](../reviews/R5-security.md#sec-106-major-the-runner-credential-has-no-route-allow-list-and-it-can-forge-the-check-values-that-drive-auto-approval), [CH-032](../reviews/R4-constraints.md#ch-032-minor-runner-channel-in-practice-proxies-idle-timeouts-the-jvm-and-internal-cas), [CH-007](../reviews/R4-constraints.md#ch-007-major-runner-commands-have-no-table-three-transports-and-no-idempotent-launch), [UX-124](../reviews/R12-ui-scenarios.md#ux-124-minor-connecting-and-checking-a-runner) (R12).
- **Context:** two transports and two credential lifetimes coexist; architecture §7.7 becomes the owner either way.
  - SR-002: one primary transport, and does the runner credential rotate or live until revoked?
  - SEC-106: runner credential rotated every 24 h (registration until revoked), stored 0600 or in a keyring, accepted only on `/runners/{id}/*`, events bound to the environment and assigned runner, a gate policy may disable auto-approval from runner values, only owning-group admins mint registration tokens.
  - CH-032 (assumed): HTTPS long poll of at most 55 s, proxy variables and a CA bundle read by bridges and runner, checked by `spectio doctor`.
  - CH-007 (assumed): a `runner_commands` table with leases, written in the decision's transaction; idempotent launch through the head-job name `spectio-<run>-<launch>`.
  - UX-124 (R12): EnvConnect shows a 15 min single-use registration token and a 24 h rotation that no spec sets; also a `runner.self_check` event and module loading.
- **Options:**
  - (a) HTTPS long poll (as admin §3.2 and the 2026-10-25 log say), chunked upload for files, WebSocket route removed; SEC-106 in full, with the UX-124 values (15 min registration, 24 h rotation with overlap);
  - (b) as (a), but the runner credential lives until revoked (SEC-106 allow-list and run binding only);
  - (c) runner-initiated WebSocket over 443 with long-poll fallback.
- **Recommendation:** (a). Checking EMBL proxies needs EMBL IT and waits until access exists.
- **Assumed:** CH-032 and CH-007 proceed on their option A; the credential lifetime and who mints registration tokens are not assumed.
- **Blocked:** APPLY1 for architecture §7.7 and the auth §3 runner row; every launch, cancel, file view and stop file; the walking skeleton. UX-124 blocks the EnvConnect values (later apply).
- **Note:** Not needed for 0.0.1 (single user, local engines; Thomas 2026-10-27); stays open for later versions.
- **Note (2026-10-27, cut revised):** 0.0.1 now runs on SLURM from a per-user server on the login node ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), not with local engines. Still not needed for 0.0.1: the runner is built into the server process; a shared server with remote runners stays later.
- **Answer (Thomas, 2026-10-27, dashboard):** asked for the pros and cons of (a), (b) and (c), and why (a). (a): outbound HTTPS long poll passes the cluster proxies, and a stolen runner credential expires within 24 h; the cost is rotation logic. (b): simpler, no rotation, but a leaked credential stays valid until someone revokes it. (c): commands arrive instantly with fewer requests, but HPC proxies often cut long-lived connections ([CH-032](../reviews/R4-constraints.md#ch-032-minor-runner-channel-in-practice-proxies-idle-timeouts-the-jvm-and-internal-cas)), so a long-poll fallback is needed anyway and there are two transports to maintain. (a) is recommended for robustness behind proxies at little cost. Not needed for 0.0.1 (the runner is built into the server). *Open.*

### #13 · Token registry, authorisation matrix and which column authorises reads

- **Covers:** [SR-024](../reviews/R1-consistency.md#sr-024-major-tokens-are-specified-twice-differently), [SEC-104](../reviews/R5-security.md#sec-104-major-no-endpoint-action-scope-role-matrix-so-every-endpoint-has-a-principal-and-a-can-cannot-be-checked), [SEC-128](../reviews/R5-security.md#sec-128-minor-revocation-latency-deactivation-and-abuse-limits-on-ingest-and-sse), [SEC-122](../reviews/R5-security.md#sec-122-major-gate-decisions-through-embed-tokens-are-attributed-to-the-hosts-service-account-which-bypasses-human-policies), [CH-030](../reviews/R4-constraints.md#ch-030-major-moving-a-run-between-projects-rewrites-millions-of-rows-and-contradicts-the-append-only-log), [UX-201](../reviews/R7-ui.md#ux-201-major-role-dependent-states-are-not-drawn-and-the-api-does-not-say-which-actions-are-allowed), [SEC-112](../reviews/R5-security.md#sec-112-major-sse-the-event-log-and-search-have-no-stated-tenancy-filter-revocation-behaviour-or-rule-for-events-with-no-project), [UX-111](../reviews/R12-ui-scenarios.md#ux-111-minor-where-each-gate-comes-from-and-lab-wide-figures) (R12).
- **Context:**
  - SR-024: auth §3 owns token kinds, formats, lifetimes and one scope registry. JWT access plus rotated refresh, opaque `spk_` for personal and service tokens?
  - SEC-104: an endpoint → action → scope → role matrix in api §6; effective rights = role ∩ token scopes ∩ project restriction ∩ gate policy; new tokens restricted to one project unless "all my projects" is ticked.
  - SEC-128: revocation checked per request (cache ≤ 30 s), per-run-token ingest limit with 429, SSE connections capped per principal. The `/version` part conflicts with the 2026-10-26 decision (git_sha in the footer).
  - SEC-122: `decide` embed tokens carry an `act` claim naming the end user, signed by the host's service account, 5 min TTL, unknown users refused; postMessage with explicit `targetOrigin` and `event.origin` checks. This commits LabID and other host apps to sign `act`.
  - CH-030: `project_id` authorises only root objects (runs, workflows, environments, webhooks); child tables resolve through `run_id`; moving a run is a chunked 202 Operation.
  - UX-201: the UI hides what a role can never do and disables with a reason what a grant would allow; the API returns `allowed_actions` computed from the SEC-104 matrix.
  - SEC-112 (assumed): every event carries `project_id` or `environment_id`, a per-event fan-out filter, streams end within 30 s of revocation.
  - UX-111 (assumed, R12): `can_decide` replaced by UX-201's `allowed_actions` once answered.
- **Options:**
  - (a) all recommendations: SR-024 (a), SEC-104 A, SEC-128 B (keep `/version` public), SEC-122 A, CH-030 A, UX-201 (a);
  - (b) as (a), but tokens stay unrestricted by default (SEC-104 B);
  - (c) one opaque `spk_` format for every token (SR-024 b), the rest as (a).
- **Recommendation:** (a). The SEC-122 postMessage origin checks apply whatever the answer.
- **Assumed:** SEC-112 A and UX-111 A proceed; the rest is not assumed.
- **Blocked:** APPLY1 for auth §3 (token catalogue, scope list, revocation), api §6 (matrix, role rows), api §4 limits, api §9 embeds and the LabID integration contract, api §5 `allowed_actions`, api §5/§7/§8 tenancy and run move; the role-variant boards of R7; spike sec-authz-matrix exit criteria.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), but kept lightweight for single-user mode and the MVP: 0.0.1 keeps only the token link of dev-env §15.3; the token registry, matrix and scopes apply from the first multi-user version. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #14 · Which Unix identity a launch runs as, and who may move a run to another runner

- **Covers:** [SR-014](../reviews/R1-consistency.md#sr-014-major-which-unix-account-runs-a-launch-on-a-group-owned-environment-is-undefined), [SEC-101](../reviews/R5-security.md#sec-101-blocker-a-runners-unix-account-is-not-tied-to-the-principals-who-launch-on-it) (blocker), [UX-206](../reviews/R7-ui.md#ux-206-major-review-queue-scopes-bulk-actions-and-move-to-another-runner-have-no-endpoint), [SEC-103](../reviews/R5-security.md#sec-103-major-group-credentials-reach-runners-and-jobs-where-any-pipeline-or-scheduler-user-can-read-them).
- **Context:** on a group-owned environment, the runner's Unix (or Kubernetes) account is not tied to the people who launch on it.
  - SR-014: `execution_identity: per_user` only, or `per_user` and `shared` (a service account with explicit delegation)?
  - SEC-101: an environment records `run_as`; a launch needs a grant plus a link or a revocable delegation from that user; a runner moves only between runners with the same `run_as`.
  - UX-206: gate assignment (assignee, `snoozed_until`, `deciders[]`, advisory only) and who may `:reassign` a queued run (owner and editors, same `run_as` only).
  - SEC-103 (assumed): per-run credentials as 0600 files, `--export=NONE` for head jobs, neutral job names, `PrivateData=jobs` recommended to sites.
- **Options:**
  - (a) one runner per user by default (SEC-101 A); a service-node runner submitting per user through slurmrestd with per-user JWTs where it exists (SEC-101 B); a declared `shared` account only with listed delegation; UX-206 (a);
  - (b) `per_user` only (SR-014 a), no shared accounts; UX-206 (a);
  - (c) as (a), but drop assign, snooze and "Move to another runner" from the boards for 0.1 (UX-206 c).
- **Recommendation:** (a), never an undeclared shared account. The EMBL acceptable-use policy and slurmrestd availability are **[to be validated at EMBL]** and need EMBL IT.
- **Assumed:** SEC-103 A proceeds; the identity model is not assumed.
- **Blocked:** APPLY1 for api §6, schedulers §6, the environments/runners schema and the gate assignment fields (api §5/§7, checking); spike sec-slurm-identity; runner protocol design and P1 planning.
- **Note:** Not needed for 0.0.1 (single user, local engines; Thomas 2026-10-27); stays open for later versions.
- **Note (2026-10-27, cut revised):** 0.0.1 now runs on SLURM from a per-user server on the login node ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), not with local engines. Still not needed for 0.0.1: every launch runs as the Unix account that started `spectio serve`.
- **Answer (Thomas, 2026-10-27, dashboard):** "skip k8s for now; focus on local and SLURM launch". No option was named. The autopilot reads it as (a) restricted to local and SLURM (per-user runner, slurmrestd where it exists, declared shared accounts only with delegation), with the Kubernetes identity model deferred; this reading needs Thomas's confirmation, and the SEC-103 text stays *assumed* until then. *Open (reading to confirm).*

### #15 · `single` mode on shared login nodes

- **Covers:** [SR-031](../reviews/R1-consistency.md#sr-031-major-single-user-mode-trusts-loopback-but-loopback-is-shared-on-a-login-node), [SEC-102](../reviews/R5-security.md#sec-102-blocker-single-mode-trusts-loopback-but-loopback-is-shared-by-every-user-of-a-login-node) (blocker).
- **Context:** `single` mode trusts tokenless 127.0.0.1, which every user of a login node shares. Both reviews ask whether that deployment is supported, and how.
- **Options:**
  - (a) supported, hardened: tokenless only on a 0700 Unix socket with SO_PEERCRED, or a 0600 local token; TCP loopback needs a cookie from a one-time URL; Host allow-list and CSRF on every write;
  - (b) `single` mode only on laptops and service nodes;
  - (c) (a), and also refuse to start tokenless when other users are logged in.
- **Recommendation:** (a): never trust the network peer, and keep the no-setup HPC story. Validate in spike sec-single-mode.
- **Assumed:** none.
- **Blocked:** APPLY1 for auth §1/§6 and api §1/§6; spike sec-single-mode; the walking-skeleton auth design.
- **Note:** Not needed for 0.0.1 (single user, local engines; Thomas 2026-10-27); stays open for later versions.
- **Note (2026-10-27, cut revised):** the 0.0.1 part is answered ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)): 0.0.1 now runs on the login node, so tokenless loopback is not accepted. The server binds to 127.0.0.1 only, the user opens it through an SSH tunnel, and every request needs the token set as a cookie from a one-time link ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)). The rest stays open for later versions: a Unix socket with SO_PEERCRED, refusing to start when other users are logged in, `single` mode on a shared server.
- **Answer (Thomas, 2026-10-27, dashboard):** "too complex, re-explain". Re-explained in the session: the 0.0.1 part is already settled by the token link; three points stay open for later: a Unix socket that only the owner can open, refusing to start when other users are logged in, and `single` mode on a shared server. *Open.*

### #16 · What ships in 0.1 (MVP cut)

- **Covers:** [SR-007](../reviews/R1-consistency.md#sr-007-major-phase-labels-do-not-map-to-release-stages-and-the-phase-tables-contradict-each-other), [SR-018](../reviews/R1-consistency.md#sr-018-major-pause-immediate-stop-or-after-the-current-stage), [SR-023](../reviews/R1-consistency.md#sr-023-major-gate-checks-depend-on-the-depictio-catalogue-but-01-has-no-depictio), [DL-104](../reviews/R8-depictio.md#dl-104-major-the-catalogue-as-a-gate-check-source-multiqc-outputs-have-no-columns-and-half-of-the-recipes-cannot-run-standalone), [CH-004](../reviews/R4-constraints.md#ch-004-major-no-scale-model-and-no-performance-budgets-in-any-spec), [UX-227](../reviews/R7-ui.md#ux-227-minor-boards-show-features-outside-the-mvp-without-marking-them), [UX-115](../reviews/R12-ui-scenarios.md#ux-115-minor-outputs-retention-and-the-depictio-hand-off) (R12).
- **Context:** one owner for "what ships in which stage" (new dev-env §15), then the scope questions that depend on it:
  - SR-007: local + SLURM in 0.1; Kubernetes launcher, Postgres, Compose and OIDC in the alpha; Helm in the beta; depictio sink after 0.1; Kafka unscheduled.
  - SR-018: both `:pause` (after a stage) and `:stop` (immediate, keep the cache)? Needed in 0.1?
  - SR-023 and DL-104: 0.1 gate checks bind only to Spectio's own bindings and `multiqc.parquet`; catalogue recipes wait for a public `depictio recipe run` that resolves `dc_ref` (61 MultiQC outputs have no columns; 186 of 339 recipes have `dc_ref` sources). This narrows the 2026-10-26 "one catalogue, two renderers" decision.
  - CH-004: are "100 000 tasks in one run" and "50 concurrent runs" targets for the 0.2 alpha or for 1.0?
  - UX-227 and UX-115: no manual "Send to depictio" in 0.1; a phase chip on boards for 1b features; RunOutputs directory listing and per-run retention now, report sandbox rules decided with #23.
- **Options:**
  - (a) all recommendations: SR-007 (a), SR-018 (a), SR-023 (a) + DL-104 (a), CH-004 A (targets for 1.0, measured by spike S1 in the alpha), UX-227 (a), UX-115 A;
  - (b) as (a), but the Kubernetes launcher is already in 0.1 (SR-007 b);
  - (c) as (a), but pause and stop are both left out of 0.1 (SR-018 c).
- **Recommendation:** (a). The old phase tables are marked historical with a link to dev-env §15. OIDC phasing is asked in #20 (UX-202).
- **Assumed:** none.
- **Blocked:** APPLY1 for dev-env §15, api §5 run verbs and state machine, api §13.6 rule 1, checking §7, reuse §0, api §15 (scale), the stage tags of SR-010, SR-035, SR-042 and SR-043; P1 walking-skeleton cut and P2 milestones; the MVP RunScheduler variant.
- **Answer (Thomas, 2026-10-27):** the reviewers' 0.1 cut is too heavy. The first version is **0.0.1**, a basic local MVP: one user with no sign-in and no roles; the engines run on the same machine as Spectio (local executor), with no SLURM, no Kubernetes and no remote runner; in it: launch a run from the UI, monitor it (state, tasks, stages), relaunch it with changed parameters, track parameters across runs, a simple QC check and gate on one stage, Snakemake (logger plugin) and Nextflow (`nf-spectio`). Out of it: multi-user, auth, roles, OIDC/SAML, share links, SLURM and Kubernetes launchers, scheduler monitoring, Postgres, Compose, Helm, the depictio hand-off, WES, MCP, embedded elements, LabID. The single owner of version contents is now [dev-env §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version); summary page [MVP 0.0.1](../specs/mvp-0.0.1.md); log entry [2026-10-27](../decisions/log.md#2026-10-27-first-version-is-001-a-basic-local-mvp). What later versions contain stays open, with no assumption: SR-007's stage split, SR-018 (pause and stop), SR-023 + DL-104, CH-004, UX-227 and UX-115 still wait for an answer. *Partly handled.*
- **Note (2026-10-27, cut revised again):** Thomas revised the 0.0.1 cut later the same day ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)): runs go to SLURM (head through `sbatch`) from a per-user server on the login node, opened with a token link through an SSH tunnel; no QC checks and no gates in 0.0.1. [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) is updated; the open scope questions above are unchanged.

### #17 · Features after 0.1: WES, TRS, Seqera API, Galaxy, batches, chaining

- **Covers:** [SR-010](../reviews/R1-consistency.md#sr-010-major-the-wes-facade-has-four-release-dates-and-is-under-specified), [FC-044](../reviews/R9-landscape.md#fc-044-minor-the-wes-facade-does-not-say-which-dialect-it-speaks), [FC-046](../reviews/R9-landscape.md#fc-046-minor-synthesis-3-standards-and-existing-projects-is-out-of-date-galaxy-is-more-than-a-minimal-wes), [FC-048](../reviews/R9-landscape.md#fc-048-minor-trs-be-a-client-before-being-a-server), [FC-051](../reviews/R9-landscape.md#fc-051-minor-partial-compatibility-with-the-seqera-api-contradicts-decision-0001), [UX-120](../reviews/R12-ui-scenarios.md#ux-120-major-batch-launches-and-spectios-own-queue) (R12), [UX-121](../reviews/R12-ui-scenarios.md#ux-121-minor-scheduled-start-notifications-pre-flight) (R12), [UX-122](../reviews/R12-ui-scenarios.md#ux-122-major-chaining-runs) (R12), [DEP-T-028](../reviews/R8b-depictio-tooling.md#dep-t-028-minor-a-try-spectio-codespace-for-design-partners), [UX-210](../reviews/R7-ui.md#ux-210-major-the-notification-bell-and-notify-me-when-it-is-back-have-no-endpoint-and-no-board).
- **Context:** each item adds, drops or schedules a feature.
  - SR-010: the GA4GH WES facade ships in the public beta (0.5–0.9), before it, or when a design partner needs it? FC-044 (assumed): strict WES 1.1.0, Sapporo 2.x a non-goal.
  - FC-048: a TRS client (register from a WorkflowHub or Dockstore TRS URL) next to RO-Crate import, under the #25 outbound policy; the TRS server stays later.
  - FC-051: mark synthesis §7bis item 6 (partial Seqera API compatibility) "not planned (decision 0001)", with a new dated log entry.
  - FC-046: refresh synthesis §3 (assumed); the Galaxy `spectio.engine` adapter under roadmap ideas is not assumed.
  - UX-120, UX-122: batch launches with a Spectio-side queue, and run chaining (fetchngs → rnaseq), both after 0.1. UX-121: no `start_at` for now.
  - DEP-T-028: a "try Spectio" Codespaces image for design partners (costs Codespaces quota).
  - UX-210 (assumed): in-app notifications now; Web Push decided after spike S-R7-3.
- **Options:**
  - (a) all recommendations: WES in the public beta, TRS client later, Seqera API not planned, no Galaxy adapter, batches and chaining after 0.1, no `start_at`, Try Codespace at the public beta, Web Push after S-R7-3;
  - (b) as (a), plus the Galaxy adapter under roadmap ideas (FC-046 B);
  - (c) as (a), but keep the Seqera API item "to be studied after a legal check" (FC-051 B).
- **Recommendation:** (a).
- **Assumed:** FC-044 A, the FC-046 table refresh and UX-210 (a) proceed.
- **Blocked:** APPLY1 for api §0/§1/§5/§10 labels (WES, TRS), synthesis §7bis item 6 and its log entry, the roadmap ideas, dev-env §14 private-alpha list, the WES item on the landing page (DOC-001); the LaunchBatch, LaunchChain and LaunchReview boards (later apply).
- **Answer (Thomas, 2026-10-27, dashboard):** to rediscuss later, separately. Nothing changes; the assumed parts stay assumed. *Deferred.*

### #18 · Who can read a project: visibility values and share links

- **Covers:** [SR-029](../reviews/R1-consistency.md#sr-029-major-project-visibility-has-three-values-in-the-model-and-two-in-the-ui), [SEC-121](../reviews/R5-security.md#sec-121-major-instance-visibility-means-everyone-so-on-a-public-or-demo-instance-internal-projects-are-readable-by-anonymous-guests), [DL-112](../reviews/R8-depictio.md#dl-112-minor-instance-is_public-over-exposes-data-on-public-mode-depictio-or-when-embedding-is-on), [SEC-117](../reviews/R5-security.md#sec-117-major-share-links-contradict-the-guest-grant-and-gate-policy-rules-and-work-as-forwardable-bearer-invitations), [UX-204](../reviews/R7-ui.md#ux-204-major-no-share-link-landing-no-create-link-tab-and-no-endpoint-to-list-or-revoke-links), [SR-019](../reviews/R1-consistency.md#sr-019-major-principal-kinds-guests-plugin-and-bridge-principals-are-outside-the-enum).
- **Context:**
  - SR-029 proposes two values like depictio (`private` / `instance`, default viewer grant to the owning group); SEC-121 proposes three (`private` / `instance` for signed-in users / `public` for guests and anonymous, gated by `allow_public_projects`, depictio `is_public` → `public`).
  - DL-112: mirroring `instance` to depictio's `is_public` exposes projects to anonymous users in public, single-user or embed mode; mirror only in standard mode with embedding off, otherwise grant viewer to an instance-wide group.
  - SEC-117 and UX-204: share links contradict the guest rules. Proposal: a separate `link` principal kind; owner and editor create viewer links, only owners create reviewer links (email, one gate, single use, one-time code); a link guest decides only the gates the link names. Check against the 2026-10-26 staging decision (reviewer links bound to one project, role and expiry).
  - SR-019 (assumed): `guest` principal kind with `expires_at` and `share_link_id`; SEC-117 may rename it `link`.
- **Options:**
  - (a) three values (SEC-121 A), DL-112 (a), SEC-117 A / UX-204 (a), the principal kind reconciled with SR-019;
  - (b) two values with `instance` hidden from guests (SEC-121 B), the rest as (a);
  - (c) two values, `instance` readable by guests (current), editors keep minting any link (UX-204 b).
- **Recommendation:** (a).
- **Assumed:** SR-019 (a) proceeds; the kind may be renamed by your answer.
- **Blocked:** APPLY1 for api §6/§12/§13.2 visibility and mapping, auth §2/§2.1 share links, the `principals.kind` enum, the sharing UI (ShareDialog, ShareLanding), the share-link endpoints and the staging reviewer flow (dev-env §13).
- **Answer (Thomas, 2026-10-27, dashboard):** too complex for the MVP. Visibility values and share links wait for a later version; the assumed SR-019 part stays assumed. *Deferred.*

### #19 · Project roles and who may decide a gate (people and agents)

- **Covers:** [SR-025](../reviews/R1-consistency.md#sr-025-major-launcher-and-reviewer-rungs-on-a-ladder-or-capability-flags), [SR-033](../reviews/R1-consistency.md#sr-033-major-on_fail-open_gate-creates-a-gate-with-no-items-policy-or-deciders), [SEC-114](../reviews/R5-security.md#sec-114-major-spectioyml-from-a-workflow-repository-can-widen-gate-policy-add-code-and-add-editable-paths-with-each-new-version), [UX-217](../reviews/R7-ui.md#ux-217-major-workflow-visibility-per-group-is-drawn-but-the-data-model-has-no-workflow-grants), [SEC-111](../reviews/R5-security.md#sec-111-major-agent-decisions-on-gates-are-not-bounded-or-reversible-and-they-record-a-self-reported-identity), [UX-106](../reviews/R12-ui-scenarios.md#ux-106-major-the-meaning-of-flag-undecided-items-and-reviewer-added-flags) (R12), [UX-126](../reviews/R12-ui-scenarios.md#ux-126-major-quotas-limits-and-who-may-launch-where) (R12).
- **Context:**
  - SR-025: base role viewer / editor / owner plus `launch` and `review` capabilities, or a five-step ladder?
  - SR-033: a gate opened by `on_fail: open_gate` is decided by project reviewers and above, `agents: none`, unless the overlay's run-level `decide` says otherwise.
  - SEC-114: policy keys in a repository `spectio.yml` stay inert until a project editor approves them per workflow version; strictest of instance, project, overlay and author wins.
  - UX-217: the workflow catalogue is per project (no `workflow_grants`) for the MVP.
  - SEC-111: agent approvals take effect after a 15 min hold with notification, at most 10 % excluded items, per-agent rate limits, no bulk-decide for agents, `claimed_model`, MCP tokens with `aud=<instance>/mcp`.
  - UX-106 (R12): anyone allowed to decide may Flag an item below a `block` threshold, with a recorded reason; Apply stays disabled until each block-failing item is decided.
  - UX-126 (R12): per-agent environment grants and partition allow-lists now; Spectio quotas after 0.1.
- **Options:**
  - (a) all recommendations: capabilities (SR-025 a), SR-033 (a), SEC-114 A, per-project catalogue, SEC-111 A, UX-106 A, UX-126 A;
  - (b) as (a), with your own SEC-111 hold time and exclusion cap;
  - (c) as (a), but a five-step role ladder (SR-025 b) and Flag below `block` needs an override permission (UX-106 B).
- **Recommendation:** (a).
- **Assumed:** none.
- **Blocked:** APPLY1 for `project_grants`, CLI `project share`, bioplatform-models Role, checking §5 decisions, checking §7 and §11.3, api §6 agent rules, the MCP tool catalogue, admin §1 Content → Workflows; the Review sticky bar and EnvAccess board (later apply).
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended, for the versions that bring roles and gates. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #20 · Admin rights, sign-in administration and new users

- **Covers:** [SR-020](../reviews/R1-consistency.md#sr-020-major-the-system-admin-flag-protected-groups-and-pi-fields-are-missing-from-the-schema), [SR-021](../reviews/R1-consistency.md#sr-021-major-launcher-instances-and-environments-are-two-models-of-the-same-cluster), [SEC-127](../reviews/R5-security.md#sec-127-minor-admins-can-sign-in-as-any-user-without-that-being-recorded-and-sensitive-admin-actions-have-no-step-up), [UX-202](../reviews/R7-ui.md#ux-202-major-administration-settings-sign-in-active-sessions-and-sign-out-have-no-board-and-no-endpoint), [UX-240](../reviews/R7-ui.md#ux-240-minor-creating-a-user-shows-a-plaintext-password-instead-of-offering-a-sign-in-link).
- **Context:**
  - SR-020: `users.is_admin` is the only source of admin rights; the `admin` group is mirrored for depictio; single-user mode sets `is_admin` and creates the protected groups.
  - SR-021: an Environment is the launcher's instance; scoped plugin instances are added by their owner or a group admin.
  - SEC-127: admin-minted sign-in links only in demo mode or when enabled, sessions carry `act=<admin>`; step-up re-authentication (≤ 5 min) for backups, restore, keys and admin tokens; hash-chained audit rows.
  - UX-202: logout endpoint, session list and revoke, "sign out everywhere", sign-in method tests, an AdminSignIn board. Is OIDC in 0.1? (Profile says "phase 2", auth §0 has no phasing.)
  - UX-240: new users get a single-use sign-in link that forces a new password by default, not a plaintext initial password.
- **Options:**
  - (a) all recommendations: SR-020 (a), SR-021 (a), SEC-127 A, UX-202 (a) with OIDC in 0.1, UX-240 (a);
  - (b) as (a), but OIDC moves to phase 2 with a phase column in auth §0 (UX-202 b), matching SR-007's cut in #16;
  - (c) as (a), but keep admin sign-in links unrestricted and only record `act=<admin>` (SEC-127 B).
- **Recommendation:** (b). R7 recommended (a), but SR-007's recommended cut in #16 puts OIDC in the alpha; (b) keeps the two answers consistent. Pick (a) if you put OIDC in 0.1 in #16.
- **Assumed:** none.
- **Blocked:** APPLY1 for the users/groups schema, environments and plugin-instance API, auth §0/§2, admin §3.4 audit log, the logout and session endpoints (api §5, admin §5); the AdminSignIn, Profile and SettingsUsers boards.
- **Answer (Thomas, 2026-10-27, dashboard):** (b), as recommended: OIDC in a later phase, with a phase column in auth §0. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #21 · How Spectio trusts depictio identities

- **Covers:** [SEC-120](../reviews/R5-security.md#sec-120-major-depictio-jwt-trust-accepts-tokens-spectio-cannot-audience-check-or-revoke-and-maps-depictio-admin-to-spectio-admin), [DL-102](../reviews/R8-depictio.md#dl-102-major-trusting-depictio-jwts-no-iss-aud-or-email-claims-revocation-lives-only-in-depictios-database-and-there-is-no-browser-hand-over), [DEP-T-015](../reviews/R8b-depictio-tooling.md#dep-t-015-major-how-spectio-gets-depictios-jwt-public-key-on-kubernetes-is-undefined), [SEC-113](../reviews/R5-security.md#sec-113-major-identities-are-linked-by-email-across-idps-and-group-sync-is-not-namespaced-or-kept-away-from-protected-groups).
- **Context:**
  - SEC-120, DL-102, DEP-T-015: accept depictio tokens only at an exchange endpoint, verified online through `GET /auth/me` (cache ≤ 60 s, field whitelist), never with the public key alone and never by mounting depictio's keys volume on Kubernetes; do not mirror depictio's `is_admin` unless `depictio.trust_admin=true`. Before SSO, "one login for both" then exists only in the CLI (`--with-depictio`).
  - SEC-113: link identities only by (provider, subject); email linking only for `trusted_email` providers (depictio never); synced groups namespaced per provider; `admin` and `users` never synced. This changes the depictio "same email, one login" parity.
- **Options:**
  - (a) introspection-only trust, no admin mirroring by default, SEC-113 A; asking depictio for `aud`, JWKS and token exchange is decided in #27;
  - (b) keep public-key verification with a revocation check, and design a browser hand-over (DL-102 b);
  - (c) keep email linking for depictio co-hosting but namespace groups (SEC-113 B), the rest as (a).
- **Recommendation:** (a).
- **Assumed:** none.
- **Blocked:** APPLY1 for auth §1/§2 (depictio trust, linking, group sync), api §13.1/§13.2, auth §6 test row, cli §2 `--with-depictio`, architecture §7.5 Helm co-hosting (phase 2); spike depictio-introspection.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #22 · depictio hand-off: credentials and storage

- **Covers:** [FC-003](../reviews/R2-open-validations.md#fc-003-major-depictio-cli-ingest-user-needs-depictios-instance-provisioning-key-not-a-short-lived-credential), [DL-101](../reviews/R8-depictio.md#dl-101-blocker-runner-side-depictio-cli-ingest-needs-two-instance-wide-secrets-that-131-forbids-on-runners) (blocker), [DEP-T-014](../reviews/R8b-depictio-tooling.md#dep-t-014-major-sharing-depictios-seaweedfs-needs-per-bucket-identities-that-depictios-compose-does-not-configure), [DL-105](../reviews/R8-depictio.md#dl-105-major-run_tag-spectio-run-id-cannot-be-set-and-attach-run-does-not-give-one-complete-run-per-spectio-run), [DL-115](../reviews/R8-depictio.md#dl-115-minor-same-seaweedfs-image-and-version-ties-spectios-storage-patches-to-depictios-bump-cadence), [DEP-T-017](../reviews/R8b-depictio-tooling.md#dep-t-017-major-depictio-is-not-pinned-anywhere-in-spectios-toolchain-or-ci).
- **Context:** runner-side `depictio-cli ingest` needs depictio's instance provisioning key and its S3 write secret, which api §13.1 forbids on runners. The hand-off is post-0.1.
  - FC-003 and DL-101: the server holds the provisioning key and passes only a per-user token (`DEPICTIO_CLI_TOKEN`), never `--user` or `--provisioning-key`; the S3 route follows spike depictio-handoff, an ingest relay next to depictio as fallback. DL-101 replaces FC-003's proposal and drops to major.
  - DEP-T-014 (assumed): Spectio's own bucket `spectio` with a bucket-scoped identity **[to be validated: weed mini identities]**, otherwise its own SeaweedFS; never depictio's root keys.
  - DL-105, DL-115, DEP-T-017 (assumed): one depictio project per Spectio run for QC dashboards; Spectio keeps its own SeaweedFS pin with depictio's as the floor (amends the 2026-10-25 log); `DEPICTIO_VERSION` pinned in `dev/versions.env`.
- **Options:**
  - (a) DL-101 (a) replacing FC-003, severity major, the depictio request handled in #27;
  - (b) an ingest relay host next to depictio from the start (DL-101 b);
  - (c) wait for depictio to accept ingestion without client S3 credentials (DL-101 c).
- **Recommendation:** (a).
- **Assumed:** DEP-T-014 (a) without the request to depictio, DL-105 (a), DL-115 (a), DEP-T-017 (a).
- **Blocked:** APPLY1 for api §13.3 step 1 and cli §2 hand-off text, the scope of spike depictio-handoff. Not 0.1.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #23 · Co-hosting with depictio and browser hardening

- **Covers:** [SEC-109](../reviews/R5-security.md#sec-109-major-co-hosting-on-one-origin-merges-depictios-and-spectios-trust-the-reports-separate-origin-is-undefined), [DL-103](../reviews/R8-depictio.md#dl-103-major-a-depictio-dashboard-can-be-embedded-only-from-the-same-origin-a-filter-message-protocol-already-exists-in-another-shape), [SEC-126](../reviews/R5-security.md#sec-126-minor-browser-hardening-defaults-are-not-written-down).
- **Context:** path co-hosting on one domain merges the two trust domains. SEC-109 proposes separate hosts (`spectio.<site>`, `depictio.<site>`) with IdP SSO, a mandatory user-content origin for reports, no shared Redis without per-app ACL users, and explicit trusted proxies. DL-103 (assumed): a depictio dashboard can only be framed from the same origin, so the gate-time Dashboard tab exists only when co-hosted on depictio's origin and is a deep link otherwise. SEC-126 (assumed): CSP baseline, Trusted Types, sanitised Markdown, no analytics on admin and gate pages; `__Host-` cookies wait for this answer.
- **Options:**
  - (a) separate hosts by default (SEC-109 A);
  - (b) path co-hosting kept, documented as one trust domain, CSP and Trusted Types required in both apps;
  - (c) (a) by default, (b) as a documented opt-in.
- **Recommendation:** (c). It affects the depictio team (shared cookie, SSO, shared Redis).
- **Assumed:** DL-103 (a) and SEC-126 A proceed; the co-hosting default is not assumed.
- **Blocked:** APPLY1 for api §13.4, architecture §8 Redis sharing, the report sandbox origin, the SEC-126 `__Host-` cookie, DEP-T-013; the RunOutputs sandbox rules (UX-115).
- **Answer (Thomas, 2026-10-27, dashboard):** (c), as recommended: separate hosts by default, path co-hosting as a documented opt-in. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #24 · Backup and restore under live runs

- **Covers:** [SR-030](../reviews/R1-consistency.md#sr-030-major-a-restore-rewinds-the-database-under-runs-still-executing-token-handling-is-contradictory), [SEC-119](../reviews/R5-security.md#sec-119-major-backups-put-signing-and-secret-store-keys-in-an-archive-whose-encryption-is-optional-and-restore-accepts-uploaded-archives), [CH-021](../reviews/R4-constraints.md#ch-021-major-restore-failure-modes-while-runs-and-engines-are-still-live), [CH-022](../reviews/R4-constraints.md#ch-022-major-logical-json-lines-backups-do-not-scale-need-one-snapshot-and-have-no-rpo-or-rto), [SR-050](../reviews/R1-consistency.md#sr-050-minor-the-backup-and-restore-contract-differs-between-the-cli-and-admin-specs).
- **Context:**
  - SR-030: keep `tokens`, `sessions` and `runners` on restore and revoke orphans; runs launched after the backup are adopted as "orphaned after restore" (or cancelled by default?).
  - SEC-119: keys and sealed secrets always encrypted to an off-instance age recipient; remote backups without a recipient refused; signed manifests; foreign archives need explicit key trust; fresh re-auth for download and restore. This reverses the 2026-10-25 "optional encryption" decision.
  - CH-021, CH-022, SR-050 (assumed): restore into a new database then switch atomically, 503 on ingest during restore, runner inventory after; native backups by default (JSON Lines for migration and export only, departs from the 2026-10-25 decision); Ed25519 manifest signature, no partial restore by table.
- **Options:**
  - (a) SR-030 (a) and SEC-119 A;
  - (b) SR-030 (b) (cancel unknown runs by default) and SEC-119 A;
  - (c) SR-030 (a) and SEC-119 B (encryption optional for local destinations).
- **Recommendation:** (a).
- **Assumed:** CH-021 A, CH-022 A, SR-050 (a) proceed.
- **Blocked:** APPLY1 for the admin §4.3 restore wizard and encryption rules, cli §2 backup example, ingest 409 behaviour.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #25 · Trust boundaries: plugins, outbound calls, event bridges, runner policy, restricted data

- **Covers:** [SEC-124](../reviews/R5-security.md#sec-124-major-plugins-run-in-process-with-full-trust-plugins-never-touch-the-database-is-a-convention-not-a-boundary), [SEC-118](../reviews/R5-security.md#sec-118-major-outbound-http-from-webhooks-plugins-wes-and-imports-has-no-ssrf-policy), [SEC-116](../reviews/R5-security.md#sec-116-major-event-bridges-hand-authentication-to-broker-acls-share-one-principal-across-all-devices-and-send-every-project-to-one-topic), [SEC-115](../reviews/R5-security.md#sec-115-major-a-server-compromise-is-code-execution-on-every-runners-unix-account-runners-hold-no-local-policy), [SEC-105](../reviews/R5-security.md#sec-105-major-runner-file-access-is-not-confined-event-paths-globs-and-symlinks-can-make-the-runner-read-any-file-of-its-unix-user), [SEC-110](../reviews/R5-security.md#sec-110-major-ro-crate-project-and-workflow-imports-are-unvalidated-paths-for-code-paths-and-forged-history), [UX-117](../reviews/R12-ui-scenarios.md#ux-117-major-listing-files-through-the-runner) (R12), [UX-123](../reviews/R12-ui-scenarios.md#ux-123-minor-overlays-versions-and-the-catalogue) (R12), [UX-129](../reviews/R12-ui-scenarios.md#ux-129-major-gates-on-clinical-data) (R12).
- **Context:** security posture defaults, one per finding.
  - SEC-124: installed server plugins are as trusted as admins (reword architecture §10 risk 2, which contradicts the 2026-10-25 "no DB session so tenancy stays enforced"); refuse `SPECTIO_EXTRA_PLUGINS` in production unless allowed; pin distribution, version and wheel hash.
  - SEC-118: one egress policy for server-side HTTP; loopback, link-local, RFC 1918 and ULA denied unless allow-listed (LabID pre-filled at install).
  - SEC-116: event bridges signals-only inbound by default, per-device credentials, ±5 min replay window, outbound opt-in per project, per-project Kafka topics.
  - SEC-115: runners enforce a local `runner.toml` (sources, roots, `script:` bindings off by default, resource caps, TLS pinning).
  - UX-123 (R12): scope of a Git credential and whether the server or a runner clones, sent to the security review (SEC-103).
  - UX-129 (R12): a "restricted data" project policy (pseudonyms only, downloads off, per-view audit, agents off).
  - SEC-105, SEC-110, UX-117 (assumed): runner reads confined to per-run roots; imports treated as untrusted; `list_dir` confined to storage roots.
- **Options:**
  - (a) all recommendations: SEC-124 A, SEC-118 A with a pre-filled allow-list, SEC-116 A, SEC-115 A, UX-123 A, UX-129 A;
  - (b) as (a), but private ranges allowed by default on `local` and `single` instances (SEC-118 B);
  - (c) as (a), but `runner.toml` optional and everything allowed when absent (SEC-115 B).
- **Recommendation:** (a).
- **Assumed:** SEC-105 A, SEC-110 A, UX-117 A proceed.
- **Blocked:** APPLY1 for architecture §3, §3.4 (`ctx.http`), §7.6 and §10, admin §2.3, schedulers §6 and jobcomp/kafka handling, checking §7 `script:` binding, the webhook and WES facade specs; the Workflow boards and ReviewTrio (later apply).
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. Spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #26 · Licences, repository governance and CI costs

- **Covers:** [FC-028](../reviews/R2-open-validations.md#fc-028-minor-megatest-outputs-come-from-full-size-public-data-not-from-nf-coretest-datasets) and [FC-037](../reviews/R2-open-validations.md#fc-037-minor-table-corrections-with-no-finding-of-their-own-batch) item 6, [CH-034](../reviews/R4-constraints.md#ch-034-minor-licences-of-server-dependencies-scheduler-integrations-and-copied-code-are-not-tracked), [DEP-T-002](../reviews/R8b-depictio-tooling.md#dep-t-002-blocker-release-please-with-github_token-cannot-trigger-release-builds-or-run-checks-on-its-own-pr), [DEP-T-008](../reviews/R8b-depictio-tooling.md#dep-t-008-major-never-auto-merged-paths-are-a-convention-not-an-enforced-rule), [DEP-T-018](../reviews/R8b-depictio-tooling.md#dep-t-018-major-no-python-or-osarchitecture-matrix-for-the-base-install-and-the-runner), [DEP-T-029](../reviews/R8b-depictio-tooling.md#dep-t-029-minor-metrics-is-a-line-not-a-contract), [DEP-T-001](../reviews/R8b-depictio-tooling.md#dep-t-001-blocker-path-filtered-workflows-used-as-required-checks-block-every-pr-they-skip), [DEP-T-005](../reviews/R8b-depictio-tooling.md#dep-t-005-major-supply-chain-evidence-sbom-provenance-signatures-scanning-is-deferred-to-phase-3), [UX-219](../reviews/R7-ui.md#ux-219-major-custom-switches-checkboxes-tabs-radios-and-sliders-cannot-be-reached-by-keyboard).
- **Context:**
  - FC-028 / FC-037: megatest outputs come from full-size public data (SRA under s3://ngi-igenomes, AWS iGenomes), not from nf-core/test-datasets (MIT); IDR idr0033, idr0062, idr0066 and idr0076 are CC BY 4.0, idr0001, idr0054 and idr0073 still to be validated.
  - CH-034: licence allow-list scan, `THIRD_PARTY_NOTICES` in wheel and image, psycopg (LGPL) as an optional extra or asyncpg, never bundle Redis 8, never link pyslurm (GPL), record depictio's licence for copied code.
  - DEP-T-002: release PRs never auto-merged (Thomas merges, publishing is irreversible) or 0.x auto-merge once `AUTOMERGE_MAIN=true`? The GitHub App token part is assumed; release-please stays off until the App exists (#8).
  - DEP-T-008: `.github/CODEOWNERS` with required code-owner review on `main` and `autopilot/integration` for `.github/**`, `.claude/**`, `pipeline.yaml`, auth and secrets code. Whether a bot approval counts when the same identity opens the PR is **[to be validated]**.
  - DEP-T-018: macOS-arm64 in CI costs 10× minutes on a private repository **[to be validated]**; Linux grid assumed.
  - DEP-T-029: who may scrape `/metrics` (scrape token by default, separate unauthenticated port opt-in)?
  - DEP-T-001, DEP-T-005, UX-219 (assumed): one `ci-ok` required check; SBOM, provenance and signing from the first image; keyboard rules added to the board conventions in CLAUDE.md.
- **Options:**
  - (a) all recommendations: licence statements as corrected with per-source terms **[to be validated]**; CH-034 A; release PRs never auto-merged; CODEOWNERS on both branches; macOS later; scrape token;
  - (b) as (a), plus no megatest-derived media until each source's terms are checked (FC-028 B), and asyncpg instead of psycopg (CH-034 B);
  - (c) as (a), but 0.x release PRs auto-merge (DEP-T-002 b) and CODEOWNERS on `main` only (DEP-T-008 b).
- **Recommendation:** (a).
- **Assumed:** DEP-T-001 (a), DEP-T-002 docs part, DEP-T-005 (a), DEP-T-018 Linux part, DEP-T-029 docs part, UX-219 (a). The CLAUDE.md edit for UX-219 is only made once you confirm.
- **Blocked:** APPLY1 for dev-env §10.3/§10.4, architecture §7.4, schedulers §5, depictio-ecosystem-reuse §1, the release-PR rule in autopilot.md §8 and documentation-system §8, the branch-protection payload (#8), admin §3.5 metrics access; RELEASE_PLEASE_ENABLED and 0.1.0; spike 8 licence scan.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended. The UX-219 keyboard rule is added to the board conventions in `CLAUDE.md`; the other spec edits in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #27 · Messages to other teams (nothing is sent without you)

- **Covers:** [DL-113](../reviews/R8-depictio.md#dl-113-minor-get-authme-returns-the-full-user-model-password-hash-included-inference-not-executed), [FC-042](../reviews/R9-landscape.md#fc-042-major-the-snakemake-monitoring-landscape-has-moved-logger-plugins-an-active-panoptes-and-flowo), [SR-036](../reviews/R1-consistency.md#sr-036-major-the-checks_as-preset-shape-requested-from-depictio-does-not-match-spectios-check-syntax), [SEC-107](../reviews/R5-security.md#sec-107-major-secrets-can-reach-parameters-logs-the-task-ledger-audit-diffs-and-ro-crate-exports).
- **Context:** the doc changes are assumed; only the outreach waits.
  - To depictio, privately: `GET /auth/me` probably returns the password hash (DL-113, an inference not yet executed). Then the request list (18 items), as one tracking issue or one per request; it includes the `checks_as` shape (SR-036), run-scoped short-lived tokens (FC-003), an identities file for SeaweedFS (DEP-T-014), `aud` / JWKS / token exchange (SEC-120, DL-102, DEP-T-015) and framing headers (DL-103).
  - To the FlowO maintainers (logger-event conventions) and an upstream Snakemake docs PR for the stale `--wms-monitor` page (FC-042).
  - Registering the `spk_` prefix with GitHub secret scanning (SEC-107 B) **[partner programme terms to be validated]**.
- **Options:**
  - (a) confirm DL-113 in spike depictio-introspection first, then report privately and file one tracking issue; FlowO, Snakemake and GitHub outreach at the public beta;
  - (b) report DL-113 now, and file one issue per request;
  - (c) no outreach before the public beta.
- **Recommendation:** (a).
- **Assumed:** the doc parts of DL-113 (api §13.1 whitelist), FC-042 (synthesis §2 and the comparison page), SR-036 (keys in checking §4/§7) and SEC-107 (one redaction function in admin §3.4).
- **Blocked:** only the messages themselves; no spec section waits.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended: confirm DL-113 in spike depictio-introspection first, then report privately; other outreach at the public beta. Nothing is sent without Thomas. *Decided.*

### #28 · Assumed: engine bridges, runner and scheduler

- **Covers:** [SR-003](../reviews/R1-consistency.md#sr-003-blocker-check-providers-run-on-the-server-in-three-specs-on-the-runner-in-three-others), [SR-006](../reviews/R1-consistency.md#sr-006-major-the-cli-command-tree-lacks-commands-that-other-specs-cite), [SR-008](../reviews/R1-consistency.md#sr-008-major-how-spectio-drives-snakemake-python-api-worker-or-command-line-head-job), [SR-017](../reviews/R1-consistency.md#sr-017-major-engine-bridge-behaviour-when-the-server-is-unreachable-tower-era-text-and-no-testable-bound), [SR-022](../reviews/R1-consistency.md#sr-022-major-no-compatibility-window-between-cli-runners-engine-bridges-plugins-and-server), [SR-035](../reviews/R1-consistency.md#sr-035-major-push-transport-needs-an-inbound-kafka-consumer-the-architecture-does-not-have), [SR-047](../reviews/R1-consistency.md#sr-047-minor-fixture-workflows-and-step-numbers-in-dev-env-disagree-with-the-playbook-and-with-101), [SR-048](../reviews/R1-consistency.md#sr-048-minor-untestable-thresholds-head-silent-and-the-10000-file-watch-limit), [FC-001](../reviews/R2-open-validations.md#fc-001-major-snakemake-drains-on-sigterm-sigint-and-a-plain-scancel-lose-running-work), [FC-038](../reviews/R9-landscape.md#fc-038-major-a-snakemake-ro-crate-exporter-exists-the-synthesis-says-none-was-found), [FC-040](../reviews/R9-landscape.md#fc-040-major-spectio-cannot-pin-snakemake-a-supported-version-range-and-a-contract-test-are-needed), [FC-052](../reviews/R9-landscape.md#fc-052-minor-prefect-makes-the-same-choice-hides-that-prefect-keeps-one-migration-tree-per-dialect), [CH-001](../reviews/R4-constraints.md#ch-001-blocker-the-recommended-head-job-puts-the-engine-and-its-event-bridge-on-a-compute-node-where-outbound-network-is-often-blocked), [CH-002](../reviews/R4-constraints.md#ch-002-major-no-compatibility-window-for-the-ingest-and-runner-protocols-across-bridge-runner-and-server-versions), [CH-003](../reviews/R4-constraints.md#ch-003-major-continue-or-relaunch-can-start-while-the-previous-head-is-still-finishing), [CH-005](../reviews/R4-constraints.md#ch-005-major-no-traffic-budget-for-the-engine-bridges-batching-back-pressure-and-spool-limits), [CH-006](../reviews/R4-constraints.md#ch-006-major-nf-spectio-failure-semantics-are-unspecified-and-a-break-in-the-beta-interface-would-be-silent), [CH-008](../reviews/R4-constraints.md#ch-008-major-sse-fan-out-no-coalescing-a-6-connection-limit-per-browser-the-full-task-stream-to-every-tab), [CH-009](../reviews/R4-constraints.md#ch-009-major-snakemake-the-logger-interface-keeps-moving-only-snakemake-9-works-and-snakemakeapi-cannot-run-from-the-runners-environment), [CH-011](../reviews/R4-constraints.md#ch-011-major-the-event-log-grows-without-bound-and-raw-nextflow-trace-records-carry-script-and-env), [CH-012](../reviews/R4-constraints.md#ch-012-major-projection-in-the-ingest-transaction-in-one-process-and-one-event-loop-stalls-the-ui-and-sse-during-bursts), [CH-016](../reviews/R4-constraints.md#ch-016-major-stopping-at-a-gate-through-extwhen-is-proven-only-on-synthetic-pipelines), [CH-025](../reviews/R4-constraints.md#ch-025-major-apptainer-the-usual-hpc-container-runtime-is-untested-the-whole-matrix-uses-docker), [CH-027](../reviews/R4-constraints.md#ch-027-major-squeue-and-sacct-json-are-heavy-and-their-schema-changes-with-each-slurm-version-on-the-cli-path-too).
- **Context:** all reversible and docs-only, so they proceed. The ones that revise a logged decision are marked †.
  - Process model: check binding on the runner, verdict on the server (SR-003); Snakemake as a CLI head job in a per-workflow environment, Snakemake ≥ 9.0, logger interface 1.x and 2.x (SR-008, CH-009, FC-040) †"no Python subprocess"; SIGTERM drain and `scancel --signal=TERM --full` (FC-001); setup by `spectio login`, no wrapper (SR-006).
  - Bridges: spool in the launch directory forwarded by the runner, prep on the login node, `NXF_OFFLINE=true` (CH-001); hooks ≤ 50 ms, buffer ≥ 24 h / 200 MB, never fail a run (SR-017), with CH-005's batching aligned to that cap; Nextflow ≥ 25.04 floor and enqueue-only hooks (CH-006); separate ingest version (CH-002); 60 s heartbeat, head silent after 5 min (SR-048).
  - Server: append-and-ack ingest with one projector (CH-012) †synthesis §4; raw payloads archived after terminal (CH-011) †synthesis §2ter; coalesced SSE deltas (CH-008); launches table and runner mutex for Continue (CH-003).
  - Scheduler and tests: text-format `squeue` poll, pinned JSON parser for details (CH-027) †2026-10-25 log; Kafka as a runner observer transport (SR-035); Apptainer in the nightly matrix (CH-025); gate stop on nf-core in T1/T2 (CH-016); synthetic pipelines as fixtures (SR-047); CLI and runners match the server minor before 1.0 (SR-022); RO-Crate plugin as optional input (FC-038); one Alembic tree (FC-052).
- **Options:**
  - (a) confirm all;
  - (b) confirm all except the IDs you name;
  - (c) revisit the bridge numbers after T2 measurements (SR-017 b, CH-005 C).
- **Recommendation:** (a). The EMBL egress probe (CH-001 round question 4) needs EMBL IT and is not assumed.
- **Assumed:** each finding's recommended option, as listed.
- **Blocked:** nothing; a different answer reverts the assumed spec text.

### #29 · Assumed: data model, API vocabulary and spec owners

- **Covers:** [SR-004](../reviews/R1-consistency.md#sr-004-blocker-spectioyml-has-four-shapes-and-no-owner-of-its-schema), [SR-005](../reviews/R1-consistency.md#sr-005-blocker-tasks-names-two-different-tables-id-spaces-and-endpoint-families), [SR-012](../reviews/R1-consistency.md#sr-012-major-gate-decisions-five-verb-sets-two-resource-names-stale-mcp-tools-and-scopes), [SR-013](../reviews/R1-consistency.md#sr-013-major-endpoint-catalogues-duplicated-between-api-5-and-admin-5-three-public-config-endpoints), [SR-015](../reviews/R1-consistency.md#sr-015-major-background-task-ledger-and-schedules-two-schemas-two-locking-designs-no-jobs-object), [SR-016](../reviews/R1-consistency.md#sr-016-major-run-and-gate-states-five-vocabularies-no-enum-a-2-of-11-wes-mapping), [SR-026](../reviews/R1-consistency.md#sr-026-major-webhooks-are-both-a-project-table-and-a-notifier-plugin-instance), [SR-032](../reviews/R1-consistency.md#sr-032-major-built-in-plugins-are-separate-distributions-yet-one-uv-tool-install-spectio-is-said-to-be-enough), [SR-034](../reviews/R1-consistency.md#sr-034-major-schedulers-8-defines-tables-events-and-endpoints-the-api-spec-does-not-have), [SR-041](../reviews/R1-consistency.md#sr-041-minor-run-and-review-screens-are-specified-outside-ui-spec-two-cross-references-are-broken), [SR-042](../reviews/R1-consistency.md#sr-042-minor-the-built-in-ai-assistant-has-ui-and-a-runner-command-but-no-api-data-model-or-cli-entry), [SR-046](../reviews/R1-consistency.md#sr-046-minor-pipeline-identifier-and-workflow-version-key-vs-no-column), [SR-052](../reviews/R1-consistency.md#sr-052-minor-check-result-vocabulary-state-vs-verdict-and-how-severity-maps-to-them), [SR-053](../reviews/R1-consistency.md#sr-053-minor-ui-spec-contradicts-the-logged-shell-and-list-decisions-without-a-new-log-entry), [FC-025](../reviews/R2-open-validations.md#fc-025-minor-mantine-7-is-two-majors-behind-and-the-import-map-makes-the-major-part-of-the-plugin-contract).
- **Context:** all reversible and docs-only.
  - Schema: checking §12 owns `spectio.yml`, `stages[].gate` (SR-004); engine tasks keep `tasks`, the ledger becomes `background_tasks` (SR-005); admin §3.1 owns ledger columns, schedule locking by unique insert (SR-015); webhooks as a project table (SR-026); scheduler contracts move to api (SR-034); `<org>/<name>/<version>` identifiers (SR-046); check outcome and severity stored apart, event `spectio.check.evaluated` (SR-052).
  - Vocabulary: `approve | apply | go_back | stop`, `gates:decide` (SR-012); run and gate enums of api §7.1 (SR-016); `/api/v1/admin/*` for system admins only (SR-013).
  - Packaging and UI: built-ins as modules of one wheel, `spectio[server]` (SR-032); Mantine 7 aligned with depictio (FC-025); assistant endpoints specified, stage per #16 (SR-042); run and review tabs in ui-spec (SR-041); a log entry ratifying the full-width top bar (SR-053) †revises the logged shell.
- **Options:**
  - (a) confirm all;
  - (b) confirm all except the IDs you name.
- **Recommendation:** (a).
- **Assumed:** each finding's recommended option, as listed.
- **Blocked:** nothing; a different answer reverts the assumed spec text.

### #30 · Assumed: UI boards, review screens and the documentation system

- **Covers:** [UX-207](../reviews/R7-ui.md#ux-207-major-headline-counts-breakdowns-and-the-activity-feed-cannot-be-served-by-the-list-api), [UX-209](../reviews/R7-ui.md#ux-209-major-envstorage-cannot-be-fed-no-api-or-table-for-locations-lifecycle-rules-or-work-directory-actions), [UX-216](../reviews/R7-ui.md#ux-216-major-the-launch-flow-is-drawn-two-ways-launch-has-no-project-picker-and-boards-disagree-on-gates), [UX-226](../reviews/R7-ui.md#ux-226-minor-branding-lets-admins-recolour-status-colours-with-no-rule-linking-them-to-run-states), [UX-234](../reviews/R7-ui.md#ux-234-minor-phone-pinned-bars-content-shows-through-chips-are-clipped-next-stays-enabled-with-an-open-issue), [UX-105](../reviews/R12-ui-scenarios.md#ux-105-major-sub-items-and-a-sixth-view-items-sub-regions) (R12), [UX-108](../reviews/R12-ui-scenarios.md#ux-108-major-decisions-that-the-pipeline-cannot-read) (R12), [UX-109](../reviews/R12-ui-scenarios.md#ux-109-major-which-stages-a-parameter-change-reruns-and-at-what-cost) (R12), [UX-110](../reviews/R12-ui-scenarios.md#ux-110-major-gates-that-wait-for-a-signal) (R12), [UX-112](../reviews/R12-ui-scenarios.md#ux-112-minor-adding-a-gate-at-launch) (R12), [UX-113](../reviews/R12-ui-scenarios.md#ux-113-major-relaunch-with-resource-changes-and-a-dry-run-estimate) (R12), [UX-125](../reviews/R12-ui-scenarios.md#ux-125-minor-software-inventory-and-pre-pulled-images) (R12), [UX-128](../reviews/R12-ui-scenarios.md#ux-128-major-thumbnails-crops-and-the-viewer-contract) (R12), [DOC-001](../reviews/R11-docs.md#doc-001-major-two-owners-describe-two-different-public-landing-pages), [DOC-003](../reviews/R11-docs.md#doc-003-major-review-approve-is-self-declared-and-leaves-no-record), [DOC-004](../reviews/R11-docs.md#doc-004-major-w0-progress-pages-cite-commits-outside-the-branch-history), [DOC-005](../reviews/R11-docs.md#doc-005-major-dark-theme-shows-light-only-screens-on-the-landing), [DOC-007](../reviews/R11-docs.md#doc-007-minor-documentation-systemmd-specifies-tools-and-settings-that-do-not-exist).
- **Context:** all reversible and docs-only.
  - R7 boards: summary endpoints and Load more instead of numbered pages (UX-207); EnvStorage endpoints and `workdir_usage` (UX-209); Launch as one page with a progress stepper (UX-216); brand status colours for alerts only (UX-226); Next disabled with its reason on MLaunch (UX-234).
  - R12 review screens: a sixth "matrix" view with `children` (UX-105); filter artifacts targeting a declared parameter (UX-108); "Apply and rerun from stage N" with an estimated cost (UX-109); a signal-gate contract (UX-110); per-run gates when the overlay allows (UX-112); relaunch overrides and `dry_run` (UX-113); a read-only software inventory (UX-125); an OME-Zarr viewer contract (UX-128).
  - Docs: documentation-system §2 owns the landing, Landing.dc.html kept as a post-0.1 draft (DOC-001; its WES item follows #17); verdicts recorded as `review_score` with 15 pages grandfathered (DOC-003); W0 pages note the squash into 9185808 without linking the old branch (DOC-004, independent of #5); dark-mode screenshots dimmed by CSS for now (DOC-005); documentation-system §1/§3 aligned to the real tools (DOC-007).
- **Options:**
  - (a) confirm all;
  - (b) confirm all except the IDs you name.
- **Recommendation:** (a).
- **Assumed:** each finding's recommended option, as listed.
- **Blocked:** nothing; a different answer reverts the assumed spec text and boards.

### #31 · Autopilot budget: a fresh reading before APPLY1

- **Context.**
  - The run was started with `/autopilot --until W2 --budget 15%w --now 50`.
  - In this cloud session the status line does not feed `.autopilot/usage.json`, so the governor cannot measure use: it stays on the manual reading (50 %, "manual-stale"), counts 0 points and always answers `go` (journal, tick 1). This settles the [to be validated] item in `autopilot.md` §6: the status line does not run in cloud sessions.
  - W1 and TRIAGE1 used about 8.5 M subagent tokens, which cannot be converted into weekly-window points here.
  - APPLY1 is the heaviest step so far: it edits specs from 163 accepted and 88 assumed findings.
- **Options:**
  - (a) read `/usage` and restart with the new reading: `/autopilot --until W2 --budget 15%w --now <pct>`;
  - (b) give a five-hour budget instead (`--budget 40%5h --now <pct>`), so a limit hit pauses rather than stops;
  - (c) stop the autopilot here and run APPLY1 interactively.
- **Recommendation:** (a), after answering at least #16 (MVP cut), #11 and #12. Those carry blockers that APPLY1 must otherwise leave untouched.
- **Assumed:** none. The autopilot stopped before APPLY1 (journal, tick 2).
- **Blocked:** APPLY1, then R3, R6, TRIAGE2 and APPLY2.
- **Reading (Thomas, 2026-10-27):** 57 %, so 7 of the 15 points are spent; the autopilot continues APPLY1 with an 8-point budget.

## TRIAGE2 (2026-10-27)

**Step page:** [TRIAGE2](../progress/W2/TRIAGE2.md)

- **Triaged:** 61 findings from [R3](R3-journeys.md) (journeys, 27) and [R6](R6-contract.md) (API contract, 34). 21 accepted, 0 rejected, 40 sent here.
- **Assumed:** 33 of the 40 already proceed on the recommended option, marked `assumed — pending Thomas`. The other 7 wait for your answer: SR-054, SR-056, SR-057, SR-058, SR-067 (R3), SR-080 and SR-091 (R6).
- **How to answer:** #32 to #37 hold one question each, in the order of the R3 and R6 "Questions for Thomas" sections. #34, #36 and #37 are reserved (scope, auth, security posture), so nothing is assumed there. #38, #39 and #40 only list assumptions to confirm. One `Answer:` line per entry is enough.

APPLY2 applies the accepted and assumed findings of R3 and R6 and leaves the sections named under **Blocked** untouched until you answer.

### #32 · Relaunch at a failed gate, Resume after a failure, and the 0.0.1 gate verbs

- **Covers:** [SR-062](../reviews/R3-journeys.md#sr-062-blocker-relaunch-with-changed-parameters-from-a-failed-gate-is-two-incompatible-flows-and-neither-is-drawn), [CH-042](../reviews/R3-journeys.md#ch-042-blocker-run-state-machine-failed-is-terminal-yet-resumable-and-launch-outcomes-are-mapped-onto-the-run-state), [SR-063](../reviews/R3-journeys.md#sr-063-major-the-post-runsidrelaunch-contract-is-undefined), [UX-243](../reviews/R3-journeys.md#ux-243-major-relaunch-with-changed-parameters-has-no-parameter-editor-and-no-snakemake-variant), [SR-081](../reviews/R6-contract.md#sr-081-major-run-actions-and-relaunch-source-states-responses-the-dialogs-three-meanings-of-resume-lineage-and-a-fourth-mode-vocabulary), [SR-085](../reviews/R6-contract.md#sr-085-major-the-001-gate-no-run-filter-untyped-check-values-without-thresholds-unclear-if-match-no-response-body-label-only-actor-kinds-verbs-still-split), [UX-280](../reviews/R6-contract.md#ux-280-major-relaunch-overrides-are-parameters-only-the-dialogs-main-example-is-a-process-resource-override-extra-config), [UX-281](../reviews/R6-contract.md#ux-281-major-the-relaunch-preview-reused-to-run-per-stage-estimate-suggested-mode-suggestions-pre-flight-has-no-operation), [UX-282](../reviews/R6-contract.md#ux-282-major-lineage-and-compare-entries-lack-name-from-stage-actor-failure-summary-and-old-new-values), [UX-284](../reviews/R6-contract.md#ux-284-major-reviewreports-action-bar-maps-to-apply-change-set-outside-001-the-001-gate-actions-are-not-drawn)
- **Context:** R3 question 1 and R6 question 4. "Relaunch with changed parameters" from a gate is drawn as two incompatible flows, `failed` is both terminal and "resumable", `:relaunch` has no contract, and ReviewReport's action bar needs change sets that 0.0.1 does not have.
- **Options:**
  - (A) the same run continues: gate `apply` or `go_back` carries a parameter change set, and `failed` → `queued` is allowed, with a lattice per launch;
  - (B) a new child run: at a gate, "Relaunch…" records `stop` (reason `relaunched`) and calls `POST /runs/{id}:relaunch`; after a failure, Resume creates a child run that reuses the parent's launch directory; the parent stays terminal. The 0.0.1 gate verbs are `approve` and `stop`; `apply` and `go_back` return 422 `not-in-this-version`;
  - (C) B for failures, A for gates.
- **Recommendation:** (B). It keeps the run lattice intact, it is what journey 2's "compare the two runs" needs, and it reuses one verb.
- **Assumed:** (B), for all ten findings. The relaunch preview is the `dry_run` of the relaunch body, as already assumed for UX-113 in #30.
- **Blocked:** nothing; a different answer reverts the assumed text in api §5, §7, §7.1, synthesis §5ter and ui-spec §4.4–§4.6.
- **Note (2026-10-27, cut revised):** gates are no longer in 0.0.1 ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), so the 0.0.1 gate verbs (`approve`, `stop`) are moot for 0.0.1; all gate verbs are now "later (open)". The relaunch part still applies to 0.0.1: every relaunch, Resume after a failure included, is a new child run, and the parent stays terminal.
- **Answer (Thomas, 2026-10-27, dashboard):** "B, but to be discussed": Thomas is not sure that Nextflow or Snakemake create a new run when the same one resumes; to be checked. Spike T1 now records what each engine does on `-resume` and on a rerun in the same directory; the B text in the specs stays *assumed* until that check and the discussion. *Open (B leaning, T1 check).*

### #33 · When every check passes, does the gate wait for a person?

- **Covers:** [SR-059](../reviews/R3-journeys.md#sr-059-major-when-every-check-passes-does-the-planned-stop-open-a-gate-or-continue-automatically)
- **Context:** R3 question 2. checking §4 and §12.4 do not say whether a planned stop with all checks passing opens a gate.
- **Options:**
  - (a) the gate always waits for a person;
  - (b) Spectio continues by itself;
  - (c) a gate row is always created, and `decide.auto_approve: when_checks_pass` in the manifest turns on automatic approval, recorded as a decision by `service`.
- **Recommendation:** (c), with "wait for a person" as the 0.0.1 default, because journey 1 needs a gate to approve.
- **Assumed:** (c).
- **Blocked:** nothing.
- **Note (2026-10-27, cut revised):** gates and QC checks are no longer in 0.0.1 ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), so the "wait for a person" 0.0.1 default is moot; the question stays open for the version that brings gates.
- **Answer (Thomas, 2026-10-27, dashboard):** (c), as recommended, for the version that brings gates. *Decided.*

### #34 · 0.0.1 scope: how nf-core/rnaseq gets its stages and gate, workflow registration, MultiQC in the install

- **Covers:** [SR-057](../reviews/R3-journeys.md#sr-057-blocker-nf-corernaseq-cannot-be-registered-get-a-stage-and-get-a-gate-in-001-through-any-specified-path), [SR-056](../reviews/R3-journeys.md#sr-056-major-registering-a-workflow-is-outside-the-001-cut-and-its-contract-is-undefined), [SR-058](../reviews/R3-journeys.md#sr-058-blocker-at-gate-time-after-stage-1-multiqc-bindings-find-no-multiqc-data-and-001-installs-no-multiqc)
- **Context:** R3 questions 3 and 4. Reserved: they add or drop 0.0.1 features ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15.1). Today no specified path lets journey 1 register rnaseq, give it a stage and a gate, and evaluate a `multiqc:` binding after stage 1 with the documented `spectio[server]` install.
- **Options:**
  - (a) 0.0.1 ships one built-in rnaseq overlay, and the user may pass a `spectio.yml` at launch (`--gates FILE`, inline in `POST /runs`); YAML only, shown read-only in the UI; the install becomes `spectio[server,checks]`, and a missing value gets verdict `error`;
  - (b) the overlay editor UI and a workflow import form in 0.0.1;
  - (c) gates only from a `spectio.yml` in the workflow repository; MultiQC stays optional and missing values show `n/a`.
- **Recommendation:** (a).
- **Assumed:** none (reserved).
- **Blocked:** checking §12.7 (overlays), api §5 `POST /workflows` and the inline `gates` value of SR-087, architecture §7.3 extras, the install line in `mvp-0.0.1.md`.
- **Note (2026-10-27, cut revised):** gates and QC checks are no longer in 0.0.1 ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), so the overlay, the `--gates FILE` and the MultiQC install questions (SR-057, SR-058) no longer block 0.0.1. How a workflow is registered for launch from the UI (SR-056) still applies to 0.0.1.
- **Answer (Thomas, 2026-10-27, dashboard):** no gating in the MVP or 0.0.1, as in the revised cut. SR-056 (how a workflow is registered for launch from the UI) still applies to 0.0.1 and stays open. *Handled for gates; SR-056 open.*

### #35 · Engines and the in-process runner on a laptop

- **Covers:** [SR-055](../reviews/R3-journeys.md#sr-055-blocker-no-local-environment-runner-record-or-in-process-runner-interface-in-001), [CH-041](../reviews/R3-journeys.md#ch-041-blocker-in-process-runner-the-engine-heads-fate-on-server-stop-re-adoption-and-exit-code-are-unspecified), [SR-067](../reviews/R3-journeys.md#sr-067-major-engine-prerequisites-on-a-laptop-who-provides-java-and-nextflow-the-snakemake-environment-and-the-bridges)
- **Context:** R3 question 5 and 6 (b). 0.0.1 has no local environment record, no runner interface for the in-process case, and no rule for engine heads when `spectio serve` stops. Who installs Java, Nextflow and Snakemake, and how nf-spectio is delivered, are unstated.
- **Options:**
  - (a) one built-in local environment and runner record is the default `environment_id`; heads keep running detached when the server stops and are re-adopted at the next start; the user installs the engines (`spectio doctor` reports them); nf-spectio ships as a jar in the spectio wheel **[to be validated]**;
  - (b) as (a), but heads are stopped with the server;
  - (c) as (a), but nf-spectio comes from the Nextflow plugin registry.
- **Recommendation:** (a). A restart or upgrade should not fail a multi-hour run, and a pinned plugin works offline.
- **Assumed:** the local environment and runner record (SR-055) and detached heads (CH-041). Not assumed: who installs the engines and how nf-spectio ships (SR-067), because they change the 0.0.1 install and what Spectio publishes.
- **Blocked:** architecture §7.3 "0.0.1 prerequisites" (SR-067).
- **Note (2026-10-27, cut revised):** 0.0.1 heads are SLURM jobs submitted from the login node, adopted after a server restart by the head-job name match ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)). The detached local heads of SR-055 and CH-041 now concern only the local executor, kept for tests and development. SR-067 (who installs the engines and how nf-spectio ships) still applies, now on a login node.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended: the user installs the engines and `spectio doctor` reports them; nf-spectio ships as a jar in the wheel **[to be validated]**. Applied in architecture §7.3. *Decided.*

### #36 · The ingest contract for 0.0.1 (split inbox #11?)

- **Covers:** [SR-054](../reviews/R3-journeys.md#sr-054-blocker-001-needs-the-ingest-contract-but-the-log-parks-it-as-not-needed-for-001), [SR-080](../reviews/R6-contract.md#sr-080-major-ingest-14-the-wire-items-the-draft-had-to-invent-beyond-sr-054s-subset)
- **Context:** R3 question 6 (a). api §14 is cited but does not exist; the log parks it as "not needed for 0.0.1", yet both bridges must report driven runs to a local server. R6 SR-080 lists the wire items the draft had to invent (batch envelope, acknowledgement, heartbeat, engine event vocabulary). Same root as SR-001 (#11), which holds the ingest credential and is reserved (auth).
- **Options:**
  - (a) split #11: write the driven-run part of api §14 for 0.0.1 (envelope, run ID and launch number variables, ack, version header, no credential on loopback); only the observed-run credential stays deferred;
  - (b) keep #11 whole and write all of §14 once it is answered;
  - (c) no §14 in 0.0.1: the bridges call the public API.
- **Recommendation:** (a).
- **Assumed:** none (auth is reserved).
- **Blocked:** api §14 and the bridge-facing parts of architecture §13.
- **Note (2026-10-27, cut revised):** in 0.0.1 the plugins write only to the spool in the run directory, and the built-in runner reads it; nothing posts over the network ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)). The 0.0.1 part of the contract is therefore the spool's event format and its size caps; the question itself stays open.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended: #11 is split. api §14 owns the ingest contract; its driven-run part, which for 0.0.1 is the spool event format and its size caps that dev-env §15.3 links to, is written in the next apply pass (see the [decision log](../decisions/log.md#2026-10-27-inbox-answers-5-to-37-dashboard), "Applied later"). *Decided.*

### #37 · Browser protection for the token-less loopback API

- **Covers:** [SR-091](../reviews/R6-contract.md#sr-091-major-token-less-loopback-the-browser-threat-dns-rebinding-csrf-was-parked-with-the-login-node-question-but-it-applies-to-every-001-laptop)
- **Context:** R6 question 1. Reserved (security posture). In 0.0.1 the API trusts loopback with no token, so any web page can reach it through DNS rebinding or CSRF and launch runs. #15 covers shared login nodes only.
- **Options:**
  - (a) a host allow-list, an Origin check on writes and JSON-only writes, now;
  - (b) wait for #15;
  - (c) a local token even in 0.0.1.
- **Recommendation:** (a). It costs little and keeps the "no setup" story.
- **Assumed:** none (reserved).
- **Blocked:** api §6 (single-user mode) and auth-and-roles for 0.0.1.
- **Note (2026-10-27, cut revised):** answered for 0.0.1 by the token link ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)): no request is accepted without the token, the cookie is `SameSite=Strict`, and a `Host` allow-list refuses DNS rebinding. Whether to add an Origin check on writes and JSON-only writes (option a) stays open.
- **Answer (Thomas, 2026-10-27, dashboard):** (a), as recommended: an Origin check and JSON-only bodies on every write, on top of the token link. Applied in dev-env §15.3. *Decided.*

### #38 · Assumed: engine events and the progress denominator

- **Covers:** [SR-084](../reviews/R6-contract.md#sr-084-major-events-and-sse-frames-outside-the-complete-catalogue-no-sequence-for-sse-only-frames-no-data-schemas), [SR-088](../reviews/R6-contract.md#sr-088-major-run-resource-name-tags-task-counts-and-the-tasks-denominator-have-no-fields), [UX-272](../reviews/R6-contract.md#ux-272-major-task-progress-denominators-1248-tasks-68-tasks-task-quarters-have-no-source)
- **Context:** R6 questions 2 and 3; reversible and docs-only.
  - Events: one `events` log; engine-native types under `spectio.engine.*`, internal (never delivered to webhooks), with a `seq`; heartbeats kept out of the log (SR-084).
  - Progress: "% tasks" only when the engine gives a total (expected for Snakemake **[to be validated]**), otherwise "N done · M running" (SR-088, UX-272).
- **Options:**
  - (a) confirm both;
  - (b) a separate ingest log, with only published types in `events`;
  - (c) estimate the task total from the previous run.
- **Recommendation:** (a).
- **Assumed:** (a).
- **Blocked:** nothing.

### #39 · Assumed: the reads that 0.0.1 boards need

- **Covers:** [UX-274](../reviews/R6-contract.md#ux-274-major-runs-list-free-text-tag-date-and-multi-state-filters-totals-previous-and-needs-attention-are-not-in-listruns), [UX-275](../reviews/R6-contract.md#ux-275-major-app-chrome-on-every-001-board-has-no-operation-runner-and-server-status-review-badge-search-bell), [UX-278](../reviews/R6-contract.md#ux-278-major-no-manifest-read-the-gate-list-before-launch-stage-sources-and-names-overlay-versions-and-gate-names-cannot-be-shown), [UX-279](../reviews/R6-contract.md#ux-279-major-copy-to-a-new-launch-cannot-rebuild-a-runcreate-samplesheet-profile-and-gates-are-not-readable-from-a-run), [UX-285](../reviews/R6-contract.md#ux-285-major-gate-check-results-cannot-be-pivoted-into-the-item-table-or-the-per-check-cards-without-reading-every-row), [UX-286](../reviews/R6-contract.md#ux-286-major-tabs-and-row-actions-that-001-boards-show-have-no-draft-operation-outputs-reports-software-environment-evidence-report), [UX-291](../reviews/R6-contract.md#ux-291-minor-runscompare-outcome-and-cpu-hours-rows-need-per-run-check-and-accounting-data-that-001-does-not-have)
- **Context:** R6 question 5; reversible and docs-only. api §5 lists `GET /runs:summary`, `/gates:summary`, `/version`, a manifest read, `/runs/{id}/samplesheets`, `/gates/{id}/items` and artefacts, but the R6 draft cut them, although 0.0.1 boards use them. Nothing here adds a feature to the §15.1 cut: they are reads behind screens that are already in it.
- **Options:**
  - (a) widen the 0.0.1 contract to all of them;
  - (b) keep the reads a 0.0.1 board needs (`runs:summary`, `/version`, `gates:summary`, a read-only manifest, `/runs/{id}/samplesheets`, `/gates/{id}/items`, evidence artefacts), and hide the rest on the boards (search, Software, Environment, Batch, Adopt, RunsCompare Outcome and CPU-hours);
  - (c) keep the draft's cut and hide everything they feed.
- **Recommendation:** (b).
- **Assumed:** (b).
- **Blocked:** nothing.
- **Note (2026-10-27, cut revised):** gates are no longer in 0.0.1 ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)), so `gates:summary`, `/gates/{id}/items`, the manifest read and the evidence artefacts are no longer 0.0.1 reads; the run reads (`runs:summary`, `/version`, `/runs/{id}/samplesheets`) still are.

### #40 · Assumed: fixes that are right but not local

- **Covers:** [SR-061](../reviews/R3-journeys.md#sr-061-major-failures-before-the-engine-starts-have-no-state-transition-reason-or-screen), [CH-047](../reviews/R3-journeys.md#ch-047-major-why-did-it-fail-no-run-level-failure-cause-no-pointer-to-the-failing-task-and-no-local-failure-classes), [CH-043](../reviews/R3-journeys.md#ch-043-major-resume-inputs-are-not-stored-launch-directory-engine-session-id-engine-version-snakemake-unlock-and-rerun-flags), [CH-046](../reviews/R3-journeys.md#ch-046-major-a-head-that-ends-with-no-terminal-event-leaves-the-run-and-its-tasks-running-forever-on-the-local-launcher), [CH-048](../reviews/R3-journeys.md#ch-048-major-task-and-run-logs-on-the-local-executor-sources-unspecified-tasks-and-logs-tabs-never-drawn), [CH-050](../reviews/R3-journeys.md#ch-050-major-task-identity-across-launches-of-one-run-cached-tasks-reported-by-nextflow-and-silent-in-snakemake), [SR-065](../reviews/R3-journeys.md#sr-065-major-the-snakemake-launch-form-and-parameter-delivery-are-not-specified-for-001), [UX-250](../reviews/R3-journeys.md#ux-250-major-runscompare-cannot-be-reached-from-a-001-run-screen-and-draws-data-a-local-run-does-not-have), [CH-051](../reviews/R3-journeys.md#ch-051-minor-boot-recovery-has-no-defined-order-and-no-catching-up-signal-in-the-ui), [SR-082](../reviews/R6-contract.md#sr-082-major-stages-have-no-api-contract-no-resource-no-state-enum-no-single-identifier)
- **Context:** the doc review of TRIAGE2 asked how policy condition 3 was checked ("the proposal changes at most two sections of the owning spec, plus links elsewhere"). A re-check found ten first-pass accepts whose proposal also writes content, not only links, into other specs or boards:
  - SR-061, CH-047, CH-046, CH-048 and UX-250 add UI frames or boards, or local failure rules in `schedulers-and-monitoring.md`;
  - CH-043, CH-050, SR-065 and CH-051 change `synthesis.md` §5ter.5 or architecture §7.2 / §13.2 as well as the owner;
  - SR-082 adds the stage resource to api §7 and §5, the glob rules to `checking-scenarios.md` §12.3, and a CLI flag.

  Each proposal is confirmed, reverses no logged decision, and stays inside the 0.0.1 features (monitor, relaunch, parameters, one gate). Only its size takes it out of the accept rule.
- **Options:**
  - (a) apply each proposal as written in APPLY2;
  - (b) apply only the owner's part in APPLY2, and turn the rest (boards, other specs) into follow-up findings for a later round.
- **Recommendation:** (a). The other-spec parts are what makes each fix usable: a failure cause with no screen, or a stage resource with no matcher rule, would leave the gap open.
- **Assumed:** (a).
- **Blocked:** nothing.


## D3 (2026-10-27)

### #41 · Codespaces: install with `dev/bootstrap.sh`

- **Covers:** [dev-env §7.2](../specs/dev-environment-and-testing.md#72-the-full-stack-on-demand-in-github-codespaces-from-d3), [D3](../progress/W3/D3.md)
- **Context:** D5's `.devcontainer/setup.sh` installs uv, Snakemake, Nextflow and Playwright with its own commands (`curl … | sh`, `uv tool install`, `pip install`). It now reads the versions from `dev/versions.env`, but none of its downloads is hash-checked, and its Snakemake has no lock. `dev/bootstrap.sh` does the same installs, checked.
- **Options:**
  - (a) `setup.sh` calls `bash dev/bootstrap.sh` and keeps only the mkdocs install; the dev-container image and its features get pins in `versions.env` at the same time (D5 asked for them; D3 pinned only the tools);
  - (b) keep `setup.sh` as it is.
- **Recommendation:** (a), in a small follow-up step that also opens a codespace to check it. One install path is the §1 rule.
- **Assumed:** none. Nothing changes until you answer.
- **Blocked:** nothing.
- **Answer (Thomas, 2026-10-27 18:23 UTC, dashboard; confirmed in session):** (a), as recommended: `setup.sh` calls `bash dev/bootstrap.sh` and keeps only the mkdocs install, with the dev-container image and features pinned in `versions.env`, in a small follow-up step that opens a codespace to check it. *Decided.*

### #42 · Align the synthetic matrix and the required check names with Nextflow 26.10.4

- **Covers:** [CR-01](code/D3.md#cr-01-minor-the-11-nextflow-version-and-the-required-check-names-disagree-with-the-new-pin)
- **Context:** `dev/versions.env` pins Nextflow 26.10.4, the 26.10 patch release current on 2026-10-27. The `pipelines-synthetic.yml` matrix (dev-env §11) and the required status check names in [`autopilot.md`](../playbooks/autopilot.md) still say 26.10.3. Renaming a required check needs the branch protection updated at the same time, or PRs wait for a check that never reports.
- **Options:**
  - (a) move the matrix to 26.10.4 and rename the required check in the same change;
  - (b) keep 26.10.3 in the matrix until the next minor release.
- **Recommendation:** (a), done by the step that next edits `pipelines-synthetic.yml`, with you updating the branch protection.
- **Assumed:** none.
- **Blocked:** nothing.
- **Answer (Thomas, 2026-10-27 18:23 UTC, dashboard; confirmed in session):** (a), as recommended: the step that next edits `pipelines-synthetic.yml` moves the matrix to 26.10.4 and renames the required check, and Thomas updates the branch protection in the same change. *Decided.*
- **Update (T1, 2026-10-27):** matrix moved to 26.10.4 in `pipelines-synthetic.yml`. No branch-protection change is needed: of the pipeline checks, only the aggregate `ci-ok` is required; the required checks are `ci-ok`, `docs-gate` and `pr-body` ([`autopilot.md` §8](../playbooks/autopilot.md#8-pull-requests-and-auto-merge)).

### #43 · Set up the cloud environment from dev-env §2

- **Covers:** [dev-env §2, cloud environment settings](../specs/dev-environment-and-testing.md#2-where-agents-work)
- **Context:** only you can edit the Claude Code cloud environment. §2 now lists what to enter: the Custom network list (D2's list plus `nodejs.org` and `get.helm.sh`), two environment variables (no secrets) and the setup script `bash dev/bootstrap.sh --ci || true`.
- **Options:**
  - (a) apply §2 as written;
  - (b) apply it without the wildcard hosts (`*.quay.io`, `*.pkg.dev`, `*.prefix.dev`) until the D2 re-probe narrows them (SEC-D3-04);
  - (c) keep the default Trusted network for now. Bootstrap then fails on Node and helm, and the setup script still exits 0.
- **Recommendation:** (b). Bootstrap and the doctor need none of the wildcard hosts; the container pulls that would are not run in cloud sessions yet.
- **Assumed:** none.
- **Blocked:** a cached setup in cloud sessions. Until then each session runs `bash dev/bootstrap.sh --ci` itself (about 25 s cold).
- **Answer (Thomas, 2026-10-27 18:23 UTC, dashboard; confirmed in session):** (b), as recommended: the §2 network list without the wildcard hosts (`*.quay.io`, `*.pkg.dev`, `*.prefix.dev`) until the D2 re-probe narrows them. The environment currently has Full network; switching it to Custom with that list is Thomas's change in the environment settings. *Decided.*
- **Update (2026-10-27, tick 8):** the environment now has Full network, the two variables and the setup script, and they reach the session (`BASH_DEFAULT_TIMEOUT_MS=600000` is set). But the script ran in `/home/user`, the clone's parent, so `[ -f dev/bootstrap.sh ]` was false and bootstrap was skipped; `dev/doctor.sh` failed on Python until `bash dev/bootstrap.sh --ci` was run by hand (19 s, then doctor: all layers passed, 2 skipped). **To do:** replace the setup script with the new one in [dev-env §2](../specs/dev-environment-and-testing.md#2-where-agents-work), which starts with `cd /home/user/spectio`. *Open.*

### #44 · Assumed: Linux x86_64 only, and Node 24 ahead of the system Node

- **Covers:** [dev-env §1](../specs/dev-environment-and-testing.md#1-toolchain-pinned-in-devversionsenv), [D3](../progress/W3/D3.md)
- **Context:**
  - The checksums in `versions.env` are for linux/amd64, so bootstrap refuses any other platform. A laptop on macOS or arm64 would need a second set of checksums.
  - Bootstrap links Node 24.22.1 into `~/.local/bin`, which comes first on `PATH`, so in a cloud session it shadows the image's Node 22. Node 24 entered Maintenance LTS on 2026-10-20 and Node 26 becomes Active LTS on 2026-10-28 ([`schedule.json`](https://github.com/nodejs/Release/blob/main/schedule.json), read 2026-10-27); §1 asks for 24 LTS, which stays supported until 2028-04-30.
- **Options:**
  - (a) keep Linux x86_64 and Node 24 for now; add a platform when someone needs it; move to Node 26 with the first UI build;
  - (b) add macOS arm64 checksums now;
  - (c) move to Node 26 now.
- **Recommendation:** (a).
- **Assumed:** (a).
- **Blocked:** nothing.

## T7 (2026-10-27)

### #45 · Assumed: rna-seq-star-deseq2 and viralrecon stay in the PR tier

- **Covers:** [dev environment §10.2](../specs/dev-environment-and-testing.md#102-real-pipelines-testspipelinesrealcorpusyaml), [T7](../progress/W3/T7.md), [corpus note §2](../research/corpus-ci-2026-10-27.md)
- **Context:**
  - `pipelines-real` gates `ci-ok` again, on PRs that touch the corpus.
  - rna-seq-star-deseq2 is the only Snakemake entry in the PR tier that really runs. It failed 2 of its 4 runs on 2026-10-27, both on external errors: a biomaRt timeout on the Ensembl archive, and a conda-forge 502.
  - viralrecon (about 40 min) sets the PR tier's wall time.
- **Options:**
  - (a) keep both in `pr`. A red job from an entry tagged `network:` that failed on an external error is re-run once before anyone investigates, as §10.2 now says.
  - (b) move rna-seq-star-deseq2 to `nightly`. The PR tier then covers Snakemake only through the ms-proteomics dry run.
  - (c) also move viralrecon to `nightly`, which cuts the PR tier to about 20 min.
- **Recommendation:** (a). The PR tier is the only place where a real Snakemake run gates a merge, and the re-run rule costs one click.
- **Assumed:** (a).
- **Answer (Thomas, 2026-10-27, session):** a light PR tier, beyond (c): only nf-core/demo and the ms-proteomics dry run stay in `pr`; rnaseq, viralrecon, methylseq, molkart and rna-seq-star-deseq2 move to `nightly`. The private runners are small, and a heavy PR tier breaks on them for reasons outside the PR (rnaseq lost a Docker pull to a registry reset in run 40578574693). Applied in T7: `corpus.yaml`, [dev environment §10.2](../specs/dev-environment-and-testing.md#102-real-pipelines-testspipelinesrealcorpusyaml). *Decided.*
- **Blocked:** nothing.

### #46 · Follow-up: pin the corpus by commit and replace the Snakemake composite action

- **Covers:** [corpus note, follow-ups](../research/corpus-ci-2026-10-27.md), `docs/reviews/code/T7.md` (SEC-T7-01, SEC-T7-04)
- **Context:**
  - Every corpus entry except chipseq is cloned by a release tag, and an upstream maintainer can move a tag. Since T7, that code runs inside the required check whenever a PR touches the corpus, on a runner that holds the private repo's read token.
  - `snakemake/snakemake-github-action` is pinned by SHA, but it runs `conda-incubator/setup-miniconda@v3` and Miniforge `latest` unpinned.
  - Both risks predate T7, and both are rated low likelihood.
- **Options:**
  - (a) add a step that does both: a `sha` next to each `tag` or `version`, bumped together by Renovate, and explicit pinned conda setup steps plus `run_corpus.py --engine snakemake` in place of the composite action;
  - (b) pin by commit only;
  - (c) leave it as is.
- **Recommendation:** (a), as a small W3 step after T7.
- **Assumed:** none. Nothing changes until you answer.
- **Blocked:** nothing.
- **Update (TRIAGE3, 2026-10-28):**
  - **Also covers:** [SPK-T4-15](spikes.md#spk-t4-15-sec-t4-05-minor-supply-chain-nf-k8s-by-version-kueue-image-by-tag-full-bootstrap-in-the-job) (SEC-T4-05), code part:
    - the Kueue controller image by digest;
    - `nf-k8s` installed by bootstrap with a sha256;
    - `bootstrap.sh --only` in `pipelines-k8s.yml`.
  - The spec rule (dev-env §1) is accepted in TRIAGE3. The code waits for the same follow-up step as (a) of #46.

## T1 (2026-10-27)

### #47 · Assumed: the rnaseq and sarek gate stop-and-resume check moves to the nightly corpus

- **Covers:** [dev environment §3](../specs/dev-environment-and-testing.md#3-fixture-workflows-see-101), [CH-016](../reviews/R4-constraints.md#ch-016-major-stopping-at-a-gate-through-extwhen-is-proven-only-on-synthetic-pipelines) ([#28](#28-assumed-engine-bridges-runner-and-scheduler)), [T1 note](../research/spike-t1-fixture-workflows-2026-10-27.md#nf-corernaseq-and-nf-coresarek-not-run)
- **Context:**
  - The T1 prompt asks for the gate stop-and-resume check on the nf-core/rnaseq and nf-core/sarek test profiles. T1 did not run it.
  - Docker works in the session. The blocker is cost: rnaseq used about 23 GB of disk and 18–23 min per full run on CI, against 26 GB free in the session ([corpus note](../research/corpus-ci-2026-10-27.md)).
  - `run_corpus.py` cannot stop at a gate or resume yet.
  - Both pipelines already run nightly in `pipelines-real.yml`.
- **Options:**
  - (a) a per-entry `gate` key in `run_corpus.py`, used by the nightly rnaseq and sarek entries. It writes a generated `ext.when = false` config for the processes after alignment, then runs `-resume` without it, and records the cached-task count and the exit code of each run. The cost is about one full run each, and no new job is needed;
  - (b) run it by hand once, in a session.
- **Recommendation:** (a).
- **Owner:** a follow-up of T7 and T3 (the corpus runner and the nightly tier), not a new pipeline step.
- **Assumed:** (a) *(assumed — pending Thomas)*. Dev environment §3 marks the check as pending.
- **Blocked:** nothing. CH-016 stays open until the first nightly run of (a).

### #48 · Gate targets must include every earlier stage's last targets (`--until` runs only the target's own dependencies)

- **Covers:** [checking-scenarios §12.3](../specs/checking-scenarios.md#123-stage-boundaries), `ui-spec.md:264`, `synthesis.md:29`, [T1 note, finding 1](../research/spike-t1-fixture-workflows-2026-10-27.md#findings-and-fixes)
- **Context:**
  - Snakemake's `--until` "Runs the pipeline until it reaches the specified rules or files. Only runs jobs that are dependencies of the specified rule or files, does not run sibling DAGs" ([`cli.py` L892–L902 at v9.27.1](https://github.com/snakemake/snakemake/blob/v9.27.1/src/snakemake/cli.py#L892-L902)).
  - In T1, the synthetic pipeline stopped with `--until align_done` never ran its qc stage. The rerun then rebuilt 12 `temp()` read files.
  - The harness now stops with `--until qc_report align_done`.
  - §12.3 says "`--until` the last rules of the stage", and `ui-spec.md:264` and `synthesis.md:29` say the same: only the stage that ends at the gate.
- **Options:**
  - (a) change §12.3: a gate after stage N passes `--until` with the last targets of every stage up to N; ui-spec and synthesis link to it;
  - (b) keep the rule and require stages to form one chain, so that each stage depends on the one before it.
- **Recommendation:** (a), applied to §12.3 through `/apply-findings`; ui-spec and synthesis then link to §12.3 instead of restating it.
- **Assumed:** none. §12.3 is unchanged until then.
- **Blocked:** nothing.

## D6 (2026-10-27)

### #49 · Virgil licence: the excalidraw/virgil font file contradicts its repository's licence (revisits #1)

- **Covers:** [#1](#1-virgil-font-licence-blocks-publishing-the-hand-drawn-figures-font), `tools/diagrams/FONT-LICENSE.md`, [D6 Progress page](../progress/W3/D6.md)
- **Context:**
  - `excalidraw/virgil` `LICENSE.md` declares OFL-1.1: "Copyright (c) 2021 - Present, Ellinor Rapp, with Reserved Font Name Virgil." (read 2026-10-27).
  - The same repository's `Virgil.woff2` (fetched through `cdn.jsdelivr.net/gh/excalidraw/virgil@main`, 2026-10-27) carries other metadata in its name table: "Virgil 3 YOFF", "Copyright (c) 2011 by Your Own Font Foundry. All rights reserved.", "Freeware for personal use! For commercial license please go to https://www.yourownfont.com/ …".
  - The local copy taken from depictio is a third build ("Virgil GS", Jason Smith 2002, "All rights reserved").
  - The repository is public now. No font file is committed; `mkdocs.yml` excludes `fonts/*.ttf` so a local copy never reaches the site. `docs/fonts/OFL.txt` is committed, scoped to the release as `excalidraw/virgil` declares it. PNGs are still rendered locally, so byte-identical PNG rendering in CI stays blocked.
- **Options:**
  - (a) ask Excalidraw (issue on `excalidraw/virgil`) which licence covers `Virgil.woff2`, and commit it only on a clear OFL answer;
  - (b) switch to a font whose file and licence agree (Excalifont, or an OFL handwriting font from Google Fonts) **[to be validated]**, re-render every figure, then commit it with its licence;
  - (c) keep (c) of #1: font local only, SVGs checked in CI, PNGs rendered locally.
- **Recommendation:** (b), since it unblocks CI rendering without waiting on a third party; (c) until then. Nothing is sent to Excalidraw without Thomas.
- **Assumed:** (c), unchanged from #1.
- **Blocked:** byte-identical PNG rendering in CI (a deferred part of D6).

### #50 · D6 was built in a minimal version: the rest needs a follow-up step

- **Covers:** [D6 Progress page](../progress/W3/D6.md), [documentation system §1, §3.3, §7, §8](../specs/documentation-system.md)
- **Context:**
  - On Thomas's request (budget, tick 9), D6 did only: the build check now fails when `hooks/progress.py` output is missing; the docs-gate unit tests run in CI; the Virgil licence record (#49); and its review fixes.
  - Deferred: mike versioning on the Cloudflare previews (`dev` from `main`, `X.Y` on release, `latest` / `stable`, `/versions` page); the Zensical evaluation; `hooks/shared_images.py` (not due: no mike version, `docs/assets` about 11 MB < 50 MB); byte-identical PNGs in CI (#49); the F4 and F6 figures.
  - Two spec gaps seen on the way, not fixed: documentation system §3.3 item 3 names a `--allow-fallback-font` flag that `sketch.py` does not have (it falls back to a system font silently); §2 item 6 says the landing strip shows each wave's `public_title`, but `hooks/progress.py` renders `title`.
- **Options:**
  - (a) Thomas adds a step `D6b` to `pipeline.yaml` (after D6, before W4) with the deferred parts and the two gaps;
  - (b) fold the deferred parts into the release work (mike only matters once there is a release) and the two gaps into the next `/apply-findings`.
- **Recommendation:** (b): nothing deferred blocks W3 or W4; mike and `shared_images.py` are due at the first versioned docs.
- **Assumed:** none. The autopilot does not edit `pipeline.yaml`.
- **Blocked:** nothing.

## T3 / T4 (2026-10-28)

### #51 · T3 and T4 cannot run in a Claude Code cloud session: where do they run?

- **Covers:** `T3` and `T4` in [next-phase.md](../playbooks/next-phase.md#t3-mini-slurm-with-sind), [dev environment §4](../specs/dev-environment-and-testing.md#4-local-clusters), [spike D2](../research/spike-cloud-env-2026-10-26.md#result)
- **Context:**
  - The two next ready steps are T3 (sind profiles `slurm-mini`, `slurm-site`, `slurm-rest`, failure modes, `NODE_FAIL`, fixtures) and T4 (kind, Kueue, Job and Workload fixtures).
  - sind and kind need cgroup v2. Cloud sessions boot with a hybrid cgroup v1 layout that a session cannot change (spike D2). Dev environment §4.2 already says it: Kubernetes and SLURM scenarios run in CI and on the user's machine only. On 2026-10-28 this session still showed the v1 controllers under `/sys/fs/cgroup` (`blkio`, `cpu`, `cpuacct`, `cpuset`, …). Connecting a computer through Remote Control is not available to this session.
  - `dev-env.yml` already brings a sind cluster up on an `ubuntu-24.04` runner (cgroup v2) and runs `sbatch --wait` (`dev/doctor.sh`). A CI-driven T3 would extend it, iterating by push. The GitHub tools available here read job logs but cannot download artifacts. Fixtures would therefore have to come back through the logs, or through a write token, which is a new permission.
  - SEC-T1-06 (the harness deleted and reused the predictable shared workdir `/tmp/spectio-scenarios`) is fixed since 2026-10-28 ([review record](code/SEC-T1-06.md)), so this prerequisite of T3 is met.
- **Options:**
  - (a) Thomas runs `/autopilot --only T3` (then T4) in Claude Code on his own machine (Docker on cgroup v2), and the autopilot integrates as usual;
  - (b) CI-driven T3/T4 from a cloud session: the worker writes the profiles and a `workflow_dispatch` job on `autopilot/T3`, and iterates through pushes. The fixtures come back printed in the job log (size-limited) or as an artifact that Thomas downloads. Slower and costlier: each loop is a CI run of several minutes;
  - (c) Thomas enables Remote Control on a machine that has Docker on cgroup v2, and a cloud session attaches to that folder.
- **Recommendation:** (a) for T3 and T4. They are experiments with many short loops (create a cluster, inject a failure, read `squeue`/`sacct`), and a local Docker keeps each loop in seconds. (b) only if no local machine is available.
- **Update (2026-10-28, 09:50):** spike `t4-ci` ran T4's whole scope on GitHub-hosted runners in 2 push iterations: kind and Kueue, the synthetic pipeline with `-profile k8s` on Nextflow 26.10.4 and 25.10.9 (65/65 tasks each), a real `OOMKilled`, Workloads waiting for quota, both §4 ServiceAccounts. One loop takes 4–5 minutes. The fixtures came back from the job log, and this session could also download full logs and an artifact, contrary to the context above ([note on branch `spike/t4-ci`](https://github.com/weber8thomas/spectio/blob/spike/t4-ci/docs/research/spike-t4-ci-2026-10-28.md)). Spike `t3-ci` (sind `slurm-site`) is still running.
- **Assumed:** (b), CI-driven, *assumed — pending Thomas, inbox #51*. Thomas cannot answer before 14:00 and asked the autopilot to go on and keep only critical decisions for later (session, 2026-10-28 09:45). (b) is reversible: the profiles and fixtures are the same on his machine, only the place where the loop runs changes. T4 starts CI-driven; T3 starts once spike `t3-ci` shows sind works on a runner.
- **Blocked:** nothing while (b) holds.

## Direction (2026-10-28)

### #52 · Code first: start the walking skeleton before T5, T6, R10 and P1? (critical, not assumed)

- **Covers:** [`pipeline.yaml`](../playbooks/pipeline.yaml) W3 to W5, the rule "do not start writing product code" in `CLAUDE.md`, [proposal](../plans/walking-skeleton-proposal.md).
- **Context:**
  - Thomas, 2026-10-28: "J'ai l'impression que l'on surcomplexifie la totalité du projet" and "À quoi servent l'ensemble de ces étapes alors que l'on n'a pas commencé à coder ?".
  - On 2026-10-28 the repository held 85,000 words of specs, 154,000 words of reviews, 51 inbox entries, 14 agents, 24 skills, 11 workflows, 54 tool scripts, and no product code.
  - What is already worth having for code: T1 (synthetic pipelines that fail on demand), T2 (engine events captured from Nextflow and Snakemake), D3 (pinned engines), T7 (real pipelines in CI).
  - T5 (scenario runner), T6 (Playwright), R10 (synthesis), P1 (plan) and GO all come before the first line of product code. They prepare tests for an API and a UI that do not exist yet.
  - The review process is the same for a three-line test-harness fix as for product code (SEC-T1-06: five review rounds for a 15-line helper).
- **Options:**
  - (a) keep the pipeline as it is;
  - (b) code first: after T3 and T4, Thomas reorders `pipeline.yaml` so the walking skeleton ([proposal](../plans/walking-skeleton-proposal.md)) starts next. T5 and T6 move after it, and R10, P1 and GO shrink to that one-page proposal and Thomas's go. The full review circuit is kept for product code and real security boundaries; tooling and test changes get tests plus one review;
  - (c) as (b), and also stop T3 and T4 now.
- **Recommendation:** (b). T3 and T4 are cheap now that they run in CI, and their findings (RBAC in schedulers §4, the `nf-k8s` plugin) are needed by the first runners.
- **Assumed:** none. It changes the plan and a `CLAUDE.md` rule, which are Thomas's. The autopilot does not edit `pipeline.yaml` and writes no product code until he answers.
- **Blocked:** nothing yet; T3 and T4 go on.
- **Note, 2026-10-28 13:35 UTC:** Thomas asked to run T6 and to go on with what can move; the pipeline continues in its order (T6, then R10 and P1) under the narrowed 0.0.1 ([log](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui)). #52 stays open.

## TRIAGE3 (2026-10-28)

From the [spikes round](spikes.md): the differences that T2, T3, T4 and T7 measured. Step page: [TRIAGE3](../progress/W3/TRIAGE3.md).

### #53 · Kubernetes Roles for the runner and the Nextflow heads

- **Covers:** [SPK-T4-01](spikes.md#spk-t4-01-major-nextflow-2610-head-role-not-sufficient-and-broader-than-needed), [SPK-T4-02](spikes.md#spk-t4-02-major-nextflow-2510-head-role-lacks-podsstatus-get), [SPK-T4-03](spikes.md#spk-t4-03-major-the-runner-role-cannot-read-kueue-workloads), [SPK-T4-04](spikes.md#spk-t4-04-minor-runner-role-visibility-needs-only-get-minimality-is-not-measured)
- **Context:** the §4 engine-head Roles break every run. 26.10 is refused `pods/status get` and `pods delete`; 25.10 is refused `pods/status get`. The runner Role forbids the Workloads that §4 tells it to watch. T4 measured replacement Roles (`tests/k8s/rbac.yaml`): 0 refusals, and every head grant used. Kubernetes is not in 0.0.1 ([log](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)). Reserved: permission defaults.
- **Options:**
  - (a) §4 takes the measured Roles of `tests/k8s/rbac.yaml`:
    - 26.10 head: `jobs` create, delete; `jobs/status` get; `pods` list, delete; `pods/status` get;
    - 25.10 head: `pods` create, delete; `pods/status` get;
    - runner: the §4 rules plus `workloads.kueue.x-k8s.io` get, list, watch when Kueue is installed, and the visibility rule with `get` only;
    - a new Nextflow call shows up as a 403 in `pipelines-k8s.yml`, which fails on any refusal;
  - (b) as (a), but each head Role keeps §4's read grants (`get`, `list`, `watch`, `pods/log`) as headroom for code paths T4 did not hit (`fetchNodeName`, `kuberun`);
  - (c) leave §4 as it is until the runner code exists.
- **Recommendation:** (a): least privilege, measured, and CI catches the next missing call.
- **Assumed:** none (reserved).
- **Blocked:** schedulers §4 RBAC text. Nothing in 0.0.1. The fact part of SPK-T4-02 (drop "[to be validated on k8s-mini]" for `pods: create`) can be applied now.

### #54 · Kubernetes work namespace: task-pod tokens and a shared namespace

- **Covers:** [SPK-T4-12](spikes.md#spk-t4-12-sec-t4-02-major-task-pods-get-the-namespaces-default-serviceaccount-token) (SEC-T4-02), [SPK-T4-14](spikes.md#spk-t4-14-sec-t4-03-major-a-shared-work-namespace-lets-any-job-run-as-any-serviceaccount-there) (SEC-T4-03); related: [#14](#14-which-unix-identity-a-launch-runs-as-and-who-may-move-a-run-to-another-runner) (Kubernetes identity model, deferred)
- **Context:**
  - Task pods mounted the `default` token in every spike run. T4 turned it off for the test cluster only.
  - In one shared `spectio-work` namespace, whoever can create Jobs or Pods can run as any ServiceAccount there, mount a hostPath and delete another run's pods.
  - architecture §7.5 says only "in a work namespace". Reserved: security posture defaults.
- **Options:**
  - (a) one work namespace per user, labelled `pod-security.kubernetes.io/enforce=restricted` (which forbids hostPath), with `automountServiceAccountToken: false` on its `default` ServiceAccount, and a ValidatingAdmissionPolicy that allows only the head ServiceAccount on head Jobs **[to be validated]**;
  - (b) one namespace per run, with the same three controls; more objects, cleaned per run;
  - (c) a shared namespace with the token off and PodSecurity `restricted` only.
- **Recommendation:** (a). It matches "one runner per user" of #14 (a). Turning the task token off costs nothing and could be written now.
- **Assumed:** none (reserved).
- **Blocked:** architecture §7.5 runner sub-chart; schedulers §4. Nothing in 0.0.1.

### #55 · What engine events may carry: task `script` and `env`, user, host and command line

- **Covers:** [SPK-T2-11](spikes.md#spk-t2-11-major-task-script-and-env-in-engine-events), [SPK-T2-23](spikes.md#spk-t2-23-major-engine-events-carry-user-host-home-directory-and-command-line)
- **Context:**
  - The Tower client sends every task's `script` and `env` in every `progress` record.
  - Snakemake `WORKFLOW_STARTED` carries `host`, `user`, `cmd` and `cwd`. Tower `begin` carries `userName`, `homeDir`, `commandLine` and `configText`.
  - architecture §13.5 leaves "`script` and `env` at most once per task, or never" open *(assumed — pending Thomas, inbox #28)*.
  - The admin §3.4 redaction covers secrets, not personal identifiers.
  - In 0.0.1 these events land in SQLite on a shared login node. Reserved: security posture defaults.
- **Options:**
  - (a) `nf-spectio` never sends `script` or `env`; the runner reads `.command.sh` on demand inside the run's roots. Identity fields are kept on the run for display only (`user`, `host`), and `homeDir`, `commandLine`, `configText` and `env` are never stored. All of it passes the §3.4 redaction;
  - (b) `script` once per task, on its terminal event, after redaction; `env` never; identity fields as in (a);
  - (c) send and store everything, redacted server-side.
- **Recommendation:** (a). The UI can still show the command (read on demand), and nothing that may hold a secret leaves the cluster by default.
- **Assumed:** none (reserved).
- **Blocked:** architecture §13.5 wording; the payload rules of api §14 (inbox #36 apply pass).

### #56 · Assumed: the state of a task still open when the run ends

- **Covers:** [SPK-T2-09](spikes.md#spk-t2-09-major-tasks-left-open-when-the-run-ends)
- **Context:**
  - After a fatal error, Nextflow leaves tasks with `onTaskPending` and nothing after (FINAL_REPORT, 26.10.4), and ends a running one `ABORTED` (25.10.9).
  - api §7.2 has no terminal state for them, so they would stay `pending` or `running` forever. Reversible and docs-only.
- **Options:**
  - (a) a terminal attempt state `aborted` in §7.2 (Nextflow `ABORTED`, and every attempt still open when the launch ends), with an "Aborted" label in ui-spec §3.1; a task with no attempt stays `not_scheduled`;
  - (b) map them to `failed` with a new `failure_class` `aborted`;
  - (c) leave them open; the UI derives "stopped" from the run's terminal state.
- **Recommendation:** (a). The failed-task counts stay true (one tool error, not five failures), and the lattice keeps one terminal state per attempt.
- **Assumed:** (a) *(assumed — pending Thomas)*.
- **Blocked:** nothing.

### #57 · Assumed: `pipelines-k8s.yml` and `pipelines-slurm.yml` join `ci.yml`, as inbox #26 decided

- **Covers:** [SPK-T4-09](spikes.md#spk-t4-09-minor-pipelines-k8syml-is-standalone-while-required-checks-says-ciyml-calls-it), and the Required-checks part of [SPK-T3-13](spikes.md#spk-t3-13-minor-the-pipelines-slurmyml-row)
- **Context:**
  - dev-env §11 "Required checks" (*decided — Thomas, 2026-10-27, inbox #26*) says `ci.yml` calls every pipeline workflow, `pipelines-k8s.yml` and `pipelines-slurm.yml` included.
  - T4 and T3 built both standalone, outside `ci-ok`, and each asked whether it should join. `pipelines-k8s.yml` takes 3 to 4 minutes, and kind adds a flake risk. The longest `pipelines-slurm.yml` job takes about 16 minutes.
- **Options:**
  - (a) keep the #26 rule: both get `on: workflow_call`, and `ci.yml` calls each one when its own paths change, so it gates `ci-ok`:
    - `pipelines-k8s.yml`: `dev/k8s/`, `tests/k8s/`, `dev/versions.env`, `tests/pipelines/synthetic/nextflow/`;
    - `pipelines-slurm.yml`: `dev/slurm/`, `tests/slurm/`, `dev/versions.env`; changes to the synthetic pipelines alone are covered by its nightly run;
    - a red kind or sind job is re-run once before anyone investigates, as for `network:` entries in §10.2;
  - (b) keep both standalone and amend the paragraph (this reverses #26 for these workflows);
  - (c) `ci.yml` calls them, but they stay out of `ci-ok`'s `needs`, as `pipelines-real` was between D4 and T7.
- **Recommendation:** (a): RBAC and Slurm-classification regressions are cheap to catch there, and only PRs that touch those paths pay the time.
- **Assumed:** (a) *(assumed — pending Thomas)*. The two §11 rows say "standalone until it is converted to `workflow_call`", and the step that next edits each workflow converts it.
- **Blocked:** nothing.

### #58 · Assumed: who watches the nightly runs

- **Covers:** [SPK-T7-01](spikes.md#spk-t7-01-minor-nobody-watches-the-nightly-runs)
- **Context:** the nightly tier now holds the heavy corpus entries (#45). The nightly on `main` failed on 2026-10-28 (run 40649538349: rna-seq-star-deseq2, taxprofiler), and nothing recorded it. Reversible and docs-only for (b).
- **Options:**
  - (a) each nightly workflow opens or updates one GitHub issue when a scheduled run fails (needs `issues: write` on that job);
  - (b) at each tick, the autopilot reads the last scheduled run of each pipeline workflow (`gh run list --event schedule`) and reports a red one in the journal and the step report, with the failed jobs; a failure seen twice in a row becomes an inbox line;
  - (c) rely on GitHub's own notification for scheduled workflows **[to be validated: who receives it]**.
- **Recommendation:** (b): no new permission, and it uses the loop that already runs.
- **Assumed:** (b) *(assumed — pending Thomas)*, written in `autopilot.md`. The autopilot skill text follows once Thomas confirms, since `.claude/` is his to change.
- **Blocked:** nothing.

### #59 · slurmrestd: which token the runner holds, and which user it names

- **Covers:** [SPK-T3-15](spikes.md#spk-t3-15-major-x-slurm-user-name-with-a-users-own-token-no-clean-refusal); related: [#14](#14-which-unix-identity-a-launch-runs-as-and-who-may-move-a-run-to-another-runner) (which identity a launch runs as)
- **Context:**
  - schedulers §3.3 says the slurmrestd transport "lets a runner live off the login node", with JWT auth, but not whose token the runner holds.
  - On `slurm-rest` (Slurm 26.05.5), a user's token sent with `X-SLURM-USER-NAME: root` gets 200 on `ping` and 511 on cancelling root's job, which stays pending (runs 40679302148, 40680736055). The header does not let a user act as root, but a 2xx proves nothing about identity, and the meaning of 511 is **[to be validated]**.
  - 0.0.1 uses the CLI transport only (dev-env §15.3). Reserved: auth modes and security posture defaults.
- **Options:**
  - (a) per-user tokens only: the runner holds a JWT made for the run's user (`scontrol token` as that user, short lifespan, renewed on the login node), names only that user in `X-SLURM-USER-NAME` (or omits the header), and never holds a `SlurmUser` or root token. A successful call is never taken as proof of identity: the runner compares the `user_name` of the jobs it reads with the run's user;
  - (b) one service token per site with impersonation through `X-SLURM-USER-NAME` for each call. This needs the site to trust the runner with every user's identity **[to be validated: slurmrestd impersonation rules]**;
  - (c) keep slurmrestd out until #14 is decided; CLI transport only.
- **Recommendation:** (a). It keeps "runs as the user" from the CLI transport, and a stolen runner token is worth one user's jobs for a short time.
- **Assumed:** none (reserved).
- **Blocked:** schedulers §3.3 slurmrestd row. Nothing in 0.0.1.

### #60 · Assumed: who builds the deferred SLURM coverage

- **Covers:** [SPK-T3-18](spikes.md#spk-t3-18-minor-slurm-versions-2511-is-described-as-if-built-and-no-step-owns-the-deferred-slurm-coverage); related: SPK-T3-12, SPK-T3-17, and T3's open question 2.
- **Context:** T3 built `slurm-mini`, `slurm-site` and `slurm-rest` as its prompt asked. The following are in the specs but not built: `slurm-versions` (25.11), partition `gpu` with fake GRES, preemption, the `slurm-mini` signal drain, and head `OUT_OF_MEMORY` / head walltime scenarios. The signal drain and the head scenarios need a head job driven by runner code. No pipeline step owns any of them. Reversible and docs-only for (a).
- **Options:**
  - (a) mark every one "Planned, not built yet" in dev-env §3 and §4.1 now. Each is built by the first build step that needs it:
    - the signal drain and the head scenarios, with the runner's head-job code;
    - `slurm-versions`, `gpu` and preemption, with the first product code that reads SLURM JSON (the CLI collector);
    - that step's prompt names them;
  - (b) a dedicated build step after T5 that builds them all, added to `pipeline.yaml` by Thomas;
  - (c) drop `slurm-versions` and `gpu` from §4.1 until a site asks for them.
- **Recommendation:** (a): each piece is built when there is code to test against it, and the rows stop claiming coverage today.
- **Assumed:** (a) *(assumed — pending Thomas)*: the rows are marked planned. Naming them in later step prompts waits for Thomas, since `pipeline.yaml` and the prompts are his to change.
- **Blocked:** nothing.

## MVP scope (2026-10-28)

### #61 · Assumed: relaunch and parameter history leave 0.0.1

- **Covers:** [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) Relaunch and Parameter history rows, [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §2–§3, [decision log](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui), inbox #32.
- **Context:** Thomas, 2026-10-28: "UI ultra simple ; launch & monitoring de wf ; pas de gating ; pas de visu". The 0.0.1 cut of 2026-10-27 also had relaunch with changed parameters (a child run) and the parameter history across runs (Parameters and Lineage tabs, RunsCompare).
- **Options:**
  - (a) both leave 0.0.1 for "later (open)"; the run detail shows its own run's parameters;
  - (b) keep a plain Relaunch button (same parameters, a new run), drop the changed-parameter dialog and the history;
  - (c) keep both, as on 2026-10-27.
- **Recommendation:** (a): the smallest UI, and both can come back without rework because the data model keeps `run_inputs`.
- **Assumed:** (a) *(assumed — pending Thomas)*.
- **Blocked:** nothing; P1 plans without them.

### #62 · Assumed: 0.0.1 can cancel a run

- **Covers:** [R10 §5](R10-synthesis.md#5-go-no-go) D4; [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (no Cancel row) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) requirement 7 (names `:cancel`).
- **Context:** R10 found a gap no review finding names: §15.3 protects a `:cancel` route, but §15.1 does not say whether 0.0.1 cancels runs. A user who launches a run with the wrong parameters needs to stop it, and the head job holds SLURM resources.
- **Options:**
  - (a) one Cancel action in the run detail: `scancel` of the head job, which lets the engine stop its tasks (the drain rule of [schedulers §2](../specs/schedulers-and-monitoring.md));
  - (b) no cancel in 0.0.1; the user runs `scancel` by hand.
- **Recommendation:** (a): one button and one route, and the security requirement already exists.
- **Assumed:** (a) *(assumed — pending Thomas)*; P1 plans it. The §15.1 row is added when Thomas confirms.
- **Blocked:** nothing.

### #63 · Assumed: the repository-wide semgrep scan skips `tests/`

- **Covers:** SEC-T6-05 ([T6 code review](code/T6.md), PR #45); the SAST row of [dev-env §11](../specs/dev-environment-and-testing.md#11-ci-workflows).
- **Context:** semgrep's default ignore list applies when the repository has no root `.semgrepignore`, and it skips test directories, so `tests/` (the e2e harness of T6, the scenario runner tests of T5) is never scanned.
- **Options:**
  - (a) add a root `.semgrepignore` that keeps the defaults except `tests/`, in the next build step that touches CI;
  - (b) leave tests unscanned: they hold no product code.
- **Recommendation:** (a): the test harnesses run shell commands and Docker on CI runners.
- **Assumed:** (a) *(assumed — pending Thomas)*; done by the next step that touches `security.yml`.
- **Blocked:** nothing.
