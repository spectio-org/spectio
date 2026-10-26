# depictio documentation system — audit for Spectio (2026-10-26)

**Sources (read-only clones in the session scratchpad).**
- `depictio-docs/` at `1610ed8` (2026-10-12): the docs site.
- `dep/` = depictio at `0d1aa0a` (2026-10-23): the product repo, which holds the release workflow, the original diagram toolkit and the screenshot scripts.

Paths below are relative to those roots. Line numbers refer to those commits. Anything not read in the files is marked **[to be validated]**.

**Images copied** to `docs/research/depictio-docs-shots/`:
- `diagram_local_up_flow.png`: Excalidraw-style flow diagram.
- `diagram_saml_login_flow.svg`: committed SVG source of a sequence-style figure.
- `screenshot_rnaseq_01.png`: product screenshot as used in the docs.
- `landing_1440x900.png`: first viewport of the locally built site.
- `landing_sections_900-4500.png`: crop of the full-page capture (the full page is 1440×16891).

---

## 1. Site structure

### 1.1 Toolchain

`pyproject.toml` (version `1.17.1`) pins the toolchain:
- `mkdocs-material>=9.7`, `mike`, `neoteroi-mkdocs`;
- `mkdocs-kroki-plugin`, `mkdocs-glightbox>=0.5.2`;
- `mkdocs-swagger-ui-tag`, `render-swagger`, `mkdocs-typer`, `mkdocstrings-python`;
- `mkdocs-inline-select-svg-plugin`, `graphviz`;
- a separate dependency group `diagrams = ["playwright"]`.

The site is built with `uv sync` + `uv run mkdocs`.

**Local build check.** The build succeeded in this session in 26.7 s with:

```
uvx --with mkdocs-material --with mkdocs-material-extensions --with neoteroi-mkdocs \
    --with mkdocs-swagger-ui-tag --with mkdocs-inline-select-svg-plugin \
    --with mkdocs-kroki-plugin --with mkdocs-glightbox --with mike mkdocs build
```

### 1.2 `mkdocs.yml`

**Theme.**
- `material` with `custom_dir: overrides` (l.16).
- Logo `images/logo/animated_favicon.svg`.
- Two palettes: `default` / white and `slate` / black, with a toggle.

**Features.**
- `content.code.copy`, `.select`, `.annotate`;
- `navigation.sections`, `.instant`, `.tracking`, `.tabs`, `.tabs.sticky`, `.indexes`, `.expand`, `.top`;
- `header.autohide`, `toc.follow`;
- `search.highlight`, `.share`, `.suggest`;
- `announce.dismiss`.

**Assets.**
- Extra CSS from `docs/stylesheets/`: `extra.css`, `timeline.css`, `blog.css`, the vendored neoteroi css, `asciinema.css`. Icon fonts (mdi, boxicons) and `asciinema-player@3.17.0` css come from a CDN.
- Extra JS, in `docs/javascripts/`:
  - `depictio-rose.js`, `depictio-logo.js`: animated logo;
  - `depictio-theme-sync.js`: syncs the theme with embedded apps;
  - `catalog-fullscreen.js`, `template-catalog.js`, `template-version.js`: template gallery;
  - `doc-sections.js`;
  - `asciinema.js`;
  - `theme-video.js`.

**Markdown extensions.**
- `admonition`, `attr_list`, `def_list`, `meta`, `md_in_html`, `footnotes`, `toc` (permalink), `neoteroi.timeline`;
- pymdownx: `caret`, `tilde`, `details`, `tasklist`, `highlight`, `inlinehilite`, `emoji` (twemoji), `tabbed` (alternate), `snippets` (`base_path: docs`), `superfences` with a `mermaid` custom fence.

**Plugins.**
- `search`;
- `glightbox`, in manual mode: a page only gets lightboxes when its front matter has `glightbox: true` (l.146–150);
- `inline-select-svg`, `blog`, `swagger-ui-tag`;
- `kroki`: `ServerURL: https://kroki.io`, Excalidraw enabled (l.189).

