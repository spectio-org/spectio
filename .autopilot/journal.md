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
- **17:20 UTC:** promotion PR weber8thomas/spectio#17 merged into `main` with a merge commit (`63614b7`). docs-gate hung on apt once more (ffmpeg install); it was cancelled and re-run once, then passed. All required checks were green; `pipelines-real` was left red, as Thomas allowed (1a).

## 2026-10-27 17:45 → 21:35 UTC — tick 8 (setup check, dashboard review, T7)

- **Setup script (inbox #43).** The cloud environment has Full network, the two variables and the setup script, and they reach the session. The script ran in `/home/user`, the clone's parent, so bootstrap was skipped and `dev/doctor.sh` failed on Python until `bash dev/bootstrap.sh --ci` was run by hand (19 s; then `doctor: all layers passed (2 skipped)`). Dev-env §2 now gives a script that starts with `cd /home/user/spectio` (`9162e84`); Thomas replaces it.
- **Budget:** Thomas's readings 69 % at the start and 70 % mid-tick; limit raised from 75 % to 80 % (session message). Step costs not recorded.
- **Dashboard and autopilot skill review** (`3217ee4..cddb67b`, unreviewed until now): `review-code` took four rounds (Thomas allowed a third fix round): round 1 changes 3+4 majors, round 4 approve / approve. Record: `docs/reviews/code/dashboard.md`. Merged by weber8thomas/spectio#18 (`bfa4f0a`); dashboard republished as version 15 at the same link (`9a30fd4`). Thomas's dashboard answers to #41, #42, #43 recorded (`b57bfd1`).
- **Finished: T7**, real-pipeline corpus green in CI. PR weber8thomas/spectio#19, squash `761d845`. code / security review approve / approve (one fix round: CR-7 unit tests in CI, summary guard, setup-uv cache off); doc-review approve 11/14 after seven required changes (Nextflow permalink, counts, duplication).
  - Causes: runner disk (9 failures across 7 nf-core entries; a free step takes `/` from 15 GB to about 46 GB), Nextflow 26's strict parser on methylseq 4.2.0 and viralrecon 3.0.0 (`NXF_SYNTAX_PARSER=v1`, nf-core/methylseq#607, nf-core/viralrecon#606), and upstream breakage in six Snakemake catalog entries, now `manual`. Tiers pr 2, nightly 14, manual 7 (see the light PR tier below).
  - Evidence: run 40555936925 (PR tier 7/7), run 40562495868 (nightly: 13/13 nf-core), and the final PR-tier run 40584542402 on `7d73267` (demo and the ms-proteomics dry run green, `ci-ok` green with `pipelines-real` in its `needs`).
  - `pipelines-real` is back in `ci-ok`'s `needs` (Thomas's decision 1a closed).
  - Runner measured: 2 CPU, 7.75 GB, 6.9 GB available; the 6 GB per-task cap stays.
