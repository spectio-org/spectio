# R9 · Prior art and landscape

**Step page:** [R9](../progress/W1/R9.md)

**Round:** R9 (prior art and landscape, again) · **Date:** 2026-10-26 · **Found by:** fact-checker and constraints-hunter, in parallel · **Status of the round:** waiting for triage (TRIAGE1)

**Sources.**
- **Branch and commit:** `autopilot/integration` at `3b209d3`. Line numbers ("l.") refer to that commit.
- **Round brief:** [`next-phase.md`](../playbooks/next-phase.md) R9.
- **Reviewer scopes:**
  - fact-checker: Seqera Platform and nf-tower, nf-shard, Sapporo and other WES servers, GA4GH WES / TES / TRS / DRS, WRROC, nf-prov;
  - constraints-hunter: panoptes, snkmt, FlowO, Galaxy, Arvados, Flyte, Prefect, Dagster, and what each means as a constraint or opportunity for Spectio.
- **Reviewer status:** both reviewers returned output. None failed.
- **The landscape itself** (per-tool entries, the GA4GH section, the neutral comparison table, every external source and commit) is in the dated research note [`landscape-2026-10-26.md`](../research/landscape-2026-10-26.md). This file holds only the findings: the spec changes the landscape implies. External code was read from shallow clones under `/tmp/w1-scratch/` (not kept). The main commits: snakemake `1c67a66`, nf-prov `8aa8280`, `snakemake-report-plugin-rocrate` `1989c5b`, `workflow-run-crate` `31518a5`, WES schemas `c3fb9fb`, Sapporo `14e6b5c`, Galaxy `fd43a3c`, flyte-sdk `0aabafa`, Prefect `21a1f02`, Dagster `c94186b`, and the FlowO 2.2.0 sdist.
- **Earlier rounds:** open findings in [R1](R1-consistency.md) (`SR-`), [R2](R2-open-validations.md) (`FC-001`–`FC-037`), [R4](R4-constraints.md) (`CH-`), [R5](R5-security.md) (`SEC-`), [R12](R12-ui-scenarios.md) (`UX-`) and [R8b](R8b-depictio-tooling.md) (`DEP-T-`) are cited, not repeated. Where an R9 finding adds new facts to an open one, it keeps a **Related** line and both should be triaged together.

**Merge method** (review-round skill, steps 3-4):
- **Input:** the fact-checker returned 13 findings (0 blockers, 2 majors, 11 minors) as FC-101 to FC-113. The constraints-hunter returned 10 findings (0 blockers, 5 majors, 5 minors) as FC-201 to FC-210. "Found by" gives each finding's original IDs.
- **IDs:** R2 already used FC-001 to FC-037, so this round continues the FC sequence at **FC-038** to keep every FC ID unique.
- **De-duplication inside R9:** four pairs describe the same problem and were merged:
  - the stale Snakemake monitoring landscape (FC-104 minor, FC-202 major) → FC-042, kept **major**;
  - the owner of the comparison page (FC-105, FC-210) → FC-047;
  - the prior art for interventions (FC-113, FC-209) → FC-053;
  - synthesis §3 out of date and Galaxy as an integration target (FC-107, FC-208) → FC-046. The WES-interop part of FC-208 went into FC-044.
- **Cited, not repeated:** two findings restate open findings from earlier rounds. Their new evidence is listed under "Cited, not repeated" and they are not counted:
  - FC-205 (engine-bridge transport) → SR-001, SR-017 (R1), CH-001, CH-005 (R4);
  - FC-207 (rules for copying third-party code) → CH-034 (R4).
- **Verification:** every quoted spec passage of every major was opened at `3b209d3` and confirmed. The external evidence of every major was re-read in the reviewers' clones or on PyPI for this merge:
  - FC-038: `rocrate_builder.py:294-305` declares RO-Crate 1.1 and wfrun 0.5; the plugin is listed at `workflow-run-crate` `docs/index.md:103`; PyPI returns no project.
  - FC-039: `--logger` is `nargs="+"` (`cli.py:1623-1628`); the API path iterates `settings.log_handler_settings` (`logging.py:648`).
  - FC-040: FlowO's `_create_filter` comment lists three `DefaultFilter` signatures within 9.x.
  - FC-041: nf-prov declares wfrun 0.1 (`WrrocRenderer.groovy:590-611`); Sapporo 0.5 (`ro_crate.py:49-50`); the WRROC 0.6 changelog says "not backward compatible".
  - FC-042: the current `monitoring.rst` describes logger plugins; the adoption note row cites `/en/master/`.
  - FC-043: `plugins/nextflow/README.md:90` (object store), `plugins/slurm/README.md:3` (SSH), `plugins/hitl/README.md:4-12` (conditions).

  All of them reproduced, so **0 findings were dropped**. Two reviewer disagreements were settled in the clones:
  - **Galaxy's WES version.** The fact-checker said Galaxy "implements all of WES 1.1"; the constraints-hunter said it declares 1.0.0. Both are true: `api/wes.py:64-151` serves every 1.1 route including `/tasks`, and `services/wes.py:412` declares `supported_wes_versions=["1.0.0"]`.
  - **Release dates.** Prefect 3.9.0 and Flyte were given different dates. PyPI says Prefect 3.9.0 is 2026-10-21 and `flyte` 2.12.1 is 2026-10-21; the research note uses those.
- **Severity changes:** FC-104 (minor) was merged into the constraints-hunter's major FC-202. FC-204 stays major although it overlaps CH-009 (R4): it adds the churn inside Snakemake 9.x and a concrete test gap, and its proposal conflicts with CH-009's (see Questions).
- **Ranking:** by severity, then by the number of documents the finding touches (specs, the roadmap page, the decision log, research notes).
- **Proposed new section numbers:** none. FC-207 proposed architecture §12, which R1 already gives to compatibility between components, and FC-205 proposed api §14, which SR-001 owns. Both are cited, not repeated.

Format: [`README.md`](README.md). Specs were not edited in this round.

## Summary

| Severity | Count |
|---|---|
| Blocker | 0 |
| Major | 6 |
| Minor | 11 |
| **Total** | **17** |
| Cited, not repeated (in R1 or R4) | 2 |
| Dropped (not reproducible) | 0 |

