# Code review · FU-P3-85c: the file preview page for the results directory

`review-code` on `autopilot/P3-fu85c`, base `fff6c18f`, head `35f4e6f2` (five commits: `3e8ad4aa` the boards, `cba2308b` the page, `8ef254fb` the round-1 fix, `9b4bc335` the round-2 fix, `35f4e6f2` the round-3 fix), 2026-11-09. The step is the third task of the build plan of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85): the browser side of the preview of one results file, on the server routes of [P3-fu85a](P3-fu85a.md) and [P3-fu85b](P3-fu85b.md). The behaviour is owned by [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview) and [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview). Progress: [P3 · M9, FU-P3-85c](../../progress/W5/P3-M9.md#fu-p3-85c-the-file-preview-page-for-the-results-directory). Format: [`README.md`](../README.md).

Outside `docs/`: 24 files, +2,061 −50 over the base (`git diff --shortstat fff6c18f..HEAD -- . ':!docs'`): the web client (`web/src/runs/FilePreview.tsx`, `preview.ts`, `LogViewer.tsx`, `runs.css`, `api.ts`, `routes.tsx` and their tests), three design boards, one route added to `static.py`, a Playwright spec and its seed, and one CI line. Three of the 24 files are boards.

## What the step does

- **Boards first** (`design/ui-canvas/`). `LiteFilePreview`, `MLiteFilePreview` and `LiteFilePreviewStates`, rendered with `tools/canvas/render.js` before the page was written.
- **Route** (`routes.tsx`, `static.py`). `/runs/{id}/results/file?path=<file>`, also served as a screen with `img-src 'self'` (`test_file_preview_is_a_screen`).
- **Page** (`runs/FilePreview.tsx`). It asks the `stat` route first; the kind, the facts, the 20 MiB image cap and the path come from that answer. Then one viewer by kind:
    - **Text:** whole up to 64 KiB; else Start (with Load more from the `Content-Range` end + 1) or End; the 1 MiB and 20,000-line caps each stop Load more and say so on one line.
    - **JSON:** a depth pre-scan, a 2 MiB cap on the formatted text, a fall-back to text with the reason. **Table:** the first 1 MiB, 500 rows, 50 columns, cells cut at 1,000 characters. **Image:** an `<img>` of the raw route with `as=image`, one error state with Retry and Download. **PDF**, **binary** and **HTML** are states with a link.
- **Pure helpers** (`runs/preview.ts`). `fileKind`, `capLines`, `wholeLines`, `jsonView`, `parseTable` and the caps.
- **`LogViewer` props** (`start`, `levels`, `gutterFrom`, `wrap`, `searchButton`). The run logs keep their defaults.
- **Client** (`api.ts`). `statResult`, `readResultText` (Range and tail reads) and `resultUrl` with `as` and `download`.
- **Playwright** (`tests/e2e/preview.spec.ts`, in CI for the `desktop` and `phone` projects). A hostile SVG in the preview's `<img>` runs nothing and fetches nothing; the same URL, loaded in the `<img>` first, downloads on a top-level navigation; Load more keeps focus in a real browser on a seeded 200 KiB `logs/big.log`.

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `cba2308b` | **changes** (0 blockers, 3 majors, 6 minors, 2 simplify; one minor, CR-11, predates the step) | **changes** (0 blockers, 1 major, 4 minors) |
| fix | `8ef254fb` | CR-01, -02, -03, SEC-01 (and SEC-04 with CR-02) | |
| 2 | `8ef254fb` | **approve** (0 blockers, 0 majors, 4 minors) | **approve** (0 blockers, 0 majors, 2 minors) |
| fix | `9b4bc335` | R2-CR-04 and R2-CR-05 | |
| 3 | `9b4bc335` | **changes** (0 blockers, 2 majors, 2 minors, 1 simplify) | **approve** (no finding) |
| fix | `35f4e6f2` | R3-CR-06 and R3-CR-07, each with a test that failed first | |
| 4 | `35f4e6f2` | **approve** (0 blockers, 0 majors, 3 minors) | **approve** (no finding) |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | |

The heads are taken from the commit order; the reports were relayed in summary, so the finding texts below are summaries.

**Finding IDs.** The reviewers numbered each round again from `-01`. Round 1 keeps the plain form (`CR-P3FU85C-01` to `-11`, `SEC-P3FU85C-01` to `-05`). The later rounds are written `R2-`, `R3-` and `R4-` (`CR-P3FU85C-R3-06` is round 3's `CR-P3FU85C-06`). The commit messages of `9b4bc335` and `35f4e6f2` use the plain form for rounds 2 and 3.

```text
CODE  step=P3-fu85c  review=approve b/M/m=0/0/3  security=approve b/M/m=0/0/0  rounds=4  simplify=skipped -0/+0  tests=pass
```

The counts are those of round 4. The minors and simplify items of rounds 1 to 3 that no commit closed are still open and are listed in the table below; none is a blocker or a major.

**Test command and result** (re-run by `doc-writer` at `35f4e6f2`):

```bash
cd web && npx --no-install vitest run src/runs/FilePreview.test.tsx src/runs/LogViewer.test.tsx \
  src/runs/preview.test.ts src/runs/previewApi.test.ts src/api.test.ts
cd web && npx --no-install tsc --noEmit
uv run --locked pytest packages/spectio-server/tests/api/test_web.py -q
```

```text
 Test Files  5 passed (5)
      Tests  106 passed (106)
tsc: exit 0
27 passed in 4.73s
```

**Tests that failed first** (relayed by the worker): the test of each of the two round-3 fixes failed before its fix. The round-1 and round-2 fixes carry their own tests (`CR-P3FU85C-04`, `-05` and `-06` are in the test names of `FilePreview.test.tsx`).

**Not run by `doc-writer`:** `tests/e2e/preview.spec.ts` (it needs `spectio serve` on a seeded run; the worker's run on Chromium is relayed by the commit message of `8ef254fb`: with the old build the Load more button lost focus, with the new one it keeps it). **Firefox and WebKit were not run** for it, though [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85) names all three and [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview) asks for the SVG check on them; CI runs the `desktop` (Desktop Chrome) and `phone` (Pixel 7) projects only (R2-CR-07, SEC-02).

## Findings

Fixed (a commit named it, with a test):

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85C-01 | major | Load more did not stop at the 20,000-line cap: the cap lived inside `Lines`, so a 64 KiB read with more than 20,000 lines showed the cap line, "… cut at 64 KiB" and Load more together, and each further read joined bytes that were never rendered. | fixed in `8ef254fb`: `TextView` computes `capLines` itself; Load more stops; the search line says "Search covers the 20,000 lines shown" |
| CR-P3FU85C-02, SEC-P3FU85C-04 | major, minor | A Load more still in flight was appended to whatever the viewer held when it landed (after End, Start or Reload), with a stale `next`. | fixed in `8ef254fb`: its own `AbortController`, aborted by the next read; an aborted answer is dropped |
| CR-P3FU85C-03 | major | Mantine's `loading` sets the native `disabled`, which probably drops focus in a real browser (ui-spec §4.4.1: "Load more otherwise keeps focus"); the jsdom test could not see it. | fixed in `8ef254fb`: not disabled while it loads, `aria-busy` and clicks ignored; the Playwright check on `logs/big.log` shows the old build losing focus and the new one keeping it (relayed) |
| SEC-P3FU85C-01 | major | The SVG check never loaded the image in an `<img>` before the top-level navigation, so the step the task names was not tested. | fixed in `8ef254fb`: the check loads the SVG in the preview's `<img>`, then navigates to the same URL from that page |
| CR-P3FU85C-R2-04 | minor | A Load more that crossed 20,000 lines made the button disappear while it had focus; the cap line could not take focus; both caps showed two lines. | fixed in `9b4bc335`: one focusable cap line (`tabIndex=-1`); with both caps, the 20,000-line sentence |
| CR-P3FU85C-R2-05, CR-P3FU85C-04 (part) | minor | On the phone the search field was always shown, not behind a Search button (ui-spec §4.4.1 Phone, board line 43). | fixed in `9b4bc335`: a native `<button aria-expanded>` that moves focus into the field |
| CR-P3FU85C-R3-06 | major | The cap line took focus on the first read and after End, away from the file name or from End. | fixed in `35f4e6f2`: focus moves only when a Load more reached the cap (`stoppedByMore`); the line still shows on either cap |
| CR-P3FU85C-R3-07 | major | `searching` was set from `searchButton` once, at mount; after a phone-to-desktop change neither the button nor the field showed, and after desktop-to-phone the field showed open and took focus. | fixed in `35f4e6f2`: `open = !searchButton \|\| searching`; focus moves only after Search is pressed |

Open (none blocks; follow-up FU-P3-94 takes the preview items, FU-P3-95 the script):

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85C-04 (part) | minor | On the phone the breadcrumb is not shortened in the middle (ui-spec §4.4.1; board MLiteFilePreview line 33 shows `results / … / log / <file>`): every part is rendered, with no truncation. Not disclosed by the worker. | open: FU-P3-94 |
| CR-P3FU85C-05, SEC-P3FU85C-03, R2-SEC-02 | minor | The 2 MiB cap on formatted JSON is checked after `JSON.stringify` has built the whole string. The depth pre-scan allows 64 levels, so each element can carry up to 128 characters of indentation. Measured by the reviewers: 1 MiB of JSON (63 levels, then 512K zeros) becomes 68,681,531 characters in 285 ms on their host; 800 KB gives 52,408,318 characters in 192 ms. The fallback is correct; the cost the cap means to bound is paid first, and a phone is the most exposed. | open: FU-P3-94, [inbox #130](../inbox.md#130-assumed-the-file-preview-as-built-open-caps-and-phone-gaps-fu-p3-85c) |
| R2-SEC-03 | minor | `LogViewer`'s search has no cap on matches. A one-character query on 1 MiB of text, or 2 MiB of formatted JSON, can create about a million `<mark>` elements in one render, which breaks the 20,000-line DOM budget by another route. Hardening, not a leak. | open: FU-P3-94, inbox #130 |
| CR-P3FU85C-06 | minor | An End read can say "This file is empty." for a non-empty file: if the last 64 KiB holds one newline, as its last character, `wholeLines` returns "" and the empty state shows. A file of 64 KiB or less is read with `tail`; if it grew between `stat` and read, the last 64 KiB are shown as "Whole file" from line 1. | open: FU-P3-94 |
| CR-P3FU85C-07 | minor | Reload does not read an image again: `ImageView`'s `<img>` is keyed by `tries` only and its `src` does not change, so the browser keeps the old image (ui-spec §4.4.1: Reload "reads again in the same mode"). | open: FU-P3-94 |
| CR-P3FU85C-08 | minor | The `h1` takes focus only when `stat` succeeds. On a 404, 409, 503 or other refusal, and for a path the client refuses, focus stays where the navigation left it (ui-spec §4.4.1: the `h1` "takes focus on open"). | open: FU-P3-94 |
| CR-P3FU85C-11 | minor | Predates the step. TanStack's default search parser JSON-parses `?path=`, so a typed or shared URL for a root file named `2024`, `1.5`, `true` or `null` becomes a non-string; `resultsSearch` drops it and the page says "Not a file of this run's results." In-app links round-trip. The worker raised it as an open question. | open: FU-P3-94 |
| CR-P3FU85C-R3-08, R4-09 | minor | On the phone, closing Search hides the field, the counter and Previous / Next, but `typed` and `query` are kept: the log keeps its `<mark>` highlights and current match, with nothing on screen to explain or step through them. | open: FU-P3-94 |
| CR-P3FU85C-R3-10 | minor | On the phone the Search button sits in `LogViewer`'s filter row. Board `MLiteFilePreview:43` draws it full width in the action row beside Wrap lines. The worker reported this gap. | open: FU-P3-94 |
| R2-CR-06 | minor | Test gaps: the 410 refusal state (in the step's scope) has no test; one test name claims three cases and checks only the PDF. | open: FU-P3-94 |
| SEC-P3FU85C-05 | minor | No regression test covers the "Content is text" rule of ui-spec §4.4.1. It holds today (React escapes the content; the diff has no `dangerouslySetInnerHTML`, checked with grep), but nothing stops a later change. | open: FU-P3-94 |
| CR-P3FU85C-R4-10 | minor | The R3-06 regression test uses a 64 KiB file, which is a whole read, so the `!whole` guard alone makes it pass. No test has a Start read of a file over 64 KiB whose first chunk passes 20,000 lines; dropping `(next ?? 0) > READ` would fail none. | open: FU-P3-94 |
| SEC-P3FU85C-02, R2-CR-07 | minor | api §5.3 asks for the SVG check on Chromium, Firefox and WebKit. CI runs only Chromium projects. The other two are recorded as not run here and on the Progress page, which the worker's report did not do. | open: FU-P3-94 (add the projects to the preview spec, or record Thomas's choice in inbox #130) |
| R2-CR-07 (part) | minor | The worker's open issue: `serve-local.sh` waits on a TCP port while `serve` listens on a Unix socket. It had no follow-up number. | open: FU-P3-95 |
| CR-P3FU85C-09, CR-P3FU85C-10, R3-09, R4-08 | simplify | `readResultText` repeats, a fourth time, the refusal parsing of `getTaskFile` (`body?.detail ?? body?.title ?? HTTP n`); `FilePreview.tsx` defines `join`, identical to `ResultsBrowser.tsx:25`; the `after` prop is a fragment around one conditional; `!whole` in `stoppedByMore` is redundant (a whole read has `next` never above `READ`). | open: for the batch `code-simplifier` |

## For the Progress page

- **Built:** the boards, `/runs/{id}/results/file`, the viewers by kind, the 1 MiB and 20,000-line caps with one focusable cap line, the phone Search button, the Playwright checks of the SVG and of Load more focus.
- **Open, minor:** the table above; none blocks.
- **Assumed:** the caps of ui-spec §4.4.1 as the spec states them; the cap line takes focus only after a Load more reached it; Load more stays enabled while it loads (`aria-busy`); the breakpoint test toggles the `searchButton` prop directly, because the `viewport()` helper stubs `matchMedia` and fires no change event.
- **Not done:** Firefox and WebKit for `preview.spec.ts`; the phone breadcrumb; the explorer (FU-P3-85d); the work directory (FU-P3-85e).
