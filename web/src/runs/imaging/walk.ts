// The IFD walk and the one-file OME-XML check (api §5.3.1, dev-env §15.3 req. 19, FU-P3-102d1).
// The page walks the IFDs itself, before any tile is read: at most 10,000, each offset inside the
// file, each seen once (an offset seen twice is a loop and ends the walk), each within the caps.
import type { GeoTIFF } from "geotiff";
import { MIB } from "../preview";
import { reading, type PinnedClient } from "./client";

export const IFDS_MAX = 10000;
const TILE_SIDE_MAX = 4096;
const STORED_MAX = 8 * MIB; // a tile or strip as stored
const DECODED_MAX = 64 * MIB; // a tile or strip as decoded
const OME_XML_MAX = 4 * MIB;
// geotiff parses every tag of an IFD at once, allocating each one's declared count, so the walk
// reads the entry table itself first (through the charged client) and holds it to these caps.
const ENTRIES_MAX = 1024;
const VALUE_MAX = 8 * MIB; // one tag's values
const IFD_VALUES_MAX = 16 * MIB;
const WALK_VALUES_MAX = 256 * MIB;
const TYPE_LENGTHS: Record<number, number> = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4, 16: 8, 17: 8, 18: 8 };

/** Refused with the "too large" state; `reason` is the state's own words (ui-spec §4.4.1). */
export class TooLarge extends Error {
  constructor(readonly reason: string) {
    super(reason);
  }
}

/** Not a TIFF Spectio can read: the "could not be decoded" state. */
export class Unreadable extends Error {}

/** The tags geotiff 2.1.3 parses, by name; the ones read here only. */
export type FileDirectory = Record<string, unknown> & { ImageWidth?: number; ImageLength?: number; ImageDescription?: string };

const FORMATS: Record<number, string> = { 1: "unsigned", 2: "signed", 3: "float" };
const many = (value: unknown): number[] => (value === undefined ? [] : Array.isArray(value) || ArrayBuffer.isView(value) ? Array.from(value as ArrayLike<number>) : [Number(value)]);

/** A sizing tag as one positive safe integer (geotiff keeps a tag of count != 1 as an array);
 * `fallback` when the tag is absent and may be; anything else is unreadable. */
function scalar(fd: FileDirectory, name: string, fallback?: number): number {
  const value = fd[name];
  if (value === undefined && fallback !== undefined) return fallback;
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value <= 0) throw new Unreadable(`${name} is not one positive integer`);
  return value;
}

/** The caps one IFD is held to before any of its tiles is read. */
function check(fd: FileDirectory) {
  const tiled = fd.TileWidth !== undefined;
  const [tw, tl] = tiled ? [scalar(fd, "TileWidth"), scalar(fd, "TileLength")] : [0, 0];
  if (tw > TILE_SIDE_MAX || tl > TILE_SIDE_MAX) throw new TooLarge("tiles larger than 4,096 px");
  for (const stored of [...many(fd.TileByteCounts), ...many(fd.StripByteCounts)]) if (stored > STORED_MAX) throw new TooLarge("a tile over 8 MiB");
  const samples = scalar(fd, "SamplesPerPixel", 1);
  if (samples > 4) throw new TooLarge(`${samples}-sample pixels are not shown`);
  const bits = many(fd.BitsPerSample);
  const formats = many(fd.SampleFormat);
  for (const list of [bits, formats]) if (list.length > 1 && list.length !== samples) throw new Unreadable(`${list.length} values for ${samples} samples`);
  let widest = 8;
  for (let i = 0; i < samples; i++) {
    const [b, f] = [bits[bits.length > 1 ? i : 0] ?? 1, formats[formats.length > 1 ? i : 0] ?? 1];
    if (![8, 16, 32].includes(b) || !FORMATS[f] || (f === 3 && b !== 32)) throw new TooLarge(`${b}-bit ${FORMATS[f] ?? "undefined"} pixels are not shown`);
    widest = Math.max(widest, b);
  }
  // a tile, or a strip of ImageWidth x RowsPerStrip, decoded: each sample at the widest bits given
  const width = scalar(fd, "ImageWidth");
  const height = scalar(fd, "ImageLength");
  const [w, h] = tiled ? [tw, tl] : [width, Math.min(scalar(fd, "RowsPerStrip", height), height)];
  if (w * h * samples * (widest / 8) > DECODED_MAX) throw new TooLarge("a tile over 64 MiB decoded");
}

type Slice = Awaited<ReturnType<GeoTIFF["getSlice"]>>;
function u64(slice: Slice, at: number): number {
  try {
    return slice.readUint64(at);
  } catch {
    throw new Unreadable("a value past 2^53");
  }
}

/** The bytes of values the IFD at `offset` declares, read from its raw entry table before
 * geotiff parses it; refused when one tag, the IFD, or the table itself is over its cap. */
