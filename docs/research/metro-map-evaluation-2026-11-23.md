# Metro-map views of workflow DAGs: evaluation for the graph view (2026-11-23)

Checked on 2026-11-23 by the fact-checker. Input: the digest `refract/res-metro/metro.md` (same date). Every kept claim carries a URL or a file:line. Anything not confirmed is marked **[to be validated]**.

**Sources and versions used**

- **nf-metro.** Source at `seqeralabs/nf-metro` commit `0834094` (main, 2026-11-23; `pyproject.toml:7` says 2.1.0, released 2026-09-15). The files were read through `raw.githubusercontent.com/seqeralabs/nf-metro/0834094…/<path>`, and the paths below are relative to that commit. The digest read the **0.6.1 and 0.7.2** docs. Since then there have been 1.0.0, 1.1.0, 2.0.0 and 2.1.0 (`gh api repos/seqeralabs/nf-metro/releases`). Where the old docs and today's code differ, the code wins.
- **Repository move.** `github.com/pinin4fjords/nf-metro` answers 301 to `github.com/seqeralabs/nf-metro`. The `pinin4fjords.github.io/nf-metro/...` docs answer 404, and `seqeralabs.github.io/nf-metro/...` answers 200 (curl, 2026-11-23).
- **Papers.** Both PDFs were downloaded and converted with `pdftotext -layout`. Line numbers below refer to those text files:
  - survey = Wu, Niedermann, Takahashi, Nöllenburg, arXiv:2208.07301v1, https://arxiv.org/pdf/2208.07301.pdf;
  - Brosi-Bast (cited below as `brosi.txt`) = The Cartographic Journal 2024, doi 10.1080/00087041.2024.2325761, https://ad-publications.cs.uni-freiburg.de/Large-Scale_Generation_of_Transit_Maps_from_OpenStreetMap_Data.pdf.
- **Web pages.** WCAG pages and the nf-core pages were read raw with curl, and with WebFetch for yWorks.
- **Spectio.** Read at `4124268d` (`autopilot/integration`, 2026-11-23). PR #251 was read with `gh pr view 251`.

## 1. nf-metro

### 1.1 Input, layout and outputs

