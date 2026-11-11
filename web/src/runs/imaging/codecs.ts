// The Zarr v2 chunk decoders (FU-P3-102h; dev-env §15.3 req. 19 Malicious Zarr), run in our
// decoder worker. numcodecs 0.3.2 runs its Blosc, LZ4 and zstd glue through `Function`, which the
// CSP refuses (inbox #150), so these are ours, in JavaScript: Blosc 1 (c-blosc 1.21 `blosc.c`
// `blosc_d` and `blosc_run_decompression_with_context`) with blosclz (`blosclz.c`
// `blosclz_decompress`), LZ4, zlib and zstd inside, byte and bit shuffle; numcodecs' LZ4 (a 4-byte
// little-endian size, then one LZ4 block); zstd through fzstd 0.1.1 (MIT, https://github.com/101arrowz/fzstd;
// pinned and listed in dev-env §15.3 req. 19 and THIRD_PARTY_NOTICES.txt). Every output is held to the
// level's decoded size, read from the header before decode; anything else is NotDecoded.
import { Decompress } from "fzstd";
import { type Fd, NotDecoded, answer, decodeTile, inflate } from "./decode";

const WINDOW_MAX = 64 * 1024 * 1024; // a zstd window, as the largest decoded chunk

export type Chunk = { compressor: string | null; bytes: number };

const lying = (n: number, bytes: number) => new NotDecoded(`the chunk holds ${n} bytes, not ${bytes}`);
const past = (max: number) => new NotDecoded(`the chunk decodes past its ${max} bytes`);
const u32 = (d: Uint8Array, at: number) => (d[at] | (d[at + 1] << 8) | (d[at + 2] << 16) | (d[at + 3] << 24)) >>> 0;

/** One LZ4 block into `out` from `at`, at most `max` bytes; the bytes written. */
function lz4Block(d: Uint8Array, out: Uint8Array, at = 0, max = out.length - at): number {
  const corrupt = () => new NotDecoded("the LZ4 data is corrupt");
  const end = at + max;
  let [ip, op] = [0, at];
  const length = (n: number) => {
    if (n === 15)
      for (let b = 255; b === 255; n += b) {
        if (ip >= d.length) throw corrupt();
        b = d[ip++];
      }
    return n;
  };
  while (ip < d.length) {
    const token = d[ip++];
    const literals = length(token >> 4);
    if (ip + literals > d.length) throw corrupt();
    if (op + literals > end) throw past(max);
    out.set(d.subarray(ip, ip + literals), op);
    [ip, op] = [ip + literals, op + literals];
    if (ip === d.length) break; // the last sequence: literals only
    if (ip + 2 > d.length) throw corrupt();
    const offset = d[ip] | (d[ip + 1] << 8);
    ip += 2;
    if (offset === 0 || offset > op - at) throw corrupt();
    const match = length(token & 15) + 4;
    if (op + match > end) throw past(max);
    for (let k = 0; k < match; k++, op++) out[op] = out[op - offset];
  }
  return op - at;
}

/** blosclz into `out` from `at`, at most `max` bytes; the bytes written (c-blosc's checks). */
function blosclz(d: Uint8Array, out: Uint8Array, at: number, max: number): number {
  const corrupt = () => new NotDecoded("the blosclz data is corrupt");
  const end = at + max;
  let [ip, op] = [0, at];
  let ctrl = d[ip++] & 31;
  for (;;) {
    if (ctrl >= 32) {
      let len = (ctrl >> 5) - 1;
      let ofs = (ctrl & 31) << 8;
      if (len === 6)
        for (let code = 255; code === 255; len += code) {
          if (ip + 1 >= d.length) throw corrupt();
          code = d[ip++];
        }
      else if (ip + 1 >= d.length) throw corrupt();
      const code = d[ip++];
      len += 3;
      let distance = ofs + code + 1;
      if (code === 255 && ofs === 31 << 8) {
        if (ip + 1 >= d.length) throw corrupt();
        ofs = (d[ip] << 8) | d[ip + 1];
        ip += 2;
        distance = ofs + 8191 + 1;
      }
      if (op + len > end) throw past(max);
      if (op - distance < at) throw corrupt();
      if (ip >= d.length) break; // as c-blosc: the stream ends before this match is copied
      ctrl = d[ip++];
      for (let k = 0; k < len; k++, op++) out[op] = out[op - distance];
    } else {
      ctrl++;
      if (op + ctrl > end) throw past(max);
      if (ip + ctrl > d.length) throw corrupt();
      out.set(d.subarray(ip, ip + ctrl), op);
      [ip, op] = [ip + ctrl, op + ctrl];
      if (ip >= d.length) break;
      ctrl = d[ip++];
    }
  }
  return op - at;
}

