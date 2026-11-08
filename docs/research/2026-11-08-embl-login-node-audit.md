# EMBL login node audit (2026-11-08)

**Question.** [Inbox #109](../reviews/inbox.md#109-assumed-writes-need-origin-and-json-as-built-p3-task-16) rule 5 keeps the API unmounted on SLURM and shared hosts, and reconsiders mounting it after a by-hand check on a real login node (W6). The core question: can another user of the node reach a port opened on `127.0.0.1`?

**Answer.** Very probably yes. The node has one network namespace for everyone, with 648 loopback listeners of other users in it. Only an access control an unprivileged user cannot see (nftables, a systemd or cgroup BPF filter) could still separate users, and that is **[to be validated]**. **Recommendation: serve the API and screens on the cluster only behind a Unix socket in a `0700` directory, never on a TCP port, and keep them unmounted until that is built** ([§11](#11-recommendation-for-inbox-109-rule-5)). Thomas chose this direction on 2026-11-08.

## Scope and method

- **Host.** `login1.cluster.embl.de`, Rocky Linux 8.10, kernel `4.18.0-553.144.1.el8_10.x86_64`, 2026-11-08 from 14:45 UTC, with the follow-up tests of [§10](#10-follow-up-tests-same-day) later that day, by SSH from a laptop. One node only; the wiki names a second login node, `login2`, which was not looked at.
- **Limits kept.** No job submitted, no other host or port contacted; `curl` only to my own test servers. Other users' processes and sockets are counted, never named.
- **Cleanup.** Every test directory was removed, including `/tmp/spectio-<uid>`, which `spectio init` created outside the test directory (its three files dated from this run). The checks afterwards:

    ```text
    $ find "$HOME" -maxdepth 1 -name '.spectio-audit-*' | wc -l
    0
    $ ls -d /tmp/spectio-audit.*
    ls: cannot access '/tmp/spectio-audit.*': No such file or directory
    $ ls -d /tmp/spectio-<uid>
    ls: cannot access '/tmp/spectio-<uid>': No such file or directory
    $ ps -u $(id -u) -o args= | grep -c "[s]pectio serve"
    0
    $ tmux ls | grep -c spectio
    0
    ```

- **Redacted, because this repository is public.** The controller and accounting host names, the controller's IP, the NFS server name, the JWT key path, my numeric uid, group, user name and the single-use sign-in token. Everything else is the literal output, shortened where marked `…`.
- **Inbox #123**, named in the task that asked for this audit, does not exist on `autopilot/integration` on this date: the numbering goes from #122 to #124. It is not covered here.

## 1. Slurm

```text
$ sinfo --version
slurm 25.11.6

$ scontrol show config | grep -Ei 'SlurmctldHost|AccountingStorage|ProctrackType|PrologFlags|SlurmVersion'
AccountingStorageBackupHost = (null)
AccountingStorageEnforce = associations,limits,qos,safe
AccountingStorageHost   = <redacted>
AccountingStorageExternalHost = (null)
AccountingStorageParameters = (null)
AccountingStoragePort   = 6819
AccountingStorageTRES   = cpu,mem,energy,node,billing,fs/disk,vmem,pages,gres/gpu,gres/gpumem,gres/gpuutil,gres/shard
AccountingStorageType   = accounting_storage/slurmdbd
ProctrackType           = proctrack/cgroup
PrologFlags             = Alloc,Contain,X11
SlurmctldHost[0]        = <redacted>(<redacted>)

$ scontrol show config | grep -Ei '^(AuthType|AuthAltTypes|AuthInfo|AuthAltParameters)'
AuthAltTypes            = auth/jwt
AuthAltParameters       = jwt_key=<redacted>
AuthInfo                = (null)
AuthType                = auth/munge

$ sacct -X -n -S now-30days -o State | wc -l
2861

$ sacct -X -n -S now-30days -o JobID,State | tail -3
64034990      COMPLETED
64035223      COMPLETED
64035246      COMPLETED

$ which slurmrestd
which: no slurmrestd in (…)          [exit 1]

$ scontrol show config | grep -i rest
GresTypes               = gpu,tmp,shard,unique,scratchbw
SlurmctldParameters     = enable_configless,cloud_dns,conmgr_max_connections=4096,rl_enable,enable_async_reply,reconfig_on_restart,validate_nodeaddr_threads=8

$ grep -rIl 6820 /etc/motd /etc/slurm        [exit 1, no match]
$ ss -ltnH "sport = :6820" | wc -l
0
```

- `sacct` works for my own jobs.
- `slurmrestd` is not on this node's `PATH`, and nothing listens on 6820 here. Whether it runs on another host is unknown.
- Daemons authenticate with munge, and `auth/jwt` is enabled as an alternative type.
- **`curl localhost:6820` was not run**, because no site document names that port: neither `/etc/slurm`, nor the wiki pages [Main_Page](https://wiki.embl.de/cluster/Main_Page), [Env](https://wiki.embl.de/cluster/Env), [Tips](https://wiki.embl.de/cluster/Tips) and [Slurm](https://wiki.embl.de/cluster/Slurm) (read 2026-11-08).

## 2. Loopback isolation

```text
$ readlink /proc/self/ns/net
net:[4026531992]

$ ls -l /proc/1/ns/net
ls: cannot read symbolic link '/proc/1/ns/net': Permission denied

# per-process readlink of /proc/*/ns/net, counts only
mine_readable=39 other_readable=0 other_denied=6844 distinct_net_ns_visible=1

$ lsns -t net -n -o NS,NPROCS | wc -l
1
$ ip netns list                              [exit 0, empty]
$ ls -ld /var/run/netns /run/netns
ls: cannot access '/var/run/netns': No such file or directory
ls: cannot access '/run/netns': No such file or directory

# ss -ltnHe, listeners by bind scope and owner class, counts only
any_or_other other_user 65
any_or_other root_or_unset 16
loopback other_user 648
loopback root_or_unset 3

# ss -ltnp, lines with a visible process name
0

$ iptables -S
iptables v1.8.5 (nf_tables): Could not fetch rule set generation id: Permission denied (you must be root)
$ nft list ruleset
Operation not permitted (you must be root)
```

- **Other users' namespaces cannot be read directly**: all 6844 of their `ns/net` links refuse `readlink`, so comparing inodes, as first planned, gives nothing.
- **The socket table answers it instead.** Port numbers belong to a network namespace: the man page lists "port numbers (sockets)" among the resources namespaces isolate ([network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)). My `ss` shows 648 loopback listeners owned by other uids, so those sockets are in my namespace. A per-user namespace would have hidden them.
- **Inferred [to be validated]:** another user can connect to a port I open on `127.0.0.1`. Not tested, since it needs a second account or a connection to someone else's port. The firewall rules are unreadable, so an access control on connections cannot be excluded ([§10](#10-follow-up-tests-same-day) rules out SELinux). Only a second account running one `curl` against a port of mine would settle it.

## 3. Process visibility

```text
$ mount | grep ' /proc '
proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)

# ps -eo uid=, counts only
mine=44 root=1625 system_lt1000=55 other_ge1000=5194 distinct_other_uids_ge1000=243
```

No `hidepid`. I can see other users' processes: 5194 of them, from 243 uids. `shared_host()`'s `/proc` check therefore works on this node ([§8](#8-spectio-serve)).

## 4. Unix sockets

```text
$ echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
XDG_RUNTIME_DIR=/run/user/<uid>
$ stat -c "%A %a %F" "$HOME"
drwx------ 700 directory
$ ls -ld /run/user
drwxr-xr-x 246 root root 4920 Nov  8 15:47 /run/user
$ ls -ld /run/user/$(id -u)
drwx------ 7 <user> <group> 180 Oct 28 14:14 /run/user/<uid>
$ stat -f -c "%T" /run/user/$(id -u)
tmpfs

# in a 0700 test directory under $HOME (NFS), Python socket.AF_UNIX bind, listen, connect, send
bound 0o700 socket 0o775
self-connect ok
```

- A Unix socket binds and answers under `$HOME`, on NFS. `$XDG_RUNTIME_DIR` is set, `tmpfs`, and `0700`, but the bind was tested only under `$HOME`.
- The socket file itself is `0775` under my umask, group-writable, so the file's mode protects nothing: any privacy has to come from the `0700` parent directory.
- **[to be validated]:** another user cannot connect through a `0700` parent directory. This is the expected behaviour of path permissions, but it has no source here and was not tested without a second account. Root on the node is not bound by it.
- **[to be validated]:** whether `/run/user/<uid>` survives the last logout, which matters for a server that outlives the SSH session (see [§10](#10-follow-up-tests-same-day)). Mine is dated 28 October, so it has lasted 11 days here, with sessions of mine possibly open throughout.

## 5. tmux

```text
$ tmux -V
tmux 2.7
$ echo "TMUX_TMPDIR=$TMUX_TMPDIR"
TMUX_TMPDIR=
$ ls -ld /tmp
drwxrwxrwt 3278 root root 104360 Nov  8 15:47 /tmp
$ ls -ld /tmp/tmux-$(id -u)
drwx------ 2 <user> <group> 60 Jul 20 09:56 /tmp/tmux-<uid>
```

tmux 2.7 is much older than the 3.4 the launcher's tests ran on. This answers the "version on the EMBL login nodes is unknown" of [inbox #110](../reviews/inbox.md#110-assumed-the-tmux-launcher-as-built-p3-task-10) rule 3. The launcher's tmux calls were then run on 2.7 ([§10](#10-follow-up-tests-same-day)).

## 6. Shared home

```text
$ stat -f -c "%T" "$HOME"
nfs
$ df -T "$HOME"
Filesystem         Type   1K-blocks        Used  Available Use% Mounted on
<nfs-server>:/home nfs4 25501368320 24486338560 1015029760  97% /home

# in the 0700 test directory
$ ln a b && stat -c "links=%h" a
links=2
$ flock -n lock -c "echo held; flock -n lock -c \"echo second-fd-acquired\" || echo second-fd-refused"
held
second-fd-refused
```

Hard links and `flock` work on this NFSv4 home from one node. Whether a `flock` taken on `login1` excludes a holder on `login2` was not tested and is **[to be validated]**. `/home` is 97% full.

## 7. Login-node policy

```text
$ ulimit -a                 (extract)
open files                      (-n) 1048000
max user processes              (-u) 8237590
max locked memory       (kbytes, -l) unlimited
cpu time               (seconds, -t) unlimited
virtual memory          (kbytes, -v) unlimited

$ cat /proc/self/cgroup     (extract)
6:cpu,cpuacct:/user.slice/user-<uid>.slice
4:pids:/user.slice/user-<uid>.slice/session-<n>.scope
3:memory:/user.slice/user-<uid>.slice/session-<n>.scope

$ cat /sys/fs/cgroup/memory/user.slice/user-<uid>.slice/memory.limit_in_bytes
137438953472
$ cat /sys/fs/cgroup/cpu,cpuacct/user.slice/user-<uid>.slice/cpu.cfs_quota_us
800000
$ cat /sys/fs/cgroup/pids/user.slice/user-<uid>.slice/pids.max
1000

$ cat /etc/motd             [empty]
$ grep -vE '^\s*(#|$)' /etc/security/limits.conf     [no active line]
$ grep -vE '^\s*(#|$)' /etc/security/limits.d/00-mpi.conf
* soft memlock unlimited
* hard memlock unlimited
* soft nofile 1048000
* hard nofile 1048576
```

- cgroup v1. The user slice is capped at 128 GiB, 1000 processes and a CPU quota of 800000 µs, which is 8 cores with the default 100 ms period ([to be validated]: the period was not read).
- The [Env](https://wiki.embl.de/cluster/Env) page (edited 2026-10-28) states: "Each login session on these two nodes is limited to 8 cores, 120GB of memory and max 1000 processes", and "Login nodes are intentionally designed to be as slow as possible, discouraging you form running any computation on them." The measured memory cap is 128 GiB, not 120 GB.
- **No rule on long-running processes or services was found** on the four wiki pages read, and `/etc/motd` is empty. The nearest stated idle policy is for VNC: "VNC sessions are configured to shut down after 2 days of inactivity" (Env). Per-user services do exist there: Env documents a user-started `vncserver` on the login nodes, and adds "this is a shared machine and … it is considered bad manners if you take over all of its resources". One idle server per user fits these limits; a formal answer is **[to be validated]** with the cluster administrators. The page `Cluster_overview` answers 404.

## 8. `spectio serve`

Wheels from `uv build` of `autopilot/integration` at `09582fe`, with `web/dist` built first, run in a private `/tmp` directory with `HOME` inside it. The `spectio` wheel was built with `--wheel`, without the engine bridges: the laptop's Java and Nextflow could not compile them. This does not affect the start message.

**With the `uv` 0.9.29 installed in my home on the node, Spectio refuses to start** (`spectio init` alone first, then with the flags below: the same refusal, and `spectio serve` gives it too). The Pythons it resolves for 3.13 and 3.14 (3.13.11 and 3.14.2) carry SQLite 3.50.4, and it cannot resolve the repository's pinned 3.13.14:

```text
$ spectio init
spectio init: SQLite 3.50.4 lacks the WAL-reset fix: Spectio needs SQLite >= 3.51.3, or >= 3.50.7 in the 3.50 series, or >= 3.44.6 in the 3.44 series (the library Python loads, sqlite3.sqlite_version)
[exit 2]
```

**With `uv` 0.13.7 (inside the test directory only) and Python 3.13.14, SQLite 3.53.1:**

```text
$ spectio init --nextflow nextflow --snakemake snakemake
Wrote <test>/home/.spectio/spectio.toml; database in /tmp/spectio-<uid>; runs under <test>/home/spectio-runs; port 8080
warning: nf-spectio not unpacked: <test>/venv/lib/python3.13/site-packages/spectio/_bridges/nf-spectio-0.0.1 is missing: build the bridges or set SPECTIO_BRIDGES_DIR
[exit 0]

$ grep -i executor spectio.toml
executor = "slurm"

$ timeout 20 spectio serve
…
INFO spectio_server.serve: index reconciled: 0 runs added
Spectio 0.0.1 is running on login1.cluster.embl.de, port 8080.
1. On your laptop, open a tunnel:  ssh -N -L 127.0.0.1:8080:127.0.0.1:8080 <user>@login1.cluster.embl.de
2. Then open this link (single use, valid 15 minutes):
   http://127.0.0.1:8080/auth/link#<redacted>
Each run's head runs in a tmux session on login1.cluster.embl.de: tmux attach -t spectio-<run ID>.
The API is served only in local mode (spectio init --local), on a machine only you use: on a cluster or another shared host, other users could reach its port.
New link at any time: spectio login --print-link
Spectio never asks you to paste a link.
INFO:     Started server process [1749054]
INFO:     Shutting down
INFO:     Finished server process [1749054]
[exit 124, the timeout]
```

**No `shared_host()` reason appears in this message, by construction.** `no_api_reason` returns `NO_API` for any executor other than `local` before it calls `shared_host()` (`packages/spectio-server/src/spectio_server/app.py:96`). Called directly from the wheel:

```text
SLURM_CONF=<unset>
$ ls -l /etc/slurm/slurm.conf
-rw-r--r-- 1 root root 14893 Apr 10  2026 /etc/slurm/slurm.conf
$ command -v sinfo
/usr/bin/sinfo

$ python -c "from spectio_server.app import shared_host; print(shared_host())"
/etc/slurm/slurm.conf exists

$ env -u SLURM_CONF PATH=/nonexistent python -c "
import pathlib, spectio_server.app as a
a.SLURM_CONF_FILE = pathlib.Path('/nonexistent')
print(a.shared_host())"
a process of uid <other-uid> runs here
```

So `/etc/slurm/slurm.conf exists` is the reason that fires on this node. `sinfo on PATH` would fire next, and the `/proc` check fires on its own too. Three independent signals out of four. From this and the code, `--local` on this node should also leave the API unmounted; `spectio init --local` was not run, so that is **[to be validated]**.

## 9. Other findings for the backlog

1. **Install path.** A `uv` as old as 0.9.29 cannot produce a working Spectio: the install guidance should name a minimum `uv`, or `spectio doctor` a clearer way out.
2. **tmux 2.7** runs the launcher's calls ([§10](#10-follow-up-tests-same-day)): a floor for the `spectio doctor` line of FU-P3-45 can start from it.
3. **The database is node-local**, in `/tmp/spectio-<uid>`, and there are two login nodes, so a server is tied to the node it started on.
4. **On the cluster, signing in leads to a short text and no screens** ([§10](#10-follow-up-tests-same-day)), while the start message promises a link. Until the socket exists, the message should say so.

## 10. Follow-up tests, same day

Run after the first draft, on the same node and with the same limits: own processes and own test port only, in a private directory with `HOME` and `TMUX_TMPDIR` inside it, removed and checked afterwards (no process, no directory, nothing left on port 8080).

**SSH tunnel to a Unix socket: it works.** A throwaway HTTP server listened on two sockets, each in a `0700` directory. From the laptop:

```text
$ ssh -o ExitOnForwardFailure=yes -N -L 127.0.0.1:18765:/tmp/spectio-sock.XXXXXX/s login1.cluster.embl.de
$ curl -i http://127.0.0.1:18765/
HTTP/1.1 200 OK
…
hello via unix socket, dir mode 700

$ ssh -o ExitOnForwardFailure=yes -N -L 127.0.0.1:18766:/run/user/<uid>/spectio-sock.XXXXXX/s login1.cluster.embl.de
$ curl -i http://127.0.0.1:18766/
HTTP/1.1 200 OK
…
hello via unix socket, dir mode 700
```

`/etc/ssh/sshd_config` is not readable (`Permission denied`), so this shows the setting is allowed today, not that it will stay so.

**What `spectio serve` listens on and answers (slurm executor).**

```text
$ ss -ltnHe "sport = :8080"
LISTEN 0      2048   127.0.0.1:8080 0.0.0.0:* uid:<uid>

# signed out
/               401 application/problem+json   "Sign-in required"
/runs, /launch  401
/api/v1/runs    401
/auth/link      200 text/html                  the bootstrap page
/ with Host: evil.example   400 Bad Request

# signed in, with the link the server printed (POST /api/v1/auth/magic-links:exchange: 204 and a session cookie)
/               200 text/plain
Spectio 0.0.1 is running.
The API is served only in local mode (spectio init --local), on a machine only you use: on a cluster or another shared host, other users could reach its port. The screens are served with it.
/runs, /launch, /assets/index.js   404
/api/v1/runs    404   detail: The API is served only in local mode …
```

So with the API unmounted, **a user on the cluster who signs in gets a short text, no screens and no API.** The start message still prints a tunnel and a sign-in link. The port is on `127.0.0.1`, and signed-out requests are refused.

**`spectio serve --detach` works with tmux 2.7**, and the server was still answering from a new SSH connection after the one that started it had ended. That connection was not my last one (three sessions, measured later), so survival after a full logout is not shown.

**tmux 2.7 runs the launcher's exact arguments.** `new-session -d -P -F '#{pane_id} #{pane_pid}' -s <name> -c <dir> bash <head>` printed `%0 1988192`, a second call answered `duplicate session: spectio-run_audit`, and after `send-keys -t <pane> C-c` the tmux server had exited, its only pane gone. `TmuxLauncher` itself was not run, as that would start an engine. Exact targets with two sessions, `spectio-run_a` and `spectio-run_ab`:

```text
$ tmux has-session -t "=spectio-run"
can't find session spectio-run                [exit 1]
$ tmux list-panes -s -t "=spectio-run" -F "#{session_name}"
can't find window spectio-run                 [exit 1]
$ tmux list-panes -s -t "=spectio-run_a" -F "#{session_name}"
spectio-run_a
$ tmux kill-session -t "=spectio-run"
can't find session spectio-run                [exit 1]
$ tmux kill-session -t "=spectio-run_a"       [exit 0, spectio-run_ab left running]
```

One oddity: with a **single** session, `list-panes -s -t "=spectio-run"` returned that session's pane, although the name is only a prefix. A run ID has a fixed length (`RUN_ID`, `packages/spectio/src/spectio/runner/rundir.py:26`), so one launcher target cannot be a prefix of another.

**Socket permissions, as the owner, on my own files.**

```text
start: dir 0o700 socket 0o775
dir 0700, socket as created -> connected
dir 0700, socket 0600 -> connected
dir 0700, socket 0000 -> PermissionError Permission denied
dir 0600 (no search bit), socket 0600 -> PermissionError Permission denied
dir 0000, socket 0600 -> PermissionError Permission denied
```

This kernel applies file permissions to `connect`, on both the socket and its directory. That another user is refused by the `0700` directory follows from the same check, and is still **[to be validated]** without a second account.

**Other access controls on loopback.**

```text
$ getenforce
Disabled
$ systemctl show user-<uid>.slice -p IPAddressDeny -p IPAddressAllow -p IPAccounting
IPAccounting=no
IPAddressAllow=[unprintable]
IPAddressDeny=[unprintable]
$ ls /sys/fs/bpf
ls: cannot open directory '/sys/fs/bpf': Permission denied
$ cat /proc/sys/user/max_user_namespaces
8237590
$ unshare -Urn true           [exit 0]
```

SELinux is ruled out. The `[unprintable]` values leave the systemd IP filters undetermined, and firewall rules remain unreadable, so the second-account test is still needed. An unprivileged user can create a network namespace here.

**Lifetime of `/run/user/<uid>`.**

```text
$ loginctl show-user <uid> -p Linger -p State
State=active
Linger=no
$ ls /run/user | wc -l
248
$ loginctl list-users --no-legend | wc -l
248
$ grep -E '^#?\s*(KillUserProcesses|RemoveIPC)' /etc/systemd/logind.conf
#KillUserProcesses=no
#RemoveIPC=no
```

One directory per user logind knows, and no lingering for my account. That fits the directory going away with the user's last session, which makes it a poor home for a server meant to outlive the SSH connection. Not observed directly, **[to be validated]**.

`spectio doctor` passed its `config`, `sqlite`, `db_dir`, `host`, `tmux` and `sbatch` lines. Its `nextflow`, `snakemake` and `java` lines failed or warned, probably because `HOME` was redirected and the login shell had no tools on its path **[to be validated]**: this says nothing about the node.

## 11. Recommendation for inbox #109 rule 5

**Serve the API and the screens on SLURM and shared hosts only behind a Unix socket in a `0700` directory, never on a TCP port. Until that is built, keep them unmounted.** This revises the first draft of this note, which recommended option (a) and said nothing was lost by waiting: [§10](#10-follow-up-tests-same-day) shows that, unmounted, the cluster user has no screens at all.

Why:

- **`127.0.0.1` is not a per-user boundary here.** One network namespace, 243 other uids ≥ 1000 with visible processes, and 648 loopback listeners of other uids ([§2](#2-loopback-isolation), [§3](#3-process-visibility)), subject to the second-account test below. A TCP API would then rest on the session of [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 2 and 3 against every account on the node. The Host and `Origin` checks (req. 4 and 7) are browser protections: `curl` "sends any `Origin` it likes" ([inbox #86](../reviews/inbox.md#86-assumed-the-001-launch-api-served-in-local-mode-only-before-sign-in)).
- **A Unix socket puts the boundary in the kernel.** Permissions are enforced at `connect`, before any Spectio code runs ([§10](#10-follow-up-tests-same-day)), so a bug in the session check is no longer open to other users. The session stays as a second barrier.
- **It costs the user almost nothing.** The tunnel to a socket works on this node, and the browser still opens `127.0.0.1` on the laptop.
- **A per-user network namespace was not pursued here.** The node runs none. An unprivileged one can be created (`unshare -Urn` works), but how the SSH tunnel would reach it was not examined.
- **The node's limits leave room for one small server** ([§7](#7-login-node-policy)).

**Where the socket should live:** in the database directory, by default `/tmp/spectio-<uid>`. It is node-local, `0700` and already checked by `spectio doctor`, whereas `/run/user/<uid>` probably goes away with the last session. Any cleaning policy on `/tmp` is **[to be validated]**.

Still **[to be validated]** before release:

1. With a second account: connecting to my `127.0.0.1` port succeeds, and connecting to a socket in my `0700` directory fails.
2. That `spectio serve` itself runs on a socket; it does not yet, and only a throwaway server was tested.
3. That the site's administrators accept one idle per-user server on a login node.

**Decided (Thomas, 2026-11-08):** this direction, recorded in [inbox #109](../reviews/inbox.md#109-assumed-writes-need-origin-and-json-as-built-p3-task-16). Building it is a task of its own.
