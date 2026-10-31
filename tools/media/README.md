# Docs media (`tools/media/`)

This folder holds the scripts that produce every recording and screenshot in the docs. Like the diagrams in [`tools/diagrams/`](../diagrams/README.md), each output can be regenerated from a script, and the output is committed.

| Output | Script | Source | Lands in |
|---|---|---|---|
| Terminal casts (asciinema v2) | `cast.py` | `casts/*.yaml` | `docs/assets/casts/<name>.cast` |
| Screenshots (WebP) | `shots.py` | `REGISTRY` in the script | `docs/assets/shots/<name>_<theme>.webp` |
| Terminal and browser side by side | `combo.py` | `combos/*.yaml` | `docs/assets/media/<name>.mp4`; the GIF preview goes to `tools/media/out/` (PR bodies, not committed) |
| The public demo's recorded API | `record_demo.py` | a running demo `spectio serve` | `web/demo/fixtures.json` (committed), built into `/demo/` of the docs site |
| Demo-data hygiene | `fixtures.yaml`, `sanitize.py` | — | used by the four scripts above |
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
- **Live shots** (`live=` steps, such as `app-launch`) are taken by `live.js` from a running `spectio serve`, with no rewriting of the page: set `SPECTIO_URL` (for example `http://127.0.0.1:8080`) and `SPECTIO_DEMO_PIPELINE`, the synthetic Nextflow pipeline (`tests/pipelines/synthetic/nextflow`) copied to a path free of the `forbidden` terms of `fixtures.yaml`. Without `SPECTIO_URL`, `--all` skips them. To run it, copy `tests/pipelines/synthetic/data` and `tests/pipelines/synthetic/bin` beside the copy too (`main.nf` reads `../data`, and `bin/synth.py` links to `../../bin`). `app-home`, `app-runs`, `app-run-detail` and `app-run-detail-phone` (P1 Task 20), and `app-home-phone` and `app-runs-phone` (P3 UI parity B), need a finished run of that copy with profile `test`; set `SPECTIO_DEMO_RUN` to its ID. `app-launch-snakemake` (P3 UI parity B) needs `SPECTIO_DEMO_SMK_PIPELINE`: `tests/pipelines/synthetic/snakemake` copied to a clean path (for example `/g/demo-lab/pipelines/synthetic-smk`) with a `config/config.yaml` added, which the repository copy does not have. Its content is the Snakefile's own defaults (`workflow/Snakefile`, `config.setdefault`) except `samples`, plus one nested map, so that the form shows a dotted-key section (UX-PAR-31):

    ```yaml
    outdir: results
    chunks: 0
    scale: 1
    seed: 42
    fail_mode: none
    fail_rule: ""
    fail_sample: ""
    fail_gb: 2
    time_limit_s: 120
    ref:
      species: homo_sapiens
      release: 113
      build: GRCh38
    ```

    The shot opens the two sections (`open:` steps) and sets `outdir` and `ref.release`, so the preview shows the whole `ref` map. The launch is not submitted. `app-run-detail-failed` (P3 UI parity A) needs a failed run of the Nextflow copy (`SPECTIO_DEMO_PIPELINE`): launch it with the parameters `fail_mode=exit` and `fail_process=MERGE`, and set `SPECTIO_DEMO_FAILED_RUN` to its ID. `app-run-logs` (P3 UI parity C) opens the Logs tab of that same failed run, on the head's output; since UI parity D it searches it for `MERGE` and waits for the counter `1 / 4`. `app-run-process` (P3 UI parity D) opens the sheet of process `ALIGN` on `SPECTIO_DEMO_RUN`. Since UI parity D, `app-launch` and `app-launch-phone` pick `SPECTIO_DEMO_PIPELINE` from Try a test pipeline, so the server must have run it once.

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

## The public demo: `record_demo.py`

The demo at `https://spectio.pages.dev/demo/` (and `/demo/` of every PR preview) is the real web UI built with `npm --prefix web run build:demo`, whose API is answered from `web/demo/fixtures.json` (`web/src/demo/stub.ts`): reads only, writes refused, no request leaves the page. The file is public, so it holds demo data only. To record it again:

1. Start the demo server as for the live shots: the account `alice`, the node name `login1` in its own UTS namespace, `HOME=/g/demo-lab`, the config `/g/demo-lab/data/spectio.toml` and the venv `/opt/spectio-demo-venv` (with this checkout's packages on `PYTHONPATH` to serve this branch's API):

    ```bash
    P=$PWD/packages; unshare --uts bash -c "hostname login1 && exec setpriv --reuid=alice --regid=alice --init-groups \
        env -i HOME=/g/demo-lab SPECTIO_CONFIG=/g/demo-lab/data/spectio.toml \
        PYTHONPATH=$P/spectio/src:$P/spectio-sdk/src:$P/spectio-server/src PATH=/opt/spectio-demo-venv/bin:/usr/bin:/bin \
        bash -c 'cd /g/demo-lab && exec spectio serve'"
    ```

2. Launch the runs the demo shows (the 2026-10-31 recording has five: two plain runs of the synthetic Nextflow copy, one failed in `MERGE` with `fail_mode=exit` and `fail_process=MERGE`, `variant-calling-batch-3`, `cohort-2026-scale` with 2069 tasks, and one run of `/g/demo-lab/pipelines/nf-core-demo`, a copy of the synthetic pipeline whose `manifest.name` is `nf-core/demo`: a demo copy, not an nf-core pipeline). The pipelines to inspect are `synthetic`, `synthetic-smk` and `nf-core-demo` under `/g/demo-lab/pipelines` (set up as for the live shots above).
3. Record, then rebuild:

    ```bash
    python3 tools/media/record_demo.py --base http://127.0.0.1:8766   # -> web/demo/fixtures.json: 41 answers, 773205 bytes
    npm --prefix web run build:demo                                    # -> web/dist-demo
    ```

What it records: `/version`, `/runs:summary?group_by=state`, the whole runs list, and per run the run, its processes, stages, every task, and the three logs (`head-out`, `head-err`, `engine`; the server's last 64 KiB of each). Lists are stored whole, so the stub filters and pages them as the server does. Before the check, Nextflow's `System: Linux <release>` banner line is cut to `System: Linux` (SEC-P3DEMO-02). The script refuses to write when `sanitize.leaks` (this file's `forbidden` terms), the recorder's own host name or its own kernel release hits, or when the file would pass 1.5 MB. The guard knows only the recorder's machine: a server on another host is not covered (SEC-P3DEMO-06). `python3 -m unittest tools/media/test_record_demo.py` checks the committed file; no CI job runs it yet (FU-P3-29). The stub moves every time in the JSON answers so that the newest run ended an hour before the page was opened; the banner says so, and the log texts keep their recorded times.

The demo's screenshot (`demo-runs`) is taken from the built demo served statically under `/demo/`:

```bash
rm -rf /tmp/demo-root/demo && mkdir -p /tmp/demo-root && cp -R web/dist-demo /tmp/demo-root/demo
(cd /tmp/demo-root && python3 -m http.server 8903 --bind 127.0.0.1) &
SPECTIO_URL=http://127.0.0.1:8903/demo python3 tools/media/shots.py run --shot demo-runs --theme light
```

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
