// Stages, processes and tasks open a detail (P3-parD, Thomas 2026-10-31: "steps & stages pas
// clickable, pas de détails"): a side sheet that is aria-modal and returns focus to its opener, a
// process's tasks paged with Load more, "Open in Tasks" kept in the URL, and a task detail that says
// what 0.0.1 does not serve yet.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, fetched, json, run, serve, stubStream, viewport } from "../testing";

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
  name: `ALIGN (S0${n})`,
  state,
  stage_id: "st2",
});

function detail(over: Record<string, unknown> = {}, more: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}/processes`]: PROCESSES,
    [`${URL_}/stages`]: STAGES,
    [`${URL_}/tasks?process=${encodeURIComponent(ALIGN)}&limit=50&cursor=c2`]: { items: [task(3, "failed")], next: null },
    [`${URL_}/tasks?process=${encodeURIComponent(ALIGN)}`]: { items: [task(1), task(2, "running")], next: "c2" },
    [`${URL_}/tasks`]: { items: [task(1), task(2, "running")], next: null },
    [`${URL_}/logs`]: () => new Response(""),
    [URL_]: { ...run(over), params: {} },
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

test("the process's tasks are paged: name, tag and state, then Load more", async () => {
  const mock = detail();
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  const list = await within(sheet).findByRole("list", { name: "Tasks of ALIGN" });
  const first = within(list).getByRole("button", { name: "Open task ALIGN (S01)" });
  expect(within(first).getByText("S01")).toBeInTheDocument();
  expect(within(first).getByText("Succeeded")).toBeInTheDocument();
  expect(within(list).getByRole("button", { name: "Open task ALIGN (S02)" })).toHaveTextContent("Running");
  expect(fetched(mock)).toContain(`${URL_}/tasks?process=${ALIGN}&limit=50`);
  await userEvent.click(within(sheet).getByRole("button", { name: "Load more tasks" }));
  expect(await within(list).findByRole("button", { name: "Open task ALIGN (S03)" })).toHaveTextContent("Failed");
  expect(within(sheet).queryByRole("button", { name: "Load more tasks" })).toBeNull();
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
  expect(await within(list).findByRole("button", { name: "Open task ALIGN (S03)" })).toBeInTheDocument();
  expect(within(list).getAllByRole("button", { name: "Open task ALIGN (S03)" })).toHaveLength(1);
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
  expect(await screen.findByRole("combobox", { name: /Process/ })).toHaveValue(ALIGN);
  await waitFor(() => expect(screen.getByRole("tabpanel", { name: "Tasks" })).toHaveFocus());
  await waitFor(() => expect(fetched(mock)).toContain(`${URL_}/tasks?process=${ALIGN}&limit=50`));
});

test("the URL ?tab=tasks&process= opens the Tasks tab on that process; changing it keeps the URL", async () => {
  detail();
  const router = app(`/runs/${ID}?tab=tasks&process=${encodeURIComponent(ALIGN)}`);
  const select = await screen.findByRole("combobox", { name: /Process/ });
  expect(select).toHaveValue(ALIGN);
  await userEvent.selectOptions(select, "");
  await waitFor(() => expect(router.state.location.search).toEqual({ tab: "tasks" }));
});

test("a task row in the sheet opens the task detail: what 0.0.1 knows, and an honest note", async () => {
  detail();
  app(`/runs/${ID}`);
  await userEvent.click(within(await alignTable()).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  await userEvent.click(await within(sheet).findByRole("button", { name: "Open task ALIGN (S02)" }));
  const taskSheet = await screen.findByRole("dialog", { name: "ALIGN (S02)" });
  const facts = within(taskSheet).getByRole("region", { name: "ALIGN (S02)" });
  expect(facts).toHaveFocus();
  expect(within(taskSheet).getByText("tsk_2")).toBeInTheDocument();
  expect(within(taskSheet).getByText("S02")).toBeInTheDocument();
  expect(within(taskSheet).getByText("Running")).toBeInTheDocument();
  expect(within(taskSheet).getByText("Stage 2 · Align")).toBeInTheDocument();
  expect(within(taskSheet).getByRole("note")).toHaveTextContent(
    "Not in Spectio 0.0.1 yet: this task's files (.command.log, .command.err, .command.out, .command.sh), its work directory, exit code, duration and resources. They arrive with P1 Tasks 28 and 29.",
  );
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
  expect(within(sheet).getByRole("note")).toHaveTextContent(
    "Not in Spectio 0.0.1 yet: this job's log, its directory, exit code, duration and resources. They arrive with P1 Tasks 28 and 29.",
  );
  await userEvent.click(within(sheet).getByRole("button", { name: `Open rule ${ALIGN}` }));
  expect(await screen.findByRole("dialog", { name: "ALIGN" })).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(open).toHaveFocus());
});

test("on the phone, a process card opens a full-screen sheet", async () => {
  viewport(390);
  detail();
  app(`/runs/${ID}`);
  const cards = await screen.findByRole("list", { name: "Processes of Align" });
  await userEvent.click(within(cards).getByRole("button", { name: `Open process ${ALIGN}` }));
  const sheet = await screen.findByRole("dialog", { name: "ALIGN" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
});
