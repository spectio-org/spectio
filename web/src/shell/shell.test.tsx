import { MantineProvider } from "@mantine/core";
import { RouterProvider, createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createAppRouter } from "../routes";
import { THEME_KEY, providerProps } from "./theme";

const VERSION = {
  version: "0.0.1",
  node: "login1",
  runs_root: "/scratch/amartin/spectio-runs",
  account: "amartin",
  executor: "slurm",
};

// jsdom applies no CSS: the shell picks its layout with matchMedia, answered here for one width
// and a light system scheme.
function viewport(width: number) {
  window.matchMedia = (query: string) => {
    const max = /max-width:\s*([\d.]+)px/.exec(query);
    const min = /min-width:\s*([\d.]+)px/.exec(query);
    const matches =
      (!!max || !!min) && (!max || width <= Number(max[1])) && (!min || width >= Number(min[1]));
    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList;
  };
}

function app(path = "/") {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  render(
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>,
  );
  return router;
}

const original = window.matchMedia;
beforeEach(() => {
  window.localStorage.clear();
  viewport(1440);
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(VERSION), { status: 200 })),
  );
});
afterEach(() => {
  window.matchMedia = original;
  vi.unstubAllGlobals();
});

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
  expect(within(crumbs).getByText("run_01K8T2F1XT")).toHaveAttribute("aria-current", "page");

  await router.navigate({ to: "/launch" });
  expect(await within(crumbs).findByText("Launch")).toHaveAttribute("aria-current", "page");
  expect(within(crumbs).queryByRole("link", { name: "Runs" })).toBeNull();
});

test("a malformed percent sequence keeps the shell (CR-P3G4-01)", async () => {
  app("/runs/%E0");
  const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByText("%E0")).toHaveAttribute("aria-current", "page");
});
