import { afterEach, expect, test, vi } from "vitest";
import { READ_ONLY, type Recorded, QuietEventSource, answer, install, shiftTimes } from "./stub";
import raw from "../../demo/fixtures.json?raw";

const page = (items: unknown[]) => JSON.stringify({ items, next: null });
const ok = (body: string, type = "application/json") => ({ status: 200, type, body });
const RUNS = [
  { id: "run_C", name: "cohort-2026-scale", state: "succeeded", created_at: "2026-10-31T11:47:00+00:00", ended_at: "2026-10-31T11:50:00+00:00" },
  { id: "run_B", name: "variant-calling-batch-3", state: "running", created_at: "2026-10-31T11:46:00+00:00", ended_at: null },
  { id: "run_A", name: "spectio/synthetic-VSQXHP", state: "failed", created_at: "2026-10-31T11:45:00+00:00", ended_at: "2026-10-31T11:45:39+00:00" },
];
const TASKS = [
  { id: "tsk_1", process: "ALIGN", state: "succeeded" },
  { id: "tsk_2", process: "MERGE", state: "failed" },
  { id: "tsk_3", process: "ALIGN", state: "succeeded" },
];
const RECORDED: Recorded = {
  "/version": ok('{"version":"0.0.1"}'),
  "/runs": ok(page(RUNS)),
  "/runs:summary?group_by=state": ok('{"groups":[]}'),
  "/runs/run_A/tasks": ok(page(TASKS)),
  "/runs/run_A/logs?source=head-out": ok("hello\n", "text/plain; charset=utf-8"),
  "/workflows:inspect?location=%2Fg%2Fdemo-lab%2Fpipelines%2Fnf-core-demo": ok('{"name":"nf-core/demo"}'),
};
const at = (url: string, method = "GET") => answer(RECORDED, method, new URL(url, "https://spectio.pages.dev/demo/"));
const ids = async (r: Response) => (await r.json()).items.map((i: { id: string }) => i.id);

test("an exact path and query answers what was recorded, with its type", async () => {
  const r = at("/api/v1/runs/run_A/logs?source=head-out");
  expect(r.status).toBe(200);
  expect(r.headers.get("content-type")).toBe("text/plain; charset=utf-8");
  expect(await r.text()).toBe("hello\n");
  // the query's encoding and order do not matter
  expect((await at("/api/v1/workflows:inspect?location=/g/demo-lab/pipelines/nf-core-demo").json()).name).toBe("nf-core/demo");
});

test("the runs list is filtered by state and by name prefix, as the server does", async () => {
  expect(await ids(at("/api/v1/runs?state=failed,running"))).toEqual(["run_B", "run_A"]);
  expect(await ids(at("/api/v1/runs?q=variant"))).toEqual(["run_B"]);
  expect(await ids(at("/api/v1/runs?q=calling"))).toEqual([]); // a prefix, not a substring
  // sort=-ended_at: ended runs only, newest end first
  expect(await ids(at("/api/v1/runs?sort=-ended_at"))).toEqual(["run_C", "run_A"]);
});

test("a list is paged by limit and the cursor it gives", async () => {
  const first = await at("/api/v1/runs/run_A/tasks?limit=2").json();
  expect(first.items.map((t: { id: string }) => t.id)).toEqual(["tsk_1", "tsk_2"]);
  expect(first.next).toEqual(expect.any(String));
  const second = await at(`/api/v1/runs/run_A/tasks?limit=2&cursor=${first.next}`).json();
  expect(second).toEqual({ items: [TASKS[2]], next: null });
  expect(await ids(at("/api/v1/runs/run_A/tasks?process=ALIGN&state=succeeded"))).toEqual(["tsk_1", "tsk_3"]);
});

test("an unknown path answers 404 in the API's problem shape", async () => {
  const r = at("/api/v1/runs/run_Z");
  expect(r.status).toBe(404);
  expect(r.headers.get("content-type")).toBe("application/problem+json");
  expect(await r.json()).toMatchObject({ type: "/problems/not-found", title: "Not found", status: 404 });
});