/** One zstd frame that gives its content size, `bytes`, with a window of at most 64 MiB. */
function zstd(d: Uint8Array, bytes: number): Uint8Array {
  const cut = () => new NotDecoded("the zstd data is cut off");
  if (d.length < 6 || u32(d, 0) !== 0xfd2fb528 || d[4] & 8) throw new NotDecoded("the zstd data is corrupt");
  const [fcf, single, checksum, dict] = [d[4] >> 6, (d[4] >> 5) & 1, (d[4] >> 2) & 1, d[4] & 3];
  if (dict) throw new NotDecoded("zstd dictionaries are not supported");
  if (!fcf && !single) throw new NotDecoded("the zstd frame does not give its size");
  const sizeBytes = fcf ? 1 << fcf : 1;
  let at = 5 + (single ? 0 : 1);
  if (at + sizeBytes > d.length) throw cut();
  let size = 0;
  for (let k = sizeBytes - 1; k >= 0; k--) size = size * 256 + d[at + k];
  if (fcf === 1) size += 256;
  const window = single ? size : 2 ** (10 + (d[5] >> 3)) * (1 + (d[5] & 7) / 8);
  if (window > WINDOW_MAX) throw new NotDecoded("the zstd window is over 64 MiB");
  if (size !== bytes) throw lying(size, bytes);
  // its blocks, by their headers: one frame, ending where the chunk ends
  for (at += sizeBytes; ; ) {
    if (at + 3 > d.length) throw cut();
    const header = d[at] | (d[at + 1] << 8) | (d[at + 2] << 16);
    if (((header >> 1) & 3) === 3) throw new NotDecoded("the zstd data is corrupt");
    at += 3 + (((header >> 1) & 3) === 1 ? 1 : header >> 3);
    if (header & 1) break;
  }
  at += checksum * 4;
  if (at < d.length) throw new NotDecoded("more than one zstd frame");
  if (at > d.length) throw cut();
  const out = new Uint8Array(bytes);
  let op = 0;
  const stream = new Decompress((block) => {
    if (op + block.length > bytes) throw past(bytes);
    out.set(block, op);
    op += block.length;
  });
  stream.push(d, true);
  if (op !== bytes) throw lying(op, bytes);
  return out;
}

const SHUFFLE = 1;
const MEMCPYED = 2;
const BITSHUFFLE = 4;
const DONT_SPLIT = 0x10;
const INNER = ["blosclz", "lz4", "snappy", "zlib", "zstd"];

/** One split of a Blosc block into `out` at `at`, `n` bytes exactly. */
function split(codec: number, d: Uint8Array, out: Uint8Array, at: number, n: number) {
  let written: number;
  if (codec === 0) written = blosclz(d, out, at, n);
  else if (codec === 1) written = lz4Block(d, out, at, n);
  else {
    const whole = codec === 3 ? new Uint8Array(inflate(d.slice().buffer, n)) : zstd(d, n);
    out.set(whole, at);
    written = whole.length;
  }
  if (written !== n) throw new NotDecoded("the Blosc data is corrupt");
}

/** Blosc's byte shuffle undone: byte j of every value is a run of `n / size` bytes. */
function unshuffle(src: Uint8Array, size: number): Uint8Array {
  const out = src.slice();
  const count = Math.floor(src.length / size);
  for (let j = 0; j < size; j++) for (let i = 0; i < count; i++) out[i * size + j] = src[j * count + i];
  return out;
}

/** Blosc's bit shuffle undone (bitshuffle's layout, c-blosc `bitshuffle-generic.c`): bit k of byte
 * j of every value is a row of `count / 8` bytes; blocks of a count not a multiple of 8 are stored as is. */
function bitunshuffle(src: Uint8Array, size: number): Uint8Array {
  const count = Math.floor(src.length / size);
  if (count % 8) return src;
  const out = src.slice();
  out.fill(0, 0, count * size);
  const row = count / 8;
  for (let j = 0; j < size; j++)
    for (let k = 0; k < 8; k++) {
      const base = (j * 8 + k) * row;
      for (let i = 0; i < count; i++) out[i * size + j] |= ((src[base + (i >> 3)] >> (i & 7)) & 1) << k;
    }
  return out;
}

