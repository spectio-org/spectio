# Research — autopilot budget governor, and telemetry/analytics for Spectio

Date: 2026-10-26. Claude Code docs fetched 2026-10-26. depictio audited at commit
`0d1aa0a` (2026-10-23), local clone. Paths below are relative to the depictio repo root.

---

## A. Budget governor for the autopilot

### A1. What Claude Code exposes (verified)

1. **Statusline JSON carries plan usage.** `rate_limits.five_hour` and `rate_limits.seven_day`,
   each with `used_percentage` (0–100) and `resets_at` (Unix epoch seconds). Also
   `cost.total_cost_usd` for the session.
   Source: <https://code.claude.com/docs/en/statusline.md> (Available data).
2. **The limits are conditional.** `rate_limits` is present only for Claude.ai Pro/Max
   subscribers (or behind a gateway that reports spend limits), and only after the first API
   response of the session. Each window can be absent on its own, and a window is dropped once
   its `resets_at` has passed. Source: same page.
3. **When the statusline runs.** At session start, after each new assistant message, on
   `/compact`, on an optional `refreshInterval` timer, and when a `resets_at` is reached. It is an
   interactive-UI feature; nothing documents it running under `claude -p`. Source: same page.
4. **`/usage`.** Shows the plan bars (5-hour session and weekly) plus a local attribution
   breakdown (24 h / 7 days, from local history only). When rate limited it shows last-known bars
   up to 60 minutes old. Limit messages are "You've hit your session limit · resets 3:45pm" and
   "You've hit your weekly limit · resets Mon 12:00am". Source:
   <https://code.claude.com/docs/en/costs.md>.
