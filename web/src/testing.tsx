// Test helpers of the run screens: the app's router on a memory history, a fetch answered by
// path, and an EventSource the test drives.
import { MantineProvider } from "@mantine/core";
import { RouterProvider, createMemoryHistory } from "@tanstack/react-router";
import { act, render } from "@testing-library/react";
import { vi } from "vitest";
import { resetLive } from "./live";
import { createAppRouter } from "./routes";
import { providerProps } from "./shell/theme";

export const VERSION = {
  version: "0.0.1",
  node: "login1",
  runs_root: "/scratch/amartin/spectio-runs",
  account: "amartin",
  executor: "local",
};

export function json(status: number, body: unknown): Response {
  const type = status >= 400 ? "application/problem+json" : "application/json";
  return new Response(JSON.stringify(body), { status, headers: { "content-type": type } });
}

type Answer = unknown | ((url: URL, init?: RequestInit) => Response | Promise<Response>);

/** `fetch` answered by the first key that the request's path and query start with; 404
 * otherwise. Returns the mock, whose calls hold each URL. */
export function serve(answers: Record<string, Answer>) {
  const all: Record<string, Answer> = { "/api/v1/version": VERSION, ...answers };
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://127.0.0.1");
    const key = Object.keys(all)
      .filter((k) => (url.pathname + url.search).startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    if (key === undefined) return json(404, { title: "Not found", detail: "no such path" });
    const answer = all[key];
    return typeof answer === "function" ? answer(url, init) : json(200, answer);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

/** The URLs fetched so far, as path and query. */
export const fetched = (mock: ReturnType<typeof serve>) =>
  mock.mock.calls.map(([input]) => {
    const url = new URL(String(input), "http://127.0.0.1");
    return decodeURIComponent(url.pathname + url.search);
  });

export class FakeEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  static last: FakeEventSource | null = null;
  readyState = FakeEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private handlers = new Map<string, (event: MessageEvent) => void>();
  constructor(readonly url: string) {
    FakeEventSource.last = this;
  }
  addEventListener(type: string, handler: (event: MessageEvent) => void) {
    this.handlers.set(type, handler);
  }
  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
  open() {
    act(() => {
      this.readyState = FakeEventSource.OPEN;
      this.onopen?.();
    });
  }
  frame(data: unknown) {
    act(() => this.handlers.get("spectio.run.delta")?.(new MessageEvent("x", { data: JSON.stringify(data) })));
  }
  fail() {
    act(() => {
      this.readyState = FakeEventSource.CONNECTING;
      this.onerror?.();
    });
  }
}

export function stubStream() {
  resetLive();
  FakeEventSource.last = null;
  vi.stubGlobal("EventSource", FakeEventSource);
}

/** jsdom applies no CSS: the shell picks its layout with matchMedia, answered here for one width
 * (390: the phone, 1024: the tablet). test-setup.ts puts the plain answer back after each test. */
export function viewport(width: number) {
  window.matchMedia = (query: string) => {
    const max = /max-width:\s*([\d.]+)px/.exec(query);
    const min = /min-width:\s*([\d.]+)px/.exec(query);
    const matches =
      (!!max || !!min) && (!max || width <= Number(max[1])) && (!min || width >= Number(min[1]));
    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList;
  };
}

/** The app at `path`, in its shell, at a desktop width unless `viewport` said otherwise. */
export function app(path: string) {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  render(
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>,
  );
  return router;
}

/** A task's resources before anything is known (schema `Resources`). */
export const NO_RESOURCES = { cpus: null, memory_bytes: null, time_s: null, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };

/** A run as `GET /runs` returns it. */
export function run(over: Record<string, unknown> = {}) {
  return {
    id: "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W",
    name: "rnaseq-a",
    state: "running",
    origin: "ui",
    created_at: "2026-10-31T07:40:00+00:00",
    started_at: "2026-10-31T07:40:05+00:00",
    ended_at: null,
    workflow: {
      engine: "nextflow",
      engine_version: "26.10.4",
      location: "/g/demo-lab/pipelines/rnaseq",
      name: "nf-core/rnaseq",
      version: "3.27.0",
    },
    profiles: ["test"],
    failure: null,
    head: { session: "spectio-run_01JBC6Q4ZK7M8N2P3R5S7T9V1W", node: "login1", alive: true, exit_code: null },
    task_counts: { succeeded: 24, running: 3, pending: 5 },
    summary: { tasks: { done: 24, total: 32, failed: 0, cached: 0 }, last_failure: null, stage_mode: "quarters" },
    ...over,
  };
}
