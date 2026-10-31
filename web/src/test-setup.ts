// jsdom lacks what Mantine reads at start (matchMedia, ResizeObserver).
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

window.matchMedia ??= (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList;

// A test that sets a viewport (testing.tsx `viewport`) gets the plain one back afterwards.
const plainMatchMedia = window.matchMedia;
afterEach(() => {
  window.matchMedia = plainMatchMedia;
});

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// The router's scroll restoration calls scrollTo, which jsdom does not implement (FU-P3-23).
window.scrollTo = () => {};
