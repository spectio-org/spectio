import { expect, test } from "vitest";
import { ago } from "./Ago";

const now = new Date(2026, 10, 25, 12, 0);

test("a date ahead, a session's end, is shown exactly, not as just now", () => {
  expect(ago(new Date(2026, 11, 2, 9, 5).toISOString(), now)).toBe("2026-12-02 09:05");
});

test("a minute of clock skew ahead still reads just now", () => {
  expect(ago(new Date(now.getTime() + 30000).toISOString(), now)).toBe("just now");
});

test("past dates keep their words", () => {
  expect(ago(new Date(now.getTime() - 12 * 60000).toISOString(), now)).toBe("12 min ago");
  expect(ago(null, now)).toBe("—");
});
