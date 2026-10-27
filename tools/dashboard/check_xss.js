#!/usr/bin/env node
// Builds the dashboard with a hostile Markdown file added and fails if any payload runs.
// node tools/dashboard/check_xss.js OUTDIR    (OUTDIR: gen.py's data.json, docs.json, imgs.json; left unchanged)
// The page loads marked, DOMPurify and mermaid from cdnjs with their integrity hashes, so a wrong hash fails here too.
const fs = require("fs"), os = require("os"), path = require("path"), {execFileSync} = require("child_process");
const {chromium} = require("playwright");

const src = process.argv[2], dir = fs.mkdtempSync(path.join(os.tmpdir(), "spectio-xss-"));
for (const f of ["data.json", "imgs.json"]) fs.copyFileSync(path.join(src, f), path.join(dir, f));
const docs = JSON.parse(fs.readFileSync(path.join(src, "docs.json"), "utf8"));
const FX = "fixture/xss.md";
docs[FX] = `# XSS fixture

<img src=x onerror=alert(1)>

<script>alert(2)</script>

[js link](javascript:alert(3)) [mixed case](JaVaScRiPt:alert(4)) [data link](data:text/html,<script>alert(5)</script>) [kept](https://example.org)

<iframe src="javascript:alert(6)"></iframe>

<svg><animate onbegin=alert(7) attributeName=x dur=1s /></svg>

<!--><img src=x onerror=alert(13)>--> <!-- --><img src=x onerror=alert(14)> -->

!!! note "<img src=x onerror=alert(8)>"
    Body <img src=x onerror=alert(9)> and a [link](javascript:alert(10)).

\`\`\`mermaid
graph TD
  A["<img src=x onerror=alert(11)>"] --> B
  click A call alert(12)
\`\`\`
`;
fs.writeFileSync(path.join(dir, "docs.json"), JSON.stringify(docs));
execFileSync("python3", [path.join(__dirname, "build.py"), dir], {stdio: "inherit"});

(async () => {
  const proxy = process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined;
  const browser = await chromium.launch({proxy});
  const page = await browser.newPage();
  const fired = [], errors = [];
  page.on("dialog", d => { fired.push(d.message()); d.dismiss(); });
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + path.join(dir, "spectio-board.html"));
  await page.evaluate(fx => openDoc(fx), FX);
  await page.waitForSelector("#doc-md .mermaid svg", {timeout: 30000});
  for (const a of await page.$$("#doc-md a")) await a.click({modifiers: []}).catch(() => {});
  await page.waitForTimeout(1000);
  const dom = await page.evaluate(() => {
    const el = document.querySelector("#doc-md");
    return {
      script: el.querySelectorAll("script, iframe").length,
      handlers: [...el.querySelectorAll("*")].filter(n => [...n.attributes].some(a => /^on/i.test(a.name))).length,
      badHref: [...el.querySelectorAll("a[href]")].filter(a => !/^(https?:|mailto:|#)/i.test(a.getAttribute("href"))).length,
      kept: !!el.querySelector('a[href="https://example.org"]'),
      admonition: !!el.querySelector(".adm .adm-t"),
    };
  });
  await browser.close();
  const fail = [];
  if (fired.length) fail.push("payload ran: " + fired.join(", "));
  if (errors.length) fail.push("page errors: " + errors.join(" | "));
  if (dom.script || dom.handlers || dom.badHref) fail.push("left in the DOM: " + JSON.stringify(dom));
  if (!dom.kept || !dom.admonition) fail.push("sanitising removed too much: " + JSON.stringify(dom));
  if (fail.length) { console.error("xss check FAILED\n" + fail.join("\n")); process.exit(1); }
  console.log("xss check ok: no payload ran, no handler, script or unsafe link left; mermaid rendered");
})().catch(e => { console.error(e); process.exit(1); });
