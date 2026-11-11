// Stages, processes and tasks open a detail (P3-parD, Thomas 2026-10-31: "steps & stages pas
// clickable, pas de détails"): a side sheet that is aria-modal and returns focus to its opener, a
// process's tasks paged with Load more, "Open in Tasks" kept in the URL, and a task detail with its
// files (TaskFiles.test.tsx, P1 Task 32).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, FakeEventSource, NO_RESOURCES, app, fetched, json, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const ALIGN = "NFCORE:RNASEQ:ALIGN";
const PROCESSES = {
  items: [
    { process: "NFCORE:RNASEQ:FASTQC", stage_id: "st1", counts: { succeeded: 12 }, retries: 0 },
    { process: ALIGN, stage_id: "st2", counts: { succeeded: 2, running: 1, failed: 1, cached: 1 }, retries: 2 },
  ],
};
const STAGES = {
  items: [
    { id: "st1", position: 1, name: "QC", source: "detected", state: "completed", task_counts: { succeeded: 12 } },
    { id: "st2", position: 2, name: "Align", source: "declared", state: "running", task_counts: { succeeded: 2, running: 1, failed: 1, cached: 1 } },
  ],
};
const task = (n: number, state = "succeeded") => ({
  id: `tsk_${n}`,
  process: ALIGN,
  tag: `S0${n}`,
  name: null, // the server keeps a name only for an untagged task (inbox #77)
  state,
  stage_id: "st2",
  attempt_n: 1,
  resources: NO_RESOURCES,
});

function detail(over: Record<string, unknown> = {}, more: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}/processes`]: PROCESSES,
    [`${URL_}/stages`]: STAGES,
    [`${URL_}/tasks?process=${encodeURIComponent(ALIGN)}&limit=50&cursor=c2`]: { items: [task(3, "failed")], next: null },
    [`${URL_}/tasks?process=${encodeURIComponent(ALIGN)}`]: { items: [task(1), task(2, "running")], next: "c2" },
    [`${URL_}/tasks`]: { items: [task(1), task(2, "running")], next: null },
    [`${URL_}/logs`]: () => new Response(""),
    [URL_]: { ...DETAIL, ...run(over), params: {} },
    "/api/v1/tasks/": { task_id: "tsk_1", attempt: 1, work_dir: null, native_id: null, files: [] },
    ...more,
  });
}

/** The Align stage's table (open: the stage runs). */
const alignTable = async () => screen.findByRole("table", { name: "Processes of Align" });

test("a process row is a button that opens its detail in a modal sheet; Close returns focus to it", async () => {
  detail();
  app(`/runs/${ID}`);
  const open = within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` });
  await userEvent.click(open);
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(within(sheet).getByText(ALIGN)).toBeInTheDocument();
  const facts = within(sheet).getByRole("list", { name: "Tasks of ALIGN by state" });
  expect(within(facts).getByText("3 of 5 done")).toBeInTheDocument();
  expect(within(facts).getByText("1 running")).toBeInTheDocument();
  expect(within(facts).getByText("0 pending")).toBeInTheDocument();
  expect(within(facts).getByText("1 failed")).toBeInTheDocument();
  expect(within(facts).getByText("1 cached")).toBeInTheDocument();
  expect(within(facts).getByText("2 retried")).toBeInTheDocument();
  expect(within(sheet).getByText("Stage 2 · Align")).toBeInTheDocument();
  await userEvent.click(within(sheet).getByRole("button", { name: "Close" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(open).toHaveFocus());
});

