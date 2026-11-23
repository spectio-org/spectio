"""The HTTP client of tests/slurm/e2e.sh (P1 Task 22): stdlib only, run on the login node (the sind
submitter, or this host in native mode) as the user that runs `spectio serve`.

    python3 e2e_client.py launch ENGINE --config TOML --location DIR --golden TSV
                          [--profile P]... [--params JSON] [--scenario YAML] [--timeout S]

It signs in as a browser does (a link from `spectio login --print-link --json`, the exchange with
`Host` and `Origin`), launches the pipeline with `POST /api/v1/runs`, polls the run until it ends,
and checks each item of CHECKS. The `expect` lines of --scenario must each name one of them. One
`ok` or `FAIL` line per check; exit 0 when every check passed, 1 otherwise. When the config's executor
is `local` (tests/local/e2e.sh, P2 §10.8), the head runs in its own session (setsid), not in tmux, and
there is no squeue: LOCAL_CHECKS replace the two cluster checks.
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
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
)
LOCAL_CHECKS = (
    "run succeeded",
    "head in its own session",
    "counts equal the golden",
    "head.exit 0, as the run reads it",
    "no spool drop",
    "no head left",
)
# `.spectio/head.pid` as the head script writes it (spectio.runner.local._PID_LINE): PID, group, start.
HEAD_PID = re.compile(r"([1-9][0-9]{0,9}) ([1-9][0-9]{0,9}) ([0-9]{1,20}) [0-9a-f-]{36} [A-Za-z0-9._-]{1,255}\n")
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback, never a proxy


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


def states_problem(seen: list[str]) -> str | None:
    """None when the run went queued, then running, then succeeded, and through nothing else."""
    if changes(seen) != ["queued", "running", "succeeded"]:
        return f"states seen {' → '.join(changes(seen)) or 'none'}, not queued → running → succeeded"
    return None


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


class Api:
    def __init__(self, port: int) -> None:
        self.port = port
        self.origin = f"http://127.0.0.1:{port}"
        self.cookie: str | None = None

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, object, object]:
        headers = {"Host": f"127.0.0.1:{self.port}", "Origin": self.origin, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        req = urllib.request.Request(self.origin + path, data=data, headers=headers, method=method)
        try:
            with DIRECT.open(req, timeout=30) as answer:
                raw = answer.read()
                return answer.status, (json.loads(raw) if raw else None), answer.headers
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                doc = json.loads(raw)
            except ValueError:
                doc = raw[:500].decode(errors="replace")
            return exc.code, doc, exc.headers

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


def launch(args: argparse.Namespace) -> int:
    config = tomllib.loads(Path(args.config).read_text())
    port, runs_root, db_dir = config["port"], config["runs_root"], config["db_dir"]
    names = checks_of(config)
    local = names == LOCAL_CHECKS
    api = Api(port)
    out = subprocess.run(["spectio", "login", "--print-link", "--json"],  # noqa: S603, S607
                         capture_output=True, text=True, timeout=60)
    _, headers = api.expect(204, "POST", "/api/v1/auth/magic-links:exchange",
                            {"ticket": parse_ticket(out.stdout)})
    api.cookie = session_cookie(headers, port)
    body = {"workflow": {"location": args.location, "engine": args.engine}, "profiles": args.profile,
            "params": json.loads(args.params)}
    run, _ = api.expect(201, "POST", "/api/v1/runs", body)
    run_id = run["id"]
    session = f"spectio-{run_id}"
    run_dir = f"{runs_root}/{run_id}"
    local_head: str | None = "the run was never seen running"
    print(f"run {run_id} launched; polling", flush=True)
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
    args = p.parse_args(argv)
    try:
        return launch(args)
    except Failed as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
