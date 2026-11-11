"""Spectio's Snakemake logger plugin: each log record becomes one spool event (P1 Task 7).

Ported from spike T2 (`spikes/engine-events/snakemake/snakemake_logger_plugin_spectio/__init__.py`
on branch `spike/engine-events`; docs/research/spike-engine-events-2026-10-28.md) and hardened.
The spool format is api-and-data-model.md §14.1; its reader and models are `spectio_sdk.events`.

- Discovered by its module name through `PYTHONPATH` (`--logger spectio`), with no install
  (`snakemake_interface_logger_plugins.registry`, interface 1.1.0 to 2.x).
- Driven, or started from a terminal (P1 Task 25, architecture §13.8): with none of
  SPECTIO_RUN_ID, SPECTIO_LAUNCH_N, SPECTIO_SPOOL_DIR set, it makes a run ID, writes the spool in
  `<launch dir>/.spectio/events/` as `<run ID>-<producer>-<nnnn>.jsonl`, and a pointer
  `~/.spectio/observed/<run ID>.json` when `~/.spectio/` exists; with one variable missing or
  invalid it says so once on stderr and writes nothing.
- Added, never replacing: it writes to no stream and no file Snakemake knows of, so Snakemake
  keeps its own stderr output and `.snakemake/log/` file (`writes_to_file = False`: with True,
  Snakemake reads `baseFilename`, which the interface does not declare; T2 note, row 21).
- Each type keeps only the keys of its §14.1 allow-list; nothing is read from the environment
  but the three variables above. Strings, lists and maps are cut (`MAX_TEXT_CHARS`, `MAX_ITEMS`,
  `MAX_DEPTH`) and a line never passes `MAX_LINE_BYTES`.
- The spool (dev-env §15.3 req. 12): `.spectio/` (made 0700 for a terminal run) and `events/`
  (made 0700) each opened with O_NOFOLLOW and used only when a directory of the user with no group
  or other bits; `bridge.err` and each spool file created relative to those descriptors with
  O_NOFOLLOW, 0600, a spool file with an exclusive create, never one another writer made; one
  `write(2)` per line on an `O_APPEND` descriptor; a failed write is cut back to the last full
  line. Nothing it does raises into Snakemake: an unwritable or full spool loses events, never
  the run. Records reach `emit` on Snakemake's QueueListener thread, so a slow disk does not
  hold the workflow's main thread either (snakemake 9.27.1 `logging.py:671-679`).

Stdlib and the interface only.
"""

import contextlib
import json
import logging
import os
import re
import secrets
import socket
import stat
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snakemake_interface_logger_plugins.base import LogHandlerBase
from snakemake_interface_logger_plugins.settings import LogHandlerSettingsBase

VERSION = "0.0.1"
NAME = "snakemake-logger-spectio"
PRODUCER = f"{NAME}/{VERSION}"

# api §14.1 (spectio_sdk.events): the writer's bounds.
MAX_LINE_BYTES = 65536  # one line, without its "\n"
ROTATE_BYTES = 33554432  # the next file is opened before a line would pass it
MAX_MESSAGE_CHARS = 4096  # error texts, as the server cuts them
_PARAMS_CHANGED = "Params have changed since last execution"  # = spectio_sdk.events
LAST_INDEX = 9999  # spool files nnnn = 0001 … 9999

# The plugin's own bounds on what one value may hold.
MAX_TEXT_CHARS = 4096  # one string (PATH_MAX on Linux)
MAX_ITEMS = 512  # items of one list, keys of one map
MAX_DEPTH = 8  # nesting; deeper values become their text
MAX_ERROR_LINES = 100  # lines in bridge.err

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_RUN_ID = re.compile(r"run_[0-7][0-9A-HJKMNP-TV-Z]{25}")
_LAUNCH_N = re.compile(r"[1-9][0-9]{0,18}")
_INT64 = 2**63 - 1
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ENV = ("SPECTIO_RUN_ID", "SPECTIO_LAUNCH_N", "SPECTIO_SPOOL_DIR")

# The SLURM executor plugin's info text on each submission, `snakemake-executor-plugin-slurm`
# 2.8.0, `snakemake_executor_plugin_slurm/__init__.py:1224-1227` (read in the 2.8.0 wheel,
# 2026-11-01): f"Job {job.jobid} has been submitted with SLURM jobid {slurm_jobid} (log:
# {slurm_logfile})." Versioned with that release; other releases [to be validated], and the
# live text on a cluster with P1 Task 22 (`slurm-mini`).
SLURM_SUBMITTED = re.compile(
    r"Job (?P<jobid>[0-9]{1,19}) has been submitted with SLURM jobid "
    r"(?P<external>[^\s()]{1,128}) \(log: (?P<log>[^\n]{1,4096})\)\."
)

