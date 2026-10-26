# Spike: diagram and media tooling for the docs (2026-10-26)

**Goal:** make every figure and recording in the docs regenerable from a script. This means:
- hand-drawn diagrams that show real pictograms, not labelled boxes;
- terminal casts;
- screenshots;
- a combined terminal and browser capture.

**Starting point:** depictio's toolkit, audited in the docs-system research note from the same day.

**Result:** every piece works end to end in this cloud session, and every output was checked by looking at it.

## What was built

| Piece | Files | Origin |
|---|---|---|
| Hand-drawn SVG toolkit | `tools/diagrams/sketch.py` | Merged port of depictio `dev/diagrams/sketch.py` (`0d1aa0a`, glyph helpers) and depictio-docs `dev/diagrams/sketch.py` (`1610ed8`, `Theme` / `write_themed`), both MIT. Every helper is theme-aware. New Spectio glyphs: `gate`, `runner`, `hpc_node`, `k8s_pod`, `pipeline`, `phone`, `envelope`, `link`, `gauge`, `task_strip`. Semantic fills. PNGs reduced to 256 colours with ImageMagick. |
| Figure: the autopilot tick | `tools/diagrams/autopilot_loop.py` → `docs/assets/diagrams/autopilot-loop_{light,dark}.{svg,png}` | New |
| Figure: stop at the gate, drop a sample, resume | `tools/diagrams/gate_resume.py` → `docs/assets/diagrams/gate-resume_{light,dark}.{svg,png}` | New. Every count is measured (see below). |
| Diagram rules, font status | `tools/diagrams/README.md`, `tools/diagrams/FONT-LICENSE.md` | Rules adapted from depictio-docs `dev/diagrams/README.md`; adds how to embed figures in a PR body |
| Font | `docs/fonts/Virgil.ttf`, kept local and git-ignored (`SPECTIO_VIRGIL_TTF`) | Copied from depictio-docs; licence **[to be validated]** (below), so not committed (inbox #1) |
| Cast generator | `tools/media/cast.py`, `tools/media/casts/synthetic-gate.yaml` → `docs/assets/casts/synthetic-gate.cast` | New: depictio's casts are recorded by hand |
| Cast player for the site | `docs/javascripts/asciinema.js`, `docs/stylesheets/asciinema.css` | Port of depictio-docs (`1610ed8`), with a `spectio` theme taken from `design/tokens/spectio-tokens.css` and a `data-autoplay` attribute |
| Screenshot registry | `tools/media/shots.py` → `docs/assets/shots/*.webp` | Pattern of depictio `dev/playwright_debug/docs_screenshots.py`; renders the canvas boards for now |
| Terminal and browser capture | `tools/media/combo.py`, `tools/media/combos/gate-review.yaml` → `docs/assets/media/gate-review.{mp4,gif}` | New: depictio has no combined capture |
| Churn guard | `tools/media/check_churn.sh` | Port of depictio `scripts/check-screenshot-churn.sh` (`0d1aa0a`), with a threshold and a CI mode |
| Docs for all of it | `tools/media/README.md` | New |

## Commands and outputs (this session)

| Command | Output | Size | Time |
|---|---|---|---|
| `python3 tools/diagrams/autopilot_loop.py` | 2 SVG + 2 PNG (1720×930 at 2×) | SVG 137 KB each; PNG 207 KB light, 225 KB dark (after quantising; about 550 KB before) | ~10 s |
| `python3 tools/diagrams/gate_resume.py` | 2 SVG + 2 PNG (1720×1000 at 2×) | SVG 86 KB; PNG 160 / 169 KB | ~10 s |
| `python3 tools/media/cast.py tools/media/casts/synthetic-gate.yaml` | `synthetic-gate.cast`, 36.2 s, 734 events | 19 KB | ~10 s (runs Snakemake 9.27.1 twice) |
| `python3 tools/media/shots.py run --all` | `run-detail`, `review-gate`, `review-gate-phone` (light only) | 94 / 77 / 39 KB | ~15 s |
| `python3 tools/media/combo.py tools/media/combos/gate-review.yaml` | `gate-review.mp4` (1280×720, 25 fps, 38 s), `gate-review.gif` (880 px, 8 fps) | 0.47 MB / 3.68 MB | ~60 s |

## What was verified

**Diagrams (by looking at them).**
- All four PNGs were read and corrected until labels stopped colliding:
  - autopilot loop: the budget link was rerouted, the turn arrow and the "next tick" label moved, the gauge given a start offset;
  - gate figure: the runner antenna and the `QC_REPORT` chip.
- Dark mode reads as well as light.

**Determinism.**
- Running both diagram scripts again gives byte-identical SVGs (`md5sum -c`).
- Running the cast script again gives a byte-identical `.cast` (`cmp`), even though Snakemake really runs each time. Lines carrying timestamps are dropped by the `keep` filters.

**Numbers in the gate figure** are measured from the trace of the `exclude_sample_and_resume` scenario on Nextflow 26.10.3:

| Run | Tasks |
|---|---|
| Run 1 | 25 tasks: 12 MAKE_READS, 12 QC_STATS, 1 QC_REPORT |
| Run 2: cached | 22 tasks: 11 MAKE_READS, 11 QC_STATS |
| Run 2: recomputed | 38 tasks: QC_REPORT 1, SPLIT 11, ALIGN 22, MERGE 1, COMPARE 2, FINAL_REPORT 1 |

Reads per sample come from `data/samplesheet.csv`: S03 has 40, every other sample 400.

**The cast.**
- Its plain text was dumped and read through.
- One problem was caught this way: `column` is missing in this container, and its error message was being written into the cast. `cast.py` now runs every command with `bash -o pipefail`, so a broken pipe fails the build instead.
- A dry run in the cast shows Snakemake does not schedule `make_reads` or `qc_stats` again after S03 is removed.

**The combined capture.** Frames at 4, 10, 15, 24, 30 and 35 s were extracted and looked at:
- the caption changes with each scene;
- the terminal and browser panes stay in sync with the cast clock;
- the "UI design boards, not a live instance" note is visible in the URL bar.

It was first placed over the phone tab bar; it was moved.

## Problems hit and fixed

1. **Chromium refuses `fetch()` of a `file://` cast.** The player failed with "Failed to fetch". `combo.py` now passes the cast inline (`{data: …}`).
2. **The first GIF was 4.5 MB** at 960 px and 10 fps. At 880 px and 8 fps, with a 128-colour diff palette, it is 3.7 MB. The MP4 is the file to embed; the GIF is for PR bodies and previews.
3. **The UI boards have no dark variant.** `shots.py` only produces light files for now and says so when asked for dark.

## [to be validated]

**The Virgil licence.**
- The TTF's own name table reads "Copyright (c) Jason Smith fonted by Font Garden, 2002. All rights reserved."
- <https://plus.excalidraw.com/virgil> says both "Released under the OFL-1.1 licence" and "Download available under MIT licence".
- <https://github.com/excalidraw/virgil> could not be fetched from this session: the permission request timed out.

Resolve this before the docs site is public. `tools/diagrams/FONT-LICENSE.md` lists the options, including Excalifont.

**Raw image URLs in a private repository's PR bodies.** The diagram README describes the `<picture>` and raw.githubusercontent.com pattern. Whether those images show for logged-in reviewers of a *private* repository was not tested, because there is no push access from this session.

**Only checked locally so far.**
- The docs site player (`asciinema.js` loading from jsDelivr, the `document$` remount) is a port and was not exercised in a built site: `mkdocs.yml` wiring is a separate step.
- The `combo.py` page loads the player from `tools/media/node_modules`, installed by `npm ci` with the pinned version 3.17.0.

## Next

1. Wire `extra_css` / `extra_javascript` and the player stylesheet into `mkdocs.yml`, embed one cast, and check it in `mkdocs serve`.
2. Run `check_churn.sh origin/main` in the docs workflow.
3. When the app exists, switch `shots.py` from board rendering to a Playwright session against the dev instance, and give the shots dark variants.
