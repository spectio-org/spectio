# Real-pipeline corpus and CI actions — research for Spectio

Date: 2026-10-26. Clones are in `scratchpad/ext/` (`smk-*`, `nfc/`, `act/`).
- **Tags** were read with `git ls-remote --tags`.
- **nf-core configs** were fetched from `raw.githubusercontent.com/nf-core/<p>/<tag>/conf/test.config` and `nextflow.config`.
- **Action inputs** come from each action's `action.yml` at HEAD.

## 1. Snakemake Workflow Catalog

**About the catalog.** Its data lives in `snakemake/snakemake-workflow-catalog/data.json`: 6,541 repositories, 472 of them marked `standardized: true` (field `standardized`).

**Standard test pattern.** Workflows in the `snakemake-workflows` organisation follow one pattern:
- the tests live in `.test/`, with its own `config/`;
- data comes either from a git submodule (`snakemake-workflows/ngs-test-data`) or from files kept in `.test`;
- CI uses `snakemake/snakemake-github-action@v2` with `directory: .test` and conda software deployment;
- most of them also run `--lint` and generate a report (`--report report.zip`).

| Workflow | Latest tag | Modality | CI test command (from `.github/workflows/main.y*ml`) | Test data | `.test` size |
|---|---|---|---|---|---|
| snakemake-workflows/rna-seq-star-deseq2 | v3.1.2 | bulk RNA, groups (DESeq2 designs) | `directory: .test`, `snakefile: workflow/Snakefile`, `--conda-cleanup-pkgs cache --software-deployment-method conda --show-failed-logs --cores 8` + matrix `--configfile .test/config_basic\|config_complex\|config_sra/config.yaml`; report step `--cores 1 --report report.zip` (main.yml:93–113) | submodule `.test/data` → github.com/snakemake-workflows/ngs-test-data (`.gitmodules`); `config_sra` downloads from SRA and frees disk first (main.yml:72) | 17 MB |
| snakemake-workflows/dna-seq-varlociraptor | v6.11.3 | small and structural variants, groups/pairs | `directory: .test`, `--conda-cleanup-pkgs cache --sdm conda --resources mem_mb=16000 --cores 10 <case args>`; matrix of configs (`config-simple`, `config-sra`, `config-chm-eval`, `config-giab`, `config-pangenome-small`, `config-no-candidate-filtering`); report `--sdm conda --cores 1 --report report.zip` (main.yml:120–135) | in repo (`.test/*.fq`) + SRA/GIAB downloads for some cases | 14 MB |
| snakemake-workflows/rna-seq-kallisto-sleuth | v4.1.1 | bulk RNA (and 3′ RNA) | `directory: .test` and `.test/three_prime`, `--use-conda --show-failed-logs --cores all --conda-cleanup-pkgs cache --all-temp` (main.yml:94–131) | submodule ngs-test-data | 80 KB (+ submodule) |
| snakemake-workflows/dna-seq-gatk-variant-calling | v2.1.1 | germline variants (GATK) | `directory: .test`, `--use-conda --show-failed-logs --cores 1 --conda-cleanup-pkgs cache` (main.yml:47–52) | in repo `.test/data` | 13 MB |
| snakemake-workflows/single-cell-rna-seq | v1.1.0 | single-cell (counts → QC) | `directory: .test`, `--use-conda --show-failed-logs` (main.yml:46–50; old action `@master`) | in repo (`.test/counts.tsv`, `cells.tsv`) | 5.2 MB |
| snakemake-workflows/chipseq | no tag | ChIP-seq | `directory: .test`, `--configfile .test/config_single_end_reduced/config.yaml` (and `config_paired_end_reduced`) `--use-conda --cache --show-failed-logs -j 10 --conda-cleanup-pkgs cache --conda-frontend mamba` (main.yaml:40–74; action v1.19.0) | submodules → github.com/nf-core/test-datasets | 26 MB |
| snakemake-workflows/cyrcular-calling | v2.1.1 | long reads (ONT), circular DNA | `directory: .test`, `--configfile .test/config/config.yaml --use-conda --show-failed-logs -j 10 --conda-cleanup-pkgs cache`; report `--cores 2 --report report.zip` (main.yaml:47–58) | in repo | 704 KB |
| MPUSP/snakemake-ms-proteomics | v1.1.1 | MS proteomics | reusable workflow `MPUSP/mpusp-github-actions/.github/workflows/snakemake-tests.yml@main` with `cores: 2`, `dryrun: true` (snakemake-tests.yml); **CI runs a dry-run only** | in repo `.test/data` | 1.7 MB |
| MathiasEskildsen/ONT-AmpSeq | v1.1.2 | ONT amplicon → OTU tables | `directory: .test`, `snakefile: workflow/Snakefile`, `--use-conda --show-failed-logs --cores 3 --conda-cleanup-pkgs cache --all-temp` (main.yml:43–49; action v1.24.0) | in repo `.test/test_data`, `databases` | 8.7 MB |
| IKIM-Essen/RiboSnake | v0.11.0 | 16S amplicon (QIIME2) | CI downloads SILVA from data.qiime2.org and the **full GRCh38** from NCBI before running (main.yaml:66–90) | downloads | 84 KB |

