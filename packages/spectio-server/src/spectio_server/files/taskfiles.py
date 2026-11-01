"""Each job's files (P1 Task 28; architecture §13.7, api §5 note 2026-10-28 "Job files",
dev-env §15.3 req. 13).

Nextflow: the files of the allow-list below, in the attempt's work directory, which must be two
levels below the run's work directory (`<2 hex>/<30 hex>`, as Nextflow makes it). Snakemake: the
rule's `log:` files and the SLURM job log, by the paths the attempt's events recorded, relative
to the launch directory. The roots come from the runs root and the run ID (req. 10), never from
a stored path; a stored path is checked again here, as the projector checked it.

`task_work_rel` and `launch_rel` are the checks of a path from an event; the projector keeps a
path only when they accept it. Nothing here touches the database, and every function that reads
the file system is meant to run in the file pool (`files.pool`).
"""

import os
import re
import stat
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from spectio.runner.rundir import open_private, run_paths
from spectio_server.files.confine import (
    MAX_READ,
    TAIL,
    NotAllowed,
    NotFound,
    Root,
    open_confined,
    read_at,
    safe_rel,
    size_of,
    stat_confined,
    tail,
)
from spectio_server.files.redact import redact_command_run, strip_escapes

Kind = Literal[
    "script",
    "wrapper",
    "stdout",
    "stderr",
    "job_log",
    "exit",
    "marker",
    "trace",
    "rule_log",
    "slurm_log",
]
State = Literal["present", "not_yet", "absent", "deleted_after_success", "cleaned"]

# The Nextflow files served, in this order (TaskRun.groovy:583-593, v26.10.4); everything else
# in a work directory is not (`.command.env`, `.command.in`, `.command.stage`, staged inputs).
NF_FILES: dict[str, Kind] = {
    ".command.sh": "script",
    ".command.run": "wrapper",
    ".command.out": "stdout",
    ".command.err": "stderr",
    ".command.log": "job_log",
    ".exitcode": "exit",
    ".command.begin": "marker",
    ".command.trace": "trace",
}
SPECTIO_SERVED = frozenset({"head.out", "head.err", "nextflow.log"})  # all else in .spectio/
SLURM_LOGS = PurePosixPath(".snakemake/slurm_logs")
OPEN_STATES = frozenset({"pending", "submitted", "running"})
SNIFF = 8192  # a NUL in these first bytes makes it a binary file
_HASH = (re.compile(r"[0-9a-f]{2}"), re.compile(r"[0-9a-f]{30}"))
_ARRAY_TASK = re.compile(r"[0-9]+_[0-9]+")
_NATIVE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}")  # a SLURM ID, a PID, a pod

MAY_SHOW = "May show values from your parameters or environment."
NOTES: dict[str, str] = {
    ".command.sh": MAY_SHOW,
    ".command.log": MAY_SHOW,
    ".command.run": "The value of every variable is hidden.",
}


class Binary(Exception):
    """The file holds a NUL byte near its start: not shown as text."""


class Cleaned(NotFound):
    """The work directory, or the launch directory, is gone."""


@dataclass(frozen=True)
class AttemptFiles:
    """What the files of one attempt are found from: its run, engine and state, and the paths
    its events recorded."""

    run_id: str
    engine: str
    state: str
    work_dir: str | None  # Nextflow: the attempt's work directory, as recorded
    native_id: str | None
    logs: tuple[tuple[str, str], ...]  # Snakemake: (path relative to the launch dir, kind)
    runs_root: Path


@dataclass(frozen=True)
class TaskFile:
    name: str
    kind: Kind
    size: int | None
    mtime: float | None
    state: State
    note: str | None


@dataclass(frozen=True)
class Served:
    text: str
    start: int  # of the bytes read, in the file (or in the hidden `.command.run`)
    end: int  # past the last byte read
    size: int
    partial: bool  # a Range answer


# --- Paths from events (the projector's checks) --------------------------------------------


def _under(base: Path, value: str) -> PurePosixPath | None:
    """`value`, an absolute path, relative to `base`, or None; every part a plain name."""
    prefix = str(base).rstrip("/") + "/"
    if not value.startswith(prefix):
        return None
    try:
        return safe_rel(value[len(prefix) :])
    except NotAllowed:
        return None


def task_work_rel(run_work_dir: Path, value: str) -> PurePosixPath | None:
    """The task work directory `value` relative to the run's, when it is `<2 hex>/<30 hex>`
    below it; None otherwise."""
    rel = _under(run_work_dir, value)
    if rel is None or len(rel.parts) != 2:
        return None
    if not all(p.fullmatch(part) for p, part in zip(_HASH, rel.parts, strict=True)):
        return None
    return rel


