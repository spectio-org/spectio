"""`GET /api/v1/workflows:inspect`, and the pipeline rules `POST /runs` shares (P1 Task 17,
Assumption 2; api §5; UX-G2-04).

A location is an absolute path to a directory this account can read, or a Git repository: an
`owner/repo` name (GitHub), or an `https://` or `ssh://` URL, under the import rule of
[api §5, Imports are untrusted input]: no other transport, no credentials in the URL, plain
path parts only. A repository is fetched once per revision into
`<data dir>/pipelines/<host>/<path…>/<revision>/`, by `git` run as an argument list with
`-c protocol.allow=never` and only the allowed transports turned back on; a commit is fetched
then checked out. Neither a location nor a revision may hold a control character
(SEC-P3T09-R5-05), and a revision never starts with `-` (G5). Those checks live in
`spectio.locations`, shared with the catalog file (SEC-PRE-FU87-02).

Inspect reads the directory, never runs it: the engine files present (`main.nf`, `Snakefile`,
`workflow/Snakefile`), the engine they point to (none for both or neither), the Nextflow
manifest's name and version and the profiles, and the parameter schema with where it came from.
"""

import contextlib
import errno
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import yaml
from fastapi import APIRouter, Request

from spectio import envfile, locations
from spectio.config import Settings
from spectio.runner.engines import EngineError, check_engine
from spectio.runner.rundir import private_dir
from spectio_server.api.problems import Invalid, Problem
from spectio_server.files.pool import READ_TIMEOUT_S, Stalled

router = APIRouter()

GIT_SCHEMES = locations.GIT_SCHEMES  # api §5; a test adds "file" for a local repo
GIT_TIMEOUT_S = 300
VERSIONS_TTL_S = 300.0  # how long the engines' versions are kept (FU-P3-109)
VERSIONS_FAILED_TTL_S = 10.0  # the same, when an engine was not found (CR-P3FU109-03)
MAX_LOCATION = locations.MAX_LOCATION
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# What a fetch failure says when the revision, not the repository, is wrong.
NO_REVISION = re.compile(r"Remote branch .* not found|couldn't find remote ref|not our ref", re.I)
ENTRY_FILES: dict[str, tuple[str, ...]] = {
    "nextflow": ("main.nf",),
    "snakemake": ("Snakefile", "workflow/Snakefile"),
}
SMK_SCHEMAS = ("config.schema.yaml", "workflow/schemas/config.schema.yaml")
MAX_FILE = 1048576  # a config or schema file read by inspect
MAX_PARAMS_FILE = 256 * 1024  # a catalog entry's params file (api §5.6, SEC-PRE-FU87-07)
MAX_DEPTH = 32  # of the params (FU-P3-17), sent or read from a params file
NO_ALIASES = "YAML aliases are not read"
MAX_NUMBER = 128  # characters of a YAML number (SEC-161S4-01)

SchemaSource = Literal["nextflow_schema.json", "config.schema.yaml", "inferred", "none"]


@dataclass(frozen=True)
class Resolved:
    """A location checked, and fetched when it is Git."""

    location: str  # as stored: the absolute path, or the repository's URL
    revision: str | None
    source: Literal["local", "git"]
    directory: Path  # what is read and launched
    default_name: str  # the directory's, or the repository's, name


@dataclass(frozen=True)
class Found:
    engine_files: list[str]
    engine: str | None
    name: str
    version: str | None
    profiles: list[str]
    schema: dict[str, Any] | None
    schema_source: SchemaSource


@contextlib.contextmanager
def _as_invalid(field: str) -> Iterator[None]:
    """A ValueError of `spectio.locations`, as `Invalid` for `field`."""
    try:
        yield
    except ValueError as exc:
        raise Invalid(field, str(exc)) from None


def refuse_control(field: str, value: str) -> None:
    """`locations.refuse_control`, raising Invalid (field `field`)."""
    with _as_invalid(field):
        locations.refuse_control(value)


# --- Locations -------------------------------------------------------------------------------


def git_url(location: str) -> tuple[str, tuple[str, ...]]:
    """`locations.git_url` under GIT_SCHEMES, raising Invalid (field `location`)."""
    with _as_invalid("location"):
        return locations.git_url(location, GIT_SCHEMES)