5. **OpenTelemetry has cost and tokens, not quota.** The metrics are `claude_code.cost.usage`,
   `claude_code.token.usage`, `claude_code.session.count` and `claude_code.active_time.total`.
   The `claude_code.api_error` event carries `status_code` (429 on a limit). No metric reports
   the percentage of the plan window used. Enable it with `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus
   the `OTEL_METRICS_EXPORTER` / `OTEL_LOGS_EXPORTER` / `OTEL_EXPORTER_OTLP_*` variables.
   Source: <https://code.claude.com/docs/en/monitoring-usage.md>.
6. **Hooks: there is a signal for hitting the limit, but no usage fields.**
   - The common hook input has no `rate_limits` or cost field.
   - `StopFailure` fires when a turn ends on an API error, with matcher values that include
     `rate_limit`, `overloaded` and `billing_error`. It has no decision control.
   - `Notification` matchers include `quota_auto_resume_fired`, `quota_auto_resume_stale` and
     `quota_auto_resume_disabled`.
   - Source: <https://code.claude.com/docs/en/hooks.md>.
   - The payloads of both events, including whether they carry a reset time, are
     **[to be validated]** (that part of the page was truncated in the fetch).
7. **Auto-continue at the usage limit.**
   - It is on by default in interactive subscription sessions (v2.1.234+). The open session waits
     and continues once the limit resets, and re-arms at most twice.
   - It does not start on its own when the reset is more than 24 h away (so a weekly limit is not
     covered), nor in Remote Control or agent-team teammate sessions.
   - Cancel it with `/rate-limit-options`; control it with the `autoContinueAtUsageLimit` setting.
   - Sources: <https://code.claude.com/docs/en/interactive-mode.md>, and the setting row in
     <https://code.claude.com/docs/en/settings-reference.md>.
8. **`/goal` and workflows.**
   - `/goal` pauses on a usage limit and continues when the session auto-continues
     (<https://code.claude.com/docs/en/goal.md>).
   - Dynamic workflows wait at a limit only in an interactive subscription session with
     auto-continue, when the reset is within 24 h, and for at most two waits. Otherwise the
     workflow's agents fail, including under `-p` and in background sessions
     (<https://code.claude.com/docs/en/workflows.md>).
9. **Headless signals.**
   - `stream-json` emits `system/api_retry` events whose `error` can be `rate_limit`.
   - The final `result` (json) carries `total_cost_usd`
     (<https://code.claude.com/docs/en/headless.md>).
   - What `claude -p` returns once the plan limit is really hit (exit code, result subtype, any
     `rate_limit_event` message with utilisation) is **[to be validated]**. It was not found in
     the docs pages fetched: errors.md, cli-reference.md, agent-sdk/typescript.md.
10. **`--max-budget-usd` is a cost cap, not a quota cap.**
    - It is print-mode only, and is checked against the client-side cost *estimate*. Subagent
      spend counts toward it, and spend can overshoot the cap.
    - Totals restored by `--resume` do not count. At the cap, new subagents fail with
      "Budget limit reached" and background subagents are stopped.
    - Source: <https://code.claude.com/docs/en/cli-reference.md>.
    - For a subscriber, the USD figure is notional and maps to plan percentage only through
      calibration (A2.3).
11. **Throttles are not limits.** "Server is temporarily limiting requests (not your usage
    limit)" is a capacity throttle, told apart from a plan limit by the quota headers. A governor
    must not treat it as exhaustion. Source: <https://code.claude.com/docs/en/errors.md>.
12. **No env var and no CLI command prints the remaining quota.**
    - Neither the CLI flags nor the settings reference list one. `claude auth status` reports
      the auth method, not usage (<https://code.claude.com/docs/en/cli-reference.md>).
    - The SDK has an alpha `taskBudget: {total}` option, a token budget the model is told about.
      It is not plan quota (<https://code.claude.com/docs/en/agent-sdk/typescript.md>).

### A2. Proposed design

1. **Primary source: a statusline tap.**
   - A tiny statusline command reads its stdin JSON and atomically writes `rate_limits`,
     `cost.total_cost_usd` and a timestamp to `.autopilot/usage.json`. It then prints the normal
     status line.
   - The orchestrator reads that file at the start of each tick and before dispatching each
     batch.
   - Keep it fresh with `refreshInterval` (e.g. 60 s) so idle waits also update. The tap needs
     the orchestrator to run in an interactive session (`/goal` or `/loop` driving `/autopilot`),
     which is the mode Spectio already uses.
   - Whether the statusline runs in a cloud or claude.ai-app session is **[to be validated]**.
2. **Staleness rule.** If `usage.json` is older than 15 min, or a window is missing, treat the
   reading as *unknown* and switch to A2.3. Never treat a missing window as 0 %: a window is
   dropped after its reset (A1.2), which really is ~0 %, but absence before the first API
   response is not.
3. **Fallback: calibrated cost.**
   - Headless workers (`-p`) report `total_cost_usd`. Record it per step, together with the
     step's kind.
   - While A2.1 works, store pairs (Δ`seven_day.used_percentage`, Δcost) per tick in
     `.autopilot/calibration.jsonl`, and keep a rolling median of *percent per USD* for each
     window.
   - With no live reading, estimate used % = last known % + Δcost × that ratio.
   - Label every estimate as such in the journal.
4. **Stop rule for "use X % of my weekly window".**
   - At start, record `P0 = seven_day.used_percentage` and `R0 = seven_day.resets_at`. The
     budget is `B = X` percentage points.
   - Track the points consumed, not the absolute level: consumed = Σ positive deltas between
     readings. This survives a weekly reset during the run: when `resets_at` changes, the new
     baseline is the new reading.
   - Before dispatching a batch, estimate its cost from the per-kind medians (review / spike /
     build) in the journal history, converted to points with A2.3.
   - Dispatch only if consumed + estimate ≤ B − margin, with margin = max(2 points, 1 × the
     largest step median). Otherwise finish the running steps, write the journal, and stop with
     reason `budget`.
   - Also cap at an absolute level of `min(P0 + X, 100 − margin)`, so that other use of the plan
     during the run (Thomas chatting elsewhere) is counted. Readings are account-wide, so this
     happens for free.
5. **Stop rule for "until exhausted / until a deadline".**
   - Run with auto-continue off for the orchestrator's own session (`autoContinueAtUsageLimit:
     false`) when a deadline is set, so the session does not sit idle past the deadline.
   - Stop when the first of these happens:
     - `five_hour` or `seven_day` ≥ 100 − margin;
     - a `StopFailure` hook with matcher `rate_limit` fires (it writes `.autopilot/limit-hit`);
     - a worker stream shows `api_retry` with error `rate_limit` that is not a throttle (A1.11);
     - the wall-clock deadline is reached.
   - At a 5-hour limit with no deadline, either let auto-continue wait (it will, if the reset is
     within 24 h; A1.7) or end the tick and let a scheduled task resume at `resets_at` + 2 min.
   - At a weekly limit, always stop: auto-continue does not cover it.
   - In both cases, mark the running steps `failed` with reason `limit`, without spending a retry
     attempt, so they are re-run cleanly.
6. **No signal at all** (API key or Bedrock user, not a subscriber). There is no `rate_limits`
   (A1.2). Use a wall-clock time-box, plus `--max-budget-usd` on each worker, set to the
   per-kind median × 1.5. A per-run USD ceiling is summed by the orchestrator.
7. **Workers.** Every headless worker gets `--max-budget-usd` (per-step cap) and
   `--output-format stream-json`, so `api_retry` and `total_cost_usd` are visible.
   Workflow-based review rounds inherit the A1.8 caveat: under `-p` they fail at the limit
   rather than wait. So the governor's margin must cover one whole round.
8. **Interface.**
   - `/autopilot --budget 30%w`, `--budget 40%5h`, `--until-exhausted`, `--deadline 15:00`.
   - These are stored in `state.json.budget` = {mode, X, P0, R0, consumed, last_reading_at,
     source: live|estimated}.
   - The AUTOPILOT status line adds `budget=12.4/30pt (live)`.

---

## B. Telemetry and analytics

### B1. What depictio does (verified, file:line)

1. **Three separate systems, named apart on purpose** (`docs/telemetry.md:272-284`):
   - `DEPICTIO_TELEMETRY_*`: outbound anonymous install counting, **on** by default.
   - `DEPICTIO_ANALYTICS_*`: per-user sessions stored in the instance's own MongoDB, never
     transmitted, **off** by default.
   - `DEPICTIO_GOOGLE_ANALYTICS_*`: GA4 in the frontend, to the operator's own property, **off**
     by default.
2. **Outbound telemetry config.** `TelemetryConfig` is at
   `depictio/api/v1/configs/settings_models.py:1973-2058`. It has `enabled=True`, `endpoint`,
   `api_key`, `interval_hours=24`, `deployment_kind`, `include_usage_metrics`, the Helm-provided
   `replicas`/`cpu_*`/`memory_*`, and `debug`. Its docstring gives the rationale: "GHCR publishes
   no pull counts for either the container images or the OCI Helm chart, so there is otherwise
   no signal at all".
3. **Transport.**
   - PostHog Cloud EU capture endpoint `https://eu.i.posthog.com/i/v0/e/`, chosen to keep data in
     the EEA. The public write-only project token is committed on purpose
     (`depictio/telemetry/constants.py:12-27`).
   - Timeouts are 5 s for the server and 2 s for the CLI (`constants.py:31-34`).
   - It uses plain `httpx` with no SDK (`depictio/telemetry/posthog.py:98-150`). Every event sets
     `$process_person_profile: false` (`posthog.py:69`).
