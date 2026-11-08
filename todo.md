# To do

Thomas's notes for later, not yet in a pipeline step. When a step takes an item, it names the step here and moves the item to its Progress page.

## UI (web/)

- [ ] **The real logo in the header.** `web/src/shell/TopBar.tsx` draws its own `Mark` (an inline SVG, desktop and phone). It should use the real Spectio logo. Which source counts as the real one is still open: the boards in `design/brand-canvas/` or a final asset. *(Thomas, 2026-10-31)*
- [ ] **Smooth sidebar and collapsible sections.** Opening and closing the sidebar and every collapsible section (`FoldSection`, the run detail's sections, Launch's groups) should animate (height and opacity) instead of jumping. It must honour `prefers-reduced-motion`. *(Thomas, 2026-10-31)*
- [x] **Client-side parameter validation in Launch** and **Required or optional on each parameter**: done by P1 Task 32 (step P3-t32, 2026-11-01); the items moved to `docs/progress/W5/P3-M8.md`, Task 32. *(Thomas, 2026-10-31)*