def check_revision(revision: str | None) -> str:
    with _as_invalid("revision"):
        return locations.check_revision(revision)


def resolve(data_dir: Path, location: str, revision: str | None) -> Resolved:
    """Check a location (fields `location`, `revision`) and fetch it when it is Git."""
    if len(location) > MAX_LOCATION:
        raise Invalid("location", f"longer than {MAX_LOCATION} characters")
    refuse_control("location", location)
    if location.startswith("/"):
        directory = local_dir(location)
        return Resolved(str(directory), None, "local", directory, directory.name)
    url, parts = git_url(location)
    revision = check_revision(revision)
    directory = fetch(data_dir, url, parts, revision)
    return Resolved(url, revision, "git", directory, parts[-1])


def local_dir(location: str) -> Path:
    """An absolute location (field `location`) that is a directory this account can read."""
    directory = Path(location)
    try:
        readable = directory.is_dir() and os.access(directory, os.R_OK | os.X_OK)
    except OSError:  # a name too long, among others
        readable = False
    if not readable:
        raise Invalid("location", f"{location} is not a directory this account can read")
    return directory


def run_git(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run git with no terminal: it fails rather than ask for a password or a passphrase
    [to be validated on the EMBL login nodes]. A timeout kills its whole process group."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    with subprocess.Popen(  # noqa: S603 - an argument list, no shell
        argv,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as proc:
        try:
            out, err = proc.communicate(timeout=GIT_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return subprocess.CompletedProcess(argv, 124, "", f"timed out after {GIT_TIMEOUT_S} s")
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def _git(*args: str) -> None:
    allow = [a for s in GIT_SCHEMES for a in ("-c", f"protocol.{s}.allow=always")]
    try:
        out = run_git(["git", "-c", "protocol.allow=never", *allow, *args])
    except OSError as exc:
        raise Invalid("location", f"git cannot run on this machine: {exc}") from None
    if out.returncode != 0:
        said = " ".join(out.stderr.strip().splitlines()[-3:])[:500]
        field = "revision" if NO_REVISION.search(out.stderr) else "location"
        raise Invalid(field, f"not fetched: {said or f'git exited {out.returncode}'}")


def fetch(data_dir: Path, url: str, parts: tuple[str, ...], revision: str) -> Path:
    """`<data dir>/pipelines/<parts…>/<revision>`, fetched once: into a temporary name, then
    renamed, so that a fetch cut short is never taken for a whole one."""
    where = ("pipelines", *parts)
    with private_dir(data_dir, *where, create=True):  # each part 0700 and the user's (req. 10)
        pass
    parent = data_dir.joinpath(*where)
    target = parent / quote(revision, safe="")  # one path part: '/' becomes %2F
    if target.is_dir():
        return target
    tmp = parent / f".{target.name}.{secrets.token_hex(6)}"
    try:
        if COMMIT.fullmatch(revision):
            _git("init", str(tmp))
            _git("-C", str(tmp), "fetch", "--depth", "1", "--", url, revision)
            _git("-C", str(tmp), "checkout", "--detach", "FETCH_HEAD")
        else:
            _git("clone", "--depth", "1", "--branch", revision, "--", url, str(tmp))
        try:
            tmp.rename(target)
        except OSError:
            if not target.is_dir():  # another request fetched it first: keep theirs
                raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


# --- What a directory holds ------------------------------------------------------------------


def _open(root: Path, *parts: str) -> int:
    """A descriptor on `root/parts…`, each part opened from the descriptor of the one before
    with O_NOFOLLOW: a symlink, in the tree or out of it, raises OSError (ELOOP), so a cloned
    repository cannot point inspect at the user's other files (SEC-P3T17-05, SEC-P3T17-08,
    the walk of dev-env §15.3 req. 13)."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for i, part in enumerate(parts):
            flags = os.O_NOFOLLOW | (os.O_DIRECTORY if i < len(parts) - 1 else os.O_NONBLOCK)
            child = os.open(part, os.O_RDONLY | flags, dir_fd=fd)
            os.close(fd)
            fd = child
    except OSError:
        os.close(fd)
        raise
    return fd


def _regular(root: Path, rel: str) -> bool:
    """Whether `root/rel` is a regular file inside `root`, reached through no symlink."""
    try:
        fd = _open(root, *rel.split("/"))
    except OSError:
        return False
    try:
        return stat.S_ISREG(os.fstat(fd).st_mode)
    finally:
        os.close(fd)


def _read(root: Path, *parts: str) -> str | None:
    """`root/parts…` when it is a regular file inside `root` (see `_open`), else None."""
    try:
        fd = _open(root, *parts)
    except OSError:  # missing, a symlink (ELOOP), not a directory
        return None
    with os.fdopen(fd, "rb") as f:  # closes the descriptor whatever happens next
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return None
            raw = f.read(MAX_FILE + 1)
        except OSError as exc:  # an I/O error after the open (FU-P3-17)
            raise ValueError(f"{parts[-1]} cannot be read: {exc.strerror}") from None
    if len(raw) > MAX_FILE:
        raise ValueError(f"{parts[-1]} is larger than {MAX_FILE} bytes")
    return raw.decode()


def depth(value: Any) -> int:
    """How deep `value` nests, iteratively: a deep value never reaches the recursion limit."""
    deepest, todo = 0, [(value, 1)]
    while todo:
        item, level = todo.pop()
        deepest = max(deepest, level)
        if isinstance(item, dict):
            todo.extend((v, level + 1) for v in item.values())
        elif isinstance(item, list):
            todo.extend((v, level + 1) for v in item)
    return deepest


def read_params(root: Path, rel: str) -> dict[str, Any]:
    """The top-level map of the params file `rel` (checked by `locations.check_params_file`)
    inside `root`, through `_open`'s walk (api §5.6). Raises ValueError with an error in words
    that names `rel` and quotes none of the file's bytes (SEC-PRE-FU87-03)."""
    try:
        fd = _open(root, *rel.split("/"))
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(
                f"{rel} is reached through a symbolic link, which is not read"
            ) from None
        if exc.errno in (errno.ENOENT, errno.ENOTDIR):
            raise ValueError(f"the pipeline has no such file as {rel}") from None
        raise ValueError(f"{rel} cannot be opened: {exc.strerror}") from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):  # a directory, a FIFO
            raise ValueError(f"{rel} is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as f:
            raw = f.read(MAX_PARAMS_FILE + 1)
    except OSError as exc:
        raise ValueError(f"{rel} cannot be read: {exc.strerror}") from None
    finally:
        os.close(fd)
    if len(raw) > MAX_PARAMS_FILE:
        raise ValueError(f"{rel} is larger than {MAX_PARAMS_FILE} bytes")
    kind = "JSON" if rel.endswith(".json") else "YAML"
    try:
        text = raw.decode()
        values = _jsonable(json.loads(text)) if kind == "JSON" else load_yaml(text)
    except UnicodeDecodeError:
        raise ValueError(f"{rel} is not UTF-8 text") from None
    except RecursionError:
        raise ValueError(f"{rel} is nested too deep to be read") from None
    # Their messages quote the file: not shown. TypeError: a key that is not a string, such
    # as a YAML date (SEC-P3FU87B-01).
    except (ValueError, TypeError, yaml.YAMLError) as exc:
        why = NO_ALIASES if str(exc) == NO_ALIASES else f"not {kind}"
        raise ValueError(f"{rel} cannot be read: {why}") from None
    if not isinstance(values, dict):
        raise ValueError(f"{rel} is not a map of parameter names to values")
    if depth(values) > MAX_DEPTH:
        raise ValueError(f"{rel} is nested deeper than {MAX_DEPTH} levels")
    return values


def _jsonable(value: Any) -> Any:
    """YAML dates and the like as strings, so that the response can carry them. Raises
    ValueError on NaN or an infinity, which JSON cannot carry (CR-P3FU87B-01), and TypeError on
    a key that is not a string, a number, a boolean or null."""
    return json.loads(json.dumps(value, default=str, allow_nan=False))


class _Loader(yaml.SafeLoader):
    """Safe YAML with no alias, which would let a small file grow huge in the response, and no
    flow nesting past `2 * MAX_DEPTH`, refused by the scanner before PyYAML's parse time grows
    with the square of the depth (SEC-161S2-01). The scanner's own level: quoted brackets do
    not hide it (SEC-161S3-01). Too deep raises `RecursionError` (CR-161S3-02, CR-161S4-05).
    One pass: aliases are refused as nodes are composed. Numbers are at most `MAX_NUMBER`
    characters: a long `1:59:59…` takes quadratic time to convert (SEC-161S4-01)."""

    def fetch_flow_collection_start(self, TokenClass: Any) -> None:
        if self.flow_level >= 2 * MAX_DEPTH:
            raise RecursionError(f"nested deeper than {2 * MAX_DEPTH} brackets")
        super().fetch_flow_collection_start(TokenClass)

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.AliasEvent):
            raise ValueError(NO_ALIASES)
        return super().compose_node(parent, index)


def _short_number(construct: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
    def checked(loader: Any, node: Any) -> Any:
        if len(node.value) > MAX_NUMBER:
            raise ValueError(f"a number longer than {MAX_NUMBER} characters")
        return construct(loader, node)

    return checked


# the subclass gets its own copy of the table: SafeLoader is not changed (tested)
_Loader.add_constructor("tag:yaml.org,2002:int", _short_number(_Loader.construct_yaml_int))
_Loader.add_constructor("tag:yaml.org,2002:float", _short_number(_Loader.construct_yaml_float))


def load_yaml(text: str) -> Any:
    """`text` read by `_Loader`, as JSON values."""
    try:
        return _jsonable(yaml.load(text, Loader=_Loader))  # noqa: S506 (a SafeLoader)
    except OverflowError:  # a float out of range (SEC-161S4-02)
        raise ValueError("a number out of range") from None


# An unterminated string or comment runs to the end, so no position is scanned twice
# (SEC-P3T17-03: a rescan per quote was quadratic); a final lone backslash is part of it
# (CR-P3T17-03).
_TOKENS = re.compile(
    r"'(?:\\.|[^'\\])*+(?:'|\\?\Z)|\"(?:\\.|[^\"\\])*+(?:\"|\\?\Z)|/\*.*?(?:\*/|\Z)|//[^\n]*",
    re.S,
)


def _block(text: str, name: str) -> str | None:
    """The body of the first `name { … }` block, braces matched."""
    found = re.search(rf"(?<![\w.]){name}\s*\{{", text)
    if found is None:
        return None
    depth, start = 1, found.end()
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    return None


def nextflow_config(root: Path) -> tuple[str | None, str | None, list[str]]:
    """The manifest's name and version and the profiles' names, read from `nextflow.config`
    without running it; `includeConfig` files are not followed (best effort)."""
    text = _read(root, "nextflow.config")
    if text is None:
        return None, None, []
    strings: list[str] = []

    def keep(m: re.Match[str]) -> str:  # comments go; strings become placeholders
        if m.group(0)[0] not in "'\"":
            return " "
        strings.append(m.group(0)[1:-1])
        return f"'{len(strings) - 1}'"

    code = _TOKENS.sub(keep, text)
    manifest = _block(code, "manifest") or ""

    def value(key: str) -> str | None:
        m = re.search(rf"(?<![\w.]){key}\s*=\s*'(\d+)'", manifest) or re.search(
            rf"manifest\.{key}\s*=\s*'(\d+)'", code
        )
        return strings[int(m.group(1))] if m else None

    profiles, depth = [], 0
    for m in re.finditer(
        r"(?<![\w-])([A-Za-z_][\w-]*+)\s*+\{|\{|\}", _block(code, "profiles") or ""
    ):
        if m.group(0) == "}":
            depth -= 1
            continue
        if depth == 0 and m.group(1):
            profiles.append(m.group(1))
        depth += 1
    return value("name"), value("version"), profiles


def snakemake_profiles(root: Path) -> list[str]:
    """The profiles the head can use: `profiles/<name>/config.yaml` (P1 Task 9)."""
    try:
        fd = _open(root, "profiles")
    except OSError:  # missing or a symlink
        return []
    try:
        names = os.listdir(fd)
    except NotADirectoryError:
        return []
    finally:
        os.close(fd)
    # `_open` reaches config.yaml only through real directories: symlinks and files drop out
    return sorted(n for n in names if _regular(root, f"profiles/{n}/config.yaml"))


def _type(value: Any) -> dict[str, Any]:
    types: list[tuple[type, str]] = [(bool, "boolean"), (int, "integer"), (float, "number")]
    types += [(str, "string"), (list, "array"), (dict, "object")]
    found = next((t for kind, t in types if isinstance(value, kind)), None)
    return {"default": value} if found is None else {"type": found, "default": value}


def schema_of(root: Path) -> tuple[dict[str, Any] | None, SchemaSource]:
    text = _read(root, "nextflow_schema.json")
    if text is not None:
        return _object(json.loads(text), "nextflow_schema.json"), "nextflow_schema.json"
    for rel in SMK_SCHEMAS:
        text = _read(root, *rel.split("/"))
        if text is not None:
            return _object(_small_yaml(text, rel), rel), "config.schema.yaml"
    text = _read(root, "config", "config.yaml")
    if text is not None:
        config = _object(_small_yaml(text, "config/config.yaml"), "config/config.yaml")
        props = {str(k): _type(v) for k, v in config.items()}
        return {"type": "object", "properties": props}, "inferred"
    return None, "none"


def _small_yaml(text: str, name: str) -> Any:
    """YAML read on the request's path at most `MAX_PARAMS_FILE` bytes: pure-Python PyYAML
    takes about 5 s a MiB (SEC-161S4-04)."""
    if len(text.encode()) > MAX_PARAMS_FILE:
        raise ValueError(f"{name} is larger than {MAX_PARAMS_FILE} bytes")
    return load_yaml(text)


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is not a mapping")
    return value


def entry_files(directory: Path) -> list[str]:
    """The ENTRY_FILES that are regular files in `directory`, reached through no symlink."""
    return [f for names in ENTRY_FILES.values() for f in names if _regular(directory, f)]


def inspect_dir(directory: Path, default_name: str) -> Found:
    """What the launch form needs from a pipeline directory. Raises Invalid (`location`) when
    a schema or config file cannot be read."""
    files = entry_files(directory)
    engines = [e for e, names in ENTRY_FILES.items() if set(names) & set(files)]
    engine = engines[0] if len(engines) == 1 else None  # both or neither: no guess
    try:
        name, version, nf_profiles = nextflow_config(directory)
        schema, source = schema_of(directory)
    # PyYAML's and the decoder's messages quote the file: not shown (SEC-161S3-04)
    except UnicodeDecodeError:
        raise Invalid("location", "the pipeline's files cannot be read: not UTF-8 text") from None
    except yaml.YAMLError:
        raise Invalid("location", "the pipeline's files cannot be read: not YAML") from None
    except (ValueError, TypeError, RecursionError) as exc:  # JSONDecodeError: a position only
        raise Invalid("location", f"the pipeline's files cannot be read: {exc}") from None
    profiles = {"nextflow": nf_profiles, "snakemake": snakemake_profiles(directory)}
    shown = [p for e in (engines if engine is None else [engine]) for p in profiles[e]]
    return Found(
        engine_files=files,
        engine=engine,
        name=name or default_name,
        version=version,
        profiles=list(dict.fromkeys(shown)),
        schema=schema,
        schema_source=source,
    )


def _daemon(target: Callable[[], None]) -> None:
    threading.Thread(target=target, name="spectio-engine-versions", daemon=True).start()


class EngineVersions:
    """The version of each engine the server would launch with, or None (UX-296, UX-G2-04).
    Each check runs a login shell, and Nextflow starts a JVM: a second or more (FU-P3-109), so
    it runs off the request path: `warm` starts it at server start, and a stale answer is
    returned as is while one background refresh replaces it (CR-P3FU109-01). The answer is kept
    for `ttl_s`, one with an engine not found only for `failed_ttl_s` (CR-P3FU109-03). Only the
    very first call, before any answer, waits for the check."""

    def __init__(
        self,
        settings: Settings,
        ttl_s: float = VERSIONS_TTL_S,
        failed_ttl_s: float = VERSIONS_FAILED_TTL_S,
        clock: Callable[[], float] = time.monotonic,
        spawn: Callable[[Callable[[], None]], None] = _daemon,
    ) -> None:
        self._settings, self._ttl, self._failed_ttl = settings, ttl_s, failed_ttl_s
        self._clock, self._spawn = clock, spawn
        self._lock = threading.Lock()
        self._kept: tuple[float, dict[str, str | None]] | None = None
        self._refreshing = False
        self._ready = threading.Event()

    def _one(self, engine: str) -> str | None:
        try:
            return check_engine(engine, getattr(self._settings.engines, f"{engine}_cmd")).version
        except (EngineError, OSError):
            return None

    def _refresh(self) -> None:
        try:  # both engines at once: a cold check costs the slower one, not their sum
            found: dict[str, str | None] = dict.fromkeys(ENTRY_FILES)

            def one(engine: str) -> None:
                found[engine] = self._one(engine)

            # daemon threads, not a ThreadPoolExecutor, whose workers the interpreter joins at
            # exit: a slow check would hold a SIGTERM'd `spectio serve` (FU-P3-108c)
            threads = [threading.Thread(target=one, args=(e,), daemon=True) for e in ENTRY_FILES]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            with self._lock:
                self._kept = (self._clock(), found)
        finally:
            with self._lock:
                self._refreshing = False
            self._ready.set()

    def warm(self) -> None:
        """Start a refresh unless one runs or the answer is fresh."""
        with self._lock:
            kept = self._kept
            ttl = self._failed_ttl if kept and None in kept[1].values() else self._ttl
            if self._refreshing or (kept is not None and self._clock() - kept[0] < ttl):
                return
            self._refreshing = True
        self._spawn(self._refresh)

    def __call__(self) -> dict[str, str | None]:
        self.warm()
        self._ready.wait()
        with self._lock:
            kept = self._kept
        return dict(kept[1]) if kept else dict.fromkeys(ENTRY_FILES)


def _params(request: Request, resolved: Resolved, engine: str | None, rel: str) -> Any:
    """Inspect's `params_file` (api §5.6): every top-level key of the file in `values`, or
    `values: null` and an `error` in words whatever went wrong, never a refusal; and what in it,
    or the file itself, loads code (SEC-PRE-FU87-01)."""
    # relaunch imports this module, so its check is imported here
    from spectio_server.api.relaunch import code_loading, writable_by_others

    values: dict[str, Any] | None = None
    error: str | None = None
    try:
        values = read_params(resolved.directory, rel)
    except ValueError as exc:
        error = envfile._clean(str(exc))  # at most 200 characters, no control one
    local = resolved.source == "local"
    file = str(resolved.directory / rel)

    def flagged() -> list[dict[str, Any]]:
        found = code_loading(resolved.location, local, values or {}, engine or "", [])
        if local:
            found.append(
                {
                    "field": "params_file",
                    "value": file,
                    "writable_by_others": writable_by_others(file),
                }
            )
        return found

    try:
        loading = request.app.state.files.run(flagged, READ_TIMEOUT_S)
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None
    return {"path": rel, "values": values, "code_loading": loading, "error": error}


@router.get("/workflows:inspect")
def inspect(
    request: Request,
    location: str,
    revision: str | None = None,
    params_file: str | None = None,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    if params_file is not None:  # before anything is fetched (SEC-PRE-FU87-04)
        with _as_invalid("params_file"):
            locations.check_params_file(params_file)
    resolved = resolve(settings.data_dir, location, revision)
    found = inspect_dir(resolved.directory, resolved.default_name)
    params = None if params_file is None else _params(request, resolved, found.engine, params_file)
    versions = request.app.state.engine_versions()
    return {
        "location": resolved.location,
        "revision": resolved.revision,
        "engine": found.engine,
        "engine_files": found.engine_files,
        "name": found.name,
        "version": found.version,
        "engine_version": versions.get(found.engine) if found.engine else None,
        "engine_versions": versions,
        "schema": found.schema,
        "schema_source": found.schema_source,
        "profiles": found.profiles,
        "params_file": params,
    }


def schema_defaults(schema: dict[str, Any] | None) -> dict[str, Any]:
    """The `default` of each parameter, at the top or in a group of `$defs` / `definitions`
    (the nf-core layout)."""
    found: dict[str, Any] = {}
    if not isinstance(schema, dict):
        return found
    groups = [schema]
    for key in ("$defs", "definitions"):
        if isinstance(schema.get(key), dict):
            groups += [g for g in schema[key].values() if isinstance(g, dict)]
    for group in groups:
        properties = group.get("properties")
        if isinstance(properties, dict):
            for name, prop in properties.items():
                if isinstance(prop, dict) and "default" in prop:
                    found.setdefault(name, prop["default"])
    return found
