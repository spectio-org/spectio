// Notifications panel (ui-spec §12.13, UI-05b): the bell names its unread count and opens a
// popover (a bottom sheet on the phone) of items derived from the runs (GET /me/notifications),
// grouped by local day, each row a link to its run; "Mark all as read" posts the newest item's time
// (POST /me/notifications:mark-read).
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, json, serve, stubStream, viewport } from "../testing";

// The clock is fixed at 2026-11-11 14:00 local time; only Date is faked, so user events still run.
const NOW = new Date(2026, 10, 11, 14, 0);
const at = (...parts: [number, number, number, number]) => new Date(2026, ...parts).toISOString();
const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const FAILED = { id: `run_failed:${ID}`, kind: "run_failed", run_id: ID, run_name: "rnaseq-a", engine: "nextflow", at: at(10, 11, 13, 48), read: false };
const WAITING = { id: "gate_waiting:run_3", kind: "gate_waiting", run_id: "run_3", run_name: "qc-b", engine: "snakemake", at: at(10, 10, 9, 3), read: false };
const DONE = { id: "run_succeeded:run_2", kind: "run_succeeded", run_id: "run_2", run_name: null, engine: "nextflow", at: at(10, 5, 10, 0), read: true };
const OLD = { id: "run_cancelled:run_4", kind: "run_cancelled", run_id: "run_4", run_name: "atac-c", engine: null, at: at(9, 28, 7, 1), read: true };
const LIST = { items: [FAILED, WAITING, DONE, OLD], unread: 2, read_up_to: DONE.at };
const READ = { items: LIST.items.map((i) => ({ ...i, read: true })), unread: 0, read_up_to: FAILED.at };
const EMPTY = { items: [], unread: 0, read_up_to: null };

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
  viewport(1440);
  stubStream();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function openPanel(unread = 2) {
  const bell = await screen.findByRole("button", { name: `Notifications, ${unread} unread` });
  await userEvent.click(bell);
  return { bell, panel: await screen.findByRole("dialog", { name: "Notifications" }) };
}
const rows = (panel: HTMLElement) => within(panel).queryAllByRole("link").filter((l) => l.getAttribute("href") !== "/runs");

test("the bell names and shows the unread count", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const bell = await screen.findByRole("button", { name: "Notifications, 2 unread" });
  expect(bell).toHaveTextContent("2");
  // the search of FU-P3-89 stays
  expect(screen.getByRole("button", { name: "Search runs, pipelines and pages" })).toBeInTheDocument();
});

test("desktop: a non-modal popover, focus on its first control, Escape closes it and focus goes back to the bell", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { bell, panel } = await openPanel();
  expect(panel).not.toHaveAttribute("aria-modal", "true");
  expect(within(panel).getByRole("heading", { level: 2, name: "Notifications" })).toBeInTheDocument();
  await waitFor(() => expect(within(panel).getByRole("radio", { name: "All" })).toHaveFocus());
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(bell).toHaveFocus());
});

test("a click outside closes the popover and focus goes back to the bell", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { bell } = await openPanel();
  fireEvent.mouseDown(document.body);
  fireEvent.mouseUp(document.body);
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(bell).toHaveFocus());
});

test("rows are grouped by local day: Today, Yesterday, then the ISO date", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  const groups = within(panel).getAllByRole("heading", { level: 3 });
  expect(groups.map((g) => g.textContent)).toEqual(["Today", "Yesterday", "2026-11-05", "2026-10-28"]);
  const today = within(panel).getByRole("list", { name: "Today" });
  expect(within(today).getAllByRole("link")).toHaveLength(1);
  expect(within(within(panel).getByRole("list", { name: "Yesterday" })).getByRole("link")).toHaveAttribute("href", "/runs/run_3");
});

test("each row is a link named by run, state word, engine, relative time and unread", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  expect(rows(panel).map((r) => r.getAttribute("aria-label"))).toEqual([
    "rnaseq-a, Failed, Nextflow, 12 min ago, unread",
    "qc-b, Awaiting review, Snakemake, 1 day ago, unread",
    "run_2, Succeeded, Nextflow, 6 days ago",
    "atac-c, Cancelled, 2026-10-28 07:01",
  ]);
  expect(rows(panel)[0]).toHaveAttribute("href", `/runs/${ID}`);
  expect(rows(panel)[0].querySelector("time")).toHaveAttribute("datetime", FAILED.at);
  expect(within(panel).getByRole("link", { name: "View all runs →" })).toHaveAttribute("href", "/runs");
});