**Hooks and extras.**
- Hook `hooks/shared_images.py` (l.139, see §1.5).
- `extra.version.provider: mike` (l.205), default `stable`.
- `extra.analytics: google` (l.209).

**Navigation (top tabs).**
- Home;
- Installation: Docker Compose, Kubernetes, Python package, upgrade guides, CLI, Configuration, env reference;
- Usage, Tutorials, Features;
- API: Overview, API Reference (swagger-ui-tag on `api/openapi.json`), FastAPI Docs;
- Templates, Tools Catalog, Developer, Roadmap, Changelog, Blog;
- More: palette, funding.

### 1.3 Overrides

- `overrides/main.html` extends `base.html` and preloads `fonts/Virgil.ttf`, so hand-drawn SVGs inlined in pages render with the right font.
- `overrides/partials/footer.html` is a custom footer with several columns: links, funding, partners.

### 1.4 Landing page (`docs/index.md`, 3356 lines)

Front matter: `hide: [navigation, toc, path]`. The page h1 is hidden by CSS. The page is raw HTML through `md_in_html`.

Sections, in order (see the two landing PNGs):
1. **`hero-section`.**
   - Light and dark logos at width 460, `hero-description` (a three-line bold tagline) and `hero-subtext`.
   - `hero-video`: an iframe with `data-src-light` / `data-src-dark` Vimeo URLs. `theme-video.js` swaps the source when the palette changes.
2. **`lead-section`:** one paragraph on the problem.
3. **`workflow-section`:** "Workflow Ecosystem" logo cards for nf-core, WorkflowHub and the Snakemake Workflow Catalog.
4. **`components-section`:** a 3×3 `component-card` grid (icon, name, one line). Brand colours are CSS variables.
5. **`live-demo-section`:**
   - a "Live interactive demo" badge with a status dot and a collapsible embed of the public demo instance;
   - Codespaces and install links.
6. Then, in order:
   - `key-features-section`: numbered rows such as "01 YOUR DATA, IN ONE PLACE";
   - `catalog-landing-section`;
   - `getting-started-section`;
   - `funding-section`, `partners-section`, `tech-section`.

**Weak point.** About 2270 lines of inline `<style>` sit at l.858–3129 of `index.md`, plus an inline `<script>`. That CSS should have lived in `extra.css`.

### 1.5 Versioning and deployment

**Workflow** `.github/workflows/deploy-docs.yaml`.
- **Trigger:** a push to `main` touching `docs/**` or `pyproject.toml`, or `workflow_dispatch` with inputs version, alias and `depictio_ref`.
- **Version:** `VERSION` is read from `pyproject.toml`. A `-b` suffix gives the `beta` alias; otherwise the aliases are `latest` and `stable`.
- **Catalog:** the job checks out the depictio source and builds the template catalog gallery with pnpm before building the site.
- **Deploy:** `uv run mike deploy --push --update-aliases "$VERSION" latest stable` and `mike set-default --push stable` (l.116–122). This writes to the `gh-pages` branch, which GitHub Pages serves.
- **Shared images:** `./scripts/publish-shared-images.sh` (l.129), then the same script with `--dest assets` for catalog assets (l.133). `./scripts/verify-shared-assets.py --version` then checks the published result (l.142).

