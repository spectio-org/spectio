---
step: TRIAGE3
wave: W3
status: running
pr: null
review: null
review_score: null
review_ref: null
---
# TRIAGE3 · Sort what the W3 spikes measured against the specs

!!! success "Triaged 2026-10-28 · 69 findings: 44 accepted, 8 rejected, 3 already applied by T3, 14 sent to the inbox (4 assumed, 9 reserved, 1 added to #46) · inbox #53–#60 · doc review pending"

![TRIAGE3 sorting figure: the 69 findings of the spikes round, one cell each, coloured by severity, grouped by step T2, T3, T4 and T7, then sorted into 44 accepted, 3 applied by the step, 4 assumed, 10 waiting for Thomas and 8 rejected](../../assets/diagrams/triage3_sort_light.png#only-light)
![TRIAGE3 sorting figure: the 69 findings of the spikes round, one cell each, coloured by severity, grouped by step T2, T3, T4 and T7, then sorted into 44 accepted, 3 applied by the step, 4 assumed, 10 waiting for Thomas and 8 rejected](../../assets/diagrams/triage3_sort_dark.png#only-dark)

*One cell is one finding, the same size on both sides. Amber cells with a thick edge are majors, grey cells minors; this round has no blocker. Eight of the 14 majors wait for Thomas, because they touch Kubernetes roles, security posture or auth.*

## What changed

- **A new round file, [`spikes.md`](../../reviews/spikes.md).** The W3 steps [T2](T2.md), [T3](T3.md), [T4](T4.md) and [T7](T7.md) measured real engines and clusters. Each listed where the specs disagree with what it measured, without editing the specs. TRIAGE3 turned each difference into one finding, `SPK-<step>-nn`, in the review format. A security finding keeps its original ID in brackets, for example SPK-T4-12 (SEC-T4-02).
- **One decision per finding.** Each `Status:` line holds one of five forms:
    - `accepted (auto: …)`, with the check that confirmed it and the section the fix is local to;
    - `rejected (…)`, with the reason;
    - `applied (T3, …)`, when T3 already made the change in the rows it built;
    - `inbox (assumed: …)`, the recommended option proceeds until Thomas answers;
    - `inbox (reserved: …)` or `inbox (existing #46 …)`, the question waits for Thomas.
- **Inbox, entries #53 to #60.** A new [TRIAGE3 block](../../reviews/inbox.md#triage3-2026-10-28) holds eight entries. [#46](../../reviews/inbox.md#46-follow-up-pin-the-corpus-by-commit-and-replace-the-snakemake-composite-action) gets a dated update: it now also covers the code part of SPK-T4-15 (Kueue image by digest, `nf-k8s` with a sha256, `bootstrap.sh --only` in `pipelines-k8s.yml`).
- **Two re-check scripts** in `tools/triage/`:
    - `check_t2.py` reads the T2 fixtures from `origin/spike/engine-events` with `git show`, so nothing is checked out;
    - `check_t3.py` reads the SLURM fixtures of `tests/fixtures/slurm/slurm-26.05.5/`.
- **No spec was edited.** Accepted and assumed findings reach the specs in APPLY3.
- **Commit** `efb00cf` on `autopilot/integration`: `autopilot(TRIAGE3): triage the spikes round, 69 findings`. Files: `docs/reviews/spikes.md` (new, 824 lines), `docs/reviews/inbox.md` (+131), `tools/triage/check_t2.py` (147), `tools/triage/check_t3.py` (54).
- **This page and its figure** (`tools/diagrams/triage3_sort.py`, listed in `docs/assets/media.yaml`) were written after the commit.

## Why

Thomas should only see what needs him. The [triage policy](../../playbooks/triage-policy.md) says what the autopilot may decide alone:

- **accept** a confirmed, local, minor or major fix that reverses no logged decision and stays out of the reserved topics;
- **reject** what cannot be reproduced, duplicates a handled finding, or only asks for style changes;
- **send to the inbox** everything else, and **assume** the recommended option when it is reversible and only affects docs.

This round differs from [TRIAGE2](../W2/TRIAGE2.md) in two ways:

- **The evidence is measured, not read.** "Confirmed" (policy condition 1) means the orchestrator re-ran the check on the committed fixtures or job logs, not only re-read a quoted passage.
- **The reserved topics come up in a new form.** Kubernetes Roles, task-pod tokens, the shared work namespace and slurmrestd tokens are "roles, permission defaults, security posture defaults, auth modes". They go to Thomas even though none of them is in 0.0.1.

Step definition: `TRIAGE3` in `docs/playbooks/pipeline.yaml` (wave W3, `kind: triage`, depends on T2, T3, T4 and T7, round `spikes`). How triage fits into a tick: [`autopilot.md`](../../playbooks/autopilot.md).

## Evidence

**How the evidence was checked.** The full list is in the header of [`spikes.md`](../../reviews/spikes.md). In short:

- **T2:** the fixtures on `origin/spike/engine-events`, re-read with `check_t2.py`. Every fact reproduced.
- **Snakemake line numbers:** re-read in the Snakemake 9.27.1 wheel and `snakemake-interface-logger-plugins` 2.1.0 that `dev/bootstrap.sh` installs.
- **T3:** `tests/fixtures/slurm/slurm-26.05.5/`, re-read with `check_t3.py`, and the job logs of run 40680736055 and spike runs 40667769713 and 40670286528.
- **T4:** `tests/fixtures/k8s/`, `tests/k8s/rbac.yaml`, and the logs of spike runs 40662141233 and 40663207755. Downloading the Kueue v0.20.3 manifest and matching its sha256 found one wrong claim in the T4 note (SPK-T4-17, accepted).
- **T7:** the job logs of nightly run 40649538349.

**The T2 checks, re-run for this page.** Decisive lines (output cut at the line ends):

```console
$ python3 -I tools/triage/check_t2.py all
## after_terminate
nextflow-26.10.4_plugin_flaky task events after their process's onProcessTerminate: {('QC_STATS', 'onTaskComplete'): 1, ('ALIGN', 'onTaskComplete'): 1, ('MERGE', 'onTaskComplete'): 1, ('COMPARE', 'onTaskComplete'): 2}
## downstream_terminate
nextflow-26.10.4_plugin_toolerr created 8 terminated 7 never terminated: ['FINAL_REPORT']
nextflow-25.10.9_plugin_toolerr created 8 terminated 6 never terminated: ['COMPARE', 'FINAL_REPORT']
## failed_status
nextflow-25.10.9_plugin_toolerr COMPARE (treatB_vs_ctrl) handler.status= RUNNING trace.status= ABORTED exit= None errorAction= None
## pending_only
nextflow-26.10.4_plugin_toolerr tasks with onTaskPending and nothing after: 1
## tower_begin_and_tasks
nextflow-26.10.4_tower_flaky begin has dag: True | task keys include script, env: True
nextflow-25.10.9_tower_flaky begin has dag: False | task keys include script, env: True
## smk
job_error keys: ['aux', 'conda_env', 'container_img', 'indent', 'input', 'jobid', 'log', 'output', 'rule_msg', 'rule_name', 'shellcmd'] | has exit code key: False
workflow_started identity keys: ['cmd', 'cwd', 'host', 'platform', 'rundir', 'user']
```

These lines back SPK-T2-01 and -02 (accepted), SPK-T2-09 (assumed, #56), SPK-T2-11 and -23 (reserved, #55) and SPK-T2-17 (accepted).

**The T3 checks, re-run for this page.** T3 is not merged into this worktree yet, so the fixtures were extracted from branch `autopilot/T3` into a scratch folder (`git archive autopilot/T3 tests/fixtures/slurm | tar -x`):

```console
$ python3 -I tools/triage/check_t3.py <scratch>/tests/fixtures/slurm/slurm-26.05.5 probes pending
# probes
   328 probe-oom OUT_OF_MEMORY None None:125 SIGNALED kill_request_user='' elapsed=1 limit_min=60
   341 probe-nodefail NODE_FAIL None 1:0 ERROR kill_request_user='' elapsed=73 limit_min=60
non-empty kill_request_user: 5 of 11
# pending
   339 probe-maint PENDING state_reason='ReqNodeNotAvail' state_description='ReqNodeNotAvail, Reserved for maintenance'
```

These lines back SPK-T3-03, -06 and -16 (accepted), and the rejection of SPK-T3-08 (`NODE_FAIL` with exit 1 already matches schedulers §3.5).

**Counts, read back from the round file.**

```console
$ cd docs/reviews
$ for s in accepted rejected applied inbox "inbox (assumed" "inbox (reserved" "inbox (existing" open; do printf "%-17s %3s\n" "$s" "$(grep -c "Status:\*\* $s" spikes.md)"; done; grep -c "^### SPK-" spikes.md
accepted           44
rejected            8
applied             3
inbox              14
inbox (assumed      4
inbox (reserved     9
inbox (existing     1
open                0
69
```

The same counts per step, from the [Counts table](../../reviews/spikes.md#counts) of the round file:

| Step | Findings | Accepted | Rejected | Applied by the step | Inbox | of which assumed | of which reserved |
|---|---:|---:|---:|---:|---:|---:|---:|
| [T2](T2.md) | 27 | 22 | 2 | 0 | 3 | 1 (#56) | 2 (#55) |
| [T3](T3.md) | 20 | 12 | 3 | 3 | 2 | 1 (#60) | 1 (#59) |
| [T4](T4.md) | 17 | 7 | 3 | 0 | 7 | 1 (#57) | 6 (#53, #54) |
| [T7](T7.md) | 5 | 3 | 0 | 0 | 2 | 1 (#58) | 0 (1 already in #46) |
| **Total** | **69** | **44** | **8** | **3** | **14** | **4** | **9** |

**Severity against decision.** This table joins each finding's heading with its status line (a short Python script over `spikes.md`):

| Severity | Accepted | Applied by the step | Inbox, assumed | Inbox, waiting | Rejected | Total |
|---|---:|---:|---:|---:|---:|---:|
| major | 5 | 0 | 1 | 8 | 0 | 14 |
| minor | 39 | 3 | 3 | 2 | 8 | 55 |
| **Total** | **44** | **3** | **4** | **10** | **8** | **69** |

- **Majors accepted (5):** SPK-T2-01 (end of stage on Nextflow), SPK-T2-07 (attempt state from the trace record), SPK-T3-05 (Nextflow's own cleanup reads as a cancel), SPK-T3-09 (a task over its time ends `FAILED 140:0`), SPK-T4-05 (Nextflow 25.10 needs `nf-k8s`).
- **Major assumed (1):** SPK-T2-09, tasks left open when the run ends (#56).
- **Majors waiting (8):** SPK-T4-01, -02, -03 (#53); SPK-T4-12, -14 (#54); SPK-T2-11, -23 (#55); SPK-T3-15 (#59).
- **Minors waiting (2):** SPK-T4-04 (#53) and SPK-T7-04 (existing #46).

**The 8 rejections,** with the reason from each status line:

| Finding | Reason |
|---|---|
| SPK-T2-13 | cannot be reproduced from the evidence: not observed |
| SPK-T2-20 | no difference: the observation matches synthesis §2ter |
| SPK-T3-07 | cannot be reproduced: one spike run, not retested; no spec text affected |
| SPK-T3-08 | no difference: the observation matches schedulers §3.5 |
| SPK-T3-14 | no difference with schedulers §3.3; already recorded in the dev-env §4.1 `slurm-rest` row |
| SPK-T4-08 | no spec contradicted: a test-harness fix already applied in `9f516a4` |
| SPK-T4-10 | duplicates a change already applied by T4 in dev-env §4.2 (PR #33) |
| SPK-T4-13 | duplicates the update already recorded in inbox #51 |

SPK-T4-10 was triaged before the "applied by the step" column existed, so it stays "rejected (already applied)". The three T3 equivalents, SPK-T3-11 to -13, are counted as "applied".

**Exit criterion.** TRIAGE3 has no `exit_check` in `pipeline.yaml`, and wave W3 has none either. The step's own outputs are complete: no finding is left `open` (last count above), and `inbox.md` holds entries #53 to #60 and the #46 update.

## Figures and media

- **Sorting figure** at the top of this page (to scale, one cell per finding), as `documentation-system.md` §3.1 asks for a `triage` step. Script: `tools/diagrams/triage3_sort.py`; outputs `docs/assets/diagrams/triage3_sort_{light,dark}.{svg,png}`. Its data is copied from the status lines of `spikes.md`, and it asserts 69 findings.

## Findings and open questions

**Inbox entries from this step.** In short (the full wording is in the [inbox](../../reviews/inbox.md#triage3-2026-10-28)):

| # | Topic | Findings | Assumed already | Blocks |
|---|---|---|---|---|
| [53](../../reviews/inbox.md#53-kubernetes-roles-for-the-runner-and-the-nextflow-heads) | Kubernetes Roles for the runner and the Nextflow heads | SPK-T4-01 to -04 | none (reserved) | schedulers §4 RBAC text; nothing in 0.0.1 |
| [54](../../reviews/inbox.md#54-kubernetes-work-namespace-task-pod-tokens-and-a-shared-namespace) | task-pod tokens and a shared work namespace | SPK-T4-12, -14 | none (reserved) | architecture §7.5, schedulers §4; nothing in 0.0.1 |
| [55](../../reviews/inbox.md#55-what-engine-events-may-carry-task-script-and-env-user-host-and-command-line) | what engine events may carry: `script`, `env`, user, host | SPK-T2-11, -23 | none (reserved) | architecture §13.5 wording; api §14 payload rules |
| [56](../../reviews/inbox.md#56-assumed-the-state-of-a-task-still-open-when-the-run-ends) | state of a task still open when the run ends | SPK-T2-09 | (a): a terminal attempt state `aborted` | nothing |
| [57](../../reviews/inbox.md#57-assumed-pipelines-k8syml-and-pipelines-slurmyml-join-ciyml-as-inbox-26-decided) | `pipelines-k8s.yml` and `pipelines-slurm.yml` join `ci.yml` | SPK-T4-09, part of SPK-T3-13 | (a): keep the #26 rule | nothing |
| [58](../../reviews/inbox.md#58-assumed-who-watches-the-nightly-runs) | who watches the nightly runs | SPK-T7-01 | (b): the autopilot reads the last scheduled run | nothing |
| [59](../../reviews/inbox.md#59-slurmrestd-which-token-the-runner-holds-and-which-user-it-names) | slurmrestd: which token the runner holds | SPK-T3-15 | none (reserved) | schedulers §3.3 slurmrestd row; nothing in 0.0.1 |
| [60](../../reviews/inbox.md#60-assumed-who-builds-the-deferred-slurm-coverage) | who builds the deferred SLURM coverage | SPK-T3-18 | (a): mark the rows "planned" now | nothing |

- **#55 is the one that reaches 0.0.1.** In 0.0.1 engine events land in SQLite on a shared login node. Until Thomas answers, the api §14 payload rules stay as they are.
- **#53 has a fact part that can go in now.** The entry says that dropping "[to be validated on k8s-mini]" for `pods: create` (SPK-T4-02) can be applied now; the Role text waits.
- **#58 and #60 are only half assumed.** The spec side proceeds. The autopilot skill text (`.claude/`) and the step prompts in `pipeline.yaml` are Thomas's to change, so those parts wait.
- **schedulers §3.5 gets six T3 fixes** (SPK-T3-01, -03, -05, -06, -09, -16). They should be applied in one pass, since -05 and -16 change the same row.

**Next.** APPLY3 applies the 44 accepted and 4 assumed findings. The accepted fixes land in checking-scenarios, synthesis, api-and-data-model, architecture-plugins-and-packaging, schedulers-and-monitoring and dev-environment-and-testing, plus a dated update line in decision 0001 ([where they land](../../reviews/spikes.md#counts)). APPLY3 leaves untouched the sections named on the "Blocked" lines of #53, #54, #55 and #59.
