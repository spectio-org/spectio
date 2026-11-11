import { Button, MantineProvider } from "@mantine/core";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { ICONS } from "../icons";
import { LayoutContext } from "./layout";
import { PageHead } from "./PageHead";
import { providerProps } from "./theme";

// PageHead v2 (ui-spec §12.4, §12.5; UI-03): tile, h1, subtitle, actions on the right with one
// primary at most and a "More actions" menu; on the phone the title row and a pinned bar.

afterEach(() => document.querySelectorAll("[data-testid=title-row]").forEach((r) => r.remove()));

function wrap(ui: ReactNode, phone = false) {
  const row = document.createElement("div");
  row.dataset.testid = "title-row";
  document.body.append(row);
  return render(
    <MantineProvider {...providerProps}>
      <LayoutContext.Provider value={{ phone, titleRow: phone ? row : null }}>{ui}</LayoutContext.Provider>
    </MantineProvider>,
  );
}

test("UI-03: the head is a banner-free header with the section tile, the h1 and its subtitle", () => {
  wrap(<PageHead section="runs" title="Runs" sub="5 runs · 0 active" />);
  const h1 = screen.getByRole("heading", { level: 1, name: "Runs" });
  expect(h1).toHaveAttribute("tabindex", "-1"); // the route-focus target
  const head = h1.closest("header")!;
  expect(head.querySelector(".sp-head-tile[data-section='runs'] svg")).toHaveAttribute("width", "24");
  expect(within(head).getByText("5 runs · 0 active")).toBeInTheDocument();
  expect(within(head).queryByRole("button")).toBeNull();
});

test("UI-03: secondaries come first, then the More actions menu, then the one primary at the far right", () => {
  wrap(
    <PageHead
      section="environments"
      title="Environments"
      secondary={[<Button key="a" variant="default">Import</Button>]}
      more={[{ label: "Export", onClick: () => {} }]}
      primary={<Button>New environment</Button>}
    />,
  );
  const names = within(screen.getByRole("banner")).getAllByRole("button").map((b) => b.getAttribute("aria-label") ?? b.textContent);
  expect(names).toEqual(["Import", "More actions", "New environment"]);
});

test("UI-03: the More actions menu opens from the keyboard, its destructive item last after a divider in the failed colour", async () => {
  const del = vi.fn();
  const exp = vi.fn();
  wrap(
    <PageHead
      section="runs"
      title="rnaseq-a"
      more={[
        { label: "Delete…", onClick: del, destructive: true },
        { label: "Export", onClick: exp },
        { label: "Copy ID", onClick: () => {} },
      ]}
    />,
  );
  const trigger = screen.getByRole("button", { name: "More actions" });
  expect(trigger).toHaveAttribute("aria-haspopup", "menu");
  trigger.focus();
  await userEvent.keyboard("{Enter}");
  const menu = await screen.findByRole("menu");
  const items = within(menu).getAllByRole("menuitem");
  expect(items.map((i) => i.textContent)).toEqual(["Export", "Copy ID", "Delete…"]);
  expect(items[2].previousElementSibling).toHaveClass("mantine-Menu-divider");
  expect(items[2]).toHaveAttribute("data-destructive", "true");
  await userEvent.click(items[0]);
  expect(exp).toHaveBeenCalledOnce();
  expect(del).not.toHaveBeenCalled();
});

test("UI-03: one primary at most and two secondaries at most, by the props' types", () => {
  const ok = () => (
    <>
      <PageHead section="home" title="t" primary={<Button>One</Button>} />
      <PageHead section="home" title="t" secondary={[<Button key="a" />, <Button key="b" />]} />
    </>
  );
  // @ts-expect-error: a list of primaries is refused
  const two = () => <PageHead section="home" title="t" primary={[<Button key="a" />, <Button key="b" />]} />;
  // @ts-expect-error: a third secondary goes to the More actions menu
  const three = () => <PageHead section="home" title="t" secondary={[<Button key="a" />, <Button key="b" />, <Button key="c" />]} />;
  expect([ok, two, three]).toHaveLength(3);
});

test("UI-03: a page may draw its own icon in the section's tile (Profile)", () => {
  wrap(<PageHead section="home" icon={ICONS.info} title="Profile" />);
  expect(document.querySelector(".sp-head-tile path")).toHaveAttribute("d", ICONS.info);
});

test("UI-03, phone: the title and subtitle go to the title row and the primary to the bar pinned above the tab bar", () => {
  wrap(<PageHead section="environments" title="Environments" sub="1 environment" primary={<Button>New environment</Button>} />, true);
  const row = screen.getByTestId("title-row");
  expect(within(row).getByRole("heading", { level: 1, name: "Environments" })).toBeInTheDocument();
  expect(within(row).getByText("1 environment")).toBeInTheDocument();
  expect(screen.queryByRole("banner")).toBeNull();
  const bar = screen.getByRole("button", { name: "New environment" }).closest(".sp-head-bar");
  expect(bar).not.toBeNull();
});

test("UI-03, phone: the subtitle may stay in the page, the primary may stay out (Launch, Runs), Home keeps its head in the page", () => {
  const { unmount } = wrap(<PageHead section="launch" title="Launch a workflow" sub="A directory" phoneTitle="title" phonePrimary="none" primary={<Button>Launch</Button>} />, true);
  const row = screen.getByTestId("title-row");
  expect(within(row).queryByText("A directory")).toBeNull();
  expect(screen.getByText("A directory")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Launch" })).toBeNull();
  unmount();
  row.remove();

  wrap(<PageHead section="home" title="Good morning" phoneTitle="page" primary={<Button>Launch a workflow</Button>} />, true);
  const head = screen.getByRole("banner");
  expect(within(head).getByRole("heading", { level: 1, name: "Good morning" })).toBeInTheDocument();
  expect(within(head).queryByRole("button")).toBeNull();
  expect(screen.getByRole("button", { name: "Launch a workflow" }).closest(".sp-head-bar")).not.toBeNull();
});
