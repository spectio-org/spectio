"""Detected stages of a Snakemake run, from the rule files its main Snakefile includes (ui-spec
§5.1.1, Snakemake rules 1 to 4; from the stage-detection spike's `detect_smk.py`).

The server reads these files as its own user, and for a run started from a terminal the main
Snakefile's path comes from the run's events, so it is untrusted input (dev-env §15.3 req. 12):
`read_confined` takes regular files only, under the main Snakefile's directory once every symlink
is resolved, at most `MAX_FILES` files of `MAX_FILE_BYTES` each. A FIFO or a device is refused
without blocking. A source that fails a check gives no detected stages, and a warning.
"""

import errno
import logging
import os
import re
import stat
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from spectio_server.stages.assign import MAX_STAGES, StageDef

log = logging.getLogger(__name__)

MAX_FILES = 200
MAX_FILE_BYTES = 1048576
INCLUDE = re.compile(r"""^\s*include:\s*["']([^"']+)["']""")
RULE = re.compile(r"^\s*(?:local)?(?:rule|checkpoint)\s+(\w+)\s*:")
USE_AS = re.compile(r"^\s*use rule\s+.*\bas\s+(\w+)")
# `snakemake --list-rules` prints `name (docstring)` for a rule with a docstring.
LISTED = re.compile(r"([A-Za-z_]\w*)(?:\s+\(.*\))?")
MAIN = "main"


class Unsafe(ValueError):
    """A source file failed the checks of dev-env §15.3 req. 12."""


def read_confined(root: Path, path: Path, cap: int = MAX_FILE_BYTES) -> str | None:
    """The text of `path`, a regular file under `root` (both resolved), or None when it does not
    exist. Raises Unsafe when it resolves outside `root`, is not a regular file (a FIFO or a
    device, opened without blocking) or is larger than `cap`."""
    real = Path(os.path.realpath(path))
    if not real.is_relative_to(root):
        raise Unsafe(f"{path} resolves outside {root}")
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:  # swapped for a symlink since realpath
            raise Unsafe(f"{path} is a symlink") from exc
        raise Unsafe(f"{path}: {exc.strerror}") from exc
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Unsafe(f"{path} is not a regular file")
        data = f.read(cap + 1)
    if len(data) > cap:
        raise Unsafe(f"{path} is larger than {cap} bytes")
    return data.decode("utf-8", errors="replace")


def read_rules_txt(data: bytes) -> list[str]:
    """The rule names of `snakemake --list-rules`, in its order, with docstrings stripped."""
    found = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        m = LISTED.fullmatch(line.strip())
        if m:
            found.append(m.group(1))
    return found


@dataclass
class _File:
    path: Path
    rules: list[str] = field(default_factory=list)


def _walk(root: Path, path: Path, seen: set[Path], files: list[_File]) -> None:
    """Every file reached by `include:` with a literal path, in source order, depth first."""
    real = Path(os.path.realpath(path))
    if real in seen:
        return
    text = read_confined(root, path)
    if text is None:
        return
    seen.add(real)
    if len(seen) > MAX_FILES:
        raise Unsafe(f"more than {MAX_FILES} rule files")
    entry = _File(real)
    files.append(entry)  # pre-order: a file comes before the files it includes
    for line in text.splitlines():
        if m := INCLUDE.match(line):
            _walk(root, real.parent / m.group(1), seen, files)
        elif m := RULE.match(line) or USE_AS.match(line):
            entry.rules.append(m.group(1))


def rule_files(main: Path) -> list[_File]:
    """The main Snakefile and the rule files it includes; raises Unsafe."""
    root = Path(os.path.realpath(main.parent))
    files: list[_File] = []
    _walk(root, main, set(), files)
    return files


def humanise(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").strip().capitalize()


def detect_snakemake(
    main_snakefile: Path, defined: Iterable[str] | None, cap: int = MAX_STAGES
) -> list[StageDef]:
    """The detected stages, at most `cap`, "Final targets" last; none when the source fails a
    check, or when fewer than 2 rule files besides the main Snakefile define rules. `defined`
    is the rules `snakemake --list-rules` printed with the run's configuration: the others
    (conditional includes this configuration leaves out) are dropped."""
    try:
        files = rule_files(main_snakefile)
    except Unsafe as exc:
        log.warning("%s: no detected stages: %s", main_snakefile, exc)
        return []
    keep = None if defined is None else set(defined)
    main = Path(os.path.realpath(main_snakefile))
    rules_dir = main.parent / "rules"
    seen: set[str] = set()
    groups: list[tuple[str, list[str], list[str]]] = []  # key, labels, rules
    for f in files:
        rules = [r for r in dict.fromkeys(f.rules) if r not in seen and (keep is None or r in keep)]
        if not rules:
            continue
        seen.update(rules)
        if f.path == main:
            key, label = MAIN, "Final targets"
        elif f.path.parent != rules_dir and rules_dir in f.path.parents:
            key, label = str(f.path.parent), f.path.parent.name  # one group per sub-directory
        else:
            key, label = str(f.path), f.path.stem
        if groups and groups[-1][0] == key:
            groups[-1][2].extend(rules)
        else:
            groups.append((key, [label], rules))
    groups.sort(key=lambda g: g[0] == MAIN)  # stable: the main Snakefile's rules last
    if sum(g[0] != MAIN for g in groups) < 2:
        return []
    while len(groups) > cap:
        pairs = [k for k in range(len(groups) - 1) if MAIN not in (groups[k][0], groups[k + 1][0])]
        k = min(pairs, key=lambda k: len(groups[k][2]) + len(groups[k + 1][2]))
        b = groups.pop(k + 1)
        groups[k][1].extend(b[1])
        groups[k][2].extend(b[2])
    return [
        StageDef(
            f"detected:{n}", " + ".join(humanise(x) for x in labels), "detected", None, tuple(rules)
        )
        for n, (_, labels, rules) in enumerate(groups, 1)
    ]
