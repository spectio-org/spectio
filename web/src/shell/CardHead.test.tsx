import { Button, MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test } from "vitest";
import { ICONS } from "../icons";
import { CardHead } from "./CardHead";
import { providerProps } from "./theme";

// The card head of ui-spec §12.7 (UI-03): tile, h3 title, meta, actions, then the fold chevron, a
// native button with aria-expanded and aria-controls (§4.4 "Open sections").

function Card() {
  const [open, setOpen] = useState(true);
  return (
    <MantineProvider {...providerProps}>
      <section aria-labelledby="fin-title">
        <CardHead id="fin" icon={ICONS.history} title="Finished recently" meta="5 runs" actions={<Button variant="subtle">All runs →</Button>} open={open} onToggle={() => setOpen(!open)} />
        <div id="fin-body" hidden={!open}>
          <p>rnaseq-a</p>
        </div>
      </section>
    </MantineProvider>
  );
}

test("UI-03: an h3 title, its meta, the actions, then a fold button named by the title", async () => {
  render(<Card />);
  expect(screen.getByRole("heading", { level: 3, name: "Finished recently" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Finished recently" })).toBeInTheDocument();
  expect(screen.getByText("5 runs")).toBeInTheDocument();
  const buttons = screen.getAllByRole("button");
  expect(buttons.map((b) => b.textContent || b.getAttribute("aria-labelledby"))).toEqual(["All runs →", "fin-title"]);
  const fold = screen.getByRole("button", { name: "Finished recently" });
  expect(fold.tagName).toBe("BUTTON");
  expect(fold).toHaveAttribute("aria-expanded", "true");
  expect(fold).toHaveAttribute("aria-controls", "fin-body");
  expect(fold.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  expect(document.querySelector(".sp-cardhead-tile svg")).toHaveAttribute("width", "16");

  fold.focus();
  await userEvent.keyboard("{Enter}");
  expect(fold).toHaveAttribute("aria-expanded", "false");
  expect(fold).toHaveFocus();
  expect(screen.getByText("rnaseq-a")).not.toBeVisible();
  await userEvent.keyboard(" ");
  expect(fold).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("rnaseq-a")).toBeVisible();
});
