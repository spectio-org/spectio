// The preview page of one results file (ui-spec §4.4.1, FU-P3-85c; boards LiteFilePreview,
// MLiteFilePreview and LiteFilePreviewStates; api §5.3): stat first, then the viewer of its kind,
// its caps, and every state.
import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, stubStream, viewport } from "../testing";

// jsdom has no Worker: the decodes run in the page, through the worker's own decodeTile
vi.mock("./imaging/pool", async () => {
  const { decodeTile } = await import("./imaging/decode");
  return { DecoderPool: class { decode = decodeTile; destroy() {} } };
});

beforeEach(stubStream);
afterEach(() => (vi.unstubAllGlobals(), vi.restoreAllMocks()));

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const RUN = `/api/v1/runs/${ID}`;
const ROOT = "/g/demo-lab/rnaseq/2026-10-25";
const T = "2026-10-31T09:02:00+00:00";
const KIB = 1024;

const stat = (path: string, size: number | null, type = "file") => ({ root: ROOT, path, name: path.split("/").pop(), type, size, mtime: T });
const text = (body: string, init: ResponseInit = {}) => new Response(body, { status: 200, ...init, headers: { "content-type": "text/plain; charset=utf-8", ...init.headers } });
const partial = (body: string, first: number, last: number, size: number) => text(body, { status: 206, headers: { "content-range": `bytes ${first}-${last}/${size}` } });
const enc = (path: string) => path.split("/").map(encodeURIComponent).join("/");

/** The run, the stat of `path` and its reads, by the answers given. */
function files(path: string, size: number | null, reads: Record<string, unknown> = {}, over: Record<string, unknown> = {}) {
  return serve({
    [`${RUN}/results/stat/${enc(path)}`]: stat(path, size),
    ...reads,
    [RUN]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25", ended_at: T }), results_dir: ROOT, ...over },
  });
}
const open = (path: string) => app(`/runs/${ID}/results/file?path=${encodeURIComponent(path)}`);
const heading = (name: string) => screen.findByRole("heading", { level: 1, name });
const rangeOf = (init?: RequestInit) => new Headers(init?.headers).get("range");
// The grid's body cells in row order (the filter row's cells are gridcells too), and one column's.
const bodyCells = (grid: HTMLElement) => within(grid).getAllByRole("gridcell").filter((c) => !c.closest(".ag-header"));
const cellTexts = (grid: HTMLElement) => bodyCells(grid).map((c) => c.textContent);
const column = (grid: HTMLElement, i: number) =>
  bodyCells(grid)
    .filter((c) => c.getAttribute("aria-colindex") === String(i + 1))
    .map((c) => c.textContent);

test("stat first, then the whole file: facts, path, Copy path, Download, focus on the name", async () => {
  const mock = files("pipeline_info/versions.yml", 12, { [`${RUN}/results/text/pipeline_info/versions.yml`]: () => text("a: 1\nb: 2\n") });
  open("pipeline_info/versions.yml");
  const h1 = await heading("versions.yml");
  await waitFor(() => expect(h1).toHaveFocus());
  expect(await screen.findByText("Whole file · 12 B")).toBeInTheDocument();
  expect(screen.getByText(/^Text · 12 B · /)).toBeInTheDocument();
  expect(screen.getByText(`${ROOT}/pipeline_info/versions.yml`)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy path" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download versions.yml" }).getAttribute("href")).toBe(`${RUN}/results/raw/pipeline_info/versions.yml?download=true`);
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Start" })).toBeNull();
  const urls = fetched(mock).filter((u) => u.includes("/results/"));
  expect(urls[0]).toBe(`${RUN}/results/stat/pipeline_info/versions.yml`);
  // the back link and the path bar name the folder; the page title names the file and the run
  const folders = screen.getAllByRole("link", { name: "pipeline_info" });
  expect(folders).toHaveLength(2); // the back link (which returns to the file's row), and the path bar
  expect(folders[0].getAttribute("href")).toBe(`/runs/${ID}/results?path=pipeline_info&focus=versions.yml`);
  expect(folders[1].getAttribute("href")).toBe(`/runs/${ID}/results?path=pipeline_info`);
  const bar = screen.getByRole("navigation", { name: "Folder" });
  expect(within(bar).getByText("versions.yml")).toHaveAttribute("aria-current", "page");
  await waitFor(() => expect(document.title).toBe("versions.yml · rnaseq-2026-10-25 · Spectio"));
  // a .yml has no level filter; the lines are numbered from 1
  expect(screen.queryByRole("group", { name: "Show lines" })).toBeNull();
  const viewer = screen.getByLabelText(/versions.yml, whole file/, { selector: "pre" });
  expect([...viewer.querySelectorAll("[data-gutter]")].map((g) => g.textContent)).toEqual(["1", "2"]);
});

