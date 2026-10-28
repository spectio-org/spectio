# Spike — detecting the big stages of a run (2026-10-28)

**Question.** Thomas, 2026-10-28: 0.0.1 shows both named stages and the list of processes or rules ("les 2 dans 0.0.1"), with example pipelines (two or three nf-core ones and [mosaicatcher-pipeline](https://github.com/friendsofstrandseq/mosaicatcher-pipeline)), and "un système automatisé qui détecte les différents grands stages … via subworkflows". In detail:
- Nextflow: where does the fully qualified process name (`NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN`) come from, what does `nf-spectio` get, and when is the full list known?
- Can a small detector turn those names into a handful of stages on real nf-core pipelines, and where is it wrong?
- Snakemake: what can the logger see, and where can a rule-to-stage map come from?
- How do detected stages compare with stages a lab declares in a `spectio.yml` overlay ([`checking-scenarios.md`](../specs/checking-scenarios.md) §12)?

**Answer in one line.** Yes for nf-core: every process name, scoped by its subworkflows, reaches the bridge **before the first task** (`onProcessCreate`, then `onFlowBegin`), and a 190-line detector gives 4 to 8 sensible stages on rnaseq, sarek and methylseq, ugly names included. For Snakemake the logger sees only rule names, so stages come from the **rule files** the main Snakefile includes, read from the source; checkpoints hide most of the DAG at start. A declared overlay gives better names and can split a subworkflow, which detection cannot. Side finding: the documented ways to enable `nf-spectio` either break nf-core runs or silently drop the bridge; `NXF_PLUGINS_DEFAULT` works.

Time box: about 90 minutes, met. No spec was edited by the spike; [What it changes](#what-it-changes) lists the edits APPLY6 makes.

## Setup

- **Machine.** Claude Code cloud session, Linux 6.18, OpenJDK 21, no Docker, so nothing ran a real nf-core task: Nextflow ran with `-preview`, which executes the script and builds the DAG without running a task, and Snakemake ran as a dry run (`-n`).
- **Engines.** Nextflow 26.10.4 and Snakemake 9.27.1, the pins of `dev/versions.env`. The spike-T2 bridges were reused unchanged: `nf-spectio` 0.0.1 (a `TraceObserverV2`), the Snakemake logger plugin `spectio`, and the capture server ([T2 note](spike-engine-events-2026-10-28.md#what-was-built-branch-spikeengine-events-throwaway)).
- **Pipelines,** pinned:
  - nf-core/rnaseq 3.27.0 (`a1fcddd`), default STAR + Salmon and `--aligner hisat2`;
  - nf-core/sarek 3.11.0 (`6e9b164`), its test profile (`tools = 'strelka'`, `conf/test.config:47`);
  - nf-core/methylseq 4.2.0 (`5aa5646`), `--aligner bismark` and `--aligner bwameth`: a different shape, where the aligner choice changes the subworkflows;
  - friendsofstrandseq/mosaicatcher-pipeline v2.5.1 (`2289f7c`), with its test data submodule `.tests` (`3ba5668`);
  - nextflow-io/nextflow v26.10.4 (`691b821`), read for the naming and plugin code.
- **Branch** `spike/stage-detection`, files under `spikes/stage-detection/` ([README](https://github.com/weber8thomas/spectio/blob/spike/stage-detection/spikes/stage-detection/README.md), [LOG](https://github.com/weber8thomas/spectio/blob/spike/stage-detection/spikes/stage-detection/LOG.md)). Paths in captures are replaced by `<src>`, `<run>`, `<scratch>`.

## Results

### Nextflow: where the stage information is

1. **The fully qualified name is the process name itself.** When a workflow calls a process or a subworkflow, Nextflow prefixes its name with the calling workflow's name and the separator `:` (`modules/nextflow/src/main/groovy/nextflow/script/BindableDef.groovy:41-49`, `SCOPE_SEP = ':'` in `modules/nf-commons/src/main/nextflow/Const.groovy:89`), and the clone carries it as its `processName` (`script/ProcessDef.groovy:113-118`). Nested workflows get the same treatment, so the name holds the whole call path. The trace record's `process` field is that name (`processor/TaskHandler.groovy:210`). Toy pipeline, real run: trace and bridge both report `NFCORE_TOY:TOY:QC:QC_INNER:STEP (s1)` ([LOG](https://github.com/weber8thomas/spectio/blob/spike/stage-detection/spikes/stage-detection/LOG.md) §3).
2. **Every process is known before the first task.** `TraceObserverV2.onProcessCreate(TaskProcessor)` (`trace/TraceObserverV2.groovy:62`) fires once per process as the script runs, in script order, and `onFlowBegin` comes after the last one. nf-tower relies on this: it collects `process.name` in `onProcessCreate` (`plugins/nf-tower/src/main/io/seqera/tower/plugin/TowerObserver.groovy:236-240`) and sends the list in its begin request, noting that "the dataflow network is fully built by the time `onFlowBegin` fires" (same file, `:397-403`). Measured: rnaseq's 67 `onProcessCreate` events arrive over 14 s, all before `onFlowBegin`. The spike-T2 `nf-spectio` already posts each one.
3. **The order is source order.** The 67 rnaseq names arrive in the order of the calls in `workflows/rnaseq/main.nf` (lines 191 to 820), after the two reference subworkflows `main.nf` calls first.
4. **Conditional branches show two ways.**
   - A Groovy `if` around a call removes the process from the list: with `--aligner hisat2`, rnaseq creates `FASTQ_ALIGN_HISAT2:*` and not `ALIGN_STAR:*` nor `QUANTIFY_BAM_SALMON:*` (62 processes instead of 67).
   - A `when:` condition, or `ext.when` from config, keeps the process in the list with no task. Sarek's test run creates `BWAMEM2_MEM`, `DRAGMAP_ALIGN`, `SENTIEON_BWAMEM`, `DEEPSOMATIC` and the Parabricks processes, though only Strelka and BWA-MEM run. The toy's `when: false` process gets `onProcessCreate`, then `onProcessTerminate`, and no task.
   - So a detected stage can end with **no task**. `onProcessTerminate` of all its processes is the signal; such a stage ends as `skipped`.
5. **The DAG export keeps the scopes too.** `-with-dag dag.mmd` writes one Mermaid `subgraph "<scope> [<name>]"` per workflow scope (25 for rnaseq). Since the process name already holds the scope, the detector does not need it.
6. **Human names are thin.** nf-core subworkflows from the modules repository ship a `meta.yml` with a one-sentence `description`; local ones mostly do not:

   | Pipeline | `subworkflows/nf-core/` with `meta.yml` | `subworkflows/local/` with `meta.yml` |
   |---|---|---|
   | rnaseq 3.27.0 | 22 of 22 | 0 of 6 |
   | sarek 3.11.0 | 8 of 8 | 5 of 68 |
   | methylseq 4.2.0 | 13 of 13 | 1 of 2 |

   The descriptions are sentences, not labels. For example, `fastq_qc_trim_filter_setstrandedness`: "Performs linting, quality control, trimming, filtering, and strandedness determination on RNA-seq FASTQ files…". They work as a tooltip, not as a stage name.

### Nextflow: the detector

The detector is `detector/detect_nf.py` (throwaway). It takes the ordered `onProcessCreate` names and works in seven steps:
1. **Expand the wrappers.** It descends through the scope every process sits under (`NFCORE_RNASEQ`), then into the pipeline's own workflow (`RNASEQ`). That is the child scope holding more than half of the processes; the manifest name, when known, gives the same answer on all five captures.
2. **One group per child.** Each child subworkflow is a group. Each run of consecutive direct process calls is a group.
3. **Merge aliases.** Groups whose names differ only in their last word are merged: `…_FORWARD`, `…_REVERSE`, and `PREPARE_GENOME_REFERENCES` with `PREPARE_GENOME_INDICES`.
4. **Attach single processes.** A one-process direct group joins its neighbour in the same scope.
5. **Keep the report separate.** `MULTIQC` stays its own "Report" stage.
6. **Cap at 8.** While there are more than 8 groups, it merges the smallest adjacent pair, because the stage gauge has 1 to 8 sectors ([`ui-spec.md`](../specs/ui-spec.md) §2).
7. **Name them.** A stage is named after its subworkflow, humanised. A pipeline with no subworkflow gets no detected stages.

Output (`out/detector_nf.txt`; the count is the number of processes):

| Pipeline | Detected stages, capped at 8 |
|---|---|
| rnaseq, STAR + Salmon (67 → 8) | Prepare genome references + Prepare genome indices (9) · Fastq qc trim filter setstrandedness (11) · Align star + Quantify bam salmon (12) · Bam markduplicates picard (6) · Bam qc rnaseq (13) · Bedtools genomecov … + Bedgraph bedclip bedgraphtobigwig … (9) · Quantify pseudo alignment (6) · Report (1) |
| rnaseq, HISAT2 (62 → 8) | the same, with Fastq align hisat2 (6) in place of the STAR and Salmon stages |
| sarek (48 → 8) | Prepare genome + Prepare intervals (5) · Spring decompress … (3) · Convert fastq input (9) · Fastq preprocess gatk (11) · Cram sampleqc + Bam variant calling germline all (7) · Bam variant calling somatic all (8) · Vcf qc bcftools vcftools (4) · Report (1) |
| methylseq, Bismark (13 → 4) | Fasta index methylseq (2) · Cat fastq, Fastqc, Trimgalore (3) · Fastq align dedup bismark (7) · Report (1) |
| methylseq, bwa-meth (15 → 5) | Fasta index methylseq (2) · Cat fastq, Fastqc, Trimgalore (3) · Fastq align dedup bwameth (7) · Bam methyldackel (2) · Report (1) |
| toy | Qc (1) · Align (3, with the direct REPORT) |
| synthetic pipeline of T2 (flat) | none: the run shows its processes only |

**Where it is wrong.**
- **The cap merges unrelated neighbours.** On rnaseq: "Align star + Quantify bam salmon". On sarek: "Cram sampleqc + Bam variant calling germline all". Uncapped, rnaseq has 10 stages and sarek 9.
- **Single direct processes land on a neighbour by position, not by data flow.** `STRINGTIE_STRINGTIE` goes into "Bam markduplicates picard", and rnaseq's first `SAMTOOLS_INDEX` into the read QC stage.
- **Names are technical.** "Fastq qc trim filter setstrandedness" and a three-part "Bedgraph bedclip bedgraphtobigwig" are correct but not what a biologist calls a stage.
- **A subworkflow is one stage, even when it does two jobs.** Bismark's subworkflow also extracts methylation (`subworkflows/nf-core/fastq_align_dedup_bismark/main.nf:78`), so the Bismark run has no methylation stage of its own.
- **Stages for tools that never run.** Sarek's "Bam variant calling somatic all" exists in a germline-only test run: its processes are created behind `when:` and run no task, so the stage ends `skipped`.

### Snakemake: where the stage information is

1. **The logger sees rule names only.** `job_info` carries `rule_name` and no file (`snakemake/jobs.py:1072-1075` in the 9.27.1 wheel; record keys in `out/mosaicatcher-v2.5.1_dryrun_events.jsonl`). The rule object does know its file (`Rule.snakefile`, `snakemake/rules.py:121`, `:165`), but that never reaches the logger.
2. **`workflow_started` names the main Snakefile.** It carries `snakefile_main`, `basedir` and `cwd` (`snakemake/workflow.py:289-305`). So the server can find the source for runs it launched and for runs started from a terminal.
3. **The rule graph at start stops at the first checkpoint.** `rulegraph` lists rules in topological order (`snakemake/workflow.py:1222-1236`). On the mosaicatcher dry run it holds 13 rules (47 jobs). The run has two checkpoints in `rules/count.smk` (lines 22 and 181), behind which most of the DAG appears later: "The run involves checkpoint jobs, which will result in alteration of the DAG".
4. **mosaicatcher has no `module`.** ASHLEYS QC comes in as `include:`d rule files under `workflow/rules/ashleys/` when `ashleys_pipeline` is true (`workflow/Snakefile:29-35`). scNOVA is the same, under `scNOVA: True` (`:73-75`). Twenty rule files are included in source order (`:26-75`).

### Snakemake: the detector

The detector is `detector/detect_smk.py` (throwaway). It follows every `include:` with a literal path from `snakefile_main`, conditional ones too, and makes one group per rule file in include order. A rules sub-directory is one group (`ashleys/`), and the main Snakefile's rules (`all`) go last as "Final targets". The cap is 8, and stages are named after the file. Two inputs were compared:

| Input | Result (`out/detector_smk.txt`) |
|---|---|
| Source only, as for a run started from a terminal: 0.05 s | 204 rules in 20 groups, including ASHLEYS (26) and scNOVA (55), which this configuration does not run; capped: Ashleys · External data + Setup + Utils · Count · Segmentation + Plots · Regenotyping + Strandphaser + Breakpointr + Haplotagging + Mosaiclassifier + Postprocessing · Ploidy + Stats + Arbigent rules + Arbigent + Gc · Scnova · Final targets |
| Plus the rules `snakemake --list-rules` defines with the run's configuration, as Spectio can do at launch: 1.4 s | 101 rules in 15 groups; capped: External data · Setup + Utils · Count + Segmentation · Plots · Regenotyping + Strandphaser · Breakpointr + Haplotagging · Mosaiclassifier + Postprocessing + Ploidy + Stats · Final targets |

**Where it is wrong.**
- **Include order is not run order.** `utils.smk` and `plots.smk` come early but hold helper and plotting rules that run late.
- **One file can hold several steps.** `count.smk` holds binning, strand-state filtering and normalisation (README steps 1 to 3).
- **Without the configuration, disabled features show up as stages.** In the source-only case, ASHLEYS and scNOVA appear; they would end `skipped`.

### Declared overlays compared with detection

The four example overlays are in `overlays/`, in the [`checking-scenarios.md`](../specs/checking-scenarios.md) §12.1 shape (`workflow`, `stages[]` with `id`, `name`, `match`), display only. `detector/apply_overlay.py` assigns each name to the stage whose glob matches it, using `fnmatchcase` on the fully qualified Nextflow name or the rule name, and reports overlaps (`out/overlays_vs_detected.txt`):

| Pipeline | Declared stages (processes or rules in this run) | Other | Overlaps |
|---|---|---|---|
| rnaseq, STAR + Salmon | Reference preparation (9) · Read QC and trimming (10) · Alignment (12) · Quantification (13) · Alignment QC and coverage (22) · Report (1) | 0 | none |
| sarek | Reference preparation (5) · Read preparation and QC (12) · Mapping, duplicates and recalibration (11) · Sample QC (4) · Variant calling (11) · Annotation (0) · Variant QC (4) · Report (1) | 0 | none |
| methylseq, Bismark | Reference indexing (2) · Read QC and trimming (3) · Alignment and deduplication (4) · Methylation calling (3) · Coverage QC (0) · Report (1) | 0 | none |
| mosaicatcher | Cell QC (ASHLEYS, optional) (0) · Inputs and references (27) · Binning and strand states (14) · Segmentation (4) · Haplotype resolution (26) · SV classification (12) · Plots and report (18) | 0 | none, after one fix |

What the overlays show:
- **Better names.** The mosaicatcher stage names follow the steps its README lists ("the workflow goes through the following steps", `README.md:18-26`).
- **They can split a subworkflow.** Methylation calling takes the last three Bismark processes; detection cannot do that.
- **They gather direct processes by meaning, not position.** `STRINGTIE_STRINGTIE` goes with Quantification.
- **A declared stage can be empty in a given run.** Examples: Annotation, Coverage QC, Cell QC. It then shows `skipped`, as the API's `run_stages.state` already allows ([`api-and-data-model.md`](../specs/api-and-data-model.md) §7).
- **Writing globs is error-prone.** The first mosaicatcher draft had an overlap (`create_haplotag_likelihoods` matched two stages), and the first methylseq draft left Methylation calling empty. The overlap check of §12.3 caught the first; nothing catches the second, so a preview of an overlay against a real process list is needed.

### Side finding: enabling `nf-spectio` next to an nf-core pipeline

| Way | Result on rnaseq 3.27.0 |
|---|---|
| `-plugins nf-spectio@0.0.1`, as the runner does in [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §13 (0.0.1 prerequisites) and P1 Task 10 | **The run fails.** `-plugins` replaces the config's plugin list (`modules/nf-cli-v1/src/main/groovy/nextflow/config/ConfigCmdAdapter.groovy:351-352`), so the pinned `nf-schema@2.7.2` (`nextflow.config:473-475`) is not declared. The pipeline's `include … from 'plugin/nf-schema'` then starts the latest version, 3.0.0, and the run stops with `Missing process or function paramsSummaryLog(…)`. |
| `-c` file with `plugins { id 'nf-spectio@…' }` | **The run fails** the same way: the `-c` file's list replaces the pipeline's. |
| `$NXF_HOME/config` with the same block, as §13.8 suggests for terminal runs | **The run succeeds without the bridge:** the pipeline's own `plugins {}` wins, and nothing warns. |
| `NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1` | **Works.** Declared `nf-schema@2.7.2`, default `nf-spectio@0.0.1`, both started (`modules/nf-commons/src/main/nextflow/plugin/PluginsFacade.groovy:458-471`, `:543-552`, merge `:621`). Caveat: a list in this variable replaces the plugins Nextflow would infer (for example `nf-amazon` for an `s3://` work dir, `:554-570`). That does not matter on a SLURM cluster with a POSIX work dir. |

Owner: architecture §13 and §13.8, P1 Task 10. Raised as [inbox #69](../reviews/inbox.md#69-nf-spectio-is-enabled-in-a-way-that-breaks-nf-core-runs-or-drops-the-bridge); APPLY6 does not change the mechanism.

## Recommendation for 0.0.1

- **Precedence.** Declared (author `spectio.yml` or lab overlay) beats detected, which beats none, per run ([`ui-spec.md`](../specs/ui-spec.md) §5.1). With none, the run shows its processes or rules only, and the gauge shows task quarters. The processes or rules list is always shown, grouped under stages when there are any, with an "Other" group for names no stage matches.
- **Where detection runs.** On the server, from what the bridges already send, so it works the same for runs Spectio launched and for runs started from a terminal:
  - Nextflow: the `onProcessCreate` names, frozen at `onFlowBegin`, before any task.
  - Snakemake: the rule files under `workflow_started.snakefile_main`, read by the server, which runs as the user on the login node, with storage shared. For runs it launches, Spectio also runs `snakemake --list-rules` with the run's configuration (1.4 s on mosaicatcher) to drop rules this configuration does not define.
- **Algorithm.** As the two detectors above. Nextflow: wrapper and pipeline scopes expanded, one stage per subworkflow, runs of direct calls grouped, aliases merged, Report kept separate. Snakemake: one stage per included rule file or rules sub-directory. Both: at most 8 stages, merging the smallest neighbours, with names humanised from the subworkflow or file name. The `meta.yml` description becomes the stage's description when present. A pipeline with no subworkflow, or a single rule file, gets no detected stages.
- **Order.** Nextflow: creation order, which is source order. Snakemake: the topological order of the start rule graph for the rules it holds, then include order for the rest.
- **Live.** A stage is `running` from its first task, `completed` when its processes are terminated or its rules have no pending job, and `skipped` when it ended with no task. Snakemake stages behind a checkpoint stay `not_started` until their first job.
- **Declared overlays are the way to good names.** 0.0.1 ships the four example overlays as fixtures and as documentation; a lab copies one and edits the globs. Overlays are files in 0.0.1, with no editor.
- **Cost and failure modes.**
  - Detection is a pure function of a name list (Nextflow) or a few file reads (Snakemake): milliseconds.
  - When the Snakemake source cannot be read, or an `include:` path is computed, the rules land in "Other".
  - A Nextflow run whose bridge did not load has no events at all; that is a monitoring failure, not a detection failure (side finding).

## Differences with the specs

| # | Spec text | What the spike found | Change |
|---|---|---|---|
| 1 | [`ui-spec.md`](../specs/ui-spec.md) §5.1: detected = "Nextflow top-level subworkflows from the fully qualified task name" | "Top-level" is two levels down in nf-core (`NFCORE_<P>:<P>:<SUBWORKFLOW>`), and the reference subworkflows sit at the wrapper level. Process names are known at `onProcessCreate`, before any task. | State the wrapper and pipeline-scope rule and the source. |
| 2 | ui-spec §5.1: Snakemake "module prefixes and checkpoints" | The real pipeline has no module. Its structure is in `include:`d rule files. Checkpoints hide the DAG; they do not mark stages. | Rule files and rule sub-directories. |
| 3 | [`api-and-data-model.md`](../specs/api-and-data-model.md) §7 `run_stages`: "frozen at each launch" | Detected Nextflow stages are only known at `onFlowBegin`, after launch but before any task. For a terminal run there is no launch step. | Frozen at the run's first `onFlowBegin` / `workflow_started` for detected stages. |
| 4 | ui-spec §2: 1 to 8 sectors | Uncapped detection gives 10 (rnaseq) and 9 (sarek). | Cap at 8 by merging neighbours. |
| 5 | [`checking-scenarios.md`](../specs/checking-scenarios.md) §12.1: `match` = "globs on process / rule names" | It does not say whether a glob sees `STAR_ALIGN` or the fully qualified name. Only the fully qualified name tells apart `ALIGN_STAR:SAMTOOLS_INDEX` from `RNASEQ:SAMTOOLS_INDEX`. | Globs match the fully qualified name; `*` crosses `:`. |
| 6 | [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) §13, §13.8: `-plugins nf-spectio@<ver>` or `~/.nextflow/config` | Both fail on nf-core pipelines (side finding). | Inbox #69; not changed here. |

## What it changes

APPLY6 (branch `autopilot/apply-stages`) edits the owning specs:
- ui-spec §5.1 owns where stages come from; new §5.1.1 holds the detection rules;
- checking-scenarios §12.1 says what `match` sees;
- api §7 notes when detected `run_stages` freeze;
- dev-env §15.1 gets a 0.0.1 row;
- mvp-0.0.1 §2 gets a row;
- P1 gets a task for the detector with the fixtures;
- the decision log gets an entry;
- inbox #68 and #69.

The fixtures (process lists, rule lists, the four overlays and the expected detector output) move to `tests/pipelines/real/stages/`.

## [to be validated]

- The same names on a real nf-core run with tasks, on SLURM. Only `-preview` and a toy real run were done here.
- The ordering and timing of `onProcessCreate` on Nextflow 25.10.x, the other pinned version. Only 26.10.4 was run.
- Whether `onProcessTerminate` arrives for a process whose upstream channel never closes because of an error. The `skipped` rule depends on it.
- Snakemake: whether `--list-rules` needs input data for other pipelines too, as mosaicatcher's `data_location` check did (here it failed until the test data was present).
- Snakemake: the topological order of rules first seen after a checkpoint (only the start rule graph was read).
- Whether nf-core pipelines with a different template (older `NFCORE_` wrappers, or none) keep the majority rule true. Three pipelines of the 2025–2026 template were tried.
- `NXF_PLUGINS_DEFAULT` on the EMBL cluster's Nextflow and with a site-wide `$NXF_HOME/config`.

## Follow-ups

- P1 task: the detector as a pure function with these fixtures as golden tests (APPLY6).
- An overlay preview that lists each stage's matches and the "Other" names against a captured process list, before saving; it would catch empty or overlapping stages. Later, with the overlay editor.
- Short names for detected stages (a small dictionary of nf-core subworkflow prefixes, for example `ALIGN_`, `QUANTIFY_`, `PREPARE_GENOME`) was considered and not built: it is guesswork per pipeline, and overlays already give good names.
