// The Viv viewer's hand-off and lifecycle (FU-P3-102e; api §5.3.1, ui-spec §4.4.1): Viv gets the
// GeoTIFF the page opened and our decoder pool, never a URL; one viewer at a time; its WebGL
// context is lost when it ends. Viv and deck.gl are mocked: jsdom has no WebGL.
import { beforeEach, expect, test, vi } from "vitest";

const viv = vi.hoisted(() => ({ loadOmeTiff: vi.fn(), layers: [] as Record<string, unknown>[] }));
const decks = vi.hoisted(() => [] as { props: Record<string, unknown>; finalize: ReturnType<typeof vi.fn> }[]);
vi.mock("@hms-dbmi/viv", () => ({
  loadOmeTiff: viv.loadOmeTiff,
  isInterleaved: (shape: number[]) => shape[shape.length - 1] === 3,
  getImageSize: (s: { shape: number[] }) => ({ height: s.shape[3], width: s.shape[4] }),
  getDefaultInitialViewState: () => ({ target: [50, 25, 0], zoom: -1 }),
  MultiscaleImageLayer: class {
    constructor(props: Record<string, unknown>) {
      viv.layers.push(props);
    }
  },
}));
vi.mock("@deck.gl/core", () => ({
  OrthographicView: class {},
  Deck: class {
    finalize = vi.fn();
    constructor(public props: Record<string, unknown>) {
      decks.push(this);
    }
    setProps(more: Record<string, unknown>) {
      Object.assign(this.props, more);
    }
  },
}));

import { Viewer, openPixels } from "./viv";
import { Unreadable } from "./walk";

const source = (levels: number[][]) =>
  levels.map((shape) => ({
    shape,
    tileSize: 512,
    getRaster: vi.fn(async () => ({ data: new Uint16Array(4).map((_, i) => 100 * i) })),
    getTile: vi.fn(async () => ({ data: new Float32Array(4).map((_, i) => -0.5 + i * 0.25), width: 2, height: 2 })),
  }));
const pixels = (c: number) => ({ SizeX: 100, SizeY: 50, SizeC: c, SizeZ: 3, SizeT: 2, Type: "uint16" });
/** The walk's IFDs: `n` planes of 100 x 50 px. */
const ifds = (n = 10_000) => Array.from({ length: n }, () => ({ ImageWidth: 100, ImageLength: 50 }));

beforeEach(() => {
  viv.loadOmeTiff.mockReset();
  viv.layers.length = decks.length = 0;
});

test("Viv is handed the opened GeoTIFF and our pool, not a URL; at most 6 channels on", async () => {
  const tiff = { opened: true };
  const pool = { decode: vi.fn() };
  viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 8, 3, 50, 100], [2, 8, 3, 25, 50]]), metadata: { Pixels: { ...pixels(8), Channels: [{ Name: "DAPI", Color: [0, 0, 255, 255] }, { Name: " " }] } } });
  const opened = await openPixels(tiff as never, pool as never, "cells.ome.tif", ifds(48));
  expect(viv.loadOmeTiff).toHaveBeenCalledWith("cells.ome.tif", { source: tiff, pool });
  expect(opened.channels).toEqual([0, 1, 2, 3, 4, 5]);
  expect(opened.facts).toBe("100 × 50 px · 8 channels · 3 planes · 2 time points · uint16");
  const { limits, domain } = await opened.stats(0);
  expect(limits[1]).toBeGreaterThan(limits[0]); // from the lowest level's percentiles
  expect(domain).toEqual([0, 300]); // its minimum and maximum
  expect(opened.names).toEqual(["DAPI", ...Array.from({ length: 7 }, (_, c) => `Channel ${c + 2}`)]);
  expect(opened.colours.slice(0, 2)).toEqual([[0, 0, 255], null]);
  expect(opened.data[1].getRaster).toHaveBeenCalledWith({ selection: { z: 0, t: 0, c: 0 } });
});

test("over 10,000 planes is too large, before any tile is read", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[200, 60, 1, 50, 100]]), metadata: { Pixels: { ...pixels(60), SizeZ: 1, SizeT: 200 } } });
  await expect(openPixels({} as never, {} as never, "x.ome.tif", ifds())).rejects.toThrow("over 10,000 planes");
});

