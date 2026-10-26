# R12 · UI scenarios: what the new boards need from the specs

Round: R12 (2026-10-26). Method: about 50 new or upgraded UI boards were built to cover the nf-core catalogue. The pipelines are representative of the classes in [`checking-scenarios.md`](../specs/checking-scenarios.md) §1, and runs without gates are included.
- **Data:** the boards use real data where it exists:
  - nf-core megatest outputs ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §10.3);
  - real test images, read from public OME-Zarr and nf-core/test-datasets (§10.4).
- **Recording:** each board agent recorded every piece of data or behaviour the board needs that no spec or API defines.
- **Status:** these are findings, not changes. The specs are untouched; triage and `/apply-findings` decide.
- **Where the boards are:** the canvas and `design/ui-canvas/`; the scenario map is ui-spec §10.

Format: [`README.md`](README.md). Prefix `UX` (board agents and the UX review of this round).

## Checks and source bindings

### UX-101 · major · MultiQC bindings do not match real column names
- **Where:** checking-scenarios.md §7 (`multiqc:<module>.<column>`).
- **Evidence:**
  - Real general statistics name their columns `module-column`. Examples are `qualimap_rnaseq-5_3_bias`, `star-uniquely_mapped_percent` and `fastqc-1-percent_duplicates` (`tests/fixtures/megatests/rnaseq/…/multiqc_general_stats.txt`, header line).
  - Plot tables such as `featurecounts_biotype_plot` and `strand_check_summary_table` are not in the general statistics at all.
  - MultiQC ≥ 1.2x nests `report_general_stats_data` as `{module: {sample: {metric}}}` in `multiqc_data.json` (smrnaseq 2.4.1 megatest).
- **Problem:** a binding written from the spec finds nothing.
- **Proposal:**
  - Define `multiqc:<general-stats column>` exactly as MultiQC writes it, and `multiqc-table:<table file>#<key>:<column>` for the other tables.
  - Test bindings against `tests/fixtures/megatests/`.
- **Found by:** ReviewReport, ReviewSmallRNA, ReviewAmpliseq agents · **Status:** open

### UX-102 · major · The binding vocabulary is too small for real checks
- **Where:** checking-scenarios.md §7.
- **Evidence:** the boards had to fall back on `script:` for each of these:
  - derived values: Mt_rRNA share, too-short %, DADA2 kept %, the ratio of two columns (ReviewReport, ReviewAmpliseq, ReviewRepertoire);
  - pair-level tables keyed by `sample_a, sample_b` (peddy relatedness, ReviewTrio);
  - long tables to pivot into sample × region (mosdepth amplicons, ReviewViral);
  - JSON paths that contain the item key (miRTrace inside `multiqc_data.json`);
  - a metadata TSV kept apart from the samplesheet (ampliseq `Metadata_full.tsv`);
  - a value relative to another run (scrnaseq Cell Ranger against simpleaf);
  - reductions of a matrix (mean PAE, proteinfold);
  - image metrics (tissue fraction, focus, streaks, hot pixels, background drift: ReviewWells, ReviewSlides, ReviewROIs).
- **Proposal:**
  - Add `expr:` over bound values, `pair:`, `pivot:`, `metadata:` and `relative:` bindings.
  - Add an image-metric check provider.
  - Keep `script:` as the escape hatch.
- **Found by:** 9 board agents · **Status:** open

### UX-103 · minor · Check states beyond pass / warn / fail
- **Where:** checking-scenarios.md §4.
- **Evidence:** the boards needed four more states:
  - `n/a`: a channel is missing, or the export is 8-bit (ReviewROIs);
  - "binding suspect": `fastp-pct_adapter` is below 0.1 % while reads shrink from 76 to 25 nt (ReviewSmallRNA);
  - "computing n of m" (ReviewQueue);
  - "muted by the overlay" (ReviewCells).
- **Proposal:** define `n/a`, `suspect`, `computing` and `muted`, and how each one counts towards the gate.
- **Status:** open

### UX-104 · major · Item roles and the constraint kinds real samplesheets need
- **Where:** checking-scenarios.md §5 and §7 (`constraints` has only `pair` and `min_per_group`).
- **Evidence:**
  - **Roles:** an input control (chipseq `control` column); a negative control (taxprofiler blanks, the viralrecon `CONTROL_01`); proband, mother and father derived from `paternal_id` / `maternal_id` / `phenotype` (raredisease).
  - **Constraints:**
    - de novo calling needs both parents;
    - clones are built per subject (airrflow `cloneby`);
    - ampliseq keeps a metadata column only if every value occurs at least twice (`bin/metadata_pairwise.r`).
  - **Grouping:** groups derived from a metric, such as read-length batches (smrnaseq).