# Snakemake 9.27.1's own untyped info texts (read at the tag v9.27.1, 2026-11-07; research note
# dag-temp-slurm-efficiency-2026-11-07 §2-§3), each read as a whole message. A text another
# release words otherwise matches none and stays a `snakemake.log` (api §14.1). The dry run's
# "Would remove temporary output <path>" (`dag.py:1048-1051`) is not read.
SNAKEMAKE_TEXTS_VERSION = "9.27.1"
SNAKEMAKE_TEXTS = {
    # `dag.py:1054-1056`, in `handle_temp`
    "snakemake.temp_removed": re.compile(r"Removing temporary output (?P<path>[^\n]{1,4096})\."),
    # `dag.py:932-936`, in `handle_protected`
    "snakemake.protected": re.compile(r"Write-protecting output file (?P<path>[^\n]{1,4096})\."),
    # `dag.py:2245`, in `update_checkpoint_dependencies`
    "snakemake.dag_updated": re.compile(r"Updating checkpoint dependencies\."),
}
MAX_TEMP_PATHS = 65536  # paths remembered to send each removal once; past it, every one is sent


# --- Values --------------------------------------------------------------------------------


def _text(value: object, limit: int = MAX_TEXT_CHARS) -> str:
    """A string the spool reader accepts: cut, no NUL, no lone surrogate."""
    text = str(value)[:limit].replace("\x00", "�")
    return text.encode("utf-8", "replace").decode("utf-8")


def _int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and -_INT64 - 1 <= value <= _INT64:
        return value
    return None


def _count(value: object) -> int | None:
    found = _int(value)
    return found if found is not None and found >= 0 else None


def _bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _opt_text(value: object) -> str | None:
    return None if value is None else _text(value)


