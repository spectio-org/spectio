# Docs media (`tools/media/`)

This folder holds the scripts that produce every recording and screenshot in the docs. Like the diagrams in [`tools/diagrams/`](../diagrams/README.md), each output can be regenerated from a script, and the output is committed.

| Output | Script | Source | Lands in |
|---|---|---|---|
| Terminal casts (asciinema v2) | `cast.py` | `casts/*.yaml` | `docs/assets/casts/<name>.cast` |
| Screenshots (WebP) | `shots.py` | `REGISTRY` in the script | `docs/assets/shots/<name>_<theme>.webp` |
| Terminal and browser side by side | `combo.py` | `combos/*.yaml` | `docs/assets/media/<name>.mp4`; the GIF preview goes to `tools/media/out/` (PR bodies, not committed) |
| Demo-data hygiene | `fixtures.yaml`, `sanitize.py` | — | used by the three scripts above |
| Churn guard | `check_churn.sh` | — | pre-commit or CI |

**Requirements:**
- Python 3.11+ with `pyyaml` and `playwright` (Chromium);
- Node with `playwright`, for `tools/canvas/render.js`;
- ImageMagick (`convert`);
- ffmpeg, with libx264;
- `npm ci` in this folder, for the local asciinema-player that `combo.py` uses. `node_modules/` is not committed.

## Terminal casts: `cast.py`

```bash
python3 tools/media/cast.py tools/media/casts/synthetic-gate.yaml
```

**How a cast is made:**
- **The output is real.** Each `run:` step runs for real, in a fresh temporary directory or in the `workdir` the YAML gives.
- **The timing is synthetic.** Typing speed, line delay and pauses are set by the YAML, so a cast is the same length every time it is regenerated.
- **Filtering only removes lines.** `keep`, `drop`, `head` and `tail` select lines, and `replace` shortens paths, but no line is ever rewritten.
- **A failed command stops the build.** If a command does not exit with `expect_exit` (default 0), the cast is not written. A cast cannot silently show an error.

**Why not record by hand with `asciinema rec`?** A hand recording goes stale as soon as the CLI changes, and nobody re-types it.

**Embedding a cast in a page:** the player (`docs/javascripts/asciinema.js`, theme `docs/stylesheets/asciinema.css`) mounts it. That needs `extra_javascript` / `extra_css` in `mkdocs.yml`, plus the player stylesheet from jsDelivr.

```html
<div class="asciinema-cast" data-cast="assets/casts/synthetic-gate.cast"></div>
```

## Screenshots: `shots.py`

```bash
python3 tools/media/shots.py list
python3 tools/media/shots.py run --shot review-gate      # light and dark
python3 tools/media/shots.py run --all --theme light
```

**The registry.**
- Each shot has a name, a board, a viewport and a caption. Pages refer to a shot by name: `assets/shots/review-gate_light.webp`.
- Today a shot renders a UI canvas board through `tools/canvas/render.js`.
- Once the app runs, the same names will be captured from a live instance with Playwright, so pages that embed them do not change.
- The boards have no dark variant yet, so `--theme dark` skips them (shots are light-only in the design phase). A page embeds the light file without the `#only-light` suffix until a dark file exists.
- WebP is lossless, so UI text stays sharp.

## Terminal and browser side by side: `combo.py`

```bash
python3 tools/media/combo.py tools/media/combos/gate-review.yaml
python3 tools/media/combo.py tools/media/combos/gate-review.yaml --html-only   # inspect the page
```

**What it records.** A local page plays a cast on the left and a browser frame on the right.
- The browser pane switches between screenshots (`shot:`) or images (`image:`) at the cast times listed under `scenes`.
- Each scene shows a caption below the panes.
- The page polls the player's own clock, so the two panes stay in sync even on a slow machine.

**How it is encoded.**
1. Playwright records the page as WebM.
2. ffmpeg cuts the page-load lead-in.
3. ffmpeg writes an MP4 (H.264, `+faststart`) and a GIF preview (8–10 fps, 128-colour palette).

**Labelling.** Until a live instance exists, the browser pane shows design boards. The YAML `note` says so on screen.

**Embedding in a page:**
```html
<video controls muted playsinline preload="metadata" poster="assets/shots/run-detail_light.webp" width="100%">
  <source src="assets/media/gate-review.mp4" type="video/mp4">
</video>
```
A PR body cannot play a video, so it uses the GIF from `tools/media/out/` instead (generated on demand, never committed, so the PR stays under the 5 MB media budget). The poster is a shot, not the GIF. The video is at most 30 s: `speed` in the YAML plays the cast faster, and `combo.py` fails above 30 s.

## Demo-data hygiene: `fixtures.yaml`

The UI boards are design sources and contain the owner's real name and environment. They are never edited:
- `shots.py` renders a sanitised copy of every board, in a temporary sibling directory of `design/ui-canvas` (so logos and shared components resolve), deleted afterwards;
- the substitutions (`Thomas` to `Alice`, `TW` to `AL`, `/scratch/tw/` to `/scratch/demo/`, `EMBL` to `demo-hpc`, any real email to `alice@example.org`) live in `fixtures.yaml`;
- after rendering, the page text and markup are checked against the `forbidden` patterns (`page_text.js` dumps them through Playwright), and the script fails if one is visible;
- `combo.py` checks the recorded page (captions, URL bar, terminal rows) the same way, and `cast.py` checks the cast text.

## Churn guard: `check_churn.sh`

Running `shots.py` or `combo.py` again rewrites every file, even when nothing visible changed. When more than three existing files in `docs/assets/shots` or `docs/assets/media` are modified, the guard blocks the commit. It is a port of depictio's `check-screenshot-churn.sh`.

```bash
tools/media/check_churn.sh                                 # staged files (pre-commit)
tools/media/check_churn.sh origin/main                     # in CI, against the base branch
SPECTIO_ALLOW_SCREENSHOT_UPDATE=1 git commit ...           # deliberate update, after looking
```
