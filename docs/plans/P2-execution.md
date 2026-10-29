# P2 · Execution guide for the P1 plan

> **For agentic workers:** this page does not repeat [P1](P1-walking-skeleton.md). It says in which order step P3 runs P1's Tasks 1–32, which run in parallel, what proves each milestone done, which review each task gets, and the few tasks P1 still lacks. Each task's files, interfaces, tests and commands are in P1.

*Written 2026-10-29 (step P2). One file instead of one plan per milestone, and no task copied from P1: Thomas's narrowing of P2 ([decision log](../decisions/log.md#2026-10-29-p2-is-a-short-execution-guide-over-p1-not-new-milestone-plans)), after the [GO of 2026-10-29](../decisions/log.md#2026-10-29-go-for-the-whole-p1-plan-with-five-changes) (whole plan M1–M8, five changes).*

Step page: [Progress · P2](../progress/W5/P2.md).

**Goal:** run P1 to its "Done when" list with the fewest blocked hours: lanes that run in parallel, the cluster-bound tasks batched, and the gaps the GO opened closed before the tasks that need them.

**Spec:** [P1](P1-walking-skeleton.md) and the specs it names per task; [dev-env §15.1 and §15.3](../specs/dev-environment-and-testing.md#151-capabilities-by-version); [autopilot §9](../playbooks/autopilot.md#9-code-review-in-the-loop); the P3 prompt in [`next-phase.md`](../playbooks/next-phase.md#p3-execution).

## 0. How P3 runs this

- **Skill.** `subagent-driven-development`, as the [P3 prompt](../playbooks/next-phase.md#p3-execution) says: one fresh implementer per task, `test-driven-development` throughout (P1's Step 1 → Step 2 FAIL → Step 3 → Step 4 PASS), `verification-before-completion` before a task is marked done, then the task's review track (§9). Sections 2 and 3 of `karpathy-guidelines` go to every task reviewer as global constraints, with P1's [Global Constraints](P1-walking-skeleton.md#global-constraints).
- **Branches.** One worktree and branch `autopilot/P3-<task>` per task (for example `autopilot/P3-t03`), or per small group named in §1–§8 (`autopilot/P3-t12-t14`); a gap task uses its id (`autopilot/P3-g6`). Each branch is based on the current `autopilot/integration` and merged into it by pull request once its checks and its review pass. Never force-push, never delete a branch, never edit a status in `pipeline.yaml` (`CLAUDE.md`).
- **Commits.** P1's commit messages; every `feat` carries `Release-As: 0.0.1` (P1 Global Constraints).
- **Docs.** Each PR leaves its docs through `write-docs`: when code contradicts a spec, the owning spec changes in the same PR with a dated log entry (P1 Process). One Progress page per milestone, not per task (P1 Process): `docs/progress/W5/P3-M<n>.md`, opened with the milestone's first PR and closed with its done proof (§1–§8, item "Done").
- **Order.** Milestones are not strict phases: a task starts when the tasks it depends on are merged. The critical path is 1 → 2 → 4 → 9 → 10 → 11 → 12 → 16 → 17 → 18 → 20 → 21 → 22 → 23.
- **Stop and inbox.** A spec ambiguity, a contradiction between P1 and a spec, or a cluster fact that P1 marks **[to be validated]** and that turns out otherwise becomes an entry in [`docs/reviews/inbox.md`](../reviews/inbox.md) with a safe default assumed and marked *(assumed — pending Thomas, inbox #N)*; the task goes on if the default is reversible. The task stops (`blocked`) only when every default would loosen a §15.3 requirement, lose data, publish something, or be hard to undo. A review fix loop that fails twice blocks the task with an inbox entry ([autopilot §9](../playbooks/autopilot.md#9-code-review-in-the-loop)). Blocked tasks do not block their independent neighbours.

### 0.1 Where each part can run

| Part | Cloud session | Needs |
|---|---|---|
| M1–M4, M6–M8 unit, API and Playwright tests; Tasks 6 and 7 with real local engine runs | yes ([dev-env §2](../specs/dev-environment-and-testing.md#2-where-agents-work): engines, the UI and Chromium work) | Java for Task 6, as in spike T2; `tmux` for Task 10's `-m tmux` tests |
| Tasks 22 and 23; the `slurm-mini` checks in Step 4 of Tasks 28–30 | **no**: cloud sessions boot with cgroup v1, so sind cannot run ([dev-env §2](../specs/dev-environment-and-testing.md#2-where-agents-work), [inbox #51](../reviews/inbox.md#51-t3-and-t4-cannot-run-in-a-claude-code-cloud-session-where-do-they-run)) | `pipelines-slurm.yml` job `e2e` on a GitHub runner, iterated by push (the route of spikes `t3-ci` and `t4-ci`), or Thomas's machine with Docker on cgroup v2 (option (a), which his 2026-10-29 answer accepts, pending his confirmation) |
| Task 24 Step 4; inbox #64 (which directory is node-local, BeeGFS locks) | no | a person on an EMBL login node; nothing in CI reaches EMBL |

The SQLite location stays P1 Assumption 21 (node-local) for Tasks 2 and 11 until Thomas confirms his dashboard answer on [inbox #64](../reviews/inbox.md#64-embl-login-nodes-is-there-a-persistent-node-local-disk-for-sqlite) (the home folder for the MVP).

The code of Tasks 22 and 23 is written in a cloud session; only their runs go to CI. Until the `e2e` job is green, M5 stays open while M6–M8 go on (none of their tasks depends on Task 22).

## 1. M1 · Events in

1. **Tasks:** [1](P1-walking-skeleton.md#task-1-workspace-and-the-spool-event-contract), [2](P1-walking-skeleton.md#task-2-sqlite-store-and-its-discipline), [3](P1-walking-skeleton.md#task-3-spool-reader-153-req-6), [4](P1-walking-skeleton.md#task-4-projector-run-state-and-nextflow-mapping), [5](P1-walking-skeleton.md#task-5-snakemake-mapping), [6](P1-walking-skeleton.md#task-6-nf-spectio-writes-the-spool), [7](P1-walking-skeleton.md#task-7-snakemake-logger-plugin-writes-the-spool).
2. **Order:** Task 1 alone first (it creates the workspace and the CI job everything else uses). Then four parallel worktrees: 2 → 4 → 5; 3; 6 (Groovy); 7. Task 4 waits for 3. Task 8 (M2) may start as soon as 2 is merged.
3. **Done:** `uv run pytest packages/spectio-sdk packages/spectio-server/tests/test_store.py packages/spectio/tests/test_spool_reader.py packages/spectio-server/tests/test_projector_nextflow.py packages/spectio-server/tests/test_projector_snakemake.py -v`, then the bridge suites with `-m engines` (Task 6 on 26.10.4 and 25.10.9; Task 7's own suite). No scenario proves M1: the files in `tests/scenarios/` describe whole runs. The stand-in is Task 5's replay of the T2 fixtures and Tasks 6 and 7's real local runs.
4. **Review:** all seven are product code; Tasks 1 and 3 (§15.3 req. 6) are security boundaries.

## 2. M2 · Heads

1. **Tasks:** [8](P1-walking-skeleton.md#task-8-spectio-init-and-spectio-doctor), [9](P1-walking-skeleton.md#task-9-head-script-local-launcher-and-the-runner-loop), [10](P1-walking-skeleton.md#task-10-tmux-launcher-on-the-login-node); gap [G6](#107-g6-local-mode-init-doctor-and-start-text).
2. **Order:** 8 after 2 (parallel with 3–7). 9 after 4, 6, 7 and 8. 10 after 9. G6's `init` and `doctor` part goes with Task 8's branch or right after it.
3. **Done:** `uv run pytest packages/spectio/tests -v` and `uv run pytest -m tmux packages/spectio/tests/test_tmux_real.py -v`. `happy-local.yaml` (Nextflow `happy`, local executor, `expect: run succeeded`) is not checked by any code yet; Task 9's local-launcher tests stand in until G7.
4. **Review:** product code. Task 9 (head script, Review Focus 1 and 4; [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) Launch) and Task 10 (tmux, adoption) are security boundaries.

## 3. M3 · Served safely

1. **Tasks:** [11](P1-walking-skeleton.md#task-11-spectio-serve-bind-153-req-1-and-boot), [12](P1-walking-skeleton.md#task-12-token-link-secrets-and-sessions-153-req-2), [13](P1-walking-skeleton.md#task-13-session-cookie-153-req-3), [14](P1-walking-skeleton.md#task-14-host-allow-list-153-req-4), [15](P1-walking-skeleton.md#task-15-file-modes-153-req-5), [16](P1-walking-skeleton.md#task-16-writes-need-origin-and-json-153-req-7); G6's start-text part.
2. **Order:** 11 after 3, 8, 9 and 10. Then 12 ∥ 14. Then 13 ∥ 15 (after 12) and 16 (after 12 and 14). Task 24 (M5) may start once 11 and 12 are merged.
3. **Done:** `uv run pytest packages/spectio-server/tests/security packages/spectio-server/tests/test_serve.py -v` all green (P1 Task 16 Step 4). No scenario.
4. **Review:** every task is a security boundary (§15.3 req. 1–5 and 7).

## 4. M4 · API and screens

1. **Tasks:** [17](P1-walking-skeleton.md#task-17-launch-api), [18](P1-walking-skeleton.md#task-18-read-api-logs-and-cancel), [19](P1-walking-skeleton.md#task-19-ui-shell-and-launch-form), [20](P1-walking-skeleton.md#task-20-runs-list-run-detail-cancel-and-the-playwright-smoke), [21](P1-walking-skeleton.md#task-21-one-wheel-with-the-ui-and-both-bridges); gaps [G1](#101-g1-paper-chrome-on-the-shared-lite-board-components), [G2](#102-g2-the-launch-boards-engine-buttons-and-path-or-git), [G3a](#103-g3a-paper-page-bodies-of-the-run-boards), [G4](#105-g4-the-paper-shell-in-web), [G5](#106-g5-tests-for-the-engine-buttons-and-the-git-source).
2. **Order:** G1 → G2 and G3a are board work and can start at once, in parallel with M1–M3. 17 after 9 and 16, with G5's API tests. Then 18 ∥ 19 (19 also after G1 and G2, with G5's UI tests). G4 after 19. 20 after 18, G3a and G4 (T6 is done). 21 after 6, 7 and 20.
3. **Done:** `uv run pytest packages/spectio-server/tests/api -v`; `npm --prefix web test`; `bash tests/e2e/serve-local.sh & npx --prefix dev/npm playwright test tests/e2e/skeleton.spec.ts` on the desktop and phone projects; `bash tests/packaging/test_wheel.sh` prints `RESULT wheel pass`. The Playwright test "link → empty list → launch happy (Nextflow, local) → detail shows Succeeded" is the stand-in for `happy-local.yaml` until G7 checks it.
4. **Review:** 17, 18, 19, 20, G4 and G5 are product code; 17 (Git fetch: argument list, protocol allow-list) is a security boundary. Task 21 is build tooling: tests and one review, but the hooks decide what the wheel ships, so `review-code` applies if in doubt. G1–G3a are board changes: rendered with `node tools/canvas/render.js`, looked at, and reviewed by `ux-reviewer`.

## 5. M5 · On the cluster

1. **Tasks:** [22](P1-walking-skeleton.md#task-22-end-to-end-on-slurm-mini-launch-and-monitor-both-engines), [23](P1-walking-skeleton.md#task-23-end-to-end-cancel-and-server-restart), [24](P1-walking-skeleton.md#task-24-laptop-access-the-ssh-config-entry-and-spectio-open); gap [G7](#108-g7-happy-local-checked-on-both-engines).
2. **Order:** 22 after 21; 23 after 22. 24 runs in parallel from M3 on (it needs only 11 and 12). G7 after 21, in parallel with 22. Runs of 22 and 23 go to CI (§0.1).
3. **Done:** `CLUSTER=mini bash tests/slurm/e2e.sh launch nextflow`, `… launch snakemake`, `… cancel nextflow`, `… cancel snakemake` and `… restart` each print `RESULT … pass`, and the `e2e` job of `pipelines-slurm.yml` is green. That job makes the `expect` lines of **`tests/scenarios/happy-slurm-mini.yaml`** checked (P1 Task 22 Files), so this scenario proves M5; `python3 -m unittest discover -s tests/scenarios -p 'test_*.py'` must stay green after that edit. `uv run pytest packages/spectio/tests/test_open.py -v`, and Task 24's manual check on an EMBL login node, recorded on the Progress page. `happy-k8s-mini.yaml` stays a description: Kubernetes is out of P1.
4. **Review:** 22, 23 and G7 are test-only (tests and one review); every fix they reveal lands in the owning task's code and gets `review-code` there (P1 Task 22 Step 3). Task 24 (ssh argument building, §15.3 req. 8) is a security boundary.

## 6. M6 · Runs from a terminal

1. **Tasks:** [25](P1-walking-skeleton.md#task-25-pointer-file-in-both-bridges-the-server-finds-and-shows-the-run), [26](P1-walking-skeleton.md#task-26-release-packages-of-both-bridges-dry-run-only).
2. **Order:** 25 after 6, 7, 9, 11, 18 and 20; 26 after 6, 7 and 21. They run in parallel. Neither waits for M5.
3. **Done:** `uv run pytest packages/spectio/tests/test_observed.py -v`, the bridge suites with `-m engines`, the Playwright smoke with its terminal run (no Cancel), and `bash tests/packaging/test_bridges_release.sh` prints `RESULT bridges-release dry-run pass`. No scenario.
4. **Review:** 25 is a security boundary (§15.3 req. 12, pointer scan). 26 is release tooling but touches the supply chain (§15.3 req. 12, Release): `review-code`.

## 7. M7 · Stages

1. **Tasks:** [27](P1-walking-skeleton.md#task-27-stages-declared-or-detected-above-the-processes-or-rules-list).
2. **Order:** after 4, 5, 18, 20 and 25; in parallel with M8's Task 28. It edits files that M8 also touches (`RunDetailPage.tsx`, the projector): merge 27 before 32.
3. **Done:** `uv run pytest packages/spectio-server/tests/test_stages.py -v` against the golden output of the four example pipelines, and the Playwright checks of P1 Task 27 Step 4. No scenario.
4. **Review:** product code (`review-code`); the `spectio.yml` overlay read is untrusted input.

## 8. M8 · Job files and run tools

1. **Tasks:** [28](P1-walking-skeleton.md#task-28-each-jobs-files-and-the-work-directory), [29](P1-walking-skeleton.md#task-29-failure-summary-and-resources-per-job), [30](P1-walking-skeleton.md#task-30-resume-copy-to-a-new-launch-and-the-copy-actions), [31](P1-walking-skeleton.md#task-31-results-and-reports), [32](P1-walking-skeleton.md#task-32-the-screens-job-files-failure-summary-results-resume-copy-and-resources); gap [G3b](#104-g3b-paper-page-bodies-of-the-run-tool-boards).
2. **Order:** 28 after 4–7, 9 and 18. Then 29 ∥ 30 ∥ 31. 32 after 20, 28–31, 27 and G3b. Each task's unit part merges without the cluster; the `slurm-mini` lines of Step 4 in Tasks 28–30 run once Task 22's `e2e` job exists, batched in one CI iteration (§0.1, and Notes for P1 item 1).
3. **Done:** the Step 2 commands of Tasks 28–31 PASS; `npm --prefix web test` and the Playwright smoke PASS with Task 32; the cluster checks of 28–30 in the `e2e` job. No scenario.
4. **Review:** 28 (confinement, req. 13), 29 (req. 15), 30 (req. 7 and 16) and 31 (report sandbox, req. 13 and 14) are security boundaries; 32 is product code. G3b is a board change (`ux-reviewer`).

## 9. Review tracks

Per [inbox #52 option (b)](../reviews/inbox.md#52-code-first-start-the-walking-skeleton-before-t5-t6-r10-and-p1-critical-not-assumed), decided in the GO entry:

| Track | Tasks |
|---|---|
| `review-code` (code-reviewer and security-reviewer in parallel, then code-simplifier) | 1–20, 24–32, G4, G5, G6 |
| tests and one review | 21, 22, 23, G7 |
| render, look, `ux-reviewer` | G1, G2, G3a, G3b |

`CLAUDE.md` (Coding behaviour) still asks `review-code` for every code change, and Thomas has not edited it yet ([autopilot §9](../playbooks/autopilot.md#9-code-review-in-the-loop), note 2026-10-29). Until he does, the stricter rule wins whenever a task's track is in doubt. The whole branch also gets one `review-code` pass before P3 ends (P3 prompt).

## 10. Gaps: tasks P1 does not carry

The GO's five changes, checked against P1: change 1 (EMBL login nodes) needs no task; change 2 (process) is §9. Changes 3, 4 and 5 are in P1's Assumptions 2, 23 and 24 and in some interfaces, but no task builds or tests the parts below. Each stub is at most half a day.

### 10.1 G1 · Paper chrome on the shared lite-board components

**Spec:** [ui-spec §7](../specs/ui-spec.md#7-consistency-with-depictio-reuse-plan) (Paper shell, note 2026-10-29), P1 Assumption 24 · **Before:** Task 19. Restyle `LiteSidebar`, `LiteTopbar`, `MLiteTopbar` and `MLiteTabbar` in `design/ui-canvas/` to the Paper shell: floating top bar with breadcrumbs and the theme toggle, foldable sidebar with the "Workspace" eyebrow and server status in its foot, bottom tab bar on phones. Search (⌘K), notifications and the avatar are left out: 0.0.1 has no users and no search *(assumed — pending Thomas, inbox [#72](../reviews/inbox.md#72-assumed-the-paper-shell-in-001-leaves-out-search-notifications-and-the-avatar))*. Thirty of the 34 lite boards import these four, so the chrome changes everywhere at once. **Test:** every `Lite*` and `MLite*` board renders with `render.js` and is looked at; the keyboard rules of `CLAUDE.md` hold; `ux-reviewer` approves.

### 10.2 G2 · The launch boards: engine buttons and path-or-Git

**Spec:** [ui-spec §4.6](../specs/ui-spec.md#46-launch-and-relaunch), P1 Assumption 2, [mvp-0.0.1 §2](../specs/mvp-0.0.1.md#2-features-and-where-they-are-specified) (note 2026-10-29) · **After:** G1 · **Before:** Task 19. `LiteLaunch`, `LiteLaunchSnakemake` and `MLiteLaunch` show the two engine buttons (`<button aria-pressed>`, one pre-selected, with "Guessed from main.nf" beside it), and a Pipeline field that takes a path, or a repository and a revision. Their states: no guess (both or neither file), a refused URL (`file://`). **Test:** rendered and looked at; `ux-reviewer` approves; Task 19 then names these boards in place of `Launch` and `LaunchSnakemake`.

### 10.3 G3a · Paper page bodies of the run boards

**Spec:** ui-spec §7 (page head: tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right) · **After:** G1 · **Before:** Task 20. `LiteHome`, `LiteRuns`, `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, `LiteStates`, `LiteStatesRun`, `LiteCancelDialog` and their phone twins. **Test:** rendered, looked at, `ux-reviewer`.

### 10.4 G3b · Paper page bodies of the run-tool boards

Same rule as G3a · **Before:** Task 32. `LiteRunTasks`, `LiteTaskFiles`, `LiteTaskFilesStates`, `LiteRunLogs`, `LiteRunFailed`, `LiteRunActions`, `LiteResults`, `LiteReportViewer`, `LiteLegend` and their phone twins (`MLiteResumeSheet`, `MLiteTaskFilesSheet`…). **Test:** as G3a.

### 10.5 G4 · The Paper shell in `web/`

**Spec:** ui-spec §7, [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout) (Mantine 7), P1 Assumption 24 · **After:** Task 19, G1 · **Before:** Task 20. Rewrite the Paper shell as Spectio code (no import from depictio): `web/src/shell/{AppShell.tsx,TopBar.tsx,Sidebar.tsx,TabBar.tsx,theme.ts}`, Spectio's palette in `theme.ts` tokens, light and dark. **Test:** Vitest with Testing Library, `web/src/shell/shell.test.tsx`: `test("theme toggle is a button and switches the scheme")`, `test("sidebar folds with a button[aria-expanded]")`, `test("below 768 px the tab bar replaces the sidebar")`, `test("breadcrumbs follow the route")`; then `npm --prefix web run build`, and a Playwright screenshot compared by eye with the G1 boards.

### 10.6 G5 · Tests for the engine buttons and the Git source

**Spec:** P1 Assumption 2, [api §5](../specs/api-and-data-model.md#imports-are-untrusted-input) (imports are untrusted input) · Folded into Tasks 17 and 19, not a branch of its own. Task 17 adds `test_git_url_refused_schemes` (`file://`, `ext::`, `git://` and a bare local path given as a URL → 422, field `workflow.location`; the clone argv carries the three `-c protocol…` flags), `test_git_revision_not_an_option` (a revision starting with `-`, such as `--upload-pack=x` → 422, field `workflow.revision`), and `test_git_short_name` (`nf-core/rnaseq` → `https://github.com/nf-core/rnaseq`; the test fakes `git` and fetches nothing). Task 19 adds `guessEngine(files: string[]) -> "nextflow" | "snakemake" | null` in `web/src/launch/guessEngine.ts` with `test("main.nf → nextflow; Snakefile or workflow/Snakefile → snakemake; both or neither → null")`, and a component test: both buttons are native `<button>`s, the guessed one is pressed, a click changes it.

### 10.7 G6 · Local mode: init, doctor and start text

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Local mode), P1 Assumption 23 · **With:** Task 8 (first three tests), Task 11 (last two). **Test:** `test_init_local_environment` (`--local` → environment kind `local`, no `[slurm]` options written, `GET /version` later says executor `local`); `test_doctor_local_skips_sbatch` (no `sbatch` on PATH → no `fail` in local mode, still `fail` on a SLURM environment); `test_init_local_refused_off_linux` (`sys.platform` `darwin` → exit 2, "Local mode needs Linux in 0.0.1"; *assumed — pending Thomas, inbox [#73](../reviews/inbox.md#73-assumed-spectio-init-local-refuses-to-run-off-linux)*: refuse rather than warn); `test_serve_local_start_text` (local mode → the link and "Open this link in a browser on this machine", no `ssh -N -L` line); `test_serve_local_same_requirements` (local mode still binds 127.0.0.1 only and needs the ticket).

### 10.8 G7 · `happy-local` checked on both engines

**Spec:** P1 Done when (Local mode), [dev-env §5](../specs/dev-environment-and-testing.md#5-isolated-parallel-scenarios) · **After:** Task 21 · Test-only. `tests/local/e2e.sh launch nextflow|snakemake` installs the wheel, runs `spectio init --local` and `spectio serve --detach` in a temporary home, launches the synthetic `happy` through the HTTP API, and compares the counts per process with `tests/pipelines/synthetic/golden/`. It uses Task 22's client `tests/slurm/e2e_client.py`; if G7 runs first, it creates that client at that path and Task 22 consumes it (one owner). It prints `RESULT e2e-local-<engine> pass`, runs in the `e2e-local` CI job of Task 20, and makes the `expect` line of `tests/scenarios/happy-local.yaml` checked; a Snakemake twin `happy-local-snakemake.yaml` is added, and `python3 -m unittest discover -s tests/scenarios -p 'test_*.py'` stays green.

## 11. Notes for P1

P1 is not edited here; these go to the next apply pass.

1. **Cluster checks without a dependency.** Step 4 of Tasks 28, 29 and 30 runs on `slurm-mini`, but none of them lists Task 22 in "Depends on". P2 batches them after Task 22 (§8). Also, Task 29 calls `sacct` and injects an out-of-memory task on `slurm-mini`, but `slurm-mini` has no accounting; `slurmdbd` and `ConstrainRAMSpace=yes` are in `slurm-site` ([dev-env §4.1](../specs/dev-environment-and-testing.md#41-slurm-with-sind)). Task 29's cluster check probably belongs on `slurm-site` **[to be validated]**.
2. **"Done when", first line,** asks a `review-code` pass for every task; P1's own Process line and inbox #52 (b) ask it for product code only. The stricter line holds until Thomas edits `CLAUDE.md` (§9).
3. **Assumption 24** says the lite boards are restyled before Task 19, but no task does it, and Task 19 does not name the Paper shell: G1–G4.
4. **Task 8**'s `doctor` checks `sbatch` (a `fail` line when it is missing), and **Task 11**'s start text always prints the `ssh -N -L` line; both are wrong in local mode (Assumption 23): G6.
5. **Task 17**'s only Git test allows the `file` transport; nothing tests the refusal of other schemes or a revision that starts with `-`: G5.
6. **Task 19**'s boards are `Launch` and `LaunchSnakemake` (reference only); after G2, `LiteLaunch` is the reference.
7. **`happy-local.yaml`** is never made checked by a P1 task, though "Done when" asks for local mode on both engines: G7.
8. **The figure** at the top of P1 and the counts on [Progress · P1](../progress/W4/P1.md) still show M1–M5 and 24 tasks; P1 already notes it.
