# UI parity 0.0.1: the built web UI against its lite boards (2026-10-31)

A parity audit of the built Spectio 0.0.1 screens (`web/src`, branch `autopilot/integration`) against the 0.0.1 lite boards, made after Thomas reviewed the screenshots and said that many defined things are missing: collapsible sections with small light icons, and the engine logos.

**Method.** Each board was rendered with `node tools/canvas/render.js design/ui-canvas/<Board>.dc.html 1440 1180` (desktop) or `390 844` (phone). The renders were compared by eye with the live build screenshots in `docs/assets/shots/` (`app-home`, `app-runs`, `app-run-detail`, `app-launch`, `app-run-detail-phone`, `app-launch-phone`, all `_light`) and with the React code. Each element was then checked in three places:

- the API snapshot `packages/spectio-server/openapi/0.0.1.json` (11 routes; schemas `Run`, `RunDetail`, `WorkflowRef`, `Task`, `Process`, `Stage`, `Summary`, `ServerVersion`);
- the 0.0.1 notes of `docs/specs/ui-spec.md`;
- the "Keeps / Drops" table of `design/README.md` §0.0.1 lite boards.

**Boards compared:** LiteHome, LiteRuns, LiteRunDetail, LiteRunDetailSnakemake, LiteRunTasks, LiteRunLogs, LiteRunFailed, LiteLaunch, LiteLaunchSnakemake, LiteCancelDialog, LiteSidebar, LiteTopbar, MLiteHome, MLiteRuns, MLiteRunDetail, MLiteTabbar, MLiteTopbar, plus MLiteLaunch, which is compared with `app-launch-phone`.

**Not compared:** the boards' grey "Data: …" provenance lines, which document the fixtures and are not product text.

**No build screenshot exists** for the phone Home and phone Runs screens. For those two, this audit relies on the code and CSS (`runs.css`, `shell.css`).

**What the 0.0.1 API can serve.** These fields come up again and again below:

- `Run.workflow` carries `engine`, `engine_version`, `name` (the manifest name, for example `nf-core/rnaseq`), `version` and `location`. There is **no** field that says whether a pipeline is a genuine nf-core one.
- `Run.head` carries `session`, `node`, `alive` and `exit_code`.
- `Run.failure` carries `class`, `message`, `task_id` and `attempt` (from `failure_json`, `projector/runs.py`). It has no process name, no tag and no exit code.
- `Run.task_counts` gives counts by state. `Run.summary.tasks` gives `done`, `total`, `failed` and `cached`, with no retries.
- `Task` has only `id`, `process`, `tag`, `name`, `state` and `stage_id`: no attempt, exit code, native job ID, duration or resources.
- `Process.retries` exists.
- `GET /version` gives `node`, `runs_root`, `account` and `executor`. A driven run's directory is `runs_root/<run id>` (`spectio/runner/rundir.py:59-63`).
- `GET /runs/{id}/logs` returns text only, with no file path.

---

## Logo source (asked by the caller)

**The files already exist in this repository.** They are `docs/assets/logos/logo-nextflow.png`, `logo-nf-core.png` and `logo-snakemake.png`: 128 × 128 RGBA PNGs, with `logo-depictio.png` beside them at 128 × 116. They have been tracked since `add68383` (2026-10-26).

