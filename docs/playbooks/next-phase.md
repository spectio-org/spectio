# Playbook — from specs to implementation

Status: v0.1 · 2026-10-25.

> **You do not run these steps one by one.** They are the reference prompts for the steps of [`pipeline.yaml`](pipeline.yaml), which the `/autopilot` skill runs in waves, in parallel, with verification and triage. To run everything, see [`autopilot.md`](autopilot.md). Run a single step by hand only to debug it (`/autopilot --only R5`).

Order of work: **R** review rounds → **D** development layer → **T** test infrastructure → **P** planning → implementation.
- Each step has a ready-to-paste prompt for Claude Code, started at the repository root.
- Steps marked ∥ can run as parallel cloud sessions (`claude --cloud "<prompt>"`), one branch each.
- Every step ends with something committed: a review file, a research note, a script, or a plan.

## How to start

1. Clone the repository and open Claude Code at its root. `CLAUDE.md`, the agents and the skills load automatically. Check with `/agents` and by typing `/` (you should see `review-round`, `apply-findings`, `verify-claims`, `render-board`, `spike`, `writing-plans`, …).
2. **Locally,** you may install the plugins instead of the vendored skills: `/plugin install superpowers@claude-plugins-official`, plus the Karpathy guidelines (see `.claude/skills/THIRD_PARTY.md`). A UI design plugin such as `frontend-design` from the official marketplace is useful for phase T and later. Check that it exists in `/plugin` first.
3. **For review rounds, use plan mode** (`claude --permission-mode plan`) or tell Claude that specs are read-only. Reviewers write only into `docs/reviews/`.

**Kick-off prompt** (paste once at the start of a session):

```text
Read CLAUDE.md, docs/map.md and docs/playbooks/next-phase.md. We are in the
pre-implementation phase: no product code. Summarise in 10 lines what Spectio is,
which specs own which topics, and which playbook step comes next given what already
exists in docs/reviews/ and docs/research/. Then wait for my go.
```

## Phase R — review rounds (no code)

Each round uses `/review-round <id> "<focus>"`. The skill dispatches the agents in parallel, checks blockers and majors itself, and writes `docs/reviews/<id>.md`. You triage (mark findings accepted or rejected), then run `/apply-findings <id>`.

### R1 · Consistency across specs

```text
/review-round R1-consistency "Contradictions, undefined contracts and ownership
problems across all docs/specs/*.md and docs/decisions/log.md. Dispatch spec-reviewer
four times in parallel with these scopes: (a) synthesis + ui-spec, (b)
api-and-data-model + admin-and-operations, (c) architecture-plugins-and-packaging +
cli-and-shared-libraries + dev-environment-and-testing, (d) checking-scenarios +
schedulers-and-monitoring + depictio-ecosystem-reuse. Each reviewer also checks its
scope against the decision log. Pay special attention to names that changed over time
(maintainer→editor, agent→runner, Settings→Administration, spectio-runner merged into
spectio, broker split into tasks/pubsub)."
```

### R2 · Fact verification ∥

```text
/verify-claims docs/specs/schedulers-and-monitoring.md docs/specs/synthesis.md
```
```text
/verify-claims docs/specs/architecture-plugins-and-packaging.md docs/specs/dev-environment-and-testing.md docs/specs/cli-and-shared-libraries.md
```
```text
/verify-claims docs/specs/api-and-data-model.md docs/specs/checking-scenarios.md docs/specs/admin-and-operations.md
```
Then:
```text
List every remaining "[to be validated]" in docs/specs with the cheapest way to settle
it (doc lookup, code read, or spike). Write docs/reviews/R2-open-validations.md and
propose which ones become spikes in phase D/T.
```

### R3 · End-to-end journeys (finding gaps)

```text
/review-round R3-journeys "Scope: version 0.0.1 only (docs/specs/mvp-0.0.1.md and
dev-environment-and-testing.md §15): one user, no sign-in, engines on the same machine.
Walk these journeys step by step through the specs and the UI boards, and report every
step that is not specified (screen, endpoint, event, state, error): (1) a researcher
installs the Python bundle on a laptop, registers nf-core/rnaseq, launches it with a QC
gate after the first stage, reads the checks, approves and the run continues; (2) the
same with a Snakemake workflow, where the gate fails, the researcher changes two
parameters and relaunches, then compares the two runs' parameters; (3) a run fails on
one task: the researcher finds the failing task, reads its log and relaunches from the
cache; (4) the server restarts while a run is active, and the run's state, tasks and
stages are still right afterwards. Use spec-reviewer for (1)(2), constraints-hunter for
(3)(4), and ux-reviewer to render every board touched. Out of scope: users, roles,
SLURM, Kubernetes, depictio, LabID, phones."
```

