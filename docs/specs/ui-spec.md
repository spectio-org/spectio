# Spectio — UI and information architecture spec

Status: draft v0.2 · 2026-10-25 · author: Thomas Weber (with Claude)
Scope: web UI of Spectio (formerly drafted as Ductio / Perspectio). Companion docs: [`synthesis.md`](synthesis.md) (architecture), [`decisions/log.md`](../decisions/log.md) (decisions log), `spectio-tokens.css` (design tokens).

## 1. Principles

1. **Same family as depictio.** Reuse depictio's app shell, theme mechanics, components and list patterns (card grid / table toggle). Spectio differs in brand colours (Dawn palette) and emblem, not in interaction model. See §9.
2. **No terminal for end users.** Everything an end user does — register a workflow, launch, monitor, review, relaunch, debug — is possible from the browser. The CLI remains for experts and automation.
3. **State is explicit.** A run's state is always shown as icon + word + context ("Awaiting review · stage 2 of 4 · 12 min"), never as a colour alone.
4. **Humans, AI agents and systems are first-class actors.** Every decision shows who made it (person, AI agent with model/version, or external system).
6. **Words.** The Spectio process installed on a compute environment is a **runner** (like a self-hosted CI runner). **Agent** always means an AI agent. A **stage** is a named group of processes or rules; a **gate** is a stop point at the end of a stage.
5. **Engine-agnostic surface, engine-aware details.** Lists look the same for Nextflow and Snakemake; detail panels expose engine specifics (nf-core schema, Snakemake checkpoints, etc.).

## 2. Main navigation

| Menu | Purpose | Key content |
|---|---|---|
| **Overview** | Landing screen after login | "Needs attention" (reviews pending, failed runs), active runs, recent activity, environment health |
| **Runs** | All runs, table or rows | Filters (state, workflow, engine, environment, owner, tag, date), saved views, bulk actions |
| **Review** | Interventions waiting for a decision | Queue (assigned to me / my team / AI agents / external systems), evidence viewers, approve / change params / rerun / reject, decision history |
| **Launch** | Start a run | Wizard: workflow → version → parameters (form from schema) → inputs → environment → review & launch |
| **Workflows** | Catalog of registered workflows | Import from nf-core, Snakemake Workflow Catalog, git URL or cluster path; versions, parameter schema, stages manifest, software versions, docs |
| **Environments** | Where runs execute | Compute environments, runners, executors/backends, storage, software deployment (conda / Apptainer / Docker / modules), credentials |
| **Administration** | Instance administration (admins only; personal settings live in Profile) | depictio's four groups: People (users, groups, service accounts) · Content (projects, workflows, environments) · Activity (tasks, runners, events & webhooks, logs, health, audit log) · Instance (branding, plugins, AI & agents, notifications, backups, maintenance, settings). Details: [`admin-and-operations.md`](admin-and-operations.md) |

Shell (depictio Glass model): a grid filling the viewport.
- **Top bar** across the full width: animated logo (home), breadcrumbs, search (⌘K), notifications, settings, **colour mode** (only here), avatar → Profile.
- **Sidebar** below it, full remaining height: head with "WORKSPACE" and the **fold button** (PanelLeftClose / PanelLeftOpen, as in depictio); one 56 px item per menu with a 25 px line icon in the menu's colour; active item tinted; Review shows its count; footer with runners status and server status. Folds to a 92 px icon rail (labels hidden, counts become badges).
- **Content** scrolls on its own; the shell never scrolls.

**Logo motion (the panorama):** on load the four blades start stacked as one narrow view and fan out into the 180° panorama; on hover a beam of light sweeps across it; boot splash and long waits use a back-and-forth "radar" beam; static for favicons, print and reduced motion. Pure CSS.

## 3. Status system

### 3.1 Run states

| State | Icon | Colour | Meaning |
|---|---|---|---|
| Queued | clock | ink 400 | Accepted, waiting for a runner or the scheduler |
| Running | play (animated ring) | blue `#3B82F6` | Engine running |
| Awaiting review | hand / flag | amber `#D9890B` | Stopped at a gate; a decision is required |
| Paused | pause | violet `#8B5CF6` | Stopped on request, resumable |
| Succeeded | check | green `#1F9D63` | Completed |
| Failed | cross | red `#DC3B3B` | Engine or task failure; resumable |
| Cancelled | slash | ink 500 | Stopped by a user or a policy |

