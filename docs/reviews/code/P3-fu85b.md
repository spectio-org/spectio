# Code review · FU-P3-85b: image mode of the results raw route, and its file identity check

`review-code` on `autopilot/P3-fu85b`, base `0fc2be73`, head `d0112957` (one commit), 2026-11-09. The step is the second task of the build plan of [inbox #127](../inbox.md#127-assumed-file-explorer-and-preview-fu-p3-85): the server side of the image preview for the results directory. The behaviour is owned by [api §5.3](../../specs/api-and-data-model.md#53-run-files-explorer-and-preview) (the table of image-mode steps and "Shared changes") and [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 14 (note of 2026-11-08). Progress: [P3 · M9, FU-P3-85b](../../progress/W5/P3-M9.md#fu-p3-85b-server-image-mode-of-the-results-raw-route-and-its-file-identity-check). Format: [`README.md`](../README.md).

Outside `docs/`: 6 files, +504 −18 over the base (`git diff --shortstat 0fc2be73..HEAD -- . ':!docs'`), all under `packages/spectio-server` plus the wheel contents list. One file is new under `src/`, `files/images.py`, and is added to `tests/packaging/contents/spectio_server.wheel.txt`.

## What the step does

- **Route** (`api/results.py`). `GET /runs/{id}/results/raw/{path}?as=image` runs api §5.3's table in its order: the raw route's checks; `?download=true`; `as` with another value is `422 validation-failed` on `as`; a name that is not an image's is `422 file-not-allowed`; without `Sec-Fetch-Dest: image`, the attachment as before; with it, `413 file-too-large` over 20 MiB (an SVG over 5 MiB), then `images.check`, then the image with its exact type, the shared headers, the CSP `sandbox; default-src 'none'` and no `Content-Disposition`. Steps 2 to 5 are in `_image_type`. Every raw answer carries `Vary: Sec-Fetch-Dest`.
- **Image check** (`files/images.py`, new, pure). `MEDIA` maps a suffix to its type. `check(media, head)` matches the signature and enforces `MAX_PIXELS = 50_000_000`, reading the size from PNG `IHDR`, GIF bytes 6 to 9, WebP `VP8 `, `VP8L` or `VP8X`, and the first `SOFn` of a JPEG found by walking the segments. A header not found in the first chunk is refused. An SVG has no signature check.
- **One opening, then identity** (`files/results.py`). `open_raw(where, rel, cap)` replaces `file_size` and returns `Raw(size, ident=(st_dev, st_ino), first)`; `first` is at most `CHUNK` bytes and is not read for a file over the cap. `read_chunk(..., ident)` raises `Replaced(NotAllowed)` when the file it opened has another identity; the stream logs it and re-raises, so the response is aborted as a short file is. The first chunk is sent as the first part of the body for every raw answer, image or not.
- **Tests** (`tests/api/test_results.py`). One per table row: `test_req14_image_{raw_checks_first,download_is_attachment,as_other_value,name_not_image,without_fetch_dest,size_caps,signature_mismatch,too_many_pixels,served}`; `test_req14_image_vary_on_every_raw_answer`; `test_req14_image_first_chunk_is_the_body`; `test_req13_raw_file_replaced_mid_download`. The OpenAPI snapshot gains the `as` query parameter.

## Review rounds

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `d0112957` | **approve** (0 blockers, 0 majors, 1 minor) | **approve** (0 blockers, 0 majors, 3 minors) |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | |

Both reviewers approved with no fix required, so the findings are not fixed in this task. The reports were relayed by the worker; the three probes below were re-run by `doc-writer`.

```text
CODE  step=P3-fu85b  review=approve b/M/m=0/0/1  security=approve b/M/m=0/0/3  rounds=1  simplify=skipped -0/+0  tests=pass
```

**Test command and result** (re-run by `doc-writer` at `d0112957`):

```bash
uv run --locked pytest packages/spectio-server/tests/api/test_results.py \
  packages/spectio-server/tests/api/test_openapi.py -q
uv run --locked ruff check packages/spectio-server
uv run --locked mypy packages/spectio-server
```

```text
47 passed in 9.22s
All checks passed!
Success: no issues found in 100 source files
```

**The probes of the size check, run by `doc-writer` on the head** (`spectio_server.files.images.check`; `None` means the file is accepted):

```text
gif   1x1 screen, first descriptor 60000x60000   None
png   IHDR 0 x 0                                 None
jpeg  SOF0 height 0, width 60000                 None
png   IHDR 60000 x 60000                         image too large to decode: 60000 x 60000
```

The first three are SEC-P3FU85B-01 and -02 below; the fourth is the case the spec names and it is refused.

**Tests that did not fail first.** `test_req14_image_raw_checks_first` passed on the base, because step 1 is the existing raw route; it guards the order. Before the implementation the other new tests gave `11 failed, 31 passed` (relayed by the worker).

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU85B-01 | minor | The problem answers of steps 6 and 7 (`413 file-too-large` over 20 MiB or 5 MiB, `422 file-not-allowed` from `images.check`) exist only for a request with `Sec-Fetch-Dest: image`, so they depend on that header, but carry no `Vary: Sec-Fetch-Dest`. The spec asks for `Vary` on the two `200` answers only, and `413` and `422` are not heuristically cacheable, so nothing breaks today. Problem answers also carry no `no-store` yet. | open: follow-up FU-P3-93, with SEC-P3FU85A-01 |
| SEC-P3FU85B-01 | minor | The 50-megapixel check on a GIF reads only the logical screen size (bytes 6 to 9). A GIF can declare a 1 x 1 screen and then a first image descriptor of 60000 x 60000; some decoders grow the canvas to fit the first frame (Chromium change 813943003 extends the screen to offset plus frame size; WebKit bug 249866 covers the same case). Whether current decoders still do is **[to be validated]**. The code matches the spec text, so this is a gap in the spec. Impact is limited to the tab of the user who opens the run's own output. | open: [inbox #129](../inbox.md#129-assumed-the-image-size-check-gif-first-frame-zero-sizes-and-the-file-identity-fu-p3-85b), assumed |
| SEC-P3FU85B-02 | minor | A width or height of 0 passes, because `0 * n <= MAX_PIXELS`. PNG forbids 0. A JPEG with height 0 takes its real height from a later DNL marker, which a first-chunk check cannot see (libjpeg rejects DNL with `JERR_EMPTY_IMAGE` **[to be validated]**). A GIF with a 0 x 0 screen takes its size from the first frame (libwebp `gif2webp` does; browsers **[to be validated]**). Either way the header has not given a size that can be trusted. | open: inbox #129, assumed |
| SEC-P3FU85B-03 | minor | The identity is `(st_dev, st_ino)` and `read_chunk` opens the file again by path for every chunk, so no descriptor stays open between chunks. After an unlink the inode number may be reused (ext4 and XFS reuse freed inodes readily **[to be validated]**), and a delete-and-recreate at the same path can pass the check. A rewrite in place keeps the inode and is not seen. Impact is low: the checked header bytes are sent from memory (`raw.first`), so PNG, JPEG and WebP dimensions cannot change afterwards; a GIF's later frames and the rest of the bytes can come from another file. This is what api §5.3 ("Shared changes") specifies, so it is a hardening point, not a defect. | open: inbox #129, assumed |

## For the Progress page

- **Built:** `?as=image` in the order of the table, the image check, `open_raw` with the first chunk sent as the body's start, the identity check on every later chunk, `Vary: Sec-Fetch-Dest` on every raw answer.
- **Open, minor:** CR-P3FU85B-01 (FU-P3-93); SEC-P3FU85B-01 to -03 ([inbox #129](../inbox.md#129-assumed-the-image-size-check-gif-first-frame-zero-sizes-and-the-file-identity-fu-p3-85b), assumed: as built).
- **Assumed:** 50 megapixels is 50,000,000 pixels; `as` is matched exactly (`IMAGE` and `image ` are `422`); the first chunk is read before the headers for every raw answer, so a read error on it is a problem answer (`404` or `503`), not an aborted body; tests set `CHUNK` to at least 24 bytes so a PNG `IHDR` fits (1 MiB in production).
- **Not done:** the Playwright check of an SVG in `<img>` and of a navigation that downloads (FU-P3-85c's list, inbox #127); the work-directory routes (FU-P3-85e); any UI. Browser decode limits and Safari's `Sec-Fetch-Dest` support stay **[to be validated]**. No new follow-up number was used: FU-P3-94 is still the next free one.
