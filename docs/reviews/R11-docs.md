# R11 · Documentation review

Round: R11 (2026-10-27). Branch `autopilot/integration`.
- **Question:** does the documentation site do what [`documentation-system.md`](../specs/documentation-system.md) asks, and can that spec be implemented with the tools in `tools/docs`, `tools/diagrams` and `tools/media`?
- **Reviewers:** `doc-reviewer` (fresh context, whole site against the spec, rubric §4.2) and `ux-reviewer` (the public landing page, `docs/index.md`).
- **What was built:** the site, with `uvx --with mkdocs-material mkdocs build --strict` (exit 0, 0 warnings). `python3 tools/docs/check.py` and `tools/media/check_churn.sh` both pass.
- **What was rendered:**
  - the landing page at 1440×900 and 390×844, light and dark, with Playwright against the built site (full pages, folds, crops, focus captures);
  - the `Landing.dc.html` board;
  - every figure PNG (light and dark);
  - frames from `gate-review.mp4` (5 frames) and the 9 screenshots;
  - the four casts (replayed);
  - on the Progress pages of W0, three commands per page re-run (rubric §4.2).
- **What the merge checked:** every major finding was reproduced in the repository at merge time (commit ancestry, `check.py` source, front matter, journal, `docs/index.md`, `extra.css`, `docs/assets/shots/`, a dark render crop). None was dropped.
- **Scope rule:** these are findings, not changes. Pages, specs and `mkdocs.yml` are untouched; triage and `/apply-findings` decide.

**Status of the round: triaged (TRIAGE1, 2026-10-27): 22 accepted, 0 rejected, 5 inbox (5 assumed)**

**Step page:** [R11](../progress/W1/R11.md)

Format: [`README.md`](README.md). Prefix `DOC` (both reviewers). Reviewer IDs (DOC-101…113 from `doc-reviewer`, DOC-201…214 from `ux-reviewer`) were renumbered into one sequence; the original ID is given under each finding.

## Summary

| Severity | Count |
|---|---|
| Blocker | 0 |
| Major | 6 |
| Minor | 21 |
| **Total** | **27** |

Reviewers reported 27 findings (doc-reviewer 3 majors and 10 minors, ux-reviewer 3 majors and 11 minors). Two overlaps were merged inside surviving findings, not removed: the `versions/` footer link (DOC-113 and DOC-212 → DOC-013) and the incoherent hero story (DOC-205 hero part → DOC-008). Dropped as not reproducible: 0.

**The five findings that matter most:**
1. **DOC-001:** two owners describe two different public landing pages. The `Landing.dc.html` board and ui-spec §4.1 advertise `pip install spectio`, MCP and GA4GH WES; `docs/index.md` says "nothing to install yet".
2. **DOC-002:** the docs gate reports "0 failure(s)" for checks it does not run: media referenced from pages, required pages per step kind, three of the five Progress sections.
3. **DOC-003:** `review: approve` is self-declared. No score, rubric or verdict is stored anywhere, and the journal has no entries.
4. **DOC-004:** the W0 Progress pages cite commits that are not in the history of `autopilot/integration` or `main`, so their evidence cannot be repeated.
5. **DOC-005:** in dark mode the landing shows five light-only screens (four step images and the video poster). The spec promises light/dark pairs that the tooling cannot produce yet.

## Findings table

