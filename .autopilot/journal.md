# Autopilot journal

One entry per tick: time, steps started and finished, verification results, triage decisions, and what is waiting on Thomas.

## 2026-10-26 21:08 → 2026-10-27 00:40 UTC — tick 1 (wave W1)

- **Run:** `/autopilot --until W2 --budget 15%w --now 50`, driven by `/goal`. Integration branch `autopilot/integration` created from `main` (8f38f49) with PR #2 merged in (decision 0001, MVP scope), so the reviews saw the recorded decisions.
- **Finished (9):** R1, R2, R4, R5, R7, R8, R9 (one dynamic workflow, 24 agents: reviewers in parallel, one merger per round that re-checked every blocker and major), D2 (spike in a worktree, branch `spike/cloud-env` @217a92c, pushed; only the note is integrated), R11 (doc-reviewer + ux-reviewer + merger).
- **Findings filed:** R1 5 blockers / 33 majors / 15 minors; R2 0/9/28 (+ verification table, 206 claims); R4 1/29/10; R5 30 findings; R7 40; R8 1/6/8; R9 0/6/11; R11 0/6/21. All waiting for TRIAGE1.
- **Docs gate and reviews** (doc-reviewer verdicts, kept here because the pages only carry `review:`; see R11 DOC-003): R1 approve 14/14, R2 approve 12/14, R4 approve 13/14, R5 approve 13/14, R7 approve 14/14, R8 approve 13/14, R9 approve 13/14, D2 approve 12/14, R11 approve 13/14. Required changes from the reviewers applied before marking done. `python3 tools/docs/check.py`: 0 failures. `mkdocs build --strict`: pass.
- **W1 exit_check:** `ls docs/reviews/R1-consistency.md … R11-docs.md` → 0 (pass).
- **Deviations:** the W1 outputs landed as commits on `autopilot/integration` instead of one PR per step (they share `mkdocs.yml` nav lines; splitting after the push would have needed a force-push). The promotion PR to `main` carries them with the full CI.
- **Budget:** the status line does not feed `.autopilot/usage.json` in this cloud session, so the governor stays on the manual reading (50 %, "manual-stale") and counts 0 points; it answered `go` every time. This settles the autopilot.md §6 item "whether the status line runs in cloud sessions": it does not. Subagent tokens this tick: about 5.9 M (W1 reviews 4.39 M, docs 1.03 M, R11 0.38 M, fixes 0.2 M).
- **D2 result:** Docker, Compose, Nextflow 26.10, Playwright and mermaid-cli work; Snakemake partly; sind and kind do not (cgroup v1). This affects D3, T3 and T4, which assume sind and kind in cloud sessions.
- **Waiting on Thomas:** nothing new yet; TRIAGE1 turns the questions of the rounds into inbox entries.

## 2026-10-27 00:20 → 06:30 UTC — tick 2 (TRIAGE1, then stop)

- **Promotion:** PR #3 (`autopilot/integration → main`, wave W1) merged with a merge commit once docs-gate, pr-body and preview passed (`15c3697`); PR #2 is merged with it.
- **Finished:** TRIAGE1. `docs/playbooks/triage-policy.md` was applied as written, with one agent per round and one consolidator as the only writer of the inbox. Totals: **320 findings, 163 accepted, 4 rejected, 153 to the inbox, 88 of them assumed.**

  | Round | accepted | rejected | inbox | assumed |
  |---|---|---|---|---|
  | R1 | 13 | 0 | 40 | 25 |
  | R2 | 33 | 0 | 4 | 2 |
  | R4 | 21 | 0 | 19 | 16 |
  | R5 | 4 | 0 | 26 | 6 |
  | R7 | 26 | 0 | 14 | 7 |
  | R8 | 7 | 0 | 8 | 4 |
  | R8b | 19 | 3 | 10 | 7 |
  | R9 | 9 | 0 | 8 | 6 |
  | R11 | 22 | 0 | 5 | 5 |
  | R12 | 9 | 1 | 19 | 10 |

- **Inbox:** entries #11–#30, grouped by decision. #11–#26 block parts of APPLY1. Five blockers wait for Thomas (SR-001 → #11, SR-002 → #12, SEC-101 → #14, SEC-102 → #15, DL-101 → #22), and #16 holds the MVP cut. #28–#30 only list assumptions to confirm. #31 asks for a budget reading.
- **R12** was triaged too, although `pipeline.yaml` leaves it out of TRIAGE1. Its findings block a later apply step, not APPLY1.
- **Restart:** the container restarted after 4 of 10 rounds. The run was resumed from the same workflow run: the 4 rounds came from cache and 6 ran live. Commits `eb411ce`, `0238f25`, `b266e5b`, `2a209a3`.
- **Docs:** `docs/progress/W2/TRIAGE1.md`, doc-reviewer **approve 12/14**. Its two required changes were applied: #20 holds no R12 finding, and back-links were added from the inbox and the ten review files. `python3 tools/docs/check.py`: 0 failures.
- **Borderline triage call to confirm:** SEC-129 (device-code expiry, CLI-only scopes, SAML replay) was accepted as hardening of decided auth modes, not as a new security default.
- **Stopped before APPLY1 (budget).** The governor cannot measure use in this session: no status line, a manual reading only, 0 points counted, `go` every time. Subagent tokens so far: about 8.6 M (tick 1: about 5.9 M; TRIAGE1: about 1.1 M, docs about 0.3 M, plus the restart). APPLY1, which edits the specs from about 250 findings, is not started on a blind governor. Inbox #31 asks Thomas for a fresh `/usage` reading or another budget.
- **Waiting on Thomas:** #11–#26 (reserved or blocking), #31 (budget); the confirmations in #27–#30.
