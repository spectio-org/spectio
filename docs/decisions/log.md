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
