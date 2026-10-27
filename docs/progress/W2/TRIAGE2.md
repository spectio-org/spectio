---
step: TRIAGE2
wave: W2
status: done
pr: null
review: approve
review_score: 12/14
review_ref: ".autopilot/journal.md, tick 5"
---
# TRIAGE2 · Sort the findings of the journeys and API contract rounds

!!! success "Done 2026-10-27 · 61 findings: 21 accepted, 0 rejected, 40 sent to the inbox (33 assumed, 7 waiting for Thomas) · inbox #32–#40"

![TRIAGE2 sorting figure: the 61 findings of R3 and R6, one cell each, coloured by severity, sorted into 21 accepted, 33 assumed, 7 waiting for Thomas and 0 rejected](../../assets/diagrams/triage2_sort_light.png#only-light)
![TRIAGE2 sorting figure: the 61 findings of R3 and R6, one cell each, coloured by severity, sorted into 21 accepted, 33 assumed, 7 waiting for Thomas and 0 rejected](../../assets/diagrams/triage2_sort_dark.png#only-dark)

*One cell is one finding, the same size on both sides. Red-edged cells are blockers, amber majors, grey minors. Four R3 blockers are assumed, three wait; none was accepted.*

## What changed

- **Status lines in two review files.** Every finding's `Status: open` now holds a triage decision, dated `(TRIAGE2, 2026-10-27)`, in the same four forms as [TRIAGE1](TRIAGE1.md):
    - `accepted`;
    - `rejected`, with the reason (none this time);
    - `inbox`, the question waits for Thomas;
    - `inbox, assumed: <option> — pending Thomas`, the recommended option proceeds until Thomas answers.

    The files are [R3](../../reviews/R3-journeys.md) (journeys) and [R6](../../reviews/R6-contract.md) (0.0.1 API contract). Each header gets a one-line round summary, and each findings table gets a Status column (R6's "All findings" table had none, so the column is new there).
- **Inbox, entries #32 to #40.** A new [TRIAGE2 block](../../reviews/inbox.md#triage2-2026-10-27) groups the 40 inbox findings by decision. Each finding appears once, on a "Covers" line. Entries #1 to #31 are unchanged.
- **No spec was edited.** Accepted and assumed findings reach the specs in APPLY2.
- **Commit** on `autopilot/integration`: `autopilot(TRIAGE2): triage R3 and R6, 21 accepted, 40 inbox (33 assumed), entries #32–#40` (the two review files, `inbox.md`, this page and the sorting figure with its script).

## Why

Thomas should only see what needs him. The [triage policy](../../playbooks/triage-policy.md) says what the autopilot may decide alone:

- **accept** a confirmed, local, minor or major fix that reverses no logged decision and stays out of the reserved topics;
- **reject** what cannot be reproduced, duplicates a handled finding, or only asks for style changes;
- **send to the inbox** everything else, and **assume** the recommended option when it is reversible and only affects docs.

R3 and R6 were written against the [0.0.1 cut](../../specs/mvp-0.0.1.md), so the reserved topic that comes up most is the scope of 0.0.1 itself ([`dev-environment-and-testing.md`](../../specs/dev-environment-and-testing.md) §15.1): any answer that adds a feature to 0.0.1 or drops one goes to Thomas.

Step definition: `TRIAGE2` in `docs/playbooks/pipeline.yaml` (wave W2, `kind: triage`, rounds R3 and R6, writes `docs/reviews/*.md` and `docs/reviews/inbox.md`). How triage fits into a tick: [`autopilot.md`](../../playbooks/autopilot.md).

## Evidence

**How the step ran.** The orchestrator triaged both rounds itself, as the [autopilot skill](../../playbooks/autopilot.md) asks for `triage` steps, with no subagent:

- "Confirmed" (policy condition 1): the R3 and R6 mergers had re-checked every finding against the quoted passages ([Progress · R3](R3.md), [Progress · R6](R6.md)); both rounds were written on the same day, on the specs that are still current.
- "Local fix" (condition 3) was read strictly: at most two content sections in total, in the owning spec or specs. Other specs may only get a link or a one-line mirror (a CLI flag that mirrors an endpoint, a UI label). A new board frame, or a rule written into another spec, counts as content. A first pass had accepted 31 findings; re-checked this way, 10 of them change content in more than two sections, so they moved to the inbox as assumed, under the new entry [#40](../../reviews/inbox.md#40-assumed-fixes-that-are-right-but-not-local): SR-061, CH-043, CH-046, CH-047, CH-048, CH-050, CH-051, SR-065 and UX-250 (R3), and SR-082 (R6). Their fix still proceeds in APPLY2; only the decision is left to Thomas.
- "No logged decision reversed" (condition 4): each accepted proposal was compared with the entries of `docs/decisions/log.md` dated up to 2026-10-27, including the 0.0.1 cut. None reverses one.
- Decisions were written into the files by one script. It asserted that every `### <ID>` heading got exactly one decision, and that no `Status: open` was left.
- The inbox "Covers" anchors were computed with the same slug rule as the site (Python-Markdown `toc`), then checked by `mkdocs build --strict`.

**Counts per round, read back from the review files.** The columns are accepted, rejected, inbox (including assumed), assumed, and still open:

```console
$ cd docs/reviews
$ for f in R3-journeys R6-contract; do printf "%-13s" $f; for s in accepted rejected inbox "inbox, assumed" open; do printf " %4s" "$(grep -c "Status:\*\* $s" $f.md)"; done; echo; done
R3-journeys      6    0   21   16    0
R6-contract     15    0   19   17    0
```

| Round | Findings | Accepted | Rejected | Inbox | of which assumed | waiting for Thomas |
|---|---:|---:|---:|---:|---:|---:|
| [R3](../../reviews/R3-journeys.md) | 27 | 6 | 0 | 21 | 16 | 5 |
| [R6](../../reviews/R6-contract.md) | 34 | 15 | 0 | 19 | 17 | 2 |
| **Total** | **61** | **21** | **0** | **40** | **33** | **7** |

**Severity against decision.** This table joins each finding's heading with its status line (a short Python script over the two files):

| Severity | Accepted | Rejected | Inbox, waiting | Inbox, assumed | Total |
|---|---:|---:|---:|---:|---:|
| blocker | 0 | 0 | 3 | 4 | 7 |
| major | 16 | 0 | 4 | 27 | 47 |
| minor | 5 | 0 | 0 | 2 | 7 |
| **Total** | **21** | **0** | **7** | **33** | **61** |

All seven blockers are in R3. No blocker was accepted, because the policy accepts only minors and majors (fact corrections excepted):

- **assumed (4):** SR-062 and CH-042 (relaunch and resume, #32), SR-055 and CH-041 (local runner and detached heads, #35);
- **waiting for Thomas (3):** SR-057 and SR-058 (how rnaseq gets a gate, MultiQC in the install, #34) and SR-054 (ingest contract, #36).

The four majors that wait are SR-056 (#34), SR-067 (#35), SR-080 (#36) and SR-091 (#37).

**Exit criterion.** TRIAGE2 has no `exit_check` of its own in `pipeline.yaml`; the wave W2 check is `python3 tools/docs/check.py`. The step's own outputs are complete: no finding is left `open` (last column above), and `inbox.md` holds entries #32 to #40.

## Figures and media

- **Sorting figure** at the top of this page (to-scale, one cell per finding), as `documentation-system.md` §3.1 asks for a `triage` step. Script: `tools/diagrams/triage2_sort.py`; outputs `docs/assets/diagrams/triage2_sort_{light,dark}.{svg,png}`.

## Findings and open questions

**Inbox entries from this step.** In short (the full wording is in the [inbox](../../reviews/inbox.md#triage2-2026-10-27)):

| # | Topic | Findings | Assumed already | Blocks APPLY2 |
|---|---|---|---|---|
| [32](../../reviews/inbox.md#32-relaunch-at-a-failed-gate-resume-after-a-failure-and-the-001-gate-verbs) | relaunch at a gate, resume after a failure, 0.0.1 gate verbs | 10 (2 blockers) | all 10, option (B): a child run | no |
| [33](../../reviews/inbox.md#33-when-every-check-passes-does-the-gate-wait-for-a-person) | default when every check passes | 1 | (c): opt-in auto-approve, waits by default | no |
| [34](../../reviews/inbox.md#34-001-scope-how-nf-corernaseq-gets-its-stages-and-gate-workflow-registration-multiqc-in-the-install) | how rnaseq gets stages and a gate; MultiQC in the install | 3 (2 blockers) | none (scope is reserved) | yes |
| [35](../../reviews/inbox.md#35-engines-and-the-in-process-runner-on-a-laptop) | local runner record, detached heads, who installs the engines | 3 (2 blockers) | SR-055, CH-041 | the prerequisites section only |
| [36](../../reviews/inbox.md#36-the-ingest-contract-for-001-split-inbox-11) | ingest contract for 0.0.1, split of #11 | 2 (1 blocker) | none (auth is reserved) | yes |
| [37](../../reviews/inbox.md#37-browser-protection-for-the-token-less-loopback-api) | browser protection for the token-less loopback API | 1 | none (security posture is reserved) | yes |
| [38](../../reviews/inbox.md#38-assumed-engine-events-and-the-progress-denominator) | assumed: engine events, progress denominator | 3 | all 3 | no |
| [39](../../reviews/inbox.md#39-assumed-the-reads-that-001-boards-need) | assumed: the reads 0.0.1 boards need | 7 | all 7 | no |
| [40](../../reviews/inbox.md#40-assumed-fixes-that-are-right-but-not-local) | assumed: fixes that are right but not local | 10 | all 10, (a): apply as written | no |

- **#32 has the most weight.** It holds both R3 relaunch blockers and five R6 findings about ReviewReport's action bar. The assumed option (B) keeps the run states as they are and makes "Relaunch…" and "Resume" create a child run; `apply` and `go_back` are not in 0.0.1.
- **#34 and #36 decide whether journey 1 works end to end.** Without an answer, APPLY2 cannot say how rnaseq gets its gate or how the bridges report a driven run.
- **#36 overlaps #11.** It asks to split #11 so that the driven-run part of api §14 can be written for 0.0.1, while the observed-run credential stays deferred.

**Next.** APPLY2 applies the 21 accepted and 33 assumed findings of R3 and R6, and leaves untouched the sections named on the "Blocked" lines of #34, #35 (SR-067 part), #36 and #37.
