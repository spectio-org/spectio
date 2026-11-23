"""The HTTP client of tests/slurm/e2e.sh (P1 Tasks 22 and 23): stdlib only, run on the login node (the
sind submitter, or this host in native mode) as the user that runs `spectio serve`.

    python3 e2e_client.py launch ENGINE --config TOML --location DIR --golden TSV
                          [--profile P]... [--params JSON] [--scenario YAML] [--timeout S]
    python3 e2e_client.py cancel ENGINE --config TOML --location DIR [--profile P]... [--params JSON] [--timeout S]
    python3 e2e_client.py restart --config TOML --location DIR --golden TSV --tmux-log FILE
                          [--profile P]... [--params JSON] [--timeout S]
    python3 e2e_client.py teardown --config TOML

It signs in as a browser does (a link from `spectio login --print-link --json`, the exchange with
`Host` and `Origin`), launches the pipeline with `POST /api/v1/runs`, polls the run until it ends,
and checks each item of CHECKS. The `expect` lines of --scenario must each name one of them. One
`ok` or `FAIL` line per check; exit 0 when every check passed, 1 otherwise. When the config's executor
is `local` (tests/local/e2e.sh, P2 §10.8), the head runs in its own session (setsid), not in tmux, and
there is no squeue: LOCAL_CHECKS replace the two cluster checks.

`cancel` (CANCEL_CHECKS) waits until the run is `running` with a task running, then `POST :cancel`s it.
`restart` (RESTART_CHECKS) SIGKILLs the server at the first succeeded task, waits RESTART_WAIT_S, starts it
again with `spectio serve --detach`, and checks that the head was adopted, not started again: the tmux
calls of the server go through the shim of e2e.sh, which logs them to --tmux-log. `teardown` kills the
heads' tmux sessions and cancels the jobs of every run under the runs root; e2e.sh runs it after each case.

The server is the one `<data dir>/server.json` names. On SLURM and on a shared host it listens only on
`spectio.sock` in its 0700 database directory, never on a TCP port (FU-P3-72, dev-env §15.3 req. 1): the
client then speaks HTTP over that socket, with `Host` and `Origin` naming 127.0.0.1 and the port, as a
browser at the laptop's end of the tunnel does. With no socket in server.json (local mode on a machine only
the user uses) it uses 127.0.0.1 and the port. Never a proxy.
"""
import argparse
import http.client
import itertools
import json
import os
import re
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import tomllib
from pathlib import Path

POLL_S = 2
LEFT_S = 60  # after the run ends: its jobs leave squeue and its tmux session closes
TICKET = re.compile(r"spectio-ticket-v1 (\{.*\})")
TICKET_VALUE = re.compile(r"[A-Za-z0-9_-]{43}")
ENDED = ("succeeded", "failed", "cancelled")
# The golden's statuses (run_scenarios.py) as task states of the API.
STATUS = {"COMPLETED": "succeeded", "FAILED": "failed", "CACHED": "cached"}
CHECKS = (
    "run succeeded",
    "head in tmux, no sbatch",
    "counts equal the golden",
    "head.exit 0, as the run reads it",
    "no spool drop",
    "no job or session left",
    "socket only, no TCP port",
)
LOCAL_CHECKS = (
    "run succeeded",
    "head in its own session",
    "counts equal the golden",
    "head.exit 0, as the run reads it",
    "no spool drop",
    "no head left",
)
CANCEL_CHECKS = (
    "run cancelled in time",
    "no job or session left",
    "no attempt left pending, submitted or running",
    "socket only, no TCP port",
)
RESTART_CHECKS = (
    "run succeeded",
    "head adopted, not started again",
    "counts equal the golden",
    "no duplicate event_id",
    "no spool drop",
    "old cookie refused, new link works",
    "no job or session left",
    "socket only, no TCP port",
)
SUCCEEDED_PATH = ("queued", "running", "succeeded")
CANCELLED_PATH = ("queued", "running", "cancelling", "cancelled")
OPEN_ATTEMPTS = ("pending", "submitted", "running")  # an attempt in none of these has ended
CANCEL_GRACE_S = 60  # spectio.runner.tmux.TmuxLauncher.cancel: Ctrl-C, SIGTERM after it, SIGKILL after another
CANCEL_WINDOW_S = CANCEL_GRACE_S + 120  # P1 Task 23: cancelling → cancelled within grace + 120 s
RESTART_WAIT_S = 20  # P1 Task 23: between the SIGKILL and `spectio serve --detach`
RUN_DIR = re.compile(r"run_[0-9A-HJKMNP-TV-Z]{26}")  # spectio.runner.rundir.RUN_ID
# `.spectio/head.pid` as the head script writes it (spectio.runner.local._PID_LINE): PID, group, start.
HEAD_PID = re.compile(r"([1-9][0-9]{0,9}) ([1-9][0-9]{0,9}) ([0-9]{1,20}) [0-9a-f-]{36} [A-Za-z0-9._-]{1,255}\n")
LOOPBACK = "127.0.0.1"
SOCKET = "spectio.sock"  # spectio.ports.SOCKET: the server's socket, in its database directory


