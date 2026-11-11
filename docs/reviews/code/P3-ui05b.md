# Code review · P3-ui05b, notifications panel (UI-05b)

`code-reviewer` on `autopilot/P3-ui05b` against base `origin/autopilot/P3-ui02`, 2026-11-11. Spec: [ui-spec §12.13](../../specs/ui-spec.md). Format: [README.md](../README.md).

```text
CODE  rounds=2  verdict=changes-applied  security=skipped  findings=8 (5 major, 3 minor)  fixed=5  commits=072796b9,02ad8147
```

Security review skipped: no sensitive path.

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| CR-P3UI05B-01 | major | `var(--sp-line)` is undefined, so the popover border and both dividers did not render | fixed in `02ad8147` (`--sp-line-border`, `--sp-line-divider`; CSS text test) |
| CR-P3UI05B-02 | major | Day labels used the raw `--sp-ink-500`, about 2:1 in dark | fixed (`--sp-text-muted`; CSS text test) |
| CR-P3UI05B-03 | major | Base moved (UI-03, UI-01 merged); panel drew its own loading, empty and error states | fixed: merge `072796b9`; uses `SkeletonRows`, `EmptyState`, `ErrorPanel` |
| CR-P3UI05B-04 | major | `KINDS` and 8 tone rules duplicated `runWord`, `tone`, `TONE_ICONS` and runs.css | fixed: `STATE` map, exports from `RunState.tsx`, `--tone-bg`/`--tone-fg` |
| CR-P3UI05B-05 | minor | Hover and focus replaced the unread tint | fixed: focus shows the outline only; unread hover keeps `--sp-accent-subtle` |
| CR-P3UI05B-06 | minor | No Tooltip on a truncated run name (§12.8) | open |
| CR-P3UI05B-07 | minor | simplify: intersection ref type, unused `ago` export, `setTimeout` focus return instead of `returnFocus` | open |
| CR-P3UI05B-08 | minor | Non-modal Popover in a portal: Tab order leaves to the end of the document | open |

## Assumptions

- `.sp-notif-error` stays: the mark-failure line still uses it. Only the load error moved to `ErrorPanel`.
- Unread hover keeps `--sp-accent-subtle`; no stronger accent token exists.
- Not fixed, outside this step: `shell.css` uses `var(--sp-shadow)`, which no token file defines.
- The phone shot `after2-phone.png` was not looked at after the fix.
