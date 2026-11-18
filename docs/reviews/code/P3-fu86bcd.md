# Code review · FU-P3-86b to -86d: the environments file, launch with an environment, and the routes

`review-code` on `autopilot/P3-fu86bcd`, base `b41952c8`, head `215eabb5` (three commits: `c39dee74` the build, `e111f87a` the round 1 fix, `215eabb5` the round 2 fix), 2026-11-09. The step is FU-P3-86b, -86c and -86d of the build plan of [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86), built as one task after [FU-P3-86a](P3-fu86a.md). The behaviour is owned by [api-and-data-model §5.4](../../specs/api-and-data-model.md#54-environments-001) and [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 18. Progress: [P3 · M9, FU-P3-86b to -86d](../../progress/W5/P3-M9.md#fu-p3-86b-to-86d-the-environments-file-launch-with-an-environment-and-the-routes). Format: [`README.md`](../README.md).

Outside `docs/`: 25 files, +2,464 −69 over the base (`git diff --shortstat b41952c8..HEAD -- . ':!docs'`): `spectio/envfile.py` (new, 303 lines) and `spectio_server/api/environments.py` (new, 300 lines) with 836 lines of new tests, `runner/headscript.py` (+135), `runner/loop.py`, `runner/types.py`, `resume.py`, `api/relaunch.py`, `api/runs_write.py`, `api/models.py`, `app.py`, `cli/doctor.py`, `web/src/api.ts`, the OpenAPI snapshot (+596) and one line in each wheel contents list.

## What the step does

- **FU-P3-86b, the file** (`spectio.envfile`). `environments.toml` next to `spectio.toml`, read without following a link: the directory opened with `O_DIRECTORY|O_NOFOLLOW`, the file with `openat` and `O_NOFOLLOW|O_NONBLOCK`, both checked with `fstat`, at most 64 KiB + 1 byte read. Five states: `missing`, `ok`, `refused`, `invalid`, `unreachable`. A write holds one process lock, renders the text, parses it back, checks the identity (`fstat` fields and the SHA-256) again, then writes through `write_file` and renames. It never writes over a `refused` or `invalid` file. The server reads it in the file pool and caches it by identity; `spectio doctor` prints the path, state and default.
- **FU-P3-86c, the launch.** `environment` (by name; the default when absent) on `POST /runs` and `POST /runs:validate`. The snapshot goes into the manifest, `runs.environment` and the payload. The runner validates the payload's snapshot with the strict model and builds `LaunchSpec` from it, never from `settings` (SEC-P3FU86A-R3-02). `headscript.py` maps the values as the table of api §5.4 says. A bare `--` in Snakemake `extra_args` is refused (SEC-P3FU86A-R3-01). The first line of `head.out` names the environment. Resume applies the launch rules to the parent's snapshot. The launch template gains `environment` and `environment_notice`.
- **FU-P3-86d, the routes.** `GET` and `POST /environments`, `GET`, `PUT` and `DELETE /environments/{name}` (`If-Match` required, `*` refused), `POST /environments/{name}:make-default`; mounted in `create_app`'s conditional set; four new problem slugs; a log line per write; the OpenAPI snapshot and `web/src/api.ts`.

## Review rounds

Finding IDs restart in each round, so a bare `CR-P3FU86BCD-03` is ambiguous: the table below says the round.

| Round | Head | code-reviewer | security-reviewer | Fix |
|---|---|---|---|---|
| 1 | `c39dee74` | **changes** (0 blockers, 1 major, 5 minors, 3 simplify: CR-P3FU86BCD-01 to -09) | **approve** (0 blockers, 0 majors, 3 minors: SEC-P3FU86BCD-01 to -03) | `e111f87a` (CR-01, with SEC-03) |
| 2 | `e111f87a` | **approve** (0 blockers, 0 majors, 2 minors, 1 simplify: CR-P3FU86BCD-02 to -04) | **approve** (0 blockers, 0 majors, 2 minors: SEC-P3FU86BCD-01, -02) | `215eabb5` ([Round 2 fix](#round-2-fix)) |
| 3 | `215eabb5` | **approve** (0 blockers, 0 majors, 2 minors: CR-P3FU86BCD-04, -05) | **approve** (0 blockers, 0 majors, 1 minor: SEC-P3FU86BCD-02) | none |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | | |

```text
CODE  step=P3-fu86bcd  review=approve b/M/m=0/0/2  security=approve b/M/m=0/0/1  rounds=3  simplify=skipped -0/+0  tests=pass
```

Round 3 approved with no fix required, so its findings are not fixed in this task.

**Test command and result** (re-run by `doc-writer` at `215eabb5`; the worker's full gate was green):

```bash
uv run --locked pytest packages/spectio/tests/test_envfile.py \
  packages/spectio-server/tests/api/test_environments.py \
  packages/spectio/tests/test_headscript.py packages/spectio/tests/test_environments.py \
  packages/spectio/tests/test_doctor.py packages/spectio-server/tests/api/test_openapi.py -q
```

```text
234 passed, 1 deselected in 22.20s
```

The two tests of the round 2 fix, run alone, pass (`-k "io_error_unreachable or no_file_bytes"`: 3 passed, 30 deselected). The worker ran them before the fix and both failed.

## Findings

| Id | Round | Severity | Finding | Status |
|---|---|---|---|---|
| CR-P3FU86BCD-01 | 1 | **major** | An `OSError` reading or writing `environments.toml` (ESTALE, EIO, EDQUOT, ENOSPC, EACCES) gave a 500, and every `POST /runs` reads the file, so a launch with a built-in failed too (api §5.4: built-ins work in every state). | fixed in `e111f87a`: a read error is `unreachable`, a write error is `503 runner-offline`; `test_req18_routes_io_error_on_read`, `test_req18_routes_io_error_on_write` |
| CR-P3FU86BCD-02 | 1 | minor | The `invalid` detail could still hold file bytes: `_QUOTED` missed repr strings with escaped quotes (`"secretXY'Z\"leakme"` declared twice). | fixed in `215eabb5`, with SEC-P3FU86BCD-01 of round 2 (the same leak) |
| CR-P3FU86BCD-03 | 1 | minor | The launch template says "The environment X of this run no longer exists" when the file is only `unreachable`, `refused` or `invalid`: `view()` lists the built-ins only then, so a file environment looks deleted. | open: FU-P3-103 (`api/relaunch.py:336`) |
| CR-P3FU86BCD-04 | 1 | minor | Assumption 2: with the file `unreachable`, a launch with no `environment` falls back to the server's built-in, though the user may have made a file environment (another account or partition) the default. | recorded as a question: [inbox #136](../inbox.md#136-assumed-the-environments-file-launches-while-it-is-unreachable-and-what-a-409-says-fu-p3-86b-to-86d), choice 1 |
| CR-P3FU86BCD-05 | 1 | minor | The deviations from api §5.4 (Assumptions 1 to 8) are not recorded; 5, 3 and 7 matter most. | closed in this task's docs for the three the code shows: the note "Built 2026-11-09, FU-P3-86b to -86d" in api §5.4, and [inbox #136](../inbox.md#136-assumed-the-environments-file-launches-while-it-is-unreachable-and-what-a-409-says-fu-p3-86b-to-86d) choice 2. The worker's own list of eight is in no file of the repository, so the other five are not recorded: see the Progress page, open items |
| CR-P3FU86BCD-06 | 1 | minor | `test_req18_snapshot_later_cores_wins_on_snakemake` runs whatever Snakemake is on PATH, but its docstring and the code comment cite 9.27.1 `cli.py:2103-2109`. | open: FU-P3-103 (skip unless `snakemake --version` is 9.27.1) |
| CR-P3FU86BCD-07 | 1 | simplify | `make_default` rebuilds the entry list (built-ins plus the file's entries with `_usable`) with the same lines as `view()`. | open: left to the batch `code-simplifier` |
| CR-P3FU86BCD-08 | 1 | simplify | `BUILTIN = frozenset({"local", "slurm"})` repeats `spectio.environments.RESERVED` without `new`. | open: left to the batch `code-simplifier` |
| CR-P3FU86BCD-09 | 1 | simplify | `_cap(local, key)` chooses its bounds from a string key and is called six times; typed accessors would be shorter and checked by mypy. | open: left to the batch `code-simplifier` |
| SEC-P3FU86BCD-01 | 1 | minor | Text from the file still reaches the `invalid` detail: `_place` keeps any location part that matches NAME (`environments.mylab.local.secret-hunter2`), and `check_default` echoes a dangling `default`. The characters are a closed set and the reader is the same user: hardening. | open: FU-P3-103 |
| SEC-P3FU86BCD-02 | 1 | minor | The runner checks the payload's snapshot for types, not against its own server kind: a payload with `executor: slurm` on a `--local` server would launch `--executor slurm`; an uncapped `local` on a SLURM server runs with no cap. `choose()` and `resume_snapshot()` stop both today; this is defence in depth. | open: FU-P3-103 |
| SEC-P3FU86BCD-03 | 1 | minor | An `OSError` from the write (EDQUOT, ENOSPC, EACCES) escaped `Store.update` as a 500. | fixed in `e111f87a`, with CR-01 |
| CR-P3FU86BCD-02 | 2 | minor | `read_file` still said it returns the file "in one of its states but `unreachable`", after `_read_in` began to return `unreachable`. | fixed in `215eabb5`: the module and `read_file` docstrings describe the five states |
| CR-P3FU86BCD-03 | 2 | minor | The same I/O error got a different state by place: ESTALE or EIO at `os.open` of the file or its directory was `refused` (a 409 telling the user to fix a mode), at `fstat` or `read` it was `unreachable` (503). | fixed in `215eabb5` ([Round 2 fix](#round-2-fix)) |
| CR-P3FU86BCD-04 | 2 | simplify | `Store.update` builds `Exception(detail)` only so that `_offline` can call `str()`; `envfile.update` repeats the same two-line `unreachable` to `Stalled` check after both reads. | open: left to the batch `code-simplifier` |
| SEC-P3FU86BCD-01 | 2 | minor | A key holding both quote kinds, declared twice, left part of itself in the `invalid` detail (`Cannot declare (…, …b"cTOKEN') twice`). Low impact: the file is the user's and the detail goes to the session holder and `spectio doctor`. | fixed in `215eabb5` ([Round 2 fix](#round-2-fix)) |
| SEC-P3FU86BCD-02 | 2 | minor | `envfile.update` takes the write lock inside a file-pool worker (`Store.update` runs it through `files.run`, then `_WRITE.acquire(timeout=5.0)`). After one hung write, each further write holds one of the 4 workers for 5 s after its own request returned 503, so reads of logs and task files become `Stalled` too. Self-healing; req. 13 says a lock wait should not use a bounded I/O worker. | open: FU-P3-103 |
| CR-P3FU86BCD-04 | 3 | minor | api §5.4 still says `unreachable` means only the pool timeout; the code now also makes an I/O error at open or read of the file or its directory `unreachable`, and a write then gets `Stalled`. | closed in this task's docs: the `unreachable` line of api §5.4 |
| CR-P3FU86BCD-05 | 3 | minor | The directory `fstat` failure changed from `refused` to `unreachable` in `215eabb5`, with no test; the new parametrized test patches only `os.open`. | open: FU-P3-103 |
| SEC-P3FU86BCD-02 | 3 | minor | A non-regular file whose `open()` fails (a UNIX socket gives ENXIO, a device node ENODEV, possibly EOPNOTSUPP) is now `unreachable`, not `refused`: a socket at `environments.toml` reads as a transient outage (503, retried), where it was a permanent 409. Nothing leaks, nothing is written: hardening and consistency. | open: FU-P3-103 |

## For the Progress page

- **Built:** `spectio.envfile` (the five states, the locked write), `spectio_server/api/environments.py` (the store, the six routes, `choose`), the launch with `environment`, the payload check, the head script's mapping, Resume's rules, the launch template, `spectio doctor`, the OpenAPI snapshot.
- **Open, minor:** CR-P3FU86BCD-03 and -06 (round 1), SEC-P3FU86BCD-01 and -02 (round 1), SEC-P3FU86BCD-02 (round 2), CR-P3FU86BCD-05 and SEC-P3FU86BCD-02 (round 3) go to FU-P3-103. The five simplify items go to the batch `code-simplifier`. CR-04 (round 1) is a question in inbox #136.
- **Not done:** the screens (FU-P3-86e to -86g). No real SLURM cluster and no real NFS were used: the I/O errors are `os.open` patched to raise.

## Round 2 fix

Base `e111f87a`. Test first: both tests failed before the fix.

- **CR-P3FU86BCD-03 (round 2).** An open that fails with `EACCES`, `EPERM`, `ELOOP` or `ENOTDIR` is `refused` (`_REFUSED`). Any other `OSError` at open or `fstat`, of the file or of its directory, is `unreachable`: `_open_dir` raises a new `_Unreachable`, which `read_file` maps to `EnvFile("unreachable")` and `update` to `Stalled`. New test `test_req18_file_open_io_error_unreachable[directory|file]` patches `os.open` to raise `ESTALE` and asserts that a read gives `unreachable` and `update` raises `Stalled`. The docstrings (module, `read_file`) say the split, which also closes CR-P3FU86BCD-02 of round 2.
- **SEC-P3FU86BCD-01 (round 2).** The `_QUOTED` scrub is removed. A `tomllib` message is cut at its first quote or `(`, and only its place is kept: `(at line N, column M)` or `(at end of document)` (regex `_AT`). The leak was reproduced first: `Cannot declare (..., '...b"cTOKEN') twice`; it now gives `not TOML: Cannot declare (at line 2, column 34)`. `test_req18_file_invalid_detail_has_no_file_bytes` declares a quoted key holding `'` and `"` twice and asserts that the detail ends with the place and holds none of `SECRET`, `TOKEN`, `'`, `"` or a backslash. It checks the key's fragments and its quote and backslash characters, not every letter, because the fixed text ("not TOML: Cannot declare") shares common letters with any key.
- **Trade-off.** A message that quotes an expected token loses it: `Expected ']' ...` becomes `not TOML: Expected (at line 1, column 16)`. The line and column are still there. Recorded in the `invalid` line of api §5.4.
