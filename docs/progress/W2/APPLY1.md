---
step: APPLY1
wave: W2
status: done
pr: null
review: approve
review_score: 11/14
review_ref: ".autopilot/journal.md, tick 3"
---
# APPLY1 · Apply the triaged findings of nine review rounds to the specs

!!! success "Done 2026-10-27 · 232 findings: 60 applied, 148 partly applied, 24 not applied · 13 specs changed · no inbox entry added"

## What changed

- **Decision recorded first: the first version is 0.0.1.** Thomas answered [inbox #16](../../reviews/inbox.md#16-what-ships-in-01-mvp-cut) at the start of the step. The first version is a basic local MVP. See the [decision log, 2026-10-27](../../decisions/log.md#2026-10-27-first-version-is-001-a-basic-local-mvp), the new page [MVP 0.0.1](../../specs/mvp-0.0.1.md), and [`dev-environment-and-testing.md` §15](../../specs/dev-environment-and-testing.md#15-what-ships-in-which-version), now the single owner of what ships in which version. Commits `2a06528` and `0954747`.
- **Findings applied to the owning specs.** APPLY1 took every finding that [TRIAGE1](TRIAGE1.md) accepted or assumed in R1, R2, R4, R5, R7, R8, R8b, R9 and R11. That is 232 findings. R12 is not part of APPLY1 (`pipeline.yaml`). The authoritative list is the decision-log section [2026-10-27 — APPLY1](../../decisions/log.md#2026-10-27-apply1-review-findings-applied-r1-r2-r4-r5-r7-r8-r8b-r9-r11). It gives the counts, the specs changed by file and §, the revisions of earlier decisions, the assumed decisions by inbox number, and the deferred work.
- **13 specs changed.** New sections got new numbers, and nothing was renumbered:
    - [`admin-and-operations.md`](../../specs/admin-and-operations.md);
    - [`api-and-data-model.md`](../../specs/api-and-data-model.md): new §7.1 and §8.1–§8.4;
    - [`architecture-plugins-and-packaging.md`](../../specs/architecture-plugins-and-packaging.md#131-event-path-spool-first-forwarded-by-the-runner): new §2.1, §12 and §13;
    - [`authentication-and-access.md`](../../specs/authentication-and-access.md): new §3.1;
    - [`checking-scenarios.md`](../../specs/checking-scenarios.md): new §4.1 and §12;
    - [`cli-and-shared-libraries.md`](../../specs/cli-and-shared-libraries.md);
    - [`depictio-ecosystem-reuse.md`](../../specs/depictio-ecosystem-reuse.md);
    - [`dev-environment-and-testing.md`](../../specs/dev-environment-and-testing.md);
    - [`documentation-system.md`](../../specs/documentation-system.md);
    - [`schedulers-and-monitoring.md`](../../specs/schedulers-and-monitoring.md);
    - [`synthesis.md`](../../specs/synthesis.md): dated "superseded" notes where a newer spec owns the topic;
    - [`telemetry-and-analytics.md`](../../specs/telemetry-and-analytics.md);
    - [`ui-spec.md`](../../specs/ui-spec.md): new §3.3, §3.4 and §11.
- **Other pages.**
    - [map](../../map.md), [API](../../api/index.md), [features](../../features/index.md), [landing page](../../index.md), [installation](../../installation/index.md), [usage](../../usage/index.md);
    - [`next-phase.md`](../../playbooks/next-phase.md) (T1–T4, P1, D6) and [`autopilot.md`](../../playbooks/autopilot.md) §7;
    - the Progress pages of W0 (F1–F7), the nine W1 pages, and [TRIAGE1](TRIAGE1.md).
- **New pages:**
    - [Other tools](../../features/other-tools.md) (FC-047);
    - the research note [depictio and LabID re-audit, 2026-10-26](../../research/depictio-audit-2026-10-26.md). It is R8's re-audit, first committed in `da129ee`. [`depictio-ecosystem-reuse.md` §3](../../specs/depictio-ecosystem-reuse.md#3-requests-to-make-to-depictio-small-reversible), the [map](../../map.md) and two research notes cite it.
- **Status lines in nine review files.** Every applied finding's **Status** line now says what was applied, where, and what is pending: `applied`, `partly applied` or `not applied`, dated `(APPLY1, 2026-10-27)`. Each file's header gets an APPLY1 count. The files are [R1](../../reviews/R1-consistency.md), [R2](../../reviews/R2-open-validations.md), [R4](../../reviews/R4-constraints.md), [R5](../../reviews/R5-security.md), [R7](../../reviews/R7-ui.md), [R8](../../reviews/R8-depictio.md), [R8b](../../reviews/R8b-depictio-tooling.md), [R9](../../reviews/R9-landscape.md) and [R11](../../reviews/R11-docs.md). Findings that wait for Thomas, and rejected ones, are unchanged.
- **One decision-log section** for the whole step: [2026-10-27 — APPLY1](../../decisions/log.md#2026-10-27-apply1-review-findings-applied-r1-r2-r4-r5-r7-r8-r8b-r9-r11).
- **Commits** on `autopilot/integration` (`git log --oneline 0954747..d287a85`, 9 commits):
    - 8 WIP commits, `7bf310d` to `fb8e167`;
    - `d287a85`: the decision-log section.

    `727bb44` merged `origin/main` (PRs #4, #5, #7) into the branch afterwards. It is not part of APPLY1.

## Why

APPLY1 turns the triage decisions into spec text. The [triage policy](../../playbooks/triage-policy.md) lets accepted and assumed findings proceed. Each assumed change is marked *(assumed — pending Thomas, inbox #n)*, so removing what a marker covers reverts it.

Step definition: `APPLY1` in `docs/playbooks/pipeline.yaml` (wave W2, `kind: apply`, `rounds: [R1, R2, R4, R5, R7, R8, R8b, R9, R11]`, writes `docs/specs/*.md` and `docs/decisions/log.md`). [`next-phase.md`](../../playbooks/next-phase.md) has no separate prompt for apply steps. Decision: [decision log, 2026-10-26, autopilot](../../decisions/log.md#2026-10-26-autopilot-instead-of-step-by-step-prompts). The applied changes are recorded in [2026-10-27 — APPLY1](../../decisions/log.md#2026-10-27-apply1-review-findings-applied-r1-r2-r4-r5-r7-r8-r8b-r9-r11).

### Before and after

**Per finding:** each finding's **Status** line in its review file is the before/after record. It names the sections changed and what is pending. For example, CH-001 in R4:

```console
$ grep -n "^- \*\*Status:\*\* partly applied (APPLY1" docs/reviews/R4-constraints.md | head -1 | cut -c1-200
150:- **Status:** partly applied (APPLY1, 2026-10-27): architecture §2, §13 (new), §13.1; schedulers §3.1, §12; synthesis §8, §10; ui-spec §4.8 (assumed — pending Thomas, inbox #28); pending
```

**Earlier decisions revised by APPLY1.** These are taken from the log section, which records them as the findings asked:

| Topic (finding) | Before | After | Owner now |
|---|---|---|---|
| Snakemake steering (SR-008, CH-009) | steering through the API | a CLI head job (`--until`, `--forcerun`, `--configfile`); the constraint is "no parsing of process output for tracking" *(assumed, #28)* | synthesis §2, §5ter |
| "Broker" (SR-049) | a "broker" in the 2026-10-25 entries; api §3 kept its own kinds table | three extension points: task backend, pub/sub, event bridge | architecture §2 |
| Shell (SR-053) | the 2026-10-25 shell | the top bar spans the full width, with the sidebar below it; list views use a "table / rows" toggle *(assumed, #29)* | ui-spec §2 |
| Raw engine payloads (CH-011) | keep the raw JSON | kept while the run is active, then archived *(assumed, #28)* | api §8.4 |
| Projections (CH-012) | read models built in the ingest transaction | one projector builds them after the ingest ack *(assumed, #28)* | api §8.1 |
| Backups (CH-022) | portable JSON Lines export | native same-engine backups by default; JSON Lines for migration and export *(assumed, #24)* | admin §4.3 |
| SLURM poll (CH-027) | `squeue/sacct/sinfo --json` | plain-text `squeue` for the routine poll; `--json` for details *(assumed, #28)* | schedulers §3.2–§3.3 |

## Evidence

**How the step ran.** These figures come from the workflow summary recorded in `.autopilot/journal.md`, tick 3.

| Item | Value |
|---|---|
| Workflow | one agent per target file, 43 agents, 0 errors |
| Totals | about 4.9 M subagent tokens, 717 tool calls |
| Duration | about 79 minutes. `.autopilot/state.json` has `APPLY1.started_at` = `2026-10-27T08:12:26Z`, and `d287a85` is dated 09:32 UTC. |
| Overlaps | a finding raised in several rounds was applied once, in the wording of the most recent round (for example CH-001 over SR-017, FC-040 over CH-009) |
| Budget | Thomas read 57 % on 2026-10-27 ([inbox #31](../../reviews/inbox.md#31-autopilot-budget-a-fresh-reading-before-apply1)). That left an 8-point budget for APPLY1. His next reading was 59 % at APPLY1 start (limit 65 %), recorded in `.autopilot/journal.md`, tick 3. |

**Counts per round, read back from the review files.** The first block reads each file's header. The second counts the status lines; its columns are applied, partly applied, not applied, and all findings in the file:

```console
$ cd docs/reviews
$ for f in R1-consistency R2-open-validations R4-constraints R5-security R7-ui R8-depictio R8b-depictio-tooling R9-landscape R11-docs; do printf "%-21s %s\n" $f "$(grep -o 'APPLY1 (2026-10-27): [0-9]* applied, [0-9]* partly applied, [0-9]* not applied' $f.md)"; done
R1-consistency        APPLY1 (2026-10-27): 11 applied, 26 partly applied, 1 not applied
R2-open-validations   APPLY1 (2026-10-27): 25 applied, 8 partly applied, 2 not applied
R4-constraints        APPLY1 (2026-10-27): 8 applied, 28 partly applied, 1 not applied
R5-security           APPLY1 (2026-10-27): 2 applied, 7 partly applied, 1 not applied
R7-ui                 APPLY1 (2026-10-27): 0 applied, 27 partly applied, 6 not applied
R8-depictio           APPLY1 (2026-10-27): 1 applied, 8 partly applied, 2 not applied
R8b-depictio-tooling  APPLY1 (2026-10-27): 1 applied, 22 partly applied, 3 not applied
R9-landscape          APPLY1 (2026-10-27): 5 applied, 9 partly applied, 1 not applied
R11-docs              APPLY1 (2026-10-27): 7 applied, 13 partly applied, 7 not applied
$ for f in R1-consistency R2-open-validations R4-constraints R5-security R7-ui R8-depictio R8b-depictio-tooling R9-landscape R11-docs; do printf "%-21s" $f; printf " %4s" "$(grep -c '^- \*\*Status:\*\* applied (APPLY1' $f.md)" "$(grep -c '^- \*\*Status:\*\* partly applied (APPLY1' $f.md)" "$(grep -c 'not applied (APPLY1' $f.md)" "$(grep -c '^- \*\*Status:\*\*' $f.md)"; echo; done
R1-consistency          11   26    1   53
R2-open-validations     25    8    2   37
R4-constraints           8   28    1   40
R5-security              2    7    1   30
R7-ui                    0   27    6   40
R8-depictio              1    8    2   15
R8b-depictio-tooling     1   22    3   32
R9-landscape             5    9    1   17
R11-docs                 7   13    7   27
```

Headers and status lines agree. The totals are 60 applied, 148 partly applied and 24 not applied, so 232 findings. That equals TRIAGE1's accepted plus assumed findings for these nine rounds, per round (for example R1: 13 + 25 = 38 = 11 + 26 + 1). "Partly applied" mostly means the spec text is done, and a board, tool, CI or inbox-blocked part remains. "Not applied" means one of five things:

- the section is blocked by an inbox entry (for example SR-035, #25);
- the fix is board-only (UX-211, UX-222, UX-236–UX-239);
- the fix is tool- or stylesheet-only (DOC-017, DOC-021, DOC-023–DOC-026);
- the finding was already fixed by another one (FC-021, by CH-001 and CH-006);
- what the fix needs does not exist yet (DOC-018: its shots are not taken yet).

**What the step touched:**

```console
$ git diff --stat 0954747 d287a85 | tail -1
 52 files changed, 1661 insertions(+), 738 deletions(-)
$ git log --diff-filter=A --format='%h %s' -- docs/research/depictio-audit-2026-10-26.md
da129ee autopilot(APPLY1): spec edits in progress
```

The 52 files are 13 specs, 9 review files, `decisions/log.md`, 17 Progress pages, 3 research notes, 2 playbooks and 7 other site pages. `inbox.md` and `R12-ui-scenarios.md` are not among them.

**Exit criterion.** APPLY1 has no `exit_check` of its own; the W2 check is `python3 tools/docs/check.py`. The log section records that `mkdocs build --strict` passed, that `check.py` reported 0 failures, and that the four Mermaid blocks in the changed files render with mermaid-cli 11. Both commands were run again after this page was written:

```console
$ uvx --with mkdocs-material mkdocs build --strict -d /tmp/spectio-site
INFO    -  Documentation built in 4.61 seconds
$ python3 tools/docs/check.py
mermaid: 4 blocks checked
diagrams: 3 scripts re-run, 6 SVGs compared
media: 30 outputs in the manifest
::error file=docs/progress/W2/APPLY1.md::[progress] a done step needs review: approve
progress: 18 pages checked
docs gate: 1 failure(s)
```

The build exits 0 with no warnings. The one `check.py` failure is gate item 6 (§3.3) for this page: it is `done`, but `doc-reviewer` has not approved it yet. It clears when the verdict is recorded.

## Figures and media

None. APPLY1 changed text only, and §3.1 asks an `apply` step for a sketch only when a mechanism changed. The new mechanisms (event pipeline, engine bridges, state machines) are specified in text. Their figures belong to the build steps that implement them. A PR carrying this step uses the `no-figure` label with that reason.

**Follow-up figure.** A sketch of the engine-bridge spool and the event pipeline ([architecture §13.1](../../specs/architecture-plugins-and-packaging.md#131-event-path-spool-first-forwarded-by-the-runner), [api §8.1](../../specs/api-and-data-model.md#81-event-pipeline)) is due in T2 (engine event capture), the first step that runs those bridges against real engines.

## Findings and open questions

**Deferred work.** The full list, finding by finding, is in the [log section](../../decisions/log.md#2026-10-27-apply1-review-findings-applied-r1-r2-r4-r5-r7-r8-r8b-r9-r11). In short:

| Area | What waits | Example findings |
|---|---|---|
| UI boards | about 70 boards and shared components, desktop and phone, plus tokens | UX-203, UX-205, UX-219, UX-220, CH-001 |
| CI workflows | `ci.yml` with `ci-ok`, release-please app token, security, publishing, Renovate, chart, upgrade, Nextflow edge, `docs.yml` on Node 24 | DEP-T-001, DEP-T-002, DEP-T-005, CH-006, FC-013 |
| Tools | `spectio.yml` JSON Schema, `dev/doctor.sh`, pre-commit, `tools/docs/check.py` coverage, media generators, `hooks/progress.py` | SR-004, SR-047, DOC-002, DOC-021 |
| Site | `extra.css`, `overrides/main.html`, `mkdocs.yml` (`repo_url`, and nav entries for `features/other-tools.md` and `research/depictio-audit-2026-10-26.md`, which are not in the nav yet) | DOC-013, FC-047, DL-111 |
| Skills, CLAUDE.md | `autopilot` and `write-docs` record the doc-reviewer verdict; External facts rule; board keyboard rules | DOC-003, DEP-T-031, UX-219 |
| For Thomas | GitHub App, trusted publishers, Renovate app, EMBL egress probe, messages to depictio and other teams | DEP-T-002, DEP-T-006, CH-001, SR-036 |
| Blocked by inbox | sections named on the "Blocked" line of [#11–#26](../../reviews/inbox.md#triage1-2026-10-27) were not edited | SR-035 (#25), FC-002 (#19), SEC-129 (#15, #20, #21) |

**Assumed decisions to confirm.** Each one is marked in the spec text and grouped by inbox number in the log section: #12, #13, #14, #17, #18 and #22–#30.

**Stale names left in place** because their sections are blocked: depictio-ecosystem-reuse §1.1, api §6, §13.1, checking §11.3, auth §2, schedulers §5. The list is in the log section.

**No new inbox entry.** APPLY1 added no question. It applied the TRIAGE1 decisions and left the blocked sections alone.

**Next.** The autopilot stops and asks Thomas for a fresh usage reading before R3 and R6, the next W2 steps (`depends_on: [APPLY1]`).
