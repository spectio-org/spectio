// The demo build's screens (vite --mode demo), against the committed recording.
import { MantineProvider } from "@mantine/core";
import { RouterProvider, createHashHistory } from "@tanstack/react-router";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import raw from "../../demo/fixtures.json?raw";
import { LaunchPage } from "../launch/LaunchPage";
import { resetLive } from "../live";
import { createAppRouter } from "../routes";
import { LayoutContext } from "../shell/layout";
import { providerProps } from "../shell/theme";
import { DemoBanner } from "./DemoBanner";
import { READ_ONLY, install } from "./stub";

const FAILED = "run_01M68WEQRQPTPJ70JFS8VSQXHP";
let undo = () => {};
const { createObjectURL, revokeObjectURL } = URL;
beforeEach(() => {
  vi.stubEnv("MODE", "demo");
  resetLive();
  undo = install(JSON.parse(raw));
  Object.assign(URL, { createObjectURL: vi.fn(() => "blob:demo-log"), revokeObjectURL: vi.fn() });
});
afterEach(() => {
  undo();
  vi.unstubAllEnvs();
  Object.assign(URL, { createObjectURL, revokeObjectURL });
  window.location.hash = "";
});

test("the banner says the data is recorded and read-only, with a keyboard-reachable docs link", async () => {
  render(<DemoBanner />);
  const banner = screen.getByRole("complementary", { name: "About this demo" });
  expect(banner).toHaveTextContent("Demo: recorded data from a test server, read-only");
  await userEvent.tab();
  expect(within(banner).getByRole("link", { name: /Spectio docs/ })).toHaveFocus();
  expect(within(banner).getByRole("link", { name: /Spectio docs/ })).toHaveAttribute("href", "https://spectio.pages.dev/");
});

test("the banner shows its whole text, and the sidebar is sized from its measured height (CR-P3DEMO-03)", () => {
  let resized = () => {};
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        resized = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  let height = 49;
  const rect = vi
    .spyOn(HTMLElement.prototype, "getBoundingClientRect")
    .mockImplementation(() => ({ height }) as DOMRect);
  const root = document.documentElement.style;
  const { unmount } = render(<DemoBanner />);
  const banner = screen.getByRole("complementary", { name: "About this demo" });
  expect(banner).toHaveTextContent(
    "Times are moved so that the newest run ended an hour ago; nf-core/demo is a renamed copy of the synthetic test pipeline, not an nf-core pipeline.",
  );
  expect(root.getPropertyValue("--sp-demo-banner-h")).toBe("49px");
  height = 67;
  resized();
  expect(root.getPropertyValue("--sp-demo-banner-h")).toBe("67px");
  unmount();
  expect(root.getPropertyValue("--sp-demo-banner-h")).toBe("");
  rect.mockRestore();
  vi.unstubAllGlobals();
});

test("Launch loads the nf-core demo copy from the recording, then gives the read-only reason", async () => {
  render(
    <MantineProvider {...providerProps}>
      <LayoutContext.Provider value={{ phone: false, titleRow: null }}>
        <LaunchPage onLaunched={vi.fn()} />
      </LayoutContext.Provider>
    </MantineProvider>,
  );
  await userEvent.type(screen.getByRole("textbox", { name: /^Pipeline/ }), "/g/demo-lab/pipelines/nf-core-demo");
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  await screen.findByText(/no parameter schema/);
  const launch = screen.getAllByRole("button", { name: "Launch" }).at(-1)!;
  expect(launch).toHaveAttribute("aria-disabled", "true");
  expect(launch).toHaveAccessibleDescription(READ_ONLY);
});

test("a hash deep link opens the failed run's Logs; Open raw opens the shown text, not the API", async () => {
  window.location.hash = `#/runs/${FAILED}?tab=logs&source=head-out`;
  const router = createAppRouter(createHashHistory());
  render(
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>,
  );
  expect(await screen.findByRole("tab", { name: "Logs", selected: true })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("region", { name: "Logs" })).not.toHaveTextContent("Loading…"));
  const openRaw = screen.getByRole("link", { name: /Open raw/ });
  await waitFor(() => expect(openRaw).toHaveAttribute("href", "blob:demo-log"));
  const [blob] = vi.mocked(URL.createObjectURL).mock.calls.at(-1)! as [Blob];
  expect(blob.size).toBeGreaterThan(0);
  expect(blob.type).toBe("text/plain;charset=utf-8");
});

test("the demo build's router reads the route from the hash, so a static host can reload it", async () => {
  window.location.hash = `#/runs/${FAILED}?tab=logs`;
  vi.resetModules();
  const { router } = await import("../routes");
  expect(router.history.location.pathname).toBe(`/runs/${FAILED}`);
  expect(router.history.location.search).toBe("?tab=logs");
});