test("a large file reads from the start; Load more reads from the Content-Range end + 1 and joins the text", async () => {
  const size = 200 * KIB;
  const ranges: (string | null)[] = [];
  files("big.log", size, {
    [`${RUN}/results/text/big.log`]: (_url: URL, init?: RequestInit) => {
      const range = rangeOf(init);
      ranges.push(range);
      // the first read ends one byte short of 64 KiB, before a 2-byte é: the next starts there
      if (range === "bytes=0-65535") return partial("line one\nhalf caf", 0, 65534, size);
      return partial("é done\nline three\n", 65535, 131070, size);
    },
  });
  open("big.log");
  await heading("big.log");
  expect(await screen.findByText(/… cut at 64 KiB/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "End" })).toHaveAttribute("aria-pressed", "false");
  const more = screen.getByRole("button", { name: "Load more" });
  more.focus();
  fireEvent.click(more);
  await screen.findByText(/^half café done/);
  expect(ranges).toEqual(["bytes=0-65535", "bytes=65535-131070"]);
  expect(screen.queryByText(/… cut at 64 KiB/)).toBeNull();
  expect(screen.getByText("128 KiB shown")).toHaveAttribute("aria-live", "polite");
  expect(more).toHaveFocus();
  // .log keeps the level filter
  expect(screen.getByRole("group", { name: "Show lines" })).toBeInTheDocument();
  expect(screen.getByText("Search covers the 128 KiB shown")).toBeInTheDocument();
});

test("End reads the last 64 KiB from its first whole line, with no line numbers", async () => {
  const size = 300 * KIB;
  files("trace.txt", size, {
    [`${RUN}/results/text/trace.txt`]: (url: URL, init?: RequestInit) =>
      rangeOf(init) ? partial("first\n", 0, 5, size) : url.searchParams.get("tail") === "65536" ? text("tial\nlast one\nlast two\n") : json(400, {}),
  });
  open("trace.txt");
  await heading("trace.txt");
  fireEvent.click(await screen.findByRole("button", { name: "End" }));
  expect(await screen.findByText("Last 64 KiB of 300 KiB: line numbers not known")).toBeInTheDocument();
  const viewer = screen.getByLabelText(/trace.txt, last 64 KiB/, { selector: "pre" });
  expect(viewer.textContent).toBe("last one\nlast two\n");
  expect(viewer.querySelector("[data-gutter]")).toBeNull();
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
});

test("at 1 MiB shown Load more stops and focus moves to the line that says so", async () => {
  const size = 3 * 1024 * KIB;
  const line = `${"x".repeat(1023)}\n`;
  files("huge.txt", size, {
    [`${RUN}/results/text/huge.txt`]: (_url: URL, init?: RequestInit) => {
      const [first, last] = rangeOf(init)!.slice(6).split("-").map(Number);
      return partial(line.repeat((last - first + 1) / 1024), first, last, size);
    },
  });
  open("huge.txt");
  await heading("huge.txt");
  for (let i = 1; i < 16; i++) {
    fireEvent.click(await screen.findByRole("button", { name: "Load more" }));
    await screen.findByText(`${(i + 1) * 64} KiB shown`);
  }
  const cap = await screen.findByText("Showing the first 1 MiB of 3 MiB. Download to see the rest.");
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  expect(cap).toHaveAttribute("tabindex", "-1");
  await waitFor(() => expect(cap).toHaveFocus());
});

test("at most 20,000 lines are rendered", async () => {
  files("newlines.txt", 64 * KIB, { [`${RUN}/results/text/newlines.txt`]: () => text("\n".repeat(64 * KIB)) });
  open("newlines.txt");
  expect(await screen.findByText("Showing the first 20,000 lines. Download to see the rest.", {}, { timeout: 10000 })).toBeInTheDocument();
  const viewer = screen.getByLabelText(/newlines.txt/, { selector: "pre" });
  expect(viewer.children.length).toBe(20000);
}, 30000);

test("a first read of more than 20,000 lines leaves focus on the file name (CR-P3FU85C-06)", async () => {
  files("newlines.txt", 64 * KIB, { [`${RUN}/results/text/newlines.txt`]: () => text("\n".repeat(64 * KIB)) });
  open("newlines.txt");
  const h1 = await heading("newlines.txt");
  await waitFor(() => expect(h1).toHaveFocus());
  await screen.findByText("Showing the first 20,000 lines. Download to see the rest.", {}, { timeout: 10000 });
  expect(h1).toHaveFocus();
}, 30000);