def _texts(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [_text(item) for item in value[:MAX_ITEMS]]


def _plain(value: object, depth: int = 1) -> Any:
    """JSON for any value: a Namedlist (`resources`) becomes a map, a UUID or a path its text."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if _int(value) is not None else _text(value)
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    if isinstance(value, str) or depth >= MAX_DEPTH:
        return _text(value)
    named = getattr(value, "_names", None) is not None and callable(getattr(value, "items", None))
    if named or isinstance(value, Mapping):
        items = list(value.items())[:MAX_ITEMS]  # type: ignore[attr-defined]
        return {_text(k, 256): _plain(v, depth + 1) for k, v in items}
    if isinstance(value, list | tuple | set | frozenset):
        return [_plain(v, depth + 1) for v in list(value)[:MAX_ITEMS]]
    return _text(value)


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    """Without the keys whose value is unknown: the models default them."""
    return {k: v for k, v in data.items() if v is not None}


# --- One builder per Snakemake event: the keys of its §14.1 allow-list ----------------------


def _workflow_started(r: Any) -> dict[str, Any]:
    keys = ("workflow_id", "snakemake_version", "rundir", "host", "user", "snakefile_main")
    data = _compact({k: _opt_text(getattr(r, k, None)) for k in keys})
    target = run_target(sys.argv[1:])
    if target is not None:
        data["target"] = target
    return data


_RULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
_MAX_TARGET = 4096


def run_target(argv: list[str]) -> dict[str, Any] | None:
    """The rule or file this run is limited to (api §5.10, architecture §13.8), from Snakemake's
    own argument parser: the first target, else `--until`, else `--allowed-rules`; a lone `all`
    is the whole pipeline. A name that looks like a rule is a rule, anything else a file. The
    command line itself is never sent; None when it cannot be read."""
    try:
        from snakemake.cli import get_argument_parser

        args, _ = get_argument_parser().parse_known_args(argv)
    except (Exception, SystemExit):  # argparse exits on what it cannot read
        return None
    for flag, given in (
        ("target", getattr(args, "targets", None)),
        ("until", getattr(args, "until", None)),
        ("allowed_rules", getattr(args, "allowed_rules", None)),
    ):
        names = [str(n) for n in given or []]
        if flag == "target" and names == ["all"]:
            continue
        if names:
            name = names[0][:_MAX_TARGET]
            kind = "rule" if _RULE.fullmatch(name) else "file"
            return {"kind": kind, "name": name, "flag": flag, "more": len(names) - 1}
    return None


def _run_info(r: Any) -> dict[str, Any]:
    stats = _plain(getattr(r, "stats", None))
    if not isinstance(stats, dict):
        return {}
    return {"stats": {k: v for k, v in stats.items() if _count(v) is not None}}


def _resources_info(r: Any) -> dict[str, Any]:
    return _compact({"cores": _count(getattr(r, "cores", None))})


def _rulegraph(r: Any) -> dict[str, Any]:
    graph = _plain(getattr(r, "rulegraph", None))
    return {"rulegraph": graph} if isinstance(graph, dict) else {}


def _job_files(r: Any) -> dict[str, Any]:
    return {
        "jobid": _count(getattr(r, "jobid", None)),
        "rule_name": _opt_text(getattr(r, "rule_name", None)),
        "input": _texts(getattr(r, "input", None)),
        "output": _texts(getattr(r, "output", None)),
        "log": _texts(getattr(r, "log", None)),
    }


def _job_info(r: Any) -> dict[str, Any]:
    wildcards = _plain(getattr(r, "wildcards", None))
    resources = _plain(getattr(r, "resources", None))
    custom = None
    if isinstance(resources, dict):
        # Raw sbatch flags (SEC-P3T1-11): the server drops them too; they are never sent, only
        # whether they were set (P1 Task 34).
        custom = bool(resources.pop("slurm_extra", None))
    # The "Params have changed" detail quotes param values (SEC-P3T1-08): cut after the marker,
    # as the server cuts it (`SnakemakeJobInfo._cut_params_detail`).
    reason = _opt_text(getattr(r, "reason", None))
    if reason is not None:
        head, marker, _ = reason.partition(_PARAMS_CHANGED)
        reason = head + marker
    return _compact(
        {
            **_job_files(r),
            "wildcards": (
                {k: _text(v) for k, v in wildcards.items()} if isinstance(wildcards, dict) else {}
            ),
            "benchmark": _opt_text(getattr(r, "benchmark", None)),
            "reason": reason,
            "is_checkpoint": _bool(getattr(r, "is_checkpoint", None)),
            "is_handover": _bool(getattr(r, "is_handover", None)),
            "local": _bool(getattr(r, "local", None)),
            "priority": _int(getattr(r, "priority", None)),  # "highest" is not sent
            "threads": _count(getattr(r, "threads", None)),
            "resources": resources if isinstance(resources, dict) else {},
            "custom_options": custom,
        }
    )


def _job_error(r: Any) -> dict[str, Any]:
    # `aux` holds the executor's keyword arguments: only its job ID is sent
    # (`snakemake-interface-executor-plugins` 9.4.0, `remote.py:259-267`). The executor's
    # error text is the record's `rule_msg` (snakemake 9.27.1 `jobs.py:1111-1150`), sent as
    # `msg`: the server parses it and never stores it (api §14.1, P1 Task 29).
    aux = getattr(r, "aux", None)
    job = aux.get("external_jobid") if isinstance(aux, Mapping) else None
    external = _count(job) if isinstance(job, int) else _opt_text(job)
    return _compact(
        {
            **_job_files(r),
            "aux": {"external_jobid": external} if external is not None else None,
            "msg": _opt_text(getattr(r, "rule_msg", None)),
        }
    )


def _job_started(r: Any) -> dict[str, Any]:
    jobs = getattr(r, "jobs", None)
    found = [_count(j) for j in jobs[:MAX_ITEMS]] if isinstance(jobs, list | tuple) else []
    return {"jobs": [j for j in found if j is not None]}


def _job_finished(r: Any) -> dict[str, Any]:
    return _compact({"job_id": _count(getattr(r, "job_id", None))})


def _progress(r: Any) -> dict[str, Any]:
    return _compact({k: _count(getattr(r, k, None)) for k in ("done", "total")})


def _error(r: Any) -> dict[str, Any]:
    # The server hides the quoted command before storing it (api §14.1, `snakemake.error`).
    return _compact({"exception": _opt_text(getattr(r, "exception", None)), "msg": _message(r)})


def _message(r: logging.LogRecord) -> str | None:
    try:
        return None if r.msg is None else _text(r.getMessage(), MAX_MESSAGE_CHARS)
    except Exception:
        return None


_EVENTS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "workflow_started": _workflow_started,
    "run_info": _run_info,
    "resources_info": _resources_info,
    "rulegraph": _rulegraph,
    "job_info": _job_info,
    "job_started": _job_started,
    "job_finished": _job_finished,
    "job_error": _job_error,
    "shellcmd": lambda r: {},  # kept as a record; the job's command is not
    "progress": _progress,
    "error": _error,
}


# The keys the models require: an event without one would be refused, so it is sent as a log.
_REQUIRED = {
    "job_info": ("jobid", "rule_name"),
    "job_finished": ("job_id",),
    "job_error": ("jobid",),
    "progress": ("done", "total"),
}


def slurm_submitted(message: str) -> dict[str, Any] | None:
    """`snakemake.slurm_submitted` from the SLURM executor plugin's submission text, or None."""
    found = SLURM_SUBMITTED.fullmatch(message)
    if found is None:
        return None
    return {
        "jobid": int(found["jobid"]),
        "external_jobid": found["external"],
        "log": found["log"],
    }


def read_text(message: str) -> tuple[str, dict[str, Any]] | None:
    """The event an untyped info text reports: a SLURM submission or one of SNAKEMAKE_TEXTS."""
    submitted = slurm_submitted(message)
    if submitted is not None:
        return "snakemake.slurm_submitted", submitted
    for type_, pattern in SNAKEMAKE_TEXTS.items():
        found = pattern.fullmatch(message)
        if found is not None:
            return type_, found.groupdict()
    return None


def to_events(record: logging.LogRecord) -> list[tuple[str, dict[str, Any]]]:
    """The spool events of one record: `snakemake.<event>`, or `snakemake.log` (its level
    only) for a record with no event, one §14.1 does not list or one missing a required key;
    after it, for an untyped record, the event its text reports, if any (`read_text`)."""
    event = getattr(record, "event", None)
    build = _EVENTS.get(str(event)) if event is not None else None
    if build is not None:
        data = build(record)
        if all(k in data for k in _REQUIRED.get(str(event), ())):
            return [(f"snakemake.{event}", data)]
    found: list[tuple[str, dict[str, Any]]] = [("snakemake.log", {"level": record.levelname})]
    message = _message(record) if event is None else None
    read = read_text(message) if message else None
    if read is not None:
        found.append(read)
    return found


# --- The spool -----------------------------------------------------------------------------


def _ulid(ms: int) -> str:
    n = (ms << 80) | secrets.randbits(80)
    return "".join(_CROCKFORD[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def _private_dir(name: str | Path, dir_fd: int | None = None, create: bool = False) -> int:
    """`name` (relative to `dir_fd`), made 0700 when `create`; refused unless a directory of
    this user that group and others cannot use, and never through a symlink."""
    if create:
        with contextlib.suppress(FileExistsError):
            os.mkdir(name, 0o700, dir_fd=dir_fd)
    fd = os.open(name, _DIR_FLAGS, dir_fd=dir_fd)
    st = os.fstat(fd)
    if st.st_uid != os.geteuid() or st.st_mode & 0o077:
        os.close(fd)
        raise PermissionError(
            f"{name} is not a private directory of yours "
            f"(uid {st.st_uid}, mode {stat.filemode(st.st_mode)})"
        )
    return fd


class Spool:
    """The append-only spool of one launch (api §14.1). `write` never raises. `terminal`: a
    run started from a terminal, whose `.spectio/` is made here and whose files carry its run
    ID (architecture §13.8)."""

    def __init__(self, directory: Path, run: str, launch: int, terminal: bool = False) -> None:
        self.directory = directory
        self.run = run
        self.launch = launch
        self.terminal = terminal
        self.seq = 0
        self.parent_fd: int | None = None  # `.spectio`, which holds bridge.err
        self.dir_fd: int | None = None
        self.fd: int | None = None
        self.size = 0
        self.index = 0
        self.broken = False  # the directory was refused: nothing more is tried
        self.errors = 0

    def start(self) -> bool:
        """Open `.spectio` and `events`, once; False, with one line said, when refused."""
        if self.dir_fd is not None or self.broken:
            return not self.broken
        try:
            self.parent_fd = _private_dir(self.directory.parent, create=self.terminal)
            self.dir_fd = _private_dir(self.directory.name, self.parent_fd, create=True)
        except OSError as e:  # read-only, refused, a symlink: no event of this launch
            self.broken = True
            self.error(f"the spool directory is refused, no events are written: {e}")
        return not self.broken

    def write(self, type_: str, data: dict[str, Any], created: float) -> None:
        if self.broken:
            return
        ms = int(created * 1000)
        line = self._line(type_, data, ms)
        if line is None and type_ in ("snakemake.job_info", "snakemake.job_error"):
            line = self._line(type_, {**data, "input": [], "output": []}, ms)
        if not self.start():
            return
        if line is None:
            self.error(f"{type_}: line over {MAX_LINE_BYTES} bytes, dropped")
            return
        try:
            fd = self.fd
            if fd is None or self.size + len(line) > ROTATE_BYTES:
                fd = self._next()
            view = memoryview(line)
            while view:
                view = view[os.write(fd, view) :]
            self.size += len(line)
            self.seq += 1
        except OSError as e:
            # ENOSPC, EDQUOT, EFBIG: cut the partial line off and keep the file; a new file per
            # event would burn the indexes (as nf-spectio, CR-P3T06-01, CR-P3T06-02).
            self.error(f"{type_}: not written: {e}")
            self._cut_back()

    def _line(self, type_: str, data: dict[str, Any], ms: int) -> bytes | None:
        envelope = {
            "v": 1,
            "id": "evt_" + _ulid(ms),
            "run": self.run,
            "launch": self.launch,
            "producer": PRODUCER,
            "seq": self.seq + 1,
            "time": datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="milliseconds")[:-6]
            + "Z",
            "type": type_,
            "data": data,
        }
        line = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode()
        return line + b"\n" if len(line) <= MAX_LINE_BYTES else None

    def _cut_back(self) -> None:
        if self.fd is None:
            return
        try:
            os.ftruncate(self.fd, self.size)
            if os.fstat(self.fd).st_nlink == 0:  # the file is gone: open the next one
                self._close_file()
        except OSError:
            self._close_file()

    def _next(self) -> int:
        """The next file that does not exist yet, opened; the current one while it is empty."""
        if self.fd is not None and self.size == 0:
            return self.fd
        self._close_file()
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        while self.index < LAST_INDEX:
            # Another error (EACCES, EDQUOT) leaves the index for the next event (as nf-spectio).
            n = self.index + 1
            name = (
                f"{self.run}-{NAME}-{n:04d}.jsonl"
                if self.terminal
                else f"{NAME}-{self.launch}-{n:04d}.jsonl"
            )
            try:
                fd = os.open(name, flags, 0o600, dir_fd=self.dir_fd)
            except FileExistsError:
                self.index += 1
                continue
            self.index += 1
            self.fd, self.size = fd, 0
            return fd
        raise OSError("no spool file index left")

    def _close_file(self) -> None:
        if self.fd is not None:
            with contextlib.suppress(OSError):
                os.close(self.fd)
        self.fd = None

    def close(self) -> None:
        self._close_file()
        for fd in (self.dir_fd, self.parent_fd):
            if fd is not None:
                with contextlib.suppress(OSError):
                    os.close(fd)
        self.dir_fd = self.parent_fd = None

    def error(self, message: str) -> None:
        """One line in `.spectio/bridge.err`, at most MAX_ERROR_LINES of them; on stderr when
        `.spectio` itself was refused (nothing is written in it)."""
        self.errors += 1
        if self.errors > MAX_ERROR_LINES:
            return
        line = f"{datetime.now(UTC).isoformat()} {NAME}: {_text(message, 1024)}\n".encode()
        if not self.broken:
            self.start()  # a record that failed before its first write (once: start sets broken)
        try:
            if self.parent_fd is None:
                raise OSError("no checked .spectio directory")
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
            fd = os.open("bridge.err", flags | os.O_CLOEXEC, 0o600, dir_fd=self.parent_fd)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):  # a FIFO or device: never written
                    raise OSError("bridge.err is not a regular file")
                os.write(fd, line)
            finally:
                os.close(fd)
        except OSError:
            _stderr(message)


def _stderr(message: str) -> None:
    with contextlib.suppress(Exception):  # a closed stderr loses the line, not the run
        print(f"{NAME}: {message}", file=sys.stderr)


def _head_pid() -> dict[str, Any]:
    """The PID fields of the head's PID file (schedulers §3.1.1): this process is the head."""
    fields = Path("/proc/self/stat").read_text().rsplit(") ", 1)[1].split()
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return {"pid": os.getpid(), "pid_start_time": fields[19], "boot_id": boot_id}


def _engine_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("snakemake")
    except Exception:
        return None


def write_pointer(spool: Spool, home: Path) -> None:
    """`~/.spectio/observed/<run ID>.json` (architecture §13.8), 0600, created under a
    temporary name, then renamed; only when `~/.spectio/` and `observed/` (made 0700) are
    private directories of the user (req. 12). No `~/.spectio/`: no pointer, silently. Any
    other error is said once and swallowed (architecture §13.3)."""
    name = f"{spool.run}.json"
    fds: list[int] = []
    try:
        fds.append(os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC))
        try:
            fds.append(_private_dir(".spectio", fds[-1]))
        except FileNotFoundError:
            return  # Spectio is not installed: the spool only
        fds.append(_private_dir("observed", fds[-1], create=True))
        data = {
            "run_id": spool.run,
            "launch_dir": str(spool.directory.parent.parent),
            "engine": "snakemake",
            "engine_version": _engine_version(),
            "bridge_version": VERSION,
            "host": socket.gethostname(),
            **_head_pid(),
        }
        tmp = f".{name}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(tmp, flags, 0o600, dir_fd=fds[-1])
        try:
            os.write(fd, json.dumps(data).encode())
        finally:
            os.close(fd)
        os.rename(tmp, name, src_dir_fd=fds[-1], dst_dir_fd=fds[-1])
    except Exception as e:  # never into Snakemake
        spool.error(f"no pointer written in ~/.spectio/observed: {e}")
    finally:
        for fd in fds:
            os.close(fd)


