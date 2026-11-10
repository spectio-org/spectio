# Lean P3 helpers for the orchestrator

Used by the autopilot orchestrator since 2026-11-09 (Thomas: optimise, simplify, cut costs; [autopilot §13](../../../docs/playbooks/autopilot.md) items 7 and 8). Not product code.

| File | Use |
|---|---|
| `p3-lean.js` | Workflow script, one P3 task: `Workflow({scriptPath, args: {step, task, base, title, extra, session, security}})`. Boards-only tasks: the worker cannot start `ux-reviewer`; the orchestrator runs it after the workflow. |
| `p3-batch.js` | Workflow script, one batch: `args: {batch, steps[], base, head, title, session, font, milestone}` (a JSON object, not a string). `milestone: true` adds the figure and `doc-reviewer` ([autopilot §14](../../../docs/playbooks/autopilot.md)). |
| `prflow.sh <step> <title>` | Run from the step's worktree with `SCRATCH` set: moves `docs-pr-body.md` to `$SCRATCH/<step>-pr-body.md`, pushes, runs the `pr-body` check. PR titles must be Conventional Commits (`docs(ui):`, not `design(ui):`). |
| `waitci.sh <sha>` | Run in the background; prints the non-green checks of that commit when all are done. |
| `resolve_docs.py <files>` | Resolves the usual Progress and inbox merge conflicts (both sides kept). Check where an appended block landed. |
| `sockshot.js <socket> <cookie> <out> <path> [click]` | Screenshots a local `spectio serve` through its Unix socket only (no TCP port); the cookie comes from `spectio login --print-link` and `POST /api/v1/auth/magic-links:exchange` with an `Origin` header. |

Labels: `no-figure` on task PRs and on batch PRs that do not close a milestone (the PR-body tool strips image embeds); `screenshots` on batch and promotion PRs that retake more than 3 existing shots.
