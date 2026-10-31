import { useLayoutEffect, useRef } from "react";
import "./demo.css";

/** On every page of the public demo, so nobody takes the recording for a live server. */
export function DemoBanner() {
  const ref = useRef<HTMLElement>(null);
  // The banner wraps as it must; the sticky sidebar takes its measured height off its own
  // (demo.css, CR-P3DEMO-03). A CSSOM property, so the CSP needs no inline style.
  useLayoutEffect(() => {
    const el = ref.current!;
    const root = document.documentElement.style;
    const measure = () => root.setProperty("--sp-demo-banner-h", `${el.getBoundingClientRect().height}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => {
      observer.disconnect();
      root.removeProperty("--sp-demo-banner-h");
    };
  }, []);
  return (
    <aside ref={ref} className="sp-demo-banner" aria-label="About this demo">
      <span>
        Demo: recorded data from a test server, read-only. Times are moved so that the newest run ended an hour ago;
        nf-core/demo is a renamed copy of the synthetic test pipeline, not an nf-core pipeline.
      </span>{" "}
      <a href="https://spectio.pages.dev/">Spectio docs</a>
    </aside>
  );
}