test("at 20,000 lines from the start Load more stops, and nothing says the text is cut at 64 KiB", async () => {
  const size = 200 * KIB;
  files("lines.txt", size, { [`${RUN}/results/text/lines.txt`]: () => partial("\n".repeat(64 * KIB), 0, 64 * KIB - 1, size) });
  open("lines.txt");
  expect(await screen.findByText("Showing the first 20,000 lines. Download to see the rest.", {}, { timeout: 10000 })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  expect(screen.queryByText(/… cut at/)).toBeNull();
  expect(screen.getByText("Search covers the 20,000 lines shown")).toBeInTheDocument();
}, 30000);

test("a Load more that crosses 20,000 lines moves focus to the one line that says so (CR-P3FU85C-04)", async () => {
  const size = 200 * KIB;
  files("rows.txt", size, {
    [`${RUN}/results/text/rows.txt`]: (_url: URL, init?: RequestInit) => {
      const [first, last] = rangeOf(init)!.slice(6).split("-").map(Number);
      return partial("abc\n".repeat((last - first + 1) / 4), first, last, size);
    },
  });
  open("rows.txt");
  await heading("rows.txt");
  const more = await screen.findByRole("button", { name: "Load more" });
  more.focus();
  fireEvent.click(more);
  const cap = await screen.findByText("Showing the first 20,000 lines. Download to see the rest.", {}, { timeout: 10000 });
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  expect(cap).toHaveAttribute("tabindex", "-1");
  await waitFor(() => expect(cap).toHaveFocus());
  expect(screen.getAllByText(/^Showing the first/)).toHaveLength(1);
}, 30000);

test("a Load more still in flight is dropped when End is pressed, and the button stays enabled and focused while it loads", async () => {
  const size = 200 * KIB;
  let land: (r: Response) => void = () => {};
  const reads: string[] = [];
  files("slow.log", size, {
    [`${RUN}/results/text/slow.log`]: (url: URL, init?: RequestInit) => {
      const range = rangeOf(init);
      reads.push(range ?? url.search);
      if (range === "bytes=0-65535") return partial("from the start\n", 0, 65535, size);
      if (range) return new Promise<Response>((resolve) => (land = resolve));
      return text("tial\nthe end\n");
    },
  });
  open("slow.log");
  await heading("slow.log");
  const more = await screen.findByRole("button", { name: "Load more" });
  more.focus();
  fireEvent.click(more);
  await waitFor(() => expect(more).toHaveAttribute("aria-busy", "true"));
  expect(more).not.toBeDisabled();
  expect(more).toHaveFocus();
  fireEvent.click(more); // ignored while it loads
  expect(reads.filter((r) => r.startsWith("bytes=65536"))).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "End" }));
  const viewer = await screen.findByLabelText(/slow.log, last 64 KiB/, { selector: "pre" });
  await waitFor(() => expect(viewer.textContent).toBe("the end\n"));
  await act(async () => land(partial("stale chunk\n", 65536, 131071, size)));
  expect(screen.getByLabelText(/slow.log, last 64 KiB/, { selector: "pre" }).textContent).toBe("the end\n");
});

test("Wrap lines is a pressed button, off on a desktop", async () => {
  files("a.txt", 4, { [`${RUN}/results/text/a.txt`]: () => text("abc\n") });
  open("a.txt");
  const wrap = await screen.findByRole("button", { name: "Wrap lines" });
  expect(wrap).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(wrap);
  expect(wrap).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByLabelText(/a.txt, whole file/, { selector: "pre" })).toHaveAttribute("data-wrap");
});

test("on the phone the search is behind a Search button that opens it and moves focus into it (CR-P3FU85C-05)", async () => {
  viewport(390);
  files("a.log", 4, { [`${RUN}/results/text/a.log`]: () => text("abc\n") });
  open("a.log");
  const search = await screen.findByRole("button", { name: "Search" });
  expect(search).toHaveAttribute("aria-expanded", "false");
  // FU-P3-104: the same button style as Wrap lines beside it
  expect(search.className).toBe(screen.getByRole("button", { name: "Wrap lines" }).className);
  expect(screen.queryByRole("searchbox")).toBeNull();
  fireEvent.click(search);
  expect(search).toHaveAttribute("aria-expanded", "true");
  await waitFor(() => expect(screen.getByRole("searchbox", { name: /Search the a.log/ })).toHaveFocus());
});

