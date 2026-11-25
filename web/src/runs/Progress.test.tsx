// The one progress cell and its count format (#385, ui-spec §12.8).
import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { ago } from "../shell/NotificationsBell";
import { Progress, progressText, tasksText } from "./RunState";
import { run } from "../testing";

test("one count format: done / total, at least while a checkpoint is open, a dash with no total", () => {
  expect(progressText(24, 32)).toBe("24 / 32");
  expect(progressText(242, 347, true)).toBe("242 / at least 347");
  expect(progressText(0, 0)).toBe("—");
  expect(tasksText(run() as never)).toBe("24 / 32");
});

test("the Progress cell is that text on one line, with the unit inline and the bar when asked", () => {
  const { container, rerender } = render(<Progress done={24} total={32} unit="jobs" />);
  expect(container.textContent).toBe("24 / 32 jobs");
  expect(container.querySelector(".sp-done")).not.toBeNull();
  expect(container.querySelector(".sp-bar")).toBeNull();
  rerender(<Progress bar done={3} total={3} />);
  expect(container.textContent).toBe("3 / 3");
  expect(container.querySelector(".sp-bar")).toHaveAttribute("data-full", "true");
  rerender(<Progress bar done={3} total={5} lower unit="jobs" />);
  expect(container.textContent).toBe("3 / at least 5 jobs");
  expect(container.querySelector(".sp-bar")).toHaveAttribute("data-full", "false");
  rerender(<Progress bar done={0} total={0} unit="jobs" />);
  expect(container.textContent).toBe("—");
});

test("one date formatter: no date reads a dash", () => {
  expect(ago(null)).toBe("—");
  expect(ago(new Date().toISOString())).toBe("just now");
});
