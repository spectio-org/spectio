import { expect, test } from "vitest";
import type { Task } from "../../api";
import { DOC } from "./fixture";
import {
  acyclic,
  aggregateStatus,
  collapse,
  collapsedSubworkflow,
  criticalPath,
  diffGraphs,
  heat,
  lineage,
  ranks,
  search,
  statusAt,
  timeSpan,
  topoOrder,
} from "./model";

const P = "NFCORE_DEMO:DEMO:";

test("aggregate status: failed and running win, all done is done, part done is running", () => {
  expect(aggregateStatus(["done", "failed", "running"])).toBe("failed");
  expect(aggregateStatus(["done", "up_to_date"])).toBe("done");
  expect(aggregateStatus(["up_to_date", "up_to_date"])).toBe("up_to_date");
  expect(aggregateStatus(["done", "pending"])).toBe("running");
  expect(aggregateStatus(["pending", "pending"])).toBe("pending");
  expect(aggregateStatus([undefined, null])).toBeNull();
});

test("process level keeps every node and edge, with lanes from subworkflows", () => {
  const v = collapse(DOC, "process");
  expect(v.nodes).toHaveLength(6);
  expect(v.edges).toHaveLength(5);
  expect(v.nodes.find((n) => n.id === `${P}ALIGN:BWA`)?.laneLabel).toBe("ALIGN");
});

test("the wrapper chain NFCORE_DEMO > DEMO is skipped when collapsing subworkflows", () => {
  const sub = collapsedSubworkflow(DOC);
  expect(sub.get(`${P}QC:FASTQC`)).toBe(`sub:${P}QC`);
  expect(sub.get(`${P}REPORT`)).toBeNull();
});

test("subworkflow level: one node per subworkflow, nodes outside stay, edges aggregate", () => {
  const v = collapse(DOC, "subworkflow");
  expect(v.nodes.map((n) => n.label).sort()).toEqual(["ALIGN", "QC", "REPORT"]);
  const qc = v.nodes.find((n) => n.label === "QC")!;
  expect(qc.kind).toBe("subworkflow");
  expect(qc.members).toHaveLength(3);
  expect(qc.counts).toEqual({ succeeded: 4, cached: 1 });
  const align = v.nodes.find((n) => n.label === "ALIGN")!;
  expect(align.status).toBe("running");
  expect(align.metrics.duration_s).toBe(330);
  expect(v.edges.map((e) => e.id).sort()).toEqual([`sub:${P}ALIGN->${P}REPORT`, `sub:${P}QC->${P}REPORT`]);
});

test("stage level: one node per stage, a bucket for nodes without one", () => {
  const v = collapse(DOC, "stage");
  expect(v.nodes.map((n) => n.label).sort()).toEqual(["Align", "No stage", "QC"]);
  expect(v.edges).toHaveLength(2);
});

test("jobs level puts the loaded jobs inside their process", () => {
  const task = { id: "tsk_1", process: `${P}ALIGN:BWA`, tag: "S1", name: null, state: "running" } as unknown as Task;
  const v = collapse(DOC, "jobs", { [`${P}ALIGN:BWA`]: [task] });
  const bwa = v.nodes.find((n) => n.id === `${P}ALIGN:BWA`)!;
  expect(bwa.jobs?.map((j) => [j.id, j.label, j.status])).toEqual([["job:tsk_1", "S1", "running"]]);
});

test("search matches names and the kind:, state:, param: and file: fields, ANDed", () => {
  const v = collapse(DOC, "process");
  expect([...search(DOC, v, "qc")].sort()).toEqual([`${P}QC:FASTQC`, `${P}QC:MULTIQC`, `${P}QC:gate`]);
  expect([...search(DOC, v, "state:running")]).toEqual([`${P}ALIGN:BWA`]);
  expect([...search(DOC, v, "param:multiqc")]).toEqual([`${P}QC:MULTIQC`]);
  expect([...search(DOC, v, "file:fastqc")]).toEqual([`${P}QC:FASTQC`]);
  expect([...search(DOC, v, "kind:gate")]).toEqual([`${P}QC:gate`]);
  expect([...search(DOC, v, "param:outdir multi")]).toEqual([`${P}QC:MULTIQC`]);
  expect(search(DOC, v, "  ").size).toBe(0);
});

test("topological order and ranks", () => {
  const v = collapse(DOC, "process");
  const order = topoOrder(v);
  expect(order.indexOf(`${P}ALIGN:TRIM`)).toBeLessThan(order.indexOf(`${P}ALIGN:BWA`));
  expect(ranks(v).get(`${P}REPORT`)).toBe(3);
  const cyclic = { nodes: v.nodes.slice(0, 2), edges: [{ id: "a", source: v.nodes[0].id, target: v.nodes[1].id, conditions: [] }, { id: "b", source: v.nodes[1].id, target: v.nodes[0].id, conditions: [] }] };
  expect(topoOrder(cyclic)).toHaveLength(2);
});