test("on a desktop the search field is shown, with no Search button", async () => {
  files("a.log", 4, { [`${RUN}/results/text/a.log`]: () => text("abc\n") });
  open("a.log");
  expect(await screen.findByRole("searchbox", { name: /Search the a.log/ })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Search" })).toBeNull();
});

test("on the phone Wrap lines starts on", async () => {
  viewport(390);
  files("a.txt", 4, { [`${RUN}/results/text/a.txt`]: () => text("abc\n") });
  open("a.txt");
  expect(await screen.findByRole("button", { name: "Wrap lines" })).toHaveAttribute("aria-pressed", "true");
});

test("JSON is formatted, with the line on what may differ, and Show as text gives it as written", async () => {
  const body = '{"n": 12345678901234567890, "a": 1, "a": 2}';
  files("stats.json", body.length, { [`${RUN}/results/text/stats.json`]: () => text(body) });
  open("stats.json");
  expect(await screen.findByText("Formatted view: large numbers and repeated keys may differ")).toBeInTheDocument();
  const formatted = screen.getByLabelText(/stats.json, formatted/, { selector: "pre" });
  expect(formatted.textContent).toContain('"n": 12345678901234567000');
  expect(formatted.textContent).not.toContain('"a": 1');
  const toggle = screen.getByRole("button", { name: "Show as text" });
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByLabelText(/stats.json, whole file/, { selector: "pre" }).textContent).toContain(body);
});

