// FU-P3-79: the shell's server status follows the live stream, not one GET /version at load.
import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import html from "../../index.html?raw";
import ours from "../assets/favicon.svg?raw";
import { FakeEventSource, VERSION, app, fetched, json, serve, stubStream, viewport } from "../testing";

beforeEach(() => stubStream());
afterEach(() => vi.unstubAllGlobals());

test("the sidebar foot reads Server not reached while the stream reconnects, then re-reads /version", async () => {
  const mock = serve({});
  app("/launch");
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  expect(await within(sidebar).findByText("Spectio 0.0.1 · online")).toBeInTheDocument();
  const stream = FakeEventSource.last!;
  expect(stream).not.toBeNull();
  stream.open();
  expect(fetched(mock).filter((u) => u === "/api/v1/version")).toHaveLength(1);

  stream.fail();
  expect(await within(sidebar).findByText("Server not reached")).toBeInTheDocument();
  expect(within(sidebar).queryByText(/online/)).toBeNull();

  serve({ "/api/v1/version": { ...VERSION, version: "0.0.2" } });
  stream.open();
  expect(await within(sidebar).findByText("Spectio 0.0.2 · online")).toBeInTheDocument();
});

test("a failed re-read of /version after a reconnection reads Server not reached, not online", async () => {
  serve({});
  app("/launch");
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  expect(await within(sidebar).findByText("Spectio 0.0.1 · online")).toBeInTheDocument();
  const stream = FakeEventSource.last!;
  stream.open();
  stream.fail();
  serve({ "/api/v1/version": () => json(500, { title: "Internal error", detail: "boom" }) });
  stream.open();
  expect(await within(sidebar).findByText("Server not reached")).toBeInTheDocument();
  expect(within(sidebar).queryByText(/online/)).toBeNull();
});

test("a first /version that failed is read again once the stream is live", async () => {
  serve({ "/api/v1/version": () => json(500, { title: "Internal error", detail: "boom" }) });
  app("/launch");
  const sidebar = await screen.findByRole("navigation", { name: "Main" });
  expect(await within(sidebar).findByText("Server not reached")).toBeInTheDocument();
  serve({});
  FakeEventSource.last!.open();
  expect(await within(sidebar).findByText("Spectio 0.0.1 · online")).toBeInTheDocument();
});

test("the phone node pill goes offline while the stream reconnects, and back online", async () => {
  viewport(390);
  serve({});
  app("/launch");
  expect(await screen.findByRole("img", { name: "Server on login1, online" })).toBeInTheDocument();
  const stream = FakeEventSource.last!;
  stream.open();
  stream.fail();
  expect(await screen.findByRole("img", { name: "Server not reached" })).toHaveAttribute("data-down");
  stream.open();
  expect(await screen.findByRole("img", { name: "Server on login1, online" })).toBeInTheDocument();
});

test("index.html links the emblem as the favicon (ui-spec §2, note 2026-10-28)", () => {
  expect(html).toMatch(/<link rel="icon" type="image\/svg\+xml" href="\/src\/assets\/favicon\.svg" \/>/);
  // A copy of docs/assets/brand/favicon.svg: the emblem alone, no wordmark.
  expect(ours).toMatch(/^<svg [^>]*viewBox="0 -50 200 200"/);
  expect(ours).not.toMatch(/<text/);
});
