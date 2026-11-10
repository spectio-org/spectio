// The flat view of a TIFF (FU-P3-102d3; ui-spec §4.4.1, imaging): which IFD is shown, the caps
// checked before its tiles are read, the plane as RGBA for a 2D canvas (grey, RGB, a percentile
// stretch), and each error as the state of the boards (LiteImageViewerStates, MLiteImageViewer).
import { ApiError } from "../../api";
import { MIB } from "../preview";
import { Answered, BUDGET, Stopped, openTiff, reading } from "./client";
import { ALLOWED } from "./decode";
import type { DecoderPool } from "./pool";
import { TooLarge, Unreadable, omeFiles, walkIfds, type FileDirectory } from "./walk";

export const PLANE_MAX = 50_000_000;
export const PHONE_SIDE_MAX = 2048;
const BINS = 4096;

/** Shown in the viewer's place, as its title says; not a problem of the file page. */
export class Unsupported extends Error {}

// TIFF 6.0 section 3 and 22 (2, 3, 4, 6); geotiff 2.1.3 `compression/index.js:28,35` (LERC, WebP);
// JPEG 2000 as libtiff numbers it **[to be validated]**.
const COMPRESSIONS: Record<number, string> = { 2: "CCITT RLE", 3: "CCITT Group 3", 4: "CCITT Group 4", 6: "old-style JPEG", 34712: "JPEG 2000", 34887: "LERC", 50001: "WebP" };

const side = (fd: FileDirectory) => [Number(fd.ImageWidth), Number(fd.ImageLength)];
const reduced = (fd: FileDirectory) => (Number(fd.NewSubfileType ?? 0) & 1) === 1;

/** The pages of a TIFF: its IFDs, reduced-resolution levels aside. */
export const pages = (ifds: FileDirectory[]) => ifds.filter((fd) => !reduced(fd)).length;

/** The first IFD; on a phone, the largest of it and the reduced levels right after it whose
 * sides are both at most 2,048 px, or null when none is that small. */
export function shownLevel(ifds: FileDirectory[], phone: boolean): FileDirectory | null {
  if (!phone) return ifds[0];
  const levels = [ifds[0]];
  for (let i = 1; i < ifds.length && reduced(ifds[i]); i++) levels.push(ifds[i]);
  const fits = levels.filter((fd) => side(fd).every((s) => s <= PHONE_SIDE_MAX));
  return fits.sort((a, b) => side(b)[0] * side(b)[1] - side(a)[0] * side(a)[1])[0] ?? null;
}

/** The shown plane's caps, before any of its tiles is read. */
export function checkPlane(fd: FileDirectory) {
  const [w, h] = side(fd);
  if (w * h > PLANE_MAX) throw new TooLarge("a plane over 50 megapixels");
  const code = Number(fd.Compression ?? 1);
  if (!ALLOWED.has(code)) throw new Unsupported(COMPRESSIONS[code] ? `Spectio cannot decode ${COMPRESSIONS[code]} compression.` : `Spectio cannot decode compression ${code}.`);
}

/** The 0.1 and 99.9 percentiles of the values (NaN and infinities skipped), to a 4,096th of their span. */
export function percentiles(values: ArrayLike<number>, lo = 0.001, hi = 0.999): [number, number] {
  let [min, max, n] = [Infinity, -Infinity, 0];
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (!Number.isFinite(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
    n++;
  }
  if (!(max > min)) return n ? [min, max] : [0, 0];
  const width = (max - min) / BINS;
  const counts = new Uint32Array(BINS);
  for (let i = 0; i < values.length; i++) if (Number.isFinite(values[i])) counts[Math.min(BINS - 1, Math.floor((values[i] - min) / width))]++;
  let [low, high, seen] = [min, max, 0];
  for (let b = 0, found = false; b < BINS; b++) {
    seen += counts[b];
    if (!found && seen > lo * n) [low, found] = [min + b * width, true];
    if (seen >= hi * n) {
      high = min + (b + 1) * width;
      break;
    }
  }
  return [low, Math.min(high, max)];
}

/** The plane as RGBA: three 8-bit samples as RGB, else the first sample in grey; anything but
 * unsigned 8-bit is stretched from its percentiles. */
export function toRgba(width: number, height: number, samples: ArrayLike<number>[], { bits, format }: { bits: number; format: number }) {
  const stretched = bits !== 8 || format !== 1;
  const rgb = samples.length === 3 && !stretched;
  const [low, high] = stretched ? percentiles(samples[0]) : [0, 255];
  const scale = high > low ? 255 / (high - low) : 0;
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < width * height; i++) {
    for (let c = 0; c < 3; c++) {
      const v = samples[rgb ? c : 0][i];
      rgba[i * 4 + c] = stretched ? (v - low) * scale : v; // NaN clamps to 0
    }
    rgba[i * 4 + 3] = 255;
  }
  return { rgba, stretched, note: rgb || samples.length === 1 ? null : `Shown: sample 1 of ${samples.length}` };
}

