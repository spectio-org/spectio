// The public demo's API (demo build only, `vite --mode demo`): every fetch is answered from the
// answers recorded on a demo server (web/demo/fixtures.json, tools/media/record_demo.py), so the
// screens run as static files. Nothing reaches the network: a path that was not recorded is a
// 404, and every write is refused with a 403. Lists are recorded whole, then filtered and paged
// here as GET /runs and GET /runs/{id}/tasks do on the server (api/runs_read.py).

export interface Answer {
  status: number;
  type: string | null;
  body: string;
}
export type Recorded = Record<string, Answer>;

export const READ_ONLY = "Read-only demo: launching and cancelling are disabled";
const API = "/api/v1";
const PROBLEM = "application/problem+json";

const reply = (status: number, body: string, type: string | null) =>
  new Response(body, { status, headers: { "content-type": type ?? "application/json" } });
const problem = (status: number, slug: string, title: string, detail: string, extra = {}) =>
  reply(status, JSON.stringify({ type: `/problems/${slug}`, title, status, detail, ...extra }), PROBLEM);

/** A path and its query in one spelling: the parameters sorted and encoded the same way. */
function canonical(path: string, params: URLSearchParams): string {
  const sorted = new URLSearchParams([...params].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
  const query = sorted.toString();
  return query ? `${path}?${query}` : path;
}

type Item = Record<string, unknown>;
const LISTS: { pattern: RegExp; filter: (items: Item[], p: URLSearchParams) => Item[] }[] = [
  {
    pattern: /^\/runs$/,
    filter: (items, p) => {
      const states = p.get("state")?.split(",");
      const q = p.get("q");
      let found = items.filter((r) => (!states || states.includes(String(r.state))) && (!q || String(r.name ?? "").startsWith(q)));
      if (p.get("sort") === "-ended_at") {
        found = found.filter((r) => r.ended_at).sort((a, b) => Date.parse(String(b.ended_at)) - Date.parse(String(a.ended_at)));
      }
      return found;
    },
  },
  {
    pattern: /^\/runs\/[^/]+\/tasks$/,
    filter: (items, p) => {
      const states = p.get("state")?.split(",");
      const process = p.get("process");
      return items.filter((t) => (!states || states.includes(String(t.state))) && (process === null || t.process === process));
    },
  },
];

/** One page of a recorded list; the cursor is the offset of the next item. */
function listPage(base: Answer, filter: (items: Item[], p: URLSearchParams) => Item[], p: URLSearchParams) {
  const items = filter((JSON.parse(base.body) as { items: Item[] }).items, p);
  const limit = Math.min(200, Math.max(1, Number(p.get("limit")) || 50));
  const start = Math.max(0, Number(p.get("cursor")) || 0);
  const end = start + limit;
  return reply(200, JSON.stringify({ items: items.slice(start, end), next: end < items.length ? String(end) : null }), base.type);
}

/** The demo server's answer to one request. */
export function answer(recorded: Recorded, method: string, url: URL): Response {
  if (method.toUpperCase() !== "GET") return problem(403, "read-only-demo", "Read-only demo", READ_ONLY);
  const path = url.pathname.startsWith(API) ? url.pathname.slice(API.length) : null;
  if (path === null) return problem(404, "not-found", "Not found", "The demo answers the API only.");
  const list = LISTS.find((l) => l.pattern.test(path));
  if (list && recorded[path]) return listPage(recorded[path], list.filter, url.searchParams);
  const exact = Object.entries(recorded).find(([key]) => {
    const at = new URL(key, "http://x");
    return canonical(at.pathname, at.searchParams) === canonical(path, url.searchParams);
  });
  if (exact) return reply(exact[1].status, exact[1].body, exact[1].type);
  if (path === "/workflows:inspect") {
    const known = Object.keys(recorded)
      .filter((k) => k.startsWith("/workflows:inspect?"))
      .map((k) => new URL(k, "http://x").searchParams.get("location"));
    const message = `This demo has recorded only ${known.join(", ")}`;
    return problem(422, "validation-failed", "Validation failed", message, { errors: [{ field: "location", message }] });
  }
  return problem(404, "not-found", "Not found", "Not in the demo's recorded data.");
}

const ISO = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})/g;

/** The recording with every time in its JSON answers moved by one offset, so that the newest
 * run ended an hour before `now` ("Today 10:05" stays true whenever the demo is opened). The
 * logs keep the times they were written with. */
export function shiftTimes(recorded: Recorded, now: Date): Recorded {
  const runs = recorded["/runs"] ? (JSON.parse(recorded["/runs"].body).items as Item[]) : [];
  const times = runs.flatMap((r) => [r.created_at, r.ended_at]).filter(Boolean).map((t) => Date.parse(String(t)));
  if (times.length === 0) return recorded;
  const offset = now.getTime() - 3_600_000 - Math.max(...times);
  return Object.fromEntries(
    Object.entries(recorded).map(([key, a]) => [
      key,
      a.type?.includes("json") ? { ...a, body: a.body.replace(ISO, (t) => new Date(Date.parse(t) + offset).toISOString()) } : a,
    ]),
  );
}

/** The live stream (api §8.3) of a recording: it opens and stays quiet, since nothing changes. */
export class QuietEventSource extends EventTarget {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  readyState = QuietEventSource.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  constructor(readonly url: string) {
    super();
    setTimeout(() => {
      if (this.readyState !== QuietEventSource.CONNECTING) return;
      this.readyState = QuietEventSource.OPEN;
      this.onopen?.(new Event("open"));
    }, 0);
  }
  close() {
    this.readyState = QuietEventSource.CLOSED;
  }
}

/** Answers `fetch` and `EventSource` from the recording; returns what puts them back (tests). */
export function install(recorded: Recorded): () => void {
  const { fetch: realFetch, EventSource: realEventSource } = window;
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : null;
    const url = new URL(request ? request.url : String(input), window.location.href);
    if (url.origin !== window.location.origin) return problem(404, "not-found", "Not found", "The demo answers its own origin only.");
    return answer(recorded, init?.method ?? request?.method ?? "GET", url);
  };
  window.EventSource = QuietEventSource as unknown as typeof EventSource;
  return () => {
    window.fetch = realFetch;
    window.EventSource = realEventSource;
  };
}