test("critical path follows the longest durations", () => {
  const { nodes, edges } = criticalPath(collapse(DOC, "process"));
  expect([...nodes].sort()).toEqual([`${P}ALIGN:BWA`, `${P}ALIGN:TRIM`]);
  expect([...edges]).toEqual([`${P}ALIGN:TRIM->${P}ALIGN:BWA`]);
});

test("lineage walks ancestors, descendants or both", () => {
  const v = collapse(DOC, "process");
  expect([...lineage(v, `${P}QC:gate`, "up")].sort()).toEqual([`${P}QC:FASTQC`, `${P}QC:MULTIQC`, `${P}QC:gate`]);
  expect([...lineage(v, `${P}ALIGN:BWA`, "down")].sort()).toEqual([`${P}ALIGN:BWA`, `${P}REPORT`]);
  expect(lineage(v, `${P}ALIGN:BWA`, "both").size).toBe(3);
});

test("diff marks added and removed nodes, duration deltas and cached reuse", () => {
  const other = {
    ...DOC,
    nodes: [
      ...DOC.nodes.filter((n) => !n.id.endsWith("REPORT")).map((n) => ({ ...n, metrics: { ...n.metrics, duration_s: 20 } })),
      { ...DOC.nodes[0], id: "OLD", name: "OLD" },
    ],
  };
  const d = diffGraphs(DOC, other);
  expect(d.get(`${P}REPORT`)?.change).toBe("added");
  expect(d.get("OLD")?.change).toBe("removed");
  expect(d.get(`${P}ALIGN:BWA`)).toEqual({ change: "same", duration_delta: 280, reuse: "rerun" });
  expect(d.get(`${P}QC:MULTIQC`)?.reuse).toBe("cached");
});

test("replay: span, then state at a time", () => {
  const span = timeSpan(DOC)!;
  expect(span.to - span.from).toBe(50_000);
  const v = collapse(DOC, "process");
  const bwa = v.nodes.find((n) => n.id === `${P}ALIGN:BWA`)!;
  const multiqc = v.nodes.find((n) => n.id === `${P}QC:MULTIQC`)!;
  expect(statusAt(bwa, span.from)).toBe("pending");
  expect(statusAt(bwa, Date.parse("2026-11-10T10:00:45Z"))).toBe("running");
  expect(statusAt(multiqc, span.to)).toBe("done");
});

test("heat scales the overlay to the view's maximum", () => {
  const h = heat(collapse(DOC, "process"), "duration");
  expect(h.get(`${P}ALIGN:BWA`)).toBe(1);
  expect(h.get(`${P}QC:MULTIQC`)).toBeCloseTo(10 / 300);
  expect(h.has(`${P}REPORT`)).toBe(false);
});

// nf-core/fetchngs as BioFlow-Insight reads it: the four download processes point to each other
const CYCLIC = {
  ...DOC,
  producer: "bioflow-insight" as const,
  estimate: true,
  nodes: ["IN", "A", "B", "C", "D", "OUT"].map((id) => ({ ...DOC.nodes[0], id, name: id, subworkflow: null, metrics: { duration_s: 10 } })),
  edges: [
    { source: "IN", target: "A" },
    ...["A", "B", "C", "D"].flatMap((s) => ["A", "B", "C", "D"].filter((t) => t !== s).map((t) => ({ source: s, target: t, condition: s === "A" ? "params.ftp" : null }))),
    { source: "D", target: "OUT" },
  ],
};

test("cycles: back edges are dropped, so order, ranks and the critical path terminate", () => {
  const v = collapse(CYCLIC, "process");
  const dag = acyclic(v);
  expect(dag.edges.length).toBeLessThan(v.edges.length);
  expect(topoOrder(dag)).toEqual(topoOrder(v));
  const order = topoOrder(v);
  expect(order).toHaveLength(6);
  expect(order[0]).toBe("IN");
  expect(order.at(-1)).toBe("OUT");
  const r = ranks(v);
  expect(r.get("IN")).toBe(0);
  expect(r.get("OUT")).toBe(5);
  expect(criticalPath(v).nodes.size).toBe(6);
  expect(lineage(v, "B", "both").size).toBe(6);
});

test("edge conditions are kept per collapsed edge", () => {
  const v = collapse(CYCLIC, "process");
  expect(v.edges.find((e) => e.id === "A->B")?.conditions).toEqual(["params.ftp"]);
  expect(v.edges.find((e) => e.id === "B->C")?.conditions).toEqual([]);
});
