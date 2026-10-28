# Security review · APPLY4, 0.0.1 access on the EMBL cluster

`security-reviewer` on `autopilot/apply-access-tmux-review` at `000ecd7`, 2026-10-28: the design in [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts), [schedulers §3.1.1](../../specs/schedulers-and-monitoring.md) and [P1](../../plans/P1-walking-skeleton.md). There is no product code yet, so every finding becomes one requirement line in the owning spec and named tests in P1. tmux claims cite tmux 3.5a source (`tmux.c:211-227`, `spawn.c:439-459`, `cmd-find.c:263-296` and `:1085`, `server.c:395`). Format: [`README.md`](../README.md).

```text
SECURITY  step=APPLY4  review=changes b/M/m=0/5/5  applied=10/10  rounds=1
```

Trust boundaries, now in §15.3: a pipeline runs as the user and is not a boundary; the boundaries are (i) the cluster towards the laptop through `spectio-open`, (ii) other Unix users on the same login node, (iii) other users who can write a shared runs root.

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-131 | major | `spectio-open` used node, port and PID from `server.json` unchecked; a node such as `-oProxyCommand=x` runs a command on the laptop | applied: §15.3 req. 8; P1 Task 24 `test_rejects_bad_node_from_state_file`, `test_ssh_argv_has_double_dash`; Task 12 checks the node before printing it |
| SEC-132 | major | `spectio-open` opened a URL printed by the remote | applied: req. 8, `spectio login --print-link --json` and a URL built on the laptop; Task 24 `test_url_built_locally`, Task 12 `test_print_link_json` |
| SEC-133 | major | the server key sat in the shared home; files written then `chmod`-ed | applied: key in the node-local directory, `O_CREAT\|O_EXCL` 0600 then rename, `server.json` created with `O_EXCL` as the cross-node lock (§15.3 Where data lives, Server key, req. 5); Task 15 `test_req5_key_not_in_shared_home` and the umask-000 test |
| SEC-134 | major | a taken port made the server pick another; another user's listener could receive the server key | applied: req. 9, fail closed, `spectio init --port`; Task 11 `test_port_taken_refuses`, Task 12 `test_print_link_refuses_foreign_listener` |
| SEC-135 | major | rebuild trusted whatever it found under the runs root | applied: req. 10; Task 11 `test_rebuild_skips_symlinked_foreign_or_loose_dirs`, `test_rebuild_run_id_must_match_dir`, `test_rebuild_ignores_manifest_session_and_paths`, `test_rebuild_caps`, `test_runs_root_loose_refused` |
| SEC-136 | minor | the node-local directory in shared `/tmp` can be squatted | applied: `mkdir` 0700, checks on the opened directory, `mkdtemp` fallback, never tightened (§15.3 Where data lives); Task 2 `test_db_dir_squatted_falls_back`; polyinstantiation and `systemd-tmpfiles` ages at EMBL **[to be validated]** in inbox #64 |
| SEC-137 | minor | tmux targets were prefix matches; the ticket could stay in the pane's scrollback | applied: req. 11, exact `=spectio-<run_id>` targets, pane ID for `send-keys`, separate arguments; the user's default socket and `.tmux.conf` kept as an accepted risk (§15.3 trust boundaries); Task 10 `test_targets_exact_and_pane_id`, `test_argv_never_single_string` |
| SEC-138 | minor | a recycled PID could be signalled | applied: `head.pid` holds process group, start time, boot ID and host, checked again before each signal (req. 11, schedulers §3.1.1); a run on another login node shows so (§15.3); Task 9 `test_cancel_never_signals_other_boot_id`. `pidfd` not required |
| SEC-139 | minor | the tunnel bound the laptop's port on every interface and did not fail on a forward error | applied: req. 8, `-N -o ExitOnForwardFailure=yes -L 127.0.0.1:…`, two-layer quoting; SSH config guide `LocalForward 127.0.0.1:<port> …`; Task 24 `test_tunnel_argv_hardened`, `test_remote_quoting_two_layers` |
| SEC-140 | minor | rebuild ran only on a fresh database; an interrupted rebuild left gaps | applied: reconciliation at every boot and a completion mark (req. 10, §15.3 Where data lives); Task 11 `test_boot_reconciles_missing_runs` |
