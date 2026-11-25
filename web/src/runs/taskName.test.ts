// A job's name as a title and labelled parts (#385): the rule or process, then the wildcards of a
// Snakemake job (`k=v, k=v`, sorted by the server) or the Nextflow tag, never one `rule (…)` string.
import { expect, test } from "vitest";
import type { Task } from "../api";
import { NO_RESOURCES } from "../testing";
import { taskName } from "./taskName";

const task = (over: Partial<Task>): Task => ({
  id: "tsk_1",
  process: "align",
  tag: null,
  name: null,
  state: "succeeded",
  stage_id: null,
  attempt_n: 1,
  resources: NO_RESOURCES,
  ...over,
});

test("a Snakemake job: the rule, then one key and value per wildcard", () => {
  expect(taskName(task({ tag: "cell=C01, sample=S1" }))).toEqual({
    title: "align",
    parts: [
      { key: "cell", value: "C01" },
      { key: "sample", value: "S1" },
    ],
  });
});

test("a Nextflow task: the last segment of the process, the tag as one part with no key", () => {
  expect(taskName(task({ process: "NFCORE:RNASEQ:ALIGN", tag: "S01" }))).toEqual({
    title: "ALIGN",
    parts: [{ key: null, value: "S01" }],
  });
});

test("no tag, no part", () => {
  expect(taskName(task({ process: "ALIGN", name: "ALIGN" })).parts).toEqual([]);
  expect(taskName(task({ tag: "  " })).parts).toEqual([]);
});

test("a value may hold = and a comma inside brackets", () => {
  expect(taskName(task({ tag: "region=chr1:1-10, path=a=b, set=(x, y), sample=S1" })).parts).toEqual([
    { key: "region", value: "chr1:1-10" },
    { key: "path", value: "a=b" },
    { key: "set", value: "(x, y)" },
    { key: "sample", value: "S1" },
  ]);
});

test("a tag that is not all k=v keeps its raw text as one part", () => {
  expect(taskName(task({ tag: "sample=S1, lane 2" })).parts).toEqual([{ key: null, value: "sample=S1, lane 2" }]);
  expect(taskName(task({ tag: "=x" })).parts).toEqual([{ key: null, value: "=x" }]);
  expect(taskName(task({ tag: "a=(b, c" })).parts).toEqual([{ key: null, value: "a=(b, c" }]);
});
