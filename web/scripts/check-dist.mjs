// The normal build (web/dist, served by `spectio serve`) must hold none of the public demo: no
// recorded run ID and none of its texts (run after `vite build` by `npm run build`).
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const dist = new URL("../dist/", import.meta.url).pathname;
const recorded = JSON.parse(readFileSync(new URL("../demo/fixtures.json", import.meta.url), "utf8"));
const ids = new Set(Object.keys(recorded).flatMap((k) => k.match(/run_[0-9A-Z]{26}/g) ?? []));
const needles = [...ids, "Demo: recorded data", "Read-only demo", "read-only-demo"];

const files = readdirSync(dist, { recursive: true, withFileTypes: true }).filter((f) => f.isFile());
const hits = files.flatMap((f) => {
  const text = readFileSync(join(f.parentPath, f.name), "latin1");
  return needles.filter((n) => text.includes(n)).map((n) => `${join(f.parentPath, f.name)}: ${n}`);
});
if (ids.size === 0 || hits.length) {
  console.error(ids.size === 0 ? "no run ID in demo/fixtures.json" : `the demo leaked into dist:\n  ${hits.join("\n  ")}`);
  process.exit(1);
}
console.log(`dist: ${files.length} files, none of the demo (${needles.length} needles)`);