| ID | Severity | Title | Where |
|---|---|---|---|
| DOC-001 | major | Two owners describe two different public landing pages | ui-spec §4.1, `Landing.dc.html`, documentation-system §2, `docs/index.md` |
| DOC-002 | major | The docs gate does not run three checks §3.3 lists | `tools/docs/check.py`, documentation-system §3.3.4, §3.3.5 |
| DOC-003 | major | `review: approve` is self-declared and leaves no record | 15 Progress pages, `.autopilot/`, documentation-system §3.3.6, §7.2 |
| DOC-004 | major | W0 Progress pages cite commits outside the branch history | `docs/progress/W0/F1.md`…`F7.md` |
| DOC-005 | major | Dark theme shows light-only screens on the landing | `docs/index.md`, `tools/media/shots.py`, documentation-system §0.2 |
| DOC-006 | major | The hero video autoplays and loops with no pause and ignores reduced motion | `docs/index.md`, `extra.css`, documentation-system §1 |
| DOC-007 | minor | documentation-system.md specifies tools and settings that do not exist | documentation-system §1, §3.2, §3.3.2 |
| DOC-008 | minor | The hero video is stale, tells three unrelated stories, and its narration presents Spectio as running | `gate-review.mp4`, `synthetic-gate.yaml` |
| DOC-009 | minor | The cloud-env cast is a stub replay, which the spec does not allow for | documentation-system §5.2, `tools/media/README.md` |
| DOC-010 | minor | PNG figures escape the freshness check and depend on an uncommitted font | `check.py`, `sketch.py`, `media.yaml` |
| DOC-011 | minor | The §2 landing render check has no script | documentation-system §2, `tools/docs/` |
| DOC-012 | minor | Theme colours drift from `spectio-tokens.css`; dark headings dimmer than body | `extra.css` |
| DOC-013 | minor | Header source widget and footer links point to resources that 404 | `mkdocs.yml`, `overrides/main.html` |
| DOC-014 | minor | F3 and F1 describe replaced infrastructure as current | `docs/progress/W0/F3.md`, `F1.md` |
| DOC-015 | minor | F5 describes the landing page as it was before add6838 | `docs/progress/W0/F5.md` |
| DOC-016 | minor | D2 says its figure and cast are not committed and its spike branch is not pushed | `docs/progress/W1/D2.md` |
| DOC-017 | minor | Figure defects: label collision, low-contrast dark legend, outdated merge step | `tools/diagrams/cloud_env.py`, `gate_resume.py`, `autopilot_loop.py` |
| DOC-018 | minor | Steps 3 and 4 are illustrated by screens that do not show what the text says | `docs/index.md` |
| DOC-019 | minor | Screen designs on the landing are unreadable on phone | `docs/index.md` |
| DOC-020 | minor | No accessible h1, and a doubled document title | `extra.css`, `docs/index.md`, `overrides/main.html` |
| DOC-021 | minor | Progress strip links have no meaningful name on phone; bars have no text alternative | `hooks/progress.py`, `extra.css` |
| DOC-022 | minor | "Where it stands" breaks the layout and uses internal jargon | `extra.css`, `hooks/progress.py` |
| DOC-023 | minor | Low-contrast icons: the dark SLURM mark and the amber tiles | `extra.css` |
| DOC-024 | minor | The keyboard focus ring is barely visible on cards | `extra.css` |
| DOC-025 | minor | Phone footer has 4 px gutters and 20 px link targets | `extra.css` |
| DOC-026 | minor | "What is inside" makes a 1 000 px single column on phone | `extra.css` |
| DOC-027 | minor | Map navigation gaps | `docs/map.md` |

## Ownership and the landing page

### DOC-001 · major · Two owners describe two different public landing pages

*Reviewer ID: DOC-201.*

- **Where:** [`ui-spec.md`](../specs/ui-spec.md) §4.1 and `design/ui-canvas/Landing.dc.html`, against [`documentation-system.md`](../specs/documentation-system.md) §2 and `docs/index.md`.
- **Evidence:**
  - ui-spec §4.1 asks for "Get started" / "Docs" / GitHub buttons, three pillars, a works-with strip that lists GA4GH WES, and three steps: "install the server, connect a runner, launch from the browser".
  - `Landing.dc.html` l.58 has a button "Install in one line"; l.61 shows `pip install spectio && spectio serve`; l.182 lists `GA4GH WES` and `MCP` in the works-with strip; l.189-190 give the install and runner commands as steps.
  - documentation-system §2 and `docs/index.md` have different content: buttons "How it works" / "Roadmap" (l.10), four steps Launch, Watch, Fix and relaunch, Results and dashboards (l.57-84), and the badge "Design phase · nothing to install yet · first release planned as 0.1" (l.11).
  - Confirmed at merge time by reading both files.
- **Problem:**
  - It is not clear which page is the public landing.
  - The board offers an install command that does not exist and a PyPI name nobody has checked **[to be validated]**.
  - This breaks "one owner per topic". SR-010 (R1) covers only the WES item.
- **Proposal:**
  - documentation-system.md §2 owns the public landing.
  - ui-spec §4.1 is reduced to one line that links to it.
  - `Landing.dc.html` is either retired, or marked "post-0.1 marketing draft" with the install line, WES and MCP removed until they ship.
- **Found by:** ux-reviewer
- **Status:** inbox, assumed: documentation-system §2 owns the public landing; ui-spec §4.1 becomes a one-line link to it; `Landing.dc.html` is kept, marked "post-0.1 marketing draft", with the install line removed, and its WES and MCP items follow the answer to SR-010 — pending Thomas (TRIAGE1, 2026-10-27)

## The docs gate and its records

### DOC-002 · major · The docs gate does not run three checks §3.3 lists

*Reviewer ID: DOC-102.*

- **Where:** `tools/docs/check.py` `check_media` (l.118-146) and `check_progress` (l.149-170); [`documentation-system.md`](../specs/documentation-system.md) §3.3 items 4 and 5.
- **Evidence:**
  - §3.3.4: "every screenshot, cast and video **referenced from a page** exists and is listed in `docs/assets/media.yaml`". `check_media` compares the files in the asset folders with `media.yaml` and never parses pages, so a missing file referenced by `data-cast="…"` or `<video src>` passes. mkdocs `--strict` does not check raw-HTML attributes either.
  - §3.3.5: "Required pages for the step kind (§3.1) changed". Nothing in `check.py` compares a step's changed files with the §3.1 table.
  - `check_progress` loops over `("## What changed", "## Evidence")` only (l.167), not the other three §3.2 sections or the `!!!` admonition line.
  - Confirmed at merge time by reading `check.py`.
