# P1 · Walking skeleton (0.0.1 on a cluster) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` (step P3 of [`next-phase.md`](../playbooks/next-phase.md)) or `executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

*Draft, 2026-10-28 (step P1); revised the same day for the head in tmux, the EMBL target and the laptop access ([log](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open)), then after the doc review of PR #47 for live refresh over SSE and SQLite as a rebuildable index ([log](../decisions/log.md#2026-10-28-001-live-refresh-over-sse-sqlite-as-a-rebuildable-index)), and after the security review of that change for §15.3 requirements 8–11 ([record](../reviews/code/APPLY4.md)); then for runs started from a terminal, Tasks 25 and 26 ([log](../decisions/log.md#2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues)); then for stages declared or detected, Assumption 6 and Task 27 ([log](../decisions/log.md#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list)); then for each job's files, Resume, the failure summary, results, the copy actions and resources, Assumptions 1, 3 and 20 (notes) and Tasks 28 to 32 ([log](../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources)). Waiting for Thomas at the GO gate ([R10 §5](../reviews/R10-synthesis.md#5-go-no-go)). No product code exists yet; this page writes none.*

![The P1 walking skeleton: a laptop browser with the launch form, runs list and run detail with Cancel, refreshed over SSE, reaches spectio serve, in its own tmux session on an EMBL login node, through an SSH tunnel (spectio-open or an SSH config entry) and a one-time token link; the runner starts each engine head in its own tmux session on that login node, the engine sends its tasks to SLURM, and the plugins' spool file in the run directory is read back into a SQLite index that the server can rebuild from the run directories; milestones M1 to M5 and §15.3 security requirements 1 to 7 are marked where they apply, above a to-scale strip of the 24 tasks](../assets/diagrams/p1_skeleton_light.png#only-light)
![The P1 walking skeleton: a laptop browser with the launch form, runs list and run detail with Cancel, refreshed over SSE, reaches spectio serve, in its own tmux session on an EMBL login node, through an SSH tunnel (spectio-open or an SSH config entry) and a one-time token link; the runner starts each engine head in its own tmux session on that login node, the engine sends its tasks to SLURM, and the plugins' spool file in the run directory is read back into a SQLite index that the server can rebuild from the run directories; milestones M1 to M5 and §15.3 security requirements 1 to 7 are marked where they apply, above a to-scale strip of the 24 tasks](../assets/diagrams/p1_skeleton_dark.png#only-dark)

*Note 2026-10-28: the figure predates Tasks 25 and 26 (M6, runs started from a terminal), Task 27 (M7, stages) and Tasks 28 to 32 (M8, job files and run tools).*

Step page: [Progress · P1](../progress/W4/P1.md).

**Goal:** the smallest Spectio a test user can run on the EMBL cluster: `spectio serve` in a tmux session on a login node, opened through an SSH tunnel with a one-time token link (by `spectio-open` or an SSH config entry), that launches the synthetic Nextflow or Snakemake pipeline (its head in its own tmux session on the login node, its tasks on SLURM), lists the runs, shows one run's state, task counts, stages (declared or detected, Task 27) and processes or rules, and whether its head is alive, as text and tables, and cancels it; it also monitors the runs that users start by hand from a terminal with the bridge enabled (Tasks 25 and 26).

**Architecture:** one process per user on the login node: a FastAPI app, an in-process runner thread and SQLite as an index in a node-local temporary directory, rebuilt from the run directories when it is missing ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts); Assumption 21). The runner writes a head script, starts it in its own tmux session on the login node, in the pane's foreground (or detached with `setsid` on the local executor in tests), watches its PID and exit files, and tails the event spool that the engine plugins write in the run directory. One writer thread validates spool events and projects them into `runs`, `tasks` and `attempts` in the same transaction. A three-screen React UI reads the API and refreshes over one SSE stream.

**Tech stack:** Python 3.13 (uv workspace), Pydantic 2, Typer, FastAPI + uvicorn, SQLAlchemy Core + Alembic on SQLite, `jsonschema`; Groovy (`nf-spectio`, built as in spike T2); React + Vite + Mantine 7 + TanStack Query; pytest, Vitest, Playwright (T6 skeleton); sind `slurm-mini`.