**What the round says.** The niche is still open, but it is narrower than the specs say. Monitoring for Snakemake and a catalogue with MCP access already exist in MIT tools (FlowO, panoptes). Flyte 2 started running Nextflow pipelines with pause-until-signal this month. What nobody offers is steering, meaning stop at a stage, review evidence, resume, for Snakemake and Nextflow on shared-file-system HPC under the user's own account. Two upstream changes in provenance affect the export design: a Snakemake RO-Crate exporter, and WRROC 0.6, which breaks compatibility.

**The five findings that matter most:**
1. **FC-039: Spectio's `--logger spectio` would silently switch off the user's own Snakemake monitor.** `--logger` takes a list, and an explicit value overrides the one in the profile. On the API path, only the handlers Spectio passes are used. Users of panoptes, snkmt or FlowO would lose them when Spectio launches or adopts their run. This is the Snakemake version of the coexistence that decision 0001 protects for Nextflow.
2. **FC-038: a Snakemake RO-Crate exporter exists.** It is `snakemake-report-plugin-rocrate`, in the `snakemake` organisation, writing a WRROC 0.5 Provenance Run Crate. The synthesis says "no native exporter was found" and plans to build one from the event store. The plugin is unreleased (0.1.0, not on PyPI), so it is a dependency to watch, not one to rely on yet.
3. **FC-041: export versions are not pinned, and WRROC 0.6 is not backward compatible.** nf-prov declares WRROC 0.1, Sapporo and the Snakemake plugin 0.5, all on RO-Crate 1.1. The current 0.6 needs RO-Crate 1.3. "Merge the engine crate with gate provenance" mixes profiles unless api §10 pins a version set.
4. **FC-043 and FC-042: the positioning claims are out of date.** "No project found targets exactly this" and "this audience has no incumbent" are now wrong on their face:
   - Flyte 2 + nf-flyte do stop, decide and resume around Nextflow runs;
   - FlowO has a Snakemake catalogue, users and MCP.

   The verdict still holds, but only when the differentiators are stated precisely.
5. **FC-040: Spectio cannot pin the Snakemake its logger runs in.** `DefaultFilter` changed signature three times within 9.x, and the interface added `needs_rulegraph` in 2.1.0. dev-env tests Snakemake 9.27.1 only. Related to CH-009 (R4).

## Findings table

| ID | Severity | Title | Documents touched | Found by (original IDs) |
|---|---|---|---|---|
| FC-038 | major | A Snakemake RO-Crate exporter exists; the synthesis says none was found | synthesis, cli-and-shared-libraries, depictio-ecosystem-reuse | FC-101 |
| FC-039 | major | The Snakemake adapter must add `spectio` to the user's loggers, not replace them | architecture-plugins-and-packaging, ui-spec, synthesis | FC-203 |
| FC-040 | major | Spectio cannot pin Snakemake: a supported version range and a contract test are needed | dev-environment-and-testing, architecture-plugins-and-packaging, synthesis | FC-204 |
| FC-041 | major | RO-Crate and WRROC versions are not pinned, and WRROC 0.6 breaks compatibility | api-and-data-model, synthesis | FC-102 |
| FC-042 | major | The Snakemake monitoring landscape has moved: logger plugins, an active panoptes, and FlowO | synthesis, adoption note | FC-104, FC-202 |
| FC-043 | major | Flyte 2 now runs nf-core pipelines with pause-until-signal; the "niche is open" verdict needs a precise boundary | synthesis, adoption note | FC-201 |
| FC-044 | minor | The WES facade does not say which dialect it speaks | api-and-data-model, synthesis, ui-spec | FC-108, FC-208 (part) |
| FC-045 | minor | nf-prov must be pinned per Nextflow version; Nextflow's lineage store is not considered | synthesis, architecture-plugins-and-packaging, dev-environment-and-testing | FC-103 |
| FC-046 | minor | Synthesis §3 "Standards and existing projects" is out of date; Galaxy is more than "a minimal WES" | synthesis, roadmap | FC-107, FC-208 |
| FC-047 | minor | No spec owns the "Spectio and other tools" page, and synthesis §7quater's comparison is out of date | documentation-system, synthesis | FC-105, FC-210 |
| FC-048 | minor | TRS: be a client before being a server | api-and-data-model, synthesis | FC-109 |
| FC-049 | minor | `drs://` can be passed through to Nextflow; the resolver is mainly for Snakemake | architecture-plugins-and-packaging, api-and-data-model | FC-110 |
| FC-050 | minor | The roadmap promises "TES interfaces", but TES is reached only through the engines | roadmap, schedulers-and-monitoring | FC-111 |
| FC-051 | minor | "Partial compatibility with the Seqera API" contradicts decision 0001 | synthesis, decision log | FC-112 |
| FC-052 | minor | "Prefect makes the same choice" hides that Prefect keeps one migration tree per dialect | architecture-plugins-and-packaging, admin-and-operations | FC-206 |
| FC-053 | minor | The prior art for gates is stale, misses the two closest designs and mixes two Prefect mechanisms | synthesis | FC-113, FC-209 |
| FC-054 | minor | How Seqera Platform reaches a cluster is misdescribed | synthesis | FC-106 |

## Findings

### FC-038 · major · A Snakemake RO-Crate exporter exists; the synthesis says none was found

- **Where:** synthesis.md §7quinquies "RO-Crate compatibility" (l.315); cli-and-shared-libraries.md §1 (l.33) and the `bioplatform-runinfo` row (l.133); depictio-ecosystem-reuse.md (l.121). The last three list only Nextflow and Galaxy crate sniffers.
- **Evidence:**
  - "For Snakemake no native exporter was found, so Spectio builds the crate from its own event store." (synthesis l.315)
  - `snakemake/snakemake-report-plugin-rocrate` at `1989c5b` (2026-10-23, MIT, `pyproject.toml` version 0.1.0). Its README says it creates "a Provenance Run Crate … after a workflow run". `rocrate_builder.py:294-305` declares RO-Crate 1.1 and wfrun process, workflow and provenance 0.5.
  - It is listed as the Snakemake implementation in `ResearchObject/workflow-run-crate` `docs/index.md:103` (`31518a5`).
  - It is **not on PyPI**: the PyPI JSON API returned no project on 2026-10-26.
  - A second exporter, `snakemake-report-plugin-fairscape` 0.1.0 (PyPI, Apache-2.0, 2026-08-18), writes a FAIRSCAPE EVI RO-Crate, not a WRROC.
