# To do

Thomas's notes for later, not yet in a pipeline step. When a step takes an item, it names the step here and moves the item to its Progress page.

## UI (web/)

- [ ] **The real logo in the header.** `web/src/shell/TopBar.tsx` draws its own `Mark` (an inline SVG, desktop and phone). It should use the real Spectio logo. Which source counts as the real one is still open: the boards in `design/brand-canvas/` or a final asset. *(Thomas, 2026-10-31)*
- [ ] **Smooth sidebar and collapsible sections.** Opening and closing the sidebar and every collapsible section (`FoldSection`, the run detail's sections, Launch's groups) should animate (height and opacity) instead of jumping. It must honour `prefers-reduced-motion`. *(Thomas, 2026-10-31)*
- [ ] **Client-side parameter validation in Launch.** **Taken by P1 Task 32** (Thomas, 2026-10-31: "avec 32"). Check each value against its schema type before Launch: `integer`, `number` (float), `string`, `boolean`, plus `enum`, `minimum`/`maximum` and `pattern`. Show the error on its field. Integer and number fields get numeric inputs. Today `web/src/launch/LaunchPage.tsx` checks only that required fields are not empty: the Launch reason at line 220 and a count per section at line 530. The server still validates; the client check only helps. *(Thomas, 2026-10-31)*
- [ ] **Required or optional on each parameter.** **Taken by P1 Task 32** (Thomas, 2026-10-31: "avec 32"). Each row shows whether its parameter is required or optional, from the schema's `required` lists (per nf-core group). Today only the section's count says so, never the row. *(Thomas, 2026-10-31)*
