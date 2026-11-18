# Code review · P3-ui19b, CSS sweep part 2 (UI-19b)

Branch `autopilot/P3-ui19b`, commits `f680f75` and `5a76864`, base `0ad4321`. Reviewer: `code-reviewer`, two rounds. `security-reviewer` did not run (no sensitive path). Format: [`README.md`](../README.md).

```text
CODE  step=P3-ui19b  review=changes-fixed b/M/m=0/1/2  security=skipped b/M/m=0/0/0  rounds=2  simplify=skipped -0/+0  tests=pass
```

## Findings

| ID | Severity | Finding | State |
|---|---|---|---|
| CR-P3UI19B-01 | major | Padding that includes the 4 px rail was snapped as if it were plain spacing; the row-hit offset no longer cleared the rail | fixed in `5a76864`: the rail side is `calc(var(--mantine-spacing-lg) + 4px)`, other sides snap to the scale; the raw-px lint accepts `+ 4px)` (ui-spec §12.15); a test fixes the five paddings and the row-hit offset |
| CR-P3UI19B-02 | minor | Shorthands repeat the same token | open |
| CR-P3UI19B-03 | minor | `tokens.test.ts` copies the declaration regex from UI-19a's `theme.test.ts`; part c would need a third copy | open |

## Assumptions

- Rows with a rail that the finding did not cover (for example `.sp-list li[data-rail]`) were left alone; part c checks them against the same rule.
- The temporary `web/node_modules` symlink used to run tests was removed.
