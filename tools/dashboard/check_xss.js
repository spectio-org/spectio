#!/usr/bin/env node
// Builds the dashboard with a hostile Markdown file added and fails if any payload runs, if the page requests anything
// from another site, if the Markdown leaves a script, handler, form control, style, unsafe link or remote media in the
// page, paints outside its own box, or can write an answer. It runs twice. The pass with the page's
// Content-Security-Policy proves the CSP does not break the page; Playwright logs a request even when the CSP blocks it,
// so it is the pass without the CSP that proves the sanitiser alone stops every remote request (the claude.ai host may
// not apply a <meta> CSP at all).
// node tools/dashboard/check_xss.js OUTDIR    (OUTDIR: gen.py's data.json, docs.json, imgs.json; left unchanged)
// The page loads marked, DOMPurify and mermaid from cdnjs with their integrity hashes, so a wrong hash fails here too.
const fs = require("fs"), os = require("os"), path = require("path"), {execFileSync} = require("child_process");
// Playwright: on NODE_PATH, or where dev/bootstrap.sh installs it (dev/lib.sh: $SPECTIO_HOME/npm/node_modules)
const {chromium} = (() => {
  const home = process.env.SPECTIO_HOME || path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local/share"), "spectio");
  for (const p of ["playwright", path.join(home, "npm/node_modules/playwright")]) { try { return require(p); } catch {} }
  console.error("check_xss.js: playwright not found; run dev/bootstrap.sh, or set NODE_PATH to a node_modules that has it");
  process.exit(2);
})();

const FX = "fixture/xss.md";
const FIXTURE = `# XSS fixture

<img src=x onerror=alert(1)>

<script>alert(2)</script>

[js link](javascript:alert(3)) [mixed case](JaVaScRiPt:alert(4)) [data link](data:text/html,<script>alert(5)</script>) [kept](https://example.org)

<iframe src="javascript:alert(6)"></iframe>

<svg><animate onbegin=alert(7) attributeName=x dur=1s /></svg>

<!--><img src=x onerror=alert(13)>--> <!-- --><img src=x onerror=alert(14)> -->

<button data-ans-rec="4">Accept</button> <a data-ans-del="4" class="dbtn">Withdraw</a>
<div class="act" data-act="4"><textarea data-ans-text="4">injected</textarea><button data-ans-own="4">Save</button></div>

<style>.act{display:none}</style> <div style="position:fixed;inset:0">overlay</div>

<form action="javascript:alert(15)"><input name="q"><select></select><button>go</button></form>

<svg><a xlink:href="javascript:alert(16)"><text>svg link</text></a><use href="data:image/svg+xml,<svg id='x'/>#x"/></svg>

<map><area href="javascript:alert(17)" shape="rect" coords="0,0,9,9"></map> <base href="javascript:alert(18)//"> <meta http-equiv="refresh" content="0;url=javascript:alert(19)">

<div id="doc-close" name="x">shadow id</div>

![remote](https://example.org/x.png) <video src="https://example.org/v.mp4" poster="https://example.org/p.png"><source src="https://example.org/v.webm"><track src="https://example.org/t.vtt" default></video>

<img srcset="https://example.org/s.png 1x"> <audio src="https://example.org/a.mp3" autoplay></audio> <picture><source srcset="https://example.org/p2.png"><img src="https://example.org/p3.png"></picture>

<table background="https://example.org/t.png"><tr><td background="https://example.org/td.png">cell</td></tr></table>

<svg width="20" height="20"><image href="https://example.org/i.png" width="10" height="10"/><image xlink:href="https://example.org/i2.png" width="10" height="10"/><filter><feImage href="https://example.org/fe.png"/></filter></svg> <math><mglyph src="https://example.org/g.png"></mglyph></math>

<svg width="20" height="20"><rect width="9" height="9" mask="url(https://example.org/m.svg#m)" filter="url(https://example.org/f.svg#f)" clip-path="url(https://example.org/c.svg#c)" fill="url(https://example.org/p.svg#p)"/><line x2="9" y2="9" stroke="red" marker-start="url(https://example.org/mk.svg#k)"/></svg>

<div class="lb">borrowed overlay class</div> <div class="docscrim">borrowed scrim class</div>

!!! note "<img src=x onerror=alert(8)>"
    Body <img src=x onerror=alert(9)> and a [link](javascript:alert(10)).

\`\`\`mermaid
graph TD
  A["<img src=x onerror=alert(11)>"] --> B
  B["<img src='https://example.org/m.png'>"] --> C
  C["<div class='act' data-act='4'><button data-ans-rec='4'>label button</button></div>"]
  click A call alert(12)
\`\`\`

\`\`\`mermaid
%%{init: {"themeCSS": ".node rect{fill:url(https://example.org/fill.svg#p)} foreignObject div{background-image:url(https://example.org/themecss.png)} .label{cursor:url(https://example.org/cur.png),auto}"}}%%
graph TD
  T1 --> T2
\`\`\`
`;

