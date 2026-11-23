# Code review · FU-P3-88a: the run detail pass

`review-code` on `autopilot/P3-fu88a`, base `64c5d83`, head `eebca1dc` (`e858b34e` the step, `eebca1dc` the round-1 fix), 2026-11-10. Owner: [ui-spec §4.4.1](../../specs/ui-spec.md). Progress: [P3 · M9, FU-P3-88a](../../progress/W5/P3-M9.md#fu-p3-88a-the-run-detail-pass). Format: [`README.md`](../README.md).

Round 1: code-reviewer changes (1 major, 4 minors); security-reviewer approve (1 minor). Round 2: both fixes resolved. Ids are as reported by the worker.

## Findings

| Id | Severity | Finding | State |
|---|---|---|---|
| CR-P3FU88A-01 | major | FU-P3-104 has three more items than Search (breadcrumb repeats the run, table caption misplaced, an unstyled link); the ui-spec said Search was the only one | fixed: listed as open for FU-P3-88b in ui-spec §4.4.1 |
| CR-P3FU88A-02 | minor | The last-lines `<pre>` opened the full log on every click, also at the end of a text selection | fixed, test first |
| CR-P3FU88A-03 | minor | Bullets state the old behaviour before the dated change note | open |
| CR-P3FU88A-04 | minor | The resume sentence in ui-spec §5.2 is **[to be validated]** (Snakemake 9.27.1 checkpoint rerun) but shown as fact | open |
| CR-P3FU88A-05 | minor | The boards still show the filled Checkpoint chip and "All logs…" | open |
| SEC-P3FU88A-01 | minor | The report-viewer size gate treats an unknown size as small; the raw route still answers 413 | open |

## The fix (`eebca1dc`)

- A test (selecting text must not open the log) failed before the fix; the click handler now skips when `window.getSelection()` is non-empty.
- `RunDetailPage.test.tsx`: 56 passed; `tsc --noEmit`: OK. Full suite not run.

Fix check: CR-P3FU88A-01 and -02 resolved; none unresolved. `code-simplifier` runs once per batch.

```text
CODE  step=P3-fu88a  review=approve b/M/m=0/0/4  security=approve b/M/m=0/0/1  rounds=2  simplify=skipped -0/+0  tests=pass
```
