import type { Resources } from "../api";

// Resources per job as words (ui-spec §4.4 note 2026-10-28, Resources; P1 Tasks 29 and 32): sizes
// in powers of 1024 written GB and MB, as Nextflow writes them; "—" for a value not known yet.

const UNITS = ["B", "KB", "MB", "GB", "TB"];

/** "8 GB", "8.0 GB" (not a whole number of GB), "512 B"; "—" when unknown. */
export function bytes(n: number | null): string {
  if (n === null) return "—";
  let value = n;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${Number.isInteger(value) ? value : value.toFixed(1)} ${UNITS[unit]}`;
}

/** "41 s", "6 min", "4 h", "1 h 12"; "—" when unknown. */
export function seconds(s: number | null): string {
  if (s === null) return "—";
  if (s < 60) return `${Math.round(s)} s`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} min`;
  const rest = minutes % 60;
  return rest ? `${Math.floor(minutes / 60)} h ${String(rest).padStart(2, "0")}` : `${minutes / 60} h`;
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
    `limit ${seconds(r.time_s)}${near.time ? ", near limit" : ""}`,
  ].join(" · ");
}