- **Who uses them today.** The landing page (`docs/index.md:29-47`) and the board renderer (`tools/canvas/render.js:7-14`, which maps the boards' `/_blob/<id>` URLs to these files).
- **Their recorded provenance.** It is only the line in `docs/assets/media.yaml:107-114`: "copied from the projects' official assets (Nextflow, nf-core, Snakemake, depictio); nominative use". It names no depictio commit, upstream URL or checksum.
- **What the spec asks for.** ui-spec §4.3 asks for "the official files (as shipped in depictio `public/logos/workflows/`)". That these four files are those files is therefore **[to be validated]** against depictio at a pinned commit.
- **The brand and licence rules.** They live in ui-spec §9: "nf-core is MIT and appears only next to genuine nf-core pipelines; Nextflow follows Seqera's brand manual (official files, never recoloured); Snakemake is MIT with no published guidelines". Size: "16–24 px on white, never recoloured" (§4.3). The licence claims in §9 have no source link either, so they too are **[to be validated]** (CLAUDE.md, external facts).
- **The web app has no copy.** There is no `web/public/` and nothing under `web/src` imports a logo.
- **The build already allows them.** Vite keeps assets as files (`assetsInlineLimit: 0`, `web/vite.config.ts`). The server serves `.png` under `/assets/` (`spectio_server/static.py:28-32`). The CSP's `img-src 'self'` allows them. No server change is needed.

---

## Shell and cross-cutting

### UX-PAR-01 · major · No engine or pipeline mark on any screen

- **Where:** boards LiteRuns (Workflow column, a 20 px `<img src="{{r.logo}}">` per row), LiteHome (active rows at 22 px, recent rows at 20 px, Your pipelines at 18 px), LiteRunDetail, LiteRunDetailSnakemake and LiteRunFailed (a 48 px pipeline-mark tile beside the `h1`; the Pipeline fact with its mark; the "Engine · profile" fact with the engine mark), LiteLaunch and LiteLaunchSnakemake (a mark inside each engine button, a mark tile in the "Loaded" card, the engine mark in "Where it runs"), MLiteHome, MLiteRuns, MLiteRunDetail and MLiteLaunch. Build: `web/src/runs/RunsPage.tsx:186-189`, `web/src/home/HomePage.tsx:101-153`, `web/src/runs/RunDetailPage.tsx:138-152` and `:363-383`, `web/src/launch/EngineButtons.tsx:24-34`, `web/src/launch/LaunchPage.tsx:289-300` and `:361-374`.
- **Evidence:** ui-spec §4.3, note 2026-10-28 (UX-323): "the 0.0.1 screens show the pipeline mark next to the pipeline name and the engine mark in the Engine fact (or next to the engine version), so an nf-core run shows both, each once". ui-spec §2, note 2026-10-28: "The engine and pipeline logos (Nextflow, Snakemake, nf-core) mark the pipeline on the run, launch and home screens". The 2026-10-31 note in §4.3 says "Workflow (name and version, no mark yet)". That is a record of what was built, not an exclusion.
- **Problem:** the build shows text only. Thomas named this gap.
- **API:** the engine mark can be served now, from `Run.workflow.engine` and from `Inspected.engine` with the chosen engine on Launch. The nf-core pipeline mark cannot be served cleanly: no field says that a pipeline is genuine nf-core. `workflow.name` starting with `nf-core/` is only a manifest claim, which any fork can make.
- **Proposal:**
  - Copy the three files, once they are verified, into `web/src/assets/logos/` and import them.
  - Add one component, `EngineMark({engine, size})`: 16–24 px, a white tile in dark mode, `alt` set to the engine name when it stands alone, `alt=""` beside the visible name.
  - Add one `PipelineMark`. It shows nf-core only under a stated rule, for example "manifest name `^nf-core/` and, for a Git location, the repository is `github.com/nf-core/<name>`"; otherwise it shows the engine mark. Ask Thomas for the rule, or add `workflow.nf_core: bool` to the API, as an inbox question.
  - Place the marks as the boards do: one mark per workflow.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the engine's mark on every screen of this step (`EngineMark.tsx`); no nf-core mark ([inbox #91](inbox.md#91-assumed-which-mark-a-pipeline-shows-no-nf-core-mark-yet-and-where-the-logos-come-from), assumed); ui-spec §4.3 note "UI parity A". The Pipeline fact has no mark (CR-P3PARA-03, open); Launch's marks go to step B

### UX-PAR-02 · major · No collapsible section anywhere: no light line icon, no summary when folded, no chevron

- **Where:** every titled section of LiteRunDetail, LiteRunDetailSnakemake and LiteRunFailed (Facts, Stages, Why it failed, Open the head by hand, Engine log, Head errors, The head has ended, Parameters, Results and reports), LiteLaunch and LiteLaunchSnakemake (Pipeline, Parameters, each schema group, Where it runs, the params preview), LiteHome (Active runs, Finished recently, Your pipelines, Where your runs go), and MLiteHome, MLiteRuns and MLiteRunDetail. On the boards each section is `h2 > button.cx-btn[aria-expanded][aria-controls]` holding a 26–30 px icon tile, a `.cx-sum` shown only when folded ("8 stages · 4 running", "4 set at launch", "login1 · SLURM") and a chevron that turns. Build: flat `<h2>` headings at `RunDetailPage.tsx:89-99`, `HomePage.tsx:95-143` and `LaunchPage.tsx:237-240`, `:330-333` and `:357-360`. Schema groups are a `<fieldset><legend>` (`LaunchPage.tsx:335-336`).
- **Evidence:** ui-spec §4.4, stages note 2026-10-28, "Open sections (UX-318)": "Every titled section is a heading with a toggle button (`aria-expanded`, `aria-controls`)… Open by default: Stages, the running stage, Why it failed, and every launch group with a required, changed or invalid field… Which sections are open is remembered per screen in the browser's storage". ui-spec §2 note: "each section of the run detail and launch form is collapsible, with a light line icon". The 2026-10-31 note lists this as "Not built in 0.0.1 yet: … the toggled sections of the stages note (only stage rows open and close)". It is not an exclusion.
- **Problem:** Thomas named this gap. Long run pages (8 stages and their processes) cannot be folded, and the screens lose the light icons that give them their look.
- **API:** no data is needed. The summaries come from data the screens already hold.
- **Proposal:** add one `<FoldSection id icon title summary defaultOpen>` component in `web/src/shell/`. Its toggle is a native `<button aria-expanded aria-controls>` inside the `h2`; it uses a lucide-style 1.6-stroke icon in a 26–30 px tile on `--sp-surface-subtle`. It hides the summary while open and turns the chevron 180°, and it remembers its state in `localStorage` per screen. Use it for every section listed above, with the default-open rule of UX-318.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `FoldSection.tsx` on Home and the run detail; ui-spec §7 note 2026-10-31. Launch's groups go to step B (UX-PAR-30)

### UX-PAR-03 · minor · The page-head icon tile is missing on Home, Runs and Launch

- **Where:** LiteHome, LiteRuns and LiteLaunch each have a tinted 48 px tile left of the `h1`: Home in indigo on `#F2F1FB`, Runs as violet ▷, Launch as coral ↑. Build: `HomePage.tsx:59-72`, `RunsPage.tsx:114-128` and `LaunchPage.tsx:228-234` have none.
- **Evidence:** ui-spec §7, "Taken as is": "Page head: tinted 48 px icon tile, Outfit h1, one-line description, primary action on the right."
- **Problem:** the build's page heads do not follow the depictio page-head pattern that the spec takes as is. They also lose the section colour, the cue that ties each page to its sidebar item.
- **API:** none needed.
- **Proposal:** add a `PageHead({section, icon, title, sub, action})` component. It reuses `NAV[i].icon` and `--sp-section-<s>` with `--sp-section-<s>-bg`, which `theme.ts:57-62` already emits.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `PageHead.tsx` on Home, Runs and Launch

### UX-PAR-04 · major · The state rail disappears on Home cards, Home rows and the run header (CSS specificity)

- **Where:**
  - LiteHome: count cards have a 5 px left rail in the state colour; active rows and recent rows have a 4 px rail.
  - LiteRunDetail: a 4 px top bar in the run's state colour sits across the header card.
  - Build: `[data-rail]` sets `box-shadow: inset 4px…` at `web/src/runs/runs.css:53-75`. Three rules then override it: `.sp-card` (`runs.css:107`, same specificity, declared later), `.sp-cards li` (`:257`) and `.sp-list li` (`:286`, higher specificity). Each sets `box-shadow: var(--sp-shadow)`.
- **Evidence:** `app-home_light.webp` shows no rail on the Failed and Succeeded cards or on the five "Finished recently" rows. `app-run-detail_light.webp` shows no rail or bar on the header. The rail does show in the runs table, where `td[data-rail]` has no competing rule.
- **Problem:** ui-spec §3 makes the rail one of the three signals of a run state, with the icon and the word. On these surfaces it is silently lost. The tests do not see it, because the attribute is present.
- **API:** none needed.
- **Proposal:** compose the shadows in one rule:

  ```css
  [data-rail]{--rail:var(--sp-state-queued)} …
  .sp-card[data-rail], .sp-cards li[data-rail], .sp-list li[data-rail] {
    box-shadow: inset 4px 0 0 var(--rail), var(--sp-shadow);
  }
  ```

  Give the run header the top-bar variant (`inset 0 4px 0 var(--rail)`), as on the board. Add a computed-style test.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the rail and the card shadow in one `box-shadow`; `rail.test.tsx` (CR-P3PARA-05, open: the test relies on rule order)

### UX-PAR-05 · major · Run-state colours are hard-coded and drift from `spectio-tokens.css`; dark mode keeps the light rails

- **Where:** `web/src/runs/runs.css:3-26` defines `--sp-st-*` and `--sp-tx-*` with raw hex values.
  - Running text is `#1d4ed8`, where the token `--sp-state-running-fg` is `#1D5FC9`.
  - Review text is `#8a5a00`, where the token is `#8F5806`.
  - In dark mode the rails stay light: failed is `#dc3b3b`, where the dark token is `#EE5A5A`; running is `#3b82f6`, where the dark token is `#5B9BF8`.
  - `web/src/shell/theme.ts:35-95` emits no `--sp-state-*` token at all, so the `-bg` tints of `design/tokens/spectio-tokens.css:37-44` and `:78-85` are unavailable. That is why the task chips are grey (UX-PAR-22).
- **Evidence:** ui-spec §7, note 2026-10-30, Tokens: "The shell's CSS reads role tokens, never a raw hex (#89 rule 1)". The boards and the Legend use the token values, for example the Running word in `#1D5FC9` on LiteRuns.
- **Problem:** the colours diverge between the boards and the build, the dark theme is wrong, and every future screen will copy the raw values.
- **API:** none needed.
- **Proposal:** emit `--sp-state-<s>`, `--sp-state-<s>-fg` and `--sp-state-<s>-bg` for the 8 states, light and dark, from `theme.ts`. Make `runs.css` read only those.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `--sp-state-*` tokens, light and dark, in `theme.ts`; ui-spec §7 note 2026-10-31. Four role tokens are not in `spectio-tokens.css` yet (CR-P3PARA-06, open)

### UX-PAR-06 · major · On a run's page, the Runs item is not active, and the "Runs" crumb is marked as the current page

- **Where:** LiteRunDetail, LiteRunTasks, LiteRunLogs and LiteRunFailed render `LiteSidebar active="runs"`, and MLiteRunDetail tints the Runs key. Build: `web/src/shell/Sidebar.tsx:62` and `web/src/shell/TabBar.tsx:14` use `activeOptions={{ exact: true }}`, so nothing is active on `/runs/$id`. The breadcrumb `<Link to="/runs">` (`TopBar.tsx:40`) has the default fuzzy match, so TanStack marks it active and the crumb renders bold, as in `app-run-detail_light.webp`, where "Runs" is bold between Home and the run name. TanStack sets `aria-current="page"` on an active link **[to be validated]** with a test, since `web/node_modules` is absent here. If it does, two crumbs carry `aria-current="page"`.
- **Evidence:** `app-run-detail_light.webp` and `app-run-detail-phone_light.webp`: no sidebar item or tab is tinted, and the "Runs" crumb is bold.
- **Problem:** the user loses the "you are in Runs" cue on the deepest screen. A screen reader may also hear two current pages.
- **API:** none needed.
- **Proposal:** use `exact: true` for Home only and fuzzy matching for Runs and Launch, in the sidebar and the tab bar. Give crumb links `activeOptions={{ exact: true }}`, or set `aria-current` by hand, and add a test that checks exactly one `aria-current="page"` per nav on `/runs/$id`.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): Runs and Launch active on their child pages, crumb links exact