const src = process.argv[2], dir = fs.mkdtempSync(path.join(os.tmpdir(), "spectio-xss-"));
(async () => {
  for (const f of ["data.json", "imgs.json"]) fs.copyFileSync(path.join(src, f), path.join(dir, f));
  const docs = JSON.parse(fs.readFileSync(path.join(src, "docs.json"), "utf8"));
  docs[FX] = FIXTURE;
  fs.writeFileSync(path.join(dir, "docs.json"), JSON.stringify(docs));
  execFileSync("python3", [path.join(__dirname, "build.py"), dir], {stdio: "inherit"});

  const built = fs.readFileSync(path.join(dir, "spectio-board.html"), "utf8");
  const csp = /<meta http-equiv="Content-Security-Policy"[^>]*>\n?/;
  if (!csp.test(built)) { console.error("xss check FAILED\nthe page has no Content-Security-Policy meta"); process.exitCode = 1; return; }
  fs.writeFileSync(path.join(dir, "no-csp.html"), built.replace(csp, ""));
  const proxy = process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined;
  const browser = await chromium.launch({proxy});
  try {
    for (const [pass, file] of [["with CSP", "spectio-board.html"], ["without CSP", "no-csp.html"]]) await check(browser, pass, path.join(dir, file));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; })
  .finally(() => fs.rmSync(dir, {recursive: true, force: true}));

async function check(browser, pass, file) {
    const page = await browser.newPage();
    // the page owner, with a database that records every write
    await page.addInitScript(() => {
      window.__writes = [];
      const db = {collection: () => ({onSnapshot: f => setTimeout(() => f({docs: []}), 0)}),
                  doc: p => ({set: async b => window.__writes.push(["set", p, b]), delete: async () => window.__writes.push(["delete", p])})};
      window.claude = {use: async n => n === "db" ? db : n === "user" ? {isOwner: async () => true} : null};
    });
    const fired = [], errors = [], remote = [];
    page.on("dialog", d => { fired.push(d.message()); d.dismiss(); });
    page.on("pageerror", e => errors.push(e.message));
    // the page loads its three libraries from cdnjs; anything else from the network is a leak
    page.on("request", r => { const u = new URL(r.url()); if (/^(https?|wss?):$/.test(u.protocol) && u.host !== "cdnjs.cloudflare.com") remote.push(r.url()); });
    await page.goto("file://" + file);
    await page.waitForFunction(() => DB && OWNER);
    await page.evaluate(fx => openDoc(fx), FX);
    await page.waitForFunction(() => document.querySelectorAll("#doc-md .mermaid svg").length === 2, null, {timeout: 30000});
    // anything in the Markdown that looks like an answer control is clicked in the DOM (an overlay cannot block it), links by the mouse
    await page.$$eval("#doc-md button, #doc-md [class~='act'] *, #doc-md [data-ans-rec], #doc-md [data-ans-own], #doc-md [data-ans-del], #doc-md [data-ans-edit]", els => els.forEach(e => e.click()));
    for (const a of await page.$$("#doc-md a, #doc-md area")) await a.click({timeout: 2000}).catch(() => {});
    await page.waitForTimeout(1000);
    const dom = await page.evaluate(() => {
      const el = document.querySelector("#doc-md"), q = s => el.querySelectorAll(s).length;
      const url = /^(https?:|mailto:|#|data:image\/)/i;
      return {
        script: q("script, iframe, object, embed, base, meta"),
        handlers: [...el.querySelectorAll("*")].filter(n => [...n.attributes].some(a => /^on/i.test(a.name))).length,
        controls: [...el.querySelectorAll("[data-ans-rec], [data-ans-own], [data-ans-del], [data-ans-edit], [data-ans-text], [data-act], form, input, textarea, button:not([data-lb]), select")].length
          + [...el.querySelectorAll("style")].filter(n => !n.parentElement?.matches(".mermaid > svg")).length,  // mermaid's own SVG carries one <style>
        styled: [...el.querySelectorAll("[style]")].filter(n => !n.closest(".mermaid")).length,
        ids: [...el.querySelectorAll("[id], [name]")].filter(n => !/^(d-|mermaid)/.test(n.id) && !n.closest(".mermaid")).length,
        comments: (() => { const w = document.createTreeWalker(el, NodeFilter.SHOW_COMMENT); let n = 0; while (w.nextNode()) if (!/^cls:[\w-]+$/.test(w.currentNode.data)) n++; return n; })(),
        badHref: [...el.querySelectorAll("a[href], area[href], form[action], [*|href]")].map(a => a.getAttribute("href") ?? a.getAttribute("action") ?? a.getAttributeNS("http://www.w3.org/1999/xlink", "href") ?? "").filter(h => !url.test(h)).length,
        remoteMedia: [...el.querySelectorAll("img[src], video[src], video[poster], source[src], [srcset], [background], audio, track, image, feImage, mglyph")].filter(m => !/^data:/.test(m.getAttribute("src") ?? m.getAttribute("poster") ?? "")).length,
        outside: (() => { const b = el.getBoundingClientRect(); return [...el.querySelectorAll("*")].filter(n => { const r = n.getBoundingClientRect();
          return r.width && r.height && (r.left < b.left - 1 || r.top < b.top - 1 || r.right > b.right + 1 || r.bottom > b.bottom + 1); }).length; })(),
        writes: window.__writes.length,
        kept: !!el.querySelector('a[href="https://example.org"]'),
        admonition: !!el.querySelector(".adm .adm-t"),
      };
    });
    const fail = [];
    if (fired.length) fail.push("payload ran: " + fired.join(", "));
    if (errors.length) fail.push("page errors: " + errors.join(" | "));
    if (remote.length) fail.push("remote request: " + remote.join(", "));
    const bad = ["script", "handlers", "controls", "styled", "ids", "comments", "badHref", "remoteMedia", "outside", "writes"].filter(k => dom[k]);
    if (bad.length) fail.push("left in the DOM or done: " + bad.map(k => `${k}=${dom[k]}`).join(" "));
    if (!dom.kept || !dom.admonition) fail.push("sanitising removed too much: " + JSON.stringify(dom));
    await page.close();
    if (fail.length) { console.error(`xss check FAILED (${pass})\n` + fail.join("\n")); process.exitCode = 1; }
    else console.log(`xss check ok (${pass}): no payload ran, no remote request, no answer written, nothing unsafe left; mermaid rendered`);
}
