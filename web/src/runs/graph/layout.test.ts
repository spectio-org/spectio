import { expect, test } from "vitest";
import type { Task } from "../../api";
import { DOC } from "./fixture";
import { NODE_H, NODE_W, hasUpstream, place, sizeOf } from "./layout";
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

test("metro gives one lane per subworkflow, x by rank", () => {
  const { boxes, lanes } = place(collapse(DOC, "process"), "metro");
  expect(lanes.map((l) => l.label)).toEqual(["QC", "ALIGN", "DEMO"]);
  expect(boxes.get(`${P}REPORT`)!.x).toBeGreaterThan(boxes.get(`${P}ALIGN:BWA`)!.x);
  const qc = lanes[0];
  expect(boxes.get(`${P}QC:FASTQC`)!.y).toBeGreaterThanOrEqual(qc.y);
  expect(boxes.get(`${P}QC:FASTQC`)!.y).toBeLessThan(qc.y + qc.h);
});

test("upstream uses BioFlow-Insight positions when present", () => {
  const doc = { ...DOC, nodes: DOC.nodes.map((n, i) => ({ ...n, layout: { x: i * 10, y: 100 - i * 10 } })) };
  const view = collapse(doc, "process");
  expect(hasUpstream(view)).toBe(true);
  const { boxes } = place(view, "upstream");
  expect(boxes.get(doc.nodes[0].id)).toMatchObject({ x: 0, y: 0 });
  expect(hasUpstream(collapse(DOC, "process"))).toBe(false);
});

test("a process with jobs grows and lays its jobs out inside", () => {
  const tasks = Array.from({ length: 6 }, (_, i) => ({ id: `t${i}`, tag: `S${i}`, name: null, state: "succeeded" }) as unknown as Task);
  const view = collapse(DOC, "jobs", { [`${P}ALIGN:BWA`]: tasks });
  const bwa = view.nodes.find((n) => n.id === `${P}ALIGN:BWA`)!;
  const size = sizeOf(bwa);
  expect(size.w).toBeGreaterThan(NODE_W);
  expect(size.h).toBeGreaterThan(NODE_H);
  const { boxes } = place(view, "layered-tb");
  const jobs = tasks.map((t) => boxes.get(`job:${t.id}`)!);
  for (const j of jobs) expect(j.x + j.w).toBeLessThanOrEqual(size.w);
  for (const j of jobs) expect(j.y + j.h).toBeLessThanOrEqual(size.h);
  noOverlaps(boxes, tasks.map((t) => `job:${t.id}`));
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