### UX-PAR-07 · minor · Sidebar: no active-run count badge, and the status pill has a dot instead of a check icon

- **Where:** LiteSidebar shows the Runs item with a "6" badge, with the screen-reader text ", 6 active runs" (`LiteSidebar.dc.html` items `hasCount`), and the badge moves to the corner on the folded rail. Its foot pill shows a ✓ icon. Build: `Sidebar.tsx:56-69` has no count; `:72-73` draws a 7 px dot.
- **Evidence:** ui-spec §2: "Review shows its count… Folds to a 92 px icon rail (labels hidden, counts become badges)." The 2026-10-30 note does not mention the count.
- **Problem:** the board's "6 active" signal is missing from every screen.
- **API:** the count can be served from `GET /runs:summary?group_by=state`, summing the `ACTIVE` keys. The shell would need one summary fetch, refreshed on stream frames.
- **Proposal:** add the badge, with its count also in screen-reader text, and use the check icon in the pill. The red pill already handles the "Server not reached" state.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the active-run badge, with screen-reader text, and the check icon

### UX-PAR-08 · major · Phone: the top bar's second row, with the back arrow, the page title as `h1` and the subtitle, is missing

- **Where:** MLiteTopbar (`hasTitle`, a 104 px bar: a back link, then `h1` at 19 px with a 12 px subtitle), used by MLiteRuns ("Runs · 15 runs · 6 active · live…"), MLiteRunDetail ("← rnaseq-2026-10-25 · Running · 3 of 8 stages done…") and MLiteLaunch ("Launch a workflow"). Build: `web/src/shell/TopBar.tsx:106-124` renders only the first row; each page keeps its own `h1` in the content (`RunDetailPage.tsx:365`).
- **Evidence:** ui-spec §2, note 2026-10-28: "On the phone the logo and the login node take a first row, and the back arrow and the page title a second". Inbox #89, rule 6: "The phone top bar's title row and back chevron come with Task 20's run detail." Task 20 shipped without them (`app-run-detail-phone_light.webp`, `app-launch-phone_light.webp`).
- **Problem:** there is no way back from a run on the phone other than the tab bar. The phone title also scrolls away with the content.
- **API:** none needed. The title and subtitle come from the page, as the crumb does (`usePageCrumb`).
- **Proposal:** extend `CrumbContext` to carry `{title, sub, back}`. Render the second row on the phone with a 44 px back link, named "Back to Runs", and make that title the page's `h1`. On the phone, the in-content title becomes a non-heading or is hidden.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `20f2de9`): the phone top bar's second row (`shell/layout.tsx`), with the page title as the `h1`, its subtitle, and a 44 px link named "Back to Runs" on a run; Home keeps its greeting in the page; ui-spec §4.11 note "UI parity B"

### UX-PAR-09 · major · Phone touch targets are 36 px, below the 44 px rule

- **Where:** MLiteLaunch's pinned Launch button is 48 px; its engine buttons and Load are 44 px or more. Build: Mantine's default buttons are 36 px. Measured on `app-launch-phone_light.webp`: Launch at y 728–763 (36 px), "Remove row 1" at 510–545 (36 px), "Add a parameter" at 556–591 (36 px). The same default applies to the engine buttons (`EngineButtons.tsx:26`), Cancel run (`RunDetailPage.tsx:379`) and the log buttons (`RunDetailPage.tsx:270`).
- **Evidence:** ui-spec §4.11, Phone rules: "touch targets ≥ 44 × 44 px of hit area". The shell keys meet it (`shell.css:54` comment).
- **Problem:** this fails the spec's own accessibility rule on the phone (WCAG 2.5.5 at AAA, the level Spectio chose).
- **API:** none needed.
- **Proposal:** add a phone theme override, `Button` with `size="md"` and a 44 px minimum height under `[data-layout=phone]`. Make the pinned Launch full width at 48 px, as on MLiteLaunch.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `20f2de9`, `d898847`): buttons, inputs, tabs and fold heads 44 px on the phone; the pinned Launch full width at 48 px

### UX-PAR-10 · major · Phone: tables where the boards and the spec ask for stacked cards

- **Where:**
  - MLiteRuns: one card per run (state with icon and duration, name, mark with pipeline and tasks, context), grouped under a collapsible "ACTIVE · 6" eyebrow, with the filter pills scrolling sideways.
  - MLiteRunDetail: a header card (marks, "Run 7T9V1W · 1 h 05 · live", "Head alive · tmux on login1", "Now · 64 tasks running in stages 4 to 7", coloured chips, full-width Cancel run and Copy…), and stage cards with bars.
  - MLiteHome: 2 × 2 count cards and a full-width "Launch a workflow" with its icon.
  - Build: the runs list is a five-column `<table>` on the phone (`RunsPage.tsx:159-202`; only Started is hidden, `shell.css:454`). The facts, processes, tasks and parameters are tables (`RunDetailPage.tsx:153-166`, `:47-83`, `:223-245`, `:432-449`); `runs.css:370-384` only hides some columns. The Home count cards use `minmax(180px,1fr)` (`runs.css:249-256`), so they fall to one per row at a 358 px content width.
