"""A pipeline's effective parameters: the default of each source and where it comes from
(api-and-data-model.md §5.12, inbox #161).

The sources, each one's keys over the previous one's: the schema's `default`s; the pipeline's
own config — the `params` of `nextflow config -o json <dir>` (with `-profile <p1,p2>` for the
chosen profiles), or, for Snakemake, the file a literal `configfile: "<path>"` line of the
Snakefile names, relative to the pipeline's root, else `config/config.yaml`; the params file.
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
import re
import threading
from pathlib import Path
from typing import Any

import yaml

from spectio_server.api.problems import Problem
from spectio_server.api.workflows import (
    MAX_YAML,
    TooLarge,
    Unreadable,
    _jsonable,
    _read,
    load_yaml,
    schema_defaults,
)
from spectio_server.targets import Engine, bounded, snakefile_of

# A literal `configfile: "<path>"` line of a Snakefile, double or single quoted; any other
# `configfile:` (a variable, a call) names no file this server can read (§5.12)
CONFIGFILE = re.compile(r"^[ \t]*configfile[ \t]*:[ \t]*(?:\"([^\"\r\n]+)\"|'([^'\r\n]+)')", re.M)
CONFIGFILE_LINE = re.compile(r"^[ \t]*configfile[ \t]*:", re.M)

# A path with a control character (SEC-05/CR-02) names no file this server reads: os.open would
# raise on a null byte, and the rest have no place in a pipeline's config file name
CONTROL = re.compile(r"[\x00-\x1f]")

# An entry of either map of DefaultsCache (SEC-02/CR-08)
MAX_CACHED = 128


def _mtime(path: Path) -> int:
    """The mtime_ns of a file or directory of the cache key (SEC-04/CR-02): 0 when it is missing."""
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _evict(store: dict[Any, Any]) -> None:
    """Keep a map of the cache within `MAX_CACHED`, dropping the least recently used (the first
    key: hits and fresh entries move to the end)."""
    while len(store) > MAX_CACHED:
        del store[next(iter(store))]


def _smk_files(directory: Path) -> tuple[int, ...]:
    """The mtime_ns of the files a Snakemake pipeline's config defaults come from (SEC-04/CR-02):
    its Snakefile and the config file it names, 0 when missing. A path the read refuses (outside
    the root, a control character) leaves the Snakefile alone: the answer is not complete then,
    so it is never cached and the second mtime does not matter."""
    snakefile = snakefile_of(directory)
    named = snakefile
    try:
        text = _read(directory, *snakefile.relative_to(directory).parts)
    except (Unreadable, TooLarge):
        text = None
    literal = CONFIGFILE.search(text or "")
    if literal is None:
        if not CONFIGFILE_LINE.search(text or ""):  # no configfile line: the fallback is read
            named = directory / "config" / "config.yaml"
    else:
        rel = literal.group(1) or literal.group(2)
        parts = rel.split("/")
        # `_yaml_defaults` refuses the same paths (SEC-05/CR-02); the answer is not complete
        # then, so the Snakefile's mtime alone cannot name a stale config file
        odd = any(p in ("", ".", "..") for p in parts)
        if not (rel.startswith("/") or CONTROL.search(rel) or odd):
            named = directory / rel
    return (_mtime(snakefile), _mtime(named))


def _nf_files(directory: Path) -> tuple[int, ...]:
    """The mtime_ns of the files a `nextflow config` answer depends on (SEC-04/CR-02):
    `nextflow.config` and the `conf/` directory it includes from, 0 when missing."""
    return (_mtime(directory / "nextflow.config"), _mtime(directory / "conf"))


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


def _configfile_defaults(directory: Path) -> tuple[dict[str, dict[str, Any]], bool]:
    """The config file a Snakemake pipeline loads (§5.12), read without running anything: the
    path of a literal `configfile: "<path>"` line of its Snakefile, relative to the pipeline's
    root, else `config/config.yaml`."""
    snakefile = snakefile_of(directory)
    try:
        text = _read(directory, *snakefile.relative_to(directory).parts)
    except Unreadable:  # the Snakefile cannot be read: no source is known
        return {}, False
    literal = CONFIGFILE.search(text or "")
    if literal is None:
        if CONFIGFILE_LINE.search(text or ""):  # a variable or a call: not a literal line
            return {}, False
        return _yaml_defaults(directory, "config/config.yaml", declared=False)
    return _yaml_defaults(directory, literal.group(1) or literal.group(2), declared=True)


def _yaml_defaults(
    directory: Path, rel: str, *, declared: bool
) -> tuple[dict[str, dict[str, Any]], bool]:
    """`rel` inside `directory` as the config defaults, through `_read`'s walk (no symlink) and
    with inspect's YAML caps. `declared`: the Snakefile names the file, so one that is missing
    was not read; the fallback `config/config.yaml` may simply not exist."""
    parts = rel.split("/")
    # outside the root, or a control character in the name (SEC-05/CR-02): not read, never a 500
    if rel.startswith("/") or CONTROL.search(rel) or any(p in ("", ".", "..") for p in parts):
        return {}, False
    try:
        text = _read(directory, *parts, cap=MAX_YAML)
    except Unreadable:
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
