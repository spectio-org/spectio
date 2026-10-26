# depictio — authentication and access modes (audit for Spectio)

Source: depictio checkout `scratchpad/dep`, v1.19.2 (commit `0d1aa0a`, 2026-10-23). Read on 2026-10-26.

Paths are relative to `dep/depictio/` unless they start with `docs/` or `packages/`. Short names:
- `routes.py` is `api/v1/endpoints/user_endpoints/routes.py`;
- `core.py` is `api/v1/endpoints/user_endpoints/core_functions.py`;
- `settings` is `api/v1/configs/settings_models.py`.

**[inf]** marks an inference that was not tested by running the code.

## 1. Configuration surface (`AuthConfig`, `settings:412–730`, env prefix `DEPICTIO_AUTH_`)

| Setting | Default | Effect |
|---|---|---|
| `keys_dir`, `keys_algorithm` (`RS256`/`RS512`/`ES256`/`SHA256`) | generated keys | JWT signing (§7) |
| `internal_api_key_env` | auto-generated | service-to-service key (§8) |
| `provisioning_api_key_env` | **unset → feature off** | pipeline provisioning gate (§5); never auto-generated (`settings` `provisioning_api_key` property) |
| `magic_link_expiry_minutes` | 15 | magic-link ticket TTL (`settings:436`) |
| `single_user_mode` | false | §2.1 |
| `public_mode` (alias `unauthenticated_mode`) | false | §2.3 |
| `demo_mode` | false | §2.4 |
| `registration_disabled` | false | blocks `/register` and SSO auto-creation |
| `password_login_disabled` | false | blocks password login, **only if** Google or SAML is enabled (`is_password_login_disabled`, `settings` ~688) |
| `public_access_code` (SecretStr) | none | shared code gating public mode (§2.3) |
| `anonymous_user_email` | `anonymous@depict.io` | anonymous identity |
| `temporary_user_expiry_hours/minutes` | 24 / 0 | guest lifetime |
| `google_oauth_*` | off | §6.1 |
| `saml_*` (entity IDs, SSO URL, cert, NameID format, attribute names for email/username/groups/title/display name/login, `saml_login_label`) | off | §6.2 |

- **Env parsing.** The modes are re-read from raw env vars in `__init__` (`settings:596–640`), because nested BaseSettings miss them otherwise.
- **Public discovery.** `GET /auth/me/optional` (`routes.py:619–742`) tells the SPA everything in one call, without a token:
  - `auth_mode` (`single_user` | `unauthenticated` | `standard`);
  - the mode flags, the effective `password_login_disabled`, and `public_access_code_required` (never the code itself);
  - `google_oauth_enabled`, `saml_enabled`, `saml_login_label`, the temp-user expiry;
  - feature flags.

## 2. Instance modes

### 2.1 Single-user mode
- **Seeding.** Bootstrap seeds a local admin (`admin@example.com`, random password never logged) when no admin exists (`api/v1/db_init.py:785–800`).
- **Login.** `/auth/login` returns a token for that admin with no credentials checked (`routes.py:185–195`).
- **Data endpoints** fall back to the anonymous user when no token is sent (`get_user_or_anonymous`, `routes.py:124–157`).
- **Anonymous session.** `GET /auth/public/get_anonymous_user_session` is enabled only in this mode and is rate-limited (`routes.py:985–1009`).
- **Disabled here:** `/register` (`routes.py:1043`), provisioning and magic links (`_require_magic_link_enabled`, `routes.py:312–324`).
- **CLI config generation** is limited to the admin (`routes.py:1435–1444`).
- **UI:** the SPA shows "Starting your session" (`viewer/src/auth/AuthApp.tsx:139`).

### 2.2 Standard mode (accounts)
- **Password login.** `POST /auth/login` (OAuth2 password form):
  - per-IP rate limit (`routes.py:181`);
  - bcrypt check (`core.py:750–778`);
  - issues a short-lived session (`routes.py:206–222`).
- **Registration.** `POST /register` (`routes.py:1012–1087`):
  - refused in single-user or public mode, when `registration_disabled` is set, and when password login is disabled;
  - rate-limited;
  - never honours a client-sent `is_admin`;
  - **every failure returns the same generic error**, so accounts cannot be enumerated (`routes.py:1006–1010`).
