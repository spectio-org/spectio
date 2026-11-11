// Resume, Copy to a new launch and the Copy menu's Command item in the shared run header (P1 Task
// 32 part two; ui-spec §4.4 run tools note; boards LiteRunActions and MLiteResumeSheet). Since
// UI-09 the header shows one primary and puts the rest in More actions (ui-spec §12.4).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, VERSION, app, json, run, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());
beforeEach(() => {
  let last = "";
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: async (text: string) => void (last = text), readText: async () => last },
  });
});
afterEach(() => {
  Reflect.deleteProperty(navigator, "clipboard");
});

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const CHILD = "run_01JBC6Q4ZK7M8N2P3R5S7T9C2D";
const URL_ = `/api/v1/runs/${ID}`;
const ENDED = { state: "failed", ended_at: "2026-10-31T08:00:00+00:00" };
const HEAD_ENDED = { session: `spectio-${ID}`, node: "login1", alive: false, exit_code: 1, checked: true };

function failedRun(over: Record<string, unknown> = {}) {
  return {
    ...DETAIL,
    ...run({ ...ENDED, name: "wgs-cohort-12", head: HEAD_ENDED }),
    summary: { tasks: { done: 143, total: 175, failed: 2, cached: 0 }, last_failure: null, stage_mode: "quarters" },
    actions: { resume: { allowed: true, reason: null } },
    command: { argv: ["nextflow", "run", "/g/p", "-params-file", "params.json"], text: "nextflow run /g/p -params-file params.json" },
    ...over,
  };
}

function detail(body: unknown, more: Record<string, unknown> = {}) {
  return serve({
    [`${URL_}/processes`]: { items: [] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/logs`]: () => new Response(""),
    [`${URL_}/results`]: { root: "/g/out", path: "", exists: false, entries: [], truncated: false, reports: [] },
    [`${URL_}:relaunch`]: () => json(500, { title: "unexpected" }),
    [URL_]: body,
    ...more,
  });
}

const header = async () => (await screen.findByRole("heading", { level: 1 })).closest("header")!;
/** Opens the header's More actions menu. */
const openMore = async () => {
  await userEvent.click(await within(await header()).findByRole("button", { name: "More actions" }));
  return screen.findByRole("menu");
};

test("Resume asks in a modal dialog, focus on Cancel first and back on Resume", async () => {
  detail(failedRun());
  app(`/runs/${ID}`);
  const resume = await within(await header()).findByRole("button", { name: "Resume" });
  await userEvent.click(resume);
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(dialog).toHaveTextContent(
    "Spectio starts a new run in the same launch directory. Nextflow runs again with -resume and reuses the 143 tasks that finished. This run stays Failed.",
  );
  // the launch directory in its own block, as on the boards
  expect(within(dialog).getByText(`${VERSION.runs_root}/${ID}/launch`).tagName).toBe("CODE");
  expect(dialog).toHaveTextContent("The head of this run has ended on login1 (checked): Spectio unlocks the directory first.");
  await waitFor(() => expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus());
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(resume).toHaveFocus());
});

test("Resume posts :relaunch with mode resume and opens the new run", async () => {
  const child = { ...failedRun({ id: CHILD, name: "wgs-cohort-12-T9C2D", state: "queued", ended_at: null, parent_run_id: ID }) };
  const posted = vi.fn((_url: URL, _init?: RequestInit) => json(201, child));
  detail(failedRun(), {
    [`${URL_}:relaunch`]: posted,
    [`/api/v1/runs/${CHILD}/processes`]: { items: [] },
    [`/api/v1/runs/${CHILD}/stages`]: { items: [] },
    [`/api/v1/runs/${CHILD}`]: child,
  });
  const router = app(`/runs/${ID}`);
  await userEvent.click(await within(await header()).findByRole("button", { name: "Resume" }));
  await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Resume" }));
  await waitFor(() => expect(posted).toHaveBeenCalledTimes(1));
  expect(posted.mock.calls[0][1]).toMatchObject({ method: "POST", body: JSON.stringify({ mode: "resume" }) });
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${CHILD}`));
  expect(await screen.findByRole("heading", { level: 1, name: "wgs-cohort-12-T9C2D" })).toBeInTheDocument();
});

