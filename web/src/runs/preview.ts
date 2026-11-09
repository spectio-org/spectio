// The pure parts of the file preview (ui-spec §4.4.1, FU-P3-85c): a file's kind from its name,
// and the caps that keep the text, JSON and table viewers inside a bounded DOM and CPU budget.
// Everything here returns text; the page puts it in the DOM as text nodes only.

export type Kind = "text" | "table" | "json" | "image" | "tiff" | "ometiff" | "omezarr" | "html" | "pdf" | "binary" | "file";

export const KIND_WORDS: Record<Kind | "folder" | "link", string> = {
  folder: "Folder",
  text: "Text",
  table: "Table",
  json: "JSON",
  image: "Image",
  tiff: "TIFF",
  ometiff: "OME-TIFF",
  omezarr: "OME-Zarr",
  html: "HTML report",
  pdf: "PDF",
  binary: "Binary",
  file: "File",
  link: "Link outside",
};

/** The kind's word; in a work directory an HTML file is "HTML (not opened)" (ui-spec §4.4.1). */
export const kindWord = (kind: keyof typeof KIND_WORDS, work: boolean) => (work && kind === "html" ? "HTML (not opened)" : KIND_WORDS[kind]);

const words = (list: string) => new Set(list.split(" "));
const BY_SUFFIX: [Kind, Set<string>][] = [
  ["text", words("txt log out err yml yaml md fa fasta fq fastq sam vcf bed gtf gff gff3 nf smk py r sh config")],
  ["table", words("csv tsv tab")],
  ["json", words("json")],
  ["image", words("png jpg jpeg gif webp svg")],
  ["tiff", words("tif tiff")],
  ["html", words("html htm")],
  ["pdf", words("pdf")],
  [
    "binary",
    words(
      "gz bgz bz2 xz zst 7z zip tar bam cram bai crai csi tbi bcf bw bigwig bb 2bit h5 hdf5 h5ad loom npy npz pod5 fast5 rds rda rdata pkl parquet sqlite db xlsx xls docx",
    ),
  ],
];

/** The kind of a file from its name only (the server decides what it serves); extensions
 * compare without case. */
export function fileKind(name: string): Kind {
  const base = name.split("/").pop() ?? name;
  if (/.\.ome\.tiff?$/i.test(base)) return "ometiff";
  if (/.\.ome\.zarr$/i.test(base)) return "omezarr"; // a folder (ui-spec §4.4.1, imaging)
  const dot = base.lastIndexOf(".");
  const suffix = dot > 0 ? base.slice(dot + 1).toLowerCase() : "";
  return BY_SUFFIX.find(([, set]) => set.has(suffix))?.[0] ?? "file";
}

/** The run logs' level tints and filter, for these names only. */
export const hasLevels = (name: string) => /\.(log|out|err)$/i.test(name);

export const KIB = 1024;
export const MIB = 1024 * KIB;
export const READ = 64 * KIB; // one read (api §5.3: the default tail, and Load more's step)
export const SHOWN_MAX = MIB; // the most text shown, and the table's and JSON's one read
export const IMAGE_MAX = 20 * MIB;
export const SVG_MAX = 5 * MIB;
export const LINES_MAX = 20000;
export const LINE_MAX = 10000;
export const JSON_DEPTH_MAX = 64;
export const JSON_FORMATTED_MAX = 2 * MIB;
export const ROWS_MAX = 500;
export const COLUMNS_MAX = 50;
export const CELL_MAX = 1000;

/** "120 B", "2.4 KiB", "3.1 MiB", "2.1 GiB". */
export function size(n: number): string {
  if (n < KIB) return `${n} B`;
  const [value, unit] = n < MIB ? [n / KIB, "KiB"] : n < 1024 * MIB ? [n / MIB, "MiB"] : [n / (1024 * MIB), "GiB"];
  return `${Number.isInteger(value) ? value : value.toFixed(1)} ${unit}`;
}

