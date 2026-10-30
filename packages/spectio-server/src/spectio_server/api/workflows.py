"""`GET /api/v1/workflows:inspect`, and the pipeline rules `POST /runs` shares (P1 Task 17,
Assumption 2; api §5; UX-G2-04).

A location is an absolute path to a directory this account can read, or a Git repository: an
`owner/repo` name (GitHub), or an `https://` or `ssh://` URL, under the import rule of
[api §5, Imports are untrusted input]: no other transport, no credentials in the URL, plain
path parts only. A repository is fetched once per revision into
`<data dir>/pipelines/<host>/<path…>/<revision>/`, by `git` run as an argument list with
`-c protocol.allow=never` and only the allowed transports turned back on; a commit is fetched
then checked out. Neither a location nor a revision may hold a control character
(SEC-P3T09-R5-05), and a revision never starts with `-` (G5).

Inspect reads the directory, never runs it: the engine files present (`main.nf`, `Snakefile`,
`workflow/Snakefile`), the engine they point to (none for both or neither), the Nextflow
manifest's name and version and the profiles, and the parameter schema with where it came from.
"""

import contextlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import yaml
from fastapi import APIRouter, Request

from spectio.config import Settings
from spectio.runner.engines import EngineError, check_engine
from spectio.runner.rundir import private_dir
from spectio_server.api.problems import Invalid

router = APIRouter()

GIT_SCHEMES: tuple[str, ...] = ("https", "ssh")  # api §5; a test adds "file" for a local repo
GIT_TIMEOUT_S = 300
GITHUB = "https://github.com"
SHORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9._-]{0,99}")
URL_CHARS = re.compile(r"[A-Za-z0-9._~:/@+-]+")  # no space, quote, `%`, `?`, `#` or backslash
HOST = re.compile(r"[a-z0-9]([a-z0-9.-]{0,252}[a-z0-9])?")
PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,99}")  # never "", "." or ".."
REVISION = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/-]{0,199}")  # never an option, never a path
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# What a fetch failure says when the revision, not the repository, is wrong.
NO_REVISION = re.compile(r"Remote branch .* not found|couldn't find remote ref|not our ref", re.I)
ENTRY_FILES: dict[str, tuple[str, ...]] = {
    "nextflow": ("main.nf",),
    "snakemake": ("Snakefile", "workflow/Snakefile"),
}
SMK_SCHEMAS = ("config.schema.yaml", "workflow/schemas/config.schema.yaml")
MAX_FILE = 1048576  # a config or schema file read by inspect

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


def refuse_control(field: str, value: str) -> None:
    if any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
        raise Invalid(field, "must not hold control characters")


# --- Locations -------------------------------------------------------------------------------


def git_url(location: str) -> tuple[str, tuple[str, ...]]:
    """The URL of a Git location under the import rule of api §5, and the parts of the directory
    it is fetched into (`host`, then the path). Raises Invalid (field `location`)."""
    if SHORT_NAME.fullmatch(location):
        location = f"{GITHUB}/{location}"
    url = urlsplit(location)
    if url.scheme not in GIT_SCHEMES or not location.startswith(f"{url.scheme}://"):
        allowed = ", ".join(f"{s}://" for s in GIT_SCHEMES)
        raise Invalid("location", f"give an absolute path, an owner/repo name or a URL ({allowed})")
    if not URL_CHARS.fullmatch(location):
        raise Invalid("location", "the URL holds a character Spectio does not accept")
    try:
        host, user, password = url.hostname or "", url.username, url.password
        url.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError as exc:
        raise Invalid("location", f"not a URL: {exc}") from None
    if password is not None or (user is not None and url.scheme != "ssh"):
        raise Invalid("location", "credentials do not belong in the URL")
    if url.scheme == "file":
        if host not in ("", "localhost"):
            raise Invalid("location", "a file:// URL names no host")
        host = "local"
    elif not HOST.fullmatch(host):
        raise Invalid("location", "the URL names no valid host")
    parts = url.path.strip("/").split("/")
    parts[-1] = parts[-1].removesuffix(".git")
    if len(parts) > 20 or not all(PART.fullmatch(p) for p in parts):
        raise Invalid("location", "the URL's path must be plain names: no '.', '..' or ''")
    return location, (host, *parts)