- **Evidence:** ui-spec §4.11: "One column… no tables (stacked rows and cards)… filters and segments as horizontally scrolling pills". `app-run-detail-phone_light.webp` shows the facts as a two-column table.
- **Problem:** the phone layout is a squeezed desktop, which §4.11 rules out: "a separate, simpler layout below 768 px".
- **API:** none needed. The cards use the same fields.
- **Proposal:** on `data-layout=phone`, render `RunCard` lists instead of `<table>`, show the facts as label and value rows, and show stages and processes as cards with bars. Make the segment row scroll sideways (`flex-wrap: nowrap; overflow-x: auto`), and lay the Home cards out two by two.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `20f2de9`): run cards on the runs list and Home, process, task and parameter cards on the run, facts as rows, count cards two by two, segments that scroll sideways; ui-spec §4.3 and §4.11 notes "UI parity B". The folding "ACTIVE · n" group is not built (CR-P3PARB-02 r1, follow-up FU-P3-26)

---

## Home (`/`, LiteHome, MLiteHome)

### UX-PAR-11 · major · The "Where your runs go" card is missing

- **Where:** LiteHome aside, the second card. It has five dotted rows: Server (version, node, account), Heads (one tmux session per run, named `spectio-<run ID>`, "attach to it by hand"), Tasks ("sent to SLURM by Nextflow or Snakemake themselves"), Run directories (`runs_root`), and From a terminal. It folds to "login1 · SLURM". Build: `HomePage.tsx:142-155` has only "Your pipelines".
- **Evidence:** `design/README.md`, LiteHome row, Keeps: "on the desktop also recent runs, the pipeline directories of the recent runs and where runs go". The 2026-10-31 §4.2 note does not mention it either way.
- **Problem:** a first-time user does not learn where heads run or where files go, the facts the board puts on Home.
- **API:** can be served from `GET /version` (`version`, `node`, `account`, `executor`, `runs_root`). The wording must follow the executor: with `local`, the heads are not tmux sessions on a login node.
- **Proposal:** add the card through `useServer()`, with executor-specific text for Heads and Tasks.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): "Where your runs go" from `GET /version`; ui-spec §4.2 note "UI parity A"

### UX-PAR-12 · minor · Count cards have no detail line and are not links

- **Where:** each LiteHome card is an `<a>` to Runs, named "4 runs running, show them", with a detail line: "1 started from a terminal", "head not started yet", "latest: rnaseq-3.27-validation", "latest: fetch-geo-2610". Build: `HomePage.tsx:85-92` shows each card as an `<li>` with only the word and the count.
- **Evidence:** board. The 2026-10-31 §4.2 note says "states with no run are not shown"; that explains the hidden zero cards, and the board's four fixed cards are not a finding.
- **Problem:** the cards are a dead end. The board's quickest path, "show me the failed ones", is missing.
- **API:** the detail lines can be served from the lists Home already loads: active `origin`, and the newest ended run by state. The links need the Runs filter in the URL (`/runs?state=failed`), which `RunsPage.tsx:54` keeps in component state only.
- **Proposal:** put the Runs filter and `q` in the URL search params, make each card a link to them, and add the detail line.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): detail lines, and cards that link to `/runs?state=`; the `state` and `q` filters in the URL (`q` in `ac5ae2c`, CR-P3PARA-01); zero cards stay hidden

### UX-PAR-13 · minor · The subtitle wording differs

- **Where:** LiteHome reads "4 runs running, 1 queued and 1 cancelling · live, updated 4 s ago"; MLiteHome reads "4 running, 1 queued, 1 cancelling". Build: `HomePage.tsx:62-67` reads "0 active runs · live, updated 0 s ago".
- **Evidence:** the board, and `app-home_light.webp`.
- **API:** can be served from the summary groups.
- **Proposal:** list the active states that have a non-zero count, as the board does, and read "No run is active" at zero.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the active states with runs, or "No run is active"

### UX-PAR-14 · minor · Active and recent rows: layout, failure context and the terminal marker

- **Where:** LiteHome's active row has a mark, the name, "pipeline · started …" and, on the right, the state word over a context line ("from a terminal · 288 / 384 tasks"). Its recent row has a fixed 120 px state column, the mark, the name over "pipeline · context", and the time on the right; the failed context reads "exit 175 ×2 · RSEM_CALCULATEEXPRESSION (H1_REP2)". "All runs →" sits right-aligned above the list. Build:
  - `HomePage.tsx:127-136` puts the state word inline before the name, and a failed run's context is the raw `failure.message` or blank (UX-PAR-16).
  - `:104-113` has no "from a terminal" text on active rows.
  - `:119` puts an underlined "All runs" below the list.
- **Evidence:** the board, and `app-home_light.webp`.
- **API:** the terminal marker can be served from `origin`. The failed context can be served as `failure.class` with the message. "exit N · PROCESS (tag)" is **not** servable from `Run`: `failure` has `task_id`, but no process, tag or exit code.
- **Proposal:** match the board's grid. Fall back as in UX-PAR-16. Ask P1 Task 29 to add `process`, `tag` and `exit_code` to `failure`, or to `summary.last_failure`.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the layout, the terminal marker and the class fallback; "exit N · PROCESS (tag)" stays for P1 Task 29

### UX-PAR-15 · minor · Your pipelines: not links, no mark

- **Where:** each LiteHome quick item is an `<a aria-label="Launch nf-core/rnaseq 3.27.0">` with a mark, and the card says "Opens the launch form with the directory filled in; parameters start from their defaults." Build: `HomePage.tsx:145-154` shows text only.
- **Evidence:** ui-spec §4.2, note 2026-10-31: "Your pipelines, … as text (launching from one with the form prefilled waits for Copy to a new launch, §4.6)". This excludes the links on purpose. The board asks only for the directory to be filled in, which needs no `:launch-template`.
- **Proposal:** add the mark now (UX-PAR-01). For the link, ask Thomas through the inbox whether `/launch?location=<dir>` (location only, then Load) may come before Copy to a new launch.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the mark; the links stay out on purpose

---

## Runs (`/runs`, LiteRuns, MLiteRuns)

### UX-PAR-16 · major · A failed run with an empty engine message shows a blank context line

- **Where:** LiteRuns, State column: every failed row has a context line ("exit 1 · DEEPVARIANT_RUNDEEPVARIANT (NA12878)", "2 jobs failed after retries"). Build: `web/src/runs/RunState.tsx:41-42` returns `failure.message` whenever it is a string. Nextflow's projector stores `data.errorMessage or ""` (`projector/nextflow.py:126`), so the context is blank.
- **Evidence:** `app-runs_light.webp`: four Failed rows have an empty second line, and two show a samplesheet path as the whole context.
- **Problem:** a failed run gives no reason in the list. A bare path read as "the reason" is confusing.
- **API:** `failure.class` can be served, and so can `summary.tasks.failed`.
- **Proposal:** when the message is empty, show "<class word> · <n> failed" ("tool error · 2 tasks failed"). Otherwise show "<class word> · <message>", clamped to two lines. This needs a class-word map (`tool_error` → "tool error", `head_lost` → "head lost", `engine_fault` → "engine error"). Same fix on Home (UX-PAR-14).
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `failureText`: "<class word> · <message>" or "<class word> · n tasks failed", never blank