### R4 · Implementation constraints and risks

```text
/review-round R4-constraints "Use constraints-hunter twice in parallel: (a) server,
data model, events, SQLite/Postgres, SSE, outbox, tasks, backups — with numbers for a
run of 100 000 tasks and 50 concurrent runs; (b) runner, engines, schedulers,
Kubernetes, HPC site policies, third-party API stability (TraceObserverV2 @Beta,
nf-spectio next to nf-tower, Snakemake logger interface, Kueue v1beta2, slurmrestd
data_parser). Each risk needs the cheapest spike that would confirm or kill it. Finish
with a ranked spike list."
```

### R5 · Security and threat model

```text
/review-round R5-security "Use security-reviewer on the whole design with STRIDE per
trust boundary (browser, embeds, service accounts, runners, engine ingest, AI agents on
gates, event bridges, plugins, backups, depictio trust, co-hosting proxy, and every
sign-in method in docs/specs/authentication-and-access.md: magic links, share links,
provisioning, OIDC and SAML). Check
tenancy leaks through search, SSE, webhooks, exports, logs and the task ledger. Produce
the findings plus a draft docs/specs/security-and-threat-model.md for me to review."
```

### R6 · API contract against the UI

```text
/review-round R6-contract "Scope: version 0.0.1 only (docs/specs/mvp-0.0.1.md and
dev-environment-and-testing.md §15). Draft an OpenAPI 3.1 skeleton (paths, schemas, no
implementation) for the 0.0.1 features only (workflows, launch, runs, tasks, stages,
events/SSE, relaunch with parameters, parameter history, checks and gates) from
api-and-data-model.md into spikes/openapi-draft/openapi.yaml on a spike branch. Then use
ux-reviewer to check that every number, list and action on the boards listed in
mvp-0.0.1.md §2 can be served by that contract, and spec-reviewer to find 0.0.1
endpoints the spec mentions but the draft cannot express. Report missing or
inconsistent fields as findings."
```

### R7 · UI review ∥

```text
/review-round R7-ui "Use ux-reviewer three times in parallel: (a) desktop core boards
(Overview, Runs, RunDetail, RunScheduler, Review*, Launch*); (b) Workflows, Environments,
EnvStorage, EnvKubernetes, EnvCapacity, Administration boards; (c) all phone boards.
Render every board with /render-board before judging. Focus on missing loading /
empty / error / no-permission states, accessibility, and consistency with the Legend
board and design/tokens/spectio-tokens.css."
Include the sign-in flows of docs/specs/authentication-and-access.md §5 (sign-in page,
magic-link confirmation, share-link landing, share dialog "Create link" tab, Settings →
Sign-in): propose the boards that are missing.
```

### R8 · depictio and LabID drift ∥

```text
/review-round R8-depictio "Use depictio-liaison on the current depictio main and
LabID repositories. Re-check every claim in api-and-data-model.md §13,
depictio-ecosystem-reuse.md and the research notes. Propose a new dated research note
with what changed, and update the status of the 'requests to make to depictio' list."
```

### R9 · Prior art and landscape, again

```text
Use fact-checker and constraints-hunter in parallel to re-scan the landscape since
synthesis.md was written: Seqera Platform / Tower open-source status, nf-tower
alternatives, Snakemake monitoring tools (panoptes, snkmt, flowo), WES implementations,
Galaxy, Arvados, Flyte, Prefect / Dagster for bioinformatics, GA4GH TES, nf-prov and
WRROC tooling. For each: licence, activity, overlap with Spectio, anything worth
reusing or integrating. Write docs/research/landscape-<date>.md and list the spec
changes it implies as findings in docs/reviews/R9-landscape.md.
```

### R11 · Documentation review ∥

```text
Use the doc-reviewer agent with a fresh context, plus the ux-reviewer for the landing
page. Build the site strictly, then render docs/index.md at 1440×900 and 390×844 in
light and dark, and look at the PNGs. Review the whole site against
docs/specs/documentation-system.md: the landing page (§2), the Progress pages of W0
(§3.2, rubric §4.2: re-run three commands per page), the figures and media (open every
PNG, extract video frames), navigation and ownership (docs/map.md). Also check that the
spec itself is implementable with the tools in tools/docs, tools/diagrams and
tools/media. Write findings with prefix DOC- to docs/reviews/R11-docs.md. Do not edit pages.
```

### R10 · Synthesis and go / no-go

