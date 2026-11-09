// The page's own TIFF reader, first part (FU-P3-102d1; api §5.3.1, dev-env §15.3 req. 19): the
// pinned client and its budgets, the IFD walk with its caps and loop set, the one-file OME-XML
// check. The fixtures are crafted here, byte by byte, and served by a fake fetch that answers
// each closed Range as the raw route does (step 11: 206 with Content-Range).
import { afterEach, expect, test, vi } from "vitest";
import { resultUrl } from "../../api";
import { Answered, BUDGET, IN_FLIGHT, PinnedClient, RANGE_MAX, Refused, Stopped, openTiff, reading } from "./client";
import { TooLarge, Unreadable, omeFiles, walkIfds } from "./walk";

const URL_ = resultUrl("run_1", "img/gel.tif", { as: "tiff" });

interface Ifd {
  width?: number;
  height?: number; // ImageLength
  rows?: number; // RowsPerStrip
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
    [257, 4, d.height ?? 2],
    [258, 3, d.bits ?? 8],
    [259, 3, 1],
    [262, 3, 1],
    ...(d.description === undefined ? [] : [[270, 2, d.description] as [number, number, string]]),
    [277, 3, d.samples ?? 1],
    ...(d.tile ? [[322, 4, d.tile], [323, 4, d.tile], [324, 4, 0], [325, 4, 8]] : [[273, 4, 0], [278, 4, d.rows ?? 2], [279, 4, 8]]) as [number, number, number][],
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
const problemAnswer = (status: number, detail: string) =>
  new Response(JSON.stringify({ detail }), { status, headers: { "content-type": "application/problem+json" } });
const ranges = (mock: ReturnType<typeof serveBytes>) => mock.mock.calls.map(([, init]) => new Headers(init?.headers).get("range")!);

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

test("opens a TIFF through the pinned raw URL only, one closed Range per request", async () => {
  const { bytes } = build([{}, {}]);
  const mock = serveBytes(bytes);
  const { tiff, client } = await openTiff(URL_, bytes.length);
  const { ifds, loop } = await walkIfds(tiff, client);
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
  const { tiff, client } = await openTiff(URL_, bytes.length);
  const { ifds, loop } = await walkIfds(tiff, client);
  expect(ifds).toHaveLength(2);
  expect(loop).toBe(true);
});

test("too many IFDs: the walk stops at the cap", async () => {
  const { bytes } = build([{}, {}, {}, {}]);
  serveBytes(bytes);
  const { tiff, client } = await openTiff(URL_, bytes.length);
  await expect(walkIfds(tiff, client, 3)).rejects.toEqual(new TooLarge("over 3 IFDs"));
  await expect(walkIfds(tiff, client, 4)).resolves.toMatchObject({ loop: false });
});

test("an IFD offset past the end is not read", async () => {
  const { bytes, setNext } = build([{}]);
  setNext(0, bytes.length + 100);
  const mock = serveBytes(bytes);
  const { tiff, client } = await openTiff(URL_, bytes.length);
  await expect(walkIfds(tiff, client)).rejects.toBeInstanceOf(Unreadable);
  expect(ranges(mock)).toEqual(["bytes=0-65536"]);
});

test("a BigTIFF header is read as BigTIFF", async () => {
  const { bytes } = build([{ width: 7 }], true);
  serveBytes(bytes);
  const { tiff, client } = await openTiff(URL_, bytes.length);
  expect(tiff.bigTiff).toBe(true);
  const { ifds } = await walkIfds(tiff, client);
  expect(ifds.map((d) => d.ImageWidth)).toEqual([7]);
});

test("the caps of each IFD are checked before any tile is read", async () => {
  for (const [ifd, reason] of [
    [{ tile: 8192 }, "tiles larger than 4,096 px"],
    [{ bits: 64, format: 3 }, "64-bit float pixels are not shown"],
    [{ bits: 32, format: 4 }, "32-bit undefined pixels are not shown"],
    [{ samples: 5 }, "5-sample pixels are not shown"],
    [{ tile: 4096, samples: 4, bits: 32 }, "a tile over 64 MiB decoded"], // 256 MiB
    [{ width: 20000, height: 20000, rows: 20000 }, "a tile over 64 MiB decoded"], // one strip of 400 MB
  ] as [Ifd, string][]) {
    const { bytes } = build([ifd]);
    serveBytes(bytes);
    const { tiff, client } = await openTiff(URL_, bytes.length);
    await expect(walkIfds(tiff, client)).rejects.toEqual(new TooLarge(reason));
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

test("only closed Ranges of at most 8 MiB + 1 byte, inside the file, are ever sent", async () => {
  const size = 32 * 1024 * 1024;
  const mock = serveBytes(new Uint8Array(0));
  const client = new PinnedClient(URL_, size);
  for (const range of ["", "bytes=0-", "bytes=-10", "bytes=0-1,4-5", "bytes=5-4", `bytes=${size}-${size + 10}`]) {
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
  serveBytes(bytes, () => problemAnswer(422, "not the TIFF its name says"));
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
  const { tiff, client } = await openTiff(URL_, bytes.length);
  const { ifds } = await walkIfds(tiff, client);
  expect(omeFiles(ifds[0].ImageDescription, "a.ome.tif")).toBe("one");
});

test("a range over 8 MiB + 1 is sent as closed ranges of 8 MiB, each charged, answered as one", async () => {
  const size = 32 * 1024 * 1024;
  const bytes = new Uint8Array(size).map((_, i) => i % 251);
  const mock = serveBytes(bytes);
  const client = new PinnedClient(URL_, size);
  const last = 20 * 1024 * 1024;
  const answer = await client.request({ headers: { Range: `bytes=0-${last}` } });
  expect(ranges(mock)).toEqual(["bytes=0-8388607", "bytes=8388608-16777215", `bytes=16777216-${last}`]);
  expect(answer.getHeader("content-range")).toBe(`bytes 0-${last}/${size}`);
  const data = new Uint8Array(await answer.getData());
  expect(data.length).toBe(last + 1);
  expect(data.every((b, i) => b === i % 251)).toBe(true);
  expect(client).toMatchObject({ requests: 3, bytes: last + 1 });
  const small = new PinnedClient(URL_, size, { requests: 2, bytes: BUDGET.bytes });
  await expect(small.request({ headers: { Range: `bytes=0-${last}` } })).rejects.toEqual(new Stopped("requests"));
});

test("the client's own errors reach the caller through geotiff", async () => {
  const { bytes } = build([{}]);
  serveBytes(bytes);
  await expect(openTiff(URL_, bytes.length, undefined, { requests: 10, bytes: 10 })).rejects.toEqual(new Stopped("bytes"));
  serveBytes(bytes, () => problemAnswer(422, "not the TIFF its name says"));
  const refused = openTiff(URL_, bytes.length);
  await expect(refused).rejects.toBeInstanceOf(Answered);
  await expect(refused).rejects.toMatchObject({ status: 422, detail: "not the TIFF its name says" });
  // an IFD past the first block: the walk's read is the one stopped
  const far = new Uint8Array(200_000);
  far.set(build([{}]).bytes.slice(8), 100_000);
  far.set([0x49, 0x49, 0x2a, 0x00]);
  new DataView(far.buffer).setUint32(4, 100_000, true);
  serveBytes(far);
  const { tiff, client } = await openTiff(URL_, far.length, undefined, { requests: 1, bytes: BUDGET.bytes });
  await expect(walkIfds(tiff, client)).rejects.toEqual(new Stopped("requests"));
});

/** A classic little-endian TIFF of one IFD at 8 with these raw entries (tag, type, count, value
 * or offset), padded to `size` bytes. */
function raw(entries: [number, number, number, number][], size = 64) {
  const bytes = new Uint8Array(Math.max(size, 8 + 2 + entries.length * 12 + 4));
  const view = new DataView(bytes.buffer);
  bytes.set([0x49, 0x49, 0x2a, 0x00, 8, 0, 0, 0]);
  view.setUint16(8, entries.length, true);
  entries.forEach(([tag, type, count, value], i) => {
    view.setUint16(10 + i * 12, tag, true);
    view.setUint16(12 + i * 12, type, true);
    view.setUint32(14 + i * 12, count, true);
    view.setUint32(18 + i * 12, value, true);
  });
  return bytes;
}

test("an IFD's entry table is held to its caps before geotiff parses it", async () => {
  const twoMib = 2 * 1024 * 1024;
  for (const [bytes, error] of [
    [raw([[279, 4, 1e8, 16]]), new TooLarge("a tag over 8 MiB")], // StripByteCounts of 10^8 values
    [raw(Array.from({ length: 400 }, (_, i) => [1000 + i, 1, twoMib, 16] as [number, number, number, number]), twoMib + 64), new TooLarge("an IFD's tags over 16 MiB")],
    [raw(Array.from({ length: 1025 }, (_, i) => [1000 + i, 3, 1, 0] as [number, number, number, number])), new TooLarge("over 1,024 tags in an IFD")],
    [raw([[256, 99, 1, 4]]), new Unreadable("a tag of unknown type 99")],
    [raw([[270, 2, 100, 60]]), new Unreadable("a tag's values past the end")],
  ] as [Uint8Array, Error][]) {
    const mock = serveBytes(bytes);
    const { tiff, client } = await openTiff(URL_, bytes.length);
    const parse = vi.spyOn(tiff, "parseFileDirectoryAt");
    await expect(walkIfds(tiff, client)).rejects.toEqual(error);
    expect(parse).not.toHaveBeenCalled();
    expect(ranges(mock)).toEqual(["bytes=0-65536"]);
  }
});

test("the OME-XML check parses whatever comes before the root", () => {
  const foreign = '<TiffData><UUID FileName="b.ome.tif">urn:uuid:2</UUID></TiffData>';
  expect(omeFiles(ome(foreign).replace("<OME", "<!-- c --><OME"), "a.ome.tif")).toBe("others");
  expect(omeFiles(`\uFEFF${ome(foreign)}`, "a.ome.tif")).toBe("others");
  const prefixed = `<ome:OME xmlns:ome="http://www.openmicroscopy.org/Schemas/OME/2016-06"><ome:Image ID="Image:0"><ome:Pixels ID="Pixels:0"><ome:TiffData><ome:UUID FileName="b.ome.tif">urn:uuid:2</ome:UUID></ome:TiffData></ome:Pixels></ome:Image></ome:OME>`;
  expect(omeFiles(prefixed, "a.ome.tif")).toBe("others");
});

test("a run of NULs in the description is stripped in linear time", () => {
  const started = performance.now();
  expect(omeFiles(`${"\0".repeat(200_000)}x`, "a.tif")).toBe("none");
  expect(omeFiles(`${ome('<TiffData IFD="0"/>')}\0\0`, "a.ome.tif")).toBe("one");
  expect(performance.now() - started).toBeLessThan(1000);
});

test("a parsererror element inside a well-formed OME document is not a parse failure", () => {
  const foreign = '<TiffData><UUID FileName="b.ome.tif">urn:uuid:2</UUID></TiffData>';
  expect(omeFiles(ome("<parsererror/>" + foreign), "a.ome.tif")).toBe("others");
});

test("an aborted request is not reported for a later error", async () => {
  const bytes = new Uint8Array(100);
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new DOMException("aborted", "AbortError");
    }),
  );
  const client = new PinnedClient(URL_, bytes.length, { requests: 1, bytes: BUDGET.bytes });
  await expect(client.request({ headers: { Range: "bytes=0-9" } })).rejects.toMatchObject({ name: "AbortError" });
  // geotiff's BlockedSource hides the client's error behind its own
  const wrapped = () => client.request({ headers: { Range: "bytes=10-19" } }).catch(() => Promise.reject(new AggregateError([], "wrapped")));
  await expect(reading(client, wrapped)).rejects.toEqual(new Stopped("requests"));
  // a page error thrown as is is rethrown as is, not the client's earlier one
  await expect(reading(client, () => Promise.reject(new Refused("later")))).rejects.toEqual(new Refused("later"));
});

/** An endless body that counts the bytes it was asked for, in chunks of `chunk` bytes. */
function endless(chunk: number) {
  const pulled = { bytes: 0 };
  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      pulled.bytes += chunk;
      controller.enqueue(new Uint8Array(chunk));
    },
  });
  return { body, pulled };
}

