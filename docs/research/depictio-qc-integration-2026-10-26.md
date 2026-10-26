# Research: one QC pipeline for Spectio gates and depictio dashboards (2026-10-26)

Question (Thomas, 2026-10-26): how should Spectio's QC screens connect to depictio, so that the two apps render the same results in a harmonious, homogeneous way?

Source: a shallow clone of `github.com/depictio/depictio` at commit `0d1aa0a` (2026-10-23). File references below are relative to that tree. The proposal that follows from it is in [`api-and-data-model.md`](../specs/api-and-data-model.md) §13.6.

## 1. What depictio already has

### 1.1 A catalogue that maps tool outputs to tables and components
- `depictio/catalog/README.md` describes a linking table:

  ```text
  raw nf-core file ─find→ recipe (.py) → bindable columns ─renders_as→ dashboard component
  ```

  It is anchored on bio.tools, nf-core and EDAM.
- **Shape.** One folder per tool module: a `module.yaml`, one YAML per output, and a co-located fixture. A recipe is a Python reshape that declares its columns in `OUTPUT_SCHEMA`. The rule is that columns have "one home", in the recipe.
- **Size.** 120 module folders and 413 output YAMLs (`ls depictio/catalog/*/`, 2026-10-26).
- **Outputs that match Spectio's checks.** They include:
  - `multiqc/frip_score.yaml`, `nsc_coefficient.yaml` and `rsc_coefficient.yaml` (ChIP-family peak QC);
  - `multiqc/mirtrace_length.*` (the small-RNA read-length distribution);
  - `multiqc/mosdepth.yaml`;
  - `cellranger/cell_qc.*`, `metrics_summary.*` and `barcode_rank.*`;
  - `checkm2/`, `busco/`, `quast` and `ivar/`.
- **Reading MultiQC.** MultiQC outputs are read from the report's `multiqc.parquet`, including the nested report folders of rnaseq (`multiqc/frip_score.yaml`, `find.path_glob` and `path_glob_alt`).
- **Per-cell QC with a MAD flag.** `cellranger/cell_qc.py` computes, per cell, `n_umi`, `n_genes`, `pct_mito`, `pct_ribo`, `pct_hb`, `pct_top20` and the cluster columns (`OUTPUT_SCHEMA`, l.227). The flag uses per-sample MAD rules (l.70–73):
  - low outlier if `log1p(n_umi)` or `log1p(n_genes)` is below the median − 5·MAD;
  - outlier if `pct_top20` is above the median + 5·MAD;
  - outlier if `pct_mito` is above the median + 3·MAD, or above 8.
- **Tooling.** `depictio dev catalog validate` (`depictio/cli/cli/commands/catalog.py:345`) grounds every `renders_as` role against the recipe's real output columns. `catalog match` and `catalog compose` recognise and assemble outputs from a run.

### 1.2 Templates validated on the same megatests
- 41 versioned nf-core templates live under `depictio/projects/nf-core/<pipeline>/<version>/`, each with its `template.yaml` and `dashboards/` (`find … -name template.yaml`).
- Each template has a `megatest.yaml`. It records the AWS megatest run it was validated against, and the tables-only subset fetched by `scripts/nfcore_megatest.py`.
- Example: `scrnaseq/4.2.0/megatest.yaml` is pbmc8k, 8,767 cells on the Cell Ranger route. That is the same run as Spectio's `tests/fixtures/megatests/scrnaseq/` and the ReviewCells board.
- **Consequence:** depictio and Spectio fetch the same public data with two tools (`scripts/nfcore_megatest.py` there, `tools/fixtures/megatests.py` here). The two should merge (§3).

### 1.3 Dashboards: component types and joins
- **Component types** (`depictio/models/components/union.py:23-33`): `advanced_viz`, `card`, `figure`, `highlight`, `interactive`, `map`, `table` and `text`.
  - `interactive` components filter the other components (`models/components/interactive.py`).
  - `advanced_viz` covers heatmap, contact map, coverage track, embedding, group compare, sankey and upset (research note depictio-admin-ops, task kinds).
- **Joins.** Projects carry `joins: list[JoinDefinition]` for client-side joins between data collections (`depictio/models/models/projects.py:32`).
- **Data collection kinds** (`data_collections_types/`): table, image, multiqc, jbrowse, geojson, indexed_file, phylogeny… (research note depictio-harmonization, §1).

