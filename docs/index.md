---
title: Spectio
hide: [navigation, toc]
---

<div class="sp-hero2">
<div class="sp-hero2__brand"><img src="assets/brand/emblem.svg" alt="" class="sp-hero2__emblem"><span class="sp-hero2__name">Spectio</span></div>
<p class="sp-hero2__tagline">Launch, monitor and relaunch your Nextflow and Snakemake runs, on your own cluster.</p>
<p class="sp-hero2__sub">Open-source run manager for HPC and Kubernetes. Add quality checks between stages only where you want them. Part of the depictio platform.</p>
<p class="sp-hero2__actions"><a class="md-button md-button--primary" href="usage/">How it works</a> <a class="md-button" href="roadmap/">Roadmap</a></p>
<p class="sp-badge">Design phase · nothing to install yet · first release planned as 0.1</p>
</div>

<figure class="sp-hero2__media">
<video autoplay muted loop playsinline poster="assets/shots/run-detail_light.webp" aria-label="A terminal runs the synthetic pipeline to its QC gate while the browser shows a gate review design board">
<source src="assets/media/gate-review.mp4" type="video/mp4">
</video>
<figcaption>A run with an optional QC gate: it stops, someone reviews it, it resumes from the cache. The screens are the current design.</figcaption>
</figure>

## Works with { .sp-h2 }

<div class="sp-logos" markdown>
<a class="sp-logo" href="https://www.nextflow.io/" markdown><img src="assets/logos/logo-nextflow.png" alt=""><span>Nextflow</span></a>
<a class="sp-logo" href="https://snakemake.github.io/" markdown><img src="assets/logos/logo-snakemake.png" alt=""><span>Snakemake</span></a>
<a class="sp-logo" href="https://nf-co.re/" markdown><img src="assets/logos/logo-nf-core.png" alt=""><span>nf-core pipelines</span></a>
<a class="sp-logo" href="https://snakemake.github.io/snakemake-workflow-catalog/" markdown><img src="assets/logos/logo-snakemake.png" alt=""><span>Snakemake Workflow Catalog</span></a>
<a class="sp-logo" href="https://slurm.schedmd.com/" markdown><span class="sp-logo__icon">:material-server-network:</span><span>SLURM and other HPC schedulers</span></a>
<a class="sp-logo" href="https://kubernetes.io/" markdown><span class="sp-logo__icon sp-k8s">:simple-kubernetes:</span><span>Kubernetes</span></a>
<a class="sp-logo" href="https://github.com/depictio/depictio" markdown><img src="assets/logos/logo-depictio.png" alt=""><span>depictio dashboards</span></a>
</div>
<p class="sp-fine">Logos are trademarks of their owners and show compatibility only.</p>

## How it works { .sp-h2 }

<div class="sp-steps">

<div class="sp-step">
<div class="sp-step__text">
<span class="sp-step__num">1</span>
<h3>Launch</h3>
<p>Pick a pipeline, fill its parameters from the pipeline's own schema, choose where it runs, and say where it should stop for a check.</p>
</div>
<img src="assets/shots/launch_light.webp" alt="The launch form of nf-core/rnaseq">
</div>

<div class="sp-step sp-step--flip">
<div class="sp-step__text">
<span class="sp-step__num">2</span>
<h3>Watch</h3>
<p>Every run in one place: its stages, its tasks and samples, its logs, and what the cluster is doing with it.</p>
</div>
<img src="assets/shots/run-detail_light.webp" alt="The detail page of a running pipeline">
</div>

<div class="sp-step">
<div class="sp-step__text">
<span class="sp-step__num">3</span>
<h3>Fix and relaunch</h3>
<p>When a task fails, Spectio says why (out of memory, out of time, a tool error, a node lost) and what to change. Relaunch with the change; finished work comes back from the cache.</p>
</div>
<img src="assets/shots/runs_light.webp" alt="Every run in one table, with its stage and status">
</div>

<div class="sp-step sp-step--flip">
<div class="sp-step__text">
<span class="sp-step__num">4</span>
<h3>Results and dashboards</h3>
<p>Outputs, reports and logs stay attached to the run. Finished results can go to depictio as dashboards, with the same users and groups.</p>
</div>
<img src="assets/shots/overview_light.webp" alt="The overview page with runs, gates and environments">
</div>

</div>

<div class="sp-optional" markdown>
<span class="sp-ic sp-ic--amber">:material-gate:</span>
<div markdown>**Optional: quality checks between stages.** For pipelines where a bad sample should not reach the expensive stage, add a gate: the run stops after a stage, someone looks at the QC evidence, from a desk or a phone, and the run resumes from the cache. Pipelines without gates run straight through. [How gates work](features/gates.md)</div>
</div>

## What is inside { .sp-h2 }

<div class="sp-cards2" markdown>
<a class="sp-card2" href="features/runs/" markdown><span class="sp-ic sp-ic--violet">:material-play-network:</span><b>Runs</b><span>Launch, watch and relaunch.</span></a>
<a class="sp-card2" href="features/runners/" markdown><span class="sp-ic sp-ic--sky">:material-server-network:</span><b>Runners</b><span>SLURM, Kubernetes, a laptop.</span></a>
<a class="sp-card2" href="features/gates/" markdown><span class="sp-ic sp-ic--amber">:material-gate:</span><b>QC gates</b><span>Optional checks between stages.</span></a>
<a class="sp-card2" href="api/" markdown><span class="sp-ic sp-ic--indigo">:material-api:</span><b>API and CLI</b><span>Everything scriptable.</span></a>
<a class="sp-card2" href="features/administration/" markdown><span class="sp-ic sp-ic--coral">:material-shield-account:</span><b>Administration</b><span>Users, plugins, backups.</span></a>
<a class="sp-card2" href="features/depictio/" markdown><span class="sp-ic sp-ic--green">:material-chart-box:</span><b>depictio</b><span>Results become dashboards.</span></a>
</div>

## Where it stands { .sp-h2 }

<!-- spectio:progress-strip -->

<p class="sp-more"><a href="roadmap/">Roadmap</a> · <a href="developer/">Developer documentation</a> · <a href="changelog/">Changelog</a></p>
