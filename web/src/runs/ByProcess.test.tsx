// The By process (By rule) view of the Tasks tab, and the efficiency columns per job (P1 Task 35;
// ui-spec §4.4 note 2026-11-07; boards LiteRunEfficiency, MLiteRunEfficiency, LiteRunTasks).
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const GIB = 1024 ** 3;
const eff = (over: Record<string, unknown>) => ({
  jobs: { done: 48, total: 48 },
  measured: 48,
  pending_accounting: 0,
  cpu_mean: 0.34,
  cpu_max: 0.41,
  mem_mean: 0.03,
  mem_max: 0.05,
  requested: { cpus: 6, mem_bytes: 36 * GIB, time_limit_s: 4 * 3600, varies: false },
  used: { peak_rss_bytes_max: 1.6 * GIB, elapsed_s_max: 180 },
  ...over,
});
const PROCESSES = {
  items: [
    // listed A to Z, STAR_ALIGN first in the pipeline (FU-P3-82)
    { process: "NFCORE:RNASEQ:FASTQC", stage_id: null, counts: { succeeded: 48 }, retries: 0, efficiency: eff({}), pipeline_order: 1 },
    { process: "NFCORE:RNASEQ:STAR_ALIGN", stage_id: null, counts: { succeeded: 20 }, retries: 0, efficiency: eff({ jobs: { done: 20, total: 20 }, measured: 20, cpu_mean: 0.81, cpu_max: 0.95, mem_mean: 0.62, mem_max: 0.71, requested: { cpus: 12, mem_bytes: 72 * GIB, time_limit_s: 8 * 3600, varies: true } }), pipeline_order: 0 },
  ],
};
const TASKS = {
  items: [
    {
      id: "tsk_1", process: "NFCORE:RNASEQ:FASTQC", tag: "S01", name: "FASTQC (S01)", state: "succeeded", stage_id: null, attempt_n: 1,
      resources: { cpus: 6, memory_bytes: 36 * GIB, time_s: 4 * 3600, realtime_s: 180, cpu_percent: 204, peak_rss_bytes: GIB, source: "trace" },
      slurm: null,
      efficiency: { cpu: 0.34, mem: 0.03, elapsed_s: 180, peak_rss_bytes: GIB, state: "available", source: "sacct", reason: null },
    },
  ],
  next: null,
};