### UX-PAR-17 · minor · Workflow and Tasks cells: the version's line and Snakemake wording

- **Where:** LiteRuns shows "nf-core/rnaseq 3.27.0", with the mark and the version muted on the same line. Its Tasks cell reads "288 / 384 known so far" while a Nextflow run runs, "31 / 96 jobs" for Snakemake, "7 retried", and "2 failed · jobs". Build: `RunsPage.tsx:187-188` puts the version on its own line (`.sp-muted` is `display:block`); `:190-195` always reads tasks.
- **API:**
  - "jobs" can be served from `workflow.engine`.
  - "known so far" can be served (engine `nextflow` and an active state).
  - "n retried" **cannot**: `Run.summary.tasks` has no retries.
- **Proposal:** put the version inline and use the engine word. Leave "retried" until `summary.tasks.retried` exists.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): "jobs", "known so far" and the inline version; "n retried" stays for when `summary.tasks` has retries

### UX-PAR-18 · minor · Small differences in the head, toolbar and footer

- **Where:**
  - The LiteRuns subtitle adds "heads in tmux sessions on login1".
  - The filter field has a magnifier icon.
  - The "From a terminal" chip has a terminal icon.
  - A footer reads "13 of 15 runs · newest first".
  - Build: `RunsPage.tsx:117-123`, `:131-137` (a bare `<input type=search>`), `:179` and `:204-210`.
- **API:** can be served from `/version` and from the summary total.
- **Proposal:** add these. Keep "of N" only while the active filter's total is known from `runs:summary`; ui-spec §4.11 says to show a count only when a total exists.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): where heads run, the icons, and the "n of N runs · newest first" footer

---

## Run detail (`/runs/$id`: LiteRunDetail, LiteRunDetailSnakemake, LiteRunTasks, LiteRunLogs, LiteRunFailed, MLiteRunDetail)

### UX-PAR-19 · minor · The header's order and content

- **Where:** LiteRunDetail's header is a card with the state-colour top bar (UX-PAR-04), a 48 px pipeline-mark tile, then the `h1` with the short ID muted beside it, then a line: state with icon, "3 of 8 stages done · 4 running · 524 / 803 tasks · 1 h 05 · live, updated 4 s ago". LiteRunFailed's line adds "2 jobs failed after their retries … · ended Sun 06:57". Build: `RunDetailPage.tsx:363-383` puts the short ID first on the line and has no tile and no "ended …".
- **API:** all of it can be served (`ended_at`, `summary.tasks.failed`).
- **Proposal:** match the board's order, and add "ended <when>" on terminal runs.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the board's order, and "ended <when>" on an ended run

### UX-PAR-20 · major · Snakemake runs are described in Nextflow words

- **Where:** LiteRunDetailSnakemake reads "242 / 347 jobs", "9 rules", "Rule, first-seen order", "Jobs done", "1 of 1 job", and its intro says "each with its rules in the order Snakemake first reported them". Build: `RunDetailPage.tsx:53`, `:90-92` and `:372` always read "tasks", "Processes" and "Process, first-seen order"; the Tasks panel says "Process" (`:209`, `:228`).
- **Evidence:** ui-spec §4.4, stages note: "opening to its processes (Nextflow) or rules (Snakemake)". The board.
- **Problem:** Snakemake users see words their engine does not use.
- **API:** can be served from `workflow.engine`.
- **Proposal:** add one `words(engine)` helper: `{unit: "task" | "job", group: "process" | "rule"}`. Use it on Runs, Home and the run detail.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `words(engine)` on Runs, Home and the run detail; some accessible names still say Tasks (CR-P3PARA-07, open)

### UX-PAR-21 · major · Facts: the layout, where they sit, their labels and missing rows

- **Where:**
  - LiteRunDetail puts Facts **inside the header card**, which every tab shares (LiteRunTasks and LiteRunLogs show them too). Facts are a collapsible section with an ⓘ icon, folding to "nf-core/rnaseq 3.27.0 · Nextflow 25.10.4 · head alive".
  - Its four-column grid of label and value pairs reads:
    - Pipeline (with mark; "(no version declared)" when there is none)
    - Engine · profile ("Nextflow 25.10.4 · singularity", with mark)
    - Started · ended
    - Duration
    - Head session
    - Head (Alive/Exited)
    - Login node
    - Exit code ("— (still running)")
    - Pipeline directory
    - Run directory
    - Executor
    - Failure ("tool_error · 2 jobs failed")
  - Build: `RunDetailPage.tsx:138-167` is a two-column, ten-row `<table>` in the Summary tab only. The engine shows as raw lower case ("nextflow 26.10.4"). The head is merged into one cell ("18823.3644058 · exited · on login1"). Run directory and Executor are absent.
- **Evidence:** the boards, and `app-run-detail_light.webp`. ui-spec §4.4, run tools note: "One run header, shared by every tab of the run (Summary, Tasks, Parameters, Logs)". The 2026-10-31 note puts the facts table under Summary; that records the build and does not exclude the board's layout.
- **Problem:** the facts take half a screen on desktop and vanish on the other tabs, and the engine name is not capitalised.
- **API:** all of it can be served. The run directory is `runs_root/<id>` from `/version` for driven runs, and absent for `cli-observed`. The executor comes from `/version`.
- **Proposal:** move the facts into the shared header (it becomes `RunHeader.tsx`, the file P1 Task 32 already plans), as a grid in a `FoldSection`, with the board's labels, `NAMES[engine]` and the missing rows.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): `RunHeader.tsx`: facts as a folding grid in the header that every tab shares; ui-spec §4.4 note "UI parity A"

### UX-PAR-22 · major · Task count chips: no label, no state tint, zeros hidden, no retried count

- **Where:** LiteRunDetail's chip row is "Tasks" then 524 succeeded (green tint), 64 running (blue), 215 pending (grey), 0 failed (red), 7 retried (amber); LiteRunFailed's row includes "30 not scheduled". Build: `RunDetailPage.tsx:358` and `:413-420` show only non-zero states, as neutral grey `.sp-chip`, with raw names ("not scheduled", "stored"), no "Tasks" label and no retried count.
- **API:** can be served: `task_counts`, and retried as the sum of `processes[].retries`.
- **Proposal:** show a fixed set (succeeded, running, pending including submitted, failed always, retried, then any other non-zero state). Each chip uses its `--sp-state-*-bg` and `-fg` tint (UX-PAR-05), with a "Tasks" label before the row. The same row goes on the phone header card.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): tinted chips with a label, failed and retried always

### UX-PAR-23 · major · The Summary aside is missing

- **Where:** LiteRunDetail's right column holds:
  - "Open the head by hand": the text, a dark code block `ssh login1` / `tmux attach -t spectio-run_…`, and a "Copy commands" button named "Copy the two commands to open the head by hand";
  - "Engine log · last lines": the last 6 lines and "All logs: head output, head errors, engine log →";
  - "Parameters": folded, "4 set at launch";
  - "Results and reports".

  LiteRunFailed's aside holds "Head errors · last lines" and "The head has ended · exit 1" (folded). Build: `RunDetailPage.tsx:410-424` has no aside; the Summary is a single column.
