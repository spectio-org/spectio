// UI-19b and UI-19c (ui-spec §12.1, §12.15): runs.css reads spacing, radius and font sizes from
// the §12.2 tokens. A 1 px line stays, and so does the 4 px rail added to the side that carries it
// (§12.15 allowlist).
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { rawPx } from "../rawPx";

const css = readFileSync("src/runs/runs.css", "utf8");

// Fixed geometry, not steps of the scale: the icon centred on the first line of a name (half the
// 16 px icon), the switch knob's two positions inside its 36 px track, and the pin's optical nudge.
const GEOMETRY = ["+ 4px)", "calc(0.5lh - 8px)", "margin-left: 3px", "margin-left: 17px", "margin-top: -2px"];

test("runs.css writes no raw px for spacing, radius or font size", () => {
  expect(rawPx(css, GEOMETRY)).toEqual([]);
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
