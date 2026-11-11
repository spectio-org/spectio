// The page's own Zarr store (FU-P3-102g; api §5.3.1, dev-env §15.3 req. 19 Malicious Zarr), given
// to Viv's `loadOmeZarrFromStore` (@vivjs/loaders 0.23.0 `dist/index.mjs:1256-1263`) with the
// `get` of @zarrita/storage's interface. Every key is one request to the raw route with as=zarr,
// below the folder (`urlOf`), counted against the view's budget. `openZarr` reads and checks the
// metadata first (Zarr v2: `.zattrs`, `.zgroup`, each level's `.zarray`; at most 1 MiB each, the
// JSON depth pre-scan, then JSON.parse); the store then serves only that checked metadata, rebuilt
// from the fields Viv reads, and the chunk keys of the checked levels, each checked against its
// decoded size by our decoders (codecs.ts, in the decoder worker in the page). `.zmetadata` and
// any other key are never asked.
import { MIB, tooDeep } from "../preview";
import { Answered, BUDGET, IN_FLIGHT, Refused, Stopped, problem, readAtMost } from "./client";
import { type Chunk, decodeChunk } from "./codecs";
import { Unsupported } from "./flat";
import { IFDS_MAX, TooLarge, Unreadable } from "./walk";

const META_MAX = MIB;
const CHUNK_READ_MAX = 16 * MIB; // the server's cap per key (api §5.3.1 step 7)
const CHUNK_VALUES_MAX = 16 * MIB; // 16 M values, so at most 64 MiB decoded
const SIDE_MAX = 2 ** 31 - 1; // px per side (req. 19: sizes are untrusted; SEC-P3FU102G-02)
export const LEVELS_MAX = 32;
const AXES = ["t", "c", "z", "y", "x"];
const PART = /^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,254}$/; // api §5.3.1 step 5, a middle part
const META = new Set([".zattrs", ".zgroup", ".zarray", "zarr.json"]); // the last part; no `.zmetadata`
const CHUNK = /^\d{1,10}([./]\d{1,10}){0,9}$/;
const DTYPES: Record<string, number> = { u1: 1, i1: 1, u2: 2, i2: 2, u4: 4, i4: 4, f4: 4 };
// decoded by codecs.ts, not numcodecs 0.3.2, whose Blosc, LZ4 and zstd glue runs through
// `Function` (dist/blosc.js:193, dist/lz4.js:192), which the CSP refuses (inbox #150)
const COMPRESSORS = new Set(["zlib", "gzip", "blosc", "lz4", "zstd"]);
const LABEL_MAX = 64; // a channel's name, in characters (SEC-P3FU102G-04)
const VERSION = /^[0-9A-Za-z.-]{1,16}$/; // the multiscales version copied to Viv

/** A folder with no OME-Zarr image, a plate or labels: shown with Browse folder. */
export class NotImage extends Unsupported {}

type Level = { bytes: number; compressor: string | null; shape: number[] };
export type ZarrMeta = { labels: string[]; names: string[]; colours: ([number, number, number] | null)[] };

const json = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));
const own = (o: unknown, k: string): unknown => (o && typeof o === "object" && Object.hasOwn(o, k) ? (o as Record<string, unknown>)[k] : undefined);
const sizes = (v: unknown, n: number) => Array.isArray(v) && v.length === n && v.every((x) => Number.isSafeInteger(x) && x >= 1);

export class ZarrStore {
  readonly log: string[] = [];
  requests = 0;
  bytes = 0;
  failure: Error | null = null;
  work = false; // a work directory's store: it refuses every dot part, so a v2 `.zattrs` gets a 422
  onBusy?: (busy: boolean) => void;
  /** A chunk's decoder: in the page, the decoder pool's worker (OmeView); here by default. */
  decode = async (chunk: Chunk, data: Uint8Array) => new Uint8Array(decodeChunk(chunk, data.buffer as ArrayBuffer));
  private served = new Map<string, Uint8Array>(); // the checked metadata, by key
  private levels = new Map<string, Level>(); // the checked levels, by path
  private active = 0;
  private waiting: (() => void)[] = [];

  constructor(
    private readonly urlOf: (key: string) => string,
    private readonly signal?: AbortSignal,
    private readonly budget = BUDGET,
  ) {}