/** The lines to render: at most LINES_MAX, each cut at LINE_MAX characters. A final newline ends
 * the last line. Reads at most what it keeps, so 1 MiB of newlines costs 20,000 lines. */
export function capLines(text: string): { lines: string[]; capped: boolean } {
  const lines: string[] = [];
  let at = 0;
  while (at < text.length && lines.length < LINES_MAX) {
    const end = text.indexOf("\n", at);
    const stop = end === -1 ? text.length : end;
    lines.push(stop - at > LINE_MAX ? `${text.slice(at, at + LINE_MAX)} … line cut: Download to see it whole` : text.slice(at, stop));
    at = stop + 1;
  }
  return { lines, capped: at < text.length };
}

/** An End read starts inside a line: it is shown from its first whole line. */
export function wholeLines(text: string): string {
  const end = text.indexOf("\n");
  return end === -1 ? text : text.slice(end + 1);
}

const TOO_BIG = "Not shown formatted: too deeply nested or too large";

/** The formatted view of a JSON file read whole, or why it is shown as text: a linear pre-scan
 * refuses a depth over 64 before JSON.parse runs, and the formatted text is capped at 2 MiB. */
export function jsonView(text: string): { text: string } | { fallback: string } {
  let depth = 0;
  let inString = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inString) {
      if (c === "\\") i++;
      else if (c === '"') inString = false;
    } else if (c === '"') inString = true;
    else if (c === "[" || c === "{") {
      if (++depth > JSON_DEPTH_MAX) return { fallback: TOO_BIG };
    } else if (c === "]" || c === "}") depth--;
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    return { fallback: "Not valid JSON: shown as text" };
  }
  const formatted = JSON.stringify(value, null, 2);
  return formatted.length > JSON_FORMATTED_MAX ? { fallback: TOO_BIG } : { text: formatted };
}

export interface Table {
  comments: string[]; // the leading lines that start with #
  rows: string[][];
  stopped: boolean; // the parser stopped after ROWS_MAX + 2 rows: more follow
}

const cell = (value: string) => (value.length > CELL_MAX ? `${value.slice(0, CELL_MAX)}…` : value);

/** A CSV (RFC 4180, quoted fields) or TSV (tabs only) read: at most a header and 501 rows,
 * each cell cut at 1,000 characters. `cut`: the read stopped before the file's end, so its
 * last row may be partial and is dropped (a row in an unclosed quote included). */
export function parseTable(text: string, format: "csv" | "tsv", cut: boolean): Table {
  const comments: string[] = [];
  let at = 0;
  while (text.startsWith("#", at)) {
    const end = text.indexOf("\n", at);
    if (end === -1) {
      if (!cut) comments.push(text.slice(at).replace(/\r$/, ""));
      return { comments, rows: [], stopped: false };
    }
    comments.push(text.slice(at, end).replace(/\r$/, ""));
    at = end + 1;
  }
  const limit = ROWS_MAX + 2;
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  let ended = true; // the last row was ended by a newline
  const endField = () => {
    row.push(cell(field));
    field = "";
  };
  const endRow = () => {
    endField();
    rows.push(row);
    row = [];
  };
  for (let i = at; i < text.length && rows.length < limit; i++) {
    const c = text[i];
    ended = false;
    if (format === "csv" && quoted) {
      if (c === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (c === '"') quoted = false;
      else if (field.length <= CELL_MAX) field += c;
    } else if (format === "csv" && c === '"' && field === "") quoted = true;
    else if (c === (format === "csv" ? "," : "\t")) endField();
    else if (c === "\n") {
      if (field.endsWith("\r")) field = field.slice(0, -1);
      endRow();
      ended = true;
    } else if (field.length <= CELL_MAX) field += c;
  }
  const stopped = rows.length >= limit;
  if (!stopped && !ended && !cut) endRow(); // the last row of a whole read, with no final newline
  return { comments, rows, stopped };
}