- **Proposal:**
  - `items.roles` with role-scoped checks.
  - Constraint kinds `requires_role`, `group_complete` and `pipeline_rule`.
  - A consequence text for each constraint, with its source.
  - `group_by` on a derived value.
- **Status:** open

### UX-105 · major · Sub-items and a sixth view: items × sub-regions
- **Where:** checking-scenarios.md §7 (`children`) and §8 (five views).
- **Evidence:**
  - Models under a sequence (proteinfold, 5 ranks each).
  - Tiles under a slide.
  - Amplicons × samples (viralrecon, 49 × 98), where a column-wise check ("one amplicon drops out in 8 samples → scheme, not samples") is the key finding.
- **Proposal:**
  - Allow `children` with their own checks.
  - Add a "matrix" view (items × sub-regions heatmap) and a column-scope check.
- **Status:** open

## Decisions

### UX-106 · major · The meaning of Flag, undecided items and reviewer-added flags
- **Where:** checking-scenarios.md §5, ui-spec.md §4.5.
- **Evidence:**
  - Flag keeps an item that is below a block threshold when excluding it would break a group (ReviewReport, K562_REP1).
  - Some boards keep undecided items by default (ReviewSlides); others disable Apply until a block check is decided (ReviewWells, the G3 streak). The two behaviours were drawn on purpose, so that the spec picks one.
  - A reviewer flags wells that no check flagged (ReviewWells: D8, E8, H12).
  - Candidates get a three-way accept / reject / flag (ReviewFusions).
- **Proposal:**
  - Define Flag (who may use it below a block threshold, and that it is recorded).
  - Define the default for undecided items under `block` checks.
  - Define "added by a reviewer" as a decision source.
- **Status:** open

### UX-107 · minor · Missing verbs
- **Evidence:** the boards needed verbs that do not exist yet:
  - Resequence: exclude now, then replace the input later (ReviewViral);
  - reassign a control (ReviewChip);
  - protect a feature from a rule (ReviewContamination, E. coli);
  - pin a run-wide parameter that the pipeline estimates from the items (airrflow `clonal_threshold`, ReviewRepertoire).
- **Proposal:** add the four verbs to §5, with how each reaches the engine (§6).
- **Status:** open

### UX-108 · major · Decisions that the pipeline cannot read
- **Where:** checking-scenarios.md §6.3 and §6.4.
- **Evidence:** the parameter lists in `nextflow_schema.json` (read 2026-10-26) show no parameter that reads:
  - a model keep list (proteinfold 2.0.0);
  - a cell keep list (scrnaseq 4.2.0);
  - a taxa list (taxprofiler 2.0.1);
  - a per-tile parameter (mcmicro 2.0.0).

  Two further consequences:
  - The filter artifact can only go to a linked downstream run, which §6.4 cannot target.
  - Excluding an item can move the parameter estimated from the items (airrflow).
- **Proposal:**
  - §6.4 lets an artifact target a declared parameter of a linked run.
  - The UI says "attached only" when nothing reads the artifact.
  - Estimated parameters get "pin or reopen" semantics.
- **Status:** open

### UX-109 · major · Which stages a parameter change reruns, and at what cost
- **Where:** api-and-data-model.md (relaunch), ui-spec.md §4.5 / §4.6.
- **Evidence:**
  - methylseq `clip_r1` reruns from stage 1 (about 15 h, taken from the real trace), while `ignore_r1` reruns only the extraction (about 1 h 25).
  - ampliseq gives a rerun cost.
  - The spec only has "Apply and continue".
- **Proposal:**
  - Map each parameter to the processes it reaches, from the process inputs or the overlay.
  - Add an "Apply and rerun from stage N" primary action.
  - Base cost estimates on per-task history.
- **Status:** open

## Gates

### UX-110 · major · Gates that wait for a signal
- **Where:** synthesis.md (gates), api-and-data-model.md (`POST /gates/{id}/signals`), checking-scenarios.md §7.
- **Evidence:** ReviewSignal needs:
  - `decide.systems`, a check `kind: signal` and a `signal:` source;
  - a signal schema: name, payload, validation, the target run or gate, and the service account it is bound to;
  - a vocabulary for `timeout`, `remind` and `action`;
  - "approve without the signal" recorded as an override.
- **Status:** open

