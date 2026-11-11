// UI-09: the run header's actions (ui-spec §12.4, §12.5, §12.7, §4.11): one primary chosen by the
// run's state, the rest in a "More actions" menu with Delete… last, the Copy items in that menu,
// the primary in the pinned bar on the phone, and Facts folded on every tab but Summary.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, json, run, serve, stubStream, viewport } from "../testing";

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
const URL_ = `/api/v1/runs/${ID}`;
const ENDED = { ended_at: "2026-10-31T08:00:00+00:00", head: { session: `spectio-${ID}`, node: "login1", alive: false, exit_code: 1, checked: true } };

function detail(over: Record<string, unknown>) {
  const body = {
    ...DETAIL,
    ...run({ name: "wgs-cohort-12", params: { outdir: "results" }, ...over }),
    actions: { resume: { allowed: over.state === "failed", reason: null } },
    command: { argv: ["nextflow", "run", "/g/p"], text: "nextflow run /g/p" },
  };
  serve({
    [`${URL_}/processes`]: { items: [] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/logs`]: () => new Response(""),
    [`${URL_}/results`]: { root: "/g/out", path: "", exists: false, entries: [], truncated: false, reports: [] },
    "/api/v1/runs:delete": () => json(200, { deleted: [ID], directories: [] }),
    [URL_]: (_url: URL, init?: RequestInit) => json(200, init?.method === "PATCH" ? { ...body, pinned: true } : body),
  });
}

const header = async () => (await screen.findByRole("heading", { level: 1 })).closest("header")!;
/** The header's own actions, outside the menu: the primary and More actions. */
const actions = async () => {
  const head = await header();
  await within(head).findByRole("button", { name: "More actions" });
  return [...head.querySelectorAll<HTMLElement>(".sp-run-actions a, .sp-run-actions button")].map((b) => b.getAttribute("aria-label") ?? b.textContent);
};
const openMenu = async () => {
  await userEvent.click(within(await header()).getByRole("button", { name: "More actions" }));
  return screen.findByRole("menu");
};
const itemNames = (menu: HTMLElement) => within(menu).getAllByRole("menuitem").map((i) => i.textContent);

test.each([
  { state: "running", primary: "Cancel run" },
  { state: "failed", primary: "Resume" },
  { state: "cancelled", primary: "Resume" },
  { state: "succeeded", primary: "Copy to a new launch" },
])("a $state run shows one primary, $primary, then More actions", async ({ state, primary }) => {
  detail(state === "running" ? { state } : { state, ...ENDED });
  app(`/runs/${ID}`);
  expect(await actions()).toEqual(["More actions", primary]);
});

test("a run started from a terminal has no primary, only More actions", async () => {
  detail({ state: "failed", origin: "cli-observed", ...ENDED });
  app(`/runs/${ID}`);
  expect(await actions()).toEqual(["More actions"]);
});

test("More actions holds the other actions, the Copy items, and Delete… last after a divider", async () => {
  detail({ state: "failed", ...ENDED });
  app(`/runs/${ID}`);
  const more = within(await header()).getByRole("button", { name: "More actions" });
  expect(more).toHaveAttribute("aria-haspopup", "menu");
  const menu = await openMenu();
  expect(itemNames(menu)).toEqual([
    "Copy to a new launch",
    "Pin",
    "Copy command",
    "Copy config (params.json)",
    "Copy run directory",
    "Copy run ID",
    "Delete…",
  ]);
  const items = within(menu).getAllByRole("menuitem");
  expect(items.at(-1)!.previousElementSibling).toHaveClass("mantine-Menu-divider");
  expect(items.at(-1)).toHaveClass("sp-menu-danger");
  expect(items[0]).toHaveAttribute("href", `/launch?from=${ID}`);
});

test("a running run's menu has Pin and Copy, and no Delete…", async () => {
  detail({ state: "running" });
  app(`/runs/${ID}`);
  const menu = await openMenu();
  expect(itemNames(menu)).toEqual(["Pin", "Copy command", "Copy config (params.json)", "Copy run directory", "Copy run ID"]);
});

test("every item is reachable by keyboard; Escape closes and returns to More actions", async () => {
  detail({ state: "succeeded", ...ENDED });
  app(`/runs/${ID}`);
  const more = within(await header()).getByRole("button", { name: "More actions" });
  more.focus();
  await userEvent.keyboard("{Enter}");
  const menu = await screen.findByRole("menu");
  const items = within(menu).getAllByRole("menuitem");
  await userEvent.keyboard("{ArrowDown}");
  const seen = [document.activeElement];
  for (let i = 1; i < items.length; i++) {
    await userEvent.keyboard("{ArrowDown}");
    seen.push(document.activeElement);
  }
  expect(seen).toEqual(items);
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  await waitFor(() => expect(more).toHaveFocus());
});

test("a Copy item copies, closes the menu and says so in the header's status", async () => {
  detail({ state: "succeeded", ...ENDED });
  app(`/runs/${ID}`);
  const menu = await openMenu();
  await userEvent.click(within(menu).getByRole("menuitem", { name: "Copy run ID" }));
  expect(await navigator.clipboard.readText()).toBe(ID);
  await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  expect(within(await header()).getByText("Copied the run ID")).toHaveAttribute("role", "status");
});

test("Pin in the menu pins the run; the next opening says Unpin", async () => {
  detail({ state: "succeeded", ...ENDED });
  app(`/runs/${ID}`);
  await userEvent.click(within(await openMenu()).getByRole("menuitem", { name: "Pin" }));
  expect(await within(await openMenu()).findByRole("menuitem", { name: "Unpin" })).toBeInTheDocument();
});

test("Delete… in the menu opens its dialog, and Cancel returns focus to More actions", async () => {
  detail({ state: "succeeded", ...ENDED });
  app(`/runs/${ID}`);
  await userEvent.click(within(await openMenu()).getByRole("menuitem", { name: "Delete…" }));
  const dialog = await screen.findByRole("dialog", { name: "Delete 1 run?" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(screen.getByRole("button", { name: "More actions" })).toHaveFocus());
});

test("on the phone the primary sits in the pinned action bar, More actions stays in the header", async () => {
  viewport(390);
  detail({ state: "failed", ...ENDED });
  app(`/runs/${ID}`);
  const resume = await screen.findByRole("button", { name: "Resume" });
  expect(resume.closest(".sp-run-bar")).not.toBeNull();
  expect(screen.getByRole("button", { name: "More actions" }).closest(".sp-run-bar")).toBeNull();
});

test("Facts are open on Summary and folded on the other tabs", async () => {
  detail({ state: "succeeded", ...ENDED });
  app(`/runs/${ID}?tab=tasks`);
  const facts = async () => within(await screen.findByRole("region", { name: "Facts" })).getByRole("button", { name: /^Facts/ });
  expect(await facts()).toHaveAttribute("aria-expanded", "false");
  await userEvent.click(screen.getByRole("tab", { name: "Summary" }));
  await waitFor(async () => expect(await facts()).toHaveAttribute("aria-expanded", "true"));
});
