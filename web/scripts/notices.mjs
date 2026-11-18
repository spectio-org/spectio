// Writes web/public/THIRD_PARTY_NOTICES.txt (dev-env §15.3 req. 19, Pinned dependencies): every
// runtime package of the lock file (not "dev"), the bundled ones among them, with its licence text
// from its own tarball as installed by `npm ci --ignore-scripts`; a package with no licence file gets
// the licence and author its package.json declares. Vite copies public/ into dist/, so the notices
// ship in the wheel (spectio_server/web/). Run from web/: node scripts/notices.mjs
// src/notices.test.ts checks that every runtime package of the lock file is in it.
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const lock = JSON.parse(readFileSync("package-lock.json", "utf8"));
const LICENCE = /^(licen[cs]e|copying|notice)(\.|-|$)/i;
const entries = Object.entries(lock.packages)
  .filter(([path, p]) => path && !p.dev && !p.link)
  .map(([path, p]) => ({ path, name: path.slice(path.lastIndexOf("node_modules/") + 13), ...p }))
  .sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));

const seen = new Set();
const parts = [
  "Third-party notices for the Spectio screens (web/), generated from web/package-lock.json by web/scripts/notices.mjs.",
  "Each runtime package is listed as name@version, with its declared licence and the licence text it ships.",
];
for (const p of entries) {
  const key = `${p.name}@${p.version}`;
  if (seen.has(key)) continue;
  seen.add(key);
  const files = existsSync(p.path) ? readdirSync(p.path).filter((f) => LICENCE.test(f)).sort() : [];
  const meta = existsSync(join(p.path, "package.json")) ? JSON.parse(readFileSync(join(p.path, "package.json"), "utf8")) : {};
  const author = typeof meta.author === "string" ? meta.author : meta.author?.name;
  const texts = files.map((f) => readFileSync(join(p.path, f), "utf8").trim());
  if (!texts.length) texts.push(`No licence file in the package. Its package.json declares: ${p.license ?? meta.license ?? "no licence"}${author ? `; author: ${author}` : ""}.`);
  parts.push(`${"=".repeat(78)}\n${key}\nLicence: ${p.license ?? meta.license ?? "not declared"}\n\n${texts.join("\n\n")}`);
}
writeFileSync("public/THIRD_PARTY_NOTICES.txt", parts.join("\n\n") + "\n");
console.log(`${seen.size} packages`);
