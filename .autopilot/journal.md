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

## 2026-10-27 06:30 → 10:30 UTC — tick 3 (0.0.1 decision, APPLY1, then stop)

- **Budget:** Thomas's readings 57 % (before) and 59 % (APPLY1 start); limit 65 %. The governor still runs on manual readings only.
- **Decision recorded first:** the first version is **0.0.1, a basic local MVP** (one user, no sign-in, engines on the same machine; launch, monitor, relaunch with changed parameters, parameter history, one simple QC check and gate; Snakemake and Nextflow through nf-spectio). Log entry "2026-10-27 — First version is 0.0.1", `docs/specs/mvp-0.0.1.md`, `dev-environment-and-testing.md` §15 as the single owner of version contents, inbox #16 answered.
- **Finished:** APPLY1. One agent per target file (43 agents, 0 errors, about 4.9 M subagent tokens, 717 tool calls, 79 min), then a close agent wrote the statuses and one log section "2026-10-27 — APPLY1: review findings applied (R1 R2 R4 R5 R7 R8 R8b R9 R11)".

  | Round | applied | partly | not applied |
  |---|---|---|---|
  | R1 | 11 | 26 | 1 |
  | R2 | 25 | 8 | 2 |
  | R4 | 8 | 28 | 1 |
  | R5 | 2 | 7 | 1 |
  | R7 | 0 | 27 | 6 |
  | R8 | 1 | 8 | 2 |
  | R8b | 1 | 22 | 3 |
  | R9 | 5 | 9 | 1 |
  | R11 | 7 | 13 | 7 |
  | **Total** | **60** | **148** | **24** |

  "Partly" mostly means the spec text is done and a board, tool, CI or inbox-blocked part remains. Not applied: blocked by an open inbox entry, or a board- or tool-only fix.
