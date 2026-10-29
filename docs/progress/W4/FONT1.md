---
step: FONT1
wave: W4
status: running
pr: null
review: null
review_score: null
review_ref: null
---
# FONT1 · The hand-drawn figures switch to Excalifont

!!! info "Running 2026-10-29 · branch `autopilot/excalifont` · Thomas: \"font utilisé pour diagram n'est pas bonne ; prends en une autre\", then \"Excalifont\" from six candidates · the font stays uncommitted (inbox #1)"

![FONT1 figure: the autopilot loop, re-rendered in Excalifont; same layout as before, rounder and more even handwriting](../../assets/diagrams/autopilot-loop_light.png#only-light)
![FONT1 figure: the autopilot loop, re-rendered in Excalifont; same layout as before, rounder and more even handwriting](../../assets/diagrams/autopilot-loop_dark.png#only-dark)

## What changed

- **`tools/diagrams/sketch.py`:**
    - the font comes from `SPECTIO_SKETCH_TTF`, default `docs/fonts/Excalifont.ttf` (was `SPECTIO_VIRGIL_TTF` and `Virgil.ttf`);
    - the SVG font stack is `Excalifont, ui-sans-serif, system-ui, sans-serif`: an SVG opened without the font shows a plain sans, not Comic Sans or a serif;
    - PNG rendering stops with a message, before any file is written, when the font file is missing. Before, it silently fell back to whatever the browser had. `--no-png`, which CI uses, does not need the font.
- **All 32 figures** in `docs/assets/diagrams/` re-rendered, SVG and both PNGs.
- **`tools/diagrams/FONT-LICENSE.md`:** an Excalifont section on top (how to make the file, its sha256, the licence statements); the Virgil notes kept below as history.
- **References:** [documentation-system §1 and §3](../../specs/documentation-system.md) (and §3's mention of an `--allow-fallback-font` flag that never existed), `tools/diagrams/README.md`, the `diagram-artist` agent, `docs/assets/media.yaml`, `mkdocs.yml`, `.gitignore`, `tools/dashboard/gen.py`.
- **Records:** a [decision-log entry](../../decisions/log.md#2026-10-29-the-hand-drawn-figures-switch-from-virgil-to-excalifont) and a note on [inbox #1](../../reviews/inbox.md#1-virgil-font-licence-blocks-publishing-the-hand-drawn-figures-font).

## Why

Thomas did not like the diagram font. Six candidates were drawn on the same figure (Excalifont, Kalam, Patrick Hand, Architects Daughter, Inter, Virgil) and he chose Excalifont. It is Excalidraw's own successor to Virgil, so the figures keep their Excalidraw look. Its widths are close to Virgil's (39.65 against 39.83 em for a sample line), so no figure needed a layout change.

## How to test it

```bash
# make the font file once (tools/diagrams/FONT-LICENSE.md has the sha256 check)
python3 tools/diagrams/autopilot_loop.py            # SVG and both PNGs, in Excalifont
SPECTIO_SKETCH_TTF=/nonexistent python3 tools/diagrams/autopilot_loop.py
# stops: "/nonexistent is missing: set SPECTIO_SKETCH_TTF …, or pass --no-png"
SPECTIO_SKETCH_TTF=/nonexistent python3 tools/diagrams/autopilot_loop.py --no-png   # SVG only, exit 0
```

## Evidence

- The six candidates were rendered side by side on one figure before Thomas chose.
- All 32 scripts re-run with the font present: every PNG shows Excalifont (contact sheets of all figures checked by eye). Re-running them gives byte-identical SVGs.
- The guard: with `SPECTIO_SKETCH_TTF` pointing at a missing file, a PNG render stops with the message above before writing any file (no SVG, no temporary page left in `TMPDIR`); with `--no-png` it writes the SVGs and exits 0.

## Figures and media

The figure above is one of the 32 re-rendered ones; no new figure. Every page that shows a hand-drawn figure now shows it in Excalifont.

## Findings and open questions

- Excalifont lacks `§`, `→`, `⌄`, `✓` and `✗` in every subset Excalidraw ships; those few characters fall back to the sans. The diagrams README now says to avoid them.
- Licence: Excalidraw states OFL-1.1, but the font file has no licence record **[to be validated]**. The font stays uncommitted, as inbox #1 decided.
- `docs/playbooks/next-phase.md` still says "settle the Virgil font licence or switch fonts" for a later step; the switch is done, the CI-rendered PNGs are not.
