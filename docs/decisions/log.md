# Project: open source equivalent of Nextflow Tower / Seqera Platform

Session notes (Thomas). Last updated: 23/10/2026.

## Goal
Rewrite/redevelop the equivalent of NF Tower (now Seqera Platform), compatible with **Nextflow and Snakemake** initially; CWL, WDL and others afterwards.

## Desired features
- Run monitoring: state, number of succeeded/failed jobs, etc.
- Modify parameters, relaunch, produce a summary.
- Properties depending on use cases, notably **workflows interrupted midway** (image analysis, etc.) for **quality control**, followed by a choice of:
  - change the parameters and relaunch everything;
  - continue to the end and produce a summary;
  - **iterative execution in parts** (1, 2, 3, 4).
- Results visualisation: PDF, HTML, images (PNG, JPEG) via standard viewers, and advanced viewers for imaging (Vizarr / Viv / OME-Zarr style).

## Special scenarios to cover (added 23/10, 09:29)
Everything must be traced, including:
- conditional execution and dynamic DAG: **Snakemake checkpoints**, Nextflow `when:` and branches;
- **temporary files** (Snakemake `temp()`, cleanup of the Nextflow `work` directory);
- **SLURM job arrays**;
- the various **compute / backends / executors** and **storage** used;
- **Snakemake wrappers** and **Nextflow modules** (name, version, source);
- (message cut off after "Nextflow modules": remainder to be completed).

## Human / AI / external interventions (added 23/10, 09:42)
- **AI-compatible** system: a human and an AI agent must be able to approve or intervene in the same way.
- Interventions external to the pipeline possible, **manual or robotic**.
- Proposal: `Intervention` concept, one API, three facades (web UI, MCP server, webhooks/SiLA 2). Details: section 5bis of the synthesis.

## Deployment and integrations (added 23/10, 22:05)
- Server **installable with pure pip** (`pip install` / `uv tool install`, then a `serve` command). The React build is embedded in the wheel; Node only in CI.
- SQLite: the uv-managed Python embeds SQLite 3.53.1 (OK, ≥ 3.51.3); the system Python tested here has 3.45.1 (affected by the WAL-reset bug). Fallback: `apsw` wheel (SQLite 3.54.1 embedded). Version check at startup.
- Engine plugins **outside the server package**: Snakemake plugin = separate pip package in the Snakemake env; Nextflow companion plugin = Nextflow plugin registry.
- **No mandatory PR** on the Snakemake or Nextflow side. Upstream PRs useful but optional (Snakemake: `external_jobid` and `attempt` in events, typed events for temp and checkpoints, end-of-workflow event, executor name).
- **Third-party integration very important** (trigger and track via our API): versioned native API + OpenAPI + generated SDKs, **GA4GH WES 1.1** facade, outgoing webhooks, SSE, scoped tokens, idempotency keys. Partial compatibility with the Seqera API (for `tw`, seqerakit): later, after a legal check.

## Name and branding (ideas from 23/10, 22:07)
- depictio style noted from its repository: Latin name ending in *-io*, logotype in thick rounded capitals, headings in Outfit, body text in Inter, rosette emblem of 8 coloured sectors, palette `#9966CC #7A5DC7 #6495ED #45B8AC #8BC34A #F9CB40 #F68B33 #E6779F`, UI in **Mantine 7**.
- Names free on PyPI and npm on 23/10 (GitHub, domains and trademarks not checked): **Ductio** (to lead, to steer; favourite), **Monitio** (warning, root of "monitor"), **Moderatio** (regulation, control), **Ordinatio** (ordering/scheduling), **Conductio**, **Rectio**.
- To avoid: Iteratio and Fluxio (taken on npm), Operatio (taken on PyPI).
- Emblem: reuse the rosette and the palette, but in motion (spiralling sectors or a progress ring).
- Stack consequence: **Mantine rather than shadcn/ui**, to reuse `depictio-react-core` and keep the same look.

## Pause, check, resume (23/10, 22:09)
- No freezing of the engine: pause = clean stop at a stage boundary; resume = relaunch with cache, a new `Run` within the same `Lineage`.
- Stages declared in a `ductio.yml` manifest (Snakemake `until` target, Nextflow `stage` parameter, intervention type, evidence, parameter schema, policy).
- Nextflow: the pipeline must cooperate (`stage` parameter). Details: section 5ter of the synthesis.

