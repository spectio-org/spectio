# Spike metroflow: BioFlow-Insight and MetroFlow as producers of Spectio's workflow graph (2026-11-10)

**Question.** For [#160](https://github.com/spectio-org/spectio/issues/160), we want to know:
- whether Spectio can fork or embed MetroFlow, the metro-map view of BioFlow-Insight;
- what its JSON looks like;
- whether it covers Snakemake;
- which renderer Spectio should use for an interactive graph with live states.

**Answer in one line.** Only the **producer** can be forked: BioFlow-Insight is MIT and its source is public, and it is vendored in `spikes/metroflow/upstream/`. The **MetroFlow renderer** is not public: it lives in a repository of the hosted service that asks for credentials. BioFlow-Insight reads Nextflow only. Its static edges are an estimate and can contain cycles. **Decision:** Spectio keeps its own engine-neutral graph document (api §5.10) and its own renderer (React Flow + dagre, ui-spec §4.14), and uses BioFlow-Insight as one optional producer, for Launch and as a fallback for Nextflow runs. Runtime truth comes from the engines: Nextflow's DAG through `nf-spectio`, and Snakemake's rule graph.

## Setup

| Item | Value |
|---|---|
| BioFlow-Insight | `bioflow-insight==2.1.1` from PyPI, plus the upstream git commit `69e0706f` (2026-10-29), in a Python 3.12 venv |
| Java | the system JDK; BioFlow-Insight bundles the Nextflow language server as a 15 MB jar and drives it through JPype |
| Graphviz | `dot` 2.x from apt. **Required**: without it, `--analysis metroflow` fails with `KeyError: 'position'` (`src/workflow.py:672`), because node positions come from Graphviz |
| Pipelines | `tests/pipelines/synthetic/nextflow/main.nf`; nf-core/fetchngs at `68fb6739` (2026-10-08) |
| Command | `bioflow-insight --analysis metroflow --output-dir <dir> <main.nf>` |

## Results

### 1. Licence and source

- BioFlow-Insight is under the MIT licence, © 2026 George Marchment, Université Paris-Saclay (`LICENSE` at commit `69e0706f`). Its source is at `gitlab.liris.cnrs.fr/sharefair/bioflow-insight`, which the PyPI project URLs point to ([PyPI JSON](https://pypi.org/pypi/bioflow-insight/json)). PyPI declares no licence classifier; the classifier line is commented out in `pyproject.toml`. The `LICENSE` file is the source of truth.
- The hosted service, `bioflow-insight.pasteur.cloud`, links its own code at `gitlab.pasteur.fr/sharefair/bioflow-insight-server` (in the page footer, read on 2026-11-10). On 2026-11-10 `git clone` of that repository asked for a username, so it is **not public**. The MetroFlow front end lives there. Its licence and whether it can be embedded are **unknown [to be validated]**: ask the authors.
- The hosted home page shows the logos of Institut Pasteur, Université Paris-Saclay, CNRS, LISN and ShareFAIR (image names in its HTML, 2026-11-10). The copyright holder is Université Paris-Saclay and the service is hosted on `pasteur.cloud`, so "Institut Pasteur lineage" in #160 is only partly right.
- Paper: Marchment et al., *BioFlow-Insight*, NAR Genomics and Bioinformatics 6(3), lqae092, 2024 ([doi](https://doi.org/10.1093/nargab/lqae092)).

### 2. The metro-map JSON (`graphs/metro_map.json`)

The output also includes `metro_map_condition.json`, `_dominator` and `_parallel`, which are variants of the same shape:

```jsonc
{
  "nodes": [{"id": "NFCORE_FETCHNGS_$$_1.FETCHNGS_$$_1.SRA_IDS_TO_RUNINFO",
             "name": "SRA_IDS_TO_RUNINFO",
             "position": {"x": "331.2", "y": "28.8"},   // strings, from Graphviz
             "code": "process … { … }",                  // the full process source
             "file_ref": "(workflows/fetchngs.nf)",
             "condition": "!skip_fastq_download" | null}],
  "edges": [{"A": "<node id>", "B": "<node id>", "id": "A -> B", "condition": "…"}],
  "subworkflows": {"NFCORE_FETCHNGS_$$_1.FETCHNGS_$$_1": {"nodes": 9, "label": "FETCHNGS",
                   "code": "workflow FETCHNGS { … }", "condition": null, "file_ref": "(…)"}}
}
```

- **Subworkflow nesting** is encoded in the ids: `.` separates the levels and `_$$_<n>` numbers the calls. This maps onto Nextflow's runtime qualified name `NFCORE_FETCHNGS:FETCHNGS:SRA_IDS_TO_RUNINFO` by stripping `_$$_<n>` and replacing `.` with `:` **[to be validated]** on a pipeline that calls the same subworkflow twice.
- **Conditions** (`if` blocks) are attached to nodes, edges and subworkflows.
- **Process code** is included, so the parameters a process reads (`params.<x>`) can be found with a regular expression.
- The JSON has **no schema version** field. Its README says of it: "**This needs to be updated**" (README L64). Expect it to change between releases.

### 3. Measurements

| Pipeline | Nodes | Edges | Subworkflows | Time | Notes |
|---|---|---|---|---|---|
| synthetic (8 processes) | 8 | 7 | 0 | < 5 s | Edges match the pipeline (MAKE_READS → … → FINAL_REPORT) |
| nf-core/fetchngs | 9 | 31 | 3 | 3.9 s wall | Edges include **cycles**: the four download processes (SRA_FASTQ_FTP, FASTQDL, ASPERA_CLI, SRATOOLS_*) each point at the others, because `ch_sra_metadata` is reassigned after `.mix()`. `process_dependency_graph.json` has **0 edges** for the same run |

The first attempt at `--analysis metroflow` falls back from the language server to BioFlow-Insight's own parser on any error. On the synthetic pipeline, the generic error "The Nextflow Language Server has detected an error" hid the real cause, the missing Graphviz.

### 4. Snakemake

The vendored source has no mention of Snakemake (`grep -ri snakemake` finds nothing). BioFlow-Insight **does not analyse Snakefiles**, as the issue assumed. For Snakemake, Spectio already stores the engine's rule graph for every invocation, with nodes and links (`snakemake.rulegraph`, api §7). That is runtime truth and needs no static analysis.

### 5. Renderer

| Option | Licence | Fit |
|---|---|---|
| MetroFlow front end | unknown, not public | Cannot be evaluated. It would also need our own states, accessibility and live updates |
| Cytoscape.js | MIT | Canvas rendering: the nodes are not DOM buttons, so the keyboard and screen-reader rules of ui-spec §4.11 need a parallel structure |
| **React Flow (`@xyflow/react`) + dagre (`@dagrejs/dagre`)** | MIT + MIT | DOM nodes, so each node is a native `<button>`. Pan, zoom, minimap and compound (parent) nodes are built in. dagre gives the layered layouts; the metro and compact layouts are ours |
| elkjs | EPL-2.0 or GPL-3.0 | Better orthogonal routing, but weak-copyleft licensing for a 1.4 MB bundle. Not needed for the first version |

**Chosen:** React Flow + dagre, pinned to versions at least two weeks old (`12.12.0` from 2026-09-24 and `3.1.2` from 2026-10-23, `npm view … time`).

## Consequences for the design

1. **Spectio's graph document** is the contract (api §5.10): one document for both engines, with `producer` and `complete` fields. BioFlow-Insight output is mapped into it, never passed through.
2. **Producers, from most to least trusted:** the Nextflow runtime DAG (`nf-spectio`, `onFlowBegin`); the Snakemake rule graph; BioFlow-Insight (static, marked as an estimate); stages only (nodes with no edges).
3. **Every graph algorithm tolerates cycles.** Layering, critical path and lineage drop back edges found by depth-first search.
4. **BioFlow-Insight runs on the server host, on the local workflow directory, in a subprocess with a timeout.** It is an optional install extra, because it needs Java and Graphviz. Code is never sent to the hosted service (security, #160 question 2).
5. **Not vendored into the product.** `spikes/metroflow/upstream/` is the spike's read-only copy. The product depends on the PyPI package through an optional extra.

## Open items

- MetroFlow front end: ask the authors about its licence and whether it is public **[to be validated]**.
- The id mapping on pipelines that call one subworkflow several times **[to be validated]**.
- nf-core scale: run BioFlow-Insight on nf-core/rnaseq for time and node count **[to be validated]**.
