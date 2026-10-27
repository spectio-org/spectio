---
icon: material/chart-timeline
hide: [navigation]
---
# Roadmap

Three questions: what is done, what is being worked on, and what comes next. Spectio stays below 1.0 until it has been checked with several use cases and several groups; the conditions are written down in the [release stages](../specs/dev-environment-and-testing.md#14-release-stages-and-the-10-gate).

<div class="sp-timeline">
<div class="sp-tl sp-tl--now"><span class="sp-tl__dot"></span><b>Design</b><span class="sp-tl__when">now</span><p>Specifications, screen designs, test pipelines on both engines, reviews before any code.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.0.1 · Local MVP</b><span class="sp-tl__when">after the go decision</span><p>One user, on one machine: launch a Nextflow or Snakemake run from the browser, follow its state, tasks and stages, relaunch it with changed parameters and see what changed, and stop it at one simple QC gate. What comes between 0.0.x and the private alpha is not decided yet. <a href="../specs/dev-environment-and-testing/#15-what-ships-in-which-version">What ships in which version</a>.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.2 – 0.4 · Private alpha</b><span class="sp-tl__when">with 3 to 5 EMBL groups</span><p>Installed from the docs in under 30 minutes, real pipelines every night, backups tested.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>0.5 – 0.9 · Public beta</b><span class="sp-tl__when">with a demo instance</span><p>Open to everyone, demo instance on EMBL's Kubernetes, upgrades tested release after release.</p></div>
<div class="sp-tl"><span class="sp-tl__dot"></span><b>1.0 · Stable</b><span class="sp-tl__when">when the 1.0 conditions are met</span><p>Several groups using it daily, both engines on SLURM and Kubernetes, frozen API.</p></div>
</div>

## Done

- **The design**, reviewed before code: 13 specifications, about 60 screen designs, a decision log.
- **Test pipelines** written for both engines, with 11 scenarios (stops at gates, failures, retries, resumes) passing on Nextflow 26.10 and 25.10 and on Snakemake 9.27, on every change.
- **A test corpus** of 14 nf-core pipelines and 9 Snakemake catalog workflows on their own test data.
- **This documentation**, written and reviewed at every step.

## Now

The design phase runs in waves. Each wave is a set of steps, done by agents and checked before the next wave starts.

<!-- spectio:progress-strip -->

Each step has its own page under [Progress](../progress/index.md).

## Next

- **Reviews before code** (waves W1 and W2): consistency, facts, constraints, security, screens, depictio.
- **Development setup and test clusters** (wave W3): local SLURM and Kubernetes for tests, dev previews, end-to-end tests.
- **The go decision** (wave W4), then the first version, [0.0.1](../specs/mvp-0.0.1.md): a basic local MVP.

## Ideas, not scheduled

- CWL and WDL engines.
- Other schedulers: LSF, PBS, SGE.
- GA4GH WES and TES interfaces.