Rendering rules (replaces the current pill badges):
- In tables: a 4 px **state rail** on the left edge of the row, plus icon + state word in the State column, plus a context line ("stage 2 of 4 · 12 min ago").
- In cards: the state rail runs along the top edge of the card; icon + word in the header.
- Hover / focus on any state shows a tooltip with the last event and timestamp.
- Task states (Nextflow / Snakemake) map to: pending, submitted, running, succeeded, retried, failed, failed (ignored), cached, stored, not scheduled.

### 3.2 Stage gauge (the emblem as a progress indicator)

The emblem's half-disc is reused as a compact **stage gauge**: one sector per declared stage (1 to 8). Workflows without declared stages get 4 sectors = quarters of task progress.

| Sector look | Meaning |
|---|---|
| Solid brand colour (indigo → violet → coral → amber, in order) | Stage completed |
| Brand colour, light tint (300) | Stage running |
| Amber outline + notch | Stage finished, gate awaiting review |
| Solid red | Stage failed |
| Grey hatched (ink 200) | Stage skipped / fully cached |
| Light grey (ink 100) | Stage not started |

A legend is available from any gauge (hover / tap) and in Help. In the relaunch stage strip, stages reused from cache use animated hatching.

## 4. Screens

### 4.1 Landing page (public site)
Hero (logo, one-line promise, "Get started" / "Docs" / GitHub), three pillars (Launch without a terminal · See every run · Steer with checkpoints), works-with strip (Nextflow, nf-core, Snakemake, SLURM, Kubernetes, GA4GH WES), how it works in three steps (install the server, connect a runner, launch from the browser), screenshots, sister project depictio, footer.

### 4.2 Overview
- Needs attention: reviews waiting (count, oldest), failed runs in the last 24 h.
- Active runs with stage gauge.
- Environments: runners online / offline, queue depth. A "Runner offline" card links to the runner page (§4.8).
- Recent activity feed (launches, decisions, failures).

### 4.3 Runs — table and rows
Columns: Run (name + ID, first) · State (rail + icon + word + context) · Workflow (official engine logo, name, version) · Progress (stage gauge + "2 of 4 stages · 63 % tasks") · Environment · Origin · Started · Duration. Toggle **Table / Rows**. Rows mode = full-width "paper" rows grouped into "Needs attention" and "Active and recent": state rail, gauge, name, workflow line, state with context, time, one contextual action (Review, Resume, Continue, Reports). The card grid is dropped.

Engine marks: the official files (as shipped in depictio `public/logos/workflows/`), 16–24 px on white, never recoloured; one mark per workflow, nf-core replacing Nextflow for genuine nf-core pipelines.

### 4.4 Run detail
Header: run name, state line, gauge, actions (Resume, Relaunch…, Cancel, Duplicate). Tabs:
1. **Summary** — stages timeline, key numbers, last events.
2. **Stages & gates** — each stage with its tasks, gate, evidence, decision.
3. **Tasks** — table (process/rule, tag/wildcards, state, attempts, executor, native job id, CPU/memory, duration), filter by state.
4. **Logs** — run log and per-task stdout/stderr (fetched on demand through the runner).
5. **Outputs & reports** — published files, MultiQC / HTML reports (sandboxed), images, PDF, OME-Zarr viewer.
6. **Parameters** — resolved params, diff against the previous run of the lineage.
7. **Software** — software versions, containers, conda envs, modules (nf-core `modules.json`).
8. **Environment** — compute environment, executor, queue/partition, storage, work dir.
9. **Lineage** — previous and next runs (resume / rerun / restart), with what changed.

### 4.5 Review
**Review views.** Every gate is items × checks × evidence × decisions ([`checking-scenarios.md`](checking-scenarios.md)). The detail page opens on Summary, then the view that fits the item kind and scale: **item table** (a few items: samples, MS runs, predictions, grouped samples), **distributions & thresholds** (massive: cells, spots, features), **spatial grid** (wells, slides, tiles), **candidate list** (many: bins, candidate variants, structures), **report reader** (MultiQC and any HTML report, sandboxed). Examples on the canvas: Review (plate, spatial grid), ReviewCoverage (grouped samples), ReviewReport (item table + report reader), ReviewCells (distributions), ReviewCandidates (MAG bins).

