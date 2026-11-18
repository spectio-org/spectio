# Code review · P3-ui19c, CSS sweep part 3 (UI-19c)

Branch `autopilot/P3-ui19c`, commit `410cecc`, base `6876ae6`. Reviewer: `code-reviewer`, one round. `security-reviewer` did not run (no sensitive path). Format: [`README.md`](../README.md).

```text
CODE  step=P3-ui19c  review=approve b/M/m=0/0/3  security=skipped b/M/m=0/0/0  rounds=1  simplify=skipped  tests=pass
```

## Findings

| ID | Severity | Finding | State |
|---|---|---|---|
| CR-P3UI19C-01 | minor | `.sp-list li[data-rail]` is left at plain `lg`; it had plain padding before the sweep, so the CR-P3UI19B-01 rule does not apply. Content sits 12 px from the rail edge, against 16 px in a row without a rail. The rule is outside part c | open |
| CR-P3UI19C-02 | minor | Two declarations repeat the same token for both shorthand values | open |
| CR-P3UI19C-03 | minor | The GEOMETRY allowlist matches fragments, not selectors; a later declaration with the same text passes silently (`theme.test` CLEARANCES has the same weakness) | open |

## Assumptions

- Values snap to the nearest step, a tie goes up, as in UI-19a and UI-19b. Font sizes follow `theme.ts` (xs/sm/md = 12/13/14), not the task text.
- 1 px values are kept. The 26 px explorer sub-line indent becomes `spacing-xl` (24 px = 16 px icon + 8 px gap).
- GEOMETRY allowlist, each with a reason: `+ 4px)`, `calc(0.5lh - 8px)`, switch knob `margin-left` 3 px and 17 px, pin `margin-top: -2px`.
- CR-P3UI19B-03 is closed: `web/src/rawPx.ts` holds the shared `rawPx(css, allowed)`.
- ui-spec §12.15 is not changed: the allowlist rule is the same as UI-19a's CLEARANCES.
- The temporary `web/node_modules` symlink was removed.
