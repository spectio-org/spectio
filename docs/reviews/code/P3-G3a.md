# UX review · P3 G3a, Paper page bodies of the run boards

Board review of `autopilot/P3-G3a`, base `531112f`, 2026-10-30. The step is [P2 §10.3 G3a](../../plans/P2-execution.md#103-g3a-paper-page-bodies-of-the-run-boards): the page head of [ui-spec §7](../../specs/ui-spec.md#7-consistency-with-depictio-reuse-plan) (tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right) on the run boards and their phone twins. It also takes the two G1 minors handed to G3a ([UX-G1-12, UX-G1-13](P3-G1.md#ux-g1-12-minor-below-1000-px-the-folded-crumbs-cannot-be-reached)) and the `crumbs` follow-up of UX-G1-11.

**Boards changed.** `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, `LiteCancelDialog`, `LiteStates`, `LiteStatesRun`, `MLiteHome`, `MLiteRunDetail`, `MLiteRunObserved`, `MLiteCancelSheet`, and the shared `LiteTopbar` and `MLiteTopbar`. Three boards end up unchanged:

- `LiteHome` and `LiteRuns` already had the §7 page head.
- `MLiteRuns` was changed in the first commit and then reverted (UX-G3a-08).

**Reviewers.** Two passes:

- a self-check against the `ux-reviewer` brief (`.claude/agents/ux-reviewer.md`), run by the worker session, which had no tool to start a sub-agent (findings UX-G3a-01 to -07);
- an independent `ux-reviewer` run started by the coordinator on `127fc46` (findings UX-G3a-08 to -13). Its renders are in `/tmp/claude-0/g3a-review/`.

| Round | Head | Reviewer | Verdict |
|---|---|---|---|
| self | the restyle, before its fixes | worker, `ux-reviewer` brief | **changes** (0 blockers, 0 majors, 3 minors), fixed in `127fc46` |
| 1 | `127fc46` | `ux-reviewer`, independent | **changes** (0 blockers, 1 major, 5 minors), fixed in the fix-round commit |
| 2 | the fix-round commit | `ux-reviewer`, independent | to do (coordinator) |

**What was rendered and looked at.**

- After the fix round:
    - the 6 changed desktop boards at 1440 × 1180, 1024 × 800 and 900 × 800;
    - `LiteTaskFilesStates` and `LiteResults` at the same widths, for the folded breadcrumbs;
    - the 5 phone boards (`MLiteHome`, `MLiteRuns`, `MLiteRunDetail`, `MLiteRunObserved`, `MLiteCancelSheet`) at 390 × 844.
- Before it, the same boards at 1440 and 1024 px, and `MLiteTopbar` alone at 360 px.

No overlap, clipping or empty list was seen.

## What changed

- **Run heads** (`LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, and the page behind `LiteCancelDialog`):
    - **Tile:** the pipeline logo sits in a tinted 48 px tile (`--sp-violet-50` `#F6F2FE`, the Runs tint of `LiteRuns`) at the top of the head (`align-self: flex-start`). Before, it was a white 52 px tile with a border.
    - **h1:** wraps anywhere, so a long run name cannot overflow.
    - **State line:** one run of inline text, so it wraps as a sentence.
    - **Text block:** it shrinks (`flex: 1 1 320px`).
    - **Actions:** one group pushed to the right (`margin-left: auto`): Cancel run and Copy, or the "monitor only" note and Copy on `LiteRunObserved`. The inert page behind `LiteCancelDialog` shows Copy too.
- **States boards** (`LiteStates`, `LiteStatesRun`):
    - a page head with a tile in the Runs tint, and a one-line description;
    - the rest of the old description ("Each panel stands in…") is now a caption under the panels;
    - the run-detail loading skeleton in `LiteStatesRun` draws the 48 px tile too.
- **Phone, top-level pages:**
    - **`MLiteRuns`** is back to base: its title and the line "15 runs · 6 active · live, updated 4 s ago" stay in the compact top bar (ui-spec §4.11).
    - **`MLiteHome`** had no top-bar title at base: its h1 was already in the body. So the page head stays in the body, and the tile added here uses `--sp-indigo-100` `#E5E3F7`. The `-50` tint barely shows on the grey phone page.
    - **The `MLiteHome` description** is shortened from "4 runs running, 1 queued and 1 cancelling · live, updated 4 s ago" to "4 running, 1 queued, 1 cancelling · live, updated 4 s ago", to fit beside the tile.
- **Phone, run pages** (`MLiteRunDetail`, `MLiteRunObserved`, `MLiteCancelSheet`):
    - the page head stays the top bar's second row: back link, h1 and state line;
    - the run card now starts with the pipeline in a 48 px tile (`--sp-violet-50`, on the white card), then its name and its engine;
    - the inert card behind `MLiteCancelSheet` shows Cancel run and Copy, as on `MLiteRunDetail`.
