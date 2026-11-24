# What Spectio shows of a run's outputs, and how it works with a central UI (2026-11-24)

Thomas asked (2026-11-24): a catalogue of what Spectio can show of a run's outputs today, and how it will work once the UI runs centrally on Kubernetes, with a runner per user on the login node (inbox #162), notably for imaging files.

Method: a read-only inventory of the code and the specs on `autopilot/integration` at `b577f627`. Line numbers refer to that commit.

## 1. What is shown today

Detection is by file name in the browser (`web/src/runs/preview.ts:27-52`). The server checks what it serves: magic bytes for images and TIFF, and a NUL test for text. Only the run's results directory and a Nextflow attempt's work directory are reachable.

| Output | Viewer | Limits | Notes |
|---|---|---|---|
| Text and logs (`.txt .log .out .err .md .yaml .nf .smk .py`…) | text view, level tints for logs (`FilePreview.tsx:127,636`) | 64 KiB tail by default, ranges up to 1 MiB (`files/confine.py:37-38`) | `.sam .vcf .fq` read as text too (`preview.ts:28`) |
| CSV, TSV | table (`FilePreview.tsx:283`) | 500 rows, 50 columns, 1,000-character cells (`preview.ts:61-70`) | sortable and filterable explorer |
| JSON | tree (`FilePreview.tsx:231`) | 1 MiB read, depth 64 (`preview.ts:61-67`) | |
| HTML reports (MultiQC…) | sandboxed report viewer (`ReportViewer.tsx:140-146`) | 1 GiB | MultiQC found first (`files/results.py:56-63`); not opened from a work directory |
| PNG, JPEG, GIF, WebP, SVG | image (`FilePreview.tsx:355`) | 20 MiB, SVG 5 MiB, 50 megapixels (`api/results.py:67-68`, `files/images.py:26`) | served inline only to `<img>` |
| TIFF | flat canvas, or WebGL through Viv on a desktop (`FilePreview.tsx:412,625`) | whole file up to 1 GiB, else ranges of 8 MiB; tiles up to 4,096 px, 20 levels (`imaging/walk.ts:8-21`) | |
| OME-TIFF | WebGL viewer (Viv, deck.gl), flat fallback (`FilePreview.tsx:525-544`) | OME-XML 4 MiB; 2,000 requests and 256 MiB per view, 3 in flight (`imaging/client.ts:8-10`) | one WebGL viewer at a time (`imaging/viv.ts:119-137`) |
| OME-Zarr | WebGL viewer, flat on a phone (`FilePreview.tsx:548-571`) | one key per request, 16 MiB per chunk, 32 levels; **Zarr v2 only** (`imaging/zarr.ts:17-21,142-147`) | a symlinked OME-Zarr gets link states, no viewer (`FilePreview.tsx:576-588`) |
| PDF | no: download (`FilePreview.tsx:601-602`) | 1 GiB | |
| BAM, CRAM, VCF.gz, FASTQ.gz, Parquet, HDF5, archives | no: download (`FilePreview.tsx:590-592`) | 1 GiB (`api/results.py:66`) | |
| Folders | results browser (`ResultsBrowser.tsx:64-137`) | 1,000 entries per listing (`files/results.py:55`) | report search: 4 levels, 10,000 entries, 5 s |

## 2. How the bytes travel today

- **The server reads the run directory itself**, with POSIX calls on its own file system (`files/confine.py:42-43`). There is no runner hop, HTTP fetch or object store anywhere in `files/`.
- **Confined reads:** each directory is opened without following symlinks from the run's root, the owner must be the server's user, and `.spectio` and `.snakemake` are never served (`files/confine.py:6-23,104-118,139-177`).
- **Whole-file streaming** in chunks of up to 1 MiB, each chunk checked against the file's identity (`api/results.py:263-289,450-479`). Range requests exist only on the imaging routes (`?as=tiff`, `?as=zarr`): one closed range, up to 8 MiB (`api/results.py:311-321,412-419`).
- **Bounded:** a pool of 4 workers with a 5 s timeout (`files/pool.py:28-30`), and 3 imaging slots per server; with none free, the answer is 503 (`api/results.py:72,324-339`). Answers are `no-store`: nothing is cached between zooms.

This works because, in 0.0.1, the server runs on the login node under the user's own account and sees the shared file system ([architecture §7.2](../specs/architecture-plugins-and-packaging.md)).

## 3. What changes with a central UI and a runner per user

A central server on Kubernetes cannot rely on reading the runs root itself:
- the pods may not mount the cluster's file systems **[to be validated with EMBL IT]** (the shared file system question is open, `architecture-plugins-and-packaging.md:511`);
- even if they do, the server runs under one service account, while the files belong to each user; today's owner check (`confine.py`) refuses them, and widening it would give the service read access to every user's data;
- without a mount, every results route answers `409 run-dir-unreachable` (`files/taskfiles.py:94-96`).

What the specs already say: the runner channel carries "commands, heartbeats, file streaming" (`api-and-data-model.md:123`); content is "streamed through the runner or presigned URL" (`api-and-data-model.md:126`); "the server never connects to a runner", so the runner opens the channel (`admin-and-operations.md:155`); a full log "stays on the runner and is fetched with range requests" (`admin-and-operations.md:173`); presigned URLs "only cover a single object, so they are unsuitable for a Zarr" (`synthesis.md:301`). The protocol itself is open (inbox #12).

### Proposal

1. **Reads go through the user's runner (default).** The browser keeps today's routes (`/results/…`, `?as=zarr` with ranges). Only the server's file source changes: instead of `openat`, it asks the run's runner over the runner's own channel. The runner reads with the user's permissions, applies the same confinement (`confine.py` moves into the shared library), and streams the bytes back. Nothing new is opened on the login node, and the data never needs to be copied.
2. **A cache on the server for imaging.** Each chunk or tile is keyed by run, path, size and modification time. A zoomed or reopened view then costs no new round trip to the login node. The imaging slots become per runner rather than per server, so one user's large view does not block another's.
3. **Imaging formats:** Zarr v3 with sharding and consolidated metadata (the layout of OME-NGFF 0.5 **[to be validated]**), so that large pyramids need fewer requests. See #246 (OME-NGFF).
4. **Publishing to object storage (opt-in).** At the end of a run, chosen outputs (an OME-Zarr, a report) are copied to S3. The server reads them through a small read-only proxy, scoped to the run's prefix. This is also the hand-off to depictio, which already keeps its data in S3 ([depictio-ecosystem-reuse](../specs/depictio-ecosystem-reuse.md)). It is worth it for large imaging datasets that many people open, but it is not the default.
5. **When a runner is offline:** viewers on its files are "on hold" (`ui-spec.md:588`); published outputs (point 4) stay readable.

### Gaps in today's viewers, independent of the deployment

- PDF: download only.
- Genomics: BAM, CRAM, VCF and BED would need IGV.js with indexed range reads.
- Parquet and Arrow tables.
- Zarr v3, and OME-Zarr published as a symlink.
- No cache, so every zoom reads again.

## 4. Next steps

- An issue that tracks points 1–5 and the gaps, linked to #246 and #355.
- The runner protocol (inbox #12) must carry ranged reads from the start: it is the path for every viewer in a central deployment.