test("Unread shows the unread rows only; with none, a Show all button", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  await userEvent.click(within(panel).getByRole("radio", { name: "Unread" }));
  expect(rows(panel).map((r) => r.getAttribute("href"))).toEqual([`/runs/${ID}`, "/runs/run_3"]);
});

test("Unread with nothing unread: 'No unread notifications' and Show all", async () => {
  serve({ "/api/v1/me/notifications": READ });
  app("/environments");
  const { panel } = await openPanel(0);
  await userEvent.click(within(panel).getByRole("radio", { name: "Unread" }));
  expect(within(panel).getByText("No unread notifications")).toBeInTheDocument();
  await userEvent.click(within(panel).getByRole("button", { name: "Show all" }));
  expect(rows(panel)).toHaveLength(4);
});

test("the list is one Tab stop with a roving tabindex: arrows, Home and End, Enter opens the run", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  const router = app("/environments");
  const { bell, panel } = await openPanel();
  const [first, second, , last] = rows(panel);
  expect(rows(panel).map((r) => r.tabIndex)).toEqual([0, -1, -1, -1]);
  first.focus();
  await userEvent.keyboard("{ArrowUp}");
  expect(first).toHaveFocus();
  await userEvent.keyboard("{ArrowDown}");
  expect(second).toHaveFocus();
  expect(rows(panel).map((r) => r.tabIndex)).toEqual([-1, 0, -1, -1]);
  await userEvent.keyboard("{End}");
  expect(last).toHaveFocus();
  await userEvent.keyboard("{Home}");
  expect(first).toHaveFocus();
  await userEvent.tab();
  expect(within(panel).getByRole("link", { name: "View all runs →" })).toHaveFocus();
  first.focus();
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(router.state.location.pathname).toBe(`/runs/${ID}`));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(bell).toHaveFocus());
});

test("loading: three skeleton rows that screen readers hear as Loading (CR-P3UI05B-03)", async () => {
  serve({ "/api/v1/me/notifications": () => new Promise<Response>(() => {}) });
  app("/environments");
  await userEvent.click(await screen.findByRole("button", { name: "Notifications" }));
  const panel = await screen.findByRole("dialog", { name: "Notifications" });
  const status = within(panel).getByRole("status");
  expect(status).toHaveTextContent("Loading…");
  expect(status.querySelectorAll(".mantine-Skeleton-root")).toHaveLength(3);
});

test("no notification yet: the empty state, and no Mark all as read", async () => {
  serve({ "/api/v1/me/notifications": EMPTY });
  app("/environments");
  const { panel } = await openPanel(0);
  expect(within(panel).getByText("No notifications yet")).toBeInTheDocument();
  // the shared empty state of UI-03 (CR-P3UI05B-03)
  expect(within(panel).getByText("No notifications yet").closest(".sp-emptystate")).not.toBeNull();
  expect(within(panel).queryByRole("button", { name: "Mark all as read" })).toBeNull();
});

