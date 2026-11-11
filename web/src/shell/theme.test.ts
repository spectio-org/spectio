// The design-system defaults of theme.ts (UI-01): the scales, the components' defaults, and the
// `failed` and `review` colours read at AA (ui-spec §3.4) in the shades Mantine actually uses.
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { DEFAULT_THEME, defaultCssVariablesResolver, mergeMantineTheme, rem } from "@mantine/core";
import { cssVariablesResolver, theme } from "./theme";

// Vitest loads no CSS here, so the stylesheets are read as text (the suite runs from web/).
const appCss = readFileSync("src/app.css", "utf8");
const shellCss = readFileSync("src/shell/shell.css", "utf8");

const merged = mergeMantineTheme(DEFAULT_THEME, theme);
const defaults = defaultCssVariablesResolver(merged);
const ours = cssVariablesResolver(merged);

/** The value a CSS variable resolves to in a scheme, following `var(--x)` chains, as Mantine
 * merges its own resolver with ours (ours wins). */
function resolve(name: string, scheme: "light" | "dark"): string {
  const table = { ...defaults.variables, ...defaults[scheme], ...ours.variables, ...ours[scheme] } as Record<
    string,
    string
  >;
  let value = table[name];
  for (let i = 0; value?.startsWith("var("); i++) {
    if (i > 10) throw new Error(`cycle at ${name}`);
    value = table[value.slice(4, -1).trim()];
  }
  if (!value) throw new Error(`${name} is not defined in the ${scheme} scheme`);
  return value;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const contrast = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

// The backgrounds text sits on: the page and the raised surface (cards, sheets) of each scheme.
const BACKGROUNDS = { light: ["#FFFFFF"], dark: ["#0F1020", "#1D2036"] } as const;

describe.each(["failed", "review"])("the %s colour", (color) => {
  test.each(["light", "dark"] as const)("reads at AA in the %s scheme", (scheme) => {
    // A filled button: its white label on the shade Mantine fills with.
    expect(contrast("#FFFFFF", resolve(`--mantine-color-${color}-filled`, scheme))).toBeGreaterThanOrEqual(4.5);
    // Text (`c="failed"`, an error message): the text shade on each background of the scheme.
    for (const bg of BACKGROUNDS[scheme]) {
      expect(contrast(resolve(`--mantine-color-${color}-text`, scheme), bg)).toBeGreaterThanOrEqual(4.5);
    }
  });

  test("is a ten-shade scale", () => {
    expect(merged.colors[color]).toHaveLength(10);
  });
});

test("the accent is the primary colour", () => {
  expect(merged.primaryColor).toBe("violet");
});

test("the scales are on a 4 px base", () => {
  expect(merged.spacing).toMatchObject({ xs: rem(4), sm: rem(8), md: rem(12), lg: rem(16), xl: rem(24) });
  expect(merged.radius).toMatchObject({ xs: rem(4), sm: rem(8), md: rem(12) });
  expect(merged.defaultRadius).toBe("sm");
  expect(merged.fontSizes).toMatchObject({ xs: rem(12), sm: rem(13), md: rem(14), lg: rem(16), xl: rem(20) });
  expect(merged.headings.fontFamily).toBe("var(--sp-font-display)");
  expect(merged.headings.fontWeight).toBe("600");
  expect(merged.headings.sizes.h1.fontSize).toBe(rem(28));
  expect(merged.headings.sizes.h2.fontSize).toBe(rem(20));
  expect(merged.headings.sizes.h3.fontSize).toBe(rem(16));
});

test("the components' defaults", () => {
  const props = (name: string) => merged.components[name]?.defaultProps;
  expect(props("Button")).toMatchObject({ size: "sm", radius: "sm" });
  expect(props("ActionIcon")).toMatchObject({ variant: "subtle", size: "input-sm" });
  expect(props("Tabs")).toMatchObject({ color: "violet" });
  expect(props("SegmentedControl")).toMatchObject({ color: "violet" });
  expect(props("Anchor")).toMatchObject({ underline: "hover" });
  expect(props("Modal")).toMatchObject({ padding: "lg" });
  for (const name of ["Modal", "Drawer", "Popover", "Menu"]) {
    expect(props(name)).toMatchObject({ radius: "md", shadow: "md" });
  }
  expect(props("Tooltip")).toMatchObject({ withArrow: false });
  expect(props("Input")).toMatchObject({ size: "sm" });
});

test("one global focus ring, which reaches the portals", () => {
  expect(appCss).toMatch(/^:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--sp-line-focus\)/m);
  expect(shellCss).not.toMatch(/\.sp-shell :focus-visible/);
});
