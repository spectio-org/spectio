import { expect, test } from "vitest";

// ui-spec §12.4 and §12.9 (UI-13, UI-18): Launch and the confirmation dialogs use the theme's
// `failed` colour, never Mantine's default red, and buttons are sm (no xs outside dense rows).
const sources = import.meta.glob(["./*.tsx", "!./*.test.tsx", "../runs/DeleteRuns.tsx", "../runs/ResumeDialog.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

// The tag body may hold an arrow prop's `=>` before size="xs" (CR-P3UI13-05).
const XS_BUTTON = /<Button\b(?:[^>]|=>)*?\bsize="xs"/g;

test("the xs-button guard sees through an arrow prop", () => {
  expect('<Button onClick={() => x} size="xs">'.match(XS_BUTTON)).toHaveLength(1);
  expect('<Button size="sm">Go</Button> <Text size="xs">'.match(XS_BUTTON)).toBeNull();
});

test("no Mantine red and no xs button in Launch and the confirmation dialogs", () => {
  expect(Object.keys(sources).length).toBeGreaterThan(5);
  for (const [file, text] of Object.entries(sources)) {
    expect([file, text.match(/\b(c|color)="red"/g)]).toEqual([file, null]);
    expect([file, text.match(XS_BUTTON)]).toEqual([file, null]);
  }
});

test("every dialog title in Launch and the confirmation dialogs is sp-sheet-title (CR-P3UI13-06)", () => {
  for (const [file, text] of Object.entries(sources)) {
    const tags = text.match(/<(?:Modal|Modal\.Title|Drawer|Drawer\.Title)\s(?:[^>]|=>)*>/g) ?? [];
    expect([file, tags.filter((tag) => !tag.includes("sp-sheet-title"))]).toEqual([file, []]);
  }
});