- **Admin-created accounts.** `POST /auth/admin/create_user` with `must_change_password` (`routes.py:1089–1140`). The flag is returned by `/me/optional` and cleared on password change (`core.py:686`).
- **Password change:** `POST /auth/edit_password` (`routes.py:1191`).

### 2.3 Public mode (guests)
- **Guest sessions.** `POST /auth/public/create_temporary_user` (`routes.py:948–983`):
  - only in public mode (404 otherwise);
  - rate-limited before the access-code check, so the code cannot be brute-forced faster than other credentials;
  - verifies `public_access_code` in constant time (`settings` `verify_public_access_code`, ~667–675).
- **Temporary users.** Each guest gets a fresh user `temp_user_<8 hex>@depictio.temp` with a random bcrypt password and `is_temporary=True`, expiring after 24 h by default (`core.py:104–141`).
- **Sliding expiry.** Every refresh re-arms the expiry (`_rearm_temporary_user_expiry`, `routes.py:261–278`), so an active visitor never lapses. Abandoned sessions stop after the refresh token's 7-day lifetime.
- **Clean-up.** Expired guests are deleted by a periodic task (`api/v1/tasks/cleanup_tasks.py:53`, `core.py:195`).
- **UI.**
  - With a code: `PublicAccessGate.tsx`, "Enter the access code", field "Access code".
  - Without one: "Starting a guest session" (`AuthApp.tsx:131,139`).
  - Guests are flagged `is_temporary` so the SPA can offer a real sign-in.
- **Elsewhere.** Monitoring and backups are hidden in public mode, and so is CLI config for non-admins (`routes.py:1435`).

### 2.4 Demo mode
- `demo_mode` adds a guided tour on top of public mode (`settings` `is_demo_mode`).
- The property returns `demo_mode` alone. **[inf]** Demo mode on its own does not imply `is_public_mode`; deployments set both. The e2e test `tests/e2e-playwright/tests/public/demo-mode.spec.ts` exists.
- `DEPICTIO_WALKTHROUGH_DISABLED` and `DEPICTIO_DEV_MODE` suppress the tour (`routes.py` in `/me/optional`).

## 3. Sessions and tokens (JWT)

- **Model.** `TokenData` is `name`, `token_lifetime` ∈ `short-lived` / `long-lived` / `permanent`, `token_type` ∈ `bearer` / `custom`, and `sub` = user ObjectId (`models/models/users.py:12–53`).
- **Signing.** JWTs are signed with the configured private key (`utils.py:119–142`, `get_private_key`). The claims are the `TokenData` fields plus `exp`.
- **Verification.** It pins `algorithms=[ALGORITHM]` and requires `exp` (`core.py:416–440`). The token must then also exist in `TokenBeanie`, which makes revocation possible (`core.py:454`).
- **Lifetimes** (`_add_token`, `core.py:697–745`):

| Kind | Access token | Refresh token | Issued by |
|---|---|---|---|
| short-lived | 1 h | 7 days | login, Google, magic-link exchange, single-user login |
| long-lived | 1 year | 1 year + 7 days | CLI tokens `POST /auth/me/tokens` (`routes.py:1260–1300`), pipeline provisioning |
| permanent | JWT exp 1 year, stored expiry `datetime.max`, no refresh | — | API only |

- **Refresh.** `POST /auth/refresh` (`routes.py:392–443`) is browser-safe: the refresh token is the only credential, and it returns a new 1-hour access token. **No rotation and no reuse detection:** an explicit `TODO(PR2)` says a leaked refresh token grants indefinite access (`routes.py:413–420`).
- **Browser storage.** The session is kept in **localStorage** (`persistSession`, `packages/depictio-react-core/src/api.ts:3953`). A bearer header means there is no CSRF surface, but XSS can read the token.
- **Logout** only removes the client copy; the code comment says "there is no server-side revocation" (`api.ts:3962–3966`). `DELETE /auth/me/tokens/{id}` revokes CLI tokens (`routes.py:1304`).
- **Storage.** Tokens (access and refresh JWTs) are stored **in clear** in `TokenBeanie` for lookup **[inf from `find_one({"access_token": token})`]**.

## 4. Magic links

