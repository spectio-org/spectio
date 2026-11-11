// The flat view of an OME-Zarr (FU-P3-102i; ui-spec §4.4.1, the flat view and Phone), on a phone
// and without WebGL 2: one plane (channel 1, z 1, t 1) of one level, read with zarrita alone
// through our checked store (zarr.ts: the same caps, budget and decoder workers as the WebGL
// viewer), then drawn as the TIFF's flat view draws it. No Viv, no WebGL; FilePreview imports it
// lazily, so zarrita and the decoders stay out of the main bundle.
import * as zarr from "zarrita";
import { BUDGET } from "./client";
import { type Flat, PHONE_SIDE_MAX, PLANE_MAX, toRgba } from "./flat";
import { TooLarge } from "./walk";
import { type Decode, ZarrStore, openZarr } from "./zarr";

export { inWorkers } from "./zarr";

/** The plane of the largest level that fits: both sides at most 2,048 px on a phone, at most
 * 50 megapixels elsewhere; null on a phone when no level is that small. */
export async function readZarrFlat(urlOf: (key: string) => string, work: boolean, phone: boolean, decode: Decode, signal?: AbortSignal): Promise<Flat | null> {
  const store = new ZarrStore(urlOf, decode, signal);
  store.work = work;
  const { labels, levels } = await openZarr(store);
  const area = (shape: number[]) => shape.at(-1)! * shape.at(-2)!;
  const fits = (shape: number[]) => (phone ? shape.slice(-2).every((side) => side <= PHONE_SIDE_MAX) : area(shape) <= PLANE_MAX);
  const level = levels.filter((l) => fits(l.shape)).sort((a, b) => area(b.shape) - area(a.shape))[0];
  if (!level && phone) return null;
  if (!level) throw new TooLarge("a plane over 50 megapixels");
  const array = await zarr.open.v2(zarr.root(store).resolve(level.path), { kind: "array", attrs: false });
  // zarrita starts one read per chunk at once: refuse a plane of more chunks than the request budget
  // before any is started (SEC-P3FU102I-01; dev-env §15.3 req. 19)
  const [cy, cx] = array.chunks.slice(-2);
  if (Math.ceil(level.shape.at(-2)! / cy) * Math.ceil(level.shape.at(-1)! / cx) > BUDGET.requests) throw new TooLarge("a plane over 2,000 Zarr chunks");
  const { data, shape } = await zarr.get(array, labels.map((axis) => (axis === "y" || axis === "x" ? null : 0)));
  const [height, width] = shape;
  const values = data as ArrayLike<number>;
  // unsigned 8-bit is drawn as it is; any other type is stretched from its percentiles
  const flat = toRgba(width, height, [values], data instanceof Uint8Array ? { bits: 8, format: 1 } : { bits: 16, format: 1 });
  const full = levels[0].shape;
  return { width, height, full: [full.at(-1)!, full.at(-2)!], pages: 1, noOme: false, ...flat };
}