### UX-111 · minor · Where each gate comes from, and lab-wide figures
- **Where:** api-and-data-model.md (run and gate resources).
- **Evidence:**
  - The lists show, for every run, where its gate comes from (lab overlay, `spectio.yml`, or none).
  - They also show where its stages come from (declared, detected, or task quarters).
  - The queue shows the worst item, the checks still computing, and whether you may decide or only view.
  - The Overview shows runs per item kind, split into gated and not gated (ReviewQueue, RunsTable, Overview).
- **Proposal:** add `gate_source`, `stage_source`, `worst_item`, `can_decide` and an aggregates endpoint.
- **Status:** open

### UX-112 · minor · Adding a gate at launch
- **Evidence:** LaunchReview offers "+ gate here" between stages. `POST /runs` accepts only `gates: "from-manifest"`.
- **Proposal:** allow per-run gates when the overlay permits them. Gates stay off by default.
- **Status:** open

## Runs, relaunch, outputs

### UX-113 · major · Relaunch with resource changes and a dry-run estimate
- **Where:** api-and-data-model.md (`POST /runs/{id}:relaunch` takes parameter overrides only).
- **Evidence:**
  - RunFailed and RelaunchDialog suggest `mem_mb 8000 → 16000` (`--set-resources`) and a Nextflow memory override generated from the failure.
  - They also show an estimate: reused, rerun, still to run.
- **Proposal:**
  - Add `resource_overrides` and `config_overrides`.
  - Give suggestions ids.
  - Add `POST /runs/{id}:relaunch?dry_run=true`, which runs `snakemake -n` or the Nextflow cache check through the runner.
  - Whether a memory change invalidates the Nextflow cache is **[to be validated]**.
- **Status:** open

### UX-114 · minor · Comparing runs
- **Evidence:** RunsCompare needs three things:
  - a compare endpoint;
  - versioned config overlays in `run_inputs`;
  - `/runs/{id}/software`, plus a link from each cached task to the attempt that computed it (to count "CPU-hours saved").
- **Status:** open

### UX-115 · minor · Outputs, retention and the depictio hand-off
- **Evidence:** RunOutputs needs:
  - a directory listing with folder sizes, where `GET /runs/{id}/artifacts` is flat today;
  - a per-run retention date and "keep 30 more days";
  - a manual depictio trigger and the hand-off status;
  - written sandbox rules for HTML reports (CSP, no network).
- **Status:** open

### UX-116 · minor · Runs launched from the terminal
- **Evidence:** RunObserved needs:
  - the launch host in the Tower payload **[to be validated]**;
  - task logs, which may not come through the Tower protocol alone **[to be validated]**;
  - an "is this run adoptable" check;
  - the rule that groups processes into detected stages;
  - the runner start command.
- **Status:** open

## Launch

### UX-117 · major · Listing files through the runner
- **Evidence:** LaunchSamplesheet, WorkflowImport (path on a cluster) and RunOutputs all browse folders on the cluster: paging, a glob, and "permission denied" on a folder the user cannot read. Synthesis mentions a "browse a directory" order but gives no shape for it.
- **Proposal:** a runner order `list_dir` with paging, glob and typed errors, exposed as `GET /environments/{id}/files`.
- **Status:** open

### UX-118 · minor · Building a samplesheet from files
- **Evidence:** pairing R1 and R2, deriving names, and handling rows that share a sample (nf-core/rnaseq concatenates them **[to be validated]**).
- **Status:** open

### UX-119 · minor · Workflows without a parameter schema, and Git refs
- **Evidence:** LaunchGitNoSchema guesses parameter types from `nextflow.config` and needs a list of Git refs reached through a runner credential. `GET /workflow-versions/{id}/schema` is undefined for a workflow with no schema.
- **Status:** open

### UX-120 · major · Batch launches and Spectio's own queue
- **Evidence:** LaunchBatch starts one run per plate. It needs name templates, a concurrency limit and a "queued because of quota / slot" reason, and can hold runs for a storage quota. No batch resource and no reason field exist.
- **Status:** open

### UX-121 · minor · Scheduled start, notifications, pre-flight
- **Evidence:** LaunchReview needs:
  - `start_at`;
  - notifications per event, where only `notify.webhook_ids` exists;
  - a pre-flight endpoint.
- **Status:** open

### UX-122 · major · Chaining runs
- **Evidence:** LaunchChain feeds the fetchngs `samplesheet/samplesheet.csv` into nf-core/rnaseq `--input`, mapping columns and starting on success. The spec has lineage (resume, rerun) but no chaining.
- **Proposal:** a `chain` resource on runs: source output, target workflow, column mapping, and a trigger (on success, or ask first).
- **Status:** open

