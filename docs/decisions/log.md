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

Step page: [APPLY1](../progress/W2/APPLY1.md).

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

## 2026-10-27 — A sketch for every step

- **Decision (Thomas):** every pipeline step gets more Excalidraw-style visuals, to make reviewing clearer and simpler.
- **Rule:** every step leaves at least one sketch pair, placed first on its Progress page. This includes review, triage and apply steps, which needed none before. A review round also puts its map at the top of the review file ([`documentation-system.md`](../specs/documentation-system.md) §3.4; minimum per step kind in §3.1).
- **Checked:** `check_progress` in `tools/docs/check.py` fails a `done` Progress page that has no light/dark pair. The 13 pages finished before the rule are listed in `FIGURE_EXEMPT` until they get their figure.
- **Who:** `diagram-artist` draws the figures. `write-docs`, `review-round`, `doc-writer` and `doc-reviewer` were updated to match.

## 2026-10-27 — APPLY2: review findings applied (R3 R6)

Step page: [APPLY2](../progress/W2/APPLY2.md).

- **Context.** APPLY2 applies the findings that TRIAGE2 accepted or assumed in rounds R3 and R6. It changes the owning specs only, adds no 0.0.1 feature and no version claims outside [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15. Each finding's **Status** line in its review file says what was applied and what is pending. Findings that wait for Thomas (SR-054, SR-056, SR-057, SR-058, SR-067, SR-080, SR-091) were not touched. Overlapping findings were applied once: UX-291 over UX-250 (CPU-hours copy), CH-042 over CH-050 (the run lattice applies per run, inbox #32), SR-081 with SR-063 (cli `relaunch`), SR-066 inside the SR-082 paragraph (checking §12.3), UX-272 through SR-088, UX-284 through SR-085, and CH-043 with UX-288. Total: 7 applied, 47 partly applied, 0 not applied. "Partly" means that the doc edits are done and a board, spike, tool or blocked part remains.
- **Per round** (applied / partly / not applied):
  - **R3** ([R3-journeys](../reviews/R3-journeys.md)), 7 / 15 / 0. Applied: CH-043, SR-064, CH-046, SR-059, SR-065, CH-045, SR-066. Partly: SR-062, SR-055, CH-041, CH-042, SR-061, CH-047, SR-063, CH-044, CH-048, CH-049, CH-050, UX-243, UX-250, CH-051, UX-249.
  - **R6** ([R6-contract](../reviews/R6-contract.md)), 0 / 32 / 0. Partly: SR-081–SR-090, UX-270–UX-291.
- **Specs changed** (new sections take new numbers; nothing was renumbered):
  - [`admin-and-operations.md`](../specs/admin-and-operations.md): §3.1;
  - [`api-and-data-model.md`](../specs/api-and-data-model.md): §4, new §4.1 (wire conventions), §5 (Public, Workflows, Runs, Tasks & logs, Gates, Artefacts, Events rows), new §5.1 (run actions), new §5.2 (launch body), §7 (tables, new `run_stages` with `stage_id` replacing `stage_index`, erDiagram, computed run fields), §7.1, new §7.2 (task and attempt states), §8 (envelope and catalogue), §8.1, §8.2, new §8.5 (stream frames);
  - [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md): §7.1, §7.2, §13.1, new §13.7 (log sources per engine);
  - [`checking-scenarios.md`](../specs/checking-scenarios.md): §4, §12.3, §12.4;
  - [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md): §2;
  - [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md): §15.1;
  - [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md): §1, §2;
  - [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md): new §3.1.1 (local launcher: detach, adopt, exit), §3.5;
  - [`synthesis.md`](../specs/synthesis.md): §2ter, §5ter intro, §5ter.2, §5ter.4, §5ter.5, §5ter.6 (dated "superseded" notes where a newer spec owns the topic);
  - [`ui-spec.md`](../specs/ui-spec.md): §2, §3.1, §3.2, §4.3, §4.4, §4.5, §4.6, §8, §11.
- **Revisions of earlier decisions:**
  - **Relaunch model** (SR-081, CH-042, inbox #32, path B): every relaunch, including Resume after a failure, is a new child run, and the parent stays terminal. `:resume` applies only to a paused run (synthesis §5ter, api §5.1) *(assumed — pending Thomas, inbox #32)*.
  - **0.0.1 gate verbs** (SR-062, SR-085): `approve` and `stop`; `apply` and `go_back` return 422 not-in-this-version (api §5, synthesis §5ter.2) *(assumed — pending Thomas, inbox #32)*.
  - **Idempotency replay** (SR-090): a reused Idempotency-Key with a different body returns 409 `idempotency-key-reused`, not 422 (api §4.1).
  - **Snakemake config** (SR-065): the run config goes through `--configfile`, never `--config` (synthesis §5ter.5, api §5) *(assumed — pending Thomas, inbox #40)*.
  - **Task states** (SR-083): api §7.2 owns the task and attempt state enums, in lower case; the upper-case list in synthesis §2ter is superseded.
  - **dev-env §15.1** (SR-062): the 0.0.1 gate row names the gate verbs `approve` and `stop`, a parameter change at a gate is Relaunch… (a child run), and `apply` and `go_back` move to the later column. This is a change of wording inside §15, not a new feature *(assumed — pending Thomas, inbox #32)*.
- **Assumed decisions.** Each is marked in the text "*(assumed — pending Thomas, inbox #n)*" and can be reverted by removing what that marker covers. 33 findings in all:
  - #32 (relaunch at a gate, resume, 0.0.1 gate verbs): SR-062, CH-042, SR-063, UX-243, SR-081, SR-085, UX-280, UX-281, UX-282, UX-284;
  - #33 (default when every check passes): SR-059;
  - #35 (engines and the in-process runner): SR-055, CH-041;
  - #38 (engine events and the progress denominator): SR-084, SR-088, UX-272;
  - #39 (the reads that 0.0.1 boards need): UX-274, UX-275, UX-278, UX-279, UX-285, UX-286, UX-291;
  - #40 (fixes that are right but not local): SR-061, CH-047, CH-043, CH-046, CH-048, CH-050, SR-065, UX-250, CH-051, SR-082.
- **Stale references fixed in this step:** synthesis §2ter, the upper-case "Normalised statuses" list now carries a dated superseded note that points to api §7.2 (SR-083). Left in place: `stage_index` and `expected_tasks` survive only as quotes in the review files; ui-spec §4.11 (phone Run detail) still names "Pause after stage", outside UX-289's scope since phones are not in 0.0.1.
- **Deferred: UI boards** (by board):
  - ReviewReport: SR-062 (GateSimple variant), SR-085, UX-283, UX-284, UX-285;
  - RunDetail: SR-062 (awaiting-review and after-decision frames), SR-061 ("Starting" and "Engine did not start" frames), UX-249 (aside), UX-250 (Lineage aside), SR-081 (Resume label), SR-082, UX-270, UX-271, UX-272, UX-273, UX-279, UX-282 (Lineage tab), UX-283, UX-286, UX-287 (processes table), UX-288, UX-289;
  - RunDetailReconnect: CH-041, CH-051;
  - RunFailed (local variant): CH-047;
  - RunTasks and RunLogs (to be drawn): CH-048;
  - RelaunchDialog: UX-243, SR-081, UX-280, UX-281;
  - Launch: SR-061 (button states), SR-087, UX-276, UX-277, UX-279;
  - LaunchSnakemake: SR-087, UX-276, UX-277;
  - RunsTable: UX-250 (selection), SR-088, UX-270, UX-274;
  - RunsRows: SR-082, SR-088, UX-271, UX-272, UX-274;
  - RunsCompare: UX-250 (0.0.1 variant), UX-291;
  - Legend: SR-082, UX-290;
  - Manifest: UX-278;
  - EnvLocal (0.0.1 variant) and the first-run Overview link (UX-211): SR-055;
  - shared components AppSidebar (footer live state: CH-041) and AppTopbar: UX-275.
- **Deferred: tools and spikes:**
  - spike openapi draft: SR-081, SR-082, SR-083, SR-084, SR-085, SR-086, SR-089, SR-090;
  - engine mapping checked in spike T2: SR-083;
  - `spectio-sdk` JSON Schemas: SR-084;
  - later api compare endpoints: UX-291.
- **Deferred: blocked by inbox** (sections not edited):
  - #34, inline `gates` value, cli `--gates FILE`, `POST /workflows` import body and checking §12.7 overlays: SR-063, SR-086 (with SR-056), SR-087, UX-278;
  - #35: no blocked doc part; architecture §7.3 "0.0.1 prerequisites" (SR-067) was left for Thomas;
  - #36, api §14 and architecture §13.2 (ingest numbers and wording, workdir in the first task delta, nf-spectio aggregated cached events, planned count): CH-044, CH-048, CH-050, SR-084, UX-272;
  - #37 (with #13–#15), api §6 built-in local environment: SR-055;
  - #13, api §4 limits: SR-090;
  - #16, pause and stop transitions, `:pause` verb, `CONTINUE_REQUESTED` lock wait: CH-042, SR-063, SR-081, UX-289;
  - #19, checking §5 gate verbs: SR-085;
  - #20, `GET /environments/{id}/files`: UX-276;
  - #25, architecture §7.6 claiming and lease renewal: CH-049.
- **Gate.** `mkdocs build --strict` passes; `python3 tools/docs/check.py` reports 0 failures.

## 2026-10-27 — 0.0.1 revised: on the cluster, no gates, a token link

- **Context.** Later the same day, Thomas revised the cut of [2026-10-27 — First version is 0.0.1](#2026-10-27-first-version-is-001-a-basic-local-mvp): 0.0.1 must be "the simplest possible to start, easily shareable with users to test, without the complexity of the full product". This entry replaces that cut where they differ; the rest of it (one user, the first tag with `Release-As: 0.0.1`, what stays open after 0.0.x) stands.
- **In 0.0.1:**
  - launch a Nextflow or Snakemake workflow from the Spectio UI, monitor it from the UI, relaunch it from the UI with changed parameters, and keep the parameter history across runs;
  - both engines, each run always launched with the Spectio plugin of its engine: Snakemake through the logger plugin, Nextflow through `nf-spectio` ([0001](0001-nextflow-through-nf-spectio.md)).
- **Changed from the earlier cut:**
  - **runs go to SLURM, not to the local executor.** The engine head is submitted with `sbatch`, and its tasks go to SLURM through the engine's own SLURM executor. The SLURM launcher is in 0.0.1 (built in, CLI transport); scheduler monitoring is limited to what the engines report plus the head job's state;
  - **no QC checks and no gates in 0.0.1.** This reverses the "QC check and gate on one stage" row; checks and gates move to "later (open)". The 2026-10-26 decision "checks and QC first" stays the product direction, but not for 0.0.1.
- **Unchanged:** no authentication, no accounts, no roles.
- **Architecture (Thomas chose "everything on the cluster"):**
  - each user runs `spectio serve` under their own Unix account on the cluster login node: one process with UI + API, the built-in runner and SQLite;
  - the user opens it through an SSH tunnel with a token link, like Jupyter ([Jupyter Server security](https://jupyter-server.readthedocs.io/en/latest/operators/security.html)). No accounts, but every request needs a secret: the link's single-use ticket is exchanged for a session secret in a cookie (definition: [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)); the server binds to 127.0.0.1 only. This answers the 0.0.1 part of inbox #15 (SEC-102): the login node's loopback is shared by all its users, so tokenless loopback is not acceptable;
  - the built-in runner submits the heads with `sbatch`;
  - the plugins write their events to the existing spool in the launch directory ([`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §13.1), on the shared file system, and the built-in runner reads it. No network from compute nodes to the server;
  - SQLite stays on node-local disk of the login node, because the server refuses a database on a network file system (architecture §7.2). Whether login nodes have persistent node-local disk, and whether sites allow a long-running user process there, is **[to be validated per site]**;
  - Kubernetes: nothing in 0.0.1. A shared server (on Kubernetes or a service node) with remote runners needs runner credentials and user identity (inbox #12–#14) and stays later (open).
- **Security requirements that make "no auth" safe:** a token of at least 256 bits from a CSPRNG, compared in constant time, on every HTTP request including SSE; an `HttpOnly`, `SameSite=Strict` cookie; a `Host` allow-list of loopback names against DNS rebinding; data directory 0700, server key and database files 0600, run directories 0700; spool events treated as untrusted input (schema-validated, size-capped, never executed).
- **Security in code review (Thomas: "il faut être béton"):**
  - every build step's code review now runs `security-reviewer` on the diff, not only for auth, tokens, runners or plugins; a step is done only when `code-reviewer` and `security-reviewer` both approve, and security blockers and majors must be fixed;
  - CI gains security checks on every PR: secret scanning, a dependency vulnerability audit for Python and JavaScript, static analysis (SAST) and a GitHub Actions workflow linter. Step D4 builds them.
- **Specs and pages changed:**
  - [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md): §15.1 (intro and rows), new §15.3 (architecture and security requirements on a cluster), §11 (security checks on every PR), §8 (Claude PR review row), §14 (first stage row and note);
  - [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) rewritten to match;
  - the docs site: the landing page `docs/index.md` (hero, status pill, Works-with icons), `docs/stylesheets/extra.css` (header and tabs on the page surface, emblem motion after depictio's logo) and `overrides/partials/logo.html` (inline header mark); the §15.3 sketch `tools/diagrams/mvp001_cluster.py`, registered in `docs/assets/media.yaml`;
  - [`authentication-and-access.md`](../specs/authentication-and-access.md) §1 and [`api-and-data-model.md`](../specs/api-and-data-model.md) §6 (single-user mode): dated notes that link to dev-env §15.3;
  - [`synthesis.md`](../specs/synthesis.md) §9, the roadmap, the installation, changelog and glossary pages, and the runners and gates feature pages: they now link to §15 instead of restating the old cut;
  - the P1 prompt and its heading, and the D4, P3 and T3 prompts in [`next-phase.md`](../playbooks/next-phase.md), and [`autopilot.md`](../playbooks/autopilot.md) §9;
  - [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §7.2 (runs root on the shared file system) and §13.1 (the server process reads the spool in 0.0.1): dated notes;
  - [`documentation-system.md`](../specs/documentation-system.md) §1 (Theme) and §2 (landing page), to match the new landing page;
  - the §15.3 sketch, `docs/assets/diagrams/mvp001_cluster_*`;
  - `.claude/skills/review-code/SKILL.md`, `.claude/skills/autopilot/SKILL.md`, `.claude/agents/code-reviewer.md` and `.claude/agents/security-reviewer.md`;
  - inbox #11, #12, #14, #15, #16, #32, #33, #34, #35, #36, #37 and #39 (dated notes).
- **Open points** (written as **[to be validated]** in §15.3): site prerequisites for a long-running process and node-local disk on login nodes; whether a Snakemake head may run inside a SLURM job, which the Snakemake SLURM executor plugin advises against ([`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) §3.1, spike T3; fallback: the head on the login node, tasks still through the SLURM executor); browser behaviour of `SameSite=Strict` cookies and SSE.

## 2026-10-27 — Inbox answers #5 to #37 (dashboard)

- **Context.** Thomas answered 24 inbox entries from the progress dashboard (14:03–14:20 UTC). Each answer is recorded on its entry in [`inbox.md`](../reviews/inbox.md). Where an answer confirms an assumed option, the specs' markers now read *decided — Thomas, 2026-10-27*.
- **Decided, as recommended:** #11 (a), #19 (a), #20 (b), #21 (a), #22 (a), #23 (c), #24 (a), #25 (a), #26 (a), #27 (a), #33 (c), #35 (a), #36 (a), #37 (a).
- **Decided, with a change:**
  - #13: (a), but kept lightweight. 0.0.1 and single mode have only the token link; the token registry and the authorisation matrix start with the first multi-user version.
  - #34: no gates in 0.0.1, as in the cut above; SR-056 (workflow registration) stays open for 0.0.1.
- **Leaning, not decided:**
  - #32: "B, but to be discussed". Thomas is not sure the engines themselves create a new run on resume; spike T1 checks it (its prompt now asks for it), and the B text stays *assumed*.
  - #14: "skip k8s for now; focus on local and SLURM launch". The autopilot reads it as (a) restricted to local and SLURM, with the Kubernetes identity model deferred; Thomas confirms or corrects this reading, and the SEC-103 text stays *assumed*.
- **Deferred:** #17 (rediscuss separately), #18 (too complex for the MVP).
- **Still open:** #5 (deleting the old branch needs Thomas's go), #8 (waiting for the GitHub App), #12 (pros and cons now in the entry) and #15 (re-explained in the entry and the session).
- **Applied now:**
  - [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §7.3, "0.0.1 prerequisites" (#35, SR-067);
  - [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15.3, security requirement 7, "Writes" (#37), and requirement 6 pointing to #36;
  - `CLAUDE.md` board conventions: the UX-219 keyboard rule (#26);
  - [`next-phase.md`](../playbooks/next-phase.md) T1 prompt (#32);
  - *assumed* → *decided* markers for #13, #22–#27, #33 and #35 in the specs, features and installation pages; dated research notes keep their markers.
- **Applied later:** the spec text of the later-version decisions (#11, #13, #19–#27, #33, and #36 for api §14) goes into one apply pass of the inbox answers after W3, as Thomas chose in the session on 2026-10-27, so the W3 budget goes to the build steps. The autopilot proposes its slot when W3 ends. Review files keep their statuses until that pass.

## 2026-10-27 — D3: pinned toolchain, bootstrap and doctor

- **Context.** Step D3 wrote `dev/versions.env`, `dev/bootstrap.sh` and `dev/doctor.sh` from the [D2 spike](../research/spike-cloud-env-2026-10-26.md) and ran them in a cloud session and in `dev-env.yml`. These are the choices the step made; Thomas reviews them in the step's PR.
- **Pins follow the cloud image where a re-download would cost or be blocked:** uv 0.11.32 and Playwright 1.63.0 are the pre-installed versions, so the cloud setup reuses them and no browser is fetched from a host off the allowlist. Node is the exception: §1 asks for 24 LTS and the image ships 22, so bootstrap installs 24.
- **Downloads are checked:** each binary and tarball has its sha256 in `versions.env`, from the project's published checksum where one exists (Nextflow publishes none, so its sha256 is the one computed at download). Snakemake's and Playwright's dependency trees are hash-locked (`dev/snakemake.lock.txt`, `dev/npm/package-lock.json`), after the security review found them unlocked (SEC-D3-01). The uv-managed CPython and Playwright's Chromium are the two downloads not hashed by us. Every image the doctor runs is pinned by digest, and Docker Hub images are pulled from `mirror.gcr.io` first.
- **Linux x86_64 only** for now: the checksums are for linux/amd64.
- **The doctor never goes green by skipping in CI:** sind and kind are skipped, with the reason, only where Docker runs on cgroup v1 (cloud sessions); `dev-env.yml` sets `SPECTIO_DOCTOR_STRICT=1`, so a skip fails there.
- **No SessionStart hook:** bootstrap `--ci` and the doctor start `dockerd` when it is missing, which covers the daemon that the environment cache does not keep.
- **Specs changed:** [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §1 (table, new "Bootstrap" paragraph, "Checks"), §2 (cloud sessions row and the cloud environment settings: network list with `nodejs.org` and `get.helm.sh` added to D2's, environment variables, setup script), §4.2 (answered: kind and sind do not run in cloud sessions), §11 (`dev-env.yml` row). Progress page: [D3](../progress/W3/D3.md).

## 2026-10-27 — A light PR tier for the real-pipeline corpus (inbox #45)

- **Decision (Thomas, session, 2026-10-27).** The PR tier of `tests/pipelines/real/corpus.yaml` keeps only nf-core/demo and the ms-proteomics dry run, about 5 min. rnaseq, viralrecon, methylseq, molkart and rna-seq-star-deseq2 move to `nightly`. `pipelines-real` stays in `ci-ok`'s `needs`, as decided in T7.
- **Why.** The private runners are small (2 CPU, 7.75 GB). The 7-entry tier took about 40 min, and its heavy entries failed for reasons outside the PR: an Ensembl timeout, a conda-forge 502, and a Docker registry reset on rnaseq (run 40578574693).
- **Specs changed:** [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §10.2 (table, re-run rule) and §11 (`ci.yml` row). Evidence: [corpus-ci-2026-10-27](../research/corpus-ci-2026-10-27.md) §2–§3. Progress page: [T7](../progress/W3/T7.md).

## 2026-10-28 — APPLY3: spikes round findings applied

Step page: [APPLY3](../progress/W3/APPLY3.md). Triage: [TRIAGE3](../progress/W3/TRIAGE3.md), round file [spikes](../reviews/spikes.md).

- **Context.** APPLY3 applies the findings that TRIAGE3 accepted or assumed in round "spikes": what the spikes and builds T2 (engine events), T3 (sind SLURM), T4 (kind and Kueue) and T7 (real-pipeline corpus) measured against the specs. It changes the owning specs only. Each finding's **Status** line in [spikes.md](../reviews/spikes.md) says what was applied and where. Findings that wait for Thomas were not touched: #53 (Kubernetes Roles), #54 (work namespace and tokens), #55 (what event payloads may carry), #59 (slurmrestd token) and #46 (corpus pinning).
- **Engine events (T2):**
  - **Nextflow bridge (SPK-T2-05, SPK-T2-25).** [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §13.3: the `nf-spectio` sender flushes and stops at observer shutdown, not at `onFlowComplete`, because `onFlowError` and a second `onFlowComplete` can follow it; [`synthesis.md`](../specs/synthesis.md) §2 links to it. §7.3: the runner unpacks the `nf-spectio` jar from the wheel into `$NXF_HOME/plugins/nf-spectio-<ver>/` and passes `-plugins nf-spectio@<ver>`; this refines inbox #35 and does not reverse it. Whether `NXF_PLUGINS_DIR` can point to a read-only copy is still to be validated. Evidence: [T2 note](../research/spike-engine-events-2026-10-28.md).
  - **Coexistence with `nf-tower` verified (SPK-T2-14).** `nf-spectio` and `nf-tower` ran together in 6 of 6 runs on Nextflow 26.10.4 and 25.10.9, with the same run name, session ID and task IDs. [Decision 0001](0001-nextflow-through-nf-spectio.md) gets a dated "Update 2026-10-28" line and stays as decided. The marks in synthesis §1, api §10 and decision 0001 become links to the T2 note.
  - **Nextflow facts corrected (SPK-T2-10, SPK-T2-12).** synthesis §1 and §2: `nf-tower` is a core plugin downloaded from the plugin registry on first use, not shipped with Nextflow. §2bis: Tower `begin` carries `dag` on 26.10 only.
  - **Snakemake logger facts (SPK-T2-15, SPK-T2-21, SPK-T2-22, SPK-T2-24, SPK-T2-26).** synthesis §2 lists the 14 `LogEvent` members (interface 2.1.0) and keeps untyped records as text. §2bis adds two plugin pitfalls: `baseFilename` with `writes_to_file = True` and the `LogHandlerSettings` class name; and defensive serialisation of `Namedlist` and `UUID`. Architecture §13.4 and §7.3: logger plugin discovery on `PYTHONPATH` by module prefix is verified (Snakemake 9.27.1).
  - **Snakemake rules in the synthesis §2ter matrix (SPK-T2-16, SPK-T2-18, SPK-T2-19).** Attempt n = 1 + the number of `JOB_ERROR` already seen for that `jobid`, with no text parsing. The checkpoint message "DAG of jobs will be updated after completion." sets "DAG may change" until the next `PROGRESS`. `temp_removed` is deduplicated by (run, path), since each deletion is logged twice. All cited at Snakemake v9.27.1.
  - **checking-scenarios §11.1** (SPK-T2-03, SPK-T2-04): Nextflow task outputs are matched by output index and a glob on the file name, never by output name (path outputs have no name; `onTaskCached` carries the same outputs); the `JOB_INFO` citation moves to snakemake v9.27.1, `jobs.py:1060-1101`, with its extra fields. Evidence: [T2 note](../research/spike-engine-events-2026-10-28.md#differences-with-the-specs), rows 3 and 4.
  - **checking-scenarios §11.4** (SPK-T2-08): live checks reuse a stored result when the target path and hash match, in the same run or in the parent run of a resume, since a Nextflow resume republishes every cached file *(assumed — pending Thomas, inbox #32)*.
  - **checking-scenarios §11.5** (SPK-T2-01, SPK-T2-02): end of stage on Nextflow = every matching process terminated **and** every seen task of those processes completed or cached (no timed drain; answers T2's open question); when the run reaches a terminal state, unended stages close as `failed` or `skipped` and their `stage_done` watches do not fire.
  - **api-and-data-model §7** (SPK-T2-17, SPK-T2-27): `attempts.exit` is nullable (Snakemake `JOB_ERROR` has no exit code); on Nextflow `runs.failure.message` comes from `onFlowComplete`'s `errorMessage` and `task_id` / `attempt_n` from the `TERMINATE` attempt, not from `onFlowError`; the mark goes for Nextflow and stays for Snakemake.
  - **api-and-data-model §7.2** (SPK-T2-07): the Nextflow engine mapping reads hooks and `trace.status`, never `handler.status` (`COMPLETED` on a failed attempt); the mark goes for Nextflow and stays for Snakemake.
  - **api-and-data-model §7.2, ui-spec §3.1** (SPK-T2-09): new terminal attempt state `aborted` for attempts still open when a launch ends (Nextflow `ABORTED` included); not a failure; a task with no attempt stays `not_scheduled`; ui-spec §3.1 lists the label *(assumed — pending Thomas, inbox #56)*.
  - **api-and-data-model §8.2** (SPK-T2-06): a repeated engine flow completion for the same launch (Nextflow 25.10.9 sent two) is logged and changes nothing.
- **Schedulers (T3, T4):**
  - **schedulers-and-monitoring §3.1, §3.2** (SPK-T3-19, SPK-T3-04): a Snakemake head submitted with `sbatch` works on `slurm-site` for the synthetic `happy` scenario (head `COMPLETED 0:0`, run 40680736055); failure scenarios, a cancelled head and long runs stay to be validated. dev-env §15.1 and §15.3 now say the same and link to §3.1. §3.2 adds Snakemake's own status clock (plugin 2.8.0 waits 40 s, up to 180 s); the run lattice of api §8.2 makes the order harmless.
  - **schedulers-and-monitoring §3.5, failure classes** (SPK-T3-01, SPK-T3-03, SPK-T3-05, SPK-T3-09, SPK-T3-16): a Nextflow task over its time limit ends `FAILED 140` (`--signal B:USR2@30`), never `TIMEOUT`, and is classed `timeout`; a Snakemake task job ends `FAILED 1:0`, so `attempts.exit` stays null unless the task log is read; `OUT_OF_MEMORY` is verified as `return_code` unset with signal 125 (the mark goes); `cancelled_external` compares `kill_request_user` with the run's user, and the engine's own cleanup is not an external cancel ("cancelled by the engine", no class). Evidence: [T3 note](../research/spike-t3-ci-2026-10-28.md).
  - **schedulers-and-monitoring §3.5, pending reasons** (SPK-T3-06, SPK-T4-11): with `--json`, match `state_reason` (`ReqNodeNotAvail` needs `state_description`); a `sacct` reason on a terminal job is history; new rows for Kubernetes `FailedScheduling … Insufficient cpu/memory` and Kueue `WaitingForQuota`, neither a failure.
  - **schedulers-and-monitoring §4** (SPK-T4-02 fact part, SPK-T4-05, SPK-T4-06, SPK-T4-07, SPK-T4-17): `pods: create` verified on `k8s-mini` (the Role lists wait for inbox #53); Nextflow 25.10 needs the `nf-k8s` plugin, 26.10 does not; a task is "queued" when the Kueue visibility API lists its Workload, with `QuotaReserved=False` as the fallback; an OOM kill shows only in `state.terminated` and a Job deadline deletes the pod, so the runner keeps terminal pod and Job states; the Kueue pod integration is in the default configuration (v0.20.3), not opt-in. Evidence: [T4 note](../research/spike-t4-ci-2026-10-28.md).
- **Development environment (T3, T4, T7):**
  - **dev-environment-and-testing §1** (SPK-T4-15 / SEC-T4-05, SPK-T4-16): "Checked downloads" also covers images named inside a pinned manifest (rewritten to a digest before `kubectl apply`), Nextflow plugins needed at run time (`nf-k8s` fetched by bootstrap with a sha256 in `versions.env`) and `bootstrap.sh --only <tools>` in CI jobs; none is built yet, the code is a follow-up with inbox #46. The Kueue row says the older version is pinned, not run.
  - **dev-environment-and-testing §3** (SPK-T3-02, SPK-T3-17): only a real over-limit allocation (`oom_real`) gives SLURM `OUT_OF_MEMORY` or Kubernetes `OOMKilled`; `oom` and `oom_once` give `FAILED 137:0` (Nextflow) or `FAILED 1:0` (Snakemake). Node failure is described as run in T3 (`sind power cut`, `NODE_FAIL`); preemption is planned, not built.
  - **dev-environment-and-testing §4 and §4.2** (SPK-T3-20 / SEC-T3-01, SPK-T4-16): new rule "Node tools are read-only for jobs" (a read-only `extraMounts` entry on kind; on sind a read-only mount or a root-owned tree), not built yet. The `k8s-kueue` row: queue positions and admission built in T4, preemption and the older Kueue version planned.
  - **dev-environment-and-testing §4.1** (SPK-T3-18): the `slurm-versions` row is "Planned, not built yet" *(assumed — pending Thomas, inbox #60)*.
  - **dev-environment-and-testing §10.1** (SPK-T3-10): the `oom_fatal` and `timeout_fatal` codes are labelled as the local executor's; on SLURM 26.05.5, Nextflow gives `FAILED 137:0` and `FAILED 140:0`, Snakemake `FAILED 1:0` for both.
  - **dev-environment-and-testing §11** (SPK-T7-03, SPK-T4-09, SPK-T3-13, SPK-T7-01): `pipelines-real.yml` uses the `versions.env` Nextflow pin (the workflow reads `NEXTFLOW_VERSION` from `dev/versions.env` since PR #38); `pipelines-slurm.yml` and `pipelines-k8s.yml` are standalone until `ci.yml` calls them, as the #26 rule says *(assumed — pending Thomas, inbox #57)*; new "Nightly runs" paragraph: the autopilot reads the last scheduled run of each pipeline workflow at each tick *(assumed — pending Thomas, inbox #58)*.
  - **dev-environment-and-testing §10.2** (SPK-T7-02, SPK-T7-05): applied by PR #36 (corpus retry), before APPLY3.
  - **dev-environment-and-testing §15.1 and §15.3** (SPK-T3-19): the Snakemake head job, as in schedulers §3.1.
- **Assumed decisions.** Each is marked in the text "*(assumed — pending Thomas, inbox #n)*" and can be reverted by removing what that marker covers: #56 (attempt state `aborted`, api §7.2 and ui-spec §3.1), #57 (`pipelines-slurm.yml` and `pipelines-k8s.yml` join `ci.yml`, dev-env §11), #58 (the autopilot reads the nightlies, dev-env §11), #60 (deferred SLURM coverage is planned, dev-env §4.1); #32 is reused in checking §11.4.
- **Marks removed:** the schedulers §3.5 `OUT_OF_MEMORY` 0:125 mark, the schedulers §3.1 and dev-env §15.1/§15.3 Snakemake-head marks, the schedulers §4 `pods: create` mark, and the `nf-tower` coexistence marks in synthesis §1, api §10 and decision 0001.
- **Marks added:** Nextflow 140 on limits well above a minute; the Snakemake status interval on real sites; where Nextflow 26.10 bundles the k8s executor; a 25.10 Pod admitted by Kueue with only the label; Snakemake head-job failures and long runs; whether the Nextflow plugin registry publishes a checksum; sind storage options for a read-only tools mount; whether `NXF_PLUGINS_DIR` can point to a read-only copy.
- **Not applied (reserved):** SPK-T3-15 (#59); SPK-T4-01, SPK-T4-03, SPK-T4-04 and the Role lists of SPK-T4-02 (#53); SPK-T4-12 and SPK-T4-14 (#54); SPK-T2-11 and SPK-T2-23, what engine events may carry (#55); SPK-T7-04 (#46).
- **Follow-ups in code** (no spec change needed): digest-pinning of images named inside manifests and the `nf-k8s` checksum (SPK-T4-15, with #46); read-only node tools on kind and sind (SPK-T3-20). The code part of SPK-T7-03 (`pipelines-real.yml` and `corpus.yaml` read the Nextflow pin from `versions.env`) is done by PR #38.

## 2026-10-28 — 0.0.1 narrowed: launch and monitor, an ultra-simple UI

- **Context.** Thomas, 2026-10-28, while the autopilot moved to T6, R10 and P1: "N'oublie pas que le MVP ne doit pas gérer kubernetes, complexité etc ; je veux une UI ultra simple ; launch & monitoring de wf ; pas de gating ; pas de visu" (the MVP must not handle Kubernetes or complexity; an ultra-simple UI; launching and monitoring workflows; no gating; no visualisation).
- **Decided (Thomas):** no Kubernetes and no gates in 0.0.1 (already so since [2026-10-27](#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link)); no visualisation: no DAG, timelines, charts, resource plots or run comparison; the UI launches and monitors workflows and does nothing else.
- **Assumed** *(pending Thomas, inbox #61)*: relaunch with changed parameters and the parameter history across runs leave 0.0.1 for "later (open)", since Thomas listed launch and monitoring only. The run detail still shows the parameters of its own run.
- **Unchanged:** one user on the SLURM login node, `spectio serve`, SSH tunnel and token link, SQLite, both engines through their plugins, the §15.3 security requirements.
- **Changed:** [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (intro, Monitoring, Relaunch and Parameter history rows, a new Visualisation row); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §1–§3; the P1 prompt in [`next-phase.md`](../playbooks/next-phase.md); inbox #61; a dated note on inbox #52. The T6 build was narrowed to a minimal Playwright skeleton (no side-by-side report against the boards).

## 2026-10-28 — 0.0.1: head in tmux on the login node; SSH config and `spectio open`

*Note, same day (doc review of PR #47): the laptop tool's command is `spectio-open`, the console script of the package `spectio-open`; the heading keeps its first wording so that links to it stay valid.*

- **Context.** Thomas, 2026-10-28, after reading how 0.0.1 launches a run and how a user reaches the server. On the head: "the good practice, as I understand it, is to launch the Snakemake or Nextflow master process in a tmux screen or an equivalent, which then hands the jobs to SLURM … I find it a bit odd to launch that master process on one of the HPC nodes … it should not be launched in an sbatch; if possible, in a tmux that can be recovered later and controlled by hand by a human if needed." On access: "I would rather have both in parallel: the SSH config for people who want to try without installing tools, and the small tool, ready and lightweight to install on the laptop, to start a Spectio remotely in one's session on the login node, with a way to give the login node's number." (Translated from French.)
- **Decided (Thomas):**
  - **The engine head runs on the login node, one detached tmux session per run, never in `sbatch`.** A person can attach to it, watch the engine's own output and stop it by hand; the tasks still go to SLURM through the engine's own SLURM executor; Spectio watches the head through its PID and exit files and reads its events from the spool, as before. Why: it matches how users run Nextflow and Snakemake by hand, and the Snakemake SLURM executor plugin warns against running Snakemake inside a SLURM job ([`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) §3.1 quotes it). It also removes the open T3 question on Snakemake head jobs and the offline-head pre-steps from 0.0.1.
  - **Two ways to open the server, side by side:** an SSH config entry with `LocalForward`, with nothing to install; and `spectio-open <host> [--node <login node>]`, a small laptop tool with no dependency beyond the Python standard library that calls the system `ssh`, starts `spectio serve` if needed, opens the tunnel, gets a fresh one-time link and opens the browser. `--node` pins the login node, because the server, its database and the heads live on one node.
- **Also decided (Thomas, same day): the target is the EMBL cluster only**, with no genericity across sites for now. EMBL facts (Thomas): user processes on login nodes have no time limit; tmux is installed by default; there are four to five login nodes, and all software and storage are shared between them (the same home, the same binaries). Consequences: one install of `spectio` in the user's shared environment serves every login node; the server still pins one login node, since its process and tmux sessions live there, so it writes a state file in the shared home (login node, port, PID) that `spectio-open` reads (`--node` stays for a first start or an override), and that `spectio login --print-link` reads to name the server's node when it is run on another one; the server itself runs in a tmux session, `spectio-server`, so a person can attach to it too. `spectio-open` runs the remote `spectio` through a login shell (so `PATH`, modules and the shell rc files apply), with a per-cluster setting on the laptop for an explicit remote command; if the command is missing it prints how to install it once rather than installing silently; if no server runs, it runs `spectio init` with defaults when needed and starts the server in its tmux session. Engines are found the same way and recorded at `spectio init`.
- **Unchanged:** one user per server, the server bound to 127.0.0.1, the one-time token link and the seven §15.3 security requirements, events through the spool.
- **To be validated:** where SQLite goes on the EMBL login nodes (inbox #64; answered by the next entry, assumed); the per-user memory limits on a login node against the heads (a Nextflow head is a JVM); whether a logout cleanup kills a user's processes there; whether Nextflow's abort on Ctrl-C cancels the SLURM jobs it submitted. For other sites, later: tmux, long-running processes and memory limits on login nodes.
- **Later (open):** the head as an `sbatch` head job, for sites that forbid long-running processes on login nodes ([`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) §3.1).
- **Changed:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Launch, a person can take the head over, Events, Site prerequisites, Server restart, Access, the diagram and the figure), the §15.1 intro and the Snakemake, Nextflow, Access, SLURM launcher and Scheduler monitoring rows, a dated note in §4.1; [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) §3.1 (dated note) and §3.1.1 (tmux launcher); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §1–§2; [P1](../plans/P1-walking-skeleton.md) Assumptions 4, 9, 10, 13, 14, 15 and 20, Tasks 8, 10, 11, 22 and 23, and a new Task 24; inbox #15, #28 and #35, and a new #64. Then, after the doc review of PR #47 (same day): P1 Tasks 2, 9, 12, 18 and 20 and Assumptions 7, 9, 13 and 21; [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout) (the `spectio-open` package); schedulers §3.1.1 (only the tmux server is detached); dev-env §4.1 note; both figures ([Progress · APPLY4](../progress/W4/APPLY4.md)).

## 2026-10-28 — 0.0.1: live refresh over SSE; SQLite as a rebuildable index

- **Context.** Thomas, 2026-10-28, answering two questions about 0.0.1 on the EMBL cluster. On the screens: "we can keep Server-Sent Events, I think it is OK." On storage: "everything is absolutely shared, except maybe some temporary directories, on the login nodes." (Translated from French.)
- **Decided (Thomas): live refresh over SSE.** The runs list and the run detail update over one Server-Sent Events stream per browser, behind the session cookie, rather than by polling ([`api-and-data-model.md`](../specs/api-and-data-model.md) §8.3, dated note; [`ui-spec.md`](../specs/ui-spec.md) §7). P1 Assumption 7, which assumed polling every 5 s, is reversed. The `EventSource` cookie behaviour of [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 3 is back in scope; the P1 Playwright smoke checks it.
- **Assumed, pending Thomas (inbox #64): SQLite as a rebuildable index in a node-local temporary directory.** The data directory (configuration, state file; no secret) stays in the shared home; the SQLite database, `serve.lock` and the server key go in a node-local temporary directory of the server's login node, since the server refuses a database on a network file system. The database is an index, not the source of truth: each run directory on the shared file system holds a manifest (`.spectio/run.json`), the event spool, the head's PID and exit files, a cancel marker and a launch-failure record, and the server rebuilds the database from them at boot when it is missing (the directory was purged, or the server moved to another login node). Why: it needs no persistent local disk, which the EMBL login nodes may not have, and no SQLite file on a network file system. **To be validated:** which temporary directory is node-local on the EMBL login nodes, and how often it is purged.
- **Changed:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Where data lives, Prerequisites at EMBL, Server restart, req. 3 and 5, the diagram), the §15.1 Monitoring and Database rows; [architecture §7.2](../specs/architecture-plugins-and-packaging.md) (dated note) and §7.3; [api §8.3](../specs/api-and-data-model.md) (dated note); [ui-spec §7](../specs/ui-spec.md); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §1; [P1](../plans/P1-walking-skeleton.md) Assumptions 7 and 21, Tasks 2, 8, 9, 11, 18 and 20; inbox #64.
- **Security review of the change (same day):** 0 blockers, 5 majors, 5 minors (SEC-131 to SEC-140, [record](../reviews/code/APPLY4.md)), all applied as [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) trust boundaries, req. 5 and the new requirements 8–11, with their tests named in P1. The server key moved from the shared home to the node-local directory; the port is fixed and fails closed; run directories are untrusted input at rebuild.

## 2026-10-28 — 0.0.1 also monitors runs started from a terminal; bridges published in the engines' catalogues

- **Context.** Thomas, 2026-10-28: "In the 0.0.1 MVP we should already have the modules, so that people can launch workflows from the terminal and not only from the UI. Otherwise few people will use it and it has no point. So we need a plugin in the style of the Nextflow plugin catalogue, and a plugin for, sorry, for the Snakemake workflow catalogue, and a Nextflow plugin as well, to be able to push to Spectio." (Translated from French; for Snakemake, the catalogue of logger plugins is the [Snakemake plugin catalogue](https://snakemake.github.io/snakemake-plugin-catalog/).)
- **Decided (Thomas):** 0.0.1 also monitors runs that users start by hand. The engine bridges are published in the engines' own catalogues: `nf-spectio` in the Nextflow plugin registry, and `snakemake-logger-plugin-spectio` on PyPI, which feeds the Snakemake plugin catalogue.
- **Assumed, pending Thomas:**
  - the bridge writes the spool in the launch directory as today, and drops a pointer file in `~/.spectio/observed/`; the server scans that folder and shows the run as origin `cli-observed`; pointers and launch directories are untrusted input under the new [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 12;
  - monitor only: no Cancel for these runs in 0.0.1 (inbox #65);
  - the engine setup is documented, not automated, in 0.0.1 (inbox #67).
- **Not assumed:** claiming the four names (`nf-spectio` in the registry; `snakemake-logger-plugin-spectio`, `spectio`, `spectio-open` on PyPI), which only Thomas can do (inbox #66). The release path is the existing default of [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) (CI jobs under `weber8thomas`, inbox #9 (c)). Claude never publishes.
- **Later (open):** a `spectio run -- <engine command>` wrapper; Adopted runs and their actions.
- **To be validated:** whether the EMBL login nodes reach `registry.nextflow.io` and PyPI; whether Nextflow 25.04 finds a plugin published only to the registry.
- **Changed:** [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (intro and the terminal row) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (a person can take the head over; Where data lives; Runs started from a terminal; trust boundary (iv); a new req. 12) and §12 (Publishing: the registry release steps); [architecture §2 and a new §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal); [ui-spec §6](../specs/ui-spec.md) and [api §5.1](../specs/api-and-data-model.md) (dated notes: no Cancel on these runs); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §2 and §3; [P1](../plans/P1-walking-skeleton.md) Goal, Milestones, Assumption 22, new Tasks 25 and 26, Out of scope, Done when; inbox #11 (note) and new #65–#67 ([Progress · APPLY5](../progress/W4/APPLY5.md)).
- **Security review (same day):** 1 blocker, 4 majors, 4 minors (SEC-141 to SEC-149, [record](../reviews/code/APPLY5.md)), all applied as dev-env §15.3 req. 12, with their tests named in P1 Tasks 25 and 26.

## 2026-10-28 — 0.0.1 has four screens; Home kept

- **Context.** The ux-reviewer pass on the 0.0.1 lite boards (UX-298, [record](../reviews/code/UI-LITE.md)) found a fourth screen, Home, while the specs said three. Thomas, 2026-10-28, had asked for a home / overview screen and for a run detail "with all its steps and their status".
- **Decided (Thomas):** 0.0.1 has four screens: home, the launch form, the runs list and the run detail. Home shows the count cards by state, the active runs, the runs that ended recently and the pipeline directories of the recent runs.
- **Follows from it:** home reads `GET /runs:summary?group_by=state`, with no time window; the runs list filters with `state=` and `q=`; the run carries `origin`, `engine_version` and the pipeline's declared version; the shell reads a minimal `GET /version` ([P1](../plans/P1-walking-skeleton.md) Task 18; [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1), note 2026-10-28). The routes are `/`, `/runs`, `/launch` and `/runs/:id` (Tasks 19 and 20). Stages, same day (Thomas: "les 2 dans 0.0.1", both in 0.0.1): the run detail shows the stages, each opening to its processes or rules, or the flat list when there is none, as the [ui-spec §4.4 note](../specs/ui-spec.md#44-run-detail) says; how stages are found is in the [next entry](#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list) ([ui-spec §5.1.1](../specs/ui-spec.md#511-detected-stages)).
- **Design (Thomas, same day):** "pour le design ; n'oublie pas les logos snakemake/nextflow/nf-core. Light icons par partie (stages, processes ...) et chaique partie collapsible ; pareil dans launch. Spectio logo uniquement en favico dans la barre ; pas le logo lui mm" (the Snakemake, Nextflow and nf-core logos; a light icon per section, each section collapsible, in the run detail and in launch; the last sentence was misread as "the Spectio logo as the favicon only, nothing in the bar"). Thomas's correction, same day: "Non je veux le logo mais pas juste le favico en mode mobile mais le logo complet" (no: I want the logo, not just the favicon as in the phone view, but the complete logo). So the app bar shows the complete logo, emblem and wordmark, on desktop and on the phone, and the emblem alone stays the favicon in the browser tab: [ui-spec §2 note](../specs/ui-spec.md#2-main-navigation).
- **Changed:** [mvp-0.0.1 §1, §2](../specs/mvp-0.0.1.md); [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (intro; the Stages row links the §4.4 note); [P1](../plans/P1-walking-skeleton.md) Assumption 6, M4, Tasks 18 to 20; the 0.0.1 lite boards and their table in [`design/README.md`](https://github.com/weber8thomas/spectio/blob/main/design/README.md#001-lite-boards); the [api §5 note](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1) (the `/stages` subset, `sort=-ended_at`); the [ui-spec §4.4 note](../specs/ui-spec.md#44-run-detail) (stages, state words, process names) and the [§2 note](../specs/ui-spec.md#2-main-navigation) (the complete logo in the app bar; emblem as favicon); the [review record](../reviews/code/UI-LITE.md) ([Progress · UILITE](../progress/W4/UILITE.md)).

## 2026-10-28 — 0.0.1 shows stages, declared or detected, and the processes or rules list

- **Context.** Thomas, 2026-10-28, on how 0.0.1 shows a run's progress: "les 2 dans 0.0.1 ; certains pipelines exemples pour montrer comment ça fonctionne pour 2/3 nf core et https://github.com/friendsofstrandseq/mosaicatcher-pipeline ; travaille pour nf core sur un systeme automatisée qui détecte les différents grand stages ; il doit y avoir un moyen via subworkflows etc" (both in 0.0.1; some example pipelines to show how it works, for two or three nf-core pipelines and mosaicatcher-pipeline; work, for nf-core, on an automated system that detects the big stages; there must be a way through subworkflows, etc.).
- **Decided (Thomas):** 0.0.1 shows both the named stages and the list of processes (Nextflow) or rules (Snakemake); stages are found automatically for nf-core pipelines, from their subworkflows; the behaviour is shown on example pipelines, two or three nf-core ones and mosaicatcher-pipeline.
- **Evidence:** the [stage-detection spike](../research/spike-stage-detection-2026-10-28.md) (branch `spike/stage-detection`). Every Nextflow process name carries its subworkflow scopes and reaches `nf-spectio` before the first task; a small detector gives 4 to 8 stages on nf-core/rnaseq 3.27.0, sarek 3.11.0 and methylseq 4.2.0. The Snakemake logger sees rule names only, so stages come from the rule files that mosaicatcher-pipeline v2.5.1 includes. Four example lab overlays give better names and match every process or rule, with no overlap.
- **Assumed, pending Thomas:**
  - the precedence declared, then detected, then none, per run; processes or rules in no stage form an unassigned group; detected stages display only, frozen at the first `onFlowBegin` or `workflow_started`, at most 8;
  - the example pipelines are those four, at those versions; detected stages keep the subworkflow or file names, humanised; good names come from lab overlays, shipped as files, with no editor (inbox #68).
- **Side finding, not decided:** `-plugins nf-spectio@<ver>`, as the specs launch it, replaces the pipeline's pinned plugins, so nf-core runs fail on Nextflow 26.10.4 and drift silently from the pin on 25.10.9, and a `plugins` block in `~/.nextflow/config` drops the bridge with no warning; `NXF_PLUGINS_DEFAULT` works, through an undocumented list form (inbox #69). The mechanism is not changed by this entry.
- **Changed:** [ui-spec §5.1](../specs/ui-spec.md) (sources, a dated note) and a new §5.1.1 (detection rules), §3.2 (gauge sectors); [checking-scenarios §12.1](../specs/checking-scenarios.md) (what `match` sees); [api §7](../specs/api-and-data-model.md) (`run_stages`: when detected stages freeze); [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (a Stages row); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §2 (a row); [P1](../plans/P1-walking-skeleton.md) Goal, Assumption 6, Milestones, a new Task 27, Done when; fixtures in `tests/pipelines/real/stages/`; inbox #68 and #69 ([Progress · APPLY6](../progress/W4/APPLY6.md)).

## 2026-10-28 — 0.0.1 shows each job's files, and gains resume, failure summary, results, copy and resources

- **Context.** Thomas, 2026-10-28: "Je veux également que ça soit possible de voir les logs globaux et les lots et stout err log sh et autres de chaque job si possible via workdir. Autres features basic mais utile en MVP ?" (I also want to see the global logs and the stdout, err, log, sh and other files of each job, through the work directory if possible; other basic but useful features for the MVP?). Claude proposed five: resume a failed run, a failure summary, open MultiQC and the results, copy the command and parameters, and resources per job. Thomas: "les 5 dans 0.0.1" (all five in 0.0.1).
- **Decided (Thomas):** 0.0.1 shows the run logs and each job's own files, with its work directory; and it has Resume of a failed or cancelled run, a failure summary, read-only results and reports, the copy actions (command, parameters, Copy to a new launch) and resources per job, as numbers.
- **Evidence:** the files, failure messages and resource fields of each engine were read in the sources on 2026-10-28 (Nextflow `v26.10.4` and `v25.10.9`, Snakemake `v9.27.1`, `snakemake-executor-plugin-slurm` `v2.8.0`) and are cited in [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine). Two findings shape the design: Nextflow rolls `.nextflow.log` at each start, so a resumed run would move its parent's log, and each run now gets its own engine log file; the Snakemake SLURM plugin deletes the log of every successful job by default, so Spectio's runs keep them.
- **Assumed, pending Thomas** (inbox #70): `.command.run` shown with its exported values hidden; Snakemake's job command not stored (P1 Assumption 3 unchanged); every SLURM job log kept; `sacct` once per failed Nextflow attempt and in batches for Snakemake resources, to be checked with the EMBL admins; HTML reports in a sandbox with no access to the API; Resume only for runs Spectio launched.
- **Reverses:** P1 Assumption 20 in part ("per-task logs come later") and Assumption 1 in part (Resume and Copy to a new launch); inbox #61 keeps (a) for the rest.
- **Changed:** [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine) (revised: files, run logs, failure reason, resources); [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1) (job files and results endpoints, a 0.0.1 note) and §5.1 (Resume note); [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (the Relaunch row, five new rows, the scheduler monitoring row) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (requirements 13 to 16); [ui-spec §4.4](../specs/ui-spec.md#44-run-detail) (note, run tools); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §2, §3; [P1](../plans/P1-walking-skeleton.md) Assumptions 1, 3 and 20 (notes), M8 and Tasks 28 to 32, Out of scope, Done when; the lite boards LiteRunDetail, MLiteRunDetail, LiteRunTasks, MLiteRunTasks, LiteRunLogs, MLiteRunLogs, LiteRunFailed and LiteLaunch, and the new boards LiteTaskFiles, MLiteTaskFilesSheet, LiteTaskFilesStates, MLiteRunFailed, LiteRunActions, MLiteResumeSheet, LiteResults and LiteReportViewer; after the review of 2026-10-28 ([APPLY7 review](../reviews/code/APPLY7.md)), [checking-scenarios §11.1](../specs/checking-scenarios.md#111-how-files-reach-a-check) (the confinement walk); inbox #61 (note) and #70 ([Progress · APPLY7](../progress/W4/APPLY7.md)).

## 2026-10-29 — `nf-spectio` is enabled with `NXF_PLUGINS_DEFAULT`, set per run

- **Context.** Inbox #69: `-plugins nf-spectio@<ver>` replaces an nf-core pipeline's pinned plugins (the run fails on Nextflow 26.10.4 and drifts on 25.10.9), and a `plugins` block in `~/.nextflow/config` is dropped with no warning. Thomas, 2026-10-29, asked for "la solution la plus simple pour la communauté Nextflow de manière générale, sans que cela affecte leur système, si possible, et sans que cela les empêche d'utiliser Seqera Platform" (the simplest solution for the Nextflow community in general, without affecting their setup if possible, and without stopping them from using Seqera Platform).
- **Evidence:** the [attach verification](../reviews/verification-2026-10-29-nextflow-attach.md) (FC-318 to FC-321; Nextflow `v26.10.4` and `v25.10.9` read and run on 2026-10-29). `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` is merged with the pipeline's declared plugins; `nf-tower`, `nf-wave` and `nf-cloudcache` are added after that merge, so `-with-tower` and Seqera Platform keep working; only executor-inferred plugins are lost (`nf-k8s` on 25.10.x, SES mail), and object-store work directories start their plugin lazily. No config route merges: `-plugins`, `-c`, `$NXF_HOME/config` and profiles replace, are replaced, or are rejected or ignored. Weblog was removed from core in 26.10 and lacks the events Spectio needs. A pinned plugin already in `$NXF_PLUGINS_DIR` starts with no registry contact.
- **Decided (Thomas, 2026-10-29):** "Ok pour ta recommandation pour la question 2". `nf-spectio` is enabled only by `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` set per run in the environment, never through `-plugins`, a config file or a profile. Launched runs: the head script exports it (plus `nf-k8s` on 25.10.x with `k8s`). Terminal runs: the one-shot prefix is the documented form, a shell-profile `export` is opt-in, `spectio doctor` checks it. Seqera Platform: a Head job variable or a pre-run `export`. Weblog is not used. 0.0.1 needs no registry release.
- **Risk accepted:** the merge is code behaviour that the Nextflow docs contradict (FC-319). `nextflow-edge.yml` checks it weekly, and an upstream issue is drafted in the verification, not filed.
- **Assumed from the decision, pending Thomas** (inbox #69): the profile export is opt-in (`spectio login` offers it, default no; one marked block in `~/.bashrc` or `~/.zshrc`); `spectio init` unpacks the wheel's jar into `$NXF_PLUGINS_DIR/nf-spectio-<ver>/`; `spectio doctor` fails when that directory is missing.
- **Reverses:** the `-plugins nf-spectio@<ver>` part of [inbox #35](../reviews/inbox.md) (2026-10-27, architecture §7.3, 0.0.1 prerequisites), and the Enabling-it mechanism for Nextflow in the [2026-10-28 terminal-runs entry](#2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues) (`-plugins` or `~/.nextflow/config`). The rest of both stands: the jar bundled in the wheel and unpacked into the plugins directory, the pointer file, monitor only.
- **Changed:** [architecture §7.3](../specs/architecture-plugins-and-packaging.md) (0.0.1 prerequisites; Operator commands: `spectio doctor` checks `NXF_PLUGINS_DEFAULT`) and [§13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal) (Enabling it, The plugin copy, the `spectio doctor` check, a Risk item, Published: no registry needed for 0.0.1); [ui-spec §6](../specs/ui-spec.md) (no config profile); [cli §2](../specs/cli-and-shared-libraries.md) (`engine nextflow env`, replacing `engine nextflow config`); [synthesis §2, §10](../specs/synthesis.md) (weblog dates); [schedulers §3.1 and §4](../specs/schedulers-and-monitoring.md) (offline head; `nf-k8s` added to `NXF_PLUGINS_DEFAULT` on 25.10); [dev-env §11](../specs/dev-environment-and-testing.md) (`nextflow-edge.yml` assertion) and [§15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (terminal row) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Runs started from a terminal note; the guide's bundled copies); [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §2; [P1](../plans/P1-walking-skeleton.md) Assumption 17, Tasks 8, 9 and 25; the figure `mvp001_cluster` (the tmux pane); inbox #69 (*Decided*).

Step page: [APPLY8](../progress/W4/APPLY8.md).

## 2026-10-29 — How the four package names are held

- **Context.** Thomas, 2026-10-29, on inbox #66: "Comment faire pour réserver ces 4 noms de paquets? … Pour PyPI, prépare-moi déjà ce qu'il faudrait faire dans un fichier ou sur le CI. Puis je préparerai ceci moi-même sur le site." (How do I reserve these four package names? For PyPI, prepare what is needed in a file or in CI; I will do the site part myself.)
- **Evidence:** the [name-claim verification](../reviews/verification-2026-10-29-names.md) (FC-314 to FC-317, sources read 2026-10-29). On the Nextflow registry, an admin-approved claim should hold the ID with no release: an inference from "ownership of a plugin is required to publish" (`plugin-registry.mdx:16`) and "you can claim a plugin even if it doesn't exist in the registry yet" (`gradle-plugin.mdx:109-111`); refusal of a second claimant is not stated. On PyPI, a pending trusted publisher holds nothing; only a project that exists does, and at most 3 publishers can be pending at once.
- **Applied (fact corrections):** dev-env §12 Publishing states what holds each name, the 3-pending limit, the registry claim review and provider rule, the README rule, `NPR_API_KEY`, and the Snakemake catalogue's exact-name rule and where it reads the plugin's page.
- **Prepared, not run:** `.github/workflows/pypi-publish.yml` (manual, one project per run, trusted publishing in environment `pypi-<project>`) and three working `0.0.0` packages in `tools/release/pypi-placeholders/`; the steps for Thomas are in [Claim the package names](../developer/claim-package-names.md). Claude never publishes.
- **Assumed, pending Thomas:** the placeholder version `0.0.0` (a PyPI file name can never be reused, so `0.0.1` stays free) and the environments' protection (Thomas as required reviewer, `main` only). The registry provider string is Thomas's choice at the claim.
- **Changed:** [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases); inbox #66 (status note); the new guide and figure `name-claim`.

## 2026-10-29 — The repository moves to the `spectio-org` organization

- **Context.** Inbox #9 (DEP-T-026) kept packages and images under `weber8thomas` until a move. Trusted publishers and the metadata of a PyPI release are bound to the owner, and a released file can never be uploaded again, so the move had to come before the first `0.0.0` upload.
- **Decided (Thomas, 2026-10-29):** a dedicated organization, not depictio's: "mais du coup spectio devient un sous ensemble de depictio alors que cela ne fais pas la mm chose" (Spectio would become a subset of depictio although it does something different). The name `spectio` was taken; Thomas transferred the repository to `spectio-org` and added the three PyPI pending publishers with that owner.
- **Changed:** the `Repository` URL and the notice of the three `0.0.0` packages in `tools/release/pypi-placeholders/` now point to `github.com/spectio-org/spectio`; their `Documentation` URL is removed, because GitHub Pages was never deployed (`weber8thomas.github.io/spectio/` answers 404, checked 2026-10-29) and a released file cannot be changed. The owner in [Claim the package names](../developer/claim-package-names.md) §2.3, [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) and figure `name-claim`. Inbox #9 is updated.
- **Not changed yet:** other links to `github.com/weber8thomas/spectio` in the site and records; GitHub redirects them while no new repository takes that name.