- **Evidence:** `design/README.md`, LiteRunDetail row, Keeps: "how to attach to the head", "the run's own engine log on Logs…". The 2026-10-31 note lists none of these as not built.
- **API:**
  - The attach commands can be served from `head.session` and `head.node`. For `executor=local` there is no ssh; show the session or PID instead.
  - The engine log tail and the head errors tail can be served from `/logs?source=engine|head-err` (64 KiB, tailed on the client). Fetch once when the section opens, and on Reload, not on every frame.
  - Parameters can be served from `RunDetail.params`.
  - The head-ended card can be served from `head`.
  - **Results and reports cannot** be served: no route, P1 Task 31.
- **Proposal:** add the aside at 1200 px and wider, stacked under the main column below that, with the four servable cards. Results waits for Task 31.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the head by hand, the log tail, the head ended and Parameters; Results and reports stay for P1 Task 31. The tail's "Empty." is in `ac5ae2c`; its level tint does not show (CR-P3PARA-04, open). The copied commands are not quoted (SEC-P3PARA-01, open)

### UX-PAR-24 · major · Stage rows and the process table lose state colour and icons, progress bars and context

- **Where:**
  - LiteRunDetail stage row: number, name, a "Detected" chip, an "N processes" line, the state word with its icon and colour (✓ Done, ▶ Running, ◷ Pending), a bar (indigo when done, blue when running) with "n of m tasks", and a chevron.
  - Process table: the state word in colour, a bar in "Tasks done", and the Running count in blue.
  - Section intro: "Eight stages detected, … All tasks →". Closing legend: "Pending: no task has started. Running: …".
  - Build:
    - `RunDetailPage.tsx:105-116`: the stage word is plain text (`stageWord`), with no icon, no bar and no process count.
    - `:70`: the process word is plain text.
    - No intro, legend or "All tasks" link.
    - `.sp-stage > summary { display:flex }` (`runs.css:326`) suppresses the native disclosure marker in Chromium, so a stage row likely shows no open or closed cue at all. **[to be validated]** on a run with stages, since the synthetic run in the shot has none.
- **Evidence:** `design/README.md`, LiteRunDetail row, Keeps: "the stages and their processes or rules … (neutral indigo bar when done, running blue when active)". `Drops` lists only the "stage gauge", which is the emblem-shaped gauge of §3.2, not these bars. ui-spec §4.4 stages note: "each with its state word and icon".
- **Problem:** colour and icon are missing on the screen with the most states. Without a chevron, a stage row does not look openable.
- **API:** can be served from the counts in `/stages` and `/processes`.
- **Proposal:** add a `StageWord` and `ProcessWord` component (icon and word, colour from the tokens); a 72 px bar using `--sp-indigo-500` when done and `--sp-state-running` when running, with the value as text beside it; an explicit chevron in the summary; the intro and the legend.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): stage rows and the process table with state words, tones and bars, the intro and the legend

### UX-PAR-25 · major · A failed run has no "Why it failed" section

- **Where:** LiteRunFailed's main column opens on "Why it failed" (⚠ icon, open by default). It holds a `tool_error` chip, a headline ("2 jobs failed on their last attempt, and Snakemake stopped the run"), an explanation, "Tasks, filtered to Failed →", and then one card per failed job. Build: the failure is only one fact row, "class: message" (`RunDetailPage.tsx:151`).
- **Evidence:** ui-spec §4.4, run tools note, Failure summary: "On a failed run, 'Why it failed' opens first."
- **API:**
  - The run-level part can be served now: `failure.class`, `failure.message`, `summary.tasks.failed`, and a link to the Tasks tab with `state=failed`.
  - The per-job cards **cannot**: they need SLURM state and reason, memory and time asked and used, and the last lines, which come in P1 Tasks 29 and 32.
- **Proposal:** add the section now with the run-level part, open first on failed runs. Leave a slot for the job cards of Task 32.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the run-level part; the per-job cards stay for P1 Tasks 29 and 32

### UX-PAR-26 · major · Tasks tab: the filters, the state display and live refresh

- **Where:**
  - LiteRunTasks has a segmented state filter with counts ("All 803 · Running 64 · Pending 215 · Succeeded 524 · Failed 0 · Retried 7"), and a Process select reading "All processes (67)".
  - Above the table, a line reads "Sorted by last change · live, updated 4 s ago". Below it, a footer reads "12 of 803 tasks".
  - Each row has a rail in its state colour. The Task cell reads "PROCESS (tag)", and the State cell is the coloured word ("Failed · retried").
  - Build:
    - `RunDetailPage.tsx:197-206`: a native `<select>` of nine raw lower-case states (it includes "stored", "aborted" and "not scheduled").
    - `:212-215`: options show the full qualified process names.
    - `:228-240`: Process and Tag in separate columns; the state as lower-case text with no icon, colour or rail.
    - `:169-186`: no `useFrames`, so the table **does not refresh** while the run runs.
- **API:**
  - The state counts can be served from `task_counts`, the process total from `/processes`, and the live refresh from the stream.
  - A "Retried" filter **cannot**: there is no retry or attempt filter on `/tasks`.
  - The columns Attempt, SLURM job, Exit, Duration, CPUs, CPU %, Memory, Peak memory, Time limit and Files **cannot**: `Task` lacks them (P1 Tasks 28, 29 and 32).
- **Proposal:** use segmented `<button aria-pressed>` filters, mirroring the Runs filters, with counts (Retried waits for the API). Use the last segment of the process name in options, with the count. Add a task-state word with icon and rail, refetch on frames while the run is active, and add the count line.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the filters with counts, the state words, the rails and live refresh; the Retried filter and the other columns stay for P1 Tasks 28, 29 and 32

### UX-PAR-27 · minor · Logs tab: nothing open by default, and Reload, Download, the description and the job-files line are missing

- **Where:**
  - LiteRunLogs has a segmented control (Head output, Head errors, Engine log), with **Engine log open** on arrival.
  - Beside it: "Nextflow's log of this run · last 64 KiB · loaded when you open it", then Reload and "Download last 64 KiB".
  - Below: a File row with the path and Copy, the log with error lines in red and warning or retry lines in amber, and the footer "Each job's own files (.command.log, …): open a job in Tasks →".
  - Build: `RunDetailPage.tsx:256-282` shows three Mantine buttons and nothing open.
- **Evidence:** ui-spec §4.4, run tools note, Run logs: "names the file each one reads (with its full path to copy), and adds a line 'Each job's own files: open a job in Tasks'".
- **API:**
  - Opening the engine log by default, Reload, Download (a Blob of the text already fetched), the description, the footer and line tinting can be served. Tinting must stay secondary: the level word is already in the text.
  - **The file path cannot**: `/logs` returns text only. Deriving it on the client from `runs_root` and `.spectio/<engine>.log` would hard-code a layout. Add the path to the API in P1 Task 32.
- **Proposal:** add the servable parts now, and the path with Task 32.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the engine log open by default, Reload, Download (attached anchor in `ac5ae2c`, CR-P3PARA-08) and the footer; the file path stays for P1 Task 32

### UX-PAR-28 · minor · Header actions: the Copy menu, Resume and Copy to a new launch