- **Problem:** the gate reports "0 failure(s)" for checks it does not run. A broken cast or a missing review file would ship.
- **Proposal:**
  - In `check_media`, scan `docs/**/*.md` for `data-cast`, `src` and `poster` and resolve each one.
  - Add a `required-pages` check driven by `pipeline.yaml` kinds and the step's `outputs` in `state.json`.
  - Check all five §3.2 headings and the `!!!` line.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-003 · major · `review: approve` is self-declared and leaves no record

*Reviewer ID: DOC-103.*

- **Where:** front matter of all 15 Progress pages; `.autopilot/journal.md`; `.autopilot/state.json` `notes`; [`documentation-system.md`](../specs/documentation-system.md) §3.3.6, §7.2.
- **Evidence:**
  - Every page in `docs/progress/W0/` and `docs/progress/W1/` has `review: approve`; `state.json` notes for R1…R9 say "docs gate pass; doc-reviewer approve".
  - No score, rubric or reviewer output is stored anywhere (`grep -rn "review_score\|13/14" .autopilot docs/progress` finds nothing).
  - `journal.md` is 3 lines: its header only, with no tick entries, although W1 finished 8 steps.
  - §7.2's example shows "doc-reviewer: approve (13/14)".
  - `check_progress` (l.165-166) accepts any page whose writer sets `review: approve`.
  - Confirmed at merge time.
- **Problem:** nobody can tell whether a page was reviewed, by whom, or with what score. This defeats "nobody grades their own work" (§0.3).
- **Proposal:**
  - Store `review_score: n/14` and a pointer to the stored verdict (for example `.autopilot/reviews/<step>.txt` or the journal line) in front matter.
  - Make `check_progress` require both when `status: done`.
  - Have autopilot append the verdict line to `journal.md`.
- **Found by:** doc-reviewer
- **Status:** inbox, assumed: the verdict is stored as a `.autopilot/journal.md` line; front matter gets `review_score: n/14` and `review_ref`, required by `check_progress` for new `status: done` pages; the 15 existing pages are grandfathered as `review_score: unrecorded` until next edited — pending Thomas (TRIAGE1, 2026-10-27)

## Progress pages

### DOC-004 · major · W0 Progress pages cite commits outside the branch history

*Reviewer ID: DOC-101.*

- **Where:** `docs/progress/W0/F1.md` (admonition l.10, What changed, Evidence l.40-49), `F2.md`…`F7.md` (admonitions l.10), `F5.md` Evidence (`--base 7a0b51c`, l.39-43).
- **Evidence:**
  - `git merge-base --is-ancestor` on b32f739, adacfdf, 7a0b51c, b2687d8, 0e5b97a and 8d74979: none is an ancestor of `HEAD` or `origin/main`. `git branch -a --contains` lists only `origin/claude/foundations-2026-10-26` and its release-please branch.
  - The message of 9185808 ("chore: initial import of the Spectio design phase") marks the squash.
  - F1's Evidence shows `git log --oneline | tail -3` → `7a0b51c / adacfdf / b32f739`. Re-run today it prints `a5609f5 / 4777f74 / 9185808`.
  - Reproduced at merge time.
