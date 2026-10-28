# P1 · Walking skeleton (0.0.1 on a cluster) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` (step P3 of [`next-phase.md`](../playbooks/next-phase.md)) or `executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

*Draft, 2026-10-28 (step P1). Waiting for Thomas at the GO gate ([R10 §5](../reviews/R10-synthesis.md#5-go-no-go)). No product code exists yet; this page writes none.*

![The P1 walking skeleton: a laptop browser with the launch form, runs list and run detail with Cancel reaches spectio serve on a SLURM login node through an SSH tunnel and a one-time token link; the runner sends the engine head to a compute node with sbatch, the plugins' spool file in the run directory is read back into SQLite; milestones M1 to M5 and the seven §15.3 security requirements are marked where they apply, above a to-scale strip of the 23 tasks](../assets/diagrams/p1_skeleton_light.png#only-light)
![The P1 walking skeleton: a laptop browser with the launch form, runs list and run detail with Cancel reaches spectio serve on a SLURM login node through an SSH tunnel and a one-time token link; the runner sends the engine head to a compute node with sbatch, the plugins' spool file in the run directory is read back into SQLite; milestones M1 to M5 and the seven §15.3 security requirements are marked where they apply, above a to-scale strip of the 23 tasks](../assets/diagrams/p1_skeleton_dark.png#only-dark)

Step page: [Progress · P1](../progress/W4/P1.md).

**Goal:** the smallest Spectio a test user can run: `spectio serve` on a SLURM login node, opened through an SSH tunnel with a one-time token link, that launches the synthetic Nextflow or Snakemake pipeline (head through `sbatch`), lists the runs, shows one run's state, task counts, processes or rules, and head-job state as text and tables, and cancels it.

**Architecture:** one process per user on the login node: a FastAPI app, an in-process runner thread and SQLite on node-local disk ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)). The runner writes a head script, submits it with `sbatch` (or starts it detached on the local executor in tests), watches the head with `squeue` / `sacct`, and tails the event spool that the engine plugins write in the run directory. One writer thread validates spool events and projects them into `runs`, `tasks` and `attempts` in the same transaction. A three-screen React UI polls the API.

**Tech stack:** Python 3.13 (uv workspace), Pydantic 2, Typer, FastAPI + uvicorn, SQLAlchemy Core + Alembic on SQLite, `jsonschema`; Groovy (`nf-spectio`, built as in spike T2); React + Vite + Mantine 7 + TanStack Query; pytest, Vitest, Playwright (T6 skeleton); sind `slurm-mini`.

**Spec:** [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) (what 0.0.1 contains) and [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (architecture and the seven security requirements); summary in [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md); decision log [2026-10-27, revised](../decisions/log.md#2026-10-27-001-revised-on-the-cluster-no-gates-a-token-link) and [2026-10-28, narrowed](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui); what P1 must handle: [R10 §3a](../reviews/R10-synthesis.md#3a-what-p1-must-handle-as-tasks-or-tests). Executors read the spec section named in each task.

**Process** *(assumed — pending Thomas, inbox #52, D0 (b))*: the [proposal](walking-skeleton-proposal.md)'s light process. Product code gets `review-code` (code-reviewer and security-reviewer, then code-simplifier); tooling and test-only changes get tests and one review. When code contradicts a spec, the owning spec changes in the same PR. One Progress page per milestone, not per task.

## Assumptions

Decisions taken in place of Thomas, who was not available for brainstorming. Each is *(assumed — pending Thomas)*; the inbox entry is named where one exists.

1. **D1, no relaunch, no parameter history** (inbox #61). The run detail shows its own parameters only. *(assumed — pending Thomas)*
2. **D2, how a workflow reaches the form** (inbox #34, SR-056). The user types an absolute path to a pipeline directory that their own account can read. The engine is detected from the files: `main.nf` means Nextflow; `workflow/Snakefile` or `Snakefile` means Snakemake. The schema comes from `nextflow_schema.json`, or from `config.schema.yaml` / `workflow/schemas/config.schema.yaml`. Without a schema, the types are inferred from `config/config.yaml`, or the form falls back to key / value rows. There is no catalogue, no `POST /workflows`, no Git URL and no `POST /runs:validate` in P1. A `workflows` row (source `local`) and a `workflow_versions` row are created at launch. *(assumed — pending Thomas)*
3. **D3, what engine events may carry** (inbox #55, option (a)). `nf-spectio` sends no `script` or `env`. The SDK event models are allow-lists (`extra="ignore"`), so `script`, `env`, `homeDir`, `commandLine`, `configText` and Snakemake's `cmd` are never stored, even if a plugin sends them. *(assumed — pending Thomas)*
4. **D4, Cancel** (inbox #62). One Cancel action: `scancel --signal=TERM --full <head>`, then a plain `scancel` if the head is still listed after a 60 s grace period ([schedulers §2](../specs/schedulers-and-monitoring.md) row L1). On the local executor: SIGTERM to the process group, then SIGKILL. *(assumed — pending Thomas)*
5. **Attempt state `aborted`** (inbox #56, option (a)). *(assumed — pending Thomas)*
6. **"Stages" in 0.0.1 are the engine's processes (Nextflow) or rules (Snakemake)**, in first-seen order, with task counts by state: a subset of `GET /runs/{id}/processes` ([api §5](../specs/api-and-data-model.md)). Structural stage detection ([ui-spec §5.1](../specs/ui-spec.md) source (2)) and `run_stages` come later. The synthetic pipelines have no subworkflows, so detection would show nothing. *(assumed — pending Thomas)*
7. **No SSE in 0.0.1.** The UI polls every 5 s and stops on a terminal state. This removes the `EventSource` cookie question of §15.3 req. 3 from 0.0.1. *(assumed — pending Thomas)*
8. **A session-free bootstrap page.** §15.3 req. 2 asks for a session on every request, but something must serve the page that reads the ticket from the URL fragment. `GET /auth/link` (static HTML) and `GET /auth/link.js` are the only routes served without a session; they carry no data. *(assumed — pending Thomas; a spec gap to record in §15.3)*
9. **`spectio login --print-link`** reads `<data-dir>/server.json` (port, pid; mode 0600) and the server key file, and calls `POST /api/v1/auth/links` with `Authorization: Bearer <server key>` and the loopback `Origin`. *(assumed — pending Thomas)*
10. **Port.** The default is 8080 ([architecture §7.3](../specs/architecture-plugins-and-packaging.md)). When 8080 is taken (likely on a shared login node), the server takes a free port and prints it. *(assumed — pending Thomas)*
11. **Ingest and projection share one transaction on the writer thread**, and the spool cursor (file, byte offset) is a SQLite row written in that same transaction, not the `.spectio/events/.cursor` file of [architecture §13.1](../specs/architecture-plugins-and-packaging.md), which stays for a remote forwarder. `runs.projected_seq` therefore always equals `last_seq`. *(assumed — pending Thomas)*
12. **Spool numbers** (written into api §14 by Task 1): one JSON object per line; a line of at most 64 KiB; the writer rotates at 32 MiB; the reader ignores anything past 64 MiB in one file and counts it. *(assumed — pending Thomas, inbox #28)*
13. **One head script for both launchers.** `<launch>/.spectio/head.sh` carries `#SBATCH` lines, which bash ignores, so the same file runs under `sbatch` or under `setsid bash` on the local executor. A trailer writes `.spectio/head.exit` (exit code, epoch). Because of `--export=NONE`, the script exports an allow-list itself: `PATH`, `HOME`, `LANG`, `LC_ALL`, `JAVA_HOME`, `NXF_HOME`, and `SPECTIO_RUN_ID`, `SPECTIO_LAUNCH_N`, `SPECTIO_SPOOL_DIR`. Parameters reach the engine as a file (`-params-file`, `--configfile`), never as shell words. *(assumed — pending Thomas)*
14. **Head defaults:** 2 CPUs, 4G, a walltime of `2-00:00:00`; partition and account are unset. All of them are configurable in `spectio.toml` `[slurm]` ([schedulers §3.1](../specs/schedulers-and-monitoring.md)). The `squeue` poll defaults to 60 s ([schedulers §3.2](../specs/schedulers-and-monitoring.md)), lowered to 5 s in tests. *(assumed — pending Thomas)*
15. **Head end state.** While the head is listed, `squeue` gives its state. After that, `sacct -j <head>` gives it when accounting is enabled, and otherwise `head.exit` does: `slurm-mini` has no accounting ([dev-env §4.1](../specs/dev-environment-and-testing.md)). A head that ended with no terminal engine event within 60 s makes the run `failed`, class `head_lost` or `engine_fault` ([api §7.1](../specs/api-and-data-model.md)). *(assumed — pending Thomas, inbox #40)*
16. **Snakemake mapping** (api §7.2 says **[to be validated]**). `job_info` creates the task (rule + wildcards) and an attempt; `job_started` gives `running` (Snakemake reports no separate submit); `job_finished` gives `succeeded`; `job_error` gives `failed`. A `job_started` on the same `jobid` after a failure opens attempt n + 1 ([T2](../research/spike-engine-events-2026-10-28.md)). A Snakemake launch succeeds when the head exits 0 and no `error` record arrived. A Nextflow launch ends on `onFlowComplete.success`. *(assumed — pending Thomas)*
17. **Bridge delivery.** `nf-spectio` is unpacked into `$NXF_HOME/plugins/nf-spectio-<ver>/`, as [architecture §7.3](../specs/architecture-plugins-and-packaging.md) says. The Snakemake logger is copied to `<launch>/.spectio/pylib/` and put on `PYTHONPATH`, so compute nodes read it from the run directory. *(assumed — pending Thomas)*
18. **Minimal tenancy.** `spectio init` creates one principal (the Unix user), one project `default`, one environment (kind `slurm`, or `local` with `--local`) and its runner row. There are no groups. Every tenant row keeps `project_id` ([`mvp-0.0.1.md`](../specs/mvp-0.0.1.md) §4). *(assumed — pending Thomas)*
19. **Where the tests run.** The Playwright smoke runs against `spectio serve` on the local executor on the CI runner. The sind end-to-end tests drive the HTTP API from inside the submitter node, as a browser behind a tunnel would. *(assumed — pending Thomas)*
20. **Ultra-simple screens.** The launch form has no stepper, no review step and no file checks. Logs are the head stdout and stderr and the engine run log, last 64 KiB; per-task logs come later. Sessions last until the server restarts. The Snakemake head stays in `sbatch` (T3); the login-node fallback is not built (R10 C7). *(assumed — pending Thomas)*

## Global Constraints

- Python 3.11–3.14 supported, tested on 3.13 (`PYTHON_VERSION` in `dev/versions.env`) ([architecture §7.3](../specs/architecture-plugins-and-packaging.md)).
- SQLite loaded by Python ≥ 3.51.3, or ≥ 3.50.7 / ≥ 3.44.6 in those series; checked at start ([api §7](../specs/api-and-data-model.md)).
- Nextflow ≥ 25.04 (tested 26.10.4, 25.10.9, 25.04.8); Snakemake ≥ 9.0 with `snakemake-interface-logger-plugins` `>=1.2,<3` (tested 9.27.1) ([architecture §13.4](../specs/architecture-plugins-and-packaging.md)).
- Package layout: `packages/spectio-sdk`, `packages/spectio`, `packages/spectio-server`, `engine-bridges/nf-spectio`, `engine-bridges/snakemake-logger-plugin-spectio`, `web/` ([architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout)). The runner never imports server code (import-linter); `spectio` has no FastAPI and no SQLAlchemy.
- IDs are ULID text with a type prefix (`run_`, `tsk_`, `att_`, `evt_`…); times are UTC; JSON is stored in `TEXT` ([api §7](../specs/api-and-data-model.md)).
- Run states: the full enum in the `CHECK` constraint; 0.0.1 uses `queued`, `running`, `cancelling`, `succeeded`, `failed`, `cancelled` ([api §7.1](../specs/api-and-data-model.md)). Attempt states: `pending`, `submitted`, `running`, `succeeded`, `failed`, `cached`, `stored`, `aborted`; states only move forward ([api §7.2](../specs/api-and-data-model.md)).
- Head job: name `spectio-head-<run_id>-<launch n>`, `--comment=spectio:<run_id>`, `--export=NONE`; job names carry the run ID only ([schedulers §3.1](../specs/schedulers-and-monitoring.md)).
- Server: bound to `127.0.0.1` only; API under `/api/v1`; errors are RFC 9457 problem details ([api §4.1](../specs/api-and-data-model.md)).
- Secrets: ≥ 256 bits from `secrets`, compared with `hmac.compare_digest`; ticket valid 15 min, single use, in the URL fragment ([dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts)).
- UI copy and labels: English; state words from [ui-spec §3.1](../specs/ui-spec.md); text and tables only, no chart, DAG or timeline ([log 2026-10-28](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui)).
- Every `feat` merged into `main` during 0.0.x carries the footer `Release-As: 0.0.1` ([dev-env §15.2](../specs/dev-environment-and-testing.md)).
- Every external fact added to a spec has a source, or is marked **[to be validated]** (`CLAUDE.md`).

## Review Focus

The five inputs most likely to hurt a test user that no other test covers. Each has its test in the task named.

1. **Parameter values or a pipeline path with spaces, quotes, `$(…)` or newlines.** They must never be interpreted by a shell: the values go into a params file, and paths are quoted with `shlex.quote`. Test: Task 9, `test_head_script_shell_metacharacters`.
2. **A spool line that is only partly written** (the engine is mid-append, or NFS shows a short file). It is not consumed and is read whole on the next tick. Test: Task 3, `test_partial_last_line_waits`.
3. **`sbatch` refuses the head** (unknown partition, `QOSMaxSubmitJobPerUserLimit`). The run ends `failed`, class `launch_error`, with the start of `sbatch`'s stderr as its message, and nothing stays `queued`. Test: Task 10, `test_sbatch_rejected_fails_run`.
4. **The engine is missing, or older than the floor, at launch.** The run ends `failed`, class `engine_missing` or `engine_version`, with a message naming the binary and the version found. Test: Task 9, `test_engine_missing_and_too_old`.
5. **A link opened twice, after 15 minutes, or after a server restart.** The bootstrap page says "This link was already used or has expired. Run `spectio login --print-link` on the cluster for a new one.", not a blank page or raw JSON. Tests: Task 12, `test_reused_or_expired_link_message`, and the browser check in Task 20.

---

## Milestones

| Milestone | Tasks | Ends with |
|---|---|---|
| M1 · Events in | 1–7 | T2 fixtures and real local runs of both engines replay into SQLite with the right states |
| M2 · Heads | 8–10 | heads launched, watched, adopted and cancelled, locally and against a fake SLURM |
| M3 · Served safely | 11–16 | `spectio serve` with the token link and §15.3 requirements 1–5 and 7 (6 is Task 3) |
| M4 · API and screens | 17–21 | the API of the three screens, the UI, and a wheel that carries the UI and both bridges |
| M5 · On the cluster | 22–23 | both engines end to end on `slurm-mini` in CI, with cancel and restart |

Commands assume the repository root, and that the uv workspace exists (after Task 1).

---

## M1 · Events in

### Task 1: Workspace and the spool event contract

**Spec:** api §14 (new: the driven-run part, inbox #36 (a)), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 6, [architecture §13.1](../specs/architecture-plugins-and-packaging.md) · **Depends on:** none · **R10 §3a:** row 1 (C2: first task)

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

**Spec:** [api §7](../specs/api-and-data-model.md) (tables, SQLite version rule), [architecture §7.2](../specs/architecture-plugins-and-packaging.md) (one writer, network file system refusal) · **Depends on:** 1 · **R10 §3a:** row 11

**Files:**
- Create: `packages/spectio-server/src/spectio_server/store/{db.py,schema.py,writer.py}`, `packages/spectio-server/src/spectio_server/migrations/` (Alembic, one initial revision)
- Test: `packages/spectio-server/tests/test_store.py`

**Interfaces:**
- Produces: tables `principals`, `projects`, `environments`, `runners`, `runner_commands`, `workflows`, `workflow_versions`, `runs`, `run_inputs`, `launches`, `tasks`, `attempts`, `events`, `spool_cursors(launch_id, file, offset)`, `spool_drops(launch_id, reason, count)`. `open_db(data_dir: Path) -> Engine` (WAL, `busy_timeout=5000`, `auto_vacuum=INCREMENTAL` at creation; raises `UnsafeDatabase` on a network file system or an old SQLite). `Writer.submit(fn: Callable[[Connection], T]) -> Future[T]`: one thread, one connection, `BEGIN IMMEDIATE`. `fs_type(path, mounts=Path("/proc/self/mounts")) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
def test_refuses_network_fs(tmp_path):          # fake mounts table: tmp_path on "nfs4", then "lustre", "gpfs"
    with pytest.raises(UnsafeDatabase, match="nfs4"): open_db(tmp_path, mounts=fake_mounts(tmp_path, "nfs4"))
def test_refuses_old_sqlite(monkeypatch): ...   # sqlite_version "3.45.0" → UnsafeDatabase naming 3.51.3
def test_pragmas(tmp_path):                     # journal_mode == "wal", auto_vacuum == 2
def test_writer_serialises(tmp_path):           # 50 concurrent submits → 50 rows, no SQLITE_BUSY
def test_run_state_check_constraint(tmp_path):  # inserting state "paused_forever" raises IntegrityError
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
def test_resume_26_10_4():     # 63 tasks cached
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

**Spec:** [architecture §13.1, §13.3, §13.4, §7.3](../specs/architecture-plugins-and-packaging.md) (spool, never throw, version floor, jar delivery), api §14 · **Depends on:** 1 · **R10 §3a:** row 5

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
  - `spectio init --data-dir PATH --runs-root PATH [--local] [--head-partition P] [--head-time T] [--head-account A]`, which writes `spectio.toml` and creates the rows of Assumption 18 through the server store (the CLI imports `spectio_server` lazily; `spectio` alone says "install spectio[server]");
  - `Settings` with `data_dir`, `runs_root`, `port=8080`, `slurm: SlurmHeadOpts(partition: str | None, account: str | None, time: str = "2-00:00:00", cpus: int = 2, mem: str = "4G")`, `runner.poll_s=60`, `runner.spool_s=2`, `engines.extra_args`;
  - `spectio doctor`, which prints `ok|warn|fail <check> <detail>` lines and exits 1 on any `fail`.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_creates_one_environment(tmp_path):  # one project "default", one environment kind slurm with
                                                  # config.runs_root, one runner row; second init → no duplicate
def test_runs_root_must_exist_and_be_absolute(tmp_path): ...
def test_doctor_reports_engines(fakebin):  # "ok nextflow 26.10.4 /…/nextflow", "fail snakemake not found on PATH"
def test_doctor_reports_fs_and_sqlite(tmp_path): ...  # data dir on nfs4 (fake mounts) → fail; SQLite version line
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_init.py packages/spectio/tests/test_doctor.py -v`: FAIL.
- [ ] **Step 3:** implement; `doctor` also checks `sbatch`, `squeue` and `sacct` on PATH, Java's major version, and the hostname pin recorded at init.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(cli): spectio init and spectio doctor`.

### Task 9: Head script, local launcher and the runner loop

**Spec:** [schedulers §3.1.1](../specs/schedulers-and-monitoring.md) (detach, PID and exit files, adopt), [architecture §7.1](../specs/architecture-plugins-and-packaging.md) (in-process runner consumes `runner_commands`), [api §7](../specs/api-and-data-model.md) (`launches`, `runner_commands`) · **Depends on:** 4, 6, 7, 8 · **R10 §3a:** row 5 (engine checks)

**Files:**
- Create: `packages/spectio/src/spectio/runner/{headscript.py,engines.py,local.py,loop.py}`
- Test: `packages/spectio/tests/test_headscript.py`, `packages/spectio/tests/test_local_launcher.py`

**Interfaces:**
- Consumes: `HeadReport`, `Failure` (Task 4); `Settings`, `SlurmHeadOpts` (Task 8).
- Produces:
  - `render_head_script(spec: LaunchSpec) -> str`, where `LaunchSpec(run_id, launch_n, engine, location: Path, launch_dir: Path, work_dir: Path, profiles: list[str], params: dict, slurm: SlurmHeadOpts | None, env: dict[str, str])`;
  - `check_engine(engine) -> EngineInfo(path, version)`, raising `EngineMissing` or `EngineTooOld`;
  - the `Launcher` protocol: `submit(spec) -> str` (native id), `poll(ids) -> dict[str, HeadReport]`, `cancel(native_id, grace_s: int = 60) -> None`, `adopt(launch) -> HeadReport`;
  - `LocalLauncher` (`setsid bash head.sh`; `.spectio/head.pid` holds PID, start time and boot ID);
  - `RunnerSink` (a protocol in `spectio/runner/types.py`, implemented by the server through its `Writer`, so the runner never imports the server): `lease_commands() -> list[Command]`, `ack(command_id: str, ok: bool, detail: str | None)`, `active_launches() -> list[LaunchRef]`, `cursor(launch_id) -> dict[str, int]`, `ingest(launch_id, batch: SpoolBatch)`, `head_report(launch_id, report: HeadReport)`;
  - `RunnerLoop(sink: RunnerSink, launcher: Launcher, tick_s: float = 2)`, which leases `runner_commands` (`launch`, `cancel`), reads spools (Task 3) and polls heads.

- [ ] **Step 1: Write the failing tests**

```python
def test_head_script_shell_metacharacters(tmp_path):  # location "/p/a b'$(x)", param "x\n$(rm -rf ~)" →
                                                      # `bash -n` OK; the value only in params.json; no "$(rm" in head.sh
def test_head_script_nextflow_args():   # "-params-file", "-plugins nf-spectio@0.0.1", "-c .spectio/spectio.config"
def test_head_script_snakemake_args():  # "--logger spectio", "--configfile", PYTHONPATH=<launch>/.spectio/pylib
def test_engine_missing_and_too_old(fakebin):  # no nextflow → class engine_missing; "24.10.0" → engine_version,
                                               # message names the path and the version
def test_local_launch_exit_file(tmp_path):     # trivial engine stub exits 3 → head.exit "3 …", HeadReport(exit_code=3)
def test_adopt_after_restart(tmp_path): ...    # new LocalLauncher sees the live PID (same start time and boot id) → adopted
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_headscript.py packages/spectio/tests/test_local_launcher.py -v`: FAIL.
- [ ] **Step 3:** implement Assumptions 13 and 17. Bridges come from `bridge_dir() -> Path` (`importlib.resources` in an installed wheel, Task 21; `$SPECTIO_BRIDGES_DIR` pointing at the Task 6 and 7 build output in a checkout). Nextflow: write `.spectio/spectio.config` (`process.executor = 'slurm'` and `queue` on a SLURM environment) and unpack `nf-spectio` into `$NXF_HOME/plugins`. Snakemake: pass `--executor slurm` on SLURM, plus `--workflow-profile <location>/profiles/<p>` when a profile is given, plus the environment's `extra_args`. Run directories are `<runs_root>/<run_id>/{launch,work}`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(runner): head script, local launcher and runner loop`.

### Task 10: SLURM launcher

**Spec:** [schedulers §3.1](../specs/schedulers-and-monitoring.md) (head job, idempotent launch, runner restart), §3.2 (text poll), §3.3 (CLI transport), §2 row L1 (cancel) · **Depends on:** 9 · **R10 §3a:** rows 6, 12 (adoption)

**Files:**
- Create: `packages/spectio/src/spectio/runner/slurm.py`, `packages/spectio/tests/fakebin/{sbatch,squeue,sacct,scancel}` (state kept in `$FAKE_SLURM_DIR`; replays the T3 fixtures in `tests/fixtures/slurm/slurm-26.05.5/`)
- Test: `packages/spectio/tests/test_slurm_launcher.py`

**Interfaces:**
- Consumes: the `Launcher` protocol (Task 9), `HeadReport` (Task 4).
- Produces: `SlurmLauncher(poll_s=60)`, with `parse_squeue_text(out: str) -> list[SqueueRow]` (format `'%i|%T|%r|%S|%P|%N|%j'`, name last), `parse_squeue_json(doc) -> list[SqueueRow]` (boot adoption, comment check) and `parse_sacct_json(doc) -> dict[str, HeadReport]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_submit_uses_name_comment_export(fakebin):  # argv has --parsable, the name, --comment=spectio:<run>, --export=NONE
def test_idempotent_submit(fakebin):                # head name already in squeue → no second sbatch, that id adopted
def test_sbatch_rejected_fails_run(fakebin):        # sbatch exit 1 "Invalid partition name" → class launch_error,
                                                    # message starts with the stderr; run not queued
def test_parse_t3_fixtures():                       # squeue/sacct JSON of nextflow-oom_fatal etc. parse; FAILED 137:0 read
def test_end_state_without_accounting(fakebin):     # sacct fails ("accounting storage is disabled") → head.exit used
def test_adopt_filters_prefix_and_comment(fakebin): # a job named spectio-head-x with a foreign comment is ignored
def test_cancel_term_then_kill(fakebin): ...        # scancel --signal=TERM --full <id>; still listed after grace → scancel <id>
```

- [ ] **Step 2:** `uv run pytest packages/spectio/tests/test_slurm_launcher.py -v`: FAIL.
- [ ] **Step 3:** implement Assumptions 4, 14 and 15. Only one `squeue` call per poll, for all runs. States are filtered client-side, never with `sacct -s` (T3 finding 6).
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(runner): SLURM launcher on the CLI transport`.

---

## M3 · Served safely

Each task below carries one §15.3 security requirement; its tests are named `test_req<N>_*` in `packages/spectio-server/tests/security/`. Requirement 6 is Task 3. `conftest.py` (Task 12) provides `app`, `client` (no session) and `authed_client` (session cookie, `Host: 127.0.0.1:8080`, matching `Origin`).

### Task 11: `spectio serve`, bind (§15.3 req. 1) and boot

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 1 and "Server restart", [architecture §7.1, §7.2](../specs/architecture-plugins-and-packaging.md) (boot order, one process) · **Depends on:** 3, 8, 9, 10 · **R10 §3a:** rows 2, 6, 12

**Files:**
- Create: `packages/spectio-server/src/spectio_server/{app.py,serve.py}`, `packages/spectio/src/spectio/cli/serve.py`
- Test: `packages/spectio-server/tests/security/test_req1_bind.py`, `packages/spectio-server/tests/test_serve.py`

**Interfaces:**
- Consumes: `open_db`, `Writer` (Task 2), `RunnerLoop`, `RunnerSink` and the launchers (Tasks 9 and 10).
- Produces: `create_app(settings) -> FastAPI` and `serve(settings) -> None`. Boot runs open the database, take `<data-dir>/serve.lock` (flock), adopt the heads, replay the spools, start the runner loop, then uvicorn on `127.0.0.1`. It writes `server.json` (`{port, pid, host}`) and prints the start text below.

```text
Spectio 0.0.1 is running on <hostname>, port <port>.
1. On your laptop, open a tunnel:  ssh -N -L <port>:127.0.0.1:<port> <user>@<hostname>
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
def test_port_taken_picks_free_port(settings): ...  # 8080 busy → another port, printed and written to server.json
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/security/test_req1_bind.py packages/spectio-server/tests/test_serve.py -v`: FAIL.
- [ ] **Step 3:** implement. There is no `--host` flag; any other configured value aborts the start.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(server): spectio serve bound to loopback`.

### Task 12: Token link, secrets and sessions (§15.3 req. 2)

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) "Access" and req. 2, [auth §2, §2.1](../specs/authentication-and-access.md) (ticket rules) · **Depends on:** 11 · **R10 §3a:** row 2

**Files:**
- Create: `packages/spectio-server/src/spectio_server/auth/{secrets.py,routes.py,middleware.py,static/link.html,static/link.js}`, `packages/spectio/src/spectio/cli/login.py`, `packages/spectio-server/tests/conftest.py`
- Test: `packages/spectio-server/tests/security/test_req2_secrets.py`

**Interfaces:**
- Produces:
  - `ServerKey.generate(data_dir) -> ServerKey`, written to `server.key`, 0600, at each start;
  - `TicketStore.mint() -> str` (43 base64url characters; only its SHA-256 is kept, with an expiry) and `TicketStore.burn(ticket) -> bool`;
  - `SessionStore.create() -> str` and `SessionStore.valid(secret) -> bool` (in memory, `compare_digest` on digests);
  - routes: `POST /api/v1/auth/magic-links:exchange` (`{"ticket"}` → 204 and the cookie) and `POST /api/v1/auth/links` (server key → `{"url"}`);
  - middleware: 401 problem with no data on every other route, except `GET /auth/link` and `GET /auth/link.js`;
  - `spectio login --print-link`.

- [ ] **Step 1: Write the failing tests**

```python
def test_req2_every_route_needs_session(client, app):  # every route of app.routes except the three exemptions → 401,
                                                       # body has no run data
def test_req2_secrets_256_bits():                      # ticket, session and key decode to ≥ 32 bytes; secrets used
def test_req2_ticket_single_use_and_15_min(client, clock):  # second exchange → 401; at +15 min 1 s → 401
def test_req2_ticket_stored_hashed(app): ...           # the store holds no plaintext ticket
def test_req2_server_key_only_for_links(client):       # server key as bearer on GET /api/v1/runs → 401
def test_reused_or_expired_link_message(client):       # 2nd exchange → 401 problem type ".../link-expired";
                                                       # GET /auth/link HTML holds the exact Review Focus 5 sentence
def test_login_print_link(cli, running_server): ...    # prints a working link; ticket removed from history
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
- Create: `packages/spectio/src/spectio/fsmodes.py` (`secure_dir(path) -> None` creates the directory 0700 or tightens it; `secure_file(path) -> None` sets 0600)
- Modify: `init.py` (Task 8), `store/db.py` (Task 2), `auth/secrets.py` (Task 12), `runner/headscript.py` (Task 9)
- Test: `packages/spectio-server/tests/security/test_req5_modes.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_req5_data_dir_0700(initialised): ...                # stat mode & 0o777 == 0o700
def test_req5_key_and_db_files_0600(served): ...             # server.key, spectio.db, -wal, -shm, server.json
def test_req5_run_dirs_0700(launched): ...                   # <runs_root>/<run_id> and launch/, work/
def test_req5_umask_does_not_loosen(monkeypatch): ...        # with umask 000 the modes above still hold
def test_req5_existing_loose_dir_tightened_or_refused(tmp_path): ...  # data dir 0755 → 0700, with a warning
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
- Test: `packages/spectio-server/tests/api/test_launch.py`

**Interfaces:**
- Consumes: `authed_client`; `runner_commands` (Task 9).
- Produces:
  - `GET /api/v1/workflows:inspect?location=` → `{location, engine, name, schema, schema_source: "nextflow_schema.json" | "config.schema.yaml" | "inferred" | "none", profiles: [str]}`;
  - `POST /api/v1/runs` with body `{workflow: {location}, name?, profiles?: [str], params: {}}` → `201` with the run (`state: queued`), a `Location` header and a `launch` row in `runner_commands` written in the same transaction; `422 validation-failed` with `errors: [{field, message}]` otherwise.

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

**Spec:** [api §5](../specs/api-and-data-model.md) (`GET /runs`, `GET /runs/{id}`, `/processes`, `/tasks`, `/logs`), [api §5.1](../specs/api-and-data-model.md) (`:cancel` source states), [architecture §13.7](../specs/architecture-plugins-and-packaging.md) (log sources), [checking-scenarios §11.1](../specs/checking-scenarios.md) (confinement rule) · **Depends on:** 4, 5, 17 · **R10 §3a:** rows 9, 10; D4

**Files:**
- Create: `packages/spectio-server/src/spectio_server/api/{runs_read.py,logs.py,cancel.py}`, `packages/spectio-server/openapi/0.0.1.json`
- Test: `packages/spectio-server/tests/api/test_read.py`, `packages/spectio-server/tests/api/test_cancel.py`, `packages/spectio-server/tests/api/test_openapi.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/runs?limit=&cursor=` → `{items, next}`, newest first;
  - `GET /api/v1/runs/{id}` → `{id, name, state, created_at, started_at, ended_at, workflow: {engine, location, name}, profiles, params, failure, head: {native_id, state, node, exit_code} | null, summary: {tasks_total, tasks_expected, counts}}`;
  - `GET /api/v1/runs/{id}/processes` → `{items: [{process, counts, retries}]}`;
  - `GET /api/v1/runs/{id}/tasks?state=&process=&limit=&cursor=`;
  - `GET /api/v1/runs/{id}/logs?source=head-out|head-err|engine` → `text/plain; charset=utf-8`, the last 64 KiB;
  - `POST /api/v1/runs/{id}:cancel` → `202` with the run (`cancelling`) and a `cancel` command; `200` when it is already `cancelling` or terminal.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_detail_after_replay(authed_client, replayed_flaky): ...  # counts, processes in first-seen order, head null
def test_runs_paging(authed_client): ...        # 3 runs, limit=2 → 2 items + next; next page → 1 item, next null
def test_logs_tail_and_sources(authed_client): ...  # 100 KiB head.out → last 65536 bytes; engine log per engine
def test_logs_confined(authed_client, tmp_path): ...  # .nextflow.log -> /etc/passwd symlink → 404 log-not-found
def test_cancel_states(authed_client): ...      # queued → 202 cancelling; cancelled → 200 unchanged; unknown → 404
def test_openapi_snapshot(app): ...             # app.openapi() == openapi/0.0.1.json (regenerate with --update)
```

- [ ] **Step 2:** `uv run pytest packages/spectio-server/tests/api -v`: FAIL.
- [ ] **Step 3:** implement; log files are opened with `O_NOFOLLOW` after a real-path check under `launch_dir`.
- [ ] **Step 4:** the same command PASSES.
- [ ] **Step 5: Commit** `feat(api): runs, tasks, logs and cancel`.

### Task 19: UI shell and launch form

**Spec:** [ui-spec §4.6](../specs/ui-spec.md) (launch form, without stepper or review: Assumption 20), §3.1 (state words), [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout) (React, Vite, Mantine 7, TanStack) · **Depends on:** 17 · **Boards:** Launch, LaunchSnakemake (reference only; boards show more than 0.0.1, UX-227)

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/src/{main.tsx,api.ts,routes.tsx}`, `web/src/launch/{LaunchPage.tsx,schemaFields.ts}`, `web/src/launch/schemaFields.test.ts`
- Modify: `packages/spectio-server/src/spectio_server/app.py` (serve `web/dist` at `/`, behind the session)

**Interfaces:**
- Consumes: `workflows:inspect`, `POST /runs` (Task 17).
- Produces: `schemaFields(schema: JSONSchema) -> Section[]` (`Section {title, fields: Field[]}`; `Field {key, label, type: "string" | "integer" | "number" | "boolean" | "enum" | "json", required, default, help}`). Routes `/`, `/launch` and `/runs/:id`. The page title is "Launch a workflow". The fields are Pipeline directory (absolute path) and Load, the detected engine, Profile, Run name (optional) and the parameters, with the Launch button disabled while a required field is empty, the reason shown beside it.

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

**Spec:** [ui-spec §4.3](../specs/ui-spec.md) (columns in 0.0.1: Run, State, Workflow, Tasks, Started, Duration; no gauge, no Rows mode, no compare), §4.4 (header and Cancel; Summary and Tasks as tables; Logs), §3.1, [ui-spec §11](../specs/ui-spec.md) (empty state) · **Depends on:** 18, 19 · **R10 §3a:** row 13 (UX-211) · **Boards:** RunsTable, RunDetail (reference only)

**Files:**
- Create: `web/src/runs/{RunsPage.tsx,RunDetailPage.tsx,stateWord.ts}`, `tests/e2e/skeleton.spec.ts` (in the T6 Playwright setup), `tests/e2e/serve-local.sh` (`spectio init --local` in a temp directory, `spectio serve`, prints the link)
- Modify: `.github/workflows/ci.yml` (job `e2e-local`: Nextflow and Snakemake from `dev/bootstrap.sh`, then Playwright)

**Interfaces:**
- Consumes: the read API and `:cancel` (Task 18).
- Produces:
  - the runs list, polled every 5 s, with "Load more"; its empty state reads "No runs yet." with a "Launch a workflow" button;
  - the run detail, polled until terminal: a header (name, state word, short id, Cancel while `queued` or `running`, after a confirm "Cancel this run? The head job and its tasks are stopped."), a facts table (pipeline, engine, profile, started, ended, duration, head job id / state / node / exit code, failure class and message), a counts row, the processes / rules table, the tasks table (filter by state; on a failed run it defaults to `failed`), the parameters table, and the logs (head out, head err, engine log) loaded on click in `<pre>`.

- [ ] **Step 1: Write the failing test**

```ts
test("link → empty list → launch happy (Nextflow, local) → detail shows Succeeded and 65 tasks", async ({ page }) => { /* … */ });
test("cancel a running Snakemake run → Cancelled", async ({ page }) => { /* happy with a larger scale, so it still runs */ });
test("a reused link shows the expired message", async ({ page }) => { /* Review Focus 5 */ });
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

**Spec:** [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (architecture), [dev-env §4.1](../specs/dev-environment-and-testing.md) (`slurm-mini`), [T3 note](../research/spike-t3-ci-2026-10-28.md) (heads in `sbatch`, Snakemake status-check delay) · **Depends on:** 21

**Files:**
- Create: `tests/slurm/e2e.sh` (subcommands `launch nextflow|snakemake`, `cancel <engine>`, `restart`; prints `RESULT e2e-<name> pass|fail`), `tests/slurm/e2e_client.py` (stdlib HTTP client: reads the link from `spectio login --print-link`, does the exchange with `Host` and `Origin`, launches, polls, compares counts)
- Modify: `.github/workflows/pipelines-slurm.yml` (an `e2e` matrix entry on `slurm-mini`; paths also `packages/**`, `engine-bridges/**`, `web/**`), `tests/scenarios/happy-slurm-mini.yaml` (`expect` lines become checked)

**Interfaces:**
- Consumes: the wheel (Task 21), installed into `$SLURM_DATA/tools` as `dev/slurm/cluster.sh` expects; `inc` from `tests/slurm/scenarios.sh` (run as user `spx` on the submitter).
- Produces: `spectio init --runs-root $SLURM_DATA/runs --head-partition htc --head-time 60`, with `engines.extra_args.snakemake = ["--slurm-init-seconds-before-status-checks", "5"]` and `runner.poll_s = 5`.

- [ ] **Step 1: Write the failing test** (the harness). For each engine: launch the synthetic `happy` (params from `tests/pipelines/synthetic/scenarios.yaml`, profile `slurm`); expect `queued` → `running` with `head.state` `RUNNING` and a native id → `succeeded`. The per-process counts must equal `tests/pipelines/synthetic/golden/{nextflow-26.10.4,snakemake-9.27.1}/happy.tsv`, `sacct` is absent (no accounting), the head end state comes from `head.exit`, `spool_drops` stays empty, and `squeue --me` lists no `spectio-` job at the end.
- [ ] **Step 2:** `bash dev/slurm/cluster.sh up mini && CLUSTER=mini bash tests/slurm/e2e.sh launch nextflow`: FAIL.
- [ ] **Step 3:** fix what the cluster reveals, each fix with a unit test in the task that owns the code.
- [ ] **Step 4:** `CLUSTER=mini bash tests/slurm/e2e.sh launch nextflow` and `… launch snakemake` print `RESULT e2e-launch-<engine> pass`; the `e2e` job is green in `pipelines-slurm.yml`.
- [ ] **Step 5: Commit** `test(slurm): end to end launch and monitor on slurm-mini`.

### Task 23: End to end Cancel and server restart

**Spec:** [schedulers §3.1](../specs/schedulers-and-monitoring.md) (runner restart, cancel), [dev-env §4.1](../specs/dev-environment-and-testing.md) (planned: drain then cancel, one test per engine; restart while a head runs), [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) "Server restart" · **Depends on:** 22 · **R10 §3a:** row 6; D4

**Files:**
- Modify: `tests/slurm/e2e.sh`, `tests/slurm/e2e_client.py`

- [ ] **Step 1: Write the failing tests**
  - `cancel <engine>`: launch `happy` with a larger `scale`, so it still runs; once `running` with tasks running, `POST :cancel`. Expect `cancelling` → `cancelled` within grace + 120 s, no `spectio-` job in `squeue --me`, and no attempt left `running` (they end `aborted` or `failed`).
  - `restart`: launch Nextflow `happy`; at the first `succeeded` task, kill `spectio serve` (SIGKILL), wait 20 s and start it again. The head is adopted by name (no second `sbatch`: the submit log shows one call); the run ends `succeeded`; the counts equal the golden; `events` has no duplicate `event_id`; a new link is needed (the old cookie gets 401).
- [ ] **Step 2:** `CLUSTER=mini bash tests/slurm/e2e.sh cancel nextflow`: FAIL.
- [ ] **Step 3:** fix what the runs reveal (unit tests in the owning tasks).
- [ ] **Step 4:** `cancel nextflow`, `cancel snakemake` and `restart` print `RESULT … pass`, locally and in the `e2e` job.
- [ ] **Step 5: Commit** `test(slurm): cancel and restart on slurm-mini`.

---

## Out of scope

Everything that [dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version) marks "no" for 0.0.1 or "later (open)":
- QC checks and gates in every form;
- Kubernetes, a shared server and remote runners;
- users, sign-in, accounts and roles;
- relaunch and the parameter history (#61);
- visualisation (DAG, timelines, charts, comparison);
- runs started from a terminal;
- full scheduler monitoring (task jobs, pending reasons, accounting, capacity);
- Postgres, Compose and Helm;
- the depictio hand-off, WES, MCP, embedded elements and LabID.

Also not in P1:
- SSE (Assumption 7) and pause / resume;
- a workflow catalogue and Git URLs (D2);
- `POST /runs:validate` and file checks;
- per-task logs;
- the offline-head pre-steps for sites without egress (**[to be validated per site]**);
- the Snakemake head on the login node (R10 C7);
- slurmrestd;
- the spike sec-single-mode (R10 C6);
- everything before the 0.0.1 tag (R10 C5–C8).

## Done when

- [ ] Tasks 1–23 are merged, each with its tests first and its `review-code` pass (Assumptions, Process).
- [ ] On `slurm-mini` in CI (`pipelines-slurm.yml`, job `e2e`), through a token-link session, the synthetic Nextflow and Snakemake `happy` runs launch with their heads in `sbatch`, end `succeeded`, and match the golden counts per process (Task 22).
- [ ] A running run of each engine cancels to `cancelled` with no job left, and a server killed while a Nextflow head runs adopts it on restart, with no duplicate event (Task 23).
- [ ] Each of §15.3 requirements 1–7 has passing `test_req<N>_*` tests (Tasks 3, 11–16).
- [ ] The Playwright smoke passes on the local executor: link, launch, list, detail, cancel (Task 20).
- [ ] `tests/packaging/test_wheel.sh` passes: one installable wheel with the UI and both bridges, and a `spectio` environment under 80 MB (Task 21).
- [ ] Tier 0 is green on every package: ruff, mypy (`--strict` on `spectio-sdk`), `lint-imports`.
- [ ] api §14 (driven runs) is written, and every spec the code contradicted is updated with a log entry; `python3 tools/docs/check.py` passes.
- [ ] Thomas has confirmed or corrected the Assumptions above (the inbox entries named there), before the 0.0.1 tag.

## Open questions

- **D2 and D3** (inbox #34 for SR-056, inbox #55) are reserved for Thomas; the plan follows R10's recommended options as Assumptions 2 and 3.
- **The bootstrap-page gap** (Assumption 8): §15.3 req. 2 should name the session-free page; it is to be recorded in the next apply pass.
- **Where the Snakemake mapping lives**: Assumption 16 replaces the **[to be validated]** of api §7.2 for 0.0.1. Thomas, or spike T1's resume check (#32), may change it.
