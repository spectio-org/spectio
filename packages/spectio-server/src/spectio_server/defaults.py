"""A pipeline's effective parameters: the default of each source and where it comes from
(api-and-data-model.md §5.12, inbox #161).

The sources, each one's keys over the previous one's: the schema's `default`s; the pipeline's
own config — the `params` of `nextflow config -o json <dir>` (with `-profile <p1,p2>` for the
chosen profiles), or, for Snakemake, the file a literal `configfile: "<path>"` line of the
Snakefile names, or the literal of a variable the line names, assigned on an earlier top-level
line (inbox #161), relative to the pipeline's root, else `config/config.yaml`; the params file.
`nextflow config` runs through the login shell, as the module and rule commands do (§5.10): an
argument list in an empty temporary directory, with that helper's timeout and output cap. Its
answer is kept in memory per directory and profile list, and per the mtime_ns of the files the
answer depends on (SEC-04/CR-02), within 128 entries per map (SEC-02/CR-08); a failed answer is
not kept (SEC-03/CR-02), so a later success is seen.

A source that cannot be read — the command fails or times out, the `configfile:` line is not a
literal — leaves the defaults *not complete*: a parameter is then missing only when no source
gives it, and the engine's own check has the last word.
"""

import json
import keyword
import os
import re
import threading
from pathlib import Path
from typing import Any

import yaml

from spectio_server.api.problems import Problem
from spectio_server.api.workflows import (
    MAX_YAML,
    Unreadable,
    _jsonable,
    _read,
    load_yaml,
    schema_defaults,
)
from spectio_server.targets import Engine, bounded, snakefile_of

# A literal `configfile: "<path>"` line of a Snakefile, double or single quoted; any other
# `configfile:` (a variable, a call) names no file this server can read (§5.12) — except a
# variable assigned a literal on an earlier top-level line (inbox #161): `CONFIGFILE_NAME`
# names it, `ASSIGNMENT` is the last such assignment above the line, and the literal goes
# through the same checks as a written-out path
CONFIGFILE = re.compile(r"^[ \t]*configfile[ \t]*:[ \t]*(?:\"([^\"\r\n]+)\"|'([^'\r\n]+)')", re.M)
CONFIGFILE_NAME = re.compile(
    r"^[ \t]*configfile[ \t]*:[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*(?:#.*)?$", re.M
)
ASSIGNMENT = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(?:\"([^\"\r\n]+)\"|'([^'\r\n]+)')", re.M
)
CONFIGFILE_LINE = re.compile(r"^[ \t]*configfile[ \t]*:", re.M)

# A path with a control character (SEC-05/CR-02) names no file this server reads: os.open would
# raise on a null byte, and the rest have no place in a pipeline's config file name
CONTROL = re.compile(r"[\x00-\x1f]")

# An entry of either map of DefaultsCache (SEC-02/CR-08)
MAX_CACHED = 128


def _stamp(path: Path) -> tuple[int, int]:
    """The mtime_ns and size of a file or directory of the cache key (SEC-04/CR-02), (0, 0) when
    it is missing: the size tells apart two edits within one tick of a coarse clock."""
    try:
        st = path.stat()
    except OSError:
        return (0, 0)
    return (st.st_mtime_ns, st.st_size)


def _evict(store: dict[Any, Any]) -> None:
    """Keep a map of the cache within `MAX_CACHED`, dropping the least recently used (the first
    key: hits and fresh entries move to the end)."""
    while len(store) > MAX_CACHED:
        del store[next(iter(store))]


def _smk_files(directory: Path) -> tuple[int, ...]:
    """The stamps of the files a Snakemake pipeline's config defaults come from (SEC-04/CR-02):
    its Snakefile and the config file `_config_file` names (the Snakefile again when none)."""
    snakefile, rel, _ = _config_file(directory)
    return (*_stamp(snakefile), *_stamp(directory / rel if rel else snakefile))


def _nf_files(directory: Path) -> tuple[int, ...]:
    """The stamps of the files a `nextflow config` answer depends on (SEC-04/CR-02):
    `nextflow.config`, the `conf/` directory and its `*.config` files (at most 64), which a
    directory's own mtime does not follow when one is edited in place."""
    conf = directory / "conf"
    try:
        names = sorted(e.name for e in os.scandir(conf) if e.name.endswith(".config"))[:64]
    except OSError:
        names = []
    stamps = [
        _stamp(directory / "nextflow.config"),
        _stamp(conf),
        *(_stamp(conf / n) for n in names),
    ]
    return tuple(n for stamp in stamps for n in stamp)