async function prescan(tiff: GeoTIFF, offset: number, size: number): Promise<number> {
  const [countSize, entrySize, word] = tiff.bigTiff ? [8, 20, 8] : [2, 12, 4];
  if (offset + countSize > size) throw new Unreadable(`an IFD at ${offset}, past the end`);
  const head = await tiff.getSlice(offset, countSize);
  const entries = tiff.bigTiff ? u64(head, offset) : head.readUint16(offset);
  if (entries > ENTRIES_MAX) throw new TooLarge(`over ${ENTRIES_MAX.toLocaleString("en-US")} tags in an IFD`);
  const tableSize = countSize + entries * entrySize + word;
  if (offset + tableSize > size) throw new Unreadable(`an IFD at ${offset}, past the end`);
  const table = await tiff.getSlice(offset, tableSize);
  let total = 0;
  for (let i = 0; i < entries; i++) {
    const at = offset + countSize + i * entrySize;
    const type = table.readUint16(at + 2);
    const count = tiff.bigTiff ? u64(table, at + 4) : table.readUint32(at + 4);
    if (!TYPE_LENGTHS[type]) throw new Unreadable(`a tag of unknown type ${type}`);
    const length = TYPE_LENGTHS[type] * count;
    if (length > VALUE_MAX) throw new TooLarge("a tag over 8 MiB");
    if (length > word) {
      const valueAt = tiff.bigTiff ? u64(table, at + 12) : table.readUint32(at + 8);
      if (valueAt + length > size) throw new Unreadable("a tag's values past the end");
    }
    total += length;
  }
  if (total > IFD_VALUES_MAX) throw new TooLarge("an IFD's tags over 16 MiB");
  return total;
}

/** The IFDs of an opened TIFF (of `client.size` bytes), in order; `loop` when the chain came back. */
export async function walkIfds(tiff: GeoTIFF, client: PinnedClient, max = IFDS_MAX): Promise<{ ifds: FileDirectory[]; loop: boolean }> {
  const size = client.size;
  const seen = new Set<number>();
  const ifds: FileDirectory[] = [];
  let values = 0;
  for (let offset = tiff.firstIFDOffset; offset !== 0; ) {
    if (seen.has(offset)) return { ifds, loop: true };
    if (!Number.isSafeInteger(offset) || offset < 8 || offset + 2 > size) throw new Unreadable(`an IFD at ${offset}, past the end`);
    if (ifds.length >= max) throw new TooLarge(`over ${max.toLocaleString("en-US")} IFDs`);
    seen.add(offset);
    values += await reading(client, () => prescan(tiff, offset, size));
    if (values > WALK_VALUES_MAX) throw new TooLarge("the IFDs' tags over 256 MiB");
    const ifd = await reading(client, () => tiff.parseFileDirectoryAt(offset));
    const fd = ifd.fileDirectory as FileDirectory;
    check(fd);
    ifds.push(fd);
    offset = Number(ifd.nextIFDByteOffset);
  }
  return { ifds, loop: false };
}

/** Whether a first IFD's ImageDescription is OME-XML, and if so whether it names this file only
 * (a `TiffData` whose `UUID` names another file, or more than one file, is refused). Parsed as
 * XML, never as HTML; any document with an `OME` or `TiffData` element is OME. */
export function omeFiles(description: string | undefined, name: string): "none" | "one" | "others" | "too-large" {
  if (!description) return "none";
  if (description.length > OME_XML_MAX) return "too-large";
  let end = description.length; // geotiff keeps the ASCII value's final NUL
  while (end && description.charCodeAt(end - 1) === 0) end--;
  description = description.slice(0, end);
  const doc = new DOMParser().parseFromString(description, "application/xml");
  // fail closed: decided from the content, whatever the root and whether the parser reported a
  // failure (a forged parsererror element, a wrapper root or a partial parse is still scanned)
  if (doc.getElementsByTagNameNS("*", "OME").length === 0 && doc.getElementsByTagNameNS("*", "TiffData").length === 0) return "none";
  const base = name.split("/").pop();
  const uuids = new Set<string>();
  for (const uuid of Array.from(doc.getElementsByTagNameNS("*", "UUID"))) {
    if (uuid.parentElement?.localName !== "TiffData") continue;
    const fileName = uuid.getAttribute("FileName");
    if (fileName !== null && fileName !== base) return "others";
    uuids.add(uuid.textContent?.trim() ?? "");
  }
  return uuids.size > 1 ? "others" : "one";
}

/** After the walk, holds every IFD geotiff or Viv parses later (a plane's IFD, a SubIFD level,
 * which the walk does not reach) to the walk's caps: the offset inside the file, its entry table
 * prescanned, its tags checked, at most 10,000 offsets, each parsed once. */
export function guardParses(tiff: GeoTIFF, client: PinnedClient, max = IFDS_MAX) {
  const parse = tiff.parseFileDirectoryAt.bind(tiff);
  const parsed = new Map<number, ReturnType<typeof parse>>();
  let values = 0;
  const checked = async (offset: number) => {
    if (!Number.isSafeInteger(offset) || offset < 8 || offset + 2 > client.size) throw new Unreadable(`an IFD at ${offset}, past the end`);
    if (parsed.size > max) throw new TooLarge(`over ${max.toLocaleString("en-US")} IFDs`);
    values += await reading(client, () => prescan(tiff, offset, client.size));
    if (values > WALK_VALUES_MAX) throw new TooLarge("the IFDs' tags over 256 MiB");
    const ifd = await reading(client, () => parse(offset));
    check(ifd.fileDirectory as FileDirectory);
    return ifd;
  };
  tiff.parseFileDirectoryAt = (offset: number) => {
    if (!parsed.has(offset)) parsed.set(offset, checked(offset));
    return parsed.get(offset)!;
  };
}
