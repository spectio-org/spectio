# Spectio — documentation system

Status: draft v0.1 · 2026-10-26 · author: Thomas Weber (with Claude)

**Step page:** [F5](../progress/W0/F5.md), how this spec was written and checked.

**Companion docs:**
- [`dev-environment-and-testing.md`](dev-environment-and-testing.md): CI workflows (§11), versioning and releases (§12), dev previews (§7), instance verification (§13).
- [`../playbooks/autopilot.md`](../playbooks/autopilot.md): the loop that runs the steps. This spec says what each step must leave in the docs; the autopilot says when it runs.
- [`ui-spec.md`](ui-spec.md): the boards that screenshots are taken from.

**Sources:**
- the audit of depictio's docs site, diagram toolkit and media (`docs/research/depictio-docs-system-2026-10-26.md`, depictio-docs at `1610ed8`, depictio at `0d1aa0a`);
- the tooling spike (`docs/research/spike-docs-media-tooling-2026-10-26.md`).

## 0. Decisions in brief

1. **Docs are part of the definition of done.** A step, a PR or a release is done only when:
   - its pages are written;
   - its pages are reviewed by a separate agent;
   - the site builds with `--strict`.

   "Docs later" is not an option. The documentation grows one verified step at a time.
2. **depictio's format, kept and fixed.** Spectio reuses depictio's site:
   - MkDocs Material and mike versions;
   - a landing page with hero, ecosystem cards, component cards and numbered features;
   - a curated per-version changelog;
   - hand-drawn diagrams from `sketch.py`;
   - asciinema casts and screenshots: light only while they come from the design boards (§5.1), light/dark pairs once they come from the running app *(assumed — pending Thomas, inbox #30)*.

   It also closes depictio's gaps:
   - no inline CSS: the landing page has 0 lines of `<style>`, against about 2 270 in depictio;
   - casts are generated from scripts, not recorded by hand;
   - combined terminal and browser captures;
   - a strict build and a diagram check on every PR, not only at deploy time.
3. **Writers and reviewers are different agents.**
   - `doc-writer` writes pages and the PR body.
   - `diagram-artist` draws the figures.
   - `media-capture` takes the screenshots, casts and videos.
   - `doc-reviewer` starts from a fresh context, scores the result against a rubric, and can block.

   Nobody grades their own work.
4. **Diagrams are drawings, not box charts.** Figures that explain a mechanism use the sketch toolkit:
   - pictograms (terminal, cluster node, phone, gate, bucket);
   - to-scale bars;
   - numbered captions.

   Mermaid is kept for small structural diagrams inside specs (sequence, state, ER), where text-diffability matters more than looks.

   Every step leaves at least one sketch, placed first on its Progress page, so a reviewer sees the step before reading it (§3.4).
5. **Every PR carries its docs.** The PR body has:
   - the summary;
   - the docs pages changed (with links into the preview site);
   - at least one sketch figure for `feat` and `docs` PRs that change a mechanism;
   - media for UI or CLI changes;
   - the checks.

   PRs auto-merge once required checks pass and `doc-reviewer` approves (§8).

## 1. Site structure

**Top tabs** (Material `navigation.tabs`). The order follows depictio-docs: user-facing first, everything technical under Developer. Revised 2026-10-26: the first version put the specs at the top level, which was too technical for a first visit.

| Tab | Content | Phase |
|---|---|---|
| Home | landing page (§2) | now |
| Installation | the three ways to run Spectio; "nothing to install yet" until 0.0.1 | now (short); the Python bundle from 0.0.1, the other ways with the versions that add them ([dev-env §15](dev-environment-and-testing.md#15-what-ships-in-which-version)) |
| Usage | how Spectio works: the five words, a run without gates, a run with an optional gate; later the guides | now (short), guides from M1 |
| Features | one short page per area (runs, runners, optional QC gates, administration, depictio), each with its screen designs, its status and a link to the owning spec; plus one neutral comparison page, "Spectio and other tools" | now |
| API | the headless API and the CLI in plain words; later the generated reference (§9) | now (short) |
| Developer | documentation map, Progress (§3.2), specifications, playbooks, reviews, decisions, research | now |
| Roadmap | done, now, next, ideas, with the release stages as a timeline | now |
| Changelog | curated, one block per version (§6) | now (empty until 0.0.1, [dev-env §15](dev-environment-and-testing.md#15-what-ships-in-which-version)) |

**Spectio and other tools** (`docs/features/other-tools.md`, under Features). This section owns the page. Its source of truth is the latest dated landscape research note, starting with [`landscape-2026-10-26.md`](../research/landscape-2026-10-26.md) §10. Every row has a "checked on" date and a link to its source. Wording is neutral: no pricing, no "alternative to" phrasing ([adoption note](../research/adoption-and-positioning-2026-10-26.md) §2). The page is re-checked at each release stage ([dev-env §14](dev-environment-and-testing.md#14-release-stages-and-the-10-gate)) and every quarter, each time in a new dated landscape note. Other docs (synthesis §7quater, the adoption note) link to it and keep no table of their own.

**Writing for users.** User-facing pages are short, use plain words, and say plainly what is designed and what is built. Gates are presented as optional: most pipelines run straight through.

**Theme and assets.**
- Theme `material`, with `custom_dir: overrides`. The overrides load the Outfit font and set a footer. The Virgil font used by the sketches is not committed or preloaded ([inbox #1](../reviews/inbox.md), 2026-10-26: it stays local); sketches are embedded as PNGs rendered locally *(assumed — pending Thomas, inbox #30)*.
- Logo and favicon: the emblem (`docs/assets/brand/`).
- Header, tabs and the phone drawer's title bar sit on the page surface (white in the light scheme, slate in the dark one), not on the violet primary colour, so the four-colour emblem keeps its contrast (revised 2026-10-27). On tablets and phones the header logo stays visible, after the menu button (Material hides it on narrow screens by default **[to be validated]**).
- Fonts: Outfit for headings, Inter for text, JetBrains Mono for code, as in the UI tokens.
- One stylesheet, `docs/stylesheets/extra.css`, which maps Material variables (`--md-default-fg-color`, `--md-typeset-color`, `--md-default-bg-color`, `--md-footer-bg-color`, primary and accent) to the Spectio tokens in both schemes and holds the landing-page classes. It reads `design/tokens/spectio-tokens.css` (by `@import` or a generated `:root` block) instead of copying hex values, and `tools/docs/check.py` diffs the two.
- Extra JavaScript is limited to `asciinema.js` (lazy player, §5.2).

**Material features:** `navigation.tabs`, `.sections`, `.top`, `.indexes`, `.instant`, `.tracking`, `content.code.copy`, `.annotate`, `search.suggest`, `.highlight`, `toc.follow`.

**Markdown extensions:** `admonition`, `attr_list`, `md_in_html`, `footnotes`, `def_list`, `pymdownx.details`, `.superfences` (mermaid), `.tabbed`, `.emoji` (twemoji), `.tasklist`.

**Versions with mike.**
- Each release deploys `X.Y` with the aliases `latest` and `stable`.
- `main` deploys `dev`.
- The size hook from depictio (`hooks/shared_images.py`) is not adopted yet (`hooks/` holds `lists.py` and `progress.py`). It is a D6 deliverable, due before the first mike version is deployed or when `docs/assets` passes 50 MB, whichever comes first (about 3.3 MB on 2026-10-27), because mike copies the site for every version *(assumed — pending Thomas, inbox #30)*. depictio hit about 2 GB of `gh-pages` against the 1 GB Pages limit (audit §1.5).

**Toolchain lifetime.** The Material for MkDocs build prints that Material reaches end of life on 2027-05-05, with critical fixes until then, and names Zensical, from the same team, as its successor (build notice seen 2026-10-26). Step D6 evaluates Zensical against this site: hooks, `md_in_html`, mike-style versions.

**Hosting.**
- **Dev previews (now):** Cloudflare Pages, one preview per PR, validated wave and release, each kept at its own URL, plus a `/versions` page (`dev-environment-and-testing.md` §7.1). This works while the repository is private, because the built site is uploaded directly.
- **Released versions** go there too under their `vX-Y-Z` alias. mike's in-site version selector is added once there are real releases (D6).
- **The public instance** (from the beta, EMBL Kubernetes, `dev-environment-and-testing.md` §7.4) serves its own docs.

**Analytics on the docs site.** None by default. Material's `extra.analytics` can be set per deployment with the same providers as the product (`telemetry-and-analytics.md` §4).

## 2. Landing page (`docs/index.md`)

Front matter `hide: [navigation, toc]`. The markup is HTML through `md_in_html`; every style lives in `extra.css`.

**Owner.** This section owns the public landing page; [ui-spec §4.1](ui-spec.md#41-landing-page-public-site) links here. The board `design/ui-canvas/Landing.dc.html` is kept as a marketing draft for a later release (marked so on the board) and does not specify this page: its install line (`pip install spectio && spectio serve`) is removed, and its GA4GH WES and MCP items wait for the answer to SR-010 ([inbox #17](../reviews/inbox.md)) *(assumed — pending Thomas, inbox #30)*.

**Sections, in depictio's order** (revised 2026-10-26: clearer and more visual):
1. **Centred hero** (revised 2026-10-27). First a status pill, "In design · First release, 0.0.1: …", linking to the roadmap; it replaces the old status badge below the buttons. Then the lockup: the emblem, drawn inline as SVG, sitting on the baseline of the "Spectio" wordmark. The emblem makes an overview sweep (Thomas, 2026-10-27): it turns in perspective from left to right and back, like a gaze surveying a scene, and each wedge lights up with a springy grow as the sweep passes it, on the way out and on the way back. The spring is the one of depictio's logo ([`depictio-rose.js`](https://github.com/depictio/depictio/blob/main/depictio/viewer/src/components/rose/depictio-rose.js), read 2026-10-27 at `0d1aa0a`): a damped spring sampled into a CSS `linear()` easing. The wedges spring open on load, then the sweep loops all the time. The header mark (inline SVG through `overrides/partials/logo.html`) sweeps only while hovered or focused. With `prefers-reduced-motion: reduce` nothing moves. An endless loop on the landing page has no pause control, which [WCAG 2.2 SC 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) asks for when moving content lasts more than 5 s next to other content; a pause on click is the fix if this is challenged. Then one sentence on what Spectio does (launch, monitor and relaunch runs on your cluster); one line on gates being optional and on depictio; two buttons (How it works, Roadmap); then the combined capture as a muted video with its poster and player controls, not autoplayed: play is opt-in, so moving content longer than 5 s never starts by itself ([WCAG 2.2 SC 2.2.2 Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)) and reduced-motion users get no loop.
2. **Works with.** Four groups, each with one icon before its label (Workflow engines, Pipeline catalogs, Where runs execute, Where results go), holding logo cards for Nextflow, Snakemake, nf-core, the Snakemake Workflow Catalog (card label "Snakemake catalog"), SLURM, Kubernetes and depictio. The logos are the projects' own assets, or Material's bundled Simple Icons, with a notice that they show compatibility only.
3. **How it works.** Four illustrated steps (Launch, Watch, Fix and relaunch, Results and dashboards), each with a screen design.
4. **Optional quality checks.** One box saying what a gate is for and that pipelines without gates run straight through.
5. **What is inside.** Six cards with coloured icons, linking to the Features pages.
6. **Where it stands.** The progress strip of the waves (`hooks/progress.py`), centred like the other sections, showing each wave's user-facing `public_title` from `pipeline.yaml` in plain words (no internal step names, dates or jargon); the wave detail stays on the Progress pages it links to. Then links to the roadmap, the developer docs and the changelog.
7. **Footer.** Licence, author, links, build SHA. While the repository is private, the GitHub source widget (`repo_url`) and the "Repository" link are hidden, because the GitHub API answers 404 for a private repository; `repo_url` is set only through the environment in previews until the repository is public. The "All preview versions" link (`versions/`) is rendered only on Cloudflare previews (`config.extra.preview != 'local'`), where that page exists ([dev environment §7.1](dev-environment-and-testing.md#71-static-previews-on-cloudflare-pages-now)).

**Check:**
- the page is rendered by Playwright at 1440 × 900 and at 390 × 844, light and dark;
- `doc-reviewer` looks at the PNGs;
- the phone render must not scroll horizontally;
- the render is scripted by `tools/docs/render_landing.js` (planned, R11 DOC-011), which writes the four PNGs and fails if `scrollWidth` exceeds the viewport; `tools/docs/check.py` calls it. Until it exists, the render is done by hand and recorded in the step's Progress page.

## 3. Incremental writing and verification in the loop

![Where docs are written and checked in one autopilot tick](../assets/diagrams/autopilot-loop_light.png#only-light)
![Where docs are written and checked in one autopilot tick](../assets/diagrams/autopilot-loop_dark.png#only-dark)

### 3.1 What each step kind leaves in the docs

| Step kind | Pages it must change | Figures and media |
|---|---|---|
| `review` | `docs/reviews/<round>.md`, plus its Progress page | a round map (§3.4), also embedded in the review file's summary |
| `triage` | inbox and review files (status fields), plus its Progress page | a to-scale sorting figure: findings in, accepted / rejected / inbox / assumed out (§3.4) |
| `apply` | the owning specs, `decisions/log.md`, plus its Progress page with a before/after summary per finding | a before/after sketch per mechanism changed; when none changed, a map of the specs touched with the findings applied to each (§3.4) |
| `spike` | `docs/research/spike-<name>-<date>.md`, plus its Progress page | a cast of the commands that proved it; a sketch of the setup |
| `build` (D*, T*, later code) | the guide or reference page for what was built, the owning spec if behaviour was decided, plus its Progress page with the `CODE` report line of the `review-code` skill and a link to `docs/reviews/code/<step>.md` | a sketch for each new mechanism; a cast for each new CLI flow; screenshots for each new screen; a combined capture for a CLI-to-UI flow |
| `plan` | `docs/plans/<id>.md`, plus its Progress page | a sketch of the milestone's architecture slice |
| `release` | the changelog block (§6) | the release's hero figure |
| `foundation` (wave W0 only) | its Progress page, written after the fact from the commits and the evidence kept in the session; the owning specs it changed | as for `build`; a figure or media that is not made yet is listed as a follow-up with the step that will make it |

### 3.2 Progress pages (`docs/progress/<wave>/<step>.md`)

**One page per step,** written by `doc-writer` *during* the step, not after. It has a fixed shape:

```markdown
---
step: T3
wave: W3
status: done            # running | done | blocked
pr: 42
review: approve         # approve | changes | block
review_score: 13/14
review_ref: ".autopilot/journal.md, tick 5"
---
# T3 · Local SLURM with sind

!!! success "Done 2026-11-02 · PR #42 · 3 findings filed"

## What changed
## Why (link to the prompt and the decision)
## Evidence
## Figures and media
## Findings and open questions
```

- **What changed:** short bullets with links to the pages and files.
- **Evidence:** commands run, their results, and the exit check.
- **Figures and media:** the sketch pair, cast or screenshots.
- **Findings and open questions:** links to the review file and the inbox.

The Progress tab index is generated by the MkDocs hook `hooks/progress.py` from `docs/playbooks/pipeline.yaml` and `.autopilot/state.json`: one row per step, ordered by wave, linking the step's Progress page when it exists *(assumed — pending Thomas, inbox #30)*. The landing-page status strip uses the same data.

### 3.3 The docs gate (run by autopilot after every step, and by CI on every PR)

A step reaches `done` only when all of these pass:

1. `mkdocs build --strict` (broken links and anchors fail).
2. Every Mermaid block renders (`check_mermaid()` in `tools/docs/check.py`, which extracts every fenced `mermaid` block from `docs/**/*.md` and renders it with `npx -y @mermaid-js/mermaid-cli@11 -p <puppeteer config>`, the config adding `--no-sandbox` for GitHub runners and root sessions) *(assumed — pending Thomas, inbox #30)*.
3. **Diagram freshness:** every `tools/diagrams/*.py` script re-run gives byte-identical SVGs. The seeded RNG makes this testable; a figure whose script changed without its output, or the reverse, fails. Only SVGs are compared (the scripts run with `--no-png`). PNGs are rendered locally, because the Virgil font is not committed ([inbox #1](../reviews/inbox.md)): rendering needs `SPECTIO_VIRGIL_TTF` (default `docs/fonts/Virgil.ttf`) and Python `playwright`, and `docs/assets/media.yaml` says so for each diagram generator. `tools/diagrams/sketch.py` fails when the font is missing unless `--allow-fallback-font` is passed, so no figure ships with a silent fallback font.
4. **Media manifest:** every screenshot, cast and video referenced from a page exists and is listed in `docs/assets/media.yaml` with its generator command. The gate scans every `docs/**/*.md` for `data-cast`, `src` and `poster` attributes and resolves each target, as well as comparing the asset folders with the manifest. The churn guard (`tools/media/check_churn.sh`) rejects a mass change unless `SPECTIO_ALLOW_SCREENSHOT_UPDATE=1`.
5. **Required pages for the step kind** (§3.1) changed, derived from the step's `kind` in `docs/playbooks/pipeline.yaml` and its `outputs` in `.autopilot/state.json`; the Progress page front matter is valid; and the page has the `!!!` admonition line and all five §3.2 headings (What changed, Why, Evidence, Figures and media, Findings and open questions). A `done` page embeds its sketch pair (§3.4).
6. **`doc-reviewer` verdict** ≥ `approve` (§4.2). The tick appends the verdict line (`<step>: doc-reviewer <verdict> n/14`, plus the required changes) to `.autopilot/journal.md`. The Progress page front matter records `review: approve | changes | block`, `review_score: n/14` and `review_ref` (the journal tick that holds the line). `check_progress` requires `review_score` and `review_ref` on every new `status: done` page. Pages done before 2026-10-27 whose score is not in the journal carry `review_score: unrecorded` until they are next edited, when they are reviewed again *(assumed — pending Thomas, inbox #30)*.
7. **Size budget:** at most 5 MB of new media per PR (checked against the base branch in CI), videos ≤ 3 MB and ≤ 30 s each. GIF previews for PR bodies are generated on demand outside `docs/assets/` and are not committed.

**Not yet run by `tools/docs/check.py` (2026-10-27):** the page scan of item 4, the required-pages check of item 5, and three of the five headings (only What changed and Evidence are checked). Until they are, a `0 failure(s)` result does not cover them (R11 DOC-002; proposed spike `spikes/docs-gate-coverage/`).

If the gate fails, the step goes back to `doc-writer` with the reviewer's notes. After two failed revisions, the step is `blocked`, with an inbox entry.

### 3.4 A sketch for every step

Since 2026-10-27 every step leaves at least one sketch pair (light and dark, `tools/diagrams/`), whatever its kind ([decision log](../decisions/log.md), 2026-10-27). The figure makes the step quick to review: Thomas and the reviewers see what the step did, and where its findings land, before reading the text.

- **Where.** The figure is the first thing under the Progress page's `!!!` line, before **What changed**, and is listed again under **Figures and media**. A review round also embeds it at the top of its review file's summary.
- **What it shows,** by step kind (§3.1 lists the minimum):
  - `review`: the scope the round walked — journeys as numbered steps, specs or boards — drawn as pictograms, with each blocker and major pinned where it hits, labelled by finding ID;
  - `triage`: bars to scale from the round's real counts;
  - `apply`: before and after, side by side, for the mechanism that changed;
  - `spike`, `build`, `plan`: the setup, the new mechanism or the architecture slice.
- **How.** One script per figure in `tools/diagrams/`, drawn by `diagram-artist` in the Excalidraw-like sketch style (§0.4, `tools/diagrams/README.md`). Counts come from the step's real outputs, never from memory.
- **Checked.** `check_progress` fails a `done` Progress page that does not embed a `docs/assets/diagrams/*_light.png#only-light` and `*_dark.png#only-dark` pair. Pages finished before the rule are listed in `FIGURE_EXEMPT` in `tools/docs/check.py`; a page leaves the list when it gets its figure.

## 4. Writers and reviewers

### 4.1 Agents (`.claude/agents/`)

| Agent | Writes | Tools | Model |
|---|---|---|---|
| `doc-writer` | Progress pages, guide and reference pages, PR bodies, changelog drafts | Read, Grep, Glob, Edit, Write, Bash | opus |
| `diagram-artist` | `tools/diagrams/<figure>.py` and its outputs | Read, Write, Edit, Bash | opus |
| `media-capture` | entries in `tools/media/` (shots registry, cast scripts, combo scripts), `docs/assets/` outputs, `media.yaml` | Read, Write, Edit, Bash | sonnet |
| `doc-reviewer` | nothing in the docs; returns a verdict and findings | Read, Grep, Glob, Bash | opus |

**Writers:**
- **Sources.** Writers work from the step's actual outputs (diff, logs, test reports), never from the prompt alone.
- **Style.** Writers follow the repository style:
  - plain English;
  - short sentences;
  - lists for scanning, tables for comparing;
  - every external fact sourced, or marked **[to be validated]**.

**`doc-reviewer`:**
- runs with a fresh context;
- receives only the changed pages, the step's outputs and this spec, not the writer's reasoning.

### 4.2 Review rubric

Each criterion is scored 0–2, with a one-line justification.

| Criterion | 2 means |
|---|---|
| Accuracy | every claim matches the diff, the logs or a cited source; commands were run |
| Completeness | the pages §3.1 requires are present; a newcomer could repeat the step |
| Ownership | the topic changed in its owning spec only; other pages link to it |
| Clarity | scannable; a page title says what it is; no unexplained jargon |
| Figures | the step's sketch (§3.4) comes first and lets a reader grasp the step without the text; a mechanism is drawn with pictograms, not boxes; labels legible in light and dark (reviewer opens the PNGs) |
| Media | screenshots match the current boards; casts replay; videos play and are short |
| Navigation | the page is reachable from the nav, the Progress index and its spec |

**Verdict:**
- `approve` when every criterion is ≥ 1 and the total is ≥ 11 / 14;
- `changes` otherwise;
- `block` for any inaccuracy that would mislead a user, or a secret or personal data in media.

## 5. Media

### 5.1 Screenshots

**The registry.**
- `tools/media/shots.py` is a registry of named shots, like depictio's `docs_screenshots.py`.
- It has `list` and `run --shot NAME --theme light|dark` commands.
- The viewport is 1440 × 900, or 1440 × 1180 for tall pages, plus 390 × 844 for phone shots.

**Sources, by phase:**
- **Design phase:** shots are rendered from `design/ui-canvas` boards with `tools/canvas/render.js`. The boards have no dark variant, so design-phase shots are **light only**. Names are substituted from `tools/media/fixtures.yaml` before rendering, so no real name, path or cluster appears (§5.5).
- **Implementation:** the same names are taken from the running app with Playwright, against the seeded demo data.

**Pairs and embedding.**
- Shots are saved as WebP. Design-phase shots are light only (see Sources above; [decision log, 2026-10-26, first independent docs review](../decisions/log.md#2026-10-26-first-independent-docs-review-w0-pages-and-landing-page)). In dark mode the landing page dims them with a CSS filter in `extra.css` so they do not glare. Light/dark pairs come with app shots, or earlier if the boards get a dark variant (proposed spike `spikes/dark-boards/`); there is no dark-twin check in the docs gate until then *(assumed — pending Thomas, inbox #30)*.
- Pairs, when they exist, are embedded with `#only-light` / `#only-dark`, inside a link that opens the full image. Pages with many shots set `glightbox: true`.

### 5.2 Terminal casts

**Generated, not recorded.**
- Each cast has a script, `tools/media/casts/<name>.yaml`, with:
  - title and size;
  - the steps (commands, narration comments, typing speed);
  - output trimming.
- `tools/media/cast.py` runs the commands for real and writes an asciinema v2 file with synthetic, stable timestamps.
- When the CLI changes, casts are regenerated in CI and the docs gate catches casts that no longer replay.

**Embedding:**
- markup: `<div class="asciinema-cast" data-cast="assets/casts/<name>.cast"></div>`;
- player: `asciinema.js` lazy-loads asciinema-player 3.17.0 and remounts on Material's instant navigation;
- theme: `spectio`.

**Tool choice.** asciinema is preferred to VHS GIFs: the text stays selectable and the files are small. VHS can be added for GIFs in the README if needed.

**Replayed casts.** A cast may replay a spike's recorded output instead of running the tools again, when they cannot run where casts are generated (for example sind and kind in a cloud session, D2). Then:
- the cast script names its recorded-log source (file and commit, for example `spikes/cloud-env/LOG.md` at `217a92c`);
- its title says "replayed";
- its `docs/assets/media.yaml` entry has `kind: cast-replay`;
- the page that embeds it says it is a replay.

The CI regeneration above does not apply to replayed casts and cannot detect drift; a replayed cast is regenerated when its log changes.

### 5.3 Browser videos

Playwright `record_video` captures a scripted UI flow (open run → open gate → decide):
- WebM from Playwright, converted to MP4 (H.264) for compatibility, plus a GIF preview of at most 4 MB at 10 fps for PR bodies (generated outside `docs/assets/`, not committed);
- at most 30 s, 1280 × 720.

### 5.4 Combined terminal and browser captures

**What it shows.** One video shows a CLI action and its effect in the UI side by side. For example, `spectio run … --gate qc` in the terminal, then the gate opening in the browser and being approved, then the terminal resuming.

**How it is made.**
- `tools/media/combo.py` drives a Playwright page with two panes:
  - the asciinema player playing the cast;
  - the browser pane, showing the app (or boards in the design phase) at timestamps set in `tools/media/combos/<name>.yaml`.
- The page is recorded with Playwright video and converted with ffmpeg.
- Captions come from the same YAML.

depictio has no equivalent (audit §4.4).

### 5.5 Data hygiene

- Media use only demo data and fixture users. No real emails, tokens, hostnames or paths.
- `doc-reviewer` checks the frames, and `block`s on a leak.
- Generators run against the seeded demo instance, which has fixed names (`demo-hpc`, `alice@example.org`).

## 6. Changelog

**Two layers, as in depictio.**
- **Layer 1, raw:** `release-please` writes `CHANGELOG.md` from Conventional Commit titles. Its output becomes the GitHub release body (`dev-environment-and-testing.md` §12).
- **Layer 2, curated:** `docs/changelog/index.md`. When the release PR opens, `doc-writer` drafts the new block from the merged PR bodies, and `doc-reviewer` reviews it in the release PR.

**Block format** (one per version, newest first, depictio's shape):

```markdown
## [v0.3.0](https://github.com/weber8thomas/spectio/releases/tag/v0.3.0) · 2026-12-04

!!! success "Minor: gates on SLURM runs, decided from a phone"

### ✨ New
* **Stop at a QC gate on SLURM**: the runner pauses after `qc` and waits for a decision.
  See [Gates](../guides/gates.md#slurm) ([#57](https://github.com/weber8thomas/spectio/pull/57), [a1b2c3d](https://github.com/weber8thomas/spectio/commit/a1b2c3d)).

### 🚀 Improved
### 🐛 Fixed
### ⚠️ Breaking
### 📦 Images and packages
```

- **Admonition type by release size:** `success` for a minor release, `info` for a patch, `warning` for a release with breaking changes.
- **Each bullet:**
  - a bold lead that says what users can now do;
  - one sentence;
  - links to the feature page, the PR and the commit.
- **Breaking changes** come with a migration note.
- **The 📦 Images and packages section is generated.** Its list comes from the `docker/metadata-action` output and the published package list of the release run, and each entry is checked with `docker manifest inspect` before the notes are published. depictio's notes list `ghcr.io/depictio/depictio:{version,latest,stable,edge}`, which are never published (`changelog_generator.sh:29-32` vs `build-images.yaml:280-282`).

## 7. Pull requests

### 7.1 Template (`.github/pull_request_template.md`)

The template keeps depictio's sections and adds Spectio's own. depictio's sections:
- summary;
- type;
- related issue;
- how it was tested;
- checklist.

Spectio adds:
- **docs:** pages changed, with preview links (Cloudflare preview of the PR);
- **figures:** sketch pairs embedded;
- **media:** a GIF or a link to the MP4;
- **specs touched and decision-log entry;**
- **review verdict** from `doc-reviewer`.

### 7.2 Generated body

**Generation.** `doc-writer` writes the PR body from the step's Progress page.

**Figure links.** Figures are embedded with `raw.githubusercontent.com` URLs pinned to the PR head SHA. A pinned URL keeps showing the figure after the branch is rebased; while the repository is private, GitHub serves these URLs only to readers who have access.

**Example:**

```markdown
## Summary
Local SLURM cluster with sind for scenario tests (T3).

## Docs
- [Progress · T3](https://pr-42.spectio.pages.dev/progress/W3/T3/) · [Dev environment §5](https://pr-42.spectio.pages.dev/specs/dev-environment-and-testing/#5-...)

## How it works
![sind topology](https://raw.githubusercontent.com/weber8thomas/spectio/<sha>/docs/assets/diagrams/sind-topology_light.png)

## Evidence
`pytest tests/slurm -q` → 14 passed · scenarios on sind: 11/11 · [cast](https://pr-42.spectio.pages.dev/assets/casts/sind-up.cast)

## Checks
- [x] docs build --strict · [x] mermaid · [x] diagrams fresh · [x] media manifest · [x] doc-reviewer: approve (13/14)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Preview links.** They point at the PR's Cloudflare preview (`https://pr-<n>.spectio.pages.dev/…`). `previews.yml` comments them on the PR, together with the "Open in Codespaces" link.

### 7.3 PR checks (`docs.yml`, required)

1. strict build;
2. Mermaid render;
3. diagram freshness;
4. media manifest and churn guard;
5. PR body lint: the required sections are present; `feat` and `docs` PRs that touch `docs/specs/` or `tools/` have at least one figure, unless labelled `no-figure` with a reason;
6. Conventional Commit title.

## 8. Auto-merge

**Policy.**
- A PR merges automatically (squash, through GitHub's native auto-merge) when:
  - all required checks pass: `docs-gate` and `pr-body` (§7.3), and `ci-ok`, the aggregator job of `ci.yml` that covers the pipeline workflows the PR touches (`dev-environment-and-testing.md` §11) *(assumed — pending Thomas, inbox #26)*;
  - its `doc-reviewer` verdict is `approve`, posted as a PR review by the bot account;
  - it has no `needs-human` label.
- **On `autopilot/integration`:** auto-merge is always on.
- **On `main`:** auto-merge is on only when the repository variable `AUTOMERGE_MAIN` is `true`. Thomas sets that variable, which is the switch from "humans merge to main" to "CI merges to main".

**Never auto-merged:**
- `human_gate` steps;
- a release PR at 1.0.0 or above (the 1.0 gate, `dev-environment-and-testing.md` §14). A 0.x release PR auto-merges like the others once `AUTOMERGE_MAIN` is `true`. The autopilot merges one at the end of a milestone or of a wave that changed the product, not after every `feat`;
- PRs that change `.github/workflows/`, `.claude/settings.json`, auth or secrets code, or `pipeline.yaml` statuses.

**Who configures it.** Thomas sets up branch protection and the auto-merge setting once, with the `gh` commands in `docs/playbooks/autopilot.md` §8. Agents cannot change repository settings or their own permissions.

## 9. Generated reference (from M1)

**API reference.**
- **Generation.** depictio's release workflow is copied: import the app inside the released image in a mode that needs no database, dump `app.openapi()`, check it with `jq` and a minimum path count, stamp it with the version, and open a docs PR (audit §1.6). The docs PR is opened with the GitHub App token of `dev-environment-and-testing.md` §12, so its checks run; a PR opened with `GITHUB_TOKEN` gets no CI *(assumed — pending Thomas, inbox #26)*.
- **Requirement.** This needs the no-database import mode in `spectio-server` from day one (`architecture-plugins-and-packaging.md` §6).

**CLI reference.** Generated from the Typer command tree (`mkdocs-typer` or a small generator).

**Configuration reference.** Generated from the Pydantic settings models:
- one table per plugin kind;
- for each setting: environment variable, TOML key, default and description.

## 10. What "verified" means for docs

A docs claim is verified when one of these holds:
- the command in it was run in the step and its output is in the Evidence section or a cast;
- the screenshot was generated from the current board or app build;
- an external fact links its source.

`doc-reviewer` samples at least three claims per page and re-runs them when they are commands that run in under a minute.

**Audits of external repositories** (depictio and others) cite the tag and the SHA (for example `v1.19.2` / `0d1aa0a`), never the SHA alone, and record `git archive <sha> | sha256sum` in the audit note, so a cited file can be found again after a history rewrite. depictio has rewritten its default branch (tag `backup-before-author-rewrite`, 2026-08-04, and `backup/pre-*` tags; R8b DEP-T-031).