function served() {
  return serve({
    [`${URL_}/processes`]: PROCESSES,
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/tasks`]: TASKS,
    [`${URL_}/logs`]: () => new Response(""),
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", ended_at: "2026-10-31T09:00:00+00:00" }), params: {} },
  });
}

test("By process is a tab button; its sort buttons are native buttons; each row names its process", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  const tab = await screen.findByRole("tab", { name: "By process" });
  expect(tab.tagName).toBe("BUTTON");
  expect(screen.getByRole("tab", { name: "Task list" })).toHaveAttribute("aria-selected", "true");
  await userEvent.click(tab);
  expect(tab).toHaveAttribute("aria-selected", "true");
  const table = screen.getByRole("table", { name: "Tasks by process" });
  const sorts = within(table).getAllByRole("button", { name: /^Sort by / });
  expect(sorts.length).toBeGreaterThan(5);
  for (const b of sorts) expect(b.tagName).toBe("BUTTON");
  await userEvent.click(within(table).getByRole("button", { name: "Sort by Mem eff. mean" }));
  const memMean = within(table).getByRole("columnheader", { name: /Mem eff\. mean/ });
  expect(memMean).toHaveAttribute("aria-sort", "ascending");
  let rows = within(table).getAllByRole("row").slice(1);
  expect(within(rows[0]).getByRole("button", { name: "Show the tasks of process NFCORE:RNASEQ:FASTQC" })).toBeInTheDocument();
  expect(rows[0].textContent).toContain("48 / 48");
  expect(rows[0].textContent).toContain("3 % low");
  expect(rows[1].textContent).toContain("vary");
  await userEvent.click(within(table).getByRole("button", { name: "Sort by CPU eff. mean" }));
  rows = within(table).getAllByRole("row").slice(1);
  expect(rows[0].textContent).toContain("FASTQC");
  await userEvent.click(within(table).getByRole("button", { name: "Sort by CPU eff. mean" }));
  expect(within(table).getByRole("columnheader", { name: /CPU eff\. mean/ })).toHaveAttribute("aria-sort", "descending");
  rows = within(table).getAllByRole("row").slice(1);
  expect(rows[0].textContent).toContain("STAR_ALIGN");
  expect(screen.getByText("48 tasks of FASTQC used under 25 % of their memory.")).toBeInTheDocument();
  // the row's name opens the task list filtered to it
  await userEvent.click(screen.getByRole("button", { name: "Show the tasks of process NFCORE:RNASEQ:FASTQC" }));
  expect(await screen.findByRole("tab", { name: "Task list" })).toHaveAttribute("aria-selected", "true");
  expect((screen.getByRole("textbox", { name: "Process" }) as HTMLInputElement).value).toMatch(/^FASTQC \(/);
});

test("the Tasks table has CPU eff. and Mem eff. columns with a 'low' text badge and their source", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  const table = await screen.findByRole("table", { name: "Tasks" });
  const head = within(table).getByRole("columnheader", { name: "Mem eff." });
  expect(head).toHaveAccessibleDescription("From sacct when the job has ended; before that from the engine's trace or benchmark");
  const cells = within(within(table).getAllByRole("row")[1]).getAllByRole("cell").map((c) => c.textContent);
  expect(cells.slice(9, 11)).toEqual(["34 %", "3 % low"]);
});

test("on the phone By process is one card per process, with a Sort by select", async () => {
  viewport(390);
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  expect(screen.getByRole("combobox", { name: "Sort by" })).toBeInTheDocument();
  const cards = screen.getByRole("list", { name: "Tasks by process" });
  const first = within(cards).getAllByRole("listitem")[0];
  expect(within(first).getByRole("button", { name: "Show the tasks of process NFCORE:RNASEQ:STAR_ALIGN" })).toBeInTheDocument();
  expect(within(first).getByText("Mem eff. mean · max")).toBeInTheDocument();
});

test("By process has the board's request and usage columns, each sortable (CR-P3T35-02)", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  const table = screen.getByRole("table", { name: "Tasks by process" });
  for (const name of ["CPUs asked", "Memory asked", "Time limit", "Peak memory", "Longest"])
    expect(within(table).getByRole("button", { name: `Sort by ${name}` })).toBeInTheDocument();
  const first = () => within(table).getAllByRole("row")[1].textContent;
  for (const name of ["CPUs asked", "Time limit"]) {
    await userEvent.click(within(table).getByRole("button", { name: `Sort by ${name}` }));
    await userEvent.click(within(table).getByRole("button", { name: `Sort by ${name}` }));
    expect(within(table).getByRole("columnheader", { name: new RegExp(name) })).toHaveAttribute("aria-sort", "descending");
    expect(first()).toContain("STAR_ALIGN");
  }
});

test("the Task list and By process tabs each control their tab panel (CR-P3T35-03)", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  const list = await screen.findByRole("tab", { name: "Task list" });
  let panel = screen.getByRole("tabpanel", { name: "Task list" });
  expect(list).toHaveAttribute("aria-controls", panel.id);
  expect(within(panel).getByRole("table", { name: "Tasks" })).toBeInTheDocument();
  const byProcess = screen.getByRole("tab", { name: "By process" });
  await userEvent.click(byProcess);
  panel = screen.getByRole("tabpanel", { name: "By process" });
  expect(byProcess).toHaveAttribute("aria-controls", panel.id);
  expect(within(panel).getByRole("table", { name: "Tasks by process" })).toBeInTheDocument();
});

test("'vary' is one mark per row, never on a request value (CR-P3T35-05)", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  const table = screen.getByRole("table", { name: "Tasks by process" });
  const heads = within(table).getAllByRole("columnheader").map((h) => h.textContent);
  const row = within(table).getAllByRole("row").find((r) => r.textContent?.includes("STAR_ALIGN"))!;
  const cell = (name: string) => within(row).getAllByRole("cell")[heads.indexOf(name)].textContent;
  expect(cell("CPUs asked")).toBe("12");
  expect(cell("Memory asked")).toBe("72 GB");
  expect(cell("Time limit")).toBe("8 h");
  expect(cell("Requests")).toBe("vary");
  expect(row.textContent?.match(/var/g)).toHaveLength(1);
  const other = within(table).getAllByRole("row").find((r) => r.textContent?.includes("FASTQC"))!;
  expect(other.textContent).not.toContain("var");
});

test("on the phone 'requests vary' is one fact line, not a suffix on each value (CR-P3T35-05)", async () => {
  viewport(390);
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  const cards = within(screen.getByRole("list", { name: "Tasks by process" })).getAllByRole("listitem");
  const star = cards.find((c) => c.textContent?.includes("STAR_ALIGN"))!;
  expect(within(star).getByText("CPUs · memory · time limit asked").nextSibling?.textContent).toBe("12 · 72 GB · 8 h");
  expect(within(star).getByText("Requests").nextSibling?.textContent).toBe("vary");
  const fastqc = cards.find((c) => c.textContent?.includes("FASTQC"))!;
  expect(within(fastqc).queryByText("Requests")).toBeNull();
});

const names = (rows: HTMLElement[]) => rows.map((r) => within(r).getAllByRole("button")[0].getAttribute("aria-label")?.split(":").pop());

test("By process opens in pipeline order; 'A to Z' and back are radio buttons, by keyboard too (FU-P3-82)", async () => {
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  const order = screen.getByRole("radiogroup", { name: "Order" });
  const pipeline = within(order).getByRole("radio", { name: "Pipeline order" });
  const az = within(order).getByRole("radio", { name: "A to Z" });
  expect(pipeline.tagName).toBe("INPUT");
  expect(pipeline).toBeChecked();
  const table = screen.getByRole("table", { name: "Tasks by process" });
  const body = () => within(table).getAllByRole("row").slice(1);
  expect(names(body())).toEqual(["STAR_ALIGN", "FASTQC"]);
  expect(within(table).queryAllByRole("columnheader").filter((h) => h.hasAttribute("aria-sort"))).toHaveLength(0);
  await userEvent.click(az);
  expect(az).toBeChecked();
  expect(names(body())).toEqual(["FASTQC", "STAR_ALIGN"]);
  // a column sort still works, and leaves neither order checked
  await userEvent.click(within(table).getByRole("button", { name: "Sort by CPU eff. mean" }));
  expect(names(body())).toEqual(["FASTQC", "STAR_ALIGN"]);
  await userEvent.click(within(table).getByRole("button", { name: "Sort by CPU eff. mean" }));
  expect(names(body())).toEqual(["STAR_ALIGN", "FASTQC"]);
  expect(pipeline).not.toBeChecked();
  expect(az).not.toBeChecked();
  // by keyboard: Tab reaches the group, the arrows move between the two orders
  az.focus();
  await userEvent.keyboard(" ");
  expect(names(body())).toEqual(["FASTQC", "STAR_ALIGN"]);
  await userEvent.keyboard("{ArrowUp}");
  expect(pipeline).toBeChecked();
  expect(names(body())).toEqual(["STAR_ALIGN", "FASTQC"]);
});

test("on the phone the cards open in pipeline order, with the same two orders (FU-P3-82)", async () => {
  viewport(390);
  served();
  app(`/runs/${ID}?tab=tasks`);
  await userEvent.click(await screen.findByRole("tab", { name: "By process" }));
  const cards = () => within(screen.getByRole("list", { name: "Tasks by process" })).getAllByRole("listitem");
  expect(names(cards())).toEqual(["STAR_ALIGN", "FASTQC"]);
  expect(screen.getByRole("combobox", { name: "Sort by" })).toHaveValue("pipeline:asc");
  await userEvent.click(screen.getByRole("radio", { name: "A to Z" }));
  expect(names(cards())).toEqual(["FASTQC", "STAR_ALIGN"]);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Sort by" }), "Pipeline order");
  expect(names(cards())).toEqual(["STAR_ALIGN", "FASTQC"]);
});
