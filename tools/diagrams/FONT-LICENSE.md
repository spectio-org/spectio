# Sketch font: licence status

## Excalifont (since 2026-10-29)

Thomas, 2026-10-29: "font utilisé pour diagram n'est pas bonne ; prends en une autre"; from six candidates rendered on the same figure, he chose Excalifont, Excalidraw's own successor to Virgil. Its widths are close to Virgil's (the summed advance widths of "The quick brown fox jumps over the lazy dog", without kerning, are 22.02 em against Virgil's 22.16), so the figures kept their layout.

**The file.** The font is **not committed**, as Virgil was not (inbox #1). `docs/fonts/*.ttf` is git-ignored; each contributor sets `SPECTIO_SKETCH_TTF` or puts the file at `docs/fonts/Excalifont.ttf`. `sketch.py` stops instead of writing a PNG when the file is missing. To make it:

```bash
curl -sLo /tmp/Excalifont.woff2 https://unpkg.com/@excalidraw/excalidraw@0.18.0/dist/prod/fonts/Excalifont/Excalifont-Regular-a88b72a24fb54c9f94e3b5fdaa7481c9.woff2
echo "e4423b318e11432aff2e6e865e300b7ca270f92321a3f56632268fede01c1b48  /tmp/Excalifont.woff2" | sha256sum -c
uv run --with fonttools --with brotli python3 -c "from fontTools.ttLib import TTFont; f=TTFont('/tmp/Excalifont.woff2'); f.flavor=None; f.save('docs/fonts/Excalifont.ttf')"
```

That file is the Latin subset Excalidraw ships (212 characters). No Excalifont subset in that package has `§`, `→`, `⌄`, `✓` or `✗` (all seven files checked, 2026-10-29); the browser draws those few in its sans fallback.

| Source | Statement |
|---|---|
| <https://plus.excalidraw.com/excalifont> (fetched 2026-10-29) | "Released under the OFL-1.1 license, Excalifont is freely available for both personal and commercial use"; "Download available under OFL-1.1 license (included in the font file)". The page's meta description says "Download Excalifont under MIT license". |
| npm `@excalidraw/excalidraw` 0.18.0 (registry metadata, 2026-10-29) | Package licence MIT; the font ships in `dist/prod/fonts/Excalifont/` as seven subset files. |
| The name table of the subset above (read with fontTools, 2026-10-29) | family `Excalifont`, version "Version 1.000;Glyphs 3.2 (3227)", copyright "Copyright (c) 2024 by Excalidraw. All rights reserved."; no licence or licence-URL record. |

**Status: likely OFL-1.1, not confirmed.** **[to be validated]** The owner, Excalidraw, states OFL-1.1, but the file carries no licence record, and the same page also says MIT. Committing the font stays Thomas's call (inbox #1); if he decides to, take the file above and add its OFL text next to it (OFL condition 2). The `docs/fonts/OFL.txt` already there is Virgil's, kept with the history below.

## Virgil (until 2026-10-29)

The sketches use Excalidraw's handwriting font, Virgil. The font file is **not committed**. `docs/fonts/*.ttf` is git-ignored, and each contributor sets `SPECTIO_VIRGIL_TTF` or puts the file at `docs/fonts/Virgil.ttf` (inbox #1, Thomas, 2026-10-26: the font stays local).

The local file used so far is copied byte for byte from `depictio-docs/docs/fonts/Virgil.ttf` (commit `1610ed8`).

### What the sources say

| Source | Statement |
|---|---|
| <https://github.com/excalidraw/virgil>, `LICENSE.md` (read 2026-10-27 through `raw.githubusercontent.com/excalidraw/virgil/main/LICENSE.md`) | First line: "Copyright (c) 2021 - Present, Ellinor Rapp, with Reserved Font Name Virgil." Then: "This Font Software is licensed under the SIL Open Font License, Version 1.1", followed by the full OFL 1.1 text (Preamble to Disclaimer). |
| <https://github.com/excalidraw/virgil>, repository page (read 2026-10-27) | The licence badge reads "OFL-1.1". The README credits "The original font of Excalidraw created by Ellinor Rapp". The font ships as `Virgil.woff2` at the repository root. |
| <https://plus.excalidraw.com/virgil> (fetched 2026-10-26) | "Released under the OFL-1.1 licence, Virgil is freely available for both personal and commercial use", and further down the same page: "Download available under MIT licence" |
| The name table of `excalidraw/virgil`'s own `Virgil.woff2` (downloaded 2026-10-27 through `cdn.jsdelivr.net/gh/excalidraw/virgil@main/Virgil.woff2`, sha256 `9976295b…fadbcf1cf`, read with fontTools) | family `Virgil 3 YOFF`, version "Version 001.001;YOFF;Virgil3YOFF;2020;FL720", copyright "Copyright (c) 2011 by Your Own Font Foundry. **All rights reserved.**", licence description "**Freeware for personal use!** For commercial license please go to https://www.yourownfont.com/ and make a donation! It can be as much as you want it to.", trademark "Virgil YOFF is a trademark of Your Own Font Foundry." |
| The name table of the depictio copy (read with fontTools, 2026-10-26) | family `Virgil GS`, version "2002; 1.0, initial release", copyright "Copyright (c) Jason Smith fonted by Font Garden, 2002. **All rights reserved.**" |

### Status

**Unconfirmed: the sources conflict.** **[to be validated]**

- **The `excalidraw/virgil` repository declares OFL-1.1.** Its `LICENSE.md` names Ellinor Rapp (2021) and gives the full OFL 1.1 text. The copyright line and the OFL 1.1 text are in [`docs/fonts/OFL.txt`](../../docs/fonts/OFL.txt). The licence body there is the standard OFL 1.1 text, taken from the rust toolchain's `OFL-1.1.txt`, whose sections match the ones in `LICENSE.md`.
- **The font file in that same repository says something else.** Its name table names another foundry (Your Own Font Foundry, 2011), says "All rights reserved", and describes it as "Freeware for personal use", with a commercial licence on request. Neither the README nor `LICENSE.md` explains the difference. It may be stale metadata from the font the design started from, or the file may carry other terms. This was found on 2026-10-27 and is not resolved.
- **The Excalidraw page** says both OFL-1.1 and MIT.
- **`OFL.txt` covers only the `excalidraw/virgil` release, as that repository declares it,** not a local `Virgil.ttf` from another source. `mkdocs.yml` excludes `fonts/*.ttf`, so a local font file never goes into the built site.
- **The depictio copy is a third build.** It carries yet another embedded name and copyright (`Virgil GS`, 2002, Jason Smith, "All rights reserved"). Do not commit it.
- Until the conflict is settled, the font stays local and uncommitted, as inbox #1 decided. The D6 figure (`d6-progress-hook-check`) was rendered locally with the `excalidraw/virgil` file, converted to TTF in a scratch folder. Earlier figures used the depictio copy. The two builds may draw some letters differently **[to be validated]**.
- If the OFL applies: OFL 1.1 allows bundling the font with software and redistributing it, but not selling it on its own. A modified version may not use the reserved name "Virgil" (OFL 1.1, conditions 1 and 3, in `OFL.txt`).

### If the font is committed later

Committing the font is Thomas's call (inbox #1), after the conflict above is settled, for example by asking the `excalidraw/virgil` maintainers. If he decides to commit it:

1. Take the font from `excalidraw/virgil` (`Virgil.woff2`), not the depictio copy.
2. Commit `docs/fonts/OFL.txt` next to it. OFL condition 2 requires the copyright notice and the licence to travel with the font.
3. Check that `tools/diagrams/sketch.py` still renders with it: the browser shell in `sketch.py` declares the font as `format('truetype')`, which a woff2 file does not match.
