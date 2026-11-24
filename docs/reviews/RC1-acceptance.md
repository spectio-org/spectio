# RC1 acceptance: the test matrix for Spectio 0.0.1-rc1 (2026-11-23)

The acceptance matrix for the tag `v0.0.1-rc1`. One row per testable case of every surface listed under [Built for 0.0.1](../roadmap/index.md#built-for-001), plus packaging. The features and their owning specs are in [MVP 0.0.1 §2](../specs/mvp-0.0.1.md#2-features-and-where-they-are-specified). This page does not restate them: each section links to the spec that owns its surface ([documentation map](../map.md)).

**Written against** `autopilot/integration` at `4124268d` (2026-11-23), after PR #164 (SLURM launch end to end) and PR #313 (SLURM cancel and restart) were merged. This branch was cut from `cee95571`, two commits earlier. Those two PRs changed only `tests/slurm/`, `tests/scenarios/happy-slurm-mini.yaml`, `dev/slurm/cluster.sh`, `pipelines-slurm.yml` and docs. So the product code (`packages/`, `engine-bridges/`, `web/`) is the same at `cee95571` and at `4124268d`.

## 1. How to read the matrix

- **One row, one cell.** Each row is one case of one surface. **N** marks the nominal case, **E** an edge case or an error. A row has one test mode, and its status holds for that mode only.
- **Test modes.**
    - **unit:** pytest in CI job `product` (`uv run --locked pytest`, without the `engines` marker); Vitest in job `web` (`npm test` in `web/`); `unittest` in job `unit`. Tests marked `engines` and the Snakemake logger plugin's own suite run in `pipelines-synthetic.yml`.
    - **Playwright:** `tests/e2e/*.spec.ts` against a real `spectio serve` in local mode (`tests/e2e/serve-local.sh`). CI job `e2e-local` of `ci.yml` runs **only** `skeleton.spec.ts` and `report.spec.ts`, on projects `desktop` and `phone`, with Nextflow and the seeded run. `e2e.yml` runs every spec against the static stand-in, where each spec that needs a server is skipped. So `preview.spec.ts`, `viewer.spec.ts`, `environments.spec.ts`, `catalog.spec.ts` and `launch-environment.spec.ts` are **not run by CI**. PR #314, still open, makes `e2e-local` run every spec in `tests/e2e`: until it is merged, the PASS (CI) of a spec outside `skeleton.spec.ts` and `report.spec.ts` rests on that PR's CI run (below), not on a CI run of integration, and must be re-checked on the tag commit once #314 is in.
    - **slurm-mini:** `tests/slurm/e2e.sh` on sind's slurm-mini profile (no `slurmdbd`, so no accounting), CI job `e2e` of `pipelines-slurm.yml`. Its cases are `install`, `launch <engine>`, `cancel <engine>` and `restart`, each checked by `tests/slurm/e2e_client.py`.
    - **login1:** the EMBL login node, a check run by hand or over ssh, following [§17](#17-login1-checklist).
- **Path short forms** in the coverage column: `srv/` is `packages/spectio-server/tests/`, `cli/` is `packages/spectio/tests/`, `sdk/` is `packages/spectio-sdk/tests/`, `smk/` is `engine-bridges/snakemake-logger-plugin-spectio/tests/`, `web/` is `web/src/` (Vitest). A Playwright test is named as `file.spec.ts` › `test title`. "(mocks)" marks a Playwright test whose API answers are route mocks, not a real run.
- **GAP** in the coverage column: no existing test covers the cell. Each GAP has a proposed test in [§18](#18-gaps-to-fill).
- **Statuses.**
    - **UNTESTED:** the starting status of every cell. A plain UNTESTED means "to be run before the tag".
    - **UNTESTED: *reason*:** deliberately not tested for rc1, with the reason. This only counts once Thomas accepts the reason.
    - **PASS (CI):** the test exists, CI ran it on the code of integration, and it passed. The evidence is below. No other PASS is written on this page until someone runs the check.
    - **PASS (*mode*, *date*, *who*)** or **FAIL (*date*, *what*)**: written when a cell is run by hand.
- **CI evidence for PASS (CI).**
    - **unit and Playwright:** run [45255488434](https://github.com/spectio-org/spectio/actions/runs/45255488434), the last CI run of PR #164 (`dc9f98d5`, merged as `f28d3106`, with the same product code as `4124268d`):
        - `product`: 1848 passed, 10 skipped, 36 deselected, then `RESULT wheel pass`;
        - `web`: 75 files, 1004 tests passed;
        - `unit`: 50 tests OK;
        - `e2e-local`: 56 passed and 6 skipped, the three `test.fixme` tests of `skeleton.spec.ts` on two projects.

        The log does not name pytest's 10 skips, so no cell here rests on a test that may skip on a CI runner: tests that need root, the real Slurm of `test_sacct_native.py`, or bioflow.
    - **Tests marked `engines` and the logger plugin's suite:** `pipelines-synthetic` in run [44202866463](https://github.com/spectio-org/spectio/actions/runs/44202866463), the push to `main` of commit `24e9d4eb`. Nothing under `packages/`, `engine-bridges/` or `tests/pipelines/` changed between that commit and `4124268d`.
    - **slurm-mini, second run:** run [45283394396](https://github.com/spectio-org/spectio/actions/runs/45283394396), the push of `7fa8dfb0` to integration, job `e2e` of `pipelines-slurm.yml`. Every case printed `RESULT … pass`: launch nextflow, launch snakemake, cancel nextflow, cancel snakemake and restart. The launch snakemake case runs without the harness's `--slurm-status-command` (the product's FU-P3-106b sets it), so it covers E-08. The new `cancel-pending` case of `tests/slurm/e2e.sh` is not in the CI matrix yet (adding it needs a workflow change), so X-12 stays UNTESTED.
    - **Playwright, every spec:** run [45284629061](https://github.com/spectio-org/spectio/actions/runs/45284629061), the `e2e-local` job of PR #314's `ci.yml`: every spec in `tests/e2e` on projects `desktop` and `phone`, with Nextflow and Snakemake — 107 passed, 0 failed, 3 skipped (the three `test.fixme` of `skeleton.spec.ts`). Every Playwright row whose test exists in `tests/e2e` is PASS (CI) with this run. An earlier `e2e-local` run of PR #314 showed, on the phone project, "the run's launch directory is gone" on a live queued run; fixed by PR #335: the server answers 404 for a run not launched yet.
    - **slurm-mini:** run [45258055502](https://github.com/spectio-org/spectio/actions/runs/45258055502), the push of `4124268d` to integration, job `e2e`. Each case printed its `ok` lines and `RESULT … pass`: `e2e-launch-nextflow` (118 s), `e2e-launch-snakemake` (305 s), `e2e-cancel-nextflow` (271 s), `e2e-cancel-snakemake` (13 s) and `e2e-restart` (119 s), every check including "socket only, no TCP port". The run before it, [45256457430](https://github.com/spectio-org/spectio/actions/runs/45256457430) on `f28d3106`, failed in "Bootstrap" before any test ran: the `node+playwright` step of `dev/bootstrap.sh` could not install three font packages. The next run's bootstrap passed with no change, so that failure was in the runner's package sources, not in Spectio. Watch for it on the tag commit.
- **The tag rule.** `v0.0.1-rc1` is tagged only when every cell is PASS, or UNTESTED with a reason Thomas accepted. **A tag waits on every FAIL**, and on every plain UNTESTED. A PASS (CI) holds for the commit it names: before tagging, re-check every PASS (CI) row on the tag commit, and re-run the matrix if product code changed after `4124268d`.

## 2. Engines and where runs go

Owners: [MVP 0.0.1 §2](../specs/mvp-0.0.1.md#2-features-and-where-they-are-specified) (engines), [schedulers §3.1.1](../specs/schedulers-and-monitoring.md#311-local-launcher-detach-adopt-exit) (heads on the login node or this machine), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (0.0.1 on a cluster).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| E-01 | N | Nextflow on one host: launch the synthetic `happy` from the UI, local executor; the detail shows Succeeded and 65 tasks | Playwright | `skeleton.spec.ts` › `link → empty list → launch happy (Nextflow, local) → detail shows Succeeded and 65 tasks` (desktop and phone); also `tests/local/e2e.sh launch nextflow`, which CI does not run | PASS (CI) |
| E-02 | N | Snakemake on one host: launch `happy` from the UI; Succeeded, counts equal to the golden | Playwright | GAP. Only `tests/local/e2e.sh launch snakemake` comes close (API client, not run by CI) | PASS (CI) |
| E-03 | N | Nextflow events into runs, tasks and attempts (spool, projector, resume) | unit | `srv/test_projector_nextflow.py::test_flaky`, `::test_resume`; `cli/test_bridge_nextflow.py::test_happy_local_spool_validates` (engines) | PASS (CI) |
| E-04 | N | Snakemake events into runs, tasks and attempts (logger plugin, projector, checkpoint) | unit | `srv/test_projector_snakemake.py::test_checkpoint_flaky_retry`; `smk/test_plugin.py::test_happy_local_spool_validates`, `::test_interface_suite` | PASS (CI) |
| E-05 | N | Nextflow on SLURM: Spectio installed from its wheel, served on the socket, `happy -profile test,slurm`; head in tmux and no head job, counts equal to the golden, `head.exit` 0, no spool drop, no job or session left | slurm-mini | `tests/slurm/e2e.sh launch nextflow` with `tests/scenarios/happy-slurm-mini.yaml` | PASS (CI) |
| E-06 | N | Snakemake on SLURM: the same checks, workflow profile `slurm` | slurm-mini | `tests/slurm/e2e.sh launch snakemake`. The harness adds `--slurm-status-command squeue` (`tests/slurm/test_e2e_sh.py::test_the_snakemake_head_queries_squeue`); the product does not | PASS (CI) |
| E-07 | N | One run per engine on the EMBL cluster, launched from the UI | login1 | [§17](#17-login1-checklist), item 8 | PASS (login1, 2026-11-24, Snakemake 9.27.1 + plugin 2.8.0): Nextflow golden counts, head in tmux, no spool drop, no job left; Snakemake golden counts, no spool drop; cancel of one run per engine pass (cancelling → cancelled in 108 s, no job left). The EMBL module's Snakemake 9.23.1 ships snakemake-executor-plugin-slurm 2.6.1, which never logs `job_info`, so no task was seen: a site requirement ([roadmap](../roadmap/index.md#001-rc1-the-release-candidate)). Resume of a failed run: not done |
| E-08 | E | A SLURM site without accounting ([inbox #156](inbox.md#156-assumed-a-slurm-site-without-accounting-and-a-run-whose-jobs-left-the-queue-task-22-2026-11-18)): a Snakemake run launched by the product, without the harness's flag. Today it hangs once its jobs leave `squeue` (FU-P3-106b) | slurm-mini | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| E-09 | E | Stall check (FU-P3-126): a task held `running` whose job is in neither `squeue` nor `sacct` gets a warning on the run and in `spectio doctor` | slurm-mini | GAP | UNTESTED: no harness case yet (the check is built, PR #325, and covered by unit tests; slurm-mini and login1 not run) |
| E-10 | E | A site without `sacct` or with accounting off: the failure summary and efficiency say so, and nothing waits on `sacct` | unit | `srv/api/test_failure.py::test_smk_message_no_sacct`, `::test_sacct_refused_tool_gives_up_at_once`; `srv/test_efficiency.py::test_eff_unavailable`, `::test_eff_unavailable_site_limit`; `cli/test_sacct.py::test_init_warns_without_sacct` | PASS (CI) |
| E-11 | E | The accounting state of the EMBL cluster, checked by hand (`scontrol show config`, `sacct -j`) | login1 | [§17](#17-login1-checklist), items 6 and 7 | Item 6 PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): `AccountingStorageType = accounting_storage/slurmdbd`. Item 7: `sacct -j` answers COMPLETED with elapsed times for the task jobs; the compare with the efficiency sheet was not done: UNTESTED: compare not done |

## 3. Serving: one host, Unix socket, restarts

Owners: [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (req. 1, the socket on a shared host), [CLI §2](../specs/cli-and-shared-libraries.md#2-the-spectio-command-tree), the guide [Opening Spectio from your laptop](../usage/open-from-your-laptop.md).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| S-01 | N | One Linux machine in local mode: TCP on 127.0.0.1 only, no `--host` flag | unit | `srv/security/test_unix_socket.py::test_lone_machine_in_local_mode_keeps_tcp`; `srv/security/test_req1_bind.py::test_req1_binds_loopback_only`, `::test_req1_has_no_host_flag` | PASS (CI) |
| S-02 | N | On SLURM, the server listens only on `spectio.sock` in its 0700 database directory, and the API and screens are served behind it | unit | `srv/security/test_unix_socket.py::test_slurm_listens_on_a_socket_in_the_db_dir_only`, `::test_the_api_and_screens_are_served_behind_the_socket` | PASS (CI) |
| S-03 | N | A shared host in local mode goes behind a socket too; a shared host is detected (`slurm.conf`, `sinfo`, other users' processes) | unit | `srv/security/test_unix_socket.py::test_shared_host_in_local_mode_goes_behind_a_socket`, `::test_tcp_never_mounts_the_api_on_a_shared_host`; `srv/security/test_shared_host.py::test_sinfo_on_path`, `::test_process_of_another_user` | PASS (CI) |
| S-04 | N | The socket on a SLURM login node, used by a client over HTTP, with no TCP listener | slurm-mini | `tests/slurm/e2e.sh launch nextflow`, `cancel <engine>` and `restart`: check "socket only, no TCP port" of `tests/slurm/e2e_client.py` | PASS (CI) |
| S-05 | E | A stale socket is replaced; a live one, a non-socket, a path too long for `AF_UNIX` and a squatted default database directory are refused | unit | `srv/security/test_unix_socket.py::test_stale_socket_replaced`, `::test_live_socket_refused`, `::test_not_a_socket_refused`, `::test_path_too_long_for_af_unix_refused`, `::test_squatted_default_db_dir_refused_behind_a_socket` | PASS (CI) |
| S-06 | E | Server restart mid-run: the heads outlive the server and are adopted; missing runs are reconciled from their directories; a rebuilt queued run is never launched | unit | `cli/test_local_launcher.py::test_adopt_after_restart`, `::test_adopt_head_gone_without_exit_file`; `cli/test_tmux_launcher.py::test_adopt_by_session_and_pid`; `srv/test_serve.py::test_boot_reconciles_missing_runs`, `::test_rebuilt_queued_run_is_never_launched` | PASS (CI) |
| S-07 | E | Server restart mid-run on SLURM: the server killed with SIGKILL and started again; the head is adopted, not started again; no duplicate event; the old cookie refused and a new link works; the run ends Succeeded | slurm-mini | `tests/slurm/e2e.sh restart` (`RESTART_CHECKS` of `tests/slurm/e2e_client.py`) | PASS (CI) |
| S-08 | E | Server restart mid-run, seen in the browser: the page reconnects and the run reaches its end without a reload | Playwright | GAP | UNTESTED |
| S-09 | E | Stop and restart: SIGTERM stops cleanly, the socket is removed, `--detach` after an unclean stop starts a new server | unit | `srv/test_serve.py::test_sigterm_stops_cleanly`; `srv/security/test_unix_socket.py::test_socket_removed_at_stop`; `srv/test_detach.py::test_detach_after_unclean_stop_on_a_socket_starts_a_server` | PASS (CI) |
| S-10 | N | Socket serving on the EMBL login node, opened from a laptop | login1 | [§17](#17-login1-checklist), items 2 and 3 | Item 3 PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): after a harness fix for EL8 (`pidfd_open` missing on kernel 4.18: it came with Linux 5.3, [pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html); PR #334) the head was adopted, golden counts, no duplicate event, no spool drop, the old cookie refused and a new link works. Item 2: the UI was driven by Playwright through an ssh tunnel to the socket — the sign-in link worked, every page answered with no API error ≥ 400, no TCP listener; Thomas's own browser and `spectio open` remain: UNTESTED: needs Thomas's laptop for `spectio open` |

## 4. Runs list

Owners: [ui-spec §4.3](../specs/ui-spec.md#43-runs-table-and-rows), [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| L-01 | N | The empty list, then the launched run; Home's count cards and lists | Playwright | `skeleton.spec.ts` › `link → empty list → launch happy (Nextflow, local) → detail shows Succeeded and 65 tasks`, `home at / shows the count cards, the active runs and the runs that ended` | PASS (CI) |
| L-02 | N | Filters, Load more, sort, the URL as the source of the filter | unit | `web/runs/RunsPage.test.tsx` › `state filters are pressed buttons and the name filter asks for a prefix`, `Load more asks for the next page and appends it`, `FU-P3-115b: a header sorts on the server, lives in the URL, and the footer says the order`; `srv/api/test_read.py::test_runs_paging`, `::test_runs_filter_state_and_q` | PASS (CI) |
| L-03 | E | Live updates; the stream cut shows "Reconnecting…" (component) | unit | `web/runs/RunsPage.test.tsx` › `a stream frame refetches the list; a lost stream reads Reconnecting…` | PASS (CI) |
| L-04 | E | SSE cut and reconnect in a real browser: the stream is dropped, the list says so, comes back and catches up on the runs that changed | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| L-05 | E | The runs root was changed (FU-P3-84): runs indexed under the old root are not shown as runs of the new one | unit | GAP: FU-P3-84 is not built ([inbox #125](inbox.md#125-question-login1-checks-for-the-runs-launch-directory-is-gone-fu-p3-81)) | UNTESTED |
| L-06 | E | Two browser tabs: a run deleted or cancelled in one tab leaves or changes in the other on the next frame | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| L-07 | E | Phone layout: one card per run, select and pin on each card | Playwright | `skeleton.spec.ts` › `FU-P3-115b: an ended run is selected in the list and deleted, and leaves the API` (project phone); `web/phone.test.tsx` › `UX-PAR-10: the runs list is one card per run, not a table` | PASS (CI) |
| L-08 | E | Pinned runs first, across pages | unit | `srv/api/test_runs_manage.py::test_sort_pinned_first_with_paging`; `web/runs/RunsPage.test.tsx` › `UX-P3FU115B-09: with a pinned run shown, the footer says pinned first, then the order` | PASS (CI) |

## 5. Run detail

Owners: [ui-spec §4.4](../specs/ui-spec.md#44-run-detail), [api §5.3](../specs/api-and-data-model.md#53-run-files-explorer-and-preview), [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine) (log sources), [schedulers §3.6](../specs/schedulers-and-monitoring.md#36-efficiency-per-job-and-per-process-or-rule) (efficiency).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| D-01 | N | Stages: a seeded nf-core/rnaseq run shows 8 detected stages above its processes | Playwright | `skeleton.spec.ts` › `a seeded rnaseq run shows 8 detected stages above its processes (P1 Task 27)` | PASS (CI) |
| D-02 | N | No stage: the flat processes list | Playwright | `skeleton.spec.ts` › `a run of the synthetic happy shows no stage, only its processes (P1 Task 27)`, `the detail shows the flat list with no stage, and the stages when /stages has items` | PASS (CI) |
| D-03 | E | Declared stages beat detected ones; two overlays matching falls back with a note | unit | `srv/api/test_stages.py::test_declared_beats_detected`, `::test_overlay_overlap_falls_back`, `::test_stages_note_when_two_overlays_match` | PASS (CI) |
| D-04 | N | Tasks update without a reload as they finish | Playwright | `skeleton.spec.ts` › `the detail updates without a reload as tasks finish` | PASS (CI) |
| D-05 | E | Snakemake states: waiting for a checkpoint, nothing to run, "at least n jobs" | unit | `srv/test_process_status.py::test_status_awaiting_checkpoint`, `::test_status_nothing_to_be_done`; `web/runs/RunDetailPage.test.tsx` › `a rule waiting for a checkpoint reads 'Waiting for checkpoint <rule>', not Pending` | PASS (CI) |
| D-06 | N | Logs: the engine log and the head log, tail and sources | unit | `srv/api/test_read.py::test_logs_tail_and_sources`, `::test_detail_head_logs`; `web/runs/RunDetailPage.test.tsx` › `UX-PAR-27: the Logs tab opens on the engine log, with Reload and Download` | PASS (CI) |
| D-07 | N | Logs of a real run in the browser (Logs tab, engine log, Download) | Playwright | GAP: the skeleton tests that open logs use mocks | PASS (CI) |
| D-08 | E | The launch directory is gone (#125): the API answers `409 run-dir-unreachable` naming the directory, not `410` | unit | `srv/api/test_read.py::test_logs_gone_only_when_the_runs_root_is_there`, `::test_logs_runs_root_through_a_symlink`; `srv/api/test_taskfiles_api.py::test_runs_root_missing_409`, `::test_other_runs_root_409`, `::test_nf_other_runs_root_409`; `srv/api/test_workdir.py::test_workdir_runs_root_unreachable_409` | PASS (CI) |
| D-09 | E | The launch directory is gone (#125), in the UI: the Logs tab and the job files say which directory could not be reached | unit | GAP: no web test, and no web code, reads `run-dir-unreachable` | UNTESTED |
| D-10 | E | The launch directory is gone (#125), on the real cluster: the six checks of the inbox item | login1 | [§17](#17-login1-checklist), item 5 | PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): no 410 on the logs of the runs; the runs root and the run directories exist and are seen the same from the serve process (same mount namespace). An earlier `e2e-local` run of PR #314 showed, on the phone project, "the run's launch directory is gone" on a live queued run: fixed in #335 (the server answers 404 for a run not launched yet) |
| D-11 | E | A head with no `head.err` (FU-P3-124): the failed run's aside tails the engine log and never asks for `head-err` | unit | `web/runs/RunDetailPage.test.tsx` › `FU-P3-124: a head with no head.err: the failed run's aside tails the engine log, and head-err is never asked for` | PASS (CI) |
| D-12 | N | Job files: the drawer opens on `.command.log` of a failed attempt | Playwright | `skeleton.spec.ts` › `Files opens the drawer on .command.log for a failed attempt; Escape returns focus to the row's button` (mocks; desktop and phone); `srv/api/test_taskfiles_api.py::test_files_listed` | PASS (CI) |
| D-13 | N | Results browser: one folder; an HTML file in the viewer, another file in its preview | Playwright | `skeleton.spec.ts` › `the results browser shows one folder; an HTML file opens in the viewer, another opens its preview` | PASS (CI) |
| D-14 | E | A cleaned work directory (`410`), a file not written yet, a binary file (`415`) | unit | `srv/api/test_taskfiles_api.py::test_cleaned_workdir_410`, `::test_not_written_yet`, `::test_binary_415`; `web/runs/TaskFiles.test.tsx` › `a read refused: 415 not text, 410 gone, 503 offline with Retry` | PASS (CI) |
| D-15 | N | Efficiency: the SLURM request, custom sbatch options, efficiency from `sacct`; the waste line per process | Playwright | `skeleton.spec.ts` › `the job sheet shows the SLURM request, 'Custom sbatch options set' and efficiency from sacct`, `By process is a tab button; the waste line names the process` (mocks); `srv/test_efficiency.py::test_eff_sacct_row`, `::test_aggregate` | PASS (CI) |
| D-16 | E | `sacct` has not measured an ended run's jobs yet (FU-P3-119): read again, within a bound | unit | `web/runs/RunDetailPage.test.tsx` › `FU-P3-119: an ended run whose jobs sacct has not measured yet is read again, until they are`; `web/runs/accounting.test.ts` › `an ended run with jobs not measured yet is read again, at most ACCOUNTING_READS times` | PASS (CI) |
| D-17 | E | Efficiency read from the real `sacct` of the EMBL cluster matches `sacct -j` | login1 | [§17](#17-login1-checklist), item 7 (slurm-mini has no accounting) | `sacct -j` answers COMPLETED with elapsed times for the task jobs (login1, 2026-11-23/24); the compare with the efficiency sheet was not done: UNTESTED: compare not done |
| D-18 | N | Why it failed: SLURM state, requested and used memory, last lines | Playwright | `skeleton.spec.ts` › `failed run: Why it failed shows SLURM state, requested and used memory, last lines` (mocks); `srv/api/test_failure.py::test_nf_failure_summary` | PASS (CI) |
| D-19 | E | Phone layout of the run detail | Playwright | `skeleton.spec.ts` › `the detail shows the flat list with no stage, and the stages when /stages has items` (project phone); `web/phone.test.tsx` › `UX-PAR-08: a run's title is the top bar's h1, with its state line and a 44 px way back to Runs` | PASS (CI) |
| D-20 | E | SSE cut and reconnect on an open run detail | Playwright | GAP (same scenario as L-04, on the detail) | PASS (CI) |

## 6. Launch form

Owners: [ui-spec §4.6](../specs/ui-spec.md#46-launch-and-relaunch), [api §5.2](../specs/api-and-data-model.md#52-launch-body) and [§5.7](../specs/api-and-data-model.md#57-run-resources-and-an-extra-config-file-001).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| F-01 | N | Schema-built form: each row says required or optional, a wrong value shows its error on the field | Playwright | `skeleton.spec.ts` › `Launch: a wrong value shows its error on the field; each row says required or optional` (desktop and phone) | PASS (CI) |
| F-02 | N | Load, the engine guess, then Launch waits for the required field and posts; parameters are validated by the server | unit | `web/launch/LaunchPage.test.tsx` › `Load inspects; the guess is pressed; Launch waits for the required field, then posts`; `srv/api/test_launch.py::test_launch_validates_params`, `::test_inspect_reads_schemas` | PASS (CI) |
| F-03 | N | Snakemake form: nested config map as dotted keys, the preview in YAML | unit | `web/launch/LaunchPage.test.tsx` › `UX-PAR-31/32: a Snakemake nested map is a section of dotted keys, rebuilt on submit; the preview is YAML`; `srv/api/test_launch.py::test_launch_snakemake_accepted` | PASS (CI) |
| F-04 | N | Run resources: optional inputs with caps; the values reach the engine | unit | `web/launch/LaunchResources.test.tsx` › `Nextflow on Login node: three optional inputs with the caps in their hints; the values go in default_resources`; `srv/api/test_config_file.py::test_req20_resources_bounds_and_kept`; `cli/test_headscript.py::test_req20_nextflow_resources_in_spectio_config`, `::test_req20_snakemake_one_default_resources_list` | PASS (CI) |
| F-05 | E | Resources out of bounds: an error under each input, listed in Before Launch, nothing sent; the server's 422 lands on its input | unit | `web/launch/LaunchResources.test.tsx` › `out of bounds before Launch: each error under its input, listed in Before Launch with a link, and nothing is sent`, `the server's 422 on a resource lands on its input`; `srv/api/test_config_file.py::test_req20_resources_above_local_cap` | PASS (CI) |
| F-06 | N | Extra config file: read once, kept with the run, passed to the engine first | unit | `srv/api/test_config_file.py::test_req20_config_file_kept`, `::test_req20_runner_gets_the_values_and_the_bytes_then_cleared`; `cli/test_headscript.py::test_req20_nextflow_extra_config_first`, `::test_req20_snakemake_extra_configfile_before_params` | PASS (CI) |
| F-07 | E | A config file of mode 664: Launch refuses it, so Before Launch must already say so, not "Nothing is missing" (FU-P3-121) | unit | `srv/api/test_config_file.py::test_inspect_config_file_says_what_launch_would_refuse`, `::test_req20_config_file_group_writable_root_and_directory`; `web/launch/LaunchResources.test.tsx` › `a file Launch would refuse is said before Launch, and checked again when the window comes back (FU-P3-121)`, `chmod, then Launch at once: the click is not dropped, a fresh check runs and one POST goes (CR-P3FU121-01)` | PASS (CI) |
| F-08 | E | The same mode-664 case in a real browser against a real server | Playwright | `launch-environment.spec.ts` › `an extra config file Launch would refuse is said before Launch; a pointer click on the aside Launch sends it` (run by `e2e-local` of PR #314) | PASS (CI) |
| F-09 | E | The same mode-664 case on login1, where group-shared directories make 664 the usual mode | login1 | [§17](#17-login1-checklist), item 9 | UNTESTED: not run on login1 yet |
| F-10 | N | Before Launch lists every reason, each a link to its field | unit | `web/launch/LaunchPage.test.tsx` › `FU-P3-86h: Before Launch lists every reason, each a link that moves focus to its field`, `FU-P3-86h: Load a pipeline first links the Pipeline field; nothing missing says so` | PASS (CI) |
| F-11 | E | Phone: the pinned bar says why Launch waits | unit | `web/launch/LaunchPage.test.tsx` › `UX-PAR-34: on the phone the pinned bar says why Launch waits, then what it launches` | PASS (CI) |
| F-12 | E | Pipeline directory missing, relative, or with both engines' entry files | unit | `srv/api/test_launch.py::test_inspect_refuses_relative_or_missing`, `::test_inspect_ambiguous_engine_no_guess`; `web/launch/LaunchPage.test.tsx` › `both entry files: no guess, Launch says to choose the engine` | PASS (CI) |
| F-13 | E | The config file can no longer be read at Launch (503): a banner, values kept | unit | `web/launch/LaunchResources.test.tsx` › `the file could not be read (503): a banner with the server's reason, the values kept, and Launch again`; `srv/api/test_config_file.py::test_req20_config_file_pool_timeout` | PASS (CI) |

## 7. Run actions: resume, copy, cancel, pin, delete

Owners: [ui-spec §4.4](../specs/ui-spec.md#44-run-detail), [api §5.1](../specs/api-and-data-model.md#51-run-actions).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| X-01 | N | Resume asks, creates a child, both runs link to each other | Playwright | `skeleton.spec.ts` › `Resume asks, creates a child, and both runs link to each other` (mocks; desktop and phone) | PASS (CI) |
| X-02 | N | Resume of a real failed run: the child reuses the parent's directories and caches the tasks that succeeded | unit | `srv/api/test_relaunch.py::test_resume_failed_creates_child`; `cli/test_local_launcher.py::test_resume_launch_runs_in_the_parents_dirs`; `cli/test_headscript.py::test_resume_head_script_nf`, `::test_resume_head_script_smk` | PASS (CI) |
| X-03 | N | Resume of a real failed run, end to end in the browser | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| X-04 | E | Resume refused: the reason shows as text, the button stays visible; the directories are checked again; no unlock while the head lives | Playwright | `skeleton.spec.ts` › `a refused Resume stays visible, aria-disabled, with its reason as text` (mocks); also `srv/api/test_relaunch.py::test_resume_rechecks_dirs`, `::test_req16_no_unlock_when_live` | PASS (CI) |
| X-05 | E | Two tabs resume the same run at once: one child only | unit | `srv/api/test_relaunch.py::test_req16_one_child_parallel` | PASS (CI) |
| X-06 | N | Copy to a new launch: the form opens prefilled with the values that differ | Playwright | `skeleton.spec.ts` › `Copy to a new launch opens the form prefilled with the non-default values listed` (mocks); `web/launch/CopyLaunch.test.tsx` › `the form opens prefilled, with the banner naming exactly the values that differ` | PASS (CI) |
| X-07 | N | The Copy items (command, config, run directory, run ID) | Playwright | `skeleton.spec.ts` › `the Copy items are in the shared header's More actions on every tab and state, and announce 'Copied'` | PASS (CI) |
| X-08 | N | Cancel a running Nextflow run on one host: the dialog, then Cancelled | Playwright | `skeleton.spec.ts` › `cancel a running Nextflow run → Cancelled` (desktop and phone) | PASS (CI) |
| X-09 | N | Cancel a running Snakemake run on one host | Playwright | GAP: `skeleton.spec.ts` › `cancel a running Snakemake run → Cancelled` is a stale `test.fixme` (TODO P1 Task 7, built since) | PASS (CI) |
| X-10 | N | Cancel on SLURM: cancelled once a task runs, in time; no attempt left pending, submitted or running; no job or session left | slurm-mini | `tests/slurm/e2e.sh cancel nextflow`, `cancel snakemake` (`CANCEL_CHECKS`); unit side `cli/test_tmux_launcher.py::test_cancel_interrupt_then_term`, `::test_cancel_waits_for_the_grace` | PASS (CI) |
| X-11 | E | Cancel during submission on one host: before the head starts, before the engine starts, in the launch's lease | unit | `cli/test_local_launcher.py::test_cancel_before_the_head_starts`, `::test_cancel_just_before_the_engine_starts`, `::test_cancel_in_the_lease_of_its_launch_beats_a_fast_head`; `cli/test_headscript.py::test_cancel_during_the_listing` | PASS (CI) |
| X-12 | E | Cancel during submission on SLURM: while the first jobs are still `PENDING` | slurm-mini | GAP | UNTESTED: not in the CI matrix yet (the `cancel-pending` case exists in `tests/slurm/e2e.sh`; adding it needs a workflow change) |
| X-13 | E | Cancel in two tabs: the second tab shows Cancelling or Cancelled and no Cancel button, with no error | Playwright | GAP; the API side is `srv/api/test_cancel.py::test_cancel_states` | PASS (CI) |
| X-14 | E | No Cancel on an ended run, nor on a run started from a terminal | unit | `srv/api/test_cancel.py::test_cancel_cli_observed_not_in_this_version`; `web/runs/RunDetailPage.test.tsx` › `no Cancel on a terminal run, nor on a run started from a terminal` | PASS (CI) |
| X-15 | N | Pin: pinned runs first; the button pressed | unit | `srv/api/test_runs_manage.py::test_pin`, `::test_pin_is_a_guarded_write`; `web/runs/RunsPage.test.tsx` › `FU-P3-115b: the pin button is pressed for a pinned run and sends PATCH pinned` | PASS (CI) |
| X-16 | N | Pin in a real browser, kept after a reload | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| X-17 | N | Delete an ended run from the list; it leaves the API | Playwright | `skeleton.spec.ts` › `FU-P3-115b: an ended run is selected in the list and deleted, and leaves the API` (desktop and phone) | PASS (CI) |
| X-18 | E | Delete with its directories: no symlink followed, refused while the head lives, a lineage deleted together | unit | `srv/api/test_runs_manage.py::test_delete_directories`, `::test_delete_directory_symlink_is_not_followed`, `::test_delete_directories_refused_while_the_head_lives`, `::test_delete_directories_of_a_lineage_together` | PASS (CI) |
| X-19 | E | Delete of a run that has not ended is refused, with its reason | unit | `srv/api/test_runs_manage.py::test_delete_refuses_a_run_not_ended`; `web/runs/RunsPage.test.tsx` › `FU-P3-115b: a selected run that has not ended keeps Delete refused, with its reason` | PASS (CI) |
| X-20 | N | A confirmed Delete on the EMBL login node, directories ticked | login1 | [§17](#17-login1-checklist), item 4 | PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): the run is gone (404) and its directory removed, the runs root kept. The resumed-run variant was not run |

## 8. Environments

Owners: [ui-spec §4.8.1](../specs/ui-spec.md#481-environments-in-001), [api §5.4](../specs/api-and-data-model.md#54-environments-001).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| V-01 | N | Create, read, update, delete and make default through the API | unit | `srv/api/test_environments.py::test_req18_routes_create_get_put_delete`, `::test_req18_routes_make_default` | PASS (CI) |
| V-02 | N | The same by keyboard in a real browser | Playwright | `environments.spec.ts` › `create, edit, make default and delete an environment with the keyboard` (run by `e2e-local` of PR #314) | PASS (CI) |
| V-03 | E | Phone: a card opens its page, which edits, makes default and deletes | Playwright | `environments.spec.ts` › `on a phone: a card opens its page, which edits, makes default and deletes, by keyboard` (run by `e2e-local` of PR #314) | PASS (CI) |
| V-04 | E | Phone, component level | unit | `web/environments/EnvironmentsPage.test.tsx` › `phone: a card is one link to its page, with no action buttons` | PASS (CI) |
| V-05 | E | An invalid or unreadable `environments.toml` | unit | `srv/api/test_environments.py::test_req18_routes_file_unusable`, `::test_req18_routes_unreachable`; `web/environments/EnvironmentsPage.test.tsx` › `an invalid file: its line above the cards, New environment waits with its reason` | PASS (CI) |
| V-06 | E | Two tabs: an edit over a changed file gets 412 and Reload | unit | `srv/api/test_environments.py::test_req18_routes_file_changed`; `web/environments/EnvironmentsPage.test.tsx` › `editing: 412 says the environment changed, with Reload; after Save, the list with focus` | PASS (CI) |
| V-07 | N | Define an environment from Launch, launch with it, read it on the run | Playwright | `launch-environment.spec.ts` › `define an environment from Launch, launch with it, and read it on the run` (not run by CI); API side `srv/api/test_environments.py::test_req18_snapshot_launch_with_environment` | PASS (CI) |

## 9. Pipeline catalog

Owners: [ui-spec §4.7.1](../specs/ui-spec.md#471-pipeline-catalog-in-001), [api §5.6](../specs/api-and-data-model.md#56-pipeline-catalog-001).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| C-01 | N | Create, read, update and delete an entry through the API | unit | `srv/api/test_catalog.py::test_req18_catalog_create_get_put_delete` | PASS (CI) |
| C-02 | N | Add, edit and delete by keyboard in a real browser | Playwright | `catalog.spec.ts` › `add, edit and delete a catalog entry with the keyboard` (run by `e2e-local` of PR #314) | PASS (CI) |
| C-03 | N | Launch from a catalog entry | Playwright | `launch-environment.spec.ts` › `launch from a catalog entry` (run by `e2e-local` of PR #314) | PASS (CI) |
| C-04 | E | A Git repository that cannot be reached, a changed file, a params file that cannot be read | unit | `srv/api/test_catalog.py::test_req18_catalog_unreachable`, `::test_req18_catalog_file_changed`, `::test_req18_catalog_params_read_failures` | PASS (CI) |
| C-05 | E | Two tabs: an edit with a stale `If-Match` gets 412 and Reload | unit | `web/catalog/CatalogPage.test.tsx` › `Edit: Name is read only, PUT carries If-Match, a 412 shows Reload; Cancel returns focus to Edit` | PASS (CI) |
| C-06 | E | Phone: a row links to the entry's page, Delete stacked under the form | unit | `web/catalog/CatalogPage.test.tsx` › `phone: a row is a link to the entry's page, which stacks Delete under the form` | PASS (CI) |

## 10. File preview

Owners: [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview), [api §5.3](../specs/api-and-data-model.md#53-run-files-explorer-and-preview) and [§5.3.1](../specs/api-and-data-model.md#531-imaging-viewers-fu-p3-102).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| P-01 | N | Text: `stat` first, the whole file or the start, Load more, End | unit | `web/runs/FilePreview.test.tsx` › `stat first, then the whole file: facts, path, Copy path, Download, focus on the name`, `End reads the last 64 KiB from its first whole line, with no line numbers`; `srv/api/test_results.py::test_req13_results_text_tail`, `::test_req13_results_text_range` | PASS (CI) |
| P-02 | N | Text in a real browser: Load more keeps focus | Playwright | `preview.spec.ts` › `Load more keeps focus while it loads and after` (not run by CI; PR #314) | PASS (CI) |
| P-03 | N | Table: a TSV in AG Grid under the CSP | Playwright | `preview.spec.ts` › `a TSV preview is an AG Grid under the CSP: no violation, sorts and moves from the keyboard` (not run by CI; PR #314) | PASS (CI) |
| P-04 | N | Image and SVG: an `<img>` that runs and fetches nothing; a navigation downloads | Playwright | `preview.spec.ts` › `an SVG in the preview loads in an <img>, runs nothing and fetches nothing`, `the image URL, once loaded in an <img>, downloads on a top-level navigation, with no SVG document` (not run by CI; PR #314) | PASS (CI) |
| P-05 | N | TIFF, drawn flat | unit | `web/runs/FilePreview.test.tsx` › `a TIFF is drawn flat on a 2D canvas through the pinned client; Actual size scrolls it`; `srv/api/test_imaging.py::test_req14_imaging_tiff_name`, `::test_req14_imaging_served` | PASS (CI) |
| P-06 | N | TIFF, drawn flat in a real browser | Playwright | GAP: `viewer.spec.ts` covers OME-TIFF and OME-Zarr only | PASS (CI) |
| P-07 | N | OME-TIFF in the WebGL viewer under the CSP | Playwright | `viewer.spec.ts` › `the OME-TIFF viewer draws under the CSP, with no violation, reading only its raw URL` (not run by CI; projects desktop, firefox, webkit) | PASS (CI) |
| P-08 | N | OME-Zarr in the WebGL viewer under the CSP | Playwright | `viewer.spec.ts` › `the OME-Zarr viewer draws under the CSP, reading only keys below its folder with as=zarr` (run by `e2e-local` of PR #314) | PASS (CI) |
| P-09 | E | Large text: the 1 MiB and 20,000-line caps, a stream cap | unit | `web/runs/FilePreview.test.tsx` › `at 1 MiB shown Load more stops and focus moves to the line that says so`, `at most 20,000 lines are rendered`; `srv/api/test_results.py::test_req14_stream_cap` | PASS (CI) |
| P-10 | E | Huge image: over the size or pixel cap, a sparse 2 GiB TIFF, a plane over 50 megapixels | unit | `srv/api/test_results.py::test_req14_image_size_caps`, `::test_req14_image_too_many_pixels`; `srv/api/test_imaging.py::test_req14_imaging_sparse_2gib`; `web/runs/imaging/flat.test.ts` › `a plane over 50 megapixels and a compression off the allow-list are refused before any tile` | PASS (CI) |
| P-11 | E | Corrupt file: a signature mismatch, not a TIFF, a refused compression, JSON 10,000 deep, an OME-Zarr that is not an image | unit | `srv/api/test_results.py::test_req14_image_signature_mismatch`; `srv/api/test_imaging.py::test_req14_imaging_not_a_tiff`; `web/runs/FilePreview.test.tsx` › `a TIFF's states: a refused compression, a 413, a 503 with Retry, an empty file`, `JSON 10,000 deep falls back to text and says why` | PASS (CI) |
| P-12 | E | Huge and corrupt files in a real browser: the page stays responsive, shows its state, no CSP violation | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| P-13 | E | A file replaced while it is read | unit | `srv/api/test_results.py::test_req13_raw_file_replaced_mid_download`; `srv/api/test_imaging.py::test_req14_imaging_replaced_mid_range` | PASS (CI) |
| P-14 | E | Phone: OME-Zarr first plane flat; a TIFF too large for 2,048 px a side says so | unit | `web/runs/FilePreview.test.tsx` › `on a phone an OME-Zarr shows the first plane flat, with Open on a larger screen and Copy link`, `on a phone a TIFF too large for 2,048 px a side says so, with Copy link and Download` | PASS (CI) |
| P-15 | E | HTML reports in the sandboxed viewer | Playwright | `report.spec.ts` › `req14: a report in the viewer cannot open windows, navigate the top page or leave`, `a MultiQC report renders in the viewer and cannot call the API` (desktop and phone) | PASS (CI) |

## 11. Search, notifications, profile

Owners: [ui-spec §12.13](../specs/ui-spec.md#1213-notifications-panel) (notifications), [ui-spec §4.10.1](../specs/ui-spec.md#4101-profile-in-001) (profile), [api §5.8](../specs/api-and-data-model.md#58-me-and-sign-out-001) and [§5.9](../specs/api-and-data-model.md#59-notifications-001).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| Q-01 | N | Search: one debounced request, results grouped under Runs, Pipelines and Pages | unit | `web/shell/SearchDialog.test.tsx` › `results are grouped under Runs, Pipelines and Pages, after one debounced request`; `srv/api/test_read.py::test_runs_filter_state_and_q` | PASS (CI) |
| Q-02 | N | Search in a real browser: Ctrl+K, type a run's short ID, Enter opens it | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| Q-03 | E | The short ID in any case; a failed request; nothing found | unit | `web/shell/SearchDialog.test.tsx` › `FU-P3-116: the short ID the UI shows (last 6 of the run ID) finds its run, in any case`, `a failed request shows an error line`, `nothing found says No match` | PASS (CI) |
| Q-04 | E | Phone: the search icon opens the same dialog, full screen | unit | `web/shell/SearchDialog.test.tsx` › `on a 360 px phone the search icon still shows and opens the dialog (CR-P3FU89-01)` | PASS (CI) |
| N-01 | N | Notifications from ended and waiting runs, unread count, Mark all as read | unit | `srv/api/test_notifications.py::test_derived_from_ended_and_waiting_runs_newest_first`, `::test_mark_read_moves_the_mark_forward_only`; `web/shell/NotificationsBell.test.tsx` › `the bell names and shows the unread count` | PASS (CI) |
| N-02 | N | Notifications in a real browser: a run ends, the bell counts it, the row opens the run | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| N-03 | E | A run change on the event stream refreshes the count | unit | `web/shell/NotificationsBell.test.tsx` › `a run change on the event stream refreshes the count` | PASS (CI) |
| N-04 | E | Two tabs: Mark all as read in one tab clears the count in the other | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| N-05 | E | Phone: the panel is a modal bottom sheet | unit | `web/shell/NotificationsBell.test.tsx` › `on a 360 px phone the panel is a modal bottom sheet with a visible Mark all as read (CR-P3FU113-01)` | PASS (CI) |
| U-01 | N | Profile: who the server runs as, this session, the config paths, the theme | unit | `srv/api/test_me.py::test_me_names_the_principal_the_session_and_the_paths`, `::test_me_holds_no_secret_and_no_file_contents`; `web/profile/ProfilePage.test.tsx` › `/profile names who the server runs as and this session` | PASS (CI) |
| U-02 | N | Profile in a real browser, then Sign out of this session | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| U-03 | E | Sign out ends this session only (another tab or browser stays signed in) | unit | `srv/api/test_me.py::test_sign_out_ends_this_session_only`; `web/profile/ProfilePage.test.tsx` › `a failed sign-out stays signed in and says why` | PASS (CI) |
| U-04 | E | Phone: the title is the top bar's h1 | unit | `web/profile/ProfilePage.test.tsx` › `phone (360 px): the title is the top bar's h1 and the avatar links to /profile` | PASS (CI) |

## 12. Runs started from a terminal

Owners: [architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), [ui-spec §6](../specs/ui-spec.md#6-runs-launched-from-the-command-line).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| T-01 | N | Nextflow with `nf-spectio`, run by hand: the bridge writes its pointer | unit | `cli/test_bridge_nextflow.py::test_terminal_run_writes_pointer`, `::test_pointer_keys_exact` (engines) | PASS (CI) |
| T-02 | N | Snakemake with `--logger spectio`, run by hand: the plugin writes its pointer | unit | `smk/test_plugin.py::test_terminal_run_writes_pointer_snakemake`, `::test_pointer_keys_exact_snakemake` | PASS (CI) |
| T-03 | N | The server finds the pointer, shows the run and ends it from its events | unit | `cli/test_observed.py::test_scan_finds_pointer`, `::test_terminal_run_shown_and_ended`, `::test_terminal_snakemake_run_ends_from_its_spool` | PASS (CI) |
| T-04 | N | End to end: an engine run by hand while `spectio serve` runs; the list shows the "From a terminal" chip, the run detail follows it to its end | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| T-05 | N | The same on the EMBL login node, once per engine | login1 | [§17](#17-login1-checklist), item 10 | UNTESTED: not run on login1 yet |
| T-06 | E | Forged or loose pointers and foreign `.spectio` directories are refused | unit | `cli/test_observed.py::test_req12_pointer_checks`, `::test_pointer_cannot_alias_driven_run`; `cli/test_bridge_nextflow.py::test_bridge_refuses_foreign_spectio_dir` (engines); `smk/test_plugin.py::test_bridge_refuses_foreign_spectio_dir_snakemake` | PASS (CI) |
| T-07 | E | Server down while the run goes on; a launch directory that hangs or is gone | unit | `cli/test_observed.py::test_server_down_events_wait`, `::test_stuck_launch_dir_never_holds_the_boot`, `::test_end_pointer_missing_is_a_no_op` | PASS (CI) |
| T-08 | E | The head is gone on the same boot: Head lost; another boot: not judged | unit | `cli/test_observed.py::test_terminal_run_same_boot_head_gone_is_head_lost`, `::test_terminal_run_other_boot_id_never_head_lost` | PASS (CI) |

## 13. Command line: `init`, `doctor`, `serve`, `login`, `open`

Owners: [CLI §2](../specs/cli-and-shared-libraries.md#2-the-spectio-command-tree), the guides [Opening Spectio from your laptop](../usage/open-from-your-laptop.md) and [Keeping the server running](../usage/keep-the-server-running.md).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| K-01 | N | `spectio init` (SLURM default) and `spectio init --local` | unit | `cli/test_init.py::test_init_creates_one_environment`, `::test_init_local_environment`, `::test_init_unpacks_nf_spectio` | PASS (CI) |
| K-02 | E | `init` refuses a missing or relative runs root, an open or symlinked data directory, a privileged port | unit | `cli/test_init.py::test_runs_root_must_exist_and_be_absolute`, `::test_init_refuses_open_or_symlinked_data_dir`, `::test_init_privileged_port_refused` | PASS (CI) |
| K-03 | N | `spectio doctor`: engines, file system, SQLite, disk, the environments and catalog files | unit | `cli/test_doctor.py::test_doctor_reports_engines`, `::test_doctor_reports_fs_and_sqlite`, `::test_doctor_reports_runs_disk`, `::test_req18_file_doctor_prints_path_state_default` | PASS (CI) |
| K-04 | E | `doctor` on a site with accounting off says so (`AccountingStorageType`) | unit | GAP | UNTESTED: belongs to FU-P3-106b and FU-P3-126, assumed for after 0.0.1 ([inbox #156](inbox.md#156-assumed-a-slurm-site-without-accounting-and-a-run-whose-jobs-left-the-queue-task-22-2026-11-18)) |
| K-05 | N | `spectio serve`: the start text in local and SLURM modes | unit | `srv/test_serve.py::test_serve_local_start_text`, `::test_serve_slurm_start_text_and_tmux_runner` | PASS (CI) |
| K-06 | N | `spectio serve --detach`: a tmux session, the link in the calling terminal, the tunnel to the socket | unit | `srv/test_detach.py::test_detach_starts_tmux_session`, `::test_detach_link_in_calling_terminal_not_in_pane`, `::test_detach_on_a_socket_prints_the_tunnel_to_it` | PASS (CI) |
| K-07 | E | A second `serve` refused, a taken port, a state file naming another node, no tmux | unit | `srv/test_serve.py::test_second_serve_refused`, `::test_port_taken_refuses`, `::test_state_file_names_other_node`; `srv/test_detach.py::test_detach_no_tmux_exits_2` | PASS (CI) |
| K-08 | N | `spectio login --print-link` (text and JSON), over TCP and over the socket | unit | `srv/security/test_req2_secrets.py::test_login_print_link`, `::test_print_link_json`; `srv/security/test_unix_socket.py::test_login_print_link_over_the_socket` | PASS (CI) |
| K-09 | E | `login` refuses a foreign listener, a socket outside the database directory, a file that is not a socket | unit | `srv/security/test_req2_secrets.py::test_print_link_refuses_foreign_listener`; `srv/security/test_unix_socket.py::test_login_refuses_a_socket_outside_the_db_dir`, `::test_login_refuses_a_socket_file_that_is_not_one` | PASS (CI) |
| K-10 | N | `spectio open <host>` with a fake ssh: reads `server.json`, first start, tunnel to the socket, link built on the laptop | unit | `cli/test_open.py::test_reads_state_file_and_reaches_its_node`, `::test_first_start_asks_no_link_from_serve`, `::test_tunnel_forwards_to_the_socket_of_server_json`, `::test_url_built_locally` | PASS (CI) |
| K-11 | E | `open` fails cleanly: ssh failure, tunnel failure, no `spectio` on the cluster, a stale state file | unit | `cli/test_open.py::test_ssh_failure_exits_3`, `::test_tunnel_that_fails_exits_3`, `::test_missing_remote_spectio_prints_install`, `::test_stale_state_file_named_in_error` | PASS (CI) |
| K-12 | N | `init`, `serve` and `login` as a user runs them, in front of a browser | Playwright | `tests/e2e/serve-local.sh` (`spectio init --local`, `spectio serve`) and `tests/e2e/global-setup.ts` (`spectio login --print-link --json`), used by every `e2e-local` test | PASS (CI) |
| K-13 | N | `spectio open` and the SSH config entry from a real laptop to login1 | login1 | [§17](#17-login1-checklist), items 2 and 3 | UNTESTED: needs Thomas's laptop for `spectio open` (the tunnel to the socket was driven by Playwright; see S-10) |

## 14. REST API and live events

Owners: [api §5](../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1) and [§8.3](../specs/api-and-data-model.md#83-live-streams-sse), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (req. 1 to 7), the [API page](../api/index.md).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| R-01 | N | `/api/v1` matches its OpenAPI snapshot; read routes have response models; no docs served | unit | `srv/api/test_openapi.py::test_openapi_snapshot`, `::test_read_routes_have_response_models`, `::test_docs_not_served` | PASS (CI) |
| R-02 | N | Browser guards: session on every route, Host check, same-origin writes, JSON bodies, no CORS | unit | `srv/security/test_req2_secrets.py::test_req2_every_route_needs_session`; `srv/security/test_req4_host.py::test_req4_others_refused`; `srv/security/test_req7_writes.py::test_req7_missing_origin_403`, `::test_req7_body_needs_json_415`, `::test_req7_no_cors_headers` | PASS (CI) |
| R-03 | N | SSE: a delta after each ingest, one for a new run, coalesced per run | unit | `srv/api/test_stream.py::test_stream_delta_after_ingest`, `::test_new_run_sends_a_delta`, `::test_stream_coalesces_per_run` | PASS (CI) |
| R-04 | E | SSE over the Unix socket | unit | `srv/security/test_unix_socket.py::test_the_event_stream_flows_over_the_socket` | PASS (CI) |
| R-05 | E | A slow client is dropped and never blocks; the client cap holds under concurrent opens (many tabs); keep-alive | unit | `srv/api/test_stream.py::test_slow_client_dropped_never_blocks`, `::test_client_cap_holds_under_concurrent_opens`, `::test_stream_keep_alive`, `::test_dropped_client_still_counts` | PASS (CI) |
| R-06 | E | SSE cut and reconnect: the client reconnects and refetches what it missed | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| R-07 | E | Server restart while a stream is open: the stream comes back on the new server | Playwright | GAP (S-08) | UNTESTED |
| R-08 | E | Errors are problem bodies that quote no input; caps on body size and depth | unit | `srv/api/test_hardening.py::test_unknown_path_is_a_problem`, `::test_body_cap_413`, `::test_deeply_nested_body_is_a_422_problem`, `::test_unparsable_url_detail_never_quotes_it` | PASS (CI) |
| R-09 | E | Served pages carry the CSP, Referrer-Policy and COOP headers; a foreign Host gets 400 | Playwright | `skeleton.spec.ts` › `the served pages carry the CSP, Referrer-Policy and COOP headers`, `a foreign Host gets 400 and no data` | PASS (CI) |

## 15. Sign-in with a single-use link

Owners: [auth §2.1](../specs/authentication-and-access.md#21-magic-link-and-share-link-safety), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (req. 2 and 3), the guide [Signing in](../usage/sign-in.md).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| M-01 | N | A link from `spectio login`, opened in a browser, sets the session cookie | Playwright | `tests/e2e/global-setup.ts` signs in this way before every `e2e-local` test; `srv/security/test_req2_secrets.py::test_req2_exchange_sets_the_session`, `::test_link_js_drops_the_ticket` | PASS (CI) |
| M-02 | E | The ticket is single use, valid 15 minutes, stored hashed | unit | `srv/security/test_req2_secrets.py::test_req2_ticket_single_use_and_15_min`, `::test_req2_ticket_stored_hashed`, `::test_reused_or_expired_link_message` | PASS (CI) |
| M-03 | E | A reused link shows the expired message, in a real browser | Playwright | GAP: `skeleton.spec.ts` › `a reused link shows the expired message` is a stale `test.fixme` (TODO P1 Task 16, built since) | PASS (CI) |
| M-04 | E | A request without the cookie shows the 401 page, not data | Playwright | GAP: `skeleton.spec.ts` › `a request without the cookie shows the 401 page, not data` is a stale `test.fixme` (TODO P1 Task 16) | PASS (CI) |
| M-05 | E | The cookie is named per port; another port's cookie is ignored | unit | `srv/security/test_req3_cookie.py::test_req3_name_has_host_port`, `::test_req3_other_port_cookie_ignored` | PASS (CI) |
| M-06 | E | Two tabs share one session; signing out in one sends the other to the sign-in page on its next request | Playwright | Filled, see [§18](#18-gaps-to-fill) | PASS (CI) |
| M-07 | N | Sign-in through the ssh tunnel on login1 | login1 | [§17](#17-login1-checklist), item 2 | PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): driven by Playwright through an ssh tunnel to the socket — the sign-in link worked, every page answered with no API error ≥ 400, no TCP listener. Thomas's own browser: see S-10 |

## 16. Packaging

Owners: [architecture §7.3](../specs/architecture-plugins-and-packaging.md#73-python-bundle) and [§6](../specs/architecture-plugins-and-packaging.md#6-code-layout), [dev-env §15.2](../specs/dev-environment-and-testing.md#152-how-the-first-tag-is-made).

| ID | Kind | Case | Mode | Existing coverage | Status |
|---|---|---|---|---|---|
| W-01 | N | `uv build --all-packages`: each wheel holds exactly its listed files; `spectio` alone installs with `uv tool install`, prints `spectio 0.0.1`, finds its bridges, stays under 80 MB | unit | `tests/packaging/test_wheel.sh` (`RESULT wheel pass`, job `product`), against `tests/packaging/contents/*.wheel.txt` | PASS (CI) |
| W-02 | N | The web build inside the server wheel: the server installed from its wheel serves the packaged screens | unit | `tests/packaging/test_wheel.sh` (the three wheels in a venv, the screens found); `srv/api/test_web.py::test_every_web_route_is_served`, `::test_spa_routes_serve_index` | PASS (CI) |
| W-03 | E | An installed wheel never uses a planted `web/dist`; a checkout without `dist` says how to build it | unit | `srv/api/test_web.py::test_installed_wheel_never_uses_a_planted_dist`, `::test_missing_dist_says_how_to_build`, `::test_refused_checkout_says_why` | PASS (CI) |
| W-04 | E | `spectio` without its server package: `init` says what to install | unit | `cli/test_init.py::test_init_needs_the_server_package` | PASS (CI) |
| W-05 | N | The wheels installed on a SLURM login node by `uv tool install … --with spectio_server --with spectio_sdk` | slurm-mini | `tests/slurm/e2e.sh install` | PASS (CI) |
| W-06 | N | The same install on login1, from the rc1 wheels | login1 | [§17](#17-login1-checklist), item 1 | PASS (login1, 2026-11-23/24, Claude over ssh for Thomas): the wheels built from autopilot/integration after PR #323 install; `spectio doctor` ok except two warnings fixed since (runs_disk on a 93%-used scratch with 86 TiB free; java when Nextflow brings its own) by PR #337 |
| W-07 | E | Install from PyPI and the Nextflow plugin registry | unit | GAP | UNTESTED: the publish workflow is listed under "Before 0.0.1 is released" in the [roadmap](../roadmap/index.md#001-rc1-the-release-candidate), not in rc1 |

## 17. login1 checklist

Run on the EMBL login node as the account that runs `spectio serve`, from a laptop. Record each item's result in the row it names, as PASS (login1, date, who) or FAIL (date, what). Item 1 comes first. Do not paste real `/scratch` paths or user names into the repository: shots and outputs go through `fixtures.yaml` first ([inbox #155](inbox.md#155-assumed-findings-of-the-login1-check-of-the-design-system-ui-fu-p3-124-fu-p3-125-2026-11-11)).

1. **Install the rc1 wheels** (W-06): `uv tool install --force <dist>/spectio-<version>-py3-none-any.whl --with <dist>/spectio_server-<version>-py3-none-any.whl --with <dist>/spectio_sdk-<version>-py3-none-any.whl` (`<version>` is `0.0.1rc1` for the release candidate), then `spectio --version` and `spectio doctor`.
2. **The laptop opens Spectio through an ssh tunnel** (S-10, K-13, M-07). Do it both ways:
    - **Way 1, the SSH config entry:** its `LocalForward` points at the socket that `spectio serve --detach` names in its tunnel line.
    - **Way 2, `spectio open <host>`:** run on the laptop, it reads `~/.spectio/server.json` and follows it.

    Each way, the link signs in. Then check on login1 that `ss -ltnp` lists no TCP listener owned by your `spectio serve`, and that `ls -ld <db dir>` shows mode `drwx------`.
3. **The tunnel survives a server restart** (S-10): `tmux kill-session -t spectio-server`, then `spectio serve --detach`. Reopen with `spectio open`; the runs are still listed.
4. **A confirmed Delete** (X-20): on an ended run, Delete… with "Also delete its run directory" ticked, confirmed. The run leaves the list, and reloading its URL shows not-found. `ls -ld <runs root>/<run ID>` says the directory is gone. The pipeline's results directory is untouched. Repeat with a resumed run, whose lineage directory goes only with its last run.
5. **The checks of #125, "the run's launch directory is gone"** (D-10), from [inbox #125](inbox.md#125-question-login1-checks-for-the-runs-launch-directory-is-gone-fu-p3-81), on a Nextflow run's Logs tab:
    1. the full problem body the browser received (DevTools, Network: the URL and its `detail`), and whether the run is a Resume;
    2. the runs root in effect (`spectio doctor`, or `spectio.toml` and `SPECTIO_RUNS_ROOT`), and `realpath` of it;
    3. `ls -ld <runs root> <runs root>/<run ID> <runs root>/<run ID>/launch`;
    4. `sqlite3 <db dir>/spectio.db "select id, lineage_id, launch_dir, work_dir from runs where id = '<run ID>'"`;
    5. `hostname` and the same `ls -ld`, both run where the `spectio serve` process runs, not only in a login1 shell;
    6. whether the view now answers `409 run-dir-unreachable` or still `410`, with its `detail`.
6. **Accounting on the site** (E-11): `scontrol show config | grep AccountingStorage`. `AccountingStorageType` must be `accounting_storage/slurmdbd`; any other value means this site is the [#156](inbox.md#156-assumed-a-slurm-site-without-accounting-and-a-run-whose-jobs-left-the-queue-task-22-2026-11-18) case and E-08 becomes a FAIL for EMBL.
7. **`sacct -j` against the efficiency sheet** (D-17, E-11): for one task job of item 8's runs, `sacct -j <jobid> -X -P -o JobID,State,ExitCode,ReqMem,MaxRSS,Elapsed,Timelimit,AllocCPUS,TotalCPU`, and once without `-X`, for the steps. Compare with the job sheet and Why it failed: state, requested and used memory, elapsed time, CPUs.
8. **One end-to-end run per engine, launched from the UI** (E-07): the synthetic `happy` for Nextflow (`-profile test,slurm`) and for Snakemake (workflow profile `slurm`), with the test profile as on 2026-11-11. Each must end Succeeded with its golden counts and its jobs gone from `squeue -u $USER`. Then `tmux ls` shows no `spectio-<run ID>` session. Also cancel one run of each engine while it runs, and resume one failed run.
9. **A config file of mode 664** (F-09): `chmod 664` an extra config file in a group-shared pipeline directory and type its path in Launch. Before Launch must list "Fix Extra config file: the file is writable by group or others" before you press Launch. After `chmod go-w`, the reason goes once the window regains focus, and Launch is accepted.
10. **Runs started from a terminal** (T-05):
    - **Nextflow:** with `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>`, run `nextflow run` by hand in a tmux session;
    - **Snakemake:** with `--logger spectio`, run `snakemake` by hand.

    Each run appears in the list with the "From a terminal" chip and follows to its end. It has no Cancel and no Resume.

## 18. Gaps to fill

Each GAP of §2 to §16, with the proposed test. Stale `test.fixme` tests are listed under their own IDs.

| Gap | Proposed test (file) | Test name | Scenario |
|---|---|---|---|
| E-02 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `launch happy (Snakemake, local) → detail shows Succeeded and the golden counts` | With Snakemake on the server's `PATH` in `e2e-local`, launch the synthetic Snakemake `happy` (chunks=2) through the API and check states and counts in the detail. |
| E-08 | `tests/slurm/e2e.sh` | Filled: `tests/slurm/e2e.sh` › `launch snakemake` (the harness no longer adds `--slurm-status-command`; the product's FU-P3-106b sets it) | On slurm-mini (no `slurmdbd`), launch Snakemake without the harness's `--slurm-status-command squeue`. Today it is expected to hang; once FU-P3-106b lands, the run ends Succeeded. |
| E-09 | `packages/spectio-server/tests/api/test_failure.py` | Filled: `packages/spectio-server/tests/api/test_failure.py` › `test_stall_on_the_run_detail` | A fake `squeue` and `sacct` that know no job for a running attempt past the grace period: the run carries a stall warning (FU-P3-126). |
| S-08 | `tests/e2e/restart.spec.ts` (new, run by `e2e-local` with a restartable server) | `a run keeps going across a server restart and the detail catches up without a reload` | Launch `happy` at scale 5, kill and restart `spectio serve`; the open detail reconnects and reaches Succeeded. |
| L-04 | `tests/e2e/stream.spec.ts` (new) | Filled: `tests/e2e/stream.spec.ts` › `a dropped event stream says Reconnecting…, comes back and refetches the runs that changed` | Abort `/api/v1/events/stream` with `page.route`, end a run meanwhile, release the route; the list shows the new state. |
| L-05 | `packages/spectio-server/tests/test_serve.py` | `test_rows_outside_the_current_runs_root_are_not_listed` | Index runs under root A, restart with root B; `GET /runs` does not list A's runs as B's (FU-P3-84). |
| L-06 | `tests/e2e/tabs.spec.ts` (new) | Filled: `tests/e2e/tabs.spec.ts` › `a run deleted in one tab leaves the list of the other` | Two pages in one context; delete in page 1; page 2's list drops the row on the next frame. |
| D-07 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `the Logs tab of a real run shows the engine log and downloads it` | After the happy run, open Logs, check `.nextflow.log` lines and the Download. |
| D-09 | `web/src/runs/RunDetailPage.test.tsx` | Filled: `web/src/runs/RunDetailPage.test.tsx` › `D-09: a 409 run-dir-unreachable on the Logs tab names the directory it tried` | Mock a 409 problem with its `detail`; the Logs tab and the job files show the directory and no "cleaned" wording. |
| D-20 | `tests/e2e/stream.spec.ts` (new) | Filled: `tests/e2e/stream.spec.ts` › `the run detail reconnects after a dropped stream and shows the tasks that finished` | As L-04, on an open run detail during `happy` at scale 5. |
| X-03 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `resume a real failed run: the child caches the tasks that succeeded` | Launch the synthetic `tool_error_then_fixed_resume`, fix, Resume from the UI; the child succeeds with cached tasks. |
| X-09 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `cancel a running Snakemake run → Cancelled` (the stale `test.fixme` is gone) | With Snakemake in `e2e-local`, launch at scale 5, cancel from the dialog, reach Cancelled. |
| X-12 | `tests/slurm/e2e.sh` | Filled: `tests/slurm/e2e.sh` › `cancel-pending` (not in the CI matrix yet) | Hold the partition (`scontrol update PartitionName=htc State=DOWN`), launch, cancel while jobs are `PENDING`; the run ends Cancelled with no job left. |
| X-13 | `tests/e2e/tabs.spec.ts` (new) | Filled: `tests/e2e/tabs.spec.ts` › `cancel in one tab, the other shows Cancelled and no Cancel button` | Two pages on one running run; cancel in page 1; page 2 updates with no error. |
| X-16 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `pin a run; it stays first after a reload` | Pin an ended run from the list; reload; it is first and its pin pressed. |
| P-06 | `tests/e2e/viewer.spec.ts` | Filled: `tests/e2e/viewer.spec.ts` › `a plain TIFF draws flat under the CSP` | Seed a non-OME TIFF in the seeded run's results; open its preview; the canvas draws, no CSP violation. |
| P-12 | `tests/e2e/preview.spec.ts` | Filled: `tests/e2e/preview.spec.ts` › `a huge or corrupt file shows its state and the page stays responsive` | Seed a 60000 × 60000 PNG header, a truncated TIFF and a 50 MiB text file; each shows its state, and the page still navigates. |
| Q-02 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `Ctrl+K finds a run by its short ID and Enter opens it` | After the happy run, search its last six characters; Enter opens the detail. |
| N-02 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `an ended run appears in the bell and opens from it` | After the happy run, the bell counts one unread; its row opens the run; Mark all as read clears it. |
| N-04 | `tests/e2e/tabs.spec.ts` (new) | Filled: `tests/e2e/tabs.spec.ts` › `Mark all as read in one tab marks the run read in the other` | Two pages; mark read in page 1; page 2's count is 0 after the next frame or reload. |
| U-02 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `the profile names the account and Sign out ends this session` | Open `/profile`, check the account and paths, sign out; the next request shows the sign-in page. Run it last, or in its own context. |
| R-06 | `tests/e2e/stream.spec.ts` (new) | Filled: the L-04 test of `tests/e2e/stream.spec.ts` | The same test closes L-04 and R-06; it also checks that a new `EventSource` opens after the abort. |
| R-07 | `tests/e2e/restart.spec.ts` (new) | the S-08 test | The same test closes S-08 and R-07; it also checks that the stream reopens on the new server. |
| T-04 | `tests/e2e/terminal.spec.ts` (new, `e2e-local`) | Filled: `tests/e2e/terminal.spec.ts` › `a Nextflow run started by hand appears with From a terminal and ends` | With `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` and the server's home, run `nextflow run` on the synthetic pipeline; the list shows the chip; the detail reaches Succeeded. |
| K-04 | `packages/spectio/tests/test_doctor.py` | Filled: `packages/spectio/tests/test_doctor.py` › `test_doctor_slurm_accounting` | A fake `scontrol show config` with `AccountingStorageType = accounting_storage/none`: `doctor` warns and names the Snakemake consequence. |
| M-03 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `a reused link shows the expired message` (the stale `test.fixme` is gone) | Get a link, open it twice in fresh contexts; the second shows the expired message. |
| M-04 | `tests/e2e/skeleton.spec.ts` | Filled: `tests/e2e/skeleton.spec.ts` › `a request without the cookie shows the 401 page, not data` (the stale `test.fixme` is gone) | A fresh context with no storage state opens `/runs`; it shows the 401 page and no run data. |
| M-06 | `tests/e2e/tabs.spec.ts` (new) | Filled: `tests/e2e/tabs.spec.ts` › `signing out in one tab sends the other to sign-in on its next request` | Two pages, one context; sign out in page 1; page 2's next navigation shows the sign-in page. |
| W-07 | `.github/workflows/pypi-publish.yml` dry run | `install from TestPyPI` | After the publish workflow is set up: install `spectio[server]` from TestPyPI in a fresh venv and run `spectio --version` and `spectio doctor`. |

**Not GAPs, but run by no CI job when this page was written:** the specs `preview.spec.ts` (P-02 to P-04), `viewer.spec.ts` (P-07, P-08), `environments.spec.ts` (V-02, V-03), `catalog.spec.ts` (C-02) and `launch-environment.spec.ts` (F-08, V-07, C-03) exist and need a real server. PR #314's `ci.yml` now runs every spec in `tests/e2e` in `e2e-local` (see the Playwright bullet of §1), so those cells are PASS (CI). The slurm-mini cells pass on integration, but slurm-mini has no accounting, so the efficiency and `sacct` cells (D-17, E-11) can only pass on login1.
