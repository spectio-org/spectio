// The pure parts of the results explorer (ui-spec §4.4.1, Explorer; FU-P3-85d; boards LiteResults,
// MLiteResults, LiteKind): an entry's kind, the sort with folders first, the filter and the counts.
// They work on the listing the server gave (at most 1,000 entries), so they are plain array work.
import type { ResultEntry } from "../api";
import { type Kind, fileKind } from "./preview";

export const SORTS = ["name", "-name", "size", "-size", "mtime", "-mtime"] as const;
export type Sort = (typeof SORTS)[number];
export type EntryKind = Kind | "folder" | "link";

/** Folder, Link outside, or the kind of a file from its name (preview.ts, one list for all). */
export const entryKind = (entry: Pick<ResultEntry, "name" | "type">): EntryKind =>
  entry.type === "dir" ? "folder" : entry.type === "link_outside" ? "link" : fileKind(entry.name);

// natural order (S2 before S10), case-insensitive
const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });
const byName = (a: ResultEntry, b: ResultEntry) => collator.compare(a.name, b.name) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);

/** The entries in `sort` order: folders first in every sort; an unknown size or time last in both
 * directions; ties by name. */
export function sortEntries(entries: ResultEntry[], sort: Sort): ResultEntry[] {
  const down = sort.startsWith("-");
  const key = sort.replace("-", "") as "name" | "size" | "mtime";
  const value = (e: ResultEntry) => (key === "size" ? e.size : e.mtime ? Date.parse(e.mtime) : null);
  return [...entries].sort((a, b) => {
    const folders = Number(b.type === "dir") - Number(a.type === "dir");
    if (folders) return folders;
    if (key === "name") return down ? byName(b, a) : byName(a, b);
    const [x, y] = [value(a), value(b)];
    if (x === null || y === null) return x === y ? byName(a, b) : x === null ? 1 : -1;
    return (down ? y - x : x - y) || byName(a, b);
  });
}

/** The entries whose name contains `q`, case-insensitive; all of them for an empty `q`. */
export function filterEntries(entries: ResultEntry[], q: string): ResultEntry[] {
  const text = q.toLowerCase();
  return text ? entries.filter((e) => e.name.toLowerCase().includes(text)) : entries;
}

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

/** "2 folders, 7 files": the entries listed, every entry that is not a folder counted as a file. */
export function counts(entries: ResultEntry[]): string {
  const folders = entries.filter((e) => e.type === "dir").length;
  return `${plural(folders, "folder")}, ${plural(entries.length - folders, "file")}`;
}

const TASK_ID = /^tsk_[0-9A-Za-z]{1,64}$/;

/** `&task=<id>&attempt=<n>`, the task sheet a run's URL reopens (ui-spec §4.4.1, Back to the task
 * sheet): both or neither, each shaped as the API's. */
export function taskSearch(search: Record<string, unknown>): { task?: string; attempt?: number } {
  const { task, attempt } = search;
  const n = typeof attempt === "number" ? attempt : typeof attempt === "string" && /^[1-9][0-9]{0,3}$/.test(attempt) ? Number(attempt) : NaN;
  return typeof task === "string" && TASK_ID.test(task) && Number.isInteger(n) && n >= 1 && n <= 9999 ? { task, attempt: n } : {};
}