**Queue** (the Review menu): built for many open gates. Summary strip (assigned to me, my groups, agents may decide, waiting for a signal), scope filter, search, group by workflow, sort by waiting time, saved views. Table rows: gate + run + ID, checks bar (pass / warn / fail), suggestion (AI or robot), who can decide, waiting time (amber over 1 h), Open. Multi-select with bulk actions: approve the selected gates whose checks all pass, assign, snooze. Auto-approve rules (Settings) are reported at the bottom. Keyboard: J / K, Enter, A.

**Detail**: back to queue with "3 of 12" and previous / next; compact header (gauge, gate, run, engine, waiting time, who can decide). Tabs — what a reviewer can actually do:
| Tab | What you can do |
|---|---|
| Summary | Read gate checks (workflow-specific, from `spectio.yml`) and run health (built in), evidence viewers, the AI or robot suggestion; "Apply suggestion" turns it into pending changes |
| Items | Partial decisions per item (well, sample, cell line…): keep, redo, exclude with a reason. Plate map for plates, rows for samples. Excluded items leave the next stages but stay in the record; redone items are recomputed alone, the rest comes from cache |
| Samplesheet | Edit rows (fix metadata, add a replacement FASTQ, drop a sample); saved as a new version; only changed rows are recomputed; file checks with Recheck |
| Parameters | Change parameters for the next stages, for all items or per item when the workflow reads that parameter from a samplesheet column |
| Files | Edit intermediate outputs declared `editable` in `spectio.yml` (e.g. a TSV of per-well metrics or annotations): grid editor with diff against the original, changes by people and proposals by AI agents accepted or rejected cell by cell; versions kept |
| History | Every event and decision with its actor |
All changes pile up in a **sticky bar** at the bottom (chips + a flow bar showing which stages rerun for how many items). One primary action follows from them: "Approve and continue" when nothing changed, "Apply and continue" otherwise; "Discard changes"; More: go back to an earlier stage, stop the run here, reassign.

How edited files reach the engine: Snakemake — the edited file replaces the output, and its consumers rerun (modification-time trigger). Nextflow — the file is passed on Continue through the parameter named in `spectio.yml` (the pipeline must read it), since files inside the work directory must not be edited.

### 4.6 Launch and relaunch
Launch: the form is generated from `nextflow_schema.json` (or the Snakemake config schema plus the `ui:` block of `spectio.yml`). One **collapsible section per schema group**, each with a light line icon mapped from the group's `fa_icon`, a summary on the right ("2 required", "1 issue", "2 changed") and a chevron; sections with issues or changes open by default. Search, "Show hidden", "Changed only", "Expand all", "Load params file…". File checks (samplesheet rows, paths with `exists: true`) run through the runner, show when they last ran, and have a **Recheck** button; they run again automatically before launch. Aside: environment, software, gates (each with "Change"), params file preview, Launch button (disabled with the reason while issues remain).

Relaunch dialog, three choices instead of five:
| Choice | What happens |
|---|---|
| **Resume** (labelled **Continue** on a paused run or an open gate) | Pick up where it stopped; finished work reused (`-resume`; Snakemake reruns incomplete jobs) |
| **Rerun from a stage** | Click a stage on the strip; earlier stages reused, later ones recomputed (Nextflow stage override + `-resume`; Snakemake `--forcerun`) |
| **Start fresh** | New work directory, nothing reused |
Under the choices: a clickable stage strip (reused · starts here · will run), "Edit parameters · N changed" (with suggestions from the failure, e.g. more memory for the task that ran out), an estimate of reused vs to-run tasks, and the primary button. "Duplicate" becomes the secondary "Copy to a new launch".

### 4.7 Workflows catalog and workflow detail
Catalog cards/table: name, source (nf-core / Snakemake catalog / git / local), engine, latest version, stars/topics when available, last run. Detail: README, versions/tags, parameter schema (browsable), stages manifest (`spectio.yml`), required inputs, profiles, software versions from the last successful run, runs of this workflow.

