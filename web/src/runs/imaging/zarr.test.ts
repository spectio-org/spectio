// The page's own Zarr store (FU-P3-102g; api §5.3.1, dev-env §15.3 req. 19 Malicious Zarr): keys
// read one by one through the raw route with as=zarr, below the folder only, metadata capped at
// 1 MiB and checked before Viv sees it, chunks checked against their decoded size before decode.
// The stores are crafted by fixtures/zarr.ts and served by a fake fetch; Viv's real loader opens them.
import "./decode"; // as in the page: our decoders are registered before Viv's chunk loads
import { loadOmeZarrFromStore } from "@hms-dbmi/viv";
import { deflate } from "pako";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { BUDGET, Stopped } from "./client";
import { type Chunk, decodeChunk } from "./codecs";
import { imageState } from "./flat";
import fixtures from "./fixtures/codecs.json";
import { type Store, attrs, crafted, raw, valid } from "./fixtures/zarr";
import { ZarrStore, openZarr } from "./zarr";

// the page gives the decoder pool's workers; here the same decoders run in the test
const inPage = async (chunk: Chunk, data: Uint8Array) => new Uint8Array(decodeChunk(chunk, data.slice().buffer));

const ROOT = "/api/v1/runs/run_1/results/raw/img/cells.ome.zarr/";
const urlOf = (key: string) => `${ROOT}${key}?as=zarr`;
let store: Store;
const asked: string[] = [];

beforeEach(async () => {
  store = valid();
  asked.length = 0;
  vi.stubGlobal("fetch", async (url: string) => {
    asked.push(url);
    const key = url.startsWith(ROOT) && url.endsWith("?as=zarr") ? url.slice(ROOT.length, -"?as=zarr".length) : null;
    const body = key === null ? undefined : store.get(key);
    return body ? new Response(body as BodyInit, { status: 200 }) : new Response(null, { status: 404 });
  });
});
afterEach(() => vi.unstubAllGlobals());

/** Every request went to a key below the folder, as the store's log says. */
function inFolder(s: ZarrStore) {
  expect(s.log).toEqual(asked);
  for (const url of asked) expect(url).toMatch(/^\/api\/v1\/runs\/run_1\/results\/raw\/img\/cells\.ome\.zarr\/[A-Za-z0-9_.\/-]+\?as=zarr$/);
  expect(asked.join(" ")).not.toMatch(/\.\.|https:|\.zmetadata/);
}

async function stateOf(variant: string) {
  crafted[variant](store);
  const s = new ZarrStore(urlOf, inPage);
  const err = await openZarr(s).then(() => null, (e: unknown) => e);
  inFolder(s);
  return err && imageState(err);
}

test("a valid OME-Zarr opens through Viv's loader fed by our store, reading keys below the folder only", async () => {
  const s = new ZarrStore(urlOf, inPage);
  const meta = await openZarr(s);
  expect(meta).toEqual({ labels: ["c", "y", "x"], names: ["DAPI", "GFP"], colours: [[0, 0, 255], [0, 255, 0]], levels: [{ path: "0", shape: [2, 10, 12] }, { path: "1", shape: [2, 5, 6] }] });
  const { data } = await loadOmeZarrFromStore(s as never);
  expect(data.map((d) => d.shape)).toEqual([[2, 10, 12], [2, 5, 6]]);
  const tile = await data[1].getRaster({ selection: { c: 1 } } as never);
  expect(Array.from(tile.data as Uint16Array).slice(0, 4)).toEqual([0, 1, 2, 3]);
  inFolder(s);
  expect(asked.filter((u) => u.includes(".zattrs"))).toHaveLength(1); // the metadata is read once, then served checked
});

