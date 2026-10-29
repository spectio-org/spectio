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

![One autopilot tick: ready batch, parallel workers, exit check, doc writer, doc reviewer, strict build, PR, checks, auto-merge; with the budget governor and the inbox](../assets/diagrams/autopilot-loop_light.png#only-light)
![One autopilot tick](../assets/diagrams/autopilot-loop_dark.png#only-dark)

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
| W3 | bootstrap / doctor, CI, dev previews, fixture workflows, engine capture, sind, kind + Kueue, scenarios, Playwright | inbox only |
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
| Dashboard | a private claude.ai artifact with a `db` collection | at the start of a tick, answers typed on the page are copied into `docs/reviews/inbox.md` (skill §0, step 3); at the end, the page is rebuilt and republished (skill §5). Interactive and cloud ticks only, not `run.sh`. Build, permissions and data exposure: `tools/dashboard/README.md` |

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
4. Check it from your phone. Answers go in `docs/reviews/inbox.md`, in a commit, by telling the session, or on the dashboard (below).

**Answering on the dashboard.** In the dashboard's Decisions view, the owner can answer an open, assumed or partial entry: accept the recommendation, or type an answer. The page applies nothing. The next interactive or cloud tick copies the answer into the entry as `Answer (Thomas, <time>, dashboard)`, and the entry stays open. Until you confirm it in a session message or a commit, the answer counts as an assumed default: the autopilot may go ahead with it only when it picks one of the entry's own options. "Withdraw" on the page works only until the tick has copied the answer; after that, tell the session. An answer typed there only chooses among the entry's options. A human gate (`GO`), a merge, a permission or configuration change, or an edit to `CLAUDE.md`, a skill or a `pipeline.yaml` status still needs a session message or a commit (skill §0, step 3).

**C. Headless, on any machine with Claude Code signed in (a laptop, or a codespace).**

```bash
tools/autopilot/run.sh --weekly 30                # at most 30 points of the weekly window
tools/autopilot/run.sh --until-exhausted          # the rest of the 5-hour window, stop when it resets
tools/autopilot/run.sh --until W3 --tick-usd 15   # no plan budget: a USD cap per tick only
```

Each tick is a separate `claude -p "/autopilot …"`; the shell loop checks the budget before every tick (§6).

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

Agents may not change their own permission rules, so add these yourself. You can put them in `.claude/settings.local.json` for your machine only, or commit them to `.claude/settings.json` for every session, including cloud ones. A complete file, merged with the current settings, is in `tools/autopilot/claude-settings.json` (`cp tools/autopilot/claude-settings.json .claude/settings.json`). It does not deny `git push origin main`, since Claude may merge into `main` for now (inbox #3). The pieces:

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
      "Bash(git branch -D *)",
      "Bash(gh workflow run *)", "Bash(gh api *pending_deployments*)",
      "Bash(gh api *dispatches*)", "Bash(gh run rerun *)", "mcp__github__actions_run_trigger"
    ]
  }
}
```

The last five rules keep agent sessions from starting, re-running or approving any workflow run, and so a PyPI publish ([inbox #71](../reviews/inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish), option (a), Thomas, 2026-10-29). The GitHub MCP tool `mcp__github__actions_run_trigger` is denied whole because it can start and re-run any workflow. The autopilot can no longer re-run a failed CI job: Thomas does it. The Bash rules match command text, so another spelling can get past them.

For the budget governor (§6), also add the status-line tap and the limit hook:

```json
{
  "statusLine": {"type": "command", "command": "python3 tools/autopilot/statusline.py", "refreshInterval": 60},
  "hooks": {
    "StopFailure": [{"matcher": "rate_limit", "hooks": [{"type": "command", "command": "python3 tools/autopilot/budget.py limit-hit --reason rate_limit"}]}]
  }
}
```

`Workflow` lets dynamic workflows start without a prompt in `-p` and in scheduled runs ([workflows: approve the plan](https://code.claude.com/docs/en/workflows.md)).

**Context compaction.** Thresholds are in tokens ([model config](https://code.claude.com/docs/en/model-config), [subagents](https://code.claude.com/docs/en/sub-agents)):
- the orchestrator and every agent without its own value compact at **400k** (`autoCompactWindow` in `.claude/settings.json`). Its state lives in git, so a compaction loses only reasoning;
- the reviewers that read whole specs or many sources (`spec-reviewer`, `fact-checker`, `constraints-hunter`, `security-reviewer`, `depictio-liaison`) get **600k** (`autoCompactWindow` in their frontmatter), so their evidence is not summarised away mid-round;
- the reviewers that read one diff or a few pages (`doc-reviewer`, and `code-reviewer` and `code-simplifier` once added) get **200k**.

Do not set `CLAUDE_CODE_AUTO_COMPACT_WINDOW` for autopilot runs: it overrides the agents' own values. Two points are **[to be validated]**: the frontmatter field needs Claude Code v2.1.296 or later, and a value above the model's context window should mean compaction at that window.

Protect `main` with a GitHub branch rule that requires a PR and a review. The autopilot only pushes `autopilot/*` branches and opens PRs.

## 5. Budget and safety

- **Cost.** Each tick fans out several agents; W1 alone starts about 15 to 25 agents. Bound a run with `--max-budget-usd` (headless), a turn clause in the `/goal` condition, or `--until <wave>`. Dynamic workflows show a "Large workflow" warning above 25 agents. Start with `--until W1` to see the real cost of one wave.
- **Reversibility.** Every change is a commit on `autopilot/integration`, and every triage decision is in the review file and the journal. Assumptions are labelled in the specs.
- **No silent weakening.** The orchestrator may not edit exit checks or statuses in `pipeline.yaml`, and it merges into `main` only through the promotion PR, once every check passed (allowed by Thomas for now, inbox #3).
- **Failures.** A step that fails twice becomes `blocked`, with an inbox entry. Two ticks without progress make `/goal` judge the condition impossible, and the run stops.

## 6. Budget governor: a share of the weekly window, or until the quota runs out

Spectio is a side project, so the autopilot spends only what Thomas gives it. How it was built and tested: [F7](../progress/W0/F7.md). The budget is set when a run starts, at any time of the week:

| You say | Command | What happens |
|---|---|---|
| "use 30 % of my week" | `run.sh --weekly 30`, or `/autopilot --budget 30%w` | at most 30 percentage points of the weekly window, counted from now; if the 5-hour window fills first, the loop waits for its reset and continues |
| "use 40 % of this 5-hour window" | `run.sh --five-hour 40` | the same, on the 5-hour window |
| "eat the rest of my quota" (Wednesday 11:00, window resets 15:00) | `run.sh --until-exhausted` | runs until the 5-hour window is used up, and stops when it resets at 15:00 at the latest |
| "the rest of my week, but stop at 18:00" | `run.sh --until-exhausted --window seven_day --deadline 18:00` | runs until the weekly window is used up or 18:00 |

**Where the numbers come from** (sources: `docs/research/budget-and-telemetry-2026-10-26.md` §A1):
- Claude Code exposes plan usage only to the **status line**: `rate_limits.five_hour` and `seven_day`, each with `used_percentage` and `resets_at`, for Pro and Max subscribers, after the first answer of a session.
- `tools/autopilot/statusline.py` writes them to `.autopilot/usage.json` (the readings are account-wide, so other use of the plan during the run counts too).
- No environment variable, CLI command, hook input or OpenTelemetry metric reports the remaining quota.
- Headless ticks (`claude -p`) have no status line. The governor then estimates: the last live reading plus the USD reported by each tick (`total_cost_usd`) times a percent-per-USD ratio. The ratio is calibrated from live readings (median of the last 20 samples), or given with `--pct-per-usd`.
- With no reading at all, say where you are: `--now 42`, read from `/usage`.
- Not to be confused: `.autopilot/usage.json` holds these rate-limit readings and is gitignored; `.autopilot/usage/` holds each session's committed token counts for the dashboard (`tools/dashboard/README.md`).

**The rules** (`tools/autopilot/budget.py`, tested in `test_budget.py`):
1. **Points, not levels.** The budget counts points consumed since the start, summed over readings, so a weekly reset during the run does not reset the budget.
2. **A batch is sized to fit.** Before each tick, `budget.py check --kinds <kinds of the ready batch>` estimates each step from the median cost of past steps of the same kind, and returns how many fit under the remaining budget minus a margin. The margin is the larger of 2 points and the largest step estimate. The tick runs with `--max-parallel` set to that number.
3. **Wait, or stop.**
   - When the 5-hour window is full but the weekly budget is not, the loop sleeps until `resets_at` + 2 min.
   - It stops when the budget is used, the deadline passes, a plan limit is hit, nothing is ready, or two ticks finish no step.
4. **Limits are detected, throttles are not counted.** The `StopFailure` hook with matcher `rate_limit`, or a stream `api_retry` with error `rate_limit` after the last retry, writes `.autopilot/limit-hit.json`. A capacity throttle ("not your usage limit") is retried and does not count.
5. **A step stopped by a limit does not use up a retry.** It is set back to `pending` with the note `limit`.
6. **Visible.** The AUTOPILOT status line ends with `budget=12.4/30pt 7d (live, window 52%)`.

**Interactive runs (`/goal` or `/loop`).**
- The tick runs `budget.py check` itself before dispatching (skill §1).
- Auto-continue at the usage limit covers only waits under 24 hours, and at most two of them. It never covers the weekly limit, and it does not apply to Remote Control.
- The weekly budget is therefore always enforced by the governor, not by waiting.

**[to be validated]**
- whether the status line runs in cloud sessions;
- the exact payload of `claude -p` when the plan limit is hit, including any `rate_limit_event` message. `budget.py ingest-stream` reads it when present.

## 7. Docs in the loop

Every step leaves its pages (`docs/specs/documentation-system.md` §3). The pages so far are under [Progress](../progress/index.md); the foundations wave W0 is [F1](../progress/W0/F1.md) to [F7](../progress/W0/F7.md).

**During the step:**
- `doc-writer` keeps the step's Progress page (`docs/progress/<wave>/<step>.md`) up to date;
- `diagram-artist` and `media-capture` produce the figures and media the step kind requires.

**After the exit check:**
- the tick runs the docs gate (`documentation-system.md` §3.3);
- `doc-reviewer` scores the pages with a fresh context.

**Outcome:**
- `changes` sends the step back to `doc-writer`, at most twice, then the step is `blocked`;
- `approve` lets the step reach `done`, and its PR body is generated from the Progress page;
- the tick appends the `doc-reviewer` verdict line, with its score out of 14, to `.autopilot/journal.md`, and the Progress page records `review_score` and `review_ref` ([documentation-system §3.3](../specs/documentation-system.md#33-the-docs-gate-run-by-autopilot-after-every-step-and-by-ci-on-every-pr) item 6). *(assumed — pending Thomas, inbox #30)*

## 8. Pull requests and auto-merge

**One PR per step**, from `autopilot/<step-id>` into `autopilot/integration`, and a running promotion PR `autopilot/integration → main`.

**When a PR merges by itself** (`documentation-system.md` §8): bodies carry the docs, figures and media, and GitHub's native auto-merge merges them once:
- the required checks pass;
- the `doc-reviewer` review approves.

**Where auto-merge applies.**
- PRs into `autopilot/integration` always auto-merge.
- The promotion PR to `main` is merged by the autopilot (merge commit) once every check passed and doc-reviewer approved: Thomas allowed it for now (inbox #3, 2026-10-26). Without that permission, it auto-merges only when the repository variable `AUTOMERGE_MAIN=true`.

**Never auto-merged:** `human_gate` steps, the release PR, and changes to workflows, settings, auth code or `pipeline.yaml`.

**One-time setup, done by Thomas.** Agents cannot change repository settings:

```bash
gh repo edit weber8thomas/spectio --enable-auto-merge --delete-branch-on-merge
for b in main autopilot/integration; do
  gh api -X PUT "repos/weber8thomas/spectio/branches/$b/protection" --input - <<'JSON'
{"required_status_checks": {"strict": true, "contexts": ["ci-ok", "docs-gate", "pr-body"]},
 "enforce_admins": false,
 "required_pull_request_reviews": {"required_approving_review_count": 1, "require_code_owner_reviews": true},
 "restrictions": null, "allow_force_pushes": false, "allow_deletions": false}
JSON
done
gh variable set AUTOMERGE_MAIN --body false   # set to true to let CI merge into main
```

**Required checks and code owners** (D4, decided by Thomas in inbox #26, 2026-10-27).
- **Three required checks:** `ci-ok`, `docs-gate` and `pr-body`. `ci-ok` is the aggregate job of `ci.yml` and stands for the security checks and the pipeline matrix ([`dev-environment-and-testing.md` §11](../specs/dev-environment-and-testing.md#11-ci-workflows)). The pipeline legs are no longer listed: they run only when their paths changed, and a required check that never reports blocks the PR for ever.
- **`require_code_owner_reviews`** makes `.github/CODEOWNERS` binding. A PR that touches workflows, `.claude/`, `pipeline.yaml`, the autopilot, the scanners' exception files or auth code needs Thomas's approval. Without it, a PR could switch off its own security gate, for example by editing `tools/ci/security.sh`.
- **Open point.** GitHub does not let an author approve their own PR. If the autopilot opens PRs under Thomas's account, those PRs can merge only through an admin bypass, which `"enforce_admins": false` keeps possible. A separate identity for the autopilot would allow `"enforce_admins": true` **[to be validated: which identity the autopilot pushes with]**.

## 9. Code review in the loop

Every step that changes code, a `build` step or a spike whose code a later step reuses, goes through the `review-code` (`.claude/skills/review-code/SKILL.md`) skill. It runs after the exit check and before the docs (§7).

1. **`code-reviewer`** reads only the step's prompt, the owning spec, the diff `base..HEAD` and the worker's report. It checks requirement fit, correctness, tests, and the Karpathy guidelines: simplicity first, surgical changes. It returns `approve`, `changes` or `block`. In parallel, **`security-reviewer`** reviews the same diff for every step, whatever it touches (Thomas, 2026-10-27); a step is done only when both approve, and security blockers and majors are always fixed.
2. **Fix loop.** On `changes`, the worker that built the step fixes the blockers and majors in its worktree. After two rounds the step is `blocked`, with an inbox entry.
3. **`code-simplifier`** then shrinks the step's own diff without changing behaviour, re-running the step's tests. A failed simplification is reverted and never blocks the step.

The step's `base` commit is recorded in `state.json` when it starts. Findings go to `docs/reviews/code/<step>.md` (prefix `CR-`), and the `CODE` report line goes into the Progress page. In W5, subagent-driven-development already reviews each task. The task reviewer gets the Karpathy guidelines as global constraints, and `review-code` runs once on the whole branch before it is finished (P3 in [`next-phase.md`](next-phase.md)).
