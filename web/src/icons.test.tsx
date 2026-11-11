import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { ICONS, Icon, groupIcon, iconSvg } from "./icons";

test("SEC-P3PARB-02: a group icon name is looked up in the map's own keys only", () => {
  expect(groupIcon("fas fa-constructor")).toBe("sliders");
  expect(groupIcon("fas fa-dna")).toBe("dna");
  expect(groupIcon(null)).toBe("sliders");
});

test("P3-parC: the board's group icons for filtering, tags, checks and institutions", () => {
  expect(groupIcon("fas fa-filter")).toBe("filter");
  expect(groupIcon("fas fa-tags")).toBe("tag");
  expect(groupIcon("fas fa-shield-alt")).toBe("shield");
  expect(groupIcon("fas fa-university")).toBe("building");
});

test("P3-parD: every group icon of the synthetic pipelines' schemas is drawn, failure injection as a warning", () => {
  expect(groupIcon("fas fa-exclamation-triangle")).toBe("alert");
  expect(groupIcon("fas fa-bug")).toBe("alert");
  expect(groupIcon("fas fa-terminal")).toBe("terminal");
  expect(groupIcon("fas fa-microchip")).toBe("server");
});

test("UI-02: four sizes (inline 16, button 16, nav 20, tile 24), one stroke, decorative by default", () => {
  const { container } = render(
    <>
      <Icon name="copy" size="inline" />
      <Icon name="copy" size="button" />
      <Icon name="home" size="nav" />
      <Icon name="home" size="tile" />
    </>,
  );
  const svgs = [...container.querySelectorAll("svg")];
  expect(svgs.map((s) => s.getAttribute("width"))).toEqual(["16", "16", "20", "24"]);
  for (const s of svgs) {
    expect(s).toHaveAttribute("stroke-width", "1.75");
    expect(s).toHaveAttribute("aria-hidden", "true");
    expect(s).not.toHaveAttribute("role");
  }
  expect(svgs[0].querySelector("path")).toHaveAttribute("d", ICONS.copy);
});

test("UI-02: a label makes the icon an image with that accessible name", () => {
  const { getByRole } = render(<Icon name="bell" size="nav" label="Notifications" />);
  const img = getByRole("img", { name: "Notifications" });
  expect(img).not.toHaveAttribute("aria-hidden");
});

test("UI-02: the markup for a string-only host (AG Grid) is the same icon", () => {
  expect(iconSvg("filter", "inline")).toContain(`d="${ICONS.filter}"`);
  expect(iconSvg("filter", "inline")).toContain('stroke-width="1.75"');
  expect(iconSvg("filter", "inline")).toContain('width="16"');
});

// Every icon path and stroke lives in icons.tsx (ui-audit D). The only other drawings allowed are
// brand marks, listed here by file and reason; the engine marks are PNGs and charts are HTML.
const EXCEPTIONS: Record<string, string> = {
  "./shell/TopBar.tsx": "the Spectio logo (SpectioMark), four filled brand paths",
};
const sources = import.meta.glob(["./**/*.{ts,tsx}", "!./**/*.test.{ts,tsx}", "!./icons.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

// What a brand mark may draw (an <svg> of filled <path d=…>) and what no file but icons.tsx may hold:
// a stroke width, an <Icon path=…> or a path string ("M12 21…") outside a d= attribute.
const BRAND = [/<svg\b/, /<path\b[^>]*\bd=/];
const ICON_ONLY = [/strokeWidth|stroke-width/, /<Icon\b[^>]*\bpath=/, /(?<!d=)["'`]M-?\d+(\.\d+)?[ ,]-?\d/];

test("UI-02: no icon path or stroke is drawn outside icons.tsx", () => {
  expect(Object.keys(sources).length).toBeGreaterThan(50);
  const offenders = Object.entries(sources).flatMap(([file, text]) => {
    const rules = file in EXCEPTIONS ? ICON_ONLY : [...BRAND, ...ICON_ONLY];
    return rules.filter((re) => re.test(text)).map((re) => `${file}: ${re}`);
  });
  expect(offenders).toEqual([]);
});

test("UI-02: the brand-mark exceptions still exist (a stale entry is removed)", () => {
  for (const file of Object.keys(EXCEPTIONS)) expect(sources[file]).toMatch(/<path\b[^>]*\bd=/);
});
