// The third-party notices (dev-env §15.3 req. 19, Pinned dependencies): every runtime package of
// the lock file, so every bundled one, is in web/public/THIRD_PARTY_NOTICES.txt, which ships in the
// wheel. Regenerate with `node scripts/notices.mjs` (in web/) after any dependency change.
import { expect, test } from "vitest";
import lockText from "../package-lock.json?raw";
import notices from "../public/THIRD_PARTY_NOTICES.txt?raw";

test("every runtime package of the lock file, at its version, is in the third-party notices", () => {
  const lock = JSON.parse(lockText) as { packages: Record<string, { version: string; dev?: boolean; link?: boolean }> };
  const listed = new Set(notices.split("\n"));
  const runtime = Object.entries(lock.packages)
    .filter(([path, p]) => path && !p.dev && !p.link)
    .map(([path, p]) => `${path.slice(path.lastIndexOf("node_modules/") + 13)}@${p.version}`);
  expect(runtime.length).toBeGreaterThan(100);
  expect(runtime.filter((key) => !listed.has(key))).toEqual([]);
});
