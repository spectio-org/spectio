import { expect, test } from "vitest";
import type { Resources } from "../api";
import { bytes, nearLimit, resourcesLine } from "./resources";

const GIB = 1024 ** 3;
const none: Resources = { cpus: null, memory_bytes: null, time_s: null, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };

test("bytes read as people write them: one fixed decimal from MB up", () => {
  expect(bytes(null)).toBe("—");
  expect(bytes(8 * GIB)).toBe("8.0 GB");
  expect(bytes(8.04 * GIB)).toBe("8.0 GB");
  expect(bytes(2.5 * 1024 ** 2)).toBe("2.5 MB");
  expect(bytes(512)).toBe("512 B");
  expect(bytes(3 * 1024)).toBe("3 KB");
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
    "asked 8.0 GB · peak 8.0 GB, near limit · limit 8 h",
  );
  expect(resourcesLine(none)).toBe("asked — · peak — · limit —");
});
