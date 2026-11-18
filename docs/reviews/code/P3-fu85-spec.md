# Pre-review · FU-P3-85, file explorer and preview (design only)

Step `P3-fu85-spec` on `autopilot/P3-fu85-spec`, base `90f19cbb`, 2026-11-08. The step writes the design of FU-P3-85 ([decision log](../../decisions/log.md#2026-11-08-file-explorer-and-preview-in-001-fu-p3-85-assumed), [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

There is no `CODE` line in this record: the step changes no code, so there is no code to review.

Reviewed sections:
- [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview), new;
- [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview), new;
- [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 14, note 2026-11-08, and §15.1, the Results row.

## Rounds

| Round | Who | Independent | security | UX |
|---|---|---|---|---|
| R0 | the design worker, on the two agents' checklists | **no** | changes 0/2/7 | changes 0/1/9 |
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator on the R0 design, in parallel | yes | **changes 0/2/9** | **changes 0/5/15** |

The R1 findings are all applied below; the design in the specs is the one after R1.

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary, paths and symlinks, headers, caps; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code read for the design. It rendered the board LiteResults (1440 × 1180) and looked at it. **This review is not independent.** R1 below is the independent round; it found that several R0 items were applied only in part.

Code read for the design: `api/taskfiles.py`, `api/logs.py`, `api/results.py`, `files/taskfiles.py`, `files/results.py`, `files/confine.py`, `static.py` (the app's CSP, `img-src 'self'`), `api/browser.py` (`Sec-Fetch-Site` already checked), `web/src/runs/TaskFiles.tsx`, `ResultsBrowser.tsx`, `ResultsSection.tsx`, `ReportViewer.tsx`, `LogViewer.tsx`, `DetailSheet.tsx`.

### Security checklist (`security-reviewer`)

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=2  minors=7
```

Every finding was applied to the design before the commit. The verdict is the verdict on the first draft.

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| SEC-PRE-FU85-01 | major | A work directory as a root would list and serve `.command.env` (the task's environment values) and `.command.run` without its hiding, bypassing req. 13's "Not served" list. | yes: any part starting with `.` is hidden and refused (`422`) under `workdir` (api §5.3, req. 14 note) |
| SEC-PRE-FU85-02 | major | Serving an SVG, or any file named as an image, inline lets a navigation to the raw URL render it as a document on the app's origin (stored XSS by anyone who can write to the results directory). | yes: image mode only with `Sec-Fetch-Dest: image`, otherwise an attachment; CSP `sandbox; default-src 'none'` and `nosniff` on the image too; never inline, never in a frame (api §5.3, req. 14 note) |
| SEC-PRE-FU85-03 | minor | A `.png` that holds HTML could be sniffed. | yes: a signature check against the MIME Sniffing patterns, `422` otherwise, plus `nosniff` |
| SEC-PRE-FU85-04 | minor | Another site could load the images with the user's tunnel and session. | yes: `Cross-Origin-Resource-Policy: same-origin` |
| SEC-PRE-FU85-05 | minor | An HTML file in a work directory has no report viewer and must not render. | yes: always an attachment from `workdir/raw` |
| SEC-PRE-FU85-06 | minor | File content with escapes, bidi controls or markup reaching the DOM. | yes: `strip_escapes` and `FORMAT_CHARS` on every text read; the screens put content in as text nodes only (ui-spec §4.4.1, "Content is text") |
| SEC-PRE-FU85-07 | minor | A preview could load a lot through the file pool or into the browser. | yes: 1 MiB per text read, 1 MiB kept in the page, 20 MiB per image, one image per page, every read in the file pool with its 5 s wait |
| SEC-PRE-FU85-08 | minor | `Sec-Fetch-Dest` is set by the client and must not decide access. | yes: api §5.3 says it decides how a file is served, never whether |
| SEC-PRE-FU85-09 | minor | A later preview of compressed files is a decompression bomb risk. | recorded: Later, "needs a cap on decompressed bytes and a review of its own" (inbox #127 choice 10) |

Checked and unchanged: no new listener or TCP port (the Unix socket decision of 2026-11-08 holds); the routes are reads, so the write checks of req. 7 do not apply; names go through `check_rel` and the confined walk; a published link is followed only into a task directory of the same run.

### UX checklist (`ux-reviewer`)

```text
UX-REVIEW  verdict=changes  blockers=0  majors=1  minors=9
```

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| UX-PRE-FU85-01 | major | No board shows a preview, a sort or the phone layout of the results browser; the board conventions need boards before screen code. | yes: LiteFilePreview, MLiteFilePreview, MLiteResults made and LiteResults updated first in FU-P3-85c and -85d (ui-spec §4.4.1, Boards) |
| UX-PRE-FU85-02 | minor | Line numbers on a read of the end would be wrong. | yes: numbers only for a read from the start; "line numbers not known" otherwise |
| UX-PRE-FU85-03 | minor | A 1,000-row table does not fit the phone. | yes: phone rows; the table preview in a focusable region that scrolls sideways |
| UX-PRE-FU85-04 | minor | Sort needs a keyboard path and a state screen readers hear. | yes: header `<button>`s with `aria-sort`; a native `<select>` on the phone |
| UX-PRE-FU85-05 | minor | Back from a preview would lose the sort. | yes: `&sort=` in the URL, kept by the back link |
| UX-PRE-FU85-06 | minor | A known binary file would flash a text load, then `415`. | yes: the known-binary extension list goes straight to facts and Download |
| UX-PRE-FU85-07 | minor | One very long line can freeze the viewer. | yes: a line is cut at 10,000 characters in the view |
| UX-PRE-FU85-08 | minor | `409 run-dir-unreachable` has no words on the screens yet. | yes: "The run's directory is not reachable", with the server's text and Retry |
| UX-PRE-FU85-09 | minor | Load more must keep focus and say what changed. | yes: focus stays, a polite region says "n KiB shown" |
| UX-PRE-FU85-10 | minor | On the phone, Download needs two taps (the preview, then Download). | not applied, open: rows stay one link each at 44 px |

Not taken: previous and next file in the preview (useful in a FastQC folder) is on the Later list.

## Round R1 (independent)

`security-reviewer` and `ux-reviewer` read the R0 design (commit `a85ecc4b`) on 2026-11-08, independent and in parallel; the coordinator relayed their findings in summary, so the texts below are summaries. Both agree with a page of its own and one folder at a time for 0.0.1.

### `security-reviewer`

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=2  minors=9
```

It disagreed with R0 on SEC-PRE-FU85-01 (applied only in part: R1-01), -03 (the stated reason was wrong: R1-03), -04 (too narrow: R1-06), -06 (in part: R1-11, R1-02), -07 (not applied: R1-02, R1-07), and on "checked and unchanged", which missed the session and cross-site tests (R1-09).

| ID | Sev. | Finding | Done |
|---|---|---|---|
| SEC-PRE-FU85-R1-01 | major | The workdir routes serve staged inputs (copies, hard links, links into a task directory of the run), while req. 13's "Not served" list names staged inputs and the req. 14 note said that list still held. | req. 13 note 2026-11-08 amends the owner list: a copy, an own hard link or a same-run task link is served like an output, any other link stays unserved, another uid's hard link is refused by `fstat`; the req. 14 note points to it; tests named (api §5.3), FU-P3-85e |
| SEC-PRE-FU85-R1-02 | major | Byte caps do not bound DOM and CPU. | ui-spec §4.4.1: at most 20,000 lines rendered, then a stop line; JSON depth pre-scan (64), 2 MiB formatted cap, fallback text; the table parser stops after row 501 and cuts cells at 1,000 characters; the Vitest cases in FU-P3-85c |
| SEC-PRE-FU85-R1-03 | minor | The signature check read another opening than the bytes served; the reason given (sniffing) was wrong; ui-spec and api disagreed (415 / 422); the UI could not see the status of an `<img>`. | the check is on the first chunk, sent as the first part of the body, said to be advisory; `(st_dev, st_ino)` compared on every raw chunk (whole raw route); `422` in both specs; the UI decides the caps from `stat` before making the `<img>`, and any `onerror` shows one state. FU-P3-85b |
| SEC-PRE-FU85-R1-04 | minor | `Vary`, cross-engine proof, untrustworthy origins. | `Vary: Sec-Fetch-Dest` on both answers; Playwright on Chromium, Firefox and WebKit (load in `<img>`, then navigate: download, no script); req. 14 note says a request without Fetch Metadata falls back to Download; Safari 16.4+ **[to be validated]** with the caniuse source |
| SEC-PRE-FU85-R1-05 | minor | The image-mode order was not written down. | api §5.3 table of 8 steps, one `test_req14_image_*` per row |
| SEC-PRE-FU85-R1-06 | minor | CORP only on images; the Job files text read lacks the CSP. | CORP on every file and listing route from the shared headers; CSP `sandbox; default-src 'none'` on the Job files read (api §5.3 Shared changes, req. 14 note). FU-P3-85a |
| SEC-PRE-FU85-R1-07 | minor | Decoded size is not bounded by file size. | 50 megapixels from the image header (PNG `IHDR`, GIF, WebP, JPEG `SOFn`), `422`; SVG 5 MiB; a 60000 × 60000 PNG test; browser decode limits **[to be validated]**. FU-P3-85b |
| SEC-PRE-FU85-R1-08 | minor | An empty file was `422`; Load more offsets; bytes joined across chunks. | empty file `200`; the next read starts at `Content-Range` last + 1; chunks joined as decoded text; tests on an empty file and a range splitting `C3 A9` |
| SEC-PRE-FU85-R1-09 | minor | Missing tests: no session, same-site, dot names on every workdir route, `x -> .command.env`, URL-unsafe names; screen routes not in `static.ROUTES`. | all listed in api §5.3 Tests and the FU-P3-85c Vitest; the three screen routes go to `static.ROUTES` in FU-P3-85c and -85e; a run from a terminal is `404 not-found` in §5.3's problems |
| SEC-PRE-FU85-R1-10 | minor | `JSON.parse` changes big integers and repeated keys. | the line "Formatted view: large numbers and repeated keys may differ" and Show as text; Vitest with a big integer and a repeated key. A token-keeping formatter: **Later** |
| SEC-PRE-FU85-R1-11 | minor | `strip_escapes` drops everything after an unterminated OSC (`files/redact.py`, the `_ESCAPES` OSC branch; reproduced). | api §5.3 Shared changes: only the introducer is removed when no terminator comes within 4 KiB; a test. FU-P3-85a |

### `ux-reviewer`

```text
UX-REVIEW  verdict=changes  blockers=0  majors=5  minors=15
```

| ID | Sev. | Finding | Done |
|---|---|---|---|
| UX-PRE-FU85-R1-01 | major | Nothing fed the facts line or the server-answered path, and the parent listing fails past 1,000 entries. | `stat` routes for results and work directories; the page asks `stat` first; `Content-Range` always carries the total. FU-P3-85a, -85e |
| UX-PRE-FU85-R1-02 | major | 415 vs 422 for a wrong image; `<img>` cannot see statuses. | `422` everywhere; caps from `stat`; one `onerror` state with Retry and Download; 413 and 415 dropped from the image state words. An `image_ok` field in `stat` was not added: the one state covers it |
| UX-PRE-FU85-R1-03 | major | No way back to the task sheet; work-directory pages unspecified. | `runSearch` keeps `&task=` and `&attempt=`, the sheet reopens with focus on its `h1`; the work-directory page's `h1`, back link, breadcrumb and title written. FU-P3-85d, -85e |
| UX-PRE-FU85-R1-04 | major | `LogViewer` as it is fits logs, not files. | props `start`, `levels`, `gutterFrom`, `wrap`; levels only for `.log`, `.out`, `.err` and job files; "Search covers the <n> KiB shown". FU-P3-85c |
| UX-PRE-FU85-R1-05 | major | Load more offsets and UTF-8 seams. | a read ends at the last whole UTF-8 sequence and `Content-Range` gives the real end; the UI reads on from there, joins the partial line, drops the cut marker; `test_req13_results_text_utf8_seam` and a Vitest |
| UX-PRE-FU85-R1-06 | minor | A file of a running run changes. | "read at HH:MM" and Reload while the run is not ended, with the Job files line |
| UX-PRE-FU85-R1-07 | minor | "Text" for every unknown name; known-binary list short. | Text only for a known list; unknown is "File", tries text, falls back on `415`; the binary list gains `.bw`, `.bigwig`, `.bb`, `.h5ad`, `.loom`, `.npy`, `.npz`, `.pod5`, `.fast5`, `.2bit`, `.zst`, `.7z` |
| UX-PRE-FU85-R1-08 | minor | Filter not kept; Back loses the row; no empty-filter state. | `&q=` (history replace), live region after 150 ms, `&focus=` on the back link, "No entry in this folder matches …" with Clear |
| UX-PRE-FU85-R1-09 | minor | The report viewer from the explorer returns to the Summary. | back to the file's folder with `sort` and `q`, breadcrumb ends with the file; LiteReportViewer in FU-P3-85d |
| UX-PRE-FU85-R1-10 | minor | Table details. | "Showing 50 of n columns", short rows padded, `#` lines above the table, the partial last row dropped, "Column 1…n" when the header is off, sticky header row and first column |
| UX-PRE-FU85-R1-11 | minor | Start / End and the whole-file case. | Start / End as a pressed pair; "Whole file · <size>" with no paging up to 64 KiB; at the 1 MiB cap focus moves to the cap line |
| UX-PRE-FU85-R1-12 | minor | Phone order and gutter with wrap. | the phone order written; Search behind a button; levels only for logs; lines as grid rows (number and text) when wrapped |
| UX-PRE-FU85-R1-13 | minor | Transparent images in dark mode; actual size. | a fixed light backdrop; Actual size into a focusable scroll region |
| UX-PRE-FU85-R1-14 | minor | Boards for the states and the work directory; a cleaned attempt. | LiteFilePreviewStates (FU-P3-85c), LiteWorkdir (FU-P3-85e); the sheet shows "The work directory was removed" instead of Browse |
| UX-PRE-FU85-R1-15 | minor | Outputs Preview on any path. | only when `isResultPath`; through `stat` to the folder or the file; named "Preview <path>" |
| UX-PRE-FU85-R1-16 | minor | The truncation text implies an order. | "… Spectio lists 1,000 of them, in no particular order; sort and filter see only those." |
| UX-PRE-FU85-R1-17 | minor | Long names and paths. | `overflow-wrap: anywhere` on the `h1` and the path; a phone breadcrumb shortened in the middle; one long-name row on MLiteResults and MLiteFilePreview |
| UX-PRE-FU85-R1-18 | minor | "Clean, like depictio". | the results card laid out as RunOutputs' "Published files"; Kind as a text badge with an icon; Download as a right-hand icon button; one set of kind names recorded in ui-spec §4.4.1 |
| UX-PRE-FU85-R1-19 | minor | HTML from a work directory. | Kind "HTML (not opened)" and its preview sentence with Download |
| UX-PRE-FU85-R1-20 | minor | The RunOutputs tree. | inbox #127 choice 2 says it is the 1.0 direction and that FU-P3-85d's rows, badges and actions are built for reuse there |

### Moved to Later by R1

Only what is clearly extra for 0.0.1: a JSON formatter that keeps tokens as written (R1-10, the line and Show as text are built instead), a virtualised viewer past 20,000 lines (R1-02 takes the cap instead), search over a whole file (R1-04's "search covers the KiB shown" is built instead), and the optional `image_ok` field of `stat` (R1-02, not needed with one `onerror` state).

## Follow-ups

- FU-P3-85a to -85e: [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85), Build plan.
