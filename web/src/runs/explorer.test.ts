// The pure parts of the results explorer (ui-spec §4.4.1, Explorer; FU-P3-85d): the kind of an
// entry, sort with folders first, the filter, the counts, and the view kept in the URL.
import { expect, test } from "vitest";
import type { ResultEntry } from "../api";
import { counts, entryKind, filterEntries, sortEntries } from "./explorer";
import { resultsSearch } from "./ResultsBrowser";

const T1 = "2026-10-31T08:00:00+00:00";
const T2 = "2026-10-31T09:00:00+00:00";
const T3 = "2026-10-31T10:00:00+00:00";
const entry = (name: string, type: ResultEntry["type"], size: number | null, mtime: string | null): ResultEntry => ({ name, type, size, mtime });
const ENTRIES = [
  entry("S10.txt", "file", 300, T1),
  entry("zips", "dir", null, T1),
  entry("latest", "link_outside", null, null),
  entry("S2.txt", "file", 100, T3),
  entry("Alpha", "dir", null, T3),
  entry("b.csv", "file", 200, T2),
];
const names = (list: ResultEntry[]) => list.map((e) => e.name);

test("an entry's kind: Folder, Link outside, else the file kind from its name (unknown names are File)", () => {
  expect(entryKind(entry("x.log", "dir", null, null))).toBe("folder");
  expect(entryKind(entry("x.log", "link_outside", null, null))).toBe("link");
  expect(entryKind(entry("x.LOG", "file", 1, null))).toBe("text");
  expect(entryKind(entry("README", "file", 1, null))).toBe("file");
  expect(entryKind(entry("x.weird", "file", 1, null))).toBe("file");
  expect(entryKind(entry("r.HTM", "file", 1, null))).toBe("html");
});

test("sort by name: folders first, then names in natural order, case-insensitive; -name reverses each group", () => {
  expect(names(sortEntries(ENTRIES, "name"))).toEqual(["Alpha", "zips", "b.csv", "latest", "S2.txt", "S10.txt"]);
  expect(names(sortEntries(ENTRIES, "-name"))).toEqual(["zips", "Alpha", "S10.txt", "S2.txt", "latest", "b.csv"]);
});

test("sort by size and modified: folders stay first, an unknown value last either way, ties by name", () => {
  expect(names(sortEntries(ENTRIES, "size"))).toEqual(["Alpha", "zips", "S2.txt", "b.csv", "S10.txt", "latest"]);
  expect(names(sortEntries(ENTRIES, "-size"))).toEqual(["Alpha", "zips", "S10.txt", "b.csv", "S2.txt", "latest"]);
  expect(names(sortEntries(ENTRIES, "mtime"))).toEqual(["zips", "Alpha", "S10.txt", "b.csv", "S2.txt", "latest"]);
  expect(names(sortEntries(ENTRIES, "-mtime"))).toEqual(["Alpha", "zips", "S2.txt", "b.csv", "S10.txt", "latest"]);
});

test("sorting does not change the listing it is given", () => {
  const copy = [...ENTRIES];
  sortEntries(ENTRIES, "-size");
  expect(ENTRIES).toEqual(copy);
});

test("the filter keeps names that contain the text, case-insensitive; an empty filter keeps all", () => {
  expect(names(filterEntries(ENTRIES, "S"))).toEqual(["S10.txt", "zips", "latest", "S2.txt", "b.csv"]);
  expect(names(filterEntries(ENTRIES, ".TXT"))).toEqual(["S10.txt", "S2.txt"]);
  expect(filterEntries(ENTRIES, "")).toEqual(ENTRIES);
  expect(filterEntries(ENTRIES, "nothing")).toEqual([]);
});

test("the card's counts are of the entries listed: folders, and every other entry as a file", () => {
  expect(counts(ENTRIES)).toBe("2 folders, 4 files");
  expect(counts([entry("a", "dir", null, null), entry("b", "file", 1, null)])).toBe("1 folder, 1 file");
  expect(counts([])).toBe("0 folders, 0 files");
});

test("the URL keeps the folder, the sort, the filter, the row to focus and the task to return to", () => {
  expect(resultsSearch({})).toEqual({});
  expect(resultsSearch({ path: "fastqc", sort: "-size", q: "html", focus: "a.html" })).toEqual({ path: "fastqc", sort: "-size", q: "html", focus: "a.html" });
  // name is the default sort, never written; an unknown sort is dropped
  expect(resultsSearch({ sort: "name" })).toEqual({});
  expect(resultsSearch({ sort: "type" })).toEqual({});
  // the task and attempt a Preview of the sheet's Outputs returns to (ui-spec §4.4.1)
  expect(resultsSearch({ path: "a.txt", task: "tsk_01JBC6Q4ZK7M8N2P3R5S7T9V1W", attempt: 2 })).toEqual({ path: "a.txt", task: "tsk_01JBC6Q4ZK7M8N2P3R5S7T9V1W", attempt: 2 });
  expect(resultsSearch({ task: "tsk_1", attempt: "3" })).toEqual({ task: "tsk_1", attempt: 3 });
  // a task needs its attempt, and both must look like the API's
  expect(resultsSearch({ task: "tsk_1" })).toEqual({});
  expect(resultsSearch({ task: "../x", attempt: 1 })).toEqual({});
  expect(resultsSearch({ task: "tsk_1", attempt: 0 })).toEqual({});
  expect(resultsSearch({ task: "tsk_1", attempt: "1e3" })).toEqual({});
});

test("a filter or focus with a control, bidi or format character, or a focus with a slash, is dropped (SEC-P3T32B-02)", () => {
  expect(resultsSearch({ q: "a‮b" })).toEqual({});
  expect(resultsSearch({ q: "a\nb" })).toEqual({});
  expect(resultsSearch({ q: "x".repeat(201) })).toEqual({});
  expect(resultsSearch({ focus: "a‏b" })).toEqual({});
  expect(resultsSearch({ focus: "a/b" })).toEqual({});
  expect(resultsSearch({ focus: ".." })).toEqual({});
});
