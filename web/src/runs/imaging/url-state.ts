// The OME-TIFF viewer's view in the URL (FU-P3-102f; ui-spec §4.4.1 "The URL keeps the view"):
// `&z=` and `&t=` (1-based), `&ch=` (the channels on, 0-based), `&zoom=`, `&x=` and `&y=` (the
// view's centre, in pixels of the full image). Read once when the viewer opens, written with a
// history replace so Back is not flooded. A value out of range is dropped and the default used.
import type { ViewState } from "./viv";

export type UrlView = { z: number; t: number; ch: number[] | null; view: ViewState | null };
type Sizes = { x: number; y: number; z: number; t: number; c: number };
const KEYS = new Set(["z", "t", "ch", "zoom", "x", "y"]);
export const ZOOM = { min: -12, max: 6 }; // the viewer's zoom range
export const CHANNELS_ON = 6; // at most 6 channels on at once (Viv draws up to 10)

/** A whole number of at most 9 digits, else NaN: "1e3", "0x2", "1.5" and "-3" are not one. */
const int = (s: string | null) => (s !== null && /^\d{1,9}$/.test(s) ? Number(s) : NaN);
const num = (s: string | null) => (s !== null && s.trim() !== "" ? Number(s) : NaN);

function params(search: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const pair of search.replace(/^\?/, "").split("&")) {
    const [k, v = ""] = pair.split("=", 2);
    try {
      if (KEYS.has(k)) out.set(k, decodeURIComponent(v));
    } catch {
      // a broken escape (%ZZ) is no value
    }
  }
  return out;
}

export function parseView(search: string, sizes: Sizes): UrlView {
  const p = params(search);
  const plane = (key: "z" | "t") => {
    const n = int(p.get(key) ?? null);
    return n >= 1 && n <= sizes[key] ? n - 1 : 0;
  };
  let ch: number[] | null = null;
  const listed = p.get("ch");
  if (listed === "") ch = [];
  else if (listed !== undefined) {
    const known = [...new Set(listed.split(",").map(int))].filter((c) => c < sizes.c); // NaN is never below
    ch = known.length ? known.slice(0, CHANNELS_ON) : null;
  }
  const [zoom, x, y] = [num(p.get("zoom") ?? null), num(p.get("x") ?? null), num(p.get("y") ?? null)];
  const fits = zoom >= ZOOM.min && zoom <= ZOOM.max && x >= 0 && x <= sizes.x && y >= 0 && y <= sizes.y;
  return { z: plane("z"), t: plane("t"), ch, view: fits ? { zoom, target: [x, y, 0] } : null };
}

/** `search` with the view's parameters replaced and every other one kept as it was written. */
export function serialiseView(search: string, { z, t, ch, view }: UrlView): string {
  const kept = search.replace(/^\?/, "").split("&").filter((pair) => pair && !KEYS.has(pair.split("=")[0]));
  const ours = [`z=${z + 1}`, `t=${t + 1}`];
  if (ch) ours.push(`ch=${ch.join(",")}`);
  if (view) ours.push(`zoom=${Math.round(view.zoom * 100) / 100}`, `x=${Math.round(view.target[0])}`, `y=${Math.round(view.target[1])}`);
  return `?${[...kept, ...ours].join("&")}`;
}

/** The view into the address bar, replacing the entry (the router's state is kept). Browsers
 * throttle replaceState, so the caller writes after a pause, and a refusal is ignored. */
export function writeView(view: UrlView) {
  try {
    const { pathname, search, hash } = window.location;
    window.history.replaceState(window.history.state, "", `${pathname}${serialiseView(search, view)}${hash}`);
  } catch {
    // throttled: the next write carries the view
  }
}
