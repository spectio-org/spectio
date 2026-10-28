---
step: APPLY3
wave: W3
status: done
pr: null
review: approve
review_score: 12/14
review_ref: "journal 2026-10-28 12:55 UTC, tick 11 continued (APPLY3)"
---
# APPLY3 · Apply the findings of the spikes round to the specs

!!! success "Done 2026-10-28 · 49 of 69 findings reached the specs: 44 applied (2 of them by PR #36), 5 partly applied, 0 not applied · 9 wait for Thomas · 7 specs and decision 0001 changed · no inbox entry added · doc review approve 12/14, changes applied"

![APPLY3 figure: the 69 findings of the spikes round as cells, grouped by step T2, T3, T4 and T7: 42 applied by APPLY3, 2 by PR #36, 5 partly applied, 9 waiting for Thomas, 3 applied by T3 and 8 rejected; the lines added and removed in each of the 7 specs and decision 0001, to scale; the work left outside the specs; the inbox entries #53, #54, #55, #59 and #46 that hold 10 findings; and the 5 assumed answers already applied](../../assets/diagrams/apply3_specs_light.png#only-light)
![APPLY3 figure: the 69 findings of the spikes round as cells, grouped by step T2, T3, T4 and T7: 42 applied by APPLY3, 2 by PR #36, 5 partly applied, 9 waiting for Thomas, 3 applied by T3 and 8 rejected; the lines added and removed in each of the 7 specs and decision 0001, to scale; the work left outside the specs; the inbox entries #53, #54, #55, #59 and #46 that hold 10 findings; and the 5 assumed answers already applied](../../assets/diagrams/apply3_specs_dark.png#only-dark)

*Left: one cell per finding; a dot marks a fix applied on an assumed inbox answer. Middle: what changed in the specs, to scale, then the work that a partly applied finding still needs outside the specs. Right: what waits for Thomas (one bar unit per finding; #53 also holds the Role part of SPK-T4-02), and the assumed answers that are already in the text.*

## What changed

- **Findings applied to the owning specs.** APPLY3 took every finding that [TRIAGE3](TRIAGE3.md) accepted (44) or assumed (4: SPK-T2-09, SPK-T3-18, SPK-T4-09, SPK-T7-01) in the [spikes round](../../reviews/spikes.md), plus the fact part of SPK-T4-02 that inbox #53 allows now. The authoritative list is the decision-log section [2026-10-28 — APPLY3](../../decisions/log.md#2026-10-28-apply3-spikes-round-findings-applied). It gives the specs changed by file and §, the assumed decisions by inbox number, and the follow-ups.
- **7 specs and one decision changed.** No new section number was needed, and nothing was renumbered:
    - [`schedulers-and-monitoring.md`](../../specs/schedulers-and-monitoring.md): §3.1 (Snakemake head job under `sbatch`), §3.2 (Snakemake's own status clock), §3.5 (failure classes and pending reasons: `FAILED 140` for a Nextflow time limit, `FAILED 1:0` for Snakemake, `OUT_OF_MEMORY` verified, engine cleanup is not an external cancel, `state_reason`, `FailedScheduling`, `WaitingForQuota`), §4 (`nf-k8s` on 25.10, "queued" from the Kueue visibility API, OOM and Job deadline, Kueue pod integration, `pods: create` verified);
    - [`dev-environment-and-testing.md`](../../specs/dev-environment-and-testing.md): §1 (checked downloads, Kueue row), §3 (`oom_real`, node failure, preemption planned), §4 (new rule "Node tools are read-only for jobs"), §4.1 (`slurm-versions` planned), §4.2 (`k8s-kueue`), §10.1 (SLURM exit codes), §11 (`pipelines-real.yml` pin, `pipelines-slurm.yml` and `pipelines-k8s.yml` standalone, "Nightly runs"), §15.1 and §15.3 (Snakemake head job);
    - [`api-and-data-model.md`](../../specs/api-and-data-model.md): §7 (`attempts.exit` nullable, `runs.failure` on Nextflow), §7.2 (Nextflow mapping from the trace record; new attempt state `aborted`), §8.2 (a repeated flow completion changes nothing), §10 (coexistence mark becomes a link);
    - [`synthesis.md`](../../specs/synthesis.md): §1 and §2 (`nf-tower` downloaded on first use; the 14 Snakemake `LogEvent` types), §2bis (Tower `begin` and `dag`; logger plugin pitfalls), §2ter (Snakemake attempts, checkpoints, `temp_removed`);
    - [`checking-scenarios.md`](../../specs/checking-scenarios.md): §11.1 (matching task outputs; `JOB_INFO` at v9.27.1), §11.4 (reuse after a resume), §11.5 (end of stage on Nextflow; stages after a failure);
    - [`architecture-plugins-and-packaging.md`](../../specs/architecture-plugins-and-packaging.md): §7.3 (`nf-spectio` unpacked into `$NXF_HOME/plugins`), §13.3 (the sender stops at observer shutdown), §13.4 (logger plugin found on `PYTHONPATH`);
    - [`ui-spec.md`](../../specs/ui-spec.md) §3.1 (label "Aborted");
    - [decision 0001](../../decisions/0001-nextflow-through-nf-spectio.md): a dated "Update 2026-10-28" line. The decision stays as decided.
- **Status lines in [`spikes.md`](../../reviews/spikes.md).** Each of the 49 findings now ends its **Status** line with `→ applied (APPLY3, 2026-10-28): <spec> §<n>`, `→ partly applied (APPLY3, 2026-10-28): … pending: …`, or `→ applied by PR #36 (corpus retry, 2026-10-28): dev-env §10.2`. The header gets an APPLY3 count. The rejected findings, the reserved inbox findings and the 3 findings T3 applied keep their TRIAGE3 status.
- **One decision-log section** for the whole step: [2026-10-28 — APPLY3](../../decisions/log.md#2026-10-28-apply3-spikes-round-findings-applied).

**Before and after.** Each row was read in `git diff 90180cb HEAD -- docs/specs docs/decisions` and matches a bullet of the [decision-log section](../../decisions/log.md#2026-10-28-apply3-spikes-round-findings-applied):

| Findings | Before | After | Owner now |
|---|---|---|---|
| SPK-T3-09 | a task over its time limit on SLURM ends `TIMEOUT` | a Nextflow task also ends `FAILED` with exit 140 (`--signal B:USR2@30`), classed `timeout` | [schedulers §3.5](../../specs/schedulers-and-monitoring.md) |
| SPK-T3-03, -02 | SLURM OOM kill gives `OUT_OF_MEMORY` 0:125 **[to be validated on sind]** | verified on sind, Slurm 26.05.5: signal 125, status `SIGNALED`; only `oom_real` triggers it | schedulers §3.5, [dev-env §3](../../specs/dev-environment-and-testing.md) |
| SPK-T3-05, -16 | not covered | Nextflow's own cleanup of pending jobs (`CANCELLED by <uid>`, the run's uid) is not an external cancel; `sacct --json` names the canceller in `kill_request_user` | schedulers §3.5 |
| SPK-T3-01, SPK-T2-17 | `attempts.exit` listed with no null case | a Snakemake task job on SLURM ends `FAILED 1:0`; `attempts.exit` is nullable | schedulers §3.5, [api §7](../../specs/api-and-data-model.md) |
| SPK-T2-09 | attempt states without `aborted` | terminal state `aborted` for attempts still open when a launch ends; not a failure *(assumed, #56)* | api §7.2, [ui-spec §3.1](../../specs/ui-spec.md) |
| SPK-T2-07 | Nextflow trace statuses map to attempt states **[to be validated]** | the mapping reads the hooks and `trace.status`, never `handler.status` | api §7.2 |
| SPK-T2-06 | not covered | a repeated flow completion for the same launch is logged and changes nothing | api §8.2 |
| SPK-T2-01, -02 | end of stage on Nextflow = every matching process fired `onProcessTerminate` | that, **and** every seen task of those processes completed or cached; unended stages close when the run ends | [checking-scenarios §11.5](../../specs/checking-scenarios.md) |
| SPK-T2-05 | not covered | the `nf-spectio` sender stops at observer shutdown, not at `onFlowComplete` | [architecture §13.3](../../specs/architecture-plugins-and-packaging.md) |
| SPK-T2-25, -26 | how `nf-spectio` reaches Nextflow **[to be validated]**; Snakemake plugin discovery open | unpacked into `$NXF_HOME/plugins`; the Snakemake logger plugin found on `PYTHONPATH`, no install | architecture §7.3, §13.4 |
| SPK-T2-12 | `nf-tower` "ships with Nextflow" | a core plugin, downloaded from the plugin registry on first use | [synthesis §1, §2](../../specs/synthesis.md) |
| SPK-T4-17 | Kueue pod integration "opt-in" **[to be validated]** | listed in Kueue's default configuration (v0.20.3) | schedulers §4 |
| SPK-T4-05 | not covered | Nextflow 25.10 needs the `nf-k8s` plugin for the `k8s` executor | schedulers §4 |
| SPK-T4-02 (fact part) | `pods: create` **[to be validated]** | verified on `k8s-mini`; the Role lists wait for inbox #53 | schedulers §4 |
| SPK-T3-19 | Snakemake head under `sbatch` or on a service node **[to be validated]** | works on `slurm-site` for `happy`; failures and long runs **[to be validated]** | schedulers §3.1, dev-env §15.1, §15.3 |
| SPK-T3-20 | no rule | "Node tools are read-only for jobs" (not built yet) | dev-env §4 |
| SPK-T4-09, SPK-T7-01 | pipeline workflows "Standalone: `ci.yml` does not call it"; nobody reads the nightly runs | standalone until `ci.yml` calls them *(assumed, #57)*; the autopilot reads the nightly runs *(assumed, #58)* | dev-env §11 |

## Why

A finding is only useful once the spec that owns its topic says what was measured. TRIAGE3 decided which findings may proceed; APPLY3 writes them into the specs, with the rules of the `apply-findings` skill:

- change the spec that owns the topic and link to it from elsewhere ("one owner per topic", `CLAUDE.md`);
- keep section numbers stable;
- mark every assumed fix with *(assumed — pending Thomas, inbox #n)*, so that one search finds what to revert;
- leave untouched the sections that an open inbox entry blocks (here: the Kubernetes Roles, task-pod tokens, the content of engine events, the slurmrestd token).

The spikes round is the first one built on measurements, not on reading. Its fixes replace **[to be validated]** marks with links to fixtures and CI runs: the T2, T3 and T4 notes in `docs/research/`.

Step definition: `APPLY3` in `docs/playbooks/pipeline.yaml` (wave W3, `kind: apply`, `depends_on: [TRIAGE3]`, rounds `[spikes]`).

## Evidence

**What APPLY3 changed, and what it did not.** The APPLY3 branch merged `autopilot/integration` at `90180cb` (T3, PR #35, and the corpus retry, PR #36). So the step's own spec diff is the branch against `90180cb`, and the T3 rows of dev-env §4.1 and §11 and the corpus text of §10.2 are not in it:

```console
$ git diff --numstat 90180cb HEAD -- docs/specs docs/decisions/0001-nextflow-through-nf-spectio.md
3	1	docs/decisions/0001-nextflow-through-nf-spectio.md
13	7	docs/specs/api-and-data-model.md
3	3	docs/specs/architecture-plugins-and-packaging.md
7	3	docs/specs/checking-scenarios.md
25	13	docs/specs/dev-environment-and-testing.md
22	11	docs/specs/schedulers-and-monitoring.md
13	9	docs/specs/synthesis.md
1	1	docs/specs/ui-spec.md
```

Most changed lines are long paragraphs or table rows, so the line counts are small.

**Each Status line was checked against the diff,** not only against the apply notes: one search per finding in the added lines of `git diff -U0 90180cb HEAD`, and the § taken from the last heading above each hunk. For example:

```console
$ git diff -U0 90180cb HEAD -- docs/specs | grep "^+" | grep -c "handler.status"     # SPK-T2-07, api §7.2
1
$ grep -n "Node tools are read-only" docs/specs/dev-environment-and-testing.md       # SPK-T3-20, dev-env §4
167:**Node tools are read-only for jobs.** Tools that cluster nodes execute come from a location the cluster's job user cannot write, …
$ grep -rno "pending Thomas, inbox #\(56\|57\|58\|60\)" docs/specs | sort | uniq -c
      1 docs/specs/api-and-data-model.md:382:pending Thomas, inbox #56
      1 docs/specs/dev-environment-and-testing.md:180:pending Thomas, inbox #60
      1 docs/specs/dev-environment-and-testing.md:490:pending Thomas, inbox #57
      1 docs/specs/dev-environment-and-testing.md:491:pending Thomas, inbox #57
      1 docs/specs/dev-environment-and-testing.md:505:pending Thomas, inbox #58
      1 docs/specs/ui-spec.md:58:pending Thomas, inbox #56
```

Every accepted or assumed finding had a matching change. None was left out.

**Status lines, read back from the review file:**

```console
$ grep -c "Status:" docs/reviews/spikes.md
69
$ grep -c "→ applied (APPLY3" docs/reviews/spikes.md; grep -c "→ partly applied (APPLY3" docs/reviews/spikes.md; grep -c "→ applied by PR #36" docs/reviews/spikes.md
42
5
2
```

| Step | Findings | Applied | Partly applied | Not applied | Waiting for Thomas | Applied by T3 | Rejected |
|---|---:|---:|---:|---:|---:|---:|---:|
| T2 | 27 | 23 | 0 | 0 | 2 | 0 | 2 |
| T3 | 20 | 12 | 1 | 0 | 1 | 3 | 3 |
| T4 | 17 | 6 | 3 | 0 | 5 | 0 | 3 |
| T7 | 5 | 3 (2 by PR #36) | 1 | 0 | 1 | 0 | 0 |
| **Total** | **69** | **44** | **5** | **0** | **9** | **3** | **8** |

"Partly" means that the spec text is done and something outside the specs remains:

| Finding | In the spec | Still to do |
|---|---|---|
| SPK-T4-02 | schedulers §4: `pods: create` verified on `k8s-mini` | the Role lists, after [inbox #53](../../reviews/inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads) |
| SPK-T4-15 (SEC-T4-05) | dev-env §1, "Checked downloads" | the code: manifest images by digest, `nf-k8s` with a sha256, `bootstrap.sh --only` (with inbox #46) |
| SPK-T3-20 (SEC-T3-01) | dev-env §4, "Node tools are read-only for jobs" | the code in `dev/slurm/` and `dev/k8s/` |
| SPK-T4-09 | dev-env §11, both rows "standalone until `ci.yml` calls it" *(assumed, #57)* | `ci.yml` calls `pipelines-slurm.yml` and `pipelines-k8s.yml` |
| SPK-T7-01 | dev-env §11, "Nightly runs" *(assumed, #58)* | the autopilot playbook and skill read the scheduled runs |

SPK-T7-03 counts as applied: its proposal was the §11 text, and its code part, `pipelines-real.yml` reading `NEXTFLOW_VERSION` from `dev/versions.env`, landed in PR #38 (merged into this branch at `3bafe3e`).

**Exit criterion.** The docs gate and the strict build:

```console
$ python3 tools/docs/check.py
...
diagrams: 21 scripts re-run, 42 SVGs compared
media: 106 outputs in the manifest
progress: 34 pages checked
docs gate: 0 failure(s)
$ uvx --with mkdocs-material mkdocs build --strict
INFO    -  Documentation built in 5.91 seconds
```

## Figures and media

- **Step figure** at the top of this page (to scale: one cell per finding, bar lengths in lines and in findings). Script: `tools/diagrams/apply3_specs.py`; outputs `docs/assets/diagrams/apply3_specs_{light,dark}.{svg,png}`; manifest entry `apply3-specs` in `docs/assets/media.yaml`.
- The figure is a map of line changes per spec, not a before-and-after drawing of a mechanism. Two changes are mechanisms: the new attempt state `aborted` (api §7.2) and the Nextflow end-of-stage rule (checking-scenarios §11.5). Their before and after are in the table under [What changed](#what-changed); the other changes are local facts (exit codes, event order, plugin loading), each linked to the T2, T3 or T4 note that measured it.

## Findings and open questions

**No new inbox entry.** What waits for Thomas is already in the [TRIAGE3 block of the inbox](../../reviews/inbox.md#triage3-2026-10-28):

- [#53](../../reviews/inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads) Kubernetes Roles: SPK-T4-01, -03, -04 and the Role part of -02;
- [#54](../../reviews/inbox.md#54-kubernetes-work-namespace-task-pod-tokens-and-a-shared-namespace) task-pod tokens and a shared work namespace: SPK-T4-12, -14;
- [#55](../../reviews/inbox.md#55-what-engine-events-may-carry-task-script-and-env-user-host-and-command-line) what engine events may carry: SPK-T2-11, -23;
- [#59](../../reviews/inbox.md#59-slurmrestd-which-token-the-runner-holds-and-which-user-it-names) slurmrestd token and user: SPK-T3-15;
- #46 (existing) corpus pins: SPK-T7-04.

**Applied on an assumed answer, to revert if Thomas answers otherwise:** #56 (attempt state `aborted`), #57 (pipeline workflows standalone until `ci.yml` calls them), #58 (the autopilot reads the nightly runs), #60 (`slurm-versions` planned, built by the first step that needs it), and #32 for the reuse of check results after a resume (SPK-T2-08).

**Left as they are:** the T3 measurements still marked **[to be validated]** in schedulers §3.1 (Snakemake head on failure scenarios, a cancelled head, long runs), and whether `NXF_PLUGINS_DIR` can point to a read-only copy (architecture §7.3).
