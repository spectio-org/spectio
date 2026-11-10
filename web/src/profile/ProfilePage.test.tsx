// The Profile page of 0.0.1 (FU-P3-112; ui-spec §4.10.1; boards LiteProfile, MLiteProfile): who
// the server runs as, this session and Sign out, the config paths with Copy, and the theme.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, json, serve, stubStream, viewport } from "../testing";
import { when } from "../runs/stateWord";
import { THEME_KEY } from "../shell/theme";

const ME_URL = "/api/v1/me";
const SIGN_OUT = "/api/v1/auth/session:sign-out";
const ME = {
  principal: { user: "amartin", uid: 1000 },
  session: { started_at: "2026-11-10T07:40:00+00:00", expires_at: null },
  paths: {
    config_file: "/home/amartin/.spectio/spectio.toml",
    data_dir: "/home/amartin/.spectio",
    db_dir: "/tmp/spectio-1000",
    observed_dir: "/home/amartin/.spectio/observed",
  },
};

beforeEach(() => {
  stubStream();
  window.localStorage.clear();
  viewport(1440);
});
afterEach(() => vi.unstubAllGlobals());

/** The top bar, once the shell is up (jsdom counts every <header> as a banner). */
async function topBar(selector: string) {
  await screen.findByRole("navigation", { name: "Main" });
  return document.querySelector<HTMLElement>(selector)!;
}

test("the avatar in the top bar is a link to /profile", async () => {
  serve({ [ME_URL]: ME });
  app("/");
  const bar = await topBar("header.sp-topbar");
  const avatar = await within(bar).findByRole("link", { name: "Profile" });
  expect(avatar).toHaveAttribute("href", "/profile");
  await userEvent.click(avatar);
  expect(await screen.findByRole("heading", { level: 1, name: "Profile" })).toBeInTheDocument();
});

test("/profile names who the server runs as and this session", async () => {
  serve({ [ME_URL]: ME });
  app("/profile");
  const who = (await screen.findByRole("heading", { name: "Who the server runs as" })).closest("section")!;
  expect(within(who).getByText("amartin")).toBeInTheDocument();
  expect(within(who).getByText("1000")).toBeInTheDocument();
  const session = screen.getByRole("heading", { name: "This session" }).closest("section")!;
  expect(session).toHaveTextContent(`Started${when(ME.session.started_at)}`);
  expect(session).toHaveTextContent("Ends when the server stops, or when you sign out");
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByText("Profile")).toHaveAttribute("aria-current", "page");
});

test("Sign out of this session posts, then says how to sign in again", async () => {
  const mock = serve({ [ME_URL]: ME, [SIGN_OUT]: () => new Response(null, { status: 204 }) });
  app("/profile");
  await userEvent.click(await screen.findByRole("button", { name: "Sign out of this session" }));
  const out = mock.mock.calls.find(([input]) => String(input).endsWith(SIGN_OUT));
  expect(out?.[1]?.method).toBe("POST");
  const said = await screen.findByText(/^Signed out of this session\./);
  expect(said).toHaveAttribute("role", "status");
  expect(said).toHaveTextContent("spectio login --print-link");
  expect(screen.queryByRole("button", { name: "Sign out of this session" })).toBeNull();
});

test("a failed sign-out stays signed in and says why", async () => {
  serve({ [ME_URL]: ME, [SIGN_OUT]: () => json(500, { title: "Server error", detail: "boom" }) });
  app("/profile");
  await userEvent.click(await screen.findByRole("button", { name: "Sign out of this session" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not sign out. boom");
  expect(screen.getByRole("button", { name: "Sign out of this session" })).toBeInTheDocument();
});

test("the config paths are read-only text, each with its own Copy button", async () => {
  serve({ [ME_URL]: ME });
  const writeText = vi.fn(async () => {});
  vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
  app("/profile");
  const paths = (await screen.findByRole("heading", { name: "Config paths" })).closest("section")!;
  expect(within(paths).queryByRole("textbox")).toBeNull();
  for (const path of Object.values(ME.paths)) expect(within(paths).getByText(path)).toBeInTheDocument();
  const copies = within(paths).getAllByRole("button");
  expect(copies.map((b) => b.getAttribute("aria-label"))).toEqual([
    "Copy the config file path",
    "Copy the data directory path",
    "Copy the database directory path",
    "Copy the observed runs directory path",
  ]);
  await userEvent.click(within(paths).getByRole("button", { name: "Copy the database directory path" }));
  expect(writeText).toHaveBeenCalledWith("/tmp/spectio-1000");
  expect(await within(paths).findByText("Copied the database directory path")).toBeInTheDocument();
});

test("the theme is three native radios: Light, Dark, System", async () => {
  serve({ [ME_URL]: ME });
  app("/profile");
  const group = await screen.findByRole("radiogroup", { name: "Theme" });
  const radios = within(group).getAllByRole("radio");
  expect(radios.map((r) => r.tagName)).toEqual(["INPUT", "INPUT", "INPUT"]);
  expect(within(group).getByRole("radio", { name: "System" })).toBeChecked();
  await userEvent.click(within(group).getByRole("radio", { name: "Dark" }));
  expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "dark");
  expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
  expect(within(group).getByRole("radio", { name: "Dark" })).toBeChecked();
  await userEvent.click(within(group).getByRole("radio", { name: "Light" }));
  expect(document.documentElement).toHaveAttribute("data-mantine-color-scheme", "light");
});

test("a failed read says why and retries; the theme still works", async () => {
  let fail = true;
  serve({ [ME_URL]: () => (fail ? json(500, { title: "Server error", detail: "boom" }) : json(200, ME)) });
  app("/profile");
  expect(await screen.findByRole("alert")).toHaveTextContent("Your profile could not be read. boom");
  expect(screen.getByRole("radiogroup", { name: "Theme" })).toBeInTheDocument();
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(screen.getByText("amartin")).toBeInTheDocument());
});

test("phone (360 px): the title is the top bar's h1 and the avatar links to /profile", async () => {
  viewport(360);
  serve({ [ME_URL]: ME });
  app("/profile");
  const bar = await topBar("header.sp-mtopbar");
  expect(await within(bar).findByRole("heading", { level: 1, name: "Profile" })).toBeInTheDocument();
  expect(within(bar).getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
  expect(await screen.findByText("amartin")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sign out of this session" })).toBeInTheDocument();
});
