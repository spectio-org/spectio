// The page's own TIFF reader, first part (FU-P3-102d1; api §5.3.1, dev-env §15.3 req. 19): the
// pinned client and its budgets, the IFD walk with its caps and loop set, the one-file OME-XML
// check. The fixtures are crafted here, byte by byte, and served by a fake fetch that answers
// each closed Range as the raw route does (step 11: 206 with Content-Range).
import { afterEach, expect, test, vi } from "vitest";
import { resultUrl } from "../../api";
import { BUDGET, IN_FLIGHT, PinnedClient, RANGE_MAX, Refused, Stopped, openTiff } from "./client";
import { TooLarge, Unreadable, omeFiles, walkIfds } from "./walk";

const URL_ = resultUrl("run_1", "img/gel.tif", { as: "tiff" });

interface Ifd {
  width?: number;
  tile?: number; // TileWidth and TileLength, instead of one strip
  bits?: number;
  format?: number; // SampleFormat
  samples?: number;
  description?: string;
}

/** A little-endian TIFF (or BigTIFF) of 1-byte-per-pixel images, one IFD each, chained in order.
 * `nextAt[i]` is where IFD i's next-IFD offset is written, for tests that rewire the chain. */
function build(ifds: Ifd[], big = false) {
  const entry = big ? 20 : 12;
  const word = big ? 8 : 4; // an offset
  const count = big ? 8 : 2; // the entry count
  const head = big ? 16 : 8;
  const tags = (d: Ifd): [number, number, number | string][] => [
    [256, 4, d.width ?? 4],
    [257, 4, 2],
    [258, 3, d.bits ?? 8],
    [259, 3, 1],
    [262, 3, 1],
    ...(d.description === undefined ? [] : [[270, 2, d.description] as [number, number, string]]),
    [277, 3, d.samples ?? 1],
    ...(d.tile ? [[322, 4, d.tile], [323, 4, d.tile], [324, 4, 0], [325, 4, 8]] : [[273, 4, 0], [278, 4, 2], [279, 4, 8]]) as [number, number, number][],
    ...(d.format === undefined ? [] : [[339, 3, d.format] as [number, number, number]]),
  ];
  const sizes = ifds.map((d) => count + tags(d).length * entry + word);
  const extras = ifds.map((d) => (d.description === undefined ? 0 : d.description.length + 1));
  const total = head + sizes.reduce((a, b) => a + b, 0) + extras.reduce((a, b) => a + b, 0) + 8;
  const bytes = new Uint8Array(total);
  const view = new DataView(bytes.buffer);
  const put = (at: number, value: number, width: number) =>
    width === 8 ? view.setBigUint64(at, BigInt(value), true) : width === 4 ? view.setUint32(at, value, true) : view.setUint16(at, value, true);
  bytes.set(big ? [0x49, 0x49, 0x2b, 0x00, 8, 0, 0, 0] : [0x49, 0x49, 0x2a, 0x00]);
  put(big ? 8 : 4, head, word);
  let extra = head + sizes.reduce((a, b) => a + b, 0);
  const nextAt: number[] = [];
  let at = head;
  ifds.forEach((d, i) => {
    const list = tags(d);
    put(at, list.length, count);
    list.forEach(([tag, type, value], j) => {
      const e = at + count + j * entry;
      put(e, tag, 2);
      put(e + 2, type, 2);
      if (typeof value === "string") {
        put(e + 4, value.length + 1, word);
        put(e + 4 + word, extra, word);
        bytes.set(new TextEncoder().encode(value), extra);
        extra += value.length + 1;
      } else {
        put(e + 4, 1, word);
        put(e + 4 + word, value, type === 3 ? 2 : 4);
      }
    });
    nextAt.push(at + count + list.length * entry);
    at += sizes[i];
    put(nextAt[i], i + 1 < ifds.length ? at : 0, word);
  });
  return { bytes, nextAt, setNext: (i: number, to: number) => put(nextAt[i], to, word) };
}