test("a body is never read past what was asked for", async () => {
  const other = endless(1024);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(other.body, { status: 200, headers: { "content-type": "application/octet-stream" } })));
  const client = new PinnedClient(URL_, 1_000_000);
  await expect(client.request({ headers: { Range: "bytes=0-99" } })).rejects.toEqual(new Answered(200, null));
  expect(other.pulled.bytes).toBeLessThanOrEqual(64 * 1024);
  expect(client.bytes).toBe(100);

  const problem = endless(1024);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(problem.body, { status: 500, headers: { "content-type": "application/problem+json" } })));
  await expect(client.request({ headers: { Range: "bytes=0-99" } })).rejects.toEqual(new Answered(500, null));
  expect(problem.pulled.bytes).toBeLessThanOrEqual(64 * 1024 + 2 * 1024);

  const longer = endless(1);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(longer.body, { status: 206, headers: { "content-range": "bytes 0-99/1000000" } })));
  await expect(client.request({ headers: { Range: "bytes=0-99" } })).rejects.toEqual(new Answered(206, "not the range asked"));
  expect(longer.pulled.bytes).toBeLessThanOrEqual(100 + 2);

  vi.stubGlobal("fetch", vi.fn(async () => new Response(new Uint8Array(200), { status: 206, headers: { "content-length": "200" } })));
  await expect(client.request({ headers: { Range: "bytes=0-99" } })).rejects.toEqual(new Answered(206, "not the range asked"));
});

