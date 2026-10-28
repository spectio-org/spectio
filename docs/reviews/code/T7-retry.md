# Code review · T7-retry, Nextflow retry and public runner limits

`review-code` on `autopilot/T7-retry`, range `origin/autopilot/integration...a29fb74`, 2026-10-28. The step applies triage findings SPK-T7-05 (retry a failed Nextflow entry once with `-resume`) and SPK-T7-02 (public runner limits from the measurement in nightly run 40649538349). Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Format: [`README.md`](../README.md).

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `a29fb74` | **approve** (0 blockers, 0 majors, 3 minors) | **approve** (0 blockers, 0 majors, 3 minors) |

Round 1 approved with minors. The fixes are in the commit that adds this page, on `autopilot/T7-retry`, and were not reviewed again. `code-simplifier` was not run. Test command:

```bash
python3 -m unittest tests/pipelines/real/test_run_corpus.py
```

```text
CODE  step=T7-retry  review=approve b/M/m=0/0/3  security=approve b/M/m=0/0/3  rounds=1  simplify=notrun -0/+0  tests=pass
```

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-T7R-01 | minor | `PASS (retried)` in the status column broke the alignment of the summary columns | fixed in the commit that adds this page: the status stays `PASS`/`FAIL`, and `(retried)` follows the seconds column |
| CR-T7R-02 | minor | An nf-core entry could put `-resume` in its `args`, which the harness now owns | fixed in the commit that adds this page: `validate()` rejects `-resume` in `nfcore[].args`, with a unit test |
| CR-T7R-03 | minor | The T7 Progress page, the `pipelines-real.yml` header and the research note still said public runners are not measured | fixed in the commit that adds this page: a dated resolution line in [T7](../../progress/W3/T7.md) Findings item 3, the workflow header names `runner_limits.<visibility>`, and a dated note in [corpus-ci-2026-10-27](../../research/corpus-ci-2026-10-27.md) §1 |
| SEC-T7R-01 | minor | A retried pass is green, so a flaky first attempt left no visible trace; a run killed by a signal was retried too | fixed in the commit that adds this page: `result.json` records `first_exit` (null when not retried); a retry prints `::warning title=corpus retry::<entry> exit <rc> on first attempt, <pass\|fail> on -resume`; no retry when the exit code is negative (killed by a signal); unit tests for each |
| SEC-T7R-02 | minor | A retry may double an entry's runtime against the 120-min job timeout | deferred: when the job times out, the cancel path still tails `run.log` (`if: failure() \|\| cancelled()` in `pipelines-real.yml`), so the log of both attempts survives |
| SEC-T7R-03 | minor | The spec did not say which failures are retried, nor how a retried pass is flagged | fixed in the commit that adds this page: one clause in [dev-env §10.2](../../specs/dev-environment-and-testing.md#102-real-pipelines-testspipelinesrealcorpusyaml) (any non-zero exit except a signal kill; a retried pass is green, flagged by the annotation and `first_exit`) |