/** A fake raw route: each call answers its closed Range with 206, or `answer`'s response. */
function serveBytes(bytes: Uint8Array, answer?: (call: number) => Response | undefined) {
  const mock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const given = answer?.(mock.mock.calls.length);
    if (given) return given;
    const [first, last] = new Headers(init?.headers).get("range")!.slice(6).split("-").map(Number);
    const end = Math.min(last, bytes.length - 1);
    return new Response(bytes.slice(first, end + 1), { status: 206, headers: { "content-range": `bytes ${first}-${end}/${bytes.length}` } });
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}
const ranges = (mock: ReturnType<typeof serveBytes>) => mock.mock.calls.map(([, init]) => new Headers(init?.headers).get("range")!);

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

test("opens a TIFF through the pinned raw URL only, one closed Range per request", async () => {
  const { bytes } = build([{}, {}]);
  const mock = serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  const { ifds, loop } = await walkIfds(tiff, bytes.length);
  expect(ifds.map((d) => d.ImageWidth)).toEqual([4, 4]);
  expect(loop).toBe(false);
  expect(URL_).toBe("/api/v1/runs/run_1/results/raw/img/gel.tif?as=tiff");
  expect(mock.mock.calls.every(([url]) => url === URL_)).toBe(true);
  expect(ranges(mock)).toEqual(["bytes=0-65536"]); // one 64 KiB block, as geotiff asks it
});

test("an IFD offset seen twice ends the walk: a loop", async () => {
  const { bytes, setNext } = build([{}, {}]);
  setNext(1, 8); // IFD 1 points back at IFD 0
  serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  const { ifds, loop } = await walkIfds(tiff, bytes.length);
  expect(ifds).toHaveLength(2);
  expect(loop).toBe(true);
});

test("too many IFDs: the walk stops at the cap", async () => {
  const { bytes } = build([{}, {}, {}, {}]);
  serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  await expect(walkIfds(tiff, bytes.length, 3)).rejects.toEqual(new TooLarge("over 3 IFDs"));
  await expect(walkIfds(tiff, bytes.length, 4)).resolves.toMatchObject({ loop: false });
});

test("an IFD offset past the end is not read", async () => {
  const { bytes, setNext } = build([{}]);
  setNext(0, bytes.length + 100);
  const mock = serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  await expect(walkIfds(tiff, bytes.length)).rejects.toBeInstanceOf(Unreadable);
  expect(ranges(mock)).toEqual(["bytes=0-65536"]);
});

test("a BigTIFF header is read as BigTIFF", async () => {
  const { bytes } = build([{ width: 7 }], true);
  serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  expect(tiff.bigTiff).toBe(true);
  const { ifds } = await walkIfds(tiff, bytes.length);
  expect(ifds.map((d) => d.ImageWidth)).toEqual([7]);
});

test("the caps of each IFD are checked before any tile is read", async () => {
  for (const [ifd, reason] of [
    [{ tile: 8192 }, "tiles larger than 4,096 px"],
    [{ bits: 64, format: 3 }, "64-bit float pixels are not shown"],
    [{ bits: 32, format: 4 }, "32-bit undefined pixels are not shown"],
    [{ samples: 5 }, "5-sample pixels are not shown"],
  ] as [Ifd, string][]) {
    const { bytes } = build([ifd]);
    serveBytes(bytes);
    const { tiff } = await openTiff(URL_, bytes.length);
    await expect(walkIfds(tiff, bytes.length)).rejects.toEqual(new TooLarge(reason));
  }
});

test("a request that would exceed the budget is not sent", async () => {
  const bytes = new Uint8Array(200_000);
  const mock = serveBytes(bytes);
  const client = new PinnedClient(URL_, bytes.length, { requests: 10, bytes: 100_000 });
  await client.request({ headers: { Range: "bytes=0-65535" } });
  await expect(client.request({ headers: { Range: "bytes=65536-131071" } })).rejects.toEqual(new Stopped("bytes"));
  const few = new PinnedClient(URL_, bytes.length, { requests: 1, bytes: BUDGET.bytes });
  await few.request({ headers: { Range: "bytes=0-9" } });
  await expect(few.request({ headers: { Range: "bytes=10-19" } })).rejects.toEqual(new Stopped("requests"));
  expect(mock).toHaveBeenCalledTimes(2);
  expect(BUDGET).toEqual({ requests: 2000, bytes: 256 * 1024 * 1024 });
});

