# Workflow graph: working contract (issue #160)

Draft contract shared by the server, web and nf-spectio work on branch
`claude/metroflow-interactive-graph-efgw5l`. When the work is done, the spec text moves to
`docs/specs/api-and-data-model.md` §5.10 (graph document), and the screens go to
`docs/specs/ui-spec.md` §4.14 (workflow graph). After that move, this file is kept only as the spike's record.

## Feature flag

- Server setting: `server.features: list[str]`, env `SPECTIO_SERVER_FEATURES` (comma-separated).
  The value `graph_view` turns the graph on. Default: off (0.0.1 ships without graphs, dev-env §15.1).
- `GET /api/v1/features` returns `{"features": ["graph_view"]}`. The web reads it once at boot.
- When the flag is off, every graph route answers `404` with problem type `feature-disabled`,
  and the web shows no Graph tab and no Launch map.

## GraphDocument (version 1)

```jsonc
{
  "version": 1,
  "engine": "nextflow" | "snakemake",
  "producer": "smk-rulegraph" | "nf-dag" | "bioflow-insight" | "stages-only",
  "complete": true,            // false: edges unknown (stages-only), or the DAG can still grow (open checkpoint)
  "groups": [                  // compounds, outermost first
    {"id": "stage:qc", "kind": "stage", "name": "QC", "parent": null, "condition": null},
    {"id": "sub:NFCORE_FETCHNGS:FETCHNGS", "kind": "subworkflow", "name": "FETCHNGS",
     "parent": "sub:NFCORE_FETCHNGS", "condition": "!skip_fastq_download"}
  ],
  "nodes": [
    {
      "id": "NFCORE_FETCHNGS:FETCHNGS:SRA_IDS_TO_RUNINFO", // the process/rule name Spectio stores (tasks.process_or_rule)
      "name": "SRA_IDS_TO_RUNINFO",                        // last segment, for display
      "kind": "process" | "rule" | "checkpoint" | "gate",
      "stage_id": "qc" | null,
      "subworkflow": "sub:NFCORE_FETCHNGS:FETCHNGS" | null,
      "source": {"file": "modules/local/x/main.nf", "line": 12} | null,
      "condition": "params.run_qc" | null,
      "params": ["outdir", "ena_metadata_fields"],         // params.<name> read by the node's code, when known
      // runtime overlay: only on /runs/{id}/graph, absent at Launch
      "status": "<ProcessStatus>",
      "counts": {"succeeded": 3, "running": 1},
      "retries": 0,
      "pipeline_order": 0,
      "metrics": {"duration_s": 120.5, "cpu_mean": 0.8, "mem_max": 0.6, "failed": 0},
      "first_start": "2026-11-10T10:00:00Z" | null,
      "last_end": "2026-11-10T10:02:00Z" | null
    }
  ],
  "edges": [{"source": "<node id>", "target": "<node id>"}]
}
```

- Node ids are the names Spectio already stores, so a node joins `/processes` and `/tasks?process=` with no mapping.
- Nextflow subworkflows come from the `:`-separated qualified process name, or from BioFlow-Insight when it produced the graph.
- Snakemake has no subworkflows. Its groups are the stages, plus one `subworkflow` group per rule `source.file` when the rules come from more than one file (`include:` / `module`).
- Gate nodes (`kind: "gate"`) come from the stage gates already detected. Each one sits after the last node of its stage, with an edge from that node.
- Untrusted text (names, conditions, file paths) is data. The web renders it only as text, never as HTML.

## Routes

| Route | Returns | Producer order |
|---|---|---|
| `GET /runs/{id}/graph` | GraphDocument with the runtime overlay | Snakemake: stored rule graphs (union, with links), `dag_updated` growth. Nextflow: `nf-dag` from `onFlowBegin` (`dag` field, see below), else `bioflow-insight` on the run's local workflow, else `stages-only` |
| `GET /workflows:graph?location=&revision=` | static GraphDocument (no overlay) for Launch | Snakemake: `snakemake --rulegraph` style output from the engine CLI (to be verified against 9.x), else rules from the files. Nextflow: `bioflow-insight` if installed, else processes from the stage detection with no edges |
| `GET /runs/{id}/processes/{name}/outputs` | `{"items": [{"path", "task_id", "attempt_n", "state": "present"/"removed"/"missing"/"unknown", "temp": bool}]}` | Snakemake: `attempts.outputs`. Nextflow: publish events (`NextflowFilePublish`) linked to the task, else the work dir |

Level collapsing (stage, subworkflow, process, jobs) runs in the browser on one document. The jobs level
loads `/runs/{id}/tasks?process=` for each expanded node.

## nf-spectio `onFlowBegin`

`onFlowBegin` adds `dag: {"processes": ["A", "B"], "edges": [["A", "B"]]}`, collapsed to process level from
`session.dag`: operators and channels are walked through, so only process-to-process dependencies remain. It is
bounded (at most 2000 processes and 20000 edges, else `dag: {"truncated": true}`). The SDK model and the projector
keep it on the logged event. The graph route reads it as `events.payload.dag` of the run's first `nextflow.onFlowBegin`.

## BioFlow-Insight producer

- Optional server extra `spectio-server[graph]`, which pins `bioflow-insight==2.1.1` (MIT). It runs in a
  subprocess with a timeout (60 s), an output directory under a temp dir, and no network. It runs on the
  local workflow directory only; code is never sent to the hosted service.
- Mapping: `metro_map.json` nodes give `name`, `code` (whose `params.<x>` reads become `params`), `file_ref`
  (which becomes `source.file`) and `position` (kept as the `upstream` layout hint `layout: {"x", "y"}`).
  `subworkflows` keys (`A_$$_1.B_$$_1`) become `sub:A:B`. A node is matched to a run node by its qualified
  name, else by its last segment when that is unique.

## Web views (ui-spec §4.14)

- **Levels:** Stage, Subworkflow, Process, Jobs (expanded).
- **Layouts:** Layered top-down, Layered left-right (dagre), Metro (one lane per stage or subworkflow, x
  = topological rank), Compact (grid per stage), Upstream (BioFlow-Insight positions, only when present).
- **Search:** by name, kind, state, parameter or file. Matches are highlighted and the rest is dimmed;
  Enter jumps to the next match; the query lives in the URL (`?tab=graph&q=`).
- **Overlays:** state (default), duration heatmap, CPU, memory, failures, and the critical path (the
  longest duration path).
- **Diff:** pick another run of the same workflow. Shows added and removed nodes, the duration change, and
  cached versus re-run.
- **Lineage:** trace the ancestors and descendants of a node, or of the node that produced an output file.
- **Replay:** a time scrubber from `first_start` to `last_end`, which colours nodes by their state at time t.
- **Minimap** and **export** (SVG/PNG).
- **Node sheet:** status, counts, params (with values from the run), outputs (live), tasks (link to the
  task sheet), source, condition.
- **Accessibility:** every node is a native `<button>` whose accessible name states its state. A List view
  is the table equivalent, and phone opens on the List view. Nothing is hover-only.
- **Live updates:** `useFrames` on the run refetches the graph; the layout stays stable, and nodes added
  after a checkpoint are appended.