- **Model** (`models/models/users.py:153–183`): `MagicLinkTicket` holds `ticket` (`secrets.token_urlsafe(32)`), `user_id`, `expire_datetime`, `used`, `created_at`.
  - The ticket has a unique index and a Mongo TTL index on `expire_datetime`, so used and expired tickets disappear without a clean-up job.
  - **The ticket is stored in clear, not hashed.**
- **Mint.** `POST /auth/me/magic_link` (`routes.py:360–383`):
  - bearer-authenticated, so the caller is the user the link logs in;
  - TTL `magic_link_expiry_minutes` (15);
  - returns `{ticket, expire_datetime, login_url}` with `login_url = <viewer>/auth/magic#ticket=…`.
- **Redeem.** `POST /auth/magic/exchange` (`routes.py:385–389`, `core.py:936–985`):
  - rejects missing, used or expired tickets with 401;
  - sets `used=True`, then mints a **short-lived** session for the ticket's user;
  - the burn is `find_one` then `save()`, not an atomic find-and-update. **[inf]** Two concurrent redemptions can both succeed.
  - **No rate limit** on this endpoint. The 256-bit secret makes guessing impractical.
- **Delivery.**
  - There is **no email sending anywhere** (no SMTP or mail settings; a grep for smtp/mail found only a sandbox blocklist).
  - The link is printed by the CLI at the end of `depictio ingest --user` (`cli/cli/commands/run.py:2750–2761`, `utils/api_calls.py:129`), with `&next=/dashboard/<id>` appended.
  - SAML reuses the same mechanism internally (§6.2).
  - There is **no** "email me a sign-in link" form in the UI.
- **Scope.** The ticket logs in as the full user, with no resource or role restriction. The resulting session is a normal one.
- **Browser side** (`viewer/src/auth/components/MagicLinkCallback.tsx`):
  - reads the ticket from the **fragment**, so it stays out of server logs and Referer;
  - strips it from history immediately;
  - POSTs the exchange;
  - restricts `next` to a same-origin path (`safePostAuthTarget`, `postAuthTarget.ts`).
- **Link scanners.** Because the ticket sits in the fragment and needs a JS POST, email or chat link scanners doing GET prefetch cannot consume it **[inf]**.
- **Off in single-user mode** (`routes.py:312–324`).

## 5. Pipeline provisioning (passwordless accounts)

Documented in `docs/pipeline-provisioning-magic-link.md`.
1. **Configure.** Set `DEPICTIO_AUTH_PROVISIONING_API_KEY` and `DEPICTIO_VIEWER_PUBLIC_URL`. TLS is required.
2. **Provision.** `POST /auth/provision_user` with header `api_key` and body `{email}` (`routes.py:327–357`). It is off in single-user mode and returns 503 when no key is configured, 403 on a wrong key (`routes.py:296–309`).
3. **What it creates.** `_provision_user` (`core.py:872–912`) creates or gets the user with an **empty password** (unusable), and reuses a long-lived token named `pipeline_provision` while it has more than one day left. It is idempotent.
4. **Run as the user.** The CLI writes a temporary `0600` CLI config, runs the ingest *as* the user, then mints a magic link *as* the user at the end, so the 15-minute clock starts when the link is handed out.
5. **Security model** (doc):
   - the key is an instance gate against bots, not isolation between users;
   - the link carries only the single-use ticket, and the session is minted at click time.
6. **Gaps.**
   - The provisioning key is compared with `!=` (`routes.py:307`), not in constant time, unlike `internal_api_key` (`routes.py:89–99`, `hmac.compare_digest`).
   - The endpoint is not rate-limited.
   - Anyone holding the key can mint a one-year token for any email, including an existing admin's **[inf: `_provision_user` returns the existing user without checking `is_admin`]**.

## 6. Single sign-on

### 6.1 Google OAuth (`api/v1/endpoints/auth_endpoints/google_oauth_routes.py`)
- **Start.** `GET /auth/google/login` returns `{authorization_url, state}` (`:37–78`). The state comes from a Redis-or-memory store with a 600 s TTL and atomic consume (`state_store.py:23,61`).
- **Callback.** `GET /auth/google/callback?code&state` (`:81–180`):
  - validates the state (CSRF), exchanges the code, fetches userinfo;
  - creates or gets the user with `allow_create = not registration_disabled`;
  - syncs the avatar and returns a short-lived session as JSON. The SPA route `GoogleOAuthCallback.tsx` performs the call.
  - No PKCE parameter is visible in the login URL **[inf from `:62–75`]**.
