# Virgil font: licence status (2026-10-26)

`docs/fonts/Virgil.ttf` is copied byte for byte from `depictio-docs/docs/fonts/Virgil.ttf` (commit `1610ed8`). It is Excalidraw's handwriting font.

## What the sources say

| Source | Statement |
|---|---|
| The font's own name table (read with fontTools) | family `Virgil GS`, version "2002; 1.0, initial release", copyright "Copyright (c) Jason Smith fonted by Font Garden, 2002. **All rights reserved.**" |
| <https://plus.excalidraw.com/virgil> (fetched 2026-10-26) | "Released under the OFL-1.1 licence, Virgil is freely available for both personal and commercial use", and further down the same page: "Download available under MIT licence" |
| <https://github.com/excalidraw/virgil> | not reachable from this session **[to be validated]** |

The sources disagree. The embedded "All rights reserved" may simply be a leftover from the original 2002 font. Excalidraw's page grants OFL-1.1, but the same page also says MIT.

## Status

**[to be validated]** before the font is published in a public docs site.

## Next steps

1. Read the LICENSE file in `excalidraw/virgil`.
2. If it is OFL-1.1, add the OFL text as `docs/fonts/OFL.txt` with the copyright line. OFL allows bundling the font with software, but not selling the font on its own.
3. If the licence cannot be confirmed, choose one of these:
   - switch to **Excalifont**, Excalidraw's newer font, if its licence is clearer **[to be validated]**;
   - leave the font out of the repository and set `SPECTIO_VIRGIL_TTF` locally. `sketch.py` falls back to a cursive system font when the file is missing; the figures then look different but still render.
