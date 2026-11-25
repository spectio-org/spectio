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

// #385 (ui-spec §12.8): one table header style, in the muted text colour, readable on the header
// background (and the sort icon's faint colour on the raised one, 3:1 for a control) in both schemes.
const tokens = readFileSync("../design/tokens/spectio-tokens.css", "utf8");
const [light, dark] = [tokens.slice(0, tokens.indexOf(':root[data-theme="dark"]')), tokens.slice(tokens.indexOf(':root[data-theme="dark"]'))];

/** A token's hex in a scheme's block, following `var(--sp-…)` aliases (dark falls back to the light block). */
function hex(token: string, scheme: string): string {
  const own = new RegExp(`${token}:\\s*(#[0-9A-Fa-f]{6}|var\\(--[\\w-]+\\))`).exec(scheme) ?? new RegExp(`${token}:\\s*(#[0-9A-Fa-f]{6}|var\\(--[\\w-]+\\))`).exec(light);
  const value = own![1];
  return value.startsWith("#") ? value : hex(value.slice(4, -1), scheme);
}
const luminance = (h: string) => {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

test("the table header is --sp-text-muted, with 4.5:1 on its background in light and dark", () => {
  const rule = css.slice(css.indexOf(".sp-table th {"), css.indexOf("}", css.indexOf(".sp-table th {")));
  expect(rule).toContain("color: var(--sp-text-muted);");
  expect(rule).toContain("padding: var(--sp-cell-py) var(--sp-cell-px);");
  for (const scheme of [light, dark]) {
    expect(contrast(hex("--sp-text-muted", scheme), hex("--sp-surface-subtle", scheme))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hex("--sp-text-faint", scheme), hex("--sp-surface-raised", scheme))).toBeGreaterThanOrEqual(3);
  }
});

test("CR-03 (#385): the compact table keeps its sticky cells' borders and scrolls a focused control clear of them", () => {
  const rule = (selector: string) => {
    const at = css.indexOf(`${selector} {`);
    expect(at).toBeGreaterThanOrEqual(0);
    return css.slice(at, css.indexOf("}", at));
  };
  expect(rule('.sp-table[data-density="compact"]')).toContain("border-collapse: separate;");
  expect(rule('.sp-table-wrap:has(> .sp-table[data-density="compact"])')).toContain("scroll-padding: 3rem 0 0 8rem;");
});
