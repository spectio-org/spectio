// The flat view's pure parts (FU-P3-102d3; ui-spec §4.4.1): the level shown, the plane caps, the
// percentile stretch, grey and RGB, and every error as the state the boards give it.
import { expect, test } from "vitest";
import { ApiError } from "../../api";
import { Answered, Refused, Stopped } from "./client";
import { NotDecoded } from "./decode";
import { Unsupported, checkPlane, imageState, pages, percentiles, shownLevel, toRgba } from "./flat";
import { TooLarge, Unreadable, type FileDirectory } from "./walk";

const fd = (width: number, height: number, more: Record<string, unknown> = {}): FileDirectory => ({ ImageWidth: width, ImageLength: height, ...more });

test("the percentiles skip the outliers, whatever the order of the values", () => {
  const values = Array.from({ length: 10000 }, (_, i) => i);
  const [low, high] = percentiles(values);
  expect(low).toBeGreaterThanOrEqual(5);
  expect(low).toBeLessThanOrEqual(15);
  expect(high).toBeGreaterThanOrEqual(9985);
  expect(high).toBeLessThanOrEqual(9999);
  const outlier = [...Array.from({ length: 2000 }, (_, i) => 100 + (i % 100)), 65535, NaN];
  const [l, h] = percentiles(new Float32Array(outlier.reverse()));
  expect(l).toBeGreaterThanOrEqual(100);
  expect(h).toBeLessThan(250);
  expect(percentiles([7, 7, 7])).toEqual([7, 7]);
});

test("one 16-bit sample is stretched to grey; a flat plane is black, not NaN", () => {
  const plane = new Uint16Array(1000).map((_, i) => 1000 + i);
  const { rgba, stretched, note } = toRgba(1000, 1, [plane], { bits: 16, format: 1 });
  expect(stretched).toBe(true);
  expect(note).toBeNull();
  expect([rgba[0], rgba[1], rgba[2], rgba[3]]).toEqual([0, 0, 0, 255]);
  expect(rgba[999 * 4]).toBe(255);
  expect(rgba[500 * 4]).toBeGreaterThan(110);
  expect(rgba[500 * 4]).toBeLessThan(145);
  expect(rgba[500 * 4 + 1]).toBe(rgba[500 * 4]);
  expect(Array.from(toRgba(2, 1, [new Float32Array([3, 3])], { bits: 32, format: 3 }).rgba)).toEqual([0, 0, 0, 255, 0, 0, 0, 255]);
});

test("three 8-bit samples are RGB as stored; one 8-bit sample is grey as stored", () => {
  const rgb = toRgba(1, 1, [[10], [20], [30]], { bits: 8, format: 1 });
  expect(Array.from(rgb.rgba)).toEqual([10, 20, 30, 255]);
  expect(rgb.stretched).toBe(false);
  expect(Array.from(toRgba(2, 1, [[0, 200]], { bits: 8, format: 1 }).rgba)).toEqual([0, 0, 0, 255, 200, 200, 200, 255]);
});

test("any other sample count shows the first sample in grey, and says so", () => {
  const four = toRgba(1, 1, [[9], [1], [2], [3]], { bits: 8, format: 1 });
  expect(Array.from(four.rgba)).toEqual([9, 9, 9, 255]);
  expect(four.note).toBe("Shown: sample 1 of 4");
  expect(toRgba(1, 1, [[1], [2], [3]], { bits: 16, format: 1 }).note).toBe("Shown: sample 1 of 3");
});

test("the level: the first IFD; on a phone the largest of it and its reduced levels at most 2,048 px a side", () => {
  const base = fd(10000, 10000);
  const levels = [base, fd(5000, 5000, { NewSubfileType: 1 }), fd(1250, 1250, { NewSubfileType: 1 }), fd(2000, 2000)];
  expect(shownLevel(levels, false)).toBe(base);
  expect(shownLevel(levels, true)).toBe(levels[2]); // the 2,000 px page is another page, not a level
  expect(shownLevel([fd(1024, 768)], true)?.ImageWidth).toBe(1024);
  expect(shownLevel([fd(18400, 12800)], true)).toBeNull();
  expect(pages(levels)).toBe(2);
});

test("a plane over 50 megapixels and a compression off the allow-list are refused before any tile", () => {
  expect(() => checkPlane(fd(7072, 7072))).toThrow(TooLarge);
  expect(() => checkPlane(fd(7071, 7071))).not.toThrow();
  expect(() => checkPlane(fd(10, 10, { Compression: 34712 }))).toThrow("Spectio cannot decode JPEG 2000 compression.");
  expect(() => checkPlane(fd(10, 10, { Compression: 99 }))).toThrow("Spectio cannot decode compression 99.");
  expect(() => checkPlane(fd(10, 10, { Compression: 5 }))).not.toThrow();
});

test("each error is its board state", () => {
  const too = imageState(new TooLarge("a plane over 50 megapixels"));
  expect(too).toEqual({ title: "This image is too large to show here (a plane over 50 megapixels). Download it to open it.", download: true });
  expect(imageState(new Answered(413, "over 1 GiB"))).toEqual({ title: "This image is too large to show here (over 1 GiB). Download it to open it.", download: true });
  expect(imageState(new Unsupported("Spectio cannot decode LERC compression."))).toEqual({ title: "Spectio cannot decode LERC compression.", download: true });
  expect(imageState(new Answered(422, "not the TIFF its name says"))).toEqual({ title: "This file is not the TIFF its name says.", download: true, action: "retry" });
  expect(imageState(new Answered(422, "a reason"))).toEqual({ title: "Not an image Spectio can read: a reason", download: true, action: "retry" });
  expect(imageState(new Unreadable("an IFD at 99, past the end"))).toEqual({ title: "Not an image Spectio can read: an IFD at 99, past the end", download: true, action: "retry" });
  for (const err of [new NotDecoded("decoding took over 10 s"), new Refused("not sent"), new Error("geotiff's own")])
    expect(imageState(err)).toEqual({ title: "This image could not be decoded.", download: true, action: "retry" });
  expect(imageState(new Stopped("requests"))).toEqual({ title: "Spectio stopped reading tiles: 2,000 reads.", action: "reload", status: true, download: false });
  expect(imageState(new Stopped("bytes"))).toEqual({ title: "Spectio stopped reading tiles: 256 MiB read.", action: "reload", status: true, download: false });
  // 404, 409, 410, 503 and any other: the file page's own states (Problem), with the server's text
  for (const status of [404, 409, 410, 500, 503]) {
    const state = imageState(new Answered(status, "the server's text"));
    expect("problem" in state && state.problem).toBeInstanceOf(ApiError);
    expect("problem" in state && [state.problem.status, state.problem.message]).toEqual([status, "the server's text"]);
  }
});
