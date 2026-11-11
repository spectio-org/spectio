// The OME-TIFF viewer's lazy chunk (FU-P3-102e; ui-spec §4.4.1, api §5.3.1, dev-env §15.3 req. 19):
// Viv and deck.gl are imported here only, by a dynamic import, so the main bundle does not carry
// them. Viv is handed the GeoTIFF the page opened through its pinned client, never a URL:
// `loadOmeTiff(name, { source, pool })`, whose `source` is "a pre-constructed GeoTIFF instance"
// (@vivjs/loaders 0.23.0 `dist/index.d.ts:83-97`; used at `dist/index.mjs:412-415` and
// `:869-876`; the name only decides the companion `.companion.ome` case, `:922-928`). An OME-Zarr
// (FU-P3-102g) is handed our own store, checked by `openZarr`, through `loadOmeZarrFromStore`.
import "./jitless"; // first: before Viv's loaders build their zod schemas
import { Deck, OrthographicView } from "@deck.gl/core";
import { MultiscaleImageLayer, ZarrPixelSource, getDefaultInitialViewState, getImageSize, isInterleaved, loadOmeTiff, loadOmeZarrFromStore } from "@hms-dbmi/viv";
import type { GeoTIFF } from "geotiff";
import { registerCapped } from "./decode";
import { percentiles } from "./flat";
import type { DecoderPool } from "./pool";
import { CHANNELS_ON } from "./url-state";
import { type FileDirectory, IFDS_MAX, TooLarge, Unreadable } from "./walk";
import { type ZarrStore, openZarr } from "./zarr";

// Tiles are decoded by our pool (Viv passes it to readRasters, `dist/index.mjs:483-494`); geotiff's
// registry on this thread gets our capped decoders back all the same, so no TIFF needs WebAssembly.
registerCapped();

const STATS_MAX = 2048 * 2048; // contrast from the lowest level when it is at most this many pixels, else from its first tile
const BYTES: Record<string, number> = { int8: 1, uint8: 1, int16: 2, uint16: 2, int32: 4, uint32: 4, float: 4, float32: 4 };
const CACHE_MAX = 256 * 1024 * 1024; // deck.gl's tile cache, as decoded tiles (dev-env §15.3 req. 19)

type Source = Awaited<ReturnType<typeof loadOmeTiff>>["data"][number] | Awaited<ReturnType<typeof loadOmeZarrFromStore>>["data"][number];
export type ViewState = { target: [number, number, number]; zoom: number };
export type Rgb = [number, number, number];
/** A channel's contrast at open (its 0.1 and 99.9 percentiles) and its domain (minimum, maximum). */
export type Stats = { limits: [number, number]; domain: [number, number] };
/** A channel as drawn. */
export type Drawn = { c: number; colour: Rgb; limits: [number, number] };
export interface Pixels {
  data: Source[];
  sizes: { x: number; y: number; z: number; c: number; t: number };
  facts: string;
  rgb: boolean;
  names: string[]; // the OME-XML Channel Name, else "Channel <n>"
  colours: (Rgb | null)[]; // the OME-XML Channel Color
  channels: number[]; // the channels on at open
  stats: (c: number) => Promise<Stats>; // read once per channel, the first channels' before the open ends
  cacheTiles: number; // deck.gl's tile cache, in tiles: 256 MiB of decoded tiles
}

/** Viv's pixel sources of the opened TIFF, with the first channels on and their contrast. The
 * OME-XML sizes, from which Viv builds each level's shape (@vivjs/loaders 0.23.0
 * `dist/index.mjs:223-225`), are held to the walked IFDs (`ifds`) before any tile is read. */
