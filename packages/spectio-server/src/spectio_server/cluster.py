"""The SLURM cluster's facts for the environment form (#401): partitions with their node groups,
the user's accounts, what each partition allows. Read only, from three client commands:

- `sinfo --noheader -o "%P|%l|%D|%c|%m|%f|%G|%T"`: field codes from `man sinfo`: `%P` partition
  (a `*` suffix marks the default), `%l` time limit (`infinite` or `[D-]HH:MM:SS`, `MM:SS`, `MM`),
  `%D` node count, `%c` CPUs per node, `%m` memory per node in MB, `%f` available features,
  `%G` generic resources (`gpu:H100:4(S:0-1)`, `gpu:4`), `%T` node state. `sinfo` prints one line
  per partition and state when `%T` is asked, so the lines of one partition that share CPUs,
  memory, features and GRES are summed into one group, with `idle` the nodes in state idle.
- `scontrol show partition --oneliner`: `AllowAccounts`, `AllowGroups`, `Default`.
- `sacctmgr --noheader --parsable2 show assoc user=<user> format=account,partition`: the
  user's accounts, and the partition an association is limited to (empty: any).

Each is run as `spectio.runner.sacct` runs `scontrol`: an argument list, no shell, a bounded
environment, a timeout after which the process group is killed, its output bounded. A command
that is missing, refused or failing leaves its part empty and never fails the request; without
`sinfo` there is no scheduler (`scheduler: null`). The answer is kept in memory for `TTL_S`
(`FAILED_TTL_S` when there is no scheduler, so a transient failure is retried sooner).
"""

import contextlib
import grp
import os
import pwd
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spectio.config import Settings
from spectio.runner.sacct import MAX_OUTPUT, Refused, _kill, check_tool, sacct_env

TIMEOUT_S = 10.0
TTL_S = 600.0
FAILED_TTL_S = 60.0
SINFO_FORMAT = "%P|%l|%D|%c|%m|%f|%G|%T"
_FIELDS = SINFO_FORMAT.count("|") + 1
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")
_FEATURE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.=-]{0,63}")  # sites write `gpu=H100` as a feature
_COUNT = re.compile(r"[0-9]{1,9}")
_IDLE = {"idle", "idle~", "idle#"}  # `idle*` does not answer: not counted


def _tool_path(settings: Settings, name: str) -> Path | None:
    """The client command beside the `sacct` `spectio init` recorded, else on the server's PATH."""
    if settings.slurm.sacct is not None:
        return settings.slurm.sacct.with_name(name)
    found = shutil.which(name)
    return Path(found) if found else None


