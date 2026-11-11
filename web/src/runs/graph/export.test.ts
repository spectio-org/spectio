import { expect, test } from "vitest";
import { escapeXml, toHtml, toSvg } from "./export";
import { DOC } from "./fixture";
import { place } from "./layout";
import { collapse } from "./model";

test("the SVG has every node, every edge, and escapes pipeline text", () => {
  const doc = { ...DOC, nodes: DOC.nodes.map((n, i) => (i === 0 ? { ...n, name: '<script>alert("x")</script>' } : n)) };
  const view = collapse(doc, "process");
  const svg = toSvg(view, place(view, "metro"), "run & co");
  expect(svg.startsWith("<svg")).toBe(true);
  expect(svg).not.toContain("<script>");
  expect(svg).toContain("&lt;script&gt;");
  expect(svg).toContain("<title>run &amp; co</title>");
  expect(svg.match(/<line /g)).toHaveLength(view.edges.length);
  expect(new DOMParser().parseFromString(svg, "image/svg+xml").querySelector("parsererror")).toBeNull();
});

test("escapeXml", () => {
  expect(escapeXml(`a<b>&"'`)).toBe("a&lt;b&gt;&amp;&quot;&apos;");
});

test("the HTML page has the drawing and one table row per box, with no script", () => {
  const doc = { ...DOC, nodes: DOC.nodes.map((n, i) => (i === 0 ? { ...n, name: "<img src=x onerror=alert(1)>" } : n)) };
  const view = collapse(doc, "process");
  const html = toHtml(view, place(view, "layered-tb"), "run <1>", "nextflow");
  const page = new DOMParser().parseFromString(html, "text/html");
  expect(page.querySelector("script, img")).toBeNull();
  expect(page.querySelector("svg")).not.toBeNull();
  expect(page.querySelectorAll("tbody tr")).toHaveLength(view.nodes.length);
  expect(page.title).toBe("run <1> · workflow graph");
});
