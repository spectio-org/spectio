# Spectio — authentication and access

Status: draft v0.1 · 2026-10-26 · author: Thomas Weber (with Claude)

**Step page:** [F4](../progress/W0/F4.md), how this spec was written and checked.

**Companion docs:**
- [`api-and-data-model.md`](api-and-data-model.md): principals, tenancy and roles (§6), plus depictio identity (§13). This spec owns the *sign-in methods, sessions, tokens and links*; §6 owns *who may do what*.
- [`admin-and-operations.md`](admin-and-operations.md): the Users and Settings screens.
- [`dev-environment-and-testing.md`](dev-environment-and-testing.md): auth tests, dev previews and access to the public instance.

**Source for depictio parity:** a code audit of depictio v1.19.2 (`docs/research/depictio-auth-2026-10-26.md`, file:line references).

## 0. Decisions in brief

1. **Same modes as depictio, same names.** Spectio offers:
   - `single` (one local user);
   - `local` (accounts with passwords);
   - `public` (temporary guests, optional access code);
   - `demo` (public + guided tour);
   - plus SSO and links on top: magic links, pipeline provisioning, OIDC (covering Google, EMBL SSO, LS Login, Keycloak), SAML 2.0, and trust of depictio tokens.
   
   An instance enables several sign-in methods at once.
2. **Magic links in three forms:**
   - **sign-in link** by email ("send me a link");
   - **hand-over link** printed by the CLI or at the end of a run, as depictio does;
   - **scoped share link**: one run, gate or project, one role, an expiry. Reviewers outside the instance and PR previews use this one.
3. **depictio's weak points are fixed, not copied:**
   - tickets and tokens stored only as hashes;
   - atomic single-use burn;
   - rate limits on mint and exchange;
   - refresh-token rotation with reuse detection;
   - server-side logout;
   - HttpOnly session cookies for the browser;
   - PKCE for OIDC;
   - provisioning through a scoped service account instead of a shared instance key.
4. **Every method has tests.** CI runs the full matrix: unit, API and Playwright end-to-end, with Keycloak (OIDC and SAML) and Mailpit (email) as containers. depictio has no end-to-end test for magic links, Google or SAML, and no Keycloak job in CI.

## 1. Instance modes (`SPECTIO_AUTH_MODE`)

