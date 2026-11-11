import { expect, test } from "vitest";
import { graphSearch, searchOf, settingsOf } from "./settings";

test("unknown or default values drop out of the URL", () => {
  expect(graphSearch({ level: "process", layout: "nope", overlay: "state", q: "  ", show: "x" })).toEqual({});
  expect(graphSearch({ level: "stage", layout: "metro", overlay: "critical", q: "bwa", show: "list", node: "A:B" })).toEqual({
    level: "stage",
    layout: "metro",
    overlay: "critical",
    q: "bwa",
    show: "list",
    node: "A:B",
  });
});

test("the phone opens on the List; the desktop on the map", () => {
  expect(settingsOf({}, true).show).toBe("list");
  expect(settingsOf({}, false).show).toBe("map");
  expect(settingsOf({ show: "map" }, true).show).toBe("map");
});

test("settings round-trip through the URL", () => {
  const s = settingsOf({ level: "jobs", q: "x" }, false);
  expect(searchOf(s, false)).toEqual({ level: "jobs", q: "x" });
  expect(searchOf({ ...s, show: "list" }, false)).toEqual({ level: "jobs", q: "x", show: "list" });
  expect(searchOf({ ...s, show: "list" }, true)).toEqual({ level: "jobs", q: "x" });
});
