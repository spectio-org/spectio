// A small GraphDocument as the contract describes it (spikes/metroflow/graph-contract.md):
// nf-core style nesting NFCORE_DEMO > DEMO > {QC, ALIGN}, two stages and a gate. Tests and the
// Graph tab's screenshot use it.
import type { GraphDocument, GraphNode } from "./types";

const node = (id: string, over: Partial<GraphNode> = {}): GraphNode => ({
  id,
  name: id.split(":").at(-1)!,
  kind: "process",
  stage_id: null,
  subworkflow: null,
  source: null,
  condition: null,
  params: [],
  ...over,
});

export const DOC: GraphDocument = {
  version: 1,
  engine: "nextflow",
  producer: "nf-dag",
  complete: true,
  groups: [
    { id: "stage:qc", kind: "stage", name: "QC", parent: null, condition: null },
    { id: "stage:align", kind: "stage", name: "Align", parent: null, condition: null },
    { id: "sub:NFCORE_DEMO", kind: "subworkflow", name: "NFCORE_DEMO", parent: null, condition: null },
    { id: "sub:NFCORE_DEMO:DEMO", kind: "subworkflow", name: "DEMO", parent: "sub:NFCORE_DEMO", condition: null },
    { id: "sub:NFCORE_DEMO:DEMO:QC", kind: "subworkflow", name: "QC", parent: "sub:NFCORE_DEMO:DEMO", condition: "!params.skip_qc" },
    { id: "sub:NFCORE_DEMO:DEMO:ALIGN", kind: "subworkflow", name: "ALIGN", parent: "sub:NFCORE_DEMO:DEMO", condition: null },
  ],
  nodes: [
    node("NFCORE_DEMO:DEMO:QC:FASTQC", {
      stage_id: "qc",
      subworkflow: "sub:NFCORE_DEMO:DEMO:QC",
      params: ["outdir"],
      source: { file: "modules/nf-core/fastqc/main.nf", line: 1 },
      status: "done",
      counts: { succeeded: 4 },
      metrics: { duration_s: 40, cpu_mean: 0.9, mem_max: 0.3, failed: 0 },
      first_start: "2026-11-10T10:00:00Z",
      last_end: "2026-11-10T10:00:40Z",
    }),
    node("NFCORE_DEMO:DEMO:QC:MULTIQC", {
      stage_id: "qc",
      subworkflow: "sub:NFCORE_DEMO:DEMO:QC",
      params: ["outdir", "multiqc_title"],
      status: "done",
      counts: { cached: 1 },
      metrics: { duration_s: 10, failed: 0 },
      first_start: "2026-11-10T10:00:40Z",
      last_end: "2026-11-10T10:00:50Z",
    }),
    node("NFCORE_DEMO:DEMO:QC:gate", { kind: "gate", name: "QC gate", stage_id: "qc", subworkflow: "sub:NFCORE_DEMO:DEMO:QC" }),
    node("NFCORE_DEMO:DEMO:ALIGN:TRIM", {
      stage_id: "align",
      subworkflow: "sub:NFCORE_DEMO:DEMO:ALIGN",
      status: "done",
      counts: { succeeded: 4 },
      metrics: { duration_s: 30, failed: 0 },
      first_start: "2026-11-10T10:00:00Z",
      last_end: "2026-11-10T10:00:30Z",
    }),
    node("NFCORE_DEMO:DEMO:ALIGN:BWA", {
      stage_id: "align",
      subworkflow: "sub:NFCORE_DEMO:DEMO:ALIGN",
      params: ["genome"],
      status: "running",
      counts: { succeeded: 2, running: 2 },
      metrics: { duration_s: 300, cpu_mean: 0.6, mem_max: 0.8, failed: 1 },
      first_start: "2026-11-10T10:00:30Z",
      last_end: null,
    }),
    node("NFCORE_DEMO:DEMO:REPORT", {
      subworkflow: "sub:NFCORE_DEMO:DEMO",
      status: "pending",
      counts: {},
      metrics: {},
    }),
  ],
  edges: [
    { source: "NFCORE_DEMO:DEMO:QC:FASTQC", target: "NFCORE_DEMO:DEMO:QC:MULTIQC" },
    { source: "NFCORE_DEMO:DEMO:QC:MULTIQC", target: "NFCORE_DEMO:DEMO:QC:gate" },
    { source: "NFCORE_DEMO:DEMO:ALIGN:TRIM", target: "NFCORE_DEMO:DEMO:ALIGN:BWA" },
    { source: "NFCORE_DEMO:DEMO:ALIGN:BWA", target: "NFCORE_DEMO:DEMO:REPORT" },
    { source: "NFCORE_DEMO:DEMO:QC:gate", target: "NFCORE_DEMO:DEMO:REPORT" },
  ],
};
