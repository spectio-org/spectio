# Code review · FU-P3-87a: the pipeline catalog file and the shared location checks

`review-code` on `autopilot/P3-fu87a`, base `a24f5af`, head `9acea98e` (two commits: `8b070be4` the build, `9acea98e` the round 1 fix), 2026-11-10. Owner: [api §5.6](../../specs/api-and-data-model.md#56-pipeline-catalog-001). Progress: [P3 · M9](../../progress/W5/P3-M9.md#fu-p3-87a-the-pipeline-catalog-file-and-the-shared-location-checks). Format: [`README.md`](../README.md).

Outside `docs/`: 11 files, +561 −167 (`git diff --shortstat a24f5af..HEAD`): `spectio/locations.py` (new), `spectio/catalog.py` (new), `envfile.py` generalised, `api/workflows.py` using the shared checks, tests.

| Round | Head | code-reviewer | security-reviewer | Fix |
|---|---|---|---|---|
| 1 | `8b070be4` | **approve** (0 blockers, 0 majors, 6 minors: CR-P3FU87A-01 to -06) | **changes** (0 blockers, 1 major, 1 minor: SEC-P3FU87A-01, -02) | `9acea98e` (SEC-01) |

```text
CODE  step=P3-fu87a  review=approve b/M/m=0/0/6  security=approve b/M/m=0/0/1  rounds=2  simplify=skipped -0/+0  tests=pass
```

The security major was fixed and its fix check passed (resolved SEC-P3FU87A-01, unresolved none); there was no separate round-2 review record.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-P3FU87A-01 | major | `locations.git_url` called `urlsplit` outside a `try`; its `ValueError` quotes the value (credentials with a fullwidth `@`, `https://[zz]/a`), so inspect and `POST /runs` answered 422 with it. Breaks api §5.6 SEC-PRE-FU87-02. | Fixed in `9acea98e`: a fixed `ValueError("not a URL")`; tests in `test_locations.py` and `test_hardening.py` failed before the fix |
| SEC-P3FU87A-02 | minor | `resolve` keeps its own length cap and control-character check beside `check_location` | Open (batch `code-simplifier`) |
| CR-P3FU87A-01 | minor | `check_default` runs a full `model_dump` per entry to get a name | Open (simplify) |
| CR-P3FU87A-02 | minor | Same duplication as SEC-02 | Open (simplify) |
| CR-P3FU87A-03 | minor | Generalising `envfile` changed messages already shown (`is a built-in name`, `an environment name is not valid`, `the environments file`); no test covers them | Open |
| CR-P3FU87A-04 | minor | `Kind.max_bytes` is 64 KiB in both kinds; `File.environments` is an alias for 5 call sites | Open (simplify) |
| CR-P3FU87A-05 | minor | The hand-edit test only asserts `entries != first.entries`, not the edited value | Open |
| CR-P3FU87A-06 | minor | +521 −167 against a target of about 300 (about 240 lines are tests, much of `locations.py` moved from `workflows.py`) | Disclosed |

## Test command and result

```bash
uv run --locked pytest packages/spectio/tests/test_locations.py packages/spectio/tests/test_catalog.py \
  packages/spectio/tests/test_envfile.py packages/spectio-server/tests/api/test_hardening.py -q
```

```text
108 passed in 2.08s
```

The full suite was not run; CI runs it.