export interface ImageState {
  title: string;
  download: boolean;
  action?: "retry" | "reload";
  status?: boolean; // the status line (role="status"), not a note
}

const tooLarge = (reason: string): ImageState => ({ title: `This image is too large to show here (${reason}). Download it to open it.`, download: true });
const unreadable = (why: string): ImageState => ({ title: `Not an image Spectio can read: ${why}`, download: true, action: "retry" });

/** An error of the open, the walk or the read, as its state; 404, 409, 410, 503 and any other
 * answer are the file page's own problems. */
export function imageState(err: unknown): ImageState | { problem: ApiError } {
  if (err instanceof TooLarge) return tooLarge(err.reason);
  if (err instanceof Unsupported) return { title: err.message, download: true };
  if (err instanceof Unreadable) return unreadable(err.message);
  if (err instanceof Stopped) {
    const spent = err.limit === "requests" ? `${BUDGET.requests.toLocaleString("en-US")} reads` : `${BUDGET.bytes / MIB} MiB read`;
    return { title: `Spectio stopped reading tiles: ${spent}.`, action: "reload", status: true, download: false };
  }
  if (err instanceof Answered) {
    if (err.status === 413) return tooLarge("over 1 GiB");
    if (err.status === 422) return err.detail === "not the TIFF its name says" ? { title: "This file is not the TIFF its name says.", download: true, action: "retry" } : unreadable(err.detail ?? "the server refused it");
    if (err.status !== 206) return { problem: new ApiError(err.status, err.detail ?? "") };
  }
  return { title: "This image could not be decoded.", download: true, action: "retry" };
}

export interface Flat {
  width: number;
  height: number;
  full: number[]; // the first IFD's width and height
  pages: number;
  noOme: boolean; // an OME-TIFF's name, no OME-XML: shown as a TIFF
  rgba: Uint8ClampedArray;
  stretched: boolean;
  note: string | null;
}

/** The TIFF at `url` opened and its IFDs walked; an OME-TIFF that names other files is refused. */
export async function openWalked(url: string, size: number, name: string, ome: boolean, signal: AbortSignal) {
  const { tiff, client } = await openTiff(url, size, signal);
  const { ifds, offsets, values } = await walkIfds(tiff, client);
  if (!ifds.length) throw new Unreadable("no image in the file");
  const files = ome ? omeFiles(ifds[0].ImageDescription, name) : "none";
  if (files === "others") throw new Unsupported("This OME-TIFF names other files: Spectio shows one file at a time.");
  if (files === "too-large") throw new TooLarge("OME-XML over 4 MiB");
  return { tiff, client, ifds, files, walked: { offsets, values } };
}

/** The shown plane of the TIFF at `url` (the raw route with `as=tiff`), opened, walked and read
 * through the pinned client and our decoder pool; null on a phone when no level is small enough. */
export async function readFlat(url: string, size: number, name: string, ome: boolean, phone: boolean, pool: DecoderPool, signal: AbortSignal): Promise<Flat | null> {
  const { tiff, client, ifds, files } = await openWalked(url, size, name, ome, signal);
  const fd = shownLevel(ifds, phone);
  if (!fd) return null;
  checkPlane(fd);
  const image = await reading(client, () => tiff.getImage(ifds.indexOf(fd)));
  const rasters = await reading(client, () => image.readRasters({ pool: pool as never, signal }));
  const [width, height] = [image.getWidth(), image.getHeight()];
  const samples = rasters as unknown as ArrayLike<number>[];
  const flat = toRgba(width, height, samples, { bits: image.getBitsPerSample(0), format: Number(image.getSampleFormat(0) ?? 1) });
  return { width, height, full: side(ifds[0]), pages: pages(ifds), noOme: ome && files === "none", ...flat };
}