## Workflows

### UX-123 · minor · Overlays, versions and the catalogue
- **Evidence:**
  - Process names of a release that has never run (`nextflow run … -preview` **[to be validated]**).
  - Module and subworkflow diffs between releases, including renames.
  - Saved launch presets are undefined.
  - For overlays: a version range, draft / saved states, history, and a dry evaluation against the last run.
  - Check presets per assay need a source.
  - Stage colours beyond four (ui-spec §3.2 allows 8).
  - What happens to processes no stage matches while a gate is open.
  - Discovered workflows: a dirty tree, no Git remote, recognising a genuine nf-core release, an Ignored state, and how many runs must agree on a captured default.
  - The scope of a Git credential, and whether the server or a runner clones.
  - Catalogue fields: lab default, update status, overlay compatibility per release.
- **Status:** open

## Environments

### UX-124 · minor · Connecting and checking a runner
- **Evidence:** EnvConnect shows a registration token valid for 15 min, a runner credential rotated every 24 h and a heartbeat every 30 s. None of these values is in a spec. It also needs a self-check report event and a way to load environment modules into the runner.
- **Status:** open

### UX-125 · minor · Software inventory and pre-pulled images
- **Evidence:** EnvSoftware shows the Apptainer cache with "Clean" actions, and pre-pulls the images of a pipeline release. The list comes from the release's containers (`nextflow inspect` **[to be validated]**). There is no API for either.
- **Status:** open

### UX-126 · major · Quotas, limits and who may launch where
- **Evidence:** EnvAccess shows several things the API does not have:
  - concurrent runs per project, and CPU-hour and GPU-hour quotas per month;
  - partitions allowed per group;
  - per-agent permission to launch on an environment (ui-spec §4.9 promises this);
  - what happens when a quota is hit (the run is queued with a reason), and alerts at 80 % and 100 %;
  - credential types (registry tokens, S3 keys, Git tokens) with rotation reminders.

  Environment grants cover projects and groups only.
- **Status:** open

### UX-127 · minor · A single machine
- **Evidence:** the rule "memory limit = 80 % of MemAvailable" exists only in the spike note and the test runner. EnvLocal also needs a local queue length (with "queue full"), and a rule for a laptop that goes to sleep.
- **Status:** open

## Imaging

### UX-128 · major · Thumbnails, crops and the viewer contract
- **Evidence:**
  - Plate maps, tile mosaics and ROI tables show one thumbnail per item, at a chosen pyramid level, read from OME-Zarr or OME-TIFF through the runner (ReviewWells, ReviewSlides, ReviewROIs, ViewerOmeZarr).
  - Densities need the pixel size, which idr0076 stores as a unitless 1.0.
  - Reviews need per-channel colour and contrast, plus an RGB brightfield mode (idr0073).
  - The api names "an OME-Zarr viewer" and nothing more.
- **Proposal:** a viewer contract: multiscale metadata, a tile endpoint with range requests, a thumbnail endpoint (level, crop), labels, the omero channel windows as defaults, and v0.4 and v0.5 stores. Test it on the images of dev-environment-and-testing.md §10.4.
- **Status:** open

## Clinical data

### UX-129 · major · Gates on clinical data
- **Evidence:** ReviewTrio (raredisease) shows:
  - pseudonyms only;
  - downloads off;
  - every view logged, with an access log on the gate;
  - AI agents off by project policy.

  checking-scenarios.md §9 says only that "roles apply strictly".
- **Proposal:** a "restricted data" project policy covering pseudonymisation, downloads, a per-view audit and agent access. Route it to the security review.
- **Status:** open

## Facts found while building (to validate or already corrected)

- **quantms:** nf-core/quantms is not among the 106 released pipelines of the survey. The proteomics board uses nf-core/diaproteomics, which the survey lists with no MultiQC.
- **spatialaxe:** the Xenium pipeline is nf-core/spatialaxe, released 1.0.1 (nf-co.re/pipelines.json, read 2026-10-26).
- **Stain:** the idr0073 slide is brightfield IHC; its chromogen and counterstain are **[to be validated]**.
- **Partial megatest uploads:** some uploads are partial. Examples are spatialaxe 1.0.1 (no objects) and the latest atacseq, chipseq and methylseq (no MultiQC data). That is why `tools/fixtures/megatests.py` falls back to older releases.
- **A real metadata swap:** the airrflow test samplesheet has its `tissue` and `treatment` columns swapped (`pipeline_info/samplesheet.valid.tsv`). The board shows it as an info-level consistency check.