- **Problem:**
  - The specs plan provenance parity between the engines around a gap that is closing upstream. Spectio would re-implement step-level Snakemake provenance that the Snakemake organisation now maintains.
  - The sniffer lists also miss the crates these plugins write, so observed or imported Snakemake runs with a crate would not be recognised.
- **Proposal:**
  - synthesis §7quinquies: name `snakemake-report-plugin-rocrate` as the Snakemake counterpart of nf-prov. When it is installed, Spectio enables it (`--reporter rocrate --report-rocrate-metadata-only`; the flag names are **[to be validated]**) and merges its output with the gate provenance. The event-store builder stays as the fallback, and stays the primary path until the plugin is released.
  - Mark the plugin "unreleased, 0.1.0" **[to be validated before relying on it]**.
  - Add a Snakemake run-crate sniffer to `bioplatform-runinfo` (cli-and-shared-libraries.md) and to depictio-ecosystem-reuse.md.
- **Related:** FC-041 (versions to pin when merging), CH-035 (R4, crate size), SEC-110 (R5, validating imported crates).
- **Found by:** fact-checker (FC-101)
- **Status:** open

### FC-039 · major · The Snakemake adapter must add `spectio` to the user's loggers, not replace them

- **Where:** architecture-plugins-and-packaging.md §2 (l.64: the `spectio.engine` plugin "generates the config that enables them"); ui-spec.md §6 (l.197: "Snakemake: `--logger spectio`"); synthesis.md §2 (driven runs through `SnakemakeApi`, l.29) and §7quater block 2 (l.339, "configures the plugins automatically (… `--logger`)").
- **Evidence:**
  - `--logger` is `nargs="+"`, "Specify one or more custom loggers" (snakemake `1c67a66`, `src/snakemake/cli.py:1623-1628`). The current docs say "Multiple logger plugins can be used simultaneously" (`docs/executing/monitoring.rst`).
  - Profiles only set "default command line arguments" (`cli.py:1916`, configargparse). So an explicit `--logger spectio` replaces a profile's `logger: [snkmt]` **[to be validated: how configargparse resolves lists]**.
  - With `nargs="+"` and the default `store` action, `--logger a --logger b` may keep only `b`, despite the docs **[to be validated]**.
  - On the API path, handlers come only from `settings.log_handler_settings` (`src/snakemake/logging.py:648`). A profile that Spectio does not read is ignored there.
  - Decision 0001: Spectio "is meant to sit next to Seqera Platform, not to replace it."
  - Twelve logger plugins are in the catalogue, among them panoptes, snkmt, FlowO and prometheus ([research note](../research/landscape-2026-10-26.md) §3).
- **Problem:** users who already run panoptes, snkmt, FlowO or prometheus would silently lose their monitor when Spectio launches or adopts their run. This is the Snakemake version of the coexistence that decision 0001 protects for Nextflow.
- **Proposal:**
  - architecture §2 (or §3.6, the engine plugin contract): the Snakemake adapter reads the effective loggers (CLI, `--profile`, `--workflow-profile`, `workflow/profiles/default`), appends `spectio`, and passes their settings through, on both the CLI and the API path. It emits one `--logger <existing…> spectio`, never a second `--logger`.
  - ui-spec §6: show `--logger <existing> spectio`.
- **Likelihood · impact:** high with any user who already has a monitor · medium (lost monitoring, support load).
- **Cheapest test** (15 min, R9 spike 1): on `smk-toy`, use a profile with `logger: [snkmt]` and run `--logger spectio`; then `--logger snkmt --logger spectio`; then the API path with one handler. Check whether the snkmt database receives rows each time.
- **Related:** CH-009 (R4) on CLI vs API process model; SR-006 (R1) on the enabling commands.
- **Found by:** constraints-hunter (FC-203)
- **Status:** open

### FC-040 · major · Spectio cannot pin Snakemake: a supported version range and a contract test are needed

