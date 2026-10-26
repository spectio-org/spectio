---
name: apply-findings
description: Apply the accepted findings of a review round to the Spectio specs, record decisions in docs/decisions/log.md, and close the findings. Use after Thomas has triaged docs/reviews/<round>.md.
argument-hint: "<round-id> [finding IDs to apply, default: all marked accepted]"
disable-model-invocation: true
---

# Apply findings from $0

1. **Select.** Read `docs/reviews/$0.md`. Select the findings with status `accepted`, or the IDs given in `$ARGUMENTS`.
2. **Edit.** For each one, change the owning spec in place, without duplicating content in another spec:
   - keep section numbers stable;
   - add `[to be validated]` where the fix depends on an unverified fact.
3. **Record.** Add one dated entry to `docs/decisions/log.md`: what changed, why, and the finding IDs. For decisions that are expensive to reverse, also create a decision record from the template in `docs/decisions/README.md`.
4. **Close.** In `docs/reviews/$0.md`, set each finding to `applied` and link the commit or section, or to `rejected` with the reason Thomas gave.
5. **Verify:**
   - the docs build (`mkdocs build --strict`);
   - Mermaid blocks render;
   - `grep` finds no stale references to renamed things.
6. **Commit.** Use one commit per round, titled `docs: apply review $0 (N findings)`, and open a PR if the session has a remote.
