"""A launch's `default_resources` and `config_file` (FU-P3-110a, api §5.7): the strict models,
the checks against the engine, the profile and the environment, and the read of the file.

The file is read once, at launch, from the descriptor of its allowed root (the user's home from
the password database, or the pipeline's directory; `spectio.locations.check_config_file` says
which): each part after the root is opened with O_NOFOLLOW, so a symbolic link is refused, and
the root, each directory and the file are checked with `fstat`. Every refusal is a ValueError
in words that never quotes the file's bytes; an I/O error is an OSError, which the route
answers with `503`. The run keeps the path, the name the runner will keep it as, its SHA-256,
its size and whether it holds `includeConfig`; the bytes reach the runner in FU-P3-110b.
"""

import contextlib
import errno
import hashlib
import json
import os
import pwd
import stat
from typing import Annotated, Any, Literal

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from spectio.environments import Environment, MemMib
from spectio.locations import refuse_control
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import NO_ALIASES, load_yaml

MAX_CONFIG_FILE = 256 * 1024
KEPT_AS = {
    "config": "extra.config",
    "yaml": "extra.yaml",
    "yml": "extra.yaml",
    "json": "extra.json",
}
_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC
_OTHERS = stat.S_IWGRP | stat.S_IWOTH


class DefaultResources(BaseModel):
    """api §5.7, in the units of §5.4."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    cpus: Annotated[int, Field(ge=1, le=256)] | None = None
    mem_mib: MemMib | None = None
    time_min: Annotated[int, Field(ge=1, le=43_200)] | None = None


def _text(value: str) -> str:
    refuse_control(value)  # a hand-edited manifest: shown as text (req. 10)
    return value


class KeptConfig(BaseModel):
    """The manifest's `config_file` (api §5.7, What the run keeps)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    path: Annotated[str, Field(min_length=2, max_length=4096, pattern=r"^/"), AfterValidator(_text)]
    kept_as: Literal["extra.config", "extra.yaml", "extra.json"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0, le=MAX_CONFIG_FILE)
    includes: bool


def home_roots() -> tuple[str, str]:
    """The user's home from the password database, never `$HOME` (SEC-P3FU110-SPEC-02): as the
    database writes it, and resolved, the directory the walk starts from (CR-P3FU110-SPEC-03)."""
    written = pwd.getpwuid(os.getuid()).pw_dir
    return written, os.path.realpath(written)


def column(model: type[BaseModel], raw: object) -> dict[str, Any] | None:
    """`runs.default_resources` or `runs.config_file` from the manifest's value (req. 10): None
    when there is none, `not_readable` with every field null when it fails the validators."""
    if raw is None:
        return None
    try:
        found = model.model_validate(raw)
    except ValidationError:
        return {**dict.fromkeys(model.model_fields), "state": "not_readable"}
    return {**found.model_dump(mode="json"), "state": "recorded"}


def check_resources(
    resources: DefaultResources, engine: str, profiles: list[str], env: Environment
) -> None:
    """The refusals of api §5.7 for values that could not apply."""
    if engine == "snakemake" and resources.cpus is not None:
        raise Invalid("default_resources.cpus", "Snakemake takes CPUs from each rule's threads")
    if engine == "snakemake" and profiles:
        raise Invalid("default_resources", f"The profile {profiles[0]} sets the resources")
    caps, where = env.local, env.label or env.name
    if caps is None:
        return
    if caps.cpus is not None and (resources.cpus or 0) > caps.cpus:
        raise Invalid("default_resources.cpus", f"At most {caps.cpus} CPUs in {where}")
    if caps.mem_mib is not None and (resources.mem_mib or 0) > caps.mem_mib:
        raise Invalid("default_resources.mem_mib", f"At most {caps.mem_mib} MiB in {where}")