def launch_rel(launch_dir: Path, value: str) -> PurePosixPath | None:
    """A Snakemake log path (relative to the launch directory, or absolute in it) as a
    relative path, or None: outside the launch directory, or a `.spectio/` file not served."""
    if value.startswith("/"):
        rel = _under(launch_dir, value)
    else:
        try:
            rel = safe_rel(value)
        except NotAllowed:
            rel = None
    if rel is None or (rel.parts[0] == ".spectio" and not _spectio_served(rel)):
        return None
    return rel


def _spectio_served(rel: PurePosixPath) -> bool:
    return len(rel.parts) == 2 and rel.parts[1] in SPECTIO_SERVED


def native_id(value: object) -> str | None:
    """An executor's job ID from an event, as text, or None when it is not one."""
    if isinstance(value, bool) or not isinstance(value, str | int):
        return None
    text = str(value)
    return text if _NATIVE_ID.fullmatch(text) else None


def log_kind(rel: PurePosixPath) -> Kind:
    return "slurm_log" if rel.is_relative_to(SLURM_LOGS) else "rule_log"


# --- Roots ------------------------------------------------------------------------------------


@contextmanager
def run_root(runs_root: Path, run_id: str, part: str) -> Iterator[Root]:
    """The run's launch or work directory, private (req. 10); Cleaned when it is gone."""
    paths = run_paths(runs_root, run_id)
    try:
        fd = open_private(runs_root, (run_id, part))
    except FileNotFoundError:
        raise Cleaned(f"the run's {part} directory is gone") from None
    except (OSError, ValueError) as exc:
        raise NotAllowed(f"the run's {part} directory is not private: {exc}") from None
    try:
        yield Root(fd, PurePosixPath(paths.launch_dir if part == "launch" else paths.work_dir))
    finally:
        os.close(fd)


def attempt_dir(attempt: AttemptFiles) -> str | None:
    """The directory to show (and copy): the work directory, or the launch directory."""
    if attempt.engine == "snakemake":
        return str(run_paths(attempt.runs_root, attempt.run_id).launch_dir)
    return attempt.work_dir


def _work_rel(attempt: AttemptFiles) -> PurePosixPath | None:
    if attempt.work_dir is None:
        return None
    return task_work_rel(run_paths(attempt.runs_root, attempt.run_id).work_dir, attempt.work_dir)


# --- Listing ------------------------------------------------------------------------------


def list_task_files(attempt: AttemptFiles) -> list[TaskFile]:
    """One entry per file the attempt has, or may have, with its state."""
    if attempt.engine == "snakemake":
        return _smk_files(attempt)
    return _nf_files(attempt)


def _missing(attempt: AttemptFiles, name: str, kind: Kind) -> TaskFile:
    note = None
    if attempt.state in OPEN_STATES:
        state: State = "not_yet"
    elif kind == "slurm_log" and attempt.state == "succeeded":
        state = "deleted_after_success"
        note = "Deleted by the SLURM executor plugin after success."
    else:
        state = "absent"
        if name == ".command.log" and _ARRAY_TASK.fullmatch(attempt.native_id or ""):
            note = "A SLURM array task writes its job log to /dev/null: see .command.err."
        elif name == ".command.trace":
            note = "Written only when the run measures its tasks."
    return TaskFile(name, kind, None, None, state, note)


def _listed(
    attempt: AttemptFiles, root: Root, rel: PurePosixPath, name: str, kind: Kind
) -> TaskFile:
    try:
        st = stat_confined(root, rel)
    except NotFound:
        return _missing(attempt, name, kind)
    except NotAllowed as exc:
        return TaskFile(name, kind, None, None, "absent", f"Not served: {exc}.")
    if st is None:
        return _missing(attempt, name, kind)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid():
        return TaskFile(
            name, kind, None, None, "absent", "Not served: not a regular file of yours."
        )
    return TaskFile(name, kind, st.st_size, st.st_mtime, "present", NOTES.get(name))


def _all(attempt: AttemptFiles, names: dict[str, Kind], state: State, note: str) -> list[TaskFile]:
    return [TaskFile(n, k, None, None, state, note) for n, k in names.items()]


def _nf_files(attempt: AttemptFiles) -> list[TaskFile]:
    rel = _work_rel(attempt)
    if rel is None:
        if attempt.state in OPEN_STATES:
            return _all(attempt, NF_FILES, "not_yet", "No work directory yet.")
        return _all(attempt, NF_FILES, "absent", "No work directory recorded for this attempt.")
    try:
        with run_root(attempt.runs_root, attempt.run_id, "work") as work:
            if stat_confined(work, rel) is None:
                raise NotFound(str(rel))
            return [_listed(attempt, work, rel / n, n, k) for n, k in NF_FILES.items()]
    except NotFound:
        if attempt.state in OPEN_STATES:  # not visible yet on a shared file system
            return _all(attempt, NF_FILES, "not_yet", "The work directory is not visible yet.")
        return _all(attempt, NF_FILES, "cleaned", "The work directory was cleaned.")
    except NotAllowed as exc:
        return _all(attempt, NF_FILES, "absent", f"Not served: {exc}.")


