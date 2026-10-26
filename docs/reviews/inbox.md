# Inbox — questions for Thomas

The autopilot adds entries here; answer inline with `Answer: <option>` (and a sentence if useful). Entries marked **assumed** already proceed with the recommended option; your answer overrides it on the next tick.

<!-- autopilot: append entries below this line -->

### #1 · Virgil font licence (blocks publishing the hand-drawn figures' font)

- **Context:** `tools/diagrams/FONT-LICENSE.md`. The file copied from depictio says "Copyright (c) Jason Smith … All rights reserved", while Excalidraw's page says OFL-1.1, and also MIT.
- **Options:**
  - (a) check `github.com/excalidraw/virgil` yourself and, if it is OFL, commit the font with `OFL.txt`;
  - (b) switch to Excalifont;
  - (c) keep the font local only (`SPECTIO_VIRGIL_TTF`), so CI renders SVG only and PNGs are rendered locally.
- **Recommendation:** (a), with (c) until then. **Assumed:** (c), so the font is not committed.

### #2 · Install telemetry: opt-in (current) or opt-out like depictio?

- **Context:** `telemetry-and-analytics.md` §0.4.
- **Options:**
  - (a) opt-in with a prompt at `spectio init` and at the first admin sign-in (current);
  - (b) opt-out like depictio, with a notice and the payload preview.
- **Recommendation:** (a) for institutional installs. **Assumed:** (a).

### #3 · Let CI merge into `main`?

- **Context:** `documentation-system.md` §8, `autopilot.md` §8. PRs into `autopilot/integration` auto-merge after the checks and the doc review. Merging into `main` needs `AUTOMERGE_MAIN=true`, and branch protection set up with the `gh` commands in `autopilot.md` §8.
- **Options:**
  - (a) keep human merges into `main` for now;
  - (b) set the variable now.
- **Recommendation:** (a) until W1 has run once; then (b). **Assumed:** (a).

### #4 · Permissions, status line and hook for unattended runs

- **What to add:** the JSON in `autopilot.md` §4, which covers the permission rules, the budget status line and the `StopFailure` hook. Agents cannot add it themselves.
- **Answer with:** `done` when added.
