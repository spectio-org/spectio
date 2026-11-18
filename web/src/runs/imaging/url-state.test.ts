// The OME-TIFF viewer's view in the URL (FU-P3-102f; ui-spec §4.4.1 "The URL keeps the view"):
// `z` and `t` 1-based, `ch` 0-based, `zoom`, `x` and `y`; a value out of range is dropped and the
// default used, and nothing throws; the page's other parameters are kept as they are.
import { expect, test } from "vitest";
import { parseView, serialiseView } from "./url-state";

const sizes = { x: 100, y: 50, z: 40, t: 3, c: 8 };

test("a view written is the view read back, and the other parameters stay as they are", () => {
  const search = serialiseView("?path=%2212%22&task=a+b", { z: 11, t: 2, ch: [0, 3], view: { zoom: -1.234, target: [50.6, 25.2, 0] } });
  expect(search).toBe("?path=%2212%22&task=a+b&z=12&t=3&ch=0,3&zoom=-1.23&x=51&y=25");
  expect(parseView(search, sizes)).toEqual({ z: 11, t: 2, ch: [0, 3], view: { zoom: -1.23, target: [51, 25, 0] } });
  expect(serialiseView(search, { z: 0, t: 0, ch: null, view: null })).toBe("?path=%2212%22&task=a+b&z=1&t=1");
});

test("no view in the URL: the defaults", () => {
  expect(parseView("", sizes)).toEqual({ z: 0, t: 0, ch: null, view: null });
});

test("hostile values are dropped, never thrown: NaN, huge, negative, fractions, unknown channels", () => {
  for (const bad of ["z=NaN&t=Infinity", "z=0&t=4", "z=-3&t=1e3", "z=99999999999999999999&t=1.5", "z=%ZZ&t=", "z=12abc&t=0x2"]) {
    const v = parseView(`?${bad}`, sizes);
    expect([v.z, v.t]).toEqual([0, 0]);
  }
  expect(parseView("?ch=8,-1,abc,2,2,NaN,1", sizes).ch).toEqual([2, 1]); // unknown and repeated channels dropped
  expect(parseView("?ch=0,1,2,3,4,5,6,7", sizes).ch).toEqual([0, 1, 2, 3, 4, 5]); // at most 6 on
  expect(parseView("?ch=", sizes).ch).toEqual([]); // every channel off
  expect(parseView("?ch=9,abc", sizes).ch).toBeNull(); // nothing known: the default
  for (const bad of ["zoom=NaN&x=1&y=1", "zoom=1e308&x=1&y=1", "zoom=-13&x=1&y=1", "zoom=1&x=-1&y=1", "zoom=1&x=101&y=1", "zoom=1&x=1"]) {
    expect(parseView(`?${bad}`, sizes).view).toBeNull();
  }
  expect(parseView("?zoom=2&x=100&y=0", sizes)).toMatchObject({ view: { zoom: 2, target: [100, 0, 0] } });
});
