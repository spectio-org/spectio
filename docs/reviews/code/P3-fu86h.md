# Code review · FU-P3-86h: the Launch aside, summary and Before Launch list

`review-code` on `autopilot/P3-fu86h`, base `autopilot/integration`, commits `7645cb81` (the feature) and `0aced17f` (the round-1 fix), 2026-11-09. Behaviour is owned by [ui-spec §4.6](../../specs/ui-spec.md). Progress: [P3 · M9](../../progress/W5/P3-M9.md). Format: [`README.md`](../README.md).

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `7645cb81` | approve (0 blockers, 0 majors, 6 minors) | skipped (no sensitive path) |
| fix | `0aced17f` | CR-P3FU86H-01, -02, -04 fixed (-01, -02 test first) | |
| 2 | `0aced17f` | fix check: resolved 01, 02, 04; none unresolved | |

## Findings

| ID | Finding | Status |
|---|---|---|
| CR-P3FU86H-01 | A reason's link may not open a folded group that already has a server error | fixed: `reveal` becomes `"link"` while a link moves focus |
| CR-P3FU86H-02 | Summary Environment row shows "…" when none is chosen | fixed: "…" only while loading |
| CR-P3FU86H-03 | Engine text written twice (simplify) | open, minor |
| CR-P3FU86H-04 | "below" should be "above" in the UI parity C bullet | fixed |
| CR-P3FU86H-05 | No test for the "Choose where it runs" link; no browser run | open, minor |
| CR-P3FU86H-06 | Inbox #146 item 2 (icon, changeable "Where it runs") is for the fix round, not built here | open, noted |

```text
CODE  step=P3-fu86h  review=approve b/M/m=0/0/3  security=skipped  rounds=2  simplify=skipped -0/+0  tests=pass
```