def run_tool(settings: Settings, name: str, args: list[str]) -> str | None:
    """The command's output, or None when it is missing, refused, failed, timed out or said
    more than MAX_OUTPUT."""
    path = _tool_path(settings, name)
    if path is None:
        return None
    try:
        check_tool(path, name)
        with subprocess.Popen(  # noqa: S603 - an argument list of checked values, no shell
            [str(path), *args],
            env=sacct_env(path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        ) as proc:
            timer = threading.Timer(TIMEOUT_S, _kill, (proc,))
            timer.start()
            try:
                data = proc.stdout.read(MAX_OUTPUT + 1) if proc.stdout else b""
                if len(data) > MAX_OUTPUT:
                    _kill(proc)
                code = proc.wait()
            finally:
                timer.cancel()
    except (Refused, OSError):
        return None
    if code != 0 or len(data) > MAX_OUTPUT:
        return None
    return data.decode("utf-8", "replace")


# --- Parsing ------------------------------------------------------------------------------


def _minutes(text: str) -> int | None:
    """A `%l` time limit in minutes, a started minute counting; None for `infinite`, or for a
    text that is no SLURM time (`MM`, `MM:SS`, `HH:MM:SS`, `D-HH[:MM[:SS]]`)."""
    days, dash, rest = text.rpartition("-")
    parts = rest.split(":")
    if not all(p.isdecimal() and len(p) <= 5 for p in parts) or (dash and not days.isdecimal()):
        return None
    units = (3600, 60, 1) if dash else {1: (60,), 2: (60, 1), 3: (3600, 60, 1)}.get(len(parts), ())
    if len(parts) > len(units):
        return None
    seconds = int(days or 0) * 86400 + sum(int(p) * u for p, u in zip(parts, units, strict=False))
    return -(-seconds // 60)


def parse_gres(text: str) -> list[dict[str, Any]]:
    """The GPUs of a `%G` text: `gpu:H100:4(S:0-1)` is type H100, count 4; `gpu:4` has no type.
    Other generic resources are not offered."""
    gpus = []
    for item in re.sub(r"\([^)]*\)", "", text).split(","):
        parts = item.strip().split(":")
        if parts[0] != "gpu" or len(parts) < 2 or not _COUNT.fullmatch(parts[-1]):
            continue
        kind = parts[1] if len(parts) > 2 and _NAME.fullmatch(parts[1]) else None
        gpus.append({"type": kind, "count": int(parts[-1])})
    return gpus


def parse_sinfo(text: str) -> dict[str, dict[str, Any]]:
    """Partition name → `{default, max_time_min, groups}`; a line that does not split into the
    format's fields, or holds a value of another shape, is dropped."""
    found: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        fields = line.strip().split("|")
        if len(fields) != _FIELDS:
            continue
        name, limit, nodes, cpus, mem, features, gres, state = fields
        default = name.endswith("*")
        name = name.rstrip("*")
        cpus, mem = cpus.rstrip("+"), mem.rstrip("+")
        if not (_NAME.fullmatch(name) and all(_COUNT.fullmatch(v) for v in (nodes, cpus, mem))):
            continue
        names = [] if features == "(null)" else features.split(",")
        if not all(_FEATURE.fullmatch(n) for n in names):
            continue
        part = found.setdefault(
            name, {"default": False, "max_time_min": _minutes(limit), "groups": {}}
        )
        part["default"] = part["default"] or default
        key = (int(cpus), int(mem), tuple(names), gres)
        group = part["groups"].setdefault(
            key,
            {
                "nodes": 0,
                "idle": 0,
                "cpus": int(cpus),
                "mem_mib": int(mem),
                "features": names,
                "gpus": parse_gres(gres),
            },
        )
        group["nodes"] += int(nodes)
        group["idle"] += int(nodes) if state in _IDLE else 0
    for part in found.values():
        part["groups"] = list(part["groups"].values())
    return found


def _limit(values: dict[str, str], key: str) -> set[str] | None:
    value = values.get(key, "ALL")
    return None if value in ("ALL", "") else set(value.split(","))


def parse_scontrol(text: str) -> dict[str, dict[str, Any]]:
    """Partition name → `{default, accounts, groups}` from `show partition --oneliner`; `accounts`
    and `groups` are None for `ALL` (no limit)."""
    found = {}
    for line in text.splitlines():
        values = dict(w.split("=", 1) for w in line.split() if "=" in w)
        name = values.get("PartitionName", "")
        if _NAME.fullmatch(name):
            found[name] = {
                "default": values.get("Default") == "YES",
                "accounts": _limit(values, "AllowAccounts"),
                "groups": _limit(values, "AllowGroups"),
            }
    return found


def parse_assoc(text: str) -> list[tuple[str, str]]:
    """The `(account, partition)` pairs of the user's associations; an empty partition is any."""
    found = []
    for line in text.splitlines():
        account, _, partition = line.strip().partition("|")
        if _NAME.fullmatch(account) and (not partition or _NAME.fullmatch(partition)):
            found.append((account, partition))
    return found


def _my_groups() -> set[str]:
    names = set()
    for gid in {os.getgid(), *os.getgroups()}:
        with contextlib.suppress(KeyError):
            names.add(grp.getgrgid(gid).gr_name)
    return names


def assemble(
    sinfo: str, scontrol: str | None, assoc: str | None, now: datetime | None = None
) -> dict[str, Any]:
    """The contract's body from the three outputs (`scontrol` and `assoc` may be missing)."""
    parts = parse_sinfo(sinfo)
    rules = parse_scontrol(scontrol or "")
    pairs = parse_assoc(assoc or "")
    accounts = list(dict.fromkeys(a for a, _ in pairs))
    mine = _my_groups()
    out = []
    for name, part in parts.items():
        rule = rules.get(name, {"default": False, "accounts": None, "groups": None})
        usable = {a for a, p in pairs if p in ("", name)}
        allowed = (
            (rule["accounts"] is None or not pairs or bool(usable & rule["accounts"]))
            and (not pairs or bool(usable))
            and (rule["groups"] is None or bool(mine & rule["groups"]))
        )
        out.append(
            {
                "name": name,
                "default": part["default"] or rule["default"],
                "allowed": allowed,
                "max_time_min": part["max_time_min"],
                "groups": part["groups"],
            }
        )
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"scheduler": "slurm", "fetched_at": stamp, "partitions": out, "accounts": accounts}


NONE: dict[str, Any] = {"scheduler": None, "fetched_at": None, "partitions": [], "accounts": []}


class Facts:
    """The facts, asked at most once per TTL_S. `run(name, args)` is the command runner; a test
    replaces it."""

    def __init__(self, settings: Settings, clock: Callable[[], float] = time.monotonic) -> None:
        self.run: Callable[[str, list[str]], str | None] = lambda name, args: run_tool(
            settings, name, args
        )
        self._clock = clock
        self._lock = threading.Lock()
        self._kept: tuple[float, dict[str, Any]] | None = None

    def get(self) -> dict[str, Any]:
        with self._lock:
            now = self._clock()
            if self._kept is not None and now < self._kept[0]:
                return self._kept[1]
            facts = self._ask()
            self._kept = (now + (TTL_S if facts["scheduler"] else FAILED_TTL_S), facts)
            return facts

    def _ask(self) -> dict[str, Any]:
        sinfo = self.run("sinfo", ["--noheader", "-o", SINFO_FORMAT])
        if sinfo is None:
            return NONE
        scontrol = self.run("scontrol", ["show", "partition", "--oneliner"])
        user = _user()
        assoc = (
            None
            if user is None
            else self.run(
                "sacctmgr",
                [
                    "--noheader",
                    "--parsable2",
                    "show",
                    "assoc",
                    f"user={user}",
                    "format=account,partition",
                ],
            )
        )
        return assemble(sinfo, scontrol, assoc)


def _user() -> str | None:
    try:
        name = pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        return None
    return name if _NAME.fullmatch(name) else None
