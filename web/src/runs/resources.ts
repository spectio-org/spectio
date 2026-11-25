import type { Resources } from "../api";
import { formatDuration } from "./stateWord";

// Resources per job as words (ui-spec §4.4 note 2026-10-28, Resources; P1 Tasks 29 and 32): sizes
// in powers of 1024 written GB and MB, as Nextflow writes them; "—" for a value not known yet.

const UNITS = ["B", "KB", "MB", "GB", "TB"];

/** "512 B", "3 KB", then one fixed decimal from MB up ("2.5 MB", "8.0 GB"); "—" when unknown. */
export function bytes(n: number | null): string {
  if (n === null) return "—";
  let value = n;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit >= 2 || !Number.isInteger(value) ? value.toFixed(1) : value} ${UNITS[unit]}`;
}

/** A peak above 90 % of the memory asked, or a duration above 90 % of the time limit. */
export function nearLimit(r: Resources): { memory: boolean; time: boolean } {
  const over = (used: number | null, asked: number | null) => used !== null && asked !== null && asked > 0 && used > 0.9 * asked;
  return { memory: over(r.peak_rss_bytes, r.memory_bytes), time: over(r.realtime_s, r.time_s) };
}

/** The phone's one line per job: "asked 8 GB · peak 8.0 GB · limit 8 h". */
export function resourcesLine(r: Resources): string {
  const near = nearLimit(r);
  return [
    `asked ${bytes(r.memory_bytes)}`,
    `peak ${bytes(r.peak_rss_bytes)}${near.memory ? ", near limit" : ""}`,
    `limit ${formatDuration(r.time_s)}${near.time ? ", near limit" : ""}`,
  ].join(" · ");
}

/** A ratio as a percentage: 0.63 → "63 %"; "—" when unknown. */
export const percent = (ratio: number | null | undefined): string => (ratio == null ? "—" : `${Math.round(ratio * 100)} %`);

/** Efficiency under 25 % reads "low" (ui-spec §4.4 note 2026-11-07); memory above 90 % "near limit". */
export const isLow = (ratio: number | null | undefined): boolean => ratio != null && ratio < 0.25;
export const isNear = (ratio: number | null | undefined): boolean => ratio != null && ratio > 0.9;
