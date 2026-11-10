// The searchable log viewer (P3-parD, Thomas 2026-10-31: "logs pas searchable"): a field with a
// label, matches highlighted, an "n / m" counter that is aria-live, previous and next with Enter
// and Shift+Enter, Escape clears, a level filter, and the query lands 150 ms after typing.
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { MantineProvider } from "@mantine/core";
import { LogViewer } from "./LogViewer";

const LOG = [
  "Oct-31 10:00:01 [main] INFO  nextflow.cli.CmdRun - N E X T F L O W",
  "Oct-31 10:00:02 [Task submitter] INFO  ALIGN (S01) submitted",
  "Oct-31 10:00:03 [Task monitor] WARN  ALIGN (S02) exit 137, retrying (1/3)",
  "Oct-31 10:00:04 [Task monitor] ERROR ALIGN (S02) terminated",
  "Oct-31 10:00:05 [Task monitor] INFO  align done",
].join("\n");

let scrolled: ReturnType<typeof vi.fn>;
beforeEach(() => {
  vi.useFakeTimers();
  // Testing Library drains its own setTimeout through `jest.advanceTimersByTime` when timers are fake
  vi.stubGlobal("jest", { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) });
  scrolled = vi.fn();
  Element.prototype.scrollIntoView = scrolled as unknown as Element["scrollIntoView"];
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(Element.prototype, "scrollIntoView");
});

const user = () => userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
const field = () => screen.getByRole("searchbox", { name: "Search the engine log" });
const viewer = () => screen.getByLabelText("Engine log", { selector: "pre" });
const marks = () => [...viewer().querySelectorAll("mark")];
const counter = () => screen.getByTestId("log-search-count");
const settle = () => act(() => vi.advanceTimersByTime(150));

function show(text: string | null = LOG) {
  render(<LogViewer text={text} label="Engine log" />);
}

test("the field has a label; the counter is a polite live region", () => {
  show();
  expect(field()).toBeInTheDocument();
  expect(counter()).toHaveAttribute("aria-live", "polite");
});

test("the query lands 150 ms after typing, case-insensitive, every match marked", async () => {
  show();
  await user().type(field(), "ALIGN");
  expect(marks()).toHaveLength(0);
  act(() => vi.advanceTimersByTime(140));
  expect(marks()).toHaveLength(0);
  await settle();
  expect(marks().map((m) => m.textContent)).toEqual(["ALIGN", "ALIGN", "ALIGN", "align"]);
  expect(counter()).toHaveTextContent("1 / 4");
  expect(marks()[0]).toHaveAttribute("data-current");
  expect(scrolled).toHaveBeenCalled();
});

test("next and previous wrap around, with the buttons and with Enter and Shift+Enter", async () => {
  const u = user();
  show();
  await u.type(field(), "align");
  await settle();
  await u.click(screen.getByRole("button", { name: "Previous match" }));
  expect(counter()).toHaveTextContent("4 / 4");
  expect(marks()[3]).toHaveAttribute("data-current");
  await u.click(screen.getByRole("button", { name: "Next match" }));
  expect(counter()).toHaveTextContent("1 / 4");
  await u.type(field(), "{Enter}");
  expect(counter()).toHaveTextContent("2 / 4");
  expect(marks()[1]).toHaveAttribute("data-current");
  expect(marks().filter((m) => m.hasAttribute("data-current"))).toHaveLength(1);
  await u.type(field(), "{Shift>}{Enter}{/Shift}");
  await u.type(field(), "{Shift>}{Enter}{/Shift}");
  expect(counter()).toHaveTextContent("4 / 4");
});

test("Enter before the debounce runs the search at once", async () => {
  const u = user();
  show();
  await u.type(field(), "ERROR{Enter}");
  expect(marks()).toHaveLength(1);
  expect(counter()).toHaveTextContent("1 / 1");
});

test("no match says so; Escape clears the field and the marks", async () => {
  const u = user();
  show();
  await u.type(field(), "zzz");
  await settle();
  expect(counter()).toHaveTextContent("No match");
  expect(screen.getByRole("button", { name: "Next match" })).toBeDisabled();
  await u.clear(field());
  await u.type(field(), "align");
  await settle();
  expect(marks()).toHaveLength(4);
  await u.type(field(), "{Escape}");
  expect(field()).toHaveValue("");
  expect(marks()).toHaveLength(0);
  expect(counter()).toHaveTextContent("");
});

