# Spectio — UI and information architecture spec

Status: draft v0.2 · 2026-10-25 · author: Thomas Weber (with Claude)
Scope: web UI of Spectio (formerly drafted as Ductio / Perspectio). Companion docs: [`synthesis.md`](synthesis.md) (architecture), [`decisions/log.md`](../decisions/log.md) (decisions log), `spectio-tokens.css` (design tokens).

## 1. Principles

1. **Same family as depictio.** Reuse depictio's app shell, theme mechanics, components and list patterns (table / rows toggle) *(assumed — pending Thomas, inbox #29)*. Spectio differs in brand colours (Dawn palette) and emblem, not in interaction model. See §9.
2. **No terminal for end users.** Everything an end user does — register a workflow, launch, monitor, review, relaunch, debug — is possible from the browser. The CLI remains for experts and automation.
3. **State is explicit.** A run's state is always shown as icon + word + context ("Awaiting review · stage 2 of 4 · 12 min"), never as a colour alone. The same holds for every other state: check verdicts, runners, health (§3.3).
4. **Humans, AI agents and systems are first-class actors.** Every decision shows who made it (person, AI agent with model/version, or external system).
6. **Words.** The Spectio process installed on a compute environment is a **runner** (like a self-hosted CI runner). **Agent** always means an AI agent. A **stage** is a named group of processes or rules; a **gate** is a stop point at the end of a stage.
5. **Engine-agnostic surface, engine-aware details.** Lists look the same for Nextflow and Snakemake; detail panels expose engine specifics (nf-core schema, Snakemake checkpoints, etc.).

## 2. Main navigation

