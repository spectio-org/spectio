# Progress

Every step of the [pre-implementation pipeline](../playbooks/autopilot.md) writes its own page here while it runs: what changed, why, the evidence, figures and media, and the findings it filed. A step is `done` only once its page has passed the docs gate ([documentation system §3.3](../specs/documentation-system.md#33-the-docs-gate-run-by-autopilot-after-every-step-and-by-ci-on-every-pr)).

This page is generated at build time from `docs/playbooks/pipeline.yaml` and `.autopilot/state.json`.

<!-- spectio:progress-table -->

## Steps outside the pipeline

- [APPLY4 · Apply Thomas's 2026-10-28 answers on cluster access](W4/APPLY4.md): PR #47 and the fixes of its doc review (running).
- [APPLY5 · Runs started from a terminal in 0.0.1](W4/APPLY5.md): monitor only, bridges published in the engines' catalogues (running).
- [APPLY6 · Stages in 0.0.1, declared or detected](W4/APPLY6.md): stages above the processes or rules list, detected from nf-core subworkflows and Snakemake rule files, shown on four example pipelines (running).
- [APPLY7 · Job files and run tools in 0.0.1](W4/APPLY7.md): each job's files from its work directory, the run's own logs, resume, a failure summary with the SLURM reason, results and reports read-only, copy and copy to a new launch, and resources per task (running).
- [APPLY8 · `nf-spectio` enabled with `NXF_PLUGINS_DEFAULT`](W4/APPLY8.md): inbox #69 decided; the bridge is added per run next to an nf-core pipeline's own plugins, with Seqera Platform unaffected (running).
- [UILITE · The 0.0.1 lite boards: review, stages and Thomas's design requests](W4/UILITE.md): four screens, stages with their processes, logos and collapsible sections (running).