class Failed(Exception):
    """The run cannot go on: the message says why."""


def parse_ticket(out: str) -> str:
    """The ticket of `spectio login --print-link --json`'s sentinel line."""
    for line in out.splitlines():
        m = TICKET.fullmatch(line)
        if m:
            ticket = json.loads(m[1]).get("ticket")
            if isinstance(ticket, str) and TICKET_VALUE.fullmatch(ticket):
                return ticket
    raise Failed("spectio login --print-link --json printed no ticket")


def session_cookie(headers, port: int) -> str:
    """`name=value` of the session cookie that the exchange set for `port`."""
    name = f"spectio_session_{port}="
    for value in headers.get_all("Set-Cookie") or []:
        pair = value.split(";", 1)[0].strip()
        if pair.startswith(name):
            return pair
    raise Failed(f"the exchange set no {name[:-1]} cookie")


def golden_counts(text: str) -> dict[str, dict[str, int]]:
    """Per process, the task states of the golden's last run and their counts."""
    rows = [line.split("\t") for line in text.splitlines() if line and not line.startswith(("#", "run\t"))]
    last = max(int(r[0]) for r in rows)
    counts: dict[str, dict[str, int]] = {}
    for run, process, status, *_, count in rows:
        if int(run) != last:
            continue
        if status not in STATUS:
            raise Failed(f"golden status {status!r} has no task state")
        by = counts.setdefault(process, {})
        by[STATUS[status]] = by.get(STATUS[status], 0) + int(count)
    return counts


def process_counts(items: list[dict]) -> dict[str, dict[str, int]]:
    """`GET /runs/{id}/processes` as the golden names it: Snakemake rules upper-cased."""
    return {item["process"].upper(): dict(item["counts"]) for item in items}


def count_diff(want: dict, got: dict) -> list[str]:
    return [f"{p}: want {want.get(p, {})}, got {got.get(p, {})}"
            for p in sorted(set(want) | set(got)) if want.get(p, {}) != got.get(p, {})]


def changes(states: list[str]) -> list[str]:
    return [s for i, s in enumerate(states) if i == 0 or s != states[i - 1]]


def states_problem(seen: list[str], want: tuple[str, ...] = SUCCEEDED_PATH) -> str | None:
    """None when the run went through the states of `want`, in order, and through nothing else."""
    if tuple(changes(seen)) != want:
        return f"states seen {' → '.join(changes(seen)) or 'none'}, not {' → '.join(want)}"
    return None


def tasks_running(detail: dict) -> bool:
    """The run is `running` with at least one task running: the moment to cancel it."""
    return detail.get("state") == "running" and (detail.get("task_counts") or {}).get("running", 0) > 0


def new_sessions(log: str, session: str) -> int:
    """How many `new-session ... -s <session>` calls the tmux shim's log holds (`$*` per line)."""
    count = 0
    for line in log.splitlines():
        words = line.split()
        if words[:1] == ["new-session"] and ("-s", session) in itertools.pairwise(words):
            count += 1
    return count


def expect_problems(lines: list[str], checks: dict[str, str | None]) -> list[str]:
    """One line per expect line that failed, or that names no check."""
    out = []
    for line in lines:
        if line not in checks:
            out.append(f"{line}: no such check in e2e_client.py")
        elif checks[line] is not None:
            out.append(f"{line}: {checks[line]}")
    return out


