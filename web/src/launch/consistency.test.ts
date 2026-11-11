import { expect, test } from "vitest";

// ui-spec §12.4 and §12.9 (UI-13, UI-18): Launch and the confirmation dialogs use the theme's
// `failed` colour, never Mantine's default red, and buttons are sm (no xs outside dense rows).
const sources = import.meta.glob(["./*.tsx", "!./*.test.tsx", "../runs/DeleteRuns.tsx", "../runs/ResumeDialog.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

test("no Mantine red and no xs button in Launch and the confirmation dialogs", () => {
  expect(Object.keys(sources).length).toBeGreaterThan(5);
  for (const [file, text] of Object.entries(sources)) {
    expect([file, text.match(/\b(c|color)="red"/g)]).toEqual([file, null]);
    expect([file, text.match(/<Button\b[^>]*\bsize="xs"/g)]).toEqual([file, null]);
  }
});
