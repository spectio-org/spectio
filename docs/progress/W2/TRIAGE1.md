---
step: TRIAGE1
wave: W2
status: done
pr: null
review: approve
---
# TRIAGE1 · Sort the findings of ten review rounds

!!! success "Done 2026-10-27 · 320 findings: 163 accepted, 4 rejected, 153 sent to the inbox (88 assumed, 65 waiting for Thomas) · inbox #11–#30, plus #31 (budget stop)"

## What changed

- **Status lines in ten review files.** Every finding's `Status: open` now holds a triage decision, dated `(TRIAGE1, 2026-10-27)`:
    - `accepted`;
    - `rejected`, with the reason;
    - `inbox`, the question waits for Thomas;
    - `inbox, assumed: <option> — pending Thomas`, the recommended option proceeds until Thomas answers.

    Each file's header also gets a one-line round summary ("triaged … N accepted, N rejected, N inbox (N assumed)"). The files are [R1](../../reviews/R1-consistency.md), [R2](../../reviews/R2-open-validations.md), [R4](../../reviews/R4-constraints.md), [R5](../../reviews/R5-security.md), [R7](../../reviews/R7-ui.md), [R8](../../reviews/R8-depictio.md), [R8b](../../reviews/R8b-depictio-tooling.md), [R9](../../reviews/R9-landscape.md), [R11](../../reviews/R11-docs.md) and [R12](../../reviews/R12-ui-scenarios.md).
- **Inbox, entries #11 to #30.** A new [TRIAGE1 block](../../reviews/inbox.md#triage1-2026-10-27) groups the 153 inbox findings by decision. Each finding appears once, on a "Covers" line. Entries #1 to #10 are unchanged.
- **Inbox, entry #31.** The autopilot added [#31 · Autopilot budget](../../reviews/inbox.md#31-autopilot-budget-a-fresh-reading-before-apply1) after the triage, when it stopped before APPLY1. It is committed in `b266e5b`.
- **No spec was edited.** Accepted and assumed findings reach the specs in APPLY1.
- **Commits** on `autopilot/integration`:
    - `eb411ce`: statuses for R1, R2, R4 and R5 (4 files, written before a container restart);
    - `0238f25`: statuses for R7, R8, R8b, R9, R11 and R12, and inbox entries #11 to #30 (7 files).
    - `b266e5b`: inbox entry #31 (1 file).

## Why

Thomas should only see what needs him. The [triage policy](../../playbooks/triage-policy.md) says what the autopilot may decide alone:

- **accept** a confirmed, local, minor or major fix that reverses no logged decision and stays out of the reserved topics;
- **reject** what cannot be reproduced, duplicates a handled finding, or only asks for style changes;
- **send to the inbox** everything else, and **assume** the recommended option when it is reversible and only affects docs.

