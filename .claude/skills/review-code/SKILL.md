---
name: review-code
description: Review and simplify the code of one Spectio build step or branch — independent code-reviewer and security-reviewer passes, a fix loop with the worker, then a behaviour-preserving code-simplifier pass, with the tests re-run after each change. Use after every build step (the autopilot skill calls it before write-docs), at the end of a plan executed with subagent-driven-development, and before opening any PR that changes code.
argument-hint: "<step-id or branch> [BASE]"
---

# Review and simplify code: $ARGUMENTS

Rules: `karpathy-guidelines` (simplicity first, surgical changes) and `requesting-code-review`. This skill is the procedure; the agents are `code-reviewer` and `security-reviewer` (both read-only) and `code-simplifier` (edits the step's branch only).

**When it applies.** Any step that changed code: `build` steps, a `spike` whose code a later step will reuse, and the whole branch of a plan. A step whose diff touches only docs, specs or boards skips it and says so in its Progress page.

1. **Pin the range.** BASE is the commit the step started from (the integration branch tip at dispatch, recorded by the autopilot as `base` in the step's `state.json` entry, or given as `$1`). HEAD is the step branch tip. Write both down; never use `HEAD~1`.
2. **Baseline.** Run the step's test or exit-check command on HEAD and keep the output. A failing baseline goes back to the worker before any review.
3. **Review.** Dispatch `code-reviewer` with only: the step's prompt (or plan task), the owning spec section, BASE, HEAD and the worker's report. Not your reasoning, not the session history. In parallel, dispatch `security-reviewer` on the same range with the same inputs, for every step, whatever the diff touches (Thomas, 2026-10-27).
4. **Fix loop.** On `changes` from either reviewer, send the blocker and major findings (not the `simplify:` ones) to the worker that built the step, in the same worktree. Then repeat 2–3 on the new HEAD. At most two rounds; after that set the step `blocked` and write an inbox entry with the open findings. Exception: while a security blocker or major is open, further rounds are allowed so that it is fixed in the step (Thomas, inbox #75, 2026-10-30); say how many rounds ran in the report. On `block`, stop and fix the cause first (leak, data loss).
   - Security blockers and majors are always fixed; they are never deferred to an inbox entry while the step is marked done.
5. **Simplify.** Once both verdicts are `approve` (the step is done only then), dispatch `code-simplifier` with BASE, the new HEAD, the test command and the `simplify:` findings. It commits on the step branch and re-runs the tests itself.
   - `reverted` or `tests=fail`: keep the pre-simplify HEAD and note it; this never blocks the step.
   - `changed`: run the test command once more yourself and compare with the baseline. If the diff of the simplifier's commits is more than trivial, run `code-reviewer` and `security-reviewer` once more on that range only.
6. **Record.** Append the two report lines to the step's evidence, so `write-docs` puts them in the Progress page, and save the findings to `docs/reviews/code/<step-id>.md` (format of `docs/reviews/README.md`, prefix `CR-`).
7. **Report** — print `CODE  step=<id>  review=<verdict> b/M/m=<n>/<n>/<n>  security=<verdict> b/M/m=<n>/<n>/<n>  rounds=<n>  simplify=<result> -<n>/+<n>  tests=pass|fail`. Security findings go to the same file with prefix `SEC-`.

**Never:** let the simplifier change behaviour, public names or tests of kept code; skip the review because a change "is small"; let the worker review or simplify its own code.
