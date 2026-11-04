"""A run's results directory, read only (P1 Task 31; api §5 note of 2026-10-28, Results;
dev-env §15.3 req. 13 and 14).

`results_dir` is the directory recorded on the run at launch (`runs.results_dir`): Nextflow's
`params.outdir` resolved against the launch directory, Snakemake's launch directory. Below it,
every read is the confined walk of `files.confine`; a last-component symlink is followed only
into a task directory of the run's work directory (a `publishDir` in `'symlink'` mode). No part
of a path may be `.spectio` or `.snakemake`, compared without case: those hold the head's and
the engine's own files, which are served by their routes or not at all.

A listing reads one folder, at most `MAX_ENTRIES` entries (`scandir` stops there), folders
first. The search for reports looks for `.html` and `.htm` files to `REPORT_DEPTH` levels
below the root, breadth first, and stops after `SEARCH_ENTRIES` entries visited, `SEARCH_S`
seconds or `MAX_REPORTS` found (req. 14, SEC-157). Every function that touches the file system
runs in the file pool (`files.pool`) and returns data, never an open file.
"""

import os
import posixpath
import stat
import time
from collections import deque
from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from spectio.runner.rundir import run_paths
from spectio_server.files.confine import (
    MAX_READ,
    Entry,
    NotAllowed,
    NotFound,
    Root,
    list_confined,
    open_confined,
    open_dir,
    open_root,
    read_at,
    safe_rel,
    size_of,
)
from spectio_server.files.taskfiles import run_root

MAX_ENTRIES = 1000  # of one listing
MAX_REPORTS = 50
REPORT_DEPTH = 4  # a report at most this many levels below the root (a file at the root: 1)
SEARCH_ENTRIES = 10_000
SEARCH_S = 5.0
CHUNK = MAX_READ  # one read of a raw file
REPORT_SUFFIXES = (".html", ".htm")
ENGINE_DIRS = frozenset({".spectio", ".snakemake"})  # never part of a results path
MULTIQC = "multiqc_report.html"

clock = time.monotonic  # the search's clock (a test moves it)


@dataclass(frozen=True)
class Where:
    """A run's results directory and the run whose work directory its links may point into
    (a Resume's lineage root)."""

    runs_root: Path
    run_id: str
    results_dir: str


@dataclass(frozen=True)
class Report:
    path: str
    title: str
    group: str | None


# --- At launch ---------------------------------------------------------------------------


def results_dir(
    engine: str,
    run_id: str,
    runs_root: Path,
    launch_dir: str,
    params: Mapping[str, Any],
    default_outdir: str | None,
) -> str | None:
    """The results directory of a run, as text, or None when it is unknown: Snakemake's launch
    directory; Nextflow's `params.outdir` (else the schema's default), resolved against the
    launch directory and normalised. None also for an `outdir` whose listing would serve more
    than results: one that holds the runs root or the home directory (`/`, `..`, `$HOME`), one
    under the runs root but not in the run's launch directory (a work directory, `.spectio/`,
    another run), or one with a `.spectio` or `.snakemake` part."""
    if engine == "snakemake":
        return launch_dir
    outdir = params.get("outdir", default_outdir)
    if not isinstance(outdir, str) or not outdir or "\x00" in outdir:
        return None
    found = posixpath.normpath(posixpath.join(launch_dir, outdir))
    root = str(runs_root)
    if _holds(found, root) or _holds(found, str(Path.home())):
        return None
    if _holds(root, found) and not _holds(launch_dir, found):
        return None
    if any(part.casefold() in ENGINE_DIRS for part in found.split("/")):
        return None
    return found


def _holds(folder: str, path: str) -> bool:
    """`path` is `folder` or below it, by their text."""
    folder = folder.rstrip("/") + "/"
    return (path.rstrip("/") + "/").startswith(folder)


# --- Names -------------------------------------------------------------------------------


def check_rel(path: str) -> PurePosixPath | None:
    """`path` as a relative path below the results root, None for the root itself (`""`);
    raises NotAllowed as `safe_rel` does, and for an engine directory on the way."""
    if path == "":
        return None
    rel = safe_rel(path)
    if any(part.casefold() in ENGINE_DIRS for part in rel.parts):
        raise NotAllowed("not a results file: the engine's own directory")
    return rel


