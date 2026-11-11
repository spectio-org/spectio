---
icon: material/laptop
---
# Opening Spectio from your laptop

On a cluster login node, Spectio's server listens on a Unix socket in its private database directory (`/tmp/spectio-<uid>/spectio.sock` by default), never on a TCP port: on a login node other users can reach any `127.0.0.1` port, but not a socket in a directory only you can open ([why](#why-a-socket-on-a-cluster)). You reach it from your laptop through an SSH tunnel from a port of your laptop to that socket, with a one-time link. Two ways ship side by side. Both call your own `ssh`, so your `~/.ssh/config`, keys, `ProxyJump` and second factor work as they do today.

This page says what you type and see.

| | SSH config entry | `spectio open <host>` |
|---|---|---|
| Installed on the laptop | nothing | the `spectio` package, with `uv tool install spectio` or `pipx` |
| Tunnel | opened by `ssh <host>`, on a port fixed in the entry | opened for you, on a free local port |
| Link | you copy it from the cluster | built on the laptop, opened in the browser |
| First start of the server | you start it | it starts it (`spectio serve --detach`, [details](keep-the-server-running.md)) |
| Server on another login node | you change `HostName` | it reads `~/.spectio/server.json` and follows it |

## Way 1: the SSH config entry

1. **Find the socket and the port.** `spectio serve` prints both in its tunnel line: `ssh -N -L 127.0.0.1:8080:/tmp/spectio-1000/spectio.sock alice@demo-hpc-login1`. The socket is `spectio.sock` in the database directory (`/tmp/spectio-<uid>` by default, or the `db_dir` of `~/.spectio/server.json`). The port is the laptop's end: `port` in `~/.spectio/spectio.toml` (8080 by default), which also names the link.
2. **Add a `Host` block** to `~/.ssh/config` on the laptop, with the login node the server runs on. `LocalForward` takes a socket path as its second argument ([`ssh_config(5)`](https://man.openbsd.org/ssh_config#LocalForward): "Unix domain socket paths may be used in place of a TCP port"; the entry itself was not run on a login node, **[to be validated]**):

    ```text
    Host demo-hpc
        HostName demo-hpc-login1
        User alice
        LocalForward 127.0.0.1:8080 /tmp/spectio-1000/spectio.sock
    ```

    A static socket path is safe only while the tunnel line still shows it. Behind a socket, `spectio serve` refuses a default `/tmp/spectio-<uid>` that another user created first (after a reboot or a `/tmp` purge): it names that user's uid and asks for `--db-dir`, and never moves to a `mkdtemp` directory that this entry would miss. With another `--db-dir` the socket moves too: copy the new path from the tunnel line. Way 2, `spectio open`, reads the path from `server.json` each time and is the safer choice.

3. **Connect** with `ssh demo-hpc`. The tunnel lasts as long as the session.
4. **Start the server** in that session if none runs: `spectio serve --detach` keeps it in a tmux session `spectio-server` and prints the link ([Keeping the server running](keep-the-server-running.md)). It has not run on a cluster yet, **[to be validated]**.
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
3. Without one, it starts a server on `--node`, else the `node` of `clusters.toml`, else `<host>`: `spectio init` only if `~/.spectio` is missing, then `spectio serve --detach --no-link`, so no link lands in the ssh output. If that exits 3 (started, no link yet), it asks for the ticket again every 2 s for up to 120 s. The whole path through `spectio open` has run against a fake remote `spectio` in the tests only, not over a real `sshd`.
4. It opens the tunnel from a free local port (`--local-port` sets one) to the socket that `server.json` names (to the server's port when it names none, in local mode), asks the node for a ticket with `spectio login --print-link --json`, builds the link itself and opens your browser. A URL printed by the cluster is never opened.
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
- a socket is `spectio.sock` in the `db_dir` of the same file, of `A-Za-z0-9._/-` only (a `:` would cut the `-L` argument), at most 107 bytes;
- `--` comes before every `ssh` destination, and no cluster value goes inside `-o`;
- the tunnel is `-N -o ExitOnForwardFailure=yes -L 127.0.0.1:<local>:<socket>`, or `-L 127.0.0.1:<local>:127.0.0.1:<port>` with no socket, with no host-key option.

## Why a socket on a cluster

The node has one network namespace for everyone, so `127.0.0.1` is not a per-user boundary. An audit of an EMBL login node on 2026-11-08 confirmed it. A socket in a `0700` directory is a boundary: the kernel refuses another user at `connect`, before any Spectio code runs. The one-time link and the session stay as a second barrier. Your browser still opens `http://127.0.0.1:<port>` on the laptop, and the session cookie is named after that port.

`spectio serve` chooses the socket by itself on a SLURM environment, and in local mode on a machine that looks shared (another user's process, a SLURM install). In local mode on a machine only you use it keeps `127.0.0.1:<port>`, opened in that machine's browser. It refuses to start when:

- the database directory is not `0700` and yours: it changes nothing, and says the directory must be one of yours with mode `0700`, naming its owner;
- the default `/tmp/spectio-<uid>` already exists and is not a private directory of yours, which on a shared `/tmp` usually means another user made it first. Behind the socket the tunnel names that exact path, so `spectio serve` does not move to another directory: it exits 2, names the owner's uid, and asks you to remove the directory if it is yours or to choose another with `--db-dir`. Do not `chmod` or reuse a directory someone else made;
- the socket path is over 107 bytes, the Linux limit: choose a shorter `--db-dir`;
- a file at the socket's path is not a socket, or a server answers on it. A socket file nothing answers on, left by a server that died, is replaced.

## See it run

The cast runs the real `spectio open` and a real `spectio serve` in a demo home on the demo host `demo-hpc-login1`. The `ssh` is the fake of the tests: it runs the remote commands in a shared home of its own and listens on the tunnel's local port, but forwards nothing, so the cast runs with `--no-browser`. The ticket is masked by a visible `sed`. Steps: the server on the node, `spectio open`, the three `ssh` calls it made, then the missing remote `spectio` (exit 2).

<div class="asciinema-cast" data-cast="assets/casts/spectio-open.cast"></div>

## Limits in 0.0.1

- **Not checked on a real login node.** The tunnel to a socket was tried on an EMBL login node with a throwaway server. `spectio serve` itself on a socket there, a second account refused at `connect`, and the server surviving a full logout are **[to be validated]**. So is the path of `spectio open` over a real `sshd`, and whether `"$SHELL" -lc` works on those nodes.
- **A POSIX-family login shell is needed.** The remote scripts fail with a syntax error under tcsh.
- **A stale `server.json`.** Spectio does not check that the server it names is alive. After a crash or a node reboot, the login fails and the error names the file as a possible cause: remove it and run `spectio open` again.
- **Ctrl-C while waiting for a second factor** exits 0, not 3.
- **The ticket** goes to the browser's command line and is echoed in the terminal. It is single use.