test("Escape closes the sheet and returns focus to the opener", async () => {
  detail();
  app(`/runs/${ID}`);
  const open = within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` });
  await userEvent.click(open);
  await screen.findByRole("dialog", { name: "ALIGN" });
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(open).toHaveFocus());
});

test("the process's tasks are paged: one task and one state column under a header, then Load more", async () => {
  const mock = detail();
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  const list = await within(sheet).findByRole("list", { name: "Tasks of ALIGN" });
  // FU-P3-80: a visible header names the columns, and every row has the same two cells.
  const head = sheet.querySelector(".sp-task-head")!;
  expect(head).toBeVisible();
  expect([...head.children].map((c) => c.textContent)).toEqual(["Task", "State"]);
  const first = within(list).getByRole("button", { name: "Open task ALIGN (S01), Succeeded" });
  expect([...first.children].map((c) => c.textContent)).toEqual(["ALIGN (S01)", "Succeeded"]);
  expect(first.textContent!.match(/S01/g)).toHaveLength(1); // the tag once, not again as a chip
  expect(within(list).getByRole("button", { name: "Open task ALIGN (S02), Running" })).toHaveTextContent("Running");
  expect(fetched(mock)).toContain(`${URL_}/tasks?process=${ALIGN}&limit=50`);
  await userEvent.click(within(sheet).getByRole("button", { name: "Load more tasks" }));
  expect(await within(list).findByRole("button", { name: "Open task ALIGN (S03), Failed" })).toHaveTextContent("Failed");
  expect(within(sheet).queryByRole("button", { name: "Load more tasks" })).toBeNull();
});

test("FU-P3-80: a frame for this run reads the process's tasks again, keeping Load more's rows; none once it has ended", async () => {
  let s02 = "running";
  let state = "running";
  const first = `${URL_}/tasks?process=${encodeURIComponent(ALIGN)}`;
  const mock = detail({}, {
    [first]: () => json(200, { items: [task(1), task(2, s02)], next: "c2" }),
    [URL_]: () => json(200, { ...DETAIL, ...run({ state }), params: {} }),
  });
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  const list = await within(sheet).findByRole("list", { name: "Tasks of ALIGN" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Load more tasks" }));
  await within(list).findByRole("button", { name: "Open task ALIGN (S03), Failed" });
  s02 = "succeeded";
  FakeEventSource.last!.frame({ run_id: ID });
  expect(await within(list).findByRole("button", { name: "Open task ALIGN (S02), Succeeded" }, { timeout: 3000 })).toBeInTheDocument();
  expect(within(list).getByRole("button", { name: "Open task ALIGN (S03), Failed" })).toBeInTheDocument();
  expect(within(list).getAllByRole("button")).toHaveLength(3);
  const count = () => fetched(mock).filter((u) => u === `${URL_}/tasks?process=${ALIGN}&limit=50`).length;
  const runs = () => fetched(mock).filter((u) => u === URL_).length;
  const read = runs();
  state = "succeeded";
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(runs()).toBeGreaterThan(read), { timeout: 3000 });
  await new Promise((r) => setTimeout(r, 1300)); // the same frame's own reads land
  const before = count();
  FakeEventSource.last!.frame({ run_id: ID });
  await new Promise((r) => setTimeout(r, 1200));
  expect(count()).toBe(before);
});

test("CR-P3FU80-02: a failed re-read shows the alert above the rows, keeps them and the focus, and a later frame clears it", async () => {
  let fail = false;
  const first = `${URL_}/tasks?process=${encodeURIComponent(ALIGN)}`;
  detail({}, {
    [first]: () => (fail ? json(500, { detail: "boom" }) : json(200, { items: [task(1), task(2, "running")], next: "c2" })),
  });
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  const list = await within(sheet).findByRole("list", { name: "Tasks of ALIGN" });
  const row = within(list).getByRole("button", { name: "Open task ALIGN (S01), Succeeded" });
  row.focus();
  fail = true;
  FakeEventSource.last!.frame({ run_id: ID });
  expect(await within(sheet).findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("The tasks could not be read");
  expect(row).toBeInTheDocument();
  expect(row).toHaveFocus();
  expect(within(list).getAllByRole("button")).toHaveLength(2);
  fail = false;
  FakeEventSource.last!.frame({ run_id: ID });
  await waitFor(() => expect(within(sheet).queryByRole("alert")).toBeNull(), { timeout: 3000 });
  expect(row).toHaveFocus();
});

test("Load more ignores a second click while its page is in flight (CR-P3PARD-06)", async () => {
  let release!: () => void;
  const held = new Promise<void>((r) => (release = r));
  const mock = detail({}, {
    [`${URL_}/tasks?process=${encodeURIComponent(ALIGN)}&limit=50&cursor=c2`]: async () => {
      await held;
      return json(200, { items: [task(3, "failed")], next: null });
    },
  });
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  const list = await within(sheet).findByRole("list", { name: "Tasks of ALIGN" });
  const more = within(sheet).getByRole("button", { name: "Load more tasks" });
  await userEvent.click(more);
  await waitFor(() => expect(more).toHaveAttribute("aria-busy", "true"));
  await userEvent.click(more);
  release();
  expect(await within(list).findByRole("button", { name: "Open task ALIGN (S03), Failed" })).toBeInTheDocument();
  expect(within(list).getAllByRole("button", { name: "Open task ALIGN (S03), Failed" })).toHaveLength(1);
  expect(fetched(mock).filter((u) => u.includes("cursor=c2"))).toHaveLength(1);
});

test("Open in Tasks goes to the Tasks tab filtered on the process, kept in the URL", async () => {
  const mock = detail();
  const router = app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Open ALIGN in Tasks" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(router.state.location.search).toEqual({ tab: "tasks", process: ALIGN });
  expect(((await screen.findByRole("textbox", { name: "Process" })) as HTMLInputElement).value).toMatch(/^ALIGN \(/);
  await waitFor(() => expect(screen.getByRole("tabpanel", { name: "Tasks" })).toHaveFocus());
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?process=${ALIGN}&limit=50`));
});

