---
step: APPLY6
wave: W4
status: running
pr: null
review: null
review_score: null
review_ref: null
---
# APPLY6 · Stages in 0.0.1, declared or detected

!!! info "Running 2026-10-28 · branch `autopilot/apply-stages` · Thomas: 0.0.1 shows both the stages and the processes or rules list · stages detected from nf-core subworkflows and Snakemake rule files · shown on four example pipelines · naming assumed (inbox #68) · a bridge-loading problem raised, not changed (inbox #69) · no doc review yet"

![APPLY6 figure in three rows. Nextflow, nf-core/rnaseq 3.27.0: nf-spectio receives onProcessCreate with each fully qualified process name, such as NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN, 67 processes, all before onFlowBegin; a detector skips the wrapper and pipeline scopes, makes one stage per subworkflow, merges aliases, keeps the Report and caps at 8 by merging the smallest neighbours; the result is 8 stages drawn to scale, one cell per process: Prepare genome references and indices 9, Fastq qc trim filter setstrandedness 11, Align star and Quantify bam salmon 12, Bam markduplicates picard 6, Bam qc rnaseq 13, Bedtools genomecov and Bedgraph 9, Quantify pseudo alignment 6, Report 1. Snakemake, mosaicatcher-pipeline v2.5.1: the main Snakefile includes 20 rule files; the logger sees rule names only, so the server reads the files from snakefile_main, and --list-rules drops the unused ones; one stage per rule file in include order, a rules sub-directory as one stage, the main Snakefile's rules last, at most 8: External data 15, Setup and Utils 18, Count and Segmentation 18, Plots 14, Regenotyping and Strandphaser 13, Breakpointr and Haplotagging 7, Mosaiclassifier to Stats 15, Final targets 1. Per run: 1 declared, from spectio.yml or a lab overlay, beats 2 detected, display only and no gates, which beats 3 none, for flat pipelines; the processes or rules list is always shown, grouped under the stages with an Other group](../../assets/diagrams/apply6_stages_light.png#only-light)
![APPLY6 figure in three rows. Nextflow, nf-core/rnaseq 3.27.0: nf-spectio receives onProcessCreate with each fully qualified process name, such as NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN, 67 processes, all before onFlowBegin; a detector skips the wrapper and pipeline scopes, makes one stage per subworkflow, merges aliases, keeps the Report and caps at 8 by merging the smallest neighbours; the result is 8 stages drawn to scale, one cell per process: Prepare genome references and indices 9, Fastq qc trim filter setstrandedness 11, Align star and Quantify bam salmon 12, Bam markduplicates picard 6, Bam qc rnaseq 13, Bedtools genomecov and Bedgraph 9, Quantify pseudo alignment 6, Report 1. Snakemake, mosaicatcher-pipeline v2.5.1: the main Snakefile includes 20 rule files; the logger sees rule names only, so the server reads the files from snakefile_main, and --list-rules drops the unused ones; one stage per rule file in include order, a rules sub-directory as one stage, the main Snakefile's rules last, at most 8: External data 15, Setup and Utils 18, Count and Segmentation 18, Plots 14, Regenotyping and Strandphaser 13, Breakpointr and Haplotagging 7, Mosaiclassifier to Stats 15, Final targets 1. Per run: 1 declared, from spectio.yml or a lab overlay, beats 2 detected, display only and no gates, which beats 3 none, for flat pipelines; the processes or rules list is always shown, grouped under the stages with an Other group](../../assets/diagrams/apply6_stages_dark.png#only-dark)

*Stage sizes are those of `tests/pipelines/real/stages/expected/`. Before: `autopilot/integration` at `1abd5dd`, where 0.0.1 showed the processes or rules only and stage detection came later (P1 Assumption 6).*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml). Thomas, 2026-10-28: "les 2 dans 0.0.1 ; certains pipelines exemples pour montrer comment ça fonctionne pour 2/3 nf core et https://github.com/friendsofstrandseq/mosaicatcher-pipeline ; travaille pour nf core sur un systeme automatisée qui détecte les différents grand stages ; il doit y avoir un moyen via subworkflows etc" ([decision log](../../decisions/log.md#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list)). A spike came first; this step applies it.

## What changed

**Part 1, the spike** (branch [`spike/stage-detection`](https://github.com/weber8thomas/spectio/tree/spike/stage-detection), files under `spikes/stage-detection/`). It ran nf-core/rnaseq, sarek and methylseq with `-preview` and the T2 bridge, and mosaicatcher-pipeline as a Snakemake dry run. It wrote two throwaway detectors and four example lab overlays. Note: [Spike: stage detection](../../research/spike-stage-detection-2026-10-28.md).

**Part 2, the specs** (this branch).

- **[ui-spec §5.1](../../specs/ui-spec.md).** Source (2), detected, now names the real rules: Nextflow subworkflows below the wrapper scopes, and Snakemake rule files, in place of "top-level subworkflows" and "module prefixes and checkpoints". A dated note says that the run detail shows both the stages and the processes or rules, with an Other group.
- **[ui-spec §5.1.1](../../specs/ui-spec.md), new.** It covers:
    - where detection runs: on the server, from what the bridges send, for launched and terminal runs alike;
    - the seven Nextflow rules and the four Snakemake rules;
    - order and state;
    - the four examples, with their fixtures.

    §2 says the gauge has one sector per declared or detected stage.
- **[checking-scenarios §12.1](../../specs/checking-scenarios.md).** A `match` glob sees the fully qualified Nextflow name, and `*` crosses `:`.
- **[api §7](../../specs/api-and-data-model.md) `run_stages`.** Detected stages freeze at the run's first `onFlowBegin` or `workflow_started`, before any task.
- **[dev-env §15.1](../../specs/dev-environment-and-testing.md#151-capabilities-by-version).** A new Stages row: yes in 0.0.1, both, display only; the overlay editor, rerun from a stage and gates stay later.
- **[`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md) §2.** A feature row.
- **[P1](../../plans/P1-walking-skeleton.md).**
    - Assumption 6 is reversed: stages and the list, both.
    - The Goal, Milestones (a new M7) and Done when are updated.
    - A new Task 27 covers the detectors as pure functions, the overlay assignment, `run_stages`, `GET /runs/{id}/stages` and the stage list in the run detail, with golden tests on the fixtures. Snakemake's `--list-rules` runs in the head script, so the server never runs `snakemake` itself.
    - Task 18–20 lines are not edited.
- **Fixtures, [`tests/pipelines/real/stages/`](https://github.com/weber8thomas/spectio/tree/autopilot/apply-stages/tests/pipelines/real/stages).** They hold:
    - five process lists and the mosaicatcher rule lists;
    - the four overlays;
    - the expected detector output;
    - a README with the pins.
- **[Inbox](../../reviews/inbox.md).** #68 and #69.
- **[Decision log](../../decisions/log.md#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list).** A new entry.

## Why

nf-core pipelines declare no stages, so without detection 0.0.1 would show a flat list of 50 to 70 processes. The spike shows that the subworkflow scopes are already in every process name, and that the names reach the bridge before any task, so detection costs nothing at run time. The detected names are technical, so lab overlays stay the way to good names. Detection runs on the server so that runs started from a terminal get the same stages.

## Evidence

- **Detector output**, from the spike (`out/detector_nf.txt`, `out/detector_smk.txt`):

    ```text
    rnaseq 3.27.0 STAR+Salmon  67 processes -> 8 stages
    rnaseq 3.27.0 HISAT2       62 processes -> 8 stages
    sarek 3.11.0               48 processes -> 8 stages
    methylseq 4.2.0 Bismark    13 processes -> 4 stages
    methylseq 4.2.0 bwa-meth   15 processes -> 5 stages
    mosaicatcher v2.5.1        101 rules (--list-rules) -> 8 stages; source only: 204 rules -> 8
    synthetic T2 (flat)        no detected stages
    ```

- **Overlays:** each of the four matches every name of its fixture, with no overlap (`out/overlays_vs_detected.txt`).
- **Docs gate**, `python3 tools/docs/check.py` on this branch:

    ```text
    mermaid: 5 blocks checked
    diagrams: 28 scripts re-run, 56 SVGs compared
    media: 138 outputs in the manifest
    progress: 41 pages checked
    docs gate: 0 failure(s)
    ```

- **Mermaid:** no diagram added or changed in this step.
- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0. The new anchors exist in the built pages: `511-detected-stages`, `2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list` and `69-nf-spectio-is-enabled-in-a-way-that-breaks-nf-core-runs-or-drops-the-bridge`.
- **Before:** `git show 1abd5dd:docs/plans/P1-walking-skeleton.md` (Assumption 6: "Structural stage detection … and `run_stages` come later"). **After:** `git diff 1abd5dd -- docs/specs docs/plans docs/decisions docs/reviews/inbox.md`.

## Figures and media

- `apply6_stages` (above), new: [`tools/diagrams/apply6_stages.py`](https://github.com/weber8thomas/spectio/blob/autopilot/apply-stages/tools/diagrams/apply6_stages.py), entry `apply6-stages` in `docs/assets/media.yaml`. Rendered light and dark; both PNGs were opened and checked for overlaps.
- The P1 figure `p1_skeleton` is not redrawn; its dated note now also names Task 27.
- No screenshot or cast: nothing in this step runs a UI.

## Findings and open questions

- **Inbox #68** *(assumed (a))*: the four example pipelines; detected stages keep technical names; readable names come from overlay files.
- **Inbox #69** *(not assumed)*: `-plugins nf-spectio@<ver>` breaks nf-core runs, and a `plugins` block in `~/.nextflow/config` silently drops the bridge; `NXF_PLUGINS_DEFAULT` works. It blocks P1 Task 10 for real nf-core pipelines.
- **[to be validated]**, from the note:
    - the same names on a real run with tasks, on SLURM;
    - `onProcessCreate` order on Nextflow 25.10.x;
    - `onProcessTerminate` for a process whose input never closes;
    - `--list-rules` needing input data on other pipelines;
    - the order of rules first seen after a checkpoint;
    - older nf-core templates;
    - `NXF_PLUGINS_DEFAULT` on the EMBL cluster.
- **Merge note:** the UI-lite review (branch `autopilot/ui-lite-review`) owns the lite boards and the P1 Task 18–20 lines; both steps add inbox items, so check the numbers at merge.