- **`LiteTopbar`** (UX-G1-12, UX-G3a-13): below 1000 px, on a page under a run, the crumbs between Home and the run fold into "…".
    - "Home › Runs › rnaseq-2026-10-25 › Tasks" shows "Home › … › rnaseq-2026-10-25 › Tasks", so the link back to the run stays.
    - The run itself never folds, and neither do crumbs that come after it.
    - The run names live in their own `runPages` map.
- **`MLiteTopbar`** (UX-G1-13):
    - `.mk-narrow-hide{width:40px}` is removed, so the search and notifications placeholders are 44 px wide like the other buttons;
    - the first row's gap is 2 px.

## Findings

### UX-G3a-01 · minor · At 1024 px the run-head actions dropped under the title

- **Where:** `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, `LiteCancelDialog`. The text block had `flex-grow: 1; min-width: 260px` in a row that wraps.
- **Evidence:** at 1024 × 800, Cancel run and Copy wrapped to a second row, left-aligned under the tile. ui-spec §7 puts the primary action on the right.
- **Fix:** `flex: 1 1 320px; min-width: 0`; the description wraps instead. See also UX-G3a-09.
- **Status:** applied in `127fc46`.

### UX-G3a-02 · minor · The state word split from its context when the line wrapped

- **Where:** the same four boards, the state line under the h1 (a flex row).
- **Evidence:** at 1024 px, "▶ Running" stood alone on one line and "· 3 of 8 stages done…" started a new one.
- **Fix:** the line is a block of inline text; the icon is inline (`vertical-align: -3px`).
- **Status:** applied in `127fc46`.

### UX-G3a-03 · minor · The phone tiles were almost invisible on the grey page

- **Where:** `MLiteHome`, `MLiteRuns`: `#F2F1FB` and `#F6F2FE` tiles on the `#F7F7FB` phone page.
- **Fix:** a stronger tint. UX-G3a-11 replaced the ad-hoc values with tokens, and UX-G3a-08 removed the `MLiteRuns` tile.
- **Status:** applied, then superseded by UX-G3a-08 and -11.

### UX-G3a-04 · minor · ui-spec §7 does not say where the page head goes on a phone

- **Status:** withdrawn. ui-spec §4.11 already says it: the phone title and subtitle sit in the compact top bar. Superseded by UX-G3a-08.

### UX-G3a-05 · minor · `LiteRuns` scrolls sideways at 1024 px

- **Where:** `LiteRuns.dc.html`, the runs table. Its fixed columns add up to 1 120 px.
- **Evidence:** at 1024 px, Tasks, Started and Duration are behind a horizontal scroll.
    - The table is a focusable region named "Runs table", so the keyboard reaches it.
    - WCAG 1.4.10 allows two-way scroll for data tables.
    - The scroll was there before G3a.
- **Proposal:** let G4's Mantine table hide Started below 1100 px, or use relative column widths.
- **Status:** open, for G4.

### UX-G3a-06 · minor · The phone run title and state line are cut on `MLiteRunObserved`

- **Where:** `MLiteRunObserved`, the top bar's second row: "Running · from a terminal · 2 of 8 stages done · 5 runni…".
- **Evidence:** one line with an ellipsis; the full counts are in the run card below. A long run name gets the same ellipsis in the title. Present before G3a.
- **Status:** open, for G4, which covers the cut title as well as the cut subtitle.

### UX-G3a-07 · minor · The top bar's global link colour still lives in `LiteTopbar`

- **Where:** `LiteTopbar.dc.html`, helmet `a{color:#4D5065}` (UX-G1-01).
- **Evidence:** the rule is global to each board that imports the top bar. Removing it touches the launch boards (G2) and the run-tool boards (G3b), which other branches edit now.
- **Status:** open, for G3b.

### UX-G3a-08 · major · Top-level phone pages moved the title out of the compact top bar