**Spec:** [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (what 0.0.1 contains) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (architecture and the seven security requirements); summary in [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md); decision log [2026-10-27, revised](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link), [2026-10-28, narrowed](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui) and [2026-10-28, head in tmux](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open); what P1 must handle: [R10 §3a](../reviews/R10-synthesis.md#3a-what-p1-must-handle-as-tasks-or-tests). Executors read the spec section named in each task.

**Process** *(assumed — pending Thomas, inbox #52, D0 (b))*: the [proposal](walking-skeleton-proposal.md)'s light process. Product code gets `review-code` (code-reviewer and security-reviewer, then code-simplifier); tooling and test-only changes get tests and one review. When code contradicts a spec, the owning spec changes in the same PR. One Progress page per milestone, not per task.

## Assumptions

Decisions taken in place of Thomas, who was not available for brainstorming. Each is *(assumed — pending Thomas)*; the inbox entry is named where one exists.

1. **D1, no relaunch, no parameter history** (inbox #61). The run detail shows its own parameters only. *(assumed — pending Thomas)* *Note 2026-10-28 (Thomas, "les 5 dans 0.0.1", [log](../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources)): Resume of a failed or cancelled run and Copy to a new launch are in 0.0.1 (Task 30); rerun from a stage, the relaunch dialog and the parameter history stay out.*
2. **D2, how a workflow reaches the form** (inbox #34, SR-056). The user types an absolute path to a pipeline directory that their own account can read. The engine is detected from the files: `main.nf` means Nextflow; `workflow/Snakefile` or `Snakefile` means Snakemake. The schema comes from `nextflow_schema.json`, or from `config.schema.yaml` / `workflow/schemas/config.schema.yaml`. Without a schema, the types are inferred from `config/config.yaml`, or the form falls back to key / value rows. There is no catalogue, no `POST /workflows`, no Git URL and no `POST /runs:validate` in P1. A `workflows` row (source `local`) and a `workflow_versions` row are created at launch. *(assumed — pending Thomas)*
3. **D3, what engine events may carry** (inbox #55, option (a)). `nf-spectio` sends no `script` or `env`. The SDK event models are allow-lists (`extra="ignore"`), so `script`, `env`, `homeDir`, `commandLine`, `configText` and Snakemake's `cmd` are never stored, even if a plugin sends them. *(assumed — pending Thomas)* *Note 2026-10-28: unchanged by Task 30. The command a run shows is the one the head script runs, built by Spectio, and Snakemake's `shellcmd` is not stored, so a Snakemake job has no script to show (inbox #70). The trace's resource fields, `workdir` and `native_id` are kept (Task 28, 29).*
4. **D4, Cancel** (inbox #62). One Cancel action: a cancel marker `.spectio/cancel` in the run directory, then an interrupt in the head's tmux pane (`tmux send-keys -t <pane id> C-c`), then SIGTERM to the head's process group if it is still alive after a 60 s grace period, then SIGKILL after another 60 s ([schedulers §3.1.1](../specs/schedulers-and-monitoring.md), tmux launcher). On the local executor: SIGTERM to the process group, then SIGKILL. *(assumed — pending Thomas)*
5. **Attempt state `aborted`** (inbox #56, option (a)). *(assumed — pending Thomas)*
6. **Stages and the processes or rules list, both** *(decided — Thomas, 2026-10-28; [log](../decisions/log.md#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list))*. The processes (Nextflow) or rules (Snakemake) list of Tasks 18 and 20 stays, in first-seen order, with task counts by state. Task 27 adds named stages: declared in a `spectio.yml` (the workflow's own, or a lab overlay file, [checking-scenarios §12.7](../specs/checking-scenarios.md)), else detected ([ui-spec §5.1.1](../specs/ui-spec.md)), else none; display only, no gates; names in no stage have `tasks.stage_id` null. State words, the header line, badges, the "Not in a stage" group, process names and the empty-state line: the [ui-spec §4.4 note of 2026-10-28](../specs/ui-spec.md#44-run-detail). The synthetic pipelines have no subworkflows, so they show no stages; the stage tests use the real-pipeline fixtures of `tests/pipelines/real/stages/`. *Note 2026-10-28: this replaces "stages are the processes or rules; detection and `run_stages` come later".* The naming of detected stages is *(assumed — pending Thomas, inbox #68)*.
7. **Live refresh over SSE** *(decided — Thomas, 2026-10-28; [log](../decisions/log.md#2026-10-28-001-live-refresh-over-sse-sqlite-as-a-rebuildable-index))*. The UI opens one stream per browser, `GET /api/v1/events/stream` ([api §8.3](../specs/api-and-data-model.md)), behind the session cookie; each frame names a run, and the UI refetches that run, or the first page of the list. The P1 subset sends one frame type, `spectio.run.delta`, and a keep-alive comment every 15 s. The `EventSource` cookie behaviour of §15.3 req. 3 is in scope and checked by the Playwright smoke (Task 20). *Note 2026-10-28: this replaces the assumption "No SSE in 0.0.1, the UI polls every 5 s".*
8. **A session-free bootstrap page.** §15.3 req. 2 asks for a session on every request, but something must serve the page that reads the ticket from the URL fragment. Four routes are served without a session cookie: `GET /auth/link` (static HTML) and `GET /auth/link.js`, which carry no data and need no credential; `POST /api/v1/auth/magic-links:exchange`, which needs a valid one-time ticket; and `POST /api/v1/auth/links`, which needs the server key (Assumption 9). *(assumed — pending Thomas; a spec gap to record in §15.3)*
9. **The state file and `spectio login --print-link`.** The server creates `~/.spectio/server.json` in the shared home with `O_EXCL` (login node, port, PID, database directory, start time; mode 0600; no secret) and removes it at a clean stop; `spectio serve` refuses to start on another login node while it names a server there, unless given `--force`, which replaces it ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)). `spectio login --print-link` reads it and the server key file in the node-local directory, checks that the listener on the recorded port belongs to the caller's uid (§15.3 req. 9), and calls `POST /api/v1/auth/links` with `Authorization: Bearer <server key>` and the loopback `Origin`. With `--json` it prints one line, a fixed sentinel then `{"ticket": …}`, for `spectio-open` (§15.3 req. 8). Run on another login node, where the server's loopback cannot be reached, it checks the node name from the state file, then prints "The server runs on <node>: run `ssh <node> spectio login --print-link`." and exits 2, with no link. *(assumed — pending Thomas)*
10. **Port.** The default is 8080 ([architecture §7.3](../specs/architecture-plugins-and-packaging.md)). When 8080 is taken (likely on a shared login node), `spectio init` picks a free port once and records it in `spectio.toml`, so an SSH config entry stays valid; `spectio init --port` changes it. If that port is taken at start, `spectio serve` refuses and names the port and the uid that holds it; it never picks another (§15.3 req. 9). *(assumed — pending Thomas)*
11. **Ingest and projection share one transaction on the writer thread**, and the spool cursor (file, byte offset) is a SQLite row written in that same transaction, not the `.spectio/events/.cursor` file of [architecture §13.1](../specs/architecture-plugins-and-packaging.md), which stays for a remote forwarder. `runs.projected_seq` therefore always equals `last_seq`. When the index is rebuilt (Assumption 21), the cursor starts again at 0 and event IDs make the replay idempotent. *(assumed — pending Thomas)*
12. **Spool numbers** (written into api §14 by Task 1): one JSON object per line; a line of at most 64 KiB; the writer rotates at 32 MiB; the reader ignores anything past 64 MiB in one file and counts it. *(assumed — pending Thomas, inbox #28)*
13. **One head script for both launchers.** `<launch>/.spectio/head.sh` runs under `setsid bash` on the local executor, and as the command of the tmux session's pane on the login node, in the pane's foreground and without `setsid` (Task 10). On both, it starts with a cleared environment that keeps only an allow-list (`HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG`, `TMPDIR`), then runs through the user's login shell (`bash -l`) so that their modules and `PATH` apply, as the `--export=NONE` head job did before: nothing from `spectio serve` or the tmux server (the `SPECTIO_*` settings, the server key path) reaches the engine. The security posture is unchanged. A trailer writes `.spectio/head.exit` (exit code, epoch), and the engine's output is copied to `.spectio/head.out` while the pane shows it. The script sets `SPECTIO_RUN_ID`, `SPECTIO_LAUNCH_N` and `SPECTIO_SPOOL_DIR`, and runs the engine command recorded at `spectio init` (Assumption 14). Parameters reach the engine as a file (`-params-file`, `--configfile`), never as shell words. *(assumed — pending Thomas)*
14. **Engines and their settings.** `spectio init` records how to run each engine: the `nextflow` and `snakemake` found on the login shell's `PATH`, or an explicit command (a full path, or `module load … && nextflow`), in `spectio.toml` `[engines]`. The task partition and account for the engines' SLURM executors are unset by default and configurable in `[slurm]`; the Nextflow head's heap is `NXF_OPTS=-Xmx2g` by default, configurable. The head watch (PID and exit file) runs every 5 s. *(assumed — pending Thomas)*
15. **Head end state.** While the PID check of [schedulers §3.1.1](../specs/schedulers-and-monitoring.md) matches, the head is alive; after that, `head.exit` gives its exit code, and a head gone with no `head.exit` (killed, or a login-node reboot) exited unknown. A head that ended with no terminal engine event within 60 s makes the run `failed`, class `head_lost` or `engine_fault` ([api §7.1](../specs/api-and-data-model.md)). *(assumed — pending Thomas, inbox #40)*
16. **Snakemake mapping** (api §7.2 says **[to be validated]**). `job_info` creates the task (rule + wildcards) and an attempt; `job_started` gives `running` (Snakemake reports no separate submit); `job_finished` gives `succeeded`; `job_error` gives `failed`. A `job_started` on the same `jobid` after a failure opens attempt n + 1 ([T2](../research/spike-engine-events-2026-10-28.md)). A Snakemake launch succeeds when the head exits 0 and no `error` record arrived. A Nextflow launch ends on `onFlowComplete.success`. *(assumed — pending Thomas)*
17. **Bridge delivery.** `nf-spectio` is unpacked into `$NXF_HOME/plugins/nf-spectio-<ver>/`, as [architecture §7.3](../specs/architecture-plugins-and-packaging.md) says. The Snakemake logger is copied to `<launch>/.spectio/pylib/` and put on `PYTHONPATH`, so compute nodes read it from the run directory. *(assumed — pending Thomas)*
18. **Minimal tenancy.** `spectio init` creates one principal (the Unix user), one project `default`, one environment (kind `slurm`, or `local` with `--local`) and its runner row. There are no groups. Every tenant row keeps `project_id` ([`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §4). *(assumed — pending Thomas)*
19. **Where the tests run.** The Playwright smoke runs against `spectio serve` on the local executor on the CI runner. The sind end-to-end tests drive the HTTP API from inside the submitter node, as a browser behind a tunnel would. *(assumed — pending Thomas)*
20. **Ultra-simple screens.** The launch form has no stepper, no review step and no file checks. Logs are the head stdout and stderr and the engine run log, last 64 KiB; per-task logs come later. Sessions last until the server restarts. *(assumed — pending Thomas)* *Reversed in part 2026-10-28 (Thomas: "Je veux également que ça soit possible de voir les logs globaux et les lots et stout err log sh et autres de chaque job si possible via workdir", [log](../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources)): each job's own files and its work directory are in 0.0.1 (Task 28), with the failure summary, Resume, results, the copy actions and resources (Tasks 29 to 32); the run logs keep the last 64 KiB.*
21. **The database is an index in a node-local temporary directory** (inbox #64, option (d)). At EMBL everything is shared between the login nodes except some temporary directories (Thomas, 2026-10-28). The data directory (`spectio.toml`, the state file; no secret) stays in `~/.spectio/`; the database, `serve.lock` and the server key go in `<node-local tmp>/spectio-<uid>/`, 0700, by default `$TMPDIR` or `/tmp`, with the `mkdtemp` fallback of §15.3 when that path is squatted (which path is node-local on the EMBL login nodes is **[to be validated]**). Each run directory holds the truth: the manifest `.spectio/run.json`, the spool, `head.pid`, `head.exit`, the cancel marker and `.spectio/launch-failed.json`. At boot the server reconciles the run directories missing from the index, which is all of them when the database is new, under the checks of §15.3 req. 10 ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) Where data lives). *(assumed — pending Thomas, inbox #64)*
22. **Runs started from a terminal** (Thomas, 2026-10-28, [log](../decisions/log.md#2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues)). A bridge started without `SPECTIO_RUN_ID` makes its own run ID, writes the spool in `<launch dir>/.spectio/events/`, and writes a pointer `~/.spectio/observed/<run ID>.json` only if `~/.spectio/` exists ([architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal)). The runner scans the pointers under §15.3 req. 12; the run gets origin `cli-observed` and is monitor only, with no Cancel (inbox #65). The bridges are released as [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) says, once Thomas has claimed the names (inbox #66); P1 builds and dry-runs the release packages only. *(assumed — pending Thomas)*

## Global Constraints

- Python 3.11–3.14 supported, tested on 3.13 (`PYTHON_VERSION` in `dev/versions.env`) ([architecture §7.3](../specs/architecture-plugins-and-packaging.md)).
- SQLite loaded by Python ≥ 3.51.3, or ≥ 3.50.7 / ≥ 3.44.6 in those series; checked at start ([api §7](../specs/api-and-data-model.md)).
- Nextflow ≥ 25.04 (tested 26.10.4, 25.10.9, 25.04.8); Snakemake ≥ 9.0 with `snakemake-interface-logger-plugins` `>=1.2,<3` (tested 9.27.1) ([architecture §13.4](../specs/architecture-plugins-and-packaging.md)).
- Package layout: `packages/spectio-sdk`, `packages/spectio`, `packages/spectio-server`, `packages/spectio-open` (laptop tool, standard library only; it depends on no other Spectio package and none depends on it), `engine-bridges/nf-spectio`, `engine-bridges/snakemake-logger-plugin-spectio`, `web/` ([architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout)). The runner never imports server code (import-linter); `spectio` has no FastAPI and no SQLAlchemy.
- IDs are ULID text with a type prefix (`run_`, `tsk_`, `att_`, `evt_`…); times are UTC; JSON is stored in `TEXT` ([api §7](../specs/api-and-data-model.md)).
- Run states: the full enum in the `CHECK` constraint; 0.0.1 uses `queued`, `running`, `cancelling`, `succeeded`, `failed`, `cancelled` ([api §7.1](../specs/api-and-data-model.md)). Attempt states: `pending`, `submitted`, `running`, `succeeded`, `failed`, `cached`, `stored`, `aborted`; states only move forward ([api §7.2](../specs/api-and-data-model.md)).
- Head: a tmux session `spectio-<run_id>` on the server's login node, never `sbatch` in 0.0.1; the server's own session is `spectio-server`; session names carry the run ID only ([schedulers §3.1.1](../specs/schedulers-and-monitoring.md), [decision log, 2026-10-28, head in tmux](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open)).
- Server: bound to `127.0.0.1` only; API under `/api/v1`; errors are RFC 9457 problem details ([api §4.1](../specs/api-and-data-model.md)).
- Secrets: ≥ 256 bits from `secrets`, compared with `hmac.compare_digest`; ticket valid 15 min, single use, in the URL fragment ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)).
- UI copy and labels: English; state words from [ui-spec §3.1](../specs/ui-spec.md); text and tables only, no chart, DAG or timeline ([log 2026-10-28](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui)).
- Every `feat` merged into `main` during 0.0.x carries the footer `Release-As: 0.0.1` ([dev-env §15.2](../specs/dev-environment-and-testing.md)).
- Every external fact added to a spec has a source, or is marked **[to be validated]** (`CLAUDE.md`).

## Review Focus

The five inputs most likely to hurt a test user that no other test covers. Each has its test in the task named.

1. **Parameter values or a pipeline path with spaces, quotes, `$(…)` or newlines.** They must never be interpreted by a shell: the values go into a params file, and paths are quoted with `shlex.quote`. Test: Task 9, `test_head_script_shell_metacharacters`.
2. **A spool line that is only partly written** (the engine is mid-append, or NFS shows a short file). It is not consumed and is read whole on the next tick. Test: Task 3, `test_partial_last_line_waits`.
3. **The head cannot start** (tmux missing, a session of that name already exists, the engine exits at once). The run ends `failed`, class `launch_error`, with the start of tmux's or the engine's stderr as its message, and nothing stays `queued`. Test: Task 10, `test_tmux_start_failure_fails_run`.
4. **The engine is missing, or older than the floor, at launch.** The run ends `failed`, class `engine_missing` or `engine_version`, with a message naming the binary and the version found. Test: Task 9, `test_engine_missing_and_too_old`.
5. **A link opened twice, after 15 minutes, or after a server restart.** The bootstrap page says "This link was already used or has expired. Run `spectio login --print-link` on the cluster for a new one.", not a blank page or raw JSON. Tests: Task 12, `test_reused_or_expired_link_message`, and the browser check in Task 20.

---

## Milestones

| Milestone | Tasks | Ends with |
|---|---|---|
| M1 · Events in | 1–7 | T2 fixtures and real local runs of both engines replay into SQLite with the right states |
| M2 · Heads | 8–10 | heads launched, watched, adopted and cancelled, locally and in tmux |
| M3 · Served safely | 11–16 | `spectio serve` in its tmux session, with the state file, the token link and §15.3 requirements 1–5 and 7 (6 is Task 3) |
| M4 · API and screens | 17–21 | the API of the four screens, the UI, and a wheel that carries the UI and both bridges |
| M5 · On the cluster | 22–24 | both engines end to end on `slurm-mini` in CI, with cancel and restart; the SSH config entry and `spectio-open` |
| M6 · Runs from a terminal | 25–26 | a run started by hand with the bridge enabled shows in the runs list, monitor only; both bridges build as release packages, dry-run only |
| M7 · Stages | 27 | the run detail shows named stages, declared or detected, above the processes or rules list, on the four example pipelines |
| M8 · Job files and run tools | 28–32 | each job's files and work directory, the failure summary with the SLURM state, resources per job, Resume and the copy actions, results and reports in a sandbox |

Commands assume the repository root, and that the uv workspace exists (after Task 1).

---

## M1 · Events in

### Task 1: Workspace and the spool event contract

**Spec:** api §14 (new: the driven-run part, inbox #36 (a)), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 6, [architecture §13.1](../specs/architecture-plugins-and-packaging.md) · **Depends on:** none · **R10 §3a:** rows 1, 4 (C2: first task)

**Files:**
- Create: `pyproject.toml` (uv workspace, members `packages/*`; ruff, mypy, pytest, import-linter config), `packages/spectio-sdk/pyproject.toml`, `packages/spectio-sdk/src/spectio_sdk/events.py`, `packages/spectio/pyproject.toml`, `packages/spectio-server/pyproject.toml` (empty packages with `__init__.py`)
- Create: `tests/fixtures/engine-events/convert_t2.py`, and its output `tests/fixtures/engine-events/*.spool.jsonl` (one per T2 fixture in `spikes/engine-events/fixtures/`)
- Modify: `docs/specs/api-and-data-model.md` (new §14, driven-run part only), `docs/decisions/log.md` (dated entry), `.github/workflows/ci.yml` (job `product`: `uv sync`, ruff, mypy, `lint-imports`, pytest; added to `ci-ok` needs)
- Test: `packages/spectio-sdk/tests/test_spool_events.py`

**Interfaces:**
- Produces: `SpoolEvent` (Pydantic, `extra="forbid"` on the envelope): `v: Literal[1]`, `id: str` (≤ 64 chars), `run: str` (`run_` + ULID), `launch: int ≥ 1`, `producer: str` (`nf-spectio/<ver>` or `snakemake-logger-spectio/<ver>`), `seq: int ≥ 1`, `time: datetime`, `type: str` (`nextflow.<hook>` or `snakemake.<event>`), `data: dict`. `parse_data(event) -> BaseModel` returns the allow-listed model of the type (`extra="ignore"`), or raises `UnknownEventType`. `MAX_LINE_BYTES = 65536`, `MAX_FILE_BYTES = 67108864`, `ROTATE_BYTES = 33554432`.

- [ ] **Step 1: Write the failing tests**

```python
def test_t2_fixtures_validate():                 # every converted line of all 15 fixtures parses
    for line in fixture_lines("*.spool.jsonl"): parse_data(SpoolEvent.model_validate_json(line))
def test_denylisted_fields_never_survive():      # D3: allow-list models drop them
    ev = make_event("nextflow.onTaskComplete", script="rm -rf", env={"K": "v"}, commandLine="x")
    assert not {"script", "env", "commandLine"} & parse_data(ev).model_dump().keys()
def test_envelope_rejects_unknown_keys_and_bad_run_id(): ...   # extra key, "run": "../x" → ValidationError
```

- [ ] **Step 2:** `uv run pytest packages/spectio-sdk/tests/test_spool_events.py -v`: FAIL (module missing).
- [ ] **Step 3: Write the spec, then the code.** First write api §14, "Driven runs (0.0.1)": envelope, file naming `.spectio/events/<producer>-<launch>-<nnnn>.jsonl`, the caps above, the per-type allow-lists, and "dropped and counted, never executed". Then write `events.py` from it, and `convert_t2.py`, which maps capture lines (`body.hook`, `body.seq`) and Snakemake `LogRecord` lines into envelopes, keeping the `<launch>` placeholders. Add the log entry "api §14 driven-run part written (inbox #36 a)".
- [ ] **Step 4:** the same command PASSES; `uvx --with mkdocs-material mkdocs build --strict` is clean.
- [ ] **Step 5: Commit** `feat(sdk): spool event contract (api §14, driven runs)`.

### Task 2: SQLite store and its discipline

**Spec:** [api §7](../specs/api-and-data-model.md) (tables, SQLite version rule), [architecture §7.2](../specs/architecture-plugins-and-packaging.md) (one writer, network file system refusal, the dated note on the rebuildable index) · **Depends on:** 1 · **R10 §3a:** row 11

**Files:**
- Create: `packages/spectio-server/src/spectio_server/store/{db.py,schema.py,writer.py}`, `packages/spectio-server/src/spectio_server/migrations/` (Alembic, one initial revision)
- Test: `packages/spectio-server/tests/test_store.py`

**Interfaces:**
- Produces: tables `principals`, `projects`, `environments`, `runners`, `runner_commands`, `workflows`, `workflow_versions`, `runs`, `run_inputs`, `launches`, `tasks`, `attempts`, `events`, `spool_cursors(launch_id, file, offset)`, `spool_drops(launch_id, reason, count)`. `default_db_dir() -> Path` (`$TMPDIR` or `/tmp`, then `spectio-<uid>`; `os.mkdir` 0700; an existing path is accepted only if, opened with `O_DIRECTORY|O_NOFOLLOW`, it is the same directory, owned by the user, with no group or other bits; otherwise `tempfile.mkdtemp(prefix=f"spectio-{uid}-")` with a warning naming the squatter's uid; never tightened). `open_db(db_dir: Path) -> tuple[Engine, bool]` (the flag is true when the database was created, so boot rebuilds it, Task 11; WAL, `busy_timeout=5000`, `auto_vacuum=INCREMENTAL` at creation; raises `UnsafeDatabase` on a network file system or an old SQLite). `Writer.submit(fn: Callable[[Connection], T]) -> Future[T]`: one thread, one connection, `BEGIN IMMEDIATE`. `fs_type(path, mounts=Path("/proc/self/mounts")) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
def test_refuses_network_fs(tmp_path):          # fake mounts table: tmp_path on "nfs4", then "lustre", "gpfs"
    with pytest.raises(UnsafeDatabase, match="nfs4"): open_db(tmp_path, mounts=fake_mounts(tmp_path, "nfs4"))
def test_refuses_old_sqlite(monkeypatch): ...   # sqlite_version "3.45.0" → UnsafeDatabase naming 3.51.3
def test_pragmas(tmp_path):                     # journal_mode == "wal", auto_vacuum == 2
def test_writer_serialises(tmp_path):           # 50 concurrent submits → 50 rows, no SQLITE_BUSY
def test_run_state_check_constraint(tmp_path):  # inserting state "paused_forever" raises IntegrityError
def test_default_db_dir_private(tmp_path, monkeypatch):  # TMPDIR=tmp_path → tmp_path/spectio-<uid>, mode 0700
def test_db_dir_squatted_falls_back(tmp_path, monkeypatch):  # a symlink there, a dir of another uid, or mode 0755 →
                                                # mkdtemp fallback, warning names the uid, the path untouched
def test_open_db_reports_created(tmp_path):     # first open → created True; second open → False
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/test_store.py -v`: FAIL.
- [ ] **Step 3:** implement as in the interfaces. The file system type comes from the longest mount prefix in `/proc/self/mounts`; the refused types are `nfs`, `nfs4`, `lustre`, `gpfs`, `beegfs`, `cifs`, `smb3`, `ceph`, `fuse.sshfs`. The refusal message names the type and the alternatives of architecture §7.2.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): SQLite store with one writer`.

### Task 3: Spool reader (§15.3 req. 6)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 6, api §14 (Task 1), [architecture §13.1](../specs/architecture-plugins-and-packaging.md) · **Depends on:** 1 · **R10 §3a:** rows 1, 2 (req. 6), 10

**Files:**
- Create: `packages/spectio/src/spectio/runner/{spool.py,types.py}` (`SpoolBatch` lives in `types.py`)
- Test: `packages/spectio/tests/test_spool_reader.py`

**Interfaces:**
- Consumes: `SpoolEvent`, `parse_data`, the caps (Task 1).
- Produces: `read_spool(launch_dir: Path, run_id: str, launch_n: int, cursor: dict[str, int], max_lines: int = 5000) -> SpoolBatch`, where `SpoolBatch(events: list[SpoolEvent], cursor: dict[str, int], drops: Counter[str])`. Pure: no database access; the caller stores `cursor` and `drops` in the same transaction as the events.

- [ ] **Step 1: Write the failing tests** (all named `test_req6_*` or after the Review Focus line)

```python
def test_req6_invalid_line_dropped_and_counted(tmp_path):     # "not json", wrong schema → drops["invalid"] == 2
def test_req6_oversized_line_dropped(tmp_path):               # 65537-byte line → drops["line_too_large"] == 1, next line read
def test_req6_file_cap(tmp_path):                             # bytes past MAX_FILE_BYTES ignored, drops["file_too_large"] == 1
def test_req6_other_run_id_dropped(tmp_path):                 # line with run != run_id → drops["wrong_run"]
def test_partial_last_line_waits(tmp_path):                   # no trailing "\n": not returned, cursor before it;
                                                              # after the append completes it is returned once
def test_symlinked_spool_file_refused(tmp_path):              # events/x.jsonl -> /etc/passwd: skipped, drops["symlink"]
def test_cursor_resumes_without_duplicates(tmp_path): ...     # two reads across a rotation → each id once
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_spool_reader.py -v`: FAIL.
- [ ] **Step 3:** implement `read_spool`. Open each file with `os.open(..., O_RDONLY | O_NOFOLLOW)` after checking that its real path is inside `launch_dir/.spectio/events/`. Read from the cursor offset; split on `\n` only; never `eval` or execute anything; iterate files in name order.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(runner): spool reader with caps and confinement`.

### Task 4: Projector, run state and Nextflow mapping

**Spec:** [api §7.1](../specs/api-and-data-model.md) (run transitions, the 0.0.1 subset), §7.2 (Nextflow mapping, `aborted`), §8.2 (lattice, double `onFlowComplete`), [synthesis §2ter](../specs/synthesis.md) (logical task key: process + tag) · **Depends on:** 2, 3 · **R10 §3a:** rows 1, 4, 7

**Files:**
- Create: `packages/spectio-server/src/spectio_server/projector/{ingest.py,runs.py,nextflow.py}`
- Modify: `packages/spectio/src/spectio/runner/types.py` (Task 3; add `HeadReport` and `Failure` here, on the runner side, so the runner never imports the server)
- Test: `packages/spectio-server/tests/test_projector_nextflow.py`

**Interfaces:**
- Consumes: `SpoolBatch` (Task 3), `Writer` (Task 2).
- Produces: `ingest(conn, launch_id: str, batch: SpoolBatch) -> None`. It inserts `events` (`seq` from `runs.last_seq`, `unique(run_id, event_id)`, duplicates ignored), projects them, and stores the cursor and the drop counts, in one transaction. Also `apply_head_report(conn, launch_id: str, report: HeadReport) -> None` (used by Tasks 9 and 10), `Failure(class_: str, message: str, task_id: str | None)` and `HeadReport(state: str, native_id: str | None, node: str | None, exit_code: int | None, ended: bool, failure: Failure | None)`. Run summary columns: `tasks_total`, `tasks_expected` (nullable), `counts` (JSON state → n).

- [ ] **Step 1: Write the failing tests** (replay the converted T2 fixtures)

```python
def test_flaky_26_10_4():      # 65 tasks all succeeded; 67 attempts, 2 failed; 2 tasks with attempts > 1; run succeeded
def test_toolerr_26_10_4():    # run failed; failure.message == "synthetic failure: tool exited with code 1";
                               # COMPARE treatA attempt failed; FINAL_REPORT attempt aborted, not counted as failed
def test_toolerr_25_10_9_double_flow_complete():  # one transition to failed, one run.state_changed event
def test_resume_26_10_4():     # 63 tasks cached: tests the `cached` state mapping only (resume is not in 0.0.1)
def test_forbidden_fields_never_stored():  # a line carrying script, env, commandLine, homeDir, configText, cmd →
                                           # none of them in the stored events row (D3, inbox #55)
def test_replay_is_idempotent():  # ingest the same batch twice → same counts, same last_seq
def test_terminal_state_never_moves_back():  # succeeded, then a late onTaskStart → still succeeded, the event is logged
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/test_projector_nextflow.py -v`: FAIL.
- [ ] **Step 3:** implement the transitions of api §7.1 that 0.0.1 uses: `queued → running` (head RUNNING or first event); `→ succeeded / failed` (Nextflow `onFlowComplete.success`); `queued → failed` (launch report); `running → failed` (`head_lost` or `engine_fault`, Assumption 15); `→ cancelling → cancelled`; a run in `cancelling` ends `cancelled` whatever the engine reports. When a launch ends, every open attempt becomes `aborted`. `failure.class` is `tool_error` when an attempt has `errorAction` `TERMINATE`, `engine_fault` otherwise.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): projector with run states and the Nextflow mapping`.

### Task 5: Snakemake mapping

**Spec:** [api §7.2](../specs/api-and-data-model.md) (Snakemake row, **[to be validated]**), [synthesis §2ter](../specs/synthesis.md) (rule + wildcards), [T2 results](../research/spike-engine-events-2026-10-28.md) · **Depends on:** 4

**Files:**
- Create: `packages/spectio-server/src/spectio_server/projector/snakemake.py`
- Test: `packages/spectio-server/tests/test_projector_snakemake.py`

**Interfaces:**
- Consumes: `ingest`, `apply_head_report` (Task 4).
- Produces: the Snakemake branch of `ingest`; `tasks_expected` from the last `progress.total`.

- [ ] **Step 1: Write the failing tests**

```python
def test_checkpoint_flaky_retry():  # no attempt left open; 2 failed attempts, each followed by a succeeded one
                                    # on the same task; tasks_expected == 67 (last progress.total)
def test_tool_error():              # head exit 1 → run failed, class tool_error, message from the last error record
def test_success_needs_head_exit_zero():  # all jobs finished, no head report yet → still running; exit 0 → succeeded
def test_untyped_records_ignored(): ...   # the 122 records without "event" change no state
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/test_projector_snakemake.py -v`: FAIL.
- [ ] **Step 3:** implement Assumption 16. Wildcards are sorted `k=v` pairs joined with `, `, so the tag matches the golden files.
- [ ] **Step 4:** the same command PASSES; Task 4's tests still pass.
- [ ] **Step 5: Commit** `feat(server): Snakemake event mapping`.

### Task 6: `nf-spectio` writes the spool

**Spec:** [architecture §13.1, §13.3, §13.4, §7.3](../specs/architecture-plugins-and-packaging.md) (spool, never throw, version floor, jar delivery), api §14 · **Depends on:** 1 · **R10 §3a:** rows 4, 5

**Files:**
- Create: `engine-bridges/nf-spectio/` (from `spikes/engine-events/nextflow/nf-spectio/` on branch `spike/engine-events`: `build.sh`, `src/spectio/SpectioPlugin.groovy`; the observer appends envelopes instead of posting), `engine-bridges/nf-spectio/tests/run_local.sh`
- Test: `packages/spectio/tests/test_bridge_nextflow.py` (marked `engines`; runs in `pipelines-synthetic.yml`)

**Interfaces:**
- Consumes: `SPECTIO_RUN_ID`, `SPECTIO_LAUNCH_N`, `SPECTIO_SPOOL_DIR`; envelope of Task 1.
- Produces: `build.sh <out-dir>` writes the unpacked plugin layout `nf-spectio-0.0.1/`. Hooks only enqueue, and one writer thread appends lines and rotates at `ROTATE_BYTES`. No `script` or `env` is sent (Assumption 3).

- [ ] **Step 1: Write the failing tests**

```python
def test_happy_local_spool_validates(nf_run):   # synthetic happy, local executor, Nextflow 26.10.4 → every line
                                                # passes SpoolEvent; replayed through ingest: run succeeded, 65 tasks
def test_no_script_or_env_keys(nf_run): ...      # raw lines contain neither '"script"' nor '"env"'
def test_unwritable_spool_never_fails_run(tmp_path):  # spool dir mode 0500 → Nextflow exits 0
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_bridge_nextflow.py -v -m engines`: FAIL.
- [ ] **Step 3:** port the observer and catch every `Throwable` in the writer, logging to `.spectio/bridge.err`. Put the 25.04 floor in the plugin's `requires`.
- [ ] **Step 4:** the same command PASSES on 26.10.4 and 25.10.9 (`NXF_VER` matrix in `pipelines-synthetic.yml`).
- [ ] **Step 5: Commit** `feat(bridges): nf-spectio writes the event spool`.

### Task 7: Snakemake logger plugin writes the spool

**Spec:** [architecture §13.1, §13.4, §7.3](../specs/architecture-plugins-and-packaging.md) (`PYTHONPATH` delivery), [dev-env §6](../specs/dev-environment-and-testing.md) (the interface's own suite) · **Depends on:** 1 · **R10 §3a:** row 5

**Files:**
- Create: `engine-bridges/snakemake-logger-plugin-spectio/snakemake_logger_plugin_spectio/__init__.py` (from the T2 spike; stdlib and the interface only), `engine-bridges/snakemake-logger-plugin-spectio/pyproject.toml`
- Test: `engine-bridges/snakemake-logger-plugin-spectio/tests/test_plugin.py`

**Interfaces:**
- Produces: a `LogHandler` subclass of `LogHandlerBase`, with a settings class named `LogHandlerSettings` and `writes_to_file = False` (T2: `baseFilename` crash). It converts `Namedlist` resources to dicts and writes envelopes `snakemake.<event>` to `$SPECTIO_SPOOL_DIR`.

- [ ] **Step 1: Write the failing tests**

```python
def test_interface_suite():                 # snakemake_interface_logger_plugins.tests against this plugin,
                                            # on interface 2.1.0 and the lowest 1.x of the range
def test_happy_local_spool_validates(smk_run):   # Snakemake 9.27.1 synthetic happy via PYTHONPATH, no install
def test_logger_added_not_replacing(smk_run):    # Snakemake's own log file still written
def test_unwritable_spool_never_fails_run(tmp_path): ...
```

- [ ] **Step 2:** `uv run --directory engine-bridges/snakemake-logger-plugin-spectio pytest -v`: FAIL.
- [ ] **Step 3:** port and harden as above.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(bridges): Snakemake logger plugin writes the event spool`.

---

## M2 · Heads

### Task 8: `spectio init` and `spectio doctor`

**Spec:** [architecture §7.3](../specs/architecture-plugins-and-packaging.md) (data directory, configuration layers, `spectio doctor`, 0.0.1 prerequisites), §7.2 (runs root), [api §6](../specs/api-and-data-model.md) (the one environment record) · **Depends on:** 2 · **R10 §3a:** rows 5, 8

**Files:**
- Create: `packages/spectio/src/spectio/cli/{main.py,init.py,doctor.py}`, `packages/spectio/src/spectio/config.py` (pydantic-settings: `spectio.toml`, then `SPECTIO_*`, then flags)
- Test: `packages/spectio/tests/test_init.py`, `packages/spectio/tests/test_doctor.py`

**Interfaces:**
- Produces:
  - `spectio init [--data-dir PATH] [--db-dir PATH] [--runs-root PATH] [--port N] [--local] [--partition P] [--account A] [--nextflow CMD] [--snakemake CMD]`, every option with a default so that `spectio-open` can run it unattended on first use (data directory `~/.spectio/`, database in `default_db_dir()`, Assumption 21; runs root `~/spectio-runs/` in the shared home); it resolves the engines through the login shell (Assumption 14), picks the port (Assumption 10), writes `spectio.toml` and creates the rows of Assumption 18 through the server store (the CLI imports `spectio_server` lazily; `spectio` alone says "install spectio[server]");
  - `Settings` with `data_dir`, `db_dir`, `runs_root`, `port=8080`, `slurm: SlurmOpts(partition: str | None, account: str | None)` (for the engines' task jobs), `engines.nextflow_cmd`, `engines.snakemake_cmd`, `engines.nxf_opts="-Xmx2g"`, `engines.extra_args`, `runner.head_watch_s=5`, `runner.spool_s=2`;
  - `spectio doctor`, which prints `ok|warn|fail <check> <detail>` lines and exits 1 on any `fail`.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_creates_one_environment(tmp_path):  # one project "default", one environment kind slurm with
                                                  # config.runs_root, one runner row; second init → no duplicate
def test_runs_root_must_exist_and_be_absolute(tmp_path): ...
def test_init_records_engine_commands(fakebin):  # nextflow on the login shell's PATH → its full path recorded;
                                                # --nextflow "module load X && nextflow" → kept as given
def test_doctor_reports_engines(fakebin):  # "ok nextflow 26.10.4 /…/nextflow", "fail snakemake not found on PATH"
def test_doctor_reports_fs_and_sqlite(tmp_path): ...  # db dir on nfs4 (fake mounts) → fail; SQLite version line
def test_init_defaults_unattended(tmp_path, monkeypatch):  # no flags, stdin closed → no prompt; data dir, db dir
                                                # and runs root take their defaults; spectio.toml records them
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_init.py packages/spectio/tests/test_doctor.py -v`: FAIL.
- [ ] **Step 3:** implement; `doctor` also checks `tmux` and `sbatch` on PATH (the engines submit with it), Java's major version, and the hostname pin recorded at init. `doctor` runs the network-file-system check and the 0700 check on the database directory, not on the data directory, which is in the shared home (Assumption 21); it also warns when the database directory is missing, since the next start rebuilds it.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(cli): spectio init and spectio doctor`.

### Task 9: Head script, local launcher and the runner loop

**Spec:** [schedulers §3.1.1](../specs/schedulers-and-monitoring.md) (detach, PID and exit files, adopt), [architecture §7.1](../specs/architecture-plugins-and-packaging.md) (in-process runner consumes `runner_commands`), [api §7](../specs/api-and-data-model.md) (`launches`, `runner_commands`) · **Depends on:** 4, 6, 7, 8 · **R10 §3a:** row 5 (engine checks)

**Files:**
- Create: `packages/spectio/src/spectio/runner/{headscript.py,engines.py,local.py,loop.py}`
- Test: `packages/spectio/tests/test_headscript.py`, `packages/spectio/tests/test_local_launcher.py`

**Interfaces:**
- Consumes: `HeadReport`, `Failure` (Task 4); `Settings`, `SlurmOpts` (Task 8).
- Produces:
  - `render_head_script(spec: LaunchSpec) -> str`, where `LaunchSpec(run_id, launch_n, engine, engine_cmd: str, location: Path, launch_dir: Path, work_dir: Path, profiles: list[str], params: dict, slurm: SlurmOpts | None, env: dict[str, str])`;
  - `check_engine(engine) -> EngineInfo(path, version)`, raising `EngineMissing` or `EngineTooOld`;
  - the `Launcher` protocol: `submit(spec) -> str` (native id), `poll(ids) -> dict[str, HeadReport]`, `cancel(native_id, grace_s: int = 60) -> None`, `adopt(launch) -> HeadReport`;
  - `write_run_manifest(run_dir: Path, manifest: RunManifest) -> None`: `.spectio/run.json` (run ID, name, workflow, parameters, profiles, creation time), written atomically when the run is created (called by Task 17), the file the index is rebuilt from (Assumption 21); the runner writes `.spectio/cancel` before a cancel interrupt and `.spectio/launch-failed.json` when a launch fails;
  - `LocalLauncher` (`setsid bash head.sh`; `.spectio/head.pid` holds PID, process group, leader start time, boot ID and host name, checked again before every signal);
  - `RunnerSink` (a protocol in `spectio/runner/types.py`, implemented by the server through its `Writer`, so the runner never imports the server): `lease_commands() -> list[Command]`, `ack(command_id: str, ok: bool, detail: str | None)`, `active_launches() -> list[LaunchRef]`, `cursor(launch_id) -> dict[str, int]`, `ingest(launch_id, batch: SpoolBatch)`, `head_report(launch_id, report: HeadReport)`;
  - `RunnerLoop(sink: RunnerSink, launcher: Launcher, tick_s: float = 2)`, which leases `runner_commands` (`launch`, `cancel`), reads spools (Task 3) and polls heads.

- [ ] **Step 1: Write the failing tests**

```python
def test_head_script_shell_metacharacters(tmp_path):  # location "/p/a b'$(x)", param "x\n$(rm -rf ~)" →
                                                      # `bash -n` OK; the value only in params.json; no "$(rm" in head.sh
def test_head_script_nextflow_args():   # "-params-file", "-plugins nf-spectio@0.0.1", "-c .spectio/spectio.config"
                                        # note 2026-10-28: how nf-spectio is loaded is open, inbox #69; mechanism unchanged
def test_head_script_snakemake_args():  # "--logger spectio", "--configfile", PYTHONPATH=<launch>/.spectio/pylib
def test_engine_missing_and_too_old(fakebin):  # no nextflow → class engine_missing; "24.10.0" → engine_version,
                                               # message names the path and the version
def test_local_launch_exit_file(tmp_path):     # trivial engine stub exits 3 → head.exit "3 …", HeadReport(exit_code=3)
def test_adopt_after_restart(tmp_path): ...    # new LocalLauncher sees the live PID (same start time and boot id) → adopted
def test_run_manifest_written(tmp_path): ...   # run.json round-trips to RunManifest; mode 0600
def test_cancel_and_launch_failure_markers(tmp_path): ...  # cancel → .spectio/cancel before the signal; missing
                                                # engine → launch-failed.json with class engine_missing
def test_cancel_never_signals_other_boot_id(tmp_path): ...  # head.pid with another boot ID or start time → no signal
def test_head_env_cleared(tmp_path, monkeypatch): ...  # SPECTIO_SERVER_X=1 in the runner's env → absent from the
                                                       # stub engine's env dump; HOME and the login PATH present
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_headscript.py packages/spectio/tests/test_local_launcher.py -v`: FAIL.
- [ ] **Step 3:** implement Assumptions 13 and 17. Bridges come from `bridge_dir() -> Path` (`importlib.resources` in an installed wheel, Task 21; `$SPECTIO_BRIDGES_DIR` pointing at the Task 6 and 7 build output in a checkout). Nextflow: write `.spectio/spectio.config` (`process.executor = 'slurm'` and `queue` on a SLURM environment) and unpack `nf-spectio` into `$NXF_HOME/plugins`. Snakemake: pass `--executor slurm` on SLURM, plus `--workflow-profile <location>/profiles/<p>` when a profile is given, plus the environment's `extra_args`. Run directories are `<runs_root>/<run_id>/{launch,work}`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(runner): head script, local launcher and runner loop`.

### Task 10: tmux launcher on the login node

**Spec:** [schedulers §3.1.1](../specs/schedulers-and-monitoring.md) (detach, PID and exit files, adopt; tmux launcher), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Launch, a person can take the head over), [decision log, 2026-10-28](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open) · **Depends on:** 9 · **R10 §3a:** rows 6, 12 (adoption)

**Files:**
- Create: `packages/spectio/src/spectio/runner/tmux.py`, `packages/spectio/tests/fakebin/tmux` (a fake that keeps its sessions in `$FAKE_TMUX_DIR` and runs the command detached, for unit tests)
- Test: `packages/spectio/tests/test_tmux_launcher.py` (unit, with the fake), `packages/spectio/tests/test_tmux_real.py` (marked `tmux`: runs only where a real `tmux` is on PATH, as on the CI runner and the sind submitter)

**Interfaces:**
- Consumes: the `Launcher` protocol, the head script and the PID file of `LocalLauncher` (Task 9), `HeadReport` (Task 4).
- Produces: `TmuxLauncher(tmux: str = "tmux")`, which implements `Launcher`: `submit` runs `tmux new-session -d -P -F '#{pane_id}' -s spectio-<run_id> -c <launch dir> bash <absolute head.sh>` (separate arguments) and returns the session name as the native id, recording the pane ID; every later call targets `=spectio-<run_id>` and `send-keys` targets the pane ID (§15.3 req. 11); only the tmux server is detached: the head runs in the pane's foreground process group, without `setsid`, so a Ctrl-C typed in the pane, or sent by `send-keys`, reaches the engine ([schedulers §3.1.1](../specs/schedulers-and-monitoring.md)); `poll` uses the PID check and `head.exit`; `adopt` matches the session name and the PID check; `cancel` sends `C-c` to the pane, then SIGTERM and SIGKILL to the head's process group (Assumption 4).

- [ ] **Step 1: Write the failing tests**

```python
def test_submit_creates_named_session(fake_tmux):     # argv "new-session -d -s spectio-<run_id>"; no sbatch, no setsid
def test_tmux_start_failure_fails_run(fake_tmux):     # tmux missing, or session exists → class launch_error,
                                                      # message starts with tmux's stderr; run not queued
def test_adopt_by_session_and_pid(fake_tmux):         # new launcher, session and PID check match → adopted, no second start
def test_head_stopped_by_hand(fake_tmux):             # the head exits 130 (Ctrl-C by a person) → HeadReport(exit_code=130)
def test_cancel_interrupt_then_term(fake_tmux): ...   # send-keys C-c; still alive after grace → SIGTERM, then SIGKILL
def test_targets_exact_and_pane_id(fake_tmux): ...    # every -t is "=spectio-<run_id>" or the recorded pane ID
def test_argv_never_single_string(fake_tmux): ...     # every tmux call is an argument list; no shell=True
def test_real_tmux_roundtrip(tmp_path): ...           # @pytest.mark.tmux: a stub engine in a real session; attach-able
                                                      # session listed by `tmux ls`; the head's process group is the pane's
                                                      # foreground group; send-keys C-c stops it; exit code from head.exit
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_tmux_launcher.py -v`: FAIL.
- [ ] **Step 3:** implement Assumptions 4, 13 and 15.
- [ ] **Step 4:** the same command PASSES, and `uv run pytest -m tmux packages/spectio/tests/test_tmux_real.py -v` PASSES where tmux exists.
- [ ] **Step 5: Commit** `feat(runner): tmux launcher on the login node`.

---

## M3 · Served safely

Each task below carries one §15.3 security requirement; its tests are named `test_req<N>_*` in `packages/spectio-server/tests/security/`. Requirement 6 is Task 3. `conftest.py` (Task 12) provides `app`, `client` (no session) and `authed_client` (session cookie, `Host: 127.0.0.1:8080`, matching `Origin`).

### Task 11: `spectio serve`, bind (§15.3 req. 1) and boot

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 1 and "Server restart", [architecture §7.1, §7.2](../specs/architecture-plugins-and-packaging.md) (boot order, one process) · **Depends on:** 3, 8, 9, 10 · **R10 §3a:** rows 2, 6, 12

**Files:**
- Create: `packages/spectio-server/src/spectio_server/{app.py,serve.py,rebuild.py}`, `packages/spectio/src/spectio/cli/serve.py`
- Test: `packages/spectio-server/tests/security/test_req1_bind.py`, `packages/spectio-server/tests/test_serve.py`

**Interfaces:**
- Consumes: `open_db`, `Writer` (Task 2), `RunnerLoop`, `RunnerSink` and the launchers (Tasks 9 and 10).
- Produces: `create_app(settings) -> FastAPI` and `serve(settings) -> None`. Boot takes `<db-dir>/serve.lock` (flock, on the node-local directory), opens the database and, when it was just created, rebuilds it from the run directories under the runs root (`rebuild_index(writer, runs_root) -> int`, in `spectio_server/rebuild.py`; Assumption 21), then adopts the heads, replays the spools, starts the runner loop, and starts uvicorn on `127.0.0.1` on the recorded port only (Assumption 10). At every boot it also reconciles run directories missing from the index, and marks the rebuild complete in its last transaction. It creates the state file `~/.spectio/server.json` with `O_EXCL` (Assumption 9) and the server key in the node-local directory and prints the start text below. `spectio serve --detach` starts the same process in the tmux session `spectio-server` and prints the same text in the calling terminal, never inside the pane.

```text
Spectio 0.0.1 is running on <hostname>, port <port>.
1. On your laptop, open a tunnel:  ssh -N -L 127.0.0.1:<port>:127.0.0.1:<port> <user>@<hostname>
2. Then open this link (single use, valid 15 minutes):
   http://127.0.0.1:<port>/auth/link#<ticket>
New link at any time: spectio login --print-link
```

- [ ] **Step 1: Write the failing tests**

```python
def test_req1_binds_loopback_only(settings):      # the listening socket's address is 127.0.0.1
def test_req1_refuses_other_bind(settings):       # host="0.0.0.0" in spectio.toml or SPECTIO_SERVER_HOST → exit 2,
                                                  # message "0.0.1 binds to 127.0.0.1 only"
def test_second_serve_refused(settings):          # serve.lock held → exit 2 naming the pid
def test_state_file_names_other_node(settings): ...  # server.json names a server on login2 → exit 2 naming login2;
                                                    # --force → starts and rewrites server.json
def test_detach_starts_tmux_session(fake_tmux): ...  # --detach → session spectio-server, link printed
def test_port_taken_refuses(settings): ...       # recorded port busy → exit 2 naming the port and the owning uid
def test_rebuild_from_run_dirs(settings, replayed_runs): ...  # two finished runs, one live head, one cancelled run and
                                                    # one failed launch; delete the database; boot → five runs
                                                    # from run.json, counts equal the golden, the live head adopted,
                                                    # cancelled and failed (launch_error) kept, no duplicate event_id
def test_boot_reconciles_missing_runs(settings): ...  # a run dir absent from an existing index → added at boot;
                                                    # a rebuild interrupted before its completion mark → redone
def test_rebuild_skips_symlinked_foreign_or_loose_dirs(settings): ...  # symlink, other uid, 0755, bad name → skipped
def test_rebuild_run_id_must_match_dir(settings): ...  # run.json run_id ≠ directory name → skipped, counted
def test_rebuild_ignores_manifest_session_and_paths(settings): ...  # extra keys → refused (extra=forbid); session
                                                    # name and paths derived from the run ID
def test_rebuild_caps(settings): ...               # more dirs or bytes than the per-boot caps → the rest next boot
def test_runs_root_loose_refused(settings): ...     # runs root group-writable or another owner → exit 2
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req1_bind.py packages/spectio-server/tests/test_serve.py -v`: FAIL.
- [ ] **Step 3:** implement. There is no `--host` flag; any other configured value aborts the start.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): spectio serve bound to loopback`.

### Task 12: Token link, secrets and sessions (§15.3 req. 2)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) "Access" and req. 2, [auth §2, §2.1](../specs/authentication-and-access.md) (ticket rules) · **Depends on:** 11 · **R10 §3a:** row 2

**Files:**
- Create: `packages/spectio-server/src/spectio_server/auth/{secrets.py,routes.py,middleware.py,static/link.html,static/link.js}`, `packages/spectio/src/spectio/cli/login.py`, `packages/spectio-server/tests/conftest.py`
- Modify: `docs/specs/api-and-data-model.md` (§5: `POST /auth/links`, `POST /auth/magic-links:exchange` and the bootstrap page `GET /auth/link`, so the OpenAPI snapshot of Task 18 matches a spec)
- Test: `packages/spectio-server/tests/security/test_req2_secrets.py`

**Interfaces:**
- Produces:
  - `ServerKey.generate(data_dir) -> ServerKey`, written to `server.key`, 0600, at each start;
  - `TicketStore.mint() -> str` (43 base64url characters; only its SHA-256 is kept, with an expiry) and `TicketStore.burn(ticket) -> bool`;
  - `SessionStore.create() -> str` and `SessionStore.valid(secret) -> bool` (in memory, `compare_digest` on digests);
  - routes: `POST /api/v1/auth/magic-links:exchange` (`{"ticket"}` → 204 and the cookie) and `POST /api/v1/auth/links` (server key → `{"url"}`);
  - middleware: 401 problem with no data on every other route, except the four of Assumption 8: `GET /auth/link` and `GET /auth/link.js` (no credential), `POST /api/v1/auth/magic-links:exchange` (a valid ticket) and `POST /api/v1/auth/links` (the server key);
  - `spectio login --print-link`.

- [ ] **Step 1: Write the failing tests**

```python
def test_req2_every_route_needs_session(client, app):  # every route of app.routes except the four exemptions → 401,
                                                       # body has no run data
def test_req2_secrets_256_bits():                      # ticket, session and key decode to ≥ 32 bytes; secrets used
def test_req2_ticket_single_use_and_15_min(client, clock):  # second exchange → 401; at +15 min 1 s → 401
def test_req2_ticket_stored_hashed(app): ...           # the store holds no plaintext ticket
def test_req2_server_key_only_for_links(client):       # server key as bearer on GET /api/v1/runs → 401
def test_reused_or_expired_link_message(client):       # 2nd exchange → 401 problem type ".../link-expired";
                                                       # GET /auth/link HTML holds the exact Review Focus 5 sentence
def test_login_print_link(cli, running_server): ...    # prints a working link; ticket removed from history
def test_print_link_on_other_node(cli, tmp_path): ...  # server.json names login3, hostname is login1 → exit 2,
                                                       # prints "ssh login3 spectio login --print-link", no request sent;
                                                       # a node "x;y" in server.json → refused, nothing printed
def test_print_link_refuses_foreign_listener(cli, tmp_path): ...  # recorded port held by another uid → exit 2, key not sent
def test_print_link_json(cli, running_server): ...     # --json → sentinel line, then {"ticket": <43 chars>}
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req2_secrets.py -v`: FAIL.
- [ ] **Step 3:** implement. `link.js` reads `location.hash`, calls `history.replaceState` to drop it, posts the exchange as JSON, then `location.replace("/")`. The bootstrap routes send `Cache-Control: no-store`, `Referrer-Policy: no-referrer` and `Content-Security-Policy: default-src 'self'`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): one-time token link and sessions`.

### Task 13: Session cookie (§15.3 req. 3)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 3 and the Jupyter cookie-name rule · **Depends on:** 12

**Files:**
- Modify: `packages/spectio-server/src/spectio_server/auth/routes.py`, `middleware.py`
- Test: `packages/spectio-server/tests/security/test_req3_cookie.py`

**Interfaces:**
- Produces: `cookie_name(host_header: str) -> str`, for example `"spectio_session_41234"` for `127.0.0.1:41234`, and `"spectio_session_80"` when `Host` has no port.

- [ ] **Step 1: Write the failing tests**

```python
def test_req3_attributes(client):          # Set-Cookie has HttpOnly, SameSite=Strict, Path=/; no Domain
def test_req3_name_has_host_port(client):  # Host 127.0.0.1:9001 → spectio_session_9001
def test_req3_other_port_cookie_ignored(client): ...  # a session cookie of port 9001 sent to Host :9002 → 401
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req3_cookie.py -v`: FAIL.
- [ ] **Step 3:** implement. The browser behaviours marked **[to be validated]** stay with spike sec-single-mode (R10 C6).
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): session cookie per host port`.

### Task 14: Host allow-list (§15.3 req. 4)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 4 · **Depends on:** 11

**Files:**
- Create: `packages/spectio-server/src/spectio_server/auth/host.py`
- Test: `packages/spectio-server/tests/security/test_req4_host.py`

**Interfaces:**
- Produces: `host_allowed(host_header: str | None) -> bool`. It accepts `127.0.0.1`, `localhost` and `[::1]`, on any port or none, case-insensitively. A request whose host is refused gets 421 or 400 before authentication, with no data.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("h", ["127.0.0.1:8080", "localhost:41234", "[::1]:5", "LOCALHOST"])
def test_req4_loopback_accepted(h): assert host_allowed(h)
@pytest.mark.parametrize("h", ["evil.example:8080", "127.0.0.1.evil.example", "0.0.0.0:8080",
                               "localhost.", "[::ffff:127.0.0.1]", "", None])
def test_req4_others_refused(h): assert not host_allowed(h)
def test_req4_refused_before_auth(authed_client): ...   # valid cookie + Host evil.example → refused, no data
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req4_host.py -v`: FAIL.
- [ ] **Step 3:** implement; this middleware runs first, also for the bootstrap routes.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): loopback Host allow-list`.

### Task 15: File modes (§15.3 req. 5)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 5 · **Depends on:** 8, 9, 12 · **R10 §4:** Q10 (group ACLs)

**Files:**
- Create: `packages/spectio/src/spectio/fsmodes.py` (`secure_dir(path) -> None` creates the data directory 0700 or tightens it; `write_secret(path, data) -> None` creates a temporary name with `O_CREAT|O_EXCL` 0600, writes, then renames)
- Modify: `init.py` (Task 8), `store/db.py` (Task 2), `auth/secrets.py` (Task 12), `runner/headscript.py` (Task 9)
- Test: `packages/spectio-server/tests/security/test_req5_modes.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_req5_data_dir_0700(initialised): ...                # stat mode & 0o777 == 0o700
def test_req5_key_and_db_files_0600(served): ...             # server.key, spectio.db, -wal, -shm, server.json
def test_req5_run_dirs_0700(launched): ...                   # <runs_root>/<run_id> and launch/, work/
def test_req5_umask_does_not_loosen(monkeypatch): ...        # with umask 000 the modes above still hold, and no file
                                                             # is wider than 0600 at any moment of its creation
def test_req5_key_not_in_shared_home(served): ...            # server.key in the node-local dir; nothing secret in ~/.spectio
def test_req5_existing_loose_dir_tightened_or_refused(tmp_path): ...  # data dir 0755 → 0700, with a warning (the node-local
                                                                      # directory is never tightened: Task 2)
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req5_modes.py -v`: FAIL.
- [ ] **Step 3:** implement; files are created with `os.open(..., 0o600)`, never chmod-ed after the write.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat: 0700 directories and 0600 secrets`.

### Task 16: Writes need Origin and JSON (§15.3 req. 7)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 7 (decided, inbox #37) · **Depends on:** 12, 14

**Files:**
- Create: `packages/spectio-server/src/spectio_server/auth/writes.py`
- Test: `packages/spectio-server/tests/security/test_req7_writes.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_req7_missing_origin_403(authed_client): ...     # POST /api/v1/runs/x:cancel without Origin → 403
def test_req7_foreign_origin_403(authed_client): ...     # Origin https://evil.example → 403
def test_req7_origin_port_must_match_host(authed_client): ...  # Host :8080, Origin http://127.0.0.1:9000 → 403
def test_req7_body_needs_json_415(authed_client): ...    # text/plain or form body on POST /api/v1/runs → 415
def test_req7_bodyless_cancel_needs_origin_only(authed_client): ...  # → not 403 and not 415
def test_req7_get_head_unaffected(authed_client): ...
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req7_writes.py -v`: FAIL.
- [ ] **Step 3:** implement; this check runs after the host and session checks and also covers the exchange and `auth/links`. There are no CORS headers on any route.
- [ ] **Step 4:** the same command PASSES; `uv run pytest packages/spectio-server/tests/security -v` is all green.
- [ ] **Step 5: Commit** `feat(server): Origin and JSON checks on writes`.

---

## M4 · API and screens

### Task 17: Launch API

**Spec:** [api §5, §5.2](../specs/api-and-data-model.md) (`POST /runs`, the 0.0.1 subset of its body: Assumption 2), [ui-spec §4.6](../specs/ui-spec.md) (where the form comes from) · **Depends on:** 9, 16 · **R10 §3a:** rows 3, 9

**Files:**
- Create: `packages/spectio-server/src/spectio_server/api/{workflows.py,runs_write.py}`, `packages/spectio-server/tests/data/{nf_schema_defs.json,nf_schema_definitions.json,smk_config.schema.yaml,smk_config.yaml}`
- Modify: `docs/specs/api-and-data-model.md` (§5: `GET /workflows:inspect` and the 0.0.1 body of `POST /runs`)
- Test: `packages/spectio-server/tests/api/test_launch.py`

**Interfaces:**
- Consumes: `authed_client`; `runner_commands` (Task 9).
- Produces:
  - `GET /api/v1/workflows:inspect?location=` → `{location, engine, name, version, engine_version, schema, schema_source: "nextflow_schema.json" | "config.schema.yaml" | "inferred" | "none", profiles: [str]}`; `version` is the pipeline's declared version, Nextflow `manifest.version` ("Project version number", [Nextflow config reference, `manifest`](https://docs.seqera.io/nextflow/reference/config/manifest); source `nextflow-io/nextflow` `docs/reference/config/manifest.mdx:130-132`, checked 2026-10-28), `null` for Snakemake, which has no version field in the workflow **[to be validated]**; `engine_version` is the version of the engine the server would launch with (UX-296);
  - `POST /api/v1/runs` with body `{workflow: {location}, name?, profiles?: [str], params: {}}` → `201` with the run (`state: queued`), a `Location` header and a `launch` row in `runner_commands` written in the same transaction, after the run directory and its manifest are written (`write_run_manifest`, Task 9); `422 validation-failed` with `errors: [{field, message}]` otherwise.

- [ ] **Step 1: Write the failing tests**

```python
def test_inspect_detects_engines(synthetic): ...  # tests/pipelines/synthetic/nextflow → nextflow, schema_source "none";
                                                 # …/snakemake → snakemake, profiles ["local", "slurm"]
def test_inspect_reads_schemas(): ...            # $defs and definitions (nf-core shapes) → one group each; config.yaml → inferred
def test_inspect_refuses_relative_or_missing(authed_client): ...   # 422 with field "location"
def test_launch_creates_run_and_command(authed_client, synthetic):  # 201; GET Location → queued; one launch command
def test_launch_validates_params(authed_client): ...  # schema says integer, value "x" → 422 errors[0].field == "params.chunks"
def test_launch_ambiguous_engine_422(tmp_path): ...   # both main.nf and Snakefile → 422
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/api/test_launch.py -v`: FAIL.
- [ ] **Step 3:** implement. Validate with `jsonschema` (draft 7 and 2020-12); the run's name defaults to `<workflow name>-<last 6 of id>`; params are stored as `run_inputs.kind = params`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(api): inspect a pipeline and launch a run`.

### Task 18: Read API, logs and Cancel

**Spec:** [api §5](../specs/api-and-data-model.md) (`GET /runs`, `GET /runs:summary`, `GET /runs/{id}`, `/processes`, `/tasks`, `/logs`, `GET /version`; the 0.0.1 subset in the dated note of 2026-10-28), [api §5.1](../specs/api-and-data-model.md) (`:cancel` source states), [api §8.3](../specs/api-and-data-model.md) (the stream, dated note 2026-10-28), [ui-spec §4.4](../specs/ui-spec.md#44-run-detail) (stages and process names, note 2026-10-28), [architecture §13.7](../specs/architecture-plugins-and-packaging.md) (log sources), [checking-scenarios §11.1](../specs/checking-scenarios.md) (confinement rule) · **Depends on:** 4, 5, 17 · **R10 §3a:** rows 9, 10; D4

**Files:**
- Create: `packages/spectio-server/src/spectio_server/api/{runs_read.py,logs.py,cancel.py,stream.py}`, `packages/spectio-server/openapi/0.0.1.json`
- Test: `packages/spectio-server/tests/api/test_read.py`, `packages/spectio-server/tests/api/test_cancel.py`, `packages/spectio-server/tests/api/test_stream.py`, `packages/spectio-server/tests/api/test_openapi.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/runs?state=&q=&sort=&limit=&cursor=` → `{items, next}`, newest first by `created_at`, or by `ended_at` with `sort=-ended_at` (home's runs that ended recently); `state` takes a comma-separated list of run states, `q` is a prefix of the run name, as in api §5; both feed the filters of the runs list (UX-296);
  - `GET /api/v1/runs:summary?group_by=state` → `{groups: [{key: <state>, count}]}` over all the user's runs, with no time window (`since=` and `project=` come later); it feeds the count cards of the home screen;
  - `GET /api/v1/version` → `{version, node, runs_root, account, executor: "slurm" | "local"}`: the Spectio version, the login node the server runs on, the runs root, the Unix account and the executor runs use; behind the session cookie in 0.0.1 (not public, Assumption 8); it feeds the shell's "server on <node>" line;
  - `GET /api/v1/runs/{id}` → `{id, name, state, origin: "ui" | "cli-observed", created_at, started_at, ended_at, workflow: {engine, engine_version, location, name, version}, profiles, params, failure, head: {session, node, alive, exit_code} | null, summary: {tasks_total, tasks_expected, counts}}`; `engine_version` is the version `check_engine` (Task 9) found at launch, or the pointer's for a `cli-observed` run (Task 25); `workflow.version` is the version the pipeline declares, from the bridge's start event (Nextflow `workflow.manifest.version` **[to be validated]**), `null` when it declares none (Snakemake declares none **[to be validated]**); `head` is `null` while the head has not started (`queued`); for a `cli-observed` run, `session` is `null` and `alive` is `null` when the head is on another node ("not checked", Task 25). No other fact (partition, queue, cluster name) is returned in 0.0.1; the run items of `GET /runs` carry the same fields but `params`;
  - `GET /api/v1/runs/{id}/processes` → `{items: [{process, stage_id, counts, retries}]}`, in first-seen order; `process` is the fully qualified Nextflow name, as `nf-spectio` reports it ([ui-spec §5.1.1](../specs/ui-spec.md#511-detected-stages)), or the Snakemake rule name, the key Task 27's `assign()` matches, and `stage_id` is `null` for a process in no stage ([ui-spec §4.4 note](../specs/ui-spec.md#44-run-detail));
  - `GET /api/v1/runs/{id}/stages` → `{items: [{id, position, name, source: "declared" | "detected", state, task_counts}]}` in `position` order, a subset of the `run_stages` row of [api §7](../specs/api-and-data-model.md); `id` is `run_stages.stage_id` (`detected:4`, or a `spectio.yml` stage id), the value the `/processes` items carry in `stage_id`; `state` is the stored `run_stages.state` of [ui-spec §5.1.1](../specs/ui-spec.md#511-detected-stages), shown with the words of the [ui-spec §4.4 note](../specs/ui-spec.md#44-run-detail); `{items: []}` when the run has no stage; Task 27 fills the rows (Assumption 6);
  - `GET /api/v1/runs/{id}/tasks?state=&process=&limit=&cursor=`;
  - `GET /api/v1/runs/{id}/logs?source=head-out|head-err|engine` → `text/plain; charset=utf-8`, the last 64 KiB;
  - `POST /api/v1/runs/{id}:cancel` → `202` with the run (`cancelling`) and a `cancel` command; `200` when it is already `cancelling` or terminal;
  - `GET /api/v1/events/stream` → `text/event-stream` (Assumption 7): `event: spectio.run.delta`, `data: {run_id, seq_through, counts, changed: {tasks}}`, a strict subset of api §8.5, one frame per committed change to a run (coalesced to at most one per run per second), and `: keep-alive` every 15 s; the writer thread publishes to an in-process broadcaster after each commit.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_detail_after_replay(authed_client, replayed_flaky): ...  # counts, processes in first-seen order, head null
def test_runs_paging(authed_client): ...        # 3 runs, limit=2 → 2 items + next; next page → 1 item, next null
def test_runs_filter_state_and_q(authed_client): ...  # state=running,queued → only those; q=rnaseq → only names starting with rnaseq
def test_runs_summary_by_state(authed_client): ...    # 2 running, 1 failed → groups running 2, failed 1; no since needed
def test_version_behind_session(client, authed_client): ...  # no cookie → 401; with it → version, node, runs_root, account, executor
def test_runs_sort_ended(authed_client): ...    # sort=-ended_at → ended runs, last ended first
def test_stages_ordered(authed_client, seeded_stages): ...  # run_stages rows inserted directly → items in position order, each with state and task_counts
def test_stages_empty(authed_client, replayed_flaky): ...  # no stage → {items: []}; processes carry stage_id null
def test_stages_source(authed_client, seeded_stages): ...  # source "declared" or "detected"; processes keyed by the fully qualified name
def test_run_versions_and_origin(authed_client, replayed_flaky): ...  # origin "ui", engine_version from check_engine,
                                                # workflow.version from the start event, null for Snakemake
def test_queued_run_head_null(authed_client): ...  # launched, head not started → state queued, head null
def test_logs_tail_and_sources(authed_client): ...  # 100 KiB head.out → last 65536 bytes; engine log per engine
def test_logs_confined(authed_client, tmp_path): ...  # .nextflow.log -> /etc/passwd symlink → 404 log-not-found
def test_cancel_states(authed_client): ...      # queued → 202 cancelling; cancelled → 200 unchanged; unknown → 404
def test_stream_needs_session(client): ...      # no cookie → 401 problem, no stream opened
def test_stream_delta_after_ingest(authed_client, writer): ...  # a spool batch committed → one spectio.run.delta
                                                # frame naming the run, its counts and the changed task IDs
def test_openapi_snapshot(app): ...             # app.openapi() == openapi/0.0.1.json (regenerate with --update)
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/api -v`: FAIL.
- [ ] **Step 3:** implement; log files are opened with `O_NOFOLLOW` after a real-path check under `launch_dir`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(api): runs, tasks, logs and cancel`.

### Task 19: UI shell and launch form

**Spec:** [ui-spec §4.6](../specs/ui-spec.md) (launch form, without stepper or review: Assumption 20), §3.1 (state words), [mvp-0.0.1 §1](../specs/mvp-0.0.1.md) (four screens), [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout) (React, Vite, Mantine 7, TanStack) · **Depends on:** 17 · **Boards:** Launch, LaunchSnakemake (reference only; boards show more than 0.0.1, UX-227)

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/src/{main.tsx,api.ts,routes.tsx}`, `web/src/launch/{LaunchPage.tsx,schemaFields.ts}`, `web/src/launch/schemaFields.test.ts`
- Modify: `packages/spectio-server/src/spectio_server/app.py` (serve `web/dist` at `/`, behind the session)

**Interfaces:**
- Consumes: `workflows:inspect`, `POST /runs` (Task 17).
- Produces: `schemaFields(schema: JSONSchema) -> Section[]` (`Section {title, fields: Field[]}`; `Field {key, label, type: "string" | "integer" | "number" | "boolean" | "enum" | "json", required, default, help}`). Routes `/` (home), `/runs`, `/launch` and `/runs/:id`; the shell shows the server's node from `GET /version` (Task 18). The page title is "Launch a workflow". The fields are Pipeline directory (absolute path) and Load, the detected engine, Profile, Run name (optional) and the parameters, with the Launch button disabled while a required field is empty, the reason shown beside it.

- [ ] **Step 1: Write the failing tests**

```ts
test("groups from $defs and definitions", () => expect(schemaFields(nfDefs).map(s => s.title)).toEqual(["Input/output", "Options"]));
test("hidden fields skipped, enums kept", () => /* hidden: true absent; enum → type "enum" */);
test("no schema → empty sections (key/value rows)", () => expect(schemaFields(null)).toEqual([]));
```

- [ ] **Step 2:** `npm --prefix web test`: FAIL.
- [ ] **Step 3:** implement. Use native `<input>` and `<button>` only and a label on every field (`CLAUDE.md` keyboard rule); key / value rows when `schema_source` is `none`. A 422 maps its errors onto the fields.
- [ ] **Step 4:** `npm --prefix web test` PASSES; `npm --prefix web run build` writes `web/dist`.
- [ ] **Step 5: Commit** `feat(web): UI shell and launch form`.

### Task 20: Runs list, run detail, Cancel, and the Playwright smoke

**Spec:** [api §8.3](../specs/api-and-data-model.md) (live refresh over SSE, decided 2026-10-28), [ui-spec §4.3](../specs/ui-spec.md) (columns in 0.0.1: Run, State, Workflow, Tasks, Started, Duration; no gauge, no Rows mode, no compare), §4.4 (header and Cancel; Summary and Tasks as tables; Logs; the stages note of 2026-10-28), §3.1, [ui-spec §11](../specs/ui-spec.md) (empty state) · **Depends on:** 18 (including `GET /runs:summary` for home), 19, step T6 (`tests/e2e/`, PR #45) · **R10 §3a:** row 13 (UX-211) · **Boards:** the 0.0.1 lite boards (`LiteHome`, `LiteRuns`, `LiteRunDetail`, `LiteRunObserved`, `LiteStatesRun` and their phone twins, [design/README](https://github.com/weber8thomas/spectio/blob/main/design/README.md#001-lite-boards)); RunsTable, RunDetail for reference only

**Files:**
- Create: `web/src/home/HomePage.tsx`, `web/src/runs/{RunsPage.tsx,RunDetailPage.tsx,stateWord.ts}`, `tests/e2e/skeleton.spec.ts` (in the T6 Playwright setup), `tests/e2e/serve-local.sh` (`spectio init --local` in a temp directory, `spectio serve`, prints the link)
- Modify: `.github/workflows/ci.yml` (job `e2e-local`: Nextflow and Snakemake from `dev/bootstrap.sh`, then Playwright)

**Interfaces:**
- Consumes: the read API and `:cancel` (Task 18).
- Produces:
  - the home screen at `/`: count cards by state from `GET /runs:summary?group_by=state`, the active runs, the runs that ended recently, and the pipeline directories of the recent runs (derived from `GET /runs`, no new endpoint), refreshed from the stream; the shell and every list say "live, updated N s ago" from the age of the last frame, and "Reconnecting…" while the `EventSource` reconnects;
  - the runs list, refreshed from the SSE stream of Task 18 (one `EventSource` per browser), with state filters and a name filter (`state=`, `q=`), "Load more", and a neutral "From a terminal" chip on `cli-observed` runs; its empty state reads "No runs yet." with a "Launch a workflow" button;
  - the run detail, refetched on each stream frame for its run until it is terminal:
    - a header: name, state word, short id, "n of m stages done · k running" for a run that has stages, and Cancel while `queued` or `running`, after a confirm "Cancel this run? Spectio interrupts its head in the tmux session, and the engine stops its tasks.";
    - a facts table: pipeline and its declared version, engine and its version, profile, started, ended, duration, the head (tmux session name, alive or exited, login node, exit code; "Head not started yet" while `head` is `null`), failure class and message;
    - a counts row, then the stages, or the flat processes or rules list when there is none, as the [ui-spec §4.4 note](../specs/ui-spec.md#44-run-detail) says (Assumption 6); `stateWord.ts` implements its state rule;
    - a `cli-observed` run: no Cancel, "head on <node>, not checked" and the engine log only (Task 25);
    - the tasks table (filter by state, and by process from `/processes`; on a failed run it defaults to `failed`), the parameters table, and the logs (head out, head err, engine log) loaded on click in `<pre>`.

- [ ] **Step 1: Write the failing test**

```ts
test("link → empty list → launch happy (Nextflow, local) → detail shows Succeeded and 65 tasks", async ({ page }) => { /* … */ });
test("home at / shows the count cards, the active runs and the runs that ended", async ({ page }) => { /* … */ });
test("the detail shows the flat list with no stage, and the stages when /stages has items", async ({ page }) => { /* route-mocked /stages */ });
test("cancel a running Snakemake run → Cancelled", async ({ page }) => { /* happy with a larger scale, so it still runs */ });
test("a reused link shows the expired message", async ({ page }) => { /* Review Focus 5 */ });
test("the detail updates without a reload as tasks finish", async ({ page }) => { /* SSE with the session cookie, §15.3 req. 3 */ });
test("a request without the cookie shows the 401 page, not data", async ({ page }) => { /* … */ });
```

- [ ] **Step 2:** `bash tests/e2e/serve-local.sh & npx --prefix dev/npm playwright test tests/e2e/skeleton.spec.ts` (T6's config): FAIL.
- [ ] **Step 3:** implement. Use the state words of ui-spec §3.1 and plain tables, with no chart.
- [ ] **Step 4:** the same command PASSES on the desktop and phone projects of T6; render the matching boards with `node tools/canvas/render.js` and compare by eye (no gate).
- [ ] **Step 5: Commit** `feat(web): runs list, run detail and cancel`.

### Task 21: One wheel with the UI and both bridges

**Spec:** [architecture §7.3](../specs/architecture-plugins-and-packaging.md) (UI in the wheel through a hatch hook; `nf-spectio` jar in the wheel; base install), [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout) (< 80 MB `spectio` environment) · **Depends on:** 6, 7, 20 · **R10 §3a:** row 5

**Files:**
- Create: `packages/spectio-server/hatch_build.py` (copies `web/dist`), `packages/spectio/hatch_build.py` (runs `engine-bridges/nf-spectio/build.sh` and copies the logger module into `spectio/_bridges/`), `tests/packaging/test_wheel.sh`
- Modify: the `.github/workflows/ci.yml` `product` job (build the wheels, run the test)

- [ ] **Step 1: Write the failing test** `tests/packaging/test_wheel.sh`. It builds with `uv build --all-packages`; installs with `uv tool install` from the built wheels into a temp `UV_TOOL_DIR`; asserts `spectio --version` prints `0.0.1`; that the wheel lists `spectio/_bridges/nf-spectio-0.0.1/` and `spectio/_bridges/snakemake_logger_plugin_spectio/__init__.py`; that `spectio_server/web/index.html` exists; and that the environment of `spectio` alone (without `[server]`) is under 80 MB.
- [ ] **Step 2:** `bash tests/packaging/test_wheel.sh`: FAIL.
- [ ] **Step 3:** implement the two hooks; the runner reads the bridges with `importlib.resources`.
- [ ] **Step 4:** the same command PASSES and prints `RESULT wheel pass`.
- [ ] **Step 5: Commit** `build: one wheel with the UI and both bridges`.

---

## M5 · On the cluster

### Task 22: End to end on `slurm-mini`: launch and monitor both engines

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (architecture), [dev-env §4.1](../specs/dev-environment-and-testing.md) (`slurm-mini`), [T3 note](../research/spike-t3-ci-2026-10-28.md) (Snakemake status-check delay) · **Depends on:** 21

**Files:**
- Create: `tests/slurm/e2e.sh` (subcommands `launch nextflow|snakemake`, `cancel <engine>`, `restart`; prints `RESULT e2e-<name> pass|fail`), `tests/slurm/e2e_client.py` (stdlib HTTP client: reads the link from `spectio login --print-link`, does the exchange with `Host` and `Origin`, launches, polls, compares counts)
- Modify: `.github/workflows/pipelines-slurm.yml` (an `e2e` matrix entry on `slurm-mini`; paths also `packages/**`, `engine-bridges/**`, `web/**`), `tests/scenarios/happy-slurm-mini.yaml` (`expect` lines become checked), `dev/slurm/cluster.sh` (installs `tmux` on the submitter node if its image lacks it; whether it does is **[to be validated]**)

**Interfaces:**
- Consumes: the wheel (Task 21), installed into `$SLURM_DATA/tools` as `dev/slurm/cluster.sh` expects; `inc` from `tests/slurm/scenarios.sh` (run as user `spx` on the submitter).
- Produces: `spectio init --runs-root $SLURM_DATA/runs --partition htc`, then `spectio serve --detach`, with `engines.extra_args.snakemake = ["--slurm-init-seconds-before-status-checks", "5"]` and `runner.head_watch_s = 5`.

- [ ] **Step 1: Write the failing test** (the harness). For each engine: launch the synthetic `happy` (params from `tests/pipelines/synthetic/scenarios.yaml`, profile `slurm`); expect `queued` → `running` with the head alive in the tmux session `spectio-<run_id>` on the submitter node (no `sbatch` for the head: the submit log of the engines' task jobs holds no `spectio-head-` name) → `succeeded`. The per-process counts must equal `tests/pipelines/synthetic/golden/{nextflow-26.10.4,snakemake-9.27.1}/happy.tsv`, the head end state comes from `head.exit`, `spool_drops` stays empty, and at the end `squeue --me` lists no job of the run and `tmux ls` no session `spectio-<run_id>`.
- [ ] **Step 2:** `bash dev/slurm/cluster.sh up mini && CLUSTER=mini bash tests/slurm/e2e.sh launch nextflow`: FAIL.
- [ ] **Step 3:** fix what the cluster reveals, each fix with a unit test in the task that owns the code.
- [ ] **Step 4:** `CLUSTER=mini bash tests/slurm/e2e.sh launch nextflow` and `… launch snakemake` print `RESULT e2e-launch-<engine> pass`; the `e2e` job is green in `pipelines-slurm.yml`.
- [ ] **Step 5: Commit** `test(slurm): end to end launch and monitor on slurm-mini`.

### Task 23: End to end Cancel and server restart

**Spec:** [schedulers §3.1.1](../specs/schedulers-and-monitoring.md) (tmux launcher: adopt, cancel), [dev-env §4.1](../specs/dev-environment-and-testing.md) (its note 2026-10-28: one cancel test per engine and a server restart while a head runs in tmux), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) "Server restart" · **Depends on:** 22 · **R10 §3a:** row 6; D4

**Files:**
- Modify: `tests/slurm/e2e.sh`, `tests/slurm/e2e_client.py`

- [ ] **Step 1: Write the failing tests**
  - `cancel <engine>`: launch `happy` with a larger `scale`, so it still runs; once `running` with tasks running, `POST :cancel`. Expect `cancelling` → `cancelled` within grace + 120 s, no job of the run in `squeue --me` (whether Nextflow's abort cancels its SLURM jobs is **[to be validated]** here), no session `spectio-<run_id>` left, and no attempt left `running` (they end `aborted` or `failed`).
  - `restart`: launch Nextflow `happy`; at the first `succeeded` task, kill `spectio serve` (SIGKILL), wait 20 s and start it again with `spectio serve --detach`. The head is adopted by its tmux session name and PID check (no second start: the launcher log shows one `new-session` for the run); the run ends `succeeded`; the counts equal the golden; `events` has no duplicate `event_id`; a new link is needed (the old cookie gets 401).
- [ ] **Step 2:** `CLUSTER=mini bash tests/slurm/e2e.sh cancel nextflow`: FAIL.
- [ ] **Step 3:** fix what the runs reveal (unit tests in the owning tasks).
- [ ] **Step 4:** `cancel nextflow`, `cancel snakemake` and `restart` print `RESULT … pass`, locally and in the `e2e` job.
- [ ] **Step 5: Commit** `test(slurm): cancel and restart on slurm-mini`.

### Task 24: Laptop access: the SSH config entry and `spectio-open`

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Access; One login node per server, and a state file), [decision log, 2026-10-28](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open) · **Depends on:** 11, 12 · **Added 2026-10-28 (Thomas)**

**Files:**
- Create: `packages/spectio-open/` (a package with no dependency beyond the Python standard library; console script `spectio-open`) with `src/spectio_open/{main.py,remote.py,config.py}`, `packages/spectio-open/tests/test_open.py`, `packages/spectio-open/tests/fakebin/ssh` (records argv, answers from fixtures), `docs/guides/open-from-your-laptop.md` (the SSH config entry and `spectio-open`, both paths side by side)
- Modify: `docs/specs/architecture-plugins-and-packaging.md` (§6: the `spectio-open/` row, already added 2026-10-28; adjust it if the code differs), `mkdocs.yml` (the guide in the nav), the `.github/workflows/ci.yml` `product` job (the new package's tests, and a check that it imports nothing outside the standard library)

**Interfaces:**
- Produces: `spectio-open <host> [--node NODE] [--remote-cmd CMD] [--local-port N] [--no-browser]`, under §15.3 req. 8; a per-cluster laptop configuration, `~/.config/spectio-open/clusters.toml` (`[<host>] node`, `remote_cmd`) read with `tomllib`; exit codes 0 (browser opened, tunnel up until Ctrl-C), 2 (remote `spectio` missing: prints the one-time install command), 3 (ssh failed).

- [ ] **Step 1: Write the failing tests**

```python
def test_reads_state_file_and_reaches_its_node(fake_ssh):   # server.json names login3 → tunnel argv targets login3
def test_node_flag_for_first_start(fake_ssh):              # no server.json, --node login2 → init if needed, then
                                                           # "spectio serve --detach" run on login2
def test_login_shell_and_remote_cmd(fake_ssh):             # remote commands run through "$SHELL -lc"; clusters.toml
                                                           # remote_cmd "module load spectio && spectio" used as given
def test_missing_remote_spectio_prints_install(fake_ssh):  # "spectio: command not found" → exit 2, prints the
                                                           # uv tool install line, runs no install
def test_rejects_bad_node_from_state_file(fake_ssh): ...  # node "-oProxyCommand=x", "a b", "x;y", "\x1b]0;" or
                                                           # non-ASCII → exit 3, ssh never called
def test_ssh_argv_has_double_dash(fake_ssh): ...           # "--" before the destination; no cluster value inside -o
def test_tunnel_argv_hardened(fake_ssh): ...               # -N, -o ExitOnForwardFailure=yes,
                                                           # -L 127.0.0.1:<lport>:127.0.0.1:<rport>, no host-key option
def test_remote_quoting_two_layers(fake_ssh): ...         # a remote_cmd with spaces and quotes reaches the remote shell
                                                           # intact (shlex.quote(shlex.join(argv)))
def test_url_built_locally(fake_ssh, monkeypatch): ...     # remote prints a URL to evil.example → ignored; the opened URL
                                                           # is http://127.0.0.1:<lport>/auth/link#<ticket>
def test_free_local_port_and_link(fake_ssh, monkeypatch): ...  # a free port; the ticket from --print-link --json
                                                              # opened with webbrowser.open, with the local port in it
def test_stdlib_only(): ...                                # every import in spectio_open is in sys.stdlib_module_names
```

- [ ] **Step 2:** `uv run pytest packages/spectio-open/tests -v`: FAIL.
- [ ] **Step 3:** implement. Remote commands are argument lists quoted with `shlex.quote(shlex.join(argv))` for the two shell layers, never strings built from user input. The guide gives the `Host` block (`HostName <login node>`, `LocalForward 127.0.0.1:<port> 127.0.0.1:<port>`) with the port that `spectio init` recorded (Assumption 10).
- [ ] **Step 4:** the same command PASSES; by hand, once, on an EMBL login node: `spectio-open <host>` opens home, and the SSH config entry does the same (recorded on the Progress page; nothing in CI reaches EMBL).
- [ ] **Step 5: Commit** `feat(open): spectio-open and the SSH config guide`.

---

## M6 · Runs from a terminal

### Task 25: Pointer file in both bridges; the server finds and shows the run

**Spec:** [architecture §13.8](../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 12 · **Depends on:** 6, 7, 9, 11, 18, 20 · **Added 2026-10-28 (Thomas)**

**Files:**
- Modify: `engine-bridges/nf-spectio/src/spectio/SpectioPlugin.groovy` and `engine-bridges/snakemake-logger-plugin-spectio/snakemake_logger_plugin_spectio/__init__.py` (run ID, spool file names, pointer, the fd-relative writes of req. 12), `packages/spectio/src/spectio/runner/loop.py` (scan when `observed/` changes), `packages/spectio-server/src/spectio_server/rebuild.py` (read the pointers), `packages/spectio-server/src/spectio_server/api/{cancel.py,logs.py}` (422 on a `cli-observed` run, [api §5.1](../specs/api-and-data-model.md) note; the log checks of req. 12), `web/src/runs/{RunsPage.tsx,RunDetailPage.tsx}` (the "started from a terminal" mark; no Cancel), `tools/docs/check.py` (install lines pin versions), `mkdocs.yml`
- Create: `packages/spectio/src/spectio/runner/observed.py`, `docs/guides/runs-from-a-terminal.md` (the setup of architecture §13.8; merged only once the names are claimed, inbox #66; how `nf-spectio` is loaded is open, [inbox #69](../reviews/inbox.md#69-nf-spectio-is-enabled-in-a-way-that-breaks-nf-core-runs-or-drops-the-bridge), note 2026-10-28)
- Test: `packages/spectio/tests/test_observed.py`; the bridge tests of Tasks 6 and 7

**Interfaces:**
- Produces: `scan_observed(home: Path, runs_root: Path, known: set[str], cap: int) -> list[ObservedRun]`; the writer thread creates each new run with `origin = 'cli-observed'`. The pointer's PID fields feed the head-alive check of Task 9 only when its boot ID is the server's; nothing sends them a signal.

- [ ] **Step 1: Write the failing tests**

```python
# bridges (Tasks 6 and 7 test files, marked engines; each also as *_snakemake with smk_run)
def test_terminal_run_writes_pointer(tmp_home, nf_run): ...   # no SPECTIO_RUN_ID → ~/.spectio/observed/run_<ULID>.json,
                                                             # 0600, run ID = file name, spool <run ID>-<producer>-0001.jsonl
def test_no_spectio_home_run_unaffected(tmp_home, nf_run): ...   # no ~/.spectio → no pointer, spool written, exit 0
def test_unwritable_home_run_unaffected(tmp_home, nf_run): ...   # ~/.spectio/observed mode 0500 → exit 0
def test_driven_run_writes_no_pointer(tmp_home, nf_run): ...     # SPECTIO_RUN_ID set → no pointer
def test_bridge_refuses_foreign_spectio_dir(tmp_home, nf_run): ...  # .spectio a symlink, other owner or 0777, bridge.err a
                                                             # symlink → nothing written outside, targets unchanged, exit 0
def test_loose_spectio_home_no_pointer(tmp_home, nf_run): ...    # ~/.spectio 0777 or a symlink → no pointer
def test_pointer_keys_exact(tmp_home, nf_run): ...               # keys are exactly those of architecture §13.8

# packages/spectio/tests/test_observed.py
def test_scan_finds_pointer(tmp_home): ...                   # valid pointer → one ObservedRun; its spool replays to succeeded
def test_req12_pointer_checks(tmp_home): ...                 # symlink, other owner, group/other bits, > size cap, bad JSON,
                                                             # extra keys, run ID ≠ file name → skipped and counted
def test_loose_observed_dir_not_scanned(tmp_home): ...       # observed/ 0777 → warning, server starts, nothing read
def test_pointer_cannot_alias_driven_run(tmp_home): ...      # run ID of a run directory, relative or unnormalised launch dir,
                                                             # launch dir under the runs root → skipped and counted
def test_group_writable_launch_dir_accepted(tmp_home): ...   # launch dir 0770, its .spectio 0700 → read
def test_spectio_dir_swapped_after_check_not_read(tmp_home): ...  # .spectio replaced by a symlink after the check → no read
def test_terminal_log_symlink_fifo_foreign_refused(tmp_home): ... # .nextflow.log a symlink, a FIFO or foreign → "log not readable"
def test_two_terminal_runs_same_launch_dir_kept_apart(tmp_home): ...  # two runs, one launch dir → each its own events only;
                                                             # an envelope for the other run is dropped and counted
def test_terminal_run_other_boot_id_never_head_lost(tmp_home): ...  # boot ID differs → "not checked", stays running
def test_runner_never_signals_cli_observed(tmp_home): ...    # boot reconciliation included: no launcher or tmux call
def test_scan_skips_unchanged_dir(tmp_home): ...             # observed/ mtime unchanged → not listed again
def test_ended_pointer_moved(tmp_home): ...                  # terminal event → pointer moved to observed/ended/
def test_scan_cap(tmp_home): ...                             # 10 000 pointers → at most the cap read per scan
def test_rebuild_keeps_terminal_run_id(tmp_home): ...        # index deleted → same run ID after rebuild, ended/ included
def test_server_down_events_wait(tmp_home): ...              # run ends while no server → read whole at next start
def test_terminal_run_has_no_cancel(client): ...             # POST :cancel on a cli-observed run → 422 not-in-this-version

# docs check
def test_guide_pins_bridge_versions(): ...                   # every install line in the guide pins ==<ver> or nf-spectio@<ver>
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_observed.py -v`: FAIL.
- [ ] **Step 3:** implement. The pointer is written under a temporary name with `O_CREAT|O_EXCL`, then renamed; any error is logged once and swallowed (architecture §13.3).
- [ ] **Step 4:** the same command PASSES, and the bridge tests PASS with `-m engines`; the Playwright smoke of Task 20 gains one terminal run that shows the mark and no Cancel.
- [ ] **Step 5: Commit** `feat(runner): show runs started from a terminal`.

### Task 26: Release packages of both bridges, dry-run only

**Spec:** [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) (Publishing), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 12 (Release), [architecture §13.4](../specs/architecture-plugins-and-packaging.md) (version ranges) · **Depends on:** 6, 7, 21 · **Added 2026-10-28 (Thomas)**

**Files:**
- Modify: `engine-bridges/nf-spectio/` (Gradle build with a pinned `io.nextflow.nextflow-plugin` and a Gradle wrapper with `distributionSha256Sum`; plugin ID `nf-spectio`, version `0.0.1`, `requires` from §13.4), `engine-bridges/snakemake-logger-plugin-spectio/pyproject.toml` (name, version, `snakemake-interface-logger-plugins` range, `docs/intro.md` for the catalogue page)
- Create: `tests/packaging/test_bridges_release.sh`

- [ ] **Step 1: Write the failing test** `tests/packaging/test_bridges_release.sh`. With a fresh, empty `GRADLE_USER_HOME`, it builds the Nextflow plugin zip and checks its manifest (ID, version, `requires`); it builds the Snakemake sdist and wheel with `uv build`, runs `twine check --strict`, installs the wheel into a fresh Snakemake 9 environment and runs a local synthetic `happy` with `--logger spectio`. It checks that no artefact holds a secret (`npr.apiKey`, a PyPI token, a `gradle.properties`), never runs `make release` or `twine upload`, and fails if `npr.apiKey` or a PyPI token is set in its environment.
- [ ] **Step 2:** `bash tests/packaging/test_bridges_release.sh`: FAIL.
- [ ] **Step 3:** implement the two builds.
- [ ] **Step 4:** the same command PASSES and prints `RESULT bridges-release dry-run pass`. The real release runs from CI or a laptop, never the cluster, once Thomas has claimed the names (inbox #66).
- [ ] **Step 5: Commit** `build(bridges): release packages for the Nextflow registry and PyPI`.

---

## M7 · Stages

### Task 27: Stages, declared or detected, above the processes or rules list

**Spec:** [ui-spec §5.1 and §5.1.1](../specs/ui-spec.md) (sources, detection rules, order and state), [checking-scenarios §12.1](../specs/checking-scenarios.md) (`stages[]`, what `match` sees) and §12.3 (overlaps), [api §7](../specs/api-and-data-model.md) (`run_stages`, `tasks.stage_id`, `summary.stage_mode`; when detected stages freeze), [api §5](../specs/api-and-data-model.md) (`GET /runs/{id}/stages`); evidence: [stage-detection spike](../research/spike-stage-detection-2026-10-28.md) · **Depends on:** 4, 5, 18, 20, 25 · **Added 2026-10-28 (Thomas, [log](../decisions/log.md#2026-10-28-001-shows-stages-declared-or-detected-and-the-processes-or-rules-list))**

**Files:**
- Create: `packages/spectio-sdk/src/spectio_sdk/stages.py` (the `stages[]` model of `spectio.yml`, read from the workflow's own file or from a lab overlay file in `~/.spectio/overlays/`, matched to the run as [checking-scenarios §12.7](../specs/checking-scenarios.md) (note 2026-10-28) says; no editor), `packages/spectio-server/src/spectio_server/stages/{detect_nf.py,detect_smk.py,assign.py,state.py}`, `packages/spectio-server/tests/test_stages.py`, `tests/pipelines/real/stages/expected/*.json` (from the spike's `out/*_detected.json`; the freeze tests replay `tests/pipelines/real/stages/events/rnaseq-3.27.0_star_salmon_preview_events.jsonl`, and build events from the other `processes/*.txt` lists)
- Modify: the projector of Tasks 4 and 5 (freeze `run_stages` at the first `onFlowBegin` or `workflow_started`; set `tasks.stage_id`; stage state on each event), the store schema of Task 2 (`run_stages`, `tasks.stage_id`), the head script of Task 9 (Snakemake only: `snakemake --list-rules` with the run's configuration into `.spectio/rules.txt` before the engine starts; a failure there is logged and ignored; it prints `name (docstring)`, so the reader strips a trailing ` (…)`), the read API of Task 18 (fills Task 18's `/stages` subset from `run_stages`, plus `summary.stage_mode`; no new route), `web/src/runs/RunDetailPage.tsx` (Task 20: stages and the processes or rules, per [ui-spec §4.4](../specs/ui-spec.md))

**Interfaces:**
- Produces: `detect_nextflow(process_names: list[str], manifest_name: str | None, meta: Mapping[str, str]) -> list[StageDef]` and `detect_snakemake(main_snakefile: Path, defined: set[str] | None) -> list[StageDef]`, pure functions with a cap of 8; `assign(stages: list[StageDef], name: str) -> str | None` (the one stage whose `match` matches, with `fnmatchcase` on the fully qualified name, since §12.3 refuses overlaps; `None` leaves `tasks.stage_id` null). `StageDef` has `id`, `name`, `source` (`declared` or `detected`), `description`, `match`.
- The Snakemake detector reads source files as the server's user, on the run's pipeline directory only: regular files, no symlink leaving the directory of the main Snakefile, at most 200 files of 1 MiB each; for a run started from a terminal, `snakefile_main` is untrusted input under [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 12, and a path that fails the checks gives no detected stages. The server never runs `snakemake` itself. *(assumed — pending Thomas)*

- [ ] **Step 1: Write the failing tests**

```python
# packages/spectio-server/tests/test_stages.py — golden tests on tests/pipelines/real/stages/
def test_detect_nf_golden(fixture): ...          # rnaseq star_salmon (67 → 8), rnaseq hisat2 (62 → 8), sarek (48 → 8),
                                                 # methylseq bismark (13 → 4), bwameth (15 → 5): == expected/*.json
def test_detect_nf_without_manifest(fixture): ...   # manifest name None → the same stages on all five lists
def test_detect_nf_flat_none(): ...              # the synthetic happy process list → []
def test_detect_nf_report_kept(fixture): ...     # MULTIQC is its own last stage "Report" after the cap
def test_detect_smk_golden(fixture): ...         # mosaicatcher v2.5.1 source + list-rules (101 rules → 8) == expected
def test_detect_smk_source_only(fixture): ...    # no rules.txt → 204 rules, 8 stages, Final targets last
def test_rules_txt_docstrings_stripped(tmp_path): ...  # "count_reads (Count reads per bin)" → "count_reads"
def test_detect_smk_unsafe_path(tmp_path): ...   # symlink out of the pipeline dir, > 200 files, FIFO → [] and a warning
def test_overlay_assign_golden(fixture): ...     # the four overlays: every name assigned, no overlap
def test_overlay_overlap_refused(fixture): ...   # two stages match one name → the overlay is refused with both stage ids
def test_overlay_matching(tmp_home): ...         # ~/.spectio/overlays/: name and engine match, version out of range,
                                                 # two files match → none applied (checking-scenarios §12.7 note)
def test_declared_beats_detected(fixture): ...   # an overlay for the pipeline → source declared; none → detected
def test_stages_frozen_at_flow_begin(replayed): ...  # onProcessCreate after onFlowBegin → no new stage, stage_id null
def test_stage_states(replayed): ...             # running on first task, completed, skipped with no task, failed
def test_stages_route(authed_client, replayed): ...  # Task 18's GET /api/v1/runs/{id}/stages: items {id, position, name,
                                                 # source, state, task_counts} in position order; stage_id on /processes items; stage_mode
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/test_stages.py -v`: FAIL.
- [ ] **Step 3:** implement, starting from the spike's `detect_nf.py` and `detect_smk.py` (branch `spike/stage-detection`), as typed pure functions.
- [ ] **Step 4:** the same command PASSES; the Playwright smoke of Task 20 gains a check that a run of the synthetic `happy` shows no stage and its processes, and a run directory seeded with the rnaseq fixture's events (read at boot, Task 11) shows 8 detected stages above its processes.
- [ ] **Step 5: Commit** `feat(server): stages, declared or detected, above the processes list`.

---

## M8 · Job files and run tools

*Added 2026-10-28 (Thomas: "Je veux également que ça soit possible de voir les logs globaux et les lots et stout err log sh et autres de chaque job si possible via workdir", then "les 5 dans 0.0.1"; [log](../decisions/log.md#2026-10-28-001-shows-each-jobs-files-and-gains-resume-failure-summary-results-copy-and-resources)).* Each job's files and the work directory (Task 28), the failure summary and resources per job (Task 29), Resume and the copy actions (Task 30), results and reports (Task 31), and their screens (Task 32). Specs: [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine) (files, failure reason, resources), [api §5 and §5.1](../specs/api-and-data-model.md) (notes 2026-10-28), [ui-spec §4.4](../specs/ui-spec.md#44-run-detail) (note 2026-10-28, run tools), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13 to 16. *(assumed — pending Thomas, inbox #70)*

### Task 28: Each job's files and the work directory

**Spec:** [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine), [api §5](../specs/api-and-data-model.md) (note 2026-10-28, Job files), [checking-scenarios §11.1](../specs/checking-scenarios.md) (confinement), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13 · **Depends on:** 4, 5, 6, 7, 9, 18

**Files:**
- Create: `packages/spectio-server/src/spectio_server/files/{confine.py,taskfiles.py,redact.py}`, `packages/spectio-server/src/spectio_server/api/taskfiles.py`
- Modify: `nf-spectio` (Task 6: send `workdir` and `native_id` with each task event, and return `true` from `enableMetrics()`), the Snakemake logger plugin (Task 7: keep `log` from `job_info`, `log` and `aux.external_jobid` from `job_error`, and the SLURM ID and log path from the submission info text, with a regular expression versioned per `snakemake-executor-plugin-slurm` release), the projector of Tasks 4 and 5 (store `attempts.work_dir`, `attempts.native_id` and the Snakemake log paths, each kept only when it resolves under a root of the run, req. 13), the head script of Task 9 (Nextflow: `NXF_LOG_FILE=<run dir>/.spectio/nextflow.log`; Snakemake on SLURM: `--slurm-keep-successful-logs`), the logs route of Task 18 (the engine log path from the run, not a fixed name)
- Test: `packages/spectio-server/tests/test_taskfiles.py`, `packages/spectio-server/tests/api/test_taskfiles_api.py`

**Interfaces:**
- Produces: `open_confined(roots: list[Path], rel: PurePosixPath) -> BinaryIO` (raises `NotAllowed`, `NotFound`), `tail(f, max_bytes: int = 65536) -> bytes`; `list_task_files(attempt) -> list[TaskFile]`; `redact_command_run(text: str) -> str`; the routes `GET /api/v1/tasks/{id}/attempts/{n}/files` and `…/files/{name}` of [api §5](../specs/api-and-data-model.md) (note 2026-10-28).

- [ ] **Step 1: Write the failing tests**

```python
def test_nf_allow_list(nf_workdir): ...          # files lists .command.log/err/out/sh/run, .exitcode, .command.begin/trace;
                                                 # never .command.env/.in/.stage or a staged input
def test_nf_file_tail(authed_client, nf_workdir): ...   # 100 KiB .command.err → last 65536 bytes, text/plain, nosniff
def test_command_run_redacted(nf_workdir): ...   # export TOKEN="abc" → export TOKEN=«hidden»; #SBATCH lines kept
def test_array_task_has_no_log(nf_workdir): ...  # native_id 8812345_3 and no .command.log → state absent, note
def test_cleaned_workdir_410(authed_client): ... # work directory gone → 410 log-cleaned
def test_not_written_yet(authed_client): ...     # running attempt, no .exitcode → state not_yet, no error
def test_smk_rule_and_slurm_logs(smk_run): ...   # job_info log + submission text → rule log and
                                                 # .snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731209.log
def test_smk_job_error_paths(smk_run): ...       # job_error log and aux.external_jobid recorded on the attempt
def test_smk_deleted_after_success(smk_run): ... # SLURM log missing on a succeeded job → deleted_after_success
def test_forged_paths_dropped(replayed): ...     # workdir /etc, log ../../.ssh/id_rsa, SLURM log outside the launch dir
                                                 # → not stored, counted
def test_symlink_fifo_refused(tmp_path): ...     # .command.err symlink to ~/.bashrc, FIFO, device → refused, no hang
def test_name_outside_allow_list_422(authed_client): ...  # name ".command.env", "../x", "/etc/passwd" → 422
def test_binary_415(authed_client, nf_workdir): ...       # NUL in the first 8 KiB → 415 binary-file
def test_engine_log_per_run(tmp_path): ...       # head.sh exports NXF_LOG_FILE under the run's .spectio/; Snakemake
                                                 # args carry --slurm-keep-successful-logs on SLURM only
def test_metrics_enabled(nf_run): ...            # the trace of a finished task has realtime, %cpu and peak_rss
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/test_taskfiles.py packages/spectio-server/tests/api/test_taskfiles_api.py -v`: FAIL.
- [ ] **Step 3:** implement; reads go through the bounded thread pool of the logs route.
- [ ] **Step 4:** the same command PASSES; on `slurm-mini` (Task 22) a finished Nextflow task shows a non-empty `.command.log` and a Snakemake job its SLURM log.
- [ ] **Step 5: Commit** `feat(server): each job's files and the work directory`.

### Task 29: Failure summary and resources per job

**Spec:** [architecture §13.7](../specs/architecture-plugins-and-packaging.md#137-log-sources-per-engine) (failure reason, resources), [api §5](../specs/api-and-data-model.md) (note 2026-10-28, Run and Resources), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 15 · **Depends on:** 4, 5, 18, 28

**Files:**
- Create: `packages/spectio/src/spectio/runner/sacct.py`, `packages/spectio-server/src/spectio_server/failure.py`
- Modify: the projector (resources from the Nextflow trace and the Snakemake `job_info`; `benchmark:` files read at job end), the read API of Task 18 (`failure` extended, `resources` on task items)
- Test: `packages/spectio/tests/test_sacct.py`, `packages/spectio-server/tests/test_failure.py`

**Interfaces:**
- Produces: `sacct_jobs(ids: list[str], timeout_s: float = 10) -> dict[str, SacctRow]` (`SacctRow(state, exit_code, reason, max_rss_bytes, elapsed_s, req_mem_bytes, time_limit_s)`), `parse_smk_slurm_message(text: str) -> SchedulerInfo | None`, `build_failure(run) -> Failure`.

- [ ] **Step 1: Write the failing tests**

```python
def test_sacct_argv_and_id_check(fakebin): ... # ids "8812477", "8812345_3" → one argv list, no shell; "1;rm" → refused
def test_sacct_parse_and_timeout(fakebin): ... # parsable2 output → SacctRow; slow fake → None after 10 s, no crash
def test_sacct_batches(fakebin): ...           # 250 finished Snakemake jobs → 3 calls, at most one a minute
def test_sacct_off(fakebin, settings): ...     # [slurm] accounting = false → no call; summary says unavailable
def test_smk_message_parsed(): ...             # "SLURM-job '48731209' failed, SLURM status is: 'OUT_OF_MEMORY'. Reason: …"
                                               # → state OUT_OF_MEMORY, reason, source engine_message
def test_smk_message_no_sacct(): ...           # "… Detailed failure reason unavailable …" → state, reason None
def test_nf_failure_summary(replayed_flaky, fakebin): ...  # exit 137 on its last attempt → process, exit_code, native_id,
                                               # scheduler from sacct, log_tail = last 20 lines of .command.log
def test_resources_nf(replayed_flaky): ...     # task item resources: cpus, memory_bytes, time_s, realtime_s, cpu_percent,
                                               # peak_rss_bytes, source trace
def test_resources_smk(smk_run): ...           # threads and mem_mb requested; benchmark file → source benchmark;
                                               # no benchmark → sacct batch → source sacct
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_sacct.py packages/spectio-server/tests/test_failure.py -v`: FAIL.
- [ ] **Step 3:** implement; `sacct` is called with `--parsable2 --noheader -j <ids> --format=JobID,State,ExitCode,Reason,MaxRSS,Elapsed,ReqMem,Timelimit` (fields **[to be validated]** on `slurm-mini` and at EMBL).
- [ ] **Step 4:** the same command PASSES; on `slurm-mini` the `flaky` pipeline's injected out-of-memory task shows its SLURM state.
- [ ] **Step 5: Commit** `feat(server): failure summary and resources per job`.

### Task 30: Resume, Copy to a new launch and the copy actions

**Spec:** [api §5.1](../specs/api-and-data-model.md) (`:relaunch` mode `resume`, note 2026-10-28), [api §5](../specs/api-and-data-model.md) (note 2026-10-28, Run, Copy to a new launch, Resume), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 16 · **Depends on:** 9, 10, 17, 18

**Files:**
- Create: `packages/spectio-server/src/spectio_server/api/relaunch.py`
- Modify: `render_head_script` (Task 9: `LaunchSpec.resume_of: ResumeSource | None`, with the parent's launch and work directories and `engine_session_id`), `write_run_manifest` (`parent_run_id`), the read API of Task 18 (`command`, `parent_run_id`, `resumed_as`), the launch API of Task 17 (`GET /runs/{id}:launch-template`)
- Test: `packages/spectio-server/tests/api/test_relaunch.py`, `packages/spectio/tests/test_headscript.py` (new cases)

- [ ] **Step 1: Write the failing tests**

```python
def test_resume_failed_creates_child(authed_client, failed_run): ...  # 201, child queued, parent_run_id set, parent stays failed
def test_resume_states(authed_client): ...     # succeeded or running → 409; cli-observed → 422 not-in-this-version
def test_resume_parent_head_alive_409(authed_client): ...
def test_resume_one_child_at_a_time(authed_client): ...  # a second resume while the first child runs → 409
def test_resume_other_fields_422(authed_client): ...     # mode rerun_from, params_patch → 422 not-in-this-version
def test_resume_head_script_nf(tmp_path): ...  # cwd = parent's launch dir, "-resume <session id>", "-w <parent work>",
                                               # spool and NXF_LOG_FILE in the child's .spectio/
def test_resume_head_script_smk(tmp_path): ... # "--unlock" then "--rerun-incomplete", in the parent's launch dir
def test_resume_rechecks_dirs(authed_client): ...  # parent launch dir made group-writable → refused (req. 10)
def test_command_quoted(authed_client): ...    # location "/p/a b'$(x)" → argv list; text is POSIX-quoted, names the
                                               # params file, never a value; cli-observed → command null
def test_launch_template(authed_client): ...   # params, profiles, location; non_default lists the changed keys
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/api/test_relaunch.py packages/spectio/tests/test_headscript.py -v`: FAIL.
- [ ] **Step 3:** implement; the child's run directory holds its own `.spectio/`, and its head runs in the parent's launch directory.
- [ ] **Step 4:** the same command PASSES; on `slurm-mini` (Task 22) a `flaky` Nextflow run, fixed by a parameter file edit, resumes and reports its earlier tasks as cached.
- [ ] **Step 5: Commit** `feat(api): resume a run and copy it to a new launch`.

### Task 31: Results and reports

**Spec:** [api §5](../specs/api-and-data-model.md) (note 2026-10-28, Results), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13 and 14 · **Depends on:** 17, 18, 28

**Files:**
- Create: `packages/spectio-server/src/spectio_server/api/results.py`
- Modify: the launch API of Task 17 (`runs.results_dir`: Nextflow `params.outdir`, resolved against the launch directory; Snakemake the launch directory, without `.snakemake/` and `.spectio/`)
- Test: `packages/spectio-server/tests/api/test_results.py`, `tests/e2e/report.spec.ts`

- [ ] **Step 1: Write the failing tests**

```python
def test_results_listing(authed_client, results): ...   # one level, dirs first, 1000-entry cap with truncated
def test_results_reports(authed_client, results): ...   # multiqc_report.html first, FastQC reports after, depth ≤ 4
def test_results_confined(authed_client, results): ...  # ../, absolute, symlink to $HOME → 422 or "link outside the run"
def test_html_sandbox_headers(authed_client, results): ...  # CSP sandbox without allow-same-origin, connect-src 'none',
                                                        # nosniff; SVG → attachment
def test_observed_run_no_results(authed_client): ...    # cli-observed → 404
```

```ts
test("a MultiQC report renders in its sandbox and cannot call the API", async ({ page }) => { /* real report fixture */ });
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/api/test_results.py -v`: FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** the same command PASSES, and the Playwright test passes with a MultiQC report from the nf-core/rnaseq megatest (whether MultiQC renders under the policy is **[to be validated]** here).
- [ ] **Step 5: Commit** `feat(api): results and reports, read only`.

### Task 32: The screens: job files, failure summary, results, Resume, copy and resources

**Spec:** [ui-spec §4.4](../specs/ui-spec.md#44-run-detail) (note 2026-10-28, run tools) · **Depends on:** 20, 28–31 · **Boards:** LiteRunTasks, MLiteRunTasks, LiteRunLogs, LiteRunFailed, LiteRunDetail, MLiteRunDetail, LiteLaunch

**Files:**
- Create: `web/src/runs/{TaskFilesDrawer.tsx,FailureSummary.tsx,ResultsSection.tsx,RunActions.tsx}`, `web/src/runs/TaskFilesDrawer.test.tsx`
- Modify: `web/src/runs/RunDetailPage.tsx`, `web/src/launch/LaunchPage.tsx` (prefill from `:launch-template`), `tests/e2e/skeleton.spec.ts`

- [ ] **Step 1: Write the failing tests**

```ts
test("Files opens the drawer on .command.log for a failed attempt; Escape returns focus to the row's button", …);
test("a missing file says why, in words", …);           // not yet, deleted after success, cleaned
test("tabs are buttons with role tab; the drawer is aria-modal", …);
test("failed run: Why it failed shows SLURM state, requested and used memory, last lines", async ({ page }) => { /* … */ });
test("Resume asks, creates a child, and both runs link to each other", async ({ page }) => { /* … */ });
test("Copy to a new launch opens the form prefilled with the non-default values listed", async ({ page }) => { /* … */ });
test("resources columns show 'near limit' as text", async ({ page }) => { /* … */ });
```

- [ ] **Step 2:** `npm --prefix web test` and the Playwright smoke: FAIL.
- [ ] **Step 3:** implement; native `<button>` and `<input>` only, per-row accessible names, nothing hover-only (`CLAUDE.md`).
- [ ] **Step 4:** both PASS on the desktop and phone projects; render the boards and compare by eye.
- [ ] **Step 5: Commit** `feat(web): job files, failure summary, results, resume and copy`.

---

## Out of scope

Everything that [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) marks "no" for 0.0.1 or "later (open)":
- QC checks and gates in every form;
- Kubernetes, a shared server and remote runners;
- users, sign-in, accounts and roles;
- relaunch with changed parameters, rerun from a stage, and the parameter history (#61); Resume and Copy to a new launch are in (Task 30);
- visualisation (DAG, timelines, charts, comparison);
- full scheduler monitoring (task jobs, pending reasons, accounting, capacity);
- Postgres, Compose and Helm;
- the depictio hand-off, WES, MCP, embedded elements and LabID.

Also not in P1:
- pause, and resume of a paused run (Resume after a failure is Task 30);
- a workflow catalogue and Git URLs (D2);
- `POST /runs:validate` and file checks;
- publishing the bridges (Thomas, inbox #66), Cancel and the other actions on runs started from a terminal (#65), and a `spectio run --` wrapper;
- the head as an `sbatch` head job, and sites other than EMBL ([log 2026-10-28](../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open));
- slurmrestd;
- the spike sec-single-mode (R10 C6);
- everything before the 0.0.1 tag (R10 C5–C8).

## Done when

- [ ] Tasks 1–32 are merged, each with its tests first and its `review-code` pass (Assumptions, Process).
- [ ] On `slurm-mini` in CI (`pipelines-slurm.yml`, job `e2e`), through a token-link session, the synthetic Nextflow and Snakemake `happy` runs launch with their heads in tmux on the submitter node, end `succeeded`, and match the golden counts per process (Task 22).
- [ ] A running run of each engine cancels to `cancelled` with no job left, and a server killed while a Nextflow head runs adopts it on restart, with no duplicate event (Task 23).
- [ ] Each of §15.3 requirements 1–7 has passing `test_req<N>_*` tests (Tasks 3, 11–16), requirements 8–12 their named tests (Tasks 2, 9–12, 24–26), and requirements 13–16 theirs (Tasks 28–31).
- [ ] The Playwright smoke passes on the local executor: link, home, launch, list, detail (stages and the flat list) with live refresh, cancel (Task 20).
- [ ] A server started with no database rebuilds it from the run directories (Task 11).
- [ ] `spectio-open` and the SSH config entry both open home on an EMBL login node (Task 24).
- [ ] A run started by hand with the bridge enabled shows in the runs list as started from a terminal, monitor only, and a missing `~/.spectio` leaves the run unaffected (Task 25).
- [ ] Both bridges build as release packages, dry-run only; nothing is published (Task 26).
- [ ] The run detail shows declared or detected stages above the processes or rules list, and the detectors match their golden output on nf-core/rnaseq, sarek, methylseq and mosaicatcher-pipeline (Task 27).
- [ ] A failed run shows each job's files, the failure summary with its SLURM state, and resources per job; it resumes as a child run; a MultiQC report opens in its sandbox (Tasks 28–32).
- [ ] `tests/packaging/test_wheel.sh` passes: one installable wheel with the UI and both bridges, and a `spectio` environment under 80 MB (Task 21).
- [ ] Tier 0 is green on every package: ruff, mypy (`--strict` on `spectio-sdk`), `lint-imports`.
- [ ] api §14 (driven runs) is written, and every spec the code contradicted is updated with a log entry; `python3 tools/docs/check.py` passes.
- [ ] Thomas has confirmed or corrected the Assumptions above (the inbox entries named there), before the 0.0.1 tag.

## Open questions

- **D2 and D3** (inbox #34 for SR-056, inbox #55) are reserved for Thomas; the plan follows R10's recommended options as Assumptions 2 and 3.
- **The bootstrap-page gap** (Assumption 8): §15.3 req. 2 should name the session-free page; it is to be recorded in the next apply pass.
- **Where the Snakemake mapping lives**: Assumption 16 replaces the **[to be validated]** of api §7.2 for 0.0.1. Thomas, or spike T1's resume check (#32), may change it.
