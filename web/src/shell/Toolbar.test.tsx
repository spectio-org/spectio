import { Button, MantineProvider, SegmentedControl } from "@mantine/core";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { Toolbar, ToolbarSearch } from "./Toolbar";
import { providerProps } from "./theme";

// The toolbar of ui-spec §12.6 (UI-03): one row, search left, filters, then actions and the
// caption at the right.

test("UI-03: a named group in the order search, filters, caption and actions; the search is a labelled search box", async () => {
  const typed = vi.fn();
  render(
    <MantineProvider {...providerProps}>
      <Toolbar
        label="Filter runs"
        search={<ToolbarSearch label="Filter by run name" value="" onChange={typed} />}
        filters={<SegmentedControl data={["All", "Active"]} />}
        caption="5 of 5 runs"
        actions={<Button variant="default">Export</Button>}
      />
    </MantineProvider>,
  );
  const bar = screen.getByRole("group", { name: "Filter runs" });
  const box = within(bar).getByRole("searchbox", { name: "Filter by run name" });
  expect(box.closest(".sp-toolbar-search")).toBe(bar.firstElementChild);
  const end = bar.lastElementChild!;
  expect(end).toHaveClass("sp-toolbar-end");
  expect(end.textContent).toBe("5 of 5 runsExport");
  await userEvent.type(box, "r");
  expect(typed).toHaveBeenCalledWith("r");
});

test("UI-03: a toolbar without search or actions draws only what it has", () => {
  render(
    <MantineProvider {...providerProps}>
      <Toolbar label="Show environments as" filters={<SegmentedControl data={["Cards", "Table"]} />} />
    </MantineProvider>,
  );
  const bar = screen.getByRole("group", { name: "Show environments as" });
  expect(bar.querySelector(".sp-toolbar-search")).toBeNull();
  expect(bar.querySelector(".sp-toolbar-end")).toBeNull();
});
