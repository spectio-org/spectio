// jsdom applies runs.css here (vite.config.ts `test.css.include`), so these read the cascade.
import "./runs.css";
import { expect, test } from "vitest";
import { cssVariablesResolver } from "../shell/theme";
import { tone } from "./stateWord";

const shadow = (html: string) => {
  document.body.innerHTML = html;
  return getComputedStyle(document.body.firstElementChild!.matches("ul") ? document.querySelector("li")! : document.body.firstElementChild!).boxShadow;
};

test("UX-PAR-04: the state rail survives the card and list shadows", () => {
  for (const html of [
    '<ul class="sp-cards"><li data-rail data-tone="failed">x</li></ul>',
    '<ul class="sp-list"><li data-rail data-tone="failed">x</li></ul>',
    '<div class="sp-card" data-rail data-tone="failed">x</div>',
  ]) {
    const value = shadow(html);
    expect(value, html).toContain("inset 4px 0 0 var(--tone)");
    expect(value, html).toContain("var(--sp-shadow)");
  }
  // The run header carries the rail as a top bar, as on LiteRunDetail.
  expect(shadow('<header class="sp-card sp-run-head" data-rail data-tone="running">x</header>')).toContain(
    "inset 0 4px 0 var(--tone)",
  );
});

test("UX-PAR-05: state colours come from the --sp-state-* tokens, light and dark", () => {
  const { light, dark } = cssVariablesResolver({} as never);
  expect(light["--sp-state-running-fg"]).toBe("#1D5FC9");
  expect(light["--sp-state-review-fg"]).toBe("#8F5806");
  expect(light["--sp-state-failed-bg"]).toBe("#FCEBEB");
  expect(dark["--sp-state-failed"]).toBe("#EE5A5A");
  expect(dark["--sp-state-running"]).toBe("#5B9BF8");
  document.body.innerHTML = '<span class="sp-state" data-tone="running">Running</span>';
  const style = getComputedStyle(document.body.firstElementChild!);
  expect(style.getPropertyValue("--tone-fg").trim()).toBe("var(--sp-state-running-fg)");
});

test("each state maps to one of the eight token tones", () => {
  expect(tone("running")).toBe("running");
  expect(tone("awaiting_review")).toBe("review");
  expect(tone("cancelling")).toBe("cancelled");
  expect(tone("pending")).toBe("queued");
  expect(tone("cached")).toBe("cached");
  expect(tone("Done")).toBe("succeeded");
});
