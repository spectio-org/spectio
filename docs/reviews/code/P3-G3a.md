# UX review · P3 G3a, Paper page bodies of the run boards

Board review of `autopilot/P3-G3a`, base `531112f`, 2026-10-30. The step is [P2 §10.3 G3a](../../plans/P2-execution.md#103-g3a-paper-page-bodies-of-the-run-boards): the page head of [ui-spec §7](../../specs/ui-spec.md#7-consistency-with-depictio-reuse-plan) (tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right) on the run boards and their phone twins. It also takes the two G1 minors handed to G3a ([UX-G1-12, UX-G1-13](P3-G1.md#ux-g1-12-minor-below-1000-px-the-folded-crumbs-cannot-be-reached)) and the `crumbs` follow-up of UX-G1-11.

**Boards changed.** `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, `LiteCancelDialog`, `LiteStates`, `LiteStatesRun`, `MLiteHome`, `MLiteRuns`, `MLiteRunDetail`, `MLiteRunObserved`, `MLiteCancelSheet`, and the shared `LiteTopbar` and `MLiteTopbar`. `LiteHome` and `LiteRuns` already had the §7 page head and are unchanged.

**Reviewers.** The worker session had no tool to start a sub-agent, so the round below is a self-check against the `ux-reviewer` brief (`.claude/agents/ux-reviewer.md`), as in [P3-G1](P3-G1.md). The independent `ux-reviewer` run is still to do, by the coordinator.

| Round | Head | Reviewer | Verdict |
|---|---|---|---|
| self | the restyle, before its fixes | worker, `ux-reviewer` brief | **changes** (0 blockers, 0 majors, 3 minors), fixed before the commit |
| 1 | the G3a commit | `ux-reviewer`, independent | to do (coordinator) |

**What was rendered and looked at.** The 8 desktop boards at 1440 × 1180 and at 1024 × 800, the 5 phone boards at 390 × 844, `MLiteTopbar` alone at 360 px, and `LiteTaskFilesStates` at 900 px for the folded breadcrumbs. No overlap, clipping or empty list was seen.

## What changed

- **Run heads** (`LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, and the page behind `LiteCancelDialog`): the pipeline logo sits in a tinted 48 px tile (`#F6F2FE`, the Runs tint of `LiteRuns`) in place of a white 52 px tile with a border. The h1 was already Outfit. The state line is now one run of inline text, so below 1440 px it wraps as a sentence. The text block shrinks (`flex: 1 1 320px`), so Cancel run and Copy stay on the right at 1024 px.
- **States boards** (`LiteStates`, `LiteStatesRun`): a page head with a tile, and a one-line description. The rest of the old description ("Each panel stands in for…") moved to a caption under the panels. The run-detail loading skeleton in `LiteStatesRun` now draws the 48 px tile too.
- **Phone, top-level pages** (`MLiteHome`, `MLiteRuns`): the page head is in the body: a 48 px tile, the Outfit h1 and the description. `MLiteRuns` no longer passes `title` and `sub` to `MLiteTopbar`, so its top bar is the 48 px row only, as on `MLiteHome`. The primary action stays a full-width row on `MLiteHome`; `MLiteRuns` has none, as before (Launch is in the tab bar).
- **Phone, run pages** (`MLiteRunDetail`, `MLiteRunObserved`, `MLiteCancelSheet`): the page head stays the top bar's second row (back link, h1, state line). The run card now starts with the pipeline in a 48 px tinted tile, its name and its engine.
- **`LiteTopbar`** (UX-G1-12): below 1000 px the crumbs between Home and the parent of the last one fold into "…". "Home › Runs › rnaseq-2026-10-25 › Tasks" shows "Home › … › rnaseq-2026-10-25 › Tasks": the link back to the run stays. The crumb that can fold today is Runs, which is also a sidebar link.
- **`MLiteTopbar`** (UX-G1-13): `.mk-narrow-hide{width:40px}` is removed, so the search and notifications placeholders are 44 px wide like the other buttons. The first row's gap is 2 px.

## Findings

### UX-G3a-01 · minor · At 1024 px the run-head actions dropped under the title

