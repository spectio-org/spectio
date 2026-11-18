# Code review · FU-P3-86f: the Environments pages, list, form, delete and make default

`review-code` on `autopilot/P3-fu86f`, 2026-11-09, base `autopilot/integration`, head `99915676` (`924660ad` the pages, `99915676` the round 1 fixes). The branch is one commit behind the base (`d2147ede`, FU-P3-106a), so use a three-dot diff. Owner: [ui-spec §4.8.1](../../specs/ui-spec.md#481-environments-in-001). Format: [`README.md`](../README.md). Reports are relayed in summary.

| Round | Head | code-reviewer | security-reviewer | Fix |
|---|---|---|---|---|
| 1 | `924660ad` | **changes** (0 blockers, 2 majors, 8 minors: CR-P3FU86F-01 to -10) | **approve** (0/0/2: SEC-P3FU86F-01, -02) | `99915676` |
| 2 | `99915676` | fix check: CR-01, -02, -06, -07, -08 resolved, none unresolved | not repeated | none |

Fixes, tests first (each failed before its fix): phone cards as one link and the page's action group with a shared `DeleteAsk` (-01); other 422 errors to the alert banner (-02); a non-404 read error with Retry (-06); Duplicate clears the label (-07); the empty-state line and skeleton cards (-08).

Open: CR-P3FU86F-03 to -05 (simplify), -09 (Playwright second Tab on a SLURM server, and the phone project), -10 (branch behind the base); SEC-P3FU86F-01 (the keyboard spec rewrites the file behind `SPECTIO_E2E_BASE_URL`, no cleanup), SEC-P3FU86F-02 (names not encoded in links; safe while the server enforces `^[a-z][a-z0-9-]{0,31}$`).

```text
CODE  step=P3-fu86f  review=approve b/M/m=0/0/5  security=approve b/M/m=0/0/2  rounds=2  simplify=skipped -0/+0  tests=pass
```