test("the level filter shows the lines of one level, with counts; search runs on what is shown", async () => {
  const u = user();
  show();
  const levels = screen.getByRole("group", { name: "Show lines" });
  expect(within(levels).getByRole("button", { name: /All/ })).toHaveAttribute("aria-pressed", "true");
  expect(within(levels).getByRole("button", { name: /INFO/ })).toHaveTextContent("3");
  await u.click(within(levels).getByRole("button", { name: /ERROR/ }));
  expect(within(levels).getByRole("button", { name: /ERROR/ })).toHaveAttribute("aria-pressed", "true");
  expect(viewer()).toHaveTextContent("terminated");
  expect(viewer()).not.toHaveTextContent("submitted");
  await u.type(field(), "align");
  await settle();
  expect(counter()).toHaveTextContent("1 / 1");
  await u.click(within(levels).getByRole("button", { name: /WARN/ }));
  expect(viewer()).toHaveTextContent("retrying");
  expect(viewer()).not.toHaveTextContent("terminated");
  await u.click(within(levels).getByRole("button", { name: /INFO/ }));
  expect(counter()).toHaveTextContent("1 / 2");
  await u.click(within(levels).getByRole("button", { name: /All/ }));
  expect(counter()).toHaveTextContent("1 / 4");
});

test("a level with no line says so", async () => {
  const u = user();
  show("INFO only here\n");
  expect(viewer().querySelector("[data-tone]")).toBeNull();
  await u.click(screen.getByRole("button", { name: /ERROR/ }));
  expect(viewer()).toHaveTextContent("No line at this level.");
});

test("the lines keep their level tints", () => {
  show();
  expect(screen.getByText(/terminated/).closest("[data-tone]")).toHaveAttribute("data-tone", "failed");
  expect(screen.getByText(/retrying/).closest("[data-tone]")).toHaveAttribute("data-tone", "review");
});

test("while the log loads, the viewer says so", () => {
  show(null);
  expect(viewer()).toHaveTextContent("Loading…");
});

test("a search for a regular-expression character is literal", async () => {
  const u = user();
  show();
  await u.type(field(), "(1/3)");
  await settle();
  expect(marks().map((m) => m.textContent)).toEqual(["(1/3)"]);
});

test("a log that ends with a newline has no extra empty line (CR-P3PARD-04)", () => {
  show("INFO a\nINFO b\n");
  const levels = screen.getByRole("group", { name: "Show lines" });
  expect(within(levels).getByRole("button", { name: /All/ })).toHaveTextContent("2");
  expect(within(levels).getByRole("button", { name: /INFO/ })).toHaveTextContent("2");
  expect(viewer().children).toHaveLength(2);
});

// The props of the file preview (ui-spec §4.4.1): start, levels, gutterFrom and wrap.

function heights(scrollHeight: number) {
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", { configurable: true, get: () => scrollHeight });
}
afterEach(() => Reflect.deleteProperty(HTMLElement.prototype, "scrollHeight"));

test("a log opens at its end; start top keeps the first line in view", () => {
  heights(900);
  const { unmount } = render(<LogViewer text={LOG} label="Engine log" />);
  expect(viewer().scrollTop).toBe(900);
  unmount();
  render(<LogViewer text={LOG} label="Engine log" start="top" />);
  expect(viewer().scrollTop).toBe(0);
});

test("levels off: no tints and no level filter; the search stays", () => {
  render(<LogViewer text={LOG} label="Engine log" levels={false} />);
  expect(screen.queryByRole("group", { name: "Show lines" })).toBeNull();
  expect(viewer().querySelector("[data-tone]")).toBeNull();
  expect(field()).toBeInTheDocument();
});

test("gutterFrom numbers the lines in an aria-hidden gutter, outside the line's text", () => {
  render(<LogViewer text={"alpha\nbeta\n"} label="Engine log" gutterFrom={41} levels={false} />);
  const gutter = [...viewer().querySelectorAll("[data-gutter]")];
  expect(gutter.map((g) => g.textContent)).toEqual(["41", "42"]);
  for (const g of gutter) expect(g).toHaveAttribute("aria-hidden", "true");
  expect(viewer().textContent).toContain("alpha");
});

test("without gutterFrom there is no gutter (an End read)", () => {
  render(<LogViewer text={LOG} label="Engine log" />);
  expect(viewer().querySelector("[data-gutter]")).toBeNull();
});

test("wrap off keeps lines on one row; wrap on wraps them, numbers beside their line", () => {
  const { unmount } = render(<LogViewer text={LOG} label="Engine log" />);
  expect(viewer()).toHaveClass("sp-nowrap");
  unmount();
  render(<LogViewer text={LOG} label="Engine log" wrap gutterFrom={1} />);
  expect(viewer()).not.toHaveClass("sp-nowrap");
  expect(viewer()).toHaveAttribute("data-wrap");
});

test("across the 768 px breakpoint the search follows: field on a desktop, closed and unfocused on the phone (CR-P3FU85C-07)", () => {
  const { rerender } = render(<LogViewer text={LOG} label="Engine log" searchButton />, { wrapper: MantineProvider }); // Search is a Mantine button (FU-P3-104)
  expect(screen.queryByRole("searchbox")).toBeNull();
  rerender(<LogViewer text={LOG} label="Engine log" />); // phone to desktop
  expect(field()).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Search" })).toBeNull();
  rerender(<LogViewer text={LOG} label="Engine log" searchButton />); // desktop to phone
  expect(screen.getByRole("button", { name: "Search" })).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("searchbox")).toBeNull();
  expect(document.body).toHaveFocus();
});
