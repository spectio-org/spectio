# Code review · FU-P3-86g: the Environment row on Launch and the Environment fact on Run detail

`review-code` on `autopilot/P3-fu86g`, base `autopilot/integration`, commits `3c2198b2` (the feature) and `0f6b9c7e` (the round-1 fix), 2026-11-09. Behaviour is owned by [ui-spec §4.8.1](../../specs/ui-spec.md); the plan is [inbox #133](../inbox.md). Progress: [P3 · M9](../../progress/W5/P3-M9.md#fu-p3-86g-the-environment-row-on-launch-and-the-environment-fact-on-run-detail). Format: [`README.md`](../README.md).

16 files, +875 −160 is the diff of the two commits, `3c2198b2^..0f6b9c7e`, and counts one docs file (`docs/reviews/inbox.md`, +8). Outside `docs/` it is 15 files, +867 −160 (`git diff --numstat`). The batch table of [P3-B11](P3-B11.md) uses the squash commit `be551cfc` of PR #211: 15 files, +870 −160 outside `docs/`, with 3 more lines in `web/src/app.css` than the two commits; the cause was not traced **[to be validated]**. The files: `LaunchPage.tsx`, the new `EnvironmentRow.tsx`, `RunHeader.tsx`, `ResumeDialog.tsx`, CSS, three Vitest files and a Playwright spec.

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `3c2198b2` | **changes** (1 blocker, 1 major, 5 minors) | ran; no finding relayed |
| fix | `0f6b9c7e` | CR-P3FU86G-01, -03 fixed (-03 test first); -02 split out | |
| 2 | `0f6b9c7e` | **approve** | approve |

The round-2 counts were not relayed in detail. The `b/M/m=0/0/4` below counts the four round-1 minors that were not fixed by name: CR-P3FU86G-04 (covered by the test added for -03), -05, -06 and -07. Round 1 had five minors (-03 to -07); -03 is fixed. Only -05, -06 and -07 are still open in the table; -04 is covered, not open.

```text
CODE  step=P3-fu86g  review=approve b/M/m=0/0/4  security=approve b/M/m=0/0/0  rounds=2  simplify=skipped -0/+0  tests=pass
```

## Findings

| ID | Severity | Finding | Result |
|---|---|---|---|
| CR-P3FU86G-01 | blocker | `shell.test.tsx` stubbed every URL with VERSION; `listEnvironments()` on /launch threw | Fixed `0f6b9c7e`: the stub routes by URL |
| CR-P3FU86G-02 | major | Aside summary and "Before Launch" list of the §4.6 board missing | Not built: follow-up FU-P3-86h, [inbox #145](../inbox.md) |
| CR-P3FU86G-03 | minor | A failed Reload in the dialog unmounted it and lost the values | Fixed `0f6b9c7e`: dialog kept outside the early returns; test failed first |
| CR-P3FU86G-04 | minor | No test for the 409 `environments-file-changed` Reload | Covered by the test added for -03 |
| CR-P3FU86G-05, -06 | minor | Test title mismatch; mis-indented `description` JSX | Open |
| CR-P3FU86G-07 | minor | Board differences: ` · runs the tasks` suffix; badges wrap at 1440 | Open, disclosed |

Open: inbox #145 may need renumbering at merge.