test("Mark all as read: an icon button with a tooltip; it posts the newest item's time and clears the count", async () => {
  const marked = vi.fn((_url: URL, _init?: RequestInit) => json(200, READ));
  serve({ "/api/v1/me/notifications:mark-read": marked, "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  const mark = within(panel).getByRole("button", { name: "Mark all as read" });
  expect(mark).not.toHaveTextContent("Mark all as read");
  // jsdom's :focus-visible does not follow Tab here, so the tooltip on focus is checked in Chromium
  // (the UI-05b screenshots); hover shows the same tooltip
  await userEvent.hover(mark);
  expect(await screen.findByRole("tooltip")).toHaveTextContent("Mark all as read");
  await userEvent.click(mark);
  await waitFor(() => expect(marked).toHaveBeenCalledTimes(1));
  const init = marked.mock.calls[0][1];
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual({ up_to: FAILED.at });
  expect(await screen.findByRole("button", { name: "Notifications, 0 unread" })).toBeInTheDocument();
  // FU-P3-116: the button goes, focus stays in the panel, on its heading
  await waitFor(() => expect(within(panel).getByRole("heading", { name: "Notifications" })).toHaveFocus());
});

test("a failed load shows an error line with Retry", async () => {
  let fail = true;
  serve({
    "/api/v1/me/notifications": () => (fail ? json(503, { title: "Unavailable", detail: "down" }) : json(200, LIST)),
  });
  app("/environments");
  await userEvent.click(await screen.findByRole("button", { name: "Notifications" }));
  const panel = await screen.findByRole("dialog", { name: "Notifications" });
  expect(await within(panel).findByText("Notifications could not be loaded: down")).toBeInTheDocument();
  // the shared error panel of UI-03 (CR-P3UI05B-03)
  expect(within(panel).getByRole("alert")).toHaveClass("sp-errorpanel");
  fail = false;
  await userEvent.click(within(panel).getByRole("button", { name: "Retry" }));
  expect(await within(panel).findByRole("link", { name: /^rnaseq-a, Failed/ })).toBeInTheDocument();
});

test("a run change on the event stream refreshes the count", async () => {
  let answer: object = EMPTY;
  serve({ "/api/v1/me/notifications": () => json(200, answer) });
  app("/environments");
  await screen.findByRole("button", { name: "Notifications, 0 unread" });
  answer = LIST;
  FakeEventSource.last!.frame({ run_id: ID });
  expect(await screen.findByRole("button", { name: "Notifications, 2 unread" }, { timeout: 3000 })).toBeInTheDocument();
});

test("a failed Mark all as read says so, and Retry tries the mark again (CR-P3FU113-02)", async () => {
  let fail = true;
  const marked = vi.fn(() => (fail ? json(503, { title: "Unavailable", detail: "locked" }) : json(200, READ)));
  serve({ "/api/v1/me/notifications:mark-read": marked, "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  await userEvent.click(within(panel).getByRole("button", { name: "Mark all as read" }));
  expect(await within(panel).findByText("Could not mark as read: locked")).toBeInTheDocument();
  expect(within(panel).queryByText(/could not be loaded/)).toBeNull();
  fail = false;
  await userEvent.click(within(panel).getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(marked).toHaveBeenCalledTimes(2));
  expect(await screen.findByRole("button", { name: "Notifications, 0 unread" })).toBeInTheDocument();
  expect(within(panel).queryByText(/Could not mark as read/)).toBeNull();
});

test("on a 360 px phone the panel is a modal bottom sheet with a visible Mark all as read (CR-P3FU113-01)", async () => {
  viewport(360);
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { bell, panel } = await openPanel();
  // jsdom applies no CSS: sp-narrow-hide (display:none below 390 px, shell.css) must not be on the bell
  expect(bell).not.toHaveClass("sp-narrow-hide");
  // the theme switch gives up its place instead: the Profile page sets the colour mode too (FU-P3-112)
  expect(screen.getByRole("switch", { name: "Dark theme", hidden: true })).toHaveClass("sp-narrow-hide");
  expect(panel).toHaveAttribute("aria-modal", "true");
  expect(panel).toHaveClass("sp-notif-sheet");
  expect(within(panel).getByRole("button", { name: "Mark all as read" })).toHaveTextContent("Mark all as read");
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(bell).toHaveFocus());
});

// Vitest loads no CSS, so the stylesheet is read as text (the suite runs from web/).
test("the panel's lines and day labels use theme tokens (CR-P3UI05B-01, -02)", () => {
  const css = readFileSync("src/shell/shell.css", "utf8");
  const rule = (selector: string) => css.match(new RegExp(`\\n${selector.replace(/\./g, "\\.")} \\{([^}]*)\\}`))?.[1] ?? "";
  expect(css).not.toMatch(/var\(--sp-line\)/);
  expect(rule(".sp-notif-popover")).toMatch(/border: 1px solid var\(--sp-line-border\)/);
  expect(rule(".sp-notif-head")).toMatch(/border-bottom: 1px solid var\(--sp-line-divider\)/);
  expect(rule(".sp-notif-foot")).toMatch(/border-top: 1px solid var\(--sp-line-divider\)/);
  expect(rule(".sp-notif-day")).toMatch(/color: var\(--sp-text-muted\)/);
  // focus and hover keep the unread tint (CR-P3UI05B-05)
  expect(css).not.toMatch(/\.sp-notif-row:focus-visible\s*\{[^}]*background/);
});
