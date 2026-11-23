# Code review · FU-P3-85d: the results explorer, sort, filter and URL state

`review-code` on `autopilot/P3-fu85d`, base `88bc5748`, head `ba8398c5` (three commits: `5adedfd1` the boards, `4036ccb9` the step, `ba8398c5` the fix of CR-P3FU85D-01), 2026-11-09. The step is the fourth task of the build plan of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85): the browser side of the folder page, on the server routes of [P3-fu85a](P3-fu85a.md) and [P3-fu85b](P3-fu85b.md) and the preview page of [P3-fu85c](P3-fu85c.md). The behaviour is owned by [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview). Progress: [P3 · M9, FU-P3-85d](../../progress/W5/P3-M9.md#fu-p3-85d-the-results-explorer-sort-filter-and-url-state). Format: [`README.md`](../README.md).

Over the base: 24 files, +1,300 −204 (`git diff --stat 88bc5748..HEAD`): 16 under `web/src/`, 5 design boards and `canvas.json`, `design/README.md`, the Progress page and the ui-spec. Nothing under `packages/`.

## What the step does

- **Boards first** (`design/ui-canvas/`). `LiteResults` redone as the RunOutputs-style card, `MLiteResults` (the phone rows) and `LiteKind` (the kind badges) made, `LiteReportViewer` gains its way back.
- **Explorer** (`runs/ResultsBrowser.tsx`, `explorer.ts`). A kind badge with an icon, a file's name opening its preview, a **Download** icon button, sort buttons with `aria-sort`, the filter and its empty state, the 1,000-entry text, phone rows. The URL keeps `&sort=`, `&q=` and `&focus=`.
- **Way back to the task sheet.** `runSearch` keeps `&task=` and `&attempt=` (`taskSearch` in `explorer.ts`). `RunDetailPage` finds the task in the run's listing (`findTask`) and reopens its sheet on that attempt; closing the sheet removes the two keys. The Snakemake Outputs tab's **Preview** goes through `stat` (`DetailSheet.tsx`, `TaskFiles.tsx`).
- **Fix of CR-P3FU85D-01** (`ba8398c5`). When the task is not found or the read fails without being cancelled, the page shows `<p role="status">This job's sheet could not be reopened.</p>` under the header; the line goes when `&task=` is gone.

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `4036ccb9` | **approve** (0 blockers, 0 majors, 5 minors, 3 simplify) | **approve** (0 blockers, 0 majors, 2 minors) |
| fix | `ba8398c5` | CR-P3FU85D-01, test first | |
| 2 | `ba8398c5` | **approve** (0 blockers, 0 majors, 3 minors) | **approve** (no finding) |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | |

The reports were relayed in summary, so the texts below are summaries. Finding numbers collide across rounds (round 2 restarts at -02), so a round-2 finding is written `r2` here. The `simplify` findings are not counted.

```text
CODE  step=P3-fu85d  review=approve b/M/m=0/0/8  security=approve b/M/m=0/0/2  rounds=2  simplify=skipped -0/+0  tests=pass
```

**Test-first.** The worker reports that the test "a task the run's listing does not have opens no sheet" in `TaskFiles.test.tsx` was changed first to expect the status line, and failed before the code change. `doc-writer` did not put the base code back to check it.

**Gate.** The worker reports: pytest 1173 passed, 1 skipped (30 deselected); ruff check, ruff format --check, mypy (147 files), lint-imports (4 contracts kept), uv lock --check and tsc clean; vitest 421 of 421; `mkdocs build --strict` and `tools/docs/check.py` pass. `doc-writer` re-ran at the head:

```bash
cd web && npx vitest run src/runs/TaskFiles.test.tsx
```

```text
 Test Files  1 passed (1)
      Tests  20 passed (20)
```

**What the checks prove and do not prove.**

- The Vitest tests run on route mocks in jsdom. They prove the markup, the URL keys, the sort and filter logic and the status line on a missing task.
- They do not prove layout (jsdom has none) or the Playwright path: the "Playwright smoke on the results browser" of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85) was not built (CR-P3FU85D-05).
- Not run: a task past the run's first 2,000 on a real server; a screen reader on the new status line.

## Findings

