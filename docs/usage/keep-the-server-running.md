---
icon: material/server
---
# Keeping the server running: `spectio serve --detach`

`spectio serve` stops when you close your terminal. `spectio serve --detach` runs the same server in a tmux session named `spectio-server` on the login node, and prints the sign-in link in the terminal you typed in. The server and its runs then outlive your ssh session.

This page says what you type and see. The sign-in itself is on [Signing in](sign-in.md).

## What you type

```console
$ spectio serve --detach
Spectio 0.0.1 is running on demo-hpc-login1, port 18092.
Open this link in a browser on this machine (single use, valid 15 minutes):
   http://127.0.0.1:18092/auth/link#<ticket>
New link at any time: spectio login --print-link
Spectio never asks you to paste a link.
The server runs in tmux session spectio-server: `tmux attach -t spectio-server` shows it, `tmux kill-session -t spectio-server` stops it.
```

In order:

1. **A server of yours already runs on this node.** `--detach` starts nothing. It asks that server for a new link, prints it, and exits 0. A server started with a plain `spectio serve` counts too.
2. **Otherwise it starts one.** It runs `spectio serve --pane` in a new detached tmux session, under `/usr/bin/env -i` with a short list of variables (below).
3. **It waits for the server** to answer, then prints the link here. The link never appears in the tmux pane, so `tmux attach` shows the log and no ticket.
4. **A second call while the first is still starting** waits for the first server and starts no second one.

## Flags and exit codes

| Flag | Does |
|---|---|
| `--detach` | run the server in the tmux session `spectio-server` and print the link |
| `--wait <seconds>` | with `--detach`: how long to wait for the link. Default 120, from 0 to 3600 |
| `--force` | start here even if `server.json` names a server on another node |

`--wait` without `--detach` exits 2. So does `--no-link`, a hidden flag that `spectio open` uses ([Opening from your laptop](open-from-your-laptop.md)).

| Code | Meaning |
|---|---|
| 0 | a link was printed |
| 2 | refused. Examples: no `tmux` or one older than 2.1; the server package is missing; `server.json` names another node (add `--force` to start here); the port is held by another user; a session named `spectio-server` exists and does not run the server; the server stopped at start, and its own message follows |
| 3 | the server was started but gave no link in time. It is still starting, and the tmux session stays. Run `spectio login --print-link` later |

## What goes into the pane

The server in the pane sees only these variables, passed as words after `env -i`: the launcher's list, `PATH`, `LD_LIBRARY_PATH`, `TMUX_TMPDIR`, `SPECTIO_CONFIG` and the `SPECTIO_*` settings names. The environment of a tmux server that was already running never reaches it. Two consequences:

- **Values are configuration, never secrets.** They show in `ps`. When `--detach` is the call that starts the tmux server itself, they also stay in that server's world-readable `/proc/<pid>/cmdline` while it runs (seen on tmux 3.4).
- **A value that ends in `;` is refused,** because tmux cuts a command there. The message names the variable.

## Stopping and restarting

- **Stop:** `tmux kill-session -t =spectio-server`. tmux sends SIGHUP and the server stops as it does on SIGTERM; `server.json` is removed.
- **Look at the log:** `tmux attach -t spectio-server`.
- **A session whose panes all ended** (a tmux setting such as `remain-on-exit on` keeps it) is replaced: `--detach` removes the dead panes one by one, never the session by name, then starts a new one.

## See it run

The cast runs the real `spectio serve --detach` and a real tmux, in a demo home on the demo host `demo-hpc-login1`, with its own tmux socket. The ticket is masked by a visible `sed`. Steps: `init`, the first `--detach` (link and exit 0), the session list, no link in the pane, a second `--detach` that starts nothing, `--wait` without `--detach` (exit 2), then the stop with `tmux kill-session`.

<div class="asciinema-cast" data-cast="assets/casts/spectio-detach.cast"></div>

## Limits in 0.0.1

- **Checked on tmux 3.4 only,** on one machine. Spectio has not run `--detach` on SLURM or on an EMBL login node yet. Whether the login nodes' tmux is 2.1 or later is **[to be validated]**.
- **Hosts that kill your processes at logout.** On systemd hosts, `KillUserProcesses=yes` can kill a tmux server started from a non-interactive ssh ([logind.conf](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)). Whether the EMBL nodes set it is **[to be validated]**.
- **Run sessions** (`spectio-<run>`) are not protected from `destroy-unattached on` in your `~/.tmux.conf`.
- **A second `--detach` call** prints no hint on how to attach to the session.