def _refusal(exc: OSError, dir_fd: int | None = None, part: str = "") -> Exception:
    """The refusal in words for an open that failed; `exc` itself for an I/O error. A directory
    part that is a link fails O_DIRECTORY|O_NOFOLLOW with ENOTDIR: `lstat` only words it."""
    if exc.errno == errno.ENOTDIR and dir_fd is not None:
        with contextlib.suppress(OSError):
            if stat.S_ISLNK(os.stat(part, dir_fd=dir_fd, follow_symlinks=False).st_mode):
                exc = OSError(errno.ELOOP, "a link")
    if exc.errno == errno.ELOOP:
        return ValueError("the file is reached through a symbolic link, which is not read")
    if exc.errno in (errno.ENOENT, errno.ENOTDIR):
        return ValueError("there is no such file")
    if exc.errno == errno.EACCES:
        return ValueError("the file cannot be opened: permission denied")
    return exc  # an I/O error: the route's 503


def _checked(fd: int, what: str, uid: int, owners: tuple[int, ...]) -> os.stat_result:
    st = os.fstat(fd)
    if st.st_uid not in owners:
        raise ValueError(f"the {what} is not owned by this user")
    if st.st_mode & _OTHERS:
        raise ValueError(f"the {what} is writable by group or others")
    return st


def _read(start: str, parts: tuple[str, ...], uid: int) -> bytes:
    try:
        fd = os.open(start, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError as exc:
        raise _refusal(exc) from None
    try:
        _checked(fd, "directory", uid, (uid, 0))
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            try:
                child = os.open(part, _FILE if last else _DIR, dir_fd=fd)
            except OSError as exc:
                raise _refusal(exc, fd, part) from None
            os.close(fd)
            fd = child
            if not last:
                _checked(fd, "directory", uid, (uid, 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):  # a directory, a FIFO: never read
            raise ValueError("the file is not a regular file")
        _checked(fd, "file", uid, (uid,))
        with os.fdopen(fd, "rb", closefd=False) as f:
            return f.read(MAX_CONFIG_FILE + 1)
    finally:
        os.close(fd)


def read_config_file(
    start: str, parts: tuple[str, ...], engine: str, uid: int | None = None
) -> dict[str, Any]:
    """`start/parts…` read as api §5.7 says (run it in the file pool): its `kept_as`, `sha256`,
    `size` and `includes`. Raises ValueError for a refusal, OSError for an I/O error."""
    raw = _read(start, parts, os.geteuid() if uid is None else uid)
    if len(raw) > MAX_CONFIG_FILE:
        raise ValueError("the file is larger than 256 KiB")
    try:
        text = raw.decode()
    except UnicodeDecodeError:
        raise ValueError("the file is not UTF-8 text") from None
    if "\x00" in text:
        raise ValueError("the file holds a NUL byte")
    suffix = parts[-1].rsplit(".", 1)[-1]
    if engine == "snakemake":
        _data_only(text, suffix)
    return {
        "kept_as": KEPT_AS[suffix],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
        "includes": engine == "nextflow" and "includeConfig" in text,  # a search, not a parse
    }


def _data_only(text: str, suffix: str) -> None:
    """A Snakemake file stays data: a top-level map without `__use_yte__` (inbox #151 choice 4),
    parsed as the params file of §5.6."""
    kind = "JSON" if suffix == "json" else "YAML"
    try:
        values = json.loads(text) if kind == "JSON" else load_yaml(text)
    except RecursionError:
        raise ValueError("the file is nested too deep to be read") from None
    # Their messages quote the file: not shown.
    except (ValueError, TypeError, yaml.YAMLError) as exc:
        why = "it uses a YAML alias, which is not read" if str(exc) == NO_ALIASES else f"not {kind}"
        raise ValueError(f"the file cannot be read: {why}") from None
    if not isinstance(values, dict):
        raise ValueError("the file is not a map of config keys to values")
    if "__use_yte__" in values:
        raise ValueError("the file sets __use_yte__, which runs code: Spectio does not accept it")