export async function openPixels(tiff: GeoTIFF, pool: DecoderPool, name: string, ifds: FileDirectory[]): Promise<Pixels> {
  const { data, metadata } = await loadOmeTiff(name, { source: tiff, pool: pool as never });
  const p = metadata.Pixels;
  const sizes = [p.SizeX, p.SizeY, p.SizeZ, p.SizeC, p.SizeT];
  if (!sizes.every((v) => Number.isSafeInteger(v) && v > 0)) throw new Unreadable("the OME-XML sizes are not positive integers");
  const planes = p.SizeZ * p.SizeC * p.SizeT;
  if (planes > IFDS_MAX) throw new TooLarge(`over ${IFDS_MAX.toLocaleString("en-US")} planes`);
  if (p.SizeX !== ifds[0]?.ImageWidth || p.SizeY !== ifds[0]?.ImageLength) throw new Unreadable("the OME-XML sizes do not match the image");
  const samples = Number(ifds[0].SamplesPerPixel ?? 1); // an interleaved RGB plane holds its 3 channels
  if (planes > ifds.length * samples) throw new Unreadable("the OME-XML names more planes than the file holds");
  // the OME-XML Channel elements (@vivjs/loaders 0.23.0 `dist/index.mjs:646-652`, Color as RGBA by `intToRgba`, `:92-100`)
  const meta = (p.Channels ?? []) as { Name?: string; Color?: number[] }[];
  const names = Array.from({ length: p.SizeC }, (_, c) => meta[c]?.Name?.trim() || `Channel ${c + 1}`);
  const colours = Array.from({ length: p.SizeC }, (_, c) => (meta[c]?.Color?.slice(0, 3) as Rgb | undefined) ?? null);
  return pixelsOf(data, { x: p.SizeX, y: p.SizeY, z: p.SizeZ, c: p.SizeC, t: p.SizeT }, String(p.Type).toLowerCase(), names, colours);
}

/** Viv's pixel sources of the OME-Zarr our store reads, its metadata checked first. */
export async function openZarrPixels(store: ZarrStore): Promise<Pixels> {
  const { labels, names, colours } = await openZarr(store);
  const { data } = await loadOmeZarrFromStore(store as never);
  const size = (l: string) => (labels.includes(l) ? data[0].shape[labels.indexOf(l)] : 1);
  return pixelsOf(data, { x: size("x"), y: size("y"), z: size("z"), c: size("c"), t: size("t") }, data[0].dtype.toLowerCase(), names, colours);
}

/** The plane `z`, `t`, channel `c`, by the source's own axes (an OME-Zarr may have no z or t). */
const selection = (data: Source[], at: { z: number; t: number; c: number }) => Object.fromEntries(Object.entries(at).filter(([k]) => (data[0].labels as string[]).includes(k)));

async function pixelsOf(data: Source[], all: Pixels["sizes"], type: string, names: string[], colours: (Rgb | null)[]): Promise<Pixels> {
  const rgb = isInterleaved(data[0].shape);
  const channels = Array.from({ length: rgb ? 1 : Math.min(CHANNELS_ON, all.c) }, (_, c) => c);
  const lowest = data[data.length - 1];
  const { width, height } = getImageSize(lowest);
  const read = async (c: number): Promise<Stats> => {
    if (rgb) return { limits: [0, 255], domain: [0, 255] };
    const at = selection(data, { z: 0, t: 0, c }) as never;
    const values = (await (width * height > STATS_MAX ? lowest.getTile({ x: 0, y: 0, selection: at }) : lowest.getRaster({ selection: at }))).data as ArrayLike<number>;
    let [min, max] = [Infinity, -Infinity]; // NaN is skipped: it compares false
    for (let i = 0; i < values.length; i++) {
      if (values[i] < min) min = values[i];
      if (values[i] > max) max = values[i];
    }
    const limits = percentiles(values);
    return { limits, domain: min <= max ? [min, max] : limits };
  };
  const cache = new Map<number, Promise<Stats>>();
  const stats = (c: number) => {
    if (!cache.has(c)) cache.set(c, read(c).catch((err) => (cache.delete(c), Promise.reject(err)))); // a failure is read again on Retry
    return cache.get(c) as Promise<Stats>;
  };
  const n = (v: number, one: string, many: string) => `${v.toLocaleString("en-US")} ${v === 1 ? one : many}`;
  const facts = [`${all.x.toLocaleString("en-US")} × ${all.y.toLocaleString("en-US")} px`, n(all.c, "channel", "channels"), n(all.z, "plane", "planes"), n(all.t, "time point", "time points"), type];
  // Viv's tiles ({data, width, height}) have no byteLength, so deck.gl's maxCacheByteSize cannot
  // count them (@deck.gl/geo-layers 9.4.1 `dist/tileset-2d/tile-2d-header.js:54-55`): the cap is a count
  const tileBytes = data[0].tileSize ** 2 * (rgb ? 3 : Math.min(CHANNELS_ON, all.c)) * (BYTES[type] ?? 4);
  const cacheTiles = Math.max(1, Math.floor(CACHE_MAX / tileBytes));
  await Promise.all(channels.map(stats));
  return { data, sizes: all, facts: facts.join(" · "), rgb, names, colours, channels, stats, cacheTiles };
}