### 4.8 Environments
An environment = a runner + compute + storage + software deployment. List of environment cards (state rail, runner, compute, engines, storage, software, load), then one page per environment with tabs Compute · Storage · Software · Credentials · Limits · Activity, built from collapsible sections with icons.
- **Compute**: SLURM / SGE / PBS / LSF partitions and job arrays, or Kubernetes namespace, node pools (incl. GPU), quota, live pods; executor settings per engine.
- **Runners**: per host or namespace, heartbeat, version, Unix user / service account, outbound-only connection.
- **Storage**: one role per location — Work (scratch), Results, Inputs (read only), References (shared cache), Archive (object store), Container cache — with path, type, usage against quota, access and retention. Work-directory lifecycle rules (succeeded: delete after 30 days; failed or paused: keep while resumable; Snakemake `temp()`; cancelled: 7 days), largest work directories with Clean / Keep, quota alert with a proposed cleanup that never breaks a resumable run. Collapsed: viewer access (files streamed by the runner, HTTP range requests), staging and transfers, permissions. Aside: how each engine is pointed at these locations.
- **Software deployment**: conda, Apptainer/Singularity, Docker, environment modules, Wave.
- **Credentials**: tokens and keys (masked), scoped to environments, rotation dates.

**Runner offline** (from the sidebar footer, the Overview card or the environment): heartbeat strip showing when contact stopped; two columns, **Still working** (runs keep computing because each engine runs as its own job; live monitoring continues because engines send events straight to the server; published results stay readable) and **On hold** (new launches, cancel/pause/continue — queued and applied on reconnect —, viewers on work-directory files, storage measurements); affected runs with one action each (Open, Move to another runner on the same cluster, Review — decisions are recorded and applied later); likely cause (maintenance feed, last message, token validity, other runners); "Bring it back" command and auto-restart setup (user systemd service or cron @reboot); "Notify me when it is back".

### 4.9 Administration (formerly Settings)
Same structure as depictio's Administration page.
- **Layout.** The header "Administration" (shield tile), then a 208 px section nav inside the content area. Labels are 11 px uppercase: People / Content / Activity / Instance. The active item is tinted, and badges show failed tasks and offline runners.
- **CLI equivalent.** Every page ends with a collapsible "CLI equivalent".
- **Access.** Admins only. Activity, Backups and Maintenance are hidden on public or demo instances, as in depictio.
- **Boards.** Users, Groups, Service accounts, Projects, Tasks, Logs, Health (with the runner registry), Branding, Plugins, AI & agents, Backups, Restore wizard, Maintenance, and a phone Administration screen. Behaviour and fields are in [`admin-and-operations.md`](admin-and-operations.md).

**AI & agents** opens with a three-lane diagram of where the model runs, then model endpoints, connected agents and limits.
Spectio needs no model of its own. Three ways AI comes in, each saying where the compute is:
1. **Your own agent** (MVP default): a coding assistant, lab bot or script connects through MCP or REST with a scoped token. Compute: wherever the agent runs.
2. **Built-in assistant** (optional): Spectio writes gate summaries and suggestions by calling a configured **model endpoint**: a hosted provider API (metrics and text only, no files by default) or a self-hosted OpenAI-compatible server. To provide the compute on your own cluster, the runner starts the model server as an ordinary GPU job (`spectio ai serve --env … --model … --gpus 1 --idle-stop 2h`), registers it as an endpoint, and stops it when idle.
3. **Models inside workflows** (Cellpose, classifiers): ordinary pipeline tasks on the environment's GPUs; their outputs feed gate checks.
Lists: model endpoints (kind, where it runs, data policy, state), connected agents (door: MCP / REST / webhook, scopes as chips, last action), default limits for agents (read, read evidence ≤ 50 MB, propose, approve gates only where `spectio.yml` allows, launch only on listed environments, send files to hosted models off). A gate can be stricter than the defaults, never looser.

### 4.10 User profile
From the avatar in the top bar (depictio model): identity header with stats; **CLI & API tokens** generated in the UI (scopes, created, last used, expiry, revoke) with copyable `spectio login` / `SPECTIO_TOKEN` / Nextflow and Snakemake snippets; account (auth mode, time zone, default environment and landing page); notifications matrix (event × in-app / email / Slack); personal agents; groups and projects (phase 2); recent activity.

