# Stage detection spike — log (2026-10-28)

Machine: Claude Code cloud session, Linux 6.18, OpenJDK 21, no Docker. Nextflow 26.10.4,
Snakemake 9.27.1. Time box about 90 minutes, met.

## 1. Clones

`git clone --depth 1 -b <tag>`: rnaseq 3.27.0 `a1fcdddd3b82`, sarek 3.11.0 `6e9b164daa2a`,
methylseq 4.2.0 `5aa56467a85a`, mosaicatcher-pipeline v2.5.1 `2289f7cc8ef2`, nextflow v26.10.4
`691b8210065a`. Mosaicatcher test data: `git submodule update --init --depth 1 .tests` → `3ba566888edf` (215 MB).

## 2. Loading the bridge next to an nf-core pipeline (dead ends first)

| Attempt | Result |
|---|---|
| `-plugins nf-spectio@0.0.1` | **Run fails.** `-plugins` replaces the config's plugin list (`ConfigCmdAdapter.groovy:351-352`), so rnaseq's `nf-schema@2.7.2` (`nextflow.config:473-475`) is not declared; the `include … from 'plugin/nf-schema'` then auto-starts the latest, 3.0.0, and the run stops: `Missing process or function paramsSummaryLog(…)` (`.nextflow.log`: `Plugins declared=[nf-spectio@0.0.1]`, `Start plugin 'nf-schema@3.0.0'`). |
| `-c spectio-bridge.config` with `plugins { id 'nf-spectio@0.0.1' }` | **Same failure:** the `-c` file's list replaces the pipeline's (`Plugins declared=[nf-spectio@0.0.1]`). |
| `$NXF_HOME/config` with the same block | **Run succeeds, bridge silently absent:** the pipeline's own list wins (`Plugins declared=[nf-schema@2.7.2]`, no `nf-spectio`). |
| `NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1` | **Works:** `Plugins declared=[nf-schema@2.7.2]`, `Plugins default=[nf-spectio@0.0.1]`, `resolved requirement=[nf-schema@2.7.2, nf-spectio@0.0.1]` (`PluginsFacade.groovy:458-471`, `543-552`, `621`). Caveat: a list in that variable replaces the defaults Nextflow infers from the config (`nf-amazon` for an `s3://` work dir, `nf-k8s`…, `PluginsFacade.groovy:554-570`). |

## 3. Nextflow captures

| Run | Command (all `-preview -profile test --outdir results -with-dag dag.mmd`) | Exit | `onProcessCreate` |
|---|---|---|---|
| rnaseq 3.27.0, STAR + Salmon (default) | `preview.sh $SRC/rnaseq …` | 0 | 67 |
| rnaseq 3.27.0, HISAT2 | `… --aligner hisat2` | 0 | 62 |
| sarek 3.11.0 (`tools = 'strelka'`, `conf/test.config:47`) | `preview.sh $SRC/sarek …` | 0 | 48 |
| methylseq 4.2.0, Bismark | `NXF_SYNTAX_PARSER=v1 … --input <data>/ms.csv --aligner bismark` | 0 | 13 |
| methylseq 4.2.0, bwa-meth | `NXF_SYNTAX_PARSER=v1 … --input <data>/ms.csv --aligner bwameth` | 0 | 15 |
| toy (real run, not preview) | `NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 nextflow run nextflow/toy -with-trace` | 0 | 4 |

- methylseq 4.2.0 needed two workarounds: the v2 config parser refuses `includeConfig 'conf/aws/batch/nextflow.config'`
  (`nextflow.config:251`), a file absent from the tag, so `NXF_SYNTAX_PARSER=v1`; and its test samplesheet
  points to a test-data URL that the schema check reports as missing, so a local samplesheet with three
  empty `.fastq.gz` files (`<data>/ms.csv`). Neither touches process naming.
- `-preview` runs the script, so `onProcessCreate` fires for every process, then `onFlowBegin`, then
  `onFlowComplete`; no task. In the rnaseq preview, 41 s from `onFlowCreate` to `onFlowBegin`, 14 s of which
  between the first `onProcessCreate` and `onFlowBegin`.
- `dag.mmd` keeps one `subgraph "<fully qualified scope> [<name>]"` per workflow scope: 25 in rnaseq.
- Toy real run: the trace file `name` column and the bridge's `process` are the fully qualified names
  (`NFCORE_TOY:TOY:QC:QC_INNER:STEP (s1)`); the `when: false` process is created, gets
  `onProcessTerminate`, and has no task.

## 4. Nextflow detector

v0 (not kept) attached every direct process to the group before it, across
wrapper scopes: rnaseq's `SAMTOOLS_INDEX` landed in "Prepare genome indices", methylseq's
`CAT_FASTQ, FASTQC, TRIMGALORE` in "Fasta index methylseq", sarek's three `SPRING_DECOMPRESS_*` in
"Prepare intervals", and the cap merged "Report" into the previous stage. v1 (committed) fixes these with
runs of direct calls, the same-parent rule and a protected Report group. Output: `out/detector_nf.txt`.
`out/fallback_no_manifest.txt`: without the manifest name, "the child of the wrapper holding more than half
of the processes" picks the same pipeline scope on all five captures.

## 5. Snakemake (mosaicatcher v2.5.1)

- `snakemake --list-rules` with the default config fails: `config/config.yaml:20` points `data_location` to
  `.tests/data_CHR17`, a submodule. After fetching it: 101 rules (1.4 s). With
  `--config ashleys_pipeline=True scNOVA=True` it fails again (needs FASTQ inputs); not pursued.
- Dry run `snakemake -n --configfile .tests/config/simple_config_mosaicatcher.yaml`: exit 0, 47 jobs of 12 rules
  plus `all`, and "The run involves checkpoint jobs, which will result in alteration of the DAG"
  (`out/mosaicatcher-v2.5.1_dryrun.txt`).
- The same dry run with `--logger spectio` (`PYTHONPATH=snakemake`): `workflow_started` carries
  `snakefile_main`; `rulegraph` holds 13 rules, in topological order; `job_info` carries `rule_name`, no
  file (`out/mosaicatcher-v2.5.1_dryrun_events.jsonl`, trimmed to those records).
- Static parse of the rule files: 0.05 s; 204 distinct rules in 20 files (scNOVA's 55 and ASHLEYS' 26
  included: their includes are conditional). `out/detector_smk.txt`.
- No `module` statement in the pipeline (`grep -rn '^module\|use rule' workflow` is empty): ASHLEYS QC is
  included as rule files under `workflow/rules/ashleys/` (`workflow/Snakefile:29-35`), not imported as a module.

## 6. Overlays

`out/overlays_vs_detected.txt`. First mosaicatcher draft had an overlap (`create_haplotag_likelihoods` matched
`*haplotag*` in "Haplotype resolution" and its own name in "SV classification"); fixed by listing names.
First methylseq draft left "Methylation calling" empty on Bismark: the Bismark subworkflow also runs
`BISMARK_METHYLATIONEXTRACTOR` (`subworkflows/nf-core/fastq_align_dedup_bismark/main.nf:78`); fixed by
splitting the subworkflow's processes between two declared stages.
