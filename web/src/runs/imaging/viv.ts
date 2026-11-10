// The OME-TIFF viewer's lazy chunk (FU-P3-102e; ui-spec §4.4.1, api §5.3.1, dev-env §15.3 req. 19):
// Viv and deck.gl are imported here only, by a dynamic import, so the main bundle does not carry
// them. Viv is handed the GeoTIFF the page opened through its pinned client, never a URL:
// `loadOmeTiff(name, { source, pool })`, whose `source` is "a pre-constructed GeoTIFF instance"
// (@vivjs/loaders 0.23.0 `dist/index.d.ts:83-97`; used at `dist/index.mjs:412-415` and
// `:869-876`; the name only decides the companion `.companion.ome` case, `:922-928`).
import { Deck, OrthographicView } from "@deck.gl/core";
import { MultiscaleImageLayer, getDefaultInitialViewState, getImageSize, isInterleaved, loadOmeTiff } from "@hms-dbmi/viv";
import type { GeoTIFF } from "geotiff";
import { registerCapped } from "./decode";
import { percentiles } from "./flat";
import type { DecoderPool } from "./pool";
import { IFDS_MAX, TooLarge } from "./walk";

// Tiles are decoded by our pool (Viv passes it to readRasters, `dist/index.mjs:483-494`); geotiff's
// registry on this thread gets our capped decoders back all the same, so no TIFF needs WebAssembly.
registerCapped();

export const CHANNELS_ON = 6;
const STATS_MAX = 2048 * 2048; // contrast from the lowest level when it is at most this many pixels
const PALETTE: [number, number, number][] = [[0, 0, 255], [0, 255, 0], [255, 0, 255], [255, 255, 0], [0, 255, 255], [255, 128, 0]];
const FULL: Record<string, number> = { uint8: 255, uint16: 65535, uint32: 2 ** 32 - 1 };

type Loaded = Awaited<ReturnType<typeof loadOmeTiff>>;
export type ViewState = { target: [number, number, number]; zoom: number };
export interface Pixels {
  data: Loaded["data"];
  sizes: { z: number; t: number };
  facts: string;
  rgb: boolean;
  channels: number[]; // the channels on at open
  contrast: [number, number][];
}

/** Viv's pixel sources of the opened TIFF, with the first channels on and their contrast. */
export async function openPixels(tiff: GeoTIFF, pool: DecoderPool, name: string): Promise<Pixels> {
  const { data, metadata } = await loadOmeTiff(name, { source: tiff, pool: pool as never });
  const p = metadata.Pixels;
  if (p.SizeZ * p.SizeC * p.SizeT > IFDS_MAX) throw new TooLarge(`over ${IFDS_MAX.toLocaleString("en-US")} planes`);
  const rgb = isInterleaved(data[0].shape);
  const channels = Array.from({ length: rgb ? 1 : Math.min(CHANNELS_ON, p.SizeC) }, (_, c) => c);
  const lowest = data[data.length - 1];
  const { width, height } = getImageSize(lowest);
  const type = String(p.Type).toLowerCase();
  const stats = async (c: number): Promise<[number, number]> => {
    if (rgb) return [0, 255];
    if (width * height > STATS_MAX) return [0, FULL[type] ?? 1];
    return percentiles((await lowest.getRaster({ selection: { z: 0, t: 0, c } })).data as ArrayLike<number>);
  };
  const n = (v: number, one: string, many: string) => `${v.toLocaleString("en-US")} ${v === 1 ? one : many}`;
  const facts = [`${p.SizeX.toLocaleString("en-US")} × ${p.SizeY.toLocaleString("en-US")} px`, n(p.SizeC, "channel", "channels"), n(p.SizeZ, "plane", "planes"), n(p.SizeT, "time point", "time points"), type];
  return { data, sizes: { z: p.SizeZ, t: p.SizeT }, facts: facts.join(" · "), rgb, channels, contrast: await Promise.all(channels.map(stats)) };
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

  /** Draws plane `z`, `t` (0-based) at `view`; a new `epoch` asks every tile again. */
  draw(view: ViewState, { z, t }: { z: number; t: number }, epoch: number) {
    const { data, rgb, channels, contrast } = this.pixels;
    const layer = new MultiscaleImageLayer({
      id: `ome-${epoch}`,
      loader: data,
      selections: channels.map((c) => ({ z, t, c })),
      contrastLimits: contrast,
      colors: rgb ? [[255, 255, 255]] : channels.map((c) => PALETTE[c % PALETTE.length]),
      channelsVisible: channels.map(() => true),
      onTileError: this.events.onTileError,
    } as never);
    this.deck?.setProps({ viewState: view, layers: [layer] });
  }

  destroy() {
    if (!this.deck) return;
    if (current === this) current = null;
    const gl = this.canvas.getContext("webgl2");
    this.deck.finalize();
    this.deck = null;
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  }
}