test("an unrecorded pipeline answers 422 on its location, naming the recorded ones", async () => {
  const r = at("/api/v1/workflows:inspect?location=/elsewhere");
  expect(r.status).toBe(422);
  const body = await r.json();
  expect(body.errors[0].field).toBe("location");
  expect(body.errors[0].message).toContain("/g/demo-lab/pipelines/nf-core-demo");
});

test.each(["POST", "PUT", "PATCH", "DELETE"])("%s is refused with 403 and the read-only reason", async (method) => {
  const r = at("/api/v1/runs", method);
  expect(r.status).toBe(403);
  expect(await r.json()).toMatchObject({ status: 403, detail: READ_ONLY });
  expect(READ_ONLY).toBe("Read-only demo: launching and cancelling are disabled");
});

test("times are shifted so the newest run ended an hour before now; logs keep theirs", async () => {
  const now = new Date("2027-01-15T09:00:00Z");
  const shifted = shiftTimes(RECORDED, now);
  const runs = JSON.parse(shifted["/runs"].body).items;
  expect(runs[0].ended_at).toBe("2027-01-15T08:00:00.000Z");
  expect(runs[2].created_at).toBe("2027-01-15T07:55:00.000Z"); // 5 min before the newest end
  expect(runs[1].ended_at).toBeNull();
  expect(shifted["/runs/run_A/logs?source=head-out"]).toBe(RECORDED["/runs/run_A/logs?source=head-out"]);
});

const installed: (() => void)[] = [];
afterEach(() => installed.splice(0).forEach((undo) => undo()));

test("install answers every fetch from the recording and never calls the real fetch", async () => {
  const real = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", real);
  installed.push(install(RECORDED), () => vi.unstubAllGlobals());
  expect((await (await fetch("/api/v1/version")).json()).version).toBe("0.0.1");
  expect((await fetch(new Request("https://elsewhere.example/api/v1/version"))).status).toBe(404);
  expect((await fetch("/assets/x.js")).status).toBe(404);
  expect(real).not.toHaveBeenCalled();
});

test("the events stream opens once and stays quiet", async () => {
  vi.useFakeTimers();
  try {
    const es = new QuietEventSource("/api/v1/events/stream");
    const onopen = vi.fn();
    const onerror = vi.fn();
    Object.assign(es, { onopen, onerror });
    expect(es.readyState).toBe(QuietEventSource.CONNECTING);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(es.readyState).toBe(QuietEventSource.OPEN);
    expect(onopen).toHaveBeenCalledTimes(1);
    expect(onerror).not.toHaveBeenCalled();
    es.close();
    expect(es.readyState).toBe(QuietEventSource.CLOSED);
  } finally {
    vi.useRealTimers();
  }
});

test("a list asked with no query answers the server's first page of 50, not the whole recording", async () => {
  const many = Array.from({ length: 60 }, (_, i) => ({ id: `tsk_${String(i).padStart(2, "0")}`, process: "P", state: "succeeded" }));
  const body = await answer({ "/runs/run_A/tasks": ok(page(many)) }, "GET", new URL("https://x/api/v1/runs/run_A/tasks")).json();
  expect(body.items).toHaveLength(50);
  expect(body.next).toBe("50");
});

// What UI parity D asks the API (P3-demo refresh): each request shape the screens send, answered
// from the recorded lists as the server would (api/runs_read.py).

