// Builds the graph demo (issue #160) into one self-contained HTML file: `node scripts/demo.mjs [out]`.
// Vite writes web/demo/dist with an entry script and one stylesheet (images already inline); this
// script moves both into the page. Default output: web/demo/dist/spectio-graph-demo.html.
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(web, "demo", "dist");
execFileSync("npx", ["vite", "build", "--config", "demo/vite.config.ts", "--logLevel", "warn"], { cwd: web, stdio: "inherit" });

const assets = join(dist, "assets");
const files = readdirSync(assets);
const css = files.filter((f) => f.endsWith(".css"));
let html = readFileSync(join(dist, "index.html"), "utf8");
// the page's entry; the imaging worker and its decoders stay behind, unused by the graph
const entry = /<script type="module" crossorigin src="\.\/assets\/([^"]+)"/.exec(html)?.[1];
if (!entry) throw new Error("no entry script in index.html");
// `</script` inside the code would end the inline element early
const code = readFileSync(join(assets, entry), "utf8").replace(/<\/script/gi, "<\\/script");
html = html.replace(/<script type="module" crossorigin src="[^"]+"><\/script>/, () => "");
html = html.replace(/<link rel="stylesheet" crossorigin href="[^"]+">/, () => "");
const styles = css.map((f) => `<style>${readFileSync(join(assets, f), "utf8")}</style>`).join("\n");
html = html.replace("</head>", () => `${styles}\n</head>`);
html = html.replace("</body>", () => `<script type="module">${code}</script>\n</body>`);
const out = resolve(process.argv[2] ?? join(dist, "spectio-graph-demo.html"));
writeFileSync(out, html);
console.log(`${out}: ${(html.length / 1e6).toFixed(2)} MB`);
