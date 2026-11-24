"""A pipeline's effective parameters: the default of each source and where it comes from
(api-and-data-model.md §5.12, inbox #161).

The sources, each one's keys over the previous one's: the schema's `default`s; the pipeline's
own config — the `params` of `nextflow config -o json <dir>` (with `-profile <p1,p2>` for the
chosen profiles), or, for Snakemake, the file a literal `configfile: "<path>"` line of the
Snakefile names, relative to the pipeline's root, else `config/config.yaml`; the params file.
`nextflow config` runs through the login shell, as the module and rule commands do (§5.10): an
argument list in an empty temporary directory, with that helper's timeout and output cap. Its
answer is kept in memory per directory and profile list.

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
# `configfile:` (a variable, a call) names no file this server can read (§5.12)
CONFIGFILE = re.compile(r"^[ \t]*configfile[ \t]*:[ \t]*(?:\"([^\"\r\n]+)\"|'([^'\r\n]+)')", re.M)
CONFIGFILE_LINE = re.compile(r"^[ \t]*configfile[ \t]*:", re.M)


class DefaultsCache:
    """The answers behind `effective_defaults`, kept in memory per pipeline directory and
    profile list (§5.12): a repeated inspect or launch reads no file and starts the JVM at most
    once. A failed `nextflow config` is kept too, as None: `defaults_complete` stays false
    rather than the command starting per request."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._base: dict[str, dict[str, Any] | None] = {}  # directory -> the no-profile answer
        self._kept: dict[tuple[str, tuple[str, ...]], tuple[dict[str, dict[str, Any]], bool]] = {}

    def lookup(
        self, directory: Path, engine: Engine, name: str | None, profiles: list[str]
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        """`{name: {"value", "source"}}` of the pipeline's own sources — no schema defaults, no
        params file — and whether they are complete. `name` None: no engine source applies."""
        key = (str(directory), tuple(profiles))
        with self._lock:
            kept = self._kept.get(key)
        if kept is not None:
            return kept
        if name == "nextflow":  # computed off the lock: the command takes seconds
            found = self._nextflow(directory, engine, profiles)
        elif name == "snakemake":
            found = _configfile_defaults(directory)
        else:
            found = ({}, True)
        with self._lock:
            self._kept[key] = found
        return found

    def _nextflow(
        self, directory: Path, engine: Engine, profiles: list[str]
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        """The config's `params` without a profile (`"config"`, §5.12) and what the chosen
        profiles changed on them (`"profile"`): each profile answer is compared with the
        no-profile one."""
        where = str(directory)
        with self._lock:
            known = where in self._base
            base = self._base.get(where)
        if not known:  # computed off the lock: the command takes seconds
            base = self._config_params(engine, directory, [])
            with self._lock:
                self._base[where] = base
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
        out (rc 124), printed past the output cap (rc 125) or answered no JSON."""
        argv = ["config", "-o", "json", str(directory)]
        if profiles:
            argv[1:1] = ["-profile", ",".join(profiles)]
        rc, out, _ = bounded(engine, "nextflow", argv)
        if rc != 0:
            return None
        try:  # a login profile may print first: what follows the JSON is not read
            answer = _jsonable(json.JSONDecoder().raw_decode(out, out.index("{"))[0])
        except (ValueError, RecursionError):
            return None
        params = answer.get("params") if isinstance(answer, dict) else None
        if not isinstance(params, dict):
            return None
        # `input = null` in nextflow.config is "not set" (nf-core): such a key gives no value
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
    if rel.startswith("/") or any(p in ("", ".", "..") for p in parts):  # outside the root
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
