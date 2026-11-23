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
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator on the R0 design, in parallel | yes | **changes 0/2/7** | **changes 0/4/11** |

The R1 findings are all applied below; the design in the specs is the one after R1.

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary, the page's CSP, supply chain, untrusted bytes; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code and the packages read for the design. No board was drawn or rendered: the boards are FU-P3-102b. **This review is not independent.** R1 below is the independent round.

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

## Round R1 (independent)

`security-reviewer` and `ux-reviewer` read the R0 design (commit `4642477c`, rebased as `f5ea0257`) on 2026-11-09, independent and in parallel; the coordinator relayed their findings in summary, so the texts below are summaries. Every major and minor was applied to the owning spec in the commit after `f5ea0257`; where a finding offered two ways, the simpler one was taken, as each line says. The same commit rebased the step on PR #195, which records Thomas's "Mets les viewer mtn" in inbox #134 and the 10 to 15 minute cycle in autopilot §13 item 5, so R0's two open questions on them are closed.

### `security-reviewer`

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=2  minors=7
```

| ID | Sev. | Finding (summary) | Applied, where |
|---|---|---|---|
| SEC-PRE-FU102-R1-01 | major | The TIFF caps had no enforcement point: Viv was handed a URL and fetches through geotiff `fromUrl` with `cacheSize: Infinity`; a self-pointing IFD loops on cached blocks; Viv may follow OME-XML `TiffData` file names. | applied: the page's own geotiff client (`fromCustomClient`, pinned URL, request and byte budget, bounded cache), its own IFD walk with a seen-offset set, the opened images handed to Viv (entry point **[to be validated]**), multi-file `TiffData` refused, fixtures `../other.tif` and `https://` (api §5.3.1 first bullet; req. 19 "Where the caps are enforced", Tests; FU-P3-102d, -102e) |
| SEC-PRE-FU102-R1-02 | major | Every range read 1 MiB from byte 0 first (`open_raw`), about 16 times a 64 KiB range. | applied: `open_raw` told how many bytes to read first (4 for TIFF, none for a Zarr range), the range read from its own start, at most range + 4 bytes, a read-counter test (api §5.3.1 "What the server reads", Tests; FU-P3-102a) |
| SEC-PRE-FU102-R1-03 | minor | The pool budget was client-side only. | applied: a server semaphore of 3 imaging reads, `503` at once, a test (api §5.3.1 step 9, Caps; FU-P3-102b) |
| SEC-PRE-FU102-R1-04 | minor | `bytes=<first>-` against the 8 MiB cap. | applied, the simpler option: open-ended ranges refused; a test (api §5.3.1 step 8; FU-P3-102a) |
| SEC-PRE-FU102-R1-05 | minor | The 1 MiB JSON cap named three keys; the server also allowed `.zgroup` and `.zmetadata`. | applied: the cap and depth pre-scan on every metadata key; `.zmetadata` dropped, since Viv's loader does not ask it and zarrita reads it only through `withConsolidated` (api §5.3.1 step 5; req. 19 Malicious Zarr) |
| SEC-PRE-FU102-R1-06 | minor | Prototype pollution from metadata on the main thread; the XML parser unnamed. | applied: Viv's `DOMParser` named (`xmldom` a development dependency only), `__proto__` and `constructor` fixtures with an `Object.prototype` check, `npm audit --omit=dev` gate (req. 19; FU-P3-102e, -102g) |
| SEC-PRE-FU102-R1-07 | minor | `worker-src 'self'` covers service workers; the safety rests on raw routes never answering a script type. | applied: the invariant stated, step 0 refuses script and worker destinations on every raw route, no `Service-Worker-Allowed`, a test (api §5.3.1 step 0, "Never script"; req. 19; FU-P3-102b) |
| SEC-PRE-FU102-R1-08 | minor | `'wasm-unsafe-eval'` widens the CSP of every screen. | applied: an accepted risk in inbox #135 choice 3; the stop rule widened to any `'unsafe-eval'` or `blob:` need, and a browser without `'wasm-unsafe-eval'`, reserved to Thomas; a header test with no `'unsafe-eval'` (req. 19; FU-P3-102b) |
| SEC-PRE-FU102-R1-09 | minor | Decide now on middle-part links; `lzw-tiff-decoder` has no LICENSE and no release since 2021. | applied: middle-part links not followed in 0.0.1, any relaxation limited to the four v2 names below `.ome.zarr` with its own review (api §5.3.1 Confinement); LZW through geotiff's JavaScript decoder, capped, registered after Viv loads, `lzw-tiff-decoder` in the third-party notices (req. 19) |

### `ux-reviewer`

```text
UX-REVIEW  verdict=changes  blockers=0  majors=4  minors=11
```

