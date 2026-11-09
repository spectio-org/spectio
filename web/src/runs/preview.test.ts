// The pure parts of the file preview (ui-spec §4.4.1, FU-P3-85c): kinds from the name, the DOM
// and CPU caps of the text, JSON and table viewers, and the End read's first whole line.
import { expect, test } from "vitest";
import { capLines, fileKind, jsonView, parseTable, wholeLines } from "./preview";

test("the kind comes from the name only, without case", () => {
  expect(fileKind("a/S01.LOG")).toBe("text");
  expect(fileKind("counts.tsv")).toBe("table");
  expect(fileKind("x.Tab")).toBe("table");
  expect(fileKind("stats.json")).toBe("json");
  expect(fileKind("plot.SVG")).toBe("image");
  expect(fileKind("report.htm")).toBe("html");
  expect(fileKind("doc.pdf")).toBe("pdf");
  expect(fileKind("reads.fastq.gz")).toBe("binary");
  expect(fileKind("S01.bam")).toBe("binary");
  expect(fileKind("quant.sf")).toBe("file");
  expect(fileKind("README")).toBe("file");
});

test("1 MiB of newlines renders at most 20,000 lines", () => {
  const started = performance.now();
  const shown = capLines("\n".repeat(1 << 20));
  expect(shown.lines).toHaveLength(20000);
  expect(shown.capped).toBe(true);
  expect(performance.now() - started).toBeLessThan(1000);
});

test("a line over 10,000 characters is cut there and says so", () => {
  const shown = capLines(`short\n${"x".repeat(25000)}\nend\n`);
  expect(shown.capped).toBe(false);
  expect(shown.lines).toHaveLength(3);
  expect(shown.lines[1].startsWith("x".repeat(10000))).toBe(true);
  expect(shown.lines[1]).toContain("line cut: Download to see it whole");
  expect(shown.lines[1].length).toBeLessThan(10100);
});

test("a final newline ends the last line; it does not add an empty one", () => {
  expect(capLines("a\nb\n").lines).toEqual(["a", "b"]);
  expect(capLines("a\nb").lines).toEqual(["a", "b"]);
});

test("an End read starts at its first whole line", () => {
  expect(wholeLines("rtial line\nwhole 1\nwhole 2\n")).toBe("whole 1\nwhole 2\n");
  expect(wholeLines("no newline at all")).toBe("no newline at all");
});

test("JSON 10,000 deep is refused by the pre-scan, not parsed", () => {
  const deep = "[".repeat(10000) + "]".repeat(10000);
  expect(jsonView(deep)).toEqual({ fallback: "Not shown formatted: too deeply nested or too large" });
  const ok = "[".repeat(64) + "]".repeat(64);
  expect("text" in jsonView(ok)).toBe(true);
});

test("brackets inside strings do not count toward the depth", () => {
  const text = JSON.stringify({ a: "[".repeat(200) + '\\"{' });
  expect(jsonView(text)).toEqual({ text: JSON.stringify(JSON.parse(text), null, 2) });
});

test("a formatted view over 2 MiB falls back to text", () => {
  // 500,000 small numbers: under 1 MiB as written, over 2 MiB once indented
  const text = `[${Array.from({ length: 500000 }, () => "1").join(",")}]`;
  expect(text.length).toBeLessThan(1 << 20);
  expect(jsonView(text)).toEqual({ fallback: "Not shown formatted: too deeply nested or too large" });
});

test("not valid JSON is shown as text", () => {
  expect(jsonView('{"a": ')).toEqual({ fallback: "Not valid JSON: shown as text" });
});

test("a big integer and a repeated key are formatted as JSON.parse reads them", () => {
  // the formatted view says they may differ; Show as text gives the file as written
  expect(jsonView('{"n": 12345678901234567890}')).toEqual({ text: '{\n  "n": 12345678901234567000\n}' });
  expect(jsonView('{"a": 1, "a": 2}')).toEqual({ text: '{\n  "a": 2\n}' });
});

test("CSV with quoted fields, quotes doubled and newlines in a field (RFC 4180)", () => {
  const table = parseTable('name,note\r\nS01,"a, b"\r\nS02,"say ""hi"""\r\nS03,"two\nlines"\r\n', "csv", false);
  expect(table.rows).toEqual([
    ["name", "note"],
    ["S01", "a, b"],
    ["S02", 'say "hi"'],
    ["S03", "two\nlines"],
  ]);
  expect(table.stopped).toBe(false);
});

test("a CSV with an unclosed quote keeps the rest as one cell, cut at 1,000 characters", () => {
  const rest = "x,".repeat(5000);
  const table = parseTable(`a,b\n1,"open ${rest}\n2,3\n`, "csv", false);
  expect(table.rows).toHaveLength(2);
  expect(table.rows[1][1].length).toBe(1001);
  expect(table.rows[1][1].endsWith("…")).toBe(true);
});

test("a cut read drops its partial last row, an unclosed quote included", () => {
  expect(parseTable("a,b\n1,2\n3,", "csv", true).rows).toEqual([["a", "b"], ["1", "2"]]);
  expect(parseTable('a,b\n1,2\n3,"open\n4', "csv", true).rows).toEqual([["a", "b"], ["1", "2"]]);
});

test("TSV splits on tabs only; leading # lines are kept apart", () => {
  const table = parseTable("# MultiQC custom content\n# id: align\nSample\tAligned, %\nS01\t91.2\n", "tsv", false);
  expect(table.comments).toEqual(["# MultiQC custom content", "# id: align"]);
  expect(table.rows).toEqual([
    ["Sample", "Aligned, %"],
    ["S01", "91.2"],
  ]);
});

test("the parser stops after 502 rows: a header and 501 rows", () => {
  const text = Array.from({ length: 5000 }, (_, i) => `r${i},${i}`).join("\n");
  const table = parseTable(text, "csv", false);
  expect(table.rows).toHaveLength(502);
  expect(table.stopped).toBe(true);
});
