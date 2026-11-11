# MetroFlow and BioFlow-Insight against Spectio's workflow graph: feature gaps (2026-11-11)

**Question.** For [#160](https://github.com/spectio-org/spectio/issues/160), which features of MetroFlow (the metro-map viewer) and BioFlow-Insight (its producer) should Spectio's workflow graph copy, which should it do better, and which should it skip? This note gives the product owner a list to choose from. It changes no spec.

**Sources read (code, not only the READMEs).**
- **MetroFlow front end.** A clone of `gitlab.pasteur.fr/sharefair/metroflow` at commit `23042464` (2026-11-01), read as data and never run. It holds `metro_map.js` (1,757 lines), `code_tooltip.js`, `toolbar.js`, `aesthetics.js`, `collision.js`, `actions.js`, `color_utils.js`, `data_utils.js`, `metro_map_utilities.js` and `offcanvas.js`. Paths below are relative to the repository root.
- **BioFlow-Insight.** The copy vendored at `spikes/metroflow/upstream/bioflow-insight/` (upstream commit `69e0706f`, [spike note](spike-metroflow-2026-11-10.md)). Paths below are relative to that folder.
- **Spectio.** `web/src/runs/graph/` and `packages/spectio-server/src/spectio_server/graph/` plus `api/graph.py`, as in the working tree of 2026-11-11, which includes uncommitted work: fold and unfold by double-click, the Jobs view, the edge sheet, step marks, the legend, `GET /workflows:source` and the right-click code card. Also [ui-spec §4.14](../specs/ui-spec.md#414-workflow-graph-002-flag-graph_view) and [api §5.10](../specs/api-and-data-model.md#510-workflow-graph-002-flag-graph_view).

**Correction to the spike note.** The spike found that the MetroFlow renderer was not public (spike §1). The clone used here has an MIT `LICENSE`, "Copyright (c) 2026 George Marchment, Université Paris-Saclay" (`LICENSE:1-3`), and a README that explains how to embed it (`README.md`, "Embed metroflow in another page"). Whether `gitlab.pasteur.fr/sharefair/metroflow` can be cloned without credentials is **[to be validated]**: this clone was made for the review. If it can, the spike's open item on the licence is closed. Spectio's renderer choice does not change, for the reasons in §3.

## 1. Feature table

Status: **done** = Spectio has it; **partial** = some of it; **missing**; **n/a** = it does not fit Spectio's model.

### 1.1 MetroFlow (front end)

| # | Feature | Where | What it does | Spectio | Notes |
|---|---|---|---|---|---|
| M1 | Embeddable API | `metro_map.js:82`; README options table | `renderMetroflow(json, {container, controls, aesthetics, theme})`; host hooks for save, fullscreen and notify (`actions.js:8-37`) | n/a | Spectio's graph is a React component shared by Run detail and Launch (`GraphView.tsx:680`) |
| M2 | Host theme | `metro_map.js:15-22`, `:86-89`; `color_utils.js:131` | Background, text, grid and station colours; borders contrast on a dark background | done | React Flow `colorMode` follows the app's colour scheme (`GraphView.tsx:281`, `:384`) |
| M3 | Stations and metro lines | `metro_map.js:677-708`, `:1077-1119` | Circles on lines with one rounded corner; positions from Graphviz | partial | Spectio draws boxes. `smoothstep` edges in Metro and Compact, bezier curves in Layered (`GraphView.tsx:355`) |
| M4 | Arrowheads | `metro_map.js:1121-1182` | Two arrows on each edge, at its start and at its end | **missing** | No `markerEnd` on Spectio's edges (`GraphView.tsx:348-362`) and none in the export (`export.ts:43`): the direction is implied by the layout only |
| M5 | Edge colour by condition | `color_utils.js:146-160` | Edges with the same `if` share a colour; unconditional edges are green | **missing** | Spectio keeps edge conditions (`document.py:97-102`) and writes them in the sheets (`GraphView.tsx:108`, `GraphPanel.tsx:320-324`), but does not draw them on the map |
| M6 | Nested subworkflow areas | `metro_map.js:948-981` | Rounded rectangles around each subworkflow's nodes, padded by depth, with a title | partial | Spectio has bands per lane in Metro and Compact (`layout.ts:66-124`), but no areas in Layered and no nesting |
| M7 | Fold and unfold a subworkflow | `metro_map.js:983-993`, `:1217-1226`, `:557-610` | Double-click an area to fold it into one pill; double-click the pill to unfold | done | Double-click (`GraphView.tsx:185`), plus a button in the sheet for the keyboard (`GraphPanel.tsx:190-196`), kept in the URL (`fold`) |
| M8 | "Collapse Subworkflows" button | `metro_map.js:101-151`; `toolbar.js:10` | Folds the deepest unfolded level, one click per level | partial | Spectio has fixed levels (Stage, Subworkflow, Process, Jobs: `settings.ts:5`) and folds one group at a time; there is no "one level more" button |
| M9 | Focus on a subworkflow | `metro_map.js:233-271`, `:771-786`, `:995-1006` | Hold F and click: only that subworkflow is drawn; a banner says "Esc to exit" | partial | Trace upstream and downstream dim the rest (`GraphPanel.tsx:208-217`); there is no "show only this group" |
| M10 | Hide a node, undo | `metro_map.js:337-370`, `:1291-1312` | Hold H and click a node to hide it; Ctrl+Z shows it again | missing | |
| M11 | Minimise a node | `metro_map.js:278-291`, `:1314-1331` | Hold M and click: a smaller circle with no label | missing | |
| M12 | Highlight paths | `metro_map.js:154-169`, `:526-554`, `:1099-1117` | A mode where the edges you click stay coloured and the others turn grey | partial | Spectio computes lineage and the critical path instead (`model.ts:422`, `:458`) |
| M13 | Drag nodes, groups and subworkflows | `metro_map.js:1020-1066`, `:1476-1555` | Shift+click selects several nodes; dragging moves them, stopped by other nodes (`collision.js:81`) | missing | Spectio nodes are not draggable (`GraphView.tsx:318`, `:387`) |
| M14 | Overlap removal | `metro_map.js:1457-1471`; `collision.js:9` | Pushes overlapping nodes and labels apart along one axis | n/a | dagre and Spectio's grid layouts do not overlap nodes |
| M15 | Labels with leader lines | `metro_map.js:1373-1407` | A label under each station, joined by a line | n/a | Spectio writes the name inside the box |
| M16 | Grid, snap | `metro_map.js:401-409`, `:825-834`; `metro_map_utilities.js:252-290` | Shows alignment lines; snapping is turned off in code (`SNAP_ENABLED = false`, `:408`) | n/a | React Flow `Background` (`GraphView.tsx:396`) |
| M17 | Layout memory | `metro_map.js:637-658` | Positions, hidden, minimised, folded and selected edges in `localStorage` | done | Spectio keeps level, layout, overlay, query, node and fold in the URL (`settings.ts:39-73`): the view can be shared and survives a reload |
| M18 | Layout file | `actions.js:117-139`; `metro_map.js:1727-1748` | Download, upload and reset a JSON file with the layout and the appearance | missing | |
| M19 | Appearance panel | `aesthetics.js:8-30`, `:107-200`; `color_utils.js:16-53` | Font (8 choices), text size 8-24 px, 5 palettes including Okabe-Ito "Colorblind safe", custom colours, grey or tinted subworkflows, overlap on or off | missing | Spectio's colours are status colours from design tokens |
| M20 | Fit to view, keep zoom | `metro_map.js:1632-1658`, `:668` | Fits on the first draw; later redraws keep the zoom | done | `fitView` and React Flow controls (`GraphView.tsx:385`, `:397`) |
| M21 | Code card (right-click a station) | `metro_map.js:1282-1287`; `code_tooltip.js:130-216`, `:242-253` | Floating card with Code and Condition tabs, file reference, Copy button; Prism highlighting if the page loads it | partial | Spectio has the right-click card (`GraphView.tsx:649-678`) and Code in the sheet (`GraphPanel.tsx:252`), with line numbers (`Code.tsx:42-55`). There is no Copy button and no highlighting. Upstream bug: Nextflow code is tagged `language-python` (`code_tooltip.js:210`, `:250`) |
| M22 | Subworkflow card | `metro_map.js:1211-1216`; `code_tooltip.js:255-340` | Right-click a folded subworkflow: its code, condition, and a tree of nested subworkflows and steps; click to go in, Back to come out | partial | Spectio's sheet lists the steps of a group, each with "Show on the graph" (`GraphPanel.tsx:233-247`). There is no subworkflow code, no file and no nested tree, because the server keeps only the subworkflow's condition (`document.py:103-108`) |
| M23 | Edge condition (right-click an edge) | `metro_map.js:1092-1097` | Shows the edge's `if` in a card | done | The edge sheet adds the condition and the files that flow along the edge (`GraphPanel.tsx:293-350`); it opens with the mouse only (`edgesFocusable={false}`, `GraphView.tsx:390`) |
| M24 | Export | `toolbar.js:140-208`; `actions.js:60-115` | SVG, PNG, PNG copied to the clipboard | partial | SVG and PNG (`export.ts:24-85`). No clipboard copy. The export has no arrows, no conditions and a fixed light palette (`export.ts:7-18`) |
| M25 | Fullscreen | `actions.js:39-41`; `toolbar.js:8` | Fullscreen on the map's root element | missing | |
| M26 | Keyboard and screen reader | `metro_map.js:48`, `:278-396` | One `aria-label` on the SVG; actions are a held key plus a mouse click; stations have no tab stop or role (searched for `tabindex`, `role=`, `aria`) | done, better | Every node is a native `<button>` with its state in its name, plus a List view (ui-spec §4.14) |

Not features: `findAllPaths` (`data_utils.js:32`) and the start and end node sets (`metro_map.js:791-792`) are computed and never used.

### 1.2 BioFlow-Insight (producer)

| # | Output or analysis | Where | What it does | Spectio | Notes |
|---|---|---|---|---|---|
| B1 | CLI | `bioflow_insight_cli/main.py:12-57` | `MAIN_WORKFLOW_PATH`, `--output-dir`, `--no-render-graphs`, `--analysis bioflow\|metroflow` (help text "todo", `:34`), `--name`, `--is_workflow`, `--display-info` | partial | The server runs `--analysis metroflow` only, as a subprocess with a timeout (`graph/bioflow.py:45-96`) |
| B2 | Two parsers | `main.py:117-148`; `src/workflow.py:364-406` | The Nextflow language server first, then BioFlow's own parser; a generic error hides the cause (`main.py:132`) | done | Spectio falls back to `stages-only` when the tool fails (`static.py:117-163`) |
| B3 | Process dependency graph | `src/graph.py:584-593`; `main.py:108-109` | Processes and the links between them; `process_dependency_graph.json`, `.dot`, `.png` | done | Through `metro_map.json`, for Launch only. Run graphs never use it (api §5.10). The spike's "fallback for Nextflow runs" was not built (`api/graph.py:189-190`) |
| B4 | Metro map JSON | `src/workflow.py:655-806` | Nodes with Graphviz positions, code, file and condition; edges with conditions; subworkflows with label, code, condition and file | partial | Mapped by `document.from_metro` (`document.py:67-115`). Kept: names, positions (Upstream layout), code, file, conditions, `params`. **Dropped: the subworkflows' `code`, `label` and `file_ref`** |
| B5 | Condition, dominator and parallel maps | `main.py:82-95`; `src/workflow.py:772-790`; `src/abstraction.py:363`, `:778`, `:810` | Three more maps whose groups are computed: steps under the same condition, a dominator tree, series-parallel parts | missing | The CLI already writes them (`metro_map_condition.json` and the others); Spectio reads only `metro_map.json` (`bioflow.py:84`) |
| B6 | User-defined and relevant views | `src/abstraction.py:575`, `:844`; `src/graph.py:698-740`; `src/workflow.py:975` | A user view built from a list of "relevant" processes | missing | Python API only, not in the CLI |
| B7 | Specification graph | `src/graph.py:338-371`; `main.py:104-105` | The full graph with operators and channels, also without labels or without orphan operations | missing | `bioflow` analysis only |
| B8 | Dependency and level graphs | `src/graph.py:595-695`, `:755-786` | Processes and operators; one graph per nesting level | missing | Python API only |
| B9 | Graph metadata | `src/graph.py:50-110`; `src/workflow.py:439-449` | Counts of nodes, edges and subworkflows, degrees, density, conditions, biconnectivity | missing | |
| B10 | Cycles | `src/graph.py:902-924` | The edges that close cycles | done | Spectio drops back edges by depth-first search (`model.ts:347`) and says so (`GraphView.tsx:637-639`) |
| B11 | Influential conditions | `src/workflow.py:869-915` | The steps each condition controls | partial | Conditions per node, per edge and per group; no "what this condition turns off" view |
| B12 | RO-Crate, provenance RO-Crate, DB file | `src/workflow.py:809-866`; `src/ro_crate.py:9-399`; `src/DBfile.py:11` | Workflow RO-Crate (validated against `workflow-ro-crate-1.0`, per the comment at `workflow.py:806-808`); it calls the GitHub API with `curl` for repository metadata (`ro_crate.py:55-62`) | n/a | Not part of the graph. RO-Crate reading is owned by `cli-and-shared-libraries.md` §2 |
| B13 | Git history of each element | `src/history.py:23-323`; `src/workflow.py:166-195` | Who created each process and when, from the commits | missing | |
| B14 | Repository facts | `src/workflow.py:196-310` | Docker, Conda and Singularity profiles, nf-core layout, pipe operator, named outputs, files, lines of code, DSL | missing | Partly covered by `/workflows:inspect` |
| B15 | Graph formats | `src/outils_graph.py:240-338` | DOT and PNG through Graphviz; Mermaid only when `mermaid=True` (`:321`), although the CLI help says Mermaid is always written (`main.py:26-27`) | partial | Spectio exports SVG and PNG |
| B16 | Tool extraction | `src/process.py:497-499` | Turned off: returns `[]` | n/a | |
| B17 | Analysis at a commit | `src/workflow.py:49-58` | `commit_2_set` runs `git checkout -f <commit>` in the pipeline directory | n/a | Overwrites the working tree. Spectio must never pass it (not exposed by the CLI) |
| B18 | Snakemake | (none: `grep -ri snakemake` finds nothing, spike §4) | | n/a | Spectio uses the engine's rule graph for runs (`api/graph.py:138-151`); Launch has no edges (`static.py:47-84`) |

## 2. Reproduce: missing features worth copying

| # | Candidate | Value | Effort | Dependencies |
|---|---|---|---|---|
| R1 | **Arrowheads** on map edges and in the export (M4) | High: in Metro, Compact and Upstream the direction cannot be read; an export without arrows is ambiguous | S | React Flow `markerEnd` **[to be validated]** on 12.12.0; `export.ts` draws its own arrow |
| R2 | **Conditional edges drawn**: dashed, with "if" at their middle and an entry in the legend (M5) | High on Launch, where most edges of an nf-core pipeline carry a condition | S | `ViewEdge.conditions` exists (`model.ts:47`). Not colour alone (ui-spec §4.11) |
| R3 | **Subworkflow areas** in Layered: nested outlines with titles (M6) | Medium-high: shows the structure without folding | M | Group boxes from the children's boxes, or dagre compound nodes (`setParent`, **[to be validated]** in `@dagrejs/dagre` 3.1.2); the export draws them too |
| R4 | **Show only this group**, with a banner and Escape to leave, in the URL as `focus=` (M9) | Medium: large nf-core graphs (rnaseq: 67 processes, ui-spec §5.1.1) | S | `collapse()` filter; button in the node sheet |
| R5 | **Subworkflow card**: code, file, nested subworkflows with Back (M22) | Medium on Launch | M | Keep `code`, `label` and `file_ref` in `from_metro` (`document.py:103-108`) and add them to the document's `groups[]` (api §5.10); for runs, `/workflows:source` finds `workflow X {` |
| R6 | **Copy** buttons: code, and PNG to the clipboard (M21, M24) | Medium, low cost | S | Clipboard API; a written fallback when it is refused |
| R7 | **Fullscreen** (M25) | Medium on laptops | S | Fullscreen API; keep focus and Escape behaviour |
| R8 | **Fold one level more / less** buttons (M8) | Low-medium: the levels do most of it | S | `fold` list in the URL |
| R9 | **Hide steps**, with undo, e.g. version-dump processes (M10) | Medium on nf-core pipelines | M | `hide=` in the URL; the List view and the export follow it; hidden steps are counted in a notice so state is never lost silently |
| R10 | **Grouping by condition** on Launch, from `metro_map_condition.json` (B5) | Medium: "what does `--skip_alignment` remove?" | M | Read a second file from the same run of the tool (`bioflow.py:84`); a "Condition" choice in the level picker; no format version, it may change (spike §2) |

## 3. Improve: where Spectio can do better than MetroFlow

| # | Candidate | Value | Effort |
|---|---|---|---|
| I1 | **Live and history**: already ahead (state colours, Heatmap, Critical path, Diff, Replay, Jobs view; ui-spec §4.14). Next: **stable positions** while the run grows, so a checkpoint does not move every node (ui-spec §4.14 "Live" says it is later) | High during a run | M |
| I2 | **Keyboard path to edges**: make each entry of the sheet's Links list a button that opens the edge sheet, since map edges are not focusable (`GraphView.tsx:390`). Also do what the spec says for **Escape in search**, which the code does not handle (`GraphView.tsx:569` handles Enter only) | High (accessibility rule) | S |
| I3 | **Launch map from the last run**: when a run of the same pipeline and revision exists, offer its runtime graph (`nf-dag` or `smk-rulegraph`) on Launch. This gives Snakemake real edges before a run without executing the Snakefile, which the server refuses to do (api §5.10), and gives Nextflow edges without BioFlow-Insight | High for Snakemake | M |
| I4 | **Conditions against the form's values**: on Launch, mark steps "skipped with these parameters" when a condition is a simple `params.x` test, with the code shown | High: the question MetroFlow raises but cannot answer | L. Safe evaluation of a small expression subset only, never Groovy; **[to be validated]** on how many nf-core conditions fit |
| I5 | **Static estimate for runs**: when `nf-spectio` sent no DAG or a truncated one, use BioFlow-Insight's edges with `estimate: true`, as the spike planned. api §5.10 currently says run graphs never use it | Medium. A product decision | M |
| I6 | **Export that matches the screen**: current overlay and legend, arrows, conditions, group outlines, dark or light palette, and the title and producer note (estimate, stages-only) | Medium: figures for reports and papers | S-M |
| I7 | **Edges show their data**: Spectio's edge sheet already lists the upstream files (`GraphPanel.tsx:337-346`); add the Nextflow channel or operator names from BioFlow's specification graph (B7) on Launch | Low-medium | M |

## 4. Skip

| Item | Reason |
|---|---|
| Free drag, multi-select drag, collision, grid and snap (M13, M14, M16) | Spectio lays the graph out from the document; hand-placed positions go stale when the DAG grows. Upstream itself turned snapping off (`metro_map.js:408`). Stable automatic positions (I1) give the value without per-user state |
| Layout file and per-browser layout memory (M17 part, M18) | The URL already keeps the view and can be shared; a JSON layout file is one more format to support |
| Minimise a node (M11) | Hide (R9) and fold cover it |
| Appearance panel: fonts, text size, palettes, custom colours (M19) | Spectio's colours mean states (ui-spec §3); text size follows browser zoom; colour is never the only signal (words, marks, legend) |
| Hold-key shortcuts (M, H, F, Shift + click) (M26) | They cannot be reached by keyboard alone; Spectio puts each action on a button in the sheet or toolbar |
| Manual "Highlight Paths" mode (M12) | Lineage and Critical path do this from data |
| Embedding MetroFlow or reusing its JSON as Spectio's format (M1, B4) | It has no schema version (spike §2), draws circles that are not buttons, and has no live state. Spectio maps the JSON into its own document (api §5.10) |
| Syntax highlighting (M21 part) | A new dependency; pipeline text is shown as text only (api §5.10). Line numbers are enough for now |
| Specification, dependency and level graphs; user and relevant views; graph metadata (B6-B9) | Research outputs for workflow analysis. Users do not need them to monitor or steer a run. R10 takes the one grouping with clear value |
| RO-Crate, DB file, Git history, repository facts (B12-B14) | Not graph features. The RO-Crate calls the GitHub API (B12), which the server's run of the tool avoids (`bioflow.py:10-16`). Provenance has its own owner |
| `commit_2_set`, `--is_workflow` (B17, B1) | The first runs `git checkout -f` in the pipeline directory. The second only re-lays out an existing process-dependency JSON into a metro map (`workflow.py:120-131`), which Spectio does not need |

## Open items

- Whether the MetroFlow repository can be cloned without credentials, and so whether the spike's licence question is closed **[to be validated]**.
- R1 and R3 depend on React Flow and dagre features named above **[to be validated]** at the pinned versions.
- I4: what share of nf-core `if` conditions are simple `params` tests **[to be validated]** on rnaseq and sarek.

## 5. Status, 2026-11-11 (second redesign, PR #251)

- **Done:** R1 (arrows and spotlight), R2 (round fold button), R3 (Metro as dagre compound group areas: `@dagrejs/dagre` 3.1.2 `compound: true`, used in `web/src/runs/graph/layout.ts`), R4 (Focus, `?focus=`), R6 (Copy PNG), R7 (full screen), R8 (Auto-fold, Fold all), R9 (Hide, `?hide=`), I2 (first lines of an output, `outputs:head`), I6 (efficiency gauges).
- **Left:** R5 (subworkflow card), R10 (grouping by condition), I1 (stable positions while live), I3 (Launch map from the last run), I4 (evaluating conditions), I5 (static estimate for runs), I7 (channel names).