def scenario_expect(path: str) -> list[str]:
    """The `expect:` list of a tests/scenarios file (the subset dev/scenario.py reads)."""
    lines, inside = [], False
    for line in Path(path).read_text().splitlines():
        if line.startswith("expect:"):
            inside = True
        elif inside and line.startswith("  - "):
            lines.append(line[4:].split("  #", 1)[0].strip())
        elif inside and line.strip():
            break
    return lines


def checks_of(config: dict) -> tuple[str, ...]:
    return LOCAL_CHECKS if config.get("executor") == "local" else CHECKS


def head_pid(text: str) -> tuple[int, int, str] | None:
    """PID, process group and start time of a head.pid line, None when it is not one."""
    m = HEAD_PID.fullmatch(text)
    return (int(m[1]), int(m[2]), m[3]) if m else None


def read_head_pid(run_dir: str) -> tuple[int, int, str] | None:
    try:
        return head_pid(Path(run_dir, "launch", ".spectio", "head.pid").read_text())
    except OSError:
        return None


def own_session(head: tuple[int, int, str] | None, api_head: dict) -> str | None:
    """None when the API shows the local head alive, as head.pid names it, leading its own group."""
    if head is None:
        return "no head.pid"
    pid, pgid, start = head
    if pgid != pid:
        return f"head {pid} is in group {pgid}, not its own session"
    if api_head.get("session") != f"{pid}.{start}":
        return f"the API's head is {api_head.get('session')}, head.pid says {pid}.{start}"
    if api_head.get("alive") is not True:
        return f"the API's head {pid}.{start} is not alive while the run is running"
    return None


def proc_start(pid: int) -> str | None:
    """The start time of a live process (field 22 of /proc/<pid>/stat), None when gone or a zombie."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    except (OSError, IndexError):
        return None
    return None if fields[0] == "Z" else fields[19]


def head_left(head: tuple[int, int, str] | None) -> str | None:
    """What is left of a local head: its process, when it still lives with head.pid's start time."""
    if head is None or proc_start(head[0]) != head[2]:
        return None
    return f"head {head[0]} still running"


def run_jobs(lines: list[str], run_dir: str) -> list[str]:
    """The `id|name|workdir` lines of squeue whose work directory is in the run's directory."""
    return [line for line in lines if line and (line.split("|")[-1] + "/").startswith(run_dir.rstrip("/") + "/")]


def head_jobs(lines: list[str]) -> list[str]:
    return [line for line in lines if line.split("|")[1:2] and line.split("|")[1].startswith("spectio-head-")]


def job_states(lines: list[str], run_dir: str) -> dict[str, int]:
    """The `id|name|state|workdir` lines of `squeue --states=all` of the run, counted by state."""
    out: dict[str, int] = {}
    for line in run_jobs(lines, run_dir):
        state = line.split("|")[2]
        out[state] = out.get(state, 0) + 1
    return out


def teardown_plan(names: list[str], lines: list[str], runs_root: str) -> tuple[list[str], list[str]]:
    """The tmux sessions of the run directories among `names`, and the IDs of the squeue jobs under the root."""
    sessions = [f"spectio-{name}" for name in sorted(names) if RUN_DIR.fullmatch(name)]
    return sessions, [line.split("|")[0] for line in run_jobs(lines, runs_root)]


# The server's own process: `spectio serve --detach` starts `python -P -m spectio serve --pane` in its tmux
# pane (spectio/cli/serve.py `_pane_argv`, `_runs_pane_serve`), and server.json names that PID.
PANE_SERVE = ["-m", "spectio", "serve", "--pane"]


def server_pid(data_dir: str) -> int:
    """The PID of server.json, once checked to be the `spectio serve --pane` of this node and this uid."""
    try:
        record = json.loads(Path(data_dir, "server.json").read_text())
    except (OSError, ValueError) as exc:
        raise Failed(f"no usable {data_dir}/server.json: {exc}") from exc
    pid = record.get("pid")
    if record.get("host") != socket.gethostname():
        raise Failed(f"server.json names node {record.get('host')!r}, not this one")
    if type(pid) is not int or pid <= 1:
        raise Failed(f"server.json names PID {pid!r}")
    try:
        uid = os.stat(f"/proc/{pid}").st_uid
        words = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError as exc:
        raise Failed(f"server.json names PID {pid}, which does not run: {exc}") from exc
    if uid != os.getuid():
        raise Failed(f"PID {pid} of server.json belongs to uid {uid}, not {os.getuid()}")
    if not any(words[i : i + len(PANE_SERVE)] == PANE_SERVE for i in range(len(words))):
        raise Failed(f"PID {pid} of server.json runs {' '.join(words)[:200]!r}, not spectio serve --pane")
    return pid


