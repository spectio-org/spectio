# Code review · T7-pin, the corpus reads the Nextflow pin

`review-code` on `autopilot/T7-pin`, range `origin/autopilot/integration...1c43630`, 2026-10-28. The step applies triage finding SPK-T7-03: `pipelines-real.yml` reads `NEXTFLOW_VERSION` from `dev/versions.env` (26.10.4) instead of a hardcoded 26.10.3, and `corpus.yaml` no longer repeats the current version, which no code read. Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Format: [`README.md`](../README.md).

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `1c43630` | **approve** (0 blockers, 0 majors, 2 minors) | **approve** (0 blockers, 0 majors, 1 minor) |

Round 1 approved with minors. The fixes are in the commit that adds this page and were not reviewed again. `code-simplifier` was not run: the change is one `grep` step. Test command:

```bash
python3 -m unittest tests/pipelines/real/test_run_corpus.py
```

```text
CODE  step=T7-pin  review=approve b/M/m=0/0/2  security=approve b/M/m=0/0/1  rounds=1  simplify=notrun -0/+0  tests=pass
```

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-T7P-01 | minor | `ci.yml:39`: the PR-tier path filter does not include `dev/versions.env`, so a PR that only bumps Nextflow starts no corpus job; the nightly run catches it a day later. | Fixed by saying so in the `pipelines-real.yml` header; the filter is unchanged, since adding the file would start the corpus on every tool bump. |
| CR-T7P-02 | minor | `pipelines-synthetic.yml:24` still hardcodes `26.10.4`, a second copy of the pin (outside this diff). | Open, with inbox #42. |
| SEC-T7PIN-01 | minor | `pipelines-real.yml:60`: `[0-9.]+` also accepts `.` or `1..`; it fails safely in setup-nextflow. | Fixed: `grep -m1 -E '^NEXTFLOW_VERSION=[0-9]+\.[0-9]+\.[0-9]+$'`. |

No injection: the pattern is anchored at both ends and allows digits and dots only, the value goes to the `with:` input of a SHA-pinned action, and the job keeps `contents: read` with no secrets.