test.each([
  ["launch_dir_refused", "Spectio will not resume in this run's launch directory: it, or a file in it, is not yours or is writable by others."],
  ["session_id_refused", "This run's Nextflow session ID is not one Spectio can pass to -resume."],
  ["profiles_unknown", "Spectio cannot read this run's profiles from its run directory, so it cannot resume it as it ran."],
  ["resume_in_progress", "A run of this launch directory has not ended yet."],
])("a 409 %s says why in words, in the dialog", async (reason, words) => {
  detail(failedRun(), {
    [`${URL_}:relaunch`]: () => json(409, { title: "Run state conflict", detail: "x", reason }),
  });
  app(`/runs/${ID}`);
  await userEvent.click(await within(await header()).findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog");
  await userEvent.click(within(dialog).getByRole("button", { name: "Resume" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(`Not resumed: ${words}`);
});

test.each([
  ["running", {}, "The run's head is still running. Resume when it has ended."],
  ["head_unverified", { head: { ...HEAD_ENDED, node: "login2" } }, "The head may still be running on login2, and Spectio cannot check it from login1. Resume when it has ended."],
  ["launch_dir_refused", {}, "Spectio will not resume in this run's launch directory: it, or a file in it, is not yours or is writable by others."],
  ["session_id_refused", {}, "This run's Nextflow session ID is not one Spectio can pass to -resume."],
])("a refused Resume (%s) stays visible, aria-disabled, its reason as text", async (reason, over, words) => {
  detail(failedRun({ actions: { resume: { allowed: false, reason } }, ...over }));
  app(`/runs/${ID}`);
  const resume = await within(await header()).findByRole("button", { name: "Resume" });
  expect(resume).toHaveAttribute("aria-disabled", "true");
  expect(resume).toHaveAccessibleDescription(words);
  await userEvent.click(resume);
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("a resume in progress links to the child that runs", async () => {
  detail(
    failedRun({
      actions: { resume: { allowed: false, reason: "resume_in_progress" } },
      resumed_as: [{ id: CHILD, name: "wgs-cohort-12-T9C2D", state: "running" }],
    }),
  );
  app(`/runs/${ID}`);
  const resume = await within(await header()).findByRole("button", { name: "Resume" });
  expect(resume).toHaveAccessibleDescription("A resume of this run is already running: wgs-cohort-12-T9C2D.");
  const link = within(await header()).getAllByRole("link", { name: /wgs-cohort-12-T9C2D/ })[0];
  expect(link.getAttribute("href")).toBe(`/runs/${CHILD}`);
  expect(getComputedStyle(link).color).toBe("var(--sp-text-link)"); // FU-P3-104: the app's link style
});

test("the facts link a resumed run and its parent both ways", async () => {
  detail(failedRun({ resumed_as: [{ id: CHILD, name: "wgs-cohort-12-T9C2D", state: "succeeded" }] }));
  app(`/runs/${ID}`);
  const facts = await screen.findByRole("region", { name: "Facts" });
  const child = within(facts).getByRole("link", { name: "wgs-cohort-12-T9C2D · Succeeded" });
  expect(child.getAttribute("href")).toBe(`/runs/${CHILD}`);
  expect(getComputedStyle(child).color).toBe("var(--sp-text-link)"); // FU-P3-104: the app's link style
  expect(within(facts).getByText("Resumed as")).toBeInTheDocument();
});

test("a resumed run's facts say Resume of its parent", async () => {
  const body = failedRun({ id: CHILD, name: "child", parent_run_id: ID });
  serve({
    [`/api/v1/runs/${CHILD}/processes`]: { items: [] },
    [`/api/v1/runs/${CHILD}/stages`]: { items: [] },
    [`/api/v1/runs/${CHILD}/logs`]: () => new Response(""),
    [`/api/v1/runs/${CHILD}/results`]: () => json(404, { title: "Not found" }),
    [`/api/v1/runs/${CHILD}`]: body,
  });
  app(`/runs/${CHILD}`);
  const facts = await screen.findByRole("region", { name: "Facts" });
  const parent = within(facts).getByRole("link", { name: "run 7T9V1W" });
  expect(parent.getAttribute("href")).toBe(`/runs/${ID}`);
  expect(getComputedStyle(parent).color).toBe("var(--sp-text-link)"); // FU-P3-104: the app's link style
  expect(within(facts).getByText("Resume of")).toBeInTheDocument();
});

test.each([
  ["failed", true, "menu"],
  ["cancelled", true, "menu"],
  ["succeeded", false, "primary"],
  ["running", false, "none"],
])("a %s run: Resume %s, Copy to a new launch %s", async (state, resume, copy) => {
  detail(failedRun({ state, actions: { resume: { allowed: false, reason: "not_failed_or_cancelled" } } }));
  app(`/runs/${ID}`);
  const head = await header();
  await within(head).findByRole("button", { name: "More actions" });
  expect(within(head).queryByRole("button", { name: "Resume" }) !== null).toBe(resume);
  const primary = within(head).queryByRole("link", { name: "Copy to a new launch" });
  const item = within(await openMore()).queryByRole("menuitem", { name: "Copy to a new launch" });
  expect(primary ? "primary" : item ? "menu" : "none").toBe(copy);
  const link = primary ?? item;
  if (link) expect(link.getAttribute("href")).toBe(`/launch?from=${ID}`);
});

test("a run started from a terminal has neither Resume nor Copy to a new launch, nor Command", async () => {
  detail(failedRun({ origin: "cli-observed", command: null, actions: { resume: { allowed: false, reason: "cli_observed" } } }));
  app(`/runs/${ID}`);
  const head = await header();
  const menu = await openMore();
  expect(within(menu).queryByRole("menuitem", { name: "Copy command" })).toBeNull();
  expect(within(menu).queryByRole("menuitem", { name: "Copy to a new launch" })).toBeNull();
  expect(within(head).queryByRole("button", { name: "Resume" })).toBeNull();
  expect(within(head).queryByRole("link", { name: "Copy to a new launch" })).toBeNull();
});

test("Copy's Command item copies the engine command, first of the Copy items", async () => {
  detail(failedRun());
  app(`/runs/${ID}`);
  const items = within(await openMore()).getAllByRole("menuitem");
  const first = items.find((i) => i.textContent?.startsWith("Copy ") && i.textContent !== "Copy to a new launch")!;
  expect(first).toHaveTextContent("Copy command");
  await userEvent.click(first);
  expect(await navigator.clipboard.readText()).toBe("nextflow run /g/p -params-file params.json");
  expect(await within(await header()).findByText("Copied the command")).toBeInTheDocument();
});

test("on the phone, Resume asks in a bottom sheet, Cancel then Resume (ui-spec §12.4)", async () => {
  viewport(390);
  detail(failedRun({ workflow: { ...run().workflow, engine: "snakemake" } }));
  app(`/runs/${ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Resume" }));
  const sheet = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(sheet).toHaveTextContent("Snakemake runs again with --rerun-incomplete and reuses the 143 jobs that finished.");
  const buttons = within(sheet).getAllByRole("button").map((b) => b.textContent);
  expect(buttons.indexOf("Cancel")).toBeLessThan(buttons.indexOf("Resume"));
  expect(sheet.querySelector(".sp-dialog-foot[data-stack]")).not.toBeNull();
  await waitFor(() => expect(within(sheet).getByRole("button", { name: "Cancel" })).toHaveFocus());
});

test("FU-P3-115b: Pin toggles the run's pin, and an ended run's Delete… deletes it and opens the list", async () => {
  const sent: { url: string; method?: string; body?: string }[] = [];
  const answer = (body: unknown) => (url: URL, init?: RequestInit) => {
    sent.push({ url: url.pathname, method: init?.method, body: init?.body ? String(init.body) : undefined });
    return json(200, body);
  };
  detail((url: URL, init?: RequestInit) => (init?.method === "PATCH" ? answer(failedRun({ pinned: true }))(url, init) : json(200, failedRun())), {
    "/api/v1/runs:delete": answer({ deleted: [ID], directories: [] }),
    "/api/v1/runs?": { items: [], next: null },
    "/api/v1/runs:summary": { groups: [] },
  });
  const router = app(`/runs/${ID}`);
  // the label says the action, so no aria-pressed (it would contradict a changing name)
  await userEvent.click(within(await openMore()).getByRole("menuitem", { name: "Pin" }));
  await waitFor(() => expect(sent[0]).toEqual({ url: URL_, method: "PATCH", body: '{"pinned":true}' }));
  expect(await within(await openMore()).findByRole("menuitem", { name: "Unpin" })).not.toHaveAttribute("aria-pressed");
  await userEvent.click(screen.getByRole("menuitem", { name: "Delete…" }));
  const sheet = await screen.findByRole("dialog", { name: "Delete 1 run?" });
  expect(within(sheet).getByRole("listitem")).toHaveTextContent("wgs-cohort-12 · Failed");
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(router.state.location.pathname).toBe("/runs"));
  expect(sent[1]).toEqual({ url: "/api/v1/runs:delete", method: "POST", body: JSON.stringify({ ids: [ID], directories: false }) });
});

test("FU-P3-115b: a run that has not ended has Pin but no Delete…", async () => {
  detail(failedRun({ state: "running", ended_at: null }));
  app(`/runs/${ID}`);
  const menu = await openMore();
  expect(within(menu).getByRole("menuitem", { name: "Pin" })).toBeInTheDocument();
  expect(within(menu).queryByRole("menuitem", { name: "Delete…" })).toBeNull();
});

test("FU-P3-110d: the sheet says the resume reuses the resources and the kept file; a changed copy's 422 is said in the server's words", async () => {
  const kept = { path: "/home/amartin/x.config", kept_as: "extra.config", sha256: "a".repeat(64), size: 10, includes: false, state: "recorded" };
  const message = "The kept config file of the parent changed: use Copy to a new launch";
  detail(failedRun({ default_resources: { cpus: 4, mem_mib: null, time_min: null, state: "recorded" }, config_file: kept }), {
    [`${URL_}:relaunch`]: () => json(422, { status: 422, detail: `config_file: ${message}`, errors: [{ field: "config_file", message }] }),
  });
  app(`/runs/${ID}`);
  await userEvent.click(await within(await header()).findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(dialog).toHaveTextContent("Same resources and the same kept config file (extra.config) as before.");
  await userEvent.click(within(dialog).getByRole("button", { name: "Resume" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(`Not resumed: ${message}`);
  expect(within(dialog).getByRole("alert")).not.toHaveTextContent("config_file:");
});

const KEPT = { path: "/home/amartin/x.config", kept_as: "extra.config", sha256: "a".repeat(64), size: 10, includes: false, state: "recorded" };
test.each([
  ["only resources", { default_resources: { cpus: 4, mem_mib: null, time_min: null, state: "recorded" }, config_file: null }, "Same resources as before.", "kept config file"],
  ["only the kept file", { default_resources: null, config_file: KEPT }, "The same kept config file (extra.config) as before.", "resources"],
])("FU-P3-110d: %s, named on its own (CR-P3FU110D-02)", async (_case, over, said, unsaid) => {
  detail(failedRun(over));
  app(`/runs/${ID}`);
  await userEvent.click(await within(await header()).findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(dialog).toHaveTextContent(said);
  expect(dialog).not.toHaveTextContent(unsaid);
});
