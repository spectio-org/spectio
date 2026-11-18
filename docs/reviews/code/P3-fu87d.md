# Code review · FU-P3-87d: the Catalog page, its list and its entry form

`review-code` on `autopilot/P3-fu87d`, base `9145e7c`, head `9ac03437` (two commits: `6b686b55` the step, `9ac03437` the round-1 fix), 2026-11-10. Owner: [api §5.6](../../specs/api-and-data-model.md#56-pipeline-catalog-001). Progress: [P3 · M9, FU-P3-87d](../../progress/W5/P3-M9.md#fu-p3-87d-the-catalog-page-its-list-and-its-entry-form). Format: [`README.md`](../README.md).

Round 1: both reviewers approved. Ids are as reported by the worker.

## Findings

| Id | Severity | Finding | State |
|---|---|---|---|
| CR-P3FU87D-01 | minor | `CatalogList.tsx` and `CatalogPage.tsx` repeat the Environments code almost line for line (simplify) | open |
| CR-P3FU87D-02 | minor | The Delete dialog said "nothing was deleted" for every error, also a network failure or 5xx | fixed, test first |
| CR-P3FU87D-03 | minor | Rows are `<article>` cards; the board draws `<ul><li>`, so no list is announced | open |
| CR-P3FU87D-04 | minor | `problem` and `toBody` are exported but used only in their modules (simplify) | open |
| CR-P3FU87D-05 | minor | No test for the Save-side `409 catalog-file-changed` banner, the skeleton, or Retry reloading | open |
| SEC-P3FU87D-01 | minor | The desktop Edit link does not encode the name; not exploitable (server names are `^[a-z][a-z0-9-]{0,31}$`) | open |
| SEC-P3FU87D-02 | minor | A Git URL with credentials passes the client checks; the server refuses it (api §5.6) | open |
| SEC-P3FU87D-03 | minor | The e2e test writes the catalog of the server named by `SPECTIO_E2E_BASE_URL` | open |

## The fix (`9ac03437`)

- The sentence "Reload reads it again; nothing was deleted." is now added only to the three known refusals (412, `catalog-file-changed`, `catalog-file-unusable`) by `problem()`. Network failures and 5xx show only the message; Reload stays.
- A new test (a 500 must not say "nothing was deleted") failed before the fix. `npx vitest run src/catalog/CatalogPage.test.tsx`: 17 passed; `npx tsc --noEmit`: clean.

Fix check: CR-P3FU87D-02 resolved; none unresolved. `code-simplifier` runs once per batch.

```text
CODE  step=P3-fu87d  review=approve b/M/m=0/0/4  security=approve b/M/m=0/0/3  rounds=2  simplify=skipped -0/+0  tests=pass
```