def check_revision(revision: str | None) -> str:
    if not revision:
        raise Invalid("revision", "a Git repository needs a revision: a tag, a branch or a commit")
    refuse_control("revision", revision)
    if not REVISION.fullmatch(revision) or ".." in revision or revision.endswith("/"):
        raise Invalid(
            "revision",
            "a tag, a branch or a commit: letters, digits, '.', '_', '-' and '/', "
            "never starting with '-'",
        )
    return revision


def resolve(data_dir: Path, location: str, revision: str | None) -> Resolved:
    """Check a location (fields `location`, `revision`) and fetch it when it is Git."""
    refuse_control("location", location)
    if location.startswith("/"):
        directory = Path(location)
        if not directory.is_dir() or not os.access(directory, os.R_OK | os.X_OK):
            raise Invalid("location", f"{location} is not a directory this account can read")
        return Resolved(str(directory), None, "local", directory, directory.name)
    url, parts = git_url(location)
    revision = check_revision(revision)
    directory = fetch(data_dir, url, parts, revision)
    return Resolved(url, revision, "git", directory, parts[-1])


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


def _read(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open("rb") as f:
        raw = f.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError(f"{path.name} is larger than {MAX_FILE} bytes")
    return raw.decode()


def _jsonable(value: Any) -> Any:
    """YAML dates and the like as strings, so that the response can carry them."""
    return json.loads(json.dumps(value, default=str))


def load_yaml(text: str) -> Any:
    """Safe YAML with no aliases, which would let a small file grow huge in the response."""
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, yaml.AliasEvent):
            raise ValueError("YAML aliases are not read")
    return _jsonable(yaml.safe_load(text))


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
    text = _read(root / "nextflow.config")
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
    found = (root / "profiles").glob("*/config.yaml")
    return sorted(p.parent.name for p in found if p.is_file())


def _type(value: Any) -> dict[str, Any]:
    types: list[tuple[type, str]] = [(bool, "boolean"), (int, "integer"), (float, "number")]
    types += [(str, "string"), (list, "array"), (dict, "object")]
    found = next((t for kind, t in types if isinstance(value, kind)), None)
    return {"default": value} if found is None else {"type": found, "default": value}


def schema_of(root: Path) -> tuple[dict[str, Any] | None, SchemaSource]:
    text = _read(root / "nextflow_schema.json")
    if text is not None:
        return _object(json.loads(text), "nextflow_schema.json"), "nextflow_schema.json"
    for rel in SMK_SCHEMAS:
        text = _read(root / rel)
        if text is not None:
            return _object(load_yaml(text), rel), "config.schema.yaml"
    text = _read(root / "config" / "config.yaml")
    if text is not None:
        config = _object(load_yaml(text), "config/config.yaml")
        props = {str(k): _type(v) for k, v in config.items()}
        return {"type": "object", "properties": props}, "inferred"
    return None, "none"


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is not a mapping")
    return value


def inspect_dir(directory: Path, default_name: str) -> Found:
    """What the launch form needs from a pipeline directory. Raises Invalid (`location`) when
    a schema or config file cannot be read."""
    files = [f for names in ENTRY_FILES.values() for f in names if (directory / f).is_file()]
    engines = [e for e, names in ENTRY_FILES.items() if set(names) & set(files)]
    engine = engines[0] if len(engines) == 1 else None  # both or neither: no guess
    try:
        name, version, nf_profiles = nextflow_config(directory)
        schema, source = schema_of(directory)
    except (ValueError, RecursionError, yaml.YAMLError) as exc:  # JSONDecodeError: ValueError
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


def engine_versions(settings: Settings) -> Callable[[], dict[str, str | None]]:
    """The version of each engine the server would launch with, or None (UX-296, UX-G2-04)."""

    def versions() -> dict[str, str | None]:
        found: dict[str, str | None] = {}
        for engine in ENTRY_FILES:
            cmd = getattr(settings.engines, f"{engine}_cmd")
            try:
                found[engine] = check_engine(engine, cmd).version
            except (EngineError, OSError):
                found[engine] = None
        return found

    return versions


@router.get("/workflows:inspect")
def inspect(request: Request, location: str, revision: str | None = None) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    resolved = resolve(settings.data_dir, location, revision)
    found = inspect_dir(resolved.directory, resolved.default_name)
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
    }
