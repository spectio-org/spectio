"""A launch's `default_resources` and `config_file` (FU-P3-110a, api §5.7): the strict models,
the checks against the engine, the profile and the environment, and the read of the file.

The file is read once, at launch, from the descriptor of its allowed root (the user's home from
the password database, or the pipeline's directory; `spectio.locations.check_config_file` says
which): each part after the root is opened with O_NOFOLLOW, so a symbolic link is refused, and
the root, each directory and the file are checked with `fstat`. Every refusal is a ValueError
in words that never quotes the file's bytes; an I/O error is an OSError, which the route
answers with `503`. The run keeps the path, the name the runner keeps it as, its SHA-256,
its size and whether it holds `includeConfig`; the bytes reach the runner in the launch command
(FU-P3-110b), which keeps them in the run's `.spectio/`: `read_kept` reads that copy back.
"""

import contextlib
import errno
import hashlib
import json
import os
import pwd
import stat
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from fastapi import Request
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from spectio import locations
from spectio.environments import DefaultResources, Environment
from spectio.locations import refuse_control
from spectio.runner.rundir import private_dir
from spectio_server.api.environments import offline
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import NO_ALIASES, load_yaml
from spectio_server.files.pool import READ_TIMEOUT_S, Stalled

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


def _checked(fd: int, what: str, owners: tuple[int, ...]) -> None:
    st = os.fstat(fd)
    if st.st_uid not in owners:
        raise ValueError(f"the {what} is not owned by this user")
    if st.st_mode & _OTHERS:
        raise ValueError(f"the {what} is writable by group or others")


def _read(start: str, parts: tuple[str, ...], uid: int) -> bytes:
    try:
        fd = os.open(start, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError as exc:
        raise _refusal(exc) from None
    try:
        _checked(fd, "directory", (uid, 0))
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            try:
                child = os.open(part, _FILE if last else _DIR, dir_fd=fd)
            except OSError as exc:
                raise _refusal(exc, fd, part) from None
            os.close(fd)
            fd = child
            if not last:
                _checked(fd, "directory", (uid, 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):  # a directory, a FIFO: never read
            raise ValueError("the file is not a regular file")
        _checked(fd, "file", (uid,))
        with os.fdopen(fd, "rb", closefd=False) as f:
            return f.read(MAX_CONFIG_FILE + 1)
    finally:
        os.close(fd)


def read_config_file(
    start: str, parts: tuple[str, ...], engine: str, uid: int | None = None
) -> dict[str, Any]:
    """`start/parts…` read as api §5.7 says (run it in the file pool): its `kept_as`, `sha256`,
    `size` and `includes`, and the bytes as `text`, for the launch command only. Raises
    ValueError for a refusal, OSError for an I/O error."""
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
        "text": text,
    }


def checked_config_file(
    request: Request, path: str, directory: Path, engine: str
) -> dict[str, Any]:
    """`path` checked (`locations.check_config_file`) and read in the file pool, as
    `read_config_file` answers, for `POST /runs` and inspect's check before Launch (FU-P3-121).
    The home is accepted as written and resolved, and read from the resolved one; the pipeline's
    directory as `resolve` gives it. Raises Invalid on `config_file`, or the 503 of `offline`."""
    written, real = request.app.state.home
    starts = {str(directory): str(directory), written: real, real: real}
    try:
        root, parts = locations.check_config_file(path, list(starts), engine)
        found: dict[str, Any] = request.app.state.files.run(
            lambda: read_config_file(starts[root], parts, engine), READ_TIMEOUT_S
        )
    except Stalled as exc:
        raise offline(exc) from None
    except ValueError as exc:
        raise Invalid("config_file", str(exc)) from None
    except OSError as exc:
        raise offline(OSError(f"the config file cannot be read: {exc.strerror}")) from None
    return found


_ABSENT = (errno.ENOENT, errno.ELOOP, errno.ENOTDIR)


def read_kept(runs_root: Path, run_id: str, kept_as: str) -> bytes | None:
    """The run's kept copy (api §5.7), `<run>/launch/.spectio/<kept_as>`, through its private
    directories and opened with O_NOFOLLOW (req. 10, 13); None when it is not there, not a
    regular file of this user writable by no one else, or over 256 KiB. Run it in the file pool:
    an I/O error is an OSError."""
    if kept_as not in KEPT_AS.values():
        return None
    try:
        with private_dir(runs_root, run_id, "launch", ".spectio") as at:
            fd = os.open(kept_as, _FILE, dir_fd=at)
    except OSError as exc:
        # ENOTDIR: `.spectio` replaced by a file, or by a link to one (CR-P3FU110B-05)
        if isinstance(exc, PermissionError) or exc.errno in _ABSENT:
            return None
        raise
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & _OTHERS:
            return None
        data = f.read(MAX_CONFIG_FILE + 1)
    return None if len(data) > MAX_CONFIG_FILE else data


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