test("a process's tasks, 50 a page with the cursor it gives (the process sheet's Load more)", async () => {
  const many = Array.from({ length: 120 }, (_, i) => ({ id: `tsk_${String(i).padStart(3, "0")}`, process: i % 2 ? "ALIGN" : "QC", state: "succeeded" }));
  const recorded = { "/runs/run_A/tasks": ok(page(many)) };
  const get = (q: string) => answer(recorded, "GET", new URL(`https://x/api/v1/runs/run_A/tasks?${q}`)).json();
  const first = await get("process=ALIGN&limit=50");
  expect(first.items).toHaveLength(50);
  expect(first.items.every((t: { process: string }) => t.process === "ALIGN")).toBe(true);
  const second = await get(`process=ALIGN&limit=50&cursor=${first.next}`);
  expect(second.items).toHaveLength(10);
  expect(second.next).toBeNull();
  expect(second.items[0].id).toBe("tsk_101"); // the 51st ALIGN task, after the first page's last
  expect((await get("process=NONE&limit=50")).items).toEqual([]);
});

test("the failed tasks, as Why it failed looks up the first to fail, and the Tasks tab's state chips", async () => {
  expect(await ids(at("/api/v1/runs/run_A/tasks?state=failed&limit=50"))).toEqual(["tsk_2"]);
  expect(await ids(at("/api/v1/runs/run_A/tasks?state=failed,succeeded&process=MERGE&limit=50"))).toEqual(["tsk_2"]);
});

test("the recent runs Try a test pipeline reads: GET /runs?limit=50", async () => {
  const body = await at("/api/v1/runs?limit=50").json();
  expect(body.items.map((r: { id: string }) => r.id)).toEqual(["run_C", "run_B", "run_A"]);
  expect(body.next).toBeNull();
});

// The same requests against the committed recording (web/demo/fixtures.json).
const FIXTURES = JSON.parse(raw) as Recorded;
const get = (path: string) => answer(FIXTURES, "GET", new URL(`https://spectio.pages.dev/api/v1${path}`));

test("the recording: every process sheet of every run lists that process's tasks, page by page", async () => {
  const runs = (await get("/runs?limit=50").json()).items as { id: string }[];
  expect(runs.length).toBeGreaterThanOrEqual(6);
  for (const { id } of runs) {
    const processes = (await get(`/runs/${id}/processes`).json()).items as { process: string; counts: Record<string, number> }[];
    for (const p of processes) {
      let cursor: string | null = null;
      let seen = 0;
      do {
        const query: URLSearchParams = new URLSearchParams({ process: p.process, limit: "50", ...(cursor ? { cursor } : {}) });
        const body: { items: { process: string }[]; next: string | null } = await get(`/runs/${id}/tasks?${query}`).json();
        expect(body.items.length).toBeLessThanOrEqual(50);
        expect(body.items.every((t) => t.process === p.process)).toBe(true);
        seen += body.items.length;
        cursor = body.next;
      } while (cursor);
      expect(seen).toBe(Object.values(p.counts).reduce((a, b) => a + b, 0));
    }
  }
});

test("the recording: the failed run's first failed task is among its failed tasks", async () => {
  const run = await get("/runs/run_01M68WEQRQPTPJ70JFS8VSQXHP").json();
  const failed = await get("/runs/run_01M68WEQRQPTPJ70JFS8VSQXHP/tasks?state=failed&limit=50").json();
  expect(failed.items.map((t: { id: string }) => t.id)).toContain(run.failure.task_id);
});

test("the recording: a run launched with non-default parameters shows them", async () => {
  const runs = (await get("/runs?limit=50").json()).items as { id: string }[];
  const params = await Promise.all(runs.map(async ({ id }) => (await get(`/runs/${id}`).json()).params as Record<string, unknown>));
  expect(params.some((p) => p.fail_mode === "flaky" && p.chunks === 6)).toBe(true);
});

test.each(["synthetic", "synthetic-smk", "nf-core-demo"])(
  "the recording: /launch?location= loads %s, with the four parameter groups",
  async (name) => {
    const r = get(`/workflows:inspect?${new URLSearchParams({ location: `/g/demo-lab/pipelines/${name}` })}`);
    expect(r.status).toBe(200);
    const schema = (await r.json()).schema as { $defs?: Record<string, { title: string }> };
    expect(Object.values(schema.$defs ?? {}).map((d) => d.title)).toEqual(["Input/output options", "Scenario", "Failure injection", "Resources"]);
  },
);
