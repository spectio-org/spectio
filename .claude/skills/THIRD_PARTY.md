# Vendored skills

These skills are copied unchanged from upstream so that they also work in Claude Code cloud sessions, which do not load plugins enabled in `.claude/settings.json`.

| Skills | Upstream | Commit | Licence |
|---|---|---|---|
| brainstorming, writing-plans, executing-plans, subagent-driven-development, test-driven-development, systematic-debugging, verification-before-completion, requesting-code-review, receiving-code-review, using-git-worktrees, dispatching-parallel-agents, finishing-a-development-branch, writing-skills | [obra/superpowers](https://github.com/obra/superpowers) | `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b` | MIT, © 2025 Jesse Vincent |
| karpathy-guidelines | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | `2c606141936f1eeef17fa3043a72095b4765b9c2` | MIT |

**Updating.** Re-copy the directories from a newer upstream commit, update the commit column, and review the diff before committing.

**Local alternative.** In local sessions you can use the plugins instead of these copies:
- `/plugin install superpowers@claude-plugins-official`
- `/plugin marketplace add forrestchang/andrej-karpathy-skills`, then `/plugin install andrej-karpathy-skills@karpathy-skills`

If you do, delete the vendored copies to avoid running two versions.

**Naming.** Upstream text refers to skills as `superpowers:<skill>`, the plugin namespace. In this repository the same skill is the vendored `<skill>`: for example `superpowers:writing-plans` is `/writing-plans`.