| Mode | depictio equivalent | Behaviour | Typical use |
|---|---|---|---|
| `single` | `single_user_mode` | **One user.** Requests map to the one local user created at `spectio init`. There is no login page. **Network safeguard:** binds to `127.0.0.1` by default. On any other interface it requires a token (from `spectio login` or a link), because anyone who reaches the port would otherwise be the user (depictio's own risk note on shared login nodes). | Python bundle on a laptop or login node |
| `local` | standard mode | **Accounts.** Passwords hashed with Argon2id; rate limits per IP and per account; registration errors that do not reveal which accounts exist. **Flags:** `registration_disabled`; `password_login_disabled` (only when another method is enabled); admin-created users with `must_change_password`. | Small team server |
| `public` | `public_mode` | **Guests.** Visitors get temporary principals (`kind=guest`, sliding 24 h expiry, cleaned up on schedule), optionally behind `SPECTIO_AUTH_PUBLIC_ACCESS_CODE`, which is compared in constant time and rate-limited before the check. **Guests are read-only:** no launches, no gate decisions, no tokens. | Public demo |
| `demo` | `demo_mode` | `public` + guided tour + nightly data reset | the public demo instance (beta, EMBL Kubernetes) |

**SSO and links add to a mode; they do not replace it.**
- In `local`, users may sign in with a password, OIDC, SAML or a magic link.
- In `public` and `demo`, signed-in users keep their roles and guests stay read-only.

**Discovery.** `GET {root}/api/v1/auth/config` is public and lets the UI draw the sign-in page. It returns:
- the mode;
- the enabled methods, with their labels (for example `saml_login_label`);
- `access_code_required`;
- `registration_open`.

It never returns secrets.

## 2. Sign-in methods

| Method | How | Notes |
|---|---|---|
| **Password** | `POST /auth/login` → session | Argon2id; lockout back-off per account and per IP; a password reset sends a sign-in magic link that forces a password change |
| **Magic link: sign-in** | `POST /auth/magic-links` `{email}` → email through the `email` notifier; the response is always "if the address exists, a link is on its way" | 15-minute ticket. For staging and demos, also shown on screen by an admin as a copyable link |
| **Magic link: hand-over** | `spectio login --print-link`, or at the end of a provisioned run (§4) | Same ticket. The 15-minute clock starts when the link is handed out, not when the run started (depictio's design) |
| **Share link (scoped magic link)** | `POST /share-links` `{resource: run\|gate\|project, id, role: viewer\|reviewer, expires_in, max_uses, email?}` by a project owner or editor | Opens one resource with one role, without an account. The recipient becomes a **guest principal bound to that link**, or signs in to keep the access. Every use is audited. Revocable at any time |
| **OIDC** (plugin `auth-oidc`) | authorization code + **PKCE** + nonce; multiple providers (Google, EMBL SSO, LS Login, Keycloak) | `allow_create` follows `registration_disabled`; group claim sync like SAML |
| **SAML 2.0** (plugin `auth-saml`) | SP-initiated; strict mode; signed assertions; relay state stored server-side, keyed by AuthnRequest ID; replay rejection | Same settings keys and group sync (`memberOf` → `sso_managed`) as depictio; IdP-initiated only when explicitly enabled |
| **depictio trust** (plugin `auth-depictio`) | verify depictio's RS256 JWT with its public key, or call `/depictio/api/v1/auth/me` | Principal linked as `depictio:user/<id>` (`api-and-data-model.md` §13) |
| **CLI** | `spectio login`: browser flow on desktop, **OIDC device code** over SSH or HPC, or paste a token | Tokens stored in the OS keyring when available |

### 2.1 Magic-link and share-link safety

**Stored:**
- **Hashes only.** The server stores `sha256(ticket)`, never the ticket. A database leak therefore reveals no usable link (depictio stores tickets in clear).
- **256-bit random tickets.**

**Delivered:**
- **In the URL fragment** (`/auth/magic#t=…`), as in depictio. Fragments are never sent to servers, so tickets do not end up in logs or in `Referer` headers.
- **Exchanged by a JavaScript POST** after a **"Continue as `<email>`" confirmation screen**. Email and chat scanners that prefetch links, even ones that run JavaScript, therefore cannot consume the ticket.

**Redeemed:**
- **Single use,** burned atomically (`UPDATE … SET used_at=now() WHERE hash=? AND used_at IS NULL RETURNING …`). depictio's read-then-save allows two redemptions in parallel.
- **Expiry:** 15 minutes for sign-in links. For share links, set by their creator, maximum 30 days.
- **Rate limits** on minting (per email, per IP, per principal) and on exchange (per IP).
- **Optional browser binding:** for sign-in links, the exchange must come from the browser that requested the link (`SameSite=Strict` nonce cookie); other browsers get a "check your email on this device" message. On by default for `public` instances.
- **`next` limited to a same-origin path.**

**After use:**
- the session carries the link's **scope claim**, so a share link can never reach beyond its resource;
- the audit log records who created the link, each use (IP, user agent), and its revocation.

## 3. Sessions and tokens

| Credential | Lifetime | Storage | Notes |
|---|---|---|---|
| **Browser session** | 12 h idle / 7 d absolute | HttpOnly, Secure, `SameSite=Lax` cookie; a CSRF token on writes | Server-side session row, so logout revokes it. Not readable by JavaScript, unlike depictio's localStorage bearer |
| **Access token** (API, CLI) | 1 h | bearer JWT (EdDSA or RS256), with `aud`, `iss`, `sub`, `scp`, `jti` | Signing keys rotated, published at `/.well-known/jwks.json` |
| **Refresh token** | 30 d, **rotated on every use** | opaque; stored as a hash | Reuse of an old refresh token revokes the whole family (reuse detection; depictio's open TODO) |
| **Personal access token** | user-chosen, maximum 1 year | opaque, shown once; stored as a hash | Named and scoped (`runs:read`, `runs:launch`, `gates:decide`…), with last-used and IP |
| **Service-account token** | maximum 1 year, rotation with 24 h overlap | as above | For LIMS, CI, robots, agents (`admin-and-operations.md` §2.3) |
| **Runner token** | until revoked | as above, bound to one environment | Can only act for its environment's runs |
| **Run token** | the run's life + 24 h | as above | Issued to a provisioned run (§4) or an engine plugin; ingest only, for that run |
| **Embed token** | ≤ 1 h | JWT bound to one resource and origin | `api-and-data-model.md` §9 |

## 4. Pipeline provisioning (passwordless users from a pipeline or LIMS)

depictio's flow (provisioning key → passwordless user → long-lived token → login link at the end) is kept for the user, with tighter mechanics:

1. **A service account** with scope `principals:provision` replaces the shared instance key. It belongs to a group, and it can only provision into the projects it may share. In depictio, a key holder can provision any email, including an admin.
2. **`POST /principals:provision`** `{email, display_name?, project_id, role}` is idempotent:
   - it creates or gets a **passwordless** user and grants the role on the project;
   - it **never** returns credentials for an existing admin or for any principal with more rights than the grant;
   - it is rate-limited, compared in constant time and audited.
3. **The run executes with a run token,** scoped to that run and expiring with it, instead of a one-year token.
4. **At the end of the run,** Spectio sends a sign-in magic link to the user, by email and in the run's `--result-json`. The link opens the run, or the gate waiting for them.

The same flow serves `depictio-cli ingest --user` when Spectio hands a run to depictio: the sink plugin calls depictio's `POST /auth/provision_user` with depictio's key (`api-and-data-model.md` §13.3).

## 5. Admin and UI

**Sign-in page:**
- the SSO buttons first (SAML label, OIDC providers), then "Email me a sign-in link", then password;
- the access-code gate for `public` instances;
- "Starting your session" in `single` mode.

This is the same order and wording as depictio (`SignInProviders.tsx`, `PublicAccessGate.tsx`).

**Share dialog:** besides users and groups, a "Create link" tab (role, expiry, maximum uses, optional email), with a list of active links and their uses, and a Revoke button.

**Administration → Settings → Sign-in:**
- the methods with their status, and test buttons (for example "Send me a test link", "Test SAML metadata");
- token lifetimes;
- rate limits;
- active sessions per user, with "sign out everywhere".

## 6. Tests (every method, in CI)

| Method | Unit and API | End-to-end (Playwright) | Service in CI |
|---|---|---|---|
| single | localhost binding; refusal on non-loopback without a token | open the UI with no login | — |
| local | Argon2id, lockout, generic errors, `must_change_password` | register, login, logout, reset by link | Mailpit |
| public / demo | access-code timing, guest read-only, expiry and clean-up | guest session, code gate, guided tour | — |
| magic sign-in link | hash at rest, atomic burn under concurrency (two parallel redemptions → one wins), expiry, rate limits, `next` validation | request → Mailpit → click → confirm → session; replay rejected | Mailpit |
| share link | scope claim enforced on every endpoint family; revocation; max uses | open a gate as an external reviewer, decide, see the audit entry | — |
| provisioning | no admin escalation; idempotency; run-token scope | run ends → email link → lands on the run | Mailpit |
| OIDC | PKCE, nonce, state replay, group claim sync | login against Keycloak, group mapped | Keycloak |
| SAML | signature required, replay rejected, relay from server | login against Keycloak (SAML client), `memberOf` sync | Keycloak |
| depictio trust | signature and audience checks, principal link | login in depictio, then open Spectio with the same session | depictio container (nightly) |
| tokens | refresh rotation and reuse detection, revocation, scopes | CLI device-code login against Keycloak | Keycloak |

The Keycloak realm (`tests/auth/keycloak-realm.json`) defines test users, groups (`rnaseq-core`, `imaging-core`) and both an OIDC and a SAML client. The Compose test profile `auth` starts Keycloak and Mailpit next to Spectio.
