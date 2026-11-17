# Code review · P3-ui19a CSS sweep part 1 on the design tokens (UI-19a)

`review-code` on `autopilot/P3-ui19a`, base `0ad4321d`, 2026-11-17. Reviewer: `code-reviewer`; `security-reviewer` did not run (no sensitive path). Format: [README.md](../README.md).

| Round | Head | code-reviewer |
|---|---|---|
| 1 | `403ba1b` | changes (1 major, 2 minors) |
| 2 | `29a0f8e` | CR-P3UI19A-01 fixed; approve on the fix |

```text
CODE-REVIEW  verdict=approve  rounds=2  security=skipped
```

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| CR-P3UI19A-01 | major | Narrow-phone tab label snapped from 10 px to 12 px; ui-spec §4.8.1 says 10 px below 340 px | fixed in `29a0f8e` (10 px restored, allowlisted in `theme.test.ts`) |
| CR-P3UI19A-02 | minor | Brand wordmark `.sp-word` 23 px to 20 px | not applied |
| CR-P3UI19A-03 | minor | CLEARANCES allowlist strips substrings from any declaration | not applied |

## Assumptions

- Values with a spec reason (the 10 px tab label) stay as declared and are allowlisted; the rest snap to the nearest token.
- Prettier was not run: it flagged both files before the change and no script uses it.
- Rendered at 360 px and 320 px with mocked data: no tab label is clipped.