Step definition: `TRIAGE1` in `docs/playbooks/pipeline.yaml` (wave W2, `kind: triage`, writes `docs/reviews/*.md` and `docs/reviews/inbox.md`). [`next-phase.md`](../../playbooks/next-phase.md) has no separate prompt for triage steps. Decision: [decision log, 2026-10-26, autopilot](../../decisions/log.md#2026-10-26-autopilot-instead-of-step-by-step-prompts). How triage fits into a tick: [`autopilot.md`](../../playbooks/autopilot.md).

## Evidence

**How the step ran** (from the workflow summary in `/tmp/triage1-evidence.json`, an uncommitted workflow result, the commits and the journal):

| Item | Value |
|---|---|
| Workflow | "apply triage-policy.md to every finding of R1 R2 R4 R5 R7 R8 R8b R9 R11 R12, then consolidate inbox entries". 11 agents, all `done`, `missing: 0`. |
| Phase 1, Triage | one agent per round (10 agents). Each applied the [triage policy](../../playbooks/triage-policy.md) as written to every `### <ID>` finding of its file. |
| Phase 2, Inbox | one consolidator, the single writer of `inbox.md`. It grouped the 153 inbox items into #11 to #30. |
| "Confirmed" (policy condition 1) | Blockers and majors had already been re-checked by each round's merger: for R1 to R9, see `.autopilot/journal.md`, tick 1; for R11, see [Progress · R11](../W1/R11.md). The triage agents re-read the quoted passages of every minor, and of every R8b and R12 finding, because no W1 merger re-checked those two rounds. |
| Rounds | the nine rounds listed for TRIAGE1 in `pipeline.yaml` (R1 R2 R4 R5 R7 R8 R8b R9 R11), plus R12. See the last section. |
| Interruption | A container restart stopped the run after 4 rounds. `eb411ce` (05:45 UTC) saved their statuses. The same run was then resumed at 05:45 UTC: R1, R2, R4 and R5 came from the cache (`"cached": true`), and the other 6 rounds ran live. The consolidator finished at 06:09 UTC, and `0238f25` followed. |
| Live agents | R7 345 s, R8 254 s, R8b 444 s, R9 189 s, R11 189 s, R12 390 s, consolidator 325 s |
| Totals | 1,032,248 tokens and 171 tool calls (`totalTokens`, `totalToolCalls`) |
| Consolidator's checks | it built the site with `mkdocs build --strict` (no warnings), checked that all 156 new finding links resolve, and checked with a script that each inbox item sits on exactly one "Covers" line |

**Counts per round,** as the workflow returned them (`result.counts`):

| Round | Findings | Accepted | Rejected | Inbox | of which assumed | waiting for Thomas |
|---|---:|---:|---:|---:|---:|---:|
| [R1](../../reviews/R1-consistency.md) | 53 | 13 | 0 | 40 | 25 | 15 |
| [R2](../../reviews/R2-open-validations.md) | 37 | 33 | 0 | 4 | 2 | 2 |
| [R4](../../reviews/R4-constraints.md) | 40 | 21 | 0 | 19 | 16 | 3 |
| [R5](../../reviews/R5-security.md) | 30 | 4 | 0 | 26 | 6 | 20 |
| [R7](../../reviews/R7-ui.md) | 40 | 26 | 0 | 14 | 7 | 7 |
| [R8](../../reviews/R8-depictio.md) | 15 | 7 | 0 | 8 | 4 | 4 |
| [R8b](../../reviews/R8b-depictio-tooling.md) | 32 | 19 | 3 | 10 | 7 | 3 |
| [R9](../../reviews/R9-landscape.md) | 17 | 9 | 0 | 8 | 6 | 2 |
| [R11](../../reviews/R11-docs.md) | 27 | 22 | 0 | 5 | 5 | 0 |
| [R12](../../reviews/R12-ui-scenarios.md) | 29 | 9 | 1 | 19 | 10 | 9 |
| **Total** | **320** | **163** | **4** | **153** | **88** | **65** |

**The same counts, read back from the review files.** The columns are accepted, rejected, inbox (including assumed), assumed, and still open. `inbox` matches `inbox, assumed` too, so the third column includes the fourth:

```console
$ cd docs/reviews
$ for f in R1-consistency R2-open-validations R4-constraints R5-security R7-ui R8-depictio R8b-depictio-tooling R9-landscape R11-docs R12-ui-scenarios; do printf "%-21s" $f; for s in accepted rejected inbox "inbox, assumed" open; do printf " %4s" "$(grep -c "Status:\*\* $s" $f.md)"; done; echo; done
R1-consistency          13    0   40   25    0
R2-open-validations     33    0    4    2    0
R4-constraints          21    0   19   16    0
R5-security              4    0   26    6    0
R7-ui                   26    0   14    7    0
R8-depictio              7    0    8    4    0
R8b-depictio-tooling    19    3   10    7    0
R9-landscape             9    0    8    6    0
R11-docs                22    0    5    5    0
R12-ui-scenarios         9    1   19   10    0
$ for s in accepted rejected inbox "inbox, assumed"; do printf "%-15s" "$s"; cat R1-consistency.md R2-open-validations.md R4-constraints.md R5-security.md R7-ui.md R8-depictio.md R8b-depictio-tooling.md R9-landscape.md R11-docs.md R12-ui-scenarios.md | grep -c "Status:\*\* $s"; done
accepted       163
rejected       4
inbox          153
inbox, assumed 88
```

Every row matches the workflow's counts, and no finding is left `open`. A plain `grep -c "Status:"` gives 30 for R12 instead of 29, because it also matches the round summary line in R12's header.

**Severity against decision.** This table joins each finding's heading with its status line (a short Python script over the same ten files):

| Severity | Accepted | Rejected | Inbox, waiting | Inbox, assumed | Total |
|---|---:|---:|---:|---:|---:|
| blocker | 0 | 0 | 5 | 6 | 11 |
| major | 59 | 1 | 46 | 59 | 165 |
| minor | 104 | 3 | 14 | 23 | 144 |
| **Total** | **163** | **4** | **65** | **88** | **320** |

No blocker was accepted, because the policy accepts only minors and majors (fact corrections excepted). The 11 blockers:

- **waiting for Thomas (5):** SR-001, SR-002, SEC-101, SEC-102 and DL-101;
- **assumed (6):** SR-003, SR-004, SR-005, CH-001, DEP-T-001 and DEP-T-002. For DEP-T-002, only the docs part is assumed; the release-PR rule waits, see #26.

**The four rejections,** with the reasons recorded in the status lines:

- three in [R8b](../../reviews/R8b-depictio-tooling.md):
    - two are not reproducible, because the tailnet VM and `staging.yml` were dropped by the 2026-10-26 dev-previews decision;
    - one is already handled by inbox #9 (answered 2026-10-26);
- one in [R12](../../reviews/R12-ui-scenarios.md): not reproducible. Its Tower-payload items rely on the Tower route, which decision 0001 dropped; the rest is already defined in ui-spec §5.1 and §6.

**Exit criterion.** TRIAGE1 has no `exit_check` of its own in `pipeline.yaml`; the wave W2 check is `python3 tools/docs/check.py`. The step's own outputs are complete:

- no finding is left `open` (last column above);
- `inbox.md` holds entries #11 to #30;
- the two triage commits touch only the files listed under `writes`:

```console
$ git show --stat --format=%h eb411ce | tail -1
 4 files changed, 164 insertions(+), 164 deletions(-)
$ git show --stat --format=%h 0238f25 | tail -1
 7 files changed, 492 insertions(+), 166 deletions(-)
```

## Figures and media

None (triage step, `documentation-system.md` §3.1).

## Findings and open questions

**Inbox entries from this step.** In short (the full wording is in the [inbox](../../reviews/inbox.md#triage1-2026-10-27)):

| # | Topic | Blocks APPLY1 | Blocker-severity finding | Assumed already |
|---|---|---|---|---|
| [11](../../reviews/inbox.md#11-ingest-credential-for-observed-runs-and-are-observed-runs-in-01) | ingest credential for observed runs; are they in 0.1? | yes | SR-001 | none |
| [12](../../reviews/inbox.md#12-runner-server-transport-and-runner-credential-lifetime) | runner ↔ server transport, runner credential lifetime | yes | SR-002 | CH-032, CH-007 |
| [13](../../reviews/inbox.md#13-token-registry-authorisation-matrix-and-which-column-authorises-reads) | token registry, authorisation matrix | yes | — | SEC-112, UX-111 |
| [14](../../reviews/inbox.md#14-which-unix-identity-a-launch-runs-as-and-who-may-move-a-run-to-another-runner) | Unix identity of a launch, moving runs | yes | SEC-101 | SEC-103 |
| [15](../../reviews/inbox.md#15-single-mode-on-shared-login-nodes) | `single` mode on shared login nodes | yes | SEC-102 | none |
| [16](../../reviews/inbox.md#16-what-ships-in-01-mvp-cut) | what ships in 0.1 (MVP cut) | yes | none rated blocker; the consolidator lists it with the blockers because it holds the MVP cut and the P1 planning | none |
| [17](../../reviews/inbox.md#17-features-after-01-wes-trs-seqera-api-galaxy-batches-chaining) | features after 0.1 | yes | — | FC-044, FC-046 table, UX-210 |
| [18](../../reviews/inbox.md#18-who-can-read-a-project-visibility-values-and-share-links) | project visibility, share links | yes | — | SR-019 |
| [19](../../reviews/inbox.md#19-project-roles-and-who-may-decide-a-gate-people-and-agents) | project roles, who decides a gate | yes | — | none |
| [20](../../reviews/inbox.md#20-admin-rights-sign-in-administration-and-new-users) | admin rights, sign-in administration | yes | — | none |
| [21](../../reviews/inbox.md#21-how-spectio-trusts-depictio-identities) | trusting depictio identities | yes | — | none |
| [22](../../reviews/inbox.md#22-depictio-hand-off-credentials-and-storage) | depictio hand-off: credentials, storage | yes | DL-101 | DEP-T-014 (partly), DL-105, DL-115, DEP-T-017 |
| [23](../../reviews/inbox.md#23-co-hosting-with-depictio-and-browser-hardening) | co-hosting with depictio, browser hardening | yes | — | DL-103, SEC-126 |
| [24](../../reviews/inbox.md#24-backup-and-restore-under-live-runs) | backup and restore under live runs | yes | — | CH-021, CH-022, SR-050 |
| [25](../../reviews/inbox.md#25-trust-boundaries-plugins-outbound-calls-event-bridges-runner-policy-restricted-data) | trust boundaries | yes | — | SEC-105, SEC-110, UX-117 |
| [26](../../reviews/inbox.md#26-licences-repository-governance-and-ci-costs) | licences, governance, CI costs | yes | DEP-T-001, DEP-T-002 (both assumed, DEP-T-002 partly) | DEP-T-001, DEP-T-005, UX-219, parts of DEP-T-002, DEP-T-018, DEP-T-029 |
| [27](../../reviews/inbox.md#27-messages-to-other-teams-nothing-is-sent-without-you) | messages to other teams | no; only the messages wait | — | the docs parts |
| [28](../../reviews/inbox.md#28-assumed-engine-bridges-runner-and-scheduler) | assumed: engine bridges, runner, scheduler | no | SR-003, CH-001 (assumed) | all 24 |
| [29](../../reviews/inbox.md#29-assumed-data-model-api-vocabulary-and-spec-owners) | assumed: data model, API vocabulary | no | SR-004, SR-005 (assumed) | all 15 |
| [30](../../reviews/inbox.md#30-assumed-ui-boards-review-screens-and-the-documentation-system) | assumed: UI boards, review screens, docs system | no | — | all 18 |
| [31](../../reviews/inbox.md#31-autopilot-budget-a-fresh-reading-before-apply1) | autopilot budget reading before APPLY1 | yes, the whole step | — | none |

- **Entries that block APPLY1: #11 to #26.** APPLY1 can still apply every accepted and assumed finding. It must leave untouched the spec sections named on each entry's "Blocked" line.
- **Blocker-level entries, as the consolidator lists them: #11, #12, #14, #15, #16 and #22.**
    - Five of them hold a finding rated blocker that is not assumed: SR-001, SR-002, SEC-101, SEC-102 and DL-101.
    - #16 holds no finding rated blocker, but it decides the MVP cut that P1 plans from.

**R12 was included.** `pipeline.yaml` lists only R1 R2 R4 R5 R7 R8 R8b R9 R11 for TRIAGE1 and APPLY1. The workflow triaged R12 as well, so that its questions sit in the same inbox entries as the related findings. The inbox block states that R12 findings block a later apply step, not APPLY1. According to the consolidator, R12 findings appear in #12, #13, #16, #17, #19, #25 and #30 (checked against the Covers lines; the consolidator's summary also named #20, which holds only R7 findings).

**Two inconsistencies flagged by the consolidator:**

- **#20 (UX-202):** R7 recommends OIDC in 0.1, but the cut recommended in #16 (SR-007) puts OIDC in the alpha. #20 recommends option (b), so that the two answers agree.
- **#12 (UX-124):** the EnvConnect board shows a 15 min registration token and 24 h rotation. These values are bundled with SEC-106's credential-lifetime question.

**Next.** The autopilot stopped before APPLY1. APPLY1 starts once Thomas answers [#31](../../reviews/inbox.md#31-autopilot-budget-a-fresh-reading-before-apply1) with a fresh budget reading. Ideally, Thomas also answers [#16](../../reviews/inbox.md#16-what-ships-in-01-mvp-cut), [#11](../../reviews/inbox.md#11-ingest-credential-for-observed-runs-and-are-observed-runs-in-01) and [#12](../../reviews/inbox.md#12-runner-server-transport-and-runner-credential-lifetime) first: they carry blockers, and APPLY1 would otherwise have to leave those sections untouched.
