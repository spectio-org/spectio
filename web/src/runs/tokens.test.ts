// UI-19b (ui-spec §12.1, §12.15): the first part of runs.css, through the run header, reads
// spacing, radius and font sizes from the §12.2 tokens. A 1 px line stays, and so does the 4 px
// rail added to the side that carries it (§12.15 allowlist); the rest of the file
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
    .map((d) => d.replaceAll("+ 4px)", ")"))
    .filter((d) => /(?<![\w.-])-?(?!1px)\d+(?:\.\d+)?px/.test(d));
  expect(raw).toEqual([]);
});

// CR-P3UI19B-01: the side that carries the 4 px rail is lg + 4 px, not a snapped step, so cards
// with the same layout match and the run card's row-hit offset (-lg) still clears the rail.
test("the side that carries the rail is lg + 4 px", () => {
  const rule = (selector: string) => {
    const at = css.indexOf(`${selector} {`);
    expect(at).toBeGreaterThanOrEqual(0);
    return css.slice(at, css.indexOf("}", at));
  };
  const rail = "calc(var(--mantine-spacing-lg) + 4px)";
  const lg = "var(--mantine-spacing-lg)";
  expect(rule(".sp-cards li > a")).toContain(`padding: ${lg} ${lg} ${lg} ${rail};`);
  expect(rule(".sp-why")).toContain(`padding: ${lg} ${lg} ${lg} ${rail};`);
  expect(rule(".sp-row-card")).toContain(`var(--mantine-spacing-md) ${rail};`);
  expect(rule(".sp-run-head")).toMatch(/padding: calc\(var\(--mantine-spacing-lg\) \+ 4px\) /);
  const phone = css.slice(css.indexOf(".sp-run-head {", css.indexOf(".sp-run-head {") + 1));
  expect(phone.slice(0, phone.indexOf("}"))).toContain(`padding: ${rail} ${lg} ${lg};`);
  expect(rule(".sp-row-hit")).toContain("calc(-1 * var(--mantine-spacing-lg));");
});
