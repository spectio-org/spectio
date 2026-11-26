# Next wave: proof-testing, MosaiCatcher, UI redesign, multi-user (from 2026-11-30)

Decided with Thomas on 2026-11-26. It runs in dev mode ([autopilot §15](autopilot.md#15-dev-mode-features-first-gates-at-the-milestone-thomas-2026-11-26)), until the budget is exhausted, with 3 or 4 tracks in parallel and one dedicated agent per track.

## 1. Release criteria

0.0.1-rc1 is **postponed**. Spectio goes to its first users only when all four of these hold:

1. **Corpus green.** 5 to 10 pipelines per engine (Nextflow, Snakemake), plus single modules, pass end to end on the login node.
2. **Central UI live.** The multi-user UI runs on Kubernetes with EMBL OIDC.
3. **MosaiCatcher validated.** A real mosaicatcher run is followed in Spectio and its results open there.
4. **UI redesign done.**

## 2. Tracks

### T1. Corpus, proof-tested by agents

- **Public sources.** nf-core pipelines with their `test` profile; snakemake-workflows repositories with a `.test` directory; nf-core/modules and snakemake-wrappers for single modules **[to be validated: which ones ship small test data]**. The #354 demonstrators are part of the corpus too: Strand-seq with the watcher, and an nf-core fork.
- **Custom pipelines.** Thomas gives a list. Claude searches WorkflowHub, public git.embl.de and EMBL GitHub organisations, and proposes more. Thomas validates before anything runs.
- **Runs.** One agent per pipeline launches it through the CLI and the API, on minikube first, then on the login node. Small SLURM runs on `/scratch` are allowed for the whole wave without asking.
- **Matrix.** Engine × source (Git, path, WorkflowHub) × software (conda, Apptainer, none) × executor (local, SLURM) × feature (parameter schema, configfile, profiles, entry scripts, failure and resume).
- **Results.** A matrix page in the docs and an artifact dashboard. Each failure becomes an issue. Conformity (#369) is shown to users as a list of capabilities, with no global tier.

### T2. MosaiCatcher as the reference case

- **Base view.** The table and the graph are as simple as possible. Rules a run never uses are hidden, behind an expandable "N unused rules" counter.
- **End of a run:**
  - the Results tab comes first;
  - the declared outputs (targets, publishDir) are listed;
  - the results folder path can be copied;
  - a "send to depictio" button (#361).
- **Data.** First the repository's test data, then a real Strand-seq sample taken from a past run (read only).
- **QC gates.** An inventory of what exists (spec, code, UI) and a proposal. Nothing is built in this wave.

### T3. UI redesign (every page)

- **References.**
  - Seqera Platform: from its public docs, and from a free account Thomas signs in to in Chrome; Claude drives the signed-in tab and never handles credentials.
  - Galaxy, the Snakemake monitors (panoptes, WMS), Flyte, Prefect and Dagster.
- **Direction.**
  - Close to depictio, with three directions on boards for Thomas to choose; the sidebar stays.
  - The logo wordmark: three proposals, aligned with depictio.
- **Known problems.**
  - Huge tables: add display modes, and hide columns that are all zeros.
  - Wasted space, and too few light icons.
  - The run status should be clearer.
  - Logs are isolated: move them to a live, collapsible bottom panel, with per-task logs opened from the task's row.
  - Results should be one click away at the end of a run.
- **A running run shows:**
  - the SLURM queue (pending reason, start estimate);
  - progress with an ETA;
  - live CPU and memory;
  - the end of the log.
- **About.** The Spectio version, commit and build date; the engine and plugin versions; the runner and server versions, with a warning when they differ; links and licences.
- **Phone.** Everything should work there, but at the lowest priority, with lightweight checks.
- **Planned now, built later.** LabID inputs and outputs, pushing outputs to depictio, and an identity shared with both.

### T4. Catalog and Launch

- **Adding a pipeline or a module** (a major point) offers three paths, and the mandatory metadata stays minimal:
  1. paste a URL, and Spectio infers and pre-fills the rest;
  2. a step-by-step wizard;
  3. a registry search (nf-core, the Snakemake catalog, WorkflowHub) with a one-click Add.
- **Checks on adding:** static inspection; a short test run, which earns a "tested" badge; the capability list.
- **Metadata fetched when available:** licence and citation, repository health, software and containers, inputs and outputs.
- **An entry's page:** its identity, how to launch it, its history (recent runs, success rate) and its structure.
- **Single modules:**
  - as their own catalog entries, which Spectio wraps in a mini-workflow;
  - as a single target of an existing pipeline.
- **Launch inputs:**
  - a file browser through the runner;
  - an editable sample sheet, from a folder or a CSV;
  - a pasted path, which is checked;
  - LabID samples (designed now, built later).
- **Parameters:** required ones first, the rest in folded groups, plus named presets.
- **Engine versions:**
  - chosen at three levels: a default in the execution profile, an override at Launch, or fixed per pipeline;
  - the compute lists the versions available;
  - each version comes from site modules or EESSI when present, otherwise from a download into a cache.
- **Updates and resume:**
  - a new pipeline version is flagged only;
  - after a failure, two actions: resume as is, or resume with changed parameters and resources.

### T5. Multi-user on Kubernetes (#355)

1. **Locally, on minikube.**
   - Accounts and sessions, with each runner bound to its user.
   - OIDC sign-in reused from depictio's code, tested against a local provider (Dex or Keycloak).
   - An admin audit log, and a history of events on each run.
2. **Deployment** to the namespace `datasci-spectio-dev-internal`.
   - It runs with OIDC not yet connected; Thomas signs in with a link only he can use.
   - The database is backed up daily from the first deployment, and a restore is tested.
3. **Ask IT** for a dedicated OIDC client, a DNS name and a certificate. They need the active deployment's URL. Then switch to EMBL OIDC.
- **Users.** Thomas first, then 2 or 3 pilot colleagues.
- **Network.** The login node reaches the internal ingress over outgoing HTTPS (`docs/research/runner-channel-spike-2026-11-25.md`); its certificate is self-signed for now.
- **Still open, with options to present:**
  - who may add to the catalog;
  - who sees whose runs;
  - where groups come from. A user can be in several groups, but EMBL OIDC exposes one; the lead option is groups assigned by an admin, possibly seeded from cluster UNIX groups.

### T6. CLI and plugins

- **CLI-launched runs.** Check that nf-spectio and the Snakemake plugin work end to end. A run launched from the CLI is tracked like any other, marked "launched from CLI", and can be relaunched from the UI.
- **Plugins on by default** in a new execution profile:
  - RO-Crate and provenance;
  - the efficiency report;
  - `snakemake --report`;
  - the Nextflow report, timeline and trace.

  A profile can turn them off, and the site (#398) can impose them.
- **AI agents (#356)** can read and launch or relaunch, with a token limited to one user.
- **Pilot docs:**
  - a first run in 5 minutes;
  - adding your own pipeline;
  - profiles and the cluster;
  - the CLI and plugins.

## 3. Not in this wave

- Email notifications: the bell only for now.
- Suggestions from the efficiency report.
- Work-directory cleanup, which will later be proposed after a successful run and never automatic.
- Jobs on Kubernetes: Kubernetes hosts the UI only.
- Output viewers beyond the current ones, OME-NGFF, MetroFlow, and the #318 and #319 evaluations.

## 4. How the wave runs

- **Dev mode** ([autopilot §15](autopilot.md#15-dev-mode-features-first-gates-at-the-milestone-thomas-2026-11-26)): features first, quick local checks, and end-to-end runs with real pipelines at the end of a feature.
- **Design decisions.** Claude takes them, records them in the [decision log](../decisions/log.md), and Thomas reviews them in the evening.
- **Each evening,** a short report with screenshots or a video of what works on minikube or the login node.