| ID | Sev. | Finding (summary) | Applied, where |
|---|---|---|---|
| UX-PRE-FU102-R1-01 | major | The 1 GiB cap hit `as=tiff`, and registered OME-TIFFs are often several GiB; no state mapped `413`. | applied, the simpler option: the cap lifted for `as=tiff` range reads (each capped at 8 MiB); `413` in the too-large state (api §5.3.1 step 1; ui-spec note, States; FU-P3-102a) |
| UX-PRE-FU102-R1-02 | major | A Zarr v2 store published as a link was a dead end between results and work directory. | applied: a final state "Spectio cannot open this OME-Zarr here (published as a link, Zarr v2)." with Copy path, and the v3 link state (ui-spec note, States; api §5.3.1 Confinement) |
| UX-PRE-FU102-R1-03 | major | Mid-view problems replaced the viewer; the read budget may be reached quickly. | applied: drawn tiles kept, a status line above the canvas with Reload (view kept) and Retry; the 2,000-read limit measured on an mcmicro-size fixture, **[to be validated]** (ui-spec note; FU-P3-102e) |
| UX-PRE-FU102-R1-04 | major | 40 to 60 channels made about 160 tab stops. | applied: "n of m on", ranges and Reset only on rows that are on, a filter above 12 channels, its own scroll region, a 40-channel board (ui-spec note; FU-P3-102c, -102f) |
| UX-PRE-FU102-R1-05 | minor | Phone: the largest level at most 2,048 px, and the shown size. | applied (ui-spec note, Phone) |
| UX-PRE-FU102-R1-06 | minor | A flat OME-Zarr view without Viv needs an owner. | applied: zarrita alone, FU-P3-102g (ui-spec note, flat view) |
| UX-PRE-FU102-R1-07 | minor | Contrast domain, step, clamp, persistence, 1-based `aria-valuetext`. | applied (ui-spec note, Contrast and Planes) |
| UX-PRE-FU102-R1-08 | minor | Per-row names with the channel's number; long names wrap. | applied |
| UX-PRE-FU102-R1-09 | minor | A visible key line, `=` accepted, the zoom as text, a black backdrop, the focus ring outside the canvas. | applied |
| UX-PRE-FU102-R1-10 | minor | Empty file, multi-page TIFF, RGB OME-TIFF. | applied (Kinds, States, the RGB bullet) |
| UX-PRE-FU102-R1-11 | minor | The view in the URL. | applied: `&viewer=`, `&z=`, `&t=`, `&ch=` with a history replace, kept by Copy link and Reload (FU-P3-102f) |
| UX-PRE-FU102-R1-12 | minor | `FilePreview.tsx` sends folders to the folder page; the row's sort place; the folder page's link. | applied: the `*.ome.zarr` exception (`:480`, `:481`), the row stays with the folders, Open as an image on the folder page (ui-spec note, Kinds; FU-P3-102d) |
| UX-PRE-FU102-R1-13 | minor | Wording of the budget, compression and work-directory lines. | applied (ui-spec note, States and Reading) |
| UX-PRE-FU102-R1-14 | minor | `role="status"`/`alert` against the file page's `role="note"`, open in FU-P3-98. | applied: the viewer follows FU-P3-98's choice and adds no third role (ui-spec note, Keyboard) |
| UX-PRE-FU102-R1-15 | minor | The boards miss many states and variants. | applied: the Boards bullet lists them (FU-P3-102c) |

**Disagreements with R0.** SEC-PRE-FU102-02 bounded the cache by a budget that Viv's own fetches would not have passed through (R1-01). SEC-PRE-FU102-05 capped the pool from the page only (R1-03). R0 missed the read amplification of `open_raw` (R1-02), the service-worker reach of `worker-src 'self'` (R1-07) and the open-ended range (R1-04). UX-PRE-FU102-08 replaced the view at the budget, which R1-03 keeps; R0 had no case for many channels (R1-04), large OME-TIFFs (R1-01) or the link dead end (R1-02).

### What moved in the build plan

Seven tasks instead of five, each one module and at most about 300 lines (autopilot §13 item 5): the server splits into the reads (-102a: modes, ranges, `open_raw`, links) and the slots, script refusal and CSP (-102b); the boards become -102c; the TIFF reader and flat view -102d gain the page's client, the IFD walk and the LZW decoder; the Viv viewer -102e gains the status line, the budget measure and the supply-chain gates; the channel panel and the view in the URL are -102f; the OME-Zarr viewer is -102g ([inbox #135](../inbox.md#135-assumed-tiff-ome-tiff-and-ome-zarr-viewers-in-001-fu-p3-102)).

## Open after R1

- Every **[to be validated]** of api §5.3.1, req. 19 and the decision log entry, in particular deck.gl and luma.gl under the CSP with no `'unsafe-eval'` (the stop rule of req. 19), the Viv entry point for an opened GeoTIFF, and the 2,000-read budget.
- Inbox #135 choice 5: a Zarr v2 store published as a link cannot be opened in 0.0.1.
