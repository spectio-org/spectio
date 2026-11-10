// The decoding side of the TIFF reader (FU-P3-102d2; api §5.3.1, dev-env §15.3 req. 19): the
// compression allow-list, the decoders capped at the tile's declared size, and the pool of our own
// decoder workers (one decode per message, an error answer, the 10 s end). The fixtures are crafted
// here: a Deflate bomb, an over-long LZW stream, PackBits and JPEG tiles that decode past the tile.
import { fromArrayBuffer, type Pool } from "geotiff";
import { deflate } from "pako";
import { afterEach, expect, test, vi } from "vitest";
import { NotDecoded, answer, decodeTile, geotiffs } from "./decode";
import { DECODE_TIMEOUT, DecoderPool } from "./pool";

const tile = (Compression: number, side = 16, extra: Record<string, unknown> = {}) => ({ Compression, TileWidth: side, TileLength: side, BitsPerSample: [8], SamplesPerPixel: 1, ...extra });
const buf = (bytes: ArrayLike<number>) => new Uint8Array(bytes).buffer;
const pattern = (n: number) => Uint8Array.from({ length: n }, (_, i) => (i * 7) % 13);

/** A TIFF LZW stream (MSB first, the early change of TIFF 6.0 §13), without clear codes: small inputs only. */
function lzw(data: Uint8Array): Uint8Array {
  const out: number[] = [];
  let [acc, held, width, next, prefix] = [0, 0, 9, 258, -1];
  const emit = (code: number) => {
    acc = (acc << width) | code;
    for (held += width; held >= 8; held -= 8) out.push((acc >>> (held - 8)) & 255);
    acc &= (1 << held) - 1;
  };
  const dict = new Map<number, number>();
  emit(256);
  for (const b of data) {
    const hit = prefix < 0 ? b : dict.get(prefix * 256 + b);
    if (hit !== undefined) prefix = hit;
    else {
      emit(prefix);
      dict.set(prefix * 256 + b, next++);
      if (next >= 1 << width) width++;
      prefix = b;
    }
  }
  emit(prefix);
  if (++next >= 1 << width) width++;
  emit(257);
  if (held) out.push((acc << (8 - held)) & 255);
  return Uint8Array.from(out);
}

/** A JPEG of one 8-bit component: DQT, then one SOF0 per `frames` entry (height x width), no scan. */
const jpeg = (...frames: [number, number][]) =>
  buf([0xff, 0xd8, 0xff, 0xdb, 0, 67, 0, ...Array(64).fill(1), ...frames.flatMap(([h, w]) => [0xff, 0xc0, 0, 11, 8, h >> 8, h & 255, w >> 8, w & 255, 1, 1, 0x11, 0]), 0xff, 0xd9]);

/** What geotiff 2.1.3's own decoder writes for this tile. */
const original = async (fd: Record<string, unknown>, data: ArrayBuffer) => new (await geotiffs[fd.Compression as number])(fd).decodeBlock(data).byteLength;

test("only the allow-listed compressions are decoded", async () => {
  for (const code of [6, 34887, 50001, 2, 99]) await expect(decodeTile(tile(code), buf([0]))).rejects.toThrow(`compression ${code} is not supported`);
  expect(new Uint8Array(await decodeTile(tile(1, 2), buf([1, 2, 3, 4])))).toEqual(new Uint8Array([1, 2, 3, 4]));
});

test("Deflate stops at the tile's declared size: a 64 MiB bomb in a 16 x 16 tile is refused", async () => {
  const bomb = deflate(new Uint8Array(64 * 1024 * 1024));
  expect(bomb.byteLength).toBeLessThan(128 * 1024);
  for (const code of [8, 32946]) await expect(decodeTile(tile(code), bomb.buffer as ArrayBuffer)).rejects.toThrow("decodes past the tile's 256 bytes");
  expect(new Uint8Array(await decodeTile(tile(8), deflate(pattern(256)).buffer as ArrayBuffer))).toEqual(pattern(256));
  await expect(decodeTile(tile(8), buf([1, 2, 3]))).rejects.toThrow("the Deflate data is corrupt");
});

test("LZW is geotiff's own decoder, held to the tile's declared size", async () => {
  const stream = lzw(pattern(1000));
  expect(await original(tile(5), stream.slice().buffer)).toBe(1000); // geotiff alone writes past the tile
  await expect(decodeTile(tile(5), stream.slice().buffer)).rejects.toThrow("decodes past the tile's 256 bytes");
  const exact = Uint8Array.from({ length: 4096 }, () => Math.floor(Math.random() * 4));
  expect(new Uint8Array(await decodeTile(tile(5, 64), lzw(exact).buffer as ArrayBuffer))).toEqual(exact);
  await expect(decodeTile(tile(5), buf([0x96, 0x00]))).rejects.toThrow("the LZW data is corrupt"); // a first code of 300, past the dictionary: geotiff alone loops
});

test("PackBits is bounded by its run headers, not the tile: held to the declared size", async () => {
  const runs = buf(Array(4).fill([0x81, 7]).flat()); // 4 runs of 128 bytes from 8 bytes
  expect(await original(tile(32773), runs)).toBe(512);
  await expect(decodeTile(tile(32773), runs)).rejects.toThrow("decodes past the tile's 256 bytes");
  expect(new Uint8Array(await decodeTile(tile(32773, 2), buf([0xfe, 9, 0, 5])))).toEqual(new Uint8Array([9, 9, 9, 5]));
});

