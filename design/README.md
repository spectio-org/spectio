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

The page **0.0.1 lite** of `ui-canvas/canvas.json` holds the screens of the 0.0.1 walking skeleton ([`mvp-0.0.1.md`](../docs/specs/mvp-0.0.1.md), [dev-env §15.1](../docs/specs/dev-environment-and-testing.md#151-capabilities-by-version)). They are cut down from the full boards of 2026-10-26, which stay unchanged as the reference for later versions. They keep the look: the tokens, the run-state colours with an icon and a word, the logo and the shell. Desktop boards render at 1440 × 1180, phone boards at 390 × 844.

| Board | Derived from | Keeps | Drops |
|---|---|---|---|
| `LiteHome`, `MLiteHome` | `Overview`, `MOverview` | the fourth 0.0.1 screen (Home kept, Thomas, 2026-10-28): counts by state from `runs:summary` with no time window, active runs with their task counts, a terminal run marked; on the desktop also recent runs, the pipeline directories of the recent runs and where runs go | project switcher, gates waiting, review queue, depictio, charts, "last 24 h" |
| `LiteRuns`, `MLiteRuns` | `RunsTable`, `MRuns` | columns Run, State, Workflow, Tasks, Started, Duration; name filter and state filters (`state=`, `q=`); a neutral "From a terminal" chip; Load more; live, updated N s ago | stage gauge, Rows mode, compare, projects, users, environments |
| `LiteLaunch`, `LiteLaunchSnakemake`, `MLiteLaunch` | `Launch`, `LaunchSnakemake` | pipeline directory and Load, detected engine, profile, optional run name, schema sections, params preview, Launch disabled with its reason; on the phone a sticky Launch bar | samplesheet and file checks, stepper, environment and gate pickers, relaunch, parameter history |
| `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunTasks`, `LiteRunLogs`, `MLiteRunDetail`, `MLiteRunTasks`, `MLiteRunLogs` | `RunDetail`, `MRunDetail` | header with "stage n of m", state, short ID, facts (Head session, Head alive or exited, Login node, Exit code; no PID), task counts, stages in order with a state word and icon, "n of m tasks" (neutral indigo bar when done, running blue when active) and a Declared or Detected badge, each opening to its processes or rules in first-seen order, plus "Not in a stage" (nf-core/rnaseq subworkflows; a MosaiCatcher-like Snakemake run with one stage per rule file; both [to be validated] by the stage-detection spike), tasks table, logs, how to attach to the head | stage gauge, DAG, timeline, resource charts, gates, review cells, outputs, lineage, relaunch |
| `LiteRunFailed` | `RunFailed` | failure class and the engine's message, failed jobs with their logs, a pipeline with no stage: the flat rules list in first-seen order with a state word and the line "No stages for this pipeline", head errors | `sacct` evidence, suggested fixes, resume and relaunch |
| `LiteCancelDialog`, `MLiteCancelSheet` | — | the P1 Task 20 confirm text verbatim, what Cancel does to the tmux session, `aria-modal`, the page behind `inert`, focus back on Cancel run | — |
| `LiteRunObserved`, `MLiteRunObserved` | `RunObserved` | a run started from a terminal, monitor only: "From a terminal" chip, no Cancel, "head on <node>, not checked", no tmux card, the engine log only with the reason; no stage detected, so the flat processes list | Cancel, head output and errors, parameters (not known) |
| `LiteLegend`, `LiteStates`, `LiteStatesRun` | `Legend` | the six 0.0.1 run states, task states, live data over SSE ("live, updated N s ago", "Reconnecting…"); empty, first use, loading, expired link, unreachable, no schema, launch error; run detail loading, not found, head not started yet, launch directory or value refused, no tasks, no match, log not readable or not created yet | gates, review, pause, stage gauge |
| `LiteSidebar`, `LiteTopbar`, `MLiteTopbar`, `MLiteTabbar` | `AppSidebar`, `AppTopbar`, `MobileTopbar`, `MobileTabbar` | Home, Runs, Launch; the cluster and login node | projects, search, notifications, settings, profile, admin |

Run IDs, paths, the login node `login1` and the account `amartin` are fixture data; task counts and failures come from the nf-core megatests named on each board.
