# Design sources

- **`tokens/spectio-tokens.css`.** Design tokens v0.2 as CSS custom properties:
  - surfaces, lines and text;
  - accent;
  - the 8 run states;
  - section colours (Workflows = coral 700 `#A54666`, distinct from depictio's Dashboards orange);
  - actors and data-viz colours;
  - the Sky scale;
  - dark mode.
- **`ui-canvas/`.** Snapshot of the UI canvas: one `.dc.html` file per board, and `canvas.json` for the board positions and pages (structure, screens, shared shell, mobile).
  - The boards use a small template syntax: `sc-for`, `sc-if` and `dc-import` for shared components such as `AppSidebar`, `AppTopbar`, `AdminNav` and `MobileTabbar`.
  - [`tools/canvas/render.js`](../tools/canvas/render.js) renders any board to PNG without the canvas host.
- **`brand-canvas/`.** Logo and colour explorations from before the name Spectio was chosen. Some file names keep the earlier working names. `SpectioUIColors` is the current UI palette board.

## 0.0.1 lite boards

The page **0.0.1 lite** of `ui-canvas/canvas.json` holds the screens of the 0.0.1 walking skeleton ([`mvp-0.0.1.md`](../docs/specs/mvp-0.0.1.md), [dev-env §15.1](../docs/specs/dev-environment-and-testing.md#151-capabilities-by-version)). They are cut down from the full boards of 2026-10-26, which stay unchanged as the reference for later versions. They keep the look: the tokens, the run-state colours with an icon and a word, and the shell. The Spectio logo is the favicon only: the top bar starts with the breadcrumbs, with no logo or wordmark (Thomas, 2026-10-28; [ui-spec §2 note](../docs/specs/ui-spec.md#2-main-navigation)). The Nextflow, Snakemake and nf-core logos mark the pipeline on the run, launch and home boards (files in `docs/assets/logos/`, which `tools/canvas/render.js` also reads). Each section of the run detail and launch boards is a collapsible `<details class="cx">` with a light line icon, a summary shown when closed and a chevron. Desktop boards render at 1440 × 1180, phone boards at 390 × 844.

| Board | Derived from | Keeps | Drops |
|---|---|---|---|
| `LiteHome`, `MLiteHome` | `Overview`, `MOverview` | the fourth 0.0.1 screen (Home kept, Thomas, 2026-10-28): counts by state from `runs:summary` with no time window, active runs with their task counts, a terminal run marked; on the desktop also recent runs, the pipeline directories of the recent runs and where runs go | project switcher, gates waiting, review queue, depictio, charts, "last 24 h" |
| `LiteRuns`, `MLiteRuns` | `RunsTable`, `MRuns` | columns Run, State, Workflow, Tasks, Started, Duration; name filter and state filters (`state=`, `q=`); a neutral "From a terminal" chip; Load more; live, updated N s ago | stage gauge, Rows mode, compare, projects, users, environments |
| `LiteLaunch`, `LiteLaunchSnakemake`, `MLiteLaunch` | `Launch`, `LaunchSnakemake` | pipeline directory and Load, detected engine, profile, optional run name, schema sections, params preview, Launch disabled with its reason; on the phone a sticky Launch bar | samplesheet and file checks, stepper, environment and gate pickers, relaunch, parameter history |
| `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunTasks`, `LiteRunLogs`, `MLiteRunDetail`, `MLiteRunTasks`, `MLiteRunLogs` | `RunDetail`, `MRunDetail` | header with "n of m stages done · k running", state, short ID, facts (Head session, Head alive or exited, Login node, Exit code; no PID), task counts, the stages and their processes or rules as the [ui-spec §4.4 note](../docs/specs/ui-spec.md#44-run-detail) says (neutral indigo bar when done, running blue when active); the stages drawn are the stage-detection spike's output for nf-core/rnaseq 3.27.0 and mosaicatcher-pipeline v2.5.1 (`tests/pipelines/real/stages/expected/` on branch `autopilot/apply-stages`), with fixture counts; tasks table, logs, how to attach to the head | stage gauge, DAG, timeline, resource charts, gates, review cells, outputs, lineage, relaunch |
| `LiteRunFailed` | `RunFailed` | failure class and the engine's message, failed jobs with their logs, a pipeline with no stage: the flat rules list in first-seen order with a state word and the line "No stages for this pipeline", head errors | `sacct` evidence, suggested fixes, resume and relaunch |
| `LiteCancelDialog`, `MLiteCancelSheet` | — | the P1 Task 20 confirm text verbatim, what Cancel does to the tmux session, `aria-modal`, the page behind `inert`, focus back on Cancel run | — |
| `LiteRunObserved`, `MLiteRunObserved` | `RunObserved` | a run started from a terminal, monitor only: "From a terminal" chip, no Cancel, "head on <node>, not checked", no tmux card, the engine log only with the reason; no stage detected, so the flat processes list | Cancel, head output and errors, parameters (not known) |
| `LiteLegend`, `LiteStates`, `LiteStatesRun` | `Legend` | the six 0.0.1 run states, task states (Pending includes Submitted), the stage and process state words with their `run_stages.state`, where a stage comes from, live data over SSE ("live, updated N s ago", "Reconnecting…"); empty, first use, loading, expired link, unreachable, no schema, launch error; run detail loading, not found, head not started yet, launch directory or value refused, no tasks, no match, log not readable or not created yet | gates, review, pause, stage gauge |
| `LiteSidebar`, `LiteTopbar`, `MLiteTopbar`, `MLiteTabbar` | `AppSidebar`, `AppTopbar`, `MobileTopbar`, `MobileTabbar` | Home, Runs, Launch; the cluster and login node; no logo in the top bar (favicon only) | projects, search, notifications, settings, profile, admin |

Run IDs, paths, the login node `login1` and the account `amartin` are fixture data; task counts and failures come from the nf-core megatests named on each board.
