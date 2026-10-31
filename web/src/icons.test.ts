import { expect, test } from "vitest";
import { ICONS, groupIcon } from "./icons";

test("SEC-P3PARB-02: a group icon name is looked up in the map's own keys only", () => {
  expect(groupIcon("fas fa-constructor")).toBe(ICONS.sliders);
  expect(groupIcon("fas fa-tostring")).toBe(ICONS.sliders);
  expect(groupIcon("fas fa-dna")).toBe(ICONS.dna);
  expect(groupIcon(null)).toBe(ICONS.sliders);
});