**`hooks/shared_images.py`.**
- **Why:** mike copies the whole site for every version. The image folders had pushed `gh-pages` to about 2 GB, over the 1 GB GitHub Pages limit (per the hook's docstring).
- **What it does:** with `DEPICTIO_DOCS_SHARED_IMAGES=1`, it rewrites links into `SHARED_SUBTREES` (l.28: architecture, blog, data-model, guides, modularity, pipeline-templates, react) to one root copy that all versions share.

### 1.6 OpenAPI

The API reference is generated from the released image, not written by hand.

**Workflow** `.github/workflows/update-on-release.yaml`.
- **Trigger:** `repository_dispatch` of type `new-release` (l.4), sent by the depictio release, or a manual run with a version.
- **Extraction:**
  - pull `ghcr.io/depictio/depictio-api:<tag>`;
  - run `python -c "import json; from depictio.api.main import app; print(json.dumps(app.openapi(), indent=2))"` (l.72) with `DEPICTIO_CONTEXT=server`, `DEPICTIO_AUTH_SINGLE_USER_MODE=true` and a throwaway password, so the app imports without a database;
  - write the output to `docs/api/openapi.json`.
- **Validation:**
  - `jq` parses the file;
  - the file must be at least 100 bytes;
  - it must contain at least 10 paths.

  The job then stamps the file with `x-generated-at` and `x-depictio-version`.
- **Result:** the job bumps the `pyproject.toml` version and opens a PR with `peter-evans/create-pull-request@v6` (l.112), labelled `documentation` and `automated`. Merging that PR triggers the deploy in §1.5.

`update_openapi.py` is the manual fallback: it fetches `{api_url}/openapi.json` from a running instance.

### 1.7 Use cases

`docs/use_cases.md` holds short biological narratives:
- Strand-seq single-cell structural variants;
- diatom interactions (TREC).

Each one says what the dashboard answers, not how it was built.

`docs/documentation/README.md` and `documentation_outline.md` hold the docs outline and contributor rules.

## 2. Changelog

There are two layers.

**Layer 1: raw notes, generated in depictio.**
- `dep/.github/workflows/release.yaml` l.63 runs `.github/scripts/changelog_generator.sh "$PREVIOUS_TAG" "$CURRENT_TAG" > CHANGELOG.md`.
- Its output is a Docker-images block plus a `<details>` list of commits. It becomes the GitHub release body.
- An "Update CHANGELOG.md for vX" commit writes it back to the repo.

**Layer 2: the curated page, written by hand.**
- `depictio-docs/docs/changelog/README.md` (3739 lines) has one block per version, newest first. Every version uses the same shape:

```markdown
## **[v1.17.0](https://github.com/depictio/depictio/releases/tag/v1.17.0)** (October 12, 2026)

!!! success "Minor: <one-line theme of the release>"

### Docker Images
    ```bash
    ghcr.io/depictio/depictio-api:v1.17.0 …
    ```

### **✨ New Features**
* **Bold lead**: one sentence on what users can now do. See [Page](../features/x.md#anchor)
  ([#917](<PR url>), [6146fe0b](<commit url>)).

### **🚀 Improvements**
### **🐛 Bug Fixes**

---
```

**Conventions:**
- every bullet links to the feature page and to the PR and commit;
- the admonition type gives the size of the release (`success` for minor);
- each bullet starts with a bold user-facing lead.

No script turning commits into the curated page was found **[to be validated]**. It appears to be written by hand, or by an assistant, from the release body.

## 3. Diagrams: the hand-drawn "sketch" toolkit

**Where it lives.**
- `dep/dev/diagrams/sketch.py`: the original, 922 lines.
- `depictio-docs/dev/diagrams/sketch.py`: a 590-line port.
- `depictio-docs/dev/diagrams/README.md`: the rules.
- Both are pure Python that writes SVG. Excalidraw itself is not involved. The kroki Excalidraw plugin is enabled, but this toolkit does not use it.

### 3.1 Look

- **Strokes:** every stroke is drawn twice along a jittered bezier. The jitter comes from a seeded RNG (`Sketch(width, height, seed=7)`), so a rerun is byte-identical and the git diff shows only real changes.
- **Font:** `FONT = "Virgil GS, Virgil, Excalifont, Comic Sans MS, …"` (dep l.43; the docs port puts `Virgil` first, l.37). Text in backticks is drawn in `MONO`.
- **Palette** (dep l.26 onwards):
  - ink: `INK #1e1e1e`, `DIM #5c5c5c`, `RED #c92a2a`;
  - pastel fills: `BLUE #e7f5ff`, `YELLOW #fff9db`, `GREEN #ebfbee`, `VIOLET #f3f0ff`, `ORANGE #ffe8cc`, `PINK #ffe3e3`, `GOLD`;
  - coloured inks: `BLUE_INK`, `RED_INK`, `GREEN_INK`.

### 3.2 API (dep)

`Box(x, y, w, h, fill, title, lines)` is a dataclass (l.72). `Sketch` (l.98) has these methods:
- **Primitives:** `line`, `rect`, `poly`, `arrow`, `curve`, `cross`, `arc`, `dot`, `diamond`, `tick`.
- **Text:** `text`, `text_rotated`, `heading`.
- **Layout:** `box`, `frame`, `shade`.
- **Charts:** `axes`, `time_axis`.
- **Pictograms:** `lock`, `thumbnail`, `commit_strip`, `ledger_strip`.
- **Output:** `svg()`.

Glyph helpers draw real pictograms rather than labelled boxes:
- shapes and signs: `ellipse`, `circle`, `warning`, `hourglass`;
- files and storage: `page`, `folder`, `bucket`, `table_stack`;
- UI pieces: `magnifier`, `browser`, `field`, `mini_table`, `button`, `chip`, `terminal`.

### 3.3 Rendering

**`write(sketch, out, name, png=True, quantize=False)`** (dep l.908):
1. writes `<out>_<name>.svg`;
2. calls `_render_png` (l.850), which:
   - inlines the SVG into an HTML page with a base64 Virgil `@font-face`, found by `_virgil_ttf()` (l.595) from `$DEPICTIO_VIRGIL_TTF` or `depictio/viewer/src/assets/fonts/Virgil.ttf`;
   - opens the page in Playwright Chromium (viewport w×h, `device_scale_factor=2`), awaits `document.fonts.ready` plus 300 ms, and screenshots it;
3. optionally runs `_quantize` (l.878), which calls ImageMagick `-colors 256` to make the PNG smaller.

`_chromium_executable` falls back to `PLAYWRIGHT_BROWSERS_PATH`. `--no-png` writes the SVG only.

**`write_themed(build, out, name)`** (docs port l.583) calls `build(theme)` twice and writes `<name>_light` and `<name>_dark` (SVG and PNG).

### 3.4 Outputs and embedding

**Scripts.** There is one script per figure in `dev/diagrams/`, for example:
- `saml_login.py`;
- `local_server.py`, which writes `same_code`, `same_code_docs` and `up_flow`;
- `user_groups.py`, `dashboard_versioning_schema.py`, `filter_persistence.py`;
- about 15 more.

Each script sets `OUT = docs/images/<topic>`, which gives files named like `saml-login_flow.svg` and `.png`.

**Embedding.** Pages embed the PNG pair as `![…](…_light.png#only-light)` and `![…](…_dark.png#only-dark)`. The README explains why: an SVG loaded through `<img>` cannot load the web font. The SVG is still committed as the reviewable source.

**Other README rules:**
- name fills by meaning ("input", "warning"), not by colour;
- avoid braces and runs of punctuation, because Virgil draws them badly;
- the toolkit is duplicated from depictio, where it "produces the schema figures attached to pull requests". So the same figures serve the PR description and the docs page.

**Example.** `diagram_local_up_flow.png`, "From a terminal to a dashboard", shows the style at its best:
- a terminal panel, package cubes, a laptop with DB, server and bucket glyphs, and a browser with charts;
- numbered captions;
- to-scale wall-time bars (47 s / 17 s / 8 s);
- red-cross cards for "no Docker / no conda / no git clone".

## 4. Media

### 4.1 Terminal casts (asciinema)

- **Files:** 13 asciinema v2 casts in `docs/assets/casts/*.cast`: install, compose, ingest-detect, ingest-template, ingest-refresh, watch, catalog, backup, recipe, nextflow-trigger, and others. Each header sets `idle_time_limit: 2.5` and a title. The sessions are typed live, with `#` comment lines as narration.
- **Embed markup:** `<div class="asciinema-cast" data-cast="assets/casts/<name>.cast"></div>`.
- **`docs/javascripts/asciinema.js`:**
  - resolves the site root from Material's `#__config`, so links work under mike version prefixes;
  - lazy-loads `asciinema-player@3.17.0` from jsDelivr;
  - remounts on Material's `document$` observable, which `navigation.instant` needs;
  - options: `fit:'width'`, `poster:'npt:0:3'`, `theme:'depictio'`, `idleTimeLimit:1.5`.
- **`docs/stylesheets/asciinema.css`:** the `.asciinema-player-theme-depictio` dark terminal theme in brand colours.
- **Gap:** no script that generates the casts was found. They look recorded by hand **[to be validated]**.

### 4.2 Screenshots

- **Main script:** `dep/dev/playwright_debug/docs_screenshots.py` is a Typer CLI with a `REGISTRY: dict[str, ShotFn]` (l.72) of named shots.
  - `list` prints the shots; `run --shot <name> --theme dark --project-id …` takes one.
  - Viewport 1440×900, 1180 high for tall shots. Output goes to `<root>/react/`.
- **Other capture scripts:**
  - `dev/advanced_viz_docs_screenshots/capture_react_screenshots.py`;
  - captures of the local server at 1920×1200.
- **Docs format:** WebP light/dark pairs, each wrapped in a link that opens the full image:
  `[![alt](../../images/guides/web-ui/look_paper_light.webp#only-light)](…){target=_blank}`.
  A page turns on lightboxes with `glightbox: true` in its front matter.
- **Churn guard:** `scripts/check-screenshot-churn.sh` refuses a mass change to screenshots unless `DEPICTIO_ALLOW_SCREENSHOT_UPDATE=1` is set.

### 4.3 Video

The only video is the hero's pair of Vimeo embeds, swapped with the theme by `theme-video.js`. There are no in-page demo videos.

### 4.4 Combined captures

No capture combining a terminal and a browser (cast plus screen, side by side or in sequence) was found. Diagrams like `up_flow` fill that role statically.

## 5. Pull request conventions and docs CI

- **PR template:** `dep/.github/pull_request_template.md` has these sections:
  - Summary;
  - Type of change: Bugfix / Feature / Refactor / Build-CI / Documentation;
  - Related issue;
  - How was this tested;
  - Checklist: ruff, ty, pre-commit, tests, docs updated.
- **Commits:** Conventional Commits with a scope and the PR number, e.g. `feat(ampliseq): … (#1264)`. Changes land through PR merges.
- **Process rule:** depictio's CLAUDE.md says: "After significant PRs, update depictio-docs and Obsidian notes".
- **Figures in PRs:** sketch.py figures are attached to PRs (diagram README, §3.4).
- **depictio-docs linting:**
  - `.markdownlint.json` / `.markdownlint.yaml`;
  - `.pre-commit-config.yaml`;
  - `scripts/check-screenshot-churn.sh`.
- **depictio-docs CI:**
  - `deploy-docs.yaml` (§1.5);
  - `update-on-release.yaml` (§1.6).
  
  No separate `mkdocs build --strict` PR check was seen in the workflows read **[to be validated]**.

## 6. Reusable for Spectio

**Copy the files as they are.** Only the names change.

| From | To (proposed) | Changes |
|---|---|---|
| `depictio-docs/dev/diagrams/sketch.py` (port, has `write_themed`) plus the glyph helpers from `dep/dev/diagrams/sketch.py` | `tools/diagrams/sketch.py` | Rename env var `DEPICTIO_VIRGIL_TTF` → `SPECTIO_VIRGIL_TTF`. Add Spectio glyphs: gate, runner, HPC node, k8s pod. Keep the seeded RNG. |
| `depictio-docs/dev/diagrams/README.md` | `tools/diagrams/README.md` | Keep the rules: commit the SVG, embed the light/dark PNG pair, semantic fill names, no braces in Virgil. |
| Virgil.ttf (from `depictio/viewer/src/assets/fonts/`) | `docs/fonts/Virgil.ttf` | Check the licence first (Excalidraw's Virgil is OFL **[to be validated]**). |
| `overrides/main.html` (font preload) | `overrides/main.html` | None. |
| `docs/javascripts/asciinema.js` + `docs/stylesheets/asciinema.css` | same paths | Rename the theme `depictio` → `spectio`. Keep the `document$` remount and the site-root logic. |
| `docs/javascripts/theme-video.js` | same path | Only if there is a hero video. |
| `hooks/shared_images.py` + `scripts/publish-shared-images.sh` + `scripts/verify-shared-assets.py` | same paths | Only once mike versions exist. Adopt it before the image folders grow. |
| `scripts/check-screenshot-churn.sh` | same path | Env var → `SPECTIO_ALLOW_SCREENSHOT_UPDATE`. |
| `dep/.github/pull_request_template.md` | `.github/pull_request_template.md` | Add "Specs touched / decision-log entry", "Diagrams regenerated (sketch / mermaid)" and "Docs build --strict passed". |

**Adapt the patterns.**
1. **`mkdocs.yml`.**
   - Copy the feature list, the markdown extensions (pymdownx set, `md_in_html`, mermaid superfence, snippets) and the plugin set: glightbox in manual mode, swagger-ui-tag, mike provider.
   - Drop the depictio-only items: neoteroi, inline-select-svg, the catalog scripts, Google Analytics.
   - Spectio's existing `mkdocs build --strict` rule must keep passing.
2. **Landing page.**
   - Keep the section skeleton: hero (logo, tagline, subtext, media) → lead → ecosystem cards (Nextflow, Snakemake, later CWL/WDL) → component cards (gates, runners, API, depictio hand-off) → demo → numbered key features → getting started.
   - Put all CSS in `docs/stylesheets/extra.css`, not inline: depictio's 2270 inline lines are the thing not to copy.
3. **Changelog.** Use the per-version block from §2 verbatim (admonition with the release theme, emoji headings, bold lead, links to the feature page, PR and commit). Generate the raw layer from commits, and curate the page by hand.
4. **OpenAPI from the release artifact.**
   - Copy `update-on-release.yaml`: import the app inside the released image, dump `app.openapi()` in a mode that needs no database, check it with jq and a minimum path count, stamp the version, open a PR.
   - This needs a "no-DB import" flag in Spectio's API from day one.
5. **Screenshots.**
   - Copy the `REGISTRY` CLI pattern from `docs_screenshots.py`: named shots, `--theme light|dark`, fixed viewport 1440×900. Output WebP light/dark pairs.
   - For the current design phase, the same registry can drive `tools/canvas/render.js` over `design/ui-canvas/*.dc.html`.
6. **Deployment.** Copy `deploy-docs.yaml`: version taken from `pyproject.toml`, `mike deploy --update-aliases $V latest stable`, `set-default stable`, then publish the shared images.

**Gaps to fill (depictio has none of these).**
- **Cast generator.** Script casts from a YAML of commands with typed delays, e.g. with `asciinema rec -c` on a fixture workflow, so casts can be recreated when the CLI changes.
- **Combined captures.** Pair a cast with a timed Playwright browser sequence, for example "`spectio run` in the terminal → gate opens in the UI". That is a natural Spectio demo.
- **PR-time docs check.** Run `mkdocs build --strict` and the Mermaid render on every PR, not only on deploy.
