# R7 · UI review: missing states, accessibility, consistency, sign-in flows

**Round:** R7 (UI review) · **Date:** 2026-10-26 · **Found by:** ux-reviewer, three instances in parallel · **Status of the round:** waiting for triage (TRIAGE1)

**Sources.**
- **Branch and commit:** `autopilot/integration` at `3b209d3`. Line numbers ("l." or `file:line`) refer to that commit.
- **Round brief:** [`next-phase.md`](../playbooks/next-phase.md), R7. It asks for missing loading, empty, error and no-permission states, accessibility, consistency with the Legend board and `design/tokens/spectio-tokens.css`, and the sign-in flows of [`authentication-and-access.md`](../specs/authentication-and-access.md) §5.
- **Read:** the boards in `design/ui-canvas/` (106 files), `design/tokens/spectio-tokens.css`, [`ui-spec.md`](../specs/ui-spec.md), [`authentication-and-access.md`](../specs/authentication-and-access.md), [`api-and-data-model.md`](../specs/api-and-data-model.md), [`admin-and-operations.md`](../specs/admin-and-operations.md), [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md), [`checking-scenarios.md`](../specs/checking-scenarios.md), decision [0001](../decisions/0001-nextflow-through-nf-spectio.md), the [decision log](../decisions/log.md) and the research note [`depictio-auth-2026-10-26.md`](../research/depictio-auth-2026-10-26.md) (depictio v1.19.2, `0d1aa0a`).
- **Reviewer scopes.** All three reviewers returned a full report; none failed.
  - (a) desktop core boards: Overview, Runs, RunDetail, RunScheduler, Review\*, Launch\*, plus the sign-in flows. 64 boards rendered at 1440×1180, RunScheduler also at 1440×2000.
  - (b) Workflows\*, Environments, EnvStorage, EnvKubernetes, EnvCapacity and the Administration boards. Tall renders of AdminHealth, EnvStorage, EnvCapacity, EnvKubernetes, WorkflowSnakemake, AdminBranding, AIAgents and SettingsUsers.
  - (c) the 13 phone boards (`M*.dc.html`) and the shared MobileTopbar and MobileTabbar, rendered at 390×844.
- **Renders.** The reviewers' PNGs are scratch files in `/tmp/w1-scratch/` (phone boards in `/tmp/w1-scratch/phone/`). They are not committed. Crop coordinates in the findings are pixels in those renders; re-render with `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180 /tmp/out.png` (390 844 for phone boards).
- **Merge checks.** I opened every quoted board line and spec passage for each major finding at `3b209d3` and reproduced all of them, so **none was dropped**. I also recomputed the nine contrast ratios with the WCAG 2.x formula; all match. Corrections made during the merge are marked **Merge note**.
- **Overlap with earlier rounds.** I read the open findings of [R1](R1-consistency.md), [R5](R5-security.md) and [R12](R12-ui-scenarios.md).
  - **Not repeated, cited instead:** R12 UX-103 (check states), UX-116 (terminal runs), UX-121 (scheduled start, pre-flight), UX-123 (overlays, catalogue), UX-124 (EnvConnect), UX-125 (software inventory), UX-126 (quotas, who may launch where); R1 SR-041 (ui-spec §10.2 points to a §3 that defines no screen states; Scheduler tab missing from §4.4), SR-042 (AI endpoints); R1 SR-038 (maintenance writes); R5 SEC-104 (endpoint → action matrix), SEC-117 (share-link rules).
  - Findings that touch these carry a **Related** line, so they can be triaged together.
- **Numbering.** The three reviewers used overlapping draft IDs (two used UX-201 onward). R12 uses UX-101 to UX-129, so this round is renumbered UX-201 to UX-240 in rank order. The table's last column gives the draft IDs as `a2nn`, `b2nn` and `c3nn` (reviewer a, b or c) for traceability only. A draft ID with "(part)" was split across two findings.

## Summary

| Severity | Count |
|---|---|
| Blocker | 0 |
| Major | 22 |
| Minor | 18 |
| **Total** | **40** |

Reviewer findings received: 61 (16 + 24 + 21). Merged as duplicates within the round: 21. Dropped as not reproducible: 0.

**The five findings that matter most:**
1. **UX-222 · major.** Five boards still teach the Tower protocol and `-with-tower` as the Nextflow route, including copyable commands on Profile and RunObserved. Decision 0001 names these boards as R7 follow-up. It is a copy fix on boards only, and should be done first.
2. **UX-203 · major.** The sign-in page, the magic-link "Continue as" confirmation (a security control against link prefetch) and their error states have no board, phone or desktop. Every multi-user instance opens on them, and the Playwright cases in auth §6 have no screens to target.
3. **UX-204 · major.** Share links, the main route for external reviewers, have no landing page, no "Create link" tab and no list or revoke endpoint. The current "Copy link" in ShareDialog suggests sharing that does not work.
4. **UX-201 · major.** No board shows a viewer, launcher, guest, link guest, a reviewer the gate policy does not name, or a non-admin. Boards show actions the API refuses with 403, and no API field tells the UI which actions are allowed.
5. **UX-205 and UX-211 · major.** No screen has a loading, error, stale-data or empty state, including the first run of a fresh `spectio serve` and the degraded states the specs define ("head silent", stale layer, runner offline). A phone reviewer can approve a gate on stale numbers.

**Recurring themes.**
- Boards show only the happy path for an owner-admin: UX-201, 205, 211, 215, 218.
- Boards offer actions and numbers that no endpoint serves: UX-202, 204, 206, 207, 208, 209, 210, 217.
- The state system's own rules are broken outside run states: UX-212, 213, 235.
- Custom controls built from `<span>` cannot be reached by keyboard: UX-219, 236.
- Boards disagree with each other, so the canvas cannot serve as a reference: UX-216, 221, 223, 224, 225.

## Findings table

| ID | Sev. | Title | Boards | Specs touched | Draft |
|---|---|---|---|---|---|
| UX-201 | major | Role-dependent states are not drawn, and the API does not say which actions are allowed | RunDetail, Review\*, ReviewQueue, Launch, Workflow\*, EnvStorage, Admin, phone | ui-spec, api, auth, admin | a204, b207, b206 (part), c306 |
| UX-202 | major | Administration → Settings → Sign-in, active sessions and sign-out have no board and no endpoint | AdminNav, Profile, SettingsUsers, MMore, MAdmin | auth, api, admin, ui-spec | a209, b202 (part), c303 |
| UX-203 | major | No boards for the sign-in page, the magic-link confirmation and their error states | none exist | auth, api, ui-spec | a205, b202 (part), c301 |
| UX-204 | major | No share-link landing, no "Create link" tab, and no endpoint to list or revoke links | ShareDialog, RunDetail, Review, phone | auth, api, ui-spec | a206, b203, b202 (part), c302 |
| UX-205 | major | No loading, error, stale-data or degraded-live states | RunDetail, RunScheduler, RunsTable, ReviewQueue, Env\*, phone | ui-spec, schedulers, api | a203, b205 (part), c305 |
| UX-206 | major | Review queue scopes, bulk actions and "Move to another runner" have no endpoint | ReviewQueue, MReviewQueue, MobileTabbar, MRunnerOffline | api, checking, ui-spec | a214, c310 |
| UX-207 | major | Headline counts, breakdowns and the activity feed cannot be served by the list API | RunsTable, Overview, ReviewQueue, RunDetail | api, checking, ui-spec | a208 |
| UX-208 | major | Four Administration sections have no board, and AI & agents and the outbox have no endpoint | AdminNav, AIAgents | admin, api, ui-spec | b204 |
| UX-209 | major | EnvStorage cannot be fed: no API or table for locations, lifecycle rules or work-directory actions | EnvStorage | api, admin, ui-spec | b209 |
| UX-210 | major | The notification bell and "Notify me when it is back" have no endpoint and no board | MobileTopbar, MRunnerOffline | api, admin, ui-spec | c309 |
| UX-211 | major | No empty or first-run state on any board, including single-user mode | Overview, Runs\*, ReviewQueue, Workflow\*, Environments, phone | ui-spec, api | a202, b205 (part), c304 |
| UX-212 | major | The Legend and tokens cover run states only; boards invent colours and words for every other state family | Legend, RunScheduler, AIAgents, EnvStorage, Admin\*, phone | ui-spec, admin | a211, b210, c315 |
| UX-213 | major | Warning and failure differ only by colour in check summaries and on the phone decision screen | Overview, ReviewQueue, MReview, MReviewCells, MWorkflows, MRunnerOffline | ui-spec, checking | a212, c313, b215 (part) |
| UX-214 | major | One tap on the phone turns on maintenance mode, and maintenance is invisible to phone users | MAdmin, every phone board | admin, ui-spec | b212, c308 |
| UX-215 | major | Administration has no single-user or untrusted-instance variant | Admin\*, AdminNav, Projects | admin, ui-spec | b206 (part) |
| UX-216 | major | The launch flow is drawn two ways, Launch has no project picker, and boards disagree on gates | Launch, LaunchReview, RunDetail | ui-spec, api | a207 |
| UX-217 | major | Workflow visibility per group is drawn, but the data model has no workflow grants | WorkflowDiscovered, WorkflowImport | api, admin | b213 |
| UX-218 | major | Phone gate decisions have no confirmation, no undo, and no lost-update or partial-failure screen | MReviewQueue, MReview, MReviewCells | ui-spec, api | c307 |
| UX-219 | major | Custom switches, checkboxes, tabs, radios and sliders cannot be reached by keyboard | SettingsUsers, WorkflowWatches, AdminGroups, Admin\*, phone | ui-spec | b211, c312 |
| UX-220 | major | Touch targets below 44 px in the shared phone components and most phone boards | MobileTopbar, MRuns, MReview\*, MWorkflows, MAdmin | ui-spec | c311, b215 (part) |
| UX-221 | major | Three navigation models for one workflow, and two editors for one overlay | Workflows, WorkflowSnakemake, WorkflowsCatalog, WorkflowVersions, WorkflowOverlay, WorkflowWatches | ui-spec | b208 |
| UX-222 | major | Five boards still show the Tower protocol or `-with-tower` as the Nextflow route | RunScheduler, RunObserved, Profile, WorkflowsCatalog, WorkflowDiscovered | boards only | a201, b201 |
| UX-223 | minor | Tab sets and run actions differ between variants of one screen and from ui-spec | RunDetail, RunScheduler, EnvCapacity, Environments | ui-spec, schedulers | a215 (part), b218 |
| UX-224 | minor | The project switcher appears on some boards and not others, with conflicting owners | most desktop boards, MProjectSwitcher | ui-spec, api | a215 (part), b219, c317 (part) |
| UX-225 | minor | Boards disagree on shared data, which hides the version-skew warning | Environments, AdminHealth, MAdmin, MRuns, MRunnerOffline, MWorkflows | ui-spec, admin | b220, c321 |
| UX-226 | minor | Branding lets admins recolour status colours with no rule linking them to run states | AdminBranding | admin, ui-spec | b223 |
| UX-227 | minor | Boards show features outside the MVP without marking them | RunScheduler, RunDetail, RunOutputs, LaunchReview | ui-spec, schedulers | a216 |
| UX-228 | minor | Runner tokens and the runner registry live in four differently named places | Environments, EnvKubernetes, SettingsServiceAccounts, AdminNav, SettingsUsers | ui-spec | b217 |
| UX-229 | minor | The desktop Maintenance board contradicts admin §4.4 | AdminMaintenance | admin | b216 |
| UX-230 | minor | The phone top bar hard-codes the Spectio emblem, so branded instances lose their brand on phones | MobileTopbar, MMore | ui-spec | c316 |
| UX-231 | minor | Phone navigation dead-ends in desktop boards and `#` links | MMore, MAdmin, MEnvironments, MWorkflows, MOverview | ui-spec | c317 (part) |
| UX-232 | minor | CLI-launched runs (`nf-spectio`) have no phone representation | MRuns, MRunDetail | ui-spec | c318 |
| UX-233 | minor | Phone boards only work at demo scale: large lists, large plates, long names | MRuns, MReview, MReviewCells, MobileTopbar | ui-spec | c319 |
| UX-234 | minor | Phone pinned bars: content shows through, chips are clipped, Next stays enabled with an open issue | MLaunch, MReview, MRuns | ui-spec | c320 |
| UX-235 | minor | Contrast failures on primary buttons, the Review badge, switches and helper text | EnvCapacity, MWorkflows, AdminMaintenance, MobileTabbar, MAdmin, MReviewQueue, Launch, LaunchChain | boards, tools | b214, c314, a213 (part) |
| UX-236 | minor | Focus ring, disabled state, active tab and truncated names on the core boards | RunsTable, ReviewQueue, Launch, RunDetail | boards | a213 (part) |
| UX-237 | minor | Clipped columns and truncated instructions | EnvStorage, WorkflowSnakemake, AdminRestore, RunScheduler | boards | b222, a213 (part) |
| UX-238 | minor | The Review boards call a run waiting at a gate "paused" | Review and 11 Review\* boards | boards | a210 |
| UX-239 | minor | The Health board's heartbeat timing and runner table disagree with the specs | AdminHealth | boards | b221 |
| UX-240 | minor | Creating a user shows a plaintext password instead of offering a sign-in link | SettingsUsers | boards | b224 |