```text
Read every docs/reviews/R*.md. Make one table of open findings by severity and spec,
and confirm that all blockers are applied or explicitly deferred with a reason. Then
propose: (1) the MVP cut: the first usable release is 0.0.1, decided by Thomas
(docs/specs/dev-environment-and-testing.md §15); check that cut against the open
findings and list which blockers it defers; (2) the list of open questions for EMBL
IT (cluster, Kubernetes, storage, auth); (3) a go / no-go with the conditions. Write
docs/reviews/R10-synthesis.md and stop for my decision.
```

## Phase D — development layer and automation

### D1 · Validate the Claude setup

```text
Check that every agent in .claude/agents loads (run `claude plugin validate
.claude/agents` if available, or `claude --debug` and read why any file is skipped),
that every skill appears, and that CLAUDE.md is accurate for the repository as it is
now. Fix what is wrong. Add a CI job that fails when an agent or skill file has invalid
frontmatter. Commit on a branch and open a PR.
```

### D2 · Spike: what the cloud environment can do ∥

```text
/spike cloud-env "In this cloud session, which of these work and with what limits:
docker run, docker compose, sind (create a 1+1 cluster, sbatch --wait), kind (create a
cluster, run a Job), Nextflow 26.10 install and a hello run, Snakemake 9 with the SLURM
executor plugin against sind, Playwright + Chromium, mermaid-cli. Record memory, disk,
timing and every network domain that was blocked by the proxy. Conclude with the exact
Custom allowlist and the setup-script budget."
```

### D3 · Bootstrap and doctor scripts

```text
Use infra-engineer. Using the D2 spike results, write dev/versions.env (exact pins),
dev/bootstrap.sh (idempotent, < 5 min with --ci, parallel installs) and dev/doctor.sh
(one smoke test per layer, non-zero exit naming the failing tool), as specified in
docs/specs/dev-environment-and-testing.md §1. Run them here and in a GitHub Actions job.
Paste the doctor output in the PR. Then write the cloud environment instructions
(network list, env vars, setup script) into the spec §2.
```

### D4 · CI and Claude in GitHub ∥

```text
Use infra-engineer. Add GitHub Actions: tier 0 checks for docs (already: docs.yml),
plus a Claude PR review workflow following https://code.claude.com/docs/en/github-actions.md
that runs the spec-reviewer agent on PRs touching docs/** and the security-reviewer
agent on every PR that changes code, posting findings as review comments. Add the
security checks on every PR of dev-environment-and-testing.md §11 (secret scanning,
dependency audit for Python and JS, SAST, workflow linter), verifying each tool from its
own docs first. Verify the action's current inputs from its README before writing YAML.
Document required secrets in the PR description; do not add any secret yourself.
```

### D5 · Dev previews: Cloudflare Pages and Codespaces

```text
Use infra-engineer. Make the dev previews of docs/specs/dev-environment-and-testing.md §7
work end to end, once Thomas has set the CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID
secrets in the GitHub environment "previews" (inbox #10).
- previews.yml: open a test PR and check the preview URL, the branch alias, the /versions
  page and the PR comment; check the build SHA in the footer; check that a second push
  keeps the first deployment's URL reachable; validate the real shape of the deployments
  API against tools/previews/versions_page.py and fix it.
- Add a "wave approved" path: when a wave-review PR is labelled wave-approved, deploy a
  wave-<id> preview.
- Codespaces: open the branch with the README badge and check that setup.sh finishes,
  that the docs are served on port 8000, and that the toolchain matches dev/versions.env.
  Configure a prebuild for main if it fits the free quota.
- Record whether Cloudflare direct uploads count as builds, and the codespace start time.
Leave the step's docs with write-docs, including a sketch of the preview flow (PR ->
Actions -> Cloudflare deployment kept at its own URL -> /versions; Codespaces on demand).
```

### D6 · Docs pipeline in CI ∥

```text
Make the documentation system run by itself, following docs/specs/documentation-system.md
§1, §7 and §8. Wire tools/docs/check.py into docs.yml as the required checks docs-gate
and pr-body; deploy the site with mike (dev from main, X.Y on release, aliases latest
and stable) on the Cloudflare previews of D5 (versions side by side, /versions page);
evaluate Zensical against this site; adopt depictio's size hook hooks/shared_images.py
before the first mike version or when docs/assets passes 50 MB
(documentation-system.md §1); add hooks/progress.py
outputs to the build check. Settle the Virgil font licence (tools/diagrams/FONT-LICENSE.md)
or switch fonts, and make the figure scripts render the same PNGs in CI. Draw the figures
tracked from F4 and F6 (a magic-link and share-link sketch: hash at rest, atomic burn,
scope claim; the three telemetry systems and where their data goes). Open a PR whose
body follows the template and passes the pr-body check, with the autopilot-loop figure.
```