def kill_server(data_dir: str) -> int:
    """SIGKILL to the server of server.json, through a pidfd opened before the checks, so that a process
    that took its PID meanwhile is never signalled (SEC-P3T23-03). Its PID."""
    try:
        record = json.loads(Path(data_dir, "server.json").read_text())
        fd = os.pidfd_open(record["pid"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Failed(f"the server of {data_dir}/server.json cannot be signalled: {exc!r}") from exc
    try:
        pid = server_pid(data_dir)
        if pid != record["pid"]:
            raise Failed(f"server.json changed while it was read: PID {record['pid']}, then {pid}")
        signal.pidfd_send_signal(fd, signal.SIGKILL)
    finally:
        os.close(fd)
    return pid


def socket_only(config: dict) -> bool:
    """Off a machine only the user uses (executor `local`), the server listens on its socket only (FU-P3-72)."""
    return config.get("executor") != "local"


def tcp_listener(port: int | None) -> str | None:
    """What listens on 127.0.0.1 at server.json's port, None when nothing does (or there is no port)."""
    if port is None:
        return None
    try:
        with socket.create_connection((LOOPBACK, port), timeout=5):
            return f"something listens on {LOOPBACK}:{port}: the server must listen on its socket only"
    except OSError:
        return None


def same_socket(old: str | None, new: str | None) -> str | None:
    """None when the restarted server is on the socket the first one was on."""
    if old is None or new is None:
        return f"no socket in server.json (before: {old}, after: {new})"
    return None if old == new else f"the socket moved from {old} to {new}"


def server_address(data_dir: str, db_dir: str, socket_only: bool = False) -> tuple[int, str | None]:
    """The port and the socket of `<data_dir>/server.json`; the socket is None for a server on TCP, which
    `socket_only` (SLURM, a shared host) refuses: no TCP fallback (SEC-P3T23-01).
    A socket other than `SOCKET` in `db_dir`, the config's database directory, is refused."""
    try:
        record = json.loads(Path(data_dir, "server.json").read_text())
    except (OSError, ValueError) as exc:
        raise Failed(f"no usable {data_dir}/server.json: {exc}") from exc
    port, sock = record.get("port"), record.get("socket")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise Failed(f"server.json names port {port!r}, not one in 1024-65535")
    if sock is not None and sock != f"{db_dir.rstrip('/')}/{SOCKET}":
        raise Failed(f"server.json names socket {sock!r}, not {SOCKET} in {db_dir}")
    if socket_only and sock is None:
        raise Failed("server.json names no socket: on SLURM the server listens on its socket only")
    return port, sock


class UnixHTTP(http.client.HTTPConnection):
    """HTTP on the server's Unix socket."""

    def __init__(self, path: str, timeout: float) -> None:
        super().__init__(LOOPBACK, timeout=timeout)
        self.socket_path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
        except BaseException:
            sock.close()
            raise
        self.sock = sock


class Api:
    """The server's API, on its socket when it has one, else on 127.0.0.1 and the port. `Host` and `Origin`
    always name 127.0.0.1 and the port, as the browser's do through the tunnel (the session cookie is per port)."""

    def __init__(self, port: int, socket_path: str | None) -> None:
        self.port = port
        self.socket_path = socket_path
        self.address = (LOOPBACK, port)  # used when there is no socket
        self.origin = f"http://{LOOPBACK}:{port}"
        self.cookie: str | None = None

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, object, object]:
        headers = {"Host": f"{LOOPBACK}:{self.port}", "Origin": self.origin, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.socket_path is None:
            conn = http.client.HTTPConnection(*self.address, timeout=30)
        else:
            conn = UnixHTTP(self.socket_path, timeout=30)
        try:
            conn.request(method, path, body=data, headers=headers)
            answer = conn.getresponse()
            raw = answer.read()
        except (OSError, http.client.HTTPException) as exc:
            where = self.socket_path or f"{self.address[0]}:{self.address[1]}"
            raise Failed(f"{method} {path} on {where}: {exc!r}") from exc
        finally:
            conn.close()
        try:
            doc = json.loads(raw) if raw else None
        except ValueError:
            doc = raw[:500].decode(errors="replace")
        return answer.status, doc, answer.headers

    def expect(self, code: int, method: str, path: str, body: dict | None = None):
        got, doc, headers = self.call(method, path, body)
        if got != code:
            raise Failed(f"{method} {path}: HTTP {got}, not {code}: {doc}")
        return doc, headers


def lines_of(*argv: str) -> list[str]:
    """The command's stdout lines; a non-zero exit raises, so a failed squeue never reads as an empty queue."""
    done = subprocess.run(argv, capture_output=True, text=True, timeout=60)  # noqa: S603
    if done.returncode != 0:
        raise Failed(f"{argv[0]} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout.splitlines()


def tmux_has(session: str) -> bool:
    return subprocess.run(["tmux", "has-session", "-t", f"={session}"],  # noqa: S603, S607
                          capture_output=True, timeout=30).returncode == 0


def squeue() -> list[str]:
    return lines_of("squeue", "--me", "-h", "-o", "%i|%j|%Z")


def left_over(run_dir: str, session: str) -> str | None:
    """What is left of the run (its jobs in squeue, its tmux session), None when nothing; a failed squeue is left over."""
    try:
        left = run_jobs(squeue(), run_dir)
    except Failed as exc:
        return f"squeue failed: {exc}"
    tmux = tmux_has(session)
    return f"jobs in squeue: {left}; tmux session {session}: {tmux}" if left or tmux else None


def spool_drops(db: Path, run_id: str) -> list[tuple]:
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return conn.execute(
            "SELECT launch_id, reason, count FROM spool_drops WHERE launch_id IN "
            "(SELECT id FROM launches WHERE run_id = ?)", (run_id,)).fetchall()


def attempts_in(db: str, run_id: str, states: tuple[str, ...]) -> list[str]:
    """The run's attempts in one of `states`, as `<process> attempt <n>: <state>`."""
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT t.process_or_rule, a.n, a.state FROM attempts a JOIN tasks t ON a.task_id = t.id "
            "WHERE t.run_id = ? ORDER BY t.process_or_rule, a.n", (run_id,)).fetchall()
    conn.close()
    return [f"{p} attempt {n}: {state}" for p, n, state in rows if state in states]


def duplicate_events(db: str, run_id: str) -> list[str]:
    """The run's event IDs that the events table holds more than once. The schema refuses them already
    (UniqueConstraint run_id, event_id: migration 0001_initial_store.py:253), so this guards that the
    constraint stays, not the projector (CR-P3T23-02)."""
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT event_id, COUNT(*) FROM events WHERE run_id = ? GROUP BY event_id HAVING COUNT(*) > 1 "
            "ORDER BY event_id", (run_id,)).fetchall()
    conn.close()
    return [f"{event_id} ({n} times)" for event_id, n in rows]


def signed_in(config: dict) -> Api:
    """The API of the server that server.json names, with a session cookie from a new link."""
    port, socket_path = server_address(config["data_dir"], config["db_dir"], socket_only(config))
    api = Api(port, socket_path)
    print(f"server on {socket_path or f'{LOOPBACK}:{port}'}", flush=True)
    out = subprocess.run(["spectio", "login", "--print-link", "--json"],  # noqa: S603, S607
                         capture_output=True, text=True, timeout=60)
    _, headers = api.expect(204, "POST", "/api/v1/auth/magic-links:exchange",
                            {"ticket": parse_ticket(out.stdout)})
    api.cookie = session_cookie(headers, port)
    return api


def start(api: Api, args: argparse.Namespace) -> dict:
    body = {"workflow": {"location": args.location, "engine": args.engine}, "profiles": args.profile,
            "params": json.loads(args.params)}
    run, _ = api.expect(201, "POST", "/api/v1/runs", body)
    print(f"run {run['id']} launched; polling", flush=True)
    return run


def poll_until(api: Api, run: dict, states: list[str], done, timeout: float) -> dict:
    """The run's detail once `done(detail)` or the run ended, or at the timeout; each state is appended."""
    deadline = time.monotonic() + timeout
    detail = run
    while not done(detail) and detail["state"] not in ENDED and time.monotonic() < deadline:
        time.sleep(POLL_S)
        detail, _ = api.expect(200, "GET", f"/api/v1/runs/{run['id']}")
        if detail["state"] != states[-1]:
            print(f"  {detail['state']} tasks={detail['task_counts']}", flush=True)
        states.append(detail["state"])
    return detail


def wait_left_over(run_dir: str, session: str) -> str | None:
    """`left_over` until nothing is left, or what is left after LEFT_S."""
    until = time.monotonic() + LEFT_S
    while (left := left_over(run_dir, session)) is not None and time.monotonic() < until:
        time.sleep(POLL_S)
    return left


def report(names: tuple[str, ...], checks: dict[str, str | None], detail: dict) -> int:
    for name in names:
        print(f"ok   {name}" if checks[name] is None else f"FAIL {name}: {checks[name]}")
    print(f"run {detail['id']}: {detail['state']}, tasks {detail['task_counts']}")
    return 1 if any(checks[name] is not None for name in names) else 0


def cancel(args: argparse.Namespace) -> int:
    config = tomllib.loads(Path(args.config).read_text())
    api = signed_in(config)
    run = start(api, args)
    run_id, states = run["id"], [run["state"]]
    session, run_dir = f"spectio-{run_id}", f"{config['runs_root']}/{run_id}"
    tcp = tcp_listener(api.port)
    detail = poll_until(api, run, states, tasks_running, args.timeout)
    if not tasks_running(detail):
        raise Failed(f"run {run_id} was never running with a task running: {detail['state']} {detail['task_counts']}")
    asked = time.monotonic()
    detail, _ = api.expect(202, "POST", f"/api/v1/runs/{run_id}:cancel")
    print(f"  cancel asked: {detail['state']} tasks={detail['task_counts']}", flush=True)
    states.append(detail["state"])
    detail = poll_until(api, detail, states, lambda d: False, CANCEL_WINDOW_S)
    took = time.monotonic() - asked
    checks: dict[str, str | None] = dict.fromkeys(CANCEL_CHECKS)
    checks["socket only, no TCP port"] = tcp
    checks["run cancelled in time"] = states_problem(states, CANCELLED_PATH) or (
        f"cancelled after {took:.0f} s, not within {CANCEL_WINDOW_S} s" if took > CANCEL_WINDOW_S else None)
    # Whether the engine's abort cancels its SLURM jobs is [to be validated] (schedulers §3.1.1): shown, not checked.
    try:
        jobs = job_states(lines_of("squeue", "--me", "-h", "--states=all", "-o", "%i|%j|%T|%Z"), run_dir)
        print(f"info: the run's jobs in squeue --states=all when it ended, by state: {jobs}", flush=True)
    except Failed as exc:
        print(f"info: squeue --states=all failed: {exc}", flush=True)
    checks["no job or session left"] = wait_left_over(run_dir, session)
    left = attempts_in(str(Path(config["db_dir"]) / "spectio.db"), run_id, OPEN_ATTEMPTS)
    checks["no attempt left pending, submitted or running"] = "; ".join(left) or None
    return report(CANCEL_CHECKS, checks, detail)


def restart(args: argparse.Namespace) -> int:
    config = tomllib.loads(Path(args.config).read_text())
    db = str(Path(config["db_dir"]) / "spectio.db")
    api = signed_in(config)
    run = start(api, args)
    run_id, states = run["id"], [run["state"]]
    session, run_dir = f"spectio-{run_id}", f"{config['runs_root']}/{run_id}"
    tcp = [tcp_listener(api.port)]
    detail = poll_until(api, run, states, lambda d: (d.get("task_counts") or {}).get("succeeded", 0) > 0,
                        args.timeout)
    if detail["state"] != "running":
        raise Failed(f"run {run_id} was {detail['state']} at its first succeeded task, not running")
    _, old_socket = server_address(config["data_dir"], config["db_dir"], socket_only(config))
    pid = kill_server(config["data_dir"])
    print(f"  server {pid} killed (SIGKILL) at tasks={detail['task_counts']}; {RESTART_WAIT_S} s", flush=True)
    time.sleep(RESTART_WAIT_S)
    started = subprocess.run(["spectio", "serve", "--detach"], stdout=subprocess.DEVNULL,  # noqa: S603, S607
                             stderr=subprocess.PIPE, text=True, timeout=180)
    if started.returncode != 0:
        raise Failed(f"spectio serve --detach exited {started.returncode}: {started.stderr.strip()[:500]}")
    checks: dict[str, str | None] = dict.fromkeys(RESTART_CHECKS)
    port, new_socket = server_address(config["data_dir"], config["db_dir"], socket_only(config))  # written again
    tcp.append(tcp_listener(port))
    stale = Api(port, new_socket)
    stale.cookie = api.cookie  # the session of the server that was killed
    refused = stale.call("GET", f"/api/v1/runs/{run_id}")[0]
    api = signed_in(config)
    detail = poll_until(api, detail, states, lambda d: False, args.timeout)
    problems = [p for p in (same_socket(old_socket, new_socket),) if p]
    if refused != 401:
        problems.append(f"the old cookie got HTTP {refused}, not 401")
    checks["old cookie refused, new link works"] = "; ".join(problems) or None
    checks["run succeeded"] = states_problem(states)
    items, _ = api.expect(200, "GET", f"/api/v1/runs/{run_id}/processes")
    diff = count_diff(golden_counts(Path(args.golden).read_text()), process_counts(items["items"]))
    checks["counts equal the golden"] = "; ".join(diff) or None
    checks["no duplicate event_id"] = "; ".join(duplicate_events(db, run_id)) or None
    drops = spool_drops(Path(db), run_id)
    checks["no spool drop"] = f"spool_drops: {drops}" if drops else None
    checks["socket only, no TCP port"] = "; ".join(t for t in tcp if t) or None
    checks["no job or session left"] = wait_left_over(run_dir, session)
    try:
        started_n = new_sessions(Path(args.tmux_log).read_text(), session)
    except OSError as exc:
        checks["head adopted, not started again"] = f"no tmux log: {exc}"
    else:
        if started_n != 1:
            checks["head adopted, not started again"] = f"{started_n} new-session calls for {session}, not 1"
    return report(RESTART_CHECKS, checks, detail)


def teardown(args: argparse.Namespace) -> int:
    """Best effort: every head session and job of the runs under the runs root goes; what went is printed."""
    try:
        runs_root = tomllib.loads(Path(args.config).read_text())["runs_root"]
        names = os.listdir(runs_root)
    except (OSError, ValueError, KeyError) as exc:  # the case failed before its init or its first run
        print(f"teardown: nothing to tear down: {exc}")
        return 0
    try:
        lines = squeue()
    except Failed as exc:
        print(f"teardown: {exc}")
        lines = []
    sessions, jobs = teardown_plan(names, lines, runs_root)
    for session in sessions:
        if tmux_has(session):
            subprocess.run(["tmux", "kill-session", "-t", f"={session}"],  # noqa: S603, S607
                           capture_output=True, timeout=30)
            print(f"teardown: killed tmux session {session}")
    if jobs:
        subprocess.run(["scancel", *jobs], capture_output=True, timeout=60)  # noqa: S603, S607
        print(f"teardown: scancel {' '.join(jobs)}")
    return 0


def launch(args: argparse.Namespace) -> int:
    config = tomllib.loads(Path(args.config).read_text())
    runs_root, db_dir = config["runs_root"], config["db_dir"]
    names = checks_of(config)
    local = names == LOCAL_CHECKS
    api = signed_in(config)
    tcp = None if local else tcp_listener(api.port)
    run = start(api, args)
    run_id = run["id"]
    session = f"spectio-{run_id}"
    run_dir = f"{runs_root}/{run_id}"
    local_head: str | None = "the run was never seen running"
    states, head_seen, tmux_seen, jobs_seen = [run["state"]], False, False, set()
    squeue_error: str | None = "no sample"  # None once a squeue sample has answered
    deadline = time.monotonic() + args.timeout
    detail: dict = run
    while detail["state"] not in ENDED:
        if time.monotonic() > deadline:
            break
        time.sleep(POLL_S)
        detail, _ = api.expect(200, "GET", f"/api/v1/runs/{run_id}")
        if detail["state"] != states[-1]:
            print(f"  {detail['state']} tasks={detail['task_counts']}", flush=True)
        states.append(detail["state"])
        if detail["state"] == "running" and local:
            local_head = local_head and own_session(read_head_pid(run_dir), detail.get("head") or {})
        elif detail["state"] == "running":
            head = detail.get("head") or {}
            head_seen |= head.get("session") == session and head.get("alive") is True
            tmux_seen |= tmux_has(session)
        if local:
            continue
        try:
            jobs_seen.update(squeue())
            squeue_error = None
        except Failed as exc:  # skip the sample
            squeue_error = squeue_error and str(exc)
    checks: dict[str, str | None] = dict.fromkeys(names)
    if not local:
        checks["socket only, no TCP port"] = tcp
    checks["run succeeded"] = states_problem(states)
    heads = head_jobs(sorted(jobs_seen))
    if local:
        checks["head in its own session"] = local_head
    elif not (head_seen and tmux_seen) or heads:
        checks["head in tmux, no sbatch"] = (
            f"the API showed {session} alive: {head_seen}; tmux had it: {tmux_seen}; head jobs in squeue: {heads}")
    elif squeue_error:
        checks["head in tmux, no sbatch"] = f"squeue never answered: {squeue_error}"
    items, _ = api.expect(200, "GET", f"/api/v1/runs/{run_id}/processes")
    diff = count_diff(golden_counts(Path(args.golden).read_text()), process_counts(items["items"]))
    checks["counts equal the golden"] = "; ".join(diff) or None
    # The run ends on the engine's last event; its head's exit is read at the next head watch.
    until = time.monotonic() + LEFT_S
    while detail["state"] in ENDED and (detail.get("head") or {}).get("exit_code") is None:
        if time.monotonic() > until:
            break
        time.sleep(POLL_S)
        detail, _ = api.expect(200, "GET", f"/api/v1/runs/{run_id}")
    try:
        code = int(Path(run_dir, "launch", ".spectio", "head.exit").read_text().split()[0])
    except (OSError, ValueError, IndexError) as exc:
        code = None
        checks["head.exit 0, as the run reads it"] = f"head.exit unreadable: {exc}"
    head = detail.get("head") or {}
    if code is not None and (code != 0 or head.get("exit_code") != code):
        checks["head.exit 0, as the run reads it"] = f"head.exit says {code}, the run's head {head.get('exit_code')}"
    drops = spool_drops(Path(db_dir) / "spectio.db", run_id)
    checks["no spool drop"] = f"spool_drops: {drops}" if drops else None
    left_until = time.monotonic() + LEFT_S
    head_at_end = read_head_pid(run_dir)
    while (left := head_left(head_at_end) if local else left_over(run_dir, session)) is not None:
        if time.monotonic() > left_until:
            checks["no head left" if local else "no job or session left"] = left
            break
        time.sleep(POLL_S)
    lines = scenario_expect(args.scenario) if args.scenario else []
    problems = expect_problems(lines + [k for k in names if k not in lines], checks)
    for name in names:
        print(f"{'ok  ' if checks[name] is None else 'FAIL'} {name}{'' if checks[name] is None else ': ' + checks[name]}")
    for line in problems:
        if line.split(":", 1)[0] not in names:
            print(f"FAIL {line}")
    print(f"run {run_id}: {detail['state']}, tasks {detail['task_counts']}")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="e2e_client.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("launch")
    lp.add_argument("engine", choices=["nextflow", "snakemake"])
    lp.add_argument("--config", required=True)
    lp.add_argument("--location", required=True)
    lp.add_argument("--golden", required=True)
    lp.add_argument("--profile", action="append", default=[])
    lp.add_argument("--params", default="{}", help="a JSON object")
    lp.add_argument("--scenario")
    lp.add_argument("--timeout", type=float, default=1800)
    cp = sub.add_parser("cancel")
    cp.add_argument("engine", choices=["nextflow", "snakemake"])
    rp = sub.add_parser("restart")
    rp.set_defaults(engine="nextflow")
    rp.add_argument("--golden", required=True)
    rp.add_argument("--tmux-log", required=True)
    for sp in (cp, rp):
        sp.add_argument("--config", required=True)
        sp.add_argument("--location", required=True)
        sp.add_argument("--profile", action="append", default=[])
        sp.add_argument("--params", default="{}", help="a JSON object")
        sp.add_argument("--timeout", type=float, default=1800)
    tp = sub.add_parser("teardown")
    tp.add_argument("--config", required=True)
    args = p.parse_args(argv)
    try:
        return {"launch": launch, "cancel": cancel, "restart": restart, "teardown": teardown}[args.cmd](args)
    except (Failed, OSError, subprocess.SubprocessError) as exc:  # a FAIL line, never a traceback
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
