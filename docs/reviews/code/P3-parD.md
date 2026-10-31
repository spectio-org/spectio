# Code review · P3 UI parity D, run detail sheets, searchable logs, test pipelines in Launch

`review-code` on `autopilot/P3-parD`, base `5ce1f89` (P3-demo's PR #111 open, not merged), 2026-10-31. The step answers what Thomas wrote after clicking through the public demo preview of #111 (2026-10-31): "steps & stages pas clickable, pas de détails ; plein de parties et d'éléments pas encore clickable ; params quasi vides pour les wf ; pas de wf par défaut de test dans launch pour tester ; logs pas searchable". It changes the UI and the synthetic pipelines' data only, with no API or server change:

- the run detail (`web/src/runs/DetailSheet.tsx`, new; `RunDetailPage.tsx`, `RunHeader.tsx`, `RunState.tsx`, `stateWord.ts`, `CopyMenu.tsx`, `runs.css`): stage, process and task rows open a modal side sheet; the Tasks tab keeps `?process=` in the URL; the task chips filter the Tasks tab; the pipeline directory gets Copy; "Why it failed" names the first failed task;
- the log viewer (`web/src/runs/LogViewer.tsx`, new): search with marked matches, an "n / m" counter, previous and next, and a level filter;
- Launch (`web/src/launch/TryPipelines.tsx`, new; `LaunchPage.tsx`, `routes.tsx`, `app.css`) and Home (`HomePage.tsx`): "Try a test pipeline" and `/launch?location=`;
- `icons.tsx`: two more `fa_icon` names;
- the synthetic pipelines: `tests/pipelines/synthetic/nextflow/nextflow_schema.json` and `tests/pipelines/synthetic/snakemake/workflow/schemas/config.schema.yaml` (new); `test_launch.py` expects their four groups;
- tests: `DetailSheet.test.tsx`, `LogViewer.test.tsx` and `TryPipelines.test.tsx` (new), and new tests in the run detail, Home and icons files.

The reviewers were `code-reviewer` and `security-reviewer`, independent and in parallel, then `code-simplifier`. Format: [`README.md`](../README.md). The behaviour is owned by the ui-spec notes "UI parity D" of 2026-10-31 in [§4.4](../../specs/ui-spec.md#44-run-detail) and [§4.6](../../specs/ui-spec.md#46-launch-and-relaunch), and the schemas by the [dev-env §10.1](../../specs/dev-environment-and-testing.md#101-synthetic-scenario-pipelines-testspipelinessynthetic) note. The docs commit wrote them.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `50ff24c` (the step) | **approve** (8 minors, one of them a simplify) | **approve** (3 minors) |
| 2 | `2a45be9` (CR-P3PARD-01, -04, -05, -06 fixed) | **approve** (1 minor) | **approve** (none) |
| simplify | `846f462` | one change: `LogViewer`'s `Line` has one render path, 9 lines out, 1 in | |

**Finding IDs restart in each round**, so this record writes the round after an ID. CR-P3PARD-07 (r1) and CR-P3PARD-07 (r2) are two different findings.

**Test-first.** Each round 1 fix adds the test that pins it. `doc-writer` re-ran the four tests of `HEAD` against the three source files of `50ff24c`; all four fail, and pass at `HEAD` ([P3-M4 Evidence](../../progress/W5/P3-M4.md#ui-parity-d-run-detail-sheets-searchable-logs-test-pipelines-in-launch_1)).

Gate at `846f462`, from the worktree, re-run by `doc-writer`:

```bash
uv run --locked pytest -q        # 511 passed, 15 deselected
uv run --locked ruff check .     # All checks passed!
uv run --locked mypy packages    # Success: no issues found in 81 source files
uv run --locked lint-imports     # Contracts: 4 kept, 0 broken.
cd web && npx vitest run         # 18 files, 175 tests passed
cd web && npx tsc --noEmit       # exit 0
cd web && npm run build          # dist/index.html, three logo PNGs, one CSS and one JS asset
```

ESLint did not run: the `web` package has no ESLint config and no lint script (FU-P3-27).

```text
CODE  step=P3-parD  review=approve b/M/m=0/0/9  security=approve b/M/m=0/0/3  rounds=2  simplify=changed -9/+1  tests=pass
```

The counts add up the two rounds of each reviewer, from each report's own count line. Round 1's code-reviewer line reads `minors=8 simplify=1`: CR-P3PARD-02 is one of the 8, marked "simplify:", so it is counted once.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3PARD-01 (r1) | minor | A count chip or "Open in Tasks" that leaves the URL unchanged left `focusPanel` set, so the next tab switch moved focus off the tab button onto the panel. | fixed in `2a45be9`: `focusTasks(process?)` focuses the Tasks panel at once when the view is already shown; with a test |
| CR-P3PARD-02 (r1) | minor (simplify) | Every `Line` gets `size={query.length}`, so each new query re-renders every line, not only those that match; the header comment says the opposite. | **open**: follow-up FU-P3-28 |
| CR-P3PARD-03 (r1) | minor | The brief asks for search in every log viewer; the Summary's 6-line tail has none. | recorded as decided in the [ui-spec §4.4 note "UI parity D"](../../specs/ui-spec.md#44-run-detail) *(assumed — standing rule)*: the tail is six lines and links to the searchable Logs tab |
| CR-P3PARD-04 (r1) | minor | A log that ends with a newline got an empty last line, counted in All and INFO and rendered. | fixed in `2a45be9`: `splitLines` drops one final newline; with a test. Round 2 notes that `LogLines`' only caller already trims its text, so the helper changes nothing there |
| CR-P3PARD-05 (r1) | minor | "First to fail" looked for `failure.task_id` in the first 50 failed tasks only, and the line vanished without notice past them. | fixed in `2a45be9`: it follows `next` for up to 5 pages of 50; past 250 failed tasks the line is still left out, as a code comment says; with a test |
| CR-P3PARD-06 (r1) | minor | "Load more" had no in-flight guard: a double click appended the same page twice, with duplicate React keys. | fixed in `2a45be9`: a `loading` state, `aria-busy`, and `more()` returns at once while a page is in flight; with a test |
| CR-P3PARD-07 (r1) | minor | The Playwright smoke the brief requires has no reported result. | recorded on the Progress page: the worker's run at `50ff24c`, 10 passed and 12 skipped without engines; CI's `e2e-local` runs it on the PR |
| CR-P3PARD-08 (r1) | minor | The worker's inventory covers Home, the run detail and Launch, not the Runs page or the phone. | done in the docs commit: the [inventory table](../../progress/W5/P3-M4.md#clickability-inventory-ui-parity-d) covers every screen of the brief |
| SEC-P3PARD-01 (r1) | minor | `/launch?location=` fills the field and inspects at once, so a crafted link can show a pipeline planted on the shared file system, loaded under a manifest name its author chose. Inspect only reads; Launch still needs a click. | **open**: follow-up FU-P3-28 (from a link, fill only; load at once only a location of the user's recent runs) |
| SEC-P3PARD-02 (r1) | minor | The schemas give no `maximum` for `chunks`, `scale`, `fail_gb` or `time_limit_s`; a large fan-out or a real allocation runs on a shared login node with the local profile. | **open**: follow-up FU-P3-28 |
| SEC-P3PARD-03 (r1) | minor | `python_image` defaults to a digest-pinned image but the schema accepts any string, so a mutable tag can replace the pin. | **open**: follow-up FU-P3-28 |
| CR-P3PARD-07 (r2) | minor | Load more sets the native `disabled` while its page loads; a keyboard user who pressed Enter loses focus to the body, and the next Tab starts at the top of the sheet. The guard in `more()` already blocks the second request. | **open**: follow-up FU-P3-28 (drop `disabled`, keep `aria-busy`, assert focus in the test) |

`security-reviewer` round 2 also noted, not as a finding, that a Load more page could land in another process's list; `code-reviewer` round 2 checked that `ProcessTasks` remounts on every view change (`key={views.length}`), so it cannot.

## Fixes by commit

| Commit | Findings |
|---|---|
| `2a45be9` fix(web): P3-parD review findings CR-P3PARD-01, -04, -05, -06 | CR-P3PARD-01, -04, -05, -06 (r1) |
| `846f462` refactor(P3-parD): simplify LogViewer Line's no-match branch | none: the simplifier's own change |
| the docs commit | CR-P3PARD-03 (r1) (recorded), CR-P3PARD-07 (r1) (result recorded), CR-P3PARD-08 (r1) (inventory) |

## For the Progress page

The parity D section of P3-M4 is written: [P3-M4 · UI parity D](../../progress/W5/P3-M4.md#ui-parity-d-run-detail-sheets-searchable-logs-test-pipelines-in-launch), with its [findings and open questions](../../progress/W5/P3-M4.md#findings-and-open-questions) and follow-up FU-P3-28.