- **Where:** `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunObserved`, `LiteCancelDialog`: the text block had `flex-grow: 1; min-width: 260px` in a wrapping row.
- **Evidence:** at 1024 × 800 Cancel run and Copy wrapped to a second row, left-aligned under the tile. ui-spec §7 puts the primary action on the right.
- **Fix:** `flex: 1 1 320px; min-width: 0`; the description wraps instead.
- **Status:** applied.

### UX-G3a-02 · minor · The state word split from its context when the line wrapped

- **Where:** the same four boards, the state line under the h1 (a flex row).
- **Evidence:** at 1024 px "▶ Running" stood alone on one line and "· 3 of 8 stages done…" started a new one.
- **Fix:** the line is a block of inline text; the icon is inline (`vertical-align: -3px`).
- **Status:** applied.

### UX-G3a-03 · minor · The phone tiles were almost invisible on the grey page

- **Where:** `MLiteHome`, `MLiteRuns`: `#F2F1FB` and `#F6F2FE` tiles on the `#F7F7FB` phone page.
- **Fix:** `#E7E5F8` (Home) and `#ECE7FC` (Runs) on the phone. The icon colours keep more than 3:1 on them.
- **Status:** applied.

### UX-G3a-04 · minor · ui-spec §7 does not say where the page head goes on a phone

- **Where:** ui-spec §7 (spec, not edited in a board step).
- **Proposal:** a dated note: on the phone, top-level pages put the page head in the body (tile, h1, description) with the primary action as a full-width row under it; drill-down pages (a run) keep the back link, h1 and state line in the top bar's second row, and the tile moves into the first card.
- **Status:** deferred to the next `/apply-findings`.

### UX-G3a-05 · minor · `LiteRuns` scrolls sideways at 1024 px

- **Where:** `LiteRuns.dc.html`, the runs table: fixed columns that add up to 1 120 px.
- **Evidence:** at 1024 px, Tasks, Started and Duration are behind a horizontal scroll. The table is a focusable region named "Runs table", so it is reachable by keyboard, and WCAG 1.4.10 allows two-way scroll for data tables. Present before G3a.
- **Proposal:** let G4's Mantine table hide Started below 1100 px, or use relative column widths.
- **Status:** open, for G4.

### UX-G3a-06 · minor · The phone run state line is cut on `MLiteRunObserved`

- **Where:** `MLiteRunObserved`, the top bar's second row: "Running · from a terminal · 2 of 8 stages done · 5 runni…".
- **Evidence:** one line with an ellipsis; the full counts are in the run card below. Present before G3a.
- **Status:** open, kept.

### UX-G3a-07 · minor · The top bar's global link colour still lives in `LiteTopbar`

- **Where:** `LiteTopbar.dc.html`, helmet `a{color:#4D5065}` (UX-G1-01).
- **Evidence:** the rule is global to each board that imports the top bar. Removing it touches the launch boards (G2) and the run-tool boards (G3b), which other branches edit now.
- **Status:** open, for G3b.

## The `crumbs` props (UX-G1-11 follow-up)

None of the G3a boards passes an in-page tab: `LiteHome` "Home", `LiteRuns` "Runs", `LiteRunDetail` and `LiteCancelDialog` "Runs / rnaseq-2026-10-25", `LiteRunDetailSnakemake` "Runs / strandseq-hg002-p01", `LiteRunObserved` "Runs / rnaseq-pilot-hand", `LiteStates` "States", `LiteStatesRun` "States · run and launch". `LiteTaskFilesStates` passes "Runs / rnaseq-2026-10-25 / Tasks", where Tasks is a tab of the run detail; it is a G3b board, so the fix is left to G3b.

## Checks against the keyboard rules (CLAUDE.md, ui-spec §4.11)

- No new control. The tiles are decorative: their SVGs are `aria-hidden` and the phone logos have `alt=""`, because the pipeline name follows as text.
- One h1 per board: `MLiteRuns` now has its h1 in the body, and its top bar draws no title.
- The folded crumbs: the "…" stays `aria-hidden`; what it hides (Runs) is the sidebar's Runs link, so no page becomes unreachable by keyboard or screen reader.
- `MLiteTopbar`: every button is 44 × 44 at 390 px; below 390 px the two placeholders are hidden as before (the 360 px render shows the row fitting).