- **Light PR tier (Thomas, inbox #45).** A PR-tier run on `7a3fe4f` lost rnaseq to a Docker registry reset (run 40578574693). Thomas: the CI runners are small, so do not spend time there. Only nf-core/demo and the ms-proteomics dry run stay in `pr`, about 5 min. rnaseq, viralrecon, methylseq, molkart and rna-seq-star-deseq2 now run nightly. Recorded in a decision-log entry, dev-env §10.2 and the figure (`7d73267`). No `review-code` pass for this commit: it changes corpus data, one test assertion and the figure, with no new logic.
- **Runner outage, then public repository.** At 21:10 every job on `7d73267` failed within 2–3 s with no runner assigned (`runner_id: 0`, no steps, no log). The likely cause is the private-repository Actions minutes or the spending limit **[to be validated]**. Thomas made the repository public; the failed jobs were re-run once and passed. Public runners are 4 CPU / 16 GB **[to be validated]**, and `--limits public` now applies. Those limits are not measured yet: the next corpus run measures them, and the docs that say "private repository" are updated then.
- **End of tick:** usage snapshot `.autopilot/usage/744d3a04-….json` (16 subagents, 880 API calls); dashboard rebuilt (41 steps, 46 inbox entries; `check_xss.js` ok with and without the CSP) and republished as version 16 at the same link. The artifact reads as private (owner only).
- **Exit checks:** T7's step test `python3 -m unittest tests/pipelines/real/test_run_corpus.py` (5 OK); `python3 tools/docs/check.py`: 0 failures.
- **Triage:** none (build step). New inbox entries #45 (answered the same day: light PR tier) and #46 (follow-up: pin the corpus by SHA, replace the Snakemake composite action).
- **Waiting on Thomas:**
  - replace the cloud setup script with the dev-env §2 version (#43); switch the network to Custom without wildcards;
  - answer #46 and #44;
  - with the repository now public: a full-history secret scan (gitleaks scans only PR diffs) **[to be validated]**;
  - a fresh `/usage` reading before D6 or T1;
  - the items still open from tick 7 (D5 secrets, D1, D4 secrets and protection, #5, #8, #14, #32).

## 2026-10-27 21:40 → 23:05 UTC — tick 8, continued (promotion, repo scan, T1)

- **Promotion:** weber8thomas/spectio#20 merged into `main` as a merge commit (`cc00b25`), all checks green.
- **Budget:** Thomas's reading 73 % at 21:40; limit 80 %. Only T1 dispatched (D6 left for the next tick). Step costs not recorded.
- **Public-repository scan** (security-reviewer, read-only; gitleaks v8.21.2 on all history and branches, plus grep):
  - no tokens, keys or passwords;
  - the nf-core megatest Slack webhook URL (third-party, already public in nf-core's S3) is removed from `main` and integration but still at the tip of 9 stale remote branches (`autopilot/D1`, `D3`, `D5`, `R6`, `claude/ci-docs-fetch-base`, `claude/code-review-agents`, `claude/compact-thresholds`, `feat/loving-noether-8xnb4j`, `spike/cloud-env`);
  - workflows clean (no `pull_request_target`, fork PRs get no secrets, actions pinned by SHA).
  Thomas decides on deleting those branches and on the history rewrite (#5).
- **Finished: T1**, golden fixtures for the synthetic pipelines. PR weber8thomas/spectio#21, squash `4cb00c1`.
  - 44 fixtures (Nextflow 26.10.4, 25.10.9, 25.04.8; Snakemake 9.27.1), each 11/11 on record and check; `--golden check` in `pipelines-synthetic.yml`, which moved to 26.10.4 (#42 done).
  - Fixed on the way: the Snakemake align gate skipped qc (`--until` runs only the target's dependencies); the `docker` profile could not run a task; spec §10.1 corrected (Snakemake retries tool errors; time-limit exit code 143 / none / 124 by version).
  - Resume identity for #32: Nextflow `-resume` gets a new run name and keeps the session ID, same launch directory only; Snakemake draws a new `workflow_id` each run. Both fit option B.
  - Not run: the rnaseq/sarek gate stop-and-resume (inbox #47, assumed: a `gate` key in the nightly corpus).
  - code / security review approve / approve after one fix round (1 blocker, 2 majors fixed); simplifier no change; doc-review changes 10/14, then approve 14/14.
  - CI: `oom_fatal` hit the known Snakemake fault `lost-retry-at-checkpoint-update` twice in a row on `712c3bc`; commented on the PR, one re-run green. A single repeat leaves a few percent of runs red.
- **Exit checks:** T1 step test `python3 -m unittest tests/pipelines/synthetic/test_golden.py && run_scenarios.py --engine snakemake --golden check` (8 OK, 11/11, exit 0); `python3 tools/docs/check.py`: 0 failures.
- **Triage:** none (build step). New inbox entries #47 (assumed) and #48 (checking-scenarios §12.3 gate targets, for `/apply-findings`).
- **Waiting on Thomas:**
  - the 9 stale branches carrying the webhook URL, and #5 (history rewrite);
  - GitHub settings: approval for fork PR workflows, secret scanning and push protection;
  - answer #44, #46, #47, #48 and #32 (option B now has the engine evidence);
  - replace the cloud setup script (#43); network to Custom without wildcards;
  - a fresh `/usage` reading before D6;
  - the items still open from tick 7.
- **Follow-ups:** SEC-T1-06 (shared `/tmp` workdir) before T3; the Snakemake fault rate (repeat more than once, or move off the checkpoint).
- **End of tick:** usage snapshot refreshed (`.autopilot/usage/744d3a04-….json`: 24 subagents, 1246 API calls); dashboard republished as version 17 at the same link, private, `answers` write rule owner-only, `check_xss.js` ok with and without the CSP.

## 2026-10-27 23:10 → 23:45 UTC — tick 9 (promotion of T1, D6 minimal)

- **Inbox:** the dashboard `answers` collection holds the same 27 documents recorded at the first owner-only publish (same `at`); nothing new to copy. No unhandled `Answer:` line.
- **Promotion:** weber8thomas/spectio#22 (T1 and the tick-8 records) merged into `main` as a merge commit (`62a4c88`), every check green; `pipelines-synthetic / snakemake 9.27.1` passed first time (no `lost-retry-at-checkpoint-update` this run).
- **Budget:** `--budget 10%w --now 75`, stop at 85 % (Thomas). One build step only (`ready.py --only D6`); `check` answered go, fits 1. No live usage reading in this cloud session (`manual-stale`); step cost not recorded.
- **Finished: D6**, docs pipeline in CI, **minimal version** on Thomas's request. PR weber8thomas/spectio#23, squash `b67ace9`.
  - `check.py` build check now fails when the `hooks/progress.py` output is missing (unrendered placeholder, or a page without the rendered strip or table); `tools/docs/test_check.py` (7 tests) runs in `docs-gate`; `fail()` escapes workflow-command characters; `mkdocs.yml` excludes `fonts/*.ttf`.
  - Virgil licence: `excalidraw/virgil` `LICENSE.md` declares OFL-1.1, but its own `Virgil.woff2` name table says "Your Own Font Foundry … Freeware for personal use"; the depictio copy is a third build. Recorded as unconfirmed in `FONT-LICENSE.md`; no font committed; inbox #49.
  - Deferred (inbox #50): mike on the previews and `/versions`; Zensical evaluation; `hooks/shared_images.py` (not due: no mike version, `docs/assets` about 11 MB); byte-identical PNGs in CI (#49); the F4 and F6 figures.
  - code / security review approve / approve (0/0/4, 0/0/2), one fix round applying all minors except CR-4 (kept); simplifier no change; doc-review changes 10/14, then approve 14/14 (a fresh reviewer after a container restart lost the first re-review).
  - CI: one `ci-ok` failure on `343ab71` was the concurrency cancel caused by the next push (`results: success cancelled …`); green on `154a2f2`.
- **Exit checks:** D6 step test `python3 -m unittest tools/docs/test_check.py && python3 tools/docs/check.py --only build` (7 OK, 0 failures); `python3 tools/docs/check.py` on integration after the merge: 0 failures.
- **Triage:** none (build step). New inbox entries #49 (Virgil licence conflict, revisits #1) and #50 (the D6 follow-up).
- **Environment:** auto-merge is not enabled on the repository, so step PRs are merged by hand once green; the container restarted once mid-step (worktree commits survived; `autopilot/D6` pushed right after).
- **Waiting on Thomas:**
  - #49 (font) and #50 (where the rest of D6 goes);
  - the 9 stale branches carrying the webhook URL, and #5 (history rewrite);
  - GitHub settings: fork PR workflow approval, secret scanning and push protection; allow auto-merge if wanted;
  - answer #44, #46, #47, #48 and #32;
  - replace the cloud setup script (#43); network to Custom without wildcards;
  - a fresh `/usage` reading before the next build step.
- **End of tick:** usage snapshot `.autopilot/usage/6396c38c-….json` (6 subagents, 202 API calls at snapshot time); dashboard rebuilt (41 steps, 50 inbox entries; `check_xss.js` ok with and without the CSP) and republished as version 18 at the same link, private, `answers` write rule owner-only. The first two publishes were refused (not read; then identical content); the third went through after checking the saved live copy is the tick-8 build (no tick-9 content), so nothing was lost.

## 2026-10-28 07:10 → 08:00 UTC — tick 10 (promotion of D6, T2 spike)

- **Promotion:** weber8thomas/spectio#24 (D6 and the tick-9 records) merged into `main` as a merge commit (`35f2514`), every check green.
- **Budget:** Thomas gave 76 % and the same 85 % stop. One step (T2). `check` answered go, fits 1, still `manual-stale`; step cost not recorded.
- **Inbox:** Thomas corrects the dashboard answers at 10:00; the next tick reads them.
- **Finished: T2**, engine event capture (spike). PR weber8thomas/spectio#25, squash `afc2e9c`. The spike code stays on `spike/engine-events` @`3b4f654`; integration gets the note, the Progress page, the figure, the cast and the fixtures.
  - Snakemake 9.27.1: a logger plugin on `snakemake-interface-logger-plugins` 2.1.0 receives every record; 3 fixtures.
  - Nextflow 26.10.4 and 25.10.9: Tower protocol captured by a stdlib server; a first `nf-spectio` (`TraceObserverV2`, built without Gradle) runs next to `nf-tower` and reports the same run name and session ID in 6 of 6 runs; 12 fixtures.
  - 24 differences with the specs, for TRIAGE3. Three change a spec: the last `onTaskComplete` of a process can arrive after its `onProcessTerminate` (end of stage in checking-scenarios §11.5); Snakemake `job_error` carries no attempt number and no exit code; a checkpoint grows the total (32 → 67) through progress events only.
  - Fixtures: 15 JSON-lines files, 2.6 MB, normalised (paths, host, user, token); whether they stay on `main` in full is follow-up 5 of the note.
  - No review-code (spike code not reused); doc-review changes 10/14, then approve 13/14. The Progress banner said "review pending" after the merge; fixed in the tick commit.
- **Exit checks:** fixtures and note present; `python3 tools/docs/check.py` green in `docs-gate` on `925d262`. `ci-ok` red on superseded `2162203` was the concurrency cancel.
- **Triage:** none (spike). No new inbox entry; the note's two open questions (task `script`/`env` in `nf-spectio`, drain after the last `onProcessTerminate`) go to TRIAGE3.
- **Waiting on Thomas:**
  - the dashboard answers (10:00);
  - #49 (font) and #50 (rest of D6);
  - the 9 stale branches carrying the webhook URL, and #5;
  - GitHub settings: fork PR workflow approval, secret scanning and push protection, auto-merge;
  - #44, #46, #47, #48 and #32; the cloud setup script (#43); network to Custom;
  - a fresh `/usage` reading before the next build step.
- **End of tick:** usage snapshot `.autopilot/usage/6396c38c-….json` (8 subagents, 424 API calls at snapshot time); dashboard rebuilt (41 steps, 50 inbox entries; `check_xss.js` ok with and without the CSP) and republished as version 19 at the same link, private, `answers` write rule owner-only.

## 2026-10-28 08:05 → 08:20 UTC — tick 11 (T3 not runnable here; inbox #51)

- **Sync:** `autopilot/integration` fast-forwarded to `main` (`26299db`, promotion weber8thomas/spectio#26 of T2, merge commit, every check green).
- **Inbox:** the dashboard `answers` collection holds the same 27 documents (version 1, same `at` as recorded); nothing to copy. Thomas corrects them at 10:00.
- **Budget:** Thomas said "continue", limit 85 %, no fresh `/usage` reading (last 76 % before T2). Asked which step; no preference given. Chose T3.
- **Not started: T3 (and T4).** Both need sind or kind, which need cgroup v2. This cloud session still has the hybrid cgroup v1 layout (spike D2; dev environment §4.2), and Remote Control is not available to it. No worktree, no claim commit; both stay `pending`. Inbox #51: where T3/T4 run (recommendation: Thomas's machine, after the SEC-T1-06 fix).
- **Exit checks:** none (no step finished). `python3 tools/docs/check.py --only build`: 0 failures after the inbox entry.
- **Triage:** none.
- **Waiting on Thomas:**
  - #51 (where T3/T4 run); every ready step is blocked on it;
  - the dashboard answers (10:00);
  - #49, #50, #44, #46, #47, #48, #32, #43; the 9 stale branches carrying the webhook URL, and #5;
  - GitHub settings: fork PR workflow approval, secret scanning and push protection, auto-merge.
- **End of tick:** usage snapshot `.autopilot/usage/6396c38c-….json` (8 subagents, 463 API calls at snapshot time); dashboard rebuilt and republished at the same link (version 20), private, `answers` write rule owner-only.

## 2026-10-28 08:25 → 08:35 UTC — tick 11, continued (SEC-T1-06 fixed)

- **Promotion:** weber8thomas/spectio#27 (inbox #51, tick-11 records) merged into `main` as a merge commit (`08ef3cf`), every check green.
- **Thomas:** "Lance ce que tu peux avant d'avoir les réponses." T3 and T4 stay blocked on #51. The one thing doable here was their prerequisite, SEC-T1-06.
- **Fixed: SEC-T1-06** (follow-up of T1, not a pipeline step). PR weber8thomas/spectio#28, squash `7a2f1b0`.
  - Without `--workdir`, `run_scenarios.py` and `run_corpus.py` create a private `mkdtemp` directory (0700), print it and keep it for debugging. Before, they deleted and reused `/tmp/spectio-scenarios` and `/tmp/spectio-corpus`. An explicit `--workdir` is used as given; CI is unchanged.
  - 3 new unit tests (16 OK). Snakemake `happy` PASS in a `drwx------` workdir.
  - code / security review: approve / approve (2 and 3 minors). The fix round applied CR-S06-1 (corpus runner too), SEC-S06-2 (T1 How-to-test command) and SEC-S06-3 (cleanup documented). Code review approved the delta, adding CR-S06-3 (`${TMPDIR:-/tmp}`), which was applied. The simplifier made no change. Doc review approve 13/14, with its one optional fix applied.
  - Open: SEC-S06-1. An explicit `--workdir` in shared `/tmp` is still trusted (owner, symlink, mode not checked). Recorded in `docs/reviews/code/SEC-T1-06.md`.
  - CI on `720c8c8`: every check green, including `pipelines-real` (nf-core/demo, snakemake-ms-proteomics) and the three `pipelines-synthetic` legs.
- **Exit checks:** `python3 -m unittest tests/pipelines/synthetic/test_golden.py tests/pipelines/real/test_run_corpus.py` (16 OK); `python3 tools/docs/check.py`: 0 failures.
- **Waiting on Thomas:** #51 (where T3/T4 run; their SEC-T1-06 prerequisite is now met), then the items listed above.
- **End of tick:** usage snapshot `.autopilot/usage/6396c38c-….json` (12 subagents, 541 API calls at snapshot time); dashboard republished as version 21 at the same link, private, `answers` write rule owner-only, `check_xss.js` ok with and without the CSP.

## 2026-10-28 08:35 → 08:52 UTC — tick 11, continued (SEC-S06-1 hardening)

- **Fixed: SEC-S06-1** and the minors of the later rounds (SEC-S06-4, 4a, 4b; CR-S06-4, CR-S06-5). PR weber8thomas/spectio#30, squash `00f48db`.
  - An explicit `--workdir` is created with its missing parents under umask 077, resolved, and refused unless this user owns it, it is not a symlink, nobody else can write to it, and every resolved parent belongs to this user or root (sticky if others can write). The resolved path is used. The refusal names `chmod go-w`; the docstrings and `--help` state the rule.
  - 10 new unit tests (26 OK). A `--workdir` under a 777 parent is refused (exit 1).
  - code review approve on `3355a10..d31b2c9` (2 minors, fixed); security review approve on rounds 3, 4 and 5 (1, 2, then 0 minors). The simplifier made no change. Doc review approve 11/14, its required changes applied.
  - CI on `8d5c062`: every check green, including `pipelines-synthetic` (3 legs) and `pipelines-real` (nf-core/demo, snakemake-ms-proteomics), so `$RUNNER_TEMP` passes the new checks on hosted runners.
  - The `pr-body` check failed once on a missing `## Summary` section; fixed by editing the PR body.
- **Exit checks:** unit tests 26 OK; `python3 tools/docs/check.py`: 0 failures; `mkdocs build --strict`: built.
- **Waiting on Thomas:** #51 (where T3/T4 run; nothing else in the pipeline is ready), the dashboard answers (10:00), then the items listed in tick 11.
- **End of tick:** usage snapshot `.autopilot/usage/6396c38c-….json` (16 subagents, 649 API calls at snapshot time); dashboard rebuilt (41 steps, 51 inbox entries; `check_xss.js` ok with and without the CSP) and republished as version 22 at the same link, private, `answers` write rule owner-only.

## 2026-10-28 08:52 → 10:55 UTC — tick 11, continued (T4)

- **Direction:** Thomas finds the project over-complicated and asked what the steps are for before any code exists. Answer in inbox #52 (critical, not assumed): start a walking skeleton before T5, T6, R10 and P1, with a lighter process. The one-page proposal is `docs/plans/walking-skeleton-proposal.md`. Until he answers, W3 goes on, leaner: one review per small fix.
- **Inbox #51 (where T3/T4 run):** option (b), CI on GitHub-hosted runners (cgroup v2), assumed — pending Thomas. Two throwaway spikes checked it first:
  - `spike/t4-ci`: kind + Kueue on `ubuntu-24.04`, green (run 40663207755).
  - `spike/t3-ci`: sind `slurm-site`, green on run 4 (40670286528). Runs 1–3 were cancelled or red while JDK and Snakemake polling were fixed. Note on that branch: `docs/research/spike-t3-ci-2026-10-28.md`.
- **Merged into integration:** weber8thomas/spectio#32, squash `89fb4f3`. It closes the T1 findings CR-07, SEC-T1-01, 02, 03 and 07; CR-08 stays open.
- **Done: T4** (kind and Kueue), CI-driven. PR weber8thomas/spectio#33, squash `db7eb7f`.
  - It adds `dev/k8s/cluster.sh` (`k8s-mini`, `k8s-kueue`), `tests/k8s/scenarios.sh` (five scenarios), `pipelines-k8s.yml` (outside `ci-ok`) and 10 fixtures in `tests/fixtures/k8s/`.
  - Code and security review, 3 rounds. Round 1: approve, 4 + 5 minors. Round 2, on the fixes: changes, because the heads' deny check ran in namespace `default` and proved nothing (CR-T4-05, major). Round 3: approve.
  - CI then caught `can-i create pods/exec` being read as a pod named `exec` (CR-T4-08); fixed with `--subresource`.
  - Run 40673184674 went red after the merge of #32, which moved the task image to `params.python_image`.
  - `pipelines-k8s` green on the final code `007683c` (run 40674240654, 3 min 38 s).
  - Doc review: changes 7/14 (missing sketch and headings), then approve 14/14 on the fixed page.
  - For TRIAGE3: 10 differences with schedulers §4 and dev-env §4.2/§11 (the §4 Roles are not sufficient; the runner cannot read Workloads; Nextflow 25.10 needs `nf-k8s@1.2.3`; the queued state comes from the visibility API), plus SEC-T4-03 (create Jobs/Pods in a shared namespace = any ServiceAccount, hostPath) and SEC-T4-05 (supply chain). Specs not edited.
- **Started: T3** (sind SLURM), CI-driven, on `autopilot/T3`, from the spike.
- **Exit checks:** T4 `python3 tools/docs/check.py`: 0 failures; `mkdocs build --strict`: built; every PR check green on `c22123d`.
- **Waiting on Thomas:** #52 (code first, critical), confirming #51 (b), the dashboard answers, then the items listed in tick 11.

## 2026-10-28 10:55 → 12:18 UTC — tick 11, continued (T3, corpus retry, TRIAGE3)

- **Done: T3** (sind SLURM), CI-driven. PR weber8thomas/spectio#35, squash `e2c7d41`.
  - It adds `dev/slurm/cluster.sh` (`slurm-mini`, `slurm-site`, `slurm-rest`), `tests/slurm/scenarios.sh`, `pipelines-slurm.yml` (outside `ci-ok`, nightly at 04:41 UTC) and 24 fixtures in `tests/fixtures/slurm/slurm-26.05.5/`.
  - Code and security review, 2 rounds: approve (1 blocker, 2 majors, 12 minors found and fixed or deferred) and approve (7 minors). Doc review approve 13/14.
  - New facts for the specs: a Nextflow task over its time limit ends `FAILED 140:0`, never `TIMEOUT`; a Snakemake task job always ends `FAILED 1:0`; `sacct --json` names `kill_request_user`; a Snakemake head in `sbatch` works for `happy`.
  - Every check green on `646a6eb`, including the six `pipelines-slurm` jobs.
- **Merged: corpus retry.** PR weber8thomas/spectio#36, squash `613c89c`. A failed Nextflow corpus entry is retried once with `-resume`, and the `public` limits go to 13 GB (SPK-T7-02, SPK-T7-05). It answers the red nightly 40649538349 (a quay.io 502 and a lost runner).
- **Done: TRIAGE3** (round "spikes", 69 findings from T2, T3, T4 and T7): 44 accepted, 8 rejected, 3 already applied by T3, 14 to the inbox. New inbox entries #53 to #60: 9 reserved (k8s Roles #53, work namespace and tokens #54, event payloads #55, slurmrestd token #59), 4 assumed (#56 `aborted`, #57 pipeline workflows join `ci.yml`, #58 the autopilot watches the nightlies, #60 deferred SLURM coverage). Commit `efb00cf` on `autopilot/APPLY3`.
- **Running:** APPLY3 (parts A to C applied, dev-env part running), T5 (scenario runner, CI-driven), T3 follow-ups (CR-T3-11, CR-T3-12, SEC-T3-07).
- **Waiting on Thomas:** #52 (code first, critical), #51 (b) to confirm, the reserved items #53, #54, #55 and #59, the dashboard answers.

## 2026-10-28 12:18 → 12:55 UTC — tick 11, continued (APPLY3, Nextflow pin, T3 follow-ups, T5)

- **Done: APPLY3** (with TRIAGE3). PR weber8thomas/spectio#40, squash `08ecc94`. 42 spikes findings applied, 5 partly, 2 by PR #36; schedulers §3, api §7.2 (`aborted`, assumed #56), dev-env §1/§3/§4/§10.1/§11 (#57, #58, #60 assumed), decision-log entry "APPLY3: spikes round findings applied". Doc review approve 12/14; its four required changes applied (Before | After table, plain #56 marker, `ABORTED` scoped to Tower with the `nf-spectio` side **[to be validated]**, `handler.status` wording). Gates: `check.py` 0 failures, `mkdocs build --strict` clean; every PR check green on `bbfa7d3`.
- **Merged: Nextflow pin from `versions.env`** (SPK-T7-03). PR weber8thomas/spectio#38, squash `3bafe3e`; `pipelines-real.yml` reads `NEXTFLOW_VERSION` from `dev/versions.env`; nf-core/demo and the Snakemake proteomics entry green on the PR. Code review approve 0/0/2, security approve 0/0/1.
- **T3 follow-ups** (PR weber8thomas/spectio#39): positive control for slurmrestd (spx `DELETE` of its own job: 200, `CANCELLED`), `test_fixture.py` in the `unit` job of `ci-ok`, slurmrestd errors redacted through `fixture.SECRET`. Review round 3: code approve 0/0/4, security approve 0/0/4; fixes in `0f17403`. Every check green, including the six `pipelines-slurm` jobs; squash `7242408`.
- **T5** (scenario runner, `dev/scenario.py`): round 1 code changes (1 major: a failed `up` leaked), security changes (2 majors: `down` ran tools from a cluster-writable PATH; kind nodes mounted the whole repository read-write). Fixed: cleanup on failed `up`, host PATH only in `down`, repository mounted read-only in kind with one read-write mount of the scenario's own directory, `apiServerAddress: 127.0.0.1`, per-scenario Kueue manifest download. `scenarios.yml` 40688967336 and `pipelines-k8s.yml` 40688967168 green on `e347ff4` (the first push broke `pipelines-k8s`: `SPECTIO_REPO` read before `lib.sh`). Deferred and recorded: SEC-T5-03 (partly), SEC-T5-04.
  - Round 2 (on `4148643`): code changes with 1 blocker (CR-8: a failed `up` ran `down` on names another checkout may own), security approve (5 minors). Fixed in `cf655ec`: `up` owns the network `spx-N` before it may clean up by name, host tools checked before `claim`, guarded `scenario.json`, Kueue manifest in `TMPDIR`, `parallel.sh` refuses existing IDs. SEC-T5-08 (kubeconfig in the read-write mount) deferred to dev-env §5 "Not built". Doc review approve 12/14, changes applied. PR weber8thomas/spectio#41 squash `90ec099` after every check went green on `aa05608` (a `RETURN` trap in the Kueue download first broke `pipelines-k8s` `kueue`, run 40690398142; fixed). T5 stays running until a round-3 code review of the round-2 fixes approves.
- **Promoted to main:** weber8thomas/spectio#42, merge commit `7e9a576` (APPLY3, Nextflow pin, T3 follow-ups), every check green on `cab3e93`. T5 reaches main with the next promotion.
- **Waiting on Thomas:** #52 (code first, critical: T5 was built under the current plan), #51 (b) to confirm, the reserved items #53, #54, #55 and #59, the assumed items #56, #57, #58 and #60, the dashboard answers.
- **T5 round 3** (code review of the round-2 fixes on `aa05608`): CR-8 closed; changes for CR-13 (major: `parallel.sh`'s failure trap could still `down` another checkout's `spx-<id>`) and CR-14 (minor: `down` released the network before the rest was gone). Fixed on `autopilot/T5-followups`, PR weber8thomas/spectio#43 open (18 unit tests OK; `scenarios.yml` running). T5 stays running until #43 merges.
- **Dashboard:** not republished at the end of the tick. The build is now 17 MB (images of the new figures), over the 16 MB artifact limit; version 24 (12:48 UTC) is the latest online. The next tick shrinks `imgs.json` in `tools/dashboard/build.py`.

## 2026-10-28 12:57 → 13:10 UTC — tick 11, end (T5 done, dashboard size)

- **Done: T5.** PR weber8thomas/spectio#43 (CR-13, CR-14), squash `aaff4e0`, every check green on `5158f4c` (17, `scenarios.yml` "four scenarios in parallel" included). Round 4 code review on `aaff4e0`: approve, 0 blockers, 0 majors, 2 minors. CR-15 (stale `parallel.sh` header) fixed on integration; CR-16 (no test runs the trap's skip of a released ID) recorded as Progress finding 11. Final `CODE step=T5 review=approve b/M/m=1/2/13 security=approve b/M/m=0/2/10 rounds=4`.
- **Dashboard:** `tools/dashboard/gen.py` embeds each figure's tracked SVG instead of its PNG (8.6 MB of PNG become 4.0 MB of SVG; the figures lose the hand-drawn font inside `<img>`, a deliberate trade-off): page 10.6 MB, under the 16 MB limit; `check_xss.js` passes. Code review approve 0/0/3 (font trade-off and size claim fixed in the comment and README; the previous entry named `build.py`, the change is in `gen.py`). Republished at the same URL.
- **Next:** promotion PR integration → main (T5, #43, dashboard fix).
- **Waiting on Thomas:** unchanged (#52 critical, #51 (b), reserved #53, #54, #55, #59; assumed #56, #57, #58, #60; dashboard answers).
- **Promoted to main:** weber8thomas/spectio#44, merge commit `1aa45fe` (T5, #43, dashboard SVG fix), 27 checks green on `452292b`. Dashboard version 25 published at the same URL.

## 2026-10-28 13:31 → — tick 12 (MVP narrowed, T6, R10, P1)

- **Thomas, 13:35 UTC:** the MVP handles no Kubernetes and no extra complexity; an ultra-simple UI; launch and monitoring of workflows; no gating; no visualisation. Recorded: decision log "0.0.1 narrowed: launch and monitor, an ultra-simple UI", dev-env §15.1 (owner), `mvp-0.0.1.md`, the P1 prompt; relaunch and parameter history out of 0.0.1, assumed (inbox #61); dated note on #52 (stays open).
- **T6 running** in a separate cloud session (`session_01MF8RxLya2qysy5qS11CEqD`, branch `autopilot/T6`), narrowed to a minimal Playwright skeleton; it reports back with its PR.
- **Done: R10** (synthesis and go / no-go), `docs/reviews/R10-synthesis.md`: 450 findings read, 123 open (8 blockers, 74 majors, 41 minors); 70 of the 82 open blockers and majors belong to features that left 0.0.1; 12 touch it, 7 already decided or applied. Recommendation: GO for P1 now, code after P1 under C1–C4; no-go trigger if login nodes forbid long-running processes or SSH forwarding. Decisions for Thomas: D0 #52, D1 #61, D2 #34 (SR-056), D3 #55, D4 #62 (new, cancel assumed yes). Doc review: changes 10/14, fixed, then approve 13/14.
- **P1 running** (plan of the walking skeleton under the narrowed cut).
- **Done: P1** (walking-skeleton plan), `docs/plans/P1-walking-skeleton.md`: 5 milestones (events in, heads, served safely, API and screens, on the cluster), 23 tasks, 20 assumptions marked pending Thomas; every R10 §3a row and every §15.3 requirement has a task and a test; no spec edited. Gap found: §15.3 req. 2 needs a session-free bootstrap page (Assumption 8). Doc review approve 11/14; required changes applied. **Next: GO**, Thomas's go / no-go; no product code before it.
- **T6:** PR weber8thomas/spectio#45 from the worker session, code review approve (3 rounds, 0/1/6 fixed), security approve (0/0/5), doc review 13/14; red only on docs-gate and preview from the base (P1 page pending review, now fixed). SEC-T6-05 filed as inbox #63 (assumed).
- **Done: T6.** PR weber8thomas/spectio#45 squash `e956025` (every check green on `84b5331`). W3 and W4 are done up to the GO gate.
- 14:28 promotion PR #46 merged into main (merge commit `48c4b4c`), all checks green; dashboard v26 republished. Pipeline waits at the GO gate (Thomas: #52, assumed #61 #62 #63 #34 #55 #56, P1 assumptions).
- 17:22 Applied Thomas's 2026-10-28 decisions (head in tmux on the login node, EMBL only, SSH config entry and `spectio open` side by side, state file `~/.spectio/server.json`): PR weber8thomas/spectio#47 squash `f51dca9`, every check green on `edf8f04`; P1 now 24 tasks (Task 10 tmux launcher, new Task 24 laptop access); new inbox #64 (node-local disk for SQLite at EMBL), open. Doc-reviewer pass not run (fork could not spawn agents); self-review only.
- 17:40 Doc review of PR #47 (already merged): changes, 9/14 (7 required, 7 optional). Fixes on branch `autopilot/apply-access-tmux-review` (no PR yet, doc review first): required 1–7 and optional 8–10, 12–14 applied, 11 answered (cleared, allow-listed head environment; security posture unchanged). Thomas, 2026-10-28: SSE kept (decided; api §8.3, ui-spec §7, P1 Assumption 7); EMBL login nodes share everything but some temporary directories, so SQLite becomes a rebuildable index in a node-local temp dir, rebuilt from the run directories (assumed, inbox #64 option (d); dev-env §15.3, architecture §7.2/§7.3, P1 Assumption 21). Laptop tool named `spectio-open` everywhere. New Progress page `docs/progress/W4/APPLY4.md` with the `apply4_access` figure; review pending.
- 18:00 Done: APPLY4 (access fixes after #47). PR weber8thomas/spectio#49 squash `2e60e24`, 15 checks green on `908365e`. Doc review of the fix branch approve 12/14 (required: inbox #15 name, Evidence grep, rebuild keeps cancels and launch failures through run-dir markers, APPLY4 Figures and Findings sections; optional 5–11 applied). Security review changes 0/5/5, SEC-131..140 all applied as dev-env §15.3 trust boundaries, req. 5 and new requirements 8–11 with named P1 tests; server key moved to the node-local directory; record `docs/reviews/code/APPLY4.md`. Inbox #64 stays open (assumed (d); temp dir, polyinstantiation and tmpfiles ages to validate).
- 18:20 APPLY5 (Thomas, 2026-10-28: 0.0.1 also monitors runs started from a terminal; bridges in the Nextflow registry and on PyPI): branch `autopilot/apply-observed-runs`, no PR yet. Architecture §13.8 (pointer file `~/.spectio/observed/`, monitor only), dev-env §15.1 row and §15.3 req. 10, api §5.1 and ui-spec §6 notes, mvp-0.0.1 §2–§3, P1 M6 Tasks 25–26 and Assumption 22, inbox #65–#67, decision log. Docs gate 0 failures, strict build green. Doc review pending.
- 18:33 Done: 0.0.1 lite UI boards. PR weber8thomas/spectio#48 squash `0b89cb9`, checks green on `fc3d070`. New canvas page "0.0.1 lite" with 20 boards: 13 desktop (Lite*: Home, Runs, Launch, LaunchSnakemake, RunDetail, RunTasks, RunLogs, RunFailed, CancelDialog, Legend, States, Sidebar, Topbar) and 7 phone (MLite*: Home, Runs, RunDetail, CancelSheet, Launch, Topbar, Tabbar). Cut: projects, gates, review, visualisation, Kubernetes and multi-environment, users and sign-in, depictio, relaunch, admin. The full boards are unchanged. mvp-0.0.1 §2 and the UX-227 sentence point at the lite boards; design/README.md lists what each board keeps and drops; 4 shots `docs/assets/shots/lite-*_light.webp`. ux-reviewer and doc-reviewer did not run (the fork could not spawn agents): self-review against ui-spec §4.11 and §11 only. [to be validated]: the Snakemake SLURM failure message wording, the class of a Snakemake job error, and whether Ctrl-C makes each engine cancel its SLURM jobs.
- 18:39 Done: APPLY5 (runs started from a terminal in 0.0.1; bridges in the Nextflow registry and on PyPI). PR weber8thomas/spectio#50 squash `4f32512`, checks green on `abac081`. Doc review approve 11/14 on `c66a29b` (required 1–6 and optional 7–13 applied: release mechanics owned by dev-env §12, the pointer stays at `~/.spectio/observed/`). Security review block 1/4/4, SEC-141..149 all applied as dev-env §15.3 req. 12 and trust boundary (iv), tests named in P1 Tasks 25–26 ([record](docs/reviews/code/APPLY5.md)). Inbox #65 and #67 assumed; #66 (claim `nf-spectio`, `snakemake-logger-plugin-spectio`, `spectio`, `spectio-open`; all 404 today) open, blocking only the terminal-runs guide. Merged #48 into the branch first, keeping both mvp-0.0.1 §2 rows.
- 19:55 Done: APPLY6 (stages in 0.0.1, declared or detected, with the processes or rules list; Thomas, 2026-10-28). PR weber8thomas/spectio#51 squash `f8fa949`, 16 checks green on `1d47d6f`. Spike `spike/stage-detection` on nf-core/rnaseq 3.27.0 (67 → 8 stages), sarek 3.11.0 (48 → 8), methylseq 4.2.0 (13 → 4, 15 → 5) and mosaicatcher-pipeline v2.5.1 (101 rules → 8); ui-spec §5.1.1 detection rules, checking-scenarios §12.7 overlay files (assumed, inbox #68), P1 M7 Task 27, fixtures `tests/pipelines/real/stages/`. Doc review approve 11/14 (required 1–6, optional 7–9 applied); fact-check FC-311..313 applied. New blocker inbox #69, open: `-plugins nf-spectio@<ver>` replaces nf-core's pinned plugins (fails on Nextflow 26.10.4, silent drift on 25.10.9); `NXF_PLUGINS_DEFAULT` works but its list form is undocumented [to be validated].
- 20:45 Done: UILITE (0.0.1 lite boards after review). PR weber8thomas/spectio#52 squash `a384eea`, checks green on `3a7c154` (label `screenshots` added for the four deliberately refreshed lite shots; the churn guard passed on re-run). Three UX review rounds: UX-292..304, then UX-305..314 (0/4/6), then UX-315..324 (0/3/7), all applied; doc review changes 7/14, then approve 12/14, required and optional applied. Thomas, 2026-10-28: both stages and processes ("les 2 dans 0.0.1"); official Nextflow, Snakemake and nf-core logos; a light icon per section and every section collapsible, on run detail and Launch; the complete Spectio logo in the app bar on desktop and phone (first read as "favicon only", corrected). ui-spec §4.4 owns the stage presentation; P1 Tasks 17–20 serve every fact the boards show. Next: APPLY7 (Thomas, 2026-10-28: per-task logs and files from the work directory, plus resume a failed run, failure summary, open reports and results, copy the command and parameters, per-task resources, all in 0.0.1).
- 21:50 Done: APPLY7 (per-task files from the work directory, failure summary, Resume, results and reports, Copy, per-task resources, all in 0.0.1; Thomas, 2026-10-28). PR weber8thomas/spectio#53 squash `019994a`, checks green on `9274e60` (label `screenshots`: the lite launch shot was refreshed). Architecture §13.7 (job files, `.spectio/nextflow.log`, three Snakemake SLURM plugin message forms), api §5 and §5.1 (`failures[]` capped at 10, `actions.resume`, `resumed_as`), dev-env §15.3 req. 13–16, checking-scenarios §11.1 (fd walk), P1 Tasks 28–32. Six new boards (LiteTaskFilesStates, LiteRunActions, MLiteResumeSheet, MLiteRunFailed, LiteResults, LiteReportViewer), 13 changed. Doc review approve 11/14 (required 1–4, optional 5–10 applied); UX-325..335 (0/5/6) and SEC-150..159 (0/4/6) all applied ([record](docs/reviews/code/APPLY7.md)). Inbox #70 assumed (four choices; sacct frequency to check with EMBL admins).
- 22:12 Promotion to main in two slices (the docs-gate media budget is 5 MB per PR; the seven step PRs together added 5.52 MB): #55 up to `5e2493e` (4.99 MB, merge `dc521d9`), then #54 for APPLY7, its journal line and a usage snapshot (0.74 MB, merge `709904a`). All checks green on both heads, including pipelines-real and pipelines-synthetic. Dashboard republished (version 27). Open for Thomas: inbox #66 (package names, urgent), #69 (`NXF_PLUGINS_DEFAULT` at EMBL), #70 (APPLY7 choices, sacct frequency with EMBL admins), the GO for product code.

## 2026-10-29 09:00 → — tick 13 (Thomas's four questions: names, #69, #70, weekend)

- 09:51 Done: APPLY8 (inbox #69 decided by Thomas, 2026-10-29: `nf-spectio` enabled only by `NXF_PLUGINS_DEFAULT` set per run). PR weber8thomas/spectio#57 squash `376ced3`, checks green on `7cee7b9`. Fact-check FC-318..321 (Nextflow 26.10.4 and 25.10.9 read and run); spec review SR-421..428 then SR-429..431, all applied; doc review approve 11/14 then 14/14. Three answers assumed from the decision, pending Thomas (inbox #69). Upstream Nextflow issue drafted, not filed.
- 09:51 Open: NAMES, PR weber8thomas/spectio#56 (PyPI trusted-publishing workflow, three working 0.0.0 packages, claim guide; FC-314..317). Code and security approve after three rounds, doc review approve 12/14; code-owned (`.github/`, `tools/release/`), so it waits for Thomas. New inbox #71 (deny agent sessions the commands that start or approve a publish). Integration merged into its branch (`2ba664d`). Nothing published.
- 14:00 Done: NAMES. Thomas moved the repository to `spectio-org` (inbox #9, decided; `spectio` was taken), added the three PyPI pending publishers with that owner, created the `pypi-*` environments with no required reviewer ("pas grave si on publie, on fera des patchs") and protected `main` (a PR and green CI, no required approval, no force-push or deletion). Packages and docs moved to `spectio-org` in `7097f7c` (Documentation URL dropped: GitHub Pages never deployed). Thomas merged PR spectio-org/spectio#56 himself (merge `bf393e6`, head `ae0c0bd`, checks green); the guide's `main`-protection commit `f75061e` landed after his merge and is cherry-picked onto integration. Nothing published yet: the workflow reaches `main` through the next promotion PR; inbox #71 still open.
- 14:15 Thomas merged the promotion PR spectio-org/spectio#58 himself (merge `3025f03`, 14:00, before every check had finished; all green by 14:11): `pypi-publish.yml` is on `main`. He claimed `nf-spectio` on the registry (provider `spectio-org`, to confirm; pending admin review). Inbox #71 answered (a): PR spectio-org/spectio#59 adds the deny rules, code-owned, waits for Thomas. Dashboard republished (version 29). Open for Thomas: run `pypi-publish` for the three projects; merge #59; whether CI should stop running on pushes to `autopilot/integration` (duplicate runs with the promotion PR).

## 2026-10-29 22:15 → — tick 14 (/goal: P2 then P3; budget 12%w from 28%)

- 22:15 Sync: the local `autopilot/integration` had unrelated history (the repository history was rewritten upstream); kept as local branch `backup/stale-integration-20261028`, switched to `origin/autopilot/integration`. No rebase on `main` (pushed history; main is ahead only by merge commits).
- 22:16 Dashboard answers: 11 documents of 2026-10-29 copied into open entries #4, #46, #48–#51, #53–#55, #59, #64, marked *Open (needs Thomas's confirmation)* (`7ba905a`). None changes a step's status.
- 22:17 Budget: `start --weekly 12 --now 28` → room 10 pt (source manual-stale); check `go`.
- 22:42 Done: P2 (plan). One short execution guide `docs/plans/P2-execution.md` over P1 (Thomas narrowed P2 at the GO; new log entry). M1–M8 order, done proofs, review tracks under #52 (b), gaps G1–G7 (Paper boards and shell, launch engine buttons and Git source tests, local mode, happy-local check), 8 notes for P1. Inbox #72 and #73 assumed (a). Doc review approve 11/14, required changes 1–8 applied (new figure `p2_lanes`). exit_check: none (plan); docs gate 0 failures; strict build exit 0.
- Waiting on Thomas: confirmations of the 11 dashboard answers; #72, #73 (assumed). Next: P3.
- 22:50 P3 started (one P1 task per branch `autopilot/P3-<task>`, across ticks). Budget governor given a proxy (inbox #74 assumed: API-equivalent USD from token counts × 0.1 pt/USD).
- 23:00 Promotion PR spectio-org/spectio#72 (P2) merged into main, merge `8fdf5ff`, all checks green on `9e08a3e`.
- 23:45 P3 Task 1 (workspace and spool event contract): PR spectio-org/spectio#73 into integration. review-code 3 rounds: code-reviewer changes (0/2/4) → approve; security-reviewer changes (0/1/5) → approve → approve (round 3, after the doc-review fix); code-simplifier −12/+3. Doc review block 11/14 (free-form `resources`/`rulegraph` kept never-stored keys) → fixed in code (`6d50d3c`, `f456646`) → approve 11/14. 44 product tests. Record `docs/reviews/code/P3-t01.md`. The first branch commit `9fb1d97` carries attribution trailers with a model name; the squash message drops them (no force-push).
- Deferred findings, tracked here for the tasks that own them: SEC-P3T1-04 (reader: file-name grammar, `wrong_launch`, partial-line cap, file-count cap) and the fresh-environment import check → Task 3; SEC-P3T1-08 (other Snakemake error forms) and SEC-P3T1-11 (`resources` values, `slurm_extra`) → Task 5; SEC-P3T1-09 (Nextflow `errorMessage`, bridge sends it, never `errorReport`) → Task 6. FU-P3-01: `hooks/progress.py` should link `P3-M<n>` pages.
- Budget: estimate 34.4 % (start 28 %, stop 40 %, target 38 %). One P1 task costs about 5 points (Task 1 ≈ 50 USD API-equivalent), more than the 3.5 points left, so no new task is started this tick even though `check` answers go (its per-kind median is built from partial records).
- 23:46 P3 Task 1 merged into integration: PR spectio-org/spectio#73 squash `622caa0` (message: title plus `Release-As: 0.0.1`, no other trailer), every check green on `41cee3e`. The pr-body check had failed twice because the body sent through the API lost the `!` of the figure's image line; resent, then green.
- 23:50 Promotion PR spectio-org/spectio#74 (P3 Task 1) opened into main; merge once every check passes. Dashboard rebuilt from the repository, XSS check ok.
- 23:57 Promotion PR spectio-org/spectio#74 merged into main, merge `3dff1c6`, every check green on `c451d37` (product, docs-gate, pr-body, pipelines-synthetic and pipelines-real, security, preview, frontmatter). Dashboard republished (version 30).
- Tick 14 ends here: budget estimate 34.4 % of the week (stop at 40 %), 3.5 points of room, and a P1 task costs about 5. Next tick: P3 Tasks 2 and 3 (give Task 3 SEC-P3T1-04 and the fresh-environment import check), board gaps G1/G2/G3a. Waiting on Thomas: confirm the 11 dashboard answers; #72, #73, #74 (assumed).

## 2026-10-30 00:00 → — tick 15 (/goal, plain /autopilot)

- 00:00 Sync clean. Dashboard answers: 2 new documents (#52, #71), both for handled entries, ignored. Budget check `go` (fits 1; estimate 34.4 %, room 3.5 pt). P3 Task 2 (SQLite store) dispatched on `autopilot/P3-t02`, base `fbbf55d`; the budget is re-checked before review.
- 00:55 P3 Task 2 (SQLite store with one writer) merged into integration: PR spectio-org/spectio#75 squash `7d90633`, every check green on `479829f`. review-code: code changes (0/2/4) → changes (0/1/2) → approve; security changes (0/3/5) → changes (0/1/3) → changes (0/1/1) → approve; code-simplifier −16/+9; 91 tests. Four rounds broke the two-round rule of `review-code` (security majors SEC-P3T2-09 and -13 were fixed in the step); recorded in new inbox #75 (assumed (a): spec changes owed go to the next `/apply-findings`; the rounds rule left for Thomas). Doc review approve 11/14, required changes 1–4 applied (`479829f`). Record `docs/reviews/code/P3-t02.md`.
- Follow-ups: the `fs_type` docstring overstates what `stat` triggers (automount; stat(2), Linux ≥ 4.11), to fix in a later code change; plan Task 4 vs api §7 run summary names (`task_counts`), for Task 4.
- 00:58 Budget check: `stop` (estimate 37.8 %, room 0.2 pt of 12). No new step. Promotion PR spectio-org/spectio#76 (P3 Task 2) opened into main; merge once every check passes. Next tick: P3 Task 3 (spool reader; give it SEC-P3T1-04 and the fresh-environment import check), then Tasks 4–7, board gaps G1/G2/G3a. Waiting on Thomas: a `/usage` reading to recalibrate the estimate (inbox #74), the 11 dashboard answers to confirm, #72–#75.
- 01:05 Promotion PR spectio-org/spectio#76 merged into main, merge `6394a5f`, every check green on `62b94f9`. Dashboard republished (version 31). Tick 15 ends on the budget `stop`.

## 2026-10-30 — tick 16

- Thomas answered in the session: #72 (b) placeholders, reverses the shipped (a), follow-up FU-P3-02; #73 (a) confirmed; #74 `/usage` 31 %, stop at 40 %; #75 (a), rounds past two allowed while a security finding is open (skills and autopilot §5 updated). Decision log entry 2026-10-30.
- Budget restarted: `budget.py start --weekly 9 --now 31 --pct-per-usd 0.031` (98.3 USD recorded for 3 points since 28 %). Check: `go`, room 7.0.
- The repository moved to `spectio-org/spectio`; the old URL redirects, fetch and push work.
- 07:47 P3 Task 3 (spool reader) merged: PR #77, squash `51d6348`. review-code: 3 rounds (round 3 on post-approval minor fixes, inbox #76), CODE `review=approve 0/1/13 security=approve 0/2/9 simplify=changed -2/+1 tests=pass`; docs: doc-reviewer approve 13/14 after one revision. Closed SEC-P3T1-04 and SEC-P3T1-06. New inbox #76 (assumed a). Follow-ups: CR-P3T3-08; Task 9 creates `.spectio`/`events` 0700 (SEC-P3T3-09).
- 07:42 Unattended mode set up at Thomas's request (autopilot §10, decision log 2026-10-30): recommendations applied, quiet session, saved workflow `p3-task` per task, self check-ins.
- 08:01 Promotion PR #78 merged into `main` (`ebcee14`), every check passed. P3 Task 4 runs as workflow `p3-task`.
- 08:53 P3 Task 4 (projector, run state, Nextflow mapping) merged: PR #79, squash `6dc5cce` (footer `Release-As: 0.0.1`), every check green on `adfb924`. CODE `review=approve 0/5/18 security=approve 0/1/10 rounds=5 simplify=changed -13/+12 tests=pass`; doc-reviewer approve 13/14. Inbox #77 applied, #78 new (assumed a). Cost recorded 55 USD (estimate, about 1.6M subagent tokens).
- 08:55 Spike `first-look` (Thomas asked to see a prototype today): the merged code of Tasks 1–4 behind a read-only page, synthetic spools, branch `spike/first-look` (`6a33d57`), note `docs/research/2026-10-30-first-look-spike.md` on that branch. Four findings: run times use the ingest clock (inbox #79), retried failures keep no class, processes are only in the event log, attempts keep no timings or resources. Part 2 running: a real dummy Nextflow run with the T2 prototype plugin and a launch form. Inbox #80: visible slice earlier in the P1 order (assumed). Budget check `go`, estimate 34 %.
- 09:20 Spike `first-look` part 2 (`5ccd8b8`): a real Nextflow 26.10.4 run of a dummy pipeline, events through the T2 prototype plugin, launched from a local page or the shell (`spikes/first-look/run-local.sh`, `AGENT.md`). Verified: 3-sample run succeeded 10/10, injected failure blamed `ALIGN (S02)` attempt 2, 0 drops. New follow-ups on merged code: FU-P3-05 running and aborted attempts store exit 2147483647 (`trace.exit` fallback in `projector/nextflow.py`); FU-P3-06 `runs.failure.message` carries the tool's stderr (security look before any screen shows it). Thomas: UI not ready (branding), no test today; autopilot continues.
- 09:20 Promotion PR #80 merged into `main` (`38bc1cc`), every check passed (pr-body re-run after the body got its Docs, Evidence and Checks sections).