### 1.4 Embedding
- The viewer accepts a colour scheme from a parent frame: `postMessage({type: 'depictio:set-color-scheme', scheme})` (`depictio/viewer/src/lib/embedColorScheme.ts:14`, `viewer/src/main.tsx:159-165`). It is used by the docs embeds today.
- There is no message for a selection or a filter yet **[to be validated]** (none found by grep on `postMessage`).

### 1.5 Renderers
- `packages/depictio-react-core` holds `FigureRenderer`, `TableRenderer`, `MultiQCRenderer`, `ImageRenderer`, `JBrowseRenderer`, `MapRenderer` and the `advanced_viz` renderers (research note depictio-frontend-admin).
- The package is private and unbuilt, and hard-codes `API_BASE` ([`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md) §1.3).

## 2. What this means for Spectio

1. **Checks should read catalogue outputs, not raw files.**
   - The catalogue already solves most of R12 UX-101 and UX-102: real MultiQC column names, reshapes, per-item tables, derived metrics and fixtures.
   - A Spectio check binds to a catalogue output's column. Example: `depictio:cellranger/cell_qc#pct_mito` with `by: sample`.
2. **One computation, two renderers.**
   - At gate time the runner runs the same recipes on the partial outputs.
   - The gate evaluates its checks on those tables.
   - The hand-off then ingests the same tables into depictio, so the numbers in a review and in the dashboard are identical by construction.
3. **Decisions travel as data.**
   - Spectio writes two tables per gate: `spectio_checks` (item, check, value, threshold, state) and `spectio_decisions` (item, decision, reason, actor, gate, time).
   - They are joined to the catalogue tables on the item key through depictio's `joins`.
   - Dashboards can then colour, filter or hide by decision without any Spectio code.
4. **Same components, a decision layer on top.**
   - Spectio's review views are depictio renderers plus a thin decision layer: selection, keep / exclude / flag, threshold handles and the sticky changes bar.
   - They share one `BrandTheme`, one chart palette and one set of check-state colours.
5. **Two-way navigation.**
   - **A preliminary dashboard at gate time.** `depictio: on: gate:<id>` already exists in §13.3. It is embedded in the review's Dashboard tab.
   - **Selection sync** between the two frames, by message. This is new and needs a request to depictio.
   - **Back-links:** a Spectio gate tile on the depictio side links back to the decision.

## 3. Requests to depictio (to add to depictio-ecosystem-reuse.md §3)

1. **`checks_as` beside `renders_as` in output YAMLs.**
   - Presets such as `{kind: outlier, column: pct_mito, by: sample, k: 3}` or `{kind: min, column: frip, value: 0.2}`, validated against `OUTPUT_SCHEMA` like `renders_as`.
   - Spectio reads them as its check presets ([`checking-scenarios.md`](../specs/checking-scenarios.md) §4).
2. **A runnable recipe entry point.** Something like `depictio catalog run <module>/<output> <results dir> --out <parquet>`, without a server. The runner then computes the same tables at gate time.
3. **Selection and filter messages for embeds.** For example `depictio:set-filter {column, values}` and `depictio:selection {key, values}`, next to `depictio:set-color-scheme`.
4. **Publish the renderers.** A built `@bioplatform/viz` package with a configurable `apiBase` (extends the existing theme-extraction request).
5. **Per-file recipes for live checks.** STAR `Log.final.out`, Trim Galore and fastp reports, Salmon `meta_info.json`, mosdepth summaries, with the same column names as the MultiQC route. Today STAR and Salmon QC are read only from `multiqc.parquet` (`multiqc/star.yaml`, `multiqc/salmon.yaml`), which exists only at the end of a run ([`checking-scenarios.md`](../specs/checking-scenarios.md) §11.6).
6. **One megatest fetcher.** Merge `scripts/nfcore_megatest.py` and Spectio's `tools/fixtures/megatests.py` into one shared tool. The two sides then pin the same release per pipeline.

## 4. Open points

- **Recipe runtime on the runner.** Recipes use polars. Running them needs a depictio-cli install, or a small shared runtime, in the runner's environment.
- **Size.** Per-cell tables are large: 8,767 cells × about 30 columns for pbmc8k, and millions of cells in real runs. Gate checks should read aggregates, with per-cell tables streamed on demand.
- **When nothing reads a decision.** A pipeline may have no parameter that reads a decision (R12 UX-108). The decision tables still reach depictio, so dashboards reflect the review even when the engine cannot.