- **Problem:** a newcomer cannot follow or repeat the evidence. The one command F1 shows no longer gives its printed output.
- **Proposal:** add one line to each W0 page: "History was squashed into `9185808`; the SHAs below are on `claude/foundations-2026-10-26`." Link the SHAs to that branch. Re-run F1's `git log` and update the expected output.
- **Found by:** doc-reviewer
- **Status:** inbox, assumed: each W0 page notes that history was squashed into `9185808` and keeps the old SHAs as plain text marked pre-squash (no link to the branch inbox #5 may delete); F1's `git log` is re-run and its output updated — pending Thomas (TRIAGE1, 2026-10-27)

### DOC-014 · minor · F3 and F1 describe replaced infrastructure as current

*Reviewer ID: DOC-104.*

- **Where:** `docs/progress/W0/F3.md` (What changed, Workflows; Figures, follow-up; Findings, "Not proven yet"); `F1.md` Findings ("Pushing").
- **Evidence:**
  - F3 says "`staging.yml`: deploys over the tailnet, checks the public Funnel URL". `.github/workflows/` has no `staging.yml`; it has `previews.yml` (commit a5609f5, "dev previews on Cloudflare Pages … instead of a staging VM").
  - F3 says "the CI workflows have not run on GitHub; the session has no push access". Commits d1852e7 and f72e1e1 record CI fixes on GitHub runners and live preview deploys.
  - F1 says "Work is delivered as a git bundle", but the branches are on origin.
- **Problem:** a reader looks for files and limits that are gone.
- **Proposal:** add a dated "Superseded" admonition to F3 that links [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §7 and the log entry. Strike the push and bundle notes in F1. (The map and spec side is already SR-044.)
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-015 · minor · F5 describes the landing page as it was before add6838

*Reviewer ID: DOC-105.*

- **Where:** `docs/progress/W0/F5.md`, What changed, "Site".
- **Evidence:** F5 says "a new landing page (hero video, ecosystem and component cards, numbered ideas, the gate figure, a cast, the progress strip)". `docs/index.md` today has no figure and no `asciinema-cast`. Its sections follow §2: hero, Works with, How it works, optional gate box, What is inside, Where it stands.
- **Proposal:** describe the current landing sections, or say "first version; revised in add6838 (§2, revised 2026-10-26)".
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-016 · minor · D2 says its figure and cast are not committed and its spike branch is not pushed

*Reviewer ID: DOC-106.*

- **Where:** `docs/progress/W1/D2.md`, What changed ("Figure and cast, not committed yet"; "`spike/cloud-env` … not pushed").
- **Evidence:** `cloud_env.py`, the cloud-env SVG/PNG files, `cloud-env.yaml`/`.cast` and the `media.yaml` entry are all in 5d8ef54 on `autopilot/integration`. `git branch -r --contains 217a92c` → `origin/spike/cloud-env`.
- **Proposal:** say they are committed in 5d8ef54. Say the evidence (`LOG.md`, fixtures) is on `origin/spike/cloud-env` at 217a92c, with a link.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

## Landing page: media and accessibility

### DOC-005 · major · Dark theme shows light-only screens on the landing

*Reviewer ID: DOC-203.*

- **Where:** `docs/index.md`: the video poster (l.15) and the step images (l.60, 69, 78, 87). Renders: `landing-desktop-dark.png` (y≈1800-4400) and `landing-phone-dark.png`.
- **Evidence:**
  - Only `*_light.webp` files exist in `docs/assets/shots/` (9 files, no `_dark`).
  - `tools/media/shots.py` docstring: "The boards have no dark variant yet, so `--theme dark` is skipped for them".
  - [`documentation-system.md`](../specs/documentation-system.md) §0.2 promises "light/dark screenshot pairs" (l.29), and §5 says "Shots are saved as WebP light/dark pairs" (l.235).
  - In dark mode each 689×565 white image sits on `#11121F`. Confirmed at merge time on the dark desktop crop of "How it works".
- **Problem:** heavy glare and a broken visual hierarchy in dark mode. The spec promises pairs that the tooling cannot produce yet, and nothing records that gap.
- **Proposal:**
  - Short term: in `extra.css`, add `[data-md-color-scheme="slate"] .sp-step img, .sp-hero2__media video { filter: brightness(.85); border-color: var(--sp-line); }`, and add a sentence to documentation-system §0.2 that records the gap.
  - Proper fix: give the boards a dark variant through `:root[data-theme="dark"]` in `spectio-tokens.css` plus a theme switch in `render.js`, then embed `…_light.webp#only-light` / `…_dark.webp#only-dark` pairs. Material hides these by `src` suffix, which also works on raw `<img>` **[to be validated]**.
  - `tools/docs/check.py` flags any landing shot that has no dark twin.
- **Found by:** ux-reviewer
- **Status:** inbox, assumed: short-term dimming in `extra.css`; documentation-system §0.2 and §5 point to the logged light-only rule of §5.1 instead of promising pairs; no dark-twin check yet; dark boards left to the proposed `spikes/dark-boards/` — pending Thomas (TRIAGE1, 2026-10-27)

### DOC-006 · major · The hero video autoplays and loops with no pause and ignores reduced motion

*Reviewer ID: DOC-202.*

- **Where:** `docs/index.md` l.15-17 (`<video autoplay muted loop playsinline …>`). Crop: 1440×900 fold, y 636-900, x 127-1313.
- **Evidence:**
  - Playwright with `reducedMotion:'reduce'` reports `{autoplay:true, paused:false, controls:false, dur:24.6}`.
  - No `prefers-reduced-motion` rule in `docs/stylesheets/`, `design/tokens/` or `overrides/` (grep at merge time: no match).
  - [`documentation-system.md`](../specs/documentation-system.md) §1 limits extra JavaScript to `asciinema.js` (l.80), so a pause control cannot be added without a spec change.
- **Problem:**
  - Fails WCAG 2.2.2 (Pause, Stop, Hide): moving content that lasts more than 5 s, starts by itself and has no control.
  - Users who set reduced motion still get the loop.
- **Proposal:**
  - Use `<video controls muted loop playsinline preload="metadata" poster=…>` with no autoplay. The poster is the first impression and play is opt-in.
  - If autoplay is wanted, documentation-system §1 must allow a tiny `media.js` that pauses the video under `prefers-reduced-motion` and adds a visible pause button.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-008 · minor · The hero video is stale, tells three unrelated stories, and its narration presents Spectio as running

*Reviewer IDs: DOC-107, plus the hero part of DOC-205.*

- **Where:** `docs/assets/media/gate-review.mp4` (landing hero, F5); `tools/media/casts/synthetic-gate.yaml` step 1 (also `docs/usage/index.md`).
- **Evidence:**
  - Frames at 0 s and 20 s show the avatar "AL" and work dir `/scratch/demo/rnaseq-1025`. `run-detail_light.webp` and the current AppTopbar board show "AM" and `/scratch/demo/amartin/rnaseq-1025`.
  - The mp4 dates from 9185808 (08:43), before 4a09480 (13:12, "fixture identities"). The shots were regenerated, the combo was not.
  - The cast comment (l.16) says "Spectio stops at the gate with --until" over `snakemake -s $WF --cores 2 --until qc_report`.
  - The hero shows three unrelated contexts: the terminal runs `snakemake … --until qc_report`, the browser shows the Nextflow `rnaseq-2026-10-25` run, then an imaging-plate gate. On desktop the browser half is the board at about 40 % scale (`vf-montage.png`).
- **Problem:** the media does not match the current boards (§4.2 Media), the story (one run stops, gets reviewed, resumes) is hard to follow, and the narration implies a product that does not exist yet.
- **Proposal:**
  - Re-capture the combo (`python3 tools/media/combo.py tools/media/combos/gate-review.yaml`) with boards seeded with the synthetic run's name, so terminal and browser show the same run.
  - Reword the comment to "the stop Spectio will generate: snakemake --until".
- **Found by:** doc-reviewer, ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-018 · minor · Steps 3 and 4 are illustrated by screens that do not show what the text says

*Reviewer ID: DOC-204.*

- **Where:** `docs/index.md` l.78 (`runs_light.webp` under "Fix and relaunch") and l.87 (`overview_light.webp` under "Results and dashboards"). Crop: 1440 light, y≈3000-3800.
- **Evidence:**
  - Step 3 says Spectio explains a failure (OOM, time, tool error, node lost) and relaunches. The image is the runs table.
  - Step 4 talks about outputs, reports and depictio. The image is the Overview ("Good morning").
  - Matching boards exist: `RunFailed.dc.html`, `RelaunchDialog.dc.html`, `RunOutputs.dc.html`, `DepictioDecisions.dc.html`.
- **Proposal:**
  - Step 3: RunFailed or RelaunchDialog, alt "A failed task with its cause and the suggested change".
  - Step 4: RunOutputs, alt "Reports and outputs attached to a run".
  - Shoot them with `tools/media/shots.py`.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-019 · minor · Screen designs on the landing are unreadable on phone

*Reviewer ID: DOC-205 (the hero part is merged into DOC-008).*

- **Where:** `landing-phone-light.png`: step images (358 px wide, from 1440 px boards) and the hero video at y≈665-865.
- **Evidence:** board text renders at about 2-3 px on phone; the overlay "design boards, not this run's data" is about 5 px.
- **Problem:** on phone, the "How it works" pictures carry no information.
- **Proposal:**
  - Add 2× cropped shots of the relevant region (about 720×540 CSS px), served through `<picture><source media="(max-width:50em)" srcset="…_crop.webp">`.
  - In the optional-gates box on phone, use the existing `review-gate-phone_light.webp`.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-020 · minor · No accessible h1, and a doubled document title

*Reviewer ID: DOC-206.*

- **Where:** `extra.css` l.101 (`h1:has(+ .sp-hero2) { display: none; }`) and the hero brand `<span class="sp-hero2__name">` in `docs/index.md` l.7.
- **Evidence:** the heading outline is `H1:Home [display:none]`, then H2/H3 only. `document.title` is "Spectio - Spectio".
- **Problem:** `display:none` removes the only h1 from the accessibility tree, so screen-reader users get no page heading; the hidden h1 says "Home", not "Spectio".
- **Proposal:**
  - Make the hero name `<h1 class="sp-hero2__name">Spectio</h1>`. Keep Material's own h1 hidden, or hide it with a visually-hidden (clip) rule rather than `display:none`.
  - Override `block htmltitle` in `overrides/main.html` for the home page so the title reads "Spectio, a run manager for Nextflow and Snakemake".
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-021 · minor · Progress strip links have no meaningful name on phone; bars have no text alternative

*Reviewer ID: DOC-208.*

- **Where:** `hooks/progress.py` `_strip()` l.38-51, and `extra.css` `@media (max-width:38em) .sp-wave__title{display:none}`.
- **Evidence:** at 390 px the accessible names are "W0 7/7" … "W5 0/2". The bar markup is `<span class="sp-wave__bar"><span style="width:100%">` with no role and no label.
- **Proposal:**
  - The hook emits `aria-label="Wave W1, Independent reviews: 8 of 9 steps done"`, and `role="img" aria-label` on the bar (or `aria-hidden` on the bar once the link label carries the count).
  - On phone, wrap the title onto a second grid row instead of hiding it.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-022 · minor · "Where it stands" breaks the layout and uses internal jargon

*Reviewer ID: DOC-209.*

- **Where:** `landing-desktop-light.png`, y≈4740-5080.
- **Evidence:**
  - `.sp-waves` is left-aligned and 1188 px wide; every other section is centred at 52-62 rem.
  - Titles shown: "Foundations, done interactively with Thomas (2026-10-24 to 26)", "Triage and apply W1 findings…", "the one human decision".
  - documentation-system §1 says user-facing pages use plain words.
- **Proposal:**
  - Add `.sp-waves{max-width:56rem;margin:0 auto}`.
  - The strip reads a user-facing `public_title` per wave, or shows the release stages (design → 0.1 → beta) from the roadmap timeline and links to Progress for the wave detail.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-023 · minor · Low-contrast icons: the dark SLURM mark and the amber tiles

*Reviewer ID: DOC-211.*

- **Where:** `extra.css` `.sp-work__icon{color:var(--sp-ink-500)}` and `.sp-ic--amber{background:#D9890B}`.
- **Evidence:**
  - The SLURM icon on the dark card is 2.17:1.
  - White glyph on amber is 2.79:1 (QC gates card, optional-gates box). Other tiles: coral 3.2, green 3.32, sky 3.58.
  - `#D9890B` is the run-state token `--sp-state-review`, reused here as decoration.
- **Proposal:** `.sp-work__icon{color:var(--sp-text-3)}` (6.45:1 on the dark card); amber-700 `#AE783B` for the tile (about 3.8:1), which also keeps the state colour for states only.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-024 · minor · The keyboard focus ring is barely visible on cards

*Reviewer ID: DOC-213.*

- **Where:** `a.sp-card2`, `a.sp-work`, `a.sp-wave`. Capture: `focus-card2.png`.
- **Evidence:** focus shows Material's `outline: auto 1px #EC5F87` on a white card: faint and pink. The palette toggle reports `outline: none` when focused. Tab order is logical.
- **Proposal:** add `:focus-visible{outline:2px solid var(--sp-line-focus);outline-offset:2px}` for these links (violet-600 light, violet-400 dark), and check the toggle's focus style.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-025 · minor · Phone footer has 4 px gutters and 20 px link targets

*Reviewer ID: DOC-207.*

- **Where:** `extra.css` `.sp-footer` (l.109). Crop: `landing-phone-light.png`, bottom 170 px.
- **Evidence:** the rule is `.sp-footer { padding-left: .8rem; padding-right: .8rem; … padding: .9rem 0; … }`; the later shorthand zeroes the side padding (confirmed at merge time). Measured gutters at 390 px: 4/4, against 16/16 for the body. Footer links are 20 px tall.
- **Proposal:** `padding:.9rem .8rem`; add `.sp-footer a{display:inline-block;padding:.35rem 0}` so targets reach at least 24 px (WCAG 2.5.8). Below 30em, stack them at 44 px.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-026 · minor · "What is inside" makes a 1 000 px single column on phone

*Reviewer ID: DOC-214.*

- **Where:** `extra.css` `@media (max-width:30em) .sp-cards2{grid-template-columns:1fr}`. Crop: `landing-phone-light.png`, y≈4960-5990.
- **Evidence:** six 358×163 cards, each holding three words.
- **Proposal:** keep two columns down to 340 px and cut card padding to .9rem; or, on phone, render compact rows (icon, title and line, 56 px each).
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

## Theme and site chrome

### DOC-012 · minor · Theme colours drift from `spectio-tokens.css`; dark headings dimmer than body

*Reviewer ID: DOC-210.*

- **Where:** `extra.css` l.4-36, and Material defaults that are not remapped.
- **Evidence:**
  - Dark h2/h3 are Material's `rgba(226,228,233,.82)` (contrast 10.03); body paragraphs are `#C4C7D4` (11.03), so the hierarchy is inverted. Light h2 is `rgba(0,0,0,.87)`, not ink-900.
  - Dark page `#11121F` vs token `--sp-surface-page` `#0F1020`; dark text `#F1F2F8` vs `--sp-text-primary` `#ECEDF5`; dark line `#2A2D45` vs `--sp-line-border` `#33364A`.
  - The dark primary button stays violet-600 with white text; the token says `--sp-accent` violet-400 with `--sp-accent-on` ink-900.
  - The footer uses Material's near-black (`#161616` light, `#111317` dark).
  - `extra.css` copies hex values instead of reading the tokens file.
- **Proposal:**
  - Map `--md-default-fg-color`, `--md-typeset-color`, `--md-default-bg-color`, `--md-footer-bg-color` and the dark primary/accent to the token names in both schemes.
  - Generate the `:root` block from `design/tokens/spectio-tokens.css`, or `@import` it, and let `tools/docs/check.py` diff the two.
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-013 · minor · Header source widget and footer links point to resources that 404

*Reviewer IDs: DOC-212, plus the footer part of DOC-113.*

- **Where:** `mkdocs.yml` `repo_url` (l.4); `overrides/main.html` footer, "Repository" (l.14) and "All preview versions" (`versions/`, l.18).
- **Evidence:**
  - Every load calls `api.github.com/repos/weber8thomas/spectio` and `/releases/latest`. Both return 404 (two console errors) because the repository is private (documentation-system §1). The widget shows "GitHub" with no stats.
  - `versions/` is not in the built site; it only exists on Cloudflare ([`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §7.1).
- **Proposal:**
  - Set `repo_url` only through env in previews until the repository is public.
  - Render the versions link only when `config.extra.preview != 'local'`.
  - Hide the "Repository" link until the repository is public.
- **Found by:** ux-reviewer, doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-027 · minor · Map navigation gaps

*Reviewer ID: DOC-113 (the footer link is merged into DOC-013).*

- **Where:** `docs/map.md` (Research, Decisions).
- **Evidence:**
  - `research/depictio-qc-integration-2026-10-26.md` and `decisions/0001-nextflow-through-nf-spectio.md` are in the nav but not in `map.md` (grep at merge time: no match).
  - The build prints an INFO line listing the 15 step pages as not in the nav, although the `on_nav` hook adds them. Cosmetic.
- **Proposal:** add the two entries to the map.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

## The spec against the tools

### DOC-007 · minor · documentation-system.md specifies tools and settings that do not exist

*Reviewer ID: DOC-110.*

- **Where:** [`documentation-system.md`](../specs/documentation-system.md) §1 (Theme, Markdown extensions, mike), §3.2 (index generation), §3.3.2.
- **Evidence:**
  - §3.3.2 names `tools/docs/check_mermaid.py`. No such file exists (`tools/docs/` holds only `check.py`); the check is `check_mermaid()` in `check.py`.
  - §1 says the overrides "preload the Virgil font". `overrides/main.html` loads only Outfit, and inbox #1 says the font stays local and is not committed.
  - §1 lists `.snippets`. `mkdocs.yml` has no `pymdownx.snippets`.
  - §1 says `hooks/shared_images.py` is adopted "before images grow". It is absent (`hooks/` holds `lists.py` and `progress.py`; `docs/assets` is about 3.3 MB).
  - §3.2 says the index is "generated from the front matter". `hooks/progress.py` reads `pipeline.yaml` and `state.json`, and `progress/index.md` says so.
- **Proposal:** update the spec to match `check.py`, inbox #1 and the hook. Either add snippets or drop it. Make `shared_images.py` a D6 deliverable with a size threshold.
- **Found by:** doc-reviewer
- **Status:** inbox, assumed: documentation-system §1, §3.2 and §3.3.2 are rewritten to match `check.py`, inbox #1 (no Virgil preload) and `hooks/progress.py`; `.snippets` is dropped from the list; `shared_images.py` becomes a D6 deliverable with a size threshold — pending Thomas (TRIAGE1, 2026-10-27)

### DOC-009 · minor · The cloud-env cast is a stub replay, which the spec does not allow for

*Reviewer ID: DOC-108.*

- **Where:** [`documentation-system.md`](../specs/documentation-system.md) §5.2 ("`cast.py` runs the commands for real"); `tools/media/README.md` ("The output is real"); `tools/media/casts/cloud-env.yaml`; `docs/assets/media.yaml` (`cloud-env`).
- **Evidence:** `cloud-env.yaml`: "The tools are NOT run again. Each of docker / nextflow / sind / npx is a stub that prints the output recorded". The replayed lines match `LOG.md` at 217a92c (`[PIPELINE]`, `ERRO the Docker daemon…`). D2 discloses the replay.
- **Problem:** a replay is a reasonable way to show a spike, but no rule covers it, and the CI check for "casts that no longer replay" cannot detect drift.
- **Proposal:** add a §5.2 subsection for "replayed casts": a recorded-log source is required, titles say "replayed", and the `media.yaml` entry gets `kind: cast-replay`. Update the README.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-010 · minor · PNG figures escape the freshness check and depend on an uncommitted font

*Reviewer ID: DOC-112.*

- **Where:** `tools/docs/check.py` `check_diagrams` (SVG only); `tools/diagrams/sketch.py`:42, 702; `docs/assets/media.yaml` diagram generators.
- **Evidence:** freshness runs with `--no-png`. `sketch.py` adds the Virgil `@font-face` only if `SPECTIO_VIRGIL_TTF` (default `docs/fonts/Virgil.ttf`, which does not exist) is present, and otherwise falls back silently to Comic Sans or cursive. Running `gate_resume.py` wrote the SVG, then failed on the Python `playwright` import.
- **Proposal:** record in `media.yaml` that the generators need `SPECTIO_VIRGIL_TTF` and Python playwright. Make `sketch.py` warn, or fail unless `--allow-fallback-font`, when the font is missing.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-011 · minor · The §2 landing render check has no script

*Reviewer ID: DOC-111.*

- **Where:** [`documentation-system.md`](../specs/documentation-system.md) §2 "Check"; `tools/docs/`.
- **Evidence:** no tool renders the landing at 1440×900 and 390×844 in light and dark; F5 says it was done by hand. Run by hand with Playwright against the built site: scrollWidth 1440 and 390 (pass); nothing failed except two `api.github.com` 404s (DOC-013).
- **Proposal:** add `tools/docs/render_landing.js`, which writes 4 PNGs and fails if scrollWidth > viewport, and call it from `check.py`.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

### DOC-017 · minor · Figure defects: label collision, low-contrast dark legend, outdated merge step

*Reviewer ID: DOC-109.*

- **Where:** `docs/assets/diagrams/cloud-env_{light,dark}.png` (`tools/diagrams/cloud_env.py`); `gate-resume_dark.png` (`gate_resume.py`); `autopilot-loop_{light,dark}.png` step 9 (`autopilot_loop.py`).
- **Evidence:**
  - cloud-env: the red ✗ on the 403 arrow is drawn over the word "scope".
  - gate-resume dark: the "QC report the gate reads" and "run in run 2" swatches are both dark brown and hard to tell apart.
  - autopilot-loop: `autopilot_loop.py` l.127 draws "Thomas merges to `main`". Inbox #3 (2026-10-26) lets Claude merge the promotion PR, and documentation-system §8 describes `AUTOMERGE_MAIN`.
- **Proposal:** move the ✗ to the arrow's end, give the qc_report cell a distinct dark-theme hue, and relabel step 9 "promotion PR to main (§8)". Then re-run the three scripts.
- **Found by:** doc-reviewer
- **Status:** accepted (TRIAGE1, 2026-10-27)

## Checks that passed

- Strict build exits 0 with 0 warnings; all 15 step pages are in the nav (`on_nav` hook).
- Every Progress page has the front matter, the admonition and all five sections; missing figures are listed as follow-ups as the `foundation` rule asks.
- Sampled counts match: R1-R9 finding totals, R2's 206 claims, the corpus 14+9, Snakemake 11/11 re-run, 10 unit tests, cast output reproduced on Snakemake 9.27.1.
- The four casts replay with increasing timestamps; `synthetic-gate` reproduces. The video is 24.6 s and 0.4 MB; no leaks visible in 5 frames or 9 shots.
- Landing: no broken images, no horizontal scroll at 390 px (16/16 gutters), decorative logos have `alt=""`, screenshots and the video have meaningful labels, all text reaches WCAG AA in both themes (lowest 6.45:1), section order matches documentation-system §2.

## Questions for Thomas

1. **Landing owner (DOC-001).** Do you confirm that documentation-system §2 owns the public landing? Should `Landing.dc.html` be retired, or kept as a "post-0.1 marketing draft" without the install line, WES and MCP?
2. **Hero video (DOC-006).** Drop autoplay (poster plus controls, play on demand), or allow a small `media.js` in documentation-system §1 that pauses under reduced motion and adds a pause button?
3. **Dark screenshots (DOC-005).** Accept the short-term CSS dimming plus a recorded gap in §0.2, or schedule dark board variants now? If now, in which step?
4. **Review records (DOC-003).** Where should the `doc-reviewer` verdict live: a journal line, or `.autopilot/reviews/<step>.txt`? Should the 15 existing pages be re-reviewed to get a stored score, or grandfathered?
5. **W0 history (DOC-004).** Is `claude/foundations-2026-10-26` the permanent home of the pre-squash SHAs, so pages can link there? Or should the W0 evidence be rewritten against 9185808?
6. **Virgil font (DOC-007, DOC-010).** Inbox #1 is still open. Until it is answered, should the docs gate accept that PNG figures cannot be regenerated reproducibly in CI, and should `sketch.py` fail rather than fall back silently?
7. **Private repository (DOC-013).** Hide the GitHub source widget and the "Repository" link until the repository is public?

## Proposed spikes

- **`spikes/dark-boards/` (DOC-005, DOC-012):** add a `:root[data-theme="dark"]` block to `spectio-tokens.css` and a `--theme dark` switch to `tools/canvas/render.js`. Render the four landing boards and the run-detail poster in dark, and measure how many boards need hand fixes. Ends with a note on effort and whether the shots pipeline can produce pairs for every board.
- **`spikes/docs-gate-coverage/` (DOC-002, DOC-003):** prototype the `required-pages` check (from `pipeline.yaml` kinds and `state.json` outputs), the page-reference media scan and the stored-verdict check. Run them against the W0 and W1 history to count false positives before they are made blocking.
- **`spikes/landing-render-check/` (DOC-011, DOC-006, DOC-020):** a Playwright script that renders the landing in the four §2 viewports and asserts scrollWidth, console errors, a visible h1, and that no media autoplays under `reducedMotion: 'reduce'`. Measure its CI time to decide whether it runs in `check.py` or only in `docs.yml`.
