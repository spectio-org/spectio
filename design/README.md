# Design sources

- **`tokens/spectio-tokens.css`.** Design tokens v0.2 as CSS custom properties:
  - surfaces, lines and text;
  - accent;
  - the 8 run states;
  - section colours (Workflows = coral 700 `#A54666`, distinct from depictio's Dashboards orange);
  - actors and data-viz colours;
  - the Sky scale;
  - dark mode.
- **`ui-canvas/`.** Snapshot of the UI canvas: one `.dc.html` file per board, and `canvas.json` for the board positions and pages (structure, screens, shared shell, mobile).
  - The boards use a small template syntax: `sc-for`, `sc-if` and `dc-import` for shared components such as `AppSidebar`, `AppTopbar`, `AdminNav` and `MobileTabbar`.
  - [`tools/canvas/render.js`](../tools/canvas/render.js) renders any board to PNG without the canvas host.
- **`brand-canvas/`.** Logo and colour explorations from before the name Spectio was chosen. Some file names keep the earlier working names. `SpectioUIColors` is the current UI palette board.