export interface Events {
  onView: (view: ViewState) => void;
  onTileError: (err: Error) => void;
  onError: (err: Error) => void;
}

let current: Viewer | null = null;

/** The one WebGL viewer of the page: a new one ends the one before; `destroy` loses its context
 * (deck.gl's `finalize` alone does not: `@deck.gl/core` 9.4.1 `dist/lib/deck.js:305-340`). */
export class Viewer {
  private deck: Deck<OrthographicView> | null;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly pixels: Pixels,
    private readonly events: Events,
  ) {
    current?.destroy();
    current = this;
    this.deck = new Deck({
      canvas,
      views: new OrthographicView({ id: "ome", controller: { keyboard: false } }),
      viewState: this.fit(),
      onViewStateChange: ({ viewState }) => events.onView(viewState as ViewState),
      onError: (err) => events.onError(err),
      layers: [],
    });
  }

  /** The whole image in the canvas. */
  fit(): ViewState {
    const size = { width: this.canvas.clientWidth || 800, height: this.canvas.clientHeight || 600 };
    return getDefaultInitialViewState(this.pixels.data, size) as ViewState;
  }

  /** Draws `channels` of plane `z`, `t` (0-based) at `view`; a new `epoch` asks every tile again. */
  draw(view: ViewState, { z, t }: { z: number; t: number }, epoch: number, channels: Drawn[]) {
    const { data, rgb } = this.pixels;
    if (!channels.length) return this.deck?.setProps({ viewState: view, layers: [] }); // every channel off: black
    // The luma.gl warning on `instancePickingColors` (FU-P3-108, retests g and h) stays: Viv's
    // XRLayer vertex shader declares that attribute (@vivjs/layers 0.23.0 `dist/index.mjs:411`) and
    // its attribute manager adds only `positions` (`dist/index.mjs:523-531`), so luma.gl 9.4.2 finds
    // no buffer layout for it (`core/dist/adapter-utils/buffer-layout-utils.js:101`; that this is the
    // retests' line is [to be validated]). `pickable: false` would not remove it: same shader.
    const layer = new MultiscaleImageLayer({
      id: `ome-${epoch}`,
      loader: data,
      selections: channels.map(({ c }) => selection(data, { z, t, c })),
      contrastLimits: channels.map((d) => d.limits),
      colors: rgb ? [[255, 255, 255]] : channels.map((d) => d.colour),
      channelsVisible: channels.map(() => true),
      onTileError: data[0] instanceof ZarrPixelSource ? this.zarrTileError : this.events.onTileError,
      maxCacheSize: this.pixels.cacheTiles, // passed on to deck.gl's TileLayer (@vivjs/layers 0.23.0 `dist/index.mjs:979`)
    } as never);
    this.deck?.setProps({ viewState: view, layers: [layer] });
  }

  // our handler replaces the source's (@vivjs/layers 0.23.0 `dist/index.mjs:1004`), whose Zarr one
  // throws every error but a tile out of the level's bounds (@vivjs/loaders 0.23.0 `dist/index.mjs:1231-1235`)
  private zarrTileError = (err: Error) => {
    try {
      (this.pixels.data[0] as ZarrPixelSource<string[]>).onTileError(err);
    } catch {
      this.events.onTileError(err);
    }
  };

  destroy() {
    if (!this.deck) return;
    if (current === this) current = null;
    const gl = this.canvas.getContext("webgl2");
    this.deck.finalize();
    this.deck = null;
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  }
}