4. **Kill switches.**
   - `telemetry_allowed()` returns a *reason*, not a bool
     (`depictio/telemetry/gates.py:55-83`).
   - Consent signals: `enabled=false` and `DO_NOT_TRACK`, any value except `0`/`false`
     (`gates.py:45-52`).
   - Data-hygiene signals: pytest, CI and DB wipe.
5. **Events.** There are four, documented in `docs/telemetry.md:27-34`:
   - `server_install` (once ever) and `server_heartbeat` (at most once per UTC day, whatever the
     number of replicas);
   - `cli_install` (first CLI run per machine) and `cli_command` (per invocation).
6. **Deduplication across replicas.**
   - A Mongo guard document with `_id = send:<event>:<UTC date>` is inserted before sending; the
     first replica to claim it wins (`depictio/api/v1/telemetry/guard.py:72-104`).
   - Daily guards expire through a TTL index; the install guard never expires
     (`guard.py:21-22,41-60`).
7. **Payload discipline.**
   - The schema forbids undeclared fields (`depictio/telemetry/schema.py`;
     `docs/telemetry.md:167-170`).
   - Counts are sent as bucket labels (`0, 1, 2-5, …, 200+`) to avoid fingerprinting
     (`docs/telemetry.md:82-90`).
   - The CLI command path is rebuilt from the CLI's own command tree, so arguments can never leak
     (`docs/telemetry.md:147-154`).
8. **Operator transparency.**
   - An admin endpoint `GET /depictio/api/v1/utils/telemetry/preview` returns the real payload
     and the current suppression reason.
   - `DEPICTIO_TELEMETRY_DEBUG=true` logs payloads instead of sending them.
   - Four end-to-end check scripts run against an in-process collector
     (`docs/telemetry.md:172-207`).
9. **Known limitations.** A restored backup clones the install ID, so `boot_id` makes it
   visible. A dropped collection re-mints the ID, so `preexisting_data` flags it
   (`docs/telemetry.md:285-299`).
10. **GA4 config.** `GoogleAnalyticsConfig(enabled, tracking_id)` with `is_configured` is at
    `settings_models.py:2123-2137`, prefix `DEPICTIO_GOOGLE_ANALYTICS_`.