def terminal_spool(launch_dir: Path) -> Spool:
    """A run started from a terminal: a new run ID, its spool in `launch_dir`, launch 1."""
    run = "run_" + _ulid(int(time.time() * 1000))
    return Spool(launch_dir / ".spectio" / "events", run, 1, terminal=True)


def spool_from_env(env: Mapping[str, str]) -> Spool | None:
    """The launch's spool: a driven run's, or one started from a terminal (nothing set); None
    when the variables are wrong (one line on stderr)."""
    values = [env.get(name, "") for name in _ENV]
    if not any(values):
        try:
            return terminal_spool(Path.cwd())
        except OSError as e:  # the launch directory is gone: no events, never a failed run
            _stderr(f"no launch directory: {e}")
            return None
    run, launch, directory = values
    if not _RUN_ID.fullmatch(run):
        problem = "SPECTIO_RUN_ID is not run_ and a ULID"
    elif not _LAUNCH_N.fullmatch(launch):
        problem = "SPECTIO_LAUNCH_N is not a launch number"
    elif not os.path.isabs(directory):
        problem = "SPECTIO_SPOOL_DIR is not an absolute path"
    else:
        return Spool(Path(directory), run, int(launch))
    _stderr(f"{problem}: no events are written")
    return None


# --- The plugin ----------------------------------------------------------------------------


