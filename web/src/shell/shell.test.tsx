import { MantineProvider } from "@mantine/core";
import { RouterProvider, createMemoryHistory } from "@tanstack/react-router";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createAppRouter } from "../routes";
import { DETAIL, json, run, serve, viewport } from "../testing";
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
  // VERSION for GET /version only: any other path (/launch reads /environments) is a 404 problem
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/api/v1/version")
        ? new Response(JSON.stringify(VERSION), { status: 200 })
        : new Response(JSON.stringify({ title: "Not found", detail: "no such path" }), { status: 404 }),
    ),
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
  for (const name of ["Home", "Runs", "Launch", "Environments"]) {
    expect(within(sidebar).getByRole("link", { name })).toBeInTheDocument();
  }
  // The server's node from GET /version stays in the sidebar's foot.
  expect(await within(sidebar).findByText(/^SLURM · server on login1/)).toBeInTheDocument();
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

test.each([
  ["/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/results/file?path=counts.tsv", "Results", "File"],
  ["/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/workdir?task=tsk_19&attempt=2", "Work directory", null],
  ["/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/workdir/file?task=tsk_19&attempt=2&path=a.txt", "Work directory", "File"],
])("FU-P3-104: the breadcrumb of %s names the run once", async (path, page, last) => {
  // the run's name loads; its files and tasks are not there (the page's own state does not matter here)
  serve({ "/api/v1/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W": { ...run(), ...DETAIL }, "/api/v1/runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/": () => json(404, { title: "Not found" }) });
  app(path);
  const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
  await within(crumbs).findAllByText("rnaseq-a");
  const items = within(crumbs).getAllByRole("listitem").map((li) => li.textContent);
  expect(items).toEqual(["Home", "Runs", "rnaseq-a", page, ...(last ? [last] : [])]);
});

test("CR-P3FU104-01: a file page's breadcrumb ends with the name the server answered for, not the URL's", async () => {
  const id = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
  const stat = { root: "/g/demo-lab/rnaseq", path: "tables/counts.tsv", name: "counts.tsv", type: "file", size: 12, mtime: "2026-11-10T09:00:00Z" };
  serve({ [`/api/v1/runs/${id}`]: { ...run(), ...DETAIL }, [`/api/v1/runs/${id}/`]: () => json(404, { title: "Not found" }), [`/api/v1/runs/${id}/results/stat/`]: stat });
  app(`/runs/${id}/results/file?path=tables/counts.tsv`);
  const crumbs = await screen.findByRole("navigation", { name: "Breadcrumb" });
  expect(await within(crumbs).findByText("counts.tsv")).toHaveAttribute("aria-current", "page");
  expect(within(crumbs).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["Home", "Runs", "rnaseq-a", "Results", "counts.tsv"]);
  expect(within(crumbs).queryByText("tables/counts.tsv")).toBeNull();
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

test("UI-04: the top bar keys share one face and one 20 px icon", async () => {
  app();
  const bar = (await screen.findByRole("switch", { name: "Dark theme" })).closest("header")!;
  const keys = [
    within(bar).getByRole("button", { name: "Search runs, pipelines and pages" }),
    within(bar).getByRole("button", { name: /notifications/i }),
    within(bar).getByRole("switch", { name: "Dark theme" }),
    within(bar).getByRole("link", { name: "Profile" }),
  ];
  for (const key of keys) {
    const icons = key.querySelectorAll("svg");
    expect(icons).toHaveLength(1);
    expect(icons[0]).toHaveAttribute("width", "20");
    expect(icons[0].parentElement).toHaveClass("sp-key-face");
  }
});

test("UI-04: sidebar items, fold key and status share one icon size", async () => {
  app();
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  const fold = within(sidebar).getByRole("button", { name: "Fold the sidebar" });
  for (const node of [fold, ...within(sidebar).getAllByRole("link")]) {
    expect(node.querySelector("svg")).toHaveAttribute("width", "20");
  }
  expect(sidebar.querySelector(".sp-status svg")).toHaveAttribute("width", "16");
});
