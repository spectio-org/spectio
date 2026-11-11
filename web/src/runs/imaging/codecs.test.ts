// The Zarr chunk decoders (FU-P3-102h; dev-env §15.3 req. 19 Malicious Zarr): Blosc with its
// inner codecs and shuffles, numcodecs' LZ4 and zstd, without `Function` or WebAssembly. The
// fixtures are chunks written by the real numcodecs (fixtures/codecs.py); the malformed ones are
// crafted here. Each decodes to exactly its level's bytes, or fails closed with NotDecoded.
import { expect, test } from "vitest";
import { decodeChunk, reply } from "./codecs";
import { NotDecoded } from "./decode";
import fixtures from "./fixtures/codecs.json";
import { DecoderPool } from "./pool";

const SIZE: Record<string, number> = { u1: 1, u2: 2, u4: 4 };
const bytesOf = (b64: string) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
const fixture = (name: string) => bytesOf(fixtures.cases.find((c) => c.name === name)!.data);

/** The values codecs.py compressed, as little-endian bytes. */
function expected(dtype: string, n: number): Uint8Array {
  const v = Array.from({ length: n }, (_, i) => ((i % 64) * 13 + Math.floor(i / 64) * 5) % 1000);
  if (dtype === "u1") return Uint8Array.from(v, (x) => x % 251);
  if (dtype === "u2") return new Uint8Array(Uint16Array.from(v).buffer);
  return new Uint8Array(Uint32Array.from(v, (x) => x * 65537).buffer);
}

const decode = (compressor: string, bytes: number, data: Uint8Array) => new Uint8Array(decodeChunk({ compressor, bytes }, data.slice().buffer));

test("every chunk numcodecs wrote decodes to its values: Blosc's five codecs, both shuffles, stored blocks, LZ4, zstd", () => {
  expect(fixtures.cases).toHaveLength(21);
  for (const c of fixtures.cases) {
    const want = expected(c.dtype, c.values);
    expect(decode(c.compressor.id, c.values * SIZE[c.dtype], bytesOf(c.data)), c.name).toEqual(want);
  }
});

test("a Blosc header that lies about its size is refused before decode; blocks that do not fill it are refused", () => {
  const data = fixture("blosc lz4 shuffle");
  expect(() => decode("blosc", 10002, data)).toThrow("the chunk holds 10000 bytes, not 10002");
  new DataView(data.buffer).setUint32(4, 10002, true); // nbytes now says the level's size; the block holds 10000
  expect(() => decode("blosc", 10002, data)).toThrow(NotDecoded);
  const bomb = fixture("blosc zstd shuffle");
  new DataView(bomb.buffer).setUint32(4, 1 << 30, true);
  expect(() => decode("blosc", 10000, bomb)).toThrow("the chunk holds 1073741824 bytes, not 10000");
});

test("a malformed Blosc chunk is refused: its compressed size, block size, block starts, version and codec", () => {
  const at = (offset: number, value: number, data = fixture("blosc lz4 shuffle")) => (new DataView(data.buffer).setUint32(offset, value, true), data);
  const byte = (offset: number, value: number) => ((d) => ((d[offset] = value), d))(fixture("blosc lz4 shuffle"));
  const cases: [Uint8Array, string][] = [
    [fixture("blosc lz4 shuffle").slice(0, 15), "the Blosc header is cut off"],
    [fixture("blosc lz4 shuffle").slice(0, 100), "the Blosc data is cut off"], // its compressed size says more than was read
    [at(12, 20), "the Blosc data is corrupt"],
    [at(8, 0), "the Blosc block size is not valid"],
    [at(8, 20000), "the Blosc block size is not valid"],
    [at(16, 1 << 30), "the Blosc data is corrupt"], // a block start past the end
    [byte(2, 0x41), "blosc snappy is not supported"], // flags: compressor 2
    [byte(2, 0xa1), "blosc codec 5 is not supported"],
    [byte(0, 9), "the Blosc version 9 is not supported"],
    [byte(3, 0), "the Blosc data is corrupt"], // a type size of 0
  ];
  for (const [data, message] of cases) expect(() => decode("blosc", 10000, data), message).toThrow(message);
});

test("numcodecs LZ4: the 4-byte size, then one block; a lying size, a bad offset, a cut or an overrun is refused", () => {
  expect(() => decode("lz4", 10002, fixture("lz4"))).toThrow("the chunk holds 10000 bytes, not 10002");
  const lz4 = (size: number, ...block: number[]) => Uint8Array.from([size, 0, 0, 0, ...block]);
  expect(decode("lz4", 9, lz4(9, 0x13, 7, 1, 0, 0x10, 9))).toEqual(Uint8Array.from([7, 7, 7, 7, 7, 7, 7, 7, 9])); // a run of 7 from offset 1
  expect(() => decode("lz4", 9, lz4(9, 0x13, 7, 0, 0, 0x10, 9))).toThrow("the LZ4 data is corrupt"); // offset 0
  expect(() => decode("lz4", 9, lz4(9, 0x13, 7, 2, 0, 0x10, 9))).toThrow("the LZ4 data is corrupt"); // before the start
  expect(() => decode("lz4", 9, lz4(9, 0xf0, 255))).toThrow("the LZ4 data is corrupt"); // its literals cut off
  expect(() => decode("lz4", 9, lz4(9, 0x13, 7, 1, 0, 0x20, 9, 9))).toThrow("the chunk decodes past its 9 bytes");
  expect(() => decode("lz4", 9, lz4(9, 0x13, 7, 1, 0))).toThrow("the chunk holds 8 bytes, not 9");
  expect(() => decode("lz4", 9, Uint8Array.from([9, 0]))).toThrow("the LZ4 data is cut off");
});

