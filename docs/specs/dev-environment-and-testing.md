# Spectio — development environment, automation and testing

Status: draft v0.1 · 2026-10-25 · author: Thomas Weber (with Claude)
Companion docs:
- [`schedulers-and-monitoring.md`](schedulers-and-monitoring.md): what is tested against SLURM and Kubernetes.
- [`architecture-plugins-and-packaging.md`](architecture-plugins-and-packaging.md): packages, plugin conformance suites, deployments.
- [`admin-and-operations.md`](admin-and-operations.md): backup compatibility tests.
- `docs/playbooks/next-phase.md`: the order in which this is built.

## 0. Decisions in brief

1. **Agents check their own work against real tools.**
   - Every behaviour Spectio relies on is tested against the real tool at a pinned version: Nextflow, Snakemake and its executor plugins, Slurm, Kubernetes and Kueue.
   - Mocks are for unit tests only.
   - Real outputs are recorded as golden fixtures, with the tool version in the file name.
2. **Local clusters, no real HPC needed for development.**
   - SLURM runs in Docker with [sind](https://github.com/GSI-HPC/sind) (Slurm 25.11 and 26.05 images; slurmdbd; slurmrestd with JWT; node power-cycle simulation; GitHub Action; MCP server; no privileged containers needed; LGPL-3.0, used as a tool, not linked).
   - Kubernetes runs in kind with Kueue installed.
3. **Scenarios are isolated and run in parallel.** Each has its own Compose project, port range, Docker network, sind realm or kind cluster, and data directory. Agents in parallel worktrees never collide.
4. **One bootstrap script everywhere.** `dev/bootstrap.sh` installs the pinned toolchain from `dev/versions.env` in:
   - the Claude Code cloud environment setup script, cached when it finishes in about 5 minutes;
   - CI;
   - a developer laptop.
   
   `dev/doctor.sh` proves each tool works.
5. **Dev previews without a server; a public instance only later, on EMBL Kubernetes** (revised 2026-10-26, §7). There is no staging VM, and the institute network is behind a VPN that GitHub cannot reach.
   - Every PR, validated wave and release is published as its own static preview on Cloudflare Pages. Nothing is overwritten, and a `/versions` page lists them all.
   - The full stack runs on demand in GitHub Codespaces, from a link on each PR.
   - The cost is 0 € within the free quotas.
   - The public instance for users comes at the beta, on EMBL's Kubernetes, deployed like depictio's.
6. **Claude is part of the development loop, inside guard rails:**
   - project agents and skills in `.claude/`;
   - PR review by those agents in GitHub Actions;
   - auto-fix of CI failures on PRs;
   - scheduled routines for drift checks.
   
   Humans merge.

## 1. Toolchain (pinned in `dev/versions.env`)

| Tool | Pin (initial) | How it is installed | Used for |
|---|---|---|---|
| Python | 3.13 (uv-managed; embeds SQLite ≥ 3.51.3) | `uv python install` | server, CLI, runner, tests |
| uv | latest at bootstrap time, then pinned | official installer | everything Python |
| Node.js | 22 LTS | distro or `nvm` | UI build, Playwright, mermaid-cli |
| Java | 21 (Temurin) | distro package or SDKMAN | Nextflow |
| Nextflow | 26.10.x and 25.10.x (two versions, both tested) | release launcher from GitHub releases, `NXF_VER` pinned **[to be validated: asset names and whether the cloud allowlist reaches `get.nextflow.io` / `www.nextflow.io`]** | fixture and nf-core runs |
| Snakemake | 9.x + `snakemake-executor-plugin-slurm`, `-kubernetes`, `-kueue`, plus `snakemake-logger-plugin-spectio` (ours) | `uv tool install` with `--with` plugins, or a pixi environment | fixture runs |
| sind | latest release, pinned | release binary **[to be validated: install method, see gsi-hpc.github.io/sind]** | SLURM clusters |
| kind, kubectl, helm | pinned releases | release binaries | Kubernetes clusters, chart tests |
| Kueue | pinned manifest version | `kubectl apply --server-side -f` | queueing scenarios |
| Playwright | pinned, Chromium | `npm i -D playwright`; Chromium is pre-installed in some environments | e2e tests, board rendering |
| mermaid-cli, mkdocs-material | pinned | `npx`, `uvx` | docs CI |
| Apptainer | optional, later | distro package | Apptainer-only HPC scenarios |

**Checks.**
- `dev/doctor.sh` prints each tool and version, then runs one smoke test per layer:
  - `docker run --rm hello-world`;
  - `sind` create, then `sbatch --wrap hostname` with `--wait`;
  - `kind create cluster`, then a Job, then delete;
  - `nextflow run tests/fixtures/workflows/nf-toy -profile local`;
  - `snakemake -n -s tests/fixtures/workflows/smk-toy/Snakefile`;
  - Playwright opening `about:blank`.
- It exits non-zero on the first failure, naming the tool.

## 2. Where agents work

| Place | What it is good for | Limits to design around |
|---|---|---|
| **Claude Code on the user's machine** (terminal, desktop) | interactive work, plugins (superpowers, Karpathy guidelines, frontend-design) installed normally | the user's machine resources |
| **Cloud sessions** (claude.ai/code, `claude --cloud`) | parallel autonomous tasks, one per branch; Docker is available | setup script cached only if it finishes in about 5 min; commands time out at 2 min by default (10 max, then moved to the background, up to 30 more min; `BASH_DEFAULT_TIMEOUT_MS` raises it); outbound network through an allowlist proxy (Trusted, Custom or Full); **plugins are not loaded**, so the skills are vendored in `.claude/skills/`; VM memory limits; idle VMs are reclaimed ([cloud environments](https://code.claude.com/docs/en/cloud-environments.md), [cloud sessions](https://code.claude.com/docs/en/claude-code-on-the-web.md)) |
| **GitHub Actions** | PR gates, nightly matrix, preview deploys, Claude PR review | runner time and memory |
| **Cloudflare Pages** | one static preview per PR, wave and release (docs, boards, later the UI with a mocked API) | static only; public unless Cloudflare Access is on |
| **GitHub Codespaces** | the full stack on demand for Thomas, one per branch | about 60 h a month of a 2-core machine in the free quota; stops when idle |

**Cloud environment settings** (claude.ai/code → environment):
- **Network:** Custom, with the default list plus the hosts Nextflow, nf-core and the container registries need. The list is to be confirmed by spike D2: `www.nextflow.io`, `get.nextflow.io`, `registry.nextflow.io`, `quay.io`, `ghcr.io`, `community.wave.seqera.io`, `conda.anaconda.org`, `prefix.dev`.
- **Environment variables:** `BASH_DEFAULT_TIMEOUT_MS=600000`, `BASH_MAX_TIMEOUT_MS=1800000`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (optional).
- **Setup script:** `bash dev/bootstrap.sh --ci` (toolchain and pre-pulled images only).
- **SessionStart hook:** in `.claude/settings.json`, starts nothing heavy by default. Scenarios start their own clusters.

## 3. Fixture workflows (`tests/fixtures/workflows/`)

Tiny, deterministic, shell-only tasks (seconds each), with explicit stages so gates can be exercised:

| Fixture | Engine | What it exercises |
|---|---|---|
| `nf-toy` | Nextflow DSL2 | 3 stages (A → gate → B → C), `ext.when` stage stop and `-resume`; params `fail=oom\|timeout\|exit\|flaky`, `fanout=N`, `array=true`; `publishDir` outputs, a MultiQC-like JSON and a per-sample TSV for checks |
| `smk-toy` | Snakemake | the same stages with `--until` and `--forcerun`; a checkpoint that changes the DAG; rule `resources` for SLURM; the same failure parameters |
| `nf-core/demo` (real) | Nextflow | `-profile test,docker` on the local executor and on kind; a real MultiQC report for review views |
| `nf-core/rnaseq` test profile (real, nightly) | Nextflow | full gate scenario "Mapping QC" from `checking-scenarios.md`, on kind |

**Failure injection.**
- *OOM:* a task allocates more memory than requested. SLURM then reports `OUT_OF_MEMORY`, Kubernetes reports `OOMKilled`.
- *Timeout:* `sleep` beyond the time limit.
- *Flaky:* fails when `task.attempt == 1`.
- *Node failure:* sind power-cycles a worker during a running job.
- *Preemption:* a higher-priority partition and QoS in the sind cluster.

## 4. Local clusters

### 4.1 SLURM with sind

| Profile | Topology | Used for |
|---|---|---|
| `slurm-mini` | controller + 1 worker, no accounting | head job, `squeue --json`, cancel, reconcile |
| `slurm-site` | controller, db (slurmdbd), 3 workers in partitions `htc`, `bigmem`, `gpu` (fake GRES), users with association limits, a maintenance reservation | pending reasons, `sacct` outcomes, fairshare, limits, pre-flight, failure classes |
| `slurm-rest` | `slurm-site` + api node (slurmrestd, JWT, 26.05) | slurmrestd transport and `data_parser` negotiation |
| `slurm-versions` | `slurm-site` on 25.11 and 26.05 | version matrix |

The runner runs on the sind submitter node as an unprivileged user, exactly as on a login node. Fixture workflows are mounted into it. Nextflow and Snakemake run inside the submitter node, using the cluster's `sbatch`.

### 4.2 Kubernetes with kind

| Profile | Setup | Used for |
|---|---|---|
| `k8s-mini` | kind, 1 node, a namespace with a `ResourceQuota`, a namespaced runner Role (see `schedulers-and-monitoring.md` §4) | watch API, pod reasons, OOMKilled, logs |
| `k8s-kueue` | kind with 2 workers, Kueue with a `ClusterQueue` and a `LocalQueue`, the visibility API | queue positions, admission, preemption |
| `k8s-rwx` | `k8s-mini` + an RWX storage class (NFS provisioner) | Nextflow k8s executor with a shared work directory |

Whether kind runs inside a Claude Code cloud session (kind needs privileged node containers) is the first thing spike D2 answers. If it does not, Kubernetes scenarios run in CI and on the user's machine only.

## 5. Isolated, parallel scenarios

- **One command per scenario.** `dev/scenario.py up <scenario> [--id <n>]` creates:
  - Docker network `spx-<id>`;
  - Compose project `spx-<id>` with ports `20000 + 100·id + k`;
  - data directory `.scenarios/<id>/`;
  - sind realm `spx-<id>` or kind cluster `spx-<id>`.
  
  It prints a JSON with every URL and credential. `down` removes all of it.
- **Scenarios are YAML** (`tests/scenarios/*.yaml`): deployment (bundle / compose), scheduler profile, engine and version, fixture and parameters, gate script (who decides what, when), and expected events and states.
- **The matrix** is engine {nextflow 25.10, 26.10; snakemake 9} × scheduler {local, slurm-mini, slurm-site, k8s-mini, k8s-kueue} × deployment {bundle, compose} × scenario {happy, gate-approve, gate-exclude-and-resume, oom-retry-suggestion, runner-offline-mid-run, restore-during-idle, multi-user-permissions}. A PR runs a smoke subset, the full matrix runs nightly.
- **Parallelism is capped by memory,** checked against free RAM before `up`. One Claude agent per worktree and scenario ID, so agents working in parallel never share state.

## 6. Test tiers

| Tier | What | Runs on | Gates |
|---|---|---|---|
| 0 · static | ruff, ty or mypy, import-linter (dependency rules), eslint, OpenAPI diff, docs build, Mermaid | every push | PR |
| 1 · unit and contract | pure logic; plugin conformance suites (`spectio_sdk.testing`); golden fixtures for the Tower protocol, Snakemake logger events, `squeue` / `sacct` JSON and Kubernetes objects | every push, seconds | PR |
| 2 · component | server with SQLite, fake runner, recorded engine event streams replayed; API tests with RFC 9457 errors, `If-Match`, idempotency | every push, < 2 min | PR |
| 3 · integration | real engines on `slurm-mini` and `k8s-mini`; backup → restore → migrate; bundle → Compose hand-over | PR (smoke subset), < 15 min | PR |
| 4 · end-to-end | Playwright against the bundle and Compose: launch, watch, review a gate, relaunch, admin pages, phone viewport | PR (smoke), nightly (full) | PR (smoke) |
| 5 · matrix and compatibility | the full scenario matrix; cross-version backup restore (previous release → current); depictio hand-off with a depictio container | nightly / weekly | release |
| 6 · preview and instance | static preview: links and media checked on the deployed URL. Public instance, from the beta: deploy + Playwright smoke over its URL; inbound webhook round trip | after merge | release |

**Visual review.** Playwright saves screenshots of the real pages named after the canvas boards (`RunDetail`, `ReviewQueue`…). A report puts them side by side with the renders of `design/ui-canvas`. This is a review aid for the `ux-reviewer` agent and for humans, not a pixel-diff gate.

## 7. Dev previews and the public instance

**Context.**
- **No staging VM:** Thomas has no VM of his own.
- **No institute host:** the institute's machines are behind a VPN that GitHub cannot reach.
- **Cost:** it must stay as close to zero as possible.

The earlier design (a tailnet VM behind Tailscale Funnel) is replaced; see the decision log of 2026-10-26.

### 7.1 Static previews on Cloudflare Pages (now)

- **What is published.** The built docs site, which already contains the progress pages, figures, casts and board screenshots. Once the UI exists, its build in **mock mode** is published too (§7.3).
- **How.**
  - `previews.yml` builds the site in GitHub Actions, then uploads it with `wrangler pages deploy` (direct upload).
  - Cloudflare never reads the repository, so a private repository is not an issue.
  - The secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` live in the GitHub environment `previews`, which only `previews.yml` uses.
- **Versions side by side, nothing overwritten** ([Cloudflare docs](https://developers.cloudflare.com/pages/configuration/preview-deployments/)):
  - each deployment gets its own hash URL (`<hash>.spectio.pages.dev`), which stays reachable;
  - each branch gets an alias that follows its latest deployment (`<branch>.spectio.pages.dev`).
- **Which branch each kind of preview is deployed under:**

  | Event | Branch |
  |---|---|
  | a PR | `pr-<n>` |
  | a validated wave | `wave-<id>`, for example `wave-w2` |
  | a release | `v<X-Y-Z>` |
  | `main` | the production URL |

- **The `/versions` page.** It is generated at every deploy from the Cloudflare deployments API (`tools/previews/versions_page.py`) and lists every preview with its date, branch, commit, PR and link. It is the "versions step by step" view.
- **Privacy.**
  - Previews are public by default. Cloudflare Access can restrict them to Thomas.
  - Media are rendered with fixture names (`documentation-system.md` §5.5).
- **Limits (free plan):** 500 builds a month, 20 000 files and 25 MiB per file ([limits](https://developers.cloudflare.com/pages/platform/limits/)). Whether direct uploads count as builds is **[to be validated]**. The site is far below both limits.
- **Without the secrets,** the workflow skips the deploy, with a notice, and still builds.
- **Checked on 2026-10-26:**
  - The first deploys worked: `https://spectio.pages.dev` (main) and `https://pr-1.spectio.pages.dev` (PR #1), with the PR comment posted.
  - `/versions` reads the deployments API as expected.
  - A new deployment's hostname took more than 60 s to answer, so the verification step waits up to 4 minutes.
  - The production branch is served at the project root, not under a `main` alias.

### 7.2 The full stack on demand in GitHub Codespaces (from D3)

- **The dev container** (`.devcontainer/`) installs the pinned toolchain (§1): uv, Python, Java 21, Nextflow, Snakemake, Node and Playwright, plus Docker-in-Docker for sind and kind.
- **Forwarded ports:** the docs site on 8000, and, once it exists, Spectio on 8080 with a seeded demo.
- **Opening it.** Each PR comment from `previews.yml` carries an "Open in Codespaces" link for its branch (`https://codespaces.new/weber8thomas/spectio/tree/<branch>?quickstart=1`). Thomas opens it when he wants to try the real thing.
- **Lifetime.** The codespace stops when idle, and nothing runs when nobody looks.
- **Cost:** GitHub Free includes 120 hours and 15 GB a month, and 2-core machines count double ([billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces)). Without a payment method, usage stops at the quota instead of being billed.
- **Showing it to someone.** A forwarded port can be made public (`https://<codespace>-<port>.app.github.dev`), with no sign-in ([ports](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace)). Use this only for short demos, with demo mode on.

### 7.3 The UI in mock mode (from the first UI milestone)

The front-end has a build flag that replaces the API with fixtures generated from the OpenAPI and the demo dataset (MSW). That build is static, so every UI iteration can be published on Cloudflare Pages and compared side by side with no backend at all. The real backend stays covered by tiers 2–4 and by Codespaces.

### 7.4 The public instance (from the public beta)

- **Where.** On EMBL's Kubernetes, with the Helm chart, as depictio does: a self-hosted runner inside EMBL, `workflow_dispatch` only, behind a GitHub environment with a required reviewer.
- **What is not copied from depictio** (`docs/reviews/R8b-depictio-tooling.md`, DEP-T-032): `--insecure-skip-tls-verify` and values files kept on the runner's disk.
- **Before it exists:** nothing public runs Spectio's backend. Inbound webhook tests run in CI against a local instance.

## 8. Claude in the development loop

| Mechanism | Use in Spectio | Reference |
|---|---|---|
| Project memory `CLAUDE.md` | project rules, phase, commands | [memory](https://code.claude.com/docs/en/memory.md) |
| Subagents `.claude/agents/` | eight reviewers and builders (spec, facts, constraints, security, UX, depictio liaison, tests, infra) | [sub-agents](https://code.claude.com/docs/en/sub-agents.md) |
| Skills `.claude/skills/` | workflow skills (`review-round`, `apply-findings`, `verify-claims`, `render-board`, `spike`) + vendored superpowers and Karpathy guidelines | [skills](https://code.claude.com/docs/en/skills.md), `.claude/skills/THIRD_PARTY.md` |
| Worktrees | one agent and scenario per worktree (`isolation: worktree` for implementer agents later) | sub-agents docs |
| Cloud sessions in parallel | independent spikes and review rounds, each on its own branch | [cloud sessions](https://code.claude.com/docs/en/claude-code-on-the-web.md) |
| Auto-fix pull requests | Claude watches CI and review comments on a PR and pushes fixes (needs the Claude GitHub App) | same page, "Auto-fix" |
| GitHub Actions with Claude | PR review by `spec-reviewer` on `docs/**`, `security-reviewer` on auth, tokens, plugins and runner paths | [GitHub Actions](https://code.claude.com/docs/en/github-actions.md) |
| Routines | weekly `depictio-liaison` drift check; weekly nf-core release check against templates and `checking-scenarios.md`; nightly `verify-claims` on specs whose upstream released | [routines](https://code.claude.com/docs/en/routines.md) |
| Agent teams (experimental) | large review rounds where reviewers discuss findings | [agent teams](https://code.claude.com/docs/en/agent-teams.md) |
| sind's MCP server | agents create and break SLURM clusters through tools instead of shell | sind README |
| Playwright | e2e tests, and agents looking at the UI they built | — |

**Guard rails.**
- Agents work on branches and open PRs.
- CI tiers 0–4 must pass.
- A human merges.
- Reviewers are read-only.
- No secrets in the repository or in shared environment variables.
- Deploy credentials (Cloudflare now, EMBL later) stay in GitHub environments, never in repository-level secrets (R8b DEP-T-007).

## 9. First steps (playbook phase D)

1. **D1:** validate `.claude/` (agents load, skills appear in `/`), and add the docs CI.
2. **D2 spike (the cloud environment):**
   - does Docker, sind and kind each work in a cloud session?
   - which domains Nextflow, nf-core and the registries need;
   - can the setup script stay under 5 minutes?
3. **D3:** write `dev/versions.env`, `dev/bootstrap.sh` and `dev/doctor.sh`, and run them green in a cloud session, in CI and locally.
4. **D4:** build the fixture workflows and record the first golden fixtures (Tower protocol payloads, Snakemake logger events, `squeue` / `sacct` JSON from sind).
5. **D5:** dev previews: the Cloudflare Pages deploy with the `/versions` page, and the Codespaces dev container (§7).

## 10. Pipeline test corpus

### 10.1 Synthetic scenario pipelines (`tests/pipelines/synthetic/`)

**Two twin pipelines, one written for each engine:**
- [`nextflow/main.nf`](https://github.com/weber8thomas/spectio/blob/main/tests/pipelines/synthetic/nextflow/main.nf)
- [`snakemake/workflow/Snakefile`](https://github.com/weber8thomas/spectio/blob/main/tests/pipelines/synthetic/snakemake/workflow/Snakefile)

**What they share:**
- the same three stages (`qc` → gate → `align` → gate → `quant`);
- the same task bodies (`bin/synth.py`, deterministic and seeded);
- the same 12-sample samplesheet (three groups, one low-depth outlier, S03);
- the same failure injection (`exit`, `oom`, `oom_once`, `oom_real`, `timeout`, `flaky`), targeted at one process or rule and, optionally, one sample.

Both engines produce byte-identical results (the counts matrix compared with `diff`).

**Gate stops** use exactly what Spectio generates:
- Nextflow: a config setting `ext.when = false` on later stages (`conf/stop_after_qc.config`), then `-resume`.
- Snakemake: `--until qc_report` or `--until align_done`, then a plain rerun.

**Scenarios** are in `scenarios.yaml`. `run_scenarios.py` runs them and checks:
- exit codes;
- expected and forbidden outputs;
- content checks;
- per-process counts of completed and failed tasks, exit codes and attempts, read from the Nextflow trace or the Snakemake log;
- cached tasks after `-resume`.

| Scenario | What it proves |
|---|---|
| `happy` | 65 tasks, all outputs |
| `gate_qc_then_resume`, `gate_align_then_resume` | stop at a gate with the generated config, resume with cached work |
| `exclude_sample_and_resume` | samplesheet v2 without the outlier; downstream recomputed without it |
| `flaky_retry` | failure on attempt 1, success on retry |
| `oom_once_retry` | exit 137 once, success with more memory on attempt 2 |
| `oom_fatal`, `timeout_fatal` | failure after 3 attempts with the right exit codes (137, 143 / 124) |
| `tool_error_then_fixed_resume` | a non-retried tool error, then a resume after the fix |
| `dynamic_fanout` | chunk count decided at run time (Nextflow dynamic channel, Snakemake checkpoint): 45 ALIGN tasks |
| `fanout_medium` | 180 ALIGN tasks (PR) |
| `fanout_stress` | about 12 000 ALIGN tasks (nightly) |

**Verified runs on 2026-10-26** (this session, local executor, 2 CPUs); see `docs/research/spike-synthetic-pipelines-2026-10-26.md` and the step page [F2](../progress/W0/F2.md):

| Engine | Result |
|---|---|
| Nextflow 26.10.3 | 11 / 11 pass |
| Nextflow 25.10.9 | 11 / 11 pass (after retrying time-limit kills that carry no exit code) |
| Snakemake 9.27.1 | 11 / 11 pass. `oom_once_retry` hit a known engine fault in 4 of its 18 executions; the faulty run is repeated once and reported as `PASS*` |

**Known engine faults.** These are listed in `scenarios.yaml` under `engine_faults`, each with the log pattern that identifies it. A failed scenario that matches one is repeated once, from scratch, and reported as `PASS*`. Any other failure fails the build.

**Profiles for the same pipelines on other executors:**
- Nextflow `-profile slurm`, which includes job arrays for ALIGN;
- Nextflow `-profile k8s`, which adds the `spectio.io/run-id` pod label;
- Snakemake `--workflow-profile profiles/slurm`.

These run against sind and kind in T3 and T4.

### 10.2 Real pipelines (`tests/pipelines/real/corpus.yaml`)

Step page: [F3](../progress/W0/F3.md). Real pipelines run with their own test datasets. They are chosen to cover the scenario classes of [`checking-scenarios.md`](checking-scenarios.md) §1. Sources: `docs/research/corpus-and-ci-2026-10-26.md`.

| Source | PR tier | Nightly tier |
|---|---|---|
| nf-core (`-profile test,docker`, data from nf-core/test-datasets) | demo, rnaseq, viralrecon, methylseq, molkart | fetchngs, sarek, scrnaseq, mhcquant, differentialabundance, mag, ampliseq, taxprofiler (mcmicro: manual) |
| Snakemake Workflow Catalog (`.test/` directory, `--sdm conda`) | rna-seq-star-deseq2, dna-seq-gatk-variant-calling, ms-proteomics (dry-run only, as upstream) | rna-seq-kallisto-sleuth, dna-seq-varlociraptor, single-cell-rna-seq, chipseq, cyrcular-calling, ONT-AmpSeq |

- **`run_corpus.py`** runs one entry, a tier or everything, and writes `result.json` per pipeline.
- **The same entries are reused later:** once the server exists, they are launched *through Spectio* (runner → engine), and the checks move from exit codes to Spectio's own run states, gates and evidence.
- **Constraints:**
  - mag 5.5.0 and ampliseq 3.0.0 need Nextflow ≥ 26.04, so the 25.10 leg skips them;
  - private-repository GitHub runners have 2 CPU / 8 GB, so nf-core runs get `process.resourceLimits` from `runner_limits.private`;
  - the heaviest entries are nightly only.

### 10.3 Real outputs from the nf-core megatests (`tests/fixtures/megatests/`)

Every nf-core release runs its full-size test on AWS and publishes the results in a public bucket, `s3://nf-core-awsmegatests/<pipeline>/results-<release commit>/` (listed and read over HTTPS on 2026-10-26). These are real outputs at real scale, without running anything.
- **`tools/fixtures/megatests.py`** resolves a pipeline's newest release whose upload includes MultiQC data (`git ls-remote` for the tag → commit), lists that prefix and downloads small QC files (`fetch`). `curate` keeps, per pipeline and under 600 kB:
  - the MultiQC general statistics (rebuilt from `multiqc_data.json` when no `.txt` was published);
  - one execution trace (real process names, durations, peak memory, exit codes);
  - the params file and the software versions;
  - a few tool tables (mosdepth, STAR, Cell Ranger, airrflow sequence numbers…).
- **Pipelines** (2026-10-26): rnaseq 3.27.0, sarek 3.10.0, scrnaseq 4.2.0, smrnaseq 2.4.1, ampliseq 3.0.0, taxprofiler 2.0.1, viralrecon 2.6.0, rnafusion 4.1.3, airrflow 5.1.0, methylseq 4.2.0, chipseq 2.1.0, mag 5.4.2. Some recent releases have partial uploads (no MultiQC data, or nothing), which is why the tool falls back to an older release. `SOURCE.json` records the release, commit and prefix.
- **Used for:**
  - check bindings tested against real column names (`multiqc:qualimap_rnaseq-5_3_bias`, …);
  - the UI boards' numbers;
  - run-detail fixtures (traces);
  - later, the API's mock mode (§7.3).
- **Licence of the outputs:** they are derived from nf-core/test-datasets **[to be validated]**.

### 10.4 Real test images (`design/ui-canvas/images/`)

Imaging review and the OME-Zarr viewer are designed on real images, not drawings.
- **`tools/canvas/images.py`** reads public OME-Zarr from the IDR OME-NGFF samples (only the pyramid level needed is fetched over HTTPS) and the imaging branches of nf-core/test-datasets (sparse git). It writes WebP thumbnails, JSON side files with real numbers, and `SOURCES.md` (source, level, channels, licence per file).
- **Scenarios covered:**

  | Scenario | Data | Item decided on |
  |---|---|---|
  | HCS plate | idr0001 (96 wells, OME-Zarr plate), idr0033 Cell Painting (5 channels) | well |
  | Whole slide, brightfield IHC | idr0073 (21115 × 16433, 8 levels) | tile |
  | Imaging mass cytometry | nf-core/imcyto test ROI, idr0076 (50 channels, with labels), idr0054 | ROI |
  | Spots (Molecular Cartography) | nf-core/molkart test data | sample / region |
  | Xenium | nf-core/spatialxe test bundle (human kidney) | section |
  | Light-sheet volume | idr0066 mesoSPIM (1937 z) | sample / region |
  | 3D nuclei with labels | idr0062 | viewer component |
  | Satellite scenes | nf-core/rangeland Landsat 4/5 (56 scenes, cloud from QA_PIXEL) | scene |

- **The same sources** become the viewer's test fixtures: a multiscale image, a plate, labels, v0.4 and v0.5 stores.
- **Licences:** IDR studies are CC BY 4.0 as a rule **[to be validated per study]**; Landsat is public domain.

## 11. CI workflows

| Workflow | Trigger | What it runs |
|---|---|---|
| `docs.yml` | PR and push touching `docs/` | strict MkDocs build, Mermaid render |
| `pipelines-synthetic.yml` | PR, main, nightly | synthetic scenarios × {Nextflow 26.10.3, 25.10.9, Snakemake 9.27.1}; stress scenario nightly; artifacts with reports, logs, traces |
| `pipelines-real.yml` | PR touching the corpus, nightly, manual | matrix generated from `corpus.yaml`: nf-core with `nf-core/setup-nextflow@v3`, the catalog with `snakemake/snakemake-github-action@v2` on the workflow's own `.test` |
| `pipelines-slurm.yml` (T3) | PR touching runner code, nightly | `GSI-HPC/sind-action@v2` cluster, synthetic scenarios with the SLURM profiles. Needs cgroup v2 Docker, which GitHub runners have; this cloud session has cgroup v1, so not here |
| `pipelines-k8s.yml` (T4) | nightly | `helm/kind-action@v1` + Kueue, synthetic scenarios with the k8s profile, nf-core/demo |
| `release-please.yml` | push to main | release PR with version bump and changelog (§12) |
| `previews.yml` | PR, push to main, `v*` tags, wave approvals, manual | build the docs site, deploy it to Cloudflare Pages under its own branch alias, regenerate `/versions`, comment the preview and Codespaces links on the PR (§7) |

## 12. Versioning and releases

- **Commit and PR titles: Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`). The PR title becomes the squash commit, so the title is what is checked.
- **Release PR.** `release-please` keeps one open on `main`, with the next version and a concise `CHANGELOG.md` section grouped by type. Each line links the PR and its commit.
- **Releasing.** Merging the release PR tags `vX.Y.Z`, creates the GitHub release, and triggers the image, Helm chart and PyPI builds.
- **One version train for the core** (`spectio`, `spectio-server`, Helm `appVersion`), kept in step with the `linked-versions` plugin once the Python packages exist. `spectio-sdk` follows its own semver (`architecture-plugins-and-packaging.md` §4). For now `release-type: simple` versions the repository as a whole.
- **Image tags** (`docker/metadata-action@v6`): `X.Y.Z` and `X.Y` on releases, `sha-<7>` on every build, `edge` on main, `pr-<n>` on previews.
- **Versions you can see:**
  - `GET /api/v1/version` returns `version`, `git_sha`, `build_date`, `schema_revision` and `deployment`;
  - the UI footer shows the version and links to its changelog entry;
  - every preview and instance shows a "vX.Y.Z+sha" banner;
  - `spectio --version` prints the client version and warns when the server differs.
- **Pre-1.0 policy:** minor versions may break the API, and the changelog says so. From 1.0, semver applies to the public API and the plugin SDK.
- **The version follows the importance of the change, automatically** (`release-please-config.json`):

  | Merged since the last release | Next version (while < 1.0) |
  |---|---|
  | only `docs`, `test`, `ci`, `chore`, `refactor` | no release |
  | at least one `fix` or `perf` | patch: 0.3.1 → 0.3.2 |
  | at least one `feat` | minor: 0.3.1 → 0.4.0 |
  | a breaking change (`feat!:` or a `BREAKING CHANGE:` footer) | minor too (`bump-minor-pre-major`), never 1.0.0 |

  - **Design phase:** `feat` and `fix` are kept for product code. Tooling (`tools/`, `tests/`, workflows) uses `chore`, `test` or `ci`. Docs, specs and research use `docs`. So no release is cut before the walking skeleton, which is planned as `0.1.0`.
  - **Docs and tests do not cut releases.** They are hidden from the generated `CHANGELOG.md`, because the curated changelog (`documentation-system.md` §6) covers docs. Whether a visible changelog section alone makes a commit releasable is **[to be validated]** with a dry run (`release-please release-pr --dry-run`).
  - **1.0.0 is never automatic.** release-please only reaches it when `release-as: 1.0.0` is set in the config (release-please manifest docs). A guard (`release-guard.yml`) also fails any release PR at ≥ 1.0.0 unless the repository variable `ALLOW_V1` is `true`. Thomas sets that variable once the 1.0 gate (§14) is met.

## 13. Instance verification and access

**Dev previews (now).**
- After each deploy, `previews.yml` fetches the deployed URL and checks:
  - the home page and `/versions` answer;
  - the build's commit SHA is in the page footer;
  - a sample of internal links resolves.
- The preview and Codespaces links are posted on the PR.

**The public instance (from the beta, §7.4).** Every deploy is verified through its public URL:
1. **Version:** `/health/ready` and `/api/v1/version`, whose `git_sha` must match the deployed commit.
2. **Playwright smoke test (T6):**
   - sign-in by magic link (Mailpit in the test profile);
   - opening a run;
   - opening a gate and approving it on a synthetic run;
   - the phone viewport.
3. **Share-link round trip:** create a link, open it in a fresh browser context, check its scope, revoke it, and check that it now fails.

**Access without accounts.**
- **Share links.** On the public instance, demos and outside reviewers use scoped share links (`authentication-and-access.md` §2) instead of shared passwords.
- **Demo mode.** Visitors without a link see read-only demo data.
- **Nightly reset.** The demo data is reset every night from a known backup, which also tests restore.

## 14. Release stages and the 1.0 gate

Spectio stays in 0.x until it has been checked, in a fairly robust way, against several use cases and by several users. Each stage has an entry condition, and the docs say which stage a version belongs to: the changelog block's admonition and a badge on the landing page.

| Stage | Versions | Who uses it | Entry condition |
|---|---|---|---|
| **Design** | none | Thomas and the agents | — |
| **Walking skeleton** | 0.1.x | Thomas, on the synthetic pipelines | `GO` gate passed (pipeline W4); one run crosses every layer once (launch, observe, gate, resume, hand-off) |
| **Private alpha** | 0.2 – 0.4 | 3 to 5 design-partner groups at EMBL (`docs/research/adoption-and-positioning-2026-10-26.md`) | install in under 30 min from the docs alone; real corpus green nightly; backup and restore tested; R5 security findings closed |
| **Public beta** | 0.5 – 0.9 | anyone, with a public demo instance | 2 weeks without a P0/P1 bug at the partners; upgrade tested across 3 consecutive minors; every guide has a cast or screenshots |
| **1.0** | 1.0.0 | stable for institutional installs | the **1.0 gate** below, checked by a review step (`R-v1`, added to the pipeline when the beta starts) and decided by Thomas |

**The 1.0 gate** (all of them):
1. **Use cases.** At least one real pipeline from each scenario class of `checking-scenarios.md` §1 runs through Spectio, with a gate decided by a person other than its author.
2. **Users and sites.** At least 3 groups, 2 of them outside Thomas's own team, and 10 or more active users over 8 consecutive weeks. At least one site other than EMBL **[to be validated: realistic target]**.
3. **Engines and schedulers.** Nextflow and Snakemake on SLURM and on Kubernetes in daily use, plus the local runner.
4. **Tests.** The synthetic suite is green on every PR, and the real corpus is green nightly for 4 consecutive weeks. The auth matrix (`authentication-and-access.md` §6) and the Playwright suite are green.
5. **Operations.** An upgrade path is tested across at least 3 minors with backup, restore and migration. No open P0 or P1 bug. A documented support channel answers within a week.
6. **Contracts.** The OpenAPI and the plugin SDK are frozen, with a deprecation policy. The data model has a migration test for every revision.
7. **Docs.** Install, user, admin and operator guides, the reference (API, CLI, configuration), and a curated changelog for every 0.x version.
