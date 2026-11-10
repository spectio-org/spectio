# Code review · FU-P3-87e: the catalog picker on Launch, Manage catalog and Save to catalog

`review-code` on `autopilot/P3-fu87e`, base `31f9ca40`, head `14c926fb` (`01ebb8ff` the step, `14c926fb` the round-1 fix), 2026-11-10. Owner: [api §5.6](../../specs/api-and-data-model.md#56-pipeline-catalog-001). Progress: [P3 · M9, FU-P3-87e](../../progress/W5/P3-M9.md#fu-p3-87e-the-catalog-picker-on-launch). Format: [`README.md`](../README.md).

Round 1: code-reviewer changes (2 majors, 3 minors); security-reviewer approve (2 minors). Round 2: the fixes were checked. Ids as reported by the worker.

## Findings

| Id | Severity | Finding | State |
|---|---|---|---|
| CR-P3FU87E-01 | major | `fromEntry` was a copy of the item taken at Load; it went stale after an edit or delete in Manage catalog (old etag, PUT conflict) | fixed, test first |
| CR-P3FU87E-02 | major | Choosing None also dropped the unplaced-values line and the code_loading warnings, against ui-spec §4.7.1 | fixed, test first |
| CR-P3FU87E-03 / SEC-P3FU87E-01 | minor | The file's own `params_file` code_loading item was dropped silently when not writable by others; api §5.6 says each is named | fixed, test first |
| CR-P3FU87E-04 | minor | No test for focus return to Save to catalog on Cancel or Escape, nor for the phone variant | open |
| CR-P3FU87E-05 | minor | Missing catalog profile note does not say the environment's profile was selected instead | open |
| SEC-P3FU87E-02 | minor | code_loading warnings reflect the file as read, not what Launch sends; advisory only, POST /runs is the authority | open |

## The fix (`14c926fb`)

- `fromName: string` replaces the item copy; the item is derived from `catalog.items`.
- None calls only `setEntryName(null)`; the params-file report is its own `paramsFile` state, cleared in `edit()` or replaced by the next Load.
- The `params_file` item is always named as a warning, with " · writable by others" when flagged. No spec change: ui-spec §4.7.1 points to api §5.6.

Fix check: CR-P3FU87E-01, -02, -03 and SEC-P3FU87E-01 resolved; none unresolved. `code-simplifier` runs once per batch.

```text
CODE  step=P3-fu87e  review=approve b/M/m=0/0/2  security=approve b/M/m=0/0/1  rounds=2  simplify=skipped -0/+0  tests=pass
```
