# Spike — synthetic scenario pipelines on two Nextflow versions and Snakemake (2026-10-26)

**Question.** Can one pair of twin pipelines reproduce, on both engines, every gate and failure scenario that Spectio must handle? Can the stop and resume mechanisms Spectio would generate be verified automatically?

**Answer.** Yes. All 11 PR scenarios pass on Nextflow 26.10.3, Nextflow 25.10.9 and Snakemake 9.27.1, with the local executor.

**Engine faults found:**
- **Snakemake:** one known engine fault, seen in 4 of 18 executions of one scenario. It is handled by a targeted repeat and reported as `PASS*`.
- **Nextflow:** one version difference that changes how timeouts must be classified.

## Setup

- **Machine.** Claude Code cloud session: 2 CPUs, Linux 6.18, Java 21, Docker started by hand (cgroup v1).
- **Engines:**
  - Nextflow 26.10.3 and 25.10.9 (release binaries from GitHub, `NXF_HOME` in the scratchpad);
  - Snakemake 9.27.1 (`uv tool install snakemake==9.27.1`).
- **Code:**
  - `tests/pipelines/synthetic/`: `nextflow/main.nf`, `snakemake/workflow/Snakefile`, `bin/synth.py`;
  - `scenarios.yaml`, run by `run_scenarios.py`.
- **Commands:**

  ```bash
  python3 run_scenarios.py --engine nextflow --nextflow ~/bin/nextflow-26.10.3 --workdir /tmp/sc/nf26
  python3 run_scenarios.py --engine nextflow --nextflow ~/bin/nextflow-25.10.9 --workdir /tmp/sc/nf25
  python3 run_scenarios.py --engine snakemake --workdir /tmp/sc/smk
  ```

## Results (final run, after the fixes below)

| Scenario | NF 26.10.3 | NF 25.10.9 | Snakemake 9.27.1 |
|---|---|---|---|
| happy (65 tasks) | PASS 16.0 s | PASS 15.9 s | PASS 4.1 s |
| gate_qc_then_resume (≥ 25 cached) | PASS | PASS | PASS |
| gate_align_then_resume (≥ 49 cached) | PASS | PASS | PASS |
| exclude_sample_and_resume | PASS | PASS | PASS |
| flaky_retry | PASS | PASS | PASS |
| oom_once_retry | PASS | PASS | PASS* (finding 1) |
| oom_fatal | PASS | PASS | PASS |
| timeout_fatal | PASS 36.8 s | PASS 35.9 s | PASS 25.7 s |
| tool_error_then_fixed_resume | PASS | PASS | PASS |
| dynamic_fanout (45 ALIGN) | PASS | PASS | PASS |
| fanout_medium (180 ALIGN) | PASS 40.7 s | PASS 45.9 s | PASS 12.8 s |

**Where the numbers come from.**
- **Nextflow:** the scratchpad files `final/nf-26.10.3.txt` and `final/nf-25.10.9.txt` (one full run each).
- **Snakemake:** `final2/smk.txt`, a full run after the known-fault rule was added. Its `oom_once_retry` hit the fault, was repeated once, and passed.
  - An earlier full run, made before the rule existed (`final/smk.txt`), failed on that scenario: 10 / 11.
  - A correction: the first version of this note had the two Nextflow columns swapped.

The counts matrix (`quant/counts_matrix.tsv`) is byte-identical between the two engines (`diff`).

## Findings

1. **Snakemake 9.27.1 can lose a retried job when a checkpoint updates the DAG at the same moment.**
   - **What happens.** In `oom_once_retry`, `qc_stats` for S05 fails (137), and Snakemake logs "Trying to restart job 10". `checkpoint split` then finishes, and Snakemake logs "Updating checkpoint dependencies". The restart is never executed. The run ends with "BUG: Out of jobs ready to be started, but not all files built yet. Please check https://github.com/snakemake/snakemake/issues/823".
   - **How often.** 4 of the 18 executions of `oom_once_retry` observed in this session (two full suites, a loop of 8, a loop of 6, and the 2 repeats, both of which passed).
   - **Recovery.** A plain rerun in the same directory completes the run (exit 0, 3 of 3 steps).
   - **Consequences:**
     - **For the tests:** `scenarios.yaml` has an `engine_faults` list. A failed scenario whose logs contain that message is repeated once, from scratch, and reported as `PASS*` with the fault ID. Any other failure fails the build.
     - **For Spectio:** a new failure class, *engine scheduling fault* (`schedulers-and-monitoring.md` §3.5). The suggested action is "rerun"; no resources change.