test("one viewer at a time: a second one ends the first; each end loses its WebGL context", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 2, 3, 50, 100]]), metadata: { Pixels: pixels(2) } });
  const opened = await openPixels({} as never, {} as never, "a.ome.tif", ifds(12));
  const lose = vi.fn();
  const canvas = (() => {
    const c = document.createElement("canvas");
    c.getContext = (() => ({ getExtension: (name: string) => (name === "WEBGL_lose_context" ? { loseContext: lose } : null) })) as never;
    return c;
  })();
  const events = { onView: vi.fn(), onTileError: vi.fn(), onError: vi.fn() };
  const first = new Viewer(canvas, opened, events);
  expect(decks[0].props.canvas).toBe(canvas);
  const drawn = [0, 1].map((c) => ({ c, colour: [0, 0, 255] as [number, number, number], limits: [0, 9] as [number, number] }));
  first.draw({ target: [1, 2, 0], zoom: 0 }, { z: 2, t: 1 }, 0, drawn);
  expect(viv.layers[0].selections).toEqual([{ z: 2, t: 1, c: 0 }, { z: 2, t: 1, c: 1 }]);
  expect(viv.layers[0].onTileError).toBe(events.onTileError);
  first.draw({ target: [1, 2, 0], zoom: 0 }, { z: 2, t: 1 }, 1, drawn);
  first.draw({ target: [1, 2, 0], zoom: 0 }, { z: 2, t: 1 }, 1, []);
  expect(decks[0].props.layers).toEqual([]); // every channel off: no layer
  expect(viv.layers[1].id).not.toBe(viv.layers[0].id); // a new epoch asks the tiles again
  const second = new Viewer(canvas, opened, events);
  expect(decks[0].finalize).toHaveBeenCalledOnce();
  expect(lose).toHaveBeenCalledOnce();
  second.destroy();
  second.destroy(); // twice is once
  first.destroy();
  expect(decks[1].finalize).toHaveBeenCalledOnce();
  expect(decks[0].finalize).toHaveBeenCalledOnce();
  expect(lose).toHaveBeenCalledTimes(2);
});

test("the OME-XML sizes are positive integers that match the IFDs, else the file is refused before any tile is read", async () => {
  for (const [given, walked, error] of [
    [{ SizeC: -2, SizeZ: -3 }, 12, new Unreadable("the OME-XML sizes are not positive integers")], // a positive product
    [{ SizeT: 1.5 }, 12, new Unreadable("the OME-XML sizes are not positive integers")],
    [{ SizeX: 1e9, SizeY: 1e9 }, 12, new Unreadable("the OME-XML sizes do not match the image")], // over a 100 x 50 IFD
    [{}, 11, new Unreadable("the OME-XML names more planes than the file holds")],
  ] as const) {
    viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 2, 3, 50, 100]]), metadata: { Pixels: { ...pixels(2), ...given } } });
    await expect(openPixels({} as never, {} as never, "x.ome.tif", ifds(walked))).rejects.toEqual(error);
  }
});

test("deck.gl's tile cache holds at most 256 MiB of decoded tiles", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 2, 3, 50, 100]]), metadata: { Pixels: pixels(2) } });
  const opened = await openPixels({} as never, {} as never, "a.ome.tif", ifds(12));
  const canvas = document.createElement("canvas");
  canvas.getContext = (() => null) as never;
  const viewer = new Viewer(canvas, opened, { onView: vi.fn(), onTileError: vi.fn(), onError: vi.fn() });
  viewer.draw({ target: [0, 0, 0], zoom: 0 }, { z: 0, t: 0 }, 0, [{ c: 0, colour: [0, 0, 255], limits: [0, 9] }]);
  expect(viv.layers[0].maxCacheSize).toBe(Math.floor((256 * 1024 * 1024) / (512 * 512 * 2 * 2))); // 2 channels of uint16
  viewer.destroy();
});

test("a lowest level over 4 megapixels takes its contrast from one tile, not from the type's whole range", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[1, 1, 1, 4096, 4096]]), metadata: { Pixels: { ...pixels(1), SizeX: 4096, SizeY: 4096, SizeZ: 1, SizeT: 1, Type: "float" } } });
  const opened = await openPixels({} as never, {} as never, "f.ome.tif", [{ ImageWidth: 4096, ImageLength: 4096 }]);
  expect(opened.data[0].getRaster).not.toHaveBeenCalled();
  expect(opened.data[0].getTile).toHaveBeenCalledWith({ x: 0, y: 0, selection: { z: 0, t: 0, c: 0 } });
  const { limits } = await opened.stats(0);
  expect(limits[0]).toBeLessThan(0);
  expect(limits[1]).toBeGreaterThan(0);
});
