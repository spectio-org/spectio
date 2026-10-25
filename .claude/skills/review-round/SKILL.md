---
name: review-round
description: Run one review round on the Spectio specs by dispatching the project reviewer agents in parallel, then merge, de-duplicate and rank their findings into docs/reviews/<round>.md. Use when Thomas asks for a review round (R1…R10 in docs/playbooks/next-phase.md) or a review of specific specs.
argument-hint: "<round-id> [focus or spec files]"
disable-model-invocation: true
---

# Review round $0

Focus: $ARGUMENTS

1. **Prepare.**
   - Read `docs/playbooks/next-phase.md`, then the section for round `$0` (goal, agents, scope, exit criteria), and `docs/reviews/README.md` (finding format).
   - If `docs/reviews/` already has earlier rounds, read their open findings so you do not report them again.
2. **Dispatch.** Start the agents named for this round in parallel, one Agent call each, all in one message. Give every agent:
   - the exact scope (files and sections);
   - the round's question;
   - the finding ID prefix;
   - the instruction to stay read-only.

   Split large scopes so that each agent reads whole documents rather than skimming many.
3. **Merge.** When all have returned:
   - de-duplicate (same problem → one finding, credit every agent);
   - **check every blocker and major finding yourself**: open the quoted passages and confirm them, and drop anything you cannot reproduce;
   - rank by severity, then by how many specs it touches.
4. **Write** `docs/reviews/$0.md` with:
   - a summary (counts by severity, the five findings that matter most);
   - the findings table;
   - the full findings;
   - the questions for Thomas;
   - proposed spikes.
5. **Check** that the docs still build: `uvx --with mkdocs-material mkdocs build --strict`. Add the review file to the `nav` in `mkdocs.yml` under "Reviews".
6. **Stop.** Do not change specs in this step. Report the summary and ask Thomas which findings to accept, after which `/apply-findings $0` applies them.
