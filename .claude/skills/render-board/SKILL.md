---
name: render-board
description: Render one or more Spectio UI canvas boards (design/ui-canvas/*.dc.html) to PNG and look at them, optionally after clicking elements. Use whenever a board is created or changed, or when reviewing the UI.
argument-hint: "<Board> [Board…] [--phone]"
---

1. **Find the files.** For each board name in `$ARGUMENTS`, the file is `design/ui-canvas/<Board>.dc.html`.
2. **Render.** Use `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180 /tmp/<Board>.png`, or `390 844` for phone boards (names starting with `M`) or with `--phone`.
   - To show an interactive state, pass CSS selectors to click after the size arguments, e.g. `'#tab-scheduler'`.
   - If Playwright is missing, run `npm install --no-save playwright` first. Chromium may need `npx playwright install chromium` outside the cloud environment.
3. **Look.** Open each PNG with Read. Look for:
   - overflow, clipped text, overlapping elements;
   - columns collapsing to zero width;
   - empty `sc-for` lists;
   - wrong colours against `design/tokens/spectio-tokens.css`.
4. **Report** what you see, honestly, before claiming the board is done.
