# Spike module-run — single-module and single-rule runs (2026-11-10)

Issue [#161](https://github.com/spectio-org/spectio/issues/161). Branch `spike/module-run`, files under `spikes/module-run/`.

**Questions.**

1. Does `nextflow module run` load nf-spectio, from `-plugins` (a driven run) and from `NXF_PLUGINS_DEFAULT` (a run started from a terminal)? **Yes, both.**
2. Which lifecycle events does it fire, does it write a trace, and what run name, session ID and work directory does it report? **The same nine events as a one-process pipeline; `-with-trace` works; a run name and a session UUID are set; the work directory is `./work`.**
3. What identifies the run, when there is no manifest and no commit? **The module's own files: `meta.yml` (name, version) and, for an installed registry module, `.module-info` (checksum, registry).** Nextflow's session has no manifest name, no repository and no commit ID for a module run.
4. On Snakemake 9.x, which jobs are planned for `<rule>`, `--until <rule>` and `--allowed-rules <rule>`? **A rule target and `--until` plan the same jobs (the rule and the jobs it needs); `--allowed-rules` alone plans nothing, and does not prune the DAG of a workflow with a checkpoint.**

**Answer in one line.** Capture works at the Observed level with no new route: nf-spectio sees a module run like a pipeline run, and only needs to say which module it is; Snakemake's logger already receives the command line. Launch can reuse the head script with `nextflow module run` in place of `nextflow run`, `-params-file` included.

Time box: about 60 minutes of work, met. Nothing in the specs was edited by the spike itself.

## Setup

- **Machine.** Claude Code cloud session, Linux 6.18, OpenJDK 21.0.12. No Docker: every run used the `local` executor.
- **Engines,** at the pins of `dev/versions.env`:
  - Nextflow **26.10.4** (the `-dist` asset, `sha256sum -c` against `NEXTFLOW_SHA256`). 26.10.4 is the pin; `module run` was added in 26.04 ([26.04 release post](https://seqera.io/blog/nextflow-26-04), [CLI reference](https://docs.seqera.io/nextflow/reference/cli/module)). 25.10 and 25.04 were not tried: the command does not exist there **[to be validated]** on those builds.
  - Snakemake **9.27.1** with `snakemake-interface-logger-plugins` 2.1.0, in a fresh uv virtual environment.
- **nf-spectio** built by `engine-bridges/nf-spectio/build.sh` into a temporary `NXF_PLUGINS_DIR`, as `run_local.sh` does.
- **Scripts.** `spikes/module-run/nf_module_run.sh OUT_DIR` replays the Nextflow runs; `spikes/module-run/smk_plan.sh RULE` prints the planned jobs. Their recorded outputs are `smk-*.txt` and `fastqc-view.json` next to them.
- **Network.** `registry.nextflow.io` and GitHub were reachable from the session (no host was blocked). Registry access from HPC login and compute nodes stays site-dependent **[to be validated]**.

## Nextflow `module run`

### Commands and help

`nextflow module -h` (26.10.4) lists `create`, `install`, `run`, `list`, `remove`, `search`, `view`, `publish`, `spec`, `validate`. `nextflow module run -h` lists the options of `nextflow run`, including `-plugins`, `-with-trace`, `-with-report`, `-params-file`, `-c`, `-work-dir`, `-profile`, `-resume`, `-name`, `-stub-run`, plus `-version` ("Module version"). `nextflow module view -h` takes `-o json` and `-version`.

### Runs

| # | Module | How | Exit | Events in the spool | Run name / session | Work dir |
|---|---|---|---|---|---|---|
| 1 | local `./modules/spectio/hello` (from `nextflow module create spectio/hello`) | driven: `SPECTIO_*` set, `-plugins nf-spectio@0.0.1 -with-trace -name spk-local` | 0 | `onFlowCreate`, `onProcessCreate`, `onFlowBegin`, `onTaskPending`, `onTaskSubmit`, `onTaskStart`, `onProcessTerminate`, `onTaskComplete`, `onFlowComplete` | `spk-local`, a UUID | `./work/48/60ca15…` |
| 2 | the same | terminal: no `SPECTIO_*`, `NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1` | 0 | the same nine, in `.spectio/events/<run ID>-nf-spectio-0001.jsonl` | a generated name (`hopeful_goldberg`), a UUID | `./work` |
| 3 | registry `nf-core/fastqc`, `-version 0.0.0-6d1763b`, `-stub-run` | driven, inputs `--meta.id test --reads s1.fastq.gz` | 0 | the same nine, process `FASTQC` | `focused_thompson`, a UUID | `./work/54/93b961…` |
| 4 | local, `-resume -c <file> -work-dir <dir> -profile standard`, `NXF_LOG_FILE` set | driven, launch 2 | 0 | `onTaskCached` in place of submit/start/complete; `onFlowCreate.resume = true` | — | the `-work-dir` given |
| 5 | local, script changed to `exit 3` | driven | 1 | `onTaskComplete` (exit 3), `onFlowComplete` (`success: false`), then `onFlowError` | — | — |
| 6 | local and registry, inputs from `-params-file` (`{"greeting": "FromFile"}`, `{"meta": {"id": "pj"}, "reads": "s1.fastq.gz"}`) | plain | 0 | — | — | — |
| 7 | registry, `-version 9.9.9` | plain | non-zero | none: "Unable to install module: nf-core/fastqc" before the session starts | — | — |

Findings:

1. **Plugins load** from both `-plugins` and `NXF_PLUGINS_DEFAULT` (`.module.log`: "Plugins declared=[nf-spectio@0.0.1]" and "Plugins default=[nf-spectio@0.0.1]"). The terminal pointer route of architecture §13.8 needs no change.
2. **The trace works** (`-with-trace` wrote `trace-<date>.txt` with the task's row). `-with-report` was not run **[to be validated]**.
3. **The log file is `.module.log`**, not `.nextflow.log`, unless `NXF_LOG_FILE` is set; with it set (as the head script does), the log goes there. The launcher line is `$> nextflow module run …`.
4. **Outputs are printed, not published.** The run prints an `Outputs:` block with work-directory paths (`html: …/work/54/93b961…/test.html`) and writes nothing outside `work/`; nf-spectio sees no `onFilePublish`. This matches the [Using modules](https://docs.seqera.io/nextflow/modules/using-modules) page.
5. **A registry module is installed into the launch directory**, `./modules/nf-core/fastqc/`, with `meta.yml`, `main.nf`, `environment.yml`, `.conda-lock/` and `.module-info`. `.module-info` holds `checksum=b64b18ed…173a` (64 hex characters) and `registryUrl=https://registry.nextflow.io/api`. A local module made by `module create` has an empty `.module-info`.
6. **No version given** (`nextflow module run nf-core/fastqc` with the module already installed) ran the installed copy; which version it would download when none is installed is **[to be validated]**. A version that does not exist fails before any event (run 7): a Spectio launch with a bad version ends with no `onFlowCreate`, so the runner's `head_lost` / exit-code path applies.
7. **What the session says** (a probe build of nf-spectio that also sent session fields, `onFlowCreate`, both runs 1 and 3): `commandLine` is the full command (`nextflow module run nf-core/fastqc -version 0.0.0-6d1763b …`); `workflowMetadata.scriptFile` is the module's `main.nf` (`<launch>/modules/nf-core/fastqc/main.nf` for the registry module); `projectName` is `main.nf`; `repository`, `revision`, `commitId`, `manifest.name` and `manifest.version` are **null**; `scriptId` is set (an MD5); `params` holds the input names (`[meta, reads]`).
8. **`-params-file` carries the inputs**, nested maps included (run 6): the head script's `params.json` works for a module run unchanged.
9. **`nextflow module view -o json <name>`** prints `name`, `fullName`, `version`, `kind`, `url`, `description`, `componentName`, `authors`, `keywords`, `tools`, `input`, `output`, `usageTemplate` (`fastqc-view.json`). `input` is a list of items, each a named input or a `tuple` of named items with a `type` (`map`, `file`, `string`…). For a local module not in the registry it prints "Failed to fetch metadata from registry" and "No release information available".

### What follows for Spectio

- **Detect a module run** in nf-spectio at `onFlowCreate`: the command line's words after the launcher are `module run`. Send a `target` with the module's name and version from `meta.yml` next to `scriptFile`, the checksum from `.module-info` when set, else the session's `scriptId` as the hash of a local module. Nothing else changes in the plugin.
- **Identity.** `namespace/name@version` for a registry module, with the checksum shown and kept; for a local module, its path and the script hash, so a changed file is a new version of the same target (answers open question 2 of #161).
- **Launch.** The head script's `nextflow run <location>` becomes `nextflow module run <name> -version <v>` (registry) or `nextflow module run <absolute path>` (local), keeping `-params-file`, `-c`, `-work-dir`, `-profile`, `-resume` and the environment. The version is always given, so "latest" never runs unseen (#161 §D).

## Snakemake 9.27.1, one rule

`smk_plan.sh RULE` runs `snakemake -n` on `tests/pipelines/synthetic/snakemake/workflow/Snakefile` from an empty working directory. `smk-after-run.txt` is the same after a real run of `qc_report`.

| Flags | `qc_report`, empty dir | `merge`, empty dir | `qc_report`, after a run |
|---|---|---|---|
| `<rule>` | 25 jobs: `make_reads` 12, `qc_stats` 12, `qc_report` 1 | 4 jobs: `make_reads`, `split`, `align_done`, `merge` (the DAG is cut at the `split` checkpoint) | nothing to be done |
| `--until <rule>` | the same 25 | the same 4 | — |
| `--allowed-rules <rule>` | "Nothing to be done" (the default target `all` is not allowed) | "Nothing to be done" | — |
| `<rule> --allowed-rules <rule>` | the same 25 | the same 4 | — |
| `<rule> --force` | — | — | 1 job: `qc_report` |
| `--until <rule> --force` | — | — | 3 jobs: `make_reads`, `qc_stats`, `qc_report` (one sample: `make_reads` is `temp`) |
| `--forcerun <rule>` | 32 jobs: the whole default DAG | 32 | — |

Findings:

1. **A rule target and `--until` plan the same jobs** here: the rule plus the jobs it needs. This confirms spike T1 for `--until` (`cli.py` L892-L902).
2. **`--allowed-rules` does not do "this rule only" on this corpus.** `workflow.py:879-892` (9.27.1): when any rule is a checkpoint, the DAG keeps every rule and `allowed_rules` only limits which jobs may need to run; here the needed jobs were still planned. Its FAQ calls it a debugging option ([FAQ](https://github.com/snakemake/snakemake/blob/v7.12.1/docs/project_info/faq.rst)). Spectio does not offer it.
3. **"This rule only"** is `<rule> --force` once its inputs exist; with missing inputs, the needed jobs run. The preview (a dry run) is what tells the user which.
4. **The logger already has the command line.** `Workflow.execute` logs `WORKFLOW_STARTED` with `**self.info_header`, whose `cmd` is `" ".join(sys.argv)` (`workflow.py:271-296`, `1291-1297`, 9.27.1). The Spectio logger reads the targets and the `--until` / `--allowed-rules` / `--forcerun` values from it; it is not in the plugin's allow-list today.
5. **`--list-rules`** prints the rule names one per line (`all`, `align`, … `split`), as the head script already uses it (P1 Task 27).
6. **Gates.** Spectio's stage gates stop a Snakemake run with `--until` ([checking-scenarios §12.3](../specs/checking-scenarios.md#123-stage-boundaries), synthetic `gate_*` scenarios). A target run carries its own target flag, so the two cannot both be on one launch: a target run has no gates (#161 §D).

## Differences with the issue

| # | Issue says | Spike found |
|---|---|---|
| 1 | Whether plugins load is unknown | They load from `-plugins` and `NXF_PLUGINS_DEFAULT` |
| 2 | Run name and session ID unknown | Both set, as for `nextflow run` |
| 3 | Capture may need a trace-file or log route | Not needed; but the log is `.module.log` when `NXF_LOG_FILE` is not set |
| 4 | Identity: `.module-info` checksum for an installed module | Confirmed: `checksum=` and `registryUrl=`; empty for a local module |
| 5 | `--allowed-rules` limits a run to one rule | Not with a checkpoint in the workflow (`workflow.py:879-892`) |

## Still open

- `module run` on Nextflow 25.10 and 25.04 (the floor): expected absent **[to be validated]**.
- A named workflow module (`-kind Workflow`): not run **[to be validated]**.
- `-with-report` and `-with-timeline` on a module run **[to be validated]**.
- What `module run` without `-version` downloads when nothing is installed **[to be validated]**.
- Registry reachability from HPC nodes **[to be validated]**, for the pre-flight check of open question 4.