Status is what `doc-writer` found at `ba8398c5` plus the docs commit. The security and code findings of round 1 were relayed in summary.

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85D-01 | minor | Reopening the sheet from `&task=&attempt=` fails without a word past the run's first 2,000 tasks. Each way back also costs up to 10 sequential reads of 200, and each read queues `sacct` asks for its page on a SLURM run. | fixed in `ba8398c5` for the silence (status line, test first, limit written in [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview)); the limit and the cost stay: FU-P3-96. The finding proposed a new `GET /runs/{id}/tasks/{task_id}`; the API catalogue already lists `GET /tasks/{id}` (api-and-data-model, line 121), so FU-P3-96 builds that one |
| CR-P3FU85D-02 | minor | A folder opened from the Outputs Preview keeps the way back to the sheet only on its first page: the entry links, the path bar and the file links in `ResultsBrowser` do not carry `task` and `attempt`, so one click into a subfolder or a file turns the back link into "<run> · Summary". | open: FU-P3-97 |
| CR-P3FU85D-03 | minor | `WhyItFailed` was edited (`page.items?.find` to `page.items.find`, `page.next ?? null` to `page.next`), unrelated to FU-P3-85d (surgical changes). | open: FU-P3-97 (the change is type-safe: `Page<T>` has both fields; it is not reverted) |
| CR-P3FU85D-04 | minor | The kind icons differ between the board and the client: `LiteKind` gives Text, PDF and Binary their own icons, `KIND_ICONS` maps text, pdf, binary and file to the same `ICONS.file`. The words match. | open: FU-P3-97 |
| CR-P3FU85D-05 | minor | The Playwright smoke on the results browser, in the -85d line of inbox #127, was not built, and the gap was written down nowhere. | open: written in the [Progress section](../../progress/W5/P3-M9.md#fu-p3-85d-the-results-explorer-sort-filter-and-url-state) and FU-P3-97 |
| CR-P3FU85D-06 | simplify | The new `.sp-vh` (`runs.css:1540`) duplicates `.sp-sr` (`shell/shell.css:13`). | open: left to the batch `code-simplifier` |
| CR-P3FU85D-07 | simplify | The Kind header is inserted inside the `COLUMNS` map with `i === 1 ? [<th key="kind">…</th>, th] : th`; the hidden index rule is harder to read than the table. | open: left to the batch `code-simplifier` |
| CR-P3FU85D-08 | simplify | An import cycle: `ReportViewer` imports `resultsSearch` from `ResultsBrowser`, and `ResultsBrowser` imports `isPlainText` and `isResultPath` from `ReportViewer`. The URL parsers are pure functions living in component modules. | open: left to the batch `code-simplifier` |
| CR-P3FU85D-r2-02 | minor | The status line says "job's", but a Nextflow run says "task" ([ui-spec §4.4](../../specs/ui-spec.md#44-run-detail), "The engine's words", UX-PAR-20). The test runs on the default Nextflow fixture (`web/src/testing.tsx:137`), so it makes the wrong word the expected one, and the ui-spec note repeated it. | open: [inbox #131](../inbox.md#131-assumed-the-status-line-of-a-lost-task-sheet-follows-the-engines-words-fu-p3-85d); the spec note now says the engine's word |
| CR-P3FU85D-r2-03 | minor | The live region is added to the page with its text already inside (`{sheetLost && <p role="status">…</p>}`), so screen readers may not announce it **[to be validated per reader]**. The rest of the app keeps `role="status"` always present and fills in the text later (`CopyMenu.tsx:94`, `:113`). | open: FU-P3-97 |
| CR-P3FU85D-r2-04 | minor | The path where the listing read fails without being cancelled (`.catch` then `setSheetLost(true)`) has no test; the only test covers `findTask` returning null. No test checks that the line goes away once `&task=` leaves the URL. | open: FU-P3-97 |
| SEC-P3FU85D-01 | minor | The report viewer's new Folder breadcrumb and its back-link label show the folder names from the URL's own `path`; nothing from the server confirms them. `ResultsBrowser.tsx:345` has the rule "never the URL's own text" (SEC-P3T32B-02), and this breaks it. `isResultPath` limits the risk (no control, bidi or format characters, no `..`, and the `h1` title already comes from the URL): a crafted link can show folder names that do not exist. | open: low risk; FU-P3-97 |
| SEC-P3FU85D-02 | minor | The no-match line quotes up to 200 characters of URL `q` inside Spectio's own sentence, so a crafted link can make text such as "Your session expired, call …" look like app copy. React renders a text node and `isPlainText` drops control, bidi and format characters: content spoofing only, no markup. | open: FU-P3-97 |

## For the Progress page

- **Fixed in the step:** the explorer, the URL state, the way back to the sheet, and (CR-P3FU85D-01) the silent failure of the way back.
- **Open, minor:** the limit of 2,000 tasks and its read cost (FU-P3-96); the eight other minors (FU-P3-97); three simplifications for the batch `code-simplifier`.
- **Assumed:** the word of the status line ([inbox #131](../inbox.md#131-assumed-the-status-line-of-a-lost-task-sheet-follows-the-engines-words-fu-p3-85d)).
- **Not done:** the Playwright smoke on the results browser; the work directory (FU-P3-85e).
