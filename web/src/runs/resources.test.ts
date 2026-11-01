import { expect, test } from "vitest";
import type { Resources } from "../api";
import { bytes, nearLimit, resourcesLine, seconds } from "./resources";

const GIB = 1024 ** 3;
const none: Resources = { cpus: null, memory_bytes: null, time_s: null, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };

test("bytes read as people write them, a whole number without its decimal", () => {
  expect(bytes(null)).toBe("—");
  expect(bytes(8 * GIB)).toBe("8 GB");
  expect(bytes(8.04 * GIB)).toBe("8.0 GB");
  expect(bytes(2.5 * 1024 ** 2)).toBe("2.5 MB");
  expect(bytes(512)).toBe("512 B");
});

test("seconds read as durations: s, min, then h and minutes", () => {
  expect(seconds(null)).toBe("—");
  expect(seconds(41)).toBe("41 s");
  expect(seconds(6 * 60 + 5)).toBe("6 min");
  expect(seconds(4 * 3600)).toBe("4 h");
  expect(seconds(3600 + 12 * 60)).toBe("1 h 12");
});

test("near limit: a peak or a duration above 90 % of its request, never when one is unknown", () => {
  expect(nearLimit(none)).toEqual({ memory: false, time: false });
  expect(nearLimit({ ...none, memory_bytes: 8 * GIB, peak_rss_bytes: 7.3 * GIB })).toEqual({ memory: true, time: false });
  expect(nearLimit({ ...none, memory_bytes: 8 * GIB, peak_rss_bytes: 7.1 * GIB }).memory).toBe(false);
  expect(nearLimit({ ...none, time_s: 3600, realtime_s: 3300 })).toEqual({ memory: false, time: true });
  expect(nearLimit({ ...none, peak_rss_bytes: 7 * GIB }).memory).toBe(false);
});

test("the phone's resources line: asked, peak and limit, near limit in words", () => {
  expect(resourcesLine({ ...none, memory_bytes: 8 * GIB, peak_rss_bytes: 8 * GIB, time_s: 8 * 3600 })).toBe(
    "asked 8 GB · peak 8 GB, near limit · limit 8 h",
  );
  expect(resourcesLine(none)).toBe("asked — · peak — · limit —");
});