- **Tests:** 17 in `tests/api/v1/endpoints/auth_endpoints/test_google_oauth.py`.

### 6.2 SAML 2.0 (`saml_routes.py`, `saml_utils.py`; extra `depictio[saml]` = `python3-saml`)
- **SP-initiated login.** `GET /auth/saml/login?next=` (`saml_routes.py:58–81`):
  - `next` is constrained to a same-origin path (`safe_relay_path`, `saml_utils.py:47–51`, which rejects `//`);
  - the relay is stored server-side, keyed by the AuthnRequest ID, so the IdP-echoed RelayState is never trusted.
- **ACS.** `POST /auth/saml/callback` (`:84–146`):
  - consumes the stored request ID, which rejects replays and unsolicited responses;
  - validates with `strict: True` and `wantAssertionsSigned: True` (`saml_utils.py:61,83`);
  - resolves the email from the configured attribute, falling back to the NameID, lower-cased (`saml_utils.py:151–160`);
  - creates or gets the user (respecting `registration_disabled`) and syncs groups and profile;
  - issues a **2-minute magic-link ticket** and redirects 303 to `/auth/magic#ticket=…&next=…`.
  
  The session is therefore never in a URL or form post.
- **Metadata:** `GET /auth/saml/metadata` serves the SP metadata (`:149`).
- **Group sync** (`sso_sync.py:22–168`):
  - groups named in the `saml_attribute_groups` attribute (e.g. `memberOf`) are created with `sso_managed=True` and the user is added;
  - the user is removed from every `sso_managed` group not asserted, including `admin_ids`, and `pi_id` is cleared;
  - manual groups are never touched;
  - title, display name and login are refreshed;
  - pending P.I. claims run on login (`groups_endpoints/pending_pi.py`);
  - a sync failure never blocks the login.
- **Tested against Keycloak** in `dev/dev_fastapi_saml/app.py`. Unit tests: 22 in `test_saml.py`, 13 in `test_sso_sync.py`, 9 in `test_auth_state_store.py`. No Keycloak job runs in CI **[inf: no `keycloak` match under `.github/`]**.
- **UI** (`viewer/src/auth/components/SignInProviders.tsx`):
  - the SAML button comes first (`saml_login_label`, default "Sign in with SSO"), then "Sign in with Google";
  - when password login is disabled the form says "This instance signs in with Google." (`LoginForm.tsx:224–245`).

## 7. Keys
- RSA (or EC) key pair in `keys_dir`, generated on first boot (`api/v1/key_utils.py`). Kubernetes takes them from a Secret (`kubernetes/multiline-secrets.yaml`: `AUTH_PUBLIC_KEY`, `AUTH_PRIVATE_KEY`).
- The token comment notes that keys from a different deployment cause "Signature verification failed" (`core.py:448–451`).
- `keys_algorithm` accepts `SHA256`, which is not a JWT signing algorithm **[inf: probably unused]**.

## 8. Service-to-service and the CLI
- **`internal_api_key`.**
  - Auto-generated and persisted with the keys unless set by env.
  - Compared in constant time (`routes.py:89–99`).
  - Used by deprecated server-side routes (`/create_temporary_user`, `/refresh_token`, temp-user clean-up).
- **CLI tokens.** `POST /auth/me/tokens` creates a named long-lived token (`routes.py:1260–1300`). `POST /auth/generate_agent_config` returns a CLI config that includes **the S3 root secret** (`routes.py:1422–1447`), restricted to admins in single-user, public and demo modes.
- **Rate limiting** (`user_endpoints/rate_limit.py`):
  - Redis fixed window of **10 calls per 60 s** per `(IP, endpoint)`;
  - **fail-open** when Redis is down;
  - the client IP is taken from **`X-Real-IP`** (trusted proxy header). If the API is reachable without the proxy, that header can be spoofed to dodge the limit **[inf]**.
  - Applied to login, register, temp-user creation and the anonymous session. **Not** applied to magic exchange or provisioning.

## 9. Tests that exist