test("a 503's body is cancelled before the request is asked again", async () => {
  vi.useFakeTimers();
  let cancelled = false;
  const body = new ReadableStream({ cancel: () => void (cancelled = true) });
  const bytes = new Uint8Array(10);
  serveBytes(bytes, (call) => (call === 1 ? new Response(body, { status: 503 }) : undefined));
  const client = new PinnedClient(URL_, bytes.length);
  const read = client.request({ headers: { Range: "bytes=0-9" } });
  await vi.advanceTimersByTimeAsync(1000);
  expect((await read).status).toBe(206);
  expect(cancelled).toBe(true);
});

test("the OME-XML check decides from the content, whatever the root or the parser says", () => {
  const foreign = '<TiffData><UUID FileName="b.ome.tif">urn:uuid:2</UUID></TiffData>';
  expect(omeFiles(ome('<parsererror xmlns="http://www.w3.org/1999/xhtml"/>' + foreign), "a.ome.tif")).toBe("others");
  const wrapped = (root: string) => `<${root}>${ome(foreign).replace(/^<\?xml[^>]*\?>/, "")}</${root.split(" ")[0]}>`;
  expect(omeFiles(wrapped('parsererror xmlns="http://www.mozilla.org/newlayout/xml/parsererror.xml"'), "a.ome.tif")).toBe("others");
  expect(omeFiles(wrapped("Wrapper"), "a.ome.tif")).toBe("others");
  expect(omeFiles("ImageJ=1.54f\nimages=3\nslices=3", "a.tif")).toBe("none");
});