test("JPEG output is its own frame's size, not the tile's: a larger frame or a second one is refused", async () => {
  expect(await original(tile(7), jpeg([64, 64]))).toBe(4096); // geotiff alone: 64 x 64 from a 16 x 16 tile
  await expect(decodeTile(tile(7), jpeg([64, 64]))).rejects.toThrow("decodes past the tile's 256 bytes");
  await expect(decodeTile(tile(7), jpeg([16, 16], [16, 16]))).rejects.toThrow("more than one JPEG frame");
  await expect(decodeTile(tile(7, 16, { JPEGTables: new Uint8Array(jpeg([16, 16])) }), jpeg([16, 16]))).rejects.toThrow("more than one JPEG frame");
  expect((await decodeTile(tile(7), jpeg([16, 16]))).byteLength).toBe(256);
});

test("the worker's answer: the decoded tile with its id, or the reason", async () => {
  const ok = await answer({ id: 3, fileDirectory: tile(1, 1), buffer: buf([5]) });
  expect(ok.message).toEqual({ id: 3, decoded: buf([5]) });
  expect(ok.transfer).toHaveLength(1);
  expect((await answer({ id: 4, fileDirectory: tile(6), buffer: buf([0]) })).message).toEqual({ id: 4, error: "compression 6 is not supported" });
});

/** A worker run in this thread: it answers as decoder.worker.ts does, unless `hang`. */
class FakeWorker {
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  terminated = false;
  sent = 0;
  constructor(private readonly hang = false) {}
  postMessage(data: Parameters<typeof answer>[0]) {
    this.sent++;
    if (!this.hang) void answer(data).then(({ message }) => this.onmessage?.({ data: message } as MessageEvent));
  }
  terminate() {
    this.terminated = true;
  }
}

afterEach(() => vi.useRealTimers());

test("the pool sends one decode per message to idle workers, and answers an error as NotDecoded", async () => {
  const workers: FakeWorker[] = [];
  const pool = new DecoderPool(2, () => (workers.push(new FakeWorker()), workers.at(-1) as unknown as Worker));
  const all = [1, 2, 3].map((n) => pool.decode(tile(1, 1), buf([n])));
  expect(workers.map((w) => w.sent)).toEqual([1, 1]); // the third waits for an idle worker
  expect((await Promise.all(all)).map((b) => new Uint8Array(b)[0])).toEqual([1, 2, 3]);
  const refused = pool.decode(tile(34887), buf([0]));
  await expect(refused).rejects.toBeInstanceOf(NotDecoded);
  await expect(refused).rejects.toThrow("compression 34887 is not supported");
  pool.destroy();
  expect(workers.every((w) => w.terminated)).toBe(true);
});

test("a decode past 10 s ends: the worker is terminated and replaced", async () => {
  vi.useFakeTimers();
  const workers: FakeWorker[] = [];
  const pool = new DecoderPool(1, () => (workers.push(new FakeWorker(workers.length === 0)), workers.at(-1) as unknown as Worker));
  const hung = pool.decode(tile(1, 1), buf([1]));
  const queued = pool.decode(tile(1, 1), buf([2]));
  vi.advanceTimersByTime(DECODE_TIMEOUT - 1);
  expect(workers[0].terminated).toBe(false);
  vi.advanceTimersByTime(1);
  await expect(hung).rejects.toThrow("decoding took over 10 s");
  expect(workers[0].terminated).toBe(true);
  expect(new Uint8Array(await queued)).toEqual(new Uint8Array([2])); // on the replacement
  expect(workers).toHaveLength(2);
});

test("a crafted TIFF whose Deflate strip is a bomb ends in NotDecoded through geotiff and the pool", async () => {
  const data = deflate(new Uint8Array(16 * 1024 * 1024));
  const tags: [number, number, number][] = [[256, 4, 16], [257, 4, 16], [258, 3, 8], [259, 3, 8], [262, 3, 1], [273, 4, 0], [277, 3, 1], [278, 4, 16], [279, 4, data.byteLength]];
  const at = 8 + 2 + tags.length * 12 + 4;
  const bytes = new Uint8Array(at + data.byteLength);
  const view = new DataView(bytes.buffer);
  bytes.set([0x49, 0x49, 0x2a, 0, 8, 0, 0, 0]);
  view.setUint16(8, tags.length, true);
  tags.forEach(([tag, type, value], i) => {
    view.setUint16(10 + i * 12, tag, true);
    view.setUint16(12 + i * 12, type, true);
    view.setUint32(14 + i * 12, 1, true);
    if (type === 3) view.setUint16(18 + i * 12, value, true);
    else view.setUint32(18 + i * 12, tag === 273 ? at : value, true);
  });
  bytes.set(data, at);
  const image = await (await fromArrayBuffer(bytes.buffer)).getImage();
  const pool = new DecoderPool(1, () => new FakeWorker() as unknown as Worker);
  await expect(image.readRasters({ pool: pool as unknown as Pool })).rejects.toThrow("decodes past the tile's 256 bytes");
  pool.destroy();
});