### 4.11 Phone and tablet
A separate, simpler layout below 768 px (depictio's phone model), not a squeezed desktop.

**Breakpoints.** Phone < 768 px: phone layout below. Tablet 768–1199 px: desktop shell with the sidebar folded to the icon rail by default, Runs in rows mode, side columns stacked under the main column. Desktop ≥ 1200 px.

**Phone shell.**
- Compact top bar (60 px): logo (or a back chevron on detail screens), title + one-line subtitle, search, notifications, avatar.
- **Bottom tab bar** replacing the sidebar: floating paper bar, 64 px, inset 8 px, five keys with icon over name — Home · Runs · Review (count) · Launch · More. Active key tinted in its section colour.
- **More** opens a bottom sheet: profile, Workflows, Environments, Settings, Help, Appearance (light / dark / auto — on the phone the colour mode lives here, as in depictio), runners and server status.
- Content scrolls between the two bars; a screen's primary action sits in a bar pinned just above the tab bar.

**Phone rules.** One column; touch targets ≥ 44 px; body text 15–16 px; no tables (stacked rows and cards); filters and segments as horizontally scrolling pills; side panels become pill tabs; dialogs and menus become bottom sheets; nothing hover-only; at most one primary action per screen.

**Phone screens (canvas page "Mobile").**
| Screen | What changes from desktop |
|---|---|
| Home | Needs-attention cards in a horizontal row, active runs, quick launch, runners |
| Runs | Search, filter pills, one card per run (state, name, workflow, gauge, context), grouped Needs attention / Active and recent |
| Run detail | Header card with gauge and actions (Pause after stage, ⋯ for Relaunch / Cancel / Copy); pill tabs Summary · Stages · Tasks · Logs · Outputs |
| Review queue | Mine / My groups / All; one card per gate with checks bar, suggestion and inline Approve when everything passes; pinned "Approve 3" bar |
| Review detail | Pill tabs Summary · Items (plate map + keep / redo / exclude) · Changes (samplesheet, parameters, files) · History; pinned "Apply and continue" bar |
| Launch | Step wizard (Workflow · Inputs · Parameters · Where · Review), one collapsible section per schema group, Back / Next bar |
| Workflows, Environments, Runner offline | Reached from More; lists of cards with the same content as desktop, fewer columns |

## 5. Engine specifics surfaced in the UI
- Nextflow: stages through a `stage` parameter; tasks filtered by `when:` shown as "not scheduled" (companion plugin); job arrays grouped under their parent job; published files and workflow outputs.
- Snakemake: checkpoints shown as "DAG grows — at least N tasks"; temporary files with lifecycle (created → removed); group jobs; benchmark-based resource usage.

### 5.1 Stages, gates and `spectio.yml`
Where stages come from, in order: (1) declared in `spectio.yml`, in the workflow repository or attached in Spectio as a **lab overlay** for a pipeline you do not own (nf-core/rnaseq declares none; the rnaseq stages in the mockups come from such an overlay); (2) detected from structure, display only, no gates: Nextflow top-level subworkflows from the fully qualified task name (`NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN`), Snakemake module prefixes and checkpoints; (3) none: the gauge shows task quarters; resume and restart still work, rerun-from-stage does not.

`spectio.yml` keys: `workflow` (name, engine, version range), `stages` (id, name, `match` globs on process / rule names, optional `gate`, `important`, `watch` for live per-file checks: [`checking-scenarios.md`](checking-scenarios.md) §11), `gates` (title, `evidence` globs for the viewers, `checks` (metric, min/max, per item), `items` (what one item is: samplesheet rows, wells…), `editable` (intermediate files a reviewer may change, with how they are fed back: in place for Snakemake, through a named parameter for Nextflow), `decide` (auto_approve, humans, agents: propose | approve | none, timeout)), `reports`, `launch` (profiles, hidden params), and for Snakemake `ui` (labels, groups, file pickers for config keys).

How a gate stops the engine without forking: Nextflow — a generated config sets `ext.when = false` on the processes of later stages (nf-core modules honour `task.ext.when`), so the run ends after the gated stage; Continue relaunches with `-resume` and without the override. Snakemake — `--until` the last rules of the stage; Continue drops `--until`; rerun from a stage uses `--forcerun`.

## 6. Runs launched from the command line

How a run started in a terminal with Spectio enabled is handled.

Enabling it:
- Nextflow: the plugin `nf-spectio` (`-plugins nf-spectio`, or a `spectio` config profile/env set once by `spectio login`). It runs next to `-with-tower`, so the same run can also report to Seqera Platform ([decision 0001](../decisions/0001-nextflow-through-nf-spectio.md)). Nextflow plugins cannot add new `run` flags, so there is no literal `--spectio`.
- Snakemake: `--logger spectio`.
- Convenience wrapper: `spectio run nextflow …` / `spectio run snakemake …` injects the above and registers the launch directory.

Three levels, decided automatically and shown on the run:

| Level | Condition | What the UI allows |
|---|---|---|
| **Observed** | Events arrive, but no runner can reach the launch directory | Full monitoring (states, tasks, logs streamed by the engine plugin). No relaunch; a banner explains how to adopt the run |
| **Adopted** | A runner running as the same user on that host can read the launch directory | Everything an UI-launched run has: resume, rerun from stage, cancel, review gates |
| **Registered workflow** | Any CLI run | The workflow is auto-added to **Workflows → Discovered** (not the curated catalog), keyed by repository + revision (Nextflow manifest / `commitId`; Snakemake git remote + Snakefile hash). One click **Promote to catalog** adds stages manifest, defaults and permissions |

Defaults: auto-registration as *Discovered* is on; an admin can switch it off (pure monitor-only). Parameters, command line, config and software versions captured from the run are kept, so a later "Duplicate" can pre-fill the launch form.

## 7. Consistency with depictio (reuse plan)

The platform-level rules (shared identity and roles, run → dashboard hand-off, branding, Settings grouping, app switcher) are in [`api-and-data-model.md`](api-and-data-model.md) §13. This section covers the code reuse.

Spectio keeps the depictio UI model so a user moving between the two apps finds the same shell, gestures and vocabulary.

**Taken as is**
- Mantine 7 and the depictio theme setup (`brandTheme.ts`), with Spectio's palette ("Dawn (light)") swapped in through tokens.
- The "glass" shell: floating top bar with breadcrumbs, search (⌘K), notifications, theme toggle and avatar; foldable sidebar with a "Workspace" eyebrow and server status in its foot; bottom tab bar on phones.
- Page head: tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right.
- List pattern: card/table toggle (`ViewPicker`), toolbar with search, group, sort, `FilterPopover` with removable chips, view state in the URL ("Share view").
- Iconify + lucide icon set; Mantine Table for lists; AG Grid only for large data (tasks, samplesheets).

**Changed for Spectio**
- Router: TanStack Router (depictio uses a pathname switch). Deep links matter here: runs, tasks and review gates are shared in chat and by webhooks.
- Data: TanStack Query + SSE for live runs.
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
| Params file | `-params-file` (JSON/YAML) | What a launch, relaunch and API call actually send; only non-default values stored. Prior art: `nf-core pipelines launch` |
| Modules | `modules.json` in the repository root | Module list and `git_sha` per release |
| Software versions | `pipeline_info/*software*versions.yml` (topic channels) | Software tab of a run; "last seen" versions on the workflow page |
| Run reports | `pipeline_info/execution_report*.html`, `execution_timeline*.html`, `execution_trace*.txt`, `params_*.json`; `**/multiqc_report.html` | Outputs & reports tab, viewers |
| Snakemake catalog | Snakemake Workflow Catalog `data.json`; `.snakemake-workflow-catalog.yml` | Catalog browsing for Snakemake |
| Snakemake config schema | `workflow/schemas/config.schema.yaml` (no UI hints) | Validation; labels, groups and pickers come from the optional `ui:` block in `spectio.yml` |
| Snakemake run data | `.snakemake/metadata`, benchmark TSVs, conda env files, wrapper tags | Task history, resource usage, software versions |

## 9. Open items
- Engine logos: plug in the official files already in depictio (`public/logos/workflows/`). nf-core is MIT and appears only next to genuine nf-core pipelines; Nextflow follows Seqera's brand manual (official files, never recoloured); Snakemake is MIT with no published guidelines. Mockups keep labelled placeholder tiles until this is done.
- `@depictio/ui` extraction: agree on the package boundary with the depictio codebase before Spectio's first UI release.
- Snakemake `ui:` block: draft its format alongside `spectio.yml`.

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
| Live checks and depictio | important stages and per-file checks during a run, no gate; editing watches in a lab overlay; a gate with an embedded preliminary depictio dashboard; the depictio dashboard with Spectio decisions joined ([`checking-scenarios.md`](checking-scenarios.md) §11, [`api-and-data-model.md`](api-and-data-model.md) §13.6) | RunLiveChecks (rnaseq), WorkflowWatches (rnaseq), ReviewDashboard (rnaseq), DepictioDecisions (rnaseq) |

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
| Embedded depictio frame with selection sync and a decision layer beside it | ReviewDashboard |

Every pattern has the states of §3: empty, loading, error, permission (view only), plus `n/a` for a check that cannot be computed.