11. **GA4 injection at runtime, not build time.**
    - The static Vite/nginx bundle cannot carry a per-deployment ID, so the backend serves it
      unauthenticated from `GET /utils/public-config`. The ID is withheld unless GA is fully
      configured (`depictio/api/v1/endpoints/utils_endpoints/routes.py:171-197`).
    - The viewer fetches it fire-and-forget (`depictio/viewer/src/main.tsx:354-360`) and injects
      gtag (`depictio/viewer/src/googleAnalytics.ts:34-66`).
    - The injection is idempotent under StrictMode, rejects anything not matching `^G-[A-Z0-9]+$`
      (which blocks the chart placeholder), and sets `allow_google_signals: false` and
      `allow_ad_personalization_signals: false`.
    - Note: the code sets `send_page_view: true` while its comment says page views on history
      changes are "the host app's job". GA4 history-change page views come from the property's
      Enhanced-measurement setting, which must be switched on
      (<https://developers.google.cn/analytics/devguides/collection/ga4/single-page-applications?hl=en>).
      Whether `anonymize_ip` has any effect in GA4 is **[to be validated]**.
12. **Browser telemetry client** (`packages/depictio-react-core/src/telemetry.ts`, 172 lines).
    - It has no SDK; one `fetch` with `keepalive` per event (`:140-160`).
    - Opt-out order: an explicit `localStorage` opt-out wins, then `navigator.doNotTrack === '1'`
      (`:16-17,60-83`).
    - The anonymous ID is a UUID in `localStorage`.
    - It is exported for the viewer and Studio (`packages/depictio-react-core/src/index.ts:1144`).
13. **Local analytics.** `AnalyticsService` (`depictio/api/v1/services/analytics_service.py:21`,
    sessions, activity, cleanup and summary) is fed by `AnalyticsMiddleware`
    (`depictio/api/v1/middleware/analytics_middleware.py:12-60`). It is configured by
    `AnalyticsConfig` (`settings_models.py:1945-1970`): off by default, 30 min session timeout,
    90 days retention.

### B2. External web analytics an instance owner can plug in

| Tool | Licence (source) | Cookies / consent | Embed |
|---|---|---|---|
| GA4 | proprietary SaaS | Sets cookies; consent is generally needed in the EU **[to be validated]** | gtag.js from `www.googletagmanager.com` |
| Umami | MIT ([GitHub org](https://github.com/orgs/umami-software/repositories)) | Cookieless **[to be validated]**; `data-do-not-track` option ([docs](https://docs.umami.is/docs/tracker-configuration)) | `<script defer src=… data-website-id=…>`; `data-domains`, `data-host-url`, `data-auto-track` (page views, clicks, "path change detection") |
| Plausible CE | AGPLv3 ([self-hosting](https://plausible.io/docs/self-hosting)) | "No cookies, no personal data collected, no consent banners required" (same page) | `<script data-domain=…>` **[to be validated]**; SPA page wasn't fetched ([spa-support](https://plausible.io/docs/spa-support), [hash routing](https://plausible.io/docs/hash-based-routing)) |
| Matomo | Core and JS tracker GPL v3 ([FAQ](https://matomo.org/faq/general/matomo-analytics-licences-for-core-tracker-and-plugins/)) | `requireConsent` (nothing sent before consent) or `requireCookieConsent` (sent, but no cookies) ([guide](https://developer.matomo.org/guides/tracking-consent)); a CNIL-exempt setup exists ([FAQ](https://matomo.org/faq/how-do-i-configure-matomo-without-tracking-consent-for-french-visitors-cnil-exemption/)) | `_paq` snippet; on SPAs, push `setCustomUrl` + `trackPageView` on each route **[to be validated]** |
| PostHog | MIT except `ee/`; FOSS mirror `posthog-foss` ([README](https://github.com/posthog/posthog)) | Default persistence uses cookies/localStorage **[to be validated]** | posthog-js, or a raw capture POST as depictio does |

1. **EU consent exemption (CNIL, France).** Audience measurement is exempt from consent only if
   all of these hold (<https://www.cnil.fr/en/sheet-ndeg16-use-analytics-your-websites-and-applications>):
   - users are informed and can object;
   - the purpose is limited to audience measurement or A/B testing;
   - there is no cross-linking with other processing;
   - the tracker serves a single publisher;
   - the last IP byte is truncated;
   - trackers live at most 13 months.

   The CNIL notes that most large offerings fall outside the exemption. This is ePrivacy guidance
   and varies by country.
2. **EMBL context.** EMBL is an intergovernmental organisation with its own internal
   data-protection policy rather than GDPR as such **[to be validated]**. Spectio should not
   decide for operators: ship **no** tracker by default and let the instance owner choose.
3. **CSP for GA**, from Google's guide
   (<https://developers.google.com/tag-platform/security/guides/csp?hl=fr>):
   - `script-src-elem https://www.googletagmanager.com`;
   - `img-src` and `connect-src` must also allow `*.google-analytics.com`, `*.google.com`,
     `*.google.<TLD>` and `*.g.doubleclick.net` (connect also `pagead2.googlesyndication.com`);
   - each Google TLD must be listed one by one, since CSP allows no wildcard after the host.

   A self-hosted Umami, Plausible or Matomo needs only its own origin in `script-src` and
   `connect-src`.
4. **Plugin design for Spectio (proposal).**
   - One frontend extension point `analytics`, configured by the instance owner (not per user):
     provider ∈ {none, ga4, umami, plausible, matomo, posthog, custom}, plus the provider's
     fields (site ID, host URL).
   - Served at runtime from a public-config endpoint, exactly like depictio's B1.11.
   - The backend adds the provider's origins to the CSP response header, so operators do not
     hand-edit CSP. Never allow `unsafe-inline`: the loader is first-party code that creates the
     script element (B1.11 pattern), so no inline snippet is needed.
   - The SPA router calls `analytics.page(path)` on each route change. Providers that auto-track
     history (Umami, GA4 with Enhanced measurement) get auto-tracking disabled, to avoid double
     counts **[to be validated per provider]**.
   - Run-, sample- and project-identifying path segments are replaced with templates
     (`/runs/:id`) before sending.
   - A consent hook (`requireConsent` flag) is exposed for providers that need it, and
     `navigator.doNotTrack` is honoured as depictio does (B1.12).

### B3. Install and upgrade tracking for the Spectio project itself

1. **PyPI.**
   - Downloads are in the BigQuery dataset `bigquery-public-data.pypi.file_downloads`, fed by
     Linehaul (<https://docs.pypi.org/api/bigquery/>).
   - Per-download fields include `details.installer.name` and `details.python`.
   - Counts are raised or lowered by mirrors and lowered by pip's cache; data before 2018-07-26
     is under-reported
     (<https://packaging.python.org/guides/analyzing-pypi-package-downloads/>).
   - These are *downloads, not installs or active users*. CI re-downloads dominate
     **[to be validated]**; depictio states the same (`docs/telemetry.md:19-21`).
2. **GitHub release assets.** Each asset has a cumulative `download_count`
   (<https://docs.github.com/en/enterprise-server@3.1/rest/releases/releases>). It is good for
   binaries and tarballs, but gives no time series (you must snapshot it yourself) and no
   identity or upgrade path.
3. **GHCR images and the OCI Helm chart.**
   - The API and GraphQL expose download counts only for GitHub's legacy container registry, not
     for ghcr.io; counts can only be scraped from the package HTML page
     (<https://voxpupuli.org/blog/2026/08/07/container-statistics/>).
   - depictio reached the same conclusion (B1.2). An OCI Helm chart on GHCR has the same gap.
   - An Artifact Hub listing gives views and stars, not pulls **[to be validated]**.
4. **Anonymous ping: the only source that counts installations, versions and upgrades.**
   - Recommended: copy depictio's model closely.
     - An install ID in the DB, plus a boot ID.
     - `install` once and `heartbeat` daily, deduplicated by a DB guard.
     - Bucketed sizes.
     - `DO_NOT_TRACK` and an `enabled` switch; suppressed in CI and tests.
     - A preview endpoint and a debug-log mode.
     - The EU PostHog endpoint, or the project's own collector.
   - The `from_version → to_version` upgrade path falls out of heartbeats carrying the version
     against a stable install ID.
   - Spectio-specific buckets: engines in use (nextflow / snakemake), runner kinds (slurm / k8s /
     local), runs per week, gate counts. All are enumerations from Spectio's own code, never
     user strings.
   - Decide default on or off as an explicit decision-log entry. depictio chose on, justified by
     a trivial opt-out and full transparency (`settings_models.py:1974-1988`).
5. **What each source can and cannot tell.**
   - PyPI and GitHub assets: rough interest and trend; not installs, users or versions in use.
   - GHCR: nothing via API.
   - Ping: real installations, versions, deployment kind and upgrades; it under-counts air-gapped
     and opted-out sites.

### B4. URLs blocked during this research (not fetched)

- <https://umami.is/docs/tracker-configuration> (fetched the docs.umami.is copy instead).
- <https://plausible.io/docs/script-extensions> and <https://plausible.io/docs/spa-support>.
- <https://developers.google.com/tag-platform/security/guides/csp> (the English page; the
  French-locale copy was used).
- GitHub API licence checks (`gh api repos/...`): repo access is not enabled for this session.