`hooks/shared_images.py` is a D6 deliverable with a 50 MB threshold *(assumed — pending Thomas, inbox #30)*.

## Phase T — test infrastructure

### T1 · Fixture workflows

```text
Use test-architect. The fixture workflows are the synthetic pipelines in
tests/pipelines/synthetic (dev-environment-and-testing.md §3 and §10.1: stages, gate
points, failure injection, fan-out, job arrays in the slurm profile, the Snakemake
checkpoint). Prove each failure mode locally with the local executor and record the
engine outputs (Nextflow trace, Snakemake log) as golden fixtures named with the tool
version. Also run the gate stop-and-resume check on the nf-core/rnaseq and nf-core/sarek
test profiles with the local executor (dev-environment-and-testing.md §3) and record
cached-task counts and exit codes.
```

The synthetic pipelines of `dev-environment-and-testing.md` §10.1 replace the separate `nf-toy` and `smk-toy` fixtures in T1–T4 and P1 *(assumed — pending Thomas, inbox #28)*. The rnaseq and sarek stop-and-resume check runs here, on the local executor; `ui-spec.md` §5.1 owns the pipeline requirements and the "gates unavailable" state *(assumed — pending Thomas, inbox #28)*.

### T2 · Engine event capture (golden fixtures) ∥

```text
/spike engine-events "Run the synthetic Nextflow pipeline
(tests/pipelines/synthetic/nextflow) with a minimal TraceObserverV2 plugin (a first
nf-spectio) that posts every event to a tiny capture server (write both under
spikes/engine-events/, the server ~50 lines, logs every request body), on
Nextflow 25.10 and 26.10, including a failed task, a retry and -resume. Run it once
more with -with-tower pointed at a second capture endpoint, and check that both
observers report the same run (docs/decisions/0001). Do the same for the synthetic
Snakemake pipeline (tests/pipelines/synthetic/snakemake) with a minimal Snakemake logger
plugin that writes every event as JSON, including a checkpoint. Save every payload as a
golden fixture. Also record `event.handler.task.outputs` in `onTaskComplete` and the
order of `onProcessTerminate` events in the golden fixtures (checking-scenarios.md
§11.1, §11.5). Compare what arrives with synthesis.md §2bis/§2ter and report every
difference."
```

Fixtures: the synthetic pipelines (see T1) *(assumed — pending Thomas, inbox #28)*.

### T3 · Mini SLURM with sind ∥

```text
Use test-architect and infra-engineer. Create the sind profiles slurm-mini, slurm-site
and slurm-rest from dev-environment-and-testing.md §4.1 (partitions, slurmdbd,
association limits, a maintenance reservation, slurmrestd with JWT). Run the synthetic
pipelines (Nextflow -profile slurm, Snakemake --workflow-profile profiles/slurm) on
slurm-site with each failure mode; record squeue --json, sacct --json,
sinfo --json and slurmrestd responses as golden fixtures; check each pending reason and
failure class in schedulers-and-monitoring.md §3.5 actually appears, and power-cycle a
node to get NODE_FAIL. Check whether a Snakemake head submitted with sbatch works with
snakemake-executor-plugin-slurm (the plugin warns against running inside a SLURM job;
dev-environment-and-testing.md §15.1, §15.3) and record the outcome for the 0.0.1
fallback. Report what the spec gets wrong.
```

Fixtures: the synthetic pipelines (see T1) *(assumed — pending Thomas, inbox #28)*.

### T4 · kind and Kueue ∥

```text
Use test-architect. Create k8s-mini and k8s-kueue (§4.2). Run nf-core/demo -profile
test,docker and the synthetic Nextflow pipeline with -profile k8s; capture pod and Job
objects, events, OOMKilled, and Kueue Workload conditions and visibility positions as
fixtures. Verify that both ServiceAccounts in schedulers-and-monitoring.md §4 (runner,
and engine head for Nextflow 25.10 and 26.10) are sufficient and minimal.
```

Fixtures: the synthetic pipelines (see T1) *(assumed — pending Thomas, inbox #28)*.

### T5 · Scenario runner and isolation

```text
Use test-architect. Write dev/scenario.py (up / down / list) and tests/scenarios/*.yaml
as in §5: one network, Compose project, port range, data dir and sind realm or kind
cluster per scenario id; JSON output with URLs. Prove that three scenarios run in
parallel without collisions, and that `down` leaves nothing behind (docker ps, docker
network ls, kind get clusters).
```

### T6 · Playwright end-to-end skeleton

```text
Use test-architect. Set up tests/e2e with Playwright (TypeScript): a config that takes
the base URL from scenario JSON, desktop and phone projects, screenshot naming after
canvas boards, and a side-by-side HTML report (real page vs design/ui-canvas render via
tools/canvas/render.js). Until the product exists, run it against the Cloudflare
docs preview and a static page.
```

### T7 · Real pipeline corpus green in CI ∥

```text
Make pipelines-real.yml pass on GitHub runners for the PR tier and run the nightly tier
(tests/pipelines/real/corpus.yaml). Use run_corpus.py (git clone at the pinned tag,
--limits private on private runners). For each failure, decide: a runner limit (adjust
resourceLimits or move the entry to nightly), an upstream issue (link it), or a corpus
bug (fix it). Measure the memory each runner type leaves free to the local executor and set
runner_limits from it. Record pass/fail, duration and peak memory per entry in a dated research
note, and update the corpus tiers. Snakemake catalog entries run on their own .test data
with snakemake-github-action. Keep the synthetic suite green on all three engine legs.
```

## Phase P — decomposition and planning

### P1 · Walking skeleton plan (0.0.1, on a cluster)

```text
Use the brainstorming skill, then the writing-plans skill. Goal: the 0.0.1 cut of
docs/specs/dev-environment-and-testing.md §15.1, deployed as §15.3 says (summary:
docs/specs/mvp-0.0.1.md). One user runs `spectio serve` (SQLite on node-local disk, no
accounts) under their own account on a SLURM login node and opens it through an SSH
tunnel with a one-time token link; every request needs the token, and §15.3's security
requirements are tasks with their own tests. From the UI it launches the synthetic
Nextflow pipeline through nf-spectio and the synthetic Snakemake pipeline through the
Spectio logger plugin: the built-in runner submits each Nextflow head with sbatch, and
the Snakemake head too unless spike T3 rules it out (then it runs on the login node, per
§15.1); each engine sends its tasks through its own SLURM executor. The plugins write events to the spool in
the run directory and the built-in runner reads it; nothing posts over the network. It
shows the runs in the Runs table and Run detail with their state, tasks, stages and head
job state, relaunches with changed parameters (a child run), and shows the parameter
history (what each run used, what changed). Tests: the local executor for unit and API
tests; the mini SLURM cluster (sind, slurm-mini, dev-environment-and-testing.md §4.1,
built by step T3) for the end-to-end launch, spool and restart tests. Out of scope: QC
checks and gates, Kubernetes, a shared server or remote runner, sign-in, the depictio
hand-off, and everything else §15 defers. The plan must list files, tests first (TDD),
and the verification command for every task. Write
docs/plans/P1-walking-skeleton.md.
```

Fixtures: the synthetic pipelines (see T1) *(assumed — pending Thomas, inbox #28)*.

### P2 · Milestone plans ∥

```text
Use writing-plans for each MVP milestone from docs/reviews/R10-synthesis.md, one plan
file per milestone in docs/plans/, each task ≤ half a day, with dependencies, the owning
spec section, tests, and the scenario from tests/scenarios that proves it done.
```

### P3 · Execution

```text
Execute docs/plans/P1-walking-skeleton.md with the subagent-driven-development skill:
one fresh implementer subagent per task in its own worktree, then spec-compliance
review and code-quality review (requesting-code-review), test-driven-development
throughout, verification-before-completion before marking a task done. Pass sections 2
and 3 of karpathy-guidelines (simplicity first, surgical changes) to every task reviewer
as global constraints. After the last task, run the review-code skill on the whole
branch (code-reviewer and security-reviewer, then code-simplifier) before
finishing-a-development-branch.
Stop and ask me at any spec ambiguity instead of guessing.
```

## Recurring routines (once the skeleton exists)

| Routine | Schedule | Prompt |
|---|---|---|
| depictio drift | weekly | `/review-round Rw-depictio-<date> "depictio-liaison on current main"` |
| nf-core releases | weekly | "Check nf-co.re pipelines.json for releases since last week for pipelines in checking-scenarios.md and depictio templates; report output path changes that break gate evidence globs." |
| Claim freshness | monthly | `/verify-claims docs/specs/schedulers-and-monitoring.md` (and others whose upstream released) |
| Demo instance reset (from the beta) | nightly (CI) | restore the known backup on the public instance, run the Playwright smoke |