Spec short names: [auth](../specs/authentication-and-access.md), [api](../specs/api-and-data-model.md), [admin](../specs/admin-and-operations.md), [ui-spec](../specs/ui-spec.md), [schedulers](../specs/schedulers-and-monitoring.md), [checking](../specs/checking-scenarios.md). Board names refer to `design/ui-canvas/<Board>.dc.html`.

---

## Major findings

### UX-201 · major · Role-dependent states are not drawn, and the API does not say which actions are allowed

- **Where:**
  - desktop: RunDetail header actions (x 1066–1396, y 115–157); Review sticky bar (x 1030–1416, y 1110–1152); Launch aside; ReviewQueue view-only row (x 290–1416, y 470–518);
  - Workflows and Environments: WorkflowOverlay and WorkflowWatches (Save overlay, toggles), WorkflowVersions ("Make 3.27.0 the lab default", "Apply suggestion"), WorkflowDiscovered (Promote, Ignore), EnvStorage (Edit, Clean, Add location), the Environments Credentials tab;
  - phone: MobileTabbar (Launch key always shown), MRunDetail ("Pause after stage", ⋯ Relaunch / Cancel), MReviewQueue (inline Approve, "Approve 3"), MReview and MReviewCells ("Apply and continue"), MWorkflows (Promote, Launch), MMore (Administration row);
  - Administration: the sidebar shows "Administration" to everyone.
- **Evidence:**
  - api §6 role table: "Launch, relaunch, cancel own runs" needs launcher; "Decide gates (when the gate policy names them)" needs reviewer; "Cancel anyone's runs, edit workflow manifests" needs editor; "the decision endpoint checks both the role and the policy".
  - auth §1: "**Guests are read-only:** no launches, no gate decisions, no tokens." auth §2: a share link makes "a guest principal bound to that link", role viewer or reviewer.
  - ui-spec §2 and §4.9: Administration is "admins only".
  - The only view-only cue on any desktop board is `title="You can view this gate; only clinical-genomics can decide"` (ReviewQueue.dc.html:184). It is hover-only, and every row, view-only or not, renders the same selection checkbox (ReviewQueue.dc.html:91), so a view-only gate can be included in "Approve the 2 where all checks pass" (:65).
  - On Workflows and Environments, the only role cue is sarek's "View only" chip on WorkflowsCatalog. MProjectSwitcher shows Viewer / Reviewer / Launcher roles, but no phone board changes with the role.
- **Problem:**
  - Implementers will either show actions that fail with 403 or hide them inconsistently.
  - "All 27" in the queue mixes gates the user can and cannot decide.
  - Without an API field, the UI has to duplicate the `can()` policy and the gate policy.
- **Proposal:**
  - **Rule (ui-spec §1, linked from §4.4, §4.5 and §4.11):** hide what a role can never do; show disabled, with a visible inline reason, what the user could do after a grant or a state change ("Only rnaseq-core can decide · Ask Alice"). No reason in a hover-only `title`.
  - **API (api §5):** return `allowed_actions` on `GET /runs/{id}`, `GET /gates` and `GET /gates/{id}` (and on workflow and environment resources).
  - **Boards:** RunDetail as a viewer; ReviewViewOnly (sticky bar replaced by "You can view · decided by clinical-genomics · Request to decide", change chips disabled); Launch for a user with no launcher grant; a viewer variant of WorkflowOverlay (read-only YAML, disabled toggles with the reason); a non-group-admin EnvStorage (Edit, Clean, Add location hidden; credentials masked); role variants of MRunDetail, MReviewQueue and MReview.
  - **ReviewQueue:** show a lock and "view only" in the "Can decide" cell, disable the checkbox and exclude the row from bulk actions.
  - **Phone:** drop the Launch tab for principals with no launch right in any project (More keeps its slot); show a "Guest · read-only" chip for public and demo guests.
  - **Administration:** hide the sidebar item from non-admins on multi-user instances and add a 403 page for direct URLs.
  - **Who edits an environment** (group admin?) and who may see credentials: state it in api §6.
- **Related:** R5 SEC-104 asks for an endpoint → action → scope → role matrix; `allowed_actions` would be computed from it. Triage together.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-202 · major · Administration → Settings → Sign-in, active sessions and sign-out have no board and no endpoint

- **Where:** `AdminNav.dc.html:68` (Settings links to `'#'`); `Profile.dc.html:185`; SettingsUsers (Sign-in column; "Identity settings →" link); MMore sheet (`/tmp/w1-scratch/phone/MMore.png`, y 300–745); MAdmin Instance group (MAdmin.dc.html:89–93); auth §3, §5; api §5; admin §5.
- **Evidence:**
  - auth §5 asks for "Administration → Settings → Sign-in: the methods with their status, and test buttons (for example 'Send me a test link', 'Test SAML metadata'); token lifetimes; rate limits; active sessions per user, with 'sign out everywhere'".
  - auth §3: "Server-side session row, so logout revokes it." The "Session & me" row of api §5 lists no logout endpoint, and neither api §5 nor admin §5 lists sessions or sign-in tests.
  - `Profile.dc.html:185` says "Single user, no login" with the tag "MVP · SSO via OIDC in phase 2". On the same demo instance, SettingsUsers lists users who sign in with "OIDC · Demo SSO" and "SAML · Keycloak". auth §0 has no phasing.
  - The MMore sheet has profile, Workflows, Environments, Administration, Help, Appearance and status, but **no Sign out**.
