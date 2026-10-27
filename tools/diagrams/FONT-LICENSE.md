# Virgil font: licence status (2026-10-27)

The sketches use Excalidraw's handwriting font, Virgil. The font file is **not committed**. `docs/fonts/*.ttf` is git-ignored, and each contributor sets `SPECTIO_VIRGIL_TTF` or puts the file at `docs/fonts/Virgil.ttf` (inbox #1, Thomas, 2026-10-26: the font stays local).

The local file used so far is copied byte for byte from `depictio-docs/docs/fonts/Virgil.ttf` (commit `1610ed8`).

## What the sources say

| Source | Statement |
|---|---|
| <https://github.com/excalidraw/virgil>, `LICENSE.md` (read 2026-10-27 through `raw.githubusercontent.com/excalidraw/virgil/main/LICENSE.md`) | First line: "Copyright (c) 2021 - Present, Ellinor Rapp, with Reserved Font Name Virgil." Then: "This Font Software is licensed under the SIL Open Font License, Version 1.1", followed by the full OFL 1.1 text (Preamble to Disclaimer). |
| <https://github.com/excalidraw/virgil>, repository page (read 2026-10-27) | The licence badge reads "OFL-1.1". The README credits "The original font of Excalidraw created by Ellinor Rapp". The font ships as `Virgil.woff2` at the repository root. |
| <https://plus.excalidraw.com/virgil> (fetched 2026-10-26) | "Released under the OFL-1.1 licence, Virgil is freely available for both personal and commercial use", and further down the same page: "Download available under MIT licence" |
| The name table of the depictio copy (read with fontTools, 2026-10-26) | family `Virgil GS`, version "2002; 1.0, initial release", copyright "Copyright (c) Jason Smith fonted by Font Garden, 2002. **All rights reserved.**" |

## Status

- **The Virgil release in `excalidraw/virgil` is under OFL-1.1.** The primary source is the repository's `LICENSE.md`. Its copyright line and the OFL 1.1 text are in [`docs/fonts/OFL.txt`](../../docs/fonts/OFL.txt). The licence body there is the standard OFL 1.1 text: the rust toolchain's `OFL-1.1.txt` copy, whose sections match the ones in `LICENSE.md`. The MIT mention on the Excalidraw page does not change this: the repository's licence file is OFL-1.1 only.
- **The depictio copy is not shown to be that release.** Its embedded name, version and copyright (`Virgil GS`, 2002, Jason Smith, "All rights reserved") do not match the `excalidraw/virgil` licence (Ellinor Rapp, 2021). Whether the two files are the same design is **[to be validated]**. Do not commit the depictio copy.
- OFL 1.1 allows bundling the font with software and redistributing it, but not selling it on its own. A modified version may not use the reserved name "Virgil" (OFL 1.1, conditions 1 and 3, in `OFL.txt`).

## If the font is committed later

Committing the font is Thomas's call (inbox #1). If he decides to commit it:

1. Take the font from `excalidraw/virgil` (`Virgil.woff2`), not the depictio copy.
2. Commit `docs/fonts/OFL.txt` next to it. OFL condition 2 requires the copyright notice and the licence to travel with the font.
3. Check that `tools/diagrams/sketch.py` still renders with it: the browser shell in `sketch.py` declares the font as `format('truetype')`, which a woff2 file does not match.