test.each([
  ["a chunk shape of 10^9", "This image is too large to show here (a Zarr chunk over 16 M values). Download it to open it."],
  ["a multiscales path with ..", "Not an image Spectio can read: a level's path is not a key of the folder"],
  ["a multiscales path with https://", "Not an image Spectio can read: a level's path is not a key of the folder"],
  ["a 1 MiB + 1 .zattrs", "This image is too large to show here (Zarr metadata over 1 MiB). Download it to open it."],
  ["a 1 MiB + 1 .zgroup", "This image is too large to show here (Zarr metadata over 1 MiB). Download it to open it."],
  ["a .zattrs with __proto__ and constructor keys only", "This folder has no OME-Zarr image metadata."],
  ["a bz2 compressor", "Spectio cannot decode bz2 compression."],
  ["a blosc snappy compressor", "Spectio cannot decode blosc snappy compression."],
  ["an array shape of c = 10^9", "This image is too large to show here (over 10,000 planes). Download it to open it."],
  ["a side over 2^31 - 1", "This image is too large to show here (a side over 2,147,483,647 px). Download it to open it."],
  ["a level whose c differs from level 0", "Not an image Spectio can read: a level's shape does not follow level 0"],
  ["a level larger than level 0", "Not an image Spectio can read: a level's shape does not follow level 0"],
  ["33 levels", "This image is too large to show here (over 32 levels). Download it to open it."],
  ["no multiscales", "This folder has no OME-Zarr image metadata."],
  ["a plate", "Spectio does not show OME-Zarr plates or labels yet."],
  ["a float64 array", "This image is too large to show here (float64 pixels are not shown). Download it to open it."],
])("%s ends in its state, with no request outside the folder", async (variant, title) => {
  expect(await stateOf(variant)).toMatchObject({ title });
  expect(Object.prototype).not.toHaveProperty("polluted");
  expect(Object.prototype).not.toHaveProperty("multiscales");
});

test("__proto__ and constructor next to multiscales: the image opens, Viv gets only the checked attributes, Object.prototype is unchanged", async () => {
  const text = JSON.stringify(attrs()).slice(0, -1) + ', "__proto__": {"polluted": 1}, "constructor": {"prototype": {"polluted": 1}}}';
  store.set(".zattrs", new TextEncoder().encode(text));
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  const served = JSON.parse(new TextDecoder().decode(await s.get("/.zattrs")));
  expect(Object.keys(served)).toEqual(["multiscales"]);
  await loadOmeZarrFromStore(s as never);
  expect(Object.prototype).not.toHaveProperty("polluted");
  inFolder(s);
});

test("a raw chunk whose size is not its level's is refused before decode", async () => {
  store.set("1/0.0.0", raw(31));
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  await expect(s.get("/1/0.0.0")).rejects.toThrow("the chunk holds 62 bytes, not 60");
  expect(s.failure).not.toBeNull(); // the viewer says "Some tiles could not be read."
  inFolder(s);
});

test("in a work directory, a 422 on .zattrs is the Zarr v2 state; elsewhere it stays the server's refusal", async () => {
  vi.stubGlobal("fetch", async (url: string) => (url.includes(".zattrs") ? new Response(JSON.stringify({ detail: "not allowed" }), { status: 422, headers: { "content-type": "application/problem+json" } }) : new Response(null, { status: 404 })));
  const s = new ZarrStore(urlOf, inPage);
  s.work = true;
  expect(imageState(await openZarr(s).catch((e: unknown) => e))).toMatchObject({ title: "This OME-Zarr uses Zarr v2, which a work directory does not serve. Open it from the results once it is published." });
  expect(imageState(await openZarr(new ZarrStore(urlOf, inPage)).catch((e: unknown) => e))).toMatchObject({ title: "Not an image Spectio can read: not allowed" });
});

test("keys outside the checked levels are never asked; an absent chunk is the fill value; a server error is the read error", async () => {
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  for (const key of ["/.zmetadata", "/0/../../x/.zattrs", "/2/0.0.0", "/0/.zattrs"]) expect(await s.get(key)).toBeUndefined();
  store.delete("1/0.0.0");
  const { data } = await loadOmeZarrFromStore(s as never);
  expect(Array.from((await data[1].getRaster({ selection: { c: 0 } } as never)).data as Uint16Array)).toEqual(new Array(30).fill(0));
  inFolder(s);
  vi.stubGlobal("fetch", async () => new Response(null, { status: 500 }));
  const err = await openZarr(new ZarrStore(urlOf, inPage)).catch((e: unknown) => e);
  expect(imageState(err)).toMatchObject({ problem: { status: 500 } });
});

test("a zlib level is inflated by the store, capped at the chunk's size: one that inflates past it is refused", async () => {
  const zarray = { zarr_format: 2, shape: [2, 5, 6], chunks: [1, 5, 6], dtype: "|u1", compressor: { id: "zlib", level: 1 }, fill_value: 0, filters: null };
  store.set("1/.zarray", new TextEncoder().encode(JSON.stringify(zarray)));
  store.set("1/0.0.0", deflate(new Uint8Array(30).map((_, i) => i)));
  store.set("1/1.0.0", deflate(new Uint8Array(64 * 1024 * 1024))); // 64 MiB of zeros in a few KiB
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  expect(JSON.parse(new TextDecoder().decode(await s.get("/1/.zarray"))).compressor).toBeNull(); // Viv gets raw bytes
  const { data } = await loadOmeZarrFromStore(s as never);
  expect(Array.from((await data[1].getRaster({ selection: { c: 0 } } as never)).data as Uint8Array).slice(0, 4)).toEqual([0, 1, 2, 3]);
  await expect(s.get("/1/1.0.0")).rejects.toThrow("decodes past");
  inFolder(s);
});