- **Where:** dev-environment-and-testing.md §1 (l.48: Snakemake "9.x"), §5 (l.133: matrix "snakemake 9"), §6 (tiers), §11 (l.358: CI on Snakemake 9.27.1 only); architecture-plugins-and-packaging.md §2 and §4 (the logger plugin's dependency range); synthesis.md §2 (l.28: "read defensively and pin the version"), §10 risk 4.
- **Evidence:**
  - FlowO has to probe `DefaultFilter.__init__` because "snakemake <=9.2.x: (quiet, debug_dag, dryrun) / >=9.10.0: … printshellcmds / >=9.23: … verbose…" (FlowO 2.2.0 sdist, `plugin/client/log_handler.py:156-176`).
  - `snakemake-interface-logger-plugins` 2.1.0 (2026-05-20) adds `needs_rulegraph`, and its `tests.py:114-116` asserts that property.
  - snkmt pins `snakemake-interface-logger-plugins<3,>=1.2.0` (PyPI `requires_dist`).
  - Nextflow, by contrast, gets two tested versions (dev-env §1, §11: 25.10.9 and 26.10.3).
- **Problem:**
  - Observed and adopted runs use whatever Snakemake the lab has. "Pin the version" works only for runs Spectio launches in its own environment.
  - No spec states the minimum supported Snakemake, the interface major, or a test against the oldest and the newest version.
  - A broken or silent logger means no events, and so no gates.
- **Proposal:**
  - dev-env §1: a Snakemake row with two tested versions, like Nextflow: the minimum supported and the latest.
  - dev-env §6: run the interface's own `snakemake_interface_logger_plugins.tests` suite plus the recorded-event replay on both versions.
  - architecture §4: give `snakemake-logger-plugin-spectio` a `snakemake-interface-logger-plugins` range of one major. The runner warns when the Snakemake it finds is outside the range.
- **Likelihood · impact:** high (three signature changes within 9.x) · high (no events means no gates).
- **Cheapest test** (half a day, R9 spike 2): a `uv` matrix that installs Snakemake 9.2, 9.10, 9.23 and 9.27.1, loads a stub logger with `has_filter=True`, and runs `smk-toy`. Merge it with CH-009's test.
- **Related:** CH-009 (R4) proposes "Snakemake ≥ 9.0 and logger interface 1.x and 2.x, tested in CI". This finding proposes one interface major. Thomas picks one (Questions, item 5); triage both together.
- **Found by:** constraints-hunter (FC-204)
- **Status:** open

### FC-041 · major · RO-Crate and WRROC versions are not pinned, and WRROC 0.6 breaks compatibility

- **Where:** api-and-data-model.md §10 (RO-Crate row, l.266); synthesis.md §7quinquies (l.313: "Target the Workflow Run Crate profile, and the Provenance Run Crate"; l.315: "enable it … and merge its output with the gate provenance").
- **Evidence:**
  - WRROC `docs/profiles/changelog.md` (`31518a5`): "0.6 (2026-09-07) … Workflow Run Crate and Provenance Run Crate are not backward compatible with RO-Crate 1.1/Workflow RO-Crate 1.0". Its compatibility table maps RO-Crate 1.1 to WRROC 0.1–0.5 and RO-Crate 1.3 to 0.6.
  - The engine exporters emit different versions:
    - nf-prov 1.8.0: RO-Crate 1.1 + wfrun **0.1** (`WrrocRenderer.groovy:590-611`);
    - Sapporo 2.4.0: RO-Crate 1.1 + **0.5** (`sapporo/ro_crate.py:47-50`);
    - the Snakemake plugin: RO-Crate 1.1 + **0.5** (`rocrate_builder.py:294-305`).
  - api §10 l.266 names the profiles without versions.
- **Problem:** "merge nf-prov output with gate provenance" produces a crate that mixes profile declarations. If Spectio follows the current 0.6, the `input` and `output` IRIs differ from those in the engine-produced parts, and readers such as LabID and WorkflowHub may reject or misread the crate.
- **Proposal:**
  - api §10 pins the export target for 0.x to RO-Crate 1.1 + WRROC 0.5, which is what the engine exporters emit today, and records a planned move to 0.6.
  - Merging rewrites `conformsTo` to the pinned versions.
  - CI validates every exported crate with `crs4/rocrate-validator`, as the Snakemake plugin does.
  - The Provenance profile is claimed only when per-step `HowToStep` / `ControlAction` entities are present. Sapporo's `docs/ro-crate.md` explains why it does not claim that profile.
- **Related:** CH-035 (R4, crate size), DL-107 (R8, depictio's provenance file and WRROC).
- **Found by:** fact-checker (FC-102)
- **Status:** open

### FC-042 · major · The Snakemake monitoring landscape has moved: logger plugins, an active panoptes, and FlowO

- **Where:** synthesis.md §2 (l.30, "Existing tools … Mature for tracking, nothing for steering") and §7quater "Comparison" (l.344, the "Tower / Panoptes (plugin mode) · Registration: none" row); docs/research/adoption-and-positioning-2026-10-26.md §1 (row 5, l.20) and §2.
- **Evidence:**
  - Adoption note l.20: "Snakemake's own docs list a single monitoring option: panoptes, 'under development', through `--wms-monitor`" … "This audience has no incumbent". It cites `/en/master/`, which is a frozen Snakemake 6.1.0 build (`build_date` 2021-04-07).
  - The current docs (`docs/executing/monitoring.rst:7-26` at `1c67a66`, stable 9.27.1) describe logger plugins and point to the catalogue, which lists 12 loggers ([catalogue](https://snakemake.github.io/snakemake-plugin-catalog/)).
  - panoptes is active again: 21 commits in 2026-05, 14 in 2026-07, `panoptes-ui` 1.6.2 on 2026-10-24. Its plugin README says it replaces "the legacy `--wms-monitor` integration that was removed in Snakemake 9" (`2062666`).
  - FlowO 2.2.0 (MIT) offers SSE monitoring, per-run DAG, jobs and timeline views, a versioned workflow "Catalog", users (`fastapi-users`) and an MCP endpoint (`fastapi-mcp`) (PyPI description, [FlowO docs](https://flowo-docs.pages.dev/)).
- **Problem:**
  - The public positioning and the comparison page would repeat a wrong fact.
  - Monitoring, a catalogue and MCP access, which Spectio plans for Snakemake, already exist in MIT tools. The §7quater row "Registration: none" is wrong for FlowO.
  - Steering is still unclaimed: no Snakemake tool read here launches, stops at a stage, gates or relaunches.
- **Proposal:**
  - synthesis §2 and §7quater: update the tool list with the versions and dates in the [research note](../research/landscape-2026-10-26.md) §3, and add a FlowO row (registration: yes, catalogue; remote launch: no; steering: none found). Or link to the comparison page (FC-047) instead of keeping a table.
  - The research note supersedes adoption §1 row 5 (research notes are not rewritten). Wherever the positioning is restated, say "no gate-and-steer tool for Snakemake" rather than "no incumbent", and name FlowO as the closest neighbour.
  - Consider contacting the FlowO maintainers about logger-event conventions, and offering the Snakemake docs a PR that replaces the stale `--wms-monitor` page with a logger-plugin list (it fits adoption §3).
- **Likelihood · impact:** certain that it is stale · medium (messaging, and which features feel new).
- **Cheapest test:** install FlowO from its Compose file for 30 minutes to confirm it has no steering, since only the sdist and docs were read.
- **Found by:** fact-checker (FC-104), constraints-hunter (FC-202)
- **Status:** open

### FC-043 · major · Flyte 2 now runs nf-core pipelines with pause-until-signal; the "niche is open" verdict needs a precise boundary

- **Where:** synthesis.md §1 (verdict, l.7: "No project found targets exactly this (non-exhaustive search)") and §3 (standards and projects table, l.115-127); docs/research/adoption-and-positioning-2026-10-26.md (short answer: "what nobody offers today").
- **Evidence:**
  - `flyteplugins-nextflow`: "Run Nextflow pipelines on Flyte … Aborting the Flyte run aborts the pipeline and its running tasks" (flyte-sdk `0aabafa`, `plugins/nextflow/README.md:1-12`). First PyPI release 2026-10-16.
  - `nf-flyte` 0.2.1 (Apache-2.0, 2026-10-23) runs each Nextflow task as a Flyte child action.
  - `flyte.new_condition` pauses "a run until they are signaled from the Flyte UI, the CLI … or programmatically" (`plugins/hitl/README.md:4-12`).
  - The limits of that path:
    - "On a cluster, the work directory must be on an object store Flyte can read (S3, GCS or Azure)" (`plugins/nextflow/README.md:90`);
    - Slurm is reached "over SSH" with a configured key, and needs Pyxis/Enroot or Apptainer on the nodes (`plugins/slurm/README.md:3,22-31`).
- **Problem:**
  - A Flyte workflow `run_nextflow(stage 1) → condition → run_nextflow(stage 2, resume)` is Spectio's "stop after a stage, decide, resume", built from Apache-2.0 parts released this month.
  - The positioning still holds, but only when it is stated precisely:
    - shared POSIX file systems, not object stores;
    - the runner runs under the user's account, not with a shared SSH key;
    - Snakemake is supported;
    - gates are item-level QC reviews with evidence, not a typed value.
  - Today the docs say nobody offers this, and that is now false on its face.
- **Proposal:**
  - Add a Flyte 2 row to synthesis §3 (see FC-046).
  - Restate the synthesis §1 verdict as the four differentiators above.
  - Put the adoption update in a new dated research note when the positioning is next revised (old notes are not rewritten). The [landscape note](../research/landscape-2026-10-26.md) already records the facts.
  - Re-check Flyte, nf-flyte and Seqera every quarter in a new landscape note.
- **Likelihood · impact:** high that a reviewer or design partner raises it · medium on positioning, none on the architecture.
- **Cheapest test** (1 h of code reading, R9 spike 4): can `flyteplugins-nextflow` use a POSIX `work_dir` on a cluster with the Slurm connector? If yes, the differentiators narrow to Snakemake, the user's identity and item-level review.
- **Found by:** constraints-hunter (FC-201)
- **Status:** open

### FC-044 · minor · The WES facade does not say which dialect it speaks

- **Where:** synthesis.md §7quinquies Surfaces table (l.297: "standard clients (Sapporo-style, workflow portals)") and §7quater (l.350: "a Sapporo or WES client can launch and track runs"); api-and-data-model.md §2.B and §10 (l.264); ui-spec.md §4.1 (l.72, landing "works-with … GA4GH WES").
- **Evidence:**
  - Sapporo 2.x is not strictly WES 1.1 (`docs/wes-compatibility.md`): `default_workflow_engine_parameters` becomes a dict keyed by engine (row 1-1), `RunLog.outputs` a list of `FileObject` (row 1-2), `workflow_engine` is required (row 2-2), and `/tasks` returns 400 (row 4-1).
  - sapporo-web, Sapporo's UI client, was last committed on 2022-09-13.
  - Galaxy serves every WES 1.1 route but declares `supported_wes_versions=["1.0.0"]` (`services/wes.py:412`, `fd43a3c`) and uses "`x-api-key` (the WES spec's bearer-token scheme is not used)" (`doc/source/dev/ga4gh_wes.md:77`).
  - `NFL` and `SMK` are valid `workflow_type` values: the TRS `DescriptorType` enum defines them (`openapi/openapi.yaml:729-739`, `d40e63b`) and Sapporo's `service_info.json` uses them. This resolves the **[to be validated]** in SR-010.
- **Problem:** a strict WES 1.1 facade is not a drop-in for Sapporo clients, and a Sapporo-shaped one is not WES 1.1. Implementers cannot tell which to build. Neither existing server is a conformance reference for auth.
- **Proposal:**
  - api §10 declares strict WES 1.1.0: `workflow_type` `NFL` / `SMK`, `workflow_engine` `nextflow` or `snakemake`, `/tasks` served from Spectio's task table, bearer tokens.
  - Sapporo 2.x compatibility is a non-goal unless a partner asks for it. Drop "Sapporo-style" and "a Sapporo … client" from synthesis l.297 and l.350.
  - Galaxy (MIT) and Sapporo (Apache-2.0) are references for the models, not conformance targets.
  - When the facade ships stays with SR-010. The landing strip shows WES only once it ships (as SR-010 already proposes).
- **Related:** SR-010 (stage and under-specification), SR-016 (state mapping) in R1.
- **Found by:** fact-checker (FC-108); constraints-hunter (WES part of FC-208)
- **Status:** open

### FC-045 · minor · nf-prov must be pinned per Nextflow version; Nextflow's lineage store is not considered

- **Where:** synthesis.md §7quinquies (l.315, nf-prov bullet); architecture-plugins-and-packaging.md §3.6 (l.176: `collect(run_dir)` "post-hoc metadata (.snakemake, nf-prov)"); dev-environment-and-testing.md §11 (CI matrix).
- **Evidence:**
  - nf-prov README requirements (`8aa8280`): "1.8.x · 26.10 | 1.7.x · 25.10 | 1.6.x · 25.10". `prov.directory` is new in 1.8.0.
  - Nextflow `docs/tutorials/data-lineage.mdx` (`193a4c2`, 26.10.3): "Data lineage is an experimental feature added in Nextflow 25.04", enabled with `lineage.enabled = true`, data model `v1beta1`.
- **Problem:** Spectio supports Nextflow 25.10 and 26.10. A generated config that always asks for the latest nf-prov breaks on 25.10. The lineage store, which records runs, tasks and outputs with LIDs, is a second provenance source that the collector does not consider.
- **Proposal:**
  - synthesis §7quinquies: the generated config pins nf-prov by Nextflow version (1.7.x on 25.10, 1.8.x on 26.10), and the CI matrix (dev-env §11) covers both.
  - architecture §3.6: Nextflow lineage as an optional, experimental input to the post-hoc collector, **[to be validated]** in a spike.
- **Found by:** fact-checker (FC-103)
- **Status:** open

### FC-046 · minor · Synthesis §3 "Standards and existing projects" is out of date; Galaxy is more than "a minimal WES"

- **Where:** synthesis.md §3 table (l.115-127); docs/roadmap/index.md (ideas).
- **Evidence:**
  - "nf-shard … Maturity to be checked" (l.124): last commit `f40ce84` (2024-09-19), last tag 0.1.23 (2024-07-14).
  - "Galaxy as an example of a minimal WES" (l.123): Galaxy serves every WES route including tasks (`api/wes.py:64-151`), declared as WES 1.0.0, ships DRS and a TRS consumer in `release_26.1` (`5a58507`), and is MIT from 2026-02-25 (`LICENSE.txt`). Its `PauseModule` ("Pause for dataset review", `workflow/modules.py:2041-2110`) records approve or cancel per invocation step.
  - Funnel moved to `calypr/funnel` (v0.12.2, MIT). TESK's last release is v0.2 (2018).
  - Sapporo 2.4.0 adds WRROC 0.5, ep3 and StreamFlow, and deviates from WES 1.1.
  - Flyte 2 is missing (FC-043).
- **Problem:** the table steers reuse decisions with stale facts. Galaxy's MIT relicensing makes its WES models directly reusable, and Galaxy is the only engine read here with a native human review step.
- **Proposal:**
  - Update the rows and link to the [research note](../research/landscape-2026-10-26.md). Add: "Galaxy WES (MIT): reference for the facade's pydantic models"; "Sapporo `ro_crate.py` and compatibility matrix: reference"; "nf-shard: unmaintained since 2024"; a Flyte 2 row.
  - Record a later `spectio.engine` "galaxy" adapter, mapping `PauseModule` onto Spectio gates, under the roadmap's ideas. It stays out of the MVP.
- **Found by:** fact-checker (FC-107), constraints-hunter (FC-208)
- **Status:** open

### FC-047 · minor · No spec owns the "Spectio and other tools" page, and synthesis §7quater's comparison is out of date

- **Where:** documentation-system.md §1 (site structure table; the tabs are Home, Installation, Usage, Features, API, Developer, Roadmap and Changelog); synthesis.md §7quater "Comparison" (l.342-350); adoption note §2 (l.33) and §5 (l.90).
- **Evidence:**
  - Adoption §2: "use a neutral, factual table in the docs ('Spectio and other tools'), including Seqera, nf-shard, panoptes, Galaxy and Arvados"; §5: "A short comparison page, factual and fair".
  - Synthesis §7quater has a four-row table with the errors listed in FC-042, FC-054 and the [research note](../research/landscape-2026-10-26.md) §12 (Sapporo HPC).
- **Problem:** without an owner, the table will be written twice and drift. Its facts age within weeks: FlowO, nf-flyte and Flyte's Slurm plugin all shipped in 2026, two of them this month.
- **Proposal:**
  - documentation-system §1: add a "Spectio and other tools" page under Features. Its source of truth is the latest dated landscape research note (starting with §10 of [`landscape-2026-10-26.md`](../research/landscape-2026-10-26.md)). Every row has a "checked on" date and a link. Neutral wording, no pricing.
  - Re-check the page at each release stage (dev-env §14) and every quarter.
  - synthesis §7quater keeps only Spectio's own modes and links to that page.
- **Found by:** fact-checker (FC-105), constraints-hunter (FC-210)
- **Status:** open

### FC-048 · minor · TRS: be a client before being a server

- **Where:** api-and-data-model.md §10 (l.265: "GA4GH TRS, DRS · phase 2: catalogue as TRS"); synthesis.md §7quater block 1 (l.338: "Can later be exposed as GA4GH TRS").
- **Evidence:**
  - TRS `openapi/openapi.yaml:729-739` (`d40e63b`): `DescriptorType` includes `NFL` and `SMK`.
  - README:34-37: "TRS has largely reached a stable state … actively used by Galaxy, WorkflowHub.eu, … Sapporo".
  - The latest tag is 2.0.2 (2025-09-02); that tag's file says `version: 2.1.0`.
- **Problem:** the specs consider only exposing Spectio's catalogue. The more useful early direction is registering workflows from existing TRS registries (WorkflowHub, Dockstore), which fits the RO-Crate import already planned.
- **Proposal:** api §10 adds "TRS client: register a workflow from a TRS URL (NFL/SMK)" next to the RO-Crate import. The TRS server stays for later. Whether WorkflowHub's TRS endpoint serves Nextflow and Snakemake entries is **[to be validated]**.
- **Related:** SEC-110, SEC-118 (R5): imports and outbound HTTP need validation and an SSRF policy.
- **Found by:** fact-checker (FC-109)
- **Status:** open

### FC-049 · minor · `drs://` can be passed through to Nextflow; the resolver is mainly for Snakemake

- **Where:** architecture-plugins-and-packaging.md §2 (l.43, input resolver examples including `drs://`); api-and-data-model.md §0 (l.12) and §3 (l.62).
- **Evidence:**
  - `nextflow-io/nf-ga4gh` 1.5.0 (2026-07-02), README:120-153: "`drs://` URIs can be used directly as process inputs … Under the TES executor, the `drs://` URI is passed straight through … The DRS filesystem is read-only".
  - The Snakemake storage plugin catalogue (2026-10-26) has no DRS plugin.
  - DRS is at 1.5.0 (`fe25c39`).
- **Problem:** staging DRS objects through Spectio's resolver duplicates engine-native resolution for Nextflow and wastes storage. It is still needed for Snakemake.
- **Proposal:** the resolver section (architecture §2, api §3) says that for Nextflow runs `drs://` is passed through to `nf-ga4gh`, with the resolver used only for pre-flight checks and checksums. For Snakemake, the resolver stages the object.
- **Found by:** fact-checker (FC-110)
- **Status:** open

### FC-050 · minor · The roadmap promises "TES interfaces", but TES is reached only through the engines

- **Where:** docs/roadmap/index.md (l.42: "GA4GH WES and TES interfaces"); schedulers-and-monitoring.md §5 (no TES environment kind). Compare the decision log 2026-10-26 ("TES as a possible later execution target") and synthesis §3.
- **Evidence:**
  - Nextflow's TES executor is in `nf-ga4gh` 1.5.0 (active).
  - `snakemake-executor-plugin-tes`: last commit 2024-09-07, v0.1.3.
  - TES is at 1.1.0, unchanged since 2022.
  - Servers: Funnel v0.12.2 (Slurm, PBS, Grid Engine, HTCondor, Kubernetes); TESK (Kubernetes, last release 2018).
- **Problem:** "TES interface" reads as Spectio exposing TES, which no spec plans. The Snakemake side of a TES target relies on a stale plugin.
- **Proposal:**
  - Roadmap: "WES facade; TES backends through the engines' executors".
  - schedulers §5: a later "TES environment" entry (executor config, plus task state through TES `GET /tasks`), with the Snakemake plugin's staleness as a risk.
- **Related:** SR-010 (R1) also moves the roadmap's WES item to a stage; apply both in one edit.
- **Found by:** fact-checker (FC-111)
- **Status:** open

### FC-051 · minor · "Partial compatibility with the Seqera API" contradicts decision 0001

- **Where:** synthesis.md §7bis item 6 (l.282); decision log (l.36: "Partial compatibility with the Seqera API (for `tw`, seqerakit): later, after a legal check").
- **Evidence:**
  - §7bis.6: "Partial compatibility with the Seqera API (to reuse `tw` or seqerakit): to be studied later".
  - [Decision 0001](../decisions/0001-nextflow-through-nf-spectio.md): "Spectio is meant to sit next to Seqera Platform, not to replace it".
  - Adoption §2: do not present Spectio as a "Tower alternative".
  - `tw` is Apache-2.0, v0.42.0 (2026-10-08).
- **Problem:** emulating the Seqera API so that Seqera's own clients drive Spectio is the replacement positioning that decision 0001 rejected. The older log entry still lists it as planned.
- **Proposal:** mark §7bis item 6 "not planned (decision 0001)", and record that in a new dated log entry (the old entry is not edited). Thomas confirms (Questions, item 6).
- **Found by:** fact-checker (FC-112)
- **Status:** open

### FC-052 · minor · "Prefect makes the same choice" hides that Prefect keeps one migration tree per dialect

- **Where:** architecture-plugins-and-packaging.md §2 (l.68: "Airflow, Prefect and MLflow make the same choice: one SQLAlchemy URL, a short list of supported backends"); admin-and-operations.md §4.3 (l.293: "Alembic with `render_as_batch` (SQLite)").
- **Evidence:** Prefect keeps `src/prefect/server/database/_migrations/versions/sqlite/` (115 entries) next to `…/postgresql/` (120 entries) (`21a1f02`; counts re-read for this merge).
- **Problem:** the spec cites Prefect as support for one portable schema, while Prefect maintains two migration histories. Choosing one tree or two changes how every migration PR is written. DEP-T-012 (R8b) covers testing on both dialects, not the structure of the migrations.
- **Proposal:**
  - admin §4.3: state "one Alembic tree, with dialect branches inside a revision only where needed", or two trees, and give the reason.
  - architecture §2: say what the cited projects actually share (one URL, a closed list of backends).
- **Likelihood · impact:** medium · low-medium (rework of early migrations).
- **Cheapest test** (2 h, R9 spike 7): write the first three revisions of the planned schema (a JSON column, a partial index, an `ALTER` of a constraint) in one tree and run them on SQLite and Postgres 18.
- **Related:** DEP-T-012 (R8b), CH-023 (R4, migration time).
- **Found by:** constraints-hunter (FC-206)
- **Status:** open

### FC-053 · minor · The prior art for gates is stale, misses the two closest designs and mixes two Prefect mechanisms

- **Where:** synthesis.md §5 (l.151: "Prior art: Airflow 3.1 (approval operators), Argo (`suspend`), Prefect 3 (pause with input)") and §5bis (l.197: "Prior art: Temporal …, Airflow 3.1 …, Argo").
- **Evidence:**
  - **Flyte 2:** `flyte.new_condition(name, prompt, data_type)` pauses a run until an external signal, with a timeout and a webhook that POSTs a `{callback_uri}` (`src/flyte/_condition.py:15-69`, `0aabafa`). An MCP tool lists "the points where it is paused for external input" (`src/flyte/ai/mcp/_tools.py:1133`). Flyte 1 had `approve`, `wait_for_input` and `sleep` (`flytekit/core/gate.py:136-166`).
  - **Galaxy:** the "Pause for dataset review" step (`lib/galaxy/workflow/modules.py:2041-2110`).
  - **Prefect has two mechanisms:** `pause_flow_run` "block[s] execution until resumed", with `timeout: int = 3600`, after which the flow fails (`flow_runs.py:166-200`); `suspend_flow_run` exits and "will be rescheduled", and needs persisted results (`flow_runs.py:505-511`).
  - **Dagster:** `blocking` asset checks, automatic, no human (`asset_check_spec.py:77-82`).
- **Problem:**
  - Flyte ships the combination Spectio specifies (typed intervention, outgoing webhook with a signal URL, MCP listing), and Galaxy is the bioinformatics precedent for a review gate. Neither is used as a design check.
  - Prefect's `pause` is Spectio's rejected "short wait": it keeps the process alive and holds an HPC slot or a login-node process. Prefect's `suspend` is Spectio's chosen "stop and relaunch with cache". Calling both "pause with input" hides the very trade-off §5bis makes.
- **Proposal:**
  - Replace the two prior-art lines with one table (Prefect suspend, Prefect pause, Flyte condition, Galaxy pause, Dagster blocking check): blocking or suspending, who decides, typed input, timeout default.
  - Compare Flyte's callback-URI pattern with `POST /api/v1/gates/{id}/signals` (api §5). The signal semantics themselves are open as UX-110 (R12) and are not repeated here; Prefect's fail-after-timeout default is evidence for its `timeout` and `action` vocabulary.
- **Related:** UX-110, UX-103 (R12).
- **Found by:** fact-checker (FC-113), constraints-hunter (FC-209)
- **Status:** open

### FC-054 · minor · How Seqera Platform reaches a cluster is misdescribed

- **Where:** synthesis.md §7quater block 2 (l.339: "same principle as Seqera's Tower Agent (outgoing WebSocket, user's account, Slurm/LSF/PBS/SGE)") and the Comparison row (l.346: "Remote launch: yes, Tower Agent").
- **Evidence:** [Seqera HPC docs](https://docs.seqera.io/platform-cloud/compute-envs/hpc): "Seqera requires SSH access to your HPC cluster to run pipelines"; Tower Agent is used for clusters without direct SSH access. The supported schedulers are PBS Pro, Grid Engine, LSF, Moab and Slurm.
- **Problem:** this misstates a competitor in a document that feeds the public comparison.
- **Proposal:** write "SSH by default, Tower Agent where SSH is not allowed; Slurm, LSF, PBS Pro, Grid Engine, Moab". Mark "outgoing WebSocket" **[to be validated]**. If FC-047 is accepted, the comparison row moves to the docs page.
- **Found by:** fact-checker (FC-106)
- **Status:** open

## Cited, not repeated

These reviewer findings restate open findings. Their new evidence should be read when those findings are triaged and applied. They are not counted above.

- **FC-205 (constraints-hunter): no spec owns the engine-bridge transport** → SR-001 (ingest contract, api §14) and SR-017 (bridge behaviour when the server is unreachable) in R1; CH-001 (spool in the launch directory, forwarded by the runner) and CH-005 (traffic budget, spool limits) in R4. New evidence:
  - panoptes 0.3.0 makes one synchronous `session.post(..., timeout=10.0)` per event and only logs a warning on failure (`log_handler.py:115-130`, `2062666`).
  - FlowO 2.2.0 does the same: `self._client.post(url, json=payload)`, `timeout=10.0`, no retry and no spool (`log_handler.py:218-251`).
  - Both run in Snakemake's `QueueListener` (synthesis §2bis), so with the server down each event can delay the following ones by up to 10 s.
  - snkmt disables SQLite WAL because "the database may live on a network filesystem (NFS/Lustre/GPFS)", and needed `busy_timeout` after "database is locked" errors (`log_handler.py:83-95`, `5b94373`). This supports an append-only JSONL spool, not SQLite, on shared file systems.
  - **Conflict to settle when applying:** the reviewer proposed a spool on node-local `$TMPDIR`. CH-001 puts the spool in the launch directory so that the runner on the login node can forward it. A node-local spool is invisible to the runner, so CH-001's placement should win where compute nodes have no egress.
  - The reviewer's 2-hour test (a blackholed ingest for 60 s during a 500-job `smk-toy` run, a synchronous handler against a batched JSONL spool) is listed below as spike 3.
- **FC-207 (constraints-hunter): no rule for copying third-party code** → CH-034 (R4: licence allow-list, CI scan, `THIRD_PARTY_NOTICES`, a record of what was copied). New evidence:
  - Arvados: "everything else is licensed AGPL-3.0" except `sdk/` (Apache-2.0) (`COPYING`, `78a35c3`). Its server code must never be copied.
  - Galaxy is MIT only "from 2026-02-25 onwards" (`LICENSE.txt`, `fd43a3c`); older copies carry the previous licence (AFL-3.0 **[to be validated]**).
  - Flyte, Prefect and Dagster are Apache-2.0: copied code keeps its NOTICE and attribution. panoptes, snkmt and FlowO are MIT.
  - Add to CH-034's proposal: "pin the source commit and its licence for any copied code", and a deny-list for copying GPL, AGPL and LGPL code into the core. The reviewer's proposed architecture §12 is taken by R1 (compatibility). Use CH-034's architecture §7.4.

**Evidence for other open findings** (from the constraints-hunter):
- **UX-103** (R12, check states and how each counts towards the gate): Dagster lets downstream steps run when a blocking check emits no result ("downstream execution proceeds and a warning is logged", `asset_check_spec.py:80-82`). The reviewer recommends that a `block` check with `error` or no result keeps the gate closed (fail closed), stated in checking-scenarios §4.
- **DEP-T-012** (R8b, SQLite-only tests): Prefect's two migration trees (FC-052) support running migrations on both dialects.
- **UX-110** (R12, gates that wait for a signal): Prefect's default timeout (3600 s, then the flow fails) and Flyte's condition timeout and webhook (`_condition.py:68-69`) are prior art for the `timeout` and `action` vocabulary.

## Questions for Thomas

1. **Positioning (FC-043, FC-042).** Accept restating the verdict as four differentiators: shared POSIX file systems, the user's own account, Snakemake, item-level QC gates with evidence? And may Spectio contact the FlowO maintainers about logger-event conventions, and offer the Snakemake docs a PR for the stale monitoring page?
2. **Snakemake provenance (FC-038).** Treat `snakemake-report-plugin-rocrate` as the primary Snakemake exporter once it is on PyPI, with Spectio's own builder as the fallback until then? Or keep Spectio's builder as the primary path?
3. **Export versions (FC-041).** Pin RO-Crate 1.1 + WRROC 0.5 for 0.x (what every engine exporter emits today) and move to 0.6 later? Or target RO-Crate 1.3 + WRROC 0.6 now and rewrite engine crates on merge?
4. **WES dialect (FC-044).** Strict WES 1.1.0, with Sapporo 2.x compatibility as a non-goal? This goes with the stage choice in SR-010.
5. **Snakemake support range (FC-040 vs CH-009).** One logger-interface major per Spectio release (FC-040), or interface 1.x and 2.x both supported (CH-009)? Both agree on testing a minimum and a latest Snakemake.
6. **Seqera API compatibility (FC-051).** Drop §7bis item 6 as contrary to decision 0001? The 2026-10-2x log entry still says "later, after a legal check".
7. **Migrations (FC-052).** One Alembic tree with dialect branches inside revisions, or two trees like Prefect? Spike 7 can inform the choice.

## Proposed spikes

Ranked by how much they unblock. Durations are the reviewers' estimates.

| # | Spike | Findings | Effort | Decides |
|---|---|---|---|---|
| 1 | **Logger coexistence and the API path:** on `smk-toy`, a profile with `logger: [snkmt]` plus `--logger spectio`; `--logger snkmt --logger spectio`; `SnakemakeApi` with one handler. Does snkmt still receive rows? | FC-039 | 15 min | how the Snakemake adapter builds its logger list |
| 2 | **Snakemake version matrix:** a stub logger with `has_filter=True` on Snakemake 9.2, 9.10, 9.23 and 9.27.1, plus the interface's `tests.py` (merge with CH-009's test) | FC-040, CH-009 | half a day | the supported range and interface pin |
| 3 | **Transport under an outage:** a blackholed ingest for 60 s during a 500-job `smk-toy` run, synchronous handler against a batched JSONL spool; measure wall-clock delta and lost events | SR-001, SR-017, CH-005 (evidence from FC-205) | 2 h | the ingest contract's numbers |
| 4 | **Flyte Nextflow on POSIX:** read `flyteplugins-nextflow` `_run.py` and `flyteplugins-slurm`: can `work_dir` be a shared-FS path under Slurm? | FC-043 | 1 h | how narrow the positioning is |
| 5 | **Snakemake run crate:** install `snakemake-report-plugin-rocrate` from git, run it on `smk-toy`, validate with `rocrate-validator`, merge with a mock gate provenance under RO-Crate 1.1 + WRROC 0.5 | FC-038, FC-041 | 2 h | whether to depend on the plugin; the merge rules |
| 6 | **nf-prov per Nextflow version, and lineage:** nf-prov 1.7.x on 25.10.9 and 1.8.x on 26.10.3 on `nf-toy`; enable `lineage.enabled` and list what it records | FC-045 | 1 h | the generated config; whether lineage feeds the collector |
| 7 | **Migration tree shape:** three representative revisions on SQLite and Postgres 18 in one tree | FC-052 | 2 h | one tree or two |
| 8 | **Galaxy WES and pause:** `gxy-wes demo` against a Galaxy 26.1 container; confirm the WES routes, the declared version, `x-api-key`, and the pause step's behaviour | FC-044, FC-046 | 1 h | Galaxy as a reference and a later adapter |
| 9 | **FlowO hands-on:** install from its Compose file and confirm it has no launch or steering | FC-042 | 30 min | the comparison row |
