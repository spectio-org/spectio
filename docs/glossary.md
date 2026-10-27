# Glossary

The codes and words used across the specs, the pipeline, the reviews and the dashboard, each with one line and a link to the document that owns it. This page owns only the legend of codes; every definition stays in its owning spec.

## 1. Pipeline codes

### 1.1 Waves

A **wave** is a group of pipeline steps that can start together once the waves it depends on are done. Owner: [`pipeline.yaml`](playbooks/pipeline.yaml), explained in [Autopilot](playbooks/autopilot.md).

| Code | Wave |
|---|---|
| `W0` | Foundations, done interactively with Thomas (2026-10-24 to 26) |
| `W1` | Independent reviews and the first spike (read-only, parallel) |
| `W2` | Triage and apply W1 findings, then the reviews that need cleaned specs |
| `W3` | Development layer and test infrastructure (parallel worktrees) |
| `W4` | Synthesis, plan and the one human decision |
| `W5` | Implementation of the walking skeleton |

### 1.2 Step codes

A **step** is one unit of work in a wave. Its prompt is the heading of the same code in [Next phase](playbooks/next-phase.md), and its Progress page is `progress/<wave>/<step>.md`.

| Code | Family | Kind | What the step does |
|---|---|---|---|
| `F1`–`F7` | Foundation | `foundation` | Specs, agents, tools and process set up with Thomas before the autopilot ran |
| `R1`–`R11` | Review round | `review` | Read-only reviewers report findings into `reviews/<round>.md`; specs are not edited |
| `D1`–`D6` | Development layer | `build`, `spike` | Dev environment, CI and tooling that later code needs |
| `T1`–`T7` | Test infrastructure | `build`, `spike` | Fixtures, local clusters, scenario matrix and end-to-end tests |
| `P1`–`P3` | Planning and implementation | `plan`, `build` | Implementation plan, then the walking skeleton |
| `TRIAGE1`–`3` | Triage | `triage` | Sorts every finding of the listed rounds with the [triage policy](playbooks/triage-policy.md) |
| `APPLY1`–`3` | Apply | `apply` | Applies accepted findings to the specs, with a dated entry in the [decision log](decisions/log.md) |
| `GO` | Human gate | `human_gate` | The go / no-go decision for implementation; only Thomas answers it |

The **kind** decides how the autopilot runs a step ([autopilot skill §2](playbooks/autopilot.md)):

| Kind | Run as |
|---|---|
| `foundation` | Done by hand before the autopilot; never scheduled |
| `review` | Parallel read-only reviewer agents |
| `spike` | A throwaway experiment in a git worktree under `spikes/<name>/`, ending with a dated note in `research/` |
| `build` | One worker in its own worktree, then `review-code` |
| `plan` | One worker with the `writing-plans` skill |
| `triage` | The orchestrator itself, one at a time |
| `apply` | The `apply-findings` skill, one at a time |
| `human_gate` | Never run; it waits for Thomas in the inbox |

### 1.3 Step statuses

State lives in `.autopilot/state.json`; `pipeline.yaml` holds no status.

| Status | Meaning |
|---|---|
| `pending` | Not started; some dependency is not done yet |
| `ready` | Every dependency is done; the next tick can take it (computed by `tools/autopilot/ready.py`, not stored) |
| `running` | Claimed by a tick, with `started_at` and `base` |
| `done` | Exit check, docs gate and reviews passed |
| `failed` | The last attempt failed; it is retried while attempts remain |
| `blocked` | Failed twice; an inbox entry explains what was tried |
| `waiting_human` | A human gate, or a step held by an open inbox question |

On the dashboard, a human gate whose dependencies are done shows as **Thomas**.

### 1.4 Autopilot words

- **Tick:** one `/autopilot` invocation: sync, pick the batch, run it, verify, record, print the status line.
- **Exit check:** the command a step or wave must pass to be `done`.
- **Integration branch:** `autopilot/integration`, where every finished step is committed.
- **Promotion PR:** the pull request from `autopilot/integration` into `main`, merged with a merge commit once every check passes.
- **Budget:** the share of the weekly usage window a run may spend ([autopilot §6](playbooks/autopilot.md)).

## 2. Review codes

### 2.1 Finding prefixes

Each finding has an ID made of the prefix of the agent that found it and a number, for example `SR-012`. The finding format is owned by [Reviews](reviews/README.md).

