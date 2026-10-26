# Canvas tools

- **`render.js`.** Renders a canvas board to PNG with Playwright, resolving `dc-import`, `sc-for` and `sc-if` the way the canvas host does.

  ```bash
  node tools/canvas/render.js <board.dc.html> <width> <height> <out.png> [css selectors to click before the shot]
  ```

  Example: `node tools/canvas/render.js design/ui-canvas/AdminTasks.dc.html 1440 1180 tasks.png`.

- **`collapsify.py`.** Turns section headers in a board into `<details>`/`<summary>` collapsibles.
- **`adminify.py`.** Moves an older Settings board onto the Administration layout: header, `AdminNav` and a "CLI equivalent" block.
- **`mu_*.py`.** Generators for the multi-user boards (projects, project detail, share dialog, users, service accounts). `mu_common.py` holds the shared data.

These are working tools from the design phase. Expect rough edges.