- **Where:** LiteRunDetail's header has "Copy ▾" (`aria-haspopup="menu"`); LiteRunFailed's has Resume (primary), Copy to a new launch, and Copy ▾; MLiteRunDetail's has "Copy…". Build: `RunDetailPage.tsx:378-382` has only Cancel run.
- **Evidence:** ui-spec §4.4, note 2026-10-31: "Not built in 0.0.1 yet: the Copy menu, Resume and Copy to a new launch (P1 Tasks 30 and 32)".
- **API:** `:relaunch` and `:launch-template` are not in the snapshot. A Copy menu of "Run directory" and "Run ID" alone could be served now.
- **Proposal:** leave these to P1 Tasks 30 and 32.
- **Found by:** ux-reviewer
- **Status:** open (deliberately later in 0.0.1)

### UX-PAR-29 · minor · The Cancel dialog is shorter than LiteCancelDialog, and its confirm label differs

- **Where:**
  - LiteCancelDialog adds a run-specific sentence after the plan's: "rnaseq-2026-10-25 has 64 running and 215 pending tasks; they will not finish. Results already written stay in the output directory."
  - It adds a grey box: Ctrl-C to the engine in its tmux session, then SIGTERM and SIGKILL after 60 s each, "The run shows Cancelling, then Cancelled".
  - Its confirm button reads "Cancel run".
  - Build: `RunDetailPage.tsx:385-401` has the plan's sentence only, and the button reads "Cancel the run".
- **Evidence:** ui-spec §4.4, note 2026-10-31: "two buttons, Keep running (focused first) and Cancel the run". The spec and the build agree; the board's label is the outlier.
- **API:** the counts can be served from `task_counts`. The escalation text must follow the executor: tmux Ctrl-C with SLURM; process-group signals with the local executor (`runner/local.py:108`, `headscript.py:37`).
- **Proposal:** add the run-specific sentence and an executor-specific box. Change the board's confirm label to "Cancel the run" when the findings are applied.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parA, 2026-10-31, `28a241c`): the run's sentence and the executor's box; the board's label waits for `/apply-findings`

---

## Launch (`/launch`: LiteLaunch, LiteLaunchSnakemake, MLiteLaunch)

### UX-PAR-30 · major · Schema groups are plain fieldsets: no icon, description, counts, status summary or folding

- **Where:**
  - In LiteLaunch, each group is a sub-card with an icon tile (from `fa_icon`: folder, dna, scissors…), its title and description, and "4 parameters · 2 required".
  - On the right of each group: "2 required · filled" in green, "2 changed" in amber, or in LiteLaunchSnakemake "1 required field empty" in red, or "defaults". A chevron follows. Groups with changes or issues open, the others fold.
  - Above the groups: "One section per schema group · 4 values differ from their defaults".
  - Field hints add the type and format ("string · file-path"), and "changed · default 5" on a changed field.
  - Build: `LaunchPage.tsx:334-349` (`fieldset`/`legend`), `schemaFields.ts:19-22` (a `Section` has no description or icon), and `:416-417` (the hint is "help · default X").
- **Evidence:** ui-spec §4.6: "One collapsible section per schema group, each with a light line icon mapped from the group's `fa_icon`, a summary on the right ("2 required", "1 issue", "2 changed") and a chevron; sections with issues or changes open by default." The 2026-10-30 note does not exclude it.
- **Problem:** a 114-parameter nf-core form is one long flat page.
- **API:** can be served: `fa_icon`, `description` and `format` are in `Inspected.schema`, and "changed" compares the field's value with its default on the client.
- **Proposal:** extend `Section` with `{description, icon}`, map `fa_icon` names to a small set of lucide paths with a neutral fallback, and render the groups with `FoldSection` (UX-PAR-02).
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `d898847`): each group a `FoldSection` with a line icon from `fa_icon` (`groupIcon`), description, counts and status, open on an issue or a change; ui-spec §4.6 note "UI parity B". The field hints sit above the input (CR-P3PARB-06 r1, FU-P3-26)

### UX-PAR-31 · major · Snakemake: a nested config map renders as one JSON textarea, not as a group of fields

- **Where:** in LiteLaunchSnakemake, `ref` is a section with species (string), release (integer) and build (string); `trimming` is a section with an `activate` checkbox; `pca` folds to "2 keys". Build: `schemaFields.ts:28-34` turns any non-scalar property into `type: "json"`, and `:69` puts every top-level property in one "Parameters" section. So `ref` is a JSON textarea.
- **Evidence:** ui-spec §4.6: "For Snakemake, the form comes from `config.schema.yaml` when present, otherwise it is inferred from the value types in `config/config.yaml` (nested maps become sections)".
- **Problem:** Snakemake users must type JSON for ordinary nested settings.
- **API:** can be served: the `properties` of nested objects are in `Inspected.schema`.
- **Proposal:** for a schema without `$defs`, make each top-level `type: object` with `properties` its own section, with dotted keys (`ref.species`). Rebuild the nested object on submit, and keep `json` only for arrays and free-form maps. The 422 field mapping (`formKey`) must accept dotted names.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `d898847`, `614b81f`): for Snakemake only, nested maps as sections of dotted keys, rebuilt on submit, a map with one value set sent whole; `formKey` maps `params.ref.release`; a Nextflow map stays one JSON field

### UX-PAR-32 · major · No params.json or config.yaml preview

- **Where:** in the LiteLaunch aside, a dark card "params.json preview" shows only the values set, with "Only values you set · written to the run directory and passed with -params-file". LiteLaunchSnakemake shows "config.yaml preview … passed with --configfile". Build: `LaunchPage.tsx:356-399` has no such card.
- **Evidence:** ui-spec §4.6, Aside: "params file preview". `design/README.md`, LiteLaunch row, Keeps: "params preview".
- **Problem:** the user cannot see exactly what will be sent before pressing Launch.
- **API:** can be served on the client: it is the `params` object that `submit()` builds (`LaunchPage.tsx:187-192`).
- **Proposal:** add a folding preview card, a `<pre>` of the params built through one shared function so the preview and the request cannot differ. Show YAML for Snakemake.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `d898847`, `35ed465`): the preview in the aside, built by the same `buildParams` as the request; YAML for Snakemake

### UX-PAR-33 · minor · Pipeline card and "Where it runs": smaller differences

- **Where:**
  - In LiteLaunch, the Loaded card has a mark tile and a "✓ Loaded" status on the right (build `LaunchPage.tsx:289-300` has neither).
  - The Profile hint is engine-specific: "From the pipeline's nextflow.config · passed as -profile" or "From the pipeline's profiles/ directory · passed as --workflow-profile" (build `:315` is generic).
  - "Where it runs" adds a Tasks row ("sent to SLURM by Nextflow (executor slurm)"), the Engine row reads "Nextflow 25.10.4, in a tmux session on login1" with its mark, and a closing line says "The executor, the login node and the run directory are fixed for this server: there is nothing to choose in 0.0.1". Build `:357-375` has none of these.
  - The executor's case is inconsistent: "local" in the Launch aside, "LOCAL" in the sidebar foot (`Sidebar.tsx:80`).
