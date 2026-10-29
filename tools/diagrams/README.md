# Hand-drawn diagrams (`tools/diagrams/`)

These figures are drawn in Python, not in an editor. They look like Excalidraw sketches but they are produced by code: double strokes along a wobbly line, pastel fills and the Excalifont handwriting font. The toolkit is `sketch.py`, ported from depictio (MIT; the commits are listed at the top of the file).

Because they are produced by code:
- a figure can be fixed in a diff when the thing it shows changes;
- running a script again writes byte-identical SVG, because the random jitter has a fixed seed;
- a review only shows real changes.

## Render

```bash
cd tools/diagrams
python3 autopilot_loop.py           # docs/assets/diagrams/autopilot-loop_{light,dark}.{svg,png}
python3 gate_resume.py              # docs/assets/diagrams/gate-resume_{light,dark}.{svg,png}
python3 gate_resume.py --no-png     # SVG only, no browser needed
```

**Requirements:**
- Python 3.11+ with `playwright` and its Chromium, for the PNGs;
- ImageMagick (optional): it reduces the PNGs to 256 colours, which makes them about 3 times smaller.

**Font:** `SPECTIO_SKETCH_TTF` points to the font. The default is `docs/fonts/Excalifont.ttf`, not committed; [`FONT-LICENSE.md`](FONT-LICENSE.md) says how to make it and what its licence status is. Without it, PNG rendering stops; `--no-png` still writes the SVGs.

## Rules

1. **One script per figure.** Each script produces both themes through `write_themed` and writes `<name>_light.*` and `<name>_dark.*`.
2. **Commit both the SVG and the PNG.**
   - The SVG is the source you review.
   - The PNG is what pages embed: an SVG loaded through `<img>` cannot use the web font, so its text would fall back to another font and overflow its boxes.
3. **Embed the light and dark PNGs as a pair.** Material for MkDocs shows the one that matches the reader's theme:
   ```markdown
   ![The autopilot loop](../assets/diagrams/autopilot-loop_light.png#only-light)
   ![The autopilot loop](../assets/diagrams/autopilot-loop_dark.png#only-dark)
   ```
4. **Draw the thing, not a box naming it.** Use the pictograms instead of labelled rectangles:
   - `terminal`, `browser`, `phone`;
   - `page`, `folder`, `envelope`, `link`;
   - `hpc_node`, `k8s_pod`, `runner`, `gate`, `pipeline`;
   - `gauge`, `task_strip`.

   Number the steps with captions (`s.step(cx, y, n, label)`).
5. **To scale, from measurements.** When a figure shows counts or durations, draw them to scale with `task_strip`, bars or axes. Take the numbers from a real run, and name the source in the script's docstring and in the figure's footer.
6. **Name fills by meaning,** not by colour: `input`, `work`, `gate`, `done`, `docs`, `problem`, `neutral`, `cached`, `recomputed`. Each theme maps them to its own colours.
7. **Handwritten text: no braces, no runs of punctuation.** The handwriting font draws them badly, and has no `§`, `→`, `✓` or `✗`. Put code between backticks so it is set in monospace (`` `nextflow run -resume` ``).
8. **Look at both PNGs before you commit:** check that no label collides with another and that the dark version reads well.

## In a pull request body

GitHub does not render a relative image path from a PR body. Link the PNG committed on the PR branch, pinned to the PR head commit, so the picture still matches the PR after more pushes:

```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/weber8thomas/spectio/<head-sha>/docs/assets/diagrams/gate-resume_dark.png">
  <img alt="Stop at the QC gate, drop a sample, resume" src="https://raw.githubusercontent.com/weber8thomas/spectio/<head-sha>/docs/assets/diagrams/gate-resume_light.png">
</picture>
```

**Private repositories:** raw URLs need authentication, so the images do not show for logged-out viewers. Reviewers are logged in, so this is acceptable. Whether GitHub's image proxy serves them to logged-in reviewers is **[to be validated]**. If it does not, the fallback is to drag the PNG into the PR body, which uploads it to `user-images.githubusercontent.com`.

## Adding a glyph

- **Where:** add it as a method on `Sketch`.
- **Inputs:** a centre or top-left corner, plus a size.
- **Drawing:** use `poly`, `line` and `circle` with single-pass, low-jitter strokes; a double stroke blurs at glyph size.
- **Colours:** use theme colours only (`self.t.ink`, `self.t.fill("…")`), so the glyph works in both themes.