- **Problem:** an admin cannot see or revoke sessions or test a method; a phone user cannot sign out, which matters on shared lab devices; Profile contradicts the instance.
- **Proposal:**
  - **AdminSignIn board** (desktop, plus a read-only phone row under Instance → Settings, following MAdmin's own "read-only on a phone" rule):
    - the mode, read-only, from `SPECTIO_AUTH_MODE`;
    - each method with its state and a test button ("Send me a test link", "Test SAML metadata", "Test OIDC discovery");
    - toggles for `registration_disabled` and `password_login_disabled`, the second disabled with its reason ("only when another method is on");
    - token lifetimes (auth §3) and rate limits, with their source (env, UI, locked; admin §4.5);
    - active sessions per user with "Sign out everywhere";
    - the "CLI equivalent" block (ui-spec §4.9).
  - **Endpoints:** `POST /auth/logout`; `GET /admin/sessions?principal=`, `DELETE /admin/sessions/{id}`, `POST /admin/principals/{id}:sign-out-everywhere`; `POST /admin/auth/{method}:test`. Where they live is open (see the questions; R1 SR-013).
  - **Phone:** "Sign out" at the bottom of the More sheet.
  - **Profile:** list the instance's methods and the user's own sessions. If OIDC really is phase 2, add a phase column to auth §0 (question for Thomas).
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open
- **Merge note:** reviewers (a) and (c) rated this minor; reviewer (b) included it in a major finding. Kept as major because a logout endpoint and session revocation are missing from the API, not only from the boards.

### UX-203 · major · No boards for the sign-in page, the magic-link confirmation and their error states

- **Where:** `design/ui-canvas/`: no board matches "magic", "access code", "Continue as" or "Starting your session" (`Landing.dc.html` is the public marketing page). AdminBranding defines a "sign-in greeting" that no board shows. auth §1, §2, §2.1, §5.
- **Evidence:**
  - auth §5: "the SSO buttons first (SAML label, OIDC providers), then 'Email me a sign-in link', then password; the access-code gate for `public` instances; 'Starting your session' in `single` mode."
  - auth §2.1: tickets in the fragment (`/auth/magic#t=…`), "Exchanged by a JavaScript POST after a **'Continue as `<email>`' confirmation screen**"; "other browsers get a 'check your email on this device' message"; 15-minute expiry; single use; "`next` limited to a same-origin path".
  - auth §2: the magic-link response "is always 'if the address exists, a link is on its way'". auth §1: `GET /auth/config` "lets the UI draw the sign-in page" (mode, methods with labels, `access_code_required`, `registration_open`). In `single` mode, any non-loopback interface "requires a token (from `spectio login` or a link)".
  - depictio v1.19.2 (`0d1aa0a`), per [`depictio-auth-2026-10-26.md`](../research/depictio-auth-2026-10-26.md): `PublicAccessGate.tsx` "Enter the access code" and "Starting a guest session" (`AuthApp.tsx:131,139`) (l.71–72); `SignInProviders.tsx` puts the SAML button first, default label "Sign in with SSO", and `LoginForm.tsx:224–245` says "This instance signs in with Google." when password login is disabled (l.174–176); the exchange is `POST /auth/magic/exchange` (l.108).
  - auth §5 says Spectio uses "the same order and wording as depictio". The audit covers the public-mode splash ("Starting a guest session"), not a single-mode "Starting your session", so wording parity for `single` is **[to be validated]**.
  - api §5 does not name the magic-link exchange endpoint.
- **Problem:**
  - This is the first screen of every multi-user instance, and on a phone the first contact is usually a sign-in or hand-over link from email or chat.
  - The confirmation screen is a security control (it stops prefetch from consuming the ticket) and is not drawn. The error states (expired, used, other browser, rate-limited, rejected `next`) are undesigned.
  - The Playwright cases in auth §6 ("request → Mailpit → click → confirm → session; replay rejected") have no screens to target.
- **Proposal:** add these boards, each at 1440×1180 and 390×844, with no app shell, branded from AdminBranding:
  1. **SignIn**, drawn from `GET /auth/config`. Variants: local + OIDC/SAML (label from `saml_login_label`) + email link + password; password disabled ("This instance signs in with SSO"); "Create account" only if `registration_open`; the `public` access-code gate, then "Continue as guest · read-only"; the `single` "Starting your session" splash, plus the non-loopback case asking for a token or a `spectio login --print-link` link; lockout or rate limit with the retry time and a generic error.
  2. **MagicLinkSent:** the neutral "If the address exists, a link is on its way", resend with a rate-limit countdown, a note when browser binding is on.
  3. **MagicLinkConfirm** (`/auth/magic#t=…`): "Continue as alice@example.org" with one button; states expired (15 min, "Send a new link"), already used, other browser ("check your email on this device"), rate-limited, rejected `next`; then a redirect to `next`.
  4. **MustChangePassword** and the password-reset landing.
  5. An OIDC/SAML callback error page.
  - **API:** name the exchange and logout endpoints in api §5 (for example `POST /auth/magic-links:exchange`, mirroring depictio's `POST /auth/magic/exchange`).
  - **Accessibility:** focus starts on the first provider; errors in an `aria-live` region; 44 px targets on the phone.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-204 · major · No share-link landing, no "Create link" tab, and no endpoint to list or revoke links

- **Where:** `ShareDialog.dc.html` (dialog x 420–1020, y 96–796; footer "Copy link" at l.91); RunDetail and Review headers; MProjectSwitcher ("All projects and sharing" goes to the desktop Projects board); auth §2, §5; api §5, §6.
- **Evidence:**
  - auth §5: "**Share dialog:** besides users and groups, a 'Create link' tab (role, expiry, maximum uses, optional email), with a list of active links and their uses, and a Revoke button."
  - auth §2: `POST /share-links {resource: run|gate|project, id, role: viewer|reviewer, expires_in, max_uses, email?}` "by a project owner or editor". "The recipient becomes a **guest principal bound to that link**, or signs in to keep the access … Revocable at any time."
  - ShareDialog has no tabs. Its footer "Copy link" copies `spectio.example.org/p/liver-time-course`, a plain URL that only works for people who already have access.
  - Only `POST /share-links` is specified. Nothing lists links, counts their uses or revokes them (auth §2, api §5).
  - Share links target runs and gates, but the dialog is reachable only from Projects.
  - api §6: "Manage grants, webhooks, service accounts, delete" is owner only, while auth §2 lets an editor create links.
- **Problem:**
  - External reviewers, the main use of share links (auth §0), cannot be invited from the UI.
  - "Copy link" next to sharing controls will be read as a share link.
  - An external reviewer opening a gate link lands in the full shell (on the phone: "Hello, Alice", Runs, Launch, More) with nothing telling them they are a scoped guest, when access ends, or how to keep it.
  - The owner cannot see or revoke links.
- **Proposal:**
  - **ShareDialog:** tabs "People and groups" and "Create link", plus a phone bottom-sheet version. Create link: resource (prefilled), role (Viewer / Reviewer), expiry (1 h / 24 h / 7 d default / 30 d max), maximum uses, optional email. The link is shown once (only its hash is stored). An active-links table: created by, role, expires, uses n / max, last use, Revoke. Rename the footer action "Copy page address (members only)".
  - **Entry points:** a Share action on the RunDetail and Review headers, for the roles allowed to create links.
  - **ShareLanding board** (desktop and phone): who shared, which run or gate, role and expiry; "Continue as guest reviewer" and "Sign in to keep access"; then Review detail with a persistent guest banner ("via link from Alice · reviewer on this gate only · expires 28 Oct"), navigation trimmed to the link's scope claim (auth §2.1), no Launch or Runs list on the phone, decisions attributed as "guest via link created by Alice"; states expired, revoked, maximum uses reached, invalid, outside scope, each with "Ask Alice for a new link".
  - **API (auth §2, listed in api §5):** `GET /share-links?resource=`, `GET /share-links/{id}/uses`, `DELETE /share-links/{id}`.
  - **Roles:** add a row "Create share links" to the api §6 table and link it from auth §2 (owner or editor: question for Thomas).
- **Related:** R5 SEC-117 (share links contradict the guest, grant and gate-policy rules; proposes owner-only reviewer links, a `link` principal kind, and revocation ending live sessions). The landing board should follow whatever SEC-117's triage decides. Triage together.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-205 · major · No loading, error, stale-data or degraded-live states

- **Where:** RunDetail header actions (x 1066–1396, y 115–157); RunScheduler footer (`RunScheduler-tall.png`, y 1590–1650); RunsTable and ReviewQueue tables; Workflow\*, Environments, EnvStorage, EnvCapacity; every phone board, in particular MRunDetail and MReview.
- **Evidence:**
  - "skeleton" or "Loading" appears only in ViewerOmeZarr, AdminRestore and Coverage. No board has an offline banner, a reconnecting state or an "updated n s ago" marker. MRunDetail's live counters and log carry no live marker.
  - The specs define degraded states with no board:
    - schedulers §3.2 (l.218): "the run shows as 'head silent' and the runner checks the head's log";
    - schedulers §3.1 (l.82): "On a timeout the interval doubles, up to 10 min, and the layer shows as stale in the UI";
    - schedulers §7 (l.155): "✗ blocks the launch unless overridden", while EnvCapacity's pre-flight (x 968–1415, y 515–1025) shows only ✓ and ⚠;
    - ui-spec §4.8: "cancel/pause/continue — queued and applied on reconnect", and storage measurements "On hold" while a runner is offline; EnvStorage and EnvCapacity show only "Runner online";
    - api §5: `GET /events/stream` "(SSE, resumable with `Last-Event-ID`)"; api §4: RFC 9457 errors.
  - Overview says "2 runs cannot be steered", but no RunDetail board shows such a run. Pause and Cancel are always enabled, with no freshness indicator.
  - WorkflowImport assumes "nf-co.re/pipelines.json · 124 pipelines · fetched 10 min ago". Whether HPC login nodes can reach it is site-dependent **[to be validated]**.
- **Problem:** the cases users actually hit (runner down, head silent, SSE dropped, phone tab suspended, 5xx, catalogue unreachable) are undesigned. Pause or Cancel may silently do nothing, and a reviewer can approve a gate on numbers that are minutes old.
- **Proposal:**
  - **RunDetailDegraded** board with three variants: runner offline (buttons become "Queue pause · applies on reconnect", reason shown, link to RunnerOffline); head silent ("No event from nf-spectio for 6 min · head job 48213351 still RUNNING · checking the head log"); live updates paused ("Reconnecting… data as of 10:41:08", Retry).
  - **Stale layers:** a RunScheduler footer ("squeue timed out · next try in 4 min"); an environment stale chip ("`sinfo` stale since 13:40, back-off 10 min"); `observer.capacity: off` ("disabled by site policy"); runner offline on Storage and Capacity ("last measured 14:02 · on hold"); a pre-flight ✗ with "Override (recorded)".
  - **Workflows:** pipelines.json or the Snakemake catalogue unreachable, falling back to Git URL or path; skeleton cards.
  - **Shared patterns:** skeleton rows for tables and cards (header kept, grey gauges); an error panel that maps the problem `type` to a sentence and shows the request ID; an API-error toast; a full-page "Spectio is unreachable".
  - **Phone:** a status strip under MobileTopbar with Live / "Reconnecting… last update 10:42" / Offline (actions disabled with the reason), shown on MRunDetail and MReview.
  - **Legend:** a "Live data" row (live, stale, reconnecting, head silent), each with an icon and a word.
  - **Spec:** define these screen states once in ui-spec (see UX-211 for where).
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-206 · major · Review queue scopes, bulk actions and "Move to another runner" have no endpoint

- **Where:** ReviewQueue bulk bar (y 268–314), "Suggestion" and "Can decide" columns; MReviewQueue (Mine / My groups / All); MobileTabbar (badge); MRunnerOffline ("Move to hpc-login-1", MRunnerOffline.dc.html:96); api §5, §7.
- **Evidence:**
  - ReviewQueue offers "Assign to…" and "Snooze 1 h" (ReviewQueue.dc.html:66–67); ui-spec §4.5 promises "assign, snooze" and a summary strip "assigned to me, my groups…". api §5 has only `POST /gates:bulk-decide` and `GET /gates (queue: ?assigned_to=me&state=open)`, with no group scope.
  - The `gates` table (api §7) has no assignee, no `snoozed_until` and no deciders resolved from the policy. Nothing defines who a gate is assigned to.
  - MobileTabbar.dc.html:43 hard-codes `count: 27`, which is the "All" count in MReviewQueue ("Mine 8 · My groups 16 · All 27").
  - ui-spec §4.8 promises "Move to another runner on the same cluster"; `PATCH /runs/{id}` covers only "name, tags, external_refs, project move".
- **Problem:** the "My groups" tab, assign, snooze and the primary action of the phone's queued-run card cannot be served. The badge shows a number most users cannot act on.
- **Proposal:**
  - Gate resource: `assignee_principal_id`, `snoozed_until`, `deciders[]` (resolved from the policy), `latest_proposal`.
  - `GET /gates?assigned_to=me|my_groups|group:<id>`; `POST /gates:bulk-assign`, `POST /gates:bulk-snooze`.
  - Define what assignment means in checking (who assigns, whether it restricts deciding).
  - `POST /runs/{id}:reassign {runner_id}` (queued runs only, same environment), and who may call it.
  - Define the Review badge as "open gates I may decide" and make it a MobileTabbar prop.
- **Related:** "Move to another runner" changes the Unix identity a run uses: R5 SEC-101 and R1 SR-014 restrict it to runners with the same `run_as`.
- **Found by:** ux-reviewer (a), ux-reviewer (c)
- **Status:** open
- **Merge note:** reviewer (a) rated its part minor, reviewer (c) major. Kept as major.

### UX-207 · major · Headline counts, breakdowns and the activity feed cannot be served by the list API

- **Where:** RunsTable header (x 354–954, y 122–138) and pager (y 1118–1152); Overview "Last 7 days by item kind" (x 1076–1416, y 466–760) and "Recent activity" (y 776–1130); ReviewQueue item-kind chips (y 172–255); RunDetail "Busiest processes" (RunDetail.dc.html:76).
- **Evidence:**
  - api §4: "cursor pagination (`?cursor=`, `limit` ≤ 200, `next` in the response)". No total, no previous page.
  - Boards show numbers the API cannot return: "1–16 of 214 runs" with Previous / Next and "2,946 runs" (RunsTable.dc.html:30, 56); "173 with no gate" (Overview.dc.html:118); "For me / My groups / All" counts and per-item-kind counts (ReviewQueue.dc.html:223–224).
  - `events` (api §7) is `run_id, seq, event_id, type, payload` with no actor column, and `GET /events` is filtered per run.
  - "Busiest processes" aggregates tasks (up to about 100 000 per run) with no per-process endpoint.
- **Problem:** each number costs N paged calls (about 15 for 2,946 runs, about 500 for 100 000 tasks), or it is dropped. The feed cannot say who acted (person, AI, API, CLI) without parsing payloads.
- **Proposal:**
  - `GET /runs:summary` and `GET /gates:summary` (`?project=&since=&group_by=state|item_kind|workflow|assignee`).
  - An optional `total` on lists (`?count=exact|estimate|none`). Without it, boards show "Next" or "Load more" instead of numbered pages.
  - `GET /runs/{id}/processes`: tasks by state, retries, peak RSS, native ID range.
  - A per-gate `item_kind` (from `spectio.yml` `items`).
  - `actor_principal_id` and `actor_kind` on events, and `GET /events?project=&type=` for the feed.
- **Found by:** ux-reviewer (a)
- **Status:** open
- **Merge note:** `gate_items.kind` exists (api §7), so item kinds can be read per item; what is missing is a per-gate kind and an aggregate. The `decisions` table already has `principal_id` and `actor_kind`; events do not.

### UX-208 · major · Four Administration sections have no board, and AI & agents and the outbox have no endpoint

- **Where:** `AdminNav.dc.html:56, 59, 65, 68` (Events & webhooks, Audit log, Notifications, Settings all link to `'#'`); AIAgents (model endpoints, connected agents, limits); admin §1, §3.3, §4.5, §5.
- **Evidence:**
  - admin §1 lists "Events & webhooks · outbox, deliveries, event bridges", "Audit log", "Notifications · notifier instances and routing" and "Settings · runtime-editable settings". admin §3.3 adds "Actions: redeliver, and pause a subscriber".
  - The admin §5 endpoint table has no rows for outbox, audit, notifications, AI or agents. api §5 has only `GET /audit-log` and per-webhook deliveries.
  - ui-spec §4.9 promises "default limits for agents … A gate can be stricter than the defaults, never looser".
- **Problem:** four routed sections (`/admin/<section>`) have nothing to show, and AI & agents, the instance outbox and pausing a subscriber cannot be fed by any specified endpoint.
- **Proposal:**
  - Boards: AdminEvents, AdminAudit, AdminNotifications and AdminSettings. AdminSettings shows every setting with its source and lock (admin §4.5) and hosts Sign-in (UX-202).
  - Endpoints in admin §5: `GET /outbox?type&state`; `POST /subscribers/{id}:pause|resume`; `GET /bridges`; `GET/PUT /notification-routes`; `GET/POST/PATCH /ai/endpoints`; `GET/PUT /ai/agent-defaults`; `GET /audit-log?principal&object&since` with a cursor.
- **Related:** R1 SR-042 already covers the missing AI endpoints and tables; R1 SR-013 covers the duplicated endpoint catalogues (where admin endpoints belong).
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-209 · major · EnvStorage cannot be fed: no API or table for locations, lifecycle rules or work-directory actions

- **Where:** EnvStorage: Locations (x 290–1097, y 200–765), "Work directory lifecycle" with Edit (y 775–1090), "Largest work directories" with Keep / Clean (y 1100–1370, tall render; EnvStorage.dc.html:178–186); api §5, §7; admin §4.4.
- **Evidence:**
  - api §7 `environments`: "owning_group_id, kind (slurm, k8s, local…), config (JSON)". api §5 has only `GET/PATCH /environments/{id}`.
  - admin §4.4 has a cleanup job for "work directories, following each environment's lifecycle policy", but the policy has no schema.
  - ui-spec §4.8 describes storage roles, usage against quota, retention, lifecycle rules, "largest work directories with Clean / Keep" and "a proposed cleanup that never breaks a resumable run". The board shows "Measured by the runner every 6 h · 18.4 TB in 41 runs".
- **Problem:** there is no contract for roles, usage, retention, lifecycle rules or measurements. Clean and Keep have no endpoint and no audit event, so the "never breaks a resumable run" guarantee cannot be enforced.
- **Proposal:**
  - api §5: `GET/PUT /environments/{id}/storage` (locations: role, path, type, quota source, access, retention); `GET/PUT /environments/{id}/lifecycle` (rules per run state); `GET /environments/{id}/workdirs?sort=size`; `POST /runs/{id}/workdir:keep|clean` with an `If-Match` guard on resumable runs.
  - api §7: a `workdir_usage` table. api §8: the event `spectio.run.workdir_cleaned`.
  - Reuse the schedulers §3 quota layer for usage.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-210 · major · The notification bell and "Notify me when it is back" have no endpoint and no board

- **Where:** MobileTopbar (bell, `aria-label="Notifications, 3 unread"`, `href="#"`, on every phone screen); MRunnerOffline ("Notify me when it is back", MRunnerOffline.dc.html:67); ui-spec §2 (top bar "notifications"), §4.10 (notifications matrix); api §5, §8; admin §1.
- **Evidence:**
  - api §5 has no `/notifications` or subscription endpoint; §8 has webhooks only.
  - admin §1 lists "Notifications: notifier instances and routing" with no admin §5 row (see UX-208).
  - ui-spec §4.10: a "notifications matrix (event × in-app / email / Slack)", so an in-app channel is promised.
- **Problem:** no in-app inbox, unread count, per-user subscription (for example to `spectio.runner.online`) or notification screen can be built. On a phone, notifications are the main reason to open the app.
- **Proposal:**
  - api §5: `GET /me/notifications?after=`, `POST /me/notifications:mark-read`, `GET/PUT /me/subscriptions` (resource and event type, for example runner `.online` or gate `.opened`).
  - Boards: an MNotifications sheet or screen grouped Today / Earlier, each item deep-linking to a run or gate, with empty and loading states; the desktop bell panel.
  - Decide whether phones get Web Push (PWA) or only email and Slack. Browser support and the iOS home-screen requirement are **[to be validated]** (see the proposed spikes).
- **Related:** R1 SR-045 (gate notifications have two paths: `gate.notify` task vs outbox notifiers).
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-211 · major · No empty or first-run state on any board, including single-user mode

- **Where:** Overview, RunsTable, RunsRows, ReviewQueue; Workflow\* and Environments; MOverview, MRuns, MReviewQueue, MWorkflows, MEnvironments; ui-spec §10.2.
- **Evidence:**
  - None of these boards has an empty variant or an `sc-if` for an empty case. The only "Nothing to review" text is in LaunchChain (l.149), about a chain step.
  - ui-spec §10.2: "Every pattern has the states of §3: empty, loading, error, permission (view only)", but §3 defines only run states and the gauge.
  - api §6 single-user mode: `spectio serve` creates one project `default`, no runners, no workflows; "The UI hides the project switcher and sharing controls while there is a single project and user." Every Overview and Runs board shows the "demo-lab · all projects" switcher (Overview.dc.html:20, RunsTable.dc.html:20).
  - MOverview always shows 27 reviews, 3 active runs and "3 of 4 online".
- **Problem:** the first launch of a fresh `spectio serve` lands on undesigned screens with no next step. Implementers will improvise "0" cards, empty charts and possibly a red "Runners 0 / 0 online". The same applies to "no match for this filter" and "nothing to review".
- **Proposal:**
  - **OverviewFirstRun** (single mode, no switcher): a checklist Connect a runner → EnvConnect, Import a workflow → WorkflowImport, Launch, and "or run from your terminal with `-plugins nf-spectio` / `--logger spectio`"; zero-count "Needs attention" cards hidden.
  - **RunsEmpty:** "no runs yet" and "filters match nothing · Clear filters".
  - **ReviewQueueEmpty:** "Nothing waiting · 173 of 214 runs went straight through", plus the auto-approve rules.
  - **Workflows:** empty catalogue with the three sources; Discovered empty with "enable `nf-spectio` / `--logger spectio`". **Environments:** no environment yet (opens EnvConnect).
  - **Phone:** an MEmpty sheet with the same variants.
  - Build them with the shared `EmptyState` component (ui-spec §7).
- **Related:** R1 SR-041 already proposes defining the screen states (empty, loading, error, permission, n/a) in ui-spec and repointing §10.2. This finding adds the boards. Triage together.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-212 · major · The Legend and tokens cover run states only; boards invent colours and words for every other state family

- **Where:** Legend.dc.html and `design/tokens/spectio-tokens.css:37–44` (run states only); RunScheduler State column (x 638–780, y 680–1140); RunObserved live events (y 890–1030); LaunchBatch "start" column; AIAgents.dc.html:163; EnvStorage.dc.html:178; AdminBranding.dc.html:295–296; AdminHealth, AdminTasks, AdminBackups, AdminPlugins; MOverview, MEnvironments, MRunnerOffline, MAdmin, MMore; `spectio-tokens.css:47–49`.
- **Evidence:**
  - ui-spec §3.1: Running blue `#3B82F6`, Paused violet `#8B5CF6`, Succeeded green, Failed red; rail + icon + word "replaces the current pill badges".
  - AIAgents.dc.html:163 draws a model endpoint "Running" in `#157A4B` green, the Succeeded colour.
  - EnvStorage.dc.html:178 draws "Failed or paused" in red (`fg: '#B02A2A'`) with a pause icon, merging violet Paused into Failed.
  - RunScheduler draws job states as pill chips (OUT_OF_MEMORY, Pending, Running, Completing, Completed); "Completed" clashes with the task state "succeeded" (§3.1). LaunchBatch draws "Starts now" with the Running play icon.
  - Runner offline is drawn four ways on the phone: grey rail (MOverview attention card), red failed rail (MOverview Runners card, MEnvironments, MRunnerOffline), amber "1 offline" badge (MAdmin), red text (MMore). Runner states `online / draining / offline` (admin §3.2) have no token.
  - State words drift: "Review" vs "Awaiting review", "Done" vs "Completed" (Legend gauge), "waiting" vs "pending".
  - The Legend omits "stored" (§3.1), the Observed / Adopted levels, check verdicts and scheduler states. The tokens still name `--sp-section-settings` after the rename to Administration.
  - Hex values outside the tokens on phone boards: `#F2B544`, `#B06D07`, `#FFF8F8`/`#F2B8B8`, `#7FCFA6`, `#C9EBD8`; two primary styles (`#7750D4` vs `#A580F8` on dark); no board renders in dark mode.
- **Problem:** green means Succeeded on run boards and Running on AIAgents; red, reserved for Failed, marks infrastructure states; the Branding preview teaches the wrong state words; each of six or more families gets its own palette.
- **Proposal:**
  - Add a "System states" section to the Legend and the tokens, mapping each family onto existing run-state tokens:

    | Run-state token | System states mapped to it |
    |---|---|
    | `running` | active, in progress, retrying |
    | `succeeded` | healthy, online, verified |
    | `review` | notice, draining, degraded, pending verification |
    | `failed` | offline, failed to load, dead |
    | `cancelled` | disabled |

  - Add Legend panels for scheduler job states and failure classes (in Spectio words, red only for failures), check verdicts (`--sp-check-*`), pre-start states (Starts now, Waits for a slot, Queued · quota, with the clock icon), origin and level chips (UI / API / CLI / Batch, Observed / Adopted).
  - Draw RunScheduler states as icon + word. On EnvStorage, split "Failed · keep while resumable" and "Paused · …" into two rows. On AdminBranding, use "Awaiting review" and "Succeeded".
  - Align phone state words with the Legend; replace stray hex with tokens; one primary button style; render one phone board with `data-theme="dark"`.
  - Alias `--sp-section-settings` as `--sp-section-admin`.
- **Related:** R12 UX-103 covers the check-state vocabulary itself (n/a, suspect, computing, muted).
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open
- **Merge note:** reviewers placed "degraded" differently (amber in (a) and (c), red in (b)). The table above follows (a) and (c), so red stays for hard failures; confirm at triage.

### UX-213 · major · Warning and failure differ only by colour in check summaries and on the phone decision screen

- **Where:** Overview "Waiting for you" (x 765–1045, y 320–545); ReviewQueue "Checks · worst item" (x 710–950, y 365–1180); MReview and MReviewCells gate checks (`/tmp/w1-scratch/phone/MReview.png`, x 28–46, y 310 and 358); MReviewQueue checks bar; MWorkflows last-run dot (`MWorkflows.dc.html:46`); MRunnerOffline heartbeat strip; ui-spec §1.
- **Evidence:**
  - ReviewQueue.dc.html:169–171: the text is `${p} / ${tot} pass · ${w + f} flagged` in both cases; only `cfg = … f ? '#B02A2A' : '#8F5806'` changes. Overview.dc.html:154 does the same, with no `aria-label`.
  - MReview.dc.html:146–147: "Objects per well" (amber, 93/96) and "Mean object size" (red, "3 outliers") both use `icon: I.warn`. MReviewCells has the same pattern.
  - MReviewQueue: green, amber and red bar segments, while the text and `aria-label` say only "9 / 12 pass".
  - MWorkflows: an 8 px dot whose meaning is only in `title="last run failed"`.
  - ui-spec §1 says state is never shown "as a colour alone"; WCAG 2.1 SC 1.4.1 (https://www.w3.org/TR/WCAG21/#use-of-color).
- **Problem:** a colour-blind reviewer cannot tell a failing check from a warning on the decision screen.
- **Proposal:**
  - Distinct icons: check / triangle / octagon-x for pass / warn / fail.
  - The severity in text: "6 / 8 pass · 1 warning · 1 failing"; "fail · 3 outliers" in the value column.
  - Show the same `checkLabel` on Overview.
  - Replace the workflow dot with the run-state icon and a short word ("Running · 27 runs"), or the stage gauge used on MRuns.
- **Related:** R12 UX-103 (additional check states); UX-212 (Legend panel for check verdicts).
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open
- **Merge note:** reviewer (a) rated its part minor; reviewer (c) rated it major because the phone decision screen uses the same icon for warn and fail. Kept as major.

### UX-214 · major · One tap on the phone turns on maintenance mode, and maintenance is invisible to phone users

- **Where:** `MAdmin.dc.html:41–42` (switch, x 318–364, y 222–250); every phone board (no banner); admin §1, §4.4, §5.
- **Evidence:**
  - MAdmin: `<span class="sw off" role="switch" aria-checked="false" aria-label="Maintenance mode">`, subtitle "Off · pauses launches and decisions". The same board says branding, plugins and backups "open read-only on a phone" (MAdmin.dc.html:61).
  - admin §4.4: "Choices: block new launches and gate decisions, or make the API read-only … A banner message with a preview, and an optional end time." "Announcement banner. Info or warning style, dates, dismissible per user." The desktop AdminMaintenance board has the choices, message, preview, Schedule and "Turn on now".
  - No phone board has a maintenance or announcement banner. admin §5 has `GET/PUT /maintenance` and `GET/PUT /announcements` under the admin prefix, and a public `GET /public-config`.
- **Problem:** a stray tap blocks every launch and gate decision for every user, with no message and no end time. Users then get refused with no explanation. The switch is not focusable either (UX-219).
- **Proposal:**
  - On MAdmin, replace the switch with a row that opens a bottom sheet (mode choice, message, end time, preview, pinned "Turn on maintenance" with typed confirmation), or make it read-only like Branding. When on, show the banner text and "End now".
  - A shared maintenance and announcement banner below MobileTopbar (and on desktop), info or warning, with end time and dismiss. Feed it to non-admins through the public config (extend `GET /public-config`) or a new public read endpoint in admin §5.
  - Disable primary actions with the reason while maintenance is on.
- **Related:** R1 SR-038 (which writes still work in maintenance); UX-229 (desktop Maintenance board).
- **Found by:** ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-215 · major · Administration has no single-user or untrusted-instance variant

- **Where:** all Administration boards; AdminNav; MAdmin; Projects.dc.html; admin §1; ui-spec §4.9.
- **Evidence:**
  - admin §1 (single-user): "Administration is always visible. People shows one user and the `personal` group, with a 'Set up sign-in' call to action."
  - admin §1: "Activity, Backups and Maintenance are hidden on untrusted instances." ui-spec §4.9 says the same for public or demo instances. No board shows this reduced nav, on desktop or on MAdmin.
  - Projects mixes viewpoints: "All I can see 6 / Mine / Shared with me" and a "My role" column, while admin §1 describes an "instance-wide list, including projects the admin is not a member of".
- **Problem:** single-user, the default for `spectio serve` (api §6), has no admin design, and the reduced nav of public and demo instances is undrawn.
- **Proposal:**
  - **AdminSingleUser:** Users shows one row and a "Set up sign-in" card leading to AdminSignIn (UX-202); the project switcher and sharing hidden (api §6).
  - An AdminNav variant and an MAdmin variant for `public` / `demo` with no Activity, Backups or Maintenance.
  - Projects: a "Not a member · admin access" role chip and an "All projects (admin)" filter.
- **Found by:** ux-reviewer (b), ux-reviewer (c) (untrusted MAdmin variant, from c308)
- **Status:** open
- **Merge note:** the non-admin part of the reviewer's finding moved to UX-201. Hiding Administration from non-admins applies to multi-user instances only, since admin §1 keeps it "always visible" in single-user mode.

### UX-216 · major · The launch flow is drawn two ways, Launch has no project picker, and boards disagree on gates

- **Where:** Launch (aside button x 1096–1416, y 580–625; Gates card y 278–345); LaunchReview (stepper x 290–1390, y 152–186; Gates panel x 1056–1416, y 200–635); RunDetail (Stages line, y 343–358).
- **Evidence:**
  - ui-spec §2: "Wizard: workflow → version → parameters (form from schema) → inputs → environment → review & launch". ui-spec §4.6 describes one form, with an aside and a Launch button. ui-spec §4.11 has a phone "Step wizard".
  - Launch has no stepper and launches from its aside. LaunchReview has a six-step stepper (`<nav aria-label="Launch steps">`, LaunchReview.dc.html:52, :185).
  - api §11: "Launch form: project and environment pickers filtered by grants". Launch has no Project field; LaunchReview shows Project with no "Change".
  - Gates for nf-core/rnaseq: Launch says "1 gate after stage 2 (spectio.yml)" (Launch.dc.html:232); ui-spec §5.1 says nf-core/rnaseq "declares none"; LaunchReview says the overlay "rnaseq-demo-lab v2 … declares none of them as a gate" (LaunchReview.dc.html:142); RunDetail says "lab overlay 'rnaseq-demo-lab' v2" with an auto-approved gate after stage 2 (RunDetail.dc.html:57).
- **Problem:** implementers cannot tell whether Launch is one page or a wizard, and the gate source and overlay version contradict each other across three boards.
- **Proposal:**
  - Settle it in ui-spec §2 and §4.6 (question for Thomas). Proposed: one parameters page, with the stepper as a progress header and "Review and launch" as the final step.
  - The Launch aside button becomes "Review and launch", with its disabled reason outside the button (UX-236).
  - A Project picker as the first aside row, hidden in single mode.
  - Gate label: "1 gate after stage 2 · lab overlay rnaseq-demo-lab vN", with one overlay version across Launch, LaunchReview and RunDetail.
- **Found by:** ux-reviewer (a)
- **Status:** open

### UX-217 · major · Workflow visibility per group is drawn, but the data model has no workflow grants

- **Where:** `WorkflowDiscovered.dc.html:159–162` ("WHO CAN SEE AND LAUNCH IT · demo-lab · launch · imaging-core · view · + Group", x 1020–1400, y 725–785); `WorkflowImport.dc.html:113` ("visible to demo-lab"); api §6, §7; admin §1.
- **Evidence:**
  - api §7: `workflows` has `project_id`; the only grant tables are `project_grants` and `environment_grants`.
  - admin §1 describes Content → Workflows as "catalogue and versions across projects".
- **Problem:** per-group view and launch rights on a workflow cannot be stored or enforced by `can()`, and whether the catalogue is per project or per instance is undefined.
- **Proposal:** choose one model and draw it (question for Thomas):
  - **(a) catalogue per project:** visibility follows the project; the boards drop the group chips. Recommended for the MVP.
  - **(b) instance catalogue with `workflow_grants`** `(workflow, group|project, view|launch)`, listed in api §6, with `GET/PUT /workflows/{id}/grants`.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-218 · major · Phone gate decisions have no confirmation, no undo, and no lost-update or partial-failure screen

- **Where:** MReviewQueue (inline Approve at x 279–363, y 352–386 and 472–506; "Approve 3" at x 263–373, y 712–756, MReviewQueue.dc.html:52); MReview and MReviewCells ("Apply and continue"); api §4, §5; ui-spec §4.11.
- **Evidence:**
  - api §4: "`ETag` / `If-Match` on gates, change sets and settings to prevent lost updates when two reviewers act at once."
  - api §5: `POST /gates/{id}/decisions` "(… with If-Match)", `POST /gates:bulk-decide`.
  - The boards have no confirmation sheet, no undo and no "decided by someone else" state.
- **Problem:** on a phone, a mis-tap on a pinned bar decides a gate. When two reviewers act at once the second gets 412, and no screen exists for it. A bulk decision can half-succeed with no report.
- **Proposal:**
  - "Approve 3" opens a bottom sheet listing the gates and their checks, then a 5-second undo snackbar.
  - A "Gate changed since you opened it" sheet (412): the other decision, then "Reload" or "Review again".
  - A bulk result sheet: "2 approved · 1 already decided by Bob".
  - Record the rules in ui-spec §4.11 "Review queue"; the desktop queue needs the same 412 and partial-result states.
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-219 · major · Custom switches, checkboxes, tabs, radios and sliders cannot be reached by keyboard

- **Where:** ARIA-role `<span>`s with no `tabindex` (counts per file; `sc-for` templates multiply them): SettingsUsers 8, WorkflowWatches 5; WorkflowImport, AdminBackups, AdminBranding, AdminMaintenance 2 each; WorkflowDiscovered, WorkflowOverlay, AdminGroups, AdminLogs, AdminTasks, MAdmin, MWorkflows 1 each; MRuns, MReviewQueue (pills); MReview, MMore (radios); MReviewCells (slider); MLaunch, MAdmin, MRunnerOffline (switches). Also `AdminMaintenance.dc.html:114, 115, 141`: switches with no role and no label.
- **Evidence:**
  - `AdminGroups.dc.html:129`: `<span class="cb …" role="checkbox" aria-checked="…" aria-label="Group admin">`, with the same label on every row; `:130`: the P.I. control is `<span title="Designate as P.I." style="color:#9A9EB0">`, not focusable, at 2.66:1 (below the 3:1 of WCAG 2.1 SC 1.4.11, https://www.w3.org/TR/WCAG21/#non-text-contrast); `:131`: every row's button is "Remove member".
  - MRuns, MWorkflows, MReviewQueue: `<span role="tab" aria-selected=…>` with no `tabindex` or `aria-controls`. MReview: `<span role="radio">` for Keep / Redo / Exclude. MReviewCells sample options have no role at all.
  - MReviewCells: `role="slider" aria-label=… aria-valuetext=…` (l.72) with no `tabindex`, `aria-valuenow`, `aria-valuemin` or `aria-valuemax` (APG slider pattern, https://www.w3.org/WAI/ARIA/apg/patterns/slider/).
  - MRunnerOffline "Notify me" is a `<label>` around a styled span with no input. MReview avatars and wells and MWorkflows' dot rely on `title=` only, which ui-spec §4.11 forbids ("nothing hover-only").
  - MMore and MProjectSwitcher sheets are `role="dialog"` with no `aria-modal`, and the tab bar behind them stays in the focus order.
- **Problem:** keyboard and screen-reader users cannot toggle maintenance, gates, important stages or group admin, designate a P.I., change a filter, decide an item or set a threshold. Identical labels make per-row actions ambiguous.
- **Proposal:**
  - Use native `<input type="checkbox|radio">` inside labels (as MRunDetail's pill tabs already do) or `<button role="switch" aria-checked>`; tabs as `<button role="tab">` with roving tabindex (APG tabs pattern).
  - Per-row labels: "Group admin: a.smith@example.org", "Remove a.smith@example.org". P.I. as `<button aria-pressed>` with an icon of at least 3:1.
  - A numeric field with −/+ beside each threshold slider.
  - Replace `title` with a visible label or a tap-to-open sheet.
  - Sheets: `aria-modal="true"`, a focus trap, focus returned to the opener.
  - Record the rules in ui-spec §4.11 and the canvas conventions, and add a lint in `tools/canvas` (see the proposed spikes). Changing CLAUDE.md needs Thomas.
- **Found by:** ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-220 · major · Touch targets below 44 px in the shared phone components and most phone boards

- **Where:** ui-spec §4.11 ("touch targets ≥ 44 px"). Measured from board CSS and the phone PNGs:

  | Element | Board | Size |
  |---|---|---|
  | Search, bell | MobileTopbar (`.mk`, l.18) | 40×40 |
  | Avatar | MobileTopbar | 32×32 |
  | Sheet close | MMore, MProjectSwitcher | 40×40 |
  | Filter and source pills | MRuns, MWorkflows (l.28) | 36 high |
  | Pill tabs | MRunDetail (`.pt`, l.17) | 38 high |
  | Segment tabs | MReview, MReviewCells, MReviewQueue | 38 high |
  | Metric segments | MReviewCells (`.mc-seg`) | 34 high |
  | Keep / Redo / Exclude | MReview | 38 high |
  | Inline Approve / Open, Launch, Promote | MReviewQueue, MWorkflows (l.49) | 36 high |
  | "Open" / "Move…" | MRunnerOffline | 40 high |
  | "All runs" link | MOverview | about 28 high |
  | Threshold thumb | MReviewCells | 28 |
  | Switches | MAdmin 46×28, MLaunch 50×30 | |
  | Sort-and-filter control | MRuns | 20 px svg, no hit area |
  | Plate wells ("tap a well") | MReview (`MReview-items.png`, x 42–364, y 268–470) | about 23×23 |

- **Evidence:** the table above. WCAG 2.2 sets 24 px at AA (2.5.8) and 44 px at AAA (2.5.5) (https://www.w3.org/TR/WCAG22/#target-size-minimum); ui-spec chose 44.
- **Problem:** the shared top bar fails on every phone screen, and the plate map, a core review interaction, is under half the rule.
- **Proposal:**
  - `.mk` and avatar hit areas 44×44 (the visual size can stay).
  - Pills, segments and inline buttons 44 high; the filter icon wrapped in a 44×44 button.
  - Plate map: tap a row to open a zoomed strip (12 wells, 44 px hit areas through spacing), or treat the map as an overview and decide from the flagged list.
  - Threshold thumb: a 44 px hit area plus −/+ steppers (UX-219).
- **Found by:** ux-reviewer (c), ux-reviewer (b)
- **Status:** open

### UX-221 · major · Three navigation models for one workflow, and two editors for one overlay

- **Where:** Workflows and WorkflowSnakemake (source pill bar "Catalog 18 · nf-core 124 · Snakemake catalog 2,300+ · Discovered 4", x 290–795, y 85–113, Workflows.dc.html:124–127; no tabs, no project switcher); WorkflowsCatalog (underline tabs "Catalog / Discovered from terminal runs", l.43); WorkflowVersions (tabs Overview · Versions · Parameters · Stages & gates · Software · Runs, l.164); WorkflowOverlay ("Draft · unsaved", l.45) vs WorkflowWatches ("Draft · 2 changes", l.48).
- **Evidence:**
  - ui-spec §4.7: "Detail: README, versions/tags, parameter schema (browsable), stages manifest (`spectio.yml`), required inputs, profiles, software versions…, runs". Only WorkflowImport mentions a README; no detail board shows one.
  - The WorkflowWatches breadcrumb is "…/ Lab overlay / Watches" (l.36), but WorkflowOverlay has no link to Watches.
- **Problem:** the detail page will be built twice; users switching between gates and watches lose their place; two draft indicators suggest two separate drafts of one `spectio.yml`.
- **Proposal:**
  - Adopt the WorkflowVersions tab set for every workflow detail, adding a README tab and "Stages & gates" with sub-tabs Stages · Watches; record it in ui-spec §4.7.
  - Move nf-core and Snakemake catalogue browsing into WorkflowImport only.
  - One overlay header with one draft state.
  - Rebuild Workflows and WorkflowSnakemake as the Overview tab.
- **Related:** R12 UX-123 (overlay versions, catalogue).
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-222 · major · Five boards still show the Tower protocol or `-with-tower` as the Nextflow route

- **Where:**
  - `RunScheduler.dc.html:59`: info banner (x 290–1416, y 262–310);
  - `RunObserved.dc.html:62` (banner, x 290–1416, y 242–358), `:101` (live-events source label, x 810–1022, y 857–872), `:187` ("Captured from the terminal" command, x 1055–1400, y 776–890);
  - `Profile.dc.html:76` (Nextflow snippet);
  - `WorkflowsCatalog.dc.html:109` (amber "4 discovered from terminal runs" tile, x 1050–1415, y 890–1070);
  - `WorkflowDiscovered.dc.html:114` ("How a workflow lands here" footer, x 290–990, y 980–1095).
- **Evidence:**
  - RunScheduler: "Task states come from Nextflow (Tower protocol, `nativeId`)".
  - RunObserved: "Events arrive through the Tower protocol, but no runner can read the launch directory"; "Tower protocol · last event 6 s ago"; the captured command ends with `-with-tower https://spectio.example.org/api/v1`.
  - Profile: `nextflow run nf-core/rnaseq -profile singularity -with-tower https://spectio.example.org/api`.
  - WorkflowsCatalog: "Seen in CLI runs (`-with-tower`, `--logger spectio`)". WorkflowDiscovered: "(`-with-tower` pointed at Spectio, or `--logger spectio`)".
  - Decision [0001](../decisions/0001-nextflow-through-nf-spectio.md) §Decision: "Nextflow reports to Spectio only through `nf-spectio` … The Tower protocol routes are not implemented." Its follow-up names these five boards for R7. api §5: "The Tower protocol routes `/trace/*` are not implemented". schedulers l.101: "`nativeId` (trace `native_id`, reported by `nf-spectio`)". ui-spec §6: "`-plugins nf-spectio`, or a `spectio` config profile/env set once by `spectio login`".
  - No phone board mentions Tower, Seqera or weblog (reviewer (c) searched every `M*.dc.html` and `Mobile*.dc.html`).
- **Problem:** users copy the Profile snippet and the "captured" command, and both point at routes that will not exist. The boards also present Spectio as a Tower endpoint, the positioning decision 0001 rejects.
- **Proposal:**
  - RunScheduler: "Task states come from the engine (`nf-spectio` for Nextflow, the logger plugin for Snakemake; `nativeId` = Slurm job ID)."
  - RunObserved: banner "Events arrive through `nf-spectio`…"; feed label "nf-spectio · last event 6 s ago"; command without `-with-tower`, showing `-plugins nf-spectio` or "nf-spectio enabled by `spectio login`".
  - Optionally a chip "also reporting to Seqera Platform (`-with-tower`)", marked **[to be validated]** until spike T2 shows both plugins in one run.
  - Profile: `nextflow run … -plugins nf-spectio` with `SPECTIO_TOKEN`.
  - WorkflowsCatalog and WorkflowDiscovered: "Seen in CLI runs (`-plugins nf-spectio`, or once with `spectio login` · Snakemake `--logger spectio`)".
  - Re-render the five boards.
- **Related:** R12 UX-116 still asks for "the launch host in the Tower payload"; it should be retargeted to `nf-spectio` at triage. UX-232 covers CLI runs on the phone.
- **Found by:** ux-reviewer (a), ux-reviewer (b); confirmed absent on phone boards by ux-reviewer (c)
- **Status:** open
- **Merge note:** reviewer (b) asked to re-render the docs media. `docs/assets/shots/` holds nine shots, none from these five boards, so only the boards change.

---

## Minor findings

### UX-223 · minor · Tab sets and run actions differ between variants of one screen and from ui-spec

- **Where:** RunDetail (actions x 1066–1396, y 115–157; tabs y 285–318); RunScheduler header (x 1304–1396, y 123–162); RunFailed, RunOutputs; EnvCapacity tabs (y 200); Environments, EnvStorage, EnvKubernetes.
- **Evidence:**
  - Actions on a running run: RunDetail shows "Pause after stage / Relaunch▾ / Cancel"; RunScheduler shows only "Relaunch▾". ui-spec §4.4 lists "Resume, Relaunch…, Cancel, Duplicate"; §4.6 renames Duplicate "Copy to a new launch".
  - RunDetail has 9 tabs (as ui-spec §4.4); RunScheduler, RunFailed and RunOutputs have 10, with Scheduler.
  - EnvCapacity has "Compute · Capacity · Storage · Software · Credentials · Limits · Activity"; ui-spec §4.8 lists no Capacity, while schedulers §10 (l.278) has "Environment → Capacity (board `EnvCapacity`)". The other environment boards have no Capacity tab.
- **Proposal:**
  - A state × action matrix in ui-spec §4.4 (Queued, Running, Awaiting review, Paused, Failed, Succeeded, Cancelled, Observed), using the §4.6 wording.
  - Add Capacity after Compute in ui-spec §4.8 (the owner) and link schedulers §10 to it; update the three environment boards.
  - Give RunDetail the Scheduler tab.
- **Related:** R1 SR-041 already proposes adding the Scheduler tab to ui-spec §4.4.
- **Found by:** ux-reviewer (a), ux-reviewer (b)
- **Status:** open

### UX-224 · minor · The project switcher appears on some boards and not others, with conflicting owners

- **Where:** shown on Overview, RunsTable, RunScheduler, RunFailed, RunObserved, RunOutputs; missing on RunsRows, RunDetail, ReviewQueue, Launch, LaunchReview, Workflows, WorkflowSnakemake, Environments, EnvStorage, EnvKubernetes, AdminBranding, AdminPlugins, AIAgents. Owners: "demo-lab / Liver time course" (WorkflowsCatalog, WorkflowDiscovered, WorkflowOverlay, WorkflowVersions), "rnaseq-core / Liver time course" (EnvCapacity and other Administration boards), "demo-lab / Cell lines" (WorkflowWatches). ShareDialog breadcrumb "Settings / Projects / …". MProjectSwitcher has no entry point.
- **Evidence:**
  - ui-spec §2 lists the top bar contents without a project switcher; api §11: "Project switcher in the top bar, hidden while there is one project"; api §6 hides it in single-user mode.
  - Projects shows Liver time course owned by `rnaseq-core`.
  - No phone board links to MProjectSwitcher; its backdrop subtitle "Liver time course · 41 runs" disagrees with MRuns ("312 runs · 4 active").
- **Proposal:**
  - Add the switcher to ui-spec §2 with the rule: shown on Overview, Runs, Review, Launch and Workflows; hidden on Environments, Administration and Profile; hidden with a single project.
  - One owning group per project across boards; ShareDialog breadcrumb "Administration".
  - Phone: make the top-bar title tappable, with a chevron, to open MProjectSwitcher.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-225 · minor · Boards disagree on shared data, which hides the version-skew warning

- **Where:** Environments, EnvKubernetes, EnvCapacity, AdminHealth, MAdmin, SettingsUsers, AdminGroups, Projects; MRuns, MRunnerOffline, MReviewQueue, MOverview, MEnvironments, MMore, MWorkflows; ui-spec §4.11.
- **Evidence:**
  - Runner versions: "Runner spectio-runner 0.1.0" (Environments.dc.html:60) vs the card's v0.4.0 and AdminHealth 0.4.0; EnvKubernetes runner 0.1.0. admin §3.2: "Version skew beyond one minor version shows a warning"; none is drawn.
  - Slurm: "SLURM 24.05" (Environments.dc.html:95) vs "Slurm 26.05" (EnvCapacity.dc.html:38).
  - Offline runners: "Workstation Offline 2 h" (Environments), "demo-lab … Draining 0.3.2" and "hpc-login-2 offline" (AdminHealth); hpc-login-2 offline "18 min" (MOverview, MEnvironments, MRunnerOffline) vs "14 min" (MAdmin).
  - Counts: MAdmin Users 23 / Groups 6 / Projects 9 vs 7 people (SettingsUsers), 7 groups (AdminGroups), 6 projects (Projects).
  - `sarek-trio-02` is Paused (MRuns), Running (MRunnerOffline) and waiting at a gate (MReviewQueue). nf-core/sarek 3.6.1 (MWorkflows) vs 3.10.0 (MRuns).
  - "Hello, Alice" (MOverview) vs "Good morning, Alice" (MMore backdrop). ui-spec §4.11's More sheet lists "Settings"; admin §0 renamed it "Administration".
- **Problem:** reviewers cannot tell intended states from mistakes, and the skew warning is never drawn.
- **Proposal:**
  - One shared fixture (environments, runners, runs, counts) for all boards (see the proposed spikes).
  - Draw the skew warning on the runner row and the environment header ("runner 0.3.2 · server 0.4.0 · update").
  - Change "Settings" to "Administration" in ui-spec §4.11.
- **Found by:** ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-226 · minor · Branding lets admins recolour status colours with no rule linking them to run states

- **Where:** AdminBranding: "Status colours 0 of 3 set" (x 526–1036, y 940–980) and the preview (x 1052–1416, y 380–780); admin §4.1; `spectio-tokens.css:37–44`.
- **Evidence:** admin §4.1 uses depictio's `BrandTheme` unchanged, including "status colours: `success`, `warning`, `danger`". Run states use fixed tokens (seven states). The panel shows no contrast check.
- **Problem:** it is undefined whether `danger` recolours Failed and the gauge, or only depictio-style alerts. A custom value can fall below AA.
- **Proposal:** in admin §4.1: `success`, `warning` and `danger` map to `--sp-state-succeeded`, `--sp-state-review` and `--sp-state-failed` (fg, bg and rail derived); the panel blocks values below 4.5:1 for `-fg` on white and on the dark surface; running, paused, queued and cancelled are not brandable.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-227 · minor · Boards show features outside the MVP without marking them

- **Where:** RunScheduler "Suggestions for the relaunch" / "Apply to relaunch" (tall render, y 1170–1560; l.137) and "Cluster capacity & limits" (l.99); RunDetail Lineage "Next: Open in depictio when reporting completes" (l.163); RunOutputs "Send to depictio" (l.117); LaunchReview pre-flight.
- **Evidence:** schedulers l.293 puts "capacity (L4), quotas, reservations, pre-flight, relaunch suggestions" in phase 1b. The [decision log](../decisions/log.md) (2026-10-26, MVP scope, l.318): "automatic hand-off to depictio comes later, not in 0.1".
- **Problem:** whoever plans 0.1 from the boards will over-scope it, or build an undefined trigger.
- **Proposal:** one phase-chip convention on boards (Profile already uses "MVP · … phase 2"), defined in ui-spec; an MVP variant of RunScheduler with layers L1–L3 and failure classes only; say whether a manual "Send to depictio" is in 0.1 (question for Thomas).
- **Related:** R12 UX-121 (pre-flight), R1 SR-023 (checks depend on depictio, which 0.1 lacks).
- **Found by:** ux-reviewer (a)
- **Status:** open

### UX-228 · minor · Runner tokens and the runner registry live in four differently named places

- **Where:** `Environments.dc.html:80` and `EnvKubernetes.dc.html:157` ("token created in Settings › Tokens"); `SettingsServiceAccounts.dc.html:77` ("(Environments › Runners)"); AdminNav "Runners" links to AdminHealth; SettingsUsers "Runners 4" tab.
- **Evidence:** api §6: "a one-time registration token becomes a rotating runner credential", via `POST /runners:register`. admin §0: "Settings" became "Administration", and personal tokens live in Profile. ui-spec §4.8 has no Runners tab.
- **Problem:** "Settings › Tokens" no longer exists, and users will look for runner tokens in Profile.
- **Proposal:** one route: Environment → "Connect a runner" (EnvConnect) issues the registration token; fix the copy on all four boards; Admin → Runners anchors to `AdminHealth#runners`; keep the Users → Runners tab read-only with a link to the environment.
- **Related:** R12 UX-124 covers the token's values, not where it comes from.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-229 · minor · The desktop Maintenance board contradicts admin §4.4

- **Where:** `AdminMaintenance.dc.html:233` ("Keep runners executing … Turn off only to stop the clusters too"); announcement tone "Info · Warning · Success" (x 1042–1400, y 330–365); the header switch (x 960–998, y 255) next to "Turn on now".
- **Evidence:** admin §4.4: "Runners keep executing running jobs either way"; "Announcement banner. Info or warning style".
- **Problem:** the board adds an option to stop the clusters that the spec rules out, a third banner tone, and two controls for one action.
- **Proposal:** remove the "Keep runners executing" option (recommended) or add it to admin §4.4 with its effect on runs; limit tones to Info and Warning; make the header switch a read-only status, with "Turn on now" and "Schedule" as the only actions.
- **Related:** UX-214 (phone), R1 SR-038.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-230 · minor · The phone top bar hard-codes the Spectio emblem, so branded instances lose their brand on phones

- **Where:** MobileTopbar (inline four-blade svg); MOverview greeting; MMore footer; admin §4.1; api §13.5.
- **Evidence:** admin §4.1 uses depictio's `BrandTheme` (`logo_mode`, `logo_url`, `logo_url_dark`, brand colours, per-project override) and says "'Powered by Spectio' shows when the Spectio wordmark is hidden". MobileTopbar has no logo or brand prop.
- **Problem:** a branded instance shows a branded desktop and an unbranded phone.
- **Proposal:** `logo` / `logoDark` / `logoMode` props on MobileTopbar, falling back to the emblem; "Powered by Spectio" in the More sheet footer when the emblem is hidden; section colours read from the branding layer; one branded phone variant using AdminBranding's "Demo Lab Spectio" preset. Mention branding in ui-spec §4.11.
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-231 · minor · Phone navigation dead-ends in desktop boards and `#` links

- **Where:** MMore, MAdmin, MEnvironments, MWorkflows, MOverview, MobileTopbar (l.36–37), MLaunch.
- **Evidence:**
  - 16 phone links open 1440 px boards: Profile, Projects, Workflows (detail), EnvStorage, Environments, EnvKubernetes, SettingsUsers, AdminGroups, SettingsServiceAccounts, AdminTasks, AdminLogs, AdminHealth, AdminBranding, AdminPlugins, AdminBackups, AdminMaintenance.
  - `href="#"` for search, the bell, Help & docs, Audit log, Add environment, "All 64 tools", outputs, the Discovered card, and Back / Next in MLaunch.
- **Problem:** no phone design exists for Profile (tokens, sign out), search, workflow or environment detail, or the read-only admin pages MAdmin promises.
- **Proposal:** add MProfile, MSearch (a sheet over `GET /search`), MWorkflowDetail, MEnvironmentDetail and a generic read-only MAdminSection; extend the ui-spec §4.11 screen table to cover them.
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-232 · minor · CLI-launched runs (`nf-spectio`) have no phone representation

- **Where:** MRuns, MRunDetail; ui-spec §6 (Observed / Adopted / Registered); decision 0001.
- **Evidence:** ui-spec §6 Observed: "No relaunch; a banner explains how to adopt the run". MRunDetail's facts show only "Launched · Alice · in UI", and its ⋯ menu always offers "relaunch, cancel, copy to a new launch" (MRunDetail.dc.html:47). No MRuns card has a CLI or Observed marker; the desktop has RunObserved.
- **Problem:** after decision 0001, every terminal Nextflow run arrives through `nf-spectio`; on the phone these runs look like UI runs and offer actions the API refuses.
- **Proposal:** a "CLI · observed" or "CLI · adopted" chip on run cards; an MRunDetail variant with the adopt banner and ⋯ limited to the level's actions; "Launched · alice@hpc-login-1 · terminal (nf-spectio)".
- **Related:** UX-222, R12 UX-116.
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-233 · minor · Phone boards only work at demo scale: large lists, large plates, long names

- **Where:** MRuns, MReviewQueue, MReview (Items), MReviewCells (Samples), MobileTopbar; also the desktop Workflows and Environments cards.
- **Evidence:** MRuns shows "All 312" with no paging or end-of-list marker; the MReview plate map is hard-wired to 8×12 (384 or 1,536 wells would give cells of about 11 px and 5 px); MReviewCells lists every sample although `GET /gates/{id}/items` is "paged, filterable" (api §5); truncated titles expose the full name only on hover. Reviewer (b) also asks for 60-character workflow and environment names and a 500-workflow catalogue.
- **Proposal:** infinite scroll with "Showing 50 of 312" and a jump to search; Items defaults to flagged first, paged through the API; the plate map is an overview for 96 wells, with a quadrant picker above that; a tap on a truncated title opens a details sheet; an MReviewItems-500 variant; long-name variants on desktop cards and breadcrumbs.
- **Found by:** ux-reviewer (c), ux-reviewer (b) (long names, large catalogue, from b205)
- **Status:** open

### UX-234 · minor · Phone pinned bars: content shows through, chips are clipped, Next stays enabled with an open issue

- **Where:** MLaunch, MReview, MReviewCells, MRuns; ui-spec §4.6, §4.11, §10.2 ("primary action disabled together with its reason").
- **Evidence:**
  - MLaunch (`/tmp/w1-scratch/phone/MLaunch.png`) shows "min_mapped_reads" between the action bar and the tab bar (y 760–772) and help text below the tab bar (y 830–844). The same 8 px transparent strip shows content on MRuns (y 836) and MReview Items (y 832).
  - MReview's change chips are cut mid-word ("tsv v", x 372) with `overflow:hidden` and no count.
  - MLaunch shows "2 required · 1 issue", but "Next: Where it runs" is enabled.
  - Top bar, action bar and tab bar take about 250 of 844 px; no `env(safe-area-inset-bottom)`.
- **Proposal:** an opaque backdrop under the tab bar covering the bottom inset (`padding-bottom: max(8px, env(safe-area-inset-bottom))`); a solid action-bar background; end the chip row with "+1"; disable Next with "Fix 1 issue in Input / output", or allow it with a warning (decide in ui-spec §4.6); hide the tab bar while a pinned action bar shows on Review and Launch detail.
- **Found by:** ux-reviewer (c)
- **Status:** open

### UX-235 · minor · Contrast failures on primary buttons, the Review badge, switches and helper text

- **Where and evidence** (ratios recomputed during the merge with the WCAG 2.x formula; thresholds per WCAG 2.1 SC 1.4.3, https://www.w3.org/TR/WCAG21/#contrast-minimum, and SC 1.4.11 for non-text):
  - `EnvCapacity.dc.html:147` "Continue to launch": white on `#EC5F87`, **3.20:1** (x 1258–1400, y 990–1025);
  - `MWorkflows.dc.html:38` "Promote" and the MobileTabbar Review badge (10.5 px bold): white on `#D9890B`, **2.79:1**;
  - `AdminMaintenance.dc.html:91` "Turn on now": white on `#B06D07`, **4.17:1**;
  - Launch.dc.html:145: disabled-button reason, white on `#C4C7D4`, **1.68:1**; the MAdmin switch off-track `#C4C7D4` on white, **1.68:1** (non-text, needs 3:1);
  - LaunchChain.dc.html:172: informative text `#9A9EB0` on white, **2.66:1**;
  - MAdmin group labels `#6E7287` on `#F7F7FB`, **4.45:1** at 12 px;
  - MReviewQueue warn segment `#F2B544` on the `#EEEFF5` track, **1.60:1**.
- **Problem:** the primary actions and the most visible counter in the app are among the least legible elements. A section colour is used as a button fill, which no token allows, and the review-state amber fills an action although the tokens say "Run-state colours never appear in the brand".
- **Proposal:** `--sp-accent` (`#7750D4`, 5.41:1) for primary buttons; section colours for tints and icons only; `--sp-state-review-fg` `#8F5806` (5.89:1) for amber fills such as the badge; `--sp-ink-400` for switch tracks; `--sp-text-faint` or `--sp-ink-500` for helper text; a 1 px divider between bar segments; a contrast check for `color` / `background` pairs in the board lint.
- **Found by:** ux-reviewer (a), ux-reviewer (b), ux-reviewer (c)
- **Status:** open

### UX-236 · minor · Focus ring, disabled state, active tab and truncated names on the core boards

- **Where and evidence:**
  - RunsTable.dc.html:38 and ReviewQueue.dc.html:55 set `outline: none` on search inputs, and the wrapping label has no `:focus-within` style (WCAG 2.4.7).
  - Launch.dc.html:145 is styled as disabled but is neither `disabled` nor `aria-disabled`, so screen readers announce it as active; its reason sits inside the button.
  - RunDetail.dc.html:50: the active tab has no `aria-current`.
  - RunsTable.dc.html:78: run names are cut ("rnaseq-3.27-validati…") with no full name in a `title` or accessible name.
- **Proposal:** `label:focus-within{outline:2px solid var(--sp-line-focus)}`; a real disabled button with the reason outside it, in a `--sp-text-secondary` line linked by `aria-describedby`; `aria-current="page"` on the active tab; the full name as the accessible name and in a visible detail on tap or focus.
- **Found by:** ux-reviewer (a)
- **Status:** open

### UX-237 · minor · Clipped columns and truncated instructions

- **Where and evidence:**
  - EnvStorage: the Locations table's last column (retention) is clipped at x 1080–1097, y 265–750, showing fragments such as "Lif rul be" and "Ke arc aft da" (`EnvStorage-tall.png`).
  - WorkflowSnakemake: the Rules table's Container column is clipped at x 975–1077, y 1060–1080 ("docker://snakem").
  - AdminRestore: the stepper truncates "Manifest and chec…", "Compare with live …", "Type the instance …" (y 232–247).
  - RunScheduler: `.tbl{min-width:1040px}` cuts the Elapsed column at 1440 px (x 1370–1416) with no scroll cue.
- **Problem:** retention, the key fact of a location, is unreadable, and the restore steps hide their instructions.
- **Proposal:** retention as a second line under the path, or an expandable row; `overflow-wrap:anywhere` on container references; shorter stepper subtitles, or the full text under the active step only; a sticky Task column on RunScheduler and CPU efficiency or Node hidden below 1440 px.
- **Found by:** ux-reviewer (b), ux-reviewer (a)
- **Status:** open

### UX-238 · minor · The Review boards call a run waiting at a gate "paused"

- **Where:** the Review header (x 390–860, y 172–188); the same text in ReviewAmpliseq, ReviewChip, ReviewCoverage, ReviewDashboard, ReviewMethyl, ReviewProteomics, ReviewReport, ReviewSignal, ReviewSmallRNA, ReviewTrio and ReviewViral.
- **Evidence:** the boards say "paused after stage 2 of 4 · waiting 47 min". ui-spec §3.1 defines Paused (violet) as "Stopped on request" and distinct from Awaiting review. The Legend says "Awaiting review · Gate after stage 2 · since 12 min".
- **Proposal:** header "Awaiting review · gate after stage 2 of 4 · 47 min" with the flag icon (§3.1 card rule); keep "paused" for the Paused state only.
- **Found by:** ux-reviewer (a)
- **Status:** open

### UX-239 · minor · The Health board's heartbeat timing and runner table disagree with the specs

- **Where:** `AdminHealth.dc.html:97` (Runners section, x 526–1416, y 1015–1345 in the 1440×2000 render).
- **Evidence:** the board says "Each runner sends a heartbeat every 15 s and is marked offline after 60 s". admin §3.2: "every 30 s … marked offline after 3 missed heartbeats". schedulers §10 (l.286): "Health → Runners shows each observer's layers, interval, last success and latency"; the table has only Version, Environment, Status, Heartbeat, Runs and Last error.
- **Proposal:** the spec values (30 s, offline after 90 s); an expandable row per runner with its observer layers (L1–L5), interval, last success, latency and stale state.
- **Found by:** ux-reviewer (b)
- **Status:** open

### UX-240 · minor · Creating a user shows a plaintext password instead of offering a sign-in link

- **Where:** SettingsUsers "Create user" panel (x 526–1202, y 1155–1540 in the 1800 px render; l.183–184): "Initial password k7Rv2qXm9LpT4w · Generate another · Copy".
- **Evidence:** auth §1: "admin-created users with `must_change_password`". auth §2: "a password reset sends a sign-in magic link that forces a password change"; sign-in links are "also shown on screen by an admin as a copyable link" for staging and demos.
- **Problem:** the default teaches admins to pass passwords around by hand when the spec already has a single-use link for this.
- **Proposal:** "Email a sign-in link (forces a new password)" as the default; "Set an initial password" as the secondary option; "Invite" with the same mechanism; an "Invited" chip with the link's expiry.
- **Found by:** ux-reviewer (b)
- **Status:** open

---

## Questions for Thomas

1. **Launch flow (UX-216).** One parameters page with a progress stepper and a final "Review and launch" step, or a true wizard as ui-spec §2 and the phone board say?
2. **Workflow catalogue (UX-217).** Per project (visibility follows the project, recommended for the MVP) or per instance with `workflow_grants`?
3. **Share links (UX-204, R5 SEC-117).** Who may create them: owner only, or owner and editor? Can a link guest decide a gate whose policy names a group?
4. **OIDC phasing (UX-202).** Profile says "SSO via OIDC in phase 2"; auth §0 has no phasing. Is OIDC in 0.1?
5. **MVP scope on boards (UX-227).** Is a manual "Send to depictio" in 0.1? Should boards carry a phase chip for 1b features (capacity, pre-flight, relaunch suggestions)?
6. **Phone notifications (UX-210).** Web Push through a PWA, or only email and Slack for phones?
7. **Maintenance (UX-229).** Remove the board's "Keep runners executing" option, as admin §4.4 implies, or add a "stop the clusters too" mode to the spec?
8. **Where new endpoints go (UX-202, UX-208).** api §5 or admin §5 for sessions, sign-in tests and admin outbox and audit routes? R1 SR-013 raises the same duplication.
9. **Launch Next with an open issue (UX-234).** Disabled with the reason, or allowed with a warning?
10. **Canvas conventions (UX-219).** May the keyboard rules (native inputs or `<button role=…>`, no hover-only `title`) be added to the board conventions in CLAUDE.md? Changing CLAUDE.md needs your approval.

## Proposed spikes

- **S-R7-1 · Board lint in `tools/canvas`.** A script over `design/ui-canvas/*.dc.html` that flags ARIA-role `<span>`s without `tabindex`, identical per-row labels, information only in `title`, `outline: none` without `:focus-within`, `color` / `background` pairs below 4.5:1 (3:1 for non-text) and phone targets below 44 px. Exit: the lint reproduces UX-219, UX-220, UX-235 and UX-236 on the current boards. Ends with a dated note in `docs/research/`.
- **S-R7-2 · Shared board fixture.** One JSON fixture (projects, environments, runners, runs, gates, counts) read by every board through `dc-import` or a shared script, so data agrees across boards (UX-225, UX-224). Exit: Environments, AdminHealth, MAdmin, MRuns and MRunnerOffline render from it with no contradiction.
- **S-R7-3 · Live data on a phone.** A throwaway page consuming an SSE stream with `Last-Event-ID` on iOS Safari and Android Chrome: what happens when the tab is suspended, the network drops and the screen locks; how fast the stale and reconnecting states can be detected (UX-205, UX-218). The same spike can check Web Push support for an installed PWA on iOS and Android (UX-210). All browser behaviour is **[to be validated]** until then.
- **S-R7-4 · Summary endpoints at scale.** Measure `GET /runs:summary` and a per-process aggregate over 100 000 tasks on SQLite (WAL) and Postgres, with and without `count=exact`, to decide whether totals are exact, estimated or dropped (UX-207).
- **Existing spike T2** ([`next-phase.md`](../playbooks/next-phase.md)) should confirm that `nf-spectio` and `nf-tower` run in one run before any board shows "also reporting to Seqera Platform" (UX-222).
