// The Graph tab's URL state (?tab=graph&level=&layout=&overlay=&show=&q=&node=), so a view of
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
  { value: "upstream", label: "Upstream (BioFlow-Insight)" },
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
}

/** The URL keys that differ from the defaults; `phone` opens on the List. */
export type GraphSearch = Partial<{ level: GraphLevel; layout: GraphLayout; overlay: GraphOverlay; show: "map" | "list"; q: string; node: string }>;

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
  };
}

/** Settings back to URL keys: the defaults are left out (`phone`: List is the default there). */
export function searchOf(s: GraphSettings, phone: boolean): GraphSearch {
  return graphSearch({ ...s, show: s.show === (phone ? "list" : "map") ? undefined : s.show, node: s.node ?? undefined });
}
