# Code review · FU-P3-126, stall check for jobs gone from squeue and sacct

`review-code` on `autopilot/P3-fu126-stall`, base `4124268d`, 2026-11-23. Two commits: the step `101abe7a` and the fix `df8012c4`. Behaviour is owned by [schedulers §3.9](../../specs/schedulers.md). Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Format: [`README.md`](../README.md).

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `101abe7a` | **changes** (1 blocker, 3 minors) | **approve** (4 minors) |
| 2 | `df8012c4` | fix check: CR-01, CR-02, SEC-01 resolved | not re-run |

```text
CODE  step=P3-fu126-stall  review=changes->resolved b/M/m=1/0/3  security=approve b/M/m=0/0/4  rounds=2  simplify=skipped -0/+0  tests=not-run-here
```

Counts are round 1. **Test-first** for the fixes. The mkdocs build and the full suite run in CI.

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU126-STALL-01 | blocker | Tasks that finished normally could be flagged stalled, and the stall outlived WATCH_S | fixed in `df8012c4` (a confirming read is needed; the stall is dropped with the run's state) |
| CR-P3FU126-STALL-02 | minor | `squeue_ids` added the base ID for every array line | fixed in `df8012c4` (pending range lines only) |
| CR-P3FU126-STALL-03 | minor | `doctor` prints `ok stalled_runs none` when no squeue is recorded | open |
| CR-P3FU126-STALL-04 | minor | pollers share a `try` with `step()` | open |
| SEC-P3FU126-STALL-01 | minor | doctor traceback on out-of-range stall values | fixed in `df8012c4` (OverflowError caught) |
| SEC-P3FU126-STALL-02 | minor | stall file written on the accounting thread, every cycle | open |
| SEC-P3FU126-STALL-03 | minor | wall clock passed to the limiter | open |
| SEC-P3FU126-STALL-04 | minor | squeue failures logged as sacct | open |

## Assumptions

- Slurm's MinJobAge default (300 s) applies on slurm-mini **[to be validated]**.
- A run is stalled only after a read made past the grace still lists the task as running.