@dataclass
class LogHandlerSettings(LogHandlerSettingsBase):
    """No settings. The registry reads this name (`registry/__init__.py`, interface 2.1.0)."""


class LogHandler(LogHandlerBase):
    def __post_init__(self) -> None:
        if not hasattr(self, "filters"):  # interface 1.x does not initialise the Handler
            logging.Handler.__init__(self)
        self.spool = spool_from_env(os.environ)
        self.temp_removed: set[str] = set()  # Snakemake logs some removals twice (T2, row 19)
        if self.spool is not None and self.spool.terminal and self.spool.start():
            write_pointer(self.spool, Path(os.path.expanduser("~")))

    def emit(self, record: logging.LogRecord) -> None:
        spool = self.spool
        if spool is None:
            return
        try:
            for type_, data in to_events(record):
                if type_ == "snakemake.temp_removed":
                    if data["path"] in self.temp_removed:
                        continue
                    if len(self.temp_removed) < MAX_TEMP_PATHS:
                        self.temp_removed.add(data["path"])
                spool.write(type_, data, record.created)
        except Exception as e:  # never into Snakemake: a lost event, not a lost run
            spool.error(f"record not written: {type(e).__name__}: {e}")

    def close(self) -> None:
        if self.spool is not None:
            self.spool.close()
        super().close()

    @property
    def writes_to_stream(self) -> bool:
        return False

    @property
    def writes_to_file(self) -> bool:
        return False

    @property
    def has_filter(self) -> bool:
        return True  # every record, also those --quiet would hide (synthesis §2bis)

    @property
    def has_formatter(self) -> bool:
        return True

    @property
    def needs_rulegraph(self) -> bool:
        return True