| Menu | Purpose | Key content |
|---|---|---|
| **Overview** | Landing screen after login | "Needs attention" (reviews pending, failed runs), active runs, recent activity, environment health |
| **Runs** | All runs, table or rows | Filters (state, workflow, engine, environment, owner, tag, date), saved views, bulk actions |
| **Review** | Gates waiting for a decision | Queue (assigned to me / my team / AI agents / external systems), evidence viewers, approve / apply changes / go back to a stage / stop *(assumed — pending Thomas, inbox #29)*, decision history |
| **Launch** | Start a run | One parameters page with a progress stepper as its header (workflow → version → parameters (form from schema) → inputs → environment → review and launch); "Review and launch" is the final step (§4.6) *(assumed — pending Thomas, inbox #30)* |
| **Workflows** | Catalog of registered workflows | Import from nf-core, Snakemake Workflow Catalog, git URL or cluster path; versions, parameter schema, stages manifest, software versions, docs |
| **Environments** | Where runs execute | Compute environments, runners, executors/backends, storage, software deployment (conda / Apptainer / Docker / modules), credentials |
| **Administration** | Instance administration (admins only; personal settings live in Profile) | depictio's four groups: People (users, groups, service accounts) · Content (projects, workflows, environments) · Activity (background tasks *(assumed — pending Thomas, inbox #29)*, runners, events & webhooks, logs, health, audit log) · Instance (branding, plugins, AI & agents, notifications, backups, maintenance, settings). Details: [`admin-and-operations.md`](admin-and-operations.md) |

Shell (depictio Glass model): a grid filling the viewport.
- **Top bar** across the full width: animated logo (home), breadcrumbs, project switcher (shown on Overview, Runs, Review, Launch and Workflows; hidden on Environments, Administration and Profile, and hidden while there is a single project ([`api-and-data-model.md`](api-and-data-model.md) §6)), search (⌘K), notifications (bell with the unread count; its panel lists in-app notifications, each deep-linking to a run or gate; `GET /me/notifications`, [`api-and-data-model.md`](api-and-data-model.md) §5) *(assumed — pending Thomas, inbox #17)*, Administration (admins only), **colour mode** (only here), avatar → Profile.
- **Sidebar** below it, full remaining height: head with "WORKSPACE" and the **fold button** (PanelLeftClose / PanelLeftOpen, as in depictio); one 56 px item per menu with a 25 px line icon in the menu's colour; active item tinted; Review shows its count; footer with runners status and server status. Folds to a 92 px icon rail (labels hidden, counts become badges).
- **Content** scrolls on its own; the shell never scrolls.

The chrome shows the bell, avatar menu, project switcher, "n / m runners" and search only when the server offers them (capabilities by version: [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §15.1). *(assumed — pending Thomas, inbox #39)*

**Logo motion (the panorama):** on load the four blades start stacked as one narrow view and fan out into the 180° panorama; on hover a beam of light sweeps across it; boot splash and long waits use a back-and-forth "radar" beam; static for favicons, print and reduced motion. Pure CSS.

## 3. Status system

### 3.1 Run states

| Value | State | Icon | Colour | Meaning |
|---|---|---|---|---|
| `queued` | Queued | clock | ink 400 | Accepted, waiting for a runner or the scheduler |
| `running` | Running | play (animated ring) | blue `#3B82F6` | Engine running |
| `awaiting_review` | Awaiting review | hand / flag | amber `#D9890B` | Stopped at a gate; a decision is required |
| `pausing` | Pausing | pause, animated ring | violet `#8B5CF6` | Stopping as requested; becomes Paused |
| `paused` | Paused | pause | violet `#8B5CF6` | Stopped on request, resumable |
| `succeeded` | Succeeded | check | green `#1F9D63` | Completed |
| `failed` | Failed | cross | red `#DC3B3B` | Engine or task failure; Resume creates a new run *(assumed — pending Thomas, inbox #32)*. With failure class `head_lost`: "Engine stopped while Spectio was down · Resume" *(assumed — pending Thomas, inbox #40)* |
| `cancelling` | Cancelling | slash, animated ring | ink 500 | Cancel requested; the head process is stopping |
| `cancelled` | Cancelled | slash | ink 500 | Stopped by a user or a policy |

The values are the run-state enum of [`api-and-data-model.md`](api-and-data-model.md) §7.1, which owns them and their WES mapping. A gate `stop` shows as Cancelled. Head silent and Runner offline are flags shown next to the state, not states ([`api-and-data-model.md`](api-and-data-model.md) §7.1). *(assumed — pending Thomas, inbox #29)*

Rendering rules (replaces the current pill badges):
- In tables: a 4 px **state rail** on the left edge of the row, plus icon + state word in the State column, plus a context line ("stage 2 of 4 · 12 min ago").
- In cards: the state rail runs along the top edge of the card; icon + word in the header.
- Hover / focus on any state shows a tooltip with the last event and timestamp.
- Task labels come from the states of [`api-and-data-model.md`](api-and-data-model.md) §7.2: pending, submitted, running, succeeded, failed, cached, stored, aborted, not scheduled; "Aborted" is an attempt the engine stopped, or never ran, because of another failure: it is not shown as a failure and does not count in the failed total *(assumed — pending Thomas, [inbox #56](../reviews/inbox.md#56-assumed-the-state-of-a-task-still-open-when-the-run-ends))*; "failed (ignored)" is `failed` with `ignored`; "retried" is shown on a task whose last attempt has n > 1. Cached and Stored are distinct looks, for `cached` and `stored`.

### 3.2 Stage gauge (the emblem as a progress indicator)

The emblem's half-disc is reused as a compact **stage gauge**: one sector per declared stage (1 to 8). Workflows without declared stages get 4 sectors = quarters of task progress, measured against `tasks_expected` when `tasks_expected_source` is `engine_plan` and against the known tasks otherwise ([`api-and-data-model.md`](api-and-data-model.md) §7 `runs`). *(assumed — pending Thomas, inbox #38)*

| Sector look | Meaning | `run_stages.state` |
|---|---|---|
| Solid brand colour (indigo → violet → coral → amber, in order) | Stage completed | `completed` |
| Brand colour, light tint (300) | Stage running | `running` |
| Amber outline + notch | Stage finished, gate awaiting review | `awaiting_review` |
| Solid red | Stage failed | `failed` |
| Grey hatched (ink 200) | Stage skipped / fully cached | `skipped` |
| Light grey (ink 100) | Stage not started | `not_started` |

Each look maps to one value of the stage-state enum ([`api-and-data-model.md`](api-and-data-model.md) §7 `run_stages`). *(assumed — pending Thomas, inbox #40)*

A legend is available from any gauge (hover / tap) and in Help. In the relaunch stage strip, stages reused from cache use animated hatching.

### 3.3 System states

States outside runs (runners, observers, model endpoints, storage, tasks, health checks, plugins) reuse the run-state tokens of §3.1. No family gets its own palette, red stays for hard failures, and every state shows icon + word.

| Run-state token | System states mapped to it |
|---|---|
| `running` | active, in progress, retrying |
| `succeeded` | healthy, online, verified |
| `review` | notice, draining, degraded, pending verification |
| `failed` | offline, failed to load, dead |
| `cancelled` | disabled |

The Legend also shows: scheduler job states and failure classes in Spectio words (red only for failures; a finished job reads Succeeded, not "Completed"); check verdicts (pass / warn / fail); pre-start states (Starts now, Waits for a slot, Queued · quota) with the clock icon, never the Running play icon; origin and level chips (UI / API / CLI / Batch; Observed / Adopted, §6). State words are exactly those of §3.1 ("Awaiting review", "Succeeded") and of its task-state list ("pending").

Check verdicts have distinct icons: check for pass, triangle for warn, octagon-x for fail. Text always says the severity ("6 / 8 pass · 1 warning · 1 failing"; in a value column "fail · 3 outliers"), never only a colour (WCAG 2.1 SC 1.4.1, https://www.w3.org/TR/WCAG21/#use-of-color).

### 3.4 Colour use and contrast

Text reaches 4.5:1 against its background (WCAG 2.1 SC 1.4.3, https://www.w3.org/TR/WCAG21/#contrast-minimum); switch tracks, icons and other non-text controls reach 3:1 (SC 1.4.11, https://www.w3.org/TR/WCAG21/#non-text-contrast). Primary buttons use `--sp-accent` (`#7750D4`, 5.41:1 with white). Section colours are for tints and icons only, never button fills. An amber fill (the Review badge, a warning action) uses `--sp-state-review-fg` (`#8F5806`, 5.89:1); otherwise run-state colours stay out of the brand. Switch tracks use `--sp-ink-400`. Helper text uses `--sp-text-faint` or `--sp-ink-500`; on the `#F7F7FB` surface use `--sp-ink-500`, since `#6E7287` gives 4.45:1 there. Adjacent segments of a bar are separated by a 1 px divider. Ratios as recomputed in review R7 with the WCAG 2.x formula.

## 4. Screens

### 4.1 Landing page (public site)
The public landing page is owned by [documentation-system §2](documentation-system.md#2-landing-page-docsindexmd). The `Landing.dc.html` board is a marketing draft for a later release, not the source of `docs/index.md`. *(assumed — pending Thomas, inbox #30)*

### 4.2 Overview
- Needs attention: reviews waiting (count, oldest), failed runs in the last 24 h.
- Active runs with stage gauge.
- Environments: runners online / offline, queue depth. A "Runner offline" card links to the runner page (§4.8).
- Recent activity feed (launches, decisions, failures).

### 4.3 Runs — table and rows
Columns: Run (name + ID, first) · State (rail + icon + word + context) · Workflow (official engine logo, name, version) · Progress (stage gauge + "2 of 4 stages · 63 % tasks" when the run has `tasks_expected`, otherwise "2 of 4 stages · N done · M running"; [`api-and-data-model.md`](api-and-data-model.md) §7 `runs`) *(assumed — pending Thomas, inbox #38)* · Environment · Origin · Started · Duration. Toggle **Table / Rows**. Rows mode = full-width "paper" rows grouped into "Needs attention" (runs in `awaiting_review`, and `failed` runs with no child run) *(assumed — pending Thomas, inbox #39)* and "Active and recent": state rail, gauge, name, workflow line, state with context, time, one contextual action (Review, Resume, Continue, Reports). The card grid is dropped. Paging: Next / Load more on cursor pages, with no numbered pages and no "of N" total until the API offers one ([`api-and-data-model.md`](api-and-data-model.md) §4); headline counts come from `GET /runs:summary` ([`api-and-data-model.md`](api-and-data-model.md) §5). *(assumed — pending Thomas, inbox #30)*

**Compare.** Selecting 2–4 rows shows a "Compare" bar that opens RunsCompare; the Parameters and Lineage tabs of Run detail open it too (§4.4). RunsCompare shows no depictio link when the hand-off is off. *(assumed — pending Thomas, inbox #40)* In Compare, Outcome and CPU-hours are shown only when per-run checks and scheduler accounting exist (capabilities by version: [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §15.1). *(assumed — pending Thomas, inbox #39)*

Engine marks: the official files (as shipped in depictio `public/logos/workflows/`), 16–24 px on white, never recoloured; one mark per workflow, nf-core replacing Nextflow for genuine nf-core pipelines.

### 4.4 Run detail
Header: run name, state line, gauge, actions by state (table below). When the runner is offline or live data is stale, the header shows that state and its actions follow §11 (for example "Queue pause · applies on reconnect"). The short run id shown is the last 6 characters of the ULID; `created_by` resolves through `GET /me` and user reads.

| State | Header actions |
|---|---|
| Queued | Cancel · Copy to a new launch |
| Running | Cancel (Pause after stage is shown only once `:pause` exists, inbox #16) |
| Awaiting review | Review (opens the gate) · Relaunch… · Cancel |
| Paused | Continue · Relaunch… · Cancel |
| Failed | Resume as new run · Relaunch… |
| Succeeded | Relaunch… |
| Cancelled | Relaunch… |
| Observed (CLI) | None besides Copy to a new launch, with the adopt banner of §6 (no relaunch); an Adopted run follows its state's row |

Copy to a new launch is under More in every state. Pause and an immediate stop follow the open question of inbox #16 (SR-018).

Relaunch… at a gate records the decision `stop` with reason `relaunched` (the run becomes `cancelled`, `cancel_reason = relaunched`), then calls `POST /runs/{id}:relaunch` with mode `rerun_from` (the gated stage by default) and the parameter overrides from the dialog (§4.6); see [`api-and-data-model.md`](api-and-data-model.md) §5 and §7. Resume on a failed run creates a child run; the failed run stays terminal. *(assumed — pending Thomas, inbox #32)*

The Failed header shows `runs.failure.message` and its class, and links to the failing task (`runs.failure.task_id`, [`api-and-data-model.md`](api-and-data-model.md) §7). *(assumed — pending Thomas, inbox #40)*

Tabs:
1. **Summary** — stages timeline, key numbers, last events.
2. **Stages & gates** — each stage with its tasks, gate, evidence, decision.
3. **Tasks** — table (process/rule, tag/wildcards, state, attempts, executor, native job id, CPU/memory, duration), filter by state; on a failed run the filter defaults to "failed, final attempt". Where each task log comes from: [architecture §13.7](architecture-plugins-and-packaging.md). *(assumed — pending Thomas, inbox #40)*
4. **Logs** — run log and per-task stdout/stderr (fetched on demand through the runner); sources per engine in [architecture §13.7](architecture-plugins-and-packaging.md). *(assumed — pending Thomas, inbox #40)*
5. **Outputs & reports** — published files, MultiQC / HTML reports (sandboxed), images, PDF, OME-Zarr viewer.
6. **Parameters** — resolved params; diff against the lineage parent, labelled "vs. run #N (resumed from)", listing only changed keys plus "N unchanged hidden · Show all". The Run detail aside shows the same short diff, with links to this tab and to RunsCompare. "Compare with previous" opens RunsCompare (§4.3) *(assumed — pending Thomas, inbox #40)*.
7. **Software** — software versions, containers, conda envs, modules (nf-core `modules.json`).
8. **Environment** — compute environment, executor, queue/partition, storage, work dir.
9. **Lineage** — previous and next runs (resume / rerun / restart), with what changed; "Compare with previous" opens RunsCompare (§4.3) *(assumed — pending Thomas, inbox #40)*.
10. **Scheduler** — head job, tasks by scheduler state, why pending, requested vs used, relaunch suggestions; shown when the environment has a scheduler observer ([`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §10). *(assumed — pending Thomas, inbox #29)*
11. **Live checks** — one row per item, one column per watched check, filled as tasks finish; shown when the run has watched stages ([`checking-scenarios.md`](checking-scenarios.md) §11.4). *(assumed — pending Thomas, inbox #29)*

The Software and Environment tabs, Batch and Adopt are shown only when the server offers them (capabilities by version: [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §15.1). *(assumed — pending Thomas, inbox #39)*

### 4.5 Review
**Review views.** Every gate is items × checks × evidence × decisions ([`checking-scenarios.md`](checking-scenarios.md)). The detail page opens on Summary, then the view that fits the item kind and scale: **item table** (a few items: samples, MS runs, predictions, grouped samples), **distributions & thresholds** (massive: cells, spots, features), **spatial grid** (wells, slides, tiles), **candidate list** (many: bins, candidate variants, structures), **report reader** (MultiQC and any HTML report, sandboxed). Examples on the canvas: Review (plate, spatial grid), ReviewCoverage (grouped samples), ReviewReport (item table + report reader), ReviewCells (distributions), ReviewCandidates (MAG bins).

**Queue** (the Review menu): built for many open gates. Summary strip (assigned to me, my groups, agents may decide, waiting for a signal), scope filter, search, group by workflow, sort by waiting time, saved views. Table rows: gate + run + ID, checks bar (pass / warn / fail) with the counts in words, e.g. "6 / 8 pass · 1 warning · 1 failing" (§3.3), suggestion (AI or robot), who can decide, waiting time (amber over 1 h), Open. Multi-select with bulk actions: approve the selected gates whose checks all pass, assign, snooze. Auto-approve rules (from the gate's `decide` policy) are reported at the bottom. Keyboard: J / K, Enter, A. Single and bulk decisions show the same lost-update (412) and partial-result states as on the phone (§4.11).

**Detail**: back to queue with "3 of 12" and previous / next; compact header (gauge, gate, run, engine, waiting time, who can decide). Tabs — what a reviewer can actually do:
| Tab | What you can do |
|---|---|
| Summary | Read gate checks (workflow-specific, from `spectio.yml`) and run health (built in), evidence viewers, the AI or robot suggestion; "Apply suggestion" turns it into pending changes |
| Items | Partial decisions per item (well, sample, cell line…): keep, redo, exclude with a reason. Plate map for plates, rows for samples. Excluded items leave the next stages but stay in the record; redone items are recomputed alone, the rest comes from cache |
| Samplesheet | Edit rows (fix metadata, add a replacement FASTQ, drop a sample); saved as a new version; only changed rows are recomputed; file checks with Recheck |
| Parameters | Change parameters for the next stages, for all items or per item when the workflow reads that parameter from a samplesheet column |
| Files | Edit intermediate outputs declared `editable` in `spectio.yml` (e.g. a TSV of per-well metrics or annotations): grid editor with diff against the original, changes by people and proposals by AI agents accepted or rejected cell by cell; versions kept |
| History | Every event and decision with its actor |
| Dashboard (only with `depictio: {on: gate:<id>}`) | Look at the preliminary depictio dashboard of the partial results, with selections kept in step ([`api-and-data-model.md`](api-and-data-model.md) §13.6, rule 3) *(assumed — pending Thomas, inbox #29)* |
All changes pile up in a **sticky bar** at the bottom (chips + a flow bar showing which stages rerun for how many items). One primary action follows from them: "Approve and continue" when nothing changed, "Apply and continue" otherwise; "Discard changes"; More: go back to an earlier stage, stop the run here, reassign.

On a server without change sets the bar is "Approve and continue" (decision `approve` with an optional justification), "Stop run" (decision `stop`) and "Relaunch with changes…" (stop with reason `relaunched`, then the relaunch dialog of §4.6); item toggles and "Apply and continue" are hidden (capabilities by version: [`dev-environment-and-testing.md`](dev-environment-and-testing.md) §15.1). *(assumed — pending Thomas, inbox #32)*

How edited files reach the engine: Snakemake — the edited file replaces the output, and its consumers rerun (modification-time trigger). Nextflow — the file is passed on Continue through the parameter named in `spectio.yml` (the pipeline must read it), since files inside the work directory must not be edited.

### 4.6 Launch and relaunch
Launch is one parameters page; a stepper across the top shows progress, and "Review and launch" is its final step *(assumed — pending Thomas, inbox #30)*. The form is generated from `nextflow_schema.json`. For Snakemake, the form comes from `config.schema.yaml` when present, otherwise it is inferred from the value types in `config/config.yaml` (nested maps become sections); the `ui:` block of `spectio.yml` refines it when present *(assumed — pending Thomas, inbox #40)*. One **collapsible section per schema group**, each with a light line icon mapped from the group's `fa_icon`, a summary on the right ("2 required", "1 issue", "2 changed") and a chevron; sections with issues or changes open by default. Search, "Show hidden", "Changed only", "Expand all", "Load params file…". File checks (samplesheet rows, paths with `exists: true`) run through the runner, show when they last ran, and have a **Recheck** button; they run again automatically before launch. Validation calls `POST /runs:validate` ([`api-and-data-model.md`](api-and-data-model.md) §5). Aside: project (first row; hidden while there is a single project, as in single-user mode, [`api-and-data-model.md`](api-and-data-model.md) §6, §11), environment, software, gates (each with "Change"), params file preview, and a "Review and launch" button, disabled while issues remain, with the reason shown beside it rather than inside it. When only one environment exists, the environment picker is hidden; Launch preselects the local environment with a software profile valid on the host *(decided — Thomas, 2026-10-27, inbox #35)*. Each gate names its source and overlay version ("1 gate after stage 2 · lab overlay rnaseq-demo-lab vN"); Launch, the review step and Run detail show the same overlay version (§5.1). *(assumed — pending Thomas, inbox #30)* On the phone wizard (§4.11), Next follows the same rule: disabled while the current step has an issue, with its reason beside it ("Fix 1 issue in Input / output") *(assumed — pending Thomas, inbox #30)*. A launch pre-filled from an imported crate shows every non-default parameter, hidden ones included, and marks the parameters that load code or config from elsewhere ([`api-and-data-model.md`](api-and-data-model.md) §5) *(decided — Thomas, 2026-10-27, inbox #25)*.

Relaunch dialog, three choices instead of five:
| Choice | What happens |
|---|---|
| **Resume** (labelled **Continue** on a paused run, which calls `:resume`; on a failed or cancelled run it calls `:relaunch` with `mode: resume` and creates a child run; on an open gate this dialog is not offered and the gate path follows the Awaiting review row of §4.4; [`api-and-data-model.md`](api-and-data-model.md) §5.1) *(assumed — pending Thomas, inbox #32)* | Pick up where it stopped; finished work reused (`-resume`; Snakemake reruns incomplete jobs) |
| **Rerun from a stage** | Click a stage on the strip; earlier stages reused, later ones recomputed (Nextflow: a generated per-process `ext` key that enters the task hash, then `-resume`, **[to be validated]** in spike T2; Snakemake `--forcerun`) |
| **Start fresh** | New work directory, nothing reused |
Under the choices: a clickable stage strip (reused · starts here · will run), "Edit parameters · N changed" (with suggestions from the failure, e.g. more memory for the task that ran out), an estimate of reused vs to-run tasks, shown only when available (for Nextflow, from a work-directory scan, labelled "estimate"; [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.5), and the primary button. "Duplicate" becomes the secondary "Copy to a new launch".

The **Edit parameters** panel reuses the Launch form sections: schema groups, search, the "Changed only" toggle, validation with the disabled reason beside the submit button, and a diff line "N changed vs. run #N". Snakemake variant: config keys (the inferred form above, SR-065) with "`--forcerun` from stage" or Continue. After submit, the new run's Run detail opens. *(assumed — pending Thomas, inbox #32)*

### 4.7 Workflows catalog and workflow detail
Catalog cards/table: name, source (nf-core / Snakemake catalog / git / local), engine, latest version, stars/topics when available, last run. Detail: one tab set for every workflow: Overview (required inputs, profiles) · README (sanitised Markdown, no raw HTML: [`authentication-and-access.md`](authentication-and-access.md) §3.1) *(decided — Thomas, 2026-10-27, inbox #23)* · Versions (versions / tags) · Parameters (schema, browsable) · Stages & gates, with sub-tabs Stages · Watches (the `spectio.yml` manifest or lab overlay, edited under one header with one draft state) · Software (versions from the last successful run) · Runs. Browsing the nf-core and Snakemake catalogues happens only in Import. When `https://nf-co.re/pipelines.json` or the Snakemake catalogue cannot be reached, import falls back to a Git URL or a path, with skeleton cards while loading. Whether HPC login nodes can reach these catalogues is site-dependent **[to be validated]**.

### 4.8 Environments
An environment = a runner + compute + storage + software deployment. List of environment cards (state rail, runner, compute, engines, storage, software, load), then one page per environment with tabs Compute · Capacity · Storage · Software · Credentials · Limits · Activity, built from collapsible sections with icons.
- **Compute**: SLURM / SGE / PBS / LSF partitions and job arrays, or Kubernetes namespace, node pools (incl. GPU), quota, live pods; executor settings per engine.
- **Capacity**: partitions, limits and fairshare, storage quotas, reservations and the pre-flight checklist; content in [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §10 (board EnvCapacity).
- **Runners**: per host or namespace, heartbeat, version, Unix user / service account, outbound-only connection. A runner is connected from its environment: "Connect a runner" (board EnvConnect) issues the one-time registration token (`POST /runners:register`, [`api-and-data-model.md`](api-and-data-model.md) §5). Registration tokens come only from there, not from Profile or Administration.
- **Storage**: one role per location — Work (scratch), Results, Inputs (read only), References (shared cache), Archive (object store), Container cache — with path, type, usage against quota, access and retention. Work-directory lifecycle rules (succeeded: delete after 30 days; failed or paused: keep while resumable; Snakemake `temp()`; cancelled: 7 days), largest work directories with Clean / Keep, quota alert with a proposed cleanup that never breaks a resumable run. Collapsed: viewer access (files streamed by the runner, HTTP range requests), staging and transfers, permissions. Aside: how each engine is pointed at these locations. API: Storage and work directories in [`api-and-data-model.md`](api-and-data-model.md) §5. *(assumed — pending Thomas, inbox #30)*
- **Software deployment**: conda, Apptainer/Singularity, Docker, environment modules, Wave.
- **Credentials**: tokens and keys (masked), scoped to environments, rotation dates.

**Runner offline** (from the sidebar footer, the Overview card or the environment): heartbeat strip showing when contact stopped; two columns, **Still working** (runs keep computing because each engine runs as its own job; live monitoring continues while the engine can post directly; otherwise events wait in the launch-directory spool and arrive when the runner is back ([architecture §13.1](architecture-plugins-and-packaging.md)) *(assumed — pending Thomas, inbox #28)*; published results stay readable) and **On hold** (new launches, cancel/pause/continue — queued and applied on reconnect —, viewers on work-directory files, storage measurements); affected runs with one action each (Open, Move to another runner on the same cluster, Review — decisions are recorded and applied later); likely cause (maintenance feed, last message, token validity, other runners); "Bring it back" command and auto-restart setup (user systemd service or cron @reboot); "Notify me when it is back" (a subscription to that runner's `spectio.runner.online`) *(assumed — pending Thomas, inbox #17)*.

### 4.9 Administration (formerly Settings)
Same structure as depictio's Administration page.
- **Layout.** The header "Administration" (shield tile), then a 208 px section nav inside the content area. Labels are 11 px uppercase: People / Content / Activity / Instance. The active item is tinted, and badges show failed background tasks and offline runners *(assumed — pending Thomas, inbox #29)*.
- **CLI equivalent.** Every page ends with a collapsible "CLI equivalent".
- **Access.** Admins only. Activity, Backups and Maintenance are hidden on public or demo instances, as in depictio.
- **Boards.** Users, Groups, Service accounts, Projects, Background tasks *(assumed — pending Thomas, inbox #29)*, Logs, Health (with the runner registry) (Administration → Runners opens Health at its Runners section, `/admin/health#runners`), Branding, Plugins, AI & agents, Backups, Restore wizard, Maintenance, and a phone Administration screen. Behaviour and fields are in [`admin-and-operations.md`](admin-and-operations.md). Events & webhooks, Audit log, Notifications and Settings have no board yet ([`admin-and-operations.md`](admin-and-operations.md) §6).

**AI & agents** opens with a three-lane diagram of where the model runs, then model endpoints, connected agents and limits.
Spectio needs no model of its own. Three ways AI comes in, each saying where the compute is:
1. **Your own agent** (MVP default): a coding assistant, lab bot or script connects through MCP or REST with a scoped token. Compute: wherever the agent runs.
2. **Built-in assistant** (optional): Spectio writes gate summaries and suggestions by calling a configured **model endpoint**: a hosted provider API (metrics and text only, no files by default) or a self-hosted OpenAI-compatible server. To provide the compute on your own cluster, the runner starts the model server as an ordinary GPU job (`spectio ai serve --env … --model … --gpus 1 --idle-stop 2h`), registers it as an endpoint, and stops it when idle.
3. **Models inside workflows** (Cellpose, classifiers): ordinary pipeline tasks on the environment's GPUs; their outputs feed gate checks.
Lists: model endpoints (kind, where it runs, data policy, state), connected agents (door: MCP / REST / webhook, scopes as chips, last action), default limits for agents (read, read evidence ≤ 50 MB, propose, approve gates only where `spectio.yml` allows, launch only on listed environments, send files to hosted models off). A gate can be stricter than the defaults, never looser.

### 4.10 User profile
From the avatar in the top bar (depictio model): identity header with stats; **CLI & API tokens** generated in the UI (scopes, created, last used, expiry, revoke) with copyable `spectio login` / `SPECTIO_TOKEN` / Nextflow and Snakemake snippets; account (auth mode, time zone, default environment and landing page); notifications matrix (event × in-app / email / Slack), stored as the user's subscriptions (`GET/PUT /me/subscriptions`) *(assumed — pending Thomas, inbox #17)*; personal agents; groups and projects (phase 2); recent activity.

### 4.11 Phone and tablet
A separate, simpler layout below 768 px (depictio's phone model), not a squeezed desktop.

**Breakpoints.** Phone < 768 px: phone layout below. Tablet 768–1199 px: desktop shell with the sidebar folded to the icon rail by default, Runs in rows mode, side columns stacked under the main column. Desktop ≥ 1200 px.

**Phone shell.**
- Compact top bar (60 px): the instance logo from Branding (`logo_mode`, `logo_url`, `logo_url_dark`, [`admin-and-operations.md`](admin-and-operations.md) §4.1), falling back to the Spectio emblem (or a back chevron on detail screens), title + one-line subtitle (where the switcher applies, the title is tappable, with a chevron, and opens the project switcher sheet), search, notifications, avatar.
- **Bottom tab bar** replacing the sidebar: floating paper bar, 64 px, inset 8 px, five keys with icon over name — Home · Runs · Review (count) · Launch · More. Active key tinted in its section colour.
- **More** opens a bottom sheet: profile, Workflows, Environments, Administration (admins only), Help, Appearance (light / dark / auto — on the phone the colour mode lives here, as in depictio), runners and server status; "Powered by Spectio" in its footer when the Spectio wordmark is hidden (admin §4.1). Section colours come from the branding layer.
- Notifications (bell) open a sheet grouped Today / Earlier, each item deep-linking to a run or gate, with empty and loading states. Phones get in-app, email and Slack notifications. Web Push through an installed PWA is undecided until spike S-R7-3 ([R7](../reviews/R7-ui.md#proposed-spikes)); browser support and the iOS home-screen requirement are **[to be validated]**. *(assumed — pending Thomas, inbox #17)*
- Content scrolls between the two bars; a screen's primary action sits in a bar pinned just above the tab bar. The pinned action bar and the tab bar are opaque, and the tab bar's backdrop covers the bottom inset (`padding-bottom: max(8px, env(safe-area-inset-bottom))`), so no content shows between or below them. A chip row that overflows ends with "+N". On Review detail and Launch, the tab bar is hidden while a pinned action bar shows. *(assumed — pending Thomas, inbox #30)*

**Phone rules.** One column; touch targets ≥ 44 × 44 px of hit area, in the shared top bar and tab bar too; the visual can be smaller (WCAG 2.2 asks 24 px at AA, SC 2.5.8, and 44 px at AAA, SC 2.5.5, https://www.w3.org/TR/WCAG22/#target-size-minimum; Spectio chose 44); body text 15–16 px; no tables (stacked rows and cards); filters and segments as horizontally scrolling pills; side panels become pill tabs; dialogs and menus become bottom sheets; nothing hover-only; at most one primary action per screen.

**Keyboard and screen readers (every layout).** Switches, checkboxes and radios are native `<input type="checkbox|radio">` inside labels, or `<button role="switch" aria-checked>`; never an ARIA-role `<span>` without focus. Tabs are `<button role="tab">` with a roving tabindex and `aria-controls` (WAI-ARIA APG tabs pattern). Per-row controls have per-row labels ("Group admin: a.smith@example.org", "Remove a.smith@example.org"); a toggle such as P.I. is a `<button aria-pressed>` with an icon of at least 3:1 (WCAG 2.1 SC 1.4.11, https://www.w3.org/TR/WCAG21/#non-text-contrast). A slider is focusable with `aria-valuenow`, `aria-valuemin` and `aria-valuemax` (APG slider pattern, https://www.w3.org/WAI/ARIA/apg/patterns/slider/), with a numeric field and −/+ beside it. No information lives only in a `title`: use a visible label or a tap-to-open sheet. Sheets and dialogs set `aria-modal="true"`, trap focus and return it to the opener. *(decided — Thomas, 2026-10-27, inbox #26)*

**Scale.** Long lists scroll without end, with an end-of-list marker and a jump to search; a count such as "Showing 50 of 312" appears only when the list returns a total ([`api-and-data-model.md`](api-and-data-model.md) §4). Gate items open flagged first and are paged through `GET /gates/{id}/items` (api §5). The plate map is an overview up to 96 wells; larger plates (384, 1,536 wells) get a quadrant picker above it. A tap on a truncated title opens a details sheet with the full name.

**Phone screens (canvas page "Mobile").**
| Screen | What changes from desktop |
|---|---|
| Home | Needs-attention cards in a horizontal row, active runs, quick launch, runners |
| Runs | Search, filter pills, one card per run (state, name, workflow, gauge, context), grouped Needs attention / Active and recent; runs started from a terminal carry a "CLI · observed" or "CLI · adopted" chip (§6) |
| Run detail | Header card with gauge and actions (Pause after stage, ⋯ for Relaunch / Cancel / Copy); pill tabs Summary · Stages · Tasks · Logs · Outputs; for a terminal run the facts say "Launched · alice@hpc-login-1 · terminal (nf-spectio)", and an observed run shows the adopt banner of §6 with ⋯ limited to that level's actions |
| Review queue | Mine / My groups / All; one card per gate with checks bar, suggestion and inline Approve when everything passes; pinned "Approve 3" bar |
| Review detail | Pill tabs Summary · Items (plate map + keep / redo / exclude) · Changes (samplesheet, parameters, files) · History; pinned "Apply and continue" bar; the plate map is an overview: tapping a row opens a zoomed strip of 12 wells with 44 px hit areas, or the reviewer decides from the flagged list; threshold sliders have −/+ steppers |
| Launch | Step wizard (Workflow · Inputs · Parameters · Where · Review), one collapsible section per schema group, Back / Next bar |
| Workflows, Environments, Runner offline | Reached from More; lists of cards with the same content as desktop, fewer columns |
| Profile | From the avatar: identity, CLI & API tokens (list, create, revoke), notification settings |
| Search | A sheet over `GET /search` (runs, workflows, tasks, samples) |
| Workflow detail | The §4.7 tabs as pill tabs |
| Environment detail | The §4.8 tabs as pill tabs, read-only |
| Administration sections | One generic read-only screen per section (Branding, Plugins, Backups… open read-only on a phone) |

**Maintenance on a phone.** The phone Administration screen never turns maintenance on with one tap: the row opens a bottom sheet (mode, message, end time, preview, a pinned "Turn on maintenance" with typed confirmation), or shows the state read-only. When maintenance is on it shows the banner text and "End now". The maintenance and announcement banner shows below the top bar on every phone screen ([`admin-and-operations.md`](admin-and-operations.md) §4.4).

**Gate decisions on a phone.** "Approve n" and inline Approve open a bottom sheet listing the gates and their checks; after confirming, a 5-second undo snackbar. A 412 from `If-Match` ([`api-and-data-model.md`](api-and-data-model.md) §4) opens "Gate changed since you opened it", showing the other decision, with "Reload" or "Review again". A bulk decision ends on a result sheet: "2 approved · 1 already decided by Bob".

## 5. Engine specifics surfaced in the UI
- Nextflow: stages from `match` globs, stopped by a generated `ext.when` config (§5.1); tasks filtered by `when:` shown as "not scheduled" (`nf-spectio`); job arrays grouped under their parent job; published files and workflow outputs.
- Snakemake: checkpoints shown as "DAG grows — at least N tasks"; temporary files with lifecycle (created → removed); group jobs; benchmark-based resource usage.

### 5.1 Stages, gates and `spectio.yml`
Where stages come from, in order: (1) declared in `spectio.yml`, in the workflow repository or attached in Spectio as a **lab overlay** for a pipeline you do not own (nf-core/rnaseq declares none; the rnaseq stages in the mockups come from such an overlay); (2) detected from structure, display only, no gates: Nextflow top-level subworkflows from the fully qualified task name (`NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN`), Snakemake module prefixes and checkpoints; (3) none: the gauge shows task quarters; resume and restart still work, rerun-from-stage does not.

The `spectio.yml` keys (`workflow`, `stages`, `gates`, `reports`, `launch`, `ui`, `depictio`) are specified in [`checking-scenarios.md`](checking-scenarios.md) §12. *(assumed — pending Thomas, inbox #29)*

How a gate stops the engine without forking:
- Nextflow — a generated config sets `ext.when = false` on the processes of later stages (nf-core modules declare `when: task.ext.when == null || task.ext.when`: nf-core/tools `0af7543`, `nf_core/module-template/main.nf:75-76`; local processes without it are not stopped **[to be validated]** in spike T2), so the run ends after the gated stage; Continue relaunches with `-resume` and without the override. This is proven only on synthetic pipelines so far ([spike note](../research/spike-synthetic-pipelines-2026-10-26.md), finding 7); real pipelines are checked on nf-core/rnaseq and sarek ([`dev-environment-and-testing.md`](dev-environment-and-testing.md) §3). **Pipeline requirements** for a Nextflow gate: every process of a later stage honours `ext.when` (nf-core modules do; local or non-nf-core processes need a `when:` that reads it); no downstream `collect`, `join`, `ifEmpty` or `mix` fails or keeps the run going when the skipped processes emit nothing; completion hooks and summaries tolerate the missing outputs. When the requirements check fails, the launch form shows "gates unavailable" with the reason. *(assumed — pending Thomas, inbox #28)*
- Snakemake — `--until` the last rules of the stage; Continue drops `--until`; rerun from a stage uses `--forcerun`.

The mechanism is owned by [`checking-scenarios.md`](checking-scenarios.md) §12.

## 6. Runs launched from the command line

How a run started in a terminal with Spectio enabled is handled.

Enabling it:
- Nextflow: the plugin `nf-spectio` (`-plugins nf-spectio`, or a `spectio` config profile/env set once by `spectio login` ([`cli-and-shared-libraries.md`](cli-and-shared-libraries.md) §2: `login` runs `engine nextflow config --install`) *(assumed — pending Thomas, inbox #28)*). It runs next to `-with-tower`, so the same run can also report to Seqera Platform (**[to be validated]** in spike T2; [decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)). Nextflow plugins cannot add new `run` flags, so there is no literal `--spectio`.
- Snakemake: `--logger <existing> spectio`, set once by `spectio login` (`engine snakemake profile --install`) *(assumed — pending Thomas, inbox #28)*: Spectio appends itself to the loggers already set on the command line or in a profile, so panoptes, snkmt or FlowO keep working ([`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md) §2).
- There is no `spectio run nextflow|snakemake` wrapper: `spectio login` is the one-time engine setup. *(assumed — pending Thomas, inbox #28)*

Three levels, decided automatically and shown on the run:

| Level | Condition | What the UI allows |
|---|---|---|
| **Observed** | Events arrive, but no runner can reach the launch directory | Full monitoring (states, tasks, logs streamed by the engine plugin). No relaunch; a banner explains how to adopt the run |
| **Adopted** | A runner running as the same user on that host can read the launch directory | Everything an UI-launched run has: resume, rerun from stage, cancel, review gates |
| **Registered workflow** | Any CLI run | The workflow is auto-added to **Workflows → Discovered** (not the curated catalog), keyed by repository + revision (Nextflow manifest / `commitId`; Snakemake git remote + Snakefile hash). One click **Promote to catalog** adds stages manifest, defaults and permissions |

Defaults: auto-registration as *Discovered* is on; an admin can switch it off (pure monitor-only). Parameters, command line, config and software versions captured from the run are kept, so a later "Copy to a new launch" can pre-fill the launch form.

## 7. Consistency with depictio (reuse plan)

The platform-level rules (shared identity and roles, run → dashboard hand-off, branding, Settings grouping, app switcher) are in [`api-and-data-model.md`](api-and-data-model.md) §13. This section covers the code reuse.

Spectio keeps the depictio UI model so a user moving between the two apps finds the same shell, gestures and vocabulary.

**Taken as is**
- Mantine 7 and the depictio theme setup (`brandTheme.ts`), with Spectio's palette ("Dawn (light)") swapped in through tokens.
- The "glass" shell: floating top bar with breadcrumbs, search (⌘K), notifications, theme toggle and avatar; foldable sidebar with a "Workspace" eyebrow and server status in its foot; bottom tab bar on phones.
- Page head: tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right.
- List pattern: table / rows toggle (`ViewPicker`) *(assumed — pending Thomas, inbox #29)*, toolbar with search, group, sort, `FilterPopover` with removable chips, view state in the URL ("Share view").
- Iconify + lucide icon set; Mantine Table for lists; AG Grid only for large data (tasks, samplesheets).

**Changed for Spectio**
- Router: TanStack Router (depictio uses a pathname switch). Deep links matter here: runs, tasks and review gates are shared in chat and by webhooks.
- Data: TanStack Query + SSE for live runs, with one `EventSource` per browser shared by its tabs (SharedWorker, or BroadcastChannel with leader election) and coalesced deltas per run ([`api-and-data-model.md`](api-and-data-model.md) §8.3) *(assumed — pending Thomas, inbox #28)*.
- Pagination on Runs and Tasks (depictio lists have none; Spectio lists grow without bound).
- JSON-schema forms (new): the launch form is generated from `nextflow_schema.json`, with a Spectio `ui:` block for Snakemake.
- Status rail + icon + word instead of pill badges (section 3).

**How to share code**
- depictio's `depictio-react-core` is private and source-only, and its shell lives in `viewer/src`. Extract a small design-system package `@depictio/ui` (theme, tokens, AppShell, PageHead, ViewPicker, FilterPopover, EmptyState) consumed by both apps; each app passes its own palette and nav.
- Until the package exists, Spectio vendors a copy of these components with a header pointing to the depictio source commit.
- depictio already has workflow models (`workflows.py`, `run_info.py`, `JobState`) and engine logos in `public/logos/workflows/`. Spectio's run states map onto `JobState`, and "Open in depictio" passes the run ID so depictio can link a dashboard to it.

## 8. Workflow metadata used by the UI

| Source | Where | Used for |
|---|---|---|
| nf-core catalog | `https://nf-co.re/pipelines.json` (`remote_workflows`, `releases[].has_schema`, topics, stars) | Catalog browsing, release picker, "has schema" hint |
| Parameter schema | `nextflow_schema.json` (draft 2020-12 `$defs`; legacy draft-07 `definitions`); nf-schema 3.x | Launch form groups (`fa_icon`, `description`, `help_text`), `hidden`, `enum`, defaults, `format` (file-path, directory-path, path, file-path-pattern), `exists`, `mimetype` |
| Samplesheet schema | `schema` key → `assets/schema_input.json` | Editable samplesheet grid with per-cell validation and file existence checks through the runner |
| Params file | `-params-file` (JSON/YAML) | What a launch, relaunch and API call actually send; submitted non-default values stored; resolved values stored separately ([`api-and-data-model.md`](api-and-data-model.md) §7). Prior art: `nf-core pipelines launch` |
| Modules | `modules.json` in the repository root | Module list and `git_sha` per release |
| Software versions | `pipeline_info/*software*versions.yml` (topic channels) | Software tab of a run; "last seen" versions on the workflow page |
| Run reports | `pipeline_info/execution_report*.html`, `execution_timeline*.html`, `execution_trace*.txt`, `params_*.json`; `**/multiqc_report.html` | Outputs & reports tab, viewers |
| Snakemake catalog | Snakemake Workflow Catalog `data.json`; `.snakemake-workflow-catalog.yml` | Catalog browsing for Snakemake |
| Snakemake config schema | `workflow/schemas/config.schema.yaml` (no UI hints) | Validation; labels, groups and pickers come from the optional `ui:` block in `spectio.yml` |
| Snakemake run data | `.snakemake/metadata`, benchmark TSVs, conda env files, wrapper tags | Task history, resource usage, software versions |

## 9. Open items
- Engine logos: plug in the official files already in depictio (`public/logos/workflows/`). nf-core is MIT and appears only next to genuine nf-core pipelines; Nextflow follows Seqera's brand manual (official files, never recoloured); Snakemake is MIT with no published guidelines. Mockups keep labelled placeholder tiles until this is done.
- `@depictio/ui` extraction: agree on the package boundary with the depictio codebase before Spectio's first UI release.
- Snakemake `ui:` block: draft its format in [`checking-scenarios.md`](checking-scenarios.md) §12. *(assumed — pending Thomas, inbox #29)*

## 10. Scenario coverage and UI patterns (2026-10-26)

The canvas covers the nf-core catalogue by class ([`checking-scenarios.md`](checking-scenarios.md) §1), runs without gates, and the operational cases. Boards use real data where it exists: nf-core megatest outputs and real test images ([`dev-environment-and-testing.md`](dev-environment-and-testing.md) §10.3–10.4). The spec gaps the boards found are in [`reviews/R12-ui-scenarios.md`](../reviews/R12-ui-scenarios.md).

### 10.1 Scenarios × boards

| Class (pipelines in the survey) | Scenario | Boards |
|---|---|---|
| Bulk sample (45) | mapping QC with groups; small RNA; amplicons through DADA2; ChIP with input controls; bisulfite conversion; fusion candidates | ReviewReport (rnaseq), ReviewSmallRNA (smrnaseq), ReviewAmpliseq (ampliseq), ReviewChip (chipseq), ReviewMethyl (methylseq), ReviewFusions (rnafusion), WorkflowOverlay (atacseq) |
| Sample + assembly (13) | MAG bins; SARS-CoV-2 amplicon coverage | ReviewCandidates (mag), ReviewViral (viralrecon) |
| Grouped samples + variants (11) | tumour/normal samplesheet; trios and consistency checks | ReviewCoverage (sarek), ReviewTrio (raredisease) |
| Predictions (8) | structures; a run-level gate waiting for a signal | ReviewStructures, ReviewSignal (proteinfold) |
| Run only (8) | public accessions chained into rnaseq; no review | LaunchChain (fetchngs) |
| Image + cell / tile (7) and lab imaging | plate wells; whole-slide tiles; IMC ROIs; spots; Xenium; light-sheet volume; satellite scenes | ReviewWells, ReviewSlides, ReviewROIs (imcyto), ReviewSpots (molkart), ReviewXenium (spatialaxe), ReviewVolume (lsmquant), ReviewTiles (rangeland), Review (Snakemake plate) |
| Sample + cells (5) | cell thresholds; immune repertoires | ReviewCells (scrnaseq), ReviewRepertoire (airrflow) |
| MS runs (5) | runs without MultiQC, table bindings | ReviewProteomics (diaproteomics) |
| Sample + features (4) | contamination and negative controls | ReviewContamination (taxprofiler) |
| No gate (most runs) | straight through, outputs, depictio; no stages declared | RunOutputs (ampliseq), RunFailed (Snakemake), LaunchGitNoSchema, LaunchReview |
| Operations | failure and relaunch; CLI-observed run; lineage compare; batch; samplesheet from files; catalogue, import, discovered, versions; runner connect, software, single machine, quotas | RunFailed, RelaunchDialog, RunObserved, RunsCompare, LaunchBatch, LaunchSamplesheet, WorkflowsCatalog, WorkflowImport, WorkflowDiscovered, WorkflowVersions, EnvConnect, EnvSoftware, EnvLocal, EnvAccess |
| Lists | a lab's mix, about 4 runs in 5 without a gate | ReviewQueue, RunsTable, RunsRows, Overview |
| Live checks and depictio | important stages and per-file checks during a run, no gate; editing watches in a lab overlay; a gate with an embedded preliminary depictio dashboard (embedded when co-hosted on depictio's origin, otherwise a deep link) *(decided — Thomas, 2026-10-27, inbox #23)*; the depictio dashboard with Spectio decisions joined ([`checking-scenarios.md`](checking-scenarios.md) §11, [`api-and-data-model.md`](api-and-data-model.md) §13.6) | RunLiveChecks (rnaseq), WorkflowWatches (rnaseq), ReviewDashboard (rnaseq), DepictioDecisions (rnaseq) |

### 10.2 UI patterns to build once

These are the component types the boards share. Each is built once, in the shared UI package, before screens multiply.

| Pattern | Used by |
|---|---|
| Item table: worst first, lanes by group or role, passing lane collapsed, a decision per row, binding chips on check cards | every Review board |
| Constraint warning with resolutions (accept degraded group, reassign, exclude group, flag instead) | ReviewTrio, ReviewChip, ReviewReport, ReviewAmpliseq, ReviewRepertoire |
| Rule strip with live counts and per-item exceptions | ReviewCells, ReviewContamination, ReviewSmallRNA, ReviewTiles |
| Distributions in HTML: histogram, strip plot, funnel, survival sparkline, knee plot, M-bias | ReviewCells, ReviewWells, ReviewAmpliseq, ReviewRepertoire, ReviewMethyl |
| Matrix: items × sub-regions heatmap with column markers | ReviewViral, ReviewTiles |
| Spatial grid of real thumbnails, with check badges, decision rings and hatching | ReviewWells, ReviewSlides, ReviewROIs |
| OME-Zarr viewer: pyramid, channels and windows, labels, z, compare inset; brightfield RGB | ViewerOmeZarr, all imaging reviews |
| Candidate list: scatter of two metrics, evidence panel, accept / reject / flag, AI proposal waiting for a person | ReviewCandidates, ReviewStructures, ReviewFusions |
| Report reader (sandboxed) with item side panel | ReviewReport, RunOutputs |
| Sticky changes bar, with a primary action disabled together with its reason | every Review board |
| Stage strip and reuse bar (reused, rerun, to run) | RelaunchDialog, RunFailed, RunsCompare, ReviewMethyl |
| Failure-class card with evidence and a suggested fix | RunFailed, RelaunchDialog |
| Diff views: parameters, modules, software, files | RunsCompare, WorkflowVersions, ReviewROIs |
| File browser through the runner, permission states | LaunchSamplesheet, WorkflowImport, RunOutputs |
| Wizard with live state (heartbeat, checks with inline fix) | EnvConnect, WorkflowImport, Launch |
| Quota and limit bars, permission matrix | EnvAccess, EnvSoftware, LaunchBatch |
| Restricted-data banner and access log | ReviewTrio |
| Live check grid: items × watched checks, cells filled as tasks finish (pass, warn, running), with a check feed | RunLiveChecks |
| Embedded depictio frame with selection sync and a decision layer beside it (only when co-hosted on depictio's origin; otherwise a deep link, [`api-and-data-model.md`](api-and-data-model.md) §13.6 rule 3) *(decided — Thomas, 2026-10-27, inbox #23)* | ReviewDashboard |

Every pattern has the component states of §11.

## 11. Component states

Every pattern of §10.2 has these states. *(assumed — pending Thomas, inbox #29)*

| State | What it shows |
|---|---|
| Empty | Nothing to show; says why and the next step |
| Loading | A skeleton of the final layout: skeleton rows for tables and skeleton cards (header kept, grey gauges); never a bare "0" |
| Error | What failed, Retry, and the request ID: an error panel that maps the RFC 9457 problem `type` (catalogue: [`api-and-data-model.md`](api-and-data-model.md) §4.1) to a sentence; an API-error toast for a failed action; a full-page "Spectio is unreachable" |
| Permission | View only; the action is disabled with its reason |
| n/a | A value that cannot be computed, such as a check whose file is missing; shown as "n/a" with the reason |

**Live data.** Each state is shown with an icon and a word, never colour alone:
- *Live*.
- *Reconnecting*: "Reconnecting… data as of 10:41:08", Retry; SSE resumes with `Last-Event-ID` (api §5).
- *Stale*: an observer layer timed out or was switched off ("squeue timed out · next try in 4 min", "`sinfo` stale since 13:40, back-off 10 min", `observer.capacity: off` shown as "disabled by site policy"; [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md) §3.2).
- *Head silent*: "No event from nf-spectio for 6 min · head job 48213351 still RUNNING · checking the head log" (schedulers §7).
- *Runner offline*: run actions become "Queue pause · applies on reconnect" with the reason and a link to Runner offline (§4.8); storage and capacity show "last measured 14:02 · on hold".
- *Catching up after restart*: a banner on a run while the API marks it `recovering: true`; its state-changing actions are disabled with that reason (boot order: [architecture §7.2](architecture-plugins-and-packaging.md)). *(assumed — pending Thomas, inbox #40)*

Live / Reconnecting in the footer is computed by the client from its SSE connection, not reported by the server (a stopped server cannot report itself). *(decided — Thomas, 2026-10-27, inbox #35)*

Actions that cannot take effect now are relabelled or disabled with their reason, and decision screens show the age of their data, so nobody pauses, cancels or approves on stale numbers without seeing it.

**Phone.** A status strip under the top bar with Live / "Reconnecting… last update 10:42" / Offline (actions disabled with the reason), on Run detail and Review detail.

The Legend board carries a "Live data" row (live, stale, reconnecting, head silent).
