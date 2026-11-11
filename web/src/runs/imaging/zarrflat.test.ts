// The flat view of an OME-Zarr (FU-P3-102i; ui-spec §4.4.1, the flat view and Phone): one plane
// (channel 1, z 1, t 1) of one level, read through our store with zarrita alone, no Viv and no WebGL.
import { deflate } from "pako";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { type Chunk, decodeChunk } from "./codecs";
import { type Store, raw, valid } from "./fixtures/zarr";
import { readZarrFlat } from "./zarrflat";

const ROOT = "/api/v1/runs/run_1/results/raw/img/cells.ome.zarr/";
const urlOf = (key: string) => `${ROOT}${key}?as=zarr`;
const json = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));
const zarray = (shape: number[], chunks: number[]) => json({ zarr_format: 2, shape, chunks, dtype: "<u2", compressor: { id: "zlib", level: 1 }, fill_value: 0, order: "C", filters: null });
let store: Store;
const asked: string[] = [];
const decoded: Chunk[] = [];
const decode = async (chunk: Chunk, data: Uint8Array) => (decoded.push(chunk), new Uint8Array(decodeChunk(chunk, data.slice().buffer)));

beforeEach(() => {
  store = valid();
  asked.length = decoded.length = 0;
  vi.stubGlobal("fetch", async (url: string) => {
    asked.push(url);
    const body = url.startsWith(ROOT) ? store.get(url.slice(ROOT.length, -"?as=zarr".length)) : undefined;
    return body ? new Response(body as BodyInit, { status: 200 }) : new Response(null, { status: 404 });
  });
});
afterEach(() => vi.unstubAllGlobals());

const read = (phone: boolean) => readZarrFlat(urlOf, false, phone, decode);

test("on a desktop without WebGL 2: channel 1 of level 0, stretched, through the given decoder, one chunk read", async () => {
  const flat = (await read(false))!;
  expect([flat.width, flat.height, flat.full]).toEqual([12, 10, [12, 10]]);
  expect(flat.stretched).toBe(true); // uint16
  const grey = Array.from(flat.rgba).filter((_, i) => i % 4 === 0);
  expect(grey[0]).toBe(0);
  expect(grey[119]).toBe(255);
  expect(decoded).toEqual([{ compressor: "zlib", bytes: 240 }]); // the decoder pool's, never the main thread's
  expect(asked.filter((u) => /\/\d+\/\d/.test(u))).toEqual([`${ROOT}0/0.0.0?as=zarr`]);
});

test("on a phone: the largest level whose sides are both at most 2,048 px", async () => {
  store.set("0/.zarray", zarray([2, 3000, 12], [1, 1000, 12]));
  const flat = (await read(true))!;
  expect([flat.width, flat.height, flat.full]).toEqual([6, 5, [12, 3000]]);
  expect(asked.filter((u) => /\/\d+\/\d/.test(u))).toEqual([`${ROOT}1/0.0.0?as=zarr`]);
});

test("on a phone with no level that small: null, and no chunk read", async () => {
  store.set("0/.zarray", zarray([2, 3000, 12], [1, 1000, 12]));
  store.set("1/.zarray", zarray([2, 2049, 6], [1, 1000, 6]));
  expect(await read(true)).toBeNull();
  expect(asked.filter((u) => /\/\d+\/\d/.test(u))).toEqual([]);
});

test("without WebGL 2 the largest level of at most 50 megapixels; none that small is the too-large state", async () => {
  store.set("0/.zarray", zarray([2, 10000, 6000], [1, 1000, 1000]));
  store.set("1/.zarray", zarray([2, 5, 6], [1, 5, 6]));
  store.set("1/0.0.0", deflate(raw(30)));
  const flat = (await read(false))!;
  expect([flat.width, flat.height, flat.full]).toEqual([6, 5, [6000, 10000]]);
  store.set("1/.zarray", zarray([2, 9000, 6000], [1, 1000, 1000])); // 54 megapixels
  await expect(read(false)).rejects.toMatchObject({ reason: "a plane over 50 megapixels" });
});
