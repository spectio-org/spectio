// AG Grid's lazy chunk (ui-spec §4.13): when it fails to load, the table's place says so with
// Retry, and the rest of the page stays (CR-P3FU101A-07).
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { app, run, serve, stubStream } from "../testing";

const chunk = vi.hoisted(() => ({ fail: true }));
vi.mock("./DataGrid", () => {
  if (chunk.fail) throw new Error("Failed to fetch dynamically imported module");
  return { default: ({ label }: { label: string }) => <div role="grid" aria-label={label} /> };
});

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

test("CR-P3FU101A-07: a grid chunk that fails to load shows an inline error with Retry, and the page stays", async () => {
  serve({ "/api/v1/runs:summary": { groups: [] }, "/api/v1/runs": { items: [run()], next: null } });
  app("/runs");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("The table could not be loaded.");
  // the page around it is still there
  expect(screen.getByRole("heading", { level: 1, name: "Runs" })).toBeInTheDocument();
  expect(screen.getByRole("searchbox", { name: "Filter by run name" })).toBeInTheDocument();
  chunk.fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("grid", { name: "Runs" })).toBeInTheDocument();
  expect(screen.queryByRole("alert")).toBeNull();
});
