# Pre-review · FU-P3-102, TIFF, OME-TIFF and OME-Zarr viewers (design only)

Step `P3-fu102-spec` on `autopilot/P3-fu102-spec`, base `2195f14a`, 2026-11-09. The step writes the design of FU-P3-102 ([decision log](../../decisions/log.md#2026-11-09-tiff-ome-tiff-and-ome-zarr-viewers-in-001-fu-p3-102-assumed), [inbox #135](../inbox.md#135-assumed-tiff-ome-tiff-and-ome-zarr-viewers-in-001-fu-p3-102)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

There is no `CODE` line in this record: the step changes no code, so there is no code to review.

Reviewed sections:
- [api §5.3.1](../../specs/api-and-data-model.md#531-imaging-viewers-fu-p3-102), new;
- [ui-spec §4.4.1](../../specs/ui-spec.md#441-file-explorer-and-preview), the note of 2026-11-09 on imaging, and one line of its Later list;
- [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 19, new;
- [MVP 0.0.1](../../specs/mvp-0.0.1.md), one row.

## Rounds

| Round | Who | Independent | security | UX |
|---|---|---|---|---|
| R0 | the design worker, on the two agents' checklists | **no** | changes 0/3/8 | changes 0/1/7 |
| R1 | `security-reviewer` and `ux-reviewer` | yes | not run yet | not run yet |

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary, the page's CSP, supply chain, untrusted bytes; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code and the packages read for the design. No board was drawn or rendered: the boards are FU-P3-102b. **This review is not independent.** R1 is the independent round and runs before FU-P3-102a.

Code read for the design: `spectio_server/static.py` (`CSP`, `HEADERS`, `TYPES`), `api/results.py` (`raw_response`, `_image_type`, `REPORT_CSP`), `api/taskfiles.py` (`_byte_range`, `HEADERS`, `TEXT_CSP`), `files/results.py` (`check_rel`, `ENGINE_DIRS`, `open_raw`, `read_chunk`, `CHUNK`), `files/confine.py` (`safe_rel`), `files/pool.py` (`WORKERS = 4`, `BACKLOG = 16`, refusal when full), `web/src/runs/FilePreview.tsx`, `web/src/runs/preview.ts`, `web/package.json`. Third-party sources read from the npm tarballs (`npm pack`, 2026-11-09): geotiff 2.1.3 `dist-module/source/remote.js`, `source/blockedsource.js`, `pool.js`, `worker/decoder.js`, `compression/index.js`, `compression/deflate.js`; `@vivjs/loaders` 0.23.0 `dist/index.mjs`; `@vivjs/constants` 0.23.0; `@zarrita/storage` 0.2.0 `dist/src/fetch.js`; zarrita 0.5.4 `dist/src/codecs.js`; numcodecs 0.3.2 `dist/`; `lzw-tiff-decoder` 0.1.1; the `LICENSE` files of `@hms-dbmi/viv`, `@deck.gl/core` and `@luma.gl/core`. GitHub was not reachable from the session (`403` from the proxy), so no repository page was read.

### Security checklist (`security-reviewer`)

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=3  minors=8
```

Every finding was applied to the design before the commit, except where the table says otherwise. The verdict is the verdict on the first draft.

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| SEC-PRE-FU102-01 | major | geotiff.js's default decoder pool starts its worker from a `blob:` URL (`worker/decoder.js`); allowing `blob:` in `worker-src` would let any script of the origin start a worker from bytes it built. | yes: our own worker file in `/assets/`, passed as the pool's `createWorker`; `worker-src 'self'`, no `blob:` anywhere (req. 19) |
| SEC-PRE-FU102-02 | major | geotiff's Deflate decoder is `pako.inflate` with no output cap (`compression/deflate.js`): an 8 MiB tile can inflate about a thousand times, and Viv opens geotiff with `cacheSize: Infinity`. | yes: a capped Deflate decoder of our own, every decoder's output capped at its declared size, the per-view budget of 256 MiB and 2,000 requests bounding the cache (req. 19) |
| SEC-PRE-FU102-03 | major | Viv's `loadOmeZarr` builds a `FetchStore` from a URL, and OME-Zarr metadata holds `path` values; a crafted `.zattrs` could make the page ask keys outside the folder, or an absolute URL. | yes: our own store given to `loadOmeZarrFromStore`, every key built below the folder and checked against the key grammar on both sides; no URL from a file (api §5.3.1; req. 19) |
| SEC-PRE-FU102-04 | minor | Serving a range without `Content-Disposition` could let a navigation render the bytes. | yes: only with `Sec-Fetch-Dest: empty`, always `application/octet-stream` with `nosniff` and the CSP `sandbox`; a navigation gets the attachment (step 6) |
| SEC-PRE-FU102-05 | minor | A viewer firing many requests can fill the file pool (4 threads, 16 queued) and stall the other screens. | yes: 3 in flight per view, one thread left; a `503` retried once (api §5.3.1, Caps) |
| SEC-PRE-FU102-06 | minor | A Zarr v2 store needs dot names, which the work-directory routes refuse to keep `.command.env` out. | yes: the dot rule kept, v2 refused there with a line to the results (inbox #135 choice 5) |
| SEC-PRE-FU102-07 | minor | `'wasm-unsafe-eval'` widens `script-src`. | yes, recorded: it allows WebAssembly compilation only, no JavaScript `eval`; needed by Viv's LZW decoder and numcodecs; the alternative is choice 3 (b) |
| SEC-PRE-FU102-08 | minor | geotiff's pool has no error path: a decoder that throws never answers. | yes: our worker answers errors, the page ends a decode after 10 s |
| SEC-PRE-FU102-09 | minor | Compression codes that bring their own decoders (LERC with `zstd` init, WebImage through the browser's image decoder) widen the parsing surface. | yes: an allow-list checked before decode |
| SEC-PRE-FU102-10 | minor | A file replaced between two ranges gives mixed tiles. | recorded: one answer is checked by identity; across answers, Later (`ETag`, `If-Match`); the page says "read at" |
| SEC-PRE-FU102-11 | minor | New npm packages are supply chain: deck.gl 9.4.1 was published 12 days before the design. | yes: exact pins, licences from the tarballs, `npm ls --all` and install scripts checked in FU-P3-102d, 9.4.0 named as the fallback |

Checked and unchanged: no new route, listener or port (req. 1); the session and cross-site checks of req. 7 on every read; the confined walk and the 1 GiB cap of req. 13; nothing from a file becomes HTML (req. 14); the server never decodes an image.

### UX checklist (`ux-reviewer`)

```text
UX-REVIEW  verdict=changes  blockers=0  majors=1  minors=7
```

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| UX-PRE-FU102-01 | major | No board shows the viewer, its states or the phone; the board conventions need boards before screen code. | yes: FU-P3-102b, before -102c (ui-spec §4.4.1 note, Boards) |
| UX-PRE-FU102-02 | minor | A canvas is not reachable by keyboard and has no text. | yes: a focusable named region, keys with a visible button each, the facts line as its text |
| UX-PRE-FU102-03 | minor | A 7th channel switched on with no word. | yes: the polite line and it stays off |
| UX-PRE-FU102-04 | minor | Contrast values shown only while dragging would be hover-only. | yes: the numbers as text beside each range |
| UX-PRE-FU102-05 | minor | An OME-Zarr row in the explorer opens a folder, so the viewer is not found. | yes: the row opens the preview; Browse folder on the page |
| UX-PRE-FU102-06 | minor | "Too large" with no reason. | yes: the reason names the cap |
| UX-PRE-FU102-07 | minor | A browser without WebGL 2 gets nothing. | yes: the flat view of the phone, with the line |
| UX-PRE-FU102-08 | minor | The read budget ends a view silently. | yes: the state names it, with Reload |

## Open for R1 and Thomas

- Thomas's move of FU-P3-102 into 0.0.1 reached the design through the session, not in #134's text, which still says "after 0.0.1"; #134 now carries a "Changed" line.
- The plan has five tasks, not four: the flat TIFF view and the Viv viewer do not fit one task of about 300 lines.
- Every **[to be validated]** of req. 19 and the decision log entry, in particular deck.gl and luma.gl under the CSP with no `'unsafe-eval'` (FU-P3-102d stops if not).
