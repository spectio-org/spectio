# Code review · FU-P3-85a: results stat and text reads for the file preview

`review-code` on `autopilot/P3-fu85a`, base `947baed7`, head `47734a57` (one commit), 2026-11-09. The step is the first task of the build plan of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85): the server side of the preview for the results directory. The behaviour is owned by [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview) and [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 13 and 14 (notes of 2026-11-08). Progress: [P3 · M9, FU-P3-85a](../../progress/W5/P3-M9.md#fu-p3-85a-server-side-of-the-file-explorer-and-preview-results-stat-and-text). Format: [`README.md`](../README.md).

Outside `docs/`: 12 files, +587 −52 over the base (`git diff --shortstat 947baed7..HEAD -- . ':!docs'`), all under `packages/spectio-server` (nine under `src/spectio_server`, the OpenAPI snapshot and four test files). No file was added under `src/`, so the wheel contents are as they were.

## What the step does

- **Routes** (`api/results.py`). `GET /runs/{id}/results/stat/{path}` answers `ResultStat` (`root`, `path`, `name`, `type`, `size`, `mtime`), the listing's entry for one path, found by `confine.entry_confined`, which calls the listing's own `_entry`. `GET /runs/{id}/results/text/{path}` reads a results file as text (`?tail=` or one `Range`). Both check the path with `check_rel` and read in the file pool. A listing would hide an entry, so `stat` answers `404 not-found`; an empty path is `422 file-not-allowed`.
- **One reader** (`files/taskfiles.py` `read_text`). The Job files read and the results text read both go through it. The old range and tail code and `_cut` are folded into `_served`; `.command.run` is hidden first, then cut. A range that ends inside the file ends on its last whole UTF-8 sequence (`_whole_utf8`), and `Content-Range` gives that end. A 1-byte range on a lead byte is not cut, so a range is never empty. An empty file is `200` with an empty body, with a `Range` too; a range past the end of a file that is not empty is still `422`. `api/taskfiles.py` `text_response` builds the `200`, `206` and `422` answers for both routes and adds the CSP `sandbox; default-src 'none'`.
- **Headers.** `Cross-Origin-Resource-Policy: same-origin` is in the shared `HEADERS` of `api/taskfiles.py`.
- **`strip_escapes`** (`files/redact.py`). An OSC is removed whole only when its terminator comes within `OSC_MAX = 4096` characters; otherwise its introducer alone goes. The OSC body is possessive and stops at the next ESC or `0x9d`, so the cost is linear.
- **Tests.** 12 new tests failed before the implementation (`12 failed, 84 passed`, relayed by the worker). The OpenAPI snapshot gains the two routes and `ResultStat`; `test_openapi.py` covers the `stat` route.

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `47734a57` | **approve** (0 blockers, 0 majors, 1 minor, 2 simplify) | **approve** (0 blockers, 0 majors, 3 minors) |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | |

The reports were relayed in summary, so the texts below are summaries. Both reviewers approved with no fix required, so the findings are not fixed in this task.

```text
CODE  step=P3-fu85a  review=approve b/M/m=0/0/1  security=approve b/M/m=0/0/3  rounds=1  simplify=skipped -0/+0  tests=pass
```

**Test command and result** (re-run by `doc-writer` at `47734a57`; the worker's full gate was 1160 passed, 1 skipped, vitest 330 passed, `tools/docs/check.py` 0 failures):

```bash
uv run --locked pytest packages/spectio-server/tests/api/test_results.py \
  packages/spectio-server/tests/api/test_taskfiles_api.py \
  packages/spectio-server/tests/test_taskfiles.py \
  packages/spectio-server/tests/api/test_openapi.py -q
uv run --locked ruff check packages/spectio-server
uv run --locked mypy packages/spectio-server
```

```text
101 passed in 13.00s
All checks passed!
Success: no issues found in 99 source files
```

**The two `strip_escapes` probes, run by `doc-writer` on the head:**

```text
strip_escapes('line1\nline2 \x9d hidden\nline3\nline4\n') == 'line1\nline2  hidden\nline3\nline4\n'
strip_escapes('a\x1b]0;t\nsecret\nmore\x07b') == 'ab'
```

The first is the case SEC-PRE-FU85-R1-11 named; it now keeps the text. The second is SEC-P3FU85A-02 below.

**Tests that did not fail first.** `test_req2_results_stat_text_need_session` (`401`) and `test_req7_results_stat_text_same_site_403` pass without the routes, because the session and Fetch-Metadata checks run in middleware before routing. They guard against a regression; they never failed on the base.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85A-01 | minor | The CORP test does not cover the run logs route, one of the routes the requirement lists. | open: follow-up FU-P3-93 |
| CR-P3FU85A-02 | simplify | `ResultStat` repeats the four fields of `ResultEntry`, and `result_stat` repeats the listing's entry-to-dict mapping. | open: left to the batch `code-simplifier` |
| CR-P3FU85A-03 | simplify | `TEXT_CSP` in `api/taskfiles.py` and `ATTACHMENT_CSP` in `api/results.py` hold the same value, `"sandbox; default-src 'none'"`, in two places. | open: left to the batch `code-simplifier` |
| SEC-P3FU85A-01 | minor | Problem answers (`404`, `415`, `422`, `503`) from the file routes carry none of the shared `HEADERS`: no CORP, `nosniff` or `no-store`. [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview) says every file and listing route carries CORP, but only the success paths add it, and error details name files. | open: follow-up FU-P3-93 |
| SEC-P3FU85A-02 | minor | A terminated OSC can span newlines, so a previewed file can still hide up to 4 KiB of whole lines (probe above). It matches the letter of api §5.3 and is not a regression (before, the hidden text was unbounded), but the preview is where a person reads a file to judge it. | open: [inbox #128](../inbox.md#128-assumed-how-much-an-escape-sequence-in-a-previewed-file-may-hide-fu-p3-85a), assumed |
| SEC-P3FU85A-03 | minor | `test_req14_corp_on_every_file_route` checks only the Results listing and raw. The new routes and Job files are checked in other tests, but no test checks the run log routes (plain read and follow stream), which the spec names in the same list. A later change to `logs.py` headers would pass unseen. | open: follow-up FU-P3-93, with CR-P3FU85A-01 |

## For the Progress page

- **Built:** the two routes, the shared reader, CORP on every file route, the bounded OSC.
- **Open, minor:** CR-P3FU85A-01 and SEC-P3FU85A-03 (one test over the run log routes), SEC-P3FU85A-01 (headers on problem answers), SEC-P3FU85A-02 (inbox #128). The two simplify items go to the batch `code-simplifier`.
- **FU-P3-93 (new):** a test that every file route (run logs, plain and follow, included) carries CORP, `nosniff` and `no-store`; the same three headers on problem answers from those routes (SEC-P3FU85A-01), so error details are not sniffed or cached; and, if wanted, the start of a tail read on a whole UTF-8 sequence (the tail can still start inside one and then shows one U+FFFD; api §5.3 asks only that a range end on a whole sequence).
- **Assumed:** a `stat` of the results root (an empty path) is `422 file-not-allowed`, "not a file", as the raw route answers. `api/results.py` imports the private `_byte_range` from `api/taskfiles.py`, as it already imports `_iso`.
- **Not done:** image mode and the raw route's inode check (FU-P3-85b), the work-directory routes (FU-P3-85e), any UI (FU-P3-85c, -85d). The web client has no `ResultStat` type yet.
