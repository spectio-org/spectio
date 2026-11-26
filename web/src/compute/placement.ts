// The placement picker's rules (#401): which partitions of `GET /cluster/facts` fit a need, and
// the constraint and GRES a choice fills. Pure, so the picker's component only draws.
import type { ClusterFacts } from "../api";

export type Partition = ClusterFacts["partitions"][number];
export type NodeGroup = Partition["groups"][number];

/** What the user needs: `gpu` is "none" (no GPU needed, no filter), "any" or a type; empty strings and lists mean no filter. */
export interface Need {
  gpu: string;
  memGb: string;
  hours: string;
  features: string[];
}
export const NO_NEED: Need = { gpu: "none", memGb: "", hours: "", features: [] };

const MIB_PER_GB = 1024;
const positive = (text: string) => (/^\d+(\.\d+)?$/.test(text.trim()) ? Number(text) : 0);

/** The GPU types the facts name, sorted; an untyped GPU is only "any". */
export const gpuTypes = (facts: ClusterFacts): string[] =>
  [...new Set(facts.partitions.flatMap((p) => p.groups.flatMap((g) => g.gpus.map((x) => x.type))))]
    .filter((t): t is string => !!t)
    .sort();

/** The union of the nodes' features, sorted. */
export const featureUnion = (facts: ClusterFacts): string[] =>
  [...new Set(facts.partitions.flatMap((p) => p.groups.flatMap((g) => g.features)))].sort();

const fits = (g: NodeGroup, need: Need): boolean => {
  if (need.gpu === "any" && g.gpus.length === 0) return false;
  if (need.gpu !== "none" && need.gpu !== "any" && !g.gpus.some((x) => x.type === need.gpu)) return false;
  if (g.mem_mib < positive(need.memGb) * MIB_PER_GB) return false;
  return need.features.every((f) => g.features.includes(f));
};

/** The node groups of `p` that fit `need`: the one group must satisfy every filter. The time
 * filter belongs to the partition (`max_time_min` null is unlimited). */
export const fittingGroups = (p: Partition, need: Need): NodeGroup[] =>
  p.max_time_min !== null && p.max_time_min < positive(need.hours) * 60 ? [] : p.groups.filter((g) => fits(g, need));

/** The constraint a choice fills: the features, joined with `&`; null when none is chosen. */
export const constraintOf = (need: Need): string | null => (need.features.length ? need.features.join("&") : null);

/** The GRES a choice fills: `gpu:<type>:1`, `gpu:1` for any; null for no GPU filter. */
export const gresOf = (need: Need): string | null =>
  need.gpu === "none" ? null : need.gpu === "any" ? "gpu:1" : `gpu:${need.gpu}:1`;
