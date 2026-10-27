# Spectio — telemetry, install tracking and analytics

Status: draft v0.1 · 2026-10-26 · author: Thomas Weber (with Claude)

**Step page:** [F6](../progress/W0/F6.md), how this spec was written and checked.

**Companion docs:**
- [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2: the `spectio.analytics` plugin kind.
- [`admin-and-operations.md`](admin-and-operations.md): the Settings screens where these switches live.
- [`cli-and-shared-libraries.md`](cli-and-shared-libraries.md): the telemetry consent helper in `bioplatform-client`.
- [`documentation-system.md`](documentation-system.md) §1: analytics on the docs site.

**Source:** an audit of depictio at `0d1aa0a` and of the tools' own docs (`docs/research/budget-and-telemetry-2026-10-26.md`, part B, with file:line references and links).

## 0. Decisions in brief

1. **Three separate systems with separate names, as in depictio** (`docs/telemetry.md:272-284` in depictio):

   | System | Variables | What it does | Default |
   |---|---|---|---|
   | Install telemetry | `SPECTIO_TELEMETRY_*` | outbound, anonymous; counts installations, versions and upgrades for the project | see 4 below |
   | Local activity analytics | `SPECTIO_ACTIVITY_*` | inside the instance; sessions and usage for its admins; never sent out | off |
   | Web analytics | `SPECTIO_WEB_ANALYTICS_*`, plugin kind `spectio.analytics` | the instance owner's own tracker: GA4, Umami, Plausible, Matomo, PostHog or custom | none |

2. **Spectio itself tracks nothing in the browser.** Web analytics exist only when an instance owner configures a provider, and the data goes to that owner's property.
3. **Download statistics are not install counts.**
   - PyPI download counts are skewed by mirrors, caches and CI.
   - GHCR exposes no pull counts through its API, for images or for the OCI Helm chart.
   - Only an anonymous ping counts installations (§3).
4. **Install telemetry is opt-out, as in depictio** (`settings_models.py:1974-1988` in depictio; Thomas, inbox #2, 2026-10-26):
   - it is on by default;
   - `spectio init` and the first admin sign-in show a notice once, with the exact payload and the one-line way to turn it off (`SPECTIO_TELEMETRY_ENABLED=false`, or *Administration → Instance → Settings → Telemetry*);
   - nothing is sent before that notice has been shown;
   - the suppressions of §2.3 (`DO_NOT_TRACK`, CI, tests, demo mode) still apply.

## 1. What is never collected

- **User data:** names, emails, IP addresses (the collector drops them; PostHog's `$ip` is not sent), and hostnames.
- **Pipeline data:** paths, pipeline parameters, sample names, run names, project names, and free text of any kind.
- **CLI details:** command arguments. Only the command path is sent, rebuilt from the CLI's own command tree as in depictio (`docs/telemetry.md:147-154`).
- **Exact counts:** sizes go in buckets (`0`, `1`, `2-5`, `6-20`, `21-50`, `51-200`, `200+`), to prevent fingerprinting.

## 2. Install telemetry (`SPECTIO_TELEMETRY_*`)

### 2.1 Events

| Event | When | Payload (beyond the common fields) |
|---|---|---|
| `server_install` | once per installation ID | deployment kind (`bundle`, `compose`, `helm`), database kind (`sqlite`, `postgres`), task backend |
| `server_heartbeat` | at most once per UTC day, whatever the number of replicas | version, `previous_version` if it changed since the last heartbeat, buckets of users, projects, runs in the last 7 days, gates in the last 7 days; engines in use; runner kinds; enabled plugin *kinds* with built-in or third-party flags (never plugin names from outside the Spectio organisation) |
| `cli_install` | first CLI run on a machine | CLI version, Python version, OS family |
| `cli_command` | each command (if enabled) | command path, exit status class (`ok`, `usage`, `error`), duration bucket |
| `runner_heartbeat` | at most once per UTC day per runner | runner version, launcher kind, engine versions in use (bucketed to minor) |

**Common fields:** `install_id` (random UUID in the database), `boot_id` (per process start), schema version, Spectio version.

**Upgrade paths** (`from → to`) come from heartbeats carrying the version against a stable `install_id`.

### 2.2 Transport and deduplication

- **Collector.** A plain HTTPS POST with `httpx` and no SDK.
  - Timeouts: 5 s for the server, 2 s for the CLI.
  - Failures are silent.
  - The default collector is PostHog Cloud EU with a public write-only key, as in depictio (`depictio/telemetry/constants.py:12-27`). `SPECTIO_TELEMETRY_ENDPOINT` can point to the project's own collector or a site's.
- **Deduplication.** A guard row `telemetry_guard(key = "send:<event>:<UTC date>")` is inserted before sending; the first replica to insert it wins. Daily guards are purged after 7 days. This is the SQL version of depictio's Mongo guard (`depictio/api/v1/telemetry/guard.py:72-104`).
- **Strict schema.** The payload is a Pydantic model with `extra="forbid"`, so a field cannot be added without a schema change, which goes through review.

### 2.3 Switches and transparency

**When it is suppressed.** `telemetry_allowed()` returns a reason, not a boolean. Telemetry is suppressed by any of these:
- `SPECTIO_TELEMETRY_ENABLED=false`, or turned off in *Administration → Instance → Settings → Telemetry* (§0.4);
- the notice of §0.4 not shown yet;
- `DO_NOT_TRACK` set to anything other than `0` or `false`;
- CI detected (`CI`, `GITHUB_ACTIONS`…);
- a pytest run;
- demo mode.

**What an admin can see.**
- `GET /api/v1/admin/telemetry/preview` returns the exact next payload and the current suppression reason.
- The admin screen *Administration → Instance → Settings → Telemetry* shows it, with the on/off switch and a link to the docs page listing every field.
- `SPECTIO_TELEMETRY_DEBUG=true` logs payloads instead of sending them.
- The docs page listing every field is generated from the payload's Pydantic model (§2.2), and CI fails when the page is out of date (`--check`), as depictio does with `scripts/gen_telemetry_docs.py --check` (`telemetry-ci.yaml:96-102`, `v1.19.2`).

**Known effects** (documented, as depictio does in `docs/telemetry.md:285-299`):
- a restored backup keeps its `install_id`, and `boot_id` shows the clone;
- a wiped database mints a new `install_id`, and `preexisting_data=true` flags it.

### 2.4 The project's dashboard

The project uses the collected events to answer four questions:
- how many active installations there are per week;
- which versions are in use;
- how upgrades go, from which version to which;
- the mix of deployment kinds and engines.

**Upstream statistics, as a weak complement.** A monthly scheduled job snapshots them into `docs/research/data/downloads-<YYYY-MM>.json`:
- **PyPI:** downloads from the `bigquery-public-data.pypi.file_downloads` dataset, by installer and Python version.
- **GitHub:** cumulative `download_count` per release asset. GitHub keeps no history, hence the snapshots.

**GitHub traffic** (views, clones, referrers) is snapshotted weekly into `docs/research/data/traffic-<YYYY>-W<ww>.json`, because GitHub keeps only the last 14 days (depictio `telemetry-metrics.yaml:1-15,112-123`; [GitHub REST traffic docs](https://docs.github.com/en/rest/metrics/traffic) **[to be validated]**). The token it needs is kept in a GitHub environment.

They show interest and trends, not installations.

## 3. Local activity analytics (`SPECTIO_ACTIVITY_*`)

**Where it lives.** An instance-internal service, the equivalent of depictio's `AnalyticsService` and middleware (`analytics_service.py:21`, `analytics_middleware.py:12-60`).

**What it records:**
- sessions, with a 30-minute idle timeout;
- page views by route template;
- API calls by endpoint family;
- runs launched, gates decided, share links used.

**Who sees it.** Instance admins only, in *Activity → Usage*. Retention is 90 days by default. Nothing leaves the instance.

**Opting out.** It is off by default. When it is on, users can opt out in their profile.

## 4. Web analytics for instance owners (`spectio.analytics`)

### 4.1 Providers

| Provider | Licence | Cookies and consent | Spectio settings |
|---|---|---|---|
| GA4 | proprietary | sets cookies; consent generally needed in the EU **[to be validated]** | `measurement_id` (`^G-[A-Z0-9]+$`) |
| Umami | MIT | cookieless **[to be validated]**; `data-do-not-track` | `website_id`, `script_url`, `host_url`, `domains` |
| Plausible CE | AGPLv3 | "no cookies… no consent banners required" (Plausible's self-hosting docs) | `domain`, `script_url` |
| Matomo | GPL v3 | `requireConsent` or `requireCookieConsent`; a CNIL-exempt configuration exists | `site_id`, `tracker_url` |
| PostHog | MIT except `ee/` | cookies or localStorage by default **[to be validated]** | `api_key`, `api_host`, `persistence` |
| custom | — | as the plugin declares | a plugin in `spectio.analytics` |

Providers ship as built-in plugins of the `spectio.analytics` kind. A site can add its own provider as a plugin.

### 4.2 How it works

1. **Runtime configuration.** The UI is a static bundle, so the tracker settings are served at runtime from the public `GET /api/v1/public-config`, under `analytics: {provider, settings, consent_required}`. This copies depictio's GA4 design (`utils_endpoints/routes.py:171-197`). Settings are only served when complete and valid.
2. **No inline snippet.** First-party UI code creates the provider's script element. The CSP never needs `unsafe-inline`.
3. **CSP managed by the server.** Each provider plugin declares its origins for `script-src`, `connect-src` and `img-src`, and the server adds them to the CSP header. Operators never edit CSP by hand. These origins are added to the baseline CSP of [`authentication-and-access.md`](authentication-and-access.md) §3.1. *(assumed — pending Thomas, inbox #23)*
   - A self-hosted Umami, Plausible or Matomo needs only its own origin.
   - GA4 needs `www.googletagmanager.com`, plus `*.google-analytics.com`, `*.google.com` and the regional Google domains, listed one by one (Google's CSP guide, cited in the research note).
4. **Page views on route changes.** The router calls `analytics.page(template)` after each navigation.
   - Auto-tracking of history changes is turned off where the provider has it (GA4 enhanced measurement, Umami `data-auto-track`), so page views are not counted twice **[to be validated per provider]**.
   - depictio's GA4 loader sets `send_page_view: true` while its comment says page views are the app's job, which leaves single-page navigation to the property's settings. Spectio avoids that ambiguity.
5. **Identifiers removed.** Paths are sent as templates (`/runs/:id/gates/:gate`), never with IDs, sample names or query strings. The page title sent is the route name, not the document title, which can contain a run name.
6. **Consent and Do Not Track.**
   - `navigator.doNotTrack === "1"` and a per-user opt-out in the profile both stop the tracker.
   - If the provider requires consent (`consent_required`), a minimal banner asks first, and nothing is loaded before the answer.
7. **Never inside sensitive views.** No tracker loads on share-link landing pages for guests, on embedded views (`api-and-data-model.md` §9), on sign-in pages, on administration pages (`/admin/*`), or on gate review and decision pages. *(assumed — pending Thomas, inbox #23)*

**Legal context.** The CNIL lists the conditions for audience measurement without consent:
- users are informed and can object;
- measurement is the only purpose;
- no cross-linking with other processing;
- one publisher;
- IP addresses truncated;
- at most 13 months of retention.

Spectio's defaults meet the purpose, cross-linking and IP conditions for self-hosted Umami, Plausible and Matomo. The operator remains responsible. EMBL's own data-protection policy applies to EMBL instances **[to be validated]**.

### 4.3 The docs site

The docs site uses the same choice of provider through Material's `extra.analytics`, configured per deployment, and none in the repository.

## 5. Tests

| What | How |
|---|---|
| No send in CI and tests | unit test: `telemetry_allowed()` returns its reason under `CI=true`, pytest, `DO_NOT_TRACK=1` |
| One heartbeat per day across replicas | API test with two server processes on one Postgres: one row in `telemetry_guard`, one request at the fake collector |
| Payload schema | snapshot test of the preview endpoint; `extra="forbid"` rejects a new field |
| No identifiers in web analytics | Playwright: navigate runs, gates and share links with a fake provider, and assert every recorded path is a template |
| CSP | each provider plugin: the response CSP contains its declared origins and no `unsafe-inline` |
| Do Not Track and consent | Playwright with `doNotTrack` set: no provider script requested |
| No tracker in sensitive views | Playwright with a fake provider: no provider script requested on sign-in, share-link landing, embedded, `/admin/*` and gate review pages *(assumed — pending Thomas, inbox #23)* |