## Register / launch without a terminal (24/10, 22:07)
- Aim: minimise terminal use for the end user. Register a workflow (local or remote), launch it, track it, debug it, relaunch it from the UI.
- Proposal: catalogue (nf-core / Snakemake schemas → forms), outgoing agent on the login node (like Seqera's Tower Agent), launch from the UI; "observed" mode (CLI + plugin) retained. Details: section 7quater of the synthesis.

## Chosen name (25/10, 08:50): **Spectio**
- Latin of the augurs: *spectio* = observation of the auspices (the right to observe a sector of the sky above the horizon). Short (7 letters), same family as depictio (-ctio). Free on PyPI, taken on npm (plan for `@spectio/…` or `spectio-ui`).
- Palette: **Dawn (light)** (#5A4FCF #8B5CF6 #EC5F87 #F9A947), emblem = half-disc in 4 equal sectors. Tokens: `spectio-tokens.css`.
- Typography: Outfit (headings), Inter (UI), JetBrains Mono (logs). UI accent violet 600 #7750D4. Green/red reserved for states.
- Logotype: depictio lettering, **rounded S + open P** (like depictio's open D). Cut S tested (C0 to C3) then dropped on 25/10: the S is no longer recognisable.

## Former name (24/10, 21:44): Perspectio
- 24/10, 22:10: Thomas likes something between panoramas 1 and 3 (3 too busy, hard to read from a distance). Three intermediate versions added: 4, 5 and 6 sectors.
- 24/10, 22:19: six sectors judged too thin, no increasing sizes. New variants with five (A: large violet on the left; B: orange apex in the centre) and four wide sectors, alternating sizes, enlarged emblem (about 1.7 times the letter height).
- 24/10, 22:42: **equal sectors** direction (half-disc in 4 identical sectors, crisp silhouette from a distance) + new palettes: Aube (#3D348B #7B4FBF #E2557A #F7A23B), Lagune (#1B3A6B #2563A8 #2E9CC0 #57CFC1), Spectre (#4361EE #7B2CBF #F72585 #FF9F1C), and the depictio palette for comparison.
- Name analysis: no negative meaning found in FR/EN/DE/ES/IT/PT/NL; risks = autocorrection to "perspective", search engines, hesitant pronunciation (-tio), neighbours Perspective (FINOS, dataviz), Perspectium, Perspecta, Perspio. Trademarks not checked (EUIPO/USPTO/INPI to be done).
- 24/10, 22:05: variant **C** chosen for the P. Emblem redone with depictio's exact geometry (8 sectors on 45° axes, separation bands of constant width, 3 sizes 0.44 / 0.72 / 1, colours from the logo file: #DD6E94 #BD63E1 #7E5FED #627AF1 #EF9745 #F2C547 #A2D54E #59B4CB). Three panoramas: top half, flipped bottom half, 8 sectors over 180°.
- Logo: same lettering and same layout as depictio (emblem on the left, name on the right), emblem separated from the letters. Letters P, E, C, T, I, O taken from depictio's outlines; R and S drawn in the same style (S to be refined).
- 24/10, 22:03: **panorama chosen**. First P "open" like depictio's D, three variants: C (bowl open on the left over a short stem, favourite), A (bowl detached at the bottom), B (stencil).
- Emblems under test: **180° panorama** (half-rosette sitting on the horizon, aligned with the text baseline) and **triangle eye** (two half-rosettes in an almond shape around a pupil). Previous directions not retained by Thomas.
- Colours: no greens (Nextflow/Snakemake, and green = success in the UI). depictio palette for the emblem, neutral UI + violet accent, colours reserved for states.

## Name: feedback from 24/10
- Thomas is not convinced by "Ductio": *duct* = a single channel, whereas the goal is the **multichannel view** (overview, monitoring, triggering, checkpoints).
- Names free on PyPI and npm on 24/10: **Perspectio** (to see through, examine thoroughly; perspective), **Prospectio** (overview, foresight), **Circumspectio** (looking all around before acting), **Gubernatio** (to govern, to hold the helm), **Moderatio** (to regulate), **Mutatio** (Roman relay station where horses were changed, and change).
- Taken: statio, mansio, inspectio, castellum, specula, custodia, vigilia, transitio.
- Multichannel logo image: the *castellum divisorium* (Roman water tower that splits an aqueduct into several channels, each with its own sluice gate).

## Technical constraints
- **Engine-transparent** integration: native APIs or mechanisms, **no** ad hoc log parsing or Python `subprocess` that would degrade the UX.
- Account for **GA4GH** standards: WES, TES (and probably TRS, DRS).
- Projects to study: Arvados (CWL), Sapporo (agnostic), and other existing ones.

## Stack and UX
- **Python** backend, **React + Tailwind** frontend (or equivalent).
- Very modern and attractive UI, in the spirit of depictio; **mobile and tablet** compatible.
- Lightweight at startup, **high performance**, no slow system.

## Phasing
1. **Lightweight MVP**, deployable by any user on a cluster. Start as simply as possible.
2. More complete version: user management, **CLI tokens generated via the web UI**, spaces restricted by user / group / project.

## Open questions
(to be completed with Thomas's answers)

## Decisions and revisions
- 23/10, after reading the nf-tower and nf-shard code: **implement the 5 Tower protocol routes on the server side** (`/trace/create`, `/begin`, `/progress`, `/heartbeat`, `/complete`) to track Nextflow without installing anything (`tower.endpoint`). Steering stays in our launcher.
- Snakemake: in-house logger plugin (batches, heartbeat, local buffer, `has_filter = True`), which sends to our native API.
- Only the engine's main process talks to the server, not the compute nodes.
- 23/10, after analysing the advanced scenarios: Nextflow as a **hybrid** (Tower protocol + companion plugin for modules, published files, environments, `when:`). Snakemake with **three sources** (logger plugin, typed text messages, `.snakemake` + `sacct` collector). n:m model between attempts and scheduler jobs (arrays, groups). Details: section 2ter of the synthesis.

## 2026-10-25 — UI review round 2
- **Words**: the Spectio process on a compute environment is a **runner**; **agent** means AI agent only.
- **Shell**: sidebar copied from depictio (logo on top, 56 px items, coloured 25 px icons, footer with theme, runners, server, profile), fixed and full height; top bar without logo.
- **Engine marks**: official files from depictio `public/logos/workflows/` (Nextflow, nf-core, Snakemake), shown small on white, never recoloured.
- **Runs**: Table (run name + ID first) or Rows ("paper" full-width rows). Card grid dropped.
- **Relaunch**: 3 choices (Resume/Continue, Rerun from a stage via a clickable stage strip, Start fresh) instead of 5; Duplicate becomes "Copy to a new launch". Stages reused from cache use animated hatching.
- **Launch**: one collapsible section per schema group with a light icon from `fa_icon`; file checks show when they ran and have a Recheck button.
- **Review**: gate checks (per workflow, from `spectio.yml`) shown separately from run health (built in, same for all workflows); decision as 4 graphic paths with a flow bar; history collapsed.
- **Stages**: rnaseq stages in the mockups come from a lab overlay `spectio.yml`; without it, stages are detected from subworkflow names (display only) or the gauge shows task quarters. Gates stop Nextflow via a generated `ext.when = false` config, Snakemake via `--until`.
- **Runner offline**: runs keep computing and reporting (engines send events straight to the server); launches, controls and file access wait; decisions are recorded and applied on reconnect.
- **AI**: no built-in model required. Own agents via MCP/REST (their compute), optional built-in assistant through a model endpoint (hosted API or a model served as a GPU job by the runner, `spectio ai serve`), models inside workflows run as normal tasks.

## 2026-10-25 — Headless use, plugins, LabID, RO-Crate
- Spectio must also run **headless**: an engine-agnostic launch-and-monitor layer for other systems (LIMS/ELN such as EMBL's LabID, portals, CI, agents). The UI is one client of the public API.
- Other interfaces integrate through: REST + SDKs, GA4GH WES facade, webhooks/SSE, MCP, and **embeddable elements** (run card, launch form, review panel) plus thin host-side plugins.
- `external_refs` on runs and samplesheet rows carry the caller's IDs for round trips.
- **RO-Crate**: import workflows from Workflow RO-Crates (nf-core, WorkflowHub); export each run as a Workflow Run / Provenance Run Crate including gates and decisions; Nextflow via `nf-prov` (WRROC), Snakemake built from Spectio's events.
- LabID: two-way integration proposed (launch from LabID, results and provenance back as a run crate); its API to be confirmed with the MODIS team.
- **Single-user first, multi-user ready**: one schema and one API; single-user = one user, one group, one project created at first start, local requests mapped to that user. Every tenant row has `project_id` and `created_by`; principals cover users, service accounts, AI agents, runners and the system. Authentication (OIDC: EMBL SSO, LS Login) comes later without schema migration. Details in [`api-and-data-model.md`](../specs/api-and-data-model.md).

## 2026-10-25 — Plugin architecture and packaging

- Everything that varies between sites is a plugin, built-ins included (Nextflow, Snakemake, single-user auth, email, local file store). Kinds: engine, launcher, resolver, sink, check, viewer, notifier, auth, AI provider, secrets, blobstore, broker, API extension, CLI extension.
- Snakemake model kept (typed interfaces, settings → CLI flags / env vars, tagged instances, conformance suites, scaffold, catalogue), two changes: standard entry points instead of a `pkgutil` module-prefix scan (which misses editable installs), and several kinds per package (`spectio-plugin-<name>`) because a connection such as LabID is resolver + sink + inbound API.
- One `spectio-sdk` with a version per kind instead of one interface package per type; can be split later.
- The relational database is **not** a plugin (SQLite / Postgres via `DATABASE_URL`); file store, broker and secrets are. Plugins get a context with a scoped API client and never a DB session, so tenancy stays enforced.
- Plugin instances (Snakemake's tags) are stored in `plugin_instances` with scope instance / group / project, or declared read-only in config (GitOps).
- One wheel → Python bundle (`uv tool install spectio`, single process, SQLite), Docker image built from that wheel (Compose profiles minimal / team / proxy / s3 / runner), Helm chart (api, worker, migrate Job, runner sub-chart). No Redis required; Postgres SKIP LOCKED + LISTEN/NOTIFY.
- MinIO CE stopped publishing images (Oct 2025) and is archived: S3 profile uses SeaweedFS, Garage as alternative; to agree with depictio.
- Details: [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md).

## 2026-10-25 — Administration, operations, CLI, depictio ecosystem

- depictio moved from MinIO to SeaweedFS (`weed mini`, image `chrislusf/seaweedfs:4.46`, service `s3` with a `minio` alias, `DEPICTIO_S3_*`, migration script). Spectio uses the same image and version; one shared instance with separate buckets when co-hosted.
- "Settings" becomes **Administration** with depictio's groups People / Content / Activity / Instance and a 208 px section nav; personal tokens move to Profile. Every admin page has a CLI equivalent.
- Users, groups (P.I., pending P.I., SSO-managed, protected `admin` / `users`), project sharing (Owner / Editor / Viewer, launcher and reviewer as an advanced row) and branding (`BrandTheme`, three layers, presets, Import / Export, logo rules) mirror depictio field for field.
- Tasks: `tasks` table is the source of truth (depictio's Job / TaskEvent split), backends in-process / SQL / Celery plugin; schedules by atomic DB claim (no beat). Commands to runners are pulled over HTTPS, not brokered. Events go out through the outbox to webhooks and to MQTT / AMQP / Kafka / NATS bridges (CloudEvents bindings).
- Logs: ring-buffer table with runner, engine and plugin sources; capture floor persisted (depictio's is lost on restart). Health covers every component (depictio checks only Celery).
- Backups: one `tar.zst` archive (manifest with schema revision and checksums, portable JSON Lines DB export, file store, keys, optional encrypted secrets); restore in maintenance mode, forward migration, file restore, orphan cleanup paused. Instance migrations: bundle → Compose (`local export`), SQLite → Postgres, local files → S3, project between instances.
- CLI: one `spectio` command tree (depictio help panels), LabID-style multi-server config, `--json` everywhere, exit codes; base install = CLI + client + runner (< 80 MB, CI-checked; depictio's base is ~0.9 GB). Generated Python and TypeScript clients.
- Shared with depictio and LabID (working names): `bioplatform-client`, `bioplatform-models` (incl. `BrandTheme`), `bioplatform-runinfo` (depictio's `RunInfoReader` + LabID's sniffers).
- First joint use case: run depictio's nf-core validation campaign (`scripts/nfcore_validation_hpc.py`) through Spectio, ending with the depictio hand-off.
- Details: [`admin-and-operations.md`](../specs/admin-and-operations.md), [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md), [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md).

## 2026-10-25 — Schedulers, Kubernetes and monitoring

- Spectio does not re-poll task states: engines already do (Nextflow `squeue … -u $USER` every `queueStatInterval` = 1 min, `--only-job-state` option; Snakemake SLURM plugin sacct/squeue from 40 s backing off to 180 s, job name = run UUID, comment = rule + wildcards). Spectio asks the scheduler only for what engines lack: pending reason + estimated start, accounting and failure class, capacity, reachability.
- One batched query per runner for all jobs of its user (`squeue --me --json` 60 s, `sacct --json` for finished jobs, `sinfo` 5 min, reservations 15 min, `sshare` / `sacctmgr` 30 min, quotas 15 min), back-off, per-site budgets.
- Transports: CLI with `--json` (default), slurmrestd (data_parser v0.0.42–0.0.45 on 26.05, negotiated from `/openapi/v3`), push via `jobcomp/kafka` (completion, start since 25.05) through the Kafka bridge; HTCondor / Flux event logs; Kubernetes watch API + Kueue visibility API (`positionInLocalQueue`).
- Join keys: Nextflow `nativeId`; Snakemake run UUID with `--slurm-jobname-prefix spectio-<run>`; Nextflow pod labels `nextflow.io/runName|taskName|processName|sessionId` + `spectio.io/run-id`.
- Outputs: plain-language pending reasons, failure classes (OOM, timeout, preempted, node failure, image pull…), relaunch suggestions from max RSS and attempts, efficiency and waste, pre-flight checks (walltime vs partition, reservations, quotas, scratch purge).
- Head process as a small long SLURM head job; runner on login node (systemd --user + linger, or cron watchdog), service node with SSH / slurmrestd, or Kubernetes.
- Details: [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md); boards RunScheduler and EnvCapacity.

## 2026-10-25 — Repository, Claude Code setup and pre-implementation playbook

- Documentation moved into `weber8thomas/spectio`. Layout: `docs/specs`, `docs/decisions`, `docs/research`, `docs/reviews`, `docs/playbooks`, `design/`, `tools/canvas`. MkDocs Material site with a strict CI build (broken links fail) and a Mermaid check.
- Before any product code: review rounds R1–R10 (consistency, facts, journeys, constraints, security, API contract vs UI, UI, depictio and LabID drift, landscape, go/no-go), then the development layer (D1–D5), test infrastructure (T1–T6) and planning (P1–P3). Prompts are in `docs/playbooks/next-phase.md`.
- Claude Code setup in the repository:
  - `CLAUDE.md`;
  - eight agents (spec-reviewer, fact-checker, constraints-hunter, security-reviewer, ux-reviewer, depictio-liaison, test-architect, infra-engineer);
  - workflow skills (`review-round`, `apply-findings`, `verify-claims`, `render-board`, `spike`);
  - vendored superpowers skills and Karpathy guidelines (MIT), because cloud sessions do not load plugins.
- Testing against real tools: sind for SLURM (25.11 / 26.05, slurmdbd, slurmrestd, failure simulation), kind with Kueue, fixture workflows with failure injection, golden fixtures named by tool version, one isolated environment per scenario, Playwright e2e and a side-by-side visual report against the canvas boards.
- Staging "fake public instance" on Thomas's VM, behind Tailscale Funnel (ports 443/8443/10000), deployed by CI over the tailnet with an ephemeral tag; cloud sessions never hold tailnet keys.
- Details: `dev-environment-and-testing.md`.

## 2026-10-26 — Autopilot instead of step-by-step prompts

- The playbook steps become nodes of `docs/playbooks/pipeline.yaml` (31 steps, 5 waves). The `/autopilot` skill runs one tick:
  - it picks ready steps, up to 6 in parallel; writers are serialised and builds run in worktrees;
  - it verifies exit checks and triages findings by `triage-policy.md`;
  - it commits to `autopilot/integration` and updates `.autopilot/state.json` and `journal.md`.
- **Driving it:** `/goal` keeps ticking until nothing is ready, with a separate evaluator model; auto mode removes per-tool prompts.
- **Where it runs:** interactively, in a cloud session, headless (`tools/autopilot/run.sh`, with stream-json and `--max-budget-usd`), or as a nightly routine.
- **Large rounds** use dynamic workflows, so the fan-out and cross-checks stay out of the orchestrator's context.
- **Human touchpoints:** the inbox, which is asynchronous (reversible doc-level questions proceed on the recommended option, marked `assumed — pending Thomas`), and the `GO` gate before product code. The autopilot never merges to `main`.
- **Permissions:** the permission rules the autopilot needs are documented for Thomas to add (`autopilot.md` §4). Agents do not modify their own permissions.

## 2026-10-26 — Real pipelines, versioning, staging access and auth parity

- **Synthetic scenarios.** Twin Nextflow and Snakemake pipelines with injected failures run 11 PR scenarios on Nextflow 26.10.3 and 25.10.9 and on Snakemake 9.27.1. All pass.
  - Known engine faults are listed with their log signature. A matching failure is repeated once and reported as `PASS*`.
  - Timeouts are classified from the trace and error text, not the exit code alone.
  - Details: `dev-environment-and-testing.md` §10.1, `schedulers-and-monitoring.md` §3.5, `research/spike-synthetic-pipelines-2026-10-26.md`.
- **Real corpus.**
  - 14 nf-core pipelines and 9 Snakemake Workflow Catalog workflows, run on their own test data in tiers.
  - Pipelines are cloned with git at the pinned tag, not pulled through Nextflow, and resource limits are sized to the runner.
  - nf-core/demo 1.2.0 passes in a cloud session.
  - Details: `dev-environment-and-testing.md` §10.2.
- **Versioning.**
  - Conventional Commit PR titles; release-please with one version train for the core.
  - Image tags `X.Y.Z`, `X.Y`, `sha-<7>`, `edge`, `pr-<n>`.
  - `/api/v1/version` returns `git_sha`, also shown in the UI footer.
  - Details: `dev-environment-and-testing.md` §12.
- **Staging access.**
  - Staging is reached through its Funnel URL, and is verified through that URL after every deploy.
  - Reviewers get scoped share links (magic links bound to one project, role and expiry) instead of shared passwords.
  - Staging runs in `demo` mode and is reset nightly from a backup.
  - Details: `dev-environment-and-testing.md` §13.
- **Authentication.**
  - depictio's modes and methods are kept (single, local, public, demo, magic links, provisioning, OIDC, SAML, depictio trust), and its weak points are fixed: hashed tickets, atomic burn, refresh rotation with reuse detection, a scoped provisioning service account, HttpOnly cookies.
  - Every method is tested in CI with Keycloak and Mailpit.
  - Details: `authentication-and-access.md`.

## 2026-10-26 — Documentation as part of done, telemetry, budget governor

- **Docs are part of the definition of done.**
  - Every step and PR leaves its pages: the Progress page, the owning spec, figures and media.
  - It passes the docs gate (`tools/docs/check.py`: strict build, Mermaid, diagram freshness, media manifest, Progress front matter, PR-body lint).
  - It passes an independent `doc-reviewer` verdict.
  - Writers (`doc-writer`, `diagram-artist`, `media-capture`) and the reviewer are separate agents.
  - Details: `documentation-system.md`.
- **depictio's docs format, without its weak points.**
  - Kept: the landing page structure, the curated per-version changelog, mike versions, sketch figures as light/dark PNG pairs, asciinema casts and screenshot pairs.
  - Changed:
    - no inline CSS on the landing page;
    - casts generated from scripts;
    - combined terminal and browser captures;
    - a strict build on every PR.
- **PR bodies carry the docs.**
  - A PR body contains the docs links, at least one sketch figure for mechanism changes, the media and the evidence.
  - PRs auto-merge into `autopilot/integration` once the required checks and the doc review pass.
  - Auto-merge into `main` is off until Thomas sets `AUTOMERGE_MAIN=true`. Release PRs, workflow, auth and settings changes are never auto-merged.
- **Telemetry.** There are three systems with separate names: install telemetry, local activity analytics, and external web analytics.
  - Install telemetry stays off by default, with an opt-in prompt at `spectio init` and at the first admin sign-in; whether to switch is in the inbox.
  - Web analytics are a `spectio.analytics` plugin kind (GA4, Umami, Plausible, Matomo, PostHog). They are configured at runtime, the server manages the CSP, and paths are sent as templates.
  - Details: `telemetry-and-analytics.md`.
- **Budget governor.**
  - The autopilot runs on a budget set at launch: a number of points of the weekly or 5-hour window, or until the window is used up (stopping at its reset or at a deadline).
  - Readings come from the status line. Between readings, usage is estimated from calibrated cost.
  - The shell loop enforces it before every tick and waits for 5-hour resets.
  - Details: `autopilot.md` §6.
- **The pipeline gained steps:** a W0 wave records the foundations; R11 is the docs review, D6 the docs pipeline in CI, T7 the real corpus green in CI.

## 2026-10-26 — First independent docs review (W0 pages and landing page)

- **Verdicts.** `doc-reviewer` gave `changes` on 6 units and `block` on 2. Both blocks had one cause: the owner's name, initials, home path and cluster name, taken from the design boards, appeared in the screenshots and the video.
- **Fixes:**
  - **Media.**
    - Shots and captures now render a copy of each board with fixture names (`tools/media/fixtures.yaml`) and fail if a forbidden term is visible.
    - The combined video is at most 30 s, and its captions match what is on screen.
    - GIF previews are generated outside `docs/assets/`.
  - **New checks in the docs gate:** video length, no committed GIF, and at most 5 MB of new media per PR.
  - **Lists.** A hook (`hooks/lists.py`) nests lists written with 2-space indentation and adds the blank line before a list. Across the site, nested lists went from 16 to 298, with no code block, admonition or table changed.
  - **Navigation.** Step pages appear in the navigation automatically (`hooks/progress.py`), and specs link back to their step page.
  - **Accuracy.** Swapped Nextflow columns were corrected in the synthetic-pipelines note. The Snakemake fault rate is now the observed 4 of 18 executions. The gate figure says what is measured and what is planned.
- **Spec changes** (`documentation-system.md`):
  - a `foundation` step kind for W0 (§3.1);
  - landing-page key ideas are statements that are measured or marked as planned (§2);
  - design-phase screenshots are light only (§5.1);
  - the per-PR media budget is checked against the base branch (§3.3).
- **Figures not made yet** are tracked in the prompts of the steps that will make them: the staging figure in D5; the share-link and telemetry figures in D6.

## 2026-10-26 — Versioning by importance, the 1.0 gate, adoption

- **Automatic versions by the weight of the change.**
  - While below 1.0: `fix` and `perf` bump the patch, `feat` bumps the minor; a breaking change also bumps the minor (`bump-minor-pre-major`). `docs`, `test`, `ci` and `chore` do not cut a release.
  - During the design phase, `feat` and `fix` are kept for product code, so the first release is the walking skeleton, `0.1.0`.
  - 0.x release PRs merge like other PRs once `AUTOMERGE_MAIN` is on, one per milestone or per wave that changed the product.
  - Details: `dev-environment-and-testing.md` §12.
- **1.0.0 is a human decision.** It requires the 1.0 gate (`dev-environment-and-testing.md` §14):
  - use cases from every scenario class;
  - 3 groups and 10 or more users over 8 weeks;
  - both engines on SLURM and Kubernetes;
  - 4 weeks of green nightly runs;
  - upgrades tested across 3 minors;
  - frozen contracts;
  - complete docs.

  release-please never reaches 1.0.0 on its own, and `release-guard.yml` fails any release PR at 1.0.0 or above unless `ALLOW_V1=true`.
- **Release stages:** walking skeleton (0.1), private alpha with EMBL design partners (0.2–0.4), public beta with a demo instance (0.5–0.9), then 1.0.
- **Adoption and positioning** (`docs/research/adoption-and-positioning-2026-10-26.md`):
  - Spectio is not presented as an open-source Seqera Platform. It is the gate-and-steer layer for self-hosted HPC, Snakemake first, part of the depictio and LabID platform.
  - The plan does not count on nf-core endorsement; nf-core pipelines are used unmodified as test cases.
  - Order of outreach: design partners first, then neighbouring institutes, then the public beta (Snakemake community, BioHackathon Europe, BOSC, registries, JOSS later).
- **Virgil** is set aside for now (inbox #1).
- **Git history.** A clean single-commit `main` was pushed; the old branch is kept until Thomas switches the default and deletes it (inbox #5).

## 2026-10-26 — Dev previews without a server

- **Context.** Thomas has no staging VM, and the institute is behind a VPN that GitHub cannot reach. Dev hosting must cost close to nothing. The public instance for users comes later, on EMBL's Kubernetes, as for depictio.
- **Decision.** The tailnet VM behind Tailscale Funnel is dropped, and `staging.yml` is replaced by `previews.yml` (`dev-environment-and-testing.md` §7, §13):
  - **Static previews on Cloudflare Pages.** The built site is uploaded directly, which works for a private repository. Each PR, validated wave and release gets its own alias; every deployment stays reachable at its own URL; a `/versions` page lists them all. The build SHA is shown in the footer and checked after each deploy.
  - **The full stack on demand in GitHub Codespaces** (`.devcontainer/`), opened from a link on each PR. The free quota is about 60 h a month of a 2-core machine.
  - **The UI in mock mode,** a static build with a fake API, published per version once the UI exists, to compare front-end iterations side by side.
  - **The public instance** at the beta, on EMBL Kubernetes, without depictio's `--insecure-skip-tls-verify`.
- **Rejected, and why:**
  - Hugging Face Spaces: Docker Spaces are no longer free for new accounts (July 2026).
  - Oracle Always Free: halved in June 2026, and account approval is uncertain.
  - A paid VPS: not needed for one developer.
  - Cloud Run: only useful for a public demo, which will be on EMBL instead.
- **Not tested here.** Running the dev container setup in this session was refused (it downloads and runs install scripts). Step D5 checks it in a real codespace.

## 2026-10-26 — Live checks, important stages, one QC for Spectio and depictio

- **Context.** Thomas asked how I/O works and how a lab marks the stages that matter and the files to check while a workflow runs; and how Spectio's QC screens and depictio's dashboards can render the same results in one consistent way.
- **Decision: live checks** ([`checking-scenarios.md`](../specs/checking-scenarios.md) §11):
  - stages get two optional keys, `important` (attention and notifications only) and `watch` (file globs, when to read them, checks, `on_fail`);
  - engines report which file was written (Nextflow `onFilePublish` / `onTaskComplete` in `nf-spectio`, Snakemake `JOB_INFO` + `JOB_FINISHED`); only the runner reads files, and only values travel;
  - `on_fail` is `notify`, `flag`, `open_gate` or `pause_after_stage`; the last two need a conditional stage boundary (an `ext.when` closure on a stop file for Nextflow, **[to be validated]**);
  - results go to `check_results` (now per run, `gate_id` nullable) and the gate reuses them when the file hash is unchanged ([`api-and-data-model.md`](../specs/api-and-data-model.md) §7–8).
- **Decision: one catalogue, two renderers** ([`api-and-data-model.md`](../specs/api-and-data-model.md) §13.6): gate checks bind to depictio catalogue outputs where they exist; the runner computes the same tables at gate time; Spectio writes `spectio_checks` and `spectio_decisions`, joined on the item key in depictio; review views reuse depictio's renderers with a decision layer on top. Five requests added to [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md) §3 (items 7–11).
- **Boards.** RunLiveChecks, WorkflowWatches, ReviewDashboard, DepictioDecisions, on nf-core/rnaseq megatest data (canvas v52).

## 2026-10-26 — Inbox answers: telemetry, merges into main, organisation

- **Install telemetry is opt-out**, like depictio (inbox #2): on by default, with a one-time notice and the payload shown at `spectio init` and the first admin sign-in; nothing is sent before the notice. Applied in [`telemetry-and-analytics.md`](../specs/telemetry-and-analytics.md) §0.4 and §2.3, and in the two specs that said "off by default".
- **Claude may merge into `main` for now** (inbox #3): the autopilot merges the promotion PR with a merge commit once every check passed and doc-reviewer approved. Force-push, branch deletion and edits to `pipeline.yaml` statuses stay forbidden.
- **Packages stay under `weber8thomas`** until Thomas moves them (inbox #9).
- **Nextflow ingestion** (inbox #6) stays open for discussion.

## 2026-10-26 — MVP scope, Nextflow through nf-spectio, licence

- **Nextflow ingestion** (inbox #6, closed): Nextflow reports to Spectio only through the `nf-spectio` plugin, from the MVP on. The Tower protocol routes are not implemented. The goal is to sit next to Seqera Platform, not to replace it: a run can report to both at once (**[to be validated]** in spike T2). Record: [0001](0001-nextflow-through-nf-spectio.md).
- **MVP scope** (Thomas):
  - Snakemake and Nextflow from the start;
  - the focus is on checks and quality control: the checks of a stage, their evidence, and the gate;
  - automatic hand-off to depictio comes later, not in 0.1.

  Applied in [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §14 (0.1 entry condition), [`synthesis.md`](../specs/synthesis.md) §9, the roadmap page and the P1 prompt in [`next-phase.md`](../playbooks/next-phase.md).
- **GA4GH: no change.** The core keeps its own model (events, stages, gates). GA4GH stays at the edges, as already specified ([`api-and-data-model.md`](../specs/api-and-data-model.md) §10, [`synthesis.md`](../specs/synthesis.md) §3):
  - WES 1.1 as a facade;
  - TES as a possible later execution target;
  - TRS and DRS later.

  When the WES facade ships is inconsistent across docs (synthesis §7quinquies and §9, the roadmap page). That is left to review R1.
- **Licence: MIT.** The date the repository goes public is not set (inbox #7).
- **Cloudflare secrets set** (inbox #10).
- **Autopilot permissions** (inbox #4): `tools/autopilot/claude-settings.json` was copied to `.claude/settings.json` on `main` at Thomas's request. The permissions are to be discussed again.
- **Postponed:** the GitHub organisation (#9, unchanged) and the questions for EMBL IT.

## 2026-10-27 — First version is 0.0.1: a basic local MVP

- **Context.** The review rounds proposed a 0.1 cut with SLURM, a remote runner and many security prerequisites (inbox #11–#16). Thomas found it far too heavy for a first version.
- **Decision (Thomas, by voice).** The first version is **0.0.1**, and it is basic:
  - one user, no authentication, no roles;
  - the engines run on the same machine as Spectio, with their local executor. Spectio manages no SLURM or Kubernetes, and there is no remote runner.
- **In 0.0.1:**
  - launch a run from the UI;
  - monitor it: run state, number of jobs / tasks, stages;
  - relaunch it, including with changed parameters;
  - track parameters across runs: which parameters each run used, and what changed;
  - a simple QC check and gate on one stage, then resume or relaunch, in its simplest form. Thomas said "maybe"; it stays in because the 2026-10-26 decision keeps checks and gates in focus;
  - both engines: Snakemake through the logger plugin, Nextflow through `nf-spectio` ([0001](0001-nextflow-through-nf-spectio.md)).
- **Not in 0.0.1:**
  - multi-user, authentication, roles, OIDC / SAML, share links;
  - SLURM and Kubernetes launchers, scheduler monitoring;
  - Postgres, Docker Compose, Helm;
  - the depictio hand-off;
  - WES, MCP, embedded elements;
  - LabID.
- **Stays open.** What comes after 0.0.x, and in which order, is not decided and nothing is assumed (inbox #16, *partly handled*). Inbox #11, #12, #14 and #15 are not needed for 0.0.1 and stay open for later versions. The private alpha, public beta and 1.0 stages keep their entry conditions; the stage between 0.0.x and the private alpha is not defined yet.
- **First tag.** The first release commit carries `Release-As: 0.0.1`. Without it, release-please would propose 1.0.0 from the `0.0.0` manifest, which the release guard blocks ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15.2, sourced from release-please's code).
- **Autopilot budget** (inbox #31): Thomas read 57 % on 2026-10-27, so 7 of the 15 points are spent; APPLY1 continues with an 8-point budget.
- **Specs and pages changed:**
  - [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md): new §15 (single owner of version contents, and how the first tag is made); §14 first row is now "0.0.x · Local MVP"; §12 no longer plans the first release as 0.1.0;
  - new page [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md): each 0.0.1 feature with its owning spec sections and UI boards; added to the nav and to the documentation map;
  - [`synthesis.md`](../specs/synthesis.md) §9 (dated revision note), [`documentation-system.md`](../specs/documentation-system.md) §1 (Installation and Changelog rows);
  - the landing page, the roadmap, the installation, changelog, API and feature pages;
  - the P1 and R10 prompts in [`next-phase.md`](../playbooks/next-phase.md);
  - inbox #11, #12, #14, #15, #16 and #31.

## 2026-10-27 — APPLY1: review findings applied (R1 R2 R4 R5 R7 R8 R8b R9 R11)

- **Context.** APPLY1 applies the findings that TRIAGE1 accepted or assumed, in the nine rounds listed. It changes the owning specs only, and adds no version claims outside [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15. Each finding's **Status** line in its review file says what was applied and what is pending. Overlapping findings were applied once, in the wording of the most recent round (for example CH-001 over SR-017, FC-007 over SR-037, FC-040 over CH-009, DEP-T-018 over FC-013). Total: 60 applied, 148 partly applied, 24 not applied. "Partly" mostly means that the doc edits are done and a board, tool, CI or blocked part remains.
- **Per round** (applied / partly / not applied):
  - **R1** ([R1-consistency](../reviews/R1-consistency.md)), 11 / 26 / 1. Applied: SR-008, SR-011, SR-026, SR-032, SR-042, SR-045, SR-046, SR-049, SR-051, SR-052, SR-053. Partly: SR-003, SR-004, SR-005, SR-006, SR-009, SR-012, SR-013, SR-015, SR-016, SR-017, SR-019, SR-022, SR-027, SR-028, SR-034, SR-036, SR-037, SR-038, SR-039, SR-040, SR-041, SR-043, SR-044, SR-047, SR-048, SR-050. Not applied: SR-035 (blocked, inbox #25).
  - **R2** ([R2-open-validations](../reviews/R2-open-validations.md)), 25 / 8 / 2. Applied: FC-004–FC-007, FC-009–FC-012, FC-014, FC-015, FC-017–FC-020, FC-022–FC-027, FC-031–FC-035. Partly: FC-001, FC-008, FC-013, FC-016, FC-029, FC-030, FC-036, FC-037. Not applied: FC-002 (blocked, inbox #19), FC-021 (already fixed by CH-001 and CH-006).
  - **R4** ([R4-constraints](../reviews/R4-constraints.md)), 8 / 28 / 1. Applied: CH-014, CH-018, CH-019, CH-024, CH-029, CH-033, CH-035, CH-039. Partly: CH-001, CH-002, CH-003, CH-005–CH-013, CH-015–CH-017, CH-020–CH-023, CH-025–CH-027, CH-031, CH-032, CH-036–CH-038, CH-040. Not applied: CH-028 (blocked, inbox #14, #25).
  - **R5** ([R5-security](../reviews/R5-security.md)), 2 / 7 / 1. Applied: SEC-125, SEC-130. Partly: SEC-103, SEC-105, SEC-107, SEC-110, SEC-112, SEC-123, SEC-126. Not applied: SEC-129 (blocked, inbox #15, #20, #21).
  - **R7** ([R7-ui](../reviews/R7-ui.md)), 0 / 27 / 6. Partly (spec text done, boards pending): UX-203, UX-205, UX-207–UX-210, UX-212–UX-216, UX-218–UX-221, UX-223–UX-226, UX-228–UX-235. Not applied (board-only fixes, no spec edit needed): UX-211, UX-222, UX-236–UX-239.
  - **R8** ([R8-depictio](../reviews/R8-depictio.md)), 1 / 8 / 2. Applied: DL-114. Partly: DL-103, DL-105–DL-108, DL-110, DL-111, DL-113. Not applied: DL-109 (blocked, inbox #21, #26), DL-115 (blocked, inbox #26).
  - **R8b** ([R8b-depictio-tooling](../reviews/R8b-depictio-tooling.md)), 1 / 22 / 3. Applied: DEP-T-012. Partly: DEP-T-001, DEP-T-002, DEP-T-004–DEP-T-006, DEP-T-009–DEP-T-011, DEP-T-014, DEP-T-016–DEP-T-024, DEP-T-027, DEP-T-029–DEP-T-031. Not applied: DEP-T-003 (blocked, inbox #26), DEP-T-013 (blocked, inbox #23), DEP-T-025 (blocked, inbox #17).
  - **R9** ([R9-landscape](../reviews/R9-landscape.md)), 5 / 9 / 1. Applied: FC-043, FC-049, FC-052, FC-053, FC-054. Partly: FC-038–FC-042, FC-044–FC-047. Not applied: FC-050 (blocked, inbox #17, #26).
  - **R11** ([R11-docs](../reviews/R11-docs.md)), 7 / 13 / 7. Applied: DOC-004, DOC-006, DOC-007, DOC-014, DOC-015, DOC-016, DOC-027. Partly: DOC-001, DOC-002, DOC-003, DOC-005, DOC-008–DOC-013, DOC-019, DOC-020, DOC-022. Not applied: DOC-017, DOC-021, DOC-023–DOC-026 (tool or stylesheet fixes only), DOC-018 (its shots do not exist yet).
- **Specs changed** (new sections keep the existing numbers; nothing was renumbered):
  - [`admin-and-operations.md`](../specs/admin-and-operations.md): header, §0, §1, §2.1, §3.1 (background tasks: ledger renamed `background_tasks`), §3.2, §3.4, §3.5, §4.1–§4.5, §5, §6;
  - [`api-and-data-model.md`](../specs/api-and-data-model.md): §2, §3 (kinds table removed, owned by architecture §2), §4, §5, §7, new §7.1 (run and gate state machines), §8, new §8.1–§8.4 (event pipeline, ordering, live streams, retention), §10, §11, §12, §13.3, §13.5, §13.6;
  - [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md): §0, §1, §2, new §2.1 (secrets on runners), §3.1, §3.5, §4, §5, §6 (diagram and dependency rules), §7.2–§7.6, §8–§11, new §12 (compatibility between components), new §13 (engine bridges, §13.1–§13.6);
  - [`authentication-and-access.md`](../specs/authentication-and-access.md): new §3.1 (browser hardening), §4, §5;
  - [`checking-scenarios.md`](../specs/checking-scenarios.md): §0, new §4.1 (keys of each check kind), §9, §11.1–§11.5, new §12 (`spectio.yml` reference, §12.1–§12.7);
  - [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md): §0–§6;
  - [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md): §2, §3 (requests turned into a dated status table);
  - [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md): §0, §1, §3 (now a pointer to §10.1), §4.1, §4.2, §5, §6, §7.1, §8, §9, §11, §12, §14;
  - [`documentation-system.md`](../specs/documentation-system.md): §0, §1, §2, §3.2, §3.3, §5.1, §5.2, §6, §8, §9, §10;
  - [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md): §0–§4, §7, §8, §10, §11, §12;
  - [`synthesis.md`](../specs/synthesis.md): §1–§5ter, §7–§10 (dated "superseded" notes where a newer spec owns the topic);
  - [`telemetry-and-analytics.md`](../specs/telemetry-and-analytics.md): §0, §2.3, §2.4, §4.2, §5;
  - [`ui-spec.md`](../specs/ui-spec.md): §1, §2, §3.1, new §3.3 (system states), new §3.4 (colour use and contrast), §4.1, §4.3–§4.11, §5, §5.1, §6, §7, §9, §10.1, §10.2, new §11 (component states);
  - pages: [`map.md`](../map.md), [`api/index.md`](../api/index.md), [`features/index.md`](../features/index.md), new [`features/other-tools.md`](../features/other-tools.md), [`index.md`](../index.md), [`installation/index.md`](../installation/index.md), [`usage/index.md`](../usage/index.md), [`next-phase.md`](../playbooks/next-phase.md) (T1–T4, P1, D6), [`autopilot.md`](../playbooks/autopilot.md) §7, new research note [`depictio-audit-2026-10-26.md`](../research/depictio-audit-2026-10-26.md), [`depictio-harmonization.md`](../research/depictio-harmonization.md) §1.3, [`depictio-qc-integration-2026-10-26.md`](../research/depictio-qc-integration-2026-10-26.md) §1.2, §1.4, §2, §3, and the Progress pages W0 F1–F7, the nine W1 pages and W2 TRIAGE1 (front matter `review_score`, pre-squash notes, superseded notes).
- **Revisions of earlier decisions** (recorded here, as the findings asked):
  - **Snakemake steering** (SR-008, with CH-009): Snakemake runs as a CLI head job (`--until`, `--forcerun`, `--configfile`), not through the API. The 2026-10-25 constraint is restated as "no parsing of process output for tracking" (synthesis §2, §5ter) *(assumed — pending Thomas, inbox #28)*.
  - **"Broker" wording** (SR-049): the 2026-10-25 entries that say "broker" mean the three extension points "task backend, pub/sub, event bridge" (architecture §2). api §3 no longer keeps its own kinds table.
  - **Shell** (SR-053): the top bar spans the full width, with the logo and the colour mode, and the sidebar sits below it (ui-spec §2). This revises the 2026-10-25 "UI review round 2" shell. List views use a "table / rows" toggle, since the card grid was dropped *(assumed — pending Thomas, inbox #29)*.
  - **Raw engine payloads** (CH-011): kept while the run is active, then archived (api §8.4). This revises "keep the raw JSON" in synthesis §2ter *(assumed — pending Thomas, inbox #28)*.
  - **Projections** (CH-012): one projector builds the read models after the ingest ack, not in the same transaction (api §8.1). This revises synthesis §4 *(assumed — pending Thomas, inbox #28)*.
  - **Backups** (CH-022): native same-engine backups by default, JSON Lines only for migration and export (admin §4.3). This departs from the 2026-10-25 JSON-backup decision *(assumed — pending Thomas, inbox #24)*.
  - **SLURM poll** (CH-027): the routine poll is plain-text `squeue --me` with a fixed format (job name last), and `--json` is kept for details (schedulers §3.2–§3.3). This revises the 2026-10-25 "JSON CLI" choice *(assumed — pending Thomas, inbox #28)*.
- **Assumed decisions.** Each is marked in the text "*(assumed — pending Thomas, inbox #n)*" and can be reverted by removing what that marker covers:
  - #12 (runner transport): CH-007 (`runner_commands`), CH-032 (proxy and CA bundle);
  - #13 (embeds and streams): SEC-112;
  - #14 (secrets on runners): SEC-103;
  - #17 (roadmap, WES): UX-210, FC-044, FC-046;
  - #18 (share links): SR-019;
  - #22 (depictio hand-off): DL-105, DEP-T-014, DEP-T-017 (DL-115 assumed but blocked);
  - #23 (co-hosting): SEC-126, DL-103;
  - #24 (backups and restore): SR-050, CH-021, CH-022;
  - #25 (runner confinement, imports): SEC-105, SEC-110;
  - #26 (CI and release rules): UX-219, DEP-T-001, DEP-T-002, DEP-T-005, DEP-T-018, DEP-T-029;
  - #27 (outreach): SR-036, SEC-107, DL-113, FC-042;
  - #28 (engine bridges and runner): SR-003, SR-006, SR-008, SR-017, SR-022, SR-047, SR-048, FC-001, CH-001, CH-002, CH-003, CH-005, CH-006, CH-008, CH-009, CH-011, CH-012, CH-016, CH-025, CH-027, FC-038, FC-040, FC-052 (SR-035 assumed but blocked);
  - #29 (names and model): SR-004, SR-005, SR-012, SR-013, SR-015, SR-016, SR-026, SR-032, SR-034, SR-041, SR-042, SR-046, SR-052, SR-053, FC-025;
  - #30 (UI and docs process): UX-207, UX-209, UX-216, UX-226, UX-234, DOC-001, DOC-003, DOC-004, DOC-005, DOC-007.
- **Stale references fixed in this step:** ui-spec §2, the Review row read "Interventions waiting for a decision" (it now says "Gates", SR-012); admin §6, the board list now names the "Background tasks" screen, and notes that board `AdminTasks` is still labelled Tasks (SR-005). Stale names left in place because their sections are blocked: depictio-ecosystem-reuse §1.1 (`tasks` table, "Settings → Version check", inbox #26), api §13.1 (`~/.spectio/config.yaml`, inbox #21), api §6 ("Flat in v1", inbox #13–#15), checking §11.3 (`nf-toy`, inbox #19), auth §2 (plugin `auth-oidc` / `auth-saml`, inbox #20, #21), schedulers §5 (inbox #26).
- **Deferred: UI boards** (by board):
  - Legend: SR-016, UX-205, UX-212;
  - RunsTable and the run lists: SR-016, UX-207, UX-236;
  - RunDetail: SR-040, SR-041, CH-006, UX-207, UX-216, UX-223, UX-236;
  - RunDetailDegraded: UX-205;
  - Main: SR-040;
  - RunScheduler: CH-027, UX-205, UX-212, UX-222, UX-223, UX-237;
  - RunObserved and Profile: UX-222;
  - Overview: UX-205, UX-207, UX-213;
  - OverviewFirstRun, RunsEmpty, ReviewQueueEmpty and MEmpty: UX-211;
  - Review, with the 11 Review* boards: CH-010, UX-238;
  - ReviewReport and ReviewDashboard: SR-041, DL-103;
  - ReviewQueue: UX-207, UX-213, UX-218, UX-236;
  - RelaunchDialog: CH-010;
  - Launch: CH-016, SEC-110, UX-216, UX-235, UX-236;
  - LaunchChain: UX-235;
  - Workflow boards: UX-221 (WorkflowVersions, Workflows, WorkflowSnakemake, WorkflowImport, WorkflowOverlay, WorkflowWatches), UX-222 (WorkflowsCatalog, WorkflowDiscovered), CH-016 (WorkflowOverlay), SEC-110 (WorkflowImport), UX-237 (WorkflowSnakemake);
  - Environments, EnvKubernetes and EnvStorage: UX-205, UX-209, UX-212, UX-223, UX-228, UX-237;
  - EnvCapacity: CH-026, UX-205, UX-235;
  - RunnerOffline: CH-001;
  - SignIn, MagicLinkSent, MagicLinkConfirm, MustChangePassword, the reset landing and the SSO callback error: UX-203;
  - AppTopbar: SR-039;
  - AdminNav and AdminTasks: SR-005, UX-208, UX-215, UX-228;
  - AdminHealth: CH-002, CH-013, UX-239;
  - AdminLogs: CH-038;
  - AdminRestore: CH-021, UX-237;
  - AdminBackups: CH-022;
  - AdminMaintenance: UX-229, UX-235;
  - AdminBranding: UX-212, UX-226;
  - AIAgents: UX-212;
  - AdminEvents, AdminAudit, AdminNotifications and AdminSettings: UX-208;
  - AdminSingleUser: UX-215;
  - SettingsServiceAccounts: UX-228;
  - admin boards titled "Settings": SR-039;
  - DepictioDecisions: DL-108;
  - Landing: DOC-001, FC-044 (WES item, inbox #17);
  - phone boards:
    - MobileTopbar: UX-205, UX-210, UX-214, UX-220, UX-230, UX-233;
    - MobileTabbar: UX-235;
    - MRunnerOffline: CH-001, UX-213;
    - MReview, MReviewCells and MReviewQueue: UX-213, UX-218, UX-233, UX-234, UX-235;
    - MRuns and MRunDetail: UX-232, UX-233, UX-234;
    - MLaunch: UX-234;
    - MWorkflows: UX-213, UX-235;
    - MAdmin: UX-214, UX-215, UX-235;
    - MMore: SR-039, UX-230;
    - MOverview: UX-230;
    - MNotifications and the desktop bell: UX-210;
    - MProfile, MSearch, MWorkflowDetail, MEnvironmentDetail and MAdminSection: UX-231;
    - MProjectSwitcher: UX-224;
  - keyboard and labels on 21 boards: UX-219;
  - 44 px hit areas on the phone boards: UX-220;
  - board data and the shared fixture: UX-225;
  - tokens (`design/tokens/spectio-tokens.css`): UX-212.
- **Deferred: tools and CI:**
  - workflows:
    - `ci.yml` with `ci-ok`, and the pipeline workflows as `workflow_call`: DEP-T-001;
    - GitHub App token in `release-please.yml`: DEP-T-002;
    - `quick-start.yml` and multi-arch builds: DEP-T-004, DEP-T-021;
    - `security.yml`, attestations and signing: DEP-T-005;
    - the publishing workflow: DEP-T-006;
    - `renovate.json` and actions pinned by SHA: DEP-T-009;
    - `chart.yml`, with the first-install case: DEP-T-010, FC-008;
    - `upgrade.yml`: DEP-T-011;
    - `base-install.yml` and the import-linter allow-list: DEP-T-018, SR-027;
    - the workflow conventions applied to the existing workflows: DEP-T-019;
    - `deploy-audit.yml`: DEP-T-020;
    - the release-notes check: DEP-T-021;
    - `nextflow-edge.yml`, plus 25.04.x in the Nextflow matrix of dev-env §5 and §11: CH-006;
    - the runtime axis in `pipelines-slurm.yml`: CH-025;
    - the minimum Snakemake version: FC-040;
    - nf-prov pins: FC-045;
    - the rocrate-validator step: FC-041;
    - the migration-time budget: CH-023;
    - `docs.yml` on Node 24: FC-013;
    - the admin-operation → CLI-command test: SR-006;
  - tools:
    - the `spectio.yml` JSON Schema and `spectio workflow validate`: SR-004;
    - `dev/doctor.sh`: SR-047;
    - `DEPICTIO_VERSION` in `dev/versions.env`: DEP-T-017;
    - `.pre-commit-config.yaml`: DEP-T-022;
    - the collection guard and diff coverage: DEP-T-023;
    - the telemetry field-docs generator and the traffic snapshot: DEP-T-024;
    - `include-component-in-tag`: DEP-T-027;
    - `tools/docs/check.py`: DOC-002, DOC-003, DOC-012;
    - `tools/docs/render_landing.js`: DOC-011;
    - media (synthetic-gate cast and combo, cloud-env replay, `sketch.py` font check, the three diagram scripts, the `run-failed`, `run-outputs` and `*_crop` shots): DOC-008, DOC-009, DOC-010, DOC-017, DOC-018, DOC-019;
    - `hooks/progress.py` and `public_title` in `pipeline.yaml` (titles only, no status edits): DOC-021, DOC-022;
    - board lint with a contrast check (spike S-R7-1): UX-219, UX-235;
    - the shared board fixture (spike S-R7-2): UX-225;
    - tests: a squid proxy (CH-032) and a slow-FUSE `stat` (CH-037);
  - site:
    - `docs/stylesheets/extra.css`: DOC-005, DOC-012, DOC-019, DOC-020, DOC-021, DOC-022, DOC-023–DOC-026;
    - `overrides/main.html`: DOC-013, DOC-020;
    - `mkdocs.yml`: `repo_url` (DOC-013), and nav entries for `features/other-tools.md` (FC-047) and `research/depictio-audit-2026-10-26.md` (DL-111);
  - skills: `autopilot` and `write-docs` record the doc-reviewer verdict: DOC-003.
- **Deferred: CLAUDE.md and agents:** the External facts rule cites the tag, the SHA and the `git archive` sha256 (DEP-T-031); keyboard rules in the board conventions (UX-219, inbox #26). Both wait for Thomas.
- **Deferred: for Thomas** (outside the repository): create the GitHub App (inbox #8, DEP-T-002); trusted publishers (DEP-T-006); the Renovate app (DEP-T-009); the EMBL egress probe (CH-001); requests and reports to depictio (SR-036, DL-113, DEP-T-014, inbox #27); `spk_` secret-scanning registration (SEC-107); FlowO and Snakemake docs outreach (FC-042).
- **Deferred: blocked by inbox** (sections not edited):
  - #11, api §14 (ingest contract): SR-006, SR-017, SR-022, SR-038, SR-048, CH-001, CH-002, CH-005, CH-011;
  - #12, architecture §7.7 (runner transport): SR-027, CH-002, CH-007, CH-021, CH-032;
  - #13–#15, api §6: SR-004, SR-006, SR-019, SR-043;
  - #13, api §4 limits and api §9: FC-036, CH-008, SEC-112;
  - #14, runners schema, gate assignment and schedulers §6: SR-012, UX-207, CH-026, CH-028, CH-031, SEC-103, SEC-105;
  - #15, auth §1, auth §6 and api §1: SR-013, CH-015, SEC-123, SEC-126, SEC-129;
  - #16, run verbs and states, stage tags and dev-env §15: SR-004, SR-016, SR-036, SR-043, CH-003, DL-105, FC-039;
  - #17, roadmap ideas, the landing page's WES item, LaunchReview and dev-env §14: UX-216, DEP-T-025, FC-044, FC-046, FC-050;
  - #18, share links and the guest kind: SR-006, SR-019, UX-203, UX-224, DL-108;
  - #19, checking §5, §7 and §11.3, and the MCP catalogue: SR-004, SR-012, SR-036, SR-047, FC-001, FC-002, CH-010, SEC-110;
  - #20, users and groups, sessions, environments API and auth §2: SR-013, SR-034, SR-044, SEC-123, SEC-129, UX-203, UX-208, UX-209, UX-215, UX-228, UX-231, DL-110;
  - #21, api §13.1–§13.2, auth §2 and the depictio chart: SR-009, SR-013, SR-019, SR-044, DL-108, DL-109, DL-110, DL-113, DEP-T-010, DEP-T-030;
  - #22, api §13.3 step 1 and `doctor`: DL-105, DL-106, DL-107, DEP-T-016;
  - #23, co-hosting and api §13.4: DL-108, DEP-T-013, SEC-126;
  - #24, admin §4.3 restore wizard and encryption: SR-038, SR-050, CH-021;
  - #25, architecture §3 and §7.6, schedulers §0, §3.3 and §6: SR-003, SR-009, SR-015, SR-022, SR-035, CH-009, CH-012, CH-020, CH-028, CH-036, SEC-103, SEC-105, FC-045, UX-221;
  - #26, depictio-ecosystem-reuse §1, architecture §7.4, schedulers §5 and autopilot.md §8: SR-005, SR-028, SR-036, SR-039, FC-001, FC-016, FC-037, CH-008, DL-103, DL-109, DL-111, DL-115, DEP-T-001–DEP-T-005, DEP-T-014, DEP-T-018, DEP-T-020, DEP-T-029, FC-038, FC-050.
- **Gate.** `mkdocs build --strict` passes; `python3 tools/docs/check.py` reports 0 failures; the four Mermaid blocks in the changed files render with mermaid-cli 11.

## 2026-10-27 — Context compaction thresholds per agent

- **Decision (Thomas):** the session-wide auto-compact window is 400k tokens (`autoCompactWindow` in `.claude/settings.json` and in `tools/autopilot/claude-settings.json`).
- **Per agent** (frontmatter `autoCompactWindow`):
  - 600k for the reviewers that read whole specs or many sources;
  - 200k for `doc-reviewer`, and for the code agents once they are merged.
- Why the values and the remaining checks: [`autopilot.md`](../playbooks/autopilot.md) §4. Sources: [model config](https://code.claude.com/docs/en/model-config), [subagents](https://code.claude.com/docs/en/sub-agents).

## 2026-10-27 — Code review and simplification after every build step

- **Gap found:** the `build` steps of W3 had no code review. Only P3 asked for one, through subagent-driven-development. The Karpathy guidelines were a rule in `CLAUDE.md`, not a check.
- **Decision (Thomas):** add two agents and one skill.
  - `code-reviewer`: read-only, fresh context; returns approve / changes / block.
  - `code-simplifier`: behaviour-preserving, on the step's own diff only.
  - `review-code`: chains them, with at most two fix rounds by the worker and the tests re-run after each change.
- **Where it runs:** step 3 of the autopilot verification, before the docs ([`autopilot.md`](../playbooks/autopilot.md) §9). In P3, the task reviewer of subagent-driven-development gets Karpathy §2–3 as global constraints, and `review-code` runs once on the whole branch. The vendored superpowers skills stay unchanged (`.claude/skills/THIRD_PARTY.md`).
- **Docs:** a `build` Progress page carries the `CODE` line and links `docs/reviews/code/<step>.md` ([`documentation-system.md`](../specs/documentation-system.md) §3.1).
