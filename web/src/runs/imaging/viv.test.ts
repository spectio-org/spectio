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

const source = (levels: number[][]) => levels.map((shape) => ({ shape, getRaster: vi.fn(async () => ({ data: new Uint16Array(4).map((_, i) => 100 * i) })) }));
const pixels = (c: number) => ({ SizeX: 100, SizeY: 50, SizeC: c, SizeZ: 3, SizeT: 2, Type: "uint16" });

beforeEach(() => {
  viv.loadOmeTiff.mockReset();
  viv.layers.length = decks.length = 0;
});

test("Viv is handed the opened GeoTIFF and our pool, not a URL; at most 6 channels on", async () => {
  const tiff = { opened: true };
  const pool = { decode: vi.fn() };
  viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 8, 3, 50, 100], [2, 8, 3, 25, 50]]), metadata: { Pixels: pixels(8) } });
  const opened = await openPixels(tiff as never, pool as never, "cells.ome.tif");
  expect(viv.loadOmeTiff).toHaveBeenCalledWith("cells.ome.tif", { source: tiff, pool });
  expect(opened.channels).toEqual([0, 1, 2, 3, 4, 5]);
  expect(opened.facts).toBe("100 × 50 px · 8 channels · 3 planes · 2 time points · uint16");
  expect(opened.contrast[0][1]).toBeGreaterThan(opened.contrast[0][0]); // from the lowest level's percentiles
  expect(opened.data[1].getRaster).toHaveBeenCalledWith({ selection: { z: 0, t: 0, c: 0 } });
});

test("over 10,000 planes is too large, before any tile is read", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[200, 60, 1, 50, 100]]), metadata: { Pixels: { ...pixels(60), SizeZ: 1, SizeT: 200 } } });
  await expect(openPixels({} as never, {} as never, "x.ome.tif")).rejects.toThrow("over 10,000 planes");
});

test("one viewer at a time: a second one ends the first; each end loses its WebGL context", async () => {
  viv.loadOmeTiff.mockResolvedValue({ data: source([[2, 2, 3, 50, 100]]), metadata: { Pixels: pixels(2) } });
  const opened = await openPixels({} as never, {} as never, "a.ome.tif");
  const lose = vi.fn();
  const canvas = (() => {
    const c = document.createElement("canvas");
    c.getContext = (() => ({ getExtension: (name: string) => (name === "WEBGL_lose_context" ? { loseContext: lose } : null) })) as never;
    return c;
  })();
  const events = { onView: vi.fn(), onTileError: vi.fn(), onError: vi.fn() };
  const first = new Viewer(canvas, opened, events);
  expect(decks[0].props.canvas).toBe(canvas);
  first.draw({ target: [1, 2, 0], zoom: 0 }, { z: 2, t: 1 }, 0);
  expect(viv.layers[0].selections).toEqual([{ z: 2, t: 1, c: 0 }, { z: 2, t: 1, c: 1 }]);
  expect(viv.layers[0].onTileError).toBe(events.onTileError);
  first.draw({ target: [1, 2, 0], zoom: 0 }, { z: 2, t: 1 }, 1);
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
