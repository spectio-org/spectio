// The preview's reads (api §5.3, FU-P3-85c): names with `?`, `#`, `%` and `%2F` in every URL, a
// Range read whose next start is the Content-Range last byte + 1, and chunks joined as text.
import { afterEach, expect, test, vi } from "vitest";
import { readResultText, resultTextUrl, resultUrl, statResult } from "../api";
import { serve } from "../testing";

afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const BASE = `/api/v1/runs/${ID}/results`;

test.each([
  ["a?b.txt", "a%3Fb.txt"],
  ["a#b.txt", "a%23b.txt"],
  ["100%.txt", "100%25.txt"],
  ["x%2Fy.png", "x%252Fy.png"],
  ["dir/sub dir/f.png", "dir/sub%20dir/f.png"],
])("a name with %s stays one path in the text, image and download URLs", (path, encoded) => {
  expect(resultTextUrl(ID, path)).toBe(`${BASE}/text/${encoded}`);
  expect(resultUrl(ID, path, { as: "image" })).toBe(`${BASE}/raw/${encoded}?as=image`);
  expect(resultUrl(ID, path, { download: true })).toBe(`${BASE}/raw/${encoded}?download=true`);
  // what the server decodes is the name, with no query and no fragment
  const url = new URL(resultUrl(ID, path, { download: true }), "http://127.0.0.1");
  expect(decodeURIComponent(url.pathname.slice(`${BASE}/raw/`.length).split("/").pop()!)).toBe(path.split("/").pop());
  expect(url.hash).toBe("");
});

test("stat asks the stat route with the encoded path", async () => {
  const mock = serve({ [`${BASE}/stat/a%3Fb.txt`]: { root: "/r", path: "a?b.txt", name: "a?b.txt", type: "file", size: 3, mtime: null } });
  const found = await statResult(ID, "a?b.txt");
  expect(found.name).toBe("a?b.txt");
  expect(String(mock.mock.calls[0][0])).toBe(`${BASE}/stat/a%3Fb.txt`);
});

test("a Range read gives the next start from Content-Range, not from the text's length", async () => {
  // "café" is 5 bytes; the server's first read ends before the 2-byte é (bytes 3 and 4)
  const ranges: string[] = [];
  serve({
    [`${BASE}/text/f.txt`]: (_url: URL, init?: RequestInit) => {
      const range = new Headers(init?.headers).get("range") ?? "";
      ranges.push(range);
      const first = range === "bytes=0-3" ? ["caf", "bytes 0-2/7"] : ["é!\n", "bytes 3-6/7"];
      return new Response(first[0], { status: 206, headers: { "content-range": first[1], "content-type": "text/plain; charset=utf-8" } });
    },
  });
  const one = await readResultText(ID, "f.txt", { from: 0, to: 3 });
  expect(one).toEqual({ text: "caf", next: 3, size: 7 });
  const two = await readResultText(ID, "f.txt", { from: one.next!, to: 6 });
  expect(ranges).toEqual(["bytes=0-3", "bytes=3-6"]);
  expect(one.text + two.text).toBe("café!\n");
});

test("a read without Range has no next start; a refusal is an ApiError with the server's text", async () => {
  serve({
    [`${BASE}/text/whole.txt`]: () => new Response("all\n", { status: 200 }),
    [`${BASE}/text/gone.txt`]: () => new Response(JSON.stringify({ title: "Conflict", detail: "/g/x is not reachable" }), { status: 409 }),
  });
  expect(await readResultText(ID, "whole.txt", {})).toEqual({ text: "all\n", next: null, size: null });
  await expect(readResultText(ID, "gone.txt", {})).rejects.toMatchObject({ status: 409, message: "/g/x is not reachable" });
});
