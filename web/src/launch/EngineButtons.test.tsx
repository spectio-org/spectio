import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test } from "vitest";
import type { Engine } from "../api";
import { EngineButtons } from "./EngineButtons";

function Harness({ guess }: { guess: Engine | null }) {
  const [engine, setEngine] = useState<Engine | null>(guess);
  return (
    <MantineProvider>
      <EngineButtons value={engine} onChange={setEngine} note="note" />
    </MantineProvider>
  );
}

const button = (name: string) => screen.getByRole("button", { name });

test("native buttons; the guess is pressed; a click changes it and releases the other (UX-G2-07)", async () => {
  render(<Harness guess="nextflow" />);
  const group = screen.getByRole("group", { name: "Engine" });
  for (const name of ["Nextflow", "Snakemake"]) {
    expect(button(name).tagName).toBe("BUTTON");
    expect(button(name)).toHaveAttribute("type", "button");
    expect(group).toContainElement(button(name));
  }
  expect(button("Nextflow")).toHaveAttribute("aria-pressed", "true");
  expect(button("Snakemake")).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(button("Snakemake"));
  expect(button("Snakemake")).toHaveAttribute("aria-pressed", "true");
  expect(button("Nextflow")).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("group", { name: "Engine" })).toBeInTheDocument(); // keeps its label
});

test("no guess: none pressed", () => {
  render(<Harness guess={null} />);
  expect(button("Nextflow")).toHaveAttribute("aria-pressed", "false");
  expect(button("Snakemake")).toHaveAttribute("aria-pressed", "false");
});

test("keyboard: Tab reaches both, Space presses", async () => {
  render(<Harness guess={null} />);
  await userEvent.tab();
  expect(button("Nextflow")).toHaveFocus();
  await userEvent.tab();
  expect(button("Snakemake")).toHaveFocus();
  await userEvent.keyboard(" ");
  expect(button("Snakemake")).toHaveAttribute("aria-pressed", "true");
});