def _smk_files(attempt: AttemptFiles) -> list[TaskFile]:
    kinds: dict[str, Kind] = {p: log_kind(PurePosixPath(p)) for p, _ in attempt.logs}
    try:
        with run_root(attempt.runs_root, attempt.run_id, "launch") as launch:
            return [_listed(attempt, launch, safe_rel(p), p, k) for p, k in kinds.items()]
    except Cleaned:
        return _all(attempt, kinds, "cleaned", "The launch directory is gone.")
    except NotAllowed as exc:
        return _all(attempt, kinds, "absent", f"Not served: {exc}.")


# --- Reading --------------------------------------------------------------------------------


def check_name(attempt: AttemptFiles, name: str) -> Kind:
    """The kind of `name` for this attempt; raises NotAllowed for any name not served."""
    rel = safe_rel(name)  # control characters, `..`, absolute paths
    if attempt.engine == "snakemake":
        recorded = {p for p, _ in attempt.logs}
        if name not in recorded:  # byte for byte (SEC-156)
            raise NotAllowed("not a file of this job")
        if rel.parts[0] == ".spectio" and not _spectio_served(rel):
            raise NotAllowed("not a file of this job")
        return log_kind(rel)
    if name not in NF_FILES:
        raise NotAllowed("not a file this server serves")
    return NF_FILES[name]


def read_task_file(
    attempt: AttemptFiles,
    name: str,
    *,
    max_bytes: int = TAIL,
    byte_range: tuple[int, int | None] | None = None,
) -> Served:
    """The text of one file: its last `max_bytes`, or `byte_range` (start, last or None), at
    most MAX_READ bytes, with escape sequences removed, and `.command.run` hidden. Raises
    NotAllowed, NotFound (Cleaned when the directory is gone) or Binary."""
    kind = check_name(attempt, name)
    with ExitStack() as stack:
        if attempt.engine == "snakemake":
            root = stack.enter_context(run_root(attempt.runs_root, attempt.run_id, "launch"))
            rel = safe_rel(name)
        else:
            dir_rel = _work_rel(attempt)
            if dir_rel is None:
                raise NotFound("no work directory recorded for this attempt")
            work = stack.enter_context(run_root(attempt.runs_root, attempt.run_id, "work"))
            root, rel = work, dir_rel / name
            if stat_confined(work, dir_rel) is None:
                state = "not visible yet" if attempt.state in OPEN_STATES else "cleaned"
                cls = NotFound if attempt.state in OPEN_STATES else Cleaned
                raise cls(f"the work directory is {state}")
        try:
            f = stack.enter_context(open_confined(root, rel))  # job files: no link followed
        except NotFound:
            missing = _missing(attempt, name, kind)
            reason = {
                "not_yet": "not written yet",
                "deleted_after_success": "deleted by the SLURM executor plugin after success",
            }.get(missing.state, "not there")
            raise NotFound(f"{name}: {reason}") from None
        if b"\x00" in read_at(f, 0, SNIFF):
            raise Binary(name)
        if kind == "wrapper":  # hidden from its start, so the lexer sees the whole file
            hidden = redact_command_run(read_at(f, 0, MAX_READ).decode("utf-8", "replace"))
            return _cut(hidden.encode(), max_bytes, byte_range)
        size = size_of(f)
        if byte_range is not None:
            start, last = byte_range
            if start >= size:
                return Served("", size, size, size, True)
            end = min(size, start + MAX_READ, size if last is None else last + 1)
            data = read_at(f, start, end - start)
            return Served(_text(data), start, start + len(data), size, True)
        data = tail(f, max_bytes)
        return Served(_text(data), size - len(data), size, size, False)


def _cut(data: bytes, max_bytes: int, byte_range: tuple[int, int | None] | None) -> Served:
    """The tail or the range of text already read whole (the hidden `.command.run`)."""
    size = len(data)
    if byte_range is not None:
        start, last = byte_range
        start = min(start, size)
        end = min(size, start + MAX_READ, size if last is None else last + 1)
        return Served(_text(data[start:end]), start, end, size, True)
    start = max(0, size - min(max_bytes, MAX_READ))
    return Served(_text(data[start:]), start, size, size, False)


def _text(data: bytes) -> str:
    return strip_escapes(data.decode("utf-8", "replace"))
