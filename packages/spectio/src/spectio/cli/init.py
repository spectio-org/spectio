"""`spectio init` (P1 Task 8): the data directory, `spectio.toml` and the rows of P1
Assumption 18. Every option has a default, so that `spectio open` can run it unattended."""

import os
import pwd
import shlex
import socket
import stat
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import typer

from spectio.config import DEFAULT_PORT, EngineOpts, Settings, config_path, write_config
from spectio.loginshell import which
from spectio.runner.engines import unpack_nf_spectio


class InitError(Exception):
    """A refusal; the message says why and what to do."""


def _private_dir(path: Path, *, strict: bool = False) -> None:
    """Create `path` with mode 0700, or accept an existing directory of this user that others
    cannot write; never tightened. `strict`: a real directory (no symlink followed) with no
    group or other bits (dev-env §15.3 req. 5)."""
    try:
        os.mkdir(path, 0o700)
        return
    except FileExistsError:
        pass
    except FileNotFoundError as exc:
        raise InitError(f"{path}: its parent directory does not exist") from exc
    if strict:
        try:
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as exc:
            raise InitError(
                f"{path} must be a real directory, not a symlink or a file: {exc.strerror}"
            ) from exc
        try:
            st = os.fstat(fd)
        finally:
            os.close(fd)
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise InitError(
                f"{path} must be a directory of yours with mode 0700 (owner uid {st.st_uid}, "
                f"mode {stat.S_IMODE(st.st_mode):o}): chmod 700 {path}"
            )
        return
    st = os.stat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise InitError(
            f"{path} must be a directory of yours that others cannot write "
            f"(owner uid {st.st_uid}, mode {stat.S_IMODE(st.st_mode):o})"
        )


def _runs_root(settings: Settings) -> Path:
    """The runs root: created when it is the default; a chosen one must exist already. Either
    way, the user's own and not writable by others (dev-env §15.3 req. 10)."""
    path = settings.runs_root
    if "runs_root" in settings.model_fields_set and not path.is_dir():
        raise InitError(f"runs root {path} does not exist: create it on the shared file system")
    _private_dir(path)
    return path


def _free_port(preferred: int) -> int:
    """`preferred` if it is free on 127.0.0.1, else a port the system picks (P1 Assumption 10)."""
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
        except OSError:
            sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _engines(settings: Settings) -> dict[str, Any]:
    """The engine commands: as recorded or given, else the engine on the login shell's PATH."""
    engines = settings.engines.model_dump()
    missing = [n for n in ("nextflow", "snakemake") if not engines[f"{n}_cmd"]]
    for name, path in which(*missing).items():
        if path:
            engines[f"{name}_cmd"] = shlex.quote(path)
        else:
            typer.echo(
                f"warning: {name} not found on the login shell's PATH: give it with --{name}"
            )
    return engines


def _unix_user() -> str:
    """The principal's name: the uid's, never the environment's (P1 Assumption 18)."""
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return str(os.getuid())


def run_init(local: bool, **flags: Any) -> int:
    """`flags`: data_dir, db_dir, runs_root, port, partition, account, nextflow, snakemake;
    None means not given."""
    given: dict[str, Any] = {k: v for k, v in flags.items() if v is not None}
    slurm = {k: given.pop(k) for k in ("partition", "account") if k in given}
    engines = {f"{k}_cmd": given.pop(k) for k in ("nextflow", "snakemake") if k in given}
    if local:
        given["executor"] = "local"
    if slurm:
        given["slurm"] = slurm
    if engines:
        given["engines"] = engines
    try:
        settings = Settings(**given)
        if settings.executor == "local" and sys.platform != "linux":  # inbox #73 (a)
            raise InitError("Local mode needs Linux in 0.0.1")
        if settings.executor == "local" and slurm:
            raise InitError("--partition and --account need a SLURM environment, not --local")
        _init(settings)
    except (ValueError, InitError, OSError) as exc:  # ValueError: a bad flag or spectio.toml
        typer.echo(f"spectio init: {exc}", err=True)
        return 2
    return 0


def _init(settings: Settings) -> None:
    try:
        import spectio_server.bootstrap as server  # the one import of the server (architecture §6)
    except ImportError as exc:
        raise InitError("the server package is missing: install spectio[server]") from exc
    runs_root = _runs_root(settings)
    for path in (config_path().parent, settings.data_dir):
        _private_dir(path, strict=True)
    try:
        # The default is resolved again at each start and never recorded, so that its mkdtemp
        # fallback still applies once the temporary directory is purged (dev-env §15.3).
        db_dir = settings.db_dir or server.default_db_dir()
        if settings.db_dir:
            _private_dir(db_dir)
        settings = settings.model_copy(
            update={
                "port": settings.port
                if "port" in settings.model_fields_set
                else _free_port(DEFAULT_PORT),
                "host": socket.gethostname(),
                "engines": EngineOpts.model_validate(_engines(settings)),
            }
        )
        server.init_store(
            db_dir,
            user=_unix_user(),
            kind=settings.executor,
            config={"runs_root": str(runs_root)},
            version=version("spectio"),
        )
    except server.UnsafeDatabase as exc:
        raise InitError(str(exc)) from exc
    path = write_config(settings)
    typer.echo(f"Wrote {path}; database in {db_dir}; runs under {runs_root}; port {settings.port}")
    try:  # the copy that runs started from a terminal load (architecture §13.8)
        typer.echo(f"nf-spectio in {unpack_nf_spectio()}")
    except (OSError, ValueError) as exc:
        typer.echo(f"warning: nf-spectio not unpacked: {exc}")
