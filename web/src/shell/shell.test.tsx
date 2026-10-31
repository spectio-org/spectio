import { MantineProvider } from "@mantine/core";
import { RouterProvider, createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createAppRouter } from "../routes";
import { viewport } from "../testing";
import { THEME_KEY, providerProps } from "./theme";

const VERSION = {
  version: "0.0.1",
  node: "login1",
  runs_root: "/scratch/amartin/spectio-runs",
  account: "amartin",
  executor: "slurm",
};

function app(path = "/") {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  render(
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>,
  );
  return router;
}

beforeEach(() => {
  window.localStorage.clear();
  viewport(1440);
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(VERSION), { status: 200 })),
  );
});
afterEach(() => vi.unstubAllGlobals());

test("theme toggle is a button and switches the scheme", async () => {
  app();
  const toggle = await screen.findByRole("switch", { name: "Dark theme" });
  expect(toggle.tagName).toBe("BUTTON");
  expect(toggle).toHaveAttribute("aria-checked", "false");
  expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "light");

  await userEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-checked", "true");
  expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "dark");
  expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");

  await userEvent.click(toggle);
  expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "light");
});

test("sidebar folds with a button[aria-expanded]", async () => {
  app();
  const fold = await screen.findByRole("button", { name: "Fold the sidebar" });
  expect(fold).toHaveAttribute("aria-expanded", "true");
  const items = document.getElementById(fold.getAttribute("aria-controls")!);
  expect(items).not.toBeNull();
  const sidebar = screen.getByRole("navigation", { name: "Main" });
  expect(within(sidebar).getByText("Workspace")).toBeVisible();

  await userEvent.click(fold);
  expect(fold).toHaveAttribute("aria-expanded", "false");
  expect(fold).toHaveAccessibleName("Unfold the sidebar");
  expect(within(sidebar).queryByText("Workspace")).toBeNull();
  // Folded to the rail, every link keeps its name.
  for (const name of ["Home", "Runs", "Launch"]) {
    expect(within(sidebar).getByRole("link", { name })).toBeInTheDocument();
  }
  // The server's node from GET /version stays in the sidebar's foot.
  expect(await within(sidebar).findByText(/server on login1/)).toBeInTheDocument();
});

test("the tablet rail is folded by default", async () => {
  viewport(1024);
  app();
  const fold = await screen.findByRole("button", { name: "Unfold the sidebar" });
  expect(fold).toHaveAttribute("aria-expanded", "false");
});

test("below 768 px the tab bar replaces the sidebar", async () => {
  viewport(390);
  app("/launch");
  const tabs = await screen.findByRole("navigation", { name: "Main" });
  expect(screen.queryByRole("button", { name: /the sidebar/ })).toBeNull();
  expect(screen.getAllByRole("navigation", { name: "Main" })).toHaveLength(1);
  expect(tabs).toHaveAttribute("data-shell", "tabbar");
  expect(within(tabs).getByRole("link", { name: "Launch" })).toHaveAttribute("aria-current", "page");
  expect(within(tabs).getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  // The phone top bar names the server's node.
  expect(await screen.findByRole("img", { name: "Server on login1, online" })).toBeInTheDocument();
});

test("breadcrumbs follow the route", async () => {
  const router = app("/runs/run_01K8T2F1XT");
  const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
  expect(within(crumbs).getByRole("link", { name: "Runs" })).toHaveAttribute("href", "/runs");
  // The URL's text is not a label (SEC-P3G4-02): a run's crumb is "Run" until its name loads.
  expect(within(crumbs).getByText("Run")).toHaveAttribute("aria-current", "page");
  expect(within(crumbs).queryByText("run_01K8T2F1XT")).toBeNull();

  await router.navigate({ to: "/launch" });
  expect(await within(crumbs).findByText("Launch")).toHaveAttribute("aria-current", "page");
  expect(within(crumbs).queryByRole("link", { name: "Runs" })).toBeNull();
});

test("a malformed percent sequence keeps the shell (CR-P3G4-01)", async () => {
  app("/runs/%E0");
  const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByText("Run")).toHaveAttribute("aria-current", "page");
});

test("the phone node pill stays neutral while connecting (CR-P3G4-02)", async () => {
  viewport(390);
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => {})));
  app();
  const pill = await screen.findByRole("img", { name: "Connecting" });
  expect(pill).not.toHaveAttribute("data-down");
});

test("UX-PAR-06: on a run's page, Runs is the active item and only the last crumb is current", async () => {
  app("/runs/run_01K8T2F1XT");
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  expect(within(sidebar).getByRole("link", { name: /^Runs/ })).toHaveAttribute("aria-current", "page");
  expect(within(sidebar).getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  const current = crumbs.querySelectorAll('[aria-current="page"]');
  expect(current).toHaveLength(1);
  expect(current[0]).toHaveTextContent("Run");
  expect(within(crumbs).getByRole("link", { name: "Runs" })).not.toHaveAttribute("aria-current");
});

test("UX-PAR-06: on the phone, the Runs tab stays active on a run's page", async () => {
  viewport(390);
  app("/runs/run_01K8T2F1XT");
  const tabs = await screen.findByRole("navigation", { name: "Main" });
  expect(within(tabs).getByRole("link", { name: /^Runs/ })).toHaveAttribute("aria-current", "page");
  expect(within(tabs).getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
});

test("UX-PAR-07: the Runs item counts the active runs, also for a screen reader", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const body = String(input).includes("runs:summary")
        ? { groups: [{ key: "running", count: 4 }, { key: "queued", count: 2 }, { key: "failed", count: 3 }] }
        : VERSION;
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
  app("/");
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  expect(await within(sidebar).findByRole("link", { name: "Runs, 6 active runs" })).toBeInTheDocument();
});