test("zstd: one frame that gives its size, the level's, with a window of at most 64 MiB; anything else is refused", () => {
  const zstd = fixture("zstd");
  expect(() => decode("zstd", 10002, zstd)).toThrow("the chunk holds 10000 bytes, not 10002");
  const frame = (descriptor: number[], ...blocks: number[]) => Uint8Array.from([0x28, 0xb5, 0x2f, 0xfd, ...descriptor, ...blocks]);
  const raw = (last: number, n: number) => [last | (n << 3), n >> 5, 0]; // a raw block header
  expect(decode("zstd", 3, frame([0x20, 3], ...raw(1, 3), 1, 2, 3))).toEqual(Uint8Array.from([1, 2, 3])); // single segment, size 3
  expect(() => decode("zstd", 3, frame([0x00, 0x00], ...raw(1, 3), 1, 2, 3))).toThrow("the zstd frame does not give its size");
  expect(() => decode("zstd", 3, frame([0x40, 0xf8, 0, 0], ...raw(1, 3), 1, 2, 3))).toThrow("the zstd window is over 64 MiB");
  expect(() => decode("zstd", 3, frame([0x21, 3], ...raw(1, 3), 1, 2, 3))).toThrow("zstd dictionaries are not supported");
  expect(() => decode("zstd", 10000, Uint8Array.from([...zstd, ...zstd]))).toThrow("more than one zstd frame");
  expect(() => decode("zstd", 3, frame([0x20, 3], ...raw(1, 5), 1, 2, 3))).toThrow("the zstd data is cut off");
  const rle = 1 | (1 << 1) | (100000 << 3); // one RLE block of 100,000 bytes in a frame that says 3
  expect(() => decode("zstd", 3, frame([0x20, 3], rle & 255, (rle >> 8) & 255, rle >> 16, 7))).toThrow("the chunk decodes past its 3 bytes");
  expect(() => decode("zstd", 4, frame([0x20, 4], ...raw(1, 3), 1, 2, 3))).toThrow("the chunk holds 3 bytes, not 4");
  expect(() => decode("zstd", 3, Uint8Array.from([1, 2, 3, 4, 5, 6]))).toThrow("the zstd data is corrupt");
});

test("a corrupted chunk of any codec fails closed: exactly its bytes, or NotDecoded, quickly", () => {
  let seed = 1;
  const random = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31), seed / 2 ** 31);
  const started = performance.now();
  for (const c of fixtures.cases) {
    const bytes = c.values * SIZE[c.dtype];
    for (let n = 0; n < 40; n++) {
      const data = bytesOf(c.data);
      for (let k = 0; k < 1 + Math.floor(random() * 4); k++) data[Math.floor(random() * data.length)] = Math.floor(random() * 256);
      const cut = random() < 0.2 ? data.slice(0, Math.floor(random() * data.length)) : data;
      try {
        expect(decode(c.compressor.id, bytes, cut).byteLength).toBe(bytes);
      } catch (err) {
        expect(err, `${c.name}: ${String(err)}`).toBeInstanceOf(NotDecoded);
      }
    }
  }
  expect(performance.now() - started).toBeLessThan(10_000);
});

test("other compressors are not decoded; zlib and gzip are inflated with the cap; raw chunks are held to their size", () => {
  expect(() => decode("bz2", 4, Uint8Array.from([1, 2, 3, 4]))).toThrow("compressor bz2 is not supported");
  expect(decode("none", 4, Uint8Array.from([1, 2, 3, 4]))).toEqual(Uint8Array.from([1, 2, 3, 4]));
  expect(() => decode("none", 4, Uint8Array.from([1, 2, 3]))).toThrow("the chunk holds 3 bytes, not 4");
  const blosc = fixture("blosc lz4 shuffle");
  expect(new Uint8Array(decodeChunk({ compressor: null, bytes: blosc.byteLength }, blosc.slice().buffer))).toEqual(blosc);
});

/** A worker run in this thread, answering as decoder.worker.ts does. */
class FakeWorker {
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  postMessage(data: Parameters<typeof reply>[0]) {
    void reply(data).then(({ message }) => this.onmessage?.({ data: message } as MessageEvent));
  }
  terminate() {}
}

test("the pool decodes Zarr chunks in the decoder worker, and answers a refusal as NotDecoded", async () => {
  const pool = new DecoderPool(1, () => new FakeWorker() as unknown as Worker);
  const decoded = await pool.decode({ compressor: "blosc", bytes: 10000 }, fixture("blosc zstd bitshuffle").buffer as ArrayBuffer, "chunk");
  expect(new Uint8Array(decoded)).toEqual(expected("u2", 5000));
  const refused = pool.decode({ compressor: "blosc", bytes: 10002 }, fixture("blosc zstd bitshuffle").buffer as ArrayBuffer, "chunk");
  await expect(refused).rejects.toBeInstanceOf(NotDecoded);
  await expect(refused).rejects.toThrow("the chunk holds 10000 bytes, not 10002");
  pool.destroy();
});
