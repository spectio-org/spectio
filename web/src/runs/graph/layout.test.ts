import { expect, test } from "vitest";
import type { Task } from "../../api";
import { DOC } from "./fixture";
import { NODE_W, hasUpstream, place, sizeOf } from "./layout";
import { collapse } from "./model";

const P = "NFCORE_DEMO:DEMO:";
const overlap = (a: { x: number; y: number; w: number; h: number }, b: typeof a) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

function noOverlaps(boxes: Map<string, { x: number; y: number; w: number; h: number }>, ids: string[]) {
  for (const a of ids) for (const b of ids) if (a < b) expect(overlap(boxes.get(a)!, boxes.get(b)!), `${a} / ${b}`).toBe(false);
}

test.each(["layered-tb", "layered-lr", "metro", "compact", "upstream"] as const)("%s places every node without overlap", (layout) => {
  const view = collapse(DOC, "process");
  const { boxes } = place(view, layout);
  expect(boxes.size).toBe(view.nodes.length);
  noOverlaps(boxes, view.nodes.map((n) => n.id));
});

test("layered top-down puts a target below its source; left-right puts it to the right", () => {
  const view = collapse(DOC, "process");
  const tb = place(view, "layered-tb").boxes;
  expect(tb.get(`${P}ALIGN:BWA`)!.y).toBeGreaterThan(tb.get(`${P}ALIGN:TRIM`)!.y);
  const lr = place(view, "layered-lr").boxes;
  expect(lr.get(`${P}ALIGN:BWA`)!.x).toBeGreaterThan(lr.get(`${P}ALIGN:TRIM`)!.x);
});

test("metro draws each subworkflow as an area around its steps, left to right", () => {
  const { boxes, lanes } = place(collapse(DOC, "process"), "metro");
  expect(lanes.map((l) => l.label).sort()).toEqual(["ALIGN", "DEMO", "QC"]);
  expect(boxes.get(`${P}REPORT`)!.x).toBeGreaterThan(boxes.get(`${P}ALIGN:BWA`)!.x);
  const qc = lanes.find((l) => l.label === "QC")!;
  const b = boxes.get(`${P}QC:FASTQC`)!;
  expect(b.x).toBeGreaterThanOrEqual(qc.x!);
  expect(b.x + b.w).toBeLessThanOrEqual(qc.x! + qc.w!);
  expect(b.y).toBeGreaterThan(qc.y);
  expect(b.y + b.h).toBeLessThanOrEqual(qc.y + qc.h);
});

test("compact packs small groups side by side, into a near-square map", () => {
  const groups = Array.from({ length: 8 }, (_, g) => ({ id: `sub:G${g}`, kind: "subworkflow" as const, name: `G${g}`, parent: null, condition: null }));
  const nodes = groups.flatMap((g, i) => [0, 1].map((j) => ({ ...DOC.nodes[0], id: `G${i}:S${j}`, name: `S${j}`, stage_id: null, subworkflow: g.id })));
  const { boxes, lanes } = place(collapse({ ...DOC, groups, nodes, edges: [] }, "process"), "compact");
  expect(new Set(lanes.map((l) => l.y)).size).toBeLessThan(lanes.length);
  const w = Math.max(...[...boxes.values()].map((b) => b.x + b.w));
  const h = Math.max(...[...boxes.values()].map((b) => b.y + b.h));
  expect(w / h).toBeLessThan(4);
  noOverlaps(boxes, [...boxes.keys()]);
});

test("upstream uses BioFlow-Insight positions when present", () => {
  const doc = { ...DOC, nodes: DOC.nodes.map((n, i) => ({ ...n, layout: { x: i * 10, y: 100 - i * 10 } })) };
  const view = collapse(doc, "process");
  expect(hasUpstream(view)).toBe(true);
  const { boxes } = place(view, "upstream");
  expect(boxes.get(doc.nodes[0].id)).toMatchObject({ x: 0, y: 0 });
  expect(hasUpstream(collapse(DOC, "process"))).toBe(false);
});

test("the Jobs level lays out one box per job, without overlaps", () => {
  const tasks = Array.from({ length: 6 }, (_, i) => ({ id: `t${i}`, tag: `S${i}`, name: null, state: "succeeded" }) as unknown as Task);
  const view = collapse(DOC, "jobs", { [`${P}ALIGN:BWA`]: tasks });
  for (const layout of ["layered-tb", "layered-lr", "metro", "compact"] as const) {
    const { boxes } = place(view, layout);
    noOverlaps(boxes, view.nodes.map((n) => n.id));
    expect(boxes.get("job:t0")!.w).toBe(sizeOf(view.nodes.find((n) => n.id === "job:t0")!).w);
  }
});

test("a cyclic static graph lays out in every layout", () => {
  const nodes = ["A", "B", "C"].map((id) => ({ ...DOC.nodes[0], id, name: id }));
  const doc = { ...DOC, nodes, edges: [{ source: "A", target: "B" }, { source: "B", target: "C" }, { source: "C", target: "A" }] };
  const view = collapse(doc, "process");
  for (const layout of ["layered-tb", "layered-lr", "metro", "compact", "upstream"] as const) {
    const { boxes } = place(view, layout);
    expect(boxes.size).toBe(3);
    noOverlaps(boxes, ["A", "B", "C"]);
  }
});

test("with no edges, every layout wraps lanes into rows instead of one long line", () => {
  const nodes = Array.from({ length: 40 }, (_, i) => ({ ...DOC.nodes[0], id: `P${i}`, name: `P${i}`, subworkflow: null, stage_id: i < 20 ? "a" : "b" }));
  const view = collapse({ ...DOC, groups: [], nodes, edges: [] }, "process");
  for (const layout of ["layered-tb", "layered-lr", "metro", "compact"] as const) {
    const { boxes } = place(view, layout);
    const width = Math.max(...[...boxes.values()].map((b) => b.x + b.w));
    expect(width, layout).toBeLessThan(8 * (NODE_W + 40));
    noOverlaps(boxes, view.nodes.map((n) => n.id));
  }
});