test("only one closed Range of at most 8 MiB + 1 byte, inside the file, is ever sent", async () => {
  const size = 32 * 1024 * 1024;
  const mock = serveBytes(new Uint8Array(0));
  const client = new PinnedClient(URL_, size);
  for (const range of ["", "bytes=0-", "bytes=-10", "bytes=0-1,4-5", "bytes=5-4", `bytes=0-${RANGE_MAX}`, `bytes=${size}-${size + 10}`]) {
    await expect(client.request({ headers: range ? { Range: range } : {} })).rejects.toBeInstanceOf(Refused);
  }
  expect(mock).not.toHaveBeenCalled();
  expect(RANGE_MAX).toBe(8 * 1024 * 1024 + 1);
});

test("at most 3 requests are in flight", async () => {
  let open = 0;
  let most = 0;
  const release: (() => void)[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      most = Math.max(most, ++open);
      await new Promise<void>((done) => release.push(done));
      open--;
      return new Response(new Uint8Array(1), { status: 206, headers: { "content-range": "bytes 0-0/100" } });
    }),
  );
  const client = new PinnedClient(URL_, 100);
  const all = Promise.all([0, 1, 2, 3, 4].map(() => client.request({ headers: { Range: "bytes=0-0" } })));
  while (release.length || open) {
    await new Promise((r) => setTimeout(r, 0));
    release.shift()?.();
  }
  await all;
  expect(most).toBe(IN_FLIGHT);
});

test("a 503 is asked again once, after 1 s; another answer is an error with its status", async () => {
  vi.useFakeTimers();
  const bytes = new Uint8Array(10);
  const mock = serveBytes(bytes, (call) => (call === 1 ? new Response(null, { status: 503 }) : undefined));
  const client = new PinnedClient(URL_, bytes.length);
  const read = client.request({ headers: { Range: "bytes=0-9" } });
  await vi.advanceTimersByTimeAsync(1000);
  expect((await read).status).toBe(206);
  expect(mock).toHaveBeenCalledTimes(2);
  serveBytes(bytes, () => Response.json({ detail: "not the TIFF its name says" }, { status: 422 }));
  await expect(client.request({ headers: { Range: "bytes=0-9" } })).rejects.toMatchObject({ status: 422, detail: "not the TIFF its name says" });
});

const ome = (tiffData: string) =>
  `<?xml version="1.0" encoding="UTF-8"?><OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"><Image ID="Image:0"><Pixels ID="Pixels:0">${tiffData}</Pixels></Image></OME>`;

test("the OME-XML check: one file, other files, none", () => {
  expect(omeFiles("Plot made by R", "a.tif")).toBe("none");
  expect(omeFiles("<OME", "a.tif")).toBe("none"); // not XML
  expect(omeFiles(ome('<TiffData IFD="0"/>'), "a.ome.tif")).toBe("one");
  expect(omeFiles(ome('<TiffData><UUID FileName="a.ome.tif">urn:uuid:1</UUID></TiffData>'), "a.ome.tif")).toBe("one");
  expect(omeFiles(ome('<TiffData><UUID FileName="b.ome.tif">urn:uuid:2</UUID></TiffData>'), "a.ome.tif")).toBe("others");
  expect(omeFiles(ome('<TiffData><UUID>urn:uuid:1</UUID></TiffData><TiffData><UUID>urn:uuid:2</UUID></TiffData>'), "a.ome.tif")).toBe("others");
  expect(omeFiles(ome(`<TiffData/>${" ".repeat(4 * 1024 * 1024)}`), "a.ome.tif")).toBe("too-large");
});

test("the first IFD's ImageDescription reaches the OME-XML check", async () => {
  const { bytes } = build([{ description: ome('<TiffData IFD="0"/>') }]);
  serveBytes(bytes);
  const { tiff } = await openTiff(URL_, bytes.length);
  const { ifds } = await walkIfds(tiff, bytes.length);
  expect(omeFiles(ifds[0].ImageDescription, "a.ome.tif")).toBe("one");
});
