// The decoding side of the TIFF reader (FU-P3-102d2; api §5.3.1, dev-env §15.3 req. 19), run in
// our own decoder worker: the compression allow-list, and every decoder held to the tile's
// declared size (width x height x bytes per pixel), checked before or while it writes.
import { BaseDecoder, addDecoder, getDecoder } from "geotiff";
import { Inflate } from "pako";

/** A tile not decoded; `reason` is shown with the "could not be decoded" state (ui-spec §4.4.1). */
export class NotDecoded extends Error {}

// none, LZW, JPEG, Deflate (both codes), PackBits; old JPEG, LERC, WebImage and the rest refused
export const ALLOWED = new Set([1, 5, 7, 8, 32946, 32773]);

export type Fd = Record<string, unknown>;
const many = (value: unknown): number[] => (value === undefined ? [] : ArrayBuffer.isView(value) || Array.isArray(value) ? Array.from(value as ArrayLike<number>) : [Number(value)]);
const num = (fd: Fd, name: string) => Number(fd[name]);

/** The width and rows of a tile (or a strip of RowsPerStrip rows). */
function extent(fd: Fd): [number, number] {
  const tiled = fd.TileWidth !== undefined;
  const width = num(fd, tiled ? "TileWidth" : "ImageWidth");
  return [width, tiled ? num(fd, "TileLength") : Math.min(num(fd, "RowsPerStrip") || Infinity, num(fd, "ImageLength"))];
}

/** The bytes a tile (or a strip of RowsPerStrip rows) holds once decoded. */
export function declaredSize(fd: Fd): number {
  const [width, rows] = extent(fd);
  const samples = num(fd, "SamplesPerPixel") || 1;
  const listed = many(fd.BitsPerSample);
  const bits = listed.length > 1 ? listed : Array<number>(samples).fill(listed[0] ?? 1);
  const pixel = fd.PlanarConfiguration === 2 ? Math.max(...bits) : bits.reduce((a, b) => a + b, 0);
  const size = Math.ceil((width * pixel) / 8) * rows;
  if (!Number.isSafeInteger(size) || size <= 0) throw new NotDecoded("the tile has no size");
  return size;
}

const past = (max: number) => new NotDecoded(`the tile decodes past the tile's ${max} bytes`);

// geotiff's own decoders, taken before ours replace them: getDecoder reads its registry before
// its first await, so these calls get geotiff 2.1.3's LZW, PackBits and JPEG classes.
type DecoderClass = new (fd: Fd) => { decodeBlock(buffer: ArrayBuffer): ArrayBuffer };
export const geotiffs = Object.fromEntries([5, 7, 32773].map((Compression) => [Compression, getDecoder({ Compression }).then((d) => d.constructor as DecoderClass)]));

/** A decoder of `fd`'s tiles, capped at their declared size; predictors are applied by BaseDecoder. */
function capped(check: (data: Uint8Array, max: number, fd: Fd) => void, Original?: Promise<DecoderClass>) {
  return async () => {
    const Decoder = Original && (await Original);
    return class extends BaseDecoder {
      constructor(readonly fd: Fd) {
        super();
      }
      decodeBlock(buffer: ArrayBuffer): ArrayBuffer {
        const max = declaredSize(this.fd);
        check(new Uint8Array(buffer), max, this.fd);
        return Decoder ? new Decoder(this.fd).decodeBlock(buffer) : inflate(buffer, max);
      }
    };
  };
}

/** A chunked inflate that stops at the first chunk past `max`. */
export function inflate(buffer: ArrayBuffer, max: number): ArrayBuffer {
  const out = new Uint8Array(max);
  let at = 0;
  const inflator = new Inflate({ chunkSize: 64 * 1024 });
  inflator.onData = (chunk: Uint8Array) => {
    if (at + chunk.byteLength > max) throw past(max);
    out.set(chunk, at);
    at += chunk.byteLength;
  };
  inflator.push(new Uint8Array(buffer), true);
  if (inflator.err || !inflator.ended) throw new NotDecoded("the Deflate data is corrupt");
  return at === max ? out.buffer : out.slice(0, at).buffer;
}

/** geotiff 2.1.3 `compression/lzw.js` `getByte`: `length` bits from `position`, MSB first. */
function getByte(array: Uint8Array, position: number, length: number): number {
  const [a, d] = [Math.floor(position / 8), position % 8];
  if (a >= array.length) return 257; // geotiff reads past the end as the end of information
  let chunks = (array[a] & (2 ** (8 - d) - 1)) << (length - (8 - d));
  if (a + 1 < array.length) chunks += (array[a + 1] >>> Math.max(0, 8 * (a + 2) - (position + length))) << Math.max(0, length - ((a + 2) * 8 - position));
  if (position + length - (a + 1) * 8 > 8 && a + 2 < array.length) chunks += array[a + 2] >>> ((a + 3) * 8 - (position + length));
  return chunks;
}

/** The length geotiff's LZW decoder writes, counted code by code as it would read them (its
 * `decompress`, entry lengths only); refused past `max`, and where geotiff would throw or loop. */
