import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test } from "vitest";
import { FoldSection } from "./FoldSection";
import { ICONS } from "../icons";

beforeEach(() => window.localStorage.clear());

function fold(defaultOpen = true) {
  return render(
    <FoldSection id="params" screen="run" icon={ICONS.sliders} title="Parameters" summary="4 set at launch" defaultOpen={defaultOpen}>
      <p>outdir = results</p>
    </FoldSection>,
  );
}

test("UX-PAR-02: a section folds and unfolds from a native button with aria-expanded and aria-controls", async () => {
  fold();
  const toggle = screen.getByRole("button", { name: /^Parameters/ });
  expect(toggle.tagName).toBe("BUTTON");
  expect(toggle.closest("h2")).not.toBeNull();
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  const body = document.getElementById(toggle.getAttribute("aria-controls")!)!;
  expect(body).toBeVisible();
  expect(screen.getByText("outdir = results")).toBeVisible();
  expect(screen.queryByText("4 set at launch")).toBeNull(); // the summary only shows folded
  expect(screen.getByRole("region", { name: "Parameters" })).toBeInTheDocument();

  toggle.focus();
  await userEvent.keyboard("{Enter}");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveFocus();
  expect(body).not.toBeVisible();
  expect(screen.getByText("4 set at launch")).toBeVisible();

  await userEvent.keyboard(" ");
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(toggle).toHaveFocus();
  expect(screen.getByText("outdir = results")).toBeVisible();
});

test("UX-PAR-02: a folded default, and the reader's choice remembered per screen", async () => {
  const first = fold(false);
  const toggle = screen.getByRole("button", { name: /^Parameters/ });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByText("outdir = results")).toBeNull();
  await userEvent.click(toggle);
  first.unmount();
  fold(false);
  expect(screen.getByRole("button", { name: /^Parameters/ })).toHaveAttribute("aria-expanded", "true");
});

test("UX-PAR-02: storage that throws does not break the section", async () => {
  const getItem = Storage.prototype.getItem;
  Storage.prototype.getItem = () => {
    throw new Error("blocked");
  };
  try {
    fold();
    expect(screen.getByRole("button", { name: /^Parameters/ })).toHaveAttribute("aria-expanded", "true");
  } finally {
    Storage.prototype.getItem = getItem;
  }
});

test("UX-PAR-30: a status stays beside the title open or folded, a description under it, and no screen means no memory", async () => {
  render(
    <FoldSection id="g0" icon={ICONS.folder} title="Input/output" sub="Where the data is · 2 parameters" status="1 changed" defaultOpen={false}>
      <p>fields</p>
    </FoldSection>,
  );
  const toggle = screen.getByRole("button", { name: "Input/output 1 changed" });
  expect(toggle).toHaveAccessibleDescription("Where the data is · 2 parameters");
  await userEvent.click(toggle);
  expect(screen.getByRole("button", { name: "Input/output 1 changed" })).toHaveAttribute("aria-expanded", "true");
  expect(window.localStorage.length).toBe(0);
});
