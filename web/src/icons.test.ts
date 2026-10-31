import { expect, test } from "vitest";
import { ICONS, groupIcon } from "./icons";

test("SEC-P3PARB-02: a group icon name is looked up in the map's own keys only", () => {
  expect(groupIcon("fas fa-constructor")).toBe(ICONS.sliders);
  expect(groupIcon("fas fa-dna")).toBe(ICONS.dna);
  expect(groupIcon(null)).toBe(ICONS.sliders);
});

test("P3-parC: the board's group icons for filtering, tags, checks and institutions", () => {
  expect(groupIcon("fas fa-filter")).toBe(ICONS.filter);
  expect(groupIcon("fas fa-tags")).toBe(ICONS.tag);
  expect(groupIcon("fas fa-shield-alt")).toBe(ICONS.shield);
  expect(groupIcon("fas fa-university")).toBe(ICONS.building);
});

test("P3-parD: every group icon of the synthetic pipelines' schemas is drawn, failure injection as a warning", () => {
  expect(groupIcon("fas fa-exclamation-triangle")).toBe(ICONS.alert);
  expect(groupIcon("fas fa-bug")).toBe(ICONS.alert);
  expect(groupIcon("fas fa-terminal")).toBe(ICONS.terminal);
  expect(groupIcon("fas fa-microchip")).toBe(ICONS.server);
});
