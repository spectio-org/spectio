import { afterEach, expect, test, vi } from "vitest";
import { READ_ONLY, type Recorded, QuietEventSource, answer, install, shiftTimes } from "./stub";

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