| Prefix | Found by |
|---|---|
| `SR` | spec-reviewer: contradictions, gaps, unclear contracts |
| `FC` | fact-checker: claims about external tools against primary sources |
| `CH` | constraints-hunter: implementation risks, scale limits, operations |
| `SEC` | security-reviewer: threat model, authz, secrets, supply chain |
| `UX` | ux-reviewer: UI boards against the UI spec |
| `DL` | depictio-liaison: compatibility with depictio and LabID |
| `DEP-T` | depictio-liaison, tooling and ecosystem re-audit (R8b) |
| `DOC` | doc-reviewer: the documentation review round (R11) |
| `TA` | test-architect |
| `IE` | infra-engineer |
| `CR` | code-reviewer, one file per build step in `reviews/code/<step-id>.md` |

### 2.2 Severity and status

- **Severity:** **blocker** (implementation cannot start, or would build the wrong thing), **major** (real problem, will cost rework), **minor** (worth fixing, low risk).
- **Status:** `open` → `accepted`, `rejected` (with the reason) or `inbox` at triage → `applied` once the spec carries the fix.
- **Inbox #n:** a numbered question for Thomas in the [inbox](reviews/inbox.md).
- ***(assumed — pending Thomas, inbox #n)*:** text a step applied on a recommended default while the question is open; it is reverted if Thomas answers otherwise ([triage policy](playbooks/triage-policy.md)).
- **[to be validated]:** a fact about another tool that has no source yet.

## 3. Product terms

| Term | One line | Owner |
|---|---|---|
| Run | One launch of a workflow by an engine, with its parameters and inputs | [api §7](specs/api-and-data-model.md#7-database-schema) |
| Run states | `queued`, `running`, `awaiting_review`, `pausing`, `paused`, `succeeded`, `failed`, `cancelling`, `cancelled` | [api §7.1](specs/api-and-data-model.md#71-run-and-gate-state-machines), shown as in [UI §3.1](specs/ui-spec.md#31-run-states) |
| Stage | A named part of a workflow (alignment, QC, calling); the unit of progress and of rerun | [UI §5.1](specs/ui-spec.md#51-stages-gates-and-spectioyml) |
| Stage gauge | The four-part emblem used as a progress indicator | [UI §3.2](specs/ui-spec.md#32-stage-gauge-the-emblem-as-a-progress-indicator) |
| Gate | A stop after a stage where a person or a rule decides before the run continues | [UI §5.1](specs/ui-spec.md#51-stages-gates-and-spectioyml) |
| Item | What a reviewer decides on: a sample, a bin, a cell, an image, a model | [checking §1](specs/checking-scenarios.md#1-inventory-what-a-reviewer-decides-on) |
| Check | A measured value compared with a threshold, per item or per run | [checking §4](specs/checking-scenarios.md#4-checks-one-vocabulary) |
| Evidence | What people look at to decide: reports, plots, tables, images | [checking §3](specs/checking-scenarios.md#3-evidence-what-people-look-at) |
| Decision | A verb applied at a gate: approve, stop, keep, exclude, redo, edit… | [checking §5](specs/checking-scenarios.md#5-decisions-one-set-of-verbs) |
| Relaunch modes | **Resume** (reuse finished work; labelled Continue at a gate), **Rerun from a stage**, **Restart** | [UI §4.6](specs/ui-spec.md#46-launch-and-relaunch) |
| Lineage | The chain of runs linked by resume, rerun or restart, with what changed | [UI §4.4](specs/ui-spec.md#44-run-detail) |
| `spectio.yml` | The manifest in a workflow repository declaring stages, gates, checks and evidence | [checking §12](specs/checking-scenarios.md#12-spectioyml-reference) |
| Overlay | A `spectio.yml` attached in Spectio for a pipeline you do not own | [checking §12.7](specs/checking-scenarios.md#127-overlays) |
| Runner | The agent next to the engines that launches runs and observes the scheduler | [schedulers §3](specs/schedulers-and-monitoring.md#3-how-the-runner-observes) |
| Environment | Where runs execute: a machine or cluster with its runner | [UI §4.8](specs/ui-spec.md#48-environments) |
| Plugin kinds | Engine, launcher, resolver, sink, check provider, viewer, notifier, identity, AI, secrets | [architecture §2](specs/architecture-plugins-and-packaging.md#2-plugin-kinds) |
| Engine bridge | How an engine reports events: nf-spectio for Nextflow, a logger plugin for Snakemake | [architecture §13](specs/architecture-plugins-and-packaging.md#13-engine-bridges) |
| Board | A UI design source in `design/ui-canvas/*.dc.html`, rendered to PNG for review | [UI spec](specs/ui-spec.md) |
| Progress page | The page each pipeline step writes while it runs, figure first | [documentation §3.2](specs/documentation-system.md#32-progress-pages-docsprogresswavestepmd) |
| Version 0.0.1 | The first, basic local version: one user, engines on the same machine | [MVP 0.0.1](specs/mvp-0.0.1.md) |