| Area | Unit / API tests | Playwright e2e (`tests/e2e-playwright/tests/`) |
|---|---|---|
| Password login, register, edit password, logout, session expiry and refresh, token login | `user_endpoints/test_routes.py`, `test_user_management.py`, `test_admin_create_user.py` | `auth/auth-ui-login`, `auth-ui-registration`, `edit-password`, `logout`, `session-expiry`, `session-refresh`, `token-login` |
| Single-user | — | `auth/single-user-mode.spec.ts` |
| Public, demo | — | `public/public-mode.spec.ts`, `public/demo-mode.spec.ts` |
| CLI configs | `test_agent_config_utils.py` | `auth/cli-configs.spec.ts` |
| Provisioning + magic link | `test_provisioning.py` (9: blocked in single-user, passwordless create, idempotent, ticket create, redeem burns, replay rejected, expired rejected, unknown rejected) | **none** |
| Google OAuth | `test_google_oauth.py` (17) | **none** |
| SAML + SSO sync | `test_saml.py` (22), `test_sso_sync.py` (13) | **none** (manual Keycloak dev app) |

## 10. Parity table for Spectio

| Mode | depictio behaviour | Spectio equivalent (proposal) | Gaps / risks to fix in Spectio |
|---|---|---|---|
| Single-user | anonymous fallback maps to the seeded local admin; no login UI; provisioning and magic links off | `auth: single`; local requests map to the one user; bind to 127.0.0.1 by default | depictio admits anonymous requests from any host that can reach the port (its own risk note on shared login nodes): require localhost binding, or a token, when not on loopback |
| Standard (password) | bcrypt, per-IP rate limit, generic register errors, `registration_disabled`, `password_login_disabled` only when SSO exists, admin-created users with `must_change_password` | `auth: local`, same flags and semantics, same field names | add an account lockout or back-off per account, not just per IP; Argon2id or bcrypt |
| Public / guests | temporary users with sliding 24 h expiry, optional constant-time `public_access_code`, clean-up task | `auth: public` for demo instances only (read-only by default; no launches for guests) | guests should never launch runs or decide gates; cap guest count |
| Demo | public + guided tour | same flag, for the staging instance | — |
| Magic link (sign-in) | 256-bit ticket, 15 min, single use, fragment delivery, JS POST exchange, safe `next`; minted only by the user's own bearer (CLI, SAML); **no email**; full-user scope | (a) **email sign-in link** ("send me a link") through the email notifier; (b) **CLI or end-of-run link** like depictio; (c) **scoped share link** (one run or gate, a role, an expiry) for reviewers and PR previews | store only **a hash** of the ticket; **atomic** burn (`UPDATE … WHERE used = false`); rate-limit mint and exchange; add a "Continue" confirm step for email links in case scanners run JS; bind to the requesting browser optionally; a scope claim in the session |
| Pipeline provisioning | shared `provisioning_api_key` → create-or-get passwordless user + 1-year token; CLI ingests as the user and prints a login link | **service account with scope `principals:provision`** (no shared instance key); provisioned principals get **run-scoped** tokens (expire with the run); login link via magic link | constant-time compare; rate limit; never provision or impersonate admins; audit every provision; shorter tokens |
| Google | OAuth code flow, state store with TTL, `allow_create` respects `registration_disabled`, avatar sync | generic **OIDC** plugin (Google, EMBL SSO, LS Login, Keycloak) with **PKCE** and nonce | depictio has no generic OIDC and no PKCE visible |
| SAML | SP-initiated, strict, signed assertions, server-side relay by request ID, 2-min ticket to fragment, `memberOf` group sync with `sso_managed` | **SAML plugin** with the same keys and behaviour (`api-and-data-model.md` §13) | also accept IdP-initiated only if explicitly enabled; add a CI job with Keycloak (depictio has none) |
| depictio trust | — | accept depictio JWTs (RS256 public key or `/auth/me`), principal link `depictio:user/<id>` | key distribution and rotation |
| CLI and API tokens | named long-lived (1 year) JWTs; agent config includes the S3 root secret | named, scoped, expiring tokens; device-code login; no storage secrets in config | refresh rotation with reuse detection (depictio TODO); hashed token storage; server-side logout |
| Sessions in the browser | localStorage bearer + refresh (1 h / 7 d), no server-side logout | HttpOnly `SameSite=Lax` session cookie for the UI with CSRF token on writes; bearer for API/CLI | XSS token theft risk in depictio's model |
| Service-to-service | `internal_api_key` (auto-generated) | service accounts and runner tokens per environment | no single shared instance key |
