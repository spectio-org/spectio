---
step: APPLY4
wave: W4
status: done
pr: null
review: approve
review_score: 12/14
review_ref: "doc-reviewer 2026-10-28, approve 12/14 on 000ecd7, required changes applied; security review: docs/reviews/code/APPLY4.md"
---
# APPLY4 · Apply Thomas's 2026-10-28 answers on cluster access

!!! success "Done 2026-10-28 · PR #47 and its fix branch `autopilot/apply-access-tmux-review` · SSE kept (decided) · SQLite a rebuildable index (assumed, inbox #64) · laptop tool `spectio-open` · security review: 10 findings, all applied as §15.3 requirements 8–11 · doc review approve 12/14, changes applied"

![APPLY4 figure, before and after, in four rows. Engine head: before, an sbatch head job on a compute node, cancelled with scancel; after, a tmux session on the login node, the head in the pane's foreground, cancelled with Ctrl-C then SIGTERM and SIGKILL, and tmux attach to take over. Laptop access: before, an ssh -L tunnel typed by hand to the right login node and port; after, spectio-open with an optional login node, which reads ~/.spectio/server.json, or an SSH config entry with LocalForward. Database: before, SQLite as the source of truth on a persistent node-local disk that may not exist at EMBL; after, SQLite as an index in a node-local temporary directory, rebuilt at boot from the shared run directories, assumed pending inbox #64. Live refresh: before, the UI polls every 5 seconds; after, one SSE stream per browser, decided by Thomas](../../assets/diagrams/apply4_access_light.png#only-light)
![APPLY4 figure, before and after, in four rows. Engine head: before, an sbatch head job on a compute node, cancelled with scancel; after, a tmux session on the login node, the head in the pane's foreground, cancelled with Ctrl-C then SIGTERM and SIGKILL, and tmux attach to take over. Laptop access: before, an ssh -L tunnel typed by hand to the right login node and port; after, spectio-open with an optional login node, which reads ~/.spectio/server.json, or an SSH config entry with LocalForward. Database: before, SQLite as the source of truth on a persistent node-local disk that may not exist at EMBL; after, SQLite as an index in a node-local temporary directory, rebuilt at boot from the shared run directories, assumed pending inbox #64. Live refresh: before, the UI polls every 5 seconds; after, one SSE stream per browser, decided by Thomas](../../assets/diagrams/apply4_access_dark.png#only-dark)

*Left: the plan and the specs on `main` at `6bf2fec`, before PR #47. Right: after PR #47 and the fixes of its doc review. Sources are named under the figure.*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml): Thomas answered questions about 0.0.1 at the GO gate, and the answers were applied in two parts.

## What changed

**Part 1, PR #47** (squash `f51dca9`, 2026-10-28). Thomas's answers: 0.0.1 targets the EMBL cluster only; its login nodes have no time limit and tmux installed; the engine head runs in a tmux session on the login node, never in `sbatch`; laptop access through an SSH config entry and a small laptop tool, side by side. Applied to:

- [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Launch, Access, the state file `~/.spectio/server.json`, Prerequisites at EMBL) and §15.1;
- [schedulers §3.1.1](../../specs/schedulers-and-monitoring.md) (the tmux launcher) and its dated note in schedulers §3.1;
- [`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md) §1;
- [P1](../../plans/P1-walking-skeleton.md): Task 10 became the tmux launcher, and a new Task 24 covers laptop access (24 tasks);
- inbox #64 (where SQLite goes at EMBL), and the decision-log entry [head in tmux on the login node](../../decisions/log.md#2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open);
- the figures `mvp001_cluster` and `p1_skeleton`, redrawn.

**Part 2, the doc review of PR #47** (changes, 9/14), plus two answers from Thomas the same evening:

- **Live refresh over SSE, decided** (Thomas). It is recorded in [api §8.3](../../specs/api-and-data-model.md) (dated note), [ui-spec §7](../../specs/ui-spec.md), `mvp-0.0.1.md` §1, dev-env §15.3 req. 3 and §15.1. P1 Assumption 7 now plans one stream, `GET /api/v1/events/stream`, with tests in Tasks 18 and 20.
- **SQLite as a rebuildable index** *(assumed — pending Thomas, inbox #64)*. At EMBL everything but some temporary directories is shared (Thomas). The database goes in `<node-local tmp>/spectio-<uid>/`, 0700, and the run directories hold the truth (`.spectio/run.json`, the spool, `head.pid`, `head.exit`). The server rebuilds the index at boot when it is missing. Recorded in dev-env §15.3 (Where data lives, Server restart, the diagram), [architecture §7.2 and §7.3](../../specs/architecture-plugins-and-packaging.md) (dated notes), inbox #64 (new option (d)), P1 Assumption 21 and Tasks 2, 8, 9 and 11 (`test_rebuild_from_run_dirs`).
- **The review's required changes:**

| # | Review finding | Fix |
|---|---|---|
| 1 | P1 Task 20 still described a head job | Task 20 shows the tmux session, alive or exited, login node, exit code, and a confirm text without "head job"; Task 18's field is `head: {session, node, alive, exit_code}`; Task 20 is in the log entry's Changed list |
| 2 | two names for the laptop tool | `spectio-open` everywhere: §15.3, `mvp-0.0.1.md` §1, the log, P1 Goal, M5, Task 24, both figures; the log entry keeps its heading so links stay valid, with a dated note |
| 3 | unattended `spectio init` against the network-file-system rule | the database defaults to a node-local temporary directory (Part 2); P1 Task 8 `test_init_defaults_unattended` |
| 4 | `--print-link` from another login node | it reads the state file, prints `ssh <node> spectio login --print-link` and exits 2 (§15.3, P1 Assumption 9); P1 Task 12 `test_print_link_on_other_node` |
| 5 | [Progress · P1](P1.md) alt text said `sbatch`, and 23 tasks | alt text rewritten for the redrawn figure, with a dated note on the revision |
| 6 | no Progress page for the apply | this page, its figure (`tools/diagrams/apply4_access.py`, registered in `docs/assets/media.yaml`), a link from the [Progress index](../index.md), a journal line |
| 7 | `packages/spectio-open` missing from the layout | [architecture §6](../../specs/architecture-plugins-and-packaging.md#6-code-layout) tree and P1 Global Constraints; Task 24 lists the §6 row under Modify |

- **The review's optional changes:**
    - 8: the EMBL callout of `mvp001_cluster` sits in the login-node box, and the cancel text of `p1_skeleton` sits under the head pane.
    - 9: the §15.3 mermaid diagram gains the `spectio-server` session and a person attaching.
    - 10: in schedulers §3.1.1 and P1 Task 10, only the tmux server is detached. The head runs in the pane's foreground without `setsid`, so a Ctrl-C reaches the engine. The cgroup claim is now **[to be validated]**.
    - 11: P1 Assumption 13 says that the head script starts the engine with a cleared, allow-listed environment and then the login shell, as the `--export=NONE` head job did before. Nothing from the server reaches the engine (Task 9 `test_head_env_cleared`). The security posture is unchanged.
    - 12: P1 Task 23 cites the dev-env §4.1 note.
    - 13: `mvp-0.0.1.md` §1 shows `[--node <login node>]` as optional.
    - 14: schedulers §3.1.1 links to dev-env §15.3 instead of restating the EMBL facts.
**Part 3, the reviews of the fix branch** (`000ecd7`):

- **Doc review**, approve 12/14. Inbox #15 now says `spectio-open`. The rebuild keeps cancels and launch failures: the runner writes `.spectio/cancel` before the interrupt and `.spectio/launch-failed.json` when a launch fails, the manifest is written when the run is created, and a run never launched ends `failed` (`launch_error`). `test_rebuild_from_run_dirs` now covers a cancelled run and a failed launch. Optional changes applied: the SSE frame is a strict subset of api §8.5, the api §8.3 note sits after its "Why", a dated note in architecture §7.2 keeps the runs root outside `<data-dir>`, the P1 alt text matches the figure, and the M2 badge of `p1_skeleton` moved up.
- **Security review**, changes: 0 blockers, 5 majors, 5 minors, all applied ([record](../../reviews/code/APPLY4.md)). [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) gains a trust-boundaries paragraph, a stricter req. 5 and requirements 8–11: values from the cluster are checked and the link is built on the laptop; the port is fixed and fails closed; run directories are untrusted at rebuild; tmux targets are exact and signals re-check the PID file. The server key moved to the node-local directory. P1 names a test for each (Tasks 2, 9–12, 15, 17 and 24).

- **Decision log:** a new entry, [live refresh over SSE; SQLite as a rebuildable index](../../decisions/log.md#2026-10-28-001-live-refresh-over-sse-sqlite-as-a-rebuildable-index); the earlier entry gains the name note, the `--print-link` behaviour and the review's Changed list.

## Why

PR #47 was merged before its independent doc review ran: the fork that applied it could not spawn agents. That review found the plan still carried head-job wording, two names for one laptop tool, and a first start that could not run unattended, because the default data directory broke the network-file-system rule. Thomas's answer on EMBL's shared login nodes settles the third problem: when the database is a rebuildable index, it can live in a temporary directory and be lost without losing a run.

## Evidence

- **Docs gate**, `python3 tools/docs/check.py` on this branch:

    ```text
    mermaid: 5 blocks checked
    diagrams: 26 scripts re-run, 52 SVGs compared
    media: 126 outputs in the manifest
    progress: 39 pages checked
    docs gate: 0 failure(s)
    ```

- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0. Both decision-log anchors linked from the specs exist in the built page: `2026-10-28-001-live-refresh-over-sse-sqlite-as-a-rebuildable-index` and `2026-10-28-001-head-in-tmux-on-the-login-node-ssh-config-and-spectio-open`.
- **Mermaid:** the §15.3 diagram renders with `npx -y @mermaid-js/mermaid-cli@11`.
- **One name:** `grep -rln 'spectio open' docs/ tools/diagrams/ --exclude=APPLY4.md` prints only the kept heading's file and the docstring that quotes it:

    ```text
    docs/decisions/log.md
    tools/diagrams/mvp001_cluster.py
    ```

- **Before:** `git show 6bf2fec:docs/plans/P1-walking-skeleton.md` (Assumption 7 "No SSE in 0.0.1", the head job). **After:** `git diff 6bf2fec -- docs/specs docs/plans docs/decisions docs/reviews/inbox.md`.

## Figures and media

- `apply4_access` (above), new: [`tools/diagrams/apply4_access.py`](https://github.com/weber8thomas/spectio/blob/main/tools/diagrams/apply4_access.py), entry `apply4-access` in `docs/assets/media.yaml`.
- `mvp001_cluster`, redrawn for `spectio-open`, the EMBL callout and the rebuildable index; shown in [`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md).
- `p1_skeleton`, redrawn for the tmux head, SSE, the index and the cancel text; shown on the [P1 plan](../../plans/P1-walking-skeleton.md) and [Progress · P1](P1.md).
- Each was rendered light and dark with `tools/diagrams`, and each PNG was opened and checked for overlaps. No screenshot or cast: nothing in this step runs.

## Findings and open questions

- **Inbox #64** stays open: option (d), the rebuildable index, is assumed. **[to be validated]**: which temporary directory is node-local on the EMBL login nodes and how often it is purged, whether `/tmp` is polyinstantiated per user, and the `systemd-tmpfiles` ages; the real-cluster checks of P1 Tasks 8 and 24 confirm them.
- **Accepted risk:** the user's own `~/.tmux.conf` can weaken or break the tmux sessions; 0.0.1 keeps the default tmux socket (§15.3 trust boundaries, SEC-137).
- **Still [to be validated]** in schedulers §3.1.1: whether the tmux server stays in the cgroup of `spectio serve`, and whether EMBL kills a user's processes at logout.
- **Review findings:** SEC-131 to SEC-140, all applied ([record](../../reviews/code/APPLY4.md)); the doc review's required changes, all applied (Part 3).