test("JSON 10,000 deep falls back to text and says why", async () => {
  const body = "[".repeat(10000) + "]".repeat(10000);
  files("deep.json", body.length, { [`${RUN}/results/text/deep.json`]: () => text(body) });
  open("deep.json");
  expect(await screen.findByText("Not shown formatted: too deeply nested or too large")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Show as text" })).toBeNull();
});

test("JSON over 1 MiB is read as text from the start", async () => {
  const size = 2 * 1024 * KIB;
  files("big.json", size, { [`${RUN}/results/text/big.json`]: () => partial('{"a": 1,', 0, 7, size) });
  open("big.json");
  expect(await screen.findByText("Not shown formatted: larger than 1 MiB")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Load more" })).toBeInTheDocument();
});

test("a CSV is a grid from the first 1 MiB, the first row a header until the toggle says not", async () => {
  const body = 'sample,"reads, M"\nS01,42\nS02,"open\n';
  const ranges: (string | null)[] = [];
  files("counts.csv", body.length, {
    [`${RUN}/results/text/counts.csv`]: (_url: URL, init?: RequestInit) => {
      ranges.push(rangeOf(init));
      return partial(body, 0, body.length - 1, body.length);
    },
  });
  open("counts.csv");
  const region = await screen.findByRole("region", { name: "counts.csv, table" });
  expect(ranges).toEqual([`bytes=0-${1024 * KIB - 1}`]);
  const grid = await within(region).findByRole("grid", { name: "counts.csv" });
  expect(within(grid).getByRole("columnheader", { name: "reads, M" })).toBeInTheDocument();
  expect(grid).toHaveAttribute("aria-rowcount", "4"); // the names and the filters, then S01, S02 with its unclosed quote
  expect(cellTexts(grid)).toEqual(["S01", "42", "S02", "open\n"]);
  const header = screen.getByRole("button", { name: "First row is a header" });
  expect(header).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(header);
  const plain = await within(region).findByRole("grid", { name: "counts.csv" });
  expect(await within(plain).findByRole("columnheader", { name: "Column 2" })).toBeInTheDocument();
  expect(within(plain).getByRole("gridcell", { name: "reads, M" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Show as text" }));
  expect(await screen.findByLabelText(/counts.csv/, { selector: "pre" })).toBeInTheDocument();
});

test("a table cut at 500 rows and 50 columns says so", async () => {
  const row = Array.from({ length: 60 }, (_, i) => `c${i}`).join(",");
  const body = Array.from({ length: 700 }, () => row).join("\n");
  files("wide.csv", body.length, { [`${RUN}/results/text/wide.csv`]: () => partial(body, 0, body.length - 1, body.length) });
  open("wide.csv");
  const region = await screen.findByRole("region", { name: "wide.csv, table" });
  expect(screen.getByText("Showing 500 of at least 501 rows")).toBeInTheDocument();
  expect(screen.getByText("Showing 50 of 60 columns")).toBeInTheDocument();
  const grid = await within(region).findByRole("grid", { name: "wide.csv" });
  expect(grid).toHaveAttribute("aria-rowcount", "502"); // two header rows, then 500
  expect(grid).toHaveAttribute("aria-colcount", "50");
  expect(within(grid).getAllByRole("columnheader")).toHaveLength(50);
});

test("a column sorts from the keyboard, numbers as numbers, and focus moves to a cell with the arrows", async () => {
  const body = "n,name\n10,ten\n9,nine\n100,hundred\nx,ex\n";
  files("n.csv", body.length, { [`${RUN}/results/text/n.csv`]: () => partial(body, 0, body.length - 1, body.length) });
  open("n.csv");
  const grid = await screen.findByRole("grid", { name: "n.csv" });
  const n = within(grid).getByRole("columnheader", { name: "n" });
  expect(n).toHaveAttribute("aria-sort", "none");
  act(() => n.focus());
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(n).toHaveAttribute("aria-sort", "ascending"));
  expect(column(grid, 0)).toEqual(["9", "10", "100", "x"]);
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(n).toHaveAttribute("aria-sort", "descending"));
  expect(column(grid, 0)).toEqual(["x", "100", "10", "9"]);
  // the header row, the filter row, then the first row's cell
  await userEvent.keyboard("{ArrowDown}{ArrowDown}");
  await waitFor(() => expect(document.activeElement).toHaveAttribute("role", "gridcell"));
  expect(document.activeElement).toHaveTextContent("x");
});

test("a column filters on what its box contains; cells are text, never markup", async () => {
  const body = "id,note\na1,<b>bold</b>\nb2,plain\na3,other\n";
  files("f.csv", body.length, { [`${RUN}/results/text/f.csv`]: () => partial(body, 0, body.length - 1, body.length) });
  open("f.csv");
  const grid = await screen.findByRole("grid", { name: "f.csv" });
  expect(within(grid).getByRole("gridcell", { name: "<b>bold</b>" })).toBeInTheDocument();
  expect(grid.querySelector("b")).toBeNull();
  await userEvent.type(within(grid).getByRole("textbox", { name: "id Filter Input" }), "a");
  await waitFor(() => expect(column(grid, 0)).toEqual(["a1", "a3"]));
  // the filtered column's funnel and the box's clear button are our SVG: AG Grid's icon set is
  // left out, so an empty .ag-icon would draw as a solid square (FU-P3-116)
  expect(Array.from(grid.querySelectorAll(".ag-icon")).filter((el) => !el.closest(".ag-hidden"))).toEqual([]);
});

test("an image is an <img> of the raw route with as=image; a failure is one state with Retry and Download", async () => {
  files("plots/a?b#c%2F.png", 2000);
  open("plots/a?b#c%2F.png");
  const img = await screen.findByRole("img", { name: "a?b#c%2F.png" });
  expect(img.getAttribute("src")).toBe(`${RUN}/results/raw/plots/a%3Fb%23c%252F.png?as=image`);
  expect(screen.getByRole("button", { name: "Actual size" })).toHaveAttribute("aria-pressed", "false");
  fireEvent.error(img);
  expect(await screen.findByText("This image could not be shown here. Download it to open it.")).toBeInTheDocument();
  expect(screen.queryByRole("img", { name: "a?b#c%2F.png" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("img", { name: "a?b#c%2F.png" })).toBeInTheDocument();
});

test("an image over its cap is never put in an <img>", async () => {
  files("plot.svg", 5 * 1024 * KIB + 1);
  open("plot.svg");
  expect(await screen.findByText("This image could not be shown here. Download it to open it.")).toBeInTheDocument();
  expect(screen.queryByRole("img", { name: "plot.svg" })).toBeNull();
  expect(screen.getAllByRole("link", { name: "Download plot.svg" }).length).toBeGreaterThan(0);
});

test("a PDF and a known binary are not opened; a text read answered 415 is binary", async () => {
  files("doc.pdf", 10);
  open("doc.pdf");
  expect(await screen.findByText("Spectio does not open PDF files. Download it to open it.")).toBeInTheDocument();
});

test("a known-binary name is not read", async () => {
  const mock = files("S01.bam", 10);
  open("S01.bam");
  expect(await screen.findByText("This file is not text. Download it to open it.")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.includes("/text/"))).toBe(false);
});

test("a File whose text read is 415 is shown as binary", async () => {
  files("quant.sf", 10, { [`${RUN}/results/text/quant.sf`]: () => json(415, { title: "Binary file", detail: "not text" }) });
  open("quant.sf");
  expect(await screen.findByText("This file is not text. Download it to open it.")).toBeInTheDocument();
});

test("an empty file says so", async () => {
  files("empty.err", 0, { [`${RUN}/results/text/empty.err`]: () => text("") });
  open("empty.err");
  expect(await screen.findByText("This file is empty.")).toBeInTheDocument();
});

test.each([
  [404, "This file is not there now", true],
  [409, "The run's directory is not reachable", true],
  [422, "Not a file of this run's results.", false],
  [503, "Spectio cannot read the cluster's files right now", true],
  [500, "The file could not be read", true],
])("a stat answered %i says '%s'", async (status, words, retry) => {
  serve({
    [`${RUN}/results/stat/x.txt`]: () => json(status, { title: "No", detail: "/g/demo-lab is not reachable from login1" }),
    [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  open("x.txt");
  expect(await screen.findByText(words)).toBeInTheDocument();
  expect(!!screen.queryByRole("button", { name: "Retry" })).toBe(retry);
  if (status === 409 || status === 500) expect(screen.getByText(/is not reachable from login1/)).toBeInTheDocument();
});

test("Retry asks again", async () => {
  let calls = 0;
  serve({
    [`${RUN}/results/stat/x.txt`]: () => (++calls === 1 ? json(503, { title: "Offline" }) : json(200, stat("x.txt", 3))),
    [`${RUN}/results/text/x.txt`]: () => text("ok\n"),
    [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  open("x.txt");
  fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
  expect(await screen.findByText("Whole file · 3 B")).toBeInTheDocument();
});

test("a path the client refuses is never asked for nor shown", async () => {
  const mock = serve({ [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT } });
  open("../secret.txt");
  expect(await screen.findByText("Not a file of this run's results.")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.includes("/results/"))).toBe(false);
  expect(screen.queryByText(/secret/)).toBeNull();
});

test("while the run is not ended, the facts say when the file was read, with Reload", async () => {
  let reads = 0;
  files("live.log", 4, { [`${RUN}/results/text/live.log`]: () => text(`v${++reads}\n`) }, { ...run({ state: "running" }), results_dir: ROOT });
  open("live.log");
  expect(await screen.findByText(/read at \d\d:\d\d/)).toBeInTheDocument();
  expect(screen.getByText("The view does not follow the file on its own: Reload reads it again.")).toBeInTheDocument();
  await screen.findByText("v1");
  await userEvent.click(screen.getByRole("button", { name: "Reload" }));
  expect(await screen.findByText("v2")).toBeInTheDocument();
});

test("a folder's stat opens the folder page", async () => {
  serve({
    [`${RUN}/results/stat/fastqc`]: stat("fastqc", null, "dir"),
    [`${RUN}/results`]: { root: ROOT, path: "fastqc", exists: true, entries: [], truncated: false, reports: [] },
    [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  const router = open("fastqc");
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${ID}/results`));
  expect(router.state.location.search).toEqual({ path: "fastqc" });
});

test("an *.ome.zarr folder stays on the preview page, which holds the viewer's place", async () => {
  serve({
    [`${RUN}/results/stat/cells.ome.zarr`]: stat("cells.ome.zarr", null, "dir"),
    [`${RUN}/results`]: { root: ROOT, path: "cells.ome.zarr", exists: true, entries: [], truncated: false, reports: [] },
    [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  const router = open("cells.ome.zarr");
  // jsdom has no WebGL 2: the viewer's WebGL-missing state, with Browse folder (a folder has no Download)
  expect(await screen.findByText("This browser cannot open the image viewer: it needs WebGL 2, which is off or missing.")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe(`/runs/${ID}/results/file`);
  await userEvent.click(screen.getByRole("link", { name: "Browse folder" }));
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${ID}/results`));
  expect(router.state.location.search).toMatchObject({ path: "cells.ome.zarr" });
});

/** A 4 x 2 TIFF of one 8-bit sample, one uncompressed strip (pixels 0, 40, ... 280 % 256). */
function tiff(compression = 1) {
  const tags: [number, number][] = [[256, 4], [257, 2], [258, 8], [259, compression], [262, 1], [273, 122], [277, 1], [278, 2], [279, 8]];
  const bytes = new Uint8Array(130);
  const view = new DataView(bytes.buffer);
  bytes.set([0x49, 0x49, 0x2a, 0, 8, 0, 0, 0]);
  view.setUint16(8, tags.length, true);
  tags.forEach(([tag, value], i) => {
    view.setUint16(10 + i * 12, tag, true);
    view.setUint16(12 + i * 12, 4, true); // LONG
    view.setUint32(14 + i * 12, 1, true);
    view.setUint32(18 + i * 12, value, true);
  });
  bytes.set(Array.from({ length: 8 }, (_, i) => (i * 40) % 256), 122);
  return bytes;
}

/** The raw route with as=tiff, answering each closed Range with 206 as the server does. */
const ranged = (bytes: Uint8Array) => (_url: URL, init?: RequestInit) => {
  const [first, last] = /bytes=(\d+)-(\d+)/.exec(rangeOf(init) ?? "")!.slice(1).map(Number);
  const body = bytes.slice(first, Math.min(last, bytes.length - 1) + 1);
  return new Response(body, { status: 206, headers: { "content-range": `bytes ${first}-${first + body.length - 1}/${bytes.length}`, "content-length": String(body.length) } });
};

function canvas() {
  const drawn: number[][] = [];
  const context = {
    createImageData: (w: number, h: number) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
    putImageData: (image: { data: Uint8ClampedArray }) => drawn.push(Array.from(image.data)),
  };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() => context) as never);
  return drawn;
}

test("a TIFF is drawn flat on a 2D canvas through the pinned client; Actual size scrolls it", async () => {
  const drawn = canvas();
  const mock = files("gel.tif", 130, { [`${RUN}/results/raw/gel.tif?as=tiff`]: ranged(tiff()) });
  open("gel.tif");
  expect(await screen.findByText("Loading the image…")).toBeInTheDocument();
  expect(await screen.findByText("4 × 2 px")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "gel.tif" }).tagName).toBe("CANVAS");
  expect(drawn[0].filter((_, i) => i % 4 === 0)).toEqual([0, 40, 80, 120, 160, 200, 240, 24]);
  expect(fetched(mock).filter((url) => url.includes("/raw/")).every((url) => url === `${RUN}/results/raw/gel.tif?as=tiff`)).toBe(true);
  await userEvent.click(screen.getByRole("button", { name: "Actual size" }));
  expect(screen.getByRole("region", { name: "gel.tif, image" })).toHaveAttribute("tabindex", "0");
  expect(drawn).toHaveLength(2); // the canvas in its scroll region is drawn again
});

test("a TIFF's states: a refused compression, a 413, a 503 with Retry, an empty file", async () => {
  canvas();
  files("lerc.tif", 130, { [`${RUN}/results/raw/lerc.tif?as=tiff`]: ranged(tiff(34887)) });
  open("lerc.tif");
  expect(await screen.findByText("Spectio cannot decode LERC compression.")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Download lerc.tif" })).toHaveLength(2);
  cleanup();

  files("big.tif", 130, { [`${RUN}/results/raw/big.tif?as=tiff`]: () => json(413, { title: "Too large", detail: "over 1 GiB" }) });
  open("big.tif");
  expect(await screen.findByText("This image is too large to show here (over 1 GiB). Download it to open it.")).toBeInTheDocument();
  cleanup();

  let busy = 2; // the client asks a 503 again once, after 1 s: two in a row are the offline state
  files("busy.tif", 130, { [`${RUN}/results/raw/busy.tif?as=tiff`]: (url: URL, init?: RequestInit) => (busy-- > 0 ? json(503, { title: "Busy" }) : ranged(tiff())(url, init)) });
  open("busy.tif");
  expect(await screen.findByText("Spectio cannot read the cluster's files right now", {}, { timeout: 3000 })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("4 × 2 px")).toBeInTheDocument();
  cleanup();

  files("empty.tif", 0);
  open("empty.tif");
  expect(await screen.findByText("This file is empty.")).toBeInTheDocument();
});

test("on a phone a TIFF too large for 2,048 px a side says so, with Copy link and Download", async () => {
  viewport(360);
  const big = tiff();
  new DataView(big.buffer).setUint32(18, 18400, true); // ImageWidth
  files("scan.tif", 130, { [`${RUN}/results/raw/scan.tif?as=tiff`]: ranged(big) });
  open("scan.tif");
  expect(await screen.findByText("This image is too large to show on a phone.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy link" })).toBeInTheDocument();
});

test("FU-P3-88a: an HTML file of the results opens in the report viewer, with its folder's sort and filter", async () => {
  files("multiqc/multiqc_report.html", 100);
  const router = app(`/runs/${ID}/results/file?path=${encodeURIComponent("multiqc/multiqc_report.html")}&sort=-size&q=multi`);
  const frame = await screen.findByTitle(/sandboxed$/);
  expect(frame.getAttribute("sandbox")).toBe("allow-scripts allow-downloads");
  expect(router.state.location.pathname).toBe(`/runs/${ID}/report`);
  expect(router.state.location.search).toEqual({ path: "multiqc/multiqc_report.html", from: "results", sort: "-size", q: "multi" });
  // the source stays reachable as text, in the preview
  const source = screen.getByRole("link", { name: "Show the source as text" });
  expect(new URL(source.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}/results/file`);
  expect(query(source)).toEqual({ path: "multiqc/multiqc_report.html", view: "text", sort: "-size", q: "multi" });
});

test("FU-P3-88a: with view=text an HTML file is shown as text", async () => {
  files("qc/a.html", 14, { [`${RUN}/results/text/qc/a.html`]: () => text("<p>hello</p>\n") });
  app(`/runs/${ID}/results/file?path=${encodeURIComponent("qc/a.html")}&view=text`);
  const viewer = await screen.findByLabelText(/a.html, whole file/, { selector: "pre" });
  await waitFor(() => expect(viewer.textContent).toContain("<p>hello</p>"));
  expect(screen.queryByTitle(/sandboxed$/)).toBeNull();
});

test("FU-P3-88a: an HTML file past the report viewer's 1 GiB cap is not opened there", async () => {
  files("big.html", 2 * 1024 * 1024 * KIB);
  open("big.html");
  expect(await screen.findByText("Too large for the report viewer (over 1 GiB). Download it to open it.")).toBeInTheDocument();
  expect(screen.queryByTitle(/sandboxed$/)).toBeNull();
});

test("an HTML file previewed from a job's Outputs links to the report viewer and keeps the way back to the sheet", async () => {
  files("multiqc/multiqc_report.html", 100);
  app(`/runs/${ID}/results/file?path=${encodeURIComponent("multiqc/multiqc_report.html")}&task=tsk_1&attempt=1`);
  const link = await screen.findByRole("link", { name: "Open it in the report viewer" });
  expect(link.getAttribute("href")).toBe(`/runs/${ID}/report?path=${encodeURIComponent("multiqc/multiqc_report.html")}`);
  await act(async () => {});
});

const query = (a: HTMLElement) => Object.fromEntries(new URL(a.getAttribute("href")!, "http://x").searchParams);

test("the back link returns to the folder with its sort and filter, and the file's row to focus (FU-P3-85d)", async () => {
  files("pipeline_info/versions.yml", 12, { [`${RUN}/results/text/pipeline_info/versions.yml`]: () => text("a: 1\n") });
  app(`/runs/${ID}/results/file?path=${encodeURIComponent("pipeline_info/versions.yml")}&sort=-size&q=ver`);
  await heading("versions.yml");
  const back = screen.getAllByRole("link", { name: "pipeline_info" })[0];
  expect(new URL(back.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}/results`);
  expect(query(back)).toEqual({ path: "pipeline_info", sort: "-size", q: "ver", focus: "versions.yml" });
  await act(async () => {});
});

test("a file at the results root goes back to the root, with the row to focus", async () => {
  files("notes.txt", 3, { [`${RUN}/results/text/notes.txt`]: () => text("a\n") });
  open("notes.txt");
  await heading("notes.txt");
  const back = screen.getAllByRole("link", { name: "results" })[0]; // the back link, then the path bar
  expect(query(back)).toEqual({ focus: "notes.txt" });
  await act(async () => {});
});

test("opened from the task sheet's Outputs, the back link reopens the sheet on that attempt", async () => {
  files("counts/S19.tsv", 3, { [`${RUN}/results/text/counts/S19.tsv`]: () => text("a\tb\n") }, {
    workflow: { engine: "snakemake", engine_version: "9.5.1", location: "/g/x", name: null, version: null },
  });
  app(`/runs/${ID}/results/file?path=${encodeURIComponent("counts/S19.tsv")}&task=tsk_19&attempt=2`);
  await heading("S19.tsv");
  const back = screen.getByRole("link", { name: /rnaseq-2026-10-25 · job, attempt 2/ });
  expect(new URL(back.getAttribute("href")!, "http://x").pathname).toBe(`/runs/${ID}`);
  expect(query(back)).toEqual({ task: "tsk_19", attempt: "2" });
  await act(async () => {});
});

test("a folder opened from the task sheet's Outputs keeps the way back to the sheet", async () => {
  serve({
    [`${RUN}/results/stat/counts`]: stat("counts", null, "dir"),
    [`${RUN}/results`]: { root: ROOT, path: "counts", exists: true, entries: [], truncated: false, reports: [] },
    [RUN]: { ...DETAIL, ...run({ state: "succeeded" }), results_dir: ROOT },
  });
  const router = app(`/runs/${ID}/results/file?path=counts&task=tsk_19&attempt=2`);
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${ID}/results`));
  expect(router.state.location.search).toEqual({ path: "counts", task: "tsk_19", attempt: 2 });
});

test("WebGL 2 is probed once per page, and the probe's context is lost at once", async () => {
  vi.resetModules();
  const lose = vi.fn();
  const probe = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() => ({ getExtension: (n: string) => (n === "WEBGL_lose_context" ? { loseContext: lose } : null) })) as never);
  const { hasWebgl2 } = await import("./FilePreview");
  expect(hasWebgl2()).toBe(true);
  expect(hasWebgl2()).toBe(true);
  expect(probe).toHaveBeenCalledOnce();
  expect(lose).toHaveBeenCalledOnce();
});