const chunk = (name: string) => Uint8Array.from(atob(fixtures.cases.find((c) => c.name === name)!.data), (c) => c.charCodeAt(0));
const zarrayOf = (compressor: unknown) => new TextEncoder().encode(JSON.stringify({ zarr_format: 2, shape: [2, 50, 100], chunks: [1, 50, 100], dtype: "<u2", compressor, fill_value: 0, filters: null }));

test.each([
  ["blosc", { id: "blosc", cname: "lz4", clevel: 5, shuffle: 1, blocksize: 0 }, "blosc lz4 shuffle", "blosc zstd bitshuffle"],
  ["lz4", { id: "lz4", acceleration: 1 }, "lz4", "lz4"],
  ["zstd", { id: "zstd", level: 3 }, "zstd", "zstd"],
])("a %s level is decoded by the store and served raw to Viv", async (_, compressor, first, second) => {
  store.set("0/.zarray", zarrayOf(compressor));
  store.set("0/0.0.0", chunk(first));
  store.set("0/1.0.0", chunk(second));
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  expect(JSON.parse(new TextDecoder().decode(await s.get("/0/.zarray"))).compressor).toBeNull();
  const { data } = await loadOmeZarrFromStore(s as never);
  const plane = Array.from((await data[0].getRaster({ selection: { c: 1 } } as never)).data as Uint16Array);
  expect(plane.slice(0, 3)).toEqual([0, 13, 26]);
  expect(plane[4999]).toBe(((4999 % 64) * 13 + Math.floor(4999 / 64) * 5) % 1000);
  inFolder(s);
});

test("the byte budget is reserved only for reads in flight: 40 concurrent gets all succeed under the default budget", async () => {
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  const before = s.bytes;
  const keys = Array.from({ length: 40 }, (_, i) => ["/0/0.0.0", "/0/1.0.0", "/1/0.0.0", "/1/1.0.0"][i % 4]);
  const read = await Promise.allSettled(keys.map((k) => s.get(k)));
  expect(read.map((r) => r.status)).toEqual(keys.map(() => "fulfilled"));
  expect(s.failure).toBeNull();
  expect(s.bytes - before).toBe(keys.reduce((n, k) => n + store.get(k.slice(1))!.byteLength, 0)); // only what was read is counted
});

test("a view near the end of its byte budget stops before it reads past it", async () => {
  const s = new ZarrStore(urlOf, inPage);
  await openZarr(s);
  store.set("0/0.0.0", new Uint8Array(2 * 1024 * 1024));
  s.bytes = BUDGET.bytes - 1024 * 1024; // 1 MiB left: the 2 MiB chunk is cut at 1 MiB
  await expect(s.get("/0/0.0.0")).rejects.toBeInstanceOf(Stopped);
  expect(s.failure).toBeInstanceOf(Stopped);
  expect(s.bytes).toBe(BUDGET.bytes - 1024 * 1024); // nothing past the budget was counted
  s.bytes = BUDGET.bytes; // none left: no request at all
  const n = asked.length;
  await expect(s.get("/1/0.0.0")).rejects.toBeInstanceOf(Stopped);
  expect(asked).toHaveLength(n);
});

test("the multiscales version and the omero labels are capped", async () => {
  const a = attrs();
  a.multiscales[0].version = "0.4".repeat(1000);
  a.omero.channels[0].label = "L".repeat(10000);
  store.set(".zattrs", new TextEncoder().encode(JSON.stringify(a)));
  const s = new ZarrStore(urlOf, inPage);
  const meta = await openZarr(s);
  expect(JSON.parse(new TextDecoder().decode(await s.get("/.zattrs"))).multiscales[0].version).toBe("0.4");
  expect(meta.names).toEqual(["L".repeat(64), "GFP"]);
  store.set(".zattrs", new TextEncoder().encode(JSON.stringify({ ...a, multiscales: [{ ...a.multiscales[0], version: { nested: [1, 2, 3] } }] })));
  const t = new ZarrStore(urlOf, inPage);
  await openZarr(t);
  expect(JSON.parse(new TextDecoder().decode(await t.get("/.zattrs"))).multiscales[0].version).toBe("0.4");
});