- **API:** all of it can be served (`/version`, `Inspected`).
- **Proposal:** add these, and use one `executorLabel()` helper in both places.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `d898847`): the Loaded card's mark and status, the engine's profile hint, the Engine and Tasks rows and the closing line of "Where it runs", `executorLabel()` in the aside, the sidebar foot, Home and the run's facts

### UX-PAR-34 · minor · Phone: the pinned Launch bar has no summary

- **Where:** MLiteLaunch's pinned bar reads "nf-core/rnaseq 3.27.0 · Nextflow · singularity · 2 values changed" beside a large Launch button. Build: `app-launch-phone_light.webp` shows a bare 36 px Launch (size: UX-PAR-09), with its reason when disabled.
- **API:** can be served on the client.
- **Proposal:** show the summary when Launch is enabled and the reason when it is not, in the same slot, linked by `aria-describedby`.
- **Found by:** ux-reviewer
- **Status:** applied (P3-parB, 2026-10-31, `d898847`): the summary or the reason above the 48 px Launch, named by `aria-describedby`

---

## Fix in the parity step, or leave out of 0.0.1

"Later in 0.0.1" means a P1 task that is still to come owns the item, because the 0.0.1 API cannot serve it yet. "Leave out" means a dated note excludes it on purpose.

| ID | Decision | Why (spec quote or API) |
|---|---|---|
| UX-PAR-01 | **Fix** (engine mark now; nf-core mark once a rule or field exists) | §4.3 UX-323: "the 0.0.1 screens show the pipeline mark … and the engine mark"; the 10-31 note's "no mark yet" is not an exclusion |
| UX-PAR-02 | **Fix** | §4.4 UX-318; the 10-31 note: "Not built in 0.0.1 yet: … the toggled sections" |
| UX-PAR-03 | **Fix** | §7: "Page head: tinted 48 px icon tile" |
| UX-PAR-04 | **Fix** | bug; §3 rail, icon and word |
| UX-PAR-05 | **Fix** | §7 note 2026-10-30: "never a raw hex" |
| UX-PAR-06 | **Fix** | bug |
| UX-PAR-07 | **Fix** | §2 counts and badges; one summary fetch |
| UX-PAR-08 | **Fix** | §2 note 2026-10-28; inbox #89 rule 6 |
| UX-PAR-09 | **Fix** | §4.11: "touch targets ≥ 44 × 44 px" |
| UX-PAR-10 | **Fix** | §4.11: "no tables (stacked rows and cards)" |
| UX-PAR-11 | **Fix** | design/README Keeps "where runs go"; `/version` |
| UX-PAR-12 | **Fix** (detail line and links); zero cards stay hidden | §4.2 10-31: "states with no run are not shown" |
| UX-PAR-13 | **Fix** | summary groups |
| UX-PAR-14 | **Fix** layout, terminal marker and class fallback; **later in 0.0.1** for "exit N · PROCESS (tag)" | `failure` has no process, tag or exit code (P1 Task 29) |
| UX-PAR-15 | **Fix** the mark; **leave out** the links | §4.2 10-31: "as text (launching from one with the form prefilled waits for Copy to a new launch, §4.6)" |
| UX-PAR-16 | **Fix** | bug |
| UX-PAR-17 | **Fix** "jobs", "known so far" and the inline version; **later** for "n retried" | `Run.summary.tasks` has no retries |
| UX-PAR-18 | **Fix** | `/version`, summary |
| UX-PAR-19 | **Fix** | servable |
| UX-PAR-20 | **Fix** | §4.4: "processes (Nextflow) or rules (Snakemake)" |
| UX-PAR-21 | **Fix** | §4.4 run tools: "One run header, shared by every tab"; P1 Task 32 already plans `RunHeader.tsx` |
| UX-PAR-22 | **Fix** | `task_counts`, `processes[].retries` |
| UX-PAR-23 | **Fix** attach, engine log tail, Parameters, head errors and head ended; **later in 0.0.1** for Results and reports | no results route (P1 Task 31) |
| UX-PAR-24 | **Fix** | design/README Keeps the bars; Drops only the §3.2 gauge |
| UX-PAR-25 | **Fix** the run-level part; **later in 0.0.1** for the per-job cards | P1 Tasks 29 and 32: SLURM and resources are not in the API |
| UX-PAR-26 | **Fix** the filters, state words, rails and live refresh; **later in 0.0.1** for the Retried filter, Attempt, SLURM job, Exit, Duration, resources and Files | `Task` has only id, process, tag, name, state, stage_id (P1 Tasks 28, 29 and 32) |
| UX-PAR-27 | **Fix** default open, Reload, Download and the footer; **later in 0.0.1** for the file path | `/logs` returns no path (P1 Task 32) |
| UX-PAR-28 | **Later in 0.0.1** | §4.4 10-31: "Not built in 0.0.1 yet: the Copy menu, Resume and Copy to a new launch (P1 Tasks 30 and 32)" |
| UX-PAR-29 | **Fix** the sentence and the box; **update the board's** label | §4.4 10-31: "Keep running (focused first) and Cancel the run" |
| UX-PAR-30 | **Fix** | §4.6: "One collapsible section per schema group, each with a light line icon mapped from the group's `fa_icon`" |
| UX-PAR-31 | **Fix** | §4.6: "nested maps become sections" |
| UX-PAR-32 | **Fix** | §4.6 Aside: "params file preview" |
| UX-PAR-33 | **Fix** | servable |
| UX-PAR-34 | **Fix** | servable |

**Board elements that stay out of 0.0.1, with the quote that excludes them** (not findings: the build is right):

| Board element | Spec quote |
|---|---|
| LiteLaunch: a Launch button in the page head | §4.6 note 2026-10-30: "One Launch button, at the foot of the aside… The page head has none (UX-227: 0.0.1 shows less than the boards)." |
| LiteLaunch: the Revision field always drawn | §4.6 note 2026-10-30: "Revision is shown only once the Pipeline field reads as a repository, not drawn disabled (UX-G2-08)." |
| LiteLaunch: the "Prefilled from …" banner and "Clear and start empty" | §4.4 note 2026-10-31: "Not built in 0.0.1 yet: … Copy to a new launch (P1 Tasks 30 and 32)" (later in 0.0.1) |
| LiteHome: four fixed count cards, zeros included | §4.2 note 2026-10-31: "states with no run are not shown" |
| LiteRuns: stage gauge, Rows mode, Compare (not drawn on the lite board, listed for completeness) | §4.3 note 2026-10-31: "Rows mode, the gauge and Compare are not in 0.0.1." |
| LiteTopbar and MLiteTopbar: search, notifications, account | Both board and build show them disabled, "(not in 0.0.1)"; `design/README.md`, shell row, Drops: "projects, search, notifications, settings, profile, admin" |

**Board updates for the apply step:**

- LiteCancelDialog: change the confirm label to "Cancel the run" (UX-PAR-29).
- LiteLaunch: add a 2026-10-30 note on the board, beside the page-head Launch and the always-drawn Revision, saying that 0.0.1 shows neither (UX-227, UX-G2-08), so the next comparison does not flag them.
