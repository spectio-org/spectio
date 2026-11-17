---
icon: material/file-search-outline
---
# Browsing and previewing a run's files

!!! note "Built on the integration branch, not released yet"

    This works today from a checkout (steps FU-P3-85a to FU-P3-85e, batch [P3-B09](../progress/W5/P3-M9.md#batch-p3-b09), 2026-11-09; tables in AG Grid, the HTML report and OME-Zarr added by batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13), 2026-11-10; the OME-TIFF viewer and the breadcrumb of a file page by batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14), 2026-11-10; Blosc, LZ4 and zstd chunks of an OME-Zarr by batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15), 2026-11-11). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **It ran on a local executor only, on a `.tsv` file:** no image, PDF or HTML state was captured, no SLURM run and no real cluster work directory was opened (see [Not shown](#not-shown)).

You can look at a run's files from the run page, with no terminal. There are two places to browse, and one page to preview a file. The rules are owned by [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview); the routes by [api §5.3](../specs/api-and-data-model.md#53-run-files-explorer-and-preview); confinement and headers by [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts), requirements 13 and 14. Everything here is read-only.

## Two places to browse

| Place | Open it from | Works for |
|---|---|---|
| **Results** | the Summary, **Results and reports**, then **Browse all results** | a run Spectio launched (Snakemake: the launch directory) |
| **Work directory** | a Nextflow task's sheet, **Browse work directory**, beside **Copy work directory** | one attempt of a Nextflow task of a run Spectio launched |

- A Snakemake job's sheet has no work directory. On its **Outputs** tab, each present output has **Preview**, which opens the folder or the file.
- A run started from a terminal has neither place yet.
- If the files of an attempt were cleaned (`nextflow clean`, `cleanup = true`, a scratch purge), the sheet says "The work directory was removed" instead of the button.
- Names that start with `.` are never listed in a work directory. The job's own `.command.*` files stay in the sheet's file tabs.

## The explorer

![The results directory of a finished Nextflow run: four folders and a report, with Name, Kind, Size and Modified](../assets/shots/app-results-explorer_light.webp#only-light)
![The results directory of a finished Nextflow run: four folders and a report, with Name, Kind, Size and Modified](../assets/shots/app-results-explorer_dark.webp#only-dark)

*The results of the synthetic Nextflow run `spectio/synthetic-scenarios-1D73Q9`, launched from Spectio on a local executor. The report has a Download button; a folder's size is not counted.*

- **One folder at a time,** under the path bar. A folder's name opens it. A file's name opens its preview; an HTML report in the results opens the report viewer.
- **Kind** is a badge with an icon: Folder, Text, Table, JSON, Image, HTML report, PDF, Binary, File, Link outside. It comes from the file's name only.
- **Sort** with the **Name**, **Size** and **Modified** buttons in the header; a second press reverses. Folders stay first. On a phone, a **Sort by** select does the same.
- **Filter** with **Filter this folder**: the entries whose name contains the text, any case. With no match the page says so and offers **Clear**.
- **The address keeps the view:** `&sort=`, `&q=` and, after a preview, `&focus=` (the folder scrolls to the file you came from). You can copy the address of a filtered, sorted folder.
- **A folder of more than 1,000 entries** lists 1,000 of them, in no particular order, and says so.

The same card shows the work directory of a task, under the heading "Work directory · COMPARE (treatA_vs_ctrl) · attempt 1":

![The work directory of the COMPARE task for treatA_vs_ctrl: two tables, counts_matrix.tsv and treatA_vs_ctrl.tsv](../assets/shots/app-workdir_light.webp#only-light)
![The work directory of the COMPARE task for treatA_vs_ctrl: two tables, counts_matrix.tsv and treatA_vs_ctrl.tsv](../assets/shots/app-workdir_dark.webp#only-dark)

*Its back link, "COMPARE (treatA_vs_ctrl) · attempt 1", opens the run with that task's sheet open. The two files are the task's staged input and its output.*

- A staged input that is a copy, or a link into another task directory of the same run, reads like an output. A link that goes elsewhere reads "not followed".
- An HTML file in a work directory is never opened: it says so, and you can download it.

## The preview

![Preview of quant/counts_matrix.tsv: a table of twelve samples with total, mapped and mapped_rate, under the path, Copy path and Download](../assets/shots/app-file-preview_light.webp#only-light)
![Preview of quant/counts_matrix.tsv: a table of twelve samples with total, mapped and mapped_rate, under the path, Copy path and Download](../assets/shots/app-file-preview_dark.webp#only-dark)

*A 250-byte TSV from the same run, taken before FU-P3-101a, when the preview drew an HTML table. The heading takes focus when the page opens. The line "counts_matrix.tsv" under the header row was the table's caption, drawn in the wrong place ([FU-P3-100](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b09)); in the grid below it sits above the table. This shot and its phone twin are kept until the run can be launched again; see [Tables](#tables) for the grid.*

The page shows the file's name, its kind, size and time, its full path with **Copy path**, **Download**, then one viewer by kind:

| Kind | What you get |
|---|---|
| Text | the file whole when it is 64 KiB or less; above that, **Start** and **End** (the last 64 KiB), and **Load more** for the next 64 KiB. Line numbers, search, **Wrap lines**; `.log`, `.out` and `.err` files are tinted by level |
| Table (`.csv`, `.tsv`, `.tab`) | a table in AG Grid, parsed in your browser from the first 1 MiB: at most 500 rows and 50 columns, **First row is a header**, **Show as text**, sort and filter on each column. See [Tables](#tables) |
| JSON | formatted, with **Show as text**; a file over 1 MiB, nested over 64 levels or not valid JSON is shown as text, with the reason |
| Image | the image itself (20 MiB at most, an SVG 5 MiB), on a light backdrop, with **Actual size**. An image that cannot be shown says so and offers Download |
| TIFF | the first plane drawn on a canvas, with **Actual size** and a line of facts under it. See [TIFF files](#tiff-files) |
| OME-TIFF (a file named `*.ome.tif` or `*.ome.tiff`) | on a desktop with WebGL 2, the image viewer with its channels; on a phone, or without WebGL 2, the flat view of the TIFF. See [OME-TIFF files](#ome-tiff-files) |
| HTML report | in the results, the report viewer, in a sandbox, opened for you. In a work directory, a note and Download. See [HTML files](#html-files) |
| OME-Zarr (a folder named `*.ome.zarr`) | the image viewer, with its channels. See [OME-Zarr](#ome-zarr) |
| PDF, binary | the facts and Download. Spectio does not open them |

- **Text is shown as text.** A file's content is never run as HTML, and an SVG is shown only in an `<img>`, where its scripts do nothing.
- **The breadcrumb names the file.** At the top of the page it reads "Home › Runs › demo-imaging › Results › cells.ome.tif": the run once, then Results or Work directory, then the file's name as the server answered it, never the name typed in the address. It reads "File" until the server has answered ([FU-P3-104](../progress/W5/P3-M9.md#fu-p3-104-the-breadcrumb-and-the-bare-links); the shot of [OME-TIFF files](#ome-tiff-files) shows it).
- **Escape sequences** in a text file are removed before it is shown. An unterminated one loses only its introducer; a terminated one can hide up to 4 KiB of lines ([inbox #128](../reviews/inbox.md#128-assumed-how-much-an-escape-sequence-in-a-previewed-file-may-hide-fu-p3-85a), assumed).
- **While the run is not over,** the page says when it read the file and has **Reload**. It does not follow a growing file on its own.
- **Limits** are 1 MiB of text or 20,000 lines, whichever comes first; then **Load more** stops, a line says so and Download gives the whole file.

On a phone the viewer comes after the facts, Copy path and Download; **Load more** is a full-width button, and the search sits behind a **Search** button.

![The same preview on a phone](../assets/shots/app-file-preview-phone_light.webp#only-light)
![The same preview on a phone](../assets/shots/app-file-preview-phone_dark.webp#only-dark)

## TIFF files

*Built on the integration branch (steps FU-P3-102d2 and -102d3, batch [P3-B12](../progress/W5/P3-M9.md#batch-p3-b12), 2026-11-10). The shots below are of a seeded demo run, see [Not shown](#not-shown). The rules are owned by [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview).*

A `.tif` or `.tiff` file opens as one flat picture: the first plane, in your browser. An OME-TIFF opens the same way on a phone, in a browser without WebGL 2 and when it has no OME metadata; otherwise it opens in the image viewer of [OME-TIFF files](#ome-tiff-files).

![Preview of imaging/cells.tif: a 512 by 384 plane of bright spots on black, on a light backdrop, under Actual size, with the line "512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff_light.webp#only-light)
![Preview of imaging/cells.tif: a 512 by 384 plane of bright spots on black, on a light backdrop, under Actual size, with the line "512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff_dark.webp#only-dark)

*A 16-bit grayscale TIFF of 512 by 384 pixels (a demo file, written for this shot), so the page says "Contrast stretched for display". The heading takes focus when the page opens, which is the purple ring around "cells.tif" in the shots (also on the phone). The backdrop stays light in the dark theme.*

![The same TIFF on a phone, with the line "Shown: 512 × 384 of 512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff-phone_light.webp#only-light)
![The same TIFF on a phone, with the line "Shown: 512 × 384 of 512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff-phone_dark.webp#only-dark)

*On a phone the line starts with "Shown:" and gives the size drawn against the size of the file, here the same.*

- **What you see.** The plane on a light backdrop, **Actual size**, and a line of facts: the size in pixels, "Shown: page 1 of N" for a multi-page file, "Contrast stretched for display" when the values were not 8-bit.
- **Contrast.** A file that is not 8-bit is stretched from its 0.1 and 99.9 percentiles to the screen's range. The file itself is not changed.
- **OME-TIFF in the flat view.** It shows its first plane, "channel 1, first plane". A file named `.ome.tif` with no OME metadata is shown as a TIFF, and says so. An OME-TIFF that names other files is not opened.
- **On a phone.** The largest reduced level that fits in 2,048 px a side is drawn, with "Open on a larger screen" and **Copy link**. If no level fits, the page says "This image is too large to show on a phone." and offers **Copy link** and **Download**.
- **Decoding is capped.** It runs in a worker of Spectio's own, with a size cap per tile, and only a short list of compressions is read: none, LZW, Deflate, PackBits and JPEG. A plane over 50 megapixels, or a file over 1 GiB, is not drawn.

| When | What the page says | What you can do |
|---|---|---|
| The file is empty | "This file is empty." | Download |
| Over the caps, or a file over 1 GiB | "This image is too large to show here (…). Download it to open it." The brackets give the reason, for example "over 1 GiB" | Download |
| A compression not on the list | "Spectio cannot decode LERC compression." (the compression's name, or "compression 99" for an unnamed code) | Download |
| An OME-TIFF that names other files | "This OME-TIFF names other files: Spectio shows one file at a time." | Download |
| The server says the file is not the TIFF its name says (422) | "This file is not the TIFF its name says." | Retry, Download |
| The file cannot be read as a TIFF (a damaged directory, or any other 422) | "Not an image Spectio can read: …" and the reason, for example "an IFD at 99, past the end" | Retry, Download |
| Too many reads | "Spectio stopped reading tiles: …" on the status line | Reload |
| A tile did not decode | "This image could not be decoded." | Retry, Download |

The wordings are in `web/src/runs/imaging/flat.ts` (`imageState`), checked by `flat.test.ts` and `FilePreview.test.tsx`.

## OME-TIFF files

*Built on the integration branch (steps FU-P3-102e and -102f, batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14), 2026-11-10). The rules are owned by [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview), the limits by [api §5.3.1](../specs/api-and-data-model.md) and [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts), requirement 19.*

A file named `*.ome.tif` or `*.ome.tiff` opens in the image viewer on a desktop or a tablet, in a browser with WebGL 2. The viewer is [Viv](https://github.com/hms-dbmi/viv) 0.23.0 on deck.gl 9.4.1, in a lazy chunk (`OmeView-*.js`), so the main bundle does not carry it.

![Preview of imaging/cells.ome.tif: three channels (DAPI blue, GFP green, Actin magenta) drawn together on a black canvas, with the channel list on the right, each with a contrast range and Reset contrast; the breadcrumb ends with cells.ome.tif](../assets/shots/app-file-preview-ome-tiff_light.webp#only-light)
![Preview of imaging/cells.ome.tif: three channels drawn together on a black canvas, with the channel list on the right, each with a contrast range and Reset contrast; the breadcrumb ends with cells.ome.tif](../assets/shots/app-file-preview-ome-tiff_dark.webp#only-dark)

*A demo OME-TIFF (three 16-bit channels of 512 by 384 pixels, 128-pixel tiles, no compression, a hand-written OME-XML), made by `tools/media/b14_demo.py`; channels 2 and 3 are the first one flipped and shifted. It is a seeded run, not a pipeline run. Captured in headless Chromium with its software WebGL 2. The canvas stays black in both themes.*

- **What is read.** The page asks the server for byte ranges of the file, through its own client, and hands Viv the opened file, never a URL. It walks the file's directories first with the caps of the flat view, then checks the OME-XML: sizes must be positive whole numbers that match the first plane, and channels × planes × time points at most 10,000. A pyramid has at most 20 levels. Over a cap, the page says so before it draws.
- **Channels.** A list headed "Channels · 3 of 3 on". Each row has a switch ("Show channel 2, GFP"), its colour name and, while on, a **Low** and a **High** contrast range, the file's range, and **Reset contrast**. At most 6 channels are on at once: a seventh says "At most 6 channels at once: switch one off first." The colour is the file's when no other channel on uses it, else the first free one of Blue, Green, Magenta, Yellow, Cyan, Orange. A list of more than 12 channels has a **Filter channels** box. The first 6 channels are on when the page opens.
- **Contrast.** It starts from the 0.1 and 99.9 percentiles of each channel's lowest level when that level has at most 2,048 × 2,048 pixels, else of its first tile, for every pixel type (`viv.ts`, `STATS_MAX`). The file is not changed.
- **Planes.** A **Z plane** and a **Time point** range show only when the file has more than one, "2 of 5".
- **Moving.** Arrows pan, `+` or `=` zooms in, `-` zooms out, `0` fits. **Zoom in**, **Zoom out** and **Fit** do the same, and "Zoom 100 %" says where you are. The canvas is a focusable region named "cells.ome.tif, image viewer".
- **The address keeps the view.** `&z=` and `&t=` (counted from 1), `&ch=` (the channels on, counted from 0, such as `ch=0,2`), `&zoom=`, `&x=` and `&y=` (the centre, in pixels of the full image). They are read once when the viewer opens and written back with a replace after a short pause, so **Reload** keeps the view and Back is not flooded. A value out of range is dropped and the default used. An RGB image has one channel and no panel, so `&ch=` is ignored for it.
- **Status line.** "Loading the image…", then "Reading tiles…" while tiles load. "Some tiles could not be read." has **Retry**; a stop by the read budget has **Reload**.
- **Flat view instead.** A phone, a browser without WebGL 2, a viewer error from deck.gl, and an `.ome.tif` with no OME-XML ("no OME metadata") show the [flat view](#tiff-files) and release the WebGL context.

Not built: **Open in the image viewer** for a plain `.tif` that has OME-XML (it stays in the flat view). A real pipeline's OME-TIFF was not opened, and the viewer test on Firefox and WebKit has not run ([inbox #148](../reviews/inbox.md#148-assumed-the-viewers-audit-gate-met-with-overrides-and-the-viewer-test-on-firefox-and-webkit-not-run-yet-fu-p3-102e)).

## Tables

*Built on the integration branch (step FU-P3-101a, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13), 2026-11-10). The rules are owned by [ui-spec §4.13](../specs/ui-spec.md#413-tables-in-ag-grid).*

A CSV or TSV file opens in an [AG Grid](https://www.ag-grid.com/) table. The grid is its own file, loaded when the first table opens, so a page with no table does not pay for it.

![Preview of quant/counts_matrix.tsv as a grid: a header row, a filter box under each header, then the first rows of 30](../assets/shots/app-file-preview-grid_light.webp#only-light)
![Preview of quant/counts_matrix.tsv as a grid: a header row, a filter box under each header, then the first rows of 30](../assets/shots/app-file-preview-grid_dark.webp#only-dark)

*A 30-row demo TSV (1.2 KiB, written by `tools/media/b13_demo.py`, not a pipeline output). The table's name is above it. Past 15 rows the grid has a fixed height and scrolls inside it, drawing only the rows in view.*

- **Sort.** Each header sorts its column: as numbers when both values are numbers, otherwise in natural order. Enter on a header sorts it.
- **Filter.** The box under each header keeps the rows whose cell contains what you type. Each box is named "<column> Filter Input".
- **Caps are the old ones:** at most 500 rows, 50 columns and the first 1 MiB, with the notes that say so.
- **Cells are text.** A cell is never read as HTML.
- **Keyboard.** Tab enters the grid at the first header. The arrow keys move between headers and cells. How NVDA, JAWS and VoiceOver read the grid is **[to be validated]** (ui-spec §4.13).
- **On a phone** the table stays a table: the grid scrolls sideways inside its frame. The batch took no phone shot of it.
- **Your runs list uses the same grid** on a desktop and a tablet. See [The runs list](states-outputs-efficiency.md#the-runs-list).

## HTML files

*Built on the integration branch (step FU-P3-88a, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13)).*

- **In the results,** opening an HTML file goes straight to the report viewer, with its folder's sort and filter kept for the way back. Before, the page stopped at a note with a link.
- **The source is one click away.** **Show the source as text** under the frame opens the same file as plain text.
- **A file over 1 GiB** reads "Too large for the report viewer (over 1 GiB). Download it to open it."
- **From a job's Outputs,** the preview keeps its note and the link "Open it in the report viewer", so the back link still returns to the job's sheet.
- **In a work directory,** an HTML file is still never opened: "Spectio does not open HTML from a work directory. Download it to open it."

## OME-Zarr

*Built on the integration branch (step FU-P3-102g, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13), 2026-11-10). The rules are owned by [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview), the limits by [api §5.3.1](../specs/api-and-data-model.md) and [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts), requirement 19.*

A folder named `*.ome.zarr` is the one folder whose row opens the preview page. The page opens it in the image viewer, on a desktop, in a browser with WebGL 2.

![Preview of imaging/cells.ome.zarr: two channels, DAPI in blue and GFP in green, on a black canvas, with the channel list and a contrast range for each](../assets/shots/app-file-preview-zarr_light.webp#only-light)
![Preview of imaging/cells.ome.zarr: two channels, DAPI in blue and GFP in green, on a black canvas, with the channel list and a contrast range for each](../assets/shots/app-file-preview-zarr_dark.webp#only-dark)

*A demo OME-Zarr (Zarr v2, two 16-bit channels of 512 by 384 pixels, a raw level and a zlib level; the shot predates the new codecs and shows the same store), seeded by `tools/media/b13_demo.py`; the second channel is the first flipped. Captured in headless Chromium with its software WebGL 2. The canvas stays black in both themes.*

- **How it is read.** The page asks the server for one key at a time, below the folder, and gives them to the viewer. It reads the metadata first, caps it at 1 MiB, and rebuilds it before the viewer sees it. `.zmetadata` is never asked. Each request counts against the view's budget (2,000 requests, 256 MiB, 3 in flight).
- **Channels.** A list with a switch per channel, its colour and a low and a high contrast range, and **Reset contrast**. The first 6 channels are on.
- **Keys.** Arrows pan, `+` zooms in, `-` zooms out, `0` fits.
- **Compression.** Chunks that are uncompressed, zlib, gzip, **Blosc** (with blosclz, lz4, lz4hc, zlib or zstd inside, byte or bit shuffle), **LZ4** or **zstd** are decoded (step FU-P3-102h, batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15)). Spectio decodes them with its own JavaScript in the decoder workers, so the page's security policy is unchanged and has no `unsafe-eval`; zstd goes through [`fzstd`](https://www.npmjs.com/package/fzstd) 0.1.1 (MIT). Any other compressor, Zarr filters and Blosc with snappy read "Spectio cannot decode <name> compression."; a chunk that does not decode to its level's size reads "Some tiles could not be read." Every chunk is held to its expected size before it is kept.
- **A multi-channel store opens.** A read reserves up to 16 MiB of the view's byte budget (256 MiB) only once it has one of the 3 slots, so at most 3 × 16 MiB is held and a store with many channels is no longer stopped on its first paint (a blocker found in review, fixed before merge).
- **Caps on what a store may claim:** a side of at most 2^31 − 1 pixels, channels × planes × time points at most 10,000, every level keeping level 0's channels, planes and time points. A store over a cap reads as too large, before anything is allocated.
- **A Zarr v2 store in a work directory** reads "This OME-Zarr uses Zarr v2, which a work directory does not serve. Open it from the results once it is published."
- **Not built yet (FU-P3-102h, part 2):** a phone and a browser without WebGL 2 show a note ("Open on a larger screen: Spectio shows an OME-Zarr in the image viewer only." or "This browser cannot open the image viewer: it needs WebGL 2, which is off or missing.") with **Browse folder**, not a flat picture. The two states for a store published as a link are not built either.

## What you can check on the API

The pages use these routes; each needs a signed-in session and a same-origin request. Against the demo run above (`curl` with the session cookie):

```console
$ GET /api/v1/runs/<id>/results/stat/quant/counts_matrix.tsv
200  {"root":"/srv/demo-b09/runs/run_01M6Z7T0FMDX057V4J131D73Q9/launch/results","path":"quant/counts_matrix.tsv","name":"counts_matrix.tsv","type":"file","size":250,...}
$ GET /api/v1/runs/<id>/results/text/quant/counts_matrix.tsv      (Range: bytes=0-20)
206  content-range: bytes 0-20/250 · content-security-policy: sandbox; default-src 'none'
$ GET /api/v1/tasks/<task>/attempts/1/workdir/stat/.command.env
422  /problems/file-not-allowed: not served here: a name that starts with '.'
```

## Not shown

- **A TIFF, in one state only.** The two shots above show the plane in the browser, taken from a server that `tools/media/tiff_demo.py` seeds: a finished run record with `results/imaging/cells.tif` written by hand, and no pipeline run (the host had no Nextflow and no Snakemake). The server and the screens are the real ones, so the pixels are drawn by the browser. Not shown: the other states of the table above (too large, a compression not on the list, not a TIFF, stopped, empty), an 8-bit and an RGB file, a multi-page file, an OME-TIFF and the phone's "too large" case. They are covered by `vitest` (`flat.test.ts`, `FilePreview.test.tsx`: 544 tests pass), which draws no pixels. The shots of those states are follow-up FU-P3-114.
- **An image, a PDF and an HTML file in a work directory:** the synthetic run writes none. They are covered by tests (`test_results.py`, `FilePreview.test.tsx`, and `preview.spec.ts`, a Playwright test of the hostile SVG that runs on Chromium only).
- **A big file with Load more,** a JSON file and the cap lines: no shot. `preview.spec.ts` loads a 200 KiB log.
- **A real Nextflow work directory on a cluster,** and any SLURM run: not done.
- **A task past the run's first 2,000:** the page cannot reopen its sheet and says "This job's sheet could not be reopened." (follow-up FU-P3-96).
- **Firefox and WebKit:** `preview.spec.ts` has not run on them.
- **Batch P3-B14 shot of the OME-TIFF viewer is of a seeded record** (`tools/media/b14_demo.py`, a hand-written file). Not shown: a channel switched off or its contrast changed, a Z or time range (the demo has one plane per channel), the `&ch=` address, the flat fallbacks, a file over a cap, and the phone.
- **Batch P3-B13 shots are of seeded records, not pipeline runs** (`tools/media/b13_demo.py`). Not shown: the grid on a phone, a column sorted or filtered, the HTML file opening in the report viewer, an OME-Zarr in the Unsupported, too-large or work-directory states, the phone and no-WebGL notes, and a Zarr store from a real pipeline. Firefox and WebKit did not run the viewer ([inbox #148](../reviews/inbox.md#148-assumed-the-viewers-audit-gate-met-with-overrides-and-the-viewer-test-on-firefox-and-webkit-not-run-yet-fu-p3-102e)).