export function lzwLength(input: Uint8Array, max: number): number {
  const lengths = new Uint16Array(4093).fill(1, 0, 258); // geotiff's dictionary arrays hold 4093
  let [size, width, position, total] = [258, 9, 0, 0];
  let old: number | undefined;
  const next = () => ((position += width), getByte(input, position - width, width));
  const corrupt = () => new NotDecoded("the LZW data is corrupt");
  for (let code = next(); code !== 257; code = next()) {
    if (code === 256) {
      [size, width] = [258, 9];
      while ((code = next()) === 256);
      if (code === 257) break;
      if (code > 256) throw corrupt();
      total += 1;
      old = code;
    } else if (code < size) {
      if (code >= 4093) throw corrupt();
      total += lengths[code];
      if (size < 4093) lengths[size] = lengths[old ?? 0] + 1; // an undefined old code reads as 0
      size++;
      old = code;
    } else {
      // only the next entry (KwKwK): a code past it would make geotiff link entries into a cycle
      if (old === undefined || code !== size || code >= 4093) throw corrupt();
      total += lengths[old] + 1;
      if (size < 4093) lengths[size] = lengths[old] + 1;
      size++;
      old = code;
    }
    if (total > max) throw past(max);
    if (size + 1 >= 2 ** width) width === 12 ? (old = undefined) : width++;
  }
  return total;
}

/** geotiff's PackBits writes header + 1 bytes per run or literal, whatever the tile. */
function packBitsLength(input: Uint8Array, max: number) {
  let total = 0;
  for (let i = 0; i < input.length; i++) {
    const header = (input[i] << 24) >> 24;
    total += Math.abs(header) + 1;
    i += header < 0 ? 1 : header + 1;
    if (total > max) throw past(max);
  }
}

/** geotiff's JPEG writes its frame's width x height x components, and allocates every frame it
 * meets (in JPEGTables and the tile), 256 bytes per block rounded up to whole MCUs (its
 * `prepareComponents`): so a frame is held to the tile's extent and samples, sampling 1 to 4.
 * Any 0xFF 0xC0-0xC2 pair counts as a frame: entropy-coded data never holds one, so this sees
 * every frame geotiff can (a pair inside another segment refuses). */
function jpegFrames(tile: Uint8Array, max: number, fd: Fd) {
  const [tileWidth, rows] = extent(fd);
  const samples = fd.PlanarConfiguration === 2 ? 1 : num(fd, "SamplesPerPixel") || 1;
  const mismatch = () => new NotDecoded("the JPEG frame does not match the tile");
  let frames = 0;
  for (const data of [fd.JPEGTables ? new Uint8Array(fd.JPEGTables as ArrayLike<number>) : new Uint8Array(), tile])
    for (let i = 0; i + 9 < data.length; i++) {
      if (data[i] !== 0xff || data[i + 1] < 0xc0 || data[i + 1] > 0xc2) continue;
      if (++frames > 1) throw new NotDecoded("more than one JPEG frame");
      const [lines, width, components] = [(data[i + 5] << 8) | data[i + 6], (data[i + 7] << 8) | data[i + 8], data[i + 9]];
      if (lines * width * components > max) throw past(max);
      if (width > tileWidth || lines > rows || components > samples || i + 10 + 3 * components > data.length) throw mismatch();
      for (let k = 0; k < components; k++) {
        const [h, v] = [data[i + 11 + 3 * k] >> 4, data[i + 11 + 3 * k] & 15];
        if (h < 1 || h > 4 || v < 1 || v > 4) throw mismatch();
      }
    }
}

/** Our capped decoders in geotiff's registry; again after Viv's chunk, whose import puts its
 * WebAssembly LZW in their place (@vivjs/loaders 0.23.0 `dist/index.mjs:921`). */
export function registerCapped() {
  addDecoder([8, 32946], capped(() => {}));
  addDecoder(5, capped(lzwLength, geotiffs[5]));
  addDecoder(32773, capped(packBitsLength, geotiffs[32773]));
  addDecoder(7, capped(jpegFrames, geotiffs[7]));
}
registerCapped();

/** One tile, decoded if its compression is allowed, within its declared size. */
export async function decodeTile(fd: Fd, buffer: ArrayBuffer): Promise<ArrayBuffer> {
  const code = fd.Compression ?? 1;
  if (!ALLOWED.has(code as number)) throw new NotDecoded(`compression ${String(code)} is not supported`);
  return (await getDecoder(fd)).decode(fd, buffer);
}

/** The worker's answer to one message of the pool, `{id, decoded}` or `{id, error}`; `decode`
 * is decodeTile, or a Zarr chunk's decoder (codecs.ts `reply`). */
export async function answer({ id, fileDirectory, buffer }: { id: number; fileDirectory: Fd; buffer: ArrayBuffer }, decode: (fd: Fd, buffer: ArrayBuffer) => ArrayBuffer | Promise<ArrayBuffer> = decodeTile) {
  try {
    const decoded = await decode(fileDirectory, buffer);
    return { message: { id, decoded }, transfer: [decoded] };
  } catch (err) {
    return { message: { id, error: err instanceof NotDecoded ? err.message : "the tile could not be decoded" }, transfer: [] };
  }
}
