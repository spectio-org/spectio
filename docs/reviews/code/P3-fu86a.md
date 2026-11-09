# Code review · FU-P3-86a: the run's own environment snapshot

`review-code` on `autopilot/P3-fu86a`, base `0ad57dd7`, head `807ef5b1` (three commits: `6e607aaf`, `ad5e2719`, `807ef5b1`), 2026-11-09. The step is FU-P3-86a of [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86), the first task of its build plan; the behaviour is owned by [api-and-data-model §5.4](../../specs/api-and-data-model.md#54-environments-001) ("The database is not the source of any run's environment", Resume). Progress: [P3 · M9, FU-P3-86a](../../progress/W5/P3-M9.md#fu-p3-86a-the-runs-own-environment). Format: [`README.md`](../README.md).

Outside `docs/`: 24 files, +1,181 −94 over the base (`git diff --shortstat 0ad57dd7..HEAD -- . ':!docs'`): `packages/spectio/src/spectio/environments.py` is new (174 lines), as are migration `0011_run_environment.py` and two test files; the rest changes `failure.py`, `resume.py`, `bootstrap.py`, `headscript.py`, `config.py`, the run routes, `web/src/api.ts` and the OpenAPI snapshot (+191). The two wheel content lists gain one line each.

## What the step does

- **The snapshot.** `spectio.environments` holds the strict model and its validators (`fullmatch`, strict `int` and `str`), shared by the routes, the runner and the rebuild, and the built-ins from `Settings`. A new column `runs.environment` (migration `0011`) holds `{name, label, executor, slurm, local, state}`, written at launch and Resume (the built-in of the server's kind until FU-P3-86c) and at rebuild from the manifest. `environments.name` is added for `ensure_tenancy`, which keys on it.
- **Every per-run decision reads the snapshot.** `failure.on_slurm`, the `sacct` call and its `local` reason, `Accounting`, and the copied command in `resume.py` read the run's own column, never `settings.executor` or an `environments` row. `read_as` (round 2) applies the Resume rule to a `not_recorded` or `not_readable` column.
- **API.** `environment` on `GET /runs` and `GET /runs/{id}`; the OpenAPI snapshot and `web/src/api.ts` follow.
- **Hardening.** `SlurmOpts` partition and account take the SLURM name pattern; Snakemake resource values go out as Python string literals (SEC-PRE-FU86-01); `--local-cores 2` is the last argument of every Snakemake SLURM launch.

## Review rounds

Finding IDs restart in each round, so a bare `CR-P3FU86A-04` is ambiguous: the table below says the round. The reports were relayed in summary, so the text of a finding is as relayed; where a finding's text was not relayed, it says so.

| Round | Head | code-reviewer | security-reviewer | Fix |
|---|---|---|---|---|
| 1 | `6e607aaf` | **changes** (0 blockers, 1 major, 4 minors, plus simplify: CR-P3FU86A-01 to -06) | **approve** (0 blockers, 0 majors, 4 minors: SEC-P3FU86A-01 to -04) | `ad5e2719` (CR-01); the rest in the round 2 fix |
| 2 | `ad5e2719` | **changes** (0 blockers, 1 major, 2 minors: CR-P3FU86A-02, -03, -04) | **approve** (0 blockers, 0 majors, 1 minor: SEC-P3FU86A-01) | `807ef5b1` ([Round 2 fix](#round-2-fix)) |
| 3 | `807ef5b1` | **approve** (0 blockers, 0 majors, 2 minors: CR-P3FU86A-R3-01, -R3-02 simplify) | **approve** (0 blockers, 0 majors, 2 minors: SEC-P3FU86A-R3-01, -R3-02) | none |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | | |

```text
CODE  step=P3-fu86a  review=approve b/M/m=0/0/2  security=approve b/M/m=0/0/2  rounds=3  simplify=skipped -0/+0  tests=pass
```

Round 3 approved with no fix required, so its findings are not fixed in this task.

**Test command and result** (re-run by `doc-writer` at `807ef5b1`; the worker's full gate was pytest 1248 passed, 1 skipped, `vitest run api.test.ts` 35 passed, `tsc`, `ruff` and `mypy` clean):

```bash
uv run --locked pytest packages/spectio-server/tests/api/test_environment_snapshot.py \
  packages/spectio-server/tests/api/test_failure.py \
  packages/spectio-server/tests/test_efficiency.py \
  packages/spectio/tests/test_environments.py \
  packages/spectio/tests/test_headscript.py -q
```

```text
195 passed, 1 deselected in 26.06s
```

**One flaky test.** `test_sigterm_stops_cleanly[15]` failed once in the full run, under load, and passed on every rerun. It is not in the five files above and the step does not touch it. It is not fixed here and is listed in the follow-ups.

## Findings

| Id | Round | Severity | Finding | Status |
|---|---|---|---|---|
| CR-P3FU86A-01 | 1 | not relayed | Migration `0011` wrote `executor` from the `environments` row, while a rebuild from the manifest writes it null, so an old SLURM run changed reading after an index rebuild. | fixed in `ad5e2719`: the backfill writes exactly `run_column(None)` |
| CR-P3FU86A-02, -03 | 1 | not relayed | The round 1 summary named these two IDs and the counts (1 major, 4 minors) but not their text or severity. | see the round 2 findings, which reuse the numbers |
| CR-P3FU86A-04 | 1 | minor | `nextflow_config` passed partition and account to `_groovy` without the `slurm_name` check the Snakemake path applies. | fixed in `807ef5b1`: `slurm_name(...)` first; `test_nextflow_config_on_slurm` |
| CR-P3FU86A-05 | 1 | minor | A 0.0.1 database re-initialised from local to SLURM holds one `environments` row per built-in kind; runs keep referencing the oldest. | recorded in [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86), no code change: no decision reads that row |
| CR-P3FU86A-06 | 1 | simplify | A simplification of the step's own diff; its text was not relayed. | open: left to the batch `code-simplifier` |
| SEC-P3FU86A-01 | 1 | minor | The Nextflow re-check: partition and account must be checked again where the config file is built (the same point as CR-04). | fixed in `807ef5b1` (with CR-04 above) |
| SEC-P3FU86A-02 | 1 | minor | `--local-cores 2` could be lifted by `extra_args`. | fixed in `807ef5b1`: last argument; `test_snakemake_slurm_local_cores_last` |
| SEC-P3FU86A-03 | 1 | minor | The migration copied the `environments` row's `kind` into the snapshot unchecked (the `executor` of the backfilled runs). | closed by `ad5e2719`: the backfill no longer reads `kind` into the snapshot |
| SEC-P3FU86A-04 | 1 | minor | `environments.name` is not unique. | recorded with CR-05 in inbox #133; no code change in this task |
| CR-P3FU86A-02 | 2 | **major** | A run whose `runs.environment` is not `recorded` was read as local, against the Resume rule of api §5.4. | fixed in `807ef5b1`: `read_as` ([Round 2 fix](#round-2-fix)) |
| CR-P3FU86A-03 | 2 | minor | A bad `[slurm]` value and the `except ValidationError` branch of `environments._slurm`. | fixed in `807ef5b1`: `Settings()` raises, as intended; the branch is commented |
| CR-P3FU86A-04 | 2 | minor | The `Run` schema comment in `web/src/api.ts` had moved away from `export interface Run`. | fixed in `807ef5b1` |
| SEC-P3FU86A-01 | 2 | minor | The copied command of a `not_recorded` run on a SLURM server was the local one. | fixed in `807ef5b1`, with CR-02 |
| CR-P3FU86A-R3-01 | 3 | minor | The `not_readable` to `not_found` mapping of a run's resources was only in the inbox, not in [api §5.4](../../specs/api-and-data-model.md#54-environments-001) (the `efficiency` reasons, line 238 of the spec, list `not_found`). | closed in this task's docs: note "Built 2026-11-09, FU-P3-86a" in api §5.4 |
| CR-P3FU86A-R3-02 | 3 | simplify | A test-readability simplification in the step's tests; its text was not relayed beyond that. | open: left to the batch `code-simplifier` |
| SEC-P3FU86A-R3-01 | 3 | minor | A bare `--` in a Snakemake `extra_args` turns the trailing `--local-cores 2` into a target, so the cap is lost again. | open: FU-P3-86c ([inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86)) |
| SEC-P3FU86A-R3-02 | 3 | minor | `runner/loop.py:284` (Resume) still builds the SLURM values from `settings` (`slurm=self.settings.slurm if self.settings.executor == "slurm" else None`), not from the run's snapshot; and there is no `422` on `environment` for a `not_readable` parent. | open: FU-P3-86c (its Resume rules) |

## For the Progress page

- **Built:** `spectio.environments` (model, validators, built-ins, `run_column`, `read_as`, `executor_of`), migration `0011`, `runs.environment` on the run routes, the per-run reads in `failure.py` and `resume.py`, `--local-cores 2` last, the SLURM name check on the Nextflow path.
- **Open, minor:** SEC-R3-01 and SEC-R3-02 go to FU-P3-86c, which builds Resume's rules and the payload check. CR-R3-02 and CR-06 go to the batch `code-simplifier`. SEC-04 and CR-05 are recorded in inbox #133.
- **Flaky:** `test_sigterm_stops_cleanly[15]`, once under load.
- **Not done:** the environments file (-86b), the launch with an `environment` (-86c), the routes (-86d), any UI (-86e to -86g).

## Round 2 fix

Base `ad5e2719`. Each finding of round 2, and the round 1 finding that was still open:

- **CR-P3FU86A-02 (major), SEC-P3FU86A-01 (minor).** A run whose `runs.environment` is not `recorded` was read as local. New `spectio.environments.read_as(column, settings)` applies the spec's Resume rule: `recorded` is the run's own snapshot, `not_recorded` the built-in of the server's kind (today's behaviour), `not_readable` and a run started from a terminal nothing. `failure.on_slurm` and `resume._slurm` read through it, so on a SLURM server a `not_recorded` run is asked of `sacct` and its copied command is the SLURM one with `--local-cores 2`. A `not_readable` run gets `command: null` and the existing reason `not_found` for its resources, never `local`; its jobs are never asked. Tests: `test_req18_snapshot_read_as`, `test_req18_snapshot_not_recorded_is_the_server_kind` (replaces `test_req18_snapshot_unknown_executor_is_not_slurm`, rewritten to the decided rule), `test_req18_snapshot_not_readable_has_no_command`; the docstrings of `test_eff_unavailable` and the `Run` helper say the `local` case is a `not_recorded` run on a local server.
- **SEC-P3FU86A-02 (minor).** `--local-cores 2` is now the last argument of every Snakemake SLURM launch, after `extra_args`, with a workflow profile too, so `extra_args` cannot lift it. Test: `test_snakemake_slurm_local_cores_last`; `test_snakemake_concurrency_without_a_profile` expects `extra_args` just before it.
- **CR-P3FU86A-04 (round 1) and the round 1 security finding.** `nextflow_config` passes partition and account through `slurm_name(...)` before `_groovy`, as the Snakemake path does. `test_nextflow_config_on_slurm` expects a `ValueError` for `lab'x` and `h'tc`.
- **CR-P3FU86A-04 (round 2).** `web/src/api.ts`: the `Run` schema comment is back directly above `export interface Run`.
- **CR-P3FU86A-03 (round 2).** A bad `[slurm]` value makes `Settings()` raise, and that stays. The `except ValidationError` branch of `environments._slurm` says that only a hand-built Settings reaches it.
- **CR-P3FU86A-05.** Recorded in inbox #133, no code change: 0.0.1 may hold one `environments` row per built-in kind, with runs referencing the oldest.

No API shape changed: the OpenAPI snapshot is unchanged.
