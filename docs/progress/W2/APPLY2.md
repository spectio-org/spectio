---
step: APPLY2
wave: W2
status: done
pr: null
review: approve
review_score: 12/14
review_ref: ".autopilot/journal.md, tick 6"
---
# APPLY2 · Apply the findings of the journeys and API contract rounds to the specs

!!! success "Done 2026-10-27 · 54 findings reached the specs: 7 applied, 47 partly applied, 0 not applied · 7 untouched, waiting for Thomas · 10 specs changed · no inbox entry added"

![APPLY2 figure: the 61 findings of R3 and R6 as cells, 7 applied, 47 partly applied and 7 untouched; the lines added and removed in each of the 10 specs, to scale; the parts left untouched because an inbox entry blocks them; and the parts deferred to UI boards and tools](../../assets/diagrams/apply2_specs_light.png#only-light)
![APPLY2 figure: the 61 findings of R3 and R6 as cells, 7 applied, 47 partly applied and 7 untouched; the lines added and removed in each of the 10 specs, to scale; the parts left untouched because an inbox entry blocks them; and the parts deferred to UI boards and tools](../../assets/diagrams/apply2_specs_dark.png#only-dark)

*Left: one cell per finding; a dot marks a fix that is assumed until Thomas answers its inbox entry. Middle: what changed in the specs, to scale, then what an inbox entry still blocks. Right: what is left for the boards and the tools, one bar unit per finding. Most findings are "partly" applied because their board is not redrawn yet.*

## What changed

- **Findings applied to the owning specs.** APPLY2 took every finding that [TRIAGE2](TRIAGE2.md) accepted (21) or assumed (33) in [R3](../../reviews/R3-journeys.md) (journeys) and [R6](../../reviews/R6-contract.md) (0.0.1 API contract). The authoritative list is the decision-log section [2026-10-27 — APPLY2](../../decisions/log.md#2026-10-27-apply2-review-findings-applied-r3-r6). It gives the specs changed by file and §, the overlaps applied once, the assumed decisions by inbox number, and the deferred work.
- **10 specs changed.** New sections got new numbers, and nothing was renumbered:
    - [`api-and-data-model.md`](../../specs/api-and-data-model.md): new [§4.1 Wire conventions](../../specs/api-and-data-model.md#41-wire-conventions), [§5.1 Run actions](../../specs/api-and-data-model.md#51-run-actions), [§5.2 Launch body](../../specs/api-and-data-model.md#52-launch-body), [§7.2 Task and attempt states](../../specs/api-and-data-model.md#72-task-and-attempt-states) and [§8.5 Stream frames](../../specs/api-and-data-model.md#85-stream-frames); edits in §4, §5, §7, §7.1, §8, §8.1 and §8.2;
    - [`ui-spec.md`](../../specs/ui-spec.md): §2, §3.1, §3.2, §4.3–§4.6, §8 and §11;
    - [`architecture-plugins-and-packaging.md`](../../specs/architecture-plugins-and-packaging.md): new [§13.7 Log sources per engine](../../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine); edits in §7.1, §7.2 and §13.1;
    - [`schedulers-and-monitoring.md`](../../specs/schedulers-and-monitoring.md): new [§3.1.1 Local launcher: detach, adopt, exit](../../specs/schedulers-and-monitoring.md#311-local-launcher-detach-adopt-exit); edit in §3.5;
    - [`synthesis.md`](../../specs/synthesis.md): §5ter, and a dated "superseded" note in §2ter that points to api §7.2 for the task states;
    - [`checking-scenarios.md`](../../specs/checking-scenarios.md) §4, §12.3, §12.4; [`cli-and-shared-libraries.md`](../../specs/cli-and-shared-libraries.md) §2; [`admin-and-operations.md`](../../specs/admin-and-operations.md) §3.1;
    - [`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md) §1 and §2, and the gate row of [`dev-environment-and-testing.md` §15.1](../../specs/dev-environment-and-testing.md) (wording only: the 0.0.1 gate verbs are `approve` and `stop`, no feature added).
- **Status lines in two review files.** Every applied finding's **Status** line now says what was applied, where, and what is pending: `applied` or `partly applied`, dated `(APPLY2, 2026-10-27)`. Each file's header gets an APPLY2 count. The seven findings that wait for Thomas keep their TRIAGE2 status.
- **One decision-log section** for the whole step: [2026-10-27 — APPLY2](../../decisions/log.md#2026-10-27-apply2-review-findings-applied-r3-r6).
- **Commit** `cf5357b` on `autopilot/integration`: `autopilot(APPLY2): apply R3 and R6 findings (7 applied, 47 partly, 33 assumed)` (the specs, the two review files, the decision log, this page and the figure with its script).

## Why

A finding is only useful once the spec that owns its topic says the right thing. TRIAGE2 decided which findings may proceed; APPLY2 writes them into the specs, following the [`apply-findings` skill](../../playbooks/autopilot.md):

- change the spec that owns the topic and link to it from elsewhere ("one owner per topic", `CLAUDE.md`);
- keep section numbers stable and add new numbers rather than renumbering;
- mark every assumed fix in the text with *(assumed — pending Thomas, inbox #n)*, so that one search finds what to revert if Thomas answers otherwise;
- leave untouched the sections that an open inbox entry blocks.

Most of R3 and R6 is about the 0.0.1 journey: launch, monitor, gate, relaunch. Writing the API contract now (wire conventions, run actions, launch body, task states, stream frames) is what lets P1 plan 0.0.1 against one contract instead of three partial ones.

Step definition: `APPLY2` in `docs/playbooks/pipeline.yaml` (wave W2, `kind: apply`, `depends_on: [TRIAGE2]`, rounds R3 and R6; wave exit check `python3 tools/docs/check.py`).

## Before and after

**Per finding.** The **Status** line of each finding in [R3](../../reviews/R3-journeys.md) and [R6](../../reviews/R6-contract.md) is the record: it names the spec and § that changed and what is still pending. For example:

```console
$ grep -A20 "^### SR-065" docs/reviews/R3-journeys.md | grep "Status:"
- **Status:** applied (APPLY2, 2026-10-27): api §5; synthesis §5ter.5; ui-spec §4.6 (assumed — pending Thomas, inbox #40)
```

**The mechanisms that changed.** Each row was read in `git diff cf5357b~1 cf5357b -- docs/specs`:

| Topic | Before | After | Owner now |
|---|---|---|---|
| Relaunch and Resume | `:resume` listed with no source state; no transition out of `failed` | `failed` is terminal; Resume and Relaunch create a child run with `parent_run_id`, and the parent stays terminal *(assumed, inbox #32)* | [api §5.1](../../specs/api-and-data-model.md#51-run-actions), §7.1 |
| 0.0.1 gate verbs | `approve`, `apply`, `go_back`, `stop` | `approve`, `stop`; Relaunch… at a gate is `stop` with reason `relaunched`, then `:relaunch` *(assumed, inbox #32)* | [`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md) §2, api §5.1 |
| Idempotency key replayed with a different body | `422` | `409 idempotency-key-reused` | [api §4.1](../../specs/api-and-data-model.md#41-wire-conventions) |
| Snakemake changed parameters | `--configfile` or `--config` | `--configfile` only, written to `<launch_dir>/.spectio/config.<n>.yaml` *(assumed, inbox #40)* | [`synthesis.md`](../../specs/synthesis.md) §5ter |
| Task and attempt states | upper case, in synthesis §2ter | lower case, one list | [api §7.2](../../specs/api-and-data-model.md#72-task-and-attempt-states) |
| Current stage of a run | `runs.stage_index` | `runs.current_stage_id`, a `run_stages.stage_id` *(assumed, inbox #40)* | api §7 |

![Before and after APPLY2: before, a failed run was resumed in place and a gate had four verbs; after, the failed parent stays terminal, Resume creates child run B that reuses its cache, and the 0.0.1 gate has approve and stop, with Relaunch… recorded as stop then a child run](../../assets/diagrams/apply2_relaunch_light.png#only-light)
![Before and after APPLY2: before, a failed run was resumed in place and a gate had four verbs; after, the failed parent stays terminal, Resume creates child run B that reuses its cache, and the 0.0.1 gate has approve and stop, with Relaunch… recorded as stop then a child run](../../assets/diagrams/apply2_relaunch_dark.png#only-dark)

*The relaunch model, the most visible change: the two R3 blockers SR-062 and CH-042.*

## Evidence

**How the step ran.** One dynamic workflow (run `wf_3dab872b-d5c`, 9 agents, 0 agent errors) ran in three phases on the integration branch: one agent per round mapped each finding to its edits; apply agents, each owning a disjoint group of files, made the edits; one last writer set the Status lines, wrote the decision-log section and ran the strict build. The orchestrator then checked the result by hand:

- the inbox labels in the decision-log section were compared with the titles in [`inbox.md`](../../reviews/inbox.md#triage2-2026-10-27); six labels did not match and were corrected (for example #40 is "fixes that are right but not local", not "engine bridges");
- the blocked sections were checked against the diff hunks: api §6 (lines 208–243) has no hunk, architecture §7.3 (from line 359) has none, and the `mvp-0.0.1.md` install line is unchanged;
- every new section got a new number (api §4.1, §5.1, §5.2, §7.2, §8.5; architecture §13.7; schedulers §3.1.1).

**Status lines, read back from the review files.** The columns are applied, partly applied, and still at a TRIAGE2 inbox status:

```console
$ cd docs/reviews
$ for f in R3-journeys R6-contract; do printf "%-13s" $f; for s in "applied (APPLY2" "partly applied" "inbox"; do printf " %4s" "$(grep -c "Status:\*\* $s" $f.md)"; done; echo; done
R3-journeys      7   15    5
R6-contract      0   32    2
```

| Round | Findings | Applied | Partly applied | Not applied | Untouched (waiting for Thomas) |
|---|---:|---:|---:|---:|---:|
| [R3](../../reviews/R3-journeys.md) | 27 | 7 | 15 | 0 | 5 |
| [R6](../../reviews/R6-contract.md) | 34 | 0 | 32 | 0 | 2 |
| **Total** | **61** | **7** | **47** | **0** | **7** |

"Partly" means that the spec text is done and a board, a spike, a tool or a blocked section remains. All of R6 is partly applied because each R6 finding also asks for a board change or for the openapi draft.

**Specs changed**, lines added and removed by the commit:

```console
$ git diff --numstat cf5357b~1 cf5357b -- docs/specs
3	1	docs/specs/admin-and-operations.md
151	49	docs/specs/api-and-data-model.md
18	0	docs/specs/architecture-plugins-and-packaging.md
6	2	docs/specs/checking-scenarios.md
4	4	docs/specs/cli-and-shared-libraries.md
1	1	docs/specs/dev-environment-and-testing.md
2	1	docs/specs/mvp-0.0.1.md
14	0	docs/specs/schedulers-and-monitoring.md
10	4	docs/specs/synthesis.md
44	25	docs/specs/ui-spec.md
```

**Assumed fixes.** 33 findings rest on an assumed inbox answer: #32 (10), #33 (1), #35 (2), #38 (3), #39 (7) and #40 (10). Their text carries 84 added or changed lines with an *(assumed — pending Thomas, inbox #n)* marker (`git diff cf5357b~1 cf5357b -- docs/specs | grep "^+" | grep -c "assumed — pending Thomas"`).

**Exit criterion.** The wave W2 check passes, and so does the strict build:

```console
$ python3 tools/docs/check.py
...
diagrams: 8 scripts re-run, 16 SVGs compared
media: 50 outputs in the manifest
progress: 22 pages checked
docs gate: 0 failure(s)
$ uvx --with mkdocs-material mkdocs build --strict
INFO    -  Documentation built in 5.80 seconds
```

## Figures and media

- **Step figure** at the top of this page (to scale: one cell per finding, bar lengths in lines and in findings). Script: `tools/diagrams/apply2_specs.py`; outputs `docs/assets/diagrams/apply2_specs_{light,dark}.{svg,png}`; manifest entry `apply2-specs` in `docs/assets/media.yaml`.
- **Relaunch figure** under "Before and after" (the run model before and after the step). Script: `tools/diagrams/apply2_relaunch.py`; outputs `docs/assets/diagrams/apply2_relaunch_{light,dark}.{svg,png}`; manifest entry `apply2-relaunch`.

## Findings and open questions

**No new inbox entry.** What remains is listed by kind in the [decision-log section](../../decisions/log.md#2026-10-27-apply2-review-findings-applied-r3-r6):

- **UI boards (15 boards).** RunDetail carries 17 findings; ReviewReport, Launch and RunsRows 5 each; RelaunchDialog and RunsTable 4. Two boards are new: RunTasks and RunLogs (log sources: architecture §13.7). No board step exists yet in `pipeline.yaml`.
- **Tools and spikes.** The openapi draft spike carries 8 R6 findings; spike T2 checks the engine-to-task-state mapping (SR-083); `spectio-sdk` JSON Schemas (SR-084); later api compare endpoints (UX-291).
- **Blocked by an open inbox entry** (sections not edited): [#36](../../reviews/inbox.md#36-the-ingest-contract-for-001-split-inbox-11) ingest contract (5 findings), [#34](../../reviews/inbox.md#34-001-scope-how-nf-corernaseq-gets-its-stages-and-gate-workflow-registration-multiqc-in-the-install) rnaseq stages and the gates file (4), #16 pause and stop (4), [#37](../../reviews/inbox.md#37-browser-protection-for-the-token-less-loopback-api), #13, #19, #20 and #25 (1 each).
- **Waiting for Thomas, untouched:** SR-054, SR-056, SR-057, SR-058, SR-067 (R3) and SR-080, SR-091 (R6).
- **One stale reference left on purpose:** `ui-spec.md` §4.11 (phone Run detail) still names "Pause after stage". Phones are not in 0.0.1, and UX-289 does not cover that section.

**Next.** APPLY2 is the last step of wave W2. Wave W3 (development layer and test infrastructure) starts with build steps in worktrees, the first that write code; each goes through `review-code` before its docs.
