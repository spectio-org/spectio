# Code review · FU-P3-87b: the catalog routes and the params file in inspect

`review-code` on `autopilot/P3-fu87b`, base `6cd4831`, head `f864fd88` (two commits: `66ecd156` the step, `f864fd88` the round-1 fix), 2026-11-10. Owner: [api §5.6](../../specs/api-and-data-model.md#56-pipeline-catalog-001). Progress: [P3 · M9, FU-P3-87b](../../progress/W5/P3-M9.md#fu-p3-87b-the-catalog-routes-and-the-params-file-in-inspect). Format: [`README.md`](../README.md).

Round 1: both reviewers asked for changes. The findings below are summaries relayed by the worker. Ids are as reported.

## Findings

| Id | Severity | Finding | State |
|---|---|---|---|
| CR-P3FU87B-01 | blocker | A params file that parses (`NaN`, `.inf`, a date key) makes inspect answer 500; api §5.6 says `values: null` and an `error` | fixed, test first |
| SEC-P3FU87B-01 | major | A non-string YAML key raises `TypeError` in `read_params` (and in `inspect_dir`): 500 | fixed, test first |
| SEC-P3FU87B-02 | minor | `NaN`, `Infinity`, `1e999`, `.nan`, `.inf` show as `null` with no error | fixed, test first |
| CR-P3FU87B-02 | minor | `catalog.py` copies the route helpers of `environments.py` | open |
| CR-P3FU87B-03 | minor | `_params` builds the 503 by hand instead of `environments.offline` | open |
| SEC-P3FU87B-03 | minor | `read_params` runs outside the file pool | open |
| SEC-P3FU87B-04 | minor | No test for the `OSError` branch after open | open |

## The fix (`f864fd88`)

- `_jsonable` uses `allow_nan=False`; JSON goes through it as YAML did.
- `read_params` and `inspect_dir` catch `TypeError`. The message is fixed ("not JSON" / "not YAML"); the file is never quoted.
- 7 new cases in `test_req18_catalog_params_read_failures` failed before the fix. After it: 158 passed (`test_catalog.py`, `test_launch.py`, `test_relaunch.py`), 21 passed (`test_hardening.py`); ruff and mypy clean.
- Not changed: `json.loads` in `schema_of` still lets `NaN` through (outside these findings).

Fix check: CR-P3FU87B-01, SEC-P3FU87B-01 and SEC-P3FU87B-02 resolved; none unresolved. `code-simplifier` runs once per batch.

```text
CODE  step=P3-fu87b  review=approve b/M/m=0/0/2  security=approve b/M/m=0/1/3  rounds=2  simplify=skipped -0/+0  tests=pass
```