  /** Viv's and zarrita's reads, by absolute key ("/0/.zarray"): checked metadata, or a checked chunk. */
  async get(key: string): Promise<Uint8Array | undefined> {
    const k = key.replace(/^\//, "");
    if (this.served.has(k)) return this.served.get(k);
    const path = [...this.levels.keys()].find((p) => k.startsWith(`${p}/`) && CHUNK.test(k.slice(p.length + 1)));
    const level = path === undefined ? undefined : this.levels.get(path);
    if (!level) return undefined; // never asked: absent
    try {
      const data = await this.fetchKey(k, CHUNK_READ_MAX);
      return data && (await this.decode({ compressor: level.compressor, bytes: level.bytes }, data));
    } catch (err) {
      if ((err as Error).name !== "AbortError") this.failure = err as Error;
      throw err;
    }
  }

  /** One key below the folder, read whole, at most `max` bytes; undefined on a 404. */
  async fetchKey(key: string, max: number): Promise<Uint8Array | undefined> {
    const parts = key.split("/");
    if (!parts.every((p, i) => (PART.test(p) && p !== "." && p !== "..") || (i === parts.length - 1 && META.has(p)))) throw new Refused(`not asked: ${key}`);
    if (this.requests + 1 > this.budget.requests) throw new Stopped("requests");
    this.requests++;
    let [reserve, read] = [0, 0];
    while (this.active >= IN_FLIGHT) await new Promise<void>((go) => this.waiting.push(go));
    if (this.active++ === 0) this.onBusy?.(true);
    try {
      // reserved in the slot, before the read: at most IN_FLIGHT reads are held (SEC-P3FU102G-03, SEC-P3FU102H-01)
      const room = Math.min(max, this.budget.bytes - this.bytes);
      if (room <= 0) throw new Stopped("bytes");
      reserve = room;
      this.bytes += reserve;
      const url = this.urlOf(key);
      this.log.push(url);
      const answer = await fetch(url, { signal: this.signal, credentials: "same-origin" });
      if (answer.status === 404) return (await answer.body?.cancel(), undefined);
      if (answer.status === 413) throw new TooLarge("a Zarr chunk over 16 MiB");
      if (answer.status !== 200) throw new Answered(answer.status, await problem(answer));
      const data = await readAtMost(answer, reserve);
      if (!data && reserve < max) throw new Stopped("bytes"); // the budget ends inside this read
      if (!data) throw new TooLarge(max === META_MAX ? "Zarr metadata over 1 MiB" : "a Zarr chunk over 16 MiB");
      read = data.byteLength;
      return data;
    } finally {
      this.bytes -= reserve - read; // the reserve given back: only what was read is counted
      this.active--;
      this.waiting.shift()?.();
      if (this.active === 0 && !this.waiting.length) this.onBusy?.(false);
    }
  }

  /** The metadata Viv will read, checked; then only it and the checked levels' chunks are served. */
  lock(served: Map<string, Uint8Array>, levels: Map<string, Level>) {
    [this.served, this.levels] = [served, levels];
  }
}

/** A key's JSON object, at most 1 MiB; undefined when the key is absent. */
async function readJson(store: ZarrStore, key: string): Promise<Record<string, unknown> | undefined> {
  const data = await store.fetchKey(key, META_MAX);
  if (!data) return undefined;
  const text = new TextDecoder().decode(data);
  if (tooDeep(text)) throw new Unreadable(`${key} is nested too deeply`);
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Unreadable(`${key} is not JSON`);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Unreadable(`${key} is not a JSON object`);
  return value as Record<string, unknown>;
}

/** A level's `.zarray`, checked: shape, chunk size, dtype, compressor; rebuilt from its fields. */
function checkArray(meta: Record<string, unknown> | undefined, n: number): { zarray: Record<string, unknown>; level: Level } {
  if (!meta || own(meta, "zarr_format") !== 2) throw new Unreadable("a level is not a Zarr v2 array");
  const [shape, chunks, dtype, order, sep] = ["shape", "chunks", "dtype", "order", "dimension_separator"].map((k) => own(meta, k));
  if (!sizes(shape, n) || !sizes(chunks, n)) throw new Unreadable("a level's shape does not match its axes");
  const dims = shape as number[];
  if (dims.slice(0, -2).reduce((a, b) => a * b, 1) > IFDS_MAX) throw new TooLarge(`over ${IFDS_MAX.toLocaleString("en-US")} planes`);
  if (dims.slice(-2).some((side) => side > SIDE_MAX)) throw new TooLarge(`a side over ${SIDE_MAX.toLocaleString("en-US")} px`);
  const values = (chunks as number[]).reduce((a, b) => a * b, 1);
  if (values > CHUNK_VALUES_MAX) throw new TooLarge("a Zarr chunk over 16 M values");
  const type = typeof dtype === "string" ? /^[<>|]?([a-z]\d+)$/.exec(dtype)?.[1] : undefined;
  if (!type || !DTYPES[type]) throw new TooLarge(`${type === "f8" ? "float64" : String(dtype)} pixels are not shown`);
  const filters = own(meta, "filters");
  if (filters !== null && filters !== undefined && !(Array.isArray(filters) && !filters.length)) throw new Unsupported("Spectio cannot decode Zarr filters.");
  const compressor = own(meta, "compressor") ?? null;
  const id = compressor === null ? null : own(compressor, "id");
  if (id !== null && (typeof id !== "string" || !COMPRESSORS.has(id))) throw new Unsupported(`Spectio cannot decode ${String(id)} compression.`);
  if (id === "blosc" && own(compressor, "cname") === "snappy") throw new Unsupported("Spectio cannot decode blosc snappy compression.");
  const fill = own(meta, "fill_value") ?? null;
  if (!(fill === null || Number.isFinite(fill) || ["NaN", "Infinity", "-Infinity"].includes(fill as string))) throw new Unreadable("a level's fill value is not a number");
  // every compressor is decoded by the store, capped, and served as raw bytes
  const zarray = { zarr_format: 2, shape, chunks, dtype, compressor: null, fill_value: fill, order: order === "F" ? "F" : "C", filters: null, dimension_separator: sep === "/" ? "/" : "." };
  return { zarray, level: { bytes: values * DTYPES[type], compressor: id as string | null, shape: dims } };
}

/** Reads and checks the OME-Zarr image's metadata, then locks the store to it (ui-spec §4.4.1 states). */
export async function openZarr(store: ZarrStore): Promise<ZarrMeta> {
  const attrs = await readJson(store, ".zattrs").catch(async (err: unknown) => {
    if (!(store.work && err instanceof Answered && err.status === 422)) throw err;
    if (await store.fetchKey("zarr.json", META_MAX)) throw new Unsupported("Spectio cannot open Zarr v3 yet.");
    throw new Unsupported("This OME-Zarr uses Zarr v2, which a work directory does not serve. Open it from the results once it is published.");
  });
  if (!attrs) throw (await store.fetchKey("zarr.json", META_MAX)) ? new Unsupported("Spectio cannot open Zarr v3 yet.") : new NotImage("This folder has no OME-Zarr image metadata.");
  if (own(attrs, "plate") !== undefined || own(attrs, "image-label") !== undefined) throw new NotImage("Spectio does not show OME-Zarr plates or labels yet.");
  const multiscales = own(attrs, "multiscales");
  const first = Array.isArray(multiscales) ? multiscales[0] : undefined;
  const datasets = own(first, "datasets");
  if (!Array.isArray(datasets) || !datasets.length) throw new NotImage("This folder has no OME-Zarr image metadata.");
  if (datasets.length > LEVELS_MAX) throw new TooLarge(`over ${LEVELS_MAX} levels`);
  const paths = datasets.map((d) => own(d, "path"));
  if (!paths.every((p) => typeof p === "string" && p.split("/").every((part) => PART.test(part) && part !== "." && part !== ".."))) throw new Unreadable("a level's path is not a key of the folder");
  const axes = own(first, "axes");
  const labels = axes === undefined ? AXES : Array.isArray(axes) ? axes.map((a) => (typeof a === "string" ? a : own(a, "name"))) : [];
  const fits = labels.length >= 2 && labels.length <= 5 && new Set(labels).size === labels.length && labels.every((l) => AXES.includes(l as string)) && labels.slice(-2).join() === "y,x";
  if (!fits) throw new Unreadable("its axes are not t, c, z, y and x");
  const group = await readJson(store, ".zgroup");
  if (!group || own(group, "zarr_format") !== 2) throw new Unreadable("the folder is not a Zarr v2 group");
  const served = new Map<string, Uint8Array>([[".zgroup", json({ zarr_format: 2 })]]);
  const version = own(first, "version");
  served.set(".zattrs", json({ multiscales: [{ version: typeof version === "string" && VERSION.test(version) ? version : "0.4", axes: labels.map((name) => ({ name })), datasets: paths.map((path) => ({ path })) }] }));
  const levels = new Map<string, Level>();
  for (const path of paths as string[]) {
    const { zarray, level } = checkArray(await readJson(store, `${path}/.zarray`), labels.length);
    const top = levels.values().next().value?.shape ?? level.shape; // level 0: the same t, c and z, and no side growing
    if (level.shape.some((size, i) => (i < labels.length - 2 ? size !== top[i] : size > top[i]))) throw new Unreadable("a level's shape does not follow level 0");
    served.set(`${path}/.zarray`, json(zarray));
    levels.set(path, level);
  }
  store.lock(served, levels);
  const shape = levels.get(paths[0] as string)!.shape;
  const count = labels.includes("c") ? shape[labels.indexOf("c")] : 1;
  const channels = own(own(attrs, "omero"), "channels");
  const meta = (i: number, k: string) => (Array.isArray(channels) ? own(channels[i], k) : undefined);
  const names = Array.from({ length: count }, (_, c) => (typeof meta(c, "label") === "string" && (meta(c, "label") as string).trim().slice(0, LABEL_MAX)) || `Channel ${c + 1}`);
  const colours = Array.from({ length: count }, (_, c) => {
    const hex = meta(c, "color");
    return typeof hex === "string" && /^[0-9A-Fa-f]{6}$/.test(hex) ? ([0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number]) : null;
  });
  return { labels: labels as string[], names, colours };
}
