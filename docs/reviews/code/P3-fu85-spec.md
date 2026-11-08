# Pre-review · FU-P3-85, file explorer and preview (design only)

Step `P3-fu85-spec` on `autopilot/P3-fu85-spec`, base `90f19cbb`, 2026-11-08. The step writes the design of FU-P3-85 ([decision log](../../decisions/log.md#2026-11-08-file-explorer-and-preview-in-001-fu-p3-85-assumed), [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

Reviewed sections:
- [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview), new;
- [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview), new;
- [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 14, note 2026-11-08, and §15.1, the Results row.

## How the pre-review ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary, paths and symlinks, headers, caps; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code read for the design. It rendered the board LiteResults (1440 × 1180) and looked at it. **This review is not independent.** The orchestrator should run both agents on these sections before FU-P3-85a starts, and add their findings here.

Code read for the design: `api/taskfiles.py`, `api/logs.py`, `api/results.py`, `files/taskfiles.py`, `files/results.py`, `files/confine.py`, `static.py` (the app's CSP, `img-src 'self'`), `api/browser.py` (`Sec-Fetch-Site` already checked), `web/src/runs/TaskFiles.tsx`, `ResultsBrowser.tsx`, `ResultsSection.tsx`, `ReportViewer.tsx`, `LogViewer.tsx`, `DetailSheet.tsx`.

## Security checklist (`security-reviewer`)

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

## UX checklist (`ux-reviewer`)

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

## Follow-ups

- Run `security-reviewer` and `ux-reviewer` as agents on the three sections before FU-P3-85a (this record is a self-review).
- FU-P3-85a to -85e: [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85), Build plan.
