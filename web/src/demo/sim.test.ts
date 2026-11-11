import { expect, test } from "vitest";
import { collapse } from "../runs/graph/model";
import { STEPS } from "./pipeline";
import { FLAKY, MAX_RUNNING, advance, finished, graphOf, newSim } from "./sim";

test("the simulated run respects its links, retries the flaky task once and ends", () => {
  const sim = newSim(Date.parse("2026-11-11T09:00:00Z"));
  let peak = 0;
  for (let i = 0; i < 400 && !finished(sim); i++) {
    advance(sim, 10);
    peak = Math.max(peak, sim.tasks.filter((t) => t.state === "running").length);
    const doc = graphOf(sim);
    for (const e of doc.edges) {
      const target = doc.nodes.find((n) => n.id === e.target)!;
      const source = doc.nodes.find((n) => n.id === e.source)!;
      if (target.status !== "pending" && !STEPS.find((s) => s.id === e.target)!.perSample) expect(source.status, e.target).toBe("done");
    }
  }
  expect(finished(sim)).toBe(true);
  expect(peak).toBeLessThanOrEqual(MAX_RUNNING);
  const doc = graphOf(sim);
  expect(doc.nodes.every((n) => n.status === "done")).toBe(true);
  expect(doc.nodes.find((n) => n.id === FLAKY.step)!.retries).toBe(1);
  expect(collapse(doc, "subworkflow").nodes.length).toBeGreaterThan(3);
});

test("a skipped step leaves the graph with its links", () => {
  const skip = STEPS.find((s) => s.id.endsWith("RSEQC_INFEREXPERIMENT"))!.id;
  const doc = graphOf(newSim(0, { skip: [skip] }));
  expect(doc.nodes.some((n) => n.id === skip)).toBe(false);
  expect(doc.edges.some((e) => e.source === skip || e.target === skip)).toBe(false);
});
