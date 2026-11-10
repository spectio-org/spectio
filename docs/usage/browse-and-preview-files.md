---
icon: material/file-search-outline
---
# Browsing and previewing a run's files

!!! note "Built on the integration branch, not released yet"

    This works today from a checkout (steps FU-P3-85a to FU-P3-85e, batch [P3-B09](../progress/W5/P3-M9.md#batch-p3-b09), 2026-11-09). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **It ran on a local executor only, on a `.tsv` file:** no image, PDF or HTML state was captured, no SLURM run and no real cluster work directory was opened (see [Not shown](#not-shown)).

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

*A 250-byte TSV from the same run. The heading takes focus when the page opens. In the table, the line "counts_matrix.tsv" under the header row (`sample`, `total`, `mapped`, `mapped_rate`) is the table's caption, not a row of the file: it should sit above the header. This is a known display fault in 0.0.1, with a fix planned ([follow-up FU-P3-100](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b09)). In the dark shot, the first column (`sample`) has a lighter background from the first row down. That is intended: the first column is sticky (`position: sticky; left: 0`) and has its own background, so it stays readable when you scroll the table sideways (`web/src/runs/runs.css:1817`).*

The page shows the file's name, its kind, size and time, its full path with **Copy path**, **Download**, then one viewer by kind:

| Kind | What you get |
|---|---|
| Text | the file whole when it is 64 KiB or less; above that, **Start** and **End** (the last 64 KiB), and **Load more** for the next 64 KiB. Line numbers, search, **Wrap lines**; `.log`, `.out` and `.err` files are tinted by level |
| Table (`.csv`, `.tsv`, `.tab`) | a table, parsed in your browser from the first 1 MiB: at most 500 rows and 50 columns, **First row is a header**, **Show as text** |
| JSON | formatted, with **Show as text**; a file over 1 MiB, nested over 64 levels or not valid JSON is shown as text, with the reason |
| Image | the image itself (20 MiB at most, an SVG 5 MiB), on a light backdrop, with **Actual size**. An image that cannot be shown says so and offers Download |
| TIFF, OME-TIFF | the first plane drawn on a canvas, with **Actual size** and a line of facts under it. See [TIFF files](#tiff-files) |
| HTML report | the report viewer, in a sandbox |
| PDF, binary | the facts and Download. Spectio does not open them |

- **Text is shown as text.** A file's content is never run as HTML, and an SVG is shown only in an `<img>`, where its scripts do nothing.
- **Escape sequences** in a text file are removed before it is shown. An unterminated one loses only its introducer; a terminated one can hide up to 4 KiB of lines ([inbox #128](../reviews/inbox.md#128-assumed-how-much-an-escape-sequence-in-a-previewed-file-may-hide-fu-p3-85a), assumed).
- **While the run is not over,** the page says when it read the file and has **Reload**. It does not follow a growing file on its own.
- **Limits** are 1 MiB of text or 20,000 lines, whichever comes first; then **Load more** stops, a line says so and Download gives the whole file.

On a phone the viewer comes after the facts, Copy path and Download; **Load more** is a full-width button, and the search sits behind a **Search** button.

![The same preview on a phone](../assets/shots/app-file-preview-phone_light.webp#only-light)
![The same preview on a phone](../assets/shots/app-file-preview-phone_dark.webp#only-dark)

## TIFF files

*Built on the integration branch (steps FU-P3-102d2 and -102d3, batch [P3-B12](../progress/W5/P3-M9.md#batch-p3-b12), 2026-11-10). The shots below are of a seeded demo run, see [Not shown](#not-shown). The rules are owned by [ui-spec §4.4.1](../specs/ui-spec.md#441-file-explorer-and-preview).*

A `.tif` or `.tiff` file, and an OME-TIFF, opens as one flat picture: the first plane, in your browser.

![Preview of imaging/cells.tif: a 512 by 384 plane of bright spots on black, on a light backdrop, under Actual size, with the line "512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff_light.webp#only-light)
![Preview of imaging/cells.tif: a 512 by 384 plane of bright spots on black, on a light backdrop, under Actual size, with the line "512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff_dark.webp#only-dark)

*A 16-bit grayscale TIFF of 512 by 384 pixels (a demo file, written for this shot), so the page says "Contrast stretched for display". The heading takes focus when the page opens, which is the purple ring around "cells.tif" in the shots (also on the phone). The backdrop stays light in the dark theme.*

![The same TIFF on a phone, with the line "Shown: 512 × 384 of 512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff-phone_light.webp#only-light)
![The same TIFF on a phone, with the line "Shown: 512 × 384 of 512 × 384 px · Contrast stretched for display"](../assets/shots/app-file-preview-tiff-phone_dark.webp#only-dark)

*On a phone the line starts with "Shown:" and gives the size drawn against the size of the file, here the same.*

- **What you see.** The plane on a light backdrop, **Actual size**, and a line of facts: the size in pixels, "Shown: page 1 of N" for a multi-page file, "Contrast stretched for display" when the values were not 8-bit.
- **Contrast.** A file that is not 8-bit is stretched from its 0.1 and 99.9 percentiles to the screen's range. The file itself is not changed.
- **OME-TIFF.** It shows its first plane, "channel 1, first plane". Until the image viewer is built (FU-P3-102e), a file with a SubIFD pyramid is not seen as one, so a large one reads "too large on a phone". A file named `.ome.tif` with no OME metadata is shown as a TIFF, and says so. An OME-TIFF that names other files is not opened.
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
