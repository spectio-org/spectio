---
title: Spectio
hide: [navigation, toc]
---

<div class="sp-hero2">
<a class="sp-status" href="roadmap/"><b>0.0.1 · built, release in preparation</b> Launch, monitor and resume runs from the browser<span class="sp-status__go">→</span></a>
<div class="sp-hero2__brand">
<svg class="sp-emblem" viewBox="0 0 200 100" role="img" aria-label="Spectio emblem"><path fill="#5A4FCF" d="M86.09 94.24L4.17 94.24A96 96 0 0 1 28.17 36.31Z"/><path fill="#8B5CF6" d="M94.24 86.09L36.31 28.17A96 96 0 0 1 94.24 4.17Z"/><path fill="#EC5F87" d="M105.76 86.09L105.76 4.17A96 96 0 0 1 163.69 28.17Z"/><path fill="#F9A947" d="M113.91 94.24L171.83 36.31A96 96 0 0 1 195.83 94.24Z"/></svg>
<span class="sp-wordmark">Spectio</span>
</div>
<p class="sp-hero2__tagline">Launch, monitor and resume your Nextflow and Snakemake runs, on your own cluster.</p>
<p class="sp-hero2__sub">Open-source run manager. The first version runs on a SLURM login node or on one machine, for one user, from a browser. It is built and not released yet.</p>
<p class="sp-hero2__actions"><a class="md-button md-button--primary" href="usage/">How it works</a> <a class="md-button" href="roadmap/">Roadmap</a></p>
</div>

<figure class="sp-hero2__media">
<img src="assets/shots/app-run-detail_light.webp#only-light" alt="The detail page of a finished Nextflow run: its facts, and each process with its state and task counts">
<img src="assets/shots/app-run-detail_dark.webp#only-dark" alt="The detail page of a finished Nextflow run: its facts, and each process with its state and task counts">
<figcaption>A finished run: its facts, its processes and tasks, and the last lines of the engine log.</figcaption>
</figure>

## Works with { .sp-h2 }

<div class="sp-works" markdown>
<div class="sp-works__group" markdown>
<p class="sp-works__label" markdown><span class="sp-ic sp-ic--sm sp-ic--indigo">:material-sitemap:</span>Workflow engines</p>
<a class="sp-work" href="https://www.nextflow.io/"><img src="assets/logos/logo-nextflow.png" alt=""><span>Nextflow</span></a>
<a class="sp-work" href="https://snakemake.github.io/"><img src="assets/logos/logo-snakemake.png" alt=""><span>Snakemake</span></a>
<p class="sp-works__later">CWL and WDL later</p>
</div>
<div class="sp-works__group" markdown>
<p class="sp-works__label" markdown><span class="sp-ic sp-ic--sm sp-ic--violet">:material-bookshelf:</span>Pipelines</p>
<a class="sp-work" href="https://nf-co.re/"><img src="assets/logos/logo-nf-core.png" alt=""><span>nf-core</span></a>
<a class="sp-work" href="https://snakemake.github.io/snakemake-workflow-catalog/"><img src="assets/logos/logo-snakemake.png" alt=""><span>Snakemake catalog</span></a>
<p class="sp-works__later">or a directory or Git repository of your own</p>
</div>
<div class="sp-works__group" markdown>
<p class="sp-works__label" markdown><span class="sp-ic sp-ic--sm sp-ic--coral">:material-server:</span>Where runs execute</p>
<a class="sp-work" href="https://slurm.schedmd.com/" markdown><span class="sp-work__icon">:material-server-network:</span><span>SLURM (HPC)</span></a>
<p class="sp-works__later">or one Linux machine. Kubernetes later</p>
</div>
</div>
<p class="sp-fine">Logos are trademarks of their owners and show compatibility only.</p>

## How it works { .sp-h2 }

<div class="sp-steps">

<div class="sp-step">
<div class="sp-step__text">
<span class="sp-step__num">1</span>
<h3>Launch</h3>
<p>Pick a pipeline from your catalog or type its path, fill its parameters from the pipeline's own schema, and choose the environment and the resources.</p>
</div>
<img src="assets/shots/app-launch_light.webp#only-light" alt="The launch form for a Nextflow pipeline: engine, profile, environment and parameters">
<img src="assets/shots/app-launch_dark.webp#only-dark" alt="The launch form for a Nextflow pipeline: engine, profile, environment and parameters">
</div>

<div class="sp-step sp-step--flip">
<div class="sp-step__text">
<span class="sp-step__num">2</span>
<h3>Watch</h3>
<p>Every run in one list. Open one to see its stages, tasks and logs, and how much of its request each process used. Runs you start by hand in a terminal show up too.</p>
</div>
<img src="assets/shots/app-runs-grid_light.webp#only-light" alt="Every run in one table, with filters, a state rail on each row and a pin">
<img src="assets/shots/app-runs-grid_dark.webp#only-dark" alt="Every run in one table, with filters, a state rail on each row and a pin">
</div>

<div class="sp-step">
<div class="sp-step__text">
<span class="sp-step__num">3</span>
<h3>Resume</h3>
<p>When a run fails, Spectio shows why (out of memory, out of time, a tool error, a node lost). Resume it: finished work comes back from the engine's cache. Or copy the run to a new launch and change what you need.</p>
</div>
<img src="assets/shots/app-run-resume_light.webp#only-light" alt="The Resume dialog of a failed run">
<img src="assets/shots/app-run-resume_dark.webp#only-dark" alt="The Resume dialog of a failed run">
</div>

<div class="sp-step sp-step--flip">
<div class="sp-step__text">
<span class="sp-step__num">4</span>
<h3>Look at the results</h3>
<p>Browse a run's results and work directories, and preview text, tables, JSON, images, TIFF and OME-Zarr in the browser.</p>
</div>
<img src="assets/shots/app-results-explorer_light.webp#only-light" alt="The results folder of a finished run: folders and a report, with their kind, size and date">
<img src="assets/shots/app-results-explorer_dark.webp#only-dark" alt="The results folder of a finished run: folders and a report, with their kind, size and date">
</div>

</div>

## What is inside { .sp-h2 }

<div class="sp-cards2" markdown>
<a class="sp-card2" href="features/runs/" markdown><span class="sp-ic sp-ic--violet">:material-play-network:</span><b>Runs</b><span>Launch, watch and resume.</span></a>
<a class="sp-card2" href="features/runners/" markdown><span class="sp-ic sp-ic--sky">:material-server-network:</span><b>Runners</b><span>SLURM, or one machine.</span></a>
<a class="sp-card2" href="api/" markdown><span class="sp-ic sp-ic--indigo">:material-api:</span><b>API and CLI</b><span>A REST API and five commands.</span></a>
</div>

## Later { .sp-h2 }

Optional QC gates between stages, Kubernetes, the hand-off to depictio, accounts and administration are planned and not in 0.0.1. See the [roadmap](roadmap/index.md).

<p class="sp-more"><a href="roadmap/">Roadmap</a> · <a href="installation/">Installation</a> · <a href="changelog/">Changelog</a></p>