def _fingerprint(directory: Path, name: str | None) -> tuple[int, ...]:
    """The cache key's part for the files the answer depends on (SEC-04/CR-02)."""
    if name == "nextflow":
        return _nf_files(directory)
    if name == "snakemake":
        return _smk_files(directory)
    return ()


class DefaultsCache:
    """The answers behind `effective_defaults`, kept in memory per pipeline directory, profile
    list and the mtime_ns of the files the answer depends on (§5.12): a repeated inspect or
    launch reads no file and starts the JVM at most once, and an edited `nextflow.config` or
    config file is read again (SEC-04/CR-02). At most 128 entries per map, the least recently
    used evicted (SEC-02/CR-08). A failed `nextflow config` or an unreadable source is not kept
    (SEC-03/CR-02): the next request reads again, so a later success is seen."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (directory, mtimes of nextflow.config and conf/) -> the no-profile answer
        self._base: dict[tuple[str, tuple[int, ...]], dict[str, Any] | None] = {}
        # (directory, profiles, mtimes of the source files) -> the answer and whether it is complete
        self._kept: dict[
            tuple[str, tuple[str, ...], tuple[int, ...]],
            tuple[dict[str, dict[str, Any]], bool],
        ] = {}

    def lookup(
        self, directory: Path, engine: Engine, name: str | None, profiles: list[str]
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        """`{name: {"value", "source"}}` of the pipeline's own sources — no schema defaults, no
        params file — and whether they are complete. `name` None: no engine source applies."""
        key = (str(directory), tuple(profiles), _fingerprint(directory, name))
        with self._lock:
            kept = self._kept.get(key)
            if kept is not None:  # the hit becomes the most recently used
                self._kept[key] = self._kept.pop(key)
        if kept is not None:
            return kept
        if name == "nextflow":  # computed off the lock: the command takes seconds
            found = self._nextflow(directory, engine, profiles, key[2])
        elif name == "snakemake":
            found = _configfile_defaults(directory)
        else:
            found = ({}, True)
        with self._lock:
            if found[1]:  # a failed read is not cached (SEC-03/CR-02)
                self._kept[key] = found
                _evict(self._kept)
        return found

    def _nextflow(
        self, directory: Path, engine: Engine, profiles: list[str], files: tuple[int, ...]
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        """The config's `params` without a profile (`"config"`, §5.12) and what the chosen
        profiles changed on them (`"profile"`): each profile answer is compared with the
        no-profile one."""
        where = (str(directory), files)
        with self._lock:
            base = self._base.get(where)
            if base is not None:
                self._base[where] = self._base.pop(where)
        if base is None:  # computed off the lock: the command takes seconds
            base = self._config_params(engine, directory, [])
            with self._lock:
                if base is not None:  # a failed command is not cached (SEC-03/CR-02)
                    self._base[where] = base
                    _evict(self._base)
        values = {k: {"value": v, "source": "config"} for k, v in (base or {}).items()}
        complete = base is not None
        if profiles:
            chosen = self._config_params(engine, directory, profiles)
            complete = complete and chosen is not None
            for k, v in (chosen or {}).items():
                source = "profile" if base is None or base.get(k) != v else "config"
                values[k] = {"value": v, "source": source}
        return values, complete

    def _config_params(
        self, engine: Engine, directory: Path, profiles: list[str]
    ) -> dict[str, Any] | None:
        """The `params` of `nextflow config`'s JSON answer, or None: the command failed, timed
        out (rc 124), printed past the output cap (rc 125) or answered no JSON, or the
        inspection pool is busy (§5.12: the source counts as not read)."""
        argv = ["config", "-o", "json", str(directory)]
        if profiles:
            argv[1:1] = ["-profile", ",".join(profiles)]
        try:
            rc, out, _ = bounded(engine, "nextflow", argv)
        except Problem:  # 503 Busy: no free slot (CR-161S2-03); never a 500 or a 503 of the form
            return None
        if rc != 0:
            return None
        try:  # a login profile may print first: what follows the JSON is not read
            answer = _jsonable(json.JSONDecoder().raw_decode(out, out.index("{"))[0])
        except (ValueError, RecursionError):
            return None
        params = answer.get("params") if isinstance(answer, dict) else None
        if not isinstance(params, dict):
            return None
        # `input = null` in nextflow.config is "not set" (nf-core): such a key gives no value, in
        # the base config as in a profile — a profile that sets a value to null keeps the base
        # config's value (§5.12), like a profile that leaves it out
        return {k: v for k, v in params.items() if v is not None}


def _config_file(directory: Path) -> tuple[Path, str | None, bool]:
    """The Snakefile, the config file it loads relative to the pipeline's root, and whether the
    Snakefile names it (§5.12): a literal `configfile: "<path>"` line's path, else the literal
    of a variable that an earlier top-level line assigns and the line names (inbox #161), else
    `config/config.yaml`. None when no file can be named: the Snakefile cannot be read, the line
    names anything else (a call, a keyword, an unassigned variable), or the path leaves the root
    or holds a control character (SEC-05/CR-02). The one place the cache key and the read both
    take it from."""
    snakefile = snakefile_of(directory)
    try:
        text = _read(directory, *snakefile.relative_to(directory).parts) or ""
    except (Unreadable, UnicodeDecodeError):
        return snakefile, None, True
    rel: str | None = None
    if (literal := CONFIGFILE.search(text)) is not None:
        rel = literal.group(1) or literal.group(2)
    elif (named := CONFIGFILE_NAME.search(text)) is not None and not keyword.iskeyword(
        named.group(1)
    ):
        for assign in reversed(list(ASSIGNMENT.finditer(text))):
            if assign.start() < named.start() and assign.group(1) == named.group(1):
                rel = assign.group(2) or assign.group(3)
                break
    if rel is None:
        if CONFIGFILE_LINE.search(text):
            return snakefile, None, True
        return snakefile, "config/config.yaml", False
    if (
        rel.startswith("/")
        or CONTROL.search(rel)
        or any(p in ("", ".", "..") for p in rel.split("/"))
    ):
        return snakefile, None, True
    return snakefile, rel, True


def _configfile_defaults(directory: Path) -> tuple[dict[str, dict[str, Any]], bool]:
    """The config file a Snakemake pipeline loads (§5.12), read without running anything."""
    _, rel, declared = _config_file(directory)
    if rel is None:
        return {}, False
    return _yaml_defaults(directory, rel, declared=declared)


def _yaml_defaults(
    directory: Path, rel: str, *, declared: bool
) -> tuple[dict[str, dict[str, Any]], bool]:
    """`rel` inside `directory` as the config defaults, through `_read`'s walk (no symlink) and
    with inspect's YAML caps. `declared`: the Snakefile names the file, so one that is missing
    was not read; the fallback `config/config.yaml` may simply not exist."""
    try:  # a file that is not UTF-8 is not read either: never a 500 (CR-345R-02)
        text = _read(directory, *rel.split("/"), cap=MAX_YAML)
    except (Unreadable, UnicodeDecodeError):
        return {}, False
    if text is None:
        return {}, not declared
    try:
        values = load_yaml(text)
    except (ValueError, TypeError, RecursionError, yaml.YAMLError):
        return {}, False
    if not isinstance(values, dict):
        return {}, False
    return {k: {"value": v, "source": "config"} for k, v in values.items()}, True


CACHE = DefaultsCache()  # the server's own; a test passes a fresh one


def effective_defaults(
    directory: Path,
    engine: Engine,
    name: str | None,
    profiles: list[str],
    schema: dict[str, Any] | None = None,
    params_file: dict[str, Any] | None = None,
    cache: DefaultsCache | None = None,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """The effective parameters' defaults of a pipeline (§5.12): `{name: {"value", "source"}}`
    of its top-level names, and whether the sources are complete. The sources, each one's keys
    over the previous one's: the schema's `default`s (`"schema"`), the pipeline's own config
    (`"config"`, or `"profile"` for a value a chosen profile changed), the params file. `schema`
    is the pipeline's, as `inspect_dir` read it; `params_file` the chosen file's values."""
    values, complete = (cache or CACHE).lookup(directory, engine, name, profiles)
    defaults = {k: {"value": v, "source": "schema"} for k, v in schema_defaults(schema).items()}
    defaults.update(values)
    for k, v in (params_file or {}).items():
        defaults[k] = {"value": v, "source": "params_file"}
    return defaults, complete
