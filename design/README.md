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
| `LiteHome`, `MLiteHome` | `Overview`, `MOverview` | counts by state, active runs; on the desktop also recent runs, the pipelines launched before and where runs go | project switcher, gates waiting, review queue, depictio, charts |
| `LiteRuns`, `MLiteRuns` | `RunsTable`, `MRuns` | columns Run, State, Workflow, Tasks, Started, Duration; filter; state filters; Load more | stage gauge, Rows mode, compare, projects, users, environments |
| `LiteLaunch`, `LiteLaunchSnakemake`, `MLiteLaunch` | `Launch`, `LaunchSnakemake` | pipeline directory and Load, detected engine, profile, optional run name, schema sections, params preview, Launch disabled with its reason | samplesheet and file checks, stepper, environment and gate pickers, relaunch, parameter history |
| `LiteRunDetail`, `LiteRunTasks`, `LiteRunLogs`, `MLiteRunDetail` | `RunDetail`, `MRunDetail` | header, state, short ID, facts with the head's tmux session, task counts, stages with their status, processes, tasks table, logs, how to attach to the head | stage gauge, DAG, timeline, resource charts, gates, review cells, outputs, lineage, relaunch |
| `LiteRunFailed` | `RunFailed` | failure class and the engine's message, failed jobs with their logs, jobs by rule, head errors | `sacct` evidence, suggested fixes, resume and relaunch |
| `LiteCancelDialog`, `MLiteCancelSheet` | — | the P1 confirm text, what Cancel does to the tmux session, `aria-modal` with focus back on Cancel run | — |
| `LiteLegend`, `LiteStates` | `Legend` | the six 0.0.1 run states, task states, live data; empty, loading, expired link, unreachable, no schema, launch error | gates, review, pause, stage gauge |
| `LiteSidebar`, `LiteTopbar`, `MLiteTopbar`, `MLiteTabbar` | `AppSidebar`, `AppTopbar`, `MobileTopbar`, `MobileTabbar` | Home, Runs, Launch; the cluster and login node | projects, search, notifications, settings, profile, admin |

Run IDs, paths, the login node `login1` and the account `amartin` are fixture data; task counts and failures come from the nf-core megatests named on each board.