- nf-metro draws metro-map SVGs from a subset of Mermaid `graph LR` plus `%%metro` directives, and each analysis route is a coloured "metro line". **Verified.** Sources: `README.md` ("Generate metro-map-style SVG diagrams…") and https://seqeralabs.github.io/nf-metro/latest/.
- A line is declared as `id | Display Name | #hexcolor`, with an **optional 4th field `solid`, `dashed` or `dotted`** and an optional 5th field `inactive` (`docs/guide.mdx:22`). Dashed and dotted lines exist since 0.7.0 (`CHANGELOG.md:580-581`). Stations can also take marker shapes and fills, explained by a `%%metro marker_legend:` key (`docs/guide.mdx:211-225`). An edge carries line IDs (`docs/guide.mdx:27`). The digest's "colour only" reading is **corrected** in §5.
- The engine infers section directions, grid positions and port sides from the topology (`docs/guide.mdx:333`). **Verified.**
- Layout options in 2.1.0 (**corrected**):
  - `--x-spacing` and `--y-spacing` default to **auto** (`docs/cli.md:142-143`). The 60 and 40 defaults held in 0.7.2 (https://seqeralabs.github.io/nf-metro/0.7.2/).
  - Rows fold with **`--fold-threshold`**, default 15 station-columns (`docs/cli.md:147`; `docs/guide.mdx:364`). `--max-layers-per-row` is no longer in the 2.1.0 CLI reference.
- `--format html` makes a self-contained page with no network access. It gives drag to pan, scroll to zoom, a station tooltip on hover and a legend line click that isolates a line. `Esc` or Reset restores the view. **Verified** (`README.md`; `docs/cli.md:229-239`). `--animate` adds balls along the lines (`docs/cli.md:174`). Verified.
- Each SVG embeds a JSON manifest (`<metadata id="diagram-manifest">`) and `data-node-*` attributes (`README.md`). Nodes need `id`, `x`, `y` and `r`; `label` is optional (`docs/manifest.md:253`). The manifest has **no description or alt-text field** (`docs/manifest.md:201,253`). Verified.
- The Python modules are not a semver-stable API (`README.md`, "Python API"). Verified. Python ≥ 3.11 (`pyproject.toml:11`); the 0.7.2 page said 3.10+. Verified.
- Theme: the default is `nfcore`, and **`dark` is a legacy alias for `nfcore`** (`docs/cli.md:119`). The digest's "dark versus nfcore" difference is a rename, not a conflict (**corrected**).

### 1.2 Converting a Nextflow DAG

All verified at `0834094`:
- The DAG comes from `nextflow run … -preview -with-dag dag.mmd`. It is in `flowchart TB` form, which "nf-metro cannot render directly but can convert" (`docs/nextflow.mdx:21-25`).
- Channel, value and operator nodes are dropped (`docs/nextflow.mdx:280-286`).
- Each subworkflow becomes a section, and processes outside any subworkflow go to an extra section (`:118`). The longest path becomes `main` (`:60`). Edges that skip a section become bypass lines, and dead-end processes become spurs (`:119-120`).
- The result is a **process-level** abstraction. A station is "a curated abstraction that usually stands for several Nextflow processes, often a whole subworkflow" (`docs/live.mdx`, §1).

### 1.3 Stated limits

- "For complex pipelines such as those in nf-core, it is unlikely to produce a good diagram, and you need to hand-write or heavily edit the `.mmd` file. This is an active area of development." (`docs/nextflow.mdx:10-13`). "For anything beyond a toy pipeline, the two-step process gives better results." (`:161`). Labels need fixing: `Gatk Haplotypeca`, `Multiqc` (`:198`, `:207`). Verified.
- Compact offsets:
  - by default "each line reserves a fixed vertical slot across the whole map, based on its declaration order" (`docs/guide.mdx:417`);
  - `compact_offsets: true` "suits maps with few lines but many stations" (`:421-423`);
  - when seven lines converge, the layout is split into two rows (`:336`).
  Verified.
- Stations whose ID starts with `_` are hidden; `--debug` shows them (`docs/guide.mdx:240,266`). Verified.
- The rendered-pipelines page lists **nine pipelines**: eight from nf-core (epitopeprediction, hlatyping, riboseq, rnaseq, sarek, seqinspector, variantbenchmarking, variantprioritization) and **`sanger-tol/genomeassembly`**, which is not an nf-core pipeline (https://seqeralabs.github.io/nf-metro/latest/pipelines/, curl 2026-11-23). This is **corrected**: the digest called all nine nf-core.
- No numeric limit on stations or lines, and no layout-time benchmark, was found in the docs **[to be validated]**. The repository does have a stress-render skill (`.claude/skills/nf-metro-stress-render/`), but no published figures. The digest's "2 to 7 sections, 2 to 6 lines" tally came from the fetch tool; **[to be validated]**.

### 1.4 Live overlay

All verified in `docs/live.mdx` unless noted:
- Stations go "from pending to queued to running to done, or to failed, each with a per-sample count" (`:14`).
- Stock `-with-weblog` drives it: "This needs no Seqera Platform and no plugin" (`:13-15`).
- "nf-metro computes the layout once and draws the overlay on top. The map never re-flows as state changes." (`:27-28`).
- "No denominator. Nextflow's task count is dynamic", so the count reads "done / submitted so far" (`:429-430`).
- `failed` is sticky for the rest of the run (`docs/manifest.md:367`).
- Stations with no `process:` mapping never light up. A process that matches two stations duplicates its progress (`:64-69`, `:414`).
- "The server tracks one run at a time" is true of **`nf-metro serve`** only (`:426`). **`serve-multi`** is a multi-run dashboard with one `/r/<id>/` page per run (`:248-249`; `README.md` "Live progress"). **Corrected.**
- Overlay styles are ring (the default), pulse, dot and led (`:208`, `:221-227`). "Animations respect `prefers-reduced-motion`" (`:232`). The code confirms the reduced-motion rule (`src/nf_metro/live/server.py:461-465`).
- `/events` is unauthenticated by default and binds to `127.0.0.1`; `--token` is available (`:206`, `:212`, `:423`).
- The optional Nextflow plugin is "not yet published to the Nextflow plugin registry" (`:307-309`).
- No throughput or timing figures are published **[to be validated]**.

## 2. Literature on automatic metro-map layout

All the inputs are transit networks, not workflow DAGs.

- Survey, abstract: an optimal method "is capable of producing results for printing, while it is not suitable for computing instant layouts due to its long running time" (survey.txt:19-20). Verified.
- Survey, conclusion: the problem is "a fundamentally difficult one, so that a certain quality loss needs to be tolerated in order to achieve fast performance" (survey.txt:381-382). Verified.
- Global MIP takes "several minutes for simple network maps to several hours for more complex instances" (survey.txt:150-153). Nöllenburg and Wolff, with labelling, ran "up to 12 hours" on Sydney (survey.txt:196-199). Oke and Siddiqui reach "few minutes" (survey.txt:166-171). Onda et al. laid out Tokyo "within 5 hours" (survey.txt:171-179). Verified.
- Timings by method (**corrected attribution**). The survey cites two different Chivers and Rodgers papers:
  - [8], hybrid force-based: "less than a second" (survey.txt:165-173);
  - [9], hill-climbing extension, labelled layouts: "within 5 to 60 minutes" (survey.txt:161-165).
  - Stott et al. [39], layout plus labelling: "between 2 and 120 minutes" (survey.txt:199-206).
  - Wang and Chi [48] "typically run in less than a second" (survey.txt:156-161).
  - van Dijk and Lutz [45] run in "a few milliseconds", but "several typical constraints of metro maps are not considered" (survey.txt:127, 181).
- The survey's time scale: T1 under a second, T2 a few seconds, T3 a few minutes, T4 several hours or more (survey.txt:123-126). Verified.
- Brosi-Bast:
  - ILPs take "multiple hours even for intermediate networks like the Berlin S-Bahn network" (brosi.txt:662-663);
  - global tiles for every network rendered "in under 2 hours" (:810);
  - laying out the whole dataset at once was impossible, so each component is laid out alone, and memory stayed under 100 GB after sampling every 10 m instead of 5 m (:812-820).
  Verified.
- yWorks blog (2018-07-06): "very CPU intensive"; "the goal was not to create maps in real time"; octilinear lines; a MIP after Nöllenburg 2005, solved with CPLEX or lpsolve; results are a "base for a designer to further fine-tune" (https://www.yworks.com/blog/automatic-metro-map-generation, WebFetch 2026-11-23). Verified.

### 2.2 Reported failure modes

- Density: "some of our maps still show areas of very high density, which makes them very hard to read". Larger grid cells bring more topology errors, and no ILP solution came "for the Europe long-distance network in under 12 hours" (brosi.txt:899-904). Verified.
- The orthoradial subway map had "over 2,500 topology errors" and took circular detours (brosi.txt:916-920). Small artefacts "were enlarged during the schematization" (:921-922). Verified.
- Bundles: the Taiwan high-speed link has "nearly 200 individual line relations" (brosi.txt:896-898). The maximum number of lines per edge is **171** for long-distance rail (Table 2, brosi.txt:834; Figure 21, :884). **Verified.** The digest's [to be validated] on 171 is lifted.
- Labels:
  - a layout "may not host all labels", and fast labelling is "a still open and important research problem" (survey.txt:286, 300);
  - Brosi-Bast's tiles "lack labels so far", though their labeller exists for SVG output (brosi.txt:944-946);
  - yWorks: "Labeling of the metro stations was a challenge, but easy with yFiles" (WebFetch). The digest dropped the second half of that sentence (**corrected**, minor).
- Usability: "a thorough evaluation of the aesthetic quality and usability of our maps is missing", and automatic evaluation is "still an open research problem" (brosi.txt:869-873). Combined networks may be "too complex to be layout together"; hierarchical approaches are suggested (brosi.txt:951-953). Verified.
- No fetched source evaluates metro-map layout on workflow DAGs, or on graphs with thousands of nodes **[to be validated]**.

### 2.3 Metro maps as a metaphor

- "Several case studies are at an early stage". Nesbitt's preliminary studies showed metro metaphors "can provide a better mental model of the target data as a first impression" (survey.txt:251-256). Metro maps have also shown project plans and software tasks (Stott et al., Aguiregoitia et al.) and document networks (survey.txt:275-298). Verified.

## 3. Accessibility and small screens

- WCAG 2.2 SC 1.4.1: "Color is not used as the only visual means of conveying information…". The Understanding page continues: "the color may not be seen by users with color deficiencies". It lists F13 and G111 ("Using color and pattern") and G14 (https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html, curl 2026-11-23). Verified.
- WCAG 2.2 SC 1.1.1 is verified (https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html). For charts, the long description "identifies the type of chart, provides a high-level summary of the data, trends and implications". The exact data-table wording is "Where possible and practical, the actual data is provided in a table." (**Corrected:** the digest's quotation was a paraphrase.)
- WCAG 2.2 SC 2.2.2 covers motion that "(1) starts automatically, (2) lasts more than five seconds, and (3) is presented in parallel with other content". Such motion needs a way to pause, stop or hide it (https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html). This source was added for §6.
- nf-core guideline:
  - "Most nf-core pipelines use a metro-map diagram, where each analysis route is a coloured line…";
  - "Use an SVG if you can: it scales to any size…";
  - colours are CSS `light-dark()` pairs;
  - `manifest.diagram` is **new in Nextflow 26.10.0**;
  - the page says nothing about accessibility.
  Source: https://nf-co.re/docs/guidelines/graphic_design/workflow_diagrams. Verified.
- nf-core gallery: all **33 `<img>` maps have an empty `alt`**, and the inline SVG maps have no `role`, `aria-label` or `<title>` (https://nf-co.re/metro_map_gallery, curl 2026-11-23). There is no per-map description. Verified.
- What nf-metro's code offers for accessibility (this settles the digest's [to be validated] items):
  - **Keyboard:** the interactive HTML listens only for `Escape` (`src/nf_metro/render/driver.js:307-308`). Legend chips are `<div>` elements with click handlers and no `tabindex` (`driver.js:243-250`). So isolating a line, panning and zooming are **not keyboard operable**.
  - **Hover-only tooltips:** tooltips come only on `mouseover` and `mousemove` (`driver.js:289-300`).
  - **Screen readers:** `render/svg.py` emits no `<title>`, `<desc>`, `role` or `aria-*`. Only the standalone page has an HTML `<title>` (`render/standalone.html:6`).
- **Touch is supported:** one finger pans and two fingers pinch-zoom on the standalone page, while inline embeds leave touch to the host page (`driver.js:86-120`). **Corrected:** the digest had this as unknown. A tap does not open a tooltip, since tooltips are mouse-only (`driver.js:289-300`).
- **Live state and colour:**
  - pending, queued and running differ by opacity, dash pattern and animation as well as by colour (`live/server.py:410-447`);
  - in the default `ring` style, **done and failed are both a solid ring and differ only in colour** (light theme `#2f9e44` and `#e03131`; `live/server.py:99-106, 413-424`);
  - with reduced motion on, running also loses its animation (`:461-465`).
  **Corrected:** the digest said this was unknown.
- No source gives a minimum legible label size on phones, and none checks whether the nf-metro palettes can be told apart with colour-vision deficiency **[to be validated]**.

## 4. Spectio's graph view (#251), as built

Spectio's code was read at `4124268d` on 2026-11-23.

- **What #251 is.** #251 is the merged **PR** "feat: interactive workflow graph behind graph_view (#160)" (`gh pr view 251`). The issue is #160. Decisions are in `docs/decisions/log.md:1388-1418`, and the screens are owned by `docs/specs/ui-spec.md:763-836` (§4.14).
- **Flag.** The flag `graph_view` is off by default (`log.md:1415`). The web app shows the screens only when `GET /features` lists it (`web/src/runs/graph/features.ts:30`; `ui-spec.md:765`).
- **Renderer.** React Flow `@xyflow/react` 12.12.0 with `@dagrejs/dagre` 3.1.2 (`web/package.json:11,26`; `log.md:1390`). dagre follows Gansner et al. (network simplex ranking), Brandes-Köpf coordinates and Sander's compound graphs, and favours speed over optimality: "Dagre must be able to draw medium sized graphs quickly" (https://github.com/dagrejs/dagre/wiki, WebFetch 2026-11-23).
- **Levels.** Stage, Subworkflow, Process (the default) and Jobs. Jobs are loaded with at most **200 per step and 2000 in all**; a step over the cap stays one node (`GraphPanel.tsx:22-24, 36-50`; `ui-spec.md:775`).
- **Layouts.** All are pure functions of the view (`web/src/runs/graph/layout.ts:169-180`):
  - **Layered top-down** is the default (`settings.ts:67`).
  - **"Metro" is not a transit-map layout.** It is a dagre **compound layered graph**, left to right, with tighter spacing (`nodesep 22`, `ranksep 64`). Each subworkflow or stage is drawn as an area (`layout.ts:69-102, 174`), and edges are `smoothstep` (`GraphView.tsx:747`). It has no lines as routes, no line colours and no octilinear constraint, so none of the transit-map literature in §2 applies to it directly. Thomas found the earlier Metro view "unclear", and it was redrawn as dagre group areas (`log.md:1396-1397`).
  - Compact uses near-square grids packed in shelves (`layout.ts:104-139`).
  - With no edges at all, every layout falls back to that grid (`layout.ts:171-173`).
- **Fold.** Auto-fold folds the biggest groups until there are at most `min(24, ⌈n/2⌉)` boxes (`GraphView.tsx:1195, 1242`; `ui-spec.md:777`).
- **Live.** The layout is computed again from each new document, so nodes can move. Keeping positions stable is listed as later (`ui-spec.md:829`; `GraphView.tsx:572`; gap item I1 is still open, `docs/research/metroflow-gap-2026-11-11.md:91,124`). This is the opposite of nf-metro's choice to lay out once (§1.4).
- **Accessibility as built:**
  - each node is a native `<button>` whose `aria-label` gives the name, kind, state, "N of M jobs done" and the marks (`GraphView.tsx:306-312, 559-565`);
  - the **state word is printed** on the node's meta line (`GraphView.tsx:717`), so state is not shown by colour alone;
  - links that run under a condition are dashed **and** labelled `if` (`graph.css:646-648`; `ui-spec.md:781`);
  - the critical path is drawn with a wider stroke and a ring as well as colour (`graph.css:92-94, 141-144`);
  - edges cannot take keyboard focus (`GraphView.tsx:748, 845-846`), and the link card is hover-only; the PR #251 "Known gaps" says so;
  - a **List** view gives the table equivalent (`GraphView.tsx:877-905`) and is the **default on phones** (`settings.ts:69`);
  - above 300 nodes, React Flow draws only what is on screen (`GraphView.tsx:855`), so the buttons of off-screen nodes leave the DOM and cannot be reached with Tab.
- **Spec drift.** `ui-spec.md:835` says the level and layout pickers are `<button role="tab">` groups and the overlays are `<button role="switch">`. The code uses native `<select>` elements (`NativeSelect` "Show", "Layout" and "Colour by", `GraphView.tsx:1113-1123`). The code is accessible, but the spec text is out of date. See FC-M11.
- **Motion.** Edges into a running step are `animated` (`GraphView.tsx:751`). React Flow 12.12.0 animates them with `dashdraw 0.5s linear infinite` (https://unpkg.com/@xyflow/react@12.12.0/dist/style.css, lines 162-164). Neither that stylesheet nor `web/src` has a `prefers-reduced-motion` rule (grep, 2026-11-23). The ui-spec asks for reduced motion only for the logo (`ui-spec.md:37`). See FC-M12.
- **Real sizes.** At process level, real pipelines are small:
  - nf-core/rnaseq 3.27.0 has 67 processes, nf-core/sarek 3.11.0 has 48 and nf-core/methylseq 13; mosaicatcher has 101 rules (`ui-spec.md:904`);
  - the end-to-end check returned 67 nodes and 30 groups (PR #251, Evidence).
  "Hundreds to thousands" happens only at the Jobs level.

## 5. Claim table

Verdicts: V = verified, C = corrected (wrong or partly true), U = unverifiable.

| # | Claim (digest) | Location | Verdict | Source | Correction |
|---|---|---|---|---|---|
| 1 | pinin4fjords.github.io docs 404; seqeralabs mirrors 200 | §0 | V | curl 2026-11-23 | repo now `seqeralabs/nf-metro` (301) |
| 2 | default theme differs (dark vs nfcore) | §0 | C | `docs/cli.md:119` | `dark` is an alias of `nfcore` |
| 3 | README 3.11+, 0.7.2 page 3.10+ | §0 | V | `pyproject.toml:11`; 0.7.2 page | none |
| 4 | Mermaid subset + `%%metro`, coloured lines | §1.1 | V | `README.md`; `docs/guide.mdx` | none |
| 5 | line = id, name, hex colour | §1.1 | C | `docs/guide.mdx:22`; `CHANGELOG.md:580` | + style solid/dashed/dotted, inactive |
| 6 | layout inferred from topology; grid pinning | §1.1 | V | `docs/guide.mdx:333` | none |
| 7 | `--x-spacing` 60, `--y-spacing` 40, `--max-layers-per-row` | §1.1, §3.3 | C | `docs/cli.md:142-147` | auto spacing; `--fold-threshold` 15 |
| 8 | HTML: pan, zoom, hover, legend isolate | §1.1 | V | `docs/cli.md:229-239` | none |
| 9 | `--animate` balls | §1.1 | V | `docs/cli.md:174` | none |
| 10 | embedded manifest, `data-node-*` | §1.1 | V | `README.md`; `docs/manifest.md:253` | none |
| 11 | nf-core: metro maps, `manifest.diagram`, formats, SVG scales | §1.1 | V | nf-core guideline (curl) | `manifest.diagram` needs NF 26.10.0 |
| 12 | `-preview -with-dag`, convert / `--from-nextflow` | §1.2 | V | `docs/nextflow.mdx:21-25` | none |
| 13 | `flowchart TB` cannot render, can convert | §1.2 | V | `docs/nextflow.mdx:25` | none |
| 14 | converter drops channels/operators, sections, main/bypass/spur, labels | §1.2 | V | `docs/nextflow.mdx:60,118-120,280-286` | none |
| 15 | process-level abstraction | §1.2 | V | `docs/live.mdx` §1 | none |
| 16 | complex pipelines "unlikely to produce a good diagram" | §1.3 | V | `docs/nextflow.mdx:10-13,161` | none |
| 17 | bad auto labels (Gatk Haplotypeca, Multiqc) | §1.3 | V | `docs/nextflow.mdx:198,207` | none |
| 18 | no numeric limit / no benchmark | §1.3 | U | docs absence | spike or upstream stress data |
| 19 | fixed vertical slot; compact_offsets; 7 lines → 2 rows | §1.3 | V | `docs/guide.mdx:336,417-423` | none |
| 20 | nine nf-core pipelines incl. genomeassembly | §1.3 | C | pipelines page (curl) | genomeassembly is sanger-tol |
| 21 | 2–7 sections, 2–6 lines tally | §1.3 | U | tool count | count by hand |
| 22 | hidden `_` stations, `--debug` | §1.3 | V | `docs/guide.mdx:240,266` | none |
| 23 | Python API not semver-stable | §1.3 | V | `README.md` | none |
| 24 | pending→queued→running→done/failed, per-sample count | §1.4 | V | `docs/live.mdx:14` | none |
| 25 | layout once, never re-flows | §1.4 | V | `docs/live.mdx:27-28` | none |
| 26 | "done / submitted so far", dynamic count | §1.4 | V | `docs/live.mdx:429-430` | none |
| 27 | server tracks one run at a time | §1.4, §4.12 | C | `docs/live.mdx:248-249,426` | only `serve`; `serve-multi` is multi-run |
| 28 | unmapped stations dark; duplicate counts | §1.4 | V | `docs/live.mdx:64-69,414` | none |
| 29 | ring/pulse/dot/led; reduced motion | §1.4 | V | `docs/live.mdx:208-232`; `server.py:461` | none |
| 30 | plugin not on registry; `/events` unauthenticated, 127.0.0.1 | §1.4 | V | `docs/live.mdx:307-309,423` | live needs no plugin (`:13-15`) |
| 31 | no timing/throughput figures | §1.4 | U | docs absence | spike |
| 32 | survey abstract (printing vs instant) | §2.1 | V | survey.txt:19-20 | none |
| 33 | "fundamentally difficult… quality loss" | §2.1 | V | survey.txt:381-382 | none |
| 34 | MIP minutes to hours; Sydney 12 h | §2.1 | V | survey.txt:150-153,196-199 | none |
| 35 | Oke and Siddiqui minutes; Onda Tokyo 5 h | §2.1 | V | survey.txt:166-179 | none |
| 36 | Stott minutes to hours; Chivers and Rodgers 5–60 min; 2–120 min | §2.1 | C | survey.txt:161-173,199-206 | two C&R papers: [8] <1 s, [9] 5–60 min; 2–120 min is Stott [39] |
| 37 | force-based seconds; Wang and Chi <1 s; van Dijk ms | §2.1 | V | survey.txt:127-161,181 | none |
| 38 | T1–T4 scale | §2.1 | V | survey.txt:123-126 | none |
| 39 | Bast ILP hours (Berlin S-Bahn) | §2.1 | V | brosi.txt:662-663 | none |
| 40 | tiles < 2 h; per component; <100 GB at 10 m | §2.1 | V | brosi.txt:810-820 | none |
| 41 | yWorks CPU-intensive, not real time, octilinear, MIP, designer | §2.1 | V | yWorks (WebFetch) | none |
| 42 | density "very hard to read"; Europe ILP >12 h | §2.2 | V | brosi.txt:899-904 | none |
| 43 | >2,500 orthoradial topology errors; detours | §2.2 | V | brosi.txt:916-920 | none |
| 44 | artefacts enlarged | §2.2 | V | brosi.txt:921-922 | none |
| 45 | ~200 line relations; 171 lines/edge [tbv] | §2.2 | V | brosi.txt:834,884,896-898 | [tbv] lifted |
| 46 | labelling weak (survey, yWorks, Brosi) | §2.2 | C | survey.txt:286,300; brosi.txt:944-946; yWorks | yWorks: "a challenge, but easy with yFiles"; Brosi has an SVG labeller |
| 47 | no usability evaluation; auto evaluation open | §2.2 | V | brosi.txt:869-873 | none |
| 48 | "too complex to be layout together"; hierarchical | §2.2 | V | brosi.txt:951-953 | none |
| 49 | "do not need to be geographically precise" | §2.2 | V | yWorks (WebFetch) | none |
| 50 | no source on workflow DAGs / thousands of nodes | §2.2 | U | absence | spike (§6.5) |
| 51 | Nesbitt mental model; early stage; project/software maps | §2.3 | V | survey.txt:251-298 | none |
| 52 | WCAG 1.4.1 quotes | §3.1 | V | WCAG 1.4.1 page | none |
| 53 | F13, G111, G14 | §3.1 | V | WCAG 1.4.1 page | none |
| 54 | nf-metro lines: no non-colour cue documented | §3.1 | C | `docs/guide.mdx:22,211-225`; `driver.js:243-248` | dash styles, marker shapes, named legend chips |
| 55 | Brosi random colours | §3.1 | V | brosi.txt:875-877 | none |
| 56 | colour is the only separator in shared segments | §3.1 | U | none | user test |
| 57 | WCAG 1.1.1 "underlying data should also appear in a table" | §3.2 | C | WCAG 1.1.1 page | exact: "Where possible and practical, the actual data is provided in a table." |
| 58 | nf-core guideline: no accessibility guidance | §3.2 | V | nf-core guideline (curl) | none |
| 59 | nf-core gallery images have empty alt | §3.2 | V | gallery (curl): 33/33 bare `alt` | inline SVGs: no name either |
| 60 | nf-metro docs: no ARIA, title/desc, keyboard | §3.2 | V | `render/svg.py`; `driver.js:243-250,307` | settled: not keyboard operable |
| 61 | hover-only tooltips | §3.2 | V | `driver.js:289-300` | none |
| 62 | live state without colour: unknown | §3.2 | C | `live/server.py:99-106,410-447` | done vs failed is colour-only in `ring` |
| 63 | touch support: unknown | §3.3 | C | `driver.js:86-120` | pan and pinch on the standalone page |
| 64 | Mapway / ExploreMetro in the survey | §3.3 | V | survey.txt:338-343 | none |
| 65 | yWorks: no small screens or accessibility | §3.3 | V | yWorks (WebFetch) | none |

**Counts:**
- 65 claims: **verified 49**, **corrected 11**, **unverifiable 5**.
- The section 4 risks of the digest re-use these claims and are not counted again. Risk 12 ("one run at a time"; "plugin") inherits corrections 27 and 30.

## Corrections

Findings in the `docs/reviews/README.md` format. They apply to the digest. FC-M11 and FC-M12 apply to Spectio's own spec and code.

### FC-M01 · minor · nf-metro docs read at stale versions
- **Where:** digest §0, §1.
- **Evidence:** the digest cites the 0.6.1 and 0.7.2 docs. The current release is 2.1.0 (2026-09-15; `pyproject.toml:7` at `0834094`), and the repository moved to `seqeralabs/nf-metro`.
- **Problem:** options and limits shifted between versions (claims 2, 5, 7, 27).
- **Proposal:** cite `seqeralabs.github.io/nf-metro/latest/` and a commit of `seqeralabs/nf-metro`.
- **Found by:** fact-checker · **Status:** open

### FC-M02 · minor · Theme "difference" is an alias
- **Where:** digest §0.
- **Evidence:** "`dark` is a legacy alias for `nfcore`" (`docs/cli.md:119`).
- **Problem:** the two theme names were read as two different defaults.
- **Proposal:** say "default theme `nfcore` (formerly `dark`)".
- **Found by:** fact-checker · **Status:** open

### FC-M03 · major · nf-metro lines are not colour-only
- **Where:** digest §1.1, §3.1, §4 risk 8.
- **Evidence:**
  - a line's optional 4th field is `solid`, `dashed` or `dotted` (`docs/guide.mdx:22`; since 0.7.0, `CHANGELOG.md:580-581`);
  - stations take marker shapes and fills with a marker legend (`docs/guide.mdx:211-225`);
  - legend chips show the line name (`render/driver.js:243-248`).
- **Problem:** the accessibility verdict on metro maps rests on a claim that is no longer true.
- **Proposal:** say that dash styles give a second channel for about three lines. Beyond that, colour still carries the line, and the palettes' colour-vision-deficiency check is **[to be validated]**.
- **Found by:** fact-checker · **Status:** open

### FC-M04 · minor · Layout options renamed
- **Where:** digest §1.1, §3.3, §4 risk 7.
- **Evidence:** `--x-spacing` and `--y-spacing` are now "auto" (`docs/cli.md:142-143`), and folding uses `--fold-threshold`, default 15 (`:147`).
- **Problem:** `--max-layers-per-row`, 60 and 40 are 0.7.2 values.
- **Proposal:** use the 2.1.0 names.
- **Found by:** fact-checker · **Status:** open

### FC-M05 · minor · genomeassembly is not nf-core
- **Where:** digest §1.3.
- **Evidence:** the pipelines page shows `sanger-tol/genomeassembly` (curl 2026-11-23).
- **Problem:** the list mislabels one pipeline.
- **Proposal:** "nine pipelines: eight from nf-core plus sanger-tol/genomeassembly".
- **Found by:** fact-checker · **Status:** open

### FC-M06 · major · "One run at a time" is only `nf-metro serve`
- **Where:** digest §1.4, §4 risk 12.
- **Evidence:** "The server tracks one run at a time" (`docs/live.mdx:426`). `serve-multi` is "a long-lived dashboard", with one `/r/<id>/` page per run (`:248-249`). Live mode needs no plugin (`:13-15`).
- **Problem:** this overstates nf-metro's limits as a live view.
- **Proposal:** scope the limit to `serve`, and add `serve-multi`.
- **Found by:** fact-checker · **Status:** open

### FC-M07 · minor · Chivers and Rodgers timings conflated
- **Where:** digest §2.1.
- **Evidence:**
  - [8], hybrid force-based: "less than a second" (survey.txt:165-173);
  - [9], hill climbing: "5 to 60 minutes" (:161-165);
  - Stott et al. [39], layout plus labelling: "2 and 120 minutes" (:199-206).
- **Problem:** one author pair is credited with both a fast and a slow method.
- **Proposal:** cite each paper separately.
- **Found by:** fact-checker · **Status:** open

### FC-M08 · minor · Labelling quotes trimmed
- **Where:** digest §2.2.
- **Evidence:** yWorks: "Labeling of the metro stations was a challenge, but easy with yFiles". Brosi-Bast: "We have implemented a labeller … but so far it only works for the SVG output" (brosi.txt:944-946).
- **Problem:** the trimmed quotes overstate labelling as a blocker.
- **Proposal:** quote both in full.
- **Found by:** fact-checker · **Status:** open

### FC-M09 · minor · WCAG 1.1.1 quotation is a paraphrase
- **Where:** digest §3.2.
- **Evidence:** the page reads "Where possible and practical, the actual data is provided in a table."
- **Problem:** a paraphrase is shown in quotation marks.
- **Proposal:** use the exact sentence.
- **Found by:** fact-checker · **Status:** open

### FC-M10 · major · nf-metro touch, keyboard and live-state facts settled from code
- **Where:** digest §3.2, §3.3, §4 risks 7, 8 and 9.
- **Evidence:**
  - touch pan and pinch on the standalone page (`render/driver.js:86-120`);
  - the only key handled is `Escape` (`:307-308`);
  - legend chips are `<div>` elements with no `tabindex` (`:243-250`);
  - tooltips come on mouseover only (`:289-300`);
  - the SVG has no `<title>`, `<desc>` or ARIA (`render/svg.py`);
  - in the default `ring` overlay, done and failed differ by colour only (`live/server.py:99-106,413-424`).
- **Problem:** three items marked [to be validated] can now be stated.
- **Proposal:**
  - touch: supported;
  - keyboard and screen reader: not supported;
  - live failed versus done: colour-only in `ring`.
- **Found by:** fact-checker · **Status:** open

### FC-M11 · minor · Spectio ui-spec §4.14 picker roles do not match the code
- **Where:** `docs/specs/ui-spec.md:835` against `web/src/runs/graph/GraphView.tsx:1113-1123`.
- **Evidence:** the spec says "Level and layout pickers are `<button role="tab">` groups, and overlays are `<button role="switch" aria-checked>`". The code renders three `NativeSelect` controls: Show, Layout, Colour by.
- **Problem:** the spec describes controls that were not built. Overlays are mutually exclusive, so `switch` would also be the wrong semantics.
- **Proposal:** make the spec say native `<select>`, or rebuild the pickers as a radio or tab group. Thomas to choose.
- **Found by:** fact-checker · **Status:** open

### FC-M12 · major · Spectio graph animates edges with no reduced-motion fallback
- **Where:** `web/src/runs/graph/GraphView.tsx:751`; ui-spec §4.14 (silent on motion); `ui-spec.md:37` (reduced motion is required for the logo only).
- **Evidence:**
  - every edge into a running step is `animated`, and React Flow 12.12.0 applies `animation: dashdraw 0.5s linear infinite` (unpkg `style.css:162-164`);
  - there is no `prefers-reduced-motion` rule in `web/src` or in that stylesheet (grep 2026-11-23);
  - WCAG 2.2.2 asks for a way to pause motion that starts automatically, lasts more than 5 s and is shown in parallel with other content.
- **Problem:** a long run shows endless motion on every running edge.
- **Proposal:**
  - under `prefers-reduced-motion: reduce`, set `animation: none` on `.react-flow__edge.animated path`;
  - add a pause control, or show "running" with a static dash instead;
  - add the rule to ui-spec §4.14.
- **Found by:** fact-checker · **Status:** open

## Re-evaluating Spectio's metro-map graph view (#251)

**6.0 What "metro" means in Spectio.**
- The `metro` layout is a **left-right dagre compound layered layout** (`layout.ts:69-102`), not a transit map. It draws one box per step, group areas and smoothstep edges. It has no route lines, no line colours, no octilinear constraint and no MIP. Layout speed is therefore dagre's (built for "medium sized graphs quickly", dagre wiki), not the minutes or hours of §2.1.
- The literature's transit-map failure modes (line bundles, labels, octilinear density) do not apply directly. What does carry over is the general finding: dense automatic layouts become "very hard to read", and nobody has tested usability.
- nf-metro, the only true metro-map tool for Nextflow, works at the curated **process** level, needs hand editing beyond toy pipelines (`docs/nextflow.mdx:10-13`), and lays out once so the map never re-flows. Spectio's view is automatic, live, and re-laid out from each document.
- Suggestion **[to be validated with Thomas]**: rename the layout ("Grouped, left-right") or say in its help line that it is not a transit map. Users who know nf-core metro maps will expect coloured route lines.

**6.1 Readability on large DAGs (hundreds to thousands of tasks).**
- At process level the graphs are small: 13 to 101 steps for the pinned real pipelines (`ui-spec.md:904`). Groups and Auto-fold (`min(24, ⌈n/2⌉)` boxes, `GraphView.tsx:1195,1242`) already collapse by subworkflow, stage or rule file. This is the level the literature and nf-metro support.
- "Hundreds to thousands" arises only at the **Jobs** level. There, Spectio caps at 200 jobs per step and 2000 in all; a step over the cap stays one node (`GraphPanel.tsx:22-24,36-50`). A wide scatter (one job per sample) becomes one rank with hundreds of 150 px boxes. dagre puts them side by side, so the map is very wide and fit-to-view shrinks labels below legibility **[to be validated by the spike]**.
- Collapsing by process or rule is the right default:
  - keep Process as the default level;
  - at the Jobs level, consider folding a step's jobs into one box with a small multiple or histogram above N jobs (the per-step job chart already exists in the panel, ui-spec §4.14 "Among its step's N jobs");
  - expand only the outliers (≥ 2× the median), not every job.
- Live re-layout moves nodes when a checkpoint adds steps (`ui-spec.md:829`). nf-metro avoids this by laying out once (`docs/live.mdx:27-28`). Stable positions (gap I1) matter more as the graph grows.
- dagre runs in `place()` on every new view (`GraphView.tsx:572`), and again inside the Auto-fold calculation (`GraphView.tsx:1202-1204`). Its cost at 2000 nodes on each live frame has not been measured **[to be validated]**.

**6.2 Phone.**
- The List view is the default on phones (`settings.ts:69`), and the details open in an `aria-modal` sheet (`ui-spec.md:818,827`). This avoids the wide-map problem the digest raises for nf-metro.
- The map is still reachable on a phone. React Flow's touch pan and pinch behaviour is not checked here **[to be validated on a device]**.
- Hover cards and right-click (code card) have no touch equivalent on the map. The ui-spec says the same facts are in the panel (`ui-spec.md:791`), so this is acceptable if the panel is complete.
- The `MRunGraph` board predates the 2026-11-11 redesigns (PR #251, Docs), so the phone screens have no current board.

**6.3 Keyboard and screen readers.**
- Strengths:
  - each node is a native `<button>` with a full accessible name (`GraphView.tsx:306-312,559-565`);
  - fold buttons have names, the panel returns focus to the step that opened it, and Escape is layered;
  - there is a List table equivalent (`GraphView.tsx:877-905`).
  This is far beyond nf-metro, which offers no keyboard operation beyond Escape and no SVG semantics (FC-M10).
- Gaps:
  - **edges cannot take focus** and their cards are hover-only (`GraphView.tsx:748,845-846`; PR #251 Known gaps);
  - Tab order follows the node array, not the drawing;
  - with **more than 300 nodes, off-screen buttons are not rendered** (`GraphView.tsx:855`), so Tab cannot reach them and a screen reader's element list is incomplete. Search (Enter for the next match) and the List view are the practical routes and should be stated as the keyboard path in ui-spec §4.14.
  - the picker roles in the spec do not match the code (FC-M11).
  - edge motion has no reduced-motion fallback (FC-M12).

**6.4 Colour-only encoding.**
- In Spectio, the state is printed as a word on each node (`GraphView.tsx:717`). The overlay value is printed too (`metric`, same line). `if` links are dashed and labelled. The critical path also gets a wider stroke and a ring (`graph.css:92-94,141-144`). So SC 1.4.1 is met for these.
- Remaining risks:
  - the **heatmap tint** and the **efficiency bands** are colour, though the value is printed;
  - the critical-path ring (state-review colour, 3 px) and the selection ring may be confused;
  - animated edges are the only cue that a link feeds a running step.
  None has been checked with a colour-vision-deficiency simulation **[to be validated]**.
- The contrast of faint edges against the background (SC 1.4.11, 3:1) has not been measured **[to be validated]**.

**6.5 What to measure in a spike** (in `spike/graph-scale`, on the demo and on real fixtures):
1. **Layout time.** Time `place()` for each layout (Layered TB and LR, Metro, Compact) at 50, 100, 300, 1000 and 2000 nodes, with real fan-out shapes: rnaseq Jobs level, Snakemake wildcards. Run it on desktop Chromium and under 4× CPU throttling as a phone proxy. Count `place()` calls per live frame (the map plus Auto-fold), and long tasks over 50 ms.
2. **Stability.** On a Snakemake checkpoint run, measure the mean and the largest node displacement between frames. Repeat with seeded positions (I1).
3. **Legibility.**
   - At fit-to-view on 1440×900 and 390×844, find the share of node labels rendered at 12 px or more.
   - Measure the map's aspect ratio, edge crossings and total edge length for Layered, Metro and Compact on the same graphs.
   - Count the folds Auto-fold needs to bring each graph to ≤ 24 boxes.
4. **Tasks.** With 5 or more users, or Thomas and colleagues, time three tasks, by mouse and keyboard only:
   - find the failed step and open its logs;
   - find the slowest sample at the Jobs level;
   - say what feeds step X.
   Compare Map (each layout) with the List.
5. **Assistive tech.** Run the same three tasks with VoiceOver (macOS and iOS) and NVDA. Record Tab stops to a given node, focus loss on a live refetch, and behaviour above 300 nodes (`onlyRenderVisibleElements`).
6. **Colour.** Run a deuteranopia, protanopia and tritanopia simulation over state, heatmap, efficiency bands and the crit and selected rings. Measure edge contrast against the background.
7. **Motion.** Count animated edges on a busy run, and check that a `prefers-reduced-motion` fix removes them.
8. **Baseline against a real metro map.** Feed Spectio's `nf-dag` document for nf-core/rnaseq to `nf-metro convert` (2.1.0). Compare the readability of that result and of Spectio's Metro layout on the same tasks. This tells whether a true transit-map view adds anything Spectio's grouped layered view lacks.
