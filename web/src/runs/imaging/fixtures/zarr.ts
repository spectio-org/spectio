// Crafted OME-Zarr stores for the store's tests (FU-P3-102g; dev-env §15.3 req. 19 Tests),
// generated here rather than committed as binaries: a small valid Zarr v2 image (2 channels, two
// levels, Blosc chunks made by numcodecs' own encoder) and the malicious variants of req. 19.
import Blosc from "numcodecs/blosc";

export type Store = Map<string, Uint8Array>;
const MIB = 1024 * 1024;
const json = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));
const zarray = (shape: number[], chunks: number[], more: Record<string, unknown> = {}) =>
  json({ zarr_format: 2, shape, chunks, dtype: "<u2", compressor: { id: "blosc", cname: "lz4", clevel: 5, shuffle: 1, blocksize: 0 }, fill_value: 0, order: "C", filters: null, ...more });
export const attrs = (paths = ["0", "1"], extra: Record<string, unknown> = {}) => ({
  multiscales: [{ version: "0.4", axes: [{ name: "c", type: "channel" }, { name: "y", type: "space" }, { name: "x", type: "space" }], datasets: paths.map((path) => ({ path })) }],
  omero: { channels: [{ label: "DAPI", color: "0000FF" }, { label: "GFP", color: "00FF00" }] },
  ...extra,
});

/** One chunk of `n` uint16 values (value i = i), Blosc-compressed. */
export async function chunk(n: number): Promise<Uint8Array> {
  const values = new Uint16Array(n).map((_, i) => i);
  return Blosc.fromConfig({ id: "blosc", cname: "lz4", clevel: 5, shuffle: 1, blocksize: 0 }).encode(new Uint8Array(values.buffer)) as Promise<Uint8Array>;
}

/** A valid image: level 0 is 2 x 10 x 12 (chunks 1 x 10 x 12), level 1 is 2 x 5 x 6
 * (no side of 3 or 4, which Viv takes for interleaved samples). */
export async function valid(): Promise<Store> {
  const store: Store = new Map([
    [".zgroup", json({ zarr_format: 2 })],
    [".zattrs", json(attrs())],
    ["0/.zarray", zarray([2, 10, 12], [1, 10, 12])],
    ["1/.zarray", zarray([2, 5, 6], [1, 5, 6])],
  ]);
  for (const c of [0, 1]) {
    store.set(`0/${c}.0.0`, await chunk(120));
    store.set(`1/${c}.0.0`, await chunk(30));
  }
  return store;
}

const padded = (bytes: number) => new Uint8Array(bytes).fill(0x20); // spaces: valid JSON whitespace, over the cap

/** The malicious variants of req. 19, each from the valid store. */
export const crafted: Record<string, (s: Store) => void> = {
  "a chunk shape of 10^9": (s) => s.set("0/.zarray", zarray([1, 100000, 10000], [1, 100000, 10000])),
  "a multiscales path with ..": (s) => s.set(".zattrs", json(attrs(["0", "../other.ome.zarr/0"]))),
  "a multiscales path with https://": (s) => s.set(".zattrs", json(attrs(["0", "https://example.org/x.zarr/0"]))),
  "a 1 MiB + 1 .zattrs": (s) => s.set(".zattrs", new Uint8Array([...json(attrs()), ...padded(MIB + 1)]).slice(0, MIB + 1)),
  "a 1 MiB + 1 .zgroup": (s) => s.set(".zgroup", new Uint8Array([...json({ zarr_format: 2 }), ...padded(MIB + 1)]).slice(0, MIB + 1)),
  "a .zattrs with __proto__ and constructor keys only": (s) =>
    s.set(".zattrs", new TextEncoder().encode(`{"__proto__": ${JSON.stringify(attrs())}, "constructor": {"prototype": {"polluted": 1}}}`)),
  "a zstd compressor": (s) => s.set("0/.zarray", zarray([2, 10, 12], [1, 10, 12], { compressor: { id: "zstd", level: 1 } })),
  "33 levels": (s) => s.set(".zattrs", json(attrs(Array.from({ length: 33 }, (_, i) => String(i))))),
  "no multiscales": (s) => s.set(".zattrs", json({ omero: {} })),
  "a plate": (s) => s.set(".zattrs", json({ plate: { rows: [] } })),
  "a float64 array": (s) => s.set("0/.zarray", zarray([2, 10, 12], [1, 10, 12], { dtype: "<f8" })),
};
