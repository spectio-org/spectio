---
title: Spectio
hide: [navigation, toc]
---

<div class="sp-hero" markdown>
<div class="sp-hero__text" markdown>
<div class="sp-hero__brand"><img src="assets/brand/emblem.svg" alt="" class="sp-hero__emblem"><span class="sp-hero__name">Spectio</span></div>

<p class="sp-hero__tagline">Launch, watch and steer Nextflow and Snakemake runs.<br>Stop at QC gates, decide from your phone.<br>Hand the results to depictio.</p>

<p class="sp-hero__sub">An open-source run manager for bioinformatics pipelines on HPC and Kubernetes, with a headless API and a plugin for everything. Spectio is in its design phase: everything below is specified and reviewed in the open before code is written.</p>

[Read the design](map.md){ .md-button .md-button--primary } [See progress](progress/index.md){ .md-button }
</div>
<figure class="sp-hero__media">
<video autoplay muted loop playsinline poster="assets/shots/run-detail_light.webp" aria-label="A terminal runs the synthetic pipeline to the QC gate while the browser shows the gate review">
<source src="assets/media/gate-review.mp4" type="video/mp4">
</video>
<figcaption>Terminal and browser side by side: the synthetic pipeline stops at the QC gate, a reviewer excludes S03, the run resumes from the cache (UI from the design boards).</figcaption>
</figure>
</div>

<section class="sp-lead" markdown>
Pipelines on clusters are still launched by hand, followed in log files, and checked after the fact. A failed sample is noticed when the report is read; a run that should have stopped after QC burns a week of CPU. Spectio watches the run from the engine's own events, stops it at the stages you choose, shows the evidence to whoever must decide, and resumes from the cache.
</section>

## Works with { .sp-section-title }

<div class="sp-eco" markdown>
<div class="sp-eco__card" markdown>**Nextflow**<br><span>trace, weblog and `-resume`, 25.10 and 26.10</span></div>
<div class="sp-eco__card" markdown>**Snakemake**<br><span>logger and executor plugins, `--until`, 9.x</span></div>
<div class="sp-eco__card" markdown>**nf-core**<br><span>14 pipelines in the test corpus, with their test data</span></div>
<div class="sp-eco__card" markdown>**Snakemake Workflow Catalog**<br><span>9 workflows, run on their `.test` data</span></div>
<div class="sp-eco__card" markdown>**depictio**<br><span>same identity, groups and branding; results handed over</span></div>
<div class="sp-eco__card sp-eco__card--later" markdown>**CWL · WDL**<br><span>later, through engine plugins</span></div>
</div>

## What it is made of { .sp-section-title }

<div class="sp-cards" markdown>
<a class="sp-card" href="specs/ui-spec/" markdown>:material-play-network:{ .sp-card__icon } **Runs**<br><span>One place for every run, with tasks, samples, logs and costs.</span></a>
<a class="sp-card" href="specs/checking-scenarios/" markdown>:material-gate:{ .sp-card__icon } **QC gates**<br><span>Stop after a stage, review the evidence, exclude samples, resume.</span></a>
<a class="sp-card" href="specs/schedulers-and-monitoring/" markdown>:material-server-network:{ .sp-card__icon } **Runners**<br><span>SLURM and other HPC schedulers, Kubernetes with Kueue, a laptop.</span></a>
<a class="sp-card" href="specs/api-and-data-model/" markdown>:material-api:{ .sp-card__icon } **Headless API**<br><span>Everything the UI does, scripted; events, webhooks, RO-Crate.</span></a>
<a class="sp-card" href="specs/cli-and-shared-libraries/" markdown>:material-console:{ .sp-card__icon } **CLI**<br><span>`spectio run`, `watch`, `gate`, with models shared with depictio.</span></a>
<a class="sp-card" href="specs/architecture-plugins-and-packaging/" markdown>:material-puzzle:{ .sp-card__icon } **Plugins**<br><span>Engines, launchers, auth, notifiers, storage: entry points, like Snakemake.</span></a>
<a class="sp-card" href="specs/admin-and-operations/" markdown>:material-shield-account:{ .sp-card__icon } **Administration**<br><span>Users and groups, branding, tasks, logs, backups and migrations.</span></a>
<a class="sp-card" href="specs/authentication-and-access/" markdown>:material-link-lock:{ .sp-card__icon } **Share links**<br><span>Magic links, scoped reviewer links, OIDC and SAML, provisioning.</span></a>
<a class="sp-card" href="specs/depictio-ecosystem-reuse/" markdown>:material-chart-box:{ .sp-card__icon } **depictio hand-off**<br><span>Finished runs become dashboards, with the same users and groups.</span></a>
</div>

## Key ideas { .sp-section-title }

<div class="sp-features" markdown>
<div class="sp-feature" markdown>
<span class="sp-feature__num">01</span>
<div markdown>**Gates stop the right stage.** Spectio generates the engine's own stop (a Nextflow config, a Snakemake `--until`) and resumes with the cache: on the synthetic test pipeline, 25 of 65 tasks come back cached after the QC gate.</div>
</div>
<div class="sp-feature" markdown>
<span class="sp-feature__num">02</span>
<div markdown>**Decide anywhere.** A reviewer opens a scoped link on a phone, sees the QC evidence, excludes a sample and approves. No account needed, every use audited.</div>
</div>
<div class="sp-feature" markdown>
<span class="sp-feature__num">03</span>
<div markdown>**Runs where the data is.** A small runner on the login node or in the cluster pulls commands over HTTPS. No inbound ports on the HPC side.</div>
</div>
<div class="sp-feature" markdown>
<span class="sp-feature__num">04</span>
<div markdown>**One Python package to start.** `pip install spectio` gives the CLI and runner; `spectio[server]` adds the server with SQLite. Docker Compose and a Helm chart come next.</div>
</div>
<div class="sp-feature" markdown>
<span class="sp-feature__num">05</span>
<div markdown>**Tested on real pipelines.** Twin synthetic pipelines already pass 11 failure and gate scenarios on two Nextflow versions and Snakemake, and nf-core/demo passes with its test data. The plan: every pull request runs them, then the nf-core and catalog corpus, once CI is green (step T7).</div>
</div>
</div>

## How a gate works { .sp-section-title }

[![Stop at the QC gate, drop a sample, resume](assets/diagrams/gate-resume_light.png#only-light)](assets/diagrams/gate-resume_light.png)
[![Stop at the QC gate, drop a sample, resume](assets/diagrams/gate-resume_dark.png#only-dark)](assets/diagrams/gate-resume_dark.png)

<p class="sp-note">Task counts measured on the synthetic pipeline; the cluster, runner, share link and phone show the planned flow. Click for the full size.</p>

<div class="asciinema-cast" data-cast="assets/casts/synthetic-gate.cast"></div>

## Where the design stands { .sp-section-title }

<!-- spectio:progress-strip -->

## Start reading { .sp-section-title }

1. [Synthesis](specs/synthesis.md): what Spectio is, the engines, the existing tools and the stack.
2. [UI spec](specs/ui-spec.md): every screen, phone included.
3. [Checking scenarios](specs/checking-scenarios.md): what a gate checks, across nf-core.
4. [Documentation map](map.md): every spec and which topic it owns.