2. **A local time limit has no exit code on Nextflow 25.10.9.**
   - **25.10.9:** the task's trace status is `FAILED` with exit `-`, the error message is "Process exceeded running time limit (4s)", and `task.exitStatus` is `Integer.MAX_VALUE`. A retry rule that matches only `[137, 140, 143]` does not retry, so `timeout_fatal` saw 1 failed attempt instead of 3.
   - **26.10.3:** the same kill gives exit 143.
   - **Fix in the test pipeline:** retry on `Integer.MAX_VALUE` as well (`nextflow.config`).
   - **For Spectio:** classify timeouts from the trace status and error text, not from the exit code alone.
3. **Nextflow's quiet console output has no "cached" summary line on 25.10.9.** The runner now counts `CACHED` rows in `execution_trace.txt`, which works on both versions. Spectio's ingest also takes cached counts from task records, never from console text.
4. **Nextflow parameters from the command line are strings.** `--chunks 0` is the string `"0"`, which is true in Groovy, so the dynamic fan-out never triggered. The fix is `(params.chunks as int) > 0`. Spectio's launch forms must type parameters from the pipeline schema. The parameters file is JSON, so its types survive.
5. **Snakemake does not format `{resources.attempt}` inside `params`.** The attempt number reached the failure hook as the literal text, so `flaky` and `oom_once` always failed. The fix is to export `SPECTIO_ATTEMPT={resources.attempt}` at the start of every shell command.
6. **Snakemake wildcards need constraints next to directory outputs.** `directory("chunks/{sample}")` also matched chunk files until `wildcard_constraints` restricted `sample` to `[A-Za-z0-9]+`.
7. **The gate mechanisms hold on both engines:**
   - a generated Nextflow config setting `ext.when = false` on later processes, then `-resume`, gives 25 cached tasks after `qc` and 49 after `align`;
   - Snakemake `--until`, then a plain rerun, recomputes nothing upstream.

   This is the mechanism described in `checking-scenarios.md`.

## Not covered here

- **SLURM (sind) and Kubernetes (kind):** this session's cgroup v1 Docker cannot run sind. These legs are steps T3 and T4.
- **Nightly `fanout_stress`** (about 12 000 ALIGN tasks): not run in this session.
- **The rest of the real corpus:** only nf-core/demo was run here (below). The other nf-core and catalog entries are run by `pipelines-real.yml`.

## Addendum: nf-core/demo 1.2.0 with Docker in this session

**Result.** `python3 tests/pipelines/real/run_corpus.py --engine nextflow --name demo --limits auto --nextflow nextflow-26.10.3` → **PASS** in 104 s:
- 8 tasks completed, 0 failed (FASTQC, SEQTK_TRIM, COWPY, MULTIQC);
- outputs: `cowpy`, `fastqc`, `fq`, `multiqc`, `pipeline_info`;
- containers were pulled from quay.io and `community.wave.seqera.io` through the session proxy.

**Two fixes to the corpus runner came out of it:**
1. **Clone with git instead of `nextflow run nf-core/demo -r 1.2.0`.**
   - Nextflow reads the project manifest through the GitHub API. Through the session proxy this gave "Forbidden -- Provide your GitHub user name and password". Unauthenticated API calls are also limited per hour on CI runners **[to be validated: current limit]**.
   - The runner now runs `git clone --depth 1 --branch <version>` and `nextflow run <dir>`.
   - Spectio's launcher should do the same, or pass a token, for pinned releases.
2. **Resource limits must stay below the memory that is free, not the memory that is installed.**
   - With `process.resourceLimits` at 7 GB on an 8 GB machine, COWPY asked for 6 GB and the local executor refused it: "Task requirement exceeds available memory -- req: 6 GB; avail: 5.8 GB". The error is `ProcessUnrecoverableException`, with no exit code.
   - `--limits auto` now uses 80 % of `MemAvailable`, which was 5 GB here.
   - **For Spectio:** the pre-flight check should compare process requests with the target's real headroom (`schedulers-and-monitoring.md` §3.5). This error should be classed as a resource request that cannot be met, not as a tool error.