- **Commits:** `ea6a9c9`, `7bf310d`, `50f0baa`, `c5fa121`, `da129ee`, `1d3a61a`, `f8e011d`, `fb8e167` (8 WIP saves while the workflow ran), `d287a85` (log). `727bb44` merged `origin/main` (PRs #4, #5, #7) into integration; the only conflict was the log, both sides kept.
- **Deferred** (full list in the log section): about 70 boards, CI workflows, tools, site CSS and nav, skills, CLAUDE.md wording, and sections blocked by inbox #11–#26.
- **Gate:** `mkdocs build --strict` exit 0; `tools/docs/check.py` 0 failures.
- **Docs:** `docs/progress/W2/APPLY1.md`. doc-reviewer: approve 11/14; its four text changes applied (workflow figures cited from this tick, five "not applied" cases, budget wording, follow-up figure due in T2), log section links back to the step page.
- **Stopped before R3 and R6 (budget).** Thomas asked for a fresh usage reading before the next reviews.

## 2026-10-27 08:00 → 10:50 UTC — tick 4 (R3 and R6 reviews, then stop)

- **Budget:** Thomas's reading 60 % at the start; limit 65 %. Manual readings only.
- **Finished:** R3 (journeys review) and R6 (API contract against the screens), claimed in `70e1501`, both read-only on specs.

  | Round | findings | blocker | major | minor | inbox questions |
  |---|---|---|---|---|---|
  | R3 journeys | 27 | 7 | 18 | 2 | — |
  | R6 contract | 34 | 0 | 29 | 5 | 5 |

- **Exit checks:** `docs/reviews/R3-journeys.md` and `docs/reviews/R6-contract.md` exist with findings tables in the README format.
- **Docs:** `docs/progress/W2/R3.md` (doc-reviewer approve 14/14 after the map was redrawn: every blocker and major pinned on its step, severity key in the pin colours) and `docs/progress/W2/R6.md` (approve 13/14, caption and step link fixed). Figures `tools/diagrams/r3_journeys_map.py` and `r6_contract_map.py`.
- **Gate:** `tools/docs/check.py` 0 failures; `mkdocs build --strict` exit 0.
- **Not triaged yet:** the 61 findings wait for TRIAGE2, then APPLY2.
- **Stopped before TRIAGE2 (budget).** Thomas is asked for a fresh `/usage` reading.

## 2026-10-27 10:59 → 11:16 UTC — tick 5 (TRIAGE2)

- **Budget:** Thomas's reading 62 %, new limit 70 % (`budget.py start --weekly 8 --now 62`).
- **Finished:** TRIAGE2, claimed in `4bf83e7`, committed in `b573cf1`. Triage done by the orchestrator, no subagent.

  | Round | findings | accepted | rejected | inbox | of which assumed | waiting |
  |---|---|---|---|---|---|---|
  | R3 journeys | 27 | 6 | 0 | 21 | 16 | 5 |
  | R6 contract | 34 | 15 | 0 | 19 | 17 | 2 |
  | **Total** | **61** | **21** | **0** | **40** | **33** | **7** |

- **Condition 3 re-check.** doc-reviewer asked how "local fix" was checked. Read strictly (at most two content sections in total; other specs get links or a one-line mirror only), 10 of the first 31 accepts were not local: SR-061, CH-043, CH-046, CH-047, CH-048, CH-050, CH-051, SR-065, UX-250, SR-082. They moved to inbox #40 as assumed (apply as written). Condition 4: no logged decision reversed.
- **Inbox:** entries #32–#40. Waiting on Thomas: #34 (rnaseq stages and gate, MultiQC), #35 SR-067 part (who installs the engines), #36 (ingest contract, split of #11), #37 (browser protection of the loopback API).
- **Exit checks:** no finding left `open` (grep above); W2 check `tools/docs/check.py` 0 failures; `mkdocs build --strict` exit 0.
- **DOC-REVIEW** TRIAGE2 verdict=approve score=12/14 (accuracy 1, completeness 1; the two required changes, the condition 3 explanation and the counts, are applied).
- **Gate weakness noted:** `tools/docs/check.py` accepts `review_score: null` on a done Progress page. Not changed here (tools are out of this step's writes); to fix in a later docs-tooling step.

## 2026-10-27 11:18 → 12:06 UTC — tick 6 (APPLY2, W2 complete)

- **Budget:** limit 70 % (Thomas's reading 62 % at tick 5). Manual readings only.
- **Finished:** APPLY2, claimed from base `8e655ea`; specs in `cf5357b`, docs fixes in `8eef7ac` and `97944c4`.
- **Result:** 54 of 61 R3 and R6 findings reached the specs (7 applied in full, 47 partly), 7 untouched waiting for Thomas, 10 specs changed, 33 fixes assumed pending inbox #32–#40. No new inbox entry.
- **Exit checks:** W2 check `tools/docs/check.py` 0 failures (8 scripts, 16 SVGs, 50 outputs, 22 pages); `mkdocs build --strict` exit 0.
- **DOC-REVIEW** APPLY2 verdict=approve score=13/14 (second pass; first pass changes 10/14: wrong §13.7 link, missing back-links, unverified configfile order, no before/after; all fixed, plus the gate-verb owner now dev-environment §15.1).
- **W2 complete.** Waiting on Thomas: inbox #32–#40 (assumed answers to confirm), #34, #36, #37, and the older open entries.

## 2026-10-27 12:45 → 13:25 UTC — decision change outside the step pipeline (0.0.1 revised, landing page)

- **Why no step.** Thomas changed the 0.0.1 cut and asked for mandatory security review, a new landing page and a header that keeps the emblem's contrast. None of this is a pipeline step (no `pipeline.yaml` entry, no Progress page); it is recorded here and in the decision log entry "2026-10-27 — 0.0.1 revised: on the cluster, no gates, a token link".
- **Before → after (0.0.1).** Before: a single machine, the local executor, one QC check and gate, tokenless loopback. After: one `spectio serve` per user on the login node through an SSH tunnel and a token link, engine heads submitted with `sbatch` (Snakemake head [to be validated] in T3), events back through the spool on the shared file system, no gates, no accounts, nothing on Kubernetes. Sketch: `docs/assets/diagrams/mvp001_cluster_*` in dev-environment §15.3.
- **Review and CI.** `review-code` runs `security-reviewer` on every step in parallel with `code-reviewer`; dev-environment §11 adds secret scanning, dependency audit, SAST and a workflow linter (built by D4).
- **Landing evidence.** Playwright renders of the built site at 1440, 900, 400 and 360 px, light and dark, header, tabs and phone drawer: no horizontal scroll, Works-with icons rendered, emblem visible on phones. doc-reviewer rendered it again at 1440, 900, 390 px.
- **Commits.** `ef9a4cf` (specs), `0302826` (landing), `bd639db` (sketch), `ab8e4e0` (CSS review fixes), then the doc-review fixes. PR weber8thomas/spectio#12, preview https://pr-12.spectio.pages.dev.
- **DOC-REVIEW** first pass verdict=changes score=10/14 (Host allow-list vs tunnel ports, undefined one-time token, Snakemake sbatch head stated as decided, §11 contradiction, stale owners and inbox notes, missing step record, landing owner not updated, emblem hover, a copied hex). All 15 fixed.
- **New assumptions for Thomas.** Snakemake head via `sbatch` (fallback: on the login node); run directories under a runs root on the shared file system; local executor for tests only; token link = single-use 15-minute ticket swapped for an in-memory session cookie (a restart ends sessions); CI security fail policy.

## 2026-10-27 14:03 → 16:35 UTC — tick 7 (inbox answers, then W3 batch D1 D3 D4 D5)

- **Inbox answers first.** Thomas answered 24 entries in the dashboard. They are recorded in `docs/reviews/inbox.md` and the decision log entry "2026-10-27 — Inbox answers #5 to #37 (dashboard)" (`69c46ad`, doc-review fixes `60e03a8`, `ae36f3a`). Later-version spec edits wait for one apply pass after W3 (Thomas's choice).
- **Budget:** Thomas's reading 64 % at about 14:25, limit 75 % (`budget.py start --weekly 11 --now 64`). Four build steps fitted. Step costs were not recorded, so the counter still reads 0 pt; a fresh `/usage` reading is needed before the next step.
- **Finished:** D5, D1, D3, D4, claimed in `98d74c2`. Each step got its own worktree and branch and was squash-merged into the integration branch.

  | Step | PR | Squash | code / security review | rounds | doc-review |
  |---|---|---|---|---|---|
  | D5 dev previews | weber8thomas/spectio#13 | `5eb2542` | approve / approve | 2 | approve 12/14 |
  | D1 Claude setup check | weber8thomas/spectio#14 | `74fd447` | approve / approve | 1 | approve 14/14 |
  | D3 toolchain, bootstrap, doctor | weber8thomas/spectio#15 | `fc19981` | approve / approve | 2 | approve 13/14 |
  | D4 CI, security checks, Claude review | weber8thomas/spectio#16 | `6a6338b` | approve / approve | 3 | approve 14/14 |

- **Exit checks and step tests, on the integration branch after the merges:**
  - D3 `bash dev/doctor.sh`: exit 0, `doctor: all layers passed (2 skipped)`. sind and kind are skipped on cgroup v1 here; all six layers pass in CI (`dev-env.yml`).
  - D4 `ZIZMOR_OFFLINE=true bash tools/ci/security.sh all`: exit 0 (no leaks, no dependency issues, 0 SAST findings, 0 workflow findings). Online zizmor audits need a GitHub token: 401 in this session, green in CI.
  - D1 and D5 have no `exit_check`. Their checks (`claude-config`, `preview`) were green on their PRs.
  - `python3 tools/docs/check.py`: 0 failures.
- **Merge conflicts:** `docs/assets/media.yaml`, `previews.yml`, the decision log and dev-env §11, because the parallel steps all edit them. Each was resolved by merging the integration branch into the step branch and keeping both sides; nothing was rebased or force-pushed.
- **CI incidents:**
  - D3's first `docs-gate` hung for 29 min on a slow apt mirror while Playwright installed its fonts. It was cancelled and re-run once, and passed in 1 min 37.
  - `pipelines-real`, the corpus of real pipelines, is red: 18 of 23 jobs failed in the nightly run on `main`, and 5 of 9 in the PR tier on D4. It is kept out of `ci-ok` until T7, but still runs and reports its own checks.
  - Causes found so far:
    - methylseq 4.2.0 and viralrecon 3.0.0: Nextflow 26 stops at config parse with `Invalid include source` (`conf/aws/batch/nextflow.config`, `conf/test_full_sispa.config`); whether those files are absent from the release tags is **[to be validated]**;
    - dna-seq-gatk-variant-calling v2.1.1: conda can no longer solve `bcftools=1.10`;
    - molkart and rnaseq: `No space left on device` on the runner (CREATE_STACK, UCSC_BEDCLIP), read from the `run.log` artifacts of run 40535210648. T7 starts with runner disk.
- **Triage:** none (build steps). New inbox entries #41–#44 (D3).
- **Waiting on Thomas:**
  - **D5:** rename the Cloudflare secrets to `CLOUDFLARE_*`, check Codespaces live, and add `wave-approved` himself.
  - **D1:** SEC-D1-03; whether `claude-config` becomes a required check; PyYAML hash pinning.
  - **D3:** inbox #41–#44.
  - **D4:** the Claude review secret; the release App ID and key in the `release` environment; `RELEASE_PLEASE_ENABLED`; the branch protection from autopilot §8; whether the autopilot gets its own GitHub identity; whether to switch to `client-id`.
  - **Earlier answers:** confirm #14 and #32; allow deleting the old branch (#5); the GitHub App (#8).
- **17:40 UTC, Thomas:** usage reading 69 % (limit 75 %; budget restarted with `--now 69`, 4 points of room). Promotion PR weber8thomas/spectio#17 may be merged once `docs-gate`, `pr-body`, `preview`, `ci-ok` and the security checks are green; the known-red `pipelines-real` corpus is ignored until T7 (his choice 1a).