/** A Blosc 1 chunk of `bytes` decoded bytes (header format: c-blosc README_HEADER.rst). */
function blosc(d: Uint8Array, bytes: number): Uint8Array {
  const corrupt = () => new NotDecoded("the Blosc data is corrupt");
  if (d.length < 16) throw new NotDecoded("the Blosc header is cut off");
  const [version, codecVersion, flags, typesize] = d;
  const [nbytes, blocksize, cbytes] = [u32(d, 4), u32(d, 8), u32(d, 12)];
  if (version !== 2) throw new NotDecoded(`the Blosc version ${version} is not supported`);
  if (nbytes !== bytes) throw lying(nbytes, bytes);
  if (cbytes > d.length) throw new NotDecoded("the Blosc data is cut off");
  if (cbytes < 16 || flags & 8 || !typesize) throw corrupt();
  if (!nbytes) return new Uint8Array();
  if (!blocksize || blocksize > nbytes) throw new NotDecoded("the Blosc block size is not valid");
  d = d.subarray(0, cbytes);
  if (flags & MEMCPYED) {
    if (cbytes !== 16 + nbytes) throw corrupt();
    return d.slice(16);
  }
  const codec = flags >> 5;
  if (codec === 2 || codec >= INNER.length) throw new NotDecoded(`blosc ${INNER[codec] ?? `codec ${codec}`} is not supported`);
  if (codecVersion !== 1) throw corrupt();
  const blocks = Math.ceil(nbytes / blocksize);
  if (16 + 4 * blocks > cbytes) throw corrupt();
  const out = new Uint8Array(nbytes);
  for (let b = 0; b < blocks; b++) {
    const size = Math.min(blocksize, nbytes - b * blocksize);
    const leftover = size < blocksize;
    // c-blosc writes split blocks in multiples of typesize; any other is one stream (CR-P3FU102H-05)
    const splits = !(flags & DONT_SPLIT) && typesize <= 16 && size / typesize >= 128 && size % typesize === 0 && !leftover ? typesize : 1;
    const block = new Uint8Array(size);
    let at = u32(d, 16 + 4 * b);
    for (let s = 0; s < splits; s++) {
      if (at < 16 + 4 * blocks || at + 4 > cbytes) throw corrupt();
      const n = u32(d, at);
      at += 4;
      if (n > cbytes - at) throw corrupt();
      const part = size / splits;
      if (n === part) block.set(d.subarray(at, at + n), s * part);
      else split(codec, d.subarray(at, at + n), block, s * part, part);
      at += n;
    }
    const plain = flags & SHUFFLE && typesize > 1 ? unshuffle(block, typesize) : flags & BITSHUFFLE && size >= typesize ? bitunshuffle(block, typesize) : block;
    out.set(plain, b * blocksize);
  }
  return out;
}

/** A chunk of `bytes` decoded bytes, as its level's compressor wrote it; raw chunks are held to that size. */
export function decodeChunk({ compressor, bytes }: Chunk, buffer: ArrayBuffer): ArrayBuffer {
  const d = new Uint8Array(buffer);
  let out: Uint8Array;
  try {
    if (compressor === null || compressor === "none") out = d;
    else if (compressor === "zlib" || compressor === "gzip") out = new Uint8Array(inflate(buffer, bytes));
    else if (compressor === "blosc") out = blosc(d, bytes);
    else if (compressor === "zstd") out = zstd(d, bytes);
    else if (compressor === "lz4") {
      if (d.length < 4) throw new NotDecoded("the LZ4 data is cut off");
      if (u32(d, 0) !== bytes) throw lying(u32(d, 0), bytes);
      out = new Uint8Array(bytes);
      const n = lz4Block(d.subarray(4), out);
      if (n !== bytes) throw lying(n, bytes);
    } else throw new NotDecoded(`compressor ${compressor} is not supported`);
  } catch (err) {
    throw err instanceof NotDecoded ? err : new NotDecoded(`the ${compressor} data is corrupt`);
  }
  if (out.byteLength !== bytes) throw lying(out.byteLength, bytes);
  return out.byteOffset === 0 && out.byteLength === out.buffer.byteLength ? (out.buffer as ArrayBuffer) : (out.slice().buffer as ArrayBuffer);
}

/** The worker's answer to one message of the pool: a Zarr chunk, or a TIFF tile. */
export const reply = (data: Parameters<typeof answer>[0] & { kind?: string }) =>
  answer(data, data.kind === "chunk" ? (fd: Fd, buffer: ArrayBuffer) => decodeChunk(fd as unknown as Chunk, buffer) : decodeTile);
