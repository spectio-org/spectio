---
icon: material/chart-timeline
hide: [navigation]
---
# Roadmap

Three questions: what is done, what is being worked on, and what comes next. Spectio stays below 1.0 until it has been checked with several use cases and several groups; the conditions are written down in the [release stages](../specs/dev-environment-and-testing.md#14-release-stages-and-the-10-gate).

<div class="sp-timeline">
<div class="sp-tl"><span class="sp-tl__dot"></span><b>Design</b><span class="sp-tl__when">done</span><p>Specifications, screen designs, test pipelines on both engines, reviews before any code.</p></div>
<div class="sp-tl sp-tl--now"><span class="sp-tl__dot"></span><b>0.0.1 · First MVP</b><span class="sp-tl__when">now, being built</span><p>The simplest version to try: launch, follow and relaunch Nextflow and Snakemake runs on your cluster from the browser. <a href="../specs/mvp-0.0.1/">What it does</a>.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.0.2</b><span class="sp-tl__when">next</span><p>Resource plots per run and across runs, and the interactive workflow graph, behind a flag. <a href="../specs/dev-environment-and-testing/#15-what-ships-in-which-version">What ships in which version</a>.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.1</b><span class="sp-tl__when">not decided yet</span><p>The step between the first MVPs and the private alpha is still open: it will be set from what test users ask for after 0.0.x.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.2 – 0.4 · Private alpha</b><span class="sp-tl__when">with 3 to 5 EMBL groups</span><p>Installed from the docs in under 30 minutes, real pipelines every night, backups tested.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.5 – 0.9 · Public beta</b><span class="sp-tl__when">with a demo instance</span><p>Open to everyone, demo instance on EMBL's Kubernetes, upgrades tested release after release.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>1.0 · Stable</b><span class="sp-tl__when">when the 1.0 conditions are met</span><p>Several groups using it daily, both engines on SLURM and Kubernetes, frozen API.</p></div>
</div>

## Done

- **The design**, reviewed before code: 13 specifications, about 60 screen designs, a decision log.
- **Reviews, development setup and test clusters**: independent reviews of the design, then local SLURM and Kubernetes clusters for tests, dev previews and end-to-end tests.
- **Test pipelines** written for both engines, with 11 scenarios (stops at gates, failures, retries, resumes) passing on Nextflow 26.10 and 25.10 and on Snakemake 9.27, on every change.
- **A test corpus** of 14 nf-core pipelines and 9 Snakemake catalog workflows on their own test data.
- **This documentation**, written and reviewed at every step.

## Now

Building [0.0.1](../specs/mvp-0.0.1.md). The work runs in waves; the last one, building the first version, is under way.

<!-- spectio:progress-strip -->

Details under [Progress](../progress/index.md).

## Next

- **0.0.1 released** to the first test users on their cluster.
- **0.0.2**: resource plots and the interactive workflow graph.
- **Deciding 0.1**, the step before the private alpha.

## Ideas, not scheduled

- CWL and WDL engines.
- Other schedulers: LSF, PBS, SGE.
- GA4GH WES and TES interfaces.