test("the URL ?tab=tasks&process= opens the Tasks tab on that process; changing it keeps the URL", async () => {
  detail();
  const router = app(`/runs/${ID}?tab=tasks&process=${encodeURIComponent(ALIGN)}`);
  const select = await screen.findByRole("textbox", { name: "Process" });
  expect((select as HTMLInputElement).value).toMatch(/^ALIGN \(/);
  Element.prototype.scrollIntoView = () => {}; // jsdom has none; the Select scrolls to its option
  await userEvent.click(select);
  await userEvent.click(await screen.findByRole("option", { name: /^All processes/ }));
  Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  await waitFor(() => expect(router.state.location.search).toEqual({ tab: "tasks" }));
});

test("a task row in the sheet opens the task detail: its facts and its files, no note about Tasks 28 and 29", async () => {
  detail();
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  await userEvent.click(await within(sheet).findByRole("button", { name: "Open task ALIGN (S02), Running" }));
  const taskSheet = await screen.findByRole("dialog", { name: "ALIGN (S02)" });
  const facts = within(taskSheet).getByRole("region", { name: "ALIGN (S02)" });
  expect(facts).toHaveFocus();
  expect(within(taskSheet).getByText("tsk_2")).toBeInTheDocument();
  expect(within(taskSheet).getByText("S02")).toBeInTheDocument();
  // UI-12: the sticky head holds the title, the state (icon and word) and Close; the facts do not repeat it
  const head = within(taskSheet).getByRole("heading", { level: 2, name: "ALIGN (S02)" }).closest(".sp-sheet-head") as HTMLElement;
  expect(within(head).getByText("Running")).toBeInTheDocument();
  expect(within(head).getByRole("button", { name: "Close" })).toBeInTheDocument();
  expect(within(taskSheet).getAllByText("Running")).toHaveLength(1);
  expect(within(taskSheet).queryByText("State", { selector: "dt" })).toBeNull();
  expect(within(taskSheet).getByText("Stage 2 · Align")).toBeInTheDocument();
  expect(within(taskSheet).getByRole("heading", { name: "Files" })).toBeInTheDocument();
  expect(await within(taskSheet).findByText("This attempt has no file to show.")).toBeInTheDocument();
  expect(within(taskSheet).queryByRole("note")).toBeNull();
  await userEvent.click(within(taskSheet).getByRole("button", { name: "Back to ALIGN" }));
  expect(await screen.findByRole("dialog", { name: "ALIGN" })).toBeInTheDocument();
});

test("a stage opens its detail, whose processes open theirs", async () => {
  detail();
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Open stage Align" }));
  const sheet = await screen.findByRole("dialog", { name: "Align" });
  expect(within(sheet).getByText("Declared")).toBeInTheDocument();
  const facts = within(sheet).getByRole("list", { name: "Tasks of Align by state" });
  expect(within(facts).getByText("2 retried")).toBeInTheDocument();
  await userEvent.click(within(sheet).getByRole("button", { name: `Open process ${ALIGN}` }));
  expect(await screen.findByRole("dialog", { name: "ALIGN" })).toBeInTheDocument();
});

test("a task row in the Tasks tab opens the task detail; Snakemake words", async () => {
  detail({ workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/p/smk", name: "smk", version: null } });
  app(`/runs/${ID}?tab=tasks`);
  const table = await screen.findByRole("table", { name: "Jobs" });
  const open = await within(table).findByRole("button", { name: "Open job ALIGN (S01)" });
  await userEvent.click(open);
  const sheet = await screen.findByRole("dialog", { name: "ALIGN (S01)" });
  expect(await within(sheet).findByText("Snakemake keeps no job script; the rule's command is in the Snakefile.")).toBeInTheDocument();
  expect(within(sheet).queryByRole("note")).toBeNull();
  await userEvent.click(within(sheet).getByRole("button", { name: `Open rule ${ALIGN}` }));
  expect(await screen.findByRole("dialog", { name: "ALIGN" })).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(open).toHaveFocus());
});

test("on the phone, a process card opens a bottom sheet that traps focus and returns it", async () => {
  viewport(390);
  detail();
  app(`/runs/${ID}`);
  const cards = await screen.findByRole("list", { name: "Processes of Align" });
  await userEvent.click(within(cards).getByRole("button", { name: `Open process ${ALIGN}` }));
  const open = within(cards).getByRole("button", { name: `Open process ${ALIGN}` });
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(sheet).toHaveClass("sp-sheet-bottom");
  expect(sheet).toContainElement(document.activeElement as HTMLElement);
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(open).toHaveFocus());
});