@contextmanager
def _roots(where: Where) -> Iterator[tuple[Root | None, Root | None]]:
    """The results root (None while it does not exist) and the run's work directory (None when
    it cannot be opened: no link is then followed)."""
    launch_dir = str(run_paths(where.runs_root, where.run_id).launch_dir)
    with ExitStack() as stack:
        work: Root | None
        try:
            work = stack.enter_context(run_root(where.runs_root, where.run_id, "work"))
        except (NotFound, NotAllowed):
            work = None
        root: Root | None
        try:
            if where.results_dir == launch_dir:
                root = stack.enter_context(run_root(where.runs_root, where.run_id, "launch"))
            elif _holds(launch_dir, where.results_dir):
                launch = stack.enter_context(run_root(where.runs_root, where.run_id, "launch"))
                rel = safe_rel(where.results_dir[len(launch_dir) + 1 :])
                root = open_dir(launch, rel)
                stack.callback(os.close, root.fd)
            else:
                root = open_root(where.results_dir)
                stack.callback(os.close, root.fd)
        except NotFound:
            root = None
        yield root, work


# --- Listing and search ------------------------------------------------------------------


def _shown(entry: Entry) -> bool:
    return entry.name.casefold() not in ENGINE_DIRS


def list_results(where: Where, rel: PurePosixPath | None) -> tuple[bool, list[Entry], bool]:
    """(exists, entries folders first then by name, truncated) of one folder; raises NotFound
    for a missing folder below an existing root, NotAllowed for a refused one."""
    with _roots(where) as (root, work):
        if root is None:
            if rel is None:
                return False, [], False
            raise NotFound("the results directory does not exist yet")
        found = list_confined(root, rel or PurePosixPath("."), MAX_ENTRIES, work=work)
    entries = sorted(filter(_shown, found.entries), key=lambda e: (e.type != "dir", e.name))
    return True, entries, found.truncated


def _report(rel: PurePosixPath) -> Report:
    multiqc = rel.name.endswith(MULTIQC)
    title = "MultiQC report" if multiqc else rel.name.rsplit(".", 1)[0]
    group = None if str(rel.parent) == "." else str(rel.parent)
    return Report(str(rel), title, group)


def find_reports(where: Where) -> list[Report]:
    """The reports below the root, MultiQC's first, then by path (a folder's together)."""
    found: list[PurePosixPath] = []
    with _roots(where) as (root, work):
        if root is not None:
            _search(root, work, found)
    reports = [_report(rel) for rel in found]
    return sorted(reports, key=lambda r: (not r.path.endswith(MULTIQC), r.path))


def _search(root: Root, work: Root | None, found: list[PurePosixPath]) -> None:
    start, visited = clock(), 0
    todo: deque[PurePosixPath] = deque([PurePosixPath(".")])
    while todo:
        folder = todo.popleft()
        try:
            fd = open_dir(root, folder).fd if str(folder) != "." else os.dup(root.fd)
        except (NotAllowed, NotFound, OSError):
            continue
        try:
            with os.scandir(fd) as items:
                for item in items:
                    visited += 1
                    if visited > SEARCH_ENTRIES or clock() - start > SEARCH_S:
                        return
                    rel = folder / item.name
                    kind = _kind(root, rel, fd, work)
                    depth = len(rel.parts)
                    if kind == "dir" and depth < REPORT_DEPTH:
                        todo.append(rel)
                    elif kind == "file" and item.name.lower().endswith(REPORT_SUFFIXES):
                        found.append(rel)
                        if len(found) >= MAX_REPORTS:
                            return
        finally:
            os.close(fd)


def _kind(root: Root, rel: PurePosixPath, dir_fd: int, work: Root | None) -> str | None:
    """`dir`, `file` (a regular file of the user, or a published link) or None."""
    if rel.name.casefold() in ENGINE_DIRS:
        return None
    try:
        st = os.stat(rel.name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError:
        return None
    if st.st_uid != os.geteuid():
        return None
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if stat.S_ISREG(st.st_mode):
        return "file"
    if stat.S_ISLNK(st.st_mode) and rel.name.lower().endswith(REPORT_SUFFIXES):
        try:
            with open_confined(root, rel, work=work):
                return "file"
        except (NotAllowed, NotFound, OSError):
            return None
    return None


# --- Raw files ---------------------------------------------------------------------------


def file_size(where: Where, rel: PurePosixPath) -> int:
    """The size of the results file `rel`; raises NotFound or NotAllowed."""
    with _roots(where) as (root, work):
        if root is None:
            raise NotFound("the results directory does not exist yet")
        with open_confined(root, rel, work=work) as f:
            return size_of(f)


def read_chunk(where: Where, rel: PurePosixPath, start: int, n: int) -> bytes:
    """At most `n` bytes (at most `CHUNK`) of the results file `rel` from `start`."""
    with _roots(where) as (root, work):
        if root is None:
            raise NotFound("the results directory does not exist yet")
        with open_confined(root, rel, work=work) as f:
            return read_at(f, start, min(n, CHUNK))
