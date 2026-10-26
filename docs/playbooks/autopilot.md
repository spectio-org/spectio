# Autopilot — running the whole pipeline without driving each step

Status: v0.1 · 2026-10-26.

The steps in [`next-phase.md`](next-phase.md) are not a to-do list for a person. They are the nodes of a pipeline ([`pipeline.yaml`](pipeline.yaml)) that the `/autopilot` skill runs:
- in parallel where it can;
- verifying each step;
- triaging findings by a written policy ([`triage-policy.md`](triage-policy.md));
- committing as it goes.

Thomas is needed in two places only:
- **the inbox** ([`docs/reviews/inbox.md`](../reviews/inbox.md)), answered whenever convenient: work continues meanwhile on reversible assumptions;
- **the `GO` gate** before product code.

## 1. Why small steps, if nobody runs them by hand

| Reason | Effect |
|---|---|
| Each step has one question and one owner agent | focused context, better findings, less hallucination |
| Each step has an output file and an exit check | the orchestrator can verify instead of trusting a summary |
| Steps declare their dependencies | independent steps run in parallel (wave W1 runs 8 at once) |
| State is in git (`.autopilot/state.json`) | any session can resume: local, cloud, a routine, the headless runner |
| Writers are serialised, builds use worktrees | parallel agents never edit the same files |

The 31 steps collapse into **5 waves**:

| Wave | What runs | Human? |
|---|---|---|
| W1 | 7 review rounds + the cloud-environment spike, all in parallel | no |
| W2 | triage → apply → journeys and API-contract reviews → triage → apply | inbox only |
| W3 | bootstrap / doctor, CI, staging prep, fixture workflows, engine capture, sind, kind + Kueue, scenarios, Playwright | inbox only |
| W4 | synthesis (MVP cut), walking-skeleton plan, **GO** | **yes** |
| W5 | milestone plans, then implementation by subagent-driven development | inbox only |

## 2. The mechanisms underneath

| Layer | Claude Code feature | Role |
|---|---|---|
| One tick | the `/autopilot` skill | read state, run ready steps, verify, triage, commit, print a status line |
| Fan-out inside a step | subagents in parallel; dynamic workflows for large or cross-checked rounds | many reviewers or builders per step, with their results kept out of the orchestrator's context ([workflows](https://code.claude.com/docs/en/workflows.md)) |
| Tick after tick | `/goal` with a completion condition, checked by a separate model after every turn | keeps going without prompts; stops at the condition, or when no progress is made ([goal](https://code.claude.com/docs/en/goal.md)) |
| No per-tool prompts | auto permission mode | a classifier reviews actions ([headless](https://code.claude.com/docs/en/headless.md)) |
| Unattended, machine off | a cloud session, or a routine | keeps running after the laptop closes; a routine can restart a tick nightly ([cloud](https://code.claude.com/docs/en/claude-code-on-the-web.md), [routines](https://code.claude.com/docs/en/routines.md)) |
| Scripted | `claude -p` with stream-json and `--max-budget-usd` | `tools/autopilot/run.sh`, for a VM or CI |

## 3. How to run it

**A. Interactive, on your machine, watching.**

```text
/goal Run /autopilot tick after tick until the latest AUTOPILOT status line shows nothing ready and every remaining step is done, waiting_human or blocked. Stop after 60 turns.
```

Use auto mode (Shift+Tab until "auto"), or answer prompts as they come. `/goal` (no argument) shows progress, and `/goal clear` stops.

**B. In the cloud, laptop closed.**
1. Push the repository and install the Claude GitHub App on it.
2. Open claude.ai/code, pick the repository and the "Spectio" cloud environment (see `docs/specs/dev-environment-and-testing.md` §2), and choose auto mode.
3. Paste the same `/goal` line.
4. Check it from your phone. Answers go in `docs/reviews/inbox.md`, either in a commit or by telling the session.

**C. Headless, on a VM or the staging host.**

```bash
tools/autopilot/run.sh --until W3 --budget-usd 40
```

**D. Nightly continuation (routine).** Create a routine at claude.ai/code/routines, or with `/schedule` in the CLI:
- repository `weber8thomas/spectio`;
- the Spectio environment;
- schedule: daily at 02:07.

The routine's prompt:

```text
Run /autopilot repeatedly (at most 10 ticks) on branch autopilot/integration, then
update the PR to main with the journal. Read docs/reviews/inbox.md first and apply any
answers. Stop early when nothing is ready.
```

**Steering in between:**
- `/autopilot --dry-run` shows what would run next;
- `/autopilot --only R5` runs one step;
- `/autopilot --until W2` stops after a wave;
- setting a `blocked` step back to `pending` in `state.json` retries it.

## 4. Permissions to add yourself

Agents may not change their own permission rules, so add these yourself. You can put them in `.claude/settings.local.json` for your machine only, or commit them to `.claude/settings.json` for every session, including cloud ones:

```json
{
  "permissions": {
    "allow": [
      "Workflow",
      "Bash(git fetch *)", "Bash(git switch *)", "Bash(git checkout *)",
      "Bash(git merge *)", "Bash(git rebase *)", "Bash(git add *)", "Bash(git commit *)",
      "Bash(git push origin autopilot/*)",
      "Bash(bash dev/doctor.sh *)", "Bash(node tools/canvas/render.js *)",
      "Bash(uvx --with mkdocs-material mkdocs build *)"
    ],
    "deny": [
      "Bash(git push --force *)", "Bash(git push -f *)", "Bash(git push origin main *)",
      "Bash(git branch -D *)"
    ]
  }
}
```

`Workflow` lets dynamic workflows start without a prompt in `-p` and in scheduled runs ([workflows: approve the plan](https://code.claude.com/docs/en/workflows.md)).

Protect `main` with a GitHub branch rule that requires a PR and a review. The autopilot only pushes `autopilot/*` branches and opens PRs.

## 5. Budget and safety

- **Cost.** Each tick fans out several agents; W1 alone starts about 15 to 25 agents. Bound a run with `--max-budget-usd` (headless), a turn clause in the `/goal` condition, or `--until <wave>`. Dynamic workflows show a "Large workflow" warning above 25 agents. Start with `--until W1` to see the real cost of one wave.
- **Reversibility.** Every change is a commit on `autopilot/integration`, and every triage decision is in the review file and the journal. Assumptions are labelled in the specs.
- **No silent weakening.** The orchestrator may not edit exit checks or statuses in `pipeline.yaml`, and it never merges to `main`.
- **Failures.** A step that fails twice becomes `blocked`, with an inbox entry. Two ticks without progress make `/goal` judge the condition impossible, and the run stops.
