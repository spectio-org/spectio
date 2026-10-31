# Code review · P3 UI parity C, parameters one per line, the logos, the run detail and its logs

`review-code` on `autopilot/P3-parC`, base `f6c09fa` (UI parity B on `main`, promotion #108), 2026-10-31. The step answers what Thomas asked after UI parity B: "disposition des params (pk une grille au lieu de 1 par ligne ?) ; pas de light icons pour les sections dans launch ; run detail UI? je veux les logos, important ; ouverture et consultation des logs ?". It changes:

- the Launch form (`web/src/launch/LaunchPage.tsx`, `EngineButtons.tsx`, `app.css`): one parameter per full-width row, `FoldSection`s with icon tiles for Pipeline, Parameters, Where it runs and the preview, the preview on a dark card, Launch in the page head as well, the engines' marks on their buttons; six more group icons in `icons.tsx`;
- the marks (`web/src/shell/EngineMark.tsx`, `markFor` and `PipelineMark`; `web/src/assets/logos/logo-nf-core.png`, new): the nf-core mark for a name that starts with `nf-core/` ([inbox #91](../inbox.md#91-assumed-which-mark-a-pipeline-shows-no-nf-core-mark-yet-and-where-the-logos-come-from), answer (b)), on the runs list, Home, the run header and the Launch Loaded card;
- the run detail: a Copy menu (`web/src/runs/CopyMenu.tsx`, new; `copyItems` and `runDirectory` in `RunHeader.tsx`);
- the Logs tab (`RunDetailPage.tsx`, `runs.css`, `api.ts`): the tab and the log source in the URL (`runSearch`, `routes.tsx`), a File row with Copy, a viewer that does not wrap and opens at its end, two more level tints, Open raw, and a link from the note to the Tasks tab;
- the boards `LiteLaunch` and `LiteLaunchSnakemake`, one parameter per line; `tests/e2e/skeleton.spec.ts` clicks the first of the two Launch buttons;
- tests: `EngineMark.test.tsx` (new) and new tests in the Launch, run detail, runs, Home and icons files.

The reviewers were `code-reviewer` and `security-reviewer`, independent and in parallel, then `code-simplifier`. Format: [`README.md`](../README.md). The behaviour is owned by the ui-spec notes "UI parity C" of 2026-10-31 in [§4.3](../../specs/ui-spec.md#43-runs-table-and-rows), [§4.4](../../specs/ui-spec.md#44-run-detail) and [§4.6](../../specs/ui-spec.md#46-launch-and-relaunch). The docs commit wrote them.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `eb46400` (the step) | **changes** (1 major, 5 minors, 1 simplify) | **approve** (2 minors) |
| 2 | `ae60a73` (CR-P3PARC-01 fixed) | **approve** (3 minors, 1 simplify) | **approve** (2 minors) |
| 3 | `4506ab5` (CR-P3PARC-02 fixed) | **approve** (none) | **approve** (none) |
| simplify | `089adc3` | one change: the Pipeline section's indentation (CR-P3PARC-06 r1), whitespace only, `git diff -w` empty | |

**Finding IDs restart in each round**, so this record writes the round after an ID. CR-P3PARC-02 (r1) and (r2) are the same bug. The heads of rounds 2 and 3 are the fix commits in their order on the branch.

**Test-first.** Each fix adds the test that pins it. `doc-writer` re-ran both against the code before the fix, with the test of `HEAD`: the CR-P3PARC-01 test fails on `eb46400`'s `LaunchPage.tsx` (`toHaveTextContent`), and the CR-P3PARC-02 test fails on `ae60a73`'s `RunDetailPage.tsx` (`aria-pressed` not `"true"`). Both pass at `HEAD` ([P3-M4 Evidence](../../progress/W5/P3-M4.md#ui-parity-c-parameters-one-per-line-the-logos-the-run-detail-and-its-logs_1)).

Gate at `089adc3`, from the worktree, re-run by `doc-writer`:

```bash
uv run --locked pytest -q        # 511 passed, 15 deselected (no product Python file changed)
uv run --locked ruff check .     # All checks passed!
uv run --locked mypy packages    # Success: no issues found in 81 source files
uv run --locked lint-imports     # Contracts: 4 kept, 0 broken.
cd web && npx vitest run         # 15 files, 140 tests passed
cd web && npx tsc --noEmit       # exit 0
cd web && npm run build          # dist/index.html, three logo PNGs, one CSS and one JS asset
```

ESLint did not run: the `web` package has no ESLint config and no lint script.

```text
CODE  step=P3-parC  review=approve b/M/m=0/1/8  security=approve b/M/m=0/0/4  rounds=3  simplify=changed -101/+101  tests=pass
```

The counts add up the three rounds of each reviewer, from each report's own count line. The two `simplify` findings are not counted. The simplifier's −101/+101 is whitespace only.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3PARC-01 (r1) | major | A boolean parameter got no type, default or changed state on its row: a bare Mantine Checkbox with only its help. The updated board draws `boolean · changed · default false`. | fixed in `ae60a73`: the checkbox row has the meta and the help, and its description is tied by `aria-describedby`; with a test |
| CR-P3PARC-02 (r1) | minor | Going from Logs to another tab and back reset the log source to the engine log: `runSearch` keeps `source` only on Logs. | fixed in `4506ab5` (as CR-P3PARC-02 r2) |
| CR-P3PARC-03 (r1) | minor | The File row names its path with `<code aria-labelledby>`; ARIA 1.2 forbids naming the `code` role, and on the phone the label is `display:none`. The test passes because Testing Library resolves `aria-labelledby` on any element. | **open**: follow-up FU-P3-27 |
| CR-P3PARC-04 (r1) | minor | The Copy menu's live region is `display:none` while empty, so "Copied the run ID" may go unannounced. | **open**: follow-up FU-P3-27 |
| CR-P3PARC-05 (r1) | minor | `/\bcompleted\b/` tints any line with the word "completed" green, which may include Nextflow's polling-monitor lines **[to be validated]**. | **open**: follow-up FU-P3-27 |
| CR-P3PARC-06 (r1) | simplify | The Pipeline `FoldSection` block keeps the indentation of the grid it was moved out of. | fixed in `089adc3` by `code-simplifier` |
| CR-P3PARC-07 (r1) | minor | Inbox #91's new Answer line contradicts its body: rule 1 and the Assumed line still read as the rule in force. | fixed in the docs commit: rule 1 and the Assumed line are marked superseded by the answer |
| SEC-P3PARC-01 (r1) | minor | Open raw loads `GET /api/v1/runs/{id}/logs` as a page. It sends `text/plain`, `nosniff` and `no-store`, but not the `Referrer-Policy: no-referrer` of [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13, nor the CSP sandbox req. 14 gives other raw files. Not exploitable today. | **open**: follow-up FU-P3-27, before the screens are served beyond local mode |
| SEC-P3PARC-02 (r1) | minor | Any pipeline can name itself `nf-core/…`; on the Launch Loaded card the mark sits beside the name when deciding to launch, and the card does not show the repository's host or owner. | recorded: Thomas chose this rule (#91 (b)); the mark gates no permission. The ui-spec §4.3 note and #91 say the name is a claim |
| CR-P3PARC-02 (r2) | minor | After Logs > Head errors > Summary > Logs, the viewer is back on the engine log. | fixed in `4506ab5`: a `lastSource` ref, set when Logs opens, passed to `runSearch`; tab changes no longer pass a source. With a test |
| CR-P3PARC-03 (r2) | minor | Copy labels Nextflow's item "Config (params.json)", where LiteRunActions says "Parameters (params.json)"; a run from a terminal also gets a Config item, which the board does not draw. Nothing records either difference. | recorded as decided in the [ui-spec §4.4 note "UI parity C"](../../specs/ui-spec.md#44-run-detail) *(assumed — standing rule)*; the board follows at the next `/apply-findings` |
| CR-P3PARC-04 (r2) | minor | In the one-per-line row, a field's error renders after its help; the boards put it right under the input. | **open**: follow-up FU-P3-27 |
| CR-P3PARC-05 (r2) | simplify | Formatting left by the move: the Pipeline block's indentation, and a `meta` line of about 150 columns. | indentation fixed in `089adc3`; the long line **open**, follow-up FU-P3-27 |
| SEC-P3PARC-01 (r2) | minor | The same as round 1: the raw log page has no CSP, no `Referrer-Policy` and no `frame-ancestors`; safe today through `text/plain`, `nosniff` and the cross-site refusal of `api/browser.py`. | **open**: follow-up FU-P3-27 |
| SEC-P3PARC-02 (r2) | minor | `markFor` shows the nf-core mark for any `nf-core/` name; the commit removed the comment saying the name is only a claim, and the #91 answer did not say it either. | #91 and the ui-spec §4.3 note now say it (docs commit); the code comment **open**, follow-up FU-P3-27 |

## Fixes by commit

| Commit | Findings |
|---|---|
| `ae60a73` P3-parC: boolean parameters get the full row (CR-P3PARC-01) | CR-P3PARC-01 (r1) |
| `4506ab5` P3-parC: Logs reopens on the last picked source after a tab switch (CR-P3PARC-02) | CR-P3PARC-02 (r1, r2) |
| `089adc3` refactor(P3-parC): simplify the Pipeline section's indentation | CR-P3PARC-06 (r1), CR-P3PARC-05 (r2) in part |
| the docs commit | CR-P3PARC-07 (r1), CR-P3PARC-03 (r2) (recorded), SEC-P3PARC-02 (r1, r2) (recorded in the docs) |

## For the Progress page

The parity C section of P3-M4 is written: [P3-M4 · UI parity C](../../progress/W5/P3-M4.md#ui-parity-c-parameters-one-per-line-the-logos-the-run-detail-and-its-logs), with its [findings and open questions](../../progress/W5/P3-M4.md#findings-and-open-questions) and follow-up FU-P3-27.
