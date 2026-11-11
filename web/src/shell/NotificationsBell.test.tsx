// Notifications in 0.0.1 (FU-P3-113; ui-spec top bar note): the bell names its unread count, opens
// a modal panel of items derived from the runs (GET /me/notifications), each a link to its run;
// "Mark all as read" posts the newest item's time (POST /me/notifications:mark-read).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FakeEventSource, app, json, serve, stubStream, viewport } from "../testing";

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const FAILED = { id: `run_failed:${ID}`, kind: "run_failed", run_id: ID, run_name: "rnaseq-a", at: "2026-11-10T09:03:00+00:00", read: false };
const DONE = { id: "run_succeeded:run_2", kind: "run_succeeded", run_id: "run_2", run_name: null, at: "2026-11-10T08:00:00+00:00", read: true };
const LIST = { items: [FAILED, DONE], unread: 1, read_up_to: "2026-11-10T08:00:00+00:00" };
const READ = { items: [{ ...FAILED, read: true }, DONE], unread: 0, read_up_to: FAILED.at };

beforeEach(() => {
  viewport(1440);
  stubStream();
});
afterEach(() => vi.unstubAllGlobals());

async function openPanel(unread = 1) {
  const bell = await screen.findByRole("button", { name: `Notifications, ${unread} unread` });
  await userEvent.click(bell);
  return { bell, panel: await screen.findByRole("dialog", { name: "Notifications" }) };
}

test("the bell names and shows the unread count", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const bell = await screen.findByRole("button", { name: "Notifications, 1 unread" });
  expect(bell).toHaveTextContent("1");
  // the search of FU-P3-89 stays
  expect(screen.getByRole("button", { name: "Search runs, pipelines and pages" })).toBeInTheDocument();
});

test("the panel is modal, lists links to the runs, closes on Escape and gives focus back", async () => {
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { bell, panel } = await openPanel();
  expect(panel).toHaveAttribute("aria-modal", "true");
  const link = within(panel).getByRole("link", { name: /^rnaseq-a failed, .+, unread$/ });
  expect(link).toHaveAttribute("href", `/runs/${ID}`);
  expect(within(panel).getByRole("link", { name: /^run_2 succeeded, / })).toHaveAttribute("href", "/runs/run_2");
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(bell).toHaveFocus());
});

test("Mark all as read posts the newest item's time and clears the count", async () => {
  const marked = vi.fn((_url: URL, _init?: RequestInit) => json(200, READ));
  serve({ "/api/v1/me/notifications:mark-read": marked, "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  await userEvent.click(within(panel).getByRole("button", { name: "Mark all as read" }));
  await waitFor(() => expect(marked).toHaveBeenCalledTimes(1));
  const init = marked.mock.calls[0][1];
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual({ up_to: FAILED.at });
  expect(await screen.findByRole("button", { name: "Notifications, 0 unread" })).toBeInTheDocument();
});

test("no notification yet: an empty state, and no Mark all as read", async () => {
  serve({ "/api/v1/me/notifications": { items: [], unread: 0, read_up_to: null } });
  app("/environments");
  const { panel } = await openPanel(0);
  expect(within(panel).getByText("No notifications yet")).toBeInTheDocument();
  expect(within(panel).queryByRole("button", { name: "Mark all as read" })).toBeNull();
});

test("a failed load shows an error line with Retry", async () => {
  let fail = true;
  serve({
    "/api/v1/me/notifications": () => (fail ? json(503, { title: "Unavailable", detail: "down" }) : json(200, LIST)),
  });
  app("/environments");
  const bell = await screen.findByRole("button", { name: "Notifications" });
  await userEvent.click(bell);
  const panel = await screen.findByRole("dialog", { name: "Notifications" });
  expect(await within(panel).findByText("Notifications could not be loaded: down")).toBeInTheDocument();
  fail = false;
  await userEvent.click(within(panel).getByRole("button", { name: "Retry" }));
  expect(await within(panel).findByRole("link", { name: /^rnaseq-a failed/ })).toBeInTheDocument();
});

test("a run change on the event stream refreshes the count", async () => {
  let answer: object = { items: [], unread: 0, read_up_to: null };
  serve({ "/api/v1/me/notifications": () => json(200, answer) });
  app("/environments");
  await screen.findByRole("button", { name: "Notifications, 0 unread" });
  answer = LIST;
  FakeEventSource.last!.frame({ run_id: ID });
  expect(await screen.findByRole("button", { name: "Notifications, 1 unread" }, { timeout: 3000 })).toBeInTheDocument();
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

test("on a 360 px phone the bell shows and the panel is a full-screen sheet (CR-P3FU113-01)", async () => {
  viewport(360);
  serve({ "/api/v1/me/notifications": LIST });
  app("/environments");
  const { bell, panel } = await openPanel();
  // jsdom applies no CSS: sp-narrow-hide (display:none below 390 px, shell.css) must not be on the bell
  expect(bell).not.toHaveClass("sp-narrow-hide");
  // the theme switch gives up its place instead: the Profile page sets the colour mode too (FU-P3-112)
  expect(screen.getByRole("switch", { name: "Dark theme", hidden: true })).toHaveClass("sp-narrow-hide");
  expect(panel).toHaveAttribute("data-full-screen", "true");
});

test("FU-P3-116: after Mark all as read, focus stays in the panel, on its heading", async () => {
  serve({ "/api/v1/me/notifications:mark-read": READ, "/api/v1/me/notifications": LIST });
  app("/environments");
  const { panel } = await openPanel();
  await userEvent.click(within(panel).getByRole("button", { name: "Mark all as read" }));
  await waitFor(() => expect(within(panel).queryByRole("button", { name: "Mark all as read" })).toBeNull());
  await waitFor(() => expect(within(panel).getByRole("heading", { name: "Notifications" }).contains(document.activeElement)).toBe(true));
});
