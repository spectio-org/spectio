---
icon: material/laptop
---
# Opening Spectio from your laptop

!!! note "Built on the integration branch, not released yet"

    `spectio open` runs today from a checkout (batch [P3-B02](../progress/W5/P3-M5.md#task-24-laptop-access-the-ssh-config-entry-and-spectio-open), 2026-11-07). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **It has not run against a real `sshd` or a login node yet:** the cast below uses a fake `ssh`, and the by-hand check on an EMBL login node is open ([Not built or not checked](#not-built-or-not-checked)).

Spectio's server listens on `127.0.0.1` of a cluster login node. You reach it from your laptop through an SSH tunnel, with a one-time link. Two ways ship side by side. Both call your own `ssh`, so your `~/.ssh/config`, keys, `ProxyJump` and second factor work as they do today.

The rules are owned by [development environment §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) (Access, and requirement 8). This page says what you type and see.

| | SSH config entry | `spectio open <host>` |
|---|---|---|
| Installed on the laptop | nothing | the `spectio` package, with `uv tool install spectio` or `pipx` |
| Tunnel | opened by `ssh <host>`, on a port fixed in the entry | opened for you, on a free local port |
| Link | you copy it from the cluster | built on the laptop, opened in the browser |
| First start of the server | you start it | it starts it (`spectio serve --detach`, [built](keep-the-server-running.md)) |
| Server on another login node | you change `HostName` | it reads `~/.spectio/server.json` and follows it |

## Way 1: the SSH config entry

1. **Find the port.** `spectio init` on the cluster picked a free port once and recorded it in `~/.spectio/spectio.toml` (`port = 8080` by default; another one when 8080 is taken). Read it there. The entry stays valid because the port does not change.
2. **Add a `Host` block** to `~/.ssh/config` on the laptop, with the login node the server runs on:

    ```text
    Host demo-hpc
        HostName demo-hpc-login1
        User alice
        LocalForward 127.0.0.1:8080 127.0.0.1:8080
    ```

3. **Connect** with `ssh demo-hpc`. The tunnel lasts as long as the session.
4. **Start the server** in that session if none runs: `spectio serve --detach` keeps it in a tmux session `spectio-server` and prints the link ([Keeping the server running](keep-the-server-running.md)). It was not run on a cluster here, **[to be validated]**.
5. **Open the link** that `spectio serve` prints, or a new one from `spectio login --print-link`, in the laptop's browser.

If the server runs on another login node, `spectio serve` names it. Point `HostName` at that node.

## Way 2: `spectio open`

```console
$ spectio open demo-hpc
Spectio on demo-hpc-login1: http://127.0.0.1:18090/auth/link#<ticket>
Ctrl-C closes the tunnel.
```

In order:

1. It runs `spectio --help` on the cluster and reads `~/.spectio/server.json`, over `ssh demo-hpc`, through your login shell (`"$SHELL" -lc`), so `PATH`, modules and your rc files apply.
2. With a state file, it reaches the node the file names. `--node` overrides it.
3. Without one, it starts a server on `--node`, else the `node` of `clusters.toml`, else `<host>`: `spectio init` only if `~/.spectio` is missing, then `spectio serve --detach --no-link`, so no link lands in the ssh output. If that exits 3 (started, no link yet), it asks for the ticket again every 2 s for up to 120 s. The real `--detach` was run on tmux 3.4 (see [Keeping the server running](keep-the-server-running.md)); the whole path through `spectio open` still runs against a fake remote `spectio` in the tests only.
4. It opens the tunnel on a free local port (`--local-port` sets one), asks the node for a ticket with `spectio login --print-link --json`, builds the link itself and opens your browser. A URL printed by the cluster is never opened.
5. Ctrl-C closes the tunnel. The server and its runs keep going.

| Flag | Does |
|---|---|
| `--node <node>` | the login node, for a first start or to override the state file |
| `--remote-cmd <cmd>` | shell text run instead of `spectio`, such as `module load spectio && spectio` |
| `--local-port <n>` | the local end of the tunnel |
| `--no-browser` | print the link and open nothing |

### Per-cluster settings

`~/.config/spectio/clusters.toml` on the laptop holds one table per host. Two keys only; any other key is refused, and so is a file that others can write. A flag wins over the file.

```toml
[demo-hpc]
node = "demo-hpc-login1"
remote_cmd = "module load spectio && spectio"
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | the browser was opened and the tunnel has ended |
| 2 | `spectio` is not installed on the cluster: the install line is printed, nothing is installed |
| 3 | any other failure: `ssh`, a remote command, or a value from the cluster that fails the checks |

### What it checks before it uses a value from the cluster

- a node is a host name (`^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$`), a port is 1024 to 65535, a PID is an integer, a ticket is 43 characters of `A-Za-z0-9_-`;
- `--` comes before every `ssh` destination, and no cluster value goes inside `-o`;
- the tunnel is `-N -o ExitOnForwardFailure=yes -L 127.0.0.1:<local>:127.0.0.1:<port>`, with no host-key option.

## See it run

The cast runs the real `spectio open` and a real `spectio serve` in a demo home on the demo host `demo-hpc-login1`. The `ssh` is the fake of the tests: it runs the remote commands in a shared home of its own and listens on the tunnel's local port, but forwards nothing, so the cast runs with `--no-browser`. The ticket is masked by a visible `sed`. Steps: the server on the node, `spectio open`, the three `ssh` calls it made, then the missing remote `spectio` (exit 2).

<div class="asciinema-cast" data-cast="assets/casts/spectio-open.cast"></div>

## Not built or not checked

- **A real `sshd` and a login node.** [P1 Task 24](../plans/P1-walking-skeleton.md#task-24-laptop-access-the-ssh-config-entry-and-spectio-open) Step 4 is by hand, once, on an EMBL login node, and is not done. Whether `"$SHELL" -lc` works there, and which login shell the nodes use, is **[to be validated]**. The remote scripts need a POSIX-family shell; a tcsh login shell fails with a syntax error.
- **A first start through `spectio open` on a real login node.** `spectio serve --detach` is built (FU-P3-44), but the path from `spectio open` to it was not run over a real `sshd`, on SLURM or at EMBL.
- **Is the server in `server.json` alive?** Not checked. After a crash or a node reboot a stale file makes the login fail, and the error names the file as a possible cause: remove it and run `spectio open` again (FU-P3-48).
- **Ctrl-C** during the wait for a second factor exits 0, not 3; the remote calls read the laptop's stdin; a local process listening on the chosen port before `ssh` binds it would receive the link (needs a hostile process on the laptop). All in FU-P3-48, with the [security review](../reviews/code/P3-t24.md#security-review-after-the-workflow-2026-11-07).
- **The ticket** goes to the browser's command line and is echoed in the terminal. It is single use.