**Notes.**
- `epigen/atacseq_pipeline` (v2.1.0) and `epigen/scrnaseq_processing_seurat` (v3.0.9) are standardized but ship no `.github/workflows`. The atacseq one has no `.test` either; scrnaseq has `test/config`, `test/data`. They are not CI-proven.
- RiboSnake is too heavy for PR CI because of the genome download. Use it nightly with a cache, or drop it.
- Several workflows use old action majors (`@v1.x`, `@master`). The current major is `snakemake/snakemake-github-action@v2` (latest tag v2.1.2).

## 2. nf-core pipelines (test profiles)

**Source.**
- Versions come from `research/pipelines.json` (field `remote_workflows[].releases`).
- `conf/test.config` and `nextflow.config` come from the tag.
- The `resourceLimits` shown are the profile's `process.resourceLimits`.
- Data comes from `nf-core/test-datasets` (`params.pipelines_testdata_base_path` = `https://raw.githubusercontent.com/nf-core/test-datasets/<branch>/`).

| Pipeline | Latest | Class (checking-scenarios §1) | test profile: limits · key params | Min Nextflow | Fits GH runner? | What Spectio gates |
|---|---|---|---|---|---|---|
| demo | 1.2.0 | run only | 2 CPU, 4 GB, 1 h; input = viralrecon amplicon samplesheet (test-datasets `viralrecon/samplesheet/samplesheet_test_illumina_amplicon.csv`) | ≥25.10.4 | yes (PR) | FastQC + MultiQC → sample gate (minimal) |
| fetchngs | 1.13.0 | run only | 4 CPU, 15 GB, 1 h; `sra_ids_test.csv` (pinned commit 2732b91) | ≥25.10.4 | yes, needs ENA/SRA network | run-level check only |
| rnaseq | 3.27.0 | bulk samples, groups | test-datasets commit 626c8fa: `samplesheet/v3.10/samplesheet_test.csv`, genome.fasta, `genes_with_empty_tid.gtf.gz`, `hisat2.tar.gz`, `salmon_2.7.0.tar.gz`, kraken2 sarscov2 db (lines 1–40) | ≥25.10.4 | yes (nf-core's own CI runs it) | "Mapping QC" after alignment + MultiQC (the R6 example), exclude a sample and resume |
| sarek | 3.10.0 | sample in groups (variants) | 4 CPU, 15 GB, 2 h; `tests/csv/3.0/fastq_single.csv`, `genome = testdata.nf-core.sarek`, igenomes_base = test-datasets modules | ≥25.10.4 | yes | coverage gate after BAM QC (mosdepth), tumour/normal pairing check |
| scrnaseq | 4.2.0 | cells (massive) | 4 CPU, 15 GB, 1 h; `samplesheet-2-0.csv`, GRCm38 chr19, `aligner = star`, `protocol = 10XV2`, `skip_cellbender`, `skip_qcatch` | ≥25.10.4 | yes | cell thresholds (n_genes, counts, pct_mt) per sample |
| mag | 5.5.0 | bins (many) | 4 CPU, 15 GB, 1 h; `samplesheet.multirun.v4.csv`, BUSCO bacteria_odb10, GTDB mock-up db; several binners skipped | **≥26.04.0** | heavy → nightly | MIMAG rule on bins (completeness / contamination) |
| ampliseq | 3.0.0 | bulk / taxa | 4 CPU, 15 GB, 1 h; `Samplesheet_v3.tsv` | **≥26.04.0** | yes, downloads databases → nightly or cache | per-sample read retention after DADA2 |
| taxprofiler | 2.0.1 | features / taxa | 4 CPU, 15 GB, **6 h**; `taxprofiler/samplesheet.csv`, `database_v2.1.csv`, host removal on human test genome | ≥25.10.4 | nightly | host-read fraction, contaminant taxa |
| viralrecon | 3.0.0 | assembly / consensus | 4 CPU, 15 GB, 1 h; `samplesheet_test_amplicon_illumina.csv`, `protocol = amplicon`, genome MN908947.3, kraken2 hs22 db | ≥25.04.0 | yes | per-sample coverage / consensus Ns |
| methylseq | 4.2.0 | bulk samples | 4 CPU, 15 GB, 1 h; `assets/samplesheet.csv`, test genome.fa.gz | ≥25.04.0 | yes | bisulfite conversion rate / coverage |
| mhcquant | 3.3.0 | MS runs (proteomics) | 2 CPU, 6 GB, 2 h; `HepG2_sample_sheet.tsv`, UP000005640_9606.fasta | ≥25.10.4 | yes | identification rate / FDR per MS run |
| mcmicro | 2.0.0 | image → cells | 4 CPU, 15 GB, 1 h (some processes 12 GB); `assets/samplesheet-test.csv` | ≥25.04.0 | heavy images → nightly | segmentation QC per image / ROI |
| molkart | 1.2.0 | image / spots | 1 CPU, 4 GB, 1 h; `molkart/test_data/samplesheets/samplesheet_membrane.csv` | ≥25.04.0 | yes | spot / segmentation counts |
| differentialabundance | 2.0.0 | groups (contrasts) | default limits; downstream of rnaseq | ≥25.10.4 | yes | contrast sanity (samples per group) |

**Version conflict.** `mag` 5.5.0 and `ampliseq` 3.0.0 require Nextflow **≥ 26.04.0**; the others accept ≥ 25.10.4. So the "old" leg of the Nextflow matrix (25.10.x) must skip those two.

**Private repository runners.**
- Standard GitHub-hosted Linux runners have **4 CPU / 16 GB / 14 GB SSD for public repositories** but **2 CPU / 8 GB / 14 GB for private repositories** ([GitHub docs](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)).
- While `weber8thomas/spectio` is private, the 15 GB test profiles need a resource override (`process.resourceLimits = [cpus: 2, memory: 7.GB]`), a self-hosted runner (the staging VM), or larger paid runners.

## 3. GitHub Actions (verified inputs)

| Action | Latest tag | Inputs that matter | Source |
|---|---|---|---|
| `nf-core/setup-nextflow` | v3.0.1 | `version` (default `latest-stable`), `all`, `install-java`, `java-version`, `java-distribution` | action.yml |
| `GSI-HPC/sind-action` | v2.2.0 | `version` (default latest, min v0.8.0), `clusters` (YAML list of config paths or inline configs), `pull`, `wait`, `realm` (isolation for parallel jobs), `verify` (attestation via `gh`); cleanup step `GSI-HPC/sind-action/cleanup@v2` | action.yml, README "Usage" |
| `snakemake/snakemake-github-action` | v2.1.2 | `directory`, `snakefile`, `args`, `stagein`, `task` (run / containerize), `snakemake-version` (default latest; pin it), `install-apptainer`, `show-disk-usage-on-error` | action.yml |
| `prefix-dev/setup-pixi` | v0.11.2 | `pixi-version`, `manifest-path`, `environments`, `cache`, `locked`, `frozen` (alternative to conda for Snakemake itself) | action.yml |
| `helm/kind-action` | v1.15.1 | `version`, `config`, `node_image`, `cluster_name`, `kubectl_version`, `registry`, `install_only` | action.yml |
| `googleapis/release-please-action` | v5.0.0 | `token`, `release-type`, `config-file`, `manifest-file`, `target-branch`, `skip-github-release`, `versioning-strategy`, `release-as` | action.yml |
| `tailscale/github-action` | v4.3.0 (node24) | `oauth-client-id` + `oauth-secret` (OAuth client needs the `auth_keys` scope and must own the tags), or `audience` for OIDC federated identity; `tags`; `ping` (verify connectivity); `hostname`; `use-cache` | action.yml |
| `docker/metadata-action` | v6.2.0 | `images`, `tags`, `flavor`, `labels`; tag types `type=semver,pattern={{version}}`, `{{major}}.{{minor}}`, `type=sha`, `type=edge` (default branch), `type=ref,event=pr`, `type=raw`, `type=schedule` | README §tags |
| `anthropics/claude-code-action` | v1.0.262 (major v1) | `prompt`, `claude_args`, `claude_code_oauth_token` or `anthropic_api_key`, `trigger_phrase`, `label_trigger`, `settings`, `allowed_bots`, `additional_permissions`; set up with `/install-github-app` from Claude Code | action.yml, README l.18, 26 |

**Snakemake on CI.** The action installs Snakemake into a conda environment inside the job, and `snakemake-version` pins it. An alternative is a pixi environment (`setup-pixi`) plus `snakemake --sdm conda`, which also works locally and in cloud sessions.

**sind requirements.** It needs a rootful Docker daemon on unified cgroup v2, `bash`, `curl`, `jq`, `yq` v4 and `gh` ≥ 2.93 for attestation. GitHub Ubuntu runners meet all of these (sind-action README "Requirements"). This cloud session's Docker reports **cgroup v1**, so sind is unlikely to run here; it is to be checked in spike D2.

**release-please.**
- Manifest mode uses `release-please-config.json` and `.release-please-manifest.json` (docs/manifest-releaser.md l.4–54).
- `release-type: python` exists (docs/customizing.md l.23).
- The `linked-versions` plugin keeps several components on one version (manifest-releaser.md l.587–623).
- `extra-files` with the generic YAML updater bumps `version:` in files such as `Chart.yaml` (customizing.md l.252–264).
- Many catalog workflows already use it (`release-please.yml` in rna-seq-star-deseq2, varlociraptor, kallisto-sleuth, cyrcular, ms-proteomics).

## 4. Versions to pin

| Tool | Pin | Source |
|---|---|---|
| Nextflow (current) | **26.10.3** (latest tag); 26.04.9 is the last of the 26.04 line | `git ls-remote --tags nextflow-io/nextflow` |
| Nextflow (previous, matrix leg) | **25.10.9** — satisfies `!>=25.10.4` but not mag/ampliseq (`!>=26.04.0`) | same; nf-core `nextflow.config` manifests |
| Snakemake | **9.27.1** (2026-10-21) | PyPI JSON |
| snakemake-executor-plugin-slurm | **2.8.0** | PyPI JSON |
| Java | 21 (present locally; Nextflow dist runs on it) | local `java -version` |

## 5. Machine-readable corpus

```yaml
nextflow_versions: {current: "26.10.3", previous: "25.10.9"}
snakemake_version: "9.27.1"
nfcore:
  - {name: demo, version: 1.2.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, gate: "after MULTIQC: sample QC"}
  - {name: fetchngs, version: 1.13.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, network: [ena, sra], gate: "run-level"}
  - {name: rnaseq, version: 3.27.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, gate: "Mapping QC after alignment; exclude sample + resume"}
  - {name: sarek, version: 3.10.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, gate: "coverage after mosdepth; pairing"}
  - {name: scrnaseq, version: 4.2.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, gate: "cell thresholds"}
  - {name: viralrecon, version: 3.0.0, profile: "test,docker", min_nf: 25.04.0, tier: pr, gate: "coverage / consensus"}
  - {name: methylseq, version: 4.2.0, profile: "test,docker", min_nf: 25.04.0, tier: pr, gate: "conversion rate"}
  - {name: mhcquant, version: 3.3.0, profile: "test,docker", min_nf: 25.10.4, tier: pr, gate: "identification rate per MS run"}
  - {name: molkart, version: 1.2.0, profile: "test,docker", min_nf: 25.04.0, tier: pr, gate: "spot / segmentation counts"}
  - {name: differentialabundance, version: 2.0.0, profile: "test,docker", min_nf: 25.10.4, tier: nightly, gate: "samples per contrast"}
  - {name: mag, version: 5.5.0, profile: "test,docker", min_nf: 26.04.0, tier: nightly, gate: "MIMAG bins"}
  - {name: ampliseq, version: 3.0.0, profile: "test,docker", min_nf: 26.04.0, tier: nightly, gate: "read retention after DADA2"}
  - {name: taxprofiler, version: 2.0.1, profile: "test,docker", min_nf: 25.10.4, tier: nightly, gate: "host fraction / contaminants"}
  - {name: mcmicro, version: 2.0.0, profile: "test,docker", min_nf: 25.04.0, tier: nightly, gate: "segmentation QC per ROI"}
snakemake_catalog:
  - {repo: snakemake-workflows/rna-seq-star-deseq2, tag: v3.1.2, submodules: true, directory: .test, args: "--sdm conda --cores 2 --configfile .test/config_basic/config.yaml", tier: pr}
  - {repo: snakemake-workflows/rna-seq-kallisto-sleuth, tag: v4.1.1, submodules: true, directory: .test, args: "--sdm conda --cores 2 --all-temp", tier: pr}
  - {repo: snakemake-workflows/dna-seq-gatk-variant-calling, tag: v2.1.1, submodules: false, directory: .test, args: "--sdm conda --cores 2", tier: pr}
  - {repo: snakemake-workflows/dna-seq-varlociraptor, tag: v6.11.3, submodules: false, directory: .test, args: "--sdm conda --cores 2 --resources mem_mb=7000", tier: nightly}
  - {repo: snakemake-workflows/single-cell-rna-seq, tag: v1.1.0, submodules: false, directory: .test, args: "--sdm conda --cores 2", tier: nightly}
  - {repo: snakemake-workflows/chipseq, tag: main, submodules: true, directory: .test, args: "--configfile .test/config_single_end_reduced/config.yaml --sdm conda --cores 2", tier: nightly}
  - {repo: snakemake-workflows/cyrcular-calling, tag: v2.1.1, submodules: false, directory: .test, args: "--configfile .test/config/config.yaml --sdm conda --cores 2", tier: nightly}
  - {repo: MathiasEskildsen/ONT-AmpSeq, tag: v1.1.2, submodules: false, directory: .test, args: "--sdm conda --cores 2 --all-temp", tier: nightly}
  - {repo: MPUSP/snakemake-ms-proteomics, tag: v1.1.1, submodules: false, directory: .test, args: "--sdm conda --cores 2 -n", tier: pr, note: "upstream CI is dry-run only"}
actions:
  setup_nextflow: nf-core/setup-nextflow@v3
  sind: GSI-HPC/sind-action@v2
  snakemake: snakemake/snakemake-github-action@v2
  pixi: prefix-dev/setup-pixi@v0.11
  kind: helm/kind-action@v1
  release_please: googleapis/release-please-action@v5
  tailscale: tailscale/github-action@v4
  docker_metadata: docker/metadata-action@v6
  claude: anthropics/claude-code-action@v1
runners: {public: "4 CPU / 16 GB / 14 GB", private: "2 CPU / 8 GB / 14 GB"}
```