- **Where:** `MLiteRuns` at `127fc46`: the title and "15 runs · 6 active · live, updated 4 s ago" moved from `MLiteTopbar` into a body page head with a tile.
- **Evidence:**
    - ui-spec §4.11 puts the phone title and subtitle in the compact top bar, and the primary action in a pinned bar (inbox #30).
    - In the body, the "live, updated" line scrolls away with the list.
- **Fix:**
    - `MLiteRuns` is back to base: `MLiteTopbar` `title` and `sub` props, no body page head, no tile.
    - `MLiteHome` was checked against the same rule. It had no top-bar title at base 531112f, so its body h1 stays, with the tile of UX-G3a-11.
- **Status:** applied.

### UX-G3a-09 · minor · The run-head actions were not one group

- **Where:**
    - `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteCancelDialog`: Cancel run and Copy were separate items of the wrapping row, so they could split across lines.
    - The tile was centred on a head that grows to three lines.
- **Fix:**
    - Cancel run and Copy are wrapped in one `<div style="display:flex;gap:12px;margin-left:auto;flex-shrink:0">`. `LiteRunObserved` already had a group; it now carries the same style.
    - The tile has `align-self: flex-start` on the four run boards.
    - At 900 px, the group wraps under the text as one unit, on the right.
- **Status:** applied.

### UX-G3a-10 · minor · A long run name could overflow the run head

- **Where:** the h1 of the four desktop run boards.
- **Fix:** `overflow-wrap: anywhere`.
- **Status:** applied.

### UX-G3a-11 · minor · The phone tiles used ad-hoc tints

- **Where:** `MLiteHome` (`#E7E5F8`), `MLiteRuns` (`#ECE7FC`), and the States boards (the Home tint on a run-related board).
- **Fix:**
    - `MLiteHome` uses `--sp-indigo-100` `#E5E3F7`. The `MLiteRuns` tile is gone (UX-G3a-08).
    - The phone run cards keep `--sp-violet-50` `#F6F2FE`, because they are white.
    - `LiteStates` and `LiteStatesRun` take the Runs tint, `--sp-violet-50` with `--sp-violet-700` icons.
    - The tokens file is not edited; the tint rule goes to `/apply-findings`.
- **Status:** applied.

### UX-G3a-12 · minor · The inert run head behind the cancel dialog lacked Copy

- **Where:** `LiteCancelDialog` (the head behind the dialog), `MLiteCancelSheet` (the run card behind the sheet).
- **Evidence:** the page behind a dialog should look like the page it opened from. `LiteRunDetail` and `MLiteRunDetail` show Copy next to Cancel run.
- **Fix:** the Copy button is added to both. It is inside the existing `inert` wrapper, so it takes no focus.
- **Status:** applied.

### UX-G3a-13 · minor · The fold rule could hide the parent of the last crumb

- **Where:** `LiteTopbar`, `renderVals`, at `127fc46`: it folded crumbs 1 to len − 3. On a deeper path, the run itself could fold, and the comment did not say so.
- **Fix:** it folds only the crumbs before the run, indexes 1 to runIndex − 1, and only when the run is not the last crumb. The comment says so.
- **Checked:** at 900 px:
    - `LiteTaskFilesStates` shows "Home › … › rnaseq-2026-10-25 › Tasks";
    - `LiteResults` shows "Home › … › rnaseq-2026-10-25 › Results";
    - `LiteRunDetail` keeps "Home › Runs › rnaseq-2026-10-25".
- **Status:** applied.

## For the next `/apply-findings`

- **ui-spec §4.11:** the tablet range, 768–1199 px, has a folded sidebar, but the desktop boards do not draw it.
- **Tile tints:** a page-head tile takes `-100` of its section colour on the grey phone page (`#F7F7FB`), and `-50` on white. This is a rule for `design/tokens/spectio-tokens.css` or ui-spec §7.

## The `crumbs` props (UX-G1-11 follow-up)

None of the G3a boards passes an in-page tab:

| Board | `crumbs` |
|---|---|
| `LiteHome` | "Home" |
| `LiteRuns` | "Runs" |
| `LiteRunDetail`, `LiteCancelDialog` | "Runs / rnaseq-2026-10-25" |
| `LiteRunDetailSnakemake` | "Runs / strandseq-hg002-p01" |
| `LiteRunObserved` | "Runs / rnaseq-pilot-hand" |
| `LiteStates` | "States" |
| `LiteStatesRun` | "States · run and launch" |

`LiteTaskFilesStates` passes "Runs / rnaseq-2026-10-25 / Tasks", and Tasks is a tab of the run detail. It is a G3b board, so the fix is left to G3b.

## Checks against the keyboard rules (CLAUDE.md, ui-spec §4.11)

- No new live control. The tiles are decorative: their SVGs are `aria-hidden`, and the phone logos have `alt=""` because the pipeline name follows as text. The Copy buttons added by UX-G3a-12 are inside `inert` wrappers.
- One h1 per board. On `MLiteRuns` it is in the top bar again; on `MLiteHome` it is in the body, as at base.
- The folded crumbs: the "…" stays `aria-hidden`. What it hides today is Runs, and the sidebar's Runs link still reaches it, by keyboard or screen reader.
- `MLiteTopbar`: every button is 44 × 44 at 390 px. Below 390 px the two placeholders are hidden, as before; the 360 px render shows the row fitting.
