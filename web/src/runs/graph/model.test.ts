import { expect, test } from "vitest";
import type { Task } from "../../api";
import { DOC } from "./fixture";
import {
  declarations,
  acyclic,
  aggregateStatus,
  autoFold,
  bandOf,
  collapse,
  collapsedSubworkflow,
  criticalPath,
  diffGraphs,
  heat,
  lineage,
  ranks,
  restrict,
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

const job = (id: string, process: string, tag: string | null, state = "succeeded") => ({ id, process, tag, name: null, state }) as unknown as Task;

test("jobs level: one node per job, linked by matching keys, a single job links to all", () => {
  const TRIM = `${P}ALIGN:TRIM`;
  const BWA = `${P}ALIGN:BWA`;
  const v = collapse(DOC, "jobs", {
    [TRIM]: [job("t1", TRIM, "S1"), job("t2", TRIM, "S2")],
    [BWA]: [job("b1", BWA, "sample=S1", "running"), job("b2", BWA, "sample=S2"), job("b3", BWA, "S3")],
  });
  expect(v.nodes.some((n) => n.id === BWA)).toBe(false);
  const b1 = v.nodes.find((n) => n.id === "job:b1")!;
  expect([b1.kind, b1.label, b1.status, b1.step, b1.lane]).toEqual(["job", "sample=S1", "running", "BWA", BWA]);
  const links = v.edges.filter((e) => e.source.startsWith("job:t")).map((e) => `${e.source}->${e.target}`);
  // "S1" is not part of "sample=S1": keys are compared as tokens, so these do not link
  expect(links).toEqual([]);
  const tagged = collapse(DOC, "jobs", { [TRIM]: [job("t1", TRIM, "S1"), job("t2", TRIM, "S2")], [BWA]: [job("b1", BWA, "S1"), job("b2", BWA, "S2 lane1")] });
  expect(tagged.edges.filter((e) => e.source.startsWith("job:t")).map((e) => `${e.source}->${e.target}`)).toEqual(["job:t1->job:b1", "job:t2->job:b2"]);
  // REPORT has no jobs: every BWA job links to it
  expect(tagged.edges.filter((e) => e.target === `${P}REPORT` && e.source.startsWith("job:")).map((e) => e.source)).toEqual(["job:b1", "job:b2"]);
});

test("a folded group is one node at the Process level, an unfolded one shows its steps", () => {
  const ALIGN = "sub:NFCORE_DEMO:DEMO:ALIGN";
  const v = collapse(DOC, "process", {}, [ALIGN]);
  const align = v.nodes.find((n) => n.id === ALIGN)!;
  expect([align.kind, align.members.length, align.group]).toEqual(["subworkflow", 2, ALIGN]);
  expect(v.nodes.find((n) => n.id === `${P}QC:FASTQC`)!.group).toBe("sub:NFCORE_DEMO:DEMO:QC");
  expect(v.edges.map((e) => e.id)).toContain(`${ALIGN}->${P}REPORT`);
  const sub = collapse(DOC, "subworkflow", {}, [ALIGN]);
  expect(sub.nodes.some((n) => n.id === `${P}ALIGN:BWA`)).toBe(true);
  expect(sub.nodes.some((n) => n.id === "sub:NFCORE_DEMO:DEMO:QC")).toBe(true);
  const stage = collapse(DOC, "stage", {}, ["stage:qc"]);
  expect(stage.nodes.map((n) => n.id)).toContain(`${P}QC:FASTQC`);
  expect(stage.nodes.map((n) => n.id)).toContain("stage:align");
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
  const cyclic = { nodes: v.nodes.slice(0, 2), edges: [{ id: "a", source: v.nodes[0].id, target: v.nodes[1].id, conditions: [], pairs: [] }, { id: "b", source: v.nodes[1].id, target: v.nodes[0].id, conditions: [], pairs: [] }] };
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

test("restrict: a focused group keeps its steps only; a hidden step's links are bridged", () => {
  const view = collapse(DOC, "process");
  const qc = restrict(DOC, view, `sub:${P}QC`, []);
  expect(qc.nodes.map((n) => n.label).sort()).toEqual(["FASTQC", "MULTIQC", "QC gate"]);
  expect(qc.edges).toHaveLength(2);
  expect(restrict(DOC, view, "stage:align", []).nodes.map((n) => n.label).sort()).toEqual(["BWA", "TRIM"]);
  const hidden = restrict(DOC, view, null, [`${P}QC:MULTIQC`, `${P}QC:gate`]);
  expect(hidden.nodes.map((n) => n.label)).not.toContain("MULTIQC");
  expect(hidden.edges.some((e) => e.source === `${P}QC:FASTQC` && e.target === `${P}REPORT`)).toBe(true);
  expect(restrict(DOC, view, null, [])).toBe(view);
});

test("autoFold folds the biggest groups first, until the view fits", () => {
  const view = collapse(DOC, "process");
  expect(autoFold(view, 100)).toEqual([]);
  const fold = autoFold(view, 4);
  expect(fold[0]).toBe(`sub:${P}QC`);
  expect(collapse(DOC, "process", {}, fold).nodes.length).toBeLessThanOrEqual(4);
});

test("efficiency bands", () => {
  expect([0.1, 0.5, 0.9, 1.3].map(bandOf)).toEqual(["low", "fair", "good", "over"]);
});

test("declarations read a process's channel items and a rule's files", () => {
  const nf = `process TRIM {
    input:
    tuple val(meta), path(reads)
    path index // the index
    output:
    tuple val(meta), path("*.fq.gz"), emit: reads
    path "*.log", emit: log, optional: true
    script:
    """
    trim
    """
}`;
  expect(declarations(nf, "nextflow", "input").map((d) => d.parts)).toEqual([
    [
      { kind: "val", name: "meta" },
      { kind: "path", name: "reads" },
    ],
    [{ kind: "path", name: "index" }],
  ]);
  const outs = declarations(nf, "nextflow", "output");
  expect(outs.map((d) => [d.label, d.optional])).toEqual([
    ["reads", false],
    ["log", true],
  ]);
  expect(outs[1].parts).toEqual([{ kind: "path", name: '"*.log"' }]);
  const smk = `rule bwa_map:
    input:
        reads="trimmed/{sample}.fq.gz",
        ref=config["ref"]
    output:
        temp("mapped/{sample}.bam")
    shell:
        "bwa mem {input} > {output}"`;
  expect(declarations(smk, "snakemake", "input").map((d) => [d.label, d.parts[0].name])).toEqual([
    ["reads", '"trimmed/{sample}.fq.gz"'],
    ["ref", 'config["ref"]'],
  ]);
  expect(declarations(smk, "snakemake", "output")[0].parts[0]).toEqual({ kind: "temp", name: '"mapped/{sample}.bam"' });
  expect(declarations('rule all:\n    input:\n        expand("qc/{sample}.html", sample=SAMPLES)\n', "snakemake", "input")[0].parts).toEqual([{ kind: "expand", name: '"qc/{sample}.html"' }]);
});

test("a job keeps its step's checkpoint, temp and conditional marks, and is marked retried on its own", () => {
  const BWA = `${P}ALIGN:BWA`;
  const doc = { ...DOC, nodes: DOC.nodes.map((n) => (n.id === BWA ? { ...n, temp: true, condition: "params.align", retries: 1 } : n)) };
  const again = { ...job("b2", BWA, "S2"), attempt_n: 2 } as Task;
  const v = collapse(doc, "jobs", { [BWA]: [job("b1", BWA, "S1"), again] });
  expect(v.nodes.find((n) => n.id === "job:b1")!.flags).toEqual(["temp", "conditional"]);
  expect(v.nodes.find((n) => n.id === "job:b2")!.flags).toEqual(["temp", "conditional", "retried"]);
});
