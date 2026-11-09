# Code review · FU-P3-85e: the work directory of a Nextflow attempt, server and pages

`review-code` on `autopilot/P3-fu85e`, base `6230c9b4`, head `6c4b280e` (three commits: `e4911863` the server routes, `cb4ae603` the boards and pages, `6c4b280e` the round-1 fix), 2026-11-09. The step is the last task of the build plan of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85): the four `workdir` routes, and the folder and file pages of a work directory on the components of [P3-fu85c](P3-fu85c.md) and [P3-fu85d](P3-fu85d.md). The behaviour is owned by [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview) and [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview); confinement by [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13 (note of 2026-11-08) and req. 14. Progress: [P3 · M9, FU-P3-85e](../../progress/W5/P3-M9.md#fu-p3-85e-the-work-directory-of-a-nextflow-attempt). Format: [`README.md`](../README.md).

Outside `docs/`: 29 files, +1,574 −192 over the base (`git diff --stat 6230c9b4..HEAD`): 12 under `packages/spectio-server/` (one new route module `api/workdir.py`, 349 lines of new tests, the OpenAPI snapshot), 10 under `web/src/`, 4 design boards with `canvas.json` and `design/README.md`, and one wheel contents list.

## What the step does

- **Server** (`api/workdir.py`, `files/taskfiles.py`, `files/results.py`, `api/results.py`, `app.py`, `static.py`). `GET /tasks/{id}/attempts/{n}/workdir` and its `stat`, `text` and `raw` routes: the results readers on a second root, `TaskDir`.
    - A name with a part that starts with `.` is hidden from the listing and refused by the others, `?download=true` and `as=image` included (`check_work_rel`).
    - A last-component link is followed only into a task directory of the same run; `x -> .command.env` is `link_outside`. A staged copy or the user's own hard link is served like an output; another uid's hard link is refused by the `fstat` owner check.
    - `.html` and `.htm` are always attachments.
    - A Snakemake attempt, an attempt of a run started from a terminal (`AttemptFiles.observed`) and an attempt with no recorded work directory are `404`; `410` and `409` as the Job files routes.
    - The raw answer is shared with the results route (`raw_response`). `/runs/{id}/workdir` and `/runs/{id}/workdir/file` join `static.ROUTES`. The OpenAPI snapshot and the wheel contents list gain the new routes.
- **Boards first** (`design/ui-canvas/`). A new `LiteWorkdir` (the folder page and states A to E); Browse work directory on `LiteTaskFiles` and `MLiteTaskFilesSheet`; the cleaned line on `LiteTaskFilesStates`.
- **Pages** (`routes.tsx`, `ResultsBrowser.tsx`, `FilePreview.tsx`, `api.ts`, `TaskFiles.tsx`). The same two components take a `WorkRoot` `{task, attempt}`: `h1` "Work directory · <task> · attempt <n>", the crumb "work directory", titles that name the task, HTML as "HTML (not opened)" with Download only, a dot name refused before any read (`hasDotPart`). The task sheet shows **Browse work directory**, or "The work directory was removed" when every file is cleaned; a run started from a terminal shows neither.
- **Round-1 fix** (`6c4b280e`). The work-directory file page's back link goes to its folder with `sort`, `q`, `focus`, `task` and `attempt` (CR-P3FU85E-01). The folder page shows "The run's directory is not reachable" (409) and "Spectio cannot read the cluster's files right now" (503) with Retry (CR-P3FU85E-03).

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `cb4ae603` | **approve** (0 blockers, 0 majors, 5 minors, 1 simplify) | **approve** (0 blockers, 0 majors, 2 minors) |
| fix | `6c4b280e` | CR-P3FU85E-01 and -03 fixed, test first; -02 kept as built | |
| 2 | `6c4b280e` | **approve** (0 blockers, 0 majors, 2 minors, 2 simplify) | **approve** (no finding) |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | |

The heads are taken from the commit order; the reports were relayed in summary, so the finding texts below are summaries. The reviewers numbered round 2 again, so a round-2 finding is written `R2-` here (`R2-CR-04` is round 2's `CR-P3FU85E-04`; round 1's `CR-P3FU85E-04` is the `Results.reports` type). The `simplify` items are not counted.

```text
CODE  step=P3-fu85e  review=approve b/M/m=0/0/7  security=approve b/M/m=0/0/2  rounds=2  simplify=skipped -0/+0  tests=pass
```

The counts are the minors of both rounds, as in [P3-fu85d](P3-fu85d.md#review-rounds).

**Test-first.** The worker reports that the fixes of CR-P3FU85E-01 and -03 were written test first: the back-link test of the HTML-file page (it opens with `sort=size&q=S19` and checks the one back link outside the breadcrumb), and a parameterised 409/503 test (title, the server's detail for 409, Retry reloads the listing). `doc-writer` did not put the base code back to check that they failed first.

**Test command and result** (re-run by `doc-writer` at `6c4b280e`):

```bash
cd web && npx --no-install vitest run src/runs/Workdir.test.tsx src/runs/TaskFiles.test.tsx
cd web && npx --no-install tsc --noEmit
uv run --locked pytest packages/spectio-server/tests/api/test_workdir.py \
  packages/spectio-server/tests/api/test_web.py packages/spectio-server/tests/api/test_openapi.py -q
```

```text
 Test Files  2 passed (2)
      Tests  31 passed (31)
tsc: exit 0
48 passed in 5.57s
```

**Not run by `doc-writer`:** the rest of the gate (ruff, mypy, lint-imports, the full pytest and vitest runs; the worker's report gives none of their numbers), any Playwright spec, and a real Nextflow work directory on a cluster. The server tests build their work directories in a temporary directory.

## Findings

Status is what `doc-writer` found at `6c4b280e` plus the docs commit.

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85E-01 | minor | The work-directory file page's back link went to the task sheet, not to the file's folder ([ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview) Preview: "a back link to its folder (with `sort`, `q` and `focus`)"); the breadcrumb carried no `focus`, so a keyboard user lost their row. | fixed in `6c4b280e`, test first; `BackToTask` is now used by the folder page only and no longer exported |
| CR-P3FU85E-02 | minor | The card heading is "Work directory · n folders, m files", the spec says "Work directory · <task name> · attempt <n>". The `LiteWorkdir` board was drawn the same way and the difference was recorded nowhere. | kept as built: the `h1` already names the task and the attempt. Written in the [ui-spec note](../../specs/ui-spec.md#441-file-explorer-and-preview) and in [inbox #132](../inbox.md#132-assumed-the-work-directory-card-heading-keeps-the-counts-fu-p3-85e) |
| CR-P3FU85E-03 | minor | On the folder page a 409 (and a 503) showed only the server's detail as an alert, with no title and no Retry; board state E and the spec's States draw both. | fixed in `6c4b280e`, test first (the mapping also serves the results folder page, which shares the component) |
| CR-P3FU85E-04 | minor | `Results.reports` stays required in the type, but a work directory's listing has no `reports`; `listResults(..., work)` is typed to return a field the server never sends, and only a comment says so. Nothing reads it today. | open: FU-P3-98 |
| CR-P3FU85E-05 | minor | `useTaskName` runs `findTask` on every mount (up to 10 reads of 200). `WorkdirFileRoute` keys `FilePreview` by path, so each work-directory file opened repeats those reads only to get the task's name. | open: FU-P3-98; FU-P3-96 (`GET /tasks/{id}`) removes the cost |
| CR-P3FU85E-06 | simplify | The listing and `stat` bodies of `workdir.py` copy those of `results.py` (the entries comprehension with `_iso`, the `ResultStat` dict, the `model_dump_json` response with `HEADERS`). The raw route was factored into `raw_response`; these two were not. | open: for the batch `code-simplifier` |
| SEC-P3FU85E-01 | minor | `test_req13_workdir_foreign_hard_link_refused` does not create a hard link: it marks the inode of a regular file written into the work directory, so it tests the owner check on a plain foreign file. The code path is the same today (`fstat` on the opened descriptor), so nothing is exploitable now; a later change that treats `st_nlink > 1` or a staged input differently would not be caught. | open: FU-P3-98 |
| SEC-P3FU85E-02 | minor | The link refusals are tested for a link at the top level (`x -> .command.env`) and for an absolute link to another task's `.command.run`. Not tested: a relative link from a subfolder to the task's own job file (`qc/y -> ../.command.env`), and a link into another task whose dot part lies deeper (`-> <other>/sub/.hidden/f`). `confine._link_target` refuses both today; a regression would leak `.command.env` or `.command.run` past the redaction of the Job files routes. | open: FU-P3-98 (a test of each) |
| CR-P3FU85E-R2-04 | simplify | The work-mode back link in `FilePreview` is a near-copy of the results back link two branches below; only the route, the root word and `task`/`attempt` differ. | open: for the batch `code-simplifier` |
| CR-P3FU85E-R2-05 | simplify | The folder page's Retry block copies `FilePreview`'s `Note` markup and the 409/503 wording of `Problem`; the 503 body "The file system does not answer. Nothing was lost; try again in a moment." is now written in four places (`FilePreview.tsx:63`, `ResultsBrowser.tsx:426`, `TaskFiles.tsx:183` and `:306`). | open: for the batch `code-simplifier` |
| CR-P3FU85E-R2-06 | minor | The folder page's 409/503 note has `role="alert"`; board `LiteWorkdir` state E draws `role="note"` (`LiteWorkdir.dc.html:142`), and `FilePreview`'s `Problem` uses `role="note"` for the same states. The two pages announce one state in two ways. The worker's report said `alert` "matches state E"; it does not. | open: FU-P3-98 (one role, in the board and both pages) |
| CR-P3FU85E-R2-07 | minor | The 409/503 mapping with Retry also applies to the results folder page, but only the `workdir` route is tested. The back-link test covers a file at the root only; a file in a subfolder (label = folder name, `path` = folder) is untested. | open: FU-P3-98 |

## For the Progress page

- **Built:** the four `workdir` routes with the dot-name and link rules, the two pages on the shared components, Browse work directory in the task sheet, the boards.
- **Fixed after review:** the way back from a work-directory file (CR-P3FU85E-01) and the 409/503 states with Retry (CR-P3FU85E-03).
- **Open, minor:** FU-P3-98 (the table above); three simplifications for the batch `code-simplifier`.
- **Assumed:** the card heading keeps the counts ([inbox #132](../inbox.md#132-assumed-the-work-directory-card-heading-keeps-the-counts-fu-p3-85e)).
- **Not done / not run:** a real Nextflow work directory on a cluster; Playwright on the work-directory pages; the Playwright smoke on the explorer, still open from FU-P3-85d.
