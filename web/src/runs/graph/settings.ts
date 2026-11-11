// The Graph tab's URL state (?tab=graph&level=&layout=&overlay=&show=&q=&node=&fold=&focus=&hide=), so a view of
// the graph can be linked and reloaded; anything unknown falls back to the defaults.
import type { GraphLayout, GraphLevel, GraphOverlay } from "./types";

export const LEVELS: { value: GraphLevel; label: string }[] = [
  { value: "stage", label: "Stages" },
  { value: "subworkflow", label: "Subworkflows" },
  { value: "process", label: "Processes" },
  { value: "jobs", label: "Jobs" },
];
export const LAYOUTS: { value: GraphLayout; label: string }[] = [
  { value: "layered-tb", label: "Layered, top-down" },
  { value: "layered-lr", label: "Layered, left-right" },
  { value: "metro", label: "Metro" },
  { value: "compact", label: "Compact" },
  { value: "upstream", label: "BioFlow-Insight (positions from the code)" },
];
export const OVERLAYS: { value: GraphOverlay; label: string }[] = [
  { value: "state", label: "State" },
  { value: "duration", label: "Duration" },
  { value: "cpu", label: "CPU" },
  { value: "memory", label: "Memory" },
  { value: "failures", label: "Failures" },
  { value: "critical", label: "Critical path" },
];

export interface GraphSettings {
  level: GraphLevel;
  layout: GraphLayout;
  overlay: GraphOverlay;
  show: "map" | "list";
  q: string;
  node: string | null;
  /** Groups folded (Process, Jobs) or unfolded (Subworkflow, Stage) by a double-click. */
  fold: string[];
  /** Only this group's steps are drawn (Show only this group). */
  focus: string | null;
  /** Steps left out of the map and the list; their links are bridged. */
  hide: string[];
}

/** The URL keys that differ from the defaults; `phone` opens on the List. */
export type GraphSearch = Partial<{ level: GraphLevel; layout: GraphLayout; overlay: GraphOverlay; show: "map" | "list"; q: string; node: string; fold: string; focus: string; hide: string }>;

const pick = <T extends string>(list: { value: T }[], v: unknown): T | undefined => list.find((x) => x.value === v)?.value;

export function graphSearch(search: Record<string, unknown>): GraphSearch {
  const out: GraphSearch = {};
  const level = pick(LEVELS, search.level);
  const layout = pick(LAYOUTS, search.layout);
  const overlay = pick(OVERLAYS, search.overlay);
  if (level && level !== "process") out.level = level;
  if (layout && layout !== "layered-tb") out.layout = layout;
  if (overlay && overlay !== "state") out.overlay = overlay;
  if (search.show === "map" || search.show === "list") out.show = search.show;
  if (typeof search.q === "string" && search.q.trim() !== "") out.q = search.q.slice(0, 200);
  if (typeof search.node === "string" && search.node !== "") out.node = search.node.slice(0, 1024);
  if (typeof search.fold === "string" && search.fold !== "") out.fold = search.fold.slice(0, 2000);
  if (typeof search.focus === "string" && search.focus !== "") out.focus = search.focus.slice(0, 1024);
  if (typeof search.hide === "string" && search.hide !== "") out.hide = search.hide.slice(0, 2000);
  return out;
}

export function settingsOf(search: GraphSearch, phone: boolean): GraphSettings {
  return {
    level: search.level ?? "process",
    layout: search.layout ?? "layered-tb",
    overlay: search.overlay ?? "state",
    show: search.show ?? (phone ? "list" : "map"),
    q: search.q ?? "",
    node: search.node ?? null,
    fold: search.fold ? search.fold.split("|").filter(Boolean) : [],
    focus: search.focus ?? null,
    hide: search.hide ? search.hide.split("|").filter(Boolean) : [],
  };
}

/** Settings back to URL keys: the defaults are left out (`phone`: List is the default there). */
export function searchOf(s: GraphSettings, phone: boolean): GraphSearch {
  return graphSearch({ ...s, show: s.show === (phone ? "list" : "map") ? undefined : s.show, node: s.node ?? undefined, fold: s.fold.join("|") || undefined, focus: s.focus ?? undefined, hide: s.hide.join("|") || undefined });
}
