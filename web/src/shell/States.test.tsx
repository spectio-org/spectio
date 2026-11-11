import { Button, MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import { EmptyState, ErrorPanel, SkeletonRows } from "./States";
import { providerProps } from "./theme";

// The shared states of ui-spec §11 and §12.12 (UI-03).

const wrap = (ui: ReactNode) => render(<MantineProvider {...providerProps}>{ui}</MantineProvider>);

test("UI-03: EmptyState says why in one sentence beside a hidden 24 px icon, then the next step", () => {
  wrap(<EmptyState icon="runs" action={<Button>Launch a workflow</Button>}>No run yet.</EmptyState>);
  const text = screen.getByText("No run yet.");
  const box = text.closest(".sp-emptystate")!;
  const svg = box.querySelector("svg")!;
  expect(svg).toHaveAttribute("width", "24");
  expect(svg.closest("[aria-hidden='true']")).not.toBeNull();
  expect(screen.getByRole("button", { name: "Launch a workflow" })).toBeInTheDocument();
});

test("UI-03: ErrorPanel is an alert with what failed, the request ID and a Retry that the keyboard reaches", async () => {
  const retry = vi.fn();
  wrap(<ErrorPanel onRetry={retry} requestId="req_01">The runs could not be read: server down.</ErrorPanel>);
  const alert = screen.getByRole("alert");
  expect(alert).toHaveTextContent("The runs could not be read: server down.");
  expect(alert).toHaveTextContent("Request ID: req_01");
  await userEvent.tab();
  expect(screen.getByRole("button", { name: "Retry" })).toHaveFocus();
  await userEvent.keyboard("{Enter}");
  expect(retry).toHaveBeenCalledOnce();
});

test("UI-03: SkeletonRows draws the rows hidden from screen readers, which hear one status line", () => {
  wrap(<SkeletonRows rows={4} label="Loading runs…" />);
  const status = screen.getByRole("status");
  expect(status).toHaveTextContent("Loading runs…");
  const rows = status.querySelectorAll(".mantine-Skeleton-root");
  expect(rows).toHaveLength(4);
  rows.forEach((r) => expect(r).toHaveAttribute("aria-hidden", "true"));
});
