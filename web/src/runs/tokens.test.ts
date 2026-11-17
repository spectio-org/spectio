// UI-19b (ui-spec §12.1, §12.15): the first part of runs.css, through the run header, reads
// spacing, radius and font sizes from the §12.2 tokens. A 1 px line stays; the rest of the file
// (from the log frame on) is UI-19c.
/// <reference types="node" />
import { readFileSync } from "node:fs";

const css = readFileSync("src/runs/runs.css", "utf8");
const end = css.indexOf("/* the frame of an empty, failed or loading log");

test("runs.css through the run header writes no raw px for spacing, radius or font size", () => {
  expect(end).toBeGreaterThan(0);
  const declaration = /(?:^|[;{\s])((?:font-size|font|gap|row-gap|column-gap|padding[a-z-]*|margin[a-z-]*|border-radius)\s*:[^;}]*)/g;
  const raw = [...css.slice(0, end).matchAll(declaration)]
    .map((m) => m[1].trim())
    .filter((d) => /(?<![\w.-])-?(?!1px)\d+(?:\.\d+)?px/.test(d));
  expect(raw).toEqual([]);
});
