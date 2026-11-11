# Module-run fixtures

Engine answers captured by the spike `module-run` on 2026-11-10
(`spikes/module-run/`, note: `docs/research/spike-module-run-2026-11-10.md`), copied here so that
the tests do not read the throwaway spike directory.

- `fastqc-view.json`: `nextflow module view -o json nf-core/fastqc`.
- `smk-merge-empty.txt`: `snakemake -n merge`, then `snakemake -n --until merge`, in an empty
  directory (`spikes/module-run/smk_plan.sh merge`).

Used by `packages/spectio-server/tests/api/test_targets.py`.
